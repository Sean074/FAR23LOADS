"""The one registry of input fields: where each is edited, and where it came from.

Design note 32 decision **OG-14** — *one registry, not two*. Two separate tables
were planned: OG-5's field-**origin** registry (is this field an input of a named
`.BAS` program, or capability sloads added?) and the 2026-08-16 GUI review's
field-**ownership** registry (GR-INPUT-2 / GR-GEOM-2 / GR-GEOM-4: which slice
owns a field, which page edits it, and is this quantity stored twice?). They
share a key — the input field path — and differ only in their value columns, so
they are built once, here.

Six columns, keyed by dotted field path:

    path │ slice │ page │ origin │ quantity │ owner-or-derived-from

``slice`` is derived from the path, never stored. The other four are declared,
and every declaration carries a ``basis`` string citing what settles it — an
origin claim with no citation is exactly the kind of assertion this project does
not accept in the calc layer, and the same rule applies here.

**What this registry is *for*, so its guards stay honest:**

* **G4 — totality.** Every input field reachable from an oracle page carries an
  origin. :func:`schema_paths` walks ``Project`` from its dataclass types (not
  from an example project, whose ``None`` slices would hide fields), so adding a
  field to ``models/inputs.py`` fails the guard until it is classified here.
  That is the point: the classification is a decision, and a new field must not
  inherit one by default.
* **G5 — the reduced input set is real.** With only ``origin=ORIGINAL`` fields
  populated, every oracle-page module still runs and every Appendix A oracle
  still passes. Until that gate exists the "oracle GUI asks less" claim is an
  assertion; :func:`original_paths` is what it runs against.
* **The duplicate-owner class** (the review's five instances, `CLAUDE.md` rule
  4). ``quantity`` names the *physical* quantity a field holds, so two fields
  holding one quantity are visible; ``derived_from`` names the owner for the
  copies. One owner per quantity, and every copy names its sync — two assertions
  over one table, replacing five independent defect reports.

Guard: ``tests/test_field_registry.py``. Consumer: ``docs/generate_data_dict.py``
takes the per-field editing page from here rather than keeping its own
slice-level override table.
"""

from __future__ import annotations

import copy
import dataclasses
import typing
from enum import Enum
from typing import Dict, List, Mapping, Optional, Set, Tuple

from sloads import models as _models
from sloads.derived import refresh_derived
from sloads.models import Project

# --------------------------------------------------------------------------- #
# The schema walk
# --------------------------------------------------------------------------- #
#: Namespace for ``get_type_hints``: ``models`` re-exports its dataclasses but
#: the annotations also name bare ``typing`` generics, which are not in it.
_HINT_NS: Dict[str, object] = dict(vars(_models))
_HINT_NS.update({
    name: getattr(typing, name)
    for name in ("List", "Dict", "Optional", "Tuple", "Any", "Union", "Sequence",
                 "Set", "Iterable", "Mapping")
})

#: `Project` attributes that are **not** input fields, each with the reason.
#: Result slices are computed outputs; the rest are document metadata or a
#: preference, none of which an origin classification is meaningful for.
#:
#: The three result slices are what :func:`reduce_to_oracle_inputs` drops
#: outright (review 2026-08-22 PB-3 -- before that the reduction never looked
#: at them, so a stored ``mass`` carried every gate while the oracle GUI wrote
#: none) and :mod:`sloads.derived` then rebuilds the ones the inputs derive.
RESULT_SLICES: Tuple[str, ...] = ("envelope", "mass", "loads")

NON_INPUT: Dict[str, str] = {
    "envelope": "result slice (WTENV output)",
    "mass": "result slice (WTONECG output; derived from weight.items, sloads.derived)",
    "loads": "result slice (per-module load cases)",
    "schema_version": "set by io.py, never by a user",
    "unit_system": "display preference, not airplane data (D-22)",
    "safety_factors": "governing SF table view, owned by sloads/safety_factors.py",
    "name": "document metadata",
    "engineer": "document metadata",
    "date": "document metadata",
    "revision": "document metadata",
    "checked_by": "document metadata",
    "approved_by": "document metadata",
    "description": "document metadata",
}

#: Marks a list-of-dataclass hop in a path: ``engines[].engine_weight_lb``.
LIST_MARKER = "[]"

#: ``str`` fields that carry a **code**, and the table of codes each accepts
#: (owned by ``models/inputs.py`` beside the field). The oracle form offers
#: these as a choice rather than free text, and every consumer normalises
#: through ``models.normalise_code`` (#63, PB-8). Guarded in
#: ``tests/test_selectors.py``: each path is a registered ``str`` field.
CODED_FIELDS: Dict[str, Mapping[str, str]] = {
    "speeds.category": _models.CATEGORIES,
    "geometry.landing_gear.main_gear.strut": _models.STRUT_TYPES,
    "geometry.landing_gear.nose_gear.strut": _models.STRUT_TYPES,
}

#: Fixed-vocabulary **row selectors** (#98, C210-46): ``str`` fields on list
#: records that pick which surface a row belongs to, offered as a choice like
#: :data:`CODED_FIELDS` -- but the values are surface *names*, stored lowercase
#: and refused by name by the consumers (``models.inputs.require_surface``),
#: not codes. The vocabularies are owned in ``models/inputs.py`` beside the
#: dataclasses; guarded in ``tests/test_selectors.py``.
ROW_SELECTOR_CHOICES: Dict[str, Tuple[str, ...]] = {
    "tab_loads.tabs[].surface": _models.TAB_SURFACES,
    "tail_mass[].surface": _models.TAIL_SURFACES,
}

#: Fields whose **declared default is a sentinel, not a value** (#98, C210-49):
#: the consumers refuse, assume-with-a-note or leave the free body open on the
#: default rather than compute with it, so "leave it at its default" -- the
#: whole basis of the OG-2/OG-5 reduction -- is not available for them. Each
#: entry cites the consumer that says so. The guard
#: ``tests/test_field_registry.py::test_a_sentinel_default_field_is_always_asked``
#: fails the build if one of these is ever filtered off its oracle page, which
#: is exactly how the gear block shipped hidden: an oracle-built project could
#: not export ground cases and the page did not say so.
SENTINEL_DEFAULTS: Dict[str, str] = {
    "geometry.landing_gear.main_gear.carrier":
        "None = not stated; export/lra_model.py assumes with a note and "
        "validation.py warns gear_carrier_unset (G-2)",
    "geometry.landing_gear.nose_gear.carrier":
        "None = not stated; export/lra_model.py assumes with a note and "
        "validation.py warns gear_carrier_unset (G-2)",
    "geometry.landing_gear.main_gear.attach":
        "(0,0,0) = not entered; export/lra_model.py omits the leg's node -- "
        "no ground case is deliverable (Step 10)",
    "geometry.landing_gear.nose_gear.attach":
        "(0,0,0) = not entered; export/lra_model.py omits the leg's node -- "
        "no ground case is deliverable (Step 10)",
    "geometry.landing_gear.main_gear.weight_lb":
        "0 = not stated; gear_loads.leg_weight returns None and the report "
        "prints the inertia term blank (G-12a)",
    "geometry.landing_gear.nose_gear.weight_lb":
        "0 = not stated; gear_loads.leg_weight returns None and the report "
        "prints the inertia term blank (G-12a)",
}

#: ``Project`` attributes that are read-through **properties**, not stored
#: slices, mapped to the path their fields actually live at. ``workflow.py``
#: names them in ``requires`` (a step needs the rational h-tail inputs), and
#: ``DATA_DICTIONARY.md`` lists them as slices, so anything reasoning from a
#: slice name to a field path has to resolve them or conclude — wrongly — that
#: the fields are missing. Guarded in ``tests/test_field_registry.py``.
SLICE_ALIASES: Dict[str, str] = {
    "tail_loads": "geometry.empennage.htail",
    "vtail_loads": "geometry.empennage.vtail",
}


def resolve_slice(name: str) -> str:
    """A ``requires``/slice name as a field-path prefix, following aliases."""
    return SLICE_ALIASES.get(name, name)


def paths_under(name: str) -> Set[str]:
    """Registry paths belonging to a slice name (alias-aware)."""
    prefix = resolve_slice(name)
    return {
        e.path for e in REGISTRY
        if e.path == prefix or e.path.startswith(prefix + ".")
        or e.path.startswith(prefix + LIST_MARKER + ".")
    }


def _dataclasses_in(annotation) -> List[type]:
    """Every dataclass reachable through an annotation (unwrapping Optional/List)."""
    found: List[type] = []

    def walk(ann) -> None:
        if dataclasses.is_dataclass(ann) and isinstance(ann, type):
            found.append(ann)
        for arg in typing.get_args(ann):
            walk(arg)

    walk(annotation)
    return found


def _is_list_of(annotation, cls: type, in_list: bool = False) -> bool:
    """True when ``cls`` is reached through a List/Tuple, not held directly.

    Decides whether a path segment gets the ``[]`` marker: ``engines[].prop_cg``
    is one row standing for every engine, while ``speeds.mach_limit.*`` is a
    single nested object.
    """
    if annotation is cls:
        return in_list
    inside = in_list or typing.get_origin(annotation) in (list, tuple)
    return any(_is_list_of(arg, cls, inside) for arg in typing.get_args(annotation))


def _hints(cls: type) -> Dict[str, object]:
    try:
        return typing.get_type_hints(cls, _HINT_NS)
    except Exception:  # pragma: no cover - a forward ref we cannot resolve
        return {f.name: f.type for f in dataclasses.fields(cls)}


def _walk(cls: type, prefix: str, stack: Tuple[str, ...]) -> List[str]:
    """Leaf field paths under ``cls``, recursing into nested dataclasses.

    ``stack`` carries the dataclass names already open on this branch, so a
    self-referential model (a section holding sections) terminates at the
    revisit instead of recursing forever; the revisit itself is emitted as a
    leaf, because that is where the user's data stops being distinguishable.
    """
    out: List[str] = []
    hints = _hints(cls)
    for field in dataclasses.fields(cls):
        annotation = hints.get(field.name, field.type)
        path = prefix + field.name
        nested = [c for c in _dataclasses_in(annotation) if c.__name__ not in stack]
        if not nested:
            out.append(path)
            continue
        for child in nested:
            marker = LIST_MARKER + "." if _is_list_of(annotation, child) else "."
            out.extend(_walk(child, path + marker, stack + (child.__name__,)))
    return out


def schema_paths() -> Set[str]:
    """Every input field path on ``Project``, from the dataclass types.

    Type-based on purpose: walking an example project would silently omit every
    field under a slice that example leaves ``None``, so the totality gate would
    pass while ignoring whole subtrees.
    """
    paths: Set[str] = set()
    hints = _hints(Project)
    for field in dataclasses.fields(Project):
        if field.name in NON_INPUT:
            continue
        annotation = hints.get(field.name, field.type)
        nested = _dataclasses_in(annotation)
        if not nested:
            paths.add(field.name)
            continue
        for child in nested:
            marker = LIST_MARKER + "." if _is_list_of(annotation, child) else "."
            paths.update(_walk(child, field.name + marker, (child.__name__,)))
    return paths


def slice_of(path: str) -> str:
    """The ``Project`` slice a field path belongs to (its first segment)."""
    return path.split(".", 1)[0].split(LIST_MARKER, 1)[0]


def _locate(path: str) -> Optional[Tuple[type, "dataclasses.Field"]]:
    """The owning dataclass and ``dataclasses.Field`` a registry path names.

    The inverse of the walk :func:`schema_paths` does. The owner comes back with
    the field because a field's *type* can only be resolved against the class
    that declares it (``from __future__ import annotations`` makes
    ``Field.type`` a string), and both callers below need one or the other.
    """
    cls: object = Project
    segments = path.split(".")
    for i, segment in enumerate(segments):
        name = segment[: -len(LIST_MARKER)] if segment.endswith(LIST_MARKER) else segment
        if not dataclasses.is_dataclass(cls):
            return None
        found = {f.name: f for f in dataclasses.fields(cls)}.get(name)
        if found is None:
            return None
        if i == len(segments) - 1:
            return cls, found  # type: ignore[return-value]
        rest = ".".join(segments[i + 1:])
        for child in _dataclasses_in(_hints(cls).get(name, found.type)):  # type: ignore[arg-type]
            if any(f.name == rest.split(".", 1)[0].split(LIST_MARKER, 1)[0]
                   for f in dataclasses.fields(child)):
                cls = child
                break
        else:
            return None
    return None


