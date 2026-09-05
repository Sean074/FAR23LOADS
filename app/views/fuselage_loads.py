"""Streamlit page for the net fuselage loads (Ch 15).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

Shows the longitudinal fuselage shear and bending for each critical fuselage
condition (SELECT) as the fuselage inertia reacted by the tail air load and the
wing attachment (Reference 1 Ch 15) -- the body analogue of the net wing loads.
The fuselage mass distribution is entered here; the wing/tail stations come from
the Flight Envelope and Tail Loads inputs, and the front/rear spar stations that
react the unbalanced moment (M4-1) from the wing planform + spar fractions on the
**Configuration & Layout** page.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_shell.components import active_system, gate, stop_page
from app_shell.limit_csv import body_limit_csv, body_limit_rows
from app_shell.widget_keys import widget_key
from sloads import (
    Project,
    UnitSystem,
    labels_for,
    mass_distribution,
    si_scalar_label,
    to_display,
    to_imperial_scalar,
    to_si_scalar,
)
from sloads.export import sbeam_bridge as sb
from sloads.models import FuselageMassInput, FuselageStation
from sloads.modules.body_loads import body_load_rows, build_body_loads

st.title("Net Fuselage Loads — shear / bending")
st.caption(
    "Python/Streamlit port of the Reference 1 Ch 15 procedure (no original .BAS): "
    "the fuselage is a beam carrying the inertia of its mass items, reacted by the "
    "tail air load and the wing attachment. Validated by equilibrium closure — "
    "vertical (ΣFz) and moment (terminal `Myy`), the Ch 15 p103 two-pass "
    "front/rear-spar solve."
)

project: Project = st.session_state.get("project", Project(name=""))
# D-16: ``active_system()`` is the single read of the unit selection. Reading
# ``session_state["unit_system"]`` here was a second authority for the same
# decision -- since M4-20 step 2 the project field is the source, and the
# session key is only the no-project-yet fallback inside ``active_system()``.
system: UnitSystem = active_system()
U = labels_for(system)  # {"weight","length",...} -> unit string

if project.flight_loads is None:
    gate("Define the flight-loads inputs on the **Flight Envelope (V-n)** page first.",
         "flight_envelope")
    stop_page()

# Captured before the form builds a replacement (#145).
_existing_fuselage_mass = project.fuselage_mass
fm = project.fuselage_mass or FuselageMassInput()

# The beam is derived from the itemized weight database (the mass SSOT, step B1);
# the table below is an explicit override. Show the reconciliation first, so an
# override is a decision taken in front of the number rather than instead of it.
_recon = mass_distribution.fuselage_reconciliation(project)
if _recon is not None and not _recon.ok:
    st.warning(
        f"**Entered stations disagree with the weight database:** {_recon.detail}. "
        "The derived distribution is used unless you tick *override* below."
    )
_derived = mass_distribution.derived_fuselage_stations(project)
_summary = mass_distribution.component_summary(project)
if _summary:
    with st.expander(
            f"Mass model — {len(_derived)} derived stations, "
            f"{sum(s.weight_lb for s in _derived):,.0f} {U['weight']} on the beam"):
        st.caption(
            "Derived from **Weight & CG → items**, tagged by component. The beam "
            "carries everything except the wing: the wing enters as the "
            "carry-through reaction, and applying it as mass too would count it "
            "twice (Ref 1 Ch 15 p103).")
        st.dataframe(pd.DataFrame(_summary), hide_index=True,
                     width="stretch")
        _tie = mass_distribution.wing_mass_tie(project)
        if _tie is not None and not _tie.ok:
            st.info(f"Wing mass tie: {_tie.detail}.")

with st.form("fuselage_mass_form"):
    st.subheader(f"Fuselage mass distribution ({U['length']} / {U['weight']})")
    st.caption("Lumped station weights nose→tail. Used **only** when *override* is "
               "ticked; otherwise the distribution is derived from the itemized "
               "weight database.")
    override = st.checkbox(
        "Override the derived distribution with the table below",
        value=fm.stations_are_override,
        key=widget_key("fus_override"),
        help="Leave unticked to use the weight database (the single source of "
             "truth). Tick to hand-enter the beam, e.g. to reproduce a legacy model.")
    default = pd.DataFrame(
        [[to_display(s.x, "length", system), to_display(s.weight_lb, "weight", system)]
         for s in (fm.stations or _derived)] or [[0.0, 0.0]],
        columns=["x", "weight_lb"],
    )
    station_cols = {
        "x": st.column_config.NumberColumn(f"x ({U['length']})"),
        "weight_lb": st.column_config.NumberColumn(f"weight ({U['weight']})"),
    }
    df = st.data_editor(default, column_config=station_cols, num_rows="dynamic",
                        hide_index=True, width="stretch", key=widget_key(f"fuselage_stations_{system.value}"))
    applied = st.form_submit_button("Apply", type="primary")

if applied:
    stations = [
        FuselageStation(x=to_imperial_scalar(float(r["x"]), "length", system),
                        weight_lb=to_imperial_scalar(float(r["weight_lb"]), "weight", system))
        for _, r in df.iterrows()
        if pd.notna(r["x"]) and pd.notna(r["weight_lb"])
    ]
    # ``mass_distribution`` reads ``stations`` only when ``stations_are_override``
    # is set, so persisting a non-override table writes a copy of the derived
    # distribution that nothing ever reads -- and on a project with no slice at
    # all that was an Apply attaching one out of derived data nobody entered
    # (#145). The override switch is this page's named gesture; an existing
    # slice is still written back, so unticking it lands.
    _built = FuselageMassInput(stations=stations, ref_waterline=fm.ref_waterline,
                               stations_are_override=bool(override))
    project.fuselage_mass = (
        _built if _existing_fuselage_mass is not None or override else None)
    st.session_state["project"] = project
    st.success("Fuselage mass distribution applied"
               + (" (overriding the weight database)." if override else
                  " — the derived distribution is in use."))
    fm = project.fuselage_mass

if project.is_concept:
    st.warning("Concept category (C): an **unverified extrapolation** above the "
               "FAR 23 calibration band.")

try:
    results = build_body_loads(project)
except (ValueError, ZeroDivisionError) as exc:
    st.error(f"Could not compute fuselage loads: {exc}")
    stop_page()

if not results:
    st.info("No critical fuselage conditions to distribute.")
    stop_page()

st.caption(
    "Loads shown are **LIMIT** (oracle-traceable), and so is every load this "
    "tool delivers: the **Review/Export** pages state the 14 CFR 23.303 factor "
    "per case and apply it nowhere."
)
if any(r.closure_artifact for r in results):
    # Fallback path only: no derivable spar stations, so the moment was closed by
    # a correction with no physical source (M4-1, CLOSURE_ARTIFACT_CAVEAT).
    st.warning(
        "**Closure artifact — the wing spar stations could not be derived.** The "
        "unbalanced moment was reacted by a self-equilibrated correction spread "
        "over the *whole* body instead of the wing carry-through: the beam "
        "closes, but the correction has no physical source (it relieves "
        "wing-region bending and loads the tail cone), and no fitting loads are "
        "reported. Define the wing planform and its front/rear spar chord "
        "fractions on the **Configuration & Layout** page to get the Ch 15 "
        "carry-through reaction. The same caveat is stamped into the exported "
        "`fuselage_loads.bdf` cards.",
        icon="⚠️",
    )

sel = st.selectbox("Show condition", [r.case for r in results],
                   key=widget_key("fus_show_condition"))
res = next(r for r in results if r.case == sel)

c1, c2, c3 = st.columns(3)
c1.metric(f"Closure ΣFz ({si_scalar_label('lbf', system)}, LIMIT)",
          f"{to_si_scalar(sum(s.fz for s in res.stations), 'lbf', system):,.2f}")
# Terminal Myy is the moment-closure residual: the p103 spar solve drives it to
# ~0, and it is the number that was non-zero while M4-1 was open.
c2.metric(f"Closure terminal Myy ({si_scalar_label('lb-in', system)}, LIMIT)",
          f"{to_si_scalar(res.stations[-1].myy, 'lb-in', system):,.2f}")
c3.metric("Stations", str(len(res.stations)))

if res.r_front is not None and res.r_rear is not None:
    st.subheader("Wing-attach reactions (LIMIT)")
    f1, f2, f3 = st.columns(3)
    f1.metric(f"R front @ X = {to_si_scalar(res.x_front, 'in', system):,.2f} "
              f"{si_scalar_label('in', system)} ({si_scalar_label('lbf', system)}, LIMIT)",
              f"{to_si_scalar(res.r_front, 'lbf', system):,.1f}")
    f2.metric(f"R rear @ X = {to_si_scalar(res.x_rear, 'in', system):,.2f} "
              f"{si_scalar_label('in', system)} ({si_scalar_label('lbf', system)}, LIMIT)",
              f"{to_si_scalar(res.r_rear, 'lbf', system):,.1f}")
    f3.metric(f"Unbalanced moment ({si_scalar_label('lb-in', system)}, LIMIT)",
              f"{to_si_scalar(res.m_unbalanced, 'lb-in', system):,.0f}")
    st.caption(
        ("⚠️ Spar stations are **assumed** (module default chord fractions) — enter "
         "the wing front/rear spar fractions on the **Configuration & Layout** page "
         "to size the fittings on real geometry. "
         if res.spars_assumed else
         "Spar stations are derived from the **entered** wing spar chord fractions. ")
        + "These are the Ch 15 p103 fitting loads that react the unbalanced moment; "
        "the load table below **already carries them** as the carry-through "
        "distribution, so do not apply them again. The ULTIMATE fitting-load CSV "
        "is on the **Export** page."
    )

for title, attr, unit_key in [("Shear Sz", "sz", "lbf"), ("Bending Myy", "myy", "lb-in")]:
    unit = f"{si_scalar_label(unit_key, system)}, LIMIT"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[to_si_scalar(s.x, "in", system) for s in res.stations],
        y=[to_si_scalar(getattr(s, attr), unit_key, system) for s in res.stations],
        mode="lines+markers", line={"width": 3}))
    fig.update_layout(title=f"{title} — {sel}",
                      xaxis_title=f"Fuselage station X ({si_scalar_label('in', system)})",
                      yaxis_title=f"{title} ({unit})", height=320)
    st.plotly_chart(fig, width="stretch")

st.subheader("Net fuselage load table (LIMIT)")
st.caption(
    f"Columns: X ({si_scalar_label('in', system)}), Fz/Sz ({si_scalar_label('lbf', system)}), "
    f"Myy ({si_scalar_label('lb-in', system)})."
)
st.dataframe(pd.DataFrame(body_limit_rows(body_load_rows([res]), system)),
             hide_index=True, width="stretch")

# Two downloads, named by *channel* (#192): both are LIMIT since note 49
# OR-116, so the labels name what differs -- the analysis table (this page's
# converted, unit-suffixed rows, L-8i -- ``limit_csv`` owns both) vs the sbeam
# bridge's body span CSV (per-case SF column), the same content family the
# Export page ships. The ``*_ULT.csv`` name is stale until OR-81 (0.8.3).
_dl = st.columns(2)
_dl[0].download_button("Download fuselage loads — analysis table (CSV)",
                       body_limit_csv(body_load_rows(results), system),
                       file_name="net_fuselage_loads_LIMIT.csv", mime="text/csv")
_dl[1].download_button("Download fuselage loads — sbeam bridge (CSV)",
                       sb.body_span_load_csv(results, system=system),
                       file_name="net_fuselage_loads_ULT.csv", mime="text/csv")
st.caption(
    "Both files are **LIMIT**; each row states the 14 CFR 23.303 factor it does "
    "not apply. The analysis table carries a `Basis` column and matches the "
    "table above; the sbeam bridge is the body span CSV also available on the "
    "**Export** page."
)
