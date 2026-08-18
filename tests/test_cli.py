"""The headless deliverable — 0.5.0 row 1 (review F-D1 / F-C2 / F-D3, m2, L-8g).

The mission is a **scripted** concept-loads → sbeam sizing loop, so "the GUI can
write it" is not the same as "the deliverable exists". Three gaps closed here,
each with its own gate:

* **F-D1 — reachability.** ``--export-target`` is the whole deliverable menu:
  wing, body, tail, the two spanwise empennage surfaces, control surfaces, the
  assembled **balanced free-free deck** (the mission's primary artifact, which
  was writable only from a Streamlit page) and the CONM2 **mass model**.
  :func:`test_the_export_menu_is_the_deliverable_menu` pins the menu against
  ``cli.EXPORT_TARGETS`` and against argparse, so a target cannot be implemented
  without being offered or offered without being implemented.
* **F-C2 / decision D-R5 — the wing axis.** The CLI passed a bare result list to
  the writers, so the boundary transfer to the surface's loads reference axis
  never ran and the headless deck's torsion, station X and lever arms were about
  the 25 % chord while the GUI's were about the LRA. The two front-ends are now
  the same deck, and the axis is pinned on a project whose LRA is *not* the
  quarter chord — on a shipped fixture (``ref_axis_pct`` 0.25 everywhere) the
  transfer is a no-op and would pin nothing.
* **F-D3 / L-8g — the stamp.** Every headless CSV and BDF carries the Step G8.3
  methods & limitations block, so a file forwarded on its own still states its
  ULTIMATE basis, its category and its approved corrections.

Plus **m2**, the error contract: one contract for every route — ``error: …`` on
stderr and status 1, never a traceback, and never a swallowed invalid input.

Conventions: ``docs/10_standard/CONVENTIONS.md``. Error-handling contract:
``docs/10_standard/00_program_overview.md``.
"""

from __future__ import annotations

import csv
import io as _io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import cli  # noqa: E402
from sloads import io as sloads_io  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.models import Project  # noqa: E402
from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results  # noqa: E402
from sloads.report.methods import strip_comment_lines  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")
# The LRA beam model refuses ga6 (no fuselage data, BM-1/BM-3) -- its headless
# route is exercised on a fixture that carries a body.
ATR42 = os.path.join(_ROOT, "examples", "atr42_100.project.json")


def _run(tmp_path, *argv) -> list:
    """Run the CLI into ``tmp_path`` and return the files it wrote, sorted."""
    assert cli.main(list(argv)) == 0, argv
    return sorted(os.listdir(tmp_path))


def _export(tmp_path, target: str, *extra) -> list:
    prefix = os.path.join(str(tmp_path), "out")
    # ga6 has no fuselage data, so the LRA beam model refuses it by design
    # (BM-1/BM-3); that target's stamped file comes from a body-carrying
    # fixture instead.
    fixture = ATR42 if target == "lra" else GA6
    return _run(tmp_path, fixture, "--export-sbeam", prefix,
                "--export-target", target, *extra)


# --------------------------------------------------------------------------- #
# F-D1 — the deliverable set is reachable headless
# --------------------------------------------------------------------------- #
def test_the_export_menu_is_the_deliverable_menu():
    """``EXPORT_TARGETS`` is what argparse offers -- no target only half-wired.

    F-D1 was exactly this drift: the balanced deck and the body deck existed and
    the menu did not know about them.
    """
    # argparse is handed the tuple itself, so an unlisted target is rejected
    # before any work happens.
    with pytest.raises(SystemExit):
        cli.main([GA6, "--export-sbeam", "x", "--export-target", "not-a-target"])
    # Every advertised target is documented in the module docstring's table, so
    # the ``--help`` menu and the prose cannot diverge either.
    for target in cli.EXPORT_TARGETS:
        assert f"``{target}``" in cli.__doc__, f"{target} is undocumented"
    # ...and every documented target is advertised (the reverse direction: a
    # target dropped from the tuple but left in the prose is the same drift).
    documented = {t for t in cli.EXPORT_TARGETS if f"``{t}``" in cli.__doc__}
    assert documented == set(cli.EXPORT_TARGETS)


