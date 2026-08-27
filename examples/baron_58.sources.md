# `baron_58.project.json` — data sources register

The oracle GUI user guide's worked twin (design note 34, UG-9): a Beechcraft
**Baron 58**, normal category, two Continental **IO-550-C** — the
configuration of Model 58 serials **TH-1396 through TH-2124** (plus TH-1389).

**Construction rule (UG-9).** Every certified value below is cited to the
document it was read in. Everything not published — mass breakdown, planform
chords, tail areas, nacelle butt line, aero coefficients — is **estimated**,
marked **[E]**, and never presented as the airplane's certified value. The
example exists to teach the tool; where an estimate is load-bearing the guide
says so. Stored values are Imperial (the project file's canonical channel);
the guide enters and reads this example in **SI** (UG-12).

## Primary sources

| Tag | Document |
|-----|----------|
| [A] | FAA Aircraft Specification **3A16, Rev 82** (Jan 31 2007), Section X (Model 58) and propeller item 13 |
| [B] | Beechcraft **Baron G58 Specification and Description**, Feb 2016 Rev A (Textron Aviation) — same airframe as the late Model 58 |
| [C] | Baron 58 **POH/AFM 58-590000-21**, Section II (airspeed limitations) and the flight-load-factors page |
| [E] | Estimated: statistical GA-twin value, or derived from the constructed planform. Not certified data. |

## Certified / published values used

| Quantity | Value | Source |
|----------|-------|--------|
| Certification basis, category | CAR 3 (as amended May 15 1956), **Normal** | [A] |
| Max takeoff weight | 5,500 lb | [A] |
| Max landing weight | 5,400 lb | [A] |
| Basic empty weight (typical) | 4,010 lb | [B] |
| CG limits | +78.3 to +86.0 in at 5,500 lb; +78.0 fwd at 5,400 lb; +74.0 to +86.0 at ≤4,200 lb | [A] |
| Datum | 83.1 in forward of the front-spar jack pads | [A] |
| Vne / Vno / Va / Vfe(30°) / Vle | 223 / 195 / 156 / 122 / 152 kt CAS | [A], [C] |
| Engines | 2 × Continental IO-550-C, 300 hp at 2,700 rpm (all operations) | [A] |
| Propellers | McCauley 3AF32C512 / 82NEA-5, 3 blades, 77 in dia, 82.5 lb each | [A] item 13 |
| Wing span / area / dihedral / c/4 sweep | 454 in / 199.2 ft² / 6.0° / 0.0° | [B] |
| Horizontal tail span | 191 in | [B] |
| Overall length | 358 in | [B] |
| Main gear track | 115 in | [B] |
| Usable fuel (standard) | 136 US gal at arm +82 | [A] |
| Seats / occupant arms | 6 (2 at +75, 2 at +117, 2 at +150) | [A] |
| Baggage | 300 lb at +15 (nose); 400 lb at +150 (rear) | [A] |
| Limit maneuver load factor | +4.2 g flaps up (POH figure at 5,400 lb; entered as ENGLOADS' LIMNZ — FLTLOADS derives its own 23.337 value) | [C] |
| Airfoils | NACA 23016.5 root / 23010.5 tip (UIUC airfoil-usage guide, secondary) | [E]-class |
| Engine dry weight | 433 lb (IO-550 family, secondary reference — not read from TCDS E3SO) | [E]-class |

## Estimated values [E] and their anchors

- **Wing planform**: root 84 in / tip 42 in (taper 0.5). Anchored: the
  straight quarter-chord this gives sits at sta 83.0 ≈ the front-spar jack
  pads at 83.1 [A], and the trapezoid area (198.6 ft²) is within 0.3 % of the
  published 199.2 ft² [B]. MAC 65.3 in at buttline 101, x-LEMAC 66.7 — the
  WTENV %-MAC limits in the file are the [A] station limits through this MAC.
- **Tail areas**: h-tail 53 ft² on the published 191-in span; v-tail 24.3 ft²,
  66-in span. Statistical GA-twin proportions; tail stations placed against
  the published 358-in length [B].
- **Nacelle butt line ±66 in**: outboard of the 57.5-in gear half-track [B]
  (the mains retract into the nacelles), giving the 77-in prop [A] ~28 in of
  fuselage clearance.
- **Chosen Vd 248 kt**: from Vne = 0.9 Vd with the published Vne 223 [A]. No
  design dive speed is published.
- **CLmax clean 1.15 / flaps 1.53**: derived from typical published stall
  speeds (~84 kt clean, ~73 kt landing) at MTOW through the constructed wing
  loading — the module's clean 1-g stall reproduces ~84 KEAS.
- **Mass breakdown**: statistical component split summing to the published
  4,010 lb empty [B] at sta 78.3; discretionary rows (occupants, baggage,
  fuel) sit at the [A] arms. The flight loading of 120 US gal fuel + 4
  occupants closes at exactly 5,500 lb inside the [A] envelope, and each
  roled ground case **states its loading** (D-25 `loading` records): aft max
  landing 5,400 lb at sta 85.7, fwd max landing 5,400 lb at sta 79.1, fwd
  light 4,440 lb at sta 78.1 — all inside the [A] limits. Inertias are
  order-of-magnitude estimates.
- **Gear geometry**: axle stations/waterlines, 8-in oleo stroke, 20-in tire —
  statistical; tread is the published 115 in [B], oleo strut type per the
  Baron's air-oil gear.
- **Aero coefficients** (section slope 0.107/deg, cm −0.008, polar, twist,
  elevator/rudder throws and hinge splits, tab data): handbook-typical values
  for the 230-series sections and a GA twin; none are published data.

## Cross-checks the file passes

- Loads every page of the oracle GUI; all 14 run without error (gate G-UG-4,
  `tests/test_guide.py`), including ONENGOUT with the off-centreline failed
  engine.
- No `validation.consistency_warnings` on load: loading CG inside the WTENV
  envelope, the G-4/G-14 weight chain, the note-29 wing-mass tie
  (items tagged `wing` = 2 × (WINGINER panel + concentrated)) all close.
- The oracle **reduction reproduces it exactly** (`tests/test_oracle_inputs.py`
  `EXACT`): every load-bearing field is an original-suite input — engine and
  propeller weight/CG are entered directly on the ENGLOADS records (duplicated
  into the weight database rows at the same values, the cessna_210 pattern).
