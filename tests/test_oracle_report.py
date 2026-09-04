"""The oracle technical report's content model (design note 44, §3 gates).

Assertions here are made against the **content model**, never by matching LaTeX
strings, for OR-6's reason: the document must be checkable independently of how
it is typeset, and a test that greps the ``.tex`` passes for the wrong reasons as
soon as the renderer changes a brace.

Gates covered: G-OR-2 (the derived section set), G-OR-6 (no concept content),
G-OR-7 (a half-filled project still yields a complete document), G-OR-10 (no
metadata reaches a number), G-OR-12 (the unit owner) and G-OR-18 (the gap states
stay distinguishable).
"""

import ast
import dataclasses
import datetime
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads import registry  # noqa: E402
from sloads import workflow as wf  # noqa: E402
from sloads.derived_geometry import mac_reference, station_to_pct_mac  # noqa: E402
from sloads.field_registry import reduce_to_oracle_inputs  # noqa: E402
from sloads.models import Project  # noqa: E402
from sloads.models.report import ReportSpec, SignatureRow  # noqa: E402
from sloads.report import content  # noqa: E402
from sloads.report import oracle_content as oc  # noqa: E402
from sloads.report import oracle_sections as osec  # noqa: E402
from sloads.report import oracle_latex as ol  # noqa: E402
from sloads.report.latex import section_tex  # noqa: E402
from sloads.report.plots_tex import figure_body_tex  # noqa: E402
from sloads.report.render import format_value  # noqa: E402
from sloads.units import UnitSystem  # noqa: E402

_EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_TWIN = os.path.join(_EXAMPLES, "baron_58.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")

_SOURCES = ("sloads/report/oracle_content.py", "sloads/report/oracle_latex.py",
            "sloads/report/oracle_package.py",
            "sloads/report/oracle_sections.py")


def _spec(**kwargs) -> ReportSpec:
    base = dict(title="FAR 23 Structural Design Loads", report_number="LR-0142",
                revision="B", abstract="An abstract.")
    base.update(kwargs)
    return ReportSpec(**base)


def _doc(path=_GA, spec=None, **kwargs):
    return oc.build_oracle_document(io.load_project(path), spec or _spec(),
                                    **kwargs)


def _flat(sections):
    """Every section of the document, subsections in place, depth-first.

    The document is a tree from iteration 2 on (section 2 groups four steps as
    subsections), while the plan stays a flat list of rows. Every test that pairs
    them flattens through here rather than each growing its own walk.
    """
    out = []
    for section in sections:
        out.append(section)
        out.extend(_flat(section.subsections))
    return out


# --------------------------------------------------------------------------- #
# G-OR-2 -- the section set is derived, both directions
# --------------------------------------------------------------------------- #
def test_every_result_producing_oracle_step_has_exactly_one_section():
    """G-OR-2, and it holds from the first commit rather than the last.

    That is what OR-32's third state buys: a section with no builder still
    *exists*, saying it is not implemented, so the derivation can be asserted now
    instead of after the final iteration.
    """
    plan = oc.section_plan(io.load_project(_GA), _spec())
    keys = [entry.step_key for entry in plan if entry.step_key]
    expected = [step.key for step in wf.oracle_steps() if step.module]
    assert keys == expected, "the analysis body is not oracle_steps() in order"
    assert len(keys) == len(set(keys)), "a step has more than one section"


def test_an_input_only_step_gets_no_analysis_section():
    """A step that produces no result has nothing to report on.

    ``aero_coefficients`` is an oracle *page* (it feeds two modules) but not an
    analysis section, and a section set that included it would promise a result
    the analysis never produces.
    """
    input_only = [s.key for s in wf.oracle_steps() if not s.module]
    assert input_only, "the fixture for this rule has gone; check oracle_steps()"
    plan_keys = {e.step_key for e in oc.section_plan(io.load_project(_GA), _spec())}
    assert not (set(input_only) & plan_keys)


def test_section_numbers_come_from_the_owner_not_from_literals():
    """Numbering moves when a section is inserted above it (review F-R2).

    Asserted by construction: the front matter's length is what offsets the body,
    so a document that grew a front section renumbers rather than misreferencing.
    """
    plan = oc.section_plan(io.load_project(_GA), _spec())
    numbers = [e.number for e in plan if e.number]

    # Top-level numbers run 1..N with no hole...
    top = [n for n in numbers if "." not in n]
    assert top == [str(i + 1) for i in range(len(top))]
    first_body = plan[len(oc.FRONT_SECTIONS)]
    assert first_body.number == str(len(oc.FRONT_SECTIONS) + 1)

    # ...and every subsection is its own parent's next child, in order. Asserted
    # against `subsection_number` rather than against "2.1", so the scheme has
    # one owner here as well as in the code.
    seen = {}
    for number in numbers:
        parent, _, _child = number.rpartition(".")
        if not parent:
            continue
        index = seen.get(parent, 0)
        assert number == oc.subsection_number(parent, index), (
            f"{number} is not child {index} of {parent}")
        seen[parent] = index + 1
        assert parent in numbers, f"{number} has no parent section"


# --------------------------------------------------------------------------- #
# G-OR-18 -- the three gap states stay apart (OR-32)
# --------------------------------------------------------------------------- #
def test_the_gap_states_have_distinct_wording():
    """Each state says whose decision produced the gap; none may borrow another's
    wording, or the document asserts something untrue about the reader's data or
    about a colleague's editorial choice.

    **Both halves are checked, and the lead is the half that matters.** The first
    build of this document gave all three states distinct sentences and then
    printed every one of them under a bold "Not analysed" -- absence's wording --
    because that lead was hard-coded in the renderer. A reader skimming the
    document sees the lead and nothing else.
    """
    leads = [lead for lead, _text in oc.STATE_TEXT.values()]
    reasons = list(oc.STATE_REASON.values())
    assert len(leads) == len(set(leads)), f"two states share a lead: {leads}"
    assert len(reasons) == len(set(reasons))
    assert all(lead.strip() and text.strip()
               for lead, text in oc.STATE_TEXT.values())
    # The renderer prints the sentence after the bold lead and a full stop, so
    # a lower-case first word reads as a typesetting fault -- which is how it
    # reached the page: the sentences were written to follow a colon.
    for state, (_lead, text) in oc.STATE_TEXT.items():
        assert text[0].isupper(), (
            f"{state.value}'s sentence follows a full stop and must open a "
            f"sentence: {text!r}")


def test_the_default_introduction_claims_nothing_about_omitted_sections():
    """Deselection is silent now, so the introduction must not promise a list.

    Its predecessor said sections not carried were "listed on the title page",
    kept saying it after they moved to the introduction, and would have kept
    saying it after they stopped being printed at all -- a cross-reference a
    reader follows and finds nothing at. The text is the author's to edit, so
    what is guarded is the *default* the generator ships.
    """
    default = oc.default_introduction().lower()
    # Narrowly the *omission* claim. The airplane really is identified on the
    # title page, so banning that phrase outright would be wrong -- it is the
    # promise of a list of what is missing that has nothing left to point at.
    for claim in ("listed at the end", "does not carry", "not carried",
                  "silently omitted", "reduced document"):
        assert claim not in default, (
            f"the default introduction still promises {claim!r}, which no "
            "longer appears anywhere in the document")


def test_each_gap_state_renders_under_its_own_lead():
    """The end of that story: what the reader actually sees on the page.

    Asserted through the rendered ``.tex`` rather than the model, because the
    defect lived entirely in the renderer -- the model was already right.
    """
    step = oc.analysis_steps()[1]
    # EXCLUDED is not here: a deselected section is not printed at all, so it
    # has no rendered lead to be distinct from (owner's decision, 2026-08-30).
    cases = {
        oc.SectionState.NOT_IMPLEMENTED: _doc(),
        oc.SectionState.ABSENT: oc.build_oracle_document(
            Project(), _spec(), implemented=frozenset({step.key})),
    }
    seen = {}
    for state, doc in cases.items():
        lead = oc.STATE_TEXT[state][0]
        tex = ol.render_oracle_document(doc)
        assert "\\textbf{" + lead + ".}" in tex, (
            f"{state.value} does not render under its own lead")
        seen[state] = lead
    # ...and no state's rendered lead is another's.
    assert len(set(seen.values())) == len(seen)


def test_deselection_is_decided_before_every_other_state():
    """Deselection outranks the rest, because it is the one that stops printing.

    Once a section is not printed there is no reader to owe a reason to, so the
    other three states have nothing to say about it. Before the 2026-08-30
    change this ordering was the opposite way round -- NOT_IMPLEMENTED first --
    and it mattered then because an excluded section still appeared.
    """
    steps = oc.analysis_steps()
    spec = _spec(excluded_steps=tuple(s.key for s in steps))
    # Every state's cause is present at once: nothing implemented, no inputs,
    # and everything deselected.
    plan = oc.section_plan(Project(name="barely started"), spec)
    body = [e for e in plan if e.step_key]
    assert body and all(e.state is oc.SectionState.EXCLUDED for e in body)
    # The choice is still visible to the preflight, which is what the column
    # exists for -- the state hides the section, not the author's decision.
    assert all(e.selected is False for e in body)


def test_among_printed_sections_not_implemented_outranks_absence():
    """A section the tool cannot build must not claim the reader's inputs are
    missing. Once every section is implemented this ordering stops mattering,
    which is the point at which ABSENT is the only one left."""
    step = next(s for s in oc.analysis_steps()
                if s.requires and s.key not in oc.IMPLEMENTED)
    empty = Project(name="empty")
    unbuilt = oc.section_plan(empty, _spec())
    assert next(e for e in unbuilt if e.step_key == step.key).state \
        is oc.SectionState.NOT_IMPLEMENTED
    built = oc.section_plan(empty, _spec(), implemented=frozenset({step.key}))
    entry = next(e for e in built if e.step_key == step.key)
    assert entry.state is oc.SectionState.ABSENT
    assert entry.inputs_present is False


def test_a_deselected_section_is_omitted_entirely_and_numbering_closes_up():
    """A deselected section is not printed, and leaves no gap behind it.

    This **reverses** OR-19 and the filtered-export rule ``ORACLE_REPORT.md``
    inherits from ``SUMMARY_REPORT.md`` §3.4 (owner's decision, 2026-08-30):
    deselection is now silent. Recorded as a deviation in `ORACLE_REPORT.md` §3
    rather than by editing `SUMMARY_REPORT.md`, which governs a different
    document.

    The numbering half is the part that bites: sections are numbered by
    position among those that *render*, so dropping one must renumber the rest.
    Numbering by workflow position would leave a hole in the printed sequence
    and every reference after it would name the wrong section.
    """
    step = oc.analysis_steps()[0]
    doc = _doc(spec=_spec(excluded_steps=(step.key,)),
               implemented=frozenset({step.key}))
    title = oc.document_title(step)
    titles = [section.title for section in _flat(doc.sections)]
    assert not any(title in heading for heading in titles), (
        "a deselected section was printed")
    tex = ol.render_oracle_document(doc)
    assert "excluded by user selection" not in tex.lower()

    # The printed numbers close up at both levels: top-level 1..N with no hole,
    # and each group's surviving members renumbered from .1 -- the deselected
    # step here is a group member, so it is the sibling renumbering that bites.
    numbers = [e.number for e in doc.plan if e.number]
    top = [int(n) for n in numbers if "." not in n]
    assert top == list(range(1, len(top) + 1)), (
        f"deselection left a hole in the section numbering: {numbers}")
    for parent in top:
        children = [n for n in numbers if n.startswith(f"{parent}.")]
        assert children == [oc.subsection_number(str(parent), i)
                            for i in range(len(children))], (
            f"deselection left a hole under section {parent}: {children}")
    assert _plan_sections(doc) == numbers
    # The excluded step keeps its plan row, so the page's preflight can still
    # show the author that their choice registered.
    excluded = [e for e in doc.plan if e.step_key == step.key]
    assert len(excluded) == 1 and excluded[0].state is oc.SectionState.EXCLUDED
    assert excluded[0].number == ""


