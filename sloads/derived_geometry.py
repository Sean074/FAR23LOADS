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

from .constants import DEFAULT_FRONT_SPAR_PCT, DEFAULT_REAR_SPAR_PCT, IN2_PER_FT2
from .models import Project


class CarryThrough(NamedTuple):
    """The wing carry-through the fuselage moment is reacted over (M4-1).

    ``x_f``/``x_r`` are the front and rear spar fuselage stations (in) at the
    surface root, ``d = x_r - x_f`` the carry-through length. ``front_pct``/
    ``rear_pct`` are the chord fractions they came from and ``assumed`` is True
    when either fraction was not entered and
    :data:`~sloads.constants.DEFAULT_FRONT_SPAR_PCT` /
    :data:`~sloads.constants.DEFAULT_REAR_SPAR_PCT` were substituted -- the
    provenance flag every deliverable states, so an assumed spar location is
    never reported as input."""
    surface_name: str
    x_f: float
    x_r: float
    d: float
    front_pct: float
    rear_pct: float
    assumed: bool


def carry_through(project: Project, surface_name: str = "wing") -> Optional[CarryThrough]:
    """The front/rear spar stations at the surface root, or ``None`` when absent.

    The spar stations are the chord fractions ``SurfaceInput.front_spar_pct``/
    ``.rear_spar_pct`` applied to the **root chord** -- the inboard-most point of
    the surface's edge polylines, which is the chord the carry-through structure
    actually spans::

        x_f = x_LE(root) + front_pct * c_root
        x_r = x_LE(root) + rear_pct  * c_root

    This is the support region ``body_loads`` reacts the Ch 15 unbalanced moment
    over (Ref 1 p103, backlog M4-1). Returns ``None`` when there is no geometry
    slice, no matching surface, or the root chord is degenerate (empty polylines
    or ``c_root <= 0``) -- ``body_loads`` then falls back to its flagged
    whole-body closure artifact. An unset fraction is filled from the module
    defaults and flags the result ``assumed``; the fractions are used as given
    otherwise (no clamping -- an out-of-order pair is caught by ``d <= 0``)."""
    geom = project.geometry
    if geom is None:
        return None
    surf = geom.by_name(surface_name)
    if surf is None or not surf.leading_edge or not surf.trailing_edge:
        return None
    x_le = surf.leading_edge[0][0]           # polylines run inboard -> outboard
    c_root = surf.trailing_edge[0][0] - x_le
    if c_root <= 0.0:
        return None
    assumed = surf.front_spar_pct is None or surf.rear_spar_pct is None
    front = DEFAULT_FRONT_SPAR_PCT if surf.front_spar_pct is None else float(surf.front_spar_pct)
    rear = DEFAULT_REAR_SPAR_PCT if surf.rear_spar_pct is None else float(surf.rear_spar_pct)
    x_f = x_le + front * c_root
    x_r = x_le + rear * c_root
    if x_r - x_f <= 0.0:
        return None
    return CarryThrough(surface_name, x_f, x_r, x_r - x_f, front, rear, assumed)


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
    integrator (:func:`sloads.modules.wing_geometry.surface_properties`); ``xw`` is the
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


def fuselage_width_at(outline, x: float) -> Optional[float]:
    """Body width (in) at fuselage station ``x``, or ``None`` without an outline.

    Linear interpolation between the bracketing sections of the same station-area
    table :func:`fuselage_summary` reduces to a maximum; clamped at both ends
    rather than extrapolated, for the same reason ``tail_geometry._interp`` clamps
    -- a station a rounding step outside the table must not produce a negative
    body.

    **The single owner of "how wide is the fuselage here".** ``fuselage_summary``
    answers the *maximum*, which is the right number for a three-view summary and
    the wrong one for any load path that attaches somewhere specific: the h-tail
    reacts into the tail cone, not into the widest frame (decision T-8a).
    """
    if outline is None or len(getattr(outline, "sections", ())) < 2:
        return None
    sections = sorted(outline.sections, key=lambda s: s.x)
    if x <= sections[0].x:
        return sections[0].width
    for a, b in zip(sections, sections[1:]):
        if x <= b.x:
            if b.x == a.x:
                return b.width
            return a.width + (b.width - a.width) * (x - a.x) / (b.x - a.x)
    return sections[-1].width


class SobStation(NamedTuple):
    """The surface's side-of-body butt line, and on whose authority (BM-1).

    ``y`` is the butt line (in) the surface structurally attaches to the fuselage
    at; ``assumed`` is False only when the project entered ``sob_y_in``;
    ``basis`` names the branch that produced the value and ``note`` is the
    in-band sentence a derived value owes its consumer -- the same provenance
    shape as :class:`CarryThrough`, :class:`BodyDragWaterline` and
    ``tail_span.HTailAttachment``."""
    y: float
    assumed: bool
    basis: str
    note: str = ""


SOB_ENTERED = "entered sob_y_in"
SOB_HALF_WIDTH = "half the fuselage maximum width -- assumed"


