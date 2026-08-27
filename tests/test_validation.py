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
from sloads.models import AnalysisKind, GeometryInput, GroundCaseRole, MassComponent

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_RJ = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")
_HEAVY = os.path.join(_EXAMPLES, "concept_heavy.project.json")


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
    assert "le_te_ordering" in _codes(project, page="configuration_layout")


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
    # Once on each page that can act on it, never twice on one (#70). Design
    # Speeds is where the disagreement decides which number STRSPEED integrates,
    # so a warning that only reaches Configuration & Layout is a warning the
    # reader of the affected result never sees.
    from sloads.validation import PAGE_CONFIGURATION, PAGE_STRUCTURAL_SPEEDS

    pages = [w.page for w in consistency_warnings(project) if w.code == "area_mismatch"]
    assert sorted(pages) == sorted([PAGE_CONFIGURATION, PAGE_STRUCTURAL_SPEEDS])


def test_no_warning_is_raised_twice_for_one_page():
    """A page must not print the same sentence twice.

    The doubled ``area_mismatch`` (#70) was two identical entries returned from
    one check -- invisible to every code-level assertion in this file, and to
    the renderer, which prints what it is given. This is the general form:
    (code, page, message) is unique, across the shipped projects and across a
    project built to trip the checks rather than pass them.
    """
    import glob

    projects = [(os.path.basename(path), sloads_io.load_project(path))
                for path in sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json")))]
    projects.append(("a deliberately contradictory project", _contradictory()))
    for name, project in projects:
        seen = [(w.code, w.page, w.message) for w in consistency_warnings(project)]
        duplicates = {entry for entry in seen if seen.count(entry) > 1}
        assert not duplicates, (
            f"{name} raises the same warning more than once: "
            f"{sorted(c for c, _p, _m in duplicates)}")


def _contradictory():
    """A project that trips as many checks at once as one project can."""
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(0.0, 0.0), (0.0, 200.0)],
        trailing_edge=[(120.0, 0.0), (120.0, 200.0)])
    return Project(
        name="t",
        geometry=GeometryInput(
            parametric=LayoutInput(wing_area_sqft=150.0, aspect_ratio=7.0,
                                   taper_ratio=1.5, fuselage_length=300.0),
            surfaces=[surf]))


def test_area_match_silent():
    # Planform (120 in * 200 in half-span, symmetric)/144 -> match config area.
    surf = SurfaceInput(
        name="wing",
        leading_edge=[(0.0, 0.0), (0.0, 200.0)],
        trailing_edge=[(120.0, 0.0), (120.0, 200.0)])
    from sloads.modules.wing_geometry import surface_properties
    area_ft2 = next(v.value for v in surface_properties(surf).values
                    if v.key == "total_area") / 144.0
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
    assert "cg_outside_envelope" in _codes(project, page="weight_mass")


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
def _ga_with_ground_cases(fn):
    """The GA fixture with its three roled GROUND cases mapped through ``fn``.

    They live on the one shared list now (decision G-3b), so a test that wants to
    perturb a landing loading edits ``weight.cg_cases`` -- and must leave the
    FLIGHT-tagged cases alone, or it perturbs the flight analysis too.
    """
    from dataclasses import replace  # noqa: F401  (used by callers' lambdas)

    project = sloads_io.load_project(_GA)
    project.weight.cg_cases = [fn(c) if c.role is not None else c
                               for c in project.weight.cg_cases]
    return project


def test_landing_hierarchy_silent_on_ga_fixture():
    """Covered by test_ga_fixture_is_clean too; asserted here against the page tag."""
    assert _codes(sloads_io.load_project(_GA), page="landing_loads") == set()


def test_a_max_landing_case_that_disagrees_with_mlw_fires():
    """G-4: MLW is one number and a certified airplane-level limit, so a roled
    max-landing case at some other weight is an error, not a preference."""
    from dataclasses import replace

    project = _ga_with_ground_cases(
        lambda c: replace(c, weight_lb=3100.0)
        if c.role is not None and c.role.value.endswith("max_landing") else c)
    assert "landing_case_weight_is_mlw" in _codes(project, page="landing_loads")


def test_landing_light_case_over_max_landing_fires():
    from dataclasses import replace

    project = _ga_with_ground_cases(
        lambda c: replace(c, weight_lb=4000.0)      # light corner heavier than W
        if c.role is not None and c.role.value == "fwd_light" else c)
    assert "landing_light_le_max" in _codes(project, page="landing_loads")


