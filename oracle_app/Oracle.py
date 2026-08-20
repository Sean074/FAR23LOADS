"""sloads — the **oracle GUI** entry point (design note 32, step OG-D).

Run with:  streamlit run oracle_app/Oracle.py    (or: sloads-oracle)

A second, independently launched front-end over the *same* ``sloads`` calc
package, exposing only the capability of the original McMaster **FAR 23 LOADS**
suite: the original programs' inputs, and nothing this replication added. It is
not a mode of ``app/`` and shares no page with it — the two are peers over one
analysis model (OG-1), and everything they genuinely share (the project in
session state, the dirty guard, the units toggle, the project-file widget, the
unit-input boundary) lives in :mod:`app_shell`, owned once (OG-4/G8).

**Its page set is derived, not listed** (OG-2, gate G2):
:func:`sloads.workflow.oracle_steps` is the owner, and the rule is *runs a
``.BAS`` program, or produces a slice such a step requires*. Adding a ``bas`` to
a workflow step therefore adds a page here with no edit to this file. There are
no per-page view files either: every page is :func:`oracle_app.form.render_step`
bound to a step key, and what it shows comes from
:mod:`sloads.field_registry` — which is why fourteen pages cost one renderer.

**What it deliberately does not have.** Plots, the sbeam decks, the workbook, the
LaTeX report, the concept-mode pages and every sloads-only field: all still fully
available in ``app/``, none of them reachable from here. A project saved by
either GUI opens in the other unchanged (OG-13, gate G6) — this front-end asks
for less, it does not store anything different.
"""

from __future__ import annotations

import streamlit as st

from app_shell.project_state import ensure_project
from app_shell.sidebar import render_shell_sidebar
from oracle_app.form import render_step
from sloads import workflow as wf

# The first Streamlit call, and the ONLY set_page_config in this entry point --
# exactly one per GUI entry point (note 32, OG-10). The shell imports above
# define widgets but emit nothing, so they do not consume it.
st.set_page_config(page_title="sloads — oracle", layout="wide", page_icon="📐")


def _page(step: wf.WorkflowStep) -> st.Page:
    """A navigable page for an oracle step.

    The page *is* the generic renderer bound to this step's key. A callable
    rather than a ``views/<key>.py`` path on purpose: a file per page would be a
    hand-maintained page list wearing a different hat, and gate G2 requires that
    adding a ``bas`` to a workflow step adds a page with no GUI edit at all.
    """
    def render() -> None:
        render_step(step.key)

    render.__name__ = step.key
    return st.Page(render, title=step.title, url_path=step.key,
                   default=(step.key == wf.oracle_steps()[0].key))


project = ensure_project()
render_shell_sidebar(project)

st.sidebar.caption(
    "**Oracle interface** — the original suite's inputs only. "
    "The full sloads app is `streamlit run app/Home.py`."
)

pg = st.navigation([_page(step) for step in wf.oracle_steps()], expanded=True)
pg.run()
