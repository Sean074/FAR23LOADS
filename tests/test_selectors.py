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
    CgCase,
    GeometryInput,
    SurfaceInput,
    normalise_code,
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
