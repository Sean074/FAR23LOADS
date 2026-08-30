- **Report dates are pickers, and an unsigned row prints no date.** The report
  page's issue date and three signature dates are date pickers storing ISO
  `YYYY-MM-DD`, so one title block cannot carry `30/8/26` and `Aug 30 2026` at
  once. The pickers open **empty** rather than at today — a date on a formal
  report is a claim about an event, and a control that defaults to the current
  date makes that claim on the author's behalf. A stored value that is not a
  date is preserved and reported rather than silently replaced, since the spec
  is a file a person is meant to be able to edit. In the document, a signature
  row with no name no longer prints its date: a date beside a ruled name blank
  reads as an approval that happened and was signed illegibly.
