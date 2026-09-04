"""The oracle report's analysis sections, built from ``ModuleResult`` values.

Design note 44, OR-8 iteration 2. :mod:`sloads.report.oracle_content` owns the
document's *structure* -- which sections exist, what state each is in, how they
are numbered. This module owns their *content*: one builder per step key,
turning the result the analysis already produced into
:class:`sloads.report.content.Section` tables and figures. Each future OR-8
iteration adds a builder here rather than growing the structure module without
limit.

**Nothing here computes.** OR-6 makes the report a view: every number it prints
is a value some module returned, reproduced without re-derivation. The only
arithmetic is unit conversion and the ULTIMATE boundary, and neither is done
here either -- :func:`sloads.units.convert_results` and
:func:`sloads.report.render.to_ultimate` are their owners, and both are asked
rather than re-implemented. That is what makes G-OR-4 hold by construction: this
module never decides what a load is, so it cannot mark a load factor as one.

**Section 2 states no load in force or moment units.** Its load factors *are*
loads -- n is a limit load factor, and calling it otherwise is the error this
paragraph used to make (owner, 2026-08-30) -- but they are dimensionless and
LIMIT, so the ultimate boundary passes them through unscaled, as it does the
geometry, mass and speeds beside them. The tables are still routed through that
boundary rather than formatted by hand, because a section that formats its own
numbers is one that will eventually format a load it should have marked.

**Known upstream oddity, filed not yet fixed** (note 44 §10): a
``ConditionResult`` holding no load value still carries ``safety_factor = 1.5``,
because that is the dataclass default. No value is affected -- the boundary
scales by units and quantity, not by the stamp -- but a wing span has no safety
factor, and the owner has ruled that such a condition shall carry ``None``,
rendered "N/A". Until that lands, this module never prints a condition's SF, so
no section 2 table can inherit a claim that does not apply to it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..constants import ULTIMATE_FACTOR
from ..derived_geometry import MacReference, mac_reference, station_to_pct_mac
from ..models import Project
from ..models.enums import AnalysisKind
from ..models.results import ConditionResult, LoadValue, ModuleResult
from ..units import UnitSystem, convert_results
from .content import Figure, PlotData, Section, Series, Table, Units, speed_altitude_plot_data, weight_cg_plot_data
from .oracle_content import (
    WING_LOAD_STATIONS,
    SectionPlan,
    appendix_ref,
    section_ref,
    subsection_ref,
)
from .render import format_value, to_ultimate, ultimate_units


# --------------------------------------------------------------------------- #
# Reading a result
# --------------------------------------------------------------------------- #
def _conditions(result: Optional[ModuleResult],
                system: UnitSystem) -> List[ConditionResult]:
    """``result``'s conditions in the document's unit system.

    :func:`sloads.units.convert_results` is the single conversion owner and
    keys off the value's own unit string and quantity hint, so this module needs
    no unit table of its own. Imperial is the identity, which is why an Imperial
    report is byte-for-byte unaffected by the conversion path existing.
    """
    if result is None:
        return []
    return list(convert_results(list(result.conditions), system))


def _find(conditions: Sequence[ConditionResult], prefix: str,
          ) -> Optional[ConditionResult]:
    """The first condition whose title starts with ``prefix``."""
    for condition in conditions:
        if condition.title.startswith(prefix):
            return condition
    return None


def _cell(value: LoadValue) -> Tuple[str, str]:
    """``(formatted value, units)`` for one result value, through the boundary.

    ``sf=1.0``: section 2 holds no loads, so the boundary has nothing to scale.
    Passing the condition's stamped 1.5 would be indistinguishable in the output
    -- non-loads pass through either way -- and would encode a claim this section
    does not make. If a load ever reaches here the empty marking will be wrong
    and visible, which is better than a silently plausible number.
    """
    scaled = to_ultimate(value.value, value.units, value.quantity, 1.0)
    units = ultimate_units(value.units, value.quantity)
    return format_value(scaled), units


def _rows(condition: Optional[ConditionResult], *, skip: Sequence[str] = (),
          ) -> List[List[str]]:
    """``[label, value, units]`` per value, minus the keys in ``skip``."""
    if condition is None:
        return []
    rows = []
    for value in condition.values:
        if value.key in skip:
            continue
        formatted, units = _cell(value)
        rows.append([value.label, formatted, units])
    return rows


def _value_table(title: str, condition: Optional[ConditionResult], *,
                 note: str = "", skip: Sequence[str] = ()) -> Optional[Table]:
    """A plain quantity/value/units table, or ``None`` when there is nothing."""
    rows = _rows(condition, skip=skip)
    if not rows:
        return None
    return Table(title=title, columns=["Quantity", "Value", "Units"], rows=rows,
                 note=note)


def _by_key(condition: Optional[ConditionResult]) -> Dict[str, LoadValue]:
    """``{value key: value}`` for one condition."""
    if condition is None:
        return {}
    return {value.key: value for value in condition.values}


def _far_note(condition: Optional[ConditionResult]) -> str:
    """The condition's own FAR reference and note, as a sentence for the prose.

    ``far_reference`` is not always a regulation. The configuration module sets
    it to ``"configuration"`` -- a category, not a clause -- and printing that
    verbatim produced "Certification basis: 14 CFR configuration" in the first
    build of this section. A reference is a regulation only if it begins with a
    part number, and anything else is dropped rather than dressed up as one.
    """
    if condition is None:
        return ""
    parts = []
    reference = (condition.far_reference or "").strip()
    if reference[:1].isdigit():
        parts.append(f"Certification basis: 14 CFR {reference}.")
    if condition.note:
        parts.append(condition.note)
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# 2.1 Geometry
# --------------------------------------------------------------------------- #
#: The condition of ``configuration`` the report carries.
#:
#: The module also returns *Longitudinal stability (estimate)* and *Landing-gear
#: geometry (estimate)*, both of which note themselves as first-order with no
#: oracle. Neither is loads configuration, and a first-order estimate printed
#: beside oracle-locked geometry in a certification document reads as though it
#: carried the same standing. Excluded by the owner, GUI review 2026-08-30.
_GEOMETRY_CONDITION = "Wing planform"

#: ``(attribute, printed label, units)`` per surface, read from the project.
#:
#: **These are inputs, not results.** Everything else in section 2 reproduces a
#: ``ModuleResult``; no module echoes a control-surface area or a throw, so the
#: only honest source is the definition the analysis was given. Echoing an input
#: is not recomputation (OR-6 forbids re-deriving, not reporting), but the tables
#: say so in their own note, because a reader must not take an entered number for
#: a computed one.
#:
#: Declared as data so a renamed or dropped input field fails
#: ``test_oracle_report.py`` rather than silently emptying a row -- the same
#: reason ``_FACTOR_PAIRS`` and ``_SPEED_PAIRS`` are tables.
_HTAIL_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("htail_area_sqft", "Horizontal tail area", "ft^2"),
    ("aspect_ratio_htail", "Aspect ratio", ""),
    ("htail_semispan_in", "Semispan", "in"),
    ("tail_incidence_deg", "Tail incidence", "deg"),
    ("xt25", "Quarter-chord station XT25", "in"),
    ("xt50", "Half-chord station XT50", "in"),
    ("elevator_area_sqft", "Elevator area", "ft^2"),
    ("elevator_fwd_hinge_sqft", "Elevator area forward of hinge", "ft^2"),
    ("elevator_aft_hinge_sqft", "Elevator area aft of hinge", "ft^2"),
    ("elevator_te_up_deg", "Elevator deflection, trailing edge up", "deg"),
    ("elevator_te_down_deg", "Elevator deflection, trailing edge down", "deg"),
)

_VTAIL_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("vtail_area_sqft", "Vertical tail area", "ft^2"),
    ("aspect_ratio_vtail", "Aspect ratio", ""),
    ("vtail_span_in", "Span", "in"),
    ("vtail_mac_in", "MAC", "in"),
    ("xv25", "Quarter-chord station XV25", "in"),
    ("rudder_area_sqft", "Rudder area", "ft^2"),
    ("rudder_fwd_hinge_sqft", "Rudder area forward of hinge", "ft^2"),
    ("rudder_aft_hinge_sqft", "Rudder area aft of hinge", "ft^2"),
    ("rudder_deflection_deg", "Rudder deflection", "deg"),
)

_AILERON_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("area_fwd_hinge_sqft", "Aileron area forward of hinge", "ft^2"),
    ("area_aft_hinge_sqft", "Aileron area aft of hinge", "ft^2"),
    ("down_deflection_deg", "Aileron deflection, trailing edge down", "deg"),
    ("up_deflection_deg", "Aileron deflection, trailing edge up", "deg"),
)

_FLAP_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("flap_area_one_side_sqft", "Flap area, one side", "ft^2"),
    ("flap_chord_ratio", "Flap chord ratio", ""),
    ("flap_deflection_deg", "Flap deflection", "deg"),
)

_TAB_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("area_sqft", "Tab area", "ft^2"),
    ("mac_in", "Tab MAC", "in"),
    ("station_in", "Tab station", "in"),
    ("airfoil_chord_in", "Airfoil chord at the tab", "in"),
    ("deflection_deg", "Tab deflection", "deg"),
)

#: Said once, in section 2.1's prose, and never under a table.
#:
#: Six surface tables each carrying it read as boilerplate, which is how a
#: reader learns to skip the notes that matter -- the same finding that moved
#: the units note out of the tables earlier in this review.
_AS_ENTERED_SENTENCE = (
    "The empennage and control-surface values below are the configuration as "
    "entered for this analysis: they are input values, reproduced so the loads "
    "that follow can be read against the surfaces they were computed for, and "
    "they are not analysis output."
)

#: Surface key -> what the document calls it.
#:
#: ``TabInput.surface`` carries the analysis's own key ("htail"), which is our
#: machinery again -- the same reason ``DOCUMENT_TITLES`` exists one level up.
_SURFACE_NAMES = {
    "htail": "horizontal tail",
    "vtail": "vertical tail",
    "wing": "wing",
}


def _input_table(title: str, source: object,
                 rows: Sequence[Tuple[str, str, str]],
                 system: UnitSystem) -> Optional[Table]:
    """One surface's definition, echoed from the project.

    Routed through :class:`LoadValue` and
    :func:`sloads.units.convert_results` rather than formatted here, so an
    echoed input converts and marks by exactly the path a computed value takes.
    A value that is absent or ``None`` is dropped rather than printed as zero --
    an unset station is not a station at the datum.
    """
    if source is None:
        return None
    values = []
    for attr, label, units in rows:
        value = getattr(source, attr, None)
        if value is None:
            continue
        values.append(LoadValue(label=label, value=value, units=units, key=attr))
    if not values:
        return None
    condition = ConditionResult(title=title, far_reference="", values=values)
    converted = convert_results([condition], system)[0]
    return _value_table(title, converted)


#: How a tail table reports where its planform came from.
#:
#: The suite carries the empennage as **scalars** -- area and span -- because
#: that is all SELECT, TAILDIST and BALLOADS ever needed, and those scalars are
#: oracle-authoritative. A spanwise distribution needs a chord at every station,
#: which comes from an ``"htail"``/``"vtail"`` entry in ``geometry.surfaces``
#: with the same leading- and trailing-edge polylines as the wing (plan 09, T-1).
#: Where that entry is absent the planform is derived as a rectangle and marked
#: assumed.
#:
#: The report **asks** :func:`sloads.tail_geometry.resolve_tail_planform` rather
#: than asserting either state. A first draft of this section told every reader
#: that both tails were rectangles, which would have been false for a project
#: that had entered its polylines -- the document stating an assumption the
#: analysis did not make.
_PLANFORM_BASIS = {
    True: "DERIVED rectangle from area and span",
    False: "entered leading- and trailing-edge polylines",
}


def _planform_assumed(project: Project, component: str) -> bool:
    """Whether ``component``'s planform was derived rather than entered."""
    from ..tail_geometry import resolve_tail_planform

    try:
        planform = resolve_tail_planform(project, component)
    except (ValueError, AttributeError):
        return False
    return bool(planform is not None and planform.assumed)


def _tail_table(title: str, project: Project, component: str, source: object,
                rows: Sequence[Tuple[str, str, str]],
                system: UnitSystem) -> Optional[Table]:
    """A tail's definition, with the basis of its planform stated on it."""
    table = _input_table(title, source, rows, system)
    if table is None:
        return None
    from ..tail_geometry import resolve_tail_planform

    try:
        planform = resolve_tail_planform(project, component)
    except (ValueError, AttributeError):
        planform = None
    if planform is not None:
        table.rows.append(["Planform basis", _PLANFORM_BASIS[planform.assumed], ""])
    return table


