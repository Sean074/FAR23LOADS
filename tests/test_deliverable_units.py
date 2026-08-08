"""Deliverable unit sets — M4-20 step 1.

Every deliverable renders in the unit system the user selected
(``docs/10_standard/00_program_overview.md`` §Units; ``SUMMARY_REPORT.md`` §3.5).
This file pins the unit *set* those writers will be handed, before any writer
consumes it:

* the **Imperial identity** — an all-1.0 set, so a writer needs no
  ``if system == IMPERIAL`` branch and Imperial output cannot drift;
* the **dimensional identity** ``moment == force × length`` for the solver
  channel, which is what stops an ``N·m`` moment reaching a deck whose GRIDs are
  in mm (decision D-19: a silent 1000× torsion error);
* the **aviation carve-out** — KEAS and altitude are never converted;
* a **standing guard** that every load unit the renderer knows has an SI mapping,
  so the next unit added without one fails here rather than shipping a mixed-unit
  table.

Plan: ``docs/30_future/06_m4-20_deliverable_units_plan.md`` §4 step 1.
"""

from __future__ import annotations

import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli  # noqa: E402
from sloads import io, registry  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.models import ConditionResult, LoadValue, Project
from sloads.registry import run_all_modules  # noqa: E402
from sloads.report.methods import (  # noqa: E402
    bdf_comment_block,
    csv_comment_block,
    methods_statement,
    strip_comment_lines,
)
from sloads.report.render import _LOAD_UNITS, _ULT_UNITS, ultimate_units  # noqa: E402
from sloads.units import (  # noqa: E402
    _RESULT_TO_SI,
    Channel,
    UnitSystem,
    convert_results,
    deliverable_units,
    unit_system_from,
    units_statement,
)

_DIMENSIONS = ("force", "length", "moment", "torque", "pressure")


# --------------------------------------------------------------------------- #
# The Imperial identity
# --------------------------------------------------------------------------- #
def test_imperial_is_the_all_one_identity():
    """Imperial factors are exactly 1.0 in both channels.

    This is the property the "Imperial output is unchanged" guarantee rests on:
    a writer multiplies unconditionally and the Imperial path is arithmetically
    the same code, not a separate branch that could diverge.
    """
    for channel in (Channel.HUMAN, Channel.SOLVER):
        u = deliverable_units(UnitSystem.IMPERIAL, channel)
        for dim in _DIMENSIONS:
            assert getattr(u, dim).factor == 1.0, f"{channel} {dim}"
        assert u.force.label == "lb"
        assert u.length.label == "in"
        assert u.moment.label == "lb-in"


def test_imperial_moment_unit_is_identical_in_both_channels():
    """The channel split is an SI-only concern; Imperial has one unit set."""
    human = deliverable_units(UnitSystem.IMPERIAL, Channel.HUMAN)
    solver = deliverable_units(UnitSystem.IMPERIAL, Channel.SOLVER)
    assert human.moment == solver.moment


# --------------------------------------------------------------------------- #
# The dimensional identity (D-19) — the invariant a solver deck needs
# --------------------------------------------------------------------------- #
def test_solver_set_is_dimensionally_consistent():
    """``moment == force × length`` exactly, in both systems.

    sbeam is only correct in a consistent unit set. With GRID coordinates in mm
    and FORCE in N, a MOMENT card must be N·mm; an N·m moment is wrong by 1000×
    in a file that parses cleanly. The factors are *derived* as force × length in
    ``units.py`` rather than quoted, so this holds by construction — this test is
    what keeps it that way.
    """
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        u = deliverable_units(system, Channel.SOLVER)
        assert u.is_consistent, f"{system}: {u.moment} != {u.force} x {u.length}"
        assert u.moment.factor == u.force.factor * u.length.factor


def test_human_set_is_not_dimensionally_consistent_in_si():
    """The human set pairs N·m with a mm length — deliberately, and it must never
    be used to write a deck. Pinned so the channel split cannot be "tidied" away."""
    u = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    assert not u.is_consistent
    assert u.moment.label == "N·m"


def test_the_two_channels_differ_in_the_derived_dimensions_only():
    """The base dimensions are shared; what a channel chooses is the derived ones.

    Both derived dimensions differ, not just the moment: pressure is force /
    length^2, so the solver's mm length makes its stress unit MPa (N/mm^2) where
    a report reads in kPa. Same D-19 argument, same 1000x, and it was missed
    when this file was first written (M4-20 step 1) -- the moment was the loud
    case, the pressure the quiet one.
    """
    human = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    solver = deliverable_units(UnitSystem.SI, Channel.SOLVER)
    assert human.moment != solver.moment
    assert human.pressure != solver.pressure
    for dim in ("force", "length", "torque"):
        assert getattr(human, dim) == getattr(solver, dim), dim


def test_si_factors_are_the_exact_nist_products():
    solver = deliverable_units(UnitSystem.SI, Channel.SOLVER)
    assert solver.force.factor == 4.4482216152605      # lbf -> N
    assert solver.length.factor == 25.4                # in -> mm
    assert solver.moment.factor == 4.4482216152605 * 25.4   # lb-in -> N·mm
    assert solver.pressure.factor == 4.4482216152605 / 25.4 ** 2  # psi -> MPa
    human = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    # lb-in -> N·m is the same product with the length in metres.
    assert math.isclose(human.moment.factor, 0.11298482902761668, rel_tol=1e-15)


# --------------------------------------------------------------------------- #
# In-band statement (step 1: the string; step 5: every channel carries it)
# --------------------------------------------------------------------------- #
def _ga_project() -> Project:
    return io.load_project(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "ga6_normal.project.json"))


