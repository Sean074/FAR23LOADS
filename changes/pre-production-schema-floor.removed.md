- **Pre-production schema floor: a project file is read at the current version, or refused (#93, tier L, 2026-08-25).**
  The twelve migration hops (v18→v55) and the v0 bare-`EngineInput` branch are gone, and
  `SUPPORTED_FLOOR` is now `SCHEMA_VERSION`. `migrations.migrate` raises the new
  `SchemaVersionError` — a `ValueError`, so it lands in the documented error contract — for a
  file that is older, newer or unversioned, naming both versions. The gate is raised once,
  inside `io.project_from_dict`, so CLI and both GUIs refuse identically; `io.schema_status`
  and the shell's `apply_schema_check` notice path went with it. This project is
  pre-production: no analysis made with an earlier build has to stay readable, and refusing is
  more honest than reshaping someone else's schema into this build's answer.
  The hop machinery is kept, empty — at production the floor drops and hops register from the
  then-current version forward, unchanged in shape.
