# Oracle GUI User Guide

A page-by-page, illustrated guide to the **oracle GUI** — the front-end that
replicates the original FAR 23 LOADS suite's input set. It is written for an
engineer who knows aircraft structures but has never seen this tool: for each
page it explains *what is being asked for, why the original program needs it,
where the number comes from, and what the page gives back.*

## What the oracle GUI is

The original suite (Hal C. McMaster, Aero Science Software; FAA report
DOT/FAA/AR-96/46) computed the structural design loads of a FAR Part 23
airplane as a chain of standalone programs, each prompting for its inputs at
the keyboard. The oracle GUI is that chain as a single application: one page
per analysis step, in the order the data flows, over one saved project file.
It asks for **the original programs' inputs and nothing more** — every field
traces to a named `.BAS` program or to the small set of values the input model
cannot do without.

Launch it and work top to bottom: [Getting started](01_getting_started.md).

## What it is not

It is not the full `sloads` application. Plots, the sbeam export decks, the
workbook, the report and concept mode all live in the main GUI
(`streamlit run app/Home.py`), documented in the task-oriented
[GUI user guide](../10_standard/GUI_USER_GUIDE.md). A project saved by either
front-end opens in the other unchanged — the oracle GUI asks for less, it does
not store anything different. When you outgrow it, see
[Where next](D_where_next.md).

It is also not a theory manual. Every statement of method here links the
[theory sources](../20_theory/00_theory_sources.md) rather than re-deriving
them, and the sign/axis/unit rules have one owner:
[`CONVENTIONS.md`](../10_standard/CONVENTIONS.md), summarised for readers in
[Conventions](03_conventions.md).

## The chapters

The chapter set and its order are the workflow's own, generated — never
hand-maintained: **[the chapter list](_generated/chapters.md)**. Each chapter
covers one page and is the same eight sections, in the same order:

1. **What this page is for** — plain English, naming the original program(s).
2. **Before this page** — what upstream pages must have run, and what you see
   if they have not.
3. **The inputs** — the generated field table, then the meaning of each input
   group and where an engineer gets the number.
4. **Screenshots** — the page as you will see it, with an example loaded.
5. **Worked example — single** — the values typed on this page for
   `ga6_normal`, and why.
6. **Worked example — twin** — the same for `baron_58`.
7. **Results on this page** — the blocks the page renders, whether they are
   LIMIT or ULTIMATE, and how to sanity-check them.
8. **Common mistakes** — the two or three ways the page is got wrong.

Skim a chapter's first two sections to orient; return to sections 3–8 while
entering your own airplane.

## The two worked examples

Every chapter carries the same two airplanes all the way through, so you can
follow either from a blank project to a full set of loads:

- **`ga6_normal`** — the 6-place GA single from the manual's own Appendix A,
  worked in **Imperial** units. It is the suite's printed oracle case: the
  numbers on your screen should reproduce the book's, and
  [Appendix A](A_worked_single.md) runs it end to end against those figures.
- **`baron_58`** — a Beech Baron 58 light twin (two Continental IO-550-C),
  built from its FAA type-certificate data sheet and worked in **SI** units.
  The twin is what makes the engine-mount and One Engine Out chapters real,
  and running it entirely in SI is what teaches the unit boundary.
  [Appendix B](B_worked_twin.md) runs it end to end; its data sources — and
  which values are estimates rather than certified figures — are registered in
  [`examples/baron_58.sources.md`](../../examples/baron_58.sources.md).

Both ship with the tool: load them from the sidebar's **New from example**.

## The rest of the guide

- [Getting started](01_getting_started.md) — install, launch, and the sidebar.
- [Before you start](02_before_you_start.md) — the data to collect first.
- [Conventions](03_conventions.md) — axes, stations, units, and the one
  LIMIT-vs-ULTIMATE statement.
- [Appendix C — Troubleshooting](C_troubleshooting.md) — what the tool's
  messages mean.
- [Appendix D — Where next](D_where_next.md) — the full application.
