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
from typing import Dict, List, Sequence, Tuple

from ..mass_distribution import (
    CaseLoading,
    MassComponent,
    component_of,
    derive_case_loadings,
    fuselage_beam_stations,
)
from ..models import MassItem, Project
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .coordinates import SBEAM_CID, to_grid
from .sbeam_bridge import _fmt, _sf_str, beam_station_gid

# --------------------------------------------------------------------------- #
# EID bands (disjoint from every GID band; see the disjointness guard)
# --------------------------------------------------------------------------- #
#: Always-aboard items (empty + minimum weight) -- the MASSSET **baseline**.
MASS_EID_BASELINE = 9001
#: Discretionary items -- overlay-only, named by a case's ``ADD`` row.
MASS_EID_DISCRETIONARY = 9101
#: Per-case ballast -- one overlay card per derived loading.
MASS_EID_BALLAST = 9201
#: MASSSET SIDs, one per payload case.
MASSSET_SID_BASE = 9301
#: GRAV SIDs, one per payload case.
GRAV_SID_BASE = 9401

_EID_BLOCK = 100


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


def _attach_gid(item: MassItem, project: Project,
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
    carried = {id(it) for ld in loadings for it in ld.items}
    discretionary = [it for it in items
                     if it.kind == MassItemKind.DISCRETIONARY and id(it) in carried]

    cards: List[MassCard] = []
    for band, group, overlay in ((MASS_EID_BASELINE, baseline, False),
                                 (MASS_EID_DISCRETIONARY, discretionary, True)):
        if len(group) > _EID_BLOCK:
            raise ValueError(
                f"mass export: {len(group)} items exceed the {_EID_BLOCK}-EID "
                f"block at {band}")
        for i, it in enumerate(group):
            gid, offset = _attach_gid(it, project, stations)
            cards.append(MassCard(eid=band + i, gid=gid, item=it,
                                  offset=offset, overlay=overlay))
    for i, loading in enumerate(loadings):
        if loading.ballast is None:
            continue
        gid, offset = _attach_gid(loading.ballast, project, stations)
        cards.append(MassCard(eid=MASS_EID_BALLAST + i, gid=gid,
                              item=loading.ballast, offset=offset, overlay=True))
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

    Matched on object identity, not on name: two items may legitimately share a
    name (``"3rd person"`` / ``"4th person"`` differ only by station in some
    databases), and a MASSSET that named an EID twice is a parse error in sbeam
    by design.
    """
    aboard = {id(it) for it in loading.items}
    eids = [c.eid for c in cards
            if c.overlay and c.eid < MASS_EID_BALLAST and id(c.item) in aboard]
    if loading.ballast is not None:
        eids.append(MASS_EID_BALLAST + index)
    return eids


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


def _massset_block(cards: Sequence[MassCard], loading: CaseLoading,
                   index: int) -> List[str]:
    sid = MASSSET_SID_BASE + index
    eids = _overlay_eids(cards, loading, index)
    label = "".join(ch for ch in loading.name.upper() if ch.isalnum())[:8] or f"CASE{index}"
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


def _header(project: Project, u: DeliverableUnits, cards: Sequence[MassCard],
            loadings: Sequence[CaseLoading]) -> List[str]:
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
                   system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """``CONM2`` + ``MASSSET`` bulk-data fragment, pasteable into any model.

    No ``GRID`` cards and no load cards: this is the mass model alone, attaching
    to nodes the receiving deck already defines. For something that runs on its
    own, see :func:`mass_check_deck`.
    """
    u = _checked_mass_units(deliverable_units(system, Channel.SOLVER))
    cards, loadings = mass_cards(project)
    if not cards:
        raise ValueError(
            "Project has no 'weight.items' database to export as CONM2 cards")
    out = _header(project, u, cards, loadings)
    out += ["$ ------------------------------------------------ BASELINE (always aboard)"]
    out += [_conm2_line(c, u) for c in cards if not c.overlay]
    out += ["$ ------------------------------------------------------- OVERLAY (per case)"]
    out += [_conm2_line(c, u) for c in cards if c.overlay]
    for i, loading in enumerate(loadings):
        out += ["$"] + _massset_block(cards, loading, i)
    return "\n".join(out) + "\n"


def mass_properties(project: Project, loading: CaseLoading,
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
    cards, loadings = mass_cards(project)
    if not loadings:
        raise ValueError(
            "no payload case is derivable from this weight database -- nothing "
            "to build a mass-check deck from (see mass_distribution."
            "derive_case_loadings for why each case was rejected)")
    stations = fuselage_beam_stations(project)
    g = u.force.factor / (u.mass.factor * u.length.factor)   # g in deck units

    head: List[str] = ["SOL 101", "$"]
    for i, loading in enumerate(loadings):
        head += [
            f"SUBCASE {MASSSET_SID_BASE + i}",
            f"  LABEL = {loading.name}",
            f"  TITLE = mass check, Nz={nz:g} (SF={_sf_str(1.0)}, no load cards)",
            f"  MASSSET = {MASSSET_SID_BASE + i}",
            f"  LOAD = {GRAV_SID_BASE + i}",
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
        f"$ GRAV carries Nz x g = {nz:g} x {g:.4f} {u.length.label}/s^2, down (-z).",
        "$ Translational only: sbeam has no RFORCE, so pitch/yaw angular",
        "$ acceleration inertia is NOT recoverable from this set and stays",
        "$ checked by sloads-side closure.",
    ]
    for i, _ in enumerate(loadings):
        bulk.append(f"GRAV, {GRAV_SID_BASE + i}, 0, {_fmt(nz * g)}, 0.0, 0.0, -1.0")
    bulk += ["$"] + conm2_fragment(project, system=system).splitlines()
    return "\n".join(head + bulk + ["ENDDATA"]) + "\n"


# --------------------------------------------------------------------------- #
# sloads' own inertia contribution, as a comparable load set (C-2 / C4)
# --------------------------------------------------------------------------- #
def inertia_only_cards(project: Project, *,
                       system: UnitSystem = UnitSystem.IMPERIAL,
                       nz: float = 1.0,
                       sid: int = GRAV_SID_BASE) -> str:
    """sloads' inertia load per beam station, as ``FORCE`` cards -- for comparison.

    **Not a deliverable, and never to be applied with the total set** (C-6): the
    ``FORCE``/``MOMENT`` deck already contains this. It exists so the numbers
    sbeam recovers from the ``CONM2`` set can be compared against the numbers
    sloads computes, card for card, at the same nodes.

    LIMIT, not ultimate: this is the raw ``-w x nz`` inertia, and the comparison
    is against a mass model that carries no safety factor either. Applying a
    limit-to-ultimate factor to one side and not the other is the obvious way to
    make this check pass while meaning nothing, so neither side has one.
    """
    u = _checked_mass_units(deliverable_units(system, Channel.SOLVER))
    stations = fuselage_beam_stations(project)
    if not stations:
        raise ValueError("Project has no fuselage beam to write inertia loads for")
    lines = [
        "$ ============================================ SLOADS INERTIA CONTRIBUTION",
        f"$ Per-station inertia load at Nz = {nz:g}, LIMIT (no SF), in "
        f"{u.force.label}.",
        "$ COMPARISON ARTIFACT ONLY. The FORCE/MOMENT deliverable already",
        "$ contains this; applying both counts the inertia twice.",
        f"$ Compare against what sbeam recovers from MASSSET + GRAV at Nz = {nz:g}.",
    ]
    for i, s in enumerate(stations):
        fz = -s.weight_lb * nz * u.force.factor
        lines.append(
            f"FORCE, {sid}, {beam_station_gid(i)}, {SBEAM_CID}, 1.0, "
            f"0.0, 0.0, {_fmt(fz)}")
    return "\n".join(lines) + "\n"


def write_conm2_fragment(project: Project, path: str, *,
                         system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(conm2_fragment(project, system=system))


def write_mass_check_deck(project: Project, path: str, *,
                          system: UnitSystem = UnitSystem.IMPERIAL,
                          nz: float = 1.0) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(mass_check_deck(project, system=system, nz=nz))


__all__ = [
    "MASS_EID_BASELINE",
    "MASS_EID_DISCRETIONARY",
    "MASS_EID_BALLAST",
    "MASSSET_SID_BASE",
    "GRAV_SID_BASE",
    "MassCard",
    "mass_cards",
    "unreferenced_overlay_eids",
    "mass_properties",
    "conm2_fragment",
    "mass_check_deck",
    "inertia_only_cards",
    "write_conm2_fragment",
    "write_mass_check_deck",
]
