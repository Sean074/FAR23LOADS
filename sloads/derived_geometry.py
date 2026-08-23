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
from typing import NamedTuple, Optional, Tuple

from . import workflow as wf
from .constants import DEFAULT_FRONT_SPAR_PCT, DEFAULT_REAR_SPAR_PCT, IN2_PER_FT2
from .models import MissingInputError, Project


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


def require_wing_reference(project: Project, surface_name: str = "wing") -> WingReference:
    """:func:`wing_reference`, or a refusal naming the page — note 33, DS-2/DS-3.

    The wing scalars ``mac``/``s_sqft``/``xw``/``zw`` used to be carried on
    ``FlightLoadsInput`` as an editable second opinion, filled from here on every
    run. With the copies gone (DS-1) there is nothing to fall back to, so an
    absent or degenerate wing is an error at the point of use rather than a
    silent set of zeros propagating into a balance.
    """
    ref = wing_reference(project, surface_name)
    if ref is None:
        raise MissingInputError(
            f"this analysis needs the {surface_name!r} wing planform: add the "
            f"surface on the {wf.BY_KEY['configuration_layout'].title} page. The MAC, "
            "area, 25%-MAC station and waterline are read from it, not entered separately.")
    return ref


def airplane_length_in(project: Project) -> float:
    """SELECT's LF, the whole-airplane length (inches), from its single home
    ``geometry.empennage.airplane_length_in`` (#52, note 33 §8); ``0.0`` when no
    empennage is defined. Both tail inertia defaults -- the 23.423(b) pitch
    inertia and the 23.441 default IZZ -- read it from here; until schema v55
    each tail carried its own copy and nothing reconciled them.
    """
    geom = project.geometry
    emp = geom.empennage if geom is not None else None
    return float(emp.airplane_length_in) if emp is not None else 0.0


def wing_plane(project: Project, surface_name: str = "wing") -> Tuple[float, float]:
    """``(wrp_waterline, dihedral_deg)`` for a surface's wing plane — note 33, DS-2.

    The **single** owner of these two scalars for every consumer (note 33, DS-1:
    they used to be carried on ``WingMassInput``, where they were a second,
    editable opinion of the parametric wing that nothing persisted). Returns
    ``(0.0, 0.0)`` when the surface or the parametric slice is absent, which is
    exactly what :func:`wing_reference` degrades to and what the removed fields
    defaulted to — so this reproduces the old effective value rather than
    changing it (gate DG-1).

    Two floats rather than the ``WingReference`` itself, matching
    :func:`sloads.modules.airloads.air_load_distribution`'s existing signature:
    the consumers are handed a ``SurfaceInput`` and cannot look the parametric
    wing up, which is the whole reason the copy existed (note 33 §1.3).
    """
    ref = wing_reference(project, surface_name)
    return (0.0, 0.0) if ref is None else (ref.wrp_waterline, ref.dihedral_deg)


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


def _section_dim_at(outline, x: float, attr: str) -> Optional[float]:
    """A section dimension at fuselage station ``x`` by clamped interpolation.

    Linear interpolation between the bracketing sections of the same station
    table :func:`fuselage_summary` reduces to a maximum; clamped at both ends
    rather than extrapolated, for the same reason ``tail_geometry._interp`` clamps
    -- a station a rounding step outside the table must not produce a negative
    body.
    """
    if outline is None or len(getattr(outline, "sections", ())) < 2:
        return None
    sections = sorted(outline.sections, key=lambda s: s.x)
    if x <= sections[0].x:
        return getattr(sections[0], attr)
    for a, b in zip(sections, sections[1:]):
        if x <= b.x:
            va, vb = getattr(a, attr), getattr(b, attr)
            if b.x == a.x:
                return vb
            return va + (vb - va) * (x - a.x) / (b.x - a.x)
    return getattr(sections[-1], attr)


def fuselage_width_at(outline, x: float) -> Optional[float]:
    """Body width (in) at fuselage station ``x``, or ``None`` without an outline.

    **The single owner of "how wide is the fuselage here".** ``fuselage_summary``
    answers the *maximum*, which is the right number for a three-view summary and
    the wrong one for any load path that attaches somewhere specific: the h-tail
    reacts into the tail cone, not into the widest frame (decision T-8a).
    """
    return _section_dim_at(outline, x, "width")


