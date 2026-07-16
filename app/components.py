"""Shared Streamlit UI components reused across the multi-page app.

Thin presentation wrappers over the pure-calc package; they hold no load math of
their own. The FAR 23 applicability banner is the first shared component: the
detection lives in :func:`farloads.far23_applicability` (pure, unit-tested) and
this module only renders it and wires the "switch to Concept" action.
"""

from __future__ import annotations

import streamlit as st

from farloads import Project, StructuralSpeedsInput, far23_applicability
from farloads.applicability import design_weight_lb
from farloads.modules.structural_speeds import _maneuver_load_factors


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
