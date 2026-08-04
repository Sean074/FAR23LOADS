"""Rendering and reporting: tables, text, and the controlled summary document.

``sloads/report.py`` became this package at **Step G8.1**, the same mechanical
move ``models.py`` -> ``models/`` made at M3-1. Everything that existed before
lives in :mod:`sloads.report.render` and is re-exported here, so every prior
import (``from sloads.report import load_cases_to_rows``) keeps working
unchanged.

Layout:

* :mod:`~sloads.report.render`   -- tables, the text report, and the
  **limit -> ultimate boundary** for tabular output (pre-existing code).
* :mod:`~sloads.report.methods`  -- the single source of the methods &
  limitations statement, plus its CSV ``#`` / BDF ``$`` comment-block wrappers.
* :mod:`~sloads.report.coverage` -- the FAR 23 Subpart C coverage matrix.
Still to come (Step G8.4's content model onward, backlog **M3-3b**):
``content.py`` (``Project`` + module results -> ``ReportDocument``), ``latex.py``
(``ReportDocument`` -> ``.tex``) and ``plots_tex.py`` (pgfplots figures).

Everything in this package is **pure**: no filesystem, no subprocess, no
Streamlit. Compiling a ``.tex`` to PDF needs both, so that one impure piece lives
outside, in :mod:`sloads.export.pdf`, and nothing here imports it.
"""

from __future__ import annotations

from .coverage import (
    COVERED,
    FAR23_SUBPART_C,
    NOT_ANALYSED,
    NOT_APPLICABLE,
    OUT_OF_SCOPE,
    CoverageRow,
    coverage_matrix,
    coverage_summary,
)
from .methods import (
    bdf_comment_block,
    csv_comment_block,
    methods_statement,
    strip_comment_lines,
)
from .render import (
    envelope_extremes,
    format_value,
    governing_loads_table,
    has_load_case_data,
    load_cases_to_rows,
    module_text_report,
    results_to_rows,
    text_report,
    to_ultimate,
    ultimate_units,
)

__all__ = [
    "envelope_extremes",
    "format_value",
    "governing_loads_table",
    "has_load_case_data",
    "load_cases_to_rows",
    "module_text_report",
    "results_to_rows",
    "text_report",
    "to_ultimate",
    "ultimate_units",
    # --- G8.3: the methods & limitations statement ------------------------- #
    "methods_statement",
    "csv_comment_block",
    "bdf_comment_block",
    "strip_comment_lines",
    # --- G8.4: FAR 23 Subpart C coverage ----------------------------------- #
    "coverage_matrix",
    "coverage_summary",
    "CoverageRow",
    "FAR23_SUBPART_C",
    "COVERED",
    "NOT_APPLICABLE",
    "NOT_ANALYSED",
    "OUT_OF_SCOPE",
]
