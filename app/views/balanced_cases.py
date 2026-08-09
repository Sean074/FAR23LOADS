"""Streamlit page for the balanced free-free airplane cases (plan 11 B2-B6).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

The mission's aim 2: a full airplane balanced case -- wing tip to wing tip, nose
to tail -- that needs no constraint because the loads balance. This page shows,
per case, the two numbers an engineer needs in order to trust it: **how far out
of balance the physics actually came** (the residual, before any correction) and
**how much was relieved to close it**. Those are the deliverable's honesty
statement, which is why they are columns here rather than a log line.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import active_system, gate

from sloads import (
    Project,
    UnitSystem,
    labels_for,
    to_display,
)
from sloads.export.balanced_deck import balanced_case_rows, balanced_deck
from sloads.models import MissingInputError
from sloads.modules.balance import RESIDUAL_GATE, build_balanced_cases

st.title("Balanced Cases — assembled full-span, free-free")
st.caption(
    "Aero and inertia together, both wings: the wing distribution recomputed at "
    "the case's own V-n point, the balancing tail load, the fuselage inertia from "
    "the itemized weight database, and the fuselage's share of the trim pitching "
    "moment. The assembled deck is the mission's primary loads deliverable; the "
    "per-component decks are analysis views of it."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = active_system()
U = labels_for(system)

if project.flight_loads is None or project.wing_mass is None:
    gate("Define the flight-loads inputs on the **Flight Envelope (V-n)** page "
         "and the wing mass on **Wing Loads** first.", "flight_envelope")
    st.stop()

try:
    cases = build_balanced_cases(project)
except (MissingInputError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

if not cases:
    st.warning(
        "No wing condition assembles into a balanced case. A condition "
        "needs a V-n point **and** a payload loading the weight database can "
        "actually produce — a CG case requiring a large fictitious ballast has no "
        "honest inertia set, and assembling one would put invented mass into the "
        "very balance the case exists to demonstrate. See the **Weights → Mass "
        "Export** tab for which loadings are derivable and why."
    )
    st.stop()

# --------------------------------------------------------------------------- #
# The residual table -- the case's own honesty statement
# --------------------------------------------------------------------------- #
st.subheader("Balance quality")
rows = balanced_case_rows(cases)
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption(
    f"Residuals are measured **before** closure — the gate ({RESIDUAL_GATE:.0%}) "
    "is on the physics, not on the correction. `dn` is the mass-proportional "
    "relief applied to close what was left. **Roll couple** is different in kind: "
    "on a rolling case (FAR 23.349) it is the *applied* aileron moment, which the "
    "airplane is supposed not to balance — it rolls — and it is reacted in full by "
    "distributed roll-acceleration inertia. It is reported, not gated."
)

worst = max(max(c.force_residual_fraction, c.moment_residual_fraction)
            for c in cases)
if worst < RESIDUAL_GATE:
    st.success(
        f"Every case balances to better than {RESIDUAL_GATE:.0%} of n·W before "
        f"any relief (worst {worst:.3%}).")
else:
    st.warning(
        f"Worst pre-closure residual is {worst:.3%} of n·W, over the "
        f"{RESIDUAL_GATE:.0%} gate. The usual cause is the strip-quadrature "
        "floor: the spanwise integration of lift differs slightly from the "
        "trim solve's closed form, and a coarser element count widens it.")

# --------------------------------------------------------------------------- #
# Where the load comes from
# --------------------------------------------------------------------------- #
st.subheader("Load breakdown")
labels = {
    "wing-air": "Wing air load",
    "wing-inertia": "Wing inertia",
    "tail-air": "Balancing tail load",
    "body-inertia": "Fuselage + empennage inertia",
    "fuselage-cm": "Fuselage pitching moment (lumped)",
    "aileron-roll": "Aileron rolling moment (lumped)",
    "closure-n": "Closure — vertical / longitudinal relief",
    "closure-pitch": "Closure — pitch relief",
    "closure-roll": "Roll-acceleration inertia",
}
def _case_label(c) -> str:
    """The selector entry. **Must** carry the hand: the two twins of a rolling
    case are otherwise identical strings, and the picker would silently show the
    starboard case whichever one was chosen."""
    hand = {"R": " — starboard roll", "L": " — port roll"}.get(c.hand, "")
    return f"{c.label}{hand} (V-n {c.vn_case}, {c.cg})"


names = [_case_label(c) for c in cases]
pick = st.selectbox("Case", names)
case = cases[names.index(pick)]

totals = {}
for load in case.loads:
    entry = totals.setdefault(load.source, [0.0, 0.0])
    entry[0] += load.fz
    entry[1] += load.my
st.dataframe(pd.DataFrame([
    {"Source": labels.get(src, src),
     f"ΣFz ({U['weight']})": f"{to_display(v[0], 'weight', system):,.1f}",
     "Cards": sum(1 for ld in case.loads if ld.source == src)}
    for src, v in totals.items()
]), hide_index=True, use_container_width=True)
st.caption(
    "No wing carry-through reaction appears here, and none may: it is the seam "
    "between two free bodies, and in an assembled model the solver recovers it. "
    "Applying it as well would react the wing twice."
)
for note in case.notes:
    st.info(note)

# --------------------------------------------------------------------------- #
# Spanwise picture
# --------------------------------------------------------------------------- #
fig = go.Figure()
for src, colour in (("wing-air", None), ("wing-inertia", None)):
    pts = sorted(((ld.y, ld.fz) for ld in case.loads if ld.source == src))
    if pts:
        fig.add_trace(go.Scatter(
            x=[to_display(y, "length", system) for y, _ in pts],
            y=[to_display(f, "weight", system) for _, f in pts],
            mode="lines+markers", name=labels[src]))
fig.update_layout(
    title=f"{case.label} — spanwise applied load, both wings",
    xaxis_title=f"Butt line y ({U['length']})",
    yaxis_title=f"Applied Fz ({U['weight']}, LIMIT)",
    height=420)
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------- #
# The deck
# --------------------------------------------------------------------------- #
st.subheader("Assembled deck")
try:
    deck = balanced_deck(project, system=system, cases=cases)
except ValueError as exc:
    st.error(str(exc))
else:
    st.download_button(
        "Download assembled full-span deck (BDF)", deck,
        file_name="balanced_airframe.bdf", mime="text/plain", key="dl_balanced")
    st.caption(
        "One `SUBCASE` per balanced case, both wings, on a statically "
        "determinate support — the recovered reaction *is* the residual above, "
        "so 'reactions ≈ 0' is the free-free equilibrium proof rather than a "
        "modelling convenience."
    )
