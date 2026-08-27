# Oracle GUI User Guide — style and contents

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-26 (owner, in session — `CLAUDE.md` rule 1's
working-alone path). The four open questions were answered by the owner on
2026-08-25 as UG-9 … UG-12 (§8); the note carried them for a day still marked
PROPOSED, which is the state that blocked note 32's step OG-B and would have
blocked the first chapter here. Milestone: 0.8.0.** Nothing below is built yet.
This note settles the *shape* of the guide — where it lives, what a chapter looks like, where its
numbers and images come from, and what "done" means — so that writing fourteen
chapters is mechanical rather than fourteen separate judgement calls.

**Scope.** A page-by-page, illustrated user guide for the **oracle GUI**
(`oracle_app/`, design note 32) aimed at an engineer who knows aircraft
structures but has never seen this tool. It explains, for each of the fourteen
derived pages, *what is being asked for, why the original program needs it,
where the number comes from, and what the page gives back.* It is not a theory
manual (`20_theory/`) and not an architecture note (note 32).

Sources reviewed: `CLAUDE.md`, `docs/10_standard/GUI_USER_GUIDE.md`,
`docs/10_standard/GUI_design.md`, `docs/10_standard/DATA_DICTIONARY.md` +
`docs/generate_data_dict.py`, `docs/30_future/32_oracle_gui_note.md`,
`oracle_app/*.py`, `app_shell/*.py`, `sloads/workflow.py`,
`sloads/field_registry.py`, `examples/*.project.json`.

---

## 1. Decisions (UG-1 … UG-8)

| # | Decision | Rationale |
|---|---|---|
| **UG-1** | The guide is a **new docs section `docs/60_guide/`**, one markdown file per oracle page, plus front matter and appendices. Images in `docs/60_guide/img/`. | A 14-chapter illustrated guide is ~1500+ lines; one file per page keeps each chapter small, keeps image churn local, and lets a chapter be regenerated when its page changes. Renders on GitHub with no build step. |
| **UG-2** | The existing **`10_standard/GUI_USER_GUIDE.md` is not superseded**. It remains the task-oriented guide to the *full* `app/` GUI. The new guide cross-links to it for concept mode, exports and plots; it links back for "the original-suite-only interface". | Two front-ends, two audiences. Merging them would force every oracle reader past concept-mode material the oracle GUI cannot reach. |
| **UG-3** | Every chapter's **field table is generated**, not written: `docs/generate_data_dict.py` grows a per-page emitter driven by `sloads/field_registry.py` (path, quantity, units, type, `.BAS` origin), written to `docs/60_guide/_generated/<step_key>.md` and included by the chapter. Prose never restates a units string, a default, or a field count. | CLAUDE.md single-source rule; the field registry is already the owner. Prose explains *meaning*; the generator owns *values*. |
| **UG-4** | Screenshots are produced by a **re-runnable capture script**, `scripts/capture_guide_shots.py` (Playwright, dev-only extra), which loads a named example, walks the derived page set and writes deterministic PNGs. Committed to the repo. | Manual captures drift silently. A script makes "the GUI changed" a one-command refresh and makes staleness detectable. |
| **UG-5** | Both worked examples run through **every chapter**: `ga6_normal` (single, Appendix A oracle) and a **new FAR 23 light twin** example. Each chapter carries the same two callout blocks, in the same order, with the same headings. | The twin is what makes One Engine Out and the engine-mount pages meaningful; a guide that only ever shows a single leaves two chapters hollow. |
| **UG-6** | The new twin is a **normal/utility-category light twin under 12,500 lb** (Beech Baron 58 class), added as `examples/<name>.project.json`. It must be expressible **entirely within the oracle GUI** — no concept-mode field, no category-C cap relief. | The oracle GUI's declared scope is the original suite. Illustrating it with `dhc8_dash8` would document the tool operating outside the scope the tool advertises. |
| **UG-7** | Chapter order **is** `sloads.workflow.oracle_steps()` order, and chapter files are named `NN_<step_key>.md` with `NN` the position in that sequence. No hand-maintained chapter list — the index is generated from the same call. | Gate G2 in note 32 says adding a `bas` adds a page with no GUI edit; the guide inherits that property instead of undoing it. |
| **UG-8** | The guide states the **LIMIT vs ULTIMATE** contract once, in the front matter, and each chapter's *Results* section says only which of the two that page's blocks carry. | The contract has one owner (`CONVENTIONS.md`); repeating it fourteen times is fourteen chances to get it wrong. |

---

## 2. Contents

