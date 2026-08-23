- **The oracle GUI's project is the project gate G5 tests** (review 2026-08-22
  PB-1 / PB-2 / PB-3, issue #62, tier M, 2026-08-23). `Project.mass` has one
  writer: `sloads/derived.py:refresh_derived` (`weight_onecg.refresh_mass`),
  called by the `app/` Weight page on Apply, by the oracle form after every
  persist and by the G5 reduction — so a twin typed from blank reaches One
  Engine Out and Configuration's tip-back uses the Weight-DB CG (it read a
  25 %-MAC estimate: 33.1° vs 13.5° on the GA-6). `reduce_to_oracle_inputs`
  now really drops the stored result slices and the records the GUI never
  creates (a rotor row stayed, required fields intact), then re-derives; G5's
  comparison folds in the three station tables it never compared, and the
  one divergence that is decided rather than discovered — the twins' turbine
  rotors, a sloads model the original ENGLOADS never had — is declared per
  example with its number (−16 % DHC-8 mount torque) and checked to be
  exercised. `weight.items[].component` **and** `wing_fraction` are rendered
  on the oracle Weight page (`supplied`: the which-beam question BODYLOAD asked
  by position; the station tables showed the DHC-8 fuel row, 86 % wing, riding
  the fuselage beam whole), and the Fuselage Loads table states what it rests
  on — untagged items lumped by inference, an open wing-mass tie, a tail
  surface with no item. The gate's second leg, `tests/test_oracle_journey.py`,
  types the GA-6 and the DHC-8 from a blank project through the pages' own
  widgets and requires the result to be the reduced key — document, every
  download byte-for-byte, save → reload a fixed point; the scratch harness
  `scripts/oracle_journey.py` is retired into it. Along the way:
  `unit_number_input` stopped rounding its seed to four decimals (`format`
  owns display; the rounding read back as a different number to anything
  reading the widget), `FieldEntry.display_only` is the one rule behind the
  form's disabled copies and the journey's compare, and `ga6_normal` /
  `concept_heavy` carried a stored mass slice one ulp off its derivation
  (refreshed; `tests/test_derived.py` holds every example bit-identical).
