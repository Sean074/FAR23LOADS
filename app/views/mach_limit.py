"""Streamlit page for the FAR 23 speed–altitude flight-limits envelope (MACHLIM.BAS).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

The design speeds (VA/VC/VD/VF) and the cruise/dive Mach (MC/MD) are OWNED by the
**Structural Speeds** page — this page reads them from the ``speeds`` slice rather
than re-asking for them (Step E7 consolidation). It only adds the two quantities
Structural Speeds does not carry: the **max operating altitude** and the tabulation
**increment**. It renders:

* the MACHLIM Mach-limited equivalent-airspeed table (V(MC)/V(MNE)/V(MD)/V(FC))
  from the shoulder altitude up to the ceiling, and
* a **speed–altitude flight-limits diagram** (altitude on y, speed on x, selectable
  KEAS / KCAS / KTAS) — the constant-Mach fan plus the composite operating boundary:
  the design speeds are EAS-limited (constant) below the shoulder and Mach-limited
  (curving in) above it, exactly like the transport-category placard chart.

All internal calc is knots equivalent airspeed (KEAS); KCAS/KTAS are presentation
conversions applied at the chart boundary (``farloads.constants.convert_airspeed``).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from farloads import MachLimitInput, Project, StructuralSpeedsInput
from farloads import io as farloads_io
from farloads.constants import convert_airspeed, mach_to_eas, standard_atmosphere
from farloads.modules.mach_limit import mach_limit_lines
from farloads.modules.structural_speeds import design_speed_values
from farloads.report import module_text_report


st.title("Speed–Altitude Envelope — FAR 23")
st.caption(
    "Python/Streamlit port of MACHLIM.BAS (Hal C. McMaster). The Mach-limited "
    "equivalent airspeeds and the speed–altitude flight-limits diagram. Design "
    "speeds and MC/MD are read from the Structural Speeds page."
)

project: Project = st.session_state.get("project", Project(name=""))
existing = project.speeds.mach_limit if project.speeds and project.speeds.mach_limit else None

# MC/MD/shoulder are computed by Structural Speeds (design_speed_values); read
# them from there instead of re-asking (Step E7 -- same unused-upstream-data bug
# class fixed on Configuration & Layout and the earlier Mach seed-chain).
ds = None
if project.speeds is not None and project.speeds.weight_lb > 0:
    try:
        ds = design_speed_values(project, project.speeds)
    except (ValueError, ZeroDivisionError):
        ds = None

if ds is not None:
    mc, md = ds.mc, ds.md
    shoulder = project.speeds.shoulder_altitude_ft
elif existing is not None:
    mc, md, shoulder = existing.mc, existing.md, existing.shoulder_altitude_ft
else:
    st.info(
        "No design speeds yet. Enter the design weight, stall speeds and shoulder "
        "altitude on the **Structural Speeds** page first — MC, MD and the shoulder "
        "altitude are read from there."
    )
    st.stop()

with st.sidebar:
    st.header("Inputs")
    st.caption(
        f"From Structural Speeds — MC **{mc:.4f}**, MD **{md:.4f}**, "
        f"shoulder **{shoulder:,.0f} ft**."
    )
    max_alt = st.number_input(
        "Max operating altitude (ft)", min_value=0.0,
        value=float(existing.max_operating_altitude_ft) if existing else 18000.0,
        help="Ceiling of the flight-limits diagram; the Mach-limited table runs from "
             "the shoulder altitude up to here (MACHLIM, Ch 6).",
    )
    incr = st.number_input(
        "Altitude increment (ft)", min_value=1.0,
        value=float(existing.increment_ft) if existing else 1000.0,
        help="Tabulation / plotting step for the Mach-limited airspeeds.",
    )
    axis_unit = st.radio(
        "Chart speed axis", ["KEAS", "KCAS", "KTAS"], horizontal=True,
        help="Equivalent (native calc unit), calibrated (compressibility-corrected, "
             "the placard convention) or true airspeed for the diagram's x-axis. "
             "Boundaries are computed in KEAS and converted at the altitude of each point.",
    )

inp = MachLimitInput(
    mc=mc, md=md, shoulder_altitude_ft=shoulder,
    max_operating_altitude_ft=max_alt, increment_ft=incr,
)
# Persist into the speeds slice (creating it if the Speeds page has not run).
speeds = project.speeds or StructuralSpeedsInput()
speeds.mach_limit = inp
project.speeds = speeds
st.session_state["project"] = project

try:
    results = mach_limit_lines(inp)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute the Mach-limit lines: {exc}")
    st.stop()

summary, *lines = results
mne, mfc = 0.9 * md, 1.2 * md
with st.expander(f"FAR {summary.far_reference} — {summary.title}", expanded=True):
    rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in summary.values]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(summary.note)

# The per-altitude Mach-limited airspeeds as a single table.
table = [{v.label: v.value for v in line.values} for line in lines]
df = pd.DataFrame(table)
st.subheader("Mach-limited equivalent airspeeds")
st.dataframe(df, hide_index=True, width="stretch")


# --------------------------------------------------------------------------- #
# Speed–altitude flight-limits diagram
# --------------------------------------------------------------------------- #
def _altitude_grid(top_ft: float, step_ft: float) -> list:
    """Sea level up to ``top_ft`` in ``step_ft`` steps, with the shoulder and the
    ceiling always present so the boundary kink lands exactly on the shoulder."""
    marks = {0.0, shoulder, top_ft}
    h = 0.0
    while h < top_ft:
        marks.add(h)
        h += step_ft
    return sorted(a for a in marks if a <= top_ft)


def _boundary(alts, unit, eas_below=None, mach_above=None, only_above=False):
    """Speed at each altitude in ``unit``: constant-EAS below the shoulder,
    Mach-limited (M*a*sqrt(sigma)) above it. ``only_above`` drops the sub-shoulder
    leg (for the Mach-only never-exceed / flutter lines)."""
    xs, ys = [], []
    for h in alts:
        above = h >= shoulder
        if above and mach_above is not None:
            a, sigma = standard_atmosphere(h)
            eas = mach_to_eas(mach_above, a, sigma)
        elif not only_above and eas_below is not None:
            eas = eas_below
        else:
            continue
        xs.append(convert_airspeed(eas, h, unit))
        ys.append(h)
    return xs, ys


st.subheader("Speed–altitude flight-limits diagram")
st.caption(
    f"Altitude vs **{axis_unit}**. Design speeds are EAS-limited (constant) below the "
    f"{shoulder:,.0f} ft shoulder and Mach-limited above it; thin grey lines are "
    "constant Mach. All speeds are ULTIMATE-independent design *limit* speeds."
)

alts = _altitude_grid(max_alt, incr)
fig = go.Figure()

# Constant-Mach fan (thin grey reference lines), 0.10 up to just past MFC.
mach_top = mfc + 0.05
m = 0.10
fan = []
while m <= mach_top + 1e-9:
    fan.append(round(m, 2))
    m += 0.05
for mval in fan:
    # A constant-Mach line spans the whole altitude grid (no shoulder kink).
    xs = [convert_airspeed(mach_to_eas(mval, *standard_atmosphere(h)), h, axis_unit) for h in alts]
    ys = list(alts)
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines", line=dict(color="lightgray", width=1),
        name=f"M {mval:.2f}", showlegend=False, hoverinfo="skip",
    ))
    fig.add_annotation(x=xs[-1], y=ys[-1], text=f"{mval:.2f}", showarrow=False,
                       font=dict(size=9, color="gray"), yshift=6)

# Operating boundary: design speeds (EAS below shoulder, Mach-limited above).
_BOUNDS = [
    ("VA / manoeuvre", ds.va if ds else None, None, "#2ca02c"),
    ("VC / MC", ds.vc if ds else None, mc, "#1f77b4"),
    ("VD / MD", ds.vd if ds else None, md, "#d62728"),
    ("VF / flap", ds.vf if ds else None, None, "#9467bd"),
]
for name, eas_below, mach_above, color in _BOUNDS:
    if eas_below is None:
        continue
    xs, ys = _boundary(alts, axis_unit, eas_below=eas_below, mach_above=mach_above)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name,
                             line=dict(color=color, width=3)))

# Mach-only lines above the shoulder: never-exceed (MNE) and flutter clearance (MFC).
for name, mval, color, dash in [("V(MNE)", mne, "#ff7f0e", "dot"), ("V(MFC)", mfc, "#8c564b", "dash")]:
    xs, ys = _boundary(alts, axis_unit, mach_above=mval, only_above=True)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name,
                             line=dict(color=color, width=2, dash=dash)))

# Reference altitudes.
fig.add_hline(y=shoulder, line_dash="dot", line_color="gray",
              annotation_text="shoulder", annotation_position="left")
fig.add_hline(y=max_alt, line_dash="dot", line_color="gray",
              annotation_text="max operating", annotation_position="left")

fig.update_layout(
    xaxis_title=f"Speed ({axis_unit})", yaxis_title="Altitude (ft)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=560, margin=dict(t=40),
)
st.plotly_chart(fig, width="stretch")

st.download_button(
    "Download Mach-limit lines (CSV)",
    farloads_io.load_cases_csv(results),
    file_name="mach_limit.csv",
    mime="text/csv",
)
st.download_button(
    "Download Mach-limit lines (text)",
    module_text_report("Mach limit lines", results),
    file_name="mach_limit.txt",
    mime="text/plain",
)
