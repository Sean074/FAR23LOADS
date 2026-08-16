"""Streamlit page for Tail Loads (Step D6): TAILDIST + BALLOADS merged.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the chordwise net pressure profile on the average tail chord for each
critical horizontal/vertical-tail condition SELECT produced -- the additive
(angle-of-attack, 25% chord) plus camber (50% chord) distributions (Reference 1
Ch 10) -- and, below it, the BALLOADS cross-check: the rational balancing
horizontal-tail load recomputed against FLTLOADS' approximate tail centre of
pressure (FAR 23.421). TAILDIST and BALLOADS are independently registered calc
modules (see ``sloads.workflow.FOLDED_MODULES``); this page is their shared
nav step.
"""

from __future__ import annotations

import csv
import io as _io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from components import active_system, gate

from sloads import Project, UnitSystem, labels_for, si_scalar_label, to_display, to_si_scalar
from sloads.modules.balloads import verify_balancing
from sloads.modules.taildist import build_tail_chordwise

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
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"length",...} -> unit string

if project.tail_loads is None and project.vtail_loads is None:
    gate("Define the tail geometry on the **Geometry** page (Empennage & "
         "control surfaces section) first (horizontal and/or vertical tail).",
         "configuration_layout")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

# --------------------------------------------------------------------------- #
# Chordwise geometry (TAILDIST). Step G6: the tail geometry (incl. the semi-span /
# span the chordwise profile uses) is the single-source empennage on the Geometry
# page; this page reads it read-only and only distributes the loads.
# --------------------------------------------------------------------------- #
st.header("Chordwise distribution")
_ht = project.tail_loads
_vt = project.vtail_loads
st.caption(
    "Tail geometry is read from the single-source **Empennage & control surfaces** "
    "section on the **Geometry** page (Step G6) — edit it there. This page distributes "
    "the SELECT tail loads over the chord (average chord CAVE = S / span)."
)
_gc1, _gc2 = st.columns(2)
if _ht is not None:
    _gc1.metric(f"H-tail semi-span ({U['length']})",
                f"{to_display(_ht.htail_semispan_in, 'length', system):,.1f}")
if _vt is not None:
    _gc2.metric(f"V-tail span ({U['length']})",
                f"{to_display(_vt.vtail_span_in, 'length', system):,.1f}")

try:
    results = build_tail_chordwise(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute tail distributions: {exc}")
    results = []

if not results:
    st.info("No critical tail conditions to distribute. Set the tail span(s) in the "
            "**Empennage & control surfaces** section on the **Geometry** page, and "
            "ensure the Critical Loads tab (Flight Envelope (V-n) page) produced tail loads.")
else:
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
    # Display-only conversion; ``stations``/``res``/``results`` (recomputed by the
    # Loads Plots and Export pages via ``build_tail_chordwise``) are never touched.
    stations = sorted(res.stations, key=lambda s: s.x)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[to_si_scalar(s.x, "in", system) for s in stations],
        y=[to_si_scalar(s.psi, "psi", system) for s in stations],
        mode="lines+markers", line={"width": 3}, name="net PSI"))
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
                       file_name="tail_chordwise_loads_LIMIT.csv", mime="text/csv")

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