def test_units_statement_names_the_system_and_its_set():
    """All four dimensions, pressure included (M4-20 step 5).

    Pressure joined the statement when step 4 found the solver set had been left
    on the human channel's kPa: it is exactly the dimension a reader cannot infer
    from the numbers, since kPa and MPa differ by the same silent 1000× as N·m and
    N·mm. A statement that named only three would have been true and useless.
    """
    imperial = "Imperial (lb, in, lb-in, lb/in^2)"
    assert units_statement(deliverable_units(UnitSystem.IMPERIAL)) == imperial
    assert units_statement(deliverable_units(UnitSystem.SI, Channel.HUMAN)) == \
        "SI (N, mm, N·m, kPa)"
    assert units_statement(deliverable_units(UnitSystem.SI, Channel.SOLVER)) == \
        "SI (N, mm, N·mm, MPa)"


def test_the_methods_statement_names_the_bundles_system_and_both_channels():
    """The in-band statement is bundle-wide, and says which files use which set.

    One stamp is wrapped for every channel (G8-3) and lands on both the human
    load-case CSVs and the sbeam decks, so it cannot be channel-specific — it
    would be wrong on half the files it appears in. In SI it must therefore name
    *both* sets and attribute each.
    """
    project = _ga_project()
    si = methods_statement(project, system=UnitSystem.SI)
    assert "UNITS: SI." in si
    assert "N·m, kPa" in si and "N·mm, MPa" in si
    assert "sbeam" in si.split("UNITS:")[1].split("\n")[0]

    # Imperial: one set does both jobs, so the statement must not invent a split.
    imperial = methods_statement(project, system=UnitSystem.IMPERIAL)
    assert "UNITS: Imperial (lb, in, lb-in, lb/in^2) throughout." in imperial
    assert "N·mm" not in imperial


def test_the_units_statement_repeats_the_aviation_carve_out():
    """KEAS/ft are unconverted in both systems — the one thing a reader of an SI
    file would otherwise take for a bug, so the statement says it in band."""
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        text = methods_statement(_ga_project(), system=system)
        assert "KEAS" in text and "altitude is ft" in text


def test_the_ult_markers_are_derived_from_the_unit_sets():
    """BASIS lists the markers a bundle can actually contain, per system.

    The list was hard-coded (``lbs-ULT, ft-lb-ULT, N-ULT, Nm-ULT``) and named
    markers no Imperial file carries while omitting every marker step 4 added. It
    is now generated from both channels' sets, so it cannot fall out of step with
    what the writers emit.
    """
    imperial = methods_statement(_ga_project(), system=UnitSystem.IMPERIAL)
    assert "(lbs-ULT, ft-lb-ULT, lb-in-ULT, lb/in^2-ULT)" in imperial

    si = methods_statement(_ga_project(), system=UnitSystem.SI)
    for marker in ("N-ULT", "Nm-ULT", "Nmm-ULT", "kPa-ULT", "MPa-ULT"):
        assert marker in si.split("UNITS:")[0], marker


def test_every_bundle_channel_carries_the_unit_statement():
    """The acceptance criterion: no file leaves without stating its units.

    The BDF decks are the reason this test exists — the Export page built a
    ``bdf_comment_block`` and never applied it, so until step 5 the four decks
    were the one channel in the bundle carrying no statement at all.
    """
    project = _ga_project()
    results = _ga_wing_net()
    kw = dict(system=UnitSystem.SI)
    csv_stamp = csv_comment_block(project, **kw)
    bdf_stamp = bdf_comment_block(project, **kw)

    channels = {
        "load-case CSV": io.load_cases_csv(
            registry.get("engine")(project), header_comment=csv_stamp,
            system=UnitSystem.SI),
        "span CSV": sb.span_load_csv(results, header_comment=csv_stamp,
                                     system=UnitSystem.SI),
        "FORCE/MOMENT deck": sb.force_moment_cards(
            results, header_comment=bdf_stamp, system=UnitSystem.SI),
        "stick model": sb.stick_model_bdf(
            results, header_comment=bdf_stamp, system=UnitSystem.SI),
        "METHODS.txt": methods_statement(project, **kw),
    }
    for name, text in channels.items():
        assert "UNITS: SI." in text, f"{name} states no unit system"
        assert "N·mm, MPa" in text, f"{name} does not name the solver set"


def test_the_deck_stamp_is_comment_only_and_optional():
    """A stamped deck differs from a bare one by ``$`` lines and nothing else.

    ``$`` is inert to every bulk-data parser, and an unstamped call must stay
    byte-identical — that is what keeps the frozen Imperial comparison and every
    existing caller unaffected (D-21).
    """
    results = _ga_wing_net()
    bare = sb.force_moment_cards(results)
    stamped = sb.force_moment_cards(
        results, header_comment=bdf_comment_block(_ga_project()))
    assert stamped != bare
    added = stamped[: len(stamped) - len(bare)]
    assert all(ln.startswith("$") or not ln for ln in added.splitlines())
    assert stamped.endswith(bare)


