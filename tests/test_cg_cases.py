"""The one weight/CG case list and the two design weights (step 10 piece 2).

CLAUDE.md practice 3: a cross-cutting convention gets a single-source code owner
**plus a drift-guard test**. :mod:`sloads.cg_cases` is the owner; this is the
guard, and it pins the four claims the piece is made of:

1. **Every case says what it is for.** A case tagged for no analysis is an entry
   error, not a state (G-3c). Decision G-3b's neutrality guard -- the
   ``FLIGHT``-tagged set equals the pre-hop ``flight_loads.cg_cases``, per
   fixture -- lived here until #93 retired the v46 hop with the rest of the
   chain. It was re-proven at the cut against the pre-regeneration files (all six
   fixtures, flight and ground sets identical) and then removed with the hop it
   guarded; the examples are now post-hop, so the pre-hop list it read no longer
   exists to compare against.
2. **The role is the ordering contract, not the name.** LANDLOAD indexes its three
   loadings positionally and is oracle-locked to Appendix A p230; before G-3a the
   order was recovered by *matching names*, falling back to entry order with only
   a warning, so renaming a row silently reordered the reaction table.
3. **Both design weights have one owner.** In particular the removed
   ``landing.gross_weight_lb`` fell back to ``max(landing cg_cases)``, which is
   MLW rather than MTOW -- ``WR = 1.0``, understating cases 13-24 by ~5 %.
4. **G-5 burn-down reaches a landing weight by burning fuel, not by dropping a
   passenger**, and it cannot touch a flight case, which is what keeps the
   Appendix-A oracles still.
"""

import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.cg_cases import (
    FLIGHT_CASE_NAMES,
    cases_for,
    database_total,
    flight_cases,
    ground_cases,
    landing_role_cases,
    max_landing_weight,
    max_landing_weight_estimate,
    max_takeoff_weight,
    seed_flight_cases,
    seed_landing_cases,
)
from sloads.mass_distribution import derive_case_loadings
from sloads.models import (
    GROUND_CASE_ROLE_ORDER,
    AnalysisKind,
    CgCase,
    GroundCaseRole,
    MissingInputError,
    Project,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))
_GA = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


# --------------------------------------------------------------------------- #
# 1. Every case says what it is for
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_every_case_states_at_least_one_analysis(path):
    """G-3c: a case run for nothing is an entry error, not a state."""
    for case in io.load_project(path).weight.cg_cases:
        assert case.analyses, case.name


# --------------------------------------------------------------------------- #
# 2. The role is the ordering contract
# --------------------------------------------------------------------------- #
def test_the_roled_cases_come_back_in_role_order_whatever_the_entry_order():
    project = io.load_project(_GA)
    cases = project.weight.cg_cases
    project.weight.cg_cases = list(reversed(cases))
    assert [c.role for c in landing_role_cases(project)] == list(GROUND_CASE_ROLE_ORDER)


def test_no_roled_case_raises_a_missing_input_rather_than_returning_a_short_list():
    project = io.load_project(_GA)
    project.weight.cg_cases = [c for c in project.weight.cg_cases if c.role is None]
    with pytest.raises(MissingInputError):
        landing_role_cases(project)


def test_a_duplicated_role_raises_rather_than_picking_one():
    project = io.load_project(_GA)
    dup = next(c for c in project.weight.cg_cases
               if c.role == GroundCaseRole.FWD_LIGHT)
    project.weight.cg_cases = list(project.weight.cg_cases) + [dup]
    with pytest.raises(ValueError, match="fwd_light"):
        landing_role_cases(project)


def test_a_ground_case_without_a_role_is_never_fed_to_landload():
    """The tag is free to grow -- a ramp loading or a second fuel state is
    assembled and distributed, but LANDLOAD keeps its exact three."""
    project = io.load_project(_GA)
    extra = CgCase("ramp", 3400.0, 85.0, 93.0, {AnalysisKind.GROUND}, None)
    project.weight.cg_cases = list(project.weight.cg_cases) + [extra]
    assert extra in ground_cases(project)
    assert extra not in landing_role_cases(project)
    assert len(landing_role_cases(project)) == 3


