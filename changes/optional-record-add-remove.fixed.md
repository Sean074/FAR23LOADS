- **An Optional record block in the oracle GUI is created and removed by name,
  never attached by a stray touch (#143, tier M, 2026-08-29).**
  One interaction with any widget in an Optional record's block used to attach
  the whole record: ticking the LANDING coefficient set's flaps-down flag on the
  Aerodynamic Data page attached a zero-coefficient set, `refresh_derived` →
  `AeroCoefficientsInput.normalize()` filled its `stall_cl` from `clmax_flap` so
  it passed the #81 guard, un-checking did not detach it, and the phantom set
  saved into the `.project.json` — taking Flight Envelope and SELECT down with a
  400-iteration solver failure (#144). Every Optional record block now takes the
  list-row posture (#88/#72): its fields are off the page behind an `➕ Add …`
  button, with a caption naming the fields that are missing, and a `🗑 Remove …`
  control behind an expander takes the record away again with everything entered
  in it. Which blocks these are is read from the field registry
  (`oracle_app.form.optional_steps`), so a new Optional slice carries the posture
  the moment the registry classifies it; a plain page visit still attaches
  nothing (OG-F), and a list record keeps its own gesture, the row counter.
