"""Streamlit page for the spanwise empennage loads (plan 09 T3).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

The **Tail Loads** page distributes each critical tail load *chordwise* (TAILDIST,
Ch 10, oracle-locked) — the pressure profile a surface is skinned to. This page
distributes the same conditions *spanwise*, on the surface's own load reference
axis: the per-station shear, bending and torsion a beam model is sized from, and
the table the empennage deck is written from.

Displayed **LIMIT**, per the CLAUDE.md analysis-page carve-out, and marked as
such; the ULTIMATE deliverable is the deck on the Export page.
"""

from __future__ import annotations

import csv
import io as _io

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
from sloads.models import MissingInputError, TailMassInput
from sloads.modules.tail_span import (
    air_total,
    build_tail_span,
    inertia_total,
    root_index,
)
from sloads.tail_geometry import HTAIL, VTAIL, resolve_tail_planform

st.title("Tail Span Loads — spanwise empennage distribution")
st.caption(
    "The empennage's structural deliverable: SELECT's critical tail loads spread "
    "**along the span** in proportion to local chord, with the surface's own "
    "inertia, reported about its load reference axis. The chordwise pressure "
    "profile for the same conditions is on the **Tail Loads** page — these are two "
    "views of one set of conditions, not two load sets."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = active_system()
U = labels_for(system)

if project.flight_loads is None or project.tail_loads is None:
    gate("Define the flight-loads inputs on the **Flight Envelope (V-n)** page and "
         "the empennage geometry on the **Geometry** page first.", "flight_envelope")
    st.stop()

# --------------------------------------------------------------------------- #
# Surface mass (the only input this page owns)
# --------------------------------------------------------------------------- #
st.subheader("Empennage surface mass")
st.caption(
    "Distributed as a **uniform area density** over the planform, and applied as "
    "`−n · W` (d'Alembert): the sign follows the case's load factor alone, so the "
    "tail's own mass **adds** to a down-load condition rather than relieving it. "
    "That is the conservative and the correct direction — the conditions that size "
    "a GA horizontal tail are down-load ones. Leave a surface at zero to report "
    "air load only."
)
_existing = {tm.surface: tm.panel_weight_lb for tm in project.tail_mass or []}
with st.form("tail_mass_form"):
    _cols = st.columns(2)
    _h_w = _cols[0].number_input(
        f"Horizontal tail, whole surface ({U['weight']})",
        min_value=0.0, value=float(to_display(_existing.get(HTAIL, 0.0), "weight", system)),
        step=1.0, key="tail_mass_h")
    _v_w = _cols[1].number_input(
        f"Vertical tail ({U['weight']})",
        min_value=0.0, value=float(to_display(_existing.get(VTAIL, 0.0), "weight", system)),
        step=1.0, key="tail_mass_v")
    if st.form_submit_button("Apply tail mass", type="primary"):
        from sloads import to_imperial_scalar

        project.tail_mass = [
            TailMassInput(surface=name, panel_weight_lb=to_imperial_scalar(w, "weight", system))
            for name, w in ((HTAIL, _h_w), (VTAIL, _v_w)) if w
        ]
        st.session_state["project"] = project
        st.rerun()

# --------------------------------------------------------------------------- #
# The distributions
# --------------------------------------------------------------------------- #
try:
    spans = build_tail_span(project)
except (MissingInputError, ValueError) as exc:
    st.error(str(exc))
    st.stop()

results = spans[HTAIL] + spans[VTAIL]
if not results:
    st.warning(
        "No empennage surface has both a planform (area + span, on the **Geometry** "
        "page) and a critical condition carrying an LT25/LT50 split."
    )
    st.stop()

_assumed = [r for r in results if r.planform_assumed]
if _assumed:
    st.info(
        "**Planform derived, not entered.** No `htail`/`vtail` surface is defined in "
        "the geometry, so a **rectangular** planform was derived from the tail area "
        "and span. It is a first-order stand-in: a real tapered tail carries its "
        "load further inboard, so root bending here is conservative but the "
        "station-by-station distribution is not the surface's own. Add a surface "
        "named `htail` or `vtail` on the **Geometry** page to use the real planform "
        "— it is validated against the area/span to 1 %."
    )
if any(not r.inertia_modelled and r.component == VTAIL for r in results):
    st.caption(
        "The vertical tail carries **no inertia load**: the suite has no lateral "
        "load factor, and applying the airplane's normal `n` to a fin's mass would "
        "be a fabricated load in the wrong direction."
    )

st.subheader("Case summary")
_rows = []
for r in results:
    root = r.stations[root_index(r)] if r.stations else None
    _rows.append({
        "Surface": r.component,
        "Case": r.case,
        "n": f"{r.n_case:.3f}",
        f"Air total ({U['weight']})": f"{to_display(air_total(r), 'weight', system):.1f}",
        f"Inertia ({U['weight']})": f"{to_display(inertia_total(r), 'weight', system):.1f}",
        f"Root Sz ({U['weight']})": f"{to_display(root.sz, 'weight', system):.1f}" if root else "—",
        f"Root Mxx ({U['torque']})": f"{to_display(root.mxx, 'torque', system):.0f}" if root else "—",
        f"Root Myy ({U['torque']})": f"{to_display(root.myy, 'torque', system):.0f}" if root else "—",
        "RH×": f"{r.rh_scale:.3f}",
        "LH×": f"{r.lh_scale:.3f}",
        "Basis": "LIMIT",
    })
st.dataframe(pd.DataFrame(_rows), hide_index=True, use_container_width=True)
st.caption(
    f"Torsion is stated about **{results[0].torsion_axis}** — every torsion names "
    "its axis. `RH×`/`LH×` are the per-side shares: equal except under FAR "
    "23.427(a), the unsymmetrical condition, where they are SELECT's own split. "
    "Values are **LIMIT**; the exported deck is ULTIMATE."
)

# --------------------------------------------------------------------------- #
# Per-case station table + plot
# --------------------------------------------------------------------------- #
st.subheader("Station table")
_names = [f"{r.component} — {r.case}" for r in results]
_pick = st.selectbox("Case", _names)
case = results[_names.index(_pick)]
planform = resolve_tail_planform(project, case.component)

_span_label = "Butt line Y" if case.component == HTAIL else "Fin station"
_fields = [f"{_span_label} ({U['length']})", f"X on LRA ({U['length']})",
           f"Fz ({U['weight']})", f"Sz ({U['weight']})",
           f"Mxx ({U['torque']})", f"Myy ({U['torque']})"]
_table = [{
    _fields[0]: to_display(st_.y, "length", system),
    _fields[1]: to_display(st_.x, "length", system),
    _fields[2]: to_display(st_.fz, "weight", system),
    _fields[3]: to_display(st_.sz, "weight", system),
    _fields[4]: to_display(st_.mxx, "torque", system),
    _fields[5]: to_display(st_.myy, "torque", system),
} for st_ in case.stations]
st.dataframe(pd.DataFrame(_table).round(3), hide_index=True, use_container_width=True)

if case.notes:
    for _note in case.notes:
        st.caption(f"• {_note}")

_fig = go.Figure()
_fig.add_trace(go.Bar(x=[row[_fields[0]] for row in _table],
                      y=[row[_fields[2]] for row in _table], name="Strip Fz"))
_fig.add_trace(go.Scatter(x=[row[_fields[0]] for row in _table],
                          y=[row[_fields[3]] for row in _table],
                          name="Cumulative Sz", yaxis="y2", mode="lines+markers"))
for _y in case.attachment_y:
    _fig.add_vline(x=to_display(_y, "length", system), line_dash="dot",
                   annotation_text="attachment")
_fig.update_layout(
    xaxis_title=f"{_span_label} ({U['length']})",
    yaxis_title=f"Strip Fz ({U['weight']}, LIMIT)",
    yaxis2=dict(title=f"Cumulative Sz ({U['weight']})", overlaying="y", side="right"),
    height=420, legend=dict(orientation="h"))
st.plotly_chart(_fig, use_container_width=True)
if case.attachment_y:
    st.caption(
        "The horizontal tail is a **full-span** beam, tip to tip through the "
        "centreline, reacted at the fuselage attachment stations marked above — "
        "not a semispan table doubled. That is the topology that carries the "
        "23.427(a) left/right asymmetry in one model."
    )

# --------------------------------------------------------------------------- #
# Download -- converted, unit-suffixed (lesson L-8i)
# --------------------------------------------------------------------------- #
_buf = _io.StringIO()
_writer = csv.DictWriter(_buf, fieldnames=["Surface", "Case", "Basis"] + _fields)
_writer.writeheader()
for r in results:
    for st_ in r.stations:
        _writer.writerow({
            "Surface": r.component, "Case": r.case, "Basis": "LIMIT",
            _fields[0]: f"{to_display(st_.y, 'length', system):.4f}",
            _fields[1]: f"{to_display(st_.x, 'length', system):.4f}",
            _fields[2]: f"{to_display(st_.fz, 'weight', system):.4f}",
            _fields[3]: f"{to_display(st_.sz, 'weight', system):.4f}",
            _fields[4]: f"{to_display(st_.mxx, 'torque', system):.3f}",
            _fields[5]: f"{to_display(st_.myy, 'torque', system):.3f}",
        })
st.download_button("Download spanwise tail loads (CSV)", _buf.getvalue(),
                   file_name="tail_span_loads_LIMIT.csv", mime="text/csv",
                   key="dl_tail_span")
st.caption(
    "Converted to the selected unit system with unit-suffixed headers, and marked "
    "**LIMIT** — the ULTIMATE `FORCE`/`MOMENT` deck is on the **Export** page."
)
if planform is not None and planform.assumed:
    st.caption("Planform: **derived rectangle** — see the note above.")
