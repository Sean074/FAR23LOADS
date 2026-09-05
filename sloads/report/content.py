"""The report's content model: ``Project`` + module results -> :class:`ReportDocument`.

Step G8.4. This module answers *what the report says*; :mod:`sloads.report.latex`
answers *how it looks*. Keeping the two apart is what lets a test assert
``doc.section("1. Input summary").subsection("Design speeds").table.rows`` instead
of matching LaTeX strings, and lets the renderer stay a dumb, fully-covered string
function.

Three rules govern everything below (``docs/10_standard/SUMMARY_REPORT.md``):

* **Nothing is recomputed here.** Every figure comes from the same pure builder
  the GUI pages and the sbeam bridge use -- ``run_all_modules``,
  ``build_net_loads``/``loads_ref_axis_results``, ``build_body_loads``,
  ``build_tail_chordwise``, the control-surface builders, ``build_vn_diagram``,
  ``loading_envelope_points``, ``mach_limit_lines``, ``governing_loads_table``.
  A report that computed its own values would eventually disagree with the
  exports it accompanies (SUMMARY_REPORT.md §5).
* **Every load is LIMIT, stated, and located.** Loads are the calc's own values
  (note 49 OR-116): nothing here is scaled, each row states the
  ``safety_factor`` a sizing analysis must apply, and each names the
  station/case it occurs at. The ``-ULT`` marker survives only on the two
  families the regulation prescribes already ultimate (OR-118). Envelopes are
  two-sided. Non-load quantities (weights, geometry, speeds, load factors) take
  no factor at all.
* **Absence is content.** A section whose inputs are missing carries an
  ``absent_reason`` and is still rendered, with that reason. It is never silently
  dropped and never rendered as an empty table (SUMMARY_REPORT.md §3.4).

Pure: no filesystem, no subprocess, no Streamlit, no clock. ``generated`` is a
caller-supplied string, so two builds of the same project are identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .. import cg_cases
from ..case_ids import ASSEMBLED_DECK, COMPONENT_DECK, NO_LOAD_ID
from ..constants import IN_PER_FT, ULTIMATE_FACTOR
from ..models import SCHEMA_VERSION, Project, VdBasis
from ..units import (
    HUMAN_SI,
    Channel,
    DeliverableUnits,
    UnitSystem,
    deliverable_units,
    system_name,
    units_statement,
)
from .coverage import (
    COVERED,
    NOT_ANALYSED,
    NOT_APPLICABLE,
    OUT_OF_SCOPE,
    coverage_matrix,
    coverage_summary,
)
from .methods import APPROVED_CORRECTIONS, TOOL_NAME, methods_statement
from .render import format_value, governing_loads_table, ultimate_units

#: Errors a defensive build step tolerates. Same set the Export page catches: a
#: half-filled project must yield a report with "not analysed" sections, never a
#: traceback -- the report is how an engineer *finds* the gaps.
_CALC_ERRORS = (ValueError, ZeroDivisionError, KeyError, IndexError, TypeError)

#: The document's numbered sections, in order: ``(key, bare title)``. **This is
#: the single source of the report's section numbering** (CLAUDE.md practice 3).
#: Headings come from :func:`section_heading` and every cross-reference — in
#: rendered prose and in the manifest's "Summarised in" column — from
#: :func:`section_ref`, so inserting a section renumbers its references with it.
#: Written after review finding **F-R2**: the §2 sign-conventions insertion left
#: three manifest rows pointing one section short, and the §6 balanced insertion
#: moved methods to §7 without touching them, because each number was a literal
#: typed in two places. ``Appendix A`` is not here — an appendix is lettered and
#: never renumbers.
SECTIONS = (
    ("inputs", "Input summary"),
    ("conventions", "Axes and sign conventions"),
    ("factors", "Governing safety factors"),
    ("envelopes", "Envelope figures"),
    ("conditions", "Conditions analysed and FAR coverage"),
    ("results", "Results summary"),
    ("balanced", "Balanced free-free airframe cases"),
    ("gear", "Landing gear interface loads"),
    ("methods", "Methods and limitations"),
)
_SECTION_NO = {key: i for i, (key, _) in enumerate(SECTIONS, start=1)}


def section_heading(key: str) -> str:
    """``"4. Conditions analysed and FAR coverage"`` — the numbered heading."""
    return f"{_SECTION_NO[key]}. {dict(SECTIONS)[key]}"


def section_ref(key: str, suffix: str = "") -> str:
    """``"§4"`` — a cross-reference to a section, or ``"§5 Wing"`` with a suffix.

    Never write ``"§4"`` as a literal in rendered text: a reference that does not
    come through here is a reference that will not move when a section is
    inserted above it (F-R2).
    """
    return f"§{_SECTION_NO[key]}" + (f" {suffix}" if suffix else "")


#: The one-line load-basis statement, on the title page and in §5 (§3.1).
BASIS_STATEMENT = (
    "All loads are LIMIT; the safety factor of 14 CFR 23.303 is stated per case "
    "and applied nowhere in sloads, including the exported deck — apply it in "
    "the sizing analysis. Load factors are limit."
)

#: Non-converted, non-scaled aviation-standard units (§3.5).
AVIATION_UNITS_NOTE = (
    "Airspeed is KEAS and altitude is ft in both unit systems (aviation standard, "
    "never converted)."
)


# --------------------------------------------------------------------------- #
# The content model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Table:
    """One rendered table: a caption, column headers and pre-formatted cells.

    Cells are **strings**: the content layer owns formatting (and therefore the
    unit conversion and the limit->ultimate scaling), so the renderer cannot
    accidentally reformat a load. ``units`` belong in the column header, never in
    the cell (§3.5).

    ``status_column`` names a column whose value classifies the row (the coverage
    matrix's ``Status``); the renderer uses it to make "not analysed" rows
    visually distinct, which §4.4 requires.
    """

    title: str
    columns: List[str]
    rows: List[List[str]]
    note: str = ""
    small: bool = False
    status_column: str = ""
    #: Relative path of a generated ``.tex`` fragment holding this table's body,
    #: for a report delivered as a **package** (design note 44 OR-23). Empty --
    #: the default, and what every summary-report table uses -- means the rows
    #: are written inline, which is what ``SUMMARY_REPORT.md`` §2 requires of a
    #: standalone ``.tex``. Carrying the mode on the table rather than on the
    #: document is deliberate: a packaged report still writes its title-block and
    #: control tables inline, so "external" is a property of one table's data,
    #: never of the document.
    data_ref: str = ""


@dataclass(frozen=True)
class Series:
    """One named polyline of a figure. ``style`` is a line style, never a colour --
    figures must stay legible in greyscale (§4.3).

    ``closed`` says the polyline bounds a **region** -- a planform outline, a
    control surface -- rather than tracing a line through the figure. An emitter
    that fills or closes a path reads it; the default is an ordinary open
    polyline, which is what every plotted curve is. It exists because a planform
    figure carries both kinds at once: the wing outline is a closed region and
    the loads reference axis drawn on it is not, and closing the axis would cut
    a chord from tip back to root that no part of the airplane follows.
    """

    name: str
    x: List[float]
    y: List[float]
    style: str = "solid"
    closed: bool = False


@dataclass(frozen=True)
class PlotData:
    """The data of one figure, in the renderer-agnostic form ``plots_tex`` consumes."""

    x_label: str
    y_label: str
    series: List[Series] = field(default_factory=list)
    #: Labelled point markers (e.g. the design CG cases).
    points: List[Tuple[str, float, float]] = field(default_factory=list)
    #: Labelled vertical reference lines (e.g. the fwd/aft CG limits).
    vlines: List[Tuple[str, float]] = field(default_factory=list)
    #: The legend entry :attr:`points` are drawn under.
    #:
    #: Defaulted to the weight/CG figure's wording, which was the only user when
    #: the marker series was written and which had it hard-coded in the emitter.
    #: The oracle report's V-n diagrams mark gust design points with the same
    #: mechanism, and inheriting a legend that named somebody else's figure was
    #: how that showed up (GUI review, 2026-08-30).
    points_label: str = "Design CG cases"


@dataclass(frozen=True)
class Figure:
    """A figure plus the corner-point table §4.3 requires beside it.

    ``data is None`` means the figure could not be built; ``absent_reason`` then
    says why, and the section renders that sentence instead of an empty axis.

    There is deliberately no ``data_ref`` here yet, though :attr:`Table.data_ref`
    exists: an axis that reads a shipped CSV has to name the *columns* it plots,
    and that schema is defined by the emitter that writes the first plotted
    section's data. Adding the field before the schema exists would be guessing
    at it in the one place a wrong guess is expensive to undo.
    """

    key: str
    title: str
    data: Optional[PlotData] = None
    caption: str = ""
    absent_reason: str = ""


@dataclass
class Section:
    """One numbered section: prose paragraphs, tables, figures, subsections."""

    title: str
    body: List[str] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    subsections: List["Section"] = field(default_factory=list)
    absent_reason: str = ""
    #: The bold lead the renderer puts in front of ``absent_reason``.
    #:
    #: Defaults to the summary report's single reason for a missing section --
    #: it was not analysed. The oracle report has *four* section states (design
    #: note 44 OR-32) that must not borrow each other's wording, because each
    #: names a different party's decision: leading a not-yet-implemented section
    #: with "Not analysed" tells the reader their data was incomplete when it was
    #: the tool that was.
    absent_lead: str = "Not analysed"
    #: Start this section on a fresh page. Back matter is reference material a
    #: reader turns to rather than reads through, so an appendix that begins
    #: halfway down the last page of the section before it reads as a
    #: continuation of it. Set by the appendix builder, not by section content.
    page_break: bool = False
    #: Render this section rotated. A station-by-station applied-load table is
    #: wide because a load needs its point as well as its components, and
    #: shrinking the type to fit is the wrong trade for a table meant to be read
    #: number by number. Applies to the whole section, so one appendix has one
    #: orientation throughout.
    landscape: bool = False

    @property
    def table(self) -> Optional[Table]:
        """The section's first table (the common case), or ``None``."""
        return self.tables[0] if self.tables else None

    def subsection(self, title: str) -> Optional["Section"]:
        """The direct subsection whose title matches ``title`` (case-insensitive)."""
        for s in self.subsections:
            if s.title.lower() == title.lower():
                return s
        return None


@dataclass
class ReportDocument:
    """The whole document: title-page control block plus the ordered sections."""

    title: str
    project_name: str
    #: (label, value) rows of the document-control block, in reading order.
    control: List[Tuple[str, str]] = field(default_factory=list)
    #: "FAR 23 (normal)" or "Concept (C) - unverified extrapolation".
    badge: str = ""
    basis: str = BASIS_STATEMENT
    units_note: str = ""
    sections: List[Section] = field(default_factory=list)
    #: The shared methods & limitations statement, verbatim (§4.6).
    methods: str = ""
    system: UnitSystem = UnitSystem.IMPERIAL

    def section(self, title: str) -> Optional[Section]:
        """The section (or subsection, at any depth) whose title matches ``title``.

        Matching is case-insensitive and ignores a leading ``"N. "`` number, so a
        test can ask for ``"Input summary"`` without pinning the numbering.
        """
        want = _bare_title(title)
        stack: List[Section] = list(self.sections)
        while stack:
            s = stack.pop(0)
            if _bare_title(s.title) == want:
                return s
            stack = list(s.subsections) + stack
        return None


def _bare_title(title: str) -> str:
    head, _, tail = title.partition(" ")
    return (tail if head.rstrip(".").replace(".", "").isdigit() else title).strip().lower()


# --------------------------------------------------------------------------- #
# Unit helpers -- one resolved set per document (M4-20)
# --------------------------------------------------------------------------- #
#: Dimensions the deliverable unit set does not carry, because they are not load
#: dimensions: (Imperial->SI factor, Imperial label, SI label). The factors are
#: ``units.HUMAN_SI``'s (the one owner, CH-7); only the ASCII labels a report
#: prints live here.
_EXTRA_DIMENSIONS = {
    "mass": (HUMAN_SI["mass"].factor, "lb", "kg"),
    "area": (HUMAN_SI["area_sqft"].factor, "ft^2", "m^2"),
    "inertia": (HUMAN_SI["inertia_slugft2"].factor, "slug-ft^2", "kg*m^2"),
    "inertia_lbin2": (HUMAN_SI["inertia_lbin2"].factor, "lb-in^2", "kg*m^2"),
}

#: Imperial unit string -> the :class:`DeliverableUnits` dimension it scales with.
#: A bare ``"lb"`` is pounds-force here; a weight sets ``quantity="mass"`` and is
#: excluded by :func:`_load_dimension`, exactly as in ``render.py``.
_UNIT_DIMENSION = {
    "lb": "force",
    "ft-lb": "torque",
    "lb-in": "moment",
    "lb/in^2": "pressure",
}


class Units:
    """The document's resolved unit set, plus the conversions the tables need.

    One instance per document, built from ``deliverable_units(system,
    Channel.HUMAN)`` -- the report is a human-readable deliverable, so it reports
    moments in N*m and pressures in kPa, never the solver deck's N*mm/MPa (D-19).
    Imperial is the all-1.0 identity, so an Imperial report is byte-for-byte what
    it was before M4-20.
    """

    def __init__(self, system: UnitSystem) -> None:
        self.system = system
        self.d: DeliverableUnits = deliverable_units(system, Channel.HUMAN)

    # -- plain (non-load) quantities: converted, never scaled, never marked --- #
    def plain(self, value: Any, dim: str) -> str:
        """A non-load quantity formatted in the document's units (no ``-ULT``).

        ``value`` is typed loosely because an absent quantity reaches here as
        ``None`` *or* as the empty string the result types use for "this
        component does not apply"; both render as an empty cell rather than a
        zero, which would read as a measurement.
        """
        if value is None or value == "":
            return ""
        return format_value(value * self._factor(dim))

    def label(self, dim: str) -> str:
        """The plain unit label for ``dim`` (``"in"``/``"mm"``, ``"lb"``/``"kg"``...)."""
        if dim in _EXTRA_DIMENSIONS:
            _, imperial, si = _EXTRA_DIMENSIONS[dim]
            return imperial if self.system == UnitSystem.IMPERIAL else si
        return getattr(self.d, dim).label

    def ult_label(self, dim: str, sf: float = 0.0) -> str:
        """The unit label for a load dimension.

        LIMIT is the project's only basis (note 49 OR-116), so a load's label is
        plain and its factor is stated in the row's ``SF`` cell. A load computed
        **already ultimate** (``sf == 1.0``) keeps the ``-ULT`` marker, which is
        now rare enough to be conspicuous (OR-118).
        """
        label = getattr(self.d, dim).label
        return ultimate_units(label) if sf == 1.0 else label

    def load(self, value: Any, dim: str, sf: float) -> str:
        """A LIMIT load, converted only -- ``sf`` is stated, not applied (OR-116).

        Same loose typing as :meth:`plain`, for the same reason.
        """
        if value is None or value == "":
            return ""
        return format_value(self.load_value(value, dim, sf))

    # -- the same two conversions as numbers, for a figure's axis ------------ #
    #
    # A plotted load goes through the boundary exactly as a tabulated one does:
    # the figure and the table beside it are then the same number drawn two
    # ways, and neither can be the one that forgot to scale.
    def load_value(self, value: float, dim: str, sf: float) -> float:
        """A LIMIT load in the document's units.

        ``sf`` is retained in the signature because every caller has it and the
        row states it; it is **not** applied (note 49 OR-116).
        """
        del sf  # stated by the caller's SF cell, never applied
        return value * getattr(self.d, dim).factor

    def plain_value(self, value: float, dim: str) -> float:
        """A non-load quantity as a number in the document's units."""
        return value * self._factor(dim)

    def _factor(self, dim: str) -> float:
        if dim in _EXTRA_DIMENSIONS:
            return 1.0 if self.system == UnitSystem.IMPERIAL else _EXTRA_DIMENSIONS[dim][0]
        return getattr(self.d, dim).factor


def _load_dimension(units: str, quantity: str = "") -> Optional[str]:
    """The deliverable dimension a LoadValue scales with, or ``None`` if not a load."""
    if quantity == "mass":
        return None
    return _UNIT_DIMENSION.get(units)


# --------------------------------------------------------------------------- #
# Component loads -- the live recompute the report and the bundle share
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ComponentLoads:
    """The four distributed-load families, recomputed from the current inputs.

    The Export page and the report build these the same way, through this one
    function, so a bundle's report can never describe different numbers from the
    CSV/BDF files beside it. Wing results are already transferred to the wing's
    loads reference axis (LRA) -- every reported wing torsion is about that axis.
    """

    wing: List[Any] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)
    tail: List[Any] = field(default_factory=list)
    control: List[Any] = field(default_factory=list)
    #: SELECT's governing conditions, recomputed live (``build_critical``) exactly
    #: as the Critical Loads and Results Review pages do -- not read off
    #: ``Project.envelope.critical``, which is only as fresh as the last page
    #: visit and is absent altogether on a project loaded from JSON.
    critical: List[Any] = field(default_factory=list)


