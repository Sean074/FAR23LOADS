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
  produced OG-2's amendment (:func:`sloads.workflow.oracle_steps`). G5 itself
  lives in ``tests/test_oracle_inputs.py``; what stays here is the shape of the
  ``supplied`` column it needed — a `SLOADS` field the oracle input set cannot
  do without — because a mark that can be handed out freely would let any G5 failure be
  silenced by marking the offending field.
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
    LIST_MARKER,
    NON_INPUT,
    REGISTRY,
    SENTINEL_DEFAULTS,
    SLICE_ALIASES,
    Origin,
    field_at,
    omitted_records,
    oracle_input_paths,
    original_paths,
    paths_under,
    quantities,
    record_of,
    schema_paths,
    slice_of,
    stale,
    structurally_required,
    untagged,
)
from sloads import field_registry as fr
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


def test_control_surface_planform_geometry_renders_on_the_geometry_page():
    """C210-37 / C210-44 (#99, owner directives): aileron/flap planform geometry
    and the engine layout are configuration, entered beside the empennage forms.
    The rows keep their slices (no schema move); the placement is the page tag,
    so this is the drift guard for the decision."""
    from sloads.field_registry import entry

    on_geometry = [
        "aileron_loads.area_aft_hinge_sqft", "aileron_loads.area_fwd_hinge_sqft",
        "aileron_loads.up_deflection_deg", "aileron_loads.down_deflection_deg",
        "flap_loads.flap_area_one_side_sqft", "flap_loads.flap_chord_ratio",
        "flap_loads.flap_deflection_deg", "engine_layout",
    ]
    wrong = {p: entry(p).page for p in on_geometry
             if entry(p).page != "configuration_layout"}
    assert not wrong, f"planform/configuration rows off the Geometry page: {wrong}"
    # The per-page condition inputs stay where they are entered.
    assert entry("flap_loads.gust_load_factor").page == "flap_loads"


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


# --- the `supplied` column: what the oracle input set cannot do without ------ #


def test_a_supplied_field_is_never_original():
    """The two columns answer different questions and must not blur. ``ORIGINAL``
    means the user is asked; ``supplied`` means the front-end fills it in. A row
    claiming both is claiming the oracle GUI asks for something it also invents."""
    both = sorted(e.path for e in REGISTRY if e.supplied and e.origin is Origin.ORIGINAL)
    assert not both, both


def test_the_supplied_mark_is_earned():
    """`SUPPLIED_RULE`: structurally required, or shown to matter by G5.

    Without this the mark is a wildcard — every G5 failure could be closed by
    marking the field that caused it, which is the opposite of what the gate is
    for. So each mark points at one of the two admissible reasons.
    """
    required = structurally_required()
    unearned = sorted(
        e.path for e in REGISTRY
        if e.supplied and e.path not in required and "G5" not in e.basis
    )
    assert not unearned, (
        "these rows are marked supplied on neither ground in SUPPLIED_RULE — "
        "they have a declared default, and the basis does not cite the G5 "
        f"result that shows omitting them moves a number: {unearned}"
    )


def test_a_list_row_selector_is_always_asked():
    """#98 (C210-46): a page can resolve a *scalar* surface selector
    positionally -- the flap page means the flap -- but it cannot resolve which
    surface each **row** of a list belongs to, so filtering a row's selector
    hardcodes it: every tab silently became an h-tail tab, and a rudder tab
    could not be entered at all. Detected structurally (a ``name``/``surface``
    leaf on a list record the GUI builds), so the next list with a selector
    cannot ship with it hidden.
    """
    keep = oracle_input_paths()
    omitted = omitted_records()
    hidden = sorted(
        e.path for e in REGISTRY
        if LIST_MARKER in e.path
        and e.path.rsplit(".", 1)[-1] in ("name", "surface")
        and record_of(e.path) not in omitted
        and e.path not in keep
    )
    assert not hidden, (
        "these row selectors are filtered off their oracle page, so every row "
        "is silently pinned to the dataclass default:\n  " + "\n  ".join(hidden)
    )


