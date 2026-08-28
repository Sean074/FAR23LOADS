- **The §3.5 release smoke gate boots both front-ends, not just the first one
  (#127, tier S, 2026-08-28; production-release review §3.2).** `smoke_test.sh`
  started `app/Home.py` and nothing else, so the release whose headline
  deliverable is the oracle GUI had no hard gate that launched it under a real
  server. It now boots each front-end in turn through one `smoke_gui` function —
  identical terms, its own port, its own log — and the oracle GUI is started the
  way a user meets it, through the **`sloads-oracle` console script**
  `pyproject.toml` binds to `oracle:main` (falling back to `python oracle.py` in
  a checkout with no install, and saying which it took). That is the half the
  existing coverage missed: `AppTest` already reaches `Oracle.py`'s
  `set_page_config`, `st.navigation` and sidebar context manager in-process, and
  `test_the_launcher_points_at_the_entry_point` proves the path *resolves* — only
  a real boot proves the launcher launches. `RELEASE_PROCESS.md` §3.5 names both.
  The structural half lives in `tests/test_ci_conformance.py`, whose defect class
  this is (a documented setting differing from the live one in silence): the
  front-ends are **found**, not listed — every top-level `.py` that calls
  `st.set_page_config`, which is one per GUI — and the gate must boot every one
  of them and the checklist must name every one it boots. A third front-end
  joins the comparison by existing. Both guards verified to fail on a mutation.
