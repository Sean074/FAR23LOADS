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

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from .. import workflow as wf
from ..models import Project
from ..models.report import ReportSpec, is_draft
from ..models.results import ModuleResult
from ..units import UnitSystem
from .content import Section

#: Step keys whose analysis section the generator can actually build.
#:
#: Each agreed OR-8 iteration adds its keys here, which is what turns a
#: placeholder into a section. Keeping it a set rather than a code branch means
#: the preflight table and the document agree by construction about what is
#: built. Iteration 1 was empty (front matter only); iteration 2 adds the four
#: steps of section 2, Loads Configuration.
IMPLEMENTED: FrozenSet[str] = frozenset({
    "configuration_layout", "weight_mass", "structural_speeds",
    "flight_envelope", "wing_loads",
})

#: The document's fixed front matter, in order, ahead of the analysis body.
FRONT_SECTIONS: Tuple[str, ...] = ("Introduction",)

#: Step key -> the heading the **document** prints for it.
#:
#: Separate from :attr:`sloads.workflow.WorkflowStep.title`, which is the oracle
#: GUI's navigation label, and the two are not the same kind of name (owner, GUI
#: review 2026-08-30). A reader of the PDF has no concept of sloads or its steps
#: -- the workflow is our machinery, not their subject -- and with the step title
#: used directly, renaming a nav item would silently retitle a report somebody
#: has already signed. Both directions are guarded against
#: :func:`analysis_steps`, so a new module-backed step fails the suite until its
#: document title is chosen deliberately.
DOCUMENT_TITLES = {
    "configuration_layout": "Geometry",
    "weight_mass": "Weight and Mass Properties",
    "structural_speeds": "Structural Design Speeds",
    "flight_envelope": "Flight Envelope",
    "wing_loads": "Wing Loads",
    "fuselage_loads": "Fuselage Loads",
    "tail_loads": "Tail Loads",
    "aileron_loads": "Aileron Loads",
    "flap_loads": "Flap Loads",
    "tab_loads": "Tab Loads",
    "engine_mount": "Engine Mount Loads",
    "one_engine_out": "One Engine Inoperative",
    "landing_loads": "Landing Gear Loads",
}


@dataclass(frozen=True)
class SectionGroup:
    """Several steps printed as subsections of one numbered section."""

    key: str
    title: str
    members: Tuple[str, ...]


#: The groupings the document prints, in order.
#:
#: Declared as data rather than as a branch in :func:`section_plan`, so a later
#: grouping needs no new logic and the guard tests read the same table the
#: builder does. Members must be **contiguous in workflow order** -- a group
#: that skipped over a step would print that step before or after its own
#: siblings while claiming to collect them, and :func:`section_plan` has no
#: honest number to give it. Guarded.
SECTION_GROUPS: Tuple[SectionGroup, ...] = (
    SectionGroup(
        key="loads_configuration",
        title="Loads Configuration",
        members=("configuration_layout", "weight_mass", "structural_speeds",
                 "flight_envelope"),
    ),
)

#: The appendix that echoes the analysed inputs, referred to by name once built.
INPUT_ECHO = "Input echo"

#: The appendix carrying the wing loads station by station (OR-56).
WING_LOAD_STATIONS = "Wing loads by station"

#: The lead paragraphs a group prints under its own heading, before its
#: subsections. Keyed by :attr:`SectionGroup.key`.
#:
#: ``{input_echo}`` is filled by :func:`group_prose` from what the document
#: actually carries; a literal "Appendix A" here would be a cross-reference
#: written as a literal, which is the thing :func:`section_number` exists to
#: prevent one level up -- and today it would point at nothing, while colliding
#: with the theory manual's own Appendix A that the introduction cites by name.
GROUP_PROSE = {
    "loads_configuration": (
        # The owner's wording, 2026-08-30. Corrected on the way in: the first
        # sentence carried both verbs ("states summarizes"), and "and payloads"
        # promised a breakdown section 2.2 does not print -- ``weight_onecg``
        # returns weight, CG and inertias per loading, not payloads.
        "This section summarizes airplane configuration for the loads analysis. "
        "Provided are the wing geometry distributed over, the weight and mass "
        "properties assessed, the structural design speeds and limit manoeuvre "
        "load factors, and the flight envelope those speeds and factors bound. "
        "This defines the loads configuration for this analysis.",

        "Every value below is reproduced from the analysis as computed"
        "{input_echo}; nothing in this section is re-derived.",
    ),
}


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
    #: The :class:`SectionGroup` this row belongs to, on the group's own row and
    #: on each of its members; empty for an ungrouped step.
    group_key: str = ""
    #: True on the group's own row, which carries no step and no state of its
    #: own -- the states belong to its members.
    is_group: bool = False

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


