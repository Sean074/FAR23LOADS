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

from farloads import Project, UnitSystem, labels_for, si_scalar_label, to_display, to_imperial_scalar, to_si_scalar
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
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"length",...} -> unit string

if project.tail_loads is None and project.vtail_loads is None:
    st.warning("Define the tail inputs on the **Flight Envelope (V-n)** page "
               "(Critical Loads tab) first (horizontal and/or vertical tail).")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

# --------------------------------------------------------------------------- #
# Chordwise geometry (TAILDIST) -- form + Apply, merged onto the existing
# tail_loads/vtail_loads slices (targeted field writes, nothing else touched).
# --------------------------------------------------------------------------- #
st.header("Chordwise distribution")
# Defaults from the Geometry page's tail spans (h_tail_span_in/v_tail_span_in),
# when this page's own field is still unset -- avoids re-asking for a span
# already entered there (read-only through the unified geometry slice, Step G1).
layout = project.geometry.parametric if project.geometry is not None else None
_htail_default = float(project.tail_loads.htail_semispan_in) if project.tail_loads else 0.0
if not _htail_default and layout is not None and layout.h_tail_span_in:
    _htail_default = layout.h_tail_span_in / 2.0
_vtail_default = float(project.vtail_loads.vtail_span_in) if project.vtail_loads else 0.0
if not _vtail_default and layout is not None and layout.v_tail_span_in:
    _vtail_default = layout.v_tail_span_in

with st.form("tail_chordwise_form"):
    st.subheader(f"Chordwise geometry ({U['length']})")
    c1, c2 = st.columns(2)
    htail_semispan_in = None
    vtail_span_in = None
    if project.tail_loads is not None:
        htail_semispan_in = c1.number_input(
            f"Horizontal-tail semi-span ({U['length']})", min_value=0.0,
            value=float(round(to_display(_htail_default, "length", system), 4)), step=1.0,
            key=f"htail_semispan_{system.value}",
            help="BLHTAIL; the average chord is CAVE = S / (2·semispan).")
    if project.vtail_loads is not None:
        vtail_span_in = c2.number_input(
            f"Vertical-tail span ({U['length']})", min_value=0.0,
            value=float(round(to_display(_vtail_default, "length", system), 4)), step=1.0,
            key=f"vtail_span_{system.value}",
            help="BLHTAIL; the average chord is CAVE = SV / span.")
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    if project.tail_loads is not None and htail_semispan_in is not None:
        project.tail_loads.htail_semispan_in = to_imperial_scalar(htail_semispan_in, "length", system)
    if project.vtail_loads is not None and vtail_span_in is not None:
        project.vtail_loads.vtail_span_in = to_imperial_scalar(vtail_span_in, "length", system)
    st.session_state["project"] = project
    st.success("Chordwise geometry applied.")

