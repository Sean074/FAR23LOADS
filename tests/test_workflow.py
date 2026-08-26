"""Workflow metadata: the Define→Analyze→Review→Export step graph.

Pure-data sanity checks on :mod:`sloads.workflow` -- the single source of truth
that drives the GUI navigation and the Home dashboard's completeness panel. These
guard against the kind of drift that froze the old Home page at "Phase 0": every
real suite module must have a step, phases/keys must stay well-formed, and the
``requires``/``produces`` predicates must read a Project correctly.
"""

import ast
import dataclasses
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import Project, io, registry  # noqa: E402
from sloads import field_registry as fr  # noqa: E402
from sloads import workflow as wf  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


def test_keys_unique_and_phases_valid():
    keys = [s.key for s in wf.STEPS]
    assert len(keys) == len(set(keys)), "duplicate step keys"
    for s in wf.STEPS:
        assert s.phase in wf.PHASES, f"{s.key} has unknown phase {s.phase!r}"
        assert s.title.strip(), f"{s.key} has no title"


def test_by_phase_partitions_all_steps():
    grouped = wf.by_phase()
    assert list(grouped) == list(wf.PHASES)
    assert sum(len(v) for v in grouped.values()) == len(wf.STEPS)


def test_every_registered_module_has_a_step():
    """Each registered calc module must be represented by a workflow step (via the
    step's ``module`` field), so the nav/dashboard can never silently omit a
    shipped program -- the bug that froze the old Home page at "Phase 0"."""
    step_modules = {s.module for s in wf.STEPS if s.module is not None}
    for name in registry.available():
        if name in wf.FOLDED_MODULES:
            continue
        assert name in step_modules, f"registered module {name!r} has no workflow step"


def test_step_modules_are_registered():
    """Conversely, every step that claims a module must name a real one."""
    available = set(registry.available())
    for s in wf.STEPS:
        if s.module is not None:
            assert s.module in available, f"{s.key} names unknown module {s.module!r}"


def test_every_folded_module_names_the_step_that_runs_it():
    """``FOLDED_MODULES`` maps a contributor to its owning step, and both halves
    have to be real: an unknown step key or an unregistered module would give
    ``step_modules`` a program no page can run (design note 32, OG-E)."""
    available = set(registry.available())
    for name, owner in wf.FOLDED_MODULES.items():
        assert name in available, f"folded module {name!r} is not registered"
        assert owner in wf.BY_KEY, f"folded module {name!r} names unknown step {owner!r}"
        assert wf.BY_KEY[owner].module != name, (
            f"{name!r} is both step {owner!r}'s primary module and folded into it")


def test_step_modules_accounts_for_every_registered_module_exactly_once():
    """The partition the results renderer depends on: every shipped program runs
    on exactly one page, so no module is shown twice and none is invisible."""
    seen = [name for s in wf.STEPS for name in wf.step_modules(s.key)]
    assert len(seen) == len(set(seen)), "a module runs on more than one step"
    assert set(seen) == set(registry.available())


def test_step_modules_puts_the_primary_first():
    """Order is the contract: the step's own ``module`` leads, contributors follow."""
    for s in wf.STEPS:
        names = wf.step_modules(s.key)
        if s.module is None:
            assert all(wf.FOLDED_MODULES[n] == s.key for n in names)
        else:
            assert names[0] == s.module


def test_produces_dotted_path_resolves():
    """A dotted ``produces`` path must be structurally valid against a Project."""
    empty = Project(name="")
    for s in wf.STEPS:
        if s.produces is not None:
            # Must not raise and must read as absent on an empty project.
            assert wf.has(empty, s.produces) is False


def test_requirements_and_production_on_example():
    proj = io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))
    # The example has the V-n environment, so the Define backbone is ready.
    fe = wf.BY_KEY["flight_envelope"]
    assert wf.requirements_met(proj, fe)
    assert wf.is_produced(proj, fe)
    # A step needing a slice the example omits is reported as not-ready.
    oeo = wf.BY_KEY["one_engine_out"]
    if not wf.has(proj, "mass"):
        assert "mass" in wf.missing_requirements(proj, oeo)


def test_empty_project_blocks_dependent_steps():
    empty = Project(name="")
    wing = wf.BY_KEY["wing_loads"]
    assert not wf.requirements_met(empty, wing)
    assert set(wf.missing_requirements(empty, wing)) == {"geometry"}