# --------------------------------------------------------------------------- #
# G-OR-7 -- absence is content
# --------------------------------------------------------------------------- #
def _number_of(section):
    """The number a rendered section's heading carries, or ``""``."""
    head = section.title.split(" ", 1)[0].rstrip(".")
    return head if head[:1].isdigit() else ""


def _numbered_sections(doc):
    """The number each rendered section carries, in document order.

    Every rendered section is a numbered plan row, a subsection a builder owns
    (section 3 renders four), or a lettered appendix -- so a count of sections
    against a count of plan rows stopped being the invariant when the first of
    those landed. What still holds, and is what the two callers assert, is that
    the *numbered* sections are exactly the numbered plan rows, in order.
    """
    return [n for n in (_number_of(s) for s in _flat(doc.sections)) if n]


def _plan_sections(doc):
    """The rendered numbers that are plan rows, in document order.

    A builder's own subsections are numbered too (section 3 renders 3.1 ... 3.4)
    and have no plan row, so a comparison against the plan filters to the rows
    the plan actually claims -- and still asserts their order and completeness.
    """
    wanted = {e.number for e in doc.plan if e.number}
    return [n for n in _numbered_sections(doc) if n in wanted]


def test_a_half_filled_project_yields_a_complete_document():
    """No traceback, and no silently missing section."""
    doc = oc.build_oracle_document(Project(name="half"), _spec())
    assert _plan_sections(doc) == [e.number for e in doc.plan if e.number]
    assert [s.title for s in doc.sections[-len(oc.APPENDICES):]] == [
        oc.appendix_heading(a.title) for a in oc.APPENDICES]
    body = [e for e in doc.plan if e.step_key]
    assert len(body) == len([s for s in wf.oracle_steps() if s.module])
    assert all(e.reason for e in body), "a gap with no reason is a silent gap"
    assert ol.render_oracle_document(doc)


def test_an_empty_project_still_renders():
    """The renderer is exercised too: a content model that builds but cannot be
    typeset is not a document."""
    tex = ol.render_oracle_document(
        oc.build_oracle_document(Project(), ReportSpec()))
    assert tex.startswith("\\documentclass")
    assert tex.rstrip().endswith("\\end{document}")


# --------------------------------------------------------------------------- #
# G-OR-6 -- no concept-mode or sloads-only content
# --------------------------------------------------------------------------- #
def test_concept_fields_cannot_reach_the_document():
    """The scope boundary is asserted, not described.

    Built from a concept project and from the same project reduced to what the
    oracle GUI can set: identical documents. This rides on the *same* owner the
    fingerprint uses, so G-OR-6 and G-OR-13 cannot drift into two different
    definitions of "oracle scope".
    """
    project = io.load_project(_CONCEPT)
    full = ol.render_oracle_document(oc.build_oracle_document(project, _spec()))
    reduced = ol.render_oracle_document(
        oc.build_oracle_document(reduce_to_oracle_inputs(project), _spec()))
    assert full == reduced


# --------------------------------------------------------------------------- #
# G-OR-10 -- document metadata cannot move a number
# --------------------------------------------------------------------------- #
def test_no_report_spec_field_reaches_a_module_result():
    """Metadata is metadata. A title that could change a load would be a defect
    of a kind no review catches by reading."""
    project = io.load_project(_GA)
    before = registry.run_all_modules(project)
    loud = _spec(title="ZZTOKEN", report_number="ZZTOKEN", revision="ZZTOKEN",
                 abstract="ZZTOKEN", marking="ZZTOKEN", distribution="ZZTOKEN",
                 organisation="ZZTOKEN", customer="ZZTOKEN",
                 prepared=SignatureRow(name="ZZTOKEN"))
    oc.build_oracle_document(project, loud)
    after = registry.run_all_modules(project)
    assert [repr(r) for r in before] == [repr(r) for r in after]


def test_metadata_does_not_leak_into_any_table_cell():
    """The other half: it may appear on the title page, and nowhere a number
    lives."""
    doc = _doc(spec=_spec(marking="ZZTOKEN"))
    for section in doc.sections:
        for table in section.tables:
            for row in table.rows:
                assert not any("ZZTOKEN" in str(cell) for cell in row)


# --------------------------------------------------------------------------- #
# G-OR-12 -- the document's unit owner is the spec
# --------------------------------------------------------------------------- #
def test_the_document_reads_the_spec_unit_system():
    imperial = _doc(spec=_spec(unit_system=UnitSystem.IMPERIAL))
    si = _doc(spec=_spec(unit_system=UnitSystem.SI))
    assert imperial.system is UnitSystem.IMPERIAL and si.system is UnitSystem.SI
    assert imperial.units_note != si.units_note


@pytest.mark.parametrize("relative", _SOURCES)
def test_the_report_builder_never_reads_the_sidebar_toggle(relative):
    """G-OR-12 made structural rather than remembered.

    ``active_system()`` is the app layer's single read of the sidebar toggle, and
    it governs what the *analysis pages* display. A report that consulted it
    would build a different document depending on where the user last clicked --
    and OR-20's whole point is that a spec plus a project is a complete recipe.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = _code_without_prose(os.path.join(root, relative))
    assert "active_system" not in source
    assert "app_shell" not in source


def _code_without_prose(path: str) -> str:
    """``path``'s source with its docstrings and comments removed.

    A source scan that reads prose finds every word the file uses to *explain*
    the rule it is being checked against -- this test failed first time round
    because the module docstring says "longtable" while describing the emitter it
    deliberately does not have. Blanking docstrings and comments makes the scan
    measure the code.
    """
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source)
    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            for index in range(first.lineno - 1, (first.end_lineno or first.lineno)):
                lines[index] = ""
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def test_the_oracle_renderer_defines_no_table_emitter_of_its_own():
    """One table emitter, two documents.

    The oracle report owns its furniture and borrows every emitter from
    ``report.latex``. Duplicating them would let the two documents' tables drift
    for a milestone and turn the eventual main-report merge into a rewrite.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "sloads/report/oracle_latex.py")
    source = _code_without_prose(path)
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = {
        alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        and (node.module or "").endswith("latex")
        for alias in node.names
    }
    assert "section_tex" in imported, (
        "the oracle renderer must reach tables and figures through the shared "
        "section emitter, not through machinery of its own")
    # Specifically the *content* table and plot machinery. Plain ``tabular`` and
    # booktabs rules are not on this list: the title page's control block and
    # signature block are furniture -- unnumbered, uncaptioned, absent from the
    # List of Tables -- and routing them through the content-table emitter would
    # put the signature block in the List of Tables, which is worse than the
    # duplication this rule exists to prevent.
    for banned in ("longtable", "tabcolsep", "addplot", "sltablewidth"):
        assert banned not in source, (
            f"{banned} means a second content-table emitter has appeared here")


def test_the_document_builder_does_not_run_the_analysis():
    """OR-6: nothing is recomputed. The preflight decides a section's state from
    slice presence, not by running a module -- a report that ran the analysis to
    decide what to print would be doing it twice, and could disagree with itself.
    """
    source = _code_without_prose(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "sloads/report/oracle_content.py"))
    for banned in ("run_all_modules", "registry.get", "import registry"):
        assert banned not in source


def test_it_builds_for_both_example_airplanes():
    """OR-11: the single is the Appendix A oracle case; the twin exercises the
    engine-mount and one-engine-out sections as present rather than absent."""
    for path in (_GA, _TWIN):
        tex = ol.render_oracle_document(_doc(path))
        assert tex.startswith("\\documentclass"), path
        assert "\\tableofcontents" in tex and "\\listoffigures" in tex


def test_the_draft_mark_follows_the_signatures():
    """OR-18/OR-27: the same build button, and the document says which it is."""
    unsigned = _doc()
    assert unsigned.draft
    assert "\\sldraftmark" in ol.headers_tex(unsigned)
    assert "DRAFT" in ol.title_page_tex(unsigned)
    signed = _doc(spec=_spec(
        prepared=SignatureRow(name="A"), checked=SignatureRow(name="B"),
        approved=SignatureRow(name="C")))
    assert not signed.draft
    # The macro is always *defined* in the preamble; what changes is whether it
    # is ever called. Asserting on the call site rather than on the word keeps
    # this test measuring the behaviour instead of the comments around it.
    assert "\\sldraftmark" not in ol.headers_tex(signed)
    assert "DRAFT" not in ol.title_page_tex(signed)


def test_the_classification_marking_is_on_every_page():
    """A marking that appears only on the cover is one photocopied page away
    from being an unmarked document."""
    tex = ol.render_oracle_document(_doc(spec=_spec(marking="RESTRICTED")))
    assert "\\fancyfoot" in tex and "RESTRICTED" in tex


def test_the_watermark_adds_no_latex_package():
    """``SUMMARY_REPORT.md`` §2 limits the document to a standard distribution,
    and the preamble is shared with the summary report -- so DRAFT is TikZ
    machinery already loaded, not a new dependency."""
    assert "usepackage" not in ol.ORACLE_PREAMBLE_EXTRA


def test_two_builds_of_one_document_are_byte_identical():
    """G-OR-5 at the document level; G-OR-16 carries it to the whole package."""
    assert ol.render_oracle_document(_doc()) == ol.render_oracle_document(_doc())


def test_the_plan_and_the_sections_agree():
    """The preflight the page shows and the document it writes are built from one
    object, so they cannot describe different documents."""
    doc = _doc()
    printed = [e for e in doc.plan if e.number]
    # Paired by number, not by position: a builder's own subsections (section 3
    # renders four) and the lettered appendices are rendered sections with no
    # plan row of their own, so a positional zip stopped naming the same thing
    # on both sides.
    numbered = {_number_of(s): s for s in _flat(doc.sections) if _number_of(s)}
    assert [e.number for e in printed] == [n for n in numbered
                                           if n in {e.number for e in printed}]
    for entry in printed:
        section = numbered[entry.number]
        assert section.title == oc.heading(entry.number, entry.title)
        # A group row heads its members and has no state of its own; every other
        # printed row states a reason exactly when it is not included.
        if not entry.is_group:
            assert bool(section.absent_reason) is (not entry.included)


def test_the_spec_is_carried_whole_and_not_copied_field_by_field():
    """The document holds the spec itself, so a field added to ``ReportSpec``
    reaches the renderer without a second list to keep in step."""
    spec = _spec()
    assert _doc(spec=spec).spec is spec
    assert dataclasses.is_dataclass(spec)



def test_a_date_is_stored_as_an_iso_string_and_a_non_date_survives():
    """The spec is a JSON file a person edits, so a hand-typed value that is not
    a date must load rather than crash -- ``parse_date`` says which it is, and
    the page keeps what it cannot parse."""
    from sloads.models.report import parse_date

    assert parse_date("2026-08-30") == datetime.date(2026, 8, 30)
    for bad in ("TBD", "30/08/2026", "", "   ", "August 30"):
        assert parse_date(bad) is None


def test_an_unsigned_row_prints_no_date():
    """A date beside a ruled name blank asserts an approval that did not happen.

    The stored value is kept -- a planned date is legitimate -- but printing it
    against an absent name is not, and the picker added in the GUI review makes
    setting one without a name a single click.
    """
    spec = _spec(
        prepared=SignatureRow(name="A Engineer", role="Stress", date="2026-08-01"),
        checked=SignatureRow(name="", role="Stress", date="2026-08-02"),
        approved=SignatureRow(name="", role="", date="2026-08-03"))
    tex = ol.title_page_tex(_doc(spec=spec))
    assert "2026-08-01" in tex, "a signed row keeps its date"
    for orphan in ("2026-08-02", "2026-08-03"):
        assert orphan not in tex, (
            "an unsigned signature row printed a date, which reads as an "
            "approval that happened and was signed illegibly")
    # The role of an unsigned row is still shown: naming who is due to sign
    # claims nothing about whether they have.
    assert "Stress" in tex


