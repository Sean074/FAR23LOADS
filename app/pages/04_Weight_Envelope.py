"""Streamlit page for the FAR 23 weight/CG envelope (port of WTENV.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

WTENV shares the weight data base edited on the Weight & CG / Inertia page and the
wing geometry from the Wing Geometry page (it needs the wing's XLEMAC/MAC). Set the
structural CG limits below as percentages of MAC plus the gross and reduced
weights; the page reports the structural-limit stations, the minimum/maximum
loadings, the forward loading envelope and the ballast to reach each limit.
Inputs are Imperial; an SI output toggle is offered (length -> mm, weight -> kg).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import Project, UnitSystem, WeightEnvelopeInput, WeightInput, convert_results
from farloads import io as farloads_io
from farloads.modules.weight_envelope import envelope as compute_envelope
from farloads.report import module_text_report

st.set_page_config(page_title="FAR 23 Weight Envelope", layout="wide")

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

with st.sidebar:
    st.header("Output units")
    out_label = st.radio("Reported weights/stations in", ["Imperial (lb, in)", "SI (kg, mm)"], index=0,
                         help="Limit inputs below are entered in Imperial units.")
    system = UnitSystem.SI if out_label.startswith("SI") else UnitSystem.IMPERIAL

    st.header("Structural limits")
    gross = st.number_input("Gross weight (lb)", min_value=1.0,
                            value=float(existing.gross_weight) if existing else 3400.0)
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
)
st.session_state["project"] = project

try:
    results = compute_envelope(project, inp)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute the weight envelope: {exc}")
    st.stop()

results = convert_results(results, system)

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
