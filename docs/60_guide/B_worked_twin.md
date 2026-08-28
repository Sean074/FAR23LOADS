# Appendix B — Worked example: the twin (`baron_58`)

The second end-to-end pass: a Beech Baron 58 light twin — two Continental
IO-550-C on the wings — built from its FAA type-certificate data and
entered, worked and read **entirely in SI**. It exists for two reasons the
single cannot serve: the twin is what makes the engine-mount and One
Engine Out chapters real, and running a whole airplane through in SI is
what proves the unit boundary rather than merely asserting it.

Load it (**New from example → `baron_58`**) and set the sidebar units to
**SI**. Every value below reads in SI on your screen; the stored file is
canonical Imperial throughout, which is the point this appendix closes on.

## The data, and its honesty

The twin's source situation is the *normal* one for a metric user: the
authoritative data — FAA Aircraft Specification 3A16, the POH — is
published in Imperial. The guide does not hide that; the conversion
happens **at the point of entry**, in the tool, not in a spreadsheet
beforehand. And unlike the single, no complete input record exists: the
certificate gives weights, CG limits, speeds, engines, propellers and
principal dimensions, and everything else — mass breakdown, chords, tail
areas, aero coefficients, gear detail — is an **estimate, marked as such**,
item by item, in
[`examples/baron_58.sources.md`](../../examples/baron_58.sources.md).
Read that register alongside this pass: knowing which numbers are
certificate and which are construction is the discipline the example
teaches.

## The pass

1. **[Geometry](01_configuration_layout.md).** Span 11.53 m and area
   18.51 m² are the certificate's; the chords are constructed so the
   unswept quarter-chord lands on the certificate's front-spar datum
   station (2,111 mm aft of datum). Twin-wing engine layout; the published
   2.92-m gear track.
2. **[Weight & Mass Properties](02_weight_mass.md).** MTOW 2,495 kg and
   MLW 2,449 kg from the certificate; the 1,819-kg empty weight split
   statistically; seats and fuel at the certificate's arms. The CG
   envelope corners are the certificate's station limits (1,989–2,184 mm
   at gross). Each ground case states its loading — who is aboard, how
   full the tanks — and the page checks the arithmetic.
3. **[Aerodynamic Data](03_aero_coefficients.md).** All estimates,
   anchored: the CLmax pair is constructed from the published stall
   speeds, so the tool's derived 1-g stall reads them back — run the
   envelope and check.
4. **[Structural Speeds](04_structural_speeds.md).** VC entered as the
   published Vno (195 kt — still knots in SI, the carve-out), VD as the
   0.9-rule construction from Vne, VA left to derive and landing within a
   few knots of the certificate's operating VA.
5. **[Flight Envelope](05_flight_envelope.md).** Three altitudes; the
   geometry-derived tail CP suggestion accepted; three certificate-corner
   CG cases balanced across all of it.
6. **[Wing](06_wing_loads.md) and [Fuselage](07_fuselage_loads.md)
   Loads.** The twin's substance: the concentrated list hangs the engines,
   propellers, gear and fuel on the wing per side, and the fuselage lumps
   carry only what the body really carries. The engine step in the
   spanwise shear curve at butt line ±1.68 m is the picture to look at.
7. **[Tail](08_tail_loads.md), [Aileron](09_aileron_loads.md),
   [Flap](10_flap_loads.md), [Tab](11_tab_loads.md) Loads.** As the
   single, with the flap slipstream now a real case: two wing-mounted
   discs directly ahead of the flaps, the washed band at the nacelle butt
   line.
8. **[Engine Mount](12_engine_mount.md).** Two identical IO-550-C records
   (224 kW at 2,700 rpm; 196-kg engines, the certificate's 1.96-m
   McCauley propellers at 37.4 kg) — torques in N·m on screen, two
   mirrored condition sets.
9. **[One Engine Out](13_one_engine_out.md).** The chapter the twin
   unlocks: fail the left engine at takeoff power and read the transient
   at each speed — and note the mixed LIMIT/ULTIMATE classifications each
   case's note states.
10. **[Landing Loads](14_landing_loads.md).** Estimated energy inputs on
    the published track; the computed gear factor carried through
    un-rounded, because no certificated design factor is published to
    round to.

## Closing the loop: the channel itself

Finish the pass with the demonstration the whole example was built for:

1. **Save** the project (or download it) with SI still selected.
2. Open the file in a text editor: the stored values are **Imperial** —
   the certificate's 5,500 lb is stored as 5,500, not 2,495. Nothing you
   entered in SI was stored in SI.
3. Reopen the project in the tool and flip the sidebar to **Imperial**:
   the same airplane, the same loads, every table re-rendered in the other
   channel — differing by unit conversion and nothing else.

The toggle is a display boundary; the project is channel-free. That is a
property the test suite guards structurally — what this appendix adds is
that you have now *seen* it hold on an airplane you worked yourself.
