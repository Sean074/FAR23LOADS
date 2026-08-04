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
    carry_through,
    fuselage_summary,
    sync_geometry_derived,
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


def test_sync_fills_derived_slices_from_geometry():
    p = io.load_project(_GA)
    wr = wing_reference(p, "wing")
    # The derived copies on every consuming slice match the single source.
    assert math.isclose(p.flight_loads.mac, wr.mac)
    assert math.isclose(p.flight_loads.wing_area_sqft, wr.s_sqft)
    assert math.isclose(p.flight_loads.xw, wr.xw)
    assert math.isclose(p.flight_loads.zw, wr.zw)
    assert math.isclose(p.wing_mass.dihedral_deg, wr.dihedral_deg)
    assert math.isclose(p.wing_mass.wrp_waterline, wr.wrp_waterline)


def test_wing_scalars_not_persisted_and_round_trip_is_noop():
    """Acceptance: no wing geometric quantity is stored as an independently editable
    copy; the serialized dict is byte-stable across save->reload."""
    p = io.load_project(_GA)
    d1 = io.project_to_dict(p)
    for key in ("mac", "wing_area_sqft", "xw", "zw"):
        assert key not in d1["flight_loads"]
    for key in ("dihedral_deg", "wrp_waterline"):
        assert key not in d1["wing_mass"]
    assert "wing_area_sqft" not in d1.get("landing", {})
    # Reload -> re-serialize is a no-op.
    d2 = io.project_to_dict(io.project_from_dict(d1))
    assert d1 == d2


def test_no_geometry_leaves_explicit_slice_values_untouched():
    """The STRSPEED fallback: a directly-constructed project with no wing surface
    keeps whatever the slice carries (sync is a no-op) -- so bare unit tests that set
    fl.xw/zw or wm.dihedral directly still work."""
    p = Project(name="bare",
                flight_loads=FlightLoadsInput(mac=1.0, wing_area_sqft=2.0, xw=3.0, zw=4.0),
                wing_mass=WingMassInput(dihedral_deg=5.0, wrp_waterline=6.0),
                landing=LandingInput(wing_area_sqft=7.0))
    sync_geometry_derived(p)
    assert (p.flight_loads.mac, p.flight_loads.xw, p.flight_loads.zw) == (1.0, 3.0, 4.0)
    assert (p.wing_mass.dihedral_deg, p.wing_mass.wrp_waterline) == (5.0, 6.0)
    assert p.landing.wing_area_sqft == 7.0


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
