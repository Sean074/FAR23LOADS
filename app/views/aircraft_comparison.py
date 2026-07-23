"""Aircraft Comparison — place the design against a reference fleet.

The Export-section input-assessment page: it answers "how does this airplane
compare to similar aircraft?" in one place, the concept-mode charter (``CLAUDE.md``:
"assesses a configuration against similar airplanes"). It carries the quantitative
placement (nearest-N similar aircraft, W/S & W/P percentile band, outlier flags),
a parameter table (subject + nearest-N / full fleet), and six scatter tabs: the two
loading/weight scatters (W/S-vs-W/P, MTOW-vs-OEW) plus four geometric scatters
(wingspan / wing area / aspect ratio / seats vs. MTOW).

Presentation only. The reference fleet is nominal published specs (Imperial) — never
a FAR input, so the ULT/limit rules and ``load_cases_to_rows`` are untouched. The
nearest-N ranking runs on MTOW / W/S / W/P via the pure :func:`sloads.fleet_stats`;
the geometry (span / area / AR / seats) is table columns and plot axes only, never a
distance term (backlog F2 decision D-F2-a).

One page of the multipage app; run the suite with:  streamlit run app/Home.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from sloads import FleetPoint, Project, Subject, fleet_stats, registry
from sloads.constants import IN2_PER_FT2
from sloads.modules.wing_geometry import surface_properties

# The reference fleet (nominal published specs; never a FAR input). This page owns
# it now that the fleet block has moved off the two input pages (backlog F2).
_REFERENCE_CSV = Path(__file__).resolve().parents[1] / "data" / "reference_aircraft.csv"

_SERIES_COLOR = {"Reference fleet": "#1f77b4", "This airplane": "#d62728"}


def _fleet_points(fleet: pd.DataFrame) -> list[FleetPoint]:
    """The reference-CSV rows as pure :class:`FleetPoint` records."""
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


def _wtestima_value(project: Project, label: str) -> Optional[float]:
    """One labelled figure out of a live WTESTIMA estimate, or ``None``.

    Runs the registered ``weight_estimate`` module (needs ``weight.estimation``);
    any failure (missing slice, ValueError) yields ``None`` so the caller falls back
    to a lower-priority source.
    """
    if not (project.weight and project.weight.estimation):
        return None
    try:
        result = registry.get("weight_estimate")(project)
    except Exception:
        return None
    for cond in result.conditions:
        for v in cond.values:
            if v.label == label:
                return float(v.value)
    return None


def _wing_surface_props(project: Project) -> dict:
    """The WINGGEOM planform properties of the ``wing`` surface, or ``{}``.

    Runs :func:`~sloads.modules.wing_geometry.surface_properties` on
    ``geometry.by_name("wing")`` and returns its labelled figures keyed by label
    (``"Total area"`` in in², ``"Aspect ratio"``, ``"Span"`` in, ...). Empty when no
    wing surface exists or the planform is degenerate (any calc failure). This is the
    surface fallback for the geometric axes on projects that carry
    ``geometry.surfaces`` but no parametric layout (the shipped Appendix examples),
    mirroring the same pattern used in ``flight_envelope.py``.
    """
    wing = project.geometry.by_name("wing") if project.geometry is not None else None
    if wing is None:
        return {}
    try:
        return {v.label: v.value for v in surface_properties(wing).values}
    except (ValueError, ZeroDivisionError):
        return {}


def _subject_from_project(project: Project) -> Optional[Subject]:
    """Assemble the comparison :class:`Subject` from the best-available slices.

    Priority per metric (backlog F2 step 2; surface fallback added in M2-5):
      MTOW  -- speeds.weight_lb -> weight.direct_totals()[0] -> WTESTIMA
      OEW   -- weight.direct_totals()[1] -> WTESTIMA
      area  -- parametric.wing_area_sqft -> WINGGEOM wing surface -> speeds.wing_area_sqft
      power -- Sum engines[].max_cont_hp -> weight.estimation.max_continuous_hp
      AR    -- parametric.aspect_ratio -> WINGGEOM wing surface
      span  -- WINGGEOM wing surface (else back-derived from AR*area by Subject.span)
      seats -- speeds.occupants -> weight.estimation.seats

    Most shipped examples carry ``geometry.surfaces`` (WINGGEOM planforms) rather than
    a parametric layout, so the surface fallback is what fills W/S, wing area, span and
    aspect ratio for them (M2-5).

    Returns ``None`` only when no MTOW can be found (the common comparison axis); a
    missing secondary metric leaves its field ``None`` (shown as "—"), never dropping
    the subject silently.
    """
    speeds = project.speeds
    weight = project.weight
    config = project.geometry.parametric if project.geometry is not None else None
    surf = _wing_surface_props(project)

    direct = weight.direct_totals() if (weight and weight.items) else None

    mtow: Optional[float] = None
    if speeds and speeds.weight_lb:
        mtow = float(speeds.weight_lb)
    elif direct and direct[0]:
        mtow = float(direct[0])
    else:
        mtow = _wtestima_value(project, "Max take-off weight")
    if not mtow:
        return None

    oew: Optional[float] = None
    if direct and direct[1]:
        oew = float(direct[1])
    else:
        oew = _wtestima_value(project, "Empty weight")

    wing_area: Optional[float] = None
    if config and config.wing_area_sqft:
        wing_area = float(config.wing_area_sqft)
    elif surf.get("Total area"):
        wing_area = float(surf["Total area"]) / IN2_PER_FT2
    elif speeds and speeds.wing_area_sqft:
        wing_area = float(speeds.wing_area_sqft)

    power: Optional[float] = None
    if project.engines:
        power = sum((e.max_cont_hp or 0.0) for e in project.engines) or None
    if power is None and weight and weight.estimation and weight.estimation.max_continuous_hp:
        power = float(weight.estimation.max_continuous_hp)

    aspect_ratio: Optional[float] = None
    if config and config.aspect_ratio:
        aspect_ratio = float(config.aspect_ratio)
    elif surf.get("Aspect ratio"):
        aspect_ratio = float(surf["Aspect ratio"])

    # Span from the surface planform (full span, inches) when available; otherwise
    # Subject.span back-derives it from sqrt(AR * area).
    wingspan_ft: Optional[float] = None
    if surf.get("Span"):
        wingspan_ft = float(surf["Span"]) / 12.0

    seats = 0
    if speeds and speeds.occupants:
        seats = int(speeds.occupants)
    elif weight and weight.estimation and weight.estimation.seats:
        seats = int(weight.estimation.seats)

    return Subject(
        name=project.name or "This airplane",
        mtow_lb=mtow,
        oew_lb=oew,
        wing_area_ft2=wing_area,
        power_hp=power,
        wingspan_ft=wingspan_ft,
        aspect_ratio=aspect_ratio,
        seats=seats,
    )


def _fmt(value: Optional[float], digits: int = 0) -> Optional[float]:
    """Round for the table, or ``None`` (rendered blank) when the metric is absent."""
    if value is None:
        return None
    return round(value, digits)


def _subject_row(subject: Subject) -> dict:
    return {
        "Aircraft": subject.name,
        "MTOW (lb)": _fmt(subject.mtow_lb),
        "OEW (lb)": _fmt(subject.oew_lb),
        "Power (hp)": _fmt(subject.power_hp),
        "W/S (lb/ft²)": _fmt(subject.w_s, 1),
        "W/P (lb/hp)": _fmt(subject.w_p, 1),
        "Wingspan (ft)": _fmt(subject.span, 1),
        "Wing area (ft²)": _fmt(subject.wing_area_ft2),
        "Aspect ratio": _fmt(subject.aspect_ratio_effective, 2),
        "Seats": subject.seats or None,
    }


def _point_row(p: FleetPoint) -> dict:
    return {
        "Aircraft": p.name,
        "MTOW (lb)": _fmt(p.mtow_lb),
        "OEW (lb)": _fmt(p.oew_lb),
        "Power (hp)": _fmt(p.max_hp),
        "W/S (lb/ft²)": _fmt(p.w_s, 1),
        "W/P (lb/hp)": _fmt(p.w_p, 1),
        "Wingspan (ft)": _fmt(p.span, 1),
        "Wing area (ft²)": _fmt(p.wing_area_ft2),
        "Aspect ratio": _fmt(p.aspect_ratio_effective, 2),
        "Seats": p.seats or None,
    }


def _render_readout(subject: Subject, points: list[FleetPoint]) -> None:
    """The quantitative placement: W/S & W/P metric cards, nearest-N table, outliers."""
    stats = fleet_stats(subject, points)

    c1, c2 = st.columns(2)
    if stats.ws_percentile is not None and stats.ws_band is not None:
        c1.metric(
            "Wing loading W/S (lb/ft²)", f"{subject.w_s:.1f}",
            help=(f"{stats.ws_percentile:.0f}th percentile of the fleet; "
                  f"p10–p90 band {stats.ws_band[0]:.1f}–{stats.ws_band[1]:.1f}."),
        )
    else:
        c1.metric("Wing loading W/S (lb/ft²)", "—",
                  help="Set the wing area and design weight to compute W/S.")
    if stats.wp_percentile is not None and stats.wp_band is not None:
        c2.metric(
            "Power loading W/P (lb/hp)", f"{subject.w_p:.1f}",
            help=(f"{stats.wp_percentile:.0f}th percentile of the fleet; "
                  f"p10–p90 band {stats.wp_band[0]:.1f}–{stats.wp_band[1]:.1f}."),
        )
    else:
        c2.metric("Power loading W/P (lb/hp)", "—",
                  help="Set the installed power and design weight to compute W/P.")

    if stats.outliers:
        st.warning(
            "Outside the fleet p10–p90 band for: **" + ", ".join(stats.outliers)
            + "** — a distinctive design point, worth a sanity check against the scatters below."
        )
    else:
        st.caption("Within the fleet p10–p90 band on every computed loading.")

    st.caption("**Parameter table** — this airplane (top) against the nearest reference "
               "aircraft (normalized distance over MTOW / W/S / W/P):")
    rows = [{"": "→", **_subject_row(subject)}]
    rows += [{"": "", **_point_row(p)} for p, _dist in stats.nearest]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _scatter(df: pd.DataFrame, x: str, y: str, labels: dict, *,
             log_x: bool = False, log_y: bool = False) -> None:
    """One two-series scatter (Reference fleet vs This airplane) over ``df``."""
    plot_df = df.dropna(subset=[x, y])
    fig = px.scatter(
        plot_df, x=x, y=y, color="series", symbol="series",
        hover_name="aircraft", log_x=log_x, log_y=log_y,
        color_discrete_map=_SERIES_COLOR, labels={**labels, "series": ""},
    )
    fig.update_layout(legend=dict(orientation="h", y=1.1, x=0))
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
st.title("Aircraft Comparison")
st.caption(
    "This airplane placed against a reference fleet by wing loading (W/S), power "
    "loading (W/P), weight and geometry. Reference figures are nominal published "
    "specs (Imperial) for comparison only — they never enter a FAR computation. "
    "Jets (no shaft power) carry no W/P."
)

project: Project = st.session_state.get("project", Project(name=""))

try:
    fleet = pd.read_csv(_REFERENCE_CSV, comment="#")
except FileNotFoundError:
    st.info(f"Reference aircraft data file not found at {_REFERENCE_CSV}.")
    st.stop()

points = _fleet_points(fleet)
subject = _subject_from_project(project)

if subject is not None:
    _render_readout(subject, points)
else:
    st.info(
        "Set the design weight (Structural Speeds, or the weight estimate / data base) "
        "to place this airplane against the fleet. The reference fleet is shown below."
    )

# --- Scatters: fleet always; "This airplane" only where the metric exists. ------ #
fleet = fleet.copy()
fleet["series"] = "Reference fleet"
fleet["w_s"] = fleet["mtow_lb"] / fleet["wing_area_ft2"].where(fleet["wing_area_ft2"] > 0)
fleet["w_p"] = fleet["mtow_lb"] / fleet["max_hp"].where(fleet["max_hp"] > 0)

if subject is not None:
    subject_row = pd.DataFrame([{
        "aircraft": subject.name, "mtow_lb": subject.mtow_lb, "oew_lb": subject.oew_lb,
        "wing_area_ft2": subject.wing_area_ft2, "max_hp": subject.power_hp,
        "wingspan_ft": subject.span, "aspect_ratio": subject.aspect_ratio_effective,
        "seats": subject.seats or None, "w_s": subject.w_s, "w_p": subject.w_p,
        "series": "This airplane",
    }])
    plot_df = pd.concat([fleet, subject_row], ignore_index=True)
else:
    plot_df = fleet

tabs = st.tabs([
    "Wing loading vs power loading", "MTOW vs OEW", "Wingspan vs MTOW",
    "Wing area vs MTOW", "Aspect ratio vs MTOW", "Seats vs MTOW",
])
with tabs[0]:
    _scatter(plot_df, "w_s", "w_p",
             {"w_s": "Wing loading W/S (lb/ft²)", "w_p": "Power loading W/P (lb/hp)"})
    st.caption("Jets (max_hp = 0) are excluded from this plot.")
with tabs[1]:
    _scatter(plot_df, "oew_lb", "mtow_lb",
             {"oew_lb": "Empty weight OEW (lb)", "mtow_lb": "MTOW (lb)"},
             log_x=True, log_y=True)
with tabs[2]:
    _scatter(plot_df, "mtow_lb", "wingspan_ft",
             {"mtow_lb": "MTOW (lb)", "wingspan_ft": "Wingspan (ft)"}, log_x=True)
with tabs[3]:
    _scatter(plot_df, "mtow_lb", "wing_area_ft2",
             {"mtow_lb": "MTOW (lb)", "wing_area_ft2": "Wing area (ft²)"}, log_x=True)
with tabs[4]:
    _scatter(plot_df, "mtow_lb", "aspect_ratio",
             {"mtow_lb": "MTOW (lb)", "aspect_ratio": "Aspect ratio"}, log_x=True)
    st.caption("Aircraft without a stored/derivable aspect ratio are omitted.")
with tabs[5]:
    _scatter(plot_df, "mtow_lb", "seats",
             {"mtow_lb": "MTOW (lb)", "seats": "Seats"}, log_x=True)

with st.expander("Reference fleet data"):
    st.dataframe(fleet.drop(columns=["series", "w_s", "w_p"]),
                 hide_index=True, use_container_width=True)
