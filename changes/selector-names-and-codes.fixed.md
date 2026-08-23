- **Selector names are seeded, unique and case-insensitive; the category and
  strut type are codes, not text** (review 2026-08-22 PB-5 / PB-8 / PB-9,
  issue #63, tier M, 2026-08-23). The names the calc keys on — surface, CG
  case, coefficient set — were seeded `""` by the oracle form with no
  uniqueness check, so two CG cases with one name collapsed to one entry and
  TAILDIST changed in 7 of 13 rows while every page reported success.
  `sloads/selectors.py` is the owner: `select.py` builds every CG-case and
  coefficient-set lookup through `keyed`, which refuses a duplicate by name;
  `render_step` runs `duplicate_selectors` after each persist and withholds
  the page's results while a name is duplicated or blank; `NAME_SEEDS` names a
  new row (`wing` first, then `CG1 … CGn`, `CRUISE` / `LANDING`), skipping
  names already taken and never counting as a touch, so a visit still dirties
  nothing. `GeometryInput.by_name` / `AeroInput.by_name` match through
  `models.same_name` (case and edge spaces forgiven), so a surface named
  `Wing` no longer blocks eight pages, and the blocked note names the
  workflow's Geometry step instead of a page this GUI does not have. The FAR
  23 category and the strut type are codes from `models.CATEGORIES` /
  `STRUT_TYPES` (`field_registry.CODED_FIELDS` says which `str` fields carry
  one): the oracle form offers them as a choice (an unknown stored value stays
  visible, marked), the `app/` views drop their private copies of the same
  tables, the owners upper-case at construction (`"u"` is Utility), and every
  consumer goes through `normalise_code`, which refuses `"Utility"` by name
  instead of reading it as Normal's 3.8.
