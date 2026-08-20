- **A gate that would have passed on an empty set (design note 32 step OG-E, tier M, 2026-08-20)** —
  OG-E was the note's smallest step: tier S, "CSV + text output through the
  existing owners". Two things about it were wrong, and both were only visible
  once the step was picked up rather than planned. The first is small: after
  OG-D the oracle GUI computed *nothing* — `render_step` rendered inputs and
  stopped — so "add downloads" meant adding a download button under a page with
  no result on it. Running the programs and showing the tables came with the
  step, which is what re-tiered it to M.
  The second is the one worth recording. Gate G7 says every CSV the oracle GUI
  offers passes the parametrized ultimate-contract scan, and OG-9 had already
  scheduled that parametrization — `tests/test_ultimate_contract.py` hardcodes
  `app/views/`, so a second GUI is invisible to it. But the scan works by
  matching a **literal** `file_name="….csv"` in the source and reading the call
  that built it, and a derived GUI has no such literal: its filenames are
  computed from the step key. Parametrizing it over `oracle_app/` would have
  found nothing, passed, and reported the second front-end as covered. That is
  worse than leaving it out, because the failure is now invisible in two places
  instead of one — and it is precisely the failure OG-9 was written to prevent,
  reappearing inside OG-9's own remedy. The diagnosis was right; the remedy did
  not transfer. G7 is therefore a **runtime** gate: `results.page_artifacts()`
  hands back every file a page offers with its bytes, and the gate reads the
  bytes — the `csv_comment_block` stamp and an `SF` column for an ULTIMATE file,
  in-band LIMIT *and* a `*_LIMIT.csv` name for a limit one, and byte equality
  with `cli.py`'s own text report. What makes it a gate rather than a sample is
  the second assertion: the package holds **exactly one `st.download_button`
  call site**, fed from that same function, so an artifact the gate has not seen
  cannot exist. A source scan checks the code that would produce the file; this
  checks the file.
  The third thing OG-E turned up is an amendment rather than a defect. OG-6
  named two output owners, which gives a page its load cases — and the load
  cases are not what AIRLOADS, NETLOADS and TAILDIST *print*. Their printed
  output, the thing Appendix A **is**, is the spanwise or chordwise station
  table, and it is in no `ModuleResult`: it is built from `wing_load_rows` /
  `body_load_rows` / `build_tail_chordwise` and rendered by
  `app_shell/limit_csv.py`. Read strictly, OG-6 forbade the oracle GUI from
  showing the oracle's own printout. It was written before OG-B existed, and
  `limit_csv` is neither a new renderer nor a bespoke CSV — it is the shared
  shell owner OG-B extracted for exactly this channel — so the amendment adds no
  path, it names one that was already there. Those tables are LIMIT and say so
  in-band and in the filename, which §5 had already anticipated.
  Two smaller structural notes. `FOLDED_MODULES` became a mapping to the owning
  step, because a page headed "WTESTIMA+WTONECG+WTENV" must run all three and a
  flat tuple cannot say which page WTESTIMA belongs to — the information was in
  a comment, which is the shape `CLAUDE.md` rule 3 exists to convert. And
  `STATION_TABLES`, the renderer's one hand-declared table, is keyed by **module
  name** rather than page key: which row builder a program has is a fact about
  the program, and keying it by page would have put a step key back into the
  GUI, which gate G2 forbids for good reason.
