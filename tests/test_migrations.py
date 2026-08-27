"""The schema gate (#93), and the migration machinery kept behind it.

Pre-production a project file is read at the current ``SCHEMA_VERSION`` or a
version the hop chain reaches it from — since note 36 (OV-10, #97) that is v55,
through the additive-identity 55→56 hop — and `sloads.migrations.migrate`
raises `SchemaVersionError` for anything else: older than the floor, newer, or
unversioned. This file pins that gate, and pins that the hop chain works
(`migrations.py` module docstring).

Until #93 this file tested twelve hops against eleven frozen legacy fixtures
(M4-10). Those hops and fixtures went out together; what remains of that
discipline is `tests/fixtures_schema/v55_current.json`, one frozen file at the
version this build reads, and the examples-are-current guard in
`test_schema_guards.py`.
"""

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.migrations import (
    MIGRATIONS,
    SUPPORTED_FLOOR,
    SchemaVersionError,
    applied_hops,
    migrate,
    source_schema_version,
)
from sloads.models import SCHEMA_VERSION

_HERE = os.path.dirname(os.path.abspath(__file__))
_FIXTURES = os.path.join(_HERE, "fixtures_schema")
_EXAMPLES = os.path.join(os.path.dirname(_HERE), "examples")
_CURRENT = "v56_current.json"


def _load(name=_CURRENT):
    with open(os.path.join(_FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# 1. The gate
# --------------------------------------------------------------------------- #
def test_the_floor_is_the_oldest_hop():
    """#93's gate with note 36's one live hop: the floor is where the chain
    starts, and every version from there to current is a registered hop."""
    assert SUPPORTED_FLOOR == min(MIGRATIONS) == 55
    assert sorted(MIGRATIONS) == list(range(SUPPORTED_FLOOR, SCHEMA_VERSION))


def test_a_current_file_passes_through_untouched():
    current = _load()
    assert current["schema_version"] == SCHEMA_VERSION, "the frozen fixture went stale"
    assert migrate(current) == current


@pytest.mark.parametrize("version", [SUPPORTED_FLOOR - 1, SCHEMA_VERSION - 14, 18, 0])
def test_an_older_file_is_refused_and_says_both_versions(version):
    d = {**_load(), "schema_version": version}
    with pytest.raises(SchemaVersionError) as exc:
        migrate(d)
    assert f"schema {version}" in str(exc.value)
    assert str(SCHEMA_VERSION) in str(exc.value)


def test_a_newer_file_is_refused_too():
    """Symmetry is the point: a file this build cannot fully read is refused
    whichever side it comes from. The old chain let a newer file through on
    'read what you understand', which pre-production means presenting a partial
    read of someone else's schema as this build's answer."""
    d = {**_load(), "schema_version": SCHEMA_VERSION + 5}
    with pytest.raises(SchemaVersionError):
        migrate(d)


def test_an_unversioned_dict_is_refused_by_name():
    """Including the bare ``EngineInput`` file that used to be discriminated by
    key-sniffing: no stamp, no read."""
    with pytest.raises(SchemaVersionError) as exc:
        migrate({"engine_designation": "CONTINENTAL IO-520-BB", "engine_type": "R"})
    assert "no schema_version" in str(exc.value)


def test_a_string_version_is_not_mistaken_for_the_number():
    with pytest.raises(SchemaVersionError):
        migrate({"schema_version": str(SCHEMA_VERSION), "geometry": {}})


def test_the_refusal_reaches_every_front_end_through_one_funnel():
    """``project_from_dict`` is what CLI, both GUIs and the tests all call."""
    with pytest.raises(SchemaVersionError):
        io.project_from_dict({**_load(), "schema_version": 41})


def test_the_refusal_is_a_value_error():
    """So it lands in the documented error contract and every existing load
    handler reports it without a new except branch."""
    assert issubclass(SchemaVersionError, ValueError)


def test_source_schema_version_reads_the_file_not_the_default():
    assert source_schema_version({"schema_version": 41}) == 41
    assert source_schema_version({}) == -1
    assert source_schema_version({"schema_version": "41"}) == -1


# --------------------------------------------------------------------------- #
# 2. The machinery, kept
# --------------------------------------------------------------------------- #
def test_a_registered_hop_still_runs():
    """This is what a migration looks like: register the hop, lower the floor."""
    def _hop(d):
        d["migrated"] = True
        return d

    original = dict(MIGRATIONS)
    try:
        MIGRATIONS[SCHEMA_VERSION] = _hop
        out = migrate(_load())
        assert out["migrated"] is True
        assert out["schema_version"] == SCHEMA_VERSION
        assert applied_hops(SCHEMA_VERSION) == [SCHEMA_VERSION]
    finally:
        MIGRATIONS.clear()
        MIGRATIONS.update(original)
    assert applied_hops(SCHEMA_VERSION) == [], "the chain did not reset"


def test_a_v55_file_loads_through_the_identity_hop_unchanged():
    """Gate G-OV-5 (note 36, OV-10): the 55->56 hop is an identity -- a v55
    file loads with nothing but its stamp moved, ``applied_hops(55)`` names the
    hop, and the loaded ``Project`` equals the same file loaded at v56."""
    v55 = _load("v55_current.json")
    assert v55["schema_version"] == 55
    out = migrate(v55)
    assert out["schema_version"] == SCHEMA_VERSION
    assert {k: v for k, v in out.items() if k != "schema_version"} == \
           {k: v for k, v in v55.items() if k != "schema_version"}
    assert applied_hops(55) == [55]
    assert io.project_to_dict(io.project_from_dict(v55)) == \
           io.project_to_dict(io.project_from_dict(_load()))


def test_migrate_does_not_mutate_the_callers_dict():
    """The GUI hands the same dict to the JSON editor after loading it."""
    original = _load()
    snapshot = copy.deepcopy(original)
    migrate(original)
    assert original == snapshot


def test_migrate_is_idempotent():
    once = migrate(_load())
    assert migrate(once) == once


def test_applied_hops_matches_the_chain():
    assert applied_hops(SCHEMA_VERSION) == []            # nothing at/above current
    assert applied_hops(SUPPORTED_FLOOR) == sorted(MIGRATIONS) == [55]


# --------------------------------------------------------------------------- #
# 3. The acceptance criterion: no project changes on the way through
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name", sorted(f for f in os.listdir(_EXAMPLES) if f.endswith(".project.json"))
)
def test_every_example_round_trips_unchanged(name):
    """Assert on the round-tripped dict, not the file: the load must be a no-op
    for a current project, or a user's saved work drifts every time they open it."""
    path = os.path.join(_EXAMPLES, name)
    once = io.project_to_dict(io.load_project(path))
    twice = io.project_to_dict(io.project_from_dict(once))
    assert twice == once


def test_the_frozen_fixture_and_the_examples_agree_on_the_version():
    """Two independent copies of 'current' -- if they can disagree, one of them
    is stale and the gate's own tests would be testing the wrong number."""
    fixture = _load()["schema_version"]
    for name in sorted(f for f in os.listdir(_EXAMPLES) if f.endswith(".project.json")):
        with open(os.path.join(_EXAMPLES, name), encoding="utf-8") as fh:
            assert json.load(fh)["schema_version"] == fixture, name


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