def test_cases_for_filters_and_never_sorts():
    """Entry order is the FLIGHT contract -- the V-n case numbering is built from
    it, so a resolver that sorted would renumber every case id."""
    project = io.load_project(_GA)
    names = [c.name for c in project.weight.cg_cases if AnalysisKind.FLIGHT in c.analyses]
    assert [c.name for c in cases_for(project, AnalysisKind.FLIGHT)] == names


# --------------------------------------------------------------------------- #
# 3. One owner per design weight
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_mtow_agrees_with_every_representation_it_replaced(path):
    """G-14, measured 2026-08-14: five of the six representations agree on every
    shipped fixture, and the sixth -- the item-database total -- is an upper bound
    that legitimately does not. Pinning the agreement is what makes the migration's
    ``speeds.weight_lb`` seed safe."""
    project = io.load_project(path)
    mtow = max_takeoff_weight(project)
    assert project.weight.max_takeoff_weight_lb == mtow
    assert project.speeds.weight_lb == mtow
    if project.weight.envelope is not None:
        assert project.weight.envelope.gross_weight == mtow
    assert database_total(project) >= mtow - 1e-6, "the item sum is the ceiling"


def test_mtow_is_not_the_heaviest_landing_case():
    """The latent defect that left with ``landing.gross_weight_lb``: its
    ``max(cg_cases)`` fallback ran over the *landing* loadings, so it returned MLW
    and made ``WR = 1.0``, understating cases 13-24 by ~5 % on every fixture."""
    project = io.load_project(_GA)
    assert max_takeoff_weight(project) == 3400.0
    assert max(c.weight_lb for c in ground_cases(project)) == 3230.0


def test_an_unset_max_landing_weight_refuses_rather_than_estimating():
    """G-4: the GUI offers the estimate for acceptance; the calc never falls back
    to it."""
    project = io.load_project(_GA)
    project.weight.max_landing_weight_lb = 0.0
    assert max_landing_weight_estimate(project) > 0, "the estimate is available"
    with pytest.raises(MissingInputError):
        max_landing_weight(project)
    assert max_landing_weight(project, required=False) == 0.0


def test_the_landing_weight_estimate_excludes_consumable_mission_fuel():
    """G-4's floor is ``OEW + max payload + reserve fuel`` -- reserve fuel is
    ``MINIMUM`` kind and stays; mission fuel is ``DISCRETIONARY`` and consumable,
    so it is burned off before landing and must not count (G-5)."""
    project = io.load_project(_GA)
    assert max_landing_weight_estimate(project) == pytest.approx(2913.0)   # plan G-4
    for item in project.weight.items:
        item.consumable = False
    assert max_landing_weight_estimate(project) == pytest.approx(3322.0)   # +409 fuel


def test_the_estimate_is_none_without_an_item_database():
    assert max_landing_weight_estimate(Project(name="bare")) is None


# --------------------------------------------------------------------------- #
# 4. G-5 burn-down
# --------------------------------------------------------------------------- #
def test_burn_down_reaches_the_landing_weight_by_burning_fuel():
    """Measured on ga6 (plan decision G-5). Without burn-down the least-ballast
    subset search drops the **6th person** (x = 150, aft cabin) and keeps the full
    409 lb of fuel (x = 70) -- the right weight with the mass 80 in out of place,
    and on a wing-fuel airplane worse than out of place, because burning fuel
    removes wing inertia relief and dropping a passenger does not."""
    project = io.load_project(_GA)
    aft = next(c for c in ground_cases(project)
               if c.role == GroundCaseRole.AFT_MAX_LANDING)
    loading = derive_case_loadings(project, [aft])[0]

    assert loading.derivable
    assert loading.ballast is None, "burn-down needs no ballast"
    fuel = [it for it in loading.items if it.consumable]
    assert len(fuel) == 1
    assert fuel[0].weight_lb == pytest.approx(317.0, abs=0.5)   # plan G-5: 317 lb
    assert abs(loading.cg_x - aft.xcg) == pytest.approx(0.12, abs=0.02)


