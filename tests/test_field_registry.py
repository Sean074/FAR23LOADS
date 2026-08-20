"""The one field registry is total, sourced and single-owner (note 32, OG-C).

`sloads/field_registry.py` answers three questions that were three separate
discussions before OG-14 merged them: **where is this field edited**, **did the
original suite ask for it**, and **is this quantity stored twice**. A table only
settles those if it cannot quietly fall out of step with the schema, so:

* **G4 — totality, both directions.** Every input field on ``Project`` has a
  row, and no row names a field the schema no longer has. Adding a field to
  ``models/inputs.py`` fails here until it is classified, which is the point:
  ``origin`` is a decision and a new field must not inherit one silently.
* **G5's precondition.** Every ``ORIGINAL`` field is editable from a page in the
  oracle set, so "populate only the original fields" is actually reachable in
  the second GUI. This is what caught ``aero_coeffs`` having no oracle page and
  produced OG-2's amendment (:func:`sloads.workflow.oracle_steps`).
* **The duplicate-owner class** (the 2026-08-16 GUI review's N1, five instances;
  a sixth — the two ``shoulder_altitude_ft`` fields — fell out of writing the
  table). One owner per quantity, and every copy names the owner it syncs from.

Every row also carries a non-empty ``basis``. An origin claim with no citation
is the thing this project does not accept in the calc layer, and a registry of
uncited classifications would be a prose rule wearing a test's clothes.
"""

from __future__ import annotations

import dataclasses

import pytest

from sloads import workflow as wf
from sloads.field_registry import (
    BY_PATH,
    NON_INPUT,
    REGISTRY,
    SLICE_ALIASES,
    Origin,
    original_paths,
    paths_under,
    quantities,
    schema_paths,
    slice_of,
    stale,
    untagged,
)
from sloads.models import Project

# --- G4: the table covers the schema, and only the schema ------------------- #


def test_every_input_field_is_classified():
    """G4. The failure message is the worklist: it names what to classify."""
    missing = sorted(untagged())
    assert not missing, (
        f"{len(missing)} input field(s) have no field_registry row — classify "
        "each as Origin.ORIGINAL (an input of a named .BAS program) or "
        "Origin.SLOADS (capability this replication added), with a basis:\n  "
        + "\n  ".join(missing)
    )


def test_no_registry_row_outlives_its_field():
    rows = sorted(stale())
    assert not rows, (
        "field_registry rows name fields the schema no longer has — a rename "
        "or removal left them behind:\n  " + "\n  ".join(rows)
    )


def test_paths_are_unique():
    paths = [e.path for e in REGISTRY]
    dupes = sorted({p for p in paths if paths.count(p) > 1})
    assert not dupes, f"duplicate registry rows: {dupes}"


def test_the_walk_skips_result_slices_and_metadata():
    """`schema_paths` must not wander into computed output or document fields —
    an origin classification is meaningless for either, and including them would
    inflate G4 with rows nobody can decide."""
    roots = {slice_of(p) for p in schema_paths()}
    assert not (roots & set(NON_INPUT)), sorted(roots & set(NON_INPUT))
    # ...and the exclusion list itself stays honest: every name in it is really
    # a Project attribute, so a renamed slice cannot hide behind a stale entry.
    attrs = {f.name for f in dataclasses.fields(Project)}
    assert set(NON_INPUT) <= attrs, sorted(set(NON_INPUT) - attrs)


# --- every classification is sourced ---------------------------------------- #


def test_every_row_cites_a_basis():
    bare = sorted(e.path for e in REGISTRY if not e.basis.strip())
    assert not bare, (
        "these rows classify a field with no citation — name the .BAS variable, "
        "the UG/PROGRAM_SPEC line, or the sloads step that added it:\n  "
        + "\n  ".join(bare)
    )


def test_every_page_is_a_real_workflow_step():
    unknown = sorted({e.page for e in REGISTRY if e.page not in wf.BY_KEY})
    assert not unknown, f"registry rows name pages that are not workflow steps: {unknown}"


# --- G5's precondition: the original set is reachable in the oracle GUI ------ #


def test_every_original_field_is_editable_from_an_oracle_page():
    """Otherwise "populate only origin=ORIGINAL" is not a thing the second GUI
    can do, and gate G5 could never pass however the calc behaved."""
    oracle = wf.oracle_step_keys()
    stranded = sorted(p for p in original_paths() if BY_PATH[p].page not in oracle)
    assert not stranded, (
        "these ORIGINAL fields are edited only on a page outside the oracle set "
        f"({sorted(oracle)}) — either the field is really Origin.SLOADS, or the "
        "page set is wrong (see workflow.oracle_steps):\n  " + "\n  ".join(stranded)
    )


