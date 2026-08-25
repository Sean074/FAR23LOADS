"""Project slices that are derived from the project's own inputs (#62, PB-1).

A *derived* slice is one the project could always rebuild from fields the user
entered: ``Project.mass`` is WTONECG over ``weight.items`` and nothing else.
Storing it is a convenience for readers (One Engine Out, Configuration's
tip-back CG, the CG-case waterline) and the ``workflow`` step's ✅ -- but a
stored copy of a derivation is a second source of the same fact, and the
oracle GUI showed what that costs: nothing in it wrote the slice, so a fresh
twin could never reach One Engine Out and Configuration fell back to a
25 %-MAC estimate (review 2026-08-22 PB-1).

It also holds the sibling table for *normalized* slices -- authored input whose
fields fill each other in (the M1-1b stall CLs, #81) -- for the same reason: the
fill lived in ``__post_init__`` alone, so a GUI that assembles a slice field by
field never ran it, and the envelope divided by a stall CL of zero.

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

#: ``Project`` attribute -> the normalizer that makes an **input** slice
#: internally consistent. Distinct from :data:`DERIVED_SLICES` in what it owns:
#: a derived slice is a *result* the project could rebuild from scratch and which
#: the field registry excludes from the input set, while a normalized slice is
#: authored input whose fields fill each other in (fill-if-missing, never
#: overwriting what the user typed). Both are idempotent by value, run from the
#: same call, and exist for the same reason -- an invariant that only one writer
#: enforces is an invariant the other writer breaks (#62/PB-1 for the first,
#: #81/C210-23 for the second).
NORMALIZED_SLICES: Dict[str, Callable[[Project], bool]] = {
    # The M1-1b stall fill. ``__post_init__`` covers every slice built in one go;
    # this covers the oracle GUI, which assembles one field at a time and so
    # never re-runs the constructor.
    "aero_coeffs": lambda p: p.aero_coeffs is not None and p.aero_coeffs.normalize(),
}


def refresh_derived(project: Project) -> List[str]:
    """Bring every derived and normalized slice up to date; the names that changed."""
    changed = [name for name, refresh in DERIVED_SLICES.items() if refresh(project)]
    changed += [name for name, fix in NORMALIZED_SLICES.items() if fix(project)]
    return changed


__all__ = ["DERIVED_SLICES", "NORMALIZED_SLICES", "refresh_derived"]
