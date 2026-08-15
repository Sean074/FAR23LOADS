"""Streamlit page for landing / ground loads (LGFACTOR + LANDLOAD, Ch 20).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Estimates the landing load factor (LGFACTOR, FAR 23.473(d)-(g)) from the drop-test
work-energy balance, then computes the tricycle-gear reaction loads for the level,
tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel ground
conditions (LANDLOAD, FAR 23.473-23.499). Since decision G-3 the three landing CG
loadings are **not** entered here: they are the roled GROUND cases of the one
shared weight/CG case list, owned by the Weight & Mass Properties page's Payload
Cases tab and shown read-only below. Both design weights (MLW, MTOW) are likewise
read from WeightInput (G-4 / G-14). Tricycle gear only (UG Table 2.1).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import page_header, workflow_page_link

from sloads import (
    LandingInput,
    UnitSystem,
    io,
    si_scalar_label,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads.cg_cases import (
    landing_role_cases,
    max_landing_weight,
    max_landing_weight_estimate,
    max_takeoff_weight,
)
from sloads.derived_geometry import wing_reference
from sloads.modules.landing import build_landing, run
from sloads.models import MissingInputError
from sloads.validation import (
    consistency_warnings,
    landing_reaction_warnings,
)


def _cg_table(cases, system: UnitSystem) -> pd.DataFrame:
    """The three roled loadings, in display units, read-only (decision G-3)."""
    return pd.DataFrame([{
        "role": c.role.value.replace("_", " ") if c.role else "",
        "name": c.name,
        "weight": round(to_display(c.weight_lb, "weight", system), 3),
        "xcg": round(to_display(c.xcg, "length", system), 3),
        "zcg": round(to_display(c.zcg, "length", system), 3),
    } for c in cases])


project, system, U = page_header("landing_loads", title="Landing Loads — LGFACTOR + LANDLOAD", banner=False)
st.caption(
    "Python/Streamlit port of LGFACTOR.BAS + LANDLOAD.BAS (Reference 1 Ch 20): the "
    "landing load factor (FAR 23.473) and the tricycle-gear ground reactions "
    "(FAR 23.473–23.499)."
)

inp = project.landing or LandingInput()

with st.form("landing_loads_form"):
    st.subheader("Landing load factor (LGFACTOR)")
    c1, c2, c3 = st.columns(3)
    _mlw = max_landing_weight(project, required=False)
    _mtow = max_takeoff_weight(project, required=False)
    c1.metric(
        f"Max landing weight, W ({U['weight']})",
        f"{to_display(_mlw, 'weight', system):,.1f}" if _mlw else "—",
        help="Single-sourced from **weight.max_landing_weight_lb** (decision G-4) — "
             "a certified airplane-level limit, not a property of a loading, so it "
             "is entered once on the Weight & Mass Properties page. Typically "
             "0.95·MTOW (FAR 23.473(b)/(c)).")
    c2.metric(
        f"Max take-off weight, GW ({U['weight']})",
        f"{to_display(_mtow, 'weight', system):,.1f}" if _mtow else "—",
        help="Single-sourced from **weight.max_takeoff_weight_lb** (decision G-14). "
             "WR = GW/W scales the braked-roll, side and supplementary-nose cases. "
             "The old override fell back to the heaviest *landing* case, which is "
             "MLW — WR = 1.0, understating those cases by ~5 %.")
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
        "fwd-light landing; UG fig 18.2) — **read-only here since decision G-3**. "
        "They are the GROUND-tagged cases of the one shared weight/CG case list, "
        "edited on **Weight & Mass Properties → Payload Cases**, where each case "
        "states the analyses it is run for and its landing **role**. The role is "
        "what fixes the order LANDLOAD consumes them in; it used to be recovered by "
        "matching names, so a renamed case silently reordered the reaction table.")
    try:
        _roled = landing_role_cases(project)
    except (MissingInputError, ValueError) as _exc:
        _roled = []
        st.warning(str(_exc))
    if _roled:
        st.dataframe(_cg_table(_roled, system), width="stretch", hide_index=True,
                     column_config={
                         "role": "Role", "name": "Case",
                         "weight": f"Weight ({U['weight']})",
                         "xcg": f"Xcg station ({U['length']})",
                         "zcg": f"Zcg waterline ({U['length']})"})
    workflow_page_link("weight_mass", label="→ Weight & Mass Properties (edit the cases)")

    st.caption(
        "The **landing-gear geometry** (axle stations, tread, rolling radius, strut) is "
        "the single-source **Landing gear** section on the **Geometry** page (Step G6b) — "
        "edit it there; LANDLOAD reads it read-only.")
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    # Neither design weight is written here any more (G-4 / G-14), and neither are
    # the CG cases (G-3): this form owns the LGFACTOR strut/tyre scalars only.
    # wing_area_sqft is derived from geometry (Step M2-6) -- not written here.
    inp.strut_stroke_in = to_imperial_scalar(strut_stroke_in, "length", system)
    inp.tire_od_in = to_imperial_scalar(tire_od_in, "length", system)
    inp.hub_diameter_in = to_imperial_scalar(hub_diameter_in, "length", system)
    inp.lift_factor = lift_factor
    inp.gear_load_factor = gear_load_factor
    inp.tail_down_angle_deg = tail_down_angle_deg
    project.landing = inp
    st.session_state["project"] = project
    st.success("Landing/ground inputs applied.")

_blocked = []
if not max_landing_weight(project, required=False):
    _est = max_landing_weight_estimate(project)
    _blocked.append(
        "**Max landing weight unset.** Enter it on **Weight & Mass Properties** "
        "(typically 0.95·MTOW, FAR 23.473(b)/(c))."
        + (f" A starting estimate from the item database — OEW + max payload + "
           f"reserve fuel — is {to_display(_est, 'weight', system):,.0f} "
           f"{U['weight']}." if _est else ""))
try:
    _cases = landing_role_cases(project)
except (MissingInputError, ValueError) as _exc:
    _cases = []
    _blocked.append(str(_exc))
else:
    _incomplete = [c.name for c in _cases
                   if c.weight_lb <= 0 or c.xcg <= 0 or c.zcg <= 0]
    if _incomplete:
        _blocked.append(
            "Each roled landing case needs a positive weight, Xcg station and "
            "**Zcg waterline** — a zero waterline puts the CG on the ground line "
            "and inverts the nose-gear reaction (M4-17c). Incomplete: "
            + ", ".join(_incomplete) + ".")
if _blocked:
    for _msg in _blocked:
        st.info(_msg)
    workflow_page_link("weight_mass", label="→ Weight & Mass Properties")
    st.stop()

for _w in consistency_warnings(project):
    if _w.page == "landing_loads":
        st.warning(_w.message)

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

for _w in landing_reaction_warnings(reactions):
    st.warning(_w.message)

st.subheader("Gear reaction loads (ground line)")
st.caption(
    "On-screen reactions are **LIMIT** (oracle values, traceable to the manual). "
    "The CSV download below and the **Review/Export** pages report **ULTIMATE** "
    "= limit × 1.5 (14 CFR 23.303) for every one of these 33 cases; the dimensionless "
    "inertia factors NVP/NDP/NS are load *factors* and are never scaled."
)
_lbf_lbl = si_scalar_label("lbf", system)
_mom_lbl = si_scalar_label("lb-in", system)
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
    f"PITCH ({_mom_lbl}, LIMIT)": round(to_si_scalar(c.pitchp, "lb-in", system), 1),
    f"ROLL ({_mom_lbl}, LIMIT)": round(to_si_scalar(c.rollp, "lb-in", system), 1),
    f"YAW ({_mom_lbl}, LIMIT)": round(to_si_scalar(c.yawp, "lb-in", system), 1),
    "NVP": round(c.nvp, 3),
    "NDP": round(c.ndp, 3),
    "NS": round(c.ns, 3),
} for c in reactions]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.caption(
    f"VMP/DMP/SMP — vertical/drag/side main per wheel; VNP/DNP/SNP — nose; loads in "
    f"{_lbf_lbl}, with respect to the ground line. PITCH/ROLL/YAW — the unbalanced "
    f"moments about the airplane CG ({_mom_lbl}). NVP/NDP/NS — the dimensionless "
    "ground-line inertia factors (limit basis; load factors are never scaled to "
    "ultimate). Cases 25–33 are the supplementary nose-wheel family: nose reactions "
    "only.")

st.download_button("Download landing loads (CSV)", io.load_cases_csv(mod, system=system),
                   file_name="landing_loads.csv", mime="text/csv")
st.caption(
    "The CSV carries **all 33 cases** — reactions, unbalanced moments and inertia "
    "factors — plus the landing load factor and the six per-family critical-reaction "
    "summaries, all ULTIMATE (M4-17e).")