def subsection_number(parent: str, index: int) -> str:
    """``("2", 0) -> "2.1"`` -- the numbering owner's child form.

    Here rather than inlined at the one call site so that the parent and child
    schemes cannot drift apart, and so a test can assert the relationship
    without reproducing it.
    """
    return f"{parent}.{index + 1}"


def heading(number: str, title: str) -> str:
    """The printed heading text: ``"2. Loads Configuration"``, ``"2.1 Geometry"``.

    Top-level numbers take a full stop, subsection numbers do not -- ordinary
    technical-report typography, owned once so a section and its own
    cross-reference cannot be styled two ways.
    """
    return f"{number} {title}" if "." in number else f"{number}. {title}"


def group_for(step_key: str) -> Optional[SectionGroup]:
    """The :class:`SectionGroup` ``step_key`` belongs to, or ``None``."""
    for group in SECTION_GROUPS:
        if step_key in group.members:
            return group
    return None


def document_title(step: wf.WorkflowStep) -> str:
    """The heading the document prints for ``step`` (:data:`DOCUMENT_TITLES`).

    Falls back to the workflow title only so that a step added without a
    document title still *renders*; the guard test is what stops it shipping.
    """
    return DOCUMENT_TITLES.get(step.key, step.title)


#: What a reference to something this issue does not carry reads as.
#:
#: One wording for both kinds of dangling reference -- a deselected or unbuilt
#: section, and an appendix that does not exist yet -- so the document cannot
#: describe the same situation two ways.
NOT_CARRIED = "a section this issue does not carry"

@dataclass(frozen=True)
class Appendix:
    """One appendix slot: what it holds, and whether the generator builds it yet.

    ``step_key`` names the analysis step the appendix is a second projection of,
    so its state follows that step's -- an appendix of wing loads for a project
    with no wing loads must say the same thing the section says, not print an
    empty table. Empty for an appendix that stands on its own.
    """

    title: str
    step_key: str = ""
    built: bool = False


#: The appendices the document prints, in order. **Position is the letter.**
#:
#: The Appendix A input echo (note 44 §339) is agreed and not built, and it holds
#: its slot anyway (OR-50). Lettering is derived from position, so shipping the
#: wing-load appendix into an empty tuple would print it as Appendix A today and
#: move it to B the moment the echo lands -- and an issue signed in between would
#: disagree with its own reissue. A reserved slot renders its OR-32 state, which
#: is the mechanism a not-yet-built *section* already uses, rather than a second
#: way of saying the same thing.
APPENDICES: Tuple[Appendix, ...] = (
    Appendix(INPUT_ECHO),
    Appendix(WING_LOAD_STATIONS, step_key="wing_loads", built=True),
)


def appendix_letter(title: str) -> str:
    """``"B"`` -- the letter position gives ``title``, built or not."""
    for index, appendix in enumerate(APPENDICES):
        if appendix.title == title:
            return chr(ord("A") + index)
    return ""


def appendix_ref(title: str) -> str:
    """``"Appendix B"`` once ``title`` is **built**, else ``""``.

    Reserving a slot letters an appendix; it does not make it referable. A
    sentence pointing the reader at a page that says "not yet implemented" is
    worse than one that points nowhere, so the reservation is visible in the
    lettering and invisible in the prose until there is something to read.
    """
    for appendix in APPENDICES:
        if appendix.title == title:
            return f"Appendix {appendix_letter(title)}" if appendix.built else ""
    return ""


