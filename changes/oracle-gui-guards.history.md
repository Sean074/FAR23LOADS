- **Before parametrizing a guard over a second target, check that it can fail there (design note 32 step OG-F, tier M, 2026-08-20)** —
  OG-9 was one of the better decisions in note 32. It spotted, before the second
  GUI existed, that `tests/test_ultimate_contract.py` and
  `tests/test_page_links.py` both hardcode `app/views/`, so a second front-end
  would be invisible to them and could ship an unmarked LIMIT CSV or a broken
  link with CI green. The diagnosis was right twice over. The remedy — run the
  same guards over both directories — turned out to be wrong twice over, and for
  the same reason each time: **both guards work by finding something in
  `app/views/*.py`, and the oracle GUI has no views.** OG-E had already found
  the first half: the ultimate-contract scan matches a literal
  `file_name="….csv"`, the oracle GUI computes its filenames, so the
  parametrized case would have found nothing, passed, and reported the second
  GUI as covered. The page-link half fails the same way and one worse: its first
  assertion is that `app/views/<key>.py` exists for every step key, which is
  false by construction for a GUI whose pages are callables, and its second
  scans for `workflow_page_link` calls the oracle GUI does not make. One wrong
  failure, one meaningless pass. OG-9 is withdrawn in full.
  What replaced it is not another scan. `workflow_page_link` no longer builds a
  path: it asks `app_shell/nav.py` for the running GUI's own page object, which
  each entry point registers as it builds its navigation. A link cannot name a
  page that does not exist because it never names a page at all — it names a
  workflow step, and the GUI that is running answers. That also removes the last
  `app/`-shaped fact from the shared shell, which is what OG-B was for.
  The sweep's real prize was somewhere else entirely, and finding it is the part
  worth keeping. Of the seventeen test files that hardcode `app/views`, most are
  legitimately per-view tests, and one states a **contract both GUIs owe**:
  `test_dirty_flag.py`'s "a render pass must not mutate the project" (M2-3,
  review G4). Its mechanism transfers, because it drives a page and compares the
  project before and after — and it does not care how the page was built.
  Pointed at the oracle GUI it failed at once, on nine of fourteen pages with
  the fully-populated oracle fixture. Three defects, each a consequence of the
  thing that makes the second GUI good: it is generic. It created a record so
  its widgets had somewhere to write, and attached it whether or not anything
  was written. It wrote back every field it rendered, so a JSON `45` became
  `45.0` — the same number, a different file, an "Unsaved changes" flag nobody
  earned. And in SI it converted each value out and straight back, so `116 in`
  returned as `115.99999999999999`: an SI user's geometry drifted on every
  rerun, which is the rounding trap `app/` had already paid for once and solved
  inside `unit_number_input`, where the composite and table widgets that convert
  for themselves never saw the fix.
  Two lessons, and the second is the one that generalises. First: a guard that
  reaches only one of two implementations is not a guard, it is a note about the
  one it reaches. Second: **the value of a guard on a new target is exactly its
  ability to fail there.** OG-9 proposed two guards that could not fail on the
  oracle GUI and did not propose the one that could. Ranking a sweep by which
  assertions can actually break is a better filter than ranking it by which
  files mention the directory.