def _try(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except _CALC_ERRORS:
        return None


def component_loads(project: Project) -> ComponentLoads:
    """Recompute the wing / fuselage / tail / control-surface distributed loads.

    Defensive by design: a component whose inputs are absent yields an empty list
    rather than an exception, so a partially-filled project still reports on the
    components it *can* cover.
    """
    from ..modules.aileron import build_aileron
    from ..modules.body_loads import build_body_loads
    from ..modules.flap import build_flap
    from ..modules.net_loads import build_net_loads, loads_ref_axis_results
    from ..modules.select import build_critical
    from ..modules.tab import build_tabs
    from ..modules.taildist import build_tail_chordwise
    from ..safety_factors import stamp

    critical = _try(build_critical, project)
    net = _try(build_net_loads, project)
    wing = loads_ref_axis_results(project, net.wing_net) if net is not None else None
    control: List[Any] = []
    for fn in (build_aileron, build_flap, build_tabs):
        control += _try(fn, project) or []
    out = ComponentLoads(
        wing=wing or [],
        body=_try(build_body_loads, project) or [],
        tail=_try(build_tail_chordwise, project) or [],
        control=control,
        critical=list(critical.conditions) if critical is not None else [],
    )
    # The governing safety-factor table is written onto the carrier here, at the
    # one boundary every front-end shares (M4-8 / G-11). Without this a project
    # override would move the report's SF column and leave the deck's SF= marker
    # and its scaled cards behind it -- the defect class review finding F-R1
    # closed. With no override (every shipped fixture) it is a no-op that writes
    # back exactly the factor the producer minted.
    stamp(project, out.wing, out.body, out.tail, out.control, out.critical)
    return out


@dataclass(frozen=True)
class BalancedRun:
    """The assembled balanced deliverable, built **once** per document.

    ``cases is None`` means the balancer could not run at all (an absent input
    slice), which is a different statement from "it ran and assembled nothing" --
    both are reported, neither is silence. ``skipped`` is the F-C7 record: the
    SELECT conditions that did not become a balanced case, and why.

    One instance is shared by §4's skipped-conditions table and §6's balanced
    section, so the two cannot describe different runs of the same assembly (and
    the assembly, which recomputes the wing at each V-n point, is paid for once).
    """

    cases: Optional[List[Any]] = None
    skipped: List[Any] = field(default_factory=list)


def balanced_run(project: Project) -> BalancedRun:
    """Assemble the balanced free-free cases, defensively (see :class:`BalancedRun`)."""
    from ..modules.balance import build_balanced_cases
    from ..safety_factors import stamp

    skipped: List[Any] = []
    cases = _try(build_balanced_cases, project, skipped)
    stamp(project, cases or [])
    return BalancedRun(cases=cases, skipped=skipped)


# --------------------------------------------------------------------------- #
# §1 Input summary
# --------------------------------------------------------------------------- #
def _input_table(title: str, rows: List[Tuple[str, str, str, str]], note: str = "") -> Table:
    """An input table: quantity / value / units / the page that owns it (§3.2)."""
    return Table(
        title=title,
        columns=["Quantity", "Value", "Units", "Owned by"],
        rows=[list(r) for r in rows if r[1] != ""],
        note=note,
    )


def _configuration_section(project: Project) -> Section:
    from ..applicability import effective_crew, effective_occupants

    speeds = project.speeds
    est = project.weight.estimation if project.weight is not None else None
    rows: List[Tuple[str, str, str, str]] = [
        ("Certification category", (speeds.category if speeds else "") or "(not set)",
         "", "Structural Speeds"),
        ("Engine layout",
         project.engine_layout.value if project.engine_layout is not None else "",
         "", "Configuration & Layout"),
        ("Engine count", str(len(project.engines)) if project.engines else "",
         "", "Configuration & Layout"),
    ]
    for i, eng in enumerate(project.engines, start=1):
        tag = f"Engine {i}" if len(project.engines) > 1 else "Engine"
        rows.append((f"{tag} designation", eng.engine_designation or "", "", "Engine Mount"))
        rows.append((f"{tag} propeller", eng.prop_designation or "", "", "Engine Mount"))
        rows.append((f"{tag} type",
                     "turbopropeller" if eng.is_turboprop else "reciprocating",
                     "", "Engine Mount"))
    occupants = effective_occupants(project)
    rows += [
        ("Occupants", str(occupants) if occupants is not None else "", "", "Structural Speeds"),
        ("Flight crew", str(effective_crew(project)), "", "Weight & Mass Properties"),
        ("Seats", str(est.seats) if est is not None and est.seats else "",
         "", "Weight & Mass Properties"),
        ("FAR 25 optional cases", "included" if project.include_far25 else "not included",
         "", "Engine Mount"),
    ]
    return Section("Configuration", tables=[_input_table("Configuration", rows)])


def _geometry_section(project: Project, u: Units) -> Section:
    from ..derived_geometry import fuselage_summary, wing_reference

    geom = project.geometry
    if geom is None:
        return Section("Geometry", absent_reason="this project has no geometry slice")

    L, A, DEG = u.label("length"), u.label("area"), "deg"
    rows: List[Tuple[str, str, str, str]] = []
    wing = wing_reference(project)
    par = geom.parametric
    if wing is not None:
        rows += [
            ("Wing area S", u.plain(wing.s_sqft, "area"), A, "Geometry"),
            ("Wing MAC", u.plain(wing.mac, "length"), L, "Geometry"),
            ("MAC leading-edge station XLEMAC", u.plain(wing.xlemac, "length"), L, "Geometry"),
            ("25% MAC station XW", u.plain(wing.xw, "length"), L, "Geometry"),
            ("25% MAC waterline ZW", u.plain(wing.zw, "length"), L, "Geometry"),
            ("Wing dihedral", format_value(wing.dihedral_deg), DEG, "Configuration & Layout"),
        ]
    if par is not None:
        rows += [
            ("Wing span b", u.plain(_span_in(project), "length"), L, "Geometry"),
            ("Aspect ratio", format_value(par.aspect_ratio) if par.aspect_ratio else "",
             "", "Configuration & Layout"),
            ("Taper ratio", format_value(par.taper_ratio) if par.taper_ratio else "",
             "", "Configuration & Layout"),
            ("Leading-edge sweep", format_value(par.le_sweep_deg), DEG, "Configuration & Layout"),
            ("Empennage arrangement", par.tail_type.value if par.tail_type else "",
             "", "Configuration & Layout"),
        ]
    surf = geom.by_name("wing")
    if surf is not None:
        rows.append(("Wing loads reference axis (LRA)",
                     format_value(surf.ref_axis * 100.0), "% chord", "Geometry"))
        if surf.front_spar_pct is not None:
            rows.append(("Front spar", format_value(surf.front_spar_pct * 100.0),
                         "% chord", "Geometry"))
        if surf.rear_spar_pct is not None:
            rows.append(("Rear spar", format_value(surf.rear_spar_pct * 100.0),
                         "% chord", "Geometry"))

    ht, vt = project.tail_loads, project.vtail_loads
    if ht is not None:
        rows += [
            ("Horizontal-tail area ST", u.plain(ht.htail_area_sqft, "area"), A, "Empennage"),
            ("Horizontal-tail semi-span", u.plain(ht.htail_semispan_in, "length"), L, "Empennage"),
            ("Horizontal-tail aspect ratio", format_value(ht.aspect_ratio_htail), "", "Empennage"),
            ("Elevator area SE", u.plain(ht.elevator_area_sqft, "area"), A, "Empennage"),
        ]
    if vt is not None:
        rows += [
            ("Vertical-tail area SV", u.plain(vt.vtail_area_sqft, "area"), A, "Empennage"),
            ("Vertical-tail span", u.plain(vt.vtail_span_in, "length"), L, "Empennage"),
            ("Vertical-tail MAC", u.plain(vt.vtail_mac_in, "length"), L, "Empennage"),
            ("Rudder area SR", u.plain(vt.rudder_area_sqft, "area"), A, "Empennage"),
        ]
    gear = geom.landing_gear
    if gear is not None:
        rows += [
            ("Main-gear axle station (static)",
             u.plain(gear.main_gear.axle_static[0], "length"), L, "Landing Gear"),
            ("Main-gear axle waterline (static)",
             u.plain(gear.main_gear.axle_static[1], "length"), L, "Landing Gear"),
            ("Nose-gear axle station (static)",
             u.plain(gear.nose_gear.axle_static[0], "length"), L, "Landing Gear"),
            ("Tread (main-wheel track)", u.plain(gear.tread_in, "length"), L, "Landing Gear"),
        ]
    fuse = fuselage_summary(geom.fuselage)
    if fuse is not None:
        length, width, height = fuse
        rows += [
            ("Fuselage length", u.plain(length, "length"), L, "Configuration & Layout"),
            ("Fuselage maximum width", u.plain(width, "length"), L, "Configuration & Layout"),
            ("Fuselage maximum depth", u.plain(height, "length"), L, "Configuration & Layout"),
        ]
    return Section("Geometry", tables=[_input_table("Geometry", rows)])


def _span_in(project: Project) -> Optional[float]:
    """Wing span (in) from the WINGGEOM surface, or ``None``."""
    geom = project.geometry
    surf = geom.by_name("wing") if geom is not None else None
    if surf is None:
        return None
    from ..modules.wing_geometry import surface_properties

    res = _try(surface_properties, surf)
    if res is None:
        return None
    for v in res.values:
        if v.key == "span":
            return v.value
    return None


def _weights_section(project: Project, u: Units) -> Section:
    W, L = u.label("mass"), u.label("length")
    weight = project.weight
    if weight is None:
        return Section("Weights and CG",
                       absent_reason="this project has no weight slice")
    rows: List[Tuple[str, str, str, str]] = []
    # The item sum is the CEILING of empty weight <= MLW <= MTOW <= sum(items), not the
    # design take-off weight (decision G-14) -- it was labelled "Maximum takeoff
    # weight (item sum)" until 2026-08-15, which is the conflation that item
    # closed. MTOW itself comes from its single owner and is stated beside it.
    database_total, empty, _ = weight.database_totals() if weight.items else (0.0, 0.0, 0.0)
    mtow = cg_cases.max_takeoff_weight(project, required=False)
    if mtow:
        rows.append(("Maximum takeoff weight (MTOW)", u.plain(mtow, "mass"), W,
                     "Weight & Mass Properties"))
    if database_total:
        rows += [
            ("Item database total (ceiling, not MTOW)", u.plain(database_total, "mass"), W,
             "Weight & Mass Properties"),
            ("Empty weight (item sum)", u.plain(empty, "mass"), W, "Weight & Mass Properties"),
        ]
    env = weight.envelope
    if env is not None:
        rows += [
            ("Design gross weight", u.plain(env.gross_weight, "mass"), W, "Weight & Mass Properties"),
            ("Aft CG limit", format_value(env.aft_gross_pct_mac), "% MAC", "Weight & Mass Properties"),
            ("Forward CG limit (gross)", format_value(env.fwd_gross_pct_mac), "% MAC",
             "Weight & Mass Properties"),
            ("Forward CG limit (regardless)", format_value(env.fwd_regardless_pct_mac), "% MAC",
             "Weight & Mass Properties"),
        ]
    for c in weight.cg_cases:
        rows.append((f"Design CG case '{c.name}'",
                     f"{u.plain(c.weight_lb, 'mass')} {W} at {u.plain(c.xcg, 'length')} {L}",
                     "", "Weight & Mass Properties"))

    tables = [_input_table("Weights and CG", rows)]
    mass = project.mass
    if mass is not None and mass.cases:
        inertia_u = u.label("inertia_lbin2")
        tables.append(Table(
            title="Mass properties per loading (WTONECG)",
            columns=["Loading", f"Weight ({W})", f"CG x ({L})", f"CG z ({L})",
                     f"Iyy ({inertia_u})", f"Izz ({inertia_u})", "Gear"],
            rows=[[
                c.name,
                u.plain(c.weight_lb, "mass"),
                u.plain(c.cg_x, "length"),
                u.plain(c.cg_z, "length"),
                u.plain(c.iyy, "inertia_lbin2"),
                u.plain(c.izz, "inertia_lbin2"),
                "down" if c.gear_down else "up",
            ] for c in mass.cases],
            note="Provenance: computed per CG case by WTONECG from the itemized "
                 "weight database (not the Ch 9 approximation).",
        ))
    else:
        tables.append(Table(
            title="Mass properties per loading (WTONECG)",
            columns=["Loading", "Status"],
            rows=[["(none)", "not analysed — no persisted WTONECG mass cases; any "
                             "inertia used downstream is the Ch 9 approximation"]],
        ))
    return Section("Weights and CG", tables=tables)


def _speeds_section(project: Project) -> Section:
    """Design speeds, each with its FAR reference and whether it was user-set."""
    speeds = project.speeds
    if speeds is None:
        return Section("Design speeds",
                       absent_reason="this project has no design-speed slice")
    from ..modules.structural_speeds import design_speed_values

    sv = _try(design_speed_values, project, speeds)
    if sv is None:
        return Section("Design speeds",
                       absent_reason="the design speeds could not be "
                                     "computed from the inputs present")

    def origin(chosen) -> str:
        return "user-specified" if chosen is not None else "derived (FAR minimum)"

    def _vd_far(sv) -> str:
        return "25.335(b)" if sv.vd_basis is VdBasis.MACH_MARGIN else "23.335(b)"

    def _vd_origin(speeds, sv) -> str:
        """VD's origin has to name its *route*, not just whether it was typed in --
        the same chosen VD survives on one route and is overridden on the other."""
        if sv.vd_basis is not VdBasis.MACH_MARGIN:
            return origin(speeds.chosen_vd)
        raised = speeds.chosen_vd is not None and sv.vd > speeds.chosen_vd * (1 + 1e-9)
        return "Mach-margin route" + (", raised to meet the margin" if raised else "")

    rows = [
        ["VS (clean stall)", format_value(sv.vs), "23.335", "derived from CLmax"],
        ["VSF (flapped stall)", format_value(sv.vsf), "23.335", "derived from CLmax"],
        ["VA (manoeuvre)", format_value(sv.va), "23.335(c)", origin(speeds.chosen_va)],
        ["VC (cruise)", format_value(sv.vc), "23.335(a)", origin(speeds.chosen_vc)],
        ["VD (dive)", format_value(sv.vd), _vd_far(sv), _vd_origin(speeds, sv)],
        ["VF (flap)", format_value(sv.vf), "23.345(b)", origin(speeds.chosen_vf)],
    ]
    # MC/MD are derived from VC/VD at the shoulder altitude by STRSPEED (F25-2);
    # they used to be read off the stale ``speeds.mach_limit`` copy, which the GUI
    # had already stopped honouring.
    if speeds.shoulder_altitude_ft:
        rows += [
            ["MC (cruise Mach)", format_value(sv.mc), "23.335(b)(4)", "derived at shoulder alt"],
            ["MD (dive Mach)", format_value(sv.md), "23.335(b)(4)", "derived at shoulder alt"],
        ]
    if sv.vd_basis is VdBasis.MACH_MARGIN:
        rows.append(["MD - MC (dive Mach margin)", format_value(sv.mach_margin),
                     "25.335(b)(2)",
                     f"required {format_value(sv.mach_margin_required)}"
                     + (" — REDUCED, rational analysis" if sv.mach_margin_reduced else "")])
    if speeds.vb_kt:
        rows.append(["VB (rough air)", format_value(speeds.vb_kt), "25.335(d)",
                     "user-specified (input only)"])
    tables = [Table(
        title="Design speeds",
        columns=["Speed", "Value (KEAS)", "FAR", "Origin"],
        rows=rows,
        note=AVIATION_UNITS_NOTE + " Mach numbers are dimensionless.",
    ), Table(
        title="Limit manoeuvre load factors",
        columns=["Quantity", "Value", "FAR minimum", "FAR"],
        rows=[
            ["n (positive)", format_value(sv.n), format_value(sv.n_min), "23.337(a)"],
            ["n (negative)", format_value(sv.nneg), format_value(sv.nneg_min), "23.337(b)"],
        ],
        note="Load factors are LIMIT and dimensionless — they are never scaled to "
             "ultimate and carry no unit marker (§3.1).",
    )]
    return Section("Design speeds", tables=tables)


def _aero_section(project: Project) -> Section:
    aero = project.aero_coeffs
    if aero is None:
        return Section("Aerodynamic data",
                       absent_reason="this project has no aerodynamic-coefficient slice")
    rows: List[Tuple[str, str, str, str]] = [
        ("CLmax clean", format_value(aero.clmax_clean), "", "Aerodynamic Data"),
        ("CLmax clean (negative)", format_value(aero.clmax_clean_neg), "", "Aerodynamic Data"),
        ("CLmax flapped", format_value(aero.clmax_flap), "", "Aerodynamic Data"),
    ]
    for name, cset in (("cruise", aero.cruise), ("flaps down", aero.flaps_down)):
        if cset is None:
            continue
        lift = getattr(cset, "lift", None)
        moment = getattr(cset, "moment", None)
        if lift:
            rows.append((f"Lift curve ({name}) CL0, CLalpha",
                         ", ".join(format_value(v) for v in lift), "per deg", "Aerodynamic Data"))
        if moment:
            rows.append((f"Moment curve ({name}) CM set",
                         ", ".join(format_value(v) for v in moment), "", "Aerodynamic Data"))
    fm = aero.fuselage_moment
    rows.append(("Fuselage dCm/dalpha (Munk)",
                 "enabled" if fm is not None and getattr(fm, "enabled", True) else "not enabled",
                 "", "Aerodynamic Data"))
    return Section("Aerodynamic data", tables=[_input_table("Aerodynamic data", rows)])


def _section_inputs(project: Project, u: Units) -> Section:
    return Section(
        section_heading("inputs"),
        body=["The airplane analysed, in enough detail to confirm identity. Each row "
              "names the page that owns the value, so a wrong number is traceable to "
              "one screen."],
        subsections=[
            _configuration_section(project),
            _geometry_section(project, u),
            _weights_section(project, u),
            _speeds_section(project),
            _aero_section(project),
        ],
    )


# --------------------------------------------------------------------------- #
# §2 Axes and sign conventions (SUMMARY_REPORT.md §4.2.1; design note 15)
def _section_conventions() -> Section:
    """The global sign-convention statement: prose, table and three figures.

    Everything here is read from :mod:`.conventions_tex`, the single source
    (CLAUDE.md rule 3) — this function only arranges it. It takes no project:
    the conventions are identical in every report, so the section can never be
    absent (§3.4 has nothing to say about it).
    """
    from .conventions_tex import CONVENTION_ROWS, CONVENTION_TABLE_NOTE, CONVENTIONS_PROSE

    return Section(
        section_heading("conventions"),
        body=list(CONVENTIONS_PROSE),
        figures=[
            Figure(key="sign_axes", title="Reference frame and state signs",
                   caption="x +aft, y +starboard, z +up (right-handed, identity "
                           "to the solver CID 0); +α nose-up, +β wind from "
                           "starboard; moment senses as drawn"),
            Figure(key="sign_controls", title="Control and rotation signs",
                   caption="elevator TE-down +, rudder TE-to-port + (left "
                           "pedal), aileron hand per case; clockwise from the "
                           "pilot's view + for rotation"),
            Figure(key="sign_beams", title="Shear, moment and torsion diagram "
                                           "conventions",
                   caption="wing integrated tip to root, body nose to tail, "
                           "fin loaded in fy; torsion axes named per figure"),
        ],
        tables=[Table(
            title="Sign conventions of record",
            columns=["Quantity", "Positive sense", "Charter"],
            rows=[list(r) for r in CONVENTION_ROWS],
            note=CONVENTION_TABLE_NOTE,
        )],
    )


# --------------------------------------------------------------------------- #
# §3 Governing safety factors
# --------------------------------------------------------------------------- #
_FACTORS_PROSE = (
    "Every load in this report and in the exported decks is a LIMIT value. The "
    "row below that governs its condition gives the factor a sizing analysis "
    "must apply to it; sloads states that factor and never applies it. "
    "This table is the authority: the per-case SF stated in the case index "
    "(§CASEREF), in the load-case CSVs and on each deck's SUBCASE header is a "
    "derived view of it, so a report figure and its bulk-data card cannot state "
    "different factors for the same case.",
    "Rows are condition families, not cases, and the family boundaries are 14 CFR "
    "Subpart C's own section groupings — so a case cannot be missed by omitting a "
    "row. The factor is prescribed for load quantities only: load factors, "
    "speeds, weights and geometry take none, and nothing here is scaled by it.",
)

_FACTORS_TABLE_NOTE = (
    "Status 'derived' is the regulation's own value. 'override' is a project-"
    "supplied replacement, which must state a basis and is repeated in the "
    "methods & limitations statement so it reaches a reader who sees only one "
    "file. 'defaulted' would mean a condition this table could not classify, "
    "factored at the conservative 1.5 and flagged; no shipped configuration "
    "produces one."
)


def _factors_section(project: Project, module_results, comps: ComponentLoads,
                     run: "BalancedRun") -> Section:
    """The governing safety-factor table (M4-8 / decision G-11).

    The table is built from :mod:`sloads.safety_factors`, the single code owner,
    and the *same* object is asked to classify every case the document carries —
    so the "defaulted" line below is a live statement about this run rather than a
    claim about the code.
    """
    from ..safety_factors import GoverningTable

    table = GoverningTable.for_project(project)
    for group in ([comps.wing, comps.body, comps.tail, comps.control, comps.critical]
                  + [mr.conditions for mr in module_results] + [run.cases or []]):
        for item in group:
            table.factor_for(item)

    body = [p.replace("§CASEREF", section_ref("conditions")) for p in _FACTORS_PROSE]
    if table.has_overrides:
        body.append(
            "This project overrides " +
            ", ".join(f"'{r.label}' to SF = {format_value(r.factor)} "
                      f"(regulation: {format_value(r.derived_factor)})"
                      for r in table.overrides) +
            ". An override cannot move a number in this report or on a deck — "
            "sloads applies no factor anywhere — but it does change the factor "
            "stated under that row, and so the ultimate load a sizing analysis "
            "will derive from it.")
    if table.defaulted:
        body.append(
            "DEFAULTED: " + ", ".join(repr(r) for r in table.defaulted) +
            " — condition(s) no row classified. They state "
            f"{format_value(ULTIMATE_FACTOR)} and are flagged here; treat this as a "
            "defect in the governing table, not a property of the airplane.")
    return Section(
        section_heading("factors"),
        body=body,
        tables=[Table(
            title="Governing safety factors of record",
            columns=["Family", "FAR", "Load class", "SF", "Status", "Basis"],
            rows=[[r.label, r.far_reference, r.load_class, format_value(r.factor),
                   r.status, r.basis] for r in table.rows],
            small=True,
            note=_FACTORS_TABLE_NOTE,
        )],
    )


# --------------------------------------------------------------------------- #
# §4 Envelope figures
# --------------------------------------------------------------------------- #
def _vn_figure(project: Project) -> Tuple[Figure, Optional[Table]]:
    from ..modules.structural_speeds import design_speed_values
    from ..vn_diagram import build_vn_diagram, gust_load_factor, resolve_gust_inputs

    speeds = project.speeds
    sv = _try(design_speed_values, project, speeds) if speeds is not None else None
    if sv is None:
        return (Figure("vn", "V-n diagram",
                       absent_reason="the design speeds this diagram is "
                                     "built from could not be computed"), None)

    aero = project.aero_coeffs
    slope = aero.cruise.lift[1] if aero is not None and aero.cruise is not None else None
    mac_ft = None
    from ..derived_geometry import wing_reference

    wing = wing_reference(project)
    if wing is not None and wing.mac:
        mac_ft = wing.mac / IN_PER_FT
    altitude = 0.0
    if project.flight_loads is not None and project.flight_loads.altitudes_ft:
        altitude = project.flight_loads.altitudes_ft[0]
    gust = resolve_gust_inputs(sv.ws, altitude, slope, mac_ft)
    diagram = build_vn_diagram(
        vs=sv.vs, va=sv.va, vc=sv.vc, vd=sv.vd, n_pos=sv.n, n_neg=sv.nneg,
        vsf=sv.vsf, vf=sv.vf, flaps="both", gust=gust,
    )
    styles = ("solid", "dashed", "dotted", "dashdotted", "densely dashed", "densely dotted")
    series = [
        Series(t.name, list(t.v), list(t.n), styles[i % len(styles)])
        for i, t in enumerate(diagram.traces)
    ]
    caption = (
        f"Manoeuvre and gust V-n envelope at {format_value(altitude)} ft. Load "
        "factors are LIMIT and dimensionless."
    )
    if diagram.gust_approximate:
        caption += (" The gust lines are APPROXIMATE: a default lift-curve slope "
                    "and/or no gust-alleviation factor was substituted because the "
                    "aero/geometry inputs were absent.")

    corner_rows = []
    for label, v in (("VS", sv.vs), ("VSF", sv.vsf), ("VA", sv.va), ("VC", sv.vc),
                     ("VD", sv.vd), ("VF", sv.vf)):
        if label in ("VC", "VD"):
            ref = "C" if label == "VC" else "D"
            n_gust_up = gust_load_factor(v, ref, gust, 1.0)
            n_gust_dn = gust_load_factor(v, ref, gust, -1.0)
            governs = "gust" if abs(n_gust_up) > abs(sv.n) else "manoeuvre"
            corner_rows.append([label, format_value(v), format_value(sv.n),
                                format_value(sv.nneg), format_value(n_gust_up),
                                format_value(n_gust_dn), governs])
        elif label == "VF":
            corner_rows.append([label, format_value(v), format_value(min(2.0, sv.n)),
                                "0", "—", "—", "manoeuvre (flaps, 23.337(b))"])
        else:
            corner_rows.append([label, format_value(v), format_value(sv.n),
                                format_value(sv.nneg), "—", "—", "manoeuvre"])
    table = Table(
        title="V-n corner points",
        columns=["Speed", "V (KEAS)", "n+ (manoeuvre)", "n- (manoeuvre)",
                 "n+ (gust)", "n- (gust)", "Governs"],
        rows=corner_rows,
        note=AVIATION_UNITS_NOTE,
    )
    return Figure("vn", "V-n diagram",
                  data=PlotData("V (KEAS)", "Load factor n", series),
                  caption=caption), table


#: The structural-limit corners, in the order they close the polygon.
#:
#: The forward limit is **piecewise**: constant at the forward-regardless station
#: below the reduced weight, then linear in weight up to the forward-gross
#: station at gross (`PROGRAM_SPEC` WTENV / M4-17c, the same relation
#: ``validation.wtenv_fwd_cg_limit_at_weight`` evaluates). Joining the anchors
#: with a straight segment *is* that interpolation, so the polygon is five WTENV
#: outputs connected, not a sixth quantity computed here.
_LIMIT_CORNERS = (
    ("forward_regardless_station", None),
    ("forward_regardless_station", "forward_regardless_point_weight"),
    ("forward_gross_station", "aft_gross_point_weight"),
    ("aft_gross_station", "aft_gross_point_weight"),
    ("aft_gross_station", None),
)


def _limit_polygon(values: Dict[str, float], floor: float,
                   len_f: float, mass_f: float) -> Optional[Series]:
    """The closed structural-limit envelope, or ``None`` if a corner is missing.

    ``floor`` is the minimum flight weight -- the bottom edge. A limit the
    airplane has no entry for leaves the polygon undrawn rather than half drawn:
    a limit envelope missing a side reads as permission, which is the one way
    this figure could mislead.
    """
    try:
        corners = [(values[x], floor if w is None else values[w])
                   for x, w in _LIMIT_CORNERS]
    except KeyError:
        return None
    if any(w <= 0 for _x, w in corners):
        return None
    corners.append(corners[0])          # close it
    return Series("Structural limits", [x * len_f for x, _w in corners],
                  [w * mass_f for _x, w in corners], style="densely dotted")


#: The Mach-limited boundaries drawn, by MACHLIM's own value keys.
#:
#: Declared as data and guarded against those keys, so a renamed key empties the
#: figure in the suite rather than on the page. Styles, never colours (SS 4.3).
_SPEED_ALTITUDE_LINES: Tuple[Tuple[str, str, str], ...] = (
    ("V(MC) cruise", "v_mc", "solid"),
    ("V(MNE) never-exceed", "v_mne", "dashed"),
    ("V(MD) dive", "v_md", "dotted"),
)


def speed_altitude_plot_data(project: Project) -> Optional[PlotData]:
    """The speed/altitude envelope figure's data -- the one owner (OR-7).

    Sea level to the maximum operating altitude, which is the whole operating
    envelope rather than its Mach-limited top: each boundary is **constant in
    EAS below the shoulder altitude and Mach-limited above it**, and the kink
    between the two is the point of the figure. The sub-shoulder segment adds no
    arithmetic -- it is the shoulder row's own speed held constant down to sea
    level, which is what "the shoulder altitude" means -- so every speed drawn
    is a value MACHLIM returned.

    ``Vh`` is marked, not drawn as a line: ``speeds.vh_kt`` is the maximum level
    flight speed **at sea level** and the analysis carries no altitude variation
    of it, so a full-height line would assert a boundary nothing computed. As a
    sea-level marker it still shows the thing worth seeing -- where Vh sits
    against VC, whose FAR floor is capped at 0.9 Vh (14 CFR 23.335(a)).

    Speeds are KEAS and altitudes feet in every unit system: the aviation
    channel is not converted (see :data:`AVIATION_UNITS_NOTE`). ``None`` when
    the airplane has no Mach-limited boundary to draw.
    """
    from ..modules.mach_limit import mach_limit_lines
    from ..modules.structural_speeds import design_speed_values

    speeds = project.speeds
    ml = speeds.mach_limit if speeds is not None else None
    if speeds is None or ml is None:
        return None
    # MC/MD come from STRSPEED, the single producer (F25-2) -- not from ``ml``.
    ds = _try(design_speed_values, project, speeds)
    results = (_try(mach_limit_lines, ml, ds.mc, ds.md, speeds.shoulder_altitude_ft)
               if ds is not None else None)
    if not results:
        return None

    rows = [{v.key: v.value for v in r.values} for r in results[1:]]
    if not rows:
        return None
    shoulder = float(speeds.shoulder_altitude_ft)

    series = []
    for name, key, style in _SPEED_ALTITUDE_LINES:
        vs = [row[key] for row in rows if key in row]
        alts = [row["altitude"] for row in rows if key in row]
        if not vs:
            continue
        if shoulder > 0:
            # Constant EAS below the shoulder: the first row's speed, held down
            # to sea level. Not a second computation of it.
            vs.insert(0, vs[0])
            alts.insert(0, 0.0)
        series.append(Series(name, vs, alts, style))
    if not series:
        return None

    points = ([("Vh", float(speeds.vh_kt), 0.0)] if speeds.vh_kt else [])
    return PlotData("V (KEAS)", "Altitude (ft)", series, points=points,
                    points_label="Maximum level-flight speed Vh (sea level)")


def weight_cg_plot_data(project: Project, u: Units) -> Optional[PlotData]:
    """The weight/CG envelope figure's data -- the one owner (OR-7).

    Both loading edges (note 45: ``WTENV.BAS`` sweeps its discretionary items
    ascending *and* descending), the closed structural-limit polygon, and every
    entered CG case as a labelled marker. Shared by the summary report and the
    oracle technical report so the two documents cannot draw the same airplane
    two ways. ``None`` when there is no weight data base to sweep.

    Drawing only the forward edge -- which is what this figure did until note 45
    -- shows the half that approaches no limit and hides the half that can
    exceed one, so the containment reading a reader takes from it would be wrong
    rather than merely partial.
    """
    from ..modules.weight_envelope import envelope as weight_envelope
    from ..modules.weight_envelope import loading_envelope

    weight = project.weight
    env_in = weight.envelope if weight is not None else None
    forward = _try(loading_envelope, project) or []
    if not forward:
        return None
    aft = _try(loading_envelope, project, aft=True) or []

    L, W = u.label("length"), u.label("mass")
    len_f = u.d.length.factor
    mass_f = 1.0 if u.system == UnitSystem.IMPERIAL else _EXTRA_DIMENSIONS["mass"][0]

    def edge(name: str, vertices, style: str) -> Series:
        return Series(name, [v.station * len_f for v in vertices],
                      [v.weight * mass_f for v in vertices], style=style)

    series = [edge("Forward loading envelope", forward, "solid")]
    if aft:
        series.append(edge("Aft loading envelope", aft, "dashed"))

    values: Dict[str, float] = {}
    if env_in is not None:
        for r in _try(weight_envelope, project, env_in) or []:
            for v in r.values:
                values.setdefault(v.key, v.value)
    polygon = _limit_polygon(values, forward[0].weight, len_f, mass_f)
    if polygon is not None:
        series.append(polygon)

    # Cases sharing a point are one marker with both names: on the GA6 the
    # forward-light landing case and CG3 are the same loading, and two labels
    # stacked on one diamond is a smudge, not information.
    marked: Dict[Tuple[float, float], List[str]] = {}
    for c in (weight.cg_cases if weight is not None else []):
        marked.setdefault((c.xcg * len_f, c.weight_lb * mass_f), []).append(c.name)
    points_marked = [(" / ".join(names), x, y)
                     for (x, y), names in marked.items()]

    return PlotData(f"Fuselage station ({L})", f"Weight ({W})", series,
                    points=points_marked)


def _weight_cg_figure(project: Project, u: Units) -> Tuple[Figure, Optional[Table]]:
    from ..modules.weight_envelope import loading_envelope_points

    weight = project.weight
    env_in = weight.envelope if weight is not None else None
    points = _try(loading_envelope_points, project) or []
    if not points:
        return (Figure("weight_cg", "Weight / CG envelope",
                       absent_reason="no itemized weight database, so "
                                     "there is no loading envelope to draw"), None)

    from ..derived_geometry import mac_reference, station_to_pct_mac

    W, L = u.label("mass"), u.label("length")
    data = weight_cg_plot_data(project, u)
    # The %MAC column reads the same reference WTENV drew the limit lines from
    # (#80): a typed envelope.xlemac/mac override else the planform. Reading the
    # planform here regardless meant that on a project carrying an override the
    # column and the vertical lines on this one chart described different wings.
    mac_ref = mac_reference(project, env_in)

    def pct_mac(x: float) -> str:
        if mac_ref is None or not mac_ref.mac:
            return ""
        return format_value(station_to_pct_mac(x, mac_ref))

    rows = [[u.plain(w, "mass"), u.plain(x, "length"), pct_mac(x)] for w, x in points]
    table = Table(
        title="Weight / CG envelope corner points",
        columns=[f"Weight ({W})", f"CG station ({L})", "CG (% MAC)"],
        rows=rows,
        note="Vertices of the forward loading envelope, most-forward first, in the "
             "order the discretionary items are loaded.",
    )
    return Figure(
        "weight_cg", "Weight / CG envelope",
        data=data,
        caption="Both loading envelopes -- discretionary items added most-forward "
                "first and most-aft first -- with the closed structural CG limit "
                "envelope and each design CG case. A loading vertex outside the "
                "limits is expected rather than a defect: the limits bound the "
                "loadings that may be flown, not those the airplane can hold. "
                "Weights and stations are not load quantities and are never "
                "scaled to ultimate.",
    ), table


def _speed_altitude_figure(project: Project) -> Tuple[Figure, Optional[Table]]:
    from ..modules.mach_limit import mach_limit_lines
    from ..modules.structural_speeds import design_speed_values
    from ..vn_diagram import _gust_ude

    speeds = project.speeds
    ml = speeds.mach_limit if speeds is not None else None
    if speeds is None or ml is None:
        return (Figure("speed_altitude", "Speed / altitude envelope",
                       absent_reason="this airplane has no Mach-limited boundary — no "
                                     "MACHLIM inputs are defined, so the operating "
                                     "envelope is bounded by VD alone"), None)
    # MC/MD come from STRSPEED, the single producer (F25-2) -- not from ``ml``.
    ds = _try(design_speed_values, project, project.speeds)
    results = (_try(mach_limit_lines, ml, ds.mc, ds.md, speeds.shoulder_altitude_ft)
               if ds is not None else None)
    if not results:
        return (Figure("speed_altitude", "Speed / altitude envelope",
                       absent_reason="the Mach-limit lines could not be "
                                     "computed from the inputs present"), None)

    lines = results[1:]  # results[0] is the MC/MD/MNE summary
    data = speed_altitude_plot_data(project)
    if data is None:
        return (Figure("speed_altitude", "Speed / altitude envelope",
                       absent_reason="the Mach-limit lines could not be "
                                     "computed from the inputs present"), None)

    rows = []
    for r in lines:
        by_key = {v.key: v.value for v in r.values}
        h = by_key["altitude"]
        rows.append([
            format_value(h),
            format_value(by_key["v_mc"]), format_value(by_key["v_mne"]),
            format_value(by_key["v_md"]),
            format_value(_gust_ude("C", h)), format_value(_gust_ude("D", h)),
        ])
    table = Table(
        title="Mach-limited speeds and derived gust velocities by altitude",
        columns=["Altitude (ft)", "V(MC) (KEAS)", "V(MNE) (KEAS)", "V(MD) (KEAS)",
                 "Ude at VC (fps)", "Ude at VD (fps)"],
        rows=rows,
        note="The derived gust velocities are tabulated rather than plotted: they "
             "are a velocity in fps, not an equivalent airspeed, and share no axis "
             "with the Mach-limited speeds. They taper above 20,000 ft per "
             "14 CFR 23.333(c)/23.341. " + AVIATION_UNITS_NOTE,
    )
    return Figure(
        "speed_altitude", "Speed / altitude envelope",
        data=data,
        caption="The operating envelope from sea level to the maximum operating "
                "altitude: each boundary is constant in equivalent airspeed below "
                "the shoulder altitude and Mach-limited above it (MACHLIM). Vh is "
                "marked at sea level, where it is entered; the analysis carries no "
                "altitude variation of it.",
    ), table


def _section_envelopes(project: Project, u: Units) -> Section:
    section = Section(
        section_heading("envelopes"),
        body=["Each figure is followed by its corner-point table — a plotted "
              "boundary without its numeric corners is not sufficient for sizing."],
    )
    for fig, table in (_vn_figure(project), _weight_cg_figure(project, u),
                       _speed_altitude_figure(project)):
        sub = Section(fig.title, figures=[fig])
        if table is not None:
            sub.tables.append(table)
        section.subsections.append(sub)
    return section


# --------------------------------------------------------------------------- #
# §4 Conditions analysed and FAR coverage
# --------------------------------------------------------------------------- #
_STATUS_LABEL = {
    COVERED: "covered",
    NOT_APPLICABLE: "not applicable",
    NOT_ANALYSED: "NOT ANALYSED",
    OUT_OF_SCOPE: "out of scope",
}


def _case_index_table(module_results, comps: ComponentLoads,
                      assembled: Sequence = (),
                      project: Optional[Project] = None) -> Table:
    """The case index, with the safety factor §4.4 requires beside each case.

    Carries **both** deck-number columns (design note 17): the component-deck
    ``LOAD``/``SUBCASE`` and the assembled-deck one, each filled only where the
    case is actually in that deck. This table is the document's join between a
    solver result and the condition that produced it, which is why every other
    table in the report identifies its rows by case id and points here rather
    than repeating the pair.
    """
    from ..export.sbeam_bridge import LOAD_ID_COLUMN, case_index_rows_from
    from ..safety_factors import GoverningTable

    # Deck-exported results first, SELECT's conditions after: first-seen defines
    # a row's flight condition, and this table is the join from a SUBCASE to the
    # condition its cards were computed at (user decision 2026-08-13 -- see
    # ``case_index_rows_from``).
    groups = [comps.wing, comps.body, comps.tail, comps.control] + [
        mr.conditions for mr in module_results]
    rows = case_index_rows_from(*groups, assembled=assembled)
    # The SF column is a **derived view of the governing table** (M4-8 / G-11),
    # not a read of whatever the result object happens to carry: the silent
    # ``getattr(item, "safety_factor", ULTIMATE_FACTOR)`` this replaced reported
    # 1.5 for a factorless case with no trace at all. An unclassified case still
    # gets 1.5 -- and is flagged, in the governing-factors section.
    table = GoverningTable.for_project(project)
    sf_by_id: Dict[str, float] = {}
    for group in groups:
        for item in group:
            ref = getattr(item, "case_ref", None)
            if ref is not None and ref.case_id not in sf_by_id:
                sf_by_id[ref.case_id] = table.required_factor_for(item)
    comp_col, asm_col = LOAD_ID_COLUMN[COMPONENT_DECK], LOAD_ID_COLUMN[ASSEMBLED_DECK]
    return Table(
        title="Case index",
        columns=["ID", "LOAD (comp.)", "LOAD (asm.)", "Component", "Condition", "CG",
                 "Speed (kt)", "Altitude (ft)", "FAR", "SF"],
        rows=[[r["ID"], r[comp_col] or NO_LOAD_ID, r[asm_col] or NO_LOAD_ID,
               r["Component"], r["Condition"], r["CG"], r["Speed (kt)"],
               r["Altitude (ft)"], r["FAR"],
               format_value(sf_by_id.get(r["ID"], ULTIMATE_FACTOR))] for r in rows],
        small=True,
        note="Case IDs are the same identities that appear in the companion "
             "case-index CSV and in the sbeam FORCE/MOMENT cards; they are never "
             "re-minted or renumbered for presentation. The two LOAD columns are "
             "the deck-side identity of the same case: the integer a deck uses "
             "for both its SUBCASE and its load-set SID (LOAD = 103 inside "
             "SUBCASE 103), and the deck's LABEL is the case ID itself. They "
             "differ because a case is numbered once per deck family — the "
             "per-component deck it is analysed in, and the assembled full-span "
             "model — and a dash means the case is not in that deck at all. "
             "Every other table in this report identifies its rows by case ID "
             "and joins to a solver result through this one. The flight "
             "condition stated is the one the cards under that ID were computed "
             "at: where an entered wing case restates the CL/speed of a "
             "condition SELECT also picked, this row carries the entered "
             "condition and the governing-loads table carries SELECT's own V-n "
             "point.",
    )


def _coverage_table(project: Project, module_results) -> Tuple[Table, str]:
    refs = [c.far_reference for mr in module_results for c in mr.conditions]
    rows = coverage_matrix(project, refs)
    summary = coverage_summary(rows)
    headline = (
        f"{summary[COVERED]} regulations covered, {summary[NOT_APPLICABLE]} not "
        f"applicable to this airplane, {summary[NOT_ANALYSED]} NOT ANALYSED "
        f"(inputs absent), {summary[OUT_OF_SCOPE]} out of scope for this tool."
    )
    table = Table(
        title="FAR 23 Subpart C coverage",
        columns=["FAR", "Title", "Module", "Status", "Cases", "Reason"],
        rows=[[r.far, r.title, r.module, _STATUS_LABEL[r.status],
               str(r.case_count) if r.case_count else "—", r.reason] for r in rows],
        small=True,
        status_column="Status",
        note="'Not applicable' is an engineering conclusion about this airplane; "
             "'NOT ANALYSED' is a gap in this run that supplying inputs would close; "
             "'out of scope' is a permanent boundary of this tool that must be "
             "covered by other means.",
    )
    return table, headline


def _balanced_skips_table(run: "BalancedRun") -> Table:
    """What the assembled balanced deliverable does **not** cover (review F-C7).

    The balanced free-free deck is the mission's primary loads deliverable, and a
    deck lists only what it holds: a condition that dropped out for a missing V-n
    point or a non-derivable loading was invisible in every rendering of it. The
    reason groups and their wording are ``modules.balance``'s -- this states them,
    it does not word them.

    A project the balancer cannot run at all yields the "not assembled" row
    rather than an absent table: silence here is the very failure mode being
    closed.
    """
    from ..modules.balance import skipped_condition_lines

    cases, skipped = run.cases, run.skipped
    if cases is None:
        rows = [["No balanced case could be assembled for this project — the "
                 "assembled full-span deliverable is absent from this run."]]
    elif skipped:
        rows = [[line] for line in skipped_condition_lines(skipped)]
    elif cases:
        rows = [["None — every condition SELECT named was assembled into a "
                 "balanced case."]]
    else:
        rows = [["SELECT named no condition at all, so there was nothing to "
                 "assemble."]]
    return Table(
        title="Conditions not assembled into a balanced case",
        columns=["Condition set, and why it did not assemble"],
        rows=rows,
        small=True,
        note="The assembled full-span balanced model is the primary loads "
             "deliverable; the conditions listed here are covered by the "
             "per-component analyses only. Horizontal-tail, fuselage, ground "
             "and one-engine-out conditions are a deliberate exclusion; the "
             "rest are gaps this project's inputs would close.",
    )


def _section_conditions(project: Project, module_results, comps: ComponentLoads,
                        scope: str, deselected_case_ids: Sequence[str],
                        run: "BalancedRun") -> Section:
    coverage, headline = _coverage_table(project, module_results)
    scope_text = f"Scope of this export: {scope or 'full case set'}."
    if deselected_case_ids:
        scope_text += (" The following cases were computed but EXCLUDED from this "
                       "deliverable: " + ", ".join(deselected_case_ids) + ".")
    else:
        scope_text += " No computed case was excluded."
    # Decision G-9, stated where a reader meets the governing sets rather than
    # left to be inferred from the absence of a comparison. It is a decision, and
    # the reason for it is structural: reading it as an oversight would invite a
    # consumer to take a cross-family max() for themselves without keeping the
    # case identity that makes the answer usable.
    families = (
        "**Ground and flight cases are separate governing families.** They are "
        "never compared against one another for a maximum, and no single "
        "envelope over both is claimed: the two load different structure by "
        "different paths, and the value of a governing table is naming WHICH "
        "case governs -- which a cross-family max() destroys. Both families are "
        "reported in full, each with its own case identities, so a consumer "
        "sizing structure that sees both must take the worst of the two per "
        "station and keep the id that produced each extreme.")
    return Section(
        section_heading("conditions"),
        body=[scope_text, headline, families],
        tables=[
            _case_index_table(module_results, comps, run.cases or [], project),
            coverage,
            _balanced_skips_table(run),
            Table(
                title="Approved corrections to the source manual",
                columns=["FAR", "Correction"],
                rows=[[far, text] for far, text in APPROVED_CORRECTIONS],
                note="Deliberate, documented deviations from McMaster's printed "
                     "manual, each approved and cited in the project's register of "
                     "approved corrections.",
            ),
        ],
    )


# --------------------------------------------------------------------------- #
# §5 Results summary (all LIMIT, SF stated per case)
# --------------------------------------------------------------------------- #
def _governing_table(title: str, conditions, u: Units) -> Optional[Table]:
    """One component's governing conditions, straight from ``governing_loads_table``.

    Deliberately not re-derived here: the report's governing figures must equal
    the ones the Results Review and Critical Loads pages show, and the only way to
    guarantee that is to call the same function.
    """
    if not conditions:
        return None
    rows = governing_loads_table(list(conditions), u.system)
    if not rows:
        return None
    columns = list(rows[0].keys())
    return Table(
        title=title,
        columns=columns,
        rows=[[str(r.get(c, "—")) for c in columns] for r in rows],
        small=len(columns) > 7,
        note="Loads are LIMIT; the SF column states the factor that was NOT "
             "applied to each row's load cells. Dimensionless quantities (n, CL) "
             "and speeds are limit values and take no factor.",
    )


class _Extreme:
    """Running two-sided extreme of one quantity, with where each side occurs."""

    def __init__(self, label: str, units: str) -> None:
        self.label = label
        self.units = units
        self.hi: Optional[float] = None
        self.lo: Optional[float] = None
        self.hi_at = ""
        self.lo_at = ""

    def add(self, value: float, at: str) -> None:
        if self.hi is None or value > self.hi:
            self.hi, self.hi_at = value, at
        if self.lo is None or value < self.lo:
            self.lo, self.lo_at = value, at

    def row(self) -> List[str]:
        return [self.label, self.units,
                format_value(self.hi) if self.hi is not None else "",
                self.hi_at,
                format_value(self.lo) if self.lo is not None else "",
                self.lo_at]


_EXTREMES_COLUMNS = ["Quantity", "Units", "Maximum", "Occurs at (case, station)",
                     "Minimum", "Occurs at (case, station)"]
_EXTREMES_NOTE = (
    "Envelopes are two-sided: the maximum and the minimum are reported separately, "
    "because the opposite-sign extreme can size a different part of the structure. "
    "Every extreme names the case and the station it occurs at."
)


def _station_extremes_table(title: str, results, u: Units, *, station_attr: str,
                            station_label: str, quantities, note: str = "") -> Optional[Table]:
    """Two-sided extremes over a distributed-load family, with case and station."""
    if not results:
        return None
    extremes = {
        key: _Extreme(label, u.ult_label(dim)) for key, label, dim in quantities
    }
    for res in results:
        case = getattr(res, "case_ref", None)
        case_id = case.case_id if case is not None else getattr(res, "case", "")
        for station in res.stations:
            where = (f"{case_id} at {station_label} "
                     f"{format_value(getattr(station, station_attr) * u.d.length.factor)} "
                     f"{u.label('length')}")
            for key, _label, dim in quantities:
                value = getattr(station, key) * getattr(u.d, dim).factor
                extremes[key].add(value, where)
    return Table(
        title=title,
        columns=_EXTREMES_COLUMNS,
        rows=[extremes[key].row() for key, _l, _d in quantities],
        note=(note + " " if note else "") + _EXTREMES_NOTE,
    )


def _wing_section(project: Project, comps: ComponentLoads, u: Units,
                  critical: Dict[str, List[Any]]) -> Section:
    from ..modules.net_loads import torsion_axis_label, wing_lra

    section = Section("Wing")
    table = _governing_table("Wing governing conditions", critical.get("wing"), u)
    if table is not None:
        section.tables.append(table)
    if not comps.wing:
        if table is None:
            section.absent_reason = ("no wing load cases (the net wing "
                                     "distribution could not be built from these inputs)")
        return section
    axis = comps.wing[0].torsion_axis or torsion_axis_label(wing_lra(project))
    extremes = _station_extremes_table(
        "Wing maxima", comps.wing, u,
        station_attr="y", station_label="span station",
        quantities=[("sz", "Shear Sz", "force"),
                    ("sx", "Chord shear Sx", "force"),
                    ("mxx", "Bending Mxx", "moment"),
                    ("myy", f"Torsion Myy about the {axis}", "moment"),
                    ("mzz", "Chord bending Mzz", "moment")],
        note=f"Wing torsion Myy is stated about the {axis} — the wing's loads "
             "reference axis, not the quarter chord it is computed on.",
    )
    if extremes is not None:
        section.tables.append(extremes)

    # The wing root design loads (step 13): the internal load at the
    # side-of-body cut, stated separately from the half-span extremes above --
    # which include the centre-box strip loads inboard of the joint and
    # overstate root bending by ~23 % on the reference GA wing (plan 10 §1.1).
    # ``sob_internal_loads`` returns LIMIT like everything else (OR-116), so the
    # 1.0 passed to the formatter is inert -- ``Units.load_value`` applies no
    # factor at all. The case's own factor is stated in the SF column beside it.
    from ..derived_geometry import sob_station

    sob = sob_station(project)
    if sob is not None and comps.wing:
        from ..export.sbeam_bridge import sob_internal_loads

        sob_rows = []
        for r in comps.wing:
            si = sob_internal_loads(r, sob.y)
            case = r.case_ref.case_id if r.case_ref else r.case
            sob_rows.append([
                case,
                u.load(si.sz, "force", 1.0),
                u.load(si.sx, "force", 1.0),
                u.load(si.mxx, "moment", 1.0),
                u.load(si.myy, "moment", 1.0),
                u.load(si.mzz, "moment", 1.0),
                format_value(r.safety_factor),
            ])
        section.tables.append(Table(
            title=("Wing side-of-body internal loads "
                   f"(BL {sob.y * u.d.length.factor:.1f} {u.label('length')})"),
            columns=["Case", f"Sz ({u.ult_label('force')})",
                     f"Sx ({u.ult_label('force')})",
                     f"Mxx ({u.ult_label('moment')})",
                     f"Myy ({u.ult_label('moment')})",
                     f"Mzz ({u.ult_label('moment')})", "SF"],
            rows=sob_rows,
            note=("The wing root design loads: the load carried across the "
                  "wing-to-fuselage joint, summed closed-form from the applied "
                  "loads outboard of the side of body. Distinct from the "
                  "half-span maxima above, which include the centre-box strip "
                  "loads inboard of the joint. " + sob.note + ". The wing stick "
                  "deck carries a tagged reporting node (SLOADS-NODE lra-sob); "
                  "the same quantities are recoverable as the CBAR end force in "
                  "the first element outboard, and the two statements are gated "
                  "against each other in the round-trip CI."),
        ))

    section.body.append(
        f"Full station-by-station distributions for all {len(comps.wing)} wing cases "
        "are in the companion file wing_span_loads.csv and the sbeam deck "
        "wing_loads.bdf; the applied load set they accumulate from -- strip by "
        "strip and mass by mass, each at its own point -- is in "
        "wing_applied_loads.csv (see the bundle manifest)."
    )
    return section


def _fuselage_section(comps: ComponentLoads, u: Units,
                      critical: Dict[str, List[Any]]) -> Section:
    section = Section("Fuselage")
    table = _governing_table("Fuselage governing conditions", critical.get("fuselage"), u)
    if table is not None:
        section.tables.append(table)
    if not comps.body:
        if table is None:
            section.absent_reason = ("no fuselage load cases (the body "
                                     "distribution could not be built from these inputs)")
        return section
    extremes = _station_extremes_table(
        "Fuselage maxima", comps.body, u,
        station_attr="x", station_label="body station",
        quantities=[("sz", "Vertical shear Sz", "force"),
                    ("sy", "Side shear Sy", "force"),
                    ("myy", "Bending Myy", "moment"),
                    ("mzz", "Side bending Mzz", "moment"),
                    ("mxx", "Torsion Mxx about the body X axis", "moment")],
    )
    if extremes is not None:
        section.tables.append(extremes)

    fitting_rows = []
    for r in comps.body:
        if r.r_front is None and r.r_rear is None:
            continue
        case = r.case_ref.case_id if r.case_ref else r.case
        fitting_rows.append([
            case,
            u.load(r.r_front, "force", r.safety_factor),
            u.plain(r.x_front, "length"),
            u.load(r.r_rear, "force", r.safety_factor),
            u.plain(r.x_rear, "length"),
            format_value(r.safety_factor),
        ])
    if fitting_rows:
        section.tables.append(Table(
            title="Wing-attach fitting loads",
            columns=["Case", f"Front spar reaction ({u.ult_label('force')})",
                     f"Front spar station ({u.label('length')})",
                     f"Rear spar reaction ({u.ult_label('force')})",
                     f"Rear spar station ({u.label('length')})", "SF"],
            rows=fitting_rows,
            note="Reported for the wing-attach fittings. The fuselage span-load "
                 "distribution already carries these reactions — do not apply them "
                 "on top of it.",
        ))

    if any(getattr(r, "closure_artifact", False) for r in comps.body):
        from ..modules.body_loads import CLOSURE_ARTIFACT_CAVEAT

        n = sum(1 for r in comps.body if r.closure_artifact)
        section.body.append(f"CLOSURE CAVEAT ({n} case(s)): {CLOSURE_ARTIFACT_CAVEAT}")
    else:
        section.body.append(
            "The exported set closes both the vertical residual and the terminal Myy "
            "at the wing front/rear spar attachments (Ref 1 Ch 15 p103)."
        )
    if any(getattr(r, "spars_assumed", False) for r in comps.body):
        section.body.append(
            "Wing spar stations were ASSUMED (front/rear spar chord fractions were "
            "not entered), so the carry-through reaction location is a default, not "
            "an input."
        )
    return section


def _tail_section(component: str, title: str, comps: ComponentLoads, u: Units,
                  critical: Dict[str, List[Any]]) -> Section:
    section = Section(title)
    table = _governing_table(f"{title} governing conditions", critical.get(component), u)
    if table is not None:
        section.tables.append(table)
    results = [r for r in comps.tail if r.component == component]
    if not results:
        if table is None:
            section.absent_reason = (f"no {title.lower()} load cases in "
                                     "this run")
        return section
    rows = []
    for r in results:
        psis = [abs(s.psi) for s in r.stations] or [0.0]
        rows.append([
            r.case_ref.case_id if r.case_ref else r.case,
            r.case,
            r.far_reference,
            u.load(r.lt25, "force", r.safety_factor),
            u.load(r.lt50, "force", r.safety_factor),
            u.load(max(psis), "pressure", r.safety_factor),
            format_value(r.safety_factor),
        ])
    section.tables.append(Table(
        title=f"{title} chordwise load split",
        columns=["ID", "Condition", "FAR",
                 f"LT25 at 25% MAC ({u.ult_label('force')})",
                 f"LT50 at 50% MAC ({u.ult_label('force')})",
                 f"Max |load intensity| ({u.ult_label('pressure')})", "SF"],
        rows=rows,
        note="LT25 is the angle-of-attack (additive) load at 25% MAC and LT50 the "
             "camber load at 50% MAC — the rational chordwise split TAILDIST "
             "distributes. Full chordwise profiles are in tail_chordwise.csv.",
    ))
    return section


def _control_surface_section(comps: ComponentLoads, u: Units) -> Section:
    section = Section("Control surfaces")
    if not comps.control:
        section.absent_reason = ("no aileron, flap or tab input slices "
                                 "in this project")
        return section
    rows = []
    for r in comps.control:
        psis = [abs(s.psi) for s in r.stations] or [0.0]
        rows.append([
            r.case_ref.case_id if r.case_ref else "",
            r.surface,
            r.case,
            u.load(r.load_lb, "force", r.safety_factor),
            u.load(max(psis), "pressure", r.safety_factor),
            format_value(r.v_kt) if r.v_kt else "",
            format_value(r.safety_factor),
        ])
    section.tables.append(Table(
        title="Control-surface design loads",
        columns=["ID", "Surface", "Condition", f"Load ({u.ult_label('force')})",
                 f"Max design pressure ({u.ult_label('pressure')})", "V (KEAS)", "SF"],
        rows=rows,
        note="The chordwise distributions are the *standard simplified* forms "
             "(aileron: constant to the hinge then tapering to zero at the trailing "
             "edge; flap: leading edge to half at the trailing edge; tab: trapezoid "
             "with the leading edge twice the trailing edge) — not measured or "
             "CFD distributions.",
    ))
    return section


def _module_extremes_section(title: str, module_results, module_name: str,
                             u: Units, note: str = "") -> Section:
    """Two-sided load extremes over one module's conditions (engine mount, gear).

    These modules produce tens of discrete reaction cases rather than a
    distribution; inlining every case would bury the governing ones (decision
    G8-4), so the report carries the extremes with their case IDs and points at
    the case index and the module's load-case CSV for the rest.
    """
    section = Section(title)
    results = [mr for mr in module_results if mr.module == module_name]
    conditions = [c for mr in results for c in mr.conditions]
    if not conditions:
        section.absent_reason = (f"the {module_name} module produced no "
                                 "conditions in this run (its inputs are absent)")
        return section
    extremes: Dict[str, _Extreme] = {}
    order: List[str] = []
    fars = []
    for c in conditions:
        if c.far_reference and c.far_reference not in fars:
            fars.append(c.far_reference)
        case_id = c.case_ref.case_id if c.case_ref else c.title
        for v in c.values:
            dim = _load_dimension(v.units, v.quantity)
            if dim is None:
                continue
            key = v.key or v.label
            if key not in extremes:
                extremes[key] = _Extreme(v.label, u.ult_label(dim, c.safety_factor))
                order.append(key)
            extremes[key].add(v.value * getattr(u.d, dim).factor,
                              f"{case_id} (SF {format_value(c.safety_factor)})")
    if not order:
        section.absent_reason = (f"the {module_name} module produced no "
                                 "load quantities in this run")
        return section
    section.tables.append(Table(
        title=f"{title} load extremes",
        columns=["Quantity", "Units", "Maximum", "Occurs at (case, SF)",
                 "Minimum", "Occurs at (case, SF)"],
        rows=[extremes[k].row() for k in order],
        note=(note + " " if note else "") + _EXTREMES_NOTE
             + f" Conditions analysed: {len(conditions)}; FAR references: "
               f"{', '.join(fars) if fars else '—'}. Every case is listed "
               "individually in the case index and in the module's load-case CSV.",
    ))
    return section


def _critical_by_component(comps: ComponentLoads,
                           deselected: Sequence[str] = ()) -> Dict[str, List[Any]]:
    """SELECT's governing conditions, grouped by component and export-scoped.

    A condition the engineer deselected on the Critical Loads page is not in the
    deliverable, so it is not in the report's results tables either -- §3.4 makes
    the exclusion itself reportable (it is listed by ID in §3), but a table of
    governing loads must describe what was actually delivered.
    """
    dropped = set(deselected)
    out: Dict[str, List[Any]] = {}
    for c in comps.critical:
        if c.case_ref is not None and c.case_ref.case_id in dropped:
            continue
        out.setdefault(c.component, []).append(c)
    return out


_ENGINE_NOTE = (
    "Preserved sign conventions: engine-mount reaction torque is reported NEGATIVE, "
    "and 'clockwise from the pilot's view is positive' for rotor RPM and stoppage "
    "torque. The four 23.371(b) gyroscopic sign combinations are separate cases "
    "(suffixes a-d on the engine-mount case ID)."
)
_GEAR_NOTE = (
    "Ground reactions act on the landing-gear geometry reported in "
    + section_ref("inputs") + " (main and nose axle stations and tread). Loads "
    "with respect to the ground line are the 'prime' reactions; the inertia "
    "factors are dimensionless load factors and are never scaled to ultimate."
)


def _section_results(project: Project, module_results, comps: ComponentLoads,
                     u: Units, deselected: Sequence[str]) -> Section:
    critical = _critical_by_component(comps, deselected)
    return Section(
        section_heading("results"),
        body=["Every load below is LIMIT, with the safety factor that was not "
              "applied to it stated per case. Full station-by-station "
              "distributions stay in the companion data files named in the "
              "bundle manifest."],
        subsections=[
            _wing_section(project, comps, u, critical),
            _fuselage_section(comps, u, critical),
            _tail_section("htail", "Horizontal tail", comps, u, critical),
            _tail_section("vtail", "Vertical tail", comps, u, critical),
            _control_surface_section(comps, u),
            _module_extremes_section("Landing gear", module_results, "landing", u,
                                     note=_GEAR_NOTE),
            _module_extremes_section("Engine mount", module_results, "engine", u,
                                     note=_ENGINE_NOTE),
        ],
    )


# --------------------------------------------------------------------------- #
# §6 Balanced free-free airframe cases (the assembled deliverable)
# --------------------------------------------------------------------------- #
_BALANCED_ABSENT = (
    "No balanced free-free case could be assembled from these inputs, so the "
    "assembled full-span deck is NOT part of this deliverable and the "
    "per-component decks of " + section_ref("results") + " are the whole of "
    "the load output. A condition assembles only when it has a V-n point and a "
    "payload loading the itemized weight database can actually produce; "
    + section_ref("conditions") + "'s table of conditions not assembled names "
    "each one and why."
)


def _hand_pair_sentence(cases: Sequence[Any]) -> str:
    """How many handed twins the assembled set carries, and what a twin is.

    An asymmetric case ships as a left/right pair generated by reflection at the
    assembly (plan 11 B-6), so a reader who sees one hand must be told the other
    exists -- and a reader who sees neither must be told the set is symmetric.
    """
    handed = [c for c in cases if getattr(c, "hand", "")]
    if not handed:
        return ("Every assembled case is symmetric, so none has a handed twin: "
                "the set contains no rolling or lateral condition.")
    return (
        f"{len(handed)} of the {len(cases)} cases are handed: an asymmetric "
        "condition (a rolling case under FAR 23.349, a lateral case under "
        "23.441/23.443, the unsymmetrical horizontal-tail case under 23.427(a)) "
        "ships as a starboard/port PAIR, the port case generated "
        "by reflecting the computed starboard one about the airplane centreline "
        f"(y -> -y, side loads negated). That is {len(handed) // 2} twin pair(s); "
        "both hands are in the deck, and both must be sized for."
    )


def _residual_gate_sentence(cases: Sequence[Any]) -> str:
    """§6's verdict on the residual gate -- over the family the gate applies to.

    The maximum is taken through ``balance.residual_gate_applies``, the one owner
    of the exemption (CR-C-2): maximised over *all* cases it reported the
    23.427(a) maneuver tail load (143.885 % on ``ga6_normal``) or a ground case's
    applied gear reaction (100.000 %) as a failure of the primary deliverable, in
    every report shipped since 0.6.0. The exempt families are stated beside the
    number rather than silently dropped, since a maximum over a filtered set is
    only honest if the filter is visible.

    **Force and pitch are judged against their own acceptances** -- the owners
    :data:`~sloads.modules.balance.FORCE_RESIDUAL_ACCEPTANCE` and
    :data:`~sloads.modules.balance.RESIDUAL_GATE` -- rather than both against the
    flat 1 %. Reporting a single ``max(force, pitch)`` against the tighter of the
    two declared four of the six fixtures failed on a bound the suite does not
    itself enforce, which is the same defect in a second coat of paint.
    """
    from ..modules.balance import (
        FORCE_RESIDUAL_ACCEPTANCE,
        RESIDUAL_GATE,
        residual_gate_exemptions,
        residual_gate_family,
    )

    exempt = residual_gate_exemptions(cases)
    standing = (
        " The gate does not apply to " + "; ".join(exempt) + " -- for those the "
        "pre-closure residual IS the applied load, by construction, and each "
        "carries its own stronger gate instead (the ground family reproduces "
        "LANDLOAD's NVP/NDP/NS exactly; the 23.427(a) family's trim half closes "
        "inside the gate with the maneuver set replaced by the trim tail load). "
        "The per-case table below reports every case, gated or not."
    ) if exempt else ""

    judged, clamped = residual_gate_family(cases)
    clamped_standing = (
        f" {len(clamped)} further case(s) carry a non-wing axial force that was "
        "NOT applied (the trim alpha falls outside the polar's trusted window), "
        "so they are out of trim by exactly that clamped force and its couple "
        "about the CG. Their residuals are that known quantity rather than a "
        "balance quality, and are gated per case against what was measured when "
        "the clamp was decided."
    ) if clamped else ""

    if not judged:
        return (
            "{} case(s) assembled. None of them is in the family the pre-closure "
            "residual acceptances apply to.".format(len(cases))
            + clamped_standing + standing)

    force = _worst_residual(judged, "force_residual_fraction")
    pitch = _worst_residual(judged, "moment_residual_fraction")
    verdict = (
        " Both are inside their acceptance."
        if force[0] < FORCE_RESIDUAL_ACCEPTANCE and pitch[0] < RESIDUAL_GATE else
        " That is OVER acceptance -- reported rather than suppressed, and the "
        "per-case table below localises it.")
    return (
        f"{len(cases)} case(s) assembled, {len(judged)} of them judged against "
        f"the pre-closure residual acceptances. Across those, the worst force "
        f"residual is {force[0]:.3%} of n*W on '{force[1]}' against a "
        f"{FORCE_RESIDUAL_ACCEPTANCE:.1%} acceptance, and the worst pitch "
        f"residual {pitch[0]:.3%} of n*W*MAC on '{pitch[1]}' against "
        f"{RESIDUAL_GATE:.0%}." + verdict + clamped_standing + standing)


def _worst_residual(cases: Sequence[Any], attribute: str) -> Tuple[float, str]:
    """``(fraction, case label)`` of the largest ``attribute`` in ``cases``.

    Through ``picks.extreme``: cases tie on a residual exactly (a handed pair
    always does), and the sentence names the case it picked, so which one wins
    the tie has to be stable across platforms rather than left to ``max``.
    """
    from ..picks import extreme

    worst = extreme(cases, key=lambda c: getattr(c, attribute))
    return getattr(worst, attribute), getattr(worst, "label", "")


def _balanced_cases_table(cases: Sequence[Any]) -> Table:
    """The per-case honesty statement, straight from the deck's own row builder."""
    from ..export.balanced_deck import balanced_case_rows
    from ..modules.balance import RESIDUAL_GATE

    rows = balanced_case_rows(cases)
    columns = list(rows[0])
    return Table(
        title="Balanced free-free cases",
        columns=columns,
        rows=[[row[c] for c in columns] for row in rows],
        small=True,
        note=(
            "Residuals are measured BEFORE closure, so the "
            f"{RESIDUAL_GATE:.0%} gate is on the physics rather than on the "
            "correction; 'Closure dn' is the mass-proportional relief that shut "
            "the remainder. The roll couple is different in kind -- on a rolling "
            "case it is the APPLIED aileron moment, which the airplane is not "
            "supposed to balance, and it is reacted in full by distributed roll "
            "acceleration. The gate does not apply to the Fz/My of the "
            "UNSYMMETRICAL rows either (FAR 23.427(a)): that case's applied tail "
            "load is a MANEUVER load and replaces the trim tail load its V-n "
            "point balances at, so the residual is the mismatch in full and the "
            "vertical and pitch closure is the motion it causes -- what is gated "
            "there is the case's trim half. The GROUND rows (FAR 23.471-23.499) "
            "read 100.000 % for the same kind of reason and are likewise not "
            "gated: a ground case has no trim to fail, so its pre-closure "
            "residual is the applied gear reaction IN FULL, and the gate it does "
            "carry is that the solved field rotated back to the ground line "
            "reproduces LANDLOAD's NVP/NDP/NS. Residual percentages and load "
            "factors are LIMIT quantities, and so are the exported cards."
        ),
    )


def _mass_cases_table(mass_rows: Sequence[Dict[str, Any]], u: Units) -> Optional[Table]:
    """Which payload case is which ``MASSSET`` in the exported CONM2 model.

    The mass model is a deliverable in its own right (plan 12 C-4) and the
    identity is not cosmetic: a consumer selecting the wrong ``MASSSET`` sizes
    the airplane at the wrong weight and CG. The SID/label pair comes from
    ``mass_cards.massset_identity`` -- the same mint the cards themselves use.
    """
    rows = list(mass_rows)
    if not rows:
        return None
    return Table(
        title="Payload cases in the exported mass model (CONM2 / MASSSET)",
        columns=["Payload case", "In the mass model", "Loading", "MASSSET",
                 f"Weight ({u.label('mass')})", f"X cg ({u.label('length')})",
                 f"Ballast weight ({u.label('mass')})", "Note"],
        rows=[[
            str(r["case"]),
            "yes" if r["exported"] else "NOT EXPORTED",
            "entered" if r.get("entered") else "derived",
            f"{r['massset_sid']} ({r['massset_label']})" if r["massset_sid"] else "—",
            u.plain(r["weight_lb"], "mass"),
            u.plain(r["cg_x"], "length"),
            (f"{u.plain(r['ballast_lb'], 'mass')} "
             f"({r['ballast_fraction'] * 100:.1f} %)") if r["ballast_lb"] else "none",
            str(r["note"]),
        ] for r in rows],
        small=True,
        note="A payload case is exported only when the weight database can "
             "produce it as a real loading; one needing a large fictitious "
             "ballast is a CG point, not a loading, and exporting it would put "
             "invented mass into the model that exists to check the real one. "
             "Weights and CG stations are the loading's own, never the case's "
             "nominal figures. A loading marked *entered* is stated on the case "
             "(D-25) and is authoritative -- the case's own weight and CG are "
             "then a checked echo of it, and its ballast is an engineering "
             "statement rather than a solved residual, so the credibility gate "
             "does not apply to it.",
    )


def _section_balanced(run: BalancedRun, mass_rows: Sequence[Dict[str, Any]],
                      u: Units) -> Section:
    """§6 -- the assembled full-span model, per case.

    The mission's primary loads deliverable had, until this section existed, no
    presence in the controlling document at all: it downloaded from a page, and
    the report described only the per-component views of it (review F-D2,
    decision D-R2).
    """
    cases = run.cases or []
    section = Section(
        section_heading("balanced"),
        body=[
            "The assembled full-span model is this deliverable's primary load "
            "output: wing tip to wing tip and nose to tail, aero and inertia "
            "together, free-free. It needs no constraint because the applied "
            "loads balance -- the deck carries one statically determinate "
            "support whose recovered reaction IS the residual tabulated below, "
            "so 'reactions ~ 0' is the equilibrium proof rather than a modelling "
            "convenience. The per-component decks of "
            + section_ref("results") + " are analysis views cut out of this "
            "model; each carries its cut reaction as an applied load, which "
            "the assembled model must never do.",
        ],
    )
    # The mass model is a deliverable in its own right: it is tabulated whether
    # or not a balanced case assembled, so the manifest's "summarised in §6"
    # holds for it either way.
    mass_table = _mass_cases_table(mass_rows, u)
    if not cases:
        section.absent_reason = _BALANCED_ABSENT
        if mass_table is not None:
            section.tables.append(mass_table)
        return section

    section.body += [_residual_gate_sentence(cases), _hand_pair_sentence(cases)]
    section.tables.append(_balanced_cases_table(cases))
    if mass_table is not None:
        section.tables.append(mass_table)
    return section


#: What the gear section says when the project cannot produce one.
_GEAR_ABSENT = (
    "No landing-gear geometry is defined for this project, so no gear interface "
    "loads were produced. The report needs the axle positions at the three strut "
    "states, the rolling radius and the tread; it does NOT need a derivable mass "
    "loading, which is why it reaches airplanes the assembled ground cases of "
    + section_ref("balanced") + " do not.")


def _section_gear(project: Project, u: Units) -> Section:
    """The gear interface load definition (decision G-12).

    A **free body**, not a load list: the reaction at the tyre contact patch, the
    strut state and ground angle it was computed at, and the same reaction where
    the airframe receives it. Both ends of the leg, so a reader can check by eye
    that the two ground artifacts are one load seen from two sides.

    Written deliberately short in the document and long in the companion CSV: the
    per-case detail is 33 cases x 2 legs x 20 columns, which is a data file, and
    what the controlling document owes is the *basis* -- what the numbers are,
    what frame each is in, and what this report must not be used for.
    """
    from ..gear_loads import UNSPRUNG_NOTE, gear_case_loads
    from ..models import MissingInputError

    section = Section(
        section_heading("gear"),
        body=[
            "This is the **gear interface load definition**: for every ground "
            "condition and each leg, the reaction at the tyre contact patch -- "
            "where 23.485(d) places it and where LANDLOAD computes it -- with "
            "the strut state, ground angle and stroke it was computed at, and "
            "the same reaction transferred to the gear reference point where "
            "the airframe receives it. Stating both ends of the leg is what "
            "makes it a free body: the reference-point reaction is the load the "
            "assembled deck of " + section_ref("balanced") + " applies at that "
            "node, sign-flipped, case by case.",
            "The two frames are each artifact's own and neither is re-derived. "
            "The contact-patch components are **ground-line** (vertical, drag, "
            "side), which is how the manual prints them and how a gear engineer "
            "reads them; the reference-point components are **airplane-datum**, "
            "which is what a beam model applies. The difference is not cosmetic "
            "-- the two resolutions of one reaction differ by the ground angle, "
            "and a level-landing drag load is over 20 % smaller in the airplane "
            "datum than on the ground line.",
        ],
    )
    try:
        cases = gear_case_loads(project)
    except (MissingInputError, *_CALC_ERRORS):
        cases = []
    if not cases:
        section.absent_reason = _GEAR_ABSENT
        return section

    legs = [leg for c in cases for leg in c.legs
            if any(leg.airplane) or any(leg.ground_line)]
    unstated = sorted({leg.leg for leg in legs if leg.leg_weight_lb is None})
    section.body += [
        f"{len(cases)} ground conditions are reported, covering every case "
        "LANDLOAD computes -- including the 23.499 supplementary nose-wheel "
        "family, which the assembled cases of " + section_ref("balanced") + " "
        "deliberately exclude because it carries nose reactions only and so is "
        "not an airplane in equilibrium. It is a gear-design case, and this is "
        "where it belongs: **the two ground artifacts carry different case sets "
        "by design.**",
        "**Limit of the inertia term.** " + UNSPRUNG_NOTE + ".",
        "**What this is not.** sloads has no gear kinematic model, so this "
        "report does not state drag-brace, side-brace, trunnion or axle-bending "
        "loads, and must not be read as doing so. With the contact patch, the "
        "components, the ground angle, the stroke and the reference-point "
        "reaction, a gear engineer builds those.",
    ]
    if unstated:
        section.body.append(
            "**The free body is shown open for the "
            + " and ".join(unstated) + " gear**: no leg weight is entered, so "
            "the inertia term and the net-above-trunnion column are blank rather "
            "than closed against a guessed weight. Enter the leg weight (the "
            "whole leg, trunnion down) to close it.")
    section.tables.append(_gear_stroke_table(cases, u))
    return section


def _gear_stroke_table(cases, u: Units) -> Table:
    """The strut state each attitude is computed at, per leg -- the one table.

    Chosen over a per-case reaction table because the reactions are already in
    the case tables of the results section and in the companion CSV,
    while *this* is the thing no previous deliverable stated at all: the landing
    families are computed near the top of the stroke and the handling families
    near the bottom -- impact versus sitting -- which is exactly what a gear
    analyst needs told.
    """
    seen: Dict[tuple, List[str]] = {}
    for case in cases:
        for leg in case.legs:
            key = (leg.leg, leg.strut_state, round(leg.ground_angle_deg, 3),
                   round(leg.stroke_in, 3), round(leg.stroke_fraction, 4))
            seen.setdefault(key, []).append(str(case.case))
    rows = []
    for (leg, state, angle, stroke, fraction), numbers in seen.items():
        rows.append([
            leg, state, f"{angle:.2f}",
            u.plain(stroke, "length"), f"{fraction * 100:.0f} %",
            _case_range(numbers),
        ])
    return Table(
        title="Strut state and ground angle, per attitude",
        columns=["Leg", "Strut state", "Ground angle (deg)",
                 f"Stroke from extended ({u.label('length')})", "% of stroke",
                 "LANDLOAD cases"],
        rows=rows,
    )


def _case_range(numbers: Sequence[str]) -> str:
    """``"1-6, 10-12"`` -- consecutive case numbers collapsed to runs."""
    ints = sorted(int(n) for n in numbers)
    runs: List[List[int]] = []
    for n in ints:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}-{r[-1]}" for r in runs)


