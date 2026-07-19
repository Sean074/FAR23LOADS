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


# --------------------------------------------------------------------------- #
# CaseRef <-> dict (Step D1) -- shared by every result type that carries one:
# VnPoint, CriticalCondition, WingLoadResult, BodyLoadResult, TailChordResult,
# ControlSurfaceLoadResult. ``asdict`` already nests CaseRef correctly on the
# to_dict side (no helper needed there); from_dict needs one since a plain
# ``**dict(d)`` splat would otherwise pass the nested dict straight through as
# ``case_ref`` instead of a CaseRef instance.
# --------------------------------------------------------------------------- #
def _case_ref_from_dict(raw) -> Any:
    return CaseRef(**dict(raw)) if raw else None


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
        **d,
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
    return MassItem(kind=kind, **d)


def weight_from_dict(d: Dict[str, Any]) -> WeightInput:
    """Build a :class:`WeightInput` from a plain dict (enum coercion)."""
    d = dict(d)
    est = d.get("estimation")
    estimation = None
    if est:
        est = dict(est)
        estimation = WeightEstimationInput(
            engine_weight_type=EngineWeightType(est.pop("engine_weight_type", "RF")),
            **est,
        )
    items = [_mass_item_from_dict(it) for it in d.get("items", []) or []]
    env = d.get("envelope")
    envelope = WeightEnvelopeInput(**dict(env)) if env else None
    cg_cases = [CgCase(**dict(c)) for c in d.get("cg_cases", []) or []]
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
    return [CgCase(**dict(c)) for c in flight_loads.get("cg_cases", []) or []]


# --------------------------------------------------------------------------- #
# Geometry slice <-> dict
# --------------------------------------------------------------------------- #
def _points(raw) -> List:
    """Coerce a list of JSON [x, y] arrays to (x, y) tuples."""
    return [tuple(p) for p in raw or []]


def _surface_from_dict(d: Dict[str, Any]) -> SurfaceInput:
    return SurfaceInput(
        name=d["name"],
        leading_edge=_points(d.get("leading_edge")),
        trailing_edge=_points(d.get("trailing_edge")),
        symmetric=d.get("symmetric", True),
        elements=d.get("elements", 20),
    )


def _fuselage_outline_from_dict(d: Dict[str, Any]) -> FuselageOutline:
    return FuselageOutline(sections=[
        FuselageSection(x=s["x"], width=s["width"], height=s["height"])
        for s in d.get("sections", []) or []
    ])