#: ``(figure key, parent surface, printed title, control surfaces, frame)``.
#:
#: The three main surfaces a reader sizes to, each with the control surfaces
#: that live on it. Declared as data for the same reason ``_HTAIL_ROWS`` is: a
#: renamed surface fails ``test_oracle_report.py`` rather than silently drawing
#: a parent with nothing on it.
#:
#: The frame is not decoration. A wing or horizontal tail is entered as
#: ``(station, butt line)`` and is symmetric about the centre plane, so it is
#: drawn with its mirror; a **vertical tail's second coordinate is a waterline**
#: -- the GA6 fin root is ``(240.912, 117.0)``, station 240.912 at waterline
#: 117.0 -- and mirroring it about ``y = 0`` would draw a second fin hanging
#: below the airplane. The frame decides that, never ``SurfaceInput.symmetric``,
#: which ``examples/baron_58.project.json`` sets ``true`` on its fin.
_PLANFORM_FIGURES: Tuple[Tuple[str, str, str, Tuple[str, ...], str], ...] = (
    ("planform_wing", "wing", "Wing planform", ("aileron", "flap"), "butt"),
    ("planform_htail", "htail", "Horizontal tail planform", ("elevator",), "butt"),
    ("planform_vtail", "vtail", "Vertical tail planform", ("rudder",), "water"),
)

#: The axis labels of each frame, without units -- those are appended from the
#: converted length channel, so an SI report says mm on both axes.
#:
#: A butt-line surface is drawn **span across, station down**: a wing is 402 in
#: of span against a 101 in root chord, and on the equal axes the figure exists
#: to hold, station-across is four times taller than it is wide. The emitter
#: reverses that vertical axis (``planform_tex.NOSE_UP_KEYS``) so the stations
#: still read in the airplane's own numbers with the nose at the top.
_PLANFORM_AXES = {
    "butt": ("Butt line Y", "Fuselage station X"),
    "water": ("Fuselage station X", "Waterline Z"),
}


def _oriented(frame: str, x_in: float, y_in: float) -> Tuple[float, float]:
    """An entered ``(station, span)`` point on the frame's plotted axes."""
    return (y_in, x_in) if frame == "butt" else (x_in, y_in)

#: Surface key -> what the figure legend calls it.
#:
#: §3.3's "a surface key SHALL NOT reach a heading" for the same reason one
#: level down: a legend a reviewer reads is not a place for the analysis's own
#: identifiers.
_REGION_NAMES = {
    "wing": "Wing",
    "aileron": "Aileron",
    "flap": "Flap",
    "htail": "Horizontal tail",
    "elevator": "Elevator",
    "vtail": "Vertical tail",
    "rudder": "Rudder",
}

#: ``(surface key, project slice, attribute, printed label)`` for the area a
#: region is labelled with.
#:
#: Every one is a value 2.1 **already prints in a table**, read from the same
#: attribute, so a figure cannot label a surface with a second number for the
#: same quantity ("a number is printed once", §3.3). The wing is not here: its
#: area is produced by the speeds module and is passed in already converted.
#: Neither is the aileron -- ``AileronInput`` carries its areas forward and aft
#: of the hinge and no total, and summing them here would be the report deriving
#: a quantity no module returned (OR-6). It is drawn and named without an area.
_REGION_AREAS: Tuple[Tuple[str, str, str, str], ...] = (
    ("htail", "htail", "htail_area_sqft", "Horizontal tail"),
    ("elevator", "htail", "elevator_area_sqft", "Elevator"),
    ("vtail", "vtail", "vtail_area_sqft", "Vertical tail"),
    ("rudder", "vtail", "rudder_area_sqft", "Rudder"),
    ("flap", "flap_loads", "flap_area_one_side_sqft", "Flap, one side"),
)


def _length_channel(system: UnitSystem) -> Tuple[float, str]:
    """``(scale, units)`` taking an entered inch coordinate into ``system``.

    Asked of :func:`sloads.units.convert_results` through a probe value rather
    than multiplied by a constant here. The conversion has one owner and this
    module is not it; a hard-coded 25.4 is exactly the drift the units history
    is the cautionary precedent for.
    """
    probe = ConditionResult(title="", far_reference="",
                            values=[LoadValue("probe", 1.0, "in", key="probe")])
    converted = convert_results([probe], system)[0].values[0]
    return float(converted.value), converted.units


def _region_areas(project: Project, wing_area: Optional[LoadValue],
                  system: UnitSystem) -> Dict[str, LoadValue]:
    """The area each drawn region is labelled with, converted once."""
    empennage = getattr(project.geometry, "empennage", None) if project.geometry else None
    slices = {
        "htail": getattr(empennage, "htail", None),
        "vtail": getattr(empennage, "vtail", None),
        "flap_loads": project.flap_loads,
    }
    values = []
    for key, slice_name, attr, label in _REGION_AREAS:
        source = slices.get(slice_name)
        value = getattr(source, attr, None) if source is not None else None
        if value is None:
            continue
        values.append(LoadValue(label=label, value=value, units="ft^2", key=key))
    areas: Dict[str, LoadValue] = {}
    if values:
        condition = ConditionResult(title="", far_reference="", values=values)
        areas = {v.key: v for v in convert_results([condition], system)[0].values}
    if wing_area is not None:
        areas["wing"] = wing_area
    return areas


def _region_label(name: str, area: Optional[LoadValue]) -> str:
    """A legend entry: the surface's name, and its area where one is tabulated."""
    printed = _REGION_NAMES.get(name, name)
    if area is None:
        return printed
    formatted, units = _cell(area)
    return f"{printed}: {formatted} {units}".strip()


def _region_series(project: Project, name: str, style: str, label: str,
                   mirror: bool, frame: str, scale: float) -> List[Series]:
    """One surface as closed outlines: the entered side, and its mirror.

    The outline itself comes from :func:`sloads.modules.wing_geometry.surface_top_outline`,
    which is already the shared "edge polylines -> closed outline" owner for the
    two GUI pages that draw a planform. The report asks it rather than walking
    the polylines again, so the document and the pages cannot disagree about
    where a surface ends.

    The mirror carries no name, so it is drawn ``forget plot`` and takes no
    legend entry of its own -- it is the same surface, not a second one.
    """
    from ..derived_geometry import require_integrable_planform
    from ..modules.wing_geometry import surface_top_outline

    surface = project.geometry.by_name(name) if project.geometry else None
    if surface is None:
        return []
    # The same precondition every other consumer of an edge polyline asks
    # (#71/PB-21, ``derived_geometry`` is its one owner). A half-entered
    # planform -- one point on an edge, or a repeated butt line -- is the state
    # the curve editor persists mid-row, and a figure drawn from it is a shape
    # nobody entered rather than an obviously broken one. The ``ValueError`` is
    # caught by the caller into a stated absence: G-OR-7 says a half-filled
    # project still builds a complete document.
    require_integrable_planform(surface)
    outlines = surface_top_outline(surface.leading_edge, surface.trailing_edge,
                                   mirror)
    series = []
    for index, (xs, ys) in enumerate(outlines):
        oriented = [_oriented(frame, x * scale, y * scale)
                    for x, y in zip(xs, ys)]
        series.append(Series(label if index == 0 else "",
                             [x for x, _y in oriented],
                             [y for _x, y in oriented], style, closed=True))
    return series


def _planform_figure(project: Project, key: str, parent: str, title: str,
                     children: Sequence[str], frame: str,
                     areas: Mapping[str, LoadValue],
                     system: UnitSystem) -> Figure:
    """One surface's to-scale planform, with its control surfaces on it."""
    from .planform_tex import OUTLINE_STYLE, REGION_STYLES

    printed = _REGION_NAMES.get(parent, parent)
    surface = project.geometry.by_name(parent) if project.geometry else None
    if surface is None:
        # Stated, never an empty axis (§3.4). For a tail this is the same state
        # the table above reports as a DERIVED planform: the rectangle the
        # analysis assumes is not a shape worth drawing, and drawing it would
        # give the assumption the standing of entered geometry.
        derived = (" The table above reports its planform DERIVED for the same "
                   "reason." if _planform_assumed(project, parent) else "")
        return Figure(
            key=key, title=title,
            absent_reason=(
                f"the project defines no {printed.lower()} leading- and "
                "trailing-edge polylines, so there is no planform to draw."
                + derived))

    scale, length_units = _length_channel(system)
    mirror = bool(surface.symmetric) and frame == "butt"
    try:
        series = _region_series(project, parent, OUTLINE_STYLE,
                                _region_label(parent, areas.get(parent)),
                                mirror, frame, scale)
    except ValueError as problem:
        # The precondition owner's refusal, in the document's own voice. Not a
        # traceback and not a drawing: G-OR-7 keeps the report buildable over a
        # half-filled project, and §3.4 makes it say what is missing.
        return Figure(key=key, title=title,
                      absent_reason=(f"the {printed.lower()} planform cannot be "
                                     f"drawn as entered -- {problem}"))
    drawn = []
    # ``zip`` stops at the shorter: a parent grown a third control surface would
    # lose it silently, so ``test_oracle_report.py`` holds every spec's child
    # count against the number of fills there are to tell them apart with.
    for child, style in zip(children, REGION_STYLES):
        try:
            child_series = _region_series(project, child, style,
                                          _region_label(child, areas.get(child)),
                                          mirror, frame, scale)
        except ValueError:
            # A control surface mid-entry costs the reader the shading, not the
            # parent's planform, which is the figure they came for.
            continue
        if child_series:
            drawn.append(child)
            series += child_series

    x_label, y_label = _PLANFORM_AXES[frame]
    entered = list(surface.leading_edge) + list(surface.trailing_edge)
    if mirror:
        entered += [(x, -y) for x, y in entered]
    points = [("",) + _oriented(frame, x * scale, y * scale)
              for x, y in entered]

    caption = [
        f"The {printed.lower()} as entered, drawn to scale on equal axes: the "
        "outline is the leading- and trailing-edge polylines the analysis "
        "integrated, and the marked points are the entered vertices.",
    ]
    if drawn:
        names = [_REGION_NAMES.get(c, c).lower() for c in drawn]
        named = (names[0] if len(names) == 1
                 else ", ".join(names[:-1]) + " and " + names[-1])
        caption.append(f"The {named} is shaded on it." if len(names) == 1
                       else f"The {named} are shaded on it.")
    caption.append(
        "Areas are the values tabulated above, not measured off the drawing. "
        "Nothing here is a load: no value is scaled to ultimate and none "
        "carries a safety factor.")
    if mirror:
        caption.append("The surface is symmetric about the airplane centre "
                       "plane and both sides are drawn.")
    caption.append(
        "The hinge line is not drawn: the analysis carries the control "
        "surface's areas forward and aft of the hinge as scalars and no hinge "
        "geometry, so a line here would be an inference rather than the "
        "configuration.")

    return Figure(
        key=key, title=title,
        data=PlotData(f"{x_label} ({length_units})",
                      f"{y_label} ({length_units})", series, points),
        caption=" ".join(caption))


