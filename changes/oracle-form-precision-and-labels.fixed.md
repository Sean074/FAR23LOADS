- **Coefficients in the oracle GUI were displayed rounded to four decimals**
  (PB-22, issue #73, tier S, 2026-08-25). Every float widget carried
  `format="%.4f"`, so FLTLOADS' airplane-less-tail polynomials showed as
  `0.3205` and `0.0041` where the project held `0.320479` and `0.004128`. The
  stored value was never touched — but this GUI exists for a persona who reads
  the coefficients off the screen to check them against the manual, and a
  coefficient the screen rounds is one nobody can check. Precision is now a
  property of the quantity rather than of the page: `sloads.units.display_format`
  answers per `FieldUnit` — `%g` for a dimensionless value, four decimals for one
  carrying a unit, where `%g`'s six significant figures would *lose* precision on
  a station or an area — and no renderer in `oracle_app/` or `app_shell/` may
  write a format string of its own.
- **Fields whose leaf name is a code rather than a word were labelled with the
  code** (PB-22, #73, tier S, 2026-08-25). *Xt25*, *Xv50*, *Fwd Regardless Pct
  MAC* and *Elevator Aft Hinge* (an area aft of the hinge line, not a fitting)
  name nothing to a reader who does not already know the schema. ~20 of them are
  now hand-declared in `oracle_app/labels.py` beside the spelling table, with the
  same guard `MEMBER_LABELS` carries: a label for a field that is not in the
  input set fails the suite. An override replaces the field's *name* and never
  its unit, so a deflection cannot lose its degrees on the way through.
- **A rate in rad/s was labelled "Design Pitch Rate Rad (s)"** (PB-22, #73,
  tier S, 2026-08-25). The unit-suffix table was matched in declaration order,
  so `design_pitch_rate_rad_s` matched `_s` before `_rad_s` — the unit split in
  half with the other half left in the name. Matched longest-first now.
- **The one V-n field whose name gives no clue had help naming a different
  quantity** (PB-22, #73, tier S, 2026-08-25). `flight_loads.mn`'s registry basis
  read "FLTLOADS gust/manoeuvre matrix"; it is the Mach number the aero
  coefficients were obtained at (~0.1, FLTLOADS.BAS line 138), not a design Mach.
  The tooltip is built from the basis, so the row was the fix.
- **The airspeed unit nested its own parentheses** (PB-22, #73, tier S,
  2026-08-25). Widgets append a unit as `label (unit)`, and the unit string was
  `kt (EAS)` — *Chosen Vc (kt (EAS))*. It is **KEAS** now, the one word
  `CONVENTIONS.md` and every help string in the tool already use, declared once
  in `sloads/units.py` and re-exported by `app_shell/components.py` instead of
  spelled separately in both. A group of fields held on the project itself is
  captioned as such rather than as a schema path `` `(project)` `` that does not
  exist.
