#!/usr/bin/env python
"""Assemble ``changes/*.md`` fragments into a ``CHANGELOG.md`` release section.

Design note ``docs/30_future/26_doc_volume_reduction_note.md`` (2026-08-16).
Fragment contract: ``changes/README.md``. Run at release cut only
(``RELEASE_PROCESS.md`` §4); ``--dry-run`` previews without writing.

Pure functions (``parse_fragments``, ``merge_section``, ``cut_release``) do all
the work on strings so ``tests/test_changelog_fragments.py`` can exercise them
without touching the repo files; ``main`` is the only I/O.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGES_DIR = os.path.join(ROOT, "changes")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

#: Subsection order in a release block. ``type`` in the fragment name maps to
#: the heading; anything else is a naming error, not a new subsection.
TYPES: Tuple[Tuple[str, str], ...] = (
    ("breaking", "Breaking"),
    ("added", "Added"),
    ("changed", "Changed"),
    ("fixed", "Fixed"),
    ("removed", "Removed"),
)
TYPE_TO_HEADING = dict(TYPES)
FRAGMENT_NAME = re.compile(r"^(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.(?P<type>[a-z]+)\.md$")
UNRELEASED = re.compile(r"^## \[Unreleased\]\s*$", re.M)
RELEASE_HEADING = re.compile(r"^## \[", re.M)
SUBSECTION = re.compile(r"^### (\w+)\s*$", re.M)


class FragmentError(ValueError):
    """A fragment that violates ``changes/README.md``; the file name is in the message."""


def validate_fragment(name: str, body: str) -> str:
    """Return the fragment's type, or raise :class:`FragmentError` naming the fault."""
    m = FRAGMENT_NAME.match(name)
    if not m:
        raise FragmentError(f"{name}: not '<slug>.<type>.md' (kebab-case slug, lower-case type)")
    kind = m.group("type")
    if kind not in TYPE_TO_HEADING:
        raise FragmentError(f"{name}: type '{kind}' not in {sorted(TYPE_TO_HEADING)}")
    if not body.lstrip().startswith("- "):
        raise FragmentError(f"{name}: body must be Markdown bullet(s) starting with '- '")
    return kind


def parse_fragments(files: Dict[str, str]) -> Dict[str, List[str]]:
    """``{filename: body}`` → ``{type: [bullet blocks…]}`` in filename order."""
    out: Dict[str, List[str]] = {}
    for name in sorted(files):
        kind = validate_fragment(name, files[name])
        out.setdefault(kind, []).append(files[name].strip("\n") + "\n")
    return out


def _split_subsections(body: str) -> Tuple[str, Dict[str, str]]:
    """Split an ``[Unreleased]`` body into (preamble, {heading: text})."""
    parts = SUBSECTION.split(body)
    preamble = parts[0]
    sections: Dict[str, str] = {}
    for i in range(1, len(parts), 2):
        sections[parts[i]] = parts[i + 1]
    return preamble, sections


def merge_section(unreleased_body: str, fragments: Dict[str, List[str]]) -> str:
    """Merge fragment bullets into an ``[Unreleased]`` body, subsection by subsection.

    Fragments lead each subsection, legacy hand-written text follows; empty
    subsections are dropped; subsection order is :data:`TYPES`, then any
    unknown legacy headings in their original order.
    """
    preamble, legacy = _split_subsections(unreleased_body)
    known = [h for _, h in TYPES]
    order = known + [h for h in legacy if h not in known]
    out = [preamble.rstrip("\n") + "\n" if preamble.strip() else ""]
    for heading in order:
        kind = next((k for k, h in TYPES if h == heading), None)
        new = "\n".join(fragments.get(kind, [])) if kind else ""
        old = legacy.get(heading, "").strip("\n")
        if not new.strip() and not old.strip():
            continue
        block = f"### {heading}\n\n"
        if new.strip():
            block += new.rstrip("\n") + "\n\n"
        if old.strip():
            block += old + "\n\n"
        out.append(block)
    return "".join(out).rstrip("\n") + "\n"


def cut_release(changelog: str, fragments: Dict[str, List[str]], version: str, date: str) -> str:
    """Return the new ``CHANGELOG.md`` text with ``[Unreleased]`` cut as ``version``.

    Only the ``[Unreleased]`` block changes; every released section below it
    is byte-identical.
    """
    m = UNRELEASED.search(changelog)
    if not m:
        raise ValueError("CHANGELOG.md has no '## [Unreleased]' heading")
    start = m.end()
    nxt = RELEASE_HEADING.search(changelog, start)
    end = nxt.start() if nxt else len(changelog)
    body = merge_section(changelog[start:end], fragments)
    new_block = f"## [Unreleased]\n\n## [{version}] — {date}\n\n{body}\n"
    return changelog[: m.start()] + new_block + changelog[end:]


def preview(changelog: str, fragments: Dict[str, List[str]]) -> str:
    """The merged ``[Unreleased]`` body as it would be cut — for ``--dry-run``."""
    m = UNRELEASED.search(changelog)
    if not m:
        raise ValueError("CHANGELOG.md has no '## [Unreleased]' heading")
    nxt = RELEASE_HEADING.search(changelog, m.end())
    end = nxt.start() if nxt else len(changelog)
    return merge_section(changelog[m.end() : end], fragments)


def load_fragments(changes_dir: str = CHANGES_DIR) -> Dict[str, str]:
    files: Dict[str, str] = {}
    for name in os.listdir(changes_dir):
        if name == "README.md" or name.startswith("."):
            continue
        with open(os.path.join(changes_dir, name), encoding="utf-8") as fh:
            files[name] = fh.read()
    return files


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version", nargs="?", help="X.Y.Z (required unless --dry-run)")
    ap.add_argument("--date", help="YYYY-MM-DD release date (required unless --dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="print the merged section; write nothing")
    args = ap.parse_args(argv)

    files = load_fragments()
    fragments = parse_fragments(files)
    with open(CHANGELOG, encoding="utf-8") as fh:
        changelog = fh.read()

    if args.dry_run:
        sys.stdout.write(preview(changelog, fragments))
        sys.stdout.write(f"\n[{len(files)} fragment(s), nothing written]\n")
        return 0
    if not args.version or not args.date:
        ap.error("version and --date are required unless --dry-run")
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        ap.error("version must be X.Y.Z")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        ap.error("--date must be YYYY-MM-DD")

    with open(CHANGELOG, "w", encoding="utf-8") as fh:
        fh.write(cut_release(changelog, fragments, args.version, args.date))
    for name in files:
        os.remove(os.path.join(CHANGES_DIR, name))
    print(f"CHANGELOG.md: cut [{args.version}] — {args.date}; {len(files)} fragment(s) consumed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
