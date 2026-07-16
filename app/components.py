"""Shared Streamlit UI components reused across the multi-page app.

Thin presentation wrappers over the pure-calc package; they hold no load math of
their own. The FAR 23 applicability banner is the first shared component: the
detection lives in :func:`farloads.far23_applicability` (pure, unit-tested) and
this module only renders it and wires the "switch to Concept" action.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from farloads import (
    FleetPoint,
    Project,
    StructuralSpeedsInput,
    Subject,
    far23_applicability,
    fleet_stats,
)
from farloads.applicability import design_weight_lb
from farloads.modules.structural_speeds import _maneuver_load_factors

# The reference fleet (nominal published specs; never a FAR input). Shared by the
# Configuration & Layout and Weight Estimate pages via ``render_fleet_comparison``.
_REFERENCE_CSV = Path(__file__).resolve().parent / "data" / "reference_aircraft.csv"


def _switch_to_concept(project: Project) -> None:
    """Flip the project to concept mode without breaking the downstream calc.

    Sets ``speeds.category = "C"`` and, when the concept load factors are unset,
    seeds them from the currently-computed FAR 23.337 limit factors so the flip is
    continuous and never raises (concept mode *requires* explicit
    ``chosen_n``/``chosen_nneg``). The factors depend only on category + weight, so
    the seed cannot fail on missing geometry.
    """
    speeds = project.speeds or StructuralSpeedsInput()
    if speeds.chosen_n is None or speeds.chosen_nneg is None:
        weight = design_weight_lb(project)
        n, _n_min, nneg, _nneg_min = _maneuver_load_factors(
            speeds.category, weight, speeds.chosen_n, speeds.chosen_nneg
        )
        speeds.chosen_n = n
        speeds.chosen_nneg = nneg
    speeds.category = "C"
    project.speeds = speeds
    st.session_state["project"] = project


def render_applicability_banner(project: Project) -> None:
    """Non-blocking FAR 23 applicability banner with a switch-to-Concept action.

    Shows nothing for a GA airplane inside the FAR 23 band, or when the project is
    already in concept mode (the per-page "unverified extrapolation" caption covers
    that case). Otherwise warns that results are a concept-mode extrapolation, lists
    each exceedance (value vs. limit), and offers a one-click switch to concept
    mode.
    """
    if project.is_concept:
        return
    exceedances = far23_applicability(project)
    if not exceedances:
        return

    st.warning(
        "**Exceeds FAR 23 applicability.** This airplane is outside the certificated "
        "band the FAR 23 replication is calibrated to; results are a **concept-mode "
        "extrapolation**, not a certified analysis."
    )
    for exc in exceedances:
        st.markdown(
            f"- **{exc.label}:** {exc.value:,.0f} exceeds the limit of {exc.limit:,.0f}"
        )
    if st.button("Switch to Concept", key="switch_to_concept"):
        _switch_to_concept(project)
        st.rerun()


def _fleet_points(fleet: pd.DataFrame) -> list[FleetPoint]:
    """The reference-CSV rows as pure :class:`FleetPoint` records for the stats."""
    def _opt(row: "pd.Series", key: str) -> Optional[float]:
        if key not in row or pd.isna(row[key]):
            return None
        return float(row[key])

    return [
        FleetPoint(
            name=str(row["aircraft"]),
            mtow_lb=float(row["mtow_lb"]),
            oew_lb=float(row["oew_lb"]),
            max_hp=float(row["max_hp"]),
            wing_area_ft2=float(row["wing_area_ft2"]),
            seats=int(row["seats"]) if "seats" in row and not pd.isna(row["seats"]) else 0,
            wingspan_ft=_opt(row, "wingspan_ft"),
            aspect_ratio=_opt(row, "aspect_ratio"),
        )
        for _, row in fleet.iterrows()
    ]


def _fleet_readout(subject: Subject, points: list[FleetPoint]) -> None:
    """Render the quantitative placement (nearest-3 / percentile band / outliers)."""
    stats = fleet_stats(subject, points)

    c1, c2 = st.columns(2)
    if stats.ws_percentile is not None and stats.ws_band is not None:
        c1.metric(
            "Wing loading W/S (lb/ft²)",
            f"{subject.w_s:.1f}",
            help=(
                f"{stats.ws_percentile:.0f}th percentile of the fleet; "
                f"p10–p90 band {stats.ws_band[0]:.1f}–{stats.ws_band[1]:.1f}."
            ),
        )
    else:
        c1.metric("Wing loading W/S (lb/ft²)", "—",
                  help="Set the wing area and design weight to compute W/S.")
    if stats.wp_percentile is not None and stats.wp_band is not None:
        c2.metric(
            "Power loading W/P (lb/hp)",
            f"{subject.w_p:.1f}",
            help=(
                f"{stats.wp_percentile:.0f}th percentile of the fleet; "
                f"p10–p90 band {stats.wp_band[0]:.1f}–{stats.wp_band[1]:.1f}."
            ),
        )
    else:
        c2.metric("Power loading W/P (lb/hp)", "—",
                  help="Set the installed power and design weight to compute W/P.")

    if stats.nearest:
        st.caption("**Nearest reference aircraft** (normalized distance over MTOW / W/S / W/P):")
        st.dataframe(
            pd.DataFrame([
                {
                    "Aircraft": p.name,
                    "MTOW (lb)": round(p.mtow_lb),
                    "OEW (lb)": round(p.oew_lb),
                    "W/S (lb/ft²)": round(p.w_s, 1) if p.w_s is not None else None,
                    "W/P (lb/hp)": round(p.w_p, 1) if p.w_p is not None else None,
                    "Distance": round(dist, 3),
                }
                for p, dist in stats.nearest
            ]),
            hide_index=True, use_container_width=True,
        )

    if stats.outliers:
        st.warning(
            "Outside the fleet p10–p90 band for: **"
            + ", ".join(stats.outliers)
            + "** — a distinctive design point, worth a sanity check against the scatters below."
        )
    else:
        st.caption("Within the fleet p10–p90 band on every computed loading.")


def render_fleet_comparison(
    project: Project,
    *,
    name: str,
    mtow: Optional[float],
    oew: Optional[float] = None,
    wing_area: Optional[float] = None,
    power: Optional[float] = None,
) -> None:
    """Place this airplane against the reference fleet: quantitative + scatters.

    Shared by ``configuration_layout`` and ``weight_estimate`` (GUI_design §8.4).
    Renders the quantitative readout (nearest-3, W/S & W/P percentile band, outlier
    flags) then the W/S-vs-W/P and MTOW-vs-OEW scatters. Values are Imperial (the
    reference data is Imperial-only, published specs, never a FAR input). Metrics the
    subject lacks (e.g. no wing area on the Weight Estimate page) are shown as "—"
    and simply omit "This airplane" from that scatter. ``mtow`` of ``None`` (or 0)
    means the design weight is not yet known -- only the fleet is shown.
    """
    st.subheader("Comparison with similar aircraft")
    st.caption(
        "This airplane placed against a reference fleet by wing loading (W/S), power "
        "loading (W/P) and MTOW-vs-OEW. Reference figures are nominal published specs "
        "for comparison only — they never enter a FAR computation. Jets (no shaft "
        "power) carry no W/P."
    )

    try:
        fleet = pd.read_csv(_REFERENCE_CSV, comment="#")
    except FileNotFoundError:
        st.info(f"Reference aircraft data file not found at {_REFERENCE_CSV}.")
        return

    points = _fleet_points(fleet)

    if mtow:
        subject = Subject(
            name=name or "This airplane",
            mtow_lb=float(mtow),
            oew_lb=float(oew) if oew else None,
            wing_area_ft2=float(wing_area) if wing_area else None,
            power_hp=float(power) if power else None,
        )
        _fleet_readout(subject, points)
    else:
        st.info("Set the design weight (Structural Speeds / the weight estimate) to place this airplane.")
        subject = None

    # --- Scatters (fleet always; "This airplane" only where the metric exists). ---
    fleet = fleet.copy()
    fleet["series"] = "Reference fleet"
    fleet["w_s"] = fleet["mtow_lb"] / fleet["wing_area_ft2"].where(fleet["wing_area_ft2"] > 0)
    fleet["w_p"] = fleet["mtow_lb"] / fleet["max_hp"].where(fleet["max_hp"] > 0)

    rows = []
    if subject is not None:
        rows.append({
            "aircraft": subject.name, "mtow_lb": subject.mtow_lb, "oew_lb": subject.oew_lb,
            "wing_area_ft2": subject.wing_area_ft2, "max_hp": subject.power_hp,
            "w_s": subject.w_s, "w_p": subject.w_p, "series": "This airplane",
        })
    plot_df = pd.concat([fleet, pd.DataFrame(rows)], ignore_index=True) if rows else fleet
    color_map = {"Reference fleet": "#1f77b4", "This airplane": "#d62728"}

    tab1, tab2 = st.tabs(["Wing loading vs power loading", "MTOW vs OEW"])
    with tab1:
        wp_df = plot_df.dropna(subset=["w_s", "w_p"])
        fig = px.scatter(
            wp_df, x="w_s", y="w_p", color="series", symbol="series",
            hover_name="aircraft", hover_data=["mtow_lb", "max_hp", "wing_area_ft2"],
            color_discrete_map=color_map,
            labels={"w_s": "Wing loading W/S (lb/ft²)", "w_p": "Power loading W/P (lb/hp)", "series": ""},
        )
        fig.update_layout(legend=dict(orientation="h", y=1.1, x=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Jets (max_hp = 0) are excluded from this plot.")
    with tab2:
        oew_df = plot_df.dropna(subset=["oew_lb"])
        fig2 = px.scatter(
            oew_df, x="oew_lb", y="mtow_lb", color="series", symbol="series",
            log_x=True, log_y=True, hover_name="aircraft",
            hover_data=["max_hp", "wing_area_ft2"],
            color_discrete_map=color_map,
            labels={"oew_lb": "Empty weight OEW (lb)", "mtow_lb": "MTOW (lb)", "series": ""},
        )
        fig2.update_layout(legend=dict(orientation="h", y=1.1, x=0))
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Reference fleet data"):
        st.dataframe(fleet.drop(columns=["series", "w_s", "w_p"]), hide_index=True, use_container_width=True)
