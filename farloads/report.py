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


def results_to_rows(results: List[ConditionResult]) -> List[Dict[str, str]]:
    """Flatten results into rows suitable for a dataframe/table."""
    rows: List[Dict[str, str]] = []
    for r in results:
        for v in r.values:
            rows.append(
                {
                    "FAR": r.far_reference,
                    "Condition": r.title,
                    "Quantity": v.label,
                    "Value": _fmt(v.value),
                    "Units": v.units,
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
    """
    force_u = _detect_unit(results, set(_VERTICAL_LABELS) | {_SIDE_LABEL, _THRUST_LABEL}) or "lb"
    len_u = _detect_unit(results, set(_LOC_LABELS)) or "in"
    mom_u = _detect_unit(results, {_TORQUE_LABEL}) or _detect_moment_unit(results)
    g_loc = _global_location(results)

    c_id = f"Loc X ({len_u})", f"Loc Y ({len_u})", f"Loc Z ({len_u})"
    c_vert = f"Vertical load ({force_u})"
    c_side = f"Side load ({force_u})"
    c_thr = f"Thrust ({force_u})"
    c_roll = f"Engine mount torque ({mom_u})"
    c_pitch = f"Pitch moment Myy ({mom_u})"
    c_yaw = f"Yaw moment Mzz ({mom_u})"

    def row(idx, far, desc, loc, *, fz="", fy="", fx="", mx="", my="", mz=""):
        x, y, z = loc
        return {
            "ID": f"LC{idx}",
            "FAR": far,
            "Case description": desc,
            c_id[0]: _num(x),
            c_id[1]: _num(y),
            c_id[2]: _num(z),
            c_vert: _num(fz),
            c_side: _num(fy),
            c_thr: _num(fx),
            c_roll: _num(mx),
            c_pitch: _num(my),
            c_yaw: _num(mz),
        }

    rows: List[Dict[str, object]] = []
    idx = 0
    for r in results:
        loc = _result_location(r) or g_loc
        if r.far_reference == _GYRO_FAR:
            for desc, my, mz, fx, fz in _gyro_subcases(r):
                idx += 1
                rows.append(row(idx, r.far_reference, desc, loc, fz=fz, fx=fx, my=my, mz=mz))
        else:
            idx += 1
            rows.append(
                row(
                    idx,
                    r.far_reference,
                    r.title,
                    loc,
                    fz=_val(_find_any(r.values, _VERTICAL_LABELS)),
                    fy=_val(_find(r.values, _SIDE_LABEL)),
                    mx=_val(_find(r.values, _TORQUE_LABEL)),
                )
            )
    return rows


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
    lines: List[str] = [title.upper(), "=" * 60, ""]
    for r in results:
        lines.append(f"{r.title}")
        lines.append(f"  FAR {r.far_reference}")
        for v in r.values:
            unit = f" {v.units}" if v.units else ""
            lines.append(f"    {v.label:<38}{_fmt(v.value)}{unit}")
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
    lines.append("")

    for r in results:
        lines.append(f"{r.title}")
        lines.append(f"  FAR {r.far_reference}")
        for v in r.values:
            unit = f" {v.units}" if v.units else ""
            lines.append(f"    {v.label:<38}{_fmt(v.value)}{unit}")
        if r.note:
            lines.append(f"    NOTE: {r.note}")
        lines.append("")

    return "\n".join(lines)
