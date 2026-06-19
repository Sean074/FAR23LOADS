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
from dataclasses import asdict
from typing import Any, Dict, List

from .models import (
    SCHEMA_VERSION,
    ConditionResult,
    EngineInput,
    EngineLayout,
    EngineType,
    EngineWeightType,
    GeometryInput,
    MassItem,
    MassItemKind,
    ModuleResult,
    Project,
    Rotor,
    RotorDirection,
    RotorType,
    SurfaceInput,
    WeightEstimationInput,
    WeightInput,
)
from .report import has_load_case_data, load_cases_to_rows, results_to_rows


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
    return WeightInput(estimation=estimation, items=items)


def weight_to_dict(inp: WeightInput) -> Dict[str, Any]:
    """Serialize a :class:`WeightInput` to JSON-friendly primitives."""
    out: Dict[str, Any] = {}
    if inp.estimation is not None:
        est = asdict(inp.estimation)
        est["engine_weight_type"] = inp.estimation.engine_weight_type.value
        out["estimation"] = est
    out["items"] = [{**asdict(it), "kind": it.kind.value} for it in inp.items]
    return out


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


def geometry_from_dict(d: Dict[str, Any]) -> GeometryInput:
    """Build a :class:`GeometryInput` from a plain dict (tuple coercion)."""
    return GeometryInput(surfaces=[_surface_from_dict(s) for s in d.get("surfaces", []) or []])


def geometry_to_dict(inp: GeometryInput) -> Dict[str, Any]:
    """Serialize a :class:`GeometryInput` to JSON-friendly primitives."""
    return {
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
        "engines" in d or "engine" in d or "weight" in d
        or "geometry" in d or "schema_version" in d or "name" in d
    ):
        weight = d.get("weight")
        geometry = d.get("geometry")
        engines, layout = _engines_from_dict(d)
        return Project(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            name=d.get("name", ""),
            engines=engines,
            engine_layout=layout,
            weight=weight_from_dict(weight) if weight else None,
            geometry=geometry_from_dict(geometry) if geometry else None,
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
    if project.engines:
        out["engines"] = [engine_to_dict(e) for e in project.engines]
        if project.engine_layout is not None:
            out["engine_layout"] = project.engine_layout.value
    if project.weight is not None:
        out["weight"] = weight_to_dict(project.weight)
    if project.geometry is not None:
        out["geometry"] = geometry_to_dict(project.geometry)
    return out


def load_project(path: str) -> Project:
    with open(path, "r", encoding="utf-8") as fh:
        return project_from_dict(json.load(fh))


def save_project(project: Project, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(project_to_dict(project), fh, indent=2)
        fh.write("\n")


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
