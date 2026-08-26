"""Shared Streamlit UI components reused across every sloads GUI.

Thin presentation wrappers over the pure-calc package; they hold no load math of
their own. The FAR 23 applicability banner is the shared component here: the
detection lives in :func:`sloads.far23_applicability` (pure, unit-tested) and
this module only renders it and wires the "switch to Concept" action.

The fleet comparison used to live here too, shared by two input pages; it now has
its own dedicated home in ``app/views/aircraft_comparison.py`` (backlog F2).

Moved out of ``app/`` into :mod:`app_shell` by design note 32 step OG-B. The one
front-end assumption that survived that move -- :func:`workflow_page_link`
emitting ``views/<key>.py``, which is true of ``app/`` and of no GUI that builds
its pages any other way -- was removed by OG-F: the target is now the running
GUI's own page object, resolved through :mod:`app_shell.nav`. Neither the page
set nor its shape is shared; each GUI derives its own (note 32, OG-2).
"""

from __future__ import annotations

from typing import Container, NamedTuple, NoReturn, Optional

import streamlit as st
from streamlit.errors import StreamlitAPIException

from app_shell.nav import page_for
from app_shell.widget_keys import widget_key
from sloads import (
    Project,
    StructuralSpeedsInput,
    UnitSystem,
    consistency_warnings,
    far23_applicability,
)
from sloads import workflow as wf
from sloads.applicability import design_weight_lb
from sloads.modules.structural_speeds import maneuver_load_factors
from sloads.units import (
    KEAS,  # noqa: F401 -- re-exported as this layer's fixed_unit constant
    labels_for,
    to_display,
    to_imperial_scalar,
    unit_system_from,
)


# --------------------------------------------------------------------------- #
# Workflow-derived page links (M2-2, review G6)
# --------------------------------------------------------------------------- #
# Every cross-page link derives its target path *and* default label from
# ``sloads.workflow`` -- the single source of navigation truth -- so a page
# rename updates every link automatically and stale hand-typed page names (the
# G6 finding: "Wing Geometry", "Configuration & Layout") can't recur.
def workflow_page_link(
    key: str,
    *,
    label: Optional[str] = None,
    icon: Optional[str] = None,
    help: Optional[str] = None,
    disabled: bool = False,
) -> None:
    """Render an ``st.page_link`` to the workflow step ``key``.

    ``key`` is a :data:`sloads.workflow.BY_KEY` step key. The label defaults to
    the step's canonical ``title`` so renaming a page re-labels every link to it.
    Raises ``KeyError`` on an unknown key -- caught by the nav-integrity test,
    which is the point.

    The target is the running GUI's own page object (:mod:`app_shell.nav`),
    never a path. Until OG-F this built ``views/<key>.py``, which is true of
    ``app/`` and of nothing else: the oracle GUI's pages are callables, so the
    shared shell held one front-end's directory layout and would have sent the
    other's links into a page set it is not part of.
    """
    step = wf.BY_KEY[key]
    text = label or step.title
    page = page_for(key)
    if page is not None:
        try:
            st.page_link(
                page, label=text, icon=icon, help=help, disabled=disabled,
            )
            return
        except StreamlitAPIException:
            # Streamlit's own refusal to render this link (a page object outside
            # the running navigation, a script run without one). Narrowed from a
            # bare ``except Exception`` by CR-A-5/CR-D-10: the intended fallback
            # -- an unregistered step -- is the ``page is None`` branch below, so
            # a broad catch here only hid genuine failures as silent text.
            pass
    # No registered page: a view driven standalone (AppTest, or run outside
    # st.navigation), or a step the running GUI does not carry. Fall back to a
    # non-clickable label so the row / gate hint still renders -- a dashboard row
    # must never silently vanish.
    st.markdown(f"{icon + ' ' if icon else ''}{text}", help=help)


class StopPage(BaseException):
    """:func:`stop_page` inside the shell: the page is over, the shell is not.

    A ``BaseException`` like Streamlit's own ``StopException``, so a view's
    ``except Exception`` cannot swallow it.
    """


