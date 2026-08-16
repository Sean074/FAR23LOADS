# User GUI review

## Sidebar - 

Should only have the page layout selection and about. All page specific user input should be in the page.

Remove: 
1) Units - move to Start / Project dash board
2) Project file - move to Start / Project dash board

## Start

### Project Dash Board

THe top to bottom page layout

EXISTING Summary of sloads - Current text is good.
ADD Load project files.  Load existing example, user selected load, new file
EXISTING Project name Engineer and Date - Good.
ADD Units selection
EXISTING Description Filed - Good
Work flow progress
REMOVE slices/produced, steps blocked, Schema version
REARRANGE into rows
    Input Data: Geometry, Weight and Mass Props, Aero Data, Structural Speed, V-n Diagram
    Flight Loads: Wing, Fuselage, Tail (Vertical), Tail (Horizontal), Balaance Cases
    Other: Aileron, Flaps, Tab, Engine Mount, Engine Out
    Ground: Landing, Ground Handling
    Plotting: Load Plots
    Export: Comparison, Report, Export

## 1 - Develop V-n diagram **RENAME** Input

the aim is to have all the airplane specific input defined here.  I.e. all geometry, Weights, engine power.  ANy analysis specif assumptions shall be on the page for that analysis (i.e. engine stoppage time, control sufface deflection limits)

### Geometry

All the geometry data is entered in this section. Including the Loads Reference Axis (LRA) definition. Geometry parameters should be user entered adn then related derived geometry that is used in analysis calculated.  Example, wing leading and trailing edge is defined, wing area is calculated. CHECK parameters are not defined multiple time, there should be one location for all definitions.

This page shall have sub pages.
1) main page
    * Assessment (Wing planform parameters, Vertical tail parameters, Horizontal tail parameters, longitudinal stability and landing gear geometry)
    * 3 view plot of the vehicle lift surface geometry, fuselage outline, LRAs, landing gear location both fully extended and compressed. 
2) Wing and Aileron And Flap
    * Symmetric flag
    * Leading edge definition (in wing reference plan)
    * Trailing Edge Definition (in wing reference plan)
    * twist definition root to tip
    * Dihedral of wing reference plane
    * LRA definition (% chord or two gird points in the wing reference plane)
3) Vertical Stabilizer And Rudder
    * V-tail span
    * V-tail tip chord
    * V-tail root chord
    * V-tail z root location (were the vtail intersect the fuselage)
    * V-tail x root location (where the LE of the V-tail is)
    * V-tail sweep
    * V-tail LRA (default 25% chord)
    * Rudder % chord at tip and % v-tail span (default 1.0)
    * Rudder % chord at root and % v-tail span (default 0.0)
    * Rudder hinge location (assume 90% rudder chord)
    * Rudder deflection range
    * MOVE Large deflection factor EFV (ADD explanation) to the tail loads analysis page.
    * MOVE yaw inertia, gross weight to mass properties
4) Horizontal Stabilizer and Elevator
    * ADD type, T tail, conventional
    * 
5) Engine
6) Landing Gear
7) Fuel volume

2) Wing and 

