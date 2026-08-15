"""`PROJECT_GUIDE.md` §4's tree is the package on disk (R6-D5 guard).

CLAUDE.md names that tree the authoritative package layout, and its whole point
is telling a reader **where the single sources live**. It had drifted far enough
that none of `cg_cases.py`, `safety_factors.py` or `gear_loads.py` — three SSOT
owners added in one cycle — appeared in it, along with `case_ids.py`,
`rigid_body.py`, `tail_geometry.py`, `aero_curves.py`, `migrations.py`, the
whole `models/` package split, and three `export/` lines mis-nested under
`mass_distribution.py`.

Prose cannot hold a file listing current, so this asserts it, **both ways**: a
new module that never reaches the tree fails, and so does a tree line whose file
does not exist. The parse is structural rather than a substring search — the
path is rebuilt from the box-drawing indentation — so a file listed under the
wrong parent is a failure too, which is the defect that shipped.

Scope is the `sloads/` package alone (user decision, 2026-08-15). The rest of
the tree — `app/`, `tests/`, `examples/`, `docs/` — stays illustrative: those
churn per view and per test, `app/views` is already generated from
`workflow.py` and guarded there, and the tree exists to locate the calc SSOTs.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GUIDE = os.path.join(_ROOT, "docs", "10_standard", "PROJECT_GUIDE.md")

#: Files every package has and no reader needs a tree line for.
_IGNORED = {"__init__.py"}

_CONNECTOR = re.compile(r"^((?:(?:│|\|)?\s{3,4})*)(?:├──|└──)\s+(\S+)")


def _tree_lines():
    """The fenced block of §4, from its ``FAR23LOADS/`` root to the fence."""
    with open(_GUIDE, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "FAR23LOADS/")
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("```"))
    return lines[start + 1:end]


def _documented_paths():
    """Every path the tree names, rebuilt from its indentation.

    Returns ``(paths, directories)`` — files as ``sloads/export/bands.py``, and
    the directory names that were open at each depth, so a mis-nested line
    produces a path that simply does not exist on disk.
    """
    stack: list = []
    paths: set = set()
    dirs: set = set()
    for line in _tree_lines():
        match = _CONNECTOR.match(line)
        if not match:
            continue
        depth = len(match.group(1)) // 4
        name = match.group(2)
        del stack[depth:]
        if name.endswith("/"):
            stack.append(name.rstrip("/"))
            dirs.add("/".join(stack))
            continue
        if not name.endswith(".py"):
            continue
        # A file whose own token carries a directory (``export/mass_cards.py``
        # sitting under ``mass_distribution.py``) is exactly the mis-nesting
        # R6-D5 found, and it would otherwise rebuild to a real path and pass.
        assert "/" not in name, f"mis-nested line: {line.strip()}"
        paths.add("/".join(stack + [name]))
    return paths, dirs


def _package_files():
    """Every module actually in `sloads/`, as repo-relative paths."""
    out = set()
    for root, _, files in os.walk(os.path.join(_ROOT, "sloads")):
        if "__pycache__" in root:
            continue
        for name in files:
            if name.endswith(".py") and name not in _IGNORED:
                rel = os.path.relpath(os.path.join(root, name), _ROOT)
                out.add(rel.replace(os.sep, "/"))
    return out


def _documented_package_files():
    paths, _ = _documented_paths()
    return {p for p in paths
            if p.startswith("sloads/") and os.path.basename(p) not in _IGNORED}


def test_the_tree_parses_at_all():
    """The parse itself is load-bearing: an empty read would pass everything."""
    paths, dirs = _documented_paths()
    assert len(paths) > 50, len(paths)
    assert {"sloads", "sloads/models", "sloads/modules", "sloads/report",
            "sloads/export"} <= dirs, sorted(dirs)


def test_every_module_in_the_package_is_in_the_tree():
    """The finding: an SSOT owner that ships without reaching the layout doc."""
    missing = sorted(_package_files() - _documented_package_files())
    assert not missing, (
        "PROJECT_GUIDE.md §4 does not list: " + ", ".join(missing))


def test_every_sloads_line_in_the_tree_is_a_real_file():
    """The other direction — a renamed or deleted module, or a mis-nested line.

    A line under the wrong parent rebuilds to a path that does not exist, which
    is how the mis-nesting R6-D5 found would have been caught.
    """
    stale = sorted(_documented_package_files() - _package_files())
    assert not stale, (
        "PROJECT_GUIDE.md §4 lists files that do not exist: " + ", ".join(stale))


def test_the_overview_does_not_carry_a_second_tree():
    """One owner (user decision, 2026-08-15).

    `00_program_overview.md` used to carry its own, staler copy — `report.py`
    before the `report/` package, no `models/` split, half the modules — and two
    trees is one more than can be kept true.
    """
    path = os.path.join(_ROOT, "docs", "10_standard", "00_program_overview.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert "PROJECT_GUIDE.md §4" in text or "PROJECT_GUIDE.md`](PROJECT_GUIDE.md) §4" in text
    assert "└── modules/" not in text, "second package tree is back"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
