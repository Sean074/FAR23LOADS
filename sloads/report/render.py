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
from enum import Enum
from typing import Callable, Dict, List, Optional

from ..case_ids import NO_LOAD_ID, deck_load_id
from ..frames import is_report_only
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
from ..units import is_load_unit as _is_load_unit


def format_value(value: float) -> str:
    """Format one numeric cell for a table or the text report.

    Public since G8.1: it was ``_fmt``, but ``tests/test_results_review.py``
    already imported it across the module boundary, which the M4-12b public-symbol
    contract (``PROJECT_GUIDE`` §5) makes a defect rather than a shortcut. Promoted
    rather than re-exported under its private name.

    **Quantized first, because a printed byte may not hang on the last ulp**
    (``CONVENTIONS.md`` §7 "platform-stable deliverable bytes", #147). The two
    branches below are far apart -- an integral value prints in full, everything
    else at four significant figures -- so on the raw double they made a
    *discontinuous* function of it: ``-687258.0`` printed ``-687258`` while
    ``-687257.9999999999``, the same load rotated through one more cosine,
    printed ``-6.873e+05``. Both spellings shipped in one landing case, and the
    choice between them moved with the libm build: macOS and glibc disagree in
    the last ulp of ``sin``/``cos``, so the frozen Imperial digest passed on the
    developer's Mac and failed on the Linux CI leg. Rounding to twelve
    significant figures first absorbs any such difference (~1e-12 relative,
    four orders above a double's ulp and far below anything a load means) and
    makes both branches read the same number the reader sees. The residual knife
    edge is a value within an ulp of a *twelfth*-digit boundary, which no
    quantization can remove and no deliverable distinguishes.
    """
    if isinstance(value, int):
        return str(value)
    value = float(f"{value:.12g}")
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
# convention: limit load factor, ultimate load). *Which* units those are is
# ``units.LOAD_UNITS`` / ``units.is_load_unit``, imported above: the rule has a
# second consumer since note 48 (``safety_factors.prescribes_factor``), so it has
# one owner rather than a copy here (CLAUDE.md rule 3).

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


# The public marking wrapper. There is no scaling wrapper any more: note 49
# OR-116 removed the multiply, so the boundary marks and never scales, and
# ``ultimate_units`` marks only a load already at SF = 1.0 (OR-118).
def ultimate_units(units: str, quantity: str = "") -> str:
    """The ULTIMATE-marked units string for a load; non-load units pass through unchanged."""
    return _ult_units(units, quantity)


# --------------------------------------------------------------------------- #
# The two channels (design note 48, OR-76 / OR-77)
# --------------------------------------------------------------------------- #
class LoadChannel(str, Enum):
    """Which basis a render states its loads on -- and since note 49 OR-116
    there is only one.

    LIMIT is every surface: the calc's own values, no factor applied, the
    factor stated in the ``SF`` column. The ``ULTIMATE`` member is **gone**, and
    with it the two multiplies that were the last in ``sloads/`` (G-OR-71).

    The type survives with a single member rather than being deleted outright
    because every caller in the frozen ``app/views/`` names it explicitly
    (``channel=LoadChannel.LIMIT``, opted in by note 48 OR-77) and those files
    cannot be edited until the #29 freeze lifts. Removing the member rather
    than the type is what makes the change loud: any code still asking for the
    ultimate channel fails at import instead of silently getting limit loads.
    The parameter itself goes at #29.
    """

    LIMIT = "limit"


def _chan_value(value, units: str, quantity: str, sf: Optional[float],
                channel: "LoadChannel"):
    """One value, verbatim: no surface scales a load (note 49 OR-116)."""
    del units, quantity, sf, channel      # one basis; nothing to dispatch on
    return value


def _chan_units(units: str, quantity: str, channel: "LoadChannel",
                sf: Optional[float] = None) -> str:
    """One units string on ``channel``.

    On LIMIT -- the project's only basis since note 49 OR-116 -- a load is plain
    and its factor is stated in the ``SF`` column. The one exception is a load
    that is **already ultimate**: ``engine_ultimate`` (23.367(a)(2)) and
    ``emergency`` (23.561(b)) are computed at ``SF = 1.0`` and cannot be
    un-factored, so the ``-ULT`` marker survives on exactly those and nowhere
    else (OR-118). The marker is now rare, which is what makes it worth having.

    ``sf`` is the factor of the case this units string belongs to. For a
    **shared column header** spanning many cases, pass :func:`_table_sf`, which
    yields 1.0 only when every case in the table is already ultimate -- a header
    must never state a basis true of only some of its rows (OR-118a).
    """
    del channel                             # one basis (OR-116)
    return _ult_units(units, quantity) if sf == 1.0 else units


