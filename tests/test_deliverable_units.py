"""Deliverable unit sets — M4-20 step 1.

Every deliverable renders in the unit system the user selected
(``docs/10_standard/00_program_overview.md`` §Units; ``SUMMARY_REPORT.md`` §3.5).
This file pins the unit *set* those writers will be handed, before any writer
consumes it:

* the **Imperial identity** — an all-1.0 set, so a writer needs no
  ``if system == IMPERIAL`` branch and Imperial output cannot drift;
* the **dimensional identity** ``moment == force × length`` for the solver
  channel, which is what stops an ``N·m`` moment reaching a deck whose GRIDs are
  in mm (decision D-19: a silent 1000× torsion error);
* the **aviation carve-out** — KEAS and altitude are never converted;
* a **standing guard** that every load unit the renderer knows has an SI mapping,
  so the next unit added without one fails here rather than shipping a mixed-unit
  table.

Plan: ``docs/30_future/06_m4-20_deliverable_units_plan.md`` §4 step 1.
"""

from __future__ import annotations

import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli  # noqa: E402
from sloads import io  # noqa: E402
from sloads.models import ConditionResult, LoadValue, Project
from sloads.report.render import _LOAD_UNITS, _ULT_UNITS, ultimate_units  # noqa: E402
from sloads.units import (  # noqa: E402
    _RESULT_TO_SI,
    Channel,
    UnitSystem,
    convert_results,
    deliverable_units,
    unit_system_from,
    units_statement,
)

_DIMENSIONS = ("force", "length", "moment", "torque", "pressure")


# --------------------------------------------------------------------------- #
# The Imperial identity
# --------------------------------------------------------------------------- #
def test_imperial_is_the_all_one_identity():
    """Imperial factors are exactly 1.0 in both channels.

    This is the property the "Imperial output is unchanged" guarantee rests on:
    a writer multiplies unconditionally and the Imperial path is arithmetically
    the same code, not a separate branch that could diverge.
    """
    for channel in (Channel.HUMAN, Channel.SOLVER):
        u = deliverable_units(UnitSystem.IMPERIAL, channel)
        for dim in _DIMENSIONS:
            assert getattr(u, dim).factor == 1.0, f"{channel} {dim}"
        assert u.force.label == "lb"
        assert u.length.label == "in"
        assert u.moment.label == "lb-in"


def test_imperial_moment_unit_is_identical_in_both_channels():
    """The channel split is an SI-only concern; Imperial has one unit set."""
    human = deliverable_units(UnitSystem.IMPERIAL, Channel.HUMAN)
    solver = deliverable_units(UnitSystem.IMPERIAL, Channel.SOLVER)
    assert human.moment == solver.moment


# --------------------------------------------------------------------------- #
# The dimensional identity (D-19) — the invariant a solver deck needs
# --------------------------------------------------------------------------- #
def test_solver_set_is_dimensionally_consistent():
    """``moment == force × length`` exactly, in both systems.

    sbeam is only correct in a consistent unit set. With GRID coordinates in mm
    and FORCE in N, a MOMENT card must be N·mm; an N·m moment is wrong by 1000×
    in a file that parses cleanly. The factors are *derived* as force × length in
    ``units.py`` rather than quoted, so this holds by construction — this test is
    what keeps it that way.
    """
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        u = deliverable_units(system, Channel.SOLVER)
        assert u.is_consistent, f"{system}: {u.moment} != {u.force} x {u.length}"
        assert u.moment.factor == u.force.factor * u.length.factor


def test_human_set_is_not_dimensionally_consistent_in_si():
    """The human set pairs N·m with a mm length — deliberately, and it must never
    be used to write a deck. Pinned so the channel split cannot be "tidied" away."""
    u = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    assert not u.is_consistent
    assert u.moment.label == "N·m"


def test_the_two_channels_differ_only_in_the_moment():
    human = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    solver = deliverable_units(UnitSystem.SI, Channel.SOLVER)
    assert human.moment != solver.moment
    for dim in ("force", "length", "torque", "pressure"):
        assert getattr(human, dim) == getattr(solver, dim), dim


