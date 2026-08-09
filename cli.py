"""Command-line runner for the sloads suite.

Run one module against a project file and emit its load-case CSV (or a text
report to stdout):

    python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
    python cli.py engine examples/ga6_normal.project.json        # text to stdout
    python cli.py --list                                         # registered modules

Or export loads to sbeam (CSV + FORCE/MOMENT cards). The wing target (default)
writes the net wing load (span-load CSV + FORCE/MOMENT cards + an optional CBAR
stick model); ``--export-target tail`` writes the chordwise tail loads (TAILDIST);
``--export-target control`` writes the simplified control-surface loads
(AILERON / FLAPLOAD / TABLOADS):

    python cli.py --export-sbeam out examples/ga6_normal.project.json
    python cli.py --export-sbeam out --export-target tail examples/ga6_normal.project.json
    python cli.py --export-sbeam out --export-target control examples/ga6_normal.project.json
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
"""

from __future__ import annotations

import argparse
import sys

from sloads import io, registry
from sloads.report import module_text_report, text_report
from sloads.units import UnitSystem, convert_results, unit_system_from


def resolve_units(project, flag=None) -> UnitSystem:
    """The unit system this run's output is rendered in.

    Resolution order, highest first: the ``--units`` flag, the project's own
    ``unit_system`` preference, then Imperial. A run with no flag and a project
    that never chose reproduces today's output exactly.
    """
    if flag:
        return unit_system_from(flag)
    return unit_system_from(getattr(project, "unit_system", None))


def _export_conm2(project, prefix: str,
                  system: UnitSystem = UnitSystem.IMPERIAL) -> int:
    """Write the CONM2/MASSSET mass model (plan 12 C-4).

    Three artifacts, and the split matters: the **fragment** is the mass model
    alone, for pasting into a model that already has the nodes; the **check
    deck** is self-contained and runnable (MASSSET + GRAV, and deliberately no
    load cards at all); the **inertia-only** file is sloads' own contribution,
    for comparing against what sbeam recovers -- never for applying.

    ``system`` is resolved once and passed to every writer, so the files of one
    export cannot disagree about their units (D-19).
    """
    from sloads.export import mass_cards as mc

    try:
        fragment = mc.conm2_fragment(project, system=system)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    label = "Imperial" if system == UnitSystem.IMPERIAL else "SI"
    written = []
    path = f"{prefix}_mass.bdf"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(fragment)
    written.append(path)

    for name, build in (("mass_check", mc.mass_check_deck),
                        ("inertia_only", mc.inertia_only_cards)):
        try:
            text = build(project, system=system)
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
                  system: UnitSystem = UnitSystem.IMPERIAL) -> int:
    """Build the loads for ``target`` and write the sbeam export artifacts.

    ``system`` is resolved once here and passed to every writer, so the files of
    one export cannot disagree with each other about their units (M4-20 D-19).
    """
    from sloads.export import sbeam_bridge as sb

    if target == "tail":
        from sloads.modules.taildist import build_tail_chordwise

        results = build_tail_chordwise(project)
        csv_path = f"{prefix}.tail_chordwise.csv"
        bdf_path = f"{prefix}.tail_loads.bdf"
        sb.write_tail_chordwise_csv(results, csv_path, system=system)
        sb.write_tail_force_moment_cards(results, bdf_path, system=system)
        print(f"Wrote {len(results)} tail condition(s) to: {csv_path}, {bdf_path}")
        return 0

    if target == "control":
        from sloads.modules.aileron import build_aileron
        from sloads.modules.flap import build_flap
        from sloads.modules.tab import build_tabs

        results = []
        for build in (build_aileron, build_flap, build_tabs):
            try:
                results.extend(build(project))
            except ValueError:
                pass  # skip a control surface whose input slice is absent
        csv_path = f"{prefix}.control_surface.csv"
        bdf_path = f"{prefix}.control_surface.bdf"
        sb.write_control_surface_csv(results, csv_path, system=system)
        sb.write_control_surface_force_moment_cards(results, bdf_path, system=system)
        print(f"Wrote {len(results)} control-surface condition(s) to: {csv_path}, {bdf_path}")
        return 0

    from sloads.modules.net_loads import build_net_loads

    results = build_net_loads(project).wing_net
    csv_path = f"{prefix}.span_loads.csv"
    bdf_path = f"{prefix}.loads.bdf"
    sb.write_span_load_csv(results, csv_path, system=system)
    sb.write_force_moment_cards(results, bdf_path, system=system)
    written = [csv_path, bdf_path]
    if stick_model:
        stick_path = f"{prefix}.stick.bdf"
        sb.write_stick_model_bdf(results, stick_path, system=system)
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
        help="export the net wing load to sbeam files prefixed with PREFIX "
             "(PROJECT is then the second positional argument)",
    )
    parser.add_argument(
        "--export-target", choices=("wing", "tail", "control"), default="wing",
        help="with --export-sbeam, which loads to export (default: wing)",
    )
    parser.add_argument(
        "--stick-model", action="store_true",
        help="with --export-sbeam, also write the CBAR stick-model BDF (wing target)",
    )
    parser.add_argument(
        "--report", metavar="PATH",
        help="render the consolidated summary report to PATH (.tex; a .pdf path "
             "also compiles it when a TeX engine is available). PROJECT is then "
             "the second positional argument",
    )
    parser.add_argument(
        "--generated", metavar="STAMP", default="",
        help="with --report, the generation timestamp printed on the title page "
             "(supplied by the caller so two renders stay byte-identical)",
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
        return _export_sbeam(project, args.export_sbeam,
                             args.export_target, args.stick_model,
                             resolve_units(project, args.units))

    # --export-conm2 follows --export-sbeam's shape: project from the first
    # positional, no module name needed.
    if args.export_conm2:
        project_path = args.module or args.project
        if not project_path:
            parser.error("--export-conm2 requires a project.json path")
        project = io.load_project(project_path)
        return _export_conm2(project, args.export_conm2,
                             resolve_units(project, args.units))

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
    result = run(project)
    system = resolve_units(project, args.units)
    # The two text reports take *converted* results plus a display label; the CSV
    # writer converts internally (M4-20 step 3), so it gets the raw results and
    # the system -- handing it ``conditions`` would be a double conversion.
    conditions = convert_results(result.conditions, system)
    label = "Imperial" if system == UnitSystem.IMPERIAL else "SI"

    if args.output:
        io.write_load_cases_csv(result.conditions, args.output, system=system)
        print(f"Wrote {len(conditions)} condition(s) to {args.output} ({label})")
    elif args.module == "engine" and project.engine is not None:
        print(text_report(project.engine, conditions, unit_system=label))
    else:
        print(module_text_report(result.module, conditions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
