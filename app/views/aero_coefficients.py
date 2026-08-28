"""Streamlit page for the airplane-less-tail aero coefficients (Project.aero_coeffs).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Owns the ``Project.aero_coeffs`` slice (Step D4.1): the Ch 7 aero-coefficients
program's output, cruise (flaps up) and an optional flaps-down (landing) set,
that the Flight Envelope page (FLTLOADS) balances against but no longer edits
(Step D4.2 — this page replaces the interim editor that lived there).

M4-5 (decision D-10) adds the **coefficient curves** below the tables: CL–α, the
drag polar and CM–α with the balanced envelope points overlaid, the recovered-CL
closure metric and the stall-clamp margin. All of that math lives in
``sloads.aero_curves`` (which ``modules.flight_envelope`` also evaluates, so the
plotted curve and the balance cannot drift apart); the coefficient-entry checks
are ``sloads.validation`` warnings tagged for this page.
"""

from __future__ import annotations

import copy

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app_shell.components import gate, page_header, stop_page
from app_shell.widget_keys import widget_key
from sloads import (
    AeroCoefficientsInput,
    AeroCoeffSet,
    FuselageMomentInput,
    LateralBodyAeroInput,
    Project,
    build_aero_curves,
    curve_closure,
    operating_points,
)
from sloads.derived_geometry import wing_reference
from sloads.fuselage_moment import estimate as estimate_fuselage_moment
from sloads.modules.flight_envelope import balance_configs, build_envelope

