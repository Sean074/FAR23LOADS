"""Concept distributed-loads closure suite (backlog Step P1-2).

Concept mode has **no printed oracle** above 12,500 lb (it extrapolates past the
FAR23 calibration band), so physics-*closure* is its only validation. Step C4's
``test_sbeam_bridge.py::test_concept_closure`` proved closure for the **wing
only**; this module extends it to every component of a full concept airframe --
wing, body, tail and the three control surfaces -- driven through the P1-1
regional-jet fixture (``examples/concept_regional_jet.project.json``).

Two kinds of check appear here:

* **Physics closure** -- an equilibrium identity the concept code path must
  satisfy, evaluated on the concept fixture so a concept-mode blow-up (NaN, an
  unbalanced result) cannot pass silently:
    - wing:  ``LZW + LT == Nz*W``            (vertical equilibrium, FLTLOADS)
    - tail:  ``LT*(Xt - Xcg) == LZW*(Xcg - Xw) - DX*(Zcg - Zw) + M(W+F)``
             (balancing tail load reacts the pitching moment about the CG)
    - body:  terminal cumulative shear ``== 0`` (the fuselage net distribution
             is built free-free: inertia + tail + wing reaction sum to zero)
* **Cross-module ties** -- one module's output reconciles against its upstream
  source, so a divergence in the concept branch of either is caught:
    - tail:  TAILDIST carries SELECT's ``lt25``/``lt50`` split verbatim.
    - control: the distributed-loads (``build_*``) load matches the analysis
      (``run``) report load for the same surface.
* **Export integrity** -- every component's nodal FORCE set (and its re-parsed
  ``FORCE`` cards) sums to that component's root/total at ULTIMATE, so the whole
  concept airframe exports cleanly through ``sbeam_bridge``.

References: Ref 1 Ch 7 (wing airload), Ch 8/9 (tail balancing), Ch 15 (fuselage
net loads); the closure strategy is Phase-C invariant 2 (``docs/30_future/
01_concept_loads_plan.md`` §2).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.modules import aileron as aileron_mod  # noqa: E402
from sloads.modules import flap as flap_mod  # noqa: E402
from sloads.modules import tab as tab_mod  # noqa: E402
from sloads.modules.body_loads import build_body_loads  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.net_loads import build_net_loads  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.taildist import build_tail_chordwise  # noqa: E402
from helpers import parse_cards  # noqa: E402  (shared free-field reader)

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "concept_regional_jet.project.json",
)

_SF = sb._SF  # ULTIMATE_FACTOR (1.5); the bridge exports LIMIT x _SF.


def _concept_project():
    """The P1-1 concept fixture with its envelope + critical set materialised."""
    p = io.load_project(_EXAMPLE)
    assert p.is_concept, "fixture must be a concept (category=C) project"
    p.envelope = build_envelope(p)
    p.envelope.critical = build_critical(p)
    return p


# --------------------------------------------------------------------------- #
# Wing -- total lift = Nz*W (FLTLOADS vertical equilibrium) + nodal export sum
# --------------------------------------------------------------------------- #
def test_wing_lift_equals_nW():
    """Every balanced V-n point closes vertically: ``LZW + LT == Nz*W``."""
    p = _concept_project()
    weight = {c.name: c.weight_lb for c in p.flight_loads.cg_cases}
    assert p.envelope.vn
    for vp in p.envelope.vn:
        nw = vp.nz * weight[vp.cg]
        assert math.isclose(vp.lzw + vp.lt, nw, rel_tol=1e-6, abs_tol=1e-6)


def test_wing_nodal_loads_sum_to_root():
    """The exported wing nodal FORCE set sums to the NETLOADS root at ULTIMATE."""
    results = build_net_loads(_concept_project()).wing_net
    assert results
    for r in results:
        nodes = sb.wing_nodal_loads(r)
        root = r.stations[0]
        y0 = nodes[0].y
        assert math.isclose(sum(n.fz for n in nodes), root.sz * _SF, rel_tol=1e-9, abs_tol=1e-6)
        assert math.isclose(sum(n.my for n in nodes), root.myy * _SF, rel_tol=1e-9, abs_tol=1e-3)
        # Bending = FORCE moments about the root strip.
        assert math.isclose(sum(n.fz * (n.y - y0) for n in nodes), root.mxx * _SF,
                            rel_tol=1e-6, abs_tol=1.0)


# --------------------------------------------------------------------------- #
# Tail -- balancing load reacts the pitching moment about the CG (Ch 8/9),
# TAILDIST carries SELECT's split, and the nodal set sums to LT25 + LT50.
# --------------------------------------------------------------------------- #
def test_tail_balancing_moment_closure():
    """``LT*(Xt - Xcg)`` reacts the wing-plus-inertia pitching moment about the CG."""
    p = _concept_project()
    fl = p.flight_loads
    cg = {c.name: c for c in fl.cg_cases}
    xt = {tb.case: tb.tail_cp_station for tb in p.envelope.tail_balance}
    for vp in p.envelope.vn:
        c = cg[vp.cg]
        lhs = vp.lt * (xt[vp.case] - c.xcg)
        rhs = vp.lzw * (c.xcg - fl.xw) - vp.dx * (c.zcg - fl.zw) + vp.m_wf
        assert math.isclose(lhs, rhs, rel_tol=1e-6, abs_tol=1e-3)


def test_taildist_carries_select_split():
    """Cross-module tie: TAILDIST's ``lt25``/``lt50`` are SELECT's verbatim, so the
    chordwise distribution sums back to the SELECT-critical tail load."""
    p = _concept_project()
    crit = {c.case_ref.case_id: c for c in p.envelope.critical.conditions if c.case_ref}
    results = build_tail_chordwise(p)
    assert results
    for r in results:
        c = crit.get(r.case_ref.case_id)
        assert c is not None, f"no SELECT condition for {r.case}"
        assert c.lt25 == r.lt25 and c.lt50 == r.lt50


def test_tail_nodal_loads_sum_to_total():
    """The exported tail nodal FORCE set sums to ULTIMATE ``LT25 + LT50``."""
    results = build_tail_chordwise(_concept_project())
    assert results
    for r in results:
        forces = sb._tail_nodal_forces(r)
        assert math.isclose(sum(forces), (r.lt25 + r.lt50) * _SF, rel_tol=1e-9, abs_tol=1e-6)


# --------------------------------------------------------------------------- #
# Body -- the fuselage net distribution is built free-free (Ch 15): inertia +
# tail air load + wing reaction sum to zero, so the terminal shear is zero.
# --------------------------------------------------------------------------- #
def test_body_vertical_equilibrium():
    """The net fuselage distribution closes: applied Fz sums to 0 (terminal Sz = 0)."""
    results = build_body_loads(_concept_project())
    assert results
    for r in results:
        applied = sum(s.fz for s in r.stations)
        # Scale tolerance by the fuselage inertia magnitude (a big concept airframe).
        scale = max(abs(s.fz) for s in r.stations)
        assert math.isclose(applied, 0.0, abs_tol=1e-6 * scale + 1e-6)
        assert math.isclose(r.stations[-1].sz, 0.0, abs_tol=1e-6 * scale + 1e-6)


def test_body_nodal_cards_sum_to_zero():
    """The exported body FORCE deck parses and its Fz set closes to ~0 (ULTIMATE)."""
    results = build_body_loads(_concept_project())
    _, _, _, forces, _ = parse_cards(sb.body_force_moment_cards(results, sid_base=1))
    # One load set per case, keyed by the case's own subcase id (M4-2 decision 9).
    assert sorted(forces) == sorted(sb._sid(1, i, r) for i, r in enumerate(results))
    for idx, r in enumerate(results):
        scale = max(abs(s.fz) for s in r.stations) * _SF
        fz = sum(scale_ * v[2] for _, scale_, v in forces[sb._sid(1, idx, r)])
        assert math.isclose(fz, 0.0, abs_tol=1e-6 * scale + 1e-3)


# --------------------------------------------------------------------------- #
# Control surfaces -- the distributed-loads path matches the analysis report,
# and each exported nodal set sums to the critical surface load (ULTIMATE).
# --------------------------------------------------------------------------- #
def _report_lb_values(module, project):
    return [lv.value for cond in module.run(project).conditions
            for lv in cond.values if lv.units == "lb"]


def test_control_build_matches_report():
    """Cross-module tie: each ``build_*`` critical load appears in that module's
    ``run`` analysis report (the distributed and analysis paths agree)."""
    p = _concept_project()
    for module, build in (
        (aileron_mod, aileron_mod.build_aileron),
        (flap_mod, flap_mod.build_flap),
        (tab_mod, tab_mod.build_tabs),
    ):
        reported = _report_lb_values(module, p)
        results = build(p)
        assert results, f"{module.MODULE_NAME}: no control-surface loads on the concept airframe"
        for r in results:
            assert any(math.isclose(r.load_lb, v, rel_tol=1e-6, abs_tol=1e-6) for v in reported), \
                f"{module.MODULE_NAME} {r.surface}/{r.case} load {r.load_lb} not in report"


def test_control_nodal_loads_sum_to_critical():
    """Each control surface's exported nodal FORCE set sums to its critical load."""
    p = _concept_project()
    for build in (aileron_mod.build_aileron, flap_mod.build_flap, tab_mod.build_tabs):
        for r in build(p):
            forces = sb._control_nodal_forces(r)
            assert math.isclose(sum(forces), r.load_lb * _SF, rel_tol=1e-9, abs_tol=1e-6)


