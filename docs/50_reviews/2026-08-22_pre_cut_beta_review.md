# Pre-cut beta review — the oracle GUI's function end-to-end (2026-08-22)

**Charge (issue #61, user, 2026-08-22):** before cutting **0.7.0 — a beta
release of the oracle GUI**, establish what must be fixed for the oracle GUI
to be *useful*. Three strands, in the order the user agreed: (1) the
**fresh-project journey** — a FAR 23 engineer who knows the McMaster suite
opens the oracle GUI cold and enters an airplane page by page, runs, downloads,
saves, reloads and re-runs; (2) a **delta code review** of `oracle_app/` +
`app_shell/` and the `sloads/` entry points they call, since `4b1ddcc`
(the 2026-08-20 review's commit: the ten MAJOR fixes, #33, #40–#45, #51, #52
landed after it); (3) the note-32 gates **G1–G8 re-checked for rot** against
the shipped artifacts (the #43 lesson: a guard that still passes but no longer
constrains). This file is the body of record (`CLAUDE.md` rule 5).

**The bar (agreed before the review):** a finding is **BLOCKS-CUT** if the
persona cannot complete the journey, gets a wrong number, or loses data;
**KNOWN-ISSUE** if the GUI is awkward but workable — those go into the
release notes. Review is read-only: no fix was applied in this pass.

**Method.** The journey was driven two ways: the live app in the browser
(`streamlit run oracle_app/Oracle.py`, Geometry / Weight / One Engine Out
pages, to calibrate wording and layout), and a scripted `AppTest` walk of all
14 pages: `examples/ga6_normal` (the Appendix A airplane) and
`examples/dhc8_dash8` (a twin, so One Engine Out and ENGLOADS' turboprop
branch are exercised) each serve as the *answer key*; a blank project is typed
page by page through the pages' own widgets (tables replayed through
`st.data_editor` with exactly the frame the loaded answer renders), and after
every page — and again once everything is typed — the page's result blocks and
download payloads are compared byte-for-byte with the loaded example's. The
typed project is then serialised, reloaded and re-run (bit-identity), and its
`project_to_dict` diffed against the example's. The script is kept as
`scripts/oracle_journey.py` (not yet a test — PB-3 proposes it become one);
its two reports are summarised in §3.

**Gate state at review time:** `ruff` clean, `mypy` clean, **2674 passed /
30 skipped / 1 xfailed** on the working tree with #52 landed and the examples
at their on-disk v41.

---

## 0. Verdict

**Do not cut yet.** The oracle GUI's *mechanics* are sound — every one of the
14 pages renders on a blank project in both unit systems, every oracle input
the registry names can be typed (nothing the answer key holds was
unreachable), the typed GA-6 reproduces the loaded GA-6's STRSPEED, V-n,
AIRLOADS, NETLOADS station table, WINGINER, BALLOADS, TAILDIST, aileron, flap,
tab, landing and WTONECG/WTENV output **byte-for-byte**, and save → reload →
re-run is a fixed point. The data-entry integrity work of the last two weeks
(#35, #36, #51, #52) holds under this pass: two-edit clobber, typed zeros,
partial curve rows, SI round-trip, the generation stamp — all observed intact.

What does not hold is the seam between *what the form accepts* and *what the
calc assumes*. Eight findings block the cut, in three groups:

**The oracle GUI's project is not the project the gates test (PB-1 … PB-3).**
`Project.mass` is a result slice only `app/`'s Apply writes, so from a fresh
project **One Engine Out is a permanent dead end** on a twin and
Configuration's tip-back silently uses a 25 %-MAC estimate (GA-6 33.1°
against 13.5°). Every weight item the oracle GUI enters is untagged, so the
wing panel lands on the fuselage beam and the **BODYLOAD station table moves
by 9 % of peak shear** with no note. And gate G5 — the claim that the reduced
input set reproduces the original — is green only because its reduction keeps
the result slices and the turbine-rotor rows it says it drops, and never
compares the station tables: the real oracle-GUI project diverges on four
pages (ENGLOADS **−16 %** twin mount torque among them). The #43 class
exactly.

**Free text where the calc wants a key (PB-5, PB-7, PB-8).** The selectors
the registry marks `supplied` — CG-case names, the cruise/flaps-down set
names — are blank-seeded text boxes with no uniqueness check, and
`select.py` keys dicts on them: leave two CG cases at the seed and TAILDIST's
chordwise loads flip sign (LT25 **925 → −297 lbf**) with no error. The FAR 23
category is a text box too: `"u"` or `"Utility"` silently becomes Normal
(n = 3.8 for 4.4). And the engine layout is validated only in
`Project.__post_init__`, so a layout set against the wrong engine count is
accepted in-session, saved, and **refused on reload** — a file the oracle GUI
cannot repair.

**The shell loses the last edit and the last project (PB-4, PB-6).** The
sidebar serialises the *Download project.json* payload before the page
persists the rerun's edit, so the file downloaded after the last entry is
always missing it (and the dirty flag says clean). `project.name` has no
widget in this GUI, so every *Save to disk* writes `project.project.json`
over the previous one, unasked — `projects/` already holds the evidence.

