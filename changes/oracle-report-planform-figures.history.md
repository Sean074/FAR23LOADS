- **Section 2.1's planform figures (note 44 OR-45, tier M, 2026-08-31)** — iteration 2
  shipped section 2.1's surface tables and left the "planform figures" half of OR-45
  unbuilt, so 2.1 was the only Loads Configuration subsection with no drawing. It now
  carries one per main surface: wing, horizontal tail and vertical tail, each the entered
  edge polylines closed into an outline with its control surfaces filled on top and every
  region labelled with the area its own table prints. The work is a new emitter,
  `sloads/report/planform_tex.py`, dispatched by figure key rather than through
  `plots_tex._EMITTERS` because a planform needs `axis equal image` and therefore takes no
  height — and dispatched on the *exact* key, because the V-n figures' `vn_<index>` keys
  already miss `_EMITTERS["vn"]` and fall through to the default emitter harmlessly, which
  a planform would not: it would silently lose its equal axes and be drawn to the wrong
  shape. Three decisions carried it. Figures stay TikZ source rather than becoming
  matplotlib PNGs: `SUMMARY_REPORT.md` §2's image prohibition was reaffirmed verbatim by
  the 2026-08-30 *Data reference* amendment, `PackageMember.content` is a string, a PNG
  cannot be self-describing to §3.1, and a polygon needs none of it. No hinge line is
  drawn while the suite carries only the fwd/aft-of-hinge *areas* and derives a chord
  station from their ratio — drawing that would print an inference on a
  rectangle-equivalent with the standing of entered geometry — and the caption says so;
  the real line arrives with #156 (band B4). And the vertical tail is drawn in the
  fuselage-station/waterline plane and never mirrored, decided by the figure's frame rather
  than by `SurfaceInput.symmetric`, which `examples/baron_58.project.json` sets `true` on
  its fin. The areas are read from the owners 2.1 already cites, so no number in the
  section can be printed twice with two values; a region whose total area no table states
  (the aileron, which carries only its areas forward and aft of the hinge) is drawn and
  named without one rather than summed here. Guards in `test_oracle_report.py` hold the
  figure set against the declaration both directions, every plotted vertex against the
  entered polylines, every labelled area against the table cells, the absent-surface state
  against an empty axis, and the fin against the mirror flag.
