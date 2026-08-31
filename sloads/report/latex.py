"""``ReportDocument`` -> LaTeX source (Step G8.5).

The renderer is deliberately dumb: it makes no engineering decisions, converts no
units and scales nothing. Every number and every unit marker was decided in
:mod:`sloads.report.content`; this module only decides where they sit on the page.
That split is what makes the content testable without matching LaTeX strings, and
this module testable without a TeX engine.

What it *does* own, and why each matters:

* **Escaping.** Every user-supplied string (project name, engineer, condition
  labels, unit strings) goes through :func:`~sloads.report.plots_tex.escape`. A
  project called ``"Model 100 & 100A"`` or a unit string ``lb/in^2-ULT`` would
  otherwise abort the compile or typeset silently wrong.
* **Controlled-document furniture** (decision G8-1): a title page with the
  document-control and signature block, a table of contents, ``fancyhdr`` running
  heads carrying the project and revision, "page *n* of *m*" footers, and
  ``longtable`` for tables that cross a page break.
* **Absence.** A section with an ``absent_reason`` renders that sentence in place
  of its content -- never an empty table or an empty axis (SUMMARY_REPORT.md §3.4).

Determinism: nothing here reads the clock or a hash-ordered container, so two
renders of one :class:`~sloads.report.content.ReportDocument` are byte-identical
(SUMMARY_REPORT.md §2). Pure: no filesystem, no subprocess. Compiling the result
to PDF needs both and lives in :mod:`sloads.export.pdf`.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from ..units import IN_TO_MM
from .content import Figure, ReportDocument, Section, Table
from .methods import STANDING_DISCLAIMER
from .plots_tex import escape, figure_body_tex

#: Packages the ``.tex`` needs. All are in a standard TeX distribution and in the
#: tectonic bundle -- SUMMARY_REPORT.md §2 forbids anything more exotic, and
#: forbids external image files (hence pgfplots rather than \includegraphics).
#: §2's *Data reference* clause (amended 2026-08-30) lets a report delivered as a
#: **package** read manifest-listed data files from inside it; this report is also
#: offered as a standalone ``.tex`` download, so it references no external file at
#: all -- everything it draws is inline (guarded in ``test_report_latex.py``).
PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[margin=22mm,includeheadfoot]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{fancyhdr}
\usepackage{float}
\usepackage{lastpage}
\usepackage{pgfplots}
\usepackage[hidelinks]{hyperref}
\pgfplotsset{compat=1.16}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.6em}
\renewcommand{\arraystretch}{1.15}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
% The width a table's columns share out between them: the text block less the
% inter-column padding, so proportioned columns fit exactly (see _column_spec).
\newlength{\sltablewidth}
"""

#: The "not analysed" marker. Bold rather than coloured: §4.3/§4.4 require the
#: document to stay legible in greyscale, so nothing may be encoded by colour.
NOT_ANALYSED_MARKER = "NOT ANALYSED"


def _headers(doc: ReportDocument) -> str:
    control = dict(doc.control)
    left = escape(doc.project_name)
    revision = control.get("Revision", "")
    right = escape(f"Rev {revision}") if revision else escape("Rev —")
    return "\n".join([
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        f"\\fancyhead[L]{{\\small {left}}}",
        f"\\fancyhead[R]{{\\small {right}}}",
        r"\fancyfoot[L]{\small ULTIMATE loads --- SF stated per case}",
        r"\fancyfoot[R]{\small Page \thepage\ of \pageref{LastPage}}",
        r"\renewcommand{\headrulewidth}{0.4pt}",
        r"\renewcommand{\footrulewidth}{0.4pt}",
    ])


def _title_page(doc: ReportDocument) -> str:
    """Title page + document control + signature block (SUMMARY_REPORT.md §4.1)."""
    rows = []
    for label, value in doc.control:
        if not value and label in ("Checked by", "Approved by", "Revision", "Date"):
            # The signature block SHALL exist even when unsigned: a ruled blank is
            # a line to sign, whereas a dropped row reads as an oversight.
            cell = r"\rule{0pt}{1.2em}\hrulefill"
        else:
            cell = escape(value) or r"\textit{(not set)}"
        rows.append(f"{escape(label)} & {cell} \\\\")
    return "\n".join([
        r"\begin{titlepage}",
        r"\thispagestyle{empty}",
        r"\begin{center}",
        r"{\Large\bfseries " + escape(doc.title) + r"}\\[0.6em]",
        r"{\LARGE " + escape(doc.project_name) + r"}\\[0.4em]",
        r"{\large\bfseries " + escape(doc.badge) + r"}",
        r"\end{center}",
        r"\vspace{1.6em}",
        r"\begin{center}",
        r"\begin{tabular}{@{}l L{0.6\textwidth}@{}}",
        r"\toprule",
        "\n".join(rows),
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{center}",
        r"\vfill",
        r"\begin{center}\begin{minipage}{0.86\textwidth}",
        r"\textbf{Load basis.} " + escape(doc.basis) + r"\\[0.4em]",
        r"\textbf{Units.} " + escape(doc.units_note) + r"\\[0.4em]",
        # Quoted, never restated: the disclaimer is one wording (methods.py), and
        # the title page adds only its pointer to the section that expands it.
        r"\textbf{Status.} " + escape(
            f"{STANDING_DISCLAIMER} See the methods and limitations section."
        ),
        r"\end{minipage}\end{center}",
        r"\vspace{1.2em}",
        r"\end{titlepage}",
    ])


