- **Xcg in %MAC in the oracle report's CG-case table (tier M, 2026-08-31)** — §2.2 stated
  every CG case as a fuselage station while the structural CG limits beside it, in the same
  subsection and on the same figure, are entered in percent of MAC. The reader was left to
  convert, by hand, against whichever XLEMAC and MAC they could find — and this suite resolves
  that pair two ways, a typed `envelope.xlemac`/`mac` override or the wing planform, so "the"
  MAC was not a single number a reader could safely assume. The table now carries the
  percentage beside the station and the note carries the relation in both directions together
  with the pair it applied and where that pair came from, which is what makes the column
  checkable rather than merely convenient. It is a change of reference, not a second analysis:
  the column reads `derived_geometry.station_to_pct_mac` against `mac_reference`, the same
  owners the limit lines use, and the section-2 guard that says the report invents no number
  was widened to admit exactly that — a case's own entered station, through that one relation,
  against that one reference — rather than by exempting the column. Where nothing resolves the
  cell is a dash with a stated reason, because `station_to_pct_mac` answers `0.0` on a
  degenerate MAC by contract and a column of zeroes reads as a centre of gravity sitting on
  the leading edge.