# --------------------------------------------------------------------------- #
# §8 Methods and limitations + Appendix A manifest
# --------------------------------------------------------------------------- #
_REFERENCES = [
    ["Reference 1", "H. C. McMaster, *FAR 23 LOADS* — theory manual and the printed "
                    "worked examples (Appendix A, GA single, p131; Appendix B, twin "
                    "turboprop, p251) this implementation is regression-tested against."],
    ["FAA User's Guide", "DOT/FAA/AR-96/46 — module data-flow reference (Table 2.2), "
                         "the provenance of the FAR coverage matrix in "
                         + section_ref("conditions") + "."],
    ["14 CFR Part 23 Subpart C", "Flight and ground load requirements; 23.303 is the "
                                 "1.5 factor of safety applied to every case unless "
                                 "stated otherwise."],
    ["14 CFR Part 25", "Referenced only where an opt-in Part 25 case was included "
                       "(25.303 factor of safety, 25.361/25.371 engine cases)."],
]


def _section_methods(methods_text: str) -> Section:
    return Section(
        section_heading("methods"),
        body=[methods_text],
        tables=[Table(title="References", columns=["Source", "Use"], rows=_REFERENCES)],
    )


#: Both tail decks are summarised by the two tail subsections of the results
#: section, so the reference names them rather than a "Tails" heading that does
#: not exist (the suffixes are pinned against the real subsection titles by
#: ``test_report_content``).
_TAILS_REF = section_ref("results", "Horizontal tail / Vertical tail")


