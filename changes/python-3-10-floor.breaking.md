- **Python 3.10 is the floor; the 3.9 claim is dropped (#132, tier M,
  2026-08-28).** The 0.8.0 cut shipped `requires-python >= 3.9` beside
  `streamlit >= 1.51` — and every Streamlit release from 1.51 declares
  `Requires-Python >= 3.10`, so the first full-matrix run on `main` after the
  tag failed in `test (3.9)` at **install**: the resolver refused the floor the
  metadata claimed. The #129 floor bump verified the API the code calls but not
  the floor's own interpreter support against the CI matrix. Owner decision:
  drop 3.9 (EOL 2025-10; Streamlit dropped it at 1.51) rather than hold the
  floor at 1.50 and re-arm the deprecated `use_container_width` on the plotly
  sites. Ships: `requires-python >= 3.10`; classifiers and the `ci.yml`
  main-push matrix move to 3.10/3.11/3.12 together; every doc stating the
  matrix swept (rule 4). The structural half (rule 3):
  `tests/test_ci_conformance.py::test_the_python_support_claim_is_one_claim_in_three_places`
  — the classifier set **is** the full-matrix set (the mirror rule was a
  pyproject comment), the `requires-python` floor is the smallest tested leg,
  and both directions were verified to fail by mutation. The half no offline
  test reaches — whether the *dependencies'* `Requires-Python` admits the
  floor — is enforced by the full-matrix install on `main`, which is exactly
  where #132 surfaced. The py310 lint target's new churn rules (B905/RUF007)
  are parked beside `UP` as the same deliberate-churn class, with the reason
  in the config.
