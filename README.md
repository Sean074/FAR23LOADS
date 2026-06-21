# FAR 23 LOADS

A modern Python + Streamlit replication of the **FAR 23 LOADS** suite
(Hal C. McMaster, Aero Science Software) — the 22-program package that computes
the structural design loads a small aircraft must sustain under **FAR Part 23
Subpart C — Structure** — being grown into an **initial-concept distributed-loads
tool**: a `concept` mode that can exceed the FAR23 weight/seat limits, assessment
against similar airplanes, per-component distributed loads (wing / body / tail +
simplified control-surface distributions), and export to **sbeam** for structural
sizing. The FAR23 replication core stays validated against the manual; concept
mode is a superset of it. See
[`docs/30_future/01_concept_loads_plan.md`](docs/30_future/01_concept_loads_plan.md).

The codebase is a shared pure-calc package (`farloads`) plus a multi-page
Streamlit UI (`app/`) and a CLI (`cli.py`). A single reloadable `project.json`
carries every module's inputs; each module emits its own load-case CSV.

**License:** MIT (see [LICENSE](LICENSE)) — free to use, modify, and
redistribute, including commercially.

> **Status:** Phases 0–2 and Phase-C Steps **C0–C6** complete — **13 of 22**
> suite programs ported (ENGLOADS, WTESTIMA, WTONECG, WTENV, WINGGEOM, STRSPEED,
> MACHLIM, TAU, AIRLOADS, FLTLOADS, SELECT, WINGINER, NETLOADS) plus two modern
> modules (`configuration`, `body_loads`). The wing distributed-loads vertical
> slice (geometry → speeds → V-n envelope → airloads → inertia → net) exports to
> sbeam, and the critical-load selection (wing / h-tail / v-tail / fuselage) is
> oracle-locked. Next up: **Step C7** (TAILDIST + AIRLOAD4). Step-by-step plan:
> `docs/30_future/00_backlog.md`; Phase-C narrative:
> `docs/30_future/01_concept_loads_plan.md`; roadmap: `docs/10_standard/PROJECT_GUIDE.md`.

## Layout

```
farloads/                 # shared, pure-calc package (no I/O in calc)
├── constants.py          # g, pi (math.pi), unit factors, atmosphere — centralized
├── models.py             # Project + per-domain slices, ConditionResult, ModuleResult, SCHEMA_VERSION
├── units.py              # Imperial<->SI conversion at the I/O boundary
├── io.py                 # load/save project JSON; load-case CSV writer
├── registry.py           # name -> run(project) -> ModuleResult
├── report.py             # text/CSV rendering
├── export/               # output renderers (sbeam bridge); not registered modules
└── modules/              # one file per program (engine, weight_*, wing_*, airloads,
                          #   flight_envelope, select, net_loads, body_loads, configuration, …)
app/
├── Home.py               # load/save project, summary, run-all
└── pages/                # one Streamlit page per module (00_Configuration_Layout … 19_Engine_Mount)
cli.py                    # python cli.py engine project.json -o out.csv
tests/                    # pytest; each module vs the manual's appendices
examples/                 # ga6_normal (Appendix A) + concept_heavy (concept) project.json
docs/                     # by type: 10_standard, 20_theory, 30_future, 40_history (see docs/00_INDEX.md)
pyproject.toml            # build metadata, deps, ruff + pytest/coverage config
cspell.json               # domain wordlist
```

## Running

Install the package in editable mode (registers `farloads` and the `cli`
module on `sys.path`, so imports work from anywhere — including Streamlit):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e '.[dev]'            # runtime deps + pytest, pytest-cov, ruff

streamlit run app/Home.py                                   # the multi-page UI
farloads engine examples/ga6_normal.project.json -o engine_loads.csv   # CLI entry point
python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
pytest                                                      # the green-build gate
ruff check farloads/ cli.py                                 # lint
```

`requirements.txt` is kept for the bare runtime set; `pip install -e '.[dev]'`
is the supported developer install. CI (`.github/workflows/ci.yml`) runs ruff
and pytest on Python 3.9 / 3.11 / 3.12.

## Validation & math fidelity

The math is **modernized** (`math.pi`, clean equations). The manual's printed
worked-example figures are used as **tolerance-based** regression oracles
(±0.1%), not exact oracles — see `docs/10_standard/PROJECT_GUIDE.md §6`. The oracle is
Reference 1 (`FAR23 loads (1).pdf`, McMaster's theory manual), whose Appendix A
(6-place GA single) and Appendix B (10-place twin turboprop) print full loads
reports. Each module gets a `tests/test_<module>.py` that checks `run(project)`
against the appropriate appendix figures within tolerance.

## Engine-mount conditions (Phase 0 module)

For both **reciprocating** and **turboprop** engines:

| FAR §        | Condition                                                  | Engine type |
|--------------|------------------------------------------------------------|-------------|
| 23.361(a)(1) | Limit takeoff torque + 75% limit maneuver vertical load    | Both        |
| 23.361(a)(2) | Factor × max-continuous torque + 100% limit vertical load  | Both        |
| 23.363       | Side load, independent of other flight loads               | Both        |
| 23.361(a)(3) | Turboprop propeller control malfunction (1.6 × torque)     | Turboprop   |
| 23.361(b)(1) | Torque from sudden engine/rotor stoppage                   | Turboprop   |
| 23.371(b)    | Gyroscopic loads at max continuous RPM                     | Turboprop   |

Sign convention preserved from the original: engine-mount reaction torque is
reported negative; "clockwise from the pilot's view is positive" for rotor RPM
and stoppage torque. The `LPRINT` printer output is replaced with on-screen
tables plus downloadable text/CSV reports and the project JSON.

## Units

A sidebar toggle switches inputs and results between **Imperial** (lb, in, ft-lb,
hp) and **SI** (kg, mm, N·m, kW). It is purely a presentation layer: calculations
always run in the Imperial units of the original program (`farloads/units.py`
converts at the boundary). Saved project JSON is always canonical Imperial.

## Disclaimer

This project is an independent, modern **replication** of the FAR 23 LOADS suite
(Hal C. McMaster, Aero Science Software). It is intended as an educational and
exploratory engineering tool, validated against the worked examples printed in
the reference manual.

Results are **not certified** for safety-critical, regulated, or
certification structural design. The replication modernises the math (clean
equations, `math.pi`) and validates to a ±0.1% tolerance against the manual's
printed figures — it is not bit-for-bit identical to the original program.
Verify any results against the original suite, an established method, and
competent engineering judgement before relying on them for design or
airworthiness decisions.

The software is provided "as is", without warranty of any kind. See the
[LICENSE](LICENSE) file for the full disclaimer of liability.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 Sean O'Meara.
