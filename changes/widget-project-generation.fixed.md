- **A loaded project reaches the widgets, and stale widgets can no longer
  overwrite it (#51, the data-loss half of parked L-8d, tier M, 2026-08-21).**
  Streamlit widget state, once registered under a key, beats the `value=`
  argument on every later rerun, and both GUIs keyed widgets by something stable
  across projects — the registry path in `oracle_app/form.py`, a hand-written
  name in `app/views/`. `adopt()` replaced `st.session_state["project"]` and
  touched no widget key, so a page **visited before** a load kept rendering its
  own retained state and wrote it back over what had just been loaded: opening
  the oracle GUI on the seed project, visiting Weight & Mass Properties and
  loading `atr42_100` showed `0` / `""` / 0 rows, and the row-count widget's `0`
  popped all 21 `weight.items` and all 8 `weight.cg_cases` out of the loaded
  project — on the load's own rerun, since that GUI has no Apply step, and onto
  disk on the next Save. New `app_shell/widget_keys.py` stamps every such key
  with a **project generation**, bumped once per replacement (`adopt`, and the
  JSON editor's Apply, which replaces the project without saving it); a
  mutation, an Apply or a unit switch is not a replacement and keeps its
  widgets. Swept across all 21 `app/views/` modules (practice 4), where the
  Apply step defers the same overwrite rather than preventing it. Guards:
  `tests/test_widget_freshness.py` — render → load → re-render leaves the
  session project equal to the loaded file on every oracle page × every shipped
  example, the widgets show the loaded values, and an AST walk fails on any GUI
  widget keyed without the stamp.