# --------------------------------------------------------------------------- #
# The requires DAG is closed and the self-entered split reads it (#45, CR-D-3)
# --------------------------------------------------------------------------- #
def test_every_requires_is_produced_or_self_entered():
    """DAG-completeness: every ``requires`` is some step's ``produces`` or in
    some step's ``edits`` — a required slice nobody makes and nobody's form
    enters is a step no fresh project can ever unblock, and it is exactly how
    two oracle pages came to send the user upstream for their own inputs."""
    made = {s.produces for s in wf.STEPS if s.produces}
    entered = {e for s in wf.STEPS for e in s.edits}
    for s in wf.STEPS:
        for r in s.requires:
            assert r in made or r in entered, (
                f"{s.key} requires {r!r}, which no step produces and no "
                f"step's own form is declared to enter (WorkflowStep.edits)")


def test_edits_name_slices_a_pages_form_really_enters():
    """The rot companion (the #43/#51 allowlist lesson): each declared edit
    must be a slice the field registry attributes to that very page — or one
    of the two Step-G6 proxy *properties* over ``geometry.empennage``, accepted
    only while they are still properties and the proxied slice is the page's
    own. When the proxies are retired this test fails and the two Geometry
    entries come out with them."""
    from sloads import field_registry as fr
    from sloads.models import Project as ProjectCls

    by_page: dict = {}
    for row in fr.REGISTRY:
        by_page.setdefault(row.page, set()).add(fr.slice_of(row.path))

    proxies = {"tail_loads": "geometry", "vtail_loads": "geometry"}
    for s in wf.STEPS:
        for e in s.edits:
            if e in by_page.get(s.key, set()):
                continue
            assert e in proxies, (
                f"{s.key}.edits declares {e!r}, but the field registry puts "
                f"no {e!r} field on that page")
            assert isinstance(getattr(ProjectCls, e, None), property), (
                f"{e!r} is no longer a Project property proxy — drop it from "
                f"{s.key}.edits (its real slice is {proxies[e]!r})")
            assert proxies[e] in by_page.get(s.key, set()), (
                f"{s.key} does not enter {proxies[e]!r}, so the {e!r} proxy "
                f"cannot be self-entered there")


def test_self_entered_split_on_a_fresh_project():
    """The measured #45 defect, at the predicate level: on a fresh project the
    two self-sufficient pages are missing only slices their own form enters —
    nothing upstream — while a genuinely dependent page still blocks."""
    fresh = Project(name="")
    for key, own in (("weight_mass", ["weight"]), ("engine_mount", ["engines"])):
        step = wf.BY_KEY[key]
        assert wf.missing_upstream(fresh, step) == [], key
        assert wf.missing_self_entered(fresh, step) == own, key
    speeds = wf.BY_KEY["structural_speeds"]
    assert wf.missing_upstream(fresh, speeds) == ["aero_coeffs"]
    assert wf.missing_self_entered(fresh, speeds) == []
    # The split partitions missing_requirements exactly, for every step.
    for s in wf.STEPS:
        assert sorted(wf.missing_upstream(fresh, s) + wf.missing_self_entered(fresh, s)) \
            == sorted(wf.missing_requirements(fresh, s)), s.key


def test_bas_is_a_program_name_or_none():
    """``bas`` answers "which original McMaster program is behind this step?" --
    so a modern page must say ``None``, not a placeholder (design note 32 OG-3).

    ``tail_span_loads`` and ``balanced_cases`` both carried ``bas="—"``. An
    em dash is truthy, so the natural "original programs only" filter
    ``[s for s in STEPS if s.bas]`` silently claimed two sloads-only pages, and
    the dashboard rendered a dangling " · —" beside them. Any non-program
    sentinel reintroduces both, so the shape is asserted rather than the two
    known values.
    """
    for s in wf.STEPS:
        if s.bas is None:
            continue
        assert re.fullmatch(r"[A-Z][A-Z0-9]*(\+[A-Z][A-Z0-9]*)*", s.bas), (
            f"{s.key}: bas={s.bas!r} is not a '+'-joined program name; a step "
            f"with no original program must use bas=None"
        )


