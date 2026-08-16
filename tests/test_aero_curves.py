"""Aero-coefficient curves, the M4-5 closure gates and the entry checks.

Three things are pinned here:

1. **One authority for the polynomials.** ``sloads.aero_curves`` is what both the
   Aerodynamic Data page's curve and the FLTLOADS balance evaluate; the balance's
   stored ``VnPoint.cl`` must equal the module's evaluation exactly.
2. **The closure gates** (the benchmark-first requirement for this step, since no
   printed oracle covers a plot):
   - *recovered CL* -- inverting the balance rotation on each balanced point's own
     dimensional output must reproduce the polynomial CL. Algebraically identical
     within a converged point, so this is a **drift guard** with a 1e-9 tolerance;
     it fails if the curve and the balance ever stop evaluating the same thing.
   - *stall clamp* -- no balanced point may carry a CL above its Mach-adjusted
     stall CL by more than the balance's own convergence band (0.005). This one
     has numerical content: it fails when the dynamic-pressure iteration never
     reaches the stall line. The ATR-42 example fixture is a **documented**
     exceedance (Mach-cap-limited at 25,000 ft) and is pinned as such below.
3. **The coefficient-entry checks** in ``sloads.validation``: silent on every
   shipped fixture, one targeted perturbation per code.
"""

import math
import os
from dataclasses import replace

from sloads import io
from sloads.aero_curves import (
    ALPHA_HI_DEG,
    CL_CLOSURE_TOL,
    STALL_CLOSURE_TOL,
    build_aero_curves,
    curve_closure,
    drag_cd,
    lift_cl,
    moment_cm,
    operating_points,
    recovered_cl,
    reference_glauert,
    stall_limits,
)
from sloads.modules.flight_envelope import balance_configs, build_envelope
from sloads.validation import consistency_warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")
_CONCEPT = os.path.join(_ROOT, "examples", "concept_heavy.project.json")
_RJ = os.path.join(_ROOT, "examples", "concept_regional_jet.project.json")
_ATR = os.path.join(_ROOT, "examples", "atr42_100.project.json")
_EXAMPLES = os.path.join(_ROOT, "examples")

# Closure-carrying fixtures: the Appendix A GA oracle plus both concept airplanes
# (the hand-built-polynomial case the plot exists for).
_CLOSING_FIXTURES = (_GA6, _CONCEPT, _RJ)


def _closures(path):
    """(project, envelope, [ClosureResult]) for every balance configuration."""
    project = io.load_project(path)
    env = build_envelope(project)
    fl = project.flight_loads
    return project, env, [
        curve_closure(env, cfg, wing_area_sqft=fl.wing_area_sqft, mach_ref=fl.mn)
        for cfg in balance_configs(project.aero_coeffs)
    ]


# --------------------------------------------------------------------------- #
# 1. One authority for the coefficient polynomials
# --------------------------------------------------------------------------- #
def test_the_balance_and_the_curve_evaluate_the_same_polynomial():
    """Every stored ``VnPoint.cl`` is exactly ``lift_cl`` at that point's alpha.

    Bit-for-bit, not within a tolerance: ``_balance`` calls this function.
    """
    project, env, _ = _closures(_GA6)
    fl = project.flight_loads
    gmn = reference_glauert(fl.mn)
    cfg = balance_configs(project.aero_coeffs)[0]
    checked = 0
    for p in env.vn:
        if p.config != cfg.name:
            continue
        assert lift_cl(cfg, p.alpha_deg, p.g_corr, gmn) == p.cl
        checked += 1
    assert checked >= 80


def test_reference_glauert_is_one_at_zero_mach_and_degenerate_input():
    assert reference_glauert(0.0) == 1.0
    assert reference_glauert(1.0) == 1.0
    assert reference_glauert(-0.1) == 1.0
    assert math.isclose(reference_glauert(0.6), 1.25, rel_tol=1e-12)


