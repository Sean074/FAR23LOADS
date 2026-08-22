"""Streamlit page for the flight envelope + balancing tail loads + SELECT.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Step G3 merges the FLTLOADS V-n page and the SELECT critical-loads page into one
tabbed page (the two share the balanced V-n matrix). Builds the FAR 23.333
maneuver + gust V-n diagram and the balancing horizontal tail load at every corner
(Reference 1 Ch 8); SELECT then prunes it to the governing wing/tail/fuselage
conditions (Ch 9). The design speeds and limit load factors come from the
Structural Speeds page; the airplane-less-tail aero coefficients from the
Aerodynamic Data page; the balance geometry and weight-CG cases are read/entered
here (the rest of the FLTLOADS input set).

Two tabs:

* **V-n diagram** -- the maneuver/gust envelope + balanced corner conditions.
* **Critical Loads (SELECT)** -- the governing conditions per component, with the
  per-condition include/exclude selection carried to Results Review and exports.
"""

from __future__ import annotations

import copy
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_shell.components import active_system, gate, unit_number_input
from app_shell.widget_keys import widget_key
from sloads import (
    FlightLoadsInput,
    Project,
    SelectInput,
    UnitSystem,
    build_vn_diagram,
    convert_results,
    labels_for,
    resolve_gust_inputs,
    to_display,
    to_imperial_scalar,
)
from sloads.case_ids import case_label
from sloads.cg_cases import flight_cases
from sloads.constants import IN_PER_FT
from sloads.derived_geometry import wing_reference
from sloads.models import MissingInputError
from sloads.modules.configuration import run as configuration_run
from sloads.modules.flight_envelope import build_envelope, trim_sweep
from sloads.modules.flight_envelope import run as flt_run
from sloads.modules.landing import build_landing
from sloads.modules.select import build_critical
from sloads.modules.structural_speeds import design_speed_values
from sloads.report import governing_loads_table, module_text_report

st.title("Flight Envelope (V-n), Balancing Tail Loads & Critical Loads")
st.caption(
    "Python/Streamlit port of FLTLOADS.BAS + SELECT.BAS (Hal C. McMaster). Balances "
    "the airplane at every corner of the FAR 23.333 maneuver + gust envelope, reports "
    "the balancing horizontal-tail load, and selects the governing conditions."
)

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"length","area_sqft",...} -> unit string

if project.speeds is None:
    gate(
        "No structural speeds found. Set design speeds on the **Structural Speeds** "
        "page first — FLTLOADS reads VA/VC/VD/VF, MC/MD and the limit load factor from it.",
        "structural_speeds",
    )
    st.stop()

aero = project.aero_coeffs
if aero is None or (aero.cruise is None and aero.flaps_down is None):
    gate(
        "No aero coefficients found. Enter the cruise (and optional flaps-down) "
        "coefficient set on the **Aerodynamic Data** page first — FLTLOADS reads "
        "the airplane-less-tail CL/CD/CM polynomials from it.",
        "aero_coefficients",
    )
    st.stop()

fl = project.flight_loads or FlightLoadsInput()

# Step M2-6: the wing geometry (MAC, area S, the 25%-MAC station/waterline) is
# single-sourced from the Geometry page and shown read-only here -- it is no longer an
# editable copy on this page. ``wing_reference`` derives MAC/S/XW from the WINGGEOM wing
# surface and ZW from the parametric wing. With no wing geometry yet there is no slice
# copy left to fall back to (note 33, DS-1), so the page falls straight through to the
# Appendix A worked-example figures and still renders a V-n diagram with numbers on it.
_wr = wing_reference(project, "wing")
_has_parametric = project.geometry is not None and project.geometry.parametric is not None
mac = _wr.mac if _wr is not None else 69.246
s = _wr.s_sqft if _wr is not None else 184.125
xw = _wr.xw if _wr is not None else 80.953
zw = _wr.zw if (_wr is not None and _has_parametric) else 87.725


def _num(label: str, value: float, key: str, kind: str, fmt: str = "%.3f", min_value: Optional[float] = None) -> float:
    display_value = float(round(to_display(value, kind, system), 4))
    kwargs = {} if min_value is None else {"min_value": min_value}
    return float(st.number_input(f"{label} ({U[kind]})", value=display_value, format=fmt,
                                 key=widget_key(f"{key}_{system.value}"), **kwargs))


