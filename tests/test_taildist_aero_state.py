"""TAILDIST states the aero state of each case it distributes (#100, note 35).

The closure gates G-AS-1 .. G-AS-5 of ``docs/40_history/38_taildist_aero_state_note.md``:

* **G-AS-1 (oracle)** -- on the Appendix A GA6, ``BAL UP RETRACTED``'s structured
  ``alpha_tail_deg``/``delta_deg`` equal the loose ``LoadValue``s already
  oracle-checked (same locals, bit-for-bit) and the delta matches Appendix A's
  "Critical Horiz Tail Loads" **-5.39 deg** (Ch 9 case 202).
* **G-AS-2 (closure identity)** -- on every shipped fixture, the published state
  reconstructs the stamped LT25/LT50 split through the method's own equations
  (rel 1e-9): the state printed beside a load is arithmetically inside it.
* **G-AS-3 (statement guard)** -- every TAILDIST condition states each of
  AoA / beta / delta / q or its AS-4 reason string; no silent blank.
* **G-AS-4 (stale set)** -- a persisted critical set that predates the fields
  says so ("re-run SELECT"), never a guess.
* **G-AS-5 (drift guard)** -- the per-label literals of section 1's inventory
  (vtail fin AoA 0 / -19.5 / -15 / -gust beta; rudder throw / throw / 0 / 0;
  the checked-maneuver delta reason), plus AS-5's one-spelling rule for the
  finite-surface lift slope.

No load number moves anywhere (AS-8): the whole oracle suite is this file's
other half.
"""

import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import replace

from sloads import io
from sloads.constants import DEG_PER_RAD
from sloads.models import SelectInput
from sloads.modules import taildist
from sloads.modules._vtail import (
    large_deflection_factor,
    lift_curve_slope,
    rudder_effectiveness,
)
from sloads.modules.select import (
    default_critical,
    default_envelope,
    effective_tail_inputs,
    effective_vtail_inputs,
)

REL = 1e-9   # pass-through identities: the method's own equations, exact
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _ga6_appendix_a():
    """The 6-place GA at the Appendix A altitude set (the case-202 setup of
    ``test_select.test_rational_balancing_tail_load_hand_calc``)."""
    p = io.load_project(_GA)
    p.flight_loads.altitudes_ft = [0.0, 12000.0, 18000.0]
    p.select_input = SelectInput(full_down_aileron_deg=15.0, basic_airfoil_cm=-0.03)
    return p


def _tail_conditions(p):
    return [c for c in default_critical(p).conditions
            if c.component in ("htail", "vtail")]


def _loads(cond):
    return {v.key: v.value for v in cond.loads}


# --------------------------------------------------------------------------- #
# G-AS-1: the oracle
# --------------------------------------------------------------------------- #
def test_up_balancing_publishes_the_oracle_checked_state():
    """The structured fields are the loose ``LoadValue``s' own locals (AS-6),
    and the balancing delta is Appendix A's -5.39 deg (Ch 9 case 202; the same
    FLTLOADS +-0.005-NZ noise tolerance as the standing case-202 oracle)."""
    p = _ga6_appendix_a()
    up = next(c for c in _tail_conditions(p) if c.label == "BAL UP RETRACTED")
    loads = _loads(up)
    assert up.alpha_tail_deg == loads["tail_angle_of_attack_at"]     # bit-for-bit
    assert up.delta_deg == loads["elevator_deflection_te_dn"]        # bit-for-bit
    assert math.isclose(up.delta_deg, -5.39, abs_tol=0.03), up.delta_deg
    assert math.isclose(up.alpha_tail_deg, 7.747, abs_tol=0.05), up.alpha_tail_deg
    assert up.q_psf is not None and up.q_psf > 0.0


# --------------------------------------------------------------------------- #
# G-AS-2: the published state reconstructs the stamped split, per family
# --------------------------------------------------------------------------- #
def _fixtures():
    return sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json")))


