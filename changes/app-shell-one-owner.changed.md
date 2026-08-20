- **The app-layer shell has one owner: `app_shell/` (design note 32 step OG-B, tier L, 2026-08-19).**
  The Streamlit code shared by every sloads front-end moves out of `app/` into a
  new installed package: `app_shell/components.py` (page scaffold, the
  `unit_number_input` unit boundary, workflow page links, the FAR 23
  applicability banner), `app_shell/project_state.py` (the project in session
  state, the saved-snapshot baseline and the dirty/discard/load guard),
  `app_shell/sidebar.py` (the global units toggle and project
  Open/Save/upload/download widget) and `app_shell/limit_csv.py` (the analysis
  pages' LIMIT tables and downloads). `app/Home.py` keeps only what is specific
  to that front-end — its page set, its sidebar grouping and its single
  `st.set_page_config` — and drops from 258 lines to 81. No behaviour changes:
  the same widgets render in the same order with the same keys, and every
  extracted function is the one that was there, minus its leading underscore.
  **Gate G8** is new, in `tests/test_app_shell.py`: no GUI package may redefine
  a name the shell owns, the shell may not import a GUI package back, and the
  GUI set is *derived* (a directory holding a `set_page_config` entry point)
  rather than listed, so a second front-end is covered on arrival instead of
  needing the guard rewritten. `app_shell` is a real installed package
  (`pyproject.toml` `packages.find`), not a directory on Streamlit's implicit
  entrypoint path — which is what lets a second entry point import it without
  inheriting the first one's `sys.path`, and which retires the
  `sys.path.insert(…, "app")` hack in `conftest.py` and eight test modules.
  **One-time developer step: re-run `pip install -e '.[dev]'`**, and restart any
  running `streamlit run app/Home.py` — an interpreter started before this
  change resolves the old package set and will raise `ModuleNotFoundError: No
  module named 'app_shell'`.
