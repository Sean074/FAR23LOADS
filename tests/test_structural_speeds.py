"""Validate STRSPEED against the FAR 23 LOADS manual, Appendix A.

The 6-place single's structural speeds and load factors are printed in the
Appendix A V-n / geometry table: VA 121.3, VC 170, VD 212.5, VF 105.5 (KEAS);
limit load factor +3.8 / -1.52; and MC 0.323 / MD 0.403 at the 12000 ft shoulder
altitude. The maneuver speed VA = VS*sqrt(n) and flap speed VF = 1.8*VSF are
computed from the (input) clean/flap stall speeds, so they validate the equations
rather than echoing inputs; VC is chosen and VD is its 1.25 floor.

Per Decision 3 the figures are matched within ±0.1%; the wing area (read from the
WINGGEOM geometry slice, 2*13257/144 = 184.1 ft^2) is g-independent.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import value_of

from sloads import AeroCoefficientsInput, Project, StructuralSpeedsInput, io
from sloads.constants import (
    cruise_speed_coefficient,
    dive_ratio_coefficient,
)
from sloads.modules import structural_speeds as calc

TOL = 1e-3  # ±0.1% relative


def _project_clmax(name, clmax_clean, clmax_flap):
    """A Project carrying only the CLmax (stall-speed source) on aero_coeffs -- the
    minimum STRSPEED needs to derive VS/VSF (M1-1b)."""
    return Project(name=name, aero_coeffs=AeroCoefficientsInput(
        clmax_clean=clmax_clean, clmax_flap=clmax_flap))

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "ga6_normal.project.json",
)


def results():
    project = io.load_project(_EXAMPLE)
    return calc.design_speeds(project, project.speeds)


def test_maneuver_load_factors():
    # W = 3400, normal: n = 2.1 + 24000/13400 = 3.891 -> capped 3.8; n_neg = -1.52.
    r = results()
    assert math.isclose(value_of(r, "limit_positive_load_factor"), 3.8, rel_tol=TOL)
    assert math.isclose(value_of(r, "limit_negative_load_factor"), -1.52, rel_tol=TOL)
    assert math.isclose(value_of(r, "wing_loading_w_s"), 3400 / 184.125, rel_tol=2e-3)


def test_design_speeds_match_manual():
    # Appendix A: VA 121.3, VC 170, VD 212.5, VF 105.5 (KEAS).
    r = results()
    assert math.isclose(value_of(r, "maneuver_speed_va"), 121.3, rel_tol=TOL)
    assert math.isclose(value_of(r, "cruise_speed_vc"), 170, rel_tol=TOL)
    assert math.isclose(value_of(r, "dive_speed_vd"), 212.5, rel_tol=TOL)
    assert math.isclose(value_of(r, "flap_speed_vf"), 105.5, rel_tol=TOL)


def test_vd_floor_no_chosen_speeds():
    # Appendix A p155, Cat N, no chosen speeds: FAR 23.335(b) requires
    # VD >= max(K_d*VCmin, 1.25*VC). Here K_d*VCmin = 1.40*141.8 = 198.53 kt
    # governs over 1.25*VCmin = 177.26. (Pre-fix code returned 177.26 -- 10.7%
    # non-conservative; STRSPEED.BAS V2DMIN=K2*V1CMIN, lines 380/390.)
    inp = StructuralSpeedsInput(category="N", weight_lb=3400, wing_area_sqft=184.125,
                                vh_kt=190)
    r = calc.design_speeds(_project_clmax("n", 1.4068, 1.5857), inp)
    assert math.isclose(value_of(r, "dive_speed_vd"), 198.53, rel_tol=TOL)          # p155
    assert math.isclose(value_of(r, "minimum_dive_vd_min"), 198.53, rel_tol=TOL)


def test_minimum_cruise_speed():
    # K_c = 33 (W/S = 18.47 < 20); VC(min) = 33*sqrt(18.47) = 141.8 kt.
    r = results()
    assert math.isclose(value_of(r, "minimum_cruise_vc_min"), 141.8, rel_tol=2e-3)


def test_cruise_and_dive_mach_at_shoulder():
    # At 12000 ft: MC 0.323, MD 0.403.
    r = results()
    assert math.isclose(value_of(r, "cruise_mach_mc"), 0.323, rel_tol=3e-3)
    assert math.isclose(value_of(r, "dive_mach_md"), 0.403, rel_tol=3e-3)


def test_utility_and_acrobatic_caps():
    # Category caps: utility 4.4, acrobatic 6.0; negative -0.4n / -0.5n.
    base = dict(weight_lb=3400, wing_area_sqft=184.125, chosen_vc=170, chosen_vd=212.5)
    u = calc.design_speeds(_project_clmax("u", 1.4068, 1.5857),
                           StructuralSpeedsInput(category="U", **base))
    a = calc.design_speeds(_project_clmax("a", 1.4068, 1.5857),
                           StructuralSpeedsInput(category="A", **base))
    assert math.isclose(value_of(u, "limit_positive_load_factor"), 4.4, rel_tol=TOL)
    assert math.isclose(value_of(u, "limit_negative_load_factor"), -0.4 * 4.4, rel_tol=TOL)
    assert math.isclose(value_of(a, "limit_positive_load_factor"), 6.0, rel_tol=TOL)
    assert math.isclose(value_of(a, "limit_negative_load_factor"), -0.5 * 6.0, rel_tol=TOL)


def test_concept_bypasses_cap():
    # Category C (concept): the user's n / n_neg are used verbatim, with no
    # FAR 23.337 formula or cap -- even above the 12,500 lb GA band.
    inp = StructuralSpeedsInput(category="C", weight_lb=18000, wing_area_sqft=280,
                                chosen_vc=250, chosen_vd=312.5,
                                chosen_n=4.0, chosen_nneg=-2.0)
    r = calc.design_speeds(_project_clmax("c", 2.101, 2.821), inp)
    assert value_of(r, "limit_positive_load_factor") == 4.0
    assert value_of(r, "limit_negative_load_factor") == -2.0


def test_concept_requires_explicit_load_factors():
    # Concept mode without chosen_n/chosen_nneg is an error (there is no FAR floor
    # to fall back on).
    inp = StructuralSpeedsInput(category="C", weight_lb=18000, wing_area_sqft=280,
                                chosen_vc=250, chosen_vd=312.5)
    raised = False
    try:
        calc.design_speeds(_project_clmax("c", 2.101, 2.821), inp)
    except ValueError:
        raised = True
    assert raised


def test_speed_coefficients_clamp_at_wing_loading_100():
    # FAR 23.335 tabulates Kc/Kd only to W/S = 100 (28.6 / 1.35). Past 100 the
    # coefficients HOLD at those endpoints; prior code kept extrapolating the taper
    # (non-conservative for the heavy-concept band). M1-6 (review T9).
    for cat in ("N", "U", "A"):
        # Continuous at the boundary: the taper reaches the endpoint exactly at 100.
        assert math.isclose(cruise_speed_coefficient(cat, 100.0), 28.6, rel_tol=TOL)
        assert math.isclose(dive_ratio_coefficient(cat, 100.0), 1.35, rel_tol=TOL)
        # Clamped (not extrapolated below the endpoint) well past 100.
        assert cruise_speed_coefficient(cat, 180.0) == cruise_speed_coefficient(cat, 100.0)
        assert dive_ratio_coefficient(cat, 180.0) == dive_ratio_coefficient(cat, 100.0)
        assert math.isclose(cruise_speed_coefficient(cat, 180.0), 28.6, rel_tol=TOL)
        assert math.isclose(dive_ratio_coefficient(cat, 180.0), 1.35, rel_tol=TOL)


def test_out_of_band_note_above_wing_loading_100():
    # A concept with W/S > 100 gets an OUT-OF-BAND note on the design-speeds
    # condition; a GA aircraft (W/S ~ 20) does not. M1-6 (review T9).
    inp = StructuralSpeedsInput(category="C", weight_lb=40000, wing_area_sqft=280,
                                chosen_vc=300, chosen_vd=375,
                                chosen_n=4.0, chosen_nneg=-2.0)
    r = calc.design_speeds(_project_clmax("c", 2.101, 2.821), inp)
    speeds = next(c for c in r if c.title == "Structural design speeds")
    assert "OUT-OF-BAND" in speeds.note

    ga = next(c for c in results() if c.title == "Structural design speeds")
    assert ga.note == ""


def test_operational_placards_ga6():
    # Preliminary Subpart-G placards derived from the GA6 design speeds (M2-10).
    # VD 212.5, VC 170, VF 105.5, MC 0.3226, MD 0.4033 (Appendix A) =>
    # VNE = 0.9*VD = 191.25; VNO = min(VC, 0.89*VNE) = min(170, 170.21) = 170;
    # MNE = 0.9*MD = 0.363; VMO = VC = 170; MMO = MC; VFE = VF (14 CFR 23.1505/
    # 23.1511; Ref 1 p47; reference/14CFR_operating_limitations.md).
    project = io.load_project(_EXAMPLE)
    ds = calc.design_speed_values(project, project.speeds)
    p = calc.operational_placards(ds)
    assert math.isclose(p.vne, 0.9 * 212.5, rel_tol=TOL)
    assert math.isclose(p.vno, 170.0, rel_tol=TOL)
    assert math.isclose(p.vfe, ds.vf, rel_tol=TOL)
    assert math.isclose(p.mne, 0.9 * 0.4033, rel_tol=TOL)
    assert math.isclose(p.vmo, 170.0, rel_tol=TOL)
    assert math.isclose(p.mmo, ds.mc, rel_tol=TOL)


def test_operational_implications_shows_both_families():
    # The advisory condition always lists both placard families (M2-10 decision).
    project = io.load_project(_EXAMPLE)
    op = calc.operational_implications(project, project.speeds)
    placards = op[0]
    labels = [v.label for v in placards.values]
    assert any("VNE" in la for la in labels) and any("VNO" in la for la in labels)
    assert any("VMO" in la for la in labels) and any("MMO" in la for la in labels)
    assert any("VFE" in la for la in labels)
    # Advisory caption present; no targets set -> only the placard condition.
    assert "certification" in placards.note.lower()
    assert len(op) == 1


def test_operational_target_feasible_and_infeasible():
    # A target VNE achievable by the design speeds is feasible; one above 0.9*VD is not.
    project = io.load_project(_EXAMPLE)
    ds = calc.design_speed_values(project, project.speeds)  # VD 212.5 -> VNE cap 191.25
    inp = project.speeds
    inp.target_vne = 180.0                    # needs VD >= 200 (<= 212.5) -> feasible
    checks = calc.operational_target_checks(inp, ds)
    vne_check = next(c for c in checks if c.target_label == "VNE")
    assert vne_check.driver_label == "VD"
    assert math.isclose(vne_check.required, 180.0 / 0.9, rel_tol=TOL)
    assert vne_check.feasible

    inp.target_vne = 200.0                    # needs VD >= 222.2 (> 212.5) -> infeasible
    checks = calc.operational_target_checks(inp, ds)
    assert not next(c for c in checks if c.target_label == "VNE").feasible
    # The feasibility condition is emitted with an INFEASIBLE note.
    op = calc.operational_implications(project, inp)
    feas = next(c for c in op if c.title.startswith("Operational-target"))
    assert "INFEASIBLE" in feas.note


def test_operational_target_mmo_margin():
    """A turbine target MMO requires MD >= MMO + the *resolved* Mach margin.

    That margin was a hardcoded 0.05 in the ladder until F25-2; it is now
    ``resolve_mach_margin``'s answer, so the ladder and the dive-speed resolution
    can never disagree about one project's margin. The default is 0.07
    (25.335(b)(2) since Amdt 25-91; 23.335(b)(4)(iii) for commuter).
    """
    project = io.load_project(_EXAMPLE)
    ds = calc.design_speed_values(project, project.speeds)  # MD ~ 0.4033
    inp = project.speeds
    inp.target_mmo = 0.40                      # needs MD >= 0.47 (> 0.4033) -> infeasible
    check = next(c for c in calc.operational_target_checks(inp, ds) if c.target_label == "MMO")
    assert math.isclose(check.required, 0.47, rel_tol=TOL)
    assert not check.feasible


def test_operational_target_mmo_margin_follows_a_declared_margin():
    """A project that declared a reduced margin gets the ladder checked against
    *that* margin -- one authority, not two."""
    project = io.load_project(_EXAMPLE)
    inp = project.speeds
    inp.target_mmo = 0.40
    inp.mach_margin_min = 0.06
    inp.mach_margin_basis = "HSPF credited per 25.335(b)(2)"
    ds = calc.design_speed_values(project, inp)
    check = next(c for c in calc.operational_target_checks(inp, ds) if c.target_label == "MMO")
    assert math.isclose(check.required, 0.46, rel_tol=TOL)


def test_run_requires_speeds():
    raised = False
    try:
        calc.run(Project(name="empty"))
    except ValueError:
        raised = True
    assert raised


# --------------------------------------------------------------------------- #
# F25-2 -- the 25.335(b) Mach-margin dive-speed route
# --------------------------------------------------------------------------- #
# All numbers below are for examples/concept_regional_jet.project.json: VC 310 kt,
# shoulder 24,000 ft, where sqrt(sigma)*a = 411.19 kt per unit Mach, so
# MC = 310/411.19 = 0.75384 and MD = VD/411.19. The margins that follow:
#   VD 350    -> MD 0.85112, margin +0.09728   (the fixture's own intent)
#   VD 338.79 -> MD 0.82384, margin +0.07000   (exactly the default)
#   VD 335    -> MD 0.81471, margin +0.06087   (reduced band, needs a basis)
# Under the speed-ratio route the same fixture is forced to VD = 1.25*310 = 387.5,
# MD 0.94231, margin +0.18847 -- the defect F25-2 fixes.
_RJ = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples", "concept_regional_jet.project.json",
)


def _rj(**overrides):
    """The RJ fixture forced onto the Mach-margin route, with field overrides."""
    from sloads import VdBasis

    project = io.load_project(_RJ)
    project.speeds.vd_basis = VdBasis.MACH_MARGIN
    for k, v in overrides.items():
        setattr(project.speeds, k, v)
    return project


def test_margin_route_honours_a_compliant_chosen_vd():
    """The defect case. The fixture's own VD 350 clears 0.07 M and must survive;
    before F25-2 it was silently overridden to 1.25*VC = 387.5 kt, inflating every
    dive-speed load case."""
    ds = calc.design_speed_values(*(lambda p: (p, p.speeds))(_rj()))
    assert math.isclose(ds.vd, 350.0, rel_tol=TOL)
    assert math.isclose(ds.md, 0.85112, rel_tol=TOL)
    assert math.isclose(ds.mach_margin, 0.09728, rel_tol=1e-2)
    assert ds.mach_margin_required == calc.MACH_MARGIN_DEFAULT
    assert not ds.mach_margin_reduced
    # And the route it did NOT take is still reported, so the difference is auditable.
    assert math.isclose(ds.vd_ratio_floor, 387.5, rel_tol=TOL)


def test_margin_route_raises_a_short_chosen_vd():
    """The 0.05 floor constrains what may be *declared*; a chosen VD that falls
    short of the requirement is raised, like every other design-speed minimum."""
    p = _rj(chosen_vd=320.0)
    ds = calc.design_speed_values(p, p.speeds)
    assert math.isclose(ds.vd, 338.79, rel_tol=TOL)
    assert math.isclose(ds.mach_margin, calc.MACH_MARGIN_DEFAULT, rel_tol=1e-6)


def test_reduced_margin_needs_a_written_basis():
    p = _rj(chosen_vd=335.0, mach_margin_min=0.06)
    try:
        calc.design_speed_values(p, p.speeds)
    except ValueError as exc:
        assert "rational" in str(exc).lower()
    else:
        raise AssertionError("a sub-0.07 margin with no basis must be refused")


def test_reduced_margin_with_a_basis_is_accepted_and_flagged():
    p = _rj(chosen_vd=335.0, mach_margin_min=0.06,
            mach_margin_basis="HSPF credited per 25.335(b)(2)")
    ds = calc.design_speed_values(p, p.speeds)
    assert math.isclose(ds.vd, 335.0, rel_tol=TOL)
    assert ds.mach_margin_reduced, "a reduced margin must be flagged, never silent"
    note = calc.design_speeds(p, p.speeds)[1].note
    assert "REDUCED MARGIN" in note
    assert "certification risk" in note
    assert "HSPF" in note, "the user's own basis text belongs in the record"


def test_a_margin_below_the_absolute_floor_is_refused():
    """0.05 M is 25.335(b)(2)'s 'in any case' floor -- not an input, at any price."""
    p = _rj(mach_margin_min=0.04, mach_margin_basis="we would really like to")
    try:
        calc.design_speed_values(p, p.speeds)
    except ValueError as exc:
        assert "floor" in str(exc).lower()
    else:
        raise AssertionError("a margin below 0.05 M must be refused")


