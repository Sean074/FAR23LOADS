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
so a missing-prerequisite guard can ``return`` without ``stop_page()`` killing the
sibling tab.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_shell.components import (
    ALTITUDE_FT,
    KEAS,
    page_header,
    render_consistency_warnings,
    unit_number_input,
    workflow_page_link,
)
from app_shell.widget_keys import widget_key
from sloads import (
    CATEGORIES,
    MachLimitInput,
    Project,
    StructuralSpeedsInput,
    UnitSystem,
    VdBasis,
    convert_results,
    to_display,
)
from sloads import io as sloads_io
from sloads.constants import convert_airspeed, mach_to_eas, standard_atmosphere
from sloads.modules.mach_limit import mach_limit_lines
from sloads.modules.structural_speeds import (
    MACH_MARGIN_DEFAULT,
    MACH_MARGIN_FLOOR,
    design_speed_values,
    design_speeds,
    operational_implications,
)
from sloads.report import LoadChannel, module_text_report

project, system, U = page_header("structural_speeds", title="Structural Design Speeds — FAR 23")
st.caption(
    "Limit maneuver load factors and design airspeeds (VA, VC, VD, VF) with their "
    "FAR minimums (STRSPEED), plus the Mach-limited speed–altitude flight-limits "
    "diagram (MACHLIM). All speeds are KEAS; altitudes are feet."
)


# The category codes and their meanings have one owner, ``models.CATEGORIES``
# (#63): this view and the oracle form offer the same table.
_CAT_LABELS = list(CATEGORIES)

# The two 25.335(b) dive-speed routes, as the radio presents them (F25-2).
_VD_BASIS = {
    "Speed ratio (VD \u2265 1.25\u00b7VC)": VdBasis.SPEED_RATIO,
    "Mach margin (MD \u2265 MC + margin)": VdBasis.MACH_MARGIN,
}
_VD_BASIS_LABELS = list(_VD_BASIS)
_VD_BASIS_LABEL = {v: k for k, v in _VD_BASIS.items()}


