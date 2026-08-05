"""Coordinate / units map: SLOADS airplane axes -> sbeam global frame (CID 0).

The whole suite works in the original program's Imperial airplane axes, all in
**inches** (SLOADS station/butt/waterline):

* ``x`` -- fuselage station, **positive aft**
* ``y`` -- butt line, **positive right** (out the starboard wing)
* ``z`` -- waterline, **positive up**

Forces follow the same axes: ``fz`` is lift (+up), ``fx`` is drag (+aft); the
wing torsion ``myy`` is the moment about the spanwise ``y`` axis.

sbeam runs in a single basic coordinate system (NASTRAN ``CID 0``), right-handed,
in whatever consistent unit set the user's model uses. SLOADS already uses a
right-handed inch frame that matches that convention, so the transform is the
**identity** -- the export emits inches into ``CID 0`` directly.

This module is the *single editable point* for that mapping: if a downstream
sbeam model ever needs a sign flip, an axis swap, or an inch->other-unit scale,
change it here and every exported GRID / FORCE / MOMENT follows.

**The unit scale (M4-20 step 4).** That "other-unit scale" is now real: a deck
may be written in the SI solver set (N / mm / N*mm / MPa) instead of the Imperial
one. Each function takes a :class:`~sloads.units.DeliverableUnits` and applies
its factor, so this module is the *only* place in the export channel where a load
or a coordinate is multiplied by anything. Nothing in ``sbeam_bridge`` scales:
its arithmetic is unchanged and unit-free, and it routes every dimensional value
it emits -- cards *and* CSV cells -- through these three functions, so a file's
numbers cannot disagree with the cards beside it.

Imperial is the all-1.0 identity set, so an Imperial deck takes the same code
path and cannot drift.
"""

from __future__ import annotations

from typing import Tuple

from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units

Vec3 = Tuple[float, float, float]

# The NASTRAN coordinate-system id the bridge emits into. CID 0 is the basic
# (global) frame; GRID/FORCE/MOMENT cards stamp this in their CP/CID field.
SBEAM_CID = 0

#: The default unit set: the Imperial identity, so an un-parameterised call
#: behaves exactly as it did before the unit scale existed.
IMPERIAL = deliverable_units(UnitSystem.IMPERIAL, Channel.SOLVER)


def _checked(units: DeliverableUnits) -> DeliverableUnits:
    """Reject a unit set that is not dimensionally consistent (D-19).

    A solver deck's correctness rests on ``moment == force x length`` and
    ``pressure == force / length^2``. The human-readable set breaks both in SI
    (N*m and kPa against a mm length) and is a plausible thing to pass by
    mistake, since it is what every *report* is written in -- so refuse it here,
    at the one point every card and cell passes through, rather than emit a deck
    that parses cleanly and sizes structure to a 1000x-wrong torsion.
    """
    if not units.is_consistent:
        raise ValueError(
            f"{units.channel.value} unit set ({units.force.label}, "
            f"{units.length.label}, {units.moment.label}, {units.pressure.label}) "
            "is not dimensionally consistent and must not be written to an sbeam "
            "deck -- resolve it with deliverable_units(system, Channel.SOLVER)"
        )
    return units


def to_grid(x: float, y: float, z: float,
            units: DeliverableUnits = IMPERIAL) -> Vec3:
    """Map a SLOADS station point (in) to an sbeam GRID location (CID 0)."""
    k = _checked(units).length.factor
    return (x * k, y * k, z * k)


def to_force(fx: float, fy: float, fz: float,
             units: DeliverableUnits = IMPERIAL) -> Vec3:
    """Map a SLOADS force vector (lb) to sbeam global components (CID 0)."""
    k = _checked(units).force.factor
    return (fx * k, fy * k, fz * k)


def to_moment(mx: float, my: float, mz: float,
              units: DeliverableUnits = IMPERIAL) -> Vec3:
    """Map a SLOADS moment vector (lb-in) to sbeam global components (CID 0)."""
    k = _checked(units).moment.factor
    return (mx * k, my * k, mz * k)


def to_pressure(psi: float, units: DeliverableUnits = IMPERIAL) -> float:
    """Map a SLOADS load intensity (lb/in^2) to the deck's stress unit."""
    return psi * _checked(units).pressure.factor
