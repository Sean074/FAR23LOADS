"""Streamlit page for Wing Loads (Step D6): AIRLOADS + WINGINER + NETLOADS merged.

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Section 1 computes the wing spanwise lift distribution by Schrenk's method
(Reference 1 Ch 7): the additive distribution (untwisted wing at CL=1), the basic
distribution (from the spanwise twist), and their combination at a target CL.
Section 2 forms the net spanwise wing load = air load (section 1) − inertia
(WINGINER), giving the shear, bending moment and torsion along the 25% chord --
the headline structural deliverable. AIRLOADS is an independently registered calc
module (see ``farloads.workflow.FOLDED_MODULES``); this page is its shared nav
step with NETLOADS.
"""

from __future__ import annotations

import csv
import io as _io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import (
    AeroInput,
    AeroSurfaceInput,
    ConcentratedWeight,
    Project,
    UnitSystem,
    WingLoadCase,
    WingMassInput,
    si_scalar_label,
    to_si_scalar,
)
from farloads import io as farloads_io
from farloads.modules.airloads import run as airloads_run
from farloads.modules.airloads import schrenk_distribution
from farloads.modules.net_loads import build_net_loads, wing_load_rows
from farloads.report import module_text_report


def _convert_wing_rows(rows, system: UnitSystem):
    """Display-only copy of ``wing_load_rows`` output converted to ``system``.

    Never mutates the source rows/objects -- CSV/export paths keep using the
    original Imperial ``rows``/``results``. Mxx/Myy/Mzz are all "lb-in" per
    ``net_loads.run`` (see its ``LoadValue`` entries), matching WINGINER/NETLOADS.
    """
    return [
        {
            **r,
            "X": round(to_si_scalar(float(r["X"]), "in", system), 3),
            "Y": round(to_si_scalar(float(r["Y"]), "in", system), 3),
            "Z": round(to_si_scalar(float(r["Z"]), "in", system), 3),
            "Fx": round(to_si_scalar(float(r["Fx"]), "lbf", system), 1),
            "Fz": round(to_si_scalar(float(r["Fz"]), "lbf", system), 1),
            "Sx": round(to_si_scalar(float(r["Sx"]), "lbf", system), 1),
            "Sz": round(to_si_scalar(float(r["Sz"]), "lbf", system), 1),
            "Mxx": round(to_si_scalar(float(r["Mxx"]), "lb-in", system), 0),
            "Myy": round(to_si_scalar(float(r["Myy"]), "lb-in", system), 0),
            "Mzz": round(to_si_scalar(float(r["Mzz"]), "lb-in", system), 0),
        }
        for r in rows
    ]

st.title("Wing Loads — AIRLOADS + WINGINER + NETLOADS")
st.caption(
    "Python/Streamlit port of AIRLOADS.BAS + TAU.BAS + WINGINER.BAS + NETLOADS.BAS "
    "(Hal C. McMaster). Spanwise c·cl lift distribution by Schrenk's method "
    "(additive + basic), then the net spanwise wing load = air load − inertia, "
    "giving the shear, bending moment and torsion along the 25% chord."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)

wing_geom = project.geometry.by_name("wing") if project.geometry else None
if wing_geom is None:
    st.warning(
        "No wing planform found. Define a `wing` surface on the **Wing Geometry** "
        "page first — AIRLOADS reads the planform (chord polylines) from it."
    )
    st.stop()

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
        value=float(existing_aero.section_slope) if existing_aero else 0.0, format="%.4f")
    taper_ratio = st.number_input(
        "Taper ratio (tip chord / root chord)", min_value=0.0, max_value=1.0,
        value=float(existing_aero.taper_ratio) if existing_aero else 0.0, format="%.4f")
    tip_ratio = st.number_input(
        "Tip ratio (rounded-tip width / semi-span)", min_value=0.0, max_value=1.0,
        value=float(existing_aero.tip_ratio) if existing_aero else 0.0, format="%.3f")
    use_tau_override = st.checkbox(
        "Override TAU", value=existing_aero.tau is not None if existing_aero else False)
    tau_override_raw = st.number_input(
        "TAU", value=float(existing_aero.tau) if existing_aero and existing_aero.tau is not None else 0.0)
    target_cl = st.number_input(
        "Target wing CL", value=float(existing_aero.target_cl) if existing_aero else 0.0,
        format="%.3f")

    st.subheader("Spanwise twist")
    st.caption("Zero-lift angle (deg) at each butt line Y (inboard → outboard). Empty = untwisted.")
    default_twist = existing_aero.twist if existing_aero and existing_aero.twist else []
    twist_df = st.data_editor(
        pd.DataFrame(default_twist or [[0.0, 0.0]], columns=["Y (in)", "Angle (deg)"]),
        num_rows="dynamic", hide_index=True, use_container_width=True)

    aero_applied = st.form_submit_button("Apply", type="primary")

