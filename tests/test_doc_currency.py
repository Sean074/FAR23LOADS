"""Documentation-currency guards: no volatile literals in the standard docs, and
`docs/00_INDEX.md` ↔ the docs tree, both ways.

Two documentation defect classes kept shipping past the structural guards
(2026-08-15 review R6-D1…D8; `00_program_overview.md` said "schema currently 15"
while the constant was 52): a **number in prose that describes the code's
current state** (schema version, test count, coverage, "currently N"), and a
**doc file with no `00_INDEX.md` row** (or a row whose file is gone). Prose
cannot hold either current, so this asserts both — the same posture
`test_package_layout.py` takes for the package tree.

Scope is the *standard* — `README.md`, `CLAUDE.md`, `docs/00_INDEX.md`,
`docs/10_standard/`, `docs/20_theory/`. Plan notes, history and reviews are
dated statements and may carry any number; `DATA_DICTIONARY.md` is generated
and legitimately prints the schema version.

Stable facts are not volatile: `schema v46` as *provenance* ("added at v46")
never rots and is allowed; `SCHEMA_VERSION` next to a number is a claim about
*now* and is not. Rule text: `00_program_overview.md` §"Documentation currency".
"""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOCS = os.path.join(_ROOT, "docs")
_INDEX = os.path.join(_DOCS, "00_INDEX.md")

def _md_in(sub):
    return sorted(os.path.join("docs", sub, f) for f in os.listdir(os.path.join(_DOCS, sub)) if f.endswith(".md"))


#: Files whose prose must not state the code's current numbers.
_STANDARD_DOCS = (
    ["README.md", "CLAUDE.md", os.path.join("docs", "00_INDEX.md")] + _md_in("10_standard") + _md_in("20_theory")
)
_GENERATED = {os.path.join("docs", "10_standard", "DATA_DICTIONARY.md")}

#: (name, pattern) — each is a claim about the code's *current* state that a
#: constant, CI, or a generated file owns instead. Word-form numbers ("two
#: tests") and provenance citations ("schema v46") are deliberately not matched.
VOLATILE = [
    ("SCHEMA_VERSION with a number", re.compile(r"SCHEMA_VERSION\W{0,8}\d")),
    ("'currently' with a number", re.compile(r"\bcurrently\W{0,4}\d")),
    ("a test count", re.compile(r"\b\d[\d,]*\s+tests?\b")),
    ("a test-file count", re.compile(r"\b\d[\d,]*\s+test files\b")),
    ("a coverage percentage", re.compile(r"\bcoverage\W{0,20}\d+\s?%")),
    ("a version-is-now claim", re.compile(r"\bversion\W{0,4}(?:is|currently|now)\W{0,4}\d")),
    ("an item/commit count", re.compile(r"\b\d[\d,]*\s+(?:open |backlog )?(?:items|commits)\b")),
    # CR-D-5 (2026-08-20 review): `streamlit>=1.30` sat in the overview against a
    # real `>=1.36`. A version floor is `pyproject.toml`'s to state; a copy of one
    # is a claim about now, and this class was invisible to the patterns above.
    ("a dependency version specifier", re.compile(r"[A-Za-z][\w.-]*\s*[<>~!=]=\s*\d")),
]


def _lines(rel):
    with open(os.path.join(_ROOT, rel), encoding="utf-8") as fh:
        return fh.read().splitlines()


@pytest.mark.parametrize("rel", [d for d in _STANDARD_DOCS if d not in _GENERATED])
def test_standard_doc_states_no_volatile_literal(rel):
    hits = []
    for n, line in enumerate(_lines(rel), 1):
        for name, pat in VOLATILE:
            if pat.search(line):
                hits.append(f"{rel}:{n}: {name} — {line.strip()[:100]}")
    assert not hits, (
        "volatile literal(s) in a standard doc — point at the owner (constant / CI / generated file) instead:\n  "
        + "\n  ".join(hits)
    )


# --- INDEX ↔ tree ---------------------------------------------------------

_INDEX_LINK = re.compile(r"\]\(((?:[0-9]{2}_[a-z_]+|\.\.)/[^)#]+\.md)\)")


