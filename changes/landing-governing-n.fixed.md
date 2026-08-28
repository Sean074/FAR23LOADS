- **The landing load factor is entered as N, not NLG — the wing lift factor moves the gear
  reaction again (note 37, #123, tier L, schema v57, 2026-08-27).** `LandingInput.gear_load_factor`
  (an NLG override with a `0.0` sentinel) is replaced by the optional governing
  `airplane_load_factor` N; `NLG = N − L` is derived by the one owner
  `landing.governing_load_factors` and never entered. The old override made `L` inert on the
  vertical reaction (`VMP = ½·NLG·W·AP/DP` read NLG and nothing else) while the page reported
  the energy-derived N the reactions were *not* computed from. The 56→57 hop is semantic
  (`N = NLG_old + L`) and reproduces every NLG the reaction path read — no load number moves;
  the only moved fleet numbers are the three concept fixtures deliberately nudged to
  `N = 2.67` (LF-10, +0.15 % on NLG, clearing the 23.473(g) floor). `ga6_normal` and
  `cessna_210` now carry the manual's rounded design point as an explicit `N = 3.167`. The
  `L ≤ 0.667` cap is removed (FAR 25.473(a)(2) permits 1.0; both GUIs caption the FAR defaults
  as guidance via one shared string); `N ≤ L` is refused by name; the 23.473(g) floors
  (`N ≥ 2.67`, `NLG ≥ 2.0`, one policy owner `landing.far23_473g_floor_violations`) **block**
  in a FAR 23 category and **warn** in concept. Both GUIs seed N from the computed energy
  value with a way back to computed, render NLG as a derived output, and caution when the
  entered N sits below the energy value (`cessna_210` trips it: 3.1670 vs 3.3885). The
  LGFACTOR condition now reports the governing pair beside the oracle-locked energy rows, so
  the landing deliverable channels and the three concept examples' balance/deck digests are
  deliberately regenerated.