def field_at(path: str) -> Optional["dataclasses.Field"]:
    """The ``dataclasses.Field`` a registry path names, or ``None``.

    Used to read a field's *declared default* — the one property of a field that
    decides whether the oracle GUI is able to omit it at all
    (:func:`structurally_required`).
    """
    located = _locate(path)
    return None if located is None else located[1]


def field_type(path: str) -> Optional[object]:
    """The **resolved** annotation of the field a registry path names.

    ``field_at(path).type`` is a *string* under ``from __future__ import
    annotations``, which is enough to read a default off but not enough to
    decide what widget a field needs. This resolves it against the same
    namespace the schema walk uses, so a caller gets ``Optional[float]`` or
    ``List[XYPoint]`` as a type object rather than as text to parse — which is
    what the oracle GUI's generic renderer builds every widget from (design
    note 32, OG-D).
    """
    located = _locate(path)
    if located is None:
        return None
    owner, field = located
    return _hints(owner).get(field.name, field.type)


# --------------------------------------------------------------------------- #
# The registry
# --------------------------------------------------------------------------- #
class Origin(Enum):
    """Which world a field belongs to (OG-5).

    ``ORIGINAL`` means the field is an input of a named ``.BAS`` program — the
    oracle GUI must offer it, because the original asked for it. ``SLOADS``
    means capability this replication added; the oracle GUI omits it and the
    field keeps its default, which is what makes the reduced input set real
    rather than cosmetic (gate G5).
    """

    ORIGINAL = "original"
    SLOADS = "sloads"


@dataclasses.dataclass(frozen=True)
class FieldEntry:
    """One input field's registry row."""

    path: str
    #: `sloads.workflow` step key of the page that edits this field.
    page: str
    origin: Origin
    #: What settles ``origin`` — a `.BAS` program name, a User's Guide section,
    #: an Appendix A echo print, or the sloads step/decision that added the
    #: field. Never empty: an unsourced classification is not a classification.
    basis: str
    #: The physical quantity held, when more than one field holds it. Empty
    #: means the field is the sole holder of its own quantity (the normal case).
    quantity: str = ""
    #: Where ``quantity`` really lives when this row is a copy — either a
    #: registry path (optionally followed by a parenthesised note on how the
    #: copy is kept in step) or :data:`EXTERNAL` + a description, for a quantity
    #: whose owner is not a single field: a list length, the weight database, a
    #: value derived from the planform. Empty means this row is the owner.
    derived_from: str = ""
    #: For a copy (``derived_from`` set): does the calc **honour** this copy, or
    #: does the owner's value govern regardless of what is stored here? (#36,
    #: CR-A-2.) The two render differently and the difference is not cosmetic:
    #:
    #: * ``True`` — an **override**. Some module reads this field verbatim, so a
    #:   value entered here takes effect and may legitimately differ from the
    #:   owner. It stays editable and is marked with the owner and its value;
    #:   disabling it would remove a capability, and silently substituting the
    #:   owner's value would change results.
    #: * ``False`` — **display-only**. The consumer resolves the owner instead
    #:   (typically from geometry), so anything entered here is ignored. It
    #:   renders disabled, showing the value that actually governs — which is the
    #:   whole wrong-belief defect this flag exists to end.
    #:
    #: Meaningless on an owner row, and asserted so by the registry guards.
    governs: bool = False
    #: How this copy resolves against its owner, in the user's words — used
    #: verbatim as the GUI's caption where the ``governs`` sentence would be
    #: wrong. Only a *conditionally* governing copy needs it: the weight
    #: estimate's horsepower is ignored in favour of the engine sum **unless**
    #: the override switch beside it is set, and neither plain sentence says
    #: that (#69). Empty everywhere else, where ``governs`` says it all.
    resolves: str = ""
    #: ``origin`` is ``SLOADS``, but the oracle input set needs the field anyway
    #: -- see :data:`SUPPLIED_RULE`. ``origin`` says who *asked* for a field;
    #: this says the oracle GUI cannot do without it, and the two differ exactly
    #: where this model carries as data something the original carried by
    #: position (which surface a planform describes, which of LANDLOAD's three
    #: loadings a CG case is). The oracle GUI's input set is therefore
    #: ``ORIGINAL | supplied`` (:func:`oracle_input_paths`), which is what gate
    #: G5 runs against.
    #:
    #: **Not "written without asking"**, which is what this said until #74: every
    #: supplied path is a rendered widget the user can see and change. Some are
    #: *seeded* with a meaningful default rather than left empty (``seed_name``
    #: on a surface, a CG case's role), which is where that reading came from --
    #: but seeding a field the user then edits is not writing it behind their
    #: back, and a mark that claimed otherwise invited a GUI that hid them.
    supplied: bool = False

    @property
    def slice(self) -> str:
        return slice_of(self.path)

    @property
    def is_owner(self) -> bool:
        return not self.derived_from

    @property
    def owner_path(self) -> str:
        """The registry path this row copies, or "" for an owner/external row."""
        if not self.derived_from or self.derived_from.startswith(EXTERNAL):
            return ""
        return self.derived_from.split(" (", 1)[0].strip()

    @property
    def owner_is_external(self) -> bool:
        return self.derived_from.startswith(EXTERNAL)

    @property
    def external_owner(self) -> str:
        """Where an external owner lives, in one phrase, or "" for a field owner.

        Split exactly as :attr:`owner_path` splits a field owner: the phrase up
        to the first " (", the parenthesis being the row's provenance note
        (which decision, which review instance) and not something to show a
        user. It is the phrase the GUI's mark names (#69), so it has to read as
        a place -- "the weight database", ``len(Project.engines)`` -- rather
        than as a citation.
        """
        if not self.owner_is_external:
            return ""
        return self.derived_from[len(EXTERNAL):].split(" (", 1)[0].strip()

    @property
    def display_only(self) -> bool:
        """A copy the consumer never reads: it renders disabled, showing the owner.

        The form's rule (``oracle_app.form._copy_note``) and the G5 journey's
        (a field no widget can write is not compared) are the one rule, here.

        An **external** owner qualifies only when its governing value can be
        resolved (:data:`EXTERNAL_VALUES`, #70). Without a number there is
        nothing to substitute into the widget, and one of these rows -- the
        weight estimate's horsepower -- is the fallback the analysis uses when
        its owner is empty; disabling it would make that fallback unenterable.
        """
        if not self.governs and self.owner_is_external:
            return self.path in EXTERNAL_VALUES
        return bool(self.owner_path) and not self.governs


#: ``derived_from`` prefix for a quantity owned outside the input-field set.
#: Several of the review's duplicate instances are this shape — the owner of
#: "engine count" is ``len(Project.engines)``, of "engine mass" the weight
#: database — so the registry has to be able to say *owned, but not by a field*
#: rather than either inventing an owner row or dropping the duplicate from view.
EXTERNAL = "external: "


def _speeds_wing_area(project: Project, _record: object = None) -> Optional[float]:
    """The planform area STRSPEED resolves for ``speeds.wing_area_sqft``."""
    from sloads.derived_geometry import planform_area_sqft

    surface = getattr(getattr(project, "speeds", None), "wing_surface", None) or "wing"
    try:
        return planform_area_sqft(project, surface)
    except ValueError:
        # A half-entered planform. Narrowed from (ValueError, ZeroDivisionError,
        # StopIteration) when #71 gave every planform sweep one precondition and
        # a named refusal -- the broad catch was there because the calc could
        # still divide by zero, and it no longer can. A mark must not be the
        # thing that takes the page down, so it answers "no governing value yet"
        # and the widget stays live.
        return None


#: ``{path: resolver}`` for the copies whose owner is an expression rather than a
#: field, but whose governing value can still be computed and shown (#70, PB-17).
#:
#: :attr:`FieldEntry.owner_path` is a dotted path the GUI reads with ``getattr``;
#: an external owner has none, so before #70 such a row could only be captioned,
#: never valued -- and the one row that *did* show a number was pointed at a
#: neighbouring field with a different value. A resolver here is the same
#: function the calc calls, so the two cannot drift; a row with no resolver stays
#: caption-only and editable. Guarded by
#: ``tests/test_field_registry.py::test_every_external_resolver_names_a_registry_row``.
def _mtow(project: Project, _record: object = None) -> Optional[float]:
    from sloads.cg_cases import max_takeoff_weight

    return max_takeoff_weight(project, required=False) or None


def _wing_ref_value(attr: str):
    def resolver(project: Project, _record: object = None) -> Optional[float]:
        from sloads.derived_geometry import wing_reference

        ref = wing_reference(project)
        return None if ref is None else getattr(ref, attr)
    return resolver


def _fuselage_bound(pick) -> "typing.Callable[..., Optional[float]]":
    def resolver(project: Project, _record: object = None) -> Optional[float]:
        fus = project.geometry.fuselage if project.geometry is not None else None
        if fus is None or not fus.sections:
            return None
        return pick([s.x for s in fus.sections])
    return resolver


def _clmax(attr: str):
    def resolver(project: Project, _record: object = None) -> Optional[float]:
        aero = project.aero_coeffs
        return (getattr(aero, attr) or None) if aero is not None else None
    return resolver


def _paired_surface(project: Project, record: object):
    name = getattr(record, "name", "") if record is not None else ""
    geom = project.geometry
    return geom.by_name(name) if geom is not None and name else None


def _planform_taper(project: Project, record: object = None) -> Optional[float]:
    from sloads.derived_geometry import taper_ratio_from_planform

    surf = _paired_surface(project, record)
    return None if surf is None else taper_ratio_from_planform(surf)


def _planform_tip(project: Project, record: object = None) -> Optional[float]:
    from sloads.derived_geometry import tip_ratio_from_planform

    surf = _paired_surface(project, record)
    return None if surf is None else tip_ratio_from_planform(surf)


def _wing_ar(project: Project, _record: object = None) -> Optional[float]:
    from sloads.derived_geometry import wing_aspect_ratio

    return wing_aspect_ratio(project)


def _wing_lift_slope(project: Project, _record: object = None) -> Optional[float]:
    from sloads.modules.select import wing_lift_slope_per_rad

    return wing_lift_slope_per_rad(project)


def _aileron_down(project: Project, _record: object = None) -> Optional[float]:
    ail = project.aileron_loads
    return (ail.down_deflection_deg or None) if ail is not None else None


def _gust_at_vf(project: Project, _record: object = None) -> Optional[float]:
    from sloads.modules.flight_envelope import gust_at_vf

    return gust_at_vf(project)


def _limnz(project: Project, _record: object = None) -> Optional[float]:
    from sloads.models import MissingInputError
    from sloads.modules.structural_speeds import design_speed_values

    if project.speeds is None:
        return None
    try:
        return design_speed_values(project, project.speeds).n or None
    except (MissingInputError, ValueError):
        return None


def _fuselage_length(project: Project, _record: object = None) -> Optional[float]:
    """The outline's own length -- what ``sync_geometry_derived`` overwrites the
    ``fuselage_length`` scalar with on every run (#95, C210-2)."""
    from sloads.derived_geometry import fuselage_summary

    fus = project.geometry.fuselage if project.geometry is not None else None
    if fus is None:
        return None
    summary = fuselage_summary(fus)
    return summary[0] if summary else None


def _elevator_area(project: Project, _record: object = None) -> Optional[float]:
    ti = project.tail_loads
    if ti is None:
        return None
    total = ti.elevator_fwd_hinge_sqft + ti.elevator_aft_hinge_sqft
    return total or None


def _rudder_area(project: Project, _record: object = None) -> Optional[float]:
    vt = project.vtail_loads
    if vt is None:
        return None
    total = vt.rudder_fwd_hinge_sqft + vt.rudder_aft_hinge_sqft
    return total or None


def _wing_span(project: Project, _record: object = None) -> Optional[float]:
    from sloads.derived_geometry import wing_span_in

    return wing_span_in(project)