def _docs_tree():
    out = set()
    for sub in sorted(os.listdir(_DOCS)):
        d = os.path.join(_DOCS, sub)
        if not os.path.isdir(d) or sub.startswith("__"):
            continue
        for f in os.listdir(d):
            if f.endswith(".md"):
                out.add(f"{sub}/{f}")
    return out


def _index_links():
    with open(_INDEX, encoding="utf-8") as fh:
        return set(_INDEX_LINK.findall(fh.read()))


def test_every_doc_has_an_index_row():
    missing = sorted(_docs_tree() - _index_links())
    assert not missing, f"docs/ files with no row in docs/00_INDEX.md: {missing}"


def test_every_index_row_points_at_a_file():
    dangling = sorted(
        link for link in _index_links() if not os.path.exists(os.path.normpath(os.path.join(_DOCS, link)))
    )
    assert not dangling, f"docs/00_INDEX.md rows whose file does not exist: {dangling}"


# --------------------------------------------------------------------------- #
# The release-state statement has one owner (owner ruling 2026-08-28,
# production-release review §3.5/§5.3)
# --------------------------------------------------------------------------- #
#: The documents that must carry the release-state sentence verbatim. Markdown
#: cannot import a symbol, so "one owner" is enforced the only way prose allows:
#: the owner's exact string has to appear, and a second spelling of it must not.
_RELEASE_STATE_DOCS = ("README.md", "CAPABILITIES.md")

#: Files allowed to hold the sentence *as a literal* -- the owner itself, this
#: guard, and the two documents above. Anywhere else is a second copy.
_RELEASE_STATE_OWNER = os.path.join("app_shell", "components.py")


def test_the_release_state_is_stated_by_one_owner():
    """`README.md`, `CAPABILITIES.md` and both GUIs' About panel say the same
    thing about what this release is, because they all trace to one string.

    The claim is mixed by nature -- an oracle GUI that is finished beside an
    `app/` that is not -- and `Development Status` takes a single trove value,
    so `pyproject.toml` carries `4 - Beta` and the sentence carries the rest.
    Four hand-written copies of that sentence would disagree by the second cut,
    which is the documentation-currency failure this whole file exists for; the
    two markdown files cannot import the constant, so their copies are pinned
    to it here instead.
    """
    from app_shell.components import RELEASE_STATE

    for rel in _RELEASE_STATE_DOCS:
        with open(os.path.join(_ROOT, rel), encoding="utf-8") as fh:
            assert RELEASE_STATE in fh.read(), (
                f"{rel} does not carry app_shell.components.RELEASE_STATE verbatim -- "
                "update the document in the same change as the constant")

    # The About panel consumes the symbol rather than re-typing the sentence, so
    # a user in the beta front-end is told so by the same owner (#129's sibling
    # concern: the classifier is read by pip, not by them).
    with open(os.path.join(_ROOT, "app_shell", "sidebar.py"), encoding="utf-8") as fh:
        assert "RELEASE_STATE" in fh.read(), "the About panel must consume the owner"


def test_no_second_spelling_of_the_release_state():
    """A literal copy anywhere outside the owner and the two documents it pins.

    The `LANDING_L_FAR_CAPTION` posture (`tests/test_landing.py`): stating the
    string once is only half of one owner -- the other half is that nobody
    spells it again somewhere the guard above would never look.
    """
    from app_shell.components import RELEASE_STATE

    # A distinctive fragment rather than the whole sentence: a second copy that
    # drifted by a word is exactly the case this must still catch.
    fragment = RELEASE_STATE.split(";")[0].strip()
    allowed = {os.path.normpath(p) for p in
               (_RELEASE_STATE_OWNER, os.path.join("tests", "test_doc_currency.py"))
               } | {os.path.normpath(d) for d in _RELEASE_STATE_DOCS}
    offenders = []
    for base, dirs, files in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in
                   {".git", ".venv", "__pycache__", ".pytest_cache", "reference",
                    "sloads.egg-info", "_to_delete", "_staging_tmp2", "projects"}]
        for name in files:
            if not name.endswith((".py", ".md", ".toml")):
                continue
            rel = os.path.normpath(os.path.relpath(os.path.join(base, name), _ROOT))
            if rel in allowed:
                continue
            with open(os.path.join(base, name), encoding="utf-8", errors="ignore") as fh:
                if fragment in fh.read():
                    offenders.append(rel)
    assert not offenders, (
        "the release-state sentence is spelled a second time in "
        f"{offenders} -- import app_shell.components.RELEASE_STATE instead")


