- **The wing carry-through is entered as a fuselage station (design note 50, tier L, 2026-09-05).**
  `SurfaceInput.front_spar_pct`/`.rear_spar_pct` are replaced by
  `front_spar_x_in`/`rear_spar_x_in` — the station itself, in the geometry page's
  length channel (**schema v60 → v61**). A chord fraction is taken on the
  centreline root chord while the wing-attach fittings are at the fuselage, so on
  a swept or cranked wing no value of the fraction could express the station:
  `ga6_normal`'s MAC leading edge sits 18.6 in aft of its root leading edge, which
  is also why %MAC was ruled out as an entry unit (20 % root chord is 2.28 %MAC
  there) and why the stored datum is a global X that does not migrate when
  somebody refines the planform (OR-121, OR-126).
- **A blank spar station derives, and says so on the page (design note 50, tier L, 2026-09-05).**
  The pair is a note 36 collapsed override — blank derives, typed overrides — so
  the geometry page states the station the analysis will actually use
  (*"Blank — derives from 20 % of the root chord (currently 65.20 in). Enter a
  value only to override."*) without writing it into the project. Accepting the
  estimate therefore stays visibly an assumption: `CarryThrough.assumed` is True
  exactly when nobody entered a station, and a page visit cannot promote a
  derived station to an entered one (OR-123, OR-126).
- **The assumed carry-through moves to 20 % / 60 % of the root chord (design note 50, tier L, 2026-09-05).**
  From 15 % / 65 %, in `constants.DEFAULT_FRONT_SPAR_PCT`/`_REAR_SPAR_PCT`, which
  are now the estimator for an unentered station rather than a stored input's
  fallback. On `ga6_normal` the carry-through moves from x = 60.15–110.65 in to
  65.20–105.60 in and the front fitting load moves −1.5 % / −11.6 % / −10.6 % /
  −4.2 % across the four fuselage conditions; `baron_58` moves further (−25.9 %
  to −33.4 %). **No printed oracle moves** — Ch 15 ships none — so the acceptance
  is the module's own equilibrium-closure gates, re-run and green, and the
  Imperial baseline is regenerated in the body channels only (OR-122).
