# 2. Weight & Mass Properties

*Original program(s):* `WTESTIMA+WTONECG+WTENV`.

## What this page is for

Three of the original programs share this page because they share one
subject: what the airplane weighs and where that weight is. `WTESTIMA` makes
a statistical first estimate of empty weight from top-level facts (seats,
horsepower, engines). `WTONECG` sums an itemized weight database into total
weight, CG and moments of inertia. `WTENV` builds the structural CG envelope
— the weight-vs-CG boundary the load analyses are run at. Everything mass
that any later page uses — the wing inertia relief, the fuselage mass
distribution, the landing CG cases, the one-engine-out yaw inertia — reads
from what you enter here.

## Before this page

Nothing upstream is required to start entering data, though the CG results
mean more once [Geometry](01_configuration_layout.md) exists (the envelope is
stated in % MAC, and the MAC comes from your wing). Have the weight
statement or equipment list, the certified design weights and the CG limits
on your desk.

## The inputs

The generated field table for this page:
[`_generated/weight_mass.md`](_generated/weight_mass.md).

**Design weights.** Max takeoff weight and max landing weight — the two
certified weights the load analyses hang from. They must respect the chain
*empty ≤ MLW ≤ MTOW ≤ everything in the database*: you must be able to land
with reserves, and you cannot weigh more than everything you have. The page
warns when the chain breaks.

**Weight estimate.** `WTESTIMA`'s inputs: an airplane description, engine
count and continuous horsepower, seats, crew, cruise hours, baggage,
pressurisation, and the engine-weight class code. The estimate it produces
is **advisory** — shown beside your entered empty weight with the difference
— and nothing downstream computes with it. Use it as a plausibility check on
the database you enter next, or as a starting point when you have no weight
statement yet.

**Weight items — the database.** One row per mass item: name, weight, and
its (x, y, z) position in inches, with optional moments of inertia for the
items big enough to carry their own (engines, wing). Three kinds sort the
loading hierarchy: **empty** (the airframe), **minimum** (aboard for any
flight — unusable fuel, oil), **discretionary** (payload and fuel you choose
to load). A **consumable** row can burn down to a fraction; the **component**
tag (wing / fuselage / h-tail / v-tail) states which structure reacts the
weight — it is explicit because most rows sit on the centreline and no
geometry can infer that an engine hangs on the wing. This database is the
single source of truth for mass: every later mass quantity is derived from
it.

**CG envelope.** `WTENV`'s corner data: gross weight, the forward and aft
gross limits in % MAC, and the "forward regardless" light-weight corner with
its weight. The certified limits arrive in inches; the page shows the
conversion through your wing's MAC.

**Weight & CG cases.** The discrete loading points the analyses run at.
Flight-tagged cases are the CG points `FLTLOADS` balances at; ground-tagged
cases are the three roled landing loadings (`aft max landing`,
`fwd max landing`, `fwd light`) that `LANDLOAD` requires. A case can simply
state weight and CG, or it can **state its loading** — which discretionary
rows are aboard and how full each consumable is — and let the page check
that the stated weight and CG are what that loading actually sums to.

**Wing weight for SELECT.** The wing structural weight the selection program
subtracts as inertia relief; enter the same wing weight your database
carries.

**Tail surface mass.** An optional per-surface override of the empennage
mass that is otherwise derived from the component-tagged database rows.

## Screenshots

![The Weight & Mass Properties page with the Appendix A single loaded: the
estimate block, the item database and the envelope](img/02_weight_mass__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

The database is Appendix A's own loading list, row for row: airframe
components (wing, tails, gear, engine install, propeller, fuselage
structure), then the manual's loading sequence — pilot, copilot, third
through sixth person, 30-minute fuel, fuel to gross weight, and the ballast
row the book itself carries. Gross weight 3,400 lb, MLW 3,230 lb; envelope
20–31 % MAC at gross with the forward-regardless corner at 13 % MAC / 2,800
lb. Four flight CG cases (`CG1`…`CG4`) reproduce the book's balance points,
and the three roled ground cases sit at the landing corners. With these rows
the page's computed weight and CG reproduce the book's — the printed case
this suite is oracle-locked against.

## Worked example — twin (`baron_58`)

The design weights and every arm are the type certificate's: MTOW 5,500 lb,
MLW 5,400 lb, seats at stations 75/117/150, fuel at 82, nose baggage at 15.
The empty-weight **split** is a marked estimate (the certificate publishes
the total, 4,010 lb, not the breakdown), with the engines and propellers on
wing rows at the estimated nacelle butt line ±66 in so the wing carries
them. The envelope corners are the certificate's station limits
(+78.3…+86.0 at gross, +74.0 forward at light weight) converted through the
constructed MAC. Each ground case **states its loading**: aft max landing
is mid+aft passengers with most of the fuel; fwd max landing is front seats,
nose baggage and fuel; fwd light is two front occupants only — three
loadings the database genuinely produces, all inside the certified
envelope. Sources and estimate markings:
[`examples/baron_58.sources.md`](../../examples/baron_58.sources.md).

## Results on this page

Three blocks, none of them loads (no LIMIT/ULTIMATE, no safety factors):
the **advisory estimate** beside your entered weights with the delta; the
**mass properties** of the itemized loading — total weight, CG position,
and the moments of inertia `WTONECG` computed; and the **CG envelope** as
`WTENV` built it. Sanity checks: computed empty weight and CG against the
weight statement; the all-aboard total against MTOW (it should exceed it —
you choose what to leave behind); inertias within the ballpark of published
values for the class; and the page's consistency warnings — a loading CG
outside the envelope, a broken weight chain, or wing-tagged mass that the
wing-loads page doesn't carry are each stated in words.

## Common mistakes

- **Treating the estimate as the answer.** `WTESTIMA` is advisory; the
  analyses read the item database. An estimate row seeded into the database
  still needs a real position.
- **Leaving component tags at fuselage.** A wing-mounted engine tagged
  `fuselage` moves its weight to the body beam and deletes the wing's
  inertia relief. Tag every row deliberately.
- **Arms from a different datum** than the geometry page. Same datum
  everywhere, always.
- **Ground cases at envelope corners the database cannot load.** The three
  landing cases are loadings, not aspirations — state the loading, or pick
  weight/CG the rows can actually produce; the page tells you when they
  cannot.
- **Forgetting inertias on the heavy items.** Zeros are accepted, but the
  one-engine-out yaw inertia and the gyroscopic terms are only as good as
  the Izz your database implies.
