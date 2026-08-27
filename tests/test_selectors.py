"""Selector names and coded fields on the oracle form (#63; review 2026-08-22 PB-5 / PB-8 / PB-9).

The calc keys on names the original suite expressed by position, and two
coded inputs (the FAR 23 category, the strut type) were free text. Three
rules now hold, each with its owner: a duplicate selector is refused, never
collapsed (``sloads.selectors.keyed``; the form withholds results); a new row
is seeded with a meaningful name (``NAME_SEEDS``); a code is chosen from its
table and normalised by the consumer (``models.normalise_code``,
``field_registry.CODED_FIELDS``). The reproductions here are the review's.
"""

from __future__ import annotations

import dataclasses
import os

import pytest
from streamlit.testing.v1 import AppTest

from oracle_app.form import seeded
from sloads import field_registry as fr
from sloads import io, registry
from sloads.field_registry import CODED_FIELDS, reduce_to_oracle_inputs
from sloads.models import (
    CATEGORIES,
    STRUT_TYPES,
    TAB_SURFACES,
    TAIL_SURFACES,
    CgCase,
    GeometryInput,
    SurfaceInput,
    normalise_code,
    require_surface,
    same_name,
)
from sloads.modules.structural_speeds import maneuver_load_factors
from sloads.selectors import NAME_SEEDS, duplicate_selectors, duplicates, keyed, seed_name

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


# --- PB-8: coded fields ------------------------------------------------------- #


def test_category_is_a_code_not_free_text():
    """``"Utility"`` and ``"u"`` both gave Normal's 3.8; now one is Utility and
    the other is refused by name (4.4 is 23.337's utility minimum)."""
    assert maneuver_load_factors("u", 3400, None, None)[0] == 4.4
    assert maneuver_load_factors("U", 3400, None, None)[0] == 4.4
    with pytest.raises(ValueError, match="FAR 23 category 'Utility' is not one of N = "):
        maneuver_load_factors("Utility", 3400, None, None)


def test_normalise_code_forgives_case_and_names_the_choices():
    assert normalise_code(" s ", STRUT_TYPES, "strut") == "S"
    with pytest.raises(ValueError, match="O = Oleo"):
        normalise_code("oleo", STRUT_TYPES, "strut")


def test_every_coded_field_is_a_registered_str_field():
    for path, codes in CODED_FIELDS.items():
        assert fr.entry(path) is not None, path
        assert fr.field_type(path) is str, path
        assert codes and all(len(c) == 1 and c.isupper() for c in codes), path
    assert CODED_FIELDS["speeds.category"] is CATEGORIES


# --- #98: row selectors -- fixed-vocabulary surface names ------------------- #


def test_every_row_selector_choice_is_a_registered_str_field():
    """The `CODED_FIELDS` contract for the surface-name row selectors (#98):
    each path is a registered ``str`` field and its vocabulary is lowercase
    names, matched by the consumers and refused by name when unknown."""
    for path, choices in fr.ROW_SELECTOR_CHOICES.items():
        assert fr.entry(path) is not None, path
        assert fr.field_type(path) is str, path
        assert choices and all(n == n.strip().lower() for n in choices), path
    assert fr.ROW_SELECTOR_CHOICES["tab_loads.tabs[].surface"] is TAB_SURFACES
    assert fr.ROW_SELECTOR_CHOICES["tail_mass[].surface"] is TAIL_SURFACES


def test_require_surface_forgives_case_and_names_the_choices():
    assert require_surface(" HTAIL ", TAB_SURFACES, "tab surface") == "htail"
    with pytest.raises(ValueError, match="'rudder' is not one of wing, htail, vtail"):
        require_surface("rudder", TAB_SURFACES, "tab surface")


def test_the_tab_component_map_matches_the_vocabulary():
    """`_TAB_COMPONENT` (the case-ID/component routing) and `TAB_SURFACES` (the
    offered vocabulary) must be the same set, or the widget could offer a
    surface the router silently defaults -- the very C210-46 defect (#98)."""
    from sloads.modules.tab import _TAB_BAND, _TAB_COMPONENT
    assert tuple(_TAB_COMPONENT) == TAB_SURFACES
    assert set(_TAB_BAND) == set(_TAB_COMPONENT.values())


def test_an_unknown_tab_surface_is_refused_not_filed_under_wing():
    """Before #98 an unknown surface fell through `_TAB_COMPONENT.get(...,
    "wing")` -- the tab was silently filed as a *wing* case with a wing case-ID
    band and a wing export tag."""
    from sloads.modules.tab import build_tabs
    project = io.load_project(_GA6)
    project.tab_loads.tabs[0].surface = "rudder"
    with pytest.raises(ValueError, match="tab surface 'rudder' is not one of"):
        build_tabs(project)


def test_an_unknown_tail_mass_surface_is_refused_not_silently_inert():
    """Before #98 a `tail_mass` row whose surface matched nothing was simply
    never read: the surface kept its derived weight and nothing said the
    override had gone nowhere."""
    from sloads.mass_distribution import tail_surface_weight
    from sloads.models import TailMassInput
    project = io.load_project(_GA6)
    project.tail_mass = [TailMassInput(surface="stabilator", panel_weight_lb=50.0,
                                       weight_is_override=True)]
    with pytest.raises(ValueError, match="tail_mass surface 'stabilator' is not one of"):
        tail_surface_weight(project, "htail")


def test_row_selector_case_normalises_at_construction():
    """`TabSpec` / `TailMassInput` lowercase their surface at construction, the
    `speeds.category` pattern -- so `==` matching downstream is safe."""
    from sloads.models import TabSpec, TailMassInput
    assert TabSpec(surface=" VTAIL ").surface == "vtail"
    assert TailMassInput(surface="Htail").surface == "htail"


