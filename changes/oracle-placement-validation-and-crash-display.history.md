**#99 — Oracle page placement and the validation/error-display pair
(2026-08-26).** The first 0.8.0 item, four C210 build-review findings sharing
one page and one channel. Placement (C210-37/44): the aileron/flap planform
geometry and the engine layout are configuration, so their registry rows are
re-tagged to the Geometry page and sit beside the empennage forms — the slices
do not move (the single-consumer pattern stands), the oracle page set being
registry-derived makes the move a tag, and
`test_control_surface_planform_geometry_renders_on_the_geometry_page` guards
the decision; the Aileron Loads page becomes results-only and says so through
the existing no-input branch. Validation (C210-21/14): the load-bearing-zero
class gets the `cg_case_without_weight` treatment — `build_envelope` refuses a
0/unset `xtc`/`xtf` by name for exactly the configs that would read it, with
`tail_cp_station_unset` warning on the page first — and
`landing_light_not_lighter` closes the role-contradiction gap the M4-17d
hierarchy checks left at the equal-weight boundary. Display (C210-24): the
not-ready catch keeps its one-liner, adds the exception type, and carries a
module:line-first traceback into an expander, closing the display half of #71.