def _geometry(project: Project,
              results: Mapping[str, Optional[ModuleResult]], *,
              system: UnitSystem,
              plan: Sequence[SectionPlan]) -> Section:  # noqa: ARG001
    conditions = _conditions(results.get("configuration_layout"), system)
    planform = _find(conditions, _GEOMETRY_CONDITION)

    # Wing area is produced by structural_speeds, not by the geometry module,
    # but it is geometry and this is where a reader looks for it. Taken from the
    # producing result rather than recomputed, and omitted from the section 2.3
    # table so the document states it once.
    speeds = _conditions(results.get("structural_speeds"), system)
    area = _by_key(_find(speeds, "Structural design speeds")).get("wing_area_s")

    table = _value_table("Wing planform geometry", planform)
    if table is not None and area is not None:
        formatted, units = _cell(area)
        table.rows.append([area.label, formatted, units])

    body = [
        "The wing planform the spanwise loads of the following sections are "
        "distributed over. The mean aerodynamic chord and its leading-edge "
        "station are the strip integrations of the planform itself, not "
        "closed-form approximations to it.",
    ]
    far = _far_note(planform)
    if far:
        body.append(far)
    body.append(
        "The empennage and control surfaces follow, with the areas and control "
        "deflections the analysis was given. " + _AS_ENTERED_SENTENCE)
    if any(_planform_assumed(project, component)
           for component in ("htail", "vtail")):
        body.append(
            "Where a tail table below states a DERIVED planform, that surface "
            "has no entered leading- and trailing-edge polylines and is treated "
            "as a rectangle of its stated area and span. A tapered surface "
            "carries its load further inboard, so the root bending reported "
            "later is conservative, while the station-by-station distribution "
            "is not the surface's own. Entering the polylines removes the "
            "assumption.")

    empennage = getattr(project.geometry, "empennage", None) if project.geometry else None
    tables = [table]
    tables.append(_tail_table("Horizontal tail and elevator", project, "htail",
                              getattr(empennage, "htail", None),
                              _HTAIL_ROWS, system))
    tables.append(_tail_table("Vertical tail and rudder", project, "vtail",
                              getattr(empennage, "vtail", None),
                              _VTAIL_ROWS, system))
    tables.append(_input_table("Aileron", project.aileron_loads,
                               _AILERON_ROWS, system))
    tables.append(_input_table("Flap", project.flap_loads, _FLAP_ROWS, system))
    for tab in getattr(project.tab_loads, "tabs", ()) or ():
        key = (getattr(tab, "surface", "") or "").strip()
        surface = _SURFACE_NAMES.get(key, key)
        tables.append(_input_table(
            f"Trim tab, {surface}" if surface else "Trim tab",
            tab, _TAB_ROWS, system))

    # One planform per main surface (OR-45). The renderer puts a section's
    # figures ahead of its tables, so the three drawings open 2.1 and the tables
    # that state their numbers follow -- the reader sees the airplane before the
    # arithmetic, which is the order the section was asked for in.
    areas = _region_areas(project, area, system)
    figures = [_planform_figure(project, key, parent, figure_title, children,
                                frame, areas, system)
               for key, parent, figure_title, children, frame in _PLANFORM_FIGURES]
    return Section("", body=body, figures=figures,
                   tables=[t for t in tables if t is not None])


# --------------------------------------------------------------------------- #
# 2.2 Weight and mass properties
# --------------------------------------------------------------------------- #
#: The order analyses are listed in, so a set never reaches the page unsorted.
#:
#: ``CgCase.analyses`` is a ``set`` by design (G-3), and set iteration order is
#: not a document property. Printing it directly would put the determinism gates
#: G-OR-5 and G-OR-16 at the mercy of hash ordering.
_ANALYSIS_ORDER = (AnalysisKind.FLIGHT, AnalysisKind.GROUND)

#: What the role and analysis columns of the CG-case table mean.
_CG_CASE_NOTE = (
    "ANALYSIS is which load families a case is carried into. A flight case "
    "feeds the V-n envelope, the balancing tail loads and the selected design "
    "cases; a ground case feeds the landing and ground-handling families "
    "(14 CFR 23.471-23.511). The two are separate governing families and are "
    "never compared for a maximum. A case may carry both tags. "
    "ROLE applies to ground cases only: the landing-load analysis takes exactly "
    "three loadings and indexes them by position, so the role states which of "
    "the three a case supplies -- aft max landing, forward max landing or "
    "forward light -- rather than leaving it to be recovered from the case "
    "name. A further ground case carrying no role is assembled and distributed "
    "but is not one of the three fed to the landing analysis. "
    "Weight and centre of gravity are the case as entered."
)


def _pct_mac_note(ref: MacReference, u: Units) -> str:
    """The relation the %MAC column applies, and the reference it applies it to.

    Stated rather than assumed: a %MAC is meaningless without the XLEMAC and MAC
    it is measured from, and this suite resolves that pair two ways (a typed
    ``envelope.xlemac``/``mac`` override, else the wing planform of 2.1). A
    reader checking a station against the entered CG limits -- which are given
    in %MAC -- needs to know which pair produced the column and be able to
    invert it, so both forms of the relation are printed.
    """
    length = u.label("length")
    where = ("the entered XLEMAC and MAC, which override the planform"
             if ref.source == "override"
             else f"the {ref.surface_name} planform stated in 2.1")
    return (
        "Xcg (% MAC) is that same station expressed in percent of the mean "
        "aerodynamic chord -- a change of reference, not a second analysis: "
        "%MAC = 100 (X - XLEMAC) / MAC, and inverted, "
        "X = XLEMAC + (%MAC / 100) MAC. Here XLEMAC = "
        f"{u.plain(ref.xlemac, 'length')} {length} and MAC = "
        f"{u.plain(ref.mac, 'length')} {length}, from {where}. The CG limits "
        "drawn in the figure below are entered in %MAC and are converted to "
        "stations through the same relation and the same pair, so a case and a "
        "limit on this page are always measured from one reference."
    )


def _cg_case_table(project: Project, system: UnitSystem) -> Optional[Table]:
    """The weight and CG cases analysed, one row each."""
    weight = project.weight
    cases = list(getattr(weight, "cg_cases", ()) or ()) if weight else []
    if not cases:
        return None
    u = Units(system)
    # The one resolver (C210-13) -- never a second reading of the planform
    # here. A degenerate MAC is treated as unresolved rather than divided by:
    # ``station_to_pct_mac`` answers 0.0 on it, which would print a column of
    # zeroes that looks like an answer.
    ref = mac_reference(project)
    if ref is not None and not ref.mac:
        ref = None
    rows = []
    for case in cases:
        analyses = [kind.value for kind in _ANALYSIS_ORDER
                    if kind in (case.analyses or ())]
        role = getattr(case, "role", None)
        rows.append([
            case.name or "unnamed",
            role.value.replace("_", " ") if role is not None else "--",
            u.plain(case.weight_lb, "mass"),
            u.plain(case.xcg, "length"),
            # ``case.xcg`` is internal inches and a percentage is dimensionless,
            # so this converts once, through the relation's owner, and not again.
            format_value(station_to_pct_mac(case.xcg, ref)) if ref else "--",
            u.plain(case.zcg, "length"),
            ", ".join(analyses) or "--",
        ])
    length = u.label("length")
    note = _CG_CASE_NOTE
    note += (" " + _pct_mac_note(ref, u) if ref is not None else
             " Xcg is not stated in %MAC: neither an entered XLEMAC and MAC nor "
             "a wing planform to read them from is present, so there is no "
             "reference to measure a percentage against.")
    return Table(
        title="Weight and centre-of-gravity cases",
        columns=["Case", "Role", f"Weight ({u.label('mass')})",
                 f"Xcg ({length})", "Xcg (% MAC)", f"Zcg ({length})",
                 "Analysis"],
        rows=rows, note=note)


#: What the weight/CG figure states about itself, beyond the caption.
#:
#: G-OR-4: section 2 marks nothing ultimate and states no safety factor. A
#: weight and a station are not load quantities, so the sentence is a statement
#: of fact rather than a disclaimer -- but it is stated, because this is the one
#: figure in section 2 whose axes carry pounds.
_ENVELOPE_NOTE = (
    "The two loading envelopes are the discretionary items of the weight data "
    "base added cumulatively, most-forward first and most-aft first, from the "
    "minimum flight weight. Both begin at that weight and end at the same "
    "full loading, so together they close the envelope of every loading the "
    "airplane can physically hold. The structural limit envelope is the "
    "entered CG limits: constant at the forward-regardless station below the "
    "reduced weight, linear in weight to the forward-gross station at gross "
    "weight, and constant at the aft-gross station. A loading vertex outside "
    "that envelope is expected and is not a defect -- the limits bound the "
    "loadings that may be flown, not those that can be loaded. Weights, "
    "stations and waterlines are not load quantities: nothing here is scaled "
    "to ultimate and no safety factor applies."
)


#: ``(printed edge name, condition-title prefix, LoadValue key prefix)``.
#:
#: WTENV publishes the forward edge under the keys it has carried since the
#: module was written and the aft edge -- added by design note 45 -- under an
#: ``aft_`` prefix, so the two stay distinguishable wherever conditions are
#: flattened together. Declared as data and guarded against the module's own
#: keys, so a renamed key fails the suite instead of silently emptying the table.
_ENVELOPE_EDGES = (("Forward", "Forward loading envelope", "point"),
                   ("Aft", "Aft loading envelope", "aft_point"))


def _envelope_vertex_table(result: Optional[ModuleResult],
                           system: UnitSystem) -> Optional[Table]:
    """The plotted vertices, numbered as the figure numbers them.

    The figure marks vertices and the table names their coordinates; a reader
    checking a corner against a number should not have to measure it off an
    axis. Read from WTENV's own ``ModuleResult`` (G-OR-3) rather than swept
    here. Which *item* each vertex adds is not stated because the analysis does
    not carry it -- see the note below the table.
    """
    conditions = _conditions(result, system)
    u = Units(system)
    rows = []
    for edge, title, prefix in _ENVELOPE_EDGES:
        condition = _find(conditions, title)
        if condition is None:
            continue
        by_index: Dict[int, Dict[str, float]] = {}
        for value in condition.values:
            parts = (value.key or "").rsplit("_", 1)
            stem, field = (parts + [""])[:2]
            if not stem.startswith(f"{prefix}_"):
                continue
            try:
                index = int(stem[len(prefix) + 1:])
            except ValueError:
                continue
            by_index.setdefault(index, {})[field] = value.value
        for index in sorted(by_index):
            cell = by_index[index]
            if not {"weight", "station"} <= set(cell):
                continue
            waterline = cell.get("waterline")
            # ``_conditions`` has already converted to the document's system,
            # so these format only -- ``u.plain`` would convert a second time.
            # The vertex names itself ("Forward 4") rather than carrying a bare
            # ordinal in its own column: an ordinal is not a quantity, and a
            # column of naked integers beside three of measurements invites the
            # reader to read one as the other.
            rows.append([f"{edge} {index}", format_value(cell["weight"]),
                         format_value(cell["station"]),
                         format_value(waterline) if waterline is not None
                         else "--"])
    if not rows:
        return None
    length = u.label("length")
    return Table(
        title="Loading envelope vertices",
        columns=["Vertex", f"Weight ({u.label('mass')})",
                 f"Station ({length})", f"Waterline ({length})"],
        rows=rows,
        note="Vertex 1 is the minimum flight weight on both edges; each "
             "subsequent vertex adds one discretionary item, in fuselage-station "
             "order. The item added at a vertex is not stated: the analysis "
             "reports the cumulative weight and centre of gravity, not the "
             "loading behind them. The items and their stations are listed in "
             "the weight data base above, in the order the vertices follow.",
    )


def _weight_cg_figure(project: Project, system: UnitSystem) -> Figure:
    """Section 2.2's weight/CG envelope -- both edges, limits, entered cases."""
    data = weight_cg_plot_data(project, Units(system))
    if data is None:
        return Figure(
            "weight_cg", "Weight and centre-of-gravity envelope",
            absent_reason="this airplane has no itemized weight data base, so "
                          "there are no loadings to sweep and no envelope to draw",
        )
    marked = (" Each entered weight and centre-of-gravity case is marked; two "
              "cases at the same weight and station share one marker and both "
              "names." if data.points else "")
    limits = ("" if any(s.name == "Structural limits" for s in data.series)
              else " No structural limit envelope is drawn: the CG limits are "
                   "not entered for this airplane.")
    return Figure(
        "weight_cg", "Weight and centre-of-gravity envelope",
        data=data,
        caption="Weight against centre-of-gravity station for every loading of "
                "the weight data base, with the structural limit envelope."
                + marked + limits,
    )


def _weights(project: Project,
             results: Mapping[str, Optional[ModuleResult]], *,
             system: UnitSystem,
             plan: Sequence[SectionPlan]) -> Section:  # noqa: ARG001
    conditions = _conditions(results.get("weight_mass"), system)
    tables = []
    for condition in conditions:
        # The module's condition title names the analysis ("...for one
        # loading"), which is our machinery describing itself. With a single
        # loading the document says what the table *is*; with several, the
        # condition title is the only thing that tells them apart and is kept.
        title = ("Mass properties" if len(conditions) == 1
                 else f"Mass properties -- {condition.title}")
        table = _value_table(title, condition)
        if table is not None:
            tables.append(table)
    cases = _cg_case_table(project, system)
    if cases is not None:
        tables.append(cases)
    vertices = _envelope_vertex_table(results.get("weight_envelope"), system)
    if vertices is not None:
        tables.append(vertices)

    body = [
        "The weight, centre of gravity and mass moments of inertia of each "
        "loading analysed. The inertias are stated twice, in slug-ft^2 and in "
        "lb-in^2, because the two conventions are both current and a factor of "
        "12^2 between them is not a difference a reader should have to detect. "
        "The principal-axis set and its inclination follow; the angle is "
        "measured up from the waterline and aft from the centre of gravity.",
        _ENVELOPE_NOTE,
    ]
    far = _far_note(conditions[0] if conditions else None)
    if far:
        body.append(far)
    return Section("", body=body, tables=tables,
                   figures=[_weight_cg_figure(project, system)])


