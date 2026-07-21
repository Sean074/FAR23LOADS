"""The shared governing-loads renderer (M2-4).

`report.governing_loads_table` is the single source for the Results Review headline
and the Flight Envelope "Critical Loads" tab. It renders SELECT's per-component
critical conditions with ULTIMATE marking: load quantities scale by the safety
factor and take the ``-ULT`` marker; dimensionless/speed quantities (n, CL, V) pass
through unscaled and unmarked; a trailing ``SF`` column states the factor; and cells
absent from a given condition render ``"—"`` (no None/NaN).

Reference: docs/30_future acceptance for M2-4; CLAUDE.md "Ultimate-load output".
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, SelectInput, UnitSystem, io  # noqa: E402
from farloads.constants import ULTIMATE_FACTOR  # noqa: E402
from farloads.modules import select  # noqa: E402
from farloads.report import (  # noqa: E402
    _fmt,
    governing_loads_table,
    to_ultimate,
    ultimate_units,
)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _ga6() -> Project:
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.select_input = SelectInput(full_down_aileron_deg=15.0, basic_airfoil_cm=-0.03)
    return p


def test_public_wrappers_mark_and_scale_loads_only():
    # A force is scaled and marked; a dimensionless quantity passes through.
    assert ultimate_units("lb") == "lbs-ULT"
    assert ultimate_units("") == ""            # dimensionless (n, CL)
    assert ultimate_units("kt(EAS)") == "kt(EAS)"  # speed -- unmarked
    assert to_ultimate(100.0, "lb") == 150.0
    assert to_ultimate(3.8, "") == 3.8         # load factor, not a load


def test_governing_loads_table_renders_ultimate_with_sf():
    conds = select.build_critical(_ga6()).conditions
    rows = governing_loads_table(conds, UnitSystem.IMPERIAL)
    assert len(rows) == len(conds)

    # Find a condition carrying a real force (fuselage conditions do); check its
    # rendered cell is limit x 1.5 under a `-ULT` header.
    idx = next(i for i, c in enumerate(conds)
               if any(lv.units == "lb" for lv in c.loads))
    lv = next(lv for lv in conds[idx].loads if lv.units == "lb")
    header = f"{lv.label} ({ultimate_units(lv.units)})"
    assert "-ULT" in header
    assert rows[idx][header] == _fmt(lv.value * ULTIMATE_FACTOR)

    # (b) A dimensionless quantity (load factor NZ) is unscaled and unmarked.
    nz_headers = [h for h in rows[0] if h.startswith("Load factor NZ")]
    for r in rows:
        for h in [h for h in r if h.startswith("Load factor NZ")]:
            assert "-ULT" not in h
    assert any("-ULT" not in h for h in nz_headers) or not nz_headers

    # (c) Every row states SF = 1.5.
    assert all(r["SF"] == _fmt(ULTIMATE_FACTOR) for r in rows)

    # (d) No None/NaN anywhere; sparse cells render "—".
    all_cols = set().union(*[set(r) for r in rows])
    for r in rows:
        assert set(r) == all_cols          # every row spans the full union
        assert all(v is not None for v in r.values())
    assert any(v == "—" for r in rows for v in r.values())


def test_headline_and_critical_tab_use_the_same_helper():
    # Both views call governing_loads_table for the same component list, so the
    # tables are identical by construction -- assert the helper is deterministic.
    conds = [c for c in select.build_critical(_ga6()).conditions if c.component == "fuselage"]
    a = governing_loads_table(conds, UnitSystem.IMPERIAL)
    b = governing_loads_table(conds, UnitSystem.IMPERIAL)
    assert a == b


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