try:
    results = build_tail_chordwise(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute tail distributions: {exc}")
    results = []

if not results:
    st.info("No critical tail conditions to distribute. Enter the tail span(s) "
            "above and ensure the Critical Loads tab (Flight Envelope (V-n) page) "
            "produced tail loads.")
else:
    # Persist so the sbeam tail export can reuse it.
    if project.loads is not None:
        project.loads.tail_chordwise = results
        st.session_state["project"] = project

    labels = [f"{r.component}: {r.case}" for r in results]
    sel = st.selectbox("Show condition", labels)
    res = results[labels.index(sel)]

    _lbf_lbl = si_scalar_label("lbf", system)
    _psi_lbl = si_scalar_label("psi", system)
    _in_lbl = si_scalar_label("in", system)

    m1, m2, m3 = st.columns(3)
    m1.metric(f"LT25 (cp 25%) {_lbf_lbl}", f"{to_si_scalar(res.lt25, 'lbf', system):,.1f}")
    m2.metric(f"LT50 (cp 50%) {_lbf_lbl}", f"{to_si_scalar(res.lt50, 'lbf', system):,.1f}")
    m3.metric(f"Total tail load {_lbf_lbl}",
              f"{to_si_scalar(res.lt25 + res.lt50, 'lbf', system):,.1f}")

    # Chordwise profile (leading-edge first), as a pressure-vs-chord line.
    # Display-only conversion; ``stations``/``res``/``results`` (persisted to
    # project.loads.tail_chordwise and consumed by the sbeam export) are never
    # touched.
    stations = sorted(res.stations, key=lambda s: s.x)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[to_si_scalar(s.x, "in", system) for s in stations],
        y=[to_si_scalar(s.psi, "psi", system) for s in stations],
        mode="lines+markers", line=dict(width=3), name="net PSI"))
    fig.update_layout(title=f"Chordwise net pressure — {sel}",
                      xaxis_title=f"Chord station from LE ({_in_lbl})",
                      yaxis_title=f"Net pressure PSI ({_psi_lbl})", height=360)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Chordwise distribution table")
    st.caption(
        "Pressures shown are **LIMIT** (oracle-traceable). ULTIMATE deliverables "
        "come from the **Review/Export** pages."
    )
    # CSV export stays Imperial (canonical units); the on-screen table gets a
    # separate, display-only converted copy so the toggle never touches export.
    rows = [
        {"Component": r.component, "Condition": r.case,
         "LT25 (lb, LIMIT)": round(r.lt25, 2), "LT50 (lb, LIMIT)": round(r.lt50, 2),
         **{f"PSI(X{i}) (LIMIT)": round(s.psi, 4) for i, s in enumerate(r.stations, start=1)}}
        for r in results
    ]
    display_rows = [
        {"Component": r.component, "Condition": r.case,
         f"LT25 ({_lbf_lbl}, LIMIT)": round(to_si_scalar(r.lt25, "lbf", system), 2),
         f"LT50 ({_lbf_lbl}, LIMIT)": round(to_si_scalar(r.lt50, "lbf", system), 2),
         **{f"PSI(X{i}) ({_psi_lbl}, LIMIT)": round(to_si_scalar(s.psi, "psi", system), 4)
            for i, s in enumerate(r.stations, start=1)}}
        for r in results
    ]
    st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)

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
        _lbf_lbl = si_scalar_label("lbf", system)
        _in_lbl = si_scalar_label("in", system)
        c1, c2 = st.columns(2)
        c1.metric("Largest UP balancing load LT (LIMIT)",
                  f"{to_si_scalar(up['LT'], 'lbf', system):.1f} {_lbf_lbl}",
                   f"CP {up['CP']:.2f}% MAC")
        c2.metric("Largest DOWN balancing load LT (LIMIT)",
                  f"{to_si_scalar(dn['LT'], 'lbf', system):.1f} {_lbf_lbl}",
                   f"CP {dn['CP']:.2f}% MAC")

        table = pd.DataFrame([{
            "Condition": r["point"].condition,
            "CG": r["point"].cg,
            "Alt (ft)": round(r["point"].altitude_ft),
            "V (kt EAS)": round(r["point"].v_eas_kt, 1),
            f"LT25 (cp 25%, {_lbf_lbl}, LIMIT)": round(to_si_scalar(r["LT25"], "lbf", system), 1),
            f"LT50 (cp 50%, {_lbf_lbl}, LIMIT)": round(to_si_scalar(r["LT50"], "lbf", system), 1),
            "Elevator δ (deg)": round(r["DELTA"], 2),
            f"Elevator load ({_lbf_lbl}, LIMIT)": round(to_si_scalar(r["ELEV"], "lbf", system), 1),
            f"Total LT ({_lbf_lbl}, LIMIT)": round(to_si_scalar(r["LT"], "lbf", system), 1),
            "Rational CP (% MAC)": round(r["CP"], 2),
            f"Rational XT ({_in_lbl})": round(to_si_scalar(r["XT"], "in", system), 2),
            f"Approx XTC ({_in_lbl})": round(to_si_scalar(r["XTC"], "in", system), 2),
            f"Error ({_in_lbl})": round(to_si_scalar(r["DXT"], "in", system), 2),
        } for r in bal_rows])
        st.dataframe(table, hide_index=True, use_container_width=True)
