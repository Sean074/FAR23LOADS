"""Weight vs CG envelope of useful loadings, ported from WTENV.BAS (H. C. McMaster).

WTENV shares WTONECG's weight data base (the itemized ``Project.weight.items``
list, partitioned into empty / minimum / discretionary sectors). From it the
program computes the minimum flight weight, the envelope enclosing every
discretionary loading, the structural CG-limit stations, and the ballast needed
to bring a practical loading up to each structural limit for stress analysis and
flight test (Reference 1 Ch 3).

Structural limit stations (Ch 3):

    X(limit) = XLEMAC + (percent_of_MAC / 100) * MAC          [from WINGGEOM]

Ballast (chosen loading point on the envelope -> structural limit) by moment
balance about the airplane nose:

    WB = WL - WA                       ballast weight
    XB = (WL*XL - WA*XA) / WB          ballast station

where (WL, XL) is the structural limit and (WA, XA) the reference envelope point.
The reference points are selected as in the worked example (Ch 3 p21-22), each
the heaviest forward-loading-envelope vertex still within the point's limit:
* aft gross      -> the heaviest loading NOT exceeding gross weight (== the full
                    discretionary loading when that is itself at/under gross, as
                    on the GA6; on databases whose full loading exceeds gross the
                    reference is the last vertex at/below gross -- M1-7);
* forward gross  -> heaviest forward-loading point with X at/forward of the
                    forward-gross station, ballasted at gross weight;
* forward regardless -> heaviest forward-loading point at/below the reduced
                    weight at which that limit applies.
When no vertex qualifies (or the reference already meets the target weight, or the
resulting moment-balance station falls outside the fuselage extent) the ballast row
carries an explicit "none -- <reason>" marker instead of vanishing or printing a
nonphysical station (M1-7 / M1-11). The fuselage extent is read from an explicit
``envelope.fuselage_nose_x``/``fuselage_tail_x`` override, else the Step G1 fuselage
outline, else the station-0 datum (only a station ahead of the nose is rejected).

Note on a preserved original-suite inconsistency: the manual's *hand* ballast
calc for the aft-gross point rounded the limit station to 85.0 (giving 78 lb @
103.7, the value its WTONECG data base then carried), whereas the precise station
is 85.107. Per Decision 3 (modernise the math) this module reports the exact
moment-balance station; the ballast *weights* match the manual exactly.

Reference: WTENV.BAS, Ch 3; worked example Appendix A (stations 85.1 / 77.49 /
72.64; min flight weight 2063 @ 73.09; ballast weights 78 / 418 / 158).
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from ..models import (
    ConditionResult,
    LoadValue,
    MassItem,
    MassItemKind,
    MissingInputError,
    ModuleResult,
    Project,
    WeightEnvelopeInput,
)
from ..picks import extreme
from ..registry import register
from .wing_geometry import surface_properties

_FAR = "23.23/23.25"
_LB = "lb"
_IN = "in"


def _weight_and_station(items: List[MassItem]) -> Tuple[float, float]:
    """Total weight and weight-averaged fuselage station of a set of items."""
    w = math.fsum(it.weight_lb for it in items)
    if w == 0:
        return 0.0, 0.0
    m = math.fsum(it.weight_lb * it.x for it in items)
    return w, m / w


def _is_ballast(item: MassItem) -> bool:
    """Ballast is computed by WTENV, so it is excluded from natural loadings."""
    return "ballast" in item.name.lower()


def _xlemac_mac(project: Project, env: WeightEnvelopeInput) -> Tuple[float, float]:
    """Wing XLEMAC and MAC, read from the geometry slice (else direct override)."""
    if env.xlemac is not None and env.mac is not None:
        return env.xlemac, env.mac
    if project.geometry is not None:
        surf = project.geometry.by_name(env.wing_surface)
        if surf is not None:
            r = surface_properties(surf)
            mac = next(v.value for v in r.values if v.key == "mac")
            xlemac = next(v.value for v in r.values if v.key == "xle_mac_station_of_mac_le")
            return xlemac, mac
    raise MissingInputError(
        "WTENV needs wing XLEMAC/MAC: add a 'wing' geometry surface or set "
        "envelope.xlemac/envelope.mac"
    )


def _fuselage_extent(
    project: Project, env: WeightEnvelopeInput
) -> Tuple[float, Optional[float]]:
    """Physical fore/aft fuselage station bounds for the ballast-station sanity
    check (M1-11).

    Explicit ``env.fuselage_nose_x``/``fuselage_tail_x`` win; else the Step G1
    fuselage outline (``Project.geometry.fuselage``) supplies min/max section
    station; failing both, degrade to the station-0 datum with an unbounded tail
    (``None``) -- only a station *ahead of the nose datum* is then rejected. The
    tail bound is ``None`` when unknown so a genuine aft loading is never falsely
    flagged.
    """
    if env.fuselage_nose_x is not None and env.fuselage_tail_x is not None:
        return env.fuselage_nose_x, env.fuselage_tail_x
    fus = project.geometry.fuselage if project.geometry is not None else None
    if fus is not None and fus.sections:
        xs = [s.x for s in fus.sections]
        return min(xs), max(xs)
    return 0.0, None


def _forward_sequence(start: Tuple[float, float], discretionary: List[MassItem]) -> List[Tuple[float, float]]:
    """Cumulative (weight, station) loading the most-forward items first.

    Starting from ``start`` (the minimum flight weight), the discretionary items
    are added in ascending fuselage-station order; each cumulative point is a
    vertex of the forward boundary of the loading envelope.
    """
    w, m = start[0], start[0] * start[1]
    points = [(w, start[1])]
    for it in sorted(discretionary, key=lambda i: i.x):
        w += it.weight_lb
        m += it.weight_lb * it.x
        points.append((w, m / w))
    return points


def _ballast(wl: float, xl: float, wa: float, xa: float) -> Optional[Tuple[float, float]]:
    """Ballast (weight, station) bringing point (wa, xa) up to limit (wl, xl)."""
    wb = wl - wa
    if wb <= 0:
        return None  # the reference loading already meets/exceeds the limit
    return wb, (wl * xl - wa * xa) / wb


def _item_buckets(items: List[MassItem]) -> Tuple[List[MassItem], List[MassItem], List[MassItem]]:
    empty = [it for it in items if it.kind == MassItemKind.EMPTY]
    minimum = [it for it in items if it.kind == MassItemKind.MINIMUM]
    discretionary = [
        it for it in items
        if it.kind == MassItemKind.DISCRETIONARY and not _is_ballast(it)
    ]
    return empty, minimum, discretionary


def loading_envelope_points(project: Project) -> List[Tuple[float, float]]:
    """The forward-loading-envelope vertices (weight, station), most-forward-first.

    Shared by :func:`envelope`'s own ballast calc and the Weight/CG Envelope
    page's chart (Step D5) -- the same vertices, computed once."""
    items = project.weight.items if project.weight else []
    if not items:
        return []
    empty, minimum, discretionary = _item_buckets(items)
    min_w, min_x = _weight_and_station(empty + minimum)
    return _forward_sequence((min_w, min_x), discretionary)


