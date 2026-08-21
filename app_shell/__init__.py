"""The app-layer shell — everything a sloads GUI needs that is *not* a page.

**One owner, no GUI is its parent** (design note 32, decision OG-4 / step OG-B).
The FAR23 replication is growing a second front-end (the oracle GUI, note 32),
and the shell is the part both front-ends must share: project state and the
unsaved-changes guard, the units toggle, the project-file sidebar, the page
scaffold, the unit-input boundary and the LIMIT CSV builders. Before this
package these lived inside ``app/`` — two of them importable only as bare
top-level modules on Streamlit's implicit path, and the project-lifecycle
helpers not importable *at all*, because ``app/Home.py`` executes a whole
Streamlit app at import time. A second GUI could therefore only have copied
them, which is the dual path this project rejects in the calc layer
(``CLAUDE.md`` rule 3), relocated to the shell.

Layout:

* :mod:`app_shell.components` — page scaffold (:func:`~app_shell.components.page`,
  :func:`~app_shell.components.page_header`), the unit boundary
  (:func:`~app_shell.components.unit_number_input`,
  :func:`~app_shell.components.active_system`), workflow-derived page links and
  the FAR 23 applicability banner.
* :mod:`app_shell.project_state` — the project in ``st.session_state``, the
  saved-snapshot baseline and the dirty/discard/load guard.
* :mod:`app_shell.sidebar` — the global sidebar every page inherits: units
  toggle, project Open/Save/upload/download, About.
* :mod:`app_shell.limit_csv` — the analysis pages' LIMIT tables and downloads
  (pure functions, no Streamlit).
* :mod:`app_shell.nav` — the register of *which page a step key is* in the
  running GUI, so a cross-page link resolves to a page object rather than to one
  front-end's directory layout (note 32, OG-F).

**What is *not* shell: navigation.** Each GUI builds its own page set —
``app/`` from every :data:`sloads.workflow.STEPS` entry, the oracle GUI from the
subset with a ``.bas`` program (note 32, OG-2) — so a shared nav builder would
be the wrong shape for both. What *is* shared is only the lookup: an entry point
hands :func:`app_shell.nav.register_pages` the page set it just built, and a link
asks for one back. ``st.set_page_config`` likewise stays in each entry point,
**exactly one call per entry point, and none anywhere else** (OG-10) — guarded in
``tests/test_app_shell.py``.

Nothing here computes a load, converts a deliverable or writes an export: the
shell is presentation over :mod:`sloads`, and the guard in
``tests/test_app_shell.py`` asserts it never imports a GUI package back.
"""

from __future__ import annotations
