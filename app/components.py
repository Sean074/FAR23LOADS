"""Shared Streamlit UI components reused across the multi-page app.

Thin presentation wrappers over the pure-calc package; they hold no load math of
their own. The FAR 23 applicability banner is the shared component here: the
detection lives in :func:`farloads.far23_applicability` (pure, unit-tested) and
this module only renders it and wires the "switch to Concept" action.

The fleet comparison used to live here too, shared by two input pages; it now has
its own dedicated home in ``app/views/aircraft_comparison.py`` (backlog F2).
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from farloads import Project, StructuralSpeedsInput, far23_applicability
from farloads import workflow as wf
from farloads.applicability import design_weight_lb
from farloads.modules.structural_speeds import _maneuver_load_factors


# --------------------------------------------------------------------------- #
# Workflow-derived page links (M2-2, review G6)
# --------------------------------------------------------------------------- #
# Every cross-page link derives its target path *and* default label from
# ``farloads.workflow`` -- the single source of navigation truth -- so a page
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

    ``key`` is a :data:`farloads.workflow.BY_KEY` step key (also the view-file
    stem, ``app/views/<key>.py``). The label defaults to the step's canonical
    ``title`` so renaming a page re-labels every link to it. Raises ``KeyError``
    on an unknown key -- caught by the nav-integrity test, which is the point.
    """
    step = wf.BY_KEY[key]
    text = label or step.title
    try:
        st.page_link(
            f"views/{key}.py", label=text, icon=icon, help=help, disabled=disabled,
        )
    except Exception:
        # Standalone execution (e.g. AppTest, or a view run outside st.navigation)
        # has no page registry, so st.page_link can't resolve the target and
        # raises. Fall back to a non-clickable label so the row / gate hint still
        # renders (a dashboard row must never silently vanish).
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
        n, _n_min, nneg, _nneg_min = _maneuver_load_factors(
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
