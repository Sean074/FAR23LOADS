"""FAR 23 applicability detection (14 CFR 23.1, pre-Amdt 23-64 applicability band).

A pure, unit-testable helper that reports whether an airplane exceeds the FAR 23
applicability limits the replication core is calibrated to. It never blocks: the
GUI surfaces the returned exceedances as a non-blocking banner offering a switch to
concept mode (``app_shell/components.py``). On Appendix-A GA inputs it yields no
exceedances, so the tool reduces exactly to the oracle-locked FAR 23 behaviour.

The certificated limits live in :mod:`sloads.constants`; this module only reads
the ``Project`` and compares. No Streamlit, no file access.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import cg_cases
from . import constants as C
from .models import Project


@dataclass(frozen=True)
class Exceedance:
    """One FAR 23 applicability limit an airplane exceeds.

    ``field`` is the ``Project`` quantity ("weight_lb" / "occupants"); ``value`` is
    the airplane's figure; ``limit`` is the FAR 23 ceiling; ``label`` is a
    human-readable description for the GUI banner.
    """
    field: str
    value: float
    limit: float
    label: str


def effective_occupants(project: Project) -> Optional[int]:
    """Total occupants used by the seat-limit check.

    ``StructuralSpeedsInput.occupants`` when the user has set it; otherwise the
    WTESTIMA design seat count (``Project.weight.estimation.seats``) as the
    seed-chain fallback. ``None`` when neither is available.
    """
    if project.speeds is not None and project.speeds.occupants is not None:
        return project.speeds.occupants
    if project.weight is not None and project.weight.estimation is not None:
        return project.weight.estimation.seats
    return None


def effective_crew(project: Project) -> int:
    """Required flight-crew count subtracted from occupants for the seat check.

    ``Project.weight.estimation.crew`` when a weight-estimation slice is present;
    otherwise :data:`constants.DEFAULT_FLIGHT_CREW`. The crew are excluded from the
    FAR 23 passenger-seat count and are carried in the operating empty weight.
    """
    if project.weight is not None and project.weight.estimation is not None:
        return project.weight.estimation.crew
    return C.DEFAULT_FLIGHT_CREW


def design_weight_lb(project: Project) -> float:
    """Design gross weight (lb) used by the MTOW check -- the MTOW SSOT.

    :func:`sloads.cg_cases.max_takeoff_weight` (decision **G-14**): the
    ``weight.max_takeoff_weight_lb`` field, else its documented fallback chain
    (``speeds.weight_lb`` -> ``weight.envelope.gross_weight`` -> the heaviest
    ``FLIGHT`` case). ``0.0`` when the airplane states no take-off weight at all,
    which leaves the gate silent rather than guessing.

    **This read the itemized database *total* until 2026-08-15**, whenever
    ``speeds.weight_lb`` was unset -- an upper bound wearing the name of a design
    limit, since a database can hold full fuel *and* full payload at once (964 lb
    high on ``atr42_100``, 1,800 lb on ``concept_regional_jet``). Latent on every
    shipped fixture, which all set ``speeds.weight_lb``, but a project caught
    mid-entry took the certification gate off the wrong number. The database total
    is the *ceiling* of ``OEW <= MLW <= MTOW <= sum(items)``, owned by
    :func:`sloads.cg_cases.database_total` and checked in
    :mod:`sloads.validation`; it is not a design weight and no longer reachable
    from here.
    """
    return cg_cases.max_takeoff_weight(project, required=False)


#: What the One Engine Out page and module say when 14 CFR 23.367 does not apply.
#: The lead phrase is fixed so both GUIs and the module refusal read identically.
ENGINE_FAILURE_NA_LEAD = "FAR 23.367 does not apply"


def engine_failure_not_applicable(project: Project) -> Optional[str]:
    """Why 14 CFR 23.367 does not apply to ``project``, or ``None`` if it does.

    The unsymmetrical-load condition is driven by the yaw moment a failed engine
    leaves behind: ``thrust * bleng`` with ``bleng = abs(engine_cg[1])``. On an
    airplane with one engine, or with the failed engine on the centreline, that
    arm is **identically zero** -- so ONENGOUT integrated a transient with no
    forcing in it and reported zero tail load, zero yaw rate and, because nothing
    ever moved back, "NOT recovered within 60 s -- the airplane is uncontrollable
    at this speed (likely below VMC)". A false uncontrollability verdict on a
    condition the airplane cannot have (C210-43, #84).

    Returned as a reason string (``None`` when the condition *does* apply) to
    match :mod:`sloads.report.coverage`'s ``na_when`` convention, so the coverage
    table, the module's refusal and the GUI's withheld form are three readers of
    **one** predicate rather than three copies of a rule (practice 3, the
    ``Project.engine_layout_problem`` shape).

    Deliberately **not** the whole of ``coverage._engine_failure_na``: that one
    also declares 23.367 inapplicable without a turbopropeller (Ref 1 Ch 11),
    which is a theory question about 23.367(b)'s reciprocating branch and is
    tracked separately. This predicate is the yaw-forcing one alone, and it is
    the one that produced the false verdict.

    With no engines entered at all the answer is ``None`` unless the layout
    settles it: an empty list is a project that is not finished, and the module's
    existing "needs Project.engines" refusal says that better than an
    applicability ruling would.
    """
    engines = project.engines
    layout = project.engine_layout
    if not engines:
        if layout is not None and layout.expected_count < 2:
            return (f"{ENGINE_FAILURE_NA_LEAD} — single/centreline engine: the "
                    f"{layout.name.replace('_', ' ').lower()} layout carries one "
                    "engine, so an engine failure leaves no asymmetric thrust and "
                    "no yaw moment to react.")
        return None
    if len(engines) < 2:
        return (f"{ENGINE_FAILURE_NA_LEAD} — single/centreline engine: a "
                "single-engine airplane has no one-engine-inoperative condition. "
                "Losing the only engine leaves no asymmetric thrust and no yaw "
                "moment to react.")
    oeo = project.one_engine_out
    index = oeo.failed_engine_index if oeo is not None else 0
    if 0 <= index < len(engines) and engines[index].engine_cg[1] == 0.0:
        eng = engines[index]
        return (f"{ENGINE_FAILURE_NA_LEAD} — single/centreline engine: the failed "
                f"engine ({eng.engine_designation or f'index {index}'}) sits on the "
                "centreline at BL 0, so its thrust has no moment arm about the CG "
                "and its failure produces no yawing moment. Set its butt line, or "
                "fail an off-centreline engine.")
    return None


#: Workflow steps whose FAR condition an airplane may simply not have, and the
#: predicate that says so. Keyed by ``sloads.workflow.STEPS`` key -- a key naming
#: anything else names a page no GUI has, the #82 defect -- and guarded as such by
#: ``tests/test_applicability.py``. It lives here rather than in a front-end for
#: two reasons: the oracle GUI's page set is derived from ``workflow`` and may not
#: write a step key as a literal (OG-2/G2), and the predicates must be the same
#: ones the modules refuse on, so a page can never offer a condition the calc
#: would decline (#84).
_STEP_NOT_APPLICABLE: Dict[str, Callable[[Project], Optional[str]]] = {
    "one_engine_out": engine_failure_not_applicable,
}


def step_not_applicable(step_key: str, project: Project) -> Optional[str]:
    """Why the workflow step ``step_key`` does not apply to ``project``, or ``None``.

    ``None`` for every step with no applicability predicate, which is most of
    them -- the question only arises where the airplane's configuration can
    remove a FAR condition outright.
    """
    predicate = _STEP_NOT_APPLICABLE.get(step_key)
    return predicate(project) if predicate is not None else None


def far23_applicability(project: Project) -> List[Exceedance]:
    """Structured FAR 23 applicability exceedances for an airplane.

    Compares the design gross weight and passenger-seat count against the
    non-commuter FAR 23 tier (12,500 lb / 9 passenger seats; the required flight
    crew, :func:`effective_crew`, are excluded from the seat count). Returns an
    empty list for a GA airplane inside the band (e.g. Appendix A). The commuter
    tier (19,000 lb / 19 seats) is encoded in :mod:`sloads.constants` but dormant
    until a distinct Commuter category exists, so it is not consulted here.
    """
    exceedances: List[Exceedance] = []

    weight = design_weight_lb(project)
    if weight > C.FAR23_MAX_WEIGHT_LB:
        exceedances.append(Exceedance(
            field="weight_lb",
            value=weight,
            limit=C.FAR23_MAX_WEIGHT_LB,
            label="Max takeoff weight (FAR 23)",
        ))

    occupants = effective_occupants(project)
    if occupants is not None:
        passenger_seats = max(occupants - effective_crew(project), 0)
        if passenger_seats > C.FAR23_MAX_PASSENGER_SEATS:
            exceedances.append(Exceedance(
                field="occupants",
                value=passenger_seats,
                limit=C.FAR23_MAX_PASSENGER_SEATS,
                label="Passenger seats, excl. crew (FAR 23)",
            ))

    return exceedances
