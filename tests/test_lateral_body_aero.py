"""L-7 lateral body aero -- the DATCOM oracle (gate G1) and the closed forms.

Design note ``docs/40_history/33_l7_lateral_body_aero_note.md`` §8 (rev. 3,
decision L-7.8): the ported wing-body ``Cy_beta`` / ``Cn_beta`` reproduce Digital
DATCOM's **printed** ``CYB``/``CNB`` for every *applicable* sample case at
+/-0.1 % -- the FAR23 core's own oracle standard. ``reference/`` is gitignored,
so the printed numbers and the case geometry are carried here as literals with
their file/line citations (``reference/datcom/examples/exN.inp`` / ``.out``),
exactly as the Appendix A oracle tests carry theirs; CI needs nothing from
``reference/``.

Applicable = the subsonic body-alone and wing-body rows. Named and pinned:

* ``ex1`` case 1 (body alone, M 0.6): ``CYB = -CLA = -3.433E-03`` -- pins
  ``CL_alpha,B`` on the never-decreasing-area path (``x_1 = l_B``);
* ``ex3`` case 1 ``BUILD``, WING-BODY row, M 0.6 (``ex3.out:237-240``):
  ``CYB = -1.610E-03`` (``CL_alpha,B`` on the boat-tail path, ``K_i = 1``),
  ``CNB = -1.845E-03`` (``K_N``, ``K_Rl`` at ``Re/ft = 4.26E6``);
* ``ex3`` case 1 WING-BODY row, M 0.8 (``ex3.out:474+``): ``CNB = -1.941E-03``
  -- the ``K_Rl`` Reynolds dependence (``Re/ft = 6.4E6``);
* ``ex5`` case 1 (= ``ex6``; same body with the section area *derived* from the
  round half-width, ``S = pi R^2``): ``CYB = -1.612E-03``;
* ``ex4`` case 1 (body + wing + canard, M 0.6, ``Re/ft = 3.1E6`` on a 60 ft
  body -> ``Re_l = 1.86E8``, the regional jet's regime): ``CYB = -3.660E-04``,
  ``CNB = -6.036E-04`` -- an independent 19-station geometry, and the
  top-of-chart ``K_Rl`` (2.075) confirmed against a printed answer.

Inapplicable, deliberately not pinned: ``ex2`` (wing alone), ``ex1`` cases 3-4
and ``ex4`` case 2 (supersonic), ``ex3`` cases 2-5 (experimental-data
overrides -- not the method), ``ex7``/``ex8`` (only the full configuration with
the fin is printed, so the wing-body row cannot be isolated), ``ex9``-``ex11``
(hypersonic / lifting body). ``ex3``'s M 0.8 ``CYB`` (-1.599E-03) is not pinned
either: DATCOM's transonic body ``CL_alpha`` differs from the subsonic BODYRT
value ported here and the suite's cases are subsonic.

**No printed case exercises ``K_i`` (every sample has ``z_w = 0``) or the
dihedral term (all ``Gamma = 0``)** -- those two lines are checked against
their closed forms only, below, and the module docstring says so.
"""

from __future__ import annotations

import math

import pytest

from sloads import atmosphere
from sloads import lateral_body_aero as lba
from sloads.constants import RHO_SL
from sloads.models import FuselageOutline, FuselageSection

TOL = 1e-3   # +/-0.1 %, the FAR23 core's oracle standard

# ex1.inp:5-10 -- APPROXIMATE AXISYMMETRIC BODY SOLUTION, EXAMPLE PROBLEM 1, CASE 1
_EX1 = lba.DatcomBody(
    x=(0.0, 0.258, 0.589, 1.260, 2.260, 2.590, 2.930, 3.590, 4.570, 6.260),
    r=(0.0, 0.186, 0.286, 0.424, 0.533, 0.533, 0.533, 0.533, 0.533, 0.533),
    s=(0.0, 0.080, 0.160, 0.323, 0.751, 0.883, 0.939, 1.032, 1.032, 1.032),
)
_EX1_SREF = 8.85

