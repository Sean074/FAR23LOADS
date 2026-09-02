- **The oracle report's CG-case table states Xcg in %MAC, and the relation it used (tier M, 2026-08-31).**
  §2.2's *Weight and centre-of-gravity cases* table gains an `Xcg (% MAC)` column beside the
  station, and its note now prints the relation both ways —
  `%MAC = 100 (X - XLEMAC) / MAC` and `X = XLEMAC + (%MAC / 100) MAC` — with the XLEMAC and
  MAC in use and whether they came from the typed `envelope.xlemac`/`mac` override or the wing
  planform of §2.1. The column comes from `derived_geometry.mac_reference` and
  `station_to_pct_mac`, the one resolver and one relation the CG limit lines and the summary
  report's `% MAC` column already use, so a case and a limit on the same page cannot end up
  measured from two different wings. Where no reference resolves, the column prints a dash and
  the note says why, rather than showing the contract's `0.0` as if it were an answer.