def fuselage_height_at(outline, x: float) -> Optional[float]:
    """Body height (in) at fuselage station ``x``, or ``None`` without an outline.

    **The single owner of "how tall is the fuselage here"** -- the height sibling
    of :func:`fuselage_width_at`, added for the fin-root datum (backlog Pri 1,
    from T-8a): the fin sits on the tail cone's local top,
    ``z_centre(x_fin) + height(x_fin)/2``, not half the *maximum* body height
    above the wing root.
    """
    return _section_dim_at(outline, x, "height")


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


class FuselageCentreline(NamedTuple):
    """The fuselage section-centre line ``(x, 0, z_c(x))`` (note 24 R-4, v52).

    The fuselage **load reference axis** of the LRA beam model: ``points`` are
    ``(x, z_centre)`` in station order, one per outline section, each taken
    from the section's entered ``z_centre`` or defaulted from
    :func:`body_drag_waterline` -- ``assumed`` is True when *any* station was
    defaulted (or the waterline default is itself assumed), and ``note`` is the
    in-band sentence the deck header carries then. Same provenance shape as
    :class:`CarryThrough` / :class:`SobStation`.
    """
    points: tuple
    assumed: bool
    basis: str
    note: str = ""

    def z_at(self, x: float) -> float:
        """Centre waterline at station ``x`` -- clamped linear interpolation,
        for the same reason :func:`fuselage_width_at` clamps."""
        pts = self.points
        if x <= pts[0][0]:
            return pts[0][1]
        for (xa, za), (xb, zb) in zip(pts, pts[1:]):
            if x <= xb:
                if xb == xa:
                    return zb
                return za + (zb - za) * (x - xa) / (xb - xa)
        return pts[-1][1]


CENTRELINE_ENTERED = "entered z_centre per section"
CENTRELINE_DEFAULTED = "defaulted from the body-drag waterline -- assumed"


def fuselage_centreline(project: Project) -> Optional[FuselageCentreline]:
    """The section-centre line, or ``None`` when there is no fuselage outline.

    **The single owner of "where is the fuselage centre here"** (decision
    LM-2, implementation note 25). A section that entered ``z_centre`` uses
    it; one that did not takes :func:`body_drag_waterline`'s value -- the
    suite's standing no-body-centreline-datum fallback -- and the whole line
    is marked assumed, because a beam axis with one guessed station is a
    guessed axis.
    """
    geom = project.geometry
    outline = geom.fuselage if geom is not None else None
    if outline is None or not outline.sections:
        return None
    bdw = body_drag_waterline(project)
    sections = sorted(outline.sections, key=lambda s: s.x)
    defaulted = [s for s in sections if s.z_centre is None]
    points = tuple((s.x, bdw.z if s.z_centre is None else float(s.z_centre))
                   for s in sections)
    if not defaulted:
        return FuselageCentreline(points, False, CENTRELINE_ENTERED)
    return FuselageCentreline(
        points, True, CENTRELINE_DEFAULTED,
        f"fuselage centre line ASSUMED at waterline {bdw.z:.2f} for "
        f"{len(defaulted)} of {len(sections)} section(s) -- defaulted from the "
        "body-drag waterline. Enter FuselageSection.z_centre to state it")


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

    Design note: ``docs/40_history/24_body_drag_carrier_note.md`` §8.1.

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
    # The ``flight_loads.zw`` copy that used to sit between the wing plane and this
    # refusal is gone (note 33, DS-1): it was the same number, one edit removed.
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
    # No wing scalars are written onto any slice any more (note 33, DS-1/DS-2):
    # ``flight_loads``' mac/S/xw/zw and ``wing_mass``' dihedral/wrp were copies
    # filled here, and their consumers now read :func:`require_wing_reference` /
    # :func:`wing_plane` at the point of use. What is left below is the fuselage
    # summary, which is a genuine derived *record* rather than a scalar copy.
    # Fuselage length/width/height: a derived read-only summary of the outline.
    geom = project.geometry
    if geom is not None and geom.parametric is not None:
        summary = fuselage_summary(geom.fuselage)
        if summary is not None:
            geom.parametric.fuselage_length, geom.parametric.fuselage_width, \
                geom.parametric.fuselage_height = summary
