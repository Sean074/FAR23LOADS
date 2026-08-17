"""Deck-derived force/moment resultants -- the export-boundary closure gate.

Every deck this package writes makes a **claim about itself** in its ``$``
header: the wing card set "sums to root Sz", the body set "sums to 0 (vertical
equilibrium)" and has a "Terminal Myy (moment equilibrium)", the tail set "sums
to LT25 + LT50". Until this module those claims were verified -- where they were
verified at all -- against *in-memory* objects, by four separately hand-rolled
summations, force-only, Imperial-only.

This module is the single owner of the other half: re-derive Σ``FORCE`` and
Σ``MOMENT`` **from the emitted card text**, about a stated reference point, in
the deck's own units, and hand the caller a :class:`Resultant` to assert
against. Reading the text rather than the objects is the whole point -- it is
the only form that catches the failure modes living at the boundary rather than
in the physics:

* the ``%.6E`` six-significant-figure card format;
* the ``_TOL`` near-zero card suppression;
* a card routed to the wrong ``SID``;
* a ``GRID`` whose coordinate disagrees with the load that references it;
* a unit set whose ``moment.factor`` is not ``force.factor x length.factor``
  (decision D-19) -- invisible to any force-only sum.

Production module, not a test helper (though today only tests call it, per the
step's decision E-4): the sbeam round-trip harness and any later runtime deck
validator must consume this authority rather than reimplement it.

Two moment sums, and the difference matters
-------------------------------------------
:class:`Resultant` carries both:

* ``m0`` -- the applied ``MOMENT`` cards alone, about nothing in particular
  (a free vector);
* ``m``  -- the full rigid-body resultant, ``m0 + Σ (p_gid - ref) x F``.

They answer different questions, and a component asserts whichever one its deck
actually claims. In particular the wing's exported ``myy`` is a **beam torsion
about the loads reference axis**, not a rigid-body moment about a point: the
station ``x`` sweeps aft and the station ``z`` rises with dihedral, so the
transfer term ``Σ (p - ref) x F`` is of the same order as the torsion itself
(≈ -93,300 lb-in against a -91,400 lb-in root torsion on ``ga6_normal`` PHAA).
The wing deck's header says "MOMENT(My) set sums to root torsion Myy", which is
``m0.y``; asserting ``m.y`` there would be asserting a quantity nothing in the
suite computes. The wing *bending* check does use ``m.x``, which is exactly the
lift's lever arm about the root station and is what the WINGINER quadrature
independently produces.

Conventions: ``docs/10_standard/CONVENTIONS.md`` (axes, signs, units channels,
ULT/SF contract). Deck contract: ``docs/10_standard/PROGRAM_SPEC.md``
(sbeam-bridge section). Design note:
``docs/40_history/15_export_equilibrium_invariant_plan.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

Vec3 = Tuple[float, float, float]

# --------------------------------------------------------------------------- #
# Tolerance policy -- one owner, so no test invents its own (required practice 3)
# --------------------------------------------------------------------------- #
#: Relative tolerance for a **non-zero** target. Set by the ``%.6E`` card format
#: (~1e-6 relative per card) accumulated over the ~50 cards a deck emits, with
#: margin. Tightening this is a real regression signal; loosening it is a claim
#: that the deck format changed.
REL_TOL = 1e-4

#: Absolute tolerance for a **zero** target, as a fraction of the sum of the
#: ``|terms|`` entering it. A relative tolerance is meaningless against zero, and
#: a bare absolute one is either vacuous on a 27,000,000 lb-in fuselage term or
#: impossible on a 3,000 lb-in one -- so it scales with the sum's own magnitude.
#:
#: Against ``Σ|term|`` rather than ``max|term|`` because the error being bounded
#: is *accumulated* card-format truncation: ``%.6E`` carries seven significant
#: figures, so each card is good to ~5e-7 relative and a 15-card set to
#: ~5e-7 x Σ|term|. Sized off the largest single term this was too tight by
#: exactly the card count -- ``concept_regional_jet``'s body deck closed to
#: -11.5 lb-in against a 11.3 lb-in budget, which is the format, not the physics.
ZERO_REL_TOL = 1e-6

#: Floor on the zero-target tolerance, in deck units, so a genuinely tiny deck
#: does not end up with a tolerance of zero.
ZERO_ABS_TOL = 1e-3


def closes(got: float, want: float, *, scale: float = 0.0) -> bool:
    """True if ``got`` matches ``want`` at the export-boundary tolerance.

    One function for both regimes, because conflating them is the trap: against
    a non-zero ``want`` the relative term dominates and ``scale`` is
    irrelevant; against ``want == 0`` the relative term vanishes and the
    ``scale``-derived absolute term is the whole tolerance. Pass the
    :class:`Resultant`'s own ``force_scale``/``moment_scale`` as ``scale`` --
    for a moment that is ``max|f_i * lever_i|``, not ``max|f_i|``, so an SI
    (N*mm) check is not ~25x tighter than the Imperial (lb-in) one for no
    physical reason.
    """
    return math.isclose(got, want, rel_tol=REL_TOL,
                        abs_tol=ZERO_REL_TOL * abs(scale) + ZERO_ABS_TOL)


# --------------------------------------------------------------------------- #
# Free-field BDF reader (moved here from tests/helpers.py)
# --------------------------------------------------------------------------- #
def parse_cards(text: str):
    """Parse the sbeam bridge's comma free-field deck into simple structures.

    Self-contained on purpose -- the export checks must not depend on sbeam's
    own parser (see the C4 test plan), or a bug shared by writer and reader
    would cancel. Returns ``(grids, cbars, spc1, forces, moments)`` where
    ``grids`` is ``{gid: (x, y, z)}``, ``cbars`` a list of ``(eid, ga, gb)``,
    ``spc1`` a list of ``(sid, comp, [gids])`` and ``forces``/``moments`` are
    ``{sid: [(gid, scale, (n1, n2, n3))]}``.
    """
    grids: Dict[int, Vec3] = {}
    cbars: List[tuple] = []
    spc1: List[tuple] = []
    forces: Dict[int, List[tuple]] = {}
    moments: Dict[int, List[tuple]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("$"):
            continue
        f = [c.strip() for c in line.split(",")]
        kw = f[0].upper()
        if kw == "GRID":
            grids[int(f[1])] = (float(f[3]), float(f[4]), float(f[5]))
        elif kw == "CBAR":
            cbars.append((int(f[1]), int(f[3]), int(f[4])))
        elif kw == "SPC1":
            spc1.append((int(f[1]), f[2], [int(g) for g in f[3:] if g]))
        elif kw in ("FORCE", "MOMENT"):
            sid, gid, scale = int(f[1]), int(f[2]), float(f[4])
            vec = (float(f[5]), float(f[6]), float(f[7]))
            (forces if kw == "FORCE" else moments).setdefault(
                sid, []).append((gid, scale, vec))
    return grids, cbars, spc1, forces, moments


# --------------------------------------------------------------------------- #
# Geometry-free totals -- for the decks that carry no GRID cards
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CardTotals:
    """Σ``FORCE`` and Σ``MOMENT`` of one load set, ignoring geometry entirely.

    The half of the check that needs no ``GRID`` cards, for the two decks that
    have none: the bare wing ``force_moment_cards`` deck (its geometry lives in
    the stick model beside it) and the control-surface deck (whose chordwise
    ``x`` is a fraction of chord, so it has no geometry to carry -- see
    :func:`sloads.export.sbeam_bridge.control_surface_force_moment_cards`).

    Use :func:`resultant` wherever the deck *does* carry ``GRID`` cards: the
    lever arms are the half that catches a coordinate error, and a force-only
    sum is blind to a wrong ``moment.factor`` besides.
    """

    sid: int
    force: Vec3
    moment: Vec3
    force_scale: float
    moment_scale: float
    n_force: int
    n_moment: int


def _sum_cards(cards) -> Tuple[Vec3, float]:
    """``((Σn1, Σn2, Σn3), max_axis Σ|term|)`` over a parsed card list."""
    total = [0.0, 0.0, 0.0]
    magnitude = [0.0, 0.0, 0.0]
    for _, scale, vec in cards:
        for axis, n in enumerate(vec):
            total[axis] += scale * n
            magnitude[axis] += abs(scale * n)
    return (total[0], total[1], total[2]), max(magnitude)


def card_totals(deck_text: str) -> Dict[int, CardTotals]:
    """``{sid: CardTotals}`` for every load set in ``deck_text``."""
    _, _, _, forces, moments = parse_cards(deck_text)
    out: Dict[int, CardTotals] = {}
    for sid in sorted(set(forces) | set(moments)):
        f_cards, m_cards = forces.get(sid, []), moments.get(sid, [])
        force, force_scale = _sum_cards(f_cards)
        moment, moment_scale = _sum_cards(m_cards)
        out[sid] = CardTotals(sid=sid, force=force, moment=moment,
                              force_scale=force_scale, moment_scale=moment_scale,
                              n_force=len(f_cards), n_moment=len(m_cards))
    return out


# --------------------------------------------------------------------------- #
# The resultant
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Resultant:
    """Σ force and Σ moment of one parsed load set, about a stated point.

    All components are in the deck's own units and are ULTIMATE (the deck's
    cards already carry the case's limit->ultimate factor). ``m0`` is the
    applied ``MOMENT`` set alone; ``m`` adds the ``FORCE`` cards' lever arms
    about ``ref`` -- see the module docstring for why both exist.

    ``force_scale`` / ``moment_scale`` are ``max_axis Σ|term_axis|`` -- the total
    magnitude the sum is built from, for :func:`closes` to size a zero-target
    tolerance with. Summed rather than maxed because the error they bound is
    accumulated card-format truncation; see :data:`ZERO_REL_TOL`.
    """

    sid: int
    ref: Vec3
    fx: float
    fy: float
    fz: float
    m0x: float
    m0y: float
    m0z: float
    mx: float
    my: float
    mz: float
    force_scale: float
    moment_scale: float
    n_force: int
    n_moment: int


def resultant(forces, moments, grids, sid: int, ref: Vec3) -> Resultant:
    """The :class:`Resultant` of load set ``sid``, about ``ref``.

    ``forces``/``moments``/``grids`` are :func:`parse_cards` output. Every
    ``FORCE`` card's GID must have a ``GRID`` in the same deck -- a load applied
    at a node the file does not define is not moment-checkable and is a defect
    in its own right (the body and tail decks did exactly that before this
    step), so it raises rather than being skipped.
    """
    fx = fy = fz = 0.0
    m0x = m0y = m0z = 0.0
    mx = my = mz = 0.0
    # Per-axis Σ|term|; the scales below are the largest of the three.
    f_abs = [0.0, 0.0, 0.0]
    m_abs = [0.0, 0.0, 0.0]

    for _gid, scale, (n1, n2, n3) in moments.get(sid, ()):
        vx, vy, vz = scale * n1, scale * n2, scale * n3
        m0x += vx
        m0y += vy
        m0z += vz
        m_abs = [a + abs(b) for a, b in zip(m_abs, (vx, vy, vz))]

    for gid, scale, (n1, n2, n3) in forces.get(sid, ()):
        vx, vy, vz = scale * n1, scale * n2, scale * n3
        fx += vx
        fy += vy
        fz += vz
        f_abs = [a + abs(b) for a, b in zip(f_abs, (vx, vy, vz))]
        if gid not in grids:
            raise KeyError(
                f"FORCE card in SID {sid} references GID {gid}, which has no "
                "GRID card in this deck -- the load set cannot be "
                "moment-checked from its own text"
            )
        gx, gy, gz = grids[gid]
        dx, dy, dz = gx - ref[0], gy - ref[1], gz - ref[2]
        # r x F, right-handed, in the SLOADS/CID-0 identity frame.
        tx, ty, tz = dy * vz - dz * vy, dz * vx - dx * vz, dx * vy - dy * vx
        mx += tx
        my += ty
        mz += tz
        m_abs = [a + abs(b) for a, b in zip(m_abs, (tx, ty, tz))]

    return Resultant(
        sid=sid, ref=ref,
        fx=fx, fy=fy, fz=fz,
        m0x=m0x, m0y=m0y, m0z=m0z,
        mx=m0x + mx, my=m0y + my, mz=m0z + mz,
        force_scale=max(f_abs), moment_scale=max(m_abs),
        n_force=len(forces.get(sid, ())), n_moment=len(moments.get(sid, ())),
    )


# --------------------------------------------------------------------------- #
# Reference-point pickers (decision E-2: per-component, deck-derived)
# --------------------------------------------------------------------------- #
# Each component asserts exactly the claim its own header makes, so each needs
# its own reference point -- and taking it from the deck's own GRIDs keeps the
# check purely deck-derived rather than joining the file back to the objects it
# was written from. Both pickers have the ``ref_for`` signature
# :func:`deck_resultants` calls: ``(sid, grids, force_cards) -> point``.

def ref_first_loaded(sid, grids, cards) -> Vec3:  # noqa: ARG001  -- reference-point callback protocol
    """The first loaded node of the set -- the wing root station, the tail's
    leading-edge chord station."""
    if not cards:
        return (0.0, 0.0, 0.0)
    return grids[cards[0][0]]


def ref_aftmost_loaded(sid, grids, cards) -> Vec3:  # noqa: ARG001  -- reference-point callback protocol
    """The aft-most (largest ``x``) loaded node -- the fuselage beam's tail end,
    the point its terminal cumulative ``Myy`` is stated about."""
    if not cards:
        return (0.0, 0.0, 0.0)
    return max((grids[gid] for gid, _, _ in cards), key=lambda p: p[0])


def deck_resultants(deck_text: str, ref_for=ref_first_loaded) -> Dict[int, Resultant]:
    """``{sid: Resultant}`` for every load set in ``deck_text``.

    ``ref_for(sid, grids, force_cards) -> (x, y, z)`` is the caller's choice of
    reference point, so the summation itself stays component-agnostic and the
    per-component convention (E-2) lives with the component.
    """
    grids, _, _, forces, moments = parse_cards(deck_text)
    sids = sorted(set(forces) | set(moments))
    return {
        sid: resultant(forces, moments, grids, sid,
                       ref_for(sid, grids, forces.get(sid, [])))
        for sid in sids
    }
