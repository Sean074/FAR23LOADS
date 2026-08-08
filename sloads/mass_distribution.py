"""The mass single source of truth: ``weight.items`` -> per-component inertia.

Plan 11 decision **B-2**, step **B1**
(``docs/30_future/11_balanced_airframe_cases_plan.md``). Conventions:
``docs/10_standard/CONVENTIONS.md``.

Why this module exists
----------------------
The suite carried **two independent mass models that never reconciled**:

* ``weight.items`` -- the itemized data base WTONECG/WTENV sum. It closes to the
  airplane weight and CG by construction, and it is the one every mass-property
  deliverable is computed from.
* ``fuselage_mass.stations`` -- a short hand-entered lump table, the only input
  the Ch 15 fuselage beam ever read.

Nothing anywhere compared them. Measured 2026-08-08 across the shipped fixtures,
the second is short of the first by:

==========================  ==========  =======  =========  ========
fixture                     item model  entered  shortfall  of beam
==========================  ==========  =======  =========  ========
``ga6_normal``                    3070     2578        492      16 %
``cessna_210``                    3450     3020        430      12 %
``atr42_100``                    32751    25210       7541      23 %
``dhc8_dash8``                    28700    25890       2810      10 %
``concept_regional_jet``         30600     18000      12600      41 %
``concept_heavy``                 16200        0      16200     100 %
==========================  ==========  =======  =========  ========

(The item-model column is every item **not** carried by the wing -- see
:func:`fuselage_beam_stations`. Plan 11 §1.3 quoted 427 lb for ga6 because it
also removed the tail items; they belong on the beam, see "What the beam
carries" below.) ``concept_heavy`` has no station table at all, which is why it
is the one fixture with no body deck.

A 12,600 lb shortfall on a 34,800 lb airplane is not a modelling nicety: every
fuselage inertia load, shear, bending moment and exported body card was computed
from a beam carrying three fifths of the mass it should. This module makes the
itemized data base authoritative and derives the beam from it.

What the beam carries
---------------------
Everything **except** the wing. The h-tail and v-tail hang off the aft fuselage,
so their weight is reacted by the fuselage beam as a point load at their own
station -- excluding them would leave the airplane's mass unaccounted for
between the two models. The wing panel is the one component with its own
distribution (WINGINER, tapered root->tip), and it enters the fuselage beam as
the carry-through *reaction*, not as mass; applying both would double-count it
(the seam rule, plan 11 §4).

So, exactly:

    Σ(items tagged WING) + Σ(fuselage beam stations) == Σ(all items) == W

which :func:`partition_closes` asserts.

Derived by default, entered as an explicit override
---------------------------------------------------
:func:`fuselage_beam_stations` returns the derived table whenever the item data
base can produce one. ``FuselageMassInput.stations`` survives as an **explicit**
override, taken only when ``stations_are_override`` is set -- so a hand-entered
table is a deliberate act rather than a stale file silently outranking the SSOT,
and :func:`fuselage_reconciliation` surfaces the difference either way.

Component tagging
-----------------
``MassItem.component`` is explicit. Plan 11 §3.1 proposed inferring it from
``(x, y, z)``; that cannot work, because every item in every fixture sits at
``y = 0`` -- the rows are lumped airplane totals on the centreline
(``"Engines (2)"``), which carry no side information. :func:`infer_component` is
the documented fallback for an untagged (pre-B1) file: deliberately conservative,
tagging only what the geometry makes unambiguous and defaulting to
``FUSELAGE`` -- the component whose distribution is a lump table, so a
mis-inferred item lands at its own station and is at worst in the right place on
the wrong beam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .models import (
    FuselageStation,
    MassComponent,
    MassItem,
    Project,
)

#: Two stations closer than this (in) are one beam node. Sized so the itemized
#: data base's hand-entered stations (whole inches, occasionally one decimal --
#: ga6's ballast at 103.7) merge only when they are genuinely the same point.
STATION_MERGE_TOL = 0.05

#: Relative tolerance for the reconciliation checks. Wider than the export
#: gate's because these compare an itemized sum against a separately *entered*
#: quantity, where the disagreement is data entry, not float error.
RECONCILE_REL_TOL = 1e-6

#: Fractional gap at which :func:`fuselage_reconciliation` calls an entered
#: station table materially wrong. 1 % of the beam total: below it the entered
#: table is a rounding of the item model, above it the two disagree about what
#: is aboard the airplane.
FUSELAGE_GAP_WARN_FRACTION = 0.01


# --------------------------------------------------------------------------- #
# Component assignment
# --------------------------------------------------------------------------- #
def infer_component(item: MassItem, project: Project) -> MassComponent:
    """The component for an **untagged** item: always :attr:`MassComponent.FUSELAGE`.

    Not a stub — a deliberate refusal to guess, and the honest reading of what
    the data supports. An item's component is a question about *which beam
    reacts its weight*, and the only geometric signal that could answer it is
    the item's spanwise station. **Every item in every shipped fixture sits at
    ``y = 0``**: the rows are lumped airplane totals on the centreline
    (``"Engines (2)"`` is both engines of a wing-mounted twin, entered at
    ``y = 0`` because that is where their combined CG is). Station ``x`` cannot
    separate a wing-mounted engine from a fuselage-mounted one — on
    ``atr42_100`` the wing is at x = 395 and the engines at x = 370, inside the
    fuselage's own x range either way — and a name-based rule would be a
    heuristic dressed as data.

    So the fallback guarantees the **one** thing it can: that the fuselage beam
    is *complete*. Every untagged pound lands on the beam, which is where all
    but the wing belongs anyway, so an untagged file gets a fuselage that is
    right in total and in station — heavier than the truth by the wing panel,
    never lighter, and never silently mis-attributed to a surface.

    What it deliberately does **not** do is let an untagged file pass as
    tagged: :func:`wing_mass_tie` fails loudly on one (nothing is tagged
    ``WING``, so the tie reads 0 against ``2 x panel_weight_lb``), which is the
    correct signal — *tag the items*. See
    :class:`~sloads.models.enums.MassComponent`.
    """
    return MassComponent.FUSELAGE


def component_of(item: MassItem, project: Project) -> MassComponent:
    """The component carrying ``item``: its explicit tag, else the inference."""
    return item.component if item.component is not None \
        else infer_component(item, project)


# --------------------------------------------------------------------------- #
# The distribution
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MassDistribution:
    """``weight.items`` partitioned by the component that carries each item.

    ``by_component`` is the partition itself; ``inferred`` names the items whose
    component was *not* explicitly tagged, so a caller can say so rather than
    presenting a guess as data. All weights are lb and stations inches, as
    entered.
    """

    by_component: Dict[MassComponent, List[MassItem]]
    inferred: Tuple[str, ...] = ()

    @property
    def items(self) -> List[MassItem]:
        """Every item, in component order then entry order."""
        return [it for comp in MassComponent for it in self.by_component.get(comp, [])]

    def weight(self, *components: MassComponent) -> float:
        """Total weight of ``components`` (all of them when none is given)."""
        comps = components or tuple(MassComponent)
        return sum(it.weight_lb for c in comps for it in self.by_component.get(c, []))

    def moment(self, axis: str, *components: MassComponent) -> float:
        """``Σ w·axis`` over ``components``; ``axis`` is ``"x"``/``"y"``/``"z"``."""
        comps = components or tuple(MassComponent)
        return sum(it.weight_lb * getattr(it, axis)
                   for c in comps for it in self.by_component.get(c, []))

    def cg(self, axis: str, *components: MassComponent) -> float:
        """CG of ``components`` along ``axis``; 0.0 for a zero-weight set."""
        w = self.weight(*components)
        return self.moment(axis, *components) / w if w else 0.0


def distribution(project: Project) -> MassDistribution:
    """Partition ``project.weight.items`` by carrying component.

    Returns an empty distribution for a project with no weight data base -- the
    absence of a mass model is a caller's decision to handle (some fixtures have
    none), not an error to raise from the SSOT.
    """
    by: Dict[MassComponent, List[MassItem]] = {c: [] for c in MassComponent}
    inferred: List[str] = []
    items = project.weight.items if project.weight is not None else []
    for it in items:
        if it.component is None:
            inferred.append(it.name)
        by[component_of(it, project)].append(it)
    return MassDistribution(by_component=by, inferred=tuple(inferred))


# --------------------------------------------------------------------------- #
# The derived fuselage beam
# --------------------------------------------------------------------------- #
#: The components the Ch 15 fuselage beam carries as *mass* -- everything the
#: wing does not. See the module docstring: the empennage hangs off the aft
#: fuselage, so its weight is reacted by this beam; the wing enters as the
#: carry-through reaction instead, and applying it as mass too would double it.
BEAM_COMPONENTS = (MassComponent.FUSELAGE, MassComponent.HTAIL, MassComponent.VTAIL)


def derived_fuselage_stations(project: Project) -> List[FuselageStation]:
    """The Ch 15 beam station table, derived from the item data base.

    Each non-wing item lumps at its own ``x``; items within
    :data:`STATION_MERGE_TOL` of each other become one node. Nose->tail. Empty
    when the project has no item data base.

    Node count is a property of the data base, not a modelling choice: ga6 goes
    from 5 hand-entered lumps to 14 derived stations. ``body_loads``' closure is
    node-count independent (tested at 2/3/5/9/33 stations), so the finer table
    changes the distribution's fidelity, not its equilibrium.
    """
    dist = distribution(project)
    lumps: List[Tuple[float, float]] = sorted(
        ((it.x, it.weight_lb) for c in BEAM_COMPONENTS
         for it in dist.by_component.get(c, [])),
        key=lambda p: p[0],
    )
    merged: List[List[float]] = []
    for x, w in lumps:
        if merged and abs(x - merged[-1][0]) <= STATION_MERGE_TOL:
            merged[-1][1] += w
        else:
            merged.append([x, w])
    return [FuselageStation(x=x, weight_lb=w) for x, w in merged]


def fuselage_beam_stations(project: Project) -> List[FuselageStation]:
    """The station table the Ch 15 beam should integrate — **the entry point**.

    The derived table (:func:`derived_fuselage_stations`) by default; the
    entered ``fuselage_mass.stations`` when the input is marked an explicit
    override, or when the item data base cannot produce a table at all. Returns
    ``[]`` when neither source has anything, which is the caller's
    ``MissingInputError`` to raise.
    """
    fm = project.fuselage_mass
    entered = list(fm.stations) if fm is not None else []
    if fm is not None and fm.stations_are_override:
        return entered
    derived = derived_fuselage_stations(project)
    return derived if derived else entered


# --------------------------------------------------------------------------- #
# Drift guards (CLAUDE.md required practice 3: an owner *plus* a guard)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MassCheck:
    """One reconciliation result: what was compared, and by how much it differs.

    ``ok`` is the pass/fail the guard tests assert on; ``detail`` is the sentence
    a warning or a deck header states. Carrying ``got``/``want`` rather than just
    a boolean is deliberate — a mass discrepancy is a number an engineer needs to
    see, not a flag.
    """

    code: str
    ok: bool
    got: float
    want: float
    detail: str

    @property
    def gap(self) -> float:
        return self.got - self.want


def _close(got: float, want: float, rel_tol: float = RECONCILE_REL_TOL) -> bool:
    return abs(got - want) <= rel_tol * max(abs(want), 1.0)


def partition_closes(project: Project) -> MassCheck:
    """Σ(wing items) + Σ(beam stations) == Σ(all items).

    The structural guard on the partition itself: every item lands in exactly one
    component, and the derived beam loses none of them. Fails if a component is
    added to :class:`MassComponent` without a home in
    :data:`BEAM_COMPONENTS`.
    """
    dist = distribution(project)
    total = dist.weight()
    wing = dist.weight(MassComponent.WING)
    beam = sum(s.weight_lb for s in derived_fuselage_stations(project))
    return MassCheck(
        code="mass_partition",
        ok=_close(wing + beam, total),
        got=wing + beam, want=total,
        detail=(f"wing {wing:.1f} + fuselage beam {beam:.1f} = {wing + beam:.1f} lb "
                f"against {total:.1f} lb of items"),
    )


def wing_mass_tie(project: Project) -> Optional[MassCheck]:
    """Σ(items tagged WING) == 2 × (``panel_weight_lb`` + Σ ``concentrated``).

    The tie between the two models of the same physical thing: the itemized wing
    rows, and the wing mass WINGINER actually distributes. Both of WINGINER's
    terms are **per side** — the tapered panel and each concentrated item — so
    the airplane carries twice their sum, and that is what the item database must
    show if the two models describe one airplane.

    Exact on the fixtures whose data is consistent (ga6 330 = 2 × 165;
    ``concept_regional_jet`` 4200 = 2 × 2100). Where it fails it names the gap to
    the pound, and the gap has a single cause on every fixture that has one — see
    :func:`unmodelled_wing_mass`. ``None`` when there is no wing mass input.
    """
    wm = project.wing_mass
    if wm is None or not (wm.panel_weight_lb or wm.concentrated):
        return None
    got = distribution(project).weight(MassComponent.WING)
    want = 2.0 * (wm.panel_weight_lb + sum(c.weight_lb for c in wm.concentrated))
    return MassCheck(
        code="mass_wing_tie", ok=_close(got, want), got=got, want=want,
        detail=(f"items tagged wing sum to {got:.0f} lb against 2 x (panel "
                f"{wm.panel_weight_lb:.0f} + concentrated "
                f"{sum(c.weight_lb for c in wm.concentrated):.0f}) = {want:.0f} lb"),
    )


def unmodelled_wing_mass(project: Project) -> float:
    """How much of ``wing_mass.concentrated`` the item database does not show as wing.

    ``2 × Σ concentrated − (Σ WING items − 2 × panel_weight_lb)``, in lb: the part
    of the wing's concentrated mass that is carried on the **fuselage** beam in
    the item model while WINGINER also hangs it on the wing. Positive means
    double-counted across the two models; zero means they agree.

    Measured 2026-08-08 on the shipped fixtures, each gap has exactly one cause:

    * ``atr42_100`` **3800 lb** — ``concentrated`` "wing fuel" 1900 lb/side. The
      engine+nacelle half *does* reconcile exactly (``Engines (2)`` 1780 +
      ``Nacelles (2)`` 600 = 2 × 1190), so this is the fuel alone.
    * ``dhc8_dash8`` **4000 lb** — likewise, "wing fuel" 2000 lb/side
      (``Engines (2)`` 2100 + ``Nacelles (2)`` 700 = 2 × 1400 reconciles).
    * ``concept_heavy`` **1200 lb** — ``concentrated`` "fuel" 600 lb/side.

    In every case the wing-tank fuel lives inside an undivided ``"Fuel to gross"``
    row. Closing it means **splitting item rows into wing-tank and body-tank
    fractions**, which is new fixture data with no oracle behind it — so this is
    reported, never guessed at. Filed on the backlog.
    """
    wm = project.wing_mass
    if wm is None or not wm.concentrated:
        return 0.0
    accounted = (distribution(project).weight(MassComponent.WING)
                 - 2.0 * (wm.panel_weight_lb or 0.0))
    return 2.0 * sum(c.weight_lb for c in wm.concentrated) - accounted


def fuselage_reconciliation(project: Project) -> Optional[MassCheck]:
    """The **entered** station table against the derived one.

    Surfaced rather than silently discarded: an entered table that disagrees with
    the item database is a statement about the airplane that somebody made, and
    which of the two is wrong is a user's call. ``ok`` is the
    :data:`FUSELAGE_GAP_WARN_FRACTION` gate; the gap itself is the useful number.
    ``None`` when there is nothing entered to compare.
    """
    fm = project.fuselage_mass
    if fm is None or not fm.stations:
        return None
    derived = derived_fuselage_stations(project)
    if not derived:
        return None
    got = sum(s.weight_lb for s in fm.stations)
    want = sum(s.weight_lb for s in derived)
    return MassCheck(
        code="mass_fuselage_reconcile",
        ok=abs(got - want) <= FUSELAGE_GAP_WARN_FRACTION * abs(want),
        got=got, want=want,
        detail=(f"entered fuselage stations total {got:.0f} lb against "
                f"{want:.0f} lb of non-wing items ({got - want:+.0f} lb; "
                f"{len(fm.stations)} entered stations vs {len(derived)} derived)"),
    )


def all_checks(project: Project) -> List[MassCheck]:
    """Every reconciliation this module owns, in report order."""
    out = [partition_closes(project)]
    for check in (wing_mass_tie(project), fuselage_reconciliation(project)):
        if check is not None:
            out.append(check)
    return out


# --------------------------------------------------------------------------- #
# Reporting helper
# --------------------------------------------------------------------------- #
def component_summary(project: Project) -> List[Dict[str, str]]:
    """One row per component: item count, weight, and CG — for the Weights page."""
    dist = distribution(project)
    total = dist.weight()
    rows: List[Dict[str, str]] = []
    for comp in MassComponent:
        items = dist.by_component.get(comp, [])
        if not items:
            continue
        w = dist.weight(comp)
        rows.append({
            "Component": comp.value,
            "Items": str(len(items)),
            "Weight (lb)": f"{w:.1f}",
            "% of W": f"{100.0 * w / total:.1f}" if total else "",
            "X cg (in)": f"{dist.cg('x', comp):.2f}",
            "Z cg (in)": f"{dist.cg('z', comp):.2f}",
        })
    return rows


__all__ = [
    "STATION_MERGE_TOL",
    "RECONCILE_REL_TOL",
    "FUSELAGE_GAP_WARN_FRACTION",
    "BEAM_COMPONENTS",
    "MassDistribution",
    "MassCheck",
    "infer_component",
    "component_of",
    "distribution",
    "derived_fuselage_stations",
    "fuselage_beam_stations",
    "partition_closes",
    "wing_mass_tie",
    "unmodelled_wing_mass",
    "fuselage_reconciliation",
    "all_checks",
    "component_summary",
]
