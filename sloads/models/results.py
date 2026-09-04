"""Result dataclasses (split from models.py at M3-1).

The uniform LoadValue/ConditionResult/ModuleResult output types and the
persisted result slices (mass, envelope, distributed loads).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..constants import ULTIMATE_FACTOR
from ..rigid_body import InertiaTensor


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
    """A single output quantity: a stable ``key``, a cosmetic ``label``, a value.

    **The key/label contract (M4-9).** ``key`` is the machine identity of the
    quantity — snake_case, stable, unique within its :class:`ConditionResult`,
    and the *only* thing downstream code may match on (``report``, the sbeam
    bridge, the views, ``tests/helpers.py``). ``label`` is display text and may be
    reworded, translated or unit-annotated at will without breaking anything.

    Before M4-9 the semantics rode on the label string, so a cosmetic relabel
    silently blanked CSV columns — the lookup returned ``None`` and the renderer
    wrote an empty cell with no error. ``sloads.load_keys`` holds the canonical
    keys the load-case schema is built from; every other producer names its own.
    ``net_loads``' ``f"Root torsion Myy ({axis})"`` is the label that made the
    case: its text varies with the elastic-axis input while the quantity does not.

    ``units`` is the Imperial display string. ``quantity`` is an optional
    dimension hint used only to disambiguate SI conversion where the unit string
    alone is ambiguous: a bare ``"lb"`` is pounds-*force* for a load (→ N) but
    pounds-*mass* for a weight (→ kg). A weight sets ``quantity="mass"``; loads
    leave it blank and convert by unit string. See :mod:`sloads.units`.

    ``frame`` names the reference frame the value is stated in, for the
    quantities that have one: :mod:`sloads.frames` owns the vocabulary and the
    words, and the ground-load matrix is the reason it exists -- LANDLOAD prints
    every reaction twice, once with respect to the ground line and once with
    respect to the airplane datum, and until design note 38 GF-6/GF-7 the
    replication carried both sets and named neither. A frame is *not* a label:
    :func:`sloads.report.render.results_to_rows` reads it to keep the delivered
    CSV in the body frame alone, while the text report keeps both. Blank is the
    right answer for a sink rate or a load factor and is therefore the default.

    ``point`` names the **application point** a force is delivered to, for the
    quantities that have one: the word beside the coordinates, not a second
    location. :mod:`sloads.gear_loads` owns the vocabulary and the words
    (:data:`~sloads.gear_loads.AXLE` / :data:`~sloads.gear_loads.GROUND_CONTACT`,
    design note 39 AP-1) -- the model holds the string only, exactly as it does
    for ``frame``, because a result type that imported a load module would
    invert the package's dependency direction. It is the same argument ``frame``
    made one step further (#141): the delivered CSV carried the point
    numerically -- ``x``/``y``/``z`` per gear -- and never said which point it
    was, so a standalone consumer could not tell case 1 acts at the axle except
    by comparing coordinates back to the geometry. Blank is the right answer for
    a load factor, a sink rate or any force whose point is not a named one, and
    is therefore the default.

    ``symbol`` names the **notation symbol** the quantity is written as, for the
    quantities a document defines in a symbol table: ``"Mzz"``, not the prose
    ``label`` that carries it. It is the third instance of the same move
    ``frame`` and ``point`` made -- a word that belongs to the value, held as
    data rather than parsed back out of display text. The oracle report is why
    it exists (design note 47 OR-74): its section 3 states that every column
    heading names a symbol from the section's own notation table, and until this
    field the only way to check that was to split a heading like ``"Root chord
    bending Mzz (lb-in-ULT)"`` on its units and hope the symbol was the last
    word -- which it is not for ``"Root torsion Myy (25% chord)"``. The guard
    reads this field instead, so a heading may be reworded freely and a symbol
    that leaves the notation still fails. Blank is the right answer for a
    quantity no document gives a symbol to, and is therefore the default.

    ``key`` is declared before it so the long-standing positional calls
    ``LoadValue(label, value, units)`` keep working; producers pass both by
    keyword.
    """
    label: str
    value: float
    units: str = ""
    quantity: str = ""
    key: str = ""
    frame: str = ""
    point: str = ""
    symbol: str = ""


@dataclass
class ConditionResult:
    """Result of one FAR 23 load condition.

    ``safety_factor`` is the per-case factor the render/export layer multiplies the
    LIMIT load quantities by to report ULTIMATE loads (14 CFR 23.303 / 25.303 -> 1.5). It is
    per-case so a future 14 CFR 25.302 / Appendix K refinement can give a failure
    case a probability-interpolated factor (1.0-1.5); the calc itself always emits
    LIMIT values, so the regression oracles are unaffected.

    It is ``Optional`` because **not every condition is a load case** (#154, note
    48 OR-82). Much of what the suite publishes through this type is surface
    geometry, weights, design speeds or a dimensionless load factor, to which no
    factor of safety applies; those resolve to ``None`` and render "N/A". Three
    values, three meanings, and they are not interchangeable:

    * ``1.5`` — a LIMIT load, factored at the deliverable (14 CFR 23.303);
    * ``1.0`` — a load the regulation prescribes as **already ultimate**
      (23.367(a)(2), 23.561(b)), so no further factor is applied;
    * ``None`` — not a load case; no factor is prescribed at all.

    The factor is written by the governing table, never by a caller's default:
    :func:`sloads.safety_factors.prescribes_factor` decides which of the three a
    condition takes. The seven dedicated load carriers below keep a plain
    ``float`` — each exists only to carry loads, so ``None`` has no meaning for
    them, and that asymmetry is deliberate rather than an oversight.
    """
    title: str
    far_reference: str
    values: List[LoadValue] = field(default_factory=list)
    note: str = ""
    safety_factor: Optional[float] = ULTIMATE_FACTOR
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
    conditions (and for tail conditions emitted before C7).

    ``loads`` holds **LIMIT** values; ``safety_factor`` is the factor the render/
    export boundary multiplies them by to report ULTIMATE (see
    :class:`ConditionResult`). Every distributed-load result derived from this
    condition copies it, so the sbeam export scales by the owning case's factor
    rather than a flat suite-wide constant.

    **Vertical-tail conditions publish their sideslip** (L-7, decisions L-7.6 /
    L-7.11): ``beta_deg`` is the case's sideslip angle in the SC-1 sense
    (``+beta`` = wind from starboard; the maneuver conditions' entered ``-19.5`` /
    ``-15`` are ``+19.5`` / ``+15``, ``SUDDEN RUDDER`` is ``0``, and ``SIDE GUST``
    is the effective ``-Kgt*Ude/V`` of the gust that produced its ``+fy`` load),
    and ``cy_beta_fin`` / ``cn_beta_fin`` are the fin's own derivatives **per
    degree, suite sign, about the wing 25 %-MAC station ``xw``**, built from the
    same ``AVT``, ``S_v`` and arm that made the load -- so ``balance`` reads the
    body and fin derivatives from their owners and re-derives neither.
    ``None`` on other components and on a persisted set that predates them.

    **Every tail condition publishes the aero state that made its load**
    (note 35, AS-1/AS-2): ``alpha_tail_deg`` is the h-tail AT (CONVENTIONS
    §1.1, ``AT = alpha_wl + IT - E``, +AT up tail load) or the fin angle of
    attack the method fed its lift slope (the yaw cases' entered ``-19.5`` /
    ``-15``: opposite sign to ``beta_deg``); ``delta_deg`` the elevator
    (TE-down +) or rudder (SC-2, TE-port +) deflection the method used --
    balancing's moment-balance value, the unchecked full throw, the trim value
    on the gust cases; ``q_psf`` the dynamic pressure at the governing point.
    The published state is the state the method actually used, never a derived
    "total effective" one -- a quantity a method never defines stays ``None``
    with its reason stated at the point of display (AS-4: the checked
    23.423(b) increment is an inertia term with no delta; 23.443(b) is linear
    in V with no q term). Tail-scoped like ``lt25``/``lt50``: ``None`` on
    wing/fuselage conditions, and on a persisted set that predates them."""
    component: str
    label: str
    far_reference: str = ""
    case: Optional[int] = None
    loads: List[LoadValue] = field(default_factory=list)
    lt25: Optional[float] = None
    lt50: Optional[float] = None
    case_ref: Optional[CaseRef] = None
    note: str = ""
    safety_factor: float = ULTIMATE_FACTOR   # limit -> ultimate factor for this case
    beta_deg: Optional[float] = None         # v-tail: sideslip of the case (SC-1)
    cy_beta_fin: Optional[float] = None      # v-tail: fin Cy_beta, per deg
    cn_beta_fin: Optional[float] = None      # v-tail: fin Cn_beta about xw, per deg
    alpha_tail_deg: Optional[float] = None   # tail: AT / fin AoA of the case (deg)
    delta_deg: Optional[float] = None        # tail: elevator/rudder deflection (deg)
    q_psf: Optional[float] = None            # tail: q at the governing point (lb/ft^2)


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
    #: Case numbers whose balance came back **clamped** -- the dynamic-pressure
    #: iteration reached a fixed point off the stall line because the Mach cap
    #: pinned the true airspeed, so the point is stall-limited flight rather than
    #: a converged stall-line solve (#33, decision **D-30**). **Derived, never
    #: persisted**: ``io.envelope_to_dict`` names its keys, so this field is not
    #: a schema field and a project loaded from disk carries an empty list --
    #: re-run FLTLOADS to repopulate it. Read it through :meth:`is_clamped`.
    clamped_cases: List[int] = field(default_factory=list)

    def is_clamped(self, point: VnPoint) -> bool:
        """Is this V-n row's balance clamped at the Mach cap? (#33)

        The **one owner** of that predicate (`CONVENTIONS.md` §7): the state comes
        from the solver that hit it, so a consumer marking these rows (#32) reads
        the same answer the balance reached rather than re-deriving it from the
        published CL. Compares by case number, the row's identity within a run.
        """
        return point.case in self.clamped_cases


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
    #: The **free** torsion this strip carries about the reference axis -- its own
    #: section/offset moment, with no accumulation of outboard transfer in it.
    #:
    #: ``myy`` above is cumulative and is *not* a free moment: it already contains
    #: the sweep/dihedral transfer of outboard shear, so assembling from it double
    #: counts (measured at 20.5 % of ``n*W*MAC`` on the wing -- see
    #: :class:`BalancedLoad`). Anything that needs the free moment therefore had to
    #: reconstruct it, which is what ``balance._free_moments`` does for the wing.
    #:
    #: Populated by ``tail_span`` (whose deck applies strip loads directly, so it
    #: needs the per-strip value); left ``0.0`` by the oracle-locked wing chain,
    #: which publishes only the cumulative column. Additive with a default, so no
    #: on-disk shape moves.
    myy_free: float = 0.0
    #: The **inertia** part of ``fz`` -- ``-n_normal * W_surf * frac`` -- carried
    #: alongside the net so a consumer can separate the two without re-deriving
    #: the quadrature.
    #:
    #: It exists because "air only" is a real requirement somewhere else: an
    #: assembled balanced case applies the surface's mass **once**, through the
    #: component-tagged mass items in its closure field, so the applied
    #: aerodynamic set it reads from here must not have inertia in it as well
    #: (``balance.fin_sets``). Before the tail carried any inertia, ``fz`` *was*
    #: the air load and the distinction cost nothing; the moment it stopped being
    #: so, a consumer with no way to ask would have double-counted the mass
    #: silently. ``fz - f_inertia`` is the air load, exactly.
    f_inertia: float = 0.0
    #: Strip load along the member's **span axis** -- an axial load on the beam,
    #: not a bending one.
    #:
    #: The wing and the horizontal tail have no producer for it (a wing carries
    #: its spanwise inertia as ``fz``), so it is ``0.0`` on both. The **fin** does:
    #: its span is airplane ``z``, so the vertical acceleration that bends an
    #: h-tail *compresses* a v-tail, and ``-n_z * W_vt`` is an axial column in its
    #: deck. Kept as its own field rather than folded into ``fx`` because ``fx`` is
    #: the chordwise (airplane X, drag) direction and the two are different loads;
    #: the local->airplane mapping is
    #: :func:`sloads.export.coordinates.tail_axial_to_airplane`.
    f_span: float = 0.0
    #: Cumulative axial force, tip -> root on the station's own half -- what
    #: ``sz`` is for the normal load. The fin's root axial force is the number a
    #: sizing check for column buckling reads.
    s_span: float = 0.0


@dataclass
class ConcentratedLoad:
    """One concentrated wing mass, as the **applied point load** it exerts.

    A concentrated wing mass (engine, gear, fuel, a store) is not part of any
    strip: ``WINGINER`` adds it to the cumulative shears, bending and torsion of
    every station inboard of it and leaves the per-strip ``fx``/``fz``
    panel-only. That is right for the cumulative column and leaves the *applied*
    set — the thing a structures model is built from — short by the whole of the
    point mass, which on ``baron_58`` PHAA is 4821.5 lb of a 5004.1 lb root
    shear. So the load is published here as well as accumulated there.

    It is a **pure force**. Every cumulative term the mass contributes is a
    transfer of that force to the station's axis --
    ``mxx += W*(y_cw - y_i)``, ``tyy += W*(x_axis_i - x_cw)``,
    ``tvyy += W*(z_cw - z_i)`` -- so a model that applies ``fx``/``fz`` at
    ``(x, y, z)`` generates the arms itself and there is no free moment to
    carry. Pounds, inches, **LIMIT**, on the parent result's safety factor.
    """
    #: The entered mass' own name (``"Engine+prop+nacelle"``), so a deck row and
    #: the weight statement it came from can be read against each other.
    name: str
    x: float
    y: float
    z: float
    fx: float
    fz: float


@dataclass
class WingLoadResult:
    """One condition's spanwise wing load table (root-last, mirroring the manual).

    ``stations`` hold **LIMIT** loads; ``safety_factor`` is the per-case factor the
    render/export boundary scales them by to deliver ULTIMATE (see
    :class:`ConditionResult`).

    ``torsion_axis`` names the chordwise reference axis the cumulative torsion
    ``myy`` (and station ``x``) is stated about — ``"25% chord"`` as computed
    (AIRLOADS/WINGINER/NETLOADS, oracle-locked), or the surface's loads reference
    axis (e.g. ``"LRA 40% chord"``) after ``net_loads.to_loads_ref_axis``. Every
    rendered/exported torsion must carry this label."""
    case: str
    nz: float = 0.0
    nx: float = 0.0
    stations: List[WingStationLoad] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None
    safety_factor: float = ULTIMATE_FACTOR   # limit -> ultimate factor for this case
    torsion_axis: str = "25% chord"          # reference axis of station x / myy
    #: The concentrated wing masses as applied point loads (empty when none are
    #: entered). Additive with a default, so no on-disk shape moves; see
    #: :class:`ConcentratedLoad` for why the strip table alone is not the
    #: applied set.
    point_loads: List[ConcentratedLoad] = field(default_factory=list)


@dataclass
class ControlPointLoad:
    """One attachment load of a discretely-modelled control surface (plan 09 T6).

    In ``control_load_mode = "discrete"`` the control surface's own air load stops
    being smeared into the parent surface and is carried into it the way the
    airplane carries it: **normal reactions at the hinges** and the **hinge-moment
    couple at the actuator**. This is one of those points.

    ``kind`` is ``"hinge"`` or ``"actuator"``. Coordinates are the surface's local
    frame, as :class:`TailSpanResult` describes: ``y`` the span station, ``x`` the
    chord station of the **load reference axis** — the point sits on the LRA line
    like every other node in the deck, so a hinge's chordwise offset from the LRA
    arrives as torsion in ``m_torsion`` rather than as a node off the beam.

    ``f_normal`` is along the surface's normal axis (vertical for the horizontal
    tail, lateral for the fin) and ``m_torsion`` is about its **span** axis, both
    LIMIT, in the same sign convention as :attr:`WingStationLoad.myy_free`. A
    hinge carries both; the actuator carries ``m_torsion`` alone — with no horn
    radius in the schema a rotary actuator is the honest model, and it is what
    makes the chordwise identity exact (plan 09 decision T-15).
    """
    kind: str
    x: float
    y: float
    z: float
    f_normal: float = 0.0
    m_torsion: float = 0.0


@dataclass
class TipTransfer:
    """The horizontal tail's reaction set, carried at the fin tip (plan 09 T7).

    On a T-tail the horizontal surface sits on top of the fin, so every fin case
    is also carrying whatever the h-tail is doing concurrently. Decision T-5 says
    what "concurrently" means: the **balancing** tail load at that case's own V-n
    point plus the h-tail's inertia at that point's load factor — a rational
    pairing, one deck per v-tail case, rather than the conservative
    superposed-critical-h-tail policy (§8 keeps that as an option).

    ``fz``/``myy`` are the transferred set in **airplane** axes at the fin-tip
    node, LIMIT: a vertical force (axial to the fin) and the moment its fore-aft
    offset makes about that node. Roll and yaw are identically zero and are not
    fields: the pairing is a *balancing* condition, which is symmetric, so the
    h-tail's two halves cancel about the centreline (decision T-16).

    Everything else here is the audit trail — the two loads separately, the
    chordwise stations their lever arms were taken from, and the node the set was
    applied at — because a transferred resultant with no stations behind it cannot
    be checked by hand.
    """
    fz: float = 0.0
    myy: float = 0.0
    air_lb: float = 0.0
    inertia_lb: float = 0.0
    x_air: float = 0.0
    x_mass: float = 0.0
    x_tip: float = 0.0
    n_case: float = 0.0
    surface_weight_lb: float = 0.0
    #: Whether ``x_air`` came from the V-n point's own tail-CP station or fell
    #: back to the 25 % tail MAC — a derived value is marked, never implied.
    cp_assumed: bool = False
    note: str = ""


@dataclass
class TailSpanResult:
    """One condition's **spanwise** empennage load table (plan 09 T2).

    The empennage's version of :class:`WingLoadResult`, reusing
    :class:`WingStationLoad` for the stations themselves (plan 09 §3.5). What it
    adds is everything the tail has and the wing does not.

    **Frame.** Stations are in the surface's **local (span, chord) frame**: ``y``
    is the span coordinate, ``x`` the chord station on the loads reference axis,
    ``z`` zero. For the horizontal tail that frame *is* the airplane frame; the
    **vertical tail spans along ``z``** and its air load is a side force, so its
    local→airplane mapping is owned by
    :func:`sloads.export.coordinates.tail_station_to_airplane` — one edit point,
    with a drift guard, never hand-mapped at a call site (``CONVENTIONS.md`` §7).

    **Full span, one member** (decision T-8). The h-tail table runs tip to tip
    through the centreline, so ``y`` is negative on the port half; it is *not* a
    semispan table doubled. That is the only topology that can carry the
    23.427(a) left/right asymmetry in one deck, and it keeps SELECT's both-sides
    totals end-to-end with no factor-of-two seam. ``attachment_y`` are the
    fuselage attachment span stations the deck is reacted at — defined here, in
    the physics, rather than improvised by the deck writer, or the export
    invariant would have nothing to close against.

    ``lt25``/``lt50`` are the SELECT totals this table distributes (read, never
    recomputed) and ``rh_scale``/``lh_scale`` the per-side shares — ``1.0``/``1.0``
    for every symmetric case, and 23.427(a)'s split for the unsymmetrical one.
    ``planform_assumed`` records that the planform was **derived** from the
    authoritative scalar area/span rather than entered as polylines; it travels
    into every rendering and deck header, because a derived rectangular tail is a
    first-order stand-in, not a structural surface definition.

    Stations hold **LIMIT** loads; ``safety_factor`` is the per-case factor the
    render/export boundary scales them by. ``torsion_axis`` names the axis ``myy``
    is stated about — every torsion names its axis.
    """
    case: str
    component: str                            # "htail" | "vtail"
    stations: List[WingStationLoad] = field(default_factory=list)
    lt25: float = 0.0
    lt50: float = 0.0
    n_case: float = 0.0
    surface_weight_lb: float = 0.0
    #: The **lateral** load factor the fin's side inertia is built from, and the
    #: case weight it came from. ``n_y = (LT25+LT50)/W_case`` -- the free-free
    #: lateral response to the only lateral aero this suite models, so it
    #: inherits the fin-only over-statement caveat (plan 13 decision L-7) that
    #: every lateral result already states in-band. Both are ``0.0`` for the
    #: horizontal tail, whose inertia is the ``n_case`` (vertical) term alone.
    n_y: float = 0.0
    case_weight_lb: float = 0.0
    #: Attachment span stations the full-span h-tail beam is reacted at (decision
    #: T-8): the fuselage-side pair on a conventional layout, the single fin-tip
    #: joint on a T-tail. Empty for the root-supported v-tail.
    attachment_y: List[float] = field(default_factory=list)
    #: Provenance of :attr:`attachment_y` (decision T-8a) — ``attachment_assumed``
    #: False only when entered data alone fixes the stations, and
    #: ``attachment_basis`` naming the branch that produced them. A structural
    #: model gates on the basis: the innermost-strip-pair fallback is not a
    #: fuselage dimension at all (note 24 BM-3).
    attachment_assumed: bool = False
    attachment_basis: str = ""
    rh_scale: float = 1.0
    lh_scale: float = 1.0
    planform_assumed: bool = False
    inertia_modelled: bool = True
    #: How the control-surface load entered this distribution (T-4/T5). Phase 1
    #: is ``"smeared"``: the ``LT50`` camber/elevator part is spread into the
    #: surface with the rest rather than applied at hinge stations. Stated on the
    #: result because the two modes describe different load paths, and a deck that
    #: claimed the wrong one would be wrong where a designer looks.
    control_load_mode: str = "smeared"
    #: The attachment loads of a ``"discrete"`` control surface (T6). Empty in
    #: ``"smeared"`` mode, where the control load is inside ``stations`` and there
    #: is nothing separate to carry.
    control_loads: List[ControlPointLoad] = field(default_factory=list)
    #: The control surface's own air load (lb) as **applied** — both sides for the
    #: elevator, and per-side scaled, exactly the treatment :attr:`air_total`
    #: gives the surface load, so the two are comparable on the one condition
    #: (23.427(a)) whose sides differ. Read from SELECT (``elevator_load`` /
    #: ``load_on_rudder``) where the condition publishes one, derived from the
    #: TAILDIST aft-of-hinge pressure block where it does not —
    #: ``control_load_basis`` says which, in words, on every result.
    control_surface_load_lb: float = 0.0
    control_load_basis: str = ""
    #: The surface's hinge moment (lb-in) and the arm it was formed on: the
    #: aft-of-hinge chord's third, the centroid of TAILDIST's aft-of-hinge block
    #: (decision T-13). **The suite's first hinge-moment output.** Non-zero only in
    #: discrete mode, which is the only mode that has a hinge line in it.
    hinge_moment_lbin: float = 0.0
    hinge_moment_arm_in: float = 0.0
    #: The h-tail set this fin carries at its tip on a T-tail (T7). ``None`` for
    #: every horizontal-tail result, and for a fin whose layout is conventional —
    #: the load path does not exist there, so neither does the field.
    tip_transfer: Optional[TipTransfer] = None
    case_ref: Optional[CaseRef] = None
    safety_factor: float = ULTIMATE_FACTOR
    torsion_axis: str = "25% chord"
    notes: List[str] = field(default_factory=list)

    @property
    def air_total(self) -> float:
        """``rh_scale*(LT25+LT50)/2 + lh_scale*(LT25+LT50)/2`` -- the air load this
        table integrates to, which is the SELECT total for a symmetric case and
        the ``RH + LH`` sum for 23.427(a)."""
        half = 0.5 * (self.lt25 + self.lt50)
        return (self.rh_scale + self.lh_scale) * half if self.component == "htail" \
            else self.rh_scale * (self.lt25 + self.lt50)


@dataclass
class BalancedLoad:
    """One applied load in an assembled free-free airplane case (plan 11 B2).

    Position ``(x, y, z)`` in airplane axes (in); force ``(fx, fy, fz)`` in lb and
    **free** moment ``(mx, my, mz)`` in lb-in. "Free" is the operative word: this
    is the moment the load carries about its *own* point, so a consumer computes
    the resultant as ``m + (p - ref) x F`` and nothing is counted twice.

    That distinction is the one this class exists to make explicit.
    ``WingStationLoad.myy`` is **not** a free moment -- it is a cumulative torsion
    that already contains the sweep/dihedral transfer of outboard shear to the
    inboard reference -- so assembling from it directly double-counts the transfer.
    Measured on ``ga6_normal`` PHAA: doing so puts the airplane's pitching-moment
    residual at 20.5 % of ``n*W*MAC`` instead of 0.15 %.

    ``source`` records what the load is (``"wing-air"``, ``"wing-inertia"``,
    ``"tail-air"``, ``"vtail-air"``, ``"body-inertia"``, ``"fuselage-cm"``,
    ``"body-axial"``,
    ``"closure-n"``, ``"closure-pitch"``, ``"closure-roll"``) and ``side`` which
    half it is on (``"L"``/``"R"``/``"C"``),
    so a deck can band them and a check can attribute a residual to its source.
    """
    x: float
    y: float
    z: float
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0
    source: str = ""
    side: str = "C"
    #: The mass this load represents (lb), for an inertia load; 0.0 for aero.
    #: Carried so the residual closure can spread relief in proportion to mass
    #: without dividing a force by a load factor that may be zero.
    weight_lb: float = 0.0


@dataclass
class BalancedCaseResult:
    """One balanced free-free airplane case: wing tip to wing tip, nose to tail.

    The mission's aim-2 deliverable (plan 11): a full-airplane load set that needs
    no constraint because it balances. ``loads`` are **LIMIT** and full-span;
    ``safety_factor`` is the factor the render/export boundary scales them by.

    The residual fields are the case's own honesty statement and are part of the
    deliverable, not internal scratch: ``residual_*`` are the out-of-balance
    *before* closure (what the physics actually achieves), and ``delta_n`` /
    ``q_dot`` the rigid-body relief applied to close it. A reader who wants to
    know how much of the balance was assumed rather than computed reads those
    three numbers.
    """
    label: str
    vn_case: int
    cg: str
    nz: float
    weight_lb: float
    mac: float
    #: The point the residuals are stated about: the case's CG station and
    #: waterline (in). Carried on the result because a residual is meaningless
    #: without the reference it was taken about, and a consumer that wants to
    #: re-derive one had to look the loading up by name -- which stopped working
    #: when the ground families arrived, since those sit at design weights that
    #: are not any *named* loading's own (23.473(a) scales cases 13-22 to the
    #: take-off weight, so "aft max landing" names two different targets).
    cg_x: float = 0.0
    cg_z: float = 0.0
    #: Wing semi-span (in) -- the lever the **roll** residual is judged against,
    #: as the MAC is for pitch. Zero on a result built without geometry, which
    #: makes :attr:`roll_residual_fraction` 0 rather than dividing by nothing.
    semi_span: float = 0.0
    loads: List[BalancedLoad] = field(default_factory=list)
    residual_fz: float = 0.0
    residual_fx: float = 0.0
    residual_my: float = 0.0
    #: The lateral three (B7). ``residual_mx`` is the one that matters today --
    #: an antisymmetric case is out of balance in **roll**, a degree of freedom
    #: the symmetric three cannot see, so a case assembled without it reads as
    #: balanced while carrying a whole unreacted rolling moment. ``fy``/``mz``
    #: are identically zero until B8a's lateral families and are carried so those
    #: inherit a complete resultant rather than growing one.
    residual_fy: float = 0.0
    residual_mx: float = 0.0
    residual_mz: float = 0.0
    delta_n: float = 0.0
    #: Longitudinal relief -- the airplane's deceleration under net drag, the
    #: quantity FAR 23 calls ``nx``. Nothing else in an assembled model reacts
    #: drag, because the suite has no distributed thrust.
    delta_nx: float = 0.0
    #: Lateral relief, ``n_y`` (B8a-2). Identically zero until a case carries a
    #: side load, and computed rather than assumed so the lateral families
    #: inherit a closure that already covers it.
    delta_ny: float = 0.0
    #: The three angular accelerations the closure solves for, in **1/in**
    #: (weight-space: g per inch of arm -- multiply by
    #: :data:`sloads.rigid_body.G_IN_S2` for rad/s^2). From B8a-2 these are true
    #: accelerations out of one coupled 3x3 solve on the assembled inertia
    #: tensor, not the per-axis moment-distribution coefficients ``delta_pitch``
    #: / ``delta_roll`` carried before it: ``q_dot`` moved 18-22 % on
    #: ``ga6_normal`` when the pitch DOF stopped being ``My / Sum w*dx^2``.
    #:
    #: ``p_dot`` is the d'Alembert reaction to the aileron's unbalanced rolling
    #: moment; its sign reverses between the handed twins, as ``r_dot`` and
    #: :attr:`delta_ny` do.
    p_dot: float = 0.0
    q_dot: float = 0.0
    r_dot: float = 0.0
    #: The assembled mass set's inertia tensor about the CG (lb-in^2), the one
    #: the closure actually solved on -- placement plus the self-inertia of every
    #: item the assembly does not spread (decision L-3). Reported because three
    #: different ``Izz`` exist for the same airplane and a reader needs to know
    #: which one reacted the load (plan 13 §3.4, risk R5).
    closure_inertia: Optional["InertiaTensor"] = None
    #: The applied unbalanced rolling moment (FAR 23.349, lb-in). Zero for a
    #: symmetric case; sign reverses between the handed twins.
    unbal_moment: float = 0.0
    fuselage_cm: float = 0.0
    #: The airplane's **non-wing** drag (lb, +aft): the airplane-less-tail polar's
    #: body-axis ``x`` force less what the wing strips carry. Applied as the
    #: ``body-axial`` load; zero on the ground families, which have no aero.
    body_axial: float = 0.0
    #: The wind-axis drag-coefficient increment that load represents,
    #: ``dD/(q*S)``. Reported because carrying the load necessarily removes it
    #: from the residual: ``residual_fx`` becomes zero by construction, so this is
    #: the quantity a regression in the two drag models shows up in. A missing
    #: parasite term is a ``CD`` offset independent of ``CL``, so what has physical
    #: content is its **consistency across the cases** of one fixture, not its
    #: value on any one of them (design note ``20_body_drag_carrier_note.md`` G10).
    delta_cd: float = 0.0
    #: ``True`` when the non-wing difference came out **forward** at a trim
    #: ``alpha`` outside the polar's trusted window
    #: (:data:`~sloads.constants.POLAR_TRUSTED_ALPHA_DEG`) and was therefore
    #: **not applied**: :attr:`body_axial` is ``0``, :attr:`delta_cd` still
    #: reports the unclamped difference, and ``residual_fx`` re-opens by exactly
    #: that amount on this case (design note 20 D-4 as revised 2026-08-17).
    body_axial_clamped: bool = False
    #: The L-7 wing-body sideslip term (design note 19), **LIMIT**: the applied
    #: side force (lb, ``+`` starboard) and the yawing moment it and its free
    #: couple make **about this case's CG** (lb-in, ``+`` nose to port). Zero
    #: when the term is disabled, unavailable, or the case has ``beta = 0``;
    #: both odd under the mirror.
    body_side_force: float = 0.0
    body_yaw_moment: float = 0.0
    #: The case's sideslip (deg, SC-1) as SELECT published it, ``None`` on a
    #: case with no lateral aero; flips with the hand.
    beta_deg: Optional[float] = None
    #: Fin + wing-body ``Cn_beta`` per degree about ``xw`` (suite sign: negative
    #: = restoring) -- note 19 gate G3's number, stated on the case whether or
    #: not the term is applied; ``None`` when either half is unknown.
    cn_beta_net: Optional[float] = None
    case_ref: Optional[CaseRef] = None
    #: ``"R"``/``"L"`` for the two twins of an antisymmetric case, ``""`` when the
    #: case is symmetric and therefore its own mirror image (B-6/B-7).
    hand: str = ""
    safety_factor: float = ULTIMATE_FACTOR
    notes: List[str] = field(default_factory=list)

    @property
    def n_w(self) -> float:
        """``n*W`` -- the scale the force residual is judged against."""
        return abs(self.nz * self.weight_lb)

    @property
    def roll_moment_fraction(self) -> float:
        """``|Mx| / (n*W*b/2)`` -- how much roll the case carries.

        **Not a residual in the sense the other two are, and deliberately not
        gated at 1 %.** ``residual_fz`` and ``residual_my`` measure what the
        physics fails to balance; ``residual_mx`` is the aileron's applied
        rolling moment, which the airplane is *supposed* not to balance -- it
        rolls, and FAR 23.349 is about the loads while it does. The quantity is
        reported (6.7 % of ``n*W*b/2`` on ``ga6_normal`` ACRL, 2.0 % on the
        regional jet) because it says how hard the case rolls, and it is reacted
        in full by :attr:`p_dot`. Same standing as :attr:`delta_nx`, which
        reacts drag for the same reason: nothing else in an assembled model can.

        Against the semi-span rather than the MAC because a rolling moment acts
        through the span.

        From B8a-3 the aileron is not the only source: a **lateral** case's fin
        load acts above the roll axis, so it rolls the airplane too (1.2 % of
        ``n*W*b/2`` on ``ga6_normal``'s ``SUDDEN RUDDER``, and the sign says
        which way). The property is the case's roll either way -- it reads
        ``residual_mx``, whatever put it there -- and the standing is the same:
        reported, reacted in full by :attr:`p_dot`, never gated.
        """
        denom = self.n_w * self.semi_span
        return abs(self.residual_mx) / denom if denom else 0.0

    @property
    def force_residual_fraction(self) -> float:
        return abs(self.residual_fz) / self.n_w if self.n_w else 0.0

    @property
    def moment_residual_fraction(self) -> float:
        denom = self.n_w * self.mac
        return abs(self.residual_my) / denom if denom else 0.0


@dataclass
class BodyStationLoad:
    """Net load at one longitudinal fuselage station (airplane body axes).

    ``x`` fuselage station (in); per-segment applied forces ``fx`` (axial), ``fy``
    (side), ``fz`` (vertical); cumulative shears ``sx``/``sy``/``sz``; bending
    ``myy`` (about Y, from the vertical load), ``mzz`` (about Z, from the side
    load) and torsion ``mxx`` (about the body X axis). Pounds and inch-pounds
    (fuselage net distribution, Ref 1 Ch 15).

    ``source`` records where the applied load came from, so the export can give
    each station a **stable GID** independent of its index in the merged table:
    ``"mass"`` (a fuselage mass item), ``"tail"`` (the balancing tail air load),
    ``"carry"`` (a wing carry-through reaction node) or ``"correction"`` (a
    whole-body fallback correction node) -- see
    :func:`sloads.export.sbeam_bridge.body_station_gids`."""
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
    source: str = "mass"


@dataclass
class BodyLoadResult:
    """One condition's longitudinal fuselage net-load table (nose-to-tail).

    ``stations`` hold **LIMIT** loads; ``safety_factor`` is the per-case factor the
    render/export boundary scales them by to deliver ULTIMATE (see
    :class:`ConditionResult`), copied from the source :class:`CriticalCondition`.

    The moment-closure fields (Ref 1 Ch 15 p103, M4-1): ``m_unbalanced`` is the
    unbalanced moment of the wing-reaction-free set (lb-in, LIMIT);
    ``r_front``/``r_rear`` are the front/rear spar **fitting loads** (lb, LIMIT) at
    stations ``x_front``/``x_rear``, reported for the wing-attach fittings and
    *not* applied on top of the distribution (which already carries them).
    ``spars_assumed`` marks spar stations taken from the module defaults rather
    than entered. ``closure_artifact`` marks the fallback path -- no derivable
    spar stations, so the moment was closed by a whole-body correction with no
    physical source; those results carry
    :data:`~sloads.modules.body_loads.CLOSURE_ARTIFACT_CAVEAT` and leave the
    fitting loads ``None``."""
    case: str
    stations: List[BodyStationLoad] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None
    safety_factor: float = ULTIMATE_FACTOR   # limit -> ultimate factor for this case
    m_unbalanced: float = 0.0                # lb-in, LIMIT (pass-1 terminal Myy)
    r_front: Optional[float] = None          # lb, LIMIT -- front spar fitting load
    r_rear: Optional[float] = None           # lb, LIMIT -- rear spar fitting load
    x_front: Optional[float] = None          # in -- front spar station
    x_rear: Optional[float] = None           # in -- rear spar station
    spars_assumed: bool = False              # spar fractions defaulted, not entered
    closure_artifact: bool = False           # moment closed by the whole-body fallback


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
    than a single hardcoded value.

    ``lt25``/``lt50`` and the station pressures are **LIMIT**; ``safety_factor`` is
    the per-case factor the render/export boundary scales them by to deliver
    ULTIMATE (see :class:`ConditionResult`), copied from the source
    :class:`CriticalCondition`.

    ``alpha_tail_deg`` / ``beta_deg`` / ``delta_deg`` / ``q_psf`` carry the
    source condition's published aero state across (note 35, AS-6), so the
    page that distributes a case can state the state that made it without
    re-deriving anything -- semantics per :class:`CriticalCondition`. Angles
    and q are never SF-scaled (CONVENTIONS §3: loads only)."""
    case: str
    component: str
    lt25: float
    lt50: float
    stations: List[TailChordStation] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None
    far_reference: str = ""
    safety_factor: float = ULTIMATE_FACTOR   # limit -> ultimate factor for this case
    alpha_tail_deg: Optional[float] = None   # source condition's AT / fin AoA (deg)
    beta_deg: Optional[float] = None         # source condition's sideslip (SC-1, deg)
    delta_deg: Optional[float] = None        # source elevator/rudder deflection (deg)
    q_psf: Optional[float] = None            # source dynamic pressure (lb/ft^2)


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
    profile (leading-edge first). Produced by AILERON / FLAPLOAD / TABLOADS (C8).

    ``load_lb`` and the station pressures are **LIMIT**; ``safety_factor`` is the
    per-case factor the render/export boundary scales them by to deliver ULTIMATE
    (see :class:`ConditionResult`)."""
    surface: str
    case: str
    load_lb: float
    v_kt: float = 0.0
    stations: List[ControlSurfaceStation] = field(default_factory=list)
    case_ref: Optional[CaseRef] = None
    safety_factor: float = ULTIMATE_FACTOR   # limit -> ultimate factor for this case


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
    #: The design weight this case is computed at (lb) -- ``WL`` in LANDLOAD.BAS
    #: (lines 820-900). **Not** simply the named loading's weight: 23.473(a) lets
    #: 23.479/481/483 be met at the design *landing* weight while 23.485/23.493
    #: are met at the maximum take-off weight, which LANDLOAD applies as
    #: ``WR = MTOW/MLW`` on cases 13-22 (and not on 23-24, which stay at the light
    #: landing weight). Carried on the record because the assembled ground case
    #: has to build its inertia set at the weight its reactions were computed at,
    #: and recovering that by re-deriving the ``WR`` table at the consumer is the
    #: duplication that made this a field instead.
    weight_lb: float = 0.0
    # Ground-line ("prime") reactions
    vmp: float = 0.0    # vertical main, per wheel
    dmp: float = 0.0    # drag main
    smp: float = 0.0    # side main
    rmp: float = 0.0    # resultant main = sqrt(vmp^2 + dmp^2)
    vnp: float = 0.0    # vertical nose
    dnp: float = 0.0    # drag nose
    snp: float = 0.0    # side nose
    result: float = 0.0  # resultant nose = sqrt(vnp^2 + dnp^2)
    # Airplane-datum reactions (resolved through PHIM/PHIN; not yet surfaced in a
    # deliverable -- they are the natural input to the M4-6 ground-case fuselage
    # distribution, which needs the reactions in the airplane's own axes).
    vm: float = 0.0
    dm: float = 0.0
    vn: float = 0.0
    dn: float = 0.0
    # Inertia factors (ground line), dimensionless -- load *factors*, so they are
    # never scaled to ultimate (M4-17e).
    nvp: float = 0.0
    ndp: float = 0.0
    ns: float = 0.0
    # Unbalanced moments about the airplane CG (ground line)
    pitchp: float = 0.0
    rollp: float = 0.0
    yawp: float = 0.0
    # --- The airplane-datum half of the printout (design note 38 GF-6, #134) ---
    #: p231's FUSELAGE AXIS ANGLE column: the attitude's ground angle ``GRA``, in
    #: degrees. An angle, never a load -- it carries no safety factor.
    fuselage_axis_angle_deg: float = 0.0
    #: The airplane-datum load factors of p232: resultant, vertical and drag.
    #: Zero on the 23.499 supplementary-nose family (25-33), which carries no
    #: airplane in equilibrium -- exactly as ``nvp``/``ndp`` are. ``ns`` is
    #: common to both frames (the side axis is normal to the rotation) and is
    #: therefore not repeated here.
    nr: float = 0.0
    nv: float = 0.0
    nd: float = 0.0
    #: The same unbalanced moments, in the airplane datum (p233's second table).
    #: The pitching moment is invariant under the rotation; roll and yaw mix.
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
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
    #: Spanwise empennage distributions (plan 09 T2) -- the tail's analogue of
    #: ``wing_net``, and the surface the empennage deck is written from. The
    #: chordwise ``tail_chordwise`` table above is unchanged and remains the
    #: oracle-locked TAILDIST view of the same conditions.
    htail_span: List[TailSpanResult] = field(default_factory=list)
    vtail_span: List[TailSpanResult] = field(default_factory=list)


__all__ = [
    "BalancedCaseResult",
    "BalancedLoad",
    "BodyLoadResult",
    "BodyStationLoad",
    "CaseRef",
    "ConcentratedLoad",
    "ConditionResult",
    "ControlPointLoad",
    "ControlSurfaceLoadResult",
    "ControlSurfaceStation",
    "CriticalCondition",
    "CriticalLoadSet",
    "EnvelopeResult",
    "GearReactionCase",
    "LoadValue",
    "LoadsResult",
    "MassCase",
    "MassResult",
    "ModuleResult",
    "TailBalanceLoad",
    "TailChordResult",
    "TailChordStation",
    "TailSpanResult",
    "TipTransfer",
    "VnPoint",
    "WingLoadResult",
    "WingStationLoad",
]