def test_the_export_page_applies_the_stamp_it_builds():
    """Source guard: every ``.bdf`` artifact gets ``header_comment=_bdf_stamp``.

    The defect this pins was invisible for a whole phase — the page built
    ``_bdf_stamp`` and then never used it, and because it is a module-level name
    ruff's unused-variable rule (a *local* check) never fired. The decks shipped
    unstamped. Reading the page's source is the only way to assert this without a
    Streamlit runtime.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "app", "views", "export_report.py")) as fh:
        source = fh.read()

    assignments = [ln for ln in source.splitlines() if '.bdf"] = ' in ln]
    # wing FORCE/MOMENT + wing stick model + fuselage + tail + control surfaces.
    assert len(assignments) == 5, assignments
    for line in assignments:
        # The call may wrap; take the whole statement up to the closing `or ""`.
        stmt = source.split(line, 1)[1].split('or ""', 1)[0]
        assert "_bdf_stamp" in stmt, line

    # ...and the workbook, which has no comment rows, states units in a cell.
    assert '"Units": units_statement(' in source


def test_the_stamp_still_round_trips_for_csv_readers():
    """``strip_comment_lines`` must survive the extra UNITS line — the G8.3
    readers (``workbook._csv_to_df`` reads with ``comment="#"``) are the audited
    path, and a stamp they cannot skip is a header row of prose."""
    stamp = csv_comment_block(_ga_project(), system=UnitSystem.SI)
    payload = sb.span_load_csv(_ga_wing_net(), system=UnitSystem.SI)
    assert strip_comment_lines(stamp + payload) == payload


# --------------------------------------------------------------------------- #
# Step 6 — the Export page resolves the system once and states it
# --------------------------------------------------------------------------- #
def _view_source(name: str) -> str:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "app", "views", f"{name}.py")) as fh:
        return fh.read()


def test_the_export_page_resolves_the_system_exactly_once():
    """One `active_system()` read, and every artifact call takes that local.

    "One bundle, one system" is only structural if there is a single value to
    disagree with. A second `active_system()` call would be harmless *today* and
    a latent split the moment anything sits between them, so the count is pinned
    rather than the behaviour.
    """
    source = _view_source("export_report")
    calls = [ln for ln in source.splitlines()
             if "active_system()" in ln and not ln.lstrip().startswith("#")]
    assert calls == ["_system = active_system()"], calls


def test_every_export_page_writer_call_takes_the_bundle_system():
    """No artifact on the Export page may fall back to a writer's Imperial default.

    A defaulted call is invisible: it produces a perfectly valid file, in the
    wrong system, beside files in the right one — the exact failure "one bundle,
    one system" exists to prevent. Every unit-taking writer call is checked here
    because the page is a script, not an importable function.
    """
    import re

    source = _view_source("export_report")
    # The unit-taking writers, by name; case_index_* is deliberately absent —
    # it carries only Speed (kt) and Altitude (ft), both aviation carve-outs.
    writers = ("span_load_csv", "force_moment_cards", "stick_model_bdf",
               "body_span_load_csv", "body_fitting_load_csv", "tail_chordwise_csv",
               "control_surface_csv", "load_cases_csv")
    # Calls wrap across lines, so match each writer reference and read the argument
    # list that follows it, rather than slicing statements out of the source.
    checked = 0
    for match in re.finditer(r"\b(?:sb|sloads_io)\.(\w+)", source):
        name = match.group(1)
        # Suffix match: the body/tail/control card writers are
        # ``body_force_moment_cards`` etc., the same writer per component.
        if not any(name.endswith(w) for w in writers):
            continue
        window = source[match.end(): match.end() + 220]
        assert "system=_system" in window, f"{name} call defaults to Imperial:\n{window}"
        checked += 1
    # 5 decks + 5 sbeam CSVs + the per-module load-case CSV.
    assert checked == 11, f"{checked} writer calls found, expected 11"


def test_the_case_index_needs_no_system():
    """Its only dimensional columns are the two that are never converted.

    Worth pinning: the case index is the one export that legitimately takes no
    `system=`, and "this writer was forgotten" and "this writer needs nothing"
    look identical at a call site.
    """
    dimensional = [k for k in sb._CASE_INDEX_FIELDS if "(" in k]
    assert dimensional == ["Speed (kt)", "Altitude (ft)"], dimensional


def _export_page_captions(system: UnitSystem):
    """Render the Export page headlessly in ``system`` and return its captions."""
    import logging

    import pytest

    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in (root, os.path.join(root, "app")):
        if path not in sys.path:
            sys.path.insert(0, path)

    project = _ga_project()
    # The selection lives on the project (D-22) and active_system() reads it
    # there; the session key is only the no-project-yet fallback.
    project.unit_system = system.value
    at = AppTest.from_file(
        os.path.join(root, "app", "views", "export_report.py"), default_timeout=180)
    at.session_state["project"] = project
    at.session_state["unit_system"] = system
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return [c.value for c in at.caption]


def test_the_export_page_states_the_system_it_will_write():
    """The plan's acceptance: the on-page caption matches what the files contain.

    AppTest cannot read a download button's payload (Streamlit serves it by URL),
    so the caption is compared against the *unit sets themselves* — the same
    `deliverable_units` the writers resolve. That is the property that matters:
    caption and files have one source, so they cannot drift.
    """
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        caption = next(c for c in _export_page_captions(system) if "written in" in c)
        for channel in (Channel.HUMAN, Channel.SOLVER):
            u = deliverable_units(system, channel)
            for dim in (u.force, u.length, u.moment, u.pressure):
                assert dim.label in caption, (system, channel, dim.label, caption)
        assert "KEAS" in caption and "ULTIMATE" in caption

    si = next(c for c in _export_page_captions(UnitSystem.SI) if "written in" in c)
    assert "**SI**" in si and "N·mm" in si
    imperial = next(
        c for c in _export_page_captions(UnitSystem.IMPERIAL) if "written in" in c)
    # Imperial's two channels are the same set, so the caption must not split.
    assert "**Imperial**" in imperial and "sbeam decks" not in imperial


# --------------------------------------------------------------------------- #
# The mappings this step adds — both were reachable, unconverted, in SI
# --------------------------------------------------------------------------- #
def _one(units: str, value: float = 1.0, quantity: str = "") -> LoadValue:
    return ConditionResult(
        title="t", far_reference="23.000",
        values=[LoadValue(label="x", value=value, units=units, quantity=quantity)],
    )


def test_lb_in_moments_now_convert_to_si():
    """``lb-in`` had no SI mapping: 1240 values across the six examples stayed
    Imperial inside an otherwise-converted table (root bending/torsion, pitching
    moment). Fixed by M4-20 step 1."""
    out = convert_results([_one("lb-in", 100.0)], UnitSystem.SI)[0].values[0]
    assert out.units == "N·m"
    assert math.isclose(out.value, 11.298482902761668, rel_tol=1e-12)


def test_design_pressure_now_converts_to_si():
    """``lb/in^2`` had no SI mapping: 340 values stayed Imperial. Fixed here."""
    out = convert_results([_one("lb/in^2", 10.0)], UnitSystem.SI)[0].values[0]
    assert out.units == "kPa"
    assert math.isclose(out.value, 68.94757, rel_tol=1e-12)


def test_converted_si_loads_still_take_an_ultimate_marker():
    """A newly-convertible unit must also be recognised as a *load* by the
    ultimate boundary, or it would convert and then silently lose its ``-ULT``
    marker — a limit load presented as a deliverable."""
    assert ultimate_units("N·m") == "Nm-ULT"
    assert ultimate_units("N·mm") == "Nmm-ULT"
    assert ultimate_units("kPa") == "kPa-ULT"


# --------------------------------------------------------------------------- #
# The aviation carve-out
# --------------------------------------------------------------------------- #
def test_airspeed_and_altitude_are_never_converted():
    """KEAS and ft are aviation-standard in *both* systems.

    The calc emits ``kt(EAS)`` and ``ft``. A ``"knot"`` row lived in the SI table
    until M4-20 and matched nothing (no producer has ever emitted that string),
    but it would have broken the carve-out the day one did; it is gone.
    """
    for unit in ("kt(EAS)", "ft"):
        out = convert_results([_one(unit, 120.0)], UnitSystem.SI)[0].values[0]
        assert out.units == unit
        assert out.value == 120.0
    assert "knot" not in _RESULT_TO_SI


# --------------------------------------------------------------------------- #
# Standing guard — catches the *next* missing mapping
# --------------------------------------------------------------------------- #
def test_every_imperial_load_unit_has_an_si_mapping():
    """A load unit the renderer knows but ``units.py`` cannot convert produces a
    mixed-unit table in SI: everything around it converts and it does not, with
    no error anywhere. That is exactly how ``lb-in`` and ``lb/in^2`` went
    unnoticed. This fails when the next one is added without its factor.
    """
    # An SI unit is any label an SI unit set can produce -- from the per-value
    # conversion table *or* from either channel's deliverable set (N·mm is only
    # ever minted by the solver set, so the table alone under-counts).
    si_units = {label for _, label in _RESULT_TO_SI.values()}
    for channel in (Channel.HUMAN, Channel.SOLVER):
        u = deliverable_units(UnitSystem.SI, channel)
        si_units |= {getattr(u, d).label for d in _DIMENSIONS}

    for unit in _LOAD_UNITS:
        if unit in si_units:
            continue  # already an SI unit (N, N·m, N·mm, kPa)
        assert unit in _RESULT_TO_SI, f"load unit {unit!r} has no SI conversion"


def test_every_load_unit_has_an_ultimate_marker():
    """Same guard for the ``-ULT`` side: a load unit with no marker would be
    exported as a bare limit-looking number."""
    for unit in _LOAD_UNITS:
        assert unit in _ULT_UNITS, f"load unit {unit!r} has no -ULT marker"


# --------------------------------------------------------------------------- #
# Selection plumbing (M4-20 step 2): Project.unit_system, schema 38, the CLI flag
# --------------------------------------------------------------------------- #
def test_unit_system_defaults_to_imperial_and_parses_leniently():
    """An unreadable preference degrades to the documented default. A project file
    is not a place to raise: a junk value must never block the load of an
    otherwise-valid project."""
    assert Project(name="x").unit_system == "imperial"
    assert unit_system_from("si") is UnitSystem.SI
    assert unit_system_from("SI") is UnitSystem.SI
    assert unit_system_from("  Imperial ") is UnitSystem.IMPERIAL
    assert unit_system_from(UnitSystem.SI) is UnitSystem.SI
    for junk in (None, "", "metric", "furlongs", 7, []):
        assert unit_system_from(junk) is UnitSystem.IMPERIAL, junk


def test_unit_system_round_trips_and_stays_out_of_a_default_file():
    """Written only when non-default, on the document-control precedent: a project
    that never chose a system round-trips byte-identically to a pre-v38 file."""
    p = Project(name="x")
    assert "unit_system" not in io.project_to_dict(p)

    p.unit_system = "si"
    d = io.project_to_dict(p)
    assert d["unit_system"] == "si"
    assert io.project_from_dict(d).unit_system == "si"


def test_a_pre_v38_file_reads_as_imperial():
    """Absent *is* the value — which is why this needed no migration hop."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "fixtures_schema", "v37_no_unit_system.json")) as fh:
        old = json.load(fh)
    assert "unit_system" not in old
    assert io.project_from_dict(old).unit_system == "imperial"


