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

**DISCUSSION** Which geometry parameters should be user input and which should be calculated. The ORACLE named parameters should be preferred as user input. Are ALL user defined parameters recorded in the project.JSON?

**DISCUSSION** Is it required that the user "seed down stream pages"? Is this needed? Is the geometry only needed if the user wishes ot use the estimated component weight?

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
    * DISCUSSION Airplane Length LF, is this parameter pure geometric 25% WING MAC to 25% V-tail MAC, or the distance from the CG to the V-tail 25% MAC? If geometric defined/calculated here, else it should be calculated in the v-tail analysis for each weight and cg. 
4) Horizontal Stabilizer and Elevator
    * ADD type: T tail, conventional
    * H-tail semi-span (tip to centerline)
    * H-tail tip chord
    * H-tail root chord (at centerline)
    * H-tail z root location (were the h-tail intersect the fuselage conventional or v-tail for T tail)
    * H-tail x root location (where the LE of the h-tail is at the centerline)
    * H-tail sweep
    * H-tail dihedral
    * H-tail LRA (default 25% chord)
    * H-tail incidence angle (assume fixed stab, may need to make this variable later or perform analysis at different setting angles, thus later development may require, max up and max down)
    * Elevator % chord at tip and % v-tail span (default 1.0)
    * Elevator % chord at root and % v-tail span (default 0.0)
    * Elevator hinge location (assume 90% rudder chord)
    * Elevator deflection range (trailing edge up and trailing edge down limits)
    * MOVE Elevator effectiveness (ADD explanation) to the tail loads analysis page.
    * MOVE Wing aero data (wing zer-life cruise, Wing zero-lift, Wing zero-lift, landing, wing lift slope AW)
    * DISCUSSION Airplane Length LF, is this parameter pure geometric 25% WING MAC to 25% H-tail MAC, or the distance from the CG to the H-tail 25% MAC? If geometric defined/calculated here, else it should be calculated in the h-tail analysis for each weight and cg. 
5) Engine
    * Number of
    * Location of prop (x, y, z)
    * Thrust line (tow, pitch)
    * propeller diameter
6) Landing Gear
    * assume tricycle gear.
    * Nose gear axle location compressed: x, y, z (y assumed 0)
    * Nose gear axle location static: x, y, z. **DISCUSSION** is this calculated or user provided? Is it calculated for each weight and cg?
    * Nose gear axle location extended: x, y, z
    * Main gear axle location compressed: x, y, z
    * Main gear axle location static: x, y, z. **DISCUSSION** is this calculated or user provided? Is it calculated for each weight and cg?
    * Main gear axle location extended: x, y, z
    * Nose gear strut type
    * Main gear strut type
    * Nose gear rolling radius
    * Main gear rolling radius
    * Wheels per node gear
    * Wheels per main gear
    * MOVE to geometry main page assessment:
        * tread between mains calculated
        * track calculated
        * MOVE tip back angle calculated fully compressed and extended, to weight and cg page.  Need to be performed at a given weight and cg.
        * MOVE turn over angle static, to weight and cg page.  Need to be performed at a given weight and cg.
7) Fuel volume
    * Number of tanks
    * For each tank: the four corners
    * For each tank: trapped fuel
    * For each tank: full fuel
8) Payload
    * crew (part of OEW)
    * passengers
        * number
        * fuse station range for passengers
    * cargo
        * number of cargo areas
        * for each the fuse range for each cargo area