def see_appendix(title: str) -> str:
    """``" (see Appendix A)"``, or nothing at all when it is not carried.

    The **whole parenthetical** is conditional, not just the name inside it: a
    sentence ending "...as computed (see a section this issue does not carry)"
    is worse than one that simply does not point anywhere. A forward reference
    to a *section* reads well degraded because it stands as its own clause; a
    parenthetical aside does not.
    """
    name = appendix_ref(title)
    return f" (see {name})" if name else ""


def appendix_heading(title: str) -> str:
    """``"Appendix B: Wing loads by station"`` -- the printed heading.

    An appendix is lettered and never renumbers, which is why it is not in
    :func:`section_number`'s sequence; the heading form still has one owner so a
    reserved slot and a built one cannot be styled two ways.
    """
    return f"Appendix {appendix_letter(title)}: {title}"


def group_prose(group_key: str) -> List[str]:
    """A group's lead paragraphs, with its references resolved.

    Resolved here rather than written into :data:`GROUP_PROSE` because the
    reference depends on what the document actually carries, and a paragraph
    stating its own cross-reference as a literal is the defect
    :func:`section_number` exists to prevent, one level up.
    """
    return [paragraph.format(input_echo=see_appendix(INPUT_ECHO))
            for paragraph in GROUP_PROSE.get(group_key, ())]


def section_ref(plan: Sequence[SectionPlan], step_key: str) -> str:
    """``"section 4"`` for a step, or a plain description if it has none.

    A deselected section has no number, so it is named the same way a section
    this issue never carried is: the reader is not told about a choice the
    author made (GUI review, 2026-08-30).
    """
    for entry in plan:
        if entry.step_key == step_key and entry.number:
            return f"section {entry.number}"
    return NOT_CARRIED


def subsection_ref(plan: Sequence[SectionPlan], step_key: str,
                   index: int) -> str:
    """``"section 3.1"`` -- a cross-reference to one subsection of a step.

    A step that renders as subsections is still one plan row, so its children
    have no rows of their own to look up; the number is composed from the
    parent's through the same owner that printed it. Written as a function for
    the reason :func:`section_ref` is: a "3.1" typed into prose is a reference
    that will not move when a section is inserted above it (F-R2).
    """
    for entry in plan:
        if entry.step_key == step_key and entry.number:
            return f"section {subsection_number(entry.number, index)}"
    return NOT_CARRIED


def _inputs_present(project: Project, step: wf.WorkflowStep) -> bool:
    """Whether every slice ``step`` declares it requires is populated.

    Deliberately a *slice presence* test and not a trial run: OR-6 forbids this
    module from computing anything, and a preflight that ran every module to
    decide what to print would be doing the analysis twice.
    """
    return all(getattr(project, attr, None) is not None for attr in step.requires)


def _plan_row(project: Project, spec: ReportSpec, step: wf.WorkflowStep,
              implemented: FrozenSet[str],
              results: Optional[Mapping[str, Optional[ModuleResult]]] = None,
              ) -> SectionPlan:
    """One step's row, everything but its number -- which position decides.

    ``present`` stays the cheap slice test even when ``results`` is available:
    it is what the preflight shows about the *project*, and a module that ran
    and returned nothing is a different fact from an input that is missing.
    """
    selected = step.key not in spec.excluded_steps
    present = _inputs_present(project, step)
    produced = present if results is None else results.get(step.key) is not None
    if not selected:
        state = SectionState.EXCLUDED
    elif step.key not in implemented:
        state = SectionState.NOT_IMPLEMENTED
    elif not produced:
        state = SectionState.ABSENT
    else:
        state = SectionState.INCLUDED
    return SectionPlan(
        step_key=step.key, number="", title=document_title(step), state=state,
        reason=STATE_REASON.get(state, ""),
        lead=STATE_TEXT.get(state, ("", ""))[0],
        selected=selected, inputs_present=present)