def test_the_report_page_never_defaults_a_date_to_today():
    """``st.date_input`` defaults its value to *today*.

    Left alone, that stamps the current date onto an issue date and three
    signature dates nobody filled in, and the title page then states that the
    report was issued and signed today. Every call must pass ``value=``
    explicitly, which is what the shared ``_date`` helper is for.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "oracle_app/report.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    calls = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute)
             and node.func.attr == "date_input"]
    assert calls, "the date fields are no longer pickers -- retire this guard"
    for call in calls:
        assert any(kw.arg == "value" for kw in call.keywords), (
            "a date_input with no explicit value= silently defaults to today")


def test_the_cover_carries_identity_and_signatures_and_nothing_to_read_through():
    """The analysis basis and the not-carried list are in the introduction.

    On the cover they pushed the signature block onto a second sheet, so the
    approval record sat on a page carrying none of the document's identity --
    the one page that must never travel alone. The guard is on the *cover*
    rather than on the introduction because the failure is additive: a block
    added back here breaks the layout silently, and the page still renders.
    """
    spec = _spec(marking="COMMERCIAL IN CONFIDENCE",
                 distribution="Approved for programme use.",
                 excluded_steps=("wing_loads",))
    doc = _doc(spec=spec, anchors=[("Design weight", "3400 lb")],
               fingerprint="deadbeefdeadbeef", fingerprint_version=1)
    cover = ol.title_page_tex(doc)
    for banned, why in (("Analysis basis", "the anchors block"),
                        ("deadbeefdeadbeef", "the fingerprint"),
                        ("3400 lb", "an anchor value"),
                        ("Limitations and scope", "the limitations subsection")):
        assert banned not in cover, f"{why} is back on the cover"
    # ...and the things the cover exists for are still on it.
    assert "COMMERCIAL IN CONFIDENCE" in cover
    assert "Prepared by" in cover and "Approved by" in cover
    assert "Approved for programme use." in cover

    # The moved blocks are in the document, immediately after the introduction.
    tex = ol.render_oracle_document(doc)
    assert (tex.index("Introduction") < tex.index("Analysis basis")
            < tex.index("Limitations and scope")), (
        "the analysis basis and the limitations subsection must follow the "
        "introduction, ahead of any analysis section")


def test_an_empty_front_matter_list_says_so():
    """A heading with nothing under it is a *silent* absence.

    It is the one thing this document does not do anywhere else -- a section the
    generator cannot build still appears, saying so -- and a reader facing an
    empty "List of Figures" cannot tell "there are none" from "it failed to
    generate". The contents entry is asserted for the same reason the abstract
    has one: two kinds of front matter treated differently reads as an
    oversight.
    """
    # A document with no builder implemented: every section is a stated
    # placeholder, so both lists are genuinely empty and must say so. Built this
    # way rather than from an empty project, so the emptiness under test is the
    # generator's and not the reader's missing inputs.
    tex = ol.render_oracle_document(_doc(implemented=frozenset()))
    for title, noun in (("List of Figures", "figures"), ("List of Tables", "tables")):
        assert f"This issue contains no {noun}." in tex
        assert r"\addcontentsline{toc}{section}{" + title + "}" in tex


def test_a_populated_front_matter_list_does_not_claim_to_be_empty():
    """The emptiness test looks into subsections too: a table one level down
    still puts a line in the list, and the document would otherwise state the
    opposite of what the reader is looking at."""
    from sloads.report.content import Section, Table

    doc = _doc(implemented=frozenset())
    nested = Section("Nested", tables=[Table(title="A table", columns=["x"],
                                             rows=[["1"]])])
    doc.sections[0].subsections.append(nested)
    tex = ol.render_oracle_document(doc)
    assert "This issue contains no tables." not in tex
    assert "This issue contains no figures." in tex, (
        "the figures list is genuinely empty and must still say so")


def test_the_footer_names_the_issuing_organisation():
    """A loose page must say who issued it.

    The footer centre carried the load basis, which the introduction already
    states and which every units string carries as its ``-ULT`` marker -- so it
    restated something self-evident from the numbers, in the one slot that could
    carry something a reader cannot recover from a photocopied page.
    """
    tex = ol.headers_tex(_doc(spec=_spec(organisation="Sean Inv",
                                         marking="COMMERCIAL IN CONFIDENCE")))
    assert "Sean Inv" in tex
    assert "ULTIMATE loads" not in tex
    assert "COMMERCIAL IN CONFIDENCE" in tex, "the marking is still owed (§4)"
    # An empty organisation leaves the slot blank rather than printing a stand-in
    # that would name an issuer the spec never stated.
    blank = ol.headers_tex(_doc(spec=_spec(organisation="")))
    assert "&  &" in blank.replace("{}", "") or "& &" in blank


def test_the_limitations_prefill_drops_the_tool_blocks_but_the_owner_keeps_them():
    """Six blocks are filtered out of the report's pre-fill (owner, 2026-08-30).

    The filtering is asserted **in both places**: gone from the report's default,
    and still present in :func:`sloads.report.methods.methods_statement`. That
    second half is the one that matters -- the statement is the single owner for
    the CSV and deck exports too, and dropping blocks at the source would
    silently thin what a forwarded file carries, which is precisely what an
    in-band self-describing block exists to prevent.
    """
    from sloads.report.methods import methods_statement

    project = io.load_project(_GA)
    prefill = oc.default_limitations(project)
    shared = methods_statement(project)

    def labels(text):
        return {para.strip().split(":")[0].split("(")[0].strip()
                for para in text.split("\n\n") if para.strip()}

    dropped = {"PROVENANCE", "UNITS", "CATEGORY", "VERIFICATION", "MATH",
               "APPROVED CORRECTIONS"}
    assert labels(prefill) == {"STATUS", "BASIS", "KNOWN LIMITATIONS"}
    assert not (labels(prefill) & dropped)
    assert dropped <= labels(shared), (
        "a block was dropped from the shared statement instead of from the "
        "report's pre-fill -- the CSV and deck exports carry it too")
    # The statement's own banner is stripped: the subsection carries the title.
    assert "METHODS AND LIMITATIONS" not in prefill


def test_an_edited_limitations_text_is_used_verbatim():
    """Once written, it is the author's -- the generator does not merge into it.

    This is the snapshot the owner asked for: a signed issue keeps saying what
    it said when it was signed, so nothing may re-derive the text at render.
    """
    mine = "SCOPE: wing only.\n\nCAVEAT: preliminary."
    doc = _doc(spec=_spec(limitations=mine))
    assert doc.limitations == mine
    tex = ol.render_oracle_document(doc)
    assert "wing only" in tex and "KNOWN LIMITATIONS" not in tex


def test_the_analysis_basis_records_the_tool_and_the_schema_it_read():
    """Which build wrote the document, and which shape of input it read.

    Both are what a reader needs when a result cannot be reproduced years later.
    The version is *handed in*, never looked up here: reading installed package
    metadata is filesystem work this package does not do, and the build already
    resolves it once for ``build.json`` -- resolving it twice is how a document
    and its own stamp come to disagree.
    """
    from sloads.models.project import SCHEMA_VERSION
    from sloads.report import fingerprint as fpm

    project = io.load_project(_GA)
    rows = dict(fpm.anchors(project, tool_version="9.9.9"))
    assert rows["sloads version"] == "9.9.9"
    assert rows["Project schema"] == f"version {SCHEMA_VERSION}"
    # No version passed: the row is omitted rather than invented. A document
    # that names a build it did not come from is worse than one that is silent.
    assert "sloads version" not in dict(fpm.anchors(project))
    assert "Project schema" in dict(fpm.anchors(project))

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))


# --------------------------------------------------------------------------- #
# The page itself, headless
# --------------------------------------------------------------------------- #
def _page(project=None, state=None):
    """Run the report page the way ``Oracle.py``'s navigation runs it."""
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(
        "from oracle_app.report import render_report_page\nrender_report_page()\n",
        default_timeout=60)
    at.session_state["project"] = project or io.load_project(_GA)
    for key, value in (state or {}).items():
        at.session_state[key] = value
    at.run()
    return at


def test_the_report_page_renders_every_block():
    """Not merely "did not crash": a page that rendered its title and then died
    quietly would pass a no-exception test while being useless.

    The blocks are OR-16's, in order, and the build control is a button rather
    than a download (OR-22/OR-27).
    """
    at = _page()
    assert not at.exception, [e.message for e in at.exception]
    assert [w.value for w in at.title] == ["Report"]
    headings = [s.value for s in at.subheader]
    assert headings == ["Report package", "Document identity", "Abstract",
                        "Introduction", "Signatures",
                        "Distribution and marking", "Sections in this issue",
                        "Preflight", "Provenance", "Build"]
    assert "Build issue package" in [b.label for b in at.button]


def test_the_report_page_renders_for_a_project_with_nothing_in_it():
    """The page is reachable before any analysis input exists, and must open
    rather than gate on data it does not need: a report's identity block can be
    filled in long before the loads are."""
    at = _page(project=Project())
    assert not at.exception, [e.message for e in at.exception]


def test_the_page_offers_no_download():
    """OR-22/OR-27: the build writes a directory. The oracle GUI has exactly one
    download call site by gate, and it belongs to the results page."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = _code_without_prose(os.path.join(root, "oracle_app/report.py"))
    assert "download_button" not in source


def test_the_page_computes_no_path_hash_or_timestamp_itself():
    """Enforced by the oracle GUI's import gate, and asserted here as intent.

    Every path, hash and clock read belongs to ``sloads``. Without this the page
    would slowly acquire a second, divergent idea of where a report lives.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = _code_without_prose(os.path.join(root, "oracle_app/report.py"))
    for banned in ("import os", "import json", "import hashlib", "datetime",
                   "os.path", "open("):
        assert banned not in source, f"{banned} belongs in sloads, not the page"


def test_every_spec_widget_is_retired_when_a_package_is_opened():
    """The drift guard for a Streamlit trap that is invisible in review.

    A keyed widget is resolved from session state and ignores the ``value=``
    passed on later reruns. So opening a second issue redraws the first one's
    title and signatures over the spec just loaded -- and the next Save writes
    them back into it. The page retires its spec widgets on a switch; this
    asserts the retirement list still covers every widget it seeds, because the
    failure mode of forgetting one is silent data loss, not an error.
    """
    import oracle_app.report as page

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "oracle_app/report.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    literals = {node.value for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
                and node.value.startswith("report_")}
    # Session-state keys and controls that hold no spec field: they carry
    # nothing that a different issue would make stale.
    not_spec = {"report_root", "report_dirname", "report_spec",
                "report_spec_saved", "report_open", "report_open_btn",
                "report_anchor", "report_anchor_btn", "report_up_btn",
                "report_subdir", "report_down_btn", "report_mkdir",
                "report_mkdir_btn", "report_pick_btn", "report_baseline",
                "report_save", "report_build", "report_sel_"}
    retired = set(page._SPEC_WIDGETS)

    def covered(literal: str) -> bool:
        # A signature row is handed a *prefix* ("report_prepared") and builds
        # three keys from it, so a prefix counts as covered when the keys it
        # builds are.
        return literal in retired or any(k.startswith(literal + "_")
                                         for k in retired)

    missing = sorted(lit for lit in literals - not_spec if not covered(lit))
    assert not missing, (
        "these widgets seed from the report spec but are not retired when a "
        f"different package is opened: {missing}")
    # ...and nothing is retired that the page no longer builds, which would
    # quietly stop covering a widget that had been renamed.
    prefixes = {lit for lit in literals if any(k.startswith(lit + "_")
                                               for k in retired)}
    stale = sorted(key for key in retired
                   if key not in literals
                   and not any(key.startswith(p + "_") for p in prefixes))
    assert not stale, f"retired widgets that the page no longer has: {stale}"


# --------------------------------------------------------------------------- #
# Section 2 -- Loads Configuration (OR-8 iteration 2, ORACLE_REPORT.md 3.3)
# --------------------------------------------------------------------------- #
def _section_two(doc):
    """The Loads Configuration group section of ``doc``."""
    group = next(e for e in doc.plan if e.is_group)
    return next(s for s in _flat(doc.sections)
                if s.title == oc.heading(group.number, group.title))


def _envelope_section(doc):
    """Section 2.4, found by the figures it owns rather than by "has figures".

    2.1 grew planform figures in the same section group, so "the subsection with
    figures" stopped naming exactly one subsection. Selecting on the key is what
    the two subsections actually differ by.
    """
    return next(s for s in _flat([_section_two(doc)])
                if any(f.key.startswith("vn_") for f in s.figures))


