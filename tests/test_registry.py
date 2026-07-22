"""M2R-8: MissingInputError contract + the SELECT single-envelope-build.

``run_all_modules`` must skip a module that legitimately has no inputs
(``MissingInputError``) but let a genuine ``ValueError`` (an invalid domain input
or a calc defect) propagate, instead of swallowing every ``ValueError`` and hiding
real failures. And ``build_critical`` must build the V-n envelope only once per run
(threading it into the searches) rather than up to 7x.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from farloads import MissingInputError, io, registry  # noqa: E402
from farloads.models import ModuleResult  # noqa: E402

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
GA6 = os.path.join(EXAMPLES, "ga6_normal.project.json")


def test_missing_input_error_is_value_error():
    """It subclasses ValueError, so every existing ``except ValueError`` (GUI/CLI)
    still catches it -- only ``run_all_modules`` narrows to it."""
    assert issubclass(MissingInputError, ValueError)


def _register_temp(name, fn):
    """Register ``fn`` under ``name`` and restore the registry afterwards."""
    saved = dict(registry._REGISTRY)
    registry.register(name, fn)
    return saved


def test_run_all_skips_missing_input_but_propagates_value_error():
    project = io.load_project(GA6)

    def _missing(_p):
        raise MissingInputError("no slice here")

    def _defect(_p):
        raise ValueError("genuine calc defect")

    saved = _register_temp("zzz_missing", _missing)
    try:
        # A MissingInputError module is skipped: run-all still returns the real results.
        results = registry.run_all_modules(project)
        assert results and all(isinstance(r, ModuleResult) for r in results)
        assert "zzz_missing" not in {r.module for r in results}

        # A genuine ValueError now propagates instead of vanishing (the M2R-8 fix).
        registry.register("zzz_defect", _defect)
        with pytest.raises(ValueError, match="genuine calc defect"):
            registry.run_all_modules(project)
    finally:
        registry._REGISTRY.clear()
        registry._REGISTRY.update(saved)


def test_run_all_skips_all_modules_on_engine_only_project():
    """The ~21 entry guards are all MissingInputError: an engine-only project runs
    only the engine module (every other module skips cleanly)."""
    from test_engine import io520bb

    from farloads import EngineLayout, Project

    project = Project(name="engine only", engines=[io520bb()], engine_layout=EngineLayout.SINGLE_NOSE)
    results = registry.run_all_modules(project)
    assert [r.module for r in results] == ["engine"]


def test_build_critical_builds_envelope_once(monkeypatch):
    """M2R-8 threading: with no persisted envelope, ``build_critical`` calls
    ``build_envelope`` exactly once (was up to 7x)."""
    from farloads.modules import select

    project = io.load_project(GA6)
    project.envelope = None  # force the fallback build path

    calls = {"n": 0}
    real = select.build_envelope

    def _counting(p):
        calls["n"] += 1
        return real(p)

    monkeypatch.setattr(select, "build_envelope", _counting)
    cls = select.build_critical(project)
    assert cls.conditions, "expected some critical conditions"
    assert calls["n"] == 1, f"build_envelope called {calls['n']}x, expected 1"


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            # monkeypatch-based test can't run without pytest; skip it in the fallback.
            if "monkeypatch" in t.__code__.co_varnames:
                continue
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed - 1}/{len(tests) - 1} ran (1 needs pytest)")
    sys.exit(1 if failed else 0)