#: Session-state flag the shell sidebar raises while it wraps the page, so
#: :func:`stop_page` knows there is a shell to hand the exit to.
IN_SHELL_KEY = "_shell_wraps_page"


def stop_page() -> NoReturn:
    """End the page here -- the shell's ``st.stop()``.

    Inside ``with render_shell_sidebar(project): pg.run()`` this raises
    :class:`StopPage`, which the sidebar catches so its project-file block still
    renders *after* the page: ``st.stop()`` discards every element emitted after
    it, so a sidebar rendered behind the page would have lost Save / Download on
    exactly the pages that gate (#64, PB-4). Driven standalone (a view under
    ``AppTest``, a script with no shell) it is ``st.stop()``. Guarded:
    ``app/views`` call this and never ``st.stop()`` directly.
    """
    if st.session_state.get(IN_SHELL_KEY):
        raise StopPage()
    st.stop()


def gate(message: str, *keys: str, kind: str = "warning") -> None:
    """Render a gating notice plus a ``workflow_page_link`` to each target page.

    The "define X on the Y page first" pattern (review G6): ``message`` is shown
    via ``st.warning`` (``kind="warning"``) or ``st.info`` (``kind="info"``),
    followed by one link per workflow step ``key`` so the user can jump straight
    to the page that unblocks this one.
    """
    (st.info if kind == "info" else st.warning)(message)
    for key in keys:
        workflow_page_link(key, label=f"→ {wf.BY_KEY[key].title}")


def _switch_to_concept(project: Project) -> None:
    """Flip the project to concept mode without breaking the downstream calc.

    Sets ``speeds.category = "C"`` and, when the concept load factors are unset,
    seeds them from the currently-computed FAR 23.337 limit factors so the flip is
    continuous and never raises (concept mode *requires* explicit
    ``chosen_n``/``chosen_nneg``). The factors depend only on category + weight, so
    the seed cannot fail on missing geometry.
    """
    speeds = project.speeds or StructuralSpeedsInput()
    if speeds.chosen_n is None or speeds.chosen_nneg is None:
        weight = design_weight_lb(project)
        n, _n_min, nneg, _nneg_min = maneuver_load_factors(
            speeds.category, weight, speeds.chosen_n, speeds.chosen_nneg
        )
        speeds.chosen_n = n
        speeds.chosen_nneg = nneg
    speeds.category = "C"
    project.speeds = speeds
    st.session_state["project"] = project


def render_applicability_banner(project: Project, *, switch_action: bool = True) -> None:
    """Non-blocking FAR 23 applicability banner with a switch-to-Concept action.

    Shows nothing for a GA airplane inside the FAR 23 band, or when the project is
    already in concept mode (the per-page "unverified extrapolation" caption covers
    that case). Otherwise warns that results are a concept-mode extrapolation, lists
    each exceedance (value vs. limit), and offers a one-click switch to concept
    mode.

    ``switch_action=False`` renders the warning and the exceedance list **without**
    the switch button, for a GUI that does not carry concept mode at all (the
    oracle GUI, note 32 OG-1; CR-A-4). The exceedances are still stated -- the
    finding is that the *action* is out of scope there, not the warning: an
    out-of-band airplane must still be told its results are an extrapolation.
    """
    if project.is_concept:
        return
    exceedances = far23_applicability(project)
    if not exceedances:
        return

    st.warning(
        "**Exceeds FAR 23 applicability.** This airplane is outside the certificated "
        "band the FAR 23 replication is calibrated to; results are a **concept-mode "
        "extrapolation**, not a certified analysis."
    )
    for exc in exceedances:
        st.markdown(
            f"- **{exc.label}:** {exc.value:,.0f} exceeds the limit of {exc.limit:,.0f}"
        )
    if not switch_action:
        return
    if st.button("Switch to Concept", key="switch_to_concept"):
        _switch_to_concept(project)
        st.rerun()


