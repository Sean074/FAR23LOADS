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

    **The footer is one full-width table, not three slots.** ``fancyhdr`` places
    ``[L]``, ``[C]`` and ``[R]`` independently, so nothing stops them printing
    on top of one another -- and a real marking does: "COMMERCIAL IN CONFIDENCE"
    ran straight through the load-basis sentence, leaving the two statements a
    reader most needs to trust illegible. Allocating the width with
    ``tabular*`` + ``\extracolsep{\fill}`` makes the columns share the line by
    construction rather than by fitting, so a longer marking wraps the layout's
    spacing instead of overprinting its neighbour.

    The centre names the **issuing organisation**, not the load basis. Only the
    marking and the draft sentence are owed on every page (``ORACLE_REPORT.md``
    §4); the load basis is already stated in the introduction, and the ``-ULT``
    marker is part of every units string by ``CONVENTIONS.md``, so each number
    is self-marking and a page-level restatement bought nothing. Who issued a
    loose page is the thing a reader cannot recover from the page itself.
    """
    marking = doc.spec.marking.strip()
    origin = doc.spec.organisation.strip()
    page = r"Page \thepage\ of \pageref{LastPage}"
    rows = []
    if doc.draft:
        rows.append(r"\multicolumn{3}{c}{\textbf{DRAFT --- not approved}} \\")
    rows.append(" & ".join([escape(marking) if marking else "",
                            escape(origin) if origin else "",
                            page]) + r" \\")
    footer = (r"\footnotesize\begin{tabular*}{\textwidth}"
              r"{@{\extracolsep{\fill}}lcr@{}}"
              + "".join(rows) + r"\end{tabular*}")
    return "\n".join([
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        # The footer grows a row on a draft, so make room for it rather than
        # letting the table ride up into the text block.
        r"\setlength{\footskip}{" + ("34pt" if doc.draft else "26pt") + "}",
        r"\fancyhead[L]{\small " + escape(doc.spec.report_number or doc.title) + "}",
        r"\fancyhead[C]{" + (r"\sldraftmark" if doc.draft else "") + "}",
        r"\fancyhead[R]{\small " + escape(
            ("Rev " + doc.spec.revision) if doc.spec.revision else "") + "}",
        r"\fancyfoot[C]{" + footer + "}",
        r"\renewcommand{\headrulewidth}{0.4pt}",
    ])


def _signature_block(doc: OracleDocument) -> str:
    """Prepared / checked / approved, with ruled blanks where unsigned.

    An unsigned row is *rendered*, not skipped: the reader must see that a
    signature is missing rather than see nothing where one belongs.

    **An unsigned row carries no date.** A date printed beside a ruled name
    blank reads as an approval that happened on that day and was signed
    illegibly -- the document asserting an event that did not occur, on the page
    a reader trusts most. The stored value is kept in the spec (a planned issue
    date is a legitimate thing to hold); it is the *printing* of it next to an
    absent name that is refused. The role is left alone: naming who is due to
    sign claims nothing about whether they have.
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
        signed = bool(row.name.strip())
        lines.append(" & ".join([
            escape(label),
            escape(row.name) if signed else blank,
            escape(row.role) if row.role.strip() else blank,
            escape(row.date) if signed and row.date.strip() else blank,
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
             r"\addcontentsline{toc}{subsection}{Analysis basis}",
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


def _limitations_tex(doc: OracleDocument) -> str:
    """The limitations and scope subsection (owner's decision, 2026-08-30).

    Pre-filled by the GUI from :func:`sloads.report.methods.methods_statement`
    and owned by the author thereafter, so what is rendered here is simply the
    text the spec carries -- this function does not reach for the generator's
    copy, because the resolution already happened in
    :func:`sloads.report.oracle_content.build_oracle_document` and doing it in
    two places is how the page and the document come to disagree.
    """
    if not doc.limitations.strip():
        return ""
    return "\n\n".join([
        r"\subsection*{Limitations and scope}",
        r"\addcontentsline{toc}{subsection}{Limitations and scope}",
        paragraphs_tex(doc.limitations),
    ])


def title_page_tex(doc: OracleDocument) -> str:
    """The cover: marking, identity, document control, signatures, distribution.

    Deliberately *not* the analysis basis or the not-carried list. Those moved
    to the introduction in the 2026-08-30 GUI review: both are read rather than
    glanced at, and on the cover they pushed the signature block onto a second
    sheet -- leaving the approval record on a page carrying none of the
    document's identity, which is the one page that must never travel alone.
    """
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
    # The analysis basis and the not-carried list live in the introduction, not
    # here (GUI review, 2026-08-30). Both are things a reader works *through*
    # -- five anchor rows, a fingerprint, a list of section titles -- and on the
    # cover they pushed the signature block onto a second sheet, which put the
    # approval record on a page that carries none of the document's identity.
    # The cover states who the document is and who signed it; the introduction
    # states what it was built from and what it does not carry.
    parts += [_control_table(doc.control), r"\vspace{10mm}",
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


def _listing_tex(doc: OracleDocument, command: str, title: str,
                 noun: str) -> str:
    """A front-matter list, and a sentence when it is empty.

    An empty list under a bare heading is a **silent** absence, which is the one
    thing this document does not do anywhere else: it is why a section the
    generator cannot build still appears, saying so, instead of being omitted.
    A reader looking at a heading with nothing under it cannot tell "this issue
    has no figures" from "the list failed to generate", and the second is what
    they will suspect.

    The entry is added to the contents for the same reason the abstract's is:
    two kinds of front matter treated differently in the same document reads as
    an oversight rather than a decision.
    """
    def holds_any(section) -> bool:
        # Recursive: a table one level down still puts a line in the list, and
        # a document that then printed "contains no tables" would be stating
        # the opposite of what the reader is looking at.
        return bool(getattr(section, noun, None)) or any(
            holds_any(child) for child in getattr(section, "subsections", ()))

    empty = not any(holds_any(section) for section in doc.sections)
    parts = [command, r"\addcontentsline{toc}{section}{" + escape(title) + "}"]
    if empty:
        parts.append(r"{\small\itshape This issue contains no "
                     + escape(noun) + r".}")
    return "\n\n".join(parts)


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
        # The document sets \parskip to 0.6em, and a contents list inherits it --
        # seventeen entries spaced like paragraphs filled the page on their own
        # and pushed the List of Tables onto a sheet of its own. Confined to a
        # group so the body's paragraph spacing is untouched.
        r"{\setlength{\parskip}{0pt}",
        r"\tableofcontents",
        _listing_tex(doc, r"\listoffigures", "List of Figures", "figures"),
        _listing_tex(doc, r"\listoftables", "List of Tables", "tables"),
        r"}",
        r"\newpage",
    ]
    # Section 1 is the introduction; the analysis basis and the not-carried
    # list follow it as unnumbered subsections. Unnumbered because
    # ``oracle_content.section_number`` owns numbering and a hand-numbered
    # "1.1" here would be a second numbering scheme that cannot renumber
    # itself when a section is inserted above it.
    for index, section in enumerate(doc.sections):
        parts.append(section_tex(section, 0))
        if index == 0:
            parts += [_provenance_block(doc), _limitations_tex(doc)]
    parts.append(r"\end{document}")
    return "\n\n".join(p for p in parts if p).rstrip() + "\n"


__all__ = [
    "ORACLE_PREAMBLE_EXTRA",
    "headers_tex",
    "render_oracle_document",
    "title_page_tex",
]
