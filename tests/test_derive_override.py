"""The derive-by-default override mechanism (design note 36, #97).

One mechanism for the eight C210 duplicated-input findings (OV-1): a blank
collapsed field falsy-derives through one named resolver per quantity, a typed
value overrides, and the registry links each collapsed path to its owner. The
gates here are the note's own G-OV-2 (derive-equals-owner, rel 1e-9), G-OV-3
(the silent-default defect dies, each test stating the pre-fix failure),
G-OV-4's registry half (OV-11: the drift guard that makes the mechanism the
single-source owner), G-OV-5's v56 round-trip half (the 55->56 hop itself is
pinned in ``test_migrations.py``) and G-OV-6 (typed disagreements warn, a
selector naming no row is refused by name). G-OV-1 is the standing oracle
suite, which this change must leave untouched.
"""

import copy
import math
import os
import sys
from dataclasses import replace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import field_registry as fr
from sloads import io
from sloads.derived_geometry import (
    taper_ratio_from_planform,
    tip_ratio_from_planform,
    wing_aspect_ratio,
)
from sloads.models import AeroCoeffSet
from sloads.modules.airloads import _tau, resolve_aero_surfaces, resolved_tau, schrenk_distribution
from sloads.modules.engine import effective_engine, run as engine_run, selected_mass_row
from sloads.modules.flap import resolved_ng
from sloads.modules.flight_envelope import (
    _gust_load_factor,
    balance_configs,
    design_inputs,
    gust_at_vf,
)
from sloads.modules.select import (
    effective_tail_inputs,
    resolved_full_down_aileron_deg,
    wing_lift_slope_per_rad,
)
from sloads.modules.structural_speeds import design_speed_values
from sloads.modules.weight_envelope import run as wtenv_run
from sloads.validation import consistency_warnings

_GA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "examples", "ga6_normal.project.json")

#: The pointed-wing knot of the TAU fit -- what a blank taper ratio used to
#: land on silently (note 36 §1, C210-31).
_POINTED_WING_TAU = 0.206209

REL = 1e-9


def _ga6():
    return io.load_project(_GA)


def _wing_chords(surf):
    """Tip and centreline chord straight off the edge polylines."""
    from sloads.modules.wing_geometry import interp_x

    y_root = max(surf.leading_edge[0][1], surf.trailing_edge[0][1])
    y_tip = min(surf.leading_edge[-1][1], surf.trailing_edge[-1][1])
    c = lambda y: interp_x(surf.trailing_edge, y) - interp_x(surf.leading_edge, y)  # noqa: E731
    return c(y_tip), c(y_root)


def _with_flaps_down(project):
    """ga6 with a synthetic flaps-down set (none is bundled -- Appendix B's
    landing polynomials are not shipped), so the GUST VF chain has a corner."""
    aero = project.aero_coeffs
    flaps = copy.deepcopy(aero.cruise)
    flaps.name = "landing"
    flaps.flaps_down = True
    flaps.stall_cl = aero.clmax_flap or 1.8
    aero.flaps_down = flaps
    project.flight_loads.xtf = project.flight_loads.xtc
    return project


# --------------------------------------------------------------------------- #
# G-OV-2: derive equals owner, each collapsed field blanked in turn (rel 1e-9)
# --------------------------------------------------------------------------- #
def test_blank_taper_derives_the_polyline_chord_ratio():
    p = _ga6()
    surf = p.geometry.by_name("wing")
    c_tip, c_root = _wing_chords(surf)
    derived = taper_ratio_from_planform(surf)
    assert math.isclose(derived, c_tip / c_root, rel_tol=REL)
    aero = replace(p.aero.by_name("wing"), taper_ratio=0.0, tau=None)
    assert math.isclose(resolved_tau(surf, aero), _tau(derived, 0.0), rel_tol=REL)


def test_blank_tip_ratio_derives_from_the_tip_cap_width():
    p = _ga6()
    surf = p.geometry.by_name("wing")
    assert tip_ratio_from_planform(surf) == 0.0        # square tip, today's blank
    surf.tip_cap_width_in = 10.0
    semi_span = surf.leading_edge[-1][1]
    assert math.isclose(tip_ratio_from_planform(surf), 10.0 / semi_span, rel_tol=REL)


