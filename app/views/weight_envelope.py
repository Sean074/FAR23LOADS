"""Streamlit page for the FAR 23 weight/CG envelope (port of WTENV.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

WTENV shares the weight data base edited on the Weight & CG / Inertia page and the
wing geometry from the Wing Geometry page (it needs the wing's XLEMAC/MAC). Set the
structural CG limits below as percentages of MAC plus the gross and reduced
weights; the page reports the structural-limit stations, the minimum/maximum
loadings, the forward loading envelope and the ballast to reach each limit.
Inputs are Imperial; results follow the sidebar's Imperial/SI toggle (``Home.py``).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import Project, UnitSystem, WeightEnvelopeInput, WeightInput, convert_results
from farloads import io as farloads_io
from farloads.modules.weight_envelope import envelope as compute_envelope, loading_envelope_points
from farloads.report import module_text_report


st.title("Weight / CG Envelope — FAR 23")
st.caption(
    "Python/Streamlit port of WTENV.BAS (Hal C. McMaster). Structural CG limits, "
    "minimum/maximum loadings, the discretionary-loading envelope and ballast."
)

project: Project = st.session_state.get("project", Project(name=""))
if project.weight is None or not project.weight.items:
    st.warning("No weight data base found. Add component weights on the Weight & CG / Inertia page first.")
    st.stop()
if project.geometry is None or project.geometry.by_name("wing") is None:
    st.warning("No wing geometry found. Define the wing on the Wing Geometry page first "
               "(WTENV needs the wing XLEMAC/MAC).")
    st.stop()

existing = project.weight.envelope
# Design weight: read-through from the Weight DB (Step D4.4), the same source
# Structural Speeds reads, so it is not entered a third time. This page already
# requires a weight data base (the st.stop() above), so the total is always
# available; an override checkbox covers a different structural gross weight.
mtow_upstream = project.weight.direct_totals()[0]

system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)

with st.sidebar:
    st.header("Structural limits")
    override_weight = st.checkbox(
        "Override gross weight", value=False,
        help="Uncheck to use the Weight DB total (Weight, CG & Inertia page).",
    )
    if override_weight:
        gross = st.number_input("Gross weight (lb)", min_value=1.0,
                                value=float(existing.gross_weight) if existing and existing.gross_weight
                                else mtow_upstream)
    else:
        gross = mtow_upstream
        st.caption(f"Gross weight from the Weight DB: **{mtow_upstream:,.0f} lb**.")
    aft = st.number_input("Aft gross CG (% MAC)", min_value=0.0, max_value=100.0,
                          value=float(existing.aft_gross_pct_mac) if existing else 31.0)
    fwd = st.number_input("Forward gross CG (% MAC)", min_value=0.0, max_value=100.0,
                          value=float(existing.fwd_gross_pct_mac) if existing else 20.0)
    reg = st.number_input("Forward regardless CG (% MAC)", min_value=0.0, max_value=100.0,
                          value=float(existing.fwd_regardless_pct_mac) if existing else 13.0)
    reg_w = st.number_input("Forward regardless weight (lb)", min_value=1.0,
                            value=float(existing.fwd_regardless_weight) if existing else 2800.0)

inp = WeightEnvelopeInput(
    gross_weight=gross,
    aft_gross_pct_mac=aft,
    fwd_gross_pct_mac=fwd,
    fwd_regardless_pct_mac=reg,
    fwd_regardless_weight=reg_w,
)

project.weight = WeightInput(
    estimation=project.weight.estimation, items=project.weight.items, envelope=inp,
    cg_cases=project.weight.cg_cases,
)
st.session_state["project"] = project

try:
    raw_results = compute_envelope(project, inp)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute the weight envelope: {exc}")
    st.stop()

# --------------------------------------------------------------------------- #
# Loading-envelope chart: forward boundary + structural limits + the shared
# loading scenarios (Step D5, Project.weight.cg_cases) overlaid read-only.
# --------------------------------------------------------------------------- #
limits_by_label = {v.label: v.value for v in raw_results[1].values}
fwd_seq = loading_envelope_points(project)
fig = go.Figure()
if fwd_seq:
    fig.add_trace(go.Scatter(
        x=[x for _w, x in fwd_seq], y=[w for w, _x in fwd_seq],
        mode="lines+markers", name="Forward loading envelope",
    ))
for label, key in [("Aft gross", "Aft gross station"), ("Forward gross", "Forward gross station"),
                   ("Forward regardless", "Forward regardless station")]:
    if key in limits_by_label:
        fig.add_vline(x=limits_by_label[key], line_dash="dash",
                      annotation_text=label, annotation_position="top")
if project.weight.cg_cases:
    fig.add_trace(go.Scatter(
        x=[c.xcg for c in project.weight.cg_cases], y=[c.weight_lb for c in project.weight.cg_cases],
        mode="markers+text", name="Loading scenarios",
        text=[c.name for c in project.weight.cg_cases], textposition="top center",
        marker=dict(size=10, symbol="diamond"),
    ))
fig.update_layout(title="Weight / CG envelope", xaxis_title="Fuselage station (in)",
                  yaxis_title="Weight (lb)", legend=dict(orientation="h"), height=440)
st.plotly_chart(fig, use_container_width=True)
if not project.weight.cg_cases:
    st.caption(
        "No loading scenarios yet — define them on the **Weight/CG Grid & Payload "
        "Cases** page to overlay them here."
    )

results = convert_results(raw_results, system)

for r in results:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        if r.note:
            st.caption(r.note)

st.download_button(
    "Download weight envelope (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="weight_envelope.csv",
    mime="text/csv",
)
st.download_button(
    "Download weight envelope (text)",
    module_text_report("Weight envelope", results),
    file_name="weight_envelope.txt",
    mime="text/plain",
)