def paragraphs_tex(text: str) -> str:
    """Escaped prose, preserving the statement's paragraphs and indented lines.

    The methods statement is a plain-text block with meaning in its layout (an
    indented ``  - exceedance`` line under its heading). Blank lines separate
    paragraphs; an indented or bulleted line starts a new typeset line inside the
    paragraph rather than being reflowed into it, which would run the exceedance
    list into one sentence.
    """
    out: List[str] = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        rendered: List[str] = []
        for ln in lines:
            indented = ln[:1].isspace() or ln.lstrip().startswith("-")
            piece = escape(ln.strip())
            if rendered and indented:
                rendered.append(r"\\" + "\n" + piece)
            elif rendered:
                rendered.append(" " + piece)
            else:
                rendered.append(piece)
        out.append("".join(rendered))
    return "\n\n".join(out)


# --------------------------------------------------------------------------- #
# Column widths
# --------------------------------------------------------------------------- #
# A ``p`` column wraps between words but never inside one, so a column narrower
# than its widest unbreakable token (a case ID, "6.833e+05", the header word
# "Maximum") does not wrap -- it prints on top of the next column. Proportioning
# columns by character count alone is therefore not enough: a column's share must
# also be at least what its longest token needs. The model below works in points
# so "at least" means something, using the page geometry this module's own
# preamble sets.
#: A4 (210mm) less the 22mm margins in :data:`PREAMBLE`, in TeX points.
TEXT_WIDTH_PT = (210.0 - 2 * 22.0) * 72.27 / IN_TO_MM
#: LaTeX's default half-gutter, applied twice per column.
TABCOLSEP_PT = 6.0
#: Average glyph width, by table font size, measured generously enough to cover
#: bold headers and digit-heavy cells (Latin Modern at 11pt base).
_CHAR_PT = {r"\small": 5.0, r"\footnotesize": 4.5}
#: Cell length beyond which a column stops asking for more width and wraps
#: instead -- one long note must not squeeze every other column to nothing.
_MAX_CHARS = 26
#: Slack added to every column so a token never sits flush against the rule.
_PAD_PT = 3.0


def _column_widths_pt(table: Table, char_pt: float, available: float) -> List[float]:
    """Column widths in points: what each column wants, capped to what fits.

    Each column asks for ``desired`` (its typical cell, capped) but never less
    than ``required`` (its longest unbreakable token). When the asks exceed the
    page, the excess is taken from the columns that have slack between the two --
    so a wide prose column shrinks and wraps while a numeric column keeps the
    width its numbers need. Only if that is not enough is everything scaled down.
    """
    required: List[float] = []
    desired: List[float] = []
    natural: List[float] = []
    for i, header in enumerate(table.columns):
        cells = [str(row[i]) for row in table.rows if i < len(row)] + [header]
        longest_word = max((len(w) for cell in cells for w in cell.split()), default=1)
        longest_cell = max((len(cell) for cell in cells), default=1)
        required.append(longest_word * char_pt + _PAD_PT)
        desired.append(max(min(longest_cell, _MAX_CHARS) * char_pt + _PAD_PT,
                           required[-1]))
        natural.append(max(longest_cell * char_pt + _PAD_PT, desired[-1]))
    excess = math.fsum(desired) - available
    if excess <= 0:
        # Room to spare: hand it to the columns the cap held back, so a two-column
        # table of prose fills the page instead of sitting in a narrow ribbon.
        unmet = [n - d for n, d in zip(natural, desired)]
        total_unmet = math.fsum(unmet)
        if total_unmet <= 0:
            return desired
        spare = -excess
        share = min(1.0, spare / total_unmet)
        return [d + un * share for d, un in zip(desired, unmet)]
    slack = [d - r for d, r in zip(desired, required)]
    total_slack = math.fsum(slack)
    if total_slack >= excess:
        return [d - excess * s / total_slack for d, s in zip(desired, slack)]
    scale = available / math.fsum(desired)
    return [d * scale for d in desired]


