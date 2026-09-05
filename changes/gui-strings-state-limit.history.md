- **The GUI states LIMIT, and the sweep that found it becomes a gate (#192,
  tier M, 2026-09-05)** — design note 49 removed the safety-factor multiply from
  81 sites and left every delivered load LIMIT, then closed the prose surface
  with **G-OR-74**, whose scope sentence reads *"rendered output only: what a
  recipient actually reads."* A Streamlit caption is exactly that, but the
  checker only ever read the documents note 49 enumerated — the summary and
  oracle reports, the methods stamp, the workbook, the package README — so the
  **GUI was gated by nothing at all**, and the AST sweep the note describes
  stayed a discovery pass rather than becoming the standing check its own
  finding argued for. Twenty-one live false claims survived in fifteen `app/`
  files. The sharpest is a download button: *"Download net wing loads —
  ULTIMATE (CSV)"* over `sb.span_load_csv`, whose station-0 `Sz` for `ga6_normal`
  case PHAA writes `5831.6` beside `SF,1.5` while the module's LIMIT value is
  `5831.646378463103` — the same number, so a reader who believed the label
  under-sized by a factor of 1.5. The rest are captions asserting *"the
  Review/Export pages report **ULTIMATE** = limit × 1.5"* on six control-surface
  and landing pages, and *"Load columns are **ULTIMATE** (limit × SF)"* on
  Results Review and the Flight Envelope SELECT tab.
  Fixing the strings was the smaller half. The durable half is rule 3: the sweep
  is now `test_no_gui_string_claims_ultimate`, walking the `app/` and
  `app_shell/` **sources** with `ast` and asserting each non-docstring literal
  through the same `assert_states_limit` the document gates use — one checker,
  not a second implementation of the rule (P-1). Source-walking rather than
  driving Streamlit is deliberate: these claims are static text no session state
  can alter, and an AST pass cannot miss a page whose branch a journey test never
  entered. Docstrings stay excluded on G-OR-74's own scope rule, and
  `oracle_app/` stays out because it is frozen under OR-13 and its three claims
  are filed, not fixed (OR-14).
  Widening the gate exposed two defects in the *checker*, both of the class the
  gate exists to prevent. `_CLAIMS` was a list of substrings, so
  `**ULTIMATE** = limit` escaped it — markdown emphasis split the phrase — and
  `limit × SF` escaped it because the pattern spelled the multiplication sign
  ASCII `x` where every artifact writes U+00D7. A gate defeatable by typography
  is not a gate; text is now normalised (emphasis, dashes, `×`) before scanning,
  and the patterns are regexes whose boundary excludes a trailing hyphen, which
  removes the one false positive the widening produced — Structural Speeds'
  perfectly true *"All speeds are ULTIMATE-independent design limit speeds"*,
  which a bare `\b` had matched and which would otherwise have needed a
  hand-written exemption, the very mechanism `_SANCTIONED` is documented as
  avoiding. Each pattern now carries a witness quoted from the artifact that
  shipped it, and the meta-test asserts both directions: every witness fails the
  gate, and every pattern catches some witness, so a pattern cannot rot into one
  that matches nothing unnoticed.
  One find was not a string at all.
  `test_deliverable_units.py::test_the_export_page_states_the_system_it_will_write`
  asserted the Export page caption **contains** "ULTIMATE" — a green test
  requiring the false claim, which is why the residue could not have been found
  by making the suite stricter alone. It now requires LIMIT.
  A second-order consequence settled a display question. The Wing and Fuselage
  pages offered two downloads distinguished *by basis* — LIMIT table versus
  ULTIMATE bridge — and OR-116 made both LIMIT, so the distinction the labels
  drew no longer exists and swapping the word would have produced two adjacent
  buttons with identical labels over different bytes. They are relabelled by
  **channel** (*analysis table* / *sbeam bridge*, owner ruling 2026-09-05),
  the vocabulary `CONVENTIONS.md` already uses internally, with the shared LIMIT
  basis stated once beneath them. The `*_ULT.csv` file names are left alone:
  OR-81 retires them in 0.8.3, and until then a truthful label over a stale name
  is strictly better than the reverse.
  No calc changes and no schema hop. `app/views/` is pre-assigned to the #29
  rework, and touching it now is a deliberate exception taken on rule 6 — a
  defect with first-order effect on shipped content outranks the freeze, and the
  alternative was shipping the 0.8.2 report beside a GUI contradicting it.
  `CONVENTIONS.md` §OR-117 and `00_program_overview.md` carry the widened G-OR-74
  scope; note 49's gate section records the widening and both checker defects.
