# `changes/` — changelog fragments

One small file per closed item, instead of an edit to the 5,000-line
`CHANGELOG.md`. This is the **only** way `[Unreleased]` content is written
(design note `docs/30_future/26_doc_volume_reduction_note.md`, 2026-08-16).

## Writing a fragment

File name: `<slug>.<type>.md`

- `slug` — short kebab-case identity of the change (`gear-csv-ult-marker`,
  `step-14-pbar-passthrough`, `r6-d5-tree-guard`). Lower-case letters, digits,
  hyphens.
- `type` — one of `breaking`, `added`, `changed`, `fixed`, `removed`. This
  selects the `### Breaking` / `### Added` / … subsection at build time.

File body: one or more Markdown bullets, **exactly** as they should appear in
`CHANGELOG.md` — start with `- `, bold lead phrase, tier and date in the lead,
cite the design note / backlog row / review ID as the project already does:

```markdown
- **Gear report CSV meets the load-output contract (R6-C2, tier M, 2026-08-16).**
  `-ULT` markers on every load column, an `SF` column per case, …
```

Multi-paragraph bullets are fine (indent continuation lines two spaces).

## Building the changelog (release cut only — `RELEASE_PROCESS.md` §4)

```bash
.venv/bin/python scripts/build_changelog.py --dry-run          # preview the section
.venv/bin/python scripts/build_changelog.py 0.6.0 --date 2026-08-20
```

The builder merges every fragment into the existing `[Unreleased]` body by
subsection (fragments first, then any legacy hand-written text), renames the
heading to `## [0.6.0] — 2026-08-20`, opens a fresh empty `[Unreleased]`, and
deletes the consumed fragments. Nothing else in `CHANGELOG.md` is touched.

## Guard

`tests/test_changelog_fragments.py` fails on a mis-named fragment or a body
that is not a bullet, and warns when the live history file passes its size
threshold. `README.md` is the only non-fragment file allowed here.