def test_every_analysis_step_has_a_document_title_of_its_own():
    """The document never prints a workflow label.

    Both directions, so a new module-backed step fails the suite until somebody
    chooses what the *report* calls it. The inequality half is the one that
    matters: a title copied from the nav satisfies the mapping while leaving the
    document coupled to a name that exists for a different audience, and renaming
    the nav item would then retitle a report that has already been signed.
    """
    keys = {step.key for step in oc.analysis_steps()}
    assert set(oc.DOCUMENT_TITLES) == keys, (
        "DOCUMENT_TITLES and the analysis steps disagree: "
        f"{set(oc.DOCUMENT_TITLES) ^ keys}")
    assert all(title.strip() for title in oc.DOCUMENT_TITLES.values())


def test_every_group_member_is_a_step_and_the_members_are_contiguous():
    """A group collects a *run* of the workflow, not a scatter of it.

    ``section_plan`` slices its members out of the step list, so a group whose
    members were not adjacent would silently collect whatever sat between them.
    """
    order = [step.key for step in oc.analysis_steps()]
    for group in oc.SECTION_GROUPS:
        assert group.members, f"{group.key} groups nothing"
        positions = [order.index(key) for key in group.members]
        assert positions == sorted(positions), f"{group.key} is out of order"
        assert positions == list(range(positions[0], positions[0] + len(positions))), (
            f"{group.key}'s members are not contiguous in workflow order")
        assert group.key in oc.GROUP_PROSE, f"{group.key} heads nothing"


def test_section_two_invents_no_number():
    """G-OR-3 through the content model: every printed number has a source.

    Three legitimate sources, and no fourth. Most of section 2 reproduces a
    ``ModuleResult``; the empennage and control-surface tables and the CG-case
    table echo the project **as entered**, because no module returns a
    control-surface area or a throw; and the CG-case table's ``% MAC`` column
    restates an entered station in the reference the entered CG limits use,
    through :func:`station_to_pct_mac`, which is a change of units and not a
    derivation. Echoing an input is not recomputation -- OR-6 forbids
    re-deriving a value, not reporting one -- but a number that is none of the
    three is invented, and this is what says so.

    Checked against the modules run independently of the report and against the
    project itself, so a builder that quietly rescaled, re-rounded or derived a
    value shows up here rather than in a reviewer's comparison against the
    analysis pages.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    doc = _doc()
    printed = {cell for section in _flat([_section_two(doc)])
               for table in section.tables for row in table.rows
               for cell in row}

    sourced = set()
    for step in oc.analysis_steps():
        if step.key not in oc.IMPLEMENTED:
            continue
        # Every module the step runs, not just its primary one: a page whose
        # ``bas`` says "WTESTIMA+WTONECG+WTENV" produces numbers from all three,
        # and 2.2's loading-envelope table is WTENV's. ``workflow.step_modules``
        # is the owner of that set (the same one the navigation reads), so this
        # cannot drift from what the report actually runs.
        for module in wf.step_modules(step.key):
            for condition in registry.get(module)(project).conditions:
                for value in condition.values:
                    sourced.add(format_value(value.value))

    empennage = project.geometry.empennage
    echoed = ((empennage.htail, osec._HTAIL_ROWS),
              (empennage.vtail, osec._VTAIL_ROWS),
              (project.aileron_loads, osec._AILERON_ROWS),
              (project.flap_loads, osec._FLAP_ROWS))
    echoed += tuple((tab, osec._TAB_ROWS) for tab in project.tab_loads.tabs)
    for source, rows in echoed:
        for attr, _label, _units in rows:
            value = getattr(source, attr, None)
            if value is not None:
                sourced.add(format_value(value))
    mac_ref = mac_reference(project)
    for case in project.weight.cg_cases:
        sourced.update(format_value(v)
                       for v in (case.weight_lb, case.xcg, case.zcg))
        # The %MAC column is the *same* station in another reference, so its
        # source is the entered station put through the one relation's owner.
        # Deliberately narrow: only a case's own xcg, only through
        # ``station_to_pct_mac``, only against the resolver's reference -- a
        # column derived any other way, or from a second reading of the wing,
        # still lands in ``unaccounted``.
        sourced.add(format_value(station_to_pct_mac(case.xcg, mac_ref)))

    numeric = {cell for cell in printed
               if cell and (cell[0].isdigit() or cell[0] == "-")
               and cell != "--"}
    unaccounted = numeric - sourced
    assert not unaccounted, (
        f"section 2 prints numbers from no source: {sorted(unaccounted)}")


def test_section_two_marks_nothing_ultimate_and_states_no_safety_factor():
    """G-OR-4's other half: a non-load must not be scaled or marked.

    Section 2 states no load in force or moment units, so the whole section is
    checked rather than a chosen sample. Its load factors *are* loads -- n is a
    limit load factor -- but they are dimensionless and LIMIT, so the boundary
    passes them through unscaled and unmarked. The modules stamp
    ``safety_factor=1.5`` on these conditions anyway (note 44 OR-14, frozen code,
    filed not fixed), which is exactly the claim that must not reach the page.
    """
    doc = _doc()
    # The **cells**, not the rendered section: the lead prose legitimately uses
    # the string "-ULT" to explain why no table carries it, and a guard that read
    # the whole section failed on the sentence written to prevent the confusion
    # it was guarding against.
    for sub in _flat([_section_two(doc)]):
        for table in sub.tables:
            assert "SF" not in table.columns
            for row in table.rows:
                for cell in row:
                    assert "-ULT" not in cell, (
                        f"section 2 marked a non-load as ultimate: {row}")
            assert "SF=" not in (table.note or "")


def test_no_table_claims_a_load_factor_is_not_a_load():
    """A load factor **is** a load: n is a limit load factor.

    An earlier draft carried a note under every section 2 table reading
    "geometry, mass, speeds and load factors are not loads". That is wrong, and
    the owner had it removed outright rather than reworded (2026-08-30). The
    marker guarantee it was trying to explain is asserted against the cells in
    ``test_section_two_marks_nothing_ultimate_and_states_no_safety_factor``,
    which is where it belongs -- an explanation is not a guard.
    """
    doc = _doc()
    prose = [p for s in _flat([_section_two(doc)]) for p in s.body]
    notes = [t.note or "" for s in _flat([_section_two(doc)]) for t in s.tables]
    for text in prose + notes:
        lowered = text.lower()
        assert "are not loads" not in lowered, text
        assert "is not a load" not in lowered, text
        assert "none of them is a load" not in lowered, text


def test_reported_load_factors_are_identified_as_limit():
    """Where section 2 reports a load factor, it says the factor is LIMIT.

    The document may not say a load factor is not a load; what it must say is
    which of limit and ultimate it is, at the point the number appears.

    The V-n figures carry no caption of their own since 2026-08-31 -- four
    figures differing only in loading were printing one identical paragraph --
    so for them the identification is required of the subsection prose that
    governs all four, and their captions are required to stay empty rather than
    the rule becoming "a caption states it if it has one". Every other figure
    states it in its own caption, and every table in its note.
    """
    envelope = _envelope_section(_doc())
    vn = _vn_figures(envelope)
    assert vn, "section 2.4 produced no V-n figure"
    assert any("LIMIT" in text for text in envelope.body), envelope.body
    for figure in envelope.figures:
        if figure.key.startswith("vn_"):
            assert figure.caption == "", figure.key
        else:
            assert "LIMIT" in figure.caption, figure.key
    for table in envelope.tables:
        assert "LIMIT" in (table.note or ""), table.title


def test_the_envelope_boundary_order_is_the_analysis_order():
    """The declared traversal cannot drift from the module's own case order.

    ``_BOUNDARY_CASES`` is a hand-written closed traversal of the envelope. If
    FLTLOADS ever emits its corners in a different order, joining them in this
    one would draw a boundary that crosses itself -- visibly wrong, but only to
    somebody looking at the figure.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    result = registry.get("flight_envelope")(project)
    emitted = [osec._split_case(c.title) for c in result.conditions]
    emitted = [(block, case) for block, case in emitted if block]
    first = emitted[0][0]
    order = [case for block, case in emitted if block == first]
    boundary = [case for case in order if case in osec._BOUNDARY_CASES]
    assert boundary == list(osec._BOUNDARY_CASES), (
        "the declared envelope traversal disagrees with the analysis: "
        f"{boundary}")
    gusts = [case for case in order if case in osec._GUST_CASES]
    assert sorted(gusts) == sorted(osec._GUST_CASES)


def _vn_figures(section):
    """2.4's V-n diagrams -- the section also opens with the speed/altitude
    envelope, which is one figure of a different kind and not a block."""
    return [f for f in section.figures if f.key.startswith("vn_")]


def test_the_envelope_figures_plot_only_produced_design_points():
    """Every plotted vertex is a case the analysis returned (OR-6).

    The figure is the one place the report could invent a number without it
    appearing in a table, so the coordinates are checked against the cases
    themselves rather than against the corner table built from them.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    result = registry.get("flight_envelope")(project)
    produced = set()
    for condition in result.conditions:
        values = {v.key: v.value for v in condition.values}
        if "v_eas" in values and "load_factor_nz" in values:
            produced.add((values["v_eas"], values["load_factor_nz"]))

    figures = _vn_figures(_envelope_section(_doc()))
    assert figures, "section 2.4 produced no envelope figure"
    for figure in figures:
        for series in figure.data.series:
            for point in zip(series.x, series.y):
                assert point in produced, f"{figure.key} plots an invented point"
        for _label, x, y in figure.data.points:
            assert (x, y) in produced


def test_the_speed_altitude_envelope_opens_2_4_and_reaches_sea_level():
    """The envelope before its slices, and the whole of it.

    The V-n diagrams are cuts through the operating envelope at a stated
    altitude, so the envelope comes first. It is drawn from sea level rather
    than from the shoulder altitude, because the sub-shoulder half is where the
    boundaries are EAS-limited and the kink at the shoulder is the figure's
    point -- MACHLIM tabulates only the Mach-limited half, and a figure that
    started where the table starts would show a boundary with no beginning.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    section = _envelope_section(_doc())
    first = section.figures[0]
    assert first.key == "speed_altitude"
    assert [f.key for f in section.figures[1:]] == [
        f.key for f in _vn_figures(section)]

    shoulder = project.speeds.shoulder_altitude_ft
    assert shoulder > 0
    for series in first.data.series:
        assert min(series.y) == 0.0, series.name
        assert max(series.y) == project.speeds.mach_limit.max_operating_altitude_ft
        # Constant in EAS below the shoulder: the sea-level point and the
        # shoulder point are one speed, and it is MACHLIM's own first row.
        at = dict(zip(series.y, series.x))
        assert at[0.0] == at[shoulder]


def test_the_speed_altitude_envelope_plots_only_machlim_s_own_speeds():
    """G-OR-3 through the figure: no speed on it is the report's arithmetic.

    The sub-shoulder segment is the shoulder row held constant, not a second
    evaluation of it, so every x-coordinate must appear in MACHLIM's result.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    produced = {v.value for c in registry.get("mach_limit")(project).conditions
                for v in c.values}
    figure = _envelope_section(_doc()).figures[0]
    for series in figure.data.series:
        for x in series.x:
            assert x in produced, f"{series.name} plots an invented speed"


def test_vh_is_marked_at_sea_level_and_is_not_drawn_as_a_boundary():
    """Vh is entered at sea level and has no altitude behaviour here.

    ``speeds.vh_kt`` is the maximum level-flight speed at sea level; the
    analysis carries no variation of it with altitude. Drawn as a full-height
    line it would assert a boundary nothing computed, so it is a marker -- and
    it is not a limit speed, which the caption says.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    figure = _envelope_section(_doc()).figures[0]
    assert figure.data.points == [("Vh", float(project.speeds.vh_kt), 0.0)]
    assert "Vh" not in {s.name for s in figure.data.series}
    assert "not a limit" in figure.caption


