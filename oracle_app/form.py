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
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from app_shell.components import active_system, page_header, unit_number_input
from oracle_app.labels import pretty
from oracle_app.results import render_results
from sloads import field_registry as fr
from sloads import workflow as wf
from sloads.models import Project
from sloads.units import FieldUnit, field_unit, to_display, to_imperial_scalar
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


def _field_label(path: str) -> str:
    leaf = _leaf(path)
    for suffix, unit in _UNIT_SUFFIX.items():
        if leaf.endswith(suffix) and len(leaf) > len(suffix):
            stem = pretty(leaf[: -len(suffix)])
            return f"{stem} ({unit})" if unit else stem
    return pretty(leaf)


def _leaf(path: str) -> str:
    return path.rsplit(".", 1)[-1].replace(fr.LIST_MARKER, "")


def _help(path: str) -> Optional[str]:
    """A field's provenance, from its registry row."""
    row = fr.entry(path)
    return f"`{path}` — {row.basis}" if row else None


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
#: :func:`commit_pending` only if the pass left something in it. Reset at the
#: top of :func:`render_step`, which is the only entry point; module state
#: rather than a threaded argument because Streamlit runs one script at a time
#: and every reader is in this file.
_PENDING: List[Tuple[Any, str, Any]] = []


def _persist(record: Any, name: str, value: Any) -> None:
    """Write ``value`` only if it differs from what is already there.

    A render pass must not mutate the project (``tests/test_dirty_flag.py``,
    M2-3), and the naive ``setattr`` on every rerun broke that twice over: it
    re-wrote every field of every visited page, and it rewrote ``45`` as
    ``45.0`` because a widget returns a float where the JSON held an int --
    the same number, a different file, an "Unsaved changes" flag the user
    never earned. Equality settles both (``45 == 45.0``). The second clause
    keeps an *absent* field absent: a ``None`` rendered as the type's empty
    value is still unfilled, and only a real entry makes it real.
    """
    current = getattr(record, name, None)
    if current == value or (current is None and not value):
        return
    setattr(record, name, value)


def _is_blank(value: Any) -> bool:
    """True if ``value`` is an untouched record (or an empty list of them)."""
    if isinstance(value, list):
        return not value
    return value == blank(type(value))


def commit_pending() -> None:
    """Attach the records this pass created, if the pass put something in them.

    A chain is attached whole or not at all: filling ``geometry.parametric`` on
    a project with no ``geometry`` must attach both, and touching neither must
    leave the project exactly as it was found.
    """
    needed = set()
    for owner, _, value in reversed(_PENDING):
        if id(value) in needed or not _is_blank(value):
            needed.add(id(value))
            needed.add(id(owner))
    for owner, name, value in _PENDING:
        if id(value) in needed:
            setattr(owner, name, value)
    _PENDING.clear()


def record_at(project: Project, prefix: str) -> Any:
    """The record instance at ``prefix``, creating every missing step of the way.

    The oracle GUI's job on a fresh project is to *make* the slices, so a missing
    one is the normal state rather than an error: an absent ``speeds`` means the
    Structural Speeds page has not been filled in yet, not that it is unavailable.
    A record created here is **detached** until :func:`commit_pending` decides
    the page earned it -- see :data:`_PENDING`.
    """
    obj: Any = project
    for segment in [s for s in prefix.split(".") if s]:
        value = getattr(obj, segment, None)
        if value is None:
            hint = fr.field_type(_path_of(obj, segment, prefix))
            inner, _ = _unwrap_optional(hint)
            if not (isinstance(inner, type) and dataclasses.is_dataclass(inner)):
                return None
            value = blank(inner)
            _PENDING.append((obj, segment, value))
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
        rows = []
        _PENDING.append((owner, attr, rows))
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
def _number(label: str, value: float, unit: FieldUnit, key: str, **kwargs: Any) -> float:
    """A number in display units that comes back Imperial, via the shell boundary."""
    if unit.kind is not None:
        return unit_number_input(label, float(value), kind=unit.kind, key=key, **kwargs)
    if unit.fixed_label is not None:
        return unit_number_input(
            label, float(value), fixed_unit=unit.fixed_label, key=key, **kwargs)
    return unit_number_input(label, float(value), key=key, **kwargs)


