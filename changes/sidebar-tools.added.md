- **A Tools section in the sidebar of both GUIs** (#80, C210 build review
  2026-08-23, tier M). Two conversions the C210 build did by hand at the
  envelope and speeds pages: an **airspeed converter** — a speed in any of
  KCAS/KEAS/KTAS plus a pressure altitude, all three out, ISA-only and subsonic
  — and a **% MAC ↔ fuselage station** converter, in both directions. The
  arithmetic is the existing `sloads` owners' (`convert_airspeed` /
  `eas_from_airspeed`; `mac_reference` and the two %MAC functions), so a Tool
  cannot answer a question differently from a page. It lives in the shared
  `app_shell` sidebar, one implementation for both front-ends, and is
  display-only: it reads the project and writes nothing back — the ground of
  the owner's refinement to the oracle GUI's capability cap, which governs
  analysis and data capability, not inert display utilities.
- **KCAS in, not only KEAS out** (#80, tier S). `convert_airspeed` converted
  *from* equivalent airspeed only, so a converter that took KEAS alone would
  have left the conversion actually wanted — a POH or placard speed, which is
  calibrated airspeed — still to be done by hand. `eas_from_airspeed` inverts
  the same relation in closed form, exactly: the round trip is pinned to 1e-9
  at five altitudes for all three measures.
- **The %MAC tool says which wing it measured from** (#80, C210-13). WTENV
  falls back to the wing planform when the weight envelope's XLEMAC/MAC pair is
  left blank, and nothing on that page says so. A tool that quietly answered
  with the fallback would have carried the same silence into the sidebar, so it
  names the reference and prints the XLEMAC and MAC it used.
