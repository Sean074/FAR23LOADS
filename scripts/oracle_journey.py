"""The oracle GUI fresh-project journey, page by page, under AppTest (review 2026-08-22, PB-3).

Not a test yet: the pre-cut beta review proposes it become gate G5's second leg.
Run: .venv/bin/python scripts/oracle_journey.py [example]   (SECOND_PASS=1 for the all-typed compare)

Answer key: examples/ga6_normal (loaded + migrated). For each oracle page:
  1. render the page on the ANSWER project, record every widget (unstamped key
     -> value) and every data_editor input frame (key -> DataFrame);
  2. render the page on the TYPED project (starts blank), set the row-count
     widgets, then every scalar widget, replaying the recorded frames through
     st.data_editor -- iterate to a fixed point;
  3. compare the page's result blocks / artifacts between TYPED and ANSWER.
Then: project_to_json(TYPED) -> project_from_dict -> artifacts bit-identical.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback

from streamlit.testing.v1 import AppTest

from app_shell.widget_keys import unstamped
from oracle_app.results import page_artifacts, step_results
from sloads import Project, UnitSystem
from sloads import field_registry as fr
from sloads import io as sloads_io
from sloads import workflow as wf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = tempfile.gettempdir()
EXAMPLE = sys.argv[1] if len(sys.argv) > 1 else "ga6_normal"
ANSWER_PATH = os.path.join(ROOT, "examples", f"{EXAMPLE}.project.json")

SCRIPT = '''
import streamlit as st
import oracle_app.form as form
from app_shell.widget_keys import unstamped
from oracle_app.form import render_step

if not hasattr(st, "_orig_data_editor"):
    st._orig_data_editor = st.data_editor

def _fake_data_editor(df, **kw):
    k = unstamped(kw.get("key"))
    st.session_state.setdefault("_rec_tables", {})[k] = df.copy()
    replay = st.session_state.get("_replay_tables")
    if replay is not None and k in replay:
        return replay[k].copy()
    return st._orig_data_editor(df, **kw)

st.data_editor = _fake_data_editor
render_step(st.session_state["_key"])
'''


def new_app(key, project, replay=None):
    at = AppTest.from_string(SCRIPT, default_timeout=120)
    at.session_state["project"] = project
    at.session_state["_key"] = key
    at.session_state["_rec_tables"] = {}
    at.session_state["_replay_tables"] = replay
    at.run()
    return at


def widgets(at):
    """{unstamped key: (kind, value)} for every value-bearing widget."""
    out = {}
    for kind in ("number_input", "text_input", "checkbox", "selectbox", "multiselect"):
        for w in getattr(at, kind):
            k = unstamped(w.key)
            if not k or k.startswith("_"):
                continue
            out[k] = (kind, w.value, w)
    return out


def drive(key, typed, answer_widgets, answer_tables, log):
    """Type the answer into the page on ``typed`` until nothing is left to set."""
    at = new_app(key, typed, replay=answer_tables)
    if at.exception:
        log.append(f"[{key}] EXCEPTION on blank render: {[e.message for e in at.exception]}")
        return at
    for round_no in range(8):
        present = widgets(at)
        pending = []
        # counts first (they create the rows the other widgets live in)
        for k, (_kind, val, w) in present.items():
            if k not in answer_widgets:
                log.append(f"[{key}] widget {k} exists on the blank page but not on the answer page")
                continue
            target = answer_widgets[k][1]
            if val != target and not (isinstance(val, float) and isinstance(target, (int, float))
                                      and abs(val - target) < 1e-9):
                pending.append((0 if k.endswith(".count") else 1, k, target, w))
        if not pending:
            break
        pending.sort(key=lambda t: t[0])
        # One rerun per batch: set all counts first if any, else all scalars.
        batch_rank = pending[0][0]
        for rank, k, target, w in pending:
            if rank != batch_rank:
                continue
            try:
                w.set_value(target)
            except Exception as exc:
                log.append(f"[{key}] cannot set {k} to {target!r}: {exc}")
        at.run()
        if at.exception:
            log.append(f"[{key}] EXCEPTION after setting round {round_no}: "
                       f"{[e.message for e in at.exception]}")
            return at
    else:
        log.append(f"[{key}] did not converge in 8 rounds; still pending: "
                   f"{[(k, t, present[k][1]) for _, k, t, _ in pending]}")
    missing = set(answer_widgets) - set(widgets(at))
    if missing:
        log.append(f"[{key}] answer page has widgets the typed page never showed: {sorted(missing)}")
    return at


def artifacts_of(project, key):
    return [(a.file_name, a.payload) for a in page_artifacts(project, key, UnitSystem.IMPERIAL)]


def blocks_of(project, key):
    return [(b.title, b.note, len(b.rows)) for b in step_results(project, key, UnitSystem.IMPERIAL)]


def main():
    answer = sloads_io.load_project(ANSWER_PATH)
    typed = Project(name=answer.name)
    log = []
    keys = [s.key for s in wf.oracle_steps()]
    for key in keys:
        ans_at = new_app(key, answer)
        if ans_at.exception:
            log.append(f"[{key}] EXCEPTION rendering the answer: {[e.message for e in ans_at.exception]}")
            continue
        ans_w = widgets(ans_at)
        ans_t = dict(ans_at.session_state["_rec_tables"])
        # the answer render must not have dirtied the answer project
        at = drive(key, typed, ans_w, ans_t, log)
        typed = at.session_state["project"]
        # page-level comparison
        tb, ab = blocks_of(typed, key), blocks_of(answer, key)
        if tb != ab:
            log.append(f"[{key}] result blocks differ:\n   typed={tb}\n   answer={ab}")
        ta, aa = artifacts_of(typed, key), artifacts_of(answer, key)
        for (tn, tp), (_an, ap) in zip(ta, aa):
            if tp != ap:
                tl, al = tp.splitlines(), ap.splitlines()
                diff = [(i, x, y) for i, (x, y) in enumerate(zip(tl, al)) if x != y][:3]
                log.append(f"[{key}] artifact {tn} differs (first diffs): {diff}")
        if len(ta) != len(aa):
            log.append(f"[{key}] artifact count typed={len(ta)} answer={len(aa)}")
        print(f"{key}: widgets={len(ans_w)} tables={len(ans_t)} blocks={len(tb)} log={len(log)}",
              flush=True)

    # Oracle-input paths that still differ between typed and answer
    td, ad = sloads_io.project_to_dict(typed), sloads_io.project_to_dict(answer)

    def flat(d, prefix=""):
        out = {}
        if isinstance(d, dict):
            for k, v in d.items():
                out.update(flat(v, f"{prefix}.{k}" if prefix else k))
        elif isinstance(d, list):
            for i, v in enumerate(d):
                out.update(flat(v, f"{prefix}[{i}]"))
        else:
            out[prefix] = d
        return out
    ft, fa = flat(td), flat(ad)
    import re
    oracle = fr.oracle_input_paths()

    def generic(p):
        return re.sub(r"\[\d+\]", "[]", p)
    diffs = sorted(p for p in set(ft) | set(fa) if ft.get(p) != fa.get(p))
    oracle_diffs = [p for p in diffs if any(generic(p).startswith(o) for o in oracle)]
    other_diffs = [p for p in diffs if p not in oracle_diffs]
    print("\n== oracle-input paths that differ after typing everything ==")
    for p in oracle_diffs:
        print(f"  {p}: typed={ft.get(p)!r} answer={fa.get(p)!r}")
    print(f"\n== non-oracle paths that differ: {len(other_diffs)} ==")
    for p in other_diffs[:60]:
        print(f"  {p}: typed={ft.get(p)!r} answer={fa.get(p)!r}")

    # save -> reload -> re-run bit identity
    print("\n== save/reload/re-run ==")
    text = sloads_io.project_to_json(typed)
    reloaded = sloads_io.project_from_dict(json.loads(text))
    for key in keys:
        a1, a2 = artifacts_of(typed, key), artifacts_of(reloaded, key)
        if a1 != a2:
            log.append(f"[{key}] artifacts differ after save/reload")
    text2 = sloads_io.project_to_json(reloaded)
    print("json fixed point:", text == text2)

    print("\n== LOG ==")
    for line in log:
        print(line)
    with open(os.path.join(OUT_DIR, f"typed_{EXAMPLE}.project.json"), "w") as fh:
        fh.write(text)


if __name__ == "__main__" and not os.environ.get("SECOND_PASS"):
    try:
        main()
    except Exception:
        traceback.print_exc()


def second_pass(example=EXAMPLE):
    """Compare every page once the whole project has been typed."""
    answer = sloads_io.load_project(ANSWER_PATH)
    with open(os.path.join(OUT_DIR, f"typed_{example}.project.json")) as fh:
        typed = sloads_io.project_from_dict(json.load(fh))
    for key in [s.key for s in wf.oracle_steps()]:
        tb, ab = blocks_of(typed, key), blocks_of(answer, key)
        if tb != ab:
            print(f"[{key}] blocks differ:\n   typed={tb}\n   answer={ab}")
        for (tn, tp), (_an, ap) in zip(artifacts_of(typed, key), artifacts_of(answer, key)):
            if tp != ap:
                tl, al = tp.splitlines(), ap.splitlines()
                diff = [(i, x, y) for i, (x, y) in enumerate(zip(tl, al)) if x != y]
                print(f"[{key}] {tn}: {len(diff)} differing lines; first: {diff[:2]}")


if __name__ == "__main__" and os.environ.get("SECOND_PASS"):
    second_pass()
