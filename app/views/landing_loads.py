"""Streamlit page for landing / ground loads (LGFACTOR + LANDLOAD, Ch 20).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Estimates the landing load factor (LGFACTOR, FAR 23.473(d)-(g)) from the drop-test
work-energy balance, then computes the tricycle-gear reaction loads for the level,
tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel ground
conditions (LANDLOAD, FAR 23.473-23.499). Reads the per-CG weight & CG from
Project.mass (WTONECG) unless overridden here. Tricycle gear only (UG Table 2.1).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import (
    CgCase,
    LandingInput,
    Project,
    UnitSystem,
    io,
    labels_for,
    si_scalar_label,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from farloads.derived_geometry import wing_reference
from farloads.modules.landing import build_landing, run
from farloads.validation import wtenv_cg_limits


_CG_NAMES = ("aft max landing", "fwd max landing", "fwd light")


def _seed_cg_rows(project: Project, inp: LandingInput, system: UnitSystem) -> list:
    """Three display-unit CG rows for the editor (M2R-5).

    Existing ``landing.cg_cases`` when present (edit what's there); otherwise a
    best-effort WTENV seed -- the fwd-most / aft-most structural CG stations
    (``validation.wtenv_cg_limits``) with the gross / fwd-regardless weights and the
    itemized-loading waterline -- so the engineer confirms/adjusts rather than typing
    JSON. Falls back to labeled zero rows when no WTENV envelope is present. The
    fwd/aft station split is a seed only: WTENV cannot distinguish it per loading."""
    if len(inp.cg_cases) == 3:
        src = list(inp.cg_cases)
    else:
        env = project.weight.envelope if project.weight is not None else None
        gross = inp.max_landing_weight_lb or (env.gross_weight if env else 0.0)
        light = (env.fwd_regardless_weight if env and env.fwd_regardless_weight
                 else 0.0) or gross
        zbar = (project.mass.cases[0].cg_z
                if project.mass is not None and project.mass.cases else 0.0)
        limits = wtenv_cg_limits(project)
        fwd, aft = limits if limits is not None else (0.0, 0.0)
        src = [CgCase(_CG_NAMES[0], gross, aft, zbar),
               CgCase(_CG_NAMES[1], gross, fwd, zbar),
               CgCase(_CG_NAMES[2], light, fwd, zbar)]
    return [{"name": c.name,
             "weight_lb": round(to_display(c.weight_lb, "weight", system), 3),
             "xcg": round(to_display(c.xcg, "length", system), 3),
             "zcg": round(to_display(c.zcg, "length", system), 3)} for c in src]


st.title("Landing Loads — LGFACTOR + LANDLOAD")
st.caption(
    "Python/Streamlit port of LGFACTOR.BAS + LANDLOAD.BAS (Reference 1 Ch 20): the "
    "landing load factor (FAR 23.473) and the tricycle-gear ground reactions "
    "(FAR 23.473–23.499)."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","length","area_sqft",...} -> unit string
inp = project.landing or LandingInput()

with st.form("landing_loads_form"):
    st.subheader("Landing load factor (LGFACTOR)")
    c1, c2, c3 = st.columns(3)
    max_landing_weight_lb = c1.number_input(
        f"Max landing weight, W ({U['weight']})", min_value=0.0,
        value=float(round(to_display(inp.max_landing_weight_lb, "weight", system), 4)),
        help="Typically 0.95·MTOW (FAR 23.473(b)/(c)); not auto-derived (an engineering "
             "judgment call, not a duplicate of another slice).",
        key=f"max_landing_weight_{system.value}")
    gross_weight_lb = c2.number_input(
        f"Gross (max take-off) weight override, GW ({U['weight']})", min_value=0.0,
        value=float(round(to_display(inp.gross_weight_lb, "weight", system), 4)),
        help="0 → derived from the heaviest CG case (Project.mass).",
        key=f"gross_weight_{system.value}")
    # Step M2-6: wing area is single-sourced from the geometry wing (read-only here).
    _wr = wing_reference(project, "wing")
    _wing_area_display = _wr.s_sqft if _wr is not None else inp.wing_area_sqft
    c3.metric(f"Wing area S ({U['area_sqft']})",
              f"{to_display(_wing_area_display, 'area_sqft', system):.3f}",
              help="Single-sourced from the wing planform on the Geometry page (Step M2-6).")
    strut_stroke_in = c1.number_input(
        f"Strut stroke ({U['length']})", min_value=0.0,
        value=float(round(to_display(inp.strut_stroke_in, "length", system), 4)),
        key=f"strut_stroke_{system.value}")
    tire_od_in = c2.number_input(
        f"Tyre OD ({U['length']})", min_value=0.0,
        value=float(round(to_display(inp.tire_od_in, "length", system), 4)),
        key=f"tire_od_{system.value}")
    hub_diameter_in = c3.number_input(
        f"Hub diameter ({U['length']})", min_value=0.0,
        value=float(round(to_display(inp.hub_diameter_in, "length", system), 4)),
        key=f"hub_diameter_{system.value}")
    lift_factor = c1.number_input(
        "Wing lift factor, L (≤ 0.667)", min_value=0.0, max_value=0.667,
        value=float(inp.lift_factor))
    gear_load_factor = c2.number_input(
        "Gear load factor override, NLG", min_value=0.0, value=float(inp.gear_load_factor),
        help="0 → use LGFACTOR's computed N − L. LANDLOAD usually rounds it up.")

    tail_down_angle_deg = st.number_input("Tail-down ground angle (deg)", min_value=0.0,
                                          value=float(inp.tail_down_angle_deg))

    st.subheader("Landing CG cases")
    st.caption(
        "The three distinct landing loadings LANDLOAD cycles (aft-max / fwd-max / "
        "fwd-light landing; UG fig 18.2) — editable here (previously project-JSON only). "
        "Seeded from the WTENV structural CG envelope (fwd/aft stations + gross / "
        "fwd-regardless weights) when present; **confirm the fwd vs aft stations**, which "
        "WTENV cannot distinguish per loading.")
    edited_cg = st.data_editor(
        pd.DataFrame(_seed_cg_rows(project, inp, system)),
        num_rows="fixed", width="stretch", key=f"landing_cg_editor_{system.value}",
        column_config={
            "name": st.column_config.TextColumn("Loading"),
            "weight_lb": st.column_config.NumberColumn(f"Weight ({U['weight']})", min_value=0.0),
            "xcg": st.column_config.NumberColumn(f"Xcg station ({U['length']})"),
            "zcg": st.column_config.NumberColumn(f"Zcg waterline ({U['length']})"),
        })

    st.caption(
        "The **landing-gear geometry** (axle stations, tread, rolling radius, strut) is "
        "the single-source **Landing gear** section on the **Geometry** page (Step G6b) — "
        "edit it there; LANDLOAD reads it read-only.")
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    inp.max_landing_weight_lb = to_imperial_scalar(max_landing_weight_lb, "weight", system)
    inp.gross_weight_lb = to_imperial_scalar(gross_weight_lb, "weight", system)
    # wing_area_sqft is derived from geometry (Step M2-6) -- not written here.
    inp.strut_stroke_in = to_imperial_scalar(strut_stroke_in, "length", system)
    inp.tire_od_in = to_imperial_scalar(tire_od_in, "length", system)
    inp.hub_diameter_in = to_imperial_scalar(hub_diameter_in, "length", system)
    inp.lift_factor = lift_factor
    inp.gear_load_factor = gear_load_factor
    inp.tail_down_angle_deg = tail_down_angle_deg
    inp.cg_cases = [
        CgCase(name=str(r["name"]),
               weight_lb=to_imperial_scalar(float(r["weight_lb"]), "weight", system),
               xcg=to_imperial_scalar(float(r["xcg"]), "length", system),
               zcg=to_imperial_scalar(float(r["zcg"]), "length", system))
        for r in edited_cg.to_dict("records")]
    project.landing = inp
    st.session_state["project"] = project
    st.success("Landing/ground inputs applied.")

if len([c for c in inp.cg_cases if c.weight_lb > 0]) != 3:
    st.info("Enter the three landing **CG cases** above (each with a positive weight) "
            "and press **Apply** to compute the ground reactions.")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    lf, reactions = build_landing(project)
    mod = run(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute landing loads: {exc}")
    st.stop()

st.subheader("Landing load factor")
m1, m2, m3 = st.columns(3)
m1.metric("Sink rate (ft/s)", f"{lf.sink_rate_fps:.3f}")
m2.metric("Airplane load factor N", f"{lf.airplane_load_factor:.3f}")
m3.metric("Gear load factor NLG", f"{lf.gear_load_factor:.3f}")

st.subheader("Gear reaction loads (ground line)")
st.caption(
    "On-screen reactions are **LIMIT** (oracle values, traceable to the manual). "
    "The CSV download below and the **Review/Export** pages report **ULTIMATE** "
    "= limit × 1.5 (14 CFR 23.303)."
)
_lbf_lbl = si_scalar_label("lbf", system)
# Display-only conversion of the ground-reaction forces; ``reactions``/``mod``
# (the CSV export below) are never touched -- they stay Imperial.
rows = [{
    "Case": c.case, "Condition": c.description, "FAR": c.far_reference, "CG": c.cg_name,
    f"VMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.vmp, "lbf", system), 1),
    f"DMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.dmp, "lbf", system), 1),
    f"SMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.smp, "lbf", system), 1),
    f"RMP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.rmp, "lbf", system), 1),
    f"VNP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.vnp, "lbf", system), 1),
    f"DNP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.dnp, "lbf", system), 1),
    f"SNP ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.snp, "lbf", system), 1),
    f"RESULT ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.result, "lbf", system), 1),
} for c in reactions]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.caption(f"VMP/DMP/SMP — vertical/drag/side main per wheel; VNP/DNP/SNP — nose. "
           f"Loads in {_lbf_lbl}, with respect to the ground line.")

st.download_button("Download landing loads (CSV)", io.load_cases_csv(mod),
                   file_name="landing_loads.csv", mime="text/csv")
