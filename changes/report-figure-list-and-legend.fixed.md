- **Report renderer: table splitting, figure lists and marker legends (tier S, 2026-08-30).**
  Three defects found by reading compiled PDFs during the oracle-report GUI review, all in
  the renderer shared with the summary report.
  A table short enough to fit a page is now set as one unbreakable `[H]` float instead of a
  `longtable`: `longtable` split the Baron's five-row Mach table between its last row and
  `\endlastfoot` and printed the repeated header and bottom rule alone at the top of the
  next page, under no data — a break no inter-row penalty prevents, because the foot is not
  a row. Tables past `latex.UNBREAKABLE_ROWS` still use `longtable`, because a hundred-row
  case index has to break somewhere.
  `figure_tex` emits `\caption[<title>]{<title>: <caption>}`, so the List of Figures carries
  titles rather than four near-identical explanatory paragraphs.
  The marker-series legend moved from a hard-coded "Design CG cases" in the emitter to
  `PlotData.points_label`, which had the oracle report's gust design points inheriting a
  legend naming a different figure.
