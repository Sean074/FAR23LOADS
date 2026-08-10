"""Two guards against the schema discipline being broken silently (M4-10).

``io.py`` maps dataclasses to JSON by **hand-written field lists**. That is a
deliberate choice — it keeps the on-disk shape stable and reviewable — but it has
one failure mode that nothing else catches: adding a field to a persisted
dataclass and forgetting to add it to ``*_to_dict``/``*_from_dict``. The field
then works perfectly in memory, in every calc test, and silently vanishes the
moment the user saves and reloads. No existing test would notice.

Two guards:

1. **Sentinel round-trip** — fill every persisted field of a `Project` with a
   distinctive value, round-trip it through ``project_to_dict``/
   ``project_from_dict``, and assert nothing was dropped.
2. **Fields hash** — a hash of every persisted dataclass's field names, checked
   against a committed value. Changing a persisted shape fails this test, whose
   message says to bump ``SCHEMA_VERSION`` and add a migration hop. The
   discipline was previously unenforced.

The fields hash is *not* a correctness assertion — it is a tripwire. Its whole
value is that it fails, loudly, at the moment someone changes a persisted shape.
"""

import dataclasses
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads import models  # noqa: E402
from sloads.models import SCHEMA_VERSION  # noqa: E402

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


# --------------------------------------------------------------------------- #
# 1. Sentinel round-trip
# --------------------------------------------------------------------------- #
def _scalar_fields(obj):
    """(name, value) for every set, JSON-scalar field of a dataclass instance."""
    if not dataclasses.is_dataclass(obj):
        return []
    out = []
    for f in dataclasses.fields(obj):
        value = getattr(obj, f.name, None)
        if isinstance(value, (int, float, str, bool)) and not isinstance(value, bool):
            out.append((f.name, value))
    return out


def _walk(obj, path="project"):
    """Yield ``(path, name, value)`` for every scalar on every nested dataclass."""
    if dataclasses.is_dataclass(obj):
        for name, value in _scalar_fields(obj):
            yield path, name, value
        for f in dataclasses.fields(obj):
            child = getattr(obj, f.name, None)
            if dataclasses.is_dataclass(child):
                yield from _walk(child, f"{path}.{f.name}")
            elif isinstance(child, list):
                for i, item in enumerate(child):
                    if dataclasses.is_dataclass(item):
                        yield from _walk(item, f"{path}.{f.name}[{i}]")


def test_every_persisted_scalar_survives_a_round_trip():
    """The real project, walked field by field: nothing set may come back changed.

    This is the generic guard the hand-written ``to_dict`` field lists need — a
    new field that nobody wired into ``io.py`` silently disappears on save/reload,
    and every calc test still passes.
    """
    project = io.load_project(_GA)
    again = io.project_from_dict(io.project_to_dict(project))

    lost = []
    for path, name, value in _walk(project):
        holder = again
        for part in path.split(".")[1:]:
            if part.endswith("]"):
                attr, idx = part[:-1].split("[")
                holder = getattr(holder, attr, None)
                holder = holder[int(idx)] if holder and len(holder) > int(idx) else None
            else:
                holder = getattr(holder, part, None)
            if holder is None:
                break
        if holder is None:
            continue
        got = getattr(holder, name, None)
        if isinstance(value, float) and isinstance(got, float):
            if abs(got - value) > 1e-9 * max(1.0, abs(value)):
                lost.append((path, name, value, got))
        elif got != value:
            lost.append((path, name, value, got))

    assert not lost, (
        "these persisted fields did not survive project_to_dict/from_dict — "
        f"check io.py's hand-written field lists: {lost[:10]}"
    )


def test_round_trip_is_stable_at_the_dict_level():
    """Two passes must agree exactly; a field that only survives one pass is a
    half-wired mapping."""
    once = io.project_to_dict(io.load_project(_GA))
    twice = io.project_to_dict(io.project_from_dict(once))
    assert twice == once


# --------------------------------------------------------------------------- #
# 2. Fields hash
# --------------------------------------------------------------------------- #
def _persisted_dataclasses():
    """Every dataclass reachable from ``sloads.models``' public surface."""
    out = {}
    for name in getattr(models, "__all__", dir(models)):
        obj = getattr(models, name, None)
        if isinstance(obj, type) and dataclasses.is_dataclass(obj):
            out[name] = [f.name for f in dataclasses.fields(obj)]
    return dict(sorted(out.items()))