with st.sidebar:
    # Form + Apply (M2-3): the FLTLOADS geometry persists only on submit, so merely
    # visiting this page no longer mutates the project and trips the dirty flag. The
    # V-n diagram below always renders live from the current inputs (see the probe).
    st.header(f"Wing geometry (read-only) ({U['length']} / {U['area_sqft']})")
    st.caption(
        "Single-sourced from the **Geometry** page (Step M2-6); edit it there. "
        "MAC/S/X at 25% MAC from the wing planform, waterline from the parametric wing."
    )
    st.metric(f"Wing MAC ({U['length']})", f"{to_display(mac, 'length', system):.3f}")
    st.metric(f"Wing area S ({U['area_sqft']})", f"{to_display(s, 'area_sqft', system):.3f}")
    st.metric(f"X at 25% wing MAC ({U['length']})", f"{to_display(xw, 'length', system):.3f}")
    st.metric(f"Z (waterline) at 25% MAC ({U['length']})", f"{to_display(zw, 'length', system):.3f}")
    if _wr is None:
        gate(
            "No wing geometry yet — MAC/S/XW/ZW are showing fallback figures. Define the "
            "wing on the **Geometry** page so the flight loads use your planform.",
            "configuration_layout",
        )
    with st.form("flight_geometry_form"):
        st.subheader(f"Tail CP stations & reference Mach ({U['length']})")
        st.caption("The only FLTLOADS geometry this page owns. **Apply** to save.")
        xtc = _num("Tail CP X, flaps up XTC", fl.xtc or 253.364, "xtc", "length")
        xtf = _num("Tail CP X, flaps down XTF", fl.xtf or 261.027, "xtf", "length")
        mn = st.number_input("Reference Mach (coeffs obtained at)", min_value=0.01,
                             value=float(fl.mn) or 0.1, format="%.3f")
        applied = st.form_submit_button("Apply geometry & altitudes", type="primary")

st.caption(
    f"Aero coefficients (from the **Aerodynamic Data** page): cruise '{aero.cruise.name}'"
    + (f", flaps-down '{aero.flaps_down.name}'" if aero.flaps_down else "") + "."
)

alt_default = pd.DataFrame({"altitude_ft": fl.altitudes_ft or [0.0]})
st.subheader("Altitudes (V-n balanced at each)")
alt_df = st.data_editor(alt_default, num_rows="dynamic", hide_index=True,
                        use_container_width=True, key=widget_key("altitudes_editor"))
altitudes_ft = sorted({float(v) for v in alt_df["altitude_ft"] if pd.notna(v)}) or [0.0]
st.caption("Edit altitudes above, then **Apply geometry & altitudes** in the sidebar to save.")

cg_cases = flight_cases(project)
if not cg_cases:
    gate(
        "No FLIGHT-tagged loading scenarios found. Define them on the **Weight & "
        "Mass Properties** page (Payload Cases tab) and tag each with **FLIGHT** — "
        "FLTLOADS balances over them.",
        "weight_mass",
    )
    st.stop()
st.caption("The **FLIGHT**-tagged weight / CG cases, read from the **Weight & Mass "
           "Properties** page (not edited here).")
st.dataframe(pd.DataFrame([
    {"name": c.name, f"weight ({U['weight']})": round(to_display(c.weight_lb, "weight", system), 2),
     f"xcg ({U['length']})": round(to_display(c.xcg, "length", system), 2),
     f"zcg ({U['length']})": round(to_display(c.zcg, "length", system), 2)}
    for c in cg_cases
]), hide_index=True, use_container_width=True)

# The effective FLTLOADS input from the current widgets. Merge (never wholesale-
# replace) so fields this page doesn't show survive the persist path; the aero sets
# are owned by other pages, and the weight/CG cases left this slice entirely at
# decision G-3b -- they are read from ``weight.cg_cases`` above, never copied here.
fl_effective = fl.merged(
    xtc=to_imperial_scalar(xtc, "length", system),
    xtf=to_imperial_scalar(xtf, "length", system),
    mn=mn, altitudes_ft=altitudes_ft,
)

