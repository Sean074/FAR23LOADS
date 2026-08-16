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


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
