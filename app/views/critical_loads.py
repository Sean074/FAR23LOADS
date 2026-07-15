"""Streamlit page for the critical flight loads (SELECT).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the governing (critical) load on each major component -- wing, horizontal
tail, vertical tail and fuselage -- selected from the FLTLOADS V-n matrix by the
SELECT module (Reference 1 Ch 9). The horizontal- and vertical-tail rational loads
appear when the Tail Loads inputs are present on the project.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from farloads import ConditionResult, Project, UnitSystem, convert_results
from farloads.modules.select import build_critical


st.title("Critical Flight Loads — SELECT")
st.caption(
    "Python/Streamlit port of SELECT.BAS (Hal C. McMaster). Searches the balanced "
    "V-n matrix (FLTLOADS) for the governing wing, horizontal-tail, vertical-tail "
    "and fuselage loads (FAR 23.301/23.331/23.333/23.421/23.423/23.425/23.427/"
    "23.441/23.443)."
)

project: Project = st.session_state.get("project", Project(name=""))
system: UnitSystem = st.session_state.get("unit_system", UnitSystem.IMPERIAL)


def _display_loads(loads: list, system: UnitSystem) -> list:
    """Display-only copy of a ``CriticalCondition.loads`` list converted to
    ``system`` (Imperial is a no-op). ``CriticalCondition`` carries a bare
    ``List[LoadValue]`` (not a :class:`~farloads.ConditionResult`), so it is
    wrapped/unwrapped around :func:`farloads.convert_results` rather than
    mutating the condition itself.
    """
    if system == UnitSystem.IMPERIAL:
        return loads
    wrapped = ConditionResult(title="", far_reference="", values=loads)
    return convert_results([wrapped], system)[0].values


if project.flight_loads is None and project.envelope is None:
    st.warning("Define the flight-loads inputs on the **Flight Envelope** page first "
               "(SELECT searches the V-n matrix it produces).")
    st.stop()

if project.is_concept:
    st.warning("Concept category (C): critical loads are an **unverified "
               "extrapolation** above the FAR 23 calibration band.")

if project.tail_loads is None:
    st.info("Add the **Tail Loads** inputs to the project to include the rational "
            "horizontal-tail loads; the wing and fuselage conditions are shown regardless.")

try:
    critical = build_critical(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not select critical loads: {exc}")
    st.stop()

# Carry forward any previously-persisted selection (Step D5) so re-visiting the
# page doesn't silently reset a curated subset back to "everything".
prior_selected = (
    set(project.envelope.critical.selected_case_ids)
    if project.envelope is not None and project.envelope.critical is not None
    and project.envelope.critical.selected_case_ids
    else None
)

_COMPONENTS = [
    ("wing", "Wing", "PHAA / PMAA / PLAA / NMAA, accelerated & steady roll"),
    ("htail", "Horizontal tail", "balancing, maneuver, gust, unsymmetrical"),
    ("vtail", "Vertical tail", "rudder, sideslip, yaw, side gust"),
    ("fuselage", "Fuselage", "load on wing, aft bending, greatest Nz"),
]

st.info(
    "Uncheck a condition to drop it from the **Results Review** page's governing-"
    "loads summary — everything is included by default. This never affects the "
    "structural calc (WINGINER/NETLOADS, fuselage/tail/control-surface loads, "
    "sbeam export), only that summary."
)

checked_ids: list = []
all_ids: list = []
for key, title, sub in _COMPONENTS:
    conds = [c for c in critical.conditions if c.component == key]
    if not conds:
        continue
    st.subheader(f"{title} — {len(conds)} condition(s)")
    st.caption(sub)
    rows = []
    for c in conds:
        cid = c.case_ref.case_id if c.case_ref else None
        if cid:
            all_ids.append(cid)
            default_checked = cid in prior_selected if prior_selected is not None else True
            checked = st.checkbox(
                f"{c.label} ({cid})", value=default_checked, key=f"select_{cid}",
            )
            if checked:
                checked_ids.append(cid)
        row = {"Condition": c.label, "FAR": c.far_reference, "V-n case": c.case}
        for lv in _display_loads(c.loads, system):
            row[lv.label] = round(lv.value, 2)
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# Empty list means "no filter" (every condition kept) -- only persist a real
# subset when the engineer has actually deselected something.
critical.selected_case_ids = [] if checked_ids == all_ids else checked_ids

# Persist so downstream pages (Fuselage Loads, Results Review, exports) can
# reuse the same selection.
if project.envelope is not None:
    project.envelope.critical = critical
    st.session_state["project"] = project