# --------------------------------------------------------------------------- #
# Tab 1 -- Design Speeds (STRSPEED)
# --------------------------------------------------------------------------- #
def _tab_design_speeds(project: Project, system: UnitSystem, U: dict) -> None:
    # This page's warnings are rendered once, above the tabs, by ``page_header``.
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

    with st.expander("ℹ️ How the design speeds bound the operating limitations", expanded=False):
        st.markdown(
            "The **design speeds** here (Subpart C) set the ceiling for the **operating "
            "limitations / cockpit placards** established at certification (Subpart G). The "
            "constraint ladder:\n\n"
            "- **VNE** (never-exceed) = **0.9·VD**; **MNE** = 0.9·MD "
            "(14 CFR 23.1505(a); Ref 1 p47). The band VC→VNE is the airspeed-indicator "
            "**yellow arc**.\n"
            "- **VNO** (max structural cruising) = **min(VC, 0.89·VNE)** (23.1505(b)).\n"
            "- **VFE** (flap extended) ≤ **VF** (23.1511).\n"
            "- **Turbine airplanes** (and any airplane whose VD is set by the 25.335(b)(2) / "
            "23.335(b)(4) Mach-margin route) have **no yellow arc**: the max operating speed "
            "**VMO/MMO ≤ VC/MC**, with a margin of **≥ 0.07 Mach** between MC and MD "
            "(25.335(b)(2) since Amdt 25-91; 23.335(b)(4)(iii) commuter). Below 0.07 M "
            "needs a rational analysis crediting automatic systems; **0.05 M is an "
            "absolute floor**.\n"
            "\n"
            "The advisory panel below derives these preliminary placards from your design "
            "speeds. Set optional **operational targets** in the form to check feasibility "
            "(e.g. a target VNE requires VD ≥ VNE/0.9). Operating limitations are fixed at "
            "certification, not by this tool — targets never change any design speed or load."
        )

    existing = project.speeds

    # WTESTIMA design seat count seeds the occupants default (seed-chain).
    seats_upstream = (
        project.weight.estimation.seats
        if project.weight is not None and project.weight.estimation is not None else 0
    )
    has_wing = project.geometry is not None and project.geometry.by_name(
        existing.wing_surface if existing else "wing") is not None
    # Design weight: read-through from the MTOW SSOT (decision G-14) so it is not
    # entered twice. It was the item-database total until 2026-08-15 -- the ceiling
    # of OEW <= MLW <= MTOW <= sum(items), not a design weight, and 964 lb / 1,800
    # lb above MTOW on two shipped fixtures. Read as the SSOT *field* rather than
    # through cg_cases.max_takeoff_weight, whose compat fallback starts at
    # speeds.weight_lb -- this page's own input, so the read-through would show the
    # user their own number as an upstream value and hide the field behind the
    # override checkbox.
    mtow_upstream = (project.weight.max_takeoff_weight_lb
                     if project.weight is not None else 0.0)
    has_mtow = mtow_upstream > 0

    with st.form("structural_speeds_form"):
        st.caption(
            f"Input units: **{'Imperial' if system == UnitSystem.IMPERIAL else 'SI'}** "
            "(set in the sidebar's global **Units** control). Airspeed (kt) and "
            "altitude (ft) stay aviation-standard in both systems."
        )
        cat_default = existing.category if existing and existing.category in CATEGORIES else "N"
        cat_label = st.selectbox(
            "Category", _CAT_LABELS, index=_CAT_LABELS.index(cat_default),
            key=widget_key("ss_category"),
            format_func=lambda c: f"{c} · {CATEGORIES[c]}",
            help="Certification category (14 CFR 23.3); sets the limit maneuver load factors (23.337). "
                 "Concept (C) applies no FAR cap — you set the factors below.",
        )

        # Both the DB-read and the override are always rendered (forms don't react
        # live to a checkbox) -- which one wins is decided at Apply.
        if has_mtow:
            mtow_upstream_display = to_display(mtow_upstream, "weight", system)
            st.caption(f"Design weight from the MTOW SSOT: **{mtow_upstream_display:,.0f} {U['weight']}**.")
            override_weight = st.checkbox(
                "Override design weight", value=False, key=widget_key("ss_override_weight"),
                help="Uncheck to use the max take-off weight entered on the Weight "
                     "& Mass Properties page (decision G-14's single owner).",
            )
            weight_default = (
                existing.weight_lb if existing and existing.weight_lb else mtow_upstream
            )
            weight_override = unit_number_input(
                "Design (gross) weight override", float(weight_default),
                kind="weight", key="ss_weight_override", min_value=0.0,
                help="Design gross (take-off) weight used for the load factors and design speeds "
                     "(14 CFR 23.335; STRSPEED, Ch 5). Used only when 'Override design weight' is ticked.",
            )
        else:
            override_weight = True
            weight_default = (
                existing.weight_lb if existing and existing.weight_lb else 0.0
            )
            weight_override = unit_number_input(
                "Design (gross) weight", float(weight_default),
                kind="weight", key="ss_weight", min_value=0.0,
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
            key=widget_key("ss_occupants"),
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
                existing.wing_area_sqft if existing and existing.wing_area_sqft else 0.0
            )
            wing_area = unit_number_input(
                "Wing area S", float(wing_area_default),
                kind="area_sqft", key="ss_wing_area", min_value=0.0,
                help="Reference wing area S; with weight gives the wing loading W/S that sets the stall "
                     "and maneuvering speeds. Read from Geometry when a wing surface exists.",
            )
            st.caption(
                "No wing geometry found. Define the wing on the **Geometry** page, "
                "or enter the wing area directly above."
            )
            workflow_page_link("configuration_layout", label="→ Geometry")
        vh = unit_number_input(
            "Max sea-level speed VH", float(existing.vh_kt) if existing else 0.0,
            fixed_unit=KEAS, key="ss_vh", min_value=0.0,
            help="Maximum speed in level flight at max continuous power, sea level (KEAS); "
                 "a floor for the minimum cruise speed VC (14 CFR 23.335).")
        st.caption(
            "Stall speeds VS/VSF are **derived from the maximum lift coefficients "
            "(CLmax)** entered on the **Aerodynamic Data** page — VS = √(2·(W/S)/(ρ₀·CLmax)) "
            "at the design weight — and set VA and VF. Enter CLmax there."
        )
        # Altitude is feet in both unit systems (D-16's aviation carve-out), so it
        # goes through the explicit non-converted path rather than a hand-typed unit.
        alt = unit_number_input(
            "Shoulder altitude", float(existing.shoulder_altitude_ft) if existing else 0.0,
            fixed_unit=ALTITUDE_FT, key="ss_shoulder_alt", min_value=0.0,
            help="Altitude at the 'shoulder' of the flight envelope where VC/VD are evaluated "
                 "for the cruise/dive Mach limit (MACHLIM, Ch 5).")
        st.subheader("Chosen speeds (blank = use minimum)")
        vc = unit_number_input(
            "Chosen cruise VC", float(existing.chosen_vc) if existing and existing.chosen_vc else 0.0,
            fixed_unit=KEAS, key="ss_vc", min_value=0.0,
            help="Design cruising speed VC (KEAS). Enter a value if you have one; "
                 "0/blank uses the computed FAR 23.335(a) minimum, and a value "
                 "below the minimum is overridden (raised) to it.")
        vd = unit_number_input(
            "Chosen dive VD", float(existing.chosen_vd) if existing and existing.chosen_vd else 0.0,
            fixed_unit=KEAS, key="ss_vd", min_value=0.0,
            help="Design dive speed VD (KEAS). Enter a value if you have one; "
                 "0/blank uses the computed FAR 23.335(b) minimum, and a value "
                 "below the minimum is overridden (raised) to it.")

        # --- Dive-speed basis (F25-2). Concept category only (decision D-1); the
        # widgets always render because a form cannot react live to the category
        # selectbox, and the choice is discarded at Apply outside category C.
        st.subheader("Dive-speed basis (used only when Category = Concept (C))")
        st.caption(
            "14 CFR 25.335(b) offers **two routes**: the speed ratio VC/MC ≤ 0.8·VD/MD "
            "(i.e. VD ≥ 1.25·VC) **or** a minimum Mach margin between MC and MD. The "
            "FAR 23 categories always use the speed ratio; a concept may choose. "
            "The Mach-margin route needs a shoulder altitude and a chosen VD above."
        )
        basis_default = (
            _VD_BASIS_LABEL[existing.vd_basis] if existing else _VD_BASIS_LABELS[0])
        basis_label = st.radio(
            "Dive-speed basis", _VD_BASIS_LABELS,
            index=_VD_BASIS_LABELS.index(basis_default), horizontal=True,
            key=widget_key("ss_vd_basis"),
            help="Speed ratio: today's behaviour, VD is raised to at least 1.25·VC. "
                 "Mach margin: your chosen VD is honoured as long as MD clears "
                 "MC + the margin below, and raised to meet it if not.",
        )
        margin_min = st.number_input(
            "Minimum MC→MD Mach margin", min_value=float(MACH_MARGIN_FLOOR),
            max_value=0.30, step=0.005, format="%.3f", key=widget_key("ss_mach_margin_min"),
            value=float(existing.mach_margin_min) if existing and existing.mach_margin_min
            else float(MACH_MARGIN_DEFAULT),
            help=f"Default {MACH_MARGIN_DEFAULT} M — the 14 CFR 25.335(b)(2) rule "
                 f"figure since Amdt 25-91 (1997). {MACH_MARGIN_FLOOR} M is an "
                 "absolute floor and cannot be entered below.",
        )
        margin_basis = st.text_input(
            "Rational-analysis basis (required below 0.07 M)",
            value=(existing.mach_margin_basis or "") if existing else "",
            key=widget_key("ss_mach_margin_basis"),
            placeholder="e.g. high-speed protection function credited per 25.335(b)(2)",
            help="Free text, recorded with the results. 25.335(b)(2) permits a margin "
                 "below 0.07 M only when it is 'determined using a rational analysis "
                 "that includes the effects of any automatic systems'.",
        )
        if margin_min < MACH_MARGIN_DEFAULT:
            st.warning(
                f"Reducing the MC→MD margin below **{MACH_MARGIN_DEFAULT} M** requires "
                "**significant justification** — a rational analysis including the "
                "effects of automatic systems (14 CFR 25.335(b)(2)) — and **represents "
                "a certification risk**. AC 25.335-1A treats 0.07 M as sufficient "
                "without further investigation; sub-0.07 margins in service are "
                "high-speed-protection-credited and typically remain above 0.06 M. "
                f"{MACH_MARGIN_FLOOR} M is an absolute floor. See "
                "`reference/14CFR_MC_MD_speed_margin.md` §2–3."
            )
        vb = unit_number_input(
            "Rough-air speed VB (optional)",
            float(existing.vb_kt) if existing and existing.vb_kt else 0.0,
            fixed_unit=KEAS, key="ss_vb", min_value=0.0,
            help="Design speed for maximum gust intensity, 14 CFR 25.335(d). Input "
                 "only — it is checked against VC for ordering and never changes a "
                 "design speed or a load. The full VC ≥ VB + 1.32·U_ref margin needs "
                 "the 25.341 reference-gust schedule, which is not yet implemented.",
        )

        st.subheader("Concept load factors (used only when Category = Concept (C))")
        st.caption("No FAR 23.337 cap is applied to the Concept category — you set the limit maneuver factors.")
        chosen_n = st.number_input("Limit positive load factor n", min_value=0.0,
                                   value=float(existing.chosen_n) if existing and existing.chosen_n else 0.0,
                                   key=widget_key("ss_chosen_n"),
                                   help="Concept-category limit positive maneuvering load factor (replaces the "
                                        "FAR 23.337 formula; used only when Category = Concept).")
        chosen_nneg = st.number_input("Limit negative load factor n_neg", max_value=0.0,
                                      value=float(existing.chosen_nneg) if existing and existing.chosen_nneg else 0.0,
                                      key=widget_key("ss_chosen_nneg"),
                                      help="Concept-category limit negative load factor (≤ 0; used only when "
                                           "Category = Concept).")

        st.subheader("Operational targets (optional, advisory)")
        st.caption(
            "Preliminary Subpart-G placard **targets** (14 CFR 23.1505/23.1511). These "
            "**never change** the design speeds or any load — on Apply, each is inverted "
            "into the design minimum it requires and flagged if the chosen speeds fall "
            "short (here and on the dashboard). Leave 0 to skip a target."
        )
        no_yellow_arc = st.checkbox(
            "Turbine / no yellow arc (VMO/MMO govern)",
            value=bool(existing.no_yellow_arc) if existing else False,
            key=widget_key("ss_no_yellow_arc"),
            help="Turbine airplanes (and any airplane with VD set by the 23.335(b)(4) "
                 "Mach-margin route) have no VNE yellow arc; VMO/MMO ≤ VC/MC govern (Ref 1 p47).",
        )
        _oc1, _oc2, _oc3 = st.columns(3)
        with _oc1:
            target_vne = unit_number_input(
                "Target VNE", float(existing.target_vne) if existing and existing.target_vne else 0.0,
                fixed_unit=KEAS, key="ss_target_vne", min_value=0.0,
                help="Desired never-exceed speed; requires VD ≥ VNE/0.9 (23.1505(a)).")
            target_vfe = unit_number_input(
                "Target VFE", float(existing.target_vfe) if existing and existing.target_vfe else 0.0,
                fixed_unit=KEAS, key="ss_target_vfe", min_value=0.0,
                help="Desired flap extended speed; requires VF ≥ VFE (23.1511).")
        with _oc2:
            target_vno = unit_number_input(
                "Target VNO", float(existing.target_vno) if existing and existing.target_vno else 0.0,
                fixed_unit=KEAS, key="ss_target_vno", min_value=0.0,
                help="Desired max structural cruising speed; requires VC ≥ VNO and "
                     "VNE ≥ VNO/0.89 (23.1505(b)).")
            target_vmo = unit_number_input(
                "Target VMO", float(existing.target_vmo) if existing and existing.target_vmo else 0.0,
                fixed_unit=KEAS, key="ss_target_vmo", min_value=0.0,
                help="Turbine max operating speed; requires VC ≥ VMO (Ref 1 p47).")
        with _oc3:
            target_mmo = st.number_input("Target MMO (Mach)", min_value=0.0, format="%.3f",
                                         value=float(existing.target_mmo) if existing and existing.target_mmo else 0.0,
                                         key=widget_key("ss_target_mmo"),
                                         help="Turbine max operating Mach; requires MD ≥ MMO + 0.05 (23.335(b)(4)).")

        applied = st.form_submit_button("Apply", type="primary")

    if applied:
        is_concept_submit = cat_label == "C"
        # unit_number_input already returned Imperial (the whole point of #44):
        # no hand conversion happens on this page any more.
        weight = weight_override if (override_weight or not has_mtow) else mtow_upstream
        wing_area_imperial = wing_area if wing_area else None
        inp = StructuralSpeedsInput(
            category=cat_label,
            weight_lb=weight,
            occupants=int(occupants_in) if occupants_in else None,
            wing_area_sqft=wing_area_imperial,
            vh_kt=vh,
            shoulder_altitude_ft=alt,
            chosen_vc=vc or None,
            chosen_vd=vd or None,
            chosen_n=chosen_n if is_concept_submit else None,
            chosen_nneg=chosen_nneg if is_concept_submit else None,
            # The dive-speed basis is concept-only (D-1): a FAR 23 category always
            # persists the speed-ratio route, so switching category cannot leave a
            # project holding a basis its category refuses to run.
            vd_basis=(_VD_BASIS[basis_label] if is_concept_submit else VdBasis.SPEED_RATIO),
            mach_margin_min=(margin_min if is_concept_submit
                             and _VD_BASIS[basis_label] is VdBasis.MACH_MARGIN
                             and margin_min != MACH_MARGIN_DEFAULT else None),
            mach_margin_basis=(margin_basis.strip() or None) if is_concept_submit else None,
            vb_kt=vb or None,
            no_yellow_arc=bool(no_yellow_arc),
            target_vne=target_vne or None,
            target_vno=target_vno or None,
            target_vmo=target_vmo or None,
            target_mmo=target_mmo or None,
            target_vfe=target_vfe or None,
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

    # The margin route's headline numbers, up front rather than buried in the
    # condition note: which route ran, what it achieved, and what the other route
    # would have imposed (F25-2).
    if inp.vd_basis is VdBasis.MACH_MARGIN:
        _ds = design_speed_values(project, inp)
        _c1, _c2, _c3 = st.columns(3)
        _c1.metric("VD (Mach-margin route)", f"{_ds.vd:,.1f} kt",
                   delta=f"{_ds.vd - _ds.vd_ratio_floor:+,.1f} kt vs 1.25·VC",
                   delta_color="off")
        _c2.metric("MD − MC margin", f"{_ds.mach_margin:.4f}",
                   delta=f"required {_ds.mach_margin_required:.4f}", delta_color="off")
        _c3.metric("MC / MD", f"{_ds.mc:.4f} / {_ds.md:.4f}")

    for r in results:
        with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
            rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            if r.note:
                st.caption(r.note)

    # Operating-limitation implications (M2-10): read-only advisory placards +
    # optional operational-target feasibility. Never changes a design speed or load.
    st.divider()
    st.subheader("Operating-limitation implications (advisory)")
    try:
        op_results = operational_implications(project, inp)
    except (ValueError, ZeroDivisionError):
        op_results = []
    for r in op_results:
        with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
            rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            if r.note:
                st.caption(r.note)
    # Deliberately re-stated here beside the placards it bears on, as well as at
    # the top of the page: this is the one warning whose subject *is* this tab.
    render_consistency_warnings(project, "structural_speeds",
                                only_codes={"operational_target_infeasible"})

    st.divider()
    st.caption(
        "📈 See the **Speed–Altitude Envelope** tab for the Mach-limited flight-limits "
        "diagram, and the **Flight Envelope (V-n)** page for the V-n diagram built from "
        "these speeds and load factors."
    )
    st.download_button(
        "Download structural speeds (CSV)",
        sloads_io.load_cases_csv(results, system=system, channel=LoadChannel.LIMIT),
        file_name="structural_speeds.csv", mime="text/csv", key="dl_speeds_csv")
    st.download_button(
        "Download structural speeds (text)", module_text_report("Structural design speeds",
                           convert_results(results, system), channel=LoadChannel.LIMIT),
        file_name="structural_speeds.txt", mime="text/plain", key="dl_speeds_txt")


# --------------------------------------------------------------------------- #
# Tab 2 -- Speed–Altitude Envelope (MACHLIM)
# --------------------------------------------------------------------------- #
def _tab_speed_altitude(project: Project, system: UnitSystem, U: dict) -> None:  # noqa: ARG001  -- uniform tab signature
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
    else:
        # There is no stored MC/MD to fall back on any more (F25-2): the pair used
        # to live on the MACHLIM slice too, and the two copies disagreed.
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
        max_alt = unit_number_input(
            "Max operating altitude",
            float(existing.max_operating_altitude_ft) if existing else 18000.0,
            fixed_unit=ALTITUDE_FT, key="ml_max_alt", min_value=0.0,
            help="Ceiling of the flight-limits diagram; the Mach-limited table runs from "
                 "the shoulder altitude up to here (MACHLIM, Ch 6).",
        )
        incr = unit_number_input(
            "Altitude increment",
            float(existing.increment_ft) if existing else 1000.0,
            fixed_unit=ALTITUDE_FT, key="ml_incr", min_value=1.0,
            help="Tabulation / plotting step for the Mach-limited airspeeds.",
        )
        applied = st.form_submit_button("Apply", type="primary")

    axis_unit = st.radio(
        "Chart speed axis", ["KEAS", "KCAS", "KTAS"], horizontal=True,
        key=widget_key("ml_axis_unit"),
        help="Equivalent (native calc unit), calibrated (compressibility-corrected, "
             "the placard convention) or true airspeed for the diagram's x-axis. "
             "Boundaries are computed in KEAS and converted at the altitude of each point.",
    )

    # The shoulder altitude is not a MACHLIM field any more (v55, #52): the
    # table starts at the one altitude MC/MD were derived at, read above.
    inp = MachLimitInput(max_operating_altitude_ft=max_alt, increment_ft=incr)
    # Persist into the speeds slice only on Apply (creating it if the Design Speeds
    # tab has not run). The chart below always renders live from the local `inp`.
    if applied:
        speeds = project.speeds or StructuralSpeedsInput()
        speeds.mach_limit = inp
        project.speeds = speeds
        st.session_state["project"] = project

    try:
        results = mach_limit_lines(inp, mc, md, shoulder)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not compute the Mach-limit lines: {exc}")
        return

    summary, *lines = results
    mne = 0.9 * md
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

    # Constant-Mach fan (thin grey reference lines), 0.10 up to just past the
    # highest boundary drawn. That was MFC (1.2*MD) until flutter clearance left
    # the tool (#79), so the fan now reaches 0.05 past MD -- narrower, and no
    # longer reserving room for a line nothing draws.
    mach_top = md + 0.05
    m = 0.10
    fan = []
    while m <= mach_top + 1e-9:
        fan.append(round(m, 2))
        m += 0.05
    for mval in fan:
        xs = [convert_airspeed(mach_to_eas(mval, *standard_atmosphere(h)), h, axis_unit) for h in alts]
        ys = list(alts)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line={"color": "lightgray", "width": 1},
            name=f"M {mval:.2f}", showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(x=xs[-1], y=ys[-1], text=f"{mval:.2f}", showarrow=False,
                           font={"size": 9, "color": "gray"}, yshift=6)

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
                                 line={"color": color, "width": 3}))

    # Mach-only lines above the shoulder: never-exceed (MNE). V(MFC) was drawn
    # here too until #79 removed flutter clearance (23.629) from the tool.
    for name, mval, color, dash in [("V(MNE)", mne, "#ff7f0e", "dot")]:
        xs, ys = _boundary(alts, axis_unit, mach_above=mval, only_above=True)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name,
                                 line={"color": color, "width": 2, "dash": dash}))

    fig.add_hline(y=shoulder, line_dash="dot", line_color="gray",
                  annotation_text="shoulder", annotation_position="left")
    fig.add_hline(y=max_alt, line_dash="dot", line_color="gray",
                  annotation_text="max operating", annotation_position="left")
    fig.update_layout(
        xaxis_title=f"Speed ({axis_unit})", yaxis_title="Altitude (ft)",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        height=560, margin={"t": 40},
    )
    st.plotly_chart(fig, width="stretch")

    st.download_button(
        "Download Mach-limit lines (CSV)",
        sloads_io.load_cases_csv(results, system=system, channel=LoadChannel.LIMIT),
        file_name="mach_limit.csv", mime="text/csv", key="dl_mach_csv")
    st.download_button(
        "Download Mach-limit lines (text)", module_text_report("Mach limit lines", convert_results(results, system),
                                                    channel=LoadChannel.LIMIT),
        file_name="mach_limit.txt", mime="text/plain", key="dl_mach_txt")


_tab_speeds, _tab_machlim = st.tabs(["Design Speeds", "Speed–Altitude Envelope"])
with _tab_speeds:
    _tab_design_speeds(project, system, U)
with _tab_machlim:
    _tab_speed_altitude(project, system, U)
