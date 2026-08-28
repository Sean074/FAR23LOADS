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

from app_shell.components import (
    active_system,
    gate,
    render_page_order_reads,
    stop_page,
)
from app_shell.widget_keys import widget_key
from sloads import (
    Project,
    UnitSystem,
    labels_for,
    to_display,
)
from sloads.export.balanced_deck import balanced_case_rows, balanced_deck
from sloads.models import MissingInputError
from sloads.modules.balance import (
    FORCE_RESIDUAL_ACCEPTANCE,
    RESIDUAL_GATE,
    build_balanced_cases,
    case_source_name,
    is_ground,
    is_lateral,
    is_unsymmetrical_htail,
    residual_gate_exemptions,
    residual_gate_family,
    skipped_condition_lines,
)
from sloads.report.methods import bdf_comment_block

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

# This page opens with its own title rather than the shared ``page_header``
# (one of fourteen main-GUI views that do; the split is #29's to settle), so the
# later-page dependency mark is called directly. The assembled cases read the
# engine thrust and the ground-case slice, both entered downstream (#69).
render_page_order_reads(project, "balanced_cases")

if project.flight_loads is None or project.wing_mass is None:
    gate("Define the flight-loads inputs on the **Flight Envelope (V-n)** page "
         "and the wing mass on **Wing Loads** first.", "flight_envelope")
    stop_page()

skipped = []
try:
    cases = build_balanced_cases(project, skipped)
except (MissingInputError, ValueError) as exc:
    st.error(str(exc))
    stop_page()

# The record of what did NOT assemble (review F-C7) — stated before the results
# and before the "nothing assembled" stop below, because it is the answer to
# "why is my condition not here?" in both situations.
lines = skipped_condition_lines(skipped)
with st.expander(f"Conditions not assembled into a balanced case ({len(skipped)})",
                 expanded=not cases):
    if lines:
        for line in lines:
            st.markdown(f"- {line}")
        # No summary caption here: each line above already carries its own
        # reason from `skipped_condition_lines`, the single owner of that
        # wording. The caption that used to sit here restated them and had gone
        # stale doing it — it called ground conditions "a deliberate exclusion …
        # covered by the per-component analyses", which has been false in both
        # halves since 0.6.0 (ground conditions assemble, and the per-component
        # fuselage view is flight-only by D-28). CR-C-2.
    else:
        st.markdown("None — every condition SELECT named was assembled.")

if not cases:
    st.warning(
        "No wing condition assembles into a balanced case. A condition "
        "needs a V-n point **and** a payload loading the weight database can "
        "actually produce — a CG case requiring a large fictitious ballast has no "
        "honest inertia set, and assembling one would put invented mass into the "
        "very balance the case exists to demonstrate. See the **Weights → Mass "
        "Export** tab for which loadings are derivable and why."
    )
    stop_page()

# --------------------------------------------------------------------------- #
# The residual table -- the case's own honesty statement
# --------------------------------------------------------------------------- #
st.subheader("Balance quality")
rows = balanced_case_rows(cases)
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
st.caption(
    f"Residuals are measured **before** closure — the gate ({RESIDUAL_GATE:.0%}) "
    "is on the physics, not on the correction. `dn` is the mass-proportional "
    "relief applied to close what was left. **Roll couple** is different in kind: "
    "on a rolling case (FAR 23.349) it is the *applied* aileron moment, which the "
    "airplane is supposed not to balance — it rolls — and it is reacted in full by "
    "distributed roll-acceleration inertia. It is reported, not gated."
)
st.caption(
    "**dNy**, **yaw** and **roll acceleration** are the answer of a lateral case "
    "(FAR 23.441/23.443): nothing in an airplane balances a rudder kick, so the "
    "fin's side load appears in full as a pre-closure `Fy`/`Mz` and the three "
    "columns are the motion that reacts it — `Ny = Lv/W` exactly. On a symmetric "
    "case they read zero, which is the statement that it has no lateral motion."
)

st.caption(
    "**Pitch acceleration** is the answer of the unsymmetrical h-tail case "
    "(FAR 23.427(a)) in the same way: its applied tail load is a *maneuver* load "
    "and replaces the trim tail load the V-n point balances at, so the airplane "
    "is genuinely not in trim — the pre-closure `Fz`/`My` are that mismatch in "
    "full, and the vertical and pitch relief are the motion. The residual gate "
    "below is on the case's trim half, which is unchanged, so those rows are "
    "excluded from it rather than judged by a number that does not apply to them."
)

# The verdict is over the family the gate applies to, through the one owner of
# that question (CR-C-2). Excluding only the 23.427(a) family, as this page used
# to, left the ground cases in — and a ground case's pre-closure residual is the
# applied gear load in full, so the page warned at 100.000 % on every project
# with landing conditions while the gated family sat under 1 %.
judged, clamped = residual_gate_family(cases)
exempt = residual_gate_exemptions(cases)
force = max((c.force_residual_fraction for c in judged), default=0.0)
pitch = max((c.moment_residual_fraction for c in judged), default=0.0)
if not judged:
    st.info("No assembled case is judged against the pre-closure residual "
            "acceptances.")
