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
    #: ``origin`` is ``SLOADS``, but the oracle GUI **sets** it anyway, without
    #: asking — see :data:`SUPPLIED_RULE`. ``origin`` says who *asked* for a
    #: field; this says who *writes* it, and the two differ exactly where this
    #: model carries as data something the original carried by position (which
    #: surface a planform describes, which of LANDLOAD's three loadings a CG case
    #: is). The oracle GUI's input set is therefore ``ORIGINAL | supplied``
    #: (:func:`oracle_input_paths`), which is what gate G5 runs against.
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
        """
        return bool(self.owner_path) and not self.governs


#: ``derived_from`` prefix for a quantity owned outside the input-field set.
#: Several of the review's duplicate instances are this shape — the owner of
#: "engine count" is ``len(Project.engines)``, of "engine mass" the weight
#: database — so the registry has to be able to say *owned, but not by a field*
#: rather than either inventing an owner row or dropping the duplicate from view.
EXTERNAL = "external: "


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
#    `speeds.wing_surface`, `aero.surfaces[].name`, `aero_coeffs.*.name`,
#    `tail_mass[].surface` and friends exist because this model carries N
#    surfaces where the original carried a fixed one. The oracle GUI resolves
#    them positionally and never asks. The ones it must still *write* to make a
#    well-formed model carry ``supplied=True`` (see :data:`SUPPLIED_RULE`) —
#    building G5 showed "never asks" and "never sets" are not the same claim,
#    and the table was only making the first one.
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
       "overall length; summarised from geometry.fuselage.sections[].x when entered (Step M2-6)"),
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
       "weight.max_takeoff_weight_lb (MTOW SSOT G-14; review N1 instance 1)",
       governs=True),
    _E("geometry.empennage.vtail.izz_slugft2", _GEO, _ORIG, "SELECT IZZ (0 -> computed)"),
    _E("geometry.empennage.vtail.xv25", _GEO, _ORIG, "SELECT 25% v-tail MAC station"),
    _E("geometry.empennage.vtail.xv50", _GEO, _ORIG, "ONENGOUT camber-load station"),
    _E("geometry.empennage.vtail.vtail_root_waterline_z", _GEO, _SLDS, "v-tail root waterline, plan 09 (tail_span)"),

    # geometry.landing_gear -- the G6b single source
    _E("geometry.landing_gear.tread_in", _GEO, _ORIG, "LANDLOAD TREAD"),
    _E("geometry.landing_gear.main_gear.attach", _GEO, _SLDS, "trunnion node, gear free body Step 10"),
    _E("geometry.landing_gear.main_gear.axle_static", _GEO, _ORIG, "LANDLOAD static axle station"),
    _E("geometry.landing_gear.main_gear.axle_compressed", _GEO, _ORIG, "LANDLOAD compressed axle station"),
    _E("geometry.landing_gear.main_gear.axle_extended", _GEO, _ORIG, "LANDLOAD extended axle reference"),
    _E("geometry.landing_gear.main_gear.rolling_radius_in", _GEO, _ORIG, "LANDLOAD RM"),
    _E("geometry.landing_gear.main_gear.strut", _GEO, _ORIG, "LGFACTOR oleo/spring selector"),
    _E("geometry.landing_gear.main_gear.carrier", _GEO, _SLDS, "BODY|WING carrier, decision G-2"),
    _E("geometry.landing_gear.main_gear.weight_lb", _GEO, _SLDS, "leg weight, decision G-12a"),
    _E("geometry.landing_gear.nose_gear.attach", _GEO, _SLDS, "trunnion node, gear free body Step 10"),
    _E("geometry.landing_gear.nose_gear.axle_static", _GEO, _ORIG, "LANDLOAD static axle station"),
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
    _E("weight.envelope.gross_weight", _WT, _ORIG, "WTENV gross weight"),
    _E("weight.envelope.mac", _WT, _ORIG, "WTENV MAC", "wing MAC",
       EXTERNAL + "derived_geometry from the planform (Optional override here)",
       governs=True),
    _E("weight.envelope.xlemac", _WT, _ORIG, "WTENV LEMAC station"),
    _E("weight.envelope.fwd_gross_pct_mac", _WT, _ORIG, "WTENV forward gross CG limit"),
    _E("weight.envelope.aft_gross_pct_mac", _WT, _ORIG, "WTENV aft gross CG limit"),
    _E("weight.envelope.fwd_regardless_pct_mac", _WT, _ORIG, "WTENV forward-regardless CG limit"),
    _E("weight.envelope.fwd_regardless_weight", _WT, _ORIG, "WTENV forward-regardless weight"),
    _E("weight.envelope.fuselage_nose_x", _WT, _ORIG, "WTENV nose station"),
    _E("weight.envelope.fuselage_tail_x", _WT, _ORIG, "WTENV tail station"),
    _E("weight.envelope.wing_surface", _WT, _SLDS, "surface selector (standing ruling)"),
    # The *grid* is Step D5's consolidation, but the cases themselves are not:
    # "the four corners of the WTENV weight-cg envelope (FLTLOADS.BAS prompts for
    # four per configuration)". So the numbers are ORIGINAL and only the columns
    # carrying what the original expressed positionally are sloads' (G5).
    _E("weight.cg_cases[].name", _WT, _SLDS,
       "case selector, Step D5; structurally required", supplied=True),
    _E("weight.cg_cases[].role", _WT, _SLDS,
       "LANDLOAD's three loadings (UG fig 18.2), positional in the original, a column here (G-3a). "
       "Load-bearing (G5): without it LANDLOAD has no GROUND cases and does not run", supplied=True),
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
    # The one display-only copy (governs=False, #36): STRSPEED resolves the wing
    # planform first and only falls back to this field when the geometry carries no
    # wing surface -- which no project the GUI can build ever does. A value entered
    # here was therefore ignored, measured at an 18 % divergence on atr42. It renders
    # disabled, showing the area that actually governs.
    _E("speeds.wing_area_sqft", _SPD, _ORIG, "STRSPEED S (W/S)", "wing reference area",
       "geometry.parametric.wing_area_sqft (display-only: structural_speeds._wing_area_sqft "
       "prefers the planform and reaches this only with no wing surface -- #36)"),
    _E("speeds.wing_surface", _SPD, _SLDS, "surface selector (standing ruling)"),
    _E("speeds.vh_kt", _SPD, _ORIG, "STRSPEED VH, max level speed"),
    _E("speeds.shoulder_altitude_ft", _SPD, _ORIG,
       "STRSPEED MC/MD altitude; MACHLIM first row (one home since v55, #52)"),
    _E("speeds.chosen_vc", _SPD, _ORIG, "STRSPEED chosen VC, Appendix A p156"),
    _E("speeds.chosen_vd", _SPD, _ORIG, "STRSPEED chosen VD, Appendix A p156"),
    _E("speeds.chosen_va", _SPD, _ORIG, "STRSPEED chosen VA, Appendix A p156"),
    _E("speeds.chosen_vf", _SPD, _ORIG, "STRSPEED chosen VF, Appendix A p156"),
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
    _E("aero_coeffs.clmax_clean", _AERO, _ORIG, "STRSPEED/FLTLOADS CLmax, UG p7-5"),
    _E("aero_coeffs.clmax_clean_neg", _AERO, _ORIG, "FLTLOADS negative stall line"),
    _E("aero_coeffs.clmax_flap", _AERO, _ORIG, "STRSPEED/FLTLOADS flapped CLmax, UG p7-5"),
    _E("aero_coeffs.cruise.name", _AERO, _SLDS,
       "set selector (standing ruling); structurally required", supplied=True),
    _E("aero_coeffs.cruise.lift", _AERO, _ORIG, "FLTLOADS C0..C4"),
    _E("aero_coeffs.cruise.drag", _AERO, _ORIG, "FLTLOADS D0..D4"),
    _E("aero_coeffs.cruise.moment", _AERO, _ORIG, "FLTLOADS M0..M4"),
    _E("aero_coeffs.cruise.stall_cl", _AERO, _ORIG, "FLTLOADS set stall CL"),
    _E("aero_coeffs.cruise.neg_stall_cl", _AERO, _ORIG, "FLTLOADS set negative stall CL"),
    _E("aero_coeffs.cruise.flaps_down", _AERO, _ORIG, "FLTLOADS configuration flag"),
    _E("aero_coeffs.flaps_down.name", _AERO, _SLDS,
       "set selector (standing ruling); structurally required", supplied=True),
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
    _E("engine_layout", _ENG, _SLDS,
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
    _E("landing.gear_load_factor", _LAND, _ORIG, "LGFACTOR NLG override"),
    _E("landing.strut_stroke_in", _LAND, _ORIG, "LGFACTOR SSTRUT"),
    _E("landing.tire_od_in", _LAND, _ORIG, "LGFACTOR OD"),
    _E("landing.hub_diameter_in", _LAND, _ORIG, "LGFACTOR ID"),
    _E("landing.tail_down_angle_deg", _LAND, _ORIG, "LANDLOAD GRA(3)"),

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
    """Field paths the oracle GUI *asks* for — the original suite's own inputs."""
    return {e.path for e in REGISTRY if e.origin is Origin.ORIGINAL}


def supplied_paths() -> Set[str]:
    """`SLOADS` field paths the oracle GUI writes without asking (:data:`SUPPLIED_RULE`)."""
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
