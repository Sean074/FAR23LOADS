# sloads

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

The codebase is a shared pure-calc package (`sloads`) plus a multi-page
Streamlit UI (`app/`) and a CLI (`cli.py`). A single reloadable `project.json`
carries every module's inputs; each module emits its own load-case CSV.

**License:** MIT (see [LICENSE](LICENSE)) — free to use, modify, and
redistribute, including commercially.

> **Status:** Phases 0–2 and Phase-C Steps **C0–C11** complete — **all 22 of 22**
> Reference 1 Appendix-C suite programs ported (ENGLOADS, WTESTIMA, WTONECG, WTENV,
> WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, WINGINER,
> NETLOADS, TAILDIST, AILERON, FLAPLOAD, TABLOADS, ONENGOUT, LGFACTOR, LANDLOAD,
> BALLOADS) plus two modern modules (`configuration`, `body_loads`). The current
> schema version, test count and coverage are whatever CI reports on the latest
> commit — see the CI badge and `CHANGELOG.md`, not a number baked in here. The
> wing distributed-loads
> vertical slice (geometry → speeds → V-n envelope → airloads → inertia → net)
> exports to sbeam; the critical-load selection (wing / h-tail / v-tail / fuselage),
> chordwise tail distribution, simplified control-surface distributions (aileron /
> flap / tab), one-engine-out vertical-tail transient, and tricycle-gear
> landing/ground loads are complete (FAR23 path oracle-locked). Step-by-step plan
> for remaining refinements: `docs/30_future/00_backlog.md`; Phase-C narrative:
> `docs/30_future/01_concept_loads_plan.md`; roadmap: `docs/10_standard/PROJECT_GUIDE.md`.

## Layout

```
sloads/                 # shared, pure-calc package (no I/O in calc)
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
├── Home.py               # st.navigation entry point — sidebar phases from workflow.py (Start + six analysis-flow sections through Export)
└── views/                # one page per workflow step + dashboard / results_review / export_report
cli.py                    # python cli.py engine project.json -o out.csv
tests/                    # pytest; each module vs the manual's appendices
examples/                 # ga6_normal (Appendix A) + cessna_210 (normal cat), atr42_100 + dhc8_dash8 + concept_regional_jet (concept) run the full workflow; concept_heavy is a minimal concept-core demo (V-n → Flight Envelope only)
docs/                     # by type: 10_standard, 20_theory, 30_future, 40_history (see docs/00_INDEX.md)
pyproject.toml            # build metadata, deps, ruff + pytest/coverage config
cspell.json               # domain wordlist
```

## Running

Install the package in editable mode (registers `sloads` and the `cli`
module on `sys.path`, so imports work from anywhere — including Streamlit):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e '.[dev]'            # runtime deps + pytest, pytest-cov, ruff

streamlit run app/Home.py                                   # the multi-page UI
sloads engine examples/ga6_normal.project.json -o engine_loads.csv   # CLI entry point
python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
pytest                                                      # the green-build gate
ruff check sloads/ cli.py app/                            # lint
```

`pyproject.toml` is the single dependency source — `pip install -e .` for the
runtime set, `pip install -e '.[dev]'` for the supported developer install (a
second `requirements.txt` list was deleted at 0.5.0 because it had drifted from
it). CI (`.github/workflows/ci.yml`) runs ruff and pytest on Python
3.9 / 3.11 / 3.12.

## Validation & math fidelity

The math is **modernized** (`math.pi`, clean equations). The manual's printed
worked-example figures are used as **tolerance-based** regression oracles
(±0.1%), not exact oracles — see `docs/10_standard/PROJECT_GUIDE.md §6`. The oracle is
Reference 1 (`FAR23Loads_Code.pdf`, McMaster's theory manual). **Appendix A**
(6-place GA single, p131) is the printed oracle and is in hand; **Appendix B**
(10-place twin turboprop, p251) is **absent from the bundled PDF**, so modules with
GA-single figures are *oracle-locked* against Appendix A while twin/turboprop-only
cases (e.g. `one_engine_out`, the turbopropeller engine-mount case) are
*closure-locked* to the `.BAS` source with the printed twin oracle deferred. The
canonical, per-module validation status lives in
[`docs/20_theory/00_theory_sources.md` § Oracle status](docs/20_theory/00_theory_sources.md#oracle-status).

## Units

A sidebar toggle switches inputs and results between **Imperial** (lb, in, ft-lb,
hp) and **SI** (kg, mm, N·m, kW). It is purely a presentation layer: calculations
always run in the Imperial units of the original program (`sloads/units.py`
converts at the boundary). Saved project JSON is always canonical Imperial.

## Disclaimer

This project is an independent, modern **open replication** of the FAR23 loads
suite (DOT/FAA/AR-96/46; Hal C. McMaster's CAE theory manual, Aero Science
Software). It is intended as an educational and exploratory engineering tool,
validated against the worked examples printed in the reference manual.

It is **not affiliated with, endorsed by, or associated with McGettrick
Structural Engineering, Inc. or DARcorporation**, whose "FAR 23 LOADS" is a
separate commercial product.

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
