"""Pytest setup: make the repo root importable so ``import farloads`` works and
the test modules can import each other (``from test_engine import io520bb``).
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (_ROOT, os.path.dirname(os.path.abspath(__file__))):
    if path not in sys.path:
        sys.path.insert(0, path)
