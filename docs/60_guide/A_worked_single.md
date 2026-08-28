# Appendix A — Worked example: the single (`ga6_normal`)

The manual this suite replicates prints, in its own Appendix A, a complete
worked case: a 6-place, 3,400-lb general-aviation single with a Continental
IO-520-BB, carried through every program with its inputs and outputs
listed. `ga6_normal` **is** that airplane, and this appendix is the
end-to-end pass: load it, walk the pages top to bottom, and the numbers on
your screen reproduce the book's. It is the strongest verification a user
can run — not against this tool's own tests, but against an independent
printed record.

Load it from the sidebar (**New from example → `ga6_normal`**), leave the
units on **Imperial** — the whole point is digit-for-digit comparison with
the book — and keep [Conventions](03_conventions.md) in mind: the book
prints **LIMIT** loads, so compare against the LIMIT-marked station tables
directly, and divide any ULTIMATE figure by its stated SF before comparing.

## The pass

Each stop below is one page; the chapter linked carries the full input
walkthrough and the *why* of every value.

1. **[Geometry](01_configuration_layout.md).** The kinked three-point wing
   leading edge, the aileron at butt lines 109–190, the Appendix A tail
   scalars (`xt25 = 261.027`). Check the derived MAC against the book's
   planform chapter before moving on.
2. **[Weight & Mass Properties](02_weight_mass.md).** The book's loading
   list row for row — pilot through sixth person, 30-minute fuel, fuel to
   gross, ballast — envelope 20–31 % MAC at 3,400 lb, the four flight CG
   cases `CG1`…`CG4` and the three landing corners.
3. **[Aerodynamic Data](03_aero_coefficients.md).** The printed polars,
   exactly: CLmax 1.4068 / −0.59 / 1.5857 and the fitted lift, drag and
   moment polynomials.
4. **[Structural Speeds](04_structural_speeds.md).** Category N; VC chosen
   170 kt, VD 212.5 kt (1.25 × VC); the derived factors and VA.
5. **[Flight Envelope](05_flight_envelope.md).** Sea level only, tail CP
   stations 253.364 / 261.027. The balanced matrix and SELECT's critical
   set reproduce the book's balancing-tail-load chapter — the elevator
   angle of the retracted balancing case reads −5.39° in the book's case
   202, and the page's aero-state rows are where you find it.
6. **[Wing Loads](06_wing_loads.md).** PHAA, TORS and ACRL with the
   printed factors; the spanwise LIMIT table against the book's `NETLOADS`
   output.
7. **[Fuselage Loads](07_fuselage_loads.md).** The five body lumps about
   waterline 55; the distributed body cases.
8. **[Tail Loads](08_tail_loads.md).** The chordwise distributions of the
   selected cases against the book's tables.
9. **[Aileron](09_aileron_loads.md), [Flap](10_flap_loads.md) and
   [Tab](11_tab_loads.md) Loads.** The three simplified-method surface
   loads, each a one-block comparison.
10. **[Engine Mount](12_engine_mount.md).** The IO-520-BB set — with the
    one **approved deviation**: the takeoff-torque case is deliberately
    higher than the book's (the corrected mean-torque factor), per the
    [approved-corrections register](../20_theory/02_approved_corrections.md).
11. **[One Engine Out](13_one_engine_out.md).** Withheld on this airplane —
    one centreline engine, no condition — which is itself the correct
    Appendix A behaviour.
12. **[Landing Loads](14_landing_loads.md).** The energy inputs and the
    typed 2.5 design gear factor beside the computed value; the wheel-load
    matrix.

## Checkpoints

A short list of printed figures worth checking by eye, with where the book
states them. The suite's oracle lock holds every one within ±0.1 %; these
are the ones a human can verify in a minute. (LIMIT values, as printed.)

| Figure | Book value | Where printed |
|---|---|---|
| Balancing case 202 elevator angle | −5.39° | Ch 9 balancing tail loads |
| Landing sink rate V | 9.0048 ft/s | `LGFACTOR.OUT`, Appendix A p236 |
| Landing load factor N | 3.0951 | same |
| Gear load factor NLG | 2.4281 | same |
| Gear geometry constant K | 0.324 | `LANDLOAD.OUT`, Appendix A p230 |
| Level-landing main-wheel vertical (case 1) | 3,144 lb | `LANDLOAD.OUT`, Appendix A p231 |
| Takeoff-case mean engine torque | 554.39 lb-ft | `ENGLOADS`, Appendix A — **reported factored** (see the deviation register) |

A figure that does not reproduce means an input drifted from the book's:
re-load the untouched example and diff your project against it before
suspecting anything else.

## What this pass proves

That the chain you will run on your own airplane — the same pages, in the
same order — reproduces an independent published record end to end. When
you then type your own design and a number looks surprising, the working
instinct this appendix builds is: *the tool is oracle-locked; check the
input first.*
