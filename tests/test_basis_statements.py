"""**G-OR-74** — no rendered document claims its own loads are ULTIMATE.

Design note 49 §8. G-OR-51 pins the ``-ULT`` *unit marker*; G-OR-73 pins the
*deck's* per-subcase sentence. Neither reads the prose of the documents that
travel beside them, and that is where the false statements survived longest.

The sweep that produced this gate found **~35 live string literals** still
asserting ULTIMATE after OR-116 had removed every multiply. They were not
comments: they were the words on the deliverable. Among them —

* the summary report's ``BASIS_STATEMENT``, printed on the title page and in §5:
  *"All loads are ULTIMATE (= limit x SF)"*;
* **Appendix A, the bundle manifest** — the controlling document's statement of
  every file and on what basis — whose basis column read ULTIMATE on fourteen
  rows, including the per-module CSVs, which had been LIMIT since note 48 and so
  were already wrong before this milestone;
* the compiled PDF's page footer, on *every page*: *"ULTIMATE loads --- SF stated
  per case"*;
* the oracle technical report's §1 basis paragraph and the issue package's README;
* the workbook's units line on both sheet channels.

Every numeric gate in the suite was green throughout. Nothing reads prose, so
nothing could see it — the same blind spot recorded for G-OR-72 (scale-invariant
deck checks) and G-OR-73 (stale deck comments), now closed on the third and last
surface.

**Scope.** Rendered output only: what a recipient actually reads. Docstrings and
code comments are swept by hand, not gated, because they carry no claim to anyone
outside the repository.

**The one true use of the word.** OR-118's two families — 23.367(a)(2) engine
torque and 23.561(b) emergency-landing inertia — *are* ultimate as computed, and
must keep saying so. Rather than exempt whole documents, the checker blanks the
sanctioned sentences first and then scans what is left, so an exemption cannot
quietly widen to cover a neighbouring false claim.
"""

import ast
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: F401
from sloads import io
from sloads.export.workbook import _unit_notes
from sloads.models.report import ReportSpec
from sloads.registry import run_all_modules
from sloads.report import content as rc
from sloads.report import latex as rl
from sloads.report import oracle_content as oc
from sloads.report import oracle_latex as ol
from sloads.report.conventions_tex import CONVENTION_TABLE_NOTE
from sloads.report.methods import methods_statement
from sloads.report.oracle_package import PACKAGE_SPEC, _units_sentence
from sloads.units import UnitSystem

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

#: The examples a full report renders on. Two is the right number here: this
#: gate reads prose, and prose does not vary with the airframe -- what varies is
#: which sections are present, so one GA single and one concept configuration
#: cover the branches that matter.
EXAMPLES = ("ga6_normal.project.json", "concept_regional_jet.project.json")


# --------------------------------------------------------------------------- #
# What may say ULTIMATE, and what may not
# --------------------------------------------------------------------------- #
#: Sentences that state the word truthfully: the two families 14 CFR prescribes
#: as already ultimate, and the regulation's own classification vocabulary.
#: Blanked before the scan rather than exempting the document that holds them --
#: a document-level exemption would also excuse a false claim written beside a
#: true one, which is exactly how the manifest's fourteen wrong cells survived
#: next to ``inertia_only.bdf``'s correct one.
_SANCTIONED = (
    "ALREADY ULTIMATE",
    "already ultimate",
    "prescribes the sudden-stoppage torque case as an ULTIMATE load",
    "prescribes ULTIMATE inertia load factors",
    "a load the regulation already prescribes",
    # the -ULT marker's own explanation, which must name what it marks
    "The -ULT marker appears only on",
    "-ULT marker appears only on a load the regulation prescribes",
)

#: Presentation that must not hide a claim from the scan. The GUI sweep (#192)
#: found the first version of this gate blind to its own subject matter twice
#: over: ``**ULTIMATE** = limit`` split the phrase with markdown emphasis, and
#: ``limit \u00d7 SF`` spelled the multiplication sign U+00D7 where ``_CLAIMS``
#: spelled it ASCII ``x``. Both are the *same sentence* a document elsewhere
#: wrote plainly, so normalising is not leniency -- it is what stops the gate
#: passing on typography.
def _normalise(text: str) -> str:
    """``text`` reduced to the form the claim patterns are written against."""
    for dash in ("\u2014", "\u2013"):
        text = text.replace(dash, "-")
    text = text.replace("\u00d7", "x")
    text = re.sub(r"[*`_]+", "", text)      # markdown emphasis and code spans
    return re.sub(r"\s+", " ", text)