def test_the_published_state_reconstructs_the_split_on_every_fixture():
    for path in _fixtures():
        p = io.load_project(path)
        if p.flight_loads is None or (p.tail_loads is None and p.vtail_loads is None):
            continue
        name = os.path.basename(path)
        ti = effective_tail_inputs(p) if p.tail_loads is not None else None
        vt = effective_vtail_inputs(p)
        conds = _tail_conditions(p)
        assert conds, name
        by_case_htail = {}
        for c in conds:
            if c.component == "htail" and c.label != "UNSYMMETRICAL":
                by_case_htail.setdefault(c.case, []).append(c)
        for c in conds:
            ident = f"{name}:{c.label}"
            if c.component == "htail":
                aht = lift_curve_slope(ti.aspect_ratio_htail)
                st = ti.htail_area_sqft
                lt25_trim = (c.alpha_tail_deg * aht / DEG_PER_RAD) * c.q_psf * st
                loads = _loads(c)
                if c.label.startswith("BAL "):
                    assert math.isclose(c.lt25, lt25_trim, rel_tol=REL), ident
                elif c.label.startswith("UNCHECKED"):
                    assert math.isclose(c.lt25, lt25_trim, rel_tol=REL), ident
                    se2st = ti.elevator_area_sqft / ti.htail_area_sqft
                    lt50 = (c.delta_deg * ti.elevator_effectiveness
                            * large_deflection_factor(abs(c.delta_deg), se2st)
                            * aht / DEG_PER_RAD * c.q_psf * st)
                    assert math.isclose(c.lt50, lt50, rel_tol=REL), ident
                elif c.label.startswith("CHECKED"):
                    inc = loads["maneuver_load_increment"]
                    assert math.isclose(c.lt25 - inc, lt25_trim, rel_tol=REL), ident
                elif c.label.startswith("GUST"):
                    inc = loads["gust_increment_cp_25_pct"]
                    assert math.isclose(c.lt25 - inc, lt25_trim, rel_tol=REL), ident
                    lt50 = (c.delta_deg * ti.elevator_effectiveness
                            * aht / DEG_PER_RAD * c.q_psf * st)
                    assert math.isclose(c.lt50, lt50, rel_tol=REL), ident
                elif c.label == "UNSYMMETRICAL":
                    # Copied from the governing source condition, unchanged.
                    assert any(
                        (c.alpha_tail_deg, c.delta_deg, c.q_psf)
                        == (s.alpha_tail_deg, s.delta_deg, s.q_psf)
                        for s in by_case_htail.get(c.case, [])), ident
            else:
                avt = lift_curve_slope(vt.aspect_ratio_vtail)
                sv = vt.vtail_area_sqft
                if c.label == "SIDE GUST":
                    assert c.q_psf is None, ident        # AS-4: linear in V
                    assert c.alpha_tail_deg == -c.beta_deg, ident
                    continue
                lyaw = c.alpha_tail_deg * avt / DEG_PER_RAD * c.q_psf * sv
                assert math.isclose(c.lt25, lyaw, rel_tol=REL, abs_tol=1e-12), ident
                lrud = (c.delta_deg * vt.rudder_large_deflection_factor
                        * rudder_effectiveness(vt.rudder_area_sqft / sv)
                        * avt / DEG_PER_RAD * c.q_psf * sv)
                assert math.isclose(c.lt50, lrud, rel_tol=REL, abs_tol=1e-12), ident


# --------------------------------------------------------------------------- #
# G-AS-3: no silent blank on the TAILDIST page
# --------------------------------------------------------------------------- #
def _distributed(p):
    mr = taildist.run(p)
    return [c for c in mr.conditions if ": " in c.title]


def test_every_taildist_condition_states_its_state_or_the_reason():
    for name in ("ga6_normal", "atr42_100"):
        p = io.load_project(os.path.join(_EXAMPLES, f"{name}.project.json"))
        conds = _distributed(p)
        assert conds, name
        for c in conds:
            keys = {v.key for v in c.values}
            ident = f"{name}:{c.title}"
            if "htail" in c.title:
                assert "tail_angle_of_attack_at" in keys, ident
                assert ("elevator_deflection_te_dn" in keys
                        or taildist.CHECKED_DELTA_NOTE in c.note), ident
                assert taildist.HTAIL_BETA_NOTE in c.note, ident
                assert "dynamic_pressure_q" in keys, ident
            else:
                assert "fin_angle_of_attack" in keys, ident
                assert "sideslip_beta" in keys, ident
                assert "rudder_deflection_te_port" in keys, ident
                assert ("dynamic_pressure_q" in keys
                        or taildist.SIDE_GUST_Q_NOTE in c.note), ident


# --------------------------------------------------------------------------- #
# G-AS-4: a stale persisted set says so
# --------------------------------------------------------------------------- #
def test_a_persisted_set_without_the_fields_says_rerun_select():
    p = io.load_project(_GA)
    env = default_envelope(p)
    crit = default_critical(p, env)
    stale = replace(crit, conditions=[
        replace(c, alpha_tail_deg=None, delta_deg=None, q_psf=None)
        if c.component in ("htail", "vtail") else c for c in crit.conditions])
    p.envelope = replace(env, critical=stale)
    conds = _distributed(p)
    assert conds
    for c in conds:
        keys = {v.key for v in c.values}
        assert taildist.STALE_STATE_NOTE in c.note, c.title
        for k in ("tail_angle_of_attack_at", "fin_angle_of_attack",
                  "elevator_deflection_te_dn", "rudder_deflection_te_port",
                  "dynamic_pressure_q"):
            assert k not in keys, (c.title, k)


