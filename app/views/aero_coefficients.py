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

from components import gate

from farloads import AeroCoefficientsInput, AeroCoeffSet, FuselageMomentInput, Project
from farloads.fuselage_moment import estimate as estimate_fuselage_moment

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
    st.subheader("Maximum lift coefficients (CLmax)")
    st.caption(
        "The single source for stall: **VS/VSF are derived from these** "
        "(VS = √(295·(W/S)/CLmax)) and drive the design speeds VA/VF on the "
        "Structural Speeds page. FLTLOADS also caps its balancing solution with them. "
        "Flaps-down CLmax is used even without a flaps-down coefficient set below."
    )
    m1, m2, m3 = st.columns(3)
    clmax_clean = m1.number_input(
        "Clean CLmax (flaps up)", value=float(aero.clmax_clean) if aero else 0.0,
        format="%.4f", key="clmax_clean",
        help="Positive maximum lift coefficient, flaps up. Sets VS and caps the positive balance.",
    )
    clmax_clean_neg = m2.number_input(
        "Clean negative CLmax", value=float(aero.clmax_clean_neg) if aero else 0.0,
        format="%.4f", key="clmax_clean_neg",
        help="Negative maximum lift coefficient, flaps up; caps the negative balancing solution.",
    )
    clmax_flap = m3.number_input(
        "Flaps-down CLmax", value=float(aero.clmax_flap) if aero else 0.0,
        format="%.4f", key="clmax_flap",
        help="Positive maximum lift coefficient, flaps down (landing). Sets VSF and hence VF.",
    )

    st.divider()
    st.subheader("Cruise (flaps up)")
    cruise_name = st.text_input(
        "Configuration name", value=aero.cruise.name if aero and aero.cruise else "CRUISE",
        key="cruise_name", help="Label for the cruise (flaps-up) coefficient set.",
    )
    cruise_df = st.data_editor(
        _coeff_table(aero.cruise if aero else None), hide_index=True,
        use_container_width=True, disabled=["row"], key="cruise_coeff",
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

    applied = st.form_submit_button("Apply", type="primary")

if applied:
    cruise = AeroCoeffSet(
        name=cruise_name or "CRUISE",
        lift=_row(cruise_df, "lift (CL vs α)"), drag=_row(cruise_df, "drag (CD vs CL)"),
        moment=_row(cruise_df, "moment (CM vs α)"), flaps_down=False,
    )
    flaps = None
    if include_flaps_down:
        flaps = AeroCoeffSet(
            name=flaps_name or "LANDING",
            lift=_row(flaps_df, "lift (CL vs α)"), drag=_row(flaps_df, "drag (CD vs CL)"),
            moment=_row(flaps_df, "moment (CM vs α)"), flaps_down=True,
        )
    # This page owns the whole aero_coeffs slice, so a wholesale replace on
    # Apply is correct here (unlike a slice shared with other pages/edits) --
    # but carry the fuselage-moment sub-slice through unchanged (its own form
    # below owns it; omitting it here would silently reset it). The CLmax scalars
    # are the single stall source; __post_init__ stamps the per-config stall_cl.
    project.aero_coeffs = AeroCoefficientsInput(
        cruise=cruise, flaps_down=flaps,
        clmax_clean=clmax_clean, clmax_clean_neg=clmax_clean_neg, clmax_flap=clmax_flap,
        fuselage_moment=aero.fuselage_moment if aero else None,
    )
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

# --------------------------------------------------------------------------- #
# Fuselage pitching-moment estimator (Step G4) -- Munk slender-body dCm/dalpha
# derived from the G1 fuselage outline, added to the airplane-less-tail M1 when
# enabled. Off by default so the FAR23 GA oracles (coefficients that already
# include the fuselage) are untouched.
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Fuselage pitching-moment (Munk slender-body)")
st.caption(
    "Estimates the fuselage's contribution to the airplane-less-tail moment "
    "slope dCm/dα from the Geometry page fuselage outline, so a concept airplane "
    "need not hand-fold it into M1 above. **Off by default** — enable it only when "
    "the coefficients above do *not* already include the fuselage (they do for "
    "wind-tunnel / DATCOM airplane-less-tail data, e.g. the FAR23 examples). "
    "Method: Munk (NACA TR-184) / DATCOM 4.2.1.1."
)

_geom = project.geometry
_outline = _geom.fuselage if _geom else None
_fl = project.flight_loads
_s = _fl.wing_area_sqft if _fl else 0.0
_mac = _fl.mac if _fl else 0.0
_est = estimate_fuselage_moment(_outline, _s, _mac)

if _est is None:
    gate(
        "Define the fuselage outline on the **Geometry** page and the wing area / MAC "
        "on the **Flight Envelope (V-n)** page first — the estimator needs at least two "
        "fuselage stations and a positive wing S and MAC.",
        "configuration_layout", "flight_envelope", kind="info",
    )
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Volume", f"{_est.volume_in3:,.0f} in³")
    m2.metric("Fineness l/d", f"{_est.fineness_ratio:.2f}")
    m3.metric("k₂ − k₁", f"{_est.k2_minus_k1:.3f}")
    st.caption(
        f"Length {_est.length_in:,.1f} in · max equiv. diameter "
        f"{_est.max_equiv_diameter_in:,.1f} in · wing S {_s:,.1f} ft² · "
        f"MAC {_mac:,.1f} in → estimated **ΔM1 = {_est.d_cm_dalpha:+.5f} /deg**."
    )

    _existing_fm = aero.fuselage_moment
    with st.form("fuselage_moment_form"):
        fm_enabled = st.checkbox(
            "Add this fuselage dCm/dα to M1 (both configurations)",
            value=bool(_existing_fm and _existing_fm.enabled),
            help="When ticked, the Flight Envelope balance adds the value below to "
                 "each configuration's M1. Leave off for coefficients that already "
                 "include the fuselage (the FAR23 oracles).",
        )
        _default_val = (
            _existing_fm.d_cm_dalpha if _existing_fm and _existing_fm.d_cm_dalpha
            else _est.d_cm_dalpha
        )
        fm_value = st.number_input(
            "ΔM1 = dCm/dα (per degree)", value=float(_default_val), format="%.5f",
            help=f"Munk estimate is {_est.d_cm_dalpha:+.5f} /deg; overridable. "
                 "Positive is destabilizing (nose-up with α).",
        )
        fm_applied = st.form_submit_button("Apply fuselage moment", type="primary")

    if fm_applied:
        project.aero_coeffs = AeroCoefficientsInput(
            cruise=aero.cruise, flaps_down=aero.flaps_down,
            fuselage_moment=FuselageMomentInput(enabled=fm_enabled, d_cm_dalpha=fm_value),
        )
        st.session_state["project"] = project
        aero = project.aero_coeffs
        if fm_enabled:
            st.success(f"Fuselage ΔM1 = {fm_value:+.5f} /deg applied to the balance.")
        else:
            st.success("Fuselage moment stored (disabled — no effect on the balance).")

if aero.fuselage_moment is not None and aero.fuselage_moment.enabled:
    st.info(
        f"Balance includes a fuselage ΔM1 = {aero.fuselage_moment.d_cm_dalpha:+.5f} /deg "
        "(the M(W+F) pitching moment on the Flight Envelope page reflects it)."
    )