if aero_applied:
    twist = [(float(r["Y (in)"]), float(r["Angle (deg)"])) for _, r in twist_df.iterrows()
             if pd.notna(r["Y (in)"]) and pd.notna(r["Angle (deg)"])]
    # Drop a lone all-zero placeholder row so an untwisted wing has an empty table.
    if twist == [(0.0, 0.0)]:
        twist = []
    tau_override = tau_override_raw if use_tau_override else None
    aero_surf = AeroSurfaceInput(
        name="wing", section_slope=section_slope, taper_ratio=taper_ratio,
        tip_ratio=tip_ratio, tau=tau_override, twist=twist, target_cl=target_cl)
    other_surfaces = [s for s in (project.aero.surfaces if project.aero else []) if s.name != "wing"]
    project.aero = AeroInput(surfaces=other_surfaces + [aero_surf])
    st.session_state["project"] = project
    st.success("Wing aero inputs applied.")
    existing_aero = project.aero.by_name("wing")

if existing_aero is None:
    st.info("No wing aero inputs defined yet — fill in the form above and Apply.")
    st.stop()

try:
    table = schrenk_distribution(wing_geom, existing_aero)
    air_results = airloads_run(project).conditions
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute airloads: {exc}")
    st.stop()

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
                         mode="lines+markers", line=dict(width=3)))
fig.update_layout(
    title="Spanwise span load c·cl", xaxis_title=f"Butt line Y ({si_scalar_label('in', system)})",
    yaxis_title=f"c·cl ({si_scalar_label('in', system)})", legend=dict(orientation="h"), height=420)
st.plotly_chart(fig, use_container_width=True)

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
}), hide_index=True, use_container_width=True)

st.download_button(
    "Download airloads (CSV)", farloads_io.load_cases_csv(air_results),
    file_name="airloads.csv", mime="text/csv")
