"""CONM2 / MASSSET mass export -- an *independent* mass model for sbeam.

Plan 12 (``docs/30_future/12_conm2_mass_export_plan.md``), steps C3/C4,
decisions C-2/C-3/C-6. Conventions: ``docs/10_standard/CONVENTIONS.md``.

Why this exists
---------------
The ``FORCE``/``MOMENT`` deck is the **total** applied load -- aero plus inertia
-- and stays that way; it is the deliverable. But it is also *self-consistent by
construction*: the inertia half is computed by the same code that writes the
cards, so nothing outside sloads can contradict it. There is no printed oracle
for a distributed inertia load, so that half has, until now, been checked only
against itself.

Exporting the mass distribution as ``CONM2`` cards breaks the circularity. sbeam
parses the mass model independently, applies the case acceleration through a
``GRAV`` card, recovers the nodal inertia loads itself, and the two can be
compared. That is a genuine external check on the half of the load set with no
oracle -- and it is precisely the class of error step B1 turned up (two mass
models disagreeing by up to 41 % of the fuselage beam, unnoticed for want of
anything comparing them).

Not double-counting inertia, structurally
-----------------------------------------
The total ``FORCE``/``MOMENT`` set already contains inertia. A deck that applies
those cards *and* accelerates the CONM2 masses counts it twice -- and decision
C-6 is that this is made impossible rather than warned about, because it is the
one error here that produces a *plausible* wrong answer (a heavier airplane, not
a crash). So:

* :func:`mass_check_deck` emits **no** ``FORCE``/``MOMENT`` cards at all. Its
  subcases carry ``MASSSET`` + ``GRAV`` and nothing else.
* :func:`inertia_only_cards` (C-4) emits sloads' own inertia contribution as a
  separate, clearly-marked load set for comparison -- and its header says in
  as many words that it must not be applied together with the total set.

Card syntax is sbeam's own (``sbeam/model/mass.py``,
``sbeam/parser/bdf_reader.py``): ``CONM2, EID, GID, CID, M, X1, X2, X3, I11,
I21, I22, I31, I32, I33`` and ``MASSSET, SID, LABEL, SCALE`` followed by
``+, ADD|REPLACE|DELETE, eid...`` continuation rows. A ``MASSSET`` modifies a
**baseline** (the model's own mass plus baseline ``CONM2``s); EIDs named by
``ADD`` are overlay-only and are excluded from that baseline. This module uses
that split directly: the always-aboard items are the baseline, and each payload
case ``ADD``s the discretionary items and ballast it carries.

Units
-----
``CONM2``'s ``M`` is **mass**, and the weight database stores **weight**. The
conversion is the ``mass`` channel added at step C2
(:func:`sloads.units.deliverable_units`), which is the only dimension in the
suite whose Imperial factor is not 1.0 -- see :data:`sloads.units.LB_TO_SLINCH`.
A mass set written with a weight-valued ``M`` is wrong by 386x in a file that
parses cleanly, so :func:`_checked_mass_units` refuses a unit set that does not
satisfy ``force / (mass x length) == g``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..mass_distribution import (
    CaseLoading,
    MassComponent,
    component_of,
    derive_case_loadings,
    fuselage_beam_stations,
)
from ..models import MassItem, Project
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .bands import band
from .coordinates import SBEAM_CID, to_grid
from .sbeam_bridge import _fmt, _sf_str, _stamped, beam_station_gid

# --------------------------------------------------------------------------- #
# EID / SID bands -- declared in :mod:`sloads.export.bands`, the single owner of
# every id run in the suite; that module's guard proves them disjoint from every
# GID band, which is what lets a CONM2 set be spliced into a load deck.
# --------------------------------------------------------------------------- #
_BASELINE_BAND = band("mass-baseline")
_DISCRETIONARY_BAND = band("mass-discretionary")
_BALLAST_BAND = band("mass-ballast")
_PART_FULL_BAND = band("mass-part-full")
_MASSSET_BAND = band("massset")
_GRAV_BAND = band("grav")

#: Always-aboard items (empty + minimum weight) -- the MASSSET **baseline**.
MASS_EID_BASELINE = _BASELINE_BAND.start
#: Discretionary items -- overlay-only, named by a case's ``ADD`` row.
MASS_EID_DISCRETIONARY = _DISCRETIONARY_BAND.start
#: Per-case ballast -- one overlay card per derived loading.
MASS_EID_BALLAST = _BALLAST_BAND.start
#: Per-case part-full consumable rows -- one overlay card per (case, scaled row).
MASS_EID_PART_FULL = _PART_FULL_BAND.start
#: MASSSET SIDs, one per payload case.
MASSSET_SID_BASE = _MASSSET_BAND.start
#: GRAV SIDs, one per payload case.
GRAV_SID_BASE = _GRAV_BAND.start


def _checked_mass_units(units: DeliverableUnits) -> DeliverableUnits:
    """Reject a unit set whose mass pair is not dimensionally consistent (C-5).

    The mass analogue of ``coordinates._checked``, and needed for the same
    reason: the human channel's mass is a pound (or a kilogram), which is a
    *weight*, and writing it into ``CONM2``'s ``M`` gives a deck that parses
    cleanly and accelerates to 386x the right force.
    """
    if not units.is_mass_consistent:
        raise ValueError(
            f"{units.channel.value} unit set (mass {units.mass.label}) is not "
            "dimensionally consistent -- F = m*a does not hold in it, so it must "
            "not be written to a CONM2 card. Resolve it with "
            "deliverable_units(system, Channel.SOLVER)"
        )
    return units


# --------------------------------------------------------------------------- #
# Item -> (EID, GID) assignment
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MassCard:
    """One ``CONM2``: an item, the node it hangs on, and the offset to its CG.

    The offset is what makes the attachment node a *presentational* choice
    (decision C-3): mass, CG and the inertia tensor are exact wherever the card
    is attached, because ``x1/x2/x3`` carry the item's true position relative to
    that node. What the node does decide is where sbeam reports the recovered
    inertia *load*, which is why fuselage items hang on their own beam station.
    """

    eid: int
    gid: int
    item: MassItem
    offset: Tuple[float, float, float]
    overlay: bool
    #: Which loading this card belongs to, for the overlay cards that exist
    #: **per case** rather than per database row -- the solved/entered ballast and
    #: a consumable row carried part-full. ``None`` on a card that is shared, i.e.
    #: one whose item is a database row at its own weight.
    case_index: Optional[int] = None


def _attach_gid(item: MassItem,
                stations: Sequence) -> Tuple[int, Tuple[float, float, float]]:
    """The beam node ``item`` hangs on, and the offset from it to the item's CG.

    Fuselage and empennage items take the nearest fuselage beam station -- the
    same ``1001+`` nodes the fuselage load deck applies its ``FORCE`` cards to,
    so a recovered inertia load lands on the node its applied counterpart does.

    **Wing items also hang on the nearest beam station, and that is a known
    limitation, not a modelling claim.** A wing item belongs on the wing beam,
    but today's wing deck is a single *half-span* (GIDs ``2..N+1``) with no
    left/right bands -- those arrive with plan 11 **B5**, the assembled full-span
    deck. Attaching to the beam keeps mass, CG and inertia exact (the offset does
    that), and the deck says so in its header rather than implying the wing mass
    is where it is drawn.
    """
    if not stations:
        return beam_station_gid(0), (item.x, item.y, item.z)
    index = min(range(len(stations)),
                key=lambda i: abs(stations[i].x - item.x))
    gid = beam_station_gid(index)
    node = stations[index]
    return gid, (item.x - node.x, item.y - 0.0, item.z - 0.0)


def mass_cards(project: Project) -> Tuple[List[MassCard], List[CaseLoading]]:
    """``(cards, loadings)`` -- the baseline + overlay ``CONM2`` set for ``project``.

    Baseline cards are the always-aboard items (empty + minimum weight); overlay
    cards are the discretionary items and each derived loading's ballast. Only
    **derivable** loadings (plan 12 C-1's credibility gate) contribute: a case
    needing 20 % of the airplane as ballast is not a mass model and is reported,
    not exported.
    """
    items = project.weight.items if project.weight is not None else []
    if not items:
        return [], []
    stations = fuselage_beam_stations(project)
    loadings = [ld for ld in derive_case_loadings(project) if ld.derivable]

    from ..models import MassItemKind

    # The overlay set is built from what the loadings actually carry, not from
    # "every discretionary item" -- and that is structural, not tidiness.
    #
    # sbeam's baseline is *every CONM2 no MASSSET names* (overlay-only status
    # comes from being referenced by an ADD/REPLACE row). So an overlay card that
    # no case adds does not sit out: it silently joins the baseline and is
    # counted in EVERY case. Caught 2026-08-08 by running sbeam's own GPWG over
    # the exported ga6 deck -- it recovered 9.0083 slinch against sloads'
    # 8.8063, exactly 78 lb too much, which is the database's own "Ballast" row.
    # That row is superseded by the per-case ballast this export derives, so
    # emitting it at all was double-counting the same physical thing.
    #
    # Deriving the overlay list from the loadings makes an unreferenced overlay
    # card impossible to write; :func:`unreferenced_overlay_eids` is the guard
    # that keeps it that way.
    baseline = [it for it in items if it.kind != MassItemKind.DISCRETIONARY]
    rows = {id(it) for it in items}
    carried = {id(it) for ld in loadings for it in ld.items}
    discretionary = [it for it in items
                     if it.kind == MassItemKind.DISCRETIONARY and id(it) in carried]

    cards: List[MassCard] = []
    for eid_band, group, overlay in ((_BASELINE_BAND, baseline, False),
                                     (_DISCRETIONARY_BAND, discretionary, True)):
        for i, it in enumerate(group):
            gid, offset = _attach_gid(it, stations)
            cards.append(MassCard(eid=eid_band.allocate(i), gid=gid, item=it,
                                  offset=offset, overlay=overlay))
    # A loading may carry a consumable row **part-full** -- a D-25 entered
    # fraction, or the G-5 burn-down a GROUND target runs -- and that item is a
    # scaled copy, not the database row. It therefore cannot share the row's
    # overlay card: one card is one mass, and the same tank at two fuel states is
    # two masses. Each gets its own card, named only by its own case's ADD row.
    #
    # Found 2026-08-15, when the Pri 5 loadings made part-full fuel the norm: the
    # scaled copy matched no card, so the row left the deck entirely and the
    # exported mass model weighed *less* than the loading it declared (dhc8's MLW
    # case by 4,160 lb). It parsed, and it solved.
    part_full = 0
    for i, loading in enumerate(loadings):
        for it in loading.items:
            if id(it) in rows or it is loading.ballast:
                continue        # a database row at its own weight, or the ballast
            if it.kind != MassItemKind.DISCRETIONARY:
                raise ValueError(
                    f"weight/CG case '{loading.name}' carries '{it.name}' "
                    f"part-full, but that row is {it.kind.value} and so sits in "
                    "the MASSSET baseline, which every case shares. Expressing it "
                    "would need a REPLACE row; today only a discretionary row may "
                    "be part-full. Make the row discretionary, or carry it whole.")
            gid, offset = _attach_gid(it, stations)
            cards.append(MassCard(eid=_PART_FULL_BAND.allocate(part_full), gid=gid,
                                  item=it, offset=offset, overlay=True,
                                  case_index=i))
            part_full += 1
    for i, loading in enumerate(loadings):
        if loading.ballast is None:
            continue
        gid, offset = _attach_gid(loading.ballast, stations)
        cards.append(MassCard(eid=_BALLAST_BAND.allocate(i), gid=gid,
                              item=loading.ballast, offset=offset, overlay=True,
                              case_index=i))
    return cards, loadings


def unreferenced_overlay_eids(project: Project) -> List[int]:
    """Overlay ``CONM2`` EIDs that no ``MASSSET`` names -- must always be empty.

    sbeam decides overlay-only status by *reference*: a card no ADD/REPLACE row
    names belongs to the baseline and is therefore in every payload case. An
    overlay card that slipped through would not fail to load, it would quietly
    make every case heavier -- the exact plausible-wrong-answer failure mode
    decision C-6 exists to rule out. Structural by construction (the overlay list
    is built from the loadings); this is the drift guard.
    """
    cards, loadings = mass_cards(project)
    named = {e for i, ld in enumerate(loadings) for e in _overlay_eids(cards, ld, i)}
    return sorted(c.eid for c in cards if c.overlay and c.eid not in named)


def _overlay_eids(cards: Sequence[MassCard], loading: CaseLoading,
                  index: int) -> List[int]:
    """The overlay EIDs one case's ``ADD`` row names.

    Two kinds of card, and the distinction is the whole correctness argument:
    a **shared** card (``case_index is None``) is a database row at its own
    weight, and any case carrying that row names it; a **per-case** card is one
    this case alone owns -- its ballast, or a row it carries part-full -- and is
    named by case index rather than by item.

    Shared cards are matched on object identity, not on name: two items may
    legitimately share a name (``"3rd person"`` / ``"4th person"`` differ only by
    station in some databases), and a MASSSET that named an EID twice is a parse
    error in sbeam by design.
    """
    aboard = {id(it) for it in loading.items}
    return [c.eid for c in cards if c.overlay
            and (c.case_index == index
                 or (c.case_index is None and id(c.item) in aboard))]


# --------------------------------------------------------------------------- #
# Card text
# --------------------------------------------------------------------------- #
def _conm2_line(card: MassCard, u: DeliverableUnits) -> str:
    m = card.item.weight_lb * u.mass.factor
    ox, oy, oz = to_grid(*card.offset, units=u)
    k = u.mass_inertia.factor
    # i21/i31/i32 are the products of inertia. ``MassItem`` carries none, and a
    # laterally symmetric airplane has Ixy = Iyz = 0 exactly; Ixz is generally
    # non-zero but the database has no field for it. Emitted as 0 with the
    # header's note rather than silently -- see plan 12 risk R2.
    return (f"CONM2, {card.eid}, {card.gid}, {SBEAM_CID}, {_fmt(m)}, "
            f"{_fmt(ox)}, {_fmt(oy)}, {_fmt(oz)}, "
            f"{_fmt(card.item.ixx * k)}, 0.0, {_fmt(card.item.iyy * k)}, "
            f"0.0, 0.0, {_fmt(card.item.izz * k)}")


def massset_identity(loading: CaseLoading, index: int) -> Tuple[int, str]:
    """``(SID, LABEL)`` -- the identity the exported mass model gives one loading.

    Minted here and nowhere else, so the ``MASSSET`` card, the report's mass-case
    table and the bundle manifest name one payload case the same way. ``index``
    is the loading's position in the **derivable** list (the order
    :func:`mass_cards` returns and :func:`conm2_fragment` writes), which is what
    the SID band is allocated against.
    """
    label = "".join(ch for ch in loading.name.upper() if ch.isalnum())[:8] or f"CASE{index}"
    return _MASSSET_BAND.allocate(index), label


def mass_case_rows(project: Project) -> List[Dict[str, object]]:
    """One row per payload case: what the exported mass model calls it, or why not.

    Every case in ``flight_loads.cg_cases`` appears -- a case the weight database
    cannot produce as a loading is reported with ``exported=False`` and its
    reason, never dropped, because "absent from the mass model" is exactly the
    fact a consumer needs (plan 12 C-1's credibility gate). ``entered`` says
    whether the loading was **stated on the case** (D-25) or searched for.

    Values are raw Imperial (lb, in) as everywhere else in the calc; the report
    converts at its own boundary.
    """
    loadings = derive_case_loadings(project)
    order = {id(ld): i for i, ld in enumerate(ld for ld in loadings if ld.derivable)}
    rows: List[Dict[str, object]] = []
    for loading in loadings:
        index = order.get(id(loading))
        sid, label = (massset_identity(loading, index) if index is not None
                      else (None, ""))
        rows.append({
            "case": loading.name,
            "exported": loading.derivable,
            # D-25: which route produced this loading. A consumer reading a mass
            # model needs to know whether the loading was stated by the engineer
            # or reconstructed by the search -- the two carry different authority.
            "entered": loading.entered,
            "massset_sid": sid,
            "massset_label": label,
            "weight_lb": loading.weight_lb,
            "cg_x": loading.cg_x,
            "cg_z": loading.cg_z,
            "ballast_lb": loading.ballast.weight_lb if loading.ballast else 0.0,
            "ballast_fraction": loading.ballast_fraction,
            "note": loading.note,
        })
    return rows


def _massset_block(cards: Sequence[MassCard], loading: CaseLoading,
                   index: int) -> List[str]:
    sid, label = massset_identity(loading, index)
    eids = _overlay_eids(cards, loading, index)
    lines = [
        f"$ {loading.name}: {loading.weight_lb:.0f} lb at "
        f"x {loading.cg_x:.2f} in, z {loading.cg_z:.2f} in"
        + (f"; ballast {loading.ballast.weight_lb:.0f} lb "
           f"({loading.ballast_fraction * 100:.1f} %) at x {loading.ballast.x:.1f}"
           if loading.ballast is not None else "; no ballast"),
        f"MASSSET, {sid}, {label}, 1.0",
    ]
    # ADD rows carry up to 7 EIDs each (sbeam's reader).
    for start in range(0, len(eids), 7):
        chunk = ", ".join(str(e) for e in eids[start:start + 7])
        lines.append(f"+, ADD, {chunk}")
    return lines


def _header(project: Project, u: DeliverableUnits, cards: Sequence[MassCard]) -> List[str]:
    total = sum(c.item.weight_lb for c in cards if not c.overlay)
    wing = sum(c.item.weight_lb for c in cards
               if component_of(c.item, project) == MassComponent.WING)
    skipped = [ld for ld in derive_case_loadings(project) if not ld.derivable]
    lines = [
        "$ ==================================================== SLOADS MASS MODEL",
        "$ CONM2 distributed mass from the itemized weight database, with one",
        "$ MASSSET per derivable payload case (baseline = always-aboard items;",
        "$ each case ADDs the discretionary items and ballast it carries).",
        f"$ Mass in {u.mass.label}; inertia in {u.mass_inertia.label}; "
        f"offsets in {u.length.label}.",
        f"$ Baseline (empty + minimum flight weight): {total:.0f} lb.",
        "$",
        "$ DO NOT apply this set together with the FORCE/MOMENT load deck: those",
        "$ cards are the TOTAL applied load and already contain inertia. Using",
        "$ both counts the inertia twice.",
        "$",
        "$ Products of inertia I21/I31/I32 are 0: the database carries none, and",
        "$ Ixy = Iyz = 0 exactly on a laterally symmetric airplane. Ixz is not",
        "$ generally zero and is not modelled.",
    ]
    if wing:
        lines += [
            "$",
            f"$ Wing items ({wing:.0f} lb) hang on the nearest fuselage beam node.",
            "$ Mass, CG and inertia are exact there (the offsets carry the true",
            "$ position), but the ATTACHMENT is provisional: the wing deck is a",
            "$ single half-span today, and the left/right spanwise bands arrive",
            "$ with the assembled full-span model.",
        ]
    if skipped:
        lines += ["$", "$ Payload cases NOT exported (not loadings this database can produce):"]
        for ld in skipped:
            lines.append(f"$   {ld.name} -- {ld.note}")
    lines.append("$ ----------------------------------------------------------------------")
    return lines


def conm2_fragment(project: Project, *,
                   header_comment: str = "",
                   system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """``CONM2`` + ``MASSSET`` bulk-data fragment, pasteable into any model.

    No ``GRID`` cards and no load cards: this is the mass model alone, attaching
    to nodes the receiving deck already defines. For something that runs on its
    own, see :func:`mass_check_deck`.

    ``header_comment`` is the ``$``-prefixed methods & units block
    (:func:`~sloads.report.bdf_comment_block`), applied through the same
    :func:`~sloads.export.sbeam_bridge._stamped` owner the load decks use, so a
    mass model forwarded on its own states its own basis and unit set. A blank
    value leaves the fragment byte-identical -- which is what keeps
    :func:`mass_check_deck` (which embeds this fragment) from carrying two
    stamps.
    """
    u = _checked_mass_units(deliverable_units(system, Channel.SOLVER))
    cards, loadings = mass_cards(project)
    if not cards:
        raise ValueError(
            "Project has no 'weight.items' database to export as CONM2 cards")
    out = _header(project, u, cards)
    out += ["$ ------------------------------------------------ BASELINE (always aboard)"]
    out += [_conm2_line(c, u) for c in cards if not c.overlay]
    out += ["$ ------------------------------------------------------- OVERLAY (per case)"]
    out += [_conm2_line(c, u) for c in cards if c.overlay]
    for i, loading in enumerate(loadings):
        out += ["$"] + _massset_block(cards, loading, i)
    return _stamped(header_comment, "\n".join(out) + "\n")


def mass_properties(project: Project, loading: CaseLoading,  # noqa: ARG001  -- public signature (project reserved for the LRA transfer)
                    system: UnitSystem = UnitSystem.IMPERIAL) -> Dict[str, float]:
    """``{weight/mass/cg_x/cg_z/iyy}`` of one loading, in deck units.

    The numbers a consumer checks the ``CONM2`` set against (plan 12 acceptance
    2). ``iyy`` is the airplane pitch inertia about the loading's own CG --
    parallel-axis transferred, so it is sensitive to *where* each mass sits and
    not only to how much there is, which is the point of checking a distribution
    rather than a total.
    """
    u = _checked_mass_units(deliverable_units(system, Channel.SOLVER))
    items = loading.items
    w = sum(it.weight_lb for it in items)
    if not w:
        return {"weight": 0.0, "mass": 0.0, "cg_x": 0.0, "cg_z": 0.0, "iyy": 0.0}
    cx = sum(it.weight_lb * it.x for it in items) / w
    cz = sum(it.weight_lb * it.z for it in items) / w
    iyy = sum(it.iyy + it.weight_lb * ((it.x - cx) ** 2 + (it.z - cz) ** 2)
              for it in items)
    return {
        "weight": w,
        "mass": w * u.mass.factor,
        "cg_x": to_grid(cx, 0.0, 0.0, u)[0],
        "cg_z": to_grid(0.0, 0.0, cz, u)[2],
        "iyy": iyy * u.mass_inertia.factor,
    }


# --------------------------------------------------------------------------- #
# The runnable mass-check deck (C-4) -- MASSSET + GRAV, and no load cards
# --------------------------------------------------------------------------- #
def mass_check_deck(project: Project, *,
                    header_comment: str = "",
                    system: UnitSystem = UnitSystem.IMPERIAL,
                    nz: float = 1.0) -> str:
    """A self-contained deck that accelerates the mass model and nothing else.

    One ``SUBCASE`` per derivable payload case, each selecting that case's
    ``MASSSET`` and a ``GRAV`` carrying ``nz x g`` downward. sbeam recovers the
    nodal inertia loads from its own parse of the mass model, which is the
    independent check :func:`inertia_only_cards` is compared against.

    **Scope of the check (verified 2026-08-08).** ``GRAV`` is a uniform
    *translational* acceleration field and sbeam has no ``RFORCE``, so
    rotational-acceleration inertia (pitch ``theta_ddot``, yaw ``psi_ddot``)
    cannot be recovered from a ``CONM2`` set this way. The comparison is
    therefore translational only; the rotational terms stay checked by
    sloads-side closure. Stated here and in the deck header, not left to be
    discovered.

    Carries **no** ``FORCE``/``MOMENT`` cards, by construction (C-6).
    """
    u = _checked_mass_units(deliverable_units(system, Channel.SOLVER))
    _, loadings = mass_cards(project)
    if not loadings:
        raise ValueError(
            "no payload case is derivable from this weight database -- nothing "
            "to build a mass-check deck from (see mass_distribution."
            "derive_case_loadings for why each case was rejected)")
    stations = fuselage_beam_stations(project)
    g = u.gravity                       # g in deck units -- single owner, units.py

    head: List[str] = ["SOL 101", "$"]
    for i, loading in enumerate(loadings):
        head += [
            f"SUBCASE {_MASSSET_BAND.allocate(i)}",
            f"  LABEL = {loading.name}",
            f"  TITLE = mass check, Nz={nz:g} (SF={_sf_str(1.0)}, no load cards)",
            f"  MASSSET = {_MASSSET_BAND.allocate(i)}",
            f"  LOAD = {_GRAV_BAND.allocate(i)}",
            "  SPC = 1",
            "$",
        ]
    head.append("BEGIN BULK")

    bulk: List[str] = [
        "$ ------------------------------------------------------------ NODES",
        f"$ Fuselage beam stations; y = z = 0. Lengths in {u.length.label}.",
        "$ GRID, GID, CP, X1, X2, X3",
    ]
    for i, s in enumerate(stations):
        gx, gy, gz = to_grid(s.x, 0.0, 0.0, u)
        bulk.append(f"GRID, {beam_station_gid(i)}, , {_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")
    # A massless beam joining the stations. The deck would not assemble without
    # elements, and every property here is a placeholder -- except RHO, which is
    # 0.0 and must stay so: sbeam builds a MASSSET's baseline from "CBAR
    # distributed mass + baseline CONM2s", so a beam with density would add mass
    # this deck does not know about and quietly corrupt the very comparison it
    # exists to make.
    bulk += [
        "$ --------------------------------------------------------- STRUCTURE",
        "$ Placeholder massless beam -- the deck needs elements to assemble.",
        "$ RHO = 0.0 is NOT a placeholder: a CBAR with density would add mass to",
        "$ the MASSSET baseline and corrupt the comparison.",
        f"MAT1, 1, {_fmt(1.0e7 * u.pressure.factor)}, , 0.33, 0.0",
        f"PBAR, 1, 1, {_fmt(u.length.factor ** 2)}, {_fmt(u.length.factor ** 4)}, "
        f"{_fmt(u.length.factor ** 4)}, {_fmt(u.length.factor ** 4)}",
    ]
    for i in range(len(stations) - 1):
        bulk.append(f"CBAR, {i + 1}, 1, {beam_station_gid(i)}, "
                    f"{beam_station_gid(i + 1)}, 0.0, 0.0, 1.0")
    bulk += [
        "$ ------------------------------------------------------- CONSTRAINTS",
        "$ Statically determinate: the recovered reactions ARE the residual.",
        f"SPC1, 1, 123456, {beam_station_gid(0)}",
        "$ ------------------------------------------------------ ACCELERATION",
        f"$ GRAV carries Nz x g = {nz:g} x {g:.4f} = {nz * g:.4f} "
        f"{u.length.label}/s^2, down (-z).",
        "$ Translational only: sbeam has no RFORCE, so pitch/yaw angular",
        "$ acceleration inertia is NOT recoverable from this set and stays",
        "$ checked by sloads-side closure.",
    ]
    for i, _ in enumerate(loadings):
        bulk.append(f"GRAV, {_GRAV_BAND.allocate(i)}, 0, {_fmt(nz * g)}, 0.0, 0.0, -1.0")
    bulk += ["$"] + conm2_fragment(project, system=system).splitlines()
    return _stamped(header_comment, "\n".join(head + bulk + ["ENDDATA"]) + "\n")


# --------------------------------------------------------------------------- #
# sloads' own inertia contribution, as a comparable load set (C-2 / C4)
# --------------------------------------------------------------------------- #
def case_station_weights(project: Project,
                         loading: CaseLoading) -> List[Tuple[int, float]]:
    """``[(GID, weight_lb)]`` -- one loading's mass, gathered onto its own nodes.

    The weight behind each ``CONM2`` attachment node for **this payload case**,
    in beam order. Built by walking ``loading.items`` through the very
    :func:`_attach_gid` the cards are written with, so it is the same mapping by
    construction rather than a second one kept in step by hand -- including the
    wing items, which hang on the nearest fuselage node today (see
    :func:`_attach_gid`) and are therefore part of what a ``GRAV`` field on this
    mass set accelerates.

    This is what makes the CONM2 round trip a *card-for-card* claim: the mass
    model is per case and carries the wing, while the Ch 15 beam table
    (:func:`sloads.mass_distribution.fuselage_beam_stations`) is gross and
    carries neither, so comparing sbeam's recovery against that table would be
    comparing two different airplanes.
    """
    stations = fuselage_beam_stations(project)
    order = {beam_station_gid(i): i for i in range(max(len(stations), 1))}
    totals: Dict[int, float] = {}
    for item in loading.items:
        gid, _ = _attach_gid(item, stations)
        totals[gid] = totals.get(gid, 0.0) + item.weight_lb
    return sorted(totals.items(), key=lambda pair: order.get(pair[0], 0))


def inertia_only_cards(project: Project, *,
                       header_comment: str = "",
                       system: UnitSystem = UnitSystem.IMPERIAL,
                       nz: float = 1.0,
                       sid: int = GRAV_SID_BASE,
                       loading: Optional[CaseLoading] = None) -> str:
    """sloads' inertia load per node, as ``FORCE`` cards -- for comparison.

    **Not a deliverable, and never to be applied with the total set** (C-6): the
    ``FORCE``/``MOMENT`` deck already contains this. It exists so the numbers
    sbeam recovers from the ``CONM2`` set can be compared against the numbers
    sloads computes, card for card, at the same nodes.

    Without ``loading`` the cards are the **gross** Ch 15 beam table -- every
    non-wing item, no payload case -- which is the artifact the CLI and the
    Weights page have always written and stays byte-identical.

    With a ``loading`` (a :func:`sloads.mass_distribution.derive_case_loadings`
    entry) the cards are **that payload case's** mass, node by node, including
    the wing items the ``CONM2`` set hangs on the beam. That is the set a
    ``GRAV`` field on the case's ``MASSSET`` accelerates, so it is the only form
    of these cards that can be equal to sbeam's recovery rather than merely
    similar to it (the round-trip leg, plan 12 C6).

    LIMIT, not ultimate: this is the raw ``-w x nz`` inertia, and the comparison
    is against a mass model that carries no safety factor either. Applying a
    limit-to-ultimate factor to one side and not the other is the obvious way to
    make this check pass while meaning nothing, so neither side has one.
    """
    u = _checked_mass_units(deliverable_units(system, Channel.SOLVER))
    if loading is None:
        stations = fuselage_beam_stations(project)
        if not stations:
            raise ValueError(
                "Project has no fuselage beam to write inertia loads for")
        weights = [(beam_station_gid(i), s.weight_lb)
                   for i, s in enumerate(stations)]
        basis = []          # the gross artifact's header is unchanged, byte for byte
    else:
        weights = case_station_weights(project, loading)
        if not weights:
            raise ValueError(
                f"loading '{loading.name}' carries no mass to write inertia "
                "loads for")
        basis = [
            f"$ Payload case {loading.name}: {loading.weight_lb:.0f} lb, the mass "
            "the case's",
            "$ MASSSET carries -- wing items included, on the node their CONM2",
            "$ hangs on.",
        ]
    lines = [
        "$ ============================================ SLOADS INERTIA CONTRIBUTION",
        f"$ Per-node inertia load at Nz = {nz:g}, LIMIT (no SF), in "
        f"{u.force.label}.",
    ] + basis + [
        "$ COMPARISON ARTIFACT ONLY. The FORCE/MOMENT deliverable already",
        "$ contains this; applying both counts the inertia twice.",
        f"$ Compare against what sbeam recovers from MASSSET + GRAV at Nz = {nz:g}.",
    ]
    for gid, weight_lb in weights:
        fz = -weight_lb * nz * u.force.factor
        lines.append(
            f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, 0.0, 0.0, {_fmt(fz)}")
    return _stamped(header_comment, "\n".join(lines) + "\n")


def write_conm2_fragment(project: Project, path: str, *,
                         header_comment: str = "",
                         system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(conm2_fragment(project, header_comment=header_comment,
                                system=system))


def write_mass_check_deck(project: Project, path: str, *,
                          header_comment: str = "",
                          system: UnitSystem = UnitSystem.IMPERIAL,
                          nz: float = 1.0) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(mass_check_deck(project, header_comment=header_comment,
                                 system=system, nz=nz))


__all__ = [
    "GRAV_SID_BASE",
    "MASSSET_SID_BASE",
    "MASS_EID_BALLAST",
    "MASS_EID_BASELINE",
    "MASS_EID_DISCRETIONARY",
    "MassCard",
    "case_station_weights",
    "conm2_fragment",
    "inertia_only_cards",
    "mass_cards",
    "mass_case_rows",
    "mass_check_deck",
    "mass_properties",
    "massset_identity",
    "unreferenced_overlay_eids",
    "write_conm2_fragment",
    "write_mass_check_deck",
]
