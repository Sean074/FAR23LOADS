"""Streamlit page for FAR 23 weight estimation (port of WTESTIMA.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Mass-properties figures are reported in Imperial units (the units of the original
program and the manual's worked examples); SI presentation is deferred.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
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
from farloads.modules.weight_estimate import estimate, estimate_to_mass_items
from farloads.report import module_text_report


st.title("Weight Estimate — FAR 23")
st.caption(
    "Python/Streamlit port of WTESTIMA.BAS (Hal C. McMaster). Estimates take-off, "
    "empty and component weights from the mission."
)

project: Project = st.session_state.get("project", Project(name=""))
existing = project.weight.estimation if project.weight and project.weight.estimation else None

if project.is_concept:
    st.warning(
        "Concept mode (category C): this statistical estimate is **out of WTESTIMA's "
        "≤12,500 lb calibration band** and is shown as a GA sanity figure only. Use "
        "the itemized weight data base (Weight, CG & Inertia page) as the design weight."
    )

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

display_results = convert_results(results, system)

for r in display_results:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

st.subheader("Seed the weight data base")
st.caption(
    "Copy the estimated component weights into the Weight, CG & Inertia page's data "
    "base as empty-weight items. Stations and per-item inertias start at zero for you "
    "to fill in. This replaces any items already entered there."
)
if st.button("Seed Weight, CG & Inertia from this estimate"):
    seed_items = estimate_to_mass_items(inp)
    project.weight = WeightInput(estimation=inp, items=seed_items)
    st.session_state["project"] = project
    st.success(
        f"Seeded {len(seed_items)} component(s) into the weight data base. "
        "Open the Weight, CG & Inertia page to set their stations."
    )

# --------------------------------------------------------------------------- #
# Comparison with similar aircraft
# --------------------------------------------------------------------------- #
_REFERENCE_CSV = Path(__file__).resolve().parent.parent / "data" / "reference_aircraft.csv"


def _estimate_value(label: str) -> float | None:
    """Pull one labelled figure out of the raw (Imperial) estimate results."""
    for r in results:
        for v in r.values:
            if v.label == label:
                return float(v.value)
    return None


st.subheader("Comparison with similar aircraft")
st.caption(
    "The estimated max take-off (MTOW) and empty (OEW) weights plotted against a reference "
    "fleet. Figures for the reference aircraft are nominal published specs for visual "
    "comparison only — they are not used in any calculation. Axes are logarithmic."
)
try:
    fleet = pd.read_csv(_REFERENCE_CSV, comment="#")
except FileNotFoundError:
    st.info(f"Reference aircraft data file not found at {_REFERENCE_CSV}.")
else:
    fleet["series"] = "Reference fleet"
    mtow = _estimate_value("Max take-off weight")
    oew = _estimate_value("Empty weight")
    if mtow and oew:
        this_airplane = pd.DataFrame([{
            "aircraft": airplane or "This airplane",
            "mtow_lb": mtow,
            "oew_lb": oew,
            "max_hp": hp,
            "engines": int(engines),
            "engine_type": engine_label,
            "seats": int(seats),
            "series": "This airplane",
        }])
        plot_df = pd.concat([fleet, this_airplane], ignore_index=True)
        plot_df["marker_size"] = plot_df["series"].map(
            {"Reference fleet": 8, "This airplane": 18}
        )
        fig = px.scatter(
            plot_df,
            x="oew_lb",
            y="mtow_lb",
            color="series",
            symbol="series",
            size="marker_size",
            size_max=18,
            log_x=True,
            log_y=True,
            hover_name="aircraft",
            hover_data=["max_hp", "engines", "seats", "wingspan_ft", "wing_area_ft2"],
            color_discrete_map={"Reference fleet": "#1f77b4", "This airplane": "#d62728"},
            labels={
                "oew_lb": "Empty weight OEW (lb)",
                "mtow_lb": "Max take-off weight MTOW (lb)",
                "series": "",
            },
        )
        fig.update_layout(legend=dict(orientation="h", y=1.05, x=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run the estimate above to plot this airplane against the reference fleet.")

    with st.expander("Reference fleet data"):
        st.dataframe(fleet.drop(columns=["series"]), hide_index=True, use_container_width=True)

st.download_button(
    "Download weight estimate (CSV)",
    farloads_io.load_cases_csv(display_results),
    file_name="weight_estimate.csv",
    mime="text/csv",
)
st.download_button(
    "Download weight estimate (text)",
    module_text_report("Weight estimate", display_results),
    file_name="weight_estimate.txt",
    mime="text/plain",
)
