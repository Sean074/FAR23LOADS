"""The one resolver for weight/CG cases and the two design weights (step 10 piece 2).

Decisions **G-3**, **G-3a**, **G-4** and **G-14** of
``docs/30_future/18_step10_ground_cases_plan.md`` collapsed three case lists and
six representations of MTOW into one owner each. This module *is* that owner, and
required practice 3 is why it is a module rather than a paragraph: a cross-cutting
convention gets a single-source code owner **plus a drift guard**, never a prose
rule alone.

What it replaced, and why each was a defect rather than a duplication:

* ``FlightLoadsInput.cg_cases`` -- a derived copy of ``WeightInput.cg_cases``
  since v19, kept in step by the *Flight Envelope page* rather than by the model.
  A calc-only front end (the CLI, a test) could hold two different lists.
* ``LandingInput.cg_cases`` -- the one case list that never joined the SSOT,
  entered separately and consumed **positionally** by LANDLOAD
  (``wl[19] = wcg[0]*wr``), with the order recovered by matching names against
  ``validation.LANDING_CG_NAMES`` and *falling back to entry order*. A renamed
  case silently reordered an oracle-locked reaction table.
* ``landing.gross_weight_lb`` -- fell back to ``max(landing cg_cases)``, which is
  **MLW, not MTOW**: ``WR = GW/W = 1.0``, understating cases 13-24 (braked roll,
  side, supplementary nose) by ~5 %. Every shipped fixture set the field
  explicitly, so it never bit; the fallback leaves with the field.

Every consumer reads from here and none filters for itself.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from .models import (
    GROUND_CASE_ROLE_ORDER,
    AnalysisKind,
    CgCase,
    GroundCaseRole,
    MassItemKind,
    MissingInputError,
    Project,
)

__all__ = [
    "cases_for",
    "database_total",
    "flight_cases",
    "ground_cases",
    "landing_role_cases",
    "max_landing_weight",
    "max_landing_weight_estimate",
    "max_takeoff_weight",
    "seed_landing_cases",
]


# --------------------------------------------------------------------------- #
# The case list
# --------------------------------------------------------------------------- #
def _all_cases(project: Project) -> List[CgCase]:
    return list(project.weight.cg_cases) if project.weight is not None else []


def cases_for(project: Project, kind: AnalysisKind) -> List[CgCase]:
    """The weight/CG cases tagged for ``kind``, in entry order (decision G-3).

    Entry order is the contract for ``FLIGHT`` -- it is what
    ``flight_loads.cg_cases`` carried, and the V-n case numbering is built from it
    -- so this filters and never sorts. ``GROUND``'s own ordering contract is
    :func:`landing_role_cases`, which is by *role* and not by entry.
    """
    return [c for c in _all_cases(project) if kind in c.analyses]


def flight_cases(project: Project) -> List[CgCase]:
    """The ``FLIGHT``-tagged cases -- what ``flight_loads.cg_cases`` used to be.

    Pinned per fixture by the migration guard: this set, after migration, equals
    the pre-hop ``flight_loads.cg_cases`` exactly.
    """
    return cases_for(project, AnalysisKind.FLIGHT)


def ground_cases(project: Project) -> List[CgCase]:
    """Every ``GROUND``-tagged case, roled or not.

    A ``GROUND`` case *without* a role (a ramp loading, a second fuel state) is
    assembled and distributed like any other, but is never fed to LANDLOAD -- see
    :func:`landing_role_cases`. That is what lets the tag grow while the
    oracle-locked module keeps its exact three-loading contract.
    """
    return cases_for(project, AnalysisKind.GROUND)


def landing_role_cases(project: Project) -> List[CgCase]:
    """LANDLOAD's three loadings, **in role order** (decision G-3a).

    ``[AFT_MAX_LANDING, FWD_MAX_LANDING, FWD_LIGHT]`` -- the order
    ``landing.landing_reactions`` consumes positionally, oracle-locked to
    Appendix A p230. Raises rather than reordering or padding: exactly one case
    per role is a contract, and the failure mode this replaced was silence.
    """
    roled = [c for c in ground_cases(project) if c.role is not None]
    if not roled:
        raise MissingInputError(
            "landing needs three roled GROUND weight/CG cases (aft max landing, "
            "fwd max landing, fwd light) per UG fig 18.2. Tag them on the "
            "Weight/CG page's Payload Cases tab: analyses must include GROUND and "
            "each must carry a role. Auto-derivation from Project.mass was removed "
            "(M2-8) -- the heaviest mass case cannot supply distinct fwd/aft CG "
            "stations.")
    out: List[CgCase] = []
    for role in GROUND_CASE_ROLE_ORDER:
        hit = [c for c in roled if c.role == role]
        if len(hit) != 1:
            raise ValueError(
                f"exactly one GROUND case must carry role '{role.value}'; "
                f"found {len(hit)} ({[c.name for c in hit]})")
        out.append(hit[0])
    return out


# --------------------------------------------------------------------------- #
# The two design weights (G-4, G-14)
# --------------------------------------------------------------------------- #
def _weight_slice(project: Project):
    return project.weight


def max_landing_weight(project: Project, *, required: bool = True) -> float:
    """MLW -- ``weight.max_landing_weight_lb``, the single owner (decision G-4).

    A certified airplane-level limit, not a property of a loading, which is why
    the ``AFT_MAX_LANDING`` / ``FWD_MAX_LANDING`` cases take their *weight* from
    here and enter only their CG station. There is **no fallback**: ``0`` means
    not entered and the calc refuses, the suite's standing habit. The GUI offers
    the derived estimate (:func:`max_landing_weight_estimate`) for acceptance; it
    is never written silently.
    """
    w = _weight_slice(project)
    mlw = w.max_landing_weight_lb if w is not None else 0.0
    if mlw <= 0.0 and required:
        raise MissingInputError(
            "the landing conditions need a max landing weight: set "
            "weight.max_landing_weight_lb (moved off landing at decision G-4). "
            "The Weight/CG page offers OEW + max payload + reserve fuel as a "
            "starting estimate.")
    return mlw


#: Where :func:`max_takeoff_weight` looks when the SSOT is unset, in order. These
#: are the *derived reads* of decision G-14 -- the five representations that used
#: to each be a separate opinion of MTOW and that measurement showed agree on
#: every shipped fixture. A loaded project never reaches them (the v46 migration
#: seeds the SSOT from ``speeds.weight_lb``); a directly-constructed test project
#: does, which is why they stay. ``validation`` flags any that disagrees, so the
#: chain is a compatibility path and not a second authority.
_MTOW_FALLBACKS = ("speeds.weight_lb", "weight.envelope.gross_weight",
                   "max FLIGHT case weight")


def max_takeoff_weight(project: Project, *, required: bool = True) -> float:
    """MTOW -- ``weight.max_takeoff_weight_lb``, the single owner (decision G-14).

    **A single scalar, constant between the forward and aft CG limits** -- a
    stated assumption, not an oversight. Some airplanes' maximum take-off weight
    varies with CG (the 777 among them), which is a change to the weight-CG
    envelope's *upper* boundary; the envelope is already not a rectangle, since
    ``fwd_regardless_weight`` makes the forward limit weight-dependent in the
    other direction. Filed as backlog "CG-dependent MTOW".

    Falls back through :data:`_MTOW_FALLBACKS` when the SSOT is unset, for
    directly-constructed projects only; see that constant for why.
    """
    w = _weight_slice(project)
    if w is not None and w.max_takeoff_weight_lb > 0.0:
        return w.max_takeoff_weight_lb
    if project.speeds is not None and project.speeds.weight_lb > 0.0:
        return project.speeds.weight_lb
    if w is not None and w.envelope is not None and w.envelope.gross_weight > 0.0:
        return w.envelope.gross_weight
    cases = flight_cases(project)
    if cases:
        return max(c.weight_lb for c in cases)
    if required:
        raise MissingInputError(
            "no max take-off weight: set weight.max_takeoff_weight_lb (decision "
            "G-14 made it the single owner of the design take-off weight).")
    return 0.0


def database_total(project: Project) -> float:
    """The sum of every ``weight.items`` row -- the **ceiling**, not MTOW.

    A database can hold full fuel *and* full payload at once, which no real
    loading can: measured 2026-08-14 this exceeds the entered design weight by
    964 lb on ``atr42_100`` and 1,800 lb on ``concept_regional_jet``. It is the
    top of the ordering chain ``OEW <= MLW <= MTOW <= sum(items)``.
    """
    w = _weight_slice(project)
    return math.fsum(it.weight_lb for it in w.items) if w is not None else 0.0


def max_landing_weight_estimate(project: Project) -> Optional[float]:
    """``OEW + max payload + reserve fuel`` -- G-4's **floor**, not a prediction.

    ``sum(EMPTY)`` + ``sum(MINIMUM)`` (crew + reserve fuel on every fixture) +
    ``sum(DISCRETIONARY)`` excluding consumable mission fuel (per G-5) and
    excluding solved ballast rows. Measured 2026-08-14, entered MLW sits *above*
    this on four shipped fixtures -- you land with more than reserves, which is
    normal -- and *below* it on ``concept_regional_jet`` (31,000 against 31,360),
    which therefore cannot land at MLW with full payload and reserve fuel. That
    is a real finding about that fixture and is what the floor check surfaces.

    Returns ``None`` when there is no item database to estimate from. The GUI
    offers this for acceptance; the calc never falls back to it.
    """
    w = _weight_slice(project)
    if w is None or not w.items:
        return None
    total = 0.0
    for it in w.items:
        if it.kind == MassItemKind.DISCRETIONARY and (
            it.consumable or it.name.strip().lower().startswith("ballast")
        ):
            continue
        total += it.weight_lb
    return total


def seed_landing_cases(project: Project) -> Tuple[List[CgCase], List[str]]:
    """The three roled GROUND loadings, seeded from WTENV + MLW (was M4-17c).

    The seed the Landing Loads page used to own, moved here with the editor
    (decision G-3). Every cell comes from a real source or the seed is refused --
    it is **never zero-filled**, because LANDLOAD on a zero waterline puts the CG
    on the ground line, inverts the nose-gear reaction and inflates the
    braked-roll main loads ~2.6x, silently:

    * weight -- the two max-landing rows take MLW (the SSOT, G-4); the light row
      takes the WTENV fwd-regardless weight.
    * xcg -- the aft row from ``wtenv_cg_limits``' aft-gross station; each forward
      row from ``wtenv_fwd_cg_limit_at_weight`` interpolated **at that row's own
      weight**. Appendix A p230 reads 76.12 in at the 3230 lb landing weight, not
      the 72.64 in weight-agnostic hull value.
    * zcg -- the WTONECG waterline ``project.mass.cases[0].cg_z``.

    Returns ``(cases, missing)``: an empty list and the named missing sources when
    it cannot seed. The fwd/aft station split is a seed only -- WTENV cannot
    distinguish it per loading, so the user confirms it.
    """
    from .validation import wtenv_cg_limits, wtenv_fwd_cg_limit_at_weight

    missing = []
    w_land = project.weight.max_landing_weight_lb if project.weight else 0.0
    if not w_land:
        missing.append("the max landing weight (Design weights, above)")
    env = project.weight.envelope if project.weight is not None else None
    w_light = (env.fwd_regardless_weight or 0.0) if env is not None else 0.0
    if not w_light:
        missing.append("the WTENV forward-regardless weight (Weight / CG Envelope tab)")
    limits = wtenv_cg_limits(project)
    aft_limit = limits[1] if limits is not None else None
    if limits is None:
        missing.append("the WTENV CG envelope (Weight / CG Envelope tab)")
    zbar = (project.mass.cases[0].cg_z
            if project.mass is not None and project.mass.cases else 0.0)
    if not zbar:
        missing.append("the WTONECG waterline (Weight, CG & Inertia tab -- Apply weight items)")
    if missing:
        return [], missing
    seeds = (
        (GroundCaseRole.AFT_MAX_LANDING, "aft max landing", w_land, aft_limit),
        (GroundCaseRole.FWD_MAX_LANDING, "fwd max landing", w_land,
         wtenv_fwd_cg_limit_at_weight(project, w_land)),
        (GroundCaseRole.FWD_LIGHT, "fwd light", w_light,
         wtenv_fwd_cg_limit_at_weight(project, w_light)),
    )
    if any(x is None or not x for _, _, _, x in seeds):
        return [], ["a forward CG limit at one of the seeded weights"]
    return [CgCase(name=name, weight_lb=w, xcg=x, zcg=zbar,
                   analyses={AnalysisKind.GROUND}, role=role)
            for role, name, w, x in seeds if x is not None], []
