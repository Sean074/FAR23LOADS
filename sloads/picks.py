"""Platform-stable extreme picks — the single owner of every keyed ``max``/``min``.

A pick between candidates whose keys are *equal in exact arithmetic* is the
classic source of a deliverable byte that depends on the machine: the two keys
are computed along different paths (a ``sqrt(sigma)`` round-trip, a summation
that one Python version compensates and another does not), land one ulp apart,
and land on **different sides on different platforms**. ``max`` then returns a
different candidate in CI than on the developer's Mac, and a frozen digest fails
for a difference no printed digit shows.

:func:`extreme` is the repo-wide answer (``CONVENTIONS.md`` §7, platform-stable
deliverable bytes). It was `select.py`'s private ``_extreme`` until review
2026-08-20 CR-B-1 found the same defect class in five other modules and in the
exporters; it now owns every keyed pick in ``sloads/``, and
``tests/test_platform_stability.py`` walks the package's AST to keep it that way.
"""

from typing import Callable, Iterable, TypeVar

__all__ = ["TIE_REL", "extreme"]

T = TypeVar("T")

#: Two keys within this *relative* band are one physical value, not two.
TIE_REL = 1e-9


def extreme(items: Iterable[T], key: Callable[[T], float], largest: bool = True) -> T:
    """``max``/``min`` by ``key`` with a **deterministic, platform-stable tie**.

    Two V-n points can carry the same physical load — VA is the same EAS at
    every altitude and CG, so ``BAL A`` at altitude 1 and altitude 2 tie
    exactly on the rudder-load key. Two gear cases can share a VMP (LANDLOAD
    cases 19-22 do), two mass cases can weigh the same, and two structural
    nodes can sit equidistant from a load point on a symmetric airplane.

    So: the winner is the largest (smallest) key, and among candidates whose
    keys agree to :data:`TIE_REL` relative, the **first in list order** — which
    is exactly what ``max``/``min`` return for a bit-exact tie, so no pick moves
    on the local machine; only the platform-dependent ones become stable.

    Raises ``IndexError`` on an empty ``items``, as ``max``/``min`` do.
    """
    seq = list(items)
    keys = [key(x) for x in seq]
    best = max(keys) if largest else min(keys)
    band = TIE_REL * abs(best)
    for x, k in zip(seq, keys):
        if (k >= best - band) if largest else (k <= best + band):
            return x
    return seq[0]  # unreachable: `best` is one of `keys`
