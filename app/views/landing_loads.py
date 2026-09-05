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

from app_shell import optional_slice
from app_shell.components import (
    LANDING_L_FAR_CAPTION,
    page_header,
    stop_page,
    unit_number_input,
    workflow_page_link,
)
from app_shell.widget_keys import widget_key
from sloads import (
    LandingInput,
    UnitSystem,
    io,
    si_scalar_label,
    to_display,
    to_si_scalar,
)
from sloads.cg_cases import (
    landing_role_cases,
    max_landing_weight,
    max_landing_weight_estimate,
    max_takeoff_weight,
)
from sloads.derived_geometry import wing_reference
from sloads.export import sbeam_bridge as sb
from sloads.frames import AIRPLANE_DATUM, GROUND_LINE, caption
from sloads.gear_loads import UNSPRUNG_NOTE, gear_case_loads
from sloads.models import MissingInputError
from sloads.modules.landing import (
    below_energy_caution,
    build_landing,
    energy_load_factor_estimate,
    governing_load_factors,
    run,
)
from sloads.report import LoadChannel
from sloads.validation import (
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

# Captured before the form mutates ``inp`` in place: ``store`` needs to
# know whether the project *had* this Optional slice (#145).
_existing_slice = project.landing
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
    strut_stroke_in = unit_number_input(
        "Strut stroke", float(inp.strut_stroke_in),
        kind="length", key="land_strut_stroke", min_value=0.0, container=c1)
    tire_od_in = unit_number_input(
        "Tyre OD", float(inp.tire_od_in),
        kind="length", key="land_tire_od", min_value=0.0, container=c2)
    hub_diameter_in = unit_number_input(
        "Hub diameter", float(inp.hub_diameter_in),
        kind="length", key="land_hub_diameter", min_value=0.0, container=c3)
    lift_factor = c1.number_input(
        "Wing lift factor, L", min_value=0.0,
        value=float(inp.lift_factor), key=widget_key("land_lift_factor"),
        help=LANDING_L_FAR_CAPTION)
    # The governing N (note 37, LF-7): seeded from LGFACTOR's computed energy
    # value, editable; the checkbox is the way back to computed (the app-form
    # shape of the oracle GUI's "✕ clear"). NLG = N − L is derived below --
    # never entered, so a change to L always moves the gear reaction.
    _energy_est = energy_load_factor_estimate(project)
    _n_seed = (inp.airplane_load_factor if inp.airplane_load_factor is not None
               else (_energy_est.airplane_load_factor if _energy_est else 0.0))
    use_computed_n = c2.checkbox(
        "Computed N governs", value=inp.airplane_load_factor is None,
        key=widget_key("land_n_use_computed"),
        help="Checked → LGFACTOR's drop-test energy N governs the reactions. "
             "Uncheck to enter a rounded design N (LANDLOAD runs at 3.167 on the "
             "p230 oracle). NLG = N − L is always derived, never entered.")
    entered_n = c2.number_input(
        "Airplane load factor, N (governing)", min_value=0.0, value=float(_n_seed),
        key=widget_key("land_airplane_load_factor"), disabled=use_computed_n,
        help="The N the gear reactions run at. FAR 23.473(g) floors: N ≥ 2.67, "
             "NLG ≥ 2.0 — refused in a FAR 23 category, warned in concept.")

    tail_down_angle_deg = st.number_input("Tail-down ground angle (deg)", min_value=0.0,
                                          value=float(inp.tail_down_angle_deg),
                                          key=widget_key("land_tail_down_angle"))

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
    inp.strut_stroke_in = strut_stroke_in
    inp.tire_od_in = tire_od_in
    inp.hub_diameter_in = hub_diameter_in
    inp.lift_factor = lift_factor
    inp.airplane_load_factor = None if use_computed_n else entered_n
    inp.tail_down_angle_deg = tail_down_angle_deg
    project.landing = optional_slice.store(inp, _existing_slice)
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
    stop_page()

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    lf, reactions = build_landing(project)
    mod = run(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute landing loads: {exc}")
    stop_page()

st.subheader("Landing load factor")
_n_gov, _nlg_gov = governing_load_factors(inp, lf)
m1, m2, m3 = st.columns(3)
m1.metric("Sink rate (ft/s)", f"{lf.sink_rate_fps:.3f}",
          help="LGFACTOR's drop-test estimate (FAR 23.473(d)).")
m2.metric("Computed (energy) N", f"{lf.airplane_load_factor:.3f}",
          help="The work-energy airplane load factor LGFACTOR estimates; it "
               "governs when no N is entered above.")
m3.metric("Computed (energy) NLG", f"{lf.gear_load_factor:.3f}")
g1, g2, g3 = st.columns(3)
g2.metric("Governing N", f"{_n_gov:.3f}",
          help="What the 33-case reaction matrix below actually runs at "
               "(entered, else the computed energy value).")
g3.metric("Governing NLG (= N − L)", f"{_nlg_gov:.3f}",
          help="Derived, never entered (note 37): the wing lift factor L "
               "always moves the gear reaction.")

_caution = below_energy_caution(project)
if _caution:
    st.warning(_caution)
for _w in landing_reaction_warnings(reactions):
    st.warning(_w.message)

st.subheader(f"Gear reaction loads ({caption(GROUND_LINE)})")
st.caption(
    "On-screen reactions are **LIMIT** (oracle values, traceable to the manual). "
    "So are the CSV download below and the **Review/Export** pages: for every "
    "one of these 33 cases the 14 CFR 23.303 factor is stated and applied "
    "nowhere — apply it in the sizing analysis. The dimensionless inertia "
    "factors NVP/NDP/NS are load *factors* and carry no factor at all."
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
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
st.caption(
    f"VMP/DMP/SMP — vertical/drag/side main per wheel; VNP/DNP/SNP — nose; loads in "
    f"{_lbf_lbl}, {caption(GROUND_LINE)}. PITCH/ROLL/YAW — the unbalanced "
    f"moments about the airplane CG ({_mom_lbl}). NVP/NDP/NS — the dimensionless "
    "ground-line inertia factors (limit basis; load factors are never scaled to "
    "ultimate). Cases 25–33 are the supplementary nose-wheel family: nose reactions "
    "only.")

# The airplane-datum half of the printout (design note 38 GF-6). p232 prints the
# whole matrix a second time in the airplane's own axes, and until #134 the
# replication computed vm/dm/vn/dn and never showed them, so this page and the
# deck that consumes them were single-frame and unlabelled.
st.subheader(f"Gear reaction loads ({caption(AIRPLANE_DATUM)})")
st.caption(
    "The same 33 cases in the airplane's own axes — the frame a beam model "
    "applies and the frame the export deck and the CSV carry. Reactions are "
    "**LIMIT** here as above.")
datum_rows = [{
    "Case": c.case, "Condition": c.description, "CG": c.cg_name,
    "Fuselage axis angle (deg)": round(c.fuselage_axis_angle_deg, 4),
    f"VM ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.vm, "lbf", system), 1),
    f"DM ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.dm, "lbf", system), 1),
    f"VN ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.vn, "lbf", system), 1),
    f"DN ({_lbf_lbl}, LIMIT)": round(to_si_scalar(c.dn, "lbf", system), 1),
    f"PITCH ({_mom_lbl}, LIMIT)": round(to_si_scalar(c.pitch, "lb-in", system), 1),
    f"ROLL ({_mom_lbl}, LIMIT)": round(to_si_scalar(c.roll, "lb-in", system), 1),
    f"YAW ({_mom_lbl}, LIMIT)": round(to_si_scalar(c.yaw, "lb-in", system), 1),
    "NR": round(c.nr, 3),
    "NV": round(c.nv, 3),
    "ND": round(c.nd, 3),
} for c in reactions]
st.dataframe(pd.DataFrame(datum_rows), width="stretch", hide_index=True)
st.caption(
    f"VM/DM — vertical/drag main per wheel; VN/DN — nose; PITCH/ROLL/YAW — the "
    f"unbalanced moments about the CG, {caption(AIRPLANE_DATUM)}. The pitching "
    f"moment is invariant under the rotation; roll and yaw mix. NR/NV/ND — the "
    f"p232 datum load factors (NS is common to both frames and is shown above). "
    f"Cases 25–33 carry no airplane in equilibrium and so no datum load factors "
    f"or moments. The fuselage axis angle is the attitude's ground angle — an "
    f"angle, never scaled.")

st.download_button("Download landing loads (CSV)", io.load_cases_csv(mod, system=system, channel=LoadChannel.LIMIT),
                   file_name="landing_loads.csv", mime="text/csv")
st.caption(
    f"The CSV carries **all 33 cases** — for each of the three wheels (nose, "
    f"left main, right main, *all three on every case*, an unloaded gear at "
    f"zero) the force and the point it acts at, plus the datum load factors and "
    f"unbalanced moments — with the landing load factor and the six per-family "
    f"critical-reaction summaries, all **LIMIT** with the 14 CFR 23.303 factor "
    f"stated per case and applied nowhere. It is the deliverable, so it is "
    f"{caption(AIRPLANE_DATUM)} throughout; the primed set above is the manual's "
    f"analysis view and rides in the **text** report instead (design note 38 "
    f"GF-6).")

# --------------------------------------------------------------------------- #
# The gear free body (decision G-12) -- both ends of the leg
# --------------------------------------------------------------------------- #
st.subheader("Gear interface loads (the free body)")
st.caption(
    "The **gear interface load definition**: where the reaction acts, at what "
    "strut state and ground angle, and what arrives at the gear reference point. "
    "This is the boundary condition a gear analysis starts from, and it is the "
    "other side of the assembled ground cases — the reference-point reaction "
    "below is the load the assembled deck applies at that node, sign-flipped."
)
try:
    _gear = gear_case_loads(project)
except MissingInputError:
    _gear = []
if not _gear:
    st.info(
        "No gear interface loads: this project has no landing-gear geometry. "
        "The report needs the axle positions at the three strut states, the "
        "rolling radius and the tread — it does **not** need a derivable mass "
        "loading, which is why it reaches airplanes the assembled ground cases "
        "do not."
    )
else:
    _stroke_rows = {}
    for _c in _gear:
        for _leg in _c.legs:
            _stroke_rows.setdefault(
                (_leg.leg, _leg.strut_state, round(_leg.ground_angle_deg, 3),
                 round(_leg.stroke_in, 3), round(_leg.stroke_fraction, 4)), []
            ).append(_c.case)
    st.dataframe(pd.DataFrame([{
        "Leg": leg, "Strut state": state, "Ground angle (deg)": round(angle, 2),
        f"Stroke from extended ({si_scalar_label('in', system)})":
            round(to_si_scalar(stroke, "in", system), 2),
        "% of stroke": f"{fraction * 100:.0f} %",
        "LANDLOAD cases": f"{min(cases)}–{max(cases)}",
    } for (leg, state, angle, stroke, fraction), cases in _stroke_rows.items()]),
        width="stretch", hide_index=True)
    st.caption(
        "The landing families are computed near the **top** of the stroke and "
        "the handling families near the **bottom** — impact versus sitting. "
        "The application node does not move between attitudes: a trunnion is "
        "fixed to the airframe, so the difference lands in the lever arm.")

    _unstated = sorted({leg.leg for c in _gear for leg in c.legs
                        if leg.leg_weight_lb is None
                        and (any(leg.airplane) or any(leg.ground_line))})
    if _unstated:
        st.warning(
            "No leg weight is entered for the "
            + " and ".join(_unstated) + " gear, so the free body is shown "
            "**open**: the inertia term and the net-above-trunnion column are "
            "blank rather than closed against a guessed weight. Enter the leg "
            "weight (the whole leg, trunnion down) on the Geometry page."
        )
    st.caption(":orange[Limit of the inertia term.] " + UNSPRUNG_NOTE + ".")
    st.caption(
        ":orange[What this is not.] sloads has no gear kinematic model, so this "
        "does **not** state drag-brace, side-brace, trunnion or axle-bending "
        "loads and must not be read as doing so. With the contact patch, the "
        "components, the ground angle, the stroke and the reference-point "
        "reaction, a gear engineer builds those.")
    st.download_button(
        "Download gear interface loads (CSV)",
        sb.gear_report_csv(project, system=system),
        file_name="gear_loads.csv", mime="text/csv")
    st.caption(
        f"All **33 cases** × each loaded leg, **LIMIT** — each row states the "
        f"14 CFR 23.303 factor and applies it nowhere. Contact-patch components "
        f"are {caption(GROUND_LINE)} (as the manual prints them); reference-point "
        f"components are {caption(AIRPLANE_DATUM)} (as a beam model applies "
        f"them). The assembled ground "
        "cases carry 24 — the 23.499 supplementary nose-wheel family is a "
        "gear-design case with no airplane equilibrium, and belongs here.")
