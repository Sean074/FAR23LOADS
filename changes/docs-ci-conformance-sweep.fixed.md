- **A documented git or CI setting can no longer differ from the live one in
  silence (CR-D-4…D-8, CR-D-11, issue #46, tier S, 2026-08-25).** Six doc/CI
  conformance findings from the 2026-08-20 critical review, closed together
  because they are one class: a rule stated in prose, with nothing comparing it
  to the thing it describes.
- **The CI matrix is asymmetric, and now says so everywhere it is described.**
  `ci.yml` runs 3.12 alone on every pull request and every `dev/**` push; the
  3.9 / 3.11 legs, `sbeam-roundtrip (3.11)` and the coverage-instrumented leg
  run only on the push to `main`, so **a change that breaks 3.9 merges green by
  design**. `README.md`, `CLAUDE.md` and `00_program_overview.md` (§Testing and
  §Coverage floor) all stated the full matrix with no caveat. Worse,
  `DEVELOPMENT_PROCESS.md` §2 listed six required status checks, three of which
  a pull request never produces — a required check that never reports blocks its
  PR forever — while §0's table on the same page named the correct three.
  Corrected to the live fast gate, with the reason the other three cannot be
  required.
- **Two new guards make it structural, in two hops** (`tests/test_ci_conformance.py`,
  `.github/branch-protection.json`, `scripts/branch_protection_snapshot.py`).
  Hop 1 always runs and needs no network: every required check in the snapshot
  must be one `ci.yml` actually reports on a PR; the process docs must name that
  set; and no doc may assert "merge commits allowed", "linear history off" or
  `git merge main` outside a quotation or a retraction — the wording that made
  the 0.7.2 milestone PR unmergeable at the cut. Hop 2 is
  `branch_protection_snapshot.py --check`, which reads GitHub and is run by the
  owner (added to the `RELEASE_PROCESS.md` §3.1 checklist). The split is
  deliberate: CI has no `gh` credential, and a gate that needs a credential CI
  lacks is a gate that silently skips — which is the defect class being closed.
- **The nav guard cuts both ways, and the user guide's phase table is derived.**
  `test_every_view_file_is_a_workflow_step` closes CR-D-8: a stray
  `app/views/foo.py` never entered nav, still passed the smoke suite, and no
  guard failed — a page could exist, be tested, and be unreachable forever.
  `GUI_USER_GUIDE.md` §2's phase table is now asserted against `workflow.py`
  (CR-D-7) and was wrong in two places: Aircraft Comparison was filed under
  Load-case plotting where the graph puts it in Export, and the Flight-loads row
  omitted **Tail Span Loads** and **Balanced Cases** — the two pages carrying the
  mission's primary distributed deliverable.
- **`pyproject.toml` owns every version floor; the overview names none** (CR-D-5).
  It had carried a `streamlit` floor six minor versions below the real one, which
  exists because of `st.navigation(expanded=…)`. `test_doc_currency.py` gains a
  volatile pattern for a version specifier beside a dependency name, so the class
  is visible to the guard that was already meant to catch it.
- **`cspell.json` is an editor convenience, and the prose rule that pretended
  otherwise is gone** (CR-D-11). "New domain terms → `cspell.json`" was a
  convention with no gate — the shape rule 3 forbids. Given the choice between
  adding a gate and dropping the rule, the rule went.
- **The suite-runtime clause stops asserting a number it cannot hold** (CR-D-6).
  §Testing claimed "the suite in the tens of seconds and no test over ten"
  against a measured parallel suite several times that, with its own revisit
  thresholds crossed and nothing filed. It now points at `--durations` output,
  and the work the clause asks for — splitting the whole-pipeline-per-assertion
  tests — is filed as its own backlog row rather than left as a standing claim.
- **`backlog_issues.py check` compares a row's band with its issue's milestone.**
  The second instance of the same class, found the same day: #71 sat open on the
  already-cut **0.7.1** while its row was in the 0.8.0 band, and no gate saw it —
  the check proved row ↔ open-issue correspondence both ways but never requested
  `milestone`. It now does, and the expected milestone is read from **the band
  header's own text** rather than a hardcoded letter map, because the letters
  move at every re-cut: band A retired when 0.7.2 was cut, making B the milestone
  in flight. An issue parked on a milestone `CHANGELOG.md` shows as already cut
  is reported too, since every cut milestone in this repository is still `open`
  on GitHub and that state carries no information.
- **Two parser defects found building that check, both pinned by tests.**
  `BAND_ROW` matched a single letter (`^\|\s*\*\*([A-Z])\s+`), so the **B2**
  header added by the 2026-08-24 re-cut never matched and every 0.9.0 row
  inherited `band:B` — the 0.8.0 label. The band is exactly what the new
  milestone check compares, so it could not have worked. And a row's issue was
  read from the whole table line, so the "(#29)" that band D's function-size row
  cites in its *What ships* cell was taken as that row's identity, putting the
  single band-B2 row under band D: a guard reporting a fault against the row it
  had misread. `row_ref` now reads the **Item** cell alone.
