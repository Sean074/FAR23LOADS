# User GUI review

**Status (2026-08-16):** in progress — Sidebar, Start and Input (Geometry) swept;
Flight loads, Other loads, Ground, Plotting and Export still to write. Nothing here
is promoted yet: the GUI freeze
([`2026-08-16_scope_and_deficiency_review.md`](2026-08-16_scope_and_deficiency_review.md) §Streamlit UI)
holds through the 0.6.0 cut, and the new stored fields below land as **one 0.7.0
input-model step** after the schema freeze ends.

**Keys.** Every actionable row carries a section-scoped key `GR-<SECTION>-<n>`
(`SIDE`, `START`, `INPUT`, `GEOM`, `WING`, `VTAIL`, `HTAIL`, `ENG`, `GEAR`, `FUEL`,
`PAY`). Keys are stable citations for issues and PRs; they are not a priority order.

**Classes.**

| Class | Meaning | Closure tier |
|---|---|---|
| **[P]** | Placement / display only — no stored field, no calc change | S |
| **[I]** | Input model — a new, moved or re-owned stored field; schema consequence | L (one hop, 0.7.0) |
| **[D]** | Decision of record — resolved in a design note, merged at AGREED **before** code | note first |

Rows marked *(guard)* are satisfied by a drift-guard test rather than by a page
change, and can be written while the GUI freeze is in force.

---

## Sidebar -

**GR-SIDE-1** [P] Should only have the page layout selection and about. All page specific user input should be in the page.

Remove:
1) **GR-SIDE-2** [P] Units - move to Start / Project dash board
2) **GR-SIDE-3** [P] Project file - move to Start / Project dash board

## Start

### Project Dash Board

THe top to bottom page layout

**GR-START-1** [P] EXISTING Summary of sloads - Current text is good.
**GR-START-2** [P] ADD Load project files.  Load existing example, user selected load, new file
**GR-START-3** [P] EXISTING Project name Engineer and Date - Good.
**GR-START-4** [P] ADD Units selection
**GR-START-5** [P] EXISTING Description Filed - Good
**GR-START-6** [P] Work flow progress
**GR-START-7** [P] REMOVE slices/produced, steps blocked, Schema version
**GR-START-8** [P] REARRANGE into rows
    Input Data: Geometry, Weight and Mass Props, Aero Data, Structural Speed, V-n Diagram
    Flight Loads: Wing, Fuselage, Tail (Vertical), Tail (Horizontal), Balaance Cases
    Other: Aileron, Flaps, Tab, Engine Mount, Engine Out
    Ground: Landing, Ground Handling
    Plotting: Load Plots
    Export: Comparison, Report, Export

## 1 - Develop V-n diagram **RENAME** Input

**GR-INPUT-1** [P] **RENAME** the step from "Develop V-n diagram" to "Input".

**GR-INPUT-2** [I] the aim is to have all the airplane specific input defined here.  I.e. all geometry, Weights, engine power.  ANy analysis specif assumptions shall be on the page for that analysis (i.e. engine stoppage time, control sufface deflection limits)

### Geometry

**GR-GEOM-1** [I] All the geometry data is entered in this section. Including the Loads Reference Axis (LRA) definition. Geometry parameters should be user entered adn then related derived geometry that is used in analysis calculated.  Example, wing leading and trailing edge is defined, wing area is calculated.

**GR-GEOM-2** [I] *(guard)* CHECK parameters are not defined multiple time, there should be one location for all definitions.

**GR-GEOM-3** [D] **DISCUSSION** Which geometry parameters should be user input and which should be calculated. The ORACLE named parameters should be preferred as user input.

**GR-GEOM-4** [D] *(guard)* **DISCUSSION** Are ALL user defined parameters recorded in the project.JSON?

**GR-GEOM-5** [D] **DISCUSSION** Is it required that the user "seed down stream pages"? Is this needed? Is the geometry only needed if the user wishes ot use the estimated component weight?

**GR-GEOM-6** [P] This page shall have sub pages.
1) main page
    * **GR-GEOM-7** [P] Assessment (Wing planform parameters, Vertical tail parameters, Horizontal tail parameters, longitudinal stability and landing gear geometry)
    * **GR-GEOM-8** [P] 3 view plot of the vehicle lift surface geometry, fuselage outline, LRAs, landing gear location both fully extended and compressed.
2) Wing and Aileron And Flap
    * **GR-WING-1** [I] Symmetric flag
    * **GR-WING-2** [I] Leading edge definition (in wing reference plan)
    * **GR-WING-3** [I] Trailing Edge Definition (in wing reference plan)
    * **GR-WING-4** [I] twist definition root to tip
    * **GR-WING-5** [I] Dihedral of wing reference plane
    * **GR-WING-6** [I] LRA definition (% chord or two gird points in the wing reference plane)
