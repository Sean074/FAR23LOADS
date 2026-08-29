# Appendix C — Troubleshooting

The tool prefers a stated refusal to a wrong number, so most of what looks
like a fault is a message with a specific meaning. This appendix decodes
them.

## "needs `x` — run the pages before this one first"

The page's results block, in place of results. The step you are on consumes a
quantity an **earlier page produces**, and that page has not produced it yet.
The backticked name is the missing data slice; the remedy is never on the
current page — go up the page list, complete the named prerequisite, and
return. The chapter's *Before this page* section lists exactly which pages
those are.

## "needs `x` — entered on this very page: fill in the form above"

The sibling message: the missing data is this page's **own form**, not an
upstream one. You are part-way through the page's inputs — typically a
required group or table still empty. Nothing upstream will help; finish the
form.

## "cannot run yet — `<Error>`: …"

The page's inputs are present but one of them cannot be computed with: the
program refused, by name, rather than guessing. The message text states the
specific input and what is wrong with it (a planform that doesn't close, a
zero that must be positive, a name that matches no surface). Fix the named
input; these are entry errors, not tool faults.

## A page that withholds its form entirely

Some conditions do not exist for some airplanes, and the page says so instead
of taking inputs it would refuse. The one you will meet first: **One Engine
Out on a single-engine airplane** — with one centreline engine there is no
asymmetric-thrust condition to analyse, so the page states that and renders
no form. This is not a gap in your data; it is the applicability rule.

## "produced no conditions"

The program ran and had nothing to report for this airplane — an empty result,
stated rather than hidden. Check the chapter's *Results* section for what the
page normally emits and which inputs give it something to select from.

## "re-run SELECT" on the Tail Loads page

The tail-distribution page prints, ahead of each condition, the aerodynamic
state that produced it (angle of attack, deflection, dynamic pressure). A
project saved by an **older version** of the tool carries the selected
conditions without those recorded states, and the page says *re-run SELECT*
rather than guessing them: revisit the
[Flight Envelope](05_flight_envelope.md) page so the selection is recomputed
and the states recorded. Your loads are unchanged; only the recorded state
was missing.

## Grid-entry surprises

The entry habits from [Getting started](01_getting_started.md), because they
generate most first-session confusion:

- **A value you typed vanished** — you pressed Enter. Enter leaves the cell's
  editor open and the next keystroke discards what you typed. Commit grid
  cells with **Tab**.
- **A row you added is gone after a reload** — it had an empty cell. Grid
  rows with any empty cell are not saved; fill every column to keep the row.
- **A blank row appeared and the page complains** — a **row counter** adds
  the row to the project the moment it appears, blank or not. Fill it in, or
  count back down to delete it.
- **The fields I need are not on the page** — an optional section is off the
  page until you add it: look for the caption naming the missing fields and
  the **➕ Add** button above it. Sections your airplane does not have stay
  absent, which is how the programs know not to ask for them.
- **A section I do not want is on the page** — open the **🗑 Remove** control
  at the foot of that block. It names what it removes and takes everything
  entered in it; the section can be added again, blank.

## Unit-toggle surprises

- **A number didn't change when you toggled** — airspeeds (KEAS) and
  altitudes (ft) are deliberately the same in both systems.
- **You entered SI but the file "looks Imperial"** — the stored project is
  always canonical Imperial; the toggle is a display boundary. Reopen the
  file in either system and it is the same airplane. Nothing you typed was
  lost in a conversion round-trip.
- **A value re-displays slightly differently than typed** — round-trip
  display rounding in the converted system; the stored value is what your
  entry converted to, once.

## The dirty flag

🟠 *Unsaved changes* means the session differs from the last loaded or saved
state — it is a **diff, not an edit counter**, so undoing a change by hand
returns the flag to ⚪. Opening another project over a dirty session asks
first; **Save to disk** writes to the fixed `projects/` folder named in the
caption, and **Download** is the browser-side copy of the same file. If a
save seems to have gone nowhere, check the caption's stated path — that is
where it went.
