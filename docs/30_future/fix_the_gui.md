# Fix the GUI

the current GUI and project files are hard for the user to get what they want.  The data flow is convoluted and the not all data is stored, so reloading often requires getting the data again.

Some input data also seems to be missing (% chord of elevator).

The below is a proposed structure.  The aim wil be to work the development phase by phase, inline with the FAR23 program standard analysis flow.

Essential a NEW GUI. However we don't want to ":through the baby out with the bath water" thus some of the existing GUI will be portable into the new interface.

The initial development will be to create a project GUI deign adn specification (no code).  This will produce a detailed development plan.

The expected analysis phases are:

1. Develop V-n diagram (load cases)
    a. Weights and CG.  The user can select a path that uses the weight estimator or inputs the know weights directly.
    b. Aerodynamics surface geometry.  All aerodynamic surfaces are defined here (add fuselage definition to support pitching moment).  The output from this should be able to produce a three view drawing of the vehicle. Addition of the landing gear location.
    c. Determines structural speeds.  The program should provide the minimums and the user should be able to edit and define the structural design speeds.
    d. Aerodynamic coefficients. The wing aerodynamics, (fuselage pitching moment) and other aerodynamic data is inputted or calculated to give the required aerodynamic coefficients for the analysis.  These are summarized (plotted), sot he user can compare these with other data.

2. Flight loads. Wing distributed loads. Empennage loads. Fuselage loads.

3. Other loads. Aileron, flap, tab, engine mount, one engine out loads.

4. Landing loads. Loads on the landing gear.  An extension here would be to calculate the distributed fuselage.and wing loads due to the landing cases.

5. Load case plotting. Plots of the distributed loads for wing and fuselage.  Envelope plots of the maximum shear V, Bending Moment / Torsion (Mx, My, Mz).  A future extension would be to load a prior loads analysis to compare.

6. Export of loads.  sbema/NASTRAN bdf data for distributed loads.  Loads tables for other components.

## Details for Develop V-n diagram (loads cases)

This is the primary user input.  It defines the geometry of the airplane, the mass distribution, the aerodynamic data, the operating envelopes for mass and speed/altitude.

At the end of this the loads cases to be assessed are derived to ocver the flight and weight/cg envelopes. Thus cases to be assessed are combination of:
1) Mass cases, weight and cg.
2) Points in the sky (speed/altitude).

Plots that help the user understand the load environment are:

1) 3 view of the vehicle, location of the flying surfaces, control surfaces, gear etc.  Also ensures that the input geometry is correct.
2) mass distribution in the vehicle plotted with the vehicle geometry.
3) Weight and CG gird.  Identify CG cases at the corners or extreme of the CG grid (note that these may be difficult/impossible to practically load but ensure coverage of the defined envelop)
4) Speed altitude chart and identify the spped/altitude conditions ot by assessed.
5) V-n diagrams for a given payload and altitude.

### Weight and Mass Properties.

The results of this should be the weight and mass property data that is used for all follow on programs.  There should be no need to enter weight or mass property data in any later interface.  All weight data is inputted or defined in this part of the GUI.

0) Design weights (not sure where this goes, maybe as part of item 4.) MTOW, MLW, ZFW, OEW, cg limits.
1) WTESTIMA.BAS: This is optional.  It allows the user to get an estimated weight if they do not have more refined data.  this is then used along with the geometry to seed the rest of the weight and mass property data.  NOTE it is optional.
2) Geometry. As the weight database and the aerodynamics need geometry.  The basic geometry of the aircraft needs to be defined.  This is the three view, showing, fuselage, wing empennage, landing gear engine locations and sizing.  Summary of basic geometry is provided, S AR, Span, Taper Ratio, etc for wing horizontal stabilizer, vertical stabilizer.  All geometry should be entered here, including control surface and high lift definitions.
4) Weight database.  This is used for the subsequent programs, it can be estimated by WTESTIMA.BAS (with geometric information) or inputted by the user.  This the user can select to use WTESTIMA.BAS and the geometry to created the mass database.  Distributed mass is also determined for the wing and fuselage. Weight items are identified as empty, payload, etc, inowrder to perform weight built ups.
5) WTENV.BAS calculates the envelope of discretionary useful loading this is the CG grid.  A CG Mass vs MAC is plotted, identifies OEW, MTOW, forward and aft CG limits. Show a loading and fuel vectors.
6) WTONECG.BAS calculates the weight, center of gravity and inertia of the airplane for any specific loading configuration of an airplane. Mass cases used for loads analysis are defined.  Load cases that cover the ch grid are defined, including case for landing (high adn low waterline cg), heavy forward and aft cg, light forward and aft cg etc.  these are shown on the cg gird alone with a table that summarizes these conditions and their mass properties, Mass, cgx/y/z, inertia, definition (MTOW@fwd_cg etc).

