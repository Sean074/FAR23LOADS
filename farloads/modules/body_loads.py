"""Net fuselage loads -- the body analogue of NETLOADS (Reference 1 Ch 15).

Ch 15 ("Net Fuselage Loads") gives a *suggested procedure* rather than a ported
``.BAS`` program: the fuselage is a simple beam carrying the inertia of the
fuselage mass items reacted by the air load on the tail and the wing-attach
reactions. For each critical fuselage condition (selected by SELECT, R5) this
module:

  1. multiplies each fuselage station weight by the linear load factor ``NZ`` to
     get its inertia force (``fz = -NZ*w``, down for positive NZ);
  2. applies the balancing tail air load ``LT`` at the tail station;
  3. reacts the residual with the wing at the 25% wing-MAC station
     (``R = NZ*W_fus - LT``) so the body is in vertical equilibrium;
  4. integrates nose->tail to the running shear ``Sz`` and bending ``Myy``.

There is **no printed station-by-station oracle** (Ch 15 ships no program), so the
result is validated by equilibrium closure: the shear returns to ~0 aft of the
wing reaction, and the cumulative applied vertical force is zero. The fuselage
station weights (``Project.fuselage_mass``) should already exclude the wing mass
outside the fuselage, per Ch 15.

Coordinates are the airplane body axes (fuselage station X aft, waterline Z up),
pounds and inch-pounds.
"""

from __future__ import annotations

from typing import Dict, List

from ..models import (
    BodyLoadResult,
    BodyStationLoad,
    ModuleResult,
    Project,
    VnPoint,
)
from ..registry import register
from .flight_envelope import build_envelope
from .select import select_fuselage

MODULE_NAME = "body_loads"


def _tail_station(project: Project, fallback: float) -> float:
    """Fuselage station of the tail air load (25% h-tail MAC) if available."""
    ti = project.tail_loads
    return ti.xt25 if ti is not None and ti.xt25 else fallback


def body_distribution(stations, nz: float, tail_load: float, tail_x: float,
                      wing_x: float) -> List[BodyStationLoad]:
    """Net body shear/bending for one condition: inertia + tail load + wing
    reaction, integrated nose->tail."""
    w_fus = sum(w for _, w in stations)
    wing_reaction = nz * w_fus - tail_load          # vertical equilibrium

    # Applied vertical point loads (x, fz): station inertia, tail air load, wing.
    points: List[tuple] = [(x, -nz * w) for x, w in stations]
    points.append((tail_x, tail_load))
    points.append((wing_x, wing_reaction))
    points.sort(key=lambda xf: xf[0])

    out: List[BodyStationLoad] = []
    sz = 0.0
    myy = 0.0
    prev_x = points[0][0]
    for x, fz in points:
        myy += sz * (x - prev_x)                    # area under the shear curve
        sz += fz
        prev_x = x
        out.append(BodyStationLoad(x=x, fx=0.0, fy=0.0, fz=fz, sx=0.0, sy=0.0,
                                   sz=sz, mxx=0.0, myy=myy, mzz=0.0))
    return out


def build_body_loads(project: Project) -> List[BodyLoadResult]:
    """Net fuselage load distribution for each critical fuselage condition."""
    fm = project.fuselage_mass
    fl = project.flight_loads
    if fm is None or not fm.stations or fl is None:
        raise ValueError("body_loads needs 'fuselage_mass' stations and 'flight_loads'")
    vn: Dict[int, VnPoint] = {p.case: p for p in build_envelope(project).vn}
    stations = [(s.x, s.weight_lb) for s in fm.stations]
    wing_x = fl.xw
    tail_x = _tail_station(project, max(s.x for s in fm.stations))

    results: List[BodyLoadResult] = []
    for cond in select_fuselage(project):
        p = vn.get(cond.case)
        if p is None:
            continue
        rows = body_distribution(stations, p.nz, p.lt, tail_x, wing_x)
        results.append(BodyLoadResult(case=cond.label, stations=rows))
    return results


def body_load_rows(results: List[BodyLoadResult]) -> List[Dict[str, str]]:
    """One CSV row per fuselage station per condition."""
    rows: List[Dict[str, str]] = []
    for r in results:
        for s in r.stations:
            rows.append({
                "Case": r.case, "X": f"{s.x:.3f}", "Fz": f"{s.fz:.2f}",
                "Sz": f"{s.sz:.2f}", "Myy": f"{s.myy:.1f}",
            })
    return rows


def run(project: Project) -> ModuleResult:
    """Run the fuselage net-load distribution (returns an empty report; the
    station table is consumed via ``build_body_loads`` / the CSV)."""
    build_body_loads(project)
    return ModuleResult(module=MODULE_NAME, conditions=[])


register(MODULE_NAME, run)
