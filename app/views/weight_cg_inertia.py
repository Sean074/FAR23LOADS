"""Streamlit page for FAR 23 weight, CG and inertia (port of WTONECG.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Edits the itemized weight data base (entered in Imperial: lb, in, lb-in^2) and
reports the loading's total weight, CG and moments of inertia; results follow
the sidebar's Imperial/SI toggle (``Home.py``).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import (
    MassItem,
    MassItemKind,
    Project,
    UnitSystem,
    WeightInput,
    consistency_warnings,
    convert_results,
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads import io as farloads_io
from farloads.modules.weight_onecg import weights_and_inertia
from farloads.report import module_text_report
from farloads.validation import _wtenv_cg_limits


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
with st.expander("ℹ️ Parameter guide", expanded=False):
    st.markdown(
        "One row per mass item; the totals below are the loading's weight, CG and moments of inertia "
        "(WTONECG, Ch 8):\n\n"
        "- **weight_lb** — the item weight.\n"
        "- **x / y / z** — the item CG station: X fuselage station (aft of the nose datum), Y butt line "
        "(+right of centreline), Z waterline (+up).\n"
        "- **ixx / iyy / izz** — the item's *own* moment of inertia about its CG (lb·in²) — the local term; "
        "the program adds the parallel-axis (transfer) term from x/y/z automatically, so leave these 0 for "
        "a point mass.\n"
        "- **kind** — mass category: *empty* (manufacturer's empty weight), *minimum* (always-present "
        "useful load), *discretionary* (optional payload/fuel). Drives the CG-envelope loadings.\n\n"
        "*Roll Ixx is about the X axis, pitch Iyy about Y, yaw Izz about Z.*"
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
    raw_result = weights_and_inertia(project.weight.items)
except ValueError as exc:
    st.warning(f"Add at least one non-zero weight item: {exc}")
    st.stop()

# Input-consistency check (Step E3): CG vs the WTENV structural envelope.
for _w in consistency_warnings(project):
    if _w.page == "weight_cg_inertia":
        st.warning(_w.message)

result = convert_results([raw_result], system)[0]

st.subheader(f"FAR {result.far_reference} — {result.title}")
rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in result.values]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
if result.note:
    st.caption(result.note)

# --------------------------------------------------------------------------- #
# CG marker + mass-distribution plot (Step E3): a stem of each item's weight at
# its fuselage station, the computed loading CG, and (when defined) the WTENV
# forward/aft structural CG limits -- a visual sanity check on the loading.
# --------------------------------------------------------------------------- #
xbar_in = next((v.value for v in raw_result.values if v.label == "XBAR (fus station)"), None)
if xbar_in is not None:
    st.subheader("CG & mass distribution")
    st.caption(
        f"Each stem is an item's weight ({U['weight']}) at its fuselage station "
        f"x ({U['length']}); the dashed line is the loading CG."
    )
    _kind_color = {"empty": "#1f77b4", "minimum": "#2ca02c", "discretionary": "#ff7f0e"}
    fig = go.Figure()
    for kind in ("empty", "minimum", "discretionary"):
        pts = [it for it in project.weight.items if it.kind.value == kind and it.weight_lb]
        if not pts:
            continue
        xs = [to_display(it.x, "length", system) for it in pts]
        ws_ = [to_display(it.weight_lb, "weight", system) for it in pts]
        fig.add_trace(go.Bar(x=xs, y=ws_, name=kind, width=0.8,
                             marker_color=_kind_color[kind],
                             hovertext=[it.name for it in pts]))
    fig.add_vline(x=to_display(xbar_in, "length", system), line_dash="dash",
                  line_color="#d62728", annotation_text="CG", annotation_position="top")
    limits = _wtenv_cg_limits(project)
    if limits is not None:
        fwd, aft = limits
        for x_in, lbl in ((fwd, "fwd limit"), (aft, "aft limit")):
            fig.add_vline(x=to_display(x_in, "length", system), line_dash="dot",
                          line_color="#7f7f7f", annotation_text=lbl, annotation_position="bottom")
    fig.update_layout(barmode="overlay", height=380, legend=dict(orientation="h"),
                      xaxis_title=f"Fuselage station x ({U['length']})",
                      yaxis_title=f"Item weight ({U['weight']})")
    st.plotly_chart(fig, use_container_width=True)

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