# --------------------------------------------------------------------------- #
# The unit boundary (M4-11, decision D-16)
# --------------------------------------------------------------------------- #
#: Units that are **aviation-standard and never converted** by the Imperial/SI
#: toggle -- airspeed is always KEAS and altitude always feet, in both systems
#: (``GUI_design.md``, "one unit per dimension"). They are passed to
#: :func:`unit_number_input` as ``fixed_unit=``, an explicit branch of the
#: signature: the carve-out is a property of the *field*, decided by the caller,
#: never sniffed out of a unit string at render time.
#:
#: ``KEAS`` is re-exported from :mod:`sloads.units`, which needs the same string
#: for :data:`~sloads.units.AVIATION_STANDARD` -- the two spelled it separately
#: until PB-22, and a widget's ``fixed_unit=`` and the registry's answer for the
#: same field disagreeing is the one way this constant can go wrong.
ALTITUDE_FT = "ft"


def active_system() -> UnitSystem:
    """The display unit system for this render.

    **The single read of the unit selection in the whole app layer** (D-16), which
    is why M4-20 step 2 re-pointed this one function at ``Project.unit_system``
    without touching a single call site that goes through
    :func:`unit_number_input`.

    The project field is the authority; the session key is the fallback for a
    render that has no project yet (the very first paint, before Home.py has put
    one in session state). Both default to Imperial.
    """
    project = st.session_state.get("project")
    if project is not None:
        return unit_system_from(getattr(project, "unit_system", None))
    return st.session_state.get("unit_system", UnitSystem.IMPERIAL)


def active_project() -> Project:
    """The project being edited, or an empty one so a bare page still renders."""
    return st.session_state.get("project", Project(name=""))


def number_input_name(key: Optional[str], kind: Optional[str] = None) -> Optional[str]:
    """The widget name :func:`unit_number_input` registers for ``key``, unstamped.

    One owner for the naming, because a second reader appeared: clearing a filled
    field writes ``None`` to the widget's own state (:func:`clear_number_input`,
    #72), and a key computed a second time somewhere else would clear a widget
    that does not exist. The **generation stamp is deliberately not applied here**
    -- ``widget_key`` wraps this at each call site, where the freshness guard
    (``tests/test_widget_freshness.py``) can see it -- so this owns the naming and
    that owns the staleness. The converted mode suffixes the active system so a unit
    switch re-seeds the field instead of reusing the stale number; the fixed-unit
    and dimensionless modes do not, because the number is the same in both
    systems and must survive the switch untouched.
    """
    if key is None:
        return None
    return f"{key}_{active_system().value}" if kind is not None else key


def clear_number_input(key: str, kind: Optional[str] = None) -> None:
    """Empty a filled :func:`unit_number_input` -- the way back to unfilled (#72).

    A ``st.number_input`` **seeded with a number is not clearable**: the frontend
    restores the last value on blur, and ``NumberInputSerde.deserialize`` reads an
    empty submission as the seed, so no amount of handling ``None`` on the return
    path can un-fill a field the user has filled (PB-20 proposed exactly that; it
    cannot work). Streamlit's one door is the widget's own state -- ``None`` there
    makes the next render seed ``value=None``, which renders empty and returns
    ``None`` -- and it may only be written **before** the widget is instantiated,
    so this belongs in an ``on_click`` callback and nowhere else.

    The record is deliberately *not* written here. The render pass that follows
    sees the empty widget and clears the field through its normal persist path,
    so there is one writer, holding the record of the pass it is in, rather than a
    callback holding a record from the pass before.
    """
    name = number_input_name(key, kind)
    if name is not None:
        st.session_state[widget_key(name)] = None


