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
  the FORCE set rather than in it), :func:`body_station_gids`.
- **Tail** — :func:`tail_chordwise_csv`, :func:`tail_force_moment_cards`
  (+ ``write_*`` variants).
- **Control surfaces** — :func:`control_surface_csv`,
  :func:`control_surface_force_moment_cards` (+ ``write_*`` variants).
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
from .sbeam_bridge import (
    NodalLoad,
    body_fitting_load_csv,
    body_force_moment_cards,
    body_span_load_csv,
    body_station_gids,
    case_index_csv,
    control_surface_csv,
    control_surface_force_moment_cards,
    filter_by_selected_case_ids,
    force_moment_cards,
    span_load_csv,
    station_gid,
    stick_model_bdf,
    tail_chordwise_csv,
    tail_force_moment_cards,
    wing_nodal_loads,
    write_case_index_csv,
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
    "body_force_moment_cards",
    "body_fitting_load_csv",
    "body_station_gids",
    # Tail
    "tail_chordwise_csv",
    "write_tail_chordwise_csv",
    "tail_force_moment_cards",
    "write_tail_force_moment_cards",
    # Control surfaces
    "control_surface_csv",
    "write_control_surface_csv",
    "control_surface_force_moment_cards",
    "write_control_surface_force_moment_cards",
    # Case index
    "case_index_csv",
    "write_case_index_csv",
    "filter_by_selected_case_ids",
    "build_workbook",
]