3) Vertical Stabilizer And Rudder
    * **GR-VTAIL-1** [I] V-tail span
    * **GR-VTAIL-2** [I] V-tail tip chord
    * **GR-VTAIL-3** [I] V-tail root chord
    * **GR-VTAIL-4** [I] V-tail z root location (were the vtail intersect the fuselage)
    * **GR-VTAIL-5** [I] V-tail x root location (where the LE of the V-tail is)
    * **GR-VTAIL-6** [I] V-tail sweep
    * **GR-VTAIL-7** [I] V-tail LRA (default 25% chord)
    * **GR-VTAIL-8** [I] Rudder % chord at tip and % v-tail span (default 1.0)
    * **GR-VTAIL-9** [I] Rudder % chord at root and % v-tail span (default 0.0)
    * **GR-VTAIL-10** [I] Rudder hinge location (assume 90% rudder chord)
    * **GR-VTAIL-11** [I] Rudder deflection range
    * **GR-VTAIL-12** [P] MOVE Large deflection factor EFV (ADD explanation) to the tail loads analysis page.
    * **GR-VTAIL-13** [P] MOVE yaw inertia, gross weight to mass properties
    * **GR-VTAIL-14** [D] DISCUSSION Airplane Length LF, is this parameter pure geometric 25% WING MAC to 25% V-tail MAC, or the distance from the CG to the V-tail 25% MAC? If geometric defined/calculated here, else it should be calculated in the v-tail analysis for each weight and cg.
4) Horizontal Stabilizer and Elevator
    * **GR-HTAIL-1** [I] ADD type: T tail, conventional
    * **GR-HTAIL-2** [I] H-tail semi-span (tip to centerline)
    * **GR-HTAIL-3** [I] H-tail tip chord
    * **GR-HTAIL-4** [I] H-tail root chord (at centerline)
    * **GR-HTAIL-5** [I] H-tail z root location (were the h-tail intersect the fuselage conventional or v-tail for T tail)
    * **GR-HTAIL-6** [I] H-tail x root location (where the LE of the h-tail is at the centerline)
    * **GR-HTAIL-7** [I] H-tail sweep
    * **GR-HTAIL-8** [I] H-tail dihedral
    * **GR-HTAIL-9** [I] H-tail LRA (default 25% chord)
    * **GR-HTAIL-10** [I] H-tail incidence angle (assume fixed stab, may need to make this variable later or perform analysis at different setting angles, thus later development may require, max up and max down)
    * **GR-HTAIL-11** [I] Elevator % chord at tip and % v-tail span (default 1.0)
    * **GR-HTAIL-12** [I] Elevator % chord at root and % v-tail span (default 0.0)
    * **GR-HTAIL-13** [I] Elevator hinge location (assume 90% rudder chord)
    * **GR-HTAIL-14** [I] Elevator deflection range (trailing edge up and trailing edge down limits)
    * **GR-HTAIL-15** [P] MOVE Elevator effectiveness (ADD explanation) to the tail loads analysis page.
    * **GR-HTAIL-16** [P] MOVE Wing aero data (wing zer-life cruise, Wing zero-lift, Wing zero-lift, landing, wing lift slope AW)
    * **GR-HTAIL-17** [D] DISCUSSION Airplane Length LF, is this parameter pure geometric 25% WING MAC to 25% H-tail MAC, or the distance from the CG to the H-tail 25% MAC? If geometric defined/calculated here, else it should be calculated in the h-tail analysis for each weight and cg.
5) Engine
    * **GR-ENG-1** [I] Number of
    * **GR-ENG-2** [I] Location of prop (x, y, z)
    * **GR-ENG-3** [I] Thrust line (tow, pitch)
    * **GR-ENG-4** [I] propeller diameter
6) Landing Gear
    * **GR-GEAR-1** [D] assume tricycle gear.
    * **GR-GEAR-2** [I] Nose gear axle location compressed: x, y, z (y assumed 0)
    * **GR-GEAR-3** [D] Nose gear axle location static: x, y, z. **DISCUSSION** is this calculated or user provided? Is it calculated for each weight and cg?
    * **GR-GEAR-4** [I] Nose gear axle location extended: x, y, z
    * **GR-GEAR-5** [I] Main gear axle location compressed: x, y, z
    * **GR-GEAR-6** [D] Main gear axle location static: x, y, z. **DISCUSSION** is this calculated or user provided? Is it calculated for each weight and cg?
    * **GR-GEAR-7** [I] Main gear axle location extended: x, y, z
    * **GR-GEAR-8** [I] Nose gear strut type
    * **GR-GEAR-9** [I] Main gear strut type
    * **GR-GEAR-10** [I] Nose gear rolling radius
    * **GR-GEAR-11** [I] Main gear rolling radius
    * **GR-GEAR-12** [I] Wheels per node gear
    * **GR-GEAR-13** [I] Wheels per main gear
    * MOVE to geometry main page assessment:
        * **GR-GEAR-14** [P] tread between mains calculated
        * **GR-GEAR-15** [P] track calculated
        * **GR-GEAR-16** [D] MOVE tip back angle calculated fully compressed and extended, to weight and cg page.  Need to be performed at a given weight and cg.
        * **GR-GEAR-17** [D] MOVE turn over angle static, to weight and cg page.  Need to be performed at a given weight and cg.
7) Fuel volume
    * **GR-FUEL-1** [I] Number of tanks
    * **GR-FUEL-2** [I] For each tank: the four corners
    * **GR-FUEL-3** [I] For each tank: trapped fuel
    * **GR-FUEL-4** [I] For each tank: full fuel
8) Payload
    * **GR-PAY-1** [I] crew (part of OEW)
    * passengers
        * **GR-PAY-2** [I] number
        * **GR-PAY-3** [I] fuse station range for passengers
    * cargo
        * **GR-PAY-4** [I] number of cargo areas
        * **GR-PAY-5** [I] for each the fuse range for each cargo area