def _side_gust_izz(project: Project, _record: object = None) -> Optional[float]:
    from sloads.modules.select import default_side_gust_izz

    return default_side_gust_izz(project)


def _select_wing_weight(project: Project, _record: object = None) -> Optional[float]:
    from sloads.cg_cases import max_takeoff_weight

    mtow = max_takeoff_weight(project, required=False)
    return 0.09 * mtow if mtow else None


def _mass_row(project: Project, record: object, selector_attr: str):
    from sloads.models import same_name

    selector = getattr(record, selector_attr, "") if record is not None else ""
    weight = project.weight
    if not selector or weight is None:
        return None
    return next((r for r in weight.items if same_name(r.name, selector)), None)


def _mass_row_value(selector_attr: str, pick):
    def resolver(project: Project, record: object = None):
        row = _mass_row(project, record, selector_attr)
        return None if row is None else pick(row)
    return resolver


EXTERNAL_VALUES: Dict[str, "typing.Callable[..., object]"] = {
    "speeds.wing_area_sqft": _speeds_wing_area,
    # The note 36 collapsed set (OV-9/OV-11): each resolver is the same
    # derivation the calc's ``value or derive(project)`` calls, so the number
    # the caption shows is the number a blank field uses. A resolver may take
    # the row instance as ``record`` when the path is a ``[]`` row.
    "weight.envelope.gross_weight": _mtow,
    "geometry.empennage.vtail.gross_weight_lb": _mtow,
    "weight.envelope.mac": _wing_ref_value("mac"),
    "weight.envelope.xlemac": _wing_ref_value("xlemac"),
    "weight.envelope.fuselage_nose_x": _fuselage_bound(min),
    "weight.envelope.fuselage_tail_x": _fuselage_bound(max),
    "aero_coeffs.cruise.stall_cl": _clmax("clmax_clean"),
    "aero_coeffs.cruise.neg_stall_cl": _clmax("clmax_clean_neg"),
    "aero_coeffs.flaps_down.stall_cl": _clmax("clmax_flap"),
    "aero.surfaces[].taper_ratio": _planform_taper,
    "aero.surfaces[].tip_ratio": _planform_tip,
    "geometry.empennage.htail.aspect_ratio_wing": _wing_ar,
    "geometry.empennage.htail.wing_lift_slope_per_rad": _wing_lift_slope,
    "select_input.full_down_aileron_deg": _aileron_down,
    "flap_loads.gust_load_factor": _gust_at_vf,
    "engines[].limit_load_factor": _limnz,
    "engines[].engine_weight_lb": _mass_row_value("engine_mass_item", lambda r: r.weight_lb),
    "engines[].engine_cg": _mass_row_value("engine_mass_item", lambda r: (r.x, r.y, r.z)),
    "engines[].prop_weight_lb": _mass_row_value("prop_mass_item", lambda r: r.weight_lb),
    "engines[].prop_cg": _mass_row_value("prop_mass_item", lambda r: (r.x, r.y, r.z)),
    # The #95 additions (C210-2/3/5/22/25): the SELECT copies and derivable
    # geometry the C210 build was asked to type by hand.
    "geometry.parametric.fuselage_length": _fuselage_length,
    "geometry.empennage.htail.elevator_area_sqft": _elevator_area,
    "geometry.empennage.vtail.rudder_area_sqft": _rudder_area,
    "geometry.empennage.vtail.wing_span_in": _wing_span,
    "geometry.empennage.vtail.izz_slugft2": _side_gust_izz,
    "select_input.wing_weight_lb": _select_wing_weight,
}

#: The paths whose calc contract is note 36's **falsy-means-derive /
#: typed-means-override** (OV-1). Enumerated once, here, and guarded by
#: OV-11's drift test: every member carries a non-empty ``derived_from`` and a
#: resolver above, and the GUI renders the resolver's value beside the field.
#: Two resolver-backed rows are **not** overrides and stand outside the set:
#: ``speeds.wing_area_sqft`` (the consumer resolves the planform; the widget
#: goes live only when there is none) and ``geometry.parametric.fuselage_length``
#: (a derived outline summary ``sync_geometry_derived`` overwrites -- #95,
#: C210-2 -- so it renders disabled once an outline exists, never as an
#: override).
_NOT_COLLAPSED: Tuple[str, ...] = (
    "speeds.wing_area_sqft", "geometry.parametric.fuselage_length")
COLLAPSED_OVERRIDES: Tuple[str, ...] = tuple(
    path for path in EXTERNAL_VALUES if path not in _NOT_COLLAPSED)


def external_value(path: str, project: Project, record: object = None):
    """The governing value behind an external copy, or ``None`` if there is none.

    ``record`` is the row instance for a ``[]`` path (which engine, which aero
    surface); scalar-path resolvers ignore it.
    """
    resolver = EXTERNAL_VALUES.get(path)
    return None if resolver is None else resolver(project, record)


#: Page-section titles that follow the **quantity**, not the dataclass (#95,
#: C210-6/22). The oracle form groups widgets by record prefix, so a wing
#: quantity that *lives* on a tail record for SELECT's convenience rendered
#: under a "Htail" heading -- and the owner read it as tail data. A path here
#: renders in its own titled section (still on its record: the caption keeps
#: the schema path) on whatever page its registry row names; paths sharing one
#: (page, record) must share one title (guarded in
#: ``tests/test_field_registry.py``).
DISPLAY_GROUPS: Dict[str, str] = {
    "geometry.empennage.htail.aspect_ratio_wing":
        "Wing aerodynamics (SELECT tail balance)",
    "geometry.empennage.htail.wing_lift_slope_per_rad":
        "Wing aerodynamics (SELECT tail balance)",
    "geometry.empennage.htail.wing_zero_lift_cruise_deg":
        "Wing aerodynamics (SELECT tail balance)",
    "geometry.empennage.htail.wing_zero_lift_enroute_deg":
        "Wing aerodynamics (SELECT tail balance)",
    "geometry.empennage.htail.wing_zero_lift_landing_deg":
        "Wing aerodynamics (SELECT tail balance)",
    "select_input.basic_airfoil_cm":
        "Wing section pitching moment (SELECT roll torsion)",
    "select_input.full_down_aileron_deg":
        "SELECT steady-roll torsion",
    "select_input.wing_weight_lb":
        "Wing weight (SELECT fuselage conditions)",
}


def _parametric_seed(project: Project, record: object = None) -> Dict[str, float]:
    from sloads.modules.configuration import parametric_wing_seed

    return parametric_wing_seed(project, record)


#: ``{record prefix: seed}`` -- records whose blank form can be filled from
#: values the project already holds, behind an explicit button (#95, C210-1 /
#: GR-GEOM-3). The seed answers ``{}`` when there is nothing to offer (the
#: block is already typed, or the source is absent), and the button writes the
#: returned fields through the normal entry path -- a page visit alone must
#: not dirty a project (OG-F), which is why this is a button and not a derive.
RECORD_SEEDS: Dict[str, "typing.Callable[..., Dict[str, float]]"] = {
    "geometry.parametric": _parametric_seed,
}


#: When a ``SLOADS`` field may be marked :attr:`FieldEntry.supplied` (G5).
#:
#: A judgement call here would quietly become "whatever made the gate pass", so
#: the mark is **earned**, one of two ways, and the ``basis`` says which:
#:
#: 1. **Structurally required** — the field has no declared default, so the
#:    record cannot be constructed without it. A ``SurfaceInput`` has no
#:    ``name``-less form; omitting it is not "keep the default", it is "have no
#:    surface". Guarded both ways in ``tests/test_field_registry.py``.
#: 2. **Demonstrably load-bearing** — omitting it changes an oracle-page result
#:    on a shipped example. That demonstration is gate G5 itself
#:    (``tests/test_oracle_inputs.py``), so the mark is never speculative.
#:
#: A ``SLOADS`` field meeting neither stays plain: the oracle GUI leaves it at
#: its default and nothing moves. That is the reduction OG-2/OG-5 promised.
SUPPLIED_RULE = "structurally required (no default), or demonstrably load-bearing (G5)"


def _E(path: str, page: str, origin: Origin, basis: str,
       quantity: str = "", derived_from: str = "", supplied: bool = False,
       governs: bool = False, resolves: str = "") -> FieldEntry:
    # Keywords, not position: ``governs`` sits before ``supplied`` on the
    # dataclass, and a positional call here would have bound one to the other.
    return FieldEntry(path=path, page=page, origin=origin, basis=basis,
                      quantity=quantity, derived_from=derived_from,
                      governs=governs, supplied=supplied, resolves=resolves)


_ORIG = Origin.ORIGINAL
_SLDS = Origin.SLOADS

# Editing-page keys, short so a 323-row table stays one row per line.
_GEO = "configuration_layout"
_WT = "weight_mass"
_SPD = "structural_speeds"
_AERO = "aero_coefficients"
_VN = "flight_envelope"
_WING = "wing_loads"
_FUS = "fuselage_loads"
_AIL = "aileron_loads"
_FLAP = "flap_loads"
_TAB = "tab_loads"
_ENG = "engine_mount"
_OEI = "one_engine_out"
_LAND = "landing_loads"

# --------------------------------------------------------------------------- #
# How `origin` was decided, so the table can be audited rather than trusted
# --------------------------------------------------------------------------- #
# Three kinds of in-repo evidence settle it, strongest first. Each row's
# ``basis`` says which one applies.
#
#  1. **A `.BAS` variable name in the field's own comment** (`models/inputs.py`):
#     SAAFT, DELTA, NG, D0..D4, ENGWT, TREAD, BLPROP... These are McMaster's
#     identifiers carried over at porting time, so the field *is* an input of
#     that program. Unambiguous.
#  2. **`PROGRAM_SPEC.md`'s per-module "Reads:"**, which restates UG Table 2.2.
#     Where it says a module's *only* upstream input is X (AILERON), fields
#     outside X are additions however plausible they look.
#  3. **A sloads step / decision tag** in the comment or class docstring — Step
#     C5/D5/E1/G1/G4/M2-6/M2-10, F25-2, L-7, plan 09, decision D-22/D-25, G-14.
#     A field the replication added carries the item that added it.
#
# Two standing rulings cover classes rather than rows:
#
#  * **Surface / set selectors are `sloads`** — `aileron_loads.surface`,
#    `speeds.wing_surface`, `aero_coeffs.*.name` and friends exist because this
#    model carries N surfaces where the original carried a fixed one. A **page
#    scalar** the oracle GUI resolves positionally and never asks (the flap page
#    means the flap). The ones it must still *write* to make a well-formed model
#    carry ``supplied=True`` (see :data:`SUPPLIED_RULE`) — building G5 showed
#    "never asks" and "never sets" are not the same claim, and the table was
#    only making the first one. The ruling stops at a **list row** (#98,
#    C210-46): a page cannot resolve which surface *each row* of
#    `tab_loads.tabs[]`, `tail_mass[]` or `aero.surfaces[]` belongs to, so
#    hiding the row's selector hardcodes it — every tab silently became an
#    h-tail tab. Row selectors are rendered (``supplied=True``, demonstrated
#    load-bearing in ``tests/test_oracle_inputs.py``), and the guard
#    ``tests/test_field_registry.py::test_a_list_row_selector_is_always_asked``
#    keeps the boundary.
#    The ruling covers selectors this model **created**; it does not cover a mode
#    the original program itself branched on. `engines[].engine_type` looks like
#    a selector and is not one: ENGLOADS ran a reciprocating and a turbine
#    branch, and every field of both (`ENGTORQ`, `CRUZTORQ`, `DT`, `CYL`) is
#    already `ORIGINAL` here — so the switch that chooses between them is too.
#  * **`origin` is about who *asked*, not who *computes*.** A field the original
#    entered directly and sloads now derives stays `ORIGINAL` and carries
#    ``derived_from`` (note 32, OG-7: an entered scalar wins and is marked). The
#    oracle GUI must still offer it; that is the whole point of OG-7.


