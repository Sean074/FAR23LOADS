# M3-1 Execution Runbook — Rename `FAR23LOADS`/`farloads` → **`sloads`** (+ split `models.py`)

Step-by-step procedure for backlog item **M3-1** (see
[`00_backlog.md`](00_backlog.md)). This is the *how*; the backlog entry is the
*what* and the acceptance criteria. Follow the steps in order — each ends with a
green-check you must pass before moving on.

**Scope (decided):** the full `farloads` → `sloads` rename **batched with** the
`models.py` → `models/` package split (same churn event, per the 2026-07-21
review). Staged into logical commits on a fresh branch.

## Conventions used below

- Shell prompt is macOS / zsh; the project venv is `.venv/`. Commands use the
  `.venv/bin/…` prefixes this repo uses everywhere.
- **`sed -i ''`** is the **BSD (macOS)** in-place form — the empty `''` is the
  mandatory backup-suffix argument. On GNU/Linux it would be `sed -i` with no
  `''`. Do not copy these onto Linux unchanged.
- **Git is yours to run.** Every `git …` line below is flagged **▶ run
  yourself** — per `CLAUDE.md`, Claude does not run git. Everything else
  (`sed`, `pip`, `pytest`, editing files) is ordinary working-tree work.

---

## Step 0 — Pre-flight baseline

Confirm a clean tree and a green suite *before* touching anything, and record the
pre-rename reference counts so Step 9 can prove they went to zero.

```bash
# ▶ run yourself
git status                                   # expect: clean, on New-GUI-Interface

# green baseline
.venv/bin/python -m pytest -q
.venv/bin/ruff check farloads/ cli.py

# record the surface counts (compare against these at the end)
grep -rn 'farloads' --include='*.py' . | wc -l    # ~404 across ~97 files
grep -rln 'farloads' --include='*.md' docs | wc -l # ~20 docs
grep -rn 'FAR23LOADS' --include='*.py' .           # uppercase brand in export/, tests
```

**Green-check:** pytest passes, ruff clean, tree clean. If not, stop and fix
first — you must not start a rename on a red tree.

---

## Step 1 — Branch

```bash
# ▶ run yourself
git checkout -b M3-1-rename-sloads
```

---

## Step 2 — Move the package directory (history-preserving)

Use `git mv` so blame/history follow the files.

```bash
# ▶ run yourself
git mv farloads sloads
```

Nothing else is renamed at this point — `cli.py` stays a top-level module (it is
listed under `[tool.setuptools] py-modules`, not inside the package). The stray
dirs `farloads.egg-info/`, `_to_delete/`, `_staging_tmp2/`, `__pycache__/` are
**gitignored and untracked**, so `git mv` does not touch them.

**Green-check:** `git status` shows the package as renamed (`R` entries); imports
are still broken (expected — fixed in Step 4).

**Commit boundary (a):**
```bash
# ▶ run yourself
git commit -am "M3-1: git mv farloads -> sloads (package move)"
```

---

## Step 3 — Split `models.py` into a `models/` package

`sloads/models.py` (~1861 lines, ~60 top-level defs) is already ordered by
lifecycle. Cut it into a package. Create `sloads/models/` with:

| File | Contents |
|------|----------|
| `enums.py` | `EngineType`, `EngineLayout`, `RotorType`, `RotorDirection`, `EngineWeightType`, `MassItemKind`, **`TailType`** (physically at ~line 1127 in the old file — pull it up here) |
| `inputs.py` | `MissingInputError` + the ~40 `*Input`/support dataclasses (`Rotor` … `LandingGearGeometry`, `LayoutInput`) **plus `default_fuselage_outline()`** (old ~line 1207) |
| `results.py` | `CaseRef`, `LoadValue`, `ConditionResult`, `ModuleResult`, and the per-domain `*Result`/`*Load` types (old lines ~1228–1755) |
| `project.py` | **`SCHEMA_VERSION = 32`** (unchanged — no schema change) + `class Project` |
| `__init__.py` | re-export the full surface (below) |

