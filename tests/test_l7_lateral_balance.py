"""L-7 lateral body aero in the balanced lateral cases -- gates G2 … G13.

Design note ``docs/40_history/33_l7_lateral_body_aero_note.md`` §8 (rev. 3).
G1, the DATCOM oracle, is ``tests/test_lateral_body_aero.py``; this file gates
what the term does once it is applied beside the fin in ``balance``:

* **G2** ``SUDDEN RUDDER`` (``beta = 0``) takes exactly zero body load;
* **G3** static directional stability -- fin + body ``Cn_beta`` restoring on
  every fixture that assembles lateral cases, and *flagged* (not silently
  emitted) when it is not;
* **G4** the rudder-neutral conditions (23.441(a)(3), 23.443(b)) keep a
  restoring yaw acceleration with the term on;
* **G5** direction: ``|psi_ddot|`` falls and ``|n_y|`` rises on every
  ``beta != 0`` case -- the corrected 2026-08-15 statement, asserted;
* **G6** closed form: the applied force + free couple reproduce
  ``Cy_beta q S beta`` and ``Cn_beta q S b beta`` about ``xw`` exactly;
* **G7** independent producer: Munk's isolated-body couple sits *below*
  DATCOM's wing-body value (a Munk value above it means a porting error);
* **G8** the term off (the default) changes nothing -- no ``body-aero`` load,
  identical closure to a case assembled without the term at all;
* **G9/G10** six-DOF closure with the term on, in memory and from the deck's own
  card text, in both unit systems;
* **G11** the symmetric half still closes inside ``RESIDUAL_GATE`` with the fin
  and the body term removed;
* **G12** the twins mirror -- ``fy``/``mz`` and the recorded body force/moment
  and sideslip flip through the single owner;
* **G13** the methods stamp carries the two wordings -- ``test_methods_stamp``.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import replace

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

from sloads import io  # noqa: E402
from sloads.export.balanced_deck import balanced_deck, case_sids  # noqa: E402
from sloads.export.equilibrium import parse_cards, resultant  # noqa: E402
from sloads.derived_geometry import require_wing_reference  # noqa: E402
from sloads.fuselage_moment import munk_yaw_slope_per_deg  # noqa: E402
from sloads.models import LateralBodyAeroInput  # noqa: E402
from sloads.modules.balance import (  # noqa: E402
    BODY_AERO_SOURCE,
    RESIDUAL_GATE,
    assemble,
    body_aero_loads,
    build_balanced_cases,
    is_lateral,
    lateral_aero_terms,
)
from sloads.modules.balance import resultant6 as case_resultant  # noqa: E402
from sloads.modules.select import default_critical, default_envelope  # noqa: E402
from sloads.units import Channel, UnitSystem, deliverable_units  # noqa: E402

#: The two shipped fixtures with lateral cases and a body outline.
EXAMPLES = ("ga6_normal.project.json", "concept_regional_jet.project.json")


def _project(example: str, enabled: bool):
    p = io.load_project(os.path.join(_ROOT, "examples", example))
    p.aero_coeffs = replace(p.aero_coeffs,
                            lateral_body_aero=LateralBodyAeroInput(enabled=enabled))
    return p


def _lateral(cases, hand="R"):
    return {c.label: c for c in cases if is_lateral(c) and (not hand or c.hand == hand)}


def _body_loads(case):
    return [ld for ld in case.loads if ld.source == BODY_AERO_SOURCE]


# --------------------------------------------------------------------------- #
# G2 / G8 -- nothing where nothing should be
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_g2_sudden_rudder_takes_exactly_zero_body_load(example):
    on = _lateral(build_balanced_cases(_project(example, True)))
    off = _lateral(build_balanced_cases(_project(example, False)))
    case = on["SUDDEN RUDDER"]
    assert case.beta_deg == 0.0
    assert _body_loads(case) == []
    assert case.body_side_force == 0.0 and case.body_yaw_moment == 0.0
    # ...and the case is the fin-only case to the last digit.
    ref = off["SUDDEN RUDDER"]
    assert case.delta_ny == ref.delta_ny and case.r_dot == ref.r_dot
    assert list(case.loads) == list(ref.loads)


@pytest.mark.parametrize("example", EXAMPLES)
def test_g8_the_term_off_is_the_default_and_changes_nothing(example):
    """Off by default (L-7.3): a fixture that never heard of the input assembles
    exactly what a fixture with it disabled does, and neither carries a
    ``body-aero`` load or a non-zero body force/moment."""
    plain = io.load_project(os.path.join(_ROOT, "examples", example))
    assert (plain.aero_coeffs.lateral_body_aero is None
            or not plain.aero_coeffs.lateral_body_aero.enabled)
    a = _lateral(build_balanced_cases(plain), hand="")
    b = _lateral(build_balanced_cases(_project(example, False)), hand="")
    assert sorted(a) == sorted(b)
    for label in a:
        ca, cb = a[label], b[label]
        assert not _body_loads(ca) and not _body_loads(cb)
        assert ca.body_side_force == 0.0 and ca.body_yaw_moment == 0.0
        assert ca.delta_ny == cb.delta_ny and ca.r_dot == cb.r_dot
        assert ca.loads == cb.loads
        # The estimate is still stated on the case (L-7.16) -- as an estimate.
        assert any("L-7) DISABLED -- estimated" in n for n in ca.notes), label


# --------------------------------------------------------------------------- #
# G3 / G4 / G5 -- the physics
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_g3_static_directional_stability_is_restoring_and_stated(example):
    for enabled in (False, True):
        for label, case in _lateral(build_balanced_cases(_project(example, enabled))).items():
            assert case.cn_beta_net is not None, f"{example} {label}"
            assert case.cn_beta_net < 0.0, f"{example} {label}: net Cn_beta {case.cn_beta_net}"
            assert any("restoring" in n and "NOT RESTORING" not in n for n in case.notes), label


def test_g3_an_unstable_configuration_is_flagged_not_silently_emitted():
    """Override the body Cn_beta with a value that overwhelms the fin: the case
    still assembles (the number is the user's) but says so, loudly."""
    p = _project("concept_regional_jet.project.json", True)
    p.aero_coeffs = replace(p.aero_coeffs, lateral_body_aero=LateralBodyAeroInput(
        enabled=True, cy_beta=-0.001, cn_beta=+0.05))
    cases = _lateral(build_balanced_cases(p))
    case = cases["YAW 15 NEUTRAL"]
    assert case.cn_beta_net > 0.0
    assert any("NOT RESTORING -- DIRECTIONALLY UNSTABLE" in n for n in case.notes)
    assert any("(entered)" in n for n in case.notes)


@pytest.mark.parametrize("example", EXAMPLES)
def test_g4_rudder_neutral_conditions_keep_a_restoring_yaw_acceleration(example):
    """23.441(a)(3) is a +beta case: restoring = nose to starboard = -mz = r_dot < 0.
    23.443(b)'s computed hand is -beta (SC-1): restoring = r_dot > 0."""
    on = _lateral(build_balanced_cases(_project(example, True)))
    assert on["YAW 15 NEUTRAL"].beta_deg > 0 and on["YAW 15 NEUTRAL"].r_dot < 0.0
    assert on["SIDE GUST"].beta_deg < 0 and on["SIDE GUST"].r_dot > 0.0


@pytest.mark.parametrize("example", EXAMPLES)
def test_g5_yaw_acceleration_falls_and_ny_rises_on_every_sideslip_case(example):
    on = _lateral(build_balanced_cases(_project(example, True)))
    off = _lateral(build_balanced_cases(_project(example, False)))
    for label in ("YAW TO SIDESLIP", "YAW 15 NEUTRAL", "SIDE GUST"):
        a, b = off[label], on[label]
        assert abs(b.delta_ny) > abs(a.delta_ny), f"{example} {label}: |n_y| did not rise"
        # The side force adds to the fin's: same sign, larger magnitude.
        assert math.copysign(1, b.delta_ny) == math.copysign(1, a.delta_ny)
        # The couple opposes the fin's: |r_dot| falls on the rudder-neutral
        # cases; on 23.441(a)(2) the rudder drives the case past equilibrium
        # and the sign may reverse (note 19 §4) -- what must hold everywhere is
        # that the body's yawing moment has the destabilizing sign.
        if label != "YAW TO SIDESLIP":
            assert abs(b.r_dot) < abs(a.r_dot), f"{example} {label}: |psi_dd| did not fall"
        assert math.copysign(1, b.body_yaw_moment) == math.copysign(1, b.beta_deg), label
        assert math.copysign(1, b.body_side_force) == -math.copysign(1, b.beta_deg), label


# --------------------------------------------------------------------------- #
# G6 / G7 -- the closed forms
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_g6_the_applied_pair_reproduces_the_derivatives_about_xw(example):
    p = _project(example, True)
    env = default_envelope(p)
    vn = {pt.case: pt for pt in env.vn}
    for cond in default_critical(p, env).conditions:
        if cond.component != "vtail" or cond.beta_deg in (None, 0.0):
            continue
        terms = lateral_aero_terms(p, cond, vn[cond.case])
        assert terms.enabled and terms.available, cond.label
        loads = body_aero_loads(terms)
        assert len(loads) == 1
        fx, fy, fz, _mx, my, mz = case_resultant(loads, (terms.x_ref, 0.0, terms.z_force))
        assert fy == pytest.approx(terms.side_force, rel=1e-12)
        assert mz == pytest.approx(terms.yaw_moment_ref, rel=1e-12)
        assert fx == fz == 0.0 and my == pytest.approx(0.0, abs=1e-9)
        # ...and the numbers are the derivatives at the case's own q, S, b, beta.
        assert terms.basis == "DATCOM"
        assert terms.side_force / terms.beta_deg < 0.0     # port at +beta
        assert terms.yaw_moment_ref / terms.beta_deg > 0.0  # destabilizing


@pytest.mark.parametrize("example", EXAMPLES)
def test_g7_munk_isolated_body_couple_sits_below_datcoms_wing_body_value(example):
    p = _project(example, True)
    env = default_envelope(p)
    vn = {pt.case: pt for pt in env.vn}
    cond = next(c for c in default_critical(p, env).conditions
                if c.component == "vtail" and c.label == "YAW 15 NEUTRAL")
    terms = lateral_aero_terms(p, cond, vn[cond.case])
    wr = require_wing_reference(p)
    munk = munk_yaw_slope_per_deg(p.geometry.fuselage, wr.s_sqft,
                                  p.vtail_loads.wing_span_in)
    assert munk is not None and munk > 0.0
    assert munk < terms.cn_beta, (
        f"{example}: Munk {munk:.6f}/deg above DATCOM {terms.cn_beta:.6f}/deg -- porting error")


# --------------------------------------------------------------------------- #
# G9 / G10 / G11 / G12 -- the fences, with the term on
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_g9_the_case_closes_in_six_dof_with_the_term_on(example):
    for case in build_balanced_cases(_project(example, True)):
        if not is_lateral(case):
            continue
        fx, fy, fz, mx, my, mz = case_resultant(case.loads, (case.cg_x, 0.0, case.cg_z))
        n_w = case.n_w
        for name, val, scale in (("fx", fx, n_w), ("fy", fy, n_w), ("fz", fz, n_w),
                                 ("mx", mx, n_w * case.semi_span),
                                 ("my", my, n_w * case.mac),
                                 ("mz", mz, n_w * case.semi_span)):
            assert abs(val) < 1e-9 * scale, f"{example} {case.label} {name} {val}"


@pytest.mark.parametrize("example", EXAMPLES)
@pytest.mark.parametrize("system", (UnitSystem.IMPERIAL, UnitSystem.SI))
def test_g10_the_deck_balances_from_its_own_cards_with_the_term_on(example, system):
    p = _project(example, True)
    cases = build_balanced_cases(p)
    u = deliverable_units(system, Channel.SOLVER)
    text = balanced_deck(p, system=system, cases=cases)
    grids, _, _, forces, moments = parse_cards(text)
    seen = 0
    for sid, case in zip(case_sids(cases), cases):
        if not is_lateral(case):
            continue
        seen += 1
        ref = (case.cg_x * u.length.factor, 0.0, case.cg_z * u.length.factor)
        got = resultant(forces, moments, grids, sid, ref)
        n_w = case.n_w * case.safety_factor * u.force.factor
        n_w_mac, n_w_span = n_w * case.mac * u.length.factor, n_w * case.semi_span * u.length.factor
        assert abs(got.fx) < 1e-5 * n_w and abs(got.fy) < 1e-5 * n_w and abs(got.fz) < 1e-5 * n_w
        assert abs(got.mx) < 1e-5 * n_w_span and abs(got.my) < 1e-5 * n_w_mac
        assert abs(got.mz) < 1e-5 * n_w_span, f"{example} {system.value} {case.label}"
    assert seen == 8
    assert "lateral body aero (L-7) APPLIED" in text


@pytest.mark.parametrize("example", EXAMPLES)
def test_g11_the_symmetric_half_still_closes_with_fin_and_body_terms_removed(example):
    for case in build_balanced_cases(_project(example, True)):
        if not is_lateral(case) or case.hand != "R":
            continue
        applied = [ld for ld in case.loads if not ld.source.startswith("closure-")]
        half = [ld for ld in applied
                if ld.source not in ("vtail-air", BODY_AERO_SOURCE)]
        _fx, fy, fz, mx, my, mz = case_resultant(half, (case.cg_x, 0.0, case.cg_z))
        assert fy == 0.0 and mx == 0.0 and mz == 0.0, f"{example} {case.label}"
        n_w = case.n_w
        assert abs(fz) <= RESIDUAL_GATE * n_w, f"{example} {case.label} fz"
        assert abs(my) <= RESIDUAL_GATE * n_w * case.mac, f"{example} {case.label} my"


@pytest.mark.parametrize("example", EXAMPLES)
def test_g12_the_twins_mirror_the_body_term(example):
    cases = build_balanced_cases(_project(example, True))
    right = _lateral(cases, "R")
    left = _lateral(cases, "L")
    for label, r in right.items():
        lft = left[label]
        assert lft.body_side_force == -r.body_side_force
        assert lft.body_yaw_moment == -r.body_yaw_moment
        assert lft.beta_deg == -r.beta_deg
        assert lft.cn_beta_net == r.cn_beta_net
        rb, lb = _body_loads(r), _body_loads(lft)
        assert len(rb) == len(lb)
        for a, b in zip(rb, lb):
            assert (b.x, b.y, b.z) == (a.x, -a.y, a.z)
            assert (b.fx, b.fy, b.fz) == (a.fx, -a.fy, a.fz)
            assert (b.mx, b.my, b.mz) == (-a.mx, a.my, -a.mz)


# --------------------------------------------------------------------------- #
# The seams
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_select_publishes_the_sideslip_and_the_fin_derivatives(example):
    """L-7.6 / L-7.11: every v-tail condition carries beta (SC-1 sense) and the
    fin's Cy_beta / Cn_beta about xw; the maneuver betas are the regulation's
    own angles, the gust's is the load's own Kgt*Ude/V, negative for the +fy hand."""
    p = _project(example, False)
    conds = {c.label: c for c in default_critical(p).conditions if c.component == "vtail"}
    assert conds["SUDDEN RUDDER"].beta_deg == 0.0
    assert conds["YAW TO SIDESLIP"].beta_deg == 19.5
    assert conds["YAW 15 NEUTRAL"].beta_deg == 15.0
    assert conds["SIDE GUST"].beta_deg < 0.0
    for c in conds.values():
        assert c.cy_beta_fin < 0.0 and c.cn_beta_fin < 0.0     # restoring aft fin
    wr = require_wing_reference(p)
    vt = p.vtail_loads
    c = conds["SIDE GUST"]
    assert c.cn_beta_fin == pytest.approx(c.cy_beta_fin * (vt.xv25 - wr.xw) / vt.wing_span_in)


def test_a_persisted_critical_set_without_beta_says_so_instead_of_guessing():
    """L-7.6: beta comes from SELECT or not at all. A critical set that predates
    the field assembles the fin-only case and says why the term is absent."""
    from sloads.modules.balance import LateralAeroTerms  # noqa: F401
    p = _project("ga6_normal.project.json", True)
    env = default_envelope(p)
    crit = default_critical(p, env)
    stale = replace(crit, conditions=[
        replace(c, beta_deg=None, cy_beta_fin=None, cn_beta_fin=None)
        if c.component == "vtail" else c for c in crit.conditions])
    p.envelope = replace(env, critical=stale)
    cases = _lateral(build_balanced_cases(p))
    for label, case in cases.items():
        assert not _body_loads(case), label
        assert any("NOT estimable" in n and "re-run SELECT" in n for n in case.notes), label


def test_direct_assemble_without_terms_keeps_the_standing_statement_only():
    """A caller that passes the fin set but no terms (the per-condition tests)
    gets the standing L-7 statement and no per-case sentence."""
    p = _project("ga6_normal.project.json", True)
    env = default_envelope(p)
    from sloads.cg_cases import flight_cases
    from sloads.mass_distribution import derive_case_loadings
    from sloads.modules.balance import _fin_distributions
    fins = _fin_distributions(p)
    cond = next(c for c in default_critical(p, env).conditions if c.label == "YAW 15 NEUTRAL")
    point = {pt.case: pt for pt in env.vn}[cond.case]
    cg = {c.name: c for c in flight_cases(p)}[point.cg]
    loading = {ld.name: ld for ld in derive_case_loadings(p)}[point.cg]
    case = assemble(p, cond.label, point, loading, cg, case_ref=cond.case_ref,
                    lateral=fins[cond.label])
    assert any("L-7 term" in n for n in case.notes)
    assert not any("lateral body aero (L-7)" in n for n in case.notes)
    assert case.beta_deg is None and case.cn_beta_net is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