def unit_number_input(
    label: str,
    value: Optional[float],
    *,
    kind: Optional[str] = None,
    fixed_unit: Optional[str] = None,
    key: Optional[str] = None,
    container=None,
    **kwargs,
) -> Optional[float]:
    """A ``st.number_input`` that renders in display units and **returns Imperial**.

    This is the whole unit boundary for GUI input, in one place. The caller holds
    canonical Imperial values on both sides -- it passes Imperial in and gets
    Imperial back -- so a view can never convert twice, convert the wrong way, or
    forget to convert on the way home.

    ``value=None`` renders the widget **empty** and returns ``None`` until the
    user enters a number (#35, CR-A-3): an unfilled ``Optional`` field must not
    display a fake ``0.0``, because then a deliberate ``0`` -- sea level, a
    datum-at-nose station -- is indistinguishable from the seed and can never be
    persisted. A ``float`` in always comes back a ``float``.

    Exactly one of these three modes applies:

    * ``kind="length"`` (or any :data:`sloads.units.UNIT_LABELS` kind) --
      **converted**. The seed is shown in the active system, the label gains the
      system's unit suffix, and the return value is converted back to Imperial.
      The widget key gains a per-system suffix so switching systems re-seeds the
      field with converted defaults instead of reusing the stale number. (Every
      key here is also stamped with the project generation, for the same reason
      one step up: see :mod:`app_shell.widget_keys`.)
    * ``fixed_unit=KEAS`` / ``fixed_unit=ALTITUDE_FT`` -- **not converted**. The
      unit is shown in the label and the value passes through untouched, in both
      systems. The widget key is *not* suffixed: the number is the same in either
      system, so the field must survive a unit switch unchanged.
    * neither -- **dimensionless** (ratios, counts, angles in degrees). No unit
      suffix, no conversion, no key suffix.

    ``container`` is the Streamlit container to render into -- a column from
    ``st.columns``, an expander, a form -- defaulting to ``st`` itself.
    ``**kwargs`` go straight to ``number_input`` (``step``, ``format``,
    ``min_value``, ``help``, ``disabled``, ...).

    Raises ``ValueError`` if both ``kind`` and ``fixed_unit`` are given -- a field
    is either on the conversion path or off it, never ambiguously both.
    """
    if kind is not None and fixed_unit is not None:
        raise ValueError(
            f"unit_number_input({label!r}): pass kind= (converted) or fixed_unit= "
            "(aviation carve-out), not both"
        )

    system = active_system()
    where = container if container is not None else st

    if kind is not None:
        shown = f"{label} ({labels_for(system)[kind]})"
        # The seed is the converted value *exactly*: ``format`` owns how many
        # decimals the widget shows, and a seed rounded here on top of it read
        # back as a different number to anything that reads the widget (the G5
        # journey, #62) while the project held the full value.
        seed = None if value is None else float(to_display(float(value), kind, system))
        # The unit-system suffix and the generation stamp below say the same
        # thing in two directions: this is a different widget now.
        # Bounds are given in Imperial like the value, so they convert with it --
        # otherwise a non-zero limit (a 12-in minimum chord, say) would silently
        # become a 12-*mm* minimum in SI and stop constraining anything.
        for bound in ("min_value", "max_value"):
            if kwargs.get(bound) is not None:
                kwargs[bound] = float(to_display(float(kwargs[bound]), kind, system))
        entered = where.number_input(
            shown, value=seed, key=widget_key(number_input_name(key, kind)), **kwargs)
        if entered is None:
            return None
        if seed is not None and float(entered) == seed:
            # Untouched field: return the caller's own Imperial value rather than
            # converting the display seed back -- a converted value does not
            # always round-trip to the same float, and an SI user's project would
            # drift by that hair on every Apply, silently, forever. Only a value
            # the user actually changed takes the conversion path.
            return float(value)  # seed is not None implies value is not None
        return float(to_imperial_scalar(float(entered), kind, system))

    shown = f"{label} ({fixed_unit})" if fixed_unit else label
    entered = where.number_input(
        shown, value=None if value is None else float(value),
        key=widget_key(number_input_name(key)), **kwargs)
    return None if entered is None else float(entered)


# --------------------------------------------------------------------------- #
# Page scaffold (M4-11)
# --------------------------------------------------------------------------- #
class PageContext(NamedTuple):
    """What every view needs off the top: the project and its display units.

    ``U`` is ``labels_for(system)`` -- the ``{"length": "in", ...}`` unit-string
    map views interpolate into headers and column names.
    """
    project: Project
    system: UnitSystem
    U: dict