def test_v38_adds_no_key_to_the_shipped_examples():
    """None of the six examples chose a system, so none gains a ``unit_system``
    key and each still round-trips to a stable dict.

    (The round-trip is asserted as *idempotence*, not equality with the file on
    disk: ``io.py`` has always normalised some values on read — tuples for
    coordinate pairs, defaults filled in — which predates this item and is not
    what this test is about.)
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sorted(glob.glob(os.path.join(here, "examples", "*.project.json")))
    assert len(paths) == 6, paths
    for path in paths:
        with open(path) as fh:
            on_disk = json.load(fh)
        first = io.project_to_dict(io.project_from_dict(on_disk))
        second = io.project_to_dict(io.project_from_dict(first))
        assert "unit_system" not in first, os.path.basename(path)
        assert first == second, path


def test_cli_units_resolution_order():
    """Flag beats the project's preference, which beats Imperial."""
    imperial, si = Project(name="i"), Project(name="s", unit_system="si")
    assert cli.resolve_units(imperial) is UnitSystem.IMPERIAL
    assert cli.resolve_units(si) is UnitSystem.SI
    # the flag overrides the project, in both directions
    assert cli.resolve_units(imperial, "si") is UnitSystem.SI
    assert cli.resolve_units(si, "imperial") is UnitSystem.IMPERIAL
    # no flag, no preference -> today's behaviour, unchanged
    assert cli.resolve_units(Project(name="x"), None) is UnitSystem.IMPERIAL


