"""The **report spec** — the metadata of one issue of the oracle technical report.

Design note 44, OR-17: a report is a *document instance*, not a property of the
airplane. One project yields many issues — different customers, revisions and
scope selections — so this is its own dataclass with its own schema version, and
:class:`sloads.models.Project` is not touched. Note 32's OG-13/G6 promise (a
project saved by either GUI opens in the other unchanged) is therefore untouched
too, and no migration is owed.

**Where it lives.** In the issue package directory, as ``report.json`` beside the
``report.tex`` it produced (OR-28, which supersedes OR-24's placement beside the
project file). One issue, one directory, holding everything about that issue.

**What is *not* here.** The as-built stamp — fingerprint, build timestamp,
generator version — lives in the package's ``build.json`` (OR-30). Nothing in
this dataclass is ever written by the builder: ``report.json`` records what a
person typed, which is what makes it diffable and what keeps the byte-identical
rebuild gate (G-OR-16) free of a field-exclusion carve-out.

:data:`ProjectIdentity` is the one apparent exception and is not one: it records
what airplane definition the report was *authored against* (OR-21), and is
written when the report is created or deliberately re-baselined by the user --
never by a build.

Mapped to JSON by :mod:`sloads.io` (``load_report``/``save_report``), which stays
the only dataclass<->JSON mapping in the package.

**Deliberately not re-exported from** :mod:`sloads.models`. Two reasons, and the
first is decisive: this module needs :class:`sloads.units.UnitSystem` (OR-20),
and ``sloads.units`` imports ``sloads.models`` -- so a star-import here would
close the cycle ``models -> report -> units -> models`` and break the package on
import. The second is that ``sloads.models``'s surface is the *airplane* schema,
and OR-17's whole point is that a report is not part of it. Import this module by
name: ``from sloads.models.report import ReportSpec``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

from ..units import UnitSystem

#: The report spec's own schema version, independent of ``SCHEMA_VERSION``.
#:
#: **Stays at 1 for the whole of milestone 0.8.2** (OR-33). Sections add spec
#: fields as they are agreed, but no report file has shipped, so there is nothing
#: to migrate and a version bumped against no readership teaches the number to
#: mean nothing. It starts carrying information at the 0.8.2 cut.
REPORT_SCHEMA_VERSION = 1


#: The window a report date may fall in.
#:
#: Explicit because ``st.date_input`` derives its own bounds from the value it is
#: given, and a picker opened empty would otherwise refuse a date more than a
#: decade away -- an as-built revision of an old airplane is a normal thing to
#: write up.
DATE_MIN = date(1980, 1, 1)
DATE_MAX = date(2100, 12, 31)


def parse_date(text: str) -> Optional[date]:
    """``text`` as a date, or ``None`` if it is not one.

    Dates are stored as ISO strings, not :class:`date` objects: the spec is a
    JSON document that a person is expected to be able to open and edit, and a
    hand-typed value that is not a date must survive being loaded rather than
    crash the page that shows it. The GUI turns the string into a picker and
    back; this is the only place that knows the format.
    """
    try:
        return date.fromisoformat(text.strip())
    except (AttributeError, TypeError, ValueError):
        return None


@dataclass(frozen=True)
class SignatureRow:
    """One of the three signature rows: prepared, checked, approved (OR-18).

    An empty ``name`` is what makes the document a draft -- see :func:`is_draft`.
    The row is still rendered when unsigned, with a ruled blank, so the reader
    sees *that* a signature is missing rather than seeing nothing.
    """

    name: str = ""
    role: str = ""
    date: str = ""


@dataclass(frozen=True)
class RevisionRow:
    """One row of the revision history table (OR-18)."""

    date: str = ""
    revision: str = ""
    description: str = ""
    by: str = ""


@dataclass(frozen=True)
class ProjectIdentity:
    """What airplane definition this report was authored against (OR-21).

    Two different questions get two different answers, and both are kept:

    * *Is this the same airplane?* -- ``project_name`` and ``designation``,
      printed beside the anchor values (design weight, wing area, design speeds)
      that the document computes from the project at build time. This is what a
      reader of the PDF actually checks; a hex string tells them nothing.

      The anchors are **computed, never stored**: stored text goes stale the
      moment the project moves, and would be frozen in whichever unit system
      happened to be selected when it was written -- while OR-20 makes the
      document's units a property of the spec. What is stored is only what is
      needed to notice that the *subject* changed.
    * *Has the definition changed since this issue was authored?* -- the
      ``fingerprint``, which is the only thing that answers it cheaply.

    ``fingerprint_version`` is carried so that a later milestone adding a field to
    an oracle-consumed slice makes existing reports report *"cannot compare --
    stamped by an earlier fingerprint definition"* rather than crying wolf. A
    warning that fires on noise is ignored on signal.

    The fingerprint is **not a signature**: there is no key, so it detects
    accident, not tampering. It is also not the record of what was analysed --
    the Appendix A input echo is that. This is the fast comparator that says
    *go read Appendix A, something moved*.
    """

    project_name: str = ""
    designation: str = ""
    fingerprint: str = ""
    fingerprint_version: int = 0


@dataclass(frozen=True)
class ReportSpec:
    """The metadata of one issue of the oracle technical report (OR-18)."""

    title: str = ""
    report_number: str = ""
    revision: str = ""
    issue_date: str = ""
    organisation: str = ""
    customer: str = ""
    #: OR-31: the author's abstract. *Not* the computed governing-loads summary,
    #: which is built from delivered loads and is never user-selectable (OR-19).
    abstract: str = ""
    #: The report's section 1 prose. Empty means "use the generator's
    #: default"; the GUI pre-fills it, so a saved spec carries the text
    #: verbatim and a later change to the default cannot silently reword
    #: a report that has already been issued.
    introduction: str = ""
    #: The limitations and scope subsection. Pre-filled from
    #: :func:`sloads.report.methods.methods_statement`, then owned by the
    #: author -- it is a snapshot, and deliberately so: a signed issue
    #: must keep saying what it said when it was signed.
    limitations: str = ""
    distribution: str = ""
    #: Classification marking, rendered in every page footer (OR-18).
    marking: str = ""
    revisions: List[RevisionRow] = field(default_factory=list)
    prepared: SignatureRow = field(default_factory=SignatureRow)
    checked: SignatureRow = field(default_factory=SignatureRow)
    approved: SignatureRow = field(default_factory=SignatureRow)
    #: OR-20: the *document's* unit system, which is not the sidebar toggle. The
    #: sidebar governs what the analysis pages display; this governs the report,
    #: so that a spec plus a project is a complete, reproducible recipe.
    unit_system: UnitSystem = UnitSystem.IMPERIAL
    #: Workflow step keys the user deselected for this issue (OR-19). Stored by
    #: step key and never by section number, which moves as steps are added.
    #: A deselected section is still rendered, with its exclusion stated.
    excluded_steps: Tuple[str, ...] = ()
    identity: ProjectIdentity = field(default_factory=ProjectIdentity)


def default_spec() -> ReportSpec:
    """A blank, unsigned draft.

    G-OR-11 requires that a missing or unreadable report file yield exactly this
    rather than a traceback: the page must open on a project that has never had a
    report, which is every project the first time.
    """
    return ReportSpec()


def is_draft(spec: ReportSpec) -> bool:
    """True while any signature name is empty (OR-18).

    Any one missing name makes the whole document a draft -- watermark and footer
    marking -- and all three present clears it. The build never blocks on this:
    an unsigned report is fully buildable, it just says what it is. A document
    that could present itself as approved because nobody filled a field is the
    failure this exists to prevent.
    """
    return not all(row.name.strip()
                   for row in (spec.prepared, spec.checked, spec.approved))


__all__ = [
    "DATE_MAX",
    "DATE_MIN",
    "REPORT_SCHEMA_VERSION",
    "ProjectIdentity",
    "ReportSpec",
    "RevisionRow",
    "SignatureRow",
    "default_spec",
    "is_draft",
    "parse_date",
]