def _table_sf(results) -> Optional[float]:
    """``1.0`` when every result in a table is already ultimate, else ``None``.

    The basis a *shared* column header may state (OR-118a). A mixed table has
    none, so its header stays plain and the per-case ``SF`` column carries the
    distinction.
    """
    factors = [getattr(r, "safety_factor", None) for r in results]
    return 1.0 if factors and all(f == 1.0 for f in factors) else None


def _sf_cell(sf: Optional[float]) -> str:
    """The ``SF`` cell for a case: the factor, or ``N/A`` where none is prescribed.

    ``None`` is not 1.0 (#154, note 48 OR-82): a geometry table prescribes no
    factor at all, and printing 1.0 would state that one applies and happens to
    be unity.
    """
    return "N/A" if sf is None else format_value(sf)


def _channel_header(channel: "LoadChannel") -> str:
    """The one-line basis statement at the top of a text report.

    It states who applies the 23.303 factor, which ``CONVENTIONS.md`` §3
    requires of every load surface now that none of them applies it.
    """
    del channel                             # one basis (OR-116)
    return ("Loads are LIMIT: the safety factor of 14 CFR 23.303 is stated "
            "per case and applied nowhere in sloads, including the exported "
            "deck. Apply it in the sizing analysis. Load factors are limit. "
            "A load marked -ULT is already ultimate; apply nothing further.")


def _channel_banner(channel: "LoadChannel", sf: Optional[float]) -> str:
    """The per-case basis marker in the text report."""
    del channel                             # one basis (OR-116)
    if sf is None:
        return "[LIMIT, no safety factor applies]"
    if sf == 1.0:
        return "[already ultimate, SF=1.0 — apply nothing further]"
    return f"[LIMIT, SF={format_value(sf)} — apply in the sizing analysis]"


def results_to_rows(results: List[ConditionResult], *,
                    channel: LoadChannel = LoadChannel.LIMIT,
                    ) -> List[Dict[str, str]]:
    """Flatten results into rows suitable for a dataframe/table.

    On the ULTIMATE channel (the default — OR-77) load quantities are reported as
    limit x the case ``safety_factor``, carry the ``-ULT`` marker in their units
    string and that factor in the ``SF`` column. On the LIMIT channel they are the
    calc's own values with plain units, and the ``SF`` column states the factor
    that will apply at the deliverable without applying it. Non-load quantities
    (weights, positions, inertias, load factors) pass through unscaled with plain
    units and a blank ``SF`` on both. A condition that prescribes no factor at all
    shows ``N/A`` (#154, note 48 OR-82).

    **Data-shaped floor (#95, C210-8, owner directive):** a column that is
    empty in every row is dropped, so a property-table module (geometry, mass
    properties) renders as Condition / FAR / Quantity / Value / Units instead
    of carrying the load-case table's blank ID / Component / CG / Speed /
    Altitude / SF columns -- and a module whose conditions do carry case
    identity keeps exactly the columns its data fills.

    **Frame floor (design note 38 GF-6):** a value stated in the ground-line
    frame is the manual's analysis view, not a delivered load, and is dropped
    here -- :func:`sloads.frames.is_report_only` is the one rule. This is the
    **only** channel that drops it: :func:`module_text_report` renders
    ``r.values`` whole, so the primed set stays in the text report beside the
    body-frame deliverable rather than disappearing from the suite. A value with
    no frame (a sink rate, a load factor, a ground angle) is delivered as before.

    **The frame and the point are stated in-band (#141):** the ``Frame`` and
    ``Applied at`` columns carry :attr:`~sloads.models.LoadValue.frame` and
    :attr:`~sloads.models.LoadValue.point` verbatim, so a CSV forwarded on its
    own says which frame its numbers are in and which named point each force
    acts at. Both words already lived on the value; this channel used to drop
    them, leaving the application point stated only numerically (``x``/``y``/``z``
    per gear) and the frame only in the condition note, which the CSV also
    drops. They are ordinary columns, so the all-empty prune above removes both
    from every module that names neither -- no other module's CSV changes.
    """
    rows: List[Dict[str, str]] = []
    for r in results:
        ref = r.case_ref
        for v in r.values:
            if is_report_only(v.frame):
                continue
            is_load = _is_load_unit(v.units, v.quantity)
            value = _chan_value(v.value, v.units, v.quantity,
                                r.safety_factor, channel)
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
                    "Units": _chan_units(v.units, v.quantity, channel, r.safety_factor),
                    "SF": _sf_cell(r.safety_factor) if is_load else "",
                    "Frame": v.frame,
                    "Applied at": v.point,
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
    table_sf = _table_sf(conditions)
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
            "SF": _sf_cell(sf),
        }
        for lv in _display_loads(c.loads, system):
            # LIMIT, with the factor stated in the ``SF`` cell above (note 49
            # OR-116). The header takes the table-wide basis (OR-118a), so a set
            # mixing an already-ultimate case with limit ones stays plain and
            # the distinction is read per row.
            u = _chan_units(lv.units, lv.quantity, LoadChannel.LIMIT, table_sf)
            header = f"{lv.label} ({u})" if u else lv.label
            if header not in seen:
                seen.add(header)
                load_cols.append(header)
            row[header] = format_value(lv.value)
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


