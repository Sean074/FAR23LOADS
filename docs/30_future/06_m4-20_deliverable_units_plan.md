# M4-20 — Deliverables render in the user-selected unit system (implementation plan)

**Backlog item:** [`00_backlog.md`](00_backlog.md) → **M4-20**, the first M4 item.
**Standard being implemented:** [`../10_standard/00_program_overview.md` §Units →
*Deliverable units follow the user's selection*](../10_standard/00_program_overview.md)
and [`../10_standard/SUMMARY_REPORT.md` §3.5](../10_standard/SUMMARY_REPORT.md).
Both were changed 2026-08-03; **the docs are updated, the code is not** — this
plan closes that gap.
**Blocks:** **M3-3b** G8.5 onward (the `.tex` renderer must be written against the
unit-aware writers, not retrofitted).
**Written:** 2026-08-04. **Decisions D-19 … D-22 resolved 2026-08-04** (§2).

**Scope:** the render/export boundary only. **Not in scope:** any calc change,
any change to what `project.json` stores, any change to GUI *input* handling
(`unit_number_input` already owns that boundary and is unchanged).

**Invariant:** Appendix A oracles pass unchanged; concept mode still reduces to
FAR 23 on GA inputs; the ultimate-load contract holds; the calc stays Imperial
and `io.py` still never converts a stored value.

---

## 1. Measured baseline (2026-08-04, clean tree)

| Quantity | Value |
|---|---|
| Suite | **653 passed**, 93 % coverage, `ruff` clean |
| `SCHEMA_VERSION` | **37** (M4-9, `LoadValue.key`) → M4-20 takes **38** |
| Unit resolver | `app/components.active_system()` — **already the single read**, and its docstring already names M4-20 as the item that re-points it |
| `units.convert_results` call sites | 38 across 10 views + `report/render.py` + tests |
| sbeam public writers | **14** (`span_load_csv`, `force_moment_cards`, `stick_model_bdf`, the body/tail/control equivalents, `case_index_csv`, + `write_*`) |
| CSV/BDF channels in the bundle | 1 load-case CSV per module, `case_index.csv`, 5 sbeam CSVs, 4 BDFs, `METHODS.txt`, the `.xlsx` workbook |
| Frozen schema fixtures | 7 (`tests/fixtures_schema/`) |

### What is already unit-aware (do not rebuild)

- **`report/render.py` is unit-agnostic by construction.** `load_cases_to_rows`,
  `text_report`, `module_text_report` and `results_to_rows` read the unit string
  off each `LoadValue` and put it in the column header (`_detect_unit`,
  `_detect_moment_unit`). They render whatever they are handed. **They need no
  `system` parameter** — the *writer* converts the results first, then calls them.
  The backlog's "the report functions take the system as a parameter" is
  satisfied one level up, at the writer, which is also where the in-band
  statement is emitted. Threading `system` into `render.py` as well would create
  a second authority for the same decision.
- **`governing_loads_table(conditions, system, sf)`** already takes the system and
  converts via `_display_loads` → the GUI's governing-load tables are done.
- **`units.convert_results(results, system)`** is the conversion engine for
  anything carrying `LoadValue`s.
- **`export/coordinates.py`** is documented as *"the single editable point … if a
  downstream sbeam model ever needs an inch→other-unit scale, change it here and
  every exported GRID / FORCE / MOMENT follows."* That promise is exactly what
  §4 step 4 cashes in. It is currently the identity.

---

## 2. Design decisions — **all resolved 2026-08-04**

| ID | Question | Resolution |
|----|----------|------------|
| D-19 | SI unit set for the sbeam deck | **(a)** N / mm / N·mm — one consistent solver set |
| D-20 | SI design-pressure unit | **(a)** `kPa-ULT`; amend the docs from `Pa-ULT` |
| D-21 | In-band statement vs. byte-identical Imperial | **(a)** in-band wins; strip-and-compare test |
| D-22 | Sidebar toggle → `Project` field | **(a)** toggle writes the field and marks the project dirty |

### D-19 ✅ *(a)* — the solver deck gets one **consistent** unit set ⚠️ *biggest finding*

A NASTRAN/sbeam deck is only correct if force, length and moment form a
consistent set. The GUI's SI convention is **mm** for length and **N·m** for
moment — those two cannot both appear in one deck: with GRID coordinates in mm
and FORCE in N, a MOMENT card must be **N·mm**, or every torsion is wrong by
1000×, silently, in a file that looks perfectly well-formed.

**Resolved: the deck is N / mm / N·mm.** mm is chosen over m so a station
coordinate reads the same number in the deck as on the GUI page that produced it.

**Consequence — two moment units across the bundle, deliberately.** The
human-readable deliverables keep **N·m** (what `convert_results` already
produces, what the GUI shows, what an engineer reads); the solver channel uses
**N·mm**. This is not the "one unit per dimension" policy being broken — it is
one unit per dimension *per channel*, with each file stating its own set in-band.
The channels are disjoint and are listed explicitly in §3.

**This needs a one-line amendment to `SUMMARY_REPORT.md` §3.5** ("Single system,
no dual display") making the solver-deck carve-out explicit, in the same way the
KEAS/altitude carve-out already is. Doing that is step 7's work, not an
afterthought: without it the shipped code contradicts the standard it implements.

### D-20 ✅ *(a)* — design pressure is `kPa`, and the docs change

`units._SCALAR_TO_SI` already converts `psi → kPa` and the GUI shows kPa. Three
documents (CLAUDE.md, `00_program_overview.md`, `SUMMARY_REPORT.md` §3.5) say
`Pa-ULT`. **Resolved: the code is right and the docs move** — the marker is
`kPa-ULT`. One pressure unit across GUI and exports, and design pressures read as
~50 kPa rather than 50 000 Pa.

### D-21 ✅ *(a)* — in-band statement wins; the Imperial guard is strip-and-compare

The item asked for both "every file states its unit system in-band" and "Imperial
output byte-identical to today". Those conflict: adding a `$ Units:` comment or a
units row *is* a byte change. **Resolved: every file states its system in both
systems**, and the regression guard becomes: strip the unit-statement lines, then
compare the remainder byte-for-byte against today's output. That still proves the
item changed no numbers, which is what the guard is for.

### D-22 ✅ *(a)* — the toggle writes the field and marks the project dirty

The unit system is a project preference, so the sidebar toggle writes
`Project.unit_system` and the project reads as unsaved until saved — consistent
with M2-3 rather than exempt from it. `active_system()` then reads the field, per
**D-16**, which is the one function the whole app layer goes through.

---

## 3. The two channels (the spine of this item)

Every deliverable belongs to exactly one channel. The channel decides the unit
set; the user's selection decides the system.

| | **Human channel** | **Solver channel** |
|---|---|---|
| Files | module load-case CSVs, `case_index.csv`, the text report, the G8 `.tex`/PDF, the `.xlsx` workbook | `wing/fuselage_span_loads.csv`, `tail_chordwise.csv`, `control_surface_loads.csv`, `fuselage_fitting_loads.csv`, all four `.bdf` |
| Imperial | lb / in / lb-in / ft-lb / lb/in² | lb / in / lb-in |
| SI | **N / mm / N·m / kPa** | **N / mm / N·mm / MPa** |
| ULT markers | `lbs-ULT`, `ft-lb-ULT`, `lb-in-ULT`, `lb/in^2-ULT` → `N-ULT`, `Nm-ULT`, `kPa-ULT` | `lbs-ULT`, `lb-in-ULT`, `lb/in^2-ULT` → `N-ULT`, `Nmm-ULT`, `MPa-ULT` |
| Never converted | airspeed **KEAS**, altitude **ft** | (no speed/altitude columns) |
| States its system | title page + manifest (report); units row or unit-suffixed headers (CSV) | `$ Units:` header comment (BDF); unit-suffixed headers (CSV) |

**One system per bundle.** The Export page resolves the system **once** and
passes that single value to every writer, so two files in one bundle cannot
disagree. The channel split above is a *unit-set* difference within one system,
never a system difference.

---

## 4. Sub-steps

Ordered so each lands green on its own. Steps 1 and 3 are pure and could run in
parallel with 2; step 4 is the risky one and is deliberately alone.

### Step 1 — `units.py`: the deliverable unit set (pure; no caller changes) ✅ *complete 2026-08-04*

**Shipped as written**, plus one thing the work turned up: the `lb-in → N·m`
factor was quoted twice as a rounded `0.1129848333` (in `_SCALAR_TO_SI` and
`_KIND_FACTORS`) against an exact product of `0.11298482902761668`. Moment
factors are now **derived** as force × length from named base constants
(`LBF_TO_N`, `IN_TO_MM`, `FT_TO_M`), so a moment factor cannot drift out of step
with the force and length factors it is the product of — which is the invariant
`is_consistent` tests and the whole solver-deck correctness argument rests on.
The 3.8e-8 change is SI-only and below display precision. Verified: **Imperial
output byte-identical** across all six examples, every module, rows + text
(6.7 MB compared); `test_every_imperial_load_unit_has_an_si_mapping` was shown to
fail when the `lb-in` row is removed again.

Add one authority for "what does dimension D look like in system S, in channel C":

```python
class Channel(str, Enum):
    HUMAN = "human"      # report, load-case CSV, workbook
    SOLVER = "solver"    # sbeam CSV + BDF (consistent N/mm/N*mm set)

class DeliverableUnits(NamedTuple):
    force:    tuple    # (factor, label)   lb  -> N
    length:   tuple    #                   in  -> mm
    moment:   tuple    #                   lb-in -> N*m (human) | N*mm (solver)
    torque:   tuple    #                   ft-lb -> N*m
    pressure: tuple    #                   lb/in^2 -> kPa
    system:   UnitSystem

def deliverable_units(system: UnitSystem, channel: Channel) -> DeliverableUnits: ...
def units_statement(u: DeliverableUnits) -> str:   # "SI (N, mm, N*mm)" / "Imperial (lb, in, lb-in)"
```

Imperial returns factor `1.0` for every dimension, so **there is no
`if system == IMPERIAL` branch at any call site** — the Imperial path is the same
code with unit factors of one. That is what makes the "Imperial unchanged"
guarantee structural rather than a promise.

**Two latent defects this step fixes** — both found while reading
`_RESULT_TO_SI` for this plan, both already live in the GUI's SI mode:

1. **`lb-in` and `lb/in^2` are not in `_RESULT_TO_SI`.** `convert_results` leaves
   them Imperial while converting everything around them, so an SI results table
   today mixes N and lb-in in adjacent rows. `render._LOAD_UNITS` lists both as
   load units, so they are real, reachable quantities (root bending/torsion,
   pitching moment, control-surface design pressure). **Add both**
   (`lb-in → N·m` 0.1129848333, `lb/in^2 → kPa` 6.894757).
2. **`_RESULT_TO_SI["knot"] = (0.514444, "m/s")` is a dead row and a trap.**
   *(Corrected 2026-08-04 when the step was implemented: the earlier draft of
   this plan called it a live carve-out violation. It is not — the calc emits
   `kt(EAS)`, never `"knot"`, so the row has never matched a value and the KEAS
   carve-out holds today by accident rather than by design.)* Every other half of
   `units.py` deliberately never converts airspeed (`_PROJECT_FIELD_KIND` omits
   `_kt`; `unit_number_input` has an explicit non-converted `fixed_unit=KEAS`
   path). **Remove the row** so the first producer that does emit `"knot"` cannot
   silently break the carve-out, and pin the behaviour with a test.

Defect 1 is a real behaviour change to today's *SI* output (**1580 values across
the six examples**, measured); defect 2 changes nothing today and closes a trap.
Neither touches Imperial. Each gets its own test and a note in the history entry:
they are corrections, not silent drift.

**Acceptance:** `deliverable_units(IMPERIAL, …)` is all-1.0 identity; SI factors
match NIST exactly; `moment` differs between the two channels and nothing else
does; the `knot` and `lb-in`/`lb/in^2` behaviour is pinned by test.
**Risk:** low — nothing calls it yet.

### Step 2 — Selection plumbing: `Project.unit_system`, schema 38, CLI, GUI ✅ *complete 2026-08-04*

**Shipped, with three deviations from the text below, all deliberate.**

1. **No migration hop.** The plan called for `_v37_unit_system`; none was written.
   The field is additive with a *total* default, so absent **is** its documented
   value and the tolerant readers already produce it — writing a hop that sets a
   key to the value it already reads as would be ceremony. The `SCHEMA_VERSION`
   bump is still required and the fields-hash tripwire duly demanded it. This
   exposed a contradiction in `PROJECT_GUIDE.md`, which said an additive field
   "needs nothing" while the tripwire fails on *any* persisted-shape change; the
   convention now states bump-without-hop explicitly.
2. **`project_to_dict` omits the key when it is default**, on the v36
   document-control precedent — so the six examples gain nothing and a project
   that never chose a system round-trips to a pre-v38 file exactly.
3. **`--units si` with `--export-sbeam` errors instead of exporting.** The sbeam
   writers are Imperial-only until step 4, and silently writing a deck in units
   the user did not ask for is precisely the failure this item exists to prevent.
   The error names the step. It disappears in step 4.

Also of note: the CLI's engine text report now prints a `Units:` line on the
default path, where it previously printed none — the first instance of D-21's
"Imperial states its system too" in shipped output.

1. **`Project.unit_system: str = "imperial"`** — a *preference*, not a claim about
   stored values. Document that beside the field, because the whole point of
   `io.py` never converting is that the file is always Imperial.
2. **`SCHEMA_VERSION` 37 → 38** + a `migrations._v37_unit_system` hop defaulting
   absent → `imperial`. The M4-10 fields-hash tripwire will demand the bump —
   that is the mechanism working. Add a v38 frozen fixture; keep the v37 one.
3. **`io.py`** round-trips the field (`project_to_dict`/`project_from_dict`). The
   M4-10 sentinel round-trip test covers it automatically.
4. **`cli.py --units imperial|si`** — overrides the project field for that run,
   for every output path (`-o` CSV, stdout text, **and** `--export-sbeam`).
   Resolution order: flag → project field → Imperial.
5. **`app/components.active_system()`** re-points at
   `active_project().unit_system`, falling back to the session key then Imperial.
   **This is the only app-layer edit** — every `unit_number_input` and `page()`
   call site follows for free, exactly as its docstring promised.
6. **`app/Home.py`** sidebar toggle writes the field on the project and marks it
   dirty (D-22).

**Acceptance:** all 6 examples round-trip byte-identically (they gain
`"unit_system": "imperial"`, so compare the round-tripped dict, not the file
bytes); all 7 + 1 frozen fixtures load; a v37 file loads with `unit_system ==
"imperial"`; `--units si` changes the CLI's output units and `--units` absent
reproduces today exactly.
**Risk:** low-medium — it is a schema change, but a leaf scalar with a total
default.

### Step 3 — Human channel: the writers convert, `render.py` does not ✅ *complete 2026-08-04*

`report/render.py` is **not modified**. The writers gain the parameter:

```python
io.load_cases_csv(results, header_comment="", *, system=UnitSystem.IMPERIAL) -> str
io.write_load_cases_csv(results, path, header_comment="", *, system=...)
```

*As built:* `header_comment` stayed where it was rather than moving behind the
`*` — it is positional in existing calls, and reordering it would have been an
unrelated breaking change smuggled into a units item. `system` is keyword-only.

*As built:* `module_text_report` gained **no** parameter. It has no
`unit_system` argument to pass a label to (only `text_report` does), and its
per-value unit strings already state the units; the missing header line is
D-21's in-band statement, which is step 5's job, not a signature change here.

*As built:* the GUI's own `load_cases_csv` calls were left alone — they still
default to Imperial, so GUI CSV downloads do not follow the toggle until step 6.
The call sites are mixed today (some pass display-converted results, some pass
raw), which is precisely the inconsistency step 6 resolves.

`load_cases_csv` calls `convert_results(conditions, system)` **once**, then hands
the converted conditions to the existing `load_cases_to_rows` /`results_to_rows`,
whose `_detect_unit` puts the right unit in every column header automatically.
`cli.py` passes the resolved system to `load_cases_csv`, `text_report` and
`module_text_report` (the two text reports take pre-converted results plus the
existing `unit_system` label argument — already supported by `text_report`).

**Acceptance:** with `system=IMPERIAL` every module CSV and text report is
byte-identical to today (no in-band line in this step yet); with `si` the headers
read `(N-ULT)` / `(Nm-ULT)` / `(mm)` and the `Speed (kt)` / `Altitude (ft)`
columns are **unchanged**.
**Risk:** low. The one trap is double conversion — a caller that converts and
then passes `system=` again. Guard: `load_cases_csv` is the only converter in the
human channel, and a test asserts converting twice is not silently accepted
(feed it already-SI values and require the units to be recognisably wrong, or
assert the writer is the sole `convert_results` caller in `io.py`).

### Step 4 — Solver channel: `coordinates.py` becomes the scale point ✅ *complete 2026-08-04*

*As built — the solver set also needed its own **pressure**.* Step 1 gave the
solver channel a consistent moment (`N·mm`) but left pressure at the human
channel's `kPa`, which is the identical D-19 defect one dimension over: pressure
is force / length², so a deck in N and mm has stresses in **`MPa` (N/mm²)**, and
`kPa` in it is wrong by 1000× exactly as `N·m` would be. Fixed here:
`PSI_TO_MPA` is *derived* (`LBF_TO_N / IN_TO_MM²`), the solver set carries it,
and `DeliverableUnits.is_consistent` now checks **both** derived dimensions
(`moment == force × length` **and** `pressure == force / length²`) so the next
one cannot be missed the same way. The moment was the loud case; the pressure was
the quiet one.

*As built — the scale point is enforced, not just documented.* `to_grid` /
`to_force` / `to_moment` / `to_pressure` (new) **raise** on a unit set that fails
`is_consistent`. `deliverable_units(SI)` defaults to `Channel.HUMAN` — the set
every report uses — so passing it to a deck writer is a plausible slip, and it
now fails loudly at the one point every card and cell passes through.

*As built — the CSV cells go through the same three functions the cards do*,
rather than being scaled beside them. A span CSV and the deck it accompanies
therefore cannot disagree; there is exactly one multiplication site in the whole
export channel.

*As built — the negligible-load cut is applied to the unscaled magnitude*, so
which cards a case emits is a property of the load, not of the unit system. An
SI deck and an Imperial deck of the same case have the same cards.

*As built — the stick model's placeholder section properties convert too*
(E by the pressure factor, A by length², I/J by length⁴). The reactions are
stiffness-independent so the numbers do not matter, but a deck mixing an Imperial
modulus with millimetre GRIDs is wrong on its face and someone will swap in a
real section long before they re-derive that it did not matter.

*Verified:* across all six examples × wing/tail/control × stick model, the
Imperial output changed by **zero numeric characters** — only the header rows and
two `$` comment lines, both authorised by D-21.

1. **`coordinates.py`** — `to_grid`/`to_force`/`to_moment` take a
   `DeliverableUnits` and apply the scale (identity for Imperial). This is the
   single editable point the module was written to be; **no `sbeam_bridge`
   arithmetic changes**, only what it hands to these three functions.
2. **The 14 sbeam public writers** take `*, system: UnitSystem = IMPERIAL`,
   resolve `deliverable_units(system, Channel.SOLVER)`, and use it for the
   GRID/FORCE/MOMENT scale, the CSV cell values and the CSV header units.
3. **Header units become explicit.** `_CSV_FIELDS` is bare today (`Fx`, `Fz`,
   `My`, `Sz`, …) while `_BODY_FITTING_FIELDS` already carries `(in)` /
   `(lb-ULT)`. Unify on the fitting form — every column header carries its unit
   and `-ULT` marker, in both systems. This is a visible Imperial change, which
   D-21 authorises.
4. **The equilibrium comment line** (`$ FORCE set sums to root Sz = … lb;
   MOMENT(My) set sums to root torsion Myy = … lb-in`) takes the active labels.

**Acceptance:** Imperial cards are byte-identical to today after stripping the
new `$ Units:` line and the header row (D-21); in SI the **check sums still
close** — the FORCE set sums to the root shear and the MOMENT set to the root
torsion in the new units, which is the physics test, not a factor test; a station
X in the SI deck equals the same station shown in mm on the GUI page.
**Risk: the highest in this item, and it is the moment scale.** N·m where N·mm
belongs is a 1000× error in a file that parses cleanly and sizes structure
wrongly. Mitigations: the consistency is expressed once, in `deliverable_units`,
not per writer; a dedicated test asserts `moment` differs between `HUMAN` and
`SOLVER` and that `SOLVER.moment == SOLVER.force × SOLVER.length` exactly (the
dimensional identity — force × length = moment — which is the actual invariant,
and it holds trivially for Imperial too).

### Step 5 — In-band unit statements ✅ *complete 2026-08-04*

*As built — one bundle-wide statement, not a per-file line.* The plan listed four
separate statements (a BDF header line, a CSV `# Units:` line, the BASIS
paragraph, a workbook row). Three of them are the *same* block: `methods.py`
already builds the statement once and wraps it per channel (G8-3), so adding a
`UNITS:` paragraph there gives the CSV its `# UNITS: …`, the deck its
`$ UNITS: …` and `METHODS.txt` its paragraph from one change. Only the workbook,
which has no comment rows, needed a separate carrier (a `Units` row on the
*Project* sheet).

*As built — the statement is the **bundle's**, and names both channels.*
`methods_statement` takes `system=`, not a `DeliverableUnits`. The Export page
builds one stamp and puts it on both the human load-case CSVs and the sbeam
CSVs/decks, so a channel-specific statement would be wrong on half the files it
lands in. In SI the paragraph therefore names both sets and attributes each
(`N·m, kPa` for the readable files; `N·mm, MPa` for the decks); in Imperial one
set does both jobs and the statement says so rather than inventing a split.

*As built — the BASIS `-ULT` marker list is derived from the unit sets.* It was
hard-coded as `lbs-ULT, ft-lb-ULT, N-ULT, Nm-ULT` regardless of system: it named
markers no Imperial file carries and omitted every marker step 4 added
(`Nmm-ULT`, `MPa-ULT`). Generated from both channels now, so it cannot drift from
what the writers emit.

*As built — `units_statement` names all four dimensions* (`Imperial (lb, in,
lb-in, lb/in^2)`, `SI (N, mm, N·mm, MPa)`). Pressure was added for the reason
step 4 uncovered: it is the dimension a reader cannot infer from the numbers, and
kPa-vs-MPa is the same silent 1000× as N·m-vs-N·mm.

**Defect found and fixed here — the `.bdf` decks carried no statement at all.**
The Export page built a `bdf_comment_block` and then never applied it, so the
four decks were the one channel in a bundle stating neither their ULTIMATE basis
(a G8.3 claim) nor their units. `ruff` cannot catch it: the unused name is
module-level and its unused-variable rule is a *local* check. Every BDF writer
now takes `header_comment=` like the CSV writers, `_stamped()` prepends it, and a
source-level test asserts all five deck artifacts pass `_bdf_stamp`. An unstamped
call is byte-identical, so Imperial CLI output is untouched.

*Not done here — the CLI channel carries no methods stamp.* `cli.py`'s `-o` and
`--export-sbeam` outputs have never carried the G8.3 block (CSV or BDF); that
predates M4-20 and is a G8.3 coverage gap, not a units one — every CLI file does
state its units, via step 3/4's column headers and the decks' `$` axis comments.
Logged as a backlog item rather than folded in, since stamping the CLI changes
the bytes of every headless export.

#### As planned

- **BDF:** a `$ Units: Imperial (lb, in, lb-in)` / `$ Units: SI (N, mm, N*mm)`
  line in the header block, beside the existing G8.3 methods stamp.
- **CSV:** unit-suffixed column headers (step 3 gets them free from
  `_detect_unit`; step 4 adds them to the sbeam CSVs) **plus** a `# Units: …`
  line in the `csv_comment_block` stamp, so a CSV opened without its headers
  still says what it is.
- **`METHODS.txt` / `methods_statement`:** the BASIS paragraph currently
  hard-codes the marker list `(lbs-ULT, ft-lb-ULT, N-ULT, Nm-ULT)`; make it state
  the bundle's actual system and its markers, including `kPa-ULT`.
- **Workbook:** a `Units` row on the *Project* sheet.

**Acceptance:** every file in a bundle carries a statement; the statement names
the same system in all of them; `strip_comment_lines` still round-trips (the G8.3
readers must not break — `workbook._csv_to_df` reads with `comment="#"` and is
the audited path).

### Step 6 — Export page and bundle: resolve once, state it ✅ *complete 2026-08-04*

*As built — the whole GUI download layer, not only the Export page.* The plan
scoped step 6 to `export_report.py`, but ten other views ship their own
CSV/BDF download buttons; leaving them on the writers' Imperial defaults while
the bundle followed the toggle would produce exactly the two-files-disagree
failure this step exists to prevent. Every download call in the app layer now
takes the page's system.

*As built — a pre-existing double-conversion hazard, fixed.* `weight_mass.py`
handed `load_cases_csv` its **display-converted** results. Since step 3 the writer
converts internally, so that page's CSV was accidentally SI while every other
page's was Imperial. It now passes the raw results plus `system=`, and only the
unit-agnostic `module_text_report` gets the converted copy — the asymmetry step 3
established, now consistent across all ten views.

**Defect found and fixed here — twelve views bypassed `active_system()`.** They
read `st.session_state["unit_system"]` directly, a *second* authority for the
selection that D-16 says must not exist. It was latent rather than live (Home.py
rewrites the session key from the project field on every render, so the two agree
in practice), but it means step 2's re-point of `active_system()` at
`Project.unit_system` reached only the views that went through
`unit_number_input`/`page`. All twelve now call `active_system()`, whose own
fallback is that same session key — so behaviour is unchanged where they already
agreed and correct where they could not.

*Not done here — the per-page hand-built LIMIT CSVs.* `wing_loads`,
`fuselage_loads`, `tail_loads` and `loads_plots` each build a CSV from their own
row dicts (`csv.DictWriter` over `wing_load_rows(...)` etc.) rather than through
a `sloads` writer. Those files are Imperial in both systems and their columns
state no units at all, while the table above them on the page is converted. They
are the LIMIT analysis-page channel (the CLAUDE.md carve-out), the row builders
are bespoke per page, and giving them unit-suffixed headers is the same shape of
work step 4 did for the sbeam CSVs — logged as **L-8i** rather than folded in.

#### As planned

- `export_report.py` resolves `active_system()` **once** into a local and passes
  it to every artifact call — that single value is what makes "one system per
  bundle" true by construction rather than by discipline.
- The page states the system beside the download control
  (`GUI_design.md` §7), e.g. *"This bundle will be written in **SI** (N, mm; the
  sbeam decks use N·mm). Airspeed stays KEAS and altitude stays ft."*
