"""The oracle GUI's one page renderer, built from the field registry.

Design note 32, step **OG-D**. There are fourteen oracle pages and no fourteen
page files: :func:`render_step` renders *any* of them from
:mod:`sloads.field_registry`, which already says — per field — which page edits
it, whether the original suite asked for it, and what settles that claim. A page
is therefore the set of registry rows whose ``page`` is this step's key and whose
path is in :func:`~sloads.field_registry.oracle_input_paths`, and the widget for
each row is derived from three owners:

* **shape** — :func:`sloads.field_registry.field_type`, the resolved annotation,
  which decides number vs text vs checkbox vs select vs table;
* **unit** — :func:`sloads.units.field_unit`, the schema's three-way answer
  (converted / aviation-standard / dimensionless), rendered through the shell's
  :func:`~app_shell.components.unit_number_input` boundary so this module holds
  no factor of its own (gate G1);
* **provenance** — the registry row's ``basis``, shown as the field's help, so
  every widget in this GUI can name the ``.BAS`` program that asked for it.

Nothing here computes a load, and nothing here holds a second copy of a page
list: adding a ``bas`` to a workflow step adds a page with no edit to this file
(gate G2), and adding a field to ``models/inputs.py`` adds a widget once the
registry classifies it (gate G4).

**Widget keys.** Every widget here is keyed by what it edits — the registry path,
plus the row index where one path is N widgets — and stamped with the project
generation through :func:`app_shell.widget_keys.widget_key`. Without the stamp
those keys are identical across projects, and Streamlit's retained widget state
beats the ``value=`` this renderer seeds from the project: a page visited before
a load re-rendered its own old values and, since the renderers below persist what
they return, wrote them back over what was just loaded (#51).

**What is hand-declared, and why.** :data:`MEMBER_LABELS` names the members of
the composite fields — an ``XYPoint`` is (X, Z) on a gear leg and (X, Y) on a
planform, and no amount of type introspection can tell them apart. It is
presentation only, never data, and ``tests/test_oracle_gui.py`` fails if a
composite field in the input set is missing from it, so a new one cannot quietly
render as "1, 2".
"""

from __future__ import annotations

import dataclasses
import typing
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from app_shell.components import (
    GRID_COMMIT_NOTE,
    active_system,
    clear_number_input,
    page_header,
    unit_number_input,
)
from app_shell.widget_keys import widget_key
from oracle_app.labels import FIELD_LABELS, pretty
from oracle_app.results import render_results
from sloads import field_registry as fr
from sloads import workflow as wf
from sloads.applicability import step_not_applicable
from sloads.derived import refresh_derived
from sloads.models import Project, same_name
from sloads.selectors import duplicate_selectors, seed_name
from sloads.units import (
    FieldUnit,
    display_format,
    field_unit,
    to_display,
    to_imperial_scalar,
)
from sloads.units import unit_label as _unit_label

#: Member labels for the composite fields the input set contains. Declared
#: because the type cannot carry it: ``Tuple[float, float]`` is a gear axle's
#: (X, Z) in one place and a planform corner's (X, Y) in another.
MEMBER_LABELS: Dict[str, Tuple[str, ...]] = {
    # Gear geometry: fuselage station and waterline.
    "axle_static": ("X", "Z"),
    "axle_compressed": ("X", "Z"),
    "axle_extended": ("X", "Z"),
    "attach": ("X", "Y", "Z"),
    # Engine mass positions.
    "engine_cg": ("X", "Y", "Z"),
    "prop_cg": ("X", "Y", "Z"),
    # WINGGEOM planform polylines: (fuselage station, butt station) per corner.
    "leading_edge": ("X", "Y"),
    "trailing_edge": ("X", "Y"),
    # Spanwise curves: butt station against the value at it.
    "twist": ("Y", "Zero-lift angle (deg)"),
    "profile_drag": ("Y", "CDO"),
    "section_cm": ("Y", "CM"),
    # FLTLOADS' airplane-less-tail polynomials.
    "lift": ("C0", "C1", "C2", "C3", "C4"),
    "drag": ("D0", "D1", "D2", "D3", "D4"),
    "moment": ("M0", "M1", "M2", "M3", "M4"),
    # Single-column lists.
    "altitudes_ft": ("Altitude",),
    "speeds_kt": ("Speed",),
}

#: Name suffixes that are a unit rather than part of the field's name, mapped to
#: what the label should say instead. ``""`` means the widget already shows the
#: unit itself -- :func:`~app_shell.components.unit_number_input` appends the
#: converted or aviation-standard one -- so repeating it in the name would give
#: "Wing Span In (in)". The rest are dimensionless units nothing else states.
_UNIT_SUFFIX = {
    "_in": "", "_lb": "", "_sqft": "", "_hp": "", "_kt": "", "_ft": "",
    "_slugft2": "", "_deg": "deg", "_s": "s", "_rpm": "rpm",
    "_per_rad": "per rad", "_rad_s": "rad/s", "_pct": "%",
}

#: :data:`_UNIT_SUFFIX` **longest suffix first**, which is the only order that
#: answers correctly: ``design_pitch_rate_rad_s`` ends in both ``_s`` and
#: ``_rad_s``, and matching the short one first labelled a rate in rad/s
#: *Design Pitch Rate Rad (s)* -- a unit split in half, with the other half left
#: in the name (PB-22). Declaration order in a dict is the author's, not the
#: matcher's; this makes the matcher's explicit.
_UNIT_SUFFIXES: Tuple[Tuple[str, str], ...] = tuple(
    sorted(_UNIT_SUFFIX.items(), key=lambda item: -len(item[0])))


def _field_label(path: str) -> str:
    """A schema leaf as a widget label: the hand-declared name, else prettified.

    :data:`~oracle_app.labels.FIELD_LABELS` wins over :func:`pretty` because
    some leaves are codes rather than shortened words, but it does **not** win
    over the unit suffix -- an override replaces the *name*, and the unit
    stays -- so a hand-written label cannot accidentally drop the ``(deg)`` off
    a deflection.
    """
    leaf = _leaf(path)
    declared = FIELD_LABELS.get(leaf)
    for suffix, unit in _UNIT_SUFFIXES:
        if leaf.endswith(suffix) and len(leaf) > len(suffix):
            stem = declared if declared is not None else pretty(leaf[: -len(suffix)])
            return f"{stem} ({unit})" if unit else stem
    return declared if declared is not None else pretty(leaf)


def _leaf(path: str) -> str:
    return path.rsplit(".", 1)[-1].replace(fr.LIST_MARKER, "")


def _help(path: str) -> Optional[str]:
    """A field's provenance, from its registry row."""
    row = fr.entry(path)
    return f"`{path}` — {row.basis}" if row else None


def _owner_value(project: Any, owner_path: str) -> Any:
    """The owner field's current value, or ``None`` if any step of it is absent."""
    obj: Any = project
    for segment in owner_path.split("."):
        obj = getattr(obj, segment, None)
        if obj is None:
            return None
    return obj


