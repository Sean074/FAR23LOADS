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

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from ..models import Project
from ..models.enums import AnalysisKind
from ..models.results import ConditionResult, LoadValue, ModuleResult
from ..units import UnitSystem, convert_results
from .content import Figure, PlotData, Section, Series, Table, Units, weight_cg_plot_data
from .oracle_content import SectionPlan, section_ref
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
                             [y for _x, y in oriented], style))
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


def _cg_case_table(project: Project, system: UnitSystem) -> Optional[Table]:
    """The weight and CG cases analysed, one row each."""
    weight = project.weight
    cases = list(getattr(weight, "cg_cases", ()) or ()) if weight else []
    if not cases:
        return None
    u = Units(system)
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
            u.plain(case.zcg, "length"),
            ", ".join(analyses) or "--",
        ])
    length = u.label("length")
    return Table(
        title="Weight and centre-of-gravity cases",
        columns=["Case", "Role", f"Weight ({u.label('mass')})",
                 f"Xcg ({length})", f"Zcg ({length})", "Analysis"],
        rows=rows, note=_CG_CASE_NOTE)


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
    return Figure(
        key=f"vn_{index}",
        title=f"Flight envelope -- {block}",
        data=PlotData("V (KEAS)", "Load factor n", series, points, list(vlines),
                      points_label="Gust design points"),
        caption=(
            "The boundary is "
            "drawn through the design points the analysis computed and is "
            "curved between them: the stall boundary follows the section lift "
            "curve and the compressibility correction, not a constant-CLmax "
            "parabola. Gust points are design points in their own right and are "
            "not vertices of the manoeuvre boundary. Load factors are LIMIT and "
            "dimensionless."),
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


def _envelope(project: Project,  # noqa: ARG001
              results: Mapping[str, Optional[ModuleResult]], *,
              system: UnitSystem,
              plan: Sequence[SectionPlan]) -> Section:
    conditions = _conditions(results.get("flight_envelope"), system)
    blocks = _blocks(conditions)

    speeds = _by_key(_find(_conditions(results.get("structural_speeds"), system),
                           "Structural design speeds"))
    vlines = [(name, float(speeds[key].value))
              for name, key in _ENVELOPE_VLINES if key in speeds]

    figures = [_envelope_figure(block, cases, vlines, index)
               for index, (block, cases) in enumerate(blocks)]
    table = _corner_table(blocks)

    cases_ref = section_ref(plan, "flight_envelope_cases")
    body = [
        "The flight envelope, one diagram per loading and altitude analysed. "
        "Each diagram shows the manoeuvre and stall boundary of that "
        "condition together with the gust design points at the cruise and dive "
        "speeds, against the design speeds of the preceding section.",

        "The design cases selected on these envelopes -- the speed, load factor, "
        "attitude and balance of each condition carried into the component load "
        f"analyses -- are tabulated in {cases_ref}.",
    ]
    far = _far_note(conditions[0] if conditions else None)
    if far:
        body.append(far)
    return Section("", body=body, figures=figures,
                   tables=[t for t in (table,) if t is not None])


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
                   figures=section.figures, subsections=section.subsections)


__all__ = [
    "BUILDERS",
    "build_section",
]
