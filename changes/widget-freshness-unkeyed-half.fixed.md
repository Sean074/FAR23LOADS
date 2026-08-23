- **The unkeyed half of `app/views/`: 98 project-seeded widgets keyed, the
  freshness guard fails closed** (issue #51 reopen, tier M, 2026-08-22): an
  unkeyed Streamlit widget derives its identity from its *arguments* —
  `value=` included — so a value typed before a project load survived it
  whenever the loaded field repeated the seed (the common case: the seed is
  `Project(name="")`; reproduced on `structural_speeds`' VB against
  `atr42_100`). All 98 unkeyed input widgets in `app/views/` now carry
  `key=widget_key(...)`; `test_widget_freshness.py`'s `_stamped` inverts to
  fail closed (its "no `key=` is per-render" premise was wrong),
  `_INPUT_CALLS` gains the missing input calls (`pills`, `segmented_control`,
  `file_uploader`, `camera_input`, `audio_input`, `chat_input`), the sidebar's
  whole-file exemption becomes a **per-key allowlist** with a companion test
  that fails when an entry stops naming a real widget (the #43 lesson), and a
  type-then-load reproduction test asserts the typed value does not survive
  and the loaded project is unchanged.
