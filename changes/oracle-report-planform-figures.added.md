- **Section 2.1 of the oracle technical report draws its planform figures (note 44 OR-45,
  tier M, 2026-08-31).** One to-scale figure per main surface — wing, horizontal tail,
  vertical tail — showing the entered leading- and trailing-edge polylines as a closed
  outline with the control surfaces that live on it filled on top, each region labelled
  with the area the table beside it already prints. OR-45 promised the figures with the
  tables in iteration 2 and only the tables shipped; this is the other half. New owner:
  `sloads/report/planform_tex.py`, a TikZ emitter dispatched by figure key from
  `plots_tex.figure_body_tex`. Drawn on `axis equal image` — a swept tapered surface on
  independent axes is a different shape from the one the loads were computed for — with
  the butt-line surfaces spanwise-across and the station axis reversed, so a 402-inch wing
  fits a page and still reads nose-up in the airplane's own stations. Regions are told
  apart by fill density, never colour (`SUMMARY_REPORT.md` §4.3), and the vertical tail is
  drawn in the fuselage-station/waterline plane and never mirrored: the frame decides that,
  not `SurfaceInput.symmetric`, which `examples/baron_58.project.json` sets `true` on its
  fin. **No hinge line is drawn**, and the caption says why: the suite carries a control
  surface's areas forward and aft of its hinge as scalars and no hinge geometry, so a line
  would be an inference printed with the standing of entered geometry. It arrives with #156.
  Figures stay **source, not images** — `SUMMARY_REPORT.md` §2's image prohibition, which
  the 2026-08-30 *Data reference* amendment reaffirmed verbatim, is unchanged and a polygon
  costs nothing to keep it.
