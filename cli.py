"""Command-line runner for the sloads suite.

Run one module against a project file and emit its load-case CSV (or a text
report to stdout):

    python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
    python cli.py engine examples/ga6_normal.project.json        # text to stdout
    python cli.py --list                                         # registered modules

Or export loads to sbeam (CSV + FORCE/MOMENT cards). ``--export-target`` is the
whole deliverable menu -- every artifact the Export & Report page writes is
reachable headless, because the concept-loads -> sbeam sizing loop is meant to be
scripted:

===============  ===========================================================
target           what it writes
===============  ===========================================================
``wing``         the net wing load: span-load CSV + FORCE/MOMENT cards
                 (+ an optional CBAR stick model), transferred to the wing's
                 loads reference axis
``body``         the fuselage net distribution: FORCE deck, span-load CSV and
                 the wing-attach fitting-load CSV
``tail``         the chordwise tail loads (TAILDIST)
``htail-span``   the **spanwise** empennage beam loads (plan 09 T4)
``vtail-span``
``control``      the simplified control-surface loads (AILERON/FLAPLOAD/
                 TABLOADS)
``balanced``     the assembled full-span balanced free-free deck -- the
                 mission's primary loads deliverable
``gear``         the landing gear interface load definition (decision G-12) --
                 per case and per leg, the reaction at the tyre contact patch
                 with its strut state and ground angle, and the same reaction
                 at the gear reference point
``mass``         the CONM2/MASSSET mass model (same artifacts, same owner and
                 same names as ``--export-conm2``)
``lra``          the LRA beam model (step 12) -- node lines on the load
                 reference axes, CBAR chains, rigid posts/attachments/gear/
                 engine ties, the balanced cases' load sets transferred onto
                 the nodes. With ``--lra-import MODEL.bdf`` the loads are
                 instead transferred onto the imported model's own nodes,
                 under its GIDs (the named-node contract maps the families)
===============  ===========================================================

    python cli.py --export-sbeam out examples/ga6_normal.project.json
    python cli.py --export-sbeam out --export-target body examples/ga6_normal.project.json
    python cli.py --export-sbeam out --export-target balanced examples/ga6_normal.project.json
    python cli.py --export-conm2 out examples/ga6_normal.project.json

Or render the consolidated **summary report** (Step G8) -- the controlling
document of a loads deliverable. The ``.tex`` is always written; ask for a
``.pdf`` path and it is compiled too, when a TeX engine is on ``PATH``:

    python cli.py --report out.tex examples/ga6_normal.project.json
    python cli.py --report out.pdf examples/ga6_normal.project.json --units si

Output units follow ``--units imperial|si`` (default: the project's own
preference, else Imperial). An sbeam deck is written in the **solver** unit set,
which in SI is N / mm / N*mm / MPa -- consistent by construction, unlike the
N*m a report uses (M4-20 D-19).

**Every file written here carries the Step G8.3 methods & limitations stamp**
(``#`` on a CSV, ``$`` on a deck), exactly as the GUI bundle does: a headless
export states its ULTIMATE basis, its category and its approved corrections
in-band, so a file forwarded on its own is still self-describing (L-8g).

**Error contract** (one, for every export route): an absent input slice or an
invalid input is reported as ``error: <message>`` on stderr with exit status 1 --
never a traceback, and never a silently empty artifact. The one deliberate
exception is the ``control`` target, where an *absent* control-surface slice
(``MissingInputError``) skips that surface, because the three surfaces are
independent; an *invalid* one still fails the run, and a target where every
surface is absent fails too.
"""

from __future__ import annotations

import argparse
import sys

from sloads import MissingInputError, io, registry
from sloads.report import module_text_report, text_report
from sloads.units import UnitSystem, convert_results, unit_system_from


#: Every headless export target, in the order the module docstring lists them.
#: This tuple is the deliverable menu -- review F-D1 was that the menu and the
#: deliverable set had diverged, so a test pins them together rather than a
#: comment asking future readers to keep them in step.
EXPORT_TARGETS = ("wing", "body", "tail", "htail-span", "vtail-span",
                  "control", "balanced", "gear", "mass", "lra")


def resolve_units(project, flag=None) -> UnitSystem:
    """The unit system this run's output is rendered in.

    Resolution order, highest first: the ``--units`` flag, the project's own
    ``unit_system`` preference, then Imperial. A run with no flag and a project
    that never chose reproduces today's output exactly.
    """
    if flag:
        return unit_system_from(flag)
    return unit_system_from(getattr(project, "unit_system", None))


