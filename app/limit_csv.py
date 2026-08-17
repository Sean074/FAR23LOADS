"""The analysis pages' LIMIT tables and CSV downloads, converted and unit-labelled.

The Wing/Fuselage/Tail Loads pages show a **LIMIT** station table (the
oracle-traceable numbers, the CLAUDE.md analysis-page carve-out) and offer it as
a CSV download beside the ULTIMATE sbeam-bridge file. Before L-8i each page built
that CSV inline from the raw Imperial row dicts, so an SI session downloaded
Imperial numbers under unit-less headers while the table above was converted --
the units-defect class M4-20 already paid for. These builders are the single
owner per page of (a) the column -> Imperial-unit map, (b) the display
conversion, and (c) the unit-suffixed header, and feed **both** the on-screen
table and the download so the two cannot disagree.

Decisions (L-8i review, 2026-08-16): the map stays per page (the sources,
``wing_load_rows``/``body_load_rows``, return pre-formatted strings with no
quantity kind); the file states its units in the headers and its basis in the
``Basis`` column / filename -- **no** ``units_statement`` line, because these
are the LIMIT analysis-page channel, not a deliverable (``CONVENTIONS.md`` §3).
The sbeam/export channel (``sloads.export``) is untouched: it never converts
here and keeps its own writers.

Pure functions, no Streamlit -- ``tests/test_limit_csv.py`` is the drift guard.
"""

from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, List, Sequence, Tuple

from sloads import UnitSystem, si_scalar_label, to_si_scalar
from sloads.models.results import TailChordResult

_UnitMap = Dict[str, Tuple[str, int]]

# Column -> (Imperial unit key of ``sloads.units._SCALAR_TO_SI``, rounding).
# Mxx/Myy/Mzz are all "lb-in" per ``net_loads.run`` (its ``LoadValue`` entries),
# matching WINGINER/NETLOADS; ``Case``/``MyyAxis``/``Basis`` are identity columns.
_WING_UNITS: _UnitMap = {
    "X": ("in", 3), "Y": ("in", 3), "Z": ("in", 3),
    "Fx": ("lbf", 1), "Fz": ("lbf", 1), "Sx": ("lbf", 1), "Sz": ("lbf", 1),
    "Mxx": ("lb-in", 0), "Myy": ("lb-in", 0), "Mzz": ("lb-in", 0),
}
_BODY_UNITS: _UnitMap = {
    "X": ("in", 3), "Fz": ("lbf", 2), "Sz": ("lbf", 2), "Myy": ("lb-in", 1),
}


def _header(col: str, unit: str, system: UnitSystem) -> str:
    return f"{col} ({si_scalar_label(unit, system)})"


def _convert_rows(rows: Iterable[Dict[str, str]], units: _UnitMap,
                  system: UnitSystem) -> List[Dict[str, object]]:
    """Copy of the row dicts with load columns converted and unit-suffixed keys.

    Never mutates the source rows -- the export paths keep the Imperial originals.
    Column order is preserved; identity columns keep their bare names.
    """
    out: List[Dict[str, object]] = []
    for r in rows:
        conv: Dict[str, object] = {}
        for key, val in r.items():
            if key in units:
                unit, nd = units[key]
                conv[_header(key, unit, system)] = round(to_si_scalar(float(val), unit, system), nd)
            else:
                conv[key] = val
        out.append(conv)
    return out


def _to_csv(rows: Sequence[Dict[str, object]]) -> str:
    buf = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Wing (``wing_load_rows``) and fuselage (``body_load_rows``) station tables
# --------------------------------------------------------------------------- #
def wing_limit_rows(rows: Iterable[Dict[str, str]], system: UnitSystem) -> List[Dict[str, object]]:
    """``wing_load_rows`` output converted to ``system`` with unit-suffixed headers."""
    return _convert_rows(rows, _WING_UNITS, system)


def wing_limit_csv(rows: Iterable[Dict[str, str]], system: UnitSystem) -> str:
    """The Wing Loads page's LIMIT download -- the same rows the table shows."""
    return _to_csv(wing_limit_rows(rows, system))


def body_limit_rows(rows: Iterable[Dict[str, str]], system: UnitSystem) -> List[Dict[str, object]]:
    """``body_load_rows`` output converted to ``system`` with unit-suffixed headers."""
    return _convert_rows(rows, _BODY_UNITS, system)


def body_limit_csv(rows: Iterable[Dict[str, str]], system: UnitSystem) -> str:
    """The Fuselage Loads page's LIMIT download -- the same rows the table shows."""
    return _to_csv(body_limit_rows(rows, system))


# --------------------------------------------------------------------------- #
# Tail chordwise distributions (``TailChordResult``)
# --------------------------------------------------------------------------- #
def tail_limit_rows(results: Iterable[TailChordResult], system: UnitSystem) -> List[Dict[str, object]]:
    """One row per ``TailChordResult``: LT25/LT50 and the station pressures.

    Headers carry the unit **and** the LIMIT marker (this table has no ``Basis``
    column). PSI stations are numbered leading-edge first.
    """
    lbf = si_scalar_label("lbf", system)
    psi = si_scalar_label("psi", system)
    return [
        {"Component": r.component, "Condition": r.case,
         f"LT25 ({lbf}, LIMIT)": round(to_si_scalar(r.lt25, "lbf", system), 2),
         f"LT50 ({lbf}, LIMIT)": round(to_si_scalar(r.lt50, "lbf", system), 2),
         **{f"PSI(X{i}) ({psi}, LIMIT)": round(to_si_scalar(s.psi, "psi", system), 4)
            for i, s in enumerate(r.stations, start=1)}}
        for r in results
    ]


def tail_limit_csv(results: Iterable[TailChordResult], system: UnitSystem) -> str:
    """The Tail Loads page's LIMIT download -- the same rows the table shows."""
    return _to_csv(tail_limit_rows(results, system))
