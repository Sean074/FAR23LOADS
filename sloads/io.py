"""Project JSON load/save and CSV writing.

The on-disk format is one ``project.json`` per airplane. This module is the only
place that knows how the dataclasses map to JSON, so calc modules stay pure.

A project file looks like::

    {"schema_version": 1, "name": "...", "engine": { ...EngineInput fields... }}

For convenience, :func:`load_project` also accepts a *legacy* flat file that is
just the EngineInput fields at top level (the original ``io520bb.json`` shape)
and wraps it into a Project.
"""

from __future__ import annotations

import csv
import json
import os
import warnings
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from .constants import ULTIMATE_FACTOR
from .migrations import is_project_dict, migrate
from .models import (
    SCHEMA_VERSION,
    AeroCoefficientsInput,
    AeroCoeffSet,
    AeroInput,
    AeroSurfaceInput,
    AileronLoadsInput,
    AnalysisKind,
    BodyLoadResult,
    BodyStationLoad,
    CaseRef,
    CgCase,
    ConcentratedWeight,
    ConditionResult,
    ControlSurfaceLoadResult,
    ControlSurfaceStation,
    CriticalCondition,
    CriticalLoadSet,
    EmpennageInput,
    EngineInput,
    EngineLayout,
    EngineType,
    EngineWeightType,
    EnvelopeResult,
    FlapLoadsInput,
    FlightLoadsInput,
    FuselageMassInput,
    FuselageMomentInput,
    FuselageOutline,
    FuselageSection,
    FuselageStation,
    GearCarrier,
    GeometryInput,
    GroundCaseRole,
    LandingGearGeometry,
    LandingGearInput,
    LandingInput,
    LateralBodyAeroInput,
    LayoutInput,
    LoadingDefinition,
    LoadsResult,
    LoadValue,
    MachLimitInput,
    MassCase,
    MassComponent,
    MassItem,
    MassItemKind,
    MassResult,
    ModuleResult,
    OneEngineOutInput,
    Project,
    Rotor,
    RotorDirection,
    RotorType,
    SafetyFactorOverride,
    SafetyFactorPolicyInput,
    SelectInput,
    StructuralSpeedsInput,
    SurfaceInput,
    TabLoadsInput,
    TabSpec,
    TailBalanceLoad,
    TailChordResult,
    TailChordStation,
    TailLoadsInput,
    TailMassInput,
    TailSpanResult,
    TailType,
    VdBasis,
    VnPoint,
    VTailLoadsInput,
    WeightEnvelopeInput,
    WeightEstimationInput,
    WeightInput,
    WingLoadCase,
    WingLoadResult,
    WingMassInput,
    WingStationLoad,
    default_fuselage_outline,
)
from .report import has_load_case_data, load_cases_to_rows, results_to_rows
from .units import UnitSystem, convert_results, unit_system_from
from .validation import safety_factor_valid


