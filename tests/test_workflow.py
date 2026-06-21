"""Workflow metadata: the Define→Analyze→Review→Export step graph.

Pure-data sanity checks on :mod:`farloads.workflow` -- the single source of truth
that drives the GUI navigation and the Home dashboard's completeness panel. These
guard against the kind of drift that froze the old Home page at "Phase 0": every
real suite module must have a step, phases/keys must stay well-formed, and the
``requires``/``produces`` predicates must read a Project correctly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, io, registry  # noqa: E402
from farloads import workflow as wf  # noqa: E402

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
    net = wf.BY_KEY["net_wing_loads"]
    assert not wf.requirements_met(empty, net)
    assert set(wf.missing_requirements(empty, net)) == {"geometry", "aero"}
