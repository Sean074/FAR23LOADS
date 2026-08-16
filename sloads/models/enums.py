"""Enumerations for the project schema (split from models.py at M3-1).

Engine/rotor/weight/mass-item kinds and the empennage-arrangement TailType.
"""

from __future__ import annotations

from enum import Enum


class EngineType(str, Enum):
    RECIPROCATING = "R"
    TURBOPROP = "T"


class EngineLayout(str, Enum):
    """Where the engines sit, constrained to the layouts the suite models.

    The value's leading digit is the engine count, so ``expected_count`` reads it
    directly: one engine on the fuselage nose, or a symmetric pair / two pairs of
    wing-mounted engines. Wing layouts place engines at mirror-symmetric butt
    lines (``+y``/``-y``); the nose engine sits on the centreline (``y = 0``).
    """
    SINGLE_NOSE = "1N"
    TWIN_WING = "2W"
    QUAD_WING = "4W"

    @property
    def expected_count(self) -> int:
        return int(self.value[0])

    @property
    def is_wing_mounted(self) -> bool:
        return self.value.endswith("W")


class RotorType(str, Enum):
    COMPRESSOR = "C"
    TURBINE = "T"


class RotorDirection(str, Enum):
    CLOCKWISE = "CW"          # viewed from rear of engine looking forward
    COUNTERCLOCKWISE = "CC"


class EngineWeightType(str, Enum):
    """Engine family used by WTESTIMA's installed-weight correlation (WTESTIMA.BAS
    lines 230-290): the two-letter codes of the original program."""
    RECIP_4CYCLE = "RF"
    RECIP_2CYCLE = "RT"
    TURBOCHARGED = "TC"
    TURBOPROP = "TP"
    LIQUID_COOLED = "LC"


class MassItemKind(str, Enum):
    """Where a mass item sits in the loading hierarchy of WTONECG/WTENV.

    Mirrors the data-base partition of WTONECG.BAS (empty-weight items, then
    minimum-flight-weight items, then discretionary useful-load items).
    """
    EMPTY = "empty"                  # part of the empty weight
    MINIMUM = "minimum"              # in minimum flight weight, not empty (pilot, reserve fuel)
    DISCRETIONARY = "discretionary"  # optional useful load (passengers, fuel, baggage, ballast)


class MassComponent(str, Enum):
    """Which structural component a mass item is carried by (plan 11 B-2, step B1).

    Orthogonal to :class:`MassItemKind`: ``kind`` says *when* an item is aboard
    (empty / minimum / discretionary — the WTONECG/WTENV loading hierarchy),
    ``component`` says *where its weight is reacted* — which beam carries it, and
    therefore which distributed load set it belongs to.

    This is the partition :mod:`sloads.mass_distribution` needs to turn
    ``weight.items`` into per-component station inertia, so that the fuselage
    beam, the wing spanwise distribution and (later) the CONM2 export all read
    one mass model instead of three.

    **Why it is an explicit field and not inferred from geometry.** Plan 11 §3.1
    proposed defaulting it from ``(x, y, z)``. Measured 2026-08-08: *every* mass
    item in *every* shipped fixture has ``y = 0`` — the entries are lumped
    airplane totals on the centreline (``"Engines (2)"``, ``"Nacelles (2)"``), a
    correct convention for CG and inertia about the airplane axis, but one that
    carries no side information at all. Inference on ``(x, y, z)`` would tag the
    whole database ``FUSELAGE``. :func:`sloads.mass_distribution.infer_component`
    survives as a documented, deliberately conservative fallback for a file that
    predates the field; every shipped fixture carries explicit tags.
    """
    WING = "wing"          # outboard wing panel + anything hung on it (engine, nacelle, wing fuel)
    FUSELAGE = "fuselage"  # the Ch 15 longitudinal beam: structure, payload, systems, body fuel
    HTAIL = "htail"        # horizontal tail
    VTAIL = "vtail"        # vertical tail