def fields_hash() -> str:
    """A stable digest of every persisted dataclass's field names."""
    blob = json.dumps(_persisted_dataclasses(), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


#: Committed digest. **When this test fails:** you changed a persisted dataclass.
#: Decide whether the change alters the on-disk *shape* — a new optional field
#: with a default does not (the tolerant readers handle it); a renamed, removed or
#: relocated field does. If it does: bump ``SCHEMA_VERSION`` and add a hop to
#: ``sloads.migrations.MIGRATIONS``. Then update this constant.
#: plan 11 B7: ``BalancedCaseResult`` gains the lateral residuals, the roll
#: relief, the applied ``unbal_moment``, ``hand`` and ``semi_span``.
#: plan 09 T1-T5 (v42): ``Project.tail_mass`` (a new ``TailMassInput``, itself
#: gaining ``control_load_mode`` at T5), ``LoadsResult.htail_span``/``.vtail_span``
#: (a new ``TailSpanResult``), and ``WingStationLoad.myy_free`` -- the free
#: per-strip torsion, which the cumulative ``myy`` is not.
#: plan 13 B8a-1 (v43): ``VTailLoadsInput.vtail_root_waterline_z`` -- the fin root
#: waterline, ``0`` meaning "derive it and mark it assumed" (decision L-1).
#: All additive with defaults, so ``SCHEMA_VERSION`` bumps but no migration hop
#: is needed -- absent *is* the documented value in every case.
#: plan 13 B8a-2: ``BalancedCaseResult`` gains ``delta_ny`` and
#: ``closure_inertia`` and **renames** ``delta_pitch``/``delta_roll`` to the
#: accelerations they became, ``p_dot``/``q_dot``/``r_dot``. A rename is not
#: additive -- but this hash covers every dataclass on ``sloads.models``' public
#: surface, not only the ones ``io.py`` writes, and ``BalancedCaseResult`` is a
#: **result**: ``Project`` holds no field of that type and ``io.py`` names none
#: of these fields, so nothing on disk has this shape and there is no hop to
#: write. Same standing as the B7 entry above, which changed the same class
#: without a version bump. ``SCHEMA_VERSION`` stays at 43.
#: tail-mass SSOT (v44): ``TailMassInput.weight_is_override`` -- the entered panel
#: weight demoted to an explicit override of the ``htail``/``vtail``-tagged
#: ``weight.items``; ``WingStationLoad.f_inertia`` -- the inertia part of ``fz``,
#: which a consumer needs separable so an assembled case applies the surface's
#: mass once; ``WingStationLoad.f_span``/``.s_span`` -- the span-axis
#: (axial) strip load and its cumulative, which only the fin has a producer for;
#: and ``TailSpanResult.n_y``/``.case_weight_lb`` -- the fin's lateral load factor
#: and the case weight it was formed from. All additive with defaults. The
#: version bumps for the first of them, which comes with the hop
#: ``migrations._v43_tail_mass_override``: absent is *not* the old behaviour there
#: (an entered weight used to be the only source and is now the override), so a
#: pre-v44 file has to be marked rather than reinterpreted.
EXPECTED_FIELDS_HASH = "82dbc19c625c139e"


def test_persisted_dataclass_shapes_are_unchanged():
    actual = fields_hash()
    assert actual == EXPECTED_FIELDS_HASH, (
        "a persisted dataclass changed shape.\n"
        f"  expected {EXPECTED_FIELDS_HASH}, got {actual}\n"
        "If the on-disk shape changed (a field renamed, removed or moved), bump "
        "SCHEMA_VERSION and add a hop to sloads.migrations.MIGRATIONS. If it is "
        "purely additive (a new optional field with a default), no hop is needed. "
        f"Either way, update EXPECTED_FIELDS_HASH in {os.path.basename(__file__)} "
        "to the value above."
    )


def test_the_fields_hash_actually_detects_a_change():
    """Test the test: a tripwire that cannot fire is worse than none."""
    baseline = fields_hash()

    @dataclasses.dataclass
    class _Sneaky:
        surprise: int = 0

    original = getattr(models, "__all__", None)
    try:
        models._TEST_ONLY_SNEAKY = _Sneaky
        if original is not None:
            models.__all__ = list(original) + ["_TEST_ONLY_SNEAKY"]
        assert fields_hash() != baseline, "the hash ignored a new persisted dataclass"
    finally:
        if original is not None:
            models.__all__ = original
        delattr(models, "_TEST_ONLY_SNEAKY")
    assert fields_hash() == baseline, "the tripwire did not reset"


def test_schema_version_is_an_int_and_matches_the_examples():
    assert isinstance(SCHEMA_VERSION, int)
    project = io.load_project(_GA)
    assert project.schema_version == SCHEMA_VERSION


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