# --------------------------------------------------------------------------- #
# 2.3 Structural design speeds
# --------------------------------------------------------------------------- #
#: ``(printed name, as-computed key, FAR-minimum key)`` for the paired tables.
#:
#: The pairing is the section's whole point: a design speed or a limit load
#: factor means nothing to a reviewer without the regulation's floor beside it.
#: Declared as data and guarded against the module's own value keys, so a
#: renamed or dropped result key fails the suite instead of silently emptying a
#: compliance column.
_FACTOR_PAIRS: Tuple[Tuple[str, str, str], ...] = (
    ("Positive limit manoeuvre load factor", "limit_positive_load_factor",
     "minimum_required_positive_factor"),
    ("Negative limit manoeuvre load factor", "limit_negative_load_factor",
     "minimum_required_negative_factor"),
)

_SPEED_PAIRS: Tuple[Tuple[str, str, str], ...] = (
    ("Design manoeuvring speed VA", "maneuver_speed_va", "minimum_maneuver_va_min"),
    ("Design cruising speed VC", "cruise_speed_vc", "minimum_cruise_vc_min"),
    ("Design dive speed VD", "dive_speed_vd", "minimum_dive_vd_min"),
    ("Design flap speed VF", "flap_speed_vf", "minimum_flap_vf_min"),
)


def _paired_table(title: str, condition: Optional[ConditionResult],
                  pairs: Sequence[Tuple[str, str, str]]) -> Optional[Table]:
    """As-computed beside the regulation's minimum, one row per pair.

    No verdict column: whether a value complies is the reviewer's finding, and a
    generator that printed "complies" would be asserting a conclusion it is not
    the authority for. The two numbers side by side are the evidence.
    """
    values = _by_key(condition)
    rows = []
    for name, computed_key, minimum_key in pairs:
        computed = values.get(computed_key)
        minimum = values.get(minimum_key)
        if computed is None:
            continue
        formatted, units = _cell(computed)
        floor = _cell(minimum)[0] if minimum is not None else ""
        rows.append([name, formatted, floor, units])
    if not rows:
        return None
    # A units column every row leaves blank is dropped rather than printed
    # empty. The limit manoeuvre load factors are the case that found this: n
    # is dimensionless -- the section body says so, and "g" would name an
    # acceleration this table does not state -- so the column carried nothing
    # but the suggestion that a unit had gone missing. Done here rather than at
    # the one table, so any dimensionless pairing added later behaves the same.
    if not any(row[3] for row in rows):
        return Table(title=title,
                     columns=["Quantity", "As computed", "FAR 23 minimum"],
                     rows=[row[:3] for row in rows])
    return Table(title=title,
                 columns=["Quantity", "As computed", "FAR 23 minimum", "Units"],
                 rows=rows)


def _speeds(project: Project,  # noqa: ARG001
            results: Mapping[str, Optional[ModuleResult]], *,
            system: UnitSystem,
            plan: Sequence[SectionPlan]) -> Section:  # noqa: ARG001
    conditions = _conditions(results.get("structural_speeds"), system)
    factors = _find(conditions, "Limit maneuver load factors")
    speeds = _find(conditions, "Structural design speeds")
    mach = _find(conditions, "Cruise/dive Mach")

    # Everything the paired table already states, plus the wing area printed in
    # section 2.1 -- so no number appears in two tables.
    paired_keys = [key for _n, a, b in _SPEED_PAIRS for key in (a, b)]
    tables = [
        _paired_table("Limit manoeuvre load factors", factors, _FACTOR_PAIRS),
        _value_table("Wing loading", factors,
                     skip=[key for _n, a, b in _FACTOR_PAIRS for key in (a, b)]),
        _paired_table("Structural design speeds", speeds, _SPEED_PAIRS),
        _value_table("Cruise and dive Mach numbers", mach),
    ]
    if speeds is not None:
        leftover = _value_table("Design speed reference values", speeds,
                                skip=paired_keys + ["wing_area_s"])
        if leftover is not None:
            tables.append(leftover)

    body = [
        "The limit manoeuvre load factors and structural design speeds the "
        "flight envelope is built on, each stated beside the minimum 14 CFR "
        "Part 23 Subpart C requires of it. Speeds are equivalent airspeeds; "
        "load factors are dimensionless and are LIMIT values.",
    ]
    far = _far_note(speeds)
    if far:
        body.append(far)
    return Section("", body=body, tables=[t for t in tables if t is not None])


# --------------------------------------------------------------------------- #
# 2.4 Flight envelope
# --------------------------------------------------------------------------- #
#: The envelope boundary, in traversal order, by the case names FLTLOADS emits.
#:
#: These nine cases are the boundary itself; the balance, rolling and asymmetric
#: cases the same module produces sit inside it and belong to the load-case
#: section. The order is a closed traversal from the 1 g stall up the positive
#: boundary, across the dive line and back along the negative one -- guarded
#: against the module's own emission order, so this declaration cannot come to
#: disagree with the analysis about which way the envelope goes.
_BOUNDARY_CASES: Tuple[str, ...] = (
    "STALL 1G", "STALL +N", "MAN A", "MAN C", "MAN D",
    "MAN -D", "MAN -C", "STALL -N", "STALL -1G",
)

#: The gust cases, drawn as marked points rather than joined into the boundary.
#:
#: They are separate design points, not vertices of the manoeuvre envelope, and
#: joining them would draw a boundary the analysis never computed.
_GUST_CASES: Tuple[str, ...] = ("GUST +C", "GUST +D", "GUST -D", "GUST -C")

#: ``(printed name, case name, value key)`` of the corner table's columns.
_CORNERS: Tuple[Tuple[str, str], ...] = (
    ("n+ at VA", "MAN A"),
    ("n+ at VD", "MAN D"),
    ("n- at VC", "MAN -C"),
    ("n- at VD", "MAN -D"),
)

#: The reference speeds drawn as vertical lines, by structural_speeds' keys.
_ENVELOPE_VLINES: Tuple[Tuple[str, str], ...] = (
    ("VA", "maneuver_speed_va"),
    ("VC", "cruise_speed_vc"),
    ("VD", "dive_speed_vd"),
)


#: How every V-n diagram in 2.4 is constructed -- stated once, above them.
#:
#: It was each figure's caption until 2026-08-31, which printed the same three
#: sentences under four figures that differ only in their loading. A caption
#: distinguishes a figure; this describes all of them, so it belongs to the
#: subsection and the caption line is left carrying the block name alone.
_VN_CONSTRUCTION = (
    "Each boundary is drawn through the design points the analysis computed and "
    "is curved between them: the stall boundary follows the section lift curve "
    "and the compressibility correction, not a constant-CLmax parabola. Gust "
    "points are design points in their own right and are not vertices of the "
    "manoeuvre boundary. Load factors are LIMIT and dimensionless."
)


def _split_case(title: str) -> Tuple[str, str]:
    """``"CRUISE CG1 @ 0 ft, case 3: MAN A"`` -> ``("CRUISE CG1 @ 0 ft", "MAN A")``.

    Returns ``("", "")`` for a title that is not a case, so a module that grows
    a summary condition does not become a phantom envelope block.
    """
    block, _, rest = title.partition(", case ")
    if not rest:
        return "", ""
    _number, _, name = rest.partition(": ")
    return (block, name) if name else ("", "")


def _blocks(conditions: Sequence[ConditionResult],
            ) -> List[Tuple[str, Dict[str, ConditionResult]]]:
    """The envelope's loading/altitude blocks, in order, each keyed by case name."""
    order: List[str] = []
    found: Dict[str, Dict[str, ConditionResult]] = {}
    for condition in conditions:
        block, case = _split_case(condition.title)
        if not block:
            continue
        if block not in found:
            order.append(block)
            found[block] = {}
        found[block][case] = condition
    return [(block, found[block]) for block in order]


def _point(condition: ConditionResult) -> Optional[Tuple[float, float]]:
    """``(V, n)`` for one case, or ``None`` when either is missing."""
    values = _by_key(condition)
    speed = values.get("v_eas")
    factor = values.get("load_factor_nz")
    if speed is None or factor is None:
        return None
    return float(speed.value), float(factor.value)


def _envelope_figure(block: str, cases: Mapping[str, ConditionResult],
                     vlines: Sequence[Tuple[str, float]], index: int) -> Figure:
    """One block's V-n diagram: boundary polyline, gust points, speed lines."""
    boundary = [_point(cases[name]) for name in _BOUNDARY_CASES if name in cases]
    joined = [p for p in boundary if p is not None]
    series = []
    if joined:
        # Closed: back to the first vertex, so the envelope reads as a boundary
        # rather than an open path that happens to end near where it began.
        closed = joined + [joined[0]]
        series.append(Series("Manoeuvre and stall boundary",
                             [v for v, _n in closed], [n for _v, n in closed],
                             "solid"))
    points = []
    for name in _GUST_CASES:
        condition = cases.get(name)
        if condition is None:
            continue
        point = _point(condition)
        if point is not None:
            points.append((name, point[0], point[1]))
    # No caption. What the four V-n figures would each say is the same sentence
    # about the same construction, and a caption repeated once per loading is
    # not a caption but a refrain -- it is stated once in the subsection body
    # (:data:`_VN_CONSTRUCTION`) instead. The block is in the title, which is
    # what distinguishes one figure from another and all the caption line needs
    # to carry (owner, 2026-08-31).
    return Figure(
        key=f"vn_{index}",
        title=f"Flight envelope -- {block}",
        data=PlotData("V (KEAS)", "Load factor n", series, points, list(vlines),
                      points_label="Gust design points"),
    )


def _corner_table(blocks: Sequence[Tuple[str, Dict[str, ConditionResult]]],
                  ) -> Optional[Table]:
    """The manoeuvre corner load factors, one row per block."""
    rows = []
    for block, cases in blocks:
        row = [block]
        for _name, case in _CORNERS:
            condition = cases.get(case)
            point = _point(condition) if condition is not None else None
            row.append(format_value(point[1]) if point is not None else "")
        rows.append(row)
    if not rows:
        return None
    return Table(
        title="Manoeuvre envelope corner load factors",
        columns=["Loading and altitude"] + [name for name, _c in _CORNERS],
        rows=rows,
        note="Dimensionless LIMIT load factors, read from the design cases "
             "plotted above. The negative boundary closes to zero at the dive "
             "speed (14 CFR 23.333(d)), so the n- at VD column is that closure "
             "point and is zero to within the solution tolerance of the balance "
             "it was found by; it is reproduced as computed rather than "
             "rounded.")


#: ``(printed name, MACHLIM value key)`` of the speed/altitude table's columns.
#:
#: Guarded against the module's own keys, so a renamed key empties the table in
#: the suite rather than on the page.
_MACH_LIMIT_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("V(MC) cruise", "v_mc"),
    ("V(MNE) never-exceed", "v_mne"),
    ("V(MD) dive", "v_md"),
)


def _speed_altitude_figure(project: Project) -> Figure:
    """2.4's first figure: the operating envelope in speed and altitude.

    Placed ahead of the V-n diagrams because it is the envelope the V-n
    diagrams are cut from: each one is a slice at a stated altitude, and the
    speeds their boundaries run to are the speeds this figure draws.

    One builder, shared with the summary report (OR-7) --
    :func:`sloads.report.content.speed_altitude_plot_data`.
    """
    data = speed_altitude_plot_data(project)
    if data is None:
        return Figure(
            "speed_altitude", "Speed and altitude envelope",
            absent_reason="this airplane has no Mach-limited boundary -- no "
                          "MACHLIM inputs are entered, so the operating envelope "
                          "is bounded by the design speeds of 2.3 alone",
        )
    return Figure(
        "speed_altitude", "Speed and altitude envelope",
        data=data,
        caption="The operating envelope from sea level to the maximum operating "
                "altitude. Each boundary is constant in equivalent airspeed below "
                "the shoulder altitude and Mach-limited above it, so the kink in "
                "each line is the shoulder. Vh is marked at sea level, where it is "
                "entered: it is the maximum level-flight speed, not a limit, and "
                "the analysis carries no altitude variation of it. Speeds are "
                "equivalent airspeeds and are LIMIT design speeds; nothing here "
                "is scaled to ultimate.",
    )


