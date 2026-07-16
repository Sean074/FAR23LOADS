"""Quantitative fleet comparison -- pure, unit-testable placement of one airplane
against a reference fleet.

A companion to the visual W/S-vs-W/P and MTOW-vs-OEW scatters on the Configuration
& Layout and Weight Estimate pages: those show *where* the design sits; this module
reports it numerically -- the nearest-N similar aircraft, the wing-loading /
power-loading percentile band, and outlier flags. It is pure (no pandas, no file
access, no Streamlit); the presentation wrapper that loads the reference CSV and
renders the readout lives in ``app/components.render_fleet_comparison`` (GUI_design
§8.4).

The two calling pages expose different subject metrics -- Configuration & Layout
knows the wing area and installed power (so W/S and W/P), Weight Estimate knows the
estimated MTOW and OEW but no subject wing area -- so the nearest-N distance is
computed over **whichever metrics the subject supplies** (always log-MTOW; add W/S
and W/P when available), each normalized against the fleet spread so the axes are
commensurate. Jets (no shaft power) carry no W/P and are excluded from W/P distance
and the W/P percentile only, never from the comparator pool.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# Defaults (GUI_design §8.4, decisions D-E4-2 / D-E4-3, 2026-07-15).
DEFAULT_NEAREST_N = 3
DEFAULT_BAND = (10.0, 90.0)  # percentile band for the W/S and W/P outlier flags


@dataclass(frozen=True)
class FleetPoint:
    """One reference aircraft (nominal published specs; never a FAR input).

    ``wingspan_ft`` and ``aspect_ratio`` are optional geometry carried for the
    geometric comparison plots (span / area / AR vs. MTOW). They are not used by
    :func:`fleet_stats` -- the loading placement runs on MTOW / W/S / W/P only -- so
    older callers that omit them are unaffected.
    """
    name: str
    mtow_lb: float
    oew_lb: float
    max_hp: float
    wing_area_ft2: float
    seats: int = 0
    wingspan_ft: Optional[float] = None
    aspect_ratio: Optional[float] = None

    @property
    def w_s(self) -> Optional[float]:
        """Wing loading MTOW/S (lb/ft^2), or ``None`` when the area is unknown."""
        if self.wing_area_ft2 and self.wing_area_ft2 > 0:
            return self.mtow_lb / self.wing_area_ft2
        return None

    @property
    def w_p(self) -> Optional[float]:
        """Power loading MTOW/P (lb/hp), or ``None`` for a jet (max_hp == 0)."""
        if self.max_hp and self.max_hp > 0:
            return self.mtow_lb / self.max_hp
        return None


@dataclass(frozen=True)
class Subject:
    """The airplane being placed against the fleet.

    ``mtow_lb`` is always required (the common comparison axis). ``oew_lb``,
    ``wing_area_ft2`` and ``power_hp`` are optional -- each present metric adds a
    dimension to the nearest-N distance and enables its percentile / outlier check.
    """
    name: str
    mtow_lb: float
    oew_lb: Optional[float] = None
    wing_area_ft2: Optional[float] = None
    power_hp: Optional[float] = None

    @property
    def w_s(self) -> Optional[float]:
        if self.wing_area_ft2 and self.wing_area_ft2 > 0:
            return self.mtow_lb / self.wing_area_ft2
        return None

    @property
    def w_p(self) -> Optional[float]:
        if self.power_hp and self.power_hp > 0:
            return self.mtow_lb / self.power_hp
        return None


@dataclass(frozen=True)
class FleetStats:
    """The quantitative placement of a :class:`Subject` against a fleet.

    ``nearest`` is the closest-N ``(FleetPoint, distance)`` pairs (ascending
    distance; the normalized distance is dimensionless). ``ws_percentile`` /
    ``wp_percentile`` are the subject's percentile rank (0-100) within the fleet
    distribution, or ``None`` when the subject lacks that metric or the fleet has no
    comparators for it. ``ws_band`` / ``wp_band`` are the fleet ``(low, high)``
    percentile band values used for the outlier test. ``outliers`` names each metric
    ("W/S", "W/P") whose subject value falls outside that band.
    """
    nearest: List[Tuple[FleetPoint, float]]
    ws_percentile: Optional[float]
    wp_percentile: Optional[float]
    ws_band: Optional[Tuple[float, float]]
    wp_band: Optional[Tuple[float, float]]
    outliers: List[str]


def percentile_rank(value: float, population: Sequence[float]) -> Optional[float]:
    """Percentile rank (0-100) of ``value`` within ``population``.

    The fraction of the population at or below ``value``, times 100 -- the standard
    "weak" rank. ``None`` for an empty population.
    """
    pop = [p for p in population if p is not None]
    if not pop:
        return None
    at_or_below = sum(1 for p in pop if p <= value)
    return 100.0 * at_or_below / len(pop)


def percentile(population: Sequence[float], pct: float) -> Optional[float]:
    """The ``pct`` (0-100) percentile of ``population`` by linear interpolation.

    ``None`` for an empty population. Mirrors numpy's default ("linear") method so
    the band is the conventional one, without adding a numpy dependency.
    """
    pop = sorted(p for p in population if p is not None)
    if not pop:
        return None
    if len(pop) == 1:
        return float(pop[0])
    rank = (pct / 100.0) * (len(pop) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(pop[lo])
    frac = rank - lo
    return float(pop[lo] + (pop[hi] - pop[lo]) * frac)


def _band(population: Sequence[float], band: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    lo = percentile(population, band[0])
    hi = percentile(population, band[1])
    if lo is None or hi is None:
        return None
    return (lo, hi)


def _spread(values: Sequence[float]) -> float:
    """A positive normalizing scale for a metric: its (max - min) over the fleet.

    Falls back to ``|mean|`` then ``1.0`` so a degenerate (all-equal or zero) metric
    never divides by zero -- it simply contributes ~no distance.
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return 1.0
    spread = max(vals) - min(vals)
    if spread > 0:
        return spread
    mean = sum(vals) / len(vals)
    return abs(mean) if mean else 1.0


