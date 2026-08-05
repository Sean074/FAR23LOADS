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


def _export_sbeam(project, prefix: str, target: str, stick_model: bool) -> int:
    """Build the loads for ``target`` and write the sbeam export artifacts."""
    from sloads.export import sbeam_bridge as sb

    if target == "tail":
        from sloads.modules.taildist import build_tail_chordwise

        results = build_tail_chordwise(project)
        csv_path = f"{prefix}.tail_chordwise.csv"
        bdf_path = f"{prefix}.tail_loads.bdf"
        sb.write_tail_chordwise_csv(results, csv_path)
        sb.write_tail_force_moment_cards(results, bdf_path)
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
        sb.write_control_surface_csv(results, csv_path)
        sb.write_control_surface_force_moment_cards(results, bdf_path)
        print(f"Wrote {len(results)} control-surface condition(s) to: {csv_path}, {bdf_path}")
        return 0

    from sloads.modules.net_loads import build_net_loads

    results = build_net_loads(project).wing_net
    csv_path = f"{prefix}.span_loads.csv"
    bdf_path = f"{prefix}.loads.bdf"
    sb.write_span_load_csv(results, csv_path)
    sb.write_force_moment_cards(results, bdf_path)
    written = [csv_path, bdf_path]
    if stick_model:
        stick_path = f"{prefix}.stick.bdf"
        sb.write_stick_model_bdf(results, stick_path)
        written.append(stick_path)
    print(f"Wrote {len(results)} case(s) to: " + ", ".join(written))
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
        # The sbeam writers are still Imperial-only (M4-20 step 4 gives them the
        # consistent N/mm/N*mm solver set). Refuse rather than silently write a
        # deck in the wrong units -- a deck whose units are not what was asked
        # for is exactly the failure this whole item exists to prevent.
        if resolve_units(project, args.units) != UnitSystem.IMPERIAL:
            parser.error(
                "SI sbeam export is not implemented yet (M4-20 step 4); "
                "re-run with --units imperial, or export the CSV/report instead"
            )
        return _export_sbeam(project, args.export_sbeam,
                             args.export_target, args.stick_model)

    if not args.module or not args.project:
        parser.error("module and project are required (or use --list / --export-sbeam)")

    try:
        run = registry.get(args.module)
    except KeyError as exc:
        parser.error(str(exc))

    project = io.load_project(args.project)
    result = run(project)
    system = resolve_units(project, args.units)
    conditions = convert_results(result.conditions, system)
    label = "Imperial" if system == UnitSystem.IMPERIAL else "SI"

    if args.output:
        io.write_load_cases_csv(conditions, args.output)
        print(f"Wrote {len(conditions)} condition(s) to {args.output} ({label})")
    elif args.module == "engine" and project.engine is not None:
        print(text_report(project.engine, conditions, unit_system=label))
    else:
        print(module_text_report(result.module, conditions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
