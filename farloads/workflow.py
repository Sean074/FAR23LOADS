"""The loads workflow as ordered, dependency-aware steps.

This is the single source of truth for *what the suite does and in what order*:
each :class:`WorkflowStep` names the calc module behind it (``module``), the
project slice(s) it needs (``requires``) and the slice it produces (``produces``),
grouped into the workflow sections the GUI presents. Since Step G2 (Phase G) the
sections follow the FAR 23 analysis flow -- a **Start** app-shell group followed by
the six analysis-flow phases **Develop V-n diagram → Flight loads → Other loads →
Landing loads → Load-case plotting → Export** (see
``docs/30_future/03_gui_rework_plan.md`` §4; this supersedes the Phase-D
Start/Airplane/Envelopes/Analysis grouping in ``02_gui_workflow_plan.md``).

It is pure metadata plus pure predicates over a :class:`~farloads.models.Project`
(no Streamlit, no I/O), so the GUI navigation, the Home dashboard's completeness
panel, and any future dependency-ordered "run pipeline" can all be driven from
one place instead of drifting apart. ``requires``/``produces`` are the seed of a
real dependency DAG (see the backlog's Option-C pipeline engine).

``produces`` accepts a dotted path (e.g. ``"weight.envelope"``) so a step whose
real output is a sub-field of a slice can still report completeness precisely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .models import Project

# --------------------------------------------------------------------------- #
# Phases (ordered) -- Start app-shell + the six analysis-flow sections (Step G2,
# see docs/30_future/03_gui_rework_plan.md §4).
# --------------------------------------------------------------------------- #
START = "Start"
DEVELOP_VN = "Develop V-n diagram"
FLIGHT_LOADS = "Flight loads"
OTHER_LOADS = "Other loads"
LANDING = "Landing loads"
LOADS_PLOTTING = "Load-case plotting"
EXPORT = "Export"

#: The workflow phases in presentation order.
PHASES: Tuple[str, ...] = (
    START, DEVELOP_VN, FLIGHT_LOADS, OTHER_LOADS, LANDING, LOADS_PLOTTING, EXPORT,
)


@dataclass(frozen=True)
class WorkflowStep:
    """One step of the loads workflow.

    ``key``      stable identifier (also the GUI view-file stem).
    ``title``    human label shown in navigation and the dashboard.
    ``phase``    one of :data:`PHASES`.
    ``module``   the :mod:`farloads.registry` module name behind the step, or
                 ``None`` for a GUI-only view (dashboard / results / export).
    ``requires`` project-slice attribute names that must be present to run.
    ``produces`` dotted attribute path the step fills, or ``None`` for a
                 derived-only view (it shows results but persists no new slice).
    ``bas``      the original McMaster program(s), or ``None`` for a modern page.
    ``summary``  one-line description for tooltips/help.
    """

    key: str
    title: str
    phase: str
    module: Optional[str] = None
    requires: Tuple[str, ...] = ()
    produces: Optional[str] = None
    bas: Optional[str] = None
    summary: str = ""


# --------------------------------------------------------------------------- #
# The steps, in workflow order within each phase
# --------------------------------------------------------------------------- #
STEPS: Tuple[WorkflowStep, ...] = (
    # ---- Start: app shell -- landing / project management -------------------- #
    # Not part of the FAR 23 analysis flow; the two app-shell pages that carry the
    # project itself (Step G2 keeps a dedicated Start group above the six
    # analysis-flow phases -- see 03_gui_rework_plan.md §4).
    WorkflowStep("dashboard", "Project Dashboard", START,
                 module=None, produces=None, bas=None,
                 summary="Load/save the project and see workflow progress at a glance."),
    WorkflowStep("project_editor", "Project JSON Editor", START,
                 module=None, produces=None, bas=None,
                 summary="Review/hand-edit the whole project as JSON, in the "
                         "sidebar's selected Imperial/SI units."),

    # ---- Develop V-n diagram: define the airplane & load environment --------- #
    # §4 Phase 1, consolidated to five sub-steps 1a–1e (Step G3). Each merged page
    # gathers several formerly-separate pages as st.tabs; the secondary calc modules
    # are folded via FOLDED_MODULES (the wing_inertia precedent), so each sub-step
    # names one primary module/produces and the others still have registered
    # modules/tests without a nav step of their own.
    #
    # 1a. Geometry -- Step G1 merged the parametric layout + WINGGEOM planform
    # pages into one Geometry page (the single geometry source of truth). The
    # wing_geometry calc module is folded in; this one step owns the geometry slice.
    WorkflowStep("configuration_layout", "Geometry", DEVELOP_VN,
                 module="configuration", produces="geometry", bas="WINGGEOM",
                 summary="Single geometry source of truth: parametric fuselage/wing/"
                         "tail/gear, fuselage outline, and WINGGEOM surface planforms."),
    # 1b. Weight & mass properties -- Step G3 merged Weight Estimate (WTESTIMA),
    # Weight/CG/Inertia (WTONECG), Payload Cases and Weight/CG Envelope (WTENV) into
    # one tabbed page that owns all weight/mass data. weight_estimate + weight_envelope
    # are folded; weight_onecg is the primary (produces mass, the downstream gate).
    WorkflowStep("weight_mass", "Weight & Mass Properties", DEVELOP_VN,
                 module="weight_onecg", requires=("weight",), produces="mass",
                 bas="WTESTIMA+WTONECG+WTENV",
                 summary="All weight/mass data: statistical estimate, itemised mass "
                         "properties (weight/CG/inertia), loading scenarios, and the "
                         "CG envelope."),
    # 1c. Aerodynamic data. Owns the maximum lift coefficients (CLmax); STRSPEED
    # (1d) derives the stall speeds VS/VSF from them (M1-1b single-source), so this
    # page precedes Structural Speeds. The FLTLOADS balance-geometry/CG inputs stay
    # on the V-n page (1e) per decision to keep those inputs where they run.
    WorkflowStep("aero_coefficients", "Aerodynamic Data", DEVELOP_VN,
                 module=None, produces="aero_coeffs", bas=None,
                 summary="Maximum lift coefficients (CLmax) + airplane-less-tail aero "
                         "coefficients (cruise + flaps-down) for the flight envelope "
                         "balance. Per-surface spanwise (Schrenk) aero is entered on "
                         "the Wing Loads page."),
    # 1d. Structural design speeds -- Step G3 merged STRSPEED design speeds and the
    # MACHLIM speed–altitude envelope into one tabbed page; mach_limit is folded.
    # Requires aero_coeffs for the CLmax that sets VS/VSF (M1-1b).
    WorkflowStep("structural_speeds", "Structural Speeds", DEVELOP_VN,
                 module="structural_speeds", requires=("aero_coeffs",),
                 produces="speeds", bas="STRSPEED+MACHLIM",
                 summary="FAR 23 design speeds VA/VC/VD/VS + the speed–altitude "
                         "flight-limits (Mach) envelope."),
    # 1e. V-n diagram + governing conditions -- Step G3 merged the FLTLOADS V-n page
    # and the SELECT critical-loads page into one tabbed page; select is folded.
    WorkflowStep("flight_envelope", "Flight Envelope (V-n)", DEVELOP_VN,
                 module="flight_envelope", requires=("speeds", "aero_coeffs"),
                 produces="flight_loads", bas="FLTLOADS+SELECT",
                 summary="V-n diagram + balancing tail loads, and the governing "
                         "wing/tail/fuselage conditions SELECT prunes from the matrix."),

    # ---- Flight loads: distributed wing / fuselage / tail loads (§4 Phase 2) - #
    # Wing Loads and Tail Loads each merge two independently-registered calc
    # modules onto one page (Step D6, decision D-7); the secondary module of
    # each pair is listed in FOLDED_MODULES below, mirroring the wing_inertia
    # precedent -- it still has its own registered module/tests, it just has
    # no dedicated nav step of its own.
    WorkflowStep("wing_loads", "Wing Loads", FLIGHT_LOADS,
                 module="net_loads", requires=("geometry",), produces="wing_mass",
                 bas="AIRLOADS+WINGINER+NETLOADS",
                 summary="Schrenk air loads + spanwise shear / bending / torsion "
                         "(air − inertia)."),
    WorkflowStep("fuselage_loads", "Fuselage Loads", FLIGHT_LOADS,
                 module="body_loads", requires=("flight_loads",), produces="fuselage_mass",
                 bas="NETLOADS", summary="Net fuselage shear / bending."),
    WorkflowStep("tail_loads", "Tail Loads", FLIGHT_LOADS,
                 module="taildist", requires=("flight_loads", "tail_loads"), produces=None,
                 bas="TAILDIST+BALLOADS",
                 summary="Chordwise tail-load distribution + balancing-load cross-check."),

    # ---- Other loads: control-surface + engine-mount reactions (§4 Phase 3) -- #
    WorkflowStep("aileron_loads", "Aileron Loads", OTHER_LOADS,
                 module="aileron", requires=("speeds",), produces="aileron_loads",
                 bas="AILERON", summary="Aileron design loads."),
    WorkflowStep("flap_loads", "Flap Loads", OTHER_LOADS,
                 module="flap", requires=("speeds",), produces="flap_loads",
                 bas="FLAPLOAD", summary="Flap design loads."),
    WorkflowStep("tab_loads", "Tab Loads", OTHER_LOADS,
                 module="tab", requires=("speeds",), produces="tab_loads",
                 bas="TABLOADS", summary="Control-surface tab loads."),
    WorkflowStep("engine_mount", "Engine Mount Loads", OTHER_LOADS,
                 module="engine", requires=("engines",), produces=None, bas="ENGLOADS",
                 summary="Engine-mount reaction loads (incl. gyroscopic)."),
    WorkflowStep("one_engine_out", "One Engine Out", OTHER_LOADS,
                 module="one_engine_out", requires=("mass", "vtail_loads"),
                 produces="one_engine_out", bas="ONENGOUT",
                 summary="One-engine-out vertical-tail loads."),

    # ---- Landing loads (§4 Phase 4) ------------------------------------------ #
    WorkflowStep("landing_loads", "Landing Loads", LANDING,
                 module="landing", requires=("mass",), produces="landing",
                 bas="LGFACTOR+LANDLOAD", summary="Landing load factors + gear reactions."),

    # ---- Load-case plotting: consolidated plots (Step D7, §4 Phase 5) -------- #
    WorkflowStep("loads_plots", "Loads Plots", LOADS_PLOTTING,
                 module=None, produces=None, bas=None,
                 summary="Overlay shear/moment/torsion by case ID, envelope curves, "
                         "whole-airframe view, and external-CSV comparison."),

    # ---- Export: hand off to downstream tools (§4 Phase 6) ------------------- #
    WorkflowStep("aircraft_comparison", "Aircraft Comparison", EXPORT,
                 module=None, produces=None, bas=None,
                 summary="Place the design against similar aircraft."),
    WorkflowStep("results_review", "Results Review", EXPORT,
                 module=None, produces=None, bas=None,
                 summary="Consolidated governing loads across every component."),
    WorkflowStep("export_report", "Export & Report", EXPORT,
                 module=None, produces=None, bas=None,
                 summary="Project JSON, per-module load CSVs, and sbeam BDF cards."),
)

#: Steps keyed by ``key`` for O(1) lookup.
BY_KEY: Dict[str, WorkflowStep] = {s.key: s for s in STEPS}

#: Calc modules folded into another step (contributors, not their own page).
#: WINGINER's inertia loads are combined with NETLOADS on the Wing Loads page;
#: AIRLOADS (Schrenk) is also combined there (Step D6). BALLOADS's balancing-load
#: cross-check is combined with TAILDIST on the Tail Loads page (Step D6).
#: WINGGEOM (wing_geometry) is combined onto the one Geometry page (Step G1), which
#: names the ``configuration`` module -- so wing_geometry has no dedicated step.
#: Step G3 folds four more: weight_estimate + weight_envelope onto the Weight & Mass
#: Properties page (weight_onecg is its named module), mach_limit onto Structural
#: Speeds, and select onto the Flight Envelope (V-n) page.
FOLDED_MODULES: Tuple[str, ...] = (
    "wing_inertia", "airloads", "balloads", "wing_geometry",
    "weight_estimate", "weight_envelope", "mach_limit", "select",
)


# --------------------------------------------------------------------------- #
# Predicates over a Project
# --------------------------------------------------------------------------- #
def _resolve(project: Project, dotted: str):
    """Walk a dotted attribute path; return the value or ``None`` if any segment
    is missing/None. Empty lists, tuples and strings count as *absent*."""
    obj = project
    for seg in dotted.split("."):
        obj = getattr(obj, seg, None)
        if obj is None:
            return None
    if isinstance(obj, (list, tuple, str)) and len(obj) == 0:
        return None
    return obj


def has(project: Project, dotted: str) -> bool:
    """True if ``dotted`` resolves to a present (non-empty) value on ``project``."""
    return _resolve(project, dotted) is not None


def requirements_met(project: Project, step: WorkflowStep) -> bool:
    """True if every slice in ``step.requires`` is present on ``project``."""
    return all(has(project, attr) for attr in step.requires)


def is_produced(project: Project, step: WorkflowStep) -> bool:
    """True if ``step.produces`` is present (a derived-only step is never 'produced')."""
    return step.produces is not None and has(project, step.produces)


def missing_requirements(project: Project, step: WorkflowStep) -> List[str]:
    """The required slices that are not yet present (empty when ready to run)."""
    return [attr for attr in step.requires if not has(project, attr)]


def steps_in_phase(phase: str) -> List[WorkflowStep]:
    """All steps in ``phase``, in workflow order."""
    return [s for s in STEPS if s.phase == phase]


def by_phase() -> Dict[str, List[WorkflowStep]]:
    """Ordered mapping of phase → its steps."""
    return {phase: steps_in_phase(phase) for phase in PHASES}