def envelope(project: Project, inp: WeightEnvelopeInput) -> List[ConditionResult]:
    """Compute the weight/CG envelope, structural limits and ballast."""
    items = project.weight.items if project.weight else []
    if not items:
        raise MissingInputError("WTENV needs the itemized weight data base (weight.items)")

    empty, minimum, discretionary = _item_buckets(items)

    empty_w, empty_x = _weight_and_station(empty)
    min_w, min_x = _weight_and_station(empty + minimum)
    max_w, max_x = _weight_and_station(empty + minimum + discretionary)

    xlemac, mac = _xlemac_mac(project, inp)

    def station(pct: float) -> float:
        return xlemac + pct / 100.0 * mac

    aft_s = station(inp.aft_gross_pct_mac)
    fwd_s = station(inp.fwd_gross_pct_mac)
    reg_s = station(inp.fwd_regardless_pct_mac)

    fwd_seq = _forward_sequence((min_w, min_x), discretionary)
    nose_x, tail_x = _fuselage_extent(project, inp)

    summary = ConditionResult(
        title="Weight envelope summary",
        far_reference=_FAR,
        values=[
            LoadValue("Empty weight", empty_w, _LB, quantity="mass", key="empty_weight"),
            LoadValue("Empty weight station", empty_x, _IN, key="empty_weight_station"),
            LoadValue("Minimum flight weight", min_w, _LB, quantity="mass", key="minimum_flight_weight"),
            LoadValue("Minimum flight weight station", min_x, _IN, key="minimum_flight_weight_station"),
            LoadValue("Maximum loading weight", max_w, _LB, quantity="mass", key="maximum_loading_weight"),
            LoadValue("Maximum loading station", max_x, _IN, key="maximum_loading_station"),
        ],
    )

    limits = ConditionResult(
        title="Structural CG-limit stations and loadings",
        far_reference=_FAR,
        values=[
            LoadValue("Aft gross station", aft_s, _IN, key="aft_gross_station"),
            LoadValue("Forward gross station", fwd_s, _IN, key="forward_gross_station"),
            LoadValue("Forward regardless station", reg_s, _IN, key="forward_regardless_station"),
            LoadValue("Aft gross point weight", inp.gross_weight, _LB, quantity="mass", key="aft_gross_point_weight"),
            LoadValue("Forward gross point weight", inp.gross_weight, _LB, quantity="mass",
                key="forward_gross_point_weight"),
            LoadValue("Forward regardless point weight", inp.fwd_regardless_weight, _LB, quantity="mass",
                key="forward_regardless_point_weight"),
            LoadValue("Minimum weight point weight", min_w, _LB, quantity="mass", key="minimum_weight_point_weight"),
            LoadValue("Minimum weight point station", min_x, _IN, key="minimum_weight_point_station"),
        ],
        note="The four points (aft gross, fwd gross, fwd regardless, min weight) feed FLTLOADS.",
    )

    # Ballast reference points (see module docstring). Each reference is the
    # heaviest forward-loading-envelope vertex that stays within the point's
    # weight/station limit. When no vertex qualifies, or the reference already
    # meets the target weight, an explicit marker row is emitted rather than
    # silently dropping the structural point (M1-7).
    ballast_values: List[LoadValue] = []

    def add_ballast(
        label: str,
        key: str,
        wl: float,
        xl: float,
        ref: Optional[Tuple[float, float]],
        no_ref_reason: str,
    ) -> None:
        if ref is None:
            ballast_values.append(
                LoadValue(f"{label} ballast (none -- {no_ref_reason})", 0.0, _LB,
                          quantity="mass", key=f"{key}_ballast_weight")
            )
            return
        b = _ballast(wl, xl, ref[0], ref[1])
        if b is None:
            ballast_values.append(
                LoadValue(
                    f"{label} ballast (none -- loading already at/above target weight)",
                    0.0, _LB, quantity="mass", key=f"{key}_ballast_weight",
                )
            )
            return
        # Physical sanity: a moment-balance station outside the fuselage extent
        # (e.g. forward of the nose datum, as on synthetic over-gross concept
        # databases whose loadings all sit aft of the forward limit) is
        # nonphysical -- report the degeneracy explicitly rather than a wild
        # station (M1-11).
        xb = b[1]
        if xb < nose_x or (tail_x is not None and xb > tail_x):
            reason = (
                f"moment-balance station {xb:.0f} in is ahead of the station-{nose_x:.0f} "
                "datum; all loadings sit aft of the limit"
                if tail_x is None
                else f"moment-balance station {xb:.0f} in is outside the fuselage "
                f"extent [{nose_x:.0f}, {tail_x:.0f}]"
            )
            ballast_values.append(
                LoadValue(f"{label} ballast (none -- {reason})", 0.0, _LB,
                          quantity="mass", key=f"{key}_ballast_weight")
            )
            return
        ballast_values.append(LoadValue(f"{label} ballast weight", b[0], _LB,
                                        quantity="mass", key=f"{key}_ballast_weight"))
        ballast_values.append(LoadValue(f"{label} ballast station", b[1], _IN,
                                        key=f"{key}_ballast_station"))

    # Aft gross: heaviest loading NOT exceeding gross weight (the manual's Ch 3
    # p22 reference). Equals the full loading when that is itself at/under gross
    # (as on the GA6 -> 78 lb); M1-7 fixed the prior code, which used the full
    # loading unconditionally and returned 0 ballast whenever it exceeded gross.
    aft_cands = [p for p in fwd_seq if p[0] <= inp.gross_weight]
    aft_ref = extreme(aft_cands, lambda p: p[0]) if aft_cands else None
    aft_reason = "no loading at/below gross weight"
    if aft_ref is not None and aft_ref[1] >= aft_s:
        # The heaviest at-or-below-gross loading already sits at/aft of the aft CG
        # limit, so the aft-CG structural case is reached by a real loading with no
        # ballast (forward ballast would land at a nonphysical station). Report the
        # degeneracy explicitly rather than a wild moment-balance station (M1-7).
        aft_ref = None
        aft_reason = "loading already at/aft of the aft-gross limit"
    add_ballast("Aft gross", "aft_gross", inp.gross_weight, aft_s, aft_ref, aft_reason)
    # Forward gross: heaviest forward-loading point at/forward of the fwd-gross station.
    fwd_cands = [p for p in fwd_seq if p[1] <= fwd_s]
    fwd_ref = extreme(fwd_cands, lambda p: p[0]) if fwd_cands else None
    add_ballast("Forward gross", "forward_gross", inp.gross_weight, fwd_s, fwd_ref,
                "no loading forward of the fwd-gross station")
    # Forward regardless: heaviest forward-loading point at/below the reduced weight.
    reg_cands = [p for p in fwd_seq if p[0] <= inp.fwd_regardless_weight]
    reg_ref = extreme(reg_cands, lambda p: p[0]) if reg_cands else None
    add_ballast("Forward regardless", "forward_regardless", inp.fwd_regardless_weight,
                reg_s, reg_ref,
                "no loading at/below the regardless weight")

    ballast = ConditionResult(
        title="Ballast to reach the structural limits",
        far_reference=_FAR,
        values=ballast_values,
        note="Ballast station by moment balance; weights match the manual exactly.",
    )

    envelope_stations = ConditionResult(
        title="Forward loading envelope (weight, station)",
        far_reference=_FAR,
        values=[v for i, (w, x) in enumerate(fwd_seq, start=1) for v in (
            LoadValue(f"Point {i} weight", w, _LB, quantity="mass",
                      key=f"point_{i}_weight"),
            LoadValue(f"Point {i} station", x, _IN, key=f"point_{i}_station"),
        )],
        note="Discretionary items added most-forward first; vertices of the forward boundary.",
    )

    return [summary, limits, ballast, envelope_stations]


# --------------------------------------------------------------------------- #
# Project entry point + registration
# --------------------------------------------------------------------------- #
MODULE_NAME = "weight_envelope"


def run(project: Project) -> ModuleResult:
    """Run WTENV against a :class:`Project`'s weight data base + envelope limits."""
    if project.weight is None or project.weight.envelope is None:
        raise MissingInputError("Project has no 'weight.envelope' inputs for the weight_envelope module")
    return ModuleResult(module=MODULE_NAME, conditions=envelope(project, project.weight.envelope))


register(MODULE_NAME, run)