Sixteen more findings are release-notes material: the surface the chain keys
on must be named exactly `wing` (`Wing` blocks eight pages, with a message);
four gate tests that no longer constrain; a migration notice that can never
fire; page-order dependencies that change numbers already downloaded; the
unit radio beating a loaded file's system; a display-only copy showing the
wrong governing value; `ZeroDivisionError` reported as "cannot run yet";
overrides that can never be cleared; a mid-entry planform that crashes Wing
Loads; coefficient widgets at four decimals; leaf-name labels; note-32 drift.

---

## 1. Findings — BLOCKS-CUT

### PB-1 — `Project.mass` is never produced in the oracle GUI: One Engine Out is unreachable, Configuration's CG falls back silently

**Where.** `sloads/workflow.py:126` (`weight_mass` `produces="mass"`),
`oracle_app/results.py:201-233` (runs `step_modules`, persists nothing — OG-F),
`app/views/weight_mass.py:10` ("Apply persists the derived `Project.mass`
slice (M4-17a)"), consumers `sloads/modules/one_engine_out.py:271`,
`sloads/modules/configuration.py:518-521`, `sloads/cg_cases.py:273`.

**What.** `mass` is in `field_registry.NON_INPUT` ("result slice (WTONECG
output)") and is written by exactly one place: the main GUI's Weight & Mass
Apply. The oracle GUI's Weight & Mass page runs WTONECG and *shows* the mass
cases, but by design a render pass mutates nothing, and no page has an Apply —
so `project.mass` stays `None` for the life of a project built there.
Every shipped example carries a persisted `mass`, which is why no test and no
example-driven walk has ever seen the consequence.

**Reproduction (journey, both examples).** After all 14 pages are typed:
`one_engine_out` → *"ONENGOUT needs `mass` — run the pages before this one
first."* on the DHC-8 (the loaded example prints 24 rows and two downloads);
`configuration` → *"CG station (25% MAC estimate) 74.07 in / Tip-back angle
33.11°"* against the example's *"CG station (Weight DB) 85 in / 13.49°"*
(GA-6), *390.3 in / 18.56°* against *397.9 in / 21.16°* (DHC-8).
`cg_cases.py:273`'s `zbar` reads `project.mass.cases[0].cg_z` and falls back
to 0 — no shipped number moved on either example (the CG cases carry their
own `zcg`), but the path is live.

**Why it blocks.** One of the 14 oracle pages cannot run from a fresh project
on the airplanes it exists for (twins), and the message it shows is wrong —
there is no page before it that produces `mass`. The #45 DAG guard accepted
`weight_mass.produces="mass"` because the *declaration* is complete; the
oracle GUI never executes it.

**Suggested fix (design call — the user's).** Two honest shapes:
(a) *derive on read:* a single-owner `mass_cases(project)` (WTONECG's
`build_mass` over `weight.items`, the persisted slice when present, with a
drift guard that the two agree on every example) — consumers take it, the OEO
step's `requires` becomes `weight`, and `mass` becomes a cache rather than an
input; or (b) *an explicit Run on the oracle Weight page* that persists
`mass`, breaking the no-Apply model for one page. (a) matches the Step-G6 tail
proxies and the `select` envelope single-owner precedent (`select.py:143`);
(b) is smaller but adds a second data-entry model. Tier M either way; if (a),
a CONVENTIONS §7 row (result slices are caches, derived by their owner).

### PB-2 — Untagged weight items put the wing on the fuselage beam: the Fuselage Loads page prints a BODYLOAD table that is 9 % off, and says nothing

**Where.** `sloads/field_registry.py:588` (`weight.items[].component`, SLOADS,
not supplied), `sloads/mass_distribution.py:131-158` (`infer_component` →
always `FUSELAGE`), `:405` (`wing_mass_tie`, never rendered by
`oracle_app/results.py`), `app_shell/limit_csv.py` (`body_limit_rows`).

**What.** The original BODYLOAD takes the *fuselage* item list as its own
input; in the replication that choice is the `component` tag on the one shared
weight database. The tag is classified SLOADS, so the oracle GUI never offers
it, every item it enters is `None`, and the documented fallback — "the
fuselage beam is complete: heavier than the truth by the wing panel, never
lighter" — applies to every oracle-GUI project. The fallback's own alarm
(`wing_mass_tie` fails: *"items tagged wing sum to 0 lb against 2 × (panel
165 + concentrated 0) = 330 lb"*) is rendered in `app/` only.

**Reproduction (journey).** GA-6, everything typed: the typed project's
distribution is `{FUSELAGE: 3400}`; the example's is `{WING: 330, FUSELAGE:
3005, HTAIL: 42, VTAIL: 23}`. Fuselage station table: 96 rows against 92;
over the 92 common `(case, station)` keys, max |ΔSz| = **494 lbf** against a
5 271 lbf peak, max |ΔMyy| = 6 107 lb-in against a 242 843 lb-in peak
(worst single station AFT UP BENDING @ 97 in: −5 068 against −2 865 lb-in).
DHC-8: 92 against 80 rows, first-station differences of the same order. The
`_LIMIT.csv` download carries the same numbers.

**Why it blocks.** A wrong delivered number on an oracle page with no
in-band signal. It also satisfies the registry's own `SUPPLIED_RULE` ("
demonstrably load-bearing — omitting it changes an oracle-page result") —
G5 did not demonstrate it only because of PB-3.

**Suggested fix.** `weight.items[].component` → `supplied=True` with the
basis *"BODYLOAD's own item list; load-bearing (G5): untagged items put the
wing panel on the fuselage beam"* — one registry row, one more column in the
Weight items table (an enum column, already supported). And the Fuselage
Loads page shows `wing_mass_tie` / `untagged_tail_surfaces` beside the table
when they fail — the check exists, it only needs the oracle channel. Tier S–M.

### PB-3 — Gate G5 tests a project the oracle GUI cannot build

**Where.** `sloads/field_registry.py:933-967` (`reduce_to_oracle_inputs`,
`_reduce`), `tests/test_oracle_inputs.py:117-131` (`_outcomes`),
`:170-193` (exact-equality test), `:196-205` (declared drops).

**What — three holes, each verified this session on the working tree:**

1. **Result slices survive the reduction.** `mass` and `envelope` are
   `NON_INPUT`, so `_walk` gives them no registry paths, so `_reduce` descends
   into them and resets nothing: `reduce_to_oracle_inputs(dhc8).mass.cases`
   has 1 case. The oracle GUI's project has `mass is None` (PB-1).
2. **Omitted records keep their values.** `omitted_records()` knows the oracle
   GUI never creates `engines[].rotors[]` (and `aero_coeffs.fuselage_moment`,
   `lateral_body_aero`, `tail_mass[]`, the CG-case loadings), yet `_reduce`
   only resets *fields with defaults* inside each row — `Rotor`'s fields have
   none, so the reduced DHC-8 still carries
   `Rotor(diameter_in=18, weight_lb=70, max_rpm=30000, TURBINE, CW)`.
   Consequence, measured: the oracle-GUI DHC-8's ENGLOADS EM-05 sudden-stoppage
   torque is **−36 300 against −42 072 ft-lb** and the EM-06 gyroscopic moments
   **4.54e4 / 1.82e4 against 5.26e4 / 2.10e4** (both engines, 10 CSV lines) —
   the turbine rotor's share, dropped with no marking, on the closure-locked
   twin family.
3. **Station tables are outside the comparison.** `_outcomes` collects
   `ModuleResult.conditions[].values`; BODYLOAD "produced no conditions" on
   every fixture, and its output — the third owner OG-6 was amended to name
   on 2026-08-20 — is `build_body_loads` → `body_limit_rows`, which no G5
   part reads. PB-2's 9 % is invisible to it. The same is true of the wing
   and tail station tables (today identical; tomorrow unguarded).

`test_the_reduced_project_reproduces_every_number` is therefore green on all
five EXACT examples while the artifact it stands for — *the project the
second front-end writes* — diverges on four pages. The lesson the 2026-08-20
review wrote into `CLAUDE.md` rule 3 ("gates read the shipped artifact") is
the one this gate misses.

**Suggested fix.** `_reduce` drops every `NON_INPUT` result slice (`mass`,
`envelope`, `loads`) and **every omitted record** (the list emptied, not the
fields defaulted); `_outcomes` folds the three `STATION_TABLES` row builders
into the value set keyed `(module, case, station, column)`; the journey
harness itself (a typed-from-blank project against the loaded example) joins
the test file as the second leg — it is what the gate's wording describes.
Then the residue is decided, not discovered: rotors either become oracle
inputs (`supplied`, "load-bearing: −16 % twin mount torque") or a
`DECLARED_DROPS` entry states the oracle GUI's ENGLOADS is the
propeller-only original. Tier M.

### PB-4 — "Download project.json" is one edit stale (and the dirty flag with it)

**Where.** `oracle_app/Oracle.py:65` and `app/Home.py:70`
(`render_shell_sidebar(project)` before `pg.run()`),
`app_shell/sidebar.py:138` (`st.download_button(..., project_to_json(project))`),
`:76` (the `has_unsaved_changes` caption).

**What.** Streamlit runs the script top to bottom on every rerun. The rerun
that carries a widget edit renders the sidebar *first* — the download
button's payload is serialised from the project **before** the page's
`_persist` writes the edit — then the page. The payload served by the button
the user now sees is therefore the project as of the previous interaction.
`Save to disk` is *not* affected (its handler runs on the click's own rerun,
after the previous rerun persisted). Verified under `AppTest` on the real
entry point: after `wing_area_sqft := 184.12` the project holds 184.12 and
the caption still reads *"⚪ No unsaved changes"*; one more rerun and it reads
*"🟠 Unsaved changes"*. The row-expander titles (`1 · (unnamed)` after the
name is typed) lag for the same reason.

**Why it blocks.** The oracle GUI has no Apply, so *every* last edit is the
one missing from the download; the user has no signal (the flag says clean).
In `app/` the Apply click is the extra rerun that hides it — except for the
Apply itself, whose merge is likewise missing from a download taken
immediately after.

**Suggested fix.** Render the project-file block after `pg.run()` (the units
radio must stay first — `active_system()` reads it), or make the payload
lazy (`st.download_button(data=callable)` where the Streamlit version allows).
One owner, both GUIs; a guard that edits then reads the payload in the same
run. Tier S.

---

### PB-5 — The selector names the calc keys on are blank-seeded free text with no uniqueness check: duplicates silently change tail loads

**Where.** `oracle_app/form.py:220-261` (`blank()` seeds `name=""`), `:477-482`
(a plain `text_input`), `sloads/modules/select.py:390-392, 406, 534-624`
(`flaps[aero.cruise.name]`, `cg_map = {c.name: c …}`, `cg_map[p.cg]`),
`sloads/field_registry.py:606-607, 681, 689` (`supplied=True`, basis "set /
case selector (standing ruling); structurally required").

**What.** The fields the original suite expressed positionally are, in the
replication, names that `select.py` uses as dictionary keys. The oracle form
seeds every new row's name to `""` and asks for nothing more; two rows with
the same name collapse to one entry, and nothing raises.

**Reproduction (reduced GA-6).** Blank every `weight.cg_cases[].name`: every
load-case row count is unchanged and no error is shown, but TAILDIST's
chordwise table changes in 7 of 13 rows — `BAL UP RETRACTED` LT25 **925.01 →
−297.08 lbf**, LT50 −409.68 → 290.63, PSI(X1) 0.6955 → −0.2234. Name
`aero_coeffs.cruise` and `flaps_down` alike (both `""`, or both `CRUISE`):
SELECT drops 115 → 101 rows and the FLTLOADS payload changes, no error.

**Why it blocks.** Wrong numbers from the most ordinary mistake a from-scratch
entry can make (leave the seed), with the page reporting success. The
`supplied` mark's own definition — "fields the oracle GUI *writes* without
asking" — is not what the renderer does; it asks, blank.

**Suggested fix.** Seed distinct names (`CRUISE` / `LANDING`; `CG1 … CGn`),
validate uniqueness in `render_table` / `render_record` with an `st.error`
that withholds results, and make `select.py` raise on a duplicate key rather
than collapse it — plus the guard test. Tier S–M.

### PB-6 — `project.name` has no widget in the oracle GUI: every save is `project.project.json`, overwriting the last, unasked

**Where.** `app_shell/sidebar.py:127-142` (filename from `project.name`;
`os.makedirs` + `save_project`, no existence check), `sloads/field_registry.py:76`
(`name` is `NON_INPUT`, "document metadata" — so no oracle page renders it),
`oracle_app/` (no other writer).

**What.** A project built in this GUI is named `""` for its whole life.
*Save to disk* therefore writes `projects/project.project.json` every time,
silently replacing whatever was there; the Open list can never show more than
that one entry; *Download project.json* is likewise always `project.project.json`.
The shipped `projects/` directory already holds a 41-byte
`project.project.json` from exactly this path. When a name *is* set (a loaded
example), the filename is the raw name with spaces replaced —
`ATR_42-300_("ATR_42-100"_prototype_designation_never_entered_production;_-300_…).project.json`
— legal on macOS, an `OSError` traceback on Windows, unreadable in the
selectbox either way.

**Why it blocks.** Loss of a previous project by a normal second save, with
no confirmation and no way to name the work.

**Suggested fix.** A name widget in the shared sidebar's project-file block
(one owner, both GUIs); an overwrite confirmation on Save; one sanitiser
(`[^A-Za-z0-9._-]` → `_`, length-capped) shared by Save and Download. Tier S.

### PB-7 — An engine layout set against the wrong engine count saves a file the loader refuses

**Where.** `sloads/models/project.py:338-345` (`__post_init__` validates
`engine_layout.expected_count == len(engines)` — construction only),
`oracle_app/form.py:456-468` (layout selectbox, `setattr`), `:686-692` (engine
row count, `setattr`), `app_shell/project_state.py:119-138` (`safe_load`
shows "Couldn't load …").

**Reproduction.** Reduced GA-6 (one engine), set `engine_layout = 2W`
in-session: accepted; `project_to_json` writes it; `project_from_dict` raises
`ValueError: engine_layout 2W expects 2 engine(s), got 1`, so the sidebar
reports "Couldn't load …" in both GUIs. This GUI has no JSON editor, so the
file is stuck until hand-edited.

**Why it blocks.** A saved project that cannot be reopened is lost work; the
path is two ordinary widgets on one page in either order.

**Suggested fix.** Validate on the Engine Mount page (an `st.error` that
withholds results while the count and layout disagree) **and** a tolerant
loader that flags the layout rather than refusing the whole file. Tier S.

### PB-8 — Coded inputs rendered as free text: the FAR 23 category and the strut type fall through silently

**Where.** `oracle_app/form.py:477-482` (`str` → `text_input`),
`sloads/modules/structural_speeds.py:189-197` (`category == "U"` / `"A"`,
else Normal), `sloads/modules/landing.py` (strut `"O"` / `"S"`),
`sloads/models/inputs.py:1388` (`strut: str = "O"`).

**Reproduction.** `maneuver_load_factors("U", 3400, …)` → n = 4.4;
`"Utility"` → 3.8; `"u"` → 3.8. The widget accepts all three; nothing is
shown. The strut box shows `O` and accepts anything, falling through to the
spring efficiency.

**Why it blocks.** The certification category is the first thing the
persona types on the Structural Speeds page and the one that sets every
manoeuvre load factor; a wrong-case entry silently produces Normal-category
loads for a Utility airplane.

**Suggested fix.** Enums for both (the renderer already does selectboxes for
enums); `category` can stay a `str` in the schema with an enum-backed widget
and `.upper()` at the owner, so no hop is needed now; `strut` becomes an enum
at the next hop. Tier S.

---

## 2. Findings — KNOWN-ISSUE (release notes unless fixed first)

### PB-9 — The whole chain keys on a surface literally named `wing`, and the form never says so

`sloads/models/inputs.py:447-451` (`by_name` exact match), defaults `"wing"`
at `inputs.py:475, 575, 945` and `landing.py:508`. A fresh surface row is
seeded `name=""` with help "surface selector (standing ruling); structurally
required — SurfaceInput has no name-less form". Naming it `Wing` blocks
Structural Speeds, V-n, Wing / Fuselage / Tail / Aileron / Flap / Landing
Loads — 16 blocked notes across 8 pages on the reduced GA-6 — all saying
"add a 'wing' geometry surface" (some still naming a "Configuration & Layout
page" that no longer exists). Recoverable by renaming, so not blocking; fix by
seeding the first surface `wing`, matching case-insensitively, and saying so
in the help. Tier S — cheap enough to ride with PB-5.

### PB-10 — Gate G2's "page set equals `oracle_steps()`" is an AST proxy, not the shipped page set

`tests/test_oracle_gui.py:194-229` (`_derives_from`) returns true if *any*
attribute named `oracle_steps` is reachable from the `st.navigation` argument;
`:232` compares `workflow` with itself. Verified: `[s for s in
wf.oracle_steps() if s.module is not None]` (drops Aerodynamic Data) and
`list(_pages.values()) + [st.Page('app/views/loads_plots.py')]` both pass every
G2 test. The registered set is observable — after
`AppTest.from_file("oracle_app/Oracle.py").run()`,
`at.session_state[app_shell.nav.PAGES]` holds `{key: st.Page}` and equals
`oracle_step_keys()` today. Fix: assert that in
`test_the_oracle_entry_point_builds` (`:611`), keep the AST scan as the drift
hint. Tier S.

### PB-11 — Gate G8 / OG-10 discover GUIs by a module-level `set_page_config` and pin only `app/`

`tests/test_app_shell.py:51-75` (`_is_entrypoint`, `_gui_dirs`) and `:174`
(asserts `app` is found — not `oracle_app`). Wrapping `Oracle.py:41`'s call
in a helper silently removes `oracle_app` from G8 (`:221`), OG-10 (`:183`),
the lint-gate check (`:138`) and the back-import test (`:241`), all still
green. Fix: a literal expected set `{app, oracle_app}` and discovery that
cannot hide (any `set_page_config` call in the AST, or the `[project.scripts]`
launchers). Tier S.

### PB-12 — G1's unit-factor scan is two disjoint half-sets, neither covering `app_shell/`

`test_oracle_gui.py:105-106` (8 literals) and `tests/test_units.py:211-214`
(5 others; scans `sloads/`, `app/` only). `0.09290304` in `oracle_app/` or
`25.4` in `app_shell/components.py` — where the boundary conversion actually
lives — ships green; the docstring points at a `test_constants.py` scan that
does not exist. Fix: one literal set derived from `sloads.units`' own
constants, one scan over all four packages with `units.py` exempt. Tier S.

### PB-13 — G7 is exercised on one fixture in one unit system; two artifacts are never inspected

`test_oracle_gui.py:407-412` builds artifacts from `ga6_normal`, IMPERIAL.
There `one_engine_out` is blocked (zero artifacts — the per-page CSV test
passes over an empty loop) and `body_loads` has no conditions (no
`body_loads.csv` ever exists). Verified by hand that OEO's artifacts pass on
`atr42_100`/`dhc8_dash8` and SI passes on GA-6, so no defect today. Fix:
parametrise over `(example, system)` with a twin and SI, and assert every
page produced at least one artifact on at least one fixture. Also: for
`engine`, `cli.py:541` prints `text_report`, not `module_text_report`, so
G7's "byte equality with `cli.py`" is literally true of 21 of 22 modules.
Tier S.

### PB-14 — The schema-migration notice can never fire

`app_shell/project_state.py:103-117` (`apply_schema_check`) toasts
*"Migrated from schema N to 55"* when `schema_status()` says `older` — but
`io.load_project` / `project_from_dict` have already stamped
`schema_version = SCHEMA_VERSION`, so the GUI always sees `ok`. Verified:
loading the v41 DHC-8 example through the sidebar produces no toast. A user
opening a v41 file is never told it was upgraded and will be rewritten at
v55 on save. (The #52 disagreement warning *is* shown — it travels by
`warnings.warn`, not by the version stamp.) Fix: `io` returns the pre-hop
version alongside, or the shell reads it from the raw dict before building.
Tier S.

### PB-15 — Page-order dependencies silently change numbers already downloaded

Flap Loads (`requires=("speeds",)`) computes FAR 23.457(b) slipstream from
`engines`, entered on Engine Mount **two pages later**: in nav order the page
prints 12 rows and no *Slipstream factor*; after Engine Mount it prints 16.
Weight & Mass's WTESTIMA takes max-continuous hp from `Σ engines[].max_cont_hp`
once engines exist (`weight_estimate.py:268`), so the estimate the user
downloaded on page 2 (DHC-8: MTOW 42 325 lb) changes after page 12 (41 775
lb). Neither page says so. Fix: `requires`/`edits` that name `engines` where it
is read, or a results caption "reads `engines` — entered on Engine Mount, not
yet present". Tier S–M. (Not a G5 matter: the journey's second pass matches.)

### PB-16 — The shell's unit radio beats a loaded project's `unit_system` and dirties it on load

`app_shell/sidebar.py:50-72`: `st.radio(..., key="_unit_system_radio")` is not
generation-stamped, so its retained state wins over `index=`; loading an
SI-saved file into an Imperial session sets `project.unit_system="imperial"`
and shows *🟠 Unsaved changes* at once (reproduced with
`AppTest.from_file("oracle_app/Oracle.py")`). Fix:
`key=widget_key("_unit_system_radio")`. Tier S.

### PB-17 — The disabled `speeds.wing_area_sqft` copy shows the wrong governing value

`field_registry.py:647-649` names `geometry.parametric.wing_area_sqft` as the
owner and `form.py:449-454` displays it; but `structural_speeds._wing_area_sqft`
(`:204-216`) reads the *planform* area of the surface named `wing` and never
`parametric`. On `concept_regional_jet` the widget would show 500.0 while
STRSPEED uses 497.75; on a hand-typed project the two are unrelated. Its
`MissingInputError` also says "…or set `speeds.wing_area_sqft`", a widget
this GUI disables. Fix: `derived_from = EXTERNAL + "planform area of the
'wing' surface"` and show that number. Tier S.

### PB-18 — `_NOT_READY` reports a `ZeroDivisionError` as "cannot run yet", and the session disagrees with the reloaded file

`oracle_app/results.py:84, 163-164, 188-189`. Leave `aero_coeffs.cruise.stall_cl`
at 0 after typing `clmax_clean`: V-n, SELECT, Net Loads and TAILDIST all say
*"cannot run yet — float division by zero"*; save and reload, and
`AeroCoefficientsInput.__post_init__` (`inputs.py:723-740`) fills `stall_cl`, so
they run — the in-session project and its own file give different answers.
Fix: catch `MissingInputError` only (re-raise the rest), and run the
`__post_init__` derivation at persist time. Tier S.

### PB-19 — `weight.estimation.max_continuous_hp` is asked for and silently ignored

`weight_estimate.py:255-269` takes `Σ engines[].max_cont_hp` unless
`override_max_continuous_hp` (SLOADS, hidden) is set; `_copy_note`
(`form.py:148-149`) returns early for `EXTERNAL` owners, so nothing is
marked. Reproduced: typing 999 hp on the Weight page leaves the WTESTIMA
payload byte-identical once engines exist. A cousin of PB-15. Fix: mark the
external owner in the caption the way field owners are marked. Tier S.

### PB-20 — Optional overrides can never be cleared from this GUI

`form.py:493-494, 504-505`: `entered is None → return`, so once
`landing.gear_load_factor`, `speeds.chosen_vc/vd/…`, `aero.surfaces[].tau` or
`weight.envelope.mac` hold a value they cannot go back to "computed" without
hand-editing JSON — and this GUI has no editor. Fix: a cleared Optional widget
writes `None` through `_set_entered`. Tier S.

### PB-21 — A mid-entry planform crashes Wing Loads with a raw `IndexError`

A one-point leading or trailing edge — the state `render_curve` persists
after the first complete row — raises at `wing_geometry.py:98` /
`wing_inertia.py:157`, outside `_NOT_READY`, so the Wing Loads page shows a
traceback rather than a note; Geometry itself degrades gracefully. Fix: a
`MissingInputError` for fewer than two points. Tier S.

### PB-22 — Presentation: coefficients shown at four decimals, leaf-name labels, help that lies

`oracle_app/form.py:503, :542` (`format="%.4f"` on every float widget).
FLTLOADS' polynomial coefficients on the V-n page (GA-6 cruise moment
`0.004128`, lift `0.320479`) display as `0.0041` / `0.3205`. The stored value
is untouched (`_persist` equality), so this is display-only — but the persona
reads coefficients off the screen to check them against the manual. Fix:
`%g`, or a per-`FieldUnit` precision. Tier S.