elif force < FORCE_RESIDUAL_ACCEPTANCE and pitch < RESIDUAL_GATE:
    st.success(
        f"All {len(judged)} judged cases are inside acceptance before any "
        f"relief: worst force residual {force:.3%} of n·W (limit "
        f"{FORCE_RESIDUAL_ACCEPTANCE:.1%}), worst pitch residual {pitch:.3%} of "
        f"n·W·MAC (limit {RESIDUAL_GATE:.0%}).")
else:
    st.warning(
        f"Over acceptance across the {len(judged)} judged cases: worst force "
        f"residual {force:.3%} of n·W (limit {FORCE_RESIDUAL_ACCEPTANCE:.1%}), "
        f"worst pitch residual {pitch:.3%} of n·W·MAC (limit "
        f"{RESIDUAL_GATE:.0%}). It is reported rather than suppressed; the table "
        "above localises it.")
if clamped:
    st.caption(
        f"A further **{len(clamped)}** case(s) carry a non-wing axial force that "
        "was *not* applied — the trim α falls outside the polar's trusted window "
        "— so they are out of trim by exactly that clamped force and its couple "
        "about the CG. Their residuals are that known quantity rather than a "
        "balance quality, and are gated per case against what was measured when "
        "the clamp was decided."
    )
if exempt:
    st.caption(
        "The gate does not apply to " + "; ".join(exempt) + " — for those the "
        "pre-closure residual **is** the applied load, by construction, and each "
        "carries its own stronger gate instead. Those rows are in the table "
        "above, reported and not judged by a number that does not fit them."
    )

# --------------------------------------------------------------------------- #
# Where the load comes from
# --------------------------------------------------------------------------- #
st.subheader("Load breakdown")
labels = {
    "wing-air": "Wing air load",
    "wing-inertia": "Wing inertia",
    "tail-air": "Balancing tail load",
    "vtail-air": "Fin side load (lateral case)",
    "htail-air": "Horizontal-tail load, distributed (23.427(a) case)",
    "body-inertia": "Fuselage + empennage inertia",
    "fuselage-cm": "Fuselage pitching moment (lumped)",
    "body-axial": "Non-wing drag (airplane-less-tail polar less the wing strips)",
    "aileron-roll": "Aileron rolling moment (lumped)",
    "closure-n": "Closure — vertical / longitudinal relief",
    "closure-pitch": "Closure — pitch relief",
    "closure-roll": "Roll-acceleration inertia",
    "closure-yaw": "Yaw-acceleration inertia",
    "closure-self": "Point-mass self-inertia (free moment)",
}
def _case_label(c) -> str:
    """The selector entry. **Must** carry the hand: the two twins of a rolling
    case are otherwise identical strings, and the picker would silently show the
    starboard case whichever one was chosen."""
    if is_ground(c):
        # A ground case's label already names the condition, and its hand is the
        # drift direction rather than a roll -- the same distinction the deck
        # header draws (decision G-8, R6-C3).
        hand = {"R": " — starboard", "L": " — port"}.get(c.hand, "")
    else:
        kind = ("side load" if is_lateral(c)
                else "tail load split" if is_unsymmetrical_htail(c) else "roll")
        hand = {"R": f" — starboard {kind}",
                "L": f" — port {kind}"}.get(c.hand, "")
    return f"{c.label}{hand} ({case_source_name(c, short=True)}, {c.cg})"


names = [_case_label(c) for c in cases]
pick = st.selectbox("Case", names, key=widget_key("bal_case"))
case = cases[names.index(pick)]

totals = {}
for load in case.loads:
    entry = totals.setdefault(load.source, [0.0, 0.0])
    entry[0] += load.fz
    # Side force, not pitching moment: a fin load is entirely ΣFy, so a
    # breakdown with a vertical column only would report the defining load of
    # every lateral case as a row of zeros.
    entry[1] += load.fy
st.dataframe(pd.DataFrame([
    {"Source": labels.get(src, src),
     f"ΣFz ({U['weight']})": f"{to_display(v[0], 'weight', system):,.1f}",
     f"ΣFy ({U['weight']})": f"{to_display(v[1], 'weight', system):,.1f}",
     "Cards": sum(1 for ld in case.loads if ld.source == src)}
    for src, v in totals.items()
]), hide_index=True, width="stretch")
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
for src in ("wing-air", "wing-inertia"):
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
st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------------------- #
# The deck
# --------------------------------------------------------------------------- #
st.subheader("Assembled deck")
# Stamped like every other deck the suite writes (G8.3 / review F-D2): the
# primary deliverable states its own ULTIMATE basis, category and unit system
# in-band, because this button is a route out of the tool in its own right --
# the file is often forwarded without the bundle that would otherwise carry the
# statement. `scope` is the full case set: the Critical Loads opt-out never
# reaches the balanced assembly.
_stamp = bdf_comment_block(project, scope="full case set", system=system)
try:
    deck = balanced_deck(project, header_comment=_stamp, system=system,
                         cases=cases, skipped=skipped)
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