def test_the_oracle_page_set_covers_what_its_pages_require():
    """OG-2 as amended. A page set that requires a slice it cannot produce is
    the defect this rule was changed to fix; it must not come back."""
    steps = wf.oracle_steps()
    oracle = wf.oracle_step_keys()
    produced = {s.produces for s in steps if s.produces}
    for step in steps:
        for slice_name in step.requires:
            if slice_name in produced:
                continue
            fields = paths_under(slice_name)
            assert fields and all(BY_PATH[p].page in oracle for p in fields), (
                f"oracle page {step.key!r} requires {slice_name!r}, which no "
                "oracle page produces and whose fields are not all editable "
                "from one either"
            )


def test_slice_aliases_are_real_properties_over_real_paths():
    """The alias table is schema knowledge, so it rots with the schema unless
    both halves are checked: the name must still be a `Project` property, and
    the target must still have fields under it."""
    for name, target in SLICE_ALIASES.items():
        assert isinstance(getattr(Project, name, None), property), (
            f"{name!r} is no longer a Project property — the alias is stale"
        )
        assert paths_under(name), f"no registry fields under alias target {target!r}"
        assert name not in {slice_of(p) for p in schema_paths()}, (
            f"{name!r} is now a stored slice, not a property — drop the alias"
        )


def test_the_original_set_is_a_real_reduction():
    """The oracle GUI's claim is that it asks less. If ORIGINAL were nearly
    everything the second front-end would be a second full input GUI, which is
    not worth building — so the reduction is asserted, not assumed."""
    original = len(original_paths())
    total = len(schema_paths())
    assert original < total * 0.75, (
        f"{original}/{total} fields classified ORIGINAL — the oracle GUI would "
        "ask for nearly the whole schema; re-check the classification"
    )


# --- the duplicate-owner class (the review's N1) ---------------------------- #


def test_each_quantity_has_at_most_one_owning_field():
    """Exactly one owner, unless the quantity is owned *outside* the field set —
    "engine count" is `len(Project.engines)`, "engine mass" is the weight
    database. Those have no owning field, so requiring one would force an
    invented row; what is required instead is that at least one copy says so."""
    offenders = {}
    for quantity, rows in quantities().items():
        owners = [e.path for e in rows if e.is_owner]
        if len(owners) > 1:
            offenders[quantity] = f"{len(owners)} owning fields: {owners}"
        elif not owners and not any(e.owner_is_external for e in rows):
            offenders[quantity] = (
                "no owning field and no external owner declared — say which "
                "field owns it, or mark the copies EXTERNAL + <where it lives>"
            )
    assert not offenders, offenders


def test_a_declared_quantity_really_is_shared():
    """`quantity` means "more than one field holds this". A lone row with a
    quantity and no external owner is a claim of duplication with nothing to
    duplicate — usually a suspicion that belongs in `basis` until it is shown."""
    lonely = {
        name: [e.path for e in rows]
        for name, rows in quantities().items()
        if len(rows) < 2 and not any(e.owner_is_external for e in rows)
    }
    assert not lonely, (
        "these quantities are declared on exactly one field and name no external "
        f"owner — drop the column or show the second holder: {lonely}"
    )


def test_every_copy_names_an_owner_that_exists():
    """A `derived_from` is either a real registry path or an explicit EXTERNAL
    declaration. Nothing else — a free-text owner is how a registry rots into
    prose."""
    for e in REGISTRY:
        if not e.derived_from or e.owner_is_external:
            continue
        assert e.owner_path in BY_PATH, (
            f"{e.path}: derived_from {e.owner_path!r} is not a registry path; "
            f"use the owning field's path, or {'EXTERNAL'} + a description when "
            "the owner is not a field"
        )
        assert e.owner_path != e.path, f"{e.path} is declared as its own copy"


def test_a_quantity_column_without_an_owner_is_rejected():
    """A row that declares a quantity but neither owns it nor points at an owner
    is the half-filled case that would let a duplicate through."""
    orphans = sorted(
        e.path for e in REGISTRY
        if e.quantity and not e.is_owner and not e.derived_from
    )
    assert not orphans, orphans


def test_the_reviews_duplicate_instances_are_all_recorded():
    """The five instances the 2026-08-16 GUI review found by hand are the
    regression fixture for the registry that replaced that hand sweep."""
    for path in (
        "geometry.empennage.vtail.gross_weight_lb",     # N1 instance 1
        "geometry.empennage.vtail.airplane_length_in",  # N1 instance 2
        "weight.estimation.engines",                    # N1 instance 3
        "engines[].limit_load_factor",                  # N1 instance 4
        "engines[].engine_weight_lb",                   # N1 instance 5
        "engines[].engine_cg",                          # N1 instance 5
    ):
        entry = BY_PATH[path]
        assert entry.derived_from, f"{path} lost its duplicate-owner record"


# --- the shape holds --------------------------------------------------------- #


@pytest.mark.parametrize("origin", list(Origin))
def test_both_origins_are_used(origin):
    """A classification everything lands on is not a classification."""
    assert any(e.origin is origin for e in REGISTRY)


def test_slice_of_handles_list_hops():
    assert slice_of("engines[].engine_cg") == "engines"
    assert slice_of("weight.cg_cases[].loading.ballast.x") == "weight"
    assert slice_of("include_far25") == "include_far25"


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