def test_blank_arw_derives_the_consolidated_planform_ar():
    p = _ga6()
    p.geometry.empennage.htail.aspect_ratio_wing = 0.0
    ti = effective_tail_inputs(p)
    from sloads.modules.wing_geometry import surface_properties

    owner = next(v.value for v in surface_properties(p.geometry.by_name("wing")).values
                 if v.key == "aspect_ratio")
    assert math.isclose(ti.aspect_ratio_wing, owner, rel_tol=REL)
    assert math.isclose(ti.aspect_ratio_wing, wing_aspect_ratio(p), rel_tol=REL)


def test_blank_aw_derives_c1_times_57_3():
    p = _ga6()
    p.geometry.empennage.htail.wing_lift_slope_per_rad = 0.0
    ti = effective_tail_inputs(p)
    from sloads.constants import DEG_PER_RAD

    assert math.isclose(ti.wing_lift_slope_per_rad,
                        p.aero_coeffs.cruise.lift[1] * DEG_PER_RAD, rel_tol=REL)
    assert math.isclose(ti.wing_lift_slope_per_rad, wing_lift_slope_per_rad(p),
                        rel_tol=REL)


def test_blank_select_aileron_derives_the_aileron_deflection():
    p = _ga6()
    p.select_input.full_down_aileron_deg = 0.0
    assert resolved_full_down_aileron_deg(p) == p.aileron_loads.down_deflection_deg


def test_blank_ng_is_the_envelopes_own_gust_vf_factor_bit_for_bit():
    p = _with_flaps_down(_ga6())
    p.flap_loads.gust_load_factor = 0.0
    ng, derived = resolved_ng(p)
    assert derived
    di = design_inputs(p)
    from sloads.cg_cases import flight_cases
    from sloads.derived_geometry import wing_reference

    wr = wing_reference(p)
    config = next(c for c in balance_configs(p.aero_coeffs) if c.flaps_down)
    expected = max(
        _gust_load_factor(1, di.vf, di.mc, "F", config, cg, p.flight_loads, wr, 0.0)
        for cg in flight_cases(p))
    assert ng == expected                              # same call, exact
    assert gust_at_vf(p) == expected


def test_typed_ng_overrides_the_envelope():
    p = _with_flaps_down(_ga6())
    assert p.flap_loads.gust_load_factor == 1.9
    ng, derived = resolved_ng(p)
    assert (ng, derived) == (1.9, False)


def test_blank_limnz_derives_the_23_337_limit_exactly():
    p = _ga6()
    eng = replace(p.engines[0], limit_load_factor=0.0)
    resolved = effective_engine(p, eng)
    assert resolved.limit_load_factor == design_speed_values(p, p.speeds).n


def test_blank_gross_weight_derives_mtow_in_wtenv():
    p = _ga6()
    p.weight.envelope.gross_weight = 0.0
    result = wtenv_run(p)
    values = {v.key: v.value for c in result.conditions for v in c.values}
    assert values["aft_gross_point_weight"] == p.weight.max_takeoff_weight_lb
    assert values["forward_gross_point_weight"] == p.weight.max_takeoff_weight_lb


def test_engine_weight_and_cg_derive_from_the_selected_row():
    p = _ga6()
    row = p.weight.items[0]
    eng = replace(p.engines[0], engine_mass_item=row.name,
                  engine_weight_lb=0.0, engine_cg=(0.0, 0.0, 0.0),
                  prop_mass_item=row.name, prop_weight_lb=0.0,
                  prop_cg=(0.0, 0.0, 0.0))
    resolved = effective_engine(p, eng)
    assert resolved.engine_weight_lb == row.weight_lb
    assert resolved.engine_cg == (row.x, row.y, row.z)
    assert resolved.prop_weight_lb == row.weight_lb
    assert resolved.prop_cg == (row.x, row.y, row.z)


def test_typed_engine_values_override_the_row():
    p = _ga6()
    row = p.weight.items[0]
    eng = replace(p.engines[0], engine_mass_item=row.name)
    resolved = effective_engine(p, eng)
    assert resolved.engine_weight_lb == eng.engine_weight_lb    # typed wins
    assert resolved.engine_cg == eng.engine_cg


