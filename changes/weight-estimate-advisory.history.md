- **The weight estimate says what reads it, and stands beside the weights the project uses (#78, C210-9, tier M, 2026-08-26)** — The Cessna 210 build stopped at the weight-estimation block and asked three questions —
what does this feed, is it either/or with the item table, are the two compared — and the
page answered none of them (C210-9). The answers were "nothing", "no" and "no", but they
were only recoverable by reading the code: `PROGRAM_SPEC` said WTESTIMA *feeds* WTONECG
and WTENV, which is true of the original suite's data flow and false of this
implementation, where the flow runs through a weight data base the user authors and the
estimate reaches it only through a seed button. Fixed at both ends — the module now owns
the sentence (`weight_estimate.ADVISORY`) so both front-ends and the spec say the same
thing, and `compare_with_itemized` puts the estimate beside the weights the project
actually uses, drawing each entered figure from its existing owner rather than re-summing
the item table. The comparison is deliberately unthresholded: a GA correlation and a
weighed airplane are not expected to agree, +22 % on the C210 is scatter rather than
error, and a page that ruled on the gap would be answering a question the finding did not
ask. The other half of #78 — the seed button — turned out to have shipped long before the
review that filed it as missing; what survives there is that its rows arrive silently
zero-stationed and untagged and that it wipes an authored table, which is main-GUI work
behind the `app/views/` freeze.
