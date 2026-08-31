- **Section 2 of the oracle technical report — Loads Configuration (note 44 OR-38…OR-44,
  tier L, 2026-08-30).** The report's first analysis section: 2.1 Geometry, 2.2 Weight and
  Mass Properties, 2.3 Structural Design Speeds, 2.4 Flight Envelope, grouped as
  subsections of one numbered section so every workflow step keeps exactly one home
  (G-OR-2 unchanged). 2.3 prints each design speed and limit load factor beside the
  FAR 23 minimum computed for it, with no compliance verdict — that is the reviewer's
  finding. 2.4 draws one V-n diagram per loading and altitude block, the boundary a
  polyline through the design points FLTLOADS produced, with gust cases marked
  separately and VA/VC/VD as reference lines. New owners: `sloads/report/oracle_sections.py`
  (one content builder per step key), `oracle_content.DOCUMENT_TITLES` (the document
  names its own sections rather than borrowing the GUI's navigation labels) and
  `oracle_content.SECTION_GROUPS` (grouping declared as data, members guarded contiguous).

- **Section 2 states the configuration in full (note 44 OR-45…OR-47, tier L, 2026-08-30).**
  2.1 carries one table per surface — wing planform, horizontal tail and elevator, vertical
  tail and rudder, aileron, flap, and each trim tab — with areas, planform figures, tail arm
  stations and control deflections. 2.2 adds the weight and centre-of-gravity cases: name,
  role, weight, Xcg, Zcg and analysis, under a note explaining which load families each
  analysis tag feeds and which of the landing analysis's three positional loadings a ground
  case's role supplies. These are the first values the report reads from the project rather
  than from a `ModuleResult`, so the section states once that they are the configuration as
  entered, and the G-OR-3 guard was widened from "every number came from a result" to "every
  number came from a result or from the project as entered, and none is invented".
