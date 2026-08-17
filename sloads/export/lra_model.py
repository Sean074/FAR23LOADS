"""The LRA beam model -- the third deliverable (step 12, note 24 R-1).

Design notes: ``docs/30_future/24_lra_beam_model_review_note.md`` (the agreed
target, decisions BM-1..BM-5) and
``docs/30_future/25_lra_model_implementation_note.md`` (the implementation
decisions LM-1..LM-7 this module encodes). Conventions:
``docs/10_standard/CONVENTIONS.md``.

The suite's other two solver artifacts make different claims. The
per-component decks are oracle-backing free-body **views**; the assembled
balanced deck is the **equilibrium proof** -- nodes at load positions, no
elements, a determinate support whose reaction is the residual. This one is a
**structural idealization**: node lines on the load reference axes, ``CBAR``
chains, rigid ties for the posts / attachments / gear / engine, and the same
balanced cases' load sets **transferred onto the model's nodes** -- so its
value is the *internal* loads a solver recovers at the named nodes (the wing
side of body, the front/rear-spar posts, the fin root, the h-tail
attachments), which neither of the other artifacts can state.

Topology (implementation note 25 §3)
------------------------------------
Free-free like the balanced deck: one node clamped in six DOF (the forward
chain node nearest the front post -- see the support comment in
:func:`build_lra_model`), and the recovered reaction IS the case residual,
~0. The members:

* the **wing**, one chain per side, **starting at the side-of-body node**
  (note 24 R-3) and running to the tip on the surface's entered LRA;
* the **split fuselage** (decision BM-2): the forward body a cantilever ending
  at the front-spar post, the aft body + empennage a cantilever starting at
  the rear-spar post, on the section-centre line ``(x, 0, z_c(x))`` (R-4).
  No element spans the carry-through region -- each mid-body load routes to
  the nearer post, which is exactly the two-sums idealization;
* a rigid **centre-box hub** tying the two SOB nodes and the two posts to the
  wing LRA centreline point. Rigid (``RBE2``), deliberately not a ``CBAR``:
  a stiffness carry-through element is step 14's (R-12);
* the **fin**, root node at the fin-root waterline, rigid to the fuselage
  node inserted at that station (R-5);
* the **h-tail**, full span; its attachment pair rigid to the fuselage node
  at the h-tail station (conventional, basis-gated per BM-3), or its
  centreline node rigid to the **fin tip** (T-tail -- and the fin deck's T7
  lumped transfer is then never applied here, plan 11 §4);
* **gear** nodes at each leg's trunnion, rigid to the parent ``carrier``
  names (BM-4's gear half, the shipped G-2 field); **engine** hub + mount
  nodes rigid to the parent ``mounted_on`` names (R-9) -- the hub thrust
  ``FORCE`` is absent until the power-effects cases ship;
* elevator/rudder **hinge/actuator** nodes where a surface runs discrete
  control mode, each rigid to an inserted parent-chain node (LM-6).

With placeholder ``PBAR``/``MAT1`` -- one identical pair per section family,
:data:`SECTION_FAMILIES`, so a sizing tool overwrites one card per family
(backlog Pri 7, step 14 descoped 2026-08-16) -- only the **determinate** paths
give honest internal loads -- the wing outboard of the SOB, the fin, the two fuselage
cantilever sums, the gear/engine links (note 24 R-12); the h-tail span between
its two rigid attachments is placeholder-stiffness-dependent and the header
says so.

Loads (LM-1/LM-7)
-----------------
Every ``BalancedLoad`` of every assembled case transfers to the nearest node
of the member its ``source`` names, carrying the exact lever-arm couple
``(p - n) x F`` -- single owner :func:`sloads.export.coordinates
.transfer_couple`. Wing strips inboard of the SOB therefore land **on** the
SOB node (R-3's collapse, by the same rule); the balanced strips sit on the
calc's 25 %-chord line, so the chordwise part of the couple *is* the torsion
transfer to the LRA. The transferred set has the identical resultant the
balanced deck's set has, which is the plan-07 acceptance gate.

Refusals (BM-3 / LM-4)
----------------------
The exporter raises, naming the missing datum, rather than building a beam on
a guess: an unset ``ref_axis_pct`` on an entered wing/tail surface (R-7c), no
resolvable side of body, no fuselage outline, no carry-through spar stations,
or an h-tail attachment on the ``ATTACH_STRIP_PAIR`` fallback. Geometry it
accepts **assumed** (section centres, spar fractions, the SOB fallback, an
outline-derived attachment) is stated in the deck header.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ..derived_geometry import carry_through, fuselage_centreline, sob_station
from ..models import BalancedCaseResult, BalancedLoad, Project
from ..models.enums import GearCarrier
from ..modules.balance import build_balanced_cases
from ..modules.net_loads import build_net_loads, loads_ref_axis_results
from ..modules.tail_span import ATTACH_STRIP_PAIR, build_tail_span, htail_attachment
from ..tail_geometry import HTAIL, VTAIL, resolve_tail_planform
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .balanced_deck import case_sids
from .bands import band
from .coordinates import SBEAM_CID, tail_station_to_airplane, to_force, to_grid, to_moment, to_pressure, transfer_couple
from .roundtrip import _orientation
from .sbeam_bridge import (
    _MAT1_E,
    _MAT1_NU,
    _PBAR_A,
    _PBAR_I,
    _PBAR_J,
    _comment,
    _fmt,
    _fmt3,
    _sf_str,
    _stamped,
    sob_gid,
    tail_control_gid,
    tail_span_gid,
    wing_nodal_loads,
)

Vec3 = Tuple[float, float, float]

_TOL = 1e-9
#: A station this close (in) to an inserted special point is *at* it.
_COINCIDENT_TOL = 1e-6

_SOB_BAND = band("lra-sob")
_WING_BAND = band("wing-stick")
_LEFT_BAND = band("lra-wing-left")
_FUSELAGE_BAND = band("lra-fuselage")
_CENTRE_BAND = band("lra-centre")
_ENGINE_BAND = band("lra-engine")
_ATTACH_BAND = band("lra-attach")
_CBAR_BAND = band("lra-cbar")
_RBE2_BAND = band("lra-rbe2")

#: The four section families of the LRA deck, in ``MID``/``PID`` order 1..4
#: (backlog Pri 7 -- step 14 descoped, 2026-08-17). Each family gets its own
#: ``MAT1``/``PBAR`` pair so a sizing tool overwrites **one card per family**;
#: the values are the same placeholder in all four (a different default per
#: family would be invented stiffness and would move the indeterminate paths
#: for no reason). The left wing shares the right's; the fwd/aft fuselage
#: chains share one. sloads takes **no** section input: section properties are
#: the sizing half's output (scope review 2026-08-16 §2.3), so the seam is the
#: deck, not the schema.
SECTION_FAMILIES: Tuple[str, ...] = ("wing", "fuselage", "htail", "vtail")


def section_id(family: str) -> int:
    """The ``MID`` == ``PID`` of ``family`` (1-based, in :data:`SECTION_FAMILIES` order)."""
    return SECTION_FAMILIES.index(family) + 1


class LraRefusal(ValueError):
    """The project lacks a datum the beam model must not guess (BM-3/LM-4)."""


@dataclass(frozen=True)
class LraNode:
    """One node of the skeleton: position, id, and its BM-5 identity tag."""
    gid: int
    pos: Vec3
    family: str = ""      # "" = untagged chain node
    side: str = ""        # R / L / C / F / A


@dataclass
class LraModel:
    """The built skeleton -- geometry and topology, no units, no loads.

    ``members`` is the LM-7 routing table: member key -> the nodes a load
    routed there may land on. ``all`` is every node (the fallback member).
    ``rbe2s`` are ``(gn, cm, [gm...], label)``; ``cbars`` are ``(ga, gb)`` in
    chain order (EIDs are assigned at emission from the ``lra-cbar`` band).
    """
    nodes: List[LraNode] = field(default_factory=list)
    cbars: List[Tuple[int, int]] = field(default_factory=list)
    #: The section family of each ``cbars`` entry, index-aligned (backlog Pri 7,
    #: descoped step 14): one of :data:`SECTION_FAMILIES`. Decides which of the
    #: four ``PBAR``/``MAT1`` pairs the element references.
    cbar_families: List[str] = field(default_factory=list)
    rbe2s: List[Tuple[int, str, List[int], str]] = field(default_factory=list)
    members: Dict[str, List[LraNode]] = field(default_factory=dict)
    support_gid: int = 0
    #: The header's honesty block: every assumed datum the model accepted.
    assumed_notes: List[str] = field(default_factory=list)

    def add_chain(self, nodes: Sequence[LraNode], family: str) -> None:
        """Register the ``CBAR`` chain through ``nodes`` under a section family."""
        if family not in SECTION_FAMILIES:
            raise ValueError(f"unknown LRA section family {family!r}")
        pairs = list(zip((n.gid for n in nodes), (n.gid for n in nodes[1:])))
        self.cbars += pairs
        self.cbar_families += [family] * len(pairs)

    def node(self, gid: int) -> LraNode:
        for n in self.nodes:
            if n.gid == gid:
                return n
        raise KeyError(gid)

    @property
    def dependent_gids(self) -> set:
        return {gm for _gn, _cm, gms, _lbl in self.rbe2s for gm in gms}


def _interp_chain(chain: List[Tuple[float, Vec3]], key: float) -> Vec3:
    """Position at coordinate ``key`` on a (coordinate, position) polyline --
    linearly interpolated between the bracketing entries, extrapolated from the
    end pair outside them (the fin root sits below the first strip midpoint)."""
    pts = sorted(chain, key=lambda cp: cp[0])
    if len(pts) == 1:
        return pts[0][1]
    if key <= pts[0][0]:
        (ka, pa), (kb, pb) = pts[0], pts[1]
    elif key >= pts[-1][0]:
        (ka, pa), (kb, pb) = pts[-2], pts[-1]
    else:
        (ka, pa), (kb, pb) = next(
            ((a, b) for a, b in zip(pts, pts[1:]) if a[0] <= key <= b[0]))
    t = 0.0 if kb == ka else (key - ka) / (kb - ka)
    return (pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1]),
            pa[2] + t * (pb[2] - pa[2]))


def _mirror(pos: Vec3) -> Vec3:
    return (pos[0], -pos[1], pos[2])


def _dist2(a: Vec3, b: Vec3) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _insert_on_chain(chain: List[LraNode], key_fn, key: float, gid: int,
                     family: str, side: str) -> Tuple[List[LraNode], LraNode]:
    """``chain`` with a node at coordinate ``key`` -- the coincident station
    re-tagged, or a new node interpolated onto the chain's own line and
    inserted in order. Returns ``(chain, the node)``."""
    for i, node in enumerate(chain):
        if abs(key_fn(node) - key) <= _COINCIDENT_TOL:
            tagged = LraNode(node.gid, node.pos, family or node.family,
                             side or node.side)
            chain[i] = tagged
            return chain, tagged
    line = [(key_fn(n), n.pos) for n in chain]
    node = LraNode(gid, _interp_chain(line, key), family, side)
    chain.append(node)
    chain.sort(key=key_fn)
    return chain, node


def build_lra_model(project: Project) -> LraModel:
    """Build the skeleton (geometry + topology; no loads, no units).

    Raises :class:`LraRefusal` on every BM-3/LM-4 missing-datum condition --
    the error names the datum, because "enter it" is the fix, never a default.
    """
    geom = project.geometry
    if geom is None:
        raise LraRefusal("the LRA beam model needs Project.geometry")
    for name in ("wing", HTAIL, VTAIL):
        surf = geom.by_name(name)
        if surf is not None and surf.ref_axis_pct is None:
            raise LraRefusal(
                f"surface {name!r} has no entered loads reference axis "
                "(ref_axis_pct) -- a beam on an unstated axis is the silently-"
                "defaulted case this exporter refuses (note 24 R-7c). Enter "
                "the axis (typically 0.40) on the Geometry page")
    if geom.by_name("wing") is None:
        raise LraRefusal("the LRA beam model needs a 'wing' geometry surface")
    sob = sob_station(project)
    if sob is None:
        raise LraRefusal(
            "no side of body resolves (no entered sob_y_in and no fuselage "
            "width) -- the wing beam starts at the SOB (note 24 R-3) and this "
            "exporter will not invent a body (BM-1)")
    centreline = fuselage_centreline(project)
    if centreline is None:
        raise LraRefusal(
            "no fuselage outline -- the fuselage LRA is the section-centre "
            "line (note 24 R-4) and there are no sections to build it from")
    ct = carry_through(project)
    if ct is None:
        raise LraRefusal(
            "no wing carry-through resolves (degenerate root chord or spar "
            "stations) -- the split-fuselage posts sit at the front/rear-spar "
            "stations (BM-2) and cannot be placed")

    model = LraModel()
    notes = model.assumed_notes
    if sob.assumed:
        notes.append(sob.note)
    if centreline.assumed:
        notes.append(centreline.note)
    if ct.assumed:
        notes.append(
            f"wing spar chord fractions ASSUMED ({ct.front_pct:.2f}/"
            f"{ct.rear_pct:.2f} of root chord) -- the posts sit at fuselage "
            f"stations {ct.x_f:.1f}/{ct.x_r:.1f} on them. Enter front/rear_"
            "spar_pct to state the joint")

    pending_body_ties: List[Tuple[float, List[int], str]] = []

    # ------------------------------------------------------------- wing chains
    net = build_net_loads(project)
    wing_results = loads_ref_axis_results(project, net.wing_net)
    base = wing_nodal_loads(wing_results[0])
    wing_line = [(nl.y, (nl.x, nl.y, nl.z)) for nl in base]
    outboard = [nl for nl in base if nl.y > sob.y + _COINCIDENT_TOL]
    if not outboard:
        raise LraRefusal(
            f"the side of body (BL {sob.y:.2f}) is outboard of the last wing "
            "station -- there is no wing beam outboard of the joint to build")
    coincident = [nl for nl in base if abs(nl.y - sob.y) <= _COINCIDENT_TOL]
    if coincident:
        sob_r = LraNode(coincident[0].gid,
                        (coincident[0].x, coincident[0].y, coincident[0].z),
                        "lra-sob", "R")
    else:
        sob_r = LraNode(sob_gid(), _interp_chain(wing_line, sob.y),
                        "lra-sob", "R")
    right = [sob_r] + [LraNode(nl.gid, (nl.x, nl.y, nl.z)) for nl in outboard]
    sob_l = LraNode(_SOB_BAND.allocate(1), _mirror(sob_r.pos), "lra-sob", "L")
    left = [sob_l] + [LraNode(_LEFT_BAND.allocate(i),
                              _mirror((nl.x, nl.y, nl.z)))
                      for i, nl in enumerate(outboard)]
    hub_c = LraNode(_CENTRE_BAND.allocate(0), _interp_chain(wing_line, 0.0),
                    "lra-centre", "C")
    model.nodes += right + left + [hub_c]
    model.add_chain(right, "wing")
    model.add_chain(left, "wing")
    model.rbe2s.append((hub_c.gid, "123456", [sob_r.gid, sob_l.gid],
                        "centre box: the two SOB nodes move with the hub -- "
                        "rigid, NOT a stiffness carry-through (step 14 / R-12)"))

    # -------------------------------------------------------------- fin chain
    try:
        spans = build_tail_span(project)
    except (ValueError, KeyError):
        spans = {}
    fin_chain: List[LraNode] = []
    fin_tip: Optional[LraNode] = None
    vt = spans.get(VTAIL) or []
    planform_v = resolve_tail_planform(project, VTAIL) if vt else None
    if vt and planform_v is not None:  # spans exist only where the planform resolved
        stations = [LraNode(tail_span_gid(VTAIL, i),
                            tail_station_to_airplane(st.x, st.y, VTAIL, st.z))
                    for i, st in enumerate(vt[0].stations)]
        root_z = planform_v.root_z
        line = [(n.pos[2], n.pos) for n in stations]
        root = LraNode(_ATTACH_BAND.allocate(0), _interp_chain(line, root_z),
                       "lra-fin-root", "C")
        fin_chain = [root, *sorted(stations, key=lambda n: n.pos[2])]
        fin_tip = fin_chain[-1]
        pending_body_ties.append((root.pos[0], [root.gid],
                                  "fin root -> fuselage (R-5)"))

    # ------------------------------------------------------------ h-tail chain
    htail_chain: List[LraNode] = []
    ht = spans.get(HTAIL) or []
    attach_x: Optional[float] = None
    planform_h = resolve_tail_planform(project, HTAIL) if ht else None
    if ht and planform_h is not None:  # spans exist only where the planform resolved
        att = htail_attachment(project, planform_h)
        if att.basis == ATTACH_STRIP_PAIR:
            raise LraRefusal(
                "the h-tail attachment resolves to the innermost-strip-pair "
                "fallback, which is not a fuselage dimension at all (BM-3) -- "
                "enter the h-tail attachment butt line (sob_y_in) or a "
                "fuselage outline")
        htail_chain = [LraNode(tail_span_gid(HTAIL, i),
                               tail_station_to_airplane(st.x, st.y, HTAIL, st.z))
                       for i, st in enumerate(ht[0].stations)]
        htail_chain.sort(key=lambda n: n.pos[1])
        if att.y == [0.0]:
            if fin_tip is None:
                raise LraRefusal(
                    "T-tail layout with no fin beam -- the h-tail's only "
                    "support is the fin-tip joint, which does not exist "
                    "without a modelled vertical tail")
            htail_chain, joint = _insert_on_chain(
                htail_chain, lambda n: n.pos[1], 0.0,
                _ATTACH_BAND.allocate(1), "lra-attach", "C")
            model.rbe2s.append((fin_tip.gid, "123456", [joint.gid],
                                "T-tail joint: h-tail centreline -> fin tip "
                                "(R-6; the fin deck's T7 lumped transfer is "
                                "NEVER applied to this model)"))
        else:
            if att.assumed:
                notes.append(att.note)
            y_att = max(att.y)
            htail_chain, att_r = _insert_on_chain(
                htail_chain, lambda n: n.pos[1], y_att,
                _ATTACH_BAND.allocate(1), "lra-attach", "R")
            htail_chain, att_l = _insert_on_chain(
                htail_chain, lambda n: n.pos[1], -y_att,
                _ATTACH_BAND.allocate(2), "lra-attach", "L")
            attach_x = planform_h.x_at(0.0, planform_h.ref_axis_pct)
            pending_body_ties.append((attach_x, [att_l.gid, att_r.gid],
                                      "h-tail attachments -> fuselage; the "
                                      "span between them is placeholder-"
                                      "stiffness-dependent (R-12)"))

    # ------------------------------------- control-surface nodes (T6 discrete)
    control_nodes: List[LraNode] = []
    for comp, chain, key_fn in (
            (HTAIL, htail_chain, lambda n: n.pos[1]),
            (VTAIL, fin_chain, lambda n: n.pos[2])):
        rs = spans.get(comp) or []
        if not rs or not rs[0].control_loads or not chain:
            continue
        for i, cp in enumerate(rs[0].control_loads):
            family = "lra-hinge" if cp.kind == "hinge" else "lra-actuator"
            side = ("C" if comp == VTAIL or abs(cp.y) <= _COINCIDENT_TOL
                    else ("R" if cp.y > 0 else "L"))
            node = LraNode(tail_control_gid(comp, i),
                           tail_station_to_airplane(cp.x, cp.y, comp, cp.z),
                           family, side)
            control_nodes.append(node)
            span_key = node.pos[1] if comp == HTAIL else node.pos[2]
            chain, parent = _insert_on_chain(  # noqa: PLW2901  -- the chain grows by the inserted node
                chain, key_fn, span_key,
                _ATTACH_BAND.allocate(3 + len(control_nodes)), "", "")
            model.rbe2s.append((parent.gid, "123456", [node.gid],
                                f"{comp} {cp.kind} node -> parent LRA (LM-6)"))
    # Chains are registered only now: a control node's parent may have been
    # inserted into them, and a chain frozen earlier would orphan it.
    for chain, family in ((fin_chain, "vtail"), (htail_chain, "htail")):
        model.nodes += chain
        model.add_chain(chain, family)
    model.nodes += control_nodes

    # ------------------------------------------------------------------- gear
    gear_nodes: List[LraNode] = []
    lg = geom.landing_gear
    if lg is not None:
        legs = [("main", lg.main_gear), ("nose", lg.nose_gear)]
        n_gear = 0
        gear_band = band("balanced-gear")
        for leg_name, leg in legs:
            ax, ay, az = leg.attach
            if not any(leg.attach):
                notes.append(
                    f"{leg_name} gear has no attach (trunnion) point entered "
                    "-- its node is omitted from this model")
                continue
            carrier = leg.carrier
            if carrier is None:
                carrier = (GearCarrier.WING if abs(ay) > sob.y
                           else GearCarrier.BODY)
                notes.append(
                    f"{leg_name} gear carrier ASSUMED {carrier.value} -- "
                    f"inferred from |attach BL {ay:.1f}| vs the side of body "
                    f"(BL {sob.y:.2f}). Enter carrier to state it (BM-4/G-2)")
            sides = ([("R", (ax, abs(ay), az)), ("L", (ax, -abs(ay), az))]
                     if abs(ay) > _COINCIDENT_TOL else [("C", (ax, 0.0, az))])
            for side, pos in sides:
                node = LraNode(gear_band.allocate(n_gear), pos,
                               "lra-gear", side)
                n_gear += 1
                gear_nodes.append(node)
                if carrier is GearCarrier.WING:
                    wing_chain = right if side != "L" else left
                    parent = min(wing_chain[1:] or wing_chain,
                                 key=lambda n: _dist2(n.pos, pos))
                    model.rbe2s.append((parent.gid, "123456", [node.gid],
                                        f"{leg_name} gear ({side}) -> wing "
                                        "LRA (carrier WING, G-2)"))
                else:
                    pending_body_ties.append(
                        (ax, [node.gid],
                         f"{leg_name} gear ({side}) -> fuselage (carrier "
                         "BODY, G-2)"))
    model.nodes += gear_nodes

    # ---------------------------------------------------------------- engines
    engine_nodes: List[LraNode] = []
    for i, eng in enumerate(project.engines or []):
        mount_pos: Tuple[float, float, float] = (eng.engine_cg[0], eng.engine_cg[1], eng.engine_cg[2])
        hub_pos: Tuple[float, float, float] = (eng.prop_cg[0], eng.prop_cg[1], eng.prop_cg[2])
        if not any(mount_pos) and not any(hub_pos):
            continue
        if not any(hub_pos):
            hub_pos = mount_pos
        mounted = eng.mounted_on
        if mounted is None:
            mounted = "wing" if abs(mount_pos[1]) > sob.y else "fuselage"
            notes.append(
                f"engine {i + 1} mounted_on ASSUMED {mounted!r} -- inferred "
                f"from |CG BL {mount_pos[1]:.1f}| vs the side of body (BL "
                f"{sob.y:.2f}). Enter mounted_on to state it (BM-4)")
        side = ("C" if abs(mount_pos[1]) <= _COINCIDENT_TOL
                else ("R" if mount_pos[1] > 0 else "L"))
        mount = LraNode(_ENGINE_BAND.allocate(2 * i), mount_pos,
                        "lra-engine-mount", side)
        hub = LraNode(_ENGINE_BAND.allocate(2 * i + 1), hub_pos,
                      "lra-engine-hub", side)
        engine_nodes += [mount, hub]
        deps = [mount.gid] + ([hub.gid] if hub.pos != mount.pos else [])
        if hub.pos == mount.pos:
            # Coincident hub and mount cannot both exist (zero-length tie adds
            # nothing); keep the mount, drop the hub node.
            engine_nodes.pop()
        if mounted == "wing":
            wing_chain = right if side != "L" else left
            parent = min(wing_chain[1:] or wing_chain,
                         key=lambda n: _dist2(n.pos, mount_pos))
            model.rbe2s.append((parent.gid, "123456", deps,
                                f"engine {i + 1} mount+hub -> wing LRA (R-9; "
                                "one RBE2, hub folded in -- sbeam refuses "
                                "chained rigid elements)"))
        else:
            pending_body_ties.append(
                (mount_pos[0], deps,
                 f"engine {i + 1} mount+hub -> fuselage (R-9)"))
    model.nodes += engine_nodes

    # -------------------------------------------------------- fuselage chains
    inserts: Dict[float, str] = {ct.x_f: "post-F", ct.x_r: "post-A"}
    for x, _gids, _label in pending_body_ties:
        if ct.x_f + _COINCIDENT_TOL < x < ct.x_r - _COINCIDENT_TOL:
            continue          # inside the carry-through: ties to the nearer post
        inserts.setdefault(x, "")
    outline = geom.fuselage
    if outline is None:  # fuselage_centreline() above has already refused in this case
        raise LraRefusal("no fuselage outline -- the fuselage LRA needs its sections")
    xs = sorted({round(s.x, 6) for s in outline.sections}
                | {round(x, 6) for x in inserts})
    fwd_xs = [x for x in xs if x < ct.x_f - _COINCIDENT_TOL] + [ct.x_f]
    aft_xs = [ct.x_r] + [x for x in xs if x > ct.x_r + _COINCIDENT_TOL]
    fus_fwd: List[LraNode] = []
    fus_aft: List[LraNode] = []
    n_fus = 0
    for chain, chain_xs in ((fus_fwd, fwd_xs), (fus_aft, aft_xs)):
        for x in chain_xs:
            family, side = "", ""
            if abs(x - ct.x_f) <= _COINCIDENT_TOL:
                family, side = "lra-post", "F"
            elif abs(x - ct.x_r) <= _COINCIDENT_TOL:
                family, side = "lra-post", "A"
            chain.append(LraNode(_FUSELAGE_BAND.allocate(n_fus),
                                 (x, 0.0, centreline.z_at(x)), family, side))
            n_fus += 1
    model.nodes += fus_fwd + fus_aft
    model.add_chain(fus_fwd, "fuselage")
    model.add_chain(fus_aft, "fuselage")
    post_f = fus_fwd[-1]
    post_a = fus_aft[0]
    model.rbe2s.append((hub_c.gid, "123456", [post_f.gid],
                        "front-spar post (BM-2): the forward-body cantilever "
                        "hangs here; its sum is the last forward element's "
                        "end force"))
    model.rbe2s.append((hub_c.gid, "123456", [post_a.gid],
                        "rear-spar post (BM-2): the aft body + empennage "
                        "cantilever hangs here"))
    fus_all = fus_fwd + fus_aft
    for x, gids, label in pending_body_ties:
        parent = min(fus_all, key=lambda n: abs(n.pos[0] - x))
        model.rbe2s.append((parent.gid, "123456", gids, label))

    # ------------------------------------------------------- support + members
    # The clamp sits on the forward-chain node NEAREST the front post (that is
    # in no RBE2 -- roundtrip._supportable's reaction-recovery rule): free-free
    # proof either way, but clamping beside the wing keeps every flexible path
    # short, and the difference is not cosmetic -- clamped at the nose the SI
    # (mm) stiffness conditions at 1.6e15, over sbeam's 1e15 singularity
    # refusal; here it is 2.8e14. Measured on atr42_100, 2026-08-16.
    dependents = model.dependent_gids
    support = next((n for n in reversed(fus_fwd) if n.gid not in dependents),
                   None)
    if support is None:
        support = next(n for n in fus_aft if n.gid not in dependents)
    model.support_gid = support.gid

    model.members = {
        "wing-R": right,
        "wing-L": left,
        "fuselage": fus_all,
        "all": list(model.nodes),
    }
    if htail_chain:
        model.members["htail"] = htail_chain
    if fin_chain:
        model.members["vtail"] = fin_chain
    if gear_nodes:
        model.members["gear"] = gear_nodes
    return model


# --------------------------------------------------------------------------- #
# Load routing (LM-7) + transfer (LM-1)
# --------------------------------------------------------------------------- #
def _member_key(load: BalancedLoad, members: Dict[str, List[LraNode]]) -> str:
    """Which member a balanced load's ``source`` routes it to.

    ``ground-lift`` is the wing spanwise shape, so it rides with the wing
    strips. Anything unrecognised -- the closure relief fields, the aileron
    couple -- goes to the nearest node in the whole skeleton: relief acts at
    each mass's own position, and nearest-node with the exact couple preserves
    the resultant wherever it lands. A member the model could not build falls
    back the same way rather than dropping the load; the invariant gate is on
    the full set.
    """
    s, side = load.source, load.side
    if s.startswith("wing-") or s == "ground-lift":
        key = {"R": "wing-R", "L": "wing-L"}.get(side, "all")
    elif s == "tail-air" or s.startswith("htail"):
        key = "htail"
    elif s.startswith("vtail"):
        key = "vtail"
    elif s.startswith("gear-"):
        key = "gear"
    elif s.startswith("body") or s == "fuselage-cm":
        key = "fuselage"
    else:
        key = "all"
    return key if members.get(key) else "all"


def transferred_case_loads(case: BalancedCaseResult, model: LraModel
                           ) -> Dict[int, Tuple[List[float], List[float]]]:
    """``{gid: (F, M)}`` -- one case's loads on the model's nodes, **LIMIT**.

    Each :class:`~sloads.models.BalancedLoad` lands on the nearest node of the
    member its source names (LM-7) with the exact lever-arm couple
    ``(p - n) x F`` (LM-1, owner
    :func:`sloads.export.coordinates.transfer_couple`), so this set's resultant
    about any point is identical to the balanced case's -- the plan-07 gate.
    The limit->ultimate factor is applied at emission, exactly as the balanced
    deck applies it.
    """
    acc: Dict[int, Tuple[List[float], List[float]]] = {}
    for load in case.loads:
        member = model.members[_member_key(load, model.members)]
        p = (load.x, load.y, load.z)
        node = min(member, key=lambda n: _dist2(n.pos, p))
        f = (load.fx, load.fy, load.fz)
        cx, cy, cz = transfer_couple(p, node.pos, f)
        force, moment = acc.setdefault(node.gid, ([0.0] * 3, [0.0] * 3))
        force[0] += load.fx
        force[1] += load.fy
        force[2] += load.fz
        moment[0] += load.mx + cx
        moment[1] += load.my + cy
        moment[2] += load.mz + cz
    return acc


# --------------------------------------------------------------------------- #
# The deck
# --------------------------------------------------------------------------- #
def _units(system: UnitSystem) -> DeliverableUnits:
    return deliverable_units(system, Channel.SOLVER)


#: The R-12 statement every LRA deck header carries -- one wording.
STIFFNESS_NOTE = (
    "placeholder PBAR/MAT1, one pair per section family (wing = MID/PID 1, "
    "fuselage 2, htail 3, vtail 4; identical values): only the DETERMINATE "
    "paths give honest internal loads -- the wing outboard of each SOB node, "
    "the fin, the two split-fuselage cantilever sums at the posts, and the "
    "rigid gear/engine links. The h-tail span between its two attachments "
    "(conventional layout) is placeholder-stiffness-dependent. sloads takes "
    "no section input: overwrite the four cards with the sizing tool's own "
    "sections to make the indeterminate paths its (backlog Pri 7, step 14 "
    "descoped)."
)


def _case_header(case: BalancedCaseResult, sid: int) -> List[str]:
    label = case.case_ref.case_id if case.case_ref else case.label
    return _comment(
        f"LRA model case {label} -- {case.label}"
        f"{('-' + case.hand) if case.hand else ''}, SID {sid}: the balanced "
        f"case's load set transferred onto the beam nodes (ULTIMATE, limit x "
        f"SF={_sf_str(case.safety_factor)}). Identical resultant to the "
        "assembled deck's set by the transfer rule (note 25 LM-1).")


def lra_model_bdf(project: Project, *,
                  header_comment: str = "",
                  system: UnitSystem = UnitSystem.IMPERIAL,
                  cases: Sequence[BalancedCaseResult] = ()) -> str:
    """The LRA beam model as one solvable SOL 101 deck.

    ``cases`` defaults to :func:`~sloads.modules.balance.build_balanced_cases`
    -- the same set, ids and factors as the assembled balanced deck, expressed
    on this model. Raises :class:`LraRefusal` when the project lacks a datum
    the skeleton must not guess (see the module docstring), and ``ValueError``
    when no case assembles -- an empty model would read as a result.
    """
    model = build_lra_model(project)
    cases = list(cases) or build_balanced_cases(project, [])
    if not cases:
        raise ValueError(
            "no balanced case could be assembled -- the LRA model carries the "
            "assembled cases' load sets and has nothing to express")
    u = _units(system)
    sids = case_sids(cases)

    head: List[str] = ["SOL 101", "$"]
    head += _comment(
        "LRA BEAM MODEL (step 12) -- a structural idealization: node lines "
        "on the load reference axes, CBAR chains, rigid posts/attachments/"
        "gear/engine ties, and the assembled balanced cases' load sets "
        "transferred onto the nodes. Its value is the INTERNAL loads at the "
        "$ SLOADS-NODE tagged nodes; the assembled balanced deck remains the "
        "equilibrium proof and the per-component decks the oracle views "
        "(note 24 R-1).")
    head += _comment(
        "grid line = LRA = the assumed elastic axis at the entered ref_axis "
        "percent chord; torsion is about it (note 24 R-7d).")
    head += _comment("Stiffness: " + STIFFNESS_NOTE)
    for note in model.assumed_notes:
        head += _comment("ASSUMED: " + note)
    head.append("$ ------------------------------------------------- CASE MAP")
    for sid, case in zip(sids, cases):
        entry = (f"SUBCASE {sid} = "
                 f"{case.case_ref.case_id if case.case_ref else '(no id)'}"
                 f" -- {case.label}{('-' + case.hand) if case.hand else ''}"
                 f" -- {case.cg} -- Nz {case.nz:g}")
        head += [f"$ {ln}" for ln in textwrap.wrap(entry, width=70,
                                                   subsequent_indent="    ")]
    head.append("$")
    for sid, case in zip(sids, cases):
        head += [
            f"SUBCASE {sid}",
            f"  LABEL = {case.case_ref.case_id if case.case_ref else case.label}",
            f"  TITLE = {case.label} on the LRA model (Nz={case.nz:g}, {case.cg})",
            "  SPC = 1",
            f"  LOAD = {sid}",
            "  DISPLACEMENT = ALL",
            "  SPCFORCE = ALL",
            "  FORCE = ALL",
            "$",
        ]
    head.append("BEGIN BULK")

    bulk: List[str] = [
        "$ ------------------------------------------------------------ NODES",
    ]
    bulk += _comment(
        "Named nodes carry a '$ SLOADS-NODE <family> <side>' tag (decision "
        "BM-5) -- the identity contract an imported model is mapped by. "
        "Sides: R/L/C, plus F/A for the front/rear-spar posts.")
    bulk.append(f"$ Lengths in {u.length.label}.")
    bulk.append("$ GRID, GID, CP, X1, X2, X3")
    for node in model.nodes:
        if node.family:
            bulk.append(f"$ SLOADS-NODE {node.family} {node.side}")
        gx, gy, gz = to_grid(*node.pos, units=u)
        bulk.append(f"GRID, {node.gid}, , {_fmt3(gx, gy, gz)}")

    e_mod = to_pressure(_MAT1_E, u)
    area = _PBAR_A * u.length.factor ** 2
    inertia = _PBAR_I * u.length.factor ** 4
    torsion_j = _PBAR_J * u.length.factor ** 4
    bulk += [
        "$ --------------------------------------------------------- MATERIAL",
        *_comment(STIFFNESS_NOTE),
        f"$ E in {u.pressure.label}; A in {u.length.label}^2; "
        f"I, J in {u.length.label}^4.",
        "$ MAT1, MID, E, G, NU, RHO   /   PBAR, PID, MID, A, I1, I2, J",
    ]
    for family in SECTION_FAMILIES:
        sid_ = section_id(family)
        bulk += [
            f"$ SLOADS-SECTION {family}",
            f"MAT1, {sid_}, {_fmt(e_mod)}, , {_MAT1_NU}, 0.0",
            f"PBAR, {sid_}, {sid_}, {_fmt(area)}, {_fmt(inertia)}, "
            f"{_fmt(inertia)}, {_fmt(torsion_j)}",
        ]
    bulk += [
        "$ --------------------------------------------------------- ELEMENTS",
        "$ CBAR, EID, PID, GA, GB, X1, X2, X3   (PID = section family)",
    ]
    positions = {n.gid: n.pos for n in model.nodes}
    for i, ((ga, gb), family) in enumerate(zip(model.cbars, model.cbar_families)):
        vx, vy, vz = _orientation(positions[ga], positions[gb])
        bulk.append(f"CBAR, {_CBAR_BAND.allocate(i)}, {section_id(family)}, "
                    f"{ga}, {gb}, {vx}, {vy}, {vz}")
    bulk.append("$ RBE2, EID, GN, CM, GM...  (rigid ties, production band)")
    for i, (gn, cm, gms, label) in enumerate(model.rbe2s):
        bulk += _comment(label)
        bulk.append(f"RBE2, {_RBE2_BAND.allocate(i)}, {gn}, {cm}, "
                    + ", ".join(str(g) for g in gms))
    bulk += [
        "$ ------------------------------------------------------- CONSTRAINTS",
        *_comment(
            "Determinate, free-free proof: one node, six DOF, on the forward "
            "fuselage chain node nearest the front post (touched by no rigid "
            "element) -- the recovered reaction IS the case residual stated "
            "by the balanced deck, ~0."),
        f"SPC1, 1, 123456, {model.support_gid}",
        "$ ------------------------------------------------------------ LOADS",
    ]
    for sid, case in zip(sids, cases):
        bulk += ["$", *_case_header(case, sid)]
        sf = case.safety_factor
        loads = transferred_case_loads(case, model)
        for gid in sorted(loads):
            force, moment = loads[gid]
            fx, fy, fz = to_force(force[0] * sf, force[1] * sf,
                                  force[2] * sf, u)
            if max(abs(v) for v in force) * sf > _TOL:
                bulk.append(f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                            f"{_fmt3(fx, fy, fz)}")
            mx, my, mz = to_moment(moment[0] * sf, moment[1] * sf,
                                   moment[2] * sf, u)
            if max(abs(v) for v in moment) * sf > _TOL:
                bulk.append(f"MOMENT, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                            f"{_fmt3(mx, my, mz)}")

    return _stamped(header_comment, "\n".join(head + bulk + ["ENDDATA"]) + "\n")


def write_lra_model_bdf(project: Project, path: str, *,
                        header_comment: str = "",
                        system: UnitSystem = UnitSystem.IMPERIAL,
                        cases: Sequence[BalancedCaseResult] = ()) -> None:
    # Rendered before the file opens: this exporter legitimately refuses (an
    # LraRefusal names the missing datum), and a failed export must leave no
    # partial artifact.
    text = lra_model_bdf(project, header_comment=header_comment, system=system,
                         cases=cases)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


__all__ = [
    "SECTION_FAMILIES",
    "STIFFNESS_NOTE",
    "LraModel",
    "LraNode",
    "LraRefusal",
    "build_lra_model",
    "lra_model_bdf",
    "section_id",
    "transferred_case_loads",
    "write_lra_model_bdf",
]
