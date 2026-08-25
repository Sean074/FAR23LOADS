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


# --------------------------------------------------------------------------- #
# Normalized input slices (#81, C210-23): fields that fill each other in, which
# ``__post_init__`` alone could only do for a slice built in one go.
# --------------------------------------------------------------------------- #
def _blank_set(name="CRUISE", **kw):
    from sloads.models import AeroCoeffSet
    zero = (0.0,) * 5
    return AeroCoeffSet(name=name, lift=zero, drag=zero, moment=zero, **kw)


def _live_slice():
    """The aero slice as the oracle GUI builds it: blank sets first, CLmax after.

    Not a contrived state -- it is the only order that GUI can produce, because
    it writes one field per widget and never re-runs the constructor.
    """
    from sloads.models import AeroCoefficientsInput

    aero = AeroCoefficientsInput(cruise=_blank_set())
    aero.clmax_clean, aero.clmax_clean_neg, aero.clmax_flap = 1.4068, -0.59, 1.5857
    return aero


def test_the_stall_fill_is_bypassed_by_field_by_field_assignment():
    """The defect itself, pinned: assignment order decides whether the fill ran."""
    from sloads.models import AeroCoefficientsInput

    assert _live_slice().cruise.stall_cl == 0.0
    built = AeroCoefficientsInput(cruise=_blank_set(), clmax_clean=1.4068,
                                  clmax_clean_neg=-0.59, clmax_flap=1.5857)
    assert built.cruise.stall_cl == 1.4068


def test_refresh_derived_normalizes_the_live_slice_and_is_idempotent():
    """The one call the oracle form already makes after every persist closes it."""
    project = Project(name="live", aero_coeffs=_live_slice())
    assert refresh_derived(project) == ["aero_coeffs"]
    assert project.aero_coeffs.cruise.stall_cl == 1.4068
    assert project.aero_coeffs.cruise.neg_stall_cl == -0.59
    # Idempotent by value -- a render pass may call it without dirtying a project.
    assert refresh_derived(project) == []


def test_normalizing_never_overwrites_an_authored_value():
    """Fill-if-missing, both directions. ga6 authors clmax_clean 1.4068 *and* a
    per-config stall_cl of 1.41 (the 0.9 stall-margin factor) -- they legitimately
    differ, and a normalizer that reconciled them would move VS on every render."""
    from sloads.models import AeroCoefficientsInput

    aero = AeroCoefficientsInput(cruise=_blank_set(stall_cl=1.41, neg_stall_cl=-0.6),
                                 clmax_clean=1.4068, clmax_clean_neg=-0.59)
    project = Project(name="authored", aero_coeffs=aero)
    assert refresh_derived(project) == []
    assert aero.cruise.stall_cl == 1.41 and aero.clmax_clean == 1.4068


def test_normalized_slices_are_input_slices_not_result_slices():
    """The distinction the two tables draw: ``mass`` is a result the project can
    rebuild, ``aero_coeffs`` is authored input made self-consistent. Mixing them
    would put an input slice under the G5 reduction's "drop and re-derive"."""
    from sloads.derived import NORMALIZED_SLICES

    assert set(NORMALIZED_SLICES) & set(RESULT_SLICES) == set()
    assert "aero_coeffs" in NORMALIZED_SLICES


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
