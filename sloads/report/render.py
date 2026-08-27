"""Render calculation results into shareable formats.

Modernized output: a flat list of rows for on-screen tables and a plain-text
report for download. No printer escape codes (unlike the original LPRINT).

This module is ``sloads/report.py`` verbatim, moved into the ``report`` package
at Step G8.1 exactly as ``models.py`` -> ``models/`` moved at M3-1. Every public
name here is re-exported from :mod:`sloads.report`, so ``from sloads.report
import load_cases_to_rows`` keeps working unchanged -- the move is mechanical,
not an API change. It owns the **limit -> ultimate boundary** for tabular and
text output (see CLAUDE.md's ultimate-load contract).
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional

from ..case_ids import NO_LOAD_ID, deck_load_id
from ..constants import ULTIMATE_FACTOR
from ..load_keys import (
    FX_THRUST,
    FY_SIDE,
    FZ_VERTICAL_2_5G,
    LOAD_CASE_KEYS,
    LOC_KEYS,
    MX_MOUNT_TORQUE,
    VERTICAL_KEYS,
    parse_gyro_key,
)
from ..models import ConditionResult, CriticalCondition, EngineInput, LoadValue
from ..units import UnitSystem, convert_results


def format_value(value: float) -> str:
    """Format one numeric cell for a table or the text report.

    Public since G8.1: it was ``_fmt``, but ``tests/test_results_review.py``
    already imported it across the module boundary, which the M4-12b public-symbol
    contract (``PROJECT_GUIDE`` §5) makes a defect rather than a shortcut. Promoted
    rather than re-exported under its private name.
    """
    if isinstance(value, int):
        return str(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.4g}"


def envelope_extremes(series: List[List[float]]) -> "tuple[List[float], List[float]]":
    """Pointwise ``(upper, lower)`` envelope across equal-length value series.

    A true load envelope is two-sided: at each station the maximum **and** the
    minimum across the cases (the opposite-sign extreme can govern a different
    part of the structure). A single max-|value| trace hides the opposite-sign
    extreme and can jump discontinuously where the governing sign flips, so it
    is not used for envelopes.
    """
    upper = [max(vals) for vals in zip(*series)]
    lower = [min(vals) for vals in zip(*series)]
    return upper, lower


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
    "N·m",       # SI moment (human-readable deliverables)
    "N·mm",      # SI moment (sbeam solver deck -- consistent N/mm set, M4-20 D-19)
    "kPa",       # SI design pressure
    "MPa",       # SI design pressure (sbeam solver deck -- N/mm^2, M4-20 D-19)
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


# The ULTIMATE-marked units string for each load unit. All load output is ULTIMATE,
# so the ``-ULT`` marker is part of the load's units string (lbs-ULT, Nm-ULT, ...) --
# "limit vs. ultimate" is treated as a property of the unit, like lb vs. N. See
# CLAUDE.md "Ultimate-load output". Non-load quantities keep their plain units.
_ULT_UNITS = {
    "lb": "lbs-ULT",       # force (lbf)
    "ft-lb": "ft-lb-ULT",  # moment / torque
    "lb-in": "lb-in-ULT",  # moment
    "lb/in^2": "lb/in^2-ULT",  # design pressure (psi)
    "N": "N-ULT",          # SI force
    "N·m": "Nm-ULT",       # SI moment
    "N·mm": "Nmm-ULT",     # SI moment, solver deck
    "kPa": "kPa-ULT",      # SI design pressure
    "MPa": "MPa-ULT",      # SI design pressure, solver deck (N/mm^2)
}


def _ult_units(units: str, quantity: str = "") -> str:
    """The ULTIMATE-marked units string for a load; plain units pass through.

    A load unit takes its ``-ULT`` marker (``lb`` -> ``lbs-ULT``, ``N·m`` ->
    ``Nm-ULT``); a non-load quantity (weight, length, inertia, area, speed, angle,
    dimensionless load factor) is returned unchanged.
    """
    if not _is_load_unit(units, quantity):
        return units
    return _ULT_UNITS.get(units, f"{units}-ULT")


def _ult(value, units: str, quantity: str, sf: float):
    """Scale a single value to ultimate if its units mark it as a load; else pass through."""
    if value == "" or value is None:
        return value
    return value * sf if _is_load_unit(units, quantity) else value


# Public wrappers over the ultimate boundary above, so callers outside this module
# (the governing-loads views) get ULTIMATE marking/scaling through report.py rather
# than hand-formatting -- the boundary stays owned here (CLAUDE.md: applied "once,
# at the render/export boundary").
def ultimate_units(units: str, quantity: str = "") -> str:
    """The ULTIMATE-marked units string for a load; non-load units pass through unchanged."""
    return _ult_units(units, quantity)


def to_ultimate(value, units: str, quantity: str = "", sf: float = ULTIMATE_FACTOR):
    """Scale a value to ULTIMATE (= value x ``sf``) when its units mark it a load; else pass through."""
    return _ult(value, units, quantity, sf)


def results_to_rows(results: List[ConditionResult]) -> List[Dict[str, str]]:
    """Flatten results into rows suitable for a dataframe/table.

    Load quantities (forces/moments/pressures) are reported as ULTIMATE = limit x
    the case ``safety_factor``, carry the ``-ULT`` marker in their units string and
    that factor in the ``SF`` column; non-load quantities (weights, positions,
    inertias, load factors) pass through unscaled with plain units and a blank ``SF``.

    **Data-shaped floor (#95, C210-8, owner directive):** a column that is
    empty in every row is dropped, so a property-table module (geometry, mass
    properties) renders as Condition / FAR / Quantity / Value / Units instead
    of carrying the load-case table's blank ID / Component / CG / Speed /
    Altitude / SF columns -- and a module whose conditions do carry case
    identity keeps exactly the columns its data fills.
    """
    rows: List[Dict[str, str]] = []
    for r in results:
        ref = r.case_ref
        for v in r.values:
            is_load = _is_load_unit(v.units, v.quantity)
            value = v.value * r.safety_factor if is_load else v.value
            rows.append(
                {
                    "ID": ref.case_id if ref else "",
                    "FAR": r.far_reference,
                    "Condition": r.title,
                    "Component": ref.component if ref else "",
                    "CG": ref.cg if ref else "",
                    "Speed (kt)": format_value(ref.speed_kt) if ref and ref.speed_kt is not None else "",
                    "Altitude (ft)": format_value(ref.altitude_ft) if ref and ref.altitude_ft is not None else "",
                    "Quantity": v.label,
                    "Value": format_value(value),
                    "Units": _ult_units(v.units, v.quantity),
                    "SF": format_value(r.safety_factor) if is_load else "",
                }
            )
    empty = {col for col in (rows[0] if rows else {})
             if all(not row[col] for row in rows)}
    return [{col: cell for col, cell in row.items() if col not in empty}
            for row in rows]


# --------------------------------------------------------------------------- #
# Governing-loads table (SELECT critical conditions, per component)
# --------------------------------------------------------------------------- #
def _display_loads(loads: List[LoadValue], system: UnitSystem) -> List[LoadValue]:
    """Display-only copy of a ``CriticalCondition.loads`` list converted to ``system``.

    ``CriticalCondition`` carries a bare ``List[LoadValue]`` (not a
    :class:`ConditionResult`), so it is wrapped/unwrapped around
    :func:`~sloads.units.convert_results` rather than mutating the condition itself.
    Imperial is a no-op.
    """
    if system == UnitSystem.IMPERIAL:
        return loads
    wrapped = ConditionResult(title="", far_reference="", values=loads)
    return convert_results([wrapped], system)[0].values


def governing_loads_table(
    conditions: List[CriticalCondition],
    system: UnitSystem = UnitSystem.IMPERIAL,
) -> List[Dict[str, object]]:
    """Rows for one component's governing (SELECT critical) loads, rendered ULTIMATE.

    Each :class:`CriticalCondition`'s ``loads`` are converted to ``system`` display
    units, then every *load* quantity (force/moment/pressure) is scaled to ULTIMATE
    (= limit x **that condition's own** ``safety_factor``) and its column header
    carries the ``-ULT`` marker; dimensionless and speed quantities (n, CL, V) pass
    through unscaled and unmarked. One row per condition; a trailing ``SF`` column
    states the factor applied to *that row's* load cells. Because conditions carry
    different label sets, cells absent from a given condition render ``"—"``
    (values are formatted strings, so this stays clean).

    The factor is read per case, never assumed flat: SELECT stamps
    ``CriticalCondition.safety_factor`` (:class:`ConditionResult`'s contract, 14 CFR
    23.303 -> 1.5 by default, 1.0 for a case whose loads are already ultimate), and
    the export side scales the same way (``export.sbeam_bridge._sf``), so a report
    figure and its bulk-data card cannot state different factors for one case
    (review F-R1; M4-8 Layer 1 report-side slice). There is deliberately no
    caller-supplied override — the case is the single owner of its factor.

    Shared by the Results Review headline and the Flight Envelope Critical Loads tab
    so the two governing-loads tables cannot diverge (M2-4).
    """
    base_cols = ["ID", "LOAD", "Condition", "FAR", "V-n case"]
    load_cols: List[str] = []  # ordered union of the per-load column headers
    seen = set()
    partial: List[Dict[str, object]] = []
    for c in conditions:
        sf = c.safety_factor
        ref = getattr(c, "case_ref", None)
        row: Dict[str, object] = {
            # Case identity beside the numbers (design note 17): the id is also
            # the deck's LABEL, and LOAD is the integer that deck uses for both
            # its SUBCASE and its load-set SID. These are per-component
            # conditions, so the number quoted is the component deck's; the case
            # index is where the full definition lives.
            "ID": ref.case_id if ref else "—",
            "LOAD": (deck_load_id(ref.case_id) or NO_LOAD_ID) if ref else NO_LOAD_ID,
            "Condition": c.label,
            "FAR": c.far_reference,
            "V-n case": _num(c.case) if c.case is not None else "—",
            "SF": format_value(sf),
        }
        for lv in _display_loads(c.loads, system):
            u = ultimate_units(lv.units, lv.quantity)
            header = f"{lv.label} ({u})" if u else lv.label
            if header not in seen:
                seen.add(header)
                load_cols.append(header)
            row[header] = format_value(to_ultimate(lv.value, lv.units, lv.quantity, sf))
        partial.append(row)

    return _union_rows(partial, base_cols, load_cols)


def _union_rows(partial: List[Dict[str, object]], base_cols: List[str],
                load_cols: List[str]) -> List[Dict[str, object]]:
    """Square per-condition dicts up over the union of quantity columns.

    The one-line-per-case core shared by :func:`governing_loads_table` and
    :func:`critical_rows` (#95, C210-27 -- M2-4's "cannot diverge" argument,
    kept structural): conditions carry different label sets, so every row gets
    every column, absent cells as ``"—"``, and the per-row ``SF`` closes the
    row.
    """
    rows: List[Dict[str, object]] = []
    for row in partial:
        full: Dict[str, object] = {col: row.get(col, "—") for col in base_cols}
        for col in load_cols:
            full[col] = row.get(col, "—")
        full["SF"] = row["SF"]
        rows.append(full)
    return rows


def critical_rows(results: List[ConditionResult]) -> List[Dict[str, object]]:
    """One row per critical condition -- SELECT's summary shape (#95, C210-27).

    The owner directive ("the SELECT table should be one line per case") for
    the channels that hold :class:`ConditionResult`\\ s rather than
    :class:`CriticalCondition`\\ s -- the module CSV and the oracle results
    page. Same semantics as :func:`governing_loads_table` through the same
    helpers (``to_ultimate`` / ``ultimate_units`` / ``deck_load_id`` /
    :func:`_union_rows`): every *load* cell is ULTIMATE by **that row's own**
    ``safety_factor``, stated in the trailing ``SF`` column; dimensionless and
    speed quantities pass through unscaled. Values are rendered in whatever
    units the results already carry -- convert first, as every rows caller
    does. The stacked one-row-per-quantity shape this replaces put SELECT's 27
    conditions on ~150 rows with the per-case SF invisible wherever a wing
    case's quantities were all non-loads.
    """
    base_cols = ["ID", "LOAD", "Component", "Condition", "FAR"]
    load_cols: List[str] = []
    seen = set()
    partial: List[Dict[str, object]] = []
    for r in results:
        ref = r.case_ref
        row: Dict[str, object] = {
            "ID": ref.case_id if ref else "—",
            "LOAD": (deck_load_id(ref.case_id) or NO_LOAD_ID) if ref else NO_LOAD_ID,
            "Component": ref.component if ref else "—",
            "Condition": r.title,
            "FAR": r.far_reference,
            "SF": format_value(r.safety_factor),
        }
        for lv in r.values:
            u = _ult_units(lv.units, lv.quantity)
            header = f"{lv.label} ({u})" if u else lv.label
            if header not in seen:
                seen.add(header)
                load_cols.append(header)
            row[header] = format_value(
                _ult(lv.value, lv.units, lv.quantity, r.safety_factor))
        partial.append(row)
    return _union_rows(partial, base_cols, load_cols)


#: Weight/station pair-folding key suffixes (:func:`weight_station_rows`).
_PAIR_SUFFIXES = ("_weight", "_station", "_point")


def _pair_stem(key: str) -> str:
    """The shared stem of a ``*_weight`` / ``*_station`` key pair.

    Not a bounded search (test_convergence's #33 class): every pass strips
    what it finds and the loop ends when a pass strips nothing.
    """
    stripped = True
    while stripped:
        stripped = False
        for suffix in _PAIR_SUFFIXES:
            if key.endswith(suffix):
                key = key[: -len(suffix)]
                stripped = True
    return key


def _pair_label(label: str) -> str:
    """The folded row's name: the value label minus its weight/station word."""
    words = label.split()
    if words and words[-1].lower() in ("weight", "station"):
        words = words[:-1]
    if words and words[-1].lower() == "point":
        words = words[:-1]
    return " ".join(words) or label


def weight_station_rows(results: List[ConditionResult]) -> List[Dict[str, object]]:
    """WTENV's summary shape: one row per (weight, station) point (#95, C210-8).

    The owner's Weight & Mass extension: the loading envelope as (weight,
    station) rows rather than "Point N weight" / "Point N station" stacked
    values, the CG-limit block as corner x (station, weight), and every paired
    "X weight / X station" folded into one row per point. Pairing is by the
    machine ``LoadValue.key`` (M4-9 -- labels are display text and free to
    reword): keys reduce to a stem by stripping ``_weight`` / ``_station`` /
    ``_point`` suffixes, and a stem holding both a weight and a station folds.
    An unpaired value (a ballast "none" marker) keeps its full label and
    leaves the other cell ``"—"``. Everything here is mass/geometry -- no load
    quantity, no SF column (M4-8: the factor is stated where it is applied).
    Units come from the values themselves, so a converted result set renders
    its own system's headers.
    """
    weight_units = next((v.units for r in results for v in r.values
                         if v.quantity == "mass"), "lb")
    station_units = next((v.units for r in results for v in r.values
                          if v.quantity != "mass"), "in")
    weight_col = f"Weight ({weight_units})"
    station_col = f"Station ({station_units})"
    rows: List[Dict[str, object]] = []
    for r in results:
        by_stem: Dict[str, Dict[str, object]] = {}
        for v in r.values:
            stem = _pair_stem(v.key or v.label)
            row = by_stem.get(stem)
            if row is None:
                row = by_stem[stem] = {
                    "Condition": r.title, "FAR": r.far_reference,
                    "Point": _pair_label(v.label),
                    weight_col: "—", station_col: "—",
                }
                rows.append(row)
            row[weight_col if v.quantity == "mass" else station_col] = \
                format_value(v.value)
            if v.quantity == "mass":
                # The weight label names the point; a station-first pair
                # (the CG-limit block lists stations before weights) still
                # ends up named by its weight value's label.
                row["Point"] = _pair_label(v.label)
    return rows


#: Module-specific summary shapes (#95, C210-8/27): ``{module: rows builder}``.
#: :func:`summary_rows` is the **one dispatch** both the on-screen table and
#: the module CSV render through -- re-shaping one channel alone would print
#: the same data two ways, which is exactly what the owner's CSV ruling
#: (2026-08-26) forbids. Guarded in ``tests/test_summary_shapes.py``.
SUMMARY_SHAPES: Dict[str, Callable[[List[ConditionResult]], List[Dict[str, object]]]] = {
    "select": critical_rows,
    "weight_envelope": weight_station_rows,
}

#: For a one-line-per-case shape, the column the on-screen renderer may group
#: the rows by (one sub-table per component, M2-4's Results Review layout);
#: the CSV keeps the rows flat under the same columns.
SUMMARY_GROUP_BY: Dict[str, str] = {"select": "Component"}


def summary_rows(module: str, results: List[ConditionResult]) -> List[Dict[str, object]]:
    """The one summary-table shape for a module's conditions (#95, C210-8/27).

    Load-case data renders through :func:`load_cases_to_rows` unchanged; a
    module with a registered :data:`SUMMARY_SHAPES` entry gets its data-shaped
    table; everything else gets the pruned :func:`results_to_rows` floor.
    Convert the conditions to the deliverable system first -- every shape here
    renders the units the values carry.
    """
    if has_load_case_data(results):
        return load_cases_to_rows(results)
    shaper = SUMMARY_SHAPES.get(module)
    if shaper is not None:
        return shaper(results)
    return [dict(row) for row in results_to_rows(results)]


# --------------------------------------------------------------------------- #
# Load-case table (one row per structural load case)
# --------------------------------------------------------------------------- #
# The flat load-case schema is assembled by ``LoadValue.key`` (M4-9). It used to
# match on the display label, so rewording a label silently blanked the column:
# the lookup returned ``None``, ``_val`` turned that into ``""`` and the renderer
# wrote an empty cell with no error anywhere. Keys are the calc's machine
# identity for a quantity and live in :mod:`sloads.load_keys`.
_GYRO_FAR = "23.371(b)"


def has_load_case_data(results: List[ConditionResult]) -> bool:
    """True if these results carry structural load-case data (forces/moments at a
    point), i.e. the ``load_cases_to_rows`` schema applies.

    Mass-properties and other property-table modules emit none of those keys, so
    this returns False for them and callers fall back to the generic table.
    """
    for r in results:
        if r.far_reference == _GYRO_FAR:
            return True
        for v in r.values:
            if v.key in LOAD_CASE_KEYS:
                return True
    return False


def _find(values: List[LoadValue], key: str) -> Optional[LoadValue]:
    for v in values:
        if v.key == key:
            return v
    return None


def _find_any(values: List[LoadValue], keys) -> Optional[LoadValue]:
    for key in keys:
        v = _find(values, key)
        if v is not None:
            return v
    return None


def _detect_unit(results, keys) -> str:
    for r in results:
        for v in r.values:
            if v.key in keys and v.units:
                return v.units
    return ""


def _detect_moment_unit(results) -> str:
    for r in results:
        for v in r.values:
            if v.units in ("ft-lb", "N·m"):
                return v.units
    return "ft-lb"


def _result_location(r: ConditionResult) -> Optional[tuple]:
    locs = [_find(r.values, k) for k in LOC_KEYS]
    if all(locs):
        return tuple(v.value for v in locs if v is not None)
    return None


def _global_location(results):
    for r in results:
        loc = _result_location(r)
        if loc is not None:
            return loc
    return (None, None, None)


def _val(loadvalue: Optional[LoadValue]):
    return loadvalue.value if loadvalue is not None else ""


_GYRO_SUBCASE_SUFFIX = "abcd"  # sign-combination order matches condition_371_b's itertools.product


def _gyro_subcase_id(r: ConditionResult, num: int) -> str:
    """The sub-case ID for one gyro sign-combination: the condition's calc-minted
    EM- id with an a/b/c/d suffix (the model has no way to carry 4 case_refs on
    one ConditionResult -- see docs/30_future/00_backlog.md Step D1)."""
    if r.case_ref is None:
        return ""
    idx = num - 1
    suffix = _GYRO_SUBCASE_SUFFIX[idx] if 0 <= idx < len(_GYRO_SUBCASE_SUFFIX) else str(num)
    return f"{r.case_ref.case_id}{suffix}"


#: The gyro sub-case *description* is the only thing still read off the label —
#: deliberately, because it is display text ("Case 1 (+Myy, +Mzz)"). Which rows
#: exist, and which component each value is, come from the key (M4-9); this regex
#: only strips the trailing ": Myy"/": Mzz" component tag off the label so the
#: same descriptive prefix is not repeated twice in the row. A relabel now
#: degrades the wording of one cell instead of dropping the row.
_GYRO_LABEL_TAIL = re.compile(r":\s*(?:Myy|Mzz)\s*$")


def _gyro_subcases(r: ConditionResult):
    """Yield (description, Myy, Mzz, thrust, vertical, case_id) for each gyro load
    case.

    The 2.5g vertical load and max-continuous thrust are constant across all four
    sign combinations; only the gyroscopic moments vary.
    """
    thrust = _val(_find(r.values, FX_THRUST))
    vertical = _val(_find(r.values, FZ_VERTICAL_2_5G))
    cases: Dict[int, Dict[str, object]] = {}
    for v in r.values:
        parsed = parse_gyro_key(v.key)
        if parsed is None:
            continue
        num, comp = parsed
        case = cases.setdefault(num, {"desc": _GYRO_LABEL_TAIL.sub("", v.label)})
        case[comp] = v.value
    for num in sorted(cases):
        c = cases[num]
        desc = f"{r.title} — {c['desc']}"
        yield desc, c.get("myy", ""), c.get("mzz", ""), thrust, vertical, _gyro_subcase_id(r, num)


def load_cases_to_rows(results: List[ConditionResult]) -> List[Dict[str, object]]:
    """One row per structural load case: ID, description, location, applied loads.

    Each row carries the load components an engine mount must react -- vertical,
    side and thrust forces plus the engine-mount (roll), pitch (Myy) and yaw
    (Mzz) moments -- at the combined engine+prop CG. Blank cells mean a component
    does not apply to that case. The gyroscopic condition (FAR 23.371(b)) expands
    into its four sign-combination cases. Units follow whatever the results carry
    (Imperial or SI), shown in the column headers.

    Forces and moments are reported as ULTIMATE loads (= limit x the case
    ``safety_factor``); the ``-ULT`` marker is part of the load's units string
    (``lbs-ULT``/``Nm-ULT``/...) and the per-case factor is in the ``SF`` column.
    Locations are geometry and are not scaled (plain units).
    """
    force_u = _detect_unit(results, set(VERTICAL_KEYS) | {FY_SIDE, FX_THRUST}) or "lb"
    len_u = _detect_unit(results, set(LOC_KEYS)) or "in"
    mom_u = _detect_unit(results, {MX_MOUNT_TORQUE}) or _detect_moment_unit(results)
    force_ult = _ult_units(force_u)
    mom_ult = _ult_units(mom_u)
    g_loc = _global_location(results)

    c_id = f"Loc X ({len_u})", f"Loc Y ({len_u})", f"Loc Z ({len_u})"
    c_vert = f"Vertical load ({force_ult})"
    c_side = f"Side load ({force_ult})"
    c_thr = f"Thrust ({force_ult})"
    c_roll = f"Engine mount torque ({mom_ult})"
    c_pitch = f"Pitch moment Myy ({mom_ult})"
    c_yaw = f"Yaw moment Mzz ({mom_ult})"

    def row(idx, far, desc, loc, sf, *, fz="", fy="", fx="", mx="", my="", mz="",
            case_id="", case_ref=None):
        x, y, z = loc
        # The structured id (case_ref.case_id or a gyro sub-case id) is used when
        # present; LC{idx} is only a fallback for results with no case_ref yet
        # (see docs/30_future/00_backlog.md Step D1) so nothing renders blank.
        return {
            "ID": case_id or f"LC{idx}",
            "FAR": far,
            "Case description": desc,
            "Component": case_ref.component if case_ref else "",
            "Condition": case_ref.condition if case_ref else "",
            "CG": case_ref.cg if case_ref else "",
            "Speed (kt)": _num(case_ref.speed_kt) if case_ref and case_ref.speed_kt is not None else "",
            "Altitude (ft)": _num(case_ref.altitude_ft) if case_ref and case_ref.altitude_ft is not None else "",
            "SF": format_value(sf),
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
            for desc, my, mz, fx, fz, gyro_id in _gyro_subcases(r):
                idx += 1
                rows.append(row(idx, r.far_reference, desc, loc, sf, fz=fz, fx=fx, my=my, mz=mz,
                                case_id=gyro_id, case_ref=r.case_ref))
        else:
            idx += 1
            case_id = r.case_ref.case_id if r.case_ref else ""
            rows.append(
                row(
                    idx,
                    r.far_reference,
                    r.title,
                    loc,
                    sf,
                    fz=_val(_find_any(r.values, VERTICAL_KEYS)),
                    fy=_val(_find(r.values, FY_SIDE)),
                    mx=_val(_find(r.values, MX_MOUNT_TORQUE)),
                    case_id=case_id,
                    case_ref=r.case_ref,
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
    return format_value(value)


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
        lines.append(f"  FAR {r.far_reference}   [ULTIMATE, SF={format_value(r.safety_factor)}]")
        for v in r.values:
            unit_str = _ult_units(v.units, v.quantity)
            unit = f" {unit_str}" if unit_str else ""
            value = _ult(v.value, v.units, v.quantity, r.safety_factor)
            lines.append(f"    {v.label:<38}{format_value(value)}{unit}")
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
        lines.append(f"  FAR {r.far_reference}   [ULTIMATE, SF={format_value(r.safety_factor)}]")
        for v in r.values:
            unit_str = _ult_units(v.units, v.quantity)
            unit = f" {unit_str}" if unit_str else ""
            value = _ult(v.value, v.units, v.quantity, r.safety_factor)
            lines.append(f"    {v.label:<38}{format_value(value)}{unit}")
        if r.note:
            lines.append(f"    NOTE: {r.note}")
        lines.append("")

    return "\n".join(lines)
