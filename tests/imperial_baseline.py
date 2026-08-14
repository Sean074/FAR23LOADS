"""The Imperial-output baseline: every deliverable channel, every example, digested.

M4-20 changed how every deliverable is written. Its central promise (decision
D-21) is that **Imperial output is unchanged** but for its new in-band unit
statement — a promise that is worth exactly as much as the test behind it.

This module builds the artifact set once, so the generator and the guard cannot
drift apart:

* :func:`artifacts` renders every channel for one example, in Imperial, with no
  header stamp (the stamp carries a tool version and would make the digest
  depend on the build rather than on the numbers).
* :func:`digests` reduces each to a SHA-256, and ``fixtures_imperial/digests.json``
  freezes them.

Digests rather than full copies: the six examples across ~10 channels each are
megabytes of near-identical CSV, and the question a guard has to answer is binary
("did any Imperial byte move?"). When one fails, regenerate locally and diff the
two renders — the frozen file tells you *that* it moved, and ``git diff`` on the
regenerated fixture tells you which channel.

Regenerate deliberately, never reflexively::

    .venv/bin/python tests/imperial_baseline.py     # rewrites the fixture

A regeneration is a claim that the change to Imperial output is intended. Say so
in the commit and in ``CHANGELOG.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures_imperial", "digests.json")

#: Every shipped example — the GA single the oracle is locked to, the twins, and
#: the two concept-mode configurations that exceed the FAR 23 caps.
EXAMPLES = (
    "atr42_100.project.json",
    "cessna_210.project.json",
    "concept_heavy.project.json",
    "concept_regional_jet.project.json",
    "dhc8_dash8.project.json",
    "ga6_normal.project.json",
)


def _try(fn, *args, **kwargs):
    """Render a channel, or skip it — an example that lacks a slice has no artifact."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, ZeroDivisionError, KeyError, IndexError, TypeError):
        return None


def artifacts(example: str) -> Dict[str, str]:
    """``{channel: text}`` for one example, rendered in Imperial with no stamp."""
    from sloads import io, registry
    from sloads.export import sbeam_bridge as sb
    from sloads.export.balanced_deck import balanced_deck
    from sloads.modules.aileron import build_aileron
    from sloads.modules.balance import build_balanced_cases
    from sloads.modules.body_loads import build_body_loads
    from sloads.modules.flap import build_flap
    from sloads.modules.net_loads import build_net_loads, loads_ref_axis_results
    from sloads.modules.tab import build_tabs
    from sloads.modules.tail_span import build_tail_span
    from sloads.modules.taildist import build_tail_chordwise
    from sloads.report import module_text_report

    project = io.load_project(os.path.join(_ROOT, "examples", example))
    out: Dict[str, str] = {}

    # Human channel: one load-case CSV and one text report per module.
    module_results = registry.run_all_modules(project)
    for mr in module_results:
        out[f"csv/{mr.module}"] = io.load_cases_csv(mr)
        out[f"txt/{mr.module}"] = module_text_report(mr.module, mr.conditions)

    # Solver channel: the component deliverables, exactly as the Export page
    # builds them (wing results transferred to the loads reference axis first).
    net = _try(build_net_loads, project)
    wing = loads_ref_axis_results(project, net.wing_net) if net is not None else None
    body = _try(build_body_loads, project)
    tail = _try(build_tail_chordwise, project)
    control = []
    for build in (build_aileron, build_flap, build_tabs):
        control += (_try(build, project) or [])

    for name, fn, arg in (
        ("wing_span", sb.span_load_csv, wing),
        ("wing_cards", sb.force_moment_cards, wing),
        ("wing_stick", sb.stick_model_bdf, wing),
        ("body_span", sb.body_span_load_csv, body),
        ("body_fitting", sb.body_fitting_load_csv, body),
        ("body_cards", sb.body_force_moment_cards, body),
        ("tail_chordwise", sb.tail_chordwise_csv, tail),
        ("tail_cards", sb.tail_force_moment_cards, tail),
        ("control_csv", sb.control_surface_csv, control),
        ("control_cards", sb.control_surface_force_moment_cards, control),
    ):
        if not arg:
            continue
        text = _try(fn, arg)
        if text:
            out[f"sbeam/{name}"] = text

    # Spanwise empennage (plan 09 T4). Per surface, because each has its own axis
    # map and its own GID band -- a shared channel would hide a swap between them.
    spans = _try(build_tail_span, project) or {}
    for component in ("htail", "vtail"):
        results = spans.get(component) or []
        if not results:
            continue
        for name, fn in ((f"{component}_span_cards", sb.tail_span_force_moment_cards),
                         (f"{component}_span_csv", sb.tail_span_csv)):
            text = _try(fn, results, component=component)
            if text:
                out[f"sbeam/{name}"] = text

    # The assembled full-span deck -- the mission's aim-2 deliverable, and until
    # B8a-2 the one deliverable this baseline did **not** cover. Found while
    # changing the closure field: the 6-DOF rewrite moved every closure card in
    # every assembled deck and no digest noticed, because the per-component
    # channels above are all this file ever rendered. Plan 11 acceptance #5 ("if
    # a digest moves, something leaked") can only mean something if the digest
    # exists.
    deck = _try(balanced_deck, project)
    if deck:
        out["sbeam/balanced_deck"] = deck

    # The index's assembled deck-number column is filled from the assembled
    # deck's own cases (design note 17), so the baseline builds them here too --
    # a column no channel renders is a column no digest can protect.
    balanced = _try(build_balanced_cases, project, []) or []
    # Deck-exported results first (see ``case_index_rows_from``): first-seen
    # defines a row's flight condition, and the row states the condition its
    # cards were computed at.
    index = _try(sb.case_index_csv_from,
                 wing or [], body or [], tail or [], control,
                 *(mr.conditions for mr in module_results),
                 assembled=balanced)
    if index:
        out["case_index"] = index
    return out


def digests() -> Dict[str, Dict[str, str]]:
    """``{example: {channel: sha256}}`` across every example."""
    return {
        example: {
            channel: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for channel, text in sorted(artifacts(example).items())
        }
        for example in EXAMPLES
    }


def load_fixture() -> Dict[str, Dict[str, str]]:
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def write_fixture() -> None:
    os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
    with open(FIXTURE, "w", encoding="utf-8") as fh:
        json.dump(digests(), fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    write_fixture()
    frozen = load_fixture()
    print(f"wrote {FIXTURE}")
    print(f"{len(frozen)} examples, "
          f"{sum(len(v) for v in frozen.values())} channels")
