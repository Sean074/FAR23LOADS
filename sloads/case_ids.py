"""Structured load-case ID allocation (Step D1; ``docs/30_future/00_backlog.md``).

Exactly six component prefixes -- control surfaces fold into their host
structural component, per the D-1 taxonomy decision:

======================  ========  ============================================
Component               Prefix    Hosts
======================  ========  ============================================
wing                    ``W``     WINGINER/NETLOADS, AILERON, FLAPLOAD, wing tab
htail                   ``HT``    SELECT rational h-tail loads, htail tab
vtail                   ``VT``    SELECT rational v-tail loads, ONENGOUT, vtail tab
fuselage                ``F``     SELECT critical fuselage conditions
engine_mount            ``EM``    ENGLOADS
landing_gear            ``LG``    LANDLOAD
======================  ========  ============================================

IDs are ``f"{prefix}-{seq:02d}"``. Each minting module owns a private
:class:`CaseIdAllocator` instance scoped to its own build call -- there is no
shared/global counter. Determinism ("the same project always yields the same
IDs") comes from each module's own fixed emission order, not from run-order
coordination.

``W`` is minted by more than one module (WINGINER/NETLOADS is the structural
deliverable; AILERON/FLAPLOAD/a wing-hosted tab are separate modules with no
shared allocator state), so those contributions are **banded** into disjoint
numeric ranges wide enough that no realistic case count collides:

* ``W-01``..``W-39`` -- WINGINER/NETLOADS wing structural cases
* ``W-40``..``W-49`` -- ``select_wing``'s own ``CriticalCondition`` list (a
  genuinely separate counter from WINGINER's -- sharing 1..49 would let two
  independent counters produce the same number, an outright collision, not
  just the accepted divergent-sequence gap)
* ``W-50``..``W-59`` -- AILERON
* ``W-60``..``W-69`` -- FLAPLOAD
* ``W-70``+          -- a wing-hosted tab (TABLOADS)

``HT``/``VT`` tabs (TABLOADS) also need a band, since they mint from their own
allocator (scoped to ``build_tabs``) rather than SELECT's -- without one, a tab's
``HT-01``/``VT-01`` could numerically collide with SELECT's own ``HT-01``/``VT-01``
(a different physical case, not just a divergent sequence like the wing/
one-engine-out gap below):

* ``HT-50``+ -- a horizontal-tail-hosted tab
* ``VT-50``+ -- a vertical-tail-hosted tab

``select_wing``'s own ``CriticalCondition`` list and ``one_engine_out``'s
vertical-tail result each mint from their *own* allocator too -- see the
accepted-gap note in ``docs/30_future/00_backlog.md`` Step D1 and
``docs/30_future/02_gui_workflow_plan.md`` D-1: they share a prefix with
WINGINER/``select_vtail`` respectively but are not the same case object.
"""

from __future__ import annotations

from typing import Dict

COMPONENT_PREFIX: Dict[str, str] = {
    "wing": "W",
    "htail": "HT",
    "vtail": "VT",
    "fuselage": "F",
    "engine_mount": "EM",
    "landing_gear": "LG",
}

# Reserved starting sequence numbers for each wing-prefix band (see module
# docstring). WINGINER/NETLOADS starts at 1 (the default); the others start an
# allocator pre-seeded at (band_start - 1) so the first next_id() call yields
# band_start.
WING_BAND_STRUCTURAL = 1
# select_wing's own CriticalCondition list is a genuinely separate counter from
# WINGINER/NETLOADS's -- sharing the 1..49 range would let the two collide (two
# independent counters starting at 1 produce the same numbers), which is not
# just the accepted "divergent sequence" gap but an outright ID collision (the
# same "W-02" meaning two different physical cases). It gets its own disjoint
# sub-band instead.
WING_BAND_SELECT = 40
WING_BAND_AILERON = 50
WING_BAND_FLAP = 60
WING_BAND_TAB = 70

# TABLOADS mints from its own allocator (not SELECT's), so its HT-/VT- tab ids
# are banded away from SELECT's own htail/vtail sequences to avoid an outright
# numeric collision (not just a divergent-sequence gap).
HTAIL_BAND_TAB = 50
VTAIL_BAND_TAB = 50


class CaseIdAllocator:
    """A per-call-site sequential allocator: one counter per component.

    Not shared across modules or runs -- create a fresh instance at the top of
    each minting build function so IDs are a pure function of that function's
    own (already-deterministic) emission order.
    """

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}

    def seed(self, component: str, start_before: int) -> None:
        """Pre-seed a component's counter so the next ``next_id`` call yields
        ``start_before`` (used to start a wing sub-band at 50/60/70)."""
        self._counters[component] = start_before - 1

    def next_id(self, component: str) -> str:
        prefix = COMPONENT_PREFIX[component]
        n = self._counters.get(component, 0) + 1
        self._counters[component] = n
        return f"{prefix}-{n:02d}"
