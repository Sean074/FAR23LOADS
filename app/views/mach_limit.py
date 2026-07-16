"""Streamlit page for the FAR 23 Mach-limit lines (port of MACHLIM.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Enter the cruise/dive Mach limits (MC, MD; usually taken from the Structural
Speeds page at the shoulder altitude) and the altitude range. The page tabulates
the Mach-limited equivalent airspeeds (V(MC), V(MNE), V(MD), V(FC)) from the
shoulder altitude up to the max operating altitude, for the flight-limits diagram
— overlaid with the VA/VC/VD/VF design speeds from Structural Speeds (Step D5)
so the whole speed-altitude boundary is visible on one chart. All speeds are
knots equivalent airspeed (KEAS).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import MachLimitInput, Project, StructuralSpeedsInput
from farloads import io as farloads_io
from farloads.modules.mach_limit import mach_limit_lines
from farloads.modules.structural_speeds import design_speed_values
from farloads.report import module_text_report


st.title("Mach Limit Lines — FAR 23")
st.caption(
    "Python/Streamlit port of MACHLIM.BAS (Hal C. McMaster). Mach-limited "
    "equivalent airspeeds vs altitude for the flight-limits diagram."
)

project: Project = st.session_state.get("project", Project(name=""))
existing = project.speeds.mach_limit if project.speeds and project.speeds.mach_limit else None

# Seed MC/MD/shoulder altitude from the Structural Speeds page (STRSPEED
# already computes these Mach numbers at its shoulder altitude) when this
# page's own mach_limit slice hasn't been set yet, instead of re-asking for
# numbers the project already has (same bug class fixed on Configuration &
# Layout: unused upstream data).
seed_mc, seed_md, seed_shoulder = 0.323, 0.403, 12000.0
if existing is not None:
    seed_mc, seed_md, seed_shoulder = existing.mc, existing.md, existing.shoulder_altitude_ft
elif project.speeds is not None and project.speeds.weight_lb > 0:
    try:
        ds = design_speed_values(project, project.speeds)
        seed_mc, seed_md = ds.mc, ds.md
        seed_shoulder = project.speeds.shoulder_altitude_ft or seed_shoulder
    except (ValueError, ZeroDivisionError):
        pass

with st.sidebar:
    st.header("Inputs")
    mc = st.number_input("Cruise Mach MC", min_value=0.0, max_value=1.0, value=float(seed_mc), format="%.4f")
    md = st.number_input("Dive Mach MD", min_value=0.0, max_value=1.0, value=float(seed_md), format="%.4f")
    shoulder = st.number_input("Shoulder altitude (ft)", min_value=0.0,
                               value=float(existing.shoulder_altitude_ft) if existing else seed_shoulder)
    max_alt = st.number_input("Max operating altitude (ft)", min_value=0.0,
                              value=float(existing.max_operating_altitude_ft) if existing else 18000.0)
    incr = st.number_input("Altitude increment (ft)", min_value=1.0,
                           value=float(existing.increment_ft) if existing else 1000.0)

inp = MachLimitInput(
    mc=mc, md=md, shoulder_altitude_ft=shoulder,
    max_operating_altitude_ft=max_alt, increment_ft=incr,
)
# Persist into the speeds slice (creating it if the Speeds page has not run).
speeds = project.speeds or StructuralSpeedsInput()
speeds.mach_limit = inp
project.speeds = speeds
st.session_state["project"] = project

try:
    results = mach_limit_lines(inp)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute the Mach-limit lines: {exc}")
    st.stop()

summary, *lines = results
with st.expander(f"FAR {summary.far_reference} — {summary.title}", expanded=True):
    rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in summary.values]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(summary.note)

# The per-altitude lines as a single table + a speed-altitude chart, with the
# VA/VC/VD/VF design speeds (Structural Speeds) overlaid as reference lines
# (Step D5) so the whole flight-limits boundary reads on one plot.
table = [{v.label: v.value for v in line.values} for line in lines]
df = pd.DataFrame(table)
st.subheader("Mach-limited equivalent airspeeds")
st.dataframe(df, hide_index=True, use_container_width=True)
if not df.empty:
    fig = go.Figure()
    for col in ("V(MC)", "V(MNE)", "V(MD)", "V(FC)"):
        fig.add_trace(go.Scatter(x=df["Altitude"], y=df[col], name=col, mode="lines+markers"))
    ds = None
    if project.speeds is not None and project.speeds.weight_lb > 0:
        try:
            ds = design_speed_values(project, project.speeds)
        except (ValueError, ZeroDivisionError):
            ds = None
    if ds is not None:
        for label, v in [("VA", ds.va), ("VC", ds.vc), ("VD", ds.vd), ("VF", ds.vf)]:
            fig.add_hline(y=v, line_dash="dash", annotation_text=label,
                         annotation_position="right")
    else:
        st.caption(
            "Set the design weight on the **Structural Speeds** page to overlay "
            "VA/VC/VD/VF on this chart."
        )
    fig.update_layout(title="Speed–altitude diagram", xaxis_title="Altitude (ft)",
                      yaxis_title="V (KEAS)", legend=dict(orientation="h"), height=440)
    st.plotly_chart(fig, use_container_width=True)

st.download_button(
    "Download Mach-limit lines (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="mach_limit.csv",
    mime="text/csv",
)
st.download_button(
    "Download Mach-limit lines (text)",
    module_text_report("Mach limit lines", results),
    file_name="mach_limit.txt",
    mime="text/plain",
)