class VdBasis(str, Enum):
    """Which regulatory route sets the design dive speed VD (F25-2).

    14 CFR 25.335(b) offers the two **disjunctively** ("VD must be selected so
    that VC/MC is not greater than 0.8 VD/MD, **or** so that the minimum speed
    margin ... is the greater of ..."); 23.335(b)(4) has the same structure. The
    speed-ratio floor ``VD >= 1.25*VC`` *is* the ``VC <= 0.8*VD`` ratio written
    the other way round, so the two members below are the regulation's two
    routes, not a house convention.

    ``MACH_MARGIN`` is available in the **concept category "C" only** (decision
    D-1, F25-2): withholding it from N/U/A keeps the Appendix-A-oracle-locked
    FAR 23 path provably untouched. See
    ``reference/14CFR_25_335_design_airspeeds.md`` and
    ``reference/14CFR_MC_MD_speed_margin.md``.
    """
    SPEED_RATIO = "speed_ratio"    # VD >= 1.25*VC   (25.335(b) first route; the default)
    MACH_MARGIN = "mach_margin"    # MD >= MC + margin (25.335(b)(2) / 23.335(b)(4)(iii))


class TailType(str, Enum):
    """Empennage arrangement, for the Configuration & Layout three-view.

    Drives how ``sloads.modules.configuration.tail_planform`` places the
    horizontal/vertical tail surfaces relative to each other; a layout sketch
    distinction only, not a structural classification."""
    CONVENTIONAL = "conventional"
    T_TAIL = "t_tail"
    V_TAIL = "v_tail"
    CRUCIFORM = "cruciform"


class AnalysisKind(str, Enum):
    """Which analysis a weight/CG case is run for (decision G-3).

    One user-owned case list, each case tagged with the analyses it feeds, rather
    than one hard-coded list per analysis. Deliberately a **set** on ``CgCase`` so
    kinds can be added later (taxi, towing, jacking, gust-on-ground) without
    another schema fight; an empty set is an entry error, not a state (G-3c)."""
    FLIGHT = "flight"      # the V-n envelope, the balancing tail loads, SELECT
    GROUND = "ground"      # the landing / ground-handling families (23.471-23.511)


class GroundCaseRole(str, Enum):
    """The role a ``GROUND`` case plays in LANDLOAD's three-loading contract (G-3a).

    LANDLOAD indexes its three loadings **positionally** (``wl[19] = wcg[0]*wr``)
    and is oracle-locked to Appendix A p230, so the order is a contract, not a
    convention. Before G-3a it was recovered by matching names against
    ``validation.LANDING_CG_NAMES`` with a fall back to entry order -- a renamed
    case silently reordered the reaction table. The role makes it a field.

    Any further ``GROUND``-tagged case (a ramp loading, a second fuel state)
    carries no role: it is assembled and distributed but never fed to LANDLOAD, so
    the tag is free to grow while the oracle-locked module keeps its exact three."""
    AFT_MAX_LANDING = "aft_max_landing"
    FWD_MAX_LANDING = "fwd_max_landing"
    FWD_LIGHT = "fwd_light"


#: LANDLOAD's three roles, in the order ``landing_reactions`` consumes them.
GROUND_CASE_ROLE_ORDER = (
    GroundCaseRole.AFT_MAX_LANDING,
    GroundCaseRole.FWD_MAX_LANDING,
    GroundCaseRole.FWD_LIGHT,
)


class GearCarrier(str, Enum):
    """Which structure carries a landing-gear leg's reaction (decision G-2).

    Body-carried and wing-carried gear are different **load paths**, not different
    labels: a wing-carried reaction relieves or reverses inboard wing bending and
    only reaches the fuselage through the carry-through, so applying it to the
    body beam over-loads the fuselage *and* hides a real wing sizing case. There
    is deliberately **no default** -- a project that exports ground cases without
    it raises, the same refuse-rather-than-fall-back habit
    ``control_load_mode = "discrete"`` follows without hinge geometry."""
    BODY = "body"
    WING = "wing"


__all__ = [
    "GROUND_CASE_ROLE_ORDER",
    "AnalysisKind",
    "EngineLayout",
    "EngineType",
    "EngineWeightType",
    "GearCarrier",
    "GroundCaseRole",
    "MassComponent",
    "MassItemKind",
    "RotorDirection",
    "RotorType",
    "TailType",
    "VdBasis",
]