**Labels.** `_field_label` prettifies the leaf name: *Elevator Te Down
(deg)*, *Xt25*, *Xv50*, *Fwd Regardless Pct MAC*, *Elevator Aft Hinge (ft²)*
(an area aft of the hinge). The help tooltip does name the program and the
path, which for this persona is most of the remedy; a small hand-declared
override table beside `MEMBER_LABELS` for the ~15 worst cases would finish it.

**Help that lies.** `flight_loads.mn`'s registry basis reads "FLTLOADS
gust/manoeuvre matrix" (`field_registry.py:706`) — it is the coefficient Mach
number (`inputs.py:834-836`), labelled *Mn*. Nits: *Chosen Vc (kt (EAS))*, the
`(project)` group caption on Engine Mount. Tier S for the lot.

### PB-23 — Sidebar and table nits

*"Saved: …"* is never seen (`st.success` then `st.rerun()`,
`sidebar.py:133-134`); a table row can only be removed from the end
(`form.py:689-692`, the count widget); clearing a required table cell silently
restores the old value (`form.py:771-772`). Tier S.

### PB-24 — Note 32 wording has drifted from the code (docs only)

OG-4 names `_has_unsaved_changes` / `_confirm_discard` / `_load_with_guard`
and `app/components.py` (now `app_shell/project_state.py` public names and
`app_shell/`); OG-8 and review 2026-08-20 §7's "not satisfied — OG-8" are
closed by note 33 DS-1 / #52 and guarded; G5/OG-C2 describe `supplied` as
"written without asking" while all 11 supplied paths are rendered widgets;
§2/§7 counts (323 / 219 / 230 on 35 groups) are now 297 / 199 / 210; G7's row
and §5 still cite the withdrawn OG-9. Tier S, with the cut's doc sweep.