# --------------------------------------------------------------------------- #
# A design note cannot claim work is unbuilt after it has shipped (#128)
# --------------------------------------------------------------------------- #
# It blocks a release rather than trailing it: `RELEASE_PROCESS.md` §4 step 3
# rolls the notes into `docs/40_history/` at the cut, so an "unbuilt" claim
# enters the permanent record of the release that built it. Two instances found
# together (production-release review 2026-08-27 §3.3): note 32 said "everything
# else is unbuilt" of the oracle GUI whose every step had shipped, note 35 said
# "Nothing below is built yet" of work that shipped as #100.
#
# The evidence is deliberately **in-repo**. Whether an issue is closed lives on
# GitHub, which CI has no credential to read (the same constraint
# `tests/test_ci_conformance.py` is built around) -- but a closed item leaves a
# `changes/` fragment behind by the tiered-closure rule, and that fragment cites
# the note. So the fragment is the proxy, and it is a faithful one: it exists
# because something closed.
_NOTES_DIR = os.path.join("docs", "30_future")
_CHANGES = os.path.join(_ROOT, "changes")
#: Claims that work in this note has not been done. Kept literal rather than
#: clever -- a guard that guesses at prose fails on innocent sentences, and the
#: two spellings this file exists for are the two the review found.
_UNBUILT_CLAIM = re.compile(
    r"(everything else is unbuilt"
    r"|\bis unbuilt\b"
    r"|nothing (?:below|here)[^.]{0,40}\bbuilt\b"
    r"|not built yet"
    r"|no code has been written)", re.I)
#: A note's own record that some of it shipped.
_SHIPPED_MARK = re.compile(r"(✅|\bSHIPPED\b|\bBUILT\b)")


def _design_notes():
    directory = os.path.join(_ROOT, _NOTES_DIR)
    return sorted(n for n in os.listdir(directory) if n.endswith("_note.md"))


def _fragments_citing(note_name):
    """Closure fragments that name this note (``note 35``), i.e. it shipped."""
    number = note_name.split("_", 1)[0].lstrip("0")
    cite = re.compile(rf"\bnote {number}\b", re.I)
    if not os.path.isdir(_CHANGES):
        return []
    out = []
    for name in sorted(os.listdir(_CHANGES)):
        if not name.endswith(".md") or name == "README.md":
            continue
        with open(os.path.join(_CHANGES, name), encoding="utf-8") as fh:
            if cite.search(fh.read()):
                out.append(name)
    return out


@pytest.mark.parametrize("note", _design_notes())
def test_a_design_note_does_not_claim_unbuilt_work_it_has_shipped(note):
    text = "\n".join(_lines(os.path.join(_NOTES_DIR, note)))
    claims = [m.group(0) for m in _UNBUILT_CLAIM.finditer(text)]
    if not claims:
        return
    evidence = []
    if _SHIPPED_MARK.search(text):
        evidence.append("the note itself marks work SHIPPED/BUILT/✅")
    fragments = _fragments_citing(note)
    if fragments:
        evidence.append("closure fragment(s) cite it: " + ", ".join(fragments))
    assert not evidence, (
        f"{note} still claims unbuilt work ({claims}) while {'; '.join(evidence)}. "
        "Restate the Status line for what shipped -- notes 36/37 (SHIPPED) and 34 "
        "(AGREED …; BUILT …) are the model. RELEASE_PROCESS.md §4 step 3 rolls "
        "this note into docs/40_history/ at the cut, so the claim would enter the "
        "permanent record of the release that built it (#128)."
    )


def test_the_unbuilt_guard_would_catch_the_two_it_was_written_for():
    """A guard whose pattern no longer matches its own founding instances is a
    guard that passes because it sees nothing. These are the exact sentences
    note 32 and note 35 carried on 2026-08-27."""
    for sentence in ("an independent tier-S fix; everything else is unbuilt.",
                     "state plus the existing load increment, nothing more. "
                     "Nothing below is built yet."):
        assert _UNBUILT_CLAIM.search(sentence), sentence


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