# Persist to the real project only on Apply. For the live diagram/SELECT/trim below,
# compute from a shallow *probe* carrying the effective input, so a plain render
# never mutates the saved project (M2-3). copy.copy shares the other slices by
# reference; the page's calc is pure (reads only), and the one intended write --
# the SELECT selection onto the shared envelope -- is gated on change below.
session_project = project
if applied:
    session_project.flight_loads = fl_effective
    st.session_state["project"] = session_project
project = copy.copy(session_project)
project.flight_loads = fl_effective

if project.is_concept:
    st.warning(
        "Concept category (C): the envelope uses the user-defined load factors and is "
        "an **unverified extrapolation** above the FAR 23 calibration band."
    )

try:
    env = build_envelope(project)
    results = convert_results(flt_run(project).conditions, system)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute the flight envelope: {exc}")
    st.stop()


# --------------------------------------------------------------------------- #
# Tab 1 -- V-n diagram + balanced flight conditions
# --------------------------------------------------------------------------- #
def _tab_vn() -> None:
    cg_names = [c.name for c in cg_cases]
    c1, c2 = st.columns([2, 1])
    selected_cg = c1.selectbox("Show CG case", cg_names) if cg_names else None
    overlay_all_alt = c2.checkbox("Overlay all altitudes", value=False)
    if overlay_all_alt:
        selected_alt = None
    else:
        selected_alt = c1.selectbox("Show altitude (ft)", altitudes_ft) if len(altitudes_ft) > 1 else altitudes_ft[0]

    pts = [p for p in env.vn if p.cg == selected_cg
           and (overlay_all_alt or p.altitude_ft == selected_alt)]

    fig = go.Figure()

    # LIMIT design-envelope backdrop rebuilt from the Structural Speeds inputs.
    envelope = None
    gust = None
    try:
        sv = design_speed_values(project, project.speeds)
    except (ValueError, ZeroDivisionError):
        sv = None
    if sv is not None:
        slope = aero.cruise.lift[1] if aero.cruise is not None else None
        mac_ft = mac / IN_PER_FT if mac else None
        gust = resolve_gust_inputs(sv.ws, selected_alt, slope, mac_ft) if not overlay_all_alt else None
        envelope = build_vn_diagram(
            vs=sv.vs, va=sv.va, vc=sv.vc, vd=sv.vd,
            n_pos=sv.n, n_neg=sv.nneg, vsf=sv.vsf, vf=sv.vf,
            flaps="both", gust=gust,
        )
        for tr in envelope.traces:
            is_gust = tr.name.startswith("Gust")
            fig.add_trace(go.Scatter(
                x=tr.v, y=tr.n, name=f"LIMIT env: {tr.name}", mode="lines",
                legendgroup="limit_env",
                line={"color": "rgba(140,140,140,0.7)",
                          "dash": "dot" if is_gust else "solid", "width": 1.5}))

    alts_to_plot = altitudes_ft if overlay_all_alt else [selected_alt]
    for alt in alts_to_plot:
        alt_pts = [p for p in pts if p.altitude_ft == alt]
        man = [p for p in alt_pts if p.condition.startswith(("STALL", "MAN"))]
        gust = [p for p in alt_pts if p.condition.startswith("GUST")]
        suffix = f" @ {alt:.0f} ft" if overlay_all_alt else ""
        fig.add_trace(go.Scatter(x=[p.v_eas_kt for p in man], y=[p.nz for p in man],
                                 name=f"maneuver{suffix}", mode="markers+lines"))
        fig.add_trace(go.Scatter(x=[p.v_eas_kt for p in gust], y=[p.nz for p in gust],
                                 name=f"gust{suffix}", mode="markers"))
    title_alt = "all altitudes" if overlay_all_alt else f"{selected_alt:.0f} ft"
    fig.update_layout(title=f"V-n diagram — {selected_cg}, {title_alt}", xaxis_title="V (KEAS)",
                      yaxis_title="Load factor NZ", legend={"orientation": "h"}, height=440)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Grey lines are the continuous **LIMIT** design envelope (stall boundary, "
        "maneuver limits and — for a single altitude — the textbook Pratt gust lines) "
        "from the **Structural Speeds** inputs; the coloured markers are the rigorous, "
        "Mach-corrected balanced corner points that feed the tail loads. The envelope "
        "should bound the markers."
    )
    if envelope is not None and gust is not None and envelope.gust_approximate:
        st.caption(
            "⚠️ LIMIT-envelope gust lines are approximate: no wing lift-curve slope "
            "(Aerodynamic Data) and/or MAC (Geometry) was available, so a textbook "
            "slope and/or Kg = 1 was used."
        )

    st.subheader("Balanced flight conditions")
    st.dataframe(pd.DataFrame({
        "case": [p.case for p in pts],
        "altitude (ft)": [p.altitude_ft for p in pts],
        "condition": [p.condition for p in pts],
        "V (KEAS)": [round(p.v_eas_kt, 1) for p in pts],
        "NZ": [round(p.nz, 2) for p in pts],
        "α (deg)": [round(p.alpha_deg, 2) for p in pts],
        "CL": [round(p.cl, 3) for p in pts],
        "M(W+F)": [round(p.m_wf) for p in pts],
        "LZW": [round(p.lzw) for p in pts],
        "LT (tail)": [round(p.lt) for p in pts],
        "DX": [round(p.dx) for p in pts],
    }), hide_index=True, use_container_width=True)

    st.download_button(
        "Download V-n data (text)", module_text_report("Flight envelope (V-n)", results),
        file_name="flight_envelope.txt", mime="text/plain", key="dl_vn_txt")


