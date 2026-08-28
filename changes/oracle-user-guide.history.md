## Step — The oracle GUI user guide (#96, note 34, tier M, 2026-08-27)

Design note 34's guide built to plan in the six UG-10 stages, gates first:
`docs/60_guide/` with generated field tables (`docs/generate_data_dict.py` →
`_generated/`, UG-3), workflow-derived chapter order (UG-7), Playwright
screenshot capture (`scripts/capture_guide_shots.py`, UG-4), fourteen
eight-section chapters, front matter carrying the single LIMIT/ULTIMATE
statement (UG-8), and the two end-to-end appendices — `ga6_normal` in
Imperial against the printed Appendix A checkpoints, and the new
`examples/baron_58.project.json` (UG-9: TCDS-sourced Baron 58, every
estimate marked in its sources register) worked entirely in SI and closed
on the channel-free stored project (UG-12). Gates G-UG-1…G-UG-6 landed in
stage 1 and checked every chapter on arrival (`tests/test_guide.py`); the
twin joined the oracle-reduction `EXACT` set and the ground-coverage pin.
Two latent defects the twin exposed were filed with bodies the same session
(#121, #122). `GUI_USER_GUIDE.md` stays the full-app guide (UG-2), now
cross-linked both ways.
