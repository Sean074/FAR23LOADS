- **Test-suite runtime, CI speed and git hooks (code-standard review item 8,
  tier S, 2026-08-16).** Measured first: the parallel suite was 59 s locally
  and ~12 min per CI leg. (1) One test —
  `test_imperial_csv_is_byte_identical_to_the_no_system_call` — re-loaded the
  project and re-ran *all* modules once per (example, module) key, ~130 full
  pipeline runs for the same assertion; it now builds the defaults once per
  example. Suite 59 → 36 s locally, no test over 10 s. (2) CI runs branch
  coverage on the **3.12 leg only** (matrix `include`), the 3.9/3.11 legs
  uninstrumented; `--durations=15` on every leg so the next hot spot is visible
  in the log. (3) **No `slow` marker** — deliberately: with the numbers above a
  fast subset saves seconds and adds a thing to keep in step
  (`00_program_overview.md` §Testing states the revisit thresholds).
  (4) `.pre-commit-config.yaml` (opt-in, local hooks on the venv's own tools):
  ruff + mypy on commit, whole suite on push. (5) `ruff` and `mypy` **pinned**
  in `[dev]` (`ruff==0.16.3`, `mypy==2.3.1`) — a newer ruff on the runner than on
  the desk is what turned a green local run into a red PR (RUF068); a bump is
  now a one-line PR whose CI run reviews the new rules. `pre-commit` added to
  `[dev]`; `CONTRIBUTING.md` §2 gains the install line.
