"""Single multi-sheet ``.xlsx`` workbook export (Step D8.2).

A spreadsheet-native alternative to the ``.zip`` bundle on the Export page: one
workbook with a tab per module's load-case CSV, the case-index table, and the
tabular (non-BDF) sbeam span-load CSVs. Like :mod:`sloads.export.sbeam_bridge`,
this is a pure renderer -- it re-shapes strings/rows the Export page has already
computed for the CSV/zip channel into DataFrames and writes them to one
in-memory workbook; it performs no new calculation and does no file I/O itself.

BDF card text (``*.bdf``) is intentionally excluded -- it is not tabular data
and belongs in the ``.zip``/individual downloads instead.
"""

from __future__ import annotations

import io as _io
from typing import Dict, Optional

import pandas as pd

# Excel sheet names are capped at 31 characters and may not contain
# ``[]:*?/\\``.
_INVALID_SHEET_CHARS = str.maketrans({c: " " for c in "[]:*?/\\"})


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


def build_workbook(
    project_info: Dict[str, str],
    module_csvs: Dict[str, str],
    module_labels: Dict[str, str],
    case_index_csv: str,
    span_csvs: Dict[str, str],
    methods: str = "",
) -> bytes:
    """Build the workbook and return its bytes.

    ``project_info`` -- ordered ``{field: value}`` for the ``Project`` sheet.
    ``module_csvs`` -- ``{module_name: csv_text}`` (the same strings the Export
    page's per-module CSV buttons already serve).
    ``module_labels`` -- ``{module_name: display title}`` for the sheet name.
    ``case_index_csv`` -- the case-index CSV text.
    ``span_csvs`` -- ``{sheet_title: csv_text}`` for the tabular sbeam artifacts
    (wing/fuselage span loads, tail chordwise, control-surface loads).
    ``methods`` -- the methods & limitations statement (Step G8.3); when given it
    becomes a dedicated *Methods* sheet, so a workbook forwarded on its own
    carries its own basis like every other channel.
    """
    buf = _io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(
            {"Field": list(project_info.keys()), "Value": list(project_info.values())}
        ).to_excel(writer, sheet_name="Project", index=False)

        for module, csv_text in module_csvs.items():
            df = _csv_to_df(csv_text)
            if df is None:
                continue
            label = module_labels.get(module, module)
            df.to_excel(writer, sheet_name=_sheet_name(label), index=False)

        case_index_df = _csv_to_df(case_index_csv)
        if case_index_df is not None:
            case_index_df.to_excel(writer, sheet_name="Case Index", index=False)

        for title, csv_text in span_csvs.items():
            df = _csv_to_df(csv_text)
            if df is None:
                continue
            df.to_excel(writer, sheet_name=_sheet_name(title), index=False)

        if methods.strip():
            pd.DataFrame({"Methods and limitations": methods.rstrip("\n").split("\n")}
                         ).to_excel(writer, sheet_name="Methods", index=False)

    return buf.getvalue()