Dependency order is acyclic: **enums → inputs → results → project**. Inside each
submodule use package-relative imports (`from .enums import …`,
`from .inputs import …`). `project.py` imports from both `.inputs` and
`.results` (and `default_fuselage_outline` from `.inputs`).

`sloads/models/__init__.py` must re-export everything so all existing import
forms keep resolving unchanged:

```python
"""Project schema + per-module input/result dataclasses (split from the former
single models.py at M3-1)."""
from .enums import *      # noqa: F401,F403
from .inputs import *     # noqa: F401,F403
from .results import *    # noqa: F401,F403
from .project import *    # noqa: F401,F403
```

Give **each submodule an explicit `__all__`** listing its public names (this is
what `import *` re-exports). Cross-check the full name set against the big
`from .models import (…)` block + `__all__` in `sloads/__init__.py` — every name
there must remain importable from `sloads.models`.

Then remove the old monolith:

```bash
# ▶ run yourself
git rm sloads/models.py     # (after the four submodules + __init__.py exist)
```

Why this is non-breaking: the 17 absolute `from sloads.models import X`, the 3
`import sloads.models as m/M`, the 32 intra-package `from .models`/`from ..models`
relative imports, and the `sloads/__init__.py` re-export block all resolve
through `models/__init__.py`'s re-exports.

**Green-check (deferred):** you can't import yet (Step 4 still pending), but
verify the split in isolation:
```bash
.venv/bin/python -c "import ast,glob; [ast.parse(open(f).read()) for f in glob.glob('sloads/models/*.py')]; print('parse OK')"
```

---

## Step 4 — Rewrite imports & internal `farloads.` references

Mechanical `farloads` → `sloads` over all Python. Registry `MODULE_NAME` values
(`"engine"`, `"aileron"`, …), JSON schema keys, and session-state keys
(`"project"`, `"unit_system"`, `"_saved_project_snapshot"`) contain **no**
`farloads` substring, so this sed cannot corrupt them. It *does* rename the
`farloads_io` alias → `sloads_io` — that is self-consistent (defined and used
per-file) and correct.

```bash
# Rewrite every .py that mentions farloads (imports, farloads.* attr paths,
# Sphinx :mod:/:func: xrefs, the farloads_io alias). BSD sed, in place.
grep -rl 'farloads' --include='*.py' . | xargs sed -i '' 's/farloads/sloads/g'

# The data-dict generator also carries a path-segment literal + a regex:
#   docs/generate_data_dict.py — "farloads" path segment (~line 46) and
#   re.sub(r"\bfarloads\.models\.", …) (~line 144). The blanket sed above
#   already turns both into "sloads"/sloads\.models\. — verify, don't redo.

# Verification: only historical-attribution passages should remain (Step 9
# tightens this). No .py import should still say farloads:
grep -rn 'farloads' --include='*.py' .        # expect: nothing
```

**Do NOT** let this pass rewrite the uppercase `FAR23LOADS` brand or the "FAR 23
LOADS" attribution strings — this sed only targets lowercase `farloads`, so those
are untouched here (handled deliberately in Step 7).

**Green-check:** `grep -rn 'farloads' --include='*.py' .` returns nothing.

---

## Step 5 — `pyproject.toml`

Six load-bearing spots (all lowercase `farloads` — a scoped sed is fine, then
eyeball):

```bash
sed -i '' 's/farloads/sloads/g' pyproject.toml
```

Confirm each landed:
- `[project] name = "sloads"`
- `[project.scripts] sloads = "cli:main"`  ← console-script entry
- `[tool.setuptools.packages.find] include = ["sloads*"]`
- `[tool.pytest.ini_options] addopts = "--cov=sloads --cov-report=term-missing"`
- `[tool.coverage.run] source = ["sloads"]`

(The `description` string carries the "FAR 23 LOADS" brand — a Step 7 decision,
left for now.)

---

## Step 6 — Reinstall & verify wiring

Delete the **stale** egg-info first so the old `farloads` entry-point script and
metadata don't linger, then reinstall editable.

