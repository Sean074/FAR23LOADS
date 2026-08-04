"""Net fuselage loads (Step C6, R6): the Ch 15 body distribution + sbeam export.

Ch 15 ("Net Fuselage Loads") ships no program and no printed station table, so
the fuselage net distribution is a modern calc validated by **equilibrium
closure**: the applied vertical loads (fuselage inertia + tail air load + wing
reaction) sum to zero, the running shear returns to zero aft of the wing
reaction, and the exported FORCE set re-sums to zero.

The closure is **vertical (ΣFz) only** — the single wing reaction leaves the
moment unbalanced (terminal `Myy != 0`), which is open work (backlog M4-1). That
limitation is a required part of the deliverable until it closes, locked here by
`test_body_bdf_carries_closure_caveat`.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.export import sbeam_bridge  # noqa: E402
from sloads.models import FuselageMassInput, FuselageStation, TailLoadsInput  # noqa: E402
from sloads.modules import body_loads  # noqa: E402

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
    assert rows and set(rows[0]) == {"Case", "X", "Fz", "Sz", "Myy", "Basis"}
    # The basis travels in-band with every row (defect M4-15).
    assert all(r["Basis"] == "LIMIT" for r in rows)


def test_sbeam_body_export_force_set_sums_to_zero():
    res = body_loads.build_body_loads(_project())
    cards = sbeam_bridge.body_force_moment_cards(res)
    assert "FORCE" in cards
    # Re-sum the Fz of every FORCE card in the first load set: must close to ~0.
    # The tolerance is relative to the load magnitude on the cards -- the cards
    # carry 6 significant digits (_fmt), so a set of ~10^4 lb loads re-sums to
    # ~10^-3 lb of print rounding, not of calc error.
    fz = [float(ln.split(",")[-1]) for ln in cards.splitlines() if ln.startswith("FORCE, 1,")]
    assert math.isclose(sum(fz), 0.0, abs_tol=1e-5 * sum(abs(f) for f in fz))


def test_sbeam_body_span_csv():
    csv_text = sbeam_bridge.body_span_load_csv(body_loads.build_body_loads(_project()))
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    assert lines[0] == "Case,GID,X,Fz,Sz,Myy,SF"
    assert len(lines) > 1


def test_body_bdf_ships_no_caveat_on_the_carry_through_path():
    """M4-1 closed: a set reacted at the spar attachments carries no caveat.

    The old lock asserted the opposite (every set stated the open ΣM limitation).
    It is inverted here: the caveat now belongs only to the whole-body fallback,
    which ``test_body_bdf_flags_the_closure_artifact`` covers. The assumed-spar
    provenance still ships on every card block.
    """
    results = body_loads.build_body_loads(_project())
    assert all(not r.closure_artifact for r in results)
    cards = sbeam_bridge.body_force_moment_cards(results)
    assert "$ CAVEAT:" not in cards
    # The spar stations were not entered, so every block says so (decision 2).
    assert len([ln for ln in cards.splitlines()
                if "spar stations ASSUMED" in ln]) == len(results)
    # Each block states both closure residuals.
    assert len([ln for ln in cards.splitlines()
                if "moment equilibrium" in ln]) == len(results)
    # Every comment line stays inside the free-field card width.
    assert all(len(ln) <= 72 for ln in cards.splitlines() if ln.startswith("$"))


def test_run_requires_fuselage_mass():
    # GA6 now ships a fuselage_mass slice (M2R-3), so clear it here to exercise
    # the missing-slice guard directly rather than relying on the fixture's gaps.
    project = io.load_project(_GA)
    project.fuselage_mass = None
    raised = False
    try:
        body_loads.run(project)
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
