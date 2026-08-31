"""Spanwise wing airloads (Step C1): Schrenk additive + basic + TAU.

The FAR23 path is oracle-locked against the Appendix A worked example (p161-162):
the additive distribution ``CC(LA1)``/``C(LA1)`` and the twist-driven basic
distribution ``Awo``/``CC(lb)``/``Clb``. The math is modernized (math.pi, not the
BASIC's 3.1416), so these are ±0.1% regression oracles, not exact. Concept mode
has no printed oracle and is checked by physics closure (integrated ``c·cl``
recovers the target CL; the basic distribution integrates to zero wing lift).

Reference: AIRLOADS.BAS / TAU.BAS, Ref 1 Ch 7 p46-47, TAU curve-fit p407;
worked example Appendix A p161-162.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import (
    AeroSurfaceInput,
    Project,
    SurfaceInput,
    io,
)
from sloads.modules import airloads as airloads_calc
from sloads.modules.airloads import (
    _sweep_operating,
    _tau,
    schrenk_distribution,
)
from sloads.modules.net_loads import build_net_loads

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_heavy.project.json")
_REGIONAL = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")

REL = 1e-3  # ±0.1% per the modernized-math tolerance convention


# The Appendix A wing planform + twist (Ref 1 p141/p161-162).
_APPA_WING = SurfaceInput(
    name="wing",
    leading_edge=[(45, 0), (64.31301, 46.5), (72, 201)],
    trailing_edge=[(146, 0), (116, 201)],
    symmetric=True, elements=20,
)
_APPA_AERO = AeroSurfaceInput(
    name="wing", section_slope=0.1075,
    twist=[(0, 5), (46.5, 4.577), (109.279, 4.028), (201, 1.9)], target_cl=1.0,
)


def test_additive_distribution_matches_appendix_a():
    t = schrenk_distribution(_APPA_WING, _APPA_AERO)
    # Additive c*cl, "CC(LA1)" column, Appendix A p161.
    assert math.isclose(t.ccl_additive[0], 91.05576, rel_tol=REL)    # elem 1
    assert math.isclose(t.ccl_additive[9], 69.44847, rel_tol=REL)    # elem 10
    assert math.isclose(t.ccl_additive[19], 31.82978, rel_tol=REL)   # elem 20
    # Additive section cl, "C(LA1)" column.
    assert math.isclose(t.cl_additive[0], 0.9275981, rel_tol=REL)    # elem 1
    # The additive distribution integrates to the manual's CL = 1.00061.
    assert math.isclose(t.recovered_cl_additive, 1.00061, rel_tol=REL)


def test_basic_distribution_matches_appendix_a():
    t = schrenk_distribution(_APPA_WING, _APPA_AERO)
    assert math.isclose(t.awo, 3.988146, rel_tol=REL)                # AWO, p162
    assert math.isclose(t.ccl_basic[0], 5.09762, rel_tol=REL)        # CC(lb) elem 1
    assert math.isclose(t.cl_basic[0], 0.05193, rel_tol=REL)         # Clb elem 1
    assert math.isclose(t.mo_wing, 0.1075, rel_tol=REL)              # Mo (constant mo)


def test_geometry_matches_winggeom():
    # AIRLOADS strips the span itself; WINGGEOM integrates in closed form. Both
    # describe one planform, so they must still agree on area/span/AR (p141).
    t = schrenk_distribution(_APPA_WING, _APPA_AERO)
    assert math.isclose(t.area_total, 26513.4, rel_tol=REL)
    assert t.span == 402.0
    assert math.isclose(t.aspect_ratio, 6.095, rel_tol=REL)


def test_tau_curve_fit():
    # TAU.BAS p407: square tip (tip ratio 0) -> the TAU0 quartic at lambda=0 is .206209.
    assert math.isclose(_tau(0.0, 0.0), 0.206209, rel_tol=REL)
    # Tip ratio 1.0 is fully rounded -> TAU = 0 for any taper.
    assert _tau(0.5, 1.0) == 0.0
    # Linear interpolation between tip-ratio knots stays between the two fits.
    lo, mid, hi = _tau(0.5, 0.0), _tau(0.5, 0.05), _tau(0.5, 0.1)
    assert min(lo, hi) <= mid <= max(lo, hi)


def test_untwisted_wing_has_zero_basic_lift():
    aero = AeroSurfaceInput(name="wing", section_slope=0.1075, twist=[], target_cl=1.0)
    t = schrenk_distribution(_APPA_WING, aero)
    assert t.awo == 0.0
    assert all(b == 0.0 for b in t.ccl_basic)


def test_concept_closure_recovers_target_cl():
    project = io.load_project(_CONCEPT)
    assert project.is_concept
    aero = project.aero.by_name("wing")
    geom = project.geometry.by_name("wing")
    t = schrenk_distribution(geom, aero)
    # Physics closure: the integrated span load recovers the target CL (no GA cap).
    assert math.isclose(t.recovered_cl, aero.target_cl, rel_tol=2e-3)
    # Untwisted concept wing -> basic distribution carries zero net wing lift.
    assert math.isclose(sum(t.ccl_basic), 0.0, abs_tol=1e-6)


def test_run_flags_concept_note():
    project = io.load_project(_CONCEPT)
    result = airloads_calc.run(project)
    assert result.module == "airloads"
    assert "concept" in result.conditions[0].note.lower()


def test_run_requires_aero_slice():
    project = Project(name="no-aero")
    try:
        airloads_calc.run(project)
    except ValueError:
        return
    raise AssertionError("expected ValueError when the aero slice is missing")


def test_aero_slice_round_trips_through_io():
    project = io.load_project(_GA)
    rebuilt = io.project_from_dict(io.project_to_dict(project))
    wing = rebuilt.aero.by_name("wing")
    assert wing is not None
    assert math.isclose(wing.section_slope, 0.1075)
    assert wing.twist[0] == (0.0, 5.0)
    assert wing.target_cl == 1.0


def test_ga_fixture_reproduces_oracle_end_to_end():
    # The shipped GA fixture, loaded from disk, reproduces the Appendix A additive.
    project = io.load_project(_GA)
    t = schrenk_distribution(project.geometry.by_name("wing"), project.aero.by_name("wing"))
    assert math.isclose(t.ccl_additive[0], 91.05576, rel_tol=REL)
    assert math.isclose(t.awo, 3.988146, rel_tol=REL)


# --------------------------------------------------------------------------- #
# AIRLOAD4 swept-wing renormalization (M1-3): the COL20 = COL19/CLCOL19 divide
# --------------------------------------------------------------------------- #
def test_swept_closure_recovers_target_cl():
    """Λ≠0 closure: the swept, renormalized span load re-integrates to the operating
    CL. Before M1-3 the shipped regional-jet wing (Λ=24°, twisted) lost ~9.6% of its
    lift (recovered_cl 0.452 vs target 0.50); the COL20 renormalization restores it.
    This guards the swept branch the previous closure test (unswept concept_heavy) did
    not exercise."""
    project = io.load_project(_REGIONAL)
    assert project.is_concept
    aero = project.aero.by_name("wing")
    geom = project.geometry.by_name("wing")
    assert aero.sweep_deg > 15.0                                  # AIRLOAD4 branch selected
    t = schrenk_distribution(geom, aero)
    assert t.airload4
    assert math.isclose(t.recovered_cl, aero.target_cl, rel_tol=2e-3)


def test_sweep_operating_matches_basic_listing():
    """Listing-traceable per-station check of the AIRLOAD4.BAS sweep subroutine.

    Independently reconstruct the traceable operations of the sweepback-adjust
    subroutine (AIRLOAD4.BAS: `COL18=(1-2*YE/B)*2*(1-COS(SBA/57.3))`,
    `COL19=COL16-COL18`, then the `COL20=COL19/CLCOL19` renormalization) and assert
    the module's `_sweep_operating` reproduces it strip-by-strip. Working in c·cl
    units the subtraction is `COL19*MAC*CL == ccl_op - Pope*MAC*CL`; the COL20 divide
    is the span-load renormalization to the operating CL (see the docstring's
    normalization note re: the OCR-garbled COL16 line and the ~0.3% chord-weight
    difference from the literal form)."""
    ye = [10.0, 30.0, 50.0, 70.0, 90.0]
    chord = [40.0, 36.0, 32.0, 28.0, 24.0]
    span = 200.0
    mac = 33.0
    cl_op = 0.6
    dy = 20.0
    area_side = sum(c * dy for c in chord)
    sweep_deg = 25.0
    # An arbitrary operating span load c·cl (need not integrate to cl_op pre-sweep).
    ccl_op = [22.0, 20.0, 17.0, 12.0, 6.0]

    got = _sweep_operating(ccl_op, ye, span, mac, cl_op, area_side, dy, sweep_deg)

    # Reference reconstruction: COL18 (Pope) -> COL19 (subtraction) -> renormalize.
    cos_lam = math.cos(math.radians(sweep_deg))
    col18 = [(1.0 - 2.0 * y / span) * 2.0 * (1.0 - cos_lam) for y in ye]      # dimensionless
    col19 = [cc - p * mac * cl_op for cc, p in zip(ccl_op, col18)]            # c·cl units
    recovered = sum(c19 * dy for c19 in col19) / area_side                   # span-load CL
    col20 = [c19 * cl_op / recovered for c19 in col19]                        # -> operating CL
    for g, ref in zip(got, col20):
        assert math.isclose(g, ref, rel_tol=1e-12)
    # The COL20 renormalization re-integrates the swept span load to the operating CL.
    assert math.isclose(sum(g * dy for g in got) / area_side, cl_op, rel_tol=1e-12)


def test_swept_deliverable_recovers_case_cl():
    """The fix reaches the deliverable path: `build_net_loads` -> `air_load_distribution`
    sweeps each case at its OWN operating CL, so the integrated wing air load recovers
    that CL rather than the pre-M1-3 ~9.6%-deficient value. Reconstruct the wing CL from
    each case's root vertical shear (Sz_root = Σ strip lift; lift = kcl·c·dy·q/144, so
    Σ kcl·c·dy ≈ 144·Sz_root/q, and CL = that / (S/2)). The small angle-of-attack rotation
    folded into Sz keeps this within a percent of the exact renormalized CL."""
    project = io.load_project(_REGIONAL)
    result = build_net_loads(project)
    geom = project.geometry.by_name("wing")
    aero = project.aero.by_name("wing")
    t = schrenk_distribution(geom, aero)
    area_side = t.area_total / 2.0
    cases = {c.name: c for c in project.wing_mass.cases}
    assert result.wing_air, "expected per-case wing air loads"
    for air in result.wing_air:
        case = cases[air.case]
        q = case.v_eas_kt ** 2 / 295.0
        sz_root = air.stations[0].sz                         # root cumulative vertical shear
        implied_cl = (sz_root * 144.0 / q) / area_side
        assert math.isclose(implied_cl, case.cl, rel_tol=2e-2), (air.case, implied_cl, case.cl)


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
