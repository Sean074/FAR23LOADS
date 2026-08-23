- **An engine layout that disagrees with the engine count no longer saves a
  file the loader refuses** (review 2026-08-22 PB-7, issue #66, tier S,
  2026-08-23). `Project.__post_init__` enforced `engine_layout.expected_count
  == len(engines)` at construction only, so the two widgets on the oracle
  Engine Mount page — set in either order — produced an in-session project
  that Save wrote and `project_from_dict` raised on: "Couldn't load …" in both
  GUIs, with no JSON editor in the oracle GUI to repair it. The rule is now
  asked, not enforced: `Project.engine_layout_problem()` is its one owner, the
  loader `warnings.warn`s it (shown as a toast by the shell's load path; the
  file loads and round-trips byte-identical), the oracle form withholds the
  page's results with the message naming the Engine Mount page, and WINGGEOM's
  wing-mounted engine stations — the one consumer that reads the layout —
  refuse by the same name. Guards in `tests/test_engine_layout_consistency.py`:
  the reproduction saved and reloaded with the warning, the refusal, the
  withheld page and its release once the two agree.
