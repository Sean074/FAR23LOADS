"""Coordinate / units map: FAR23LOADS airplane axes -> sbeam global frame (CID 0).

The whole suite works in the original program's Imperial airplane axes, all in
**inches** (FAR23LOADS station/butt/waterline):

* ``x`` -- fuselage station, **positive aft**
* ``y`` -- butt line, **positive right** (out the starboard wing)
* ``z`` -- waterline, **positive up**

Forces follow the same axes: ``fz`` is lift (+up), ``fx`` is drag (+aft); the
wing torsion ``myy`` is the moment about the spanwise ``y`` axis.

sbeam runs in a single basic coordinate system (NASTRAN ``CID 0``), right-handed,
in whatever consistent unit set the user's model uses. FAR23LOADS already uses a
right-handed inch frame that matches that convention, so the transform is the
**identity** -- the export emits inches into ``CID 0`` directly.

This module is the *single editable point* for that mapping: if a downstream
sbeam model ever needs a sign flip, an axis swap, or an inch->other-unit scale,
change it here and every exported GRID / FORCE / MOMENT follows.
"""

from __future__ import annotations

from typing import Tuple

Vec3 = Tuple[float, float, float]

# The NASTRAN coordinate-system id the bridge emits into. CID 0 is the basic
# (global) frame; GRID/FORCE/MOMENT cards stamp this in their CP/CID field.
SBEAM_CID = 0


def to_grid(x: float, y: float, z: float) -> Vec3:
    """Map a FAR23LOADS station point (in) to an sbeam GRID location (CID 0, in)."""
    return (x, y, z)


def to_force(fx: float, fy: float, fz: float) -> Vec3:
    """Map a FAR23LOADS force vector (lb) to sbeam global components (CID 0)."""
    return (fx, fy, fz)


def to_moment(mx: float, my: float, mz: float) -> Vec3:
    """Map a FAR23LOADS moment vector (lb-in) to sbeam global components (CID 0)."""
    return (mx, my, mz)
