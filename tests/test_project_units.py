"""Whole-project Imperial<->SI display conversion (Project JSON Editor page).

Guards the failure modes that matter for a field-name-driven converter:
a mass field (weight_lb, lbm) and a force field (load_lb, lbf) must use
*different* factors even though both end in "_lb", and the round trip through
project_dict_to_display/project_dict_to_imperial must be lossless (so Apply on
the editor page never silently drifts a project's numbers). Airspeed/altitude
must never be touched, per CLAUDE.md's aviation-standard-units decision.

**The completeness guard** (``test_every_dimensional_project_field_is_classified``)
is the one that had been missing, and its absence is why ``EngineInput.thrust_lb``
shipped unclassified: it displayed raw pounds in the SI view while every
neighbour converted. A round-trip test cannot see that -- an unconverted field is
lossless in both directions -- and no fixture entered a thrust, so a
fixture-driven check could not see it either. The guard therefore walks the
**type graph** reachable from ``Project``, not the fixtures, so a field no
project has ever set is still covered the day it is added.
"""

import dataclasses
import math
import os
import re
import typing

from sloads import UnitSystem, io
from sloads.models import Project
from sloads.units import (
    _NOT_DIMENSIONAL,
    _PROJECT_FIELD_KIND,
    project_dict_to_display,
    project_dict_to_imperial,
    project_field_si_label,
)

_EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


def _round_trip_close(a, b, path=""):
    if isinstance(a, dict):
        for k in a:
            _round_trip_close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        for i, (x, y) in enumerate(zip(a, b)):
            _round_trip_close(x, y, f"{path}[{i}]")
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9), f"{path}: {a} != {b}"
    else:
        assert a == b, f"{path}: {a!r} != {b!r}"


def test_mass_and_force_lb_fields_use_different_factors():
    # A pounds-mass weight (0.45359237 kg/lb) must not be confused with a
    # pounds-force load (4.4482216152605 N/lb) -- same "_lb" suffix, ~9.8x
    # different factor. Regression for the exact bug class this table exists
    # to prevent.
    d = {"weight_lb": 100.0, "load_lb": 100.0}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert math.isclose(si["weight_lb"], 45.359237, rel_tol=1e-9)
    assert math.isclose(si["load_lb"], 444.82216152605, rel_tol=1e-9)


def test_airspeed_and_altitude_are_never_converted():
    d = {"vh_kt": 150.0, "altitude_ft": 8000.0, "shoulder_altitude_ft": 12000.0}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si == d


def test_unknown_field_passes_through_unconverted():
    d = {"some_future_field": 42.0}
    assert project_dict_to_display(d, UnitSystem.SI) == d


def test_imperial_is_a_no_op():
    d = {"weight_lb": 100.0, "engine_cg": [1.0, 2.0, 3.0]}
    assert project_dict_to_display(d, UnitSystem.IMPERIAL) == d
    assert project_dict_to_imperial(d, UnitSystem.IMPERIAL) == d


def test_round_trip_is_lossless_on_example_projects():
    for fname in ("ga6_normal.project.json", "dhc8_dash8.project.json", "concept_heavy.project.json"):
        project = io.load_project(os.path.join(_EXAMPLES, fname))
        original = io.project_to_dict(project)
        si = project_dict_to_display(original, UnitSystem.SI)
        back = project_dict_to_imperial(si, UnitSystem.SI)
        _round_trip_close(original, back)


def test_engine_cg_vector_converts_as_length():
    d = {"engine_cg": [10.0, 0.0, -5.0]}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si["engine_cg"] == [254.0, 0.0, -127.0]
    back = project_dict_to_imperial(si, UnitSystem.SI)
    assert back["engine_cg"] == d["engine_cg"]


# --------------------------------------------------------------------------- #
# The completeness guard (CLAUDE.md rule 3: a convention gets a drift guard,
# never a prose rule alone)
# --------------------------------------------------------------------------- #
#: A field name that names a physical quantity, by the schema's own suffix
#: conventions (``models.py`` documents every one of these as dimensional).
#: ``_kt`` / ``_ft`` / ``_deg`` are deliberately absent: airspeed and altitude
#: stay aviation-standard in both systems and angles have nothing to convert,
#: which is the same decision ``_PROJECT_FIELD_KIND``'s own comment records.
_DIMENSIONAL_NAME = re.compile(
    r"(_lb$|_in$|_sqft$|_sqin$|_hp$|torque|inertia|^psi$|_psi$)")

#: The ``Project`` slices ``io.project_to_dict`` actually writes -- read from
#: ``io`` itself rather than listed here, so a new persisted slice joins the
#: guard automatically. Result slices (``loads``, ``envelope``) are reachable
#: from ``Project`` by type but are never written to ``project.json``, so the
#: project-field table has no business classifying their fields.
def _persisted_slice_names():
    return set(io.project_to_dict(
        io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))))


