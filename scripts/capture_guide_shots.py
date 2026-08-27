#!/usr/bin/env python3
"""Capture the oracle GUI user-guide screenshots (design note 34, UG-4).

Launches the oracle GUI (``oracle_app/Oracle.py``) headless, loads a named
example through the sidebar exactly as a reader would, walks the derived page
set (``sloads.workflow.oracle_steps()``) and writes deterministic full-page
PNGs to ``docs/60_guide/img/`` — light theme, fixed 1440x900 viewport, no
browser chrome, named ``<NN>_<step_key>__<slug>.png`` (guide style rules).

Manual captures drift silently; this script makes "the GUI changed" a
one-command refresh::

    .venv/bin/python scripts/capture_guide_shots.py                 # walk all
    .venv/bin/python scripts/capture_guide_shots.py --example ga6_normal \
        --step wing_loads                                           # one shot

Needs the ``dev`` extra (Playwright) plus its browser once:
``.venv/bin/playwright install chromium``. Dev-only tooling — nothing at
runtime imports this; the guide gates (``tests/test_guide.py``) import only
:data:`GUIDE_EXAMPLES` and never launch a browser.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import socket
import subprocess
import sys
import time
from typing import Dict, Iterator, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

DEFAULT_OUT = os.path.join(REPO_ROOT, "docs", "60_guide", "img")
VIEWPORT = {"width": 1440, "height": 900}

#: The guide's worked examples — the single source the capture walk and gate
#: G-UG-4 (``tests/test_guide.py``) both read. ``channel`` is the unit system
#: the example's shots are taken in (UG-12: the single Imperial, the twin SI);
#: ``not_reached`` lists oracle pages the example legitimately cannot run
#: (the module refuses with ``MissingInputError``), so the walk skips their
#: shots and the gate asserts the refusal instead of a pass.
GUIDE_EXAMPLES: Dict[str, Dict[str, object]] = {
    "ga6_normal": {"channel": "Imperial", "not_reached": ("one_engine_out",)},
}


def _free_port() -> int:
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with contextlib.closing(socket.socket()) as s:
            s.settimeout(1.0)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise RuntimeError(f"oracle GUI did not open port {port} within {timeout_s}s")


@contextlib.contextmanager
def _streamlit_server(port: int) -> Iterator[str]:
    """The oracle GUI on ``port``, torn down on exit."""
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        os.path.join(REPO_ROOT, "oracle_app", "Oracle.py"),
        "--server.headless=true",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        "--client.toolbarMode=viewer",
        "--theme.base=light",
    ]
    proc = subprocess.Popen(
        cmd, cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port)
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def _wait_idle(page) -> None:
    """Wait until Streamlit finishes the current rerun."""
    # The status widget appears while a script run is in flight and detaches
    # when it settles; a page that never showed one is already idle.
    with contextlib.suppress(Exception):
        page.wait_for_selector(
            '[data-testid="stStatusWidget"]', state="attached", timeout=2_000
        )
    page.wait_for_selector(
        '[data-testid="stStatusWidget"]', state="detached", timeout=60_000
    )
    page.wait_for_timeout(400)  # let the last frame paint


def _load_example(page, example: str) -> None:
    """Drive the sidebar's New-from-example flow, as a reader would."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text("📂 Open", exact=False).first.click()
    _wait_idle(page)
    box = sidebar.locator(
        '[data-testid="stSelectbox"]', has_text="New from example"
    ).first
    box.click()
    page.get_by_role("option", name=f"{example}.project.json").click()
    _wait_idle(page)
    sidebar.get_by_role("button", name="Load example").click()
    _wait_idle(page)


def _set_channel(page, channel: str) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text(channel, exact=True).first.click()
    _wait_idle(page)


def _goto_step(page, title: str) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_role("link", name=title, exact=True).click()
    _wait_idle(page)


def _chapters() -> List[Tuple[str, object]]:
    from sloads import workflow as w

    return [(f"{i:02d}", s) for i, s in enumerate(w.oracle_steps(), start=1)]


def capture(example: str, channel: str, steps: Optional[List[str]],
            out_dir: str) -> List[str]:
    """Capture ``example``'s page shots; returns the files written."""
    from playwright.sync_api import sync_playwright

    spec = GUIDE_EXAMPLES.get(example, {})
    skip = set(spec.get("not_reached", ()) if not steps else ())
    os.makedirs(out_dir, exist_ok=True)
    written: List[str] = []
    port = _free_port()
    with _streamlit_server(port) as url, sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(url)
        _wait_idle(page)
        _load_example(page, example)
        _set_channel(page, channel)
        for nn, step in _chapters():
            if steps is not None and step.key not in steps:
                continue
            if step.key in skip:
                print(f"skip {step.key}: {example} does not reach it")
                continue
            _goto_step(page, step.title)
            name = f"{nn}_{step.key}__page-{example.replace('_', '-')}.png"
            path = os.path.join(out_dir, name)
            page.screenshot(path=path, full_page=True)
            written.append(path)
            print(f"wrote {os.path.relpath(path, REPO_ROOT)}")
        browser.close()
    return written


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--example", choices=sorted(GUIDE_EXAMPLES),
                        help="one example (default: walk all guide examples)")
    parser.add_argument("--channel", choices=["Imperial", "SI"],
                        help="unit channel (default: the example's own)")
    parser.add_argument("--step", action="append", dest="steps",
                        help="step key to capture (repeatable; default: all)")
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="output directory (default: docs/60_guide/img)")
    args = parser.parse_args(argv)

    examples = [args.example] if args.example else sorted(GUIDE_EXAMPLES)
    for example in examples:
        channel = args.channel or str(GUIDE_EXAMPLES[example]["channel"])
        capture(example, channel, args.steps, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