def test_margin_policy_table():
    """:func:`resolve_mach_margin` is the single authority; this is its contract."""
    def margin(**kw):
        return calc.resolve_mach_margin(StructuralSpeedsInput(**kw))

    assert margin().required == calc.MACH_MARGIN_DEFAULT
    assert not margin().reduced
    assert margin(mach_margin_min=0.10).required == 0.10
    assert not margin(mach_margin_min=0.10).reduced
    assert margin(mach_margin_min=0.06, mach_margin_basis="HSPF").reduced
    for bad in (dict(mach_margin_min=0.06), dict(mach_margin_min=0.049),
                dict(mach_margin_min=0.0)):
        try:
            margin(**bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} should not resolve")


def test_margin_route_is_concept_category_only():
    """Decision D-1: withheld from N/U/A so the Appendix A oracles stay locked."""
    p = _rj(category="N")
    try:
        calc.design_speed_values(p, p.speeds)
    except ValueError as exc:
        assert "concept" in str(exc).lower()
    else:
        raise AssertionError("the margin route must be refused outside category C")


def test_margin_route_needs_a_shoulder_altitude_and_a_chosen_vd():
    for kw in (dict(shoulder_altitude_ft=0.0), dict(chosen_vd=None)):
        p = _rj(**kw)
        try:
            calc.design_speed_values(p, p.speeds)
        except ValueError:
            pass
        else:
            raise AssertionError(f"the margin route must refuse {kw}")