def critical_rows(results: List[ConditionResult], *,
                  channel: LoadChannel = LoadChannel.LIMIT,
                  ) -> List[Dict[str, object]]:
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
            "SF": _sf_cell(r.safety_factor),
        }
        for lv in r.values:
            u = _chan_units(lv.units, lv.quantity, channel, r.safety_factor)
            header = f"{lv.label} ({u})" if u else lv.label
            if header not in seen:
                seen.add(header)
                load_cols.append(header)
            row[header] = format_value(
                _chan_value(lv.value, lv.units, lv.quantity,
                            r.safety_factor, channel))
        partial.append(row)
    return _union_rows(partial, base_cols, load_cols)


#: Weight/station pair-folding key suffixes (:func:`weight_station_rows`).
#: ``_waterline`` joined at design note 45: WTENV's envelope vertices carry the
#: ``ZBAR`` column the original prints, and a vertex is one point whether it
#: states two coordinates or three.
_PAIR_SUFFIXES = ("_weight", "_station", "_waterline", "_point")


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
    if words and words[-1].lower() in ("weight", "station", "waterline"):
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
    waterline_col = f"Waterline ({station_units})"
    # The waterline column appears only when something in this result set has
    # one (note 45): WTENV's envelope vertices do, its summary and CG-limit
    # blocks do not, and a result set with no waterline anywhere -- an isolated
    # ballast marker, say -- keeps the two-column shape it has always had.
    has_waterline = any((v.key or "").endswith("_waterline")
                        for r in results for v in r.values)
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
                if has_waterline:
                    row[waterline_col] = "—"
                rows.append(row)
            # Routed by key, not by ``quantity``: a waterline and a station are
            # both lengths and both carry an empty quantity, so the dimension
            # hint cannot tell them apart.
            if (v.key or "").endswith("_waterline"):
                column = waterline_col
            elif v.quantity == "mass":
                column = weight_col
            else:
                column = station_col
            row[column] = format_value(v.value)
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

#: The registered shapes that render **load** values and therefore take the
#: channel. ``weight_envelope``'s rows are weights and stations -- never loads --
#: so it takes none rather than accepting one and ignoring it. A new shape that
#: renders loads and is not named here would silently stay ULTIMATE on a LIMIT
#: surface; ``tests/test_limit_channel.py`` (G-OR-47) is what catches that, by
#: scanning every module's LIMIT render for a ``-ULT`` marker.
_CHANNELLED_SHAPES = {"select"}

#: For a one-line-per-case shape, the column the on-screen renderer may group
#: the rows by (one sub-table per component, M2-4's Results Review layout);
#: the CSV keeps the rows flat under the same columns.
SUMMARY_GROUP_BY: Dict[str, str] = {"select": "Component"}


