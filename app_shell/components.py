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

from contextlib import contextmanager
from typing import Iterator, NamedTuple, Optional

import streamlit as st

from app_shell.nav import page_for
from sloads import Project, StructuralSpeedsInput, UnitSystem, far23_applicability
from sloads import workflow as wf
from sloads.applicability import design_weight_lb
from sloads.modules.structural_speeds import maneuver_load_factors
from sloads.units import labels_for, to_display, to_imperial_scalar, unit_system_from


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
        except Exception:
            pass
    # No registered page: a view driven standalone (AppTest, or run outside
    # st.navigation), or a step the running GUI does not carry. Fall back to a
    # non-clickable label so the row / gate hint still renders -- a dashboard row
    # must never silently vanish.
    st.markdown(f"{icon + ' ' if icon else ''}{text}", help=help)


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


def render_applicability_banner(project: Project) -> None:
    """Non-blocking FAR 23 applicability banner with a switch-to-Concept action.

    Shows nothing for a GA airplane inside the FAR 23 band, or when the project is
    already in concept mode (the per-page "unverified extrapolation" caption covers
    that case). Otherwise warns that results are a concept-mode extrapolation, lists
    each exceedance (value vs. limit), and offers a one-click switch to concept
    mode.
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
KEAS = "kt (EAS)"
ALTITUDE_FT = "ft"


def active_system() -> UnitSystem:
    """The display unit system for this render.

    **The single read of the unit selection in the whole app layer** (D-16), which
    is why M4-20 step 2 re-pointed this one function at ``Project.unit_system``
    without touching a single call site that goes through
    :func:`unit_number_input` or :func:`page`.

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


def unit_number_input(
    label: str,
    value: float,
    *,
    kind: Optional[str] = None,
    fixed_unit: Optional[str] = None,
    key: Optional[str] = None,
    container=None,
    **kwargs,
) -> float:
    """A ``st.number_input`` that renders in display units and **returns Imperial**.

    This is the whole unit boundary for GUI input, in one place. The caller holds
    canonical Imperial values on both sides -- it passes Imperial in and gets
    Imperial back -- so a view can never convert twice, convert the wrong way, or
    forget to convert on the way home. Exactly one of these three modes applies:

    * ``kind="length"`` (or any :data:`sloads.units.UNIT_LABELS` kind) --
      **converted**. The seed is shown in the active system, the label gains the
      system's unit suffix, and the return value is converted back to Imperial.
      The widget key gains a per-system suffix so switching systems re-seeds the
      field with converted defaults instead of reusing the stale number.
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
        seed = float(round(to_display(float(value), kind, system), 4))
        widget_key = f"{key}_{system.value}" if key else None
        # Bounds are given in Imperial like the value, so they convert with it --
        # otherwise a non-zero limit (a 12-in minimum chord, say) would silently
        # become a 12-*mm* minimum in SI and stop constraining anything.
        for bound in ("min_value", "max_value"):
            if kwargs.get(bound) is not None:
                kwargs[bound] = float(to_display(float(kwargs[bound]), kind, system))
        entered = float(where.number_input(shown, value=seed, key=widget_key, **kwargs))
        if entered == seed:
            # Untouched field: return the caller's own Imperial value rather than
            # converting the *rounded* display seed back. The seed is rounded to 4
            # display decimals for legibility (the per-view ``_num`` helpers this
            # replaces did the same), so converting it home would return a number
            # a hair different from the one passed in -- and an SI user's project
            # would drift by that hair on every Apply, silently, forever. Only a
            # value the user actually changed takes the conversion path.
            return float(value)
        return float(to_imperial_scalar(entered, kind, system))

    shown = f"{label} ({fixed_unit})" if fixed_unit else label
    return float(where.number_input(shown, value=float(value), key=key, **kwargs))


# --------------------------------------------------------------------------- #
# Page scaffold (M4-11)
# --------------------------------------------------------------------------- #
#: Project slice -> the workflow step that produces it, derived from
#: ``workflow.STEPS`` so a re-sequenced workflow re-points every gate link.
_PRODUCER = {s.produces: s.key for s in wf.STEPS if s.produces}


class PageContext(NamedTuple):
    """What every view needs off the top: the project and its display units.

    ``U`` is ``labels_for(system)`` -- the ``{"length": "in", ...}`` unit-string
    map views interpolate into headers and column names.
    """
    project: Project
    system: UnitSystem
    U: dict


def page_header(
    key: str,
    *,
    title: Optional[str] = None,
    caption: Optional[str] = None,
    banner: bool = True,
) -> PageContext:
    """Render a view's standard opening and return its :class:`PageContext`.

    The four lines every view repeated -- title, caption, applicability banner,
    and reading the project + unit system out of session state -- in one call.
    ``key`` is the :data:`sloads.workflow.BY_KEY` step key (the view's filename
    stem), so the **title comes from ``workflow.py``** rather than being restated
    per page; pass ``title=`` only where a page wants a different heading from
    its navigation label.

    This is the plain-call form, for the top-level script views. Use
    :func:`page` -- the same thing plus an automatic upstream gate -- in new code
    and anywhere the page body already lives inside a function.
    """
    step = wf.BY_KEY[key]
    st.title(title if title is not None else step.title)
    if caption:
        st.caption(caption)

    project = active_project()
    if banner:
        render_applicability_banner(project)

    system = active_system()
    return PageContext(project, system, labels_for(system))


@contextmanager
def page(
    key: str,
    *,
    title: Optional[str] = None,
    caption: Optional[str] = None,
    banner: bool = True,
    gate_missing: bool = True,
) -> Iterator[PageContext]:
    """:func:`page_header` plus the upstream gate, as a context manager.

    The *required* slices come from the same ``workflow.py`` step as the title,
    and each gate's jump link is looked up from the step that **produces** the
    missing slice -- so a re-sequenced workflow re-points every gate without a
    view being touched. With ``gate_missing`` (the default) the page body is
    skipped entirely (``st.stop()``) when a requirement is absent.

    A page with a more specific thing to say about *why* it is blocked should
    keep its own :func:`gate` call and pass ``gate_missing=False``: the generic
    message here is a floor, not a replacement for page-specific guidance.

    Usage::

        with page("structural_speeds", caption="...") as (project, system, U):
            v_a = unit_number_input("VA", inp.va, fixed_unit=KEAS, key="va")
    """
    ctx = page_header(key, title=title, caption=caption, banner=banner)

    missing = wf.missing_requirements(ctx.project, wf.BY_KEY[key])
    if missing and gate_missing:
        for slice_name in missing:
            producer = _PRODUCER.get(slice_name)
            target = wf.BY_KEY[producer].title if producer else slice_name
            gate(
                f"This page needs **{target}** first — it has no `{slice_name}` yet.",
                *([producer] if producer else []),
            )
        st.stop()

    yield ctx
