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
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads import registry  # noqa: E402
from sloads import workflow as wf  # noqa: E402
from sloads.field_registry import reduce_to_oracle_inputs  # noqa: E402
from sloads.models import Project  # noqa: E402
from sloads.models.report import ReportSpec, SignatureRow  # noqa: E402
from sloads.report import oracle_content as oc  # noqa: E402
from sloads.report import oracle_latex as ol  # noqa: E402
from sloads.units import UnitSystem  # noqa: E402

_EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_TWIN = os.path.join(_EXAMPLES, "baron_58.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")

_SOURCES = ("sloads/report/oracle_content.py", "sloads/report/oracle_latex.py",
            "sloads/report/oracle_package.py")


def _spec(**kwargs) -> ReportSpec:
    base = dict(title="FAR 23 Structural Design Loads", report_number="LR-0142",
                revision="B", abstract="An abstract.")
    base.update(kwargs)
    return ReportSpec(**base)


def _doc(path=_GA, spec=None, **kwargs):
    return oc.build_oracle_document(io.load_project(path), spec or _spec(),
                                    **kwargs)


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
    assert [e.number for e in plan] == [str(i + 1) for i in range(len(plan))]
    first_body = plan[len(oc.FRONT_SECTIONS)]
    assert first_body.number == str(len(oc.FRONT_SECTIONS) + 1)


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
    step = oc.analysis_steps()[1]
    assert step.requires, "pick a step whose inputs can be missing"
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
    titles = [section.title for section in doc.sections]
    assert not any(step.title in title for title in titles), (
        "a deselected section was printed")
    tex = ol.render_oracle_document(doc)
    assert step.title not in tex
    assert "excluded by user selection" not in tex.lower()

    # The printed numbers run 1..N with no hole, and the plan agrees with them.
    numbers = [int(e.number) for e in doc.plan if e.number]
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"deselection left a hole in the section numbering: {numbers}")
    assert len(doc.sections) == len(numbers)
    # The excluded step keeps its plan row, so the page's preflight can still
    # show the author that their choice registered.
    excluded = [e for e in doc.plan if e.step_key == step.key]
    assert len(excluded) == 1 and excluded[0].state is oc.SectionState.EXCLUDED
    assert excluded[0].number == ""


# --------------------------------------------------------------------------- #
# G-OR-7 -- absence is content
# --------------------------------------------------------------------------- #
def test_a_half_filled_project_yields_a_complete_document():
    """No traceback, and no silently missing section."""
    doc = oc.build_oracle_document(Project(name="half"), _spec())
    assert len(doc.sections) == len(doc.plan)
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
    assert len(doc.sections) == len(doc.plan)
    for entry, section in zip(doc.plan, doc.sections):
        assert section.title.startswith(entry.number + ".")
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
    tex = ol.render_oracle_document(_doc())
    for title, noun in (("List of Figures", "figures"), ("List of Tables", "tables")):
        assert f"This issue contains no {noun}." in tex
        assert r"\addcontentsline{toc}{section}{" + title + "}" in tex


def test_a_populated_front_matter_list_does_not_claim_to_be_empty():
    """The emptiness test looks into subsections too: a table one level down
    still puts a line in the list, and the document would otherwise state the
    opposite of what the reader is looking at."""
    from sloads.report.content import Section, Table

    doc = _doc()
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
