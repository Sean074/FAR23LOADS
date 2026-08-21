"""Which page a workflow step key *is*, in whichever GUI is running.

Design note 32, step **OG-F**. ``components.workflow_page_link`` used to build
its target as ``views/<key>.py`` -- correct for ``app/``, and an ``app/``-shaped
fact living in the shared shell OG-B extracted precisely so neither front-end
would own the other's assumptions. The oracle GUI has no view files at all (its
pages are callables, gate G2), so the same helper called from there would have
linked into a page set it is not part of.

The fix is to stop the shell knowing any layout. Each entry point already builds
its own ``st.Page`` objects from :mod:`sloads.workflow`; it registers them here
when it does, and the link helper resolves a step key to the page object of the
GUI that is actually running. ``st.page_link`` accepts a ``StreamlitPage``
directly, so nothing has to be spelled as a path.

Registration lives in session state rather than a module global because the
pages belong to a *session's* running app, not to the imported module: two
browser tabs on the two GUIs share this process and must not see each other's
page set.

A caller that has not registered (a view driven standalone under ``AppTest``,
or a page rendered outside ``st.navigation``) gets ``None`` and the helper falls
back to plain text, which is what it already did when ``st.page_link`` could not
resolve a path.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import streamlit as st

#: Session-state key holding ``{step key: st.Page}`` for the running GUI.
PAGES = "_app_shell_pages"


def register_pages(pages: Mapping[str, Any]) -> None:
    """Record the running GUI's pages, keyed by workflow step key.

    Called by each entry point as it builds its navigation, so the mapping is
    always the page set ``st.navigation`` was handed -- never a second list.
    """
    st.session_state[PAGES] = dict(pages)


def page_for(key: str) -> Optional[Any]:
    """The running GUI's page for ``key``, or ``None`` if it has none.

    ``None`` is a real answer, not a failure: the oracle GUI has fourteen of the
    twenty-two steps, so a link to a page it does not carry must degrade to text
    rather than point somewhere that does not exist.
    """
    pages: Dict[str, Any] = st.session_state.get(PAGES, {})
    return pages.get(key)


__all__ = ["PAGES", "page_for", "register_pages"]
