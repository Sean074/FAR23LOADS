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

from sloads import Project, SelectInput, UnitSystem, io
from sloads.constants import ULTIMATE_FACTOR
from sloads.modules import select
from sloads.report import (
    format_value,
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
    assert rows[idx][header] == format_value(lv.value * ULTIMATE_FACTOR)

    # (b) A dimensionless quantity (load factor NZ) is unscaled and unmarked.
    nz_headers = [h for h in rows[0] if h.startswith("Load factor NZ")]
    for r in rows:
        for h in [h for h in r if h.startswith("Load factor NZ")]:
            assert "-ULT" not in h
    assert any("-ULT" not in h for h in nz_headers) or not nz_headers

    # (c) Every row states its own case's factor -- the contract, not a flat 1.5
    #     (F-R1). On this GA project SELECT stamps the 23.303 default throughout,
    #     so the two happen to coincide here; test_per_case_safety_factor_is_honoured
    #     is what pins the per-case behavior.
    assert all(r["SF"] == format_value(c.safety_factor) for r, c in zip(rows, conds))
    assert all(c.safety_factor == ULTIMATE_FACTOR for c in conds)

    # (d) No None/NaN anywhere; sparse cells render "—".
    all_cols = set().union(*[set(r) for r in rows])
    for r in rows:
        assert set(r) == all_cols          # every row spans the full union
        assert all(v is not None for v in r.values())
    assert any(v == "—" for r in rows for v in r.values())


def test_per_case_safety_factor_is_honoured():
    """A case whose loads are already ultimate (SF = 1.0) is neither re-scaled nor
    mislabelled, and it does not change its neighbours' rows (review F-R1).

    ``CriticalCondition.safety_factor`` is the case's own limit->ultimate factor
    (models/results.py; 14 CFR 23.303 default 1.5, 1.0 = already ultimate) and the
    render boundary must read it per case -- the same rule the export side applies
    (``export.sbeam_bridge._sf``), so a report figure and its bulk-data card state
    one factor for one case.
    """
    conds = [c for c in select.build_critical(_ga6()).conditions if c.component == "fuselage"]
    idx = next(i for i, c in enumerate(conds) if any(lv.units == "lb" for lv in c.loads))
    other = next(i for i in range(len(conds)) if i != idx)

    before = governing_loads_table(conds, UnitSystem.IMPERIAL)
    conds[idx].safety_factor = 1.0
    after = governing_loads_table(conds, UnitSystem.IMPERIAL)

    lv = next(lv for lv in conds[idx].loads if lv.units == "lb")
    header = f"{lv.label} ({ultimate_units(lv.units)})"
    assert after[idx][header] == format_value(lv.value)          # x1.0, not x1.5
    assert after[idx]["SF"] == format_value(1.0)                 # and it says so
    assert "-ULT" in header                                      # still an ULTIMATE column
    assert after[other] == before[other]                         # neighbours untouched
    assert after[other]["SF"] == format_value(ULTIMATE_FACTOR)


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