def _mach_limit_table(result: Optional[ModuleResult],
                      system: UnitSystem) -> Optional[Table]:
    """The plotted speed/altitude boundaries, from MACHLIM's own result.

    The figure's numeric corners (SS 4.3), read rather than re-derived (G-OR-3).
    Only the Mach-limited rows are tabulated: below the shoulder each speed is
    its shoulder value held constant, which the note states rather than the
    table repeating it as though it were a further computed row.
    """
    rows = []
    units = ""
    for condition in _conditions(result, system):
        values = _by_key(condition)
        if "altitude" not in values:
            continue
        row = [format_value(values["altitude"].value)]
        for _name, key in _MACH_LIMIT_COLUMNS:
            value = values.get(key)
            row.append(format_value(value.value) if value is not None else "")
            if value is not None and not units:
                units = value.units
        rows.append(row)
    if not rows:
        return None
    speed = f" ({units})" if units else ""
    return Table(
        title="Mach-limited speeds by altitude",
        columns=["Altitude (ft)"] + [f"{name}{speed}"
                                     for name, _key in _MACH_LIMIT_COLUMNS],
        rows=rows,
        note="The Mach-limited half of the figure above, from the shoulder "
             "altitude to the maximum operating altitude. Below the shoulder "
             "each boundary is constant in equivalent airspeed at its value in "
             "the first row, which is what the shoulder altitude is: the "
             "altitude at which an EAS limit becomes a Mach limit. MNE = 0.9 MD "
             "(Ch 6). These are LIMIT design speeds.",
    )


def _envelope(project: Project,
              results: Mapping[str, Optional[ModuleResult]], *,
              system: UnitSystem,
              plan: Sequence[SectionPlan]) -> Section:
    conditions = _conditions(results.get("flight_envelope"), system)
    blocks = _blocks(conditions)

    speeds = _by_key(_find(_conditions(results.get("structural_speeds"), system),
                           "Structural design speeds"))
    vlines = [(name, float(speeds[key].value))
              for name, key in _ENVELOPE_VLINES if key in speeds]

    # The speed/altitude envelope opens the subsection: the V-n diagrams that
    # follow are slices of it, and a reader meets the envelope before its cuts.
    figures = [_speed_altitude_figure(project)]
    figures += [_envelope_figure(block, cases, vlines, index)
                for index, (block, cases) in enumerate(blocks)]
    table = _corner_table(blocks)
    mach = _mach_limit_table(results.get("mach_limit"), system)

    cases_ref = section_ref(plan, "flight_envelope_cases")
    body = [
        "The operating envelope in speed and altitude, and then the flight "
        "envelope itself, one diagram per loading and altitude analysed. "
        "Each diagram shows the manoeuvre and stall boundary of that "
        "condition together with the gust design points at the cruise and dive "
        "speeds, against the design speeds of the preceding section.",

        _VN_CONSTRUCTION,

        "The design cases selected on these envelopes -- the speed, load factor, "
        "attitude and balance of each condition carried into the component load "
        f"analyses -- are tabulated in {cases_ref}.",
    ]
    far = _far_note(conditions[0] if conditions else None)
    if far:
        body.append(far)
    return Section("", body=body, figures=figures,
                   tables=[t for t in (mach, table) if t is not None])


# --------------------------------------------------------------------------- #
# Section 3 -- Wing Loads (OR-48 ... OR-56)
# --------------------------------------------------------------------------- #
#: The step whose result this section reports, named once.
_WING_STEP = "wing_loads"

#: Positions of the subsections other prose points at, so a cross-reference is
#: composed from the numbering owner rather than typed as "3.1" (F-R2).
_WING_INPUTS = 0
_WING_CASES = 1
_WING_ASSESSED = 2
_WING_DISTRIBUTIONS = 3


def _load_cell(value: LoadValue, sf: float) -> Tuple[str, str]:
    """``(formatted value, ULT units)`` for one **load**, through the boundary.

    :func:`_cell`'s sibling, and deliberately a separate function rather than a
    parameter on it. Section 2 passes ``sf=1.0`` because it holds no loads and a
    factor there would encode a claim it does not make (OR-44); section 3 holds
    nothing but loads and every one of them is delivered ULTIMATE at its own
    case's factor (OR-49). Two callers, two statements, no default to get wrong.
    """
    scaled = to_ultimate(value.value, value.units, value.quantity, sf)
    return format_value(scaled), ultimate_units(value.units, value.quantity)


def _wing_net(project: Project) -> List[object]:
    """The net wing load distributions, transferred to the surface's LRA.

    Asked of ``net_loads``' own builders -- the same pair the Export page and the
    summary report call -- so the section, the appendix and the exported deck
    describe one set of numbers. Returns ``[]`` rather than raising: G-OR-7 keeps
    a half-filled project building a complete document, and the callers turn an
    empty list into a stated absence.
    """
    from ..modules.net_loads import build_net_loads, loads_ref_axis_results

    try:
        net = build_net_loads(project)
        return list(loads_ref_axis_results(project, net.wing_net))
    except Exception:
        return []


def _torsion_axis(results: Sequence[object]) -> str:
    """What the distributions' torsion is stated about, from the results."""
    return str(getattr(results[0], "torsion_axis", "")) if results else ""


def _wing_surface_name(project: Project) -> str:
    """The surface the wing-load chain runs on, as WINGINER names it."""
    return getattr(project.wing_mass, "surface", "wing") or "wing"


_LRA_NOTE = (
    "The loads reference axis (LRA) is the chordwise line every distributed "
    "load in this section is stated about: the shears and bending moments are "
    "unaffected by the choice, and the torsion is not. The replicated "
    "programs accumulate torsion about the local 25 per cent chord, so for the "
    "oracle the LRA is the quarter chord; in this suite the axis is entered per "
    "surface, and the torsion is transferred to it at the delivery boundary by "
    "Myy(LRA) = Myy(25%) + Sz (X(LRA) - X(25%)). The table gives the axis "
    "point at each load station and the figure draws it on the planform, so the "
    "axis a torsion is measured about can be read off the airplane rather than "
    "assumed."
)


def _lra_station_table(net: Sequence[object],
                       system: UnitSystem) -> Optional[Table]:
    """The loads reference axis, station by station.

    The axis coordinates are the transferred results' own station points -- the
    transform's output, not a second reading of the planform (OR-6). Coordinates
    are geometry: nothing here is scaled to ultimate and nothing is marked.
    """
    if not net:
        return None
    stations = list(getattr(net[0], "stations", ()))
    if not stations:
        return None
    u = Units(system)
    length = u.label("length")
    rows = [[str(index), u.plain(s.y, "length"), u.plain(s.x, "length"),
             u.plain(s.z, "length")]
            for index, s in enumerate(stations, start=1)]
    axis = _torsion_axis(net)
    return Table(
        title=f"Loads reference axis by station ({axis})",
        columns=["Station", f"Butt line Y ({length})",
                 f"Station X on the axis ({length})", f"Waterline Z ({length})"],
        rows=rows,
        note=("The stations are the load stations the air-load and inertia "
              "distributions are evaluated at, root to tip. These are "
              "coordinates, not loads: nothing in this table is scaled to "
              "ultimate and nothing carries a safety factor."))


def _lra_planform_figure(project: Project, net: Sequence[object],
                         system: UnitSystem) -> Figure:
    """The wing planform with its loads reference axis drawn on it."""
    from .planform_tex import LRA_STYLE, OUTLINE_STYLE

    key, title = "planform_wing_lra", "Wing loads reference axis"
    name = _wing_surface_name(project)
    surface = project.geometry.by_name(name) if project.geometry else None
    if surface is None:
        return Figure(key=key, title=title,
                      absent_reason=("the project defines no wing planform, so "
                                     "there is no surface to draw an axis on."))
    if not net:
        return Figure(key=key, title=title,
                      absent_reason=("the wing load distributions were not "
                                     "produced, so the axis they are stated "
                                     "about cannot be drawn."))
    scale, length_units = _length_channel(system)
    mirror = bool(surface.symmetric)
    try:
        series = _region_series(project, name, OUTLINE_STYLE, "Wing planform",
                                mirror, "butt", scale)
    except ValueError as problem:
        return Figure(key=key, title=title,
                      absent_reason=("the wing planform cannot be drawn as "
                                     f"entered -- {problem}"))
    axis = _torsion_axis(net)
    stations = list(getattr(net[0], "stations", ()))
    points = [_oriented("butt", s.x * scale, s.y * scale) for s in stations]
    series.append(Series(f"Loads reference axis ({axis})" if axis
                         else "Loads reference axis",
                         [x for x, _y in points], [y for _x, y in points],
                         LRA_STYLE))
    if mirror:
        series.append(Series("", [-x for x, _y in points],
                             [y for _x, y in points], LRA_STYLE))
    x_label, y_label = _PLANFORM_AXES["butt"]
    return Figure(
        key=key, title=title,
        data=PlotData(f"{x_label} ({length_units})",
                      f"{y_label} ({length_units})", series,
                      [("", x, y) for x, y in points]),
        caption=("The wing as entered, with the loads reference axis of this "
                 f"analysis ({axis}) drawn through the load stations every "
                 "distributed load in this section is stated at. The marked "
                 "points are those stations. Nothing in this figure is a load."))


#: The wing lift coefficients the span load is drawn at, and how each is named.
#:
#: ``None`` means *the airplane's own CLmax*, taken from the aero set's
#: ``stall_cl`` rather than typed here: a span load drawn to a constant somebody
#: chose would be a plot of this module's opinion (OR-52).
_SPAN_LOAD_CASES: Tuple[Tuple[str, Optional[float]], ...] = (
    ("CL = 0 (basic distribution)", 0.0),
    ("CL = 1.0", 1.0),
    ("CL = CLmax", None),
)

_SPAN_LOAD_STYLES = ("dotted", "solid", "dashed")


def _wing_aero_row(project: Project):
    """The aero input row the wing's span load is built from, or ``None``."""
    from ..models import same_name
    from ..modules.airloads import resolve_aero_surfaces

    name = _wing_surface_name(project)
    try:
        rows = resolve_aero_surfaces(project)
    except Exception:
        return None
    for row in rows:
        if same_name(row.name, name):
            return row
    return None


def _span_load_figure(project: Project, clmax: Optional[float],
                      system: UnitSystem) -> Figure:
    """``c*cl`` along the span at the three reference lift coefficients.

    Each curve is AIRLOADS' own distribution evaluated at a target ``CL`` -- the
    report calls the owner once per coefficient rather than combining the
    additive and basic parts itself, which is what keeps a three-curve figure
    inside OR-6.

    **These are LIMIT.** A span load at a target ``CL`` is an input to the load
    cases below, not a delivered load, so it is neither scaled nor marked -- and
    it says so, because a figure in a section whose every other number is
    ULTIMATE must not leave the reader to assume which kind this is (OR-49).
    """
    from dataclasses import replace as _replace

    from ..modules.airloads import schrenk_distribution

    key, title = "wing_span_load", "Wing span loading (LIMIT)"
    name = _wing_surface_name(project)
    surface = project.geometry.by_name(name) if project.geometry else None
    aero = _wing_aero_row(project)
    if surface is None or aero is None:
        return Figure(key=key, title=title,
                      absent_reason=("the project carries no wing planform and "
                                     "aerodynamic row to distribute a lift "
                                     "coefficient over."))
    u = Units(system)
    series: List[Series] = []
    for (label, target), style in zip(_SPAN_LOAD_CASES, _SPAN_LOAD_STYLES):
        cl = clmax if target is None else target
        if cl is None:
            continue
        try:
            table = schrenk_distribution(surface, _replace(aero, target_cl=cl))
        except Exception:
            continue
        printed = (label if target is not None
                   else f"CL = CLmax = {format_value(cl)}")
        series.append(Series(
            printed,
            [u.plain_value(y, "length") for y in table.ye],
            [u.plain_value(v, "length") for v in table.ccl_total], style))
    if not series:
        return Figure(key=key, title=title,
                      absent_reason=("the wing span load could not be "
                                     "distributed from the planform and "
                                     "aerodynamic data as entered."))
    length = u.label("length")
    return Figure(
        key=key, title=title,
        data=PlotData(f"Butt line Y ({length})", f"Span load c*cl ({length})",
                      series),
        caption=("The Schrenk span load along the semi-span at three wing lift "
                 "coefficients: the basic distribution alone, which carries no "
                 "net lift but is not zero locally; unit CL; and the airplane's "
                 "own CLmax. This is span load c*cl, not running load -- it is "
                 "the shape the air load is distributed to, and it is an input "
                 "to the cases below. All three curves are LIMIT: no safety "
                 "factor is applied to any of them."))