# --------------------------------------------------------------------------- #
# G-OV-3: the silent-default defect dies (each test states the pre-fix failure)
# --------------------------------------------------------------------------- #
def test_a_blank_taper_no_longer_yields_the_pointed_wing_tau():
    """Pre-fix: a blank ``taper_ratio`` hit the TAU fit at taper 0 -- the
    pointed-wing knot, tau = 0.206209, the *maximum* correction -- on any
    tapered planform, silently. Now the polyline chord ratio derives first."""
    p = _ga6()
    surf = p.geometry.by_name("wing")
    aero = replace(p.aero.by_name("wing"), taper_ratio=0.0, tau=None)
    tau = resolved_tau(surf, aero)
    assert not math.isclose(tau, _POINTED_WING_TAU, rel_tol=1e-3)
    assert math.isclose(tau, _tau(taper_ratio_from_planform(surf), 0.0), rel_tol=REL)
    # ...and the distribution consumes the same resolution (one spelling).
    table = schrenk_distribution(surf, aero)
    assert math.isclose(table.tau, tau, rel_tol=REL)


def test_a_blank_arw_no_longer_divides_by_zero():
    """Pre-fix: ``select.py``'s downwash ``E = 114.6*CL/(pi*ARW)`` divided by
    the field's 0.0 default unguarded (C210-36) -- a bare ZeroDivisionError.
    Now it derives; and with no planform to derive from it is refused by name."""
    p = _ga6()
    p.geometry.empennage.htail.aspect_ratio_wing = 0.0
    assert effective_tail_inputs(p).aspect_ratio_wing > 0.0
    p.geometry.surfaces = [s for s in p.geometry.surfaces if s.name != "wing"]
    with pytest.raises(ValueError, match="aspect_ratio_wing"):
        effective_tail_inputs(p)


def test_a_blank_limnz_no_longer_zeroes_the_mount_loads():
    """Pre-fix: a 0 LIMNZ multiplied straight into every vertical mount case
    (C210-41) -- plausible output, silently zero. Now it derives from 23.337."""
    p = _ga6()
    p.engines[0].limit_load_factor = 0.0
    result = engine_run(p)
    values = [v.value for c in result.conditions for v in c.values]
    assert any(abs(v) > 100.0 for v in values), "the mount loads are still zeroed"


def test_an_empty_aero_slice_no_longer_skips_the_wing():
    """Pre-fix (C210-29 seed half): an absent aero row meant the surface was
    never analysed at all. Now every symmetric planform without a same-name row
    gets the schema-default row, per name; single-sided placement planforms
    (ga6's aileron) do not."""
    p = _ga6()
    p.aero.surfaces = []
    resolved = resolve_aero_surfaces(p)
    assert [a.name for a in resolved] == ["wing"]
    # per-name: a typed wing row never suppresses a derivable second surface
    p2 = _ga6()
    assert [a.name for a in resolve_aero_surfaces(p2)] == ["wing"]


# --------------------------------------------------------------------------- #
# G-OV-4 (registry half) -- OV-11's drift guard
# --------------------------------------------------------------------------- #
def test_every_collapsed_path_is_linked_and_resolvable():
    """OV-11: the collapsed set is enumerated once
    (``field_registry.COLLAPSED_OVERRIDES``) and every member carries a
    non-empty ``derived_from``, ``governs=True`` (the calc honours the typed
    value) and a resolver in ``EXTERNAL_VALUES`` -- which is what makes the
    mechanism the single-source owner rather than a convention."""
    assert fr.COLLAPSED_OVERRIDES, "the collapsed set is empty"
    for path in fr.COLLAPSED_OVERRIDES:
        entry = fr.BY_PATH.get(path)
        assert entry is not None, f"{path} has no registry row"
        assert entry.derived_from.strip(), f"{path} lacks derived_from"
        assert entry.governs, f"{path} must govern (typed-means-override)"
        assert path in fr.EXTERNAL_VALUES, f"{path} lacks a resolver"


