"""FAR 23 applicability detection (14 CFR 23.1, pre-Amdt 23-64 applicability band).

A pure, unit-testable helper that reports whether an airplane exceeds the FAR 23
applicability limits the replication core is calibrated to. It never blocks: the
GUI surfaces the returned exceedances as a non-blocking banner offering a switch to
concept mode (``app/components.py``). On Appendix-A GA inputs it yields no
exceedances, so the tool reduces exactly to the oracle-locked FAR 23 behaviour.

The certificated limits live in :mod:`sloads.constants`; this module only reads
the ``Project`` and compares. No Streamlit, no file access.
"""

from dataclasses import dataclass
from typing import List, Optional

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
    """Design gross weight (lb) used by the MTOW check.

    ``speeds.weight_lb`` when set (> 0); otherwise the itemized Weight DB take-off
    total (``Project.weight.direct_totals()`` MTOW). ``0.0`` when neither is
    available.
    """
    if project.speeds is not None and project.speeds.weight_lb > 0:
        return project.speeds.weight_lb
    if project.weight is not None:
        return project.weight.direct_totals()[0]
    return 0.0


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
