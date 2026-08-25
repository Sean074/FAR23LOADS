- **The stall fill gets a second caller, and the balance gets a refusal (issue
  #81, C210-23, tier M, 2026-08-24)** — The M1-1b fill that keeps the CLmax trio
  and the per-config stall CLs consistent was written into `__post_init__`, which
  is the right place for a slice that is built in one go and no place at all for
  one that is assembled field by field. The oracle GUI does the latter: it seeds
  the coefficient sets blank and writes the CLmax trio afterwards, a widget per
  rerun, so the constructor never ran a second time, the live sets kept a stall CL
  of zero, and both Flight Envelope and SELECT died on a division by it. The
  workaround that kept the C210 build moving — save, reload — is the tell: the
  loader constructs, so the file was always right and only the session was wrong.
  The fix needed no new call site. `sloads.derived` already existed for the
  neighbouring problem (a derived slice whose only writer was one GUI, #62/PB-1)
  and the oracle form already calls `refresh_derived` after every persist, so the
  fill was extracted to `AeroCoefficientsInput.normalize` and registered there;
  what the module gained was a second table, because a *derived* slice and a
  *normalized* one are not the same thing — the first is a result the project
  could rebuild from scratch and the field registry excludes from the input set,
  the second is authored input whose fields fill each other in, and letting
  `aero_coeffs` into the first would have put user input under the G5 reduction's
  drop-and-re-derive. Beside the fill, the balance now refuses: `balance_configs`,
  the choke point `build_envelope` and `trim_sweep` share, names the set, the
  quantity and the page rather than letting a stall speed divide by zero — the
  #84 lesson, that a condition the airplane has not stated is refused rather than
  computed, applied one layer down. The sweep item that came with the issue could
  not be closed as it was written. `flaps_down.neg_stall_cl` is not a fill that
  was forgotten; it has no source to fill from, since the schema carries no
  `clmax_flap_neg` and the clean negative CLmax is a different number — Appendix
  A's landing set prints −0.41 against a clean −0.59, so the obvious fill would
  have injected a 44 % error into the flaps-extended negative band. Left at zero
  it does not crash but clamps that band at CL = 0, which the balance reports as
  a quietly small load, so it is now a validation warning and the schema field
  that would let it fill symmetrically is filed as its own item.
