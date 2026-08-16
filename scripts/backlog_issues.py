#!/usr/bin/env python
"""The backlog ↔ GitHub Issues bridge (design note 28 MD-5).

Issues are the system of record for open work; ``docs/30_future/00_backlog.md``
keeps the plan (mission, definition of done, the priority table with bands).
This script does the one-off migration and the standing both-ways check:

    plan     parse the backlog into the issue set and print it (no gh, no writes)
    create   open the issues with ``gh`` (labels created idempotently), record
             ``title -> #N`` in .github/backlog_issue_map.json
    rewrite  add ``(#N)`` to every priority-table row and replace each detail
             section / defect bullet with a one-line pointer to its issue
    check    every priority-table row names an open issue, and every open issue
             labelled ``band:*`` appears in the table (needs gh; exit 1 on drift)

Pure functions (``parse_backlog``, ``issue_set``, ``rewrite_backlog``) work on
strings so ``tests/test_backlog_issues.py`` runs them on the live file without
``gh``; only ``create`` and ``check`` shell out. Owner-run; never from CI.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "docs", "30_future", "00_backlog.md")
MAP = os.path.join(ROOT, ".github", "backlog_issue_map.json")

BAND_ROW = re.compile(r"^\|\s*\*\*([A-Z])\s+[—-]\s*(.*?)\*\*\s*\|")
ITEM_ROW = re.compile(r"^\|\s*(\d+)\s*\|")
DETAIL_HEADING = re.compile(r"^### \[([EVM])\]\s+(.*)$")
DEFECT_BULLET = re.compile(r"^- \*\*(.+?)\*\*")
ISSUE_REF = re.compile(r"\(#(\d+)\)")
_WORD = re.compile(r"[a-z0-9]{4,}")


@dataclass
class Item:
    kind: str                       # "row" | "detail" | "defect" | "decision"
    title: str
    body: str
    labels: List[str] = field(default_factory=list)
    band: str = ""
    pri: Optional[int] = None
    number: Optional[int] = None    # issue number once created
    line: int = 0                   # 1-based line in the backlog
    merged: List[str] = field(default_factory=list)  # titles folded into this issue


def _plain(md: str) -> str:
    """A GitHub issue title: markdown stripped, one line, <= 120 chars."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    t = re.sub(r"[`*]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:117] + "…" if len(t) > 120 else t


def _words(s: str) -> set:
    return set(_WORD.findall(_plain(s).lower()))


def parse_backlog(text: str) -> List[Item]:
    """Priority-table rows, detail sections, open defects, open decisions."""
    lines = text.splitlines()
    items: List[Item] = []
    band = ""
    section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            section = line[3:].strip()
        m = BAND_ROW.match(line)
        if m:
            band = m.group(1)
            i += 1
            continue
        m = ITEM_ROW.match(line)
        if m and band:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # | Pri | Item | What ships | Tag | Tier / effort | Depends on |
            if len(cells) >= 6:
                pri, title, ships, tag, tier, depends = int(cells[0]), cells[1], cells[2], cells[3], cells[4], cells[5]
                tier_letter = tier.strip().split("/")[0].strip()[:1].upper() or "M"
                labels = [f"band:{band}", f"tier:{tier_letter}", f"tag:{tag.strip()[:1].upper()}"]
                labels.append("kind:defect" if "defect" in title.lower() else "kind:step")
                if "hygiene" in title.lower() or "CH-" in title:
                    labels[-1] = "kind:hygiene"
                body = (f"**Priority table row {pri}, band {band}** (`docs/30_future/00_backlog.md`).\n\n"
                        f"**Item.** {title}\n\n**What ships.** {ships}\n\n**Tag.** {tag}  "
                        f"**Tier / effort.** {tier}  **Depends on.** {depends}\n")
                items.append(Item("row", _plain(title), body, labels, band, pri, line=i + 1))
            i += 1
            continue
        m = DETAIL_HEADING.match(line)
        if m:
            tag, heading = m.group(1), m.group(2)
            j = i + 1
            buf: List[str] = []
            while j < len(lines) and not lines[j].startswith("### ") and not lines[j].startswith("## "):
                buf.append(lines[j])
                j += 1
            body = "\n".join(buf).strip("\n")
            labels = [f"tag:{tag}" if tag in "EV" else "tier:M", "kind:step"]
            items.append(Item("detail", _plain(heading), body, labels, line=i + 1))
            i = j
            continue
        if section.startswith("Open defects") and DEFECT_BULLET.match(line):
            j = i + 1
            buf = [line]
            while j < len(lines) and lines[j].startswith("  "):
                buf.append(lines[j])
                j += 1
            head = DEFECT_BULLET.match(line).group(1)
            items.append(Item("defect", _plain(head), "\n".join(buf), ["kind:defect", "tag:V"], line=i + 1))
            i = j
            continue
        if section.startswith("Open design decisions") and line.startswith("- [ ] **"):
            j = i + 1
            buf = [line]
            while j < len(lines) and lines[j].startswith("  "):
                buf.append(lines[j])
                j += 1
            head = re.match(r"^- \[ \] \*\*(.+?)\*\*", line).group(1)
            items.append(Item("decision", _plain(head), "\n".join(buf), ["kind:decision"], line=i + 1))
            i = j
            continue
        i += 1
    return items


#: Explicit row ↔ detail/defect pairs the word-overlap matcher does not reach
#: (checked before the score; keys/values are substrings of the plain titles).
PINNED_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("Lateral body aero", "No lateral aerodynamic load exists but the fin"),
    ("Decisions, not effort", "The five non-oracle fixtures do not close as tightly as ga6"),
    ("Hygiene batch", "M4-23 — flight_envelope.density_ratio duplicates"),
    ("Hygiene batch", "Conventions-extraction findings"),
)


def _pinned(row_title: str, other_title: str) -> bool:
    return any(a in row_title and b in other_title for a, b in PINNED_PAIRS)


def _containment(a: str, b: str) -> float:
    """Shared significant words over the smaller title -- a detail heading is
    usually a longer restatement of its table row, so Jaccard under-scores it."""
    aw, bw = _words(a), _words(b)
    return len(aw & bw) / float(min(len(aw), len(bw)) or 1)


def issue_set(items: Sequence[Item], threshold: float = 0.5) -> List[Item]:
    """One issue per table row (its matching detail section / defect bullet
    folded into the body), plus every detail section / defect / decision that
    matched no row."""
    rows = [it for it in items if it.kind == "row"]
    others = [it for it in items if it.kind in ("detail", "defect")]
    used = set()
    out: List[Item] = []
    for row in rows:
        picks = [k for k, d in enumerate(others) if k not in used and _pinned(row.title, d.title)]
        if not picks:
            best, score = None, 0.0
            for k, d in enumerate(others):
                if k in used:
                    continue
                sc = _containment(row.title, d.title)
                if sc > score:
                    best, score = k, sc
            if best is not None and score >= threshold:
                picks = [best]
        for k in picks:
            used.add(k)
            d = others[k]
            row.body += f"\n---\n\n**Detail (from `{d.title}`)**\n\n{d.body}\n"
            row.merged.append(d.title)
            # A folded defect makes a *step* row a defect; a hygiene batch stays hygiene.
            if "kind:defect" in d.labels and "kind:step" in row.labels:
                row.labels = [lb for lb in row.labels if not lb.startswith("kind:")] + ["kind:defect"]
        out.append(row)
    out += [d for k, d in enumerate(others) if k not in used]
    out += [it for it in items if it.kind == "decision"]
    return out


def rewrite_backlog(text: str, numbers: Dict[str, int]) -> str:
    """``(#N)`` after each table row's title; detail sections and defect
    bullets replaced by one-line pointers. Rows already carrying ``(#N)`` are left."""
    lines = text.splitlines()
    out: List[str] = []
    i = 0
    band = ""
    while i < len(lines):
        line = lines[i]
        if BAND_ROW.match(line):
            band = "x"
        m = ITEM_ROW.match(line)
        if m and band and not ISSUE_REF.search(line):
            cells = line.strip().strip("|").split("|")
            title = cells[1].strip()
            n = numbers.get(_plain(title))
            if n is not None:
                cells[1] = f" {title} (#{n}) "
                line = "|" + "|".join(cells) + "|"
            out.append(line)
            i += 1
            continue
        m = DETAIL_HEADING.match(line)
        if m:
            n = numbers.get(_plain(m.group(2)))
            j = i + 1
            while j < len(lines) and not lines[j].startswith("### ") and not lines[j].startswith("## ") \
                    and lines[j].strip() != "---":
                j += 1
            if n is not None:
                out.append(f"### [{m.group(1)}] {m.group(2)} → #{n}")
                out.append("")
                out.append(f"Body moved to issue #{n} (design note 28 MD-5).")
                out.append("")
                i = j
                continue
        m = DEFECT_BULLET.match(line)
        if m and numbers.get(_plain(m.group(1))) is not None:
            n = numbers[_plain(m.group(1))]
            out.append(f"- #{n} — {m.group(1)}")
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out) + "\n"


def table_refs(text: str) -> List[int]:
    return [int(n) for line in text.splitlines() if ITEM_ROW.match(line) for n in ISSUE_REF.findall(line)]


# --- gh ----------------------------------------------------------------------

LABEL_COLOURS = {"band": "1d76db", "tier": "5319e7", "tag": "0e8a16", "kind": "d93f0b"}


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def ensure_labels(labels: Sequence[str]) -> None:
    existing = {ln.split("\t")[0] for ln in _gh("label", "list", "--limit", "200").splitlines()}
    for lab in sorted(set(labels)):
        if lab in existing:
            continue
        colour = LABEL_COLOURS.get(lab.split(":")[0], "ededed")
        subprocess.run(["gh", "label", "create", lab, "--color", colour, "--force"], check=True)


def create(items: Sequence[Item], milestone: Optional[str]) -> Dict[str, int]:
    ensure_labels([lab for it in items for lab in it.labels] + ["parked", "physics", "needs-design-note",
                                                                "self-merge-ok"])
    numbers: Dict[str, int] = {}
    if os.path.exists(MAP):
        with open(MAP, encoding="utf-8") as fh:
            numbers = json.load(fh)
    for it in items:
        if it.title in numbers:
            continue
        cmd = ["issue", "create", "--title", it.title, "--body", it.body, "--label", ",".join(it.labels)]
        if milestone and it.band == "A":
            cmd += ["--milestone", milestone]
        url = _gh(*cmd).strip()
        it.number = int(url.rstrip("/").rsplit("/", 1)[-1])
        numbers[it.title] = it.number
        with open(MAP, "w", encoding="utf-8") as fh:
            json.dump(numbers, fh, indent=2, ensure_ascii=False)
        print(f"#{it.number}  {it.title}")
    return numbers


def check(text: str) -> Tuple[List[int], List[Tuple[int, str]]]:
    """(table refs with no open issue, open band:* issues not in the table)."""
    refs = set(table_refs(text))
    raw = _gh("issue", "list", "--state", "open", "--limit", "500", "--json", "number,title,labels")
    open_issues = json.loads(raw)
    open_nums = {it["number"] for it in open_issues}
    banded = [(it["number"], it["title"]) for it in open_issues
              if any(lb["name"].startswith("band:") for lb in it["labels"])]
    return sorted(refs - open_nums), [(n, t) for n, t in banded if n not in refs]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["plan", "create", "rewrite", "check"])
    ap.add_argument("--milestone", help="milestone for band-A issues on create (e.g. 0.6.0)")
    args = ap.parse_args(argv)
    with open(BACKLOG, encoding="utf-8") as fh:
        text = fh.read()
    items = issue_set(parse_backlog(text))

    if args.command == "plan":
        for it in items:
            print(f"[{it.kind:8}] {' '.join(it.labels):32} {it.title}")
        print(f"\n{len(items)} issue(s) — {sum(it.kind == 'row' for it in items)} table rows, "
              f"{sum(it.kind == 'detail' for it in items)} unmatched detail sections, "
              f"{sum(it.kind == 'defect' for it in items)} defects, "
              f"{sum(it.kind == 'decision' for it in items)} decisions")
        return 0
    if args.command == "create":
        create(items, args.milestone)
        print(f"map: {os.path.relpath(MAP, ROOT)}")
        return 0
    if args.command == "rewrite":
        with open(MAP, encoding="utf-8") as fh:
            numbers = json.load(fh)
        for it in items:  # a folded detail section / defect bullet points at its row's issue
            if it.title in numbers:
                for t in it.merged:
                    numbers.setdefault(t, numbers[it.title])
        with open(BACKLOG, "w", encoding="utf-8") as fh:
            fh.write(rewrite_backlog(text, numbers))
        print(f"rewrote {os.path.relpath(BACKLOG, ROOT)} with {len(numbers)} issue references")
        return 0
    dangling, missing = check(text)
    for n in dangling:
        print(f"table row references #{n} but no such open issue")
    for n, t in missing:
        print(f"open band:* issue #{n} is not in the priority table: {t}")
    return 1 if (dangling or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
