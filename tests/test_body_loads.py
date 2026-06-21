"""Net fuselage loads (Step C6, R6): the Ch 15 body distribution + sbeam export.

Ch 15 ("Net Fuselage Loads") ships no program and no printed station table, so
the fuselage net distribution is a modern calc validated by **equilibrium
closure**: the applied vertical loads (fuselage inertia + tail air load + wing
reaction) sum to zero, the running shear returns to zero aft of the wing
reaction, and the exported FORCE set re-sums to zero.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import io  # noqa: E402
from farloads.export import sbeam_bridge  # noqa: E402
from farloads.models import FuselageMassInput, FuselageStation, TailLoadsInput  # noqa: E402
from farloads.modules import body_loads  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _project():
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.fuselage_mass = FuselageMassInput(stations=[
        FuselageStation(x=x, weight_lb=w) for x, w in
        [(30, 200), (60, 400), (90, 600), (140, 500), (200, 300), (250, 150)]
    ])
    p.tail_loads = TailLoadsInput(xt25=261.027)
    return p


def test_body_distribution_for_each_fuselage_condition():
    res = body_loads.build_body_loads(_project())
    # One distribution per critical fuselage condition (SELECT R5).
    assert {r.case for r in res} == {
        "MAX DOWN LOAD ON WING", "AFT DOWN BENDING", "AFT UP BENDING", "GREATEST NZ"}


def test_body_net_closes_in_equilibrium():
    for r in body_loads.build_body_loads(_project()):
        assert math.isclose(sum(s.fz for s in r.stations), 0.0, abs_tol=1e-6)  # forces balance
        assert math.isclose(r.stations[-1].sz, 0.0, abs_tol=1e-6)              # shear returns to 0


def test_body_load_rows_shape():
    rows = body_loads.body_load_rows(body_loads.build_body_loads(_project()))
    assert rows and set(rows[0]) == {"Case", "X", "Fz", "Sz", "Myy"}


def test_sbeam_body_export_force_set_sums_to_zero():
    res = body_loads.build_body_loads(_project())
    cards = sbeam_bridge.body_force_moment_cards(res)
    assert "FORCE" in cards
    # Re-sum the Fz of every FORCE card in the first load set: must close to ~0.
    fz_total = 0.0
    for line in cards.splitlines():
        if line.startswith("FORCE, 1,"):
            fz_total += float(line.split(",")[-1])
    assert math.isclose(fz_total, 0.0, abs_tol=1e-3)


def test_sbeam_body_span_csv():
    csv_text = sbeam_bridge.body_span_load_csv(body_loads.build_body_loads(_project()))
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    assert lines[0] == "Case,GID,X,Fz,Sz,Myy"
    assert len(lines) > 1


def test_run_requires_fuselage_mass():
    raised = False
    try:
        body_loads.run(io.load_project(_GA))   # no fuselage_mass slice
    except ValueError:
        raised = True
    assert raised


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
