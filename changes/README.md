# `changes/` — changelog fragments

One small file per closed item, instead of an edit to the 5,000-line
`CHANGELOG.md`. This is the **only** way `[Unreleased]` content is written
(design note `docs/30_future/26_doc_volume_reduction_note.md`, 2026-08-16).

## Writing a fragment

File name: `<slug>.<type>.md`

- `slug` — short kebab-case identity of the change (`gear-csv-ult-marker`,
  `step-14-pbar-passthrough`, `r6-d5-tree-guard`). Lower-case letters, digits,
  hyphens.
- `type` — one of `breaking`, `added`, `changed`, `fixed`, `removed` (a
  changelog bullet; selects the `### Breaking` / `### Added` / … subsection at
  build time) **or `history`** (design note 28 MD-4: the tier-M paragraph or
  tier-L full-step entry for `docs/40_history/00_completed_development.md`,
  rolled to the top of that file at release cut, newest first). A tier-M/L
  closure therefore writes **two** fragments: `<slug>.<type>.md` and
  `<slug>.history.md`; tier S writes one.

File body (changelog types): one or more Markdown bullets, **exactly** as they should appear in
`CHANGELOG.md` — start with `- `, bold lead phrase, tier and date in the lead,
cite the design note / backlog row / review ID as the project already does:

```markdown
- **Gear report CSV meets the load-output contract (R6-C2, tier M, 2026-08-16).**
  `-ULT` markers on every load column, an `SF` column per case, …
```

Multi-paragraph bullets are fine (indent continuation lines two spaces).

File body (`history`): a tier-M paragraph starting `- **Title (…, tier M, date)** —`
or a tier-L step starting `## Step N — …` / `**Step N — …**` in the history
file's step format (Objective / Deliverables / Test / Key decisions).

## Building the changelog (release cut only — `RELEASE_PROCESS.md` §4)

```bash
.venv/bin/python scripts/build_changelog.py --dry-run          # preview the section
.venv/bin/python scripts/build_changelog.py 0.6.0 --date 2026-08-20
```

The builder merges every changelog fragment into the existing `[Unreleased]`
body by subsection (fragments first, then any legacy hand-written text), renames
the heading to `## [0.6.0] — 2026-08-20`, opens a fresh empty `[Unreleased]`,
inserts every `*.history.md` entry directly under the history file's header
rule (the live cycle below is byte-identical), and deletes the consumed
fragments. Nothing else in either file is touched. Until the cut, `ls changes/`
*is* the release's history.

## Guard

`tests/test_changelog_fragments.py` fails on a mis-named fragment or a body
that is not a bullet, and warns when the live history file passes its size
threshold. `README.md` is the only non-fragment file allowed here.