#: How a document has actually claimed its own numbers are ultimate. Patterns,
#: not one phrase: the first version of the deck-side scan matched only "Loads
#: are ULTIMATE" and missed two live sites that said the same thing in other
#: words, and the GUI sweep then found five further shapes -- a download
#: *button label* that names no verb at all, and the "= limit x SF" gloss that
#: asserts the multiply without using the word in a claim position.
#:
#: ``(?![-\w])`` is load-bearing. A bare ``\b`` after ULTIMATE is satisfied by a
#: following hyphen, so ``"All speeds are ULTIMATE-independent design *limit*
#: speeds"`` -- a true sentence on the Structural Speeds page -- matched
#: ``"are ULTIMATE"`` and would have had to be exempted by hand.
_CLAIMS = (
    r"loads? (?:are|is) ULTIMATE(?![-\w])",
    r"\bare ULTIMATE(?![-\w])",
    r"\bis ULTIMATE(?![-\w])",
    r"\bULTIMATE loads?\b",
    r"\bULTIMATE \(CSV\)",
    r"\bULTIMATE \(limit x",
    r"\bULTIMATE = limit\b",
    r"\bULTIMATE files? (?:is|are) limit\b",
    r"\ball ULTIMATE\b",
    r",\s*ULTIMATE(?![-\w])",
    r"\breport(?:s|ed)? ULTIMATE(?![-\w])",
    r"limit x (?:1\.5|SF|the per-case SF|safety factor)",
)


def _residue(text: str) -> str:
    """``text``, normalised, with every sanctioned sentence blanked."""
    text = _normalise(text)
    for allowed in _SANCTIONED:
        text = text.replace(_normalise(allowed), "<sanctioned>")
    return text


def assert_states_limit(label: str, text: str, *, min_chars: int = 0) -> None:
    """The gate itself: ``text`` claims nothing ultimate of its own loads.

    ``min_chars`` is the vacuity guard. A substring scan passes trivially on an
    empty string, so a builder that quietly stopped emitting a document would
    turn this gate green rather than red -- the failure mode a "not in" assertion
    is most prone to.
    """
    assert len(text) >= min_chars, (
        f"{label}: rendered {len(text)} chars, expected at least {min_chars} -- "
        f"this gate cannot pass by rendering nothing")
    residue = _residue(text)
    for claim in _CLAIMS:
        assert not re.search(claim, residue), (
            f"{label}: matches {claim!r} of its own loads. Under note 49 OR-116 "
            f"every load sloads delivers is LIMIT and the safety factor is "
            f"stated, never applied — including in the exported deck.")


# --------------------------------------------------------------------------- #
# G-OR-74, surface by surface
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.split(".")[0])
def test_the_summary_report_states_limit(example):
    """The controlling document, rendered — title page, §3, §5 and Appendix A.

    Rendered to LaTeX rather than inspected as a tree, because the page furniture
    that carried the worst offender (the ``fancyfoot`` basis line, on every page
    of the compiled PDF) exists only in the render.
    """
    project = io.load_project(os.path.join(_EXAMPLES, example))
    results = run_all_modules(project)
    doc = rc.build_report(project, module_results=results, tool_version="test")
    tex = rl.render_document(doc)
    assert_states_limit(f"{example}: summary report", tex, min_chars=20_000)
    # ...and it does state the basis, rather than merely not stating the wrong one
    assert "LIMIT" in tex


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.split(".")[0])
def test_the_oracle_report_states_limit(example):
    """The oracle technical report — the surface note 48 OR-78 made ULTIMATE and
    note 49 OR-89/OR-116 brought back. Its §1 basis paragraph is the sentence a
    reader checks the numbers against before reading a single table."""
    project = io.load_project(os.path.join(_EXAMPLES, example))
    doc = oc.build_oracle_document(
        project,
        ReportSpec(title="FAR 23 Structural Design Loads",
                   report_number="LR-0142", revision="B", abstract="An abstract."))
    tex = ol.render_oracle_document(doc)
    assert_states_limit(f"{example}: oracle report", tex, min_chars=20_000)
    assert "LIMIT" in tex


def test_the_methods_statement_states_limit():
    """``METHODS.txt`` and the in-band CSV/BDF comment blocks come off one owner,
    so one assertion covers the stamp wherever it travels."""
    project = io.load_project(_GA)
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        text = methods_statement(project, system=system)
        assert_states_limit(f"methods ({system.value})", text, min_chars=1_000)
        assert "LIMIT" in text


def test_the_workbook_sheet_notes_state_limit():
    """Both channels: the human sheet and the solver sheet, which state different
    unit sets and used to state the same wrong basis."""
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        for name, note in _unit_notes(system).items():
            assert_states_limit(f"workbook {name} ({system.value})", str(note))


def test_the_package_and_convention_lines_state_limit():
    """The oracle issue package's README line and the conventions table's note --
    two single sentences that each speak for a whole archive."""
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        assert_states_limit(f"package basis ({system.value})",
                            _units_sentence(system))
    # The package spec's own per-file prose -- the ``units`` and ``conventions``
    # cells the manifest prints under every member, which is the same claim the
    # summary report's Appendix A got wrong on fourteen rows.
    for spec in PACKAGE_SPEC:
        for field in ("units", "conventions", "contents"):
            value = getattr(spec, field, "") or ""
            assert_states_limit(f"package spec {getattr(spec, 'name', spec)!r} "
                                f"{field}", str(value))
    assert_states_limit("convention table note", CONVENTION_TABLE_NOTE)


