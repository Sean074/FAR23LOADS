"""The analysis pages' LIMIT CSV downloads follow the unit toggle and label units (L-8i).

Before L-8i the Wing/Fuselage/Tail Loads pages built their LIMIT download inline
from the raw Imperial row dicts: an SI session downloaded Imperial numbers under
unit-less headers while the table above was converted. ``app/limit_csv.py`` is
now the single owner per page of the column->unit map, the conversion and the
header; the on-screen table and the download share it. This is the drift guard:

1. **Imperial in, Imperial out** -- the Imperial file's numbers are the row
   builders' own strings, headers ``(in)``/``(lbf)``/``(lb-in)``/``(psi)``.
2. **SI converts** -- every load cell equals ``to_si_scalar`` of the Imperial
   one, headers ``(mm)``/``(N)``/``(N·m)``/``(kPa)``.
3. **No bare load header** in either system: every non-identity column states
   its unit; the tail table also states LIMIT in-band (it has no ``Basis``
   column); the wing/fuselage ``Basis`` column still says ``LIMIT``.
"""

import csv
import io
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402
from limit_csv import (  # noqa: E402
    body_limit_csv,
    body_limit_rows,
    tail_limit_csv,
    tail_limit_rows,
    wing_limit_csv,
    wing_limit_rows,
)

from sloads import UnitSystem  # noqa: E402
from sloads import io as sloads_io  # noqa: E402
from sloads.modules.body_loads import body_load_rows, build_body_loads  # noqa: E402
from sloads.modules.net_loads import build_net_loads, wing_load_rows  # noqa: E402
from sloads.modules.taildist import build_tail_chordwise  # noqa: E402
from sloads.units import to_si_scalar  # noqa: E402

_GA = os.path.join(_ROOT, "examples", "ga6_normal.project.json")
_IDENTITY = {"Case", "MyyAxis", "Basis", "Component", "Condition"}
_IMPERIAL = {"in", "lbf", "lb-in", "psi"}
_SI = {"mm", "N", "N·m", "kPa"}


def _project():
    return sloads_io.load_project(_GA)


def _parse(text: str):
    return list(csv.DictReader(io.StringIO(text)))


def _unit_of(header: str) -> str:
    """``"Fz (lbf)"`` -> ``"lbf"``; ``"LT25 (lbf, LIMIT)"`` -> ``"lbf"``."""
    assert header.endswith(")"), header
    inner = header[header.rindex("(") + 1:-1]
    return inner.split(",")[0].strip()


def _check_headers(headers, expected_units, limit_in_band: bool):
    for h in headers:
        if h in _IDENTITY:
            continue
        assert "(" in h, f"bare load header {h!r}"
        assert _unit_of(h) in expected_units, h
        if limit_in_band:
            assert h.endswith(", LIMIT)"), h


# --------------------------------------------------------------------------- #
# Wing
# --------------------------------------------------------------------------- #
def test_wing_imperial_file_is_the_row_builder_bit_for_bit():
    rows = wing_load_rows(build_net_loads(_project()).wing_net)
    parsed = _parse(wing_limit_csv(rows, UnitSystem.IMPERIAL))
    _check_headers(parsed[0].keys(), _IMPERIAL, limit_in_band=False)
    assert {r["Basis"] for r in parsed} == {"LIMIT"}
    for src, out in zip(rows, parsed):
        assert math.isclose(float(out["Sz (lbf)"]), float(src["Sz"]), rel_tol=0, abs_tol=0.05)
        assert math.isclose(float(out["Mxx (lb-in)"]), float(src["Mxx"]), abs_tol=0.5)
        assert out["Case"] == src["Case"] and out["MyyAxis"] == src["MyyAxis"]


