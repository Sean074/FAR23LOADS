"""Pytest setup: make the repo root importable so ``import sloads`` works and
the test modules can import each other (``from test_engine import io520bb``).

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
