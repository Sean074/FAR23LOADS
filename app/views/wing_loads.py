"""Streamlit page for Wing Loads (Step D6): AIRLOADS + WINGINER + NETLOADS merged.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Section 1 computes the wing spanwise lift distribution by Schrenk's method
(Reference 1 Ch 7): the additive distribution (untwisted wing at CL=1), the basic
distribution (from the spanwise twist), and their combination at a target CL.
Section 2 forms the net spanwise wing load = air load (section 1) − inertia
(WINGINER), giving the shear, bending moment and torsion along the 25% chord --
the headline structural deliverable. AIRLOADS is an independently registered calc
module (see ``sloads.workflow.FOLDED_MODULES``); this page is its shared nav
step with NETLOADS.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_shell.components import gate, page_header, stop_page, unit_number_input
from app_shell.limit_csv import wing_limit_csv, wing_limit_rows
from app_shell.widget_keys import widget_key
from sloads import (
    AeroInput,
    AeroSurfaceInput,
    ConcentratedWeight,
    WingLoadCase,
    WingMassInput,
    convert_results,
    si_scalar_label,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads import io as sloads_io
from sloads.derived_geometry import wing_plane
from sloads.export import sbeam_bridge as sb
from sloads.modules.airloads import run as airloads_run
from sloads.modules.airloads import schrenk_distribution
from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results, wing_load_rows
from sloads.modules.wing_inertia import resolve_wing_cases
from sloads.report import LoadChannel, module_text_report

project, system, U = page_header("wing_loads", title="Wing Loads — AIRLOADS + WINGINER + NETLOADS", banner=False)
st.caption(
    "Python/Streamlit port of AIRLOADS.BAS + TAU.BAS + WINGINER.BAS + NETLOADS.BAS "
    "(Hal C. McMaster). Spanwise c·cl lift distribution by Schrenk's method "
    "(additive + basic), then the net spanwise wing load = air load − inertia, "
    "giving the shear, bending moment and torsion along the 25% chord."
)


wing_geom = project.geometry.by_name("wing") if project.geometry else None
if wing_geom is None:
    gate(
        "No wing planform found. Define a `wing` surface on the **Geometry** "
        "page first — AIRLOADS reads the planform (chord polylines) from it.",
        "configuration_layout",
    )
    stop_page()

if project.is_concept:
    st.warning(
        "Concept category (C): the span-load distribution is a Schrenk "
        "**extrapolation** and is unverified above the FAR 23 calibration band."
    )

# --------------------------------------------------------------------------- #
# Section 1: Wing airloads (Schrenk) -- form + Apply, upserted by name into
# project.aero.surfaces (never a wholesale replace of the whole list, so a
# future htail/vtail aero entry from another module survives this page's Apply).
# --------------------------------------------------------------------------- #
st.header("Wing airloads (Schrenk)")
st.caption(
    "This is the wing's spanwise lift/twist/drag input, kept next to the "
    "per-strip distribution it drives. Airplane-less-tail cruise/flaps-down "
    "balance coefficients are entered on the Aerodynamic Data page (Airplane phase)."
)

existing_aero = project.aero.by_name("wing") if project.aero else None

with st.form("wing_airloads_form"):
    st.subheader("Wing aero inputs")
    section_slope = st.number_input(
        "Section lift-curve slope m₀ (per deg)", min_value=0.0,
        value=float(existing_aero.section_slope) if existing_aero else 0.0, format="%.4f",
        key=widget_key("wing_section_slope"))
    taper_ratio = st.number_input(
        "Taper ratio (tip chord / root chord)", min_value=0.0, max_value=1.0,
        value=float(existing_aero.taper_ratio) if existing_aero else 0.0, format="%.4f",
        key=widget_key("wing_taper_ratio"))
    tip_ratio = st.number_input(
        "Tip ratio (rounded-tip width / semi-span)", min_value=0.0, max_value=1.0,
        value=float(existing_aero.tip_ratio) if existing_aero else 0.0, format="%.3f",
        key=widget_key("wing_tip_ratio"))
    use_tau_override = st.checkbox(
        "Override TAU", value=existing_aero.tau is not None if existing_aero else False,
        key=widget_key("wing_use_tau"))
    tau_override_raw = st.number_input(
        "TAU", value=float(existing_aero.tau) if existing_aero and existing_aero.tau is not None else 0.0,
        key=widget_key("wing_tau"))
    target_cl = st.number_input(
        "Target wing CL", value=float(existing_aero.target_cl) if existing_aero else 0.0,
        format="%.3f", key=widget_key("wing_target_cl"))

    st.subheader("Spanwise twist")
    st.caption(f"Zero-lift angle (deg) at each butt line Y ({U['length']}, inboard → outboard). "
              "Empty = untwisted.")
    default_twist = existing_aero.twist if existing_aero and existing_aero.twist else []
    twist_display = [(to_display(y, "length", system), a) for y, a in default_twist] or [[0.0, 0.0]]
    twist_cols = {"Y": st.column_config.NumberColumn(f"Y ({U['length']})"),
                 "Angle": st.column_config.NumberColumn("Angle (deg)")}
    twist_df = st.data_editor(
        pd.DataFrame(twist_display, columns=["Y", "Angle"]), column_config=twist_cols,
        num_rows="dynamic", hide_index=True, width="stretch", key=widget_key(f"twist_{system.value}"))

    aero_applied = st.form_submit_button("Apply", type="primary")

if aero_applied:
    twist = [(to_imperial_scalar(float(r["Y"]), "length", system), float(r["Angle"]))
             for _, r in twist_df.iterrows() if pd.notna(r["Y"]) and pd.notna(r["Angle"])]
    # Drop a lone all-zero placeholder row so an untwisted wing has an empty table.
    if twist == [(0.0, 0.0)]:
        twist = []
    tau_override = tau_override_raw if use_tau_override else None
    # Built from the *existing* surface, not from scratch (#36): this form renders
    # seven of AeroSurfaceInput's fields, and a fresh construction reset the other
    # four to their defaults -- wiping the profile-drag and section-Cm polars, the
    # design Mach and the sweep, none of which any widget in the GUI can restore.
    base = existing_aero if existing_aero is not None else AeroSurfaceInput(name="wing")
    aero_surf = replace(
        base, name="wing", section_slope=section_slope, taper_ratio=taper_ratio,
        tip_ratio=tip_ratio, tau=tau_override, twist=twist, target_cl=target_cl)
    other_surfaces = [s for s in (project.aero.surfaces if project.aero else []) if s.name != "wing"]
    project.aero = AeroInput(surfaces=[*other_surfaces, aero_surf])
    st.session_state["project"] = project
    st.success("Wing aero inputs applied.")
    existing_aero = project.aero.by_name("wing")

if existing_aero is None:
    st.info("No wing aero inputs defined yet — fill in the form above and Apply.")
    stop_page()

try:
    table = schrenk_distribution(wing_geom, existing_aero)
    air_results = airloads_run(project).conditions
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute airloads: {exc}")
    stop_page()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Wing CLα slope M", f"{table.m_wing:.4f}", help="incl. AR & TAU (per deg)")
col2.metric("TAU", f"{table.tau:.4f}")
col3.metric("Target CL", f"{table.target_cl:.3f}")
col4.metric("Recovered CL", f"{table.recovered_cl:.4f}", help="∫c·cl dy / (S/2) — closure check")

_ye_disp = [to_si_scalar(v, "in", system) for v in table.ye]
fig = go.Figure()
fig.add_trace(go.Scatter(x=_ye_disp, y=[to_si_scalar(v, "in", system) for v in table.ccl_additive],
                         name="additive (×CL)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=_ye_disp, y=[to_si_scalar(v, "in", system) for v in table.ccl_basic],
                         name="basic (twist)", mode="lines+markers"))
fig.add_trace(go.Scatter(x=_ye_disp, y=[to_si_scalar(v, "in", system) for v in table.ccl_total],
                         name=f"total @ CL={table.target_cl:g}",
                         mode="lines+markers", line={"width": 3}))
fig.update_layout(
    title="Spanwise span load c·cl", xaxis_title=f"Butt line Y ({si_scalar_label('in', system)})",
    yaxis_title=f"c·cl ({si_scalar_label('in', system)})", legend={"orientation": "h"}, height=420)
st.plotly_chart(fig, width="stretch")

st.subheader("Per-strip distribution")
_len_lbl = si_scalar_label("in", system)
# c·cl (chord x dimensionless section cl) carries the same length dimension as
# chord itself, so it converts with the "in" factor; cl_total is dimensionless
# and is never converted.
st.dataframe(pd.DataFrame({
    f"Y ({_len_lbl})": [to_si_scalar(v, "in", system) for v in table.ye],
    f"chord ({_len_lbl})": [to_si_scalar(v, "in", system) for v in table.chord],
    f"c·cl additive ({_len_lbl})": [to_si_scalar(v, "in", system) for v in table.ccl_additive],
    f"c·cl basic ({_len_lbl})": [to_si_scalar(v, "in", system) for v in table.ccl_basic],
    f"c·cl total ({_len_lbl})": [to_si_scalar(v, "in", system) for v in table.ccl_total],
    "cl total": table.cl_total,
}), hide_index=True, width="stretch")

st.download_button(
    "Download airloads (CSV)",
    sloads_io.load_cases_csv(air_results, system=system, channel=LoadChannel.LIMIT),
    file_name="airloads.csv", mime="text/csv")
st.download_button(
    "Download airloads (text)", module_text_report("Spanwise wing airloads",
                       convert_results(air_results, system), channel=LoadChannel.LIMIT),
    file_name="airloads.txt", mime="text/plain")

# --------------------------------------------------------------------------- #
# Section 2: Net wing loads (WINGINER + NETLOADS) -- form + Apply. This page is
# WingMassInput's sole editor, so a full-field reconstruction on Apply is correct
# (every field the dataclass has is exposed below), same pattern as
# aero_coefficients.py's Project.aero_coeffs.
# --------------------------------------------------------------------------- #
st.divider()
st.header("Net wing loads")

wm = project.wing_mass or WingMassInput()

# The wing reference-plane waterline and dihedral are single-sourced from the
# parametric wing on the Geometry page (WINGINER reads them from there); this page
# shows them read-only. Note 33: they are no longer fields on ``WingMassInput``, so
# there is nothing to fall back to and nothing to write back — ``wing_plane`` is the
# one resolver, and the display and the calc cannot disagree.
_wrp_derived, _dihedral_derived = wing_plane(project, wm.surface or "wing")

st.caption(
    "**WL of wing ref plane** and **dihedral** are single-sourced from the "
    "**Geometry** page (Step M2-6); edit them there."
)
_gc1, _gc2 = st.columns(2)
_gc1.metric(f"WL of wing ref plane ({U['length']})",
            f"{to_display(_wrp_derived, 'length', system):.3f}")
_gc2.metric("Dihedral (deg)", f"{_dihedral_derived:.3f}")

# Step M4-2 decision 2: SELECT already searched the V-n matrix for the governing
# wing conditions, so re-typing them here is a second, silently-divergent entry of
# the same cases. The button materialises SELECT's list into the editable table --
# visibly, so the engineer can still override any of it -- rather than deriving
# behind the page's back; leaving the table empty falls back to the same list at
# run time (wing_inertia.resolve_wing_cases).
_from_select = resolve_wing_cases(project, WingMassInput())
if _from_select:
    _names = ", ".join(c.name for c in _from_select)
    _cols = st.columns([1, 3])
    if _cols[0].button("Pull cases from SELECT", key="pull_wing_cases"):
        project.wing_mass = WingMassInput(
            panel_weight_lb=wm.panel_weight_lb, tip_root_density_ratio=wm.tip_root_density_ratio,
            inboard_rib_y=wm.inboard_rib_y, surface=wm.surface or "wing",
            concentrated=list(wm.concentrated), cases=_from_select)
        st.session_state["project"] = project
        st.rerun()
    _cols[1].caption(
        f"SELECT's critical wing conditions: **{_names}**. Nz/Nx/CL/V fill from each "
        "condition's V-n point; an accelerated-roll case still needs its unbalanced "
        "rolling moment entered by hand."
    )

with st.form("net_wing_loads_form"):
    st.subheader(f"Wing mass distribution ({U['weight']} / {U['length']})")
    panel = unit_number_input(
        "Outboard panel weight, one side", float(wm.panel_weight_lb),
        kind="weight", key="wing_panel_weight", min_value=0.0)
    dr = st.number_input("Tip/root area-density ratio", min_value=0.0, max_value=1.0,
                         value=float(wm.tip_root_density_ratio), format="%.3f",
                         key=widget_key("wing_density_ratio"))
    rib = unit_number_input(
        "Inboard rib butt line", float(wm.inboard_rib_y),
        kind="length", key="wing_inboard_rib")

    st.subheader(f"Concentrated wing weights ({U['weight']} / {U['length']})")
    cw_display = [
        [c.name, to_display(c.weight_lb, "weight", system), to_display(c.x, "length", system),
         to_display(c.y, "length", system), to_display(c.z, "length", system)]
        for c in wm.concentrated
    ] or [["", 0.0, 0.0, 0.0, 0.0]]
    cw_cols = {
        "weight_lb": st.column_config.NumberColumn(f"weight ({U['weight']})"),
        "x": st.column_config.NumberColumn(f"x ({U['length']})"),
        "y": st.column_config.NumberColumn(f"y ({U['length']})"),
        "z": st.column_config.NumberColumn(f"z ({U['length']})"),
    }
    cw_df = st.data_editor(
        pd.DataFrame(cw_display, columns=["name", "weight_lb", "x", "y", "z"]),
        column_config=cw_cols, num_rows="dynamic", hide_index=True,
        width="stretch", key=widget_key(f"cw_{system.value}"))

    st.subheader("Critical load cases")
    st.caption("Nz / Nx are the inertia load factors (negative of the air-load factor); "
               "CL / V are the air-load condition. Reference a V-n case to auto-fill from FLTLOADS. "
               "**0 rows = the SELECT governing set** is used at run time; typed rows "
               "**replace that set entirely** — adding one case drops every derived "
               "condition from WINGINER/NETLOADS and the export (C210-30).")
    case_default = pd.DataFrame(
        [[c.name, c.case, c.nz, c.nx, c.unbal_moment, c.cl, c.v_eas_kt] for c in wm.cases]
        or [["", None, 0.0, 0.0, 0.0, 0.0, 0.0]],
        columns=["name", "vn_case", "nz", "nx", "unbal_moment", "cl", "v_eas_kt"],
    )
    case_df = st.data_editor(case_default, num_rows="dynamic", hide_index=True, width="stretch",
                             key=widget_key("wing_case_editor"))

    mass_applied = st.form_submit_button("Apply", type="primary")


def _opt(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


if mass_applied:
    concentrated = [
        ConcentratedWeight(
            name=str(r["name"]), weight_lb=to_imperial_scalar(float(r["weight_lb"]), "weight", system),
            x=to_imperial_scalar(float(r["x"]), "length", system),
            y=to_imperial_scalar(float(r["y"]), "length", system),
            z=to_imperial_scalar(float(r["z"]), "length", system))
        for _, r in cw_df.iterrows()
        if pd.notna(r["weight_lb"]) and float(r["weight_lb"]) != 0.0
    ]
    cases = [
        WingLoadCase(name=str(r["name"]), case=_opt(r["vn_case"]) and int(r["vn_case"]),
                     nz=_opt(r["nz"]), nx=_opt(r["nx"]),
                     unbal_moment=float(r["unbal_moment"]) if pd.notna(r["unbal_moment"]) else 0.0,
                     cl=_opt(r["cl"]), v_eas_kt=_opt(r["v_eas_kt"]))
        for _, r in case_df.iterrows()
        if pd.notna(r["name"]) and str(r["name"]).strip()
    ]
    project.wing_mass = WingMassInput(
        panel_weight_lb=panel,
        tip_root_density_ratio=dr, inboard_rib_y=rib,
        surface="wing", concentrated=concentrated, cases=cases)
    st.session_state["project"] = project
    st.success("Wing mass distribution applied.")
    wm = project.wing_mass

if not resolve_wing_cases(project, wm):
    st.info("No wing load cases defined yet — fill in the form above and Apply, "
            "or run SELECT and pull its critical conditions.")
    stop_page()

try:
    loads = build_net_loads(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute net wing loads: {exc}")
    stop_page()

if project.is_concept:
    st.warning("Concept category (C): net loads are an **unverified extrapolation** "
               "above the FAR 23 calibration band.")

st.caption(
    "Loads shown are **LIMIT** (oracle-traceable), and so is every load this "
    "tool delivers: the **Review/Export** pages state the 14 CFR 23.303 factor "
    "per case and apply it nowhere. Torsion Myy on this page is about the **25% chord** (the axis the "
    "original suite computes about, so these numbers cross-check against the "
    "manual); the Loads-Plots/Export deliverables state it about the wing's "
    "**loads reference axis** (LRA, set on the Geometry page)."
)

case_names = [r.case for r in loads.wing_net]
sel = st.selectbox("Show case", case_names, key=widget_key("wing_show_case"))
air = next(r for r in loads.wing_air if r.case == sel)
inertia = next(r for r in loads.wing_inertia if r.case == sel)
net = next(r for r in loads.wing_net if r.case == sel)

c1, c2, c3 = st.columns(3)
c1.metric(f"Root shear Sz ({si_scalar_label('lbf', system)}, LIMIT)",
          f"{to_si_scalar(net.stations[0].sz, 'lbf', system):,.0f}")
c2.metric(f"Root bending Mxx ({si_scalar_label('lb-in', system)}, LIMIT)",
          f"{to_si_scalar(net.stations[0].mxx, 'lb-in', system):,.0f}")
c3.metric(f"Root torsion Myy, 25% chord ({si_scalar_label('lb-in', system)}, LIMIT)",
          f"{to_si_scalar(net.stations[0].myy, 'lb-in', system):,.0f}")

for title, attr, unit_key in [("Shear Sz", "sz", "lbf"), ("Bending Mxx", "mxx", "lb-in"),
                              ("Torsion Myy about 25% chord", "myy", "lb-in")]:
    unit = f"{si_scalar_label(unit_key, system)}, LIMIT"
    fig = go.Figure()
    for label, r in [("air", air), ("inertia", inertia), ("net", net)]:
        fig.add_trace(go.Scatter(
            x=[to_si_scalar(s.y, "in", system) for s in r.stations],
            y=[to_si_scalar(getattr(s, attr), unit_key, system) for s in r.stations],
            name=label, mode="lines+markers", line={"width": 3 if label == "net" else 1}))
    fig.update_layout(title=f"{title} — {sel}",
                      xaxis_title=f"Butt line Y ({si_scalar_label('in', system)})",
                      yaxis_title=f"{title} ({unit})", legend={"orientation": "h"}, height=320)
    st.plotly_chart(fig, width="stretch")

st.subheader("Net load station table (LIMIT)")
st.dataframe(pd.DataFrame(wing_limit_rows(wing_load_rows([net]), system)),
             hide_index=True, width="stretch")

# Three downloads, named by *channel* (#192). Before note 49 the split was by
# basis -- LIMIT table vs ULTIMATE bridge -- but OR-116 made every one of them
# LIMIT, so a basis marker no longer tells them apart and the labels name what
# does differ: the analysis table (this page's converted, unit-suffixed rows,
# L-8i -- ``limit_csv`` owns both) vs the sbeam bridge, the same content family
# the Export page ships. The ``*_ULT.csv`` file names are stale and stay so
# until OR-81 renames them in 0.8.3; a truthful label over a stale name beats
# the reverse. The applied set is the structures deliverable and is stated about
# the wing's loads reference axis, so it goes through ``loads_ref_axis_results``
# -- the transfer the Export page's Project argument does for itself.
_lra_net = loads_ref_axis_results(project, loads.wing_net)
_dl = st.columns(3)
_dl[0].download_button("Download net wing loads — analysis table (CSV)",
                       wing_limit_csv(wing_load_rows(loads.wing_net), system),
                       file_name="net_wing_loads_LIMIT.csv", mime="text/csv")
_dl[1].download_button("Download net wing loads — sbeam bridge (CSV)",
                       sb.span_load_csv(loads.wing_net, system=system),
                       file_name="net_wing_loads_ULT.csv", mime="text/csv")
_dl[2].download_button("Download applied load set — sbeam bridge (CSV)",
                       sb.applied_load_csv(_lra_net, system=system),
                       file_name="wing_applied_loads_ULT.csv", mime="text/csv")
st.caption(
    "All three files are **LIMIT**; each row states the 14 CFR 23.303 factor "
    "it does not apply. The analysis table carries a `Basis` column and matches "
    "the table above; its torsion is about the 25% chord and it carries no "
    "concentrated-mass row. The two sbeam files are the deck channel. "
    "**Applied load set** is the file a structures model is built from: one row "
    "per strip and one per concentrated wing mass, each at its own point, as "
    "all six body-axis components `Fx Fy Fz Mx My Mz` — nothing in it is a "
    "running total. `My` is the section moment that is *not* already a force "
    "acting through an arm; `Fy`, `Mx` and `Mz` are zero throughout and are "
    "printed rather than omitted, so a zero cannot be read as a missing "
    "column. It is the oracle report's Appendix B.1, and its torsion is about "
    "the **loads reference axis**. The span-load file carries the cumulative "
    "distributions beside it and is also on the **Export** page; each file "
    "states its own moment convention in its header comment."
)
