"""Unit tests for the pure input-consistency predicates (``sloads.validation``).

Each predicate must fire on a crafted bad input and stay silent on well-formed
input -- in particular on the Appendix-A GA fixture (``examples/ga6_normal``),
where the tool reduces to the oracle-locked FAR 23 behaviour and nothing is
inconsistent.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import (
    LayoutInput,
    MassItem,
    MassItemKind,
    Project,
    SurfaceInput,
    consistency_warnings,
)
from sloads import io as sloads_io
from sloads.models import GeometryInput

_GA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "examples", "ga6_normal.project.json")


def _codes(project, page=None):
    return {w.code for w in consistency_warnings(project)
            if page is None or w.page == page}


def test_ga_fixture_is_clean():
    project = sloads_io.load_project(_GA)
    assert consistency_warnings(project) == []


def test_taper_gt_1_fires():
    project = Project(name="t", geometry=GeometryInput(parametric=LayoutInput(
        wing_area_sqft=150.0, aspect_ratio=7.0, taper_ratio=1.4, fuselage_length=300.0)))
    assert "taper_gt_1" in _codes(project)


def test_taper_le_1_silent():
    project = Project(name="t", geometry=GeometryInput(parametric=LayoutInput(
        wing_area_sqft=150.0, aspect_ratio=7.0, taper_ratio=0.5, fuselage_length=300.0)))
    assert "taper_gt_1" not in _codes(project)


def test_nonpositive_area_fires():
    project = Project(name="t", geometry=GeometryInput(parametric=LayoutInput(
        wing_area_sqft=0.0, aspect_ratio=7.0, taper_ratio=0.5, fuselage_length=300.0)))
    assert "nonpositive_area" in _codes(project)


def test_le_te_ordering_fires_when_le_behind_te():
    # Leading edge aft of the trailing edge (X_LE > X_TE) -- inverted chord.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(100.0, 0.0), (110.0, 100.0)],
        trailing_edge=[(90.0, 0.0), (95.0, 100.0)])
    project = Project(name="t", geometry=GeometryInput(surfaces=[surf]))
    assert "le_te_ordering" in _codes(project, page="wing_geometry")


def test_le_te_ordering_silent_when_well_formed():
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(90.0, 0.0), (95.0, 100.0)],
        trailing_edge=[(120.0, 0.0), (118.0, 100.0)])
    project = Project(name="t", geometry=GeometryInput(surfaces=[surf]))
    assert "le_te_ordering" not in _codes(project)


def test_area_mismatch_fires():
    # WINGGEOM planform ~ (120 in chord * 400 in span)/144 = 333 ft^2, well away
    # from the 150 ft^2 claimed on Configuration & Layout.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(0.0, 0.0), (0.0, 200.0)],
        trailing_edge=[(120.0, 0.0), (120.0, 200.0)])
    project = Project(
        name="t",
        geometry=GeometryInput(
            parametric=LayoutInput(wing_area_sqft=150.0, aspect_ratio=7.0, fuselage_length=300.0),
            surfaces=[surf]))
    assert "area_mismatch" in _codes(project)


def test_area_match_silent():
    # Planform (120 in * 200 in half-span, symmetric)/144 -> match config area.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(0.0, 0.0), (0.0, 200.0)],
        trailing_edge=[(120.0, 0.0), (120.0, 200.0)])
    from sloads.modules.wing_geometry import surface_properties
    area_ft2 = next(v.value for v in surface_properties(surf).values
                    if v.label == "Total area") / 144.0
    project = Project(
        name="t",
        geometry=GeometryInput(
            parametric=LayoutInput(wing_area_sqft=area_ft2, aspect_ratio=7.0, fuselage_length=300.0),
            surfaces=[surf]))
    assert "area_mismatch" not in _codes(project)


def test_cg_outside_envelope_fires():
    project = sloads_io.load_project(_GA)
    # Push the loading CG far aft with a heavy tail-boom mass well behind any limit.
    project.weight.items.append(MassItem(
        name="ballast", weight_lb=5000.0, x=100000.0, y=0.0, z=0.0,
        ixx=0.0, iyy=0.0, izz=0.0, kind=MassItemKind.DISCRETIONARY))
    assert "cg_outside_envelope" in _codes(project, page="weight_cg_inertia")


def test_cg_check_skipped_without_envelope():
    project = sloads_io.load_project(_GA)
    project.weight.envelope = None  # no WTENV envelope -> check silently skipped
    assert "cg_outside_envelope" not in _codes(project)


def test_operational_target_infeasible_fires():
    # A target VNE above 0.9*VD (GA6 VD 212.5 -> cap 191.25) is infeasible and
    # surfaces on the Design Speeds page for the dashboard (M2-10).
    project = sloads_io.load_project(_GA)
    project.speeds.target_vne = 250.0  # needs VD >= 277.8, chosen VD 212.5
    assert "operational_target_infeasible" in _codes(project, page="structural_speeds")


def test_operational_target_feasible_silent():
    # A reachable target produces no warning (VNE 180 needs VD >= 200 <= 212.5).
    project = sloads_io.load_project(_GA)
    project.speeds.target_vne = 180.0
    assert "operational_target_infeasible" not in _codes(project)


def _project_with_sf(sf):
    """A project holding one critical condition and one wing case at ``sf``."""
    from sloads.models import (
        CriticalCondition,
        CriticalLoadSet,
        EnvelopeResult,
        LoadsResult,
        WingLoadResult,
    )

    return Project(
        name="sf",
        envelope=EnvelopeResult(critical=CriticalLoadSet(conditions=[
            CriticalCondition(component="htail", label="balancing", safety_factor=sf)])),
        loads=LoadsResult(wing_net=[WingLoadResult(case="PHAA", safety_factor=sf)]),
    )


def test_safety_factor_out_of_range_fires():
    # Defect M4-14: below 1.0 is unconservative-labelled-ULTIMATE, above 1.5 is
    # non-standard -- both flagged, one warning per case, on the Export page.
    for bad in (0.9, 2.0):
        warnings = [w for w in consistency_warnings(_project_with_sf(bad))
                    if w.code == "safety_factor_out_of_range"]
        assert len(warnings) == 2, bad          # the condition + the wing case
        assert {w.page for w in warnings} == {"export_report"}
        assert any("balancing" in w.message for w in warnings)
        assert any("PHAA" in w.message for w in warnings)


def test_safety_factor_legal_band_silent():
    # [1.0, 1.5] inclusive is the legal band (a case already at ultimate is 1.0).
    for good in (1.0, 1.25, 1.5):
        assert "safety_factor_out_of_range" not in _codes(_project_with_sf(good)), good


def test_safety_factor_valid_predicate():
    from sloads.validation import safety_factor_valid

    for v in (1.0, 1.25, 1.5):
        assert safety_factor_valid(v), v
    for v in (None, "1.25", True, float("nan"), float("inf"), 0.5, -1.5, 0.999, 1.6):
        assert not safety_factor_valid(v), v


# --------------------------------------------------------------------------- #
# M4-17c -- the WTENV forward CG limit read *at* a weight
# --------------------------------------------------------------------------- #
def test_wtenv_fwd_cg_limit_at_weight():
    """The forward structural CG limit interpolated at a weight (Appendix A p230).

    WTENV's forward limit is a two-point line: 72.643 in at the 2800 lb
    fwd-regardless weight and 77.490 in at the 3400 lb gross weight. The manual
    reads it **at the landing weight** -- 76.12 in at 3230 lb -- where
    ``wtenv_cg_limits`` returns the weight-agnostic hull (72.643 in), which pairing
    with the max landing weight was the M4-17c seed defect.
    """
    import math

    from sloads.validation import wtenv_cg_limits, wtenv_fwd_cg_limit_at_weight

    project = sloads_io.load_project(_GA)
    hull = wtenv_cg_limits(project)
    assert math.isclose(hull[0], 72.6431, rel_tol=1e-3), hull
    # The anchors, then the manual's printed landing-weight value (p230).
    assert math.isclose(wtenv_fwd_cg_limit_at_weight(project, 2800), 72.6431, rel_tol=1e-3)
    assert math.isclose(wtenv_fwd_cg_limit_at_weight(project, 3400), 77.4903, rel_tol=1e-3)
    assert math.isclose(wtenv_fwd_cg_limit_at_weight(project, 3230), 76.12, rel_tol=1e-3), \
        wtenv_fwd_cg_limit_at_weight(project, 3230)
    # Clamped, never extrapolated, outside the two anchor weights.
    assert math.isclose(wtenv_fwd_cg_limit_at_weight(project, 100), 72.6431, rel_tol=1e-3)
    assert math.isclose(wtenv_fwd_cg_limit_at_weight(project, 99999), 77.4903, rel_tol=1e-3)
    # No source -> None, so the caller blanks the cell rather than fabricating one.
    assert wtenv_fwd_cg_limit_at_weight(project, 0) is None
    assert wtenv_fwd_cg_limit_at_weight(Project(name="empty"), 3230) is None


# --------------------------------------------------------------------------- #
# M4-17d -- landing weight/CG hierarchy + post-compute reaction sanity
# --------------------------------------------------------------------------- #
def _ga_with_landing(**changes):
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    project.landing = replace(project.landing, **changes)
    return project


def test_landing_hierarchy_silent_on_ga_fixture():
    """Covered by test_ga_fixture_is_clean too; asserted here against the page tag."""
    assert _codes(sloads_io.load_project(_GA), page="landing_loads") == set()


def test_landing_gross_below_max_landing_fires():
    """GW < W deflates WR = GW/W below 1, under-predicting the braked-roll, side and
    supplementary-nose cases while the numbers still look plausible."""
    project = _ga_with_landing(gross_weight_lb=3000.0)   # below the 3230 lb landing weight
    assert "gross_ge_max_landing" in _codes(project, page="landing_loads")


def test_landing_light_case_over_max_landing_fires():
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    cases = list(project.landing.cg_cases)
    cases[2] = replace(cases[2], weight_lb=4000.0)       # light corner heavier than W
    project.landing.cg_cases = cases
    assert "landing_light_le_max" in _codes(project, page="landing_loads")


def test_landing_cg_ordering_fires_on_fwd_aft_swap():
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    aft, fwd, light = project.landing.cg_cases
    project.landing.cg_cases = [replace(aft, xcg=fwd.xcg), replace(fwd, xcg=aft.xcg), light]
    assert "landing_cg_ordering" in _codes(project, page="landing_loads")


def test_landing_cg_below_axle_fires_on_zero_waterline():
    """The M4-17c signature: a zero waterline puts the CG below the 59.6 in static
    main-axle waterline, which is geometrically impossible for a tricycle airplane."""
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    project.landing.cg_cases = [replace(c, zcg=0.0) for c in project.landing.cg_cases]
    assert "landing_cg_below_axle" in _codes(project, page="landing_loads")


def test_landing_cg_names_fires_on_non_canonical_names():
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    project.landing.cg_cases = [replace(c, name=f"case {i}")
                                for i, c in enumerate(project.landing.cg_cases)]
    assert "landing_cg_names" in _codes(project, page="landing_loads")


def test_landing_reaction_warnings_flag_the_zero_waterline_reactions():
    """Post-compute proof of the M4-17c defect: with zcg = 0 the GA-6 nose reactions
    go negative (-233..-2887 lb), which the old seed produced silently."""
    from dataclasses import replace

    from sloads.modules.landing import build_landing
    from sloads.validation import landing_reaction_warnings

    project = sloads_io.load_project(_GA)
    _, good = build_landing(project)
    assert landing_reaction_warnings(good) == []

    project.landing.cg_cases = [replace(c, zcg=0.0) for c in project.landing.cg_cases]
    _, bad = build_landing(project)
    codes = {w.code for w in landing_reaction_warnings(bad)}
    assert "landing_negative_vertical" in codes, codes
    assert any(c.vnp < 0 for c in bad), "expected the nonphysical negative nose reactions"


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
