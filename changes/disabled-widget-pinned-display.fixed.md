- **A widget that flips disabled is pinned to its governing value (tier S,
  2026-08-27; the #95 CI find on 0b38c8a).** A display-only number widget kept
  its stale live state when its owner appeared mid-session — type a fuselage
  length, add the outline on the same page, and the disabled field went on
  showing the typed number while the analysis read the outline's own length
  (current Streamlit lets keyed widget state outvote `value=`; the G5 journey
  caught it on CI's newer Streamlit, not the pinned local one).
  `app_shell.components._seeded_number` now writes the governing seed into a
  **disabled** widget's session state before instantiation — one point on the
  unit boundary, so every disabled scalar in both GUIs shows the number the
  calc uses. Guard:
  `tests/test_oracle_gui.py::test_a_widget_that_flips_disabled_is_pinned_to_the_governing_value`
  walks the exact live→disabled flip.
