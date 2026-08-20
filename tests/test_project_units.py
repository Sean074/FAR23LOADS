"""Whole-project Imperial<->SI display conversion (Project JSON Editor page).

Guards the failure modes that matter for a field-name-driven converter:
a mass field (weight_lb, lbm) and a force field (load_lb, lbf) must use
*different* factors even though both end in "_lb", and the round trip through
project_dict_to_display/project_dict_to_imperial must be lossless (so Apply on
the editor page never silently drifts a project's numbers). Airspeed/altitude
must never be touched, per CLAUDE.md's aviation-standard-units decision.

**The completeness guard** (``test_every_numeric_project_field_is_classified``)
is the one that had been missing, and its absence is why ``EngineInput.thrust_lb``
shipped unclassified: it displayed raw pounds in the SI view while every
neighbour converted. A round-trip test cannot see that -- an unconverted field is
lossless in both directions -- and no fixture entered a thrust, so a
fixture-driven check could not see it either. The guard therefore walks the
**type graph** reachable from ``Project``, not the fixtures, so a field no
project has ever set is still covered the day it is added.

Its question was inverted on 2026-08-19. It used to ask *does this name look
dimensional?*, from a suffix regex, which meant a quantity whose name breaks the
suffix convention was invisible to the guard rather than reported by it --
thirty-four lengths and weights were, ``xt25`` and ``gross_weight`` among them.
It now asks the total question instead: **every numeric field is classified**,
converted or aviation-standard or dimensionless-with-a-reason, and a new one
fails here until somebody decides which.
"""

import dataclasses
import math
import os
import re
import typing

