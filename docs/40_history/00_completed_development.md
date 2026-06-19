# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

---

## Phase 0 — Package restructure (complete)

**Objective.** Recast the standalone `engloads` program into the shared
pure-calc package + thin-shell architecture that every subsequent module will
follow, with the engine-mount module as the proof of pattern.

**Deliverables.**
- `farloads/` pure-calc package: `models.py` (`Project`, `EngineInput`/`Rotor`,
  `ConditionResult`/`LoadValue`, `ModuleResult`, `SCHEMA_VERSION`),
  `modules/engine.py` (port of `ENGLOADS.BAS`), `registry.py`, `io.py`,
  `units.py`, `report.py`, `constants.py`.
- `app/` Streamlit multi-page UI (`Home.py` + `pages/19_Engine_Mount.py`).
- `cli.py` argparse front-end.
- `tests/` suite vs the manual's Appendix A/B figures.

**Test / Acceptance.** Green build — full `pytest` suite passing, engine module
checked against Appendix A (p131) and Appendix B (p251) figures within ±0.1%.

**Key decisions.**
1. **Hybrid architecture** — one shared calc package, interchangeable GUI/CLI/test
   front-ends; calc does no I/O.
2. **Single reloadable `Project`** — one JSON bundle carries every module's input
   slice; `schema_version` from day one.
3. **Modernize the math** — `math.pi` and clean equations, *not* the BASIC's
   `3.1416`. The manual's printed figures become **tolerance-based** regression
   oracles (±0.1%), not exact oracles. Constants centralised in `constants.py` so
   this stays a one-file decision.
4. **Preserved engineering conventions** — engine-mount reaction torque reported
   negative; "clockwise from the pilot's view is positive"; selected intermediate
   quantities truncated to 3 decimals (`int(x*1000)/1000`) to mirror the BASIC.

---

## Tooling & documentation standard (complete)

**Objective.** Bring the project's tooling and documentation standard in line
with the sibling `sbeam` project before the module-porting work scales up.

**Deliverables.**
- `pyproject.toml` — editable install (`pip install -e '.[dev]'`), so `farloads`
  and `cli` import from any cwd; the `sys.path` shims were removed from `app/`.
  `ruff` (select `E`/`F`/`W`, ignore `E741`) and `pytest`/coverage config.
- `cspell.json` domain wordlist.
- `.github/workflows/ci.yml` — `ruff` + `pytest` on Python 3.9 / 3.11 / 3.12.
- `docs/` reorganised by type (`10_standard` / `20_theory` / `30_future` /
  `40_history`) with `docs/00_INDEX.md`.
- `docs/10_standard/CODE_REVIEW_PROCESS.md` and `RELEASE_PROCESS.md`;
  `CHANGELOG.md` (Keep a Changelog).
- `CLAUDE.md` mandate strengthened: consult `reference/`, keep `docs/` in sync,
  and the backlog→history→changelog move-on-completion rule.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passing after the `sys.path` shims were removed.

**Key decisions.**
- CI lints `farloads/` and `cli.py` (the pure calc + CLI). Streamlit pages in
  `app/` are not lint-gated: their long widget-label lines and the deliberate
  late `from farloads.modules import engine` import are acceptable there.
- `requires-python = ">=3.9"` to match `sbeam` (the code uses
  `from __future__ import annotations`, so 3.9 is safe).

---

## Resolved defects

- _(none recorded)_