def test_landing_cg_ordering_fires_on_fwd_aft_swap():
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    roled = {c.role: c for c in project.weight.cg_cases if c.role is not None}
    aft = roled[GroundCaseRole.AFT_MAX_LANDING]
    fwd = roled[GroundCaseRole.FWD_MAX_LANDING]
    swap = {aft.name: fwd.xcg, fwd.name: aft.xcg}
    project.weight.cg_cases = [replace(c, xcg=swap[c.name]) if c.name in swap else c
                               for c in project.weight.cg_cases]
    assert "landing_cg_ordering" in _codes(project, page="landing_loads")


def test_landing_cg_below_axle_fires_on_zero_waterline():
    """The M4-17c signature: a zero waterline puts the CG below the 59.6 in static
    main-axle waterline, which is geometrically impossible for a tricycle airplane."""
    from dataclasses import replace

    project = _ga_with_ground_cases(lambda c: replace(c, zcg=0.0))
    assert "landing_cg_below_axle" in _codes(project, page="landing_loads")


def test_a_role_on_a_case_that_is_not_a_ground_case_is_rejected():
    """G-3a: the role is LANDLOAD's ordering contract, so carried by a flight-only
    case it says the user meant one thing and the calc will do another."""
    from dataclasses import replace

    project = _ga_with_ground_cases(lambda c: replace(c, analyses={AnalysisKind.FLIGHT}))
    assert "cg_case_role_without_ground" in _codes(project, page="weight_mass")


def test_a_case_run_for_no_analysis_is_rejected():
    """G-3c: it disappears from every result while still occupying a row."""
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    project.weight.cg_cases = [replace(c, analyses=set()) if i == 0 else c
                               for i, c in enumerate(project.weight.cg_cases)]
    assert "cg_case_no_analysis" in _codes(project, page="weight_mass")


def test_an_entered_loading_that_does_not_produce_its_case_is_reported():
    """D-25a on the page the loading is edited on.

    The loading is authoritative, so the tool must never quietly bend it to the
    case's entered weight/CG -- what it does instead is say the two disagree,
    here as well as in the mass checks and the report.
    """
    project = sloads_io.load_project(_HEAVY)      # the fixture with an entered loading (D-27)
    case = next(c for c in project.weight.cg_cases if c.name == "CGmax")
    assert "cg_case_loading_echo" not in _codes(project)      # as shipped
    case.weight_lb += 500.0
    codes = _codes(project, page="weight_mass")
    assert "cg_case_loading_echo" in codes


def test_a_malformed_loading_is_reported_rather_than_raised_at_the_page():
    """An entry error in a loading is a *finding*, not a traceback, on the page
    the user is editing -- the calc path still raises (mass_distribution)."""
    from sloads.models import LoadingDefinition

    project = sloads_io.load_project(_RJ)
    case = next(c for c in project.weight.cg_cases if c.name == "fwd regardless")
    case.loading = LoadingDefinition(aboard=["No such item"])
    warnings = [w for w in consistency_warnings(project)
                if w.code == "cg_case_loading_invalid"]
    assert len(warnings) == 1
    assert "not a row of weight.items" in warnings[0].message


def test_the_design_weight_ordering_chain_fires_on_an_inverted_pair():
    """G-14: OEW <= MLW <= MTOW <= sum(items), one check where four were scattered."""
    project = sloads_io.load_project(_GA)
    project.weight.max_landing_weight_lb = project.weight.max_takeoff_weight_lb + 100.0
    assert "weight_order_chain" in _codes(project, page="weight_mass")


def test_the_mlw_floor_fires_on_the_regional_jet_and_no_other_fixture():
    """G-4, measured 2026-08-14: the RJ cannot land at MLW (31,000) with full
    payload and reserve fuel (31,360). That is a real finding about that fixture,
    and it is why the estimate is a floor rather than a prediction."""
    import glob

    fired = set()
    for path in sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json"))):
        if "mlw_below_landing_estimate" in _codes(sloads_io.load_project(path)):
            fired.add(os.path.basename(path))
    assert fired == {"concept_regional_jet.project.json"}, fired


def test_no_shipped_fixture_disagrees_about_who_carries_the_gear():
    """G-2 guard 1, clear on every fixture since 2026-08-15.

    The Dash 8 was the one that fired: its main gear sits in wing-mounted
    nacelles, and both mass models now say so -- the item row is tagged
    ``wing`` and WINGINER's ``concentrated`` carries the 600 lb/side leg, so
    the same structure carries the load *and* the weight.
    """
    import glob

    fired = set()
    for path in sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json"))):
        if "gear_carrier_mass_disagrees" in _codes(sloads_io.load_project(path)):
            fired.add(os.path.basename(path))
    assert fired == set(), fired


