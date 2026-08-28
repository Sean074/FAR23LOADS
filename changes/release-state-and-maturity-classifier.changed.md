- **What this release is has one owner, and the trove classifier moves to
  `4 - Beta` (tier S, 2026-08-28; production-release review §3.5, owner ruling
  §5.3).** The maturity claim is genuinely mixed — the FAR23 core is
  oracle-locked and the oracle GUI is the finished deliverable, while `app/` and
  the concept-mode features are not — and PyPI's `Development Status` takes one
  value from a fixed vocabulary. So `pyproject.toml` carries the value a *fresh
  installer* is owed (`4 - Beta`: the distribution ships both front-ends and one
  of them is beta), and the sentence the classifier cannot hold gets a single
  owner, `app_shell.components.RELEASE_STATE`: *"Core analysis developed per
  FAR 23 LOADS and the oracle GUI production-ready; additional features and the
  full sloads GUI in beta."* `README.md` and `CAPABILITIES.md` carry it verbatim
  and both GUIs' About panel consumes the symbol — so a person typing an
  airplane into the beta front-end is told so where they are, rather than in
  packaging metadata `pip` reads and they do not. Markdown cannot import a
  constant, so "one owner" is enforced the only way prose allows
  (`tests/test_doc_currency.py`, two halves, both verified to fail on a
  mutation): the documents must contain the owner's string verbatim and the
  About panel must consume the symbol, and **no second spelling** of it may
  appear anywhere else in the tree. Same posture as `LANDING_L_FAR_CAPTION`,
  one level up — a statement about the product rather than about a widget.
