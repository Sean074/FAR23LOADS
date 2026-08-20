"""Gate G5 — the reduced input set is real (design note 32, OG-C/OG-D).

The oracle GUI's claim is that it asks for **less** and still gets the original
suite's answers. Until this file existed that was an assertion: OG-C's registry
said which fields the second front-end offers, and nothing checked that a
project holding only those fields still runs, let alone still matches Appendix A.

The gate as the note words it — *"with only ``origin=original`` fields populated
from ``ga6_normal``, all oracle-page modules run and every Appendix A oracle test
still passes at ±0.1 %"* — is checked in three parts:

1. **It runs.** Every oracle-page module behaves on the reduced project exactly
   as it does on the full one: the same modules succeed, and the ones that
   correctly refuse (``one_engine_out`` has no case on a single-engine airplane,
   OG-12) refuse the same way. No exception list, because "the reduction changes
   nothing about what runs" is the stronger and simpler claim.
2. **The numbers are the same.** Every load value the reduced project produces
   agrees with the full project's within the oracle tolerance. This is what
   carries the *"every Appendix A oracle test still passes"* half: the tests that
   hold Appendix A's printed figures — ``test_weight_onecg`` (p136),
   ``test_wing_geometry`` (p141-142), ``test_flight_envelope`` (p179-181),
   ``test_weight_envelope``, ``test_structural_speeds`` (p155-156) — all run on
   ``ga6_normal``, so agreement with the full project transfers every one of them
   onto the reduced set without restating a single figure.
3. **A short Appendix A spine, restated anyway.** Part 2 would be satisfied by a
   reduction that broke the oracle *and* the full project identically, so a
   handful of printed figures are asserted directly against the reduced project,
   page-cited. They are deliberately the ones the reduction got wrong first.

**What building this found.** The first run of part 2 failed on three modules,
and every failure was a misclassified row in the registry rather than a problem
with the gate — per-item inertia, the WTONECG loading-hierarchy tag, the wing
edge polylines, the CG-case corners, WTESTIMA's engine-weight code and ENGLOADS'
engine type were all marked ``SLOADS`` and are all inputs of a named ``.BAS``
program (``models/inputs.py`` says so in its own docstrings; Appendix A p136's
IXX 1201.527 comes out 66.7 without the item inertias). Twelve rows moved to
``ORIGINAL``, and the fields the second front-end must *write* without asking —
selectors, LANDLOAD's three loading roles — gained
:attr:`~sloads.field_registry.FieldEntry.supplied` rather than being quietly
folded into ``origin``, which answers a different question (who asked, not who
writes).
"""

from __future__ import annotations

import glob
import math
import os
from typing import Dict, Tuple

import pytest

from sloads import io, registry
from sloads import workflow as wf
from sloads.field_registry import (
    oracle_input_paths,
    original_paths,
    reduce_to_oracle_inputs,
    schema_paths,
    supplied_paths,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "examples")

#: The oracle tolerance: the manual's printed figures are ±0.1 % (`CLAUDE.md`).
TOL = 1e-3

#: Examples the reduction must reproduce **exactly**. These are airplanes the
#: original suite could analyse, which is the oracle GUI's whole scope.
EXACT: Tuple[str, ...] = (
    "ga6_normal.project.json",       # the Appendix A GA-6 airplane; G5 as worded
    "cessna_210.project.json",
    "atr42_100.project.json",
    "dhc8_dash8.project.json",
    "concept_heavy.project.json",
)

#: Examples the reduction is only required to keep *runnable*, with the reason.
#: An airplane the original suite has no method for is out of the oracle GUI's
#: scope by construction (OG-1/OG-6), so requiring the reduced project to
#: reproduce it would be claiming the second front-end covers ground the first
#: suite never did.
RUNS_ONLY: Dict[str, str] = {
    "concept_regional_jet.project.json":
        "FAR 25 concept airplane: the 25.335(b) Mach-margin dive-speed route "
        "(speeds.vd_basis, F25-2) and turbofan engine data have no counterpart "
        "in the original suite, so the reduced project falls back to the speed-"
        "ratio route and the recip/turboprop branch and diverges by design.",
}

#: Values the full project produces and the reduced one does not, with the
#: reason each is sloads-only output rather than a lost oracle quantity.
DECLARED_DROPS: Dict[str, str] = {
    "root_torsion_myy_lra":
        "torsion about the loads reference axis (note 24 R-7c). The axis is "
        "geometry.surfaces[].ref_axis_pct, sloads capability the original had "
        "no concept of; unset, every consumer reports about the original "
        "quarter-chord instead and this key is simply not emitted -- which is "
        "the refusal-to-assume the field was added for.",
}