def run_sections(project: Project, spec: ReportSpec, *,
                 implemented: FrozenSet[str] = IMPLEMENTED,
                 ) -> Dict[str, Optional[ModuleResult]]:
    """Run each implemented, selected step once: ``step key -> result or None``.

    The **one** place a module is run for the report, so the preflight and the
    document can never describe different analyses (the same reasoning that has
    ``package_members`` accept an already-built document). ``None`` records a
    step that could not produce a result -- missing inputs, or a module that
    raised on a partial project -- and :func:`section_plan` reads it as
    ``ABSENT``. Catching broadly is deliberate: G-OR-7 says a half-filled
    project still builds, and a traceback out of here would take the whole
    report down over one absent slice.

    **A step's folded modules are run too**, keyed by *module name* beside the
    step keys. A page that names three programs in its ``bas`` -- Weight & Mass
    Properties says ``WTESTIMA+WTONECG+WTENV`` -- produces numbers from all
    three, and section 2.2's loading-envelope table is WTENV's. Running them
    here rather than in the section builder keeps this the single run point;
    :func:`sloads.workflow.step_modules` owns which modules a step runs, so the
    set cannot drift from the navigation's own claim. The primary module is not
    re-run under its own name: it is already under the step key.
    """
    from ..registry import get as get_module
    from ..workflow import step_modules

    results: Dict[str, Optional[ModuleResult]] = {}
    for step in analysis_steps():
        if step.key not in implemented or step.key in spec.excluded_steps:
            continue
        if not step.module or not _inputs_present(project, step):
            results[step.key] = None
            continue
        for name in step_modules(step.key):
            key = step.key if name == step.module else name
            try:
                results[key] = get_module(name)(project)
            except Exception:                 # see the docstring
                results[key] = None
    return results


def section_plan(project: Project, spec: ReportSpec, *,
                 implemented: FrozenSet[str] = IMPLEMENTED,
                 results: Optional[Mapping[str, Optional[ModuleResult]]] = None,
                 ) -> List[SectionPlan]:
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
    steps = analysis_steps()
    index = 0
    while index < len(steps):
        step = steps[index]
        group = group_for(step.key)
        if group is None:
            row = _plan_row(project, spec, step, implemented, results)
            number = ""
            if row.state is not SectionState.EXCLUDED:
                number = section_number(printed)
                printed += 1
            plan.append(replace(row, number=number))
            index += 1
            continue
        # A group consumes its members as one run. Contiguity is a guarded
        # property of SECTION_GROUPS, so slicing is safe here and the slice is
        # what makes the members' order the workflow's order rather than the
        # declaration's -- one ordering owner, not two.
        members = steps[index:index + len(group.members)]
        rows = [_plan_row(project, spec, member, implemented, results)
                for member in members]
        shown = [row for row in rows if row.state is not SectionState.EXCLUDED]
        if shown:
            parent = section_number(printed)
            printed += 1
            plan.append(SectionPlan(
                step_key="", number=parent, title=group.title,
                state=SectionState.INCLUDED, reason="",
                group_key=group.key, is_group=True))
        else:
            # Every member deselected: the group has nothing to head, so it is
            # not printed at all and takes no number. Its member rows stay in
            # the plan so the page's preflight still shows the choices.
            parent = ""
        child = 0
        for row in rows:
            number = ""
            if parent and row.state is not SectionState.EXCLUDED:
                number = subsection_number(parent, child)
                child += 1
            plan.append(replace(row, number=number, group_key=group.key))
        index += len(members)
    return plan


