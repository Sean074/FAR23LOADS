"""Structured load-case ID allocation (Step D1; unified at M4-2).

Exactly six component prefixes -- control surfaces fold into their host
structural component, per the D-1 taxonomy decision:

======================  ========  ============================================
Component               Prefix    Hosts
======================  ========  ============================================
wing                    ``W``     SELECT + WINGINER/NETLOADS, AILERON, FLAPLOAD, wing tab
htail                   ``HT``    SELECT rational h-tail loads, htail tab
vtail                   ``VT``    SELECT rational v-tail loads, ONENGOUT, vtail tab
fuselage                ``F``     SELECT critical fuselage conditions
engine_mount            ``EM``    ENGLOADS
landing_gear            ``LG``    LANDLOAD
======================  ========  ============================================

IDs are ``f"{prefix}-{seq:02d}"``. **One ID per physical condition** (M4-2
decision 1): where two modules deliver the same condition -- SELECT names the
governing wing point, WINGINER/NETLOADS distribute it spanwise -- they carry the
*same* ``CaseRef``, minted once, so ``sbeam_bridge.case_index_rows_from``'s
dedupe-by-``case_id`` collapses them to one row as it was written to.

Wing sequence: fixed slots, not positions (M4-2 decision 4)
-----------------------------------------------------------
The wing ``seq`` is a property of the *condition*, taken from
:data:`WING_SLOTS` -- ``select_wing``'s own fixed pick order. A wing case is
``W-01`` because it is PHAA, not because it happened to be first in a list, so a
changed envelope (one pick missing, a different order in
``WingMassInput.cases``) leaves a gap instead of renumbering every other case.
Persisted ``selected_case_ids`` and previously exported decks reference these
strings, which is why they may not float.

Bands
-----
Modules that mint from their own allocator are **banded** into disjoint numeric
ranges wide enough that no realistic case count collides -- two independent
counters starting at 1 would otherwise produce the same ID for two different
physical cases (an outright collision, not merely a divergent sequence):

* ``W-01``..``W-19`` -- the fixed :data:`WING_SLOTS` conditions (SELECT and the
  WINGINER/NETLOADS results derived from them: the same case, the same ID)
* ``W-20``..``W-39`` -- :data:`WING_BAND_EXTRA`: a hand-authored
  ``WingMassInput.cases`` entry with no ``WING_SLOTS`` name (a concept-mode
  extra condition SELECT does not emit)
* ``W-50``..``W-59`` -- AILERON
* ``W-60``..``W-69`` -- FLAPLOAD
* ``W-70``+          -- a wing-hosted tab (TABLOADS)
* ``HT-01``..        -- SELECT's rational h-tail conditions
* ``HT-50``+         -- a horizontal-tail-hosted tab
* ``VT-01``..        -- SELECT's rational v-tail conditions
* ``VT-30``..``VT-49`` -- :data:`VTAIL_BAND_ONENGOUT`: ONENGOUT (23.367). Its
  dynamic one-engine-out case is **not** one of SELECT's picks, so it is a
  different case object with its own ID -- banded rather than sharing SELECT's
  counter, which would need cross-module allocator state and make IDs depend on
  module run order (M4-2 decision 5).
* ``VT-50``+         -- a vertical-tail-hosted tab

``tests/test_case_ids.py`` is the drift guard: it asserts every minted ID across
a full run is unique, so a new minter that forgets its band fails there rather
than in a deck.

Deck subcase numbering (M4-2 decision 8)
----------------------------------------
:func:`subcase_id` maps a case ID to the integer a solver deck uses for its
``SUBCASE`` and its load-set ``SID``. It is a pure function of the case ID, so a
filtered export (``filter_by_selected_case_ids``) cannot renumber the subcases
that survive, and the component blocks keep wing/tail/body subcases distinct in
an assembled multi-component deck.
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

#: The wing condition -> sequence number map: ``select_wing``'s fixed pick order
#: (``modules/select.py``'s ``picks`` list). The *name* owns the number, so
#: WINGINER/NETLOADS and SELECT reach the same ID for the same condition without
#: sharing runtime state, and a missing pick leaves a gap rather than shifting
#: its neighbours (M4-2 decision 4).
WING_SLOTS: Dict[str, int] = {
    "PHAA": 1,
    "PLAA": 2,
    "PMAA": 3,
    "NMAA": 4,
    "ACRL": 5,
    "TORS": 6,
}

# Reserved starting sequence numbers for each band (see the module docstring).
# An allocator is pre-seeded at (band_start - 1) so its first next_id() call
# yields band_start.
WING_BAND_SLOTS = 1        # WING_SLOTS conditions: 1..19
WING_BAND_EXTRA = 20       # hand-authored wing cases outside WING_SLOTS: 20..39
WING_BAND_AILERON = 50
WING_BAND_FLAP = 60
WING_BAND_TAB = 70

# TABLOADS mints from its own allocator (not SELECT's), so its HT-/VT- tab ids
# are banded away from SELECT's own htail/vtail sequences.
HTAIL_BAND_TAB = 50
VTAIL_BAND_TAB = 50

# ONENGOUT's own VT- band, below the tab band (M4-2 decision 5).
VTAIL_BAND_ONENGOUT = 30


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
        ``start_before`` (used to start a band at 20/30/50/60/70)."""
        self._counters[component] = start_before - 1

    def next_id(self, component: str) -> str:
        prefix = COMPONENT_PREFIX[component]
        n = self._counters.get(component, 0) + 1
        self._counters[component] = n
        return f"{prefix}-{n:02d}"


