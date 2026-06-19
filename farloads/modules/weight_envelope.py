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
The reference points are selected as in the worked example (Ch 3 p21-22):
* aft gross      -> the full discretionary loading (heaviest, aft-most);
* forward gross  -> heaviest forward-loading point with X at/forward of the
                    forward-gross station, ballasted at gross weight;
* forward regardless -> heaviest forward-loading point at/below the reduced
                    weight at which that limit applies.

Note on a preserved original-suite inconsistency: the manual's *hand* ballast
calc for the aft-gross point rounded the limit station to 85.0 (giving 78 lb @
103.7, the value its WTONECG data base then carried), whereas the precise station
is 85.107. Per Decision 3 (modernise the math) this module reports the exact
moment-balance station; the ballast *weights* match the manual exactly.

Reference: WTENV.BAS, Ch 3; worked example Appendix A (stations 85.1 / 77.49 /
72.64; min flight weight 2063 @ 73.09; ballast weights 78 / 418 / 158).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..models import (
    ConditionResult,
    LoadValue,
    MassItem,
    MassItemKind,
    ModuleResult,
    Project,
    WeightEnvelopeInput,
)
from ..registry import register
from .wing_geometry import surface_properties

_FAR = "23.23/23.25"
_LB = "lb"
_IN = "in"


def _weight_and_station(items: List[MassItem]) -> Tuple[float, float]:
    """Total weight and weight-averaged fuselage station of a set of items."""
    w = sum(it.weight_lb for it in items)
    if w == 0:
        return 0.0, 0.0
    m = sum(it.weight_lb * it.x for it in items)
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
            mac = next(v.value for v in r.values if v.label == "MAC")
            xlemac = next(v.value for v in r.values if v.label.startswith("XLE(MAC)"))
            return xlemac, mac
    raise ValueError(
        "WTENV needs wing XLEMAC/MAC: add a 'wing' geometry surface or set "
        "envelope.xlemac/envelope.mac"
    )


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


def envelope(project: Project, inp: WeightEnvelopeInput) -> List[ConditionResult]:
    """Compute the weight/CG envelope, structural limits and ballast."""
    items = project.weight.items if project.weight else []
    if not items:
        raise ValueError("WTENV needs the itemized weight data base (weight.items)")

    empty = [it for it in items if it.kind == MassItemKind.EMPTY]
    minimum = [it for it in items if it.kind == MassItemKind.MINIMUM]
    discretionary = [
        it for it in items
        if it.kind == MassItemKind.DISCRETIONARY and not _is_ballast(it)
    ]

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

    summary = ConditionResult(
        title="Weight envelope summary",
        far_reference=_FAR,
        values=[
            LoadValue("Empty weight", empty_w, _LB, quantity="mass"),
            LoadValue("Empty weight station", empty_x, _IN),
            LoadValue("Minimum flight weight", min_w, _LB, quantity="mass"),
            LoadValue("Minimum flight weight station", min_x, _IN),
            LoadValue("Maximum loading weight", max_w, _LB, quantity="mass"),
            LoadValue("Maximum loading station", max_x, _IN),
        ],
    )

    limits = ConditionResult(
        title="Structural CG-limit stations and loadings",
        far_reference=_FAR,
        values=[
            LoadValue("Aft gross station", aft_s, _IN),
            LoadValue("Forward gross station", fwd_s, _IN),
            LoadValue("Forward regardless station", reg_s, _IN),
            LoadValue("Aft gross point weight", inp.gross_weight, _LB, quantity="mass"),
            LoadValue("Forward gross point weight", inp.gross_weight, _LB, quantity="mass"),
            LoadValue("Forward regardless point weight", inp.fwd_regardless_weight, _LB, quantity="mass"),
            LoadValue("Minimum weight point weight", min_w, _LB, quantity="mass"),
            LoadValue("Minimum weight point station", min_x, _IN),
        ],
        note="The four points (aft gross, fwd gross, fwd regardless, min weight) feed FLTLOADS.",
    )

    # Ballast reference points (see module docstring).
    ballast_values: List[LoadValue] = []

    def add_ballast(label: str, wl: float, xl: float, ref: Optional[Tuple[float, float]]) -> None:
        if ref is None:
            return
        b = _ballast(wl, xl, ref[0], ref[1])
        if b is None:
            ballast_values.append(LoadValue(f"{label} ballast", 0.0, _LB, quantity="mass"))
            return
        ballast_values.append(LoadValue(f"{label} ballast weight", b[0], _LB, quantity="mass"))
        ballast_values.append(LoadValue(f"{label} ballast station", b[1], _IN))

    # Aft gross: reference is the full (max) discretionary loading.
    add_ballast("Aft gross", inp.gross_weight, aft_s, (max_w, max_x))
    # Forward gross: heaviest forward-loading point at/forward of the fwd-gross station.
    fwd_cands = [p for p in fwd_seq if p[1] <= fwd_s]
    fwd_ref = max(fwd_cands, key=lambda p: p[0]) if fwd_cands else None
    add_ballast("Forward gross", inp.gross_weight, fwd_s, fwd_ref)
    # Forward regardless: heaviest forward-loading point at/below the reduced weight.
    reg_cands = [p for p in fwd_seq if p[0] <= inp.fwd_regardless_weight]
    reg_ref = max(reg_cands, key=lambda p: p[0]) if reg_cands else None
    add_ballast("Forward regardless", inp.fwd_regardless_weight, reg_s, reg_ref)

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
            LoadValue(f"Point {i} weight", w, _LB, quantity="mass"),
            LoadValue(f"Point {i} station", x, _IN),
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
        raise ValueError("Project has no 'weight.envelope' inputs for the weight_envelope module")
    return ModuleResult(module=MODULE_NAME, conditions=envelope(project, project.weight.envelope))


register(MODULE_NAME, run)
