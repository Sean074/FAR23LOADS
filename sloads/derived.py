"""Project slices that are derived from the project's own inputs (#62, PB-1).

A *derived* slice is one the project could always rebuild from fields the user
entered: ``Project.mass`` is WTONECG over ``weight.items`` and nothing else.
Storing it is a convenience for readers (One Engine Out, Configuration's
tip-back CG, the CG-case waterline) and the ``workflow`` step's ✅ -- but a
stored copy of a derivation is a second source of the same fact, and the
oracle GUI showed what that costs: nothing in it wrote the slice, so a fresh
twin could never reach One Engine Out and Configuration fell back to a
25 %-MAC estimate (review 2026-08-22 PB-1).

This module is the table of those slices and the one call that keeps them
current. Every writer of the inputs a derived slice reads calls
:func:`refresh_derived` afterwards -- the ``app/`` Weight page on Apply, the
oracle form after every persist -- and gate G5's reduction calls it after
dropping the stored slices, so a project made by either front-end and a
project reduced to what the oracle GUI would have set carry the same
derivations by construction. Each refresher is idempotent by value (a render
pass may call it without dirtying the project) and returns whether it wrote.

Guarded in ``tests/test_derived.py``: every shipped example stores exactly the
slice it derives, and every name here is a result slice the field registry
already excludes from the input set.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from .models import Project
from .modules.weight_onecg import refresh_mass

#: ``Project`` attribute -> the refresher that rebuilds it from the inputs.
DERIVED_SLICES: Dict[str, Callable[[Project], bool]] = {
    "mass": refresh_mass,
}


def refresh_derived(project: Project) -> List[str]:
    """Bring every derived slice up to date; the names of those that changed."""
    return [name for name, refresh in DERIVED_SLICES.items() if refresh(project)]


__all__ = ["DERIVED_SLICES", "refresh_derived"]
