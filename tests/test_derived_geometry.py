"""Single-source geometry + power derivations (Step M2-6).

The wing scalars ``FlightLoadsInput.mac``/``wing_area_sqft``/``xw``/``zw``,
``WingMassInput.dihedral_deg``/``wrp_waterline`` and ``LandingInput.wing_area_sqft``
are derived from ``Project.geometry``; the fuselage ``LayoutInput`` length/width/height
are a derived summary of the ``GeometryInput.fuselage`` outline; and the weight-estimate
``max_continuous_hp`` is single-sourced from the engine list. These tests lock in the
derivation, the no-persistence/no-op-round-trip acceptance, and the no-geometry fallback.
"""

import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, io  # noqa: E402
from farloads.derived_geometry import (  # noqa: E402
    fuselage_summary,
    sync_geometry_derived,
    wing_reference,
)
from farloads.models import (  # noqa: E402
    EngineInput,
    FlightLoadsInput,
    FuselageOutline,
    FuselageSection,
    LandingInput,
    WeightEstimationInput,
    WeightInput,
    WingMassInput,
)
from farloads.modules.weight_estimate import resolve_max_continuous_hp  # noqa: E402

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


def test_every_example_round_trips_with_no_change():
    """Every shipped example is a save->reload no-op (M2-6 / seeds M2-7)."""
    for f in sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json"))):
        d1 = io.project_to_dict(io.load_project(f))
        d2 = io.project_to_dict(io.project_from_dict(d1))
        assert d1 == d2, f


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
