## Derived-scalar consolidation — one owner per quantity, in the dataclasses (note 33, tier L, 2026-08-21)

**Why.** The 2026-08-20 review's CR-A-2 found ten quantities with two or more
independently editable copies and proposed the obvious remedy: teach the generic
renderer to read the registry's `is_owner`/`derived_from` and grey the copies out.
The owner asked the prior question instead — *why do we need the copies at all,
and can they be consolidated?* — and stated the preference plainly: changing
tests is acceptable and preferred to keeping confusing redundant variables. That
turned a display fix into a contract change, which is why it took a design note
(rule 1) rather than a patch.

**What the measurement found.** Three classes, not one. Seven copies were a
**cache of `Project.geometry`** — `io.py` already refused to write every one of
them, so `project.json` held each quantity exactly once and the duplication lived
only in the dataclass API, from where the field registry propagated it to both
GUIs. Three were genuine overrides. Two were entered twice with nothing
reconciling them at all. The remedy the review proposed would have decorated all
ten identically; the classes need different answers, and only the first is a
copy that can simply cease to exist.

**Three defects fell out of the measurement**, each an argument for removing the
copies rather than marking them. `landing._wing_area` preferred its slice copy and
fell back to geometry while `structural_speeds._wing_area_sqft` preferred geometry
and fell back to its slice — **opposite precedence for one quantity**, masked only
because the sync overwrote the landing copy first, and with no guard because a
guard cannot be written while two modules each own the answer. Note 32's decision
OG-7 promised that an entered scalar "wins and is marked"; nothing implemented the
*wins* half, so the oracle GUI was offering an entry the next run discarded — the
note amends OG-7 rather than building the override, which would need a stored flag
per scalar against OG-13. And the registry described `speeds.weight_lb` as a
read-through of MTOW with an override checkbox, a mechanism the calc never had;
its text now says what the code does.

**What shipped.** The ten fields are gone from `FlightLoadsInput`, `WingMassInput`
and `LandingInput`. Their values are resolved at the point of use through three
accessors — `require_wing_reference`, `wing_plane`, `gear_geometry` — and the
functions that could not look the parametric wing up because they receive a bare
`SurfaceInput` take the scalars as parameters, which is the shape
`air_load_distribution` had used all along. Two `_effective` helpers performing the
identical gear substitution (`landing` and `gear_loads` each had one) collapsed
into the single resolver. With the copies gone the fallbacks they provided become
explicit refusals naming the page that owns the input, which is what DS-3 asked
for: absent geometry is an error, not a silent zero propagating into a balance.

**No schema hop**, and this was checked rather than asserted: the shipped examples
carry none of the ten keys on disk, and save→reload→save is a fixed point before
and after, so `SCHEMA_VERSION` stays at 54 — the single largest reason the two
persisted duplicate pairs (`shoulder_altitude_ft`, `airplane_length_in`) were
deferred to their own item instead of being folded in behind a no-hop change.

**Guards, per rule 3.** DG-2 pins the surviving multi-copy quantities as a named
literal rather than a count, so one duplicate leaving cannot mask another
arriving. DG-3 has two halves: an AST guard that the wing strip integral happens
only in its owner and the two accessors allowed to name it — verified against a
deliberate violation, since a guard that cannot fail on its target is the trap
note 32 §8 already recorded — and a numeric check that the two modules keeping
their own area accessor return the same number on every fixture, which before
this change they could not be relied on to do. Every Appendix A oracle passes
unchanged; the refactor moved no equation, and DG-1 is what would have said
otherwise.

**Cost, against the estimate.** ~40 read sites across six modules and 14 test
construction sites, as the note predicted. Three things the note did not predict
and the implementation records in its §7: `wing_inertia_distribution` shed two
now-unused parameters once its second construction path was removed; a fixture
that deleted the wing planform to reach the carry-through fallback had to be
rewritten to make the *spar stations* underivable instead, which is the condition
that fallback actually tests; and one test's subject vanished rather than moved —
"the sync fills the derived slices" became "every resolver answers from the one
source", asserting the property the copies never had.