from sloads import UnitSystem, field_registry, io
from sloads.models import Project
from sloads.units import (
    _DIMENSIONLESS_RULES,
    _NOT_DIMENSIONAL,
    _PROJECT_FIELD_KIND,
    _PROJECT_PAIR_KIND,
    AVIATION_STANDARD,
    field_classification,
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
#: The ``Project`` slices that hold **input** data, read from the field registry
#: -- the schema-walk owner, whose own gate G4 already keeps it total, and whose
#: ``NON_INPUT`` names the exclusions with reasons (result slices, the schema
#: stamp, the units preference, document metadata: none of them airplane data a
#: unit applies to).
#:
#: This used to be the slice list of one example project, which made the guard
#: only as complete as ``ga6_normal`` happened to be: a single-engine airplane
#: has no ``one_engine_out`` slice, so every field on it -- and on ``tail_mass``,
#: which no shipped example sets -- was outside the guard entirely.
def _input_slice_names():
    return {path.split(".")[0].replace(field_registry.LIST_MARKER, "")
            for path in field_registry.schema_paths()}


def _is_numeric(hint):
    """True if an annotation bottoms out in ``float``/``int`` only.

    ``Optional[float]``, ``List[float]``, ``Vec3``, ``XYPoint``,
    ``List[XYPoint]`` and the five-term coefficient tuples all qualify -- they
    are numbers a unit could apply to. ``bool`` does not (it is an ``int`` by
    inheritance, never by identity), nor does a ``str``, an ``Enum`` or a nested
    dataclass.
    """
    args = typing.get_args(hint)
    if args:
        parts = [a for a in args if a is not type(None) and a is not Ellipsis]
        return bool(parts) and all(_is_numeric(a) for a in parts)
    return hint is float or hint is int


def _reachable_fields():
    """``{field name: (owning class, is-numeric)}`` for every dataclass field
    reachable from the input slices of ``Project``, by type -- so an optional
    field that no fixture sets is covered exactly like one they all set."""
    def unwrap(hint):
        args = typing.get_args(hint)
        if args:
            return [t for a in args for t in unwrap(a)]
        return [hint] if isinstance(hint, type) else []

    seen, found = set(), {}

    def record(name, owner, hint):
        found.setdefault(name, (owner, _is_numeric(hint)))

    def walk(cls):
        if cls in seen or not dataclasses.is_dataclass(cls):
            return
        seen.add(cls)
        try:
            hints = typing.get_type_hints(cls)
        except Exception:                                    # pragma: no cover
            hints = {f.name: f.type for f in dataclasses.fields(cls)}
        for f in dataclasses.fields(cls):
            hint = hints.get(f.name, f.type)
            record(f.name, cls.__name__, hint)
            for sub in unwrap(hint):
                walk(sub)

    persisted = _input_slice_names()
    hints = typing.get_type_hints(Project)
    for f in dataclasses.fields(Project):
        if f.name not in persisted:
            continue
        hint = hints.get(f.name, f.type)
        record(f.name, "Project", hint)
        for sub in unwrap(hint):
            walk(sub)
    return found


def test_every_numeric_project_field_is_classified():
    """Every numeric leaf the editor can show is classified, one of three ways.

    The guard ``thrust_lb`` needed, run the right way round. It used to ask *does
    this name look dimensional?* -- a suffix regex over ``_lb``/``_in``/``_sqft``
    and friends -- and a length whose name does not follow the suffix convention
    was therefore invisible to it. Thirty-four were: ``xt25`` sat unconverted at
    261.0 in the SI view beside ``htail_semispan_in`` showing 1856.7 mm, on the
    same record, and ``gross_weight`` displayed 3400 lb as 3400 kg.

    So the question is inverted. Every **numeric** field must be classified --
    converted, aviation-standard, or dimensionless with a stated reason -- and a
    new one is a failure here until somebody decides which. That is the same
    totality standard ``field_registry``'s gate G4 holds 323 fields to, and the
    only kind that can see a defect nobody thought to look for: an unclassified
    quantity is not a crash and not a data loss (it round-trips perfectly,
    unconverted in both directions), it is a **wrong number on screen**.
    """
    unclassified = sorted(
        (name, owner) for name, (owner, numeric) in _reachable_fields().items()
        if numeric and field_classification(name) is None)
    assert not unclassified, (
        "these project fields hold a number that sloads.units classifies no "
        "way at all, so the Project JSON Editor shows them unconverted and "
        "unlabelled in the SI view. Classify each: a row in _PROJECT_FIELD_KIND "
        "(or _PROJECT_PAIR_KIND for an [[a, b], ...] curve) if it is a quantity, "
        "AVIATION_STANDARD if it is KEAS/ft, else _NOT_DIMENSIONAL with the "
        f"reason it carries no unit: {unclassified}")


def test_every_classification_is_of_a_field_that_exists():
    """No table may name a field the schema no longer has -- the inverse of the
    totality guard, and what keeps a stale row from looking like coverage."""
    reachable = _reachable_fields()
    for table, label in ((_NOT_DIMENSIONAL, "_NOT_DIMENSIONAL"),
                         (AVIATION_STANDARD, "AVIATION_STANDARD"),
                         (_PROJECT_PAIR_KIND, "_PROJECT_PAIR_KIND")):
        for name in table:
            assert name in reachable, (
                f"{name} is listed in {label} but is no longer a project field "
                "-- remove the entry")


def test_no_field_is_classified_twice():
    """The three buckets are exclusive: converted, aviation-standard, or nothing
    to convert. A name in two of them means one of the two is a wrong answer,
    and ``field_classification`` would silently prefer whichever it checks first.
    """
    for name in _PROJECT_FIELD_KIND:
        assert name not in _NOT_DIMENSIONAL, f"{name}: converted and exempt"
        assert name not in AVIATION_STANDARD, f"{name}: converted and aviation-standard"
        assert name not in _PROJECT_PAIR_KIND, f"{name}: scalar kind and pair kind"
    for name in AVIATION_STANDARD:
        assert name not in _NOT_DIMENSIONAL, f"{name}: aviation-standard and exempt"
    for name in list(_NOT_DIMENSIONAL) + list(AVIATION_STANDARD):
        matched = [p for p, _r in _DIMENSIONLESS_RULES if re.search(p, name)]
        assert not matched or name in _NOT_DIMENSIONAL, (
            f"{name} is aviation-standard but rule {matched} calls it dimensionless")


def test_every_exemption_states_a_reason():
    """A reason, not a shrug. ``_NOT_DIMENSIONAL`` was a bare set of names; a
    name alone records that somebody decided, not what they decided."""
    for name, reason in _NOT_DIMENSIONAL.items():
        assert reason and len(reason) > 5, f"{name}: {reason!r} is not a reason"
    for pattern, reason in _DIMENSIONLESS_RULES:
        assert reason and len(reason) > 5, f"{pattern}: {reason!r} is not a reason"


def test_every_dimensionless_rule_still_covers_something():
    """A rule that matches no field is dead weight standing in for coverage --
    and worse, it would keep matching a *future* field by accident."""
    names = [n for n, (_owner, numeric) in _reachable_fields().items() if numeric]
    for pattern, _reason in _DIMENSIONLESS_RULES:
        assert any(re.search(pattern, n) for n in names), (
            f"no numeric project field matches {pattern!r} -- remove the rule")


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


def test_an_unsuffixed_length_converts_like_its_suffixed_neighbour():
    """Regression for the class the suffix-driven guard could not see: two inch
    stations on the same record, one named ``_in`` and one not, must convert
    identically. Before 2026-08-19 ``xt25`` did not convert at all."""
    d = {"xt25": 261.027, "htail_semispan_in": 73.1, "gross_weight": 3400.0}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert math.isclose(si["xt25"], 261.027 * 25.4, rel_tol=1e-12)
    assert math.isclose(si["htail_semispan_in"], 73.1 * 25.4, rel_tol=1e-12)
    assert math.isclose(si["gross_weight"], 3400.0 * 0.45359237, rel_tol=1e-9)
    _round_trip_close(d, project_dict_to_imperial(si, UnitSystem.SI))


def test_a_pair_curve_converts_only_the_members_that_carry_a_unit():
    """The planform edges are (station, station) and convert on both members; a
    spanwise curve is (station, coefficient) and converts on the first only.
    Converting a profile-drag coefficient by 25.4 is the failure this shape
    exists to prevent, and one kind per field could not express it."""
    d = {"leading_edge": [[45.0, 0.0], [72.0, 201.0]],
         "profile_drag": [[0.0, 0.01], [201.0, 0.01]]}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si["leading_edge"] == [[45.0 * 25.4, 0.0], [72.0 * 25.4, 201.0 * 25.4]]
    assert si["profile_drag"] == [[0.0, 0.01], [201.0 * 25.4, 0.01]]
    _round_trip_close(d, project_dict_to_imperial(si, UnitSystem.SI))


def test_a_gear_point_converts_as_a_pair_of_stations():
    """``axle_static`` is a flat ``(X, Z)`` inch pair -- one quantity twice, so
    an ordinary element-wise row, not a curve."""
    d = {"axle_static": [96.7, 59.6]}
    si = project_dict_to_display(d, UnitSystem.SI)
    assert si["axle_static"] == [96.7 * 25.4, 59.6 * 25.4]


if __name__ == "__main__":
    test_every_numeric_project_field_is_classified()
    test_every_classification_is_of_a_field_that_exists()
    test_no_field_is_classified_twice()
    test_every_exemption_states_a_reason()
    test_every_dimensionless_rule_still_covers_something()
    test_an_unsuffixed_length_converts_like_its_suffixed_neighbour()
    test_a_pair_curve_converts_only_the_members_that_carry_a_unit()
    test_a_gear_point_converts_as_a_pair_of_stations()
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
