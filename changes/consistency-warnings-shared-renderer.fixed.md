- **The oracle GUI shows the entry-error warnings it was already computing, and
  two page tags stopped naming pages that do not exist (C210-35, issue #82,
  tier M, 2026-08-24).** `sloads.validation.consistency_warnings` is part of the
  analysis contract, and `oracle_app`/`app_shell` had **no consumer of
  `ConsistencyWarning` at all** — so a page-targeted entry-error channel was dark
  exactly where entries are made. On the C210 build that meant six detected
  contradictions were never shown, including both `wing_fraction`-on-a-wing-row
  entries; the 85-lb wing-tie gap they caused took three GUI round-trips to close
  and was found only by reading the saved file off-GUI.
  `app_shell.components.render_consistency_warnings(project, key)` is now the
  **only** consumer in either front-end, called by `page_header` from the step key
  it already holds — so every page opening with the shared header shows its own
  warnings, in `app/` and in `oracle_app/` alike, with nothing to remember per
  page. The six open-coded loops in `app/views` are gone;
  `aero_coefficients.py` and `export_report.py` moved onto `page_header`
  (`banner=False`, so nothing but the warnings changed on them); the Design
  Speeds page keeps its deliberate re-statement of the one warning whose subject
  *is* its operational-limitations tab, now through an `only_codes=` filter.
- **Two `page` tags named pages that no longer existed.** `weight_cg_inertia`
  (the weights page has been `weight_mass` since Step G3) and `wing_geometry`
  (merged into `configuration_layout` at Step G1) covered **19 checks — 14 of
  them the weights group, the largest in the module** — and were reachable only
  because two views in `app/` compared against the old strings by hand. Every tag
  is now a `sloads.workflow.STEPS` key: `workflow.py` is the nav SSOT, so a tag
  naming anything else names a page no GUI has. Rule-3 drift guard
  (`tests/test_validation.py`) asserts it over both the `PAGE_*` constants and
  the tags the live checks actually emit across four fixtures, so a new check
  with a typo'd page fails there rather than rendering nowhere. Two oracle-GUI
  guards read the **rendered** warnings (`tests/test_oracle_gui.py`): the
  contradictory wing row shows on the page that owns it, and does *not* show on
  one that does not — targeting honoured, not ignored. Warnings tagged
  `export_report` stay main-GUI-only: the oracle GUI has no export page and no
  way to set a safety-factor override, so the guard permits a tag that is a
  workflow key without being an oracle step (OG-2 scope).