def test_the_speed_altitude_envelope_has_one_builder_for_both_reports():
    """OR-7: the summary report and the oracle report draw one figure.

    Two documents drawing one airplane two ways is the defect the shared-owner
    rule exists to prevent, and this figure had a second construction in the
    summary report until 2026-08-31.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    shared = content.speed_altitude_plot_data(project)
    assert _envelope_section(_doc()).figures[0].data == shared


def test_an_airplane_with_no_mach_inputs_says_so_instead_of_drawing():
    """OR-32: an absent boundary is stated, never an empty axis."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    stripped = dataclasses.replace(
        project, speeds=dataclasses.replace(project.speeds, mach_limit=None))
    figure = osec._speed_altitude_figure(stripped)
    assert figure.data is None
    assert "no MACHLIM inputs are entered" in figure.absent_reason


def test_one_envelope_figure_per_loading_and_altitude():
    """Every block analysed is shown, and none is shown twice.

    The alternative considered was one overlaid diagram; it was rejected because
    a block that governs one component must not be the one a reader cannot see
    (owner's decision, 2026-08-30).
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    result = registry.get("flight_envelope")(project)
    blocks = {osec._split_case(c.title)[0] for c in result.conditions}
    blocks.discard("")
    figures = _vn_figures(_envelope_section(_doc()))
    assert len(figures) == len(blocks)
    assert len({f.key for f in figures}) == len(figures), "duplicate figure keys"
    for block in blocks:
        assert any(block in f.title for f in figures), f"{block} has no figure"


def test_a_paired_table_drops_a_units_column_no_row_fills():
    """A dimensionless pairing prints three columns, not a blank fourth.

    The limit manoeuvre load factors have no unit: n is dimensionless, which
    the section body states, and "g" would name an acceleration the table does
    not state. An empty ``Units`` column beside them reads as a unit somebody
    forgot to enter. The speeds table in the same subsection keeps its column,
    which is what says this is a blank-column rule and not a special case.
    """
    doc = _doc()
    speeds = [s for s in _flat([_section_two(doc)]) if s.tables][2]
    factors = next(t for t in speeds.tables if "load factors" in t.title)
    assert "Units" not in factors.columns
    assert all(len(row) == len(factors.columns) for row in factors.rows)

    design = next(t for t in speeds.tables if "design speeds" in t.title)
    assert design.columns[-1] == "Units"
    assert all(row[-1] for row in design.rows)

def test_the_paired_tables_pair_keys_the_modules_actually_produce():
    """A renamed result key must fail here, not empty a compliance column.

    The as-computed-beside-the-minimum pairing is the whole point of section
    2.3; a pair whose minimum key had gone stale would print a blank cell that
    reads as "no minimum applies".
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    keys = {v.key
            for condition in registry.get("structural_speeds")(project).conditions
            for v in condition.values}
    for _name, computed, minimum in osec._FACTOR_PAIRS + osec._SPEED_PAIRS:
        assert computed in keys, f"{computed} is not produced any more"
        assert minimum in keys, f"{minimum} is not produced any more"


def test_a_wing_area_is_stated_once_in_the_whole_section():
    """No number appears in two tables.

    Wing area is produced by the speeds module and printed under geometry, where
    a reader looks for it. It is skipped in 2.3 for that reason, and this is what
    stops the skip being quietly dropped.
    """
    doc = _doc()
    labels = [row[0] for section in _flat([_section_two(doc)])
              for table in section.tables for row in table.rows]
    assert labels.count("Wing area S") == 1


def test_a_far_reference_that_is_not_a_regulation_is_not_printed_as_one():
    """The configuration module's reference is ``"configuration"``.

    Printed through the normal path it produced "Certification basis: 14 CFR
    configuration" (GUI review, 2026-08-30). A citation a reader cannot look up
    is worse than none.
    """
    doc = _doc()
    prose = "\n".join(p for s in _flat([_section_two(doc)]) for p in s.body)
    assert "14 CFR configuration" not in prose
    assert "14 CFR 23.335" in prose, "a real citation was dropped with it"


def test_a_figure_lists_its_title_not_its_whole_caption():
    """The List of Figures is a list.

    Captions in a report a reviewer signs have to explain the figure, and without
    a short form every word of every caption was repeated in the front matter --
    four near-identical paragraphs for four envelopes (GUI review, 2026-08-30).
    """
    tex = ol.render_oracle_document(_doc())
    assert r"\caption[Flight envelope" in tex, "no short caption for the list"
    # The short form carries the title alone: the explanatory sentence appears
    # only inside the braces that follow it, never in the bracketed entry.
    for start in (i for i in range(len(tex)) if tex.startswith(r"\caption[", i)):
        entry = tex[start + len(r"\caption["):tex.index("]{", start)]
        assert "boundary is drawn" not in entry, (
            f"the list of figures carries a whole caption: {entry[:60]}...")


def test_the_echoed_surface_inputs_are_the_fields_the_project_still_has():
    """A renamed or dropped input field fails here, not silently in the PDF.

    Section 2.1's empennage and control-surface tables are the first values the
    report reads straight from the project rather than from a ``ModuleResult``.
    Nothing computes them, so nothing else would notice them going missing --
    the row would simply stop appearing, and a reader has no way to know a
    surface definition was dropped from a document that never claimed it.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    empennage = project.geometry.empennage
    sources = (
        (empennage.htail, osec._HTAIL_ROWS),
        (empennage.vtail, osec._VTAIL_ROWS),
        (project.aileron_loads, osec._AILERON_ROWS),
        (project.flap_loads, osec._FLAP_ROWS),
        (project.tab_loads.tabs[0], osec._TAB_ROWS),
    )
    for source, rows in sources:
        assert rows, "a surface with no declared rows prints nothing"
        for attr, label, _units in rows:
            assert hasattr(source, attr), (
                f"{type(source).__name__} no longer has {attr!r}")
            assert label.strip()


def test_every_control_surface_the_project_defines_gets_a_table():
    """Both tails, the aileron, the flap and each trim tab are stated."""
    section = _section_two(_doc())
    geometry = next(s for s in _flat([section]) if s.tables)
    titles = " | ".join(t.title for t in geometry.tables)
    for expected in ("Wing planform", "Horizontal tail", "Vertical tail",
                     "Aileron", "Flap", "Trim tab"):
        assert expected in titles, f"{expected} has no table: {titles}"
    # The tab names its surface in words, not by the analysis's own key.
    assert "htail" not in titles, "a surface key leaked into a table title"


def test_the_as_entered_statement_is_made_once():
    """Six surface tables each carrying it would read as boilerplate.

    Same finding as the units note earlier in this review: a note repeated under
    every table is one a reader learns to skip.
    """
    section = _section_two(_doc())
    geometry = next(s for s in _flat([section]) if s.tables)
    fragment = "as entered"
    assert sum(fragment in p for p in geometry.body) == 1
    for table in geometry.tables:
        assert fragment not in (table.note or ""), table.title


def test_the_cg_case_table_states_every_case_and_its_role_and_analysis():
    """Section 2.2 lists the weight and CG cases the analysis was given."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    section = _section_two(_doc())
    weights = [s for s in _flat([section]) if s.tables][1]
    table = next(t for t in weights.tables if "centre-of-gravity cases" in t.title)

    assert len(table.rows) == len(project.weight.cg_cases)
    for row, case in zip(table.rows, project.weight.cg_cases):
        assert row[0] == case.name
        # A flight case has no role, and says so rather than showing a blank
        # cell that reads as a value somebody forgot to enter.
        assert row[1] != ""
        if case.role is None:
            assert row[1] == "--"
        else:
            assert case.role.value.replace("_", " ") == row[1]
        analysis = row[table.columns.index("Analysis")]
        for kind in case.analyses:
            assert kind.value in analysis
    assert "ANALYSIS is" in (table.note or "")
    assert "ROLE applies to ground cases only" in (table.note or "")



def _cg_case_table(project):
    return osec._cg_case_table(project, UnitSystem.IMPERIAL)


def test_the_cg_case_table_states_xcg_in_percent_mac_from_the_one_reference():
    """A station and its %MAC name the same point, measured one way.

    The entered CG limits are given in %MAC and the cases in stations, so
    without this column the reader converts by hand -- against whichever
    XLEMAC and MAC they can find. The column is required to come from
    ``derived_geometry.mac_reference``, the single resolver the limit lines
    already use (C210-13), so a case and a limit on the page cannot end up
    measured from two different wings.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    table = _cg_case_table(project)
    column = table.columns.index("Xcg (% MAC)")
    ref = mac_reference(project)
    assert ref is not None
    for row, case in zip(table.rows, project.weight.cg_cases):
        assert row[column] == format_value(station_to_pct_mac(case.xcg, ref))

    # And the relation closes against the entered limit rather than only
    # against itself: CG1 sits on the aft gross CG limit, which is entered in
    # %MAC, so the column must reproduce that number.
    aft = project.weight.envelope.aft_gross_pct_mac
    cg1 = table.rows[[r[0] for r in table.rows].index("CG1")][column]
    assert abs(float(cg1) - aft) < 0.05, (cg1, aft)


def test_the_cg_case_table_prints_the_percent_mac_relation_and_its_reference():
    """The equation is stated, both ways round, with the pair it uses.

    A percentage of MAC is not checkable without the XLEMAC and MAC behind it,
    and this suite resolves that pair two ways (typed override, else the
    planform). The note therefore names the relation, its inverse and the
    source, so section 2.2 can be re-derived on paper.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    note = _cg_case_table(project).note or ""
    assert "%MAC = 100 (X - XLEMAC) / MAC" in note
    assert "X = XLEMAC + (%MAC / 100) MAC" in note
    ref = mac_reference(project)
    assert format_value(ref.xlemac) in note and format_value(ref.mac) in note
    assert "planform" in note


def test_a_case_table_with_no_mac_reference_says_so_instead_of_printing_zero():
    """G-OR-32: an unresolvable %MAC is stated absent, never printed as 0.

    ``station_to_pct_mac`` answers 0.0 on a degenerate MAC by contract, which
    is the right answer for a divide and the wrong one for a page: a column of
    zeroes reads as a centre of gravity at the leading edge.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    stripped = dataclasses.replace(
        project,
        geometry=None,
        weight=dataclasses.replace(
            project.weight,
            envelope=dataclasses.replace(project.weight.envelope,
                                         xlemac=None, mac=None)))
    assert mac_reference(stripped) is None
    table = _cg_case_table(stripped)
    column = table.columns.index("Xcg (% MAC)")
    assert {row[column] for row in table.rows} == {"--"}
    assert "not stated in %MAC" in (table.note or "")
    assert "%MAC = 100" not in (table.note or "")

def test_the_analysis_column_is_ordered_not_set_ordered():
    """``CgCase.analyses`` is a set, and set order is not a document property.

    Printing it directly would put the byte-determinism gates at the mercy of
    hash ordering -- which is exactly the kind of defect that passes locally and
    fails on another interpreter.
    """
    from sloads.models.enums import AnalysisKind

    assert set(osec._ANALYSIS_ORDER) == set(AnalysisKind), (
        "an AnalysisKind was added without a place in the printed order")
    both = [k for k in osec._ANALYSIS_ORDER
            if k in {AnalysisKind.GROUND, AnalysisKind.FLIGHT}]
    assert both == list(osec._ANALYSIS_ORDER)


def test_a_tail_table_states_where_its_planform_came_from():
    """Asked of the owner, never asserted.

    The empennage carries oracle-authoritative **scalars** (area, span) because
    that is all SELECT, TAILDIST and BALLOADS need; a spanwise distribution
    needs polylines, which a project may or may not enter (plan 09, T-1). A
    first draft of section 2.1 told every reader both tails were rectangles,
    which would be false for a project that had entered them -- the document
    stating an assumption the analysis did not make.
    """
    from sloads.tail_geometry import resolve_tail_planform

    project = reduce_to_oracle_inputs(io.load_project(_GA))
    section = _section_two(_doc())
    geometry = next(s for s in _flat([section]) if s.tables)

    for component, title in (("htail", "Horizontal tail"),
                             ("vtail", "Vertical tail")):
        planform = resolve_tail_planform(project, component)
        table = next(t for t in geometry.tables if t.title.startswith(title))
        basis = next(r for r in table.rows if r[0] == "Planform basis")
        assert basis[1] == osec._PLANFORM_BASIS[planform.assumed]
        # A derived planform says so in a word a reader cannot miss.
        assert ("DERIVED" in basis[1]) is planform.assumed

    # The prose warns about the rectangle only where one is actually used.
    warned = "treated as a rectangle" in " ".join(geometry.body)
    assumed = any(resolve_tail_planform(project, c).assumed
                  for c in ("htail", "vtail"))
    assert warned is assumed


# --------------------------------------------------------------------------- #
# 2.1's planform figures (OR-45: "each carries ... its planform figures")
# --------------------------------------------------------------------------- #
def _geometry_section(doc):
    """Section 2.1, which is the first subsection of the group that has tables."""
    return next(s for s in _flat([_section_two(doc)]) if s.tables)


def _planforms(doc):
    """``{figure key: figure}`` for 2.1's planform figures."""
    return {f.key: f for f in _geometry_section(doc).figures
            if f.key.startswith("planform_")}


