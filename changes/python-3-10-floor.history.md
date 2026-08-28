- **Python 3.10 is the floor, and the support claim is one claim (#132, tier M,
  2026-08-28)** — 0.8.0's first full-matrix run on `main` failed at install on
  the 3.9 leg: `streamlit >= 1.51` (the #129 `width=` floor) declares
  `Requires-Python >= 3.10`, and the floor bump had verified the API but not
  the interpreter support behind it. The owner dropped 3.9 (EOL 2025-10;
  Streamlit dropped it at 1.51) over re-arming `use_container_width` on the
  plotly sites, and the fix made the support claim structural: `requires-python`,
  the trove classifiers and the `ci.yml` full matrix now state one set, guarded
  by `test_the_python_support_claim_is_one_claim_in_three_places` (classifiers ≡
  matrix, floor = smallest tested leg, mutation-verified both ways); the
  dependency-side half of the class stays with the full-matrix install on
  `main`, where this instance surfaced. Docs stating the matrix swept
  (`CLAUDE.md`, `README.md`, `CONTRIBUTING.md`, `00_program_overview.md`,
  `DEVELOPMENT_PROCESS.md`, `RELEASE_PROCESS.md`, `WORKFLOW_COMMANDS.txt`,
  `CONVENTIONS.md`); B905/RUF007 parked beside `UP` as deliberate churn.