def _manifest_rows(comps: ComponentLoads, module_results, u: Units,
                   solver: DeliverableUnits, project: Project, run: BalancedRun,
                   mass_rows: Sequence[Dict[str, Any]]) -> List[List[str]]:
    human = f"{u.d.force.label} / {u.d.length.label} / {u.d.moment.label} / {u.d.pressure.label}"
    deck = (f"{solver.force.label} / {solver.length.label} / {solver.moment.label} / "
            f"{solver.pressure.label}")
    rows = [
        ["<project>.json", "The project inputs this report was produced from.",
         "canonical Imperial (a stored project is never converted)", "—",
         section_ref("inputs")],
        ["<project>_case_index.csv",
         "Every case ID produced by this run, mapped to its full definition.",
         "—", "IDs are verbatim, never renumbered", section_ref("conditions")],
        ["<project>_safety_factors.csv",
         "The governing safety-factor table: the authority every case's SF is "
         "derived from.", "—", "factors, not loads — nothing here is scaled",
         section_ref("factors")],
        ["METHODS.txt", "The methods & limitations statement, standalone.",
         human, "—", section_ref("methods")],
        # The bundle carries this document too, and until 2026-08-22 the
        # manifest named every file except itself (CR-C-1's class, one site the
        # review's sweep did not reach). A controlling document that does not
        # name itself is the same defect as one that does not name a deck.
        ["<project>_summary_report.tex",
         "This document, as LaTeX source — the controlling statement of the "
         "whole bundle.", human, "the basis of every other file here",
         section_ref("inputs")],
        ["<project>_summary_report.pdf",
         "This document, compiled — present only when a TeX engine ran on the "
         "Export page.", human, "identical content to the .tex beside it",
         section_ref("inputs")],
        ["load_cases/<project>_<module>.csv",
         "One row per structural load case, per module.", human,
         "LIMIT loads, SF column per case", section_ref("results")],
    ]
    if comps.wing:
        axis = comps.wing[0].torsion_axis
        rows += [
            ["sbeam/<project>_wing_span_loads.csv",
             "Station-by-station net wing shear, bending and torsion.", deck,
             f"torsion Myy about the {axis}; LIMIT",
             section_ref("results", "Wing")],
            ["sbeam/<project>_wing_applied_loads.csv",
             "The applied wing load set: one row per strip and one per "
             "concentrated wing mass, each at its own point, as all six "
             "body-axis components. Nothing in it is a running total; Fy, Mx "
             "and Mz are zero throughout and are printed so a zero cannot be "
             "read as an omission.", deck,
             f"free torsion about the {axis}; LIMIT",
             section_ref("results", "Wing")],
            ["sbeam/<project>_wing_loads.bdf",
             "FORCE/MOMENT bulk data for the wing.", deck,
             f"torsion about the {axis}; LIMIT", section_ref("results", "Wing")],
            ["sbeam/<project>_wing_stick.bdf", "CBAR stick model of the wing beam.",
             deck, "geometry only", section_ref("results", "Wing")],
        ]
    if comps.body:
        rows += [
            ["sbeam/<project>_fuselage_span_loads.csv",
             "Station-by-station fuselage net shear, bending and torsion.", deck,
             "torsion Mxx about the body X axis; LIMIT",
             section_ref("results", "Fuselage")],
            ["sbeam/<project>_fuselage_loads.bdf",
             "FORCE/MOMENT bulk data for the fuselage.", deck, "LIMIT",
             section_ref("results", "Fuselage")],
            ["sbeam/<project>_fuselage_fitting_loads.csv",
             "Wing-attach front/rear spar fitting loads.", deck,
             "already carried by the span loads — do not superpose",
             section_ref("results", "Fuselage")],
        ]
    if comps.tail:
        rows += [
            ["sbeam/<project>_tail_chordwise.csv",
             "Chordwise tail load intensities per critical condition.", deck,
             "leading-edge-first stations; Fn is normal to the surface (Axis "
             "column: h-tail Fz, fin Fy); LIMIT", _TAILS_REF],
            ["sbeam/<project>_tail_loads.bdf", "FORCE/MOMENT bulk data for the tails.",
             deck, "loads normal to each surface — h-tail Fz, fin Fy; LIMIT",
             _TAILS_REF],
        ]
    if comps.control:
        rows += [
            ["sbeam/<project>_control_surface_loads.csv",
             "Simplified chordwise control-surface distributions.", deck,
             "standard simplified distributions; LIMIT",
             section_ref("results", "Control surfaces")],
            ["sbeam/<project>_control_surface_loads.bdf",
             "FORCE/MOMENT bulk data for the control surfaces.", deck, "LIMIT",
             section_ref("results", "Control surfaces")],
        ]
    # The assembled deliverable and its mass model. Listed here for the reason
    # the manifest exists at all: an artifact the controlling document does not
    # name travels without a basis, and these two are the mission's primary
    # output and the independent check on its inertia half (review F-D2, D-R2).
    if run.cases:
        rows.append([
            "sbeam/<project>_balanced_airframe.bdf",
            "The assembled full-span free-free deck: one SUBCASE per balanced "
            "case, both wings, aero and inertia together.", deck,
            "LIMIT; determinate support, its reaction is the residual",
            section_ref("balanced")])
    # The LRA beam model (step 12, note 24 R-1) -- the third deliverable, and
    # the one the F-D2 class re-opened on (CR-C-1): it shipped in the bundle from
    # 0.6.0 with no row here. Gated on the model *building*, not merely on cases
    # existing: ``lra_model_bdf`` refuses a project missing a datum it must not
    # guess (no SOB, no ref axis, no outline, no spars, a strip-pair h-tail
    # attachment), and ``concept_heavy`` is such a project -- it assembles
    # balanced cases and produces no LRA deck. A row gated on ``run.cases``
    # would name a file that bundle does not carry, which is this same defect
    # pointing the other way. The cost is one model build per document, the
    # price ``_gear_cases`` already pays for the gear row.
    if run.cases and _lra_model(project, run) is not None:
        rows.append([
            "sbeam/<project>_lra_model.bdf",
            "The loads-reference-axis beam model: CBAR wing/body/tail beams, "
            "RBE2 attachments, and the balanced-case loads applied to them.",
            deck, "LIMIT; torsion about each surface's LRA",
            section_ref("balanced")])
    if project.weight is not None and project.weight.items:
        rows.append([
            "sbeam/<project>_mass_model.bdf",
            "CONM2 mass model + one MASSSET per payload case, for splicing into "
            "a model that already has nodes.", deck,
            "mass, NOT weight; do not apply with the load decks",
            section_ref("balanced")])
    if _try(_gear_cases, project):
        rows.append([
            "<project>_gear_loads.csv",
            "The gear interface load definition: per case and per leg, the "
            "reaction at the tyre contact patch with its strut state and ground "
            "angle, and the same reaction at the gear reference point.", deck,
            "LIMIT; contact patch ground-line, reference point airplane-datum",
            section_ref("gear")])
    if any(r["exported"] for r in mass_rows):
        rows += [
            ["sbeam/<project>_mass_check.bdf",
             "Self-contained runnable deck: MASSSET + GRAV, and deliberately no "
             "load cards.", deck, "no load cards, by construction",
             section_ref("balanced")],
            ["sbeam/<project>_inertia_only.bdf",
             "sloads' own nodal inertia set, for comparison against what the "
             "solver recovers.", deck,
             # CR-C-3: the cell said ULTIMATE and the file said LIMIT, in
             # band, by design -- factoring one side of a comparison and not the
             # other is how you make a check pass while meaning nothing, and the
             # manifest was out by 1.5x on the one artifact whose whole purpose
             # is to be compared. Under note 49 OR-116 the whole bundle is LIMIT
             # and this row is no longer the exception; the parenthetical stays
             # because "no SF" here means the factor is not even *prescribed*,
             # which is still narrower than the rest of the deck column.
             "LIMIT (no SF) — comparison only, never applied",
             section_ref("balanced")],
        ]
    if module_results:
        rows.append(["<project>_report.txt",
                     "Plain-text per-module report of every condition.", human,
                     "LIMIT", section_ref("results")])
    return rows


