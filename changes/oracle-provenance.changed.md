- **An oracle cell says where its number came from, and a gate may not re-derive
  the rule it checks (#146, tier S, 2026-08-29).** The three worst defects the
  0.8.0 cut shipped share one mechanism rather than any error of physics — *the
  oracle silently shrank*: an illegible column was recorded as a missing oracle
  when it was an OCR failure over a legible page (#133), a fixture weight was
  back-solved from a mis-OCR'd cell and then used to check that cell (#137), and
  a gate moved the applied load from the tyre to the axle *inside the test*
  before comparing (#139). "An oracle test exists, ±0.1 %" is binary where two
  further facts decide whether the test can fail. `00_theory_sources.md` gains an
  **Oracle provenance and gate independence** section stating both as rules —
  **P-1**, every cell states *transcription* / *OCR extraction* / *absent — not
  printed* / *absent — illegible* / *back-solved*, with a back-solved value
  disqualified as the oracle for anything downstream of what it was solved from;
  and **P-2**, promoted from design note 39's G-AP-2, *two copies of one rule
  cannot disagree* — and `CODE_REVIEW_PROCESS.md` Step 3 gains both as checklist
  items. With them, the bounded sweep the rules exist to make possible: every
  family with no printed oracle, classified by whether its gate has a witness
  independent of the code. `one_engine_out` is the exposed one — its gate reads
  the `ONENGOUT.BAS` listing the port was written from, so a change to it is
  unguarded until the Appendix B twin is in hand — and the `configuration` /
  `vn_diagram` / `validation` / airspeed closures are named as not-a-load and
  ranked accordingly. Nothing in the sweep is a defect; it is the statement the
  citations were missing. The "partially oracle-locked where the scan is
  OCR-garbled" bullet in the canonical oracle-status list, stale since LANDLOAD's
  three pages were transcribed, goes with it.
