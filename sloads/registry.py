"""Module registry: map a module name to its ``run(project)`` function.

Each suite module calls :func:`register` at import time, so importing
``sloads.modules`` populates the registry. The CLI, GUI "run all" and tests
look modules up here by name instead of importing each one directly -- adding
program #2..#22 is then just a new module file that registers itself.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .models import MissingInputError, ModuleResult, Project

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

    A module raises :class:`~sloads.models.MissingInputError` when a required
    project slice is absent; those are skipped here so "run all" works on a
    partially-filled project. A plain :class:`ValueError` (an invalid domain input
    or a genuine calc defect) is **not** caught -- it propagates so the failure is
    visible in run-all/export rather than silently vanishing (M2R-8).
    """
    from .safety_factors import stamp

    results: List[ModuleResult] = []
    for name in available():
        try:
            results.append(_REGISTRY[name](project))
        except MissingInputError:
            continue
    # Every module's conditions take their factor from the project's governing
    # safety-factor table (M4-8 / decision G-11) -- one site, so a producer can
    # never disagree with the deliverable about a case's SF. A no-op unless the
    # project carries an override.
    stamp(project, *[r.conditions for r in results])
    return results


def run_all_modules_reporting(project: Project) -> Tuple[List[ModuleResult],
                                                         List[Tuple[str, Exception]]]:
    """:func:`run_all_modules`, with the invalid-input failures handed back.

    ``run_all_modules`` lets a plain :class:`ValueError` propagate on purpose
    (M2R-8): an invalid domain input and an absent one are different answers, and
    the invalid one must not vanish. That is right for the CLI and the export,
    which should fail the run — but a *page* that renders every module's results
    then dies whole on one bad slice, showing a traceback instead of the twenty
    modules that are fine. Three of the seven bundled examples carry an aileron
    or flap slice with no area, and both the Results Review and Export pages were
    dead on all three (#145).

    So the failure is neither swallowed nor fatal here: each module that raises is
    returned with its exception, for the caller to show by name beside the results
    that did compute. ``MissingInputError`` is still simply skipped — that is
    "not my turn", not a failure.
    """
    from .safety_factors import stamp

    results: List[ModuleResult] = []
    failures: List[Tuple[str, Exception]] = []
    for name in available():
        try:
            results.append(_REGISTRY[name](project))
        except MissingInputError:
            continue
        except Exception as exc:  # reported, by name, to the caller
            failures.append((name, exc))
    stamp(project, *[r.conditions for r in results])
    return results, failures
