"""Single-source geometry + power derivations (Step M2-6).

The wing scalars ``FlightLoadsInput.mac``/``wing_area_sqft``/``xw``/``zw``,
``WingMassInput.dihedral_deg``/``wrp_waterline`` and ``LandingInput.wing_area_sqft``
are derived from ``Project.geometry``; the fuselage ``LayoutInput`` length/width/height
are a derived summary of the ``GeometryInput.fuselage`` outline; and the weight-estimate
``max_continuous_hp`` is single-sourced from the engine list. These tests lock in the
derivation, the no-persistence/no-op-round-trip acceptance, and the no-geometry fallback.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import Project, io  # noqa: E402
from sloads.constants import DEFAULT_FRONT_SPAR_PCT, DEFAULT_REAR_SPAR_PCT  # noqa: E402
from sloads.derived_geometry import (  # noqa: E402
    SOB_ENTERED,
    SOB_HALF_WIDTH,
    carry_through,
    fuselage_summary,
    sob_station,
    require_wing_reference,
    sync_geometry_derived,
    wing_plane,
    wing_reference,
)
from sloads.models import (  # noqa: E402
    EngineInput,
    FlightLoadsInput,
    FuselageOutline,
    FuselageSection,
    GeometryInput,
    LandingInput,
    SurfaceInput,
    WeightEstimationInput,
    WeightInput,
    WingMassInput,
)
from sloads.modules.weight_estimate import resolve_max_continuous_hp  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_HEAVY = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def test_wing_reference_derives_from_ga6_geometry():
    """Appendix A wing: MAC 69.246, XLEMAC 63.641; XW = XLEMAC + 0.25*MAC and
    ZW = wrp + Y_MAC*tan(dihedral) (78.5 + Y_MAC*tan(6 deg) ~= 87.73)."""
    wr = wing_reference(io.load_project(_GA), "wing")
    assert wr is not None
    assert math.isclose(wr.mac, 69.246, rel_tol=1e-3)
    assert math.isclose(wr.s_sqft, 184.125, rel_tol=1e-3)
    assert math.isclose(wr.xw, 80.953, rel_tol=1e-3)
    assert math.isclose(wr.zw, 87.734, rel_tol=1e-3)
    assert math.isclose(wr.dihedral_deg, 6.0)
    assert math.isclose(wr.wrp_waterline, 78.5)


def test_every_wing_resolver_answers_from_the_one_source():
    """Note 33 (DS-2), replacing "sync fills the derived slices".

    There are no derived slice copies left to fill: the scalars that used to be
    written onto ``flight_loads`` and ``wing_mass`` are read through the
    resolvers instead. What is worth asserting is that the resolvers are views of
    one computation rather than three re-derivations that could drift — which is
    the property the copies never had.
    """
    p = io.load_project(_GA)
    wr = wing_reference(p, "wing")
    assert require_wing_reference(p, "wing") == wr
    assert wing_plane(p, "wing") == (wr.wrp_waterline, wr.dihedral_deg)
    # And the slices genuinely no longer carry them.
    for name in ("mac", "wing_area_sqft", "xw", "zw"):
        assert not hasattr(p.flight_loads, name)
    for name in ("dihedral_deg", "wrp_waterline"):
        assert not hasattr(p.wing_mass, name)
    assert not hasattr(p.landing, "wing_area_sqft")
    for name in ("main_gear", "nose_gear", "tread_in"):
        assert not hasattr(p.landing, name)


def test_wing_scalars_not_persisted_and_round_trip_is_noop():
    """Acceptance: no wing geometric quantity is stored as an independently editable
    copy; the serialized dict is byte-stable across save->reload."""
    p = io.load_project(_GA)
    d1 = io.project_to_dict(p)
    for key in ("mac", "wing_area_sqft", "xw", "zw"):
        assert key not in d1["flight_loads"]   # note 33: not fields at all any more
    for key in ("dihedral_deg", "wrp_waterline"):
        assert key not in d1["wing_mass"]   # note 33: not fields at all any more
    assert "wing_area_sqft" not in d1.get("landing", {})
    # Reload -> re-serialize is a no-op.
    d2 = io.project_to_dict(io.project_from_dict(d1))
    assert d1 == d2


def test_no_geometry_leaves_explicit_slice_values_untouched():
    """The STRSPEED fallback: a directly-constructed project with no wing surface
    keeps whatever the slice carries (sync is a no-op) -- so bare unit tests that set
    fl.xw/zw or wm.dihedral directly still work."""
    p = Project(name="bare",
                flight_loads=FlightLoadsInput(),
                wing_mass=WingMassInput(),
                landing=LandingInput())
    sync_geometry_derived(p)
    # The wing plane has no slice copy to keep (note 33, DS-1/DS-3): with no
    # parametric wing it degrades to the centreline plane, which is what the
    # removed fields defaulted to -- an absent plane, not a remembered one.
    assert wing_plane(p, "wing") == (0.0, 0.0)


def test_fuselage_summary_derives_from_outline():
    outline = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=0.0, height=0.0),
        FuselageSection(x=120.0, width=48.0, height=52.0),
        FuselageSection(x=300.0, width=6.0, height=9.0),
    ])
    assert fuselage_summary(outline) == (300.0, 48.0, 52.0)
    assert fuselage_summary(None) is None
    assert fuselage_summary(FuselageOutline(sections=[])) is None


# --------------------------------------------------------------------------- #
# Wing carry-through (Ref 1 Ch 15 p103 fuselage moment closure, M4-1)
# --------------------------------------------------------------------------- #
def _wing_project(front=None, rear=None, *, root_le=45.0, root_te=146.0):
    """A minimal project whose wing root chord runs ``root_le`` -> ``root_te``."""
    wing = SurfaceInput(name="wing",
                        leading_edge=[(root_le, 0.0), (root_le + 20.0, 100.0)],
                        trailing_edge=[(root_te, 0.0), (root_te + 5.0, 100.0)],
                        front_spar_pct=front, rear_spar_pct=rear)
    return Project(name="ct", geometry=GeometryInput(surfaces=[wing]))


def test_carry_through_from_entered_spar_fractions():
    """x = x_LE(root) + pct * c_root, off the inboard-most polyline points."""
    ct = carry_through(_wing_project(0.20, 0.60))          # c_root = 101 in
    assert ct is not None and not ct.assumed
    assert math.isclose(ct.x_f, 45.0 + 0.20 * 101.0)       # 65.2
    assert math.isclose(ct.x_r, 45.0 + 0.60 * 101.0)       # 105.6
    assert math.isclose(ct.d, ct.x_r - ct.x_f)
    assert (ct.front_pct, ct.rear_pct) == (0.20, 0.60)


def test_carry_through_defaults_are_flagged_assumed():
    """Unset fractions take the module defaults and flag the result -- an assumed
    spar location must never be reported as entered input (M4-1 decision 2)."""
    ct = carry_through(_wing_project())
    assert ct is not None and ct.assumed
    assert (ct.front_pct, ct.rear_pct) == (DEFAULT_FRONT_SPAR_PCT, DEFAULT_REAR_SPAR_PCT)
    assert math.isclose(ct.x_f, 45.0 + DEFAULT_FRONT_SPAR_PCT * 101.0)
    # One entered, one absent is still 'assumed' -- the pair is only as good as
    # its weaker half.
    assert carry_through(_wing_project(front=0.18)).assumed
    assert carry_through(_wing_project(rear=0.62)).assumed


def test_carry_through_none_when_underivable():
    """No geometry / no wing / degenerate root chord / inverted spars -> None, so
    body_loads takes its flagged whole-body fallback rather than a bogus x_f/x_r."""
    assert carry_through(Project(name="bare")) is None
    assert carry_through(_wing_project(), "no_such_surface") is None
    assert carry_through(_wing_project(root_te=45.0)) is None        # c_root = 0
    assert carry_through(_wing_project(root_te=20.0)) is None        # c_root < 0
    assert carry_through(_wing_project(0.60, 0.20)) is None          # x_r <= x_f
    empty = Project(name="e", geometry=GeometryInput(
        surfaces=[SurfaceInput(name="wing", leading_edge=[], trailing_edge=[])]))
    assert carry_through(empty) is None


def test_carry_through_on_ga6_example():
    """The shipped Appendix A wing resolves on the primary path (assumed spars)."""
    ct = carry_through(io.load_project(_GA))
    assert ct is not None and ct.assumed and ct.d > 0.0


def test_spar_fractions_round_trip_and_default_to_none():
    """A saved project keeps 'not entered' distinct from an entered number, and an
    older file (no keys) loads as None -- the lenient v34 -> v35 migration."""
    p = _wing_project(0.18, 0.62)
    d = io.project_to_dict(p)
    surf = d["geometry"]["surfaces"][0]
    assert (surf["front_spar_pct"], surf["rear_spar_pct"]) == (0.18, 0.62)
    back = io.project_from_dict(d).geometry.by_name("wing")
    assert (back.front_spar_pct, back.rear_spar_pct) == (0.18, 0.62)
    # v34 file: the keys are absent entirely.
    del surf["front_spar_pct"], surf["rear_spar_pct"]
    legacy = io.project_from_dict(d).geometry.by_name("wing")
    assert legacy.front_spar_pct is None and legacy.rear_spar_pct is None
    assert carry_through(io.project_from_dict(d)).assumed


# --------------------------------------------------------------------------- #
# Side-of-body station (step 13, decision BM-1)
# --------------------------------------------------------------------------- #
def test_sob_station_entered_wins_and_is_not_assumed():
    p = _wing_project()
    p.geometry.by_name("wing").sob_y_in = 40.0
    p.geometry.fuselage = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=10.0, height=10.0),
        FuselageSection(x=100.0, width=96.0, height=90.0),
        FuselageSection(x=300.0, width=8.0, height=9.0)])
    sync_geometry_derived(p)
    sob = sob_station(p)
    assert sob is not None and not sob.assumed
    assert sob.y == 40.0 and sob.basis == SOB_ENTERED


def test_sob_station_falls_back_to_half_the_width_marked_assumed():
    p = _wing_project()
    p.geometry.fuselage = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=10.0, height=10.0),
        FuselageSection(x=100.0, width=96.0, height=90.0),
        FuselageSection(x=300.0, width=8.0, height=9.0)])
    sob = sob_station(p)          # works un-synced too (summary fallback)
    assert sob is not None and sob.assumed
    assert math.isclose(sob.y, 48.0)
    assert sob.basis == SOB_HALF_WIDTH and "ASSUMED" in sob.note


def test_sob_station_is_none_without_a_body_and_never_the_inboard_rib():
    """BM-1's negative half: no butt line and no body -> None, and the WINGINER
    mass-panel start must never be substituted -- ``inboard_rib_y`` is a mass
    model quantity (BL 40 sits well inboard of the RJ's 52.5 in half-body)."""
    p = _wing_project()
    p.wing_mass = WingMassInput(inboard_rib_y=23.0)
    assert sob_station(p) is None
    assert sob_station(Project(name="bare")) is None
    # ``concept_heavy`` ships no fuselage data: its decks must not invent a
    # side of body. (``ga6_normal`` carried none until the Pri 1 fixture-data
    # pass, 2026-08-17, gave it the Appendix A body outline -- width 3.833 ft,
    # length 26.522 ft, height from the 17.231 sq ft frontal area as an ellipse
    # -- so it now resolves the assumed half-width like every other fixture.)
    assert sob_station(io.load_project(_HEAVY)) is None
    ga = sob_station(io.load_project(_GA))
    assert ga is not None and ga.assumed and math.isclose(ga.y, 23.0)


def test_sob_y_in_round_trips_and_defaults_to_none():
    p = _wing_project()
    p.geometry.by_name("wing").sob_y_in = 40.0
    d = io.project_to_dict(p)
    surf = d["geometry"]["surfaces"][0]
    assert surf["sob_y_in"] == 40.0
    assert io.project_from_dict(d).geometry.by_name("wing").sob_y_in == 40.0
    del surf["sob_y_in"]          # pre-v51 file: the key is absent entirely
    assert io.project_from_dict(d).geometry.by_name("wing").sob_y_in is None


def _project_with_engines(hps, *, estimate_total, override):
    engines = [EngineInput(max_cont_hp=hp) for hp in hps]
    est = WeightEstimationInput(max_continuous_hp=estimate_total,
                                override_max_continuous_hp=override, engines=len(hps))
    return Project(name="p", engines=engines, weight=WeightInput(estimation=est))


def test_power_single_sourced_from_engine_list():
    # Off: the engine-list total is used, not the (drifted) stored estimate total.
    p = _project_with_engines([270.0, 270.0], estimate_total=999.0, override=False)
    assert resolve_max_continuous_hp(p) == 540.0
    # On: the stored override total wins.
    p = _project_with_engines([270.0, 270.0], estimate_total=600.0, override=True)
    assert resolve_max_continuous_hp(p) == 600.0
    # Fallback: no engine carries a rating -> the stored total is used.
    p = _project_with_engines([None, None], estimate_total=480.0, override=False)
    assert resolve_max_continuous_hp(p) == 480.0


# --- note 33 gate DG-3: one place resolves the wing area ---------------------- #


def test_no_module_integrates_the_wing_planform_behind_the_resolvers_back():
    """Gate DG-3. The defect note 33 §2.1 found had no guard, and could not have
    one while each module wrote its own precedence.

    ``landing._wing_area`` preferred its slice copy and fell back to geometry;
    ``structural_speeds._wing_area_sqft`` preferred geometry and fell back to its
    slice copy -- opposite orders for one quantity, invisible only because
    ``sync_geometry_derived`` overwrote the landing copy before the module read
    it. This asserts the shape that keeps the divergence from coming back: the
    strip integral is performed by its **producer** and read by its **owner**,
    and nowhere else.

    Two accessors were allowlisted here until #70 -- ``landing._wing_area`` and
    ``structural_speeds._wing_area_sqft`` -- on the grounds that each keeps its
    own precedence. Their precedence is a policy (LGFACTOR refuses when there is
    no planform, STRSPEED falls back to a typed field); the integral underneath
    it is not, and leaving it copied is what let ``validation`` grow a third
    version and the oracle GUI display a fourth number entirely. Policy stays
    with the caller; the arithmetic has one home. The sweep also covers all of
    ``sloads/`` rather than ``sloads/modules/`` alone -- ``validation.py`` sat
    outside the old scan and was never checked.
    """
    import ast
    import glob

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sloads")
    allowed = {"wing_geometry.py", "derived_geometry.py"}
    offenders = []
    for path in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):
        if os.path.basename(path) in allowed:
            continue
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "total_area":
                offenders.append(f"{os.path.relpath(path, root)}:{node.lineno}")
    assert not offenders, (
        "a module integrates the wing planform itself rather than reading the one "
        f"resolver -- that is how the two-precedences defect started: {offenders}"
    )


def test_the_landing_and_speeds_wing_areas_agree_on_every_fixture():
    """DG-3's numeric half: the two modules that keep their own accessor return
    the same area. Before note 33 they could not, by construction."""
    import glob

    from sloads.modules.landing import _wing_area
    from sloads.modules.structural_speeds import _wing_area_sqft

    checked = 0
    for f in sorted(glob.glob(os.path.join(os.path.dirname(_GA), "*.json"))):
        p = io.load_project(f)
        if p.landing is None or p.speeds is None:
            continue
        assert math.isclose(_wing_area(p), _wing_area_sqft(p, p.speeds),
                            rel_tol=1e-12), f
        checked += 1
    assert checked, "no fixture carried both slices -- the check proved nothing"