def _shown(path: str, value: Any) -> str:
    """``value`` (Imperial) written for a caption in the page's own units.

    A caption that quotes a governing number beside a converted widget has to
    convert it too, or the SI reader is told the widget's 19 200 kg "is"
    42,325 -- two numbers for one quantity, on one line, which is the exact
    confusion the copy mark exists to end (#70). The unit label is stated for
    the same reason; a bare number in the wrong system is not less wrong for
    being unlabelled.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return f"{value}"
    system = active_system()
    unit = field_unit(_leaf(path))
    number = to_display(float(value), unit.kind, system) if unit.kind else float(value)
    label = _unit_label(unit, system)
    return f"{number:,.4g}{' ' + label if label else ''}"


def _external_note(row: Any, project: Any, where: Any) -> bool:
    """Mark a copy whose owner is not a field, and never disable it (#69).

    Until now ``_copy_note`` returned early on these rows, so the registry knew
    the engine weight and CG belong to the weight database and the engine-mount
    limit load factor to the computed 23.337 limit -- and the page rendered all
    three as silent peer inputs (C210-41). Half the point of the #36 mark was
    the half it never reached.

    Disabled only when the owner's value can actually be resolved
    (``field_registry.EXTERNAL_VALUES``, #70/PB-17). An external owner is
    usually an expression rather than a path, so there is nothing to substitute
    into the widget, and one of these rows (the weight estimate's horsepower) is
    the *fallback* the analysis uses when the owner is empty -- disabling that
    would make the fallback unenterable. Where a resolver does exist, it is the
    same function the calc calls, so the number shown is the number used; and it
    answering ``None`` is itself meaningful -- the wing-area row's owner is a
    planform, and no planform is exactly when that field stops being inert and
    starts governing, so the widget goes live in the same breath.

    What it says is the row's deliberate answer, never a default: ``resolves``
    verbatim where the rule is conditional, else ``governs`` -- pinned by
    ``tests/test_field_registry.py::test_every_external_copy_states_how_it_resolves``.
    """
    owner = row.external_owner
    governing = fr.external_value(row.path, project) if project is not None else None
    if governing is not None:
        where.caption(
            f"Derived from the **{owner}** ({_shown(row.path, governing)}) — entering a value "
            "here has no effect; the analysis reads the owner."
            + (f" {row.resolves}" if row.resolves else ""))
        return True
    if row.resolves:
        where.caption(f"Also owned by **{owner}** — {row.resolves}")
    elif row.governs:
        where.caption(f"Also held by **{owner}** — the analysis reads the value "
                      "entered here, so the two must be kept in step.")
    else:
        where.caption(f"Owned by **{owner}** — the analysis reads the owner, not "
                      "a value entered here.")
    return False


def _collapsed_note(row: Any, value: Any, project: Any, where: Any,
                    record: Any = None) -> bool:
    """The note 36 collapsed-override caption (OV-9) -- never disabled.

    A path in ``field_registry.COLLAPSED_OVERRIDES`` carries the OV-1 calc
    contract: blank falsy-derives from the owner, a typed value overrides. So
    the widget stays live both ways, and what the caption says tracks the
    stored value: blank shows the derived number the calc will use (the same
    resolver the calc calls -- ``EXTERNAL_VALUES``); typed shows the override
    with the owner's number beside it, and a > 1e-9 disagreement warns (the
    ``_copy_note`` pattern). ``record`` is the row instance for a ``[]`` path
    (which engine, which aero surface).
    """
    governing = fr.external_value(row.path, project, record) if project is not None else None
    owner = (f"**{row.external_owner}**" if row.owner_is_external
             else f"`{row.owner_path}`")
    blank = (not any(value) if isinstance(value, (tuple, list))
             else value is None or not value)
    if blank:
        if governing is not None:
            where.caption(
                f"Blank — derives from {owner} (currently {_shown(row.path, governing)}). "
                "Enter a value only to override.")
        else:
            where.caption(
                f"Blank — derives from {owner}, which cannot answer yet; "
                "0/empty stands until it can, or a value is entered.")
        return False
    where.caption(
        f"Overrides {owner}"
        + (f" (currently {_shown(row.path, governing)})" if governing is not None else "")
        + " — the value entered here is what the analysis uses. Clear it to derive.")
    if (isinstance(governing, (int, float)) and isinstance(value, (int, float))
            and not isinstance(governing, bool) and not isinstance(value, bool)
            and abs(float(governing) - float(value)) > 1e-9):
        where.warning(
            f"This is {_shown(row.path, value)} but {owner} says "
            f"{_shown(row.path, governing)}. The typed value governs — confirm "
            "the disagreement is intended.")
    return False


def _copy_note(path: str, value: Any, project: Any, where: Any,
               record: Any = None) -> bool:
    """Mark a non-owner copy; return ``True`` if it must render **disabled**.

    The registry has always known which field owns each shared quantity; until
    now nothing in the renderer read it, so a user could enter a wing area on one
    page and a different one on another and feed both to the calc with no warning
    (#36, CR-A-2). What the mark says depends on ``FieldEntry.governs``:

    * **display-only** (``governs=False``) — the consumer resolves the owner
      instead, so the widget is disabled and shows the governing value. Anything
      stored here is inert, and the caption says so rather than letting the page
      imply an input that does nothing.
    * **override** (``governs=True``) — the calc reads this field verbatim, so it
      stays editable; the caption names the owner and its value, and a
      disagreement is called out. A disagreement is *legal* here — that is what
      an override is — so this warns, it does not correct.
    """
    row = fr.entry(path)
    if row is None or row.is_owner:
        return False
    if row.governs and path in fr.COLLAPSED_OVERRIDES:
        return _collapsed_note(row, value, project, where, record)
    if row.owner_is_external:
        return _external_note(row, project, where)
    owner = row.owner_path
    if not owner:
        return False
    owner_value = _owner_value(project, owner)
    owner_label = f"`{owner}`"

    if row.display_only:
        where.caption(
            f"Derived from {owner_label} — entering a value here has no effect; "
            "the analysis reads the owner.")
        return True

    where.caption(f"Overrides {owner_label}"
                  + (f" (currently {_shown(path, owner_value)})"
                     if isinstance(owner_value, (int, float)) and not isinstance(owner_value, bool)
                     else "")
                  + " — a value entered here is what the analysis uses.")
    if (isinstance(owner_value, (int, float)) and isinstance(value, (int, float))
            and not isinstance(owner_value, bool) and not isinstance(value, bool)
            and owner_value and value and abs(float(owner_value) - float(value)) > 1e-9):
        where.warning(
            f"This is {_shown(path, value)} but {owner_label} says "
            f"{_shown(owner, owner_value)}. Both reach the calc, on different "
            "pages — confirm which is intended.")
    return False


def _mark_composite(path: str, project: Any, where: Any,
                    record: Any = None) -> None:
    """The non-owner mark for a composite field (#89, code review 2026-08-24 §4.3).

    ``_copy_note`` was reachable from :func:`render_scalar` alone, so the first
    non-owner **tuple, curve or enum set** would have shipped unmarked and
    silently editable -- the #36/CR-A-2 defect returning through a door that was
    never closed. Marking the external owners (#69) walked straight through it:
    ``engines[].engine_cg`` is a three-member tuple, and it is a copy of the
    weight database.

    Caption only, never disabled: a composite widget is N sub-widgets and there
    is no single value to substitute. A *display-only* composite would therefore
    be unmarkable, so the registry is not allowed to hold one --
    ``tests/test_oracle_gui.py::test_every_non_owner_field_is_on_a_route_that_can_mark_it``.
    """
    if project is None:
        return
    value = getattr(record, _leaf(path), None) if record is not None else None
    _copy_note(path, value, project, where, record)


# --------------------------------------------------------------------------- #
# Type introspection: what widget does this annotation want?
# --------------------------------------------------------------------------- #
def _unwrap_optional(hint: object) -> Tuple[object, bool]:
    """``(inner, was_optional)`` for ``Optional[T]``; ``(hint, False)`` otherwise."""
    args = typing.get_args(hint)
    if typing.get_origin(hint) is typing.Union and type(None) in args:
        rest = [a for a in args if a is not type(None)]
        if len(rest) == 1:
            return rest[0], True
    return hint, False


def _enum_of(hint: object) -> Optional[type]:
    inner, _ = _unwrap_optional(hint)
    return inner if isinstance(inner, type) and issubclass(inner, Enum) else None


def _tuple_arity(hint: object) -> int:
    """The fixed length of a ``Tuple[float, ...]`` annotation, else 0."""
    inner, _ = _unwrap_optional(hint)
    if typing.get_origin(inner) is tuple:
        args = typing.get_args(inner)
        return 0 if Ellipsis in args else len(args)
    return 0


def _list_element(hint: object) -> Optional[object]:
    """The element annotation of a ``List[...]``/``Set[...]``, else ``None``."""
    inner, _ = _unwrap_optional(hint)
    if typing.get_origin(inner) in (list, set):
        args = typing.get_args(inner)
        return args[0] if args else None
    return None


def is_composite(hint: object) -> bool:
    """True if the field needs more than one number/word to hold its value."""
    return _tuple_arity(hint) > 0 or _list_element(hint) is not None


# --------------------------------------------------------------------------- #
# Building the records the widgets write into
# --------------------------------------------------------------------------- #
def blank(cls: type) -> Any:
    """An instance of ``cls`` with every structurally required field zeroed.

    Several input records have no argument-free form -- a ``SurfaceInput``
    without edges is not a surface, which is exactly the property gate G5's
    ``structurally_required`` rule rests on. The oracle GUI still has to be able
    to create one before the user has typed anything, so the required fields get
    the empty value of their own type and the user fills them in.
    """
    kwargs: Dict[str, Any] = {}
    hints = typing.get_type_hints(cls)
    for field in dataclasses.fields(cls):
        if (field.default is not dataclasses.MISSING
                or field.default_factory is not dataclasses.MISSING):
            continue
        kwargs[field.name] = _empty_value(hints.get(field.name, field.type))
    return cls(**kwargs)


def _empty_value(hint: object) -> Any:
    inner, optional = _unwrap_optional(hint)
    if optional:
        return None
    enum = _enum_of(inner)
    if enum is not None:
        return next(iter(enum))
    arity = _tuple_arity(inner)
    if arity:
        return tuple(0.0 for _ in range(arity))
    if typing.get_origin(inner) is list:
        return []
    if typing.get_origin(inner) is set:
        return set()
    if inner is str:
        return ""
    if inner is bool:
        return False
    if inner is int:
        return 0
    if isinstance(inner, type) and dataclasses.is_dataclass(inner):
        return blank(inner)
    return 0.0


# --------------------------------------------------------------------------- #
# Writing to the project: only what the user actually changed (OG-F)
# --------------------------------------------------------------------------- #
#: Records this render pass created but has not attached to the project. A page
#: needs somewhere for its widgets to write *before* it knows whether anything
#: will be written, so a missing record is built detached and committed by
#: :func:`commit_pending` only if the pass left something in it. Keyed on
#: ``(id(owner), attribute)`` so every group that walks through the same missing
#: ancestor gets the **same** pending record (#35, CR-A-1) -- when it was a
#: plain append, eight groups on the Geometry page each minted their own blank
#: ``geometry`` and the last non-blank chain clobbered the earlier ones on
#: commit, silently discarding one of two edits made in one rerun. Insertion
#: order is creation order (parent before child), which :func:`commit_pending`
#: relies on. Reset at the top of :func:`render_step`, which is the only entry
#: point; module state rather than a threaded argument because Streamlit runs
#: one script at a time and every reader is in this file.
_PENDING: Dict[Tuple[int, str], Tuple[Any, str, Any]] = {}


def _persist(record: Any, name: str, value: Any) -> None:
    """Write ``value`` only if it differs from what is already there.

    A render pass must not mutate the project (``tests/test_dirty_flag.py``,
    M2-3), and the naive ``setattr`` on every rerun broke that twice over: it
    re-wrote every field of every visited page, and it rewrote ``45`` as
    ``45.0`` because a widget returns a float where the JSON held an int --
    the same number, a different file, an "Unsaved changes" flag the user
    never earned. Equality settles both (``45 == 45.0``). The second clause
    keeps an *absent* field absent: a ``None`` rendered as the type's empty
    value is still unfilled, and only a real entry makes it real. It guards the
    widgets that must show *something* for ``None`` (text, tuples, curves);
    Optional scalars render empty instead and route typed values -- including
    a deliberate ``0`` -- through :func:`_set_entered` (#35, CR-A-3).
    """
    current = getattr(record, name, None)
    if current == value or (current is None and not value):
        return
    setattr(record, name, value)


def _set_entered(record: Any, name: str, value: Any) -> None:
    """Write a value the user actually entered, even a falsy one (#35, CR-A-3).

    The persist path for a widget that was **seeded empty** -- an unfilled
    Optional scalar rendered blank, a table cell that displayed NaN. Anything
    that came back from one is a real entry, so a deliberate ``0`` (sea level
    into ``one_engine_out.altitude_ft``, a datum-at-nose ``fuselage_nose_x``)
    must land where :func:`_persist`'s absent-stays-absent clause would read
    it as the untouched seed and drop it.
    """
    if getattr(record, name, None) != value:
        setattr(record, name, value)


def _clear_optional(record: Any, name: str, *, optional: bool) -> None:
    """An empty number widget means the field is unfilled -- if it may be (#72).

    The one place that reads an empty widget back into the model, so "cleared
    means unfilled" is stated once. It is reached only through
    :func:`_offer_clear`\'s button (a filled widget cannot come back empty by
    itself), and it is equality-guarded through :func:`_set_entered`, so a field
    that was already unfilled writes nothing and a page merely visited stays
    clean (M2-3, ``tests/test_dirty_flag.py``).

    A **required** field is left exactly as it was: ``None`` is not one of its
    values, and writing it would hand the loader a file to repair. The widget
    cannot be emptied by the user, so there is nothing to explain here -- the
    reachable half of that case is a required *table cell*, which says so
    (:func:`_render_flat_table`).
    """
    if optional:
        _set_entered(record, name, None)


def _offer_clear(where: Any, key: str, kind: Optional[str], *, path: str,
                 optional: bool) -> None:
    """The way back from an entered Optional override to "computed" (#72, PB-20).

    Once ``landing.gear_load_factor``, ``speeds.chosen_vc`` or
    ``weight.envelope.mac`` held a number, this GUI could not un-set it: an
    override was a one-way door, and the only escape was hand-editing the JSON in
    an editor this GUI does not have. The review proposed writing ``None`` when
    the widget comes back empty; it cannot work, because a number-seeded
    ``st.number_input`` never comes back empty (see
    :func:`app_shell.components.clear_number_input`). So the clear is a
    deliberate, named click -- the same posture row deletion takes (#88) -- and
    it goes through the ``on_click`` callback, the only moment Streamlit allows a
    widget\'s state to be written.

    Rendered only where there is something to clear: an Optional field, holding a
    value, whose widget is live. A display-only copy of someone else\'s quantity
    is disabled and never reaches here.
    """
    if not optional:
        return
    where.button(
        "✕ clear", key=widget_key(f"{key}.clear"), on_click=clear_number_input,
        args=(key, kind),
        help=f"Clear {_field_label(path)} — the field goes back to unfilled, and "
             "whatever the program computes for it governs again.")


def seeded(cls: type, path: str, index: int = 0, taken: Sequence[str] = ()) -> Any:
    """A :func:`blank` record whose selector name is already meaningful.

    ``sloads.selectors.seed_name`` says what a new row at ``path`` is called
    (the first surface ``wing``, CG cases ``CG1 … CGn``, ``CRUISE`` /
    ``LANDING``), skipping any name ``taken`` already (#63, PB-5/PB-9). A
    seeded record is still *untouched* for :func:`_is_blank`, so visiting a
    page attaches nothing.
    """
    record = blank(cls)
    if hasattr(record, "name") and not record.name:
        name = seed_name(f"{path}.name", index)
        i = index
        while name and any(same_name(name, t) for t in taken):
            i += 1
            name = seed_name(f"{path}.name", i)
        record.name = name
    return record


def _is_blank(value: Any) -> bool:
    """True if ``value`` is an untouched record (or an empty list of them).

    A seeded selector name does not count as a touch: the user did not type
    it, so it alone must not attach the record.
    """
    if isinstance(value, list):
        return not value
    untouched = blank(type(value))
    if hasattr(value, "name") and dataclasses.is_dataclass(value):
        return dataclasses.replace(value, name="") == untouched
    return value == untouched


def commit_pending() -> None:
    """Attach the records this pass created, if the pass put something in them.

    A chain is attached whole or not at all: filling ``geometry.parametric`` on
    a project with no ``geometry`` must attach both, and touching neither must
    leave the project exactly as it was found.
    """
    entries = list(_PENDING.values())
    needed = set()
    for owner, _, value in reversed(entries):
        if id(value) in needed or not _is_blank(value):
            needed.add(id(value))
            needed.add(id(owner))
    for owner, name, value in entries:
        if id(value) in needed:
            setattr(owner, name, value)
    _PENDING.clear()


def record_at(project: Project, prefix: str) -> Any:
    """The record instance at ``prefix``, creating every missing step of the way.

    The oracle GUI's job on a fresh project is to *make* the slices, so a missing
    one is the normal state rather than an error: an absent ``speeds`` means the
    Structural Speeds page has not been filled in yet, not that it is unavailable.
    A record created here is **detached** until :func:`commit_pending` decides
    the page earned it -- see :data:`_PENDING`. A step another group of this
    same pass already created is **reused**, never re-minted: two blanks for
    one ``(owner, attribute)`` would race each other at commit and one group's
    edits would win over the other's (#35, CR-A-1).
    """
    obj: Any = project
    for segment in [s for s in prefix.split(".") if s]:
        value = getattr(obj, segment, None)
        if value is None:
            pending = _PENDING.get((id(obj), segment))
            if pending is not None:
                value = pending[2]
            else:
                path = _path_of(obj, segment, prefix)
                hint = fr.field_type(path)
                inner, _ = _unwrap_optional(hint)
                if not (isinstance(inner, type) and dataclasses.is_dataclass(inner)):
                    return None
                value = seeded(inner, path)
                _PENDING[(id(obj), segment)] = (obj, segment, value)
        obj = value
    return obj


def _path_of(_obj: object, segment: str, prefix: str) -> str:
    """The registry path of ``segment`` within ``prefix`` (a dotted head slice)."""
    parts = prefix.split(".")
    return ".".join(parts[: parts.index(segment) + 1])


def rows_at(project: Project, prefix: str) -> List[Any]:
    """The list a ``…[]`` record prefix names, creating the chain to it."""
    head, _, attr = prefix.rstrip(fr.LIST_MARKER).rpartition(".")
    owner = record_at(project, head) if head else project
    if owner is None:
        return []
    rows = getattr(owner, attr, None)
    if rows is None:
        pending = _PENDING.get((id(owner), attr))
        if pending is not None:
            return pending[2]
        rows = []
        _PENDING[(id(owner), attr)] = (owner, attr, rows)
    return rows


def row_class(prefix: str, paths: Sequence[str]) -> Optional[type]:
    """The dataclass one row of a ``…[]`` record is an instance of."""
    element = _list_element(fr.field_type(prefix.rstrip(fr.LIST_MARKER)))
    if isinstance(element, type) and dataclasses.is_dataclass(element):
        return element
    located = fr._locate(paths[0])
    return located[0] if located else None


# --------------------------------------------------------------------------- #
# Scalar widgets
# --------------------------------------------------------------------------- #
def _number(label: str, value: Optional[float], unit: FieldUnit, key: str,
            **kwargs: Any) -> Optional[float]:
    """A number in display units that comes back Imperial, via the shell boundary.

    ``None`` in renders the widget empty and comes back ``None`` until the user
    enters a number (#35, CR-A-3); a float in always comes back a float.
    """
    seed = None if value is None else float(value)
    if unit.kind is not None:
        return unit_number_input(label, seed, kind=unit.kind, key=key, **kwargs)
    if unit.fixed_label is not None:
        return unit_number_input(
            label, seed, fixed_unit=unit.fixed_label, key=key, **kwargs)
    return unit_number_input(label, seed, key=key, **kwargs)


def render_scalar(record: Any, path: str, *, key: str, container: Any = None,
                  project: Any = None) -> None:
    """One widget for one non-composite field, written straight back to ``record``.

    ``key`` is the Streamlit widget key. It is not the registry path, because a
    table row repeats every path: ``weight.items[].name`` is one registry row and
    N widgets. The caller owns uniqueness, so the field renderers never have to
    know that tables exist.

    ``project`` is needed only to resolve the *owner* of a shared quantity
    (#36) — pass it wherever one is available and the field gets its
    derived/override marking; omit it and the widget renders unmarked, which is
    what a detached unit test wants.
    """
    where = container if container is not None else st
    name = _leaf(path)
    hint = fr.field_type(path)
    inner, optional = _unwrap_optional(hint)
    label, help_text = _field_label(path), _help(path)
    value = getattr(record, name)

    # A non-owner copy is marked, and a display-only one is disabled and shows the
    # value that actually governs. It is never *persisted* from here: rendering a
    # page must not write to the project (OG-F), so the stored copy keeps whatever
    # it held and only the display tells the truth.
    disabled = (_copy_note(path, value, project, where, record)
                if project is not None else False)
    if disabled:
        row = fr.entry(path)
        governing = None
        if row is not None:
            governing = (fr.external_value(path, project, record) if row.owner_is_external
                         else _owner_value(project, row.owner_path))
        if governing is not None:
            value = governing

    enum = _enum_of(inner)
    if enum is not None:
        options: List[Any] = ([None] if optional else []) + list(enum)
        current = value if value in options else options[0]
        chosen = where.selectbox(
            label, options, index=options.index(current), key=widget_key(key),
            help=help_text,
            format_func=lambda o: "—" if o is None else f"{o.value} · {pretty(o.name)}",
            disabled=disabled,
        )
        if not disabled:
            _persist(record, name, chosen)
        return

    if inner is bool:
        entered_bool = where.checkbox(label, bool(value), key=widget_key(key),
                                      help=help_text, disabled=disabled)
        if not disabled:
            _persist(record, name, entered_bool)
        return

    codes = fr.CODED_FIELDS.get(path)
    if codes is not None:
        # A coded field offers its codes, never free text: "Utility" and "u"
        # both fell through every ``== "U"`` to Normal's 3.8 (#63, PB-8). A
        # stored value outside the table is still shown, marked, so a loaded
        # file is not silently rewritten -- STRSPEED refuses it by name.
        options_s: List[str] = list(codes)
        current_s = (value or "").strip().upper()
        if current_s not in options_s:
            options_s.append(current_s)
        chosen_s = where.selectbox(
            label, options_s, index=options_s.index(current_s), key=widget_key(key),
            help=help_text, disabled=disabled,
            format_func=lambda c: f"{c} · {codes[c]}" if c in codes else f"{c or '—'} · (not a known code)")
        if not disabled:
            _persist(record, name, chosen_s)
        return

    if inner is str:
        entered_str = where.text_input(label, value or "", key=widget_key(key),
                                       help=help_text, disabled=disabled)
        if not disabled:
            _persist(record, name, entered_str)
        return

    # An unfilled Optional renders *empty*, not as a fake 0 (#35, CR-A-3): the
    # widget returns None until the user enters a number, so anything it does
    # return -- including 0 -- is a real entry and lands via _set_entered. The
    # return leg is the clear button below (#72): once filled, the widget itself
    # can never come back empty.
    unit = field_unit(name)
    if inner is int:
        entered = where.number_input(
            f"{label} ({_unit_label(unit, active_system())})".replace(" ()", ""),
            value=None if (optional and value is None) else int(value or 0),
            step=1, key=widget_key(key), help=help_text, disabled=disabled)
        if disabled:
            return
        if entered is None:
            _clear_optional(record, name, optional=optional)
            return
        _offer_clear(where, key, None, path=path, optional=optional)
        if optional and value is None:
            _set_entered(record, name, int(entered))
        else:
            _persist(record, name, int(entered))
        return

    entered = _number(
        label, None if (optional and value is None) else float(value or 0.0),
        unit, key, container=where, help=help_text, format=display_format(unit),
        disabled=disabled)
    if disabled:
        return
    if entered is None:
        _clear_optional(record, name, optional=optional)
        return
    _offer_clear(where, key, unit.kind, path=path, optional=optional)
    if optional and value is None:
        _set_entered(record, name, float(entered))
    else:
        _persist(record, name, float(entered))


# --------------------------------------------------------------------------- #
# Composite widgets
# --------------------------------------------------------------------------- #
def _members(path: str, arity: int) -> Tuple[str, ...]:
    """Member labels for a composite field, or positional ones as a last resort."""
    declared = MEMBER_LABELS.get(_leaf(path), ())
    return declared if len(declared) >= arity else tuple(str(i + 1) for i in range(arity))


def _member_units(path: str, arity: int) -> Tuple[FieldUnit, ...]:
    """One :class:`FieldUnit` per member: the declared pair, else the field's own."""
    unit = field_unit(_leaf(path))
    if unit.members:
        return unit.members
    return tuple(unit for _ in range(arity))


def render_tuple(record: Any, path: str, *, key: str, container: Any = None,
                 project: Any = None) -> None:
    """A fixed-length numeric tuple as one labelled input per member."""
    where = container if container is not None else st
    _mark_composite(path, project, where, record)
    name = _leaf(path)
    arity = _tuple_arity(fr.field_type(path))
    current = list(getattr(record, name) or [0.0] * arity)
    current += [0.0] * (arity - len(current))

    where.markdown(f"**{_field_label(path)}**", help=_help(path))
    columns = where.columns(arity)
    units = _member_units(path, arity)
    entered = [
        _number(member, float(current[i]), units[i], f"{key}.{i}",
                container=columns[i], format=display_format(units[i]))
        for i, member in enumerate(_members(path, arity))
    ]
    _persist(record, name, tuple(entered))


def render_curve(record: Any, path: str, *, key: str, container: Any = None,
                 project: Any = None) -> None:
    """A ``List[XYPoint]`` / ``List[float]`` as an editable table of its members."""
    where = container if container is not None else st
    _mark_composite(path, project, where, record)
    name = _leaf(path)
    element = _list_element(fr.field_type(path))
    arity = _tuple_arity(element) or 1
    units = _member_units(path, arity)
    labels = _members(path, arity)
    system = active_system()
    headers = [f"{lbl} ({_unit_label(units[i], system)})".replace(" ()", "")
               for i, lbl in enumerate(labels)]

    rows = getattr(record, name) or []
    display = [
        [_to_display(v, units[i]) for i, v in enumerate(row if arity > 1 else [row])]
        for row in rows
    ]
    where.markdown(f"**{_field_label(path)}**", help=_help(path))
    # ``dtype=float`` even when ``display`` is empty: a frame built from no rows
    # has object-typed columns, which the grid renders as *text* -- so every
    # polyline typed from blank came back as strings ('28', '0'), was stored as
    # string tuples and crashed WINGGEOM on ``ytip - yroot`` (C210-7, the
    # Cessna 210 build review 2026-08-23). A curve's members are all numeric.
    # The base frame is *stable per page visit* (C210-4, _FRAME_CACHE_KEY):
    # added/edited/deleted rows live in the widget's own state, so the row
    # count must NOT be in the cache key -- the editor itself grows the model.
    frame = _stable_frame(
        f"{widget_key(key)}|{system.value}",
        lambda: pd.DataFrame(display, columns=headers, dtype=float),
    )
    edited = where.data_editor(
        frame, num_rows="dynamic", key=widget_key(key), width="stretch",
    )
    # ``rows`` is what was rendered, so row ``n`` of the editor is row ``n`` of
    # the stored curve until the user adds or removes one -- and past that point
    # the value has genuinely changed, so reconstructing it is correct.
    def _stored(index: int, member: int) -> Any:
        if index >= len(rows):
            return None
        row = rows[index]
        return row[member] if arity > 1 else row

    entered = edited.values.tolist()
    kept = [
        [_numeric(_to_imperial_kept(v, units[i], _stored(n, i))) for i, v in enumerate(values)]
        for n, values in enumerate(entered)
        if not any(pd.isna(v) for v in values)
    ]
    _persist(record, name, [tuple(r) if arity > 1 else r[0] for r in kept])
    # A row with an empty cell is held out of the stored curve; that used to be
    # silent, so a half-typed corner just vanished on rerun (#35, CR-A-6). An
    # all-empty row is a freshly added one, not a partial entry -- no nagging.
    if any(any(pd.isna(v) for v in values) and not all(pd.isna(v) for v in values)
           for values in entered):
        where.caption("Rows with an empty cell are not saved — fill every "
                      "column to keep the row.")


def render_enum_set(record: Any, path: str, *, key: str, container: Any = None,
                    project: Any = None) -> None:
    """A ``Set[Enum]`` as a multiselect."""
    where = container if container is not None else st
    _mark_composite(path, project, where, record)
    name = _leaf(path)
    enum = _list_element(fr.field_type(path))
    assert isinstance(enum, type) and issubclass(enum, Enum)
    chosen = where.multiselect(
        _field_label(path), list(enum), default=sorted(getattr(record, name) or (),
                                                       key=lambda m: m.value),
        key=widget_key(key), help=_help(path), format_func=lambda m: pretty(m.name))
    _persist(record, name, set(chosen))


def _to_display(value: Any, unit: FieldUnit) -> Any:
    if unit.kind is None or not isinstance(value, (int, float)):
        return value
    return to_display(float(value), unit.kind, active_system())


def _to_imperial(value: Any, unit: FieldUnit) -> Any:
    if unit.kind is None or not isinstance(value, (int, float)):
        return value
    return to_imperial_scalar(float(value), unit.kind, active_system())


#: Session-state key of the per-page grid frame cache (C210-4, build review
#: 2026-08-23). ``st.data_editor``'s widget identity includes the data bytes,
#: so a grid whose input frame is rebuilt from the model on every rerun gets a
#: **new identity after every committed cell** -- the frontend remounts it, and
#: any keystroke in flight when the remount lands is silently discarded (the
#: classic write-back anti-pattern: cells lost at normal typing pace, a typed
#: minus sign swallowed). The base frame is therefore built **once per page
#: visit** and reused byte-identically; every edit lives in the widget's own
#: state and is persisted to the model each run (idempotently -- `_persist` /
#: `_set_entered` are equality-guarded). The cache is keyed by widget key +
#: unit system (+ row count for count-driven tables) and reset on page change,
#: so a project load (generation bump), a unit toggle, a row-count change or
#: navigating away all rebuild from the model.
_FRAME_CACHE_KEY = "_grid_frame_cache"


def _reset_frame_cache(step_key: str) -> None:
    """Drop cached grid frames when the page changes (see _FRAME_CACHE_KEY)."""
    try:
        cache = st.session_state.get(_FRAME_CACHE_KEY)
        if not isinstance(cache, dict) or cache.get("__step") != step_key:
            st.session_state[_FRAME_CACHE_KEY] = {"__step": step_key}
    except Exception:  # bare mode: no session state, no cache
        pass


def _stable_frame(ckey: str, build: "Callable[[], pd.DataFrame]") -> pd.DataFrame:
    """The grid's base frame: cached per page visit, else freshly built."""
    try:
        cache = st.session_state.get(_FRAME_CACHE_KEY)
    except Exception:
        cache = None
    if not isinstance(cache, dict):
        return build()
    frame = cache.get(ckey)
    if frame is None:
        frame = build()
        cache[ckey] = frame
    return frame


def _numeric(value: Any) -> Any:
    """``value`` as a number: a grid cell that came back as text is parsed, a
    number is returned as it is (an ``int`` stays an ``int``, so an untouched
    stored value is still equal to itself). A curve member is always numeric
    (C210-7); a cell that cannot be parsed raises, which the page shows."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return float(value)


def _to_imperial_kept(value: Any, unit: FieldUnit, stored: Any) -> Any:
    """``value`` back in Imperial, or ``stored`` unchanged if it was untouched.

    The rounding trap, in the paths that convert for themselves (the composite
    and table widgets; ``unit_number_input`` already does this for scalars).
    In SI, ``116 in`` goes out as ``2946.4 mm`` and comes back as
    ``115.99999999999999`` -- so an SI user rendering a geometry page walked
    every station a hair, on every rerun, having typed nothing. The widget hands
    back exactly the float it was given when the user has not touched it, so
    equality *in display space* is the test for "unchanged", and the stored
    value is returned untouched rather than reconstructed.
    """
    numeric = isinstance(stored, (int, float)) and not isinstance(stored, bool)
    if numeric and value == _to_display(stored, unit):
        return stored
    return _to_imperial(value, unit)


def render_field(record: Any, path: str, *, key: str, container: Any = None,
                 project: Any = None) -> None:
    """The one entry point per field: pick the widget its annotation asks for.

    ``project`` is forwarded to every branch so the non-owner mark reaches
    composites too, not scalars alone (#89) -- pass it wherever one is
    available; omit it and the widget renders unmarked, which is what a detached
    unit test wants.
    """
    hint = fr.field_type(path)
    element = _list_element(hint)
    if isinstance(element, type) and issubclass(element, Enum):
        render_enum_set(record, path, key=key, container=container, project=project)
    elif element is not None:
        render_curve(record, path, key=key, container=container, project=project)
    elif _tuple_arity(hint):
        render_tuple(record, path, key=key, container=container, project=project)
    else:
        render_scalar(record, path, key=key, container=container, project=project)


# --------------------------------------------------------------------------- #
# Records and tables
# --------------------------------------------------------------------------- #
#: Scalar fields shown per row of a record block.
_COLUMNS = 3


def render_record(project: Project, prefix: str, paths: Sequence[str]) -> None:
    """One non-list record: its scalars in a grid, its composites underneath."""
    record = record_at(project, prefix)
    if record is None:
        st.warning(f"`{prefix}` cannot be created on this project.")
        return

    scalars = [p for p in paths if not is_composite(fr.field_type(p))]
    composites = [p for p in paths if is_composite(fr.field_type(p))]

    for start in range(0, len(scalars), _COLUMNS):
        columns = st.columns(_COLUMNS)
        for column, path in zip(columns, scalars[start:start + _COLUMNS]):
            render_scalar(record, path, key=path, container=column, project=project)
    for path in composites:
        render_field(record, path, key=path, project=project)


def _delete_row(rows: List[Any], index: int, prefix: str) -> None:
    """Remove one row of a list record, wherever it sits in the table (#72, PB-23).

    Until now a row could only be removed from the **end** -- the count widget
    plus the surplus button (#88) -- so dropping item 4 of 24 meant deleting
    twenty rows and retyping nineteen. This is the same deletion contract seen
    from the middle of the list: a deliberate click on a control that names the
    row it removes (``GUI_design.md``, "a widget never deletes entered data").

    It runs as an ``on_click`` callback because it must also re-size the row
    counter. The counter\'s retained state outlives the delete, and
    :func:`render_table` grows the list back up to it on the very next render --
    so a deletion that did not move the counter would reappear as a blank row,
    which is the #88 defect wearing the other sign. Widget state may only be
    written before its widget is instantiated, which is what a callback is.
    """
    if 0 <= index < len(rows):
        del rows[index]
    st.session_state[widget_key(f"{prefix}.count")] = len(rows)


def _delete_button(where: Any, rows: List[Any], index: int, prefix: str,
                   title: str) -> None:
    """A per-row delete control, naming the row it removes (:func:`_delete_row`)."""
    where.button(
        f"\U0001f5d1 Delete row {index + 1} · {title}",
        key=widget_key(f"{prefix}.{index}.delete"),
        on_click=_delete_row, args=(rows, index, prefix),
        help=f"Removes **{title}** from the project. The row count follows; "
             "nothing else in the table moves.")


def render_table(project: Project, prefix: str, paths: Sequence[str]) -> None:
    """One list record. Flat rows get a data editor; rows holding a composite get
    an expander each, because a table cell cannot hold a polyline."""
    rows = rows_at(project, prefix)
    cls = row_class(prefix, paths)
    if cls is None:
        st.warning(f"`{prefix}` cannot be created on this project.")
        return

    label = pretty(prefix.rstrip(fr.LIST_MARKER).rsplit(".", 1)[-1])
    count = st.number_input(
        f"{label} — rows", min_value=0, value=len(rows), step=1,
        key=widget_key(f"{prefix}.count"))
    while len(rows) < count:
        rows.append(seeded(cls, prefix, len(rows),
                           taken=[getattr(r, "name", "") for r in rows]))
    # Counting **down** deletes nothing. ``rows`` is the project's own attached
    # list, so the ``rows.pop()`` that used to close this gap destroyed entered
    # data during a render pass: typing 3 here dropped 21 of 24 weight items with
    # no confirmation and no undo, and counting back up returned blanks -- the
    # user-triggered half of the #51 data-loss class the generation stamp closed
    # only for the state-triggered one. The same pop also fired with no user
    # interaction at all when the model grew underneath a retained count
    # (``02_parked.md`` L-8d's mutation case; #78's seed button is such a
    # writer). The model wins both ways now, and a deletion is a deliberate,
    # named click.
    if count < len(rows):
        surplus = len(rows) - count
        going = [getattr(r, "name", "") or f"row {i + 1}"
                 for i, r in enumerate(rows[count:], start=count)]
        shown = ", ".join(f"**{n}**" for n in going[:6]) + (" …" if len(going) > 6 else "")
        st.warning(
            f"The row count says {count:,d}, but {label} still holds "
            f"{len(rows):,d}. Counting down does not delete entered rows. To "
            f"remove the last {surplus:,d} ({shown}), use the button below — "
            "otherwise set the count back."
        )
        if st.button(f"🗑 Delete the last {surplus:,d} row(s) of {label}",
                     key=widget_key(f"{prefix}.delete_surplus")):
            del rows[count:]
            st.rerun()
    if not rows:
        return

    if any(is_composite(fr.field_type(p)) for p in paths):
        for index, row in enumerate(rows):
            title = _row_title(row, paths, f"{prefix}.{index}")
            with st.expander(f"{index + 1} · {title}", expanded=index == 0):
                render_record_row(row, paths, f"{prefix}.{index}", project)
                _delete_button(st, rows, index, prefix, title)
        return

    _render_flat_table(rows, paths, prefix)


def render_record_row(row: Any, paths: Sequence[str], key_prefix: str,
                      project: Any = None) -> None:
    """One row of a composite-bearing table, laid out like a record block.

    ``key_prefix`` carries the row index into every widget key: one registry
    path is N widgets across N rows, and Streamlit needs each of them named.
    """
    scalars = [p for p in paths if not is_composite(fr.field_type(p))]
    composites = [p for p in paths if is_composite(fr.field_type(p))]
    for start in range(0, len(scalars), _COLUMNS):
        columns = st.columns(_COLUMNS)
        for column, path in zip(columns, scalars[start:start + _COLUMNS]):
            render_scalar(row, path, key=f"{key_prefix}.{_leaf(path)}", container=column,
                          project=project)
    for path in composites:
        render_field(row, path, key=f"{key_prefix}.{_leaf(path)}", project=project)


def _row_title(row: Any, paths: Sequence[str], key_prefix: str) -> str:
    """The row's name for its expander title, read from the widget state first.

    The title is emitted before the name widget inside the expander runs, but on
    the rerun that carries the edit Streamlit already holds the typed value
    under the widget's key -- so the title says what the user just typed
    instead of lagging one keystroke behind (#64, PB-4).
    """
    for path in paths:
        if _leaf(path) == "name":
            typed = st.session_state.get(widget_key(f"{key_prefix}.name"))
            name = typed if isinstance(typed, str) else getattr(row, "name", "")
            return str(name or "(unnamed)")
    return type(row).__name__


def _render_flat_table(rows: List[Any], paths: Sequence[str], prefix: str) -> None:
    """Scalar-only rows as one ``st.data_editor``, converted at both edges."""
    system = active_system()
    units = {p: field_unit(_leaf(p)) for p in paths}
    headers = {
        p: f"{_field_label(p)} ({_unit_label(units[p], system)})".replace(" ()", "")
        for p in paths
    }
    # Stable per page visit (C210-4, _FRAME_CACHE_KEY). Row count IS in the
    # cache key here: these tables are sized by the count widget outside the
    # grid, so a count change must rebuild the frame (from the model, which
    # holds every persisted edit) while cell edits must not.
    frame = _stable_frame(
        f"{widget_key(prefix)}|{system.value}|{len(rows)}",
        lambda: pd.DataFrame([
            {headers[p]: _cell_out(getattr(row, _leaf(p)), units[p]) for p in paths}
            for row in rows
        ], columns=[headers[p] for p in paths]),
    )
    edited = st.data_editor(
        frame, key=widget_key(prefix), width="stretch", column_config={
            headers[p]: _column_config(p, headers[p]) for p in paths
        },
    )
    kept: List[str] = []
    with st.expander("\U0001f5d1 Remove a row", expanded=False):
        # A grid cannot carry a per-row button, so the flat shape picks the row
        # by name and deletes it here; the expander shape puts the same control
        # inside each row (#72, PB-23). Both go through :func:`_delete_row`.
        # ``_``-prefixed like the shell's own widgets: this picker holds no
        # project value, so the round-trip journey must not try to type it.
        # The labels are read **once**, here, and the picker formats from that
        # list: a ``format_func`` that reaches back into the live rows is
        # re-evaluated later against a list that has since moved, and then it
        # cannot find its own option (the round-trip journey does exactly that).
        titles = [f"{i + 1} · {_row_title(row, paths, f'{prefix}.{i}')}"
                  for i, row in enumerate(rows)]
        chosen = st.selectbox(
            "Row", list(range(len(rows))), key=widget_key(f"_delete_choice.{prefix}"),
            format_func=lambda i: titles[i] if i < len(titles) else str(i + 1))
        _delete_button(st, rows, int(chosen), prefix, titles[int(chosen)])

    for row, (_index, edited_row) in zip(rows, edited.iterrows()):
        for path in paths:
            if (_cell_in(row, path, edited_row[headers[path]], units[path])
                    and headers[path] not in kept):
                kept.append(headers[path])
    # Clearing a required cell restores the old value, which it must -- ``None``
    # is not one of that field's values -- but it used to do it in silence: the
    # number reappeared in the cell with nothing to say why, reading as a grid
    # that had eaten the edit (#72, PB-23). The sibling rule for a *row* with an
    # empty cell is stated by ``render_curve``; this is the cell rule.
    if kept:
        st.caption(
            f"{', '.join(kept)} cannot be empty — the previous value was kept. "
            "Type a new one to change it, or delete the row below to remove it.")


def _column_config(path: str, header: str) -> Any:
    enum = _enum_of(fr.field_type(path))
    if enum is not None:
        return st.column_config.SelectboxColumn(
            header, options=[m.value for m in enum], help=_help(path))
    inner, _ = _unwrap_optional(fr.field_type(path))
    if inner in (float, int):
        # An explicit NumberColumn, not the inferred generic cell: the generic
        # number editor refused a typed minus sign (C210 build review
        # 2026-08-23 -- "-25" landed as "25", silently, on a station column).
        return st.column_config.NumberColumn(header, help=_help(path))
    return st.column_config.Column(header, help=_help(path))


def _cell_out(value: Any, unit: FieldUnit) -> Any:
    if isinstance(value, Enum):
        return value.value
    return _to_display(value, unit)


def _cell_in(row: Any, path: str, value: Any, unit: FieldUnit) -> bool:
    """Write one edited cell back to its row; report a *required* cell kept.

    An emptied cell clears an Optional column and is refused by a required one
    -- the return value says which happened, so the grid can state the refusal
    instead of just putting the old number back (#72, PB-23).
    """
    name = _leaf(path)
    hint = fr.field_type(path)
    inner, optional = _unwrap_optional(hint)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        _persist(row, name, None if optional else getattr(row, name))
        return not optional and getattr(row, name, None) is not None
    # Past the NaN guard the cell held a concrete value, so it is a real entry
    # even when falsy -- a typed 0 into an unfilled Optional column must land,
    # which _persist's absent-stays-absent clause would drop (#35, CR-A-3).
    enum = _enum_of(inner)
    if enum is not None:
        _set_entered(row, name, enum(value))
    elif inner is bool:
        _set_entered(row, name, bool(value))
    elif inner is str:
        _set_entered(row, name, str(value))
    elif inner is int:
        _set_entered(row, name, int(value))
    else:
        _set_entered(row, name, float(_to_imperial_kept(value, unit, getattr(row, name, None))))
    return False


# --------------------------------------------------------------------------- #
# The page
# --------------------------------------------------------------------------- #
def page_groups(key: str) -> List[Tuple[str, List[str]]]:
    """``[(record prefix, [field paths])]`` for one oracle page, in registry order.

    The whole page definition: no hand-written list of what a page shows, and no
    field on a page the registry does not put there.
    """
    keep = fr.oracle_input_paths()
    groups: Dict[str, List[str]] = {}
    for row in fr.REGISTRY:
        if row.page != key or row.path not in keep:
            continue
        groups.setdefault(fr.record_of(row.path), []).append(row.path)
    return list(groups.items())


def _page_has_grid(groups: Sequence[Tuple[str, Sequence[str]]]) -> bool:
    """True when any group renders a ``st.data_editor`` grid: a list record
    (flat table or expander rows, which may hold curve grids) or a curve field
    on a plain record."""
    for prefix, paths in groups:
        if prefix.endswith(fr.LIST_MARKER):
            return True
        for p in paths:
            element = _list_element(fr.field_type(p))
            if element is not None and not (
                    isinstance(element, type) and issubclass(element, Enum)):
                return True
    return False


def render_step(key: str) -> None:
    """Render the oracle GUI page for workflow step ``key``."""
    _PENDING.clear()
    _reset_frame_cache(key)
    step = wf.BY_KEY[key]
    # ``switch_action=False``: an out-of-band airplane is still told its results
    # are an extrapolation, but concept mode is not this GUI's to enter (OG-1) --
    # the button wrote ``speeds.category="C"`` and seeded the concept load
    # factors from a GUI that shows neither (CR-A-4).
    ctx = page_header(key, caption=_step_caption(step), switch_action=False)

    # A page for a condition this airplane cannot have collects nothing. 23.367 on
    # a single or centreline engine has no yaw forcing at all, and the page used to
    # take a full simulation's inputs and then print zero tail load, zero yaw rate
    # and "NOT recovered ... uncontrollable" -- a verdict about an airplane that has
    # no engine-out case (#84, C210-43). Said and withheld here, one step earlier
    # than the #66/PB-7 results withhold: there is no input to take, not merely
    # nothing to show. Keyed by a table so the next such condition is data.
    reason = step_not_applicable(key, ctx.project)
    if reason:
        st.info(reason)
        return

    groups = page_groups(key)

    if not groups:
        st.info(
            f"**{step.title}** takes no input of its own — "
            f"{step.bas or 'it'} reads what the pages before it produced "
            f"({', '.join(step.requires) or 'nothing'})."
        )
    else:
        if _page_has_grid(groups):
            # Everything a grid on this page will do with a keystroke, said
            # once above the first one.
            #
            # How a cell commits is Streamlit's behaviour, not ours, and is
            # owned by the shell so both GUIs can say it identically
            # (:data:`~app_shell.components.GRID_COMMIT_NOTE`, #77). It was
            # said here until 2026-08-23 and then withdrawn as fixed: Enter
            # dropping an entry was *also* a symptom of C210-4, the remount
            # race that was ours, and when _stable_frame closed that race the
            # warning went out with it. The two presented identically and only
            # one of them was fixed.
            st.caption(GRID_COMMIT_NOTE)
            # Asked for by the owner mid-build (C210 review 2026-08-23): a
            # part-filled row is deliberately held out of the project, which is
            # invisible until it vanishes on a rerun.
            # Both halves, because the first one alone was read as a promise the
            # page does not keep: a *grid* row with an empty cell is held out,
            # but a row created with the row counter is part of the project the
            # moment it appears -- blank, saved, and (a zero-weight CG case) able
            # to stop a downstream page from running at all.
            st.caption(
                "Grid rows with an empty cell are not saved — fill every column "
                "to keep the row. A row added with a **row counter** is part of "
                "the project as soon as it appears, blank or not: fill it in, or "
                "count back down and delete it."
            )
        for prefix, paths in groups:
            st.subheader(pretty(prefix.rstrip(fr.LIST_MARKER).rsplit(".", 1)[-1] or "Project"))
            # The caption is the schema path, as code. The root group has no
            # path, so it says what it is instead of rendering ``(project)`` in
            # backticks -- which reads as a path, and there is no such path
            # (PB-22).
            st.caption(f"`{prefix}`" if prefix
                       else "Fields held on the project itself, not in a slice")
            if prefix.endswith(fr.LIST_MARKER):
                render_table(ctx.project, prefix, paths)
            else:
                render_record(ctx.project, prefix, paths)
            st.divider()

    # Records the widgets were given are attached only now, and only if the pass
    # put something in them (OG-F): visiting a page must not dirty a project.
    commit_pending()
    # ...and the slices the inputs derive (``Project.mass`` from the items) are
    # brought up to date by their one owner (#62, PB-1). Idempotent by value, so
    # a visit still dirties nothing; this GUI has no Apply for the user to miss.
    refresh_derived(ctx.project)

    # Names the calc keys on must be unique and present, or the numbers below
    # would be the wrong airplane's (two CG cases with one name collapse to
    # one; #63, PB-5). Said here, and the results withheld, rather than
    # discovered in a changed TAILDIST table.
    problems = duplicate_selectors(ctx.project)
    # Likewise an engine layout that disagrees with the engine count: accepted
    # in-session (two widgets, either order), it used to save a file the loader
    # refused (#66, PB-7). The rule is the model's; it is said on every page
    # because the file it would write is every page's.
    layout_problem = ctx.project.engine_layout_problem()
    if layout_problem:
        # Both owning pages resolved from the registry, so the message follows
        # any re-tag -- since C210-44 (#99) the layout is entered on Geometry
        # while the engine rows stay on Engine Mount Loads, so the two are
        # named separately.
        layout_page = wf.BY_KEY[fr.entry("engine_layout").page].title
        engines_page = wf.BY_KEY[fr.entry("engines[].engine_designation").page].title
        where = (f"the {layout_page} page" if layout_page == engines_page
                 else f"the {layout_page} (layout) and {engines_page} (engine rows) pages")
        problems.append(f"{layout_problem} -- set the engine layout and the engine "
                        f"rows to agree on {where}.")
    if problems:
        for problem in problems:
            st.error(problem)
        st.info("Results are withheld until the inputs above agree.")
        return

    # A page that takes no input still runs its programs -- Tail Loads reads
    # entirely upstream and is all output (OG-E).
    render_results(ctx.project, key, ctx.system)


def _step_caption(step: wf.WorkflowStep) -> str:
    programs = step.bas or "—"
    return f"{programs} · {step.summary}"


__all__ = [
    "MEMBER_LABELS", "blank", "commit_pending", "is_composite", "page_groups", "record_at",
    "render_field", "render_record", "render_scalar", "render_step",
    "render_table", "row_class", "rows_at", "seeded",
]