def summary_rows(module: str, results: List[ConditionResult], *,
                 channel: LoadChannel = LoadChannel.LIMIT,
                 ) -> List[Dict[str, object]]:
    """The one summary-table shape for a module's conditions (#95, C210-8/27).

    Load-case data renders through :func:`load_cases_to_rows` unchanged; a
    module with a registered :data:`SUMMARY_SHAPES` entry gets its data-shaped
    table; everything else gets the pruned :func:`results_to_rows` floor.
    Convert the conditions to the deliverable system first -- every shape here
    renders the units the values carry.
    """
    if has_load_case_data(results):
        return load_cases_to_rows(results, channel=channel)
    shaper = SUMMARY_SHAPES.get(module)
    if shaper is not None:
        if module in _CHANNELLED_SHAPES:
            return shaper(results, channel=channel)  # type: ignore[call-arg]
        return shaper(results)
    return [dict(row) for row in results_to_rows(results, channel=channel)]


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


def load_cases_to_rows(results: List[ConditionResult], *,
                       channel: LoadChannel = LoadChannel.LIMIT,
                       ) -> List[Dict[str, object]]:
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
    table_sf = _table_sf(results)
    force_ult = _chan_units(force_u, "", channel, table_sf)
    mom_ult = _chan_units(mom_u, "", channel, table_sf)
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
            "SF": _sf_cell(sf),
            c_id[0]: _num(x),
            c_id[1]: _num(y),
            c_id[2]: _num(z),
            c_vert: _num(_cell_value(fz, sf, channel)),
            c_side: _num(_cell_value(fy, sf, channel)),
            c_thr: _num(_cell_value(fx, sf, channel)),
            c_roll: _num(_cell_value(mx, sf, channel)),
            c_pitch: _num(_cell_value(my, sf, channel)),
            c_yaw: _num(_cell_value(mz, sf, channel)),
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


def _cell_value(value, sf: Optional[float],
                channel: LoadChannel = LoadChannel.LIMIT):
    """A force/moment cell: the calc's own value; blank cells stay blank.

    Was ``_scale``, and scaled. Nothing scales since note 49 OR-116 -- the
    factor is carried by the row's ``SF`` cell instead.
    """
    del sf, channel                         # one basis (OR-116)
    if value == "" or value is None:
        return value
    return value


def _num(value) -> str:
    """Format a numeric cell; blank for missing components."""
    if value == "" or value is None:
        return ""
    return format_value(value)


def module_text_report(title: str, results: List[ConditionResult], *,
                       channel: LoadChannel = LoadChannel.LIMIT) -> str:
    """A clean fixed-width text report for any module's results.

    Module-agnostic (no engine-specific header), so the CLI can print results for
    modules whose inputs are not the engine slice. ``channel`` has one value
    since note 49 OR-116 and survives only for the frozen ``app/views/`` callers
    that name it; it goes at #29.
    """
    lines: List[str] = [title.upper(), "=" * 60]
    lines.append(_channel_header(channel))
    lines.append("")
    for r in results:
        lines.append(f"{r.title}")
        lines.append(f"  FAR {r.far_reference}   "
                     f"{_channel_banner(channel, r.safety_factor)}")
        for v in r.values:
            unit_str = _chan_units(v.units, v.quantity, channel, r.safety_factor)
            unit = f" {unit_str}" if unit_str else ""
            value = _chan_value(v.value, v.units, v.quantity,
                                r.safety_factor, channel)
            lines.append(f"    {v.label:<38}{format_value(value)}{unit}")
        if r.note:
            lines.append(f"    NOTE: {r.note}")
        lines.append("")
    return "\n".join(lines)


def text_report(
    inp: EngineInput, results: List[ConditionResult], unit_system: str = "",
    *, channel: LoadChannel = LoadChannel.LIMIT,
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
    lines.append(_channel_header(channel))
    lines.append("")

    for r in results:
        lines.append(f"{r.title}")
        lines.append(f"  FAR {r.far_reference}   "
                     f"{_channel_banner(channel, r.safety_factor)}")
        for v in r.values:
            unit_str = _chan_units(v.units, v.quantity, channel, r.safety_factor)
            unit = f" {unit_str}" if unit_str else ""
            value = _chan_value(v.value, v.units, v.quantity,
                                r.safety_factor, channel)
            lines.append(f"    {v.label:<38}{format_value(value)}{unit}")
        if r.note:
            lines.append(f"    NOTE: {r.note}")
        lines.append("")

    return "\n".join(lines)
