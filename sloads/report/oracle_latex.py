r"""LaTeX for the **oracle technical report** -- its furniture, and nothing else.

Design note 44, OR-4. This module owns what makes the oracle report *this
document*: its title page (the OR-18 block), its running heads and classification
footer, its DRAFT state, and its front matter (contents, figures, tables).

**It defines no table or figure emitter.** ``table_tex``, ``figure_tex``,
``section_tex`` and ``paragraphs_tex`` are imported from :mod:`sloads.report.latex`
and used as-is. Two documents, one table emitter: the column-width model, the
``longtable`` header machinery and the not-analysed marking exist once, so a fix
to any of them reaches both reports. This is also what makes the note's strategic
intent affordable -- when the main report is rebuilt on this one (band B2), there
is one emitter to merge, not two that have drifted for a milestone.

**The watermark adds no package.** ``PREAMBLE`` already loads ``pgfplots``
(which loads TikZ) and ``fancyhdr``, so DRAFT is a TikZ overlay node and a footer
sentence, not ``draftwatermark``. ``SUMMARY_REPORT.md`` §2 limits the document to
a standard distribution, and a preamble shared with the summary report is not the
place to acquire a dependency that four lines of existing machinery replace.

Note that ``remember picture, overlay`` needs **two LaTeX passes** to position
itself; ``tectonic`` and ``latexmk`` do that automatically, a single bare
``pdflatex`` run does not.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .latex import PREAMBLE, escape, paragraphs_tex, section_tex
from .oracle_content import OracleDocument

#: Preamble additions this document needs on top of the shared ``PREAMBLE``.
#: No ``\usepackage`` line: everything used here is already loaded.
ORACLE_PREAMBLE_EXTRA = r"""
% --- oracle report additions (design note 44, OR-18) ----------------------
% The DRAFT overlay. Grey and rotated so it cannot be mistaken for content,
% and never the sole carrier of the meaning -- the footer sentence below says
% it in words, which is what keeps the document legible in greyscale and to a
% screen reader (SUMMARY_REPORT.md 4.3/4.4).
\newcommand{\sldraftmark}{\begin{tikzpicture}[remember picture,overlay]
  \node[rotate=45,scale=7,gray,opacity=0.10] at (current page.center) {DRAFT};
\end{tikzpicture}}
"""


def _control_table(rows: Sequence[Tuple[str, str]]) -> str:
    """A borderless two-column block for the title page.

    Not a ``Table``: the content model's tables are numbered, captioned and
    listed in the List of Tables, and the title block is none of those things.
    """
    if not rows:
        return ""
    body = r" \\".join(
        r"\textbf{" + escape(label) + "} & " + escape(value)
        for label, value in rows)
    return (r"\begin{tabular}{@{}p{0.34\textwidth}p{0.58\textwidth}@{}}"
            + body + r" \\\end{tabular}")


def headers_tex(doc: OracleDocument) -> str:
    r"""Running heads and footers, including the classification marking.

    The marking is rendered on **every page** (OR-18): a classified document
    whose marking appears only on the cover is one photocopied page away from
    being an unmarked document.
    """
    marking = doc.spec.marking.strip()
    # Three statements are owed on every page -- the marking, the load basis and
    # (when unsigned) DRAFT -- and three of them will not fit across one footer
    # line: the first attempt overprinted the marking and the draft sentence on
    # top of each other. The centre slot is therefore stacked, and each line is
    # kept short enough to clear the left and right slots.
    basis = "ULTIMATE loads --- SF stated per case"
    centre_lines = ([r"\textbf{DRAFT --- not approved}"] if doc.draft else []) + [
        escape(basis)]
    centre = (r"\shortstack{" + r"\\".join(centre_lines) + "}"
              if len(centre_lines) > 1 else centre_lines[0])
    return "\n".join([
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        # The footer grows a line on a draft, so make room for it rather than
        # letting the stack ride up into the text block.
        r"\setlength{\footskip}{" + ("34pt" if doc.draft else "26pt") + "}",
        r"\fancyhead[L]{\small " + escape(doc.spec.report_number or doc.title) + "}",
        r"\fancyhead[C]{" + (r"\sldraftmark" if doc.draft else "") + "}",
        r"\fancyhead[R]{\small " + escape(
            ("Rev " + doc.spec.revision) if doc.spec.revision else "") + "}",
        r"\fancyfoot[L]{\small " + (escape(marking) if marking else "") + "}",
        r"\fancyfoot[C]{\small " + centre + "}",
        r"\fancyfoot[R]{\small Page \thepage\ of \pageref{LastPage}}",
        r"\renewcommand{\headrulewidth}{0.4pt}",
    ])


def _signature_block(doc: OracleDocument) -> str:
    """Prepared / checked / approved, with ruled blanks where unsigned.

    An unsigned row is *rendered*, not skipped: the reader must see that a
    signature is missing rather than see nothing where one belongs.
    """
    spec = doc.spec
    rows = [("Prepared by", spec.prepared), ("Checked by", spec.checked),
            ("Approved by", spec.approved)]
    lines = [r"\begin{tabular}{@{}p{0.22\textwidth}p{0.30\textwidth}"
             r"p{0.22\textwidth}p{0.18\textwidth}@{}}",
             r"\toprule",
             r"\textbf{Role} & \textbf{Name} & \textbf{Function} & \textbf{Date} \\",
             r"\midrule"]
    blank = r"\rule{0pt}{2.2ex}\hrulefill"
    for label, row in rows:
        lines.append(" & ".join([
            escape(label),
            escape(row.name) if row.name.strip() else blank,
            escape(row.role) if row.role.strip() else blank,
            escape(row.date) if row.date.strip() else blank,
        ]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def _provenance_block(doc: OracleDocument) -> str:
    """Human anchors plus the fingerprint (OR-21).

    Both, because they answer different questions: the anchors answer *is this
    the same airplane* for a person holding a drawing, and the fingerprint
    answers *has anything moved* for a person holding a previous issue. Neither
    substitutes for the other, and the fingerprint is explicitly not a signature.
    """
    if not doc.anchors and not doc.fingerprint:
        return ""
    parts = [r"\subsection*{Analysis basis}",
             _control_table(doc.anchors)]
    if doc.fingerprint:
        parts.append(
            r"{\footnotesize Input fingerprint \texttt{"
            + escape(doc.fingerprint[:16]) + r"} (definition v"
            + escape(str(doc.fingerprint_version))
            + r"). This detects an accidental change to the analysis inputs; "
            + r"it is not a signature, and the input echo remains the "
            + r"definitive record of what was analysed.}")
    return "\n\n".join(p for p in parts if p)


def _gaps_block(doc: OracleDocument) -> str:
    """What this issue does not carry, stated on the title page (OR-19).

    ``SUMMARY_REPORT.md`` §3.4's filtered-export rule at section level: an
    analyst never receives a reduced document without being told on the face of
    it, rather than by noticing an absence.

    **The three gap states are not listed alike.** An exclusion and an absence
    are facts about *this issue* -- somebody's choice, or this project's data --
    and belong itemised where a reader checks what they were sent. A section the
    generator cannot build yet is a fact about the *tool*, identical in every
    issue it produces, and itemising thirteen of them would bury the two that
    are about the reader's own report under a list that says the same thing
    thirteen times.
    """
    from .oracle_content import SectionState

    per_issue = [(entry.title, entry.reason) for entry in doc.plan
                 if entry.state in (SectionState.EXCLUDED, SectionState.ABSENT)]
    pending = [entry.title for entry in doc.plan
               if entry.state is SectionState.NOT_IMPLEMENTED]
    parts = []
    if per_issue:
        items = "\n".join(r"\item " + escape(f"{title} --- {reason}")
                          for title, reason in per_issue)
        parts += [r"\subsection*{Sections not carried by this issue}",
                  r"\begin{itemize}\setlength{\itemsep}{0pt}", items,
                  r"\end{itemize}"]
    if pending:
        parts += [
            r"\subsection*{Sections not yet produced by this tool}",
            escape(
                f"{len(pending)} analysis sections are not yet implemented in "
                "this revision of the report generator. Each appears in the body "
                "below, saying so in place of its analysis: ")
            + escape(", ".join(pending)) + ".",
        ]
    return "\n\n".join(parts)


def title_page_tex(doc: OracleDocument) -> str:
    """The cover: identity, control block, provenance, exclusions, signatures."""
    # Deliberately **not** ``\begin{titlepage}``. That environment resets the
    # page counter when it ends, so a cover that runs to two sheets makes the
    # next page "Page 1 of 4" on the third sheet -- and it suppresses the page
    # style, which would drop the classification marking from the one page most
    # likely to be photocopied on its own. OR-18 wants the marking everywhere.
    parts: List[str] = [
        r"\vspace*{0.5cm}",
    ]
    marking = doc.spec.marking.strip()
    if marking:
        parts.append(r"{\large\bfseries " + escape(marking) + r"}\par\vspace{6mm}")
    parts += [
        r"{\Huge\bfseries " + escape(doc.title) + r"}\par\vspace{4mm}",
        r"{\large " + escape(doc.spec.identity.project_name
                             or doc.spec.customer or "") + r"}\par\vspace{8mm}",
    ]
    if doc.draft:
        parts.append(r"{\large\bfseries DRAFT --- not approved}\par\vspace{4mm}")
    parts += [_control_table(doc.control), r"\vspace{8mm}",
              _provenance_block(doc), r"\vspace{6mm}",
              _gaps_block(doc), r"\vspace{6mm}",
              _signature_block(doc)]
    if doc.spec.distribution.strip():
        parts += [r"\vspace{6mm}", r"{\footnotesize\textbf{Distribution:} "
                  + escape(doc.spec.distribution) + "}"]
    parts.append(r"\clearpage")
    return "\n\n".join(p for p in parts if p)


def _abstract_tex(doc: OracleDocument) -> str:
    """The author's abstract (OR-31).

    Rendered even when empty, saying so: a report whose abstract is missing has
    an author who has not written it yet, and printing nothing would hide that
    from the reviewer whose job is to notice.
    """
    body = doc.abstract.strip() or (
        "No abstract has been written for this issue.")
    return "\n\n".join([r"\section*{Abstract}",
                        r"\addcontentsline{toc}{section}{Abstract}",
                        paragraphs_tex(body)])


def render_oracle_document(doc: OracleDocument) -> str:
    """The whole ``.tex`` source for ``doc``.

    Contents, figures and tables are all listed from the first iteration, even
    while the last two are empty (OR-34): an empty list is an accurate statement,
    and a document that silently drops its own front matter when incomplete is
    harder to trust than one that shows it.
    """
    parts = [
        PREAMBLE,
        ORACLE_PREAMBLE_EXTRA,
        headers_tex(doc),
        r"\begin{document}",
        title_page_tex(doc),
        _abstract_tex(doc),
        r"\newpage",
        r"\tableofcontents",
        r"\listoffigures",
        r"\listoftables",
        r"\newpage",
    ]
    parts += [section_tex(s, 0) for s in doc.sections]
    parts.append(r"\end{document}")
    return "\n\n".join(p for p in parts if p).rstrip() + "\n"


__all__ = [
    "ORACLE_PREAMBLE_EXTRA",
    "headers_tex",
    "render_oracle_document",
    "title_page_tex",
]
