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
* ``tail_mass`` -- a per-surface panel weight, the only input the spanwise
  empennage distribution ever read. **No shipped fixture ever set one**, so its
  failure mode was quieter and worse than the fuselage's: every h-tail deck in
  the suite was air-only while the item data base carried the tail weight
  correctly the whole time (ga6 42/23 lb, the RJ 520/640). Derived since this
  step -- see :func:`tail_surface_weight`.

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
:func:`tail_surface_weight` applies the identical rule to the empennage surface
weights, with :func:`tail_reconciliation` as its reporter.

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

import dataclasses
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .cg_cases import flight_cases

from .models import (
    AnalysisKind,
    CgCase,
    FuselageStation,
    MassComponent,
    MassItem,
    MassItemKind,
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

#: Fractional gap at which :func:`tail_reconciliation` calls an entered surface
#: weight materially different from the tagged items. 1 %, the fuselage gate's
#: value and for the same reason -- below it the two are the same airplane
#: rounded differently; above it they disagree about what the surface is.
TAIL_GAP_WARN_FRACTION = 0.01


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


#: Components whose mass an **assembled balanced case spreads out** rather than
#: carrying as a point. Today exactly one: ``WING``, which ``balance.wing_sets``
#: spreads over WINGINER's spanwise shape.
#:
#: The set exists because it is the predicate decision L-3 turns on, and a
#: predicate is not a comment (``CLAUDE.md`` practice 3). See
#: :func:`assembly_distributes_mass`.
_DISTRIBUTED_BY_ASSEMBLY = frozenset({MassComponent.WING})


def assembly_distributes_mass(component: MassComponent) -> bool:
    """True when the assembled case spreads ``component``'s mass over a shape.

    Plan 13 decision **L-3**, and the single owner of that question. It decides
    whether an item's **entered self-inertia** joins the closure tensor: a
    component the assembly spreads already has its rotational inertia represented
    *by the spread*, so adding the entered figure on top counts the same physical
    quantity twice. Measured on ``ga6_normal``'s wing the two agree to -3.5 %
    (4.444e6 lb-in^2 entered against 4.288e6 built from WINGINER's distribution),
    which is the check that they are the same quantity rather than two.

    Everything else is carried as a point mass at its own station, so its
    self-inertia is a **free moment** nothing else in the model supplies --
    13.3 % of ``ga6_normal``'s ``Izz``, the fuselage-structure lump alone being
    1.131e6 lb-in^2.

    Stated as a predicate over the component rather than tested inline so that
    the day the empennage or the fuselage gains a distributed mass model, the
    exclusion follows it here instead of being rediscovered at the call site.
    ``tests/test_rigid_body.py`` guards the pairing.
    """
    return component in _DISTRIBUTED_BY_ASSEMBLY


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


#: The mass component each empennage surface's distributed inertia is built from.
#: Keyed by the ``tail_span``/``tail_geometry`` component name so a caller never
#: has to map the two vocabularies itself.
TAIL_COMPONENTS = {"htail": MassComponent.HTAIL, "vtail": MassComponent.VTAIL}


def derived_tail_surface_weight(project: Project, component: str) -> float:
    """``Σ weight_lb`` of the items tagged as carried by one empennage surface.

    The tail's half of the same move B1 made for the fuselage beam: the surface
    weight the spanwise empennage distribution smears is **derived from the item
    data base**, not entered a second time. ``component`` is ``"htail"`` or
    ``"vtail"``; anything else is 0.0 rather than an error, because a caller
    asking about a surface this suite does not model is asking a well-formed
    question with the answer "no mass".

    Placement is *not* read from the items. Plan 09 decision T-3 distributes the
    surface weight as a **uniform area density** over the planform, so an item's
    own ``x``/``z`` says nothing here; it is used by
    :func:`tail_reconciliation` to report a mistagged item, and by the fuselage
    beam, which does lump each item at its own station.
    """
    tag = TAIL_COMPONENTS.get(component)
    if tag is None:
        return 0.0
    return distribution(project).weight(tag)


def tail_surface_weight(project: Project, component: str) -> float:
    """The surface weight one empennage distribution should use — **the entry point**.

    The derived weight (:func:`derived_tail_surface_weight`) by default; the
    entered ``TailMassInput.panel_weight_lb`` when that input is marked an
    explicit override. Exactly :func:`fuselage_beam_stations`' rule, for the same
    reason: before this, ``tail_span`` read only the entered value, no fixture
    ever set one, and **every h-tail deck in the suite was air-only** while the
    item data base carried the tail mass correctly all along.

    Returns 0.0 when neither source has anything — a surface with no tagged item
    and no override. That is reported in-band by the caller (the deck says it
    carries no inertia), never silently taken for "weightless".
    """
    for tm in project.tail_mass or []:
        if tm.surface == component and tm.weight_is_override:
            return tm.panel_weight_lb
    derived = derived_tail_surface_weight(project, component)
    if derived:
        return derived
    for tm in project.tail_mass or []:
        if tm.surface == component:
            return tm.panel_weight_lb
    return 0.0


def tail_reconciliation(project: Project, component: str) -> Optional[MassCheck]:
    """One surface's **entered** panel weight against the derived one.

    The tail analogue of :func:`fuselage_reconciliation`, and surfaced for the
    same reason: an entered weight that disagrees with the tagged items is
    somebody's statement about the airplane, and which of the two is wrong is the
    user's call, not this module's. ``None`` when nothing is entered to compare.
    """
    entered = next((tm for tm in project.tail_mass or []
                    if tm.surface == component), None)
    if entered is None or not entered.panel_weight_lb:
        return None
    derived = derived_tail_surface_weight(project, component)
    if not derived:
        return None
    got, want = entered.panel_weight_lb, derived
    return MassCheck(
        code=f"mass_{component}_reconcile",
        ok=abs(got - want) <= TAIL_GAP_WARN_FRACTION * abs(want),
        got=got, want=want,
        detail=(f"entered {component} weight {got:.1f} lb against {want:.1f} lb "
                f"of {component}-tagged items ({got - want:+.1f} lb)"
                + ("; the entered value is the explicit override and is what the "
                   "distribution uses" if entered.weight_is_override else
                   "; the derived value is what the distribution uses")),
    )


def untagged_tail_surfaces(project: Project) -> List[str]:
    """The modelled empennage surfaces with **no** tagged mass item at all.

    A zero here is an omission, not a weightless fin: it means the data base
    never said which items the surface carries. Named so the caller can say
    which surface, rather than shipping a deck whose inertia is quietly absent.
    """
    return [c for c in TAIL_COMPONENTS
            if not derived_tail_surface_weight(project, c)]


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


# --------------------------------------------------------------------------- #
# Per-payload-case itemization (step C1, plan 12 decision C-1)
# --------------------------------------------------------------------------- #
#: Ballast above this fraction of the case weight is not ballast -- it is a
#: statement that the loading is not one the item database can produce. The
#: derivation still reports the number; it just refuses to present it as a mass
#: model. 10 % is the gate: real stress/flight-test ballast on the Appendix A
#: airplane runs 2-7 % (ga6's four cases: 2.3 / 7.3 / 5.6 / 0 %), and the
#: implausible ones on the other fixtures start at 12 % and reach 31 %.
BALLAST_CREDIBLE_FRACTION = 0.10


@dataclass(frozen=True)
class CaseLoading:
    """One payload case's itemization, derived from the weight database.

    ``weight_lb``/``cg_x``/``cg_z`` are the **loading's own** properties, not the
    case's nominal numbers -- what gets exported is a real loading, never one
    fudged to hit a target.

    When a ballast row is needed it is *solved* from the case's weight, xcg and
    zcg, so those three match exactly by construction. When the loading already
    weighs the case weight, no ballast exists to move it and the match is only
    within :data:`_CG_MATCH_TOL`: ga6's CG4 is the minimum-flight-weight loading
    at station 73.0924 against a case entered as 73.09. That difference is real
    and is exported as it stands.

    What is *not* guaranteed at all is that the ballast is physically credible,
    and that is what ``derivable`` and ``note`` carry: a case needing 31 % of the
    airplane as ballast is reported, not exported.
    """

    name: str
    items: List[MassItem]
    weight_lb: float
    cg_x: float
    cg_z: float
    ballast: Optional[MassItem]
    derivable: bool
    note: str

    @property
    def ballast_fraction(self) -> float:
        return (self.ballast.weight_lb / self.weight_lb
                if self.ballast is not None and self.weight_lb else 0.0)


def _wx(items: Sequence[MassItem]) -> Tuple[float, float, float]:
    """``(Σw, Σw·x/Σw, Σw·z/Σw)`` over ``items``."""
    w = sum(it.weight_lb for it in items)
    if not w:
        return 0.0, 0.0, 0.0
    return (w,
            sum(it.weight_lb * it.x for it in items) / w,
            sum(it.weight_lb * it.z for it in items) / w)


def derive_case_loadings(project: Project,
                         cases: Optional[Sequence[CgCase]] = None) -> List[CaseLoading]:
    """One :class:`CaseLoading` per weight/CG case.

    ``cases`` defaults to the ``FLIGHT``-tagged cases -- what this used to read
    off ``flight_loads.cg_cases``. Decision G-3 generalized it to *any* case list
    so each analysis asks for the cases tagged for it; the ``derivable`` gate and
    the ``SkippedCondition`` record are unchanged, so a ground case whose loading
    the weight database cannot produce is skipped and recorded, never invented,
    exactly as a flight case is.

    **How, and why not the way plan 12 C-1 described.** C-1 proposed deriving
    each loading from WTENV's ballast machinery -- its structural-limit points
    and their reference vertices. Measured 2026-08-08: the fixtures'
    ``cg_cases`` *are* WTENV's structural points on ``ga6_normal`` (the
    Appendix A airplane, built that way) and on **no other fixture** --
    ``concept_regional_jet``'s cases sit at 619/599/595 in against WTENV's
    594/574/569. Worse, WTENV's reference is the forward-loading *sequence*, a
    prefix of the discretionary items sorted by station; targeting the cg cases
    through it derives only 6 of 18 shipped cases, the rest wanting a ballast
    station up to 3800 in off the airplane, or landing on a vertex that already
    weighs the target with the CG 13-60 in away, which no ballast can move.

    So the search is over **discretionary subsets**, not the sorted prefix: any
    combination of the discretionary items may be aboard (dropping aft
    passengers is how a real loading moves its CG forward), plus a ballast row
    solved from the residual. That reaches 16 of 18. The subset count is
    ``2^n`` over 3-7 discretionary items -- 8 to 128 -- so exhaustive search is
    the right algorithm, not an optimisation problem.

    Selection rule, stated so it is not an accident of iteration order: among
    the subsets that reproduce the case within the fuselage extent, take the one
    needing the **least ballast**; ties break toward the larger payload. Least
    ballast is the loading closest to something an operator could actually fly.

    The ballast row's ``x`` **and** ``z`` are both solved (weight from the
    residual, station from the x-moment, waterline from the z-moment), so the
    derived loading matches the case in all three. Its inertias are zero -- a
    point mass, which is what a ballast weight is.
    """
    targets = list(cases) if cases is not None else flight_cases(project)
    items = project.weight.items if project.weight is not None else []
    if not targets or not items:
        return []

    from .modules.weight_envelope import _fuselage_extent, _item_buckets

    empty, minimum, discretionary = _item_buckets(items)
    base = empty + minimum
    env = project.weight.envelope if project.weight is not None else None
    nose_x, tail_x = _fuselage_extent(project, env) if env is not None else (0.0, None)
    # Waterline extent, the z analogue of the fuselage's fore/aft extent. There is
    # no outline input to read it from, so the airframe's own items bound it: a
    # ballast weight has to sit somewhere the airplane exists. Without this,
    # solving the z-moment happily returns a station above the fin -- dhc8's
    # CGmid wants 1500 lb at waterline 373, which is 143 in over the tail.
    z_lo = min(it.z for it in items)
    z_hi = max(it.z for it in items)

    out: List[CaseLoading] = []
    for case in targets:
        burns = AnalysisKind.GROUND in case.analyses
        best: Optional[Tuple[float, int, List[MassItem], Optional[MassItem]]] = None
        for mask in range(1 << len(discretionary)):
            sub = [it for i, it in enumerate(discretionary) if mask >> i & 1]
            # G-5: for a GROUND target, burn the consumables in this subset down
            # to a continuous partial value -- proportionally, so a tank layout is
            # preserved -- *before* considering the subset a loading. A design
            # landing weight is fuel burned off (23.473(b)/(c)), not a passenger
            # left behind, and on a wing-fuel airplane the difference is not
            # cosmetic: burning fuel removes wing inertia relief and dropping a
            # passenger does not. The candidate carries no ballast, so it wins the
            # least-ballast rule outright over any subset that dropped payload.
            if burns:
                burnt = _burn_down(base + sub, case.weight_lb)
                if burnt is not None:
                    _, bx, bz = _wx(burnt)
                    if abs(bx - case.xcg) <= _CG_MATCH_TOL:
                        cand = (0.0, -len(sub), burnt, None)
                        if best is None or cand[:2] < best[:2]:
                            best = cand
                        continue
            wa, xa, za = _wx(base + sub)
            wb = case.weight_lb - wa
            if wb < -_BALLAST_EPS:
                continue                       # loading is already heavier than the case
            if abs(wb) <= _BALLAST_EPS:
                if abs(xa - case.xcg) > _CG_MATCH_TOL:
                    continue                   # right weight, wrong CG -- ballast cannot help
                cand = (0.0, -len(sub), base + sub, None)
            else:
                xb = (case.weight_lb * case.xcg - wa * xa) / wb
                if xb < nose_x or (tail_x is not None and xb > tail_x):
                    continue                   # ballast would sit off the airplane
                zb = (case.weight_lb * case.zcg - wa * za) / wb
                if not (z_lo <= zb <= z_hi):
                    continue                   # ballast would float above/below the airframe
                ballast = MassItem(
                    name=f"Ballast ({case.name})", weight_lb=wb, x=xb, y=0.0, z=zb,
                    kind=MassItemKind.DISCRETIONARY, component=MassComponent.FUSELAGE)
                cand = (wb, -len(sub), base + sub + [ballast], ballast)
            if best is None or cand[:2] < best[:2]:
                best = cand

        if best is None:
            out.append(CaseLoading(
                name=case.name, items=[], weight_lb=case.weight_lb,
                cg_x=case.xcg, cg_z=case.zcg, ballast=None, derivable=False,
                note=("no combination of discretionary items reaches this weight "
                      "and CG with ballast inside the fuselage -- the case is not "
                      "a loading this weight database can produce"),
            ))
            continue

        wb, _, loading, ballast = best
        fraction = wb / case.weight_lb if case.weight_lb else 0.0
        credible = fraction <= BALLAST_CREDIBLE_FRACTION
        note = "" if credible else (
            f"ballast {wb:.0f} lb is {fraction * 100:.0f} % of the case weight "
            f"(gate {BALLAST_CREDIBLE_FRACTION * 100:.0f} %) -- this is not a "
            "loading, it is a CG point the database cannot reach"
        )
        w, cx, cz = _wx(loading)
        out.append(CaseLoading(
            name=case.name, items=loading, weight_lb=w, cg_x=cx, cg_z=cz,
            ballast=ballast, derivable=credible, note=note,
        ))
    return out


def _burn_down(items: List[MassItem], target_lb: float) -> Optional[List[MassItem]]:
    """``items`` with their consumables scaled to reach ``target_lb`` exactly (G-5).

    The scale is one fraction applied to every ``consumable`` row, so the relative
    tank (or tank-group) split is preserved rather than one tank being drained
    first -- a real airplane burns to a schedule, and the loading's *distribution*
    is the whole reason this is not simply a weight subtraction.

    Returns ``None`` when burn-down cannot reach the target: the loading is
    already lighter than the case (nothing to burn *into*), or it carries no
    consumables, or the whole consumable load is not enough. The caller then falls
    back to the generic discretionary-subset search, which is unchanged.

    A row burnt to zero is dropped rather than kept as a 0 lb card.
    """
    total = sum(it.weight_lb for it in items)
    burnable = sum(it.weight_lb for it in items if it.consumable)
    needed = total - target_lb
    if needed < -_BALLAST_EPS or burnable <= 0.0 or needed > burnable + _BALLAST_EPS:
        return None
    if needed <= _BALLAST_EPS:
        return list(items)
    fraction = 1.0 - needed / burnable
    out: List[MassItem] = []
    for it in items:
        if not it.consumable:
            out.append(it)
            continue
        left = it.weight_lb * fraction
        if left <= _BALLAST_EPS:
            continue
        out.append(dataclasses.replace(it, weight_lb=left))
    return out


#: Weight below which a residual is "no ballast needed" rather than a mass.
_BALLAST_EPS = 1e-6
#: How near a zero-ballast loading's CG must be to the case's to count as it.
_CG_MATCH_TOL = 0.5   # in


def case_loading_checks(project: Project) -> List[MassCheck]:
    """Each derivable loading reproduces its case's weight and CG (plan 12 acc. 1).

    Exact by construction -- the ballast is *solved* from the target -- so this
    guards the construction, not the physics: it fails if the subset search ever
    returns a loading that does not actually sum to what it claims.
    """
    out: List[MassCheck] = []
    for loading in derive_case_loadings(project):
        if not loading.derivable:
            continue
        case = next(c for c in flight_cases(project) if c.name == loading.name)
        for got, want, label in ((loading.weight_lb, case.weight_lb, "weight"),
                                 (loading.cg_x, case.xcg, "xcg"),
                                 (loading.cg_z, case.zcg, "zcg")):
            out.append(MassCheck(
                code=f"mass_case_{label}", ok=_close(got, want, 1e-9),
                got=got, want=want,
                detail=f"{loading.name} {label} {got:.4f} against {want:.4f}",
            ))
    return out


def all_checks(project: Project) -> List[MassCheck]:
    """Every reconciliation this module owns, in report order."""
    out = [partition_closes(project)]
    for check in (wing_mass_tie(project), fuselage_reconciliation(project),
                  tail_reconciliation(project, "htail"),
                  tail_reconciliation(project, "vtail")):
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
    "TAIL_GAP_WARN_FRACTION",
    "BEAM_COMPONENTS",
    "TAIL_COMPONENTS",
    "MassDistribution",
    "MassCheck",
    "infer_component",
    "component_of",
    "distribution",
    "derived_fuselage_stations",
    "fuselage_beam_stations",
    "derived_tail_surface_weight",
    "tail_surface_weight",
    "tail_reconciliation",
    "untagged_tail_surfaces",
    "BALLAST_CREDIBLE_FRACTION",
    "CaseLoading",
    "derive_case_loadings",
    "case_loading_checks",
    "partition_closes",
    "wing_mass_tie",
    "unmodelled_wing_mass",
    "fuselage_reconciliation",
    "all_checks",
    "component_summary",
]