def render_scalar(record: Any, path: str, *, key: str, container: Any = None) -> None:
    """One widget for one non-composite field, written straight back to ``record``.

    ``key`` is the Streamlit widget key. It is not the registry path, because a
    table row repeats every path: ``weight.items[].name`` is one registry row and
    N widgets. The caller owns uniqueness, so the field renderers never have to
    know that tables exist.
    """
    where = container if container is not None else st
    name = _leaf(path)
    hint = fr.field_type(path)
    inner, optional = _unwrap_optional(hint)
    label, help_text = _field_label(path), _help(path)
    value = getattr(record, name)

    enum = _enum_of(inner)
    if enum is not None:
        options: List[Any] = ([None] if optional else []) + list(enum)
        current = value if value in options else options[0]
        chosen = where.selectbox(
            label, options, index=options.index(current), key=key, help=help_text,
            format_func=lambda o: "—" if o is None else f"{o.value} · {pretty(o.name)}",
        )
        _persist(record, name, chosen)
        return

    if inner is bool:
        _persist(record, name, where.checkbox(label, bool(value), key=key, help=help_text))
        return

    if inner is str:
        _persist(record, name, where.text_input(label, value or "", key=key, help=help_text))
        return

    unit = field_unit(name)
    if inner is int:
        entered = where.number_input(
            f"{label} ({_unit_label(unit, active_system())})".replace(" ()", ""),
            value=int(value or 0), step=1, key=key, help=help_text)
        _persist(record, name, int(entered))
        return

    _persist(record, name, _number(
        label, value if value is not None else 0.0, unit, key,
        container=where, help=help_text, format="%.4f"))


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


def render_tuple(record: Any, path: str, *, key: str, container: Any = None) -> None:
    """A fixed-length numeric tuple as one labelled input per member."""
    where = container if container is not None else st
    name = _leaf(path)
    arity = _tuple_arity(fr.field_type(path))
    current = list(getattr(record, name) or [0.0] * arity)
    current += [0.0] * (arity - len(current))

    where.markdown(f"**{_field_label(path)}**", help=_help(path))
    columns = where.columns(arity)
    units = _member_units(path, arity)
    entered = [
        _number(member, float(current[i]), units[i], f"{key}.{i}",
                container=columns[i], format="%.4f")
        for i, member in enumerate(_members(path, arity))
    ]
    _persist(record, name, tuple(entered))


def render_curve(record: Any, path: str, *, key: str, container: Any = None) -> None:
    """A ``List[XYPoint]`` / ``List[float]`` as an editable table of its members."""
    where = container if container is not None else st
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
    edited = where.data_editor(
        pd.DataFrame(display, columns=headers), num_rows="dynamic", key=key,
        width="stretch",
    )
    # ``rows`` is what was rendered, so row ``n`` of the editor is row ``n`` of
    # the stored curve until the user adds or removes one -- and past that point
    # the value has genuinely changed, so reconstructing it is correct.
    def _stored(index: int, member: int) -> Any:
        if index >= len(rows):
            return None
        row = rows[index]
        return row[member] if arity > 1 else row

    kept = [
        [_to_imperial_kept(v, units[i], _stored(n, i)) for i, v in enumerate(values)]
        for n, values in enumerate(edited.values.tolist())
        if not any(pd.isna(v) for v in values)
    ]
    _persist(record, name, [tuple(r) if arity > 1 else r[0] for r in kept])


def render_enum_set(record: Any, path: str, *, key: str, container: Any = None) -> None:
    """A ``Set[Enum]`` as a multiselect."""
    where = container if container is not None else st
    name = _leaf(path)
    enum = _list_element(fr.field_type(path))
    assert isinstance(enum, type) and issubclass(enum, Enum)
    chosen = where.multiselect(
        _field_label(path), list(enum), default=sorted(getattr(record, name) or (),
                                                       key=lambda m: m.value),
        key=key, help=_help(path), format_func=lambda m: pretty(m.name))
    _persist(record, name, set(chosen))


def _to_display(value: Any, unit: FieldUnit) -> Any:
    if unit.kind is None or not isinstance(value, (int, float)):
        return value
    return to_display(float(value), unit.kind, active_system())


def _to_imperial(value: Any, unit: FieldUnit) -> Any:
    if unit.kind is None or not isinstance(value, (int, float)):
        return value
    return to_imperial_scalar(float(value), unit.kind, active_system())


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


def render_field(record: Any, path: str, *, key: str, container: Any = None) -> None:
    """The one entry point per field: pick the widget its annotation asks for."""
    hint = fr.field_type(path)
    element = _list_element(hint)
    if isinstance(element, type) and issubclass(element, Enum):
        render_enum_set(record, path, key=key, container=container)
    elif element is not None:
        render_curve(record, path, key=key, container=container)
    elif _tuple_arity(hint):
        render_tuple(record, path, key=key, container=container)
    else:
        render_scalar(record, path, key=key, container=container)


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
            render_scalar(record, path, key=path, container=column)
    for path in composites:
        render_field(record, path, key=path)


def render_table(project: Project, prefix: str, paths: Sequence[str]) -> None:
    """One list record. Flat rows get a data editor; rows holding a composite get
    an expander each, because a table cell cannot hold a polyline."""
    rows = rows_at(project, prefix)
    cls = row_class(prefix, paths)
    if cls is None:
        st.warning(f"`{prefix}` cannot be created on this project.")
        return

    count = st.number_input(
        f"{pretty(prefix.rstrip(fr.LIST_MARKER).rsplit('.', 1)[-1])} — rows",
        min_value=0, value=len(rows), step=1, key=f"{prefix}.count")
    while len(rows) < count:
        rows.append(blank(cls))
    while len(rows) > count:
        rows.pop()
    if not rows:
        return

    if any(is_composite(fr.field_type(p)) for p in paths):
        for index, row in enumerate(rows):
            with st.expander(f"{index + 1} · {_row_title(row, paths)}", expanded=index == 0):
                render_record_row(row, paths, f"{prefix}.{index}")
        return

    _render_flat_table(rows, paths, prefix)


