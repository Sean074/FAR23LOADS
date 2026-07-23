"""Single-source geometry derivations (Step M2-6).

The wing scalars several slices used to carry as independently-editable copies --
``FlightLoadsInput.mac``/``wing_area_sqft``/``xw``/``zw``,
``WingMassInput.dihedral_deg``/``wrp_waterline``, ``LandingInput.wing_area_sqft`` --
and the fuselage ``LayoutInput.fuselage_length``/``_width``/``_height`` are now
**derived** from the single source of truth, ``Project.geometry`` (the WINGGEOM wing
surface + the parametric wing + the fuselage outline).

:func:`wing_reference` computes the wing quantities from geometry; :func:`fuselage_summary`
the fuselage length/width/height from the outline. :func:`sync_geometry_derived` writes
the derived values onto the consuming slices; every module that reads them calls it first.
(Landing gear was a sibling of this pattern until M2R-4 made it pure: `landing.build_landing`
now resolves ``geometry.landing_gear`` onto a local effective-input copy instead of writing
onto ``Project.landing``.) When the wing/parametric/outline
geometry is absent (a directly-constructed test project) the sync is a no-op, so an
explicitly-set slice value still flows through -- exactly the STRSPEED wing-area fallback.

The derived values are deliberately **not** serialized (see ``io.py``); the GUI shows them
read-only. So there is no independently-editable copy and a save->reload is a no-op.
"""
from __future__ import annotations

import math
from typing import NamedTuple, Optional

from .constants import IN2_PER_FT2
from .models import Project


class WingReference(NamedTuple):
    """The wing geometry derived from ``Project.geometry`` (Step M2-6)."""
    surface_name: str
    s_sqft: float           # total wing area S (ft^2), WINGGEOM strip integral
    mac: float              # mean aerodynamic chord (in)
    xlemac: float           # fuselage station of the MAC leading edge (in)
    y_mac: float            # butt line of the MAC (in)
    xw: float               # fuselage station of 25% wing MAC (= XLEMAC + 0.25*MAC)
    zw: float               # waterline of 25% wing MAC (wrp + Y_MAC*tan(dihedral))
    dihedral_deg: float     # wing geometric dihedral (parametric)
    wrp_waterline: float    # waterline of the wing reference plane at centreline (parametric)


def wing_reference(project: Project, surface_name: str = "wing") -> Optional[WingReference]:
    """The wing reference geometry from ``project.geometry``, or ``None`` when absent.

    ``mac``/``s_sqft``/``xlemac``/``y_mac`` come from the WINGGEOM surface strip
    integrator (:func:`farloads.modules.wing_geometry.surface_properties`); ``xw`` is the
    25%-MAC station and ``zw`` the 25%-MAC waterline, using the parametric wing's
    ``root_waterline_z`` and ``dihedral_deg`` (both default to 0 when there is no
    parametric slice, so ``zw`` degrades to the centreline waterline). Returns ``None``
    when there is no geometry slice, no matching wing surface, or the surface is
    degenerate (fewer than two strips / points)."""
    geom = project.geometry
    if geom is None:
        return None
    surf = geom.by_name(surface_name)
    if surf is None:
        return None
    from .modules.wing_geometry import surface_properties
    try:
        vals = {v.label: v.value for v in surface_properties(surf).values}
    except (ValueError, ZeroDivisionError):
        return None
    mac = vals["MAC"]
    xlemac = vals["XLE(MAC) station of MAC LE"]
    y_mac = vals["YLE(MAC) butt line of MAC"]
    s_sqft = vals["Total area"] / IN2_PER_FT2
    par = geom.parametric
    dihedral_deg = par.dihedral_deg if par is not None else 0.0
    wrp_waterline = par.root_waterline_z if par is not None else 0.0
    xw = xlemac + 0.25 * mac
    zw = wrp_waterline + y_mac * math.tan(math.radians(dihedral_deg))
    return WingReference(surface_name, s_sqft, mac, xlemac, y_mac, xw, zw,
                         dihedral_deg, wrp_waterline)


def fuselage_summary(outline) -> Optional[tuple]:
    """``(length, max_width, max_height)`` in inches from a fuselage outline.

    Length is the fuselage-station span (last minus first section); width/height are
    the maxima over the sections. Returns ``None`` when the outline is empty."""
    if outline is None or not outline.sections:
        return None
    xs = [s.x for s in outline.sections]
    length = max(xs) - min(xs)
    width = max(s.width for s in outline.sections)
    height = max(s.height for s in outline.sections)
    return length, width, height


def sync_geometry_derived(project: Project) -> None:
    """Fill the derived geometry copies on the consuming slices from ``project.geometry``.

    Idempotent and cheap; called at the top of every consuming module's ``run`` (and by
    ``io`` after a project loads) so the calc always reads the single-source value. A
    no-op for any slice whose backing geometry is absent, so a directly-constructed test
    project that set the value on the slice keeps working."""
    geom = project.geometry
    # ``mac``/``S``/``xw`` come from the wing surface alone -- always derivable when a
    # wing surface is present. ``zw`` and the wing-mass dihedral/wrp need the parametric
    # wing (Z data a WINGGEOM surface does not carry), so they are only synced when a
    # parametric slice exists; a project with a wing surface but no parametric keeps its
    # stored zw/dihedral/wrp (the STRSPEED fallback), so no value is ever zeroed.
    has_parametric = geom is not None and geom.parametric is not None
    wr = wing_reference(project, "wing")
    if wr is not None:
        fl = project.flight_loads
        if fl is not None:
            fl.mac = wr.mac
            fl.wing_area_sqft = wr.s_sqft
            fl.xw = wr.xw
            if has_parametric:
                fl.zw = wr.zw
        ld = project.landing
        if ld is not None:
            ld.wing_area_sqft = wr.s_sqft
    if has_parametric:
        wm = project.wing_mass
        if wm is not None:
            wr_wm = wing_reference(project, wm.surface or "wing")
            if wr_wm is not None:
                wm.dihedral_deg = wr_wm.dihedral_deg
                wm.wrp_waterline = wr_wm.wrp_waterline
    # Fuselage length/width/height: a derived read-only summary of the outline.
    geom = project.geometry
    if geom is not None and geom.parametric is not None:
        summary = fuselage_summary(geom.fuselage)
        if summary is not None:
            geom.parametric.fuselage_length, geom.parametric.fuselage_width, \
                geom.parametric.fuselage_height = summary
