- **Design note 32 described a GUI that had moved on** (PB-24, issue #74, tier S,
  2026-08-25). The oracle-GUI note is a live plan, not a historic record, and six
  of its statements no longer matched the code it plans: OG-4 named
  `_has_unsaved_changes` / `_confirm_discard` / `_load_with_guard` in
  `app/components.py`, which shipped as the public `app_shell/project_state.py`
  API; OG-8's gear-duplication prerequisite was closed by note 33 DS-1 / #52 and
  guarded, and both it and review 2026-08-20 §7's "not satisfied" now say so;
  gate G7's *statement* still promised "the parametrized ultimate-contract scan"
  and §5 still leaned on it, although OG-9 — the item that would have built it —
  was withdrawn in full on 2026-08-20 and the gate as shipped reads the payload
  bytes instead.
- **`supplied` was documented as a field written behind the user's back** (PB-24,
  #74, tier S, 2026-08-25). Note 32's G5 row, the registry's own comment, its
  `supplied_paths` docstring and two test docstrings all read "a field the oracle
  GUI *writes* without asking" — and all thirteen supplied paths are rendered
  widgets the user can see and change. Several are *seeded* with a meaningful
  default rather than left empty (a surface name, a CG case's role), which is
  where the reading came from, but seeding a field the user then edits is not
  writing it behind their back, and a mark documented that way invites a GUI that
  hides them. Corrected in all five places.
- **Every field count in note 32 was a present-tense claim about a moving
  number** (PB-24, #74, tier S, 2026-08-25). The registry has been 323 fields /
  219 `ORIGINAL` / 11 supplied and 230 fields on 35 groups since 2026-08-19; it
  is 297 / 199 / 13 and 212 on 34 groups today, and the oracle page count went
  from 13 to 14 with nothing noticing. Each measurement now carries the date it
  was taken, the section that leans on them carries a one-line recount command,
  and the live page count points at its owner (`workflow.oracle_step_keys()`) and
  the guard that holds it — rather than being re-frozen at a value that will
  drift again.
