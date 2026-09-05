"""**G-OR-73** — every deck and every bundle document states, per subcase, the
safety factor that was *not* applied, and the two agree.

Design note 49 §8, OR-117. This is the obligation that **replaces the multiply**.
Until 2026-09-05 a recipient could read the basis off the numbers: the deck said
"Loads are ULTIMATE (limit x SF=1.5)" and the cards had in fact been scaled by
1.5. OR-116 removes the scaling, so the sentence is now the *only* thing standing
between the recipient and a 1.5x error — and a sentence is exactly the kind of
thing that goes stale silently while every numeric gate stays green.

It already had. Five blocks in ``sbeam_bridge`` (fuselage, chordwise tail,
spanwise tail, control surface, and the wing's card block) still read "Loads are
ULTIMATE (limit x SF=1.5)" over LIMIT cards after the multiplies came out, and
two of them printed a derivation — ``= 1.5 x (LT25 + LT50)`` — for a sum that no
longer had the 1.5 in it. Nothing in the suite could see that, which is the
argument for this gate in one sentence.

What is asserted, per example, per artifact:

* **every card-bearing deck** names a case and states its basis for *each* case
  block, with no block left unstated and no orphan statement;
* the factor the deck states equals the case's own ``safety_factor`` — the
  governing table's number (:mod:`sloads.safety_factors`), not a literal;
* **every bundle document** that carries an ``SF`` column states one on every
  row, and it is the same case's same factor;
* therefore deck and document agree, through the one source both are checked
  against rather than through a string comparison that would pass if both drifted
  together.

Measured, not assumed: restoring one of those five sentences fails this file on
**all six fixtures** — the six ``test_every_deck_states_the_factor_it_did_not_apply``
cases plus ``test_no_deck_claims_a_factor_has_been_applied`` — while the rest of
the suite stays green, which is the same blind spot G-OR-72 was written for.

The two already-ultimate families (23.367(a)(2), 23.561(b)) are handled by the
same code path: :func:`sloads.export.sbeam_bridge.basis_sentence` states
"ALREADY ULTIMATE (SF=1.0) -- apply no further factor" for them, and the parser
below reads that as a stated 1.0. No shipped deck currently exports one, so the
branch is exercised directly in :func:`test_the_already_ultimate_sentence_is_read_as_a_stated_factor`
rather than left to a fixture that may never grow the case.
"""

import csv
import io as _io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: F401
from sloads import io
from sloads.export import sbeam_bridge as sb
from sloads.export.balanced_deck import balanced_deck
from sloads.export.lra_model import lra_model_bdf
from sloads.export.sbeam_bridge import basis_sentence
from sloads.modules.aileron import build_aileron
from sloads.modules.balance import build_balanced_cases
from sloads.modules.body_loads import build_body_loads
from sloads.modules.flap import build_flap
from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results
from sloads.modules.tab import build_tabs
from sloads.modules.tail_span import build_tail_span
from sloads.modules.taildist import build_tail_chordwise

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The same set the Imperial baseline freezes -- the GA single the oracle is
#: locked to, the twins, and the two concept configurations.
EXAMPLES = (
    "atr42_100.project.json",
    "cessna_210.project.json",
    "concept_heavy.project.json",
    "concept_regional_jet.project.json",
    "dhc8_dash8.project.json",
    "ga6_normal.project.json",
)


# --------------------------------------------------------------------------- #
# Reading a basis statement back off an artifact
# --------------------------------------------------------------------------- #
#: How a deck block names the case it belongs to. Two spellings because two
#: builders wrote them: the component and assembled decks emit a ``Case ID:``
#: line, and the LRA beam model names the id inside its one-sentence header.
_CASE_KEY = re.compile(r"Case ID: (\S+)|LRA model case (\S+) --")

