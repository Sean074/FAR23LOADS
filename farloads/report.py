"""Render calculation results into shareable formats.

Modernized output: a flat list of rows for on-screen tables and a plain-text
report for download. No printer escape codes (unlike the original LPRINT).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .models import ConditionResult, EngineInput, LoadValue


def _fmt(value: float) -> str:
    if isinstance(value, int):
        return str(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.4g}"


# --------------------------------------------------------------------------- #
# Limit -> ultimate scaling at the render/export boundary
# --------------------------------------------------------------------------- #
# The calc emits LIMIT loads (oracle-locked). The rendered output reports ULTIMATE
# loads = limit x ConditionResult.safety_factor. The factor multiplies *load*
# quantities only -- forces, moments and design pressures -- never lengths, masses,
# inertias, areas, speeds, angles, or the dimensionless load factors (standard
# convention: limit load factor, ultimate load). Units are the canonical Imperial
# strings the modules emit plus the SI strings units.convert_results may produce.
_LOAD_UNITS = {
    "lb",        # force (lbf); a *weight* uses quantity="mass" and is excluded below
    "ft-lb",     # moment / torque
    "lb-in",     # moment (root bending/torsion, pitching moment)
    "lb/in^2",   # control-surface / tab / tail design pressure
    "N",         # SI force
    "N·m",       # SI moment
}


def _is_load_unit(units: str, quantity: str = "") -> bool:
    """True if a quantity in these ``units`` is a structural load to scale to ultimate.

    A bare ``"lb"`` is pounds-force (a load) unless ``quantity == "mass"`` (a weight).
    Wing loading ("lb/ft^2"), positions ("in"), inertias, areas, speeds and angles
    are not loads and pass through unscaled.
    """
    if quantity == "mass":
        return False
    return units in _LOAD_UNITS


def _ult(value, units: str, quantity: str, sf: float):
    """Scale a single value to ultimate if its units mark it as a load; else pass through."""
    if value == "" or value is None:
        return value
    return value * sf if _is_load_unit(units, quantity) else value


def results_to_rows(results: List[ConditionResult]) -> List[Dict[str, str]]:
    """Flatten results into rows suitable for a dataframe/table.

    Load quantities (forces/moments/pressures) are reported as ULTIMATE = limit x
    the case ``safety_factor`` and carry that factor in the ``SF`` column; non-load
    quantities (weights, positions, inertias, load factors) pass through unscaled
    with a blank ``SF``.
    """
    rows: List[Dict[str, str]] = []
    for r in results:
        for v in r.values:
            is_load = _is_load_unit(v.units, v.quantity)
            value = v.value * r.safety_factor if is_load else v.value
            rows.append(
                {
                    "FAR": r.far_reference,
                    "Condition": r.title,
                    "Quantity": v.label,
                    "Value": _fmt(value),
                    "Units": v.units,
                    "SF": _fmt(r.safety_factor) if is_load else "",
                }
            )
    return rows


# --------------------------------------------------------------------------- #
# Load-case table (one row per structural load case)
# --------------------------------------------------------------------------- #
# Labels emitted by the calc modules, mapped into the flat load-case schema below.
_LOC_LABELS = ("Applied at X", "Applied at Y", "Applied at Z")
_VERTICAL_LABELS = ("Vertical down load", "Vertical 2.5g load")
_SIDE_LABEL = "Side load"
_THRUST_LABEL = "Max continuous thrust"
_TORQUE_LABEL = "Engine mount torque"
_GYRO_FAR = "23.371(b)"
_GYRO_CASE_RE = re.compile(r"Case (\d+) \(([^)]*)\):\s*(Myy|Mzz)")


_LOAD_CASE_LABELS = set(_LOC_LABELS) | set(_VERTICAL_LABELS) | {_SIDE_LABEL, _THRUST_LABEL, _TORQUE_LABEL}


def has_load_case_data(results: List[ConditionResult]) -> bool:
    """True if these results carry structural load-case data (forces/moments at a
    point), i.e. the ``load_cases_to_rows`` schema applies.

    Mass-properties and other property-table modules emit none of those labels, so
    this returns False for them and callers fall back to the generic table.
    """
    for r in results:
        if r.far_reference == _GYRO_FAR:
            return True
        for v in r.values:
            if v.label in _LOAD_CASE_LABELS:
                return True
    return False


def _find(values: List[LoadValue], label: str) -> Optional[LoadValue]:
    for v in values:
        if v.label == label:
            return v
    return None


def _find_any(values: List[LoadValue], labels) -> Optional[LoadValue]:
    for label in labels:
        v = _find(values, label)
        if v is not None:
            return v
    return None


def _detect_unit(results, labels) -> str:
    for r in results:
        for v in r.values:
            if v.label in labels and v.units:
                return v.units
    return ""


def _detect_moment_unit(results) -> str:
    for r in results:
        for v in r.values:
            if v.units in ("ft-lb", "N·m"):
                return v.units
    return "ft-lb"


def _result_location(r: ConditionResult):
    locs = [_find(r.values, lbl) for lbl in _LOC_LABELS]
    if all(locs):
        return tuple(v.value for v in locs)
    return None


def _global_location(results):
    for r in results:
        loc = _result_location(r)
        if loc is not None:
            return loc
    return (None, None, None)


def _val(loadvalue: Optional[LoadValue]):
    return loadvalue.value if loadvalue is not None else ""


def _gyro_subcases(r: ConditionResult):
    """Yield (description, Myy, Mzz, thrust, vertical) for each gyro load case.

    The 2.5g vertical load and max-continuous thrust are constant across all four
    sign combinations; only the gyroscopic moments vary.
    """
    thrust = _val(_find(r.values, _THRUST_LABEL))
    vertical = _val(_find(r.values, "Vertical 2.5g load"))
    cases: Dict[str, Dict[str, object]] = {}
    for v in r.values:
        m = _GYRO_CASE_RE.match(v.label)
        if not m:
            continue
        num, signs, comp = m.groups()
        case = cases.setdefault(num, {"signs": signs})
        case[comp] = v.value
    for num in sorted(cases, key=int):
        c = cases[num]
        desc = f"{r.title} — Case {num} ({c['signs']})"
        yield desc, c.get("Myy", ""), c.get("Mzz", ""), thrust, vertical


def load_cases_to_rows(results: List[ConditionResult]) -> List[Dict[str, object]]:
    """One row per structural load case: ID, description, location, applied loads.

    Each row carries the load components an engine mount must react -- vertical,
    side and thrust forces plus the engine-mount (roll), pitch (Myy) and yaw
    (Mzz) moments -- at the combined engine+prop CG. Blank cells mean a component
    does not apply to that case. The gyroscopic condition (FAR 23.371(b)) expands
    into its four sign-combination cases. Units follow whatever the results carry
    (Imperial or SI), shown in the column headers.

    Forces and moments are reported as ULTIMATE loads (= limit x the case
    ``safety_factor``); the headers carry the ``ULT`` marker and the per-case factor
    is in the ``SF`` column. Locations are geometry and are not scaled.
    """
    force_u = _detect_unit(results, set(_VERTICAL_LABELS) | {_SIDE_LABEL, _THRUST_LABEL}) or "lb"
    len_u = _detect_unit(results, set(_LOC_LABELS)) or "in"
    mom_u = _detect_unit(results, {_TORQUE_LABEL}) or _detect_moment_unit(results)
    g_loc = _global_location(results)

    c_id = f"Loc X ({len_u})", f"Loc Y ({len_u})", f"Loc Z ({len_u})"
    c_vert = f"Vertical load ({force_u}) ULT"
    c_side = f"Side load ({force_u}) ULT"
    c_thr = f"Thrust ({force_u}) ULT"
    c_roll = f"Engine mount torque ({mom_u}) ULT"
    c_pitch = f"Pitch moment Myy ({mom_u}) ULT"
    c_yaw = f"Yaw moment Mzz ({mom_u}) ULT"

    def row(idx, far, desc, loc, sf, *, fz="", fy="", fx="", mx="", my="", mz=""):
        x, y, z = loc
        return {
            "ID": f"LC{idx}",
            "FAR": far,
            "Case description": desc,
            "SF": _fmt(sf),
            c_id[0]: _num(x),
            c_id[1]: _num(y),
            c_id[2]: _num(z),
            c_vert: _num(_scale(fz, sf)),
            c_side: _num(_scale(fy, sf)),
            c_thr: _num(_scale(fx, sf)),
            c_roll: _num(_scale(mx, sf)),
            c_pitch: _num(_scale(my, sf)),
            c_yaw: _num(_scale(mz, sf)),
        }

    rows: List[Dict[str, object]] = []
    idx = 0
    for r in results:
        loc = _result_location(r) or g_loc
        sf = r.safety_factor
        if r.far_reference == _GYRO_FAR:
            for desc, my, mz, fx, fz in _gyro_subcases(r):
                idx += 1
                rows.append(row(idx, r.far_reference, desc, loc, sf, fz=fz, fx=fx, my=my, mz=mz))
        else:
            idx += 1
            rows.append(
                row(
                    idx,
                    r.far_reference,
                    r.title,
                    loc,
                    sf,
                    fz=_val(_find_any(r.values, _VERTICAL_LABELS)),
                    fy=_val(_find(r.values, _SIDE_LABEL)),
                    mx=_val(_find(r.values, _TORQUE_LABEL)),
                )
            )
    return rows


def _scale(value, sf: float):
    """Scale a force/moment cell to ultimate; blank cells stay blank."""
    if value == "" or value is None:
        return value
    return value * sf


def _num(value) -> str:
    """Format a numeric cell; blank for missing components."""
    if value == "" or value is None:
        return ""
    return _fmt(value)


def module_text_report(title: str, results: List[ConditionResult]) -> str:
    """A clean fixed-width text report for any module's results.

    Module-agnostic (no engine-specific header), so the CLI can print results for
    modules whose inputs are not the engine slice.
    """
    lines: List[str] = [title.upper(), "=" * 60]
    lines.append("Loads are ULTIMATE (= limit x SF); load factors are limit.")
    lines.append("")
    for r in results:
        lines.append(f"{r.title}")
        lines.append(f"  FAR {r.far_reference}   [ULTIMATE, SF={_fmt(r.safety_factor)}]")
        for v in r.values:
            unit = f" {v.units}" if v.units else ""
            value = _ult(v.value, v.units, v.quantity, r.safety_factor)
            lines.append(f"    {v.label:<38}{_fmt(value)}{unit}")
        if r.note:
            lines.append(f"    NOTE: {r.note}")
        lines.append("")
    return "\n".join(lines)


def text_report(
    inp: EngineInput, results: List[ConditionResult], unit_system: str = ""
) -> str:
    """A clean, fixed-width text report (replaces the BASIC printout).

    ``results`` are rendered with whatever units their values carry, so pass
    already-converted results when reporting in SI. ``unit_system`` is an
    optional label ("Imperial"/"SI") shown in the header.
    """
    lines: List[str] = []
    lines.append("ENGINE MOUNT LOADS")
    lines.append("=" * 60)
    if inp.engine_designation:
        lines.append(f"Engine: {inp.engine_designation}")
    if inp.prop_designation:
        lines.append(f"Prop:   {inp.prop_designation}")
    lines.append(f"Type:   {'Turboprop' if inp.is_turboprop else 'Reciprocating'}")
    if unit_system:
        lines.append(f"Units:  {unit_system}")
    lines.append("Loads are ULTIMATE (= limit x SF); load factors are limit.")
    lines.append("")

    for r in results:
        lines.append(f"{r.title}")
        lines.append(f"  FAR {r.far_reference}   [ULTIMATE, SF={_fmt(r.safety_factor)}]")
        for v in r.values:
            unit = f" {v.units}" if v.units else ""
            value = _ult(v.value, v.units, v.quantity, r.safety_factor)
            lines.append(f"    {v.label:<38}{_fmt(value)}{unit}")
        if r.note:
            lines.append(f"    NOTE: {r.note}")
        lines.append("")

    return "\n".join(lines)
