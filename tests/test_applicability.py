"""Tests for FAR 23 applicability detection (Step E1).

The pure ``far23_applicability`` helper must yield no exceedances for a GA airplane
inside the certificated band (Appendix A) and the expected weight + passenger-seat
exceedances for a beyond-FAR23 concept airplane. ``effective_occupants`` seeds from
the Weight Estimate seat count when the speeds slice has no explicit occupant count.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import io  # noqa: E402
from farloads.applicability import (  # noqa: E402
    design_weight_lb,
    effective_crew,
    effective_occupants,
    far23_applicability,
)

EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)
GA6 = os.path.join(EXAMPLES, "ga6_normal.project.json")


def test_ga_appendix_a_has_no_exceedances():
    # The Appendix A 6-place GA single (~3,400 lb, 6 occupants - 1 crew = 5
    # passenger seats) sits inside the 12,500 lb / 9-seat FAR 23 band.
    project = io.load_project(GA6)
    assert far23_applicability(project) == []


def test_beyond_far23_normal_flags_weight_and_seats():
    project = io.load_project(GA6)
    project.speeds.category = "N"
    project.speeds.weight_lb = 20000.0
    project.speeds.occupants = 12  # crew defaults to 1 (GA6 has no crew key)
    exc = far23_applicability(project)
    fields = {e.field: e for e in exc}
    assert set(fields) == {"weight_lb", "occupants"}
    assert fields["weight_lb"].value == 20000.0
    assert fields["weight_lb"].limit == 12500.0
    # 12 occupants - 1 crew = 11 passenger seats > 9.
    assert fields["occupants"].value == 11
    assert fields["occupants"].limit == 9


def test_crew_field_reduces_passenger_seats():
    # With 12 occupants and 3 crew -> 9 passenger seats == the limit (not over).
    project = io.load_project(GA6)
    project.speeds.occupants = 12
    project.weight.estimation.crew = 3
    assert effective_crew(project) == 3
    assert all(e.field != "occupants" for e in far23_applicability(project))
    # One more occupant tips it over.
    project.speeds.occupants = 13
    seat_exc = [e for e in far23_applicability(project) if e.field == "occupants"]
    assert seat_exc and seat_exc[0].value == 10


def test_effective_crew_defaults_when_no_estimation():
    from farloads import Project
    from farloads.constants import DEFAULT_FLIGHT_CREW
    assert effective_crew(Project(name="bare")) == DEFAULT_FLIGHT_CREW


def test_effective_occupants_falls_back_to_seats():
    project = io.load_project(GA6)
    assert project.speeds.occupants is None
    # GA6 Weight Estimate carries 6 seats (see test_io).
    assert effective_occupants(project) == project.weight.estimation.seats == 6
    # An explicit occupant count overrides the seat fallback.
    project.speeds.occupants = 4
    assert effective_occupants(project) == 4


def test_design_weight_prefers_speeds_then_weight_db():
    project = io.load_project(GA6)
    project.speeds.weight_lb = 4200.0
    assert design_weight_lb(project) == 4200.0
    # With no speeds weight, fall back to the itemized Weight DB total.
    project.speeds.weight_lb = 0.0
    assert design_weight_lb(project) == project.weight.direct_totals()[0]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all applicability tests passed")