def test_burn_down_is_proportional_across_the_consumable_rows():
    """One fraction applied to every consumable row, so a tank layout survives --
    a real airplane burns to a schedule, and the loading's *distribution* is the
    whole reason this is not a weight subtraction."""
    project = io.load_project(_GA)
    fuel = next(it for it in project.weight.items if it.consumable)
    fuel.weight_lb /= 2
    project.weight.items.append(
        type(fuel)(name="Fuel 2", weight_lb=fuel.weight_lb, x=fuel.x, y=fuel.y,
                   z=fuel.z, kind=fuel.kind, component=fuel.component,
                   consumable=True))
    aft = next(c for c in ground_cases(project)
               if c.role == GroundCaseRole.AFT_MAX_LANDING)
    loading = derive_case_loadings(project, [aft])[0]
    burnt = [it.weight_lb for it in loading.items if it.consumable]
    assert len(burnt) == 2
    assert burnt[0] == pytest.approx(burnt[1]), "one tank was drained before the other"


@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_burn_down_cannot_touch_a_flight_case(path):
    """``consumable`` is gated on the target being ``GROUND`` (G-5). This is the
    acceptance test for the whole field: every flight case is unchanged to the
    pound, so the Appendix-A oracles cannot move."""
    project = io.load_project(path)
    before = [(ld.name, ld.weight_lb, ld.cg_x, ld.cg_z)
              for ld in derive_case_loadings(project)]
    for item in project.weight.items:
        item.consumable = True
    after = [(ld.name, ld.weight_lb, ld.cg_x, ld.cg_z)
             for ld in derive_case_loadings(project)]
    assert before == after


def test_ground_coverage_matches_what_the_plan_measured():
    """G-3/G-5, and what Pri 5 / **D-26** did to it: every fixture is now 3/3.

    Measured 2026-08-14 this was ga6 3/3, the RJ 2/3 and the rest 0/3, and the
    reason was never burn-down -- which fixes the *weight* half only -- but the
    landing CG targets themselves, entered 9-34 in forward of anything those
    databases could load. D-26 corrected the case data to the database and gave
    each ground case an entered loading, so what used to be skipped-and-recorded
    is now assembled. The recording path is unchanged and still guarded by
    ``test_every_condition_is_either_assembled_or_recorded``; this pin now says
    coverage is complete rather than partial, and goes red if a fixture edit
    quietly loses a ground loading again.
    """
    got = {}
    for path in _EXAMPLES:
        project = io.load_project(path)
        cases = ground_cases(project)
        if not cases:
            continue
        loadings = derive_case_loadings(project, cases)
        got[os.path.basename(path).split(".")[0]] = (
            sum(1 for ld in loadings if ld.derivable), len(loadings))
    assert got == {
        "ga6_normal": (3, 3),
        "concept_regional_jet": (3, 3),
        "cessna_210": (3, 3),
        "atr42_100": (3, 3),
        "dhc8_dash8": (3, 3),
    }, got


# --------------------------------------------------------------------------- #
# D-27 (2026-08-17): the flight cases ARE the WTENV limit points
# --------------------------------------------------------------------------- #
#: The four type fixtures whose CG cases are seeded from their WTENV envelope
#: (D-27). ``ga6_normal`` keeps Appendix A's own four (``CG1``..``CG4``) -- but
#: the seed reproduces them, which is the check that the seed *is* FLTLOADS'
#: definition; ``concept_heavy`` carries no envelope and one loading.
_SEEDED = ("cessna_210", "atr42_100", "dhc8_dash8", "concept_regional_jet")


@pytest.mark.parametrize("name", _SEEDED)
def test_the_fixture_flight_cases_are_the_wtenv_seed(name):
    """D-27 drift guard: a fixture's FLIGHT cases are exactly what
    ``seed_flight_cases`` produces from its own envelope and database -- name,
    weight, station and waterline -- so an edit to either the envelope or the
    items that is not followed by a re-seed goes red here."""
    project = io.load_project(os.path.join(_ROOT, "examples", f"{name}.project.json"))
    seeded, missing = seed_flight_cases(project)
    assert not missing, missing
    got = [(c.name, c.weight_lb, c.xcg, c.zcg) for c in flight_cases(project)]
    want = [(c.name, round(c.weight_lb, 2), round(c.xcg, 2), round(c.zcg, 2)) for c in seeded]
    assert [n for n, *_ in want] == list(FLIGHT_CASE_NAMES)
    for g, w in zip(got, want):
        assert g[0] == w[0]
        assert g[1:] == pytest.approx(w[1:], abs=0.011), (name, g, w)


