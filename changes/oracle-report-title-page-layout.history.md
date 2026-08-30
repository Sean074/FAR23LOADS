- **The title page reduced to identity and signatures; front-matter defects
  fixed (`ORACLE_REPORT.md` §3–§5, tier M, 2026-08-30)** — Reading the compiled PDF, rather than the renderer's output, is what produced
this change — the third time in this milestone that a green suite and a correct
model still put something wrong on the page.

The cover was carrying identity, document control, the analysis basis, the input
fingerprint, a thirteen-item list of sections the generator cannot yet build,
the signatures and the distribution statement. It ran to two sheets and broke
where it hurts: the signature block landed alone on sheet two, so the approval
record sat on a page carrying no report number, no revision and no title. The
anchors and the not-carried list moved to the end of the introduction, which is
where a reader meets them before any analysis; the cover keeps what identifies
the document and who signed it. `ORACLE_REPORT.md` §3, §4 and §5 previously
required the gap list *on the title page* and are amended, and the guard is on
the cover rather than on the introduction because the failure mode is additive —
a block added back renders perfectly and only the layout suffers.

Three defects came out of the same two pages. The footer printed the
classification marking through the load-basis sentence: `fancyhdr` places `[L]`,
`[C]` and `[R]` independently and nothing stops them colliding, so the two
statements a reader most needs to trust were illegible whenever the marking was
a real phrase. It is now one full-width `tabular*` whose columns share the line
by construction rather than by fitting. The gap sentences were written to follow
a colon and are printed after a bold lead and a full stop, so every placeholder
read "**Not yet implemented.** this revision…". And the introduction still told
the reader that sections not carried were "listed on the title page" after they
had moved — a cross-reference that a reader follows and finds nothing at, now
checked against the location it names.

Checking the remaining pages found the document breaking its own rule in the
front matter. The List of Figures and List of Tables rendered as headings with
nothing beneath them — an absence stated by omission, which is precisely what
every placeholder section exists to avoid, and which a reader is more likely to
read as a generator failure than as "there are none". Both now carry a sentence,
and both are added to the Contents, since the abstract already was and two kinds
of front matter treated differently in one document reads as an oversight. The
emptiness test recurses into subsections: a table one level down still puts a
line in the list, and the document would otherwise state the opposite of what
the reader is looking at.

That fix cost a page — the List of Tables landed alone on a sheet — which
exposed the cause as `\parskip`. The document sets it to 0.6 em and a contents
list inherits it, so seventeen entries spaced like paragraphs filled the page by
themselves. Confined to a group around the front matter, which leaves the body's
paragraph spacing alone and puts all three lists back on one page.