def test_margin_route_always_says_the_upset_term_is_missing():
    """25.335(b) wants the GREATER of the Mach margin and the (b)(1) upset-criterion
    speed increase. Only the Mach term exists here, so a clean margin is not a
    sufficiency demonstration and the output must never imply that it is."""
    p = _rj()
    note = calc.design_speeds(p, p.speeds)[1].note
    assert "NOT A SUFFICIENCY DEMONSTRATION" in note
    assert "upset" in note


def test_speed_ratio_route_reproduces_todays_numbers_on_every_example():
    """The reduction invariant: F25-2 must not move one number in any project that
    did not ask for the new route.

    Values read off the pre-F25-2 build (commit 5c7809b) and frozen here to full
    precision, so this is a real before/after comparison rather than a restatement
    of what the code now does. (VA/VF re-pinned 2026-08-17 when the dynamic
    pressure went from ``V^2/295`` to the exact ``V^2/295.237`` -- issue #26,
    register line in ``02_approved_corrections.md``; VD/VC do not depend on q.) VD/VC/VA/VF together cover every branch of the
    speed resolution -- including cessna_210, where the K_d*VCmin term governs
    (214.53) rather than the 1.25*VC floor (208.75).
    """
    import glob

    frozen = {                       # name: (vd, vc, va, vf)
        "atr42_100": (300.0, 240.0, 167.756878, 161.136638),
        "cessna_210": (214.529286, 167.0, 125.800909, 104.454285),
        "concept_heavy": (312.5, 250.0, 189.338480, 147.085572),
        "concept_regional_jet": (387.5, 310.0, 187.071106, 169.649611),
        "dhc8_dash8": (306.25, 245.0, 145.599724, 140.532490),
        # VA/VF re-pinned 2026-08-30 (register line in 02_approved_corrections):
        # both scale with sqrt(W/S), and the wing area moves 0.019 % under
        # closed-form planform integration -- VA 121.352521 -> 121.340758
        # (-0.0097 %), VF 105.544396 -> 105.534165. VC and VD are entered.
        "ga6_normal": (212.5, 170.0, 121.34075796089789, 105.53416467978909),
    }
    seen = set()
    for path in sorted(glob.glob(os.path.join(os.path.dirname(_RJ), "*.project.json"))):
        name = os.path.basename(path).replace(".project.json", "")
        project = io.load_project(path)
        if project.speeds is None or name not in frozen:
            continue
        # The RJ fixture ships on the margin route (F25-2 step 7); the invariant is
        # about the speed-ratio route, so force it back for the comparison.
        from sloads import VdBasis

        project.speeds.vd_basis = VdBasis.SPEED_RATIO
        ds = calc.design_speed_values(project, project.speeds)
        vd, vc, va, vf = frozen[name]
        assert math.isclose(ds.vd, vd, rel_tol=1e-6), f"{name} VD"
        assert math.isclose(ds.vc, vc, rel_tol=1e-6), f"{name} VC"
        assert math.isclose(ds.va, va, rel_tol=1e-6), f"{name} VA"
        assert math.isclose(ds.vf, vf, rel_tol=1e-6), f"{name} VF"
        seen.add(name)
    assert seen == set(frozen), f"a frozen example vanished: {set(frozen) - seen}"


