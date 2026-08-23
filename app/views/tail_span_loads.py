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

from app_shell.components import active_system, gate, workflow_page_link
from app_shell.widget_keys import widget_key
from sloads import (
    Project,
    UnitSystem,
    labels_for,
    mass_distribution,
    to_display,
)
from sloads.models import MissingInputError
from sloads.modules.tail_span import (
    air_total,
    axial_total,
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
# Surface mass -- derived, not entered here (the mass SSOT)
# --------------------------------------------------------------------------- #
st.subheader("Empennage surface mass")
st.caption(
    "Read from the **weight data base** — the `htail` / `vtail` rows of the "
    "*Weights & Mass* page's item table, tagged by their `component` column. This "
    "page owns no mass input: one airplane has one mass model, and entering the "
    "tail twice is how the two drift apart. Distributed as a **uniform area "
    "density** over the planform and applied as `−n · W` (d'Alembert), so the "
    "sign follows the case's load factor alone — the tail's own mass **adds** to "
    "a down-load condition rather than relieving it, which is both the correct "
    "and the conservative direction for the conditions that size a horizontal "
    "tail."
)
_derived = {c: mass_distribution.tail_surface_weight(project, c) for c in (HTAIL, VTAIL)}
_cols = st.columns(2)
for _col, (_name, _label) in zip(_cols, ((HTAIL, "Horizontal tail"), (VTAIL, "Vertical tail"))):
    _override = next((tm for tm in project.tail_mass or []
                      if tm.surface == _name and tm.weight_is_override), None)
    _col.metric(
        f"{_label} ({U['weight']})",
        f"{to_display(_derived[_name], 'weight', system):,.1f}",
        help="Whole surface: both sides for the horizontal tail, the single fin "
             "for the vertical.")
    if _override is not None:
        _col.caption("⚠️ **Explicit override** in the project file — the weight "
                     "data base is not being used for this surface.")

_untagged = [c for c in (HTAIL, VTAIL) if not _derived[c]]
if _untagged:
    st.warning(
        f"**No mass items tagged `{'` / `'.join(_untagged)}`** in the weight data "
        "base, so the surface(s) below carry **air load only**. That is a gap in "
        "the data, not a weightless tail: open the *Weights & Mass* page and set "
        "the `component` column on the empennage rows."
    )
for _surface in (HTAIL, VTAIL):
    _check = mass_distribution.tail_reconciliation(project, _surface)
    if _check is not None and not _check.ok:
        st.info(f"**{_surface} mass:** {_check.detail}")
workflow_page_link("weight_mass", label="→ Weight & Mass Properties (the mass SSOT)")

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
# A fin case can carry the axial term with **no** lateral one: no V-n point means
# no case weight, so n_y has no denominator and is reported as absent rather than
# invented. The relief figure below therefore reads from a case that has one.
_fin = [r for r in results if r.component == VTAIL and r.inertia_modelled]
_fin_lat = [r for r in _fin if r.case_weight_lb > 0.0]
if _fin:
    _relief = (f"`W_vt/W` ≈ "
               f"{100.0 * _fin_lat[0].surface_weight_lb / _fin_lat[0].case_weight_lb:.2f} %"
               if _fin_lat else "`W_vt/W` of the case weight")
    st.caption(
        "**The fin's mass acts on two axes, and they are different loads.** Its "
        "*bending* inertia runs sideways at `n_y = side load / case weight` — the "
        "free-free lateral response to the fin's own load, the only lateral "
        f"aerodynamic force this suite models — which **relieves** the surface "
        f"total by {_relief}. Its *axial* inertia runs along the span at the "
        "case's own `n`, because a fin spans vertically: it compresses the "
        "surface and bends nothing. Since no fuselage or wing sideslip force is "
        "modelled, the real airplane's `n_y` is smaller than this and the relief "
        "above is an upper bound on itself."
    )

st.subheader("Case summary")
_rows = []
for r in results:
    root = r.stations[root_index(r)] if r.stations else None
    _rows.append({
        "Surface": r.component,
        "Case": r.case,
        "n": f"{r.n_case:.3f}",
        # The fin bends under n_y and compresses under n; the h-tail has only the
        # one axis, so its cells are blank rather than a misleading 0.000.
        "n_y": f"{r.n_y:+.4f}" if r.component == VTAIL else "—",
        f"Air total ({U['weight']})": f"{to_display(air_total(r), 'weight', system):.1f}",
        f"Inertia ({U['weight']})": f"{to_display(inertia_total(r), 'weight', system):.1f}",
        f"Axial ({U['weight']})": (
            f"{to_display(axial_total(r), 'weight', system):.1f}"
            if r.component == VTAIL else "—"),
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
_pick = st.selectbox("Case", _names, key=widget_key("tspan_case"))
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

# The discrete control-surface load path (plan 09 T6). Shown beside the strip
# table rather than folded into it, because these are different points on the
# structure -- hinge stations are not strip midpoints -- and the hinge moment is
# a deliverable in its own right, the first one the suite produces.
if case.control_loads:
    st.markdown("**Control-surface attachment loads** (discrete mode)")
    _attach = [{
        "Point": cp.kind,
        f"{_span_label} ({U['length']})": to_display(cp.y, "length", system),
        f"X on LRA ({U['length']})": to_display(cp.x, "length", system),
        f"Normal load ({U['weight']})": to_display(cp.f_normal, "weight", system),
        f"Torsion ({U['torque']})": to_display(cp.m_torsion, "torque", system),
    } for cp in case.control_loads]
    st.dataframe(pd.DataFrame(_attach).round(3), hide_index=True,
                 use_container_width=True)
    _hm_cols = st.columns(3)
    _hm_cols[0].metric(f"Control-surface load ({U['weight']})",
                       f"{to_display(case.control_surface_load_lb, 'weight', system):,.1f}")
    _hm_cols[1].metric(f"Hinge moment ({U['torque']})",
                       f"{to_display(case.hinge_moment_lbin, 'torque', system):,.0f}")
    _hm_cols[2].metric(f"On an arm of ({U['length']})",
                       f"{to_display(case.hinge_moment_arm_in, 'length', system):,.2f}")
    st.caption(
        "The control surface's own load is **out** of the strip table above and "
        f"applied here instead — {case.control_load_basis}. The hinge moment is "
        "that load on the centroid of the aft-of-hinge pressure block (a third of "
        "the aft-of-hinge chord), reacted as a couple at the actuator; the hinges "
        "carry the load itself, shared by tributary span. Values are **LIMIT**."
    )

if case.tip_transfer is not None:
    _t = case.tip_transfer
    st.markdown("**T-tail transfer at the fin tip**")
    _tt = st.columns(3)
    _tt[0].metric(f"Transferred Fz ({U['weight']})",
                  f"{to_display(_t.fz, 'weight', system):,.1f}")
    _tt[1].metric(f"Transferred Myy ({U['torque']})",
                  f"{to_display(_t.myy, 'torque', system):,.0f}")
    _tt[2].metric(f"of which inertia ({U['weight']})",
                  f"{to_display(_t.inertia_lb, 'weight', system):,.1f}")
    st.caption(
        "On a T-tail the horizontal surface reaches the airplane **through the "
        "fin**, so this fin case also carries the h-tail load concurrent with it: "
        "the balancing load at this case's own V-n point plus the h-tail's own "
        "inertia there. Roll and yaw transfer are zero — that pairing is a "
        "balancing condition, so the horizontal tail's two halves cancel about the "
        "centreline. Values are **LIMIT**."
    )

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
    yaxis2={"title": f"Cumulative Sz ({U['weight']})", "overlaying": "y", "side": "right"},
    height=420, legend={"orientation": "h"})
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
_writer = csv.DictWriter(_buf, fieldnames=["Surface", "Case", "Basis", *_fields])
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
