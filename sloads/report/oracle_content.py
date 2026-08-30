"""What the **oracle technical report** says, in the renderer-agnostic model.

Design note 44. This module owns the report's *content*: which sections exist,
what state each is in, and the front matter's prose. It emits no LaTeX -- that is
:mod:`sloads.report.oracle_latex` -- and it recomputes nothing: every number it
will eventually show comes from a ``ModuleResult`` the analysis already produced
(OR-6). Iteration 1 delivers the front matter (OR-31); the analysis sections
exist from the first commit as stated placeholders (OR-32).

**The section set is derived, never listed** (OR-2, gate G-OR-2). The owner is
:func:`sloads.workflow.oracle_steps`, and the rule is *a step is an analysis
section iff it produces a result* -- it has a ``module``. An input-only step
(``aero_coefficients`` today) has nothing to report and belongs to the input
sections, not to the analysis body. Adding a module-backed step to the workflow
therefore adds a section here with no edit to this file, which is the same
property note 32's G2 gives the GUI's page set.

**Numbering has one owner** and it is :func:`section_number`, derived from
position. Section references are built from it and never written as a literal --
a reference that does not move when a section is inserted above it is a reference
to the wrong section (``SUMMARY_REPORT.md`` §4.7, review F-R2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, List, Optional, Sequence, Tuple

from .. import workflow as wf
from ..models import Project
from ..models.report import ReportSpec, is_draft
from ..units import UnitSystem
from .content import Section

#: Step keys whose analysis section the generator can actually build.
#:
#: Empty in iteration 1: the front matter is the whole document, and every
#: analysis section renders as :attr:`SectionState.NOT_IMPLEMENTED`. Each agreed
#: OR-8 iteration adds its key here, which is what turns a placeholder into a
#: section. Keeping it a set rather than a code branch means the preflight table
#: and the document agree by construction about what is built.
IMPLEMENTED: FrozenSet[str] = frozenset()

#: The document's fixed front matter, in order, ahead of the analysis body.
FRONT_SECTIONS: Tuple[str, ...] = ("Introduction",)


class SectionState(Enum):
    """Why a section is, or is not, showing its analysis.

    Four states, and keeping them apart is the point (OR-32). Each answers a
    different question about *whose* decision produced the gap, and collapsing
    any two would make the document assert something untrue about the reader's
    own data or about a colleague's editorial choice.
    """

    INCLUDED = "included"
    #: The tool cannot produce it yet -- nobody's decision, and not a data gap.
    NOT_IMPLEMENTED = "not yet implemented"
    #: A person deselected it for this issue (OR-19).
    EXCLUDED = "excluded"
    #: The inputs it needs are missing from the project (OR-5).
    ABSENT = "absent"


#: The lead phrase and sentence each non-included state renders, owned once so
#: the document and the page's preflight cannot word the same state two ways.
#:
#: The **lead** matters as much as the sentence. The renderer prints it in bold
#: ahead of the reason, and it is the part a reader skimming the document
#: actually takes in -- so three states sharing one lead would say the same thing
#: three times however carefully the sentences differ. The first build of this
#: document did exactly that: every placeholder read "Not analysed", which is
#: *absence*'s wording, telling the reader their inputs were missing when it was
#: the generator that was incomplete.
#:
#: The sentences open a sentence, capitalised: the renderer prints them after
#: the bold lead and a full stop, so a lower-case first word reads as a
#: typesetting fault on the page a reader is being asked to trust.
STATE_TEXT = {
    SectionState.NOT_IMPLEMENTED: (
        "Not yet implemented",
        "This revision of the report generator does not yet produce this "
        "section. Nothing about this project or this issue is missing."),
    SectionState.EXCLUDED: (
        "Not included in this issue",
        "Excluded by user selection at report generation."),
    SectionState.ABSENT: (
        "Not analysed",
        "The inputs this section needs are not present in the project."),
}

#: Just the sentences, for the preflight table and anything showing one alone.
STATE_REASON = {state: text for state, (_lead, text) in STATE_TEXT.items()}


@dataclass(frozen=True)
class SectionPlan:
    """One row of the document's plan: what the section is and why.

    ``selected`` and ``inputs_present`` are carried alongside ``state`` rather
    than folded into it, because the preflight table must keep showing both even
    where a higher-precedence state hides them. An analyst who deselected a
    section wants to see that their choice registered, even in a build where the
    generator could not have produced it anyway.
    """

    step_key: str
    number: str
    title: str
    state: SectionState
    reason: str
    #: The bold lead the document prints ahead of :attr:`reason`.
    lead: str = ""
    selected: bool = True
    inputs_present: bool = True

    @property
    def included(self) -> bool:
        return self.state is SectionState.INCLUDED


def analysis_steps() -> List[wf.WorkflowStep]:
    """The oracle steps that produce a result, in workflow order (G-OR-2)."""
    return [step for step in wf.oracle_steps() if step.module]


def section_number(index: int) -> str:
    """The printed number of the ``index``-th numbered section, 0-based.

    The single numbering owner. Front matter occupies the first slots, so the
    analysis body starts after it and renumbers itself when a front section is
    added -- which is the whole reason this is a function and not a literal.
    """
    return str(index + 1)


def section_ref(plan: Sequence[SectionPlan], step_key: str) -> str:
    """``"section 4"`` for a step, or a plain description if it has none."""
    for entry in plan:
        if entry.step_key == step_key:
            return f"section {entry.number}"
    return "a section this issue does not carry"


def _inputs_present(project: Project, step: wf.WorkflowStep) -> bool:
    """Whether every slice ``step`` declares it requires is populated.

    Deliberately a *slice presence* test and not a trial run: OR-6 forbids this
    module from computing anything, and a preflight that ran every module to
    decide what to print would be doing the analysis twice.
    """
    return all(getattr(project, attr, None) is not None for attr in step.requires)


def section_plan(project: Project, spec: ReportSpec, *,
                 implemented: FrozenSet[str] = IMPLEMENTED) -> List[SectionPlan]:
    """The whole document's sections, front matter first (G-OR-2).

    **Precedence.** ``EXCLUDED`` is decided first, because a deselected section
    is not printed at all and there is no reader to owe a reason to (GUI review,
    2026-08-30). Among the states that *do* print, ``NOT_IMPLEMENTED`` outranks
    ``ABSENT``: a section the tool cannot produce must not claim the reader's
    inputs are missing. Once every section is implemented that ordering stops
    mattering and ``ABSENT`` is the only one left.
    """
    plan: List[SectionPlan] = []
    for offset, title in enumerate(FRONT_SECTIONS):
        plan.append(SectionPlan(step_key="", number=section_number(offset),
                                title=title, state=SectionState.INCLUDED,
                                reason=""))
    # The number is assigned from position among the sections that will
    # *render*, not from position in the workflow. A deselected section is
    # omitted entirely (GUI review, 2026-08-30), so numbering by workflow
    # position would leave a gap in the printed sequence and every cross
    # reference after it would name the wrong section.
    printed = len(FRONT_SECTIONS)
    for step in analysis_steps():
        selected = step.key not in spec.excluded_steps
        present = _inputs_present(project, step)
        if not selected:
            state = SectionState.EXCLUDED
        elif step.key not in implemented:
            state = SectionState.NOT_IMPLEMENTED
        elif not present:
            state = SectionState.ABSENT
        else:
            state = SectionState.INCLUDED
        if state is SectionState.EXCLUDED:
            number = ""
        else:
            number = section_number(printed)
            printed += 1
        plan.append(SectionPlan(
            step_key=step.key, number=number,
            title=step.title, state=state, reason=STATE_REASON.get(state, ""),
            lead=STATE_TEXT.get(state, ("", ""))[0],
            selected=selected, inputs_present=present))
    return plan


@dataclass(frozen=True)
class OracleDocument:
    """The whole oracle report, ready for :mod:`sloads.report.oracle_latex`."""

    title: str
    spec: ReportSpec
    draft: bool
    #: (label, value) rows of the title page's document-control block.
    control: List[Tuple[str, str]] = field(default_factory=list)
    #: (label, value) human identity rows (OR-21), computed at build time.
    anchors: List[Tuple[str, str]] = field(default_factory=list)
    fingerprint: str = ""
    fingerprint_version: int = 0
    abstract: str = ""
    #: The limitations and scope subsection's text, already resolved to either
    #: the author's version or the generator's default.
    limitations: str = ""
    units_note: str = ""
    plan: List[SectionPlan] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    system: UnitSystem = UnitSystem.IMPERIAL


_INTRODUCTION = [
    "This report presents the FAR Part 23 Subpart C structural design loads "
    "computed for the airplane identified on the title page. It is generated "
    "directly from the analysis model: every number it contains is a value the "
    "analysis produced, reproduced here without recomputation, so that the "
    "document and the tool cannot disagree.",

    "The method is the FAR 23 LOADS suite of Hal C. McMaster (Aero Science "
    "Software), as replicated by sloads. The governing equations, and the "
    "worked example the replication is held to within 0.1 per cent, are given "
    "in the theory manual (reference/FAR23Loads_Code.pdf, Appendix A); the "
    "module data flow is described in DOT/FAA/AR-96/46 "
    "(reference/FAR23Loads_UserGuide.pdf, Table 2.2). The certification basis "
    "is 14 CFR Part 23 Subpart C.",

    "All delivered loads in this report are ULTIMATE. Every load-bearing "
    "quantity states its units with the -ULT marker, and every load case states "
    "the safety factor applied to it together with the basis of that factor. "
    "Quantities that are not loads are neither scaled nor marked.",

]


def default_introduction() -> str:
    """The introduction the GUI pre-fills, as editable text.

    Returned as one string rather than the paragraph list because that is what
    the author edits and what the spec stores. The generator's copy is a
    *starting point*: once a report is issued, its introduction is whatever its
    author wrote, and a later improvement here must not silently reword a
    document somebody has already signed.
    """
    return "\n\n".join(_INTRODUCTION)


#: The statement's own heading, stripped from the report's copy.
_LIMITATIONS_BANNER = "METHODS AND LIMITATIONS"

#: Blocks of the shared statement the report does not pre-fill (owner's
#: decision, 2026-08-30). Four of them describe the *tool* -- how it is verified,
#: how its arithmetic is done, which oracle deviations are approved, where it
#: came from -- rather than the limits of this issue; the other two are already
#: stated in the document, the category in the analysis basis and the units in
#: the manifest's opening statement.
#:
#: **Filtered here, never in** :mod:`sloads.report.methods`. That statement is
#: the single owner for the CSV and deck exports as well, and dropping blocks at
#: the source would silently thin what a forwarded file carries -- which is the
#: one thing an in-band self-describing block exists to prevent. This is the
#: report's *pre-fill*, and the author can put any of it back.
_LIMITATIONS_DROPPED = (
    "PROVENANCE", "UNITS", "CATEGORY", "VERIFICATION", "MATH",
    "APPROVED CORRECTIONS",
)


def default_limitations(project: Project) -> str:
    """The limitations and scope text the GUI pre-fills.

    Taken from :func:`sloads.report.methods.methods_statement` -- the single
    owner of that statement across every export channel -- so the report opens
    saying the same thing the CSVs and the decks say. Its own
    "METHODS AND LIMITATIONS" banner is stripped: the subsection already carries
    that title, and printing it twice reads as a paste.

    From then on the author owns the text (owner's decision, 2026-08-30). That
    makes it a **snapshot**: it will not track a later change to the project or
    to the shared statement, which is the price of a signed issue continuing to
    say what it said when it was signed.
    """
    from .methods import methods_statement

    text = methods_statement(project)
    kept = [para for para in text.split("\n\n")
            if para.strip()
            and not para.lstrip().startswith(_LIMITATIONS_BANNER)
            and not para.lstrip().startswith(_LIMITATIONS_DROPPED)]
    return "\n\n".join(kept).strip()


def build_oracle_document(
    project: Project,
    spec: ReportSpec,
    *,
    implemented: FrozenSet[str] = IMPLEMENTED,
    anchors: Optional[List[Tuple[str, str]]] = None,
    fingerprint: str = "",
    fingerprint_version: int = 0,
) -> OracleDocument:
    """Build the document from a project and a report spec.

    ``anchors``/``fingerprint`` are passed in rather than computed here so this
    module stays free of :mod:`sloads.io` and the field registry, and so a caller
    that has already computed them does not pay twice.

    The unit system is read from ``spec`` and from nowhere else (OR-20, G-OR-12):
    a report plus a project is a complete, reproducible recipe, and the sidebar
    toggle governs what the *analysis pages* display, which is a different
    question with a different owner.
    """
    plan = section_plan(project, spec, implemented=implemented)
    system = spec.unit_system

    intro_text = spec.introduction.strip() or default_introduction()
    sections: List[Section] = [
        Section(f"{plan[0].number}. Introduction",
                body=[p for p in intro_text.split("\n\n") if p.strip()]),
    ]
    for entry in plan[len(FRONT_SECTIONS):]:
        # A deselected section is not printed at all -- no heading, no reason
        # (owner's decision, GUI review 2026-08-30). It keeps its row in the
        # plan so the page's preflight still shows the choice registering.
        if entry.state is SectionState.EXCLUDED:
            continue
        sections.append(Section(
            f"{entry.number}. {entry.title}",
            absent_reason="" if entry.included else entry.reason,
            absent_lead=entry.lead or "Not analysed",
        ))

    control = [
        ("Report number", spec.report_number or "not assigned"),
        ("Revision", spec.revision or "-"),
        ("Issue date", spec.issue_date or "not stated"),
        ("Issuing organisation", spec.organisation or "not stated"),
        ("Customer / programme", spec.customer or "not stated"),
    ]
    return OracleDocument(
        title=spec.title or "FAR 23 structural design loads",
        spec=spec,
        draft=is_draft(spec),
        control=control,
        anchors=list(anchors or []),
        fingerprint=fingerprint,
        fingerprint_version=fingerprint_version,
        abstract=spec.abstract,
        limitations=(spec.limitations.strip()
                     or default_limitations(project)),
        units_note=("All values are stated in SI units." if system is UnitSystem.SI
                    else "All values are stated in Imperial units."),
        plan=plan,
        sections=sections,
        system=system,
    )


__all__ = [
    "FRONT_SECTIONS",
    "IMPLEMENTED",
    "STATE_REASON",
    "STATE_TEXT",
    "OracleDocument",
    "SectionPlan",
    "SectionState",
    "analysis_steps",
    "build_oracle_document",
    "default_introduction",
    "default_limitations",
    "section_number",
    "section_plan",
    "section_ref",
]