# --------------------------------------------------------------------------- #
# Step 3 -- the human channel: io.load_cases_csv takes the unit system
# --------------------------------------------------------------------------- #
def _every_module_csv(system):
    """{(example, module): csv} for every example x every module that runs."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = {}
    for path in sorted(glob.glob(os.path.join(here, "examples", "*.project.json"))):
        project = io.load_project(path)
        for mr in run_all_modules(project):
            out[(os.path.basename(path), mr.module)] = io.load_cases_csv(
                mr, system=system)
    assert out, "no module CSVs produced -- the sweep is not exercising anything"
    return out


def test_imperial_csv_is_byte_identical_to_the_no_system_call():
    """Imperial is the identity: the new parameter cannot move today's output.

    ``system=IMPERIAL`` must reach ``convert_results``' early return, not a
    round trip through a factor table. Swept over every example x module rather
    than one sample, because the writer picks between two row builders
    (``load_cases_to_rows`` / ``results_to_rows``) and both paths matter.
    """
    for key, csv_si_off in _every_module_csv(UnitSystem.IMPERIAL).items():
        example, module = key
        project = io.load_project(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "examples", example))
        default = io.load_cases_csv(
            next(mr for mr in run_all_modules(project) if mr.module == module))
        assert csv_si_off == default, key


def test_si_csv_converts_loads_and_leaves_speed_and_altitude_alone():
    """SI headers carry the SI unit; the aviation carve-out survives the writer.

    The header text is produced by ``report/render.py``'s ``_detect_unit`` from
    each ``LoadValue.units`` string -- so this is also the assertion that the
    renderer needed no unit-system knowledge to do the right thing.
    """
    imperial = _every_module_csv(UnitSystem.IMPERIAL)
    si = _every_module_csv(UnitSystem.SI)
    assert set(imperial) == set(si)

    converted = 0
    for key in imperial:
        imp_head = imperial[key].splitlines()[0] if imperial[key] else ""
        si_head = si[key].splitlines()[0] if si[key] else ""
        # Speed and altitude columns are byte-identical in both systems.
        for carved in ("(kt)", "(ft)", "(kt(EAS))"):
            assert imp_head.count(carved) == si_head.count(carved), (key, carved)
        # ...while no load column keeps its Imperial marker.
        for imperial_marker in ("lbs-ULT", "lb-in-ULT", "ft-lb-ULT", "psi-ULT"):
            assert imperial_marker not in si_head, (key, imperial_marker)
        if "lbs-ULT" in imp_head:
            assert "N-ULT" in si_head, key
            converted += 1
    assert converted, "no module produced a force column -- sweep is degenerate"


def test_si_csv_values_are_the_imperial_values_times_the_factor():
    """Spot-check the numbers, not only the headers (engine, a load-case table)."""
    import csv as _csv

    project = io.load_project(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "ga6_normal.project.json"))
    result = registry.get("engine")(project)
    imp = list(_csv.DictReader(io.load_cases_csv(result).splitlines()))
    si = list(_csv.DictReader(
        io.load_cases_csv(result, system=UnitSystem.SI).splitlines()))
    assert len(imp) == len(si) and imp

    force_imp = next(c for c in imp[0] if "lbs-ULT" in c)
    force_si = next(c for c in si[0] if "N-ULT" in c)
    checked = 0
    for a, b in zip(imp, si):
        if not a[force_imp] or not b[force_si]:
            continue
        assert math.isclose(float(b[force_si]),
                            float(a[force_imp]) * 4.4482216152605,
                            rel_tol=1e-3), (a[force_imp], b[force_si])
        checked += 1
    assert checked, "no force values compared"


def test_load_cases_csv_is_the_only_converter_in_the_human_channel():
    """One conversion point, so a caller cannot convert twice by accident.

    The writer converts internally; a caller that pre-converts *and* passes
    ``system=SI`` would double-convert. Today that is silently a no-op (``N``
    has no SI mapping), which is exactly why it needs a guard rather than
    trust: if ``io.py`` ever grows a second ``convert_results`` call, the human
    channel has two conversion points and the invariant is gone.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "sloads", "io.py")) as fh:
        source = fh.read()
    calls = [ln for ln in source.splitlines()
             if "convert_results(" in ln and not ln.lstrip().startswith(("#", "*"))
             and "from .units import" not in ln]
    assert len(calls) == 1, calls
    assert "_as_conditions" in calls[0], calls