def test_the_owners_normalise_case_at_construction():
    project = io.load_project(_GA6)
    project.speeds.category = "n"
    project.speeds.__post_init__()
    assert project.speeds.category == "N"
    leg = project.geometry.landing_gear.main_gear
    leg.strut = "o"
    leg.__post_init__()
    assert leg.strut == "O"


# --- PB-5: selectors are unique, or the calc says so --------------------------- #


def test_keyed_refuses_a_duplicate_instead_of_collapsing_it():
    cases = [CgCase(name="CG1", weight_lb=1.0, xcg=0.0, zcg=0.0),
             CgCase(name="cg1 ", weight_lb=2.0, xcg=0.0, zcg=0.0)]
    assert duplicates([c.name for c in cases]) == ["CG1"]
    with pytest.raises(ValueError, match="CG case names must be unique: 'CG1'"):
        keyed(cases, lambda c: c.name, "CG case")
    assert list(keyed(cases[:1], lambda c: c.name, "CG case")) == ["CG1"]


def test_select_refuses_blank_cg_case_names_rather_than_moving_taildist():
    """The review's reproduction: every CG-case name blanked changed TAILDIST
    in 7 of 13 rows with nothing said. Now SELECT refuses, by name."""
    project = reduce_to_oracle_inputs(io.load_project(_GA6))
    for case in project.weight.cg_cases:
        case.name = ""
    with pytest.raises(ValueError, match="CG case names must be unique"):
        registry.get("select")(project)
    with pytest.raises(ValueError, match="CG case names must be unique"):
        registry.get("taildist")(project)


def test_two_coefficient_sets_with_one_name_are_refused():
    project = io.load_project(_GA6)
    project.aero_coeffs.flaps_down = dataclasses.replace(project.aero_coeffs.cruise, name="cruise")
    with pytest.raises(ValueError, match="Coefficient set names must be unique"):
        registry.get("select")(project)


def test_duplicate_selectors_speaks_the_forms_words():
    project = io.load_project(_GA6)
    assert duplicate_selectors(project) == []
    project.weight.cg_cases[1].name = "CG1"
    project.geometry.surfaces[1].name = " "
    out = duplicate_selectors(project)
    assert any(m.startswith("CG case names must be unique: 'CG1'") for m in out)
    assert any(m.startswith("Every geometry surface needs a name: 1 row") for m in out)


# --- PB-9 + seeds: a new row is named, the wing is found ------------------------ #


def test_by_name_matches_ignoring_case_and_edges():
    geom = GeometryInput(surfaces=[SurfaceInput(name="Wing ", leading_edge=[], trailing_edge=[])])
    assert geom.by_name("wing") is geom.surfaces[0]
    assert same_name("WING", " wing")
    assert not same_name("wing", "wing2")


def test_every_supplied_selector_name_has_a_seed():
    supplied_names = {p for p in fr.supplied_paths() if p.endswith(".name")}
    assert supplied_names == set(NAME_SEEDS), (
        f"unseeded: {supplied_names - set(NAME_SEEDS)}; stale: {set(NAME_SEEDS) - supplied_names}")
    assert seed_name("geometry.surfaces[].name", 0) == "wing"
    assert seed_name("weight.cg_cases[].name", 3) == "CG4"
    assert seed_name("no.such.name") == ""


def test_seeded_rows_skip_names_already_taken():
    row = seeded(CgCase, "weight.cg_cases[]", 1, taken=["CG1", "cg2"])
    assert row.name == "CG3"
    assert seeded(SurfaceInput, "geometry.surfaces[]", 0).name == "wing"
    assert seeded(SurfaceInput, "geometry.surfaces[]", 0, taken=["Wing"]).name == "surface2"


_PAGE = '''
import streamlit as st
from oracle_app.form import render_step
render_step(st.session_state["_key"])
'''


def _page(key, project):
    at = AppTest.from_string(_PAGE, default_timeout=60)
    at.session_state["project"] = project
    at.session_state["_key"] = key
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_a_fresh_geometry_page_seeds_the_first_surface_wing():
    from sloads import Project

    at = _page("configuration_layout", Project(name="fresh"))
    count = next(w for w in at.number_input if "geometry.surfaces[].count" in w.key)
    count.set_value(2).run()
    names = [w.value for w in at.text_input if w.key.endswith("geometry.surfaces[].0.name")
             or w.key.endswith("geometry.surfaces[].1.name")]
    assert names == ["wing", "surface2"]


def test_a_duplicate_name_withholds_the_results():
    project = reduce_to_oracle_inputs(io.load_project(_GA6))
    project.weight.cg_cases[1].name = "CG1"
    at = _page("tail_loads", project)
    assert any("CG case names must be unique" in e.value for e in at.error)
    assert not [h for h in at.header if h.value == "Results"]
    project.weight.cg_cases[1].name = "CG2"
    at = _page("tail_loads", project)
    assert not at.error and [h for h in at.header if h.value == "Results"]


def test_the_category_widget_offers_codes_and_keeps_an_unknown_one_visible():
    project = reduce_to_oracle_inputs(io.load_project(_GA6))
    at = _page("structural_speeds", project)
    box = next(w for w in at.selectbox if w.key.endswith("speeds.category"))
    assert box.value == "N"
    assert {o.split(" · ")[0] for o in box.options} >= set(CATEGORIES)
    project.speeds.category = "X"
    at = _page("structural_speeds", project)
    box = next(w for w in at.selectbox if w.key.endswith("speeds.category"))
    assert box.value == "X" and any(o.startswith("X · ") for o in box.options)


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
