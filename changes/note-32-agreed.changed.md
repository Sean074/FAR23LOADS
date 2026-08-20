- **Design note 32 (oracle GUI) agreed; the GUI freeze lifted for its work (tier S, 2026-08-19).**
  `docs/30_future/32_oracle_gui_note.md` moves `PROPOSED` → `AGREED`, making the
  oracle GUI the next development phase and unblocking step OG-B (tier L, so
  `CLAUDE.md` rule 1 gated it on the note being agreed — the note's status, not
  the freeze, was what actually held step one). §8 records the freeze decision in
  place of the request for one, including what it defers: the 2026-08-16 GUI
  review's placement batch for `app/`, except the two findings that outrank it
  under rule 6 as defects in shipped behaviour rather than placement — the gear
  reference point having no widget, and `speeds.wing_area_sqft` being an input
  nothing reads. One decision was added at agreement: **OG-14**, one registry
  rather than two — OG-5's field-*origin* registry and the GUI review's
  field-*ownership* registry (GR-INPUT-2) are the same table under two names, so
  step OG-C now builds a single `field path │ owning slice │ editing page │
  origin` registry with one drift guard, closing gates G4/G5 and the review's
  duplicate-owner class together. OG-5 and OG-C are amended to match.