# ex3.inp:8-13 -- CONFIGURATION BUILDUP, EXAMPLE PROBLEM 3, CASE 1 (also ex5-ex8's body)
_EX3_X = (0.0, .175, .322, .530, .850, 1.46, 2.5, 3.43, 3.97, 4.57)
_EX3_S = (0.0, .00547, .022, .0491, .0872, .136, .136, .136, .0993, .0598)
_EX3_R = (0.0, .0417, .0833, .125, .1665, .208, .208, .208, .178, .138)
_EX3 = lba.DatcomBody(x=_EX3_X, s=_EX3_S, r=_EX3_R)
_EX3_SREF, _EX3_BREF, _EX3_XCG = 2.25, 3.00, 2.60

# ex4.inp:5-19 -- BODY PLUS WING PLUS CANARD, EXAMPLE PROBLEM 4, CASE 1
_EX4 = lba.DatcomBody(
    x=(0.0, 2.01, 5.49, 8.975, 12.47, 15.97, 19.47, 22.89, 26.49, 30.0,
       33.51, 37.02, 40.53, 44.03, 47.53, 51.02, 54.52, 57.99, 60.0),
    s=(0.0, 2.89, 7.42, 11.32, 14.64, 17.36, 19.49, 21.0, 21.91, 22.20,
       21.90, 21.0, 19.49, 17.36, 14.64, 11.33, 7.42, 2.89, 0.0),
    r=(0.0, 0.293, 0.752, 1.15, 1.48, 1.76, 1.97, 2.13, 2.22, 2.25,
       2.22, 2.13, 1.97, 1.76, 1.48, 1.15, 0.752, 0.293, 0.0),
)
_EX4_SREF, _EX4_BREF, _EX4_XCG = 694.2, 45.6, 36.68


# --------------------------------------------------------------------------- #
# G1 -- the printed oracle
# --------------------------------------------------------------------------- #
def test_g1_ex1_body_alone_lift_slope():
    """ex1.out:434 -- CLA = 3.433E-03 (CYB = -3.433E-03), per degree."""
    lift = lba.body_lift_slope(_EX1, _EX1_SREF)
    assert math.isclose(lift.cl_alpha, 3.433e-3, rel_tol=TOL)
    assert lift.x1 == _EX1.x[-1]          # area never decreases -> x_1 = l_B


def test_g1_ex3_wing_body_side_force_m06():
    """ex3.out:239 -- WING-BODY CYB = -1.610E-03 per degree at M 0.6 (K_i = 1)."""
    lift = lba.body_lift_slope(_EX3, _EX3_SREF)
    cy = lba.side_force_derivative(lift.cl_alpha, lba.wing_height_factor(0.0, 0.416), 0.0)
    assert math.isclose(cy, -1.610e-3, rel_tol=TOL)
    assert math.isclose(lift.x1, 3.97)     # the boat-tail path: steepest dS/dx station


def test_g1_ex3_wing_body_yaw_m06():
    """ex3.out:239 -- WING-BODY CNB = -1.845E-03 per degree, Re/ft 4.26E6."""
    y = lba.yaw_derivative(_EX3, _EX3_XCG, _EX3_SREF, _EX3_BREF, 4.26e6)
    assert math.isclose(y.cn_beta_datcom, -1.845e-3, rel_tol=TOL)


def test_g1_ex3_wing_body_yaw_m08_reynolds_dependence():
    """ex3.out (second WING-BODY block, M 0.8) -- CNB = -1.941E-03, Re/ft 6.4E6."""
    y = lba.yaw_derivative(_EX3, _EX3_XCG, _EX3_SREF, _EX3_BREF, 6.4e6)
    assert math.isclose(y.cn_beta_datcom, -1.941e-3, rel_tol=TOL)


def test_g1_ex5_side_force_with_area_from_round_half_width():
    """ex5.out WING-BODY -- CYB = -1.612E-03: S omitted in the deck, so DATCOM
    takes S = pi R^2 (the outline's own ellipse rule with width = height)."""
    body = lba.DatcomBody(x=_EX3_X, s=tuple(math.pi * r * r for r in _EX3_R), r=_EX3_R)
    lift = lba.body_lift_slope(body, _EX3_SREF)
    assert math.isclose(-lift.cl_alpha, -1.612e-3, rel_tol=TOL)


