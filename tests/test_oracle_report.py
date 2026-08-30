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


def test_each_gap_state_renders_under_its_own_lead():
    """The end of that story: what the reader actually sees on the page.

    Asserted through the rendered ``.tex`` rather than the model, because the
    defect lived entirely in the renderer -- the model was already right.
    """
    step = oc.analysis_steps()[1]
    cases = {
        oc.SectionState.NOT_IMPLEMENTED: _doc(),
        oc.SectionState.EXCLUDED: _doc(
            spec=_spec(excluded_steps=(step.key,)),
            implemented=frozenset({step.key})),
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


def test_not_implemented_outranks_selection_and_absence():
    """While a section has no builder, its state is that -- not "you excluded it"
    and not "your inputs are missing", neither of which is true."""
    spec = _spec(excluded_steps=tuple(s.key for s in oc.analysis_steps()))
    plan = oc.section_plan(Project(name="barely started"), spec)
    body = [e for e in plan if e.step_key]
    assert all(e.state is oc.SectionState.NOT_IMPLEMENTED for e in body)
    # ...but the user's choice is still visible, which is what the preflight
    # column exists for.
    assert all(e.selected is False for e in body)


def test_once_implemented_absence_outranks_exclusion():
    """OR-19's rule takes over as soon as a section can be built: *absent is not
    excluded*, and a reader is owed the reason that is true of their project."""
    step = oc.analysis_steps()[1]          # one with a `requires`
    assert step.requires, "pick a step whose inputs can be missing"
    spec = _spec(excluded_steps=(step.key,))
    plan = oc.section_plan(Project(name="empty"), spec,
                           implemented=frozenset({step.key}))
    entry = next(e for e in plan if e.step_key == step.key)
    assert entry.state is oc.SectionState.ABSENT
    assert entry.selected is False and entry.inputs_present is False


def test_a_deselected_section_is_still_in_the_document():
    """OR-19: stated exclusion, never omission. An analyst never receives a
    shortened document without being told it is one."""
    step = oc.analysis_steps()[0]
    doc = _doc(spec=_spec(excluded_steps=(step.key,)),
               implemented=frozenset({step.key}))
    titles = [section.title for section in doc.sections]
    assert any(step.title in title for title in titles)
    assert any(step.title == title for title, _ in doc.gaps)


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
                        "Signatures", "Distribution and marking",
                        "Sections in this issue", "Preflight", "Provenance",
                        "Build"]
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
                "report_spec_saved", "report_open", "report_baseline",
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