def fleet_stats(
    subject: Subject,
    fleet: Sequence[FleetPoint],
    *,
    n: int = DEFAULT_NEAREST_N,
    band: Tuple[float, float] = DEFAULT_BAND,
) -> FleetStats:
    """Place ``subject`` against ``fleet``: nearest-N, percentile band, outliers.

    Distance is a normalized Euclidean metric over the axes the subject supplies:
    always ``log10(MTOW)`` (weight spans orders of magnitude across the fleet), plus
    W/S and W/P when the subject has them. Each axis is divided by the fleet spread
    on that axis so the axes are commensurate. A fleet point missing an axis the
    subject has (e.g. a jet's W/P) simply contributes no term for that axis, so it
    can still rank as a neighbour on the remaining axes.
    """
    fleet = list(fleet)

    # Per-axis normalizing scales from the fleet spread (subject included so an
    # off-fleet concept still yields a finite, comparable distance).
    log_mtows = [math.log10(p.mtow_lb) for p in fleet if p.mtow_lb > 0]
    log_mtows.append(math.log10(subject.mtow_lb) if subject.mtow_lb > 0 else 0.0)
    s_mtow = _spread(log_mtows)
    ws_pop = [p.w_s for p in fleet if p.w_s is not None]
    wp_pop = [p.w_p for p in fleet if p.w_p is not None]
    s_ws = _spread(ws_pop + ([subject.w_s] if subject.w_s is not None else []))
    s_wp = _spread(wp_pop + ([subject.w_p] if subject.w_p is not None else []))

    subj_log_mtow = math.log10(subject.mtow_lb) if subject.mtow_lb > 0 else None

    def _distance(p: FleetPoint) -> float:
        sq = 0.0
        if subj_log_mtow is not None and p.mtow_lb > 0:
            sq += ((subj_log_mtow - math.log10(p.mtow_lb)) / s_mtow) ** 2
        if subject.w_s is not None and p.w_s is not None:
            sq += ((subject.w_s - p.w_s) / s_ws) ** 2
        if subject.w_p is not None and p.w_p is not None:
            sq += ((subject.w_p - p.w_p) / s_wp) ** 2
        return math.sqrt(sq)

    ranked = sorted(((p, _distance(p)) for p in fleet), key=lambda pd: pd[1])
    nearest = ranked[: max(0, n)]

    # Percentile band + outlier flags on the metrics the subject supplies.
    ws_percentile = percentile_rank(subject.w_s, ws_pop) if subject.w_s is not None else None
    wp_percentile = percentile_rank(subject.w_p, wp_pop) if subject.w_p is not None else None
    ws_band = _band(ws_pop, band) if subject.w_s is not None else None
    wp_band = _band(wp_pop, band) if subject.w_p is not None else None

    outliers: List[str] = []
    if subject.w_s is not None and ws_band is not None and not (ws_band[0] <= subject.w_s <= ws_band[1]):
        outliers.append("W/S")
    if subject.w_p is not None and wp_band is not None and not (wp_band[0] <= subject.w_p <= wp_band[1]):
        outliers.append("W/P")

    return FleetStats(
        nearest=nearest,
        ws_percentile=ws_percentile,
        wp_percentile=wp_percentile,
        ws_band=ws_band,
        wp_band=wp_band,
        outliers=outliers,
    )
