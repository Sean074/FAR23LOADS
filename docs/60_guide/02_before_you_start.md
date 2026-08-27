# Before you start

The tool asks for real numbers from the first page on, and stopping mid-form
to hunt for a tail arm is the slowest way to work. Collect the material below
first. Each item names the chapters that consume it, so you can also work the
other way: open a chapter's *The inputs* section and read exactly what its
page will ask for.

## The checklist

| Have on your desk | What it must give you | Consumed by |
|---|---|---|
| **Three-view / general-arrangement drawing** | Wing, aileron, tail planform corner points in fuselage stations and butt lines; fuselage length, width, height; overall dimensions | [Geometry](01_configuration_layout.md), [Tail Loads](08_tail_loads.md) |
| **Weight statement / equipment list** | Component weights with arms (stations and waterlines); empty weight and its CG | [Weight & Mass Properties](02_weight_mass.md) |
| **Design weights and CG limits** | Max takeoff weight, max landing weight, forward/aft CG limits vs weight | [Weight & Mass Properties](02_weight_mass.md), [Landing Loads](14_landing_loads.md) |
| **Airfoil and wing aero data** | Section lift-curve slope, section pitching moment, CLmax clean and flapped, twist/washout, profile drag | [Aerodynamic Data](03_aero_coefficients.md), [Wing Loads](06_wing_loads.md) |
| **Speeds** | Certified or target VC/VD (or VH and category to derive them), stall speeds, flap speed | [Structural Speeds](04_structural_speeds.md), [Flight Envelope](05_flight_envelope.md) |
| **Tail geometry and control throws** | Tail areas/spans/arms, elevator and rudder areas and deflection limits, tab dimensions | [Tail Loads](08_tail_loads.md), [Tab Loads](11_tab_loads.md) |
| **Control-surface data** | Aileron and flap planforms, areas each side of the hinge, deflection limits, hinge/actuator stations | [Aileron Loads](09_aileron_loads.md), [Flap Loads](10_flap_loads.md) |
| **Engine and propeller data** | Engine designation, weight and CG; rated hp and rpm (takeoff and max continuous); cylinders; propeller designation, weight, diameter, blade count | [Engine Mount](12_engine_mount.md), [One Engine Out](13_one_engine_out.md) |
| **Landing-gear geometry** | Axle positions (extended/static/compressed), rolling radii, tread, strut type and stroke, tire outer and hub diameters | [Landing Loads](14_landing_loads.md) |

## Where the numbers come from

For a certified airplane, start from the **type certificate data sheet** and
the **POH/AFM**: weights, CG limits, speeds, engine ratings and propeller
limits are all there, with an authority you can cite. Geometry comes off the
drawing; what neither source publishes (mass breakdown detail, hinge splits,
aero coefficients) you estimate by a named method and *mark as estimated* —
exactly what this guide's own twin does, item by item, in
[`examples/baron_58.sources.md`](../../examples/baron_58.sources.md). For a
new design, the same list is your concept data package.

The aerodynamic coefficients deserve their own word on sourcing — measured
data, handbook method, or defensible estimate — and get it in
[Aerodynamic Data](03_aero_coefficients.md).

## Units

Collect the numbers in whatever system your sources use; the tool converts at
the point of entry. The one habit to fix now: airspeeds are **knots EAS** and
altitudes **feet** in both display systems. See
[Conventions](03_conventions.md) before entering data.