def test_curve_evaluators_match_their_written_form():
    """The three polynomials, spot-checked against the documented equations."""
    project = io.load_project(_GA6)
    cfg = project.aero_coeffs.cruise
    c0, c1 = cfg.lift[0], cfg.lift[1]
    assert math.isclose(lift_cl(cfg, 0.0), c0, rel_tol=1e-12)
    assert math.isclose(lift_cl(cfg, 10.0), c0 + 10.0 * c1, rel_tol=1e-12)
    # Glauert scales the alpha-dependent terms only, never C0.
    assert math.isclose(lift_cl(cfg, 10.0, 1.25, 1.0), c0 + 10.0 * c1 * 1.25, rel_tol=1e-12)
    assert math.isclose(drag_cd(cfg, 0.0), cfg.drag[0], rel_tol=1e-12)
    assert math.isclose(drag_cd(cfg, 1.0), cfg.drag[0] + cfg.drag[1] + cfg.drag[2],
                        rel_tol=1e-12)
    assert math.isclose(moment_cm(cfg, 0.0), cfg.moment[0], rel_tol=1e-12)


# --------------------------------------------------------------------------- #
# 2. The closure gates
# --------------------------------------------------------------------------- #
def test_recovered_cl_closure_holds_on_the_closing_fixtures():
    """The drift guard: recovery through the rotation == the polynomial."""
    for path in _CLOSING_FIXTURES:
        _project, _env, closures = _closures(path)
        assert closures, f"{path} produced no balance configuration"
        for c in closures:
            assert c.n_points > 0
            assert c.worst_cl <= CL_CLOSURE_TOL, (
                f"{os.path.basename(path)}: recovered-CL residual {c.worst_cl:.3e} "
                f"at {c.worst_cl_label}")


def test_stall_clamp_closure_holds_on_the_closing_fixtures():
    """No balanced point sits above its Mach-adjusted stall CL."""
    for path in _CLOSING_FIXTURES:
        _project, _env, closures = _closures(path)
        for c in closures:
            assert c.worst_stall_excess <= STALL_CLOSURE_TOL, (
                f"{os.path.basename(path)}: stall excess {c.worst_stall_excess:.4f} "
                f"at {c.worst_stall_label}")
            assert c.passed


def test_the_atr42_stall_exceedance_is_the_documented_mach_capped_one():
    """The ATR-42 example does *not* close -- deliberately pinned, not ignored.

    Five of its 180 balanced points (MAN A/C and AC ROLL at 25,000 ft) sit up to
    ~0.14 CL above the stall clamp because the local Mach is pinned at MC, so the
    dynamic-pressure iteration cannot raise q any further: the airplane cannot
    reach n = 2.5 at that altitude within its own Mach cap and CLmax. That is a
    property of the fixture's speeds/altitude set, not of this module. If it ever
    starts closing, delete this test and add the fixture to ``_CLOSING_FIXTURES``.

    **It got roughly half way there on its own.** Pri 5 / D-26 corrected this
    fixture's CG cases to loadings its weight database can produce, and the
    exceedance fell from 7 points at +0.29 to 5 at +0.14 -- the cases are lighter
    and their CGs are where the airplane's mass actually puts them, so less lift
    is asked of the same Mach-capped q. Still not attainable, still pinned.
    """
    project, env, closures = _closures(_ATR)
    fl = project.flight_loads
    cfg = balance_configs(project.aero_coeffs)[0]
    assert len(closures) == 1
    assert 0.1 < closures[0].worst_stall_excess < 0.2
    assert "25,000 ft" in closures[0].worst_stall_label
    # The recovered-CL drift guard still holds -- the points are self-consistent,
    # they are simply not attainable.
    assert closures[0].worst_cl <= CL_CLOSURE_TOL

    exceeding = []
    for p in env.vn:
        rec = recovered_cl(p, fl.wing_area_sqft)
        pos, neg = stall_limits(cfg, p.g_corr, fl.mn)
        if max(rec - pos, neg - rec) > STALL_CLOSURE_TOL:
            exceeding.append(p)
    assert len(exceeding) == 5
    assert {p.altitude_ft for p in exceeding} == {25000.0}


