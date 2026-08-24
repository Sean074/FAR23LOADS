- **Every oracle page with a grid says that a part-filled row is not saved (C210 build review, tier S, 2026-08-23).**
  A grid row with an empty cell is deliberately held out of the project, which is
  invisible until the row vanishes on a rerun. Asked for by the owner mid-build:
  pages that render a `st.data_editor` now carry one caption ("fill every column to
  keep the row"), derived from the page's field set, absent on grid-less pages. The
  hint briefly also warned that Enter could drop an entry — that symptom was the
  C210-4 remount race (see the stable-frame fix in this release) and the warning
  came back out once the fix removed it. Guard:
  `tests/test_oracle_gui.py::test_grid_pages_carry_the_commit_hint`.
