"""Streamlit page for flap loads (FLAPLOAD, Ch 17).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Computes the critical flaps-extended flap load (FAR 23.345 / 23.457) over the
four-condition envelope, plus the FAR 23.457(b) slipstream and FAR 23.345(c)(1)
head-on-gust amplifications. Stall speeds / VF / weight come from STRSPEED; wing
area from the geometry; propeller power/diameter from the engine.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_shell import optional_slice
from app_shell.components import gate, page_header, stop_page, unit_number_input
from app_shell.widget_keys import widget_key
from sloads import (
    FlapLoadsInput,
    Project,
    UnitSystem,
    convert_results,
    to_si_scalar,
)
from sloads.export import sbeam_bridge as sb
from sloads.modules.flap import build_flap, run

# The shared header, so this page shows the entry errors tagged for it in both
# GUIs (#82 renderer, #83 slipstream warning) rather than only in the oracle GUI,
# which reaches every page through it. ``banner=False`` keeps the page's own
# concept notice below as the one applicability statement -- nothing else about
# the opening changes. It also carries D-16: ``active_system()`` inside the
# header is the single read of the unit selection.
ctx = page_header(
    "flap_loads",
    title="Flap Loads — FLAPLOAD",
    caption=("Python/Streamlit port of FLAPLOAD.BAS (Reference 1 Ch 17): the critical "
             "flaps-extended load (Abbott & von Doenhoff Fig 98 flap-lift build-up), with "
             "the propeller-slipstream and head-on-gust amplifications."),
    banner=False,
)
project: Project = ctx.project
system: UnitSystem = ctx.system
U = ctx.U  # {"area_sqft","length",...} -> unit string

if project.speeds is None:
    gate("Define the **Structural Speeds** (VS/VSF/VF, weight) first.", "structural_speeds")
    stop_page()

# Captured before the form mutates ``inp`` in place: ``store`` needs to
# know whether the project *had* this Optional slice (#145).
_existing_slice = project.flap_loads
inp = project.flap_loads or FlapLoadsInput()
with st.form("flap_loads_form"):
    st.subheader("Flap geometry & deflection")
    c1, c2 = st.columns(2)
    flap_deflection_deg = c1.number_input(
        "Max flap deflection (deg)", min_value=0.0, value=float(inp.flap_deflection_deg), step=1.0,
        key=widget_key("flap_deflection"))
    flap_chord_ratio = c2.number_input(
        "Flap chord / wing chord, E", min_value=0.0, value=float(inp.flap_chord_ratio), step=0.01,
        key=widget_key("flap_chord_ratio"))
    flap_area_one_side_sqft = unit_number_input(
        "Flap area on one side, SF", float(inp.flap_area_one_side_sqft),
        kind="area_sqft", key="flap_area", min_value=0.0, step=0.1, container=c1)
    gust_load_factor = c2.number_input(
        "Flaps-extended gust load factor, NG", min_value=0.0,
        value=float(inp.gust_load_factor), step=0.1,
        key=widget_key("flap_gust_ng"))
    # Both feed the 23.457(b) slipstream band only, and the term itself needs the
    # engine record's power and propeller diameter -- so say where the rest of the
    # slipstream comes from, right where these two are entered (#83).
    _SLIP_HELP = ("Slipstream band geometry (FAR 23.457(b)). The band is placed by "
                  "these two, but the slipstream itself is driven by the **engine "
                  "record** — takeoff power and propeller diameter, entered on the "
                  "Engine Mount Loads page. With no such engine the term is skipped "
                  "and these are read for nothing.")
    nacelle_frontal_area_sqft = unit_number_input(
        "Nacelle/fuselage frontal area, AF", float(inp.nacelle_frontal_area_sqft),
        kind="area_sqft", key="flap_nacelle_area", min_value=0.0, step=0.1, container=c1,
        help=_SLIP_HELP)
    engine_butt_line_in = unit_number_input(
        "Engine butt line, BLPROP (0 = fuselage)", float(inp.engine_butt_line_in),
        kind="length", key="flap_engine_bl", step=1.0, container=c2,
        help=_SLIP_HELP)
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.flap_deflection_deg = flap_deflection_deg
    inp.flap_chord_ratio = flap_chord_ratio
    inp.flap_area_one_side_sqft = flap_area_one_side_sqft
    inp.gust_load_factor = gust_load_factor
    inp.nacelle_frontal_area_sqft = nacelle_frontal_area_sqft
    inp.engine_butt_line_in = engine_butt_line_in
    project.flap_loads = optional_slice.store(inp, _existing_slice)
    st.session_state["project"] = project
    st.success("Flap geometry applied.")

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    mod = run(project)
    results = build_flap(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute flap loads: {exc}")
    stop_page()

display_conditions = convert_results(mod.conditions, system)
# Flattened across **every** condition: since #85 the slipstream is its own
# delivered case and so its own ConditionResult, and this dict is keyed by
# ``LoadValue.key`` -- reading only ``[0]`` (and then testing membership with the
# *label* "Slipstream factor") is what kept the slipstream block below dark on
# this page since it was written.
vals = {v.key: v.value for c in display_conditions for v in c.values}
force_u = "N" if system == UnitSystem.SI else "lb"
pressure_u = "kPa" if system == UnitSystem.SI else "lb/in²"
st.caption(
    "On-screen loads are **LIMIT** (oracle values, traceable to the manual). "
    "Every load below is **LIMIT** too: the downloads and the "
    "**Review/Export** pages state the 14 CFR 23.303 factor per case and "
    "apply it nowhere — apply it in the sizing analysis."
)
m1, m2, m3 = st.columns(3)
m1.metric(f"Critical flap load ({force_u}, LIMIT)", f"{vals['critical_flap_load_23_345_a']:,.0f}")
m2.metric(f"LE pressure ({pressure_u}, LIMIT)",
          f"{to_si_scalar(vals['le_pressure_te_half'], 'psi', system):.3f}")
m3.metric(f"Combined w/ gust ({force_u}, LIMIT)", f"{vals['flap_load_combined_w_gust']:,.0f}")

st.subheader("Flaps-extended envelope")
# (row heading, LoadValue key suffix) -- the heading is this page's wording,
# the suffix is the calc's key for the same envelope point (M4-9).
conditions = [("1G stall", "1g_stall"), ("2G stall", "2g_stall"),
              ("2G at VF", "2g_at_vf"), ("gust at VF", "gust_at_vf")]
st.write(pd.DataFrame([
    {"Condition": heading,
     "Flap CL": round(vals[f"flap_cl_{suffix}"], 4),
     f"Flap load ({force_u}, LIMIT)": round(vals[f"flap_load_{suffix}"], 1)}
    for heading, suffix in conditions
]))

if "slipstream_factor" in vals:
    st.subheader("Slipstream (FAR 23.457(b))")
    s1, s2, s3 = st.columns(3)
    s1.metric("Slipstream factor", f"{vals['slipstream_factor']:.3f}")
    s2.metric("Slipstream V at flap (kt)", f"{vals['slipstream_velocity_at_flap']:.1f}")
    length_u = "mm" if system == UnitSystem.SI else "in"
    s3.metric(f"Slipstream BL band ({length_u})",
              f"{vals['slipstream_inboard_bl']:.1f} … {vals['slipstream_outboard_bl']:.1f}")
    st.metric(f"Flap load in slipstream ({force_u}, LIMIT)",
              f"{vals['flap_load_in_slipstream']:,.0f}")
    st.caption(
        "Delivered as a **case beside** the gust-combined one (not multiplied "
        "with it): the head-on gust and full takeoff power at VF are independent "
        "worst cases, and the governing flap load is the larger of the two. The "
        "factor is applied over the whole flap — the exported case carries chord "
        "fractions and no span, so a partial-span distribution has nowhere to "
        "live; that is conservative for the flap and its attachments."
    )

st.download_button("Download flap loads (CSV)", sb.control_surface_csv(results, system=system),
                   file_name="flap_loads.csv", mime="text/csv")
st.download_button("Download FORCE cards (sbeam)",
                   sb.control_surface_force_moment_cards(results, system=system),
                   file_name="flap_loads.bdf", mime="text/plain")