@pytest.mark.parametrize("target,expected", [
    ("wing", ["out.loads.bdf", "out.span_loads.csv"]),
    ("body", ["out.body_fitting_loads.csv", "out.body_loads.bdf",
              "out.body_span_loads.csv"]),
    ("tail", ["out.tail_chordwise.csv", "out.tail_loads.bdf"]),
    ("htail-span", ["out.htail_span.csv", "out.htail_span_loads.bdf"]),
    ("vtail-span", ["out.vtail_span.csv", "out.vtail_span_loads.bdf"]),
    ("control", ["out.control_surface.bdf", "out.control_surface.csv"]),
    ("balanced", ["out.balanced_airframe.bdf"]),
    ("mass", ["out_inertia_only.bdf", "out_mass.bdf", "out_mass_check.bdf"]),
])
def test_every_export_target_writes_its_artifacts(tmp_path, target, expected):
    """Each target writes its files, non-empty, on the Appendix A airplane."""
    written = _export(tmp_path, target)
    assert written == expected, f"{target} wrote {written}"
    for name in written:
        assert os.path.getsize(os.path.join(str(tmp_path), name)) > 0


def test_the_balanced_deck_is_reachable_headless(tmp_path):
    """The mission's primary deliverable, from the CLI, byte-for-byte the page's.

    F-D1's headline: ``balanced_airframe.bdf`` was downloadable only from the
    Balanced Cases page, so the sizing loop could not script the one artifact it
    is about.
    """
    from sloads.export.balanced_deck import balanced_deck

    _export(tmp_path, "balanced")
    with open(os.path.join(str(tmp_path), "out.balanced_airframe.bdf")) as fh:
        written = fh.read()

    # The stamp rides on top; below it the deck is the page's, to the byte. (A
    # deck's own ``$`` lines are part of the deliverable, so "ends with the
    # unstamped build" is the honest form of this assertion -- see
    # ``report.methods.strip_comment_lines``.)
    project = sloads_io.load_project(GA6)
    assert written.endswith(balanced_deck(project))
    assert written.startswith("$ METHODS AND LIMITATIONS")


def test_the_mass_target_and_export_conm2_are_one_owner(tmp_path):
    """``--export-target mass`` and ``--export-conm2`` write identical files.

    Two spellings, one implementation: the second exists only because it shipped
    first. If they ever diverge, one of the two is a stale copy of the mass
    model -- which is the class of defect the CONM2 export exists to catch.
    """
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    assert cli.main([GA6, "--export-sbeam", str(a / "m"),
                     "--export-target", "mass"]) == 0
    assert cli.main([GA6, "--export-conm2", str(b / "m")]) == 0
    names = sorted(os.listdir(str(a)))
    assert names == sorted(os.listdir(str(b))) and names
    for name in names:
        with open(str(a / name)) as fh_a, open(str(b / name)) as fh_b:
            assert fh_a.read() == fh_b.read(), name


