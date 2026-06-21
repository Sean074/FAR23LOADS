"""The loads workflow as ordered, dependency-aware steps.

This is the single source of truth for *what the suite does and in what order*:
each :class:`WorkflowStep` names the calc module behind it (``module``), the
project slice(s) it needs (``requires``) and the slice it produces (``produces``),
grouped into the four workflow phases the GUI presents -- **Define → Analyze →
Review → Export**.

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
# Phases (ordered)
# --------------------------------------------------------------------------- #
DEFINE = "Define"
ANALYZE = "Analyze"
REVIEW = "Review"
EXPORT = "Export"

#: The workflow phases in presentation order.
PHASES: Tuple[str, ...] = (DEFINE, ANALYZE, REVIEW, EXPORT)


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
    # ---- Define: geometry, mass, and the operating/load environment --------- #
    WorkflowStep("configuration_layout", "Configuration & Layout", DEFINE,
                 module="configuration", produces="configuration", bas=None,
                 summary="Parametric geometry source of truth + fleet comparison."),
    WorkflowStep("wing_geometry", "Wing / Surface Geometry", DEFINE,
                 module="wing_geometry", produces="geometry", bas="WINGGEOM",
                 summary="Lifting-surface planform polylines."),
    WorkflowStep("airloads", "Wing Airloads (Schrenk)", DEFINE,
                 module="airloads", requires=("geometry",), produces="aero",
                 bas="AIRLOADS", summary="Spanwise wing air-load distribution."),
    WorkflowStep("weight_estimate", "Weight Estimate", DEFINE,
                 module="weight_estimate", produces="weight.estimation", bas="WTESTIMA",
                 summary="Statistical empty-weight / MTOW sanity estimate."),
    WorkflowStep("weight_cg_inertia", "Weight, CG & Inertia", DEFINE,
                 module="weight_onecg", requires=("weight",), produces="mass",
                 bas="WTONECG", summary="Itemised mass properties: weight, CG, inertia."),
    WorkflowStep("weight_envelope", "Weight / CG Envelope", DEFINE,
                 module="weight_envelope", requires=("geometry", "weight"),
                 produces="weight.envelope", bas="WTENV",
                 summary="Loading CG envelope vs limits."),
    WorkflowStep("structural_speeds", "Structural Speeds", DEFINE,
                 module="structural_speeds", produces="speeds", bas="STRSPEED",
                 summary="FAR 23 design speeds VA/VC/VD/VS."),
    WorkflowStep("mach_limit", "Mach Limit", DEFINE,
                 module="mach_limit", requires=("speeds",), produces="speeds.mach_limit",
                 bas="MACHLIM", summary="Mach-limited speed boundary."),
    WorkflowStep("flight_envelope", "Flight Envelope (V-n)", DEFINE,
                 module="flight_envelope", requires=("speeds",), produces="flight_loads",
                 bas="FLTLOADS",
                 summary="V-n diagram + balancing tail loads (the load environment)."),

    # ---- Analyze: the structural loads ------------------------------------- #
    WorkflowStep("net_wing_loads", "Net Wing Loads", ANALYZE,
                 module="net_loads", requires=("geometry", "aero"), produces="wing_mass",
                 bas="WINGINER+NETLOADS",
                 summary="Spanwise shear / bending / torsion = air − inertia."),
    WorkflowStep("fuselage_loads", "Fuselage Loads", ANALYZE,
                 module="body_loads", requires=("flight_loads",), produces="fuselage_mass",
                 bas="NETLOADS", summary="Net fuselage shear / bending."),
    WorkflowStep("tail_distribution", "Tail Distribution", ANALYZE,
                 module="taildist", requires=("tail_loads",), produces=None,
                 bas="TAILDIST", summary="Chordwise tail-load distribution."),
    WorkflowStep("aileron_loads", "Aileron Loads", ANALYZE,
                 module="aileron", requires=("speeds",), produces="aileron_loads",
                 bas="AILERON", summary="Aileron design loads."),
    WorkflowStep("flap_loads", "Flap Loads", ANALYZE,
                 module="flap", requires=("speeds",), produces="flap_loads",
                 bas="FLAPLOAD", summary="Flap design loads."),
    WorkflowStep("tab_loads", "Tab Loads", ANALYZE,
                 module="tab", requires=("speeds",), produces="tab_loads",
                 bas="TABLOADS", summary="Control-surface tab loads."),
    WorkflowStep("landing_loads", "Landing Loads", ANALYZE,
                 module="landing", requires=("mass",), produces="landing",
                 bas="LGFACTOR+LANDLOAD", summary="Landing load factors + gear reactions."),
    WorkflowStep("engine_mount", "Engine Mount Loads", ANALYZE,
                 module="engine", requires=("engines",), produces=None, bas="ENGLOADS",
                 summary="Engine-mount reaction loads (incl. gyroscopic)."),
    WorkflowStep("one_engine_out", "One Engine Out", ANALYZE,
                 module="one_engine_out", requires=("mass", "vtail_loads"),
                 produces="one_engine_out", bas="ONENGOUT",
                 summary="One-engine-out vertical-tail loads."),

    # ---- Review: pick the governing loads, verify, summarise --------------- #
    WorkflowStep("critical_loads", "Critical Loads (SELECT)", REVIEW,
                 module="select", requires=("flight_loads",), produces="envelope.critical",
                 bas="SELECT",
                 summary="Governing wing/tail/fuselage conditions from the V-n matrix."),
    WorkflowStep("balanced_tail_verification", "Balanced-Tail Verification", REVIEW,
                 module="balloads", requires=("flight_loads", "tail_loads"), produces=None,
                 bas="BALLOADS", summary="Cross-check the balancing tail loads."),
    WorkflowStep("results_review", "Results Review", REVIEW,
                 module=None, produces=None, bas=None,
                 summary="Consolidated governing loads across every component."),

    # ---- Export: hand off to downstream tools ------------------------------ #
    WorkflowStep("export_report", "Export & Report", EXPORT,
                 module=None, produces=None, bas=None,
                 summary="Project JSON, per-module load CSVs, and sbeam BDF cards."),
)

#: Steps keyed by ``key`` for O(1) lookup.
BY_KEY: Dict[str, WorkflowStep] = {s.key: s for s in STEPS}

#: Calc modules folded into another step (contributors, not their own page).
#: WINGINER's inertia loads are combined with NETLOADS on the Net Wing Loads page.
FOLDED_MODULES: Tuple[str, ...] = ("wing_inertia",)


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
