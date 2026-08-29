## Step — LANDLOAD's `BETA` sign, and the figure that settled it (tier L, 2026-08-29, issue #133)

**Objective.** Adjudicate and correct the sign `LANDLOAD.BAS` carries in
`BETA(2)`/`BETA(3)`, which set both the ground-roll lever arms and the
airplane-datum resolution of every attitude-1 ground case — quantities that reach
the exported deck as ULTIMATE loads.

**Deliverables.** `beta = (gamma - gra1, -gra2, -gra3)` at `landing.py:229`, plus
the `ap[1]` call site that read the literal `gra2` rather than `beta[1]`.
Attitude 3's two compensating negations — `bp[2]` written longhand with a flipped
second term, and `PHIM(7–9) = −BETA(3)` — are removed as redundant, moving no
number and leaving the sign in one place. `cp[1]` stays on `+gra2`: it builds the
contact-patch line, and the figure confirms `CP` unchanged. The `ρ` pin is
flipped and renamed; the register entry supersedes the declined decision of
2026-08-15; `PROGRAM_SPEC`, `theory_sources` and `balanced_cases.md` §9.5 follow.

**Test.** `test_rho_is_minus_the_ground_angle_in_every_attitude` — `ρ == −GRA`
exactly, every case, every gear fixture, against `ground_angles` directly. The
p230 arm oracle re-pins to p235's figure (77.052 / 17.760 / 94.811, `CP` 42.981
unchanged); the p231/p232/p233 page locks gain a `_CORRECTED` table whose every
value is derived from Appendix A's own printed formulas with the single
substitution `BETA(2) = −GRA(2)`, never from the module under test — the two
agree to ~1e-5 relative. No lock removed; the printed cells stay transcribed as
the thing deviated from.

**Key decisions.** *The manual contradicts itself, and that is what made this
adjudicable.* Three sessions of frame reasoning had produced arguments on both
sides and two of them were wrong: a `DP`-as-wheelbase argument whose premise was
false (`DP` is axle-to-axle normal to the resultant, and the patch separation is
94.622, not the 94.811 it asserted), and a reading of the p232 force cells as
refuting the correction, withdrawn within the day because `LANDLOAD.BAS` computes
those cells *from* the angle they were taken to test. What settled it was not an
argument at all: Appendix A's construction figures. p234 states the rule the code
implements for one attitude out of three; p235 prints the braked-roll arms the
corrected sign produces, against the table its own program printed. **A printed
number overrules an argument only when it is independent of it** — the lesson the
withdrawn p232 reading paid for, and the reason the p235 figure counts where the
p232 cells did not.

The correction has an independent witness, which is why it can be believed
without the figure: the assembled ground case's pre-closure residual pitching
moment, measured against LANDLOAD's *own* printed unbalanced moments — a quantity
the fix does not touch. On `ga6_normal` case 13 it falls from **−757.1 to −0.7
lb-in** and `q̈` from −8.0e-5 to −7.4e-8. The wrong-signed lever arm was what
that residual had been reading all along; §1.8 had found it and read it as
evidence *against* the correction, because at that point only one of the two use
sites was being fixed.

*Fix at the origin, not the use sites.* The defect's whole shape was one value
read twice, with one attitude patched at both its readers and another at neither
— the signature of a sign fixed where it was noticed. Correcting `beta` and
deleting the compensations puts it in one place and makes the field comment
("resultant-to-FS angle") true for the first time.

*The enabler is retired.* `ground_rotation_deg` recovers `ρ` from each case's own
two resolutions, which is self-consistent by construction and structurally cannot
see a sign error; its docstring said so and treated that as a feature —
"never has to adjudicate a sign inconsistency that is in LANDLOAD.BAS itself".
Its own measured output had isolated attitude 2 for months (−4.0570 level,
−15.0003 tail down, +4.7253 ground roll). The absolute gate now sits upstream of
it, with its assumption stated: the nose-up sense of `GRA` is derived on tricycle
geometry, the only arrangement the suite models.