def test_g1_ex4_independent_geometry_and_top_of_chart_krl():
    """ex4.out WING-BODY-HORIZONTAL TAIL row -- CYB = -3.660E-04, CNB = -6.036E-04
    (the h-tail adds nothing laterally in DATCOM's subsonic method, so this is
    the wing-body value). Re_l = 3.1E6 * 60 = 1.86E8: K_Rl = 2.075, past the
    plotted range of figure 5.2.3.1-9 and reproduced from the closed form the
    Fortran uses (decision L-7.13)."""
    lift = lba.body_lift_slope(_EX4, _EX4_SREF)
    assert math.isclose(-lift.cl_alpha, -3.660e-4, rel_tol=TOL)
    y = lba.yaw_derivative(_EX4, _EX4_XCG, _EX4_SREF, _EX4_BREF, 3.1e6)
    assert math.isclose(y.cn_beta_datcom, -6.036e-4, rel_tol=TOL)
    assert y.k_rl > 2.0


# --------------------------------------------------------------------------- #
# The two lines with no printed oracle -- closed forms
# --------------------------------------------------------------------------- #
def test_wing_height_factor_closed_form():
    """Figure 5.2.1.1-7 as datcom.f:29028-29033 writes it."""
    assert lba.wing_height_factor(0.0, 10.0) == 1.0
    assert math.isclose(lba.wing_height_factor(2.5, 10.0), 1.0 + 0.49 * 0.5)     # low wing
    assert math.isclose(lba.wing_height_factor(-2.5, 10.0), 1.0 + 0.85 * 0.5)    # high wing
    assert lba.wing_height_factor(3.0, 0.0) == 1.0                                # no body depth


def test_dihedral_term_closed_form():
    """DATCOM 5.2.1.1: -0.0001 per degree of |dihedral|, sign-independent."""
    assert math.isclose(lba.side_force_derivative(0.0, 1.0, 6.0), -0.0006)
    assert math.isclose(lba.side_force_derivative(0.0, 1.0, -6.0), -0.0006)
    assert math.isclose(lba.side_force_derivative(0.002, 1.2, 0.0), -0.0024)


# --------------------------------------------------------------------------- #
# The suite adaptor and its geometry
# --------------------------------------------------------------------------- #
def _outline_from_datcom(body: lba.DatcomBody, scale: float) -> FuselageOutline:
    """A round outline (width = height = 2R) at ``scale`` in/unit, so the
    ellipse rule gives S = pi R^2 -- the ex5 deck's own reading."""
    return FuselageOutline(sections=[
        FuselageSection(x=x * scale, width=2 * r * scale, height=2 * r * scale)
        for x, r in zip(body.x, body.r)])


def test_outline_adaptor_reproduces_the_datcom_body_in_inches():
    outline = _outline_from_datcom(_EX3, 12.0)
    body = lba.datcom_body_from_outline(outline)
    assert body is not None
    assert math.isclose(body.length, 4.57 * 12.0)
    assert body.heights()[5] == pytest.approx(2 * .208 * 12.0)
    # S from the ellipse rule with width = height is pi R^2 (ex5's path)
    assert body.s[5] == pytest.approx(math.pi * (.208 * 12.0) ** 2)


def test_estimate_signs_and_transfer_identity():
    """Suite sign: cy_beta < 0 (port at +beta), cn_beta > 0 (destabilizing);
    the moment transfer to another station is the fixed-force lever arm."""
    outline = _outline_from_datcom(_EX3, 12.0)
    x_ref = 2.60 * 12.0
    est = lba.estimate(outline, _EX3_SREF, _EX3_BREF * 12.0, x_ref, 4.26e6)
    assert est is not None
    assert est.cy_beta < 0.0 and est.cn_beta > 0.0
    assert est.cn_beta == -est.cn_beta_datcom
    assert math.isclose(est.cn_beta_datcom, -1.845e-3, rel_tol=TOL)
    # Force at x_force, couple = N_ref - (x_force - x_ref) Y  ->  about x_to the
    # pair gives Cn_ref - Cy (x_to - x_ref)/b; check with explicit statics.
    q_s_beta = 1.0
    y_force = est.cy_beta * q_s_beta
    n_ref = est.cn_beta * q_s_beta * (_EX3_BREF * 12.0)
    couple = n_ref - (est.x_force - x_ref) * y_force
    x_to = x_ref + 20.0
    n_to = couple + (est.x_force - x_to) * y_force
    cn_to = lba.transfer_cn_beta(est.cn_beta, est.cy_beta, x_ref, x_to, _EX3_BREF * 12.0)
    assert math.isclose(n_to / (_EX3_BREF * 12.0), cn_to, rel_tol=1e-12)