def _flaps_down_span_load(project: Project) -> Figure:
    """The flaps-down span load -- stated absent, with the reason (OR-53)."""
    flaps = getattr(project.aero_coeffs, "flaps_down", None)
    entered = (" This project enters no flaps-down aerodynamic set either."
               if flaps is None else "")
    return Figure(
        key="wing_span_load_flaps",
        title="Wing span loading, flaps down (LIMIT)",
        absent_reason=(
            "the air-load distribution does not model the lift discontinuity a "
            "deflected flap puts in the basic distribution, so a flaps-down "
            "span load is not produced by this analysis at all." + entered))


#: ``(figure key, title, curve attribute, points attribute, y label)`` for the
#: two airplane-coefficient figures 3.1 carries.
_AERO_CURVE_FIGURES: Tuple[Tuple[str, str, str, str, str], ...] = (
    ("aero_cl_alpha", "Airplane-less-tail lift coefficient (LIMIT)",
     "lift", "cl", "CL"),
    ("aero_cm_alpha", "Airplane-less-tail pitching moment (LIMIT)",
     "moment", "cm", "CM"),
)


def _aero_curves(project: Project):
    """``(curves, config)`` for the cruise configuration, or ``(None, None)``.

    Built through :mod:`sloads.aero_curves` -- the single authority the FLTLOADS
    balance itself evaluates -- and overlaid with the balanced points that
    balance produced, so the curve and the points on it cannot come from two
    readings of the same polynomial.
    """
    from ..aero_curves import build_aero_curves, operating_points
    from ..derived_geometry import wing_reference
    from ..modules.flight_envelope import build_envelope

    config = getattr(project.aero_coeffs, "cruise", None)
    if config is None:
        return None, None
    points = None
    try:
        reference = wing_reference(project, _wing_surface_name(project))
        if reference is not None:
            points = operating_points(build_envelope(project), config.name,
                                      wing_area_sqft=reference.s_sqft,
                                      mac_in=reference.mac)
    except Exception:
        points = None
    return build_aero_curves(config, points=points), config


def _aero_curve_figure(curves, config, key: str, title: str,
                       curve_attr: str, point_attr: str, y_label: str) -> Figure:
    """One coefficient curve, with the balanced operating points on it."""
    if curves is None:
        return Figure(key=key, title=title,
                      absent_reason=("the project carries no airplane-less-tail "
                                     "aerodynamic coefficients, so there is no "
                                     "curve to draw."))
    trace = getattr(curves, curve_attr)
    series = [Series(f"Airplane less tail, as entered ({config.name})",
                     list(trace.x), list(trace.y), "solid")]
    points = curves.points
    marked = ([("", a, v) for a, v in zip(points.alpha_deg,
                                          getattr(points, point_attr))]
              if points is not None and len(points) else [])
    return Figure(
        key=key, title=title,
        data=PlotData("Angle of attack (deg)", y_label, series, marked,
                      points_label="Balanced envelope points (tail on)"),
        caption=(
            "The entered coefficient curve of the airplane less its horizontal "
            "tail -- the tail-off data the flight balance solves against -- "
            "with every balanced condition marked on it. A marked point is the "
            "tail-on solution at that angle of attack, recovered from the "
            "point's own dimensional output rather than from a second "
            "evaluation of the polynomial: it sits on the curve because the "
            "balance carries the tail load as a separate force rather than "
            "inside this coefficient, and any visible departure is the "
            "compressibility correction at that point's Mach. The tail load "
            "itself is a load and is reported with the tail. Coefficients are "
            "dimensionless and are stated LIMIT; nothing in this figure is "
            "scaled or marked ultimate."))


def _wing_inputs(project: Project, *, system: UnitSystem,
                 plan: Sequence[SectionPlan]) -> Section:
    """3.1 -- the wing data the load cases were run from."""
    net = _wing_net(project)
    curves, config = _aero_curves(project)
    clmax = getattr(config, "stall_cl", None) or None
    figures = [_lra_planform_figure(project, net, system),
               _span_load_figure(project, clmax, system),
               _flaps_down_span_load(project)]
    figures += [_aero_curve_figure(curves, config, *spec)
                for spec in _AERO_CURVE_FIGURES]
    table = _lra_station_table(net, system)
    body = [
        "This subsection states the wing data the load cases of this section "
        "were run from: the axis the loads are stated about, the span load the "
        "air load is distributed to, and the airplane lift and moment "
        "coefficients the flight cases were balanced against. The planform "
        "itself is stated in " + section_ref(plan, "configuration_layout")
        + " and is not repeated here.",

        "The coefficients are the airplane less its horizontal tail, which "
        "is the form the balance requires and the form the aerodynamic data "
        "was produced in. The tail-on airplane is the balanced solution at each "
        "condition: the same angle of attack with the balancing tail load "
        "carried as a separate force, which is why the balanced conditions are "
        "marked on the tail-off curve rather than drawn as a second curve. "
        "This analysis publishes no tail-on lift coefficient of its own.",
        _LRA_NOTE,
        "The span loading and the coefficient curves below are inputs to the "
        "load cases and are stated LIMIT. Every load case in the rest of this "
        "section is delivered ULTIMATE. Both kinds carry the label wherever "
        "they are printed, so no number in this section leaves its basis to be "
        "inferred.",
    ]
    return Section("", body=body, figures=figures,
                   tables=[t for t in (table,) if t is not None])


def _sign_note(plan: Sequence[SectionPlan]) -> str:
    """The axes and sign statement, with its own cross-reference composed."""
    return (
        "Loads are stated in airplane axes, and both moments are stated about "
        "the loads reference axis given in "
        + subsection_ref(plan, _WING_STEP, _WING_INPUTS) + ". The symbols, "
        "their units and whether each is an applied increment or a cumulative "
        "load are tabulated below; the full sign convention is the "
        "analysis-wide one and is not restated per section.")


def _cg_weight(project: Project, name: str) -> Optional[float]:
    """The entered weight of the CG case ``name`` (OR-46: as entered, labelled)."""
    for case in list(getattr(project.weight, "cg_cases", ()) or ()):
        if case.name == name:
            return case.weight_lb
    return None


#: What the sign of the register's load factors means.
#:
#: Not a footnote. ``Nz`` here is the **inertia** load factor -- the negative of
#: the airplane's flight load factor, because the inertia opposes the air load
#: (``wing_inertia._resolve_case``: ``Nz = -NZ``) -- so a +3.8 g manoeuvre is
#: printed as -3.8. A reader who does not know that reads a table of positive-g
#: conditions as a table of negative ones, which is exactly what happened in the
#: owner's review of this section (2026-09-03).
_LOAD_FACTOR_SIGN = (
    "Nz is the inertia load factor, which opposes the air load and is therefore "
    "the negative of the airplane's flight load factor: a case printed at "
    "Nz = -3.8 is a +3.8 g condition. Nx is the inertia drag factor on the same "
    "convention.")


def _negative_case_sentence(net: Sequence[object]) -> str:
    """Whether the analysed set contains a negative-flight-load-factor case.

    A wing is enveloped by its positive *and* its negative conditions -- FAR
    23.333(c)'s negative manoeuvre and the negative gust reverse the bending the
    positive cases produce. A set holding only positive-g cases does not envelop
    the wing, and on the printed sign convention that is not visible at a glance:
    every load factor in the table is a negative number either way. So it is
    stated (OR-58).
    """
    if not net:
        return ""
    # Inertia Nz < 0 is a positive-g condition; > 0 is a negative-g one.
    negative = [r for r in net if float(getattr(r, "nz", 0.0)) > 0.0]
    if negative:
        names = ", ".join(getattr(r, "case", "") for r in negative)
        return (f"The set includes {len(negative)} negative-load-factor "
                f"condition{'' if len(negative) == 1 else 's'} ({names}), which "
                "reverse the bending the positive cases produce.")
    return (
        "Every case run here is a positive-load-factor condition. The set holds "
        "no negative-load-factor case, so the distributions in this section do "
        "not envelop the wing: the negative manoeuvre and negative gust "
        "conditions of 14 CFR 23.333(c), which reverse the bending, are not "
        "among them.")


def _wing_selection(project: Project):
    """``(SELECT's wing conditions, the V-n matrix it searched)``, or ``([], None)``.

    The selection is asked for even when it is overridden, because *whether it was
    overridden* is a fact the register has to state (OR-57): a section that
    presents three entered cases as the outcome of a search is describing an
    analysis nobody ran.
    """
    from ..modules.flight_envelope import build_envelope
    from ..modules.select import build_critical

    try:
        conditions = [c for c in build_critical(project).conditions
                      if getattr(c, "component", "") == "wing"]
    except Exception:
        conditions = []
    try:
        envelope = build_envelope(project)
    except Exception:
        envelope = None
    return conditions, envelope


def _matrix_sentence(envelope) -> str:
    """What the V-n matrix the selection searched actually enumerates.

    The reader's question this answers is a real one: a V-n diagram states a
    speed and a load factor and says nothing about weight, centre of gravity or
    altitude, so the set of *points* behind it has to be described or the
    selection looks like it ran on twenty conditions rather than on every
    combination of them.
    """
    if envelope is None or not envelope.vn:
        return ("The balanced V-n matrix the selection searches was not "
                "produced for this project.")
    points = envelope.vn
    configs = sorted({p.config for p in points})
    cgs = sorted({p.cg for p in points})
    altitudes = sorted({p.altitude_ft for p in points})
    conditions = len({p.condition for p in points})
    altitude_text = (f"the single altitude {format_value(altitudes[0])} ft"
                     if len(altitudes) == 1
                     else "the altitudes "
                          + ", ".join(f"{format_value(a)} ft" for a in altitudes))
    return (
        f"The selection searches the balanced V-n matrix: {len(points)} points, "
        f"every combination of {len(configs)} configuration"
        f"{'' if len(configs) == 1 else 's'} "
        f"({', '.join(configs)}), {len(cgs)} weight and centre-of-gravity "
        f"case{'' if len(cgs) == 1 else 's'} ({', '.join(cgs)}), "
        f"{altitude_text}, and {conditions} flight conditions. A V-n diagram "
        "states a speed and a load factor and nothing about loading or "
        "altitude; the matrix behind it carries all three, and it is the matrix "
        "that is searched.")


def _selection_table(conditions: Sequence[object],
                     run: Sequence[str]) -> Optional[Table]:
    """Every wing condition the selection names, and whether it was run.

    Printed whether or not the two agree, because the case a section does *not*
    carry is the one a reader has no other way of finding.
    """
    if not conditions:
        return None
    rows = []
    for condition in conditions:
        ref = getattr(condition, "case_ref", None)
        label = getattr(condition, "label", "")
        rows.append([
            getattr(ref, "case_id", "") or "--",
            label or "--",
            getattr(ref, "far_reference", "") or "--",
            str(getattr(condition, "case", "") or "--"),
            getattr(ref, "cg", "") or "--",
            "yes" if label in run else "no",
        ])
    return Table(
        title="Critical wing conditions named by the selection",
        columns=["Case", "Condition", "14 CFR", "V-n point", "CG case",
                 "Run here"],
        rows=rows,
        note=("The governing wing condition of each FAR family, as the "
              "critical-load selection found it in the V-n matrix. A condition "
              "marked 'no' is named by the selection and is not carried into "
              "the wing analysis of this project, because the project enters "
              "its own wing case list and an entered list is used as entered."))


def _wing_case_table(project: Project, net: Sequence[object],
                     system: UnitSystem) -> Optional[Table]:
    """3.2's run register: one row per selected wing case."""
    if not net:
        return None
    u = Units(system)
    rows = []
    for result in net:
        ref = getattr(result, "case_ref", None)
        cg = getattr(ref, "cg", "") or ""
        weight = _cg_weight(project, cg)
        rows.append([
            getattr(ref, "case_id", "") or "--",
            getattr(result, "case", "") or "--",
            getattr(ref, "far_reference", "") or "--",
            cg or "--",
            u.plain(weight, "mass") if weight is not None else "--",
            format_value(getattr(ref, "speed_kt", 0.0) or 0.0),
            format_value(getattr(ref, "altitude_ft", 0.0) or 0.0),
            format_value(getattr(result, "nz", 0.0)),
            format_value(getattr(result, "nx", 0.0)),
        ])
    return Table(
        title="Wing load cases run",
        columns=["Case", "Condition", "14 CFR", "CG case",
                 f"Weight ({u.label('mass')})", "V (KEAS)", "Altitude (ft)",
                 "Nz", "Nx"],
        rows=rows,
        note=("The cases carried into the wing analysis, each with the loading "
              "it was run at and the paragraph of 14 CFR Part 23 it is required "
              "by. Speed is equivalent airspeed and altitude is feet: both are "
              "aviation standard in either unit system and are never converted. "
              "The weight is the CG case as entered. "
              + _LOAD_FACTOR_SIGN
              + " Nz and Nx are LIMIT and dimensionless, and the loads they "
              "produce are delivered ULTIMATE below."))