def test_a_sentinel_default_field_is_always_asked():
    """#98 (C210-49): a field whose declared default is "not stated" -- refused,
    assumed-with-a-note, or a free body left open -- cannot be left at it, so
    filtering it off the page removes a deliverable with nothing said: an
    oracle-built project could not export ground cases. The register of such
    fields is ``SENTINEL_DEFAULTS``; each entry cites the consumer that treats
    the default as a sentinel, and every one must be asked.
    """
    keep = oracle_input_paths()
    omitted = omitted_records()
    for path, why in SENTINEL_DEFAULTS.items():
        assert path in BY_PATH, f"SENTINEL_DEFAULTS names an unregistered path: {path}"
        assert why, path
    hidden = sorted(p for p in SENTINEL_DEFAULTS
                    if p not in keep and record_of(p) not in omitted)
    assert not hidden, (
        "these fields have a sentinel default (SENTINEL_DEFAULTS says which "
        "consumer refuses it) yet are filtered off their oracle page:\n  "
        + "\n  ".join(hidden)
    )


def test_a_structurally_required_field_is_never_omitted():
    """A field with no declared default cannot be left out — there is nothing to
    leave it *at*. Either the oracle GUI supplies it, or the original asked for
    it, or the whole record is one the second front-end never builds.

    Read off ``dataclasses.fields``, so it is a fact rather than a judgement:
    the day someone gives ``SurfaceInput.leading_edge`` a ``default_factory``,
    the wing quietly becomes omittable and this is what notices.
    """
    omitted = omitted_records()
    stranded = sorted(
        p for p in structurally_required()
        if p not in oracle_input_paths() and record_of(p) not in omitted
    )
    assert not stranded, (
        "these fields have no default, so the oracle GUI cannot omit them, yet "
        "they are neither ORIGINAL nor supplied and their record is one it does "
        "build:\n  " + "\n  ".join(stranded)
    )


def test_the_inverse_walk_finds_every_field():
    """:func:`field_at` is how `structurally_required` reads defaults; if it
    silently returned ``None`` the guard above would pass on an empty set."""
    lost = sorted(p for p in schema_paths() if field_at(p) is None)
    assert not lost, lost


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


def test_governs_is_only_claimed_by_copies():
    """``governs`` answers "does the calc honour *this* copy" (#36), so it is
    meaningless on an owner row — an owner always governs — and a True there
    would read as though the owner were itself a copy of something."""
    stray = [e.path for e in REGISTRY if e.governs and e.is_owner]
    assert not stray, (
        "these owner rows claim `governs`, which only a copy can: " + ", ".join(stray))


