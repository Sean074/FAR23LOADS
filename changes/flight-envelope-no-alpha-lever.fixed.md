- **A lift polynomial with no alpha lever is refused by name, not iterated into
  an opaque solver failure (#144, tier M, 2026-08-29).**
  `flight_envelope.balance_configs` — the choke point `build_envelope` and
  `trim_sweep` share — now refuses a coefficient set whose lift polynomial has
  no alpha term (`C1..C4` all zero), naming the set and the fix, beside the #81
  stall-CL, weightless-CG and tail-CP-at-datum refusals. The inner balance moves
  alpha until NZ lands in its ±0.005 band; with no alpha term CL (and with it
  LZ, MM and the tail load) is the same number at every alpha, so no trip can
  answer differently and the loop exhausted 400 of them, reporting "reached
  NZ=0 at alpha=41.3861 deg" — a solver failure naming no input, on a page that
  had been working a moment earlier. `AeroCoefficientsInput.normalize` fills a
  blank set's `stall_cl` from `clmax_flap`, so the #81 guard did not catch it.
  Only lift is guarded: an all-zero drag or moment polynomial is a legitimate
  entry, an all-zero lift polynomial says the set carries no airplane.
