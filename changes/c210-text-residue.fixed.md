- **The C210 review's text-only residue lands: eleven helps and captions now say
  what the mechanisms do (#94, tier S, 2026-08-27).** The EMPTY-only item sum is
  labelled **empty weight** everywhere it shows (the ordering chain, the fleet
  comparison; OEW adds the MINIMUM crew — C210-12); `role` help states it assigns
  the LANDLOAD slot and validates nothing (C210-14); the chosen speeds state
  "blank = computed minimum, below-minimum values are raised", with `chosen_vf`
  distinguished from the placard VFE (C210-16, the MFC half moot since #79);
  `xtc`/`xtf` carry the CP convention (flaps up ≈ 5 % tail MAC, flaps down ≈ 25 %)
  **plus a computed suggestion from the empennage record** beside the fields in
  both GUIs (`derived_geometry.tail_cp_suggestion`; `oracle_app.form.GROUP_NOTES`),
  `mn` and the altitudes say what they are (C210-20); the SELECT block states its
  search scope — the governing case over the full V-n matrix, all loadings, CGs
  and altitudes (C210-26); `section_slope` says it is the 2-D section slope, not
  the AR-reduced C1 (C210-28); `wing_mass.cases` states "0 rows = the SELECT
  governing set; typed rows REPLACE it entirely" (C210-30); the oracle Tail Loads
  page points at the spanwise deliverable's home (main GUI Tail Span Loads + the
  export decks — C210-33); `ref_waterline` is captioned reserved/not consumed
  (C210-34, owner ruling); blank Optional number inputs carry an "empty — type a
  value" placeholder so Streamlit's inert steppers stop reading as a locked
  widget (C210-42, the #35 blank-render contract unchanged); and the sidebar says
  before the click that **Save to disk** writes `projects/<name>.project.json`
  beside the app while **Download** lets the browser choose the location
  (C210-48). Guards in `tests/test_oracle_gui.py` (`GROUP_NOTES` keys must name a
  rendered group; the suggestion arithmetic; the placeholder; the two advisories).
