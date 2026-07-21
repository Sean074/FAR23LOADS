"""Streamlit page for FAR 23 structural design speeds (Step G3 consolidation).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Two tabs, each a formerly-separate page:

* **Design Speeds** -- STRSPEED limit maneuver load factors (FAR 23.337) and
  design airspeeds VA/VC/VD/VF (FAR 23.335) with their FAR minimums.
* **Speed–Altitude Envelope** -- MACHLIM Mach-limited equivalent airspeeds and the
  speed–altitude flight-limits diagram (MC/MD read from the Design Speeds tab).

The category, design weight, stall speeds and chosen speeds are owned here; the
speed–altitude tab only adds the ceiling and tabulation increment. Wing area and
design weight are read from the Geometry / Weight pages when present. All speeds
are knots equivalent airspeed (KEAS); altitudes are feet. Each tab is a function
so a missing-prerequisite guard can ``return`` without ``st.stop()`` killing the
sibling tab.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import render_applicability_banner, workflow_page_link

from farloads import (
    MachLimitInput,
    Project,
    StructuralSpeedsInput,
    UnitSystem,
    consistency_warnings,
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads import io as farloads_io
from farloads.constants import convert_airspeed, mach_to_eas, standard_atmosphere
from farloads.modules.mach_limit import mach_limit_lines
from farloads.modules.structural_speeds import design_speed_values, design_speeds
from farloads.report import module_text_report


st.title("Structural Design Speeds — FAR 23")
st.caption(
    "Limit maneuver load factors and design airspeeds (VA, VC, VD, VF) with their "
    "FAR minimums (STRSPEED), plus the Mach-limited speed–altitude flight-limits "
    "diagram (MACHLIM). All speeds are KEAS; altitudes are feet."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)

render_applicability_banner(project)

_CATS = {"Normal / commuter": "N", "Utility": "U", "Acrobatic": "A", "Concept (C)": "C"}
_CAT_LABELS = list(_CATS)


# --------------------------------------------------------------------------- #
# Tab 1 -- Design Speeds (STRSPEED)
# --------------------------------------------------------------------------- #
def _tab_design_speeds(project: Project, system: UnitSystem, U: dict) -> None:
    for _w in consistency_warnings(project):
        if _w.page == "structural_speeds":
            st.warning(_w.message)

    with st.expander("ℹ️ Parameter guide", expanded=False):
        st.markdown(
            "Design speeds and load factors per 14 CFR 23.335/23.337 (STRSPEED/MACHLIM, Ch 5). All speeds are "
            "**KEAS** (knots equivalent airspeed) and altitudes are feet — both stay aviation-standard in either "
            "unit system.\n\n"
            "- **VS / VSF** — stall speed, flaps up / flaps down.\n"
            "- **VA** — design manoeuvring speed (the positive-manoeuvre corner of the V-n envelope).\n"
            "- **VC** — design cruising speed; **VD** — design dive speed; **VF** — design flap speed.\n"
            "- **VH** — max level-flight speed at max continuous power (sea level).\n"
            "- **Shoulder altitude** — the envelope 'shoulder' where VC/VD are checked against the cruise/dive "
            "Mach limit.\n"
            "- **Concept load factors (n, n_neg)** — for Category = Concept only, you set the limit maneuver "
            "factors directly; no 14 CFR 23.337 cap is applied."
        )

    existing = project.speeds

    # WTESTIMA design seat count seeds the occupants default (seed-chain).
    seats_upstream = (
        project.weight.estimation.seats
        if project.weight is not None and project.weight.estimation is not None else 0
    )
    has_wing = project.geometry is not None and project.geometry.by_name(
        existing.wing_surface if existing else "wing") is not None
    # Design weight: read-through from the Weight DB so it is not entered twice.
    mtow_upstream = project.weight.direct_totals()[0] if project.weight and project.weight.items else 0.0
    has_weight_db = mtow_upstream > 0

    with st.form("structural_speeds_form"):
        st.caption(
            f"Input units: **{'Imperial' if system == UnitSystem.IMPERIAL else 'SI'}** "
            "(set in the sidebar's global **Units** control). Airspeed (kt) and "
            "altitude (ft) stay aviation-standard in both systems."
        )
        cat_default = next((k for k, v in _CATS.items() if existing and v == existing.category), "Normal / commuter")
        cat_label = st.selectbox(
            "Category", _CAT_LABELS, index=_CAT_LABELS.index(cat_default),
            help="Certification category (14 CFR 23.3); sets the limit maneuver load factors (23.337). "
                 "Concept (C) applies no FAR cap — you set the factors below.",
        )

        # Both the DB-read and the override are always rendered (forms don't react
        # live to a checkbox) -- which one wins is decided at Apply.
        if has_weight_db:
            mtow_upstream_display = to_display(mtow_upstream, "weight", system)
            st.caption(f"Design weight from the Weight DB: **{mtow_upstream_display:,.0f} {U['weight']}**.")
            override_weight = st.checkbox(
                "Override design weight", value=False,
                help="Uncheck to use the Weight DB total (Weight & Mass Properties page).",
            )
            weight_default = (
                to_display(existing.weight_lb, "weight", system) if existing and existing.weight_lb
                else mtow_upstream_display
            )
            weight_override = st.number_input(
                f"Design (gross) weight override ({U['weight']})", min_value=0.0,
                value=float(weight_default), key=f"weight_override_{system.value}",
                help="Design gross (take-off) weight used for the load factors and design speeds "
                     "(14 CFR 23.335; STRSPEED, Ch 5). Used only when 'Override design weight' is ticked.",
            )
        else:
            override_weight = True
            weight_default = (
                to_display(existing.weight_lb, "weight", system) if existing and existing.weight_lb else 0.0
            )
            weight_override = st.number_input(
                f"Design (gross) weight ({U['weight']})", min_value=0.0,
                value=float(weight_default), key=f"weight_{system.value}",
                help="Design gross (take-off) weight used for the load factors and design speeds "
                     "(14 CFR 23.335; STRSPEED, Ch 5).",
            )
            st.caption(
                "No weight data base found. Add items on the **Weight & Mass "
                "Properties** page, or enter the design weight directly above."
            )

        occ_default = (
            existing.occupants if existing and existing.occupants is not None
            else seats_upstream
        )
        occupants_in = st.number_input(
            "Occupants (total souls)", min_value=0, step=1, value=int(occ_default),
            help=(
                "Total people on board (crew + passengers). The FAR 23 applicability "
                "check counts passenger seats = occupants − 2 pilot stations against "
                "the 9-seat limit (14 CFR 23.1). Seeds from the Weight Estimate seat "
                "count when left unset."
            ),
        )

        if has_wing:
            st.caption("Wing area read from the Geometry page.")
            wing_area = None
        else:
            wing_area_default = (
                to_display(existing.wing_area_sqft, "area_sqft", system) if existing and existing.wing_area_sqft
                else 0.0
            )
            wing_area = st.number_input(
                f"Wing area S ({U['area_sqft']})", min_value=0.0,
                value=float(wing_area_default), key=f"wing_area_{system.value}",
                help="Reference wing area S; with weight gives the wing loading W/S that sets the stall "
                     "and maneuvering speeds. Read from Geometry when a wing surface exists.",
            )
            st.caption(
                "No wing geometry found. Define the wing on the **Geometry** page, "
                "or enter the wing area directly above."
            )
            workflow_page_link("configuration_layout", label="→ Geometry")
        vh = st.number_input("Max sea-level speed VH (kt)", min_value=0.0,
                             value=float(existing.vh_kt) if existing else 0.0,
                             help="Maximum speed in level flight at max continuous power, sea level (KEAS); "
                                  "a floor for the minimum cruise speed VC (14 CFR 23.335).")
        st.caption(
            "Stall speeds VS/VSF are **derived from the maximum lift coefficients "
            "(CLmax)** entered on the **Aerodynamic Data** page — VS = √(295·(W/S)/CLmax) "
            "at the design weight — and set VA and VF. Enter CLmax there."
        )
        alt = st.number_input("Shoulder altitude (ft)", min_value=0.0,
                              value=float(existing.shoulder_altitude_ft) if existing else 0.0,
                              help="Altitude at the 'shoulder' of the flight envelope where VC/VD are evaluated "
                                   "for the cruise/dive Mach limit (MACHLIM, Ch 5).")
        st.subheader("Chosen speeds (blank = use minimum)")
        vc = st.number_input("Chosen cruise VC (kt)", min_value=0.0,
                             value=float(existing.chosen_vc) if existing and existing.chosen_vc else 0.0,
                             help="Design cruising speed VC (KEAS); leave 0 to use the FAR 23.335(a) minimum.")
        vd = st.number_input("Chosen dive VD (kt)", min_value=0.0,
                             value=float(existing.chosen_vd) if existing and existing.chosen_vd else 0.0,
                             help="Design dive speed VD (KEAS); leave 0 to use the FAR 23.335(b) minimum.")

        st.subheader("Concept load factors (used only when Category = Concept (C))")
        st.caption("No FAR 23.337 cap is applied to the Concept category — you set the limit maneuver factors.")
        chosen_n = st.number_input("Limit positive load factor n", min_value=0.0,
                                   value=float(existing.chosen_n) if existing and existing.chosen_n else 0.0,
                                   help="Concept-category limit positive maneuvering load factor (replaces the "
                                        "FAR 23.337 formula; used only when Category = Concept).")
        chosen_nneg = st.number_input("Limit negative load factor n_neg", max_value=0.0,
                                      value=float(existing.chosen_nneg) if existing and existing.chosen_nneg else 0.0,
                                      help="Concept-category limit negative load factor (≤ 0; used only when "
                                           "Category = Concept).")
        applied = st.form_submit_button("Apply", type="primary")

    if applied:
        is_concept_submit = _CATS[cat_label] == "C"
        weight_imperial = to_imperial_scalar(weight_override, "weight", system)
        weight = weight_imperial if (override_weight or not has_weight_db) else mtow_upstream
        wing_area_imperial = to_imperial_scalar(wing_area, "area_sqft", system) if wing_area else None
        inp = StructuralSpeedsInput(
            category=_CATS[cat_label],
            weight_lb=weight,
            occupants=int(occupants_in) if occupants_in else None,
            wing_area_sqft=wing_area_imperial,
            vh_kt=vh,
            shoulder_altitude_ft=alt,
            chosen_vc=vc or None,
            chosen_vd=vd or None,
            chosen_n=chosen_n if is_concept_submit else None,
            chosen_nneg=chosen_nneg if is_concept_submit else None,
        )
        # Preserve any existing MACHLIM sub-slice owned by the other tab.
        inp.mach_limit = existing.mach_limit if existing else None
        project.speeds = inp
        st.session_state["project"] = project
        existing = inp

    if existing is None:
        st.info("No structural-speeds inputs yet -- fill in the form and Apply.")
        return
    inp = existing

    if inp.category == "C":
        st.warning(
            "Concept category (C): results are an **unverified extrapolation** beyond "
            "the FAR 23 ≤12,500 lb calibration band. The statistical weight estimate is "
            "a sanity figure only — use the itemized weight data base as the design weight."
        )

    try:
        results = design_speeds(project, inp)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not compute structural speeds: {exc}")
        workflow_page_link("aero_coefficients", label="→ Set CLmax on Aerodynamic Data",
                           icon="🛩️")
        return

    for r in results:
        with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
            rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            if r.note:
                st.caption(r.note)

    st.divider()
    st.caption(
        "📈 See the **Speed–Altitude Envelope** tab for the Mach-limited flight-limits "
        "diagram, and the **Flight Envelope (V-n)** page for the V-n diagram built from "
        "these speeds and load factors."
    )
    st.download_button(
        "Download structural speeds (CSV)", farloads_io.load_cases_csv(results),
        file_name="structural_speeds.csv", mime="text/csv", key="dl_speeds_csv")
    st.download_button(
        "Download structural speeds (text)", module_text_report("Structural design speeds", results),
        file_name="structural_speeds.txt", mime="text/plain", key="dl_speeds_txt")


# --------------------------------------------------------------------------- #
# Tab 2 -- Speed–Altitude Envelope (MACHLIM)
# --------------------------------------------------------------------------- #
def _tab_speed_altitude(project: Project, system: UnitSystem, U: dict) -> None:
    existing = project.speeds.mach_limit if project.speeds and project.speeds.mach_limit else None

    # MC/MD/shoulder are computed by the Design Speeds tab (design_speed_values);
    # read them from there instead of re-asking.
    ds = None
    if project.speeds is not None and project.speeds.weight_lb > 0:
        try:
            ds = design_speed_values(project, project.speeds)
        except (ValueError, ZeroDivisionError):
            ds = None

    if ds is not None:
        mc, md = ds.mc, ds.md
        shoulder = project.speeds.shoulder_altitude_ft
    elif existing is not None:
        mc, md, shoulder = existing.mc, existing.md, existing.shoulder_altitude_ft
    else:
        st.info(
            "No design speeds yet. Enter the design weight, stall speeds and shoulder "
            "altitude on the **Design Speeds** tab first — MC, MD and the shoulder "
            "altitude are read from there."
        )
        return

    st.caption(
        f"From Design Speeds — MC **{mc:.4f}**, MD **{md:.4f}**, "
        f"shoulder **{shoulder:,.0f} ft**."
    )
    # Form + Apply (M2-3): the MACHLIM inputs persist only on submit, so merely
    # visiting this tab no longer mutates the project and trips the dirty flag.
    with st.form("mach_limit_form"):
        max_alt = st.number_input(
            "Max operating altitude (ft)", min_value=0.0,
            value=float(existing.max_operating_altitude_ft) if existing else 18000.0,
            help="Ceiling of the flight-limits diagram; the Mach-limited table runs from "
                 "the shoulder altitude up to here (MACHLIM, Ch 6).",
        )
        incr = st.number_input(
            "Altitude increment (ft)", min_value=1.0,
            value=float(existing.increment_ft) if existing else 1000.0,
            help="Tabulation / plotting step for the Mach-limited airspeeds.",
        )
        applied = st.form_submit_button("Apply", type="primary")

    axis_unit = st.radio(
        "Chart speed axis", ["KEAS", "KCAS", "KTAS"], horizontal=True,
        help="Equivalent (native calc unit), calibrated (compressibility-corrected, "
             "the placard convention) or true airspeed for the diagram's x-axis. "
             "Boundaries are computed in KEAS and converted at the altitude of each point.",
    )

    inp = MachLimitInput(
        mc=mc, md=md, shoulder_altitude_ft=shoulder,
        max_operating_altitude_ft=max_alt, increment_ft=incr,
    )
    # Persist into the speeds slice only on Apply (creating it if the Design Speeds
    # tab has not run). The chart below always renders live from the local `inp`.
    if applied:
        speeds = project.speeds or StructuralSpeedsInput()
        speeds.mach_limit = inp
        project.speeds = speeds
        st.session_state["project"] = project

    try:
        results = mach_limit_lines(inp)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not compute the Mach-limit lines: {exc}")
        return

    summary, *lines = results
    mne, mfc = 0.9 * md, 1.2 * md
    with st.expander(f"FAR {summary.far_reference} — {summary.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in summary.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(summary.note)

    table = [{v.label: v.value for v in line.values} for line in lines]
    st.subheader("Mach-limited equivalent airspeeds")
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")

    def _altitude_grid(top_ft: float, step_ft: float) -> list:
        """Sea level up to ``top_ft`` in ``step_ft`` steps, with the shoulder and the
        ceiling always present so the boundary kink lands exactly on the shoulder."""
        marks = {0.0, shoulder, top_ft}
        h = 0.0
        while h < top_ft:
            marks.add(h)
            h += step_ft
        return sorted(a for a in marks if a <= top_ft)

    def _boundary(alts, unit, eas_below=None, mach_above=None, only_above=False):
        """Speed at each altitude in ``unit``: constant-EAS below the shoulder,
        Mach-limited (M*a*sqrt(sigma)) above it."""
        xs, ys = [], []
        for h in alts:
            above = h >= shoulder
            if above and mach_above is not None:
                a, sigma = standard_atmosphere(h)
                eas = mach_to_eas(mach_above, a, sigma)
            elif not only_above and eas_below is not None:
                eas = eas_below
            else:
                continue
            xs.append(convert_airspeed(eas, h, unit))
            ys.append(h)
        return xs, ys

    st.subheader("Speed–altitude flight-limits diagram")
    st.caption(
        f"Altitude vs **{axis_unit}**. Design speeds are EAS-limited (constant) below the "
        f"{shoulder:,.0f} ft shoulder and Mach-limited above it; thin grey lines are "
        "constant Mach. All speeds are ULTIMATE-independent design *limit* speeds."
    )

    alts = _altitude_grid(max_alt, incr)
    fig = go.Figure()

    # Constant-Mach fan (thin grey reference lines), 0.10 up to just past MFC.
    mach_top = mfc + 0.05
    m = 0.10
    fan = []
    while m <= mach_top + 1e-9:
        fan.append(round(m, 2))
        m += 0.05
    for mval in fan:
        xs = [convert_airspeed(mach_to_eas(mval, *standard_atmosphere(h)), h, axis_unit) for h in alts]
        ys = list(alts)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line=dict(color="lightgray", width=1),
            name=f"M {mval:.2f}", showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(x=xs[-1], y=ys[-1], text=f"{mval:.2f}", showarrow=False,
                           font=dict(size=9, color="gray"), yshift=6)

    # Operating boundary: design speeds (EAS below shoulder, Mach-limited above).
    _BOUNDS = [
        ("VA / manoeuvre", ds.va if ds else None, None, "#2ca02c"),
        ("VC / MC", ds.vc if ds else None, mc, "#1f77b4"),
        ("VD / MD", ds.vd if ds else None, md, "#d62728"),
        ("VF / flap", ds.vf if ds else None, None, "#9467bd"),
    ]
    for name, eas_below, mach_above, color in _BOUNDS:
        if eas_below is None:
            continue
        xs, ys = _boundary(alts, axis_unit, eas_below=eas_below, mach_above=mach_above)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name,
                                 line=dict(color=color, width=3)))

    # Mach-only lines above the shoulder: never-exceed (MNE) and flutter (MFC).
    for name, mval, color, dash in [("V(MNE)", mne, "#ff7f0e", "dot"), ("V(MFC)", mfc, "#8c564b", "dash")]:
        xs, ys = _boundary(alts, axis_unit, mach_above=mval, only_above=True)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name,
                                 line=dict(color=color, width=2, dash=dash)))

    fig.add_hline(y=shoulder, line_dash="dot", line_color="gray",
                  annotation_text="shoulder", annotation_position="left")
    fig.add_hline(y=max_alt, line_dash="dot", line_color="gray",
                  annotation_text="max operating", annotation_position="left")
    fig.update_layout(
        xaxis_title=f"Speed ({axis_unit})", yaxis_title="Altitude (ft)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=560, margin=dict(t=40),
    )
    st.plotly_chart(fig, width="stretch")

    st.download_button(
        "Download Mach-limit lines (CSV)", farloads_io.load_cases_csv(results),
        file_name="mach_limit.csv", mime="text/csv", key="dl_mach_csv")
    st.download_button(
        "Download Mach-limit lines (text)", module_text_report("Mach limit lines", results),
        file_name="mach_limit.txt", mime="text/plain", key="dl_mach_txt")


_tab_speeds, _tab_machlim = st.tabs(["Design Speeds", "Speed–Altitude Envelope"])
with _tab_speeds:
    _tab_design_speeds(project, system, U)
with _tab_machlim:
    _tab_speed_altitude(project, system, U)
