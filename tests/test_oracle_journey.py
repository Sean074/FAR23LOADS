"""Gate G5, second leg — a project typed from blank through the oracle GUI's own
widgets is the reduced project (review 2026-08-22 PB-3, #62).

``test_oracle_inputs.py`` proves that a shipped example *reduced to the oracle
input set* still gives the original suite's numbers. It cannot prove that the
GUI can make such a project: the reduction is a deep copy with fields cleared,
and for a while it cleared less than it claimed (a stored ``mass`` slice
carried every gate while no oracle page wrote one). This leg closes that from
the other side. For each oracle page, in workflow order, the answer key is
rendered under ``AppTest`` and every value-bearing widget and every
``st.data_editor`` input frame is recorded; the same page is then rendered on
a project that started as ``Project(name=...)`` and the recorded values are
set through the widgets -- row counts first, then scalars, frames replayed
through the editor -- until nothing is left to set. When all fourteen pages
have been typed, the typed project must equal the reduced answer key:

* the serialised documents are identical (document metadata aside),
* every page's result blocks and download payloads are byte-identical, and
* a save → reload → re-run of the typed project is a fixed point.

Comparing against the **reduced** key rather than the full one is what makes
this the gate's second leg rather than a third claim: the first leg ties the
reduced key to the full one, and this ties the GUI to the reduced key, so the
declared divergences (the twins' turbine rotors) need stating once.

``AppTest`` cannot drive a ``data_editor`` (a canvas), so the harness swaps
``st.data_editor`` for a recorder/replayer around the real one -- the frame the
page *offers* is recorded from the answer render and handed back as the
*edited* frame on the typed render, which is the persist path the #35 tests
exercise as well.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

import pytest
from streamlit.testing.v1 import AppTest

from app_shell.widget_keys import unstamped
from oracle_app.results import page_artifacts, step_results
from sloads import Project, UnitSystem
from sloads import io as sloads_io
from sloads import workflow as wf
from sloads.field_registry import (
    LIST_MARKER,
    NON_INPUT,
    display_only_paths,
    reduce_to_oracle_inputs,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "examples")

#: The Appendix A airplane, and a twin turboprop so One Engine Out has a case
#: and the rotor divergence is exercised through the reduction.
JOURNEYS = ("ga6_normal", "dhc8_dash8")

_SCRIPT = '''
import streamlit as st
from app_shell.widget_keys import unstamped
from oracle_app.form import render_step

if not hasattr(st, "_orig_data_editor"):
    st._orig_data_editor = st.data_editor


def _recording_data_editor(df, **kw):
    key = unstamped(kw.get("key"))
    st.session_state.setdefault("_rec_tables", {})[key] = df.copy()
    replay = st.session_state.get("_replay_tables")
    if replay is not None and key in replay:
        return replay[key].copy()
    return st._orig_data_editor(df, **kw)


st.data_editor = _recording_data_editor
render_step(st.session_state["_key"])
'''

_WIDGET_KINDS = ("number_input", "text_input", "checkbox", "selectbox", "multiselect")
_MAX_ROUNDS = 8


def _render(key: str, project: Project, replay=None) -> AppTest:
    at = AppTest.from_string(_SCRIPT, default_timeout=120)
    at.session_state["project"] = project
    at.session_state["_key"] = key
    at.session_state["_rec_tables"] = {}
    at.session_state["_replay_tables"] = replay
    at.run()
    assert not at.exception, f"[{key}] {[e.message for e in at.exception]}"
    return at


def _widgets(at: AppTest) -> Dict[str, Tuple[Any, Any]]:
    """{unstamped key: (value, widget)} for every value-bearing widget."""
    out = {}
    for kind in _WIDGET_KINDS:
        for w in getattr(at, kind):
            key = unstamped(w.key)
            if key and not key.startswith("_"):
                out[key] = (w.value, w)
    return out


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-9
    return a == b


def _type_page(key: str, typed: Project, answer_at: AppTest) -> Project:
    """Set every recorded widget on the blank page; the project as persisted."""
    wanted = _widgets(answer_at)
    frames = dict(answer_at.session_state["_rec_tables"])
    at = _render(key, typed, replay=frames)
    for _round in range(_MAX_ROUNDS):
        present = _widgets(at)
        unknown = sorted(set(present) - set(wanted))
        assert not unknown, f"[{key}] widgets on the blank page the answer never showed: {unknown}"
        pending = [(0 if k.endswith(".count") else 1, k, wanted[k][0], w)
                   for k, (val, w) in present.items() if not _same(val, wanted[k][0])]
        if not pending:
            break
        # Counts first: they create the rows the other widgets live in.
        rank = min(p[0] for p in pending)
        for r, _k, target, w in pending:
            if r == rank:
                w.set_value(target)
        at.run()
        assert not at.exception, f"[{key}] {[e.message for e in at.exception]}"
    else:
        pytest.fail(f"[{key}] did not converge in {_MAX_ROUNDS} rounds: "
                    f"{[(k, t, present[k][0]) for _, k, t, _ in pending]}")
    missing = sorted(set(wanted) - set(_widgets(at)))
    assert not missing, f"[{key}] the answer page has widgets the typed page never showed: {missing}"
    return at.session_state["project"]


def _blocks(project: Project, key: str) -> List[Tuple[str, str, int, Tuple[str, ...]]]:
    return [(b.title, b.note, len(b.rows), b.warnings)
            for b in step_results(project, key, UnitSystem.IMPERIAL)]


def _artifacts(project: Project, key: str) -> List[Tuple[str, Any]]:
    return [(a.file_name, a.payload)
            for a in page_artifacts(project, key, UnitSystem.IMPERIAL)]


def _first_diff(a: Any, b: Any) -> str:
    if isinstance(a, bytes) or isinstance(b, bytes):
        return f"{a[:120]!r} != {b[:120]!r}"
    al, bl = str(a).splitlines(), str(b).splitlines()
    for i, (x, y) in enumerate(zip(al, bl)):
        if x != y:
            return f"line {i}: {x!r} != {y!r}"
    return f"{len(al)} vs {len(bl)} lines"


def _document(project: Project) -> Dict[str, Any]:
    """The serialised project, less what no widget can carry.

    Document metadata has no widget in this GUI (review PB-6), and a
    display-only copy of another field (``speeds.wing_area_sqft`` shows the
    wing planform's area, disabled) is never written by it -- the registry's
    ``governs`` rule, which is also why no number moves on it.
    """
    doc = sloads_io.project_to_dict(project)
    for name, reason in NON_INPUT.items():
        if reason == "document metadata":
            doc.pop(name, None)
    for path in display_only_paths():
        _clear(doc, path.split("."))
    return doc


def _clear(node: Any, segments: List[str]) -> None:
    head, rest = segments[0], segments[1:]
    if head.endswith(LIST_MARKER):
        for item in node.get(head[: -len(LIST_MARKER)], None) or []:
            _clear(item, rest)
        return
    if not isinstance(node, dict) or head not in node:
        return
    if rest:
        _clear(node[head], rest)
    else:
        node[head] = None


@pytest.fixture(scope="module", params=JOURNEYS)
def journey(request):
    """``(answer, typed)``: the reduced answer key and the project typed from it."""
    full = sloads_io.load_project(os.path.join(_EXAMPLES, f"{request.param}.project.json"))
    answer = reduce_to_oracle_inputs(full)
    typed = Project(name=answer.name)
    for step in wf.oracle_steps():
        typed = _type_page(step.key, typed, _render(step.key, answer))
    return answer, typed


def test_the_typed_project_is_the_reduced_key(journey):
    answer, typed = journey
    a, t = _document(answer), _document(typed)
    off = sorted(k for k in set(a) | set(t) if a.get(k) != t.get(k))
    assert not off, "\n".join(
        f"{k}: typed={json.dumps(t.get(k))[:300]}\n   answer={json.dumps(a.get(k))[:300]}"
        for k in off)


def test_every_page_gives_the_reduced_keys_numbers(journey):
    answer, typed = journey
    for step in wf.oracle_steps():
        assert _blocks(typed, step.key) == _blocks(answer, step.key), step.key
        for (name, payload), (_n, want) in zip(_artifacts(typed, step.key),
                                               _artifacts(answer, step.key)):
            assert payload == want, f"[{step.key}] {name}: {_first_diff(payload, want)}"
        assert len(_artifacts(typed, step.key)) == len(_artifacts(answer, step.key)), step.key


def test_save_reload_rerun_is_a_fixed_point(journey):
    _answer, typed = journey
    text = sloads_io.project_to_json(typed)
    reloaded = sloads_io.project_from_dict(json.loads(text))
    assert sloads_io.project_to_json(reloaded) == text
    for step in wf.oracle_steps():
        assert _artifacts(reloaded, step.key) == _artifacts(typed, step.key), step.key


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
