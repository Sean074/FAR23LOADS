"""Streamlit page for the flight envelope + balancing tail loads (FLTLOADS.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Builds the FAR 23.333 maneuver + gust V-n diagram and the balancing horizontal
tail load at every corner (Reference 1 Ch 8). The design speeds and limit load
factors come from the Structural Speeds page (STRSPEED); the airplane-less-tail
aero coefficients come from the **Aero Coefficients** page (Step D4.2); the
balance geometry and weight-CG cases are entered here (the rest of the FLTLOADS
input set).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import (
    FlightLoadsInput,
    Project,
    UnitSystem,
    build_vn_diagram,
    convert_results,
    labels_for,
    resolve_gust_inputs,
    to_display,
    to_imperial_scalar,
)
from farloads.constants import IN2_PER_FT2
from farloads.modules.flight_envelope import build_envelope, run as flt_run
from farloads.modules.structural_speeds import design_speed_values
from farloads.modules.wing_geometry import surface_properties
from farloads.report import module_text_report


st.title("Flight Envelope (V-n) & Balancing Tail Loads")
st.caption(
    "Python/Streamlit port of FLTLOADS.BAS (Hal C. McMaster). Balances the airplane "
    "at every corner of the FAR 23.333 maneuver + gust envelope and reports the "
    "balancing horizontal-tail load — the candidate conditions SELECT then prunes."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"length","area_sqft",...} -> unit string

if project.speeds is None:
    st.warning(
        "No structural speeds found. Set design speeds on the **Structural Speeds** "
        "page first — FLTLOADS reads VA/VC/VD/VF, MC/MD and the limit load factor from it."
    )
    st.stop()

aero = project.aero_coeffs
if aero is None or (aero.cruise is None and aero.flaps_down is None):
    st.warning(
        "No aero coefficients found. Enter the cruise (and optional flaps-down) "
        "coefficient set on the **Aero Coefficients** page first — FLTLOADS reads "
        "the airplane-less-tail CL/CD/CM polynomials from it."
    )
    st.stop()

fl = project.flight_loads or FlightLoadsInput()


def _geometry_defaults(project: Project) -> dict:
    """MAC/wing-area/25%-MAC-station fallback defaults (Appendix A example
    figures), overridden by the project's own Wing Geometry / Configuration &
    Layout data when present -- so a project that already has a "wing" surface
    doesn't get asked to re-enter numbers WINGGEOM/Configuration already give
    (same bug class fixed on Configuration & Layout: unused upstream geometry).
    """
    defaults = {"mac": 69.246, "wing_area_sqft": 184.125, "xw": 80.953, "zw": 87.725}
    wing_surf = project.geometry.by_name("wing") if project.geometry else None
    if wing_surf is not None:
        try:
            values = {v.label: v.value for v in surface_properties(wing_surf).values}
            defaults["mac"] = values["MAC"]
            defaults["wing_area_sqft"] = values["Total area"] / IN2_PER_FT2
            defaults["xw"] = values["XLE(MAC) station of MAC LE"] + 0.25 * values["MAC"]
        except (ValueError, ZeroDivisionError):
            pass
    if project.configuration is not None and project.configuration.root_waterline_z:
        defaults["zw"] = project.configuration.root_waterline_z
    return defaults


_geo_defaults = _geometry_defaults(project)


def _num(label: str, value: float, key: str, kind: str, fmt: str = "%.3f", min_value: float = None) -> float:
    display_value = float(round(to_display(value, kind, system), 4))
    kwargs = {} if min_value is None else {"min_value": min_value}
    return float(st.number_input(f"{label} ({U[kind]})", value=display_value, format=fmt,
                                 key=f"{key}_{system.value}", **kwargs))


with st.sidebar:
    st.header(f"Geometry (FLTLOADS) ({U['length']} / {U['area_sqft']})")
    st.caption(
        f"Input units: **{'Imperial' if system == UnitSystem.IMPERIAL else 'SI'}**. "
        "Defaults come from the Wing Geometry / Configuration & Layout pages when "
        "available, else the Appendix A worked example."
    )
    mac = _num("Wing MAC", fl.mac or _geo_defaults["mac"], "mac", "length", min_value=0.0)
    s = _num("Wing area S", fl.wing_area_sqft or _geo_defaults["wing_area_sqft"], "s", "area_sqft", min_value=0.0)
    xw = _num("X at 25% wing MAC", fl.xw or _geo_defaults["xw"], "xw", "length")
    zw = _num("Z (waterline) at 25% MAC", fl.zw or _geo_defaults["zw"], "zw", "length")
    xtc = _num("Tail CP X, flaps up XTC", fl.xtc or 253.364, "xtc", "length")
    xtf = _num("Tail CP X, flaps down XTF", fl.xtf or 261.027, "xtf", "length")
    mn = st.number_input("Reference Mach (coeffs obtained at)", min_value=0.01,
                         value=float(fl.mn) or 0.1, format="%.3f")

st.caption(
    f"Aero coefficients (from the **Aero Coefficients** page): cruise '{aero.cruise.name}'"
    + (f", flaps-down '{aero.flaps_down.name}'" if aero.flaps_down else "") + "."
)

st.subheader("Altitudes (V-n balanced at each)")
alt_default = pd.DataFrame({"altitude_ft": fl.altitudes_ft or [0.0]})
alt_df = st.data_editor(alt_default, num_rows="dynamic", hide_index=True,
                        use_container_width=True, key="altitudes_editor")
altitudes_ft = sorted({float(v) for v in alt_df["altitude_ft"] if pd.notna(v)}) or [0.0]

st.subheader("Weight / CG cases")
cg_cases = project.weight.cg_cases if project.weight else []
if not cg_cases:
    st.warning(
        "No loading scenarios found. Define them on the **Weight/CG Grid & Payload "
        "Cases** page first — FLTLOADS balances over them."
    )
    st.stop()
st.caption("Read from the **Weight/CG Grid & Payload Cases** page (not edited here).")
st.dataframe(pd.DataFrame([
    {"name": c.name, f"weight ({U['weight']})": round(to_display(c.weight_lb, "weight", system), 2),
     f"xcg ({U['length']})": round(to_display(c.xcg, "length", system), 2),
     f"zcg ({U['length']})": round(to_display(c.zcg, "length", system), 2)}
    for c in cg_cases
]), hide_index=True, use_container_width=True)

# Merge (never wholesale-replace) so fields this page doesn't show survive the
# persist path. Aero coefficients (Step D4.2) and CG cases (Step D5) are owned
# by other pages -- this page only reads them.
project.flight_loads = fl.merged(
    mac=to_imperial_scalar(mac, "length", system),
    wing_area_sqft=to_imperial_scalar(s, "area_sqft", system),
    xw=to_imperial_scalar(xw, "length", system),
    zw=to_imperial_scalar(zw, "length", system),
    xtc=to_imperial_scalar(xtc, "length", system),
    xtf=to_imperial_scalar(xtf, "length", system),
    mn=mn, altitudes_ft=altitudes_ft, cg_cases=cg_cases,
)
st.session_state["project"] = project

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

# V-n diagram: the continuous LIMIT design envelope (backdrop) + the rigorous
# balanced corner points (markers) on top -- one maneuver/gust trace per altitude
# when overlaid (Step D5, multi-altitude V-n).
fig = go.Figure()

# LIMIT design-envelope backdrop: the continuous textbook V-n outline rebuilt
# from the Structural Speeds inputs (project.speeds, guaranteed present here) and
# drawn behind the rigorous balanced points so the envelope visibly bounds them.
# Consolidated onto this page -- it was a duplicate diagram on Structural Speeds.
# All quantities are LIMIT; the gust lines use the textbook Pratt approximation.
envelope = None
gust = None
try:
    sv = design_speed_values(project, project.speeds)
except (ValueError, ZeroDivisionError):
    sv = None
if sv is not None:
    slope = aero.cruise.lift[1] if aero.cruise is not None else None
    mac_ft = (project.flight_loads.mac / 12.0) if project.flight_loads.mac else None
    # Gust lines are altitude-dependent, so draw them only for a single selected
    # altitude; the maneuver envelope (stall boundary + n caps) is altitude-free.
    gust = resolve_gust_inputs(sv.ws, selected_alt, slope, mac_ft) if not overlay_all_alt else None
    envelope = build_vn_diagram(
        vs=project.speeds.stall_clean_kt, va=sv.va, vc=sv.vc, vd=sv.vd,
        n_pos=sv.n, n_neg=sv.nneg, vsf=project.speeds.stall_flap_kt, vf=sv.vf,
        flaps="both", gust=gust,
    )
    for tr in envelope.traces:
        is_gust = tr.name.startswith("Gust")
        fig.add_trace(go.Scatter(
            x=tr.v, y=tr.n, name=f"LIMIT env: {tr.name}", mode="lines",
            legendgroup="limit_env",
            line=dict(color="rgba(140,140,140,0.7)",
                      dash="dot" if is_gust else "solid", width=1.5)))

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
                  yaxis_title="Load factor NZ", legend=dict(orientation="h"), height=440)
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
        "(Aerodynamic Data) and/or MAC (Wing Geometry) was available, so a textbook "
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
    file_name="flight_envelope.txt", mime="text/plain")
