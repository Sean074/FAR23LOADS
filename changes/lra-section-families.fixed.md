- **LRA deck: one `PBAR`/`MAT1` pair per section family, editable in place
  (backlog Pri 7 / #7 — step 14 descoped, tier S, 2026-08-17).** The LRA
  model wrote a single placeholder pair that every `CBAR` referenced; a
  sizing tool with real sections had nowhere to put them. The deck now
  carries four pairs — `wing` / `fuselage` / `htail` / `vtail`
  (`lra_model.SECTION_FAMILIES`, `MID = PID` 1–4, each tagged
  `$ SLOADS-SECTION <family>`), the left wing sharing the right's and the
  fwd/aft fuselage chains one — with **identical placeholder values** in all
  four (a different default per family would be invented stiffness and would
  move the indeterminate paths for no reason), and every `CBAR` carries its
  family's PID. Decision of record (user, 2026-08-17): **no input path** —
  not the review's "consumer-supplied" sidecar/schema, because section
  properties are the sizing half's output (scope review §2.3), so the seam is
  the deck a sizing tool edits, not `sloads`' schema; the 0.6.0 freeze holds
  at v53. `STIFFNESS_NOTE` rewritten to say which cards to overwrite. Solved
  results unchanged (same numbers, new IDs); guard
  `test_lra_model.py::test_every_cbar_references_its_family_section_and_the_four_pairs_are_identical`;
  round-trip leg still solves; Imperial digest regenerated on `sbeam/lra_model`
  for the four fixtures that export one.