def _provenance_sentence(entered: bool, named: Sequence[str],
                         run: Sequence[str], missing: Sequence[str]) -> str:
    """Where the analysed case list came from -- selection, or entry (OR-57).

    Two different statements, and the report may not make the first while the
    second is true. An entered list is legitimate and is sometimes necessary --
    the selection names a condition but not the unbalanced rolling moment an
    accelerated-roll case needs, which only an entered case can carry -- but it
    is the project's list, not the selection's, and the difference is the
    reader's to see (OR-46's rule, applied to a case set rather than a value).
    """
    if not entered:
        return ("The cases below are the critical-load selection's own result: "
                "the governing condition of each FAR family, taken from the "
                "matrix without further choice.")
    sentence = (
        "The cases below are the wing case list entered in this project, not "
        "the selection's own result. An entered list is used exactly as "
        "entered, and it is what the loads were computed from. It exists "
        "because a condition can carry data the selection does not name -- an "
        "accelerated-roll case needs an unbalanced rolling moment, which comes "
        "from the aileron analysis and not from the V-n matrix.")
    if missing:
        sentence += (
            " The selection names "
            f"{len(named)} governing wing conditions and {len(run)} "
            f"{'is' if len(run) == 1 else 'are'} carried here; "
            f"{', '.join(missing)} "
            f"{'is' if len(missing) == 1 else 'are'} named and not run, and "
            "the table below states which is which.")
    return sentence


#: The symbols section 3 uses, in the order a reader meets them: the point
#: first, then what is applied at it, then what the structure carries there.
#:
#: A table rather than a sentence because the distinction the section turns on
#: -- which quantities are per-strip increments and which are running totals --
#: is a property of each symbol, and prose that carries it for ten symbols at
#: once is prose nobody checks a column heading against (owner review,
#: 2026-09-03).
_NOMENCLATURE: Tuple[Tuple[str, str, str, str], ...] = (
    ("X", "Station, positive aft along the fuselage reference line",
     "length", "coordinate"),
    ("Y", "Butt line, positive outboard on the starboard wing",
     "length", "coordinate"),
    ("Z", "Waterline, positive up", "length", "coordinate"),
    ("Fz", "Normal force applied at the station", "force", "increment"),
    ("Fx", "Chordwise force applied at the station", "force", "increment"),
    ("Myy free", "Free torsion applied at the station", "moment", "increment"),
    ("Sz", "Normal shear carried across the station", "force", "cumulative"),
    ("Sx", "Chordwise shear carried across the station", "force", "cumulative"),
    ("Mxx", "Bending moment about X", "moment", "cumulative"),
    ("Myy", "Torsion carried across the station", "moment", "cumulative"),
)


def _nomenclature_table(net: Sequence[object], system: UnitSystem) -> Table:
    """The symbols of section 3, each stated as increment or cumulative.

    The one owner of the distinction: a column heading anywhere in section 3 or
    its appendix names a symbol from this table and nothing else.
    """
    u = Units(system)
    axis = _torsion_axis(net) or "loads reference axis"
    rows = [[symbol, quantity, u.label(dim), sense]
            for symbol, quantity, dim, sense in _NOMENCLATURE]
    return Table(
        title="Notation", columns=["Symbol", "Quantity", "Units", "Sense"],
        rows=rows,
        note=("An increment is the load applied at that station alone. A "
              "cumulative value is the load the structure carries there: the "
              "sum of everything outboard of it, accumulated from the tip "
              f"inboard. Both moments are stated about the {axis}. "
              "Coordinates are geometry -- they are neither scaled to ultimate "
              "nor marked."))


def _derivation_note(net: Sequence[object]) -> str:
    """How the cumulative loads are built from the applied ones.

    Written out because the appendix is a deck: a reader assembling a structural
    model from it has to know which of these terms the model will generate for
    itself, and there is no way to tell that from the column headings alone.
    """
    axis = _torsion_axis(net) or "loads reference axis"
    reference = appendix_ref(WING_LOAD_STATIONS)
    tail = (f" That is why {reference} tabulates Fz, Fx and Myy free at each "
            "station's own point rather than the differences of the cumulative "
            "columns: the differences are mostly transfer, and a model given "
            "them would count it twice.") if reference else ""
    return (
        "The cumulative loads are the applied loads summed from the tip "
        "inboard. Writing i for a station, i+1 for the station outboard of it "
        f"and dy for the strip width, all moments about the {axis}:\n"
        "  Sz(i) = Sz(i+1) + Fz(i)\n"
        "  Sx(i) = Sx(i+1) + Fx(i)\n"
        "  Mxx(i) = Mxx(i+1) + Sz(i+1) dy\n"
        "  Myy(i) = Myy(i+1) - Sz(i+1) [X(i+1) - X(i)] + Sx(i+1) [Z(i+1) - "
        "Z(i)] + Myy free(i)\n\n"
        "The two terms carrying Sz and Sx into Myy, and the term carrying Sz "
        "into Mxx, are position transfers -- the shear already carried at the "
        "station, moved across the sweep, dihedral and span of the bay. They "
        "are not applied loads, and a structural model generates them itself "
        "from its own geometry. Only Myy free is applied." + tail)


def _point_load_note(net: Sequence[object]) -> str:
    """How a concentrated wing mass enters, stated only where there is one."""
    if not any(getattr(r, "point_loads", ()) for r in net):
        return ""
    return (
        "A concentrated wing mass -- an engine, a gear leg, fuel, a store -- is "
        "not part of any strip. It applies a point force at its own X, Y and Z, "
        "and enters the cumulative loads of every station inboard of it: Fz and "
        "Fx into the shears, and their moments about that station's axis into "
        "Mxx and Myy. It carries no free moment of its own, because every "
        "moment it produces is that force acting through an arm the geometry "
        "already states.")


def _wing_cases(project: Project, *, system: UnitSystem,
                plan: Sequence[SectionPlan]) -> Section:
    """3.2 -- what was run, at what condition, under which rule."""
    net = _wing_net(project)
    table = _wing_case_table(project, net, system)
    conditions, envelope = _wing_selection(project)
    run = [getattr(r, "case", "") for r in net]
    entered = bool(getattr(project.wing_mass, "cases", ()) or ())
    named = [getattr(c, "label", "") for c in conditions]
    missing = [name for name in named if name not in run]
    body = [
        "The wing is analysed at a subset of the flight envelope: not every "
        "point of it, but the conditions that govern the wing structure. Those "
        "cases are listed below, and they are the same cases the summary, the "
        "distributions and the station-by-station appendix state -- one set, "
        "projected four ways.",
        _matrix_sentence(envelope),
        _provenance_sentence(entered, named, run, missing),
        _negative_case_sentence(net),
        _sign_note(plan),
        _derivation_note(net),
        _point_load_note(net),
    ]
    body = [paragraph for paragraph in body if paragraph]
    tables = [t for t in (table, _selection_table(conditions, run),
                          _nomenclature_table(net, system))
              if t is not None]
    if table is None:
        return Section("", body=body,
                       absent_reason=("No wing load cases were produced for "
                                      "this project, so there is nothing to "
                                      "register."))
    return Section("", body=body, tables=tables)


def _wing_summary_table(result: Optional[ModuleResult],
                        system: UnitSystem) -> Optional[Table]:
    """3.3's root values, one row per case, ULTIMATE at each case's own factor.

    Built from the module's own conditions, so the quantities printed are the
    ones ``net_loads`` publishes -- including both torsions where the loads
    reference axis is not the quarter chord, which is the pair OR-51 requires
    the section to keep distinct.
    """
    conditions = _conditions(result, system)
    if not conditions:
        return None
    first = conditions[0]
    keys = [value.key for value in first.values]
    labels = {value.key: value for value in first.values}
    columns = ["Case", "Condition", "SF"]
    for key in keys:
        _text, units = _load_cell(labels[key], first.safety_factor)
        columns.append(f"{labels[key].label} ({units})".replace(" ()", ""))
    rows = []
    for condition in conditions:
        ref = condition.case_ref
        by_key = {value.key: value for value in condition.values}
        row = [getattr(ref, "case_id", "") or "--",
               getattr(ref, "condition", "") or condition.title,
               format_value(condition.safety_factor)]
        for key in keys:
            value = by_key.get(key)
            row.append(_load_cell(value, condition.safety_factor)[0]
                       if value is not None else "--")
        rows.append(row)
    return Table(
        title="Wing root loads by case (ULTIMATE)",
        columns=columns, rows=rows, small=True,
        note=("Root values of each selected case. Every load is ULTIMATE: the "
              "limit load the analysis computed multiplied by the safety factor "
              "stated in its own row, applied once at this boundary. The "
              "torsion names the axis it is stated about; where the loads "
              "reference axis is not the quarter chord both are given, and they "
              "are the same load about two axes rather than two loads."))


def _wing_summary(results: Mapping[str, Optional[ModuleResult]], *,
                  system: UnitSystem,
                  plan: Sequence[SectionPlan]) -> Section:
    """3.3 -- the load cases assessed, at the root."""
    table = _wing_summary_table(results.get(_WING_STEP), system)
    body = [
        "The root of the wing carries the whole of each distribution, so the "
        "values below size the wing and are the ones a reader checks first. "
        "The distributions they are the root of are plotted in "
        + subsection_ref(plan, _WING_STEP, _WING_DISTRIBUTIONS)
        + " and tabulated station by station in "
        + (appendix_ref(WING_LOAD_STATIONS) or "the appendix") + ".",
    ]
    if table is None:
        return Section("", body=body,
                       absent_reason=("The wing load analysis produced no "
                                      "conditions for this project."))
    return Section("", body=body, tables=[table])


#: ``(figure key, station attribute, dimension, title)`` for 3.4's distributions.
#:
#: Chord bending Mzz is deliberately not here (OR-55): it is carried in the
#: results and is not a quantity the wing is sized by, and a fifth figure of it
#: would be four pages of drawing for a load nobody reads off a plot.
_DISTRIBUTION_FIGURES: Tuple[Tuple[str, str, str, str], ...] = (
    ("wing_shear_sz", "sz", "force", "Vertical shear Sz"),
    ("wing_bending_mxx", "mxx", "moment", "Bending moment Mxx"),
    ("wing_torsion_myy", "myy", "moment", "Torsion Myy"),
    ("wing_shear_sx", "sx", "force", "Drag shear Sx"),
)

_CASE_STYLES = ("solid", "dashed", "dotted", "dashdotted", "densely dashed")


def _distribution_figure(net: Sequence[object], key: str, attr: str, dim: str,
                         title: str, system: UnitSystem, assessed: str) -> Figure:
    """One quantity along the span, every selected case on one axes."""
    axis = _torsion_axis(net)
    named = f"{title} ({axis})" if attr == "myy" and axis else title
    if not net:
        return Figure(key=key, title=f"{named} (ULTIMATE)",
                      absent_reason=("the wing load distributions were not "
                                     "produced for this project."))
    u = Units(system)
    series = []
    for result, style in zip(net, _CASE_STYLES * 4):
        stations = list(getattr(result, "stations", ()))
        if not stations:
            continue
        sf = float(getattr(result, "safety_factor", ULTIMATE_FACTOR))
        ref = getattr(result, "case_ref", None)
        name = getattr(ref, "case_id", "") or getattr(result, "case", "")
        series.append(Series(
            f"{name} {getattr(result, 'case', '')}".strip(),
            [u.plain_value(s.y, "length") for s in stations],
            [u.load_value(getattr(s, attr), dim, sf) for s in stations], style))
    if not series:
        return Figure(key=key, title=f"{named} (ULTIMATE)",
                      absent_reason=("the wing load distributions carry no "
                                     "stations to plot."))
    return Figure(
        key=key, title=f"{named} (ULTIMATE)",
        data=PlotData(f"Butt line Y ({u.label('length')})",
                      f"{named} ({u.ult_label(dim)})", series),
        caption=(f"{named} along the semi-span, every selected wing case on one "
                 "axes. The quantity is cumulative: it is summed from the tip "
                 "inboard, so a value is what the wing carries across that "
                 "station and not the load applied at it. All values are "
                 "ULTIMATE, each case scaled by its own safety factor as "
                 f"stated in {assessed}."))


