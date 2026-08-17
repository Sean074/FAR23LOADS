- **Solo scripts: `--suffix`/`--date` honoured, the expected fragment name printed, `gh` errors shown (issue #28, tier S, 2026-08-17).**
  Three things the first three closes taught: `solo_close.sh` now reads a
  `Pri N` and a date out of `--suffix` (and takes `--date`), so the close
  comment says "row N removed" and the commit date matches the fragment even
  when the fragment lead omits them; `solo_start.sh` prints the
  `changes/<slug>.<type>.md` name `solo_close.sh` will look for, so the branch
  slug and the fragment slug stop diverging (#7 and #26 both needed `--slug`);
  and both scripts surface `gh`'s own stderr instead of reporting "issue not
  found" on a GitHub 503. Guard: `tests/test_solo_scripts.py`. Closes #28.