st.download_button(
    "Download airloads (text)", module_text_report("Spanwise wing airloads", air_results),
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

with st.form("net_wing_loads_form"):
    st.subheader("Wing mass distribution")
    panel = st.number_input("Outboard panel weight, one side (lb)", min_value=0.0,
                            value=float(wm.panel_weight_lb))
    dr = st.number_input("Tip/root area-density ratio", min_value=0.0, max_value=1.0,
                         value=float(wm.tip_root_density_ratio), format="%.3f")
    rib = st.number_input("Inboard rib butt line (in)", value=float(wm.inboard_rib_y))
    wrp = st.number_input("WL of wing ref plane at centreline (in)", value=float(wm.wrp_waterline))
    dihedral = st.number_input("Dihedral (deg)", value=float(wm.dihedral_deg))

    st.subheader("Concentrated wing weights")
    cw_default = pd.DataFrame(
        [[c.name, c.weight_lb, c.x, c.y, c.z] for c in wm.concentrated]
        or [["", 0.0, 0.0, 0.0, 0.0]],
        columns=["name", "weight_lb", "x", "y", "z"],
    )
    cw_df = st.data_editor(cw_default, num_rows="dynamic", hide_index=True, use_container_width=True)

    st.subheader("Critical load cases")
    st.caption("Nz / Nx are the inertia load factors (negative of the air-load factor); "
               "CL / V are the air-load condition. Reference a V-n case to auto-fill from FLTLOADS.")
    case_default = pd.DataFrame(
        [[c.name, c.case, c.nz, c.nx, c.unbal_moment, c.cl, c.v_eas_kt] for c in wm.cases]
        or [["", None, 0.0, 0.0, 0.0, 0.0, 0.0]],
        columns=["name", "vn_case", "nz", "nx", "unbal_moment", "cl", "v_eas_kt"],
    )
    case_df = st.data_editor(case_default, num_rows="dynamic", hide_index=True, use_container_width=True)

    mass_applied = st.form_submit_button("Apply", type="primary")


def _opt(v):
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


if mass_applied:
    concentrated = [
        ConcentratedWeight(name=str(r["name"]), weight_lb=float(r["weight_lb"]),
                           x=float(r["x"]), y=float(r["y"]), z=float(r["z"]))
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
        panel_weight_lb=panel, tip_root_density_ratio=dr, inboard_rib_y=rib, wrp_waterline=wrp,
        dihedral_deg=dihedral, surface="wing", concentrated=concentrated, cases=cases)
    st.session_state["project"] = project
    st.success("Wing mass distribution applied.")
    wm = project.wing_mass

if not wm.cases:
    st.info("No wing load cases defined yet — fill in the form above and Apply.")
    st.stop()

try:
    loads = build_net_loads(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute net wing loads: {exc}")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): net loads are an **unverified extrapolation** "
               "above the FAR 23 calibration band.")

st.caption(
    "Loads shown are **LIMIT** (oracle-traceable). The deliverable **ULTIMATE** "
    "loads (= limit × safety factor, 14 CFR 23.303) come from the **Review/Export** "
    "pages."
)

case_names = [r.case for r in loads.wing_net]
sel = st.selectbox("Show case", case_names)
air = next(r for r in loads.wing_air if r.case == sel)
inertia = next(r for r in loads.wing_inertia if r.case == sel)
net = next(r for r in loads.wing_net if r.case == sel)

c1, c2, c3 = st.columns(3)
c1.metric(f"Root shear Sz ({si_scalar_label('lbf', system)}, LIMIT)",
          f"{to_si_scalar(net.stations[0].sz, 'lbf', system):,.0f}")
c2.metric(f"Root bending Mxx ({si_scalar_label('lb-in', system)}, LIMIT)",
          f"{to_si_scalar(net.stations[0].mxx, 'lb-in', system):,.0f}")
c3.metric(f"Root torsion Myy ({si_scalar_label('lb-in', system)}, LIMIT)",
          f"{to_si_scalar(net.stations[0].myy, 'lb-in', system):,.0f}")

for title, attr, unit_key in [("Shear Sz", "sz", "lbf"), ("Bending Mxx", "mxx", "lb-in"),
                              ("Torsion Myy", "myy", "lb-in")]:
    unit = f"{si_scalar_label(unit_key, system)}, LIMIT"
    fig = go.Figure()
    for label, r in [("air", air), ("inertia", inertia), ("net", net)]:
        fig.add_trace(go.Scatter(
            x=[to_si_scalar(s.y, "in", system) for s in r.stations],
            y=[to_si_scalar(getattr(s, attr), unit_key, system) for s in r.stations],
            name=label, mode="lines+markers", line=dict(width=3 if label == "net" else 1)))
    fig.update_layout(title=f"{title} — {sel}",
                      xaxis_title=f"Butt line Y ({si_scalar_label('in', system)})",
                      yaxis_title=f"{title} ({unit})", legend=dict(orientation="h"), height=320)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Net load station table (LIMIT)")
st.dataframe(pd.DataFrame(_convert_wing_rows(wing_load_rows([net]), system)),
             hide_index=True, use_container_width=True)

buf = _io.StringIO()
rows = wing_load_rows(loads.wing_net)
writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
writer.writeheader()
writer.writerows(rows)
st.download_button("Download net wing loads (CSV)", buf.getvalue(),
                   file_name="net_wing_loads.csv", mime="text/csv")
