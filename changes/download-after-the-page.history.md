- **The project-file block renders after the page (#64, review 2026-08-22
  PB-4, tier M, 2026-08-23)** — the review's suggested fix had two shapes:
  render the block after `pg.run()`, or make the payload lazy. The lazy
  payload (`st.download_button(data=callable)`) arrived in Streamlit 1.52,
  which requires Python ≥ 3.10 while the CI matrix still carries 3.9 — a floor
  bump is not a defect fix's call, so the ordering route was taken. Its own
  trap: `st.stop()`, which 19 `app/` views use as their missing-prerequisite
  exit, discards every element emitted after it, so "render after the page"
  in the plain sense lost Save/Download on exactly the gated pages (verified
  under `AppTest`: nothing emitted in a `finally` after `st.stop()` survives).
  The shell therefore owns the page exit — `stop_page()` raises a
  `BaseException` the sidebar context catches, then fills the slot it reserved
  before the page — and the 45 `st.stop()` sites were swept in one pass with a
  guard against the next one (rule 4, generalize on first find). Closed at
  tier M rather than the row's S because the change is a shell contract every
  view now follows, not a reorder.