def sob_station(project: Project, surface_name: str = "wing") -> Optional[SobStation]:
    """The surface's side-of-body station, or ``None`` when nothing states one.

    **The single owner of the SOB source** (decision BM-1, note 24 R-3)::

        entered SurfaceInput.sob_y_in      -> its value        (assumed False)
        geometry.parametric.fuselage_width -> width / 2        (assumed True)
        neither                            -> None

    The fallback is half the fuselage **maximum** width -- for the wing that is
    ordinarily the right frame, because the wing carries through near the widest
    section; it is still marked assumed because nobody entered the joint. It is
    **never** ``wing_mass.inboard_rib_y``: that is the WINGINER mass-panel
    start, a mass-model quantity that sits well inboard of a real fuselage side
    (BL 40 on the regional jet against a 74.5 in body half-width would be a
    different airplane). ``None`` means the project has neither an entered butt
    line nor any fuselage width -- consumers then omit their SOB node and say
    so, rather than inventing a body.
    """
    geom = project.geometry
    if geom is None:
        return None
    surf = geom.by_name(surface_name)
    if surf is not None and surf.sob_y_in is not None:
        return SobStation(
            float(surf.sob_y_in), False, SOB_ENTERED,
            f"side of body at BL {float(surf.sob_y_in):.2f} (entered sob_y_in)")
    width = geom.parametric.fuselage_width if geom.parametric is not None else 0.0
    if not width:
        summary = fuselage_summary(geom.fuselage)
        width = summary[1] if summary is not None else 0.0
    if width:
        return SobStation(
            0.5 * width, True, SOB_HALF_WIDTH,
            f"side of body ASSUMED at BL {0.5 * width:.2f} -- half the fuselage "
            f"maximum width ({width:.1f} in). Enter {surface_name} sob_y_in to "
            "state the joint")
    return None


class BodyDragWaterline(NamedTuple):
    """Where the assembled model applies the airplane's non-wing drag (D-1).

    ``z`` is the waterline (in), ``assumed`` False only when the project entered
    it, and ``basis`` names where it came from. ``note`` is the in-band statement
    a derived value carries onto every deliverable -- the same provenance shape
    :class:`CarryThrough` and ``tail_geometry.FinRoot`` use."""
    z: float
    assumed: bool
    basis: str
    note: str = ""


#: What a derived body-drag waterline says on every deliverable it reaches.
_BODY_DRAG_ASSUMED = (
    "body drag waterline ASSUMED at the wing reference plane -- the suite has no "
    "body-centreline datum, so the non-wing drag is applied where the FLTLOADS "
    "trim itself assumes the whole airplane's drag acts. Enter "
    "body_drag_waterline_z to state it.")


def body_drag_waterline(project: Project) -> BodyDragWaterline:
    """Waterline the ``body-axial`` load acts at (in) -- **the single owner** (D-1).

    Design note: ``docs/30_future/20_body_drag_carrier_note.md`` §8.1.

    **Why this is worth an owner at all.** The magnitude of the body-axial load is
    fixed by definition (``vn.dx - sum(fx of the wing strips)``) and its fuselage
    station reaches no gate -- a pure axial force contributes ``my = (z-zcg)*fx``,
    with no ``x`` term. So this waterline is the *entire* free parameter of the
    body drag carrier, and it moves the pre-closure pitch residual one-for-one.

    Resolution order -- deliberately **two** branches::

        explicit body_drag_waterline_z -> use it                  (assumed False)
        otherwise                      -> zw, with a loud note    (assumed True)

    There is no geometry branch, and its absence is the decision. The obvious
    candidate, ``root_waterline_z``, is the datum ``tail_geometry.fin_root_waterline``
    measures "the top of the fuselage" from -- but it is the **wing** root, and
    using it puts ``ga6_normal``'s ``SIDE GUST`` pitch residual at -1.173 %,
    over the 1 % gate, on the Appendix A fixture. It would also be a trap rather
    than merely wrong: ``ga6_normal`` carries ``fuselage_height = 0.0``, so any
    branch conditioned on body geometry would *flip* the first time a fixture
    gained a body outline -- a fixture-data change silently moving a gate.

    ``zw`` is the fallback because it is the trim's own assumption
    (``flight_envelope._balance`` lumps the whole airplane-less-tail force system
    at ``(xw, zw)``), so a project that has not stated where its body is asserts
    nothing this suite cannot support. It is also the most robust point available:
    the residual is zero there and grows linearly either side, so ``zw`` sits at
    the **centre** of the band within which every gated case passes -- +/-10.6 in
    on ``concept_regional_jet``, +/-8.0 in on ``ga6_normal``. A later measured
    waterline can replace it without re-baselining anything.
    """
    par = project.geometry.parametric if project.geometry is not None else None
    if par is not None and par.body_drag_waterline_z:
        return BodyDragWaterline(par.body_drag_waterline_z, False, "entered")
    ref = wing_reference(project)
    if ref is not None:
        return BodyDragWaterline(ref.zw, True, "wing-plane", _BODY_DRAG_ASSUMED)
    fl = project.flight_loads
    if fl is not None and fl.zw:
        return BodyDragWaterline(fl.zw, True, "wing-plane", _BODY_DRAG_ASSUMED)
    return BodyDragWaterline(0.0, True, "none", (
        "body drag waterline UNKNOWN (no wing reference plane) -- the non-wing "
        "drag is applied at waterline 0. Enter body_drag_waterline_z."))


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