# --------------------------------------------------------------------------- #
# G-AS-5: per-label literals + the one-spelling slope
# --------------------------------------------------------------------------- #
def test_the_vtail_states_are_the_section_1_literals():
    p = io.load_project(_GA)
    vt = effective_vtail_inputs(p)
    conds = {c.label: c for c in _tail_conditions(p) if c.component == "vtail"}
    assert conds["SUDDEN RUDDER"].alpha_tail_deg == 0.0
    assert conds["YAW TO SIDESLIP"].alpha_tail_deg == -19.5
    assert conds["YAW 15 NEUTRAL"].alpha_tail_deg == -15.0
    gust = conds["SIDE GUST"]
    assert gust.alpha_tail_deg == -gust.beta_deg and gust.alpha_tail_deg > 0.0
    assert conds["SUDDEN RUDDER"].delta_deg == vt.rudder_deflection_deg
    assert conds["YAW TO SIDESLIP"].delta_deg == vt.rudder_deflection_deg
    assert conds["YAW 15 NEUTRAL"].delta_deg == 0.0
    assert gust.delta_deg == 0.0


def test_the_checked_maneuver_delta_is_the_stated_reason():
    p = io.load_project(_GA)
    checked = [c for c in _tail_conditions(p) if c.label.startswith("CHECKED")]
    assert checked
    for c in checked:
        assert c.delta_deg is None and c.alpha_tail_deg is not None, c.label
    rows = [c for c in _distributed(p) if ": CHECKED" in c.title]
    assert rows
    for c in rows:
        assert taildist.CHECKED_DELTA_NOTE in c.note, c.title


def test_the_finite_surface_slope_has_one_spelling():
    """AS-5 / rule 3: ``2*pi/(1 + 2/AR)`` lives in ``_vtail.lift_curve_slope``
    and nowhere else -- an inline respelling is the drift this guard exists
    to refuse (the pre-note state: three copies in ``select.py``)."""
    owner = os.path.join("sloads", "modules", "_vtail.py")
    offenders = []
    for path in glob.glob(os.path.join(_ROOT, "sloads", "**", "*.py"), recursive=True):
        rel = os.path.relpath(path, _ROOT)
        if rel == owner:
            continue
        with open(path, encoding="utf-8") as fh:
            if "math.pi / (1.0 + 2.0" in fh.read():
                offenders.append(rel)
    assert not offenders, offenders


# --------------------------------------------------------------------------- #
# AS-5/AS-6: the intermediates, once per component, from their owners
# --------------------------------------------------------------------------- #
def test_the_constants_print_once_per_component_from_their_owners():
    p = io.load_project(_GA)
    mr = taildist.run(p)
    titles = [c.title for c in mr.conditions]
    assert titles.count("Chordwise htail constants") == 1
    assert titles.count("Chordwise vtail constants") == 1
    ti, vt = effective_tail_inputs(p), effective_vtail_inputs(p)
    ht = next(c for c in mr.conditions if c.title == "Chordwise htail constants")
    assert _values(ht)["tail_lift_curve_slope_aht"] == lift_curve_slope(ti.aspect_ratio_htail)
    vtc = next(c for c in mr.conditions if c.title == "Chordwise vtail constants")
    assert _values(vtc)["vtail_lift_curve_slope_avt"] == lift_curve_slope(vt.aspect_ratio_vtail)
    assert _values(vtc)["rudder_effectiveness_effectv"] == rudder_effectiveness(
        vt.rudder_area_sqft / vt.vtail_area_sqft)
    # The constants precede their component's conditions (AS-6's header shape).
    assert titles.index("Chordwise htail constants") < titles.index(
        next(t for t in titles if t.startswith("Chordwise htail load")))


def _values(cond):
    return {v.key: v.value for v in cond.values}


# --------------------------------------------------------------------------- #
# AS-7: additive result fields round-trip (and load as None from older files)
# --------------------------------------------------------------------------- #
def test_the_new_fields_round_trip_and_default_to_none():
    p = io.load_project(_GA)
    env = default_envelope(p)
    crit = default_critical(p, env)
    p.envelope = replace(env, critical=crit)
    doc = io.project_to_dict(p)
    back = io.project_from_dict(doc)
    orig = {c.label: c for c in crit.conditions if c.component in ("htail", "vtail")}
    got = {c.label: c for c in back.envelope.critical.conditions
           if c.component in ("htail", "vtail")}
    assert orig.keys() == got.keys()
    for label, c in orig.items():
        b = got[label]
        assert (b.alpha_tail_deg, b.delta_deg, b.q_psf) == \
            (c.alpha_tail_deg, c.delta_deg, c.q_psf), label
    # An older file simply lacks the keys: the reader answers None.
    d = {"component": "htail", "label": "BAL UP RETRACTED"}
    old = io._critical_condition_from_dict(d)
    assert old.alpha_tail_deg is None and old.delta_deg is None and old.q_psf is None


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
    raise SystemExit(1 if failed else 0)