def test_the_report_basis_statement_says_who_applies_the_factor():
    """Stating LIMIT is half the job; OR-117 requires the document to say whose
    job the factor is. A report that says only "loads are LIMIT" leaves the
    recipient to guess whether sizing has already happened."""
    assert "LIMIT" in rc.BASIS_STATEMENT
    assert "applied nowhere" in rc.BASIS_STATEMENT
    assert "sizing analysis" in rc.BASIS_STATEMENT


#: One real sentence per ``_CLAIMS`` pattern, quoted from the artifact that
#: shipped it. Kept as data so the meta-test below can prove both directions:
#: each witness fails the gate, and each pattern catches some witness.
_WITNESSES = (
    "All exported loads are ULTIMATE.",
    "Load columns are **ULTIMATE** (limit \u00d7 SF), marked `-ULT`.",
    "The deliverable load is ULTIMATE.",
    "The deliverable **ULTIMATE** loads come from the Export page.",
    "Download net wing loads \u2014 ULTIMATE (CSV)",
    "Loads shown are ULTIMATE = limit \u00d7 1.5 (14 CFR 23.303).",
    "The two ULTIMATE files are limit \u00d7 the per-case `SF`.",
    "critical-reaction summaries, all ULTIMATE.",
    "All **33 cases** \u00d7 each loaded leg, ULTIMATE.",
    "The **Review/Export** pages report **ULTIMATE** loads.",
    "The ULTIMATE file is limit \u00d7 the per-case `SF` (14 CFR 23.303).",
)

#: The GUI trees this gate reads. ``oracle_app/`` is **excluded**: it is frozen
#: under note 44 OR-13, and its three surviving claims are filed, not fixed
#: (OR-14). Adding it here is the first step of that later ticket.
_GUI_TREES = ("app", "app_shell")


def _live_literals(path):
    """Every string literal in ``path`` that is not a docstring, with its line.

    Docstrings are excluded on G-OR-74's own scope rule -- they carry no claim
    to anyone outside the repository. Everything else in a Streamlit page is a
    candidate for the screen: ``st.caption``, ``st.markdown``, a
    ``download_button`` label, a ``help=`` tooltip.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                docs.add(id(first.value))
    return [(node.lineno, node.value) for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docs]


def test_no_gui_string_claims_ultimate():
    """G-OR-74 on its third surface: the screen (#192).

    Note 49's sweep was a one-off discovery pass, so the two rendered-document
    gates above stood while the GUI went on offering a *"Download net wing loads
    -- ULTIMATE (CSV)"* button over bytes identical to the module's LIMIT
    values. A reader who trusted that label under-sized by 1.5.

    This walks the source rather than driving Streamlit because the claims are
    static text: no session state, no example project and no widget interaction
    can change what the literal says, and an AST sweep cannot miss a page whose
    branch a journey test failed to enter.
    """
    seen = 0
    for tree in _GUI_TREES:
        assert os.path.isdir(os.path.join(_ROOT, tree)), tree
        for dirpath, _, filenames in os.walk(os.path.join(_ROOT, tree)):
            for filename in sorted(filenames):
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, _ROOT)
                for lineno, text in _live_literals(path):
                    seen += 1
                    assert_states_limit(f"{rel}:{lineno}", text)
    assert seen > 1000, (
        f"swept only {seen} literals -- this gate cannot pass by finding no "
        f"GUI source to read")


def test_the_gate_would_catch_each_spelling():
    """The checker's teeth, and the sanctioned-sentence carve-out's limits.

    Every spelling in ``_CLAIMS`` is one a real artifact used. The last two
    assertions are the ones that matter: a sanctioned sentence must not license a
    false claim sitting beside it.
    """
    for witness in _WITNESSES:
        with pytest.raises(AssertionError):
            assert_states_limit("witness", witness)
    # every pattern is exercised by at least one witness -- otherwise a pattern
    # could rot into one that matches nothing and this test would not notice
    for claim in _CLAIMS:
        assert any(re.search(claim, _residue(w)) for w in _WITNESSES), (
            f"no witness exercises {claim!r}")
    # the true sentences pass
    assert_states_limit("ok", "Loads are ALREADY ULTIMATE (SF=1.0) -- apply "
                              "no further factor.")
    assert_states_limit("ok", "23.561(b) prescribes ULTIMATE inertia load "
                              "factors for the emergency landing conditions.")
    # ...and do not cover a false claim written next to them
    with pytest.raises(AssertionError):
        assert_states_limit(
            "mixed", "Loads are ALREADY ULTIMATE (SF=1.0). All exported "
                     "loads are ULTIMATE.")


if __name__ == "__main__":
    import traceback

    failed = 0
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        marks = getattr(fn, "pytestmark", [])
        args = [a for m in marks for a in (m.args[1] if m.name == "parametrize"
                                           else [])]
        try:
            if args:
                for a in args:
                    fn(a)
            else:
                fn()
            print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