---

## 3. The journey — what was done and what matched

| Page | Widgets typed (GA-6 / DHC-8) | Tables replayed | After all pages typed, vs the loaded example |
|---|---|---|---|
| Geometry | 67 / 70 | 5 / 7 | Configuration: CG source and tip-back differ (**PB-1**); Wing Geometry identical |
| Weight & Mass | 63 / 69 | 1 / 1 | WTESTIMA / WTONECG / WTENV identical (in nav order WTESTIMA differed until Engine Mount — **PB-15**) |
| Aerodynamic Data | 41 / 41 | 0 | no results page |
| Structural Speeds | 13 / 13 | 0 | identical |
| Flight Envelope (V-n) | 6 / 6 | 1 / 1 | identical |
| Wing Loads | 13 / 13 | 4 / 5 | NETLOADS case rows 15 vs 18 — the LRA torsion rows, a **declared** drop (`ref_axis_pct` is sloads'); station table, WINGINER, AIRLOADS identical |
| Fuselage Loads | 2 / 2 | 1 / 1 | **PB-2**: 96 vs 92 stations, 9 % of peak shear |
| Tail Loads | 0 | 0 | BALLOADS identical to 1 ulp (one *station error* value, 0.006848 vs 0.00685 in, from `wing_area_sqft` typed at the widget's four decimals); TAILDIST identical |
| Aileron / Flap / Tab | 4 / 6 / 1 | 0 / 0 / 1 (GA-6) | identical once engines exist (**PB-15** in nav order) |
| Engine Mount | 25 / 48 | 0 | GA-6 identical; DHC-8 **−16 %** torque / gyro (rotor rows, **PB-3**) |
| One Engine Out | 8 / 8 | 1 / 1 | GA-6 n/a (single); DHC-8 **blocked** (**PB-1**) |
| Landing Loads | 6 / 6 | 0 | identical |

Oracle-input paths that differ after everything is typed: three, all at the
widgets' display precision (`wing_area_sqft` 184.1211 vs 184.12113907866492,
`vtail_mac_in` 40.404 vs 40.403999999999996, one `zcg` 90.73 vs 90.73001) —
entry precision, not loss. Save → reload → re-run: every page's artifacts
bit-identical; `project_to_json` is a fixed point. Non-oracle paths that differ
(44 / 56): exactly the SLOADS fields — `component`, `consumable`,
`wing_fraction`, `ref_axis_pct`, gear `attach`/`carrier`/`weight_lb`,
`mounted_on`, rotors, `tail_type` — plus `mass`, which is the point of PB-1.

Browser calibration (Geometry, Weight, One Engine Out): the pages read as
the registry renders them — one subheader per record with its dotted path,
three scalars per row, composites beneath; the row-count widget creates rows
that open as expanders; a typed surface name persists (reproduced the
apparent loss seen once under automation — not the app's). The blocked
notes and the category line (*"FAR 23 category '(not set)'"* in a Geometry
download taken before Structural Speeds is entered) are honest.

---

## 4. Gates G1–G8 — rot re-check

| Gate | Verdict | Where it stands |
|---|---|---|
| G1 (no arithmetic / factors / CSV writer in `oracle_app/`) | HOLDS, caveat | allowlist + AST scan real; factor scan split and shell-blind (**PB-12**) |
| G2 (page set derived from `oracle_steps()`) | **ROT** | proxy satisfiable by a filtered list (**PB-10**) |
| G3 (`bas` names well-formed) | HOLDS | regex stricter than the note, over live `STEPS` |
| G4 (every field tagged) | HOLDS | walks the dataclass live; 297 paths = 297 rows |
| G5 (reduced input set reproduces the oracle) | **ROT** | the reduced project ≠ the oracle GUI's project; station tables uncompared (**PB-3**) |
| G6 (a project saved by either GUI loads in the other unchanged) | HOLDS | json round-trip on every example; all 22 `app/` views render the reduced GA-6 |
| G7 (every artifact states its basis / SF; one download call site) | HOLDS, caveat | reads payload bytes; single fixture and system (**PB-13**) |
| G8 / OG-10 (no shell symbol defined twice; one `set_page_config` per GUI) | **ROT** (discovery half) | `oracle_app` can silently leave the set (**PB-11**) |
| OG-7 marking, OG-11, OG-F (render never mutates) | HOLD | vacuity-guarded; AppTest snapshot diff over 14 pages × 6 examples |

---

## 5. Delta code review — `oracle_app/` + `app_shell/` since `4b1ddcc`

Read-only adversarial pass over `oracle_app/` (all four modules), `app_shell/`
(all six) and the `sloads/` entry points they call (`workflow`,
`field_registry`, `units.field_unit` / `unit_label`, `io`), with every
2026-08-20 Pass-A finding re-checked as *really fixed* rather than re-read.
Findings from this strand: PB-5, PB-6, PB-7, PB-8 (blocking); PB-9, PB-16 …
PB-23 (known). **Checked and fine:**

- All 14 pages render on an empty project and on all 6 examples, Imperial
  **and SI** — no exception, no mutation (the dirty-flag contract holds).
- CR-A-1's two-edit clobber is genuinely fixed: `_PENDING` keyed on
  `(id(owner), attr)`, chain commit correct for parent and child.
- CR-A-3: the `_set_entered` path, typed zeros, absent-stays-absent — real.
- SI round-trip: converted scalar, tuple and flat-table edits return exact
  Imperial; untouched values return the stored object (no drift on an idle
  rerun — verified under `AppTest` and by direct `_render_flat_table` call).
- `data_editor` identity includes the data bytes (Streamlit 1.58), so a
  persisted edit does not re-apply as a duplicate.
- Unit factors and labels for every kind (`lb-in²` → `kg·m²` …) correct;
  aviation-standard fields carry unsuffixed keys.
- Every project-seeded widget is generation-stamped (count, curve and table
  widgets included); download keys unique per page.
- CSV/text downloads and the on-screen tables share one converted path
  (`load_cases_csv(system=)`, `limit_csv`); ULT/LIMIT captions and
  `_LIMIT.csv` naming consistent; G7 reads the payload bytes.
- `_NOT_READY` catches `MissingInputError` (a `ValueError` subclass); zeroing
  every oracle scalar one at a time across all pages raised nothing uncaught
  (the planform case, PB-21, is a list, not a scalar).
- Upload goes through `project_from_dict` → `migrate`; the #34 edge trigger
  is present; the discard dialog's keys are fine.
- `oracle_steps()` derivation, `step_modules`, the `missing_upstream` /
  `missing_self_entered` split: correct; no step-key literal in `oracle_app/`.
- No concept switch on any oracle page; the applicability banner still shows.
- Results per page < 0.1 s on `atr42_100`: per-keystroke recompute is fine.

---

## 6. Coverage and what this review did not do

- **Not driven:** the `st.data_editor` grid by mouse (canvas; replayed through
  the renderer instead, which is the persist path the #35 tests also use);
  SI entry on the journey (G7's SI leg, the delta pass's SI render sweep and
  the `_to_imperial_kept` tests cover the round-trip; the oracle beta is
  Imperial-first); the Open-from-`projects/` path beyond the shipped listing;
  `app/`'s views (frozen; the shell findings PB-4, PB-6, PB-14, PB-16 apply
  to both GUIs by construction).
- **Not re-reported:** the 2026-08-20 MAJORs — each was checked to be really
  fixed on the journey and in the delta pass rather than re-read.
- **No code changed.** The journey harness is checked in as
  `scripts/oracle_journey.py`, a script and not a test; PB-3 proposes it
  become the test.

## 7. Disposition

**Before the cut — five passes, 0.7.0:**

1. **PB-1 + PB-2 + PB-3** as one pass (PB-3's corrected gate is what proves
   PB-1 and PB-2 closed; its residue — the rotors — is decided in the same
   pass). Tier M. PB-1's shape (derive-on-read vs an explicit Run) is the
   user's call before code.
2. **PB-5 + PB-8 + PB-9** — the form's selector and code fields: seeded,
   unique, enum-backed, `wing` matched case-insensitively. Tier S–M.
3. **PB-4** — the sidebar's download payload and dirty flag after the page.
   Tier S.
4. **PB-6** — a name widget, overwrite confirmation, filename sanitiser.
   Tier S.
5. **PB-7** — engine layout validated on the page; loader tolerant. Tier S.

**Release notes (filed for 0.7.x / 0.8.0):** PB-10 … PB-13 (gate rot, one
sweep — cheapest with pass 1 if it has room), PB-14, PB-15 + PB-19,
PB-16 + PB-17, PB-18 + PB-21, PB-20 + PB-23, PB-22, PB-24.