def _stamps(project, system: UnitSystem, generated: str = ""):
    """``(csv_stamp, bdf_stamp)`` -- the Step G8.3 methods & limitations block.

    The headless counterpart of the Export & Report page's one-stamp-per-bundle
    build (L-8g / review F-D3): built once per run from the *resolved* unit
    system, then handed to every writer, so the files of one export cannot
    disagree with each other -- or with their own numbers -- about their basis
    or their units.

    ``scope`` is always the full case set: the Critical Loads opt-out selection
    is a GUI session state, so a headless export has nothing to filter and
    nothing to warn a recipient about. ``generated`` is the caller's timestamp
    and defaults to absent, which keeps two headless runs of one project
    byte-identical (the renderer never reads the clock -- see
    ``report.methods``).
    """
    from sloads.report.methods import bdf_comment_block, csv_comment_block

    kwargs = dict(tool_version=_tool_version(), scope="full case set",
                  system=system, generated=generated or None)
    return csv_comment_block(project, **kwargs), bdf_comment_block(project, **kwargs)


def _export_conm2(project, prefix: str,
                  system: UnitSystem = UnitSystem.IMPERIAL,
                  bdf_stamp: str = "") -> int:
    """Write the CONM2/MASSSET mass model (plan 12 C-4).

    Three artifacts, and the split matters: the **fragment** is the mass model
    alone, for pasting into a model that already has the nodes; the **check
    deck** is self-contained and runnable (MASSSET + GRAV, and deliberately no
    load cards at all); the **inertia-only** file is sloads' own contribution,
    for comparing against what sbeam recovers -- never for applying.

    ``system`` is resolved once and passed to every writer, so the files of one
    export cannot disagree about their units (D-19), and ``bdf_stamp`` likewise
    so all three state one basis.

    A project with no weight database raises (caught by ``main``'s one error
    contract); a project that has one but from which no payload case is
    derivable still gets its fragment, with the two per-case artifacts reported
    as absent by name -- an unbuildable check deck is a fact about the data, not
    a failed run.
    """
    from sloads.export import mass_cards as mc

    fragment = mc.conm2_fragment(project, header_comment=bdf_stamp, system=system)

    label = "Imperial" if system == UnitSystem.IMPERIAL else "SI"
    written = []
    path = f"{prefix}_mass.bdf"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(fragment)
    written.append(path)

    for name, build in (("mass_check", mc.mass_check_deck),
                        ("inertia_only", mc.inertia_only_cards)):
        try:
            text = build(project, header_comment=bdf_stamp, system=system)
        except ValueError as exc:
            print(f"note: no {name} deck -- {exc}", file=sys.stderr)
            continue
        path = f"{prefix}_{name}.bdf"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        written.append(path)

    _, loadings = mc.mass_cards(project)
    print(f"Wrote {', '.join(written)} ({label}; "
          f"{len(loadings)} derivable payload case(s))")
    return 0


