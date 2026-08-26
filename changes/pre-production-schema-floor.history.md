## Step #93 — Pre-production schema floor: read only the current `SCHEMA_VERSION` (tier L, 2026-08-25)

**Objective.** Stop carrying compatibility this project does not need. `sloads/migrations.py`
migrated any file from v18 up through twelve shape hops, plus a v0 bare-`EngineInput` branch —
632 lines of code and 439 of test guarding the ability to read files written by builds that
never shipped to anyone. Pre-production, no prior analysis has to stay readable. The floor
moves to the current version and everything below it goes; the hop *machinery* stays, empty,
so the first post-production shape change registers a hop unchanged.

The item was raised by the owner at the close of #68, which had just fixed the GUI's migration
notice. That fix is what surfaced this: the notice could only ever have fired on the six
bundled examples, which had sat at v41 for fourteen versions and ran hops 43, 46 and 54 in
memory on every load. The repo's own fixtures were the only prior-schema files in existence.

**Deliverables.**

- **The examples re-stamped at v55, first, through the chain still standing.** `migrate(raw)`
  written back at the same `indent=2`, so the diff is only what the hops touch (16–111 lines
  per file, nearly all the v46 cg-case reshape) and the hand-authored key order survives.
- **`migrations.py` rewritten as a gate.** `MIGRATIONS = {}`, `SUPPORTED_FLOOR =
  SCHEMA_VERSION`, and `migrate` raising the new `SchemaVersionError` — a `ValueError`, so it
  lands in the documented error contract and every front-end's existing load handling reports
  it with no new branch — for anything older, newer or unversioned, naming both versions.
  `source_schema_version` moved here from `io.py` and now answers `-1` for an unversioned
  dict rather than defaulting it to the floor: an unstamped dict is not an old project file,
  it is one nobody wrote as a project file, and the gate has to be able to say so.
- **One decider.** The gate sits inside `io.project_from_dict`, the funnel CLI, both GUIs and
  every test load through. `io.schema_status`, `app_shell.project_state.apply_schema_check`
  and the JSON editor's copy of the same classification are deleted; `safe_load` keeps the
  dict-reader signature #68 gave it and reports the refusal through the error path it already
  had. `read_project_dict` stays — that split was right for its own reasons.
- **The v0 bare-engine branch and `is_project_dict` retired.** A dict with no
  `schema_version` is refused by the gate, which discriminates a foreign file better than the
  key-set intersection did, and the reader no longer makes the distinction at all.
- **Eleven frozen legacy fixtures deleted**, leaving `tests/fixtures_schema/v55_current.json`.
  The tests that read them were re-homed rather than dropped where the property under test
  outlived the hop: the fuselage-outline defaulting, the empennage slice properties and the
  absent-`unit_system`-is-Imperial rule are now written against current-schema dicts, because
  none of them was ever about the vintage.
- **Docs.** `PROJECT_GUIDE.md` §5 (the rule, and what changing a persisted dataclass now
  requires), `00_program_overview.md`'s error-handling table, `GUI_design.md` §10's load path,
  `CONVENTIONS.md`'s SSOT row for the two twice-persisted quantities (its guard cited a hop
  test that no longer exists), `PROGRAM_SPEC.md`'s cg-case note, and the fields-hash
  tripwire's own failure message, which told the next developer to write a hop.

**Test / Acceptance.**

- Output-neutrality of the re-stamp proved two ways before anything was deleted: the `Project`
  loaded from each pre-regeneration file and from its replacement are **identical dicts**, all
  six fixtures; and `tests/fixtures_imperial/digests.json` — every deliverable channel of every
  example — did not move. Decision **G-3b**'s own guard (the `FLIGHT`-tagged set equals the
  pre-hop `flight_loads.cg_cases`) was re-run against the pre-regeneration files and passed on
  all six, flight and ground, then retired with the hop it guarded.
- **New structural guard (rule 3):**
  `test_schema_guards.py::test_every_bundled_example_is_written_at_the_current_version`, read
  off **disk** rather than off a loaded `Project` — asking the built object is precisely the
  #68 defect and would make the test vacuous exactly when it matters. Mutation-tested by
  re-stamping an example at 41.
- **Second structural guard:** `test_app_shell.py::test_no_gui_decides_whether_a_file_is_readable`,
  an AST walk for the names that do the deciding (`schema_status`, `source_schema_version`,
  `SCHEMA_VERSION`, `SUPPORTED_FLOOR`, `migrate`, `MIGRATIONS`) anywhere under a GUI or the
  shell. Reading `project.schema_version` to *display* it, as the dashboard metric does, is
  not deciding and is not flagged. Mutation-tested by importing `SCHEMA_VERSION` into
  `app_shell/project_state.py`.
- `test_migrations.py` rewritten as the gate's tests: refusal in both directions and for an
  unversioned dict, the string-version trap, the refusal reaching a front-end through
  `project_from_dict`, and — so the kept machinery is not decorative —
  `test_a_registered_hop_still_runs`, which registers a hop, watches it fire, and unregisters
  it.
- Whole suite green; net ~1,100 lines removed.

**Key decisions.**

1. **Refuse, do not warn, in both directions.** The old chain let a *newer* file through on
   "read what you understand". Pre-production that means presenting a partial read of another
   build's schema as this build's answer, which is the same dishonesty as silently upgrading
   an old one.
2. **Keep the chain, empty.** Deleting the mechanism and rebuilding it from git history at
   production would be a second design exercise for no saving; `MIGRATIONS` and `applied_hops`
   cost nothing standing still, and the reversal is two edits — lower the floor, register the
   hops.
3. **The examples are the floor's only customers, so the guard is on the examples.** With
   `SUPPORTED_FLOOR == SCHEMA_VERSION`, a stale example is not a compatibility question but a
   broken example: the app would refuse to open its own bundled projects. That test is what
   makes the next version bump safe.
4. **The retired hops are recorded, not merely deleted.** The archaeology table that
   reconstructed which schema version each legacy path belonged to (M4-10) stays in
   `docs/40_history/11_completed_development_to_0.5.0.md`, and `migrations.py`'s docstring
   points at it.
