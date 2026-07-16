"""Streamlit page for the airplane-less-tail aero coefficients (Project.aero_coeffs).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Owns the ``Project.aero_coeffs`` slice (Step D4.1): the Ch 7 aero-coefficients
program's output, cruise (flaps up) and an optional flaps-down (landing) set,
that the Flight Envelope page (FLTLOADS) balances against but no longer edits
(Step D4.2 — this page replaces the interim editor that lived there).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import AeroCoefficientsInput, AeroCoeffSet, Project

st.title("Aerodynamic Data")
st.caption(
    "Airplane-less-tail aerodynamic coefficient sets (Ch 7 aero-coefficients "
    "program output) that the Flight Envelope page (FLTLOADS) balances against: "
    "CL = C0 + C1·α + C2·α² + C3·α³ + C4·α⁴ (α in deg); CD = D0 + D1·CL + … ; "
    "CM = M0 + M1·α + … . Cruise is balanced at every altitude in the flight "
    "envelope; flaps-down is balanced at sea level only (FLTLOADS.BAS line 3000)."
)
st.caption(
    "This page holds the airplane-less-tail balance coefficients. Each lifting "
    "surface's spanwise (Schrenk) aero -- lift-curve slope, twist, target CL, "
    "profile drag, section CM -- is entered on the Wing Loads page (Analysis "
    "phase), next to the load distribution it drives."
)

project: Project = st.session_state.get("project", Project(name=""))
aero = project.aero_coeffs

with st.expander("ℹ️ Parameter guide", expanded=False):
    st.markdown(
        "The airplane-less-tail balance coefficients the Flight Envelope page (FLTLOADS) balances against "
        "(Ch 7 aero-coefficients program):\n\n"
        "- **lift (CL vs α)** — polynomial `CL = C0 + C1·α + C2·α² + C3·α³ + C4·α⁴`, with α in **degrees**. "
        "C0 is the zero-α lift; C1 is the lift-curve slope (per deg).\n"
        "- **drag (CD vs CL)** — polynomial `CD = D0 + D1·CL + D2·CL² + …` (a drag polar in CL).\n"
        "- **moment (CM vs α)** — polynomial `CM = M0 + M1·α + …` (pitching-moment coefficient).\n"
        "- **Stall CL / negative stall CL** — the positive and negative maximum lift coefficients that cap "
        "the balancing solution.\n\n"
        "**Cruise** is balanced at every altitude in the flight envelope; **Flaps down (landing)** is "
        "balanced at sea level only (FLTLOADS.BAS line 3000)."
    )


def _coeff_table(existing) -> pd.DataFrame:
    zero = (0.0,) * 5
    lift = existing.lift if existing else zero
    drag = existing.drag if existing else zero
    moment = existing.moment if existing else zero
    return pd.DataFrame(
        {
            "row": ["lift (CL vs α)", "drag (CD vs CL)", "moment (CM vs α)"],
            "0": [lift[0], drag[0], moment[0]],
            "1": [lift[1], drag[1], moment[1]],
            "2": [lift[2], drag[2], moment[2]],
            "3": [lift[3], drag[3], moment[3]],
            "4": [lift[4], drag[4], moment[4]],
        }
    )


def _row(df: pd.DataFrame, label: str) -> tuple:
    r = df[df["row"] == label].iloc[0]
    return tuple(float(r[str(i)]) for i in range(5))


with st.form("aero_coefficients_form"):
    st.subheader("Cruise (flaps up)")
    cruise_name = st.text_input(
        "Configuration name", value=aero.cruise.name if aero and aero.cruise else "CRUISE",
        key="cruise_name", help="Label for the cruise (flaps-up) coefficient set.",
    )
    cruise_df = st.data_editor(
        _coeff_table(aero.cruise if aero else None), hide_index=True,
        use_container_width=True, disabled=["row"], key="cruise_coeff",
    )
    c1, c2 = st.columns(2)
    cruise_stall = c1.number_input(
        "Stall CL", value=float(aero.cruise.stall_cl) if aero and aero.cruise else 0.0,
        format="%.3f", key="cruise_stall",
        help="Positive maximum lift coefficient (flaps up); caps the positive balancing solution.",
    )
    cruise_neg_stall = c2.number_input(
        "Negative stall CL",
        value=float(aero.cruise.neg_stall_cl) if aero and aero.cruise else 0.0,
        format="%.3f", key="cruise_neg_stall",
        help="Negative maximum lift coefficient (flaps up); caps the negative balancing solution.",
    )

    st.divider()
    include_flaps_down = st.checkbox(
        "Include a flaps-down (landing) configuration",
        value=bool(aero and aero.flaps_down is not None),
        help="Add a second coefficient set for the landing configuration, balanced at sea level only "
             "(FLTLOADS.BAS line 3000).",
    )
    st.subheader("Flaps down (landing)")
    st.caption("Ignored unless the checkbox above is ticked.")
    flaps_name = st.text_input(
        "Configuration name", value=aero.flaps_down.name if aero and aero.flaps_down else "LANDING",
        key="flaps_name", help="Label for the flaps-down (landing) coefficient set.",
    )
    flaps_df = st.data_editor(
        _coeff_table(aero.flaps_down if aero else None), hide_index=True,
        use_container_width=True, disabled=["row"], key="flaps_coeff",
    )
    c3, c4 = st.columns(2)
    flaps_stall = c3.number_input(
        "Stall CL", value=float(aero.flaps_down.stall_cl) if aero and aero.flaps_down else 0.0,
        format="%.3f", key="flaps_stall",
        help="Positive maximum lift coefficient (flaps down); caps the positive balancing solution.",
    )
    flaps_neg_stall = c4.number_input(
        "Negative stall CL",
        value=float(aero.flaps_down.neg_stall_cl) if aero and aero.flaps_down else 0.0,
        format="%.3f", key="flaps_neg_stall",
        help="Negative maximum lift coefficient (flaps down); caps the negative balancing solution.",
    )

    applied = st.form_submit_button("Apply", type="primary")

if applied:
    cruise = AeroCoeffSet(
        name=cruise_name or "CRUISE", stall_cl=cruise_stall, neg_stall_cl=cruise_neg_stall,
        lift=_row(cruise_df, "lift (CL vs α)"), drag=_row(cruise_df, "drag (CD vs CL)"),
        moment=_row(cruise_df, "moment (CM vs α)"), flaps_down=False,
    )
    flaps = None
    if include_flaps_down:
        flaps = AeroCoeffSet(
            name=flaps_name or "LANDING", stall_cl=flaps_stall, neg_stall_cl=flaps_neg_stall,
            lift=_row(flaps_df, "lift (CL vs α)"), drag=_row(flaps_df, "drag (CD vs CL)"),
            moment=_row(flaps_df, "moment (CM vs α)"), flaps_down=True,
        )
    # This page owns the whole aero_coeffs slice, so a wholesale replace on
    # Apply is correct here (unlike a slice shared with other pages/edits).
    project.aero_coeffs = AeroCoefficientsInput(cruise=cruise, flaps_down=flaps)
    st.session_state["project"] = project
    st.success("Aero coefficients applied.")
    aero = project.aero_coeffs

if aero is None or (aero.cruise is None and aero.flaps_down is None):
    st.info("No aero coefficients defined yet — fill in the cruise set above and Apply.")
    st.stop()

st.subheader("Current coefficients")


def _summary(name: str, cfg: AeroCoeffSet) -> None:
    st.markdown(f"**{name} — {cfg.name}**")
    st.dataframe(_coeff_table(cfg), hide_index=True, use_container_width=True)
    st.caption(f"Stall CL {cfg.stall_cl:.3f} / negative stall CL {cfg.neg_stall_cl:.3f}")


if aero.cruise is not None:
    _summary("Cruise", aero.cruise)
if aero.flaps_down is not None:
    _summary("Flaps down", aero.flaps_down)