def _wing_distributions(project: Project, *, system: UnitSystem,
                        plan: Sequence[SectionPlan]) -> Section:
    """3.4 -- the net distributions of every selected case."""
    net = _wing_net(project)
    axis = _torsion_axis(net)
    assessed = subsection_ref(plan, _WING_STEP, _WING_ASSESSED)
    figures = [_distribution_figure(net, key, attr, dim, title, system, assessed)
               for key, attr, dim, title in _DISTRIBUTION_FIGURES]
    body = [
        "The distributions below are the net wing loads: the air load and "
        "the inertia load of the same case summed station by station, which is "
        "what the structure carries. Air and inertia are not shown separately; "
        "the loads shown are the net external load, referred to the loads "
        "reference axis" + (f" ({axis})" if axis else "") + ".",
        "Every case selected for the wing is drawn on each axes, so the "
        "governing case for a quantity can be read off the figure rather than "
        "taken on assertion. The station values behind these curves are "
        "tabulated in "
        + (appendix_ref(WING_LOAD_STATIONS) or "the appendix") + ".",
    ]
    return Section("", body=body, figures=figures)


def _wing_loads(project: Project, results: Mapping[str, Optional[ModuleResult]],
                *, system: UnitSystem, plan: Sequence[SectionPlan]) -> Section:
    """Section 3 -- Wing Loads, in its four subsections (OR-48).

    The subsections carry no numbers of their own: each is titled here and
    numbered by :func:`build_section`, so a subsection cannot be renumbered
    without the section it sits under moving with it.
    """
    return Section("", body=[
        "This section states the wing loads: the data they were run from, the "
        "cases run, the loads at the wing root, and the distributions along "
        "the span. Every load case delivered here is ULTIMATE, and every "
        "quantity that is not a delivered load says which it is.",
    ], subsections=[
        replace(_wing_inputs(project, system=system, plan=plan),
                title="Wing input data"),
        replace(_wing_cases(project, system=system, plan=plan),
                title="Load cases and sign convention"),
        replace(_wing_summary(results, system=system, plan=plan),
                title="Load cases assessed"),
        replace(_wing_distributions(project, system=system, plan=plan),
                title="Critical load distributions"),
    ])


# --------------------------------------------------------------------------- #
# Appendix B -- wing loads by station (OR-56)
# --------------------------------------------------------------------------- #
#: ``(station attribute, dimension, label)`` of each column the appendix prints.
#:
#: ``fz``/``fx`` are the **increment** each strip contributes; the rest are the
#: cumulative quantities of 3.4. Both are printed because the reader checking a
#: distribution needs the thing being summed as well as the sum, and neither is
#: recoverable from the other on a page.
#: The cumulative channels of B.2, in the order the structure carries them.
#: ``Mzz`` is deliberately absent -- the drag bending is not delivered by this
#: analysis (owner decision, iteration 3).
_CUMULATIVE_LOADS: Tuple[Tuple[str, str, str], ...] = (
    ("sz", "force", "Sz"),
    ("sx", "force", "Sx"),
    ("mxx", "moment", "Mxx"),
    ("myy", "moment", "Myy"),
)

#: The applied channels of B.1 -- what a structural model is given, not what it
#: carries. ``Fy`` is not among them: the wing has no producer for a spanwise
#: strip load (``WingStationLoad.f_span`` is the fin's), and there is no applied
#: ``Mxx`` or ``Mzz`` at all, because a strip applies forces and a section
#: moment and nothing else. See :func:`_derivation_note`.
_APPLIED_LOADS: Tuple[Tuple[str, str, str], ...] = (
    ("fz", "force", "Fz"),
    ("fx", "force", "Fx"),
    ("myy_free", "moment", "Myy free"),
)


def _case_name(result: object) -> str:
    """The case identity a table row is keyed by."""
    ref = getattr(result, "case_ref", None)
    return getattr(ref, "case_id", "") or getattr(result, "case", "")


def _applied_table(net: Sequence[object], system: UnitSystem,
                   assessed: str) -> Optional[Table]:
    """B.1 -- the applied load set: every strip, and every point mass.

    Deck-grade, which is why the point travels with the load: ``Fz`` applied at
    a station other than the one stated here produces a different ``Myy``, so a
    table that left the coordinates to a cross-reference would be half a load
    definition.
    """
    if not net:
        return None
    u = Units(system)
    length = u.label("length")
    columns = ["Case", "Station", f"X ({length})", f"Y ({length})",
               f"Z ({length})"]
    columns += [f"{label} ({u.ult_label(dim)})"
                for _attr, dim, label in _APPLIED_LOADS]
    rows: List[List[str]] = []
    for result in net:
        name = _case_name(result)
        sf = float(getattr(result, "safety_factor", ULTIMATE_FACTOR))
        for index, station in enumerate(getattr(result, "stations", ()), start=1):
            rows.append([name, str(index)]
                        + [u.plain(getattr(station, a), "length")
                           for a in ("x", "y", "z")]
                        + [u.load(getattr(station, attr), dim, sf)
                           for attr, dim, _label in _APPLIED_LOADS])
        for point in getattr(result, "point_loads", ()):
            rows.append([name, point.name or "point mass"]
                        + [u.plain(getattr(point, a), "length")
                           for a in ("x", "y", "z")]
                        + [u.load(point.fz, "force", sf),
                           u.load(point.fx, "force", sf),
                           u.load(0.0, "moment", sf)])
    if not rows:
        return None
    axis = _torsion_axis(net) or "loads reference axis"
    return Table(
        title="Applied wing loads by station (ULTIMATE)", columns=columns,
        rows=rows, small=True,
        note=("The load applied at each station's own point: a strip row per "
              "load station, root to tip, and a row per concentrated wing mass "
              "at its own coordinates. Together they are the whole applied "
              f"set. Torsion is stated about the {axis}; a point mass carries "
              "no free torsion, because every "
              "moment it produces is its force acting through an arm the "
              "coordinates already state. Every load is ULTIMATE, scaled by "
              f"its own case's safety factor as stated in {assessed}; the "
              "coordinates are geometry and are neither scaled nor marked."))


def _cumulative_table(net: Sequence[object], system: UnitSystem,
                      notation: str) -> Optional[Table]:
    """B.2 -- what the structure carries at each station."""
    if not net:
        return None
    u = Units(system)
    length = u.label("length")
    columns = ["Case", "Station", f"Y ({length})"]
    columns += [f"{label} ({u.ult_label(dim)})"
                for _attr, dim, label in _CUMULATIVE_LOADS]
    rows: List[List[str]] = []
    for result in net:
        name = _case_name(result)
        sf = float(getattr(result, "safety_factor", ULTIMATE_FACTOR))
        for index, station in enumerate(getattr(result, "stations", ()), start=1):
            rows.append([name, str(index), u.plain(station.y, "length")]
                        + [u.load(getattr(station, attr), dim, sf)
                           for attr, dim, _label in _CUMULATIVE_LOADS])
    if not rows:
        return None
    axis = _torsion_axis(net)
    return Table(
        title="Cumulative wing loads by station (ULTIMATE)", columns=columns,
        rows=rows, small=True,
        note=("What the wing carries at each station: the applied loads of the "
              "table above, summed from the tip inboard by the relations in "
              f"{notation}. The station coordinates are printed once, with the "
              "applied set. Torsion is stated about the "
              f"{axis or 'loads reference axis'}. Every load is ULTIMATE, "
              "scaled by its own case's safety factor."))


def _station_appendix(project: Project, *, system: UnitSystem,
                      plan: Sequence[SectionPlan]) -> Section:
    """Appendix B's content: the applied set, then the cumulative one."""
    net = _wing_net(project)
    assessed = subsection_ref(plan, _WING_STEP, _WING_ASSESSED)
    notation = subsection_ref(plan, _WING_STEP, _WING_CASES)
    applied = _applied_table(net, system, assessed)
    carried = _cumulative_table(net, system, notation)
    body = [
        "This appendix carries the wing load distributions of "
        + section_ref(plan, _WING_STEP) + " in full: every selected case at "
        "every load station, in the airplane axes and about the loads "
        "reference axis stated in "
        + subsection_ref(plan, _WING_STEP, _WING_INPUTS) + ". It is the same "
        "result the figures are drawn from, printed rather than plotted.",
        "It is given in two parts, because they are two different quantities "
        "and a reader who takes one for the other builds the wrong model. The "
        "first is the load applied at each station -- what a structural model "
        "is given. The second is the load carried across each station -- what "
        "that model should return. The symbols and the relation between them "
        "are stated in " + notation + ".",
    ]
    if applied is None or carried is None:
        return Section("", body=body,
                       absent_reason=("The wing load distributions were not "
                                      "produced for this project, so there is "
                                      "nothing to tabulate."),
                       page_break=True)
    return Section("", body=body, page_break=True, landscape=True,
                   subsections=[Section("Applied loads", tables=[applied]),
                                Section("Cumulative loads", tables=[carried])])


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
#: Step key -> the builder that produces its section body.
#:
#: A step with no entry renders as its plan state, which is how a not-yet-built
#: section stays a stated placeholder rather than an empty heading.
#:
#: The builders share one signature so that this stays a table of callables
#: rather than four shapes and a dispatch that knows which is which. ``plan`` is
#: unused by three of them today -- hence the ARG001 waivers -- because only a
#: builder that cross-references another section needs it, and section 2.4 is
#: the first that does.
BUILDERS = {
    "configuration_layout": _geometry,
    "weight_mass": _weights,
    "structural_speeds": _speeds,
    "flight_envelope": _envelope,
    "wing_loads": _wing_loads,
}

#: Appendix title -> the builder that produces its body.
#:
#: Separate from :data:`BUILDERS` because an appendix is not a step: it is keyed
#: by the slot it occupies, and a reserved slot has no builder at all -- which is
#: what makes "reserved" renderable rather than a special case in the loop.
APPENDIX_BUILDERS = {
    WING_LOAD_STATIONS: _station_appendix,
}


def build_section(project: Project, entry: SectionPlan,
                  results: Mapping[str, Optional[ModuleResult]], *,
                  system: UnitSystem,
                  plan: Sequence[SectionPlan]) -> Section:
    """One analysis section, headed and either built or stated as absent.

    A section that is not included carries its state's lead and reason and no
    content -- the states are :mod:`.oracle_content`'s to decide, and this
    module only renders what it was told.
    """
    from .oracle_content import heading

    title = heading(entry.number, entry.title)
    builder = BUILDERS.get(entry.step_key)
    if not entry.included or builder is None:
        return Section(title,
                       absent_reason=entry.reason,
                       absent_lead=entry.lead or "Not analysed")
    section = builder(project, results, system=system, plan=plan)
    return Section(title, body=section.body, tables=section.tables,
                   figures=section.figures,
                   subsections=_numbered(entry.number, section.subsections))


def _numbered(parent: str, subsections: Sequence[Section]) -> List[Section]:
    """A builder's own subsections, numbered under ``parent``.

    A step that renders as subsections (section 3) titles them and does not
    number them, exactly as a *group* of steps does not number its members --
    :func:`sloads.report.oracle_content.subsection_number` is the one owner of
    the child form, and a builder that wrote "3.1" into a title would be a
    second numbering scheme that cannot renumber itself when a section is
    inserted above it.
    """
    from .oracle_content import heading, subsection_number

    return [replace(child, title=heading(subsection_number(parent, index),
                                         child.title))
            for index, child in enumerate(subsections)]


def build_appendix(project: Project, entry: SectionPlan,
                   results: Mapping[str, Optional[ModuleResult]], *,  # noqa: ARG001
                   system: UnitSystem,
                   plan: Sequence[SectionPlan]) -> Section:
    """One appendix, lettered and either built or stated as reserved (OR-50).

    The same shape as :func:`build_section` and deliberately not folded into it:
    an appendix is lettered rather than numbered, and its state comes from the
    slot and its step rather than from a plan row of its own.
    """
    from .oracle_content import appendix_heading, appendix_letter

    title = appendix_heading(entry.title)
    builder = APPENDIX_BUILDERS.get(entry.title)
    if not entry.included or builder is None:
        return Section(title, absent_reason=entry.reason,
                       absent_lead=entry.lead or "Not analysed",
                       page_break=True)
    section = builder(project, system=system, plan=plan)
    return Section(title, body=section.body, tables=section.tables,
                   figures=section.figures,
                   # An appendix' children are lettered from their parent by the
                   # same owner a section's are numbered from theirs, so "B.1"
                   # cannot be written down anywhere but here.
                   subsections=_numbered(appendix_letter(entry.title),
                                         section.subsections),
                   absent_reason=section.absent_reason,
                   absent_lead=section.absent_lead,
                   page_break=section.page_break,
                   landscape=section.landscape)


__all__ = [
    "APPENDIX_BUILDERS",
    "BUILDERS",
    "build_appendix",
    "build_section",
]
