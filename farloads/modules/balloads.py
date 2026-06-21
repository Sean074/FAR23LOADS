"""Balanced-tail-load verification utility (BALLOADS.BAS, Reference 1 Ch 8-9).

BALLOADS is an **off-pipeline cross-check**, not a main-pipeline module. After
FLTLOADS balances the V-n envelope with an *approximate* horizontal-tail centre of
pressure (``XTC`` ~5% tail MAC flaps-up, ``XTF`` ~25% flaps-down; Ch 8
"Assumption"), BALLOADS recomputes the balancing load **rationally** -- resolving
it into the angle-of-attack load at 25% tail MAC (``LT25``) and the camber/elevator
load at 50% (``LT50``) -- to verify that the approximate CP was adequate.

The rational balance equations live in :func:`farloads.modules.select.htail_balance`
(oracle-locked in Step C6); per the project convention this utility **reuses** that
routine rather than re-deriving it, so the verification can never silently drift
from the production balance. BALLOADS' contribution is the *comparison*: for each
balanced V-n condition it converts the rational CP (% tail MAC) back to a fuselage
station ``XT_rational`` and reports it against FLTLOADS' assumed ``XTC``/``XTF``.

It also makes the Ch 9 teaching point that the elevator load is **not** always
opposite the stabilizer load: the per-condition elevator load (reusing SELECT's
:func:`_elevator_load`) is reported alongside the total.

Validation: Appendix A / Ch 9 case-202 hand-calc -- the up balancing load with
flaps retracted is ``LT = 519.845 lb`` (LT25 +907.62, LT50 -387.78, elevator
deflection -5.39 deg, CP 6.35% tail MAC), matching SELECT's rational result.
"""

from __future__ import annotations

from typing import Dict, List

from ..models import CgCase, ConditionResult, LoadValue, ModuleResult, Project, VnPoint
from ..registry import register
from .select import _elevator_load, _envelope, htail_balance

MODULE_NAME = "balloads"


def _rational_station(cp_pct: float, xt25: float, xt50: float) -> float:
    """Fuselage station of the rational tail CP, in inches.

    ``cp_pct`` is the load centre of pressure in percent tail MAC (25 -> ``xt25``,
    50 -> ``xt50``); the station scales linearly between the two known stations."""
    return xt25 + (cp_pct - 25.0) * (xt50 - xt25) / 25.0


def verify_balancing(project: Project) -> List[Dict[str, float]]:
    """Rationally recompute the balancing tail load for every flaps-retracted V-n
    point and pair it with FLTLOADS' approximate CP station.

    Mirrors the search set of :func:`select.select_htail_balancing` (every
    flaps-retracted point carries a balancing load; the governing up/down loads do
    not necessarily fall on the explicitly trimmed ``BAL`` conditions). Returns one
    dict per point with the rational split (``LT25``/``LT50``/``DELTA``/``LT``/
    ``CP``), the elevator load, the rational station ``XT`` and the approximate
    ``XTC`` FLTLOADS assumed, plus their difference ``DXT``.
    """
    ti, fl = project.tail_loads, project.flight_loads
    if ti is None or fl is None:
        raise ValueError("balloads needs Project.tail_loads and Project.flight_loads")
    cg_map: Dict[str, CgCase] = {c.name: c for c in fl.cg_cases}
    flaps: Dict[str, bool] = {c.name: c.flaps_down for c in fl.configurations}

    rows: List[Dict[str, float]] = []
    for p in _envelope(project).vn:
        if flaps.get(p.config, False):
            continue
        cg = cg_map.get(p.cg)
        if cg is None:
            continue
        b = htail_balance(p, cg, fl.xw, fl.zw, ti)
        xt = _rational_station(b["CP"], ti.xt25, ti.xt50)
        rows.append({
            "point": p,
            "LT25": b["LT25"], "LT50": b["LT50"], "DELTA": b["DELTA"],
            "LT": b["LT"], "CP": b["CP"],
            "ELEV": _elevator_load(b["LT50"], b["LT25"], ti),
            "XT": xt, "XTC": fl.xtc, "DXT": xt - fl.xtc,
        })
    return rows


def _condition(row: Dict[str, float], note: str) -> ConditionResult:
    p: VnPoint = row["point"]
    return ConditionResult(
        title=f"Balanced tail load {p.condition} (case {p.case}, {p.cg}, {p.altitude_ft:.0f} ft)",
        far_reference="23.421",
        values=[
            LoadValue("Total balancing load LT", row["LT"], "lb"),
            LoadValue("AoA load LT25 (cp 25%)", row["LT25"], "lb"),
            LoadValue("Camber/elevator load LT50 (cp 50%)", row["LT50"], "lb"),
            LoadValue("Elevator deflection (TE dn +)", row["DELTA"], "deg"),
            LoadValue("Elevator load", row["ELEV"], "lb"),
            LoadValue("Rational CP", row["CP"], "% tail MAC"),
            LoadValue("Rational CP station XT", row["XT"], "in"),
            LoadValue("FLTLOADS approx station XTC", row["XTC"], "in"),
            LoadValue("Station error (rational - approx)", row["DXT"], "in"),
            LoadValue("V (EAS)", p.v_eas_kt, "kt(EAS)"),
        ],
        note=note,
    )


def run(project: Project) -> ModuleResult:
    """Verify FLTLOADS' approximate balancing-tail CP against the rational
    recomputation (reusing SELECT's balance routine) for each balanced condition."""
    rows = verify_balancing(project)
    note = ("Concept mode -- unverified extrapolation past the FAR23 band."
            if project.is_concept else "")
    return ModuleResult(module=MODULE_NAME,
                        conditions=[_condition(r, note) for r in rows])


register(MODULE_NAME, run)