def test_write_load_cases_csv_passes_the_system_through():
    """The file writer is a thin wrapper -- it must not drop the parameter.

    Uses ``tempfile`` rather than pytest's ``tmp_path`` fixture: every test in
    this file must also run under the zero-dependency self-runner at the bottom,
    which calls each test with no arguments and cannot supply a fixture.
    """
    import tempfile

    project = io.load_project(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "ga6_normal.project.json"))
    result = registry.get("engine")(project)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "out.csv")
        io.write_load_cases_csv(result, path, system=UnitSystem.SI)
        # newline="" -- the writer emits csv's \r\n and universal-newline reads
        # would translate them, turning a pass-through check into a line-ending
        # check.
        with open(path, newline="") as fh:
            written = fh.read()
    assert written == io.load_cases_csv(result, system=UnitSystem.SI)
    assert "N-ULT" in written.splitlines()[0]


# --------------------------------------------------------------------------- #
# Step 4 -- the solver channel: the sbeam deck on the N/mm/N*mm set
# --------------------------------------------------------------------------- #
def _ga_wing_net():
    from sloads.modules.net_loads import build_net_loads

    project = io.load_project(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "ga6_normal.project.json"))
    return build_net_loads(project).wing_net


def _card_sums(bdf: str):
    """[(stated_sz, stated_myy, summed_fz, summed_my)] per case block."""
    import re

    out, stated, fz, my = [], None, 0.0, 0.0
    for line in bdf.splitlines():
        if line.startswith("$ SLOADS"):
            if stated is not None:
                out.append((stated[0], stated[1], fz, my))
            stated, fz, my = None, 0.0, 0.0
        elif line.startswith("$ FORCE set sums"):
            nums = re.findall(r"=\s*(-?[\d.]+)", line)
            stated = (float(nums[0]), float(nums[1]))
        elif line.startswith("FORCE,"):
            fz += float(line.split(",")[7])
        elif line.startswith("MOMENT,"):
            my += float(line.split(",")[6])
    if stated is not None:
        out.append((stated[0], stated[1], fz, my))
    return out


def test_si_deck_still_closes_on_the_root_shear_and_torsion():
    """The physics test, not a factor test (plan step 4 acceptance).

    A scale bug that multiplied the cards but not the stated total -- or the
    moment by the force factor -- would leave every number plausible and the
    closure broken. Checking the *set sums to the root* in the new units is what
    actually catches it.
    """
    results = _ga_wing_net()
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        blocks = _card_sums(sb.force_moment_cards(results, system=system))
        assert len(blocks) == len(results), system
        for stated_sz, stated_myy, fz, my in blocks:
            assert math.isclose(fz, stated_sz, rel_tol=1e-5), (system, fz, stated_sz)
            assert math.isclose(my, stated_myy, rel_tol=1e-5), (system, my, stated_myy)


def test_si_deck_is_the_imperial_deck_times_the_solver_factors():
    """Same cards, same GIDs, same SIDs -- only the magnitudes move, each by its
    own dimension's factor. In particular the moment moves by force x length
    (N*mm), not by the human channel's N*m: that difference is D-19's 1000x."""
    results = _ga_wing_net()
    u = deliverable_units(UnitSystem.SI, Channel.SOLVER)
    imp = [ln for ln in sb.force_moment_cards(results).splitlines()
           if ln.startswith(("FORCE,", "MOMENT,"))]
    si = [ln for ln in sb.force_moment_cards(results, system=UnitSystem.SI).splitlines()
          if ln.startswith(("FORCE,", "MOMENT,"))]
    assert len(imp) == len(si) and imp

    checked_force = checked_moment = 0
    for a, b in zip(imp, si):
        pa, pb = a.split(","), b.split(",")
        assert pa[:5] == pb[:5], (a, b)   # card type, SID, GID, CID, scale
        factor = u.force.factor if pa[0] == "FORCE" else u.moment.factor
        for va, vb in zip(pa[5:], pb[5:]):
            if abs(float(va)) < 1e-9:
                assert abs(float(vb)) < 1e-9, (a, b)
                continue
            assert math.isclose(float(vb), float(va) * factor, rel_tol=1e-6), (a, b)
            if pa[0] == "FORCE":
                checked_force += 1
            else:
                checked_moment += 1
    assert checked_force and checked_moment


def test_the_solver_deck_never_uses_the_human_moment():
    """The 1000x guard, at the level of the numbers in the file.

    An N*m moment in a millimetre deck is the failure D-19 exists to prevent, so
    assert the deck's moments are *not* what the human channel would have
    written -- a stronger statement than 'the factor is the one we chose'.
    """
    results = _ga_wing_net()
    human = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    si = [ln for ln in sb.force_moment_cards(results, system=UnitSystem.SI).splitlines()
          if ln.startswith("MOMENT,")]
    imp = [ln for ln in sb.force_moment_cards(results).splitlines()
           if ln.startswith("MOMENT,")]
    compared = 0
    for a, b in zip(imp, si):
        va, vb = float(a.split(",")[6]), float(b.split(",")[6])
        if abs(va) < 1e-9:
            continue
        assert not math.isclose(vb, va * human.moment.factor, rel_tol=1e-3), a
        compared += 1
    assert compared


