"""GW-BASIC numeric semantics the ported ``.BAS`` programs depend on.

**The one owner** (CONVENTIONS.md §5/§7) of the single BASIC intrinsic whose
Python look-alike is *not* equivalent: ``INT()``. GW-BASIC's ``INT(x)`` returns
the largest integer <= ``x`` (floor); Python's ``int(x)`` truncates toward zero.
The two agree for ``x >= 0`` and differ by exactly one unit for every negative
non-integer ``x`` -- so spelling ``INT()`` as ``int()`` is correct only for as
long as the truncated quantity happens to stay positive, and silently reports one
unit less the first time it does not.

ENGLOADS.BAS prints ``INT(-TORQSUDSTOP)`` for the 23.361(b)(1) sudden-stoppage
engine-mount reaction torque (``reference/FAR23Loads_Code.pdf`` p466, Appendix C
listing line 944), and the reaction torque is reported *negative* by convention
(CONVENTIONS.md §5) -- so that argument is negative by construction and the
``int()`` port under-reported the torque by 1 ft-lb, in the non-conservative
direction. The 3-decimal truncations are the same defect class wherever their
argument can go negative (a left-hand engine's Y c.g., a lever arm forward of
the datum), which is why they route through here too rather than being judged
site by site.

Truncation is preserved only where the ``.BAS`` truncated -- never added or
removed without checking the Appendix C listing.
"""

import math


def basic_int(value: float) -> float:
    """GW-BASIC ``INT(value)``: the largest integer <= ``value`` (floor)."""
    return float(math.floor(value))


def basic_trunc3(value: float) -> float:
    """GW-BASIC ``INT(value*1000)/1000`` -- the suite's 3-decimal truncation."""
    return math.floor(value * 1000) / 1000
