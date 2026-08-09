"""Balanced free-free airplane cases -- wing tip to wing tip, nose to tail.

Plan 11 (``docs/30_future/11_balanced_airframe_cases_plan.md``) step **B2**,
decisions B-1…B-5. Conventions: ``docs/10_standard/CONVENTIONS.md``.

The goal, in the user's words: *a full airplane balanced case with no need for a
constraint, because the loads balance.* The airplane already balances at trim --
``flight_envelope._balance`` closes ``LZW + LT = Nz*W`` exactly, and
``test_concept_closure`` has asserted it for a long time. What was missing is
that the **distributed** loads never inherited that balance: the wing
distribution, the tail load, the fuselage inertia and the trim solve were four
separate calculations that nothing assembled.

This module assembles them and reports what is left over.

Three things had to be got right, and each was measured rather than assumed
-------------------------------------------------------------------------
**1. A cumulative torsion is not a free moment.** ``WingStationLoad.myy`` is the
torsion about the *root* 25 % chord, and it already contains the sweep and
dihedral transfer of outboard shear inboard (``tyy``/``tvyy`` in
``airloads.py``). Assembling from it *and* applying the strip's position offset
counts the transfer twice: on ``ga6_normal`` PHAA that puts the pitching-moment
residual at **20.5 %** of ``n*W*MAC`` instead of 0.15 %. Only the section
pitching moment ``ml`` is a free moment, and :func:`_free_moments` recovers it by
subtracting the two transfer accumulations back out.

**2. The wing load must be at the balanced case's own flight condition.** The
entered ``wing_mass.cases`` carry a hand-written ``cl``/``v_eas_kt`` that is a
*different condition* from the V-n point SELECT pairs them with -- ``atr42_100``
enters CL 1.55 at 170 kt against its V-n point's 1.7283 at 185.85 kt. Assembling
the two halves then compares different flight conditions, and the force residual
runs 10-37 % of ``n*W``. So the wing distribution is **recomputed at the V-n
point's own** ``cl``/``v``/``nz`` (:func:`wing_sets`). The entered distributions
are untouched and remain the FAR 23 deliverables -- this adds a case, it does not
change one, and no Appendix A oracle moves.

**3. The mass model is the items, not WINGINER's own.** Wing inertia comes from
the ``WING``-tagged items of the case's derived loading (step B1/C1), spread over
WINGINER's spanwise shape -- decision B-2 and plan 11 §4. Taking it from
``wing_mass.panel_weight_lb + concentrated`` instead double-counts anything that
is in both models: on ``atr42_100`` and ``dhc8_dash8`` the wing-tank fuel is, and
the residual runs 12-13 % rather than 1.9 %.

What the assembled case carries, and what it must not
-----------------------------------------------------
The seam rule (plan 11 §4), stated once: **a load that a free-body cut
introduces is never applied in the assembled model.** Each per-component deck
takes a cut and carries the cut reaction as an applied load; in the assembled
model the solver recovers it. Concretely the wing carry-through reaction
(``BodyStationLoad.source == "carry"``) is *excluded* -- :func:`assemble` never
reads ``body_loads``, and :func:`carry_sources_absent` is the guard.

The fuselage pitching moment
----------------------------
The trim carries ``Cm`` for the airplane **less tail** -- wing *and* fuselage --
while the distributed wing carries only its own section ``Cm``. The difference is
the fuselage's Munk moment: measured at **+4.3 to +6.3 %** of ``n*W*MAC`` across
the fixtures, positive (destabilising), and with no distributed carrier until
backlog item M4-19 lands the Multhopp/Nelson body moment. It is applied here as a
single free moment on the fuselage (``source="fuselage-cm"``), which preserves the
total exactly and is labelled as lumped wherever it is rendered. Omitting it
would leave a systematic ~5 % moment residual that the closure would then absorb
silently -- a real aero load disguised as a correction.

Residual closure (B-3)
----------------------
Whatever is left is closed as mass-proportional inertia relief in two decoupled
degrees of freedom -- ``delta_n`` on every mass, and a pitch term
``+k*(x_i - x_cg)*w_i``. They do not fight each other: the pitch term sums to
zero force because ``sum(w_i*(x_i - x_cg)) == 0`` by the definition of the CG,
and the ``delta_n`` term sums to zero moment for the same reason. Both magnitudes
are recorded on the result, and the gate is on the residual **before** closure --
the physics, not the correction.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Sequence, Tuple

from ..derived_geometry import sync_geometry_derived
from ..mass_distribution import (
    CaseLoading,
    MassComponent,
    component_of,
    derive_case_loadings,
)
from ..models import (
    BalancedCaseResult,
    BalancedLoad,
    CgCase,
    MissingInputError,
    ModuleResult,
    Project,
    VnPoint,
    WingLoadResult,
)
from ..registry import register
from .airloads import air_load_distribution
from .flight_envelope import build_envelope
from .select import build_critical
from .wing_inertia import inertia_units, resolve_wing_cases

MODULE_NAME = "balance"

#: Symmetric wing conditions this step assembles. ``ACRL``/``TORS`` are
#: antisymmetric and need the handedness machinery of plan 11 **B7** (phase 2),
#: so they are deliberately not here -- a symmetric assembly of an antisymmetric
#: case would balance and mean nothing.
SYMMETRIC_WING_CONDITIONS = ("PHAA", "PLAA", "PMAA", "NMAA")

#: Acceptance gate (plan 11 §6): the residual **before** closure, as a fraction
#: of ``n*W`` for force and ``n*W*MAC`` for moment.
RESIDUAL_GATE = 0.01


# --------------------------------------------------------------------------- #
# Free moments -- undoing AIRLOADS' cumulative transfer
# --------------------------------------------------------------------------- #
def _free_moments(result: WingLoadResult) -> List[float]:
    """Per-strip **free** pitching moment (the section ``Cm`` term alone).

    ``AIRLOADS`` accumulates ``myy = tyy + tvyy + trq``: the sweep transfer of
    outboard shear (``tyy``), the dihedral transfer of outboard drag (``tvyy``)
    and the section pitching moment (``trq``). Only the last is a free moment;
    the other two are position transfers that an assembly applies for itself.
    Both are reconstructed here from the station table by the same recurrence
    ``airloads`` builds them with, and subtracted back out.

    On ``ga6_normal`` PHAA the root torsion is -79,003 lb-in, of which -60,474 is
    sweep transfer and -9,594 dihedral -- so the free moment is -8,935, and using
    the -79,003 figure as if it were free is the 20 % error.
    """
    s = result.stations
    h = len(s)
    tyy = [0.0] * h
    tvyy = [0.0] * h
    for i in range(h - 2, -1, -1):
        tyy[i] = tyy[i + 1] - s[i + 1].sz * (s[i + 1].x - s[i].x)
        tvyy[i] = tvyy[i + 1] + s[i + 1].sx * (s[i + 1].z - s[i].z)
    trq = [s[i].myy - tyy[i] - tvyy[i] for i in range(h)]
    return [trq[i] - (trq[i + 1] if i + 1 < h else 0.0) for i in range(h)]


# --------------------------------------------------------------------------- #
# The applied sets
# --------------------------------------------------------------------------- #
def _mirror(loads: Sequence[BalancedLoad]) -> List[BalancedLoad]:
    """The port-side image of a starboard set (``y -> -y``).

    Symmetric cases only, which is all this step assembles: the side loads and
    the roll/yaw moments that a general reflection has to negate are zero here.
    The general operator is plan 11 **B-6**, and it lands with the antisymmetric
    cases that actually need it -- writing it now would be a sign convention
    nothing exercises.
    """
    return [replace(ld, y=-ld.y, side="L") for ld in loads]


def wing_sets(project: Project, vn: VnPoint,
              condition: str) -> Tuple[List[BalancedLoad], float, float]:
    """Starboard wing air + inertia loads, at ``vn``'s own flight condition.

    Returns ``(loads, wing_item_weight, cm_free_total)`` where ``cm_free_total``
    is the section-``Cm`` free moment of **both** wings -- the caller needs it to
    work out the fuselage's share of the trim moment.
    """
    wm = project.wing_mass
    geom = project.geometry.by_name(wm.surface)
    aero = project.aero.by_name(wm.surface)
    base = next((c for c in resolve_wing_cases(project, wm)), None)
    if geom is None or aero is None or base is None:
        raise MissingInputError("balance needs a wing surface, aero set and load case")

    air = air_load_distribution(geom, aero, vn.cl, vn.v_eas_kt,
                                wm.wrp_waterline, wm.dihedral_deg)
    ml = _free_moments(air)
    loads = [
        BalancedLoad(x=s.x, y=s.y, z=s.z, fx=s.fx, fz=s.fz, my=ml[i],
                     source="wing-air", side="R")
        for i, s in enumerate(air.stations)
    ]
    cm_free = 2.0 * sum(ml)

    # Inertia: the loading's own WING items, spread over WINGINER's shape.
    # Inertia strips take WINGINER's **spanwise shape** at the 50 % chord (where
    # it models the panel mass CG -- its torsion carries ``-w*(c50x - c25x)`` for
    # exactly that reason), then are shifted bodily in x and z so the set's
    # centroid is the WING items' own.
    #
    # The split of authority is decision B-2: the item database owns *where* the
    # mass is, WINGINER owns *how it is spread along the span*. Without the shift
    # the two disagree -- ga6's wing item sits at x 97.87 while the 50 % chord
    # line runs 78-95 -- and the difference lands in the pitching residual as a
    # moment the trim does not have, because the trim lumps all mass at the CG.
    # It is worth 2.8-4.3 % of ``n*W*MAC`` on ``concept_regional_jet``.
    u = inertia_units(geom, wm)
    panel = sum(u.w)
    strips = [(i, w) for i, w in enumerate(u.w) if w]
    if strips and panel:
        x_shape = sum(w * u.c50x[i] for i, w in strips) / panel
        z_shape = sum(w * u.z[i] for i, w in strips) / panel
    else:
        x_shape = z_shape = 0.0
    for i, w in strips:
        loads.append(BalancedLoad(
            x=u.c50x[i] - x_shape, y=u.ye[i], z=u.z[i] - z_shape,
            fz=-w * vn.nz, weight_lb=w, source="wing-inertia", side="R"))
    return loads, 2.0 * panel, cm_free


def _wing_inertia_scale(loading: CaseLoading, project: Project,
                        panel_both_sides: float) -> float:
    """Factor bringing WINGINER's panel mass onto the loading's WING item weight.

    Decision B-2: the items are the mass SSOT, and WINGINER supplies the *shape*.
    Where the two models already agree the factor is exactly 1.0 (``ga6_normal``
    330 = 2 x 165); where they do not it is what stops the disagreement becoming
    a load. Returns 0.0 for a wing with no modelled panel, which is a caller
    error rather than a silent zero -- :func:`assemble` notes it.
    """
    wing_items = sum(it.weight_lb for it in loading.items
                     if component_of(it, project) == MassComponent.WING)
    return wing_items / panel_both_sides if panel_both_sides else 0.0


def body_inertia(loading: CaseLoading, project: Project,
                 nz: float) -> List[BalancedLoad]:
    """Inertia of everything the wing does not carry, at each item's own station.

    The wing enters the fuselage as the carry-through *reaction*, which the
    assembled model's solver recovers -- so no ``carry`` load appears here, and
    none may (plan 11 §4).
    """
    return [
        BalancedLoad(x=it.x, y=it.y, z=it.z, fz=-it.weight_lb * nz,
                     weight_lb=it.weight_lb, source="body-inertia", side="C")
        for it in loading.items
        if component_of(it, project) != MassComponent.WING
    ]


# --------------------------------------------------------------------------- #
# Resultants and closure
# --------------------------------------------------------------------------- #
def resultant(loads: Sequence[BalancedLoad],
              ref: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """``(Fx, Fz, My)`` of ``loads`` about ``ref`` -- free moments plus lever arms."""
    fx = sum(ld.fx for ld in loads)
    fz = sum(ld.fz for ld in loads)
    my = sum(ld.my + (ld.z - ref[2]) * ld.fx - (ld.x - ref[0]) * ld.fz
             for ld in loads)
    return fx, fz, my


def _closure(loads: List[BalancedLoad], cg: CgCase,
             residual_fx: float, residual_fz: float,
             residual_my: float) -> Tuple[float, float, float]:
    """Close the residual as mass-proportional relief; return ``(dn, dnx, k)``.

    **Three** degrees of freedom, not the two plan 11 B-3 anticipated -- the
    symmetric airplane's x, z and pitch. All three are mutually decoupled, and
    every cross-term vanishes for the same reason: the loading's own centroid
    *is* the CG (step C1 solves the ballast from it), so
    ``sum(w_i*(x_i - x_cg)) == sum(w_i*(z_i - z_cg)) == 0``.

    * ``dn`` -- ``-w_i*dn`` on every mass. No pitching moment (x-centroid).
    * ``dnx`` -- ``-w_i*dnx`` longitudinally. No pitching moment (z-centroid).
    * pitch -- ``+k*(x_i - x_cg)*w_i``. No force in either component.

    The x degree of freedom is not optional: **nothing else in the assembled
    model reacts drag.** The suite has no distributed thrust, and FAR 23's
    longitudinal load factor ``nx`` is exactly this quantity. On ``ga6_normal``
    PHAA the closure gives 0.661 g against the fixture's entered ``nx`` of
    0.6065, the difference being the same strip-quadrature-versus-closed-form gap
    that sets the vertical residual floor. Leaving it open would put 17-26 % of
    ``n*W`` into the support reaction and make "reactions ~ 0" untrue in a file
    that still solved.

    The relief is spread over **the inertia loads already in the model**, not
    over the raw item list. Those are the same masses, but at the places the
    assembled model actually carries them -- wing mass out along the span rather
    than on the centreline where the database enters it -- so the deck's internal
    load path stays physical and no relief lands on a node the airplane has no
    mass at.
    """
    masses = [(ld, ld.weight_lb) for ld in loads if ld.weight_lb]
    w_total = sum(w for _, w in masses)
    if not w_total:
        return 0.0, 0.0, 0.0
    j = sum(w * (ld.x - cg.xcg) ** 2 for ld, w in masses)
    dn = residual_fz / w_total
    dnx = residual_fx / w_total
    k = residual_my / j if j else 0.0
    for ld, w in masses:
        loads.append(BalancedLoad(
            x=ld.x, y=ld.y, z=ld.z, fz=-w * dn, fx=-w * dnx,
            source="closure-n", side=ld.side))
        loads.append(BalancedLoad(
            x=ld.x, y=ld.y, z=ld.z, fz=k * (ld.x - cg.xcg) * w,
            source="closure-pitch", side=ld.side))
    return dn, dnx, k


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def assemble(project: Project, condition: str, vn: VnPoint,
             loading: CaseLoading, cg: CgCase,
             case_ref=None) -> BalancedCaseResult:
    """Assemble one balanced case and close its residual."""
    fl = project.flight_loads
    notes: List[str] = []

    wing_r, panel_both, cm_free = wing_sets(project, vn, condition)
    scale = _wing_inertia_scale(loading, project, panel_both)
    if scale == 0.0:
        notes.append("wing panel mass is zero -- wing inertia not modelled")
    elif abs(scale - 1.0) > 1e-6:
        notes.append(
            f"wing inertia scaled x{scale:.4f} onto the loading's WING items "
            f"({scale * panel_both:.0f} lb); WINGINER's integrated panel mass is "
            f"{panel_both:.0f} lb")
    wing_items = [it for it in loading.items
                  if component_of(it, project) == MassComponent.WING]
    w_wing = sum(it.weight_lb for it in wing_items)
    x_wing = (sum(it.weight_lb * it.x for it in wing_items) / w_wing) if w_wing else 0.0
    z_wing = (sum(it.weight_lb * it.z for it in wing_items) / w_wing) if w_wing else 0.0
    wing_r = [
        replace(ld, fz=ld.fz * scale, weight_lb=ld.weight_lb * scale,
                x=ld.x + x_wing, z=ld.z + z_wing)
        if ld.source == "wing-inertia" else ld
        for ld in wing_r
    ]

    loads: List[BalancedLoad] = list(wing_r) + _mirror(wing_r)
    loads.append(BalancedLoad(x=fl.xtc, y=0.0, z=fl.zw, fz=vn.lt,
                              source="tail-air", side="C"))
    loads += body_inertia(loading, project, vn.nz)

    # The fuselage's share of the trim pitching moment: what the airplane-less-tail
    # Cm carries that the distributed wing does not (see the module docstring).
    wing_about_ac = sum(
        ld.my + (ld.z - fl.zw) * ld.fx - (ld.x - fl.xw) * ld.fz
        for ld in loads if ld.source == "wing-air")
    fuselage_cm = vn.m_wf - wing_about_ac
    loads.append(BalancedLoad(x=fl.xw, y=0.0, z=fl.zw, my=fuselage_cm,
                              source="fuselage-cm", side="C"))

    ref = (cg.xcg, 0.0, cg.zcg)
    fx, fz, my = resultant(loads, ref)
    dn, dnx, k = _closure(loads, cg, fx, fz, my)

    return BalancedCaseResult(
        label=condition, vn_case=vn.case, cg=cg.name, nz=vn.nz,
        weight_lb=cg.weight_lb, mac=fl.mac, loads=loads,
        residual_fz=fz, residual_fx=fx, residual_my=my,
        delta_n=dn, delta_nx=dnx, delta_pitch=k, fuselage_cm=fuselage_cm,
        case_ref=case_ref, notes=notes,
    )


def build_balanced_cases(project: Project) -> List[BalancedCaseResult]:
    """One :class:`BalancedCaseResult` per symmetric wing condition SELECT picked.

    A condition is assembled only when the whole chain exists for it: SELECT
    named it, it has a V-n point, and its CG case resolves to a **derivable**
    loading (step C1). A case whose CG the weight database cannot produce has no
    honest inertia set, and inventing one would put fictitious mass into the very
    balance the case exists to demonstrate.
    """
    sync_geometry_derived(project)
    if project.flight_loads is None or project.wing_mass is None:
        raise MissingInputError("balance needs 'flight_loads' and 'wing_mass'")
    envelope = project.envelope or build_envelope(project)
    critical = envelope.critical or build_critical(project)
    vn = {p.case: p for p in envelope.vn}
    cgs = {c.name: c for c in project.flight_loads.cg_cases}
    loadings = {ld.name: ld for ld in derive_case_loadings(project)}

    out: List[BalancedCaseResult] = []
    for cond in critical.conditions:
        if cond.component != "wing" or cond.label not in SYMMETRIC_WING_CONDITIONS:
            continue
        point = vn.get(cond.case)
        if point is None:
            continue
        cg = cgs.get(point.cg)
        loading = loadings.get(point.cg)
        if cg is None or loading is None or not loading.derivable:
            continue
        out.append(assemble(project, cond.label, point, loading, cg,
                            case_ref=cond.case_ref))
    return out


def carry_sources_absent(result: BalancedCaseResult) -> bool:
    """No cut reaction is applied in an assembled case (plan 11 §4's seam rule).

    The wing carry-through is *internal* to a full-span model -- the solver
    recovers it — so applying it as well would react the wing twice. Structural
    here (``assemble`` never reads ``body_loads``); this is the drift guard.
    """
    return not any(ld.source in ("carry", "correction") for ld in result.loads)


def run(project: Project) -> ModuleResult:
    """Registry entry point: the balanced cases as a reportable result."""
    from ..models import ConditionResult, LoadValue

    cases = build_balanced_cases(project)
    if not cases:
        raise MissingInputError(
            "no symmetric wing condition has both a V-n point and a derivable "
            "payload loading -- nothing to balance")
    conditions = []
    for c in cases:
        conditions.append(ConditionResult(
            title=f"Balanced case {c.label} (V-n {c.vn_case}, {c.cg})",
            far_reference="23.321",
            values=[
                LoadValue("Load factor Nz", c.nz, "g", key="balanced_nz"),
                LoadValue("Weight", c.weight_lb, "lb", quantity="mass",
                          key="balanced_weight"),
                LoadValue("Residual Fz (pre-closure)", c.residual_fz, "lb",
                          key="balanced_residual_fz"),
                LoadValue("Residual Fz (% of n*W)",
                          100.0 * c.force_residual_fraction, "%",
                          key="balanced_residual_fz_pct"),
                LoadValue("Residual My (pre-closure)", c.residual_my, "lb-in",
                          key="balanced_residual_my"),
                LoadValue("Residual My (% of n*W*MAC)",
                          100.0 * c.moment_residual_fraction, "%",
                          key="balanced_residual_my_pct"),
                LoadValue("Closure dn", c.delta_n, "g", key="balanced_delta_n"),
                LoadValue("Lumped fuselage Cm moment", c.fuselage_cm, "lb-in",
                          key="balanced_fuselage_cm"),
            ],
            note="; ".join(c.notes) or None,
        ))
    return ModuleResult(module=MODULE_NAME, conditions=conditions)


register(MODULE_NAME, run)


__all__ = [
    "SYMMETRIC_WING_CONDITIONS",
    "RESIDUAL_GATE",
    "wing_sets",
    "body_inertia",
    "resultant",
    "assemble",
    "build_balanced_cases",
    "carry_sources_absent",
]
