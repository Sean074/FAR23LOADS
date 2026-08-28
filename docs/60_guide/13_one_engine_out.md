# 13. One Engine Out

*Original program(s):* `ONENGOUT`.

## What this page is for

`ONENGOUT` simulates the engine-failure condition of 14 CFR 23.367: one
engine's thrust decays while its windmilling propeller's drag builds, the
asymmetric couple yaws the airplane, the pilot's corrective rudder arrives
after a delay, and the program marches the yaw dynamics in time to find the
vertical-tail loads of the transient and the recovery. It is the page the
twin exists for: the condition is *defined* by an engine off the
centreline.

On a single-engine airplane this page **withholds its form** and says why —
with one centreline engine the yawing couple is identically zero and there
is no condition to analyse ([Appendix C](C_troubleshooting.md)).

## Before this page

[Engine Mount](12_engine_mount.md) must carry the engines — the failed
engine's power, propeller disc and butt line are the forcing function — and
the yaw inertia and CG default from the
[Weight & Mass Properties](02_weight_mass.md) database. The speeds evaluated
come from [Structural Speeds](04_structural_speeds.md).

## The inputs

The generated field table for this page:
[`_generated/one_engine_out.md`](_generated/one_engine_out.md).

**The event's timing.** Thrust decay time, windmill-drag build-up time, the
pilot's rudder travel time, and the integration time step. These are the
original program's inputs, and the customary values are short: the thrust
is gone in a fraction of a second, the drag arrives over a couple of
seconds, the rudder starts moving after the recognition delay the
regulation's method assumes.

**Which engine fails.** The failed-engine index on a multi — with identical
engines at symmetric butt lines the choice is a mirror; with different
installations, fail the critical one (and run both to prove which that is).

**Power basis.** Whether the live engine holds takeoff or max-continuous
power — the regulation's condition is at takeoff power; the choice is
yours to state, not the tool's to assume.

**State overrides.** Evaluation speeds (blank runs the design-speed set),
altitude, and the yaw inertia and CG — blank derives both from the weight
database, which is why the database's inertias matter
([Weight & Mass Properties](02_weight_mass.md)).

## Screenshots

![The One Engine Out page with the Baron twin loaded in SI: the timing
inputs and the failed-engine choice](img/13_one_engine_out__page-baron-58.png)

## Worked example — single (`ga6_normal`)

The page's honest answer for the single is the refusal: one engine on the
centreline, no condition. Nothing to enter, and the guide's Appendix A pass
skips it accordingly.

## Worked example — twin (`baron_58`)

Timing at the customary values — half-second thrust decay, two-second
windmill build, 0.3-second rudder travel, 0.05-second step — failing the
left engine at takeoff power, speeds left to the design set, inertia and CG
left to derive from the database. The results run the condition at VC and
VD and at the stall-speed floor: the derived clean stall stands in for the
minimum control speed per the manual's method, and on this airplane the
stall-speed case reports the transient honestly at the edge of
controllability. The published rudder-load history is where you see the
regulation's story frame by frame: thrust gone, drag grown, rudder in,
yaw rate peaked and recovered.

## Results on this page

One condition per evaluated speed. Read the classifications carefully —
this page mixes them deliberately, and each case's note states its basis:
the failure cases the regulation defines at ultimate report **ULTIMATE
with SF = 1.0**; the ones it defines as limit report **LIMIT × 1.5** as
usual; the stall-floor case is a stated substitution (clean stall for
minimum control speed) per the manual's method. Each case carries the
evaluated speed, the peak windmill drag and thrust asymmetry, the yaw-rate
peak and the vertical-tail loads of the transient and recovery.

Sanity checks: the asymmetric thrust at a given speed is roughly
`power × 0.85 / speed` in consistent units (the program's own relation);
the yaw forcing scales with the failed engine's butt line — a doubled arm
doubles the couple; and a "not recovered" verdict at a speed near stall is
the condition being genuinely below the controllable floor, stated in
band, not a crash.

## Common mistakes

- **Hunting for this condition on a centreline airplane.** The withheld
  form is the answer; see Appendix C.
- **Zero or placeholder inertias in the weight database.** The yaw
  transient divides by Izz; garbage in, garbage rate out. Enter the heavy
  items' inertias before trusting the time history.
- **Reading every case as SF = 1.5.** The mixed classifications are the
  regulation's own; the note on each case says which you are looking at.
- **A propeller with no disc.** The windmill-drag model is propeller
  physics; the page refuses a zero-diameter disc by name rather than
  reporting a zero-drag failure.
