- **The guide's landing chapter describes the 0.8.1 landing output (tier S, 2026-08-29).**
  `docs/60_guide` had zero diff across v0.8.0..v0.8.1 while the landing
  deliverable was rebuilt underneath it: chapter 14's *Results on this page*
  still described the primed-only output — no body-frame three-wheel
  deliverable, no axle-vs-contact-point split, no statement of which frame the
  CSV is in, and no NR/NV/ND or fuselage-axis angle. It now describes what the
  page ships: the two frames and which one is delivered, the three wheels on
  every case with the force, the point it acts at and the reference node it is
  transferred to, the datum load factors and unbalanced moments, and the two
  approved p232 deviations a reader cross-checking against the book will meet
  (citing the register, not the development trail). Two new *Common mistakes*
  cover reading one frame's numbers as the other's and taking a reference node
  for a point of application.

  The guide's `03_conventions.md` gains the frame statement
  the chapter leans on — airplane datum as the delivered frame, ground line as
  the manual's analysis view, the rotation between them, and the point of
  application — plus the `Frame` and `Applied at` columns in the results-table
  and CSV sections, and the one place the text download carries more than the
  CSV.
