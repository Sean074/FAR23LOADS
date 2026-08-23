"""Streamlit page for FAR 23 weight & mass properties (Step G3 consolidation).

One page of the multi-page app; run the suite with:  streamlit run app/Home.py

The single owner of all weight/mass data (decision G-2: nothing weight is asked
downstream). Four tabs, each a formerly-separate page:

* **Estimate** -- WTESTIMA statistical empty-weight / MTOW sanity figure.
* **Weight, CG & Inertia** -- WTONECG itemised mass data base → weight/CG/inertia.
  Apply persists the derived ``Project.mass`` slice (M4-17a), the single source of
  IZZ for ONENGOUT, of the "Weight DB" CG estimate, and of the landing waterline.
* **Payload Cases** -- the shared named (weight, CG) loading scenarios
  (``Project.weight.cg_cases``) used by the CG envelope and the FLTLOADS balance.
* **Weight / CG Envelope** -- WTENV structural CG limits, loadings and ballast.

Inputs are Imperial (the manual's units); results follow the sidebar Imperial/SI
toggle (``Home.py``). Each tab is a function so a missing-prerequisite guard can
``return`` without ``stop_page()`` killing the sibling tabs.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_shell.components import gate, page_header, unit_number_input, workflow_page_link
from app_shell.widget_keys import widget_key
from sloads import (
    GROUND_CASE_ROLE_ORDER,
    AnalysisKind,
    CgCase,
    EngineWeightType,
    GroundCaseRole,
    MassItem,
    MassItemKind,
    Project,
    UnitSystem,
    WeightEnvelopeInput,
    WeightEstimationInput,
    WeightInput,
    consistency_warnings,
    convert_results,
    mass_distribution,
    to_display,
    to_imperial_scalar,
)
from sloads import io as sloads_io
from sloads.cg_cases import max_landing_weight_estimate, seed_landing_cases
from sloads.export import mass_cards
from sloads.models import MassComponent
from sloads.modules.weight_envelope import envelope as compute_envelope
from sloads.modules.weight_envelope import loading_envelope_points
from sloads.modules.weight_estimate import estimate, estimate_to_mass_items
from sloads.modules.weight_onecg import refresh_mass, weights_and_inertia
from sloads.report import module_text_report
from sloads.report.methods import bdf_comment_block
from sloads.validation import wtenv_cg_limits

project, system, U = page_header("weight_mass", title="Weight & Mass Properties — FAR 23", banner=False)
st.caption(
    "The single home for all weight/mass data (WTESTIMA + WTONECG + WTENV). "
    "Estimate a starting weight, build the itemised mass data base (weight/CG/"
    "inertia), define the shared loading scenarios, and check the structural CG "
    "envelope. Inputs are Imperial; results follow the sidebar's Imperial/SI toggle."
)


# Fleet placement belongs at definition time: once MTOW/OEW/power are set here, the
# Aircraft Comparison page (in the Export phase) places this design against similar
# airplanes by wing loading, power loading and geometry. Link there rather than
# moving it (M2-5 — keeps workflow.py the single source of navigation truth).
workflow_page_link(
    "aircraft_comparison", label="→ Compare against similar aircraft (fleet W/S, W/P)",
    icon="📊",
    help="Place this design against a reference fleet — best checked once the design "
         "weights and installed power below are set.",
)

_ENGINE_TYPES = {
    "4-cycle reciprocating": EngineWeightType.RECIP_4CYCLE,
    "2-cycle reciprocating": EngineWeightType.RECIP_2CYCLE,
    "Turbocharged": EngineWeightType.TURBOCHARGED,
    "Turboprop": EngineWeightType.TURBOPROP,
    "Liquid-cooled": EngineWeightType.LIQUID_COOLED,
}
_ENGINE_LABELS = list(_ENGINE_TYPES)


# --------------------------------------------------------------------------- #
# Tab 1 -- Weight Estimate (WTESTIMA)
# --------------------------------------------------------------------------- #
def _tab_estimate(project: Project, system: UnitSystem, U: dict) -> None:
    existing = project.weight.estimation if project.weight and project.weight.estimation else None

    if project.is_concept:
        st.warning(
            "Concept mode (category C): this statistical estimate is **out of WTESTIMA's "
            "≤12,500 lb calibration band** and is shown as a GA sanity figure only. Use "
            "the itemized data base (Weight, CG & Inertia tab) as the design weight."
        )

    with st.form("weight_estimate_form"):
        st.subheader("Mission inputs")
        airplane = st.text_input("Airplane", value=existing.airplane if existing else "",
                                 key=widget_key("we_airplane"),
                                 help="Airplane name/label; used on the report and the fleet-comparison marker.")
        # No hard max_value caps: this is a concept-aware superset that must accept
        # airplanes beyond the GA band, so a loaded value can never exceed the widget's
        # own max. WTESTIMA's ≤12,500 lb band is surfaced as a warning, not enforced.
        # Step M2-6: the combined max-continuous power is single-sourced from the engine
        # list -- sum(engines[].max_cont_hp) -- unless overridden here. The engine sum is
        # shown for reference; the override value below is used only when the box is ticked
        # (or when no engine carries a max-continuous rating). The two power concepts stay
        # distinct: per-engine ratings on the Engine Mount page (torque/slipstream loads)
        # vs. this combined total the weight estimate correlates against.
        _engine_hp_sum = sum((e.max_cont_hp or 0.0) for e in project.engines)
        st.caption(
            f"Engine list total (Engine Mount page): **{to_display(_engine_hp_sum, 'power', system):.1f} "
            f"{U['power']}** — the weight estimate uses this unless you override it below."
        )
        override_hp = st.checkbox(
            "Override max continuous power for the weight estimate",
            value=existing.override_max_continuous_hp if existing else False,
            key=widget_key("we_override_hp"),
            help="Off: the estimate uses the engine-list total above. On: it uses the value "
                 "you enter here instead (they can legitimately differ for a first-cut estimate).")
        hp = unit_number_input(
            "Max continuous power override (total)",
            float(existing.max_continuous_hp) if existing else 0.0,
            kind="power", key="we_max_cont_hp", min_value=0.0,
            help="Combined total maximum continuous power. Applied only when the override box "
                 "is ticked (else the engine-list total is used). Separate from the per-engine "
                 "power on the Engine Mount page (engine-torque and flap-slipstream loads).")
        engines = st.number_input("Number of engines", min_value=1,
                                  value=existing.engines if existing else 1,
                                  key=widget_key("we_engines"),
                                  help="Engine count; the power above is the combined total, not per engine.")
        seats = st.number_input("Number of seats", min_value=1,
                                value=existing.seats if existing else 1,
                                key=widget_key("we_seats"),
                                help="Total design seats (crew + passengers). Seeds the Structural Speeds "
                                     "occupant count for the FAR 23 seat-limit check.")
        crew = st.number_input(
            "Flight crew", min_value=0,
            value=existing.crew if existing else 1,
            key=widget_key("we_crew"),
            help=(
                "Required flight crew (170 lb each). Carried in the operating empty "
                "weight (OEW = empty + crew×170), not the payload. The FAR 23 "
                "applicability check counts passenger seats = occupants − crew."
            ),
        )
        hours = st.number_input("Endurance at cruise power (hr)", min_value=0.0,
                                value=float(existing.cruise_hours) if existing else 0.0,
                                key=widget_key("we_hours"),
                                help="Mission endurance at cruise power; drives the estimated fuel weight "
                                     "(WTESTIMA, Ch 3).")
        baggage = unit_number_input(
            "Baggage weight", float(existing.baggage_lb) if existing else 0.0,
            kind="weight", key="we_baggage", min_value=0.0,
            help="Design baggage payload weight; part of the useful load.")
        pressurized = st.checkbox("Pressurized", value=existing.pressurized if existing else False,
                                  key=widget_key("we_pressurized"),
                                  help="Cabin pressurization adds a structural-weight allowance in the estimate.")
        default_idx = _ENGINE_LABELS.index(
            next((k for k, v in _ENGINE_TYPES.items() if existing and v == existing.engine_weight_type),
                 "4-cycle reciprocating")
        )
        engine_label = st.selectbox("Engine type", _ENGINE_LABELS, index=default_idx,
                                    key=widget_key("we_engine_type"),
                                    help="Engine class; selects the empty-weight correlation used for the "
                                         "powerplant weight (WTESTIMA, Ch 3).")
        applied = st.form_submit_button("Apply mission inputs", type="primary")

    if applied:
        inp = WeightEstimationInput(
            airplane=airplane,
            max_continuous_hp=hp,
            override_max_continuous_hp=bool(override_hp),
            engines=int(engines),
            seats=int(seats),
            crew=int(crew),
            cruise_hours=hours,
            baggage_lb=baggage,
            pressurized=pressurized,
            engine_weight_type=_ENGINE_TYPES[engine_label],
        )
        # Merge-write: keep the itemized data base and envelope; only the estimation
        # inputs are this tab's own.
        items = project.weight.items if project.weight else []
        envelope = project.weight.envelope if project.weight else None
        cg_cases = project.weight.cg_cases if project.weight else []
        project.weight = WeightInput(estimation=inp, items=items, envelope=envelope, cg_cases=cg_cases)
        st.session_state["project"] = project
        existing = inp

    if existing is None:
        st.info("No mission inputs yet -- fill in the form and Apply mission inputs.")
        return
    inp = existing

    # Resolve the max-continuous power the estimate correlates against the same way the
    # module does (Step M2-6): the engine-list total unless this estimate overrides it.
    _resolved_hp = (inp.max_continuous_hp if inp.override_max_continuous_hp
                    else (_engine_hp_sum or inp.max_continuous_hp))
    inp = replace(inp, max_continuous_hp=_resolved_hp)

    try:
        results = estimate(inp)
    except ValueError as exc:
        st.error(f"Could not estimate weights: {exc}")
        return

    display_results = convert_results(results, system)
    for r in display_results:
        with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
            rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.subheader("Seed the weight data base")
    st.caption(
        "Copy the estimated component weights into the **Weight, CG & Inertia** tab's "
        "data base as empty-weight items. Stations and per-item inertias start at zero "
        "for you to fill in. This replaces any items already entered there."
    )
    if st.button("Seed Weight, CG & Inertia from this estimate", key="seed_weight_db"):
        seed_items = estimate_to_mass_items(inp)
        project.weight = WeightInput(
            estimation=inp, items=seed_items, envelope=project.weight.envelope,
            cg_cases=project.weight.cg_cases,
            max_landing_weight_lb=project.weight.max_landing_weight_lb,
            max_takeoff_weight_lb=project.weight.max_takeoff_weight_lb,
        )
        st.session_state["project"] = project
        st.success(
            f"Seeded {len(seed_items)} component(s) into the weight data base. "
            "Open the Weight, CG & Inertia tab to set their stations."
        )

        # The CSV writer converts internally (M4-20 step 3), so it takes the *raw*
        # Imperial results plus the system; the text report is unit-agnostic and
        # takes the already-converted display copy. Passing the display copy to
        # both would be the double conversion step 3's guard exists to prevent.
    st.download_button(
        "Download weight estimate (CSV)",
        sloads_io.load_cases_csv(results, system=system),
        file_name="weight_estimate.csv", mime="text/csv", key="dl_est_csv")
    st.download_button(
        "Download weight estimate (text)", module_text_report("Weight estimate", display_results),
        file_name="weight_estimate.txt", mime="text/plain", key="dl_est_txt")


# --------------------------------------------------------------------------- #
# Tab 2 -- Weight, CG & Inertia (WTONECG)
# --------------------------------------------------------------------------- #
def _tab_cg_inertia(project: Project, system: UnitSystem, U: dict) -> None:
    _KINDS = [k.value for k in MassItemKind]
    #: The component tag drives which structural beam carries each item -- the
    #: fuselage station table, the wing panel distribution and the empennage
    #: surface weights are all derived from it (``sloads.mass_distribution``).
    #: ``""`` means untagged, which infers ``fuselage``; it is a real state and
    #: has to be selectable, not a blank that silently becomes something else.
    _COMPONENTS = [""] + [c.value for c in MassComponent]
    items = project.weight.items if project.weight and project.weight.items else []

    def _disp(v: float, kind: str) -> float:
        return to_display(v, kind, system)

    if items:
        default_df = pd.DataFrame([
            {"name": it.name, "weight_lb": _disp(it.weight_lb, "weight"),
             "x": _disp(it.x, "length"), "y": _disp(it.y, "length"), "z": _disp(it.z, "length"),
             "ixx": _disp(it.ixx, "inertia_lbin2"), "iyy": _disp(it.iyy, "inertia_lbin2"),
             "izz": _disp(it.izz, "inertia_lbin2"), "kind": it.kind.value,
             "component": it.component.value if it.component else "",
             "consumable": it.consumable}
            for it in items
        ])
    else:
        default_df = pd.DataFrame([
            {"name": "", "weight_lb": 0.0, "x": 0.0, "y": 0.0, "z": 0.0,
             "ixx": 0.0, "iyy": 0.0, "izz": 0.0, "kind": "empty", "component": "",
             "consumable": False}
        ])

    st.subheader("Weight data base")
    st.caption(
        f"Each row is a component: weight ({U['weight']}) at station x/y/z ({U['length']}), "
        f"with its own inertia ({U['inertia_lbin2']})."
    )
    with st.expander("ℹ️ Parameter guide", expanded=False):
        st.markdown(
            "One row per mass item; the totals below are the loading's weight, CG and moments of inertia "
            "(WTONECG, Ch 8):\n\n"
            "- **weight_lb** — the item weight.\n"
            "- **x / y / z** — the item CG station: X fuselage station (aft of the nose datum), Y butt line "
            "(+right of centreline), Z waterline (+up).\n"
            "- **ixx / iyy / izz** — the item's *own* moment of inertia about its CG (lb·in²) — the local term; "
            "the program adds the parallel-axis (transfer) term from x/y/z automatically, so leave these 0 for "
            "a point mass.\n"
            "- **kind** — mass category: *empty* (manufacturer's empty weight), *minimum* (always-present "
            "useful load), *discretionary* (optional payload/fuel). Drives the CG-envelope loadings.\n"
            "- **component** — which structural component *carries* the item, and so which distributed "
            "load set its weight enters: *wing* (the panel distribution, plus anything hung on it), "
            "*fuselage* (the Ch 15 body beam), *htail* / *vtail* (the empennage surface weight the "
            "spanwise tail loads smear over the planform). This is the **only** place tail mass is "
            "entered — the Tail Span Loads page derives it from these rows. Blank means untagged and is "
            "treated as *fuselage*.\n\n"
            "*`kind` says when an item is aboard; `component` says what holds it up — they are "
            "independent.*\n\n"
            "*Roll Ixx is about the X axis, pitch Iyy about Y, yaw Izz about Z.*"
        )
    _COLUMN_CONFIG = {
        "weight_lb": st.column_config.NumberColumn(f"weight_lb ({U['weight']})"),
        "x": st.column_config.NumberColumn(f"x ({U['length']})"),
        "y": st.column_config.NumberColumn(f"y ({U['length']})"),
        "z": st.column_config.NumberColumn(f"z ({U['length']})"),
        "ixx": st.column_config.NumberColumn(f"ixx ({U['inertia_lbin2']})"),
        "iyy": st.column_config.NumberColumn(f"iyy ({U['inertia_lbin2']})"),
        "izz": st.column_config.NumberColumn(f"izz ({U['inertia_lbin2']})"),
        "kind": st.column_config.SelectboxColumn("kind", options=_KINDS),
        "component": st.column_config.SelectboxColumn(
            "component", options=_COMPONENTS,
            help="Which structural component carries this weight. Drives the "
                 "fuselage beam stations, the wing panel mass and the empennage "
                 "surface weights. Blank = untagged, treated as fuselage."),
        "consumable": st.column_config.CheckboxColumn(
            "consumable",
            help="Mission fuel and anything else burned or expended down to a "
                 "partial value. Deriving a loading for a GROUND case burns these "
                 "down proportionally before dropping any payload — a design "
                 "landing weight is fuel burned off (14 CFR 23.473(b)/(c)), not a "
                 "passenger left behind. Reserve fuel stays aboard, so tag it "
                 "*minimum* and leave this clear."),
    }
    with st.form("weight_items_form"):
        edited = st.data_editor(
            default_df, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config=_COLUMN_CONFIG, key=widget_key(f"weight_items_{system.value}"),
        )
        applied = st.form_submit_button("Apply weight items", type="primary")

    if applied:
        def _imp(v: float, kind: str) -> float:
            return to_imperial_scalar(v, kind, system)

        mass_items = []
        for _, row in edited.iterrows():
            try:
                kind = MassItemKind(str(row.get("kind", "empty")))
            except ValueError:
                kind = MassItemKind.EMPTY
            # Untagged stays untagged: ``None`` is the documented "infer it"
            # state, and coercing a blank to ``fuselage`` here would make the
            # inference invisible on the page that owns the data.
            raw_component = str(row.get("component", "") or "").strip()
            try:
                component = MassComponent(raw_component) if raw_component else None
            except ValueError:
                component = None
            mass_items.append(MassItem(
                name=str(row.get("name", "")),
                weight_lb=_imp(float(row.get("weight_lb", 0) or 0), "weight"),
                x=_imp(float(row.get("x", 0) or 0), "length"),
                y=_imp(float(row.get("y", 0) or 0), "length"),
                z=_imp(float(row.get("z", 0) or 0), "length"),
                ixx=_imp(float(row.get("ixx", 0) or 0), "inertia_lbin2"),
                iyy=_imp(float(row.get("iyy", 0) or 0), "inertia_lbin2"),
                izz=_imp(float(row.get("izz", 0) or 0), "inertia_lbin2"),
                kind=kind,
                component=component,
                consumable=bool(row.get("consumable", False)),
            ))
        # Merge-write: keep estimation, envelope and cg_cases owned by other tabs.
        estimation = project.weight.estimation if project.weight else None
        envelope = project.weight.envelope if project.weight else None
        cg_cases = project.weight.cg_cases if project.weight else []
        project.weight = WeightInput(
            estimation=estimation, items=mass_items, envelope=envelope,
            cg_cases=cg_cases,
            max_landing_weight_lb=project.weight.max_landing_weight_lb if project.weight else 0.0,
            max_takeoff_weight_lb=project.weight.max_takeoff_weight_lb if project.weight else 0.0,
        )
        # M4-17a: the derived mass-properties slice, so the weight_mass step's
        # produces="mass" turns ✅ and the downstream consumers have a real source
        # -- ONENGOUT's IZZ, configuration.cg_estimate's "Weight DB" branch and
        # the Landing Loads waterline seed. One owner for both GUIs (#62):
        # refresh_mass derives from the items as applied, or clears the slice
        # when they derive nothing, rather than leaving a stale loading behind.
        refresh_mass(project)
        if project.mass is None:
            st.warning("Weight items applied, but they derive no mass slice -- "
                       "add at least one item with a non-zero weight.")
        st.session_state["project"] = project

    if not project.weight or not project.weight.items:
        st.info("No weight items yet -- fill in the data base above and Apply weight items.")
        return

    try:
        raw_result = weights_and_inertia(project.weight.items)
    except ValueError as exc:
        st.warning(f"Add at least one non-zero weight item: {exc}")
        return

    # Input-consistency check (Step E3): CG vs the WTENV structural envelope.
    for _w in consistency_warnings(project):
        if _w.page == "weight_cg_inertia":
            st.warning(_w.message)

    result = convert_results([raw_result], system)[0]
    st.subheader(f"FAR {result.far_reference} — {result.title}")
    rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in result.values]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if result.note:
        st.caption(result.note)

    # CG marker + mass-distribution plot (Step E3).
    xbar_in = next((v.value for v in raw_result.values if v.key == "xbar_fus_station"), None)
    if xbar_in is not None:
        st.subheader("CG & mass distribution")
        st.caption(
            f"Each stem is an item's weight ({U['weight']}) at its fuselage station "
            f"x ({U['length']}); the dashed line is the loading CG."
        )
        _kind_color = {"empty": "#1f77b4", "minimum": "#2ca02c", "discretionary": "#ff7f0e"}
        fig = go.Figure()
        for kind in ("empty", "minimum", "discretionary"):
            pts = [it for it in project.weight.items if it.kind.value == kind and it.weight_lb]
            if not pts:
                continue
            xs = [to_display(it.x, "length", system) for it in pts]
            ws_ = [to_display(it.weight_lb, "weight", system) for it in pts]
            fig.add_trace(go.Bar(x=xs, y=ws_, name=kind, width=0.8,
                                 marker_color=_kind_color[kind],
                                 hovertext=[it.name for it in pts]))
        fig.add_vline(x=to_display(xbar_in, "length", system), line_dash="dash",
                      line_color="#d62728", annotation_text="CG", annotation_position="top")
        limits = wtenv_cg_limits(project)
        if limits is not None:
            fwd, aft = limits
            for x_in, lbl in ((fwd, "fwd limit"), (aft, "aft limit")):
                fig.add_vline(x=to_display(x_in, "length", system), line_dash="dot",
                              line_color="#7f7f7f", annotation_text=lbl, annotation_position="bottom")
        fig.update_layout(barmode="overlay", height=380, legend={"orientation": "h"},
                          xaxis_title=f"Fuselage station x ({U['length']})",
                          yaxis_title=f"Item weight ({U['weight']})")
        st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "Download weight/CG/inertia (CSV)",
        sloads_io.load_cases_csv([result], system=system),
        file_name="weight_cg_inertia.csv", mime="text/csv", key="dl_cg_csv")
    st.download_button(
        "Download weight/CG/inertia (text)",
        module_text_report("Weight, CG and inertia", convert_results([result], system)),
        file_name="weight_cg_inertia.txt", mime="text/plain", key="dl_cg_txt")


# --------------------------------------------------------------------------- #
#: The "no landing role" selectbox entry. A blank string reads as an unset cell in
#: ``st.data_editor``; a named option makes "this case is not one of LANDLOAD's
#: three" an explicit choice rather than an omission.
_NO_ROLE = "—"


def _analyses(row) -> set:
    """The ``analyses`` set from the two checkbox columns (decision G-3c)."""
    out = set()
    if bool(row.get("flight", False)):
        out.add(AnalysisKind.FLIGHT)
    if bool(row.get("ground", False)):
        out.add(AnalysisKind.GROUND)
    return out


def _role(row):
    """The ``GroundCaseRole`` from the selectbox column, or ``None``."""
    raw = str(row.get("role", _NO_ROLE) or _NO_ROLE)
    return GroundCaseRole(raw) if raw != _NO_ROLE else None


# --------------------------------------------------------------------------- #
# Tab 3 -- Payload Cases (shared loading scenarios, Project.weight.cg_cases)
# --------------------------------------------------------------------------- #
def _tab_payload_cases(project: Project, system: UnitSystem, U: dict) -> None:
    st.caption(
        "Named weight/CG loading scenarios, defined once here and shared by every "
        "analysis — the Weight / CG Envelope chart, the Flight Envelope (FLTLOADS) "
        "balance and, since decision G-3, the LANDLOAD ground conditions. **This "
        "tab is the sole editor**: tag each case with the analyses it is run for, "
        "and give the three landing loadings their role."
    )
    if project.weight is None or not project.weight.items:
        st.warning("No weight data base found. Add component weights on the "
                   "**Weight, CG & Inertia** tab first.")
        return

    existing = project.weight.cg_cases
    with st.form("payload_cases_form"):
        st.subheader("Loading scenarios")
        st.caption(
            "One row per named CG case (e.g. forward/aft/ramp loadings): total weight, "
            "the resultant fuselage station / waterline of the CG, the analyses it is "
            "run for, and — for the three GROUND loadings LANDLOAD cycles — its role. "
            "A case run for **nothing** is an entry error, not a state: it disappears "
            "from every result while still occupying a row."
        )
        default_rows = pd.DataFrame(
            [[c.name, to_display(c.weight_lb, "weight", system),
              to_display(c.xcg, "length", system), to_display(c.zcg, "length", system),
              AnalysisKind.FLIGHT in c.analyses, AnalysisKind.GROUND in c.analyses,
              c.role.value if c.role else _NO_ROLE] for c in existing]
            or [["CG1", 0.0, 0.0, 0.0, True, False, _NO_ROLE]],
            columns=["name", "weight_lb", "xcg", "zcg", "flight", "ground", "role"],
        )
        payload_cols = {
            "weight_lb": st.column_config.NumberColumn(f"weight_lb ({U['weight']})"),
            "xcg": st.column_config.NumberColumn(f"xcg ({U['length']})"),
            "zcg": st.column_config.NumberColumn(f"zcg ({U['length']})"),
            "flight": st.column_config.CheckboxColumn(
                "FLIGHT", help="Run for the V-n envelope, the balancing tail loads "
                               "and SELECT."),
            "ground": st.column_config.CheckboxColumn(
                "GROUND", help="Run for the landing / ground-handling families "
                               "(14 CFR 23.471-23.511)."),
            "role": st.column_config.SelectboxColumn(
                "Landing role", options=[_NO_ROLE] + [r.value for r in GROUND_CASE_ROLE_ORDER],
                help="LANDLOAD consumes exactly one case per role, in role order "
                     "(UG fig 18.2). A GROUND case with no role is assembled and "
                     "distributed but never fed to LANDLOAD."),
        }
        rows = st.data_editor(
            default_rows, column_config=payload_cols, num_rows="dynamic", hide_index=True,
            use_container_width=True, key=widget_key(f"payload_cases_editor_{system.value}"),
        )
        applied = st.form_submit_button("Apply", type="primary")

    if applied:
        cases = [
            CgCase(name=str(r["name"]), weight_lb=to_imperial_scalar(float(r["weight_lb"]), "weight", system),
                   xcg=to_imperial_scalar(float(r["xcg"]), "length", system),
                   zcg=to_imperial_scalar(float(r["zcg"]), "length", system),
                   analyses=_analyses(r), role=_role(r))
            for _, r in rows.iterrows()
            if pd.notna(r["weight_lb"]) and pd.notna(r["xcg"]) and str(r["name"]).strip()
        ]
        # This tab owns cg_cases exclusively; merge to keep estimation/items/envelope
        # and the two design-weight SSOTs the Weight/CG tab owns.
        w = project.weight
        project.weight = WeightInput(
            estimation=w.estimation, items=w.items, envelope=w.envelope, cg_cases=cases,
            max_landing_weight_lb=w.max_landing_weight_lb,
            max_takeoff_weight_lb=w.max_takeoff_weight_lb,
        )
        st.session_state["project"] = project
        st.success(f"{len(cases)} loading scenario(s) applied.")
        existing = cases

    # The three roled GROUND loadings LANDLOAD needs -- offered, never written
    # silently, and refused outright when any cell has no real source (M4-17c).
    if not [c for c in existing if c.role is not None]:
        st.subheader("Landing loadings")
        seeded, missing = seed_landing_cases(project)
        if missing:
            st.warning(
                "The three LANDLOAD loadings (aft max landing / fwd max landing / "
                "fwd light; UG fig 18.2) cannot be seeded — no source for "
                + "; ".join(missing) + ". Enter them as GROUND-tagged rows above "
                "with a role, or fill those sources first. A cell is never "
                "defaulted to zero: a zero waterline puts the CG on the ground "
                "line and inverts the nose-gear reaction.")
        elif st.button("Seed the three landing loadings from WTENV",
                       key="seed_landing_cases"):
            w = project.weight
            project.weight = WeightInput(
                estimation=w.estimation, items=w.items, envelope=w.envelope,
                cg_cases=list(w.cg_cases) + seeded,
                max_landing_weight_lb=w.max_landing_weight_lb,
                max_takeoff_weight_lb=w.max_takeoff_weight_lb,
            )
            st.session_state["project"] = project
            st.success("Seeded the three landing loadings — **confirm the forward "
                       "vs aft stations**, which WTENV cannot distinguish per "
                       "loading.")
            existing = project.weight.cg_cases

    if not existing:
        st.info("No loading scenarios defined yet — add rows above and Apply.")
        return

    st.subheader("Current scenarios")
    st.dataframe(
        pd.DataFrame([
            {"Name": c.name, f"Weight ({U['weight']})": to_display(c.weight_lb, "weight", system),
             f"Xcg ({U['length']})": to_display(c.xcg, "length", system),
             f"Zcg ({U['length']})": to_display(c.zcg, "length", system),
             "Analyses": ", ".join(sorted(a.value for a in c.analyses)) or "— none —",
             "Landing role": c.role.value if c.role else ""}
            for c in existing
        ]),
        hide_index=True, use_container_width=True,
    )


# --------------------------------------------------------------------------- #
# Tab 4 -- Weight / CG Envelope (WTENV)
# --------------------------------------------------------------------------- #
def _tab_envelope(project: Project, system: UnitSystem, U: dict) -> None:
    st.caption(
        "Structural CG limits, minimum/maximum loadings, the discretionary-loading "
        "envelope and ballast (WTENV)."
    )
    if project.weight is None or not project.weight.items:
        st.warning("No weight data base found. Add component weights on the "
                   "**Weight, CG & Inertia** tab first.")
        return
    if project.geometry is None or project.geometry.by_name("wing") is None:
        gate("No wing geometry found. Define the wing on the **Geometry** page "
             "first (WTENV needs the wing XLEMAC/MAC).", "configuration_layout")
        return

    existing = project.weight.envelope

    # --- The two design weights (decisions G-4 / G-14) --------------------- #
    # Certified airplane-level limits, not properties of a loading, so they are
    # entered once here and read everywhere else through ``sloads.cg_cases``.
    st.subheader("Design weights")
    st.caption(
        "MTOW and MLW are **single inputs** and the sole owners of those two "
        "numbers: LANDLOAD's WR = MTOW/MLW, the max-landing loadings' weight and "
        "the FAR 23 12,500 lb applicability gate all read them from here. The "
        "ordering chain OEW ≤ MLW ≤ MTOW ≤ Σ items is checked below."
    )
    dw1, dw2 = st.columns(2)
    mtow_ssot = unit_number_input(
        "Max take-off weight, MTOW", float(project.weight.max_takeoff_weight_lb),
        kind="weight", key="wm_mtow", min_value=0.0, container=dw1,
        help="A single scalar, assumed constant between the forward and aft CG "
             "limits (decision G-14). The item-database total is an upper bound, "
             "not this: a database can hold full fuel *and* full payload at once.")
    mlw_ssot = unit_number_input(
        "Max landing weight, MLW", float(project.weight.max_landing_weight_lb),
        kind="weight", key="wm_mlw", min_value=0.0, container=dw2,
        help="Typically 0.95·MTOW (14 CFR 23.473(b)/(c)). Never derived silently — "
             "the estimate below is offered for acceptance, not written for you.")
    _floor = max_landing_weight_estimate(project)
    if _floor:
        st.caption(
            "MLW estimate from the item database — OEW + max payload + reserve fuel "
            f"(consumable mission fuel excluded): **{to_display(_floor, 'weight', system):,.0f} "
            f"{U['weight']}**. It is a *floor*: entering less means the airplane "
            "cannot land at MLW with full payload and reserves.")

    # Design weight for the envelope: read-through from the MTOW SSOT entered
    # above (the same source Structural Speeds reads), so it is not entered a
    # third time. The item-database total was the fallback until 2026-08-15 --
    # it is the ceiling of OEW <= MLW <= MTOW <= sum(items), not a design weight,
    # and it stood 964 lb / 1,800 lb above MTOW on two shipped fixtures. With MTOW
    # unentered the read-through simply has nothing to offer, and the override
    # below is the way in.
    mtow_upstream = mtow_ssot

    st.subheader("Structural limits")
    override_weight = st.checkbox(
        "Override gross weight", value=False, key=widget_key("wenv_override_weight"),
        help="Uncheck to use the MTOW entered above (decision G-14's single owner).",
    )
    if not mtow_upstream and not override_weight:
        st.info(
            "No max take-off weight entered above, so there is nothing to read "
            "through — tick **Override gross weight** to enter the envelope's "
            "gross weight directly, or fill MTOW.")
    if override_weight or not mtow_upstream:
        gross = unit_number_input(
            "Gross weight",
            float(existing.gross_weight if existing and existing.gross_weight else mtow_upstream),
            kind="weight", key="wenv_gross_weight", min_value=1.0)
    else:
        gross = mtow_upstream
        st.caption(
            f"Gross weight from the MTOW entered above: "
            f"**{to_display(mtow_upstream, 'weight', system):,.0f} {U['weight']}**.")
    aft = st.number_input("Aft gross CG (% MAC)", min_value=0.0, max_value=100.0,
                          value=float(existing.aft_gross_pct_mac) if existing else 31.0,
                          key=widget_key("wenv_aft_pct_mac"))
    fwd = st.number_input("Forward gross CG (% MAC)", min_value=0.0, max_value=100.0,
                          value=float(existing.fwd_gross_pct_mac) if existing else 20.0,
                          key=widget_key("wenv_fwd_pct_mac"))
    reg = st.number_input("Forward regardless CG (% MAC)", min_value=0.0, max_value=100.0,
                          value=float(existing.fwd_regardless_pct_mac) if existing else 13.0,
                          key=widget_key("wenv_reg_pct_mac"))
    reg_w = unit_number_input(
        "Forward regardless weight",
        float(existing.fwd_regardless_weight if existing else 2800.0),
        kind="weight", key="wenv_reg_w", min_value=1.0)

    inp = WeightEnvelopeInput(
        gross_weight=gross, aft_gross_pct_mac=aft, fwd_gross_pct_mac=fwd,
        fwd_regardless_pct_mac=reg, fwd_regardless_weight=reg_w,
    )
    project.weight = WeightInput(
        estimation=project.weight.estimation, items=project.weight.items, envelope=inp,
        cg_cases=project.weight.cg_cases,
        max_landing_weight_lb=mlw_ssot, max_takeoff_weight_lb=mtow_ssot,
    )
    st.session_state["project"] = project

    try:
        raw_results = compute_envelope(project, inp)
    except (ValueError, ZeroDivisionError) as exc:
        st.error(f"Could not compute the weight envelope: {exc}")
        return

    # Loading-envelope chart: forward boundary + structural limits + the shared
    # loading scenarios (Project.weight.cg_cases) overlaid read-only.
    limits_by_label = {v.label: v.value for v in raw_results[1].values}
    fwd_seq = loading_envelope_points(project)
    fig = go.Figure()
    if fwd_seq:
        fig.add_trace(go.Scatter(
            x=[x for _w, x in fwd_seq], y=[w for w, _x in fwd_seq],
            mode="lines+markers", name="Forward loading envelope",
        ))
    for label, key in [("Aft gross", "Aft gross station"), ("Forward gross", "Forward gross station"),
                       ("Forward regardless", "Forward regardless station")]:
        if key in limits_by_label:
            fig.add_vline(x=limits_by_label[key], line_dash="dash",
                          annotation_text=label, annotation_position="top")
    if project.weight.cg_cases:
        fig.add_trace(go.Scatter(
            x=[c.xcg for c in project.weight.cg_cases], y=[c.weight_lb for c in project.weight.cg_cases],
            mode="markers+text", name="Loading scenarios",
            text=[c.name for c in project.weight.cg_cases], textposition="top center",
            marker={"size": 10, "symbol": "diamond"},
        ))
    fig.update_layout(title="Weight / CG envelope", xaxis_title="Fuselage station (in)",
                      yaxis_title="Weight (lb)", legend={"orientation": "h"}, height=440)
    st.plotly_chart(fig, use_container_width=True)
    if not project.weight.cg_cases:
        st.caption(
            "No loading scenarios yet — define them on the **Payload Cases** tab to "
            "overlay them here."
        )

    results = convert_results(raw_results, system)
    for r in results:
        with st.expander(f"FAR {r.far_reference} — {r.title}", expanded=True):
            rows = [{"Quantity": v.label, "Value": v.value, "Units": v.units} for v in r.values]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            if r.note:
                st.caption(r.note)

    st.download_button(
        "Download weight envelope (CSV)",
        sloads_io.load_cases_csv(results, system=system),
        file_name="weight_envelope.csv", mime="text/csv", key="dl_env_csv")
    st.download_button(
        "Download weight envelope (text)",
        module_text_report("Weight envelope", convert_results(results, system)),
        file_name="weight_envelope.txt", mime="text/plain", key="dl_env_txt")


def _tab_mass_export(project, system, U) -> None:
    """CONM2 / MASSSET mass model — the independent check sbeam can contradict.

    The FORCE/MOMENT deck's inertia half is computed by the same code that
    writes it, so nothing outside sloads can disagree with it. This gives sbeam
    a mass model it parses for itself."""
    st.subheader("CONM2 mass model")
    st.caption(
        "The itemized weight database as `CONM2` cards, with one `MASSSET` per "
        "payload case sloads can actually derive as a loading. sbeam applies the "
        "case acceleration to its own parse of this and recovers the nodal "
        "inertia loads — an external check on the half of the load set that has "
        "no printed oracle.")

    if project.weight is None or not project.weight.items:
        gate("Enter the itemized weight data base on the **Weight, CG & Inertia** "
             "tab first.", "weight_mass")
        return

    loadings = mass_distribution.derive_case_loadings(project)
    rows = []
    for ld in loadings:
        rows.append({
            "Payload case": ld.name,
            "Exported": "yes" if ld.derivable else "no",
            "Loading": "entered" if ld.entered else "derived",
            f"Weight ({U['weight']})": f"{to_display(ld.weight_lb, 'weight', system):.0f}",
            f"X cg ({U['length']})": f"{to_display(ld.cg_x, 'length', system):.2f}",
            f"Ballast ({U['weight']})": (
                f"{to_display(ld.ballast.weight_lb, 'weight', system):.0f} "
                f"({ld.ballast_fraction * 100:.1f} %)" if ld.ballast else "none"),
            "Note": ld.note,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if any(not ld.derivable for ld in loadings):
        st.info(
            "A payload case is exported only when the weight database can "
            "actually produce it as a loading — the discretionary items aboard "
            "plus a credible ballast weight. A case needing a large fictitious "
            "ballast is a CG point, not a loading, and exporting it would put "
            "invented mass into the very model that exists to check the real one.")

    st.warning(
        "**Do not apply the mass model together with the FORCE/MOMENT deck.** "
        "Those cards are the *total* applied load and already contain inertia; "
        "accelerating the masses as well counts it twice.")

    # Stamped like every other BDF the suite writes (G8.3 / review F-D2): a mass
    # model forwarded on its own still states its unit system -- and a CONM2 set
    # whose M is read as weight is wrong by 386x in a file that parses cleanly.
    stamp = bdf_comment_block(project, scope="full case set", system=system)
    try:
        fragment = mass_cards.conm2_fragment(project, header_comment=stamp,
                                             system=system)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.download_button(
        "Download CONM2 + MASSSET fragment (BDF)", fragment,
        file_name="mass_model.bdf", mime="text/plain", key="dl_conm2_fragment")
    for label, build, name, key in (
        ("Download runnable mass-check deck (BDF)", mass_cards.mass_check_deck,
         "mass_check.bdf", "dl_mass_check"),
        ("Download sloads inertia set, for comparison only (BDF)",
         mass_cards.inertia_only_cards, "inertia_only.bdf", "dl_inertia_only"),
    ):
        try:
            text = build(project, header_comment=stamp, system=system)
        except ValueError as exc:
            st.caption(f"No {name}: {exc}")
            continue
        st.download_button(label, text, file_name=name, mime="text/plain", key=key)


_tab_est, _tab_cg, _tab_pl, _tab_env, _tab_mx = st.tabs(
    ["Estimate", "Weight, CG & Inertia", "Payload Cases", "Weight / CG Envelope",
     "Mass Export"]
)
with _tab_est:
    _tab_estimate(project, system, U)
with _tab_cg:
    _tab_cg_inertia(project, system, U)
with _tab_pl:
    _tab_payload_cases(project, system, U)
with _tab_env:
    _tab_envelope(project, system, U)
with _tab_mx:
    _tab_mass_export(project, system, U)
