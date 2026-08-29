- **The delivered landing load is a body-frame force with a stated point, for every gear on every case (design note 38 GF-6/GF-7, issue #134, tier L, 2026-08-29).**
  LANDLOAD prints its whole reaction matrix twice — "VALUES ARE WITH RESPECT TO
  GROUND LINE -- DENOTED BY P (PRIME)" and "VALUES ARE WITH RESPECT TO AIRPLANE
  DATUM" — and the replication shipped the first set only: no application point,
  no attitude, no frame label, while the export deck consumed the other frame. A
  stress model consumes a force **and a point**; a magnitude in an unnamed frame
  is not a load.

  Every case now emits **three wheels — nose, left main, right main, all three
  always, an unloaded gear at zero rather than omitted** — each with the
  airplane-datum `Fx, Fy, Fz`, the **location `x, y, z`** it acts at, and the
  gear reference node it is delivered to, with the strut state and Appendix A's
  own point-of-load column named in the condition note (axle on cases 1–12 and
  25/26/28/29/31/32, ground contact on 13–24 and 27/30/33 — design note 39). It
  is built *from* `gear_loads.applied_wheels`, so the statement a stress model
  reads and the load the deck applies cannot come to differ.

  Also emitted, all new: p231's **fuselage-axis angle** per case (`deg`, an
  attitude and never a load), p232's **airplane-datum load factors NR/NV/ND**,
  and p233's **airplane-datum unbalanced moments**. Both GUIs gain the datum
  table beside the primed one.

- **Both frames are named on the value, and the delivered CSV carries only one of them (GF-6/GF-7, tier L, 2026-08-29).**
  New `sloads/frames.py` owns the frame vocabulary, the manual's own caption
  words, the report-vs-deliver rule and the rotation between the frames.
  `LoadValue` gains `frame` (schema **v57 → v58**, identity hop): the render
  boundary reads it to keep the delivered CSV in the airplane datum while the
  text report keeps both sets — drift-guarded both ways, so neither can leak
  into the other. Both GUIs caption their reactions tables from the one function
  that has the words, guarded against either spelling them out again.

- **72 more Appendix A cells locked (2026-08-29).** p232's NR/NV/ND columns join
  the page locks, transcribed at 200 dpi; the tail-down family reproduces all
  three printed cells exactly.
