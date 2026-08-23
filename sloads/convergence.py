"""Iterative-solver outcomes: the one vocabulary for "did that loop converge?".

Several calc paths ported from the BASIC are fixed-point iterations with a bounded
trip count (``for _ in range(N)``). The BASIC's habit -- and this port's, until
#33 -- is to fall out of the loop on exhaustion and return the last iterate as if
it were the answer. That is the masked-defect shape: an exhausted solve and a
converged one are indistinguishable to every caller downstream, and in this suite
"downstream" means every V-n point, every SELECT pick and every balanced case.

Three outcomes, not two (decision 2026-08-22, #33):

``CONVERGED``
    The loop met its own acceptance band.

``CLAMPED``
    The iteration reached a **fixed point outside** its acceptance band -- it has
    no lever left, so a further trip would reproduce the same iterate exactly.
    This is not a solver failure: on the shipped ``atr42_100`` fixture it is the
    Mach-capped stall-limited corner that decision **D-30** ruled ordinary flight
    (FAR **23.333(b)** applies the manoeuvring envelope "except where limited by
    maximum (static) lift coefficients"). A clamped solve returns its iterate, and
    the state travels with the result so a consumer can mark the row (#32) instead
    of re-deriving the same predicate from the published numbers.

``FAILED``
    Trips exhausted with the iterate still moving: no fixed point, no answer.
    Never returned -- it is raised as :class:`SolverFailure`, a ``ValueError``
    per the error contract (`00_program_overview.md` -- a genuine calc defect must
    stay visible, and is deliberately *not* caught by ``run_all_modules``).

Owner of the vocabulary (`CONVENTIONS.md` §7); the drift guard that no bounded
solver loop in ``sloads/`` exhausts silently is ``tests/test_convergence.py``.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["SolveState", "SolverFailure", "solver_failure"]


class SolveState(str, Enum):
    """How an iterative solve ended. ``str`` mixin so it renders as its own name."""

    CONVERGED = "converged"
    CLAMPED = "clamped"
    FAILED = "failed"


class SolverFailure(ValueError):
    """A bounded iteration exhausted with its iterate still moving.

    A ``ValueError`` (not ``MissingInputError``): the inputs are present, the calc
    could not close on them. ``run_all_modules`` lets it through by design.
    """


def solver_failure(what: str, *, trips: int, detail: str) -> SolverFailure:
    """Build the refusal for an exhausted solve, in one wording.

    ``what`` names the iteration ("flight-envelope angle-of-attack iteration"),
    ``trips`` the bound it exhausted, ``detail`` the state that identifies the
    case -- enough for a user to find the condition without a debugger.
    """
    return SolverFailure(
        f"{what} did not converge in {trips} iterations and is still moving: "
        f"{detail}. No load is reported from an unconverged balance."
    )
