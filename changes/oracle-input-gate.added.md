- **Gate G5: the oracle GUI's reduced input set is run, not asserted (design note 32 step OG-C2, tier M, 2026-08-19).**
  `tests/test_oracle_inputs.py` builds the project the second front-end would
  produce — `sloads.field_registry.reduce_to_oracle_inputs`, every field outside
  its input set returned to its declared default — and checks it three ways: the
  same oracle-page modules run (or refuse, as `one_engine_out` correctly does on
  a single-engine airplane), every load value agrees with the full project
  within **±0.1 %**, and four Appendix A figures are restated directly on the
  reduced project (p136 IXX/IYY/IZZ, p141 wing AREA/MAC/XLE(MAC), p142 aileron,
  WTENV's 78 lb aft-gross ballast). Five of the six shipped examples reduce
  **exactly**; `concept_regional_jet` is excused in the file with its reason (the
  25.335(b) Mach-margin dive-speed route and turbofan engine data have no
  counterpart in the original suite), and a guard fails if a new example is
  neither. The one quantity the reduction drops — `root_torsion_myy_lra`, torsion
  about the loads reference axis — is declared with the reason it is sloads-only
  output rather than a lost oracle. Because every ga6-based Appendix A oracle
  test asserts against the *full* project, agreement carries all of them onto the
  reduced set without restating a figure.
