"""Streamlit page for FAR 23 structural design speeds (port of STRSPEED.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Choose the certification category and enter the design weight, stall speeds and
chosen design speeds (KEAS). The wing area is read from the Wing Geometry page's
wing surface when present, else entered here. Reports the limit maneuver load
factors (FAR 23.337), the design speeds (FAR 23.335) and the cruise/dive Mach at
the shoulder altitude. All speeds are knots equivalent airspeed.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import render_applicability_banner

from farloads import (
    Project,
    StructuralSpeedsInput,
    UnitSystem,
    consistency_warnings,
    labels_for,
    to_display,
    to_imperial_scalar,
)
from farloads import io as farloads_io
from farloads.modules.structural_speeds import design_speeds
from farloads.report import module_text_report


st.title("Structural Design Speeds — FAR 23")
st.caption(
    "Python/Streamlit port of STRSPEED.BAS (Hal C. McMaster). Limit maneuver load "
    "factors and design airspeeds (VA, VC, VD, VF) with their FAR minimums."
)

project: Project = st.session_state.get("project", Project(name=""))
render_applicability_banner(project)
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

# WTESTIMA design seat count seeds the occupants default (seed-chain) when the
# user has not set an explicit occupant count for the FAR 23 seat-limit check.
seats_upstream = (
    project.weight.estimation.seats
    if project.weight is not None and project.weight.estimation is not None else 0
)

system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)  # {"weight","area_sqft",...} -> unit string

_CATS = {"Normal / commuter": "N", "Utility": "U", "Acrobatic": "A", "Concept (C)": "C"}
_CAT_LABELS = list(_CATS)

has_wing = project.geometry is not None and project.geometry.by_name(
    existing.wing_surface if existing else "wing") is not None

# Design weight: read-through from the Weight DB (Step D4.4) so it is not
# entered twice -- once here, once on Weight, CG & Inertia. An explicit
# override checkbox covers the (rare) case a page needs a different weight
# than the itemized total, per the original program's own entry point.
mtow_upstream = project.weight.direct_totals()[0] if project.weight and project.weight.items else 0.0
has_weight_db = mtow_upstream > 0

with st.sidebar:
    st.header(f"Inputs ({U['weight']} / KEAS)")
    st.caption(
        f"Input units: **{'Imperial' if system == UnitSystem.IMPERIAL else 'SI'}** "
        "(set in the sidebar's global **Units** control, above). Airspeed (kt) and "
        "altitude (ft) stay aviation-standard in both systems."
    )
    with st.form("structural_speeds_form"):
        cat_default = next((k for k, v in _CATS.items() if existing and v == existing.category), "Normal / commuter")
        cat_label = st.selectbox(
            "Category", _CAT_LABELS, index=_CAT_LABELS.index(cat_default),
            help="Certification category (14 CFR 23.3); sets the limit maneuver load factors (23.337). "
                 "Concept (C) applies no FAR cap — you set the factors below.",
        )

        # Both the DB-read and the override are always rendered (forms don't
        # react live to a checkbox) -- which one wins is decided at Apply.
        if has_weight_db:
            mtow_upstream_display = to_display(mtow_upstream, "weight", system)
            st.caption(f"Design weight from the Weight DB: **{mtow_upstream_display:,.0f} {U['weight']}**.")
            override_weight = st.checkbox(
                "Override design weight", value=False,
                help="Uncheck to use the Weight DB total (Weight, CG & Inertia page).",
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
                "No weight data base found. Add items on the **Weight, CG & Inertia** "
                "page, or enter the design weight directly above."
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
            st.caption("Wing area read from the Wing Geometry page.")
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
                     "and maneuvering speeds. Read from Wing Geometry when a wing surface exists.",
            )
            st.caption(
                "No wing geometry found. Define the wing on the **Configuration & "
                "Layout** or **Wing Geometry** page, or enter the wing area directly above."
            )
        vh = st.number_input("Max sea-level speed VH (kt)", min_value=0.0,
                             value=float(existing.vh_kt) if existing else 0.0,
                             help="Maximum speed in level flight at max continuous power, sea level (KEAS); "
                                  "a floor for the minimum cruise speed VC (14 CFR 23.335).")
        vs = st.number_input("Stall speed, flaps up VS (kt)", min_value=0.0,
                             value=float(existing.stall_clean_kt) if existing else 0.0,
                             help="Clean (flaps-up) stall speed VS (KEAS); sets VA and the positive-manoeuvre "
                                  "corner of the V-n envelope (14 CFR 23.335).")
        vsf = st.number_input("Stall speed, flaps down VSF (kt)", min_value=0.0,
                              value=float(existing.stall_flap_kt) if existing else 0.0,
                              help="Flaps-down (landing) stall speed VSF (KEAS); sets the flap design speed VF.")
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
        stall_clean_kt=vs,
        stall_flap_kt=vsf,
        shoulder_altitude_ft=alt,
        chosen_vc=vc or None,
        chosen_vd=vd or None,
        chosen_n=chosen_n if is_concept_submit else None,
        chosen_nneg=chosen_nneg if is_concept_submit else None,
    )
    project.speeds = inp
    st.session_state["project"] = project
    existing = inp

if existing is None:
    st.info("No structural-speeds inputs yet -- fill in the sidebar and Apply.")
    st.stop()
inp = existing
is_concept = inp.category == "C"

if is_concept:
    st.warning(
        "Concept category (C): results are an **unverified extrapolation** beyond "
        "the FAR 23 ≤12,500 lb calibration band. The statistical weight estimate is "
        "a sanity figure only — use the itemized weight data base as the design weight."
    )

try:
    results = design_speeds(project, inp)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute structural speeds: {exc}")
    st.stop()

for r in results:
    with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
        rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        if r.note:
            st.caption(r.note)

# The V-n diagram lives on the Flight Envelope (V-n) page, where the continuous
# LIMIT design envelope built from these design speeds/load factors is overlaid on
# the rigorous, Mach-corrected balanced corner points (Step E6 consolidation).
st.divider()
st.caption(
    "📈 See the **Flight Envelope (V-n)** page for the V-n diagram: the continuous "
    "LIMIT design envelope built from these speeds and load factors, overlaid on "
    "the rigorous Mach-corrected balanced corner points."
)

st.download_button(
    "Download structural speeds (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="structural_speeds.csv",
    mime="text/csv",
)
st.download_button(
    "Download structural speeds (text)",
    module_text_report("Structural design speeds", results),
    file_name="structural_speeds.txt",
    mime="text/plain",
)
