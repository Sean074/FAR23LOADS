# The factor is stated, never applied — closing OR-86's endpoint

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: AGREED, 2026-09-04 (owner).** E-a … E-f, including the two
sub-questions E-a′ and E-c′, were ruled in session; **OR-87 … OR-93**. §5 is
written against the rulings as taken. Milestone **0.8.3**. Closure tier **L**:
it rewrites `CONVENTIONS.md` §3 and `ORACLE_REPORT.md` §3.3/§8. The Phase C
mission sentence in `CLAUDE.md` is **unchanged** — OR-87 is what preserves it.

Design note 48 (0.8.2, shipped) split the render boundary into two channels and
took the module-analysis half: the CLI and the app render LIMIT, ULTIMATE stays
the channel of case selection, the export deck and the oracle technical report.
**OR-86** recorded the owner's principle — *the factor is stated, never
applied* — and deliberately deferred the rest here, because extending it past
the module views changes what the project calls its deliverable, and that is a
mission decision rather than a channel decision.

This note is that decision. It also carries OR-81's marker sweep and the
frozen-file work the 0.8.2 freeze was blocking (`tests/test_frozen_set.py`
deletes itself at the milestone cut, so 0.8.3 opens with an unfrozen tree).

Sources reviewed: `sloads/export/` (`balanced_deck.py`, `lra_import.py`,
`lra_model.py`, `sbeam_bridge.py` — `_sf`, `_SF`, `_sf_str`),
`sloads/report/render.py` (`LoadChannel`, `_ult`, `_ult_units`, `_ULT_UNITS`),
`sloads/safety_factors.py`, `docs/10_standard/CONVENTIONS.md` §3,
`SUMMARY_REPORT.md` §2/§4, `ORACLE_REPORT.md` §3.3/§8,
`PROGRAM_SPEC.md` (M4-15), `GUI_design.md` §6,
`tests/test_sbeam_roundtrip.py`, `tests/test_export_equilibrium.py`,
`tests/test_frozen_set.py`, and design note 48 throughout.

---

## 1. What is left, measured

Four sites still multiply, all in `sloads/export/`:

| Site | What it scales |
|---|---|
| `sbeam_bridge.py:825` | the applied-load CSV rows (`load.safety_factor`) |
| `balanced_deck.py:383` | every `FORCE`/`MOMENT` card of the balanced full-span deck |
| `lra_import.py:248` | loads transferred to the loads reference axis |
| `lra_model.py:820` | the LRA beam model's own load set |

plus `sbeam_bridge._sf` / `_SF` / `_sf_str`, which are the accessors those four
read, and the report side — `oracle_sections._load_cell` and
`render._ult` — still ULTIMATE under note 48's OR-78.

