- **Fields the user must state are no longer filtered off the oracle pages
  (#98, C210-46/49/29, tier M, 2026-08-27).** One cause — the `_SLDS`-origin
  filter — and the same failure three ways, now closed as two guarded classes
  plus a generated caption. **Row selectors** (`tab_loads.tabs[].surface`,
  `tail_mass[].surface`, `aero.surfaces[].name`): a page resolves a *scalar*
  surface selector positionally, never a *row's*, so hiding one hardcoded every
  row — every tab was silently an h-tail tab (wrong case-ID band, export tag
  and BL-vs-WL station reading) and a rudder or aileron tab could not be
  entered at all. They are rendered now (selectboxes over the
  `TAB_SURFACES`/`TAIL_SURFACES` vocabularies), an unknown surface is **refused
  by name** (`models.inputs.require_surface`) where it used to be silently
  filed under `wing` or silently inert, and
  `test_a_list_row_selector_is_always_asked` fails structurally on the next
  hidden one. **Sentinel defaults** (both gear legs' `carrier`, `attach`,
  `weight_lb`): defaults that mean "not stated" — the export assumes or omits
  the leg's node and no ground case is deliverable — are registered in
  `field_registry.SENTINEL_DEFAULTS` (each entry citing its refusing consumer),
  rendered, and guarded by `test_a_sentinel_default_field_is_always_asked`.
  **Empty lists** (C210-29's caption half; the seed half shipped with #97): an
  empty list table used to be a bare rows counter with no trace of the whole
  AIRLOADS block it hid; it now captions every field the page holds behind a
  row, **generated from the page's own field set** so every empty list in the
  GUI gains it and the caption cannot drift when a field is added. Each new
  `supplied` mark is demonstrated load-bearing in `tests/test_oracle_inputs.py`.