def wing_case_id(label: str) -> str:
    """The ``W-nn`` id of the fixed-slot wing condition ``label`` (``"PHAA"``).

    Raises :class:`KeyError` for a label outside :data:`WING_SLOTS` -- the caller
    decides whether that is an error or an extra-band case."""
    return f"{COMPONENT_PREFIX['wing']}-{WING_SLOTS[label]:02d}"


#: Deck subcase/SID block per component prefix: ``W-03`` -> ``103``,
#: ``HT-02`` -> ``202``, ... Blocks are 100 wide, which covers every band above
#: (the widest, ``W``, tops out in the 70s).
SUBCASE_BLOCK: Dict[str, int] = {
    "W": 100,
    "HT": 200,
    "VT": 300,
    "F": 400,
    "EM": 500,
    "LG": 600,
}


#: The handedness suffixes a balanced case id may carry (plan 11 decision B-7).
HANDS = ("L", "R")


def handed_case_id(case_id: str, hand: str) -> str:
    """``("W-05", "R") -> "W-05R"`` -- the handed form of a case id (B-7).

    Every asymmetric family has an opposite-hand twin, and decision B-7 makes
    handedness a **suffix on the existing id** rather than a new ID series
    (``CLAUDE.md`` naming rule): the unhanded id remains the physical condition,
    and ``W-05L``/``W-05R`` are the two cases derived from it. Idempotent -- a
    handed id re-handed keeps one suffix, so a twin of a twin is not ``W-05RL``.

    Deliberately **not** understood by :func:`subcase_id`: the assembled deck
    numbers its own subcases positionally from ``BALANCED_SID_BASE``, and a
    handed id reaching the per-component numbering would mean a component deck
    had grown a hand it has no band for. That raises, loudly, which is correct.
    """
    if hand not in HANDS:
        raise ValueError(f"hand must be one of {HANDS}, got {hand!r}")
    return unhanded_case_id(case_id) + hand


def unhanded_case_id(case_id: str) -> str:
    """The physical condition's id, with any handedness suffix removed."""
    return case_id[:-1] if case_id[-1:] in HANDS else case_id


def subcase_id(case_id: str) -> int:
    """The deck ``SUBCASE`` / load-set ``SID`` integer for ``case_id``.

    ``"W-03"`` -> ``103``, ``"VT-31"`` -> ``331``. Deterministic and reversible
    by eye, so a solver result labelled ``SUBCASE 103`` traces back to the
    governing condition through the deck's own ``$`` map block and the exported
    case index (M4-2 decisions 8/9).

    Raises :class:`ValueError` for a string that is not a case ID -- the deck
    writers fall back to positional numbering only for results that carry no
    ``CaseRef`` at all, never for a malformed one.
    """
    prefix, _, seq = case_id.partition("-")
    if prefix not in SUBCASE_BLOCK or not seq.isdigit():
        raise ValueError(f"not a case id: {case_id!r}")
    return SUBCASE_BLOCK[prefix] + int(seq)
