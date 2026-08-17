"""Rigid-body d'Alembert relief -- the single owner of the closure field.

Plan 13 (``docs/40_history/18_b8a_lateral_closure_plan.md``) decisions **L-2** and
**L-3**, step B8a-2. Conventions: ``docs/10_standard/CONVENTIONS.md`` §1 (axes and
signs) and §7 (single-source owners).

A balanced free-free case closes its residual by accelerating the airplane: the
loads that do not balance are reacted by the mass, exactly as they are in flight.
The field that does it is the **rigid-body d'Alembert field**

.. code-block:: text

    f_i = -m_i (a_cg + omega_dot x r_i)

and this module is the one place it is written. Before B8a-2 the suite carried
three hand-rolled one-component slices of it -- ``fz = -w*dn`` for the vertical
DOF, ``fz = +k*w*dx`` for pitch, ``fz = -k*w*dy`` for roll -- each correct as far
as it went and each missing the companion component that makes the *moment* the
field produces equal ``-[I]{omega_dot}`` rather than ``-Sum w*d^2``. Measured
(plan 13 §3.6), the three omissions were worth 0.08 %, 7 % and 55 % of their
own degree of freedom: three different magnitudes from one omission, which is the
argument for writing the field once instead of a fourth and fifth special case.

Weight-space, and why ``omega_dot`` is in 1/in
----------------------------------------------
Everything here is in the suite's Imperial internal channel and in **weight**
rather than mass: an item contributes ``w_i`` (lb), not ``w_i/g``. That is not a
convenience -- it is what makes the translational DOF come out directly as load
factors (``n = F/W``, in g) the way FAR 23 states them, and it is the convention
``balance._closure`` has used since B2.

The consequence is that the inertia terms are ``Sum w*d^2`` in **lb-in^2** (the
same units ``MassItem.ixx`` is entered in and ``WTONECG`` reports, so the two
producers are directly comparable -- gate G4), and the angular accelerations that
come out of ``[I]{omega_dot} = {M}`` are in **1/in**, i.e. g per inch of arm.
Multiply by :data:`sloads.units.G_IN_S2` for rad/s^2, or use
:func:`radians_per_s2`. The force the field applies stays in lb throughout, with
no gravity constant anywhere in the arithmetic.

The tensor's sign convention
----------------------------
:class:`InertiaTensor` stores the **products of inertia as sums**, ``ixy = Sum
w*dx*dy``, not as the negated off-diagonal entries of the matrix. That is the
form ``WTONECG`` prints (``IXZ``, Appendix A p136) and the form a reader
checking it against a handbook expects; the negation happens once, in
:meth:`InertiaTensor.matrix`. Getting this backwards is a sign error that no
symmetric case can see -- ``ixy`` and ``iyz`` vanish for a mirror-symmetric mass
model -- so it is stated here and gated in ``tests/test_rigid_body.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from .constants import IN_PER_FT, G

Vec3 = Tuple[float, float, float]

#: Gravity in in/s^2, from :data:`sloads.constants.G` rather than
#: :data:`sloads.units.G_IN_S2` (386.0886, ISO standard gravity). Two reasons:
#: this module is Imperial-internal weight-space arithmetic, which the suite
#: pins to ``constants.G`` throughout (``LBIN2_PER_SLUGFT2`` is built from the
#: same value, so a tensor and its slug-ft^2 report stay consistent); and
#: ``units`` imports ``models``, so importing it here would close a cycle the
#: moment a result type carries a tensor. The two differ by 1.5e-6 relative.
G_IN_S2 = G * IN_PER_FT

__all__ = [
    "InertiaTensor",
    "PointMass",
    "SelfInertia",
    "SingularInertiaError",
    "inertia_tensor",
    "radians_per_s2",
    "relief_force",
    "relief_moment",
]


class SingularInertiaError(ValueError):
    """The assembled mass model has no invertible inertia tensor.

    Raised rather than pseudo-inverted (plan 13 risk R4): a real mass set gives a
    symmetric positive-definite tensor, so a singular one means a degenerate
    model -- every mass on one line, or no mass at all -- and silently returning
    *an* answer for it would put a fabricated acceleration into a deliverable.
    """


@dataclass(frozen=True)
class PointMass:
    """A weight at a position **relative to the reference point** (the CG).

    ``weight_lb`` in lb, ``dx``/``dy``/``dz`` in inches. Relative rather than
    absolute so the caller states the reference once and this module never has to
    guess which point a residual was taken about.
    """

    weight_lb: float
    dx: float
    dy: float
    dz: float


@dataclass(frozen=True)
class SelfInertia:
    """An item's own rotational inertia about its own CG, in lb-in^2.

    The L-3 term: a mass the assembly models as a *point* still resists angular
    acceleration about its own centre, and that resistance is a **free moment**
    at its node, not a force. Only items the assembly does not itself distribute
    carry one -- see :func:`sloads.mass_distribution.assembly_distributes_mass`.
    """

    ixx: float = 0.0
    iyy: float = 0.0
    izz: float = 0.0


@dataclass(frozen=True)
class InertiaTensor:
    """The assembled mass set's inertia about a stated point, in lb-in^2.

    Diagonals are the moments of inertia ``Sum w*(b^2 + c^2)``; ``ixy``/``ixz``/
    ``iyz`` are the products of inertia stored as **plain sums** ``Sum w*a*b``
    (see the module docstring). ``Ixy`` and ``Iyz`` vanish identically for a
    mirror-symmetric mass model and are computed rather than assumed, so a
    fixture that ever breaks that symmetry is reacted correctly instead of
    silently.
    """

    ixx: float = 0.0
    iyy: float = 0.0
    izz: float = 0.0
    ixy: float = 0.0
    ixz: float = 0.0
    iyz: float = 0.0

    def __add__(self, other: "InertiaTensor") -> "InertiaTensor":
        return InertiaTensor(
            ixx=self.ixx + other.ixx, iyy=self.iyy + other.iyy,
            izz=self.izz + other.izz, ixy=self.ixy + other.ixy,
            ixz=self.ixz + other.ixz, iyz=self.iyz + other.iyz)

    def matrix(self) -> Sequence[Sequence[float]]:
        """The 3x3 matrix ``[I]``, with the products of inertia **negated**."""
        return [[self.ixx, -self.ixy, -self.ixz],
                [-self.ixy, self.iyy, -self.iyz],
                [-self.ixz, -self.iyz, self.izz]]

    def solve(self, moment: Vec3) -> Vec3:
        """``omega_dot`` (1/in) such that ``[I]{omega_dot} = {moment}``.

        The rotational closure in one call. Coupled through ``ixz``, which is
        **not** small -- 8.4 % of the ga6's own pitch inertia and larger still on
        the regional jet -- so solving roll, pitch and yaw as three independent
        ratios is not an approximation but an error (plan 13 §3.5).

        A zero-moment case short-circuits to exactly zero rather than solving,
        so a symmetric case's lateral accelerations are ``0.0`` on the nose
        instead of the 1e-18 a floating-point solve leaves behind.
        """
        if not any(moment):
            return (0.0, 0.0, 0.0)
        return _solve3(self.matrix(), moment)

    def moment(self, omega_dot: Vec3) -> Vec3:
        """``[I]{omega_dot}`` (lb-in) -- the moment that angular acceleration takes.

        The forward direction of :meth:`solve`, and the quantity G-6's rotational
        gate compares with LANDLOAD's ``PITCHP``/``ROLLP``/``YAWP`` (R6-T1). It
        is stated here rather than written out at the check because it is the
        same ``[I]`` -- products of inertia negated, roll and yaw coupled through
        ``ixz`` -- and a second hand-rolled matrix multiply beside the test is the
        drift ``CLAUDE.md`` practice 3 forbids.

        **Reference-independent for a closure field**: the relief the assembler
        applies at ``omega_dot`` is referred to the mass set's own centroid, where
        ``Sum w_i r_i`` is zero, so the rotational half carries no net force and
        its moment is the same about every point. That is what lets the gate
        compare it with a moment LANDLOAD states about the CG.
        """
        rows = self.matrix()
        return (math.fsum(rows[0][j] * omega_dot[j] for j in range(3)),
                math.fsum(rows[1][j] * omega_dot[j] for j in range(3)),
                math.fsum(rows[2][j] * omega_dot[j] for j in range(3)))


def _solve3(a: Sequence[Sequence[float]], b: Vec3) -> Vec3:
    """Gauss-Jordan with partial pivoting on a 3x3. Raises when singular.

    Hand-rolled because the calc package takes no numerical dependency (see
    ``PROJECT_GUIDE`` §4) -- and at 3x3 with pivoting, the accuracy is the
    inputs', not the algorithm's: the closure residuals it produces come out at
    1e-16 of ``n*W``.
    """
    m = [[*list(row), rhs] for row, rhs in zip(a, b)]
    scale = max(abs(v) for row in a for v in row) or 1.0
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) <= 1e-12 * scale:
            raise SingularInertiaError(
                "the assembled mass model's inertia tensor is singular -- every "
                "mass lies on one line, or the model has no mass. A rigid-body "
                "relief field cannot be solved for it")
        m[col], m[piv] = m[piv], m[col]
        for row in range(3):
            if row == col:
                continue
            f = m[row][col] / m[col][col]
            for k in range(col, 4):
                m[row][k] -= f * m[col][k]
    return (m[0][3] / m[0][0], m[1][3] / m[1][1], m[2][3] / m[2][2])


def inertia_tensor(masses: Iterable[PointMass],
                   self_inertia: Iterable[SelfInertia] = ()) -> InertiaTensor:
    """The tensor of ``masses`` about their reference point, plus ``self_inertia``.

    Two contributions, and the split is decision L-3: the **placement** term
    ``Sum w*d^2`` from where the assembly puts each mass, and the **self** term
    from what each item resists on its own. Adding an item's entered self-inertia
    on top of a spread the assembly already models would count the same physical
    quantity twice -- measured on the ga6 wing, 4.444e6 entered against 4.288e6
    spread, -3.5 % -- which is why the caller filters ``self_inertia`` through
    :func:`sloads.mass_distribution.assembly_distributes_mass` rather than
    passing every item.
    """
    ixx = iyy = izz = ixy = ixz = iyz = 0.0
    for pm in masses:
        w, dx, dy, dz = pm.weight_lb, pm.dx, pm.dy, pm.dz
        ixx += w * (dy * dy + dz * dz)
        iyy += w * (dx * dx + dz * dz)
        izz += w * (dx * dx + dy * dy)
        ixy += w * dx * dy
        ixz += w * dx * dz
        iyz += w * dy * dz
    placement = InertiaTensor(ixx, iyy, izz, ixy, ixz, iyz)
    total = InertiaTensor()
    for si in self_inertia:
        total = total + InertiaTensor(si.ixx, si.iyy, si.izz)
    return placement + total


def relief_force(weight_lb: float, r: Vec3, n: Vec3, omega_dot: Vec3) -> Vec3:
    """``-w (n + omega_dot x r)`` -- the d'Alembert force on one mass, in lb.

    ``r`` is the position **relative to the CG** (in), ``n`` the translational
    load factor triple (g) and ``omega_dot`` the angular acceleration (1/in).
    Written out, the six rotational terms are::

        roll   p_dot ->  fy = +w p_dot dz ,  fz = -w p_dot dy
        pitch  q_dot ->  fx = -w q_dot dz ,  fz = +w q_dot dx
        yaw    r_dot ->  fx = +w r_dot dy ,  fy = -w r_dot dx

    Each acceleration has **two** force components. The one the suite carried
    before B8a-2 is the second of each pair; the first is the companion, and it
    is the difference between ``Sum w*d^2`` and a moment of inertia.
    """
    dx, dy, dz = r
    p, q, s = omega_dot
    # ``+ 0.0`` normalises IEEE negative zero (-0.0 + 0.0 is +0.0, and adding
    # zero is the identity on everything else). A component that is exactly zero
    # -- every lateral one on a symmetric case -- would otherwise reach the deck
    # as ``-0.000000E+00`` on one platform and ``0.000000E+00`` on another, and
    # the Imperial digest would churn for no physical reason.
    return (-weight_lb * (n[0] + q * dz - s * dy) + 0.0,
            -weight_lb * (n[1] + s * dx - p * dz) + 0.0,
            -weight_lb * (n[2] + p * dy - q * dx) + 0.0)


def relief_moment(self_inertia: SelfInertia, omega_dot: Vec3) -> Vec3:
    """``-[I_self]{omega_dot}`` -- the free moment an item's own inertia applies.

    Diagonal because :class:`~sloads.models.inputs.MassItem` enters no products
    of inertia; the day it does, this is the one place that changes.
    """
    return (-self_inertia.ixx * omega_dot[0],
            -self_inertia.iyy * omega_dot[1],
            -self_inertia.izz * omega_dot[2])


def radians_per_s2(omega_dot: Vec3) -> Vec3:
    """``omega_dot`` (1/in, weight-space) converted to rad/s^2."""
    return (omega_dot[0] * G_IN_S2, omega_dot[1] * G_IN_S2,
            omega_dot[2] * G_IN_S2)
