"""Streamlit page for the net fuselage loads (Ch 15).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the longitudinal fuselage shear and bending for each critical fuselage
condition (SELECT) as the fuselage inertia reacted by the tail air load and the
wing attachment (Reference 1 Ch 15) -- the body analogue of the net wing loads.
The fuselage mass distribution is entered here; the wing/tail stations come from
the Flight Envelope and Tail Loads inputs.
"""

from __future__ import annotations

import csv
import io as _io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import Project, UnitSystem, si_scalar_label, to_si_scalar
from farloads.models import FuselageMassInput, FuselageStation
from farloads.modules.body_loads import body_load_rows, build_body_loads


def _convert_body_rows(rows, system: UnitSystem):
    """Display-only copy of ``body_load_rows`` output converted to ``system``.

    Never mutates the source rows/objects -- CSV/export paths keep using the
    original Imperial ``rows``/``results``.
    """
    return [
        {
            **r,
            "X": round(to_si_scalar(float(r["X"]), "in", system), 3),
            "Fz": round(to_si_scalar(float(r["Fz"]), "lbf", system), 2),
            "Sz": round(to_si_scalar(float(r["Sz"]), "lbf", system), 2),
            "Myy": round(to_si_scalar(float(r["Myy"]), "lb-in", system), 1),
        }
        for r in rows
    ]


st.title("Net Fuselage Loads — shear / bending")
st.caption(
    "Python/Streamlit port of the Reference 1 Ch 15 procedure (no original .BAS): "
    "the fuselage is a beam carrying the inertia of its mass items, reacted by the "
    "tail air load and the wing attachment. Validated by equilibrium closure."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)

if project.flight_loads is None:
    st.warning("Define the flight-loads inputs on the **Flight Envelope** page first.")
    st.stop()

fm = project.fuselage_mass or FuselageMassInput()
with st.form("fuselage_mass_form"):
    st.subheader("Fuselage mass distribution")
    st.caption("Lumped station weights nose→tail (exclude the wing mass outside the "
               "fuselage, per Ch 15).")
    default = pd.DataFrame(
        [[s.x, s.weight_lb] for s in fm.stations] or [[0.0, 0.0]],
        columns=["x", "weight_lb"],
    )
    df = st.data_editor(default, num_rows="dynamic", hide_index=True, use_container_width=True)
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    stations = [
        FuselageStation(x=float(r["x"]), weight_lb=float(r["weight_lb"]))
        for _, r in df.iterrows()
        if pd.notna(r["x"]) and pd.notna(r["weight_lb"])
    ]
    project.fuselage_mass = FuselageMassInput(stations=stations, ref_waterline=fm.ref_waterline)
    st.session_state["project"] = project
    st.success("Fuselage mass distribution applied.")
    fm = project.fuselage_mass

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    results = build_body_loads(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute fuselage loads: {exc}")
    st.stop()

if not results:
    st.info("No critical fuselage conditions to distribute.")
    st.stop()

# Persist so the sbeam body export can reuse it.
if project.loads is not None:
    project.loads.body_net = results
    st.session_state["project"] = project

st.caption(
    "Loads shown are **LIMIT** (oracle-traceable). The deliverable **ULTIMATE** "
    "loads (= limit × safety factor, 14 CFR 23.303) come from the "
    "**Review/Export** pages."
)
sel = st.selectbox("Show condition", [r.case for r in results])
res = next(r for r in results if r.case == sel)

c1, c2 = st.columns(2)
c1.metric(f"Closure ΣFz ({si_scalar_label('lbf', system)}, LIMIT)",
          f"{to_si_scalar(sum(s.fz for s in res.stations), 'lbf', system):,.2f}")
c2.metric("Stations", str(len(res.stations)))

for title, attr, unit_key in [("Shear Sz", "sz", "lbf"), ("Bending Myy", "myy", "lb-in")]:
    unit = f"{si_scalar_label(unit_key, system)}, LIMIT"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[to_si_scalar(s.x, "in", system) for s in res.stations],
        y=[to_si_scalar(getattr(s, attr), unit_key, system) for s in res.stations],
        mode="lines+markers", line=dict(width=3)))
    fig.update_layout(title=f"{title} — {sel}",
                      xaxis_title=f"Fuselage station X ({si_scalar_label('in', system)})",
                      yaxis_title=f"{title} ({unit})", height=320)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Net fuselage load table (LIMIT)")
st.caption(
    f"Columns: X ({si_scalar_label('in', system)}), Fz/Sz ({si_scalar_label('lbf', system)}), "
    f"Myy ({si_scalar_label('lb-in', system)})."
)
st.dataframe(pd.DataFrame(_convert_body_rows(body_load_rows([res]), system)),
             hide_index=True, use_container_width=True)

buf = _io.StringIO()
rows = body_load_rows(results)
writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
writer.writeheader()
writer.writerows(rows)
st.download_button("Download fuselage loads (CSV)", buf.getvalue(),
                   file_name="net_fuselage_loads.csv", mime="text/csv")