```bash
rm -rf farloads.egg-info sloads.egg-info
.venv/bin/pip install -e '.[dev]'

# console script + registry
.venv/bin/sloads --list                       # lists registered modules
.venv/bin/python -c "import sloads; from sloads.models import Project, SCHEMA_VERSION; print(SCHEMA_VERSION)"

# full gates
.venv/bin/python -m pytest -q
.venv/bin/ruff check sloads/ cli.py
```

**Green-check:** `sloads --list` prints the modules; import of `sloads` and
`sloads.models` succeeds; pytest passes; ruff clean.

**Commit boundaries (b)(c)(d):** the models split, the import rewrite, and the
pyproject+reinstall are logically distinct — commit them separately if the tree
was green between each; otherwise fold Steps 3–6 into one "rename wiring" commit.
```bash
# ▶ run yourself  (example, adjust to how you staged)
git add -A && git commit -m "M3-1: split models/ package, rewrite imports, pyproject -> sloads"
```

---

## Step 7 — Brand strings (deliberate; attribution stays)

These are a **separate decision** from the package identifier — change them
consciously, do not sed blindly.

**Rename to the `sloads` brand:**
- `app/Home.py:44` — `st.set_page_config(page_title="FAR 23 LOADS", …)`
- `app/Home.py:1` — module docstring header
- `README.md:1` — H1 `# FAR 23 LOADS` (+ the bold brand on line ~3)
- `sloads/__init__.py:1` — package docstring header
- `pyproject.toml` — `description` string
- **sbeam export headers** — `sloads/export/sbeam_bridge.py` emits
  `$ FAR23LOADS …` deck comments (~lines 245, 247, 416, 505, 607). **If you
  rebrand these, update `tests/test_workbook.py:114`** (`assert not
  cell.startswith("$ FAR23LOADS")`) **in the same commit** — otherwise the test
  silently drifts. (Also the `FAR23LOADS` docstrings in `export/coordinates.py`
  and `export/__init__.py`.)

**KEEP (historical attribution — the acceptance grep must find only these):**
- `app/Home.py:235` — `"FAR 23 LOADS" is a separate commercial product.` (the
  trademark-disambiguation line — the M2R-2 attribution)
- README attribution prose and the McMaster / "FAR 23 LOADS suite" citations
- Historical `.md` reviews (`CHANGELOG.md`, `PROJECT_REVIEW_2026-07-19.md`)

Smoke the GUI title/About:
```bash
.venv/bin/streamlit run app/Home.py      # confirm tab title + About/footer brand; Ctrl-C
```

**Commit boundary (e):**
```bash
# ▶ run yourself
git commit -am "M3-1: rebrand GUI/README/export to sloads (attribution retained)"
```

---

## Step 8 — Docs, generator & examples sweep

Update the doc references (paths `farloads/…`, the `farloads` command, `:mod:`
xrefs). The ~20 affected `.md` files include: `CLAUDE.md`,
`docs/10_standard/PROGRAM_SPEC.md`, `PROJECT_GUIDE.md`,
`00_program_overview.md`, `RELEASE_PROCESS.md`,
`docs/20_theory/00_theory_sources.md`, this `30_future/` tree, and
`docs/40_history/00_completed_development.md`.

```bash
# docs (review the diff — docs also contain "FAR 23 LOADS" attribution to keep)
grep -rln 'farloads' --include='*.md' . | xargs sed -i '' 's/farloads/sloads/g'

# scripts + generator
sed -i '' 's/farloads/sloads/g' scripts/smoke_test.sh    # `sloads engine …`
# docs/generate_data_dict.py already handled by Step 4's .py sed — verify:
grep -n 'farloads' docs/generate_data_dict.py            # expect: nothing
```

Review each `.md` diff — the sed only hits lowercase `farloads` (command/paths),
so the "FAR 23 LOADS" attribution prose is untouched, which is correct.

**Repo folder name (out of scope):** no source hardcodes
`Loads_Programs/FAR23LOADS`; renaming the working directory itself is optional and
**not** part of M3-1 — folder name ≠ package name, and renaming it would break the
local `.venv` and any absolute paths. Leave it, or rename separately with care.

**Green-check:** `grep -rn 'farloads' --include='*.md' docs` returns only
intentional attribution (ideally nothing); `scripts/smoke_test.sh` references
`sloads`.

