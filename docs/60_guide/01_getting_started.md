# Getting started

## Install and launch

From a clone of the repository, create the environment once:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Then launch the oracle GUI either way:

```bash
.venv/bin/streamlit run oracle_app/Oracle.py
# or, equivalently:
.venv/bin/sloads-oracle
```

Streamlit opens your browser (or prints a local URL to open yourself). There
is no separate home screen: you land directly on the first analysis page,
**Geometry**, with a new empty project. The pages listed down the left side
are the whole tool, in working order — enter each page's data, read its
results at the bottom, and move to the next.

## What a "project" is

Everything you type describes one airplane, held in one file:
`<name>.project.json`. That single file is the whole analysis input —
geometry, weights, speeds, coefficients, gear — and both this GUI and the full
`app/` GUI read and write the same format. Values are stored in one canonical
unit system regardless of how you chose to view them (see
[Conventions](03_conventions.md)), so a project made in SI opens identically
for an Imperial-minded colleague.

Nothing is saved until you save: the browser session holds your edits, and
the sidebar tells you when they are unsaved.

## The sidebar

The sidebar appears on every page. From top to bottom:

### Units

**Reported results in — Imperial / SI.** A display choice, not a data one:
results and input widgets re-render in the selected system, while the stored
project and the calculation are unaffected. Airspeeds (KEAS) and altitudes
(ft) are aviation-standard in both systems and never convert. Toggle it
whenever you like — [Appendix B](B_worked_twin.md) closes by reopening the SI
twin in Imperial to show the same loads.

### Project file

- **Project name** — names the saved and downloaded file. Set it early: the
  name is the identity every save writes to.
- **The dirty indicator** — 🟠 *Unsaved changes* / ⚪ *No unsaved changes*.
  It diffs your session against the last loaded or saved state, so undoing an
  edit by hand genuinely clears it.
- **📂 Open** — three ways in:
  - **Saved projects** lists the `projects/` directory beside the app; pick
    one and press **Open**.
  - **New from example** loads a bundled example — `ga6_normal` and
    `baron_58` are this guide's two worked airplanes — as a fresh unsaved
    project.
  - **Upload project.json** loads a file from anywhere via the browser.
  Opening over a dirty project asks before discarding your edits.
- **💾 Save to disk** writes `projects/<name>.project.json` beside the app —
  a fixed location, no dialog; files there appear under **Saved projects**.
- **Download project.json** hands the same file to your browser, which
  chooses where it goes. A downloaded file dropped into `projects/` is listed
  by Open too. The caption under the buttons states both routes.
- **Results zip** — builds every page's result tables against the current
  project and downloads them as one archive, with a manifest naming any page
  that refused to run and why.

## Working through the pages

Each page is a form over one analysis step, with the step's results rendered
below the form and offered as per-table downloads. The pages are ordered by
data flow: a page that needs an upstream quantity says so in plain text until
the earlier page has what it needs (the exact messages are decoded in
[Appendix C](C_troubleshooting.md)). Three entry habits worth forming
immediately, all stated on the pages themselves:

- **Commit a grid cell with Tab, not Enter** — Enter leaves the cell's editor
  open, and the next keystroke discards what you typed.
- **Grid rows with an empty cell are not saved** — fill every column to keep
  the row. A row added with a **row counter** is part of the project as soon
  as it appears, blank or not: fill it in, or count back down to delete it.
- **Some blocks start off the page, behind an "Add" button** — a section your
  airplane may simply not have (a flaps-down coefficient set, a Mach limit, a
  weight envelope) shows a caption naming the fields it holds and an **➕ Add**
  button instead of the fields. Click it when the airplane has that thing; the
  fields appear, blank, and are yours to fill. Nothing is added to the project
  by looking at a page, or by touching anything on it. The matching **🗑
  Remove** control at the foot of the block takes the whole section away again,
  with everything entered in it.

Start with [Before you start](02_before_you_start.md) so the numbers are on
your desk before the forms ask for them.