def test_a_perturbed_lift_polynomial_breaks_the_recovered_cl_closure():
    """The drift guard has teeth: closing the envelope against *other* coefficients
    than the ones that produced it must fail."""
    project, env, _ = _closures(_GA6)
    fl = project.flight_loads
    cfg = balance_configs(project.aero_coeffs)[0]
    bent = replace(cfg, lift=(cfg.lift[0] + 0.05,) + tuple(cfg.lift[1:]))
    c = curve_closure(env, bent, wing_area_sqft=fl.wing_area_sqft, mach_ref=fl.mn)
    assert c.worst_cl > CL_CLOSURE_TOL
    assert not c.passed
    assert c.worst_cl_label


def test_recovered_cl_rejects_a_degenerate_point():
    _project, env, _ = _closures(_GA6)
    dead = replace(env.vn[0], v_eas_kt=0.0)
    try:
        recovered_cl(dead, 100.0)
    except ValueError:
        pass
    else:  # pragma: no cover - the assertion below reports it
        raise AssertionError("a zero-speed point should not yield a CL")


# --------------------------------------------------------------------------- #
# 3. Curve construction and the overlay
# --------------------------------------------------------------------------- #
def test_curves_sample_the_band_and_find_the_stall_alpha():
    project = io.load_project(_GA6)
    cfg = project.aero_coeffs.cruise
    curves = build_aero_curves(cfg)
    assert len(curves.lift.x) == len(curves.lift.y) > 2
    assert len(curves.polar.x) == len(curves.polar.y)
    assert len(curves.moment.x) == len(curves.moment.y)
    assert curves.lift.x[0] == curves.alpha_lo_deg
    assert curves.lift.x[-1] == curves.alpha_hi_deg
    # ga6: CL = 0.320479 + 0.080358*alpha reaches stall_cl 1.41 at ~13.6 deg.
    assert curves.alpha_stall_deg is not None
    assert 13.0 <= curves.alpha_stall_deg <= 14.5
    assert curves.cl_max_on_curve > cfg.stall_cl
    # The polar is CL vs CD (drag on x, the conventional orientation).
    assert curves.polar.x[0] > 0.0
    assert math.isclose(curves.polar.y[0], curves.lift.y[0], rel_tol=1e-12)


def test_an_unreachable_stall_cl_leaves_no_stall_alpha():
    project = io.load_project(_GA6)
    cfg = replace(project.aero_coeffs.cruise, stall_cl=5.0)
    assert build_aero_curves(cfg).alpha_stall_deg is None


def test_the_alpha_band_widens_to_hold_every_operating_point():
    project, env, _ = _closures(_GA6)
    fl = project.flight_loads
    cfg = balance_configs(project.aero_coeffs)[0]
    pts = operating_points(env, cfg.name, wing_area_sqft=fl.wing_area_sqft,
                           mac_in=fl.mac)
    assert len(pts) == len(pts.cl) == len(pts.cd) == len(pts.cm) == len(pts.label)
    assert len(pts) > 0
    curves = build_aero_curves(cfg, points=pts)
    assert curves.alpha_lo_deg <= min(pts.alpha_deg)
    assert curves.alpha_hi_deg >= max(pts.alpha_deg)
    # A point beyond the default band widens it rather than clipping the plot.
    wide = build_aero_curves(cfg, points=replace(pts, alpha_deg=[ALPHA_HI_DEG + 9.0]))
    assert wide.alpha_hi_deg >= ALPHA_HI_DEG + 9.0


def test_the_overlay_points_lie_on_the_curve():
    """Recovered operating points reproduce the polynomial, Glauert included."""
    project, env, _ = _closures(_GA6)
    fl = project.flight_loads
    gmn = reference_glauert(fl.mn)
    cfg = balance_configs(project.aero_coeffs)[0]
    for p in env.vn:
        if p.config != cfg.name:
            continue
        rec = recovered_cl(p, fl.wing_area_sqft)
        assert math.isclose(rec, lift_cl(cfg, p.alpha_deg, p.g_corr, gmn), abs_tol=1e-9)