# --------------------------------------------------------------------------- #
# F-C2 / D-R5 — the CLI wing deck is about the loads reference axis
# --------------------------------------------------------------------------- #
def _project_with_lra(tmp_path, pct: float) -> str:
    """ga6 with its wing surface's loads reference axis moved to ``pct`` chord.

    Written as a project file rather than mutated in memory because the gate is
    about the **CLI route**: it must load, build and transfer, exactly as a
    scripted run does.
    """
    project = sloads_io.load_project(GA6)
    geom = project.geometry.by_name(project.wing_mass.surface)
    assert geom is not None and geom.ref_axis_pct == 0.40, (
        "fixture assumption: the shipped wing LRA is the entered 40% chord "
        "(step 12/R-7a); these tests move it elsewhere so the deck pins the "
        "transfer, not the fixture")
    geom.ref_axis_pct = pct
    path = os.path.join(str(tmp_path), "lra.project.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sloads_io.project_to_json(project))
    return path


def test_the_cli_wing_deck_is_stated_about_the_loads_reference_axis(tmp_path):
    """D-R5: the headless wing export transfers to the LRA, and says so in-band.

    The axis is pinned by name in the span CSV's ``MyyAxis`` column -- the
    in-band statement a consumer reads -- so a regression to the 25 % chord
    fails here rather than shipping a silently different torsion.
    """
    path = _project_with_lra(tmp_path, 0.45)
    prefix = os.path.join(str(tmp_path), "w")
    assert cli.main([path, "--export-sbeam", prefix]) == 0

    with open(prefix + ".span_loads.csv", newline="") as fh:
        rows = list(csv.DictReader(_io.StringIO(strip_comment_lines(fh.read()))))
    assert rows
    assert {r["MyyAxis"] for r in rows} == {"LRA 45% chord"}, "not on the LRA"


def test_the_headless_and_gui_wing_decks_are_the_same_deck(tmp_path):
    """Both front-ends produce the same bytes -- the module contract, both ways.

    ``report.content.component_loads`` (the GUI/report route) transfers to the
    LRA; the CLI now uses the same two calls. This asserts the *outcome* rather
    than the call sequence, so a future divergence in either front-end fails.
    """
    path = _project_with_lra(tmp_path, 0.45)
    prefix = os.path.join(str(tmp_path), "w")
    assert cli.main([path, "--export-sbeam", prefix, "--stick-model"]) == 0

    from sloads.derived_geometry import sob_station

    project = sloads_io.load_project(path)
    gui = loads_ref_axis_results(project, build_net_loads(project).wing_net)
    # The GUI route (app/views/export_report.py) passes the resolved SOB to the
    # stick model, so the reference build here does too.
    sob = sob_station(project)
    for suffix, build in ((".loads.bdf", lambda r: sb.force_moment_cards(r)),
                          (".stick.bdf", lambda r: sb.stick_model_bdf(r, sob=sob))):
        with open(prefix + suffix) as fh:
            assert fh.read().endswith(build(gui)), suffix
    with open(prefix + ".span_loads.csv", newline="") as fh:
        assert strip_comment_lines(fh.read()) == sb.span_load_csv(gui)


# --------------------------------------------------------------------------- #
# F-D3 / L-8g — every headless artifact carries the methods stamp
# --------------------------------------------------------------------------- #
_STAMP_MARKER = {".csv": "#", ".bdf": "$"}


@pytest.mark.parametrize("target", cli.EXPORT_TARGETS)
def test_every_exported_file_carries_the_methods_stamp(tmp_path, target):
    """G8.3 in every headless channel: basis, units and approved corrections.

    Before this the whole headless route was the one channel that stated its
    ULTIMATE basis nowhere -- the route the sizing loop scripts.
    """
    for name in _export(tmp_path, target):
        marker = _STAMP_MARKER[os.path.splitext(name)[1]]
        with open(os.path.join(str(tmp_path), name)) as fh:
            text = fh.read()
        assert text.startswith(f"{marker} METHODS AND LIMITATIONS"), name
        assert "ULTIMATE" in text and "APPROVED CORRECTIONS" in text, name


def test_the_load_case_csv_carries_the_stamp_and_still_parses(tmp_path):
    """The ``-o`` module CSV is stamped too, and a reader still reads it."""
    out = os.path.join(str(tmp_path), "engine.csv")
    assert cli.main(["engine", GA6, "-o", out]) == 0
    with open(out, newline="") as fh:
        text = fh.read()
    assert text.startswith("# METHODS AND LIMITATIONS")
    rows = list(csv.DictReader(_io.StringIO(strip_comment_lines(text))))
    assert rows and any("lbs-ULT" in (h or "") for h in rows[0])


def test_a_stamped_headless_deck_still_parses_as_bulk_data(tmp_path):
    """``$`` is a comment to every bulk-data parser -- the stamp is inert.

    Asserted through the suite's own card parser (the closure gate's owner), so
    the claim is the same one the equilibrium tests rely on.
    """
    from sloads.export.equilibrium import parse_cards

    project = sloads_io.load_project(GA6)
    unstamped = sb.force_moment_cards(
        loads_ref_axis_results(project, build_net_loads(project).wing_net))
    _export(tmp_path, "wing")
    with open(os.path.join(str(tmp_path), "out.loads.bdf")) as fh:
        stamped = fh.read()
    assert stamped != unstamped, "the fixture must actually be stamped"
    assert parse_cards(stamped) == parse_cards(unstamped)


def test_a_headless_export_is_byte_stable_across_runs(tmp_path):
    """No clock in the stamp unless the caller supplies one (report.methods).

    A deliverable that changes bytes every run cannot be diffed between two
    revisions, which is the whole reason the renderer never reads the clock.
    """
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    for d in (a, b):
        assert cli.main([GA6, "--export-sbeam", str(d / "out")]) == 0
    for name in sorted(os.listdir(str(a))):
        with open(str(a / name)) as fh_a, open(str(b / name)) as fh_b:
            assert fh_a.read() == fh_b.read(), name

    # ...and a supplied timestamp does reach the file, so the determinism above
    # is the default rather than the stamp being incapable of carrying one.
    assert cli.main([GA6, "--export-sbeam", str(b / "t"),
                     "--generated", "2026-08-10 09:00"]) == 0
    with open(str(b / "t.loads.bdf")) as fh:
        assert "2026-08-10 09:00" in fh.read()


# --------------------------------------------------------------------------- #
# m2 — one error contract
# --------------------------------------------------------------------------- #
def _empty_project(tmp_path) -> str:
    path = os.path.join(str(tmp_path), "empty.project.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sloads_io.project_to_json(Project(name="empty")))
    return path


@pytest.mark.parametrize("target", cli.EXPORT_TARGETS)
def test_an_absent_input_is_one_error_line_not_a_traceback(tmp_path, capsys, target):
    """Every route, one contract: ``error: …`` on stderr, status 1, no traceback.

    m2: ``control`` swallowed everything, an all-skipped run raised through
    ``main``, the wing/tail targets let ``MissingInputError`` reach the terminal
    as a traceback, and only ``--export-conm2`` caught and printed.
    """
    project = _empty_project(tmp_path)
    prefix = os.path.join(str(tmp_path), "out")
    assert cli.main([project, "--export-sbeam", prefix,
                     "--export-target", target]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error: "), captured.err
    assert "Traceback" not in captured.err
    assert not [f for f in os.listdir(str(tmp_path)) if f.startswith("out")], \
        "a failed export must not leave a partial artifact set"


def test_an_invalid_control_surface_input_fails_rather_than_vanishing(tmp_path, capsys):
    """m2's core: bad input and absent input are different answers.

    ``except ValueError`` around each control-surface build made a mistyped
    aileron area indistinguishable from an airplane with no aileron -- the deck
    simply came out short a case. ``MissingInputError`` ("not my turn") still
    skips; a plain ``ValueError`` (an invalid domain input) now fails the run.
    """
    with open(GA6) as fh:
        raw = json.load(fh)
    assert raw["aileron_loads"]["area_fwd_hinge_sqft"] > 0
    raw["aileron_loads"]["area_fwd_hinge_sqft"] = 0.0
    raw["aileron_loads"]["area_aft_hinge_sqft"] = 0.0
    path = os.path.join(str(tmp_path), "bad.project.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh)

    assert cli.main([path, "--export-sbeam", os.path.join(str(tmp_path), "out"),
                     "--export-target", "control"]) == 1
    assert "aileron area" in capsys.readouterr().err


def test_a_surface_with_no_input_slice_is_still_skipped(tmp_path):
    """The other half of the contract: absent really does mean skip.

    A project with no tab slice still exports its aileron and flap loads --
    tightening the ``except`` must not turn "not fitted" into a failed run.
    """
    with open(GA6) as fh:
        raw = json.load(fh)
    assert raw.pop("tab_loads", None) is not None
    path = os.path.join(str(tmp_path), "no_tab.project.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh)

    prefix = os.path.join(str(tmp_path), "out")
    assert cli.main([path, "--export-sbeam", prefix,
                     "--export-target", "control"]) == 0
    with open(prefix + ".control_surface.csv", newline="") as fh:
        rows = list(csv.DictReader(_io.StringIO(strip_comment_lines(fh.read()))))
    assert rows, "the fitted surfaces still export"


def test_a_module_run_reports_its_error_the_same_way(tmp_path, capsys):
    """The module route shares the contract -- it is one CLI, not five."""
    project = _empty_project(tmp_path)
    assert cli.main(["engine", project, "-o",
                     os.path.join(str(tmp_path), "o.csv")]) == 1
    assert capsys.readouterr().err.startswith("error: ")


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-q"]))