#: Row count up to which a table is set as one unbreakable float.
#:
#: Above it a table cannot fit a page whatever is done to it, and ``longtable``
#: -- which is what handles that honestly -- takes over. The threshold is
#: deliberately generous: nearly every table this report prints is a handful of
#: rows, and the failure this prevents (a header and a rule stranded above no
#: data) is worse than a table drifting to the next page.
UNBREAKABLE_ROWS = 30


def _table_size_and_spec(table: Table) -> Tuple[str, str]:
    r"""``(font-size command, column spec)`` for ``table``.

    A table that cannot hold its own tokens at ``\small`` drops to
    ``\footnotesize`` rather than overflowing -- the case index and the coverage
    matrix are wide by nature, and shrinking the type is the trade §4.4 already
    accepts for them.
    """
    ncols = len(table.columns)
    available = TEXT_WIDTH_PT - 2 * TABCOLSEP_PT * ncols
    sizes = (r"\footnotesize",) if table.small else (r"\small", r"\footnotesize")
    # The last size is used whether or not it fits -- there is nothing smaller to
    # fall back to. Seeding from it (rather than from ``None``) keeps both names
    # bound on every path, so neither the reader nor a type checker has to prove
    # the loop runs at least once.
    size = sizes[-1]
    widths = _column_widths_pt(table, _CHAR_PT[size], available)
    for candidate in sizes:
        size = candidate
        widths = _column_widths_pt(table, _CHAR_PT[candidate], available)
        if math.fsum(widths) <= available + 0.01:
            break
    # Columns share out ``\sltablewidth`` -- the text block with the inter-column
    # padding already taken off (:func:`_table_tex` sets it). Subtracting the
    # padding per column as well would take it twice and leave every column a few
    # points too narrow, which is exactly how a number ends up on top of its
    # neighbour.
    specs = [r"L{%.4f\sltablewidth}" % (w / available) for w in widths]
    return size, "@{}" + "".join(specs) + "@{}"


def _cell(table: Table, column: str, value: str) -> str:
    text = escape(value)
    if table.status_column and column == table.status_column and \
            value.strip().upper() == NOT_ANALYSED_MARKER:
        return r"\textbf{" + text + "}"
    return text


def table_tex(table: Table) -> str:
    """One table as a ``longtable`` (booktabs rules, repeated header on a break)."""
    if not table.rows:
        return ""
    ncols = len(table.columns)
    header = " & ".join(r"\textbf{" + escape(c) + "}" for c in table.columns) + r" \\"
    body = []
    last = len(table.rows) - 1
    for index, row in enumerate(table.rows):
        cells = [_cell(table, table.columns[i] if i < ncols else "", str(row[i]))
                 for i in range(min(ncols, len(row)))]
        cells += [""] * (ncols - len(cells))
        # ``\\*`` forbids a page break after this row. Applied to the first and
        # the last, which is widow and orphan control for a table: without it
        # longtable happily broke between the final row and ``\endlastfoot``,
        # printing the repeated header and the bottom rule alone at the top of
        # the next page with no data under them (Baron 58, section 2.3, GUI
        # review 2026-08-30). Only those two rows are pinned, so a genuinely
        # long table -- the case index, the coverage matrix -- still breaks
        # wherever it needs to.
        terminator = r" \\*" if index in (0, last) and last > 0 else r" \\"
        body.append(" & ".join(cells) + terminator)
    if table.data_ref:
        # A packaged report ships the table's body as a generated fragment and
        # reads it here (OR-23). The document therefore cannot disagree with the
        # data it ships, because it is the same bytes -- which is why no
        # drift-guard between two renderings is owed. Permitted by
        # ``SUMMARY_REPORT.md`` §2 *Data reference* for a manifest-carrying
        # package only; a standalone ``.tex`` sets no ``data_ref`` and is
        # guarded to keep it that way.
        return r"\input{" + table.data_ref + "}"
    size, spec = _table_size_and_spec(table)
    width = r"\setlength{\sltablewidth}{\dimexpr\linewidth-%d\tabcolsep\relax}" % (2 * ncols)
    if len(table.rows) <= UNBREAKABLE_ROWS:
        # A table short enough to fit a page is set as one unbreakable float, so
        # it moves whole rather than splitting. ``longtable`` split the Baron's
        # five-row Mach table between its last row and ``\endlastfoot`` and put
        # the repeated header and the bottom rule alone at the top of the next
        # page, under no data (GUI review, 2026-08-30) -- a break that no
        # inter-row penalty prevents, because the foot is not a row.
        #
        # ``[H]``, the same placement the figures use and for the same reason:
        # a table belongs to the prose above it. ``[!ht]`` was tried first and
        # floated four of the Baron's five section-2 tables onto a page of their
        # own, away from the subsections that introduce them. ``[H]`` does not
        # float -- when the table will not fit, the page breaks and the whole
        # table moves, which is the behaviour wanted here.
        out = [
            r"\begin{table}[H]", r"\centering", "{" + size, width,
            r"\caption{" + escape(table.title) + "}",
            r"\begin{tabular}{" + spec + "}",
            r"\toprule", header, r"\midrule",
            "\n".join(body),
            r"\bottomrule",
            r"\end{tabular}}", r"\end{table}",
        ]
    else:
        out = [
            "{" + size, width,
            r"\begin{longtable}{" + spec + "}",
            r"\caption{" + escape(table.title) + r"}\\",
            r"\toprule", header, r"\midrule", r"\endfirsthead",
            r"\toprule", header, r"\midrule", r"\endhead",
            r"\bottomrule", r"\endlastfoot",
            "\n".join(body),
            r"\end{longtable}}",
        ]
    if table.note:
        out.append(r"{\footnotesize\textit{" + escape(table.note) + "}}")
    return "\n".join(out)


