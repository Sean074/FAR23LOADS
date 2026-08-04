"""Streamlit page for landing / ground loads (LGFACTOR + LANDLOAD, Ch 20).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Estimates the landing load factor (LGFACTOR, FAR 23.473(d)-(g)) from the drop-test
work-energy balance, then computes the tricycle-gear reaction loads for the level,
tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel ground
conditions (LANDLOAD, FAR 23.473-23.499). The three landing CG loadings are entered
here (landing.cg_cases); the waterline is seeded from Project.mass (WTONECG) when
present and left **blank** otherwise — LANDLOAD will not run on a zero waterline
(M4-17c). Tricycle gear only (UG Table 2.1).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import page_header, workflow_page_link

from sloads import (
    CgCase,
    LandingInput,
    Project,
    UnitSystem,
    io,
    si_scalar_label,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads.derived_geometry import wing_reference
from sloads.modules.landing import build_landing, run
from sloads.validation import (
    LANDING_CG_NAMES,
    consistency_warnings,
    landing_reaction_warnings,
    wtenv_cg_limits,
    wtenv_fwd_cg_limit_at_weight,
)


_CG_NAMES = LANDING_CG_NAMES


def _row(name: str, w, x, z, system: UnitSystem) -> dict:
    """One editor row in display units; a missing (None / non-positive) source is
    left blank (``None``), never zero-filled -- see ``_seed_cg_rows``."""
    def d(value, kind: str):
        if value is None or value <= 0:
            return None
        return round(to_display(value, kind, system), 3)

    return {"name": name, "weight_lb": d(w, "weight"),
            "xcg": d(x, "length"), "zcg": d(z, "length")}


def _seed_cg_rows(project: Project, inp: LandingInput, system: UnitSystem) -> list:
    """Three display-unit CG rows for the editor (M2R-5; rewritten M4-17c).

    Existing ``landing.cg_cases`` when present (edit what's there); otherwise a WTENV
    seed in which **every cell without a real source is left blank rather than
    zero-filled**:

    * ``weight`` -- the two max-landing rows use the entered max landing weight and
      are blank when it is unset (they previously seeded full MTOW, silently
      analysing an over-weight landing); the light row uses the WTENV
      fwd-regardless weight.
    * ``xcg`` -- aft rows from ``wtenv_cg_limits``' aft-gross station; forward rows
      from ``wtenv_fwd_cg_limit_at_weight`` **interpolated at that row's own
      weight**. Appendix A p230 reads 76.12 in at the 3230 lb landing weight, not
      the 72.64 in weight-agnostic hull value the old seed handed both max-landing
      rows.
    * ``zcg`` -- the WTONECG waterline ``project.mass.cases[0].cg_z``, blank when no
      mass slice exists. Seeding 0.0 against a ~60 in axle waterline put the CG on
      the ground line and produced nonphysical negative nose reactions and
      braked-roll main loads ~2.6x the p230 oracle, with no warning.

    The fwd/aft station split is a seed only: WTENV cannot distinguish it per loading."""
    if len(inp.cg_cases) == 3:
        return [_row(c.name, c.weight_lb, c.xcg, c.zcg, system) for c in inp.cg_cases]

    env = project.weight.envelope if project.weight is not None else None
    w_land = inp.max_landing_weight_lb or None
    w_light = (env.fwd_regardless_weight or None) if env is not None else None
    limits = wtenv_cg_limits(project)
    aft = limits[1] if limits is not None else None
    fwd_land = wtenv_fwd_cg_limit_at_weight(project, w_land) if w_land else None
    fwd_light = wtenv_fwd_cg_limit_at_weight(project, w_light) if w_light else None
    zbar = (project.mass.cases[0].cg_z
            if project.mass is not None and project.mass.cases else None)
    seeds = ((_CG_NAMES[0], w_land, aft, zbar),
             (_CG_NAMES[1], w_land, fwd_land, zbar),
             (_CG_NAMES[2], w_light, fwd_light, zbar))
    return [_row(n, w, x, z, system) for n, w, x, z in seeds]


def _seed_warnings(project: Project, inp: LandingInput) -> list:
    """Missing-source messages for the seed, each naming the source and its effect."""
    out = []
    if project.mass is None or not project.mass.cases:
        out.append(
            "**Zcg waterline — no source.** `Project.mass` is empty, so the waterline "
            "cells are blank. Open **Weight & Mass Properties → Weight, CG & Inertia**, "
            "fill the itemised mass data base and press **Apply weight items**: its "
            "ZBAR is the waterline LANDLOAD needs. A zero waterline puts the CG on the "
            "ground line — it inverts the nose-gear reaction (negative VNP) and "
            "inflates the braked-roll main loads ~2.6×.")
    if not inp.max_landing_weight_lb:
        out.append(
            "**Max landing weight unset** — the two max-landing rows are blank. Enter "
            "it above (typically 0.95·MTOW, FAR 23.473(b)/(c)). It is no longer seeded "
            "at full MTOW, and the forward CG limit is interpolated *at* it.")
    if wtenv_cg_limits(project) is None:
        out.append(
            "**No WTENV envelope** — the Xcg stations are blank. Fill the **Weight / CG "
            "Envelope** tab on the Weight & Mass Properties page.")
    return out


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
    max_landing_weight_lb = c1.number_input(
        f"Max landing weight, W ({U['weight']})", min_value=0.0,
        value=float(round(to_display(inp.max_landing_weight_lb, "weight", system), 4)),
        help="Typically 0.95·MTOW (FAR 23.473(b)/(c)); not auto-derived (an engineering "
             "judgment call, not a duplicate of another slice).",
        key=f"max_landing_weight_{system.value}")
    gross_weight_lb = c2.number_input(
        f"Gross (max take-off) weight override, GW ({U['weight']})", min_value=0.0,
        value=float(round(to_display(inp.gross_weight_lb, "weight", system), 4)),
        help="0 → derived from the heaviest **landing CG case** below (the max of the "
             "three weights). Must be ≥ the max landing weight: WR = GW/W scales the "
             "braked-roll, side and supplementary-nose cases.",
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
        "fwd-regardless weights, with the forward limit interpolated **at** each row's "
        "weight) when present; **confirm the fwd vs aft stations**, which WTENV cannot "
        "distinguish per loading. A cell with no real source is left **blank** — it is "
        "never defaulted to zero (M4-17c).")
    for _msg in _seed_warnings(project, inp):
        st.warning(_msg)
    edited_cg = st.data_editor(
        pd.DataFrame(_seed_cg_rows(project, inp, system)),
        num_rows="fixed", width="stretch", key=f"landing_cg_editor_{system.value}",
        column_config={
            "name": st.column_config.TextColumn(
                "Loading", disabled=True,
                help="Fixed order: LANDLOAD assigns the braked-roll / side weight "
                     "groups by position (aft max landing, fwd max landing, fwd "
                     "light; UG fig 18.2)."),
            "weight_lb": st.column_config.NumberColumn(f"Weight ({U['weight']})",
                                                       min_value=0.0, format="%.3f"),
            "xcg": st.column_config.NumberColumn(f"Xcg station ({U['length']})",
                                                 format="%.3f"),
            "zcg": st.column_config.NumberColumn(f"Zcg waterline ({U['length']})",
                                                 format="%.3f"),
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
    # A blank/zero cell is *not* saved: LANDLOAD on a zero waterline or a zero station
    # computes nonphysical reactions silently (M4-17c). The names are written from the
    # canonical tuple, never from the (read-only) cell, so a renamed row cannot
    # mis-assign the positional weight groups.
    _records = edited_cg.to_dict("records")
    _incomplete_rows = [
        _CG_NAMES[i] for i, r in enumerate(_records)
        if any(r.get(k) is None or pd.isna(r.get(k)) or float(r[k]) <= 0.0
               for k in ("weight_lb", "xcg", "zcg"))]
    if _incomplete_rows:
        st.error(
            "Landing CG cases **not saved** — every row needs a positive weight, Xcg "
            "station and Zcg waterline. Incomplete: " + ", ".join(_incomplete_rows)
            + ". (A zero waterline is rejected, not defaulted.)")
    else:
        inp.cg_cases = [
            CgCase(name=_CG_NAMES[i],
                   weight_lb=to_imperial_scalar(float(r["weight_lb"]), "weight", system),
                   xcg=to_imperial_scalar(float(r["xcg"]), "length", system),
                   zcg=to_imperial_scalar(float(r["zcg"]), "length", system))
            for i, r in enumerate(_records)]
    project.landing = inp
    st.session_state["project"] = project
    st.success("Landing/ground inputs applied.")

_incomplete = [c.name for c in inp.cg_cases
               if c.weight_lb <= 0 or c.xcg <= 0 or c.zcg <= 0]
if len(inp.cg_cases) != 3 or _incomplete:
    st.info(
        "Enter the three landing **CG cases** above — each needs a positive weight, "
        "Xcg station and **Zcg waterline** — then press **Apply** to compute the "
        "ground reactions."
        + (f" Incomplete: {', '.join(_incomplete)}." if _incomplete else ""))
    workflow_page_link("weight_mass", label="→ Weight & Mass Properties (waterline source)")
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

st.download_button("Download landing loads (CSV)", io.load_cases_csv(mod),
                   file_name="landing_loads.csv", mime="text/csv")
st.caption(
    "The CSV carries **all 33 cases** — reactions, unbalanced moments and inertia "
    "factors — plus the landing load factor and the six per-family critical-reaction "
    "summaries, all ULTIMATE (M4-17e).")
