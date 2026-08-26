#!/usr/bin/env python3
"""Keep `.github/branch-protection.json` in step with the live protection on `main`.

**Why this exists.** A documented git/CI setting and the live one drifted apart
twice on 2026-08-25 and nothing compared them: `RELEASE_PROCESS.md` §4,
`DEVELOPMENT_PROCESS.md` §0/§2 and `WORKFLOW_COMMANDS.txt` all asserted "linear
history off, merge commits allowed" while `main` enforces linear history and
refused the 0.7.2 milestone PR ("This branch must not contain merge commits");
separately, §2 listed six required checks, three of which `ci.yml` never
produces on a pull request. Backlog row 6 / issue #46, review finding CR-D-4.

**The two hops.** CI cannot read GitHub — the test job has no `gh` auth — so the
comparison is split:

1. **snapshot -> docs**, on every test run, no network:
   `tests/test_ci_conformance.py` asserts the prose in the process docs against
   this file, and asserts every required check in it is one `ci.yml` actually
   reports on a pull request.
2. **live -> snapshot**, on demand, needs `gh`: this script. Run
   ``--check`` (it exits 1 on any difference) or ``--write`` to refresh.

Run ``--check`` when you change a protection setting, and at the release cut
(`RELEASE_PROCESS.md` §4). It is deliberately *not* wired into CI: a gate that
needs a credential CI does not have is a gate that silently skips, which is the
defect class this whole row is about.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(_ROOT, ".github", "branch-protection.json")

#: Keys this script owns. Anything else in the file (the ``_``-prefixed prose,
#: ``captured``) is preserved on a write: the snapshot is documentation as well
#: as data, and a refresh must not silently drop the explanation of itself.
LIVE_KEYS = (
    "required_status_checks",
    "required_linear_history",
    "required_pull_request",
)


def load() -> dict:
    with open(SNAPSHOT, encoding="utf-8") as fh:
        return json.load(fh)


def _gh_json(*args: str) -> dict:
    out = subprocess.run(
        ["gh", "api", *args], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        sys.exit(
            f"gh api {' '.join(args)} failed (exit {out.returncode}):\n{out.stderr.strip()}\n"
            "Authenticate with `gh auth login`, or run without --check/--write."
        )
    return json.loads(out.stdout)


def live(branch: str) -> dict:
    """The live settings, reduced to the keys this snapshot tracks."""
    prot = _gh_json(f"repos/:owner/:repo/branches/{branch}/protection")
    checks = prot.get("required_status_checks", {}) or {}
    contexts = checks.get("contexts")
    if contexts is None:  # newer API shape
        contexts = [c.get("context", "") for c in checks.get("checks", [])]
    return {
        "required_status_checks": sorted(contexts),
        "required_linear_history": bool(
            (prot.get("required_linear_history") or {}).get("enabled", False)
        ),
        "required_pull_request": prot.get("required_pull_request_reviews") is not None,
    }


def diff(snap: dict, now: dict) -> list:
    return [
        f"{k}: snapshot {snap.get(k)!r} != live {now[k]!r}"
        for k in LIVE_KEYS
        if snap.get(k) != now[k]
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="exit 1 if the snapshot has drifted from live")
    g.add_argument("--write", action="store_true", help="refresh the snapshot from live")
    ap.add_argument("--date", help="value for `captured` on --write (default: today)")
    args = ap.parse_args(argv)

    snap = load()
    now = live(snap["branch"])
    drift = diff(snap, now)

    if args.check:
        if drift:
            print("branch-protection snapshot has DRIFTED from the live setting:")
            for d in drift:
                print(f"  - {d}")
            print(
                "\nDecide which is right, then either change the setting on GitHub or run\n"
                "  python scripts/branch_protection_snapshot.py --write\n"
                "and correct the process docs the snapshot is asserted against\n"
                "(tests/test_ci_conformance.py names them)."
            )
            return 1
        print(f"branch-protection snapshot matches live `{snap['branch']}` on {len(LIVE_KEYS)} tracked keys.")
        return 0

    if not drift:
        print("no change — snapshot already matches live.")
        return 0
    snap.update(now)
    if args.date:
        snap["captured"] = args.date
    else:
        from datetime import date

        snap["captured"] = date.today().isoformat()
    snap["captured_by"] = "scripts/branch_protection_snapshot.py"
    with open(SNAPSHOT, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=2)
        fh.write("\n")
    print("snapshot refreshed:")
    for d in drift:
        print(f"  - {d}")
    print("\nNow re-run the suite: the process docs are asserted against this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