### Aerodynamic Surface Geometry.

WINGGEOM.BAS calculates the geometry for all the aerodynamic surfaces on the airplane. These include the wing, aileron, aileron tab, flap, horizontal tail, horizontal stabilizer, elevator, elevator tab, vertical tail, vertical stabilizer, rudder and rudder tab.  Additionally the fuselage is to be added to get a three view and to allow for fuselage pitching moment to be added later.

This is mentioned above.  Need to resolve where this is in the flow.  **Open Decision: Is this before Weight and mass properties?**

(Geometry. As the weight database and the aerodynamics need geometry.  The basic geometry of the aircraft needs to be defined.  This is the three view, showing, fuselage, wing empennage, landing gear engine locations and sizing.  Summary of basic geomdetry is provided, S AR, Span, Taper Ratio, etc for wing horizontal stabilizer, vertical stabilizer.  All gemetry should be entered here, including control surface and high lift definitions.)

Three view plots of hte airplane and summary of the main geomewtric parameters.

### Other input data

There is additional input data for some specific analysis (For example Landing gear: wheel size, brake torque limit etc.  Engine power, RPM, etc) **Open Decision: Is this better here in a input section or with that specific analysis?**

### Determine structural speeds

STRSPEED.BAS calculates the minimum structural design speeds and load factors.  the user can elect to modify these speeds.  

MACHLIM.BAS calculates the mach limitations at altitude for VC and VD when you specify the shoulder altitude.

The results of this is to define the speed altitude envelop and plot it.  This then defines the load conditions to be assessed.  Note a number of designs speeds change with weight (eg. Va).

### Aerodynamic coefficients (Really only wing)

AIRLOADS.BAS calculates the basic and additive spanwise aerodynamic lift coefficient distributions for the wing.  This used a simplifed method. Future development may add additional methods to improve the accuracy. Also a significnat limitation is tha the fuselage pitching moment is not includeed (***NEED TO CHECK***) this has a significant effect on the balance tail load required.

### V-n Diagram

Plot is V-n diagrams.  This along with the mass cases defines all the conditions that need to be assessed by flight loads.

the user will want to plot the V-n diagrams.

The user would like a summary of the weight and cg and speed altitude condition that wil be assessed in the flight loads analysis.

## Flight Loads

FLTLOADS.BAS program computes an the loads for any combination of airspeed and load factor (mass/cg as well?) on and within the boundaries of the flight envelopes.

SELECT.BAS reads the data file for all the balanced symmetrical flight conditions on the V-n diagrams calculated by FLTLOADS.BAS

Out of this we get distributed loads.

Would be good ot get some standard longitudinal stability plots in this section to check trim and balance tail loads.

## Other loads

Control surfaces chordwise distributed load etc.

## Landing Loads

this is needed to get distributed fuselage loads.  How to address this? Do we add the distributed fuselage loads from ground cases here?  Not that for pressurized airplanes we CAN NOT down select ground cases. over flight due to pressurization load needs to be assessed for flight and not for ground/landing. 

## Load Case Plotting

VMT plots for wing and fuselage

## Export

Export of bdf for wing and fuselage.

Would also like to generate a summary report:
1) summary of input data
2) envelope plots, V-n, weight/cg, speed altitude etc
3) Summary of loads analysis conditions and FAR coverage
4) Summary of results.
    1) VMT plots wing
    2) VMT plots fuselage
    3) Summary control surface/flap loads
    4) summary landing gear loads
    5) Summary engine loads