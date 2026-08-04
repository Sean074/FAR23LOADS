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
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from .constants import ULTIMATE_FACTOR
from .models import (
    SCHEMA_VERSION,
    AeroCoeffSet,
    AeroCoefficientsInput,
    AeroInput,
    AeroSurfaceInput,
    AileronLoadsInput,
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
    GeometryInput,
    LandingGearGeometry,
    LandingGearInput,
    LandingInput,
    SelectInput,
    TabLoadsInput,
    TabSpec,
    TailLoadsInput,
    TailType,
    VTailLoadsInput,
    LayoutInput,
    LoadsResult,
    LoadValue,
    MachLimitInput,
    MassCase,
    MassItem,
    MassItemKind,
    MassResult,
    ModuleResult,
    OneEngineOutInput,
    Project,
    Rotor,
    RotorDirection,
    RotorType,
    StructuralSpeedsInput,
    SurfaceInput,
    TailBalanceLoad,
    TailChordResult,
    TailChordStation,
    VnPoint,
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


def _rename_legacy_units(d: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Rename + rescale legacy unit-suffixed keys to canonical units (schema v24,
    Phase G0). ``mapping`` is ``{old_key: (new_key, factor)}``: a present ``old_key``
    becomes ``new_key = old_value * factor`` (feet->inches ``*12``, in^2->ft^2
    ``/144``). The new key wins if both are present. Returns ``d`` unchanged when no
    legacy key is present, so current files pay nothing."""
    if not any(k in d for k in mapping):
        return d
    out = dict(d)
    for old, (new, factor) in mapping.items():
        if old in out:
            val = out.pop(old)
            if new not in out and isinstance(val, (int, float)) and not isinstance(val, bool):
                out[new] = val * factor
    return out


# --------------------------------------------------------------------------- #
# Engine slice <-> dict
# --------------------------------------------------------------------------- #
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
def _mass_item_from_dict(d: Dict[str, Any]) -> MassItem:
    d = dict(d)
    kind = MassItemKind(d.pop("kind", "empty"))
    return MassItem(kind=kind, **_filtered(MassItem, d))


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
    cg_cases = [CgCase(**_filtered(CgCase, c)) for c in d.get("cg_cases", []) or []]
    return WeightInput(estimation=estimation, items=items, envelope=envelope, cg_cases=cg_cases)


def weight_to_dict(inp: WeightInput) -> Dict[str, Any]:
    """Serialize a :class:`WeightInput` to JSON-friendly primitives."""
    out: Dict[str, Any] = {}
    if inp.estimation is not None:
        est = asdict(inp.estimation)
        est["engine_weight_type"] = inp.estimation.engine_weight_type.value
        out["estimation"] = est
    out["items"] = [{**asdict(it), "kind": it.kind.value} for it in inp.items]
    if inp.envelope is not None:
        out["envelope"] = asdict(inp.envelope)
    if inp.cg_cases:
        out["cg_cases"] = [asdict(c) for c in inp.cg_cases]
    return out


def _legacy_cg_cases_from_flight_loads(flight_loads: Any) -> List[CgCase]:
    """Migrate pre-schema-19 files: ``flight_loads.cg_cases`` was the only copy
    of the loading scenarios before the Weight/CG Grid & Payload Cases page gave
    them a shared home on ``weight.cg_cases`` (Step D5). Returns ``[]`` when
    there is nothing to migrate, so older project files still load; the
    calc-facing ``FlightLoadsInput.cg_cases`` is unaffected either way."""
    if not flight_loads:
        return []
    return [CgCase(**_filtered(CgCase, c)) for c in flight_loads.get("cg_cases", []) or []]


# --------------------------------------------------------------------------- #
# Geometry slice <-> dict
# --------------------------------------------------------------------------- #
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
        ref_axis_pct=float(d.get("ref_axis_pct", 0.25)),
        # None is meaningful (= "not entered" -> assumed default, M4-1), so an
        # absent/null key stays None rather than taking a numeric default here.
        front_spar_pct=_opt_float(d.get("front_spar_pct")),
        rear_spar_pct=_opt_float(d.get("rear_spar_pct")),
    )


def _fuselage_outline_from_dict(d: Dict[str, Any]) -> FuselageOutline:
    return FuselageOutline(sections=[
        FuselageSection(x=s["x"], width=s["width"], height=s["height"])
        for s in d.get("sections", []) or []
    ])


def _landing_gear_from_dict(d: Dict[str, Any]) -> LandingGearGeometry:
    return LandingGearGeometry(
        main_gear=_gear_from_dict(d.get("main_gear") or {}),
        nose_gear=_gear_from_dict(d.get("nose_gear") or {}),
        tread_in=float(d.get("tread_in", 0.0) or 0.0),
    )


def geometry_from_dict(d: Dict[str, Any], legacy_configuration: Optional[Dict[str, Any]] = None,
                       legacy_tail_loads: Optional[Dict[str, Any]] = None,
                       legacy_vtail_loads: Optional[Dict[str, Any]] = None,
                       legacy_landing: Optional[Dict[str, Any]] = None) -> GeometryInput:
    """Build the unified :class:`GeometryInput` from a plain dict (Step G1/G6).

    ``surfaces`` is the WINGGEOM planform list (unchanged). ``parametric`` is the
    embedded :class:`LayoutInput`; ``legacy_configuration`` folds a pre-v25 file's
    top-level ``"configuration"`` block into it when ``geometry.parametric`` is
    absent. ``fuselage`` is the body outline, defaulted from the parametric
    length/width/height scalars when the file predates it. ``empennage`` (Step G6)
    is the single-source tail + elevator/rudder geometry: read from ``d["empennage"]``
    (``{htail, vtail}``) or, for a pre-v27 file, migrated from the top-level
    ``tail_loads``/``vtail_loads`` slices passed as ``legacy_tail_loads``/
    ``legacy_vtail_loads`` (the retired duplicated ``LayoutInput`` tail area/span/arm
    fields are dropped -- the analysis-native values are authoritative).
    """
    parametric_raw = d.get("parametric")
    if parametric_raw is None:
        parametric_raw = legacy_configuration
    parametric = configuration_from_dict(parametric_raw) if parametric_raw else None

    fuselage_raw = d.get("fuselage")
    if fuselage_raw:
        fuselage = _fuselage_outline_from_dict(fuselage_raw)
    elif parametric is not None:
        fuselage = default_fuselage_outline(parametric)
    else:
        fuselage = None

    emp_raw = d.get("empennage")
    if emp_raw is not None:
        htail_raw, vtail_raw = emp_raw.get("htail"), emp_raw.get("vtail")
    else:
        htail_raw, vtail_raw = legacy_tail_loads, legacy_vtail_loads
    empennage = None
    if htail_raw is not None or vtail_raw is not None:
        empennage = EmpennageInput(
            htail=tail_loads_from_dict(htail_raw) if htail_raw else None,
            vtail=vtail_loads_from_dict(vtail_raw) if vtail_raw else None,
        )

    # Step G6b: landing-gear geometry from d["landing_gear"], else migrated from a
    # pre-v28 file's top-level "landing" gear, else (coarse-only file) synthesized
    # from the retired LayoutInput gear fields (static axle X + tread only).
    landing_gear = None
    lg_raw = d.get("landing_gear")
    if lg_raw is not None:
        landing_gear = _landing_gear_from_dict(lg_raw)
    elif legacy_landing and any(legacy_landing.get(k) for k in ("main_gear", "nose_gear", "tread_in")):
        landing_gear = _landing_gear_from_dict(legacy_landing)
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
            }
            for s in inp.surfaces
        ]
    }
    if inp.parametric is not None:
        out["parametric"] = configuration_to_dict(inp.parametric)
    if inp.fuselage is not None:
        out["fuselage"] = {
            "sections": [
                {"x": s.x, "width": s.width, "height": s.height}
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
            "main_gear": asdict(lg.main_gear),
            "nose_gear": asdict(lg.nose_gear),
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
        mac=d.get("mac", 0.0),
        wing_area_sqft=d.get("wing_area_sqft", 0.0),
        xw=d.get("xw", 0.0),
        zw=d.get("zw", 0.0),
        xtc=d.get("xtc", 0.0),
        xtf=d.get("xtf", 0.0),
        mn=d.get("mn", 0.1),
        altitudes_ft=[float(a) for a in d.get("altitudes_ft", [0.0]) or [0.0]],
        cg_cases=[CgCase(**_filtered(CgCase, c)) for c in d.get("cg_cases", []) or []],
    )


def flight_loads_to_dict(inp: FlightLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`FlightLoadsInput` to JSON-friendly primitives.

    Step M2-6: ``mac``/``wing_area_sqft``/``xw``/``zw`` are derived from geometry and
    are deliberately **not** written (see :func:`sloads.derived_geometry`); a legacy
    file's stored copies are ignored on load and re-derived, so save->reload is a no-op.
    """
    return {
        "xtc": inp.xtc,
        "xtf": inp.xtf,
        "mn": inp.mn,
        "altitudes_ft": list(inp.altitudes_ft),
        "cg_cases": [asdict(c) for c in inp.cg_cases],
    }


# --------------------------------------------------------------------------- #
# Aero coefficients slice <-> dict (Project.aero_coeffs, Step D4.1)
# --------------------------------------------------------------------------- #
def aero_coefficients_from_dict(d: Dict[str, Any]) -> AeroCoefficientsInput:
    """Build an :class:`AeroCoefficientsInput` from a plain dict."""
    fm = d.get("fuselage_moment")
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
    return out


def _legacy_aero_coeffs_from_flight_loads(
    flight_loads: Any,
) -> Any:
    """Migrate pre-schema-18 files: ``flight_loads.configurations`` moved to the
    top-level ``aero_coeffs`` slice (Step D4.1). Returns ``None`` when there is
    nothing to migrate, so older project files still load."""
    if not flight_loads:
        return None
    configs = flight_loads.get("configurations") or []
    if not configs:
        return None
    cruise = next((c for c in configs if not c.get("flaps_down")), None)
    flapped = next((c for c in configs if c.get("flaps_down")), None)
    if cruise is None and flapped is None:
        return None
    return AeroCoefficientsInput(
        cruise=_aero_coeff_set_from_dict(cruise) if cruise else None,
        flaps_down=_aero_coeff_set_from_dict(flapped) if flapped else None,
    )


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
    )


def _vn_point_from_dict(d: Dict[str, Any]) -> VnPoint:
    d = dict(d)
    ref = d.pop("case_ref", None)
    return VnPoint(case_ref=_case_ref_from_dict(ref), **_filtered(VnPoint, d))


def _critical_from_dict(d: Dict[str, Any]) -> CriticalLoadSet:
    return CriticalLoadSet(
        conditions=[_critical_condition_from_dict(c) for c in d.get("conditions", []) or []],
        selected_case_ids=[str(i) for i in d.get("selected_case_ids", []) or []],
    )


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
    d = _rename_legacy_units(d, {"airplane_length_ft": ("airplane_length_in", 12.0)})
    return TailLoadsInput(**_filtered(TailLoadsInput, d))


def tail_loads_to_dict(inp: TailLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`TailLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Rational vertical-tail-loads input slice <-> dict (SELECT)
# --------------------------------------------------------------------------- #
def vtail_loads_from_dict(d: Dict[str, Any]) -> VTailLoadsInput:
    """Build a :class:`VTailLoadsInput` from a plain dict."""
    d = _rename_legacy_units(d, {
        "airplane_length_ft": ("airplane_length_in", 12.0),
        "wing_span_ft": ("wing_span_in", 12.0),
        "vtail_mac_ft": ("vtail_mac_in", 12.0),
    })
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
    return LandingGearInput(**kw)


def landing_from_dict(d: Dict[str, Any]) -> LandingInput:
    """Build a :class:`LandingInput` from a plain dict (CG cases + non-geometry
    LANDLOAD params). Step G6b: the gear geometry (``main_gear``/``nose_gear``/
    ``tread_in``) is no longer read here -- it lives in ``geometry.landing_gear`` and
    is synced onto ``Project.landing`` by the calc; a legacy file's top-level gear is
    migrated into geometry by :func:`geometry_from_dict`."""
    kw = {k: v for k, v in _filtered(LandingInput, d).items()
          if k not in ("main_gear", "nose_gear", "tread_in", "cg_cases")}
    kw["cg_cases"] = [CgCase(**_filtered(CgCase, c)) for c in d.get("cg_cases", []) or []]
    return LandingInput(**kw)


def landing_to_dict(inp: LandingInput) -> Dict[str, Any]:
    """Serialize a :class:`LandingInput` (Step G6b: the gear geometry
    ``main_gear``/``nose_gear``/``tread_in`` is written under
    ``geometry.landing_gear``, not here -- the single stored home). Step M2-6:
    ``wing_area_sqft`` is derived from the geometry wing (``landing._wing_area``) and
    not written -- re-derived on load."""
    out = asdict(inp)
    for gear_key in ("main_gear", "nose_gear", "tread_in", "wing_area_sqft"):
        out.pop(gear_key, None)
    return out


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
    tabs = [TabSpec(**_filtered(TabSpec,
                                _rename_legacy_units(t, {"area_sqin": ("area_sqft", 1.0 / 144.0)})))
            for t in d.get("tabs", []) or []]
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
        wrp_waterline=d.get("wrp_waterline", 0.0),
        dihedral_deg=d.get("dihedral_deg", 0.0),
        surface=d.get("surface", "wing"),
        concentrated=[ConcentratedWeight(**_filtered(ConcentratedWeight, c))
                      for c in d.get("concentrated", []) or []],
        cases=[WingLoadCase(**_filtered(WingLoadCase, c)) for c in d.get("cases", []) or []],
    )


def wing_mass_to_dict(inp: WingMassInput) -> Dict[str, Any]:
    """Serialize a :class:`WingMassInput` to JSON-friendly primitives.

    Step M2-6: ``dihedral_deg``/``wrp_waterline`` are derived from the parametric wing
    on ``Project.geometry`` and are not written (re-derived on load)."""
    out = asdict(inp)
    out.pop("dihedral_deg", None)
    out.pop("wrp_waterline", None)
    return out


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
    d = _rename_legacy_units(d, {
        "h_tail_span_ft": ("h_tail_span_in", 12.0),
        "v_tail_span_ft": ("v_tail_span_in", 12.0),
    })
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
    """Build a :class:`Project` from a dict, accepting the legacy flat shape.

    Accepts either the multi-engine ``"engines": [...]`` + ``"engine_layout"``
    form or the legacy single ``"engine": {...}`` key (wrapped into a one-element
    list with a SINGLE_NOSE layout).
    """
    if (
        "engines" in d or "engine" in d or "weight" in d or "geometry" in d
        or "speeds" in d or "aero" in d or "aero_coeffs" in d
        or "flight_loads" in d or "envelope" in d
        or "mass" in d or "wing_mass" in d or "fuselage_mass" in d
        or "select_input" in d or "tail_loads" in d or "vtail_loads" in d
        or "aileron_loads" in d or "flap_loads" in d or "tab_loads" in d
        or "one_engine_out" in d or "landing" in d or "loads" in d
        or "configuration" in d or "schema_version" in d or "name" in d
    ):
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
        tail_loads = d.get("tail_loads")
        vtail_loads = d.get("vtail_loads")
        aileron_loads = d.get("aileron_loads")
        flap_loads = d.get("flap_loads")
        tab_loads = d.get("tab_loads")
        one_engine_out = d.get("one_engine_out")
        landing = d.get("landing")
        loads = d.get("loads")
        # v25: the parametric layout unified onto the geometry slice. A pre-v25 file
        # carries it as a top-level "configuration" block -- fold it into geometry.
        legacy_configuration = d.get("configuration")
        engines, layout = _engines_from_dict(d)
        weight_slice = weight_from_dict(weight) if weight else None
        if weight_slice is not None and not weight_slice.cg_cases:
            weight_slice.cg_cases = _legacy_cg_cases_from_flight_loads(flight_loads)
        project = Project(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            name=d.get("name", ""),
            engineer=d.get("engineer", ""),
            date=d.get("date", ""),
            revision=d.get("revision", ""),
            checked_by=d.get("checked_by", ""),
            approved_by=d.get("approved_by", ""),
            description=d.get("description", ""),
            engines=engines,
            engine_layout=layout,
            weight=weight_slice,
            geometry=(
                geometry_from_dict(
                    geometry or {}, legacy_configuration=legacy_configuration,
                    legacy_tail_loads=tail_loads, legacy_vtail_loads=vtail_loads,
                    legacy_landing=landing)
                if (geometry or legacy_configuration or tail_loads or vtail_loads
                    or (landing and any(landing.get(k) for k in ("main_gear", "nose_gear", "tread_in"))))
                else None
            ),
            speeds=speeds_from_dict(speeds) if speeds else None,
            aero=aero_from_dict(aero) if aero else None,
            aero_coeffs=(
                aero_coefficients_from_dict(aero_coeffs) if aero_coeffs
                else _legacy_aero_coeffs_from_flight_loads(flight_loads)
            ),
            flight_loads=flight_loads_from_dict(flight_loads) if flight_loads else None,
            envelope=envelope_from_dict(envelope) if envelope else None,
            mass=mass_from_dict(mass) if mass else None,
            wing_mass=wing_mass_from_dict(wing_mass) if wing_mass else None,
            fuselage_mass=fuselage_mass_from_dict(fuselage_mass) if fuselage_mass else None,
            select_input=select_input_from_dict(select_input) if select_input else None,
            # tail_loads / vtail_loads are no longer Project fields (Step G6): they are
            # migrated into geometry.empennage above (legacy_tail_loads/legacy_vtail_loads).
            aileron_loads=aileron_loads_from_dict(aileron_loads) if aileron_loads else None,
            flap_loads=flap_loads_from_dict(flap_loads) if flap_loads else None,
            tab_loads=tab_loads_from_dict(tab_loads) if tab_loads else None,
            one_engine_out=one_engine_out_from_dict(one_engine_out) if one_engine_out else None,
            landing=landing_from_dict(landing) if landing else None,
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
    # Legacy: the whole file is just the engine slice.
    return Project(name="", engines=[engine_from_dict(d)], engine_layout=EngineLayout.SINGLE_NOSE)


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


def load_cases_csv(results, header_comment: str = "") -> str:
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
    """
    conditions = _as_conditions(results)
    if has_load_case_data(conditions):
        rows = load_cases_to_rows(conditions)
    else:
        rows = results_to_rows(conditions)
    if not rows:
        return ""
    import io as _io

    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return header_comment + buf.getvalue()


def write_load_cases_csv(results, path: str, header_comment: str = "") -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(load_cases_csv(results, header_comment=header_comment))