def test_coordinates_refuse_an_inconsistent_unit_set():
    """The human set is a plausible thing to pass, so the scale point rejects it.

    ``deliverable_units(SI)`` defaults to HUMAN -- the set every *report* uses --
    and a caller who forgets ``Channel.SOLVER`` gets an error, not a deck with
    N*m moments and kPa pressures against millimetre GRIDs.
    """
    from sloads.export import coordinates as coords

    human = deliverable_units(UnitSystem.SI, Channel.HUMAN)
    assert not human.is_consistent
    for call in (lambda: coords.to_grid(1.0, 0.0, 0.0, human),
                 lambda: coords.to_force(1.0, 0.0, 0.0, human),
                 lambda: coords.to_moment(0.0, 1.0, 0.0, human),
                 lambda: coords.to_pressure(1.0, human)):
        try:
            call()
        except ValueError as exc:
            assert "not dimensionally consistent" in str(exc)
        else:
            raise AssertionError("an inconsistent unit set was accepted")


def test_every_sbeam_writer_takes_a_system():
    """A writer without the parameter would silently emit an Imperial file into
    an SI bundle -- the 'one system per bundle' guarantee is only as good as its
    least-updated writer, so enumerate them rather than trust the sweep."""
    import inspect

    writers = [
        sb.span_load_csv, sb.write_span_load_csv,
        sb.force_moment_cards, sb.write_force_moment_cards,
        sb.stick_model_bdf, sb.write_stick_model_bdf,
        sb.body_span_load_csv, sb.body_force_moment_cards, sb.body_fitting_load_csv,
        sb.tail_chordwise_csv, sb.write_tail_chordwise_csv,
        sb.tail_force_moment_cards, sb.write_tail_force_moment_cards,
        sb.control_surface_csv, sb.write_control_surface_csv,
        sb.control_surface_force_moment_cards,
        sb.write_control_surface_force_moment_cards,
    ]
    for fn in writers:
        param = inspect.signature(fn).parameters.get("system")
        assert param is not None, fn.__name__
        assert param.kind is inspect.Parameter.KEYWORD_ONLY, fn.__name__
        assert param.default is UnitSystem.IMPERIAL, fn.__name__


def test_sbeam_headers_state_their_units_in_both_systems():
    """Every dimensional column carries its unit; no column is left bare (D-21)."""
    results = _ga_wing_net()
    for system, length, force, moment in (
        (UnitSystem.IMPERIAL, "(in)", "(lbs-ULT)", "(lb-in-ULT)"),
        (UnitSystem.SI, "(mm)", "(N-ULT)", "(Nmm-ULT)"),
    ):
        header = sb.span_load_csv(results, system=system).splitlines()[0]
        cells = header.split(",")
        assert cells[2] == f"X {length}", header
        assert cells[5] == f"Fx {force}", header
        assert cells[7] == f"My {moment}", header
        # Only the non-dimensional columns are bare.
        bare = [c for c in cells if "(" not in c]
        assert bare == ["Case", "GID", "MyyAxis", "SF"], bare


# --------------------------------------------------------------------------- #
# Step 7 — the closing guarantees: Imperial is unchanged, a bundle is one
# system, the round trip is lossless, and the calc is not in this path
# --------------------------------------------------------------------------- #
def test_imperial_output_matches_the_frozen_baseline():
    """**Decision D-21's guarantee**: no Imperial byte moved across M4-20.

    Six examples × every channel (load-case CSVs, text reports, all five sbeam
    CSVs, all five decks, the case index), digested and frozen in
    ``fixtures_imperial/digests.json``. This is the test the whole item rests on:
    everything else asserts that SI is *right*, and only this asserts that adding
    SI cost the Imperial user nothing.

    Regenerate with ``.venv/bin/python tests/imperial_baseline.py`` — and only
    when the change to Imperial output is intended and recorded.
    """
    import imperial_baseline as baseline

    frozen = baseline.load_fixture()
    for example in baseline.EXAMPLES:
        current = {
            channel: __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()
            for channel, text in baseline.artifacts(example).items()
        }
        expected = frozen[example]
        assert set(current) == set(expected), (
            example, sorted(set(current) ^ set(expected)))
        drifted = [c for c in sorted(current) if current[c] != expected[c]]
        assert not drifted, f"{example}: Imperial output changed in {drifted}"


def test_the_frozen_baseline_is_not_vacuous():
    """A guard over an empty set passes forever — pin the coverage too.

    ``imperial_baseline`` swallows the exception when an example lacks a slice, so
    a regression that made every channel raise would shrink the fixture to nothing
    and the guard above would still be green.
    """
    import imperial_baseline as baseline

    frozen = baseline.load_fixture()
    assert set(frozen) == set(baseline.EXAMPLES)
    assert sum(len(v) for v in frozen.values()) > 200, "baseline lost channels"
    for example, channels in frozen.items():
        assert any(c.startswith("csv/") for c in channels), example

    # Which examples reach the *solver* channel is pinned exactly, not merely
    # "most of them" — an example silently dropping out of the sbeam set is
    # exactly what a lenient assertion would hide. Every example now reaches it:
    # concept_heavy was the sole exception until step B1, because it carries no
    # `fuselage_mass.stations` and the body module read nothing else. The beam is
    # now derived from `weight.items` (the mass SSOT), so a project needs no
    # hand-entered station table to have fuselage loads at all.
    with_sbeam = {e for e, ch in frozen.items() if any(c.startswith("sbeam/") for c in ch)}
    assert with_sbeam == set(baseline.EXAMPLES), with_sbeam