def _reachable_fields():
    """``{field name: owning class}`` for every dataclass field reachable from
    the persisted slices of ``Project``, by type -- so an optional field that no
    fixture sets is covered exactly like one they all set."""
    def unwrap(hint):
        args = typing.get_args(hint)
        if args:
            return [t for a in args for t in unwrap(a)]
        return [hint] if isinstance(hint, type) else []

    seen, found = set(), {}

    def walk(cls):
        if cls in seen or not dataclasses.is_dataclass(cls):
            return
        seen.add(cls)
        try:
            hints = typing.get_type_hints(cls)
        except Exception:                                    # pragma: no cover
            hints = {f.name: f.type for f in dataclasses.fields(cls)}
        for f in dataclasses.fields(cls):
            found.setdefault(f.name, cls.__name__)
            for sub in unwrap(hints.get(f.name, f.type)):
                walk(sub)

    persisted = _persisted_slice_names()
    hints = typing.get_type_hints(Project)
    for f in dataclasses.fields(Project):
        if f.name not in persisted:
            continue
        found.setdefault(f.name, "Project")
        for sub in unwrap(hints.get(f.name, f.type)):
            walk(sub)
    return found


def test_every_dimensional_project_field_is_classified():
    """Every dimensional leaf the editor can show is in the table, or is
    explicitly exempt with a reason.

    The guard ``thrust_lb`` needed. An unclassified dimensional field is not a
    crash and not a data loss -- it round-trips perfectly, because it is
    unconverted in both directions -- it is a **wrong number on screen**, shown
    beside converted neighbours with no unit label. This is the only check that
    can see that, and it reads the schema rather than the fixtures.
    """
    unclassified = sorted(
        (name, owner) for name, owner in _reachable_fields().items()
        if _DIMENSIONAL_NAME.search(name)
        and name not in _PROJECT_FIELD_KIND
        and name not in _NOT_DIMENSIONAL)
    assert not unclassified, (
        "these project fields name a physical quantity but sloads.units."
        "_PROJECT_FIELD_KIND does not classify them, so the Project JSON "
        "Editor shows them unconverted and unlabelled in the SI view. Add a "
        "row (or add the name to _NOT_DIMENSIONAL with the reason it is not a "
        f"quantity): {unclassified}")


def test_the_exempt_list_only_holds_fields_that_are_not_quantities():
    """The exemption cannot become a dumping ground: every name on it must
    still be a field that exists, and must not be classified as well."""
    reachable = _reachable_fields()
    for name in _NOT_DIMENSIONAL:
        assert name in reachable, (
            f"{name} is exempted from the units table but is no longer a "
            "project field -- remove the entry")
        assert name not in _PROJECT_FIELD_KIND, (
            f"{name} is both exempt and classified -- pick one")


def test_a_classified_field_always_has_an_si_label():
    """The table and the label view cannot disagree: what converts, labels."""
    for name in _PROJECT_FIELD_KIND:
        assert project_field_si_label(name), name


def test_thrust_is_a_force_not_a_weight():
    """Regression for the field that found the gap: ``thrust_lb`` is lbf -> N
    (4.448), never lbm -> kg (0.4536). Same suffix, ~9.8x apart."""
    si = project_dict_to_display({"thrust_lb": 1000.0}, UnitSystem.SI)
    assert math.isclose(si["thrust_lb"], 4448.2216152605, rel_tol=1e-9)
    assert project_field_si_label("thrust_lb") == "N"


def test_a_classified_key_converts_a_numeric_list_elementwise():
    """One rule for scalars and lists: the aileron hinge stations are the same
    quantity repeated, and were passing through unconverted beside their
    scalar neighbours."""
    d = {"hinges_span_in": [12.0, 30.0], "actuator_span_in": 5.0}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si["hinges_span_in"] == [304.79999999999995, 762.0]
    assert si["actuator_span_in"] == 127.0
    # Closeness, not equality: 12 in -> 304.8 mm -> 12 in is a float round trip
    # (the engine_cg case is exact only because 254.0 happens to be).
    _round_trip_close(d, project_dict_to_imperial(si, UnitSystem.SI))


def test_an_empty_or_mixed_list_is_left_alone():
    """Nothing to convert, and a list that is not all numbers is not a vector
    of one quantity -- both pass through rather than raising."""
    d = {"hinges_span_in": [], "some_future_field": [1.0, "x"]}
    assert project_dict_to_display(d, UnitSystem.SI) == d


if __name__ == "__main__":
    test_every_dimensional_project_field_is_classified()
    test_the_exempt_list_only_holds_fields_that_are_not_quantities()
    test_a_classified_field_always_has_an_si_label()
    test_thrust_is_a_force_not_a_weight()
    test_a_classified_key_converts_a_numeric_list_elementwise()
    test_an_empty_or_mixed_list_is_left_alone()
    test_mass_and_force_lb_fields_use_different_factors()
    test_airspeed_and_altitude_are_never_converted()
    test_unknown_field_passes_through_unconverted()
    test_imperial_is_a_no_op()
    test_round_trip_is_lossless_on_example_projects()
    test_engine_cg_vector_converts_as_length()
    print("OK")