# --------------------------------------------------------------------------- #
# Tab 2 -- Critical Loads (SELECT)
# --------------------------------------------------------------------------- #
_COMPONENTS = [
    ("wing", "Wing", "PHAA / PMAA / PLAA / NMAA, accelerated & steady roll"),
    ("htail", "Horizontal tail", "balancing, maneuver, gust, unsymmetrical"),
    ("vtail", "Vertical tail", "rudder, sideslip, yaw, side gust"),
    ("fuselage", "Fuselage", "load on wing, aft bending, greatest Nz"),
]


def _select_inputs_form() -> None:
    """SELECT search inputs beyond the V-n matrix (M2R-5): the wing steady-roll
    torsion drivers (23.349(b)) and the critical-fuselage wing weight. Previously
    defaulted silently (0 / 0 / 0.09·MTOW) with no visible knob. Form + Apply, so a
    plain render never dirties the project."""
    si = project.select_input or SelectInput()
    with st.expander("SELECT search inputs (wing torsion & critical fuselage)"), st.form("select_inputs_form"):
        c1, c2, c3 = st.columns(3)
        aileron = c1.number_input(
            "Full-down aileron deflection, DN (deg)", min_value=0.0,
            value=float(si.full_down_aileron_deg),
            help="Drives the FAR 23.349(b) steady-roll wing-torsion score "
                 "(cm − 0.01·DN)·q·V²; 0 leaves the roll case out of the wing search.")
        cm = c2.number_input(
            "Basic airfoil Cm (no aileron)", value=float(si.basic_airfoil_cm),
            format="%.4f",
            help="Section pitching-moment coefficient with no aileron deflection; "
                 "pairs with DN in the wing-torsion score.")
        wing_weight = c3.number_input(
            f"Wing weight, WW ({U['weight']})", min_value=0.0,
            value=float(round(to_display(si.wing_weight_lb, "weight", system), 3)),
            help="Wing weight reacted at the wing for the critical-fuselage search "
                 "(load on wing = LZW − Nz·WW). 0 → default 0.09·MTOW.")
        if st.form_submit_button("Apply", type="primary"):
            si.full_down_aileron_deg = float(aileron)
            si.basic_airfoil_cm = float(cm)
            si.wing_weight_lb = to_imperial_scalar(float(wing_weight), "weight", system)
            # M4-22: persist *only this form's* slice, and onto the session
            # project -- writing the page's probe copy back committed the
            # un-applied "Apply geometry & altitudes" edits it carries
            # (fl_effective), breaking the M2-3 persist-only-on-Apply
            # contract for that other form. ``project`` (the probe) is
            # updated too so the rest of this render sees the new input.
            session_project.select_input = si
            st.session_state["project"] = session_project
            project.select_input = si
            st.success("SELECT search inputs applied.")


