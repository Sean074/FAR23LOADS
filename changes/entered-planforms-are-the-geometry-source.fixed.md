- **Entered leading- and trailing-edge polylines are the geometry source of record
  (tier L, 2026-08-30).** Where a surface carries LE/TE polylines, its area, aspect ratio,
  MAC and 25 %-MAC station are computed from them. `sloads/modules/wing_geometry.py`
  integrates the closed planform in **closed form** rather than by WINGGEOM's unprinted
  strip count: both edges are piecewise linear, so every integral has an exact value on
  each interval between their breakpoints. `elements` reverts to meaning only the spanwise
  load-station count. A surface whose edges span different stations is closed by its root
  and tip chords — the root chord running from the lowest-span leading-edge point to the
  lowest-span trailing-edge point, the tip chord likewise at maximum span — and its span is
  measured across both edges. `tail_geometry` and `TailPlanform` now ask
  `wing_geometry.planform_boundary` instead of carrying two more copies of the integration;
  the copies had already drifted apart. Registered oracle deviation:
  `docs/20_theory/02_approved_corrections.md`, "WINGGEOM's strip sum goes closed-form".
