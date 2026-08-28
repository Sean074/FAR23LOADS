- **The oracle GUI user guide ships (design note 34, #96, tier M,
  2026-08-27).** A new docs section `docs/60_guide/`: front matter (index,
  getting started, before-you-start checklist, conventions with the one
  LIMIT-vs-ULTIMATE statement — UG-8), one chapter per oracle page in
  `sloads.workflow.oracle_steps()` order with the eight-section note-34
  template, and four appendices (the `ga6_normal` Appendix A pass with
  page-cited checkpoints, the `baron_58` SI pass closing on the unit channel
  — UG-12, troubleshooting, where-next). Per-page **field tables and the
  chapter list are generated** from `sloads/field_registry.py` by
  `docs/generate_data_dict.py` into `60_guide/_generated/` (UG-3/UG-7 —
  adding a `.BAS`-backed step scaffolds its chapter with no hand edit);
  screenshots come from the re-runnable Playwright script
  `scripts/capture_guide_shots.py` (UG-4; `playwright` joins the dev extra).
  The worked twin is new: **`examples/baron_58.project.json`** (UG-9), a
  Beech Baron 58 / two IO-550-C built from FAA Aircraft Spec 3A16 with every
  estimate marked in `examples/baron_58.sources.md`, running all fourteen
  oracle pages warning-free — including ONENGOUT — with D-25 entered ground
  loadings, and declared `EXACT` under the oracle-reduction gate. Acceptance
  gates **G-UG-1…G-UG-6** (`tests/test_guide.py`) landed before any chapter:
  chapter↔step bijection, generated-tree exactness, image↔reference
  closure with alt text, both examples running every module they reach,
  link resolution, and the template-heading order. `10_standard/GUI_USER_GUIDE.md`
  is not superseded (UG-2) — the two guides now cross-link. Filed en route:
  #121 (main-GUI `float(None)` crash on the blank SELECT aileron field) and
  #122 (the OV-7 derive chain escaping as a raw traceback on a half-entered
  planform).
