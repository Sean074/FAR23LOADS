- **SELECT's search scope stated explicitly in the theory sources (review 2026-08-23
  C210-26, tier S, 2026-08-23).** The `select` row of
  `docs/20_theory/00_theory_sources.md` now opens with the scope the criteria always
  implied but no doc stated in one place: the candidate pool for every selection —
  wing, h-tail, v-tail and fuselage alike — is the entire balanced V-n matrix (every
  loading/CG × altitude combination FLTLOADS balanced), filtered only by condition
  label, with one governing case per category proceeding to the distributed-loads
  pass; 23.333(b)'s "each combination" requirement is discharged by FLTLOADS' full
  matrix, and the airload-side-criteria method limit (wing inertia relief not in the
  selection criterion) is recorded beside it. Docs only; the GUI-caption half stays
  with #73.
