"""Streamlit page for Loads Plots (Step D7): consolidated multi-case overlays.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

A read-only viewer over the distributed-load results **recomputed live from the
project inputs** (exactly as the Export page does — there is no code path that
constructs ``Project.loads``). It writes nothing back to the project: pick a
component, overlay the spanwise/chordwise curve for the selected case IDs plus
their two-sided envelope (pointwise max and min across the cases — a max-|value|
trace would hide the opposite-sign extreme, which can govern),
see a combined wing+fuselage "total loads" snapshot for one case, and
optionally compare against an externally-computed span-load CSV in the same
schema :mod:`sloads.export.sbeam_bridge` exports.

Wing torsion here (like the Export page) is stated about the wing surface's
**loads reference axis** (LRA, ``SurfaceInput.ref_axis_pct`` — the beam-model
elastic axis; the 25%-chord default reduces to the original suite's reporting),
via the ``net_loads.loads_ref_axis_results`` boundary transfer. Every torsion
label names its axis.

Engine Mount and Landing Gear are scalar reaction-load components with no
spanwise distribution -- the original suite never plotted them either, so they
are not in the component picker here; see their own Analysis pages.
"""

from __future__ import annotations

import csv
import io as _io
from types import SimpleNamespace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components import active_system, gate

from sloads import Project, UnitSystem, si_scalar_label, to_si_scalar
from sloads.modules.aileron import build_aileron
from sloads.modules.body_loads import build_body_loads
from sloads.modules.flap import build_flap
from sloads.modules.net_loads import (
    build_net_loads,
    loads_ref_axis_results,
    torsion_axis_label,
    wing_lra,
)
from sloads.modules.tab import build_tabs
from sloads.modules.taildist import build_tail_chordwise
from sloads.report import envelope_extremes

st.title("Loads Plots")

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()

# The wing torsion reference axis: the surface's loads reference axis (LRA),
# named in every torsion label below.
_LRA = wing_lra(project)
_WING_TORSION_AXIS = torsion_axis_label(_LRA)

st.caption(
    "Consolidated multi-case overlays over the distributed loads already computed "
    "on the Analysis pages. Values shown are **LIMIT** (oracle-traceable); the "
    "deliverable **ULTIMATE** loads (= limit × safety factor, 14 CFR 23.303) come "
    "from the **Review/Export** pages. Wing torsion Myy is stated about the "
    f"**{_WING_TORSION_AXIS}** (the wing's loads reference axis, set on the "
    "Geometry page); the envelope traces are the two-sided pointwise max/min "
    "across the selected cases."
)

_CALC_ERRORS = (ValueError, ZeroDivisionError, KeyError, IndexError)


def _try(fn, *args):
    """Run a build call defensively; return its value or ``None``."""
    try:
        return fn(*args)
    except _CALC_ERRORS:
        return None


# Recompute the distributed-load results live from the project inputs, exactly as
# the Export page does -- nothing is read from a persisted result slice (no code
# path constructs ``Project.loads``, so it is always ``None``). Wing results are
# transferred to the loads reference axis at this boundary, matching the export.
_net = _try(build_net_loads, project)
_control = []
for _fn in (build_aileron, build_flap, build_tabs):
    _control += _try(_fn, project) or []
loads = SimpleNamespace(
    wing_net=(loads_ref_axis_results(project, _net.wing_net)
              if _net is not None else []),
    body_net=_try(build_body_loads, project) or [],
    tail_chordwise=_try(build_tail_chordwise, project) or [],
    control_surface=_control,
)

if not any((loads.wing_net, loads.body_net, loads.tail_chordwise, loads.control_surface)):
    st.info(
        "No distributed loads computed yet — set the upstream inputs on the "
        "**Wing Loads**, **Fuselage Loads**, **Tail Loads**, and "
        "**Aileron/Flap/Tab Loads** pages first."
    )
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): shown curves may be an **unverified "
               "extrapolation** above the FAR 23 calibration band.")


# --------------------------------------------------------------------------- #
# Curve extraction: normalize every component's results into a common shape --
# (case_id, case_label, x, {y_field: (title, unit, [values])}) -- so the plot
# code below is generic across wing/fuselage/tail/control-surface results.
# --------------------------------------------------------------------------- #
def _case_label(r) -> str:
    return r.case_ref.case_id if r.case_ref else r.case