def _lra_model(project: Project, run: BalancedRun) -> Optional[str]:
    """The LRA beam deck, or ``None`` when the model refuses -- so the manifest
    lists it only when the bundle actually carries one (CR-C-1).

    ``LraRefusal`` is a ``ValueError``, so :func:`_try` catches it: a refused
    model is a stated absence (the CLI route prints the missing datum), and here
    that absence is simply one fewer manifest row.
    """
    from ..export.lra_model import lra_model_bdf

    return _try(lra_model_bdf, project, cases=run.cases)


def _gear_cases(project: Project):
    """The gear free bodies, or ``None`` -- so the manifest lists the companion
    file only when the run actually produces one."""
    from ..gear_loads import gear_case_loads

    return gear_case_loads(project) or None


def mass_case_data(project: Project) -> List[Dict[str, Any]]:
    """The exported mass model's per-payload-case rows, defensively (see
    :func:`sloads.export.mass_cards.mass_case_rows`). Built once per document and
    read by both §6 and the manifest, like :func:`balanced_run`."""
    from ..export.mass_cards import mass_case_rows

    return _try(mass_case_rows, project) or []


def _section_manifest(comps: ComponentLoads, module_results, u: Units,
                      project: Project, run: BalancedRun,
                      mass_rows: Sequence[Dict[str, Any]]) -> Section:
    solver = deliverable_units(u.system, Channel.SOLVER)
    same = (u.d.force.label, u.d.length.label, u.d.moment.label, u.d.pressure.label) == (
        solver.force.label, solver.length.label, solver.moment.label, solver.pressure.label)
    opening = (
        f"Every file in this bundle is written in {system_name(u.system)}. "
        f"Human-readable deliverables are in {units_statement(u.d)}"
    )
    opening += (
        "; the sbeam solver decks and their companion CSVs use the dimensionally "
        f"consistent set {units_statement(solver)}, because a deck whose GRID "
        "coordinates are millimetres and whose FORCE cards are newtons is only "
        "correct when its MOMENT cards are N*mm and its pressures MPa."
        if not same else " throughout."
    )
    return Section(
        "Appendix A. Bundle manifest",
        body=[opening + " " + AVIATION_UNITS_NOTE],
        tables=[Table(
            title="Companion files",
            columns=["File", "Contents", "Units", "Conventions", "Summarised in"],
            rows=_manifest_rows(comps, module_results, u, solver, project, run,
                                mass_rows),
            small=True,
            note="A distribution file is not usable without its torsion axis and its "
                 "load basis, so both are stated here as well as in the file itself.",
        )],
    )


