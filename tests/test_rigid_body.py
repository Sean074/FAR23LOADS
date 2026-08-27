"""The rigid-body relief field and the inertia tensor (plan 13 B8a-2, L-2/L-3).

``sloads.rigid_body`` is the single owner of the d'Alembert field every balanced
case closes with. It has no printed oracle -- concept mode never does -- so per
``CONVENTIONS.md`` §6 the gate is a set of stated identities, and they are the
strong kind: each one is a property the field must have for *any* mass set, not
a number pinned off a fixture.

* ``Sum r x f == -[I]{omega_dot}`` -- the whole reason the tensor is the right
  operator, and the identity the four one-component predecessors did **not**
  satisfy;
* a uniform load factor produces no moment about the mass centre, so the
  translational and rotational halves of the closure cannot fight;
* the products of inertia carry the sign the matrix says they do -- invisible to
  every symmetric case, hence stated here;
* the singular tensor raises rather than pseudo-inverting (risk R4).

The L-3 predicate is guarded here too, beside the field it feeds.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from sloads.mass_distribution import assembly_distributes_mass
from sloads.models import MassComponent
from sloads.rigid_body import (
    G_IN_S2,
    InertiaTensor,
    PointMass,
    SelfInertia,
    SingularInertiaError,
    inertia_tensor,
    radians_per_s2,
    relief_force,
    relief_moment,
)

#: A deliberately lopsided mass set: no plane of symmetry, so every product of
#: inertia is non-zero and every coupling term is exercised. A symmetric set
#: would pass this file with three of the tensor's six components wrong.
_MASSES = [
    PointMass(120.0, 30.0, 12.0, -4.0),
    PointMass(80.0, -45.0, 3.0, 9.0),
    PointMass(200.0, 5.0, -20.0, 6.0),
    PointMass(60.0, -18.0, -7.0, -11.0),
]


def _resultant(loads, self_terms=()):
    """``(F, M)`` about the origin of a list of ``(r, f)`` pairs plus free moments."""
    f = [0.0, 0.0, 0.0]
    m = [0.0, 0.0, 0.0]
    for (x, y, z), (fx, fy, fz) in loads:
        f[0] += fx
        f[1] += fy
        f[2] += fz
        m[0] += y * fz - z * fy
        m[1] += z * fx - x * fz
        m[2] += x * fy - y * fx
    for mx, my, mz in self_terms:
        m[0] += mx
        m[1] += my
        m[2] += mz
    return tuple(f), tuple(m)


def _centred(masses):
    """``masses`` shifted so their own centroid is the origin -- the closure's
    reference point, where the translational DOF produce no moment."""
    w = sum(pm.weight_lb for pm in masses)
    cx = sum(pm.weight_lb * pm.dx for pm in masses) / w
    cy = sum(pm.weight_lb * pm.dy for pm in masses) / w
    cz = sum(pm.weight_lb * pm.dz for pm in masses) / w
    return [PointMass(pm.weight_lb, pm.dx - cx, pm.dy - cy, pm.dz - cz)
            for pm in masses]


# --------------------------------------------------------------------------- #
# The defining identity
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("omega_dot", [
    (1.7e-3, 0.0, 0.0), (0.0, -2.9e-4, 0.0), (0.0, 0.0, 5.1e-4),
    (1.7e-3, -2.9e-4, 5.1e-4),
])
def test_the_field_produces_exactly_minus_the_inertia_times_omega_dot(omega_dot):
    """``Sum r x f == -[I]{omega_dot}`` -- the identity the whole closure rests on.

    This is what the one-component fields the suite carried before B8a-2 did not
    satisfy: ``fz = +k*w*dx`` alone gives ``Sum w*dx^2``, not ``Iyy``, and the
    gap is whatever ``Sum w*dz^2`` happens to be -- 4 % for pitch, 30 % for roll
    on ``concept_regional_jet``, and 55 % for the yaw DOF that would have copied
    the pattern (plan 13 §3.6).
    """
    masses = _centred(_MASSES)
    tensor = inertia_tensor(masses)
    loads = [((pm.dx, pm.dy, pm.dz),
              relief_force(pm.weight_lb, (pm.dx, pm.dy, pm.dz),
                           (0.0, 0.0, 0.0), omega_dot))
             for pm in masses]
    _, moment = _resultant(loads)

    matrix = tensor.matrix()
    want = [-sum(matrix[i][j] * omega_dot[j] for j in range(3)) for i in range(3)]
    for axis, (got, expect) in enumerate(zip(moment, want)):
        assert got == pytest.approx(expect, rel=1e-12, abs=1e-9), axis


def test_a_uniform_load_factor_produces_no_moment_about_the_mass_centre():
    """Why the three translational DOF stay decoupled ratios.

    ``n = F/W`` is only a closure if it disturbs nothing else, and it is one
    exactly because the reference point is the mass set's own centroid -- which
    step C1 guarantees by solving the ballast from it.
    """
    masses = _centred(_MASSES)
    n = (0.31, -0.12, 2.7)
    loads = [((pm.dx, pm.dy, pm.dz),
              relief_force(pm.weight_lb, (pm.dx, pm.dy, pm.dz), n, (0.0, 0.0, 0.0)))
             for pm in masses]
    force, moment = _resultant(loads)
    w = sum(pm.weight_lb for pm in masses)
    assert force == pytest.approx((-n[0] * w, -n[1] * w, -n[2] * w), rel=1e-12)
    assert moment == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)


def test_the_solve_inverts_the_tensor_including_its_coupling():
    """``[I]{solve(M)} == {M}`` on a set with every product of inertia non-zero.

    ``Ixz`` is the one that matters on a real airplane -- 8.4 % of the ga6's
    pitch inertia -- and it is why the rotational closure is one 3x3 solve rather
    than three ratios.

    Both directions in one place: :meth:`InertiaTensor.moment` is the forward
    multiply G-6's rotational gate reads (R6-T1), and it is checked here against
    the hand-written product as well as against ``solve`` -- an owner compared
    only with a second call to itself is not a drift guard (``CLAUDE.md``
    practice 3).
    """
    tensor = inertia_tensor(_centred(_MASSES))
    assert tensor.ixz != 0.0 and tensor.ixy != 0.0 and tensor.iyz != 0.0
    moment = (1.3e5, -8.8e4, 4.1e5)
    omega_dot = tensor.solve(moment)
    matrix = tensor.matrix()
    got = [sum(matrix[i][j] * omega_dot[j] for j in range(3)) for i in range(3)]
    assert got == pytest.approx(moment, rel=1e-9)
    assert tensor.moment(omega_dot) == pytest.approx(got, rel=1e-12)
    # And the coupling is carried, not dropped: a pure roll takes pitch and yaw
    # moments too, through the products of inertia.
    assert tensor.moment((1.0, 0.0, 0.0)) == pytest.approx(
        (tensor.ixx, -tensor.ixy, -tensor.ixz), rel=1e-12)


def test_the_products_of_inertia_are_stored_as_sums_and_negated_in_the_matrix():
    """The sign convention, stated where it can be checked.

    ``ixz`` is ``Sum w*dx*dz`` -- the form ``WTONECG`` prints and Appendix A
    p136 shows -- and the matrix carries ``-ixz``. Getting this backwards is
    invisible to every symmetric case and to every uncoupled solve, so nothing
    else in the suite would catch it.
    """
    tensor = inertia_tensor([PointMass(10.0, 2.0, 3.0, 5.0)])
    assert tensor.ixx == pytest.approx(10.0 * (9.0 + 25.0))
    assert tensor.ixz == pytest.approx(10.0 * 2.0 * 5.0)
    assert tensor.matrix()[0][2] == pytest.approx(-tensor.ixz)
    assert tensor.matrix()[2][0] == pytest.approx(-tensor.ixz)


def test_a_zero_moment_returns_exactly_zero_rather_than_solving():
    assert InertiaTensor(1.0, 2.0, 3.0).solve((0.0, 0.0, 0.0)) == (0.0, 0.0, 0.0)


def test_a_degenerate_mass_model_raises_rather_than_pseudo_inverting():
    """Risk R4: every mass on one line has no invertible tensor, and inventing
    an acceleration for it would put a fabricated load in a deliverable."""
    collinear = [PointMass(10.0, x, 0.0, 0.0) for x in (-5.0, 0.0, 5.0)]
    with pytest.raises(SingularInertiaError):
        inertia_tensor(collinear).solve((0.0, 1.0, 1.0))


# --------------------------------------------------------------------------- #
# Self-inertia (L-3)
# --------------------------------------------------------------------------- #
def test_self_inertia_adds_to_the_tensor_and_comes_back_as_a_free_moment():
    """The two halves of L-3 are the same quantity, so the case still closes.

    An item's entered inertia joins ``[I]``, which lowers ``omega_dot``; the
    free moment it applies at its node is exactly the share of the reaction that
    lowering represents. If the two ever disagreed the case would stop closing
    -- which is what ``test_the_case_closes_in_all_six_dof`` would then say.
    """
    masses = _centred(_MASSES)
    self_terms = [SelfInertia(1.0e5, 2.0e5, 3.0e5), SelfInertia(0.0, 0.0, 7.0e4)]
    placement = inertia_tensor(masses)
    full = inertia_tensor(masses, self_terms)
    assert full.izz == pytest.approx(placement.izz + 3.0e5 + 7.0e4)
    assert full.ixz == placement.ixz          # no self products of inertia

    moment = (2.2e5, -1.4e5, 9.0e4)
    omega_dot = full.solve(moment)
    loads = [((pm.dx, pm.dy, pm.dz),
              relief_force(pm.weight_lb, (pm.dx, pm.dy, pm.dz),
                           (0.0, 0.0, 0.0), omega_dot))
             for pm in masses]
    frees = [relief_moment(si, omega_dot) for si in self_terms]
    _, got = _resultant(loads, frees)
    assert got == pytest.approx((-moment[0], -moment[1], -moment[2]), rel=1e-9)


def test_the_distributed_mass_predicate_is_the_wing_and_only_the_wing():
    """**The L-3 drift guard.** The predicate and the assembly must agree.

    ``balance.body_inertia`` carries as a point mass exactly what this returns
    ``False`` for, and ``balance.point_mass_self_inertia`` gives a free moment to
    exactly the same set. Today that is every component but ``WING``. When the
    empennage or the fuselage gains a distributed mass model, this test is the
    one that says the exclusion has to follow it -- rather than the double-count
    being rediscovered from a wrong ``Izz``.
    """
    assert assembly_distributes_mass(MassComponent.WING)
    others = [c for c in MassComponent if c is not MassComponent.WING]
    assert others, "MassComponent has only one member -- the guard is vacuous"
    for component in others:
        assert not assembly_distributes_mass(component), component


def test_the_weight_space_conversion_is_the_suites_own_gravity():
    """``omega_dot`` is in 1/in; ``G_IN_S2`` takes it to rad/s^2.

    Pinned against ``constants.G`` rather than ``units.G_IN_S2`` deliberately --
    see the module docstring for why this arithmetic uses the Imperial-internal
    value the inertia unit conversion is built from.
    """
    from sloads.constants import LBIN2_PER_SLUGFT2

    assert pytest.approx(386.088, rel=1e-9) == G_IN_S2
    assert pytest.approx(144.0 * G_IN_S2 / 12.0, rel=1e-12) == LBIN2_PER_SLUGFT2
    assert radians_per_s2((1.0, 2.0, 3.0)) == pytest.approx(
        (G_IN_S2, 2 * G_IN_S2, 3 * G_IN_S2))


if __name__ == "__main__":  # pragma: no cover - zero-dependency self-runner
    raise SystemExit(pytest.main([__file__, "-q"]))