def _wing_cases(results, sys_=None):
    sys_ = system if sys_ is None else sys_
    return [
        (r.case_ref.case_id if r.case_ref else r.case, f"{_case_label(r)} — {r.case}",
         [to_si_scalar(s.y, "in", sys_) for s in r.stations],
         {"sz": ("Shear Sz", si_scalar_label("lbf", sys_),
                 [to_si_scalar(s.sz, "lbf", sys_) for s in r.stations]),
          "mxx": ("Bending Mxx", si_scalar_label("lb-in", sys_),
                  [to_si_scalar(s.mxx, "lb-in", sys_) for s in r.stations]),
          # The torsion label carries its reference axis (the result's stamp).
          "myy": (f"Torsion Myy about {r.torsion_axis}", si_scalar_label("lb-in", sys_),
                  [to_si_scalar(s.myy, "lb-in", sys_) for s in r.stations])})
        for r in results
    ]


def _fuselage_cases(results, sys_=None):
    sys_ = system if sys_ is None else sys_
    return [
        (r.case_ref.case_id if r.case_ref else r.case, f"{_case_label(r)} — {r.case}",
         [to_si_scalar(s.x, "in", sys_) for s in r.stations],
         {"sz": ("Shear Sz", si_scalar_label("lbf", sys_),
                 [to_si_scalar(s.sz, "lbf", sys_) for s in r.stations]),
          "myy": ("Bending Myy", si_scalar_label("lb-in", sys_),
                  [to_si_scalar(s.myy, "lb-in", sys_) for s in r.stations])})
        for r in results
    ]


def _tail_cases(results, component):
    filtered = [r for r in results if r.component == component]
    return [
        (r.case_ref.case_id if r.case_ref else r.case, f"{_case_label(r)} — {r.case}",
         [to_si_scalar(s.x, "in", system) for s in sorted(r.stations, key=lambda s: s.x)],
         {"psi": ("Net pressure PSI", si_scalar_label("psi", system),
                  [to_si_scalar(s.psi, "psi", system)
                   for s in sorted(r.stations, key=lambda s: s.x)])})
        for r in filtered
    ]


def _control_surface_cases(results, surface_match):
    filtered = [r for r in results if surface_match(r.surface)]
    return [
        (r.case_ref.case_id if r.case_ref else r.case,
         f"{_case_label(r)} — {r.surface}/{r.case}",
         [s.x for s in sorted(r.stations, key=lambda s: s.x)],
         {"psi": ("Pressure PSI", si_scalar_label("psi", system),
                  [to_si_scalar(s.psi, "psi", system)
                   for s in sorted(r.stations, key=lambda s: s.x)])})
        for r in filtered
    ]


_COMPONENTS = {
    "wing": ("Wing", lambda: _wing_cases(loads.wing_net),
             f"Butt line Y ({si_scalar_label('in', system)})"),
    "fuselage": ("Fuselage", lambda: _fuselage_cases(loads.body_net),
                 f"Fuselage station X ({si_scalar_label('in', system)})"),
    "htail": ("Horizontal Tail", lambda: _tail_cases(loads.tail_chordwise, "htail"),
              f"Chord station from LE ({si_scalar_label('in', system)})"),
    "vtail": ("Vertical Tail", lambda: _tail_cases(loads.tail_chordwise, "vtail"),
              f"Chord station from LE ({si_scalar_label('in', system)})"),
    "aileron": ("Aileron", lambda: _control_surface_cases(
        loads.control_surface, lambda s: s == "aileron"), "Fractional chord"),
    "flap": ("Flap", lambda: _control_surface_cases(
        loads.control_surface, lambda s: s == "flap"), "Fractional chord"),
    "tab": ("Tab", lambda: _control_surface_cases(
        loads.control_surface, lambda s: s.startswith("tab:")), "Fractional chord"),
}


def _overlay_figure(title: str, x_label: str, y_label: str, x: list,
                     traces: "list[tuple[str, list]]") -> go.Figure:
    fig = go.Figure()
    for name, y in traces:
        fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines+markers", line=dict(width=1.5)))
    if len(traces) > 1:
        # Two-sided envelope: pointwise max AND min across the cases. The
        # opposite-sign extreme can govern a different part of the structure, so
        # a single max-|value| trace is not a true envelope.
        upper, lower = envelope_extremes([y for _, y in traces])
        fig.add_trace(go.Scatter(x=x, y=upper, name="envelope (max)",
                                 mode="lines", line=dict(width=4, dash="dot")))
        fig.add_trace(go.Scatter(x=x, y=lower, name="envelope (min)",
                                 mode="lines", line=dict(width=4, dash="dash")))
    fig.update_layout(title=title, xaxis_title=x_label, yaxis_title=y_label,
                      legend=dict(orientation="h"), height=380)
    return fig


# --------------------------------------------------------------------------- #
# Component / case-ID pickers
# --------------------------------------------------------------------------- #
st.header("Overlay by case ID")