def _tab_select() -> None:
    st.caption(
        "SELECT searches the balanced V-n matrix for the governing wing, horizontal-"
        "tail, vertical-tail and fuselage loads (FAR 23.301/23.331/23.333/23.421/"
        "23.423/23.425/23.427/23.441/23.443). Load columns are **ULTIMATE** (limit × SF), "
        "marked `-ULT`; the `SF` column states the factor. Dimensionless/speed columns "
        "(n, CL, V) are unscaled and unmarked."
    )
    if project.is_concept:
        st.warning("Concept category (C): critical loads are an **unverified "
                   "extrapolation** above the FAR 23 calibration band.")
    if project.tail_loads is None:
        st.info("Add the **Tail Loads** inputs to the project to include the rational "
                "horizontal-tail loads; the wing and fuselage conditions are shown regardless.")

    _select_inputs_form()

    try:
        critical = build_critical(project)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not select critical loads: {exc}")
        return

    # Carry forward any previously-persisted selection so re-visiting doesn't reset
    # a curated subset back to "everything".
    prior_selected = (
        set(project.envelope.critical.selected_case_ids)
        if project.envelope is not None and project.envelope.critical is not None
        and project.envelope.critical.selected_case_ids
        else None
    )

    st.info(
        "Uncheck a condition to drop it from the **Results Review** page's governing-"
        "loads summary — everything is included by default. This never affects the "
        "structural calc (WINGINER/NETLOADS, fuselage/tail/control-surface loads, "
        "sbeam export), only that summary."
    )

    checked_ids: list = []
    all_ids: list = []
    for key, title, sub in _COMPONENTS:
        conds = [c for c in critical.conditions if c.component == key]
        if not conds:
            continue
        st.subheader(f"{title} — {len(conds)} condition(s)")
        st.caption(sub)
        for c in conds:
            cid = c.case_ref.case_id if c.case_ref else None
            if cid:
                all_ids.append(cid)
                default_checked = cid in prior_selected if prior_selected is not None else True
                checked = st.checkbox(
                    # One shared formatter for every case label in the app
                    # (design note 17): id, deck LOAD/SUBCASE, condition, FAR.
                    case_label(c.case_ref, condition=c.label),
                    value=default_checked, key=widget_key(f"select_{cid}"),
                )
                if checked:
                    checked_ids.append(cid)
        rows = governing_loads_table(conds, system)
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Ground conditions (decision G-9). SELECT does not name them -- LANDLOAD
    # mints its own ``LG-`` ids -- so without this section the filter would miss
    # the family by default and silently enrol it in the ``export-case-filter``
    # standing limitation. Up to 24 assembled ground cases plus twins is exactly
    # the family an engineer wants to scope, so the filter is extended to reach
    # them rather than the limitation widened to excuse not reaching them.
    #
    # This is the **engineer's opt-out filter** and not SELECT's physics pick:
    # ground cases are still a separate governing family and are never compared
    # against flight cases for a maximum (G-9), which is stated as a standing
    # limitation in the methods block.
    try:
        _gear = build_landing(project)[1]
    except (MissingInputError, ValueError, ZeroDivisionError, KeyError):
        _gear = []
    if _gear:
        st.subheader(f"Landing gear (ground) — {len(_gear)} condition(s)")
        st.caption(
            "FAR 23.479–23.499, from LANDLOAD. A **separate governing family**: "
            "these are never compared against the flight conditions above for a "
            "maximum, because the two load different structure by different "
            "paths and the point of a governing table is naming *which* case "
            "governs. Unchecking one drops it from the summary and the exports, "
            "exactly as above."
        )
        for c in _gear:
            cid = c.case_ref.case_id if c.case_ref else None
            if not cid:
                continue
            all_ids.append(cid)
            default_checked = cid in prior_selected if prior_selected is not None else True
            if st.checkbox(case_label(c.case_ref, condition=c.description),
                           value=default_checked, key=widget_key(f"select_{cid}")):
                checked_ids.append(cid)

    # Empty list means "no filter" (every condition kept) -- only persist a real
    # subset when the engineer has actually deselected something.
    new_ids = [] if checked_ids == all_ids else checked_ids

    # Persist ONLY the selection, ONLY when it changed (M2-3): reassigning the whole
    # recomputed `critical` would dirty the project on every render. Write the id
    # list onto the *stored* critical (shared with the saved project via the probe),
    # so a no-op render leaves the project byte-for-byte unchanged and a real
    # deselection persists to Fuselage Loads / Results Review / exports.
    stored = project.envelope.critical if project.envelope is not None else None
    if stored is not None and new_ids != stored.selected_case_ids:
        stored.selected_case_ids = new_ids


