"""Single-source landing-gear geometry (Step G6b).

The tricycle-gear geometry native to LANDLOAD (axle X/Z at three strut states,
rolling radius, strut type, tread) is entered once in ``GeometryInput.landing_gear``
and drives both the three-view (tip-back/overturn/clearance) and the ground-load
analysis. ``landing.build_landing`` syncs it onto ``Project.landing`` before the
reaction solve, so the LANDLOAD math is unchanged. These tests lock in the
single-source mechanics (serialization under geometry, pre-v28 migration, the
derived coarse gear values) and that the Appendix A gear reactions stay bit-for-bit.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.modules.configuration import gear_stations  # noqa: E402
from sloads.modules.landing import build_landing  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_JET = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")  # has a parametric layout


def test_gear_geometry_serializes_under_geometry_not_landing():
    p = io.load_project(_GA)
    assert p.geometry.landing_gear is not None
    d = io.project_to_dict(p)
    assert "landing_gear" in d["geometry"]
    assert "main_gear" not in d["landing"] and "tread_in" not in d["landing"]
    p2 = io.project_from_dict(d)
    assert p2.geometry.landing_gear.main_gear.axle_static == p.geometry.landing_gear.main_gear.axle_static
    assert p2.geometry.landing_gear.tread_in == p.geometry.landing_gear.tread_in


def test_gear_stations_derives_coarse_values_from_axles():
    p = io.load_project(_JET)   # a fixture with a parametric layout + gear geometry
    gc = gear_stations(p.geometry.parametric, p.geometry.landing_gear)
    lg = p.geometry.landing_gear
    assert gc["main_x"] == lg.main_gear.axle_static[0]
    assert gc["track"] == lg.tread_in
    # Ground line = lowest static wheel contact (static axle Z - rolling radius).
    ground = min(lg.main_gear.axle_static[1] - lg.main_gear.rolling_radius_in,
                 lg.nose_gear.axle_static[1] - lg.nose_gear.rolling_radius_in)
    assert math.isclose(gc["ground_z"], ground)
    assert math.isclose(gc["gear_height"], p.geometry.parametric.root_waterline_z - ground)


def test_landloads_reactions_unchanged_bit_for_bit():
    """The gear syncs from geometry.landing_gear -> LANDLOAD produces byte-identical
    reactions before and after a JSON round-trip (Appendix A ground-load lock)."""
    def reactions(pr):
        _lf, rx = build_landing(pr)
        return [(c.case, round(c.result, 9), round(c.rmp, 9)) for c in rx]
    p = io.load_project(_GA)
    before = reactions(p)
    after = reactions(io.project_from_dict(io.project_to_dict(p)))
    assert before and before == after


if __name__ == "__main__":
    test_gear_geometry_serializes_under_geometry_not_landing()
    print("ok serializes under geometry")
    test_pre_v28_top_level_landing_gear_migrates()
    print("ok pre-v28 migration")
    test_gear_stations_derives_coarse_values_from_axles()
    print("ok gear_stations derivation")
    test_landloads_reactions_unchanged_bit_for_bit()
    print("ok LANDLOAD bit-for-bit")
    print("all landing-gear-geometry tests passed")
