"""Streamlit page for Tail Loads (Step D6): TAILDIST + BALLOADS merged.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the chordwise net pressure profile on the average tail chord for each
critical horizontal/vertical-tail condition SELECT produced -- the additive
(angle-of-attack, 25% chord) plus camber (50% chord) distributions (Reference 1
Ch 10) -- and, below it, the BALLOADS cross-check: the rational balancing
horizontal-tail load recomputed against FLTLOADS' approximate tail centre of
pressure (FAR 23.421). TAILDIST and BALLOADS are independently registered calc
modules (see ``farloads.workflow.FOLDED_MODULES``); this page is their shared
nav step.
"""

from __future__ import annotations

import csv
import io as _io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import Project
from farloads.modules.balloads import verify_balancing
from farloads.modules.taildist import build_tail_chordwise

st.title("Tail Loads — TAILDIST + BALLOADS")
st.caption(
    "Python/Streamlit port of TAILDIST.BAS and BALLOADS.BAS (Reference 1 Ch 10, "
    "Hal C. McMaster). Chordwise distribution: the additive (angle-of-attack, 25% "
    "chord) + camber (50% chord) distributions on the average tail chord, for each "
    "critical tail condition from SELECT -- these replace the arbitrary FAR 23 "
    "Appendix B figures (pre-amendment 42). Balance verification: recomputes the "
    "rational balancing horizontal-tail load and cross-checks FLTLOADS' approximate "
    "tail centre of pressure."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.tail_loads is None and project.vtail_loads is None:
    st.warning("Define the tail inputs on the **Critical Loads** page first "
               "(horizontal and/or vertical tail).")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

# --------------------------------------------------------------------------- #
# Chordwise geometry (TAILDIST) -- form + Apply, merged onto the existing
# tail_loads/vtail_loads slices (targeted field writes, nothing else touched).
# --------------------------------------------------------------------------- #
st.header("Chordwise distribution")
with st.form("tail_chordwise_form"):
    st.subheader("Chordwise geometry")
    c1, c2 = st.columns(2)
    htail_semispan_in = None
    vtail_span_in = None
    if project.tail_loads is not None:
        htail_semispan_in = c1.number_input(
            "Horizontal-tail semi-span (in)", min_value=0.0,
            value=float(project.tail_loads.htail_semispan_in), step=1.0,
            help="BLHTAIL; the average chord is CAVE = S / (2·semispan).")
    if project.vtail_loads is not None:
        vtail_span_in = c2.number_input(
            "Vertical-tail span (in)", min_value=0.0,
            value=float(project.vtail_loads.vtail_span_in), step=1.0,
            help="BLHTAIL; the average chord is CAVE = SV / span.")
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    if project.tail_loads is not None and htail_semispan_in is not None:
        project.tail_loads.htail_semispan_in = htail_semispan_in
    if project.vtail_loads is not None and vtail_span_in is not None:
        project.vtail_loads.vtail_span_in = vtail_span_in
    st.session_state["project"] = project
    st.success("Chordwise geometry applied.")

try:
    results = build_tail_chordwise(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute tail distributions: {exc}")
    results = []

if not results:
    st.info("No critical tail conditions to distribute. Enter the tail span(s) "
            "above and ensure the Critical Loads page produced tail loads.")
else:
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
    st.caption(
        "Pressures shown are **LIMIT** (oracle-traceable). ULTIMATE deliverables "
        "come from the **Review/Export** pages."
    )
    rows = [
        {"Component": r.component, "Condition": r.case,
         "LT25 (lb, LIMIT)": round(r.lt25, 2), "LT50 (lb, LIMIT)": round(r.lt50, 2),
         **{f"PSI(X{i}) (LIMIT)": round(s.psi, 4) for i, s in enumerate(r.stations, start=1)}}
        for r in results
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button("Download tail distributions (CSV)", buf.getvalue(),
                       file_name="tail_chordwise_loads.csv", mime="text/csv")

# --------------------------------------------------------------------------- #
# Balanced-tail verification (BALLOADS) -- read-only cross-check, no inputs.
# --------------------------------------------------------------------------- #
st.divider()
st.header("Balanced-tail verification")

if project.flight_loads is None or project.tail_loads is None:
    st.info("Define the **Flight Envelope** and the horizontal-tail inputs above "
            "to run the BALLOADS balancing-load cross-check.")
else:
    try:
        bal_rows = verify_balancing(project)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not verify balancing loads: {exc}")
        bal_rows = []

    if not bal_rows:
        st.info("No flaps-retracted balanced V-n points to verify.")
    else:
        st.caption(
            "Balance-check tool: the loads shown are **LIMIT** (oracle values, "
            "traceable to the manual). The deliverable **ULTIMATE** loads "
            "(= limit × 1.5, 14 CFR 23.303) come from the **Review/Export** pages."
        )
        up = max(bal_rows, key=lambda r: r["LT"])
        dn = min(bal_rows, key=lambda r: r["LT"])
        c1, c2 = st.columns(2)
        c1.metric("Largest UP balancing load LT (LIMIT)", f"{up['LT']:.1f} lb",
                   f"CP {up['CP']:.2f}% MAC")
        c2.metric("Largest DOWN balancing load LT (LIMIT)", f"{dn['LT']:.1f} lb",
                   f"CP {dn['CP']:.2f}% MAC")

        table = pd.DataFrame([{
            "Condition": r["point"].condition,
            "CG": r["point"].cg,
            "Alt (ft)": round(r["point"].altitude_ft),
            "V (kt EAS)": round(r["point"].v_eas_kt, 1),
            "LT25 (cp 25%, LIMIT)": round(r["LT25"], 1),
            "LT50 (cp 50%, LIMIT)": round(r["LT50"], 1),
            "Elevator δ (deg)": round(r["DELTA"], 2),
            "Elevator load (lb, LIMIT)": round(r["ELEV"], 1),
            "Total LT (lb, LIMIT)": round(r["LT"], 1),
            "Rational CP (% MAC)": round(r["CP"], 2),
            "Rational XT (in)": round(r["XT"], 2),
            "Approx XTC (in)": round(r["XTC"], 2),
            "Error (in)": round(r["DXT"], 2),
        } for r in bal_rows])
        st.dataframe(table, hide_index=True, use_container_width=True)
