- **Flutter clearance (MFC / V(FC)) is gone from the tool** (C210-19, issue #79, tier M,
  2026-08-26). `MACHLIM.BAS` computes `MFC = 1.2·MD` and a per-altitude
  `V(FC) = MFC·a·√σ`, and this port reproduced both. Flutter substantiation is
  **14 CFR 23.629**, not a design load — nothing in this suite sizes structure to MFC —
  and the symbol makes it worse rather than clearer: a Part 25 reader takes `VFC`/`MFC`
  for **§25.253's** maximum-speed-for-stability pair, a different quantity under a
  different definition. Removed on the owner's directive from the calc
  (`mach_limit.py`), the report's plot series **and its `V(MFC) (KEAS)` workbook
  column**, the Speed–Altitude chart in the main GUI (whose constant-Mach fan reached
  `1.2·MD + 0.05` and now reaches `MD + 0.05`), and the theory document. **MNE = 0.9·MD
  and the V(MC)/V(MNE)/V(MD) lines are untouched and stay oracle-locked.**
- **The dropped Appendix A output is registered as a scope withdrawal, not a
  correction** (#79, tier M, 2026-08-26). Appendix A p160 prints MFC 0.4836 and the
  oracle test asserted it to ±0.1 % until this date; we now decline to compute it, and
  the printed figure stands uncontradicted.
  `docs/20_theory/02_approved_corrections.md` gains a **third category** for that: its
  existing entries say *the manual is wrong and here is the right number*, which is the
  opposite claim. Guarded by
  `tests/test_mach_limit.py::test_no_shipped_module_computes_a_flutter_clearance_speed`,
  an AST scan of every shipped package — because the quantity was computed in **two**
  places, and deleting only the module's would have left the chart still drawing the
  line. **The VF half of #79 closes verified-correct:** every `VF` in code and docs is
  the 23.345 design flap speed, with no flutter conflation anywhere.
