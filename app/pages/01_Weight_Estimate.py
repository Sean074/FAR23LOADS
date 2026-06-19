"""Streamlit page for FAR 23 weight estimation (port of WTESTIMA.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Mass-properties figures are reported in Imperial units (the units of the original
program and the manual's worked examples); SI presentation is deferred.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import (
    EngineWeightType,
    Project,
    UnitSystem,
    WeightEstimationInput,
    WeightInput,
    convert_results,
)
from farloads import io as farloads_io
from farloads.modules.weight_estimate import estimate
from farloads.report import module_text_report

st.set_page_config(page_title="FAR 23 Weight Estimate", layout="wide")

st.title("Weight Estimate — FAR 23")
st.caption(
    "Python/Streamlit port of WTESTIMA.BAS (Hal C. McMaster). Estimates take-off, "
    "empty and component weights from the mission."
)

project: Project = st.session_state.get("project", Project(name=""))
existing = project.weight.estimation if project.weight and project.weight.estimation else None

_ENGINE_TYPES = {
    "4-cycle reciprocating": EngineWeightType.RECIP_4CYCLE,
    "2-cycle reciprocating": EngineWeightType.RECIP_2CYCLE,
    "Turbocharged": EngineWeightType.TURBOCHARGED,
    "Turboprop": EngineWeightType.TURBOPROP,
    "Liquid-cooled": EngineWeightType.LIQUID_COOLED,
}
_ENGINE_LABELS = list(_ENGINE_TYPES)

with st.sidebar:
    st.header("Output units")
    out_label = st.radio("Reported weights in", ["Imperial (lb)", "SI (kg)"], index=0,
                         help="Mission inputs below are entered in Imperial units.")
    system = UnitSystem.SI if out_label.startswith("SI") else UnitSystem.IMPERIAL

    st.header("Mission inputs")
    airplane = st.text_input("Airplane", value=existing.airplane if existing else "")
    hp = st.number_input("Max continuous HP (total)", min_value=1.0, max_value=3000.0,
                         value=float(existing.max_continuous_hp) if existing else 265.0)
    engines = st.number_input("Number of engines", min_value=1, max_value=6,
                              value=existing.engines if existing else 1)
    seats = st.number_input("Number of seats", min_value=1, max_value=12,
                            value=existing.seats if existing else 6)
    hours = st.number_input("Endurance at cruise power (hr)", min_value=0.1, max_value=10.0,
                            value=float(existing.cruise_hours) if existing else 3.0)
    baggage = st.number_input("Baggage weight (lb)", min_value=0.0,
                              value=float(existing.baggage_lb) if existing else 0.0)
    pressurized = st.checkbox("Pressurized", value=existing.pressurized if existing else False)
    default_idx = _ENGINE_LABELS.index(
        next((k for k, v in _ENGINE_TYPES.items() if existing and v == existing.engine_weight_type),
             "4-cycle reciprocating")
    )
    engine_label = st.selectbox("Engine type", _ENGINE_LABELS, index=default_idx)

inp = WeightEstimationInput(
    airplane=airplane,
    max_continuous_hp=hp,
    engines=int(engines),
    seats=int(seats),
    cruise_hours=hours,
    baggage_lb=baggage,
    pressurized=pressurized,
    engine_weight_type=_ENGINE_TYPES[engine_label],
)

# Persist into the shared project (keep any existing itemized weight data base).
items = project.weight.items if project.weight else []
project.weight = WeightInput(estimation=inp, items=items)
st.session_state["project"] = project

try:
    results = estimate(inp)
except ValueError as exc:
    st.error(f"Could not estimate weights: {exc}")
    st.stop()

results = convert_results(results, system)

for r in results:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

st.download_button(
    "Download weight estimate (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="weight_estimate.csv",
    mime="text/csv",
)
st.download_button(
    "Download weight estimate (text)",
    module_text_report("Weight estimate", results),
    file_name="weight_estimate.txt",
    mime="text/plain",
)
