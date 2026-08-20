"""Launcher for the oracle GUI (design note 32, OG-11).

    sloads-oracle                    # the console script
    sloads-oracle -- --server.port 8600
    python oracle.py

Equivalent to ``streamlit run oracle_app/Oracle.py``; the console script exists
so the second front-end is launched on its own terms rather than as a flag on
the first (OG-11), and so a user who installed the package does not have to know
where the entry point lives. Arguments after the module name are passed straight
through to Streamlit.

This is a *launcher*, not a front-end: it holds no page, reads no project and
computes nothing. The GUI itself is ``oracle_app/``.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional

#: The Streamlit entry point this launcher runs, relative to the repo root.
ENTRY_POINT = os.path.join("oracle_app", "Oracle.py")


def entry_point_path() -> str:
    """Absolute path to ``oracle_app/Oracle.py``, beside this launcher."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ENTRY_POINT)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the oracle GUI under Streamlit. Returns a process exit code."""
    path = entry_point_path()
    if not os.path.isfile(path):
        print(f"oracle: {path} not found — run from a source checkout "
              "(the GUI is a script directory, not part of the wheel).",
              file=sys.stderr)
        return 2
    try:
        from streamlit.web import cli as stcli
    except ImportError:                                      # pragma: no cover
        print("oracle: streamlit is not installed — pip install -e '.[dev]'",
              file=sys.stderr)
        return 2

    sys.argv = ["streamlit", "run", path] + list(argv if argv is not None else sys.argv[1:])
    return int(stcli.main() or 0)


if __name__ == "__main__":                                   # pragma: no cover
    raise SystemExit(main())
