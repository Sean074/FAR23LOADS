- **A condition that is not a load case no longer claims a safety factor
  (#154, design note 48, tier L, 2026-09-04).** Surface geometry, weights,
  centres of gravity, design speeds, Mach-limit lines and a dimensionless
  landing load factor carried `safety_factor = 1.5` from the dataclass default
  and printed it, so a table of areas and chord lengths was headed
  `[ULTIMATE, SF=1.5]`. `ConditionResult.safety_factor` is now `Optional[float]`
  and renders `N/A`; `safety_factors.prescribes_factor` is its single owner — a
  condition prescribes no factor exactly when it states no value in load units
  **and** carries no `case_ref`. Measured, that is 38 conditions on both shipped
  airframes. The `case_ref` clause is load-bearing: SELECT's six critical wing
  conditions publish no load value (their loads live on `WingLoadResult`) but
  are load cases whose bulk-data cards are factored, and blanking them would
  have printed `N/A` in the case index against a factored case. The governing
  table writes the `None` through `stamp()`, since `registry.run_all_modules`
  re-stamps every condition and a dataclass default alone would not have
  survived the shipped path. Nothing substitutes 1.0 silently: `_ult`, `_scale`,
  `GoverningTable.required_factor_for` and the report's `_required_sf` all raise
  on a load found inside a factorless condition.
