- **The deprecated `use_container_width` is gone from both front-ends, and the
  Streamlit requirement now states both a floor and a ceiling policy (#129,
  tier S, 2026-08-28; production-release review §3.7, owner ruling §5.4).**
  73 call sites migrated to `width="stretch"` — 62 in `app/views/`, 11 in
  `app_shell/` (`sidebar.py` ×7, `project_state.py` ×4) — taken **whole**
  rather than by GUI, because upstream documents the parameter as *"deprecated
  and will be removed in a future release"* and the release that removes it
  breaks Open / Save / Download / Build-results-zip in *both* GUIs at once, on
  a fresh install, with no version constraint to stop it. The migration also
  closed the mirror-image gap: four `width="stretch"` sites had already shipped
  against a `streamlit` floor set years earlier for `st.navigation(expanded=…)`,
  so a resolver honouring the declared floor would have raised on an unexpected
  keyword. The floor now names the API the code actually calls — `width=`
  arrived per element upstream (buttons, then `st.dataframe`/`st.data_editor`,
  then `st.plotly_chart`), and the last of those is the binding one. **No upper
  bound, stated as a decision rather than left as an omission**
  (`pyproject.toml`, `00_program_overview.md` §Dependency requirements): CI
  installs the runtime set unpinned on every run, so an upstream removal fails
  the GUI tests here before it reaches an installed user. Three guards
  (practice 3): no front-end file may pass `use_container_width` (AST-derived
  over every GUI package plus the shell, so a third front-end is covered the
  day it lands); the declared floor must admit the layout parameter the
  front-ends pass; and CI's install must stay unpinned and unconstrained, since
  the ceiling policy rests on it. Each verified by mutation — reinstating the
  old spelling, lowering the floor, and constraining the CI install each fail
  their own guard. No behaviour change: `width="stretch"` is the documented
  equivalent of `use_container_width=True`.
