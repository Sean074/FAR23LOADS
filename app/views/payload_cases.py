"""Streamlit page for the shared weight/CG loading scenarios (Step D5).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Owns ``Project.weight.cg_cases``: named (weight, CG) loading scenarios entered
once here instead of on the Weight/CG Envelope and Flight Envelope pages
separately, so the two views of the same airplane cannot diverge. The Weight/CG
Envelope page overlays these points on its loading-envelope chart (read-only);
the Flight Envelope page reads them read-only and balances the V-n matrix over
them (FLTLOADS' ``cg_cases``).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import (
    CgCase,
    Project,
    UnitSystem,
    WeightInput,
    labels_for,
    to_display,
    to_imperial_scalar,
)

st.title("Weight/CG Grid & Payload Cases")
st.caption(
    "Named weight/CG loading scenarios, defined once and shared by the Weight/CG "
    "Envelope chart and the Flight Envelope (FLTLOADS) balance — so the two can "
    "no longer diverge."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","length",...} -> unit string

if project.weight is None or not project.weight.items:
    st.warning(
        "No weight data base found. Add component weights on the "
        "**Weight, CG & Inertia** page first."
    )
    st.stop()

existing = project.weight.cg_cases

with st.form("payload_cases_form"):
    st.subheader("Loading scenarios")
    st.caption(
        "One row per named CG case (e.g. forward/aft/ramp loadings): total weight "
        "and the resultant fuselage station / waterline of the CG."
    )
    default_rows = pd.DataFrame(
        [[c.name, to_display(c.weight_lb, "weight", system), to_display(c.xcg, "length", system),
          to_display(c.zcg, "length", system)] for c in existing]
        or [["CG1", 0.0, 0.0, 0.0]],
        columns=["name", "weight_lb", "xcg", "zcg"],
    )
    payload_cols = {
        "weight_lb": st.column_config.NumberColumn(f"weight_lb ({U['weight']})"),
        "xcg": st.column_config.NumberColumn(f"xcg ({U['length']})"),
        "zcg": st.column_config.NumberColumn(f"zcg ({U['length']})"),
    }
    rows = st.data_editor(
        default_rows, column_config=payload_cols, num_rows="dynamic", hide_index=True,
        use_container_width=True, key=f"payload_cases_editor_{system.value}",
    )
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    cases = [
        CgCase(name=str(r["name"]), weight_lb=to_imperial_scalar(float(r["weight_lb"]), "weight", system),
               xcg=to_imperial_scalar(float(r["xcg"]), "length", system),
               zcg=to_imperial_scalar(float(r["zcg"]), "length", system))
        for _, r in rows.iterrows()
        if pd.notna(r["weight_lb"]) and pd.notna(r["xcg"]) and str(r["name"]).strip()
    ]
    # This page owns cg_cases exclusively, but the weight slice also carries
    # estimation/items/envelope owned by other pages -- merge, don't replace.
    w = project.weight
    project.weight = WeightInput(
        estimation=w.estimation, items=w.items, envelope=w.envelope, cg_cases=cases,
    )
    st.session_state["project"] = project
    st.success(f"{len(cases)} loading scenario(s) applied.")
    existing = cases

if not existing:
    st.info("No loading scenarios defined yet — add rows above and Apply.")
    st.stop()

st.subheader("Current scenarios")
st.dataframe(
    pd.DataFrame([
        {"Name": c.name, f"Weight ({U['weight']})": to_display(c.weight_lb, "weight", system),
         f"Xcg ({U['length']})": to_display(c.xcg, "length", system),
         f"Zcg ({U['length']})": to_display(c.zcg, "length", system)}
        for c in existing
    ]),
    hide_index=True, use_container_width=True,
)