def geometry_from_dict(d: Dict[str, Any], legacy_configuration: Optional[Dict[str, Any]] = None) -> GeometryInput:
    """Build the unified :class:`GeometryInput` from a plain dict (Step G1).

    ``surfaces`` is the WINGGEOM planform list (unchanged). ``parametric`` is the
    embedded :class:`LayoutInput`; ``legacy_configuration`` folds a pre-v25 file's
    top-level ``"configuration"`` block into it when ``geometry.parametric`` is
    absent. ``fuselage`` is the body outline, defaulted from the parametric
    length/width/height scalars when the file predates it.
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

    return GeometryInput(
        surfaces=[_surface_from_dict(s) for s in d.get("surfaces", []) or []],
        parametric=parametric,
        fuselage=fuselage,
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
    mach_limit = MachLimitInput(**dict(ml)) if ml else None
    return StructuralSpeedsInput(mach_limit=mach_limit, **d)


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
    return AeroCoeffSet(
        name=d.get("name", "CRUISE"),
        stall_cl=d["stall_cl"],
        neg_stall_cl=d["neg_stall_cl"],
        lift=_coeff5(d.get("lift")),
        drag=_coeff5(d.get("drag")),
        moment=_coeff5(d.get("moment")),
        flaps_down=d.get("flaps_down", False),
    )


def _aero_coeff_set_to_dict(c: AeroCoeffSet) -> Dict[str, Any]:
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
        cg_cases=[CgCase(**dict(c)) for c in d.get("cg_cases", []) or []],
    )


def flight_loads_to_dict(inp: FlightLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`FlightLoadsInput` to JSON-friendly primitives."""
    return {
        "mac": inp.mac,
        "wing_area_sqft": inp.wing_area_sqft,
        "xw": inp.xw,
        "zw": inp.zw,
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


# --------------------------------------------------------------------------- #
# Envelope slice <-> dict (FLTLOADS result)
# --------------------------------------------------------------------------- #
def _critical_condition_from_dict(d: Dict[str, Any]) -> CriticalCondition:
    return CriticalCondition(
        component=d.get("component", ""),
        label=d.get("label", ""),
        far_reference=d.get("far_reference", ""),
        case=d.get("case"),
        loads=[LoadValue(**dict(v)) for v in d.get("loads", []) or []],
        lt25=d.get("lt25"),
        lt50=d.get("lt50"),
        case_ref=_case_ref_from_dict(d.get("case_ref")),
    )


def _vn_point_from_dict(d: Dict[str, Any]) -> VnPoint:
    d = dict(d)
    ref = d.pop("case_ref", None)
    return VnPoint(case_ref=_case_ref_from_dict(ref), **d)


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
        tail_balance=[TailBalanceLoad(**dict(t)) for t in d.get("tail_balance", []) or []],
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
    return MassResult(cases=[MassCase(**dict(c)) for c in d.get("cases", []) or []])


def mass_to_dict(inp: MassResult) -> Dict[str, Any]:
    """Serialize a :class:`MassResult` to JSON-friendly primitives."""
    return {"cases": [asdict(c) for c in inp.cases]}


# --------------------------------------------------------------------------- #
# Fuselage-mass slice <-> dict (fuselage net-load input)
# --------------------------------------------------------------------------- #
def fuselage_mass_from_dict(d: Dict[str, Any]) -> FuselageMassInput:
    """Build a :class:`FuselageMassInput` from a plain dict."""
    return FuselageMassInput(
        stations=[FuselageStation(**dict(s)) for s in d.get("stations", []) or []],
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
    fields = {f for f in SelectInput.__dataclass_fields__}
    return SelectInput(**{k: v for k, v in d.items() if k in fields})


def select_input_to_dict(inp: SelectInput) -> Dict[str, Any]:
    """Serialize a :class:`SelectInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Rational tail-loads input slice <-> dict (SELECT)
# --------------------------------------------------------------------------- #
def tail_loads_from_dict(d: Dict[str, Any]) -> TailLoadsInput:
    """Build a :class:`TailLoadsInput` from a plain dict."""
    d = _rename_legacy_units(d, {"airplane_length_ft": ("airplane_length_in", 12.0)})
    fields = {f for f in TailLoadsInput.__dataclass_fields__}
    return TailLoadsInput(**{k: v for k, v in d.items() if k in fields})


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
    fields = {f for f in VTailLoadsInput.__dataclass_fields__}
    return VTailLoadsInput(**{k: v for k, v in d.items() if k in fields})


def vtail_loads_to_dict(inp: VTailLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`VTailLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# One-engine-out input slice <-> dict (ONENGOUT)
# --------------------------------------------------------------------------- #
def one_engine_out_from_dict(d: Dict[str, Any]) -> OneEngineOutInput:
    """Build a :class:`OneEngineOutInput` from a plain dict."""
    fields = {f for f in OneEngineOutInput.__dataclass_fields__}
    return OneEngineOutInput(**{k: v for k, v in d.items() if k in fields})


def one_engine_out_to_dict(inp: OneEngineOutInput) -> Dict[str, Any]:
    """Serialize a :class:`OneEngineOutInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Landing / ground-load input slice <-> dict (LGFACTOR + LANDLOAD)
# --------------------------------------------------------------------------- #
def _gear_from_dict(d: Dict[str, Any]) -> LandingGearInput:
    fields = {f for f in LandingGearInput.__dataclass_fields__}
    kw = {k: v for k, v in d.items() if k in fields}
    for axle in ("axle_compressed", "axle_static", "axle_extended"):
        if axle in kw and kw[axle] is not None:
            kw[axle] = tuple(kw[axle])
    return LandingGearInput(**kw)


def landing_from_dict(d: Dict[str, Any]) -> LandingInput:
    """Build a :class:`LandingInput` from a plain dict (nested gear + CG cases)."""
    fields = {f for f in LandingInput.__dataclass_fields__}
    kw = {k: v for k, v in d.items() if k in fields and k not in
          ("main_gear", "nose_gear", "cg_cases")}
    if d.get("main_gear"):
        kw["main_gear"] = _gear_from_dict(d["main_gear"])
    if d.get("nose_gear"):
        kw["nose_gear"] = _gear_from_dict(d["nose_gear"])
    cg_fields = {f for f in CgCase.__dataclass_fields__}
    kw["cg_cases"] = [CgCase(**{k: v for k, v in c.items() if k in cg_fields})
                      for c in d.get("cg_cases", []) or []]
    return LandingInput(**kw)


def landing_to_dict(inp: LandingInput) -> Dict[str, Any]:
    """Serialize a :class:`LandingInput` to JSON-friendly primitives."""
    return asdict(inp)


# --------------------------------------------------------------------------- #
# Control-surface load input slices <-> dict (AILERON / FLAPLOAD / TABLOADS)
# --------------------------------------------------------------------------- #
def aileron_loads_from_dict(d: Dict[str, Any]) -> AileronLoadsInput:
    """Build an :class:`AileronLoadsInput` from a plain dict."""
    fields = {f for f in AileronLoadsInput.__dataclass_fields__}
    return AileronLoadsInput(**{k: v for k, v in d.items() if k in fields})


def aileron_loads_to_dict(inp: AileronLoadsInput) -> Dict[str, Any]:
    """Serialize an :class:`AileronLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


def flap_loads_from_dict(d: Dict[str, Any]) -> FlapLoadsInput:
    """Build a :class:`FlapLoadsInput` from a plain dict."""
    fields = {f for f in FlapLoadsInput.__dataclass_fields__}
    return FlapLoadsInput(**{k: v for k, v in d.items() if k in fields})


def flap_loads_to_dict(inp: FlapLoadsInput) -> Dict[str, Any]:
    """Serialize a :class:`FlapLoadsInput` to JSON-friendly primitives."""
    return asdict(inp)


def tab_loads_from_dict(d: Dict[str, Any]) -> TabLoadsInput:
    """Build a :class:`TabLoadsInput` from a plain dict (nested ``tabs``)."""
    spec_fields = {f for f in TabSpec.__dataclass_fields__}
    tabs = [TabSpec(**{k: v for k, v in
                       _rename_legacy_units(t, {"area_sqin": ("area_sqft", 1.0 / 144.0)}).items()
                       if k in spec_fields})
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
        concentrated=[ConcentratedWeight(**dict(c)) for c in d.get("concentrated", []) or []],
        cases=[WingLoadCase(**dict(c)) for c in d.get("cases", []) or []],
    )


def wing_mass_to_dict(inp: WingMassInput) -> Dict[str, Any]:
    """Serialize a :class:`WingMassInput` to JSON-friendly primitives."""
    out = asdict(inp)
    return out


# --------------------------------------------------------------------------- #
# Loads slice <-> dict (WINGINER / NETLOADS result)
# --------------------------------------------------------------------------- #
def _wing_load_result_from_dict(d: Dict[str, Any]) -> WingLoadResult:
    return WingLoadResult(
        case=d.get("case", ""),
        nz=d.get("nz", 0.0),
        nx=d.get("nx", 0.0),
        stations=[WingStationLoad(**dict(s)) for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
    )


def _body_load_result_from_dict(d: Dict[str, Any]) -> BodyLoadResult:
    return BodyLoadResult(
        case=d.get("case", ""),
        stations=[BodyStationLoad(**dict(s)) for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
    )


def _tail_chord_result_from_dict(d: Dict[str, Any]) -> TailChordResult:
    return TailChordResult(
        case=d.get("case", ""),
        component=d.get("component", ""),
        lt25=d.get("lt25", 0.0),
        lt50=d.get("lt50", 0.0),
        stations=[TailChordStation(**dict(s)) for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
        far_reference=d.get("far_reference", ""),
    )


def _control_surface_result_from_dict(d: Dict[str, Any]) -> ControlSurfaceLoadResult:
    return ControlSurfaceLoadResult(
        surface=d.get("surface", ""),
        case=d.get("case", ""),
        load_lb=d.get("load_lb", 0.0),
        v_kt=d.get("v_kt", 0.0),
        stations=[ControlSurfaceStation(**dict(s)) for s in d.get("stations", []) or []],
        case_ref=_case_ref_from_dict(d.get("case_ref")),
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
    fields = {f for f in LayoutInput.__dataclass_fields__}
    kwargs = {k: v for k, v in d.items() if k in fields}
    if "tail_type" in kwargs:
        kwargs["tail_type"] = TailType(kwargs["tail_type"])
    return LayoutInput(**kwargs)


def configuration_to_dict(inp: LayoutInput) -> Dict[str, Any]:
    """Serialize a :class:`LayoutInput` to JSON-friendly primitives."""
    return {**asdict(inp), "tail_type": inp.tail_type.value}


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
        return Project(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            name=d.get("name", ""),
            engineer=d.get("engineer", ""),
            date=d.get("date", ""),
            engines=engines,
            engine_layout=layout,
            weight=weight_slice,
            geometry=(
                geometry_from_dict(geometry or {}, legacy_configuration=legacy_configuration)
                if (geometry or legacy_configuration) else None
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
            tail_loads=tail_loads_from_dict(tail_loads) if tail_loads else None,
            vtail_loads=vtail_loads_from_dict(vtail_loads) if vtail_loads else None,
            aileron_loads=aileron_loads_from_dict(aileron_loads) if aileron_loads else None,
            flap_loads=flap_loads_from_dict(flap_loads) if flap_loads else None,
            tab_loads=tab_loads_from_dict(tab_loads) if tab_loads else None,
            one_engine_out=one_engine_out_from_dict(one_engine_out) if one_engine_out else None,
            landing=landing_from_dict(landing) if landing else None,
            loads=loads_from_dict(loads) if loads else None,
            include_far25=bool(d.get("include_far25", False)),
        )
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
    if project.tail_loads is not None:
        out["tail_loads"] = tail_loads_to_dict(project.tail_loads)
    if project.vtail_loads is not None:
        out["vtail_loads"] = vtail_loads_to_dict(project.vtail_loads)
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


def load_cases_csv(results) -> str:
    """Render module results to a CSV string.

    Load-producing modules emit one row per structural load case; modules that
    emit a property table instead (e.g. the mass-properties modules, whose
    ``ConditionResult``s carry no load-case labels) fall back to the generic
    quantity-per-row table so they still export a useful CSV.
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
    return buf.getvalue()


def write_load_cases_csv(results, path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(load_cases_csv(results))