def appendix_plan(plan: Sequence[SectionPlan]) -> List[SectionPlan]:
    """One row per appendix slot, lettered by position, with the state it renders.

    A built appendix **inherits its step's state**: an appendix of wing loads for
    a project that produced none has to say what its section says, because it is
    the same absence seen twice and not a second fact. An appendix whose section
    was deselected is dropped with it -- and dropping it does not relabel
    anything, because the letter comes from the slot's position and not from
    what is printed (OR-50).
    """
    rows: List[SectionPlan] = []
    for appendix in APPENDICES:
        state = SectionState.NOT_IMPLEMENTED
        if appendix.built:
            source = next((row for row in plan
                           if row.step_key == appendix.step_key), None)
            if source is not None:
                if source.state is SectionState.EXCLUDED:
                    continue
                state = source.state
        rows.append(SectionPlan(
            step_key=appendix.step_key,
            number=appendix_letter(appendix.title),
            title=appendix.title, state=state,
            reason=STATE_REASON.get(state, ""),
            lead=STATE_TEXT.get(state, ("", ""))[0]))
    return rows


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

    "All delivered loads in this report are LIMIT. Every load case states the "
    "safety factor 14 CFR 23.303 prescribes for it and the basis of that "
    "factor; sloads applies it nowhere, here or in the exported deck, so it is "
    "the sizing analysis that applies it. The -ULT marker appears only on the "
    "two families the regulation prescribes already ultimate — 23.367(a)(2) "
    "engine torque and 23.561(b) emergency-landing inertia — which ask for "
    "nothing further. Quantities that are not loads take no factor at all.",

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
    # Imported here, not at module scope: oracle_sections needs this module's
    # SectionPlan, and a top-level import in both directions is a cycle.
    from ..field_registry import reduce_to_oracle_inputs
    from .oracle_sections import build_appendix, build_section

    # **The document is a function of the oracle projection, not of the file.**
    # The same reducer the fingerprint hashes through (OR-21, gate G-OR-13), so
    # "a field the oracle GUI cannot set can move neither the hash nor the
    # document" is one guarantee with one owner rather than two that can drift.
    #
    # This is not belt-and-braces. Section 2 quotes each module's own
    # certification basis, and on a concept project the speeds module takes the
    # Part 25 Mach-margin route and says so -- so a concept-only field reached
    # the printed page through a module note, and G-OR-6 caught it (GUI review,
    # 2026-08-30). Avoiding that one field would have left every future section
    # free to find another; reducing once forecloses the class.
    project = reduce_to_oracle_inputs(project)

    results = run_sections(project, spec, implemented=implemented)
    plan = section_plan(project, spec, implemented=implemented, results=results)
    system = spec.unit_system

    intro_text = spec.introduction.strip() or default_introduction()
    sections: List[Section] = [
        Section(heading(plan[0].number, "Introduction"),
                body=[p for p in intro_text.split("\n\n") if p.strip()]),
    ]
    #: The group currently open, so its members land in its ``subsections``
    #: rather than at the top level. A group row always precedes its members
    #: (:func:`section_plan`), so one slot is enough.
    open_group: Optional[Section] = None
    for entry in plan[len(FRONT_SECTIONS):]:
        # A deselected section is not printed at all -- no heading, no reason
        # (owner's decision, GUI review 2026-08-30). It keeps its row in the
        # plan so the page's preflight still shows the choice registering.
        if entry.state is SectionState.EXCLUDED:
            continue
        if entry.is_group:
            open_group = Section(heading(entry.number, entry.title),
                                 body=group_prose(entry.group_key))
            sections.append(open_group)
            continue
        section = build_section(project, entry, results, system=system,
                                plan=plan)
        if entry.group_key and open_group is not None:
            open_group.subsections.append(section)
        else:
            sections.append(section)

    # The appendices follow every numbered section, in slot order. They are
    # built from the same results and the same plan the body was, so an appendix
    # can never describe a different analysis from the section it echoes.
    for entry in appendix_plan(plan):
        sections.append(build_appendix(project, entry, results, system=system,
                                       plan=plan))

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
    "APPENDICES",
    "DOCUMENT_TITLES",
    "FRONT_SECTIONS",
    "GROUP_PROSE",
    "IMPLEMENTED",
    "INPUT_ECHO",
    "NOT_CARRIED",
    "SECTION_GROUPS",
    "STATE_REASON",
    "STATE_TEXT",
    "WING_LOAD_STATIONS",
    "Appendix",
    "OracleDocument",
    "SectionGroup",
    "SectionPlan",
    "SectionState",
    "analysis_steps",
    "appendix_heading",
    "appendix_letter",
    "appendix_plan",
    "appendix_ref",
    "build_oracle_document",
    "default_introduction",
    "default_limitations",
    "document_title",
    "group_for",
    "group_prose",
    "heading",
    "run_sections",
    "section_number",
    "section_plan",
    "section_ref",
    "see_appendix",
    "subsection_number",
    "subsection_ref",
]
