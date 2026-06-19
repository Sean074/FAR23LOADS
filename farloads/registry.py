"""Module registry: map a module name to its ``run(project)`` function.

Each suite module calls :func:`register` at import time, so importing
``farloads.modules`` populates the registry. The CLI, GUI "run all" and tests
look modules up here by name instead of importing each one directly -- adding
program #2..#22 is then just a new module file that registers itself.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from .models import ModuleResult, Project

RunFn = Callable[[Project], ModuleResult]

_REGISTRY: Dict[str, RunFn] = {}


def register(name: str, fn: RunFn) -> None:
    """Register ``fn`` as the runner for module ``name`` (last registration wins)."""
    _REGISTRY[name] = fn


def get(name: str) -> RunFn:
    """Return the runner for ``name`` or raise ``KeyError`` listing what's available."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown module {name!r}; registered: {', '.join(available()) or '(none)'}"
        ) from None


def available() -> List[str]:
    """Names of all registered modules, in registration order."""
    return list(_REGISTRY)


def run_all_modules(project: Project) -> List[ModuleResult]:
    """Run every registered module that has the input slice it needs.

    A module raises ``ValueError`` when its project slice is absent; those are
    skipped here so "run all" works on a partially-filled project (Phase 0: only
    the engine slice is ever present).
    """
    results: List[ModuleResult] = []
    for name in available():
        try:
            results.append(_REGISTRY[name](project))
        except ValueError:
            continue
    return results