@pytest.mark.parametrize("name", _SEEDED)
def test_the_fixture_ground_cases_are_the_landing_seed(name):
    """The GROUND half of the same guard: the three roled landing cases are
    ``seed_landing_cases``' own (MLW and the WTENV forward limit *at* MLW)."""
    project = io.load_project(os.path.join(_ROOT, "examples", f"{name}.project.json"))
    seeded, missing = seed_landing_cases(project)
    assert not missing, missing
    got = [(c.name, c.role, c.weight_lb, c.xcg, c.zcg) for c in ground_cases(project)]
    for g, w in zip(got, seeded):
        assert (g[0], g[1]) == (w.name, w.role)
        assert g[2:] == pytest.approx((w.weight_lb, w.xcg, w.zcg), abs=0.011), (name, g)
    assert len(got) == len(seeded) == 3


def test_the_seed_reproduces_appendix_a_s_four_points_on_ga6():
    """The seed is FLTLOADS.BAS's own prompt set: on the Appendix A airplane it
    lands on CG1..CG4 (Ref 1 Ch 3 p21: 3400 @ 85.1 / 77.49, 2800 @ 72.64,
    2063 @ 73.09) to the rounding of the printed stations. ga6 keeps its
    Appendix A names, so this is a reproduction, not a pin of the fixture."""
    project = io.load_project(_GA)
    seeded, missing = seed_flight_cases(project)
    assert not missing
    by_name = {c.name: c for c in seeded}
    want = {"aft gross": (3400, 85.1), "fwd gross": (3400, 77.49),
            "fwd regardless": (2800, 72.64), "min weight": (2063, 73.09)}
    for name, (w, x) in want.items():
        assert by_name[name].weight_lb == pytest.approx(w, rel=1e-3), name
        assert by_name[name].xcg == pytest.approx(x, abs=0.02), name


@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_every_fixture_case_sits_inside_its_wtenv_envelope(path):
    """D-27's aim, made structural: every CG case of every fixture with an
    envelope lies between the WTENV forward limit *at its weight* and the aft
    limit. ``concept_heavy`` has no envelope and is skipped, not passed."""
    from sloads.validation import wtenv_cg_limits, wtenv_fwd_cg_limit_at_weight

    project = io.load_project(path)
    limits = wtenv_cg_limits(project)
    if limits is None:
        pytest.skip("no WTENV envelope on this fixture")
    _, aft = limits
    # 0.05 in: the echo rounding of the seeded cases, and Appendix A's own
    # ``fwd light`` (2803 lb at the printed 72.64) sits 0.03 in ahead of the
    # forward line interpolated at 2803 rather than 2800 lb.
    for case in project.weight.cg_cases:
        fwd = wtenv_fwd_cg_limit_at_weight(project, case.weight_lb)
        assert fwd is not None
        assert fwd - 0.05 <= case.xcg <= aft + 0.05, (
            f"{os.path.basename(path)} {case.name}: {case.xcg} outside {fwd:.2f}..{aft:.2f}")


@pytest.mark.parametrize("path", _EXAMPLES, ids=lambda p: os.path.basename(p))
def test_every_fuselage_item_sits_inside_the_outline_and_the_check_has_teeth(path):
    """The three-view's claim (D-27): a fuselage-carried mass is inside the body
    it is carried by. Silent as shipped on every fixture with an outline, and
    the ``mass_item_outside_body`` warning fires the moment one is not."""
    from sloads.models import MassComponent
    from sloads.validation import consistency_warnings

    project = io.load_project(path)
    codes = [w.code for w in consistency_warnings(project)]
    assert "mass_item_outside_body" not in codes, os.path.basename(path)
    assert "cg_outside_envelope" not in codes, os.path.basename(path)
    if project.geometry is None or project.geometry.fuselage is None:
        pytest.skip("no fuselage outline on this fixture")
    item = next(it for it in project.weight.items if it.component == MassComponent.FUSELAGE)
    item.x = max(sec.x for sec in project.geometry.fuselage.sections) + 50.0
    assert "mass_item_outside_body" in [w.code for w in consistency_warnings(project)]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
