- **The printer that amplified the noise the package had already been taught to
  suppress (#147, tier M, 2026-08-29)** — Found running down a red fast gate on
  a **docs-only** commit: `test_imperial_output_matches_the_frozen_baseline`
  failed on the Linux 3.12 leg naming `concept_regional_jet`'s landing channels,
  and passed on macOS. `CONVENTIONS.md` §7 already carried the rule this
  violates — a byte in a deck or report must not depend on the libm build, FMA
  or the interpreter's `sum()` — with three owners: `picks.extreme` for keyed
  picks, `sbeam_bridge._fmt3` for card-component dust, and `math.fsum` at every
  summation. The human-channel formatter was never one of them, and it was the
  one place where an ulp of difference was not damped but *amplified*: its two
  branches are `str(int(value))` and `f"{value:.4g}"`, and the test between them
  was exact equality with the integer.
  The evidence that settled it needed no second platform. The shipped output
  already disagreed with itself: case 12 of `concept_regional_jet` prints the
  unbalanced yawing moment as `-687258` on the datum row and `-6.873e+05` on the
  body-frame row — the same load, one ulp apart, two precisions — and case 18
  prints the main drag reaction as `12768` on one row and `1.277e+04` on
  another. A sweep found 95 ulp-unstable cells in that one example's landing
  output alone. Landing is where it surfaced because landing is the trig-heavy
  path the #133/#134/#139 rotations built, and `sin`/`cos` are exactly where two
  libm builds part company.
  The fix is one line of quantization rather than a widened branch, because the
  quantity being made stable is *what the reader sees*: rounding to twelve
  significant figures first makes both branches read the same number, and the
  residual knife edge — a value within an ulp of a twelfth-digit boundary — is
  one no deliverable distinguishes. The guard is stated on real values, not
  invented ones (`test_no_printed_deliverable_cell_hangs_on_the_last_ulp` walks
  every value of every condition of the failing example's landing module under
  ±4 ulp, with a non-vacuity floor), and the row in §7 gains the formatter as an
  owner so the next printer added has somewhere to be listed. `tests/
  test_platform_stability.py`'s docstring had recorded the precedent a week
  earlier: 3.12's compensated `sum()` moved values "where a value sat on a print
  boundary" and the digest failed on the 3.12 leg only. That fix removed a
  source of noise; this one removes the amplifier, which is why the class is
  closed at the printer and not at the next quantity to land on an integer.
