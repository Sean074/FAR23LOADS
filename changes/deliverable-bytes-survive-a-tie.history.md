- **Deliverable bytes survive a rounding tie (tier M, 2026-09-06)** — the Linux
  CI leg had been red since `2d263f1` (note 49's LIMIT sweep), failing the frozen
  Imperial digest on one channel of one fixture while the full local gate stayed
  green. The cause was not note 49: `export.sbeam_bridge._fmt` prints seven
  significant digits of quantities that reproduce across platforms only to about
  twelve, so any value landing on the decimal rounding tie of its seventh digit
  resolves round-half-even off bits that x86 and ARM do not agree on. Note 49
  moved values onto ties; the fragility was always there, and measurement showed
  **all six shipped examples exposed** (248 tie-fragile values of 159,407 emitted,
  concept_regional_jet worst at 80) with only one having flipped so far. The
  human channel had already met this class at #147 and answered it by quantizing
  to twelve significant figures before formatting; the solver channel never
  inherited that rule. Rather than copy it, the quantization became one owner —
  `units.canonical` — that `report.render.format_value` and
  `export.sbeam_bridge._fmt` both read, recorded as clause (e) of
  `CONVENTIONS.md` §7's platform-stable-bytes row beside the (d) it generalises.
  Cost: 36 emitted lines moved across 4 of 330 digest channels, each a single
  seventh-place digit. One of them was a defect in a delivered artifact rather
  than a CI colour — `atr42_100`'s gear report stated the same load as
  `2.448331E+04` in its *Ground-line V* column and `2.448330E+04` in its *Datum
  Fz* column on the same row, the two straddling the tie from opposite sides.
  The guard is the population rather than a sample: every value every deck emits,
  on all six examples, invariant under ±3 ulp, so the next emitter that formats a
  solved scalar by hand fails the day it is written — verified by reverting the
  fix and watching it fail.
