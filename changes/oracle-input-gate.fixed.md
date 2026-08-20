- **Twelve input fields were classified as sloads additions and are inputs of the original programs (design note 32 gate G5, tier M, 2026-08-19).**
  Running the field registry rather than reading it moved `weight.items[].ixx/
  iyy/izz` and `.kind`, `geometry.surfaces[].leading_edge/trailing_edge/
  elements`, `weight.cg_cases[].weight_lb/xcg/zcg`,
  `weight.estimation.engine_weight_type` and `engines[].engine_type` from
  `Origin.SLOADS` to `Origin.ORIGINAL`. Each is settled by a citation the repo
  already carried and the table had not been read against — `MassItemKind`
  *"mirrors the data-base partition of WTONECG.BAS"*, the edge polylines are
  entered *"exactly as the original program prompts for them"*, `elements` **is**
  WINGGEOM.BAS's `H`, `EngineWeightType` holds *"the two-letter codes of the
  original program"* (WTESTIMA.BAS lines 230–290) — and by the printed oracle:
  without the per-item inertias Appendix A p136's IXX comes out **66.7** against
  the printed **1201.527**, so the oracle the suite already passes depends on
  them being entered. Nothing in the calc changed and no shipped number moved;
  what was wrong was the claim about which fields the oracle GUI could omit.
  Registry consequence: `origin` gains a companion column, `supplied`, for the
  eleven fields the second front-end writes without asking (selectors, LANDLOAD's
  three loading roles, the engine layout), so "the user is not asked" and "the
  field is not set" stop being the same claim; and `structurally_required()`
  reads declared defaults off `dataclasses.fields`, so a field the oracle GUI
  *cannot* omit can no longer be classified as omittable by accident.
