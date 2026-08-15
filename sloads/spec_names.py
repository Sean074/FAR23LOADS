"""Registry module name -> ``PROGRAM_SPEC.md`` section heading (R6-D6).

`PROGRAM_SPEC.md` is the per-module spec of record, but a registered module's
name and its spec heading are not the same string: the 22 ported programs are
sectioned under McMaster's original program names (``weight_estimate`` is
``WTESTIMA``), while the modern additions use their registry name. That
correspondence used to live only in a reader's head, which is how ``balance``
and ``tail_span`` -- the two most mission-central modules -- went without a
section at all.

This is that correspondence's single owner (``CLAUDE.md`` practice 3: a
cross-cutting convention gets a code owner **plus** a drift guard, never a prose
rule alone). ``tests/test_spec_coverage.py`` is the guard: every registered
module has a mapped heading, every mapped heading exists in the document, and
every heading in the document is either a module's or on the
:data:`NON_MODULE_SECTIONS` allowlist below.

The map is deliberately explicit rather than derived from the workflow graph:
``WorkflowStep.bas`` names the original program(s) per *step*, and a merged step
carries several (``"WTESTIMA+WTONECG+WTENV"``) while a folded module owns no
step at all -- so it cannot answer this question for every module.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

#: Registry name -> the ``###`` heading it is specified under. Keys are the
#: complete registry (the guard asserts that), values the heading's leading
#: token -- the text before the em dash.
SPEC_HEADINGS: Dict[str, str] = {
    # Phase 1 -- mass properties
    "weight_estimate": "WTESTIMA",
    "weight_envelope": "WTENV",
    "weight_onecg": "WTONECG",
    # Phase 2 -- geometry & speeds
    "wing_geometry": "WINGGEOM",
    "structural_speeds": "STRSPEED",
    "mach_limit": "MACHLIM",
    # Phase 3 -- aero coefficients & flight envelope
    "airloads": "AIRLOADS",
    "flight_envelope": "FLTLOADS",
    "select": "SELECT",
    "balloads": "BALLOADS",
    # Phase 4 -- component loads
    "wing_inertia": "WINGINER",
    "net_loads": "NETLOADS",
    "aileron": "AILERON",
    "flap": "FLAPLOAD",
    "tab": "TABLOADS",
    "taildist": "TAILDIST",
    "engine": "ENGLOADS",
    "one_engine_out": "ONENGOUT",
    # LANDLOAD's section covers the module; LGFACTOR (the landing load factor it
    # computes on the way) has a section of its own and no registry entry.
    "landing": "LANDLOAD",
    # Modern additions -- registry name is the heading
    "configuration": "configuration",
    "body_loads": "body_loads",
    "tail_span": "tail_span",
    "balance": "balance",
}

#: Spec sections that are not registered calc modules, and why each is one:
#: ``TAU`` folded into ``airloads``; ``LGFACTOR`` folded into ``landing``;
#: ``payload_cases`` and ``gear_loads`` are library modules
#: (``sloads/cg_cases.py``, ``sloads/gear_loads.py``) consumed by others rather
#: than run through the registry; the rest are export bridges / renderers, which
#: the document says up front are not calc modules.
NON_MODULE_SECTIONS: FrozenSet[str] = frozenset({
    "TAU",
    "LGFACTOR",
    "payload_cases",
    "gear_loads",
    "sbeam export bridge",
    "Workbook export bridge",
    "Summary report",
    "Export-scope filter",
})


__all__ = ["SPEC_HEADINGS", "NON_MODULE_SECTIONS"]
