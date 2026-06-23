"""Streamlit page for the balanced-tail-load verification utility (BALLOADS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Off-pipeline cross-check: recomputes the horizontal-tail balancing load rationally
(reusing SELECT's balance routine) for every flaps-retracted V-n condition and
compares the rational centre of pressure against the *approximate* XTC station
FLTLOADS assumed (Reference 1 Ch 8-9, BALLOADS.BAS).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import Project
from farloads.modules.balloads import verify_balancing


st.title("Balanced Tail Load Verification — BALLOADS")
st.caption(
    "Python/Streamlit port of BALLOADS.BAS (Hal C. McMaster). Recomputes the "
    "rational balancing horizontal-tail load (AoA load at 25% MAC + camber/elevator "
    "load at 50%) and verifies FLTLOADS' approximate tail centre of pressure "
    "(FAR 23.421). Note the elevator load is not always opposite the stabilizer load."
)

project: Project = st.session_state.get("project", Project(name=""))

if project.flight_loads is None or project.tail_loads is None:
    st.warning("Define the **Flight Envelope** and **Tail Loads** inputs first "
               "(BALLOADS verifies the balancing tail CP they produce).")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): balancing loads are an **unverified "
               "extrapolation** above the FAR 23 calibration band.")

try:
    rows = verify_balancing(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not verify balancing loads: {exc}")
    st.stop()

if not rows:
    st.info("No flaps-retracted balanced V-n points to verify.")
    st.stop()

st.caption(
    "Balance-check tool: the loads shown are **LIMIT** (oracle values, traceable "
    "to the manual). The deliverable **ULTIMATE** loads (= limit × 1.5, 14 CFR "
    "23.303) come from the **Review/Export** pages."
)
up = max(rows, key=lambda r: r["LT"])
dn = min(rows, key=lambda r: r["LT"])
c1, c2 = st.columns(2)
c1.metric("Largest UP balancing load LT (LIMIT)", f"{up['LT']:.1f} lb", f"CP {up['CP']:.2f}% MAC")
c2.metric("Largest DOWN balancing load LT (LIMIT)", f"{dn['LT']:.1f} lb", f"CP {dn['CP']:.2f}% MAC")

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
} for r in rows])
st.dataframe(table, hide_index=True, use_container_width=True)