def figure_tex(figure: Figure) -> str:
    body = figure_body_tex(figure)
    if not body:
        # An absent figure states why in place of the axis (§3.4). The reason is
        # a bare phrase in the content model, so the "Not analysed" marker is
        # added exactly once here rather than baked into every reason string.
        reason = figure.absent_reason or "no data for this figure"
        return (r"\textbf{" + escape(figure.title) + r" --- not analysed.} "
                + escape(reason))
    # ``[H]`` (the ``float`` package), not ``[htbp]``: each figure is followed by
    # its own corner-point table (§4.3), and a float that drifts three pages away
    # from the numbers it belongs to breaks that pairing.
    # The optional argument is what the List of Figures carries. Without it a
    # caption that explains the figure -- which a caption in a report a reviewer
    # signs has to -- is repeated in full in the front matter, once per figure,
    # and the list stops being a list. The title alone is the entry.
    parts = [r"\begin{figure}[H]", r"\centering", body,
             r"\caption[" + escape(figure.title) + "]{" + escape(figure.title)
             + (": " + escape(figure.caption) if figure.caption else "") + "}",
             r"\end{figure}"]
    return "\n".join(parts)


def section_tex(section: Section, level: int) -> str:
    r"""One section (and its subsections), unnumbered but present in the ToC.

    ``\section*`` rather than ``\section`` because the content model already
    carries the document's own numbering ("1. Input summary", "Appendix A ..."),
    and letting LaTeX number them too would print "1 1. Input summary".
    """
    command = {0: "section", 1: "subsection", 2: "subsubsection"}.get(level, "paragraph")
    title = escape(section.title)
    out = [f"\\{command}*{{{title}}}",
           f"\\addcontentsline{{toc}}{{{command}}}{{{title}}}"]
    if section.absent_reason:
        out.append(r"\textbf{" + escape(section.absent_lead) + ".} "
                   + escape(section.absent_reason))
    for paragraph in section.body:
        out.append(paragraphs_tex(paragraph))
    for figure in section.figures:
        out.append(figure_tex(figure))
    for table in section.tables:
        out.append(table_tex(table))
    for sub in section.subsections:
        out.append(section_tex(sub, level + 1))
    return "\n\n".join(p for p in out if p)


def render_document(doc: ReportDocument) -> str:
    """The whole ``.tex`` source for ``doc``."""
    parts = [
        PREAMBLE,
        _headers(doc),
        r"\begin{document}",
        _title_page(doc),
        r"\tableofcontents",
        r"\newpage",
    ]
    parts += [section_tex(s, 0) for s in doc.sections]
    parts.append(r"\end{document}")
    return "\n\n".join(parts).rstrip() + "\n"


def render_report(project, **kwargs) -> str:
    """Build and render in one call: ``Project`` -> ``.tex`` source.

    ``kwargs`` are :func:`sloads.report.content.build_report`'s -- ``system``,
    ``generated``, ``tool_version``, ``scope``, ``deselected_case_ids`` and the
    precomputed ``module_results``/``components``.
    """
    from .content import build_report

    return render_document(build_report(project, **kwargs))


__all__ = [
    "PREAMBLE",
    "escape",
    "figure_tex",
    "paragraphs_tex",
    "render_document",
    "render_report",
    "section_tex",
    "table_tex",
]
