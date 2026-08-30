- **The report stamped a stale sloads version.** The provenance stamp read
  `importlib.metadata`, which reports the version recorded in `PKG-INFO` when the
  package was *installed* — so in an editable checkout every report built after
  the 0.8.1 bump stated 0.8.0 until somebody reinstalled, naming a build it did
  not come from. The version now has one owner, `sloads/_version.py`:
  `pyproject.toml` declares it dynamic and reads that attribute, and so does the
  report generator, so an edit is in effect immediately and the two cannot
  disagree. Release note: the bump target is now `sloads/_version.py`, not
  `pyproject.toml`.
