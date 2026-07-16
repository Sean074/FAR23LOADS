"""Streamlit page for FAR 23 weight estimation (port of WTESTIMA.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Mission inputs are entered in Imperial units (the units of the original program
and the manual's worked examples); results follow the sidebar's Imperial/SI
toggle (``Home.py``).
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
    labels_for,
    to_display,
    to_imperial_scalar,
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

system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"power","weight",...} -> unit string

with st.sidebar:
    st.header("Mission inputs")
    with st.form("weight_estimate_form"):
        airplane = st.text_input("Airplane", value=existing.airplane if existing else "",
                                 help="Airplane name/label; used on the report and the fleet-comparison marker.")
        # No hard max_value caps: this is a concept-aware superset that must accept
        # airplanes beyond the GA band (e.g. the DHC-8 at 4000 hp / ~50 seats), so a
        # loaded value can never exceed the widget's own max. min_value keeps physical
        # sanity. WTESTIMA's own ≤12,500 lb calibration band is surfaced as a warning
        # (concept mode), not enforced on these inputs.
        hp = st.number_input(
            f"Max continuous power ({U['power']}, total)", min_value=0.0,
            value=float(round(to_display(existing.max_continuous_hp, "power", system), 4))
            if existing else 0.0, key=f"max_cont_hp_{system.value}",
            help="Total maximum continuous power for all engines combined (WTESTIMA, Ch 3).")
        engines = st.number_input("Number of engines", min_value=1,
                                  value=existing.engines if existing else 1,
                                  help="Engine count; the power above is the combined total, not per engine.")
        seats = st.number_input("Number of seats", min_value=1,
                                value=existing.seats if existing else 1,
                                help="Total design seats (crew + passengers). Seeds the Structural Speeds "
                                     "occupant count for the FAR 23 seat-limit check.")
        crew = st.number_input(
            "Flight crew", min_value=0,
            value=existing.crew if existing else 1,
            help=(
                "Required flight crew (170 lb each). Carried in the operating empty "
                "weight (OEW = empty + crew×170), not the payload. The FAR 23 "
                "applicability check counts passenger seats = occupants − crew."
            ),
        )
        hours = st.number_input("Endurance at cruise power (hr)", min_value=0.0,
                                value=float(existing.cruise_hours) if existing else 0.0,
                                help="Mission endurance at cruise power; drives the estimated fuel weight "
                                     "(WTESTIMA, Ch 3).")
        baggage = st.number_input(
            f"Baggage weight ({U['weight']})", min_value=0.0,
            value=float(round(to_display(existing.baggage_lb, "weight", system), 4))
            if existing else 0.0, key=f"baggage_{system.value}",
            help="Design baggage payload weight; part of the useful load.")
        pressurized = st.checkbox("Pressurized", value=existing.pressurized if existing else False,
                                  help="Cabin pressurization adds a structural-weight allowance in the estimate.")
        default_idx = _ENGINE_LABELS.index(
            next((k for k, v in _ENGINE_TYPES.items() if existing and v == existing.engine_weight_type),
                 "4-cycle reciprocating")
        )
        engine_label = st.selectbox("Engine type", _ENGINE_LABELS, index=default_idx,
                                    help="Engine class; selects the empty-weight correlation used for the "
                                         "powerplant weight (WTESTIMA, Ch 3).")
        applied = st.form_submit_button("Apply mission inputs", type="primary")

if applied:
    inp = WeightEstimationInput(
        airplane=airplane,
        max_continuous_hp=to_imperial_scalar(hp, "power", system),
        engines=int(engines),
        seats=int(seats),
        crew=int(crew),
        cruise_hours=hours,
        baggage_lb=to_imperial_scalar(baggage, "weight", system),
        pressurized=pressurized,
        engine_weight_type=_ENGINE_TYPES[engine_label],
    )
    # Merge-write: keep any existing itemized weight data base and envelope,
    # only the estimation inputs are this page's own.
    items = project.weight.items if project.weight else []
    envelope = project.weight.envelope if project.weight else None
    project.weight = WeightInput(estimation=inp, items=items, envelope=envelope)
    st.session_state["project"] = project
    existing = inp

if existing is None:
    st.info("No mission inputs yet -- fill in the sidebar and Apply mission inputs.")
    st.stop()
inp = existing

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
    project.weight = WeightInput(estimation=inp, items=seed_items, envelope=project.weight.envelope)
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
        inp_engine_label = next(
            (k for k, v in _ENGINE_TYPES.items() if v == inp.engine_weight_type), inp.engine_weight_type.value
        )
        this_airplane = pd.DataFrame([{
            "aircraft": inp.airplane or "This airplane",
            "mtow_lb": mtow,
            "oew_lb": oew,
            "max_hp": inp.max_continuous_hp,
            "engines": inp.engines,
            "engine_type": inp_engine_label,
            "seats": inp.seats,
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
