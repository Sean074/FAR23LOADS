"""The `changes/` fragment contract and the release-cut builder (design notes 26, 28).

Closure writes a fragment, not an edit to `CHANGELOG.md` or the history file;
the release cut assembles them (changelog subsections; history entries rolled
to the top of `00_completed_development.md`, MD-4). Two things can rot: a
fragment that the builder cannot place (bad name, wrong shape) and would be discovered only at release time, and
the live history file growing back into the 9k-line record the split retired.
The first is a failure here; the second is a warning — size is a release-roll
trigger (`RELEASE_PROCESS.md` §4), not a defect in the change that crossed it.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import warnings

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHANGES = os.path.join(_ROOT, "changes")
_CHANGELOG = os.path.join(_ROOT, "CHANGELOG.md")
_HISTORY = os.path.join(_ROOT, "docs", "40_history", "00_completed_development.md")
_SCRIPT = os.path.join(_ROOT, "scripts", "build_changelog.py")

#: The live history file rolls into an archive at the next release cut once it
#: passes this (design note 26 D-4). Warn, do not fail.
HISTORY_LINE_THRESHOLD = 1500


def _builder():
    spec = importlib.util.spec_from_file_location("build_changelog", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bc():
    return _builder()


# --- the fragments on disk -------------------------------------------------


def test_every_fragment_on_disk_is_valid(bc):
    files = bc.load_fragments(_CHANGES)
    bc.parse_fragments(files)  # raises FragmentError naming the file


def test_changes_dir_holds_only_fragments_and_the_readme():
    stray = [n for n in os.listdir(_CHANGES) if not n.startswith(".") and n != "README.md" and not n.endswith(".md")]
    assert stray == [], f"non-fragment files in changes/: {stray}"


def test_changelog_still_has_an_unreleased_heading():
    with open(_CHANGELOG, encoding="utf-8") as fh:
        assert bc_unreleased(fh.read())


def bc_unreleased(text: str) -> bool:
    return "\n## [Unreleased]\n" in text


# --- the builder's pure functions ---------------------------------------


@pytest.mark.parametrize(
    "name",
    ["Foo.added.md", "foo.md", "foo.bar.baz.md", "foo_bar.added.md", "foo.improved.md", "foo.added.txt"],
)
def test_bad_fragment_names_are_refused(bc, name):
    with pytest.raises(bc.FragmentError, match=name.split(".")[0]):
        bc.validate_fragment(name, "- ok\n")


def test_non_bullet_body_is_refused(bc):
    with pytest.raises(bc.FragmentError, match="bullet"):
        bc.validate_fragment("foo.fixed.md", "**Foo.** not a bullet\n")


def test_merge_leads_with_fragments_and_keeps_legacy_text(bc):
    legacy = "\n### Added\n\n- **Old added.** text\n\n### Fixed\n\n- **Old fixed.**\n"
    frags = {"fixed": ["- **New fixed.**\n"], "changed": ["- **New changed.**\n"]}
    out = bc.merge_section(legacy, frags)
    assert out.index("### Added") < out.index("### Changed") < out.index("### Fixed")
    assert out.index("**New fixed.**") < out.index("**Old fixed.**")
    assert "**Old added.**" in out and "**New changed.**" in out
    assert "### Breaking" not in out and "### Removed" not in out


def test_cut_release_touches_only_the_unreleased_block(bc):
    log = (
        "# Changelog\n\n---\n\n## [Unreleased]\n\n### Fixed\n\n- **legacy**\n\n"
        "## [0.5.0] — 2026-08-13\n\n### Added\n\n- old\n"
    )
    out = bc.cut_release(log, {"added": ["- **frag**\n"]}, "0.6.0", "2026-08-20")
    head, _, tail = out.partition("## [0.5.0]")
    assert tail == " — 2026-08-13\n\n### Added\n\n- old\n"
    assert head.count("## [Unreleased]") == 1
    assert "## [0.6.0] — 2026-08-20\n\n### Added\n\n- **frag**\n\n### Fixed\n\n- **legacy**\n" in head
    assert head.index("## [Unreleased]") < head.index("## [0.6.0]")


def test_cut_release_without_unreleased_heading_is_an_error(bc):
    with pytest.raises(ValueError, match="Unreleased"):
        bc.cut_release("# Changelog\n\n## [0.5.0] — d\n", {}, "0.6.0", "2026-08-20")


# --- history fragments (design note 28 MD-4) ---------------------------


def test_history_fragment_shapes():
    bc = _builder()
    assert bc.validate_fragment("x.history.md", "- **Tier M (tier M, 2026-08-20)** — one paragraph\n") == "history"
    assert bc.validate_fragment("x.history.md", "## Step 14 — full step\n\n**Objective.** …\n") == "history"
    with pytest.raises(bc.FragmentError, match="history fragment"):
        bc.validate_fragment("x.history.md", "a plain paragraph\n")
    with pytest.raises(bc.FragmentError, match="empty"):
        bc.validate_fragment("x.history.md", "\n")


def test_roll_history_inserts_after_the_header_rule_and_keeps_the_rest_byte_identical(bc):
    history = "# Completed Development\n\nheader prose\n\n---\n\n- **Old (tier M)** — t\n\n**Step X**\n\nbody\n"
    out = bc.roll_history(history, ["- **New A** — a\n", "**Step B**\n\n**Objective.** b\n"])
    head, _, tail = out.partition("---\n")
    assert head == "# Completed Development\n\nheader prose\n\n"
    assert tail == (
        "\n- **New A** — a\n\n**Step B**\n\n**Objective.** b\n\n"
        "- **Old (tier M)** — t\n\n**Step X**\n\nbody\n"
    )
    assert bc.roll_history(history, []) == history


def test_roll_history_without_a_rule_is_an_error(bc):
    with pytest.raises(ValueError, match="rule"):
        bc.roll_history("# H\n\nno rule here\n", ["- **x** — y\n"])


def test_parse_separates_history_from_changelog_types(bc):
    out = bc.parse_fragments({"a.fixed.md": "- **f**\n", "b.history.md": "- **h** — p\n"})
    assert set(out) == {"fixed", "history"}


# --- the history file size ---------------------------------------------


def test_live_history_size_is_within_the_roll_threshold_or_warns():
    with open(_HISTORY, encoding="utf-8") as fh:
        n = sum(1 for _ in fh)
    if n > HISTORY_LINE_THRESHOLD:
        warnings.warn(
            f"docs/40_history/00_completed_development.md is {n} lines (> {HISTORY_LINE_THRESHOLD}): "
            "roll the previous release block into an archive at the next cut (RELEASE_PROCESS.md §4)",
            stacklevel=1,
        )


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
