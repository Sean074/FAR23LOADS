- **The 0.8.0 band has its closure order, and `backlog_issues.py create` can
  no longer duplicate the table (tier S, 2026-08-26).** The 2026-08-26 re-cut
  (owner, in session) orders band B by fix dependency — #99, then #97 (the
  collapsed-override mechanism #95 consumes), #98, #95, #100's implementation,
  #94 (text last, against shipped mechanisms), #96 last so the guide captures
  finished pages — with #100's design note drafted first (rule 1); the table is
  renumbered densely; **#92 is ruled (b)**, re-aimed at CI's coverage leg (the
  local command already passes the clause's own thresholds); and the wing-fuel
  row, which had never had an issue behind its old "7a" ordinal, is filed as
  **#111** (milestone 1.0.0). The filing exposed that
  `.github/backlog_issue_map.json` still held only the original 20-issue
  migration keyed by pre-rewrite titles, so `create` re-opened the whole table
  as #101–#120: the 19 duplicates are closed with cross-references, the map is
  rebuilt keying every current row title to its real issue number, and
  `scripts/backlog_issues.py check` runs clean both ways.
