"""Command-line runner for the FAR 23 LOADS suite.

Run one module against a project file and emit its load-case CSV (or a text
report to stdout):

    python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
    python cli.py engine examples/ga6_normal.project.json        # text to stdout
    python cli.py --list                                         # registered modules
"""

from __future__ import annotations

import argparse
import sys

from farloads import io, registry
from farloads.report import module_text_report, text_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a FAR 23 LOADS module on a project.")
    parser.add_argument("module", nargs="?", help="module name, e.g. 'engine'")
    parser.add_argument("project", nargs="?", help="path to project.json")
    parser.add_argument("-o", "--output", help="write load-case CSV to this path")
    parser.add_argument("--list", action="store_true", help="list registered modules and exit")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(registry.available()) or "(none registered)")
        return 0

    if not args.module or not args.project:
        parser.error("module and project are required (or use --list)")

    try:
        run = registry.get(args.module)
    except KeyError as exc:
        parser.error(str(exc))

    project = io.load_project(args.project)
    result = run(project)

    if args.output:
        io.write_load_cases_csv(result, args.output)
        print(f"Wrote {len(result.conditions)} condition(s) to {args.output}")
    elif args.module == "engine" and project.engine is not None:
        print(text_report(project.engine, result.conditions))
    else:
        print(module_text_report(result.module, result.conditions))

    return 0


if __name__ == "__main__":
    sys.exit(main())
