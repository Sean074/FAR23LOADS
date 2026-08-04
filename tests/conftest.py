"""Pytest setup: make the repo root importable so ``import sloads`` works and
``tests/`` importable so the test modules can reach the shared
:mod:`helpers` / :mod:`fixtures` support modules.

**A test module never imports another test module** (M4-12a). Shared lookup
helpers live in ``tests/helpers.py`` and shared input builders in
``tests/fixtures.py``; neither collects as a test.

``app/`` is also added so the view smoke test (which runs each ``app/views/*.py``
as its own entrypoint) can resolve shared app modules like ``components`` -- at
real runtime Streamlit puts ``app/`` on the path via the ``app/Home.py``
entrypoint, but ``AppTest.from_file`` on a view file does not.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP = os.path.join(_ROOT, "app")
for path in (_ROOT, os.path.dirname(os.path.abspath(__file__)), _APP):
    if path not in sys.path:
        sys.path.insert(0, path)