def _export_sbeam(project, prefix: str, target: str, stick_model: bool,
                  system: UnitSystem = UnitSystem.IMPERIAL,
                  csv_stamp: str = "", bdf_stamp: str = "",
                  lra_import: str = "") -> int:
    """Build the loads for ``target`` and write the sbeam export artifacts.

    ``system`` is resolved once here and passed to every writer, so the files of
    one export cannot disagree with each other about their units (M4-20 D-19);
    ``csv_stamp``/``bdf_stamp`` ride along for the same reason (G8.3).

    Nothing here catches an exception: an absent or invalid input reaches
    ``main``'s single error contract. The one exception is the ``control``
    target -- see below.
    """
    from sloads.export import sbeam_bridge as sb

    if target == "tail":
        from sloads.modules.taildist import build_tail_chordwise

        results = build_tail_chordwise(project)
        csv_path = f"{prefix}.tail_chordwise.csv"
        bdf_path = f"{prefix}.tail_loads.bdf"
        sb.write_tail_chordwise_csv(results, csv_path, header_comment=csv_stamp,
                                    system=system)
        sb.write_tail_force_moment_cards(results, bdf_path,
                                         header_comment=bdf_stamp, system=system)
        print(f"Wrote {len(results)} tail condition(s) to: {csv_path}, {bdf_path}")
        return 0

    if target in ("htail-span", "vtail-span"):
        from sloads.modules.tail_span import build_tail_span

        component = target.split("-")[0]
        results = build_tail_span(project)[component]
        if not results:
            raise MissingInputError(
                f"no spanwise {component} loads: the surface needs an area and a "
                "span, and a critical condition carrying an LT25/LT50 split")
        csv_path = f"{prefix}.{component}_span.csv"
        bdf_path = f"{prefix}.{component}_span_loads.bdf"
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(sb.tail_span_csv(results, component=component,
                                      header_comment=csv_stamp, system=system))
        sb.write_tail_span_force_moment_cards(results, bdf_path, component=component,
                                              header_comment=bdf_stamp,
                                              system=system)
        print(f"Wrote {len(results)} {component} condition(s) to: "
              f"{csv_path}, {bdf_path}")
        return 0

    if target == "control":
        from sloads.modules.aileron import build_aileron
        from sloads.modules.flap import build_flap
        from sloads.modules.tab import build_tabs

        # The three surfaces are independent inputs, so an *absent* slice skips
        # that surface only -- but an *invalid* one is a defect and propagates,
        # per the error-handling contract (MissingInputError is "not my turn";
        # a plain ValueError is a bad input). Catching ValueError here made a
        # mistyped aileron area indistinguishable from an unfitted aileron.
        results = []
        for build in (build_aileron, build_flap, build_tabs):
            try:
                results.extend(build(project))
            except MissingInputError:
                pass
        if not results:
            raise MissingInputError(
                "no control-surface loads: this project has no aileron, flap or "
                "tab input slice to export")
        csv_path = f"{prefix}.control_surface.csv"
        bdf_path = f"{prefix}.control_surface.bdf"
        sb.write_control_surface_csv(results, csv_path, header_comment=csv_stamp,
                                     system=system)
        sb.write_control_surface_force_moment_cards(
            results, bdf_path, header_comment=bdf_stamp, system=system)
        print(f"Wrote {len(results)} control-surface condition(s) to: {csv_path}, {bdf_path}")
        return 0

    if target == "body":
        from sloads.modules.body_loads import build_body_loads

        results = build_body_loads(project)
        bdf_path = f"{prefix}.body_loads.bdf"
        span_path = f"{prefix}.body_span_loads.csv"
        # Reported beside the FORCE set, never in it -- the span loads already
        # carry the carry-through reaction (M4-1), so applying the point
        # reactions too would double them.
        fitting_path = f"{prefix}.body_fitting_loads.csv"
        sb.write_body_force_moment_cards(results, bdf_path,
                                         header_comment=bdf_stamp, system=system)
        sb.write_body_span_load_csv(results, span_path, header_comment=csv_stamp,
                                    system=system)
        sb.write_body_fitting_load_csv(results, fitting_path,
                                       header_comment=csv_stamp, system=system)
        print(f"Wrote {len(results)} fuselage condition(s) to: "
              f"{bdf_path}, {span_path}, {fitting_path}")
        return 0

    if target == "gear":
        # The gear report needs LANDLOAD output and gear geometry and **no mass
        # model**, so it reaches airplanes the assembled ground cases do not --
        # which is why it is its own target rather than a file the balanced
        # target happens to drop beside its deck.
        csv_path = f"{prefix}.gear_loads.csv"
        sb.write_gear_report_csv(project, csv_path, header_comment=csv_stamp,
                                 system=system)
        rows = sb.gear_report_rows(project)
        print(f"Wrote {len(rows)} gear interface load row(s) to: {csv_path}")
        return 0

    if target == "lra":
        # The third deliverable (note 24 R-1). A missing datum raises
        # LraRefusal (a ValueError), which main's one error contract reports
        # as ``error: <the datum>`` -- a refused model is a stated absence,
        # never a traceback and never an empty file.
        if lra_import:
            from sloads.export.lra_import import write_lra_loads_on_imported_model

            out_path = f"{prefix}.lra_loads.bdf"
            write_lra_loads_on_imported_model(project, lra_import, out_path,
                                              header_comment=bdf_stamp,
                                              system=system)
            print(f"Wrote balanced-case loads on the imported model "
                  f"{lra_import} to: {out_path}")
            return 0
        from sloads.export.lra_model import write_lra_model_bdf

        bdf_path = f"{prefix}.lra_model.bdf"
        write_lra_model_bdf(project, bdf_path, header_comment=bdf_stamp,
                            system=system)
        print(f"Wrote the LRA beam model to: {bdf_path}")
        return 0

    if target == "balanced":
        from sloads.export.balanced_deck import balanced_deck
        from sloads.modules.balance import build_balanced_cases

        # Assembled once here rather than inside the writer, so the count printed
        # is the deck's own case set and not a second pass that might differ.
        skipped = []
        cases = build_balanced_cases(project, skipped)
        bdf_path = f"{prefix}.balanced_airframe.bdf"
        with open(bdf_path, "w", encoding="utf-8") as fh:
            fh.write(balanced_deck(project, header_comment=bdf_stamp, system=system,
                                   cases=cases, skipped=skipped))
        note = f"; {len(skipped)} condition(s) not assembled" if skipped else ""
        print(f"Wrote {len(cases)} balanced case(s) to: {bdf_path}{note}")
        return 0

    # Wing (the default). The results are transferred to the wing surface's loads
    # reference axis first -- decision D-R5: the headless deck and the GUI's are
    # the same deck, and the module contract ("when the export is built from a
    # Project, the bridge first transfers the loads to the LRA") holds on the
    # route the sizing loop actually scripts. Every exported wing torsion,
    # station X and lever arm is therefore about the LRA, stated in-band by the
    # span CSV's `MyyAxis` column and the deck's `$` header.
    from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results

    results = loads_ref_axis_results(project, build_net_loads(project).wing_net)
    csv_path = f"{prefix}.span_loads.csv"
    bdf_path = f"{prefix}.loads.bdf"
    sb.write_span_load_csv(results, csv_path, header_comment=csv_stamp, system=system)
    sb.write_force_moment_cards(results, bdf_path, header_comment=bdf_stamp,
                                system=system)
    written = [csv_path, bdf_path]
    if stick_model:
        from sloads.derived_geometry import sob_station

        stick_path = f"{prefix}.stick.bdf"
        sb.write_stick_model_bdf(results, stick_path, header_comment=bdf_stamp,
                                 system=system, sob=sob_station(project))
        written.append(stick_path)
    print(f"Wrote {len(results)} case(s) to: " + ", ".join(written))
    return 0