# ``banner=False`` keeps this page exactly as it was apart from the warnings
# (#82) -- it has never carried the applicability banner, and adding one is not
# this item's to decide. The title is the workflow step's, which is the same
# "Aerodynamic Data" it stated by hand.
project: Project = page_header(
    "aero_coefficients",
    caption=(
        "Airplane-less-tail aerodynamic coefficient sets (Ch 7 aero-coefficients "
        "program output) that the Flight Envelope page (FLTLOADS) balances against: "
        "CL = C0 + C1·α + C2·α² + C3·α³ + C4·α⁴ (α in deg); CD = D0 + D1·CL + … ; "
        "CM = M0 + M1·α + … . Cruise is balanced at every altitude in the flight "
        "envelope; flaps-down is balanced at sea level only (FLTLOADS.BAS line 3000)."
    ),
    banner=False,
).project
st.caption(
    "This page holds the airplane-less-tail balance coefficients. Each lifting "
    "surface's spanwise (Schrenk) aero -- lift-curve slope, twist, target CL, "
    "profile drag, section CM -- is entered on the Wing Loads page (Analysis "
    "phase), next to the load distribution it drives."
)

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
        "(VS = √(2·(W/S)/(ρ₀·CLmax))) and drive the design speeds VA/VF on the "
        "Structural Speeds page. FLTLOADS also caps its balancing solution with them. "
        "Flaps-down CLmax is used even without a flaps-down coefficient set below."
    )
    m1, m2, m3 = st.columns(3)
    clmax_clean = m1.number_input(
        "Clean CLmax (flaps up)", value=float(aero.clmax_clean) if aero else 0.0,
        format="%.4f", key=widget_key("clmax_clean"),
        help="Positive maximum lift coefficient, flaps up. Sets VS and caps the positive balance.",
    )
    clmax_clean_neg = m2.number_input(
        "Clean negative CLmax", value=float(aero.clmax_clean_neg) if aero else 0.0,
        format="%.4f", key=widget_key("clmax_clean_neg"),
        help="Negative maximum lift coefficient, flaps up; caps the negative balancing solution.",
    )
    clmax_flap = m3.number_input(
        "Flaps-down CLmax", value=float(aero.clmax_flap) if aero else 0.0,
        format="%.4f", key=widget_key("clmax_flap"),
        help="Positive maximum lift coefficient, flaps down (landing). Sets VSF and hence VF.",
    )

    st.divider()
    st.subheader("Cruise (flaps up)")
    cruise_name = st.text_input(
        "Configuration name", value=aero.cruise.name if aero and aero.cruise else "CRUISE",
        key=widget_key("cruise_name"), help="Label for the cruise (flaps-up) coefficient set.",
    )
    cruise_df = st.data_editor(
        _coeff_table(aero.cruise if aero else None), hide_index=True,
        width="stretch", disabled=["row"], key=widget_key("cruise_coeff"),
    )

    st.divider()
    include_flaps_down = st.checkbox(
        "Include a flaps-down (landing) configuration",
        value=bool(aero and aero.flaps_down is not None),
        key=widget_key("aero_include_flaps"),
        help="Add a second coefficient set for the landing configuration, balanced at sea level only "
             "(FLTLOADS.BAS line 3000).",
    )
    st.subheader("Flaps down (landing)")
    st.caption("Ignored unless the checkbox above is ticked.")
    flaps_name = st.text_input(
        "Configuration name", value=aero.flaps_down.name if aero and aero.flaps_down else "LANDING",
        key=widget_key("flaps_name"), help="Label for the flaps-down (landing) coefficient set.",
    )
    flaps_df = st.data_editor(
        _coeff_table(aero.flaps_down if aero else None), hide_index=True,
        width="stretch", disabled=["row"], key=widget_key("flaps_coeff"),
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
    stop_page()

st.subheader("Current coefficients")


def _summary(name: str, cfg: AeroCoeffSet) -> None:
    st.markdown(f"**{name} — {cfg.name}**")
    st.dataframe(_coeff_table(cfg), hide_index=True, width="stretch")
    st.caption(f"Stall CL {cfg.stall_cl:.3f} / negative stall CL {cfg.neg_stall_cl:.3f}")


if aero.cruise is not None:
    _summary("Cruise", aero.cruise)
if aero.flaps_down is not None:
    _summary("Flaps down", aero.flaps_down)

# --------------------------------------------------------------------------- #
# Coefficient curves (M4-5, decision D-10) -- CL-alpha / drag polar / CM-alpha,
# with the balanced envelope points overlaid and the recovered-CL closure. All
# math is in ``sloads.aero_curves`` (which the FLTLOADS balance also evaluates,
# so the plotted curve cannot drift from the one that produces the loads).
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Coefficient curves")
st.caption(
    "The entered polynomials drawn as curves, so a coefficient-entry error shows "
    "as a shape rather than hiding in a table — the concept-aircraft case, where "
    "the polynomials are hand-built rather than wind-tunnel/DATCOM output. All "
    "quantities are **dimensionless**; α is in **degrees** — nothing here changes "
    "with the unit-system toggle."
)

# The balance's own view of the coefficients (Step G4 folds an enabled fuselage
# dCm/dalpha into M1 on a copy), so the curve is the one FLTLOADS actually flies.
_configs = balance_configs(aero)
_fm_on = aero.fuselage_moment is not None and aero.fuselage_moment.enabled

_env = None
_env_note = ""
_fl_bal = project.flight_loads
# The wing area and MAC the curves are non-dimensionalised on come from the
# planform (note 33), not from a copy on the flight-loads slice.
_wr_bal = wing_reference(project, "wing")
if _fl_bal is None or _wr_bal is None or project.speeds is None:
    _env_note = ("no balanced envelope yet — the operating-point overlay needs the "
                 "**Flight Envelope (V-n)** inputs and the **Structural Speeds** "
                 "design speeds")
else:
    try:
        _env = build_envelope(copy.deepcopy(project))
    except (ValueError, ZeroDivisionError, KeyError) as exc:
        _env_note = f"the balanced envelope could not be built ({exc})"

if _env is None:
    gate(
        f"Curves only — {_env_note}. The coefficient curves below are unaffected.",
        "flight_envelope", "structural_speeds", kind="info",
    )


def _curve_figure(curves) -> go.Figure:
    """The three-panel coefficient figure for one configuration."""
    fig = make_subplots(
        rows=1, cols=3, horizontal_spacing=0.08,
        subplot_titles=("Lift  CL vs α", "Drag polar  CL vs CD", "Moment  CM vs α"),
    )
    fig.add_trace(go.Scatter(x=curves.lift.x, y=curves.lift.y, mode="lines",
                             name="CL(α)", line={"width": 3}), row=1, col=1)
    fig.add_trace(go.Scatter(x=curves.polar.x, y=curves.polar.y, mode="lines",
                             name="CD(CL)", line={"width": 3}, showlegend=False),
                  row=1, col=2)
    fig.add_trace(go.Scatter(x=curves.moment.x, y=curves.moment.y, mode="lines",
                             name="CM(α)", line={"width": 3}, showlegend=False),
                  row=1, col=3)
    # Stall clamps: the balance never carries a CL outside these lines.
    for cl_line, label in ((curves.stall_cl, "stall CL"),
                           (curves.neg_stall_cl, "neg stall CL")):
        if cl_line:
            for col in (1, 2):
                fig.add_hline(y=cl_line, row=1, col=col,
                              line={"color": "rgba(200,80,80,0.7)", "width": 1, "dash": "dash"},
                              annotation_text=label if col == 1 else None,
                              annotation_position="top left")
    if curves.alpha_stall_deg is not None:
        fig.add_vline(x=curves.alpha_stall_deg, row=1, col=1,
                      line={"color": "rgba(120,120,120,0.6)", "width": 1, "dash": "dot"},
                      annotation_text=f"α {curves.alpha_stall_deg:.1f}°",
                      annotation_position="bottom right")
    pts = curves.points
    if pts is not None and len(pts):
        marker = {"symbol": "circle-open", "size": 8, "color": "rgba(60,110,200,0.9)"}
        fig.add_trace(go.Scatter(x=pts.alpha_deg, y=pts.cl, mode="markers",
                                 name="balanced points", marker=marker,
                                 text=pts.label, hovertemplate="%{text}<br>α %{x:.2f}° "
                                 "CL %{y:.3f}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=pts.cd, y=pts.cl, mode="markers", marker=marker,
                                 name="balanced points", showlegend=False,
                                 text=pts.label, hovertemplate="%{text}<br>CD %{x:.4f} "
                                 "CL %{y:.3f}<extra></extra>"), row=1, col=2)
        fig.add_trace(go.Scatter(x=pts.alpha_deg, y=pts.cm, mode="markers", marker=marker,
                                 name="balanced points", showlegend=False,
                                 text=pts.label, hovertemplate="%{text}<br>α %{x:.2f}° "
                                 "CM %{y:.4f}<extra></extra>"), row=1, col=3)
    fig.update_xaxes(title_text="α (deg)", row=1, col=1)
    fig.update_xaxes(title_text="CD", row=1, col=2)
    fig.update_xaxes(title_text="α (deg)", row=1, col=3)
    fig.update_yaxes(title_text="CL", row=1, col=1)
    fig.update_yaxes(title_text="CL", row=1, col=2)
    fig.update_yaxes(title_text="CM", row=1, col=3)
    fig.update_layout(height=380, legend={"orientation": "h"},
                      margin={"t": 60, "b": 40, "l": 10, "r": 10})
    return fig


for _cfg in _configs:
    _pts = _closure = None
    if _env is not None:
        _pts = operating_points(_env, _cfg.name, wing_area_sqft=_wr_bal.s_sqft,
                                mac_in=_wr_bal.mac)
        _closure = curve_closure(_env, _cfg, wing_area_sqft=_wr_bal.s_sqft,
                                 mach_ref=_fl_bal.mn)
    _curves = build_aero_curves(_cfg, points=_pts, closure=_closure)
    st.markdown(f"**{'Flaps down' if _cfg.flaps_down else 'Cruise'} — {_cfg.name}**")
    st.plotly_chart(_curve_figure(_curves), width="stretch")

    _bits = [
        f"Curve at the reference Mach (as entered). Lift peaks at CL "
        f"{_curves.cl_max_on_curve:.3f} over α {_curves.alpha_lo_deg:g}…"
        f"{_curves.alpha_hi_deg:g}°"
    ]
    if _curves.alpha_stall_deg is not None:
        _bits.append(f"reaching the stall CL {_curves.stall_cl:.3f} at α "
                     f"{_curves.alpha_stall_deg:.1f}°")
    else:
        _bits.append(f"**never reaching the stall CL {_curves.stall_cl:.3f}**")
    if _fm_on:
        _bits.append("CM includes the enabled fuselage ΔM1")
    st.caption(" · ".join(_bits) + ".")

    if _closure is not None and _closure.n_points:
        c1, c2 = st.columns(2)
        c1.metric(
            "Recovered-CL closure", f"{_closure.worst_cl:.2e}",
            help="Worst |CL recovered from the balanced point's own LZW/DX/α/V — "
                 "inverting the balance rotation — minus the coefficient polynomial "
                 "at that α|, over every balanced point of this configuration. The "
                 "two are the same number algebraically, so this is a drift guard "
                 f"(tolerance {_closure.cl_tol:g}), not a numerical discovery.")
        c2.metric(
            "Stall-clamp margin", f"{_closure.worst_stall_excess:.4f}",
            delta=None if _closure.worst_stall_excess <= _closure.stall_tol else "exceeded",
            delta_color="inverse",
            help="Worst amount by which a balanced point's CL sits *above* its "
                 "Mach-adjusted stall CL. The balance iterates dynamic pressure to "
                 "hold this at zero; a non-zero value means the point never "
                 "converged onto the stall line — typically because the Mach cap "
                 f"binds first (tolerance {_closure.stall_tol:g}).")
        if _closure.worst_stall_excess > _closure.stall_tol:
            st.warning(
                f"{_closure.worst_stall_label}: the balanced CL exceeds the stall CL by "
                f"{_closure.worst_stall_excess:.3f}. The airplane cannot reach that "
                "condition's load factor within its Mach cap and stall CL, so those "
                "points' loads are not physically attainable — check the design "
                "speeds, the altitude list and the entered CLmax.")
        st.caption(f"Closure over {_closure.n_points} balanced point"
                   f"{'s' if _closure.n_points != 1 else ''} of this configuration.")

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
# Tolerant, as the flight-loads read it replaces was: with no planform the
# estimator gets zeros and declines, rather than the page refusing to render.
_wr = wing_reference(project, "wing")
_s = _wr.s_sqft if _wr else 0.0
_mac = _wr.mac if _wr else 0.0
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
            key=widget_key("aero_fm_enabled"),
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
            key=widget_key("aero_fm_value"),
            help=f"Munk estimate is {_est.d_cm_dalpha:+.5f} /deg; overridable. "
                 "Positive is destabilizing (nose-up with α).",
        )
        fm_applied = st.form_submit_button("Apply fuselage moment", type="primary")

    if fm_applied:
        # Carry the CLmax scalars through explicitly: they are a *sibling* slice
        # this form does not own, and omitting them let ``__post_init__`` re-derive
        # them from the per-config ``stall_cl``. Where the two legitimately differ
        # (ga6: clmax_clean 1.4068 from the printed VS vs stall_cl 1.41) that
        # silently moved VS -- and hence VA/VF on the Structural Speeds page --
        # on a form that should touch nothing but the fuselage moment.
        project.aero_coeffs = AeroCoefficientsInput(
            cruise=aero.cruise, flaps_down=aero.flaps_down,
            clmax_clean=aero.clmax_clean, clmax_clean_neg=aero.clmax_clean_neg,
            clmax_flap=aero.clmax_flap,
            fuselage_moment=FuselageMomentInput(enabled=fm_enabled, d_cm_dalpha=fm_value),
            lateral_body_aero=aero.lateral_body_aero,   # sibling slice, not this form's
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


# --------------------------------------------------------------------------- #
# L-7: lumped wing-body lateral aero in sideslip (design note 19, rev. 3)
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Lateral body aero in sideslip (Cy_β / Cn_β, DATCOM)")
st.caption(
    "The wing-body side force and yawing moment in sideslip, applied beside the "
    "fin's load in the balanced 23.441 / 23.443 cases. **Off by default** — it "
    "raises |n_y| (the side force adds to the fin's) and lowers the yaw "
    "acceleration (the body's couple opposes the fin's), so it is your decision. "
    "Method: DATCOM 5.2.1.1 / 5.2.3.1 from the Geometry page fuselage outline, "
    "computed per case (the yaw term depends on the case Reynolds number); "
    "entering a value overrides it for every case. Per degree of sideslip, "
    "suite sign (+Cn_β = destabilizing), Cn_β about the wing 25 %-MAC station."
)
_existing_lb = aero.lateral_body_aero
_lb_est = None
if _outline is not None and _wr is not None and _wr.s_sqft > 0:
    from sloads import atmosphere as _atm
    from sloads import lateral_body_aero as _lba
    _vt = project.vtail_loads
    _span = _vt.wing_span_in if _vt is not None and _vt.wing_span_in > 0 else 0.0
    _v_ill = 150.0   # illustrative EAS, kt; VC when STRSPEED can supply it
    try:
        from sloads.modules.flight_envelope import design_inputs as _design_inputs
        _v_ill = float(_design_inputs(project).vc) or _v_ill
    except Exception:
        pass
    if _span > 0:
        _lb_est = _lba.estimate(_outline, _wr.s_sqft, _span, _wr.xw,
                                _atm.reynolds_per_ft(_v_ill, 0.0))
if _lb_est is None:
    gate(
        "Define the fuselage outline (**Geometry**), the wing area / 25 %-MAC "
        "station (**Flight Envelope**) and the wing span (**Empennage**, v-tail "
        "slice) first — the estimator needs all three.",
        "configuration_layout", "flight_envelope", kind="info",
    )
else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Cy_β (per deg)", f"{_lb_est.cy_beta:+.5f}")
    c2.metric("Cn_β (per deg, about xw)", f"{_lb_est.cn_beta:+.5f}")
    c3.metric("K_N · K_Rl", f"{_lb_est.k_n:.5f} · {_lb_est.k_rl:.3f}")
    st.caption(
        f"Illustrative estimate at sea level, {_v_ill:.0f} kt EAS (the balance "
        f"recomputes K_Rl at each case's own speed and altitude): body length "
        f"{_lb_est.length_in:,.0f} in, side area {_lb_est.s_bs_in2:,.0f} in², "
        f"CL_α,B {_lb_est.cl_alpha_body:.5f}/deg, K_i {_lb_est.k_i:.3f}, "
        f"dihedral term {_lb_est.cy_beta_dihedral:+.5f}/deg. Munk isolated-body "
        "cross-check and the DATCOM oracle: `tests/test_lateral_body_aero.py`."
    )
with st.form("lateral_body_aero_form"):
    lb_enabled = st.checkbox(
        "Apply the wing-body Cy_β / Cn_β in the balanced lateral cases",
        value=bool(_existing_lb and _existing_lb.enabled),
        key=widget_key("aero_lb_enabled"),
    )
    lb_override = st.checkbox(
        "Override the computed derivatives with the values below",
        value=bool(_existing_lb and (_existing_lb.cy_beta is not None
                                     or _existing_lb.cn_beta is not None)),
        key=widget_key("aero_lb_override"),
    )
    _cy0 = (_existing_lb.cy_beta if _existing_lb and _existing_lb.cy_beta is not None
            else (_lb_est.cy_beta if _lb_est else 0.0))
    _cn0 = (_existing_lb.cn_beta if _existing_lb and _existing_lb.cn_beta is not None
            else (_lb_est.cn_beta if _lb_est else 0.0))
    lb_cy = st.number_input("Cy_β (per degree)", value=float(_cy0), format="%.5f",
                            key=widget_key("aero_lb_cy"))
    lb_cn = st.number_input("Cn_β about xw (per degree, + = destabilizing)",
                            value=float(_cn0), format="%.5f",
                            key=widget_key("aero_lb_cn"))
    lb_applied = st.form_submit_button("Apply lateral body aero", type="primary")
if lb_applied:
    project.aero_coeffs = AeroCoefficientsInput(
        cruise=aero.cruise, flaps_down=aero.flaps_down,
        clmax_clean=aero.clmax_clean, clmax_clean_neg=aero.clmax_clean_neg,
        clmax_flap=aero.clmax_flap,
        fuselage_moment=aero.fuselage_moment,
        lateral_body_aero=LateralBodyAeroInput(
            enabled=lb_enabled,
            cy_beta=lb_cy if lb_override else None,
            cn_beta=lb_cn if lb_override else None),
    )
    st.session_state["project"] = project
    aero = project.aero_coeffs
    st.success("Lateral body aero " + ("ENABLED" if lb_enabled else "stored (disabled)")
               + (" with entered derivatives." if lb_override else " — computed per case."))
if aero.lateral_body_aero is not None and aero.lateral_body_aero.enabled:
    st.info("The balanced lateral cases carry the wing-body sideslip term; each "
            "case note states the applied numbers and the net fin+body Cn_β.")
