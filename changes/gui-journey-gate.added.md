- **The GUI is walked end to end in CI, not just booted (#145, tier M,
  2026-08-29).** `tests/test_gui_journey.py` loads every bundled example, visits
  every `workflow.py` step in order carrying one session forward — widget state
  included — presses every Apply and re-enters every widget with the value it
  already holds, then runs every registered module. It asserts that no page
  raises, that every module runs clean or refuses by name with
  `MissingInputError`, and that the project is **byte-identical** across the
  whole walk, since nothing was entered anywhere in it. The release gate above
  it (`RELEASE_PROCESS` §3.5) booted both front-ends and checked the root page
  answered 200, which cannot reach a defect two pages downstream of an
  interaction — the shape of both post-0.8.0 escapes. §3.5 now names the journey
  and gains a short manual walkthrough as its second line. The accepted no-op
  Apply writes are the file's `KNOWN_OPEN` list, each carrying its #148 line and each
  asserted to still reproduce, so a carve-out cannot lapse into silence.
