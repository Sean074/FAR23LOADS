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
from .models import MissingInputError, Project, SurfaceInput, WeightEnvelopeInput


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


def require_integrable_planform(surf: SurfaceInput) -> None:
    """Refuse a surface whose planform cannot be integrated (#71, PB-21).

    The single owner of the WINGGEOM strip integral's precondition: two or more
    points on each edge polyline (a strip needs a chord at both ends) and two or
    more integration elements. Both checks lived inline in
    :func:`sloads.modules.wing_geometry.surface_properties` and nowhere else,
    so ``wing_inertia.inertia_units`` -- the other entry into the same strip
    sweep -- indexed ``leading_edge[-1]`` and ``interp_x``'s ``pts[-2]`` with no
    guard at all. A one-point edge is the state the oracle GUI's curve editor
    persists after the first complete row, so Wing Loads and Net Loads answered
    a half-entered planform with a raw ``IndexError`` traceback while every
    other wing consumer refused by name.

    A **plain** :class:`ValueError`, not :class:`~sloads.models.MissingInputError`,
    and deliberately (#71, ruling of 2026-08-25): a half-entered planform is
    present-but-invalid input, the second row of the error contract in
    ``00_program_overview.md``. ``MissingInputError`` would make it "not my
    turn", and ``run_all_modules`` catches exactly that -- so a run-all or an
    sbeam export over a mid-entry planform would skip the wing and ship a deck
    with no wing in it rather than refuse. The oracle GUI reads it as
    "cannot run yet" either way, because ``_NOT_READY`` is ``(ValueError,)``.

    The strictly-increasing butt lines are the same precondition seen from
    ``interp_x``, which divides by the butt-line difference of the segment it
    lands on: a repeated station (the curve editor's second row before its
    butt line is typed) divided by zero. What cannot be known before the sweep
    -- a planform that integrates to zero or negative area -- is refused by
    name in ``surface_properties`` at the same point, for the same reason.
    """
    if surf.elements < 2:
        raise ValueError(f"surface '{surf.name}' needs >= 2 integration elements")
    if len(surf.leading_edge) < 2 or len(surf.trailing_edge) < 2:
        raise ValueError(f"surface '{surf.name}' needs >= 2 LE and TE points")
    for edge_name, edge in (("leading", surf.leading_edge), ("trailing", surf.trailing_edge)):
        butt_lines = [pt[1] for pt in edge]
        if any(b <= a for a, b in zip(butt_lines, butt_lines[1:])):
            raise ValueError(
                f"surface '{surf.name}' {edge_name} edge must be ordered inboard "
                f"-> outboard with increasing butt lines, got {butt_lines}")


def require_positive_planform_area(surface_name: str, area_per_side: float) -> None:
    """Refuse a planform that integrated to zero or negative area (#71).

    The half of :func:`require_integrable_planform`'s precondition that can only
    be known after the strip sweep, so it is asked for at the point of use --
    but with one message, because the three sweeps (WINGGEOM's
    ``surface_properties``, the Schrenk distribution, the tail polylines) each
    divide by this area on the next line and each produced the same bare
    ``float division by zero``. Coincident edges and a trailing edge entered
    ahead of the leading edge are ordinary states of a planform mid-entry.
    """
    if area_per_side <= 0.0:
        raise ValueError(
            f"surface '{surface_name}' has no planform area to integrate "
            f"({area_per_side:.6g} in^2 per side): check that the trailing edge is "
            "aft of the leading edge and that the two edges span a butt-line range")


def planform_area_sqft(project: Project, surface_name: str = "wing") -> Optional[float]:
    """The WINGGEOM planform area S (ft^2) of ``surface_name``, or ``None``.

    The single owner of "what area does the analysis actually use" (#70, review
    2026-08-22 PB-17). Three call sites computed this integral independently --
    ``structural_speeds._wing_area_sqft``, ``validation._wing_geometry_area_sqft``
    and this module's own :func:`wing_reference` -- and the oracle GUI showed a
    fourth number entirely (``geometry.parametric.wing_area_sqft``, 18 % adrift
    on ``atr42_100``) beside a widget claiming to be the one STRSPEED reads.
    A displayed number that is not the governing number is worse than no number,
    so the resolution lives in one place and both the calc and the widget read it.

    ``None`` means *there is no such planform to integrate*: no geometry slice,
    or no surface of that name -- the condition under which
    ``speeds.wing_area_sqft`` stops being an ignored copy and becomes the
    fallback the analysis really uses.

    A surface that exists but cannot be integrated (fewer than two strips, a
    degenerate chord) **raises**, as it always has: it is a half-entered
    planform, and answering ``None`` there would send STRSPEED to a typed
    fallback the user believes is inert -- a wrong number in place of a visible
    error. Callers that only want to display something (the GUI mark,
    ``validation``) catch it themselves; the crash-vs-not-ready reporting of
    that raise is #71's, not this function's.
    """
    geom = project.geometry
    if geom is None:
        return None
    surf = geom.by_name(surface_name)
    if surf is None:
        return None
    from .modules.wing_geometry import surface_properties
    total_in2 = next(v.value for v in surface_properties(surf).values
                     if v.key == "total_area")
    return total_in2 / IN2_PER_FT2