#: The two halves of :func:`basis_sentence`, matched after the comment block has
#: been unwrapped. Matched as prose, not as an ``SF=`` token: ``SF=1.5`` on its
#: own would also match the old, now-false "Loads are ULTIMATE (limit x SF=1.5)"
#: and this gate exists precisely to fail on that sentence.
_LIMIT_BASIS = re.compile(
    r"Loads are LIMIT\. The 14 CFR 23\.303 safety factor SF=([0-9.]+) "
    r"is NOT applied here")
_ULT_BASIS = re.compile(r"Loads are ALREADY ULTIMATE \(SF=([0-9.]+)\)")


def _unwrapped(text: str) -> str:
    """Comment lines with their ``$`` and wrapping removed, joined into prose.

    Every basis statement in the tree is wrapped to the 72-column free-field card
    width, so it spans two or three lines on every deck; a line-oriented match
    would see none of them.
    """
    return " ".join(line.lstrip("$ ").strip() for line in text.splitlines())


def _stated_factor(block: str):
    """The factor a deck block states it did not apply, or ``None``."""
    prose = _unwrapped(block)
    for pattern in (_LIMIT_BASIS, _ULT_BASIS):
        found = pattern.search(prose)
        if found:
            return float(found.group(1))
    return None


def deck_statements(text: str):
    """``{case id: stated factor}`` for one deck, and its unstated case ids.

    Split on the case-naming line rather than on a blank line or a card prefix:
    the block layouts differ per builder (the assembled deck puts its cases in
    one LOADS section, the component decks concatenate whole blocks) and the case
    line is the one thing all of them have.
    """
    keys = list(_CASE_KEY.finditer(text))
    stated, missing = {}, []
    for i, match in enumerate(keys):
        case_id = match.group(1) or match.group(2)
        end = keys[i + 1].start() if i + 1 < len(keys) else len(text)
        factor = _stated_factor(text[match.start():end])
        if factor is None:
            missing.append(case_id)
        else:
            stated[case_id] = factor
    return stated, missing


def csv_factors(text: str, key: str = "Case"):
    """``{case: SF}`` off a bundle document's own ``SF`` column, or ``None``."""
    body = "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))
    rows = list(csv.DictReader(_io.StringIO(body)))
    if not rows or "SF" not in rows[0]:
        return None
    return {row[key]: row["SF"] for row in rows}


