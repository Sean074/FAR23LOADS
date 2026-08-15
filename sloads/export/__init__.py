"""Export bridges from SLOADS results to external structural tools.

Currently the sbeam bridge (C4): turns SLOADS component loads into
sbeam-consumable span/chordwise-load CSVs, ``FORCE``/``MOMENT`` bulk-data cards,
and an optional CBAR stick-model BDF. See :mod:`sloads.export.sbeam_bridge`.

The concept deliverable is "all components to sbeam", so the package API exports
all four component families plus the case index:

- **Wing** — :func:`span_load_csv`, :func:`force_moment_cards`,
  :func:`stick_model_bdf` (+ ``write_*`` variants), built from the NETLOADS net
  wing load (``Project.loads.wing_net``).
- **Body / fuselage** — :func:`body_span_load_csv`, :func:`body_force_moment_cards`,
  :func:`body_fitting_load_csv` (the wing-attach fitting loads, reported beside
  the FORCE set rather than in it) — all three with ``write_*`` variants —
  and :func:`body_station_gids`.
- **Tail** — :func:`tail_chordwise_csv`, :func:`tail_force_moment_cards`
  (+ ``write_*`` variants).
- **Control surfaces** — :func:`control_surface_csv`,
  :func:`control_surface_force_moment_cards` (+ ``write_*`` variants).
- **Mass model** — :mod:`sloads.export.mass_cards`: :func:`conm2_fragment`,
  :func:`mass_check_deck` and :func:`inertia_only_cards`, the ``CONM2``/
  ``MASSSET`` export that gives sbeam an *independently parsed* mass model to
  check sloads' inertia loads against. Deliberately **not** re-exported at
  package level beyond these three: the inertia-only set is a comparison
  artifact, never a deliverable, and reaching it stays an explicit import.
- **Closure gate** — :mod:`sloads.export.equilibrium`: :func:`parse_cards`,
  :func:`deck_resultants` and :func:`closes`, the single owner of "re-derive a
  deck's Σ force / Σ moment from its own card text and check the claim its
  header makes". Every deck-closure check in the suite goes through it.
- **Case index** — :func:`case_index_csv` (+ ``write_case_index_csv``) and
  :func:`filter_by_selected_case_ids`, the manifest tying exported decks back to
  their FAR 23 load-case IDs and the selective-export filter.

:mod:`sloads.export.pdf` (Step G8.6) also lives here but is **deliberately not
re-exported**: it is the one module in the codebase that runs a subprocess and
writes a temp directory (compiling the summary report's ``.tex``), so reaching it
stays an explicit ``from sloads.export.pdf import compile_pdf`` at the two call
sites that want it. See its docstring for the documented I/O exemption.
"""

from __future__ import annotations

from .coordinates import SBEAM_CID, to_force, to_grid, to_moment, to_pressure
from .equilibrium import (
    CardTotals,
    Resultant,
    card_totals,
    closes,
    deck_resultants,
    parse_cards,
    ref_aftmost_loaded,
    ref_first_loaded,
    resultant,
)
from .sbeam_bridge import (
    NodalLoad,
    body_fitting_load_csv,
    body_force_moment_cards,
    body_span_load_csv,
    beam_station_gid,
    body_station_gids,
    case_index_csv,
    safety_factors_csv,
    control_surface_csv,
    control_surface_force_moment_cards,
    filter_by_selected_case_ids,
    force_moment_cards,
    span_load_csv,
    station_gid,
    stick_model_bdf,
    tail_chordwise_csv,
    tail_force_moment_cards,
    tail_station_gid,
    wing_nodal_loads,
    write_body_fitting_load_csv,
    write_body_force_moment_cards,
    write_body_span_load_csv,
    write_case_index_csv,
    write_safety_factors_csv,
    write_control_surface_csv,
    write_control_surface_force_moment_cards,
    write_force_moment_cards,
    write_span_load_csv,
    write_stick_model_bdf,
    write_tail_chordwise_csv,
    write_tail_force_moment_cards,
)
from .workbook import build_workbook

__all__ = [
    "SBEAM_CID",
    "to_force",
    "to_grid",
    "to_moment",
    "to_pressure",
    "NodalLoad",
    "wing_nodal_loads",
    "station_gid",
    # Wing
    "span_load_csv",
    "write_span_load_csv",
    "force_moment_cards",
    "write_force_moment_cards",
    "stick_model_bdf",
    "write_stick_model_bdf",
    # Body / fuselage
    "body_span_load_csv",
    "write_body_span_load_csv",
    "body_force_moment_cards",
    "write_body_force_moment_cards",
    "body_fitting_load_csv",
    "write_body_fitting_load_csv",
    "body_station_gids",
    "beam_station_gid",
    # Tail
    "tail_chordwise_csv",
    "write_tail_chordwise_csv",
    "tail_force_moment_cards",
    "write_tail_force_moment_cards",
    "tail_station_gid",
    # Control surfaces
    "control_surface_csv",
    "write_control_surface_csv",
    "control_surface_force_moment_cards",
    "write_control_surface_force_moment_cards",
    # Case index
    "case_index_csv",
    "safety_factors_csv",
    "write_case_index_csv",
    "write_safety_factors_csv",
    "filter_by_selected_case_ids",
    "build_workbook",
    # Export-boundary closure gate (sloads.export.equilibrium)
    "parse_cards",
    "CardTotals",
    "card_totals",
    "Resultant",
    "resultant",
    "deck_resultants",
    "ref_first_loaded",
    "ref_aftmost_loaded",
    "closes",
]
