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
#: plan 09 T6/T7 (v45): ``TailMassInput.hinges_span_in``/``.actuator_span_in`` --
#: the control-surface attachment geometry ``control_load_mode = "discrete"``
#: requires; and the results it produces, ``ControlPointLoad`` (a hinge or
#: actuator attachment load) and ``TipTransfer`` (the h-tail set a T-tail's fin
#: carries at its tip), reached from ``TailSpanResult``'s new ``control_loads`` /
#: ``tip_transfer`` and its hinge-moment fields. Additive with defaults, and on
#: the input side absent *is* the documented value -- no attachment geometry
#: means the surface stays smeared, which is what every pre-v45 project already
#: was -- so ``SCHEMA_VERSION`` bumps to 45 with no migration hop.
#: M4-8 / step 10 piece 1 (v46): ``Project.safety_factors`` -- the governing
#: safety-factor table's **override layer** (decision G-11), carrying
#: ``SafetyFactorPolicyInput`` and ``SafetyFactorOverride``. Additive with a
#: ``None`` default, and the writer emits the key only when an override exists, so
#: absent *is* the documented value -- the factors 14 CFR 23.303/25.303 derives --
#: and every shipped fixture round-trips byte-for-byte. No migration hop.
#: step 10 piece 2 (v47): the weight/CG case model and the gear inputs (decisions
#: G-2, G-3, G-4, G-5, G-14). ``CgCase`` gains ``analyses``/``role``;
#: ``WeightInput`` gains ``max_landing_weight_lb``/``max_takeoff_weight_lb``;
#: ``MassItem`` gains ``consumable``; ``LandingGearInput`` gains
#: ``carrier``/``attach``; and ``FlightLoadsInput.cg_cases``,
#: ``LandingInput.cg_cases``, ``LandingInput.gross_weight_lb`` and
#: ``LandingInput.max_landing_weight_lb`` are **removed**. Removals and a
#: relocation are exactly what this tripwire exists for: absent is *not* the old
#: behaviour for any of them, so the hop ``migrations._v46_cg_case_model`` carries
#: each value across from the file's own rather than letting a reader default it.
#: step 10 piece 3 (v48): ``LandingGearInput.weight_lb`` -- the leg's own weight,
#: whole leg trunnion down, which closes the gear load report's free body
#: (decision G-12a). Purely additive with a ``0.0`` default, and the writer emits
#: the key only when stated, so absent *is* the documented value: "not stated",
#: which the report prints as a blank inertia term with its reason rather than as
#: a leg that weighs nothing. No migration hop, and no shipped number moves --
#: the assembled ground cases take gear mass from ``weight.items`` as they always
#: did, and this field is read by the report alone. Two **result** types move with
#: it, both additive and neither persisted as an input: ``GearReactionCase`` gains
#: ``weight_lb`` (the design weight the case is computed at -- ``WL``, which is
#: *not* the named loading's own weight on cases 13-22, since 23.473(a) scales
#: those to the take-off weight) and ``BalancedCaseResult`` gains ``cg_x``/``cg_z``
#: (the point its residuals are stated about). Both existed only implicitly
#: before, recoverable by looking the loading up **by name** -- which the ground
#: families broke, because "aft max landing" names two different targets in one
#: run.
#: body drag carrier (v49): ``LayoutInput.body_drag_waterline_z`` -- the waterline
#: the airplane's **non-wing** drag is applied at in the assembled model (design
#: note ``docs/40_history/24_body_drag_carrier_note.md``, decision D-1). Purely
#: additive with a ``0.0`` default, and ``0.0`` *is* a documented value rather
#: than a missing one: "derive it", which resolves to the wing reference plane
#: ``zw``, marked assumed and stated in-band -- the same contract v43 gave
#: ``vtail_root_waterline_z``. No migration hop. Two **result** fields move with
#: it, additive and not persisted: ``BalancedCaseResult`` gains ``body_axial``
#: (the non-wing drag, lb) and ``delta_cd`` (the wind-axis ``CD`` increment it
#: represents -- the diagnostic that must stay visible, because carrying the load
#: makes the applied axial resultant equal the trim's ``dx`` by construction).
#: h-tail attachment provenance (T-8a): ``TailSpanResult`` gains
#: ``attachment_assumed`` and ``attachment_basis`` beside ``attachment_y`` -- where
#: the beam's supports came from, so a structural model can gate on the basis
#: instead of trusting two numbers (note 24 BM-3). Both are **result** fields,
#: purely additive with defaults, and no input dataclass changed shape: the fixture
#: side of the same step is data (three fuselage outlines), not schema. No
#: migration hop, and ``SCHEMA_VERSION`` is unchanged.
#: Step 13 (v51, decision BM-1): ``SurfaceInput`` gains ``sob_y_in``, the
#: entered side-of-body butt line, read by the wing SOB reporting node and the
#: h-tail attachment. Additive with a ``None`` default ("not entered" -> the
#: half-fuselage-width fallback marked assumed), so no migration hop.
#: Step 12 (v52, the LRA beam model): ``FuselageSection.z_centre`` (section
#: centre waterline, R-4), ``EngineInput.mounted_on`` (BM-4),
#: ``AileronLoadsInput``/``FlapLoadsInput`` butt-line + hinge/actuator fields
#: (R-2/§6), and ``SurfaceInput.ref_axis_pct`` becomes Optional (R-7c: ``None``
#: = "not entered"; every reporting consumer reads the effective 25 % through
#: ``SurfaceInput.ref_axis``, and the io reader maps a stored 0.25 -- which the
#: pre-v52 writer emitted unconditionally, entered or not -- back to ``None``).
#: All additive/widening with unchanged effective defaults, so no migration hop.
#: backlog Pri 2 (design note 20 D-4 as revised 2026-08-17): ``BalancedCaseResult``
#: gains ``body_axial_clamped`` -- ``True`` on the cases whose forward non-wing
#: axial force was **not applied** because the trim ``alpha`` is outside the
#: polar's trusted window (``constants.POLAR_TRUSTED_ALPHA_DEG``). A **result**
#: field, additive with a ``False`` default and not persisted; no input dataclass
#: changed and ``SCHEMA_VERSION`` is unchanged.
#: Design note 29 (v53, wing-tank fuel separability, WF-1/WF-2): ``MassItem``
#: gains ``wing_fraction`` -- the fraction of a row (weight and own inertias)
#: reacted by the wing, the remainder by ``component``. Additive with a ``0.0``
#: default (today's behaviour bit-for-bit), so no migration hop; the 0.6.0
#: freeze's one schema hop.
#: Design note 19 rev. 3 (v54, L-7 lateral body aero -- the 0.7.0 freeze's one
#: hop): ``AeroCoefficientsInput.lateral_body_aero`` (``LateralBodyAeroInput``:
#: enabled / cy_beta / cn_beta, off by default) and its passenger
#: ``EngineInput.thrust_lb`` (decision L-7.10, reserved a day ahead of its
#: reader and read from #10, 2026-08-17); the
#: v-tail ``CriticalCondition`` gains ``beta_deg`` / ``cy_beta_fin`` /
#: ``cn_beta_fin`` and ``BalancedCaseResult`` gains ``body_side_force`` /
#: ``body_yaw_moment`` / ``beta_deg`` / ``cn_beta_net`` (result fields). All
#: additive with ``None``/``0.0`` defaults, so no migration hop.
#: Note 33 (DS-1, derived-scalar consolidation): five fields were **removed** —
#: ``WingMassInput.dihedral_deg``/``wrp_waterline`` and ``LandingInput.main_gear``/
#: ``nose_gear``/``tread_in``, plus ``LandingInput.wing_area_sqft`` and
#: ``FlightLoadsInput``'s ``mac``/``wing_area_sqft``/``xw``/``zw`` — ten fields in
#: all. A removal normally demands a hop, and this one does
#: not, for a reason that was checked rather than assumed: **none of the five was
#: ever written**. ``wing_mass_to_dict`` popped its two and ``landing_to_dict``
#: popped its three, so no `project.json` this program has ever produced contains
#: those keys — verified against all six shipped examples, whose ``landing`` and
#: ``wing_mass`` objects carry none of them, and whose save→reload→save is a fixed
#: point before and after. ``LandingInput.wing_area_sqft`` was popped by
#: ``landing_to_dict`` for the same reason, ``flight_loads_to_dict`` emitted only
#: xtc/xtf/mn/altitudes_ft, and all of it is covered by the same check. A legacy file that did carry them still loads: the
#: readers moved from an explicit exclusion list to ``_filtered``, which drops
#: unknown keys anyway. On-disk shape is therefore unchanged and
#: ``SCHEMA_VERSION`` stays at 54.
EXPECTED_FIELDS_HASH = "f47688a9acda539f"


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
