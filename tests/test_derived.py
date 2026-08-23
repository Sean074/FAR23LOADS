"""``sloads.derived`` -- the derived slices have one owner and stay current (#62, PB-1).

``Project.mass`` is WTONECG over ``weight.items``; storing it is a convenience
for its readers, not a second fact. These guards keep it that way: every
shipped example stores exactly what it derives (two had drifted by an ulp
under a changed summation before this file existed), the table names only
result slices the registry already excludes from the input set, and the
refresher is idempotent by value -- which is what lets the oracle form call it
on every render without dirtying a project it only visited.
"""

from __future__ import annotations

import glob
import os

import pytest

from sloads import io
from sloads.derived import DERIVED_SLICES, refresh_derived
from sloads.field_registry import RESULT_SLICES
from sloads.models import Project
from sloads.modules.weight_onecg import build_mass, refresh_mass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))


@pytest.mark.parametrize("path", _EXAMPLES, ids=os.path.basename)
def test_every_example_stores_the_mass_it_derives(path):
    """Bit-identical, not close: a stored slice an ulp off its derivation is a
    second source of the same fact, and gate G5 compares at exact equality."""
    project = io.load_project(path)
    assert project.mass == build_mass(project), os.path.basename(path)
    assert refresh_derived(project) == []


def test_derived_slices_are_result_slices():
    assert set(DERIVED_SLICES) <= set(RESULT_SLICES)
    assert "mass" in DERIVED_SLICES


def test_refresh_mass_derives_clears_and_is_idempotent():
    project = io.load_project(_EXAMPLES[0])
    items = project.weight.items
    project.mass = None
    assert refresh_mass(project) is True and project.mass == build_mass(project)
    assert refresh_mass(project) is False
    project.weight.items = []
    assert refresh_mass(project) is True and project.mass is None
    assert refresh_mass(project) is False
    project.weight.items = items
    assert refresh_derived(project) == ["mass"]


def test_a_blank_project_derives_nothing_and_is_not_dirtied():
    project = Project(name="blank")
    assert refresh_derived(project) == []
    assert project == Project(name="blank")


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
