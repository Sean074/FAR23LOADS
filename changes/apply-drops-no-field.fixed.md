- **Apply no longer deletes what the form does not render — the landing gear is
  reachable, and four pages stopped silently discarding stated values (#36 part 1,
  review 2026-08-20 CR-A-2 neighbourhood, tier M, 2026-08-21).** A form that
  rebuilds an input dataclass from its own widgets resets every field it forgot to
  name, so pressing **Apply** — with nothing typed — erased data a hand-written
  `project.json` had supplied. The landing-gear form was the worst case and the
  one the backlog names: it dropped `carrier` (decision G-2), `attach` (the G-12
  trunnion node) and `weight_lb` (G-12a), the three fields the sbeam ground model
  needs, so a GUI-built project exported **zero gear nodes** — and because the
  form never rendered them, re-entering them was impossible. All three now have
  widgets, with a **"— not stated —"** carrier option so G-2's deliberate absence
  survives a round trip instead of being guessed. The same defect, swept in the
  same change: the empennage form dropped the fin root waterline (B8a-1) so the
  fin quietly re-derived onto the centreline as a *marked assumption*; the engine
  form dropped `mounted_on`, replacing a stated engine parent with an inferred
  one; and the wing-aero form wiped the profile-drag and section-Cm polars, which
  no widget anywhere in the GUI could restore. Guard
  (`tests/test_configuration_layout_view.py`): every Apply on every page is
  pressed **without touching a widget**, and anything the project stated that has
  become unstated fails the test — one-sided by design, so Apply may still seed
  and re-derive but may never delete.