available = {k: v for k, v in _COMPONENTS.items() if v[1]()}
if not available:
    gate("No component has any distributed-load results yet — visit a component "
         "Loads page first.",
         "wing_loads", "fuselage_loads", "tail_loads",
         "aileron_loads", "flap_loads", "tab_loads", kind="info")
else:
    comp_key = st.radio(
        "Component", list(available.keys()),
        format_func=lambda k: available[k][0], horizontal=True)
    title, cases_fn, x_label = available[comp_key]
    cases = cases_fn()

    case_ids = [c[0] for c in cases]
    labels = {c[0]: c[1] for c in cases}
    selected = st.multiselect(
        "Case IDs", case_ids, default=case_ids, format_func=lambda cid: labels[cid])

    shown = [c for c in cases if c[0] in selected]
    if not shown:
        st.info("Select at least one case ID above.")
    else:
        y_fields = list(shown[0][3].keys())
        for field in y_fields:
            y_title, unit, _ = shown[0][3][field]
            traces = [(labels[cid], data[field][2]) for cid, _, _, data in shown]
            x = shown[0][2]
            fig = _overlay_figure(f"{y_title} — {title}", x_label,
                                  f"{y_title} ({unit}, LIMIT)", x, traces)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Case-index for this selection")
        st.dataframe(pd.DataFrame([
            {"Case ID": cid, "Condition": lab} for cid, lab, _, _ in shown
        ]), hide_index=True, use_container_width=True)

        # Comparison-CSV download: the currently displayed component/cases, one
        # row per station per case per y-field -- long format, easy to re-plot.
        buf = _io.StringIO()
        fieldnames = ["Case ID", "Condition", x_label, "Field", "Value"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for cid, lab, x, data in shown:
            for field, (y_title, unit, values) in data.items():
                for xv, yv in zip(x, values):
                    # ", LIMIT" travels with the file, matching the plot axis
                    # labels above (defect M4-15); the torsion y_title carries
                    # its reference axis the same way.
                    writer.writerow({"Case ID": cid, "Condition": lab, x_label: xv,
                                     "Field": f"{y_title} ({unit}, LIMIT)", "Value": yv})
        # The plotted two-sided envelope rows travel with the file too.
        if len(shown) > 1:
            for field in y_fields:
                y_title, unit, _ = shown[0][3][field]
                upper, lower = envelope_extremes([data[field][2] for _, _, _, data in shown])
                for env_name, env in (("ENVELOPE (max)", upper), ("ENVELOPE (min)", lower)):
                    for xv, yv in zip(shown[0][2], env):
                        writer.writerow({"Case ID": env_name,
                                         "Condition": "pointwise envelope of selection",
                                         x_label: xv,
                                         "Field": f"{y_title} ({unit}, LIMIT)", "Value": yv})
        st.download_button("Download this selection (CSV)", buf.getvalue(),
                           file_name=f"loads_plots_{comp_key}_LIMIT.csv", mime="text/csv")

# --------------------------------------------------------------------------- #
# Total-loads view: wing + fuselage side by side for one case each.
# --------------------------------------------------------------------------- #
st.divider()
st.header("Total loads (whole-airframe snapshot)")

wing_cases = _wing_cases(loads.wing_net)
body_cases = _fuselage_cases(loads.body_net)

if not wing_cases or not body_cases:
    gate("Needs both Wing Loads and Fuselage Loads results — visit those pages first.",
         "wing_loads", "fuselage_loads", kind="info")
else:
    c1, c2 = st.columns(2)
    wing_labels = {c[0]: c[1] for c in wing_cases}
    body_labels = {c[0]: c[1] for c in body_cases}
    wing_sel = c1.selectbox("Wing case", list(wing_labels), format_func=lambda k: wing_labels[k])
    body_sel = c2.selectbox("Fuselage case", list(body_labels), format_func=lambda k: body_labels[k])

    w = next(c for c in wing_cases if c[0] == wing_sel)
    b = next(c for c in body_cases if c[0] == body_sel)

    _force_lbl = si_scalar_label("lbf", system)
    _moment_lbl = si_scalar_label("lb-in", system)
    _in_lbl = si_scalar_label("in", system)

    fig = make_subplots(
        rows=1, cols=2, subplot_titles=("Wing", "Fuselage"),
        specs=[[{"secondary_y": True}, {"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=w[2], y=w[3]["sz"][2], name=f"Wing Sz ({_force_lbl})",
                             mode="lines+markers"), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=w[2], y=w[3]["mxx"][2], name=f"Wing Mxx ({_moment_lbl})",
                             mode="lines+markers"), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=w[2], y=w[3]["myy"][2],
                             name=f"Wing Myy about {_WING_TORSION_AXIS} ({_moment_lbl})",
                             mode="lines+markers"), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=b[2], y=b[3]["sz"][2], name=f"Fuselage Sz ({_force_lbl})",
                             mode="lines+markers"), row=1, col=2, secondary_y=False)
    fig.add_trace(go.Scatter(x=b[2], y=b[3]["myy"][2], name=f"Fuselage Myy ({_moment_lbl})",
                             mode="lines+markers"), row=1, col=2, secondary_y=True)
    fig.update_yaxes(title_text=f"Shear ({_force_lbl}, LIMIT)", secondary_y=False)
    fig.update_yaxes(title_text=f"Moment ({_moment_lbl}, LIMIT)", secondary_y=True)
    fig.update_xaxes(title_text=f"Butt line Y ({_in_lbl})", row=1, col=1)
    fig.update_xaxes(title_text=f"Fuselage station X ({_in_lbl})", row=1, col=2)
    fig.update_layout(height=420, legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------- #
# External-comparison CSV import: the sbeam_bridge span-load CSV schema
# (wing: Case,GID,X,Y,Z,Fx,Fz,My,Sx,Sz,Mxx,Myy,Mzz; body: Case,GID,X,Fz,Sz,Myy).
# Pure overlay against the live-computed curve above -- no numeric diff table.
# --------------------------------------------------------------------------- #
st.divider()
st.header("External-comparison import")
st.caption(
    "Import a span-load CSV in the same schema the **Export** page writes "
    "(`sloads.export.sbeam_bridge.span_load_csv` / `body_span_load_csv`) to "
    "overlay an externally-computed distribution against the curves above. "
    f"Computed wing torsion here is about the **{_WING_TORSION_AXIS}** — check "
    "the imported file's `MyyAxis` column states the same axis before comparing "
    "`Myy` (mixed axes are comparable only after transfer)."
)

_WING_COLS = {"Case", "GID", "X", "Y", "Z", "Fx", "Fz", "My", "Sx", "Sz", "Mxx", "Myy", "Mzz"}
_BODY_COLS = {"Case", "GID", "X", "Fz", "Sz", "Myy"}

uploaded = st.file_uploader("Span-load CSV", type=["csv"])
if uploaded is not None:
    try:
        # comment='#': an uploaded file may be one of this tool's own stamped
        # CSVs, whose methods block sits above the header row (G8.3).
        df = pd.read_csv(uploaded, comment="#")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        st.error(f"Could not parse CSV: {exc}")
        df = None

    if df is not None:
        cols = set(df.columns)
        if _WING_COLS.issubset(cols):
            kind, x_col, y_cols = "wing", "Y", ["Sz", "Mxx", "Myy"]
        elif _BODY_COLS.issubset(cols):
            kind, x_col, y_cols = "fuselage", "X", ["Sz", "Myy"]
        else:
            kind = None

        if kind is None:
            st.error(
                "Unrecognized column set. Expected either the wing span-load "
                f"schema ({sorted(_WING_COLS)}) or the fuselage schema "
                f"({sorted(_BODY_COLS)})."
            )
        else:
            # The imported span-load CSV is always in canonical Imperial units
            # (sloads.export.sbeam_bridge never converts), so build a
            # Imperial-forced overlay reference here regardless of the global
            # toggle -- the ``wing_cases``/``body_cases`` used in "Total loads"
            # above may be SI-converted and would otherwise mismatch units.
            computed = (
                _wing_cases(loads.wing_net, UnitSystem.IMPERIAL) if kind == "wing"
                else _fuselage_cases(loads.body_net, UnitSystem.IMPERIAL)
            )
            comp_labels = {c[0]: c[1] for c in computed} if computed else {}
            st.success(f"Recognized as a {kind} span-load CSV — "
                      f"{df['Case'].nunique()} case(s), {len(df)} rows.")
            overlay_target = None
            if comp_labels:
                overlay_target = st.selectbox(
                    f"Overlay against this computed {kind} case",
                    list(comp_labels), format_func=lambda k: comp_labels[k])
            for y_col in y_cols:
                fig = go.Figure()
                for case_name, grp in df.groupby("Case"):
                    grp = grp.sort_values(x_col)
                    fig.add_trace(go.Scatter(
                        x=grp[x_col], y=grp[y_col], name=f"imported: {case_name}",
                        mode="lines+markers", line=dict(dash="dash")))
                if overlay_target is not None:
                    ref = next(c for c in computed if c[0] == overlay_target)
                    field = y_col.lower()
                    if field in ref[3]:
                        fig.add_trace(go.Scatter(
                            x=ref[2], y=ref[3][field][2], name=f"computed: {comp_labels[overlay_target]}",
                            mode="lines+markers"))
                fig.update_layout(title=f"Imported vs computed — {y_col}",
                                  xaxis_title=x_col, yaxis_title=y_col, height=360,
                                  legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