def test_a_bundle_states_exactly_one_system():
    """Every file in one bundle names the same system — the D-19 bundle invariant.

    Two files in one hand-off disagreeing about units is the failure mode the
    whole two-channel design is built to make impossible; a *channel* difference
    (N·m vs N·mm) is legitimate, a *system* difference is not.
    """
    import imperial_baseline as baseline

    project = _ga_project()
    for system, expected, forbidden in (
        (UnitSystem.IMPERIAL, "UNITS: Imperial", "UNITS: SI"),
        (UnitSystem.SI, "UNITS: SI.", "UNITS: Imperial"),
    ):
        stamps = {
            "csv": csv_comment_block(project, system=system),
            "bdf": bdf_comment_block(project, system=system),
            "methods": methods_statement(project, system=system),
        }
        # Every channel of a real bundle, each carrying its channel's stamp.
        bundle = dict(baseline.artifacts("ga6_normal.project.json"))
        bundle = {
            name: (stamps["bdf"] if name.endswith(("cards", "stick"))
                   else stamps["csv"]) + text
            for name, text in bundle.items()
        }
        bundle["METHODS.txt"] = stamps["methods"]
        for name, text in bundle.items():
            assert expected in text, f"{name} does not state {expected}"
            assert forbidden not in text, f"{name} also claims {forbidden}"


def test_the_round_trip_is_lossless_per_dimension():
    """Imperial → SI → Imperial returns the original, dimension by dimension.

    The factors are exact NIST products, so this is exact rather than merely
    within display precision — a factor quoted to too few places (the way
    ``0.1129`` would be) fails here long before it shows up in a load.
    """
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        for channel in (Channel.HUMAN, Channel.SOLVER):
            u = deliverable_units(system, channel)
            for dim in (u.force, u.length, u.moment, u.torque, u.pressure):
                for value in (1.0, 1234.5678, 1e-6, 9.87e5):
                    assert math.isclose(value * dim.factor / dim.factor, value,
                                        rel_tol=1e-15), (dim.label, value)

    # ...and through the LoadValue path a deliverable actually uses.
    for units, si_units in (("lb", "N"), ("lb-in", "N·m"), ("lb/in^2", "kPa")):
        original = 1234.5678
        si = convert_results([_one(units, original)], UnitSystem.SI)[0].values[0]
        assert si.units == si_units
        factor, _ = _RESULT_TO_SI[units]
        assert math.isclose(si.value / factor, original, rel_tol=1e-12)


def test_no_calc_module_converts_units():
    """The calc is not in the conversion path, so the oracles cannot be touched.

    Appendix A is asserted numerically in the per-module tests; what M4-20 has to
    prove is that it never *reaches* those assertions differently. Conversion
    living entirely at the render/export boundary is that proof, and it is a
    structural property worth pinning rather than re-deriving from a passing suite.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    modules_dir = os.path.join(here, "sloads", "modules")
    offenders = []
    for name in sorted(os.listdir(modules_dir)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(modules_dir, name)) as fh:
            source = fh.read()
        for banned in ("convert_results", "deliverable_units", "to_si_scalar"):
            if banned + "(" in source:
                offenders.append(f"{name}: {banned}")
    assert not offenders, offenders


# --------------------------------------------------------------------------- #
# Step 7 — the CLI, end to end
# --------------------------------------------------------------------------- #
def _cli_csv(*argv) -> str:
    """Run the CLI with ``-o`` into a temp file and return what it wrote."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.csv")
        assert cli.main([*argv, "-o", out]) == 0
        # newline="" -- the writer emits csv's \r\n; a universal-newline read
        # would translate them and mask a line-ending regression.
        with open(out, newline="") as fh:
            return fh.read()


def test_cli_writes_the_requested_system():
    """``--units si`` changes the file; the default is byte-identical to no flag."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    example = os.path.join(here, "examples", "ga6_normal.project.json")

    plain = _cli_csv("engine", example)
    imperial = _cli_csv("engine", example, "--units", "imperial")
    si = _cli_csv("engine", example, "--units", "si")

    assert plain == imperial, "the default run must not depend on the flag existing"
    assert si != plain
    assert "lbs-ULT" in plain.splitlines()[0] and "N-ULT" in si.splitlines()[0]
    # The aviation carve-out survives the CLI boundary too.
    for carved in ("(kt(EAS))", "(ft)"):
        assert plain.splitlines()[0].count(carved) == si.splitlines()[0].count(carved)


def test_cli_exports_an_si_sbeam_deck():
    """``--units si --export-sbeam`` writes the solver set, not the human one.

    Step 2 made this combination refuse outright (the deck had no SI unit set yet)
    and step 4 lifted the refusal; this is the end-to-end proof that the lift is
    real and reaches the files rather than only the writer signatures.
    """
    import tempfile

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    example = os.path.join(here, "examples", "ga6_normal.project.json")
    with tempfile.TemporaryDirectory() as d:
        prefix = os.path.join(d, "wing")
        assert cli.main([example, "--export-sbeam", prefix, "--units", "si"]) == 0
        written = sorted(os.listdir(d))
        assert written, "export wrote nothing"
        deck = next(f for f in written if f.endswith(".bdf"))
        with open(os.path.join(d, deck)) as fh:
            text = fh.read()
        assert "lengths in mm" in text
        assert "N·mm" in text and "N·m." not in text, "deck must not use the human moment"

        span = next(f for f in written if f.endswith(".csv"))
        with open(os.path.join(d, span)) as fh:
            header = fh.readline()
        assert "X (mm)" in header and "Nmm-ULT" in header, header


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    mod = sys.modules[__name__]
    failed = 0
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        try:
            getattr(mod, name)()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print("OK" if not failed else f"{failed} failure(s)")
    sys.exit(1 if failed else 0)
