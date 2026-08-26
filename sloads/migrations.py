"""Schema gate: a ``project.json`` is read at the current version, or not at all.

**The rule (#93, 2026-08-25).** This project is pre-production. No analysis
performed with an earlier build has to stay readable, so a file is accepted only
when its ``schema_version`` *is* :data:`~sloads.models.SCHEMA_VERSION`; anything
older, newer or unversioned raises :class:`SchemaVersionError` naming both
versions. Refusing is the honest answer — an old file's numbers were produced by
a different tool, and silently reshaping them into the current schema presents
them as this build's.

The gate lives here rather than in a front-end because
:func:`sloads.io.project_from_dict` funnels every load — CLI, both GUIs, every
test — through :func:`migrate`. One owner, one refusal, no GUI deciding
compatibility for itself. The standing guard is
``tests/test_app_shell.py::test_no_gui_decides_whether_a_file_is_readable``.

**The machinery is kept, empty.** :data:`MIGRATIONS` is a ``{from_version: hop}``
chain applied in ascending order, each hop turning a file of version *n* into
*n+1* shape:

    v_file --hop--> v_file+1 --hop--> ... --> SCHEMA_VERSION --> one tolerant reader

Today it is empty and :data:`SUPPORTED_FLOOR` equals ``SCHEMA_VERSION``, so no
hop runs. At production the floor drops to whatever version ships and hops
register from there forward — the shape of that work is unchanged, which is why
the chain stays rather than being deleted and rebuilt from history.

**The twelve retired hops** (v18–v54, plus the v0 bare-``EngineInput`` branch
from the Phase-0 ``engloads`` era) covered every shape change from v18 to v55.
They are recorded, with the archaeology table that reconstructed which schema
version each legacy path belonged to, in
``docs/40_history/11_completed_development_to_0.5.0.md`` (M4-10) and in this
file's own git history. The six bundled examples were re-stamped through that
chain at the cut, verified output-neutral: the ``Project`` loaded from each old
file and from its re-stamped replacement are identical dicts, and
``tests/fixtures_imperial/digests.json`` did not move.

The examples are now the floor's only customers, so
``tests/test_schema_guards.py::test_every_bundled_example_is_written_at_the_current_version``
turns the next ``SCHEMA_VERSION`` bump into a red suite until they are re-stamped.

Pure: dicts in, dicts out, no I/O.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Mapping

from .models import SCHEMA_VERSION


class SchemaVersionError(ValueError):
    """A project file is not at the version this build reads.

    A ``ValueError``, so it lands in the documented error contract
    (``00_program_overview.md``) and every front-end's existing load handling
    reports it without a new branch.
    """


#: ``{from_version: hop}`` -- applied in ascending order, each turning a file of
#: version *n* into version *n+1* shape. Empty while the floor sits at the
#: current version (#93); a version that changes shape after production adds its
#: hop here and lowers :data:`SUPPORTED_FLOOR`.
MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

#: The oldest project version this build reads. Pre-production this **is**
#: ``SCHEMA_VERSION``: there is nothing older worth reading, and saying so is
#: what lets the readers describe exactly one schema.
SUPPORTED_FLOOR = SCHEMA_VERSION


def source_schema_version(d: Mapping[str, Any]) -> int:
    """The ``schema_version`` a project dict carries, or ``-1`` if it carries none.

    ``-1`` rather than a floor default: an unversioned dict is not an old project
    file, it is a dict nobody wrote as one (``project_to_dict`` has stamped the
    version since the versioned era began). The gate must be able to say so.
    """
    version = d.get("schema_version")
    return version if isinstance(version, int) else -1


def migrate(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``d`` at the current schema, or raise :class:`SchemaVersionError`.

    Works on a deep copy -- the caller's dict is never mutated, which matters
    because the GUI hands the same dict to the JSON editor.
    """
    version = source_schema_version(d)
    if version != SCHEMA_VERSION:
        found = "no schema_version" if version < 0 else f"schema {version}"
        raise SchemaVersionError(
            f"This file is not readable by this build: {found}; this build reads "
            f"schema {SCHEMA_VERSION} only. Pre-production, projects are not "
            "migrated -- rebuild the project on the current version."
        )

    out = copy.deepcopy(d)
    for hop_from in sorted(MIGRATIONS):
        if version <= hop_from:
            out = MIGRATIONS[hop_from](out)
    out["schema_version"] = SCHEMA_VERSION
    return out


def applied_hops(from_version: int) -> List[int]:
    """Which hops :func:`migrate` would run for a file of ``from_version``.

    Empty while the chain is (#93). Kept as the chain's own accessor, so the
    tests and a future "this file was migrated from vN" provenance line read the
    answer from one place.
    """
    return [h for h in sorted(MIGRATIONS) if from_version <= h]
