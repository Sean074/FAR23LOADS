- **The GUI journey test no longer drives disabled widgets (tier S, 2026-09-02).**
  `tests/test_gui_journey.py::_touch_everything` set a value on every widget on every page,
  disabled ones included. A Streamlit release refused the interaction outright — *"Cannot
  update a disabled radio widget ... A browser user cannot interact with a disabled
  widget"* — turning the whole journey suite red on CI while the pinned local environment
  still permitted it. Disabled widgets are now skipped, for both the value-bearing widgets
  and the form submit buttons. That is what the function's own docstring has always claimed
  ("every **editable** block"): a page disables a control to say this cannot be entered here
  and now, and a journey that drove it anyway asserted about a gesture no browser user can
  make. No assertion was weakened — every `KNOWN_OPEN` entry still reproduces, which is the
  guard that says so.
