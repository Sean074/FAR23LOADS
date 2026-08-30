- **Report dates became pickers, and an unsigned row stopped printing one
  (`ORACLE_REPORT.md` §4, tier M, 2026-08-30)** — Asking whether the report's date fields should be pickers turned up a defect in
what was already there. The pickers themselves are straightforward — ISO storage,
one format per document, `sloads.models.report.parse_date` as the only place that
knows the format, since `oracle_app` may not import `datetime` (gate G1). The two
things worth recording are what the obvious implementation would have got wrong.

`st.date_input` defaults its `value` to **today**. Dropped in without thought, it
stamps the current date onto an issue date and three signature dates that nobody
filled in, and the title page then states that the report was issued and signed
today — the same class as the placeholder that printed "Not analysed" over the
generator's own gap, a control putting words in the author's mouth. Every picker
passes `value=` explicitly and an AST guard fails any `date_input` that does not.

The second was already shipped and the picker only made it easy to reach: the
document printed a signature date beside a ruled *name* blank, which reads as an
approval that occurred and was signed illegibly. An unsigned row now prints no
date; the value stays in the spec, because a planned date is legitimate, and it
is the printing of it against an absent name that is refused. The role is still
shown — naming who is due to sign claims nothing about whether they have.
Recorded as three SHALLs in `ORACLE_REPORT.md` §4, which previously said the
opposite by omission, with a **Dates and signatures** row in the section register.
