- **Oracle page placement moves, the load-bearing zero tail CP is refused, and
  a crash names its line (tier M, 2026-08-26, #99).** C210-37/44 (owner
  directives): the aileron/flap planform geometry (areas, deflection limits,
  chord ratio) and `engine_layout` render on the Geometry page beside the
  empennage forms — the rows keep their slices, the placement is the registry
  page tag, and a drift guard holds the decision; the Engine Mount page's
  layout-consistency message now names both owning pages. C210-21: `xtc`/`xtf`
  at their 0.0 default put the tail CP at the datum, sign-flip the tail arm and
  balance silently wrong — `build_envelope` refuses the station a config in
  play would read, by name, and `tail_cp_station_unset` warns on the Flight
  Envelope page before anything runs. C210-14: `landing_light_not_lighter`
  warns when a `fwd_light` case weighs exactly the max landing weight — the
  role claims the light corner while the numbers answer the heavy question.
  C210-24 (the display half of #71): a not-ready result block keeps its
  friendly one-liner but adds the exception type and carries the traceback,
  module:line first, in an expander — a from-blank user can report *where* it
  died without leaving the GUI.
