**One consistency-warning renderer for both GUIs (issue #82, C210-35, tier M,
2026-08-24).** The finding was that the oracle GUI renders no part of the
`consistency_warnings` channel; the cause turned out to be one layer down. The
`page` tag each warning carries was never checked against anything, and two tags
had gone stale — `weight_cg_inertia`, left behind when the weights page became
`weight_mass` at Step G3, and `wing_geometry`, left behind when Step G1 merged
that page into `configuration_layout`. Between them they carried 19 of the
module's checks, 14 in the weights group alone, and they kept working in `app/`
only because two views compared against the old strings by hand. So the channel
was not merely unrendered in the second GUI: its largest group was propped up by
a literal in one file and was dark everywhere else, which is why a contradictory
`wing_fraction` entry could survive an entire build review unshown and cost three
round-trips to diagnose from the saved file. Both halves were fixed at the level
that makes them structural rather than patched. Every tag is now a
`sloads.workflow.STEPS` key — `workflow.py` is the nav SSOT, so a tag naming
anything else names a page no GUI has — with a rule-3 guard over both the
`PAGE_*` constants and the tags the live checks emit. And the rendering has one
owner, `app_shell.components.render_consistency_warnings`, called by
`page_header` from the step key it already holds: the same place, and for the
same reason, as the applicability banner. That choice is what makes the fix
cover all fourteen oracle pages and every main-GUI view at once instead of
page by page, and it removed the six open-coded loops rather than adding a
seventh; `aero_coefficients.py` and `export_report.py` were migrated onto
`page_header` with `banner=False` so nothing but the warnings changed on them.
Warnings tagged `export_report` were deliberately left main-GUI-only by owner
call: the oracle GUI has no export page and no way to set a safety-factor
override, so a warning about one concerns state it can neither create nor act on,
and the guard permits a tag that is a workflow key without being an oracle step.
Verified on the C210 build file: all six of the warnings the owner saw in the
main GUI now render on the oracle GUI, on the pages that own them.