def planform_aspect_ratio(yroot: float, ytip: float, area_per_side: float,
                          symmetric: bool) -> float:
    """``AR = b^2 / S`` from a planform strip integral — **the one spelling** (OV-5).

    ``b`` is the full span (``2*ytip`` for a symmetric surface, ``ytip - yroot``
    for a single-sided one) and ``S`` the matching area (both sides for a
    symmetric surface). Until note 36 this formula lived independently in
    ``wing_geometry.surface_properties`` and ``airloads.schrenk_distribution``;
    both now call here, and the h-tail's ``aspect_ratio_wing`` falsy-derives
    through :func:`wing_aspect_ratio` rather than growing a third spelling.
    """
    if symmetric:
        return (2.0 * ytip) ** 2 / (2.0 * area_per_side)
    return (ytip - yroot) ** 2 / area_per_side


def wing_aspect_ratio(project: Project, surface_name: str = "wing") -> Optional[float]:
    """The project wing's planform aspect ratio, or ``None`` when absent (OV-5).

    The derivation owner ``geometry.empennage.htail.aspect_ratio_wing``
    falsy-derives from (note 36, OV-2): the WINGGEOM strip integral's own AR,
    read from :func:`~sloads.modules.wing_geometry.surface_properties` so it is
    the number the wing analysis itself reports. ``None`` when there is no
    geometry slice, no such surface, or the planform cannot be integrated —
    the consumer then refuses on the still-blank input rather than dividing
    by zero (``select.py``'s downwash divides by ARW).
    """
    geom = project.geometry
    surf = geom.by_name(surface_name) if geom is not None else None
    if surf is None:
        return None
    from .modules.wing_geometry import surface_properties
    try:
        return next(v.value for v in surface_properties(surf).values
                    if v.key == "aspect_ratio")
    except (ValueError, ZeroDivisionError):
        return None


def wing_span_in(project: Project, surface_name: str = "wing") -> Optional[float]:
    """The project wing's full planform span (in), or ``None`` when absent.

    The derivation owner for ``geometry.empennage.vtail.wing_span_in`` (SELECT
    B), which falsy-derives from it (#95, C210-3): the WINGGEOM strip
    integral's own span, read from
    :func:`~sloads.modules.wing_geometry.surface_properties` so it is the
    number the wing analysis itself reports (the C210 build saw the typed
    copy disagree with it, 440 vs 441 in). Same shape and same reasons as
    :func:`wing_aspect_ratio` above.
    """
    geom = project.geometry
    surf = geom.by_name(surface_name) if geom is not None else None
    if surf is None:
        return None
    from .modules.wing_geometry import surface_properties
    try:
        return next(v.value for v in surface_properties(surf).values
                    if v.key == "span")
    except (ValueError, ZeroDivisionError):
        return None


def _edge_chord(surf: SurfaceInput, y: float) -> float:
    """Local chord (in) at butt line ``y`` from the edge polylines."""
    from .modules.wing_geometry import interp_x
    return interp_x(surf.trailing_edge, y) - interp_x(surf.leading_edge, y)


def taper_ratio_from_planform(surf: SurfaceInput) -> Optional[float]:
    """TAU's taper ratio — tip chord / centreline (root) chord — from the
    surface's own edge polylines (note 36, OV-2; C210-31).

    The derivation owner ``aero.surfaces[].taper_ratio`` falsy-derives from: the
    chords at the polylines' shared inboard-most and outboard-most butt lines.
    ``None`` when the planform is not integrable or the root chord is
    degenerate — the consumer's ``value or derive`` then leaves the typed 0.0
    in place, which is today's (pointed-wing) behaviour on a planform that
    cannot answer. A genuinely pointed wing derives 0.0 from its own polylines,
    so a blank is never load-bearing (OV-1).
    """
    try:
        require_integrable_planform(surf)
    except ValueError:
        return None
    y_root = max(surf.leading_edge[0][1], surf.trailing_edge[0][1])
    y_tip = min(surf.leading_edge[-1][1], surf.trailing_edge[-1][1])
    if y_tip <= y_root:
        return None
    c_root = _edge_chord(surf, y_root)
    c_tip = _edge_chord(surf, y_tip)
    if c_root <= 0.0 or c_tip < 0.0:
        return None
    return c_tip / c_root