# --------------------------------------------------------------------------- #
# The document
# --------------------------------------------------------------------------- #
def _badge(project: Project) -> str:
    if project.is_concept:
        return "Concept (C) — unverified extrapolation"
    category = (project.speeds.category if project.speeds is not None else "") or "(not set)"
    return f"FAR 23 — category {category}"


def _control_rows(project: Project, generated: Optional[str], tool_version: str,
                  u: Units) -> List[Tuple[str, str]]:
    rows = [
        ("Project", project.name or "(unnamed)"),
        ("Description", project.description),
        ("Engineer", project.engineer),
        ("Date", project.date),
        ("Revision", project.revision),
        ("Checked by", project.checked_by),
        ("Approved by", project.approved_by),
        ("Certification basis", _badge(project)),
        ("Tool", f"{TOOL_NAME} {tool_version}".strip()),
        ("Project schema version", str(SCHEMA_VERSION)),
        ("Units", units_statement(u.d)),
        ("Generated", generated or ""),
    ]
    # A blank control field is *shown* as blank rather than dropped for the four
    # signature/revision rows: an empty "Checked by" line is the signature block
    # §4.1 requires, whereas a missing row reads as an oversight.
    always = {"Project", "Engineer", "Date", "Revision", "Checked by", "Approved by",
              "Certification basis", "Tool", "Project schema version", "Units"}
    return [(k, v) for k, v in rows if v or k in always]


