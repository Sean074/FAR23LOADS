- **The weight/CG chart drew its `% MAC` column and its CG-limit lines from
  different wings** (#80, tier M). `X = XLEMAC + (pct/100)·MAC` was spelled four
  times, and the spellings disagreed about the prior question the relation
  cannot answer for itself — *which* XLEMAC and MAC. WTENV preferred the typed
  `weight.envelope.xlemac`/`mac` override and fell back to the planform; the
  report's envelope-corner table inverted the relation over the planform alone.
  On a project carrying an override the vertical limit lines and the `% MAC`
  column beside them therefore described different references, on one chart,
  with nothing saying so. No shipped example sets the override — which is why
  this was invisible and why nothing in the frozen Imperial baseline moves — so
  the guard makes one disagree on purpose. `sloads/derived_geometry.py` now owns
  the resolution and both directions of the relation (`mac_reference`,
  `pct_mac_to_station`, `station_to_pct_mac`), and an AST scan over `sloads/`,
  `app/`, `app_shell/` and `oracle_app/` fails on a fifth spelling.
- **Two more MAC-frame quantities were computed locally** (#80, generalised from
  the above). The tail-volume neutral point and the 25%-MAC CG estimate in
  `modules/configuration.py`, and the static-margin sweep's station→%MAC
  conversion in `app/views/flight_envelope.py`, each open-coded the same
  arithmetic. All three now share the relation while passing a **planform**
  reference explicitly: they are aerodynamic quantities, so the weight
  envelope's override deliberately does not reach them, and saying so in one
  line is what stops the next reader from "fixing" it the other way.