def _oracle_modules() -> Tuple[str, ...]:
    """Calc modules behind the oracle page set, derived (OG-2 as amended).

    ``FOLDED_MODULES`` are contributors without a page of their own; every one
    of them today folds onto an oracle page (WINGGEOM onto Geometry, AIRLOADS /
    WINGINER onto Wing Loads, BALLOADS onto Tail Loads, WTESTIMA / WTENV onto
    Weight & Mass, MACHLIM onto Structural Speeds, SELECT onto the V-n page), so
    they are part of what the oracle GUI runs.
    """
    named = {s.module for s in wf.oracle_steps() if s.module}
    return tuple(sorted(named | set(wf.FOLDED_MODULES)))


def _outcomes(project) -> Tuple[Dict[str, str], Dict[Tuple[str, str, str], object]]:
    """``({module: "ok" | exception name}, {(module, case, key): value})``."""
    ran: Dict[str, str] = {}
    values: Dict[Tuple[str, str, str], object] = {}
    for name in _oracle_modules():
        try:
            result = registry.get(name)(project)
        except Exception as exc:  # noqa: BLE001 - the type is the assertion
            ran[name] = type(exc).__name__
            continue
        ran[name] = "ok"
        for condition in result.conditions:
            for value in condition.values:
                values.setdefault((name, condition.title, value.key), value.value)
    return ran, values


def _load(example: str):
    return io.load_project(os.path.join(_EXAMPLES, example))


def _both(example: str):
    project = _load(example)
    return _outcomes(project), _outcomes(reduce_to_oracle_inputs(project))


# --- G5, part 1: the reduced project runs ------------------------------------ #


@pytest.mark.parametrize("example", EXACT + tuple(RUNS_ONLY))
def test_the_reduction_changes_nothing_about_what_runs(example):
    """Every oracle-page module succeeds, or refuses, exactly as it did.

    ``one_engine_out`` refusing on a single-engine airplane is the correct
    behaviour and not a gap (OG-12), so the assertion is equality of outcome
    rather than universal success — that way an oracle module that starts
    refusing *because* of the reduction cannot hide behind an exemption.
    """
    (full_ran, _), (reduced_ran, _) = _both(example)
    changed = {m: (full_ran[m], reduced_ran[m])
               for m in full_ran if full_ran[m] != reduced_ran[m]}
    assert not changed, (
        f"{example}: the oracle input set is not sufficient — these modules "
        f"behave differently on it (full -> reduced): {changed}. Either a field "
        "they need is misclassified in sloads/field_registry.py, or it is really "
        "SLOADS and the module has no business on an oracle page."
    )


# --- G5, part 2: the numbers are the same ------------------------------------ #


@pytest.mark.parametrize("example", EXACT)
def test_the_reduced_project_reproduces_every_number(example):
    """±0.1 % on every load value, which is what carries the Appendix A oracles.

    Every ga6-based oracle test asserts against the *full* project; if the
    reduced one agrees with it everywhere, each of those oracles holds on the
    reduced set too, without this file restating a single printed figure.
    """
    (_, full), (_, reduced) = _both(example)
    off = []
    for key in sorted(set(full) & set(reduced)):
        a, b = full[key], reduced[key]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not math.isclose(a, b, rel_tol=TOL, abs_tol=1e-9):
                off.append(f"{key}: {a!r} -> {b!r}")
        elif a != b:
            off.append(f"{key}: {a!r} -> {b!r}")
    assert not off, (
        f"{example}: {len(off)} value(s) move when the sloads-only fields are "
        "dropped, so one of them is really an input of a .BAS program:\n  "
        + "\n  ".join(off[:20])
    )


@pytest.mark.parametrize("example", EXACT)
def test_what_the_reduction_drops_is_declared(example):
    """A quantity that disappears must be sloads-only output, said out loud.

    Silence here is how an oracle quantity would go missing without a single
    number moving: nothing compares values that are not there.
    """
    (_, full), (_, reduced) = _both(example)
    dropped = {key[2] for key in set(full) - set(reduced)}
    assert not (dropped - set(DECLARED_DROPS)), sorted(dropped - set(DECLARED_DROPS))
    assert not set(reduced) - set(full), sorted(set(reduced) - set(full))[:10]


# --- G5, part 3: Appendix A, restated on the reduced project ----------------- #


