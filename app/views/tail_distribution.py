"""Streamlit page for the chordwise tail-load distribution (TAILDIST, Ch 10).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the chordwise net pressure profile on the average tail chord for each
critical horizontal/vertical-tail condition SELECT produced -- the additive
(angle-of-attack, 25% chord) plus camber (50% chord) distributions (Reference 1
Ch 10). The chordwise geometry (the tail span that sets the average chord) is
entered here; the LT25/LT50 loads come from the Critical Loads (SELECT) inputs.
"""

from __future__ import annotations

import csv
import io as _io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import Project
from farloads.modules.taildist import build_tail_chordwise


st.title("Chordwise Tail-Load Distribution — TAILDIST")
st.caption(
    "Python/Streamlit port of TAILDIST.BAS (Reference 1 Ch 10): the additive "
    "(angle-of-attack, 25% chord) + camber (50% chord) distributions on the average "
    "tail chord, for each critical tail condition from SELECT. These replace the "
    "arbitrary FAR 23 Appendix B figures (pre-amendment 42)."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.tail_loads is None and project.vtail_loads is None:
    st.warning("Define the tail inputs on the **Critical Loads** page first "
               "(horizontal and/or vertical tail).")
    st.stop()

# Chordwise geometry: the tail span sets the average chord CAVE = area / span.
st.subheader("Chordwise geometry")
c1, c2 = st.columns(2)
if project.tail_loads is not None:
    project.tail_loads.htail_semispan_in = c1.number_input(
        "Horizontal-tail semi-span (in)", min_value=0.0,
        value=float(project.tail_loads.htail_semispan_in), step=1.0,
        help="BLHTAIL; the average chord is CAVE = S / (2·semispan).")
if project.vtail_loads is not None:
    project.vtail_loads.vtail_span_in = c2.number_input(
        "Vertical-tail span (in)", min_value=0.0,
        value=float(project.vtail_loads.vtail_span_in), step=1.0,
        help="BLHTAIL; the average chord is CAVE = SV / span.")
st.session_state["project"] = project

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    results = build_tail_chordwise(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute tail distributions: {exc}")
    st.stop()

if not results:
    st.info("No critical tail conditions to distribute. Enter the tail span(s) "
            "above and ensure the Critical Loads page produced tail loads.")
    st.stop()

# Persist so the sbeam tail export can reuse it.
if project.loads is not None:
    project.loads.tail_chordwise = results
    st.session_state["project"] = project

labels = [f"{r.component}: {r.case}" for r in results]
sel = st.selectbox("Show condition", labels)
res = results[labels.index(sel)]

m1, m2, m3 = st.columns(3)
m1.metric("LT25 (cp 25%) lb", f"{res.lt25:,.1f}")
m2.metric("LT50 (cp 50%) lb", f"{res.lt50:,.1f}")
m3.metric("Total tail load lb", f"{res.lt25 + res.lt50:,.1f}")

# Chordwise profile (leading-edge first), as a pressure-vs-chord line.
stations = sorted(res.stations, key=lambda s: s.x)
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=[s.x for s in stations], y=[s.psi for s in stations],
    mode="lines+markers", line=dict(width=3), name="net PSI"))
fig.update_layout(title=f"Chordwise net pressure — {sel}",
                  xaxis_title="Chord station from LE (in)",
                  yaxis_title="Net pressure PSI (lb/in²)", height=360)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Chordwise distribution table")
rows = [
    {"Component": r.component, "Condition": r.case, "LT25": round(r.lt25, 2),
     "LT50": round(r.lt50, 2),
     **{f"PSI(X{i})": round(s.psi, 4) for i, s in enumerate(r.stations, start=1)}}
    for r in results
]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

buf = _io.StringIO()
writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
writer.writeheader()
writer.writerows(rows)
st.download_button("Download tail distributions (CSV)", buf.getvalue(),
                   file_name="tail_chordwise_loads.csv", mime="text/csv")