def test_every_main_surface_has_a_planform_figure():
    """One figure per spec row, and the spec is the three main surfaces.

    Both directions. A surface added to ``_PLANFORM_FIGURES`` without a drawing,
    or a drawing that appears without a spec row, is the same defect from either
    side: the section's figures stop being derived from a declaration and start
    being whatever the builder happened to append.
    """
    figures = _planforms(_doc())
    expected = [key for key, _p, _t, _c, _f in osec._PLANFORM_FIGURES]
    assert list(figures) == expected
    assert expected == ["planform_wing", "planform_htail", "planform_vtail"]


def test_a_planform_key_reaches_its_own_emitter():
    """The registered keys and the minted keys are the same set.

    This is a guard against a specific near-miss already in the file: the V-n
    figures key themselves ``vn_<index>``, which never matches
    ``plots_tex._EMITTERS["vn"]`` and silently falls through to the default
    emitter. It is harmless there. A planform that fell through would lose
    ``axis equal image`` and be drawn to the wrong shape -- a figure that is
    wrong about geometry while looking entirely plausible.
    """
    from sloads.report.planform_tex import PLANFORM_KEYS

    doc = _doc()
    minted = {key for key, _p, _t, _c, _f in osec._PLANFORM_FIGURES}
    # 3.1's loads-reference-axis figure is a planform too: same emitter, same
    # equal axes, minted by its own builder rather than from the 2.1 table.
    minted.add(next(f.key for s in _flat(doc.sections) for f in s.figures
                    if f.key == "planform_wing_lra"))
    assert minted == set(PLANFORM_KEYS)
    for figure in list(_planforms(doc).values()) + [
            f for s in _flat(doc.sections) for f in s.figures
            if f.key == "planform_wing_lra"]:
        assert "axis equal image" in figure_body_tex(figure)


def test_a_planform_has_a_fill_for_every_control_surface_it_draws():
    """No spec may declare more children than there are fills to tell them apart.

    ``_planform_figure`` zips the children against ``REGION_STYLES``, and a zip
    stops at the shorter: a third control surface on one parent would be dropped
    from the drawing without a word. The bound is asserted here rather than
    guarded with a runtime branch, because the fix is to add a fill, not to
    degrade the figure.
    """
    from sloads.report.planform_tex import REGION_STYLES

    for _key, _parent, _title, children, _frame in osec._PLANFORM_FIGURES:
        assert len(children) <= len(REGION_STYLES)


def test_a_surface_without_polylines_states_why_instead_of_drawing():
    """§3.4: an absent figure says why; it never renders an empty axis.

    Asserted by taking the polylines away rather than by finding a project that
    happens to lack them, so the state is reachable in the test whatever the
    shipped examples grow.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    project.geometry.surfaces = [s for s in project.geometry.surfaces
                                 if s.name != "vtail"]
    doc = oc.build_oracle_document(project, _spec())
    figure = _planforms(doc)["planform_vtail"]
    assert figure.data is None
    assert "no vertical tail leading- and trailing-edge polylines" in \
        figure.absent_reason
    assert figure_body_tex(figure) == "", "an absent figure drew an axis anyway"


def test_the_vertical_tail_is_drawn_in_its_own_frame_and_never_mirrored():
    """The fin's second coordinate is a waterline, not a butt line.

    ``examples/baron_58.project.json`` enters its fin with ``symmetric: true``,
    so a figure that mirrored on that flag would draw a second fin hanging below
    the airplane. The frame decides, and this is the project that proves the flag
    does not.
    """
    project = reduce_to_oracle_inputs(io.load_project(_TWIN))
    assert project.geometry.by_name("vtail").symmetric, \
        "the twin's fin no longer carries the flag this test exists for"

    figure = _planforms(_doc(_TWIN))["planform_vtail"]
    assert "Waterline" in figure.data.y_label
    assert "Fuselage station" in figure.data.x_label
    # One outline, not two, and every plotted waterline is above the datum.
    assert len(figure.data.series) == 1
    assert all(y >= 0 for series in figure.data.series for y in series.y)


def test_a_planform_plots_only_entered_vertices():
    """OR-6 for a drawing: every vertex is a point the project states.

    The same assertion the envelope figures carry, for the same reason -- a
    figure is the one place the report could put a number on the page without it
    appearing in a table.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    doc = oc.build_oracle_document(project, _spec())
    for key, parent, _title, _children, frame in osec._PLANFORM_FIGURES:
        surface = project.geometry.by_name(parent)
        entered = set(surface.leading_edge) | set(surface.trailing_edge)
        if frame == "butt":
            entered |= {(x, -y) for x, y in entered}
        plotted = {osec._oriented(frame, x, y) for x, y in entered}
        for _label, x, y in _planforms(doc)[key].data.points:
            assert (x, y) in plotted, f"{key} marks a vertex nobody entered"


def test_a_planform_labels_a_region_with_the_area_its_table_prints():
    """"A number is printed once" (§3.3), extended to the figures.

    A figure that quoted an area from a second owner could disagree with the
    table directly beneath it, and the reader would have no way to tell which
    was the analysis.
    """
    section = _geometry_section(_doc())
    cells = {cell for table in section.tables for row in table.rows
             for cell in row}
    labelled = 0
    for figure in _planforms(_doc()).values():
        for series in figure.data.series:
            if ":" not in series.name:
                continue          # a region whose total area is not tabulated
            value = series.name.split(":", 1)[1].strip().split(" ")[0]
            assert value in cells, f"{series.name} quotes an untabulated number"
            labelled += 1
    assert labelled >= 4, "no figure labelled an area; the check proved nothing"


def test_a_planform_states_no_load_and_no_safety_factor():
    """G-OR-4 for the figures: section 2 marks nothing ultimate.

    The captions say so in words; this asserts it of the content, so a caption
    edited into a claim the numbers do not support fails here.
    """
    for figure in _planforms(_doc()).values():
        text = " ".join([figure.title, figure.caption]
                        + [s.name for s in figure.data.series]
                        + [figure.data.x_label, figure.data.y_label])
        assert "-ULT" not in text
        assert "SF=" not in text
        for unit in ("lbs", "lb-in", "ft-lb", "N-ULT", "Nm"):
            assert unit not in text


def test_a_half_entered_planform_is_refused_rather_than_drawn():
    """The figure asks the precondition owner, and says so instead of drawing.

    A one-point edge is the state the oracle GUI's curve editor persists after
    the first complete row (#71/PB-21), so it reaches a report built mid-entry.
    ``derived_geometry.require_integrable_planform`` is the single owner of that
    precondition and every other edge-polyline consumer asks it; a figure that
    did not would draw a shape nobody entered, which is worse than a traceback
    because it looks like an answer. G-OR-7 keeps the rest of the document
    building around it.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    wing = project.geometry.by_name("wing")
    wing.leading_edge = wing.leading_edge[:1]

    doc = oc.build_oracle_document(project, _spec())
    figures = _planforms(doc)
    assert figures["planform_wing"].data is None
    assert "cannot be drawn as entered" in figures["planform_wing"].absent_reason
    assert figure_body_tex(figures["planform_wing"]) == ""
    # The other surfaces are untouched: one bad slice does not empty the section.
    assert figures["planform_htail"].data is not None
    assert figures["planform_vtail"].data is not None


# --------------------------------------------------------------------------- #
# 2.2's weight/CG envelope figure (design note 45 WE-8)
# --------------------------------------------------------------------------- #
def _weights_section(doc):
    """Section 2.2, selected by the figure key it owns."""
    return next(s for s in _flat([_section_two(doc)])
                if any(f.key == "weight_cg" for f in s.figures))


def _weight_cg(doc):
    return next(f for f in _weights_section(doc).figures if f.key == "weight_cg")


def test_the_weight_cg_figure_draws_both_loading_edges():
    """The reason note 45 exists: half the envelope is the misleading half.

    On the GA6 the forward edge never leaves the structural box while the aft
    edge runs 2.2 in past the aft-gross limit, so a figure carrying only the
    forward one reads as containment where there is none."""
    data = _weight_cg(_doc()).data
    names = [s.name for s in data.series]
    assert "Forward loading envelope" in names and "Aft loading envelope" in names
    forward = next(s for s in data.series if s.name.startswith("Forward"))
    aft = next(s for s in data.series if s.name.startswith("Aft"))
    assert max(aft.x) > max(forward.x)
    # Both edges start at the minimum flight weight and end at the full loading.
    assert (forward.x[0], forward.y[0]) == (aft.x[0], aft.y[0])
    assert (forward.x[-1], forward.y[-1]) == (aft.x[-1], aft.y[-1])


def test_the_weight_cg_figure_reaches_its_own_emitter_and_closes_its_limits():
    """The limit envelope is drawn closed, not as three loose rules.

    Guards the ``vn_{index}`` fall-through class the planform figures were
    written against: ``weight_cg`` must hit ``_EMITTERS["weight_cg"]`` exactly."""
    figure = _weight_cg(_doc())
    tex = figure_body_tex(figure)
    assert tex and tex.count("addplot") >= 4
    polygon = next(s for s in figure.data.series if s.name == "Structural limits")
    assert (polygon.x[0], polygon.y[0]) == (polygon.x[-1], polygon.y[-1])


def test_the_weight_cg_figure_marks_every_entered_case_once():
    """Every CG case is marked; cases sharing a point share one marker.

    On the GA6 ``fwd light`` and ``CG3`` are the same loading (2800 lb @ 72.64),
    and two labels on one diamond is a smudge rather than information."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    data = _weight_cg(_doc()).data
    entered = {(c.xcg, c.weight_lb) for c in project.weight.cg_cases}
    assert len(data.points) == len(entered)
    named = {n for label, _x, _y in data.points for n in label.split(" / ")}
    assert named == {c.name for c in project.weight.cg_cases}
    assert any(" / " in label for label, _x, _y in data.points)


def test_the_envelope_vertex_table_is_wtenv_s_own_result():
    """G-OR-3: the table reproduces WTENV, it does not re-sweep the loadings."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    table = next(t for t in _weights_section(_doc()).tables
                 if t.title == "Loading envelope vertices")
    result = registry.get("weight_envelope")(project)
    printed = {row[0]: row[1:] for row in table.rows}
    for title, prefix, edge in (("Forward loading envelope", "point", "Forward"),
                                ("Aft loading envelope", "aft_point", "Aft")):
        condition = next(c for c in result.conditions if c.title.startswith(title))
        values = {v.key: v.value for v in condition.values}
        count = sum(1 for k in values if k.endswith("_weight"))
        assert count and sum(1 for r in table.rows if r[0].startswith(edge)) == count
        for i in range(1, count + 1):
            assert printed[f"{edge} {i}"] == [
                format_value(values[f"{prefix}_{i}_weight"]),
                format_value(values[f"{prefix}_{i}_station"]),
                format_value(values[f"{prefix}_{i}_waterline"])]


def test_the_weight_cg_figure_states_no_load_and_no_safety_factor():
    """G-OR-4: section 2 marks nothing ultimate and states no safety factor."""
    figure = _weight_cg(_doc())
    text = f"{figure.caption} {figure.data.x_label} {figure.data.y_label}"
    assert "-ULT" not in text and "SF" not in text
    assert "lb" in figure.data.y_label and "in" in figure.data.x_label


def test_a_project_with_no_weight_database_says_why_instead_of_drawing():
    """G-OR-7 / §3.4: an absent figure states its reason, never an empty axis.

    Tested at the builder, because through the *document* an empty weight data
    base takes WTONECG down with it and 2.2 goes ABSENT as a whole — OR-32's
    business, asserted below, not this figure's. The branch still earns its
    keep: the figure is built from a project, and a caller that reaches it with
    no loadings must get the sentence rather than an axis with nothing in it."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    project.weight.items = []
    figure = osec._weight_cg_figure(project, UnitSystem.IMPERIAL)
    assert figure.data is None
    assert "no itemized weight data base" in figure.absent_reason
    assert figure_body_tex(figure) == ""
    assert osec._envelope_vertex_table(None, UnitSystem.IMPERIAL) is None

    # And the document-level truth: the subsection is absent, figure and all.
    doc = oc.build_oracle_document(project, _spec())
    entry = next(e for e in doc.plan if e.title == "Weight and Mass Properties")
    assert entry.state is oc.SectionState.ABSENT
    assert not [f for s in _flat(doc.sections) for f in s.figures
                if f.key == "weight_cg"]
    assert "Loading envelope vertices" not in [
        t.title for s in _flat(doc.sections) for t in s.tables]