def test_wing_si_file_converts_every_load_column():
    rows = wing_load_rows(build_net_loads(_project()).wing_net)
    parsed = _parse(wing_limit_csv(rows, UnitSystem.SI))
    _check_headers(parsed[0].keys(), _SI, limit_in_band=False)
    for src, out in zip(rows, parsed):
        for col, unit, hdr in (("Y", "in", "Y (mm)"), ("Sz", "lbf", "Sz (N)"),
                               ("Mxx", "lb-in", "Mxx (N·m)")):
            want = to_si_scalar(float(src[col]), unit, UnitSystem.SI)
            assert math.isclose(float(out[hdr]), want, rel_tol=1e-3, abs_tol=0.6), (col, want, out[hdr])


def test_wing_table_and_download_are_the_same_rows():
    rows = wing_load_rows(build_net_loads(_project()).wing_net)
    table = wing_limit_rows(rows, UnitSystem.SI)
    parsed = _parse(wing_limit_csv(rows, UnitSystem.SI))
    assert list(table[0].keys()) == list(parsed[0].keys())
    assert len(table) == len(parsed) == len(rows)


# --------------------------------------------------------------------------- #
# Fuselage
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("system", [UnitSystem.IMPERIAL, UnitSystem.SI])
def test_body_file_labels_and_converts(system):
    rows = body_load_rows(build_body_loads(_project()))
    parsed = _parse(body_limit_csv(rows, system))
    expected = _IMPERIAL if system == UnitSystem.IMPERIAL else _SI
    _check_headers(parsed[0].keys(), expected, limit_in_band=False)
    assert {r["Basis"] for r in parsed} == {"LIMIT"}
    myy_hdr = "Myy (lb-in)" if system == UnitSystem.IMPERIAL else "Myy (N·m)"
    for src, out in zip(rows, parsed):
        want = to_si_scalar(float(src["Myy"]), "lb-in", system)
        assert math.isclose(float(out[myy_hdr]), want, rel_tol=1e-3, abs_tol=0.06)
    assert list(body_limit_rows(rows, system)[0].keys()) == list(parsed[0].keys())


# --------------------------------------------------------------------------- #
# Tail chordwise
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("system", [UnitSystem.IMPERIAL, UnitSystem.SI])
def test_tail_file_labels_units_and_limit_in_band(system):
    results = build_tail_chordwise(_project())
    assert results
    parsed = _parse(tail_limit_csv(results, system))
    expected = _IMPERIAL if system == UnitSystem.IMPERIAL else _SI
    _check_headers(parsed[0].keys(), expected, limit_in_band=True)
    lbf = "lbf" if system == UnitSystem.IMPERIAL else "N"
    psi = "psi" if system == UnitSystem.IMPERIAL else "kPa"
    for src, out in zip(results, parsed):
        assert out["Component"] == src.component and out["Condition"] == src.case
        assert math.isclose(float(out[f"LT25 ({lbf}, LIMIT)"]),
                            to_si_scalar(src.lt25, "lbf", system), rel_tol=1e-3, abs_tol=0.006)
        assert math.isclose(float(out[f"PSI(X1) ({psi}, LIMIT)"]),
                            to_si_scalar(src.stations[0].psi, "psi", system), rel_tol=1e-3, abs_tol=6e-5)
    assert list(tail_limit_rows(results, system)[0].keys()) == list(parsed[0].keys())


def test_empty_results_give_an_empty_file():
    assert wing_limit_csv([], UnitSystem.SI) == ""
    assert tail_limit_csv([], UnitSystem.SI) == ""


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        marks = getattr(t, "pytestmark", [])
        params = [m for m in marks if m.name == "parametrize"]
        arg_sets = params[0].args[1] if params else [None]
        for a in arg_sets:
            try:
                t(a) if params else t()
                print(f"PASS {t.__name__} {a if params else ''}")
            except Exception:
                failed += 1
                print(f"FAIL {t.__name__} {a if params else ''}")
                traceback.print_exc()
    print(f"\n{failed} failed")
    sys.exit(1 if failed else 0)