def test_an_empty_envelope_yields_curves_without_points():
    project = io.load_project(_GA6)
    cfg = project.aero_coeffs.cruise
    curves = build_aero_curves(cfg)
    assert curves.points is None and curves.closure is None
    assert len(curves.lift.x) > 2


# --------------------------------------------------------------------------- #
# 4. The coefficient-entry checks
# --------------------------------------------------------------------------- #
def _aero_codes(project):
    return [w.code for w in consistency_warnings(project)
            if w.code.startswith("aero_")]


def test_every_shipped_fixture_is_free_of_aero_warnings():
    """The conservative-validation invariant, including the Appendix A oracle."""
    for name in sorted(os.listdir(_EXAMPLES)):
        if not name.endswith(".project.json"):
            continue
        project = io.load_project(os.path.join(_EXAMPLES, name))
        assert _aero_codes(project) == [], f"{name} raised aero warnings"


def test_a_project_without_aero_coefficients_is_silent():
    project = io.load_project(_GA6)
    project.aero_coeffs = None
    assert _aero_codes(project) == []


def test_a_radian_lift_slope_fires_the_slope_check():
    """A per-radian slope entered as per-degree flips sign only when transposed;
    the check catches the non-positive slope either way."""
    project = io.load_project(_GA6)
    cruise = project.aero_coeffs.cruise
    project.aero_coeffs.cruise = replace(
        cruise, lift=(cruise.lift[0], -cruise.lift[1]) + tuple(cruise.lift[2:]))
    assert "aero_lift_slope_sign" in _aero_codes(project)


def test_a_lift_curve_that_never_reaches_stall_fires_the_reachability_check():
    project = io.load_project(_GA6)
    cruise = project.aero_coeffs.cruise
    project.aero_coeffs.cruise = replace(cruise, stall_cl=4.0)
    codes = _aero_codes(project)
    assert "aero_clmax_unreachable" in codes


def test_a_negative_drag_polar_fires_the_drag_check():
    project = io.load_project(_GA6)
    cruise = project.aero_coeffs.cruise
    project.aero_coeffs.cruise = replace(cruise, drag=(-0.05, 0.0, 0.001, 0.0, 0.0))
    assert "aero_drag_negative" in _aero_codes(project)


def test_an_inverted_quadratic_polar_fires_the_shape_check():
    project = io.load_project(_GA6)
    cruise = project.aero_coeffs.cruise
    project.aero_coeffs.cruise = replace(
        cruise, drag=(cruise.drag[0], 0.0, -cruise.drag[2], 0.0, 0.0))
    assert "aero_drag_polar_shape" in _aero_codes(project)


def test_a_general_higher_order_polar_is_left_alone():
    """The shape check only judges the plain quadratic form."""
    project = io.load_project(_GA6)
    cruise = project.aero_coeffs.cruise
    project.aero_coeffs.cruise = replace(
        cruise, drag=(cruise.drag[0], 0.02, 0.0, 0.01, 0.0))
    assert "aero_drag_polar_shape" not in _aero_codes(project)


def test_a_positive_negative_clmax_fires_the_sign_check():
    project = io.load_project(_GA6)
    project.aero_coeffs.clmax_clean_neg = 0.59
    assert "aero_clmax_neg_sign" in _aero_codes(project)


def test_the_aero_warnings_are_tagged_for_the_aero_page():
    project = io.load_project(_GA6)
    project.aero_coeffs.clmax_clean_neg = 0.59
    tagged = [w for w in consistency_warnings(project) if w.code.startswith("aero_")]
    assert tagged and all(w.page == "aero_coefficients" for w in tagged)


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"ok  {_name}")
    print("all aero-curve tests passed")