Three standard documents state the current contract in SHALL form and would
have to change with it: `CONVENTIONS.md` §3, `SUMMARY_REPORT.md` §2 (*"Every
load figure in the report SHALL be ULTIMATE"*) and `ORACLE_REPORT.md` §3.3
(*"Every load in section 3 and its appendix is ULTIMATE and marked"*, with two
conformance rows in §8).

---

## 2. The question this note exists to settle

**The deck is not a view. It is an input to a sizing program.**

Every other surface note 48 moved is read by a person, who can act on a stated
factor. The sbeam deck is read by sbeam, and the mission is explicit about what
happens next: *"a demonstrated **concept-loads → sbeam sizing loop**"*. A sizing
run compares the loads it is given against material allowables. Ultimate loads
pair with ultimate allowables; that pairing is the entire content of 14 CFR
23.303. Hand sbeam limit loads with no factor applied and nothing downstream
applies one, and the sizing is wrong by 1.5 — silently, and in the
unconservative direction.

Nothing in the repo would catch it. The round-trip gate
(`tests/test_sbeam_roundtrip.py`) checks *equilibrium*: it compares a
solver-recovered internal load against the NETLOADS quadrature. Equilibrium is
scale-invariant, so both sides move together and the gate stays green whatever
the factor is. The same is true of `test_export_equilibrium`'s card-sum check
and of the `sum(dFz) == sf × root` closure invariant, which merely becomes
`sum(dFz) == root`. **Every existing gate passes either way.** That is precisely
why this needs deciding in a design note rather than discovering in a diff.

So the principle divides cleanly along a line that is not the one OR-86 drew:

* **A surface a person reads** should state the factor and not apply it. The
  reader knows what 23.303 is for and can apply it knowingly, per case,
  including the cases where the factor is not 1.5.
* **A machine input whose consumer has no way to learn the factor** must carry
  loads the consumer can use directly, or the factor is lost.

The current rule — *applied exactly once, at the render/export boundary* — is
the second bullet already correctly implemented. Note 48 removed the render
half, which was the half that never should have had it.

---

## 3. Decisions put to the owner

Each carries a recommendation. Nothing is implemented until these are ruled.

### E-a — Does the sbeam deck stop applying the factor? — **RULED 2026-09-04 (owner): no, the deck stays ULTIMATE**

*Recommendation:* **No — the deck stays ULTIMATE**, and OR-86's endpoint is
declared reached when every *human-readable* surface states rather than applies.
The four export sites keep their multiply; `CONVENTIONS.md` §3 is rewritten to
say the factor is applied **once, at the export boundary only**, which is a
narrowing of today's rule rather than its removal, and is exactly what the code
will then do. The Phase C mission sentence needs no change.

This is a recommendation against the literal reading of OR-86, and I would
rather say so here than implement it and let the consequence surface in a sizing
run. If it is overruled, §3.1 below states what else must then be true.

**Ruled as recommended, 2026-09-04.** → **OR-87**. The four `sloads/export/`
multiply sites keep their factor; `CONVENTIONS.md` §3 narrows from *"applied
once at the render/export boundary"* to *"applied once, at the **export**
boundary"*, which is what the code will then do; `CLAUDE.md`'s Phase C mission
sentence is unchanged. OR-86's endpoint is reached when every human-readable
surface states rather than applies — which, after E-c, it does.

**E-a′ is moot** and is kept below as the record of what was weighed.

### E-a′ — If the deck does go LIMIT, what must come with it *(moot under OR-87; kept as the record)*

Not a separate decision — the obligations that attach to overruling E-a, listed
so the choice is made with them in view:

1. **A consumer must apply the factor, demonstrably.** Either sbeam is
   configured with a load factor per subcase (needs checking — I have not found
   that it can be), or the sizing step in the loop applies it, or the loop is
   documented as producing limit-load sizing, which is not the mission.
2. **A new gate**, since no existing one can see the difference: the deck's
   `FORCE` resultant compared against `nz × W` *without* the factor, so the
   assertion pins the basis rather than only the balance.
3. **The already-ultimate cases still cannot be scaled** (E-b), so the deck
   carries two bases at once and must mark which per subcase.
4. `CLAUDE.md`'s mission sentence and `SUMMARY_REPORT.md` §2 are rewritten.

### E-b — How an already-ultimate case is marked when nothing is applied — **RULED 2026-09-04 (owner): invert the marker**

`engine_ultimate` (23.367(a)(2)) and `emergency` (23.561(b), the 9 g inertia
factors) are computed already ultimate, at SF = 1.0. Under OR-81 LIMIT is the
unmarked default, so these are the "unless specified".

*Recommendation:* the `-ULT` marker **inverts** — it survives on exactly these
cases and nowhere else, in the units string and in the `SF=1.0` statement, and
becomes rare enough to be conspicuous, which is what a marker is for.
`ultimate_units` therefore survives too, driven by the case's factor rather than
by a channel — `sf == 1.0` marks, anything else on a human surface is plain.
The governing table already owns that number, so no new authority appears, and
**G-OR-51** pins it in both directions across every fixture.

**Ruled as recommended, 2026-09-04.** → **OR-88**. Carries with it a wording
change, not a logic one: `SF=1.0` reads *"no further factor is applied"* on an
ULTIMATE surface and must read *"this load is already ultimate; apply
nothing"* on a LIMIT one — same fact, opposite framing, in
`safety_factors.FAMILIES`' basis strings and in the render banner. The
alternative weighed and rejected was a distinct word in a `Basis` column, which
would reintroduce for two families exactly the per-artifact marker vocabulary
OR-81 retires.

### E-c — Does the oracle technical report go LIMIT? — **RULED 2026-09-04 (owner): LIMIT, factor stated per case**

The report is where the argument for LIMIT is strongest, and note 48 recorded
the reason in §2.4: **Appendix A is a limit-load oracle**, the oracle tests
compare at calc level and never cross the render boundary, so §3's tables print
1.5× the manual's figures and nothing catches it. The report's whole purpose is
to be read against p131.

*Recommendation:* **LIMIT**, with each case's factor stated in its `SF` column
and a basis line per section. Section 2 is unaffected — it states no loads,
which is already its own SHALL and its own conformance row. Under OR-88 the
already-ultimate cases keep their `-ULT`, so §3's 23.367(a)(2) engine cases stay
distinguishable. → **OR-89**, **ruled as recommended, 2026-09-04.**

The gap this closes is a defect, not a preference: the oracle tests compare at
calc level and never cross the render boundary, so §3 prints 1.5× Appendix A's
figures, the oracle suite passes, and nothing notices — the same class of blind
spot as the scale-invariant deck gates in §2.

Changes with it: `ORACLE_REPORT.md` §3.3's SHALL and its two §8 conformance
rows; `oracle_sections._load_cell` and `_required_sf` (added in 0.8.2 as the
ULTIMATE-only path); and every §3 wing-load table and Appendix B figure changes
value, which is why this belongs at the **top** of 0.8.3 — the report is re-read
once, against the manual, with both finally on one basis.

### E-c′ — Does the summary report move with it? — **RULED 2026-09-04 (owner): no, it stays ULTIMATE**

Put separately rather than assumed, because the two documents have different
readers. `SUMMARY_REPORT.md` §2 carries its own SHALL (*"Every load figure in
the report SHALL be ULTIMATE"*) and §1 writes the basis into the document's
stated job: the reader must *"read every governing ULTIMATE load, with its
safety factor, and know **where**"*. It also ships **inside the export bundle**,
beside the deck, as the controlling document for what a sizing engineer
receives.

That is the inverse of E-c. The technical report exists to be read against
Appendix A, a limit oracle; the summary report exists to travel with the deck,
and after OR-87 the deck is ULTIMATE. A bundle whose `_summary_report.pdf`
states limit loads beside `.bdf` files carrying ultimate ones is the F-R1 class
across the two files a recipient is most likely to read together.

**Ruled as recommended.** → **OR-93**. The export bundle is therefore consistent
*by audience*, and nothing in it moves: deck and summary report ULTIMATE, the
per-module transcript and CSVs LIMIT with their basis stamped in-band (OR-79 /
OR-80, shipped in 0.8.2), `METHODS.txt` naming both.

Accepted cost: the project ends 0.8.3 with two reports on two bases. Each is on
the basis its own reader needs and each states which — the alternative would put
limit loads in the one document whose job is to accompany ultimate bulk data.


**Recorded risk.** A technical report is closer to a certification artifact than
an app page, and a reader lifting a §3 number for sizing now lifts a limit load.
The mitigation is the one every LIMIT surface uses — the `SF` column and the
basis line — but this is the surface where that carries the most weight, in both
directions.

### E-d — The marker sweep (OR-81, deferred from 0.8.2) — **RULED 2026-09-04 (owner): collapse M4-15 into the stamp**

With one channel, a per-artifact LIMIT marker says what the default says.

**Correction to this note's own premise.** OR-81 assumed the marker becomes
redundant because one channel remains. After OR-87 and OR-89 **two channels
still exist** — the deck and the summary report are ULTIMATE, everything else
LIMIT — so the reason 0.8.2 held M4-15 has not gone away, and a blanket retirement
would leave an unmarked LIMIT CSV beside an ULTIMATE BDF in the same bundle.
E-d is narrowed accordingly.

*Recommendation:* retire M4-15's **redundant** half and keep its principle by
collapsing it into the stamp. → **OR-90**, **ruled as recommended, 2026-09-04.**

Retired:

* `Basis = LIMIT` from `net_loads.wing_load_rows` and
  `body_loads.body_load_rows` — ordinary edits now, the freeze having lapsed;
* the `_LIMIT` stem from `net_wing_loads_LIMIT.csv` and its Fuselage twin;
* the rule as prose in `PROGRAM_SPEC.md` and `GUI_design.md` §6, rewritten to
  state the default.

Kept, because still load-bearing:

* **every file states its basis in-band** — through the `methods_statement`
  stamp 0.8.2 built, which already says it per file and per channel. Same
  guarantee, delivered once instead of by a filename convention, a duplicated
  column and a stamp all asserting it;
* the `*_ULT.csv` twins keep their marker under OR-88 — those are the exception
  now.

`tests/test_ultimate_contract.py` inverts a second time: it stops requiring a
LIMIT declaration on a filename and starts requiring that every load download
route through a stamped writer, with a marker required only where the basis is
ULTIMATE.

### E-e — Does `LoadChannel` itself survive? — **SETTLED by OR-87: yes**

*Recommendation:* **delete it** if E-a is overruled (one channel, no parameter —
the consolidation the two-channel period was always a bridge to), and **keep
it** if E-a stands, because two channels still exist and the parameter is what
names them. This decision is therefore E-a's consequence, not an independent
choice, and is listed so it is not discovered late. → **OR-91**.

**Settled by OR-87: `LoadChannel` survives.** The deck is ULTIMATE and the
human surfaces are LIMIT, so two channels remain and the parameter is what
names them. Its ULTIMATE default also stays load-bearing while any caller
renders a deck-side artifact through the report layer.

### E-f — The safety-factor GUI page (OR-85) — **RULED 2026-09-04 (owner): its own note**

Note 48 deferred it here with its own note. It is untouched by E-a: the page
edits the governing table, which decides the factor whether or not anything
applies it.

*Recommendation:* keep it a **separate note**, after this one. → **OR-92**,
**ruled as recommended, 2026-09-04.** Three reasons, in order of weight: a
contract change and a UI addition should not share a note, since this one's
agreement ought to be readable on its own and its history entry ought not be
half about a Streamlit page; the page is easier to design once OR-88 has settled
what a factor *means* on a rendered surface, rather than against a moving
target; and it is the only item here with no defect behind it — everything else
fixes something currently wrong or currently unstated, and mixing the two makes
the milestone's risk profile harder to read.

Almost nothing is missing but the GUI itself: `SafetyFactorOverride` /
`SafetyFactorPolicyInput` exist, round-trip through `io.py`, are validated by
`validation._check_safety_factor_overrides` (mandatory basis, out-of-range
refusal, certification-risk warning for an override below the regulation), feed
`GoverningTable.for_project`, and export as `<project>_safety_factors.csv`. The
table is displayed and edited nowhere.

**One question for that note, not this one:** whether the page may edit the
regulation rows at all. `CONVENTIONS.md` §3 says the table is fully
user-editable *including* those rows, with four mitigations — written when no
GUI existed and the edit meant hand-editing JSON. A page makes it two clicks.

---

## 4. What the rulings amount to

OR-86's endpoint is reached, and it is narrower than the sentence that proposed
it. **The factor is stated, never applied — on every surface a person reads.**
It is still applied, exactly once, where a machine consumes it.

| Surface | Basis | Why |
|---|---|---|
| sbeam deck, applied-load CSVs, LRA model | **ULTIMATE** | a sizing input; its consumer cannot learn the factor (OR-87) |
| summary report | **ULTIMATE** | travels with the deck, in the same bundle (OR-93) |
| oracle technical report | **LIMIT** | exists to be read against Appendix A, a limit oracle (OR-89) |
| CLI, app pages, per-module CSVs, results zip, bundle transcript | **LIMIT** | shipped 0.8.2 (OR-76, OR-79, OR-80) |
| the two already-ultimate families | **marked `-ULT`** | 23.367(a)(2), 23.561(b) — the exception, made conspicuous (OR-88) |

Two channels remain, so `LoadChannel` remains (OR-91), and its ULTIMATE default
keeps protecting every caller that renders a deck-side artifact.

---

## 5. As-built plan

Written against the rulings as taken. **Order matters:** E-c moves every load
figure in the technical report, so it lands first and the report is re-read once,
against the manual, rather than twice.

### 5.1 Code

| File | Change |
|---|---|
| `sloads/report/oracle_sections.py` | `_load_cell` renders LIMIT; `_required_sf` stays as the "this is a load case" assertion but no longer feeds a multiply. Every §3 and Appendix B table gains its basis line and keeps its `SF` column (OR-89). |
| `sloads/report/render.py` | `ultimate_units` stops keying off the channel and keys off the case's factor: `sf == 1.0` marks, everything else on a human surface is plain (OR-88). `_ult` / `_ULT_UNITS` survive — the deck still uses them. |
| `sloads/safety_factors.py` | the `engine_ultimate` and `emergency` basis strings reworded: `SF=1.0` must read *"already ultimate; apply nothing"* on a LIMIT surface, not *"no further factor is applied"* (OR-88). Wording, not logic. |
| `sloads/modules/net_loads.py`, `sloads/modules/body_loads.py` | drop `Basis = LIMIT` from `wing_load_rows` / `body_load_rows` (OR-90). Ordinary edits — the freeze lapsed at the 0.8.2 cut. |
| `app/views/wing_loads.py`, the Fuselage Loads twin | drop the `_LIMIT` stem; keep the `*_ULT.csv` twins, which are the exception now. |
| `sloads/report/methods.py` | the single owner of the in-band basis statement, per file and per channel — M4-15 collapses into it (OR-90). |
| `sloads/export/**` | **unchanged** (OR-87). The four multiply sites stay. |

### 5.2 Standard

- `CONVENTIONS.md` §3 — *"applied exactly once, at the render/export boundary"*
  narrows to *"applied exactly once, at the **export** boundary"*; the channel
  table above replaces the two-channel paragraph note 48 added; the `-ULT`
  marker rule inverts.
- `ORACLE_REPORT.md` §3.3 — the *"Every load in section 3 and its appendix is
  ULTIMATE and marked"* SHALL becomes LIMIT-with-stated-factor, and the two §8
  conformance rows change with it. Section 2's SHALL and conformance row are
  untouched: it states no loads.
- `PROGRAM_SPEC.md` and `GUI_design.md` §6 — M4-15's prose replaced by the
  default plus the stamp.
- `SUMMARY_REPORT.md` — **unchanged** (OR-93).
- `CLAUDE.md` — the mission sentence unchanged (OR-87); the load-output
  paragraph gains the one-line channel table.

### 5.3 Not in this note

The safety-factor GUI page (OR-85/OR-92) — its own note, after this one, with
the regulation-row question §3 E-f raises.

---

## 6. Gates

- **G-OR-49** — no `sloads/report/**` path multiplies by a safety factor, the
  export package being the only one that may (OR-87). A source-level assertion,
  since a numeric one cannot distinguish a scaled load from an unscaled one
  without a second producer — which is the same blind spot G-OR-50 exists to
  close from the other side.
- **G-OR-50** — every deliverable states its basis in-band, and a file's stated
  basis **matches what its numbers actually are**: for one known case, the
  deck's `FORCE` resultant is compared against `nz × W` *with* the factor the
  header claims, and the technical report's §3 figure against the same case
  *without* it. This is the gate §2 found missing — every existing check
  (round-trip solve, card-sum, closure invariant) is scale-invariant and stays
  green on either basis. **It is the most valuable single item in this note**,
  and OR-87 does not make it less so: it is what would have caught the deck
  going LIMIT by accident, and it is now what catches the report failing to.
- **G-OR-51** — the `-ULT` marker appears on a case if and only if its factor is
  1.0 by the governing table (E-b), across every shipped fixture.
- **G-OR-52** — the Imperial baseline moves only in the channels the ruling
  names; regenerated deliberately, with the diff shape stated in the commit as
  note 48 established.
- Existing gates extended, not replaced: the closure invariant, the round-trip
  solve, and the Appendix A oracles — which are unaffected either way, the calc
  having always emitted LIMIT.

---

## 7. Closure

**Tier L.** Contract change: `CONVENTIONS.md` §3 and `ORACLE_REPORT.md`
§3.3/§8. `CLAUDE.md`'s mission sentence and `SUMMARY_REPORT.md` §2 are
**unchanged** — OR-87 and OR-93 are what preserve them. Needs: this note agreed first, the amended convention
cited, `changes/` fragments, and a history fragment in **full step format**
stating any deliberate Imperial regeneration and its diff shape.

No frozen set exists in 0.8.3 (`tests/test_frozen_set.py` is deleted at the
0.8.2 cut), so no OR-15 admission arises — E-d's two module edits are ordinary
work. Whether a `SCHEMA_VERSION` hop is needed depends on no ruling here: none
of these changes a persisted dataclass's shape.
