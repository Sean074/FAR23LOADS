- **CI red on every `main` run since step 12: platform-dependent bytes in the
  frozen Imperial digest and the 3.9 data dictionary (tier M, 2026-08-16).**
  Two classes, both invisible locally (macOS, Python 3.11) and red on the Linux
  matrix: (a) `select.py` picked critical cases with `max()`/`min()` over keys
  that tie *exactly* in exact arithmetic — `BAL A` at two altitudes carries the
  same VA — but land one ulp apart on another libm (and under 3.12's
  compensated `sum()`), so `atr42_100`'s SUDDEN RUDDER came from V-n 74 in CI
  and V-n 14 on the Mac; every keyed pick now goes through **`_extreme`**, first-
  in-order inside a `_TIE_REL` (1e-9 relative) band, which is exactly what
  `max` returned for a bit-exact tie, so no local pick moved. (b) FORCE/MOMENT
  components that are zero by construction printed their ~1e-14 cancellation
  residue (`6.101335E-15` here, `1.987480E-14` there) or `-0.000000E+00`;
  every vector card (FORCE, MOMENT, GRID, CONM2 offset — 26 sites across five
  exporters) now formats through **`sbeam_bridge._fmt3`**, which snaps a
  component below `_TOL ×` its own card's scale to `0.000000E+00` (the
  per-component form of `_closed`). Digest regenerated: every one of the 23,649
  changed lines is `-0` → `0` or dust → `0`, no load value moved. (c) With (a)
  and (b) in, the 3.12 leg alone still failed on `concept_regional_jet`: Python
  3.12 changed the built-in `sum()` of floats to compensated summation, so
  `resultant6`'s `sum(ld.fz …)` landed a few ulp from 3.9/3.11 and two values
  sat on print boundaries (an integer-valued residual `65013` vs `6.501e+04`;
  a FORCE card's 7th digit). **Every float summation in `sloads/` — 102 sites
  in 20 files — is now `math.fsum`**, exactly rounded and therefore identical
  on every interpreter and platform; the digest moved by 20 lines, all
  last-digit, and every oracle/closure pin passed unmodified. Also
  `docs/generate_data_dict.py` drops the `"An enumeration."` placeholder that
  Python ≤ 3.10's `EnumMeta` stamps into a docstring-less enum's own `__dict__`
  (the 3.9-only `DATA_DICTIONARY.md is stale` failure). New guards
  `tests/test_select.py::test_extreme_pick_is_first_in_order_across_a_platform_ulp_tie`,
  `tests/test_sbeam_bridge.py::test_card_components_snap_dust_and_negative_zero`
  and `tests/test_platform_stability.py::test_every_float_summation_in_sloads_is_fsum`
  (all grep for bypasses); `CONVENTIONS.md` §7 gains the row.
