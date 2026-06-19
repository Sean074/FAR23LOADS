"""Streamlit page for FAR 23 weight, CG and inertia (port of WTONECG.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Edits the itemized weight data base and reports the loading's total weight, CG
and moments of inertia (slug-ft^2 and lb-in^2). Imperial units throughout.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import (
    MassItem,
    MassItemKind,
    Project,
    UnitSystem,
    WeightInput,
    convert_results,
)
from farloads import io as farloads_io
from farloads.modules.weight_onecg import weights_and_inertia
from farloads.report import module_text_report

st.set_page_config(page_title="FAR 23 Weight, CG & Inertia", layout="wide")

st.title("Weight, CG & Inertia — FAR 23")
st.caption(
    "Python/Streamlit port of WTONECG.BAS (Hal C. McMaster). Total weight, centre "
    "of gravity and moments of inertia for one loading."
)

with st.sidebar:
    st.header("Output units")
    out_label = st.radio("Reported results in", ["Imperial", "SI"], index=0,
                         help="The weight data base below is entered in Imperial units "
                              "(lb, in, lb-in²); this toggle converts the reported results.")
    system = UnitSystem.SI if out_label == "SI" else UnitSystem.IMPERIAL

_COLUMNS = ["name", "weight_lb", "x", "y", "z", "ixx", "iyy", "izz", "kind"]
_KINDS = [k.value for k in MassItemKind]

project: Project = st.session_state.get("project", Project(name=""))
items = project.weight.items if project.weight and project.weight.items else []

if items:
    default_df = pd.DataFrame([
        {"name": it.name, "weight_lb": it.weight_lb, "x": it.x, "y": it.y, "z": it.z,
         "ixx": it.ixx, "iyy": it.iyy, "izz": it.izz, "kind": it.kind.value}
        for it in items
    ])
else:
    default_df = pd.DataFrame([
        {"name": "Item 1", "weight_lb": 0.0, "x": 0.0, "y": 0.0, "z": 0.0,
         "ixx": 0.0, "iyy": 0.0, "izz": 0.0, "kind": "empty"}
    ])

st.subheader("Weight data base")
st.caption("Each row is a component: weight (lb) at station x/y/z (in), with its own inertia (lb-in²).")
edited = st.data_editor(
    default_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={"kind": st.column_config.SelectboxColumn("kind", options=_KINDS)},
)

mass_items = []
for _, row in edited.iterrows():
    try:
        kind = MassItemKind(str(row.get("kind", "empty")))
    except ValueError:
        kind = MassItemKind.EMPTY
    mass_items.append(MassItem(
        name=str(row.get("name", "")),
        weight_lb=float(row.get("weight_lb", 0) or 0),
        x=float(row.get("x", 0) or 0),
        y=float(row.get("y", 0) or 0),
        z=float(row.get("z", 0) or 0),
        ixx=float(row.get("ixx", 0) or 0),
        iyy=float(row.get("iyy", 0) or 0),
        izz=float(row.get("izz", 0) or 0),
        kind=kind,
    ))

# Persist into the shared project (keep any existing estimation inputs).
estimation = project.weight.estimation if project.weight else None
project.weight = WeightInput(estimation=estimation, items=mass_items)
st.session_state["project"] = project

try:
    result = weights_and_inertia(mass_items)
except ValueError as exc:
    st.warning(f"Add at least one non-zero weight item: {exc}")
    st.stop()

result = convert_results([result], system)[0]

st.subheader(f"FAR {result.far_reference} — {result.title}")
rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in result.values]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
if result.note:
    st.caption(result.note)

st.download_button(
    "Download weight/CG/inertia (CSV)",
    farloads_io.load_cases_csv([result]),
    file_name="weight_cg_inertia.csv",
    mime="text/csv",
)
st.download_button(
    "Download weight/CG/inertia (text)",
    module_text_report("Weight, CG and inertia", [result]),
    file_name="weight_cg_inertia.txt",
    mime="text/plain",
)
