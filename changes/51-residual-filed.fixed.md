- **#51's residual scope filed, and the prose that overstated the shipped fix
  corrected (tier S, 2026-08-22).** The 2026-08-21 closure review of #51 found
  the project-generation stamp covers the *keyed* widgets only: 98
  project-seeded widgets in `app/views/` carry no `key=`, an unkeyed widget's
  Streamlit identity derives from its arguments (not per-render, as the guard
  assumed), and the stale-edit-survives-a-load defect still reproduces there.
  #51 is reopened with the full scope in its 2026-08-22 comment and a band-B
  backlog row (10a) riding the #44 unit-boundary rollout. Corrected in the
  same pass: the `widget_keys.py` / `project_state.adopt` docstrings now name
  both generation-bump sites (the JSON editor's Apply is the second), and
  parked L-8d's residual reads unkeyed-replacement *and* mutation, not
  mutation only.
