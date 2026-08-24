- **The flap page says when it skips the 23.457(b) slipstream case, instead of
  printing a quietly understated load (C210-40, issue #83, tier S, 2026-08-24).**
  `flap.py` computes the propeller-slipstream term only when the engine record
  supplies both a power and a propeller diameter. With no such record the Flap
  Loads page still collects the slipstream band's geometry (AF, BLPROP), reads it
  for nothing, and prints a critical flap load with a first-order amplification
  absent and no trace — the manual's own example prints ×1.407 (Ref 1 Appendix A
  p201). Since #85 that is not a factor left unprinted but a **delivered case
  that does not exist**, so the flap and its attachments are sized on the
  gust-combined load alone. A `consistency_warnings` entry
  (`flap_slipstream_skipped`, tagged `flap_loads`) now names the skip, what is
  missing from the engine record, and the page that fixes it; AF and BLPROP
  caption their engine-record dependency in both GUIs (the main GUI through
  `help=`, the oracle GUI through the field registry's basis string).
- **The predicate is the module's own skip condition, not a copy of it.**
  `flap.slipstream_is_available(project)` states `maxhp > 0 and pdia_in > 0`
  once; `validation` reads it, and a test walks the partial records — power with
  no propeller, a propeller with no power — asserting the warning fires *exactly*
  when `_compute` skips the term, so the two cannot drift.
- **It fires on the entered band, not on the absent engine.** `EngineType` has
  no jet member, so `concept_regional_jet`'s turbofans are stored as TURBOPROP
  with a zero propeller diameter and are indistinguishable from an unentered
  piston record by type alone. Keying on AF/BLPROP — the evidence a slipstream
  was intended — keeps the check silent on jets and gliders and true to the
  module's "no warnings on well-formed input" contract; the schema gap is filed
  separately. The residual is stated rather than hidden: an airplane that enters
  neither AF nor BLPROP and has no engine still gets the understated load
  unwarned.
- **The main GUI's flap page joined the shared header, so this is not an
  oracle-GUI-only warning.** `app/views/flap_loads.py` opened with a bare
  `st.title`, which #82's renderer (hung off `page_header`) never reaches — the
  warning would have appeared in one GUI and not the other, the exact divergence
  #82 was written to end. It now calls `page_header("flap_loads", banner=False)`,
  so nothing but the warnings changed on it. Guards read the **rendered**
  warning in both front-ends (`tests/test_views_smoke.py`,
  `tests/test_oracle_gui.py`), and the GA fixture asserts silence where the
  slipstream *is* computed.
- **Rule-4 sweep (defect class: an upstream record's absence silently degrading a
  delivered number).** Every other conditional skip in `sloads/modules` was
  checked and none is this defect: `configuration._stability_condition` /
  `_gear_geometry` / `wing_geometry._engine_stations` return `None` and the whole
  block is visibly absent; `configuration`'s prop-clearance omits its one
  `LoadValue`; `weight_estimate.resolve_max_continuous_hp` falls back to the
  stored figure with the fallback named in its docstring; `balance`'s hub thrust
  applies nothing from `None` and says so. The flap slipstream was the only site
  where the number kept printing while quietly losing a term.
