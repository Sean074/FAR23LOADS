- **The report's title page carries identity and signatures only.** The analysis
  basis (project anchors and the input fingerprint) and the list of sections the
  issue does not carry have moved to the end of the introduction. Both are read
  rather than glanced at, and on the cover they pushed the signature block onto
  a second sheet — leaving the approval record on a page carrying none of the
  document's identity. The cover now fits one sheet: marking, title, document
  control, the three signature rows and the distribution statement.
- **Fixed:** the page footer printed the classification marking on top of the
  load-basis sentence. `fancyhdr` places its left, centre and right slots
  independently, so a marking of any real length overprinted its neighbour; the
  footer is now one full-width table whose columns share the line by
  construction. A placeholder's sentence is capitalised after its bold lead, and
  the introduction no longer points at the title page for a list that is not
  there any more.
- **An empty List of Figures or List of Tables now says it is empty**, and both
  appear in the Contents alongside the Abstract. A heading with nothing under it
  is a silent absence — the one thing this document does not do anywhere else —
  and a reader cannot tell "this issue has no figures" from "the list failed to
  generate". The Contents is also no longer spaced like body paragraphs, so the
  front matter fits one page instead of three.

