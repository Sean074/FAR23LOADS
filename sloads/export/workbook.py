"""Single multi-sheet ``.xlsx`` workbook export (Step D8.2).

A spreadsheet-native alternative to the ``.zip`` bundle on the Export page: one
workbook with a tab per module's load-case CSV, the case-index table, and the
tabular (non-BDF) sbeam span-load CSVs. Like :mod:`sloads.export.sbeam_bridge`,
this is a pure renderer -- it re-shapes strings/rows the Export page has already
computed for the CSV/zip channel into DataFrames and writes them to one
in-memory workbook; it performs no new calculation and does no file I/O itself.

BDF card text (``*.bdf``) is intentionally excluded -- it is not tabular data
and belongs in the ``.zip``/individual downloads instead.

**Units are stated per sheet, not per workbook** (review m14). One workbook
carries both channels of the selected system: the module and case-index sheets
are the HUMAN channel (the same tables the per-module CSVs serve), while the
span-load sheets are the SOLVER channel that feeds the sbeam decks -- in SI
``N·m``/``kPa`` beside ``N·mm``/``MPa``. A single workbook-level statement is
therefore wrong for half the sheets, which is a SUMMARY_REPORT.md 3.5/4.7-class
conformance failure ("a per-file units column that disagrees ... is a
conformance failure, not a footnote"). Each data sheet states its own set in
cell ``A1`` above its header row, and the ``Project`` sheet names both channels
and which sheets carry which.
"""

from __future__ import annotations

import io as _io
from typing import Dict, Optional

import pandas as pd

from ..units import Channel, UnitSystem, deliverable_units, units_statement

# Excel sheet names are capped at 31 characters and may not contain
# ``[]:*?/\\``.
_INVALID_SHEET_CHARS = str.maketrans({c: " " for c in "[]:*?/\\"})

# The aviation-standard exception (SUMMARY_REPORT.md 3.5): KEAS and ft are held
# in both systems, so every sheet that carries them says so rather than leaving
# an unconverted speed looking like an oversight.
_AVIATION = "airspeed KEAS and altitude ft are aviation-standard and unconverted"


def _sheet_name(name: str) -> str:
    return name.translate(_INVALID_SHEET_CHARS)[:31]


def _csv_to_df(csv_text: str) -> Optional[pd.DataFrame]:
    """Parse one CSV string, ignoring the G8.3 ``#`` methods-statement header.

    ``comment="#"`` is required, not cosmetic: since G8.3 every exported CSV may
    carry the methods & limitations block as ``#`` lines above the header row, and
    without this pandas would read the first comment line as the column names.
    Any in-repo CSV reader must do the same.
    """
    if not csv_text or not csv_text.strip():
        return None
    df = pd.read_csv(_io.StringIO(csv_text), comment="#")
    return None if df.empty and not list(df.columns) else df


def _unit_notes(system: UnitSystem) -> Dict[str, str]:
    """The unit statements this workbook needs -- the three per-sheet ``A1``
    lines plus the two bare sets the ``Project`` sheet names -- from one
    resolution of the selected system, so a sheet's statement cannot drift from
    the channel the numbers in it were written in."""
    human = units_statement(deliverable_units(system, Channel.HUMAN))
    solver = units_statement(deliverable_units(system, Channel.SOLVER))
    return {
        "human": f"Units: {human}. Loads are ULTIMATE; {_AVIATION}.",
        # The consistent set the decks need spelled out beside the sheet, because
        # N·m against mm coordinates is a silent 1000x (SUMMARY_REPORT.md 3.5,
        # solver-deck exception M4-20 D-19).
        "solver": (f"Units: {solver} — the sbeam solver channel (a consistent set: "
                   f"moments are force x length in the same base units). Loads are "
                   f"ULTIMATE; {_AVIATION}."),
        # The case index carries no load quantity at all -- only identity, speed
        # and altitude -- so claiming either channel's set would be false.
        "index": f"Units: no load quantities on this sheet; {_AVIATION}.",
        "human_set": human,
        "solver_set": solver,
    }


def build_workbook(
    project_info: Dict[str, str],
    module_csvs: Dict[str, str],
    module_labels: Dict[str, str],
    case_index_csv: str,
    span_csvs: Dict[str, str],
    methods: str = "",
    *,
    system: UnitSystem = UnitSystem.IMPERIAL,
) -> bytes:
    """Build the workbook and return its bytes.

    ``project_info`` -- ordered ``{field: value}`` for the ``Project`` sheet. It
    SHALL NOT carry a units row: units are this function's own to state, per
    sheet, from ``system`` (see the module docstring).
    ``module_csvs`` -- ``{module_name: csv_text}`` (the same strings the Export
    page's per-module CSV buttons already serve).
    ``module_labels`` -- ``{module_name: display title}`` for the sheet name.
    ``case_index_csv`` -- the case-index CSV text.
    ``span_csvs`` -- ``{sheet_title: csv_text}`` for the tabular sbeam artifacts
    (wing/fuselage span loads, tail chordwise, control-surface loads).
    ``methods`` -- the methods & limitations statement (Step G8.3); when given it
    becomes a dedicated *Methods* sheet, so a workbook forwarded on its own
    carries its own basis like every other channel.
    ``system`` -- the deliverable unit system the caller wrote every CSV string
    above in. This function converts nothing; it states what it was given.
    """
    notes = _unit_notes(system)
    buf = _io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:

        def write(df: pd.DataFrame, title: str, units_note: str) -> None:
            """One data sheet, its unit statement in ``A1`` above the header row."""
            sheet = _sheet_name(title)
            df.to_excel(writer, sheet_name=sheet, index=False, startrow=1)
            writer.sheets[sheet]["A1"] = units_note

        project_rows = list(project_info.items()) + [
            ("Units (module & report sheets)", notes["human_set"]),
            ("Units (sbeam span-load sheets)", notes["solver_set"]),
            ("Units (airspeed, altitude)", "KEAS, ft — aviation-standard, unconverted"),
        ]
        pd.DataFrame(
            {"Field": [f for f, _ in project_rows], "Value": [v for _, v in project_rows]}
        ).to_excel(writer, sheet_name="Project", index=False)

        for module, csv_text in module_csvs.items():
            df = _csv_to_df(csv_text)
            if df is None:
                continue
            write(df, module_labels.get(module, module), notes["human"])

        case_index_df = _csv_to_df(case_index_csv)
        if case_index_df is not None:
            write(case_index_df, "Case Index", notes["index"])

        for title, csv_text in span_csvs.items():
            df = _csv_to_df(csv_text)
            if df is None:
                continue
            write(df, title, notes["solver"])

        if methods.strip():
            pd.DataFrame({"Methods and limitations": methods.rstrip("\n").split("\n")}
                         ).to_excel(writer, sheet_name="Methods", index=False)

    return buf.getvalue()
