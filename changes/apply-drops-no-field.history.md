- **Apply made loss-free across the main GUI (#36 part 1, tier M, 2026-08-21)** —
  `GUI_design.md` §6 already said *Apply merges targeted fields onto the existing
  slice*, and four forms had drifted off it by rebuilding their input dataclass
  from the widgets they render. The backlog entry named one symptom, the three
  unreachable landing-gear fields (`carrier`/`attach`/`weight_lb`, ranked #1 in
  the 2026-08-20 review's "first-order defect in shipped export content" row),
  but the measurement that opened the change found the reachability gap was the
  *smaller* half: the form did not merely fail to offer those fields, it **reset
  them on every Apply**, so a project that supplied them by hand lost them the
  first time a user pressed a button on the Geometry page. The fix gives the three
  fields widgets — the carrier as a three-way selector, because G-2 gives it no
  default and "not stated" has to survive a round trip rather than collapse to
  `BODY` — and, under rule 4, sweeps the class: the fin root waterline, the
  engine's `mounted_on` and the wing's profile-drag/section-Cm polars were being
  discarded the same way. The first guard written for it was an AST scan for
  dataclass constructions that name too few fields; it was **withdrawn before
  landing** because it could not separate a dangerous rebuild from a legitimate
  fresh construction and reported twenty-odd false positives, including every
  `Project(...)` in the codebase. What replaced it is behavioural and page-generic
  — press every Apply on every page with no widget touched, and fail if a stated
  value became unstated — which found the engine and wing-aero defects that the
  AST scan's noise had buried, and which was checked against a reverted fix to
  confirm it can actually fail (note 32 §8's lesson: a guard that cannot fail on
  its target is worse than none). The asymmetry is deliberate: Apply is allowed to
  seed `speeds.occupants` from the weight slice and to materialise an optional
  sub-record as explicitly disabled, so the invariant is *never delete*, not
  *never change*.