# --------------------------------------------------------------------------- #
# Tolerant reader (M2R-7): the one place every ``*_from_dict`` filters a raw dict
# down to its dataclass's fields before the ``cls(**d)`` splat. A file carrying an
# unknown key -- saved by a newer app version, an older one, or hand-edited -- must
# LOAD, dropping the unrecognized field, not crash with ``TypeError: __init__() got
# an unexpected keyword argument``. This makes good on the forward-compat promise in
# :func:`schema_status` ("unrecognized fields are ignored"). The full migration-chain
# overhaul (per-version hops + one frozen fixture per schema) is M4-10; this is the
# minimal tolerant-read guard that unblocks cross-version file sharing.
# --------------------------------------------------------------------------- #
def _filtered(cls: Any, d: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only the keys of ``d`` that are fields of dataclass ``cls``."""
    fields = cls.__dataclass_fields__
    return {k: v for k, v in d.items() if k in fields}


# --------------------------------------------------------------------------- #
# CaseRef <-> dict (Step D1) -- shared by every result type that carries one:
# VnPoint, CriticalCondition, WingLoadResult, BodyLoadResult, TailChordResult,
# ControlSurfaceLoadResult. ``asdict`` already nests CaseRef correctly on the
# to_dict side (no helper needed there); from_dict needs one since a plain
# ``**dict(d)`` splat would otherwise pass the nested dict straight through as
# ``case_ref`` instead of a CaseRef instance.
# --------------------------------------------------------------------------- #
def _case_ref_from_dict(raw) -> Any:
    return CaseRef(**_filtered(CaseRef, raw)) if raw else None


def _rotor_from_dict(d: Dict[str, Any]) -> Rotor:
    return Rotor(
        diameter_in=d["diameter_in"],
        weight_lb=d["weight_lb"],
        max_rpm=d["max_rpm"],
        rotor_type=RotorType(d.get("rotor_type", "T")),
        direction=RotorDirection(d.get("direction", "CW")),
        inertia=d.get("inertia"),
    )


def engine_from_dict(d: Dict[str, Any]) -> EngineInput:
    """Build an :class:`EngineInput` from a plain dict (enum + tuple coercion)."""
    d = dict(d)
    d.pop("units", None)  # legacy marker; calc is always Imperial internally
    rotors = [_rotor_from_dict(r) for r in d.pop("rotors", []) or []]

    def vec(key):
        v = d.pop(key, (0.0, 0.0, 0.0))
        return tuple(v) if v is not None else (0.0, 0.0, 0.0)

    engine_cg = vec("engine_cg")
    prop_cg = vec("prop_cg")
    engine_type = EngineType(d.pop("engine_type", "R"))

    return EngineInput(
        engine_type=engine_type,
        engine_cg=engine_cg,
        prop_cg=prop_cg,
        rotors=rotors,
        **_filtered(EngineInput, d),
    )


def engine_to_dict(inp: EngineInput) -> Dict[str, Any]:
    """Serialize an :class:`EngineInput` to JSON-friendly primitives."""
    d = asdict(inp)
    d["engine_type"] = inp.engine_type.value
    d["engine_cg"] = list(inp.engine_cg)
    d["prop_cg"] = list(inp.prop_cg)
    d["rotors"] = [
        {
            **asdict(r),
            "rotor_type": r.rotor_type.value,
            "direction": r.direction.value,
        }
        for r in inp.rotors
    ]
    return d


# --------------------------------------------------------------------------- #
# Weight slice <-> dict
# --------------------------------------------------------------------------- #
def _cg_case_from_dict(d: Dict[str, Any]) -> CgCase:
    """Build a :class:`CgCase`, coercing the G-3 ``analyses`` set and ``role``.

    ``analyses`` is a *set* in memory and a sorted list on disk -- JSON has no set,
    and sorting keeps a re-save byte-stable. An absent key means ``{FLIGHT}``,
    which is what every pre-v47 case was; the v46 hop writes the tag explicitly, so
    absence only reaches here from a hand-written dict.
    """
    d = dict(d)
    raw = d.pop("analyses", None)
    analyses = ({AnalysisKind(a) for a in raw} if raw
                else {AnalysisKind.FLIGHT})
    role_raw = d.pop("role", None)
    role = GroundCaseRole(role_raw) if role_raw else None
    loading_raw = d.pop("loading", None)
    # ``is not None``, not truthiness: an **empty** loading is a real and distinct
    # statement -- "no discretionary item is aboard", i.e. the minimum flight
    # weight, which is what ``cessna_210``'s CG4 is. It serializes to ``{}``
    # (``_loading_to_dict`` omits empty members), and reading that back as
    # ``None`` would silently return the case to the derived route (D-25c) with
    # no error anywhere. Absence of the key is the only "derive it" state.
    loading = _loading_from_dict(loading_raw) if loading_raw is not None else None
    return CgCase(analyses=analyses, role=role, loading=loading,
                  **_filtered(CgCase, d))


def _loading_from_dict(d: Dict[str, Any]) -> LoadingDefinition:
    """Build a :class:`LoadingDefinition` (D-25); its ballast is a full item row."""
    d = dict(d)
    ballast_raw = d.pop("ballast", None)
    ballast = _mass_item_from_dict(ballast_raw) if ballast_raw else None
    return LoadingDefinition(ballast=ballast, **_filtered(LoadingDefinition, d))


def _cg_case_to_dict(c: CgCase) -> Dict[str, Any]:
    """Serialize a :class:`CgCase`; ``role``/``loading`` are omitted when unset.

    Absent ``loading`` is the pre-v50 shape *and* the live "derive it" state
    (D-25c), so writing it only when set keeps a re-save of an older file
    byte-identical.
    """
    out: Dict[str, Any] = {
        "name": c.name, "weight_lb": c.weight_lb, "xcg": c.xcg, "zcg": c.zcg,
        "analyses": sorted(a.value for a in c.analyses),
    }
    if c.role is not None:
        out["role"] = c.role.value
    if c.loading is not None:
        out["loading"] = _loading_to_dict(c.loading)
    return out


def _loading_to_dict(ld: LoadingDefinition) -> Dict[str, Any]:
    """Serialize a :class:`LoadingDefinition`; empty members are omitted."""
    out: Dict[str, Any] = {}
    if ld.aboard:
        out["aboard"] = list(ld.aboard)
    if ld.fractions:
        out["fractions"] = dict(ld.fractions)
    if ld.ballast is not None:
        out["ballast"] = _mass_item_to_dict(ld.ballast)
    return out


def _mass_item_to_dict(it: MassItem) -> Dict[str, Any]:
    """Serialize one :class:`MassItem` row (the item list and D-25 ballast share it)."""
    return {**asdict(it), "kind": it.kind.value,
            "component": it.component.value if it.component else None}


def _mass_item_from_dict(d: Dict[str, Any]) -> MassItem:
    d = dict(d)
    kind = MassItemKind(d.pop("kind", "empty"))
    raw = d.pop("component", None)
    # ``None``/absent stays ``None`` -- "not tagged" is a distinct state from any
    # component, and it is what routes the item through
    # ``mass_distribution.infer_component`` rather than silently taking a default.
    component = MassComponent(raw) if raw else None
    return MassItem(kind=kind, component=component, **_filtered(MassItem, d))


def weight_from_dict(d: Dict[str, Any]) -> WeightInput:
    """Build a :class:`WeightInput` from a plain dict (enum coercion)."""
    d = dict(d)
    est = d.get("estimation")
    estimation = None
    if est:
        est = dict(est)
        estimation = WeightEstimationInput(
            engine_weight_type=EngineWeightType(est.pop("engine_weight_type", "RF")),
            **_filtered(WeightEstimationInput, est),
        )
    items = [_mass_item_from_dict(it) for it in d.get("items", []) or []]
    env = d.get("envelope")
    envelope = WeightEnvelopeInput(**_filtered(WeightEnvelopeInput, env)) if env else None
    cg_cases = [_cg_case_from_dict(c) for c in d.get("cg_cases", []) or []]
    return WeightInput(
        estimation=estimation, items=items, envelope=envelope, cg_cases=cg_cases,
        max_landing_weight_lb=float(d.get("max_landing_weight_lb", 0.0) or 0.0),
        max_takeoff_weight_lb=float(d.get("max_takeoff_weight_lb", 0.0) or 0.0),
    )


def weight_to_dict(inp: WeightInput) -> Dict[str, Any]:
    """Serialize a :class:`WeightInput` to JSON-friendly primitives."""
    out: Dict[str, Any] = {}
    if inp.estimation is not None:
        est = asdict(inp.estimation)
        est["engine_weight_type"] = inp.estimation.engine_weight_type.value
        out["estimation"] = est
    out["items"] = [_mass_item_to_dict(it) for it in inp.items]
    if inp.envelope is not None:
        out["envelope"] = asdict(inp.envelope)
    if inp.cg_cases:
        out["cg_cases"] = [_cg_case_to_dict(c) for c in inp.cg_cases]
    # The two design-weight SSOTs (G-4 / G-14). Written only when set, so a
    # project that predates them -- or a concept sketch that has not stated them
    # -- keeps the same bytes it had.
    if inp.max_landing_weight_lb:
        out["max_landing_weight_lb"] = inp.max_landing_weight_lb
    if inp.max_takeoff_weight_lb:
        out["max_takeoff_weight_lb"] = inp.max_takeoff_weight_lb
    return out



def _points(raw) -> List:
    """Coerce a list of JSON [x, y] arrays to (x, y) tuples."""
    return [tuple(p) for p in raw or []]


def _opt_float(raw) -> Optional[float]:
    """``float(raw)``, keeping ``None``/absent distinct from a numeric value."""
    return None if raw is None else float(raw)


def _surface_from_dict(d: Dict[str, Any]) -> SurfaceInput:
    return SurfaceInput(
        name=d["name"],
        leading_edge=_points(d.get("leading_edge")),
        trailing_edge=_points(d.get("trailing_edge")),
        symmetric=d.get("symmetric", True),
        elements=d.get("elements", 20),
        # v52: None = "not entered" (R-7c). The pre-v52 writer emitted the field
        # unconditionally, so a stored 0.25 carries no entered-ness information
        # -- it is read back as unset (any deliberately-entered non-default
        # value survives; an entered 0.25 was indistinguishable from the
        # default the day it was written, so nothing knowable is lost).
        ref_axis_pct=(lambda v: None if v == 0.25 else v)(
            _opt_float(d.get("ref_axis_pct"))),
        # None is meaningful (= "not entered" -> assumed default, M4-1), so an
        # absent/null key stays None rather than taking a numeric default here.
        front_spar_pct=_opt_float(d.get("front_spar_pct")),
        rear_spar_pct=_opt_float(d.get("rear_spar_pct")),
        sob_y_in=_opt_float(d.get("sob_y_in")),
    )


def _fuselage_outline_from_dict(d: Dict[str, Any]) -> FuselageOutline:
    return FuselageOutline(sections=[
        FuselageSection(x=s["x"], width=s["width"], height=s["height"],
                        z_centre=_opt_float(s.get("z_centre")))
        for s in d.get("sections", []) or []
    ])


def _landing_gear_from_dict(d: Dict[str, Any]) -> LandingGearGeometry:
    return LandingGearGeometry(
        main_gear=_gear_from_dict(d.get("main_gear") or {}),
        nose_gear=_gear_from_dict(d.get("nose_gear") or {}),
        tread_in=float(d.get("tread_in", 0.0) or 0.0),
    )


def geometry_from_dict(d: Dict[str, Any]) -> GeometryInput:
    """Build the unified :class:`GeometryInput` from a plain dict (Step G1/G6).

    Reads the **current** schema only. A pre-v25 top-level ``"configuration"``
    block, pre-v27 top-level ``tail_loads``/``vtail_loads`` and a pre-v28 gear on
    ``landing`` were all folded into this slice by
    :mod:`sloads.migrations` before this function sees the dict, so the three
    ``legacy_*`` parameters this used to take are gone (M4-10).

    ``surfaces`` is the WINGGEOM planform list; ``parametric`` the embedded
    :class:`LayoutInput`; ``fuselage`` the body outline, defaulted from the
    parametric length/width/height scalars when the file predates it;
    ``empennage`` (Step G6) the single-source tail + elevator/rudder geometry.
    """
    parametric_raw = d.get("parametric")
    parametric = configuration_from_dict(parametric_raw) if parametric_raw else None

    fuselage_raw = d.get("fuselage")
    fuselage: Optional[FuselageOutline]
    if fuselage_raw:
        fuselage = _fuselage_outline_from_dict(fuselage_raw)
    elif parametric is not None:
        fuselage = default_fuselage_outline(parametric)
    else:
        fuselage = None

    emp_raw = d.get("empennage") or {}
    htail_raw, vtail_raw = emp_raw.get("htail"), emp_raw.get("vtail")
    empennage = None
    if htail_raw is not None or vtail_raw is not None:
        empennage = EmpennageInput(
            htail=tail_loads_from_dict(htail_raw) if htail_raw else None,
            vtail=vtail_loads_from_dict(vtail_raw) if vtail_raw else None,
        )

    # Step G6b: landing-gear geometry from d["landing_gear"] (a pre-v28 file's
    # top-level "landing" gear was moved here by the v28 migration hop), else
    # synthesized from the retired coarse LayoutInput gear fields (static axle X
    # + tread only) for a file that only ever had those.
    landing_gear = None
    lg_raw = d.get("landing_gear")
    if lg_raw is not None:
        landing_gear = _landing_gear_from_dict(lg_raw)
    elif parametric_raw and any(parametric_raw.get(k) for k in
                                ("main_gear_x", "nose_gear_x", "track", "gear_height")):
        gz = float(parametric_raw.get("root_waterline_z", 0.0) or 0.0) \
            - float(parametric_raw.get("gear_height", 0.0) or 0.0)
        landing_gear = LandingGearGeometry(
            main_gear=LandingGearInput(axle_static=(float(parametric_raw.get("main_gear_x", 0.0) or 0.0), gz)),
            nose_gear=LandingGearInput(axle_static=(float(parametric_raw.get("nose_gear_x", 0.0) or 0.0), gz)),
            tread_in=float(parametric_raw.get("track", 0.0) or 0.0),
        )

    return GeometryInput(
        surfaces=[_surface_from_dict(s) for s in d.get("surfaces", []) or []],
        parametric=parametric,
        fuselage=fuselage,
        empennage=empennage,
        landing_gear=landing_gear,
    )


def geometry_to_dict(inp: GeometryInput) -> Dict[str, Any]:
    """Serialize the unified :class:`GeometryInput` to JSON-friendly primitives."""
    out: Dict[str, Any] = {
        "surfaces": [
            {
                "name": s.name,
                "leading_edge": [list(p) for p in s.leading_edge],
                "trailing_edge": [list(p) for p in s.trailing_edge],
                "symmetric": s.symmetric,
                "elements": s.elements,
                "ref_axis_pct": s.ref_axis_pct,
                # Written even when None so "not entered" round-trips explicitly
                # (the assumed-default provenance, M4-1).
                "front_spar_pct": s.front_spar_pct,
                "rear_spar_pct": s.rear_spar_pct,
                "sob_y_in": s.sob_y_in,
            }
            for s in inp.surfaces
        ]
    }
    if inp.parametric is not None:
        out["parametric"] = configuration_to_dict(inp.parametric)
    if inp.fuselage is not None:
        out["fuselage"] = {
            "sections": [
                {"x": s.x, "width": s.width, "height": s.height,
                 "z_centre": s.z_centre}
                for s in inp.fuselage.sections
            ]
        }
    if inp.empennage is not None:
        emp: Dict[str, Any] = {}
        if inp.empennage.htail is not None:
            emp["htail"] = tail_loads_to_dict(inp.empennage.htail)
        if inp.empennage.vtail is not None:
            emp["vtail"] = vtail_loads_to_dict(inp.empennage.vtail)
        if emp:
            out["empennage"] = emp
    if inp.landing_gear is not None:
        lg = inp.landing_gear
        out["landing_gear"] = {
            "main_gear": _gear_to_dict(lg.main_gear),
            "nose_gear": _gear_to_dict(lg.nose_gear),
            "tread_in": lg.tread_in,
        }
    return out


# --------------------------------------------------------------------------- #
# Aero slice <-> dict
# --------------------------------------------------------------------------- #
def _aero_surface_from_dict(d: Dict[str, Any]) -> AeroSurfaceInput:
    return AeroSurfaceInput(
        name=d.get("name", "wing"),
        section_slope=d.get("section_slope", 0.1075),
        taper_ratio=d.get("taper_ratio", 0.0),
        tip_ratio=d.get("tip_ratio", 0.0),
        tau=d.get("tau"),
        twist=_points(d.get("twist")),
        target_cl=d.get("target_cl", 1.0),
        profile_drag=_points(d.get("profile_drag")),
        section_cm=_points(d.get("section_cm")),
        sweep_deg=d.get("sweep_deg", 0.0),
        design_mach=d.get("design_mach", 0.0),
    )


def aero_from_dict(d: Dict[str, Any]) -> AeroInput:
    """Build an :class:`AeroInput` from a plain dict (tuple coercion for twist)."""
    return AeroInput(surfaces=[_aero_surface_from_dict(s) for s in d.get("surfaces", []) or []])


def aero_to_dict(inp: AeroInput) -> Dict[str, Any]:
    """Serialize an :class:`AeroInput` to JSON-friendly primitives."""
    return {
        "surfaces": [
            {
                "name": s.name,
                "section_slope": s.section_slope,
                "taper_ratio": s.taper_ratio,
                "tip_ratio": s.tip_ratio,
                "tau": s.tau,
                "twist": [list(p) for p in s.twist],
                "target_cl": s.target_cl,
                "profile_drag": [list(p) for p in s.profile_drag],
                "section_cm": [list(p) for p in s.section_cm],
                "sweep_deg": s.sweep_deg,
                "design_mach": s.design_mach,
            }
            for s in inp.surfaces
        ]
    }


# --------------------------------------------------------------------------- #
# Speeds slice <-> dict
# --------------------------------------------------------------------------- #
def speeds_from_dict(d: Dict[str, Any]) -> StructuralSpeedsInput:
    """Build a :class:`StructuralSpeedsInput` from a plain dict (nested MACHLIM)."""
    d = dict(d)
    ml = d.pop("mach_limit", None)
    # Stall speeds are derived from CLmax (M1-1b); drop any legacy scalar keys.
    d.pop("stall_clean_kt", None)
    d.pop("stall_flap_kt", None)
    mach_limit = MachLimitInput(**_filtered(MachLimitInput, ml)) if ml else None
    # F25-2: an unrecognised dive-speed basis is an error, not a silent fallback --
    # quietly reading it as "speed_ratio" would apply the 1.25*VC floor to a project
    # whose author asked for the Mach-margin route, which is the very defect F25-2
    # fixes. VdBasis(...) raises ValueError naming the bad value.
    if d.get("vd_basis") is not None:
        d["vd_basis"] = VdBasis(d["vd_basis"])
    return StructuralSpeedsInput(mach_limit=mach_limit, **_filtered(StructuralSpeedsInput, d))


def speeds_to_dict(inp: StructuralSpeedsInput) -> Dict[str, Any]:
    """Serialize a :class:`StructuralSpeedsInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Flight-loads slice <-> dict (FLTLOADS input)
# --------------------------------------------------------------------------- #
def _coeff5(raw) -> tuple:
    """Coerce a 5-element coefficient list to a tuple, padding short lists with 0."""
    vals = list(raw or [])
    vals = (vals + [0.0] * 5)[:5]
    return tuple(float(v) for v in vals)


def _aero_coeff_set_from_dict(d: Dict[str, Any]) -> AeroCoeffSet:
    # stall_cl/neg_stall_cl are derived from the parent's clmax_* (M1-1b); accept
    # a legacy per-config value if present, else default and let __post_init__ sync.
    return AeroCoeffSet(
        name=d.get("name", "CRUISE"),
        stall_cl=d.get("stall_cl", 0.0),
        neg_stall_cl=d.get("neg_stall_cl", 0.0),
        lift=_coeff5(d.get("lift")),
        drag=_coeff5(d.get("drag")),
        moment=_coeff5(d.get("moment")),
        flaps_down=d.get("flaps_down", False),
    )


def _aero_coeff_set_to_dict(c: AeroCoeffSet) -> Dict[str, Any]:
    # stall_cl/neg_stall_cl are the FLTLOADS balance clamp -- authored per config and
    # round-tripped (they can differ slightly from the parent's stall-speed clmax_*;
    # see AeroCoefficientsInput.__post_init__). M1-1b: the *stall-speed* source moved
    # to the parent clmax_*; the FLTLOADS clamp stays here.
    return {
        "name": c.name,
        "stall_cl": c.stall_cl,
        "neg_stall_cl": c.neg_stall_cl,
        "lift": list(c.lift),
        "drag": list(c.drag),
        "moment": list(c.moment),
        "flaps_down": c.flaps_down,
    }


def flight_loads_from_dict(d: Dict[str, Any]) -> FlightLoadsInput:
    """Build a :class:`FlightLoadsInput` from a plain dict."""
    return FlightLoadsInput(
        xtc=d.get("xtc", 0.0),
        xtf=d.get("xtf", 0.0),
        mn=d.get("mn", 0.1),
        altitudes_ft=[float(a) for a in d.get("altitudes_ft", [0.0]) or [0.0]],
    )


def flight_loads_to_dict(inp: FlightLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`FlightLoadsInput` to JSON-friendly primitives.

    Note 33 (DS-1): ``mac``/``wing_area_sqft``/``xw``/``zw`` are no longer fields —
    they are read from the planform at their point of use. They were never written,
    so a legacy file's stored copies are ignored exactly as they already were, and
    save->reload stays a no-op.
    """
    return {
        "xtc": inp.xtc,
        "xtf": inp.xtf,
        "mn": inp.mn,
        "altitudes_ft": list(inp.altitudes_ft),
    }


# --------------------------------------------------------------------------- #
# Aero coefficients slice <-> dict (Project.aero_coeffs, Step D4.1)
# --------------------------------------------------------------------------- #
def aero_coefficients_from_dict(d: Dict[str, Any]) -> AeroCoefficientsInput:
    """Build an :class:`AeroCoefficientsInput` from a plain dict."""
    fm = d.get("fuselage_moment")
    lb = d.get("lateral_body_aero")
    return AeroCoefficientsInput(
        cruise=_aero_coeff_set_from_dict(d["cruise"]) if d.get("cruise") else None,
        flaps_down=_aero_coeff_set_from_dict(d["flaps_down"]) if d.get("flaps_down") else None,
        clmax_clean=float(d.get("clmax_clean", 0.0)),
        clmax_clean_neg=float(d.get("clmax_clean_neg", 0.0)),
        clmax_flap=float(d.get("clmax_flap", 0.0)),
        fuselage_moment=(
            FuselageMomentInput(
                enabled=bool(fm.get("enabled", False)),
                d_cm_dalpha=float(fm.get("d_cm_dalpha", 0.0)),
            )
            if fm else None
        ),
        lateral_body_aero=(
            LateralBodyAeroInput(
                enabled=bool(lb.get("enabled", False)),
                cy_beta=None if lb.get("cy_beta") is None else float(lb["cy_beta"]),
                cn_beta=None if lb.get("cn_beta") is None else float(lb["cn_beta"]),
            )
            if lb else None
        ),
    )


def aero_coefficients_to_dict(inp: AeroCoefficientsInput) -> Dict[str, Any]:
    """Serialize an :class:`AeroCoefficientsInput` to JSON-friendly primitives."""
    out: Dict[str, Any] = {}
    if inp.clmax_clean:
        out["clmax_clean"] = inp.clmax_clean
    if inp.clmax_clean_neg:
        out["clmax_clean_neg"] = inp.clmax_clean_neg
    if inp.clmax_flap:
        out["clmax_flap"] = inp.clmax_flap
    if inp.cruise is not None:
        out["cruise"] = _aero_coeff_set_to_dict(inp.cruise)
    if inp.flaps_down is not None:
        out["flaps_down"] = _aero_coeff_set_to_dict(inp.flaps_down)
    if inp.fuselage_moment is not None:
        out["fuselage_moment"] = {
            "enabled": inp.fuselage_moment.enabled,
            "d_cm_dalpha": inp.fuselage_moment.d_cm_dalpha,
        }
    if inp.lateral_body_aero is not None:
        out["lateral_body_aero"] = {
            "enabled": inp.lateral_body_aero.enabled,
            "cy_beta": inp.lateral_body_aero.cy_beta,
            "cn_beta": inp.lateral_body_aero.cn_beta,
        }
    return out


def _safety_factor(d: Dict[str, Any]) -> float:
    """The persisted per-case limit->ultimate factor, coerced to the valid band
    (defect M4-14).

    The field is hand-editable (Project JSON Editor / the file itself) and scales
    every exported ULTIMATE load, so a corrupt value must never pass through:
    anything non-numeric (null, string, bool, NaN/inf) or outside the legal
    **[1.0, ULTIMATE_FACTOR]** band (14 CFR 23.303; a case already at ultimate is
    1.0) falls back to the conservative default ``ULTIMATE_FACTOR`` — a low value
    would silently under-scale cards still labelled ULTIMATE, including on the
    headless CLI export path where no GUI warning can surface.
    ``validation._check_safety_factors`` is the advisory companion for in-session
    values, and the Project JSON Editor warns on the raw dict at Apply (both via
    the shared ``validation.safety_factor_valid``)."""
    v = d.get("safety_factor", ULTIMATE_FACTOR)
    return float(v) if safety_factor_valid(v) else ULTIMATE_FACTOR


# --------------------------------------------------------------------------- #
# Envelope slice <-> dict (FLTLOADS result)
# --------------------------------------------------------------------------- #
def _critical_condition_from_dict(d: Dict[str, Any]) -> CriticalCondition:
    return CriticalCondition(
        component=d.get("component", ""),
        label=d.get("label", ""),
        far_reference=d.get("far_reference", ""),
        case=d.get("case"),
        loads=[LoadValue(**_filtered(LoadValue, v)) for v in d.get("loads", []) or []],
        lt25=d.get("lt25"),
        lt50=d.get("lt50"),
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        note=d.get("note", ""),
        safety_factor=_safety_factor(d),
        beta_deg=d.get("beta_deg"),
        cy_beta_fin=d.get("cy_beta_fin"),
        cn_beta_fin=d.get("cn_beta_fin"),
    )


def _vn_point_from_dict(d: Dict[str, Any]) -> VnPoint:
    d = dict(d)
    ref = d.pop("case_ref", None)
    return VnPoint(case_ref=_case_ref_from_dict(ref), **_filtered(VnPoint, d))


def _critical_from_dict(d: Dict[str, Any]) -> CriticalLoadSet:
    """The persisted critical-load set, with stale ``selected_case_ids`` dropped
    **loudly** (schema v39, M4-2 decision 6).

    ``selected_case_ids`` is the one persisted field that references case-id
    *strings*, so the M4-2 renumbering (SELECT's retired W-40.. band, ONENGOUT's
    move to VT-30..) can leave a saved project pointing at ids that no longer
    exist. An id that matches no condition never filtered anything --
    ``CriticalLoadSet.selected()`` and ``filter_by_selected_case_ids`` simply do
    not match it -- so the stale entry silently *widened* the governing-set
    export. Dropping it changes nothing about the result and saying so is the
    only part that is new.

    Filtering is skipped entirely when no condition carries a ``case_ref`` (a
    pre-D1 file, or a set persisted before the ids were minted): there is nothing
    to validate against, and dropping every id there would be the same silent
    widening in the other direction.
    """
    conditions = [_critical_condition_from_dict(c) for c in d.get("conditions", []) or []]
    ids = [str(i) for i in d.get("selected_case_ids", []) or []]
    known = {c.case_ref.case_id for c in conditions if c.case_ref is not None}
    if ids and known:
        stale = [i for i in ids if i not in known]
        if stale:
            warnings.warn(
                "dropping selected_case_ids that match no critical condition: "
                + ", ".join(stale)
                + " (case ids were renumbered by schema v39 / M4-2; re-pick the "
                  "governing set on the Critical Loads page)",
                stacklevel=2,
            )
            ids = [i for i in ids if i in known]
    return CriticalLoadSet(conditions=conditions, selected_case_ids=ids)


def envelope_from_dict(d: Dict[str, Any]) -> EnvelopeResult:
    """Build an :class:`EnvelopeResult` from a plain dict (the persisted V-n data)."""
    critical = d.get("critical")
    return EnvelopeResult(
        vn=[_vn_point_from_dict(p) for p in d.get("vn", []) or []],
        tail_balance=[TailBalanceLoad(**_filtered(TailBalanceLoad, t))
                      for t in d.get("tail_balance", []) or []],
        critical=_critical_from_dict(critical) if critical else None,
    )


def envelope_to_dict(inp: EnvelopeResult) -> Dict[str, Any]:
    """Serialize an :class:`EnvelopeResult` to JSON-friendly primitives."""
    out: Dict[str, Any] = {
        "vn": [asdict(p) for p in inp.vn],
        "tail_balance": [asdict(t) for t in inp.tail_balance],
    }
    if inp.critical is not None:
        out["critical"] = asdict(inp.critical)
    return out


# --------------------------------------------------------------------------- #
# Mass slice <-> dict (WTONECG result)
# --------------------------------------------------------------------------- #
def mass_from_dict(d: Dict[str, Any]) -> MassResult:
    """Build a :class:`MassResult` from a plain dict (the persisted mass props)."""
    return MassResult(cases=[MassCase(**_filtered(MassCase, c)) for c in d.get("cases", []) or []])


def mass_to_dict(inp: MassResult) -> Dict[str, Any]:
    """Serialize a :class:`MassResult` to JSON-friendly primitives."""
    return {"cases": [asdict(c) for c in inp.cases]}


# --------------------------------------------------------------------------- #
# Fuselage-mass slice <-> dict (fuselage net-load input)
# --------------------------------------------------------------------------- #
def fuselage_mass_from_dict(d: Dict[str, Any]) -> FuselageMassInput:
    """Build a :class:`FuselageMassInput` from a plain dict."""
    return FuselageMassInput(
        stations=[FuselageStation(**_filtered(FuselageStation, s))
                  for s in d.get("stations", []) or []],
        ref_waterline=d.get("ref_waterline", 0.0),
        stations_are_override=bool(d.get("stations_are_override", False)),
    )


def fuselage_mass_to_dict(inp: FuselageMassInput) -> Dict[str, Any]:
    """Serialize a :class:`FuselageMassInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# SELECT search-input slice <-> dict
# --------------------------------------------------------------------------- #
def select_input_from_dict(d: Dict[str, Any]) -> SelectInput:
    """Build a :class:`SelectInput` from a plain dict."""
    return SelectInput(**_filtered(SelectInput, d))


def select_input_to_dict(inp: SelectInput) -> Dict[str, Any]:
    """Serialize a :class:`SelectInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Rational tail-loads input slice <-> dict (SELECT)
# --------------------------------------------------------------------------- #
def tail_loads_from_dict(d: Dict[str, Any]) -> TailLoadsInput:
    """Build a :class:`TailLoadsInput` from a plain dict."""
    return TailLoadsInput(**_filtered(TailLoadsInput, d))


def tail_loads_to_dict(inp: TailLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`TailLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Rational vertical-tail-loads input slice <-> dict (SELECT)
# --------------------------------------------------------------------------- #
def vtail_loads_from_dict(d: Dict[str, Any]) -> VTailLoadsInput:
    """Build a :class:`VTailLoadsInput` from a plain dict."""
    return VTailLoadsInput(**_filtered(VTailLoadsInput, d))


def vtail_loads_to_dict(inp: VTailLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`VTailLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# One-engine-out input slice <-> dict (ONENGOUT)
# --------------------------------------------------------------------------- #
def one_engine_out_from_dict(d: Dict[str, Any]) -> OneEngineOutInput:
    """Build a :class:`OneEngineOutInput` from a plain dict."""
    return OneEngineOutInput(**_filtered(OneEngineOutInput, d))


def one_engine_out_to_dict(inp: OneEngineOutInput) -> Dict[str, Any]:
    """Serialize a :class:`OneEngineOutInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Landing / ground-load input slice <-> dict (LGFACTOR + LANDLOAD)
# --------------------------------------------------------------------------- #
def _gear_from_dict(d: Dict[str, Any]) -> LandingGearInput:
    kw = _filtered(LandingGearInput, d)
    for axle in ("axle_compressed", "axle_static", "axle_extended"):
        if axle in kw and kw[axle] is not None:
            kw[axle] = tuple(kw[axle])
    if kw.get("attach") is not None:
        kw["attach"] = tuple(kw["attach"])
    # G-2: absent stays ``None`` -- "carrier not stated" is a distinct state that
    # the ground export refuses on, not a value to default.
    carrier = d.get("carrier")
    kw["carrier"] = GearCarrier(carrier) if carrier else None
    return LandingGearInput(**kw)


def _gear_to_dict(g: LandingGearInput) -> Dict[str, Any]:
    """Serialize one leg; ``carrier`` is written only when stated (G-2)."""
    out = asdict(g)
    out["carrier"] = g.carrier.value if g.carrier is not None else None
    if out["carrier"] is None:
        out.pop("carrier")
    if tuple(out.get("attach") or ()) == (0.0, 0.0, 0.0):
        out.pop("attach", None)
    # G-12a: the same "written only when stated" rule. ``0.0`` is *not stated*,
    # and a project that never entered a leg weight should not gain a field
    # claiming it weighs nothing.
    if not out.get("weight_lb"):
        out.pop("weight_lb", None)
    return out


def landing_from_dict(d: Dict[str, Any]) -> LandingInput:
    """Build a :class:`LandingInput` from a plain dict (the non-geometry LANDLOAD
    params; the weight/CG cases and both design weights left this slice at
    G-3b/G-4/G-14). Step G6b: the gear geometry (``main_gear``/``nose_gear``/
    ``tread_in``) lives in ``geometry.landing_gear``; note 33 (DS-1) removed the
    slice copies it used to be synced onto, so ``_filtered`` drops a legacy file's
    keys on its own and the explicit exclusion is no longer needed. A legacy file's
    top-level gear is migrated into geometry by :func:`geometry_from_dict`."""
    return LandingInput(**_filtered(LandingInput, d))


def landing_to_dict(inp: LandingInput) -> Dict[str, Any]:
    """Serialize a :class:`LandingInput` (Step G6b: the gear geometry
    ``main_gear``/``nose_gear``/``tread_in`` is written under
    ``geometry.landing_gear``, not here -- the single stored home). Step M2-6:
    Note 33 (DS-1): the gear geometry and ``wing_area_sqft`` are not fields on this
    slice any more — the gear lives in ``geometry.landing_gear`` and the area is read
    off the wing planform — so there is nothing left to pop."""
    return asdict(inp)


def safety_factors_from_dict(d: Dict[str, Any]) -> SafetyFactorPolicyInput:
    """Build a :class:`SafetyFactorPolicyInput` (M4-8 / G-11) from a plain dict.

    Only *overrides* are persisted -- the governing table's derived rows are code
    (:mod:`sloads.safety_factors`), so a project file records deviations, never the
    regulation. Reading it back is therefore a no-op for every project that has
    none, which is every shipped fixture."""
    return SafetyFactorPolicyInput(
        overrides=[SafetyFactorOverride(**_filtered(SafetyFactorOverride, o))
                   for o in d.get("overrides", []) or []])


def safety_factors_to_dict(inp: SafetyFactorPolicyInput) -> Dict[str, Any]:
    """Serialize the safety-factor override layer."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Control-surface load input slices <-> dict (AILERON / FLAPLOAD / TABLOADS)
# --------------------------------------------------------------------------- #
def aileron_loads_from_dict(d: Dict[str, Any]) -> AileronLoadsInput:
    """Build an :class:`AileronLoadsInput` from a plain dict."""
    return AileronLoadsInput(**_filtered(AileronLoadsInput, d))


def aileron_loads_to_dict(inp: AileronLoadsInput) -> Dict[str, Any]:
    """Serialize an :class:`AileronLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


def flap_loads_from_dict(d: Dict[str, Any]) -> FlapLoadsInput:
    """Build a :class:`FlapLoadsInput` from a plain dict."""
    return FlapLoadsInput(**_filtered(FlapLoadsInput, d))


def flap_loads_to_dict(inp: FlapLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`FlapLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


def tab_loads_from_dict(d: Dict[str, Any]) -> TabLoadsInput:
    """Build a :class:`TabLoadsInput` from a plain dict (nested ``tabs``)."""
    tabs = [TabSpec(**_filtered(TabSpec, t)) for t in d.get("tabs", []) or []]
    return TabLoadsInput(tabs=tabs)


def tab_loads_to_dict(inp: TabLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`TabLoadsInput` to JSON-friendly primitives."""
    return {"tabs": [asdict(t) for t in inp.tabs]}


# --------------------------------------------------------------------------- #
# Wing-mass slice <-> dict (WINGINER input)
# --------------------------------------------------------------------------- #
def wing_mass_from_dict(d: Dict[str, Any]) -> WingMassInput:
    """Build a :class:`WingMassInput` from a plain dict."""
    return WingMassInput(
        panel_weight_lb=d.get("panel_weight_lb", 0.0),
        tip_root_density_ratio=d.get("tip_root_density_ratio", 1.0),
        inboard_rib_y=d.get("inboard_rib_y", 0.0),
        surface=d.get("surface", "wing"),
        concentrated=[ConcentratedWeight(**_filtered(ConcentratedWeight, c))
                      for c in d.get("concentrated", []) or []],
        cases=[WingLoadCase(**_filtered(WingLoadCase, c)) for c in d.get("cases", []) or []],
    )


def wing_mass_to_dict(inp: WingMassInput) -> Dict[str, Any]:
    """Serialize a :class:`WingMassInput` to JSON-friendly primitives.

    Note 33 (DS-1): ``dihedral_deg``/``wrp_waterline`` are no longer fields at all
    — the wing plane is resolved at its point of use from the parametric wing
    (:func:`sloads.derived_geometry.wing_plane`). They were never written, so a
    legacy file carrying them still loads unchanged: the keys are simply ignored,
    as they already were."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Loads slice <-> dict (WINGINER / NETLOADS result)
# --------------------------------------------------------------------------- #
def _wing_load_result_from_dict(d: Dict[str, Any]) -> WingLoadResult:
    return WingLoadResult(
        case=d.get("case", ""),
        nz=d.get("nz", 0.0),
        nx=d.get("nx", 0.0),
        stations=[WingStationLoad(**_filtered(WingStationLoad, s))
                  for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        safety_factor=_safety_factor(d),
        torsion_axis=d.get("torsion_axis", "25% chord"),
    )


def _body_load_result_from_dict(d: Dict[str, Any]) -> BodyLoadResult:
    return BodyLoadResult(
        case=d.get("case", ""),
        stations=[BodyStationLoad(**_filtered(BodyStationLoad, s))
                  for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        safety_factor=_safety_factor(d),
        # Moment-closure fields (M4-1). An older file lacks them: m_unbalanced
        # defaults to 0.0 and the fitting loads to None, exactly as a
        # closure-artifact result serializes.
        m_unbalanced=float(d.get("m_unbalanced", 0.0) or 0.0),
        r_front=_opt_float(d.get("r_front")),
        r_rear=_opt_float(d.get("r_rear")),
        x_front=_opt_float(d.get("x_front")),
        x_rear=_opt_float(d.get("x_rear")),
        spars_assumed=bool(d.get("spars_assumed", False)),
        closure_artifact=bool(d.get("closure_artifact", False)),
    )


def _tail_chord_result_from_dict(d: Dict[str, Any]) -> TailChordResult:
    return TailChordResult(
        case=d.get("case", ""),
        component=d.get("component", ""),
        lt25=d.get("lt25", 0.0),
        lt50=d.get("lt50", 0.0),
        stations=[TailChordStation(**_filtered(TailChordStation, s))
                  for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        far_reference=d.get("far_reference", ""),
        safety_factor=_safety_factor(d),
    )


def _control_surface_result_from_dict(d: Dict[str, Any]) -> ControlSurfaceLoadResult:
    return ControlSurfaceLoadResult(
        surface=d.get("surface", ""),
        case=d.get("case", ""),
        load_lb=d.get("load_lb", 0.0),
        v_kt=d.get("v_kt", 0.0),
        stations=[ControlSurfaceStation(**_filtered(ControlSurfaceStation, s))
                  for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        safety_factor=_safety_factor(d),
    )


def _tail_span_result_from_dict(d: Dict[str, Any]) -> TailSpanResult:
    """Read one spanwise empennage result (plan 09 T1).

    Tolerant like its siblings: a file written before the tail path existed has
    no such entry at all, and one written by a later build carrying extra keys is
    filtered rather than rejected.
    """
    return TailSpanResult(
        case=d.get("case", ""),
        component=d.get("component", "htail"),
        stations=[WingStationLoad(**_filtered(WingStationLoad, s))
                  for s in d.get("stations", []) or []],
        lt25=d.get("lt25", 0.0) or 0.0,
        lt50=d.get("lt50", 0.0) or 0.0,
        n_case=d.get("n_case", 0.0) or 0.0,
        surface_weight_lb=d.get("surface_weight_lb", 0.0) or 0.0,
        attachment_y=[float(v) for v in d.get("attachment_y", []) or []],
        attachment_assumed=bool(d.get("attachment_assumed", False)),
        attachment_basis=d.get("attachment_basis", ""),
        rh_scale=d.get("rh_scale", 1.0),
        lh_scale=d.get("lh_scale", 1.0),
        planform_assumed=bool(d.get("planform_assumed", False)),
        control_load_mode=d.get("control_load_mode", "smeared"),
        inertia_modelled=bool(d.get("inertia_modelled", True)),
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        safety_factor=_safety_factor(d),
        torsion_axis=d.get("torsion_axis", "25% chord"),
        notes=list(d.get("notes", []) or []),
    )


def loads_from_dict(d: Dict[str, Any]) -> LoadsResult:
    """Build a :class:`LoadsResult` from a plain dict (the persisted loads)."""
    return LoadsResult(
        wing_air=[_wing_load_result_from_dict(r) for r in d.get("wing_air", []) or []],
        wing_inertia=[_wing_load_result_from_dict(r) for r in d.get("wing_inertia", []) or []],
        wing_net=[_wing_load_result_from_dict(r) for r in d.get("wing_net", []) or []],
        body_net=[_body_load_result_from_dict(r) for r in d.get("body_net", []) or []],
        tail_chordwise=[_tail_chord_result_from_dict(r) for r in d.get("tail_chordwise", []) or []],
        control_surface=[_control_surface_result_from_dict(r)
                         for r in d.get("control_surface", []) or []],
        htail_span=[_tail_span_result_from_dict(r) for r in d.get("htail_span", []) or []],
        vtail_span=[_tail_span_result_from_dict(r) for r in d.get("vtail_span", []) or []],
    )


def loads_to_dict(inp: LoadsResult) -> Dict[str, Any]:
    """Serialize a :class:`LoadsResult` to JSON-friendly primitives."""
    return {
        "wing_air": [asdict(r) for r in inp.wing_air],
        "wing_inertia": [asdict(r) for r in inp.wing_inertia],
        "wing_net": [asdict(r) for r in inp.wing_net],
        "body_net": [asdict(r) for r in inp.body_net],
        "tail_chordwise": [asdict(r) for r in inp.tail_chordwise],
        "control_surface": [asdict(r) for r in inp.control_surface],
        "htail_span": [asdict(r) for r in inp.htail_span],
        "vtail_span": [asdict(r) for r in inp.vtail_span],
    }


# --------------------------------------------------------------------------- #
# Configuration & layout slice <-> dict (LayoutInput)
# --------------------------------------------------------------------------- #
def configuration_from_dict(d: Dict[str, Any]) -> LayoutInput:
    """Build a :class:`LayoutInput` from a plain dict.

    Every field is an optional scalar with a default, so unknown keys are ignored
    and missing keys fall back to the dataclass default (additive forward-compat);
    a file with no ``tail_type`` defaults to ``TailType.CONVENTIONAL``.
    """
    kwargs = _filtered(LayoutInput, d)
    if "tail_type" in kwargs:
        kwargs["tail_type"] = TailType(kwargs["tail_type"])
    return LayoutInput(**kwargs)


def configuration_to_dict(inp: LayoutInput) -> Dict[str, Any]:
    """Serialize a :class:`LayoutInput` to JSON-friendly primitives.

    Step M2-6: the fuselage ``fuselage_length``/``fuselage_width``/``fuselage_height``
    are a derived read-only summary of the ``GeometryInput.fuselage`` outline and are
    not written; ``configuration_from_dict`` still reads them so an older file with only
    the scalars (no outline) migrates via ``default_fuselage_outline`` on load."""
    out = {**asdict(inp), "tail_type": inp.tail_type.value}
    for key in ("fuselage_length", "fuselage_width", "fuselage_height"):
        out.pop(key, None)
    return out


# --------------------------------------------------------------------------- #
# Project <-> JSON
# --------------------------------------------------------------------------- #
def project_from_dict(d: Dict[str, Any]) -> Project:
    """Build a :class:`Project` from a dict of any historical schema version.

    The dict is first normalised to the current shape by
    :func:`sloads.migrations.migrate` -- a chain of small ``dict -> dict`` hops,
    one per version that changed the file's *shape* (M4-10). Everything below
    therefore reads the **current** schema only; there are no ``legacy_*``
    parameters and no key-presence sniffing left in the readers.

    A bare :class:`EngineInput` file (the Phase-0 ``engloads`` era, before
    ``Project`` existed) is still accepted, discriminated by
    :func:`sloads.migrations.is_project_dict` rather than by enumerating every
    slice name -- so adding a slice to ``Project`` can no longer silently
    downgrade a real project to an engine-only read.
    """
    if not is_project_dict(d):
        # The whole file is just the engine slice.
        return Project(name="", engines=[engine_from_dict(d)],
                       engine_layout=EngineLayout.SINGLE_NOSE)

    d = migrate(d)
    if True:
        weight = d.get("weight")
        geometry = d.get("geometry")
        speeds = d.get("speeds")
        aero = d.get("aero")
        aero_coeffs = d.get("aero_coeffs")
        flight_loads = d.get("flight_loads")
        envelope = d.get("envelope")
        mass = d.get("mass")
        wing_mass = d.get("wing_mass")
        fuselage_mass = d.get("fuselage_mass")
        select_input = d.get("select_input")
        aileron_loads = d.get("aileron_loads")
        flap_loads = d.get("flap_loads")
        tab_loads = d.get("tab_loads")
        one_engine_out = d.get("one_engine_out")
        landing = d.get("landing")
        safety_factors = d.get("safety_factors")
        loads = d.get("loads")
        engines, layout = _engines_from_dict(d)
        weight_slice = weight_from_dict(weight) if weight else None
        project = Project(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            name=d.get("name", ""),
            engineer=d.get("engineer", ""),
            date=d.get("date", ""),
            revision=d.get("revision", ""),
            checked_by=d.get("checked_by", ""),
            approved_by=d.get("approved_by", ""),
            description=d.get("description", ""),
            # v38: absent (every pre-v38 file) reads as Imperial, so an older
            # project's deliverables render exactly as they do today.
            unit_system=unit_system_from(d.get("unit_system")).value,
            engines=engines,
            engine_layout=layout,
            weight=weight_slice,
            geometry=geometry_from_dict(geometry) if geometry else None,
            speeds=speeds_from_dict(speeds) if speeds else None,
            aero=aero_from_dict(aero) if aero else None,
            aero_coeffs=aero_coefficients_from_dict(aero_coeffs) if aero_coeffs else None,
            flight_loads=flight_loads_from_dict(flight_loads) if flight_loads else None,
            envelope=envelope_from_dict(envelope) if envelope else None,
            mass=mass_from_dict(mass) if mass else None,
            wing_mass=wing_mass_from_dict(wing_mass) if wing_mass else None,
            tail_mass=[TailMassInput(**_filtered(TailMassInput, t))
                       for t in d.get("tail_mass", []) or []],
            fuselage_mass=fuselage_mass_from_dict(fuselage_mass) if fuselage_mass else None,
            select_input=select_input_from_dict(select_input) if select_input else None,
            # tail_loads / vtail_loads are not Project fields (Step G6); a pre-v27
            # file's top-level slices were folded into geometry.empennage by the
            # v27 migration hop before this reader ever saw the dict.
            aileron_loads=aileron_loads_from_dict(aileron_loads) if aileron_loads else None,
            flap_loads=flap_loads_from_dict(flap_loads) if flap_loads else None,
            tab_loads=tab_loads_from_dict(tab_loads) if tab_loads else None,
            one_engine_out=one_engine_out_from_dict(one_engine_out) if one_engine_out else None,
            landing=landing_from_dict(landing) if landing else None,
            # v46: absent (every pre-v46 file, and every shipped fixture) means no
            # override -- the governing table is the regulation's own factors.
            safety_factors=(safety_factors_from_dict(safety_factors)
                            if safety_factors else None),
            loads=loads_from_dict(loads) if loads else None,
            include_far25=bool(d.get("include_far25", False)),
        )
        # Step M2-6: fill the derived geometry copies (wing mac/S/xw/zw, wing-mass
        # dihedral/wrp, landing wing area, fuselage L/W/H summary) from the single
        # source now that every slice is present, so a freshly-loaded project reads
        # them correctly before any module runs (each module re-syncs defensively).
        from .derived_geometry import sync_geometry_derived
        sync_geometry_derived(project)
        return project


def _engines_from_dict(d: Dict[str, Any]):
    """Read the engine list + layout, accepting the legacy single-engine key."""
    if "engines" in d:
        engines = [engine_from_dict(e) for e in d.get("engines") or []]
        layout = d.get("engine_layout")
        layout = EngineLayout(layout) if layout else None
    elif d.get("engine"):
        engines = [engine_from_dict(d["engine"])]
        layout = EngineLayout.SINGLE_NOSE
    else:
        engines, layout = [], None
    return engines, layout


def project_to_dict(project: Project) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "schema_version": project.schema_version,
        "name": project.name,
    }
    if project.engineer:
        out["engineer"] = project.engineer
    if project.date:
        out["date"] = project.date
    # Document control (v36). Written only when set, so a project that never
    # filled them in round-trips byte-identically to a pre-v36 file.
    for _field in ("revision", "checked_by", "approved_by", "description"):
        _value = getattr(project, _field, "")
        if _value:
            out[_field] = _value
    # Deliverable unit preference (v38). Written only when it differs from the
    # default, on the same principle as the document-control fields above: a
    # project that never chose a system round-trips byte-identically to a pre-v38
    # file, and an absent key reads as Imperial.
    if getattr(project, "unit_system", "imperial") != "imperial":
        out["unit_system"] = project.unit_system
    if project.engines:
        out["engines"] = [engine_to_dict(e) for e in project.engines]
        if project.engine_layout is not None:
            out["engine_layout"] = project.engine_layout.value
    if project.weight is not None:
        out["weight"] = weight_to_dict(project.weight)
    if project.geometry is not None:
        out["geometry"] = geometry_to_dict(project.geometry)
    if project.speeds is not None:
        out["speeds"] = speeds_to_dict(project.speeds)
    if project.aero is not None:
        out["aero"] = aero_to_dict(project.aero)
    if project.aero_coeffs is not None:
        out["aero_coeffs"] = aero_coefficients_to_dict(project.aero_coeffs)
    if project.flight_loads is not None:
        out["flight_loads"] = flight_loads_to_dict(project.flight_loads)
    if project.envelope is not None:
        out["envelope"] = envelope_to_dict(project.envelope)
    if project.mass is not None:
        out["mass"] = mass_to_dict(project.mass)
    if project.wing_mass is not None:
        out["wing_mass"] = wing_mass_to_dict(project.wing_mass)
    # Written only when present, so a project with no empennage mass round-trips
    # byte-identically to a pre-v42 file.
    if project.tail_mass:
        out["tail_mass"] = [asdict(t) for t in project.tail_mass]
    if project.fuselage_mass is not None:
        out["fuselage_mass"] = fuselage_mass_to_dict(project.fuselage_mass)
    if project.select_input is not None:
        out["select_input"] = select_input_to_dict(project.select_input)
    # tail_loads / vtail_loads (Step G6) are serialized under geometry.empennage
    # (geometry_to_dict), not as top-level keys -- the single stored home.
    if project.aileron_loads is not None:
        out["aileron_loads"] = aileron_loads_to_dict(project.aileron_loads)
    if project.flap_loads is not None:
        out["flap_loads"] = flap_loads_to_dict(project.flap_loads)
    if project.tab_loads is not None:
        out["tab_loads"] = tab_loads_to_dict(project.tab_loads)
    if project.one_engine_out is not None:
        out["one_engine_out"] = one_engine_out_to_dict(project.one_engine_out)
    if project.landing is not None:
        out["landing"] = landing_to_dict(project.landing)
    # Written only when it carries something: an empty override layer and an
    # absent one are the same statement, and the fixtures must stay byte-for-byte.
    if project.safety_factors is not None and project.safety_factors.overrides:
        out["safety_factors"] = safety_factors_to_dict(project.safety_factors)
    if project.loads is not None:
        out["loads"] = loads_to_dict(project.loads)
    if project.include_far25:
        out["include_far25"] = True
    return out


def schema_status(version: int) -> Tuple[str, str]:
    """Classify an on-disk ``schema_version`` against the current one.

    Returns ``(status, message)`` where ``status`` is ``"ok"`` (same version,
    empty message), ``"newer"`` (file was written by a newer app version -- it
    still loads, but unrecognized fields are ignored) or ``"older"`` (the file's
    field-presence migration in :func:`project_from_dict` has already run; the
    caller should bump the loaded project's ``schema_version`` to
    :data:`SCHEMA_VERSION`). Pure -- the UI decides how to surface the message so
    calc stays free of Streamlit.
    """
    if version > SCHEMA_VERSION:
        return "newer", (
            f"This file was saved by a newer version (schema {version}; this app "
            f"supports {SCHEMA_VERSION}). Loading anyway -- unrecognized fields "
            "are ignored."
        )
    if version < SCHEMA_VERSION:
        return "older", f"Migrated from schema {version} to {SCHEMA_VERSION}."
    return "ok", ""


def load_project(path: str) -> Project:
    with open(path, "r", encoding="utf-8") as fh:
        return project_from_dict(json.load(fh))


def save_project(project: Project, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(project_to_dict(project), fh, indent=2)
        fh.write("\n")


def default_projects_dir() -> str:
    """The default local-disk projects directory (Step D3, decision D-3).

    Resolved from this file's location (repo root / ``projects``) rather than
    the process's current working directory, so it is stable no matter where
    ``streamlit run app/Home.py`` is invoked from. Git-ignored; not created
    until the first save.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, "projects")


def list_saved_projects(directory: str) -> List[Tuple[str, float]]:
    """``(filename, mtime)`` for every ``*.project.json`` in ``directory``,
    newest first. Returns ``[]`` if the directory does not exist yet."""
    if not os.path.isdir(directory):
        return []
    entries = []
    for fname in os.listdir(directory):
        if fname.endswith(".project.json"):
            mtime = os.path.getmtime(os.path.join(directory, fname))
            entries.append((fname, mtime))
    entries.sort(key=lambda e: e[1], reverse=True)
    return entries


def project_to_json(project: Project) -> str:
    """Project as a JSON string (for the GUI download button)."""
    return json.dumps(project_to_dict(project), indent=2)


# --------------------------------------------------------------------------- #
# CSV output
# --------------------------------------------------------------------------- #
def _as_conditions(results) -> List[ConditionResult]:
    """Accept a ModuleResult or a bare list of ConditionResult."""
    if isinstance(results, ModuleResult):
        return results.conditions
    return list(results)


def load_cases_csv(
    results,
    header_comment: str = "",
    *,
    system: UnitSystem = UnitSystem.IMPERIAL,
) -> str:
    """Render module results to a CSV string.

    Load-producing modules emit one row per structural load case; modules that
    emit a property table instead (e.g. the mass-properties modules, whose
    ``ConditionResult``s carry no load-case labels) fall back to the generic
    quantity-per-row table so they still export a useful CSV.

    ``header_comment`` (Step G8.3) is prepended verbatim -- pass
    ``report.csv_comment_block(project)`` so a CSV forwarded on its own still
    states that its loads are ULTIMATE and under what basis. The lines are
    ``#``-prefixed, so a reader needs ``comment="#"``; every in-repo reader was
    audited when this landed.

    ``system`` (M4-20 step 3) is the *deliverable* unit system: pass
    :attr:`~sloads.units.UnitSystem.SI` and the whole table is converted once,
    here, before rendering. This is the **only** unit conversion in the human
    export channel -- ``report/render.py`` stays unit-agnostic (it reads each
    ``LoadValue.units`` string and puts it in the column header), so nothing
    downstream needs to learn about unit systems. Callers therefore pass
    *Imperial* results plus ``system=``; passing already-converted results and
    ``system=SI`` would be a double conversion (silently a no-op today, because
    ``N`` has no SI mapping, but not something to rely on).
    """
    conditions = convert_results(_as_conditions(results), system)
    rows = load_cases_to_rows(conditions) if has_load_case_data(conditions) else results_to_rows(conditions)
    if not rows:
        return ""
    import io as _io

    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return header_comment + buf.getvalue()


def write_load_cases_csv(
    results,
    path: str,
    header_comment: str = "",
    *,
    system: UnitSystem = UnitSystem.IMPERIAL,
) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(load_cases_csv(results, header_comment=header_comment,
                                system=system))