- Per-module CSV buttons and the workbook use the same local.

**Acceptance:** an AppTest builds a bundle in each system and asserts the caption
matches what the files contain.

### Step 7 — Tests and doc sync ✅ *complete 2026-08-04* — **M4-20 CLOSED**

*As built — the Imperial guard is a digest baseline, not frozen copies.* The plan
asked for "byte-identical to a frozen pre-M4-20 snapshot of all 6 examples". Six
examples × ~43 channels of near-identical CSV is megabytes of fixture, and the
question the guard answers is binary. `tests/imperial_baseline.py` renders every
channel and freezes a SHA-256 per channel in
`tests/fixtures_imperial/digests.json` (23 KB, **256 channels**); the failure
message names the drifted channel, and `python tests/imperial_baseline.py`
regenerates. Verified to bite: a hand-corrupted digest fails with
`ga6_normal.project.json: Imperial output changed in ['sbeam/wing_span']`.

*As built — a companion test asserts the baseline is not vacuous.* The renderer
swallows a `MissingInputError` for an example that lacks a slice, so a regression
making every channel raise would shrink the fixture to nothing and leave the guard
green forever. The set of examples reaching the solver channel is pinned exactly —
`concept_heavy` legitimately has none (no `cl`/`v_eas_kt`, no `fuselage_mass`).