def build_report(
    project: Project,
    *,
    system: UnitSystem = UnitSystem.IMPERIAL,
    generated: Optional[str] = None,
    tool_version: str = "",
    scope: str = "",
    deselected_case_ids: Optional[Sequence[str]] = None,
    module_results=None,
    components: Optional[ComponentLoads] = None,
) -> ReportDocument:
    """Build the whole :class:`ReportDocument` for ``project``.

    ``system`` is the bundle's unit system and must be the same value every writer
    in that bundle was given (§3.5). ``generated`` is the caller's timestamp
    string -- nothing here reads the clock, so two builds of one project at one
    unit selection are identical.

    ``module_results``/``components`` let a caller that has already computed them
    (the Export page builds both for the CSV/BDF channels) pass them in, so a
    bundle computes each result exactly once and the report cannot describe
    different numbers from the files beside it.
    """
    from ..registry import run_all_modules

    u = Units(system)
    if module_results is None:
        module_results = _try(run_all_modules, project) or []
    comps = components if components is not None else component_loads(project)
    deselected = list(deselected_case_ids or [])
    # Assembled once, read by §4's skipped-conditions table, §6 and the manifest.
    run = balanced_run(project)
    mass_rows = mass_case_data(project)

    methods = methods_statement(
        project, generated=generated, tool_version=tool_version, scope=scope,
        deselected_case_ids=deselected or None, system=system,
    )
    return ReportDocument(
        title="Structural Design Loads — Summary Report",
        project_name=project.name or "(unnamed)",
        control=_control_rows(project, generated, tool_version, u),
        badge=_badge(project),
        basis=BASIS_STATEMENT,
        units_note=f"Units: {units_statement(u.d)}. {AVIATION_UNITS_NOTE}",
        sections=[
            _section_inputs(project, u),
            _section_conventions(),
            _factors_section(project, module_results, comps, run),
            _section_envelopes(project, u),
            _section_conditions(project, module_results, comps, scope, deselected,
                                run),
            _section_results(project, module_results, comps, u, deselected),
            _section_balanced(run, mass_rows, u),
            _section_gear(project, u),
            _section_methods(methods),
            _section_manifest(comps, module_results, u, project, run, mass_rows),
        ],
        methods=methods,
        system=system,
    )


__all__ = [
    "AVIATION_UNITS_NOTE",
    "BASIS_STATEMENT",
    "BalancedRun",
    "ComponentLoads",
    "Figure",
    "PlotData",
    "ReportDocument",
    "Section",
    "Series",
    "Table",
    "Units",
    "balanced_run",
    "build_report",
    "component_loads",
    "mass_case_data",
]