def tip_ratio_from_planform(surf: SurfaceInput) -> Optional[float]:
    """TAU's rounded-tip ratio — tip-cap width / semi-span — from geometry
    (note 36, OV-4).

    The polylines end square by construction, so the rounding is carried by the
    surface's own ``tip_cap_width_in`` (entered once with the wing, 0 = square
    tip) and ``aero.surfaces[].tip_ratio`` falsy-derives as that width over the
    semi-span. ``None`` only when the planform has no span to divide by; a
    square tip derives 0.0, which is exactly the blank field's old meaning.
    """
    if len(surf.leading_edge) < 2 or len(surf.trailing_edge) < 2:
        return None
    y_root = max(surf.leading_edge[0][1], surf.trailing_edge[0][1])
    y_tip = min(surf.leading_edge[-1][1], surf.trailing_edge[-1][1])
    semi_span = y_tip if surf.symmetric else y_tip - y_root
    if semi_span <= 0.0:
        return None
    return float(surf.tip_cap_width_in) / semi_span


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


# --------------------------------------------------------------------------- #
# The %MAC <-> fuselage-station relation (#80, C210-13)
# --------------------------------------------------------------------------- #
# ``X = XLEMAC + (pct/100)*MAC`` (Reference 1 Ch 3) was spelled three times with
# three different answers to the prior question -- *which* XLEMAC and MAC:
# WTENV's private ``_xlemac_mac`` preferred the typed ``envelope.xlemac``/``mac``
# override and fell back to the planform; the report's envelope-corner table
# inverted the relation over :func:`wing_reference`, which reads the planform and
# ignores the override; and the sidebar %MAC tool (#80) would have been a fourth.
# So a project that typed an override got a CG-limit *line* drawn from it and a
# ``% MAC`` *column* drawn from the planform, on the same chart. One resolver and
# one relation now serve all of them; the drift guard is
# ``tests/test_derived_geometry.py``'s scan for a second spelling.
class MacReference(NamedTuple):
    """Where a %MAC is measured from: the MAC leading-edge station and the MAC.

    ``source`` is ``"override"`` when the pair came from the typed
    ``envelope.xlemac``/``mac`` and ``"planform"`` when it came from the WINGGEOM
    surface -- the C210-13 blank-derive fallback, which nothing on the page
    states. It is carried so a display can say which it used rather than leaving
    the reader to guess why a station moved.
    """
    xlemac: float           # fuselage station of the MAC leading edge (in)
    mac: float              # mean aerodynamic chord (in)
    source: str             # "override" | "planform"
    surface_name: str


def mac_reference(project: Project,
                  env: Optional[WeightEnvelopeInput] = None,
                  surface_name: Optional[str] = None) -> Optional[MacReference]:
    """The XLEMAC/MAC a %MAC is measured against, or ``None`` when unresolvable.

    The one resolution chain (C210-13): an explicit ``envelope.xlemac`` *and*
    ``envelope.mac`` win; otherwise the WINGGEOM planform of the envelope's
    ``wing_surface``. ``env`` defaults to ``project.weight.envelope`` so a caller
    that does not hold one still honours the override; pass it explicitly when
    running an envelope input that is not the one on the project (the report's
    figure builder does).
    """
    if env is None:
        weight = project.weight
        env = weight.envelope if weight is not None else None
    if surface_name is None:
        surface_name = env.wing_surface if env is not None else "wing"
    if env is not None and env.xlemac is not None and env.mac is not None:
        return MacReference(env.xlemac, env.mac, "override", surface_name)
    ref = wing_reference(project, surface_name)
    if ref is None:
        return None
    return MacReference(ref.xlemac, ref.mac, "planform", surface_name)


def require_mac_reference(project: Project,
                          env: Optional[WeightEnvelopeInput] = None,
                          surface_name: Optional[str] = None) -> MacReference:
    """:func:`mac_reference`, or a refusal naming both ways to supply it."""
    ref = mac_reference(project, env, surface_name)
    if ref is None:
        raise MissingInputError(
            "this analysis needs the wing XLEMAC/MAC a %MAC is measured from: add "
            f"the {wf.BY_KEY['configuration_layout'].title} wing surface (they are "
            "read from the planform) or set envelope.xlemac and envelope.mac.")
    return ref


def pct_mac_to_station(pct: float, ref: MacReference) -> float:
    """Fuselage station (in) of a percentage of MAC: ``X = XLEMAC + pct/100*MAC``."""
    return ref.xlemac + pct / 100.0 * ref.mac


def station_to_pct_mac(station_in: float, ref: MacReference) -> float:
    """Percentage of MAC of a fuselage station -- the inverse of
    :func:`pct_mac_to_station`. Undefined on a degenerate (zero) MAC, which
    :func:`mac_reference` cannot return from a planform but a typed override can,
    so a zero MAC yields 0.0 rather than dividing by it."""
    if not ref.mac:
        return 0.0
    return (station_in - ref.xlemac) / ref.mac * 100.0


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
