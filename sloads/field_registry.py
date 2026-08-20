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

import dataclasses
import typing
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from sloads import models as _models
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
NON_INPUT: Dict[str, str] = {
    "envelope": "result slice (WTENV output)",
    "mass": "result slice (WTONECG output)",
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


#: ``derived_from`` prefix for a quantity owned outside the input-field set.
#: Several of the review's duplicate instances are this shape — the owner of
#: "engine count" is ``len(Project.engines)``, of "engine mass" the weight
#: database — so the registry has to be able to say *owned, but not by a field*
#: rather than either inventing an owner row or dropping the duplicate from view.
EXTERNAL = "external: "


def _E(path: str, page: str, origin: Origin, basis: str,
       quantity: str = "", derived_from: str = "") -> FieldEntry:
    return FieldEntry(path, page, origin, basis, quantity, derived_from)


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
#    `speeds.wing_surface`, `aero.surfaces[].name`, `aero_coeffs.*.name`,
#    `tail_mass[].surface` and friends exist because this model carries N
#    surfaces where the original carried a fixed one. The oracle GUI resolves
#    them positionally and never asks.
#  * **`origin` is about who *asked*, not who *computes*.** A field the original
#    entered directly and sloads now derives stays `ORIGINAL` and carries
#    ``derived_from`` (note 32, OG-7: an entered scalar wins and is marked). The
#    oracle GUI must still offer it; that is the whole point of OG-7.


REGISTRY: Tuple[FieldEntry, ...] = (
    # ----------------------------------------------------------------- #
    # geometry -- WINGGEOM (configuration_layout)
    # ----------------------------------------------------------------- #
    # The planform polyline model is this replication's (Step C5/G1); WINGGEOM
    # took planform *scalars*, which is what `parametric` holds. So the oracle
    # GUI offers `parametric` and never the polylines -- GR-GEOM-3's "planform
    # primary" runs the other way for the second front-end, by design.
    _E("geometry.surfaces[].name", _GEO, _SLDS, "surface selector (standing ruling)"),
    _E("geometry.surfaces[].leading_edge", _GEO, _SLDS, "polyline planform model, Step C5/G1"),
    _E("geometry.surfaces[].trailing_edge", _GEO, _SLDS, "polyline planform model, Step C5/G1"),
    _E("geometry.surfaces[].elements", _GEO, _SLDS, "polyline planform model, Step C5/G1"),
    _E("geometry.surfaces[].symmetric", _GEO, _SLDS, "polyline planform model, Step C5/G1"),
    _E("geometry.surfaces[].front_spar_pct", _GEO, _SLDS, "spar fractions, sbeam box model (Step C4)"),
    _E("geometry.surfaces[].rear_spar_pct", _GEO, _SLDS, "spar fractions, sbeam box model (Step C4)"),
    _E("geometry.surfaces[].ref_axis_pct", _GEO, _SLDS, "loads reference axis, R-7c"),
    _E("geometry.surfaces[].sob_y_in", _GEO, _SLDS, "side-of-body station, BM-1"),
    _E("geometry.parametric.wing_area_sqft", _GEO, _ORIG, "WINGGEOM reference area S", "wing reference area"),
    _E("geometry.parametric.aspect_ratio", _GEO, _ORIG, "WINGGEOM AR = b^2/S"),
    _E("geometry.parametric.taper_ratio", _GEO, _ORIG, "WINGGEOM tip/root chord"),
    _E("geometry.parametric.dihedral_deg", _GEO, _ORIG, "WINGGEOM geometric dihedral", "wing dihedral"),
    _E("geometry.parametric.le_sweep_deg", _GEO, _ORIG, "WINGGEOM/AIRLOAD4 leading-edge sweep"),
    _E("geometry.parametric.le_root_x", _GEO, _ORIG, "WINGGEOM centreline LE station"),
    _E("geometry.parametric.root_waterline_z", _GEO, _ORIG, "WINGGEOM root-chord waterline", "wing root waterline"),
    _E("geometry.parametric.datum_x", _GEO, _ORIG, "WINGGEOM nose datum reference"),
    _E("geometry.parametric.h_tail_z", _GEO, _ORIG, "SELECT h-tail vertical offset (Ch 9)"),
    _E("geometry.parametric.tail_type", _GEO, _SLDS, "layout sketch only, Step G1"),
    _E("geometry.parametric.body_drag_waterline_z", _GEO, _SLDS, "body-drag line, Step G4 balance work"),
    # Candidate 19th duplicate, NOT declared: this and SELECT's LF
    # (geometry.empennage.htail.airplane_length_in, quantity "airplane length")
    # are plausibly one dimension, but nothing in the repo says so and the two
    # are not held equal on any fixture. Declaring it would assert a defect that
    # has not been demonstrated; it is raised in the OG-C closure instead.
    _E("geometry.parametric.fuselage_length", _GEO, _ORIG,
       "overall length; summarised from geometry.fuselage.sections[].x when entered (Step M2-6)"),
    _E("geometry.parametric.fuselage_width", _GEO, _SLDS, "derived outline summary, Step M2-6"),
    _E("geometry.parametric.fuselage_height", _GEO, _SLDS, "derived outline summary, Step M2-6"),
    _E("geometry.fuselage.sections[].x", _GEO, _SLDS, "body outline model, Step G1"),
    _E("geometry.fuselage.sections[].width", _GEO, _SLDS, "body outline model, Step G1"),
    _E("geometry.fuselage.sections[].height", _GEO, _SLDS, "body outline model, Step G1"),
    _E("geometry.fuselage.sections[].z_centre", _GEO, _SLDS, "body outline model, Step G1"),

    # geometry.empennage.htail -- SELECT's rational h-tail inputs (Ch 9)
    _E("geometry.empennage.htail.airplane_length_in", _GEO, _ORIG, "SELECT LF", "airplane length"),
    _E("geometry.empennage.htail.aspect_ratio_htail", _GEO, _ORIG, "SELECT ARHT"),
    _E("geometry.empennage.htail.aspect_ratio_wing", _GEO, _ORIG, "SELECT ARW (downwash)"),
    _E("geometry.empennage.htail.htail_area_sqft", _GEO, _ORIG, "SELECT ST"),
    _E("geometry.empennage.htail.htail_semispan_in", _GEO, _ORIG, "SELECT BLHTAIL"),
    _E("geometry.empennage.htail.elevator_area_sqft", _GEO, _ORIG, "SELECT SE"),
    _E("geometry.empennage.htail.elevator_aft_hinge_sqft", _GEO, _ORIG, "SELECT SEAFTHL"),
    _E("geometry.empennage.htail.elevator_fwd_hinge_sqft", _GEO, _ORIG, "SELECT SEFWDHL"),
    _E("geometry.empennage.htail.elevator_te_down_deg", _GEO, _ORIG, "SELECT EDN"),
    _E("geometry.empennage.htail.elevator_te_up_deg", _GEO, _ORIG, "SELECT EUP"),
    _E("geometry.empennage.htail.elevator_effectiveness", _GEO, _ORIG, "SELECT dalpha/ddelta_e"),
    _E("geometry.empennage.htail.tail_incidence_deg", _GEO, _ORIG, "SELECT IT"),
    _E("geometry.empennage.htail.wing_lift_slope_per_rad", _GEO, _ORIG, "SELECT AW"),
    _E("geometry.empennage.htail.wing_zero_lift_cruise_deg", _GEO, _ORIG, "SELECT IW (cruise)"),
    _E("geometry.empennage.htail.wing_zero_lift_enroute_deg", _GEO, _ORIG, "SELECT IW (enroute)"),
    _E("geometry.empennage.htail.wing_zero_lift_landing_deg", _GEO, _ORIG, "SELECT IW (landing)"),
    _E("geometry.empennage.htail.xt25", _GEO, _ORIG, "SELECT 25% tail MAC station"),
    _E("geometry.empennage.htail.xt50", _GEO, _ORIG, "SELECT 50% tail MAC station"),

    # geometry.empennage.vtail -- SELECT's rational v-tail inputs (Ch 9)
    _E("geometry.empennage.vtail.airplane_length_in", _GEO, _ORIG, "SELECT LF", "airplane length",
       "geometry.empennage.htail.airplane_length_in (entered twice; review N1 instance 2)"),
    _E("geometry.empennage.vtail.aspect_ratio_vtail", _GEO, _ORIG, "SELECT ARVT"),
    _E("geometry.empennage.vtail.vtail_area_sqft", _GEO, _ORIG, "SELECT SV"),
    _E("geometry.empennage.vtail.vtail_mac_in", _GEO, _ORIG, "SELECT VMAC"),
    _E("geometry.empennage.vtail.vtail_span_in", _GEO, _ORIG, "SELECT BLHTAIL (v-tail span)"),
    _E("geometry.empennage.vtail.rudder_area_sqft", _GEO, _ORIG, "SELECT SR"),
    _E("geometry.empennage.vtail.rudder_aft_hinge_sqft", _GEO, _ORIG, "SELECT SRAFTHL"),
    _E("geometry.empennage.vtail.rudder_fwd_hinge_sqft", _GEO, _ORIG, "SELECT SRFWDHL"),
    _E("geometry.empennage.vtail.rudder_deflection_deg", _GEO, _ORIG, "SELECT RD"),
    _E("geometry.empennage.vtail.rudder_large_deflection_factor", _GEO, _ORIG, "SELECT EFV (subr 10000)"),
    _E("geometry.empennage.vtail.wing_span_in", _GEO, _ORIG, "SELECT B"),
    _E("geometry.empennage.vtail.gross_weight_lb", _GEO, _ORIG, "SELECT GW", "max take-off weight",
       "weight.max_takeoff_weight_lb (MTOW SSOT G-14; review N1 instance 1)"),
    _E("geometry.empennage.vtail.izz_slugft2", _GEO, _ORIG, "SELECT IZZ (0 -> computed)"),
    _E("geometry.empennage.vtail.xv25", _GEO, _ORIG, "SELECT 25% v-tail MAC station"),
    _E("geometry.empennage.vtail.xv50", _GEO, _ORIG, "ONENGOUT camber-load station"),
    _E("geometry.empennage.vtail.vtail_root_waterline_z", _GEO, _SLDS, "v-tail root waterline, plan 09 (tail_span)"),

    # geometry.landing_gear -- the G6b single source
    _E("geometry.landing_gear.tread_in", _GEO, _ORIG, "LANDLOAD TREAD", "gear tread"),
    _E("geometry.landing_gear.main_gear.attach", _GEO, _SLDS, "trunnion node, gear free body Step 10"),
    _E("geometry.landing_gear.main_gear.axle_static", _GEO, _ORIG,
       "LANDLOAD static axle station", "main-gear static axle"),
    _E("geometry.landing_gear.main_gear.axle_compressed", _GEO, _ORIG, "LANDLOAD compressed axle station"),
    _E("geometry.landing_gear.main_gear.axle_extended", _GEO, _ORIG, "LANDLOAD extended axle reference"),
    _E("geometry.landing_gear.main_gear.rolling_radius_in", _GEO, _ORIG, "LANDLOAD RM"),
    _E("geometry.landing_gear.main_gear.strut", _GEO, _ORIG, "LGFACTOR oleo/spring selector"),
    _E("geometry.landing_gear.main_gear.carrier", _GEO, _SLDS, "BODY|WING carrier, decision G-2"),
    _E("geometry.landing_gear.main_gear.weight_lb", _GEO, _SLDS, "leg weight, decision G-12a"),
    _E("geometry.landing_gear.nose_gear.attach", _GEO, _SLDS, "trunnion node, gear free body Step 10"),
    _E("geometry.landing_gear.nose_gear.axle_static", _GEO, _ORIG,
       "LANDLOAD static axle station", "nose-gear static axle"),
    _E("geometry.landing_gear.nose_gear.axle_compressed", _GEO, _ORIG, "LANDLOAD compressed axle station"),
    _E("geometry.landing_gear.nose_gear.axle_extended", _GEO, _ORIG, "LANDLOAD extended axle reference"),
    _E("geometry.landing_gear.nose_gear.rolling_radius_in", _GEO, _ORIG, "LANDLOAD RN"),
    _E("geometry.landing_gear.nose_gear.strut", _GEO, _ORIG, "LGFACTOR oleo/spring selector"),
    _E("geometry.landing_gear.nose_gear.carrier", _GEO, _SLDS, "BODY|WING carrier, decision G-2"),
    _E("geometry.landing_gear.nose_gear.weight_lb", _GEO, _SLDS, "leg weight, decision G-12a"),

    # ----------------------------------------------------------------- #
    # weight -- WTESTIMA / WTONECG / WTENV (weight_mass)
    # ----------------------------------------------------------------- #
    _E("weight.max_takeoff_weight_lb", _WT, _ORIG, "MTOW, every module's design weight", "max take-off weight"),
    _E("weight.max_landing_weight_lb", _WT, _ORIG, "MLW, LANDLOAD design landing weight"),
    _E("weight.estimation.airplane", _WT, _ORIG, "WTESTIMA airplane class"),
    _E("weight.estimation.engines", _WT, _ORIG, "WTESTIMA NOENGS", "engine count",
       EXTERNAL + "len(Project.engines) (review N1 instance 3: concept_heavy 2 vs 0)"),
    _E("weight.estimation.max_continuous_hp", _WT, _ORIG, "WTESTIMA HP", "max continuous power",
       EXTERNAL + "sum of engines[].max_cont_hp unless overridden"),
    _E("weight.estimation.override_max_continuous_hp", _WT, _SLDS, "override switch for the engine-sum derivation"),
    _E("weight.estimation.seats", _WT, _ORIG, "WTESTIMA SEATS"),
    _E("weight.estimation.crew", _WT, _SLDS, "FAR 23 seat-limit check, Step E1"),
    _E("weight.estimation.baggage_lb", _WT, _ORIG, "WTESTIMA BAG"),
    _E("weight.estimation.cruise_hours", _WT, _ORIG, "WTESTIMA HOURS"),
    _E("weight.estimation.pressurized", _WT, _ORIG, 'WTESTIMA P$ = "P"'),
    _E("weight.estimation.engine_weight_type", _WT, _SLDS, "engine-weight basis selector, Step D5"),
    _E("weight.items[].name", _WT, _ORIG, "WTONECG item name"),
    _E("weight.items[].weight_lb", _WT, _ORIG, "WTONECG item weight"),
    _E("weight.items[].x", _WT, _ORIG, "WTONECG item station"),
    _E("weight.items[].y", _WT, _ORIG, "WTONECG item butt line"),
    _E("weight.items[].z", _WT, _ORIG, "WTONECG item waterline"),
    _E("weight.items[].ixx", _WT, _SLDS, "per-item inertia; WTONECG summed point masses"),
    _E("weight.items[].iyy", _WT, _SLDS, "per-item inertia; WTONECG summed point masses"),
    _E("weight.items[].izz", _WT, _SLDS, "per-item inertia; WTONECG summed point masses"),
    _E("weight.items[].kind", _WT, _SLDS, "mass-model tagging, decision D-25"),
    _E("weight.items[].component", _WT, _SLDS, "component tag, plan 09 T-3"),
    _E("weight.items[].consumable", _WT, _SLDS, "loading model, decision D-25"),
    _E("weight.items[].wing_fraction", _WT, _SLDS, "wing/body split for CONM2 export, plan 11"),
    _E("weight.envelope.gross_weight", _WT, _ORIG, "WTENV gross weight"),
    _E("weight.envelope.mac", _WT, _ORIG, "WTENV MAC", "wing MAC",
       EXTERNAL + "derived_geometry from the planform (Optional override here)"),
    _E("weight.envelope.xlemac", _WT, _ORIG, "WTENV LEMAC station"),
    _E("weight.envelope.fwd_gross_pct_mac", _WT, _ORIG, "WTENV forward gross CG limit"),
    _E("weight.envelope.aft_gross_pct_mac", _WT, _ORIG, "WTENV aft gross CG limit"),
    _E("weight.envelope.fwd_regardless_pct_mac", _WT, _ORIG, "WTENV forward-regardless CG limit"),
    _E("weight.envelope.fwd_regardless_weight", _WT, _ORIG, "WTENV forward-regardless weight"),
    _E("weight.envelope.fuselage_nose_x", _WT, _ORIG, "WTENV nose station"),
    _E("weight.envelope.fuselage_tail_x", _WT, _ORIG, "WTENV tail station"),
    _E("weight.envelope.wing_surface", _WT, _SLDS, "surface selector (standing ruling)"),
    _E("weight.cg_cases[].name", _WT, _SLDS, "CG-case grid, Step D5 / decision D-25"),
    _E("weight.cg_cases[].role", _WT, _SLDS, "CG-case grid, Step D5 / decision D-25"),
    _E("weight.cg_cases[].weight_lb", _WT, _SLDS, "CG-case grid, Step D5 / decision D-25"),
    _E("weight.cg_cases[].xcg", _WT, _SLDS, "CG-case grid, Step D5 / decision D-25"),
    _E("weight.cg_cases[].zcg", _WT, _SLDS, "CG-case grid, Step D5 / decision D-25"),
    _E("weight.cg_cases[].analyses", _WT, _SLDS, "which analyses use this case, Step D5"),
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
       "weight.max_takeoff_weight_lb (read-through, Step D4.4; override checkbox)"),
    _E("speeds.wing_area_sqft", _SPD, _ORIG, "STRSPEED S (W/S)", "wing reference area",
       "geometry.parametric.wing_area_sqft (note 32 §8: nothing reads this copy)"),
    _E("speeds.wing_surface", _SPD, _SLDS, "surface selector (standing ruling)"),
    _E("speeds.vh_kt", _SPD, _ORIG, "STRSPEED VH, max level speed"),
    _E("speeds.shoulder_altitude_ft", _SPD, _ORIG, "STRSPEED MC/MD altitude", "shoulder altitude"),
    _E("speeds.chosen_vc", _SPD, _ORIG, "STRSPEED chosen VC, Appendix A p156"),
    _E("speeds.chosen_vd", _SPD, _ORIG, "STRSPEED chosen VD, Appendix A p156"),
    _E("speeds.chosen_va", _SPD, _ORIG, "STRSPEED chosen VA, Appendix A p156"),
    _E("speeds.chosen_vf", _SPD, _ORIG, "STRSPEED chosen VF, Appendix A p156"),
    _E("speeds.chosen_n", _SPD, _ORIG, "STRSPEED chosen n, Appendix A p156"),
    _E("speeds.chosen_nneg", _SPD, _ORIG, "STRSPEED chosen negative n, Appendix A p156"),
    _E("speeds.mach_limit.shoulder_altitude_ft", _SPD, _ORIG, "MACHLIM shoulder altitude", "shoulder altitude",
       "speeds.shoulder_altitude_ft (same quantity on two dataclasses)"),
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
    _E("aero_coeffs.clmax_clean", _AERO, _ORIG, "STRSPEED/FLTLOADS CLmax, UG p7-5"),
    _E("aero_coeffs.clmax_clean_neg", _AERO, _ORIG, "FLTLOADS negative stall line"),
    _E("aero_coeffs.clmax_flap", _AERO, _ORIG, "STRSPEED/FLTLOADS flapped CLmax, UG p7-5"),
    _E("aero_coeffs.cruise.name", _AERO, _SLDS, "set selector (standing ruling)"),
    _E("aero_coeffs.cruise.lift", _AERO, _ORIG, "FLTLOADS C0..C4"),
    _E("aero_coeffs.cruise.drag", _AERO, _ORIG, "FLTLOADS D0..D4"),
    _E("aero_coeffs.cruise.moment", _AERO, _ORIG, "FLTLOADS M0..M4"),
    _E("aero_coeffs.cruise.stall_cl", _AERO, _ORIG, "FLTLOADS set stall CL"),
    _E("aero_coeffs.cruise.neg_stall_cl", _AERO, _ORIG, "FLTLOADS set negative stall CL"),
    _E("aero_coeffs.cruise.flaps_down", _AERO, _ORIG, "FLTLOADS configuration flag"),
    _E("aero_coeffs.flaps_down.name", _AERO, _SLDS, "set selector (standing ruling)"),
    _E("aero_coeffs.flaps_down.lift", _AERO, _ORIG, "FLTLOADS C0..C4"),
    _E("aero_coeffs.flaps_down.drag", _AERO, _ORIG, "FLTLOADS D0..D4"),
    _E("aero_coeffs.flaps_down.moment", _AERO, _ORIG, "FLTLOADS M0..M4"),
    _E("aero_coeffs.flaps_down.stall_cl", _AERO, _ORIG, "FLTLOADS set stall CL"),
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
    _E("flight_loads.altitudes_ft", _VN, _ORIG, "FLTLOADS envelope altitudes"),
    _E("flight_loads.mn", _VN, _ORIG, "FLTLOADS gust/manoeuvre matrix"),
    _E("flight_loads.xtc", _VN, _ORIG, "FLTLOADS tail CP, cruise"),
    _E("flight_loads.xtf", _VN, _ORIG, "FLTLOADS tail CP, flapped"),
    _E("flight_loads.wing_area_sqft", _VN, _ORIG, "FLTLOADS S", "wing reference area",
       "geometry.parametric.wing_area_sqft (Step M2-6; synced by derived_geometry, not persisted)"),
    _E("flight_loads.mac", _VN, _ORIG, "FLTLOADS MAC", "wing MAC",
       EXTERNAL + "derived_geometry.sync_geometry_derived from the planform (Step M2-6; not persisted)"),
    _E("flight_loads.xw", _VN, _ORIG, "FLTLOADS wing CP station", "wing aerodynamic centre station",
       EXTERNAL + "derived_geometry.sync_geometry_derived from the planform (Step M2-6; not persisted)"),
    _E("flight_loads.zw", _VN, _ORIG, "FLTLOADS wing drag waterline", "wing drag waterline",
       EXTERNAL + "derived_geometry.sync_geometry_derived from the planform (Step M2-6; not persisted)"),

    # select_input -- SELECT beyond the V-n matrix (flight_envelope)
    _E("select_input.basic_airfoil_cm", _VN, _ORIG, "SELECT basic airfoil CM, Ch 9"),
    _E("select_input.full_down_aileron_deg", _VN, _ORIG, "SELECT full-down aileron, Ch 9"),
    _E("select_input.wing_weight_lb", _VN, _ORIG, "SELECT wing weight, Ch 9"),

    # ----------------------------------------------------------------- #
    # aero -- AIRLOADS/AIRLOAD4/TAU per-surface inputs (wing_loads)
    # ----------------------------------------------------------------- #
    _E("aero.surfaces[].name", _WING, _SLDS, "surface selector (standing ruling)"),
    _E("aero.surfaces[].section_slope", _WING, _ORIG, "AIRLOADS mo"),
    _E("aero.surfaces[].profile_drag", _WING, _ORIG, "AIRLOADS CDO(Y)"),
    _E("aero.surfaces[].section_cm", _WING, _ORIG, "AIRLOADS CM(Y)"),
    _E("aero.surfaces[].twist", _WING, _ORIG, "AIRLOADS zero-lift angle(Y)"),
    _E("aero.surfaces[].taper_ratio", _WING, _ORIG, "TAU taper ratio"),
    _E("aero.surfaces[].tip_ratio", _WING, _ORIG, "TAU rounded-tip ratio"),
    _E("aero.surfaces[].tau", _WING, _ORIG, "TAU output, enterable as an override"),
    _E("aero.surfaces[].target_cl", _WING, _ORIG, "AIRLOADS evaluation CL"),
    _E("aero.surfaces[].sweep_deg", _WING, _ORIG, "AIRLOAD4 sweepback"),
    _E("aero.surfaces[].design_mach", _WING, _ORIG, "AIRLOAD4 high-Mach branch"),

    # wing_mass -- WINGINER (wing_loads)
    _E("wing_mass.surface", _WING, _SLDS, "surface selector (standing ruling)"),
    _E("wing_mass.panel_weight_lb", _WING, _ORIG, "WINGINER panel weight"),
    _E("wing_mass.inboard_rib_y", _WING, _ORIG, "WINGINER inboard rib station"),
    _E("wing_mass.tip_root_density_ratio", _WING, _ORIG, "WINGINER tip/root density ratio"),
    _E("wing_mass.dihedral_deg", _WING, _ORIG, "WINGINER dihedral", "wing dihedral",
       "geometry.parametric.dihedral_deg (Step M2-6; synced, not persisted)"),
    _E("wing_mass.wrp_waterline", _WING, _ORIG, "WINGINER wing reference-plane waterline", "wing root waterline",
       "geometry.parametric.root_waterline_z (Step M2-6; synced, not persisted)"),
    _E("wing_mass.concentrated[].name", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].weight_lb", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].x", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].y", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.concentrated[].z", _WING, _ORIG, "WINGINER concentrated item"),
    _E("wing_mass.cases[].name", _WING, _ORIG, "WINGINER.BAS 1660-1710 case name"),
    _E("wing_mass.cases[].case", _WING, _ORIG, "WINGINER.BAS 1660-1710 case id"),
    _E("wing_mass.cases[].nz", _WING, _ORIG, "WINGINER.BAS 1660-1710 nz"),
    _E("wing_mass.cases[].nx", _WING, _ORIG, "WINGINER.BAS 1660-1710 nx"),
    _E("wing_mass.cases[].cl", _WING, _ORIG, "WINGINER.BAS 1660-1710 CL"),
    _E("wing_mass.cases[].v_eas_kt", _WING, _ORIG, "WINGINER.BAS 1660-1710 speed"),
    _E("wing_mass.cases[].unbal_moment", _WING, _ORIG, "WINGINER.BAS 1660-1710 unbalanced moment"),

    # fuselage_mass -- NETLOADS / Ch 15 (fuselage_loads)
    _E("fuselage_mass.ref_waterline", _FUS, _ORIG, "Ch 15 reference waterline"),
    _E("fuselage_mass.stations[].x", _FUS, _ORIG, "Ch 15 station"),
    _E("fuselage_mass.stations[].weight_lb", _FUS, _ORIG, "Ch 15 station weight"),
    _E("fuselage_mass.stations_are_override", _FUS, _SLDS, "override switch for the weight-DB derivation"),

    # ----------------------------------------------------------------- #
    # Control-surface pages. The span-station fields are NOT .BAS inputs:
    # PROGRAM_SPEC says AILERON's only upstream input per UG Table 2.2 is the
    # deflections + areas; the stations feed the sbeam control-surface bridge.
    # ----------------------------------------------------------------- #
    _E("aileron_loads.surface", _AIL, _SLDS, "surface selector (standing ruling)"),
    _E("aileron_loads.area_aft_hinge_sqft", _AIL, _ORIG, "AILERON SAAFT"),
    _E("aileron_loads.area_fwd_hinge_sqft", _AIL, _ORIG, "AILERON SAFWD"),
    _E("aileron_loads.up_deflection_deg", _AIL, _ORIG, "AILERON AUPDEG"),
    _E("aileron_loads.down_deflection_deg", _AIL, _ORIG, "AILERON ADEG"),
    _E("aileron_loads.inboard_y_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("aileron_loads.outboard_y_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("aileron_loads.hinges_span_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("aileron_loads.actuator_span_in", _AIL, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.surface", _FLAP, _SLDS, "surface selector (standing ruling)"),
    _E("flap_loads.flap_area_one_side_sqft", _FLAP, _ORIG, "FLAPLOAD SF"),
    _E("flap_loads.flap_chord_ratio", _FLAP, _ORIG, "FLAPLOAD E"),
    _E("flap_loads.flap_deflection_deg", _FLAP, _ORIG, "FLAPLOAD DELTA"),
    _E("flap_loads.gust_load_factor", _FLAP, _ORIG, "FLAPLOAD NG"),
    _E("flap_loads.nacelle_frontal_area_sqft", _FLAP, _ORIG, "FLAPLOAD AF"),
    _E("flap_loads.engine_butt_line_in", _FLAP, _ORIG, "FLAPLOAD BLPROP"),
    _E("flap_loads.inboard_y_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.outboard_y_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.hinges_span_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("flap_loads.actuator_span_in", _FLAP, _SLDS, "sbeam control-surface bridge station"),
    _E("tab_loads.tabs[].surface", _TAB, _SLDS, "surface selector (standing ruling)"),
    _E("tab_loads.tabs[].area_sqft", _TAB, _ORIG, "TABLOADS STAB"),
    _E("tab_loads.tabs[].mac_in", _TAB, _ORIG, "TABLOADS MACTAB"),
    _E("tab_loads.tabs[].airfoil_chord_in", _TAB, _ORIG, "TABLOADS CAIRFOIL"),
    _E("tab_loads.tabs[].deflection_deg", _TAB, _ORIG, "TABLOADS DELTATAB"),
    _E("tab_loads.tabs[].station_in", _TAB, _ORIG, "TABLOADS BL/WL of the tab MAC"),

    # ----------------------------------------------------------------- #
    # engines -- ENGLOADS (engine_mount)
    # ----------------------------------------------------------------- #
    _E("engines[].engine_designation", _ENG, _ORIG, "ENGLOADS engine designation"),
    _E("engines[].engine_type", _ENG, _SLDS, "recip/turboprop selector, Step C9"),
    _E("engines[].mounted_on", _ENG, _SLDS, "fuselage/wing carrier, Step C5"),
    _E("engines[].engine_weight_lb", _ENG, _ORIG, "ENGLOADS ENGWT", "engine mass",
       EXTERNAL + "the weight database (decision D-25 mass SSOT; review N1 instance 5: regional jet 300 lb apart)"),
    _E("engines[].engine_cg", _ENG, _ORIG, "ENGLOADS XENG/YENG/ZENG", "engine station",
       EXTERNAL + "the weight database (decision D-25 mass SSOT; review N1 instance 5: regional jet 130 in apart)"),
    _E("engines[].hub_weight_lb", _ENG, _ORIG, "ENGLOADS HUBWT"),
    _E("engines[].prop_weight_lb", _ENG, _ORIG, "ENGLOADS PROPWT"),
    _E("engines[].prop_cg", _ENG, _ORIG, "ENGLOADS XPROP/YPROP/ZPROP"),
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
       EXTERNAL + "the FAR 23.337 limit computed from speeds (review N1 instance 4)"),
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
    _E("engine_layout", _ENG, _SLDS, "multi-engine layout constraint, Step C5"),
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
    # landing -- LGFACTOR + LANDLOAD (landing_loads). The gear-geometry block
    # duplicates geometry.landing_gear wholesale: OG-8's "one owner before it
    # is put on an oracle page", resolved at run time onto an effective input
    # (G6b) rather than by a second entry.
    # ----------------------------------------------------------------- #
    _E("landing.lift_factor", _LAND, _ORIG, "LGFACTOR L"),
    _E("landing.gear_load_factor", _LAND, _ORIG, "LGFACTOR NLG override"),
    _E("landing.strut_stroke_in", _LAND, _ORIG, "LGFACTOR SSTRUT"),
    _E("landing.tire_od_in", _LAND, _ORIG, "LGFACTOR OD"),
    _E("landing.hub_diameter_in", _LAND, _ORIG, "LGFACTOR ID"),
    _E("landing.tail_down_angle_deg", _LAND, _ORIG, "LANDLOAD GRA(3)"),
    _E("landing.tread_in", _LAND, _ORIG, "LANDLOAD TREAD", "gear tread",
       "geometry.landing_gear.tread_in (G6b effective-input resolution)"),
    _E("landing.wing_area_sqft", _LAND, _ORIG, "LANDLOAD S", "wing reference area",
       "geometry.parametric.wing_area_sqft (Step M2-6; synced, not persisted)"),
    _E("landing.main_gear.attach", _LAND, _SLDS, "trunnion node, gear free body Step 10",
       "", "geometry.landing_gear.main_gear.attach (G6b effective-input resolution)"),
    _E("landing.main_gear.axle_static", _LAND, _ORIG, "LANDLOAD static axle station", "main-gear static axle",
       "geometry.landing_gear.main_gear.axle_static (G6b effective-input resolution)"),
    _E("landing.main_gear.axle_compressed", _LAND, _ORIG, "LANDLOAD compressed axle station",
       "", "geometry.landing_gear.main_gear.axle_compressed (G6b)"),
    _E("landing.main_gear.axle_extended", _LAND, _ORIG, "LANDLOAD extended axle reference",
       "", "geometry.landing_gear.main_gear.axle_extended (G6b)"),
    _E("landing.main_gear.rolling_radius_in", _LAND, _ORIG, "LANDLOAD RM",
       "", "geometry.landing_gear.main_gear.rolling_radius_in (G6b)"),
    _E("landing.main_gear.strut", _LAND, _ORIG, "LGFACTOR oleo/spring selector",
       "", "geometry.landing_gear.main_gear.strut (G6b)"),
    _E("landing.main_gear.carrier", _LAND, _SLDS, "BODY|WING carrier, decision G-2",
       "", "geometry.landing_gear.main_gear.carrier (G6b)"),
    _E("landing.main_gear.weight_lb", _LAND, _SLDS, "leg weight, decision G-12a",
       "", "geometry.landing_gear.main_gear.weight_lb (G6b)"),
    _E("landing.nose_gear.attach", _LAND, _SLDS, "trunnion node, gear free body Step 10",
       "", "geometry.landing_gear.nose_gear.attach (G6b effective-input resolution)"),
    _E("landing.nose_gear.axle_static", _LAND, _ORIG, "LANDLOAD static axle station", "nose-gear static axle",
       "geometry.landing_gear.nose_gear.axle_static (G6b effective-input resolution)"),
    _E("landing.nose_gear.axle_compressed", _LAND, _ORIG, "LANDLOAD compressed axle station",
       "", "geometry.landing_gear.nose_gear.axle_compressed (G6b)"),
    _E("landing.nose_gear.axle_extended", _LAND, _ORIG, "LANDLOAD extended axle reference",
       "", "geometry.landing_gear.nose_gear.axle_extended (G6b)"),
    _E("landing.nose_gear.rolling_radius_in", _LAND, _ORIG, "LANDLOAD RN",
       "", "geometry.landing_gear.nose_gear.rolling_radius_in (G6b)"),
    _E("landing.nose_gear.strut", _LAND, _ORIG, "LGFACTOR oleo/spring selector",
       "", "geometry.landing_gear.nose_gear.strut (G6b)"),
    _E("landing.nose_gear.carrier", _LAND, _SLDS, "BODY|WING carrier, decision G-2",
       "", "geometry.landing_gear.nose_gear.carrier (G6b)"),
    _E("landing.nose_gear.weight_lb", _LAND, _SLDS, "leg weight, decision G-12a",
       "", "geometry.landing_gear.nose_gear.weight_lb (G6b)"),

    # tail_mass -- the empennage surface-mass override (plan 09 T-3)
    _E("tail_mass[].surface", _WT, _SLDS, "surface selector (standing ruling)"),
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
    """Field paths the oracle GUI offers — the input set gate G5 runs against."""
    return {e.path for e in REGISTRY if e.origin is Origin.ORIGINAL}


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