def test_si_factors_are_the_exact_nist_products():
    solver = deliverable_units(UnitSystem.SI, Channel.SOLVER)
    assert solver.force.factor == 4.4482216152605      # lbf -> N
    assert solver.length.factor == 25.4                # in -> mm
    assert solver.moment.factor == 4.4482216152605 * 25.4   # lb-in -> N·mm
    human = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    # lb-in -> N·m is the same product with the length in metres.
    assert math.isclose(human.moment.factor, 0.11298482902761668, rel_tol=1e-15)


# --------------------------------------------------------------------------- #
# In-band statement
# --------------------------------------------------------------------------- #
def test_units_statement_names_the_system_and_its_set():
    assert units_statement(deliverable_units(UnitSystem.IMPERIAL)) == "Imperial (lb, in, lb-in)"
    assert units_statement(deliverable_units(UnitSystem.SI, Channel.HUMAN)) == "SI (N, mm, N·m)"
    assert units_statement(deliverable_units(UnitSystem.SI, Channel.SOLVER)) == "SI (N, mm, N·mm)"


# --------------------------------------------------------------------------- #
# The mappings this step adds — both were reachable, unconverted, in SI
# --------------------------------------------------------------------------- #
def _one(units: str, value: float = 1.0, quantity: str = "") -> LoadValue:
    return ConditionResult(
        title="t", far_reference="23.000",
        values=[LoadValue(label="x", value=value, units=units, quantity=quantity)],
    )


def test_lb_in_moments_now_convert_to_si():
    """``lb-in`` had no SI mapping: 1240 values across the six examples stayed
    Imperial inside an otherwise-converted table (root bending/torsion, pitching
    moment). Fixed by M4-20 step 1."""
    out = convert_results([_one("lb-in", 100.0)], UnitSystem.SI)[0].values[0]
    assert out.units == "N·m"
    assert math.isclose(out.value, 11.298482902761668, rel_tol=1e-12)


def test_design_pressure_now_converts_to_si():
    """``lb/in^2`` had no SI mapping: 340 values stayed Imperial. Fixed here."""
    out = convert_results([_one("lb/in^2", 10.0)], UnitSystem.SI)[0].values[0]
    assert out.units == "kPa"
    assert math.isclose(out.value, 68.94757, rel_tol=1e-12)


def test_converted_si_loads_still_take_an_ultimate_marker():
    """A newly-convertible unit must also be recognised as a *load* by the
    ultimate boundary, or it would convert and then silently lose its ``-ULT``
    marker — a limit load presented as a deliverable."""
    assert ultimate_units("N·m") == "Nm-ULT"
    assert ultimate_units("N·mm") == "Nmm-ULT"
    assert ultimate_units("kPa") == "kPa-ULT"


# --------------------------------------------------------------------------- #
# The aviation carve-out
# --------------------------------------------------------------------------- #
def test_airspeed_and_altitude_are_never_converted():
    """KEAS and ft are aviation-standard in *both* systems.

    The calc emits ``kt(EAS)`` and ``ft``. A ``"knot"`` row lived in the SI table
    until M4-20 and matched nothing (no producer has ever emitted that string),
    but it would have broken the carve-out the day one did; it is gone.
    """
    for unit in ("kt(EAS)", "ft"):
        out = convert_results([_one(unit, 120.0)], UnitSystem.SI)[0].values[0]
        assert out.units == unit
        assert out.value == 120.0
    assert "knot" not in _RESULT_TO_SI


# --------------------------------------------------------------------------- #
# Standing guard — catches the *next* missing mapping
# --------------------------------------------------------------------------- #
def test_every_imperial_load_unit_has_an_si_mapping():
    """A load unit the renderer knows but ``units.py`` cannot convert produces a
    mixed-unit table in SI: everything around it converts and it does not, with
    no error anywhere. That is exactly how ``lb-in`` and ``lb/in^2`` went
    unnoticed. This fails when the next one is added without its factor.
    """
    # An SI unit is any label an SI unit set can produce -- from the per-value
    # conversion table *or* from either channel's deliverable set (N·mm is only
    # ever minted by the solver set, so the table alone under-counts).
    si_units = {label for _, label in _RESULT_TO_SI.values()}
    for channel in (Channel.HUMAN, Channel.SOLVER):
        u = deliverable_units(UnitSystem.SI, channel)
        si_units |= {getattr(u, d).label for d in _DIMENSIONS}

    for unit in _LOAD_UNITS:
        if unit in si_units:
            continue  # already an SI unit (N, N·m, N·mm, kPa)
        assert unit in _RESULT_TO_SI, f"load unit {unit!r} has no SI conversion"


