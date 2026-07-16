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

from farloads import FlightLoadsInput, Project, UnitSystem, convert_results, labels_for, to_display, to_imperial_scalar
from farloads.constants import IN2_PER_FT2
from farloads.modules.flight_envelope import build_envelope, run as flt_run
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

# V-n diagram: maneuver corners (line) + gust + balancing points, one trace per
# altitude when overlaid (Step D5, multi-altitude V-n).
fig = go.Figure()
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