def test_estimate_returns_none_without_a_body():
    assert lba.estimate(None, 100.0, 400.0, 100.0, 1e6) is None
    assert lba.estimate(FuselageOutline(sections=[]), 100.0, 400.0, 100.0, 1e6) is None
    flat = FuselageOutline(sections=[FuselageSection(0.0, 0.0, 0.0),
                                     FuselageSection(100.0, 0.0, 0.0)])
    assert lba.estimate(flat, 100.0, 400.0, 100.0, 1e6) is None


def test_side_area_centroid_of_a_uniform_body_is_mid_length():
    body = lba.DatcomBody(x=(0.0, 10.0, 20.0), s=(1.0, 1.0, 1.0), r=(1.0, 1.0, 1.0))
    assert math.isclose(lba.side_area_centroid(body), 10.0)
    # A triangular profile (linear taper to zero) has its centroid at l/3
    tri = lba.DatcomBody(x=(0.0, 30.0), s=(1.0, 0.0), r=(1.0, 0.0))
    assert math.isclose(lba.side_area_centroid(tri), 10.0)


# --------------------------------------------------------------------------- #
# The interpolators reproduce the Fortran's end rules
# --------------------------------------------------------------------------- #
def test_tbfunx_end_rules():
    x, y = (0.0, 1.0, 2.0, 3.0), (0.0, 1.0, 4.0, 9.0)
    assert lba._tbfunx(1.5, x, y, 0, 0)[0] == pytest.approx(2.5)      # linear inside
    assert lba._tbfunx(5.0, x, y, 0, 0)[0] == 9.0                     # clamp
    assert lba._tbfunx(5.0, x, y, 0, 1)[0] == pytest.approx(9.0 + 2 * 5.0)   # linear from end two
    assert lba._tbfunx(5.0, x, y, 0, 2)[0] == pytest.approx(25.0)     # end parabola (exact here)
    assert lba._tbfunx(-1.0, x, y, 2, 0)[0] == pytest.approx(1.0)     # start parabola


def test_tlinex_matches_hand_interpolation_on_chart_a():
    # ex3's K_N chart-A look-up, worked by hand in the design-note review:
    # rows 14 -> (.40, 2.21), 10 -> (.74, 2.60), t2 = 0.6148, t1 = 0.2535
    val = lba._tlinex(lba._KN_A_X1, lba._KN_A_X2, lba._KN_A_Y, 12.986, 0.5689, 2, 1, 2, 1)
    assert val == pytest.approx(1.6068, abs=2e-4)


# --------------------------------------------------------------------------- #
# atmosphere.py -- the viscosity/Reynolds owner (L-7.13)
# --------------------------------------------------------------------------- #
def test_sea_level_viscosity_and_reynolds():
    mu = atmosphere.dynamic_viscosity(518.67)
    assert math.isclose(mu, 3.737e-7, rel_tol=2e-3)          # textbook sea-level value
    assert math.isclose(atmosphere.standard_temperature_r(0.0), 59.0 + 459.67)
    # Re/ft at 100 kt EAS, sea level: rho V / mu
    v = 100.0 * 1.6878098571011957
    assert math.isclose(atmosphere.reynolds_per_ft(100.0, 0.0), RHO_SL * v / mu, rel_tol=1e-9)


def test_reynolds_uses_true_airspeed_and_local_viscosity():
    """At altitude rho falls, TAS rises and mu falls: Re/ft at fixed EAS is
    lower than sea level by ~sqrt(sigma) * mu_0/mu (not the EAS shortcut)."""
    re_sl = atmosphere.reynolds_per_ft(200.0, 0.0)
    re_20 = atmosphere.reynolds_per_ft(200.0, 20000.0)
    assert 0.5 < re_20 / re_sl < 0.85
    with pytest.raises(ValueError):
        atmosphere.dynamic_viscosity(0.0)


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
    raise SystemExit(1 if failed else 0)
