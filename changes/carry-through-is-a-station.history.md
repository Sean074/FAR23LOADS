## Step — The wing carry-through is entered as a fuselage station (design note 50, tier L, 2026-09-05)

**Objective.** Discharge design note 44 §13's **OR-97** finding — that every
wing-attach fitting load the oracle technical report can print is derived from
*assumed* spar stations — by making the station enterable, rather than by
stating the assumption more loudly. OR-97 called the exposure structural, and it
was: `front_spar_pct`/`rear_spar_pct` were `Origin.SLOADS` and unmarked, so the
oracle GUI never offered them and `reduce_to_oracle_inputs` stripped them,
which meant no project the report could be built from could carry a real
carry-through whatever it held on disk.

**Deliverables.** `SurfaceInput.front_spar_x_in`/`.rear_spar_x_in` replace the
chord-fraction pair (**schema v60 → v61**); `derived_geometry.carry_through`
reads the entered stations and falls back to the new
`derived_geometry.default_spar_station`, the one owner of the
`x_LE(root) + pct × c_root` estimator; `constants.DEFAULT_FRONT_SPAR_PCT` /
`_REAR_SPAR_PCT` move 0.15/0.65 → 0.20/0.60 and are re-cast as that estimator;
the two registry rows carry `governs=True` + `supplied=True` with an
`EXTERNAL_VALUES` resolver, which makes the pair a note 36 collapsed override
(blank derives, typed overrides) and puts it inside the oracle input set; the
geometry page renders the stations in the display system's length units with the
derivation captioned; `units.py` classifies them as lengths, where the fractions
they replaced were dimensionless; `migrations._hop_60` converts an entered
fraction to the station its own polylines describe; `report/content.py` echoes
only an *entered* station; the LRA export's assumed-joint note names the new
field. `PROGRAM_SPEC`, `theory_sources`, `ORACLE_REPORT` §7, the data dictionary
and the generated guide follow; the seven bundled examples are re-stamped at v61.

**Test.** Five gates. **G-OR-75/G-OR-77** — an entered station survives
`reduce_to_oracle_inputs` and `assumed` is False through the projection, with
the blank case asserted in the same test so promotion in either direction fails
(`test_oracle_inputs.py`; this is OR-97's own experiment kept as a gate and run
the other way round). **G-OR-76** — the G5 demonstration earning the `supplied`
mark: entering 70/100 in on `ga6_normal` moves the front fitting load by more
than 1 lb, so the mark is not speculative. **G-OR-78**'s other half —
`test_the_estimator_has_one_owner` pins that the caption's number and the
analysis's number come from the same function, which is what stops the page
describing a station nothing uses. **G-OR-79** — the hop converts an entered
0.18/0.62 to that airplane's own stations and the loaded project resolves the
pre-hop carry-through exactly; a `null` file hops to `null`; a degenerate
planform yields `null` rather than a station off a chord that does not exist.
The Imperial baseline is regenerated: 23 of 330 digests move, all in the body
channels, which is the default change and nothing else.

**Key decisions.** *A percentage could never have held the answer.* The datum is
measured at the fuselage; the fraction is taken on the centreline root chord, and
on a swept or cranked wing the two are different stations that no value of the
fraction reconciles. %MAC was put up as an alternative unit and measured out:
`ga6_normal`'s MAC leading edge sits 18.6 in aft of its root leading edge, so
20 % root chord is **2.28 %MAC** there against 18.57 % on `baron_58` and 12.64 %
on `cessna_210` — not a unit conversion but a different quantity — and `MAC`/
`XLEMAC` are themselves derived from the polylines, so a station stored that way
would migrate whenever anyone refined the wing outline. *The percentages left
rather than staying beside the station*: two stored fields for one quantity with
only one of them rendered is the duplicate-owner shape this project removes, and
because the replacement is computable from the same file the hop could convert
instead of dropping — the first live hop that is not an identity. Its first
draft was **not idempotent**, and `project_from_dict` re-runs `migrate`, so the
second pass wrote the freshly converted station back to `None`; the guard is now
that an entered fraction converts and wins while the key is otherwise only
created, never overwritten. *Note 44 §14 is superseded whole* — its OR-103
(mark the fractions), OR-105 (store them as percent) and OR-106 (blank widget)
answered a question this note removes; **OR-107 stands**, the change touching no
file frozen by OR-13, so no OR-15 admission was needed. OR-105's premise is
corrected on the way past: the spar pair were not the only `_pct` leaves holding
a fraction — `ref_axis_pct` is a third, filed rather than swept because the
two-front-end trap OR-105 named cannot reach a field the oracle GUI never
offers. The owner's related proposal — publishing the fuselage as two
cantilevers off the carry-through, with the between-spar VMT withdrawn — is
**not** in this step: it edits the frozen `body_loads.py` and gets its own note,
with its measurements parked in note 50 §7.
