- **The fin-root "fuselage-top" formula has a body-centreline datum (backlog
  Pri 1, defect from T-8a, tier M, 2026-08-16).**
  `tail_geometry.fin_root_waterline`'s fuselage-top branch was
  `root_waterline_z + fuselage_height/2`, which reads the **wing** root as the
  body centreline — the substitution `CONVENTIONS.md`'s body-drag row refuses
  for D-1 — and on the three high-wing outline fixtures stacked half a body
  above the real top. With a fuselage outline present the branch is now
  **`z_centre(x_fin) + height(x_fin)/2`**: the v52 section-centre line
  (`derived_geometry.fuselage_centreline`, note 24 R-4) plus half the **local**
  body height (new sibling owner `derived_geometry.fuselage_height_at`), both
  at the fin's `xv25`. The old formula survives only as the no-outline fallback
  and its note now names the wing-root substitution it makes; a pointed tail
  cone (zero local height at `x_fin`) declines the branch rather than seating a
  fin on nothing. The new project-level resolver `tail_geometry.fin_root`
  is read by both the load path and the three-view
  (`configuration.tail_planform` gained an optional `project` argument), so the
  single-owner guard holds. **Re-pins (the un-pinning the backlog row
  promised):** fin roots `atr42_100` 223.15 → 191.17 in, `dhc8_dash8` 232.95 →
  203.45, `cessna_210` 109.60 → 100.24 (`ga6_normal` — no outline — and the
  T-tail regional jet unchanged); the twelve lateral-case pins moved in `p_dot`
  (roll arm) and slightly in `r_dot` (`Ixz` coupling) with fin load and `n_y`
  byte-identical; the Imperial digest baseline regenerated deliberately for the
  three fixtures' `balance`/`tail_span`/vtail cards and decks (plus a
  note-text-only move on `ga6_normal`'s fin deck header).