def test_the_limit_envelope_is_omitted_rather_than_half_drawn():
    """A limit envelope missing a side reads as permission.

    With no entered CG limits the loading edges still draw and the caption says
    the limits are absent -- the one way this figure could actively mislead is
    by showing a boundary that is not the airplane's."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    project.weight.envelope = None
    figure = _weight_cg(oc.build_oracle_document(project, _spec()))
    assert figure.data is not None
    assert [s.name for s in figure.data.series] == [
        "Forward loading envelope", "Aft loading envelope"]
    assert "CG limits are not entered" in figure.caption


# --------------------------------------------------------------------------- #
# Section 3 -- Wing Loads (OR-8 iteration 3, note 44 §11, ORACLE_REPORT.md 3.4)
# --------------------------------------------------------------------------- #
def _section_three(doc):
    """The Wing Loads section of ``doc``."""
    entry = next(e for e in doc.plan if e.step_key == "wing_loads")
    return next(s for s in _flat(doc.sections)
                if s.title == oc.heading(entry.number, entry.title))


def _appendix(doc, title):
    """The appendix section carrying ``title``."""
    return next(s for s in doc.sections
                if s.title == oc.appendix_heading(title))


def _wing_tables(doc):
    """Every table section 3 and its appendix print."""
    return ([t for s in _flat([_section_three(doc)]) for t in s.tables]
            + [t for s in _flat([_appendix(doc, oc.WING_LOAD_STATIONS)])
               for t in s.tables])


def test_the_wing_section_renders_its_four_subsections_numbered_by_the_owner():
    """3.1 ... 3.4, and the numbers come from the numbering owner.

    A builder that titled its own subsections "3.1" would be a second numbering
    scheme -- one that cannot renumber itself when a section is inserted above
    it, which is exactly the defect ``section_number`` exists to prevent one
    level up (F-R2).
    """
    doc = _doc()
    section = _section_three(doc)
    entry = next(e for e in doc.plan if e.step_key == "wing_loads")
    assert [s.title for s in section.subsections] == [
        oc.heading(oc.subsection_number(entry.number, index), title)
        for index, title in enumerate(
            ["Wing input data", "Load cases and sign convention",
             "Load cases assessed", "Critical load distributions"])]


def test_wing_loads_is_appendix_b_while_the_input_echo_holds_appendix_a():
    """G-OR-22 -- the reserved slot letters the appendix that follows it.

    The whole point of OR-50: shipping the wing-load appendix into an empty
    tuple would print it as Appendix A today and move it to B the moment the
    input echo lands, so an issue signed in between would disagree with its own
    reissue.
    """
    assert oc.appendix_letter(oc.INPUT_ECHO) == "A"
    assert oc.appendix_letter(oc.WING_LOAD_STATIONS) == "B"
    titles = [s.title for s in _doc().sections]
    assert titles[-2:] == ["Appendix A: Input echo",
                           "Appendix B: Wing loads by station"]


def test_the_reserved_appendix_states_its_state_and_is_not_pointed_at():
    """A slot is lettered, not referable -- the two are separate facts.

    Pointing a reader at a page that says "not yet implemented" is worse than
    pointing nowhere, which is the judgement ``see_appendix`` already makes for
    a dangling reference.
    """
    doc = _doc()
    echo = _appendix(doc, oc.INPUT_ECHO)
    assert echo.absent_lead == oc.STATE_TEXT[oc.SectionState.NOT_IMPLEMENTED][0]
    assert echo.absent_reason == oc.STATE_REASON[oc.SectionState.NOT_IMPLEMENTED]
    assert not echo.tables and not echo.figures
    assert oc.appendix_ref(oc.INPUT_ECHO) == ""
    assert oc.see_appendix(oc.INPUT_ECHO) == ""
    # The *report's* own Appendix A, not the theory manual's -- which the
    # introduction cites by name and must go on citing.
    assert "see Appendix A" not in "\n".join(
        p for s in _flat(doc.sections) for p in s.body)
    assert "Appendix A" not in "\n".join(oc.group_prose("loads_configuration"))


def test_every_load_the_wing_section_prints_is_marked_ultimate():
    """G-OR-20/G-OR-21 -- section 3 is where G-OR-4 stops being vacuous.

    Section 2 held the no-unmarked-load rule by carrying no force or moment at
    all (OR-44). Section 3 carries nothing else, so it holds it only by marking
    every one of them -- in the column header, where the unit is.
    """
    doc = _doc()
    loads = ("lb", "lbs", "lb-in", "N", "N*m", "kg")
    for table in _wing_tables(doc):
        for column in table.columns:
            if "(" not in column:
                continue
            units = column.rsplit("(", 1)[1].rstrip(")")
            if units.split("-ULT")[0] in loads and units not in ("lb", "kg"):
                assert units.endswith("-ULT"), (table.title, column)


def test_the_wing_root_loads_are_the_limit_result_times_the_case_factor():
    """G-OR-21 -- the printed value is the analysis's own, scaled once."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    result = registry.get("net_loads")(project)
    table = next(t for t in _wing_tables(_doc())
                 if t.title.startswith("Wing root loads"))
    column = table.columns.index("Root shear Sz (lbs-ULT)")
    for row, condition in zip(table.rows, result.conditions):
        limit = next(v.value for v in condition.values
                     if v.key == "root_shear_sz")
        assert row[column] == format_value(limit * condition.safety_factor)
        assert row[table.columns.index("SF")] == format_value(
            condition.safety_factor)


def test_every_wing_torsion_names_the_axis_it_is_stated_about():
    """G-OR-23 -- a torsion whose axis is unstated is not a load (OR-51).

    The oracle projection resets the loads reference axis to the quarter chord,
    which is the whole content of "for oracle loads the 25 per cent chord *is*
    the LRA": the report cannot print a 40 %-chord torsion because the document
    is a function of that projection (OR-43).
    """
    doc = _doc()
    axis = "25% chord"
    torsions = [c for t in _wing_tables(doc) for c in t.columns
                if c.startswith("Root torsion") or c.startswith("Myy")]
    assert torsions
    assert any(axis in c for c in torsions) or all(
        axis in (t.note or "") for t in _wing_tables(doc)
        if any(c.startswith("Myy") for c in t.columns))
    figure = next(f for s in _flat([_section_three(doc)]) for f in s.figures
                  if f.key == "wing_torsion_myy")
    assert axis in figure.title


def test_the_span_load_is_drawn_at_zero_unit_and_the_airplanes_own_clmax():
    """G-OR-24 -- three curves, and CLmax is an owner rather than a constant."""
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    clmax = project.aero_coeffs.cruise.stall_cl
    figure = next(f for s in _flat([_section_three(_doc())]) for f in s.figures
                  if f.key == "wing_span_load")
    names = [s.name for s in figure.data.series]
    assert names[:2] == ["CL = 0 (basic distribution)", "CL = 1.0"]
    assert names[2] == f"CL = CLmax = {format_value(clmax)}"
    assert "LIMIT" in figure.title and "LIMIT" in figure.caption


def test_the_span_load_curves_are_airloads_own_distribution():
    """OR-52 -- the report calls the owner once per CL, it does not combine.

    Asserted by equality with the module's own table rather than by inspecting
    the call: a report that reproduced the additive/basic sum itself would drift
    from AIRLOADS the first time the method moved, and would pass any test that
    only checked the shape of the curve.
    """
    import dataclasses as _dc

    from sloads.modules.airloads import resolve_aero_surfaces, schrenk_distribution

    project = reduce_to_oracle_inputs(io.load_project(_GA))
    surface = project.geometry.by_name("wing")
    aero = next(a for a in resolve_aero_surfaces(project) if a.name == "wing")
    figure = next(f for s in _flat([_section_three(_doc())]) for f in s.figures
                  if f.key == "wing_span_load")
    for series, cl in zip(figure.data.series,
                          [0.0, 1.0, project.aero_coeffs.cruise.stall_cl]):
        table = schrenk_distribution(surface, _dc.replace(aero, target_cl=cl))
        assert series.y == pytest.approx(table.ccl_total)
        assert series.x == pytest.approx(table.ye)


def test_a_project_with_no_flaps_down_set_says_so_and_draws_nothing():
    """G-OR-25 -- the missing half is stated, never filled with the clean set.

    The oracle prints two sets of span-load plots and this analysis can produce
    one: AIRLOADS does not model the lift discontinuity a deflected flap puts in
    the basic distribution. Printing the clean curves under a flaps-down heading
    would be the one failure mode that matters here (OR-53).
    """
    figure = next(f for s in _flat([_section_three(_doc())]) for f in s.figures
                  if f.key == "wing_span_load_flaps")
    assert figure.data is None
    assert "does not model the lift discontinuity" in figure.absent_reason
    assert "no flaps-down aerodynamic set" in figure.absent_reason


def test_the_wing_cases_are_one_set_seen_four_ways():
    """G-OR-26 -- 3.2, 3.3, 3.4 and the appendix state the same cases.

    Four projections of SELECT's own subset (OR-55). A section that registered
    three cases and plotted two would be describing an analysis nobody ran.
    """
    doc = _doc()
    register = next(t for t in _wing_tables(doc)
                    if t.title == "Wing load cases run")
    summary = next(t for t in _wing_tables(doc)
                   if t.title.startswith("Wing root loads"))
    stations = next(t for t in _wing_tables(doc)
                    if t.title.startswith("Applied wing loads by station"))
    cases = [row[0] for row in register.rows]
    assert cases and [row[0] for row in summary.rows] == cases
    assert sorted({row[0] for row in stations.rows}) == sorted(cases)
    for figure in [f for s in _flat([_section_three(doc)]) for f in s.figures
                   if f.key.startswith("wing_") and f.data is not None
                   and f.key != "wing_span_load"]:
        assert [s.name.split()[0] for s in figure.data.series] == cases


def _appendix_tables(doc):
    """``(B.1 applied, B.2 cumulative)``."""
    subs = _appendix(doc, oc.WING_LOAD_STATIONS).subsections
    return subs[0].tables[0], subs[1].tables[0]