### Front matter (`docs/60_guide/`)

| File | Contents |
|---|---|
| `00_index.md` | What the oracle GUI is and is not; the fourteen chapters as a generated list; how to read a chapter; the two worked examples introduced side by side; link to `10_standard/GUI_USER_GUIDE.md` for the full app. |
| `01_getting_started.md` | Install, `.venv/bin/streamlit run oracle_app/Oracle.py` / `sloads-oracle`, the browser landing page. The **sidebar** in full: units toggle, open saved / open example / upload, the dirty indicator, save to disk, download. What a "project" is and that one file holds the whole airplane. |
| `02_before_you_start.md` | The data you should collect before opening the tool: three-view or GA drawing, weight statement, airfoil/aero data, speeds, gear geometry. A one-page **checklist**, keyed to the chapters that consume each item. |
| `03_conventions.md` | Axes and sign conventions (citing `CONVENTIONS.md`, not restating derivations), stations and reference datum, units and the Imperial/SI boundary, the **LIMIT vs ULTIMATE** rule (UG-8), and how to read a results table and a downloaded CSV. |

### The fourteen chapters

Order and `.BAS` attribution are the workflow's, not the author's:

| # | Chapter | Page | Programs |
|---|---|---|---|
| 1 | Geometry | `configuration_layout` | WINGGEOM |
| 2 | Weight & Mass Properties | `weight_mass` | WTESTIMA, WTONECG, WTENV |
| 3 | Aerodynamic Data | `aero_coefficients` | — (feeds the programs after it) |
| 4 | Structural Speeds | `structural_speeds` | STRSPEED, MACHLIM |
| 5 | Flight Envelope (V–n) | `flight_envelope` | FLTLOADS, SELECT |
| 6 | Wing Loads | `wing_loads` | AIRLOADS, WINGINER, NETLOADS |
| 7 | Fuselage Loads | `fuselage_loads` | NETLOADS |
| 8 | Tail Loads | `tail_loads` | TAILDIST, BALLOADS |
| 9 | Aileron Loads | `aileron_loads` | AILERON |
| 10 | Flap Loads | `flap_loads` | FLAPLOAD |
| 11 | Tab Loads | `tab_loads` | TABLOADS |
| 12 | Engine Mount | `engine_mount` | ENGLOADS |
| 13 | One Engine Out | `one_engine_out` | ONENGOUT |
| 14 | Landing Loads | `landing_loads` | LGFACTOR, LANDLOAD |

*(This table is illustrative in the note; in the guide it is generated — UG-7.)*

### Appendices

| File | Contents |
|---|---|
| `A_worked_single.md` | `ga6_normal` end to end in one continuous pass, with the Appendix A figures the run should reproduce and their page citations. |
| `B_worked_twin.md` | The new light twin end to end, emphasising what differs from the single: two engine mounts, One Engine Out, asymmetric cases. |
| `C_troubleshooting.md` | The "needs *x* — run the pages before this one first" message and what it means; "cannot run yet" module notes; unit-toggle surprises; where the dirty flag comes from. |
| `D_where_next.md` | What the full `app/` GUI adds (plots, sbeam export, workbook, report, concept mode) and when to move over. |

---

## 3. Chapter template

Every chapter is the same eight sections, in this order. A chapter that has
nothing to say in a section keeps the heading and says so in one line — a
uniform skeleton is what makes the guide navigable.

1. **What this page is for** — one paragraph, plain English, naming the original
   program(s) and what the original asked the user to type.
2. **Before this page** — the upstream pages whose output this one consumes, and
   what the page shows if they have not been run.
3. **The inputs** — the generated field table (UG-3), then prose grouped by the
   page's own record grouping: for each group, *what the quantity is*, *where an
   engineer gets the number* (drawing, weight statement, wind-tunnel/handbook,
   regulation), and *what a plausible value looks like*.
4. **Screenshots** — the page as the reader will see it, with the example
   loaded; one shot per input group where the group is non-trivial.
5. **Worked example — single (`ga6_normal`)** — the actual values typed on this
   page and why.
6. **Worked example — twin** — same, for the light twin.
7. **Results on this page** — the blocks the page renders, LIMIT or ULTIMATE
   (UG-8), the downloads offered, and how to sanity-check the numbers.
8. **Common mistakes** — the two or three ways this page is got wrong.

---

## 4. Style rules