*As built — "oracles unchanged" is asserted structurally.* The plan's matrix row
was "Appendix A assertions numerically unchanged". The per-module tests already
assert the numbers; what M4-20 has to prove is that the calc never *reaches* them
differently. A source guard that no `sloads/modules/*.py` calls `convert_results`
/ `deliverable_units` / `to_si_scalar` says exactly that, and does not go stale.

*Doc sync.* `DATA_DICTIONARY.md` needed no regeneration (schema v38 landed in step
2 and it was regenerated then — confirmed by a no-diff run). `CLAUDE.md`,
`00_program_overview.md`, `SUMMARY_REPORT.md` §3.5, `PROJECT_GUIDE.md` and
`GUI_design.md` §7 were each updated in the step that changed the behaviour they
describe, not batched here.

*Close-out.* M4-20 moved to
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md);
**D-19 … D-22** moved to
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md);
**M3-3b G8.5 unblocked** (the `.tex` renderer is now written against the
unit-aware writers rather than retrofitted). Three follow-ups logged rather than
folded in: **L-8g**, **L-8h**, **L-8i**.

#### As planned

**Tests** (new file `tests/test_deliverable_units.py` plus additions):

| Test | Asserts |
|---|---|
| Imperial guard | every channel's output, with unit-statement lines stripped, is byte-identical to a frozen pre-M4-20 snapshot of all 6 examples |
| Dimensional identity | `SOLVER.moment == SOLVER.force × SOLVER.length` for both systems |
| Channel split | `HUMAN.moment != SOLVER.moment` in SI; equal in Imperial |
| Bundle single-system | one zip → report + every CSV + every BDF all state the same system |
| SI closure | SI FORCE set sums to root shear; MOMENT set to root torsion |
| Aviation carve-out | KEAS and altitude columns identical in both systems, in CSV **and** report (this is the `knot` fix from step 1) |
| Round-trip | Imperial → SI → Imperial lossless to display precision, per dimension |
| Oracles | Appendix A assertions numerically unchanged — the calc is not in this path |
| CLI | `--units si` vs. default; `--units` with `--export-sbeam` |

