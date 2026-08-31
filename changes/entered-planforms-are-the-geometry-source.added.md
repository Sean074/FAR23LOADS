- **The GA6 example carries its printed Appendix A empennage (tier L, 2026-08-30).**
  `examples/ga6_normal.project.json` gains horizontal tail, vertical tail, elevator, rudder
  and flap entries in `geometry.surfaces`, transcribed from the coordinate tables Appendix A
  prints for each (p145 flap, p149 rudder, p151 h-tail, p153 elevator, p157 tab). The
  fixture had kept those WINGGEOM runs' **outputs** as scalars and dropped their **inputs**.
  Every entered polyline reproduces its own printed AREA/SIDE, MAC, YLE(MAC), XLE(MAC) and
  aspect ratio to within **0.084 %**. The GA6 tail therefore stops being an assumed
  rectangle: its spanwise strip distribution, its deck and its LRA beam model now describe
  the surface the manual drew.
