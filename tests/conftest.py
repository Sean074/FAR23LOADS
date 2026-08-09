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

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP = os.path.join(_ROOT, "app")
for path in (_ROOT, os.path.dirname(os.path.abspath(__file__)), _APP):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture
def sbeam():
    """The solver, or a skip -- unless the environment says it must be there.

    The sbeam round-trip gate (``docs/30_future/10_sbeam_roundtrip_ci_harness_plan.md``,
    decision S-7) is the one test family in the suite that needs another
    repository installed. Local development without it stays frictionless: those
    tests skip. But a bare ``importorskip`` would let a **broken CI install**
    report green, which is the exact failure mode the gate exists to end -- so
    the round-trip CI job sets ``SLOADS_REQUIRE_SBEAM=1`` and the skip becomes a
    failure there.

    Lives in ``conftest.py`` so it is one implementation shared by every test
    module that needs it (M4-12a: a test module never imports another).
    """
    try:
        import sbeam as _sbeam  # noqa: F401
    except ImportError:
        if os.environ.get("SLOADS_REQUIRE_SBEAM") == "1":
            pytest.fail(
                "sbeam is required in this environment (SLOADS_REQUIRE_SBEAM=1) "
                "but is not installed -- the round-trip gate would have been "
                "silently skipped")
        pytest.skip("sbeam not installed -- `pip install -e '.[solver]'` to run "
                    "the round-trip gate")
    return _sbeam