def test_vb_is_input_only_and_checked_for_ordering():
    """D-5: VB is accepted and its 25.335(a) ordering checked; the +1.32*U_ref term
    needs the 25.341 gust schedule and is deferred to F25-1."""
    from sloads.validation import consistency_warnings

    p = _rj(vb_kt=400.0)                     # above VC 310 -> inverted
    codes = {w.code for w in consistency_warnings(p)}
    assert "vb_above_vc" in codes
    ok = _rj(vb_kt=250.0)
    assert "vb_above_vc" not in {w.code for w in consistency_warnings(ok)}
    # VB never moves a design speed.
    assert calc.design_speed_values(p, p.speeds).vd == calc.design_speed_values(
        _rj(), _rj().speeds).vd


def test_the_reduced_margin_reaches_the_dashboard():
    from sloads.validation import consistency_warnings

    p = _rj(chosen_vd=335.0, mach_margin_min=0.06, mach_margin_basis="HSPF credited")
    warnings = {w.code: w.message for w in consistency_warnings(p)}
    assert "mach_margin_reduced" in warnings
    assert "certification risk" in warnings["mach_margin_reduced"]
    assert "mach_margin_below_ratio_floor" in warnings, (
        "VD below 1.25*VC is expected on this route, and must be stated rather "
        "than left for a reviewer to trip over")


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