def test_no_owned_quantity_copy_lacks_its_link():
    """OV-11's inverse: a registry row holding a quantity another row owns must
    name that owner -- a future duplicated input without its link fails CI."""
    for quantity, rows in fr.quantities().items():
        owners = [e for e in rows if e.is_owner]
        if not owners:
            continue
        unlinked = [e.path for e in rows if not e.is_owner and not e.derived_from]
        assert not unlinked, f"{quantity!r}: copies without derived_from: {unlinked}"


def test_collapsed_resolvers_answer_on_the_shipped_fixture():
    """The resolver is the same function the calc calls, so on ga6 (which types
    every collapsed field) each scalar resolver must produce a value close to
    the typed one -- the fixture's own agreement, which is what the caption
    will show beside the field."""
    p = _ga6()
    checks = {
        "weight.envelope.gross_weight": p.weight.envelope.gross_weight,
        "geometry.empennage.htail.aspect_ratio_wing":
            p.geometry.empennage.htail.aspect_ratio_wing,
        "geometry.empennage.htail.wing_lift_slope_per_rad":
            p.geometry.empennage.htail.wing_lift_slope_per_rad,
        "select_input.full_down_aileron_deg": p.select_input.full_down_aileron_deg,
        "engines[].limit_load_factor": p.engines[0].limit_load_factor,
    }
    for path, typed in checks.items():
        governing = fr.external_value(path, p, p.engines[0])
        assert governing is not None, path
        assert math.isclose(governing, typed, rel_tol=1e-2), (path, governing, typed)


def test_row_resolvers_read_the_record():
    p = _ga6()
    row = p.weight.items[0]
    eng = replace(p.engines[0], engine_mass_item=row.name)
    assert fr.external_value("engines[].engine_weight_lb", p, eng) == row.weight_lb
    assert fr.external_value("engines[].engine_cg", p, eng) == (row.x, row.y, row.z)
    assert fr.external_value("engines[].engine_weight_lb", p, p.engines[0]) is None
    aero_wing = p.aero.by_name("wing")
    assert math.isclose(
        fr.external_value("aero.surfaces[].taper_ratio", p, aero_wing),
        taper_ratio_from_planform(p.geometry.by_name("wing")), rel_tol=REL)


# --------------------------------------------------------------------------- #
# G-OV-5 (v56 half): the three new fields round-trip
# --------------------------------------------------------------------------- #
def test_the_v56_fields_round_trip():
    p = _ga6()
    p.geometry.by_name("wing").tip_cap_width_in = 7.5
    p.engines[0].engine_mass_item = "Engine"
    p.engines[0].prop_mass_item = "Prop"
    again = io.project_from_dict(io.project_to_dict(p))
    assert again.geometry.by_name("wing").tip_cap_width_in == 7.5
    assert again.engines[0].engine_mass_item == "Engine"
    assert again.engines[0].prop_mass_item == "Prop"


# --------------------------------------------------------------------------- #
# G-OV-6: disagreement surfaced, bad selector refused by name
# --------------------------------------------------------------------------- #
def test_aileron_deflection_mismatch_warns():
    p = _ga6()
    p.select_input.full_down_aileron_deg = 20.0        # aileron says 15.0
    codes = {w.code for w in consistency_warnings(p)}
    assert "aileron_deflection_mismatch" in codes
    p.select_input.full_down_aileron_deg = 0.0         # blank derives: no warning
    codes = {w.code for w in consistency_warnings(p)}
    assert "aileron_deflection_mismatch" not in codes


def test_engine_mass_row_mismatch_warns():
    p = _ga6()
    row = p.weight.items[0]
    p.engines[0].engine_mass_item = row.name           # typed 505 lb vs the row's
    assert p.engines[0].engine_weight_lb != row.weight_lb
    warnings = [w for w in consistency_warnings(p)
                if w.code == "engine_mass_row_mismatch"]
    assert warnings and row.name in warnings[0].message


def test_a_selector_naming_no_row_is_refused_by_name():
    p = _ga6()
    p.engines[0].engine_mass_item = "no such row"
    with pytest.raises(ValueError, match="no such row"):
        engine_run(p)
    with pytest.raises(ValueError, match="engine_mass_item"):
        selected_mass_row(p, "no such row", "engine 1", "engine_mass_item")


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
