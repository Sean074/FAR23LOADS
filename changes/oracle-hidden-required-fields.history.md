## Step — Hidden required fields rendered or captioned (#98, tier M, 2026-08-27)

The `_SLDS`-origin filter hid fields the user must state (C210-46/49/29): every
tab silently defaulted to the h-tail because `tab_loads.tabs[].surface` was
never rendered, an oracle-built project could not export ground cases because
both gear legs' `carrier`/`attach`/`weight_lb` were hidden with sentinel
defaults, and an empty `aero.surfaces` list showed a bare rows counter with no
trace of the AIRLOADS block behind it. The fix is two structural classes rather
than three patches (rule 4): **row selectors** — a `name`/`surface` leaf on a
list record, which a page can never resolve positionally — are rendered
(`supplied=True`, selectboxes over `models.inputs.TAB_SURFACES`/`TAIL_SURFACES`)
with unknown surfaces refused by name (`require_surface`; the silent
`_TAB_COMPONENT.get(..., "wing")` fallback and the silently-inert `tail_mass`
row died with it), guarded by
`test_field_registry.py::test_a_list_row_selector_is_always_asked`; **sentinel
defaults** are registered in `field_registry.SENTINEL_DEFAULTS`, rendered, and
guarded by `::test_a_sentinel_default_field_is_always_asked`; and the empty-list
caption is generated from the page's own field set at `render_table`'s one early
return, so every empty list gains it and it cannot drift. Every new `supplied`
mark carries a G5 demonstration in `tests/test_oracle_inputs.py` (the tab
misroute, the override that went nowhere, the unmatched aero row's refusal, the
carrier warning, the omitted gear node, the open free body); the supplied-ratio
dial moved 10 % → 15 % with the reason stated. SSOT row: `CONVENTIONS.md` §7.
