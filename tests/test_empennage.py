"""Single-source empennage geometry (Step G6).

The horizontal-/vertical-tail + elevator/rudder geometry is entered once on the
Geometry page and stored in ``GeometryInput.empennage`` (``htail``/``vtail`` = the
analysis-native ``TailLoadsInput``/``VTailLoadsInput``). ``Project.tail_loads`` /
``.vtail_loads`` are properties proxying to it, so the SELECT/TAILDIST/BALLOADS/
ONENGOUT calc reads it unchanged. These tests lock in the single-source mechanics
(property proxy, serialization, pre-v27 migration) and that the derived slices keep
the Appendix A SELECT tail loads **bit-for-bit** (the calc is untouched).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import (  # noqa: E402
    Project,
    TailLoadsInput,
    VTailLoadsInput,
    io,
)
from farloads.modules.select import build_critical  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def test_tail_loads_property_proxies_to_empennage():
    p = Project(name="t")
    assert p.tail_loads is None and p.vtail_loads is None   # no geometry yet
    ti = TailLoadsInput(htail_area_sqft=36.0, xt25=261.0)
    p.tail_loads = ti
    # The single stored home is geometry.empennage.htail; the property reads it back.
    assert p.geometry is not None and p.geometry.empennage is not None
    assert p.geometry.empennage.htail is ti
    assert p.tail_loads is ti
    p.vtail_loads = VTailLoadsInput(vtail_area_sqft=14.0)
    assert p.geometry.empennage.vtail is p.vtail_loads
    # Clearing goes back through the proxy.
    p.tail_loads = None
    assert p.tail_loads is None and p.geometry.empennage.htail is None


def test_empennage_round_trips_through_io():
    p = io.load_project(_GA)
    ti, vt = p.tail_loads, p.vtail_loads
    assert ti is not None and vt is not None
    p2 = io.project_from_dict(io.project_to_dict(p))
    # Every native field survives, and it is stored under geometry.empennage (not top-level).
    assert p2.tail_loads == ti
    assert p2.vtail_loads == vt
    assert p2.geometry.empennage.htail is p2.tail_loads
    d = io.project_to_dict(p)
    assert "tail_loads" not in d and "vtail_loads" not in d      # no top-level keys
    assert "htail" in d["geometry"]["empennage"] and "vtail" in d["geometry"]["empennage"]


def test_pre_v27_top_level_tail_slices_migrate_to_empennage():
    d = {
        "name": "legacy",
        "tail_loads": {"htail_area_sqft": 36.944, "xt25": 261.027, "htail_semispan_in": 73.1},
        "vtail_loads": {"vtail_area_sqft": 14.84, "vtail_span_in": 57.0},
    }
    p = io.project_from_dict(d)
    assert p.geometry is not None and p.geometry.empennage is not None
    assert math.isclose(p.tail_loads.htail_area_sqft, 36.944)
    assert math.isclose(p.vtail_loads.vtail_span_in, 57.0)


def test_select_tail_loads_survive_round_trip_bit_for_bit():
    """The empennage-derived slices feed SELECT losslessly: the governing
    horizontal-tail loads are byte-identical before and after a JSON round-trip
    (the single-source move does not perturb the oracle-locked calc). The exact
    Appendix A values are asserted in test_select.py."""
    def htail_loads(pr):
        return {c.label: {v.label: v.value for v in c.loads}
                for c in build_critical(pr).conditions if c.component == "htail"}
    p = io.load_project(_GA)
    before = htail_loads(p)
    after = htail_loads(io.project_from_dict(io.project_to_dict(p)))
    assert before and before == after


if __name__ == "__main__":
    test_tail_loads_property_proxies_to_empennage()
    print("ok property proxy")
    test_empennage_round_trips_through_io()
    print("ok io round-trip")
    test_pre_v27_top_level_tail_slices_migrate_to_empennage()
    print("ok pre-v27 migration")
    test_select_tail_loads_survive_round_trip_bit_for_bit()
    print("ok SELECT bit-for-bit")
    print("all empennage tests passed")
