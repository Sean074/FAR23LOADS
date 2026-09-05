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

import os
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

#: How a document has actually claimed its own numbers are ultimate. Spellings,
#: not one phrase: the first version of the deck-side scan matched only "Loads
#: are ULTIMATE" and missed two live sites that said the same thing in other
#: words.
_CLAIMS = (
    "loads are ULTIMATE",
    "load is ULTIMATE",
    "are ULTIMATE",
    "is ULTIMATE",
    "ULTIMATE loads",
    "limit x SF",
)


def _residue(text: str) -> str:
    """``text`` with every sanctioned sentence blanked, ready to scan."""
    for allowed in _SANCTIONED:
        text = text.replace(allowed, "<sanctioned>")
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
        assert claim not in residue, (
            f"{label}: says {claim!r} of its own loads. Under note 49 OR-116 "
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


def test_the_gate_would_catch_each_spelling():
    """The checker's teeth, and the sanctioned-sentence carve-out's limits.

    Every spelling in ``_CLAIMS`` is one a real artifact used. The last two
    assertions are the ones that matter: a sanctioned sentence must not license a
    false claim sitting beside it.
    """
    for claim in _CLAIMS:
        with pytest.raises(AssertionError):
            assert_states_limit("witness", f"prose {claim} more prose")
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