# --------------------------------------------------------------------------- #
# Whole-airframe export -- every component family emits a parseable card deck
# whose per-case FORCE set re-sums to that component's root/total at ULTIMATE.
# --------------------------------------------------------------------------- #
def test_full_airframe_exports_cleanly():
    """All four component families export FORCE cards that parse and re-sum -- the
    P1-2 acceptance: the whole concept set exports cleanly through ``sbeam_bridge``."""
    p = _concept_project()
    wing = build_net_loads(p).wing_net
    body = build_body_loads(p)
    tail = build_tail_chordwise(p)
    control = aileron_mod.build_aileron(p) + flap_mod.build_flap(p) + tab_mod.build_tabs(p)
    assert wing and body and tail and control

    # Wing: FORCE Fz re-sums to the NETLOADS root shear.
    _, _, _, wf, _ = parse_cards(sb.force_moment_cards(wing, sid_base=1))
    assert len(wf) == len(wing)
    for idx, r in enumerate(wing):
        fz = sum(sc * v[2] for _, sc, v in wf[sb._sid(1, idx, r)])
        assert math.isclose(fz, r.stations[0].sz * _SF, rel_tol=1e-4, abs_tol=1.0)

    # Tail: FORCE Fz re-sums to ULTIMATE (LT25 + LT50).
    _, _, _, tf, _ = parse_cards(sb.tail_force_moment_cards(tail, sid_base=1))
    assert len(tf) == len(tail)
    for idx, r in enumerate(tail):
        fz = sum(sc * v[2] for _, sc, v in tf[sb._sid(1, idx, r)])
        assert math.isclose(fz, (r.lt25 + r.lt50) * _SF, rel_tol=1e-4, abs_tol=1.0)

    # Control surfaces: FORCE Fz re-sums to the critical surface load.
    _, _, _, cf, _ = parse_cards(sb.control_surface_force_moment_cards(control, sid_base=1))
    assert len(cf) == len(control)
    for idx, r in enumerate(control):
        fz = sum(sc * v[2] for _, sc, v in cf[sb._sid(1, idx, r)])
        assert math.isclose(fz, r.load_lb * _SF, rel_tol=1e-4, abs_tol=1.0)

    # Body: FORCE deck parses and closes to ~0 (already asserted per case above).
    _, _, _, bf, _ = parse_cards(sb.body_force_moment_cards(body, sid_base=1))
    assert len(bf) == len(body)


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
