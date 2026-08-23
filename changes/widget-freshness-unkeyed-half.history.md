- **The unkeyed half of `app/views/` (#51 reopen, tier M, 2026-08-22)** — the
  keyed half of the L-8d data-loss class shipped 2026-08-21 believing the
  guard's own exemption: "no `key=` at all is Streamlit's positional identity,
  per-render". It is not. An unkeyed widget's identity derives from its
  *arguments*, `value=` included, so its retained state is exactly as stable
  across a project load as a hand-written key whenever the loaded field
  repeats the seed — and the seed is `Project(name="")`, so most loaded fields
  do. Ninety-eight of the 187 project-seeded widgets in `app/views/` were
  riding that exemption. The fix is the same stamp the keyed half got, applied
  where there was no key to stamp; the guard inverts to fail closed, gains the
  input calls the first cut missed, and trades the sidebar's whole-file
  exemption for a per-key allowlist with a companion that fails when an entry
  stops naming anything — the same lesson #43 taught about guards that had
  rotted into always-passing, applied before this one could. A type-then-load
  reproduction pins the behaviour the AST walk can only infer.