def render_consistency_warnings(
    project: Project,
    key: str,
    *,
    only_codes: Optional[Container[str]] = None,
) -> None:
    """Render the input-consistency warnings tagged for workflow step ``key``.

    The **one** consumer of :func:`sloads.consistency_warnings` in either GUI
    (practice 3: one source, so the two front-ends cannot diverge). Until #82 the
    main GUI open-coded this loop in six views -- two of them against page names
    that no longer existed -- and ``oracle_app``/``app_shell`` had no consumer of
    ``ConsistencyWarning`` at all: a page-targeted entry-error channel that is
    part of the analysis contract was dark exactly where entries are made. A
    detected contradictory ``wing_fraction`` entry survived a whole build review
    unshown that way (C210-35).

    ``only_codes`` narrows to a named subset, for a page that re-states one
    warning next to the result it bears on (the Design Speeds page's operational
    limitations tab).
    """
    for w in consistency_warnings(project):
        if w.page != key:
            continue
        if only_codes is not None and w.code not in only_codes:
            continue
        st.warning(w.message)


def render_page_order_reads(project: Project, key: str) -> None:
    """State the later pages this page's numbers depend on (#69, PB-15/PB-19).

    A page whose result reads a slice entered further down the workflow shows a
    complete-looking answer that changes once that later page is filled -- the
    Flap page's 23.457(b) slipstream case is a whole *delivered case* that does
    not exist until an engine record does, ~19 % of the governing flap load on
    the C210. Downloaded in between, the numbers are wrong and nothing on the
    page ever said why.

    The dependencies are declared on the step (:attr:`sloads.workflow.WorkflowStep.reads`)
    and resolved by :func:`sloads.workflow.later_page_reads`, so this renders
    what the workflow already knows and holds no list of its own. Stated on
    every visit, not only when the slice is absent: it is provenance either way,
    and a mark that appears only in the broken state teaches nothing about the
    page. The loud channel stays :func:`render_consistency_warnings` -- this one
    is a caption, and turns into a warning only when a dependency is genuinely
    still empty.

    Links to the entering page when the running GUI carries it; the oracle GUI
    has fourteen of the twenty-two steps, so the name degrades to plain text
    rather than pointing at a page that is not there.
    """
    rows = wf.later_page_reads(project, wf.BY_KEY[key])
    if not rows:
        return
    parts = []
    for row in rows:
        where = wf.BY_KEY[row.entered_on].title if row.entered_on else "another page"
        label = row.slice_name.replace("_", " ")
        parts.append(f"**{label}** (entered on {where})"
                     + ("" if row.present else " — not entered yet"))
    lead = "These numbers also read " + ", ".join(parts) + "."
    if all(row.present for row in rows):
        st.caption(lead)
        return
    st.warning(lead + " Fill that page first: results shown or downloaded now "
                      "will change once it is.")


def page_header(
    key: str,
    *,
    title: Optional[str] = None,
    caption: Optional[str] = None,
    banner: bool = True,
    switch_action: bool = True,
) -> PageContext:
    """Render a view's standard opening and return its :class:`PageContext`.

    The four lines every view repeated -- title, caption, applicability banner,
    and reading the project + unit system out of session state -- in one call.
    ``key`` is the :data:`sloads.workflow.BY_KEY` step key (the view's filename
    stem), so the **title comes from ``workflow.py``** rather than being restated
    per page; pass ``title=`` only where a page wants a different heading from
    its navigation label.

    ``switch_action=False`` keeps the applicability warning but drops its
    switch-to-Concept button, for a GUI without concept mode (CR-A-4).
    """
    step = wf.BY_KEY[key]
    st.title(title if title is not None else step.title)
    if caption:
        st.caption(caption)

    project = active_project()
    if banner:
        render_applicability_banner(project, switch_action=switch_action)
    # Every page that opens with this header gets the entry-error warnings tagged
    # for it -- both GUIs, all fourteen oracle pages included, with nothing to
    # remember per page (#82). It sits with the applicability banner because it is
    # the same kind of thing: a page-targeted finding about the inputs, rendered
    # from the step key the header already has.
    render_consistency_warnings(project, key)
    # Same rationale, the other direction: the consistency channel reports a
    # contradiction in what was entered, this one reports a dependency on what
    # has not been (#69).
    render_page_order_reads(project, key)

    system = active_system()
    return PageContext(project, system, labels_for(system))