**Docs** (per CLAUDE.md, same session):

| Doc | Change |
|---|---|
| `CLAUDE.md` | `Pa-ULT` → `kPa-ULT` in the ultimate-load contract (D-20) |
| `00_program_overview.md` | §Units: `Pa-ULT` → `kPa-ULT`; add the solver-channel unit set |
| `SUMMARY_REPORT.md` §3.5 | `Pa-ULT` → `kPa-ULT`; the D-19 solver-deck carve-out beside the KEAS/altitude one |
| `PROJECT_GUIDE.md` | `Project.unit_system` semantics (preference, never a claim about stored units); schema 38 |
| `GUI_design.md` §7 | the Export page states the bundle's system |
| `DATA_DICTIONARY.md` | regenerate |
| `00_backlog.md` → `40_history/` | close M4-20, unblock M3-3b |
| `CHANGELOG.md` | `[Unreleased]` entry incl. both step-1 corrections |

---

## 5. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **N·m in a deck that needs N·mm** | **highest** — 1000× silent torsion error | one authority (`deliverable_units`), the force×length=moment identity test, SI closure test |
| Double conversion (writer converts, caller already did) | high — 4.45× | exactly one `convert_results` per channel, at the writer; test |
| A `LoadValue` unit missing from `_RESULT_TO_SI` passes through unconverted | medium — mixed units in one table | step 1 fixes the two known gaps; add a test that every unit in `render._LOAD_UNITS` has an SI mapping, so the next new unit fails loudly |
| Schema 38 breaks a saved project | medium | migration hop + frozen fixtures + M4-10's sentinel/tripwire tests |
| Imperial output drifts unnoticed | medium | the strip-and-compare guard over all 6 examples |

## 6. Global gates (every step)

- `ruff check sloads/ cli.py` clean; `pytest` green (**653 baseline**, count may only rise).
- Appendix A oracle assertions numerically unchanged. **Any edited expected value
  is a stop-and-review, not a fix.**
- Both concept fixtures run end-to-end.
- New domain terms (`kPa`, `N·mm`) → `cspell.json`.
- Git stays the user's: this plan describes changes; the user commits.