def test_the_appendix_separates_the_applied_loads_from_the_carried_ones():
    """OR-56, restated 2026-09-03 -- B.1 is a deck, B.2 is what it should return.

    They were one table with both sets of columns, which invited exactly the
    reading that put this section's purpose at risk: a difference of the
    cumulative column taken for an applied load. Two tables, two headings.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results
    net = loads_ref_axis_results(project, build_net_loads(project).wing_net)
    applied, carried = _appendix_tables(_doc())

    for column in ("Fz (lbs-ULT)", "Fx (lbs-ULT)", "Myy free (lb-in-ULT)"):
        assert column in applied.columns
        assert column not in carried.columns
    for column in ("Sz (lbs-ULT)", "Mxx (lb-in-ULT)", "Myy (lb-in-ULT)"):
        assert column in carried.columns
        assert column not in applied.columns

    station, result = net[0].stations[0], net[0]
    row = applied.rows[0]
    assert row[applied.columns.index("Fz (lbs-ULT)")] == format_value(
        station.fz * result.safety_factor)
    assert carried.rows[0][carried.columns.index("Sz (lbs-ULT)")] == format_value(
        station.sz * result.safety_factor)


def test_the_applied_table_carries_the_point_every_load_acts_at():
    """A force without its point is half a load definition (owner review).

    X and Z were dropped to 3.1 when the table overflowed; an appendix a
    structural model is built from cannot make the reader fetch half the load
    definition from another section.
    """
    applied, carried = _appendix_tables(_doc())
    for axis in ("X (in)", "Y (in)", "Z (in)"):
        assert axis in applied.columns
    # The cumulative table keys on the station and does not repeat them.
    assert "X (in)" not in carried.columns


def test_the_appendix_table_and_the_exported_csv_are_one_load_set():
    """The SSOT gate: B.1 and ``wing_applied_loads.csv`` are two views of one list.

    The stress analyst reads the appendix and loads the CSV; if the two were
    built by separate row assemblers they could disagree about what is applied,
    and nothing would say which one the deck was solved from. Both go through
    ``sbeam_bridge.applied_load_rows``, and this asserts they still do -- row
    for row, value for value.
    """
    import csv as _csv

    from sloads.export.sbeam_bridge import applied_load_csv

    project = reduce_to_oracle_inputs(io.load_project(_TWIN))
    from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results
    net = loads_ref_axis_results(project, build_net_loads(project).wing_net)

    applied, _carried = _appendix_tables(_doc(_TWIN))
    rows = list(_csv.DictReader(applied_load_csv(net).splitlines()))
    assert len(rows) == len(applied.rows)
    ci = {c: applied.columns.index(c) for c in applied.columns}
    for table_row, csv_row in zip(applied.rows, rows):
        assert table_row[ci["Station"]] == csv_row["Station"]
        for col, key in (("X (in)", "X (in)"), ("Fz (lbs-ULT)", "Fz (lbs-ULT)"),
                         ("Myy free (lb-in-ULT)", "Myy free (lb-in-ULT)")):
            assert math.isclose(float(table_row[ci[col]].replace(",", "")),
                                float(csv_row[key]), abs_tol=1.0), (
                f"{col} disagrees on station {csv_row['Station']}")


def test_every_concentrated_wing_mass_is_a_row_of_the_applied_table():
    """The Baron's four wing masses, each at its own coordinates.

    Without them the applied set is short by most of the inertia relief -- the
    defect the OR-15 admission of 2026-09-03 was granted to fix, #166 -- and a short
    deck reads exactly like a complete one.
    """
    project = reduce_to_oracle_inputs(io.load_project(_TWIN))
    from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results
    net = loads_ref_axis_results(project, build_net_loads(project).wing_net)
    points = [pl for r in net for pl in r.point_loads]
    assert points, "the Baron enters concentrated wing masses"

    applied, _carried = _appendix_tables(_doc(_TWIN))
    station_column = applied.columns.index("Station")
    named = [row[station_column] for row in applied.rows]
    for pl in points:
        assert pl.name in named
    assert len(applied.rows) == sum(len(r.stations) for r in net) + len(points)

    # A point mass carries no free moment -- its every moment is its force
    # through an arm the coordinates state.
    free = applied.columns.index("Myy free (lb-in-ULT)")
    for row in applied.rows:
        if row[station_column] in {pl.name for pl in points}:
            assert float(row[free].replace(",", "")) == 0.0


def test_the_appendix_is_landscape_and_starts_a_fresh_page():
    """Back matter a reader turns to, not one that trails the section before it."""
    doc = _doc()
    station_appendix = _appendix(doc, oc.WING_LOAD_STATIONS)
    assert station_appendix.landscape and station_appendix.page_break
    echo = _appendix(doc, oc.INPUT_ECHO)
    assert echo.page_break, "every appendix starts a page, built or reserved"

    tex = ol.render_oracle_document(doc)
    assert r"\usepackage{pdflscape}" in tex
    assert tex.count(r"\begin{landscape}") == tex.count(r"\end{landscape}") == 1


def test_the_appendix_subsections_are_lettered_from_their_parent():
    """B.1 and B.2 -- composed by the numbering owner, never typed (F-R2)."""
    subs = _appendix(_doc(), oc.WING_LOAD_STATIONS).subsections
    letter = oc.appendix_letter(oc.WING_LOAD_STATIONS)
    assert [s.title.split()[0] for s in subs] == [f"{letter}.1", f"{letter}.2"]


def test_section_three_defines_every_symbol_its_tables_use():
    """The notation table is the one owner of increment-versus-cumulative.

    A column heading anywhere in section 3 or its appendix names a symbol from
    it; a heading that named something else would be a definition living only in
    the reader's head.
    """
    doc = _doc()
    notation = next(t for t in _wing_tables(doc) if t.title == "Notation")
    defined = {row[0] for row in notation.rows}
    assert {"X", "Y", "Z", "Fz", "Fx", "Myy free", "Sz", "Sx", "Mxx", "Myy"} <= defined
    senses = {row[0]: row[3] for row in notation.rows}
    assert senses["Fz"] == "increment" and senses["Sz"] == "cumulative"
    assert senses["Myy free"] == "increment" and senses["Myy"] == "cumulative"

    applied, carried = _appendix_tables(doc)
    for table in (applied, carried):
        for column in table.columns:
            symbol = column.split(" (")[0]
            if symbol in ("Case", "Station"):
                continue
            assert symbol in defined, f"{symbol!r} is used but not defined"


def test_section_three_states_how_the_cumulative_loads_are_built():
    """The recurrences, printed -- including which terms are transfer.

    A reader assembling a model from the appendix has to know that the Sz and Sx
    terms of Myy are position transfers the model generates for itself; there is
    no way to tell that from a column heading.
    """
    body = " ".join(_section_three(_doc()).subsections[1].body)
    assert "Sz(i) = Sz(i+1) + Fz(i)" in body
    assert "Mxx(i) = Mxx(i+1) + Sz(i+1) dy" in body
    assert "transfer" in body and "Only Myy free is applied." in body


def test_the_point_mass_rule_is_stated_only_where_there_is_one():
    """Stated for the Baron, absent for the GA6, which enters none."""
    def _text(path):
        return " ".join(_section_three(_doc(path)).subsections[1].body)

    assert "A concentrated wing mass" in _text(_TWIN)
    assert "A concentrated wing mass" not in _text(_GA)


def test_the_reference_axis_is_drawn_open_on_a_closed_planform():
    """OR-51 -- the axis is a line through the wing, not a region of it.

    Closing it would cut a chord from tip back to root that no part of the
    airplane follows, so the emitter draws a closed series and an open one
    differently and the content layer says which each is.
    """
    figure = next(f for s in _flat([_section_three(_doc())]) for f in s.figures
                  if f.key == "planform_wing_lra")
    outlines = [s for s in figure.data.series if s.closed]
    axes = [s for s in figure.data.series if not s.closed]
    assert outlines and axes
    assert all("Loads reference axis" in s.name or not s.name for s in axes)
    body = figure_body_tex(figure)
    drawn = [line for line in body.splitlines() if line.startswith("\\addplot")]
    assert sum(1 for line in drawn if line.rstrip().endswith("--cycle;")) == len(outlines)


def test_a_project_with_no_wing_loads_states_the_absence_and_still_builds():
    """G-OR-7 -- a half-filled project yields a complete document.

    Both halves are asserted: the section and its appendix have to say the same
    thing about the same missing analysis, because it is one absence seen twice
    and not two facts.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    project.wing_mass = None
    doc = oc.build_oracle_document(project, _spec())
    entry = next(e for e in doc.plan if e.step_key == "wing_loads")
    assert entry.state is oc.SectionState.ABSENT
    appendix = _appendix(doc, oc.WING_LOAD_STATIONS)
    assert appendix.absent_reason == oc.STATE_REASON[oc.SectionState.ABSENT]
    assert not appendix.tables


def _case_section(doc):
    """3.2, the run register."""
    return _section_three(doc).subsections[1]


def test_the_register_states_the_matrix_the_selection_actually_searched():
    """G-OR-27 -- a V-n point is a loading and an altitude, not just a speed.

    The reader's question this answers is a fair one: a V-n diagram states a
    speed and a load factor and says nothing about weight, centre of gravity or
    altitude, so a register that named twenty conditions would read as though
    the selection had twenty points to choose between rather than every
    combination of them.
    """
    from sloads.modules.flight_envelope import build_envelope

    project = reduce_to_oracle_inputs(io.load_project(_GA))
    points = build_envelope(project).vn
    body = " ".join(_case_section(_doc()).body)
    assert f"{len(points)} points" in body
    for cg in sorted({p.cg for p in points}):
        assert cg in body
    for altitude in sorted({p.altitude_ft for p in points}):
        assert f"{format_value(altitude)} ft" in body


def test_an_entered_wing_case_list_is_not_reported_as_the_selections_result():
    """OR-57 -- the register says where its cases came from.

    ``ga6_normal`` enters three wing cases, which override the six the selection
    finds; a section that presented those three as the outcome of a search would
    be describing an analysis nobody ran. Both the sentence and the table that
    marks each named condition run or not are asserted, because the case a
    section does *not* carry is the one a reader has no other way of finding.
    """
    doc = _doc()
    body = " ".join(_case_section(doc).body)
    assert "entered in this project, not the selection's own result" in body
    for name in ("PLAA", "PMAA", "NMAA"):
        assert name in body
    table = next(t for t in _case_section(doc).tables
                 if t.title.startswith("Critical wing conditions"))
    run = dict(zip([row[1] for row in table.rows],
                   [row[-1] for row in table.rows]))
    assert run == {"PHAA": "yes", "PLAA": "no", "PMAA": "no", "NMAA": "no",
                   "ACRL": "yes", "TORS": "yes"}


def test_a_project_that_enters_no_wing_cases_reports_the_selections_own_result():
    """The other half of OR-57, and the state the suite is designed for.

    With the entered override removed the wing runs every condition the
    selection names, and the register says so instead of explaining an override
    that is not there.
    """
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    project.wing_mass.cases = []
    doc = oc.build_oracle_document(project, _spec())
    body = " ".join(_case_section(doc).body)
    assert "the critical-load selection's own result" in body
    assert "not the selection's own result" not in body
    table = next(t for t in _case_section(doc).tables
                 if t.title.startswith("Critical wing conditions"))
    assert {row[-1] for row in table.rows} == {"yes"}


def test_the_register_states_what_the_sign_of_a_load_factor_means():
    """OR-58 -- `Nz = -3.8` is a +3.8 g condition, and the table says so.

    ``Nz`` in the wing case list is the **inertia** load factor, the negative of
    the airplane's flight load factor, because the inertia opposes the air load.
    A reader who does not know that reads a table of positive-g conditions as a
    table of negative ones -- which is what happened in the owner's review of
    this section.
    """
    table = next(t for t in _case_section(_doc()).tables
                 if t.title == "Wing load cases run")
    assert "negative of the airplane's flight load factor" in table.note
    assert "Nz = -3.8 is a +3.8 g condition" in table.note


def test_a_case_set_with_no_negative_load_factor_says_it_does_not_envelop():
    """OR-58 -- a set of positive-g cases alone does not envelop the wing.

    Invisible at a glance on the printed sign convention: every load factor in
    the table is a negative number whichever kind of condition it is. So it is
    stated, and it is stated from the data rather than asserted -- a project
    whose set does carry a negative case gets the other sentence.
    """
    body = " ".join(_case_section(_doc()).body)
    assert "no negative-load-factor case" in body
    assert "do not envelop the wing" in body
    assert "23.333(c)" in body

    # The other branch, from a set that does carry one: the sentence names it
    # rather than repeating the warning.
    project = reduce_to_oracle_inputs(io.load_project(_GA))
    project.wing_mass.cases = []
    other = " ".join(_case_section(
        oc.build_oracle_document(project, _spec())).body)
    assert "negative-load-factor condition" in other
    assert "do not envelop the wing" not in other