def test_every_load_unit_has_an_ultimate_marker():
    """Same guard for the ``-ULT`` side: a load unit with no marker would be
    exported as a bare limit-looking number."""
    for unit in _LOAD_UNITS:
        assert unit in _ULT_UNITS, f"load unit {unit!r} has no -ULT marker"


# --------------------------------------------------------------------------- #
# Selection plumbing (M4-20 step 2): Project.unit_system, schema 38, the CLI flag
# --------------------------------------------------------------------------- #
def test_unit_system_defaults_to_imperial_and_parses_leniently():
    """An unreadable preference degrades to the documented default. A project file
    is not a place to raise: a junk value must never block the load of an
    otherwise-valid project."""
    assert Project(name="x").unit_system == "imperial"
    assert unit_system_from("si") is UnitSystem.SI
    assert unit_system_from("SI") is UnitSystem.SI
    assert unit_system_from("  Imperial ") is UnitSystem.IMPERIAL
    assert unit_system_from(UnitSystem.SI) is UnitSystem.SI
    for junk in (None, "", "metric", "furlongs", 7, []):
        assert unit_system_from(junk) is UnitSystem.IMPERIAL, junk


def test_unit_system_round_trips_and_stays_out_of_a_default_file():
    """Written only when non-default, on the document-control precedent: a project
    that never chose a system round-trips byte-identically to a pre-v38 file."""
    p = Project(name="x")
    assert "unit_system" not in io.project_to_dict(p)

    p.unit_system = "si"
    d = io.project_to_dict(p)
    assert d["unit_system"] == "si"
    assert io.project_from_dict(d).unit_system == "si"


def test_a_pre_v38_file_reads_as_imperial():
    """Absent *is* the value — which is why this needed no migration hop."""
    here = os.path.dirname(os.path.abspath(__file__))
    old = json.load(open(os.path.join(here, "fixtures_schema", "v37_no_unit_system.json")))
    assert "unit_system" not in old
    assert io.project_from_dict(old).unit_system == "imperial"


def test_v38_adds_no_key_to_the_shipped_examples():
    """None of the six examples chose a system, so none gains a ``unit_system``
    key and each still round-trips to a stable dict.

    (The round-trip is asserted as *idempotence*, not equality with the file on
    disk: ``io.py`` has always normalised some values on read — tuples for
    coordinate pairs, defaults filled in — which predates this item and is not
    what this test is about.)
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sorted(glob.glob(os.path.join(here, "examples", "*.project.json")))
    assert len(paths) == 6, paths
    for path in paths:
        with open(path) as fh:
            on_disk = json.load(fh)
        first = io.project_to_dict(io.project_from_dict(on_disk))
        second = io.project_to_dict(io.project_from_dict(first))
        assert "unit_system" not in first, os.path.basename(path)
        assert first == second, path


def test_cli_units_resolution_order():
    """Flag beats the project's preference, which beats Imperial."""
    imperial, si = Project(name="i"), Project(name="s", unit_system="si")
    assert cli.resolve_units(imperial) is UnitSystem.IMPERIAL
    assert cli.resolve_units(si) is UnitSystem.SI
    # the flag overrides the project, in both directions
    assert cli.resolve_units(imperial, "si") is UnitSystem.SI
    assert cli.resolve_units(si, "imperial") is UnitSystem.IMPERIAL
    # no flag, no preference -> today's behaviour, unchanged
    assert cli.resolve_units(Project(name="x"), None) is UnitSystem.IMPERIAL


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    mod = sys.modules[__name__]
    failed = 0
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        try:
            getattr(mod, name)()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print("OK" if not failed else f"{failed} failure(s)")
    sys.exit(1 if failed else 0)
