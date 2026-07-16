"""Streamlit page for FAR 23 weight, CG and inertia (port of WTONECG.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Edits the itemized weight data base (entered in Imperial: lb, in, lb-in^2) and
reports the loading's total weight, CG and moments of inertia; results follow
the sidebar's Imperial/SI toggle (``Home.py``).
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
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads import io as farloads_io
from farloads.modules.weight_onecg import weights_and_inertia
from farloads.report import module_text_report


st.title("Weight, CG & Inertia — FAR 23")
st.caption(
    "Python/Streamlit port of WTONECG.BAS (Hal C. McMaster). Total weight, centre "
    "of gravity and moments of inertia for one loading."
)

system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","length","inertia_lbin2",...} -> unit string

_COLUMNS = ["name", "weight_lb", "x", "y", "z", "ixx", "iyy", "izz", "kind"]
_KINDS = [k.value for k in MassItemKind]

project: Project = st.session_state.get("project", Project(name=""))
items = project.weight.items if project.weight and project.weight.items else []


def _disp(v: float, kind: str) -> float:
    return to_display(v, kind, system)


if items:
    default_df = pd.DataFrame([
        {"name": it.name, "weight_lb": _disp(it.weight_lb, "weight"),
         "x": _disp(it.x, "length"), "y": _disp(it.y, "length"), "z": _disp(it.z, "length"),
         "ixx": _disp(it.ixx, "inertia_lbin2"), "iyy": _disp(it.iyy, "inertia_lbin2"),
         "izz": _disp(it.izz, "inertia_lbin2"), "kind": it.kind.value}
        for it in items
    ])
else:
    default_df = pd.DataFrame([
        {"name": "", "weight_lb": 0.0, "x": 0.0, "y": 0.0, "z": 0.0,
         "ixx": 0.0, "iyy": 0.0, "izz": 0.0, "kind": "empty"}
    ])

st.subheader("Weight data base")
st.caption(
    f"Each row is a component: weight ({U['weight']}) at station x/y/z ({U['length']}), "
    f"with its own inertia ({U['inertia_lbin2']})."
)
_COLUMN_CONFIG = {
    "weight_lb": st.column_config.NumberColumn(f"weight_lb ({U['weight']})"),
    "x": st.column_config.NumberColumn(f"x ({U['length']})"),
    "y": st.column_config.NumberColumn(f"y ({U['length']})"),
    "z": st.column_config.NumberColumn(f"z ({U['length']})"),
    "ixx": st.column_config.NumberColumn(f"ixx ({U['inertia_lbin2']})"),
    "iyy": st.column_config.NumberColumn(f"iyy ({U['inertia_lbin2']})"),
    "izz": st.column_config.NumberColumn(f"izz ({U['inertia_lbin2']})"),
    "kind": st.column_config.SelectboxColumn("kind", options=_KINDS),
}
with st.form("weight_items_form"):
    edited = st.data_editor(
        default_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=_COLUMN_CONFIG,
        key=f"weight_items_{system.value}",
    )
    applied = st.form_submit_button("Apply weight items", type="primary")

if applied:
    def _imp(v: float, kind: str) -> float:
        return to_imperial_scalar(v, kind, system)

    mass_items = []
    for _, row in edited.iterrows():
        try:
            kind = MassItemKind(str(row.get("kind", "empty")))
        except ValueError:
            kind = MassItemKind.EMPTY
        mass_items.append(MassItem(
            name=str(row.get("name", "")),
            weight_lb=_imp(float(row.get("weight_lb", 0) or 0), "weight"),
            x=_imp(float(row.get("x", 0) or 0), "length"),
            y=_imp(float(row.get("y", 0) or 0), "length"),
            z=_imp(float(row.get("z", 0) or 0), "length"),
            ixx=_imp(float(row.get("ixx", 0) or 0), "inertia_lbin2"),
            iyy=_imp(float(row.get("iyy", 0) or 0), "inertia_lbin2"),
            izz=_imp(float(row.get("izz", 0) or 0), "inertia_lbin2"),
            kind=kind,
        ))
    # Merge-write: keep any existing estimation inputs and envelope, only the
    # itemized data base is this page's own.
    estimation = project.weight.estimation if project.weight else None
    envelope = project.weight.envelope if project.weight else None
    project.weight = WeightInput(estimation=estimation, items=mass_items, envelope=envelope)
    st.session_state["project"] = project

if not project.weight or not project.weight.items:
    st.info("No weight items yet -- fill in the data base above and Apply weight items.")
    st.stop()

try:
    result = weights_and_inertia(project.weight.items)
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