# --------------------------------------------------------------------------- #
# Tab 3 -- Trim & Stability (Step G5)
# --------------------------------------------------------------------------- #
def _neutral_point() -> "tuple[float, float, float] | None":
    """(neutral-point %MAC, XLE(MAC) station, MAC) from the Configuration module,
    or ``None`` when the layout geometry it needs isn't in the project (e.g. the
    Appendix A/B fixtures carry no parametric layout)."""
    try:
        conds = configuration_run(project).conditions
    except (ValueError, ZeroDivisionError, KeyError):
        return None
    vals = {lv.key: lv.value for c in conds for lv in c.values}
    np_pct = vals.get("neutral_point_pct_mac")
    xlemac = vals.get("xle_mac_station_of_mac_le")
    mac_in = vals.get("mac")
    if np_pct is None or xlemac is None or not mac_in:
        return None
    return np_pct, xlemac, mac_in


def _tab_trim() -> None:
    st.caption(
        "Balancing horizontal-tail load at 1-g trim (FLTLOADS **BAL A/C/D**) swept "
        "across the CG range, and the tail-volume static margin. Tail loads on this "
        "tab are **LIMIT** — the oracle-traceable balance values an engineer checks "
        "against the manual. The **ULTIMATE** tail loads used for sizing are on the "
        "**Critical Loads** tab, the Results Review page and the exports. Values are "
        "Imperial (in, lb), matching the balanced-conditions table."
    )

    ref_names = [c.name for c in cg_cases]
    ref_name = st.selectbox(
        "Reference loading (sets the swept weight & waterline)", ref_names,
        help="The sweep holds this case's weight and waterline (zcg) fixed and varies "
             "only the CG station. Cases at this same weight land exactly on the curve.")
    ref = next(c for c in cg_cases if c.name == ref_name)

    xcgs = [c.xcg for c in cg_cases]
    lo_default, hi_default = min(xcgs), max(xcgs)
    if hi_default - lo_default < 1e-6:  # a single distinct station -> widen by +-5% MAC
        pad = 0.05 * (mac or 1.0) * IN_PER_FT
        lo_default, hi_default = lo_default - pad, hi_default + pad

    _, _, c3 = st.columns(3)
    # M4-11: these were hard-coded to inches and took raw Imperial even in SI.
    # Through ``unit_number_input`` they render in the active system and come
    # back Imperial, which is what ``trim_sweep`` expects for a station.
    x_lo = unit_number_input("CG station min", round(lo_default, 2), kind="length",
                             key="trim_x_lo", format="%.2f")
    x_hi = unit_number_input("CG station max", round(hi_default, 2), kind="length",
                             key="trim_x_hi", format="%.2f")
    n_stations = int(c3.slider("Stations", min_value=5, max_value=41, value=15, step=2))
    if x_hi <= x_lo:
        st.warning("CG station max must exceed min.")
        return

    step = (x_hi - x_lo) / (n_stations - 1)
    stations = [x_lo + i * step for i in range(n_stations)]
    try:
        curves = trim_sweep(project, weight_lb=ref.weight_lb, zcg=ref.zcg, xcg_stations=stations)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not sweep the trim loads: {exc}")
        return

    fig = go.Figure()
    fig.add_hline(y=0.0, line={"color": "rgba(120,120,120,0.6)", "width": 1})
    for cur in curves:
        fig.add_trace(go.Scatter(x=cur.xcg_in, y=cur.lt_lb, mode="lines", name=cur.condition))
    # Overlay the real CG cases that share the reference weight -- they land on the
    # curve (the trim sweep reuses the same balance), so this doubles as a check.
    same_w = [c for c in cg_cases if abs(c.weight_lb - ref.weight_lb) < 1e-6]
    if same_w:
        env_bal = {(p.cg, p.condition): p.lt for p in env.vn if p.condition in ("BAL A", "BAL C", "BAL D")}
        for cond in ("BAL A", "BAL C", "BAL D"):
            xs = [c.xcg for c in same_w if (c.name, cond) in env_bal]
            ys = [env_bal[(c.name, cond)] for c in same_w if (c.name, cond) in env_bal]
            if xs:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="markers", name=f"{cond} CG cases",
                    marker={"symbol": "circle-open", "size": 11}, showlegend=False))
    fig.update_layout(
        title=f"Balancing tail load vs CG — {ref.weight_lb:.0f} lb, zcg {ref.zcg:.1f} in",
        xaxis_title="CG station Xcg (in)", yaxis_title="Balancing tail load LT (lb, LIMIT)",
        legend={"orientation": "h"}, height=430)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Positive LT is up (tail lift). Open markers are the project's CG cases at this "
        "weight — they lie on the swept curve because the sweep reuses the same FLTLOADS "
        "balance (subroutine 3900). A forward CG needs more tail **download** (LT more "
        "negative) to trim; moving the CG aft raises LT toward (and past) zero.")

    st.dataframe(pd.DataFrame({
        "Xcg (in)": [round(x, 2) for x in stations],
        **{f"{cur.condition} LT (lb)": [round(v) for v in cur.lt_lb] for cur in curves},
    }), hide_index=True, use_container_width=True)

    # ------------------------------------------------------------------ #
    # Static-margin sweep (tail-volume neutral point, Configuration module)
    # ------------------------------------------------------------------ #
    st.subheader("Static margin")
    npt = _neutral_point()
    if npt is None:
        gate(
            "The static-margin sweep needs the tail-volume **neutral point** from the "
            "**Geometry** page (a parametric layout + horizontal-tail area/arm). This "
            "project carries no such layout (e.g. an Appendix A/B fixture), so only the "
            "trim plot above is shown.",
            "configuration_layout", kind="info")
        return
    np_pct, xlemac, mac_in = npt
    cg_pct = [(x - xlemac) / mac_in * 100.0 for x in stations]
    sm_pct = [np_pct - p for p in cg_pct]

    figs = go.Figure()
    figs.add_hline(y=0.0, line={"color": "rgba(200,80,80,0.7)", "width": 1, "dash": "dash"},
                   annotation_text="neutral (NP)", annotation_position="top left")
    figs.add_trace(go.Scatter(x=[round(p, 2) for p in cg_pct], y=sm_pct, mode="lines",
                              name="static margin"))
    env_w = project.weight.envelope if project.weight is not None else None
    if env_w is not None:
        for label, pct in (("fwd limit", env_w.fwd_gross_pct_mac), ("aft limit", env_w.aft_gross_pct_mac)):
            if pct:
                figs.add_vline(x=pct, line={"color": "rgba(120,120,120,0.6)", "width": 1, "dash": "dot"},
                               annotation_text=label, annotation_position="top")
    figs.update_layout(
        title=f"Static margin vs CG — neutral point {np_pct:.1f} %MAC",
        xaxis_title="CG (%MAC)", yaxis_title="Static margin (%MAC)",
        legend={"orientation": "h"}, height=360)
    st.plotly_chart(figs, use_container_width=True)
    st.caption(
        f"Static margin = NP − CG (both %MAC); NP = {np_pct:.1f} %MAC from the tail-volume "
        "estimate (Geometry page, Ref 1 Ch 8: h_acw = 0.25, a_t/a_w = 1.0, "
        "1 − dε/dα = 0.6). Positive is statically stable; the margin shrinks as the CG "
        "moves aft toward the neutral point.")


_tab_a, _tab_b, _tab_c = st.tabs(["V-n diagram", "Critical Loads (SELECT)", "Trim & Stability"])
with _tab_a:
    _tab_vn()
with _tab_b:
    _tab_select()
with _tab_c:
    _tab_trim()