def _value(module, case_contains, key):
    project = reduce_to_oracle_inputs(_load("ga6_normal.project.json"))
    for condition in registry.get(module)(project).conditions:
        if case_contains in condition.title:
            for value in condition.values:
                if value.key == key:
                    return value.value
    raise KeyError(f"{module}/{case_contains}/{key}")


def test_appendix_a_inertias_hold_on_the_reduced_project():
    """Appendix A p136, slug-ft²: IXX 1201.527, IYY 2058.209, IZZ 3022.766.

    The figure that caught the registry's largest error: with the weight
    database's per-item inertias treated as sloads capability and dropped, IXX
    came out 66.7 — the parallel-axis transfer of a centreline point-mass
    database, which is not what WTONECG prints.
    """
    assert math.isclose(_value("weight_onecg", "Weight, centre of gravity", "ixx"),
                        1201.527, rel_tol=TOL)
    assert math.isclose(_value("weight_onecg", "Weight, centre of gravity", "iyy"),
                        2058.209, rel_tol=TOL)
    assert math.isclose(_value("weight_onecg", "Weight, centre of gravity", "izz"),
                        3022.766, rel_tol=TOL)


def test_appendix_a_wing_planform_holds_on_the_reduced_project():
    """Appendix A p141 wing: AREA/SIDE 13257, MAC 69.246, XLE(MAC) 63.641.

    The registry said the oracle GUI would offer the parametric scalars and
    never the edge polylines; ``SurfaceInput`` says the polylines are entered
    "exactly as the original program prompts for them", and this is the figure
    that settles which is right.
    """
    assert math.isclose(_value("wing_geometry", "wing", "area_per_side"), 13257, rel_tol=TOL)
    assert math.isclose(_value("wing_geometry", "wing", "mac"), 69.246, rel_tol=TOL)
    assert math.isclose(_value("wing_geometry", "wing", "xle_mac_station_of_mac_le"),
                        63.641, rel_tol=TOL)


def test_appendix_a_aileron_stays_single_sided_on_the_reduced_project():
    """Appendix A p142 aileron: AREA/SIDE 932, MAC 11.645 (±2 %, as p142 is not
    tabulated to the element count). Dropping ``symmetric`` mirrored the aileron
    and doubled both, which is why the field is ``supplied``."""
    assert math.isclose(_value("wing_geometry", "aileron", "area_per_side"), 932, rel_tol=2e-2)
    assert math.isclose(_value("wing_geometry", "aileron", "mac"), 11.645, rel_tol=2e-2)


def test_appendix_a_ballast_holds_on_the_reduced_project():
    """Appendix A: aft-gross ballast 78 lb (`PROGRAM_SPEC.md`, WTENV Validation).

    WTENV's ballast exists only if the weight database says which rows are
    discretionary, so this is the figure behind ``weight.items[].kind`` being an
    input of WTONECG.BAS rather than sloads' mass-model tagging: without it every
    loading weighs the full 3400 lb and the ballast falls to zero.
    """
    assert math.isclose(_value("weight_envelope", "Ballast", "aft_gross_ballast_weight"),
                        78.0, rel_tol=TOL)


# --- the reduction is a reduction, and the example set stays honest ---------- #


def test_the_reduction_actually_removes_fields():
    """Otherwise every assertion above passes on a no-op."""
    project = _load("ga6_normal.project.json")
    assert reduce_to_oracle_inputs(project) != project
    omitted = schema_paths() - oracle_input_paths()
    assert len(omitted) > 50, f"only {len(omitted)} fields omitted — that is not a reduction"


def test_the_supplied_set_stays_small_against_the_asked_set():
    """``supplied`` is the escape hatch in this gate: anything can be made to
    pass by marking it supplied. It buys nothing the user sees — a supplied field
    is one the second front-end writes on its own — so it stays a rounding error
    beside the fields actually asked for, or the reduction is being faked."""
    assert len(supplied_paths()) < 0.1 * len(original_paths())


def test_every_shipped_example_is_classified():
    """A new example must be declared exact or excused, never silently skipped."""
    shipped = {os.path.basename(p)
               for p in glob.glob(os.path.join(_EXAMPLES, "*.project.json"))}
    covered = set(EXACT) | set(RUNS_ONLY)
    assert shipped == covered, (
        f"undeclared: {sorted(shipped - covered)}; stale: {sorted(covered - shipped)}"
    )


def test_every_excused_example_states_a_reason():
    for example, reason in RUNS_ONLY.items():
        assert len(reason) > 40, f"{example}: excused with no real reason"
    for key, reason in DECLARED_DROPS.items():
        assert len(reason) > 40, f"{key}: dropped with no real reason"


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
