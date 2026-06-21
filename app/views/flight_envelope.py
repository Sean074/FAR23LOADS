"""Streamlit page for the flight envelope + balancing tail loads (FLTLOADS.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Builds the FAR 23.333 maneuver + gust V-n diagram and the balancing horizontal
tail load at every corner (Reference 1 Ch 8). The design speeds and limit load
factors come from the Structural Speeds page (STRSPEED); the airplane-less-tail
aero coefficients, tail-CP / 25%-MAC stations and weight-CG cases are entered
here (the FLTLOADS input set).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import AeroCoeffSet, CgCase, FlightLoadsInput, Project
from farloads.modules.flight_envelope import build_envelope, run as flt_run
from farloads.report import module_text_report


st.title("Flight Envelope (V-n) & Balancing Tail Loads")
st.caption(
    "Python/Streamlit port of FLTLOADS.BAS (Hal C. McMaster). Balances the airplane "
    "at every corner of the FAR 23.333 maneuver + gust envelope and reports the "
    "balancing horizontal-tail load — the candidate conditions SELECT then prunes."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.speeds is None:
    st.warning(
        "No structural speeds found. Set design speeds on the **Structural Speeds** "
        "page first — FLTLOADS reads VA/VC/VD/VF, MC/MD and the limit load factor from it."
    )
    st.stop()

fl = project.flight_loads or FlightLoadsInput()

with st.sidebar:
    st.header("Geometry (FLTLOADS)")
    mac = st.number_input("Wing MAC (in)", min_value=0.0, value=float(fl.mac) or 69.246, format="%.3f")
    s = st.number_input("Wing area S (ft²)", min_value=0.0,
                        value=float(fl.wing_area_sqft) or 184.125, format="%.3f")
    xw = st.number_input("X at 25% wing MAC (in)", value=float(fl.xw) or 80.953, format="%.3f")
    zw = st.number_input("Z (waterline) at 25% MAC (in)", value=float(fl.zw) or 87.725, format="%.3f")
    xtc = st.number_input("Tail CP X, flaps up XTC (in)", value=float(fl.xtc) or 253.364, format="%.3f")
    xtf = st.number_input("Tail CP X, flaps down XTF (in)", value=float(fl.xtf) or 261.027, format="%.3f")
    mn = st.number_input("Reference Mach (coeffs obtained at)", min_value=0.01,
                         value=float(fl.mn) or 0.1, format="%.3f")
    altitude = st.number_input("Altitude (ft)", min_value=0.0,
                               value=float(fl.altitudes_ft[0]) if fl.altitudes_ft else 0.0, step=1000.0)

st.subheader("Airplane-less-tail aerodynamic coefficients (cruise)")
st.caption(
    "CL = C0 + C1·α + C2·α² + C3·α³ + C4·α⁴ (α in deg); CD = D0 + D1·CL + … ; "
    "CM = M0 + M1·α + … — from the Ch 7 aero-coefficients program."
)
cfg = next((c for c in fl.configurations if not c.flaps_down), None)
coeff_default = pd.DataFrame(
    {
        "row": ["lift (CL vs α)", "drag (CD vs CL)", "moment (CM vs α)"],
        "0": [cfg.lift[0] if cfg else 0.320479, cfg.drag[0] if cfg else 0.026917,
              cfg.moment[0] if cfg else -0.017328],
        "1": [cfg.lift[1] if cfg else 0.080358, cfg.drag[1] if cfg else 0.0,
              cfg.moment[1] if cfg else 0.004128],
        "2": [cfg.lift[2] if cfg else 0.0, cfg.drag[2] if cfg else 0.053647, cfg.moment[2] if cfg else 0.0],
        "3": [cfg.lift[3] if cfg else 0.0, cfg.drag[3] if cfg else 0.0, cfg.moment[3] if cfg else 0.0],
        "4": [cfg.lift[4] if cfg else 0.0, cfg.drag[4] if cfg else 0.0, cfg.moment[4] if cfg else 0.0],
    }
)
coeff_df = st.data_editor(coeff_default, hide_index=True, use_container_width=True, disabled=["row"])
c1, c2 = st.columns(2)
stall_cl = c1.number_input("Stall CL", value=float(cfg.stall_cl) if cfg else 1.41, format="%.3f")
neg_stall_cl = c2.number_input("Negative stall CL", value=float(cfg.neg_stall_cl) if cfg else -0.59,
                               format="%.3f")


def _row(label):
    r = coeff_df[coeff_df["row"] == label].iloc[0]
    return tuple(float(r[str(i)]) for i in range(5))


cruise = AeroCoeffSet(
    name="CRUISE", stall_cl=stall_cl, neg_stall_cl=neg_stall_cl,
    lift=_row("lift (CL vs α)"), drag=_row("drag (CD vs CL)"), moment=_row("moment (CM vs α)"),
    flaps_down=False,
)

st.subheader("Weight / CG cases")
cg_default = pd.DataFrame(
    [[c.name, c.weight_lb, c.xcg, c.zcg] for c in fl.cg_cases]
    or [["CG1", 3400.0, 85.1, 93.0]],
    columns=["name", "weight_lb", "xcg (in)", "zcg (in)"],
)
cg_df = st.data_editor(cg_default, num_rows="dynamic", hide_index=True, use_container_width=True)
cg_cases = [
    CgCase(name=str(r["name"]), weight_lb=float(r["weight_lb"]), xcg=float(r["xcg (in)"]),
           zcg=float(r["zcg (in)"]))
    for _, r in cg_df.iterrows()
    if pd.notna(r["weight_lb"]) and pd.notna(r["xcg (in)"])
]

project.flight_loads = FlightLoadsInput(
    mac=mac, wing_area_sqft=s, xw=xw, zw=zw, xtc=xtc, xtf=xtf, mn=mn,
    altitudes_ft=[altitude], configurations=[cruise], cg_cases=cg_cases,
)
st.session_state["project"] = project

if project.is_concept:
    st.warning(
        "Concept category (C): the envelope uses the user-defined load factors and is "
        "an **unverified extrapolation** above the FAR 23 calibration band."
    )

try:
    env = build_envelope(project)
    results = flt_run(project).conditions
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute the flight envelope: {exc}")
    st.stop()

cg_names = [c.name for c in cg_cases]
selected = st.selectbox("Show CG case", cg_names) if cg_names else None
pts = [p for p in env.vn if p.cg == selected]

# V-n diagram: maneuver corners (line) + gust + balancing points.
man = [p for p in pts if p.condition.startswith(("STALL", "MAN"))]
gust = [p for p in pts if p.condition.startswith("GUST")]
fig = go.Figure()
fig.add_trace(go.Scatter(x=[p.v_eas_kt for p in man], y=[p.nz for p in man],
                         name="maneuver", mode="markers+lines"))
fig.add_trace(go.Scatter(x=[p.v_eas_kt for p in gust], y=[p.nz for p in gust],
                         name="gust", mode="markers"))
fig.update_layout(title=f"V-n diagram — {selected}", xaxis_title="V (KEAS)",
                  yaxis_title="Load factor NZ", legend=dict(orientation="h"), height=440)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Balanced flight conditions")
st.dataframe(pd.DataFrame({
    "case": [p.case for p in pts],
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
