"""The schema migration chain (M4-10).

`io.project_from_dict` used to decide what it was reading by sniffing keys — a
19-clause ``or`` gate — and handled each legacy file shape with an inline shim
threaded through the readers. This file pins the replacement: a chain of pure
``dict -> dict`` hops that normalises any historical file to the current shape
before a single tolerant reader sees it.

The failure mode that matters is **silent data loss on a user's saved project**,
so the tests are built around frozen fixtures (`tests/fixtures_schema/`), one per
historical shape actually reachable, rather than around dicts mutated in-test.
"""

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.migrations import (  # noqa: E402
    MIGRATIONS,
    SUPPORTED_FLOOR,
    applied_hops,
    is_project_dict,
    migrate,
)
from sloads.models import SCHEMA_VERSION  # noqa: E402
from sloads.modules import select  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_FIXTURES = os.path.join(_HERE, "fixtures_schema")
_EXAMPLES = os.path.join(os.path.dirname(_HERE), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

_FROZEN = sorted(f for f in os.listdir(_FIXTURES) if f.endswith(".json"))


def _load(name):
    with open(os.path.join(_FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Every frozen historical shape still loads
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", _FROZEN)
def test_every_frozen_fixture_loads(name):
    project = io.load_project(os.path.join(_FIXTURES, name))
    assert project is not None
    assert project.schema_version == SCHEMA_VERSION, "a loaded project is at the current schema"


def test_the_frozen_set_covers_every_shape_changing_hop():
    """A hop with no fixture is an untested migration path."""
    covered = {int(n.split("_")[0].lstrip("v")) for n in _FROZEN}
    for hop in MIGRATIONS:
        assert any(v <= hop for v in covered), f"no fixture old enough to exercise the v{hop} hop"


@pytest.mark.parametrize("name", [n for n in _FROZEN if n != "v0_bare_engine.json"])
def test_a_migrated_legacy_file_carries_its_geometry_across(name):
    """The hops move data, they do not merely tolerate its absence."""
    project = io.load_project(os.path.join(_FIXTURES, name))
    assert project.geometry is not None, f"{name} lost its geometry slice"
    assert project.geometry.parametric is not None, f"{name} lost geometry.parametric"


def test_pre_g6_file_lands_its_tail_slices_on_the_empennage():
    project = io.load_project(os.path.join(_FIXTURES, "v26_top_level_tail_loads.json"))
    assert project.geometry.empennage is not None
    assert project.geometry.empennage.htail is not None
    assert project.tail_loads is not None, "the Step-G6 proxy must see the migrated slice"


def test_pre_g6b_file_lands_its_gear_on_the_geometry():
    project = io.load_project(os.path.join(_FIXTURES, "v28_gear_on_landing.json"))
    assert project.geometry.landing_gear is not None
    assert project.geometry.landing_gear.main_gear is not None


def test_pre_m4_9_file_gets_its_load_value_keys_backfilled():
    """A v36 file's persisted SELECT loads carry labels and no keys. Every consumer
    now matches on the key, so without the backfill the reloaded governing-loads
    table would silently lose its columns -- the exact M4-9 failure mode, re-entering
    through the file path."""
    project = io.load_project(os.path.join(_FIXTURES, "v36_select_loads_without_keys.json"))
    by_label = {
        lv.label: lv
        for c in project.envelope.critical.conditions
        for lv in c.loads
    }
    assert by_label["Balancing tail load"].key == "balancing_tail_load"
    assert by_label["Tail angle of attack AT"].key == "tail_angle_of_attack_at"
    assert by_label["Load factor NZ"].key == "load_factor_nz"
    assert by_label["V (EAS)"].key == "v_eas"
    # A label this build has never emitted keeps an empty key rather than an
    # invented one -- the row still renders, it just cannot be matched by key.
    assert by_label["A label no build ever emitted"].key == ""


def test_the_backfill_table_is_frozen_against_todays_producer():
    """Every label the table claims maps to a key SELECT still emits under that key.

    The table describes what *old files say*, so it is never regenerated -- but a key
    renamed in ``select.py`` without a new hop would leave migrated files pointing at
    a key nothing produces, which this catches.
    """
    from sloads.migrations import _V36_LOAD_VALUE_KEYS

    project = io.load_project(_GA)
    emitted = {
        lv.label: lv.key
        for c in select.build_critical(project).conditions
        for lv in c.loads
    }
    drifted = {
        label: (key, emitted[label])
        for label, key in _V36_LOAD_VALUE_KEYS.items()
        if label in emitted and emitted[label] != key
    }
    assert not drifted, f"backfill table maps labels to keys select.py no longer emits: {drifted}"


def test_pre_d5_file_recovers_its_cg_cases():
    project = io.load_project(os.path.join(_FIXTURES, "v18_cg_cases_on_flight_loads.json"))
    assert project.weight is not None
    assert [c.name for c in project.weight.cg_cases] == ["CG1", "CG2", "CG3", "CG4"]


def test_bare_engine_file_is_still_accepted():
    """The Phase-0 ``engloads`` era file: the whole document is one EngineInput."""
    project = io.load_project(os.path.join(_FIXTURES, "v0_bare_engine.json"))
    assert len(project.engines) == 1
    assert project.engine.engine_designation


# --------------------------------------------------------------------------- #
# The discriminator that replaced the 19-clause or-gate
# --------------------------------------------------------------------------- #
def test_project_and_engine_dicts_are_told_apart():
    assert is_project_dict(_load("v38_current.json"))
    assert not is_project_dict(_load("v0_bare_engine.json"))


def test_discriminator_tracks_project_fields_automatically():
    """The old gate enumerated slice names by hand, so a new slice had to be added
    to it or a real project would be misread as a bare engine file. The
    replacement derives its key set from ``Project``'s own fields."""
    from dataclasses import fields as dc_fields

    from sloads import Project

    for f in dc_fields(Project):
        if f.name == "schema_version":
            continue
        assert is_project_dict({f.name: None}), f"{f.name} not recognised as a project key"


# --------------------------------------------------------------------------- #
# Chain mechanics
# --------------------------------------------------------------------------- #
def test_migrate_does_not_mutate_the_callers_dict():
    """The GUI hands the same dict to the JSON editor after loading it."""
    original = _load("v24_top_level_configuration.json")
    snapshot = copy.deepcopy(original)
    migrate(original)
    assert original == snapshot


def test_migrate_is_idempotent():
    once = migrate(_load("v24_top_level_configuration.json"))
    assert migrate(once) == once


def test_current_file_is_untouched_by_the_chain():
    """No hop may fire for a current-schema file — that is what version-gating buys."""
    current = _load("v38_current.json")
    assert migrate(current) == {**current, "schema_version": SCHEMA_VERSION}


def test_a_newer_file_is_not_mangled_by_hops_that_do_not_apply():
    """Forward compatibility degrades to 'read what you understand'."""
    future = _load("v38_current.json")
    future["schema_version"] = SCHEMA_VERSION + 5
    out = migrate(future)
    assert out["schema_version"] == SCHEMA_VERSION + 5
    assert "geometry" in out


def test_applied_hops_reports_the_chain_for_a_version():
    assert applied_hops(SCHEMA_VERSION) == []
    assert applied_hops(SUPPORTED_FLOOR) == sorted(MIGRATIONS)
    assert 27 in applied_hops(26) and 18 not in applied_hops(26)


def test_unversioned_dict_runs_the_whole_chain():
    d = _load("v24_top_level_configuration.json")
    del d["schema_version"]
    out = migrate(d)
    assert "configuration" not in out, "the v25 hop should have folded it into geometry"


# --------------------------------------------------------------------------- #
# The acceptance criterion: no example changes on the way through
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name", sorted(f for f in os.listdir(_EXAMPLES) if f.endswith(".project.json"))
)
def test_every_example_round_trips_unchanged(name):
    """Assert on the round-tripped dict, not the file: the chain must be a no-op
    for a current project, or a user's saved work drifts every time they open it."""
    path = os.path.join(_EXAMPLES, name)
    once = io.project_to_dict(io.load_project(path))
    twice = io.project_to_dict(io.project_from_dict(once))
    assert twice == once


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
