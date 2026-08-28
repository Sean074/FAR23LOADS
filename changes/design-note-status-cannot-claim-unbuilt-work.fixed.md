- **A design note can no longer claim work is unbuilt after it has shipped
  (#128, tier S, 2026-08-28; production-release review §3.3).** Two notes still
  carried their pre-build status: [note 32](docs/30_future/32_oracle_gui_note.md)
  said *"everything else is unbuilt"* of the oracle GUI whose every §7 step is
  marked shipped in its own table (OG-A…OG-C2 on 2026-08-19, OG-D…OG-F on
  2026-08-20), and [note 35](docs/30_future/35_taildist_aero_state_note.md) said
  *"Nothing below is built yet"* of work that shipped as #100 on 2026-08-27.
  Both now state what shipped, in the shape notes 36/37 (`SHIPPED`) and 34
  (`AGREED …; BUILT …`) already use. This blocks a cut rather than trailing it:
  `RELEASE_PROCESS.md` §4 step 3 rolls the notes into `docs/40_history/` at the
  cut, so an "unbuilt" claim would enter the permanent record of the release
  that built it. The structural half (practice 3) is a guard in
  `tests/test_doc_currency.py`: a note carrying an unbuilt claim while also
  carrying shipped evidence fails. The evidence is deliberately **in-repo** —
  whether an issue is closed lives on GitHub, which CI has no credential to
  read, but a closed item leaves a `changes/` fragment citing its note by the
  tiered-closure rule, and that fragment exists *because* something closed. A
  companion test asserts the pattern still matches the two sentences it was
  written for, so it cannot quietly decay into a guard that passes by seeing
  nothing. Verified: reintroducing either sentence fails its note's case.