- **Voice.** Second person, present tense, imperative for actions ("Enter the
  wing reference area"). Explain the engineering, never the Streamlit widget —
  "enter" not "type into the number input".
- **Length.** A chapter targets 150–350 lines including generated includes. A
  chapter running past that is a signal the page groups should become
  sub-sections, not that the limit should move.
- **Terminology.** The names the GUI shows, matched exactly to
  `oracle_app/labels.py`. Original program names in `CAPS`, code paths in
  backticks, regulation references as `14 CFR 23.xxx`.
- **Numbers.** No field default, units string, field count, coverage figure or
  "currently N" in prose (CLAUDE.md documentation-currency rule). Values appear
  only in generated tables and in the two worked examples, where they are the
  example's own data.
- **Citations.** Any statement of what the regulation or the manual requires
  cites the paragraph or the manual page. Physics rationale links
  `20_theory/00_theory_sources.md` rather than re-deriving.
- **Images.** Named `<NN>_<step_key>__<slug>.png`; light theme, fixed 1440×900
  viewport, the chapter's example loaded, no browser chrome. Every image has
  alt text stating what it shows. An image is used to disambiguate *where* and
  *what shape* — never as the only place a value or an instruction appears.
- **Cross-links.** Relative paths, and every link resolves inside the repo.

---

## 5. Tooling to be built

| Item | Where | Note |
|---|---|---|
| Per-page field-table emitter | `docs/generate_data_dict.py` | New output tree `docs/60_guide/_generated/`; the existing data dictionary is unchanged. |
| Screenshot capture | `scripts/capture_guide_shots.py` | Playwright, added as a `dev` extra; takes an example name and a step key, or walks all. |
| Light-twin example | `examples/<name>.project.json` | Must load, must run all fourteen pages, must use no concept-mode field. |

---

## 6. Acceptance gates

| Gate | Statement |
|---|---|
| **G-UG-1** | Every step in `sloads.workflow.oracle_steps()` has exactly one chapter file, and every chapter file maps to a step. Guard test. |
| **G-UG-2** | No generated file under `docs/60_guide/_generated/` is hand-edited; regenerating produces no diff. Guard test, as for `DATA_DICTIONARY.md`. |
| **G-UG-3** | Every image referenced by a chapter exists, and every image in `img/` is referenced. Guard test. |
| **G-UG-4** | Both worked examples load and every oracle module they reach runs without error. Extends the existing example smoke test. |
| **G-UG-5** | Every relative link in `docs/60_guide/` resolves. Guard test. |
| **G-UG-6** | Each chapter contains the eight template headings, in order. Guard test — this is what keeps chapter fourteen as complete as chapter one. |

---

## 7. Closure tier

**Tier M.** Docs alone would be tier S, but this ships a generator change, a new
example project and six guard tests, and it changes what `docs/00_INDEX.md`
declares the tree to contain. Closure therefore needs the `changes/` fragment,
the `00_INDEX.md` / `GUI_USER_GUIDE.md` cross-reference updates, and a
one-paragraph history fragment.

---

## 8. Answers to the open questions (UG-9 … UG-12)

*Resolved by the owner 2026-08-25. These are decisions, on the same footing as
UG-1 … UG-8; §6's gates apply to them.*

### UG-9 — The twin is a **Beech Baron 58**, `examples/baron_58.project.json`

Chosen on four grounds, in order of weight:

1. **Engine-data continuity.** The Baron 58 flies Continental **IO-550-C** —
   the same family as the IO-520 already carried by `ga6_normal` and
   `cessna_210`. Engine weight, mounting and torque provenance is reused rather
   than freshly sourced, and chapter 12 can point the reader at how the single's
   engine block differs from the twin's.
2. **Public certification data.** A Type Certificate Data Sheet gives MTOW,
   category, speeds and CG range with a citable authority, which is what the
   guide's numbers must have — a walkthrough whose inputs are unattributable is
   not a worked example, it is a demonstration.
3. **It exercises the pages that need a twin.** Wing-mounted engines either side
   of the centreline make ENGLOADS and ONENGOUT (chapters 12–13) real rather
   than degenerate, and retractable gear makes LGFACTOR/LANDLOAD (chapter 14)
   more than a fixed-gear special case.
4. **Comfortably inside the oracle scope (UG-6).** Normal category, MTOW well
   under 12,500 lb, piston, unpressurised in the sense that matters here — no
   field of the example needs anything the oracle GUI does not expose.

Rejected: *Piper PA-34 Seneca* (counter-rotating installation adds an
explanation the guide does not need in its first twin), *Beech Duchess 76*
(thinner published structural data), *Cessna 310* (would pair neatly with
`cessna_210`, but the IO-550 continuity above outweighs the naming symmetry).

**Construction rule.** Every field of the example is sourced from published
certification or handbook data and cited in the example's own header comment or
accompanying note. Anything not published — mass distribution detail, mount
geometry, hinge-moment coefficients — is **estimated, marked as estimated, and
never presented in the guide as the airplane's certified value.** The example
exists to teach the tool, and the guide says so where an estimate is load-bearing.

### UG-10 — Staged delivery, gates first

Six PRs, in this order:

| PR | Contents | Why here |
|---|---|---|
| 1 | Tooling + scaffolding: the per-page emitter, `capture_guide_shots.py`, `docs/60_guide/` skeleton, **all six gates from §6** | Gates that land first check every chapter on arrival; gates that land last are a retrofit that finds fourteen problems at once. |
| 2 | `examples/baron_58.project.json` + its smoke coverage (G-UG-4) | The twin must run before any chapter can quote it. |
| 3 | Front matter (`00`–`03`) + appendix `C_troubleshooting.md` | Establishes the voice, the conventions and the LIMIT/ULTIMATE statement that all fourteen chapters lean on (UG-8). |
| 4 | Chapters 1–5 | The seed chain's head: geometry → weight → aero → speeds → envelope. |
| 5 | Chapters 6–11 | The distributed-load and control-surface pages, which consume PR 4's output. |
| 6 | Chapters 12–14 + appendices `A`, `B`, `D`, `00_INDEX.md` cross-links, tier-M closure | The walkthrough appendices can only be finalised once every chapter's example values exist. |

The batches follow the **workflow dependency order, not convenience**: a
chapter's worked-example values are the values the pages before it produced, so
writing chapter 6 before chapter 5 means inventing numbers that the tool will
later contradict.

### UG-11 — Chapter 3 states the requirement and teaches *sourcing*, not aerodynamics

The guide does **not** teach how to estimate aerodynamic coefficients. It does
teach, for each coefficient the page asks for, a four-part entry:

1. **What it is** — one sentence, and the sign convention it must be given in
   (citing `CONVENTIONS.md`).
2. **Where it comes from** — a ladder: measured/test data → published handbook
   or standard method (DATCOM, Roskam, the airfoil's own data) → a defensible
   estimate. The guide names the method; it does not reproduce it.
3. **What it drives** — which downstream chapters' loads move when this number
   moves. This is the part a reader cannot get from the theory sources, and it
   is the reason chapter 3 exists as prose rather than as a bare table.
4. **Sanity check** — the sign, and whether the magnitude is plausible.

Derivations and equation provenance stay in `20_theory/00_theory_sources.md`,
linked. Both worked examples give their own coefficient values with their source
named, per UG-9's construction rule.

### UG-12 — One example per unit channel: the single Imperial, the twin SI

*Revised by the owner 2026-08-25, replacing an Imperial-throughout proposal.*

- **`ga6_normal` (single) is Imperial.** It is the Appendix A oracle case, and a
  reader cross-checking it must see the same number on the page as in the book.
  Converting the one example whose whole purpose is comparison against a printed
  figure would defeat it.
- **`baron_58` (twin) is SI.** Every chapter's twin block, and the whole of
  `B_worked_twin.md`, is entered and read in SI. A guide that never leaves one
  channel teaches the reader nothing about the unit boundary except that it
  exists; running an entire airplane through in SI proves it.
- **The twin's published data is Imperial, and the guide says so.** That is not
  an awkwardness to hide — it is the actual situation of a metric user working
  from US certification data, and appendix B shows the conversion happening at
  the point of entry rather than in a spreadsheet beforehand.
- **Appendix B closes on the channel itself.** It ends by reopening the saved
  project in Imperial and showing the same loads — the demonstration that the
  toggle is a display boundary and the stored project is channel-free. This is a
  reader-visible statement of what `tests/` already guards, not a new claim.
- **Screenshots follow the example, not a fixed channel.** A chapter's shots come
  from the single in Imperial by default; from the twin in SI where the twin is
  the substance of the page (chapters 12 and 13, and any page whose twin content
  differs structurally). `capture_guide_shots.py` therefore takes an example and
  a channel, and `01_getting_started.md` shows the toggle with one before/after
  pair.

**Consequence for UG-9.** The twin being the SI case slightly weakens the
US-airplane choice on presentation grounds — a European CS-23 twin (DA42,
P2006T) would come with metric source data. The Baron stays: the IO-550
engine-data continuity with the two existing singles is the stronger argument,
and entering Imperial-sourced data in SI is the case worth teaching.
