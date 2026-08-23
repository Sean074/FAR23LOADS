- **The two quantities that were entered twice are entered once (schema v55;
  note 33 §8 / DS-7, issue #52, tier L, 2026-08-22).** `MachLimitInput` no
  longer stores a shoulder altitude — `speeds.shoulder_altitude_ft` is its one
  home and `mach_limit_lines(inp, mc, md, shoulder_altitude_ft)` takes it as an
  argument beside MC/MD, so the Mach-limit table's first row and the Mach
  numbers on it are at the same altitude by construction. SELECT's airplane
  length LF is one field, `geometry.empennage.airplane_length_in`
  (`derived_geometry.airplane_length_in`), read by both the 23.423(b) pitch
  inertia and the default IZZ; the per-tail copies are gone. Migration hop
  `54` reconciles a legacy file's pairs — the value that governed the shipped
  output wins (the MACHLIM altitude; the htail length), a zero/absent copy
  loses silently, and a real disagreement raises a warning naming both numbers,
  which the GUIs show as a toast on load (`app_shell.project_state.safe_load`)
  and the CLI on stderr. Each oracle page now renders one widget per quantity
  (DG-5 completed; `STILL_DUPLICATED` shrank to the two class-B overrides).
  Both `app/views/` pages lost their second widget (the freeze's one hop). No
  oracle moved: every shipped example agrees on both pairs and is folded in
  silently at load (examples stay on disk at their original version, as
  `test_cg_cases.py` requires).