---

## Step 9 — Final acceptance gate

The backlog's acceptance list:

```bash
# 1) one name everywhere — grep finds only historical-attribution passages
grep -rn 'farloads' --include='*.py' --include='*.md' --include='*.toml' . \
  | grep -v '.git/'
grep -rn 'FAR23LOADS' . | grep -v '.git/'    # expect: only attribution/history + (intentional) export headers

# 2) imports / CLI / tests green
.venv/bin/sloads --list
.venv/bin/python -m pytest
.venv/bin/ruff check sloads/ cli.py

# 3) GUI/CLI smoke
scripts/smoke_test.sh                          # exits 0
```

Confirm the disclaimer is present in **both** README and the GUI About/footer
(the "separate commercial product" line survived Step 7).

**Green-check:** the grep shows only attribution; pytest/ruff green; smoke test
exits 0.

---

## Step 10 — Lifecycle bookkeeping (same session as execution)

Per `CLAUDE.md` — do this in the **same session** the rename is executed (not the
planning session):

1. **Remove** M3-1 from [`00_backlog.md`](00_backlog.md) (and drop the D-6 row's
   "at 0.3.0 (M3-1)" once closed, as appropriate).
2. **Add** M3-1 to
   [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
   in full step format (surface counts, split boundaries, acceptance evidence).
3. **`CHANGELOG.md`** `[Unreleased]` entry (a `Changed` line: package/CLI/brand
   rename to `sloads`; models split).
4. Add any new domain terms to `cspell.json` (e.g. `sloads` if not already
   present).
5. Update [`00_INDEX.md`](../00_INDEX.md) wording if it references `farloads/`.

---

## Step 11 — Commit boundaries (summary) & merge

Suggested staged commits (adjust to how the tree stayed green):

| # | Commit | Covers |
|---|--------|--------|
| a | `git mv farloads -> sloads (package move)` | Step 2 |
| b | `split models/ package (enums/inputs/results/project)` | Step 3 |
| c | `rewrite imports farloads -> sloads` | Step 4 |
| d | `pyproject -> sloads; reinstall editable` | Steps 5–6 |
| e | `rebrand GUI/README/export (attribution retained)` | Step 7 |
| f | `docs/scripts sweep + lifecycle bookkeeping` | Steps 8, 10 |

```bash
# ▶ run yourself — merge when the branch is green end-to-end
git checkout New-GUI-Interface
git merge --no-ff M3-1-rename-sloads
```

M3-1 then feeds **M3-2** (the `sloads 0.3.0` release cut per
[`../10_standard/RELEASE_PROCESS.md`](../10_standard/RELEASE_PROCESS.md)).

---

## Rollback

The branch is disposable and the pre-rename tree was clean:
```bash
# ▶ run yourself
git checkout New-GUI-Interface        # abandon; delete branch with: git branch -D M3-1-rename-sloads
```

## Gotchas

- **BSD vs GNU sed.** macOS needs `sed -i ''` (empty backup arg); GNU is
  `sed -i`. All commands here are the BSD form.
- **Don't sed the attribution strings** — `app/Home.py:235`, README/McMaster
  citations, historical `.md` reviews. The Step 9 grep must find *only* these.
  The rename seds target lowercase `farloads`, which leaves "FAR 23 LOADS" prose
  alone by construction — but review every `.md` diff.
- **`$ FAR23LOADS` ↔ `test_workbook.py:114`.** If you rebrand the sbeam export
  header, change the test assertion in the same commit.
- **Delete `farloads.egg-info/` before reinstalling** (Step 6) so no stale
  `farloads` entry-point script survives. `_to_delete/` and `_staging_tmp2/` are
  untracked — remove freely.
- **Off-limits:** registry `MODULE_NAME` values, JSON schema keys, session-state
  keys — they contain no `farloads`, so the sed skips them; never hand-edit them
  (saved projects must keep loading; `SCHEMA_VERSION` stays 32, no schema change).
- **Package-relative imports** (`from .models import …`, 32 sites) carry no
  `farloads` token — the sed won't touch them; they rely on the re-exporting
  `sloads/models/__init__.py` from Step 3.