def render_record_row(row: Any, paths: Sequence[str], key_prefix: str) -> None:
    """One row of a composite-bearing table, laid out like a record block.

    ``key_prefix`` carries the row index into every widget key: one registry
    path is N widgets across N rows, and Streamlit needs each of them named.
    """
    scalars = [p for p in paths if not is_composite(fr.field_type(p))]
    composites = [p for p in paths if is_composite(fr.field_type(p))]
    for start in range(0, len(scalars), _COLUMNS):
        columns = st.columns(_COLUMNS)
        for column, path in zip(columns, scalars[start:start + _COLUMNS]):
            render_scalar(row, path, key=f"{key_prefix}.{_leaf(path)}", container=column)
    for path in composites:
        render_field(row, path, key=f"{key_prefix}.{_leaf(path)}")


def _row_title(row: Any, paths: Sequence[str]) -> str:
    for path in paths:
        if _leaf(path) == "name":
            return str(getattr(row, "name", "") or "(unnamed)")
    return type(row).__name__


def _render_flat_table(rows: List[Any], paths: Sequence[str], prefix: str) -> None:
    """Scalar-only rows as one ``st.data_editor``, converted at both edges."""
    system = active_system()
    units = {p: field_unit(_leaf(p)) for p in paths}
    headers = {
        p: f"{_field_label(p)} ({_unit_label(units[p], system)})".replace(" ()", "")
        for p in paths
    }
    frame = pd.DataFrame([
        {headers[p]: _cell_out(getattr(row, _leaf(p)), units[p]) for p in paths}
        for row in rows
    ], columns=[headers[p] for p in paths])

    edited = st.data_editor(
        frame, key=prefix, width="stretch", column_config={
            headers[p]: _column_config(p, headers[p]) for p in paths
        },
    )
    for row, (_index, edited_row) in zip(rows, edited.iterrows()):
        for path in paths:
            _cell_in(row, path, edited_row[headers[path]], units[path])


def _column_config(path: str, header: str) -> Any:
    enum = _enum_of(fr.field_type(path))
    if enum is not None:
        return st.column_config.SelectboxColumn(
            header, options=[m.value for m in enum], help=_help(path))
    return st.column_config.Column(header, help=_help(path))


def _cell_out(value: Any, unit: FieldUnit) -> Any:
    if isinstance(value, Enum):
        return value.value
    return _to_display(value, unit)


def _cell_in(row: Any, path: str, value: Any, unit: FieldUnit) -> None:
    name = _leaf(path)
    hint = fr.field_type(path)
    inner, optional = _unwrap_optional(hint)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        _persist(row, name, None if optional else getattr(row, name))
        return
    enum = _enum_of(inner)
    if enum is not None:
        _persist(row, name, enum(value))
    elif inner is bool:
        _persist(row, name, bool(value))
    elif inner is str:
        _persist(row, name, str(value))
    elif inner is int:
        _persist(row, name, int(value))
    else:
        _persist(row, name, float(_to_imperial_kept(value, unit, getattr(row, name, None))))


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


def render_step(key: str) -> None:
    """Render the oracle GUI page for workflow step ``key``."""
    _PENDING.clear()
    step = wf.BY_KEY[key]
    ctx = page_header(key, caption=_step_caption(step))
    groups = page_groups(key)

    if not groups:
        st.info(
            f"**{step.title}** takes no input of its own — "
            f"{step.bas or 'it'} reads what the pages before it produced "
            f"({', '.join(step.requires) or 'nothing'})."
        )
    else:
        for prefix, paths in groups:
            st.subheader(pretty(prefix.rstrip(fr.LIST_MARKER).rsplit(".", 1)[-1] or "Project"))
            st.caption(f"`{prefix or '(project)'}`")
            if prefix.endswith(fr.LIST_MARKER):
                render_table(ctx.project, prefix, paths)
            else:
                render_record(ctx.project, prefix, paths)
            st.divider()

    # Records the widgets were given are attached only now, and only if the pass
    # put something in them (OG-F): visiting a page must not dirty a project.
    commit_pending()

    # A page that takes no input still runs its programs -- Tail Loads reads
    # entirely upstream and is all output (OG-E).
    render_results(ctx.project, key, ctx.system)


def _step_caption(step: wf.WorkflowStep) -> str:
    programs = step.bas or "—"
    return f"{programs} · {step.summary}"


__all__ = [
    "MEMBER_LABELS", "blank", "commit_pending", "is_composite", "page_groups", "record_at",
    "render_field", "render_record", "render_scalar", "render_step",
    "render_table", "row_class", "rows_at",
]