def test_the_gear_carrier_mass_guard_still_fires_on_a_mistagged_leg():
    """The guard is kept honest now that no fixture trips it: put the Dash 8's
    gear mass back on the fuselage and it must be named again."""
    project = sloads_io.load_project(os.path.join(_EXAMPLES, "dhc8_dash8.project.json"))
    gear = next(it for it in project.weight.items if it.name == "Main gear")
    assert gear.component is MassComponent.WING
    gear.component = MassComponent.FUSELAGE
    assert "gear_carrier_mass_disagrees" in _codes(project, page="weight_mass")


# --------------------------------------------------------------------------- #
# Wing-tank fuel separability (design note 29): the tie as a validator
# --------------------------------------------------------------------------- #
def test_the_wing_mass_tie_is_closed_on_every_shipped_fixture():
    """WF-4: ``wing_mass_tie_open`` fires on none of the six -- since the three
    fuel-in-wing fixtures carry ``wing_fraction`` on their fuel row (WF-5)."""
    import glob

    fired = set()
    for path in sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json"))):
        if "wing_mass_tie_open" in _codes(sloads_io.load_project(path)):
            fired.add(os.path.basename(path))
    assert fired == set(), fired


def test_the_wing_mass_tie_validator_names_the_pounds_and_the_remedy():
    """Strip the ATR's fraction: 3,800 lb of wing fuel ride the fuselage beam
    again, and the warning says so on the Weight & CG page."""
    project = sloads_io.load_project(os.path.join(_EXAMPLES, "atr42_100.project.json"))
    fuel = next(it for it in project.weight.items if it.name == "Fuel to gross")
    fuel.wing_fraction = 0.0
    warnings = [w for w in consistency_warnings(project) if w.code == "wing_mass_tie_open"]
    assert len(warnings) == 1
    assert warnings[0].page == "weight_mass"
    assert "3,800 lb" in warnings[0].message
    assert "wing_fraction" in warnings[0].message


def test_the_wing_mass_tie_validator_reads_the_other_sign_too():
    """The item database showing *more* wing than WINGINER hangs is the other
    entry error, and it is named as such rather than as missing fuel."""
    project = sloads_io.load_project(os.path.join(_EXAMPLES, "atr42_100.project.json"))
    fuel = next(it for it in project.weight.items if it.name == "Fuel to gross")
    fuel.wing_fraction = 1.0
    (w,) = [w for w in consistency_warnings(project) if w.code == "wing_mass_tie_open"]
    assert "more on the wing than WINGINER" in w.message


def test_wing_fraction_entry_rules():
    """WF-2: outside [0, 1] and non-zero on a WING row are both named."""
    project = sloads_io.load_project(os.path.join(_EXAMPLES, "atr42_100.project.json"))
    fuel = next(it for it in project.weight.items if it.name == "Fuel to gross")
    wing = next(it for it in project.weight.items if it.name == "Wing")
    fuel.wing_fraction = 1.2
    wing.wing_fraction = 0.3
    codes = _codes(project, page="weight_mass")
    assert "wing_fraction_out_of_range" in codes
    assert "wing_fraction_on_wing_row" in codes


def test_an_unstated_gear_carrier_is_flagged():
    """G-2: body-carried and wing-carried gear are different load paths, so there
    is no default to fall back to."""
    from dataclasses import replace

    project = sloads_io.load_project(_GA)
    lg = project.geometry.landing_gear
    project.geometry.landing_gear = replace(
        lg, main_gear=replace(lg.main_gear, carrier=None))
    assert "gear_carrier_unset" in _codes(project, page="configuration_layout")


def test_landing_reaction_warnings_flag_the_zero_waterline_reactions():
    """Post-compute proof of the M4-17c defect: with zcg = 0 the GA-6 nose reactions
    go negative (-233..-2887 lb), which the old seed produced silently."""
    from dataclasses import replace

    from sloads.modules.landing import build_landing
    from sloads.validation import landing_reaction_warnings

    project = sloads_io.load_project(_GA)
    _, good = build_landing(project)
    assert landing_reaction_warnings(good) == []

    bad_project = _ga_with_ground_cases(lambda c: replace(c, zcg=0.0))
    _, bad = build_landing(bad_project)
    codes = {w.code for w in landing_reaction_warnings(bad)}
    assert "landing_negative_vertical" in codes, codes
    assert any(c.vnp < 0 for c in bad), "expected the nonphysical negative nose reactions"


