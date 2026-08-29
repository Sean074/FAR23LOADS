"""Schema gate: a ``project.json`` is read at the current version, or not at all.

**The rule (#93, 2026-08-25).** This project is pre-production. No analysis
performed with an earlier build has to stay readable, so a file is accepted only
when its ``schema_version`` is :data:`~sloads.models.SCHEMA_VERSION` or a
version the hop chain reaches it from (:data:`SUPPORTED_FLOOR`); anything
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

The chain holds one live hop today — the v55→v56 identity of note 36's additive
fields (OV-10, #97) — so :data:`SUPPORTED_FLOOR` is 55. At production the floor
drops to whatever version ships and hops register from there forward — the
shape of that work is unchanged.

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


def _hop_55(d: Dict[str, Any]) -> Dict[str, Any]:
    """v55 -> v56 (note 36 OV-10, #97): **identity**.

    v56 adds three input fields with backward-benign defaults --
    ``SurfaceInput.tip_cap_width_in`` (0.0 = square tip, the v55 meaning) and
    the ``EngineInput.engine_mass_item``/``prop_mass_item`` selectors ("" = no
    derivation, the v55 behaviour). The readers take the defaults for absent
    keys, so the hop changes nothing; it exists because the gate refuses any
    version it has no hop for, and an additive field is still a shape change.
    """
    return d


def _hop_56(d: Dict[str, Any]) -> Dict[str, Any]:
    """v56 -> v57 (note 37 LF-8, #123): **semantic** -- the landing N inversion.

    ``landing.gear_load_factor`` (an NLG override, ``0.0`` = unset) is replaced
    by ``landing.airplane_load_factor`` (the governing N, ``None`` = unset):
    ``N = NLG_old + L``, the vertical-equilibrium identity at peak load. Not an
    identity hop, deliberately -- the field's role inverts from input to derived,
    and re-pointing an old project at the energy equation instead would move its
    NLG (ga6 p230: 2.5 entered vs 2.4281 energy). The hop reproduces every NLG
    the reaction path read, so no load number moves.
    """
    landing = d.get("landing")
    if isinstance(landing, dict):
        nlg = landing.pop("gear_load_factor", 0.0)
        if nlg:
            landing["airplane_load_factor"] = nlg + landing.get("lift_factor", 0.667)
    return d


def _hop_57(d: Dict[str, Any]) -> Dict[str, Any]:
    """v57 -> v58 (design note 38 GF-6/GF-7, #134): **identity**.

    v58 adds ``LoadValue.frame`` -- the reference frame a value is stated in
    (:mod:`sloads.frames`), which the delivered CSV reads to keep the ground-line
    set out of it. ``""`` (no frame named) is exactly the v57 meaning, and it is
    the default, so a v57 file loads bit-identical. ``LoadValue`` is persisted
    inside ``critical.conditions[].loads``, which is why an added display-neutral
    field is still a shape change and still gets a hop.
    """
    return d


def _hop_58(d: Dict[str, Any]) -> Dict[str, Any]:
    """v58 -> v59 (#141): **identity**.

    v59 adds ``LoadValue.point`` -- the named application point a force is
    delivered to (:data:`sloads.gear_loads.AXLE` /
    :data:`~sloads.gear_loads.GROUND_CONTACT`), which the delivered CSV states
    beside the coordinates so a standalone consumer no longer has to compare
    x/y/z back to the geometry to learn whether a case acts at the axle. ``""``
    (no point named) is exactly the v58 meaning and is the default, so a v58
    file loads bit-identical. This is ``_hop_57`` one step on, for the same
    reason: ``LoadValue`` is persisted inside ``critical.conditions[].loads``,
    so an added display-neutral field is still a shape change and still gets a
    hop.
    """
    return d


#: ``{from_version: hop}`` -- applied in ascending order, each turning a file of
#: version *n* into version *n+1* shape. A version that changes shape adds its
#: hop here; :data:`SUPPORTED_FLOOR` names the oldest version the chain starts
#: from.
MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    55: _hop_55,
    56: _hop_56,
    57: _hop_57,
    58: _hop_58,
}

#: The oldest project version this build reads. It sat at ``SCHEMA_VERSION``
#: while the chain was empty (#93: pre-production, nothing older worth
#: reading); the v56 additive bump (note 36 OV-10) keeps v55 readable through
#: the identity hop, so the floor is the oldest version a hop starts from.
SUPPORTED_FLOOR = min(MIGRATIONS) if MIGRATIONS else SCHEMA_VERSION


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
    if version < SUPPORTED_FLOOR or version > SCHEMA_VERSION:
        found = "no schema_version" if version < 0 else f"schema {version}"
        supported = (f"schema {SCHEMA_VERSION} only" if SUPPORTED_FLOOR == SCHEMA_VERSION
                     else f"schemas {SUPPORTED_FLOOR}-{SCHEMA_VERSION}")
        raise SchemaVersionError(
            f"This file is not readable by this build: {found}; this build reads "
            f"{supported}. Older projects are not migrated -- rebuild the "
            "project on the current version."
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
