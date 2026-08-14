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

The full-span balanced deck mints through :func:`balanced_subcase_id`, which is
the same map moved into its own per-hand block (decision **D-R7**, 2026-08-10):
that deck is the only family carrying handed twins, and an integer subcase id
has nowhere to put the ``L``/``R`` suffix.

Because there are two minters, one case can hold **two** deck numbers -- ``W-05``
is ``105`` in the wing component deck and ``5105`` in the assembled one.
:func:`deck_load_id` is the single owner of that choice for every deliverable
(report, case index, GUI), and :func:`case_label` the single formatter that
states id + ``LABEL`` + ``LOAD``/``SUBCASE`` together
(``docs/30_future/17_case_load_id_linkage_note.md``).
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

    Deliberately **not** understood by :func:`subcase_id`: a handed id reaching
    the per-component numbering would mean a component deck had grown a hand it
    has no band for. That raises, loudly, which is correct. The assembled deck,
    which is where handed cases live, mints through
    :func:`balanced_subcase_id` instead.
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


#: The assembled (balanced) deck's subcase block, per hand: the thousands part
#: names the hand, the rest is the case's own :func:`subcase_id`, so ``W-05R``
#: reads as *starboard, wing slot 5* by eye. ``6000`` is deliberately skipped --
#: the balanced deck's own GIDs run 6001-7000, and a file whose SUBCASE ids
#: repeat its node numbers is needlessly hard to read (``export/bands.py``).
BALANCED_HAND_BLOCK: Dict[str, int] = {"": 5000, "R": 7000, "L": 8000}


def balanced_subcase_id(case_id: str) -> int:
    """The assembled deck's ``SUBCASE`` / ``SID`` integer for ``case_id`` (D-R7).

    ``"W-01"`` -> ``5101``, ``"W-05R"`` -> ``7105``, ``"VT-01L"`` -> ``8301``.

    The assembled deck numbered its subcases positionally (``BALANCED_SID_BASE +
    i``) until 2026-08-10, which is exactly the renumbering instability M4-2
    decision 8 removed from every other deck family: dropping one condition from
    the set moved the id of every case after it, and a solver result labelled
    ``SUBCASE 5007`` meant nothing without the run that produced it. Minted here
    instead, from the case's own :class:`~sloads.models.CaseRef` id, the number
    survives any edit to the case set and traces back by eye.

    Handedness is a **block**, not a suffix on the number, because a ``SUBCASE``
    id is an integer: the port twin of ``W-05`` cannot be ``7105L``. The
    unhanded id still names the physical condition, so the two twins of one
    condition differ only in their thousands digit.
    """
    hand = case_id[-1:] if case_id[-1:] in HANDS else ""
    return BALANCED_HAND_BLOCK[hand] + subcase_id(unhanded_case_id(case_id))


# --------------------------------------------------------------------------- #
# Deck-side identity for the deliverables (report, case index, GUI)
# --------------------------------------------------------------------------- #
#: The two deck families a case can be numbered in. They are **not**
#: interchangeable and one case may have a number in both: ``W-05`` is ``105`` in
#: the wing component deck and ``5105`` in the assembled full-span deck. Every
#: deliverable that prints the integer states which family it is quoting, because
#: an unqualified number is silently wrong for whichever family it is not.
COMPONENT_DECK = "component"
ASSEMBLED_DECK = "assembled"
DECK_FAMILIES = (COMPONENT_DECK, ASSEMBLED_DECK)


def deck_load_id(case_id: str, family: str = COMPONENT_DECK) -> str:
    """The deck ``LOAD``/``SUBCASE`` integer for ``case_id`` as display text.

    The single owner of "which minter applies, and what a case without a number
    in this family shows" -- the report (``report/content``), the case index
    (``export/sbeam_bridge``) and the GUI all read it here rather than each
    reaching into :func:`subcase_id` / :func:`balanced_subcase_id` with their own
    handedness rule. ``tests/test_case_ids.py`` pins the answers against the deck
    writers' own output.

    Returns ``""`` -- never raises -- when the case has no number in ``family``:

    * a **handed** id (``W-05R``) in the component family: those cases exist only
      in the assembled deck, and :func:`subcase_id` refuses a hand by design;
    * a string that is not a case id at all.

    A blank is deliberate and is never filled with the positional fallback
    (``sid_base + index``) the deck writers keep for a result carrying no
    ``CaseRef``: that number is the position-dependent id M4-2 decision 8
    removed, and publishing it invites a reader to key on it.
    """
    if family not in DECK_FAMILIES:
        raise ValueError(f"family must be one of {DECK_FAMILIES}, got {family!r}")
    try:
        if family == ASSEMBLED_DECK:
            return str(balanced_subcase_id(case_id))
        if case_id[-1:] in HANDS:
            return ""
        return str(subcase_id(case_id))
    except ValueError:
        return ""


#: What a deliverable prints where a case has no number in the family it is
#: quoting -- one em dash, so a blank cell reads as "none", not as "not filled in".
NO_LOAD_ID = "—"


def case_label(case_ref, family: str = COMPONENT_DECK, *, condition: str = "") -> str:
    """One case's display identity: ``"W-03 · LOAD 103 · PHAA · FAR 23.333(b)"``.

    The single formatter for every GUI case label and any prose that names a
    case, so the id, the deck ``LABEL`` (which *is* the id) and the deck
    ``LOAD``/``SUBCASE`` integer are stated together everywhere a human reads
    them -- before this existed the views each built their own string and only
    the case-index CSV carried the number at all.

    ``case_ref`` is anything with ``case_id`` / ``condition`` / ``far_reference``
    (a :class:`~sloads.models.results.CaseRef`); ``condition`` overrides the
    ref's own text for a caller that has a better label to hand. ``family``
    picks which deck's number is quoted -- pass :data:`ASSEMBLED_DECK` on a page
    showing the assembled full-span cases.
    """
    case_id = getattr(case_ref, "case_id", "") or ""
    load = deck_load_id(case_id, family) or NO_LOAD_ID
    parts = [case_id or "(no case id)", f"LOAD {load}"]
    text = condition or getattr(case_ref, "condition", "") or ""
    if text:
        parts.append(text)
    far = getattr(case_ref, "far_reference", "") or ""
    if far:
        parts.append(f"FAR {far}")
    return " · ".join(parts)
