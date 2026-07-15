"""The loads workflow as ordered, dependency-aware steps.

This is the single source of truth for *what the suite does and in what order*:
each :class:`WorkflowStep` names the calc module behind it (``module``), the
project slice(s) it needs (``requires``) and the slice it produces (``produces``),
grouped into the six workflow sections the GUI presents -- **Start → Airplane →
Envelopes & Critical Conditions → Analysis → Loads Plots → Export** (Phase D,
see ``docs/30_future/02_gui_workflow_plan.md``).

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
# Phases (ordered) -- the six Phase-D GUI sections
# --------------------------------------------------------------------------- #
START = "Start"
AIRPLANE = "Airplane"
ENVELOPES = "Envelopes & Critical Conditions"
ANALYSIS = "Analysis"
LOADS_PLOTS = "Loads Plots"
EXPORT = "Export"

#: The workflow phases in presentation order.
PHASES: Tuple[str, ...] = (START, AIRPLANE, ENVELOPES, ANALYSIS, LOADS_PLOTS, EXPORT)


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
    # ---- Start: landing / project management -------------------------------- #
    WorkflowStep("dashboard", "Project Dashboard", START,
                 module=None, produces=None, bas=None,
                 summary="Load/save the project and see workflow progress at a glance."),
    WorkflowStep("project_editor", "Project JSON Editor", START,
                 module=None, produces=None, bas=None,
                 summary="Review/hand-edit the whole project as JSON, in the "
                         "sidebar's selected Imperial/SI units."),

    # ---- Airplane: geometry, weight, mass, design speeds --------------------- #
    WorkflowStep("configuration_layout", "Configuration & Layout", AIRPLANE,
                 module="configuration", produces="configuration", bas=None,
                 summary="Parametric geometry source of truth + fleet comparison."),
    WorkflowStep("wing_geometry", "Wing / Surface Geometry", AIRPLANE,
                 module="wing_geometry", produces="geometry", bas="WINGGEOM",
                 summary="Lifting-surface planform polylines."),
    WorkflowStep("weight_estimate", "Weight Estimate", AIRPLANE,
                 module="weight_estimate", produces="weight.estimation", bas="WTESTIMA",
                 summary="Statistical empty-weight / MTOW sanity estimate."),
    WorkflowStep("weight_cg_inertia", "Weight, CG & Inertia", AIRPLANE,
                 module="weight_onecg", requires=("weight",), produces="mass",
                 bas="WTONECG", summary="Itemised mass properties: weight, CG, inertia."),
    WorkflowStep("structural_speeds", "Structural Speeds", AIRPLANE,
                 module="structural_speeds", produces="speeds", bas="STRSPEED",
                 summary="FAR 23 design speeds VA/VC/VD/VS."),
    WorkflowStep("aero_coefficients", "Aero Coefficients", AIRPLANE,
                 module=None, produces="aero_coeffs", bas=None,
                 summary="Airplane-less-tail aero coefficients (cruise + flaps-down) "
                         "for the flight envelope balance."),

    # ---- Envelopes & Critical Conditions: the load environment --------------- #
    WorkflowStep("payload_cases", "Weight/CG Grid & Payload Cases", ENVELOPES,
                 module=None, requires=("weight",), produces="weight.cg_cases", bas=None,
                 summary="Named loading scenarios shared by the CG envelope and the "
                         "flight-envelope balance."),
    WorkflowStep("weight_envelope", "Weight / CG Envelope", ENVELOPES,
                 module="weight_envelope", requires=("geometry", "weight"),
                 produces="weight.envelope", bas="WTENV",
                 summary="Loading CG envelope vs limits."),
    WorkflowStep("mach_limit", "Mach Limit", ENVELOPES,
                 module="mach_limit", requires=("speeds",), produces="speeds.mach_limit",
                 bas="MACHLIM", summary="Mach-limited speed boundary."),
    WorkflowStep("flight_envelope", "Flight Envelope (V-n)", ENVELOPES,
                 module="flight_envelope", requires=("speeds", "aero_coeffs"),
                 produces="flight_loads", bas="FLTLOADS",
                 summary="V-n diagram + balancing tail loads (the load environment)."),
    WorkflowStep("critical_loads", "Critical Loads (SELECT)", ENVELOPES,
                 module="select", requires=("flight_loads",), produces="envelope.critical",
                 bas="SELECT",
                 summary="Governing wing/tail/fuselage conditions from the V-n matrix."),

    # ---- Analysis: the structural loads -------------------------------------- #
    # Wing Loads and Tail Loads each merge two independently-registered calc
    # modules onto one page (Step D6, decision D-7); the secondary module of
    # each pair is listed in FOLDED_MODULES below, mirroring the wing_inertia
    # precedent -- it still has its own registered module/tests, it just has
    # no dedicated nav step of its own.
    WorkflowStep("wing_loads", "Wing Loads", ANALYSIS,
                 module="net_loads", requires=("geometry",), produces="wing_mass",
                 bas="AIRLOADS+WINGINER+NETLOADS",
                 summary="Schrenk air loads + spanwise shear / bending / torsion "
                         "(air − inertia)."),
    WorkflowStep("fuselage_loads", "Fuselage Loads", ANALYSIS,
                 module="body_loads", requires=("flight_loads",), produces="fuselage_mass",
                 bas="NETLOADS", summary="Net fuselage shear / bending."),
    WorkflowStep("tail_loads", "Tail Loads", ANALYSIS,
                 module="taildist", requires=("flight_loads", "tail_loads"), produces=None,
                 bas="TAILDIST+BALLOADS",
                 summary="Chordwise tail-load distribution + balancing-load cross-check."),
    WorkflowStep("aileron_loads", "Aileron Loads", ANALYSIS,
                 module="aileron", requires=("speeds",), produces="aileron_loads",
                 bas="AILERON", summary="Aileron design loads."),
    WorkflowStep("flap_loads", "Flap Loads", ANALYSIS,
                 module="flap", requires=("speeds",), produces="flap_loads",
                 bas="FLAPLOAD", summary="Flap design loads."),
    WorkflowStep("tab_loads", "Tab Loads", ANALYSIS,
                 module="tab", requires=("speeds",), produces="tab_loads",
                 bas="TABLOADS", summary="Control-surface tab loads."),
    WorkflowStep("landing_loads", "Landing Loads", ANALYSIS,
                 module="landing", requires=("mass",), produces="landing",
                 bas="LGFACTOR+LANDLOAD", summary="Landing load factors + gear reactions."),
    WorkflowStep("engine_mount", "Engine Mount Loads", ANALYSIS,
                 module="engine", requires=("engines",), produces=None, bas="ENGLOADS",
                 summary="Engine-mount reaction loads (incl. gyroscopic)."),
    WorkflowStep("one_engine_out", "One Engine Out", ANALYSIS,
                 module="one_engine_out", requires=("mass", "vtail_loads"),
                 produces="one_engine_out", bas="ONENGOUT",
                 summary="One-engine-out vertical-tail loads."),

    # ---- Loads Plots: consolidated plots (Step D7) --------------------------- #
    WorkflowStep("loads_plots", "Loads Plots", LOADS_PLOTS,
                 module=None, produces=None, bas=None,
                 summary="Overlay shear/moment/torsion by case ID, envelope curves, "
                         "whole-airframe view, and external-CSV comparison."),

    # ---- Export: hand off to downstream tools -------------------------------- #
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
FOLDED_MODULES: Tuple[str, ...] = ("wing_inertia", "airloads", "balloads")


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