# --------------------------------------------------------------------------- #
# The artifacts, paired with the results they were built from
# --------------------------------------------------------------------------- #
def _try(fn, *args, **kwargs):
    """Build a channel, or report its absence -- an example that lacks a slice
    has no artifact, exactly as ``tests/imperial_baseline.py`` treats it."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, ZeroDivisionError, KeyError, IndexError, TypeError):
        return None


def _pairs(example: str):
    """``[(name, deck text, csv text or None, results)]`` for one example.

    The pairing is written out rather than derived: *which* results a deck was
    built from is the fact this gate turns on, and inferring it from the artifact
    would be inferring the very thing under test.
    """
    project = io.load_project(os.path.join(_ROOT, "examples", example))
    net = _try(build_net_loads, project)
    wing = loads_ref_axis_results(project, net.wing_net) if net is not None else None
    body = _try(build_body_loads, project)
    tail = _try(build_tail_chordwise, project)
    control = []
    for build in (build_aileron, build_flap, build_tabs):
        control += (_try(build, project) or [])
    spans = _try(build_tail_span, project) or {}
    balanced = _try(build_balanced_cases, project, []) or []

    from sloads.derived_geometry import sob_station

    out = []

    def add(name, deck, csv_text, results):
        if deck and results:
            out.append((name, deck, csv_text, list(results)))

    add("wing_cards", _try(sb.force_moment_cards, wing),
        _try(sb.span_load_csv, wing), wing)
    add("wing_stick",
        _try(sb.stick_model_bdf, wing, sob=sob_station(project)), None, wing)
    add("body_cards", _try(sb.body_force_moment_cards, body),
        _try(sb.body_span_load_csv, body), body)
    add("tail_cards", _try(sb.tail_force_moment_cards, tail),
        _try(sb.tail_chordwise_csv, tail), tail)
    add("control_cards", _try(sb.control_surface_force_moment_cards, control),
        _try(sb.control_surface_csv, control), control)
    for component in ("htail", "vtail"):
        results = spans.get(component) or []
        add(f"{component}_span",
            _try(sb.tail_span_force_moment_cards, results, component=component),
            _try(sb.tail_span_csv, results, component=component), results)
    add("balanced_deck", _try(balanced_deck, project), None, balanced)
    add("lra_model", _try(lra_model_bdf, project), None, balanced)
    return out


def _case_id(result) -> str:
    ref = getattr(result, "case_ref", None)
    return getattr(ref, "case_id", "") or ""


# --------------------------------------------------------------------------- #
# G-OR-73
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.split(".")[0])
def test_every_deck_states_the_factor_it_did_not_apply(example):
    """**G-OR-73**, first half: no subcase without a basis statement.

    An unstated block is the failure mode that matters. A recipient reading a
    deck whose neighbouring blocks all say "SF=1.5 is NOT applied" will read the
    silent one as saying the same thing, and it may be the one already-ultimate
    case in the file.
    """
    pairs = _pairs(example)
    assert pairs, f"{example}: no deck built -- the gate would be vacuous"
    for name, deck, _csv, results in pairs:
        stated, missing = deck_statements(deck)
        assert not missing, (
            f"{example}/{name}: case block(s) {missing} state no basis; every "
            f"subcase must state the factor it did not apply (note 49 OR-117)")
        assert stated, f"{example}/{name}: no case block found at all"
        expected = {_case_id(r) for r in results if _case_id(r)}
        # The assembled deck splits a handed case into -R/-L subcases, so the
        # deck's id set is a superset of the results'; every result must appear
        # in it under its own id or a handed suffix of it.
        for case_id in expected:
            assert any(k == case_id or k.startswith(case_id)
                       for k in stated), (
                f"{example}/{name}: case {case_id} exports cards but states "
                f"no basis")


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.split(".")[0])
def test_the_stated_factor_is_the_cases_own(example):
    """**G-OR-73**, second half: the number is the governing table's, per case.

    Checked against ``result.safety_factor`` rather than against the literal 1.5:
    a deck that hard-coded the common value would state the wrong factor for the
    two already-ultimate families the moment one is exported, and would do it
    silently.
    """
    for name, deck, _csv, results in _pairs(example):
        stated, _missing = deck_statements(deck)
        for result in results:
            case_id = _case_id(result)
            if not case_id:
                continue
            mine = [v for k, v in stated.items()
                    if k == case_id or k.startswith(case_id)]
            for value in mine:
                assert value == result.safety_factor, (
                    f"{example}/{name}: case {case_id} states SF={value} but "
                    f"its governing factor is {result.safety_factor}")


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.split(".")[0])
def test_the_deck_and_its_document_agree(example):
    """**G-OR-73**, third half: "and the two agree".

    Both are compared to the case's own factor rather than to each other, so a
    drift that moved deck and CSV together -- the same helper feeding both -- is
    still caught. The CSV is keyed by the case *name* and the deck by the case
    *id*; the result object is what joins them, which is why the pairing above is
    written out by hand.
    """
    for name, deck, csv_text, results in _pairs(example):
        if not csv_text:
            continue
        factors = csv_factors(csv_text)
        assert factors is not None, (
            f"{example}/{name}: the document carries no SF column; every "
            f"bundle document states the factor it did not apply")
        stated, _missing = deck_statements(deck)
        for result in results:
            case_id, case = _case_id(result), getattr(result, "case", "")
            assert case in factors, f"{example}/{name}: no SF row for {case!r}"
            assert float(factors[case]) == result.safety_factor, (
                f"{example}/{name}: document states SF={factors[case]} for "
                f"{case!r}; its governing factor is {result.safety_factor}")
            if case_id in stated:
                assert stated[case_id] == float(factors[case]), (
                    f"{example}/{name}: deck and document disagree on {case_id}")


#: Every way a shipped artifact has actually claimed its own numbers are
#: ultimate. Written as a list of spellings rather than a single phrase because
#: the first version of this scan matched only "Loads are ULTIMATE" and
#: "limit x SF" -- and missed two live sites that said the same thing in other
#: words: the balanced deck's "the cards below are ULTIMATE" (ten times per
#: deck) and the wing stick deck's "(closed-form, ULTIMATE)". A gate that
#: catches one phrasing of a false statement licenses every other phrasing.
_CLAIMS_ULTIMATE = (
    "limit x SF",
    "are ULTIMATE",
    "is ULTIMATE",
    "ULTIMATE)",
)

#: The one true use of the word on a deck: OR-118's already-ultimate families,
#: whose sentence necessarily contains "ULTIMATE" and must not be swept up.
_TRUE_ULTIMATE = "ALREADY ULTIMATE"


def test_no_deck_claims_a_factor_has_been_applied():
    """The sentence this gate was written to find, in its own assertion.

    ``basis_sentence`` is the only wording allowed to state the basis on a deck.
    Five blocks still said "Loads are ULTIMATE (limit x SF=...)" over LIMIT
    cards, and two more said it in different words -- which is why the scan
    below is a list of spellings, and why it covers the CSV twin as well as the
    deck. Kept as a whole-text scan so a builder this file does not pair cannot
    quietly grow an eighth.
    """
    for example in EXAMPLES:
        for name, deck, csv_text, _results in _pairs(example):
            for label, text in ((name, deck), (f"{name} csv", csv_text)):
                if not text:
                    continue
                # Blank the legitimate sentence first, so the spellings below
                # can stay broad.
                prose = _unwrapped(text).replace(_TRUE_ULTIMATE, "<ok>")
                for claim in _CLAIMS_ULTIMATE:
                    assert claim not in prose, (
                        f"{example}/{label}: says {claim!r} of its own numbers; "
                        f"under note 49 OR-116 every load sloads delivers is "
                        f"LIMIT and the factor is applied nowhere")


def test_the_already_ultimate_sentence_is_read_as_a_stated_factor():
    """OR-118's two families, exercised directly.

    No shipped fixture exports a 23.367(a)(2) or 23.561(b) case to a deck, so the
    already-ultimate branch of ``basis_sentence`` would otherwise be asserted by
    nothing -- and the parser above would be free to stop recognising it.
    """
    assert _stated_factor(f"$ Case ID: X\n$ {basis_sentence(1.0)}") == 1.0
    assert _stated_factor(f"$ Case ID: X\n$ {basis_sentence(1.5)}") == 1.5
    assert "apply no further factor" in basis_sentence(1.0)


def test_the_gate_would_catch_an_unstated_or_wrong_block():
    """The gate's teeth: a parser that matched nothing would pass every test above."""
    good = "$ Case ID: W-01\n$ " + basis_sentence(1.5) + "\nFORCE, 1, 2\n"
    stated, missing = deck_statements(good)
    assert stated == {"W-01": 1.5} and not missing
    # the sentence the five stale blocks carried -- read as no statement at all
    stale = "$ Case ID: W-01\n$ Loads are ULTIMATE (limit x SF=1.5).\n"
    stated, missing = deck_statements(stale)
    assert stated == {} and missing == ["W-01"]
    # and wrapping must not hide a good one
    wrapped = ("$ Case ID: W-01\n$ Loads are LIMIT. The 14 CFR 23.303 safety\n"
               "$   factor SF=1.5 is NOT applied here -- apply it in the\n"
               "$   sizing analysis.\n")
    assert deck_statements(wrapped)[0] == {"W-01": 1.5}


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