def test_every_copy_declares_whether_it_governs():
    """The flag is a claim about the *calc*, checked against it by hand when the
    row is written, so this only pins that a copy carries a deliberate answer:
    a display-only copy is disabled in the GUI and an override stays editable,
    and defaulting silently to one of those is how the wrong one ships."""
    for e in REGISTRY:
        if e.is_owner or e.owner_is_external or not e.owner_path:
            continue
        assert isinstance(e.governs, bool), e.path
        assert e.derived_from.strip(), e.path


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
    regression fixture for the registry that replaced that hand sweep.
    N1 instance 2 (the v-tail's ``airplane_length_in``) is no longer a
    duplicate at all: v55 (#52) left the quantity one field, which
    :func:`test_no_quantity_regains_a_second_field` holds."""
    for path in (
        "geometry.empennage.vtail.gross_weight_lb",     # N1 instance 1
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



# --- note 33: the consolidated quantities stay consolidated ------------------- #

#: The quantities that still hold more than one field after note 33's
#: consolidation, and **why each is allowed to**. Anything else appearing here is
#: a duplicate re-entering the schema, which is what gate DG-2 exists to catch.
#: Deliberately a literal, not a count: a count would go green if one duplicate
#: were removed while another was added.
STILL_DUPLICATED = {
    # Class B (note 33 §1, DS-6) -- a genuine override of its owner.
    "max take-off weight",
    "wing reference area",
    # Class C (DS-7) -- "airplane length" and "shoulder altitude" were here
    # until the v55 hop (#52, note 33 §8) left each one field. DG-2 shrunk.
    # Note 36 (OV-1, #97) -- collapsed overrides: the copy stays a field
    # because the oracle deck can legitimately clamp/score at a different
    # value, but blank now derives from the owner and a typed disagreement is
    # marked (the C210-15 ruling for the stall CLs, C210-38 for the aileron).
    "clean positive stall CL",
    "clean negative stall CL",
    "flapped positive stall CL",
    "full-down aileron deflection",
}


def test_no_quantity_regains_a_second_field():
    """Gate DG-2. Note 33 (DS-1) removed ten fields that were copies of a
    quantity's owner: the wing scalars off ``flight_loads``, the wing plane off
    ``wing_mass``, and the gear block plus the wing area off ``landing``. Before
    it, ten quantities had two or more independently editable fields; after it,
    four do, and each of those four is named above with its reason.
    """
    duplicated = {name for name, rows in quantities().items() if len(rows) > 1}
    assert duplicated == STILL_DUPLICATED, (
        "the set of multi-field quantities changed. Added means a copy came back "
        "(resolve it where it is used, as note 33 did); removed means a row was "
        f"consolidated and this literal should shrink. Now: {sorted(duplicated)}"
    )


def test_the_consolidated_quantities_have_exactly_one_field():
    """Gate DG-5, stated positively: each consolidated quantity is entered once.

    The GUI half of DG-5 follows from this without a second assertion — both
    front-ends build their widgets from this registry, so a quantity with one
    field cannot render a second editable copy of itself on any page.
    """
    for name in ("wing MAC", "wing dihedral", "wing root waterline", "gear tread",
                 "main-gear static axle", "nose-gear static axle",
                 "wing aerodynamic centre station", "wing drag waterline"):
        rows = quantities().get(name, [])
        editable = [e for e in rows if not e.owner_is_external]
        assert len(editable) <= 1, (
            f"{name!r} is entered in more than one place again: "
            f"{[e.path for e in editable]}"
        )


# --------------------------------------------------------------------------- #
# #95: display groups and the fuselage-length summary
# --------------------------------------------------------------------------- #
def test_every_display_group_path_is_registered_and_rendered():
    """A DISPLAY_GROUPS path that is not a rendered oracle input is a section
    title for a widget that never appears -- and paths sharing one (page,
    record) must share one title, or page_groups' split becomes ambiguous."""
    keep = fr.oracle_input_paths()
    titles: dict = {}
    for path, title in fr.DISPLAY_GROUPS.items():
        entry = fr.entry(path)
        assert entry is not None, f"{path}: DISPLAY_GROUPS names an unregistered path"
        assert path in keep, f"{path}: titled but filtered off its page"
        assert title.strip(), f"{path}: blank display-group title"
        key = (entry.page, fr.record_of(path))
        assert titles.setdefault(key, title) == title, (
            f"{key}: two display-group titles on one page/record -- "
            f"{titles[key]!r} vs {title!r}")


def test_the_moved_select_rows_render_with_their_quantity():
    """C210-6/22: the wing-aero fields that live on the h-tail record render on
    the Aerodynamic Data page, and the SELECT trio on the pages their
    quantities belong to -- placement is the registry's, so this is the drift
    guard on the placement itself."""
    assert fr.entry("geometry.empennage.htail.wing_lift_slope_per_rad").page == "aero_coefficients"
    assert fr.entry("geometry.empennage.htail.aspect_ratio_wing").page == "aero_coefficients"
    assert fr.entry("select_input.basic_airfoil_cm").page == "aero_coefficients"
    assert fr.entry("select_input.full_down_aileron_deg").page == "aileron_loads"
    assert fr.entry("select_input.wing_weight_lb").page == "weight_mass"


def test_the_fuselage_length_summary_is_display_only_once_an_outline_exists():
    """C210-2: sync_geometry_derived overwrites the scalar on every run, so the
    widget renders disabled exactly when the outline it summarises exists --
    and stays live on a project with no outline yet."""
    entry = fr.entry("geometry.parametric.fuselage_length")
    assert entry.owner_is_external and not entry.governs and entry.display_only
    assert "geometry.parametric.fuselage_length" not in fr.COLLAPSED_OVERRIDES, (
        "a derived summary is not an override -- the OV-1 contract does not apply")
    import os

    from sloads import io as sloads_io

    ga = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "examples", "ga6_normal.project.json")
    project = sloads_io.load_project(ga)
    fus = project.geometry.fuselage
    length = fr.external_value("geometry.parametric.fuselage_length", project)
    assert length == max(s.x for s in fus.sections) - min(s.x for s in fus.sections)
    project.geometry.fuselage = None
    assert fr.external_value("geometry.parametric.fuselage_length", project) is None


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
