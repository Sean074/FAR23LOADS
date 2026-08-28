# 12. Engine Mount Loads

*Original program(s):* `ENGLOADS`.

## What this page is for

`ENGLOADS` computes the engine-mount design conditions of 14 CFR 23.361,
23.363 and 23.371: the limit torque cases (takeoff power, max continuous,
and the malfunction factors), the side load on the mount, and the
gyroscopic moments the spinning propeller adds under pitch and yaw rates.
It is the suite's one **standalone** program — every input is direct, none
comes from another module — and on this page each engine of a multi is its
own record, analysed in turn.

## Before this page

Strictly nothing — the program is standalone. Practically, the engine
count and placement came from the Geometry page's engine-layout selector,
and the airplane's limit load factor (which the torque cases combine with
1-g flight loads) should agree with the envelope you built. Have the
engine's type-certificate data sheet and the propeller's on your desk.

## The inputs

The generated field table for this page:
[`_generated/engine_mount.md`](_generated/engine_mount.md).

**Engine identity and ratings.** Designation, reciprocating/turbine class,
cylinder count, and the two rating points: takeoff horsepower at takeoff
rpm, max-continuous horsepower at its rpm. The mean torque every 23.361
case factors is horsepower and rpm, nothing else — these four numbers are
the load.

**Weights and positions.** Engine weight and CG, propeller weight, CG and
hub position — entered per engine, with the butt line carrying real
meaning on a twin (the One Engine Out yaw arm reads it). The optional
mass-item selectors can instead derive weight and CG from a named weight-
database row, keeping the value in one place.

**Propeller.** Diameter, blade count, and optionally a measured polar
inertia — blank, the tool approximates the inertia from weight and
diameter. The gyroscopic cases scale with this inertia directly.

**Factors and options.** The limit load factor the torque cases combine
with (blank derives the 23.337 value), torque overrides for engines whose
certificate states them, the sudden-stoppage time for turboprops, and the
per-rotor records a turbine installation adds. The FAR 25 supplemental
cases are an opt-in that leaves the FAR 23 output untouched when off.

## Screenshots

![The Engine Mount page with the Baron twin loaded in SI: the engine
selector and one engine's record](img/12_engine_mount__page-baron-58.png)

## Worked example — single (`ga6_normal`)

Appendix A's Continental IO-520-BB: 285 hp at 2,700 rpm takeoff, 265 at
2,500 continuous, six cylinders, 505 lb engine, 74-lb three-blade Hartzell
of 84-in diameter, limit load factor 3.8. One deliberate deviation from
the book is worth knowing when you cross-check: the manual left the
takeoff-torque case **unfactored** (an encoding of a regulatory drafting
error later corrected by amendment), and this tool applies the corrected
mean-torque factor — the printed Appendix A torque is therefore lower than
the reported one, and the deviation is documented in the
[approved-corrections register](../20_theory/02_approved_corrections.md).

## Worked example — twin (`baron_58`)

Two identical records — Continental IO-550-C, 300 hp at 2,700 rpm for all
operations (the certificate's single rating), six cylinders, 433-lb engine
(a secondary-source weight, marked), the certificate's 77-in McCauley
three-blade at 82.5 lb — at butt lines ±66 in, mounted on the wing. The
limit load factor is the POH's published +4.2. In SI display the weights
read in kilograms and the torques in newton-metres; the stored file is
unchanged. Each engine yields its own condition set, and on an identical
pair the two sets mirror.

## Results on this page

Per engine, the reciprocating set (all ULTIMATE, SF stated): the
**23.361 torque cases** (takeoff and max-continuous, with their mean-torque
factors) as mount torques combined with 1-g flight loads; the **23.363
side load**; and the **23.371(b) gyroscopic case**, expanded over its
sign combinations of pitch and yaw rate. A turboprop adds the sudden-
stoppage and malfunction cases. Sanity checks: the takeoff mean torque by
hand is `hp × 5252 / rpm` in lb-ft — the case value is that times its
factor; the gyroscopic moments scale with rpm and the propeller inertia;
and a twin's two engines should report identical numbers unless their
records genuinely differ.

## Common mistakes

- **Rating confusion.** Takeoff and max-continuous are separate cases with
  separate factors; an engine placarded with one rating (like the twin's)
  enters the same numbers in both, deliberately.
- **Propeller weight or diameter from the wrong propeller.** The certificate
  lists approved propellers; the gyro case scales with the disc you enter.
- **A limit load factor that disagrees with the envelope.** Left blank it
  derives the 23.337 value and cannot drift; typed (as both examples type
  it), it is your responsibility to keep it consistent with the Flight
  Envelope page after a weight or category change.
- **Expecting the book's unfactored takeoff torque.** See the approved
  correction above — the tool is deliberately more conservative than the
  printed oracle on that one case.