REGISTRY: Tuple[FieldEntry, ...] = (
    # ----------------------------------------------------------------- #
    # geometry -- WINGGEOM (configuration_layout)
    # ----------------------------------------------------------------- #
    # Corrected building G5 (2026-08-19). This block read "the polyline planform
    # model is this replication's, so the oracle GUI offers `parametric` and
    # never the polylines" -- which `models/inputs.py` contradicts in its own
    # docstring: the edge polylines are entered "exactly as the original program
    # prompts for them" and `elements` *is* WINGGEOM.BAS's `H`. The oracle GUI
    # offers both, as the original did; `parametric` is not a substitute for the
    # planform, and no parametric->polyline builder is needed after all.
    _E("geometry.surfaces[].name", _GEO, _SLDS, "surface selector (standing ruling); "
       "structurally required -- SurfaceInput has no name-less form. Every downstream program "
       "reads the surface named `wing` (matched ignoring case), so the first row is seeded "
       "`wing`; `htail` / `vtail` / `aileron` / `flap` name the others", supplied=True),
    _E("geometry.surfaces[].leading_edge", _GEO, _ORIG,
       "WINGGEOM planform, '(X, Y) points ... exactly as the original program prompts for them'"),
    _E("geometry.surfaces[].trailing_edge", _GEO, _ORIG,
       "WINGGEOM planform, '(X, Y) points ... exactly as the original program prompts for them'"),
    _E("geometry.surfaces[].elements", _GEO, _ORIG,
       "WINGGEOM.BAS H, the strip count (Appendix A wing uses 20)"),
    _E("geometry.surfaces[].symmetric", _GEO, _SLDS,
       "mirrored vs single-side surface; the original kept one *GEOM.INP per surface, so the "
       "surface's identity carried this. Load-bearing (G5): omitting it doubles the ga6 aileron",
       supplied=True),
    _E("geometry.surfaces[].front_spar_pct", _GEO, _SLDS, "spar fractions, sbeam box model (Step C4)"),
    _E("geometry.surfaces[].rear_spar_pct", _GEO, _SLDS, "spar fractions, sbeam box model (Step C4)"),
    _E("geometry.surfaces[].ref_axis_pct", _GEO, _SLDS, "loads reference axis, R-7c"),
    _E("geometry.surfaces[].sob_y_in", _GEO, _SLDS, "side-of-body station, BM-1"),
    _E("geometry.surfaces[].tip_cap_width_in", _GEO, _SLDS,
       "rounded tip-cap width, note 36 OV-4 (C210-31): the planform rounding the polylines "
       "cannot carry; aero.surfaces[].tip_ratio falsy-derives from it / semi-span"),
    # The five scalars a typed ``wing`` planform determines are seedable from
    # it behind a button (#95, C210-1 / GR-GEOM-3): RECORD_SEEDS above offers
    # ``configuration.parametric_wing_seed`` while the block is not yet typed.
    _E("geometry.parametric.wing_area_sqft", _GEO, _ORIG, "WINGGEOM reference area S", "wing reference area"),
    _E("geometry.parametric.aspect_ratio", _GEO, _ORIG, "WINGGEOM AR = b^2/S"),
    _E("geometry.parametric.taper_ratio", _GEO, _ORIG, "WINGGEOM tip/root chord"),
    _E("geometry.parametric.dihedral_deg", _GEO, _ORIG, "WINGGEOM geometric dihedral"),
    _E("geometry.parametric.le_sweep_deg", _GEO, _ORIG, "WINGGEOM/AIRLOAD4 leading-edge sweep"),
    _E("geometry.parametric.le_root_x", _GEO, _ORIG, "WINGGEOM centreline LE station"),
    _E("geometry.parametric.root_waterline_z", _GEO, _ORIG, "WINGGEOM root-chord waterline"),
    _E("geometry.parametric.datum_x", _GEO, _ORIG, "WINGGEOM nose datum reference"),
    _E("geometry.parametric.h_tail_z", _GEO, _ORIG, "SELECT h-tail vertical offset (Ch 9)"),
    _E("geometry.parametric.tail_type", _GEO, _SLDS, "layout sketch only, Step G1"),
    _E("geometry.parametric.body_drag_waterline_z", _GEO, _SLDS, "body-drag line, Step G4 balance work"),
    # Candidate 19th duplicate, NOT declared: this and SELECT's LF
    # (geometry.empennage.airplane_length_in, one field since v55 / #52)
    # are plausibly one dimension, but nothing in the repo says so and the two
    # are not held equal on any fixture. Declaring it would assert a defect that
    # has not been demonstrated; it is raised in the OG-C closure instead.
    _E("geometry.parametric.fuselage_length", _GEO, _ORIG,
       "overall length; summarised from geometry.fuselage.sections[].x when entered "
       "(Step M2-6; #95, C210-2: rendered disabled once an outline exists -- "
       "sync_geometry_derived overwrites it on every run)",
       derived_from=EXTERNAL + "the fuselage outline (derived_geometry."
       "fuselage_summary; sync_geometry_derived keeps this scalar equal to it)",
       resolves="With no fuselage outline entered yet, a typed length stands "
       "(and seeds the outline when an older file loads); once outline "
       "sections exist, the outline governs and this is its read-only summary."),
    _E("geometry.parametric.fuselage_width", _GEO, _SLDS, "derived outline summary, Step M2-6"),
    _E("geometry.parametric.fuselage_height", _GEO, _SLDS, "derived outline summary, Step M2-6"),
    # The outline itself is sloads (Step G1), but a section cannot be constructed
    # without all three, so a project that has one at all has these (G5 rule 1).
    _E("geometry.fuselage.sections[].x", _GEO, _SLDS,
       "body outline model, Step G1; structurally required", supplied=True),
    _E("geometry.fuselage.sections[].width", _GEO, _SLDS,
       "body outline model, Step G1; structurally required", supplied=True),
    _E("geometry.fuselage.sections[].height", _GEO, _SLDS,
       "body outline model, Step G1; structurally required", supplied=True),
    _E("geometry.fuselage.sections[].z_centre", _GEO, _SLDS, "body outline model, Step G1"),

    # geometry.empennage -- the whole-airplane length both tail inertias use
    # (one home since v55, #52; each tail carried a copy before)
    _E("geometry.empennage.airplane_length_in", _GEO, _ORIG, "SELECT LF (Iyy and default IZZ)"),

    # geometry.empennage.htail -- SELECT's rational h-tail inputs (Ch 9)
    _E("geometry.empennage.htail.aspect_ratio_htail", _GEO, _ORIG, "SELECT ARHT"),
    _E("geometry.empennage.htail.aspect_ratio_wing", _AERO, _ORIG, "SELECT ARW (downwash); "
       "a wing quantity, edited with the wing aero data (#95, C210-6 display group)",
       "wing planform aspect ratio",
       EXTERNAL + "the wing planform AR (derived_geometry.wing_aspect_ratio, the OV-5 "
       "consolidated owner; note 36 OV-2, C210-36)",
       governs=True),
    _E("geometry.empennage.htail.htail_area_sqft", _GEO, _ORIG, "SELECT ST"),
    _E("geometry.empennage.htail.htail_semispan_in", _GEO, _ORIG, "SELECT BLHTAIL"),
    _E("geometry.empennage.htail.elevator_area_sqft", _GEO, _ORIG,
       "SELECT SE; blank derives as SEFWDHL + SEAFTHL -- one owner for the "
       "elevator-area triple (#95, C210-5)",
       derived_from=EXTERNAL + "its own hinge halves, SEFWDHL + SEAFTHL "
       "(select.derived_elevator_area; a typed SE that disagrees warns, "
       "validation.elevator_area_mismatch)",
       governs=True),
    _E("geometry.empennage.htail.elevator_aft_hinge_sqft", _GEO, _ORIG, "SELECT SEAFTHL"),
    _E("geometry.empennage.htail.elevator_fwd_hinge_sqft", _GEO, _ORIG, "SELECT SEFWDHL"),
    _E("geometry.empennage.htail.elevator_te_down_deg", _GEO, _ORIG, "SELECT EDN"),
    _E("geometry.empennage.htail.elevator_te_up_deg", _GEO, _ORIG, "SELECT EUP"),
    _E("geometry.empennage.htail.elevator_effectiveness", _GEO, _ORIG, "SELECT dalpha/ddelta_e"),
    _E("geometry.empennage.htail.tail_incidence_deg", _GEO, _ORIG, "SELECT IT"),
    _E("geometry.empennage.htail.wing_lift_slope_per_rad", _AERO, _ORIG, "SELECT AW; "
       "a wing quantity, edited with the wing aero data (#95, C210-6 display group)",
       "wing lift-curve slope",
       EXTERNAL + "the cruise aero set's C1 x 57.3 (select.wing_lift_slope_per_rad; "
       "note 36 OV-2, C210-36)",
       governs=True),
    _E("geometry.empennage.htail.wing_zero_lift_cruise_deg", _AERO, _ORIG,
       "SELECT IW (cruise); wing aero, #95 C210-6 display group"),
    _E("geometry.empennage.htail.wing_zero_lift_enroute_deg", _AERO, _ORIG,
       "SELECT IW (enroute); wing aero, #95 C210-6 display group"),
    _E("geometry.empennage.htail.wing_zero_lift_landing_deg", _AERO, _ORIG,
       "SELECT IW (landing); wing aero, #95 C210-6 display group"),
    _E("geometry.empennage.htail.xt25", _GEO, _ORIG, "SELECT 25% tail MAC station"),
    _E("geometry.empennage.htail.xt50", _GEO, _ORIG, "SELECT 50% tail MAC station"),

    # geometry.empennage.vtail -- SELECT's rational v-tail inputs (Ch 9)
    _E("geometry.empennage.vtail.aspect_ratio_vtail", _GEO, _ORIG, "SELECT ARVT"),
    _E("geometry.empennage.vtail.vtail_area_sqft", _GEO, _ORIG, "SELECT SV"),
    _E("geometry.empennage.vtail.vtail_mac_in", _GEO, _ORIG, "SELECT VMAC"),
    _E("geometry.empennage.vtail.vtail_span_in", _GEO, _ORIG, "SELECT BLHTAIL (v-tail span)"),
    _E("geometry.empennage.vtail.rudder_area_sqft", _GEO, _ORIG,
       "SELECT SR; blank derives as SRFWDHL + SRAFTHL -- one owner for the "
       "rudder-area triple (#95, C210-5)",
       derived_from=EXTERNAL + "its own hinge halves, SRFWDHL + SRAFTHL "
       "(select.derived_rudder_area; a typed SR that disagrees warns, "
       "validation.rudder_area_mismatch)",
       governs=True),
    _E("geometry.empennage.vtail.rudder_aft_hinge_sqft", _GEO, _ORIG, "SELECT SRAFTHL"),
    _E("geometry.empennage.vtail.rudder_fwd_hinge_sqft", _GEO, _ORIG, "SELECT SRFWDHL"),
    _E("geometry.empennage.vtail.rudder_deflection_deg", _GEO, _ORIG, "SELECT RD"),
    _E("geometry.empennage.vtail.rudder_large_deflection_factor", _GEO, _ORIG, "SELECT EFV (subr 10000)"),
    _E("geometry.empennage.vtail.wing_span_in", _GEO, _ORIG,
       "SELECT B; blank derives from the WINGGEOM wing planform's own span "
       "(#95, C210-3 -- the C210 build typed 440 in against the integrator's 441)",
       "wing planform span",
       EXTERNAL + "the wing planform span (derived_geometry.wing_span_in, the "
       "WINGGEOM strip integral's span; select.effective_vtail_inputs)",
       governs=True),
    _E("geometry.empennage.vtail.gross_weight_lb", _GEO, _ORIG, "SELECT GW", "max take-off weight",
       "weight.max_takeoff_weight_lb (MTOW SSOT G-14; review N1 instance 1)",
       governs=True),
    _E("geometry.empennage.vtail.izz_slugft2", _GEO, _ORIG,
       "SELECT IZZ; 0 -> the SELECT.BAS rod estimate, now disclosed (#95, "
       "C210-25: it measured +49 % over WTONECG's database IZZ on the C210 "
       "with nothing saying an estimate was in play)",
       derived_from=EXTERNAL + "the rod-estimate default IZZ, two slender "
       "rods over the span and airplane length (select.default_side_gust_izz, "
       "SELECT.BAS 8884; WTONECG's database IZZ is disclosed beside the "
       "results, not consumed)",
       governs=True),
    _E("geometry.empennage.vtail.xv25", _GEO, _ORIG, "SELECT 25% v-tail MAC station"),
    _E("geometry.empennage.vtail.xv50", _GEO, _ORIG, "ONENGOUT camber-load station"),
    _E("geometry.empennage.vtail.vtail_root_waterline_z", _GEO, _SLDS, "v-tail root waterline, plan 09 (tail_span)"),

    # Aileron/flap planform geometry -- C210-37 (owner: "very similar
    # information" to the empennage forms). The rows keep their slices
    # (``aileron_loads``/``flap_loads`` -- the single-consumer pattern, no
    # schema move) but render on the Geometry page beside the empennage forms;
    # the load pages keep their per-page condition inputs (flap NG and the
    # slipstream band). Placed here so the sections sit with the other
    # planform forms in registry order.
    _E("aileron_loads.area_aft_hinge_sqft", _GEO, _ORIG, "AILERON SAAFT"),
    _E("aileron_loads.area_fwd_hinge_sqft", _GEO, _ORIG, "AILERON SAFWD"),
    _E("aileron_loads.up_deflection_deg", _GEO, _ORIG, "AILERON AUPDEG"),
    _E("aileron_loads.down_deflection_deg", _GEO, _ORIG, "AILERON ADEG",
       "full-down aileron deflection"),
    _E("flap_loads.flap_area_one_side_sqft", _GEO, _ORIG, "FLAPLOAD SF"),
    _E("flap_loads.flap_chord_ratio", _GEO, _ORIG, "FLAPLOAD E"),
    _E("flap_loads.flap_deflection_deg", _GEO, _ORIG, "FLAPLOAD DELTA"),

    # geometry.landing_gear -- the G6b single source
    _E("geometry.landing_gear.tread_in", _GEO, _ORIG, "LANDLOAD TREAD"),
    _E("geometry.landing_gear.main_gear.attach", _GEO, _SLDS,
       "trunnion node, gear free body Step 10; load-bearing (G5, #98, C210-49): without it "
       "the leg's node is omitted from the free-free model and no ground case is delivered",
       supplied=True),
    _E("geometry.landing_gear.main_gear.axle_static", _GEO, _ORIG, "LANDLOAD static axle station"),
    _E("geometry.landing_gear.main_gear.axle_compressed", _GEO, _ORIG, "LANDLOAD compressed axle station"),
    _E("geometry.landing_gear.main_gear.axle_extended", _GEO, _ORIG, "LANDLOAD extended axle reference"),
    _E("geometry.landing_gear.main_gear.rolling_radius_in", _GEO, _ORIG, "LANDLOAD RM"),
    _E("geometry.landing_gear.main_gear.strut", _GEO, _ORIG, "LGFACTOR oleo/spring selector"),
    _E("geometry.landing_gear.main_gear.carrier", _GEO, _SLDS,
       "BODY|WING carrier, decision G-2; load-bearing (G5, #98, C210-49): None = not stated, "
       "the export assumes and warns rather than routes",
       supplied=True),
    _E("geometry.landing_gear.main_gear.weight_lb", _GEO, _SLDS,
       "leg weight, decision G-12a; load-bearing (G5, #98, C210-49): 0 = not stated, the "
       "gear report's free body stays open (no inertia term)",
       supplied=True),
    _E("geometry.landing_gear.nose_gear.attach", _GEO, _SLDS,
       "trunnion node, gear free body Step 10; load-bearing (G5, #98, C210-49): without it "
       "the leg's node is omitted from the free-free model and no ground case is delivered",
       supplied=True),
    _E("geometry.landing_gear.nose_gear.axle_static", _GEO, _ORIG, "LANDLOAD static axle station"),
    _E("geometry.landing_gear.nose_gear.axle_compressed", _GEO, _ORIG, "LANDLOAD compressed axle station"),
    _E("geometry.landing_gear.nose_gear.axle_extended", _GEO, _ORIG, "LANDLOAD extended axle reference"),
    _E("geometry.landing_gear.nose_gear.rolling_radius_in", _GEO, _ORIG, "LANDLOAD RN"),
    _E("geometry.landing_gear.nose_gear.strut", _GEO, _ORIG, "LGFACTOR oleo/spring selector"),
    _E("geometry.landing_gear.nose_gear.carrier", _GEO, _SLDS,
       "BODY|WING carrier, decision G-2; load-bearing (G5, #98, C210-49): None = not stated, "
       "the export assumes and warns rather than routes",
       supplied=True),
    _E("geometry.landing_gear.nose_gear.weight_lb", _GEO, _SLDS,
       "leg weight, decision G-12a; load-bearing (G5, #98, C210-49): 0 = not stated, the "
       "gear report's free body stays open (no inertia term)",
       supplied=True),

    # ----------------------------------------------------------------- #
    # weight -- WTESTIMA / WTONECG / WTENV (weight_mass)
    # ----------------------------------------------------------------- #
    _E("weight.max_takeoff_weight_lb", _WT, _ORIG, "MTOW, every module's design weight", "max take-off weight"),
    _E("weight.max_landing_weight_lb", _WT, _ORIG, "MLW, LANDLOAD design landing weight"),
    _E("weight.estimation.airplane", _WT, _ORIG, "WTESTIMA airplane class"),
    _E("weight.estimation.engines", _WT, _ORIG, "WTESTIMA NOENGS", "engine count",
       EXTERNAL + "len(Project.engines) (review N1 instance 3: concept_heavy 2 vs 0)",
       governs=True),
    _E("weight.estimation.max_continuous_hp", _WT, _ORIG, "WTESTIMA HP", "max continuous power",
       EXTERNAL + "sum of engines[].max_cont_hp (unless overridden -- see resolves)",
       resolves="The estimate correlates against the engine list's combined "
                "max-continuous power, not this field, unless the override "
                "switch beside it is set (or no engine states a rating)."),
    _E("weight.estimation.override_max_continuous_hp", _WT, _SLDS, "override switch for the engine-sum derivation"),
    _E("weight.estimation.seats", _WT, _ORIG, "WTESTIMA SEATS"),
    _E("weight.estimation.crew", _WT, _SLDS, "FAR 23 seat-limit check, Step E1"),
    _E("weight.estimation.baggage_lb", _WT, _ORIG, "WTESTIMA BAG"),
    _E("weight.estimation.cruise_hours", _WT, _ORIG, "WTESTIMA HOURS"),
    _E("weight.estimation.pressurized", _WT, _ORIG, 'WTESTIMA P$ = "P"'),
    _E("weight.estimation.engine_weight_type", _WT, _ORIG,
       "WTESTIMA.BAS lines 230-290 installed-weight correlation, 'the two-letter codes of the "
       "original program' (RF/RT/TC/TP/LC) -- corrected from SLOADS building G5"),
    _E("weight.items[].name", _WT, _ORIG, "WTONECG item name"),
    _E("weight.items[].weight_lb", _WT, _ORIG, "WTONECG item weight"),
    _E("weight.items[].x", _WT, _ORIG, "WTONECG item station"),
    _E("weight.items[].y", _WT, _ORIG, "WTONECG item butt line"),
    _E("weight.items[].z", _WT, _ORIG, "WTONECG item waterline"),
    # Corrected building G5: these four were SLOADS, and Appendix A p136 settles
    # it. The item's own inertia is stored "in lb-in^2 (the units the original
    # data base stores)" and is added to WTONECG's parallel-axis transfer --
    # without it ga6's IXX comes out 66.7 slug-ft^2 against the printed 1201.527,
    # so the oracle the suite already passes *depends* on these being entered.
    _E("weight.items[].ixx", _WT, _ORIG, "WTONECG item inertia, 'the units the original data "
       "base stores'; Appendix A p136 IXX 1201.527 needs it"),
    _E("weight.items[].iyy", _WT, _ORIG, "WTONECG item inertia; Appendix A p136 IYY 2058.209"),
    _E("weight.items[].izz", _WT, _ORIG, "WTONECG item inertia; Appendix A p136 IZZ 3022.766"),
    _E("weight.items[].kind", _WT, _ORIG,
       "'Mirrors the data-base partition of WTONECG.BAS (empty / minimum-flight / discretionary)'; "
       "WTENV's discretionary envelope and Appendix A's 78 lb aft ballast need it"),
    _E("weight.items[].component", _WT, _SLDS,
       "component tag, plan 09 T-3. The original carried this by position -- BODYLOAD "
       "took its own fuselage item list -- so the tag is how the same question is asked "
       "here. Load-bearing (G5, review 2026-08-22 PB-2): untagged, the wing panel sits "
       "on the fuselage beam at 9 % of peak BODYLOAD shear", supplied=True),
    _E("weight.items[].consumable", _WT, _SLDS, "loading model, decision D-25"),
    _E("weight.items[].wing_fraction", _WT, _SLDS,
       "wing/body split of one row (plan 11, note 29 WF-2): `component` at finer grain, the "
       "same which-beam question BODYLOAD asked by position. Load-bearing (G5, #62): the "
       "DHC-8 fuel row is 86 % wing, and dropped it rides the fuselage beam whole",
       supplied=True),
    _E("weight.envelope.gross_weight", _WT, _ORIG, "WTENV gross weight", "max take-off weight",
       "weight.max_takeoff_weight_lb (blank derives from the MTOW SSOT, note 36 OV-2; C210-13)",
       governs=True),
    _E("weight.envelope.mac", _WT, _ORIG, "WTENV MAC", "wing MAC",
       EXTERNAL + "derived_geometry from the planform (Optional override here)",
       governs=True),
    _E("weight.envelope.xlemac", _WT, _ORIG, "WTENV LEMAC station", "wing XLEMAC",
       EXTERNAL + "derived_geometry from the planform (Optional override here; the mac_reference "
       "pair, note 36 / C210-13)",
       governs=True),
    _E("weight.envelope.fwd_gross_pct_mac", _WT, _ORIG, "WTENV forward gross CG limit"),
    _E("weight.envelope.aft_gross_pct_mac", _WT, _ORIG, "WTENV aft gross CG limit"),
    _E("weight.envelope.fwd_regardless_pct_mac", _WT, _ORIG, "WTENV forward-regardless CG limit"),
    _E("weight.envelope.fwd_regardless_weight", _WT, _ORIG, "WTENV forward-regardless weight"),
    _E("weight.envelope.fuselage_nose_x", _WT, _ORIG, "WTENV nose station", "fuselage nose station",
       EXTERNAL + "the fuselage outline (all-or-nothing pair with tail_x, weight_envelope."
       "_fuselage_extent; note 36 / C210-13)",
       governs=True),
    _E("weight.envelope.fuselage_tail_x", _WT, _ORIG, "WTENV tail station", "fuselage tail station",
       EXTERNAL + "the fuselage outline (all-or-nothing pair with nose_x, weight_envelope."
       "_fuselage_extent; note 36 / C210-13)",
       governs=True),
    _E("weight.envelope.wing_surface", _WT, _SLDS, "surface selector (standing ruling)"),
    # The *grid* is Step D5's consolidation, but the cases themselves are not:
    # "the four corners of the WTENV weight-cg envelope (FLTLOADS.BAS prompts for
    # four per configuration)". So the numbers are ORIGINAL and only the columns
    # carrying what the original expressed positionally are sloads' (G5).
    _E("weight.cg_cases[].name", _WT, _SLDS,
       "case selector, Step D5; structurally required", supplied=True),
    _E("weight.cg_cases[].role", _WT, _SLDS,
       "LANDLOAD's three loadings (UG fig 18.2), positional in the original, a column here (G-3a). "
       "Load-bearing (G5): without it LANDLOAD has no GROUND cases and does not run. "
       "The role only assigns the case to its slot -- nothing checks the numbers "
       "against the tag, so a heavy-aft case tagged fwd_light is consumed in the "
       "light-forward slot without complaint (#94, C210-14)", supplied=True),
    _E("weight.cg_cases[].weight_lb", _WT, _ORIG, "FLTLOADS.BAS prompts for four CG cases"),
    _E("weight.cg_cases[].xcg", _WT, _ORIG, "FLTLOADS.BAS CG station of the case"),
    _E("weight.cg_cases[].zcg", _WT, _ORIG, "FLTLOADS.BAS CG waterline of the case"),
    _E("weight.cg_cases[].analyses", _WT, _SLDS,
       "which analyses use this case, Step D5 -- the original recorded it by which program's screen "
       "the case was typed into. Load-bearing (G5): the default {FLIGHT} loses every ground case",
       supplied=True),
    _E("weight.cg_cases[].loading.aboard", _WT, _SLDS, "loading definition, decision D-25"),
    _E("weight.cg_cases[].loading.fractions", _WT, _SLDS, "loading definition, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.name", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.weight_lb", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.x", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.y", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.z", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.ixx", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.iyy", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.izz", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.kind", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.component", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.consumable", _WT, _SLDS, "ballast item, decision D-25"),
    _E("weight.cg_cases[].loading.ballast.wing_fraction", _WT, _SLDS, "ballast item, decision D-25"),

    # ----------------------------------------------------------------- #
    # speeds -- STRSPEED + MACHLIM (structural_speeds)
    # ----------------------------------------------------------------- #
    _E("speeds.category", _SPD, _ORIG, "STRSPEED category, UG Table 7.1"),
    _E("speeds.weight_lb", _SPD, _ORIG, "STRSPEED design weight W", "max take-off weight",
       "weight.max_takeoff_weight_lb (override, not a read-through: STRSPEED uses "
       "this value verbatim; the link back is cg_cases.max_takeoff_weight's fallback "
       "and validation's mtow_representation_drift warning -- note 33 DS-6/2.3)",
       governs=True),
    # The one conditionally-governing copy (#36, corrected by #70 / PB-17). STRSPEED
    # resolves the ``speeds.wing_surface`` **planform** and reaches this field only
    # when the geometry carries no such surface. The owner named here was
    # ``geometry.parametric.wing_area_sqft`` -- a different quantity, which the
    # disabled widget then displayed: 500.0 against the 497.75 STRSPEED used on
    # concept_regional_jet, and unrelated numbers on a hand-typed project. The owner
    # is not a field at all, so it is external, and the value shown comes from the
    # same resolver the calc calls (:data:`EXTERNAL_VALUES`).
    _E("speeds.wing_area_sqft", _SPD, _ORIG, "STRSPEED S (W/S)", "wing reference area",
       EXTERNAL + "wing planform (the WINGGEOM integral over speeds.wing_surface -- #70)",
       resolves="STRSPEED integrates that planform whenever the surface exists, "
                "and reads this field only when it does not -- so it is disabled "
                "while there is a planform, and live when there is none."),
    _E("speeds.wing_surface", _SPD, _SLDS, "surface selector (standing ruling)"),
    _E("speeds.vh_kt", _SPD, _ORIG, "STRSPEED VH, max level speed"),
    _E("speeds.shoulder_altitude_ft", _SPD, _ORIG,
       "STRSPEED MC/MD altitude; MACHLIM first row (one home since v55, #52)"),
    # The chosen speeds are optional overrides of computed regulatory minimums
    # (#94, C210-16): enter a value if you have one; blank uses the computed
    # minimum, and a value below the minimum is overridden (raised) to it.
    _E("speeds.chosen_vc", _SPD, _ORIG,
       "STRSPEED chosen VC, Appendix A p156 -- blank uses the computed 23.335(a) "
       "minimum; a value below the minimum is raised to it"),
    _E("speeds.chosen_vd", _SPD, _ORIG,
       "STRSPEED chosen VD, Appendix A p156 -- blank uses the computed 23.335(b) "
       "minimum; a value below the minimum is raised to it"),
    _E("speeds.chosen_va", _SPD, _ORIG,
       "STRSPEED chosen VA, Appendix A p156 -- blank uses the computed 23.335(c) "
       "minimum (VS*sqrt(n)); a value below the minimum is raised to it"),
    _E("speeds.chosen_vf", _SPD, _ORIG,
       "STRSPEED chosen VF, Appendix A p156 -- the 23.345 *design* wing-flap speed "
       "(>= max(1.4*VS, 1.8*VSF)), the structural speed for flaps-extended cases, "
       "not the operating placard VFE (which must be <= VF). Blank uses the "
       "computed minimum; a value below it is raised"),
    _E("speeds.chosen_n", _SPD, _ORIG, "STRSPEED chosen n, Appendix A p156"),
    _E("speeds.chosen_nneg", _SPD, _ORIG, "STRSPEED chosen negative n, Appendix A p156"),
    _E("speeds.mach_limit.max_operating_altitude_ft", _SPD, _ORIG, "MACHLIM ceiling"),
    _E("speeds.mach_limit.increment_ft", _SPD, _ORIG, "MACHLIM altitude step"),
    _E("speeds.occupants", _SPD, _SLDS, "FAR 23 applicability check, Step E1"),
    _E("speeds.vd_basis", _SPD, _SLDS, "25.335(b) route selector, F25-2"),
    _E("speeds.mach_margin_min", _SPD, _SLDS, "25.335(b)(2) Mach margin, F25-2"),
    _E("speeds.mach_margin_basis", _SPD, _SLDS, "25.335(b)(2) rational analysis, F25-2"),
    _E("speeds.vb_kt", _SPD, _SLDS, "25.335(d) rough-air speed, F25-2"),
    _E("speeds.no_yellow_arc", _SPD, _SLDS, "Subpart G placard family, M2-10"),
    _E("speeds.target_vne", _SPD, _SLDS, "operational target, advisory only, M2-10"),
    _E("speeds.target_vno", _SPD, _SLDS, "operational target, advisory only, M2-10"),
    _E("speeds.target_vmo", _SPD, _SLDS, "operational target, advisory only, M2-10"),
    _E("speeds.target_mmo", _SPD, _SLDS, "operational target, advisory only, M2-10"),
    _E("speeds.target_vfe", _SPD, _SLDS, "operational target, advisory only, M2-10"),

    # ----------------------------------------------------------------- #
    # aero_coeffs -- FLTLOADS coefficient sets (aero_coefficients)
    # ----------------------------------------------------------------- #
    _E("aero_coeffs.clmax_clean", _AERO, _ORIG, "STRSPEED/FLTLOADS CLmax, UG p7-5",
       "clean positive stall CL"),
    _E("aero_coeffs.clmax_clean_neg", _AERO, _ORIG, "FLTLOADS negative stall line",
       "clean negative stall CL"),
    _E("aero_coeffs.clmax_flap", _AERO, _ORIG, "STRSPEED/FLTLOADS flapped CLmax, UG p7-5",
       "flapped positive stall CL"),
    _E("aero_coeffs.cruise.name", _AERO, _SLDS,
       "set selector (standing ruling); structurally required", supplied=True),
    _E("aero_coeffs.cruise.lift", _AERO, _ORIG, "FLTLOADS C0..C4"),
    _E("aero_coeffs.cruise.drag", _AERO, _ORIG, "FLTLOADS D0..D4"),
    _E("aero_coeffs.cruise.moment", _AERO, _ORIG, "FLTLOADS M0..M4"),
    # The per-set stall CLs are the FLTLOADS balance clamp; blank inherits the
    # CLmax trio through ``normalize()``'s fill-through -- shipped mechanism,
    # registered here (note 36, OV-3; the C210-15 ruling). Enter one only to
    # reproduce a deck that clamps at a different value (ga6: 1.41 vs 1.4068).
    _E("aero_coeffs.cruise.stall_cl", _AERO, _ORIG, "FLTLOADS set stall CL",
       "clean positive stall CL",
       "aero_coeffs.clmax_clean (blank inherits via normalize(); note 36 OV-3, C210-15)",
       governs=True),
    _E("aero_coeffs.cruise.neg_stall_cl", _AERO, _ORIG, "FLTLOADS set negative stall CL",
       "clean negative stall CL",
       "aero_coeffs.clmax_clean_neg (blank inherits via normalize(); note 36 OV-3, C210-15)",
       governs=True),
    _E("aero_coeffs.cruise.flaps_down", _AERO, _ORIG, "FLTLOADS configuration flag"),
    _E("aero_coeffs.flaps_down.name", _AERO, _SLDS,
       "set selector (standing ruling); structurally required", supplied=True),
    _E("aero_coeffs.flaps_down.lift", _AERO, _ORIG, "FLTLOADS C0..C4"),
    _E("aero_coeffs.flaps_down.drag", _AERO, _ORIG, "FLTLOADS D0..D4"),
    _E("aero_coeffs.flaps_down.moment", _AERO, _ORIG, "FLTLOADS M0..M4"),
    _E("aero_coeffs.flaps_down.stall_cl", _AERO, _ORIG, "FLTLOADS set stall CL",
       "flapped positive stall CL",
       "aero_coeffs.clmax_flap (blank inherits via normalize(); note 36 OV-3, C210-15)",
       governs=True),
    # flaps_down.neg_stall_cl stays a plain row (note 36 OV-3): there is no
    # clmax_flap_neg for it to inherit from -- the documented #81 gap, which
    # validation warns about rather than guessing.
    _E("aero_coeffs.flaps_down.neg_stall_cl", _AERO, _ORIG, "FLTLOADS set negative stall CL"),
    _E("aero_coeffs.flaps_down.flaps_down", _AERO, _ORIG, "FLTLOADS configuration flag"),
    _E("aero_coeffs.fuselage_moment.enabled", _AERO, _SLDS, "Munk slender-body increment, Step G4"),
    _E("aero_coeffs.fuselage_moment.d_cm_dalpha", _AERO, _SLDS, "Munk slender-body increment, Step G4"),
    _E("aero_coeffs.lateral_body_aero.enabled", _AERO, _SLDS, "lumped lateral body aero, L-7"),
    _E("aero_coeffs.lateral_body_aero.cy_beta", _AERO, _SLDS, "lumped lateral body aero, L-7"),
    _E("aero_coeffs.lateral_body_aero.cn_beta", _AERO, _SLDS, "lumped lateral body aero, L-7"),

    # ----------------------------------------------------------------- #
    # flight_loads -- FLTLOADS (flight_envelope); the M2-6 derived copies
    # ----------------------------------------------------------------- #
    _E("flight_loads.altitudes_ft", _VN, _ORIG,
       "FLTLOADS envelope altitudes -- the cruise set balances at every entry; "
       "the flaps-down envelope runs at sea level only (FLTLOADS.BAS line 3000)"),
    # Not "the gust/manoeuvre matrix", which is what this row said until PB-22:
    # ``mn`` is the Mach number the aero coefficients were *measured* at (~0.1;
    # FLTLOADS.BAS line 138, ``FlightLoadsInput``), and the help tooltip is
    # built from this string, so the one field on the page whose name gives no
    # clue was the one field whose help named a different quantity.
    _E("flight_loads.mn", _VN, _ORIG,
       "FLTLOADS coefficient Mach number — the Mach the aero-coefficient sets "
       "were obtained at (typically ~0.1), not a design Mach"),
    # The h-tail centre-of-pressure fuselage stations (#94, C210-20): flaps up
    # the CP sits well forward on the tail, flaps down it moves aft. The page
    # shows a computed suggestion from the empennage record beside the fields
    # (oracle_app.form.GROUP_NOTES); the user still types the value.
    _E("flight_loads.xtc", _VN, _ORIG,
       "FLTLOADS tail CP, cruise -- h-tail centre-of-pressure fuselage station, "
       "flaps up (cruise/clean): CP well forward on the tail, ~5% of tail MAC"),
    _E("flight_loads.xtf", _VN, _ORIG,
       "FLTLOADS tail CP, flapped -- h-tail centre-of-pressure fuselage station, "
       "flaps down (VF/landing): CP moves aft, ~25% of tail MAC"),

    # select_input -- SELECT beyond the V-n matrix. All three rows moved off
    # the V-n page to the page their *quantity* belongs to (#95, C210-22
    # display groups): the section cm with the aero data, the aileron travel
    # with the aileron record, the wing weight with the weight data.
    _E("select_input.basic_airfoil_cm", _AERO, _ORIG, "SELECT basic airfoil CM, Ch 9 "
       "(the bare section cm at zero aileron for the 23.349(b) roll torsion -- "
       "not the airplane-less-tail M0 beside it; #95, C210-22)"),
    _E("select_input.full_down_aileron_deg", _AIL, _ORIG, "SELECT full-down aileron, "
       "Ch 9; control geometry, edited with the aileron record (#95, C210-22)",
       "full-down aileron deflection",
       "aileron_loads.down_deflection_deg (blank derives from the AILERON travel; "
       "note 36 OV-2, C210-38 -- a typed disagreement warns, aileron_deflection_mismatch)",
       governs=True),
    _E("select_input.wing_weight_lb", _WT, _ORIG, "SELECT wing weight, Ch 9; a weight "
       "quantity, edited with the weight data (#95, C210-22 -- the 0 -> 0.09*MTOW "
       "fallback was undisclosed on the page)",
       derived_from=EXTERNAL + "the Ch 9 statistical stand-in 0.09 x MTOW "
       "(select.select_fuselage; the items table's wing-component sum is the "
       "better number to type -- both-sides total wing group weight)",
       governs=True),

    # ----------------------------------------------------------------- #
    # aero -- AIRLOADS/AIRLOAD4/TAU per-surface inputs (wing_loads)
    # ----------------------------------------------------------------- #
    _E("aero.surfaces[].name", _WING, _SLDS,
       "row selector -- pairs the row with its geometry planform; load-bearing (G5, #98): "
       "an unmatched name leaves the surface on its seeded defaults (note 36 OV-8)",
       supplied=True),
    _E("aero.surfaces[].section_slope", _WING, _ORIG,
       "AIRLOADS mo -- the 2-D airfoil *section* lift-curve slope per degree "
       "(typical 0.105-0.110), NOT the aero page's C1: C1 is the 3-D "
       "airplane-less-tail slope, already reduced for finite AR, so entering it "
       "here double-counts the aspect-ratio reduction (#94, C210-28)"),
    _E("aero.surfaces[].profile_drag", _WING, _ORIG, "AIRLOADS CDO(Y)"),
    _E("aero.surfaces[].section_cm", _WING, _ORIG, "AIRLOADS CM(Y)"),
    _E("aero.surfaces[].twist", _WING, _ORIG, "AIRLOADS zero-lift angle(Y)"),
    _E("aero.surfaces[].taper_ratio", _WING, _ORIG, "TAU taper ratio", "surface taper ratio",
       EXTERNAL + "the paired planform's tip/centreline chord (derived_geometry."
       "taper_ratio_from_planform; note 36 OV-2, C210-31 owner directive)",
       governs=True),
    _E("aero.surfaces[].tip_ratio", _WING, _ORIG, "TAU rounded-tip ratio", "surface rounded-tip ratio",
       EXTERNAL + "the paired surface's tip_cap_width_in / semi-span (derived_geometry."
       "tip_ratio_from_planform; note 36 OV-4)",
       governs=True),
    _E("aero.surfaces[].tau", _WING, _ORIG, "TAU output, enterable as an override"),
    _E("aero.surfaces[].target_cl", _WING, _ORIG, "AIRLOADS evaluation CL"),
    _E("aero.surfaces[].sweep_deg", _WING, _ORIG, "AIRLOAD4 sweepback"),
    _E("aero.surfaces[].design_mach", _WING, _ORIG, "AIRLOAD4 high-Mach branch"),

    # wing_mass -- WINGINER (wing_loads)
    _E("wing_mass.surface", _WING, _SLDS, "surface selector (standing ruling)"),
    _E("wing_mass.panel_weight_lb", _WING, _ORIG, "WINGINER panel weight"),
    _E("wing_mass.inboard_rib_y", _WING, _ORIG, "WINGINER inboard rib station"),
    _E("wing_mass.tip_root_density_ratio", _WING, _ORIG, "WINGINER tip/root density ratio"),
    _E("wing_mass.concentrated[].name", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].weight_lb", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].x", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].y", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].z", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.cases[].name", _WING, _ORIG,
       "WINGINER.BAS 1660-1710 case name. 0 rows = the SELECT governing set; "
       "typed rows REPLACE that set entirely (#94, C210-30)"),
    _E("wing_mass.cases[].case", _WING, _ORIG, "WINGINER.BAS 1660-1710 case id"),
    _E("wing_mass.cases[].nz", _WING, _ORIG, "WINGINER.BAS 1660-1710 nz"),
    _E("wing_mass.cases[].nx", _WING, _ORIG, "WINGINER.BAS 1660-1710 nx"),
    _E("wing_mass.cases[].cl", _WING, _ORIG, "WINGINER.BAS 1660-1710 CL"),
    _E("wing_mass.cases[].v_eas_kt", _WING, _ORIG, "WINGINER.BAS 1660-1710 speed"),
    _E("wing_mass.cases[].unbal_moment", _WING, _ORIG, "WINGINER.BAS 1660-1710 unbalanced moment"),

    # fuselage_mass -- NETLOADS / Ch 15 (fuselage_loads)
    _E("fuselage_mass.ref_waterline", _FUS, _ORIG,
       "Ch 15 reference waterline -- reserved: stored and round-tripped, but "
       "consumed by no current calculation (the Ch 15 beam ignores it; pending "
       "M4-19/M4-21), so any value, 0 included, is currently equivalent "
       "(#94, C210-34 owner ruling)"),
    _E("fuselage_mass.stations[].x", _FUS, _ORIG, "Ch 15 station"),
    _E("fuselage_mass.stations[].weight_lb", _FUS, _ORIG, "Ch 15 station weight"),
    _E("fuselage_mass.stations_are_override", _FUS, _SLDS, "override switch for the weight-DB derivation"),

    # ----------------------------------------------------------------- #
    # Control-surface pages. The span-station fields are NOT .BAS inputs:
    # PROGRAM_SPEC says AILERON's only upstream input per UG Table 2.2 is the
    # deflections + areas; the stations feed the sbeam control-surface bridge.
    # ----------------------------------------------------------------- #
    _E("aileron_loads.surface", _AIL, _SLDS, "surface selector (standing ruling)"),
    _E("aileron_loads.inboard_y_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("aileron_loads.outboard_y_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("aileron_loads.hinges_span_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("aileron_loads.actuator_span_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.surface", _FLAP, _SLDS, "surface selector (standing ruling)"),
    _E("flap_loads.gust_load_factor", _FLAP, _ORIG, "FLAPLOAD NG",
       "flaps-extended gust load factor",
       EXTERNAL + "the flight envelope's GUST VF corner factor (flight_envelope.gust_at_vf, "
       "bit-for-bit the envelope's own number; note 36 OV-6, C210-39 owner directive)",
       governs=True),
    # Both place the 23.457(b) slipstream band; the term that uses the band is
    # driven by the engine record, so the basis says so where it is entered (#83).
    _E("flap_loads.nacelle_frontal_area_sqft", _FLAP, _ORIG,
       "FLAPLOAD AF (slipstream band; the slipstream needs an engine record's "
       "power + propeller diameter, entered on Engine Mount Loads)"),
    _E("flap_loads.engine_butt_line_in", _FLAP, _ORIG,
       "FLAPLOAD BLPROP (slipstream band; the slipstream needs an engine record's "
       "power + propeller diameter, entered on Engine Mount Loads)"),
    _E("flap_loads.inboard_y_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.outboard_y_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.hinges_span_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.actuator_span_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("tab_loads.tabs[].surface", _TAB, _SLDS,
       "row selector -- host surface; load-bearing (G5, #98, C210-46): picks the case-ID "
       "band, the exported component tag and the BL-vs-WL reading of station_in",
       supplied=True),
    _E("tab_loads.tabs[].area_sqft", _TAB, _ORIG, "TABLOADS STAB"),
    _E("tab_loads.tabs[].mac_in", _TAB, _ORIG, "TABLOADS MACTAB"),
    _E("tab_loads.tabs[].airfoil_chord_in", _TAB, _ORIG, "TABLOADS CAIRFOIL"),
    _E("tab_loads.tabs[].deflection_deg", _TAB, _ORIG, "TABLOADS DELTATAB"),
    _E("tab_loads.tabs[].station_in", _TAB, _ORIG, "TABLOADS BL/WL of the tab MAC"),

    # ----------------------------------------------------------------- #
    # engines -- ENGLOADS (engine_mount)
    # ----------------------------------------------------------------- #
    _E("engines[].engine_designation", _ENG, _ORIG, "ENGLOADS engine designation"),
    _E("engines[].engine_type", _ENG, _ORIG,
       "ENGLOADS reciprocating/turbine branch; every field of both branches (ENGTORQ, CRUZTORQ, "
       "DT, CYL) is ORIGINAL here, so the switch between them is -- corrected building G5"),
    _E("engines[].mounted_on", _ENG, _SLDS, "fuselage/wing carrier, Step C5"),
    _E("engines[].engine_weight_lb", _ENG, _ORIG, "ENGLOADS ENGWT", "engine mass",
       EXTERNAL + "the weight database (decision D-25 mass SSOT; review N1 instance 5: regional jet 300 lb apart)",
       governs=True),
    _E("engines[].engine_cg", _ENG, _ORIG, "ENGLOADS XENG/YENG/ZENG", "engine station",
       EXTERNAL + "the weight database (decision D-25 mass SSOT; review N1 instance 5: regional jet 130 in apart)",
       governs=True),
    _E("engines[].hub_weight_lb", _ENG, _ORIG, "ENGLOADS HUBWT"),
    _E("engines[].prop_weight_lb", _ENG, _ORIG, "ENGLOADS PROPWT", "propeller mass",
       EXTERNAL + "the weight database (the prop_mass_item row; note 36 OV-7, C210-41)",
       governs=True),
    _E("engines[].prop_cg", _ENG, _ORIG, "ENGLOADS XPROP/YPROP/ZPROP", "propeller station",
       EXTERNAL + "the weight database (the prop_mass_item row; note 36 OV-7, C210-41)",
       governs=True),
    _E("engines[].engine_mass_item", _ENG, _SLDS,
       "weight-database row selector, note 36 OV-7 (the D-25 mass SSOT linkage, stated where "
       "it is consumed; blank = no derivation, a name matching no row is refused)"),
    _E("engines[].prop_mass_item", _ENG, _SLDS,
       "weight-database row selector, note 36 OV-7 (the propeller half of the linkage)"),
    _E("engines[].prop_designation", _ENG, _ORIG, "ENGLOADS propeller designation"),
    _E("engines[].prop_diameter_in", _ENG, _ORIG, "ENGLOADS PROPDIA"),
    _E("engines[].prop_blades", _ENG, _ORIG, "ENGLOADS NOBLADES"),
    _E("engines[].prop_inertia", _ENG, _SLDS, "measured polar inertia override"),
    _E("engines[].cylinders", _ENG, _ORIG, "ENGLOADS CYL"),
    _E("engines[].takeoff_hp", _ENG, _ORIG, "ENGLOADS TOHP"),
    _E("engines[].takeoff_rpm", _ENG, _ORIG, "ENGLOADS TORPM"),
    _E("engines[].max_cont_hp", _ENG, _ORIG, "ENGLOADS MAXCONTHP"),
    _E("engines[].max_cont_rpm", _ENG, _ORIG, "ENGLOADS CONTRPM"),
    _E("engines[].max_engine_torque", _ENG, _ORIG, "ENGLOADS ENGTORQ"),
    _E("engines[].cruise_torque", _ENG, _ORIG, "ENGLOADS CRUZTORQ"),
    _E("engines[].stop_time_s", _ENG, _ORIG, "ENGLOADS DT (sudden stoppage)"),
    _E("engines[].limit_load_factor", _ENG, _ORIG, "ENGLOADS LIMNZ", "limit manoeuvre load factor",
       EXTERNAL + "the FAR 23.337 limit computed from speeds (review N1 instance 4)",
       governs=True),
    _E("engines[].max_accel_torque", _ENG, _SLDS, "FAR 25.361(a)(3)(ii), FAR 25 opt-in"),
    _E("engines[].thrust_lb", _ENG, _SLDS, "hub thrust, note 21 carve-out"),
    _E("engines[].design_pitch_rate_rad_s", _ENG, _SLDS, "concept real rate, 25.371"),
    _E("engines[].design_yaw_rate_rad_s", _ENG, _SLDS, "concept real rate, 25.371"),
    _E("engines[].rotors[].rotor_type", _ENG, _SLDS, "turbine rotor model, Step C9"),
    _E("engines[].rotors[].weight_lb", _ENG, _SLDS, "turbine rotor model, Step C9"),
    _E("engines[].rotors[].diameter_in", _ENG, _SLDS, "turbine rotor model, Step C9"),
    _E("engines[].rotors[].inertia", _ENG, _SLDS, "turbine rotor model, Step C9"),
    _E("engines[].rotors[].max_rpm", _ENG, _SLDS, "turbine rotor model, Step C9"),
    _E("engines[].rotors[].direction", _ENG, _SLDS, "turbine rotor model, Step C9"),
    # C210-44 (owner directive): layout is Step C5 *configuration*, not a
    # mount-load input -- its one calc consumer is WINGGEOM's engine stations --
    # so it renders on the Geometry page. The page set is registry-derived, so
    # the move is this tag; the Engine Mount page's layout-consistency message
    # resolves the owning page from this entry and follows automatically.
    _E("engine_layout", _GEO, _SLDS,
       "multi-engine layout constraint, Step C5 -- the arrangement the entered engines already "
       "describe, where the original ran one program per fixed layout. Load-bearing (G5): "
       "omitting it moves the twins' nacelle geometry", supplied=True),
    _E("include_far25", _ENG, _SLDS, "FAR 25 supplemental-case opt-in"),

    # one_engine_out -- ONENGOUT (one_engine_out)
    _E("one_engine_out.failed_engine_index", _OEI, _SLDS, "multi-engine index; ONENGOUT had one"),
    _E("one_engine_out.thrust_decay_time_s", _OEI, _ORIG, "ONENGOUT TIME2DECAY"),
    _E("one_engine_out.windmill_drag_time_s", _OEI, _ORIG, "ONENGOUT TIME2DRAG"),
    _E("one_engine_out.rudder_travel_time_s", _OEI, _ORIG, "ONENGOUT INCTIMERUD"),
    _E("one_engine_out.time_step_s", _OEI, _ORIG, "ONENGOUT DT (Euler step)"),
    _E("one_engine_out.use_takeoff_power", _OEI, _ORIG, "ONENGOUT MAXHP selector"),
    _E("one_engine_out.speeds_kt", _OEI, _ORIG, "ONENGOUT evaluation speeds"),
    _E("one_engine_out.altitude_ft", _OEI, _ORIG, "ONENGOUT altitude"),
    _E("one_engine_out.izz_slugft2", _OEI, _ORIG, "ONENGOUT IZZ (0 -> from mass)"),
    _E("one_engine_out.xcg_in", _OEI, _ORIG, "ONENGOUT XCG (0 -> from mass)"),

    # ----------------------------------------------------------------- #
    # landing -- LGFACTOR + LANDLOAD (landing_loads). **No gear-geometry block**:
    # it used to duplicate geometry.landing_gear wholesale, resolved at run time
    # onto an effective input copy. Note 33 (DS-1) removed the copies from
    # ``LandingInput`` outright, which is what OG-8 asked for -- one owner before
    # either copy reaches a page -- so the seventeen rows that stood here are the
    # ``geometry.landing_gear.*`` rows and nothing else.
    # ----------------------------------------------------------------- #
    _E("landing.lift_factor", _LAND, _ORIG, "LGFACTOR L"),
    # Replaced ``landing.gear_load_factor`` (note 37, LF-1/LF-12): the governing
    # airplane load factor N, entered where LANDLOAD runs at a rounded design
    # value (2.5 + 0.667 = 3.167 on p230); NLG = N - L is derived, never entered.
    # ``SLOADS``, honestly: LGFACTOR.BAS had an NLG override, never an N input.
    # The oracle GUI carries it regardless (C210-15), and the mark is earned:
    # demonstrably load-bearing (G5) -- omit it on ga6 and the p230 K/gamma/
    # reaction table moves off the oracle (NLG 2.4281 vs the printed 2.5).
    _E("landing.airplane_load_factor", _LAND, _SLDS,
       "governing N; None -> LGFACTOR energy value (demonstrably load-bearing, G5: "
       "ga6 p230 reproduces only at N 3.167)", supplied=True),
    _E("landing.strut_stroke_in", _LAND, _ORIG, "LGFACTOR SSTRUT"),
    _E("landing.tire_od_in", _LAND, _ORIG, "LGFACTOR OD"),
    _E("landing.hub_diameter_in", _LAND, _ORIG, "LGFACTOR ID"),
    _E("landing.tail_down_angle_deg", _LAND, _ORIG, "LANDLOAD GRA(3)"),

    # tail_mass -- the empennage surface-mass override (plan 09 T-3)
    _E("tail_mass[].surface", _WT, _SLDS,
       "row selector -- which tail surface the row describes; load-bearing (G5, #98): an "
       "unmatched row is refused by name where it used to be silently inert",
       supplied=True),
    _E("tail_mass[].panel_weight_lb", _WT, _SLDS, "empennage distributed inertia, plan 09 T-3"),
    _E("tail_mass[].weight_is_override", _WT, _SLDS, "empennage distributed inertia, plan 09 T-3"),
    _E("tail_mass[].control_load_mode", _WT, _SLDS, "empennage distributed inertia, plan 09 T-3"),
    _E("tail_mass[].hinges_span_in", _WT, _SLDS, "sbeam control-surface bridge station"),
    _E("tail_mass[].actuator_span_in", _WT, _SLDS, "sbeam control-surface bridge station"),
)

BY_PATH: Dict[str, FieldEntry] = {e.path: e for e in REGISTRY}


def entry(path: str) -> Optional[FieldEntry]:
    return BY_PATH.get(path)


def original_paths() -> Set[str]:
    """Field paths the oracle GUI *asks* for — the original suite's own inputs."""
    return {e.path for e in REGISTRY if e.origin is Origin.ORIGINAL}


def supplied_paths() -> Set[str]:
    """`SLOADS` field paths the oracle input set needs (:data:`SUPPLIED_RULE`)."""
    return {e.path for e in REGISTRY if e.supplied}


def display_only_paths() -> Set[str]:
    """Field paths that render disabled in the oracle GUI (:attr:`FieldEntry.display_only`)."""
    return {e.path for e in REGISTRY if e.display_only}


def oracle_input_paths() -> Set[str]:
    """Everything a project made by the oracle GUI carries — what G5 runs against."""
    return original_paths() | supplied_paths()


def structurally_required() -> Set[str]:
    """Field paths whose dataclass declares no default, so the record needs them.

    Not a judgement — read off ``dataclasses.fields``. Every one of these must be
    ``ORIGINAL`` or ``supplied``, because "omit it" is not available: there is no
    default to fall back to, only the absence of the whole record. The guard is
    in ``tests/test_field_registry.py``; without it the rule holds today only by
    accident, and a ``default_factory=list`` added to ``SurfaceInput`` one
    afternoon would quietly delete the wing from the oracle GUI's input set.
    """
    required = set()
    for path in schema_paths():
        field = field_at(path)
        if field is None:
            continue
        if (field.default is dataclasses.MISSING
                and field.default_factory is dataclasses.MISSING):
            required.add(path)
    return required


def record_of(path: str) -> str:
    """The dotted prefix of the record a field sits on (``""`` at ``Project`` level)."""
    return path.rsplit(".", 1)[0] if "." in path else ""


def omitted_records() -> Set[str]:
    """Record prefixes the oracle GUI never creates at all.

    A ``Rotor`` row is every bit as absent as a defaulted scalar when the second
    front-end does not offer turbine rotors: no field of the record is in its
    input set, so no such row exists to have required fields. This is what keeps
    :func:`structurally_required`'s guard from demanding a decision about a
    record nobody builds — omission happens at record level as well as at field
    level, and only the guard would confuse the two.
    """
    keep = oracle_input_paths()
    rows: Dict[str, List[FieldEntry]] = {}
    for e in REGISTRY:
        rows.setdefault(record_of(e.path), []).append(e)
    return {rec for rec, group in rows.items()
            if rec and not any(r.path in keep for r in group)}


def reduce_to_oracle_inputs(project: Project) -> Project:
    """A deep copy of ``project`` holding only what the oracle GUI would have set.

    Every field outside :func:`oracle_input_paths` is returned to the default its
    dataclass declares — which is precisely OG-13's promise from the other side:
    *"fields it does not expose keep their defaults."* This is gate G5's
    mechanism (``tests/test_oracle_inputs.py``), and it is here rather than in
    the test because it is registry knowledge: what the second front-end writes
    is a property of the table, not of one test's convenience.

    Structurally required fields (no declared default) are left as they are; the
    guard above makes that a rule rather than an accident.

    Three things go, not one (review 2026-08-22 PB-3): every field outside the
    input set, every **record** the GUI never creates (:func:`omitted_records`
    -- a turbine-rotor row with its required fields intact is not "reduced"),
    and the stored :data:`RESULT_SLICES`. What the GUI *would* have written on
    its own is then put back by :func:`sloads.derived.refresh_derived`, the
    same call the form makes after a persist, so the reduced project carries a
    ``mass`` slice exactly when a typed one would.
    """
    reduced = copy.deepcopy(project)
    _reduce(reduced, "", oracle_input_paths(), omitted_records())
    for name in RESULT_SLICES:
        _reset(reduced, next(f for f in dataclasses.fields(reduced) if f.name == name))
    refresh_derived(reduced)
    return reduced


def _reset(obj: object, field: "dataclasses.Field[object]") -> None:
    """``obj.<field>`` back to its declared default, if it declares one."""
    if field.default is not dataclasses.MISSING:
        setattr(obj, field.name, copy.deepcopy(field.default))
    elif field.default_factory is not dataclasses.MISSING:
        setattr(obj, field.name, field.default_factory())
    # no default: structurally required, guarded above


def _reduce(obj: object, prefix: str, keep: Set[str], omitted: Set[str]) -> None:
    for field in dataclasses.fields(obj):  # type: ignore[arg-type]
        path = prefix + field.name
        value = getattr(obj, field.name)
        if path in BY_PATH:
            if path not in keep and value is not None:
                _reset(obj, field)
            continue
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            if path in omitted:
                _reset(obj, field)
            else:
                _reduce(value, path + ".", keep, omitted)
        elif isinstance(value, list) and value and dataclasses.is_dataclass(value[0]):
            if path + LIST_MARKER in omitted:
                _reset(obj, field)
            else:
                for item in value:
                    _reduce(item, path + LIST_MARKER + ".", keep, omitted)


def paths_for_page(page: str) -> Set[str]:
    return {e.path for e in REGISTRY if e.page == page}


def quantities() -> Dict[str, List[FieldEntry]]:
    """Declared quantity -> every field holding it (owner first)."""
    grouped: Dict[str, List[FieldEntry]] = {}
    for e in REGISTRY:
        if e.quantity:
            grouped.setdefault(e.quantity, []).append(e)
    for rows in grouped.values():
        rows.sort(key=lambda e: (not e.is_owner, e.path))
    return grouped


def untagged() -> Set[str]:
    """Schema fields with no registry row — what gate G4 fails on."""
    return schema_paths() - set(BY_PATH)


def stale() -> Set[str]:
    """Registry rows naming a field the schema no longer has."""
    return set(BY_PATH) - schema_paths()


def entering_step(slice_name: str) -> Optional[str]:
    """The workflow step whose form enters ``slice_name``, or ``None``.

    The registry is what knows this: every input row names the ``page`` — a
    workflow step key — it is entered on, so "which page fills this slice"
    needs no second list to drift from. A slice split across pages answers with
    the **earliest** in workflow order, which is the one a user reaches first
    and so the one a "fill this first" pointer must name (#69).

    ``None`` for a slice no form enters (a result slice, or one derived only).
    """
    from sloads import workflow as wf  # local: workflow must not import upward

    pages = {e.page for e in REGISTRY if e.slice == slice_name}
    # Walked in workflow order rather than picked with a keyed ``min``: the
    # order is the answer, and a keyed built-in pick is what
    # ``tests/test_platform_stability.py`` exists to keep out of this package.
    for step in wf.STEPS:
        if step.key in pages:
            return step.key
    return None
