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

Both edges of the envelope are computed (design note 45). WTENV.BAS sorts the
discretionary items by fuselage station, sweeps them cumulatively from the
minimum flight weight (``GOSUB 657`` at line 330 -- the FORWARD EDGE), re-sorts
in descending order and sweeps again (line 500 -- the AFT EDGE); one subroutine,
two calls. Each vertex carries the weight, station and waterline the program
prints (``XBAR``/``ZBAR``, lines 760/770). The ballast below reads the forward
edge alone, as the Ch 3 hand calculation does (WE-7), so the aft edge moves no
delivered quantity. The *name* of the item added at each vertex is printed by
the original and is not carried here -- see :class:`EnvelopeVertex`.

Reference: WTENV.BAS (Appendix C p382-383), Ch 3; worked example Appendix A
(stations 85.1 / 77.49 / 72.64; min flight weight 2063 @ 73.09; ballast weights
78 / 418 / 158). Both edges are printed at Appendix A p139 and plotted at p140.
"""

from __future__ import annotations

import math
from typing import List, NamedTuple, Optional, Tuple

from ..cg_cases import max_takeoff_weight
from ..derived_geometry import pct_mac_to_station, require_mac_reference
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

_FAR = "23.23/23.25"
_LB = "lb"
_IN = "in"


class EnvelopeVertex(NamedTuple):
    """One vertex of a loading-envelope edge: the three columns WTENV prints.

    ``WTENV.BAS`` 760/770 print ``XBAR``, ``ZBAR`` and the cumulative weight per
    vertex, labelled with the item just added. The label is **not** carried
    (design note 45 WE-3, amended): a name has nowhere to live in
    :class:`~sloads.models.results.LoadValue`, whose value is a float and whose
    ``label`` is cosmetic by the M4-9 contract.
    """

    weight: float
    station: float
    waterline: float


def _weight_and_station(items: List[MassItem]) -> Tuple[float, float]:
    """Total weight and weight-averaged fuselage station of a set of items."""
    w = math.fsum(it.weight_lb for it in items)
    if w == 0:
        return 0.0, 0.0
    m = math.fsum(it.weight_lb * it.x for it in items)
    return w, m / w


def _weight_and_cg(items: List[MassItem]) -> EnvelopeVertex:
    """Total weight with the weight-averaged station **and waterline**.

    The waterline half is what :func:`_sweep` needs to reproduce WTENV's printed
    ``ZBAR`` column; :func:`_weight_and_station` stays as the station-only view
    its three existing callers use, so no value they produce can move.
    """
    w, x = _weight_and_station(items)
    if w == 0:
        return EnvelopeVertex(0.0, 0.0, 0.0)
    return EnvelopeVertex(w, x, math.fsum(it.weight_lb * it.z for it in items) / w)


def _is_ballast(item: MassItem) -> bool:
    """Ballast is computed by WTENV, so it is excluded from natural loadings."""
    return "ballast" in item.name.lower()


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


def _sweep(start: EnvelopeVertex, discretionary: List[MassItem], *,
           aft: bool) -> List[EnvelopeVertex]:
    """One edge of the loading envelope -- ``WTENV.BAS`` 200-330 / 400-500.

    The original sorts the discretionary items by fuselage station, sweeps them
    cumulatively from the minimum flight weight (``GOSUB 657``), then re-sorts in
    the opposite order and sweeps again -- one subroutine, two calls, two edges.
    ``aft`` selects which call this is: ``False`` adds the most-*forward* item
    first and traces the forward boundary, ``True`` the most-aft and traces the
    aft one. Both start at ``start`` and end at the same full-loading point,
    which is what closes the envelope.

    The sort is **stable**, so items sharing a station keep their data-base
    order (note 45 WE-4). The manual's own sort is unstable -- lines 220/420
    compare strictly and swap on equality -- and additionally shuffles the blank
    records of the dimensioned array, so its printed tie order is a function of
    the array size rather than of the airplane. It cannot move a number: tied
    items share a station, so whichever is counted first the cumulative vertex
    is identical.
    """
    w, mx, mz = start.weight, start.weight * start.station, start.weight * start.waterline
    vertices = [start]
    for it in sorted(discretionary, key=lambda i: -i.x if aft else i.x):
        w += it.weight_lb
        mx += it.weight_lb * it.x
        mz += it.weight_lb * it.z
        vertices.append(EnvelopeVertex(w, mx / w, mz / w))
    return vertices


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


def loading_envelope(project: Project, *, aft: bool = False) -> List[EnvelopeVertex]:
    """One edge of the loading envelope for ``project`` -- the WE-2 single owner.

    ``aft=False`` is the forward boundary, ``aft=True`` the aft one; both are the
    same sweep with the sort reversed, exactly as ``WTENV.BAS`` calls one
    subroutine twice. Empty for a project with no weight data base.
    """
    items = project.weight.items if project.weight else []
    if not items:
        return []
    empty, minimum, discretionary = _item_buckets(items)
    return _sweep(_weight_and_cg(empty + minimum), discretionary, aft=aft)


def loading_envelope_points(project: Project) -> List[Tuple[float, float]]:
    """The forward-loading-envelope vertices (weight, station), most-forward-first.

    Shared by :func:`envelope`'s own ballast calc and the Weight/CG Envelope
    page's chart (Step D5) -- the same vertices, computed once. Kept as the
    station-only projection of :func:`loading_envelope` so its existing callers
    are untouched by note 45; new code should ask for the vertices."""
    return [(v.weight, v.station) for v in loading_envelope(project)]


def envelope(project: Project, inp: WeightEnvelopeInput) -> List[ConditionResult]:
    """Compute the weight/CG envelope, structural limits and ballast."""
    items = project.weight.items if project.weight else []
    if not items:
        raise MissingInputError("WTENV needs the itemized weight data base (weight.items)")

    empty, minimum, discretionary = _item_buckets(items)

    empty_w, empty_x = _weight_and_station(empty)
    min_w, min_x = _weight_and_station(empty + minimum)
    max_w, max_x = _weight_and_station(empty + minimum + discretionary)

    # The XLEMAC/MAC and the relation both come from the one owner (#80): the
    # typed override else the planform (C210-13), and X = XLEMAC + pct/100*MAC.
    mac_ref = require_mac_reference(project, inp)

    # The gross-weight corner falsy-derives from the MTOW SSOT (note 36,
    # OV-1/OV-2; C210-13): a blank envelope.gross_weight used to put the gross
    # corners at 0 lb, silently. Safe against the reverse G-14 fallback --
    # max_takeoff_weight reads this same raw field only when it is non-zero,
    # which is exactly when this branch does not run.
    gross_weight = inp.gross_weight or max_takeoff_weight(project, required=False)

    aft_s = pct_mac_to_station(inp.aft_gross_pct_mac, mac_ref)
    fwd_s = pct_mac_to_station(inp.fwd_gross_pct_mac, mac_ref)
    reg_s = pct_mac_to_station(inp.fwd_regardless_pct_mac, mac_ref)

    # Both edges, from one sweep called twice (WTENV.BAS 330 and 500; note 45
    # WE-1/WE-2). The ballast below keeps reading the forward edge alone -- the
    # manual's ballast is a Ch 3 hand calculation on the forward loading and
    # WE-7 leaves it there, so no delivered quantity moves.
    start = _weight_and_cg(empty + minimum)
    fwd_vertices = _sweep(start, discretionary, aft=False)
    aft_vertices = _sweep(start, discretionary, aft=True)
    fwd_seq = [(v.weight, v.station) for v in fwd_vertices]
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
            LoadValue("Aft gross point weight", gross_weight, _LB, quantity="mass", key="aft_gross_point_weight"),
            LoadValue("Forward gross point weight", gross_weight, _LB, quantity="mass",
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
    aft_cands = [p for p in fwd_seq if p[0] <= gross_weight]
    aft_ref = extreme(aft_cands, lambda p: p[0]) if aft_cands else None
    aft_reason = "no loading at/below gross weight"
    if aft_ref is not None and aft_ref[1] >= aft_s:
        # The heaviest at-or-below-gross loading already sits at/aft of the aft CG
        # limit, so the aft-CG structural case is reached by a real loading with no
        # ballast (forward ballast would land at a nonphysical station). Report the
        # degeneracy explicitly rather than a wild moment-balance station (M1-7).
        aft_ref = None
        aft_reason = "loading already at/aft of the aft-gross limit"
    add_ballast("Aft gross", "aft_gross", gross_weight, aft_s, aft_ref, aft_reason)
    # Forward gross: heaviest forward-loading point at/forward of the fwd-gross station.
    fwd_cands = [p for p in fwd_seq if p[1] <= fwd_s]
    fwd_ref = extreme(fwd_cands, lambda p: p[0]) if fwd_cands else None
    add_ballast("Forward gross", "forward_gross", gross_weight, fwd_s, fwd_ref,
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

    # The two edges. The forward one keeps its title, note, keys, labels, units
    # and values exactly (note 45 WE-6) and *gains* a waterline row per vertex;
    # its title therefore under-describes its contents until the 0.8.2 freeze
    # lapses, which is the cheaper of the two warts -- the alternative was a
    # second condition reprinting the same forward numbers. The aft edge is new,
    # so it says all three columns in its title and prefixes its keys, keeping
    # them distinguishable wherever conditions are flattened together.
    envelope_stations = ConditionResult(
        title="Forward loading envelope (weight, station)",
        far_reference=_FAR,
        values=[v for i, p in enumerate(fwd_vertices, start=1) for v in (
            LoadValue(f"Point {i} weight", p.weight, _LB, quantity="mass",
                      key=f"point_{i}_weight"),
            LoadValue(f"Point {i} station", p.station, _IN, key=f"point_{i}_station"),
            LoadValue(f"Point {i} waterline", p.waterline, _IN,
                      key=f"point_{i}_waterline"),
        )],
        note="Discretionary items added most-forward first; vertices of the forward boundary.",
    )

    aft_stations = ConditionResult(
        title="Aft loading envelope (weight, station, waterline)",
        far_reference=_FAR,
        values=[v for i, p in enumerate(aft_vertices, start=1) for v in (
            LoadValue(f"Aft point {i} weight", p.weight, _LB, quantity="mass",
                      key=f"aft_point_{i}_weight"),
            LoadValue(f"Aft point {i} station", p.station, _IN,
                      key=f"aft_point_{i}_station"),
            LoadValue(f"Aft point {i} waterline", p.waterline, _IN,
                      key=f"aft_point_{i}_waterline"),
        )],
        note="Discretionary items added most-aft first; vertices of the aft boundary. "
             "Both edges start at the minimum flight weight and end at the same full "
             "loading, closing the envelope. A vertex outside the structural CG limits "
             "is expected, not a defect (Ch 3 p21): the limits bound the loadings the "
             "pilot may fly, not the loadings the airplane can physically hold.",
    )

    return [summary, limits, ballast, envelope_stations, aft_stations]


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