# --------------------------------------------------------------------------- #
# Page-order dependencies (#69, PB-15/PB-19)
# --------------------------------------------------------------------------- #
#: ``Project`` attributes that are not analysis slices -- provenance, the unit
#: system, the SF table, the results bundle. Reading one of these says nothing
#: about page order.
_NOT_A_SLICE = {
    "schema_version", "name", "description", "engineer", "checked_by",
    "approved_by", "date", "revision", "unit_system", "include_far25",
    "safety_factors", "loads",
}

#: ``Project.engine`` is a convenience property over ``Project.engines``; the
#: sweep would not otherwise see the Flap page's own dependency, which is the
#: instance #69 was filed on.
_SLICE_ALIASES = {"engine": "engines"}


def _slice_reads(key):
    """Every ``Project`` slice the modules behind step ``key`` read, by AST.

    Direct ``project.<slice>`` attribute access in the step's own module and in
    the modules folded onto it. Reads reached through a helper in *another*
    module are not seen -- ``design_speed_values`` is the live example -- so
    this under-reports rather than over-reports, which is the safe direction
    for a guard whose failure mode is a demand to declare something.
    """
    slices = {f.name for f in dataclasses.fields(Project)} - _NOT_A_SLICE
    found = set()
    for module in wf.step_modules(key):
        path = os.path.join(os.path.dirname(_EXAMPLES), "sloads", "modules", module + ".py")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == "project"):
                name = _SLICE_ALIASES.get(node.attr, node.attr)
                if name in slices:
                    found.add(name)
    return found


def test_every_page_order_dependency_is_declared():
    """A page whose numbers read a slice entered on a *later* page declares it.

    The #69 defect in one assertion. The Flap page computes its FAR 23.457(b)
    slipstream case from an engine record entered two pages later; before the
    engine page exists the case does not either, and the flap is sized ~19 %
    low on the C210 with the page showing a complete-looking answer. The
    weight estimate correlates against the engine list's power rather than the
    horsepower typed beside it. Neither page said so.

    ``requires`` is not the remedy -- it blocks, and both calcs run correctly
    with no engine at all -- so the dependency is declared in ``reads`` and
    *stated* by ``app_shell.components.render_page_order_reads``. This is the
    guard that a new one cannot be added silently: a module that starts reading
    a later page's slice fails here until the step says so.

    Only *later* pages are flagged. A slice entered on this page or an earlier
    one has no order problem to state.
    """
    order = {s.key: i for i, s in enumerate(wf.STEPS)}
    undeclared = {}
    for step in wf.STEPS:
        if not step.module:
            continue
        declared = set(step.requires) | set(step.edits) | set(step.reads)
        if step.produces:
            declared.add(step.produces.split(".", 1)[0])
        for name in sorted(_slice_reads(step.key) - declared):
            entered_on = fr.entering_step(name)
            if entered_on and order.get(entered_on, -1) > order[step.key]:
                undeclared.setdefault(step.key, []).append(f"{name} (entered on {entered_on})")
    assert not undeclared, (
        "these steps read a slice entered on a later page without declaring it "
        "-- add it to the step's `reads` so the page states the dependency "
        f"instead of silently changing its numbers later (#69): {undeclared}")


def test_declared_reads_are_real_slices_the_step_really_reads():
    """The other direction: a stale ``reads`` entry states a dependency that no
    longer exists, which is a caption telling the user to go fill a page for
    nothing. Kept honest against the same sweep."""
    for step in wf.STEPS:
        for name in step.reads:
            assert name in _slice_reads(step.key), (
                f"{step.key} declares reads={name!r} but no module behind it "
                "reads that slice any more -- drop it")
            assert name not in step.requires and name not in step.edits, (
                f"{step.key}: {name!r} is both `reads` and gated/entered here; "
                "`reads` is for the dependencies those two do not cover")


def test_later_page_reads_resolves_against_a_project():
    """The predicate the GUI renders from: each declared read comes back with the
    page that enters it and whether the project carries it yet."""
    project = io.load_project(os.path.join(_EXAMPLES, "ga6_normal.project.json"))
    rows = wf.later_page_reads(project, wf.BY_KEY["flap_loads"])
    assert [r.slice_name for r in rows] == ["engines"]
    assert rows[0].entered_on == "engine_mount"
    assert rows[0].present is True

    stripped = dataclasses.replace(project, engines=[])
    assert wf.later_page_reads(stripped, wf.BY_KEY["flap_loads"])[0].present is False
    assert wf.later_page_reads(project, wf.BY_KEY["aileron_loads"]) == []
