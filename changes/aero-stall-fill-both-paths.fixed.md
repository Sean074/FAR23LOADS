- **The stall-CL fill runs for the GUI that builds a slice field by field, and a
  zero stall CL is refused instead of divided by (C210-23, issue #81, tier M,
  2026-08-24).** The M1-1b fill lived in `AeroCoefficientsInput.__post_init__`,
  which runs when a slice is *constructed*. The oracle GUI never constructs one:
  it creates the coefficient sets blank and writes the CLmax trio afterwards, one
  widget per rerun. So the live sets kept `stall_cl = 0.0`, and Flight Envelope
  and SELECT — where every stall speed is `√(n·W/(CL·S))` — died with "cannot run
  yet — float division by zero" on a from-blank build, which is precisely the
  session the exercise exists to test. Saving and reloading fixed it, because the
  loader constructs. Same shape as C210-4: an invariant enforced in one code path
  and bypassed by another.
- **One owner, called from both paths.** `AeroCoefficientsInput.normalize()`
  holds the fill (fill-if-missing, both directions, never overwriting an authored
  value — ga6's `clmax_clean` 1.4068 and per-config `stall_cl` 1.41 legitimately
  differ and must both survive). `__post_init__` calls it for every slice built
  in one go, including the main GUI's Apply, which rebuilds the whole slice and
  was never affected. `sloads.derived.NORMALIZED_SLICES` calls it for a slice
  assembled field by field, through the `refresh_derived` the oracle form already
  runs after every persist — so the fix needed no new call site in the GUI, and
  none of the OG-2/G2 page-key problem that comes with adding one. `normalize`
  returns whether it wrote and is idempotent by value, which is what lets a
  render pass call it without dirtying a project it only visited (M2-3).
- **A derived slice and a normalized slice are different things, and the tables
  say so.** `DERIVED_SLICES` holds *results* the project could rebuild from
  scratch and which the field registry excludes from the input set (`mass`);
  `NORMALIZED_SLICES` holds authored *input* made self-consistent
  (`aero_coeffs`). Guarded both ways in `tests/test_derived.py`, so an input slice
  cannot drift into the G5 reduction's drop-and-re-derive path.
- **The consumer refuses rather than dividing (the #84 lesson).**
  `balance_configs` — the choke point `build_envelope` and `trim_sweep` share —
  now raises `MissingInputError` naming the set, the quantity and the page it is
  entered on, in the shape STRSPEED already uses for the same missing input. The
  fill is what keeps this from firing; the refusal is what makes every future
  writer safe, including one that bypasses `refresh_derived`.
- **Rule-4 sweep, and where it stops.** The other two `__post_init__`
  normalizations in `inputs.py` (`speeds.category`, `gear.strut`) are
  constrained-choice fields rendered as selectors, so no GUI edit can defeat
  them. The mirror-image case — CLmax entered per-config but not at the top level
  — was already refused by name in STRSPEED (`_stall_speeds`). **The sweep item in
  the issue cannot be closed as written**: `flaps_down.neg_stall_cl` is not a
  forgotten fill but a field with **no source** — there is no `clmax_flap_neg`,
  and the clean value is a different number (Appendix A's landing set prints
  −0.41 against a clean −0.59, so filling from clean would inject a 44 % error).
  Left at 0 it does not crash; `_balanced_point` clamps the band to
  `[0, +CLmax]`, so the 0-g point and the down gust at VF come back quietly
  small. Now warned (`aero_flap_neg_stall_unset`, page `aero_coefficients`)
  rather than guessed at; the schema field that would let it fill symmetrically
  is filed separately, being a schema/contract change.
- **Guarded on the real path**, not a stand-in for it:
  `tests/test_oracle_gui.py::test_the_aero_page_fills_the_stall_cl_it_was_given_field_by_field`
  renders the actual page with the actual broken live slice and then requires
  `build_envelope` to run — the reported symptom, gone without a save-and-reload.
  Note that no shipped fixture carries a `flaps_down` set at all, so nothing in
  CI exercises the flap envelope today.
