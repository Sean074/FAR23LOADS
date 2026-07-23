"""Result dataclasses (split from models.py at M3-1).

The uniform LoadValue/ConditionResult/ModuleResult output types and the
persisted result slices (mass, envelope, distributed loads).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..constants import ULTIMATE_FACTOR




@dataclass
class CaseRef:
    """A stable, traceable identity for one delivered structural load case (Step D1).

    ``case_id`` is ``"<component>-<seq>"`` (``"W-01"``, ``"HT-03"``, ``"VT-02"``,
    ``"F-04"``, ``"EM-01"``, ``"LG-05"``, ...) -- see ``sloads.case_ids`` for the
    six-entry component-prefix taxonomy (control surfaces fold into their host
    structural component; the surface identity lives in ``condition``, not a
    separate prefix). Minted **once**, by the module that first names the physical
    condition, and carried unchanged by every downstream stage that derives a
    result from that same case (never re-minted) -- see ``docs/30_future/
    00_backlog.md`` Step D1 for the full design, including the accepted gap where
    the wing (``select_wing`` vs. ``WingMassInput.cases``) and vertical-tail
    (``select_vtail`` vs. ``one_engine_out``) pipelines mint two independent
    sequences that share a prefix but are not the same case object.
    """
    case_id: str
    component: str          # "wing" | "htail" | "vtail" | "fuselage" | "engine_mount" | "landing_gear"
    condition: str          # human label, e.g. "PHAA", "down aileron", "sudden rudder"
    cg: str = ""
    speed_kt: Optional[float] = None
    altitude_ft: Optional[float] = None
    far_reference: str = ""


@dataclass
class LoadValue:
    """A single labelled output quantity with units (for clean rendering).

    ``units`` is the Imperial display string. ``quantity`` is an optional
    dimension hint used only to disambiguate SI conversion where the unit string
    alone is ambiguous: a bare ``"lb"`` is pounds-*force* for a load (→ N) but
    pounds-*mass* for a weight (→ kg). A weight sets ``quantity="mass"``; loads
    leave it blank and convert by unit string. See :mod:`sloads.units`.
    """
    label: str
    value: float
    units: str = ""
    quantity: str = ""


@dataclass
class ConditionResult:
    """Result of one FAR 23 load condition.

    ``safety_factor`` is the per-case factor the render/export layer multiplies the
    LIMIT load quantities by to report ULTIMATE loads (14 CFR 25.303 -> 1.5). It is
    per-case so a future 14 CFR 25.302 / Appendix K refinement can give a failure
    case a probability-interpolated factor (1.0-1.5); the calc itself always emits
    LIMIT values, so the regression oracles are unaffected.
    """
    title: str
    far_reference: str
    values: List[LoadValue] = field(default_factory=list)
    note: str = ""
    safety_factor: float = ULTIMATE_FACTOR
    case_ref: Optional[CaseRef] = None


@dataclass
class ModuleResult:
    """The output of one suite module: its name plus the conditions it produced.

    Every module's ``run(project)`` returns this uniform type so the registry,
    CLI and GUI can treat all 22 programs identically.
    """
    module: str
    conditions: List[ConditionResult] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Mass-properties results (WTONECG) -- the Project.mass slice
# --------------------------------------------------------------------------- #
@dataclass
class MassCase:
    """Weight, CG and inertia for one loading (one WTONECG result).

    The persisted form of WTONECG's per-loading output: total ``weight_lb`` at the
    CG (``cg_x``/``cg_y``/``cg_z``, in) with the moments and product of inertia
    about that CG in **lb-in^2** (the weight-database unit; convert to slug-ft^2 by
    dividing by ``constants.LBIN2_PER_SLUGFT2``). ``name`` labels the loading
    (e.g. "aft gross", "fwd gross", "min weight"); ``gear_down`` distinguishes the
    gear-up/down pair for retractable gear.
    """
    name: str
    weight_lb: float = 0.0
    cg_x: float = 0.0
    cg_y: float = 0.0
    cg_z: float = 0.0
    ixx: float = 0.0
    iyy: float = 0.0
    izz: float = 0.0
    ixz: float = 0.0
    gear_down: bool = True


@dataclass
class MassResult:
    """The persisted mass-properties slice (``Project.mass``), written by WTONECG.

    Carries the weight/CG/inertia of each structural-limit loading (up to the four
    CG cases x gear up/down). SELECT reads the inertia for the maneuver/gust
    balancing and unbalanced-load conditions; FLTLOADS/LANDLOAD read weight & CG.
    Introduced in Step C6 -- the point at which a consumer (SELECT) finally needs
    the long-deferred persisted ``Project.mass`` (see the WTONECG note in
    ``PROGRAM_SPEC.md``)."""
    cases: List[MassCase] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Flight-envelope results (FLTLOADS) -- the Project.envelope slice
# --------------------------------------------------------------------------- #
@dataclass
class VnPoint:
    """One balanced point on the flight envelope (one row of FLTLOADS V-n data).

    The balanced-flight-load output of FLTLOADS.BAS subroutine 3900 for one
    condition, configuration, CG case and altitude: equivalent airspeed, normal
    load factor, balanced angle of attack, Glauert compressibility factor, wing
    lift coefficient, the airplane-less-tail pitching moment ``M(W+F)``, the lift
    airplane-less-tail normal to the reference ``LZW``, the balancing horizontal
    tail load ``LT`` and the drag ``DX`` (lb / lb-in).
    """
    case: int
    condition: str
    config: str
    cg: str
    altitude_ft: float
    v_eas_kt: float
    nz: float
    alpha_deg: float
    g_corr: float
    cl: float
    m_wf: float
    lzw: float
    lt: float
    dx: float
    # Stamped by SELECT (case_ids.py) when this point is chosen as a governing
    # critical condition -- the same CaseRef as the CriticalCondition it produced.
    # None for the bulk of the V-n matrix (never selected).
    case_ref: Optional["CaseRef"] = None


@dataclass
class TailBalanceLoad:
    """The balancing horizontal-tail load at one V-n point (FLTLOADS, Ch 8).

    ``tail_cp_station`` is the fuselage station of the tail CP used (``XTC`` flaps
    up, ``XTF`` flaps down); ``tail_load_lb`` is the load that zeroes the pitching
    moment about the CG. SELECT (C6) later refines the CP rationally.
    """
    case: int
    condition: str
    tail_load_lb: float
    tail_cp_station: float
    flaps_down: bool


@dataclass
class CriticalCondition:
    """One governing (critical) load condition selected/computed by SELECT (Ch 9).

    SELECT scans the FLTLOADS V-n matrix (plus inertia and geometry) and, per
    component, computes the rational critical loads and names the governing point.
    ``component`` is "wing" / "htail" / "vtail" / "fuselage"; ``label`` is the FAR
    condition tag (wing PHAA/PMAA/PLAA/NMAA; h-tail balancing/maneuver/gust/
    unsymmetrical; v-tail 23.441/23.443; fuselage 23.301/23.331/23.351/23.471).
    ``case`` references the source :class:`VnPoint` in ``Project.envelope.vn`` (or
    ``None`` for a derived condition); ``far_reference`` cites the regulation.
    ``loads`` carries the governing scalar quantities (n, CL, V, tail load, shear,
    bending, ...) as labelled :class:`LoadValue`s so report/units render unchanged.

    For horizontal/vertical-tail conditions, ``lt25``/``lt50`` carry the load
    resolved at 25% MAC (angle-of-attack) and 50% MAC (camber) -- the rational
    split TAILDIST (C7) distributes chordwise. They are ``None`` for wing/fuselage
    conditions (and for tail conditions emitted before C7)."""
    component: str
    label: str
    far_reference: str = ""
    case: Optional[int] = None
    loads: List[LoadValue] = field(default_factory=list)
    lt25: Optional[float] = None
    lt50: Optional[float] = None
    case_ref: Optional[CaseRef] = None
    note: str = ""


@dataclass
class CriticalLoadSet:
    """The governing critical-load set per component (SELECT -> ``envelope.critical``).

    One :class:`CriticalCondition` per (component, FAR condition). Read by AIRLOADS/
    AIRLOAD4 (iterative -- SELECT names the conditions they evaluate), WINGINER and
    TAILDIST (the ownership table in ``PROGRAM_SPEC.md``).

    ``selected_case_ids`` (Step D5) is the engineer's opt-out subset -- the
    Critical Loads page persists the ``case_id`` of every condition the engineer
    keeps for the deliverable; an empty list means "no filter, use every computed
    condition" (the default, and the whole behavior for any project that predates
    this field or never visits the page). Structural calc modules (WINGINER,
    NETLOADS, body_loads, the sbeam bridge) deliberately keep reading
    ``conditions`` directly -- the selection never changes what the
    load-producing modules compute. It governs what the *Results Review* GUI
    page displays, and (Step D8.3) an opt-in "governing set" toggle on the
    *Export* page that filters the fuselage/tail sbeam artifacts and the case
    index -- wing and control-surface exports are unaffected (their case ids
    don't overlap this set; see ``sbeam_bridge.filter_by_selected_case_ids``).
    """
    conditions: List[CriticalCondition] = field(default_factory=list)
    selected_case_ids: List[str] = field(default_factory=list)

    def selected(self) -> List[CriticalCondition]:
        """``conditions`` filtered to ``selected_case_ids``, or all of them when
        that list is empty (no filter applied)."""
        if not self.selected_case_ids:
            return self.conditions
        ids = set(self.selected_case_ids)
        return [c for c in self.conditions if c.case_ref and c.case_ref.case_id in ids]


@dataclass
class EnvelopeResult:
    """The persisted flight-envelope slice written by FLTLOADS (read by SELECT,
    WINGINER). ``vn`` is the full balanced-condition matrix; ``tail_balance`` is
    the balancing tail load per point. ``critical`` is the per-component governing
    load set SELECT (C6) computes from that matrix."""
    vn: List[VnPoint] = field(default_factory=list)
    tail_balance: List[TailBalanceLoad] = field(default_factory=list)
    critical: Optional[CriticalLoadSet] = None


# --------------------------------------------------------------------------- #
# Wing distributed loads (WINGINER / NETLOADS) -- the Project.loads slice
# --------------------------------------------------------------------------- #
@dataclass
class WingStationLoad:
    """Distributed load at one wing station along the 25% chord (airplane axes).

    Coordinates ``x``/``y``/``z`` (in) of the quarter chord; per-strip forces
    ``fx`` (drag) and ``fz`` (lift); cumulative shears ``sx``/``sz``; bending
    ``mxx`` (about X, from lift) and ``mzz`` (about Z, from drag); ``myy`` total
    torsion about Y (lift offset + drag offset + section pitching moment). Pounds
    and inch-pounds (AIRLOADS.BAS 4700-5060 / WINGINER.BAS / NETLOADS.BAS)."""
    x: float
    y: float
    z: float
    fx: float
    fz: float
    sx: float
    sz: float
    mxx: float
    myy: float
    mzz: float


@dataclass
class WingLoadResult:
    """One condition's spanwise wing load table (root-last, mirroring the manual)."""
    case: str
    nz: float = 0.0
    nx: float = 0.0
    stations: List[WingStationLoad] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None


@dataclass
class BodyStationLoad:
    """Net load at one longitudinal fuselage station (airplane body axes).

    ``x`` fuselage station (in); per-segment applied forces ``fx`` (axial), ``fy``
    (side), ``fz`` (vertical); cumulative shears ``sx``/``sy``/``sz``; bending
    ``myy`` (about Y, from the vertical load), ``mzz`` (about Z, from the side
    load) and torsion ``mxx`` (about the body X axis). Pounds and inch-pounds
    (fuselage net distribution, Ref 1 Ch 15)."""
    x: float
    fx: float
    fy: float
    fz: float
    sx: float
    sy: float
    sz: float
    mxx: float
    myy: float
    mzz: float


@dataclass
class BodyLoadResult:
    """One condition's longitudinal fuselage net-load table (nose-to-tail)."""
    case: str
    stations: List[BodyStationLoad] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None


@dataclass
class TailChordStation:
    """One chordwise station of a tail load distribution (TAILDIST, Ref 1 Ch 10).

    ``x`` is the chord station aft of the leading edge (in); ``psi`` the net load
    intensity there (lb/in^2), the algebraic sum of the angle-of-attack ("additive")
    and camber distributions. Five stations define the piecewise-linear profile:
    leading edge, quarter chord, trailing edge and the hinge-line chord stations."""
    x: float
    psi: float


@dataclass
class TailChordResult:
    """One critical tail condition's chordwise load distribution (TAILDIST, Ch 10).

    ``component`` is "htail" / "vtail"; ``case`` the SELECT condition label; ``lt25``
    /``lt50`` the angle-of-attack (25% MAC) and camber (50% MAC) loads it resolves
    (lb); ``stations`` the five chordwise pressure points (leading-edge first).
    ``far_reference`` is copied from the source :class:`CriticalCondition` so the
    distribution keeps the governing condition's citation (23.421 balancing, 23.423
    maneuver, 23.425 gust, 23.427 unsymmetrical h-tail; 23.441/23.443 v-tail) rather
    than a single hardcoded value."""
    case: str
    component: str
    lt25: float
    lt50: float
    stations: List[TailChordStation] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None
    far_reference: str = ""


@dataclass
class ControlSurfaceStation:
    """One chordwise station of a control-surface simplified distribution (Step C8).

    ``x`` is the fractional chord aft of the leading edge (0 = LE, 1 = TE); ``psi``
    is the load intensity there (lb/in^2). The simplified FAR-style profiles use a
    few stations: aileron (constant LE->hinge, taper to 0 at TE), flap (LE->half at
    TE), tab (trapezoid, LE = 2x TE)."""
    x: float
    psi: float


@dataclass
class ControlSurfaceLoadResult:
    """One critical control-surface load + its simplified chordwise distribution.

    ``surface`` is the control surface ("aileron" / "flap" / "tab:htail" ...);
    ``case`` the FAR condition tag ("down aileron" / "up aileron" / "flap 23.345(a)"
    / "flap gust-combined" / "<surface> tab"); ``load_lb`` the critical load and
    ``v_kt`` the speed it occurs at; ``stations`` the simplified chordwise pressure
    profile (leading-edge first). Produced by AILERON / FLAPLOAD / TABLOADS (C8)."""
    surface: str
    case: str
    load_lb: float
    v_kt: float = 0.0
    stations: List[ControlSurfaceStation] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None


@dataclass
class GearReactionCase:
    """One LANDLOAD ground-condition wheel-load case (LANDLOAD.BAS output tables).

    The reaction loads for one of the 24 main-wheel / 33 nose-wheel ground cases,
    carried both with respect to the **ground line** (the "prime" P loads) and with
    respect to the **airplane datum**, plus the unbalanced moments and the inertia
    factors. ``case`` is the 1-based case number; ``description`` the FAR condition
    family; ``cg_name`` the loading. All loads in pounds; moments in inch-pounds;
    angles in degrees (Ref 1 Ch 20)."""
    case: int
    description: str
    far_reference: str
    cg_name: str
    # Ground-line ("prime") reactions
    vmp: float = 0.0    # vertical main, per wheel
    dmp: float = 0.0    # drag main
    smp: float = 0.0    # side main
    rmp: float = 0.0    # resultant main = sqrt(vmp^2 + dmp^2)
    vnp: float = 0.0    # vertical nose
    dnp: float = 0.0    # drag nose
    snp: float = 0.0    # side nose
    result: float = 0.0  # resultant nose = sqrt(vnp^2 + dnp^2)
    # Airplane-datum reactions
    vm: float = 0.0
    dm: float = 0.0
    vn: float = 0.0
    dn: float = 0.0
    # Inertia factors (ground line / airplane datum)
    nvp: float = 0.0
    ndp: float = 0.0
    ns: float = 0.0
    nv: float = 0.0
    nd: float = 0.0
    nns: float = 0.0
    # Unbalanced moments about the airplane CG (ground line)
    pitchp: float = 0.0
    rollp: float = 0.0
    yawp: float = 0.0
    case_ref: Optional[CaseRef] = None


@dataclass
class LoadsResult:
    """The persisted distributed-loads slice (``Project.loads``).

    ``wing_air`` is the AIRLOADS air-load distribution, ``wing_inertia`` the
    WINGINER inertia distribution, and ``wing_net`` their algebraic sum (NETLOADS)
    -- the headline wing structural deliverable (root shear/BM/torsion). One
    :class:`WingLoadResult` per critical condition. ``body_net`` is the fuselage
    longitudinal net-load distribution per critical condition (SELECT, C6) -- the
    body analogue of ``wing_net``. ``tail_chordwise`` is the chordwise tail-load
    distribution per critical horizontal/vertical-tail condition (TAILDIST, C7)."""
    wing_air: List[WingLoadResult] = field(default_factory=list)
    wing_inertia: List[WingLoadResult] = field(default_factory=list)
    wing_net: List[WingLoadResult] = field(default_factory=list)
    body_net: List[BodyLoadResult] = field(default_factory=list)
    tail_chordwise: List[TailChordResult] = field(default_factory=list)
    control_surface: List[ControlSurfaceLoadResult] = field(default_factory=list)


__all__ = [
    "CaseRef",
    "LoadValue",
    "ConditionResult",
    "ModuleResult",
    "MassCase",
    "MassResult",
    "VnPoint",
    "TailBalanceLoad",
    "CriticalCondition",
    "CriticalLoadSet",
    "EnvelopeResult",
    "WingStationLoad",
    "WingLoadResult",
    "BodyStationLoad",
    "BodyLoadResult",
    "TailChordStation",
    "TailChordResult",
    "ControlSurfaceStation",
    "ControlSurfaceLoadResult",
    "GearReactionCase",
    "LoadsResult",
]
