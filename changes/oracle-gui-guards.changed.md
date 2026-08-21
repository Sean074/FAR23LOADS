- **A cross-page link names a step, not a path; one `set_page_config` per GUI (design note 32 step OG-F, tier M, 2026-08-20).**
  `app_shell.components.workflow_page_link` built its target as
  `views/<key>.py` — true of `app/` and of nothing else, and the last
  front-end-shaped fact left inside the shell OG-B extracted so neither GUI
  would carry the other's assumptions. It now resolves a step key to the running
  GUI's own `st.Page` object through the new **`app_shell/nav.py`**: each entry
  point registers the page set it hands `st.navigation`, and a link therefore
  cannot name a page that GUI does not carry. A step outside the running page
  set degrades to plain text, as it already did when a path would not resolve.
  **OG-10** is restated — the rule was "only `Home.py` calls
  `st.set_page_config`", which names a file rather than a role and says nothing
  about a second front-end. It is now **exactly one call per GUI entry point,
  exactly one entry point per GUI, and none in a view or in the shell**, stated
  in `PROJECT_GUIDE.md` §5 and `CLAUDE.md` and guarded in
  `tests/test_app_shell.py`. The shell case is the one the old wording could not
  express: `app_shell/` is imported by both GUIs, so a `set_page_config` there
  would be the first Streamlit call of whichever one ran.
  `tests/test_page_links.py` stays `app/`-scoped and now says why (see the
  history entry): OG-9's parametrization of it is withdrawn.