def test_flap_slipstream_warns_when_the_band_is_entered_with_no_engine():
    """#83 (C210-40): AF/BLPROP entered, no engine record -> the 23.457(b) case is
    skipped and the flap is sized on the gust-combined load alone. Since #85 that
    is a missing *delivered* case, not just an unprinted factor."""
    project = sloads_io.load_project(_GA)
    assert project.flap_loads.nacelle_frontal_area_sqft > 0, "fixture must enter AF"
    assert "flap_slipstream_skipped" not in _codes(project), "engine present -> silent"

    project.engines = []
    codes = _codes(project, page="flap_loads")
    assert "flap_slipstream_skipped" in codes, codes
    message = next(w.message for w in consistency_warnings(project)
                   if w.code == "flap_slipstream_skipped")
    assert "Engine Mount Loads" in message, "the warning must name where to fix it"


def test_flap_slipstream_warning_fires_exactly_when_the_module_skips_the_term():
    """The predicate and ``flap.slipstream_is_available`` are the same condition.

    A second copy of ``maxhp > 0 and pdia_in > 0`` in ``validation`` could drift
    from the one in ``flap_loads`` and warn about a term that was computed (or stay
    silent about one that was not). This ties them together over the partial
    records -- power without a propeller, and a propeller without power -- which
    are the cases a hand-written copy gets wrong."""
    from dataclasses import replace as _replace

    from sloads.modules.flap import _compute, slipstream_is_available

    base = sloads_io.load_project(_GA)
    eng = base.engines[0]
    variants = {
        "complete": [eng],
        "no engine record": [],
        "power, no propeller": [_replace(eng, prop_diameter_in=0.0)],
        "propeller, no power": [_replace(eng, takeoff_hp=None, max_cont_hp=None)],
    }
    for name, engines in variants.items():
        project = sloads_io.load_project(_GA)
        project.engines = list(engines)
        available = slipstream_is_available(project)
        computed = _compute(project).slipstream_factor > 0
        warned = "flap_slipstream_skipped" in _codes(project)
        assert available == computed, f"{name}: predicate disagrees with the module"
        assert warned != computed, f"{name}: warned={warned} but computed={computed}"


def test_flap_slipstream_is_silent_when_the_band_was_never_entered():
    """A jet leaves AF/BLPROP at zero and must stay silent.

    ``EngineType`` has no jet member, so ``concept_regional_jet``'s turbofans are
    stored as TURBOPROP with a zero propeller diameter -- indistinguishable from an
    unentered piston record by type alone. The entered band geometry is what
    separates them, and it is why this check keys on AF/BLPROP rather than on the
    engine list (#83)."""
    jet = sloads_io.load_project(os.path.join(_EXAMPLES, "concept_regional_jet.project.json"))
    assert jet.flap_loads is not None and jet.flap_loads.flap_area_one_side_sqft > 0
    assert jet.flap_loads.nacelle_frontal_area_sqft == 0
    assert "flap_slipstream_skipped" not in _codes(jet)

    stripped = sloads_io.load_project(_GA)
    stripped.engines = []
    stripped.flap_loads.nacelle_frontal_area_sqft = 0.0
    stripped.flap_loads.engine_butt_line_in = 0.0
    assert "flap_slipstream_skipped" not in _codes(stripped)


def test_every_warning_targets_a_real_page():
    """Rule-3 drift guard: every ``page`` tag is a ``workflow.STEPS`` key (#82).

    ``workflow.py`` is the nav SSOT, so a tag naming anything else names a page
    no GUI has, and the warning is dark wherever it is not propped up by a
    hand-typed literal. Two tags were exactly that until #82 --
    ``weight_cg_inertia`` (the weights page has been ``weight_mass`` since Step
    G3) and ``wing_geometry`` (merged into ``configuration_layout`` at Step G1)
    -- covering 19 checks, 14 of them the weights group. This asserts against
    *every* tag the module can emit, not the ones one fixture happens to trip,
    so a new check with a typo'd page fails here rather than rendering nowhere.
    """
    from sloads import validation
    from sloads import workflow as wf

    keys = {s.key for s in wf.STEPS}
    tagged = {name: value for name, value in vars(validation).items()
              if name.startswith("PAGE_") and isinstance(value, str)}
    assert tagged, "no PAGE_* tags found -- has the constant naming changed?"
    bad = {n: v for n, v in tagged.items() if v not in keys}
    assert not bad, f"page tags that are not workflow step keys: {bad}"

    # ...and the tags the live checks actually emit, across every fixture, so a
    # page string written inline instead of through a PAGE_* constant is caught
    # too.
    emitted = set()
    for name in ("ga6_normal", "concept_regional_jet", "concept_heavy",
                 "atr42_100"):
        project = sloads_io.load_project(
            os.path.join(_EXAMPLES, f"{name}.project.json"))
        emitted |= {w.page for w in consistency_warnings(project)}
    assert emitted <= keys, f"emitted page tags outside workflow: {emitted - keys}"


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