def _tool_version() -> str:
    """The installed package version, for the report's provenance block."""
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - Python < 3.8
        return ""
    try:
        return version("sloads")
    except PackageNotFoundError:  # pragma: no cover - source checkout without install
        return ""


def _write_report(project, path: str, system: UnitSystem, generated: str = "") -> int:
    """Render the summary report to ``path`` (``.tex``, or ``.pdf`` to compile it).

    The ``.tex`` is the primary artifact and is written in both cases (beside the
    PDF), per decision G8-1: a machine with no TeX engine still gets the complete
    document source. ``generated`` is passed through so the caller owns the
    timestamp -- the renderer never reads the clock.
    """
    from sloads.report.latex import render_report

    tex = render_report(project, system=system, generated=generated,
                        tool_version=_tool_version())
    tex_path = path[:-4] + ".tex" if path.lower().endswith(".pdf") else path
    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(tex)
    print(f"Wrote {tex_path}")
    if not path.lower().endswith(".pdf"):
        return 0

    from sloads.export.pdf import compile_pdf

    result = compile_pdf(tex)
    if not result.ok:
        print(f"PDF not produced: {result.log}", file=sys.stderr)
        return 1
    with open(path, "wb") as fh:
        fh.write(result.pdf)
    print(f"Wrote {path} ({len(result.pdf)} bytes, {result.engine})")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a sloads module on a project.")
    parser.add_argument("module", nargs="?", help="module name, e.g. 'engine'")
    parser.add_argument("project", nargs="?", help="path to project.json")
    parser.add_argument("-o", "--output", help="write load-case CSV to this path")
    parser.add_argument("--list", action="store_true", help="list registered modules and exit")
    parser.add_argument(
        "--export-sbeam", metavar="PREFIX",
        help="export loads to sbeam files prefixed with PREFIX; which loads is "
             "--export-target (default: the net wing load). PROJECT is then the "
             "second positional argument",
    )
    parser.add_argument(
        "--export-target",
        choices=EXPORT_TARGETS,
        default="wing",
        help="with --export-sbeam, which deliverable to export (default: wing). "
             "'balanced' is the assembled full-span free-free deck; 'gear' is "
             "the landing gear interface load definition; 'mass' is "
             "the CONM2/MASSSET model, identical to --export-conm2; 'lra' is "
             "the LRA beam model (step 12)",
    )
    parser.add_argument(
        "--stick-model", action="store_true",
        help="with --export-sbeam, also write the CBAR stick-model BDF (wing target)",
    )
    parser.add_argument(
        "--lra-import", metavar="MODEL_BDF", default="",
        help="with --export-target lra: transfer the balanced-case loads onto "
             "this external GRID/CBAR beam model instead of the "
             "geometry-derived one -- the imported node line becomes the LRA "
             "and the cards are written under its own GIDs (the $ SLOADS-NODE "
             "named-node contract maps the families; nearest-node is the "
             "marked-assumed fallback)",
    )
    parser.add_argument(
        "--report", metavar="PATH",
        help="render the consolidated summary report to PATH (.tex; a .pdf path "
             "also compiles it when a TeX engine is available). PROJECT is then "
             "the second positional argument",
    )
    parser.add_argument(
        "--generated", metavar="STAMP", default="",
        help="the generation timestamp printed on the report title page and in "
             "every export's methods stamp (supplied by the caller so two runs "
             "stay byte-identical; omitted by default)",
    )
    parser.add_argument(
        "--export-conm2", metavar="PREFIX",
        help="write the CONM2/MASSSET mass model: PREFIX_mass.bdf (fragment), "
             "PREFIX_mass_check.bdf (runnable MASSSET+GRAV deck) and "
             "PREFIX_inertia_only.bdf (sloads' inertia, for comparison only)",
    )
    parser.add_argument(
        "--units", choices=("imperial", "si"), default=None,
        help="unit system for the output; overrides the project's own preference "
             "for this run (default: the project's, else imperial)",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(registry.available()) or "(none registered)")
        return 0

    # --export-sbeam takes the project from the first positional (module slot) so
    # the module name is not required for an export-only run.
    if args.export_sbeam:
        project_path = args.module or args.project
        if not project_path:
            parser.error("--export-sbeam requires a project.json path")
        project = io.load_project(project_path)
        system = resolve_units(project, args.units)
        csv_stamp, bdf_stamp = _stamps(project, system, args.generated)
        # One error contract for every export route (review m2): an absent or
        # invalid input is a one-line `error:` on stderr and status 1, never a
        # traceback. The routes themselves catch nothing.
        try:
            if args.export_target == "mass":
                return _export_conm2(project, args.export_sbeam, system, bdf_stamp)
            return _export_sbeam(project, args.export_sbeam,
                                 args.export_target, args.stick_model,
                                 system, csv_stamp, bdf_stamp,
                                 lra_import=args.lra_import)
        except ValueError as exc:      # MissingInputError included -- it subclasses
            print(f"error: {exc}", file=sys.stderr)
            return 1

    # --export-conm2 follows --export-sbeam's shape: project from the first
    # positional, no module name needed. It is the same owner (and the same file
    # names) as `--export-target mass`; both spellings are kept because this one
    # shipped first.
    if args.export_conm2:
        project_path = args.module or args.project
        if not project_path:
            parser.error("--export-conm2 requires a project.json path")
        project = io.load_project(project_path)
        system = resolve_units(project, args.units)
        _, bdf_stamp = _stamps(project, system, args.generated)
        try:
            return _export_conm2(project, args.export_conm2, system, bdf_stamp)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    # --report likewise takes the project from the first positional, so no module
    # name is needed for a report-only run.
    if args.report:
        project_path = args.module or args.project
        if not project_path:
            parser.error("--report requires a project.json path")
        project = io.load_project(project_path)
        return _write_report(project, args.report,
                             resolve_units(project, args.units), args.generated)

    if not args.module or not args.project:
        parser.error("module and project are required (or use --list / "
                     "--export-sbeam / --report)")

    try:
        run = registry.get(args.module)
    except KeyError as exc:
        parser.error(str(exc))

    project = io.load_project(args.project)
    try:
        result = run(project)
    except ValueError as exc:          # same one contract as the export routes
        print(f"error: {exc}", file=sys.stderr)
        return 1
    system = resolve_units(project, args.units)
    # The two text reports take *converted* results plus a display label; the CSV
    # writer converts internally (M4-20 step 3), so it gets the raw results and
    # the system -- handing it ``conditions`` would be a double conversion.
    conditions = convert_results(result.conditions, system)
    label = "Imperial" if system == UnitSystem.IMPERIAL else "SI"

    if args.output:
        # A downloaded CSV leaves the tool, so it owes the same G8.3 basis
        # statement the GUI's does -- the text report to stdout does not, being
        # a terminal view rather than an artifact.
        csv_stamp, _ = _stamps(project, system, args.generated)
        io.write_load_cases_csv(result.conditions, args.output,
                                header_comment=csv_stamp, system=system)
        print(f"Wrote {len(conditions)} condition(s) to {args.output} ({label})")
    elif args.module == "engine" and project.engine is not None:
        print(text_report(project.engine, conditions, unit_system=label))
    else:
        print(module_text_report(result.module, conditions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
