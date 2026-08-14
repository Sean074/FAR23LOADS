"""The single owner of every exported id band -- GID, EID and SID.

Why this module exists
----------------------
Bulk-data ids are a shared namespace across deck families that were written
months apart. Two decks that number their nodes from the same base do not fail:
they *splice*, and an assembled airframe then sums two unrelated loads on one
node. That is the D-19 failure class -- a deck that parses cleanly and is
silently wrong -- applied to ids instead of units.

It happened. The balanced deck (plan 11) allocated ``4001+`` for its right wing
while the spanwise h-tail deck already owned ``4001-4499``; both files' own
docstrings claimed disjointness, and both guard tests hand-enumerated the bands
they knew about, so neither saw it (review 2026-08-10 **F-C1**/**F-G3**). The
structural fix is ``CLAUDE.md`` practice 3: **one owner plus a drift guard**, not
prose. Every band is declared here, every allocator goes through
:meth:`Band.allocate`, and :mod:`tests.test_bands` proves the registry is both
internally disjoint and exhaustive -- a base constant defined anywhere in
``sloads/export`` that is not a registered band's ``start`` fails the guard, so a
new deck family cannot re-open the blind spot.

The map
-------
::

    GID   1-1000    wing stick model (root node + stations)
       1001-1500    fuselage mass stations + the tail air load
       1501-2000    wing carry-through / fallback correction nodes
       2001-2100    chordwise h-tail stations
       2101-2200    chordwise v-tail stations
       3001-4000    control-surface chord stations
       4001-4500    spanwise h-tail stations
       4501-5000    spanwise v-tail stations
       5001-5300    elevator hinge / actuator nodes
       5301-5600    rudder hinge / actuator nodes
       6001-6200    balanced deck, right wing
       6201-6400    balanced deck, left wing
       6401-7000    balanced deck, centreline

    EID      1-1000  stick-model CBAR chain
          9001-9100  CONM2 baseline (always-aboard items)
          9101-9200  CONM2 discretionary overlay items
          9201-9300  CONM2 per-case ballast
        900001-901000  round-trip harness RBE2 ties (test scaffolding)

    SID          1  SPC set (constraints, not loads)
           101-199  wing subcases          (case_ids.SUBCASE_BLOCK)
           201-299  h-tail subcases
           301-399  v-tail subcases
           401-499  fuselage subcases
           501-599  empennage subcases
           601-699  landing-gear subcases
          5001-5100  balanced-deck subcases, positional fallback (no CaseRef)
          5101-5699  balanced-deck subcases, symmetric  (case_ids.
          7101-7699  balanced-deck subcases, starboard   balanced_subcase_id:
          8101-8699  balanced-deck subcases, port        block + subcase_id)
          9301-9400  MASSSET sets, one per payload case
          9401-9500  GRAV sets, one per payload case

The ``CONM2`` EID bands are additionally kept clear of **GID** space, which
NASTRAN does not require: it makes every id in a spliced mass-plus-load deck
traceable to one owner by inspection. Bands say so for themselves
(:attr:`Band.clear_of_gids`); the stick model's ``CBAR`` chain declines, having
numbered 1..n alongside its own GRIDs since the first deck.

One deliberate mirror: the per-component subcase blocks are **allocated** by
:data:`sloads.case_ids.SUBCASE_BLOCK` -- and the balanced deck's per-hand blocks
by :data:`sloads.case_ids.BALANCED_HAND_BLOCK` -- which are calc-side and must
not import the export package. They are registered here so the disjointness
question has one place to be asked, and ``tests/test_bands.py`` pins the two
against each other so neither can move alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterator, Tuple


class IdKind(Enum):
    """The bulk-data namespace a band allocates in."""

    GID = "GID"
    EID = "EID"
    SID = "SID"


@dataclass(frozen=True)
class Band:
    """One contiguous, exclusively-owned run of ids.

    ``start`` is the first id and ``size`` the count, so the band owns
    ``start .. start + size - 1``. ``owner`` names the code that allocates from
    it -- the answer to "who put this id in my deck?" -- and ``note`` carries
    the reason the band exists where it does, when that is not obvious.
    """

    name: str
    kind: IdKind
    start: int
    size: int
    owner: str
    note: str = ""
    #: EID bands only: also keep clear of every GID band. NASTRAN does not
    #: require it -- elements and grids are separate namespaces -- but a deck
    #: that splices a ``CONM2`` set into a load deck is much easier to read (and
    #: to debug) when an id belongs to exactly one owner. The stick model's
    #: ``CBAR`` chain deliberately declines: it numbers 1..n alongside the
    #: GRIDs it connects, and always has.
    clear_of_gids: bool = False

    @property
    def end(self) -> int:
        """The last id in the band (inclusive)."""
        return self.start + self.size - 1

    def allocate(self, index: int) -> int:
        """The ``index``-th id in this band (0-based), or raise.

        Raising on overflow rather than returning ``start + index`` is the whole
        point: an unchecked allocator walks into the next band and the deck it
        writes is still valid bulk data.
        """
        if not 0 <= index < self.size:
            raise ValueError(
                f"{self.owner}: {self.kind.value} index {index} is outside the "
                f"{self.size}-id band '{self.name}' at {self.start}-{self.end}")
        return self.start + index

    def __contains__(self, value: int) -> bool:
        return self.start <= value <= self.end

    def ids(self) -> range:
        """Every id the band owns -- for the disjointness guard."""
        return range(self.start, self.end + 1)


def _band(*args, **kwargs) -> Band:
    return Band(*args, **kwargs)


#: Every band in the suite, in id order within each kind. **The registry.**
#: Adding a deck family means adding a row here first; nothing else may invent a
#: base constant (guarded by ``tests/test_bands.py``).
BANDS: Tuple[Band, ...] = (
    # ----------------------------------------------------------------- GIDs
    _band("wing-stick", IdKind.GID, 1, 1000, "sbeam_bridge.station_gid",
          "GID 1 is the clamped root; station i takes 2 + i."),
    _band("body-mass", IdKind.GID, 1001, 500, "sbeam_bridge.beam_station_gid",
          "Fuselage mass stations and the tail air load, nose->tail."),
    _band("body-reaction", IdKind.GID, 1501, 500, "sbeam_bridge.body_station_gids",
          "Wing carry-through / fallback correction nodes -- a separate band so "
          "inserting one never renumbers a mass station."),
    _band("tail-chord-htail", IdKind.GID, 2001, 100, "sbeam_bridge.tail_station_gid"),
    _band("tail-chord-vtail", IdKind.GID, 2101, 100, "sbeam_bridge.tail_station_gid",
          "Its own sub-block: the two surfaces' chord stations are different "
          "points, so one shared run would define a node at two locations."),
    _band("control-surface", IdKind.GID, 3001, 1000, "sbeam_bridge.control_station_gid"),
    _band("tail-span-htail", IdKind.GID, 4001, 500, "sbeam_bridge.tail_span_gid"),
    _band("tail-span-vtail", IdKind.GID, 4501, 500, "sbeam_bridge.tail_span_gid"),
    _band("tail-control-htail", IdKind.GID, 5001, 300,
          "sbeam_bridge.tail_control_gid",
          "Elevator hinge and actuator nodes (plan 09 T6). Their own band rather "
          "than a continuation of the spanwise one: a hinge station is not a "
          "strip midpoint, so it is a different point, and adding hinges must "
          "never renumber the strips beside them."),
    _band("tail-control-vtail", IdKind.GID, 5301, 300,
          "sbeam_bridge.tail_control_gid", "Rudder hinge and actuator nodes."),
    _band("balanced-wing-right", IdKind.GID, 6001, 200, "balanced_deck.deck_nodes",
          "Left and right are separate runs so an antisymmetric case can load "
          "them differently without renumbering (plan 11 B7). The name records "
          "what first needed the split; the run carries every load on that side "
          "of the centreline, which from D-R8 includes the 23.427(a) h-tail "
          "strips."),
    _band("balanced-wing-left", IdKind.GID, 6201, 200, "balanced_deck.deck_nodes"),
    _band("balanced-centreline", IdKind.GID, 6401, 600, "balanced_deck.deck_nodes",
          "Fuselage masses, the tail air load, the lumped body Cm, and every "
          "closure point on the centreline."),
    # ----------------------------------------------------------------- EIDs
    _band("stick-element", IdKind.EID, 1, 1000, "sbeam_bridge.stick_model_bdf",
          "The CBAR chain of the minimal stick model."),
    _band("mass-baseline", IdKind.EID, 9001, 100, "mass_cards.mass_cards",
          "Always-aboard items -- the MASSSET baseline (plan 12 C-1).",
          clear_of_gids=True),
    _band("mass-discretionary", IdKind.EID, 9101, 100, "mass_cards.mass_cards",
          "Overlay-only items, named by a case's ADD row.", clear_of_gids=True),
    _band("mass-ballast", IdKind.EID, 9201, 100, "mass_cards.mass_cards",
          "One per derived loading.", clear_of_gids=True),
    _band("roundtrip-rbe2", IdKind.EID, 900001, 1000, "roundtrip.wrap_as_stick_model",
          "Test scaffolding: numbered well clear of the CBAR chain so a wrapped "
          "deck's ties are never mistaken for exported structure.",
          clear_of_gids=True),
    # ----------------------------------------------------------------- SIDs
    _band("spc", IdKind.SID, 1, 1, "sbeam_bridge / balanced_deck / roundtrip",
          "The constraint set. A different NASTRAN namespace from LOAD, but "
          "registered so nothing quietly allocates a load set at 1."),
    _band("subcase-W", IdKind.SID, 101, 99, "case_ids.subcase_id"),
    _band("subcase-HT", IdKind.SID, 201, 99, "case_ids.subcase_id"),
    _band("subcase-VT", IdKind.SID, 301, 99, "case_ids.subcase_id"),
    _band("subcase-F", IdKind.SID, 401, 99, "case_ids.subcase_id"),
    _band("subcase-EM", IdKind.SID, 501, 99, "case_ids.subcase_id"),
    _band("subcase-LG", IdKind.SID, 601, 99, "case_ids.subcase_id"),
    _band("balanced-subcase-unmapped", IdKind.SID, 5001, 100,
          "balanced_deck.case_sids",
          "The positional fallback, for an assembled case carrying no CaseRef "
          "at all (a bare case list built in a test). Every case the suite "
          "assembles is minted; this band is what an unidentifiable one gets "
          "instead of colliding with a minted id."),
    _band("balanced-subcase", IdKind.SID, 5101, 599, "case_ids.balanced_subcase_id",
          "Minted, symmetric hand (D-R7): 5000 + the case's own subcase_id."),
    _band("balanced-subcase-stbd", IdKind.SID, 7101, 599,
          "case_ids.balanced_subcase_id",
          "Minted, starboard twin. 6000 is skipped: it is this same deck's "
          "wing/centreline GID range, and repeating those numbers as load-set "
          "ids in one file is a readability trap for no gain."),
    _band("balanced-subcase-port", IdKind.SID, 8101, 599,
          "case_ids.balanced_subcase_id", "Minted, port twin."),
    _band("massset", IdKind.SID, 9301, 100, "mass_cards.mass_check_deck"),
    _band("grav", IdKind.SID, 9401, 100, "mass_cards.inertia_only_cards"),
)

_BY_NAME: Dict[str, Band] = {b.name: b for b in BANDS}


def band(name: str) -> Band:
    """The registered band called ``name``, or raise."""
    try:
        return _BY_NAME[name]
    except KeyError:
        raise ValueError(
            f"no id band named {name!r} -- registered: "
            f"{', '.join(sorted(_BY_NAME))}") from None


def bands_of_kind(kind: IdKind) -> Tuple[Band, ...]:
    """Every band in one namespace, in id order."""
    return tuple(b for b in BANDS if b.kind is kind)


def owner_of(value: int, kind: IdKind) -> str:
    """The band name owning ``value``, or ``""`` -- for error messages and tests."""
    for b in bands_of_kind(kind):
        if value in b:
            return b.name
    return ""


def _compared(a: Band, b: Band) -> bool:
    """Do these two bands have to be disjoint?

    Same namespace: always. Different namespaces: only where an EID band asked
    to stay clear of GID space (:attr:`Band.clear_of_gids`) -- NASTRAN keeps the
    namespaces apart, so this is a readability contract, declared per band
    rather than assumed for all of them.
    """
    if a.kind is b.kind:
        return True
    kinds = {a.kind, b.kind}
    if kinds == {IdKind.GID, IdKind.EID}:
        eid = a if a.kind is IdKind.EID else b
        return eid.clear_of_gids
    return False


def overlaps() -> Iterator[Tuple[Band, Band]]:
    """Every colliding pair in the registry -- the disjointness guard's engine."""
    numbered = tuple(BANDS)
    for i, a in enumerate(numbered):
        for b in numbered[i + 1:]:
            if not _compared(a, b):
                continue
            if a.start <= b.end and b.start <= a.end:
                yield (a, b)


__all__ = [
    "BANDS",
    "Band",
    "IdKind",
    "band",
    "bands_of_kind",
    "overlaps",
    "owner_of",
]
