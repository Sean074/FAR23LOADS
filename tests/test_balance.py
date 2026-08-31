"""Balanced free-free airplane cases and the assembled deck (plan 11 B2-B5).

The mission's aim 2: *a full airplane balanced case -- wing tip to wing tip, nose
to tail -- with no need for a constraint, because the loads balance.*

The airplane has always balanced at **trim** (``LZW + LT == Nz*W``, asserted for
a long time in ``test_concept_closure``). What never inherited that balance was
the **distributed** load set: the wing distribution, the tail load, the fuselage
inertia and the trim solve were four calculations nothing assembled. These tests
gate the assembly.

Two kinds of check, and the distinction matters:

* **the residual before closure** -- what the physics actually achieves, gated at
  1 % of ``n*W`` / ``n*W*MAC`` (plan 11 §6 acceptance 1). This is the real
  measurement, and it is deliberately taken *before* any relief is applied;
* **closure to machine precision after** -- that the three-DOF relief does what
  it claims, checked both in memory and, separately, by re-deriving the resultant
  from the exported deck's own card text.

Three things this suite exists to keep from regressing, each of which was a real
error found while building:

1. ``WingStationLoad.myy`` is a *cumulative* torsion carrying the sweep/dihedral
   transfer, not a free moment. Treating it as free puts the pitching residual at
   20.5 % of ``n*W*MAC`` instead of 0.12 %.
2. The wing load must be at the balanced case's own flight condition, not the
   hand-entered one -- otherwise the two halves describe different conditions and
   the force residual runs 10-37 %.
3. The deck's nodes must sit at each load's true position. Flattening them onto
   the fuselage beam line, or letting a ballast item fall through to a shared
   node, unbalanced the *deck* by 3.9-21.9 % while the in-memory case still
   closed to 1e-13 -- visible only by re-deriving from the card text.
"""

import math
import os
import sys
from dataclasses import replace
from typing import NamedTuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from imperial_baseline import EXAMPLES

from sloads import io
from sloads import mass_distribution as md
from sloads.constants import DEG_PER_RAD, LBIN2_PER_SLUGFT2, POLAR_TRUSTED_ALPHA_DEG
from sloads.derived_geometry import (
    body_drag_waterline,
    require_wing_reference,
    wing_plane,
)
from sloads.export import balanced_deck as balanced_deck_module
from sloads.export.balanced_deck import (
    BALANCED_GEAR_BASE,
    BALANCED_WING_L_BASE,
    BALANCED_WING_R_BASE,
    balanced_case_rows,
    balanced_deck,
    case_sids,
    deck_nodes,
)
from sloads.export.coordinates import (
    reflect_force,
    reflect_moment,
    reflect_point,
    reflect_side,
)
from sloads.export.equilibrium import parse_cards, resultant
from sloads.gear_loads import gear_case_loads
from sloads.models import (
    BalancedLoad,
    MassComponent,
    MassItemKind,
    MissingInputError,
)
from sloads.modules import balance as balance_module
from sloads.modules import one_engine_out
from sloads.modules.balance import (
    BALANCED_VTAIL_CONDITIONS,
    FORCE_RESIDUAL_ACCEPTANCE,
    HANDEDNESS_TOL,
    RESIDUAL_GATE,
    ROLLING_WING_CONDITIONS,
    SKIP_REASONS,
    SKIPPED_RECORD_TITLE,
    SYMMETRIC_WING_CONDITIONS,
    build_balanced_cases,
    carry_sources_absent,
    fin_load,
    handed_twin,
    htail_load,
    htail_side_loads,
    is_ground,
    is_handed,
    is_lateral,
    is_powered,
    is_unsymmetrical_htail,
    polar_alpha_trusted,
    residual_gate_applies,
    residual_gate_exemptions,
    residual_gate_family,
    resultant6,
    skipped_condition_lines,
    source_case_name,
)
from sloads.modules.balance import resultant as case_resultant
from sloads.modules.select import default_critical, default_envelope
from sloads.modules.tail_span import build_tail_span, strip_spans
from sloads.modules.wing_inertia import inertia_units
from sloads.rigid_body import InertiaTensor, radians_per_s2
from sloads.tail_geometry import HTAIL, VTAIL, resolve_tail_planform
from sloads.units import Channel, UnitSystem, deliverable_units

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SYSTEMS = (UnitSystem.IMPERIAL, UnitSystem.SI)

#: Which fixtures assemble a balanced case at all, and how many.
#:
#: A condition is assembled only when the whole chain exists: SELECT named it, it
#: has a V-n point, and its CG case resolves to a **derivable** payload loading
#: (step C1). ``cessna_210``, ``atr42_100``, ``dhc8_dash8`` and ``concept_heavy``
#: produce none, because none of their payload cases is a loading their weight
#: database can actually produce -- a case needing 12-31 % of the airplane as
#: ballast has no honest inertia set, and inventing one would put fictitious mass
#: into the very balance the case exists to demonstrate. Filed on the backlog as
#: a fixture-data item; pinned here so it is a recorded fact, not a silent gap.
#:
#: ``(label, hand)`` pairs from B7: a rolling condition appears **twice**, once
#: per hand, and every other condition once with no hand.
#:
#: B8a-3 adds the four **lateral** conditions -- the vertical tail's own FAR
#: 23.441/23.443 set -- and every one of them is handed, because a fin load is
#: handed by construction (decision L-6, :func:`test_the_handedness_predicate`).
#: They assemble on both fixtures and on neither of the others, for the same
#: derivable-loading reason the symmetric families do.
_LATERAL_CASES = [
    ("SUDDEN RUDDER", "R"), ("SUDDEN RUDDER", "L"),
    ("YAW TO SIDESLIP", "R"), ("YAW TO SIDESLIP", "L"),
    ("YAW 15 NEUTRAL", "R"), ("YAW 15 NEUTRAL", "L"),
    ("SIDE GUST", "R"), ("SIDE GUST", "L"),
]

#: The 23.427(a) family (D-R8), handed by construction: SELECT puts 100 % of half
#: the governing tail load on one side and ``min(100 - 10(n-1), 80)`` percent on
#: the other, so both hands must be sized for and both are emitted. It sits
#: between the wing and lateral families because that is SELECT's own emission
#: order -- wing, h-tail, v-tail.
_UNSYMMETRICAL_CASES = [("UNSYMMETRICAL", "R"), ("UNSYMMETRICAL", "L")]

#: The symmetric wing families every fixture with a full V-n set reaches.
#: ``ACRL`` is handed only where SELECT names a rolling condition with a
#: **left/right** split; where it does not, the case is its own mirror image and
#: is emitted once, which is why the twins and the Cessna carry ``("ACRL", "")``
#: against ga6's and the RJ's handed pair.
_WING_CASES = [("PHAA", ""), ("PLAA", ""), ("PMAA", ""), ("NMAA", "")]

#: **Six of six fixtures assemble, since Pri 5 / D-26 (2026-08-15).** Four of
#: them produced nothing at all before: not for any failure of the assembly, but
#: because none of their payload cases was a loading their weight database could
#: produce. Correcting the case data to the database and entering a loading per
#: case is what brought them in -- the mechanism is unchanged.
#:
#: ``concept_heavy`` stops after ``ACRL`` because it carries no v-tail and no
#: unsymmetrical condition, not because anything was skipped for want of a
#: loading; ``test_every_condition_is_either_assembled_or_recorded`` is what
#: proves that distinction, per fixture.
_EXPECTED_CASES = {
    "ga6_normal.project.json": _WING_CASES + [
        ("ACRL", "R"), ("ACRL", "L"), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
    "cessna_210.project.json": _WING_CASES + [
        ("ACRL", ""), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
    "atr42_100.project.json": _WING_CASES + [
        ("ACRL", ""), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
    "dhc8_dash8.project.json": _WING_CASES + [
        ("ACRL", ""), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
    "concept_heavy.project.json": _WING_CASES + [("ACRL", "")],
    "concept_regional_jet.project.json": _WING_CASES + [
        ("ACRL", "R"), ("ACRL", "L"), ("TORS", ""),
    ] + _UNSYMMETRICAL_CASES + _LATERAL_CASES,
}

#: The **symmetric** ground families: LANDLOAD cases 1-9 (level 3-/2-wheel,
#: tail-down) and 13-18 (braked roll), each assembled once and unhanded. Both
#: main wheels carry the same reaction and ``ROLLP``/``YAWP`` are zero, so the
#: case is its own mirror image (decision G-8's measured table).
_GROUND_SYMMETRIC = [(f"LG-{n:02d}", "") for n in
                     list(range(1, 10)) + list(range(13, 19))]

#: The 23.483 one-wheel family: LANDLOAD supplies **neither** twin (cases 10-12
#: are the three loadings, one hand each), so the suite mints both and the id
#: takes the suffix.
_GROUND_ONE_WHEEL = [(f"LG-{n:02d}{h}", h) for n in (10, 11, 12) for h in ("R", "L")]

#: The 23.485 side family: LANDLOAD supplies **both** hands as three loadings x
#: two drift directions, so the ids are its own and unsuffixed. The odd member is
#: assembled and the even one is its reflection -- ``SMP`` is negative on the odd
#: member (0.5 W inboard to port), which is why the computed case is the **port**
#: one and its twin starboard.
_GROUND_SIDE = [(f"LG-{n:02d}", h) for n, h in
                ((19, "L"), (20, "R"), (21, "L"), (22, "R"), (23, "L"), (24, "R"))]

#: What each fixture's assembled ground family actually is: **the complete
#: 27-case family on every fixture that has landing-gear geometry**, since Pri 5 /
#: D-26 gave all three roled loadings on all five. It was ga6 alone until
#: 2026-08-15 (the RJ reached 2 of its 3 roled loadings and lost every case
#: sitting on the third -- 3, 6, 9, 12, 15, 18 and the 23/24 side pair).
#:
#: ``concept_heavy`` is the one empty row and for a different reason entirely: it
#: carries no gear geometry, so LANDLOAD produces nothing to assemble. That is
#: backlog Pri 8, not a loading problem.
_GROUND_FULL = (_GROUND_SYMMETRIC[:9] + _GROUND_ONE_WHEEL
                + _GROUND_SYMMETRIC[9:] + _GROUND_SIDE)
_EXPECTED_GROUND_CASES = {
    "ga6_normal.project.json": _GROUND_FULL,
    "cessna_210.project.json": _GROUND_FULL,
    "atr42_100.project.json": _GROUND_FULL,
    "dhc8_dash8.project.json": _GROUND_FULL,
    "concept_heavy.project.json": [],
    "concept_regional_jet.project.json": _GROUND_FULL,
}

#: The worst pre-closure **pitch** residual any fixture reaches, as a fraction of
#: ``n*W*MAC`` -- a *ratchet*, not a gate. The gate is plan 11's flat
#: ``RESIDUAL_GATE`` (1 %), and it now applies to every fixture and every family.
#:
#: **The per-fixture ceiling table is retired (body drag carrier, 2026-08-15).**
#: It existed because ``concept_regional_jet``'s high-speed low-CL cases sat over
#: 1 % (PLAA 1.041 %, TORS 1.174 %, SIDE GUST 1.586 %) and plan 11 R3's remedy was
#: "state the floor per fixture". The cause turned out to be neither of the two
#: things that were suspected: the assembled model carried **no non-wing drag**,
#: and the couple that missing force left about the CG was the residual. Carrying
#: it (``balance.body_axial_set``) drops every family on both fixtures to the
#: lift-model floor, so there is nothing left to except:
#:
#: =========================  ==========  ==========  ==============
#: fixture                    symmetric   lateral     unsym (trim half)
#: =========================  ==========  ==========  ==============
#: ``ga6_normal``             0.075 %     0.014 %     0.018 %
#: ``concept_regional_jet``   0.086 %     0.069 %     0.030 %
#: =========================  ==========  ==========  ==============
#:
#: This ratchet keeps the bite the per-fixture numbers used to provide: the flat
#: 1 % gate would now pass a **12x** regression on the RJ in silence. Raise a
#: number here only with the measurement that justifies it.
_PITCH_RESIDUAL_RATCHET = {
    "ga6_normal.project.json": {"symmetric": 0.0010, "lateral": 0.0005,
                                "unsymmetrical": 0.0005},
    "cessna_210.project.json": {"symmetric": 0.0010, "lateral": 0.0005,
                                "unsymmetrical": 0.0025},
    "atr42_100.project.json": {"symmetric": 0.0025, "lateral": 0.0010,
                               "unsymmetrical": 0.0065},
    "dhc8_dash8.project.json": {"symmetric": 0.0020, "lateral": 0.0010,
                                "unsymmetrical": 0.0040},
    "concept_heavy.project.json": {"symmetric": 0.0090, "lateral": 0.0010,
                                   "unsymmetrical": 0.0010},
    "concept_regional_jet.project.json": {"symmetric": 0.0005, "lateral": 0.0005,
                                          "unsymmetrical": 0.0010},
}

#: The worst pre-closure **force** residual each fixture reaches, as a fraction of
#: ``n*W`` -- and, since ``delta_n = residual_fz / W``, the same number as the
#: closure *relief*. Both are gated against this table.
#:
#: **Why this is a table and not plan 11's flat 1 %.** Until 2026-08-15 only
#: ``ga6_normal`` and ``concept_regional_jet`` assembled any balanced case, and
#: both sat under 1 %, so the flat gate was the whole story. Pri 5 / D-26 brought
#: the other four fixtures into the assembly, and measured across all six the
#: worst symmetric force residual runs:
#:
#: =========================  ===========  =========
#: fixture                    symmetric    lateral
#: =========================  ===========  =========
#: ``ga6_normal``             0.624 %      0.275 %
#: ``cessna_210``             1.190 %      0.404 %
#: ``concept_regional_jet``   1.506 %      0.349 %
#: ``dhc8_dash8``             1.626 %      0.523 %
#: ``atr42_100``              1.929 %      0.520 %
#: ``concept_heavy``          1.990 %      --
#: =========================  ===========  =========
#:
#: The ordering is the tell: ga6 -- the Appendix A airplane, the one fixture whose
#: aero and planform come from a printed source -- is best by 2x, and the concept
#: configurations are worst. This reads as **fixture data quality in the lift
#: model**, not a defect in the assembly: every case still closes exactly after
#: correction, and the *pitch* residual (the DOF that would expose a mis-placed
#: force) stays at 0.07-0.84 %. The spread is accepted rather than
#: absorbed silently (owner, 2026-08-22): the balanced full-span model has no
#: printed oracle behind it, so :data:`FORCE_RESIDUAL_ACCEPTANCE` -- the hard stop
#: no fixture may cross whatever this table says -- is the stated acceptance, and
#: this per-fixture table stays as the regression guard beneath it.
#:
#: **Re-measured 2026-08-17 (D-27, the fixture CG-datum reconciliation):** the
#: four type fixtures' flight cases are now the WTENV limit points themselves
#: (aft/fwd gross at MTOW, fwd regardless, min weight, mid gross), so the
#: heaviest cases sit at the aft limit at full gross weight and the worst
#: symmetric force residual moved with them -- ``cessna_210`` 1.209 %,
#: ``dhc8_dash8`` 1.818 %, ``atr42_100`` 2.360 % (the same fixture-lift-model
#: reading as before, now under a heavier aft-CG case; still under the 2.5 %
#: hard stop), while the regional jet's re-spaced cabin took its unclamped worst
#: *down* to 0.481 % (its clamped ``PHAA`` reads 1.04 %, and the relief gate
#: below reads this table for clamped cases too, so the RJ row covers it).
#: Lateral residuals moved 0.32-0.61 %. Ratchets re-pinned to those.
_FORCE_RESIDUAL_RATCHET = {
    "ga6_normal.project.json": {"symmetric": 0.0065, "lateral": 0.0030,
                                "unsymmetrical": 0.0030},
    "cessna_210.project.json": {"symmetric": 0.0125, "lateral": 0.0040,
                                "unsymmetrical": 0.0070},
    "atr42_100.project.json": {"symmetric": 0.0240, "lateral": 0.0065,
                               "unsymmetrical": 0.0140},
    "dhc8_dash8.project.json": {"symmetric": 0.0185, "lateral": 0.0065,
                                "unsymmetrical": 0.0100},
    "concept_heavy.project.json": {"symmetric": 0.0200, "lateral": 0.0030,
                                   "unsymmetrical": 0.0030},
    "concept_regional_jet.project.json": {"symmetric": 0.0110, "lateral": 0.0035,
                                          "unsymmetrical": 0.0040},
}

#: The hard stop on the force residual, whatever the ratchet above records: the
#: level at which "a small correction to a balance that nearly held" stops being a
#: fair description of the closure. Plan 11 stated a flat 1 % for both components;
#: the owner accepted this value as the **force** half on 2026-08-22 (none of these
#: six fixtures is a printed oracle, unlike the FAR23 core) and it moved into the
#: package so the report judges force against the same number the tests do. Read
#: from the owner here rather than re-declared -- a second copy is how the report
#: and the suite came to disagree in the first place (CR-C-2).
FORCE_RESIDUAL_CEILING = FORCE_RESIDUAL_ACCEPTANCE

#: Cases whose forward non-wing axial force is **not applied** (backlog Pri 2,
#: design note 20 D-4 as revised 2026-08-17): the trim ``alpha`` is outside the
#: polar's trusted window :data:`~sloads.constants.POLAR_TRUSTED_ALPHA_DEG` and
#: the airplane-less-tail polar less the wing strips came out forward. On these
#: cases -- and only these -- the assembled model is out of trim by exactly the
#: clamped force and the couple it made about the CG at the body-drag waterline,
#: so both pre-closure residuals re-open and are gated **per case** here as
#: ``(force, pitch)`` ceilings instead of by the family ratchets above. Measured
#: 2026-08-17: the three crude-polar fixtures' ``NMAA`` (alpha -12.9 to -14.3
#: deg, forward 1.0-1.4 klb, pitch 1.5-2.1 % because the wing plane the load
#: sat on is ~40 in from the CG on a high-wing turboprop) and the regional jet's
#: four cases above +15 / below -10 deg. An entry here is asserted to still
#: clamp, so it cannot outlive the condition it records; a clamp not recorded
#: here fails :func:`test_the_pre_closure_residual_is_within_the_gate` loudly.
#: Re-measured 2026-08-17 under D-27's limit-point cases: ``dhc8_dash8``'s and
#: the regional jet's ``NMAA`` no longer clamp (their trim alpha came back inside
#: the trusted window at the new CG stations); the RJ's ``PHAA`` clamp grew to
#: 1.04 % force / 0.59 % pitch at the aft-gross point.
_CLAMPED_BODY_AXIAL = {
    "atr42_100.project.json": {"NMAA": (0.0030, 0.0165)},
    "concept_heavy.project.json": {"NMAA": (0.0060, 0.0220)},
    "concept_regional_jet.project.json": {"PHAA": (0.0110, 0.0065),
                                          "ACRL": (0.0020, 0.0020)},
}

#: The hard stop on a clamped case's pitch residual, the pitch twin of
#: :data:`FORCE_RESIDUAL_CEILING`. Above this the un-applied force is no longer
#: "a difference between two drag models where one is not trusted" but a load
#: the model is missing, and the fixture's polar needs re-entering.
CLAMPED_PITCH_CEILING = 0.025


class _Ref(NamedTuple):
    """The point a case's residual is stated about."""
    xcg: float
    zcg: float


def _ref_of(case) -> _Ref:
    """The reference point ``case`` was assembled about.

    Read off the case rather than looked up by loading name. The name lookup
    (``{c.name: c for c in flight_cases(project)}``) stopped being able to answer
    the question when the ground families arrived: those sit at design weights
    that are not any *named* loading's own, because 23.473(a) lets LANDLOAD scale
    cases 13-22 to the take-off weight, so "aft max landing" names two different
    targets in one run.
    """
    return _Ref(case.cg_x, case.cg_z)


def _family(case) -> str:
    """``"ground"``, ``"lateral"``, ``"unsymmetrical"`` or ``"symmetric"`` --
    which of the four balanced families a case belongs to.

    Named off the *applied* load set through balance's own readers, so the test
    suite cannot drift from what the deck header calls each family.

    ``"ground"`` is asked **first** because a ground case can also carry lateral
    content (the 23.485 side family does, in full) and would otherwise be gated
    as a rudder kick. It is its own family for the reason G-9 gives: ground and
    flight cases load different structure by different paths, and the gates that
    apply to them are different too.
    """
    if is_ground(case):
        return "ground"
    if is_lateral(case):
        return "lateral"
    return "unsymmetrical" if is_unsymmetrical_htail(case) else "symmetric"


def _flight_cases(project):
    """The balanced cases of the three **flight** families.

    The gates written for those families are asked of this rather than of
    ``build_balanced_cases`` directly: a ground case has no trim to be measured
    against, so a residual gate on it would be a gate on nothing (its own gate,
    G-6's closed-form one, is in :func:`test_the_ground_closure_reproduces_landload`).
    """
    return [c for c in build_balanced_cases(project) if not is_ground(c)]


def _ground_cases(project):
    """The balanced cases of the ground family alone."""
    return [c for c in build_balanced_cases(project) if is_ground(c)]


def _landload_conditions(project):
    """LANDLOAD's 33 ground conditions, or none where the project has no gear.

    The ground family's analogue of ``default_critical(project).conditions``: the
    set the assembly must account for, whether by assembling it, by deriving it as
    a twin, or by recording why not.
    """
    try:
        return gear_case_loads(project)
    except MissingInputError:
        return []


def _project(example: str):
    return io.load_project(os.path.join(_ROOT, "examples", example))


def _with_cases():
    return [e for e, v in _EXPECTED_CASES.items() if v]


def _with_ground_cases():
    """Fixtures whose assembled family includes ground cases.

    ``concept_heavy`` carries no landing-gear geometry (backlog Pri 8), so it has
    no gear reference point to find. Driven off the pinned table rather than off a
    ``if not x: return``, so a fixture that *stops* producing ground cases fails
    :func:`test_which_ground_cases_assemble_is_pinned` instead of quietly dropping
    out of every test that needs one.
    """
    return [e for e, v in _EXPECTED_GROUND_CASES.items() if v]


def _with_handed_cases():
    """Fixtures that assemble at least one handed (left/right) flight case.

    ``concept_heavy`` has no v-tail and no unsymmetrical condition, so every case
    it produces is its own mirror image and there is no twin to compare.
    """
    return [e for e, v in _EXPECTED_CASES.items() if any(h for _, h in v)]


def _with_handed_roll():
    """Fixtures whose ``ACRL`` is handed -- i.e. that actually roll.

    SELECT hands a rolling case only where it names a left/right split; on
    ``cessna_210``, ``atr42_100``, ``dhc8_dash8`` and ``concept_heavy`` it does
    not, so their ``ACRL`` is symmetric and carries no applied roll couple. Those
    fixtures have nothing for a roll-closure test to check -- which is a property
    of their input, pinned in :data:`_EXPECTED_CASES`, not a gap here.
    """
    return [e for e, v in _EXPECTED_CASES.items()
            if ("ACRL", "R") in v or ("ACRL", "L") in v]


def _with_lateral_cases():
    """Fixtures that assemble the v-tail's lateral family.

    ``concept_heavy`` carries no vertical tail, so SELECT names no lateral
    condition for it and there is nothing to pin.
    """
    return [e for e, v in _EXPECTED_CASES.items() if ("SUDDEN RUDDER", "R") in v]


def _with_unsymmetrical_cases():
    """Fixtures that assemble the 23.427(a) unsymmetrical h-tail pair.

    ``concept_heavy``'s V-n set names no unsymmetrical condition.
    """
    return [e for e, v in _EXPECTED_CASES.items() if ("UNSYMMETRICAL", "R") in v]


# --------------------------------------------------------------------------- #
# Scope
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_which_conditions_assemble_is_pinned(example):
    got = [(c.label, c.hand) for c in _flight_cases(_project(example))]
    assert got == _EXPECTED_CASES[example], example


@pytest.mark.parametrize("example", EXAMPLES)
def test_which_ground_cases_assemble_is_pinned(example):
    """**G-13's coverage pin for the assembled ground family.**

    Pinned by **case id** rather than by label, because the ground labels repeat
    (three loadings share "3-wheel level landing") and the id is what a consumer
    joins on. The pin is deliberately a statement of *coverage*, not only of
    correctness -- it goes red the day a fixture gains a derivable ground loading,
    which is the mechanism ``test_which_conditions_assemble_is_pinned`` already
    uses and the reason G-13 says coverage is "pinned, not chased".

    Two fixtures reach the assembled ground cases and four do not, and the
    asymmetry is the already-pinned Pri 9 fixture-data finding rather than
    anything about this step: a ground case needs a **derivable mass loading**,
    and ``cessna_210`` / ``atr42_100`` / ``dhc8_dash8`` produce none for the same
    reason they produce no flight balanced case. ``concept_heavy`` has no gear
    geometry at all. Every one of them is *recorded*, not silently absent.

    Note what the ids say about G-8, which is the whole handedness decision
    visible in one list: ``LG-10R``/``LG-10L`` are **minted** (the 23.483
    one-wheel condition exists once, so its two hands are suffixes), while
    ``LG-19``/``LG-20`` are **LANDLOAD's own** (the 23.485 family ships both
    drift directions), so they carry no suffix and differ only in the ``hand``
    field. The gear report, which needs no mass loading, reaches five fixtures --
    a different set, pinned separately in ``test_gear_report.py``.
    """
    got = [(c.case_ref.case_id, c.hand) for c in _ground_cases(_project(example))]
    assert got == _EXPECTED_GROUND_CASES[example], example


# --------------------------------------------------------------------------- #
# The skipped-conditions record (review F-C7)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_every_condition_is_either_assembled_or_recorded(example):
    """**The F-C7 gate.** No condition SELECT named may leave the assembly
    unaccounted for.

    Before this, a missing V-n point, an unknown CG case or a non-derivable
    loading each dropped a condition with no record anywhere -- and the only
    thing standing between that and a user's project was ``_EXPECTED_CASES``
    above, which pins the *shipped fixtures'* drop set and nothing else. This
    asserts the property instead of the fixture: assembled ∪ recorded is exactly
    SELECT's set, and the two are disjoint.
    """
    project = _project(example)
    skipped = []
    cases = build_balanced_cases(project, skipped)

    named = {(c.component, c.label, c.case)
             for c in default_critical(project).conditions}
    # SELECT is no longer the only producer of conditions this assembly must
    # account for. The ground families come from LANDLOAD's own 1..33 case
    # numbering (decision G-1 puts them in the assembled deck), so the property
    # is stated over both producers -- otherwise adding a family would quietly
    # weaken the gate from "everything is accounted for" to "everything SELECT
    # named is".
    named |= {("landing_gear", g.description, g.case)
              for g in _landload_conditions(project)}
    assembled = {(c.case_ref.component, c.label, c.vn_case) for c in cases}
    recorded = {(s.component, s.label, s.case) for s in skipped}
    assert assembled | recorded == named, sorted(named ^ (assembled | recorded))
    assert not (assembled & recorded), sorted(assembled & recorded)
    # Every recorded reason is one of the declared ones -- a hand-written
    # sentence at a fifth ``continue`` would slip past the two set checks above.
    assert {s.code for s in skipped} <= set(SKIP_REASONS), skipped
    assert all(s.reason == SKIP_REASONS[s.code] for s in skipped)


def test_the_record_names_the_conditions_a_loading_cannot_carry():
    """A condition dropped for want of a loading is *stated*, with its reason
    (review F-C7), rather than silently absent from the primary deliverable.

    The concrete case F-C7 was raised on was ``concept_regional_jet``'s **NMAA**,
    flown at ``CG3 fwd light``. It assembles since D-25, and since Pri 5 / D-26
    (2026-08-15) **no shipped fixture drops a condition for want of a loading at
    all** -- every case of every fixture states one. So the unreachable case is
    made here: a mechanism whose only test is "some fixture happens to fail"
    stops testing anything the day the fixtures are fixed, which is the day this
    step arrived.

    The rest of the record is still read off the fixture as shipped, because the
    *other* skip codes are structural and permanent.
    """
    project = _project("concept_regional_jet.project.json")

    # As shipped: nothing is dropped for want of a loading any more.
    shipped = []
    build_balanced_cases(project, shipped)
    assert [s for s in shipped if s.code == "loading-not-derivable"] == []
    assert "NMAA" not in {s.label for s in shipped}     # closed by D-25

    # Put one flight case beyond what the weight database can load, and the
    # record must name every condition that sits on it, with its reason.
    #
    # The CG is moved 73 in forward of the case as shipped: far enough forward
    # that no subset of the discretionary items plus a ballast row reproduces it,
    # near enough that the airplane still trims there. The perturbation used to
    # be ``min(item.x) - 40``, i.e. 40 in ahead of the forwardmost mass in the
    # airplane and 484 in ahead of the design CG -- a CG no airplane flies at,
    # where the balance cannot reach 1 g at any angle of attack. It reported one
    # anyway (NZ 0.658 at alpha 41 deg, presented as a 1-g point) until #33 gave
    # the iteration a failure channel; now it refuses, and this test would be
    # exercising that refusal instead of the loading record it is about.
    case = next(c for c in project.weight.cg_cases if c.name == "fwd gross")
    case.loading = None
    case.xcg = 500.0
    skipped = []
    build_balanced_cases(project, skipped)
    not_derivable = [s for s in skipped if s.code == "loading-not-derivable"]
    assert not_derivable, skipped
    assert all(s.reason for s in not_derivable)
    # The fuselage family is a deliberate exclusion, and is recorded as one
    # rather than left to be inferred from its absence. The h-tail's *symmetric*
    # conditions are a different statement since D-R8 -- they are already in
    # every case, as the trim tail load -- and only 23.427(a) assembles.
    # Read off the record as *shipped*: these codes are structural and permanent,
    # and the perturbation above would add its own rows to both components.
    assert {s.code for s in shipped if s.component == "fuselage"} == {
        "out-of-family"}
    assert {s.code for s in shipped if s.component == "htail"} == {
        "htail-symmetric"}
    assert "UNSYMMETRICAL" not in {s.label for s in shipped}


@pytest.mark.parametrize("example", _with_cases())
def test_the_deck_states_what_it_does_not_cover(example):
    """The record travels in the deck's own ``$`` block.

    A deck lists what it holds; a condition that dropped out is invisible in it
    by construction. The block is emitted whether or not anything was skipped --
    "none" is the completeness statement, and a block that appears only on a
    lossy run cannot be told from a deck written before the record existed.
    """
    project = _project(example)
    skipped = []
    build_balanced_cases(project, skipped)
    text = balanced_deck(project)
    assert "CONDITIONS NOT ASSEMBLED" in text
    # The block is line-wrapped, so it is compared as unwrapped text: every
    # recorded line, verbatim, has to be in there.
    block = " ".join(
        ln.lstrip("$ ").lstrip("- ") for ln in _skipped_lines_of(text))
    block = " ".join(block.split())
    for line in skipped_condition_lines(skipped):
        assert " ".join(line.split()) in block, (example, line)
    # The deck the caller supplies cases to states the same record as the one
    # that assembles them itself -- the GUI path must not lose the block.
    assert _skipped_lines_of(text) == _skipped_lines_of(
        balanced_deck(project, cases=build_balanced_cases(project),
                      skipped=skipped))


def test_the_deck_block_says_none_when_nothing_was_skipped():
    assert ("None -- every condition SELECT named assembled into a case."
            in _skipped_block([]))


def test_the_module_result_carries_the_record():
    """The record is on the ``ModuleResult`` too, so every consumer of the module
    (report, CSV, GUI) states it without re-running the assembly."""
    project = _project("concept_regional_jet.project.json")
    result = balance_module.run(project)
    record = [c for c in result.conditions if c.title == SKIPPED_RECORD_TITLE]
    assert len(record) == 1, [c.title for c in result.conditions]
    row = record[0]
    skipped = []
    build_balanced_cases(project, skipped)
    assert row.values[0].value == float(len(skipped))
    assert row.values[0].key == "balanced_skipped_count"
    assert "supplementary nose-wheel" in row.note
    # It is a statement about the run, not a load case: no case_ref, so it mints
    # no case-index row, and its one value is dimensionless so the ULTIMATE
    # boundary passes it through unscaled.
    assert row.case_ref is None
    assert row.values[0].units == ""


@pytest.mark.parametrize("example",
                         [e for e, v in _EXPECTED_GROUND_CASES.items() if v])
def test_a_ground_row_cites_its_own_far_condition(example):
    """**R6-C1's pin.** A ground condition row in the module result cites the
    FAR condition LANDLOAD computed it under -- its ``CaseRef``'s own
    ``far_reference`` (23.479(a) ... 23.493) -- never the flight balancing
    literal 23.321, which is what every ground row rendered with before the
    fix. The flight families are asserted unchanged in the same walk: their
    ``CaseRef`` names the V-n envelope source (23.333), but the balancing of
    that point is 23.321's requirement, so those rows keep their literals.
    ``run()`` emits one row per built case in order, plus the trailing F-C7
    record, which is what lets the walk pair them."""
    project = _project(example)
    cases = build_balanced_cases(project)
    rows = balance_module.run(project).conditions
    assert len(rows) == len(cases) + 1  # + the skipped-conditions record
    ground = 0
    for case, row in zip(cases, rows):
        if is_ground(case):
            assert row.far_reference == case.case_ref.far_reference, row.title
            assert row.far_reference.startswith("23.4"), row.title
            ground += 1
        elif not (is_lateral(case) or is_unsymmetrical_htail(case)):
            assert row.far_reference in ("23.321", "23.349"), row.title
    assert ground == len(_EXPECTED_GROUND_CASES[example])


def _skipped_block(skipped):
    from sloads.export.balanced_deck import _skipped_block as block
    return "\n".join(block(skipped))


def _skipped_lines_of(deck_text: str):
    lines = deck_text.splitlines()
    start = lines.index(
        "$ ------------------------------ CONDITIONS NOT ASSEMBLED (SELECT set)")
    end = lines.index("$", start)
    return lines[start:end]


# --------------------------------------------------------------------------- #
# The gate: the residual BEFORE closure (plan 11 acceptance 1)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _with_cases())
def test_the_residual_gate_family_is_the_predicates(example):
    """``residual_gate_applies`` IS the exemption, and it keeps lateral in (CR-C-2).

    The three surfaces that summarise a worst residual each used to decide the
    family for themselves and each decided differently. This pins what the one
    owner answers, on every fixture: exempt exactly where an applied load is the
    whole pre-closure ``Fz``/``My``, and **not** exempt for the lateral family --
    those two fractions are precisely the symmetric half that :func:`is_lateral`
    names as the gate that does apply to it, so dropping the family would delete
    a live gate rather than fix a false one. It passes, which is the point.
    """
    cases = build_balanced_cases(_project(example), [])
    for case in cases:
        expected = not (is_ground(case) or is_unsymmetrical_htail(case)
                        or is_powered(case))
        assert residual_gate_applies(case) is expected, f"{example} {case.label}"

    lateral = [c for c in cases if is_lateral(c)]
    if lateral:
        assert all(residual_gate_applies(c) for c in lateral)
        worst = max(max(c.force_residual_fraction, c.moment_residual_fraction)
                    for c in lateral)
        assert worst < RESIDUAL_GATE, (
            f"{example}: lateral symmetric half at {worst:.3%} -- the gate this "
            "family IS held to has started failing")

    # And the exemptions a surface states are the families actually present.
    stated = " ".join(residual_gate_exemptions(cases))
    assert ("ground" in stated) == any(is_ground(c) for c in cases)
    assert ("h-tail" in stated) == any(is_unsymmetrical_htail(c) for c in cases)


@pytest.mark.parametrize("example", _with_cases())
def test_the_judged_family_excludes_the_clamped_cases(example):
    """``residual_gate_family`` splits off the cases the flat acceptances do not fit.

    A clamped case is out of trim by exactly the non-wing axial force that was not
    applied and the couple it made (design note 20 D-4), so its residual is a known
    measured quantity gated per case in :data:`_CLAMPED_BODY_AXIAL` -- judging it
    against the flat acceptance instead reports a modelling decision as a failure.
    Pinned here because the split is what keeps the report's §6 sentence true: the
    judged family clears both acceptances on every fixture, and the clamped one
    does not have to.
    """
    cases = build_balanced_cases(_project(example), [])
    judged, clamped = residual_gate_family(cases)
    assert all(residual_gate_applies(c) for c in judged + clamped)
    assert not any(c.body_axial_clamped for c in judged)
    assert all(c.body_axial_clamped for c in clamped)
    assert {id(c) for c in judged + clamped} == {
        id(c) for c in cases if residual_gate_applies(c)}

    assert max(c.force_residual_fraction for c in judged) < FORCE_RESIDUAL_ACCEPTANCE
    assert max(c.moment_residual_fraction for c in judged) < RESIDUAL_GATE
    # The clamped record is per case and lives with the gate that uses it, so the
    # split cannot quietly become a way of not measuring them.
    for case in clamped:
        assert case.label in _CLAMPED_BODY_AXIAL.get(example, {}), (
            f"{example} {case.label}: clamped but not recorded")



@pytest.mark.parametrize("example", _with_cases())
def test_the_pre_closure_residual_is_within_the_gate(example):
    """``|dFz|/(n*W)`` and ``|dMy|/(n*W*MAC)`` both under plan 11's flat 1 %.

    The gate is on the physics, not on the correction -- which is the whole point
    of measuring it before closure. **Force** meets it on every case of every
    fixture (ga6 0.05-0.62 %, RJ 0.03-0.70 %). **Pitch** now does too, on every
    fixture and every family, at 0.014-0.086 %: the per-fixture ceiling the RJ's
    low-CL cases used to need was retired when the body drag carrier landed, and
    :data:`_PITCH_RESIDUAL_RATCHET` records what each family actually reaches so
    the flat gate cannot pass a 12x regression in silence.

    The **roll** and **yaw** DOF are deliberately not gated here. On a rolling
    case ``residual_mx`` is the applied aileron couple; on a lateral case
    ``residual_fy``/``residual_mz`` are the applied fin load in full. In both
    the airplane is *supposed* not to balance them -- it rolls and yaws instead
    -- so a residual gate on those components would be a gate on nothing. See
    :func:`test_the_roll_moment_is_the_applied_couple` and
    :func:`test_the_symmetric_half_of_a_lateral_case_still_closes`.

    The **23.427(a)** family is excluded from ``Fz``/``My`` for the same kind of
    reason and it is the strongest instance of it (D-R8): its applied tail load
    is a *maneuver* load and replaces the trim tail load its V-n point balances
    at, so the airplane is genuinely out of trim and the residual is that
    mismatch in full -- 49.8 % of ``n*W`` on ``ga6_normal``. Gating it here would
    gate the maneuver. What is gated instead is the case's **trim half**, at the
    same 1 %, in
    :func:`test_the_trim_half_of_an_unsymmetrical_case_still_closes`.

    A **powered** case (backlog #10) is excluded for the same reason and is
    stated here so the exemption cannot be discovered later from a failure: the
    V-n point it is assembled at is thrust-free, so the entered hub thrust and
    its couple about the CG are the pre-closure ``Fx`` and ``My`` in full, by
    construction, and are reacted by ``delta_nx`` and ``q_dot``
    (:func:`sloads.modules.balance.hub_thrust_set`). No shipped fixture enters
    thrust, so this branch is never taken here; what gates the powered case is
    ``tests/test_hub_thrust.py``, whose G-3 asserts the residual **is** the
    thrust, to the last digit, rather than merely being small.
    """
    clamped_seen = set()
    for case in _flight_cases(_project(example)):
        if _family(case) == "unsymmetrical" or is_powered(case):
            continue
        where = f"{example} {case.label}{case.hand}"
        if case.body_axial_clamped:
            # Out of trim by the un-applied forward force and its couple; gated
            # per case against what was measured when the clamp was decided.
            clamped_seen.add(case.label)
            recorded = _CLAMPED_BODY_AXIAL.get(example, {}).get(case.label)
            assert recorded is not None, (
                f"{where}: the non-wing force is clamped but the case is not "
                "recorded in _CLAMPED_BODY_AXIAL")
            f_ceiling, p_ceiling = recorded
            assert case.force_residual_fraction < min(f_ceiling, FORCE_RESIDUAL_CEILING), (
                f"{where}: force residual {case.force_residual_fraction * 100:.3f} % "
                f"over the clamped-case ceiling {f_ceiling * 100:.2f} %")
            assert case.moment_residual_fraction < min(p_ceiling, CLAMPED_PITCH_CEILING), (
                f"{where}: pitch residual {case.moment_residual_fraction * 100:.3f} % "
                f"over the clamped-case ceiling {p_ceiling * 100:.2f} %")
            continue
        force_ceiling = _FORCE_RESIDUAL_RATCHET[example][_family(case)]
        assert case.force_residual_fraction < FORCE_RESIDUAL_CEILING, (
            f"{where}: force residual {case.force_residual_fraction * 100:.3f} % "
            f"is over the hard ceiling {FORCE_RESIDUAL_CEILING * 100:.1f} %")
        assert case.force_residual_fraction < force_ceiling, (
            f"{where}: force residual {case.force_residual_fraction * 100:.3f} % "
            f"is over the {_family(case)} ratchet {force_ceiling * 100:.2f} % "
            "-- see _FORCE_RESIDUAL_RATCHET")
        assert case.moment_residual_fraction < RESIDUAL_GATE, (
            f"{where}: pitch residual {case.moment_residual_fraction * 100:.3f} %")
        ratchet = _PITCH_RESIDUAL_RATCHET[example][_family(case)]
        assert case.moment_residual_fraction < ratchet, (
            f"{where}: pitch residual {case.moment_residual_fraction * 100:.4f} % "
            f"is inside the 1 % gate but over the {_family(case)} ratchet "
            f"{ratchet * 100:.2f} % -- see _PITCH_RESIDUAL_RATCHET")
    # The record cannot outlive the condition it excuses.
    for label in _CLAMPED_BODY_AXIAL.get(example, {}):
        assert label in clamped_seen, (
            f"{example} {label}: recorded in _CLAMPED_BODY_AXIAL but no longer "
            "clamped -- remove the entry")


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_relief_is_small(example):
    """``|dn|/n < 1 %`` (plan 11 acceptance 2) -- how much of the balance was
    assumed rather than computed.

    Read the other way round on the 23.427(a) family, and deliberately: there the
    relief is not a correction to a balance that nearly held, it is the airplane's
    response to a maneuver tail load (-0.496 g on ``ga6_normal``), so it is the
    *answer* rather than a measure of how much was assumed. It is bounded by its
    own gate -- the trim half -- and reported per case in the table and the deck
    header.
    """
    for case in _flight_cases(_project(example)):
        if _family(case) == "unsymmetrical":
            continue
        ceiling = _FORCE_RESIDUAL_RATCHET[example][_family(case)]
        assert abs(case.delta_n / case.nz) < ceiling, (
            f"{example} {case.label}: relief {abs(case.delta_n / case.nz) * 100:.3f} % "
            f"over the {_family(case)} ratchet {ceiling * 100:.2f} % "
            "-- see _FORCE_RESIDUAL_RATCHET")


@pytest.mark.parametrize("example", _with_cases())
def test_the_case_closes_in_all_three_symmetric_dof(example):
    """After closure: ``Fx``, ``Fz`` and ``My`` about the CG are zero to machine
    precision.

    Three degrees of freedom, not the two plan 11 B-3 anticipated. Nothing else
    in the assembled model reacts **drag** -- the suite has no distributed thrust
    -- so leaving x open puts 17-26 % of ``n*W`` into the support reaction and
    makes "reactions ~ 0" untrue in a deck that still solves. FAR 23's ``nx`` is
    exactly this quantity.
    """
    p = _project(example)
    for case in build_balanced_cases(p):
        cg = _ref_of(case)
        fx, fz, my = case_resultant(case.loads, (cg.xcg, 0.0, cg.zcg))
        scale = case.n_w
        assert abs(fx) < 1e-6 * scale, f"{example} {case.label} Fx"
        assert abs(fz) < 1e-6 * scale, f"{example} {case.label} Fz"
        assert abs(my) < 1e-6 * scale * case.mac, f"{example} {case.label} My"


@pytest.mark.parametrize("example", _with_cases())
def test_the_inertia_set_weighs_the_case(example):
    """Σ modelled mass == the payload case's weight, exactly.

    The mass SSOT's guarantee carried into the balance: wing mass comes from the
    loading's WING items (spread by WINGINER's shape) and everything else from
    the beam items, so the two partition the airplane rather than overlapping.
    Where they overlapped -- the wing-tank fuel on two fixtures -- taking WINGINER's
    own panel+concentrated model instead cost 12-13 % of ``n*W``.
    """
    for case in build_balanced_cases(_project(example)):
        modelled = sum(ld.weight_lb for ld in case.loads
                       if ld.source in ("wing-inertia", "body-inertia"))
        assert modelled == pytest.approx(case.weight_lb, rel=1e-9), \
            f"{example} {case.label}"


def test_wing_items_with_no_panel_model_raise_rather_than_vanish():
    """The B-2 partition's edge-case gate (review **F-C5**).

    ``panel_weight_lb = 0`` makes WINGINER integrate no panel, so the wing
    inertia scale has nothing to scale onto -- while ``assembly_distributes_mass``
    goes on excluding the same WING items from ``body_inertia`` because the wing
    set is meant to carry them. The whole WING item weight used to leave the
    model there, absorbed silently by the closure. No shipped fixture reaches it,
    which is why it needs its own case: ``ga6_normal``'s 330 lb of wing items
    against an emptied panel model.
    """
    p = _project("ga6_normal.project.json")
    wing = sum(it.weight_lb for it in p.weight.items
               if md.component_of(it, p) is MassComponent.WING)
    assert wing, "fixture must carry WING-tagged item mass for this to gate"

    p.wing_mass = replace(p.wing_mass, panel_weight_lb=0.0)
    with pytest.raises(MissingInputError) as exc:
        build_balanced_cases(p)
    assert f"{wing:.0f} lb" in str(exc.value)


def test_no_wing_items_and_no_panel_still_weighs_the_case():
    """The other half of the gate: nothing to spread is not an error.

    With the WING tag off the items, the fuselage beam carries them, the wing
    inertia scale is legitimately 0.0 and no mass is lost -- so this must build,
    and the partition must still weigh the whole case.
    """
    p = _project("ga6_normal.project.json")
    p.weight.items = [replace(it, component=MassComponent.FUSELAGE)
                      if md.component_of(it, p) is MassComponent.WING else it
                      for it in p.weight.items]
    p.wing_mass = replace(p.wing_mass, panel_weight_lb=0.0)

    cases = build_balanced_cases(p)
    assert cases
    for case in cases:
        modelled = sum(ld.weight_lb for ld in case.loads
                       if ld.source in ("wing-inertia", "body-inertia"))
        assert modelled == pytest.approx(case.weight_lb, rel=1e-9), case.label
        assert not [ld for ld in case.loads if ld.source == "wing-inertia"]


# --------------------------------------------------------------------------- #
# The body drag carrier (design note 20_body_drag_carrier_note.md), gates G1-G10
# --------------------------------------------------------------------------- #
#: The wind-axis ``dCD`` the non-wing drag represents, per fixture: ``(lo, hi)``.
#:
#: **What has physical content is the consistency, not the value.** A missing
#: parasite term is a ``CD`` offset independent of ``CL``, so on ``ga6_normal``
#: this is a near-constant **-0.018 across all seven cases** -- the measurement
#: that identified the defect as drag rather than a lift-model disagreement.
#:
#: ``concept_regional_jet``'s band is wide, and deliberately so: it **records a
#: known anomaly rather than hiding it**. Its two high-``alpha`` points invert the
#: sign (PHAA +0.0558 at 22.8 deg, ACRL +0.0139 at 19.5 deg) because the strip
#: model's induced drag overshoots the airplane-less-tail polar there. Below
#: 15 deg every case of both fixtures is negative, which
#: :func:`test_the_non_wing_drag_is_a_consistent_parasite_offset` asserts
#: separately -- that is the gate with the physics in it, and it is what a
#: sign-flip regression at ordinary ``alpha`` would trip. (Two lower edges widened
#: by 0.0001 on 2026-08-17 when q went to the exact ``V^2/295.237``, issue #26.)
_DELTA_CD_BAND = {
    'ga6_normal.project.json': (-0.0208, -0.0164),
    'cessna_210.project.json': (-0.0822, -0.0030),
    'atr42_100.project.json': (-0.1519, +0.0221),
    'dhc8_dash8.project.json': (-0.1061, -0.0018),
    'concept_heavy.project.json': (-0.1385, +0.0398),
    'concept_regional_jet.project.json': (-0.0372, +0.0726),
}

#: The trusted-``alpha`` window is **read from its owner**,
#: :data:`sloads.constants.POLAR_TRUSTED_ALPHA_DEG`, through
#: :func:`sloads.modules.balance.polar_alpha_trusted` -- the code decides where a
#: forward non-wing force is clamped and this file decides where one is a
#: defect, and they must be the same window (rule 3). Until 2026-08-17 the test
#: kept its own ``|alpha| <= 15`` and a table of three excused ``NMAA`` points
#: (``atr42_100``, ``dhc8_dash8``, ``concept_heavy``, alpha -12.9 to -14.3 deg)
#: whose forward force the deck nevertheless carried; the window is now
#: one-sided (-10, +15) and those points are outside it and **not applied**
#: (:data:`_CLAMPED_BODY_AXIAL`), so there is nothing left to excuse: inside the
#: window every case is negative, on every fixture, or the fixture's aero data is
#: wrong.


@pytest.mark.parametrize("example", _with_cases())
def test_the_applied_axial_force_is_the_airplanes_drag_not_the_wings(example):
    """G1/G5: ``sum(applied fx) == vn.dx``, exactly, on every flight case.

    The gate that the body drag carrier exists to make true. Before it, the only
    ``fx`` in the assembled model was the wing strips' own chordwise force, so
    ``residual_fx`` *equalled* that sum and the airplane's fuselage, nacelle and
    remaining parasite drag was simply absent.

    Note what is **not** asserted: that the residual is zero. There is no thrust
    in the model and there is not meant to be -- FAR 23's longitudinal load factor
    ``nx`` is exactly this unbalanced axial force, and
    :func:`test_the_longitudinal_closure_is_the_trims_own_drag` is where it is
    accounted for. An earlier draft of this gate asked for zero and was wrong.

    **The one stated exception** (:data:`_CLAMPED_BODY_AXIAL`, D-4 as revised):
    where the non-wing difference came out forward at an ``alpha`` outside the
    polar's trusted window it is not applied, so on that case the applied ``fx``
    is the wing strips' own -- *more* drag than the trim's ``dx``, never less --
    and there is no ``body-axial`` card at all.
    """
    project = _project(example)
    vn = {p.case: p for p in default_envelope(project).vn}
    for case in _flight_cases(project):
        applied = sum(ld.fx for ld in case.loads
                      if not ld.source.startswith("closure-"))
        expected = vn[case.vn_case].dx
        where = f"{example} {case.label}{case.hand}"
        if case.body_axial_clamped:
            strips = sum(ld.fx for ld in case.loads if ld.source == "wing-air")
            assert not [ld for ld in case.loads if ld.source == "body-axial"], where
            assert case.body_axial == 0.0, where
            assert applied == pytest.approx(strips, rel=1e-9, abs=1e-6), (
                f"{where}: clamped, so applied Fx {applied:,.1f} lb should be the "
                f"strips' own {strips:,.1f} lb")
            assert applied > expected, (
                f"{where}: the clamped-away force must have been FORWARD "
                f"(applied {applied:,.1f} lb vs trim dx {expected:,.1f} lb)")
            assert case.residual_fx == pytest.approx(applied, rel=1e-9, abs=1e-6)
            continue
        assert applied == pytest.approx(expected, rel=1e-9, abs=1e-6), (
            f"{where}: applied Fx {applied:,.1f} lb "
            f"against the trim's drag {expected:,.1f} lb")
        assert case.residual_fx == pytest.approx(expected, rel=1e-9, abs=1e-6)


@pytest.mark.parametrize("example", _with_cases())
def test_the_longitudinal_closure_is_the_trims_own_drag(example):
    """G2: ``delta_nx`` is the trim's ``dx/W``, to 1e-9.

    The ``x`` degree of freedom of the closure stands in for thrust, so what it
    reads *should* be the airplane's drag over its weight. Before the body drag
    carrier it was the wing's drag alone -- ``ga6_normal`` PHAA closed at 0.661 g
    against the trim's own 0.610, and the 0.05 g difference was the missing load,
    not a modelling choice.

    On a clamped case (:data:`_CLAMPED_BODY_AXIAL`) it is the strips' own drag
    over the weight instead -- the applied ``fx`` in either case, which is what
    the ``x`` degree of freedom reacts.
    """
    project = _project(example)
    vn = {p.case: p for p in default_envelope(project).vn}
    for case in _flight_cases(project):
        expected = vn[case.vn_case].dx / case.weight_lb
        if case.body_axial_clamped:
            expected = sum(ld.fx for ld in case.loads
                           if not ld.source.startswith("closure-")) / case.weight_lb
        assert case.delta_nx == pytest.approx(expected, rel=1e-9), (
            f"{example} {case.label}{case.hand}: closure nx {case.delta_nx:.5f} "
            f"against the trim's drag {expected:.5f}")


@pytest.mark.parametrize("example", _with_cases())
def test_a_ground_case_carries_no_body_drag(example):
    """G4: the ground families have no aero, so they carry no non-wing drag.

    The same rule that keeps ``fuselage_cm`` at zero there. A ground case's
    longitudinal load is the braked-roll/side-load wheel reaction, which the gear
    family applies itself -- adding an airborne drag term beside it would be a
    load the airplane is not carrying.
    """
    for case in _ground_cases(_project(example)):
        assert case.body_axial == 0.0, f"{case.label}: {case.body_axial} lb"
        assert not [ld for ld in case.loads if ld.source == "body-axial"]


@pytest.mark.parametrize("example", _with_cases())
def test_the_non_wing_drag_is_a_consistent_parasite_offset(example):
    """G10: the ``dCD`` diagnostic, and the physics that gives it bite.

    Carrying the load makes the applied axial resultant equal the trim's ``dx``
    **by construction** (G1), so the residual can no longer report a disagreement
    between the two drag models. This is where that signal lives instead, and it
    is not decoration: it is the measurement that identified the defect.

    Two assertions, and the second is the one with physics in it:

    * every case sits inside its fixture's recorded band
      (:data:`_DELTA_CD_BAND`) -- a regression guard;
    * inside the polar's trusted ``alpha`` window
      (:data:`~sloads.constants.POLAR_TRUSTED_ALPHA_DEG`, read from its owner)
      every case is **negative**, i.e. the wing strips carry strictly less axial
      force than the whole airplane. That is a real statement, not a tautology:
      the polar covers airplane-less-tail and the strips cover the wing, so the
      difference is other components' drag and can only have one sign while both
      models are trusted. There are no excused points (there were three until
      2026-08-17; they are outside the one-sided window now and clamped, see
      :func:`test_a_forward_non_wing_force_outside_the_window_is_not_applied`).

    ``dCD`` is the **unclamped** difference on every case, clamped or not, so
    the band and the sign gate see the same signal they always did.
    """
    project = _project(example)
    vn = {p.case: p for p in default_envelope(project).vn}
    lo, hi = _DELTA_CD_BAND[example]
    trusted = []
    for case in _flight_cases(project):
        where = f"{example} {case.label}{case.hand}"
        assert lo <= case.delta_cd <= hi, (
            f"{where}: dCD {case.delta_cd:+.5f} outside the recorded band "
            f"({lo:+.4f}, {hi:+.4f}) -- see _DELTA_CD_BAND")
        if polar_alpha_trusted(vn[case.vn_case].alpha_deg):
            trusted.append((where, case.delta_cd))
    assert trusted, f"{example}: no case inside the trusted window {POLAR_TRUSTED_ALPHA_DEG}"
    for where, cd in trusted:
        assert cd < 0.0, (
            f"{where}: dCD {cd:+.5f} says the wing strips carry MORE axial force "
            f"than the whole airplane less tail, inside the alpha window "
            f"{POLAR_TRUSTED_ALPHA_DEG} deg where both drag models are trusted "
            f"-- a fixture aero-data defect, not something to excuse")


@pytest.mark.parametrize("example", _with_cases())
def test_a_forward_non_wing_force_outside_the_window_is_not_applied(example):
    """Backlog Pri 2 / design note 20 D-4 as revised 2026-08-17.

    A forward non-wing axial force at a trim ``alpha`` **outside** the polar's
    trusted window is a difference between two drag models where one of them is
    being read outside its fit -- not a load. So on exactly those cases, and no
    others: ``body_axial_clamped`` is set, ``body_axial`` is zero, no
    ``body-axial`` card is written, the unclamped ``dCD`` is still positive and
    reported, and the case note says so. The clamped set is the recorded one
    (:data:`_CLAMPED_BODY_AXIAL`), both ways. A forward value *inside* the
    window is never clamped -- it fails
    :func:`test_the_non_wing_drag_is_a_consistent_parasite_offset` instead.
    """
    project = _project(example)
    vn = {p.case: p for p in default_envelope(project).vn}
    clamped = set()
    for case in _flight_cases(project):
        where = f"{example} {case.label}{case.hand}"
        alpha = vn[case.vn_case].alpha_deg
        if case.body_axial_clamped:
            clamped.add(case.label)
            assert not polar_alpha_trusted(alpha), (
                f"{where}: clamped INSIDE the trusted window at alpha {alpha:+.1f}")
            assert case.delta_cd > 0.0, f"{where}: clamped but dCD {case.delta_cd:+.5f}"
            assert case.body_axial == 0.0, where
            assert not [ld for ld in case.loads if ld.source == "body-axial"], where
            assert any("NOT applied" in n and "trusted window" in n
                       for n in case.notes), f"{where}: no clamp note"
        else:
            assert not (case.delta_cd > 0.0 and not polar_alpha_trusted(alpha)), (
                f"{where}: forward outside the window at alpha {alpha:+.1f} "
                f"but not clamped")
    assert clamped == set(_CLAMPED_BODY_AXIAL.get(example, {})), (
        f"{example}: clamped {sorted(clamped)} vs recorded "
        f"{sorted(_CLAMPED_BODY_AXIAL.get(example, {}))}")


@pytest.mark.parametrize("example", _with_cases())
def test_the_body_drag_waterline_is_stated_and_is_the_only_free_parameter(example):
    """G6/G9: one owner for the waterline, and it is what moves the residual.

    Two halves, and together they are the drift guard ``CLAUDE.md`` practice 3
    asks for on a cross-cutting convention:

    * **provenance** -- an underived waterline is marked ``assumed`` and says so
      in-band, exactly as ``FinRoot`` does for the fin root (decision D-1 follows
      that pattern deliberately);
    * **the owner is the one that is used** -- entering
      ``body_drag_waterline_z`` moves every case's pitch residual by exactly
      ``(z_new - z_cg) * fx``, which is only true if ``assemble`` reads the owner
      rather than a private copy of the same rule.

    The second half also pins the design note's central finding: the residual is
    linear in this height and zero at the wing plane, so a body drag load placed
    at the body's own mass centroid would make the pitch residual **worse**, not
    better. Nothing else about the load can move a gate -- its magnitude is fixed
    by G1 and its fuselage station contributes no pitching moment at all.
    """
    project = _project(example)
    resolved = body_drag_waterline(project)
    assert resolved.assumed is True and resolved.basis == "wing-plane"
    assert resolved.note and "ASSUMED" in resolved.note
    assert resolved.z == pytest.approx(require_wing_reference(project).zw, rel=1e-12)

    before = {(c.label, c.hand): c for c in _flight_cases(project)}
    moved = replace(
        project,
        geometry=replace(project.geometry, parametric=replace(
            project.geometry.parametric,
            body_drag_waterline_z=resolved.z + 10.0)))
    assert body_drag_waterline(moved) == (resolved.z + 10.0, False, "entered", "")

    for case in _flight_cases(moved):
        old = before[(case.label, case.hand)]
        expected = old.residual_my + 10.0 * old.body_axial
        assert case.residual_my == pytest.approx(expected, rel=1e-9, abs=1e-6), (
            f"{example} {case.label}{case.hand}: moving the body drag waterline "
            f"10 in did not move the pitch residual by 10 * {old.body_axial:,.0f} lb")


# --------------------------------------------------------------------------- #
# B3 -- the seam rule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _with_cases())
def test_no_free_body_cut_reaction_is_applied(example):
    """Plan 11 §4: *a load that a free-body cut introduces is never applied in
    the assembled model.*

    The wing carry-through is the seam between two free bodies. The per-component
    fuselage deck applies it because it has cut the wing off; the assembled model
    has not, so its solver recovers it, and applying it as well would react the
    wing twice. Structural (``balance.assemble`` never reads ``body_loads``);
    this is the drift guard.
    """
    for case in build_balanced_cases(_project(example)):
        assert carry_sources_absent(case), f"{example} {case.label}"
        assert not any(ld.source in ("carry", "correction") for ld in case.loads)


# --------------------------------------------------------------------------- #
# B5 -- the assembled deck
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", _with_cases())
@pytest.mark.parametrize("system", _SYSTEMS)
def test_the_deck_balances_from_its_own_cards(example, system):
    """**The acceptance test of the whole step.**

    Re-derive each subcase's resultant from the emitted ``GRID``/``FORCE``/
    ``MOMENT`` text and check it is zero about the CG. Reading the deck rather
    than the objects is what makes this meaningful: the in-memory case closed to
    1e-13 while the deck was out by 3.9-21.9 %, because distinct loads were
    collapsing onto shared nodes. Nothing but the card text would have shown it.

    **All six DOF** (review finding F-G1, closed 2026-08-10). Until then this
    read ``fx``/``fz``/``my`` only, while ``equilibrium.Resultant`` carried the
    lateral three all along -- so the node-collapse failure mode this gate exists
    for could hit a fin ``FORCE`` card or a reflected port-twin node and unbalance
    ``fy``/``mx``/``mz`` with nothing looking. The lateral three are not
    decoration on this deck: from B8a-3 every assembled deck carries eight
    lateral cases, and the handed twins differ *only* in those components.

    Levers, per axis: pitch against the MAC as before, roll and yaw against the
    **semi-span** -- the same lever ``BalancedCaseResult.roll_residual_fraction``
    judges the physics residual by, so the deck gate and the closure report agree
    on what "small" means for a moment.
    """
    p = _project(example)
    cases = build_balanced_cases(p)
    u = deliverable_units(system, Channel.SOLVER)
    grids, _, _, forces, moments = parse_cards(
        balanced_deck(p, system=system, cases=cases))
    for sid, case in zip(case_sids(cases), cases):
        cg = _ref_of(case)
        ref = (cg.xcg * u.length.factor, 0.0, cg.zcg * u.length.factor)
        got = resultant(forces, moments, grids, sid, ref)
        n_w = case.n_w * case.safety_factor * u.force.factor
        n_w_mac = n_w * case.mac * u.length.factor
        n_w_span = n_w * case.semi_span * u.length.factor
        assert n_w_span > 0.0, f"{example}: no semi-span to judge roll/yaw by"
        where = f"{example} {system.value} {case.label}"
        # 1e-5 is the %.6E card format accumulated over ~150 cards, not physics.
        assert abs(got.fx) < 1e-5 * n_w, f"{where} Fx"
        assert abs(got.fy) < 1e-5 * n_w, f"{where} Fy"
        assert abs(got.fz) < 1e-5 * n_w, f"{where} Fz"
        assert abs(got.mx) < 1e-5 * n_w_span, f"{where} Mx"
        assert abs(got.my) < 1e-5 * n_w_mac, f"{where} My"
        assert abs(got.mz) < 1e-5 * n_w_span, f"{where} Mz"


def test_the_lateral_half_of_the_deck_gate_has_teeth():
    """**F-G1's teeth**: reverse one lateral ``FORCE`` card and only ``fy``/``mx``/
    ``mz`` notice.

    A widened gate that passes on the first run proves nothing, so this measures
    what the three DOF it gained can see that the three it had could not. The
    mutation is the review's own failure mode -- a lateral card of the fin family
    with its ``y`` component reversed, which is what a sign error in the
    span-to-waterline map or in the port-twin reflection produces.

    Measured on ``ga6_normal``, as fractions of the gate's own scales: ``fy``
    **0.62 %**, ``mz`` **0.62 %**, ``mx`` **0.041 %** -- against ``fx`` 1e-9,
    ``fz`` 1e-8 and ``my`` 1e-8, all of them comfortably inside the 1e-5
    tolerance. The old gate would have called this deck balanced.

    Those margins were 3.4 / 3.1 / 0.20 % until 2026-08-30, when ga6 entered its
    printed Appendix A fin. The fin is now distributed over 20 spanwise stations
    where the derived rectangle used 10, so reversing **one** card is half the
    share of the total it was -- the mutation is the same size, the deck it hides
    in has twice the cards. The separation that matters is unchanged: the three
    gained DOF still see it five orders of magnitude more clearly than the three
    that were blind to it.
    """
    p = _project("ga6_normal.project.json")
    cases = build_balanced_cases(p)
    index = next(i for i, c in enumerate(cases)
                 if is_lateral(c) and not is_ground(c))
    sid = case_sids(cases)[index]
    case = cases[index]

    lines, hit = [], False
    for line in balanced_deck(p, cases=cases).splitlines():
        f = line.split(",")
        if not hit and line.startswith(f"FORCE, {sid},") and abs(float(f[6])) > 1e-9:
            f[6], hit = f" {-float(f[6]):.6E}", True
            line = ",".join(f)
        lines.append(line)
    assert hit, "no lateral FORCE card to reverse -- the deck format changed"

    cg = _ref_of(case)
    grids, _, _, forces, moments = parse_cards("\n".join(lines) + "\n")
    got = resultant(forces, moments, grids, sid, (cg.xcg, 0.0, cg.zcg))
    n_w = case.n_w * case.safety_factor

    # The three the gate always had: blind to it.
    assert abs(got.fx) < 1e-5 * n_w
    assert abs(got.fz) < 1e-5 * n_w
    assert abs(got.my) < 1e-5 * n_w * case.mac
    # The three it gained: each on its own, by a wide margin.
    assert abs(got.fy) > 5e-3 * n_w, got.fy
    assert abs(got.mx) > 2e-4 * n_w * case.semi_span, got.mx
    assert abs(got.mz) > 5e-3 * n_w * case.semi_span, got.mz


@pytest.mark.parametrize("example", _with_cases())
def test_every_load_has_its_own_node(example):
    """Two loads at different positions never share a GID.

    The bug this pins cost 21.9 % of the deck's balance and was invisible in
    memory: wing air (25 % chord) and wing inertia (item-anchored 50 % chord) at
    one span station were keyed on span alone, and every ballast item -- which has
    no fuselage beam station, the beam being derived from the untouched database
    -- fell through to a shared node.
    """
    p = _project(example)
    cases = build_balanced_cases(p)
    nodes = deck_nodes(cases, p)
    assert len(set(nodes.values())) == len(nodes), "two positions share a GID"


@pytest.mark.parametrize("example", _with_ground_cases())
def test_the_wing_has_two_node_bands(example):
    """Left and right are separate runs -- the first deck in the suite with both.

    Every previous deck carried a single half-span. The split is what lets an
    antisymmetric case (plan 11 B7) load the two sides differently without
    renumbering anything.
    """
    p = _project(example)
    cases = build_balanced_cases(p)
    nodes = deck_nodes(cases, p)
    # A gear reference point is on a side too, but takes its own band (G-2) so
    # G-13's solver assertion can find it by id. Its keys are identified from the
    # cases rather than from the node table, which carries positions only.
    gear_keys = {(ld.side, round(ld.x, 6), round(ld.y, 6), round(ld.z, 6))
                 for c in cases for ld in c.loads if ld.source.startswith("gear-")}
    gear = {g for k, g in nodes.items() if k in gear_keys}
    right = {g for k, g in nodes.items() if k[0] == "R" and k not in gear_keys}
    left = {g for k, g in nodes.items() if k[0] == "L" and k not in gear_keys}
    assert right and left and len(right) == len(left)
    assert all(BALANCED_WING_R_BASE <= g < BALANCED_WING_R_BASE + 200 for g in right)
    assert all(BALANCED_WING_L_BASE <= g < BALANCED_WING_L_BASE + 200 for g in left)
    assert not (right & left)
    # The gear band is disjoint from both, and every gear node is in it: a
    # trunnion is fixed to the airframe, so there is at most one node per leg per
    # side however many attitudes the 24 ground cases are computed in.
    assert gear, f"{example}: no gear reference point in the assembled deck"
    assert all(BALANCED_GEAR_BASE <= g < BALANCED_GEAR_BASE + 100 for g in gear)
    assert not (gear & (right | left))
    assert len(gear) == 3, sorted(gear)   # main starboard, main port, nose


@pytest.mark.parametrize("example", _with_cases())
def test_the_deck_is_determinately_supported(example):
    """One node, six DOF: the reaction *is* the residual, which is the free-free
    proof rather than a modelling convenience."""
    text = balanced_deck(_project(example))
    _, _, spc1, _, _ = parse_cards(text)
    assert len(spc1) == 1
    _, comp, gids = spc1[0]
    assert comp == "123456" and len(gids) == 1
    assert "the reaction IS the residual" in text.replace("its reaction IS the residual",
                                                          "the reaction IS the residual")


@pytest.mark.parametrize("example", _with_cases())
def test_the_deck_states_its_residual_and_its_lumped_moment(example):
    """A deck forwarded on its own must say how much of the balance was computed
    and how much relieved, and that the body ``Cm`` is lumped."""
    text = balanced_deck(_project(example))
    assert "Residual BEFORE closure" in text
    assert "Lumped fuselage Cm moment" in text
    assert "FULL SPAN, free-free" in text


@pytest.mark.parametrize("example", _with_cases())
def test_deck_subcase_ids_are_minted_and_survive_a_dropped_case(example):
    """**D-R7** at deck level: the ``SUBCASE`` a case is written under is its own
    id, and dropping a condition renumbers nothing.

    The positional scheme made the flagship deliverable's case identity a
    property of the export -- one missing V-n point moved every subsequent
    ``SUBCASE`` number, so a solver result could not be read without the run
    that produced it. This drops a case from the middle and asserts the
    survivors keep the numbers they had, which is the property the shipped deck
    now offers a consumer.
    """
    p = _project(example)
    cases = build_balanced_cases(p)
    assert len(cases) > 2, f"{example}: too few cases to drop one from the middle"
    minted = {c.case_ref.case_id: sid
              for sid, c in zip(case_sids(cases), cases) if c.case_ref}
    assert len(minted) == len(cases), f"{example}: a case reached the deck unidentified"

    text = balanced_deck(p, cases=cases)
    for sid, case in zip(case_sids(cases), cases):
        assert f"SUBCASE {sid}\n" in text, \
            f"{example}: {case.label} is not written under its minted id"

    kept = [c for i, c in enumerate(cases) if i != 1]
    after = {c.case_ref.case_id: sid for sid, c in zip(case_sids(kept), kept)}
    assert all(after[cid] == minted[cid] for cid in after), \
        f"{example}: dropping one case renumbered the survivors"


def test_two_cases_with_one_identity_cannot_share_a_subcase():
    """The one failure minting can have, refused rather than merged.

    Positional ids could not collide; minted ones can, if a build hands the same
    ``CaseRef`` and hand to two cases. Sharing a ``SUBCASE`` would silently sum
    two load sets in the solver -- the D-19 class -- so the deck refuses.
    """
    p = _project("ga6_normal.project.json")
    cases = build_balanced_cases(p)
    with pytest.raises(ValueError, match="mint SUBCASE"):
        balanced_deck(p, cases=list(cases) + [cases[0]])


def test_a_project_with_no_balanced_case_refuses_a_deck():
    """A deck with no subcases would read as a clean result rather than an absent
    one.

    The empty project is built here rather than named off a fixture: since Pri 5 /
    D-26 all six assemble, and ``cessna_210`` -- which used to be the one with
    nothing to export -- now produces the full flight and ground families.

    Emptying the discretionary rows is what makes it unproducible: every case
    then needs 12-35 % of the airplane as solved ballast, which is what the
    credibility gate refuses. The CG stations stay physical, so the trim still
    solves and the refusal comes from the loading gate rather than from a
    diverging balance.
    """
    project = _project("cessna_210.project.json")
    project.weight.items = [it for it in project.weight.items
                            if it.kind != MassItemKind.DISCRETIONARY]
    base = sum(it.weight_lb for it in project.weight.items)
    # ``CG4`` *is* the minimum-flight-weight loading, so it survives the cull and
    # would leave one case standing; it goes with the payload it no longer needs.
    project.weight.cg_cases = [c for c in project.weight.cg_cases
                               if c.weight_lb > base + 1.0]
    for case in project.weight.cg_cases:
        case.loading = None
    with pytest.raises(ValueError, match="no balanced case"):
        balanced_deck(project)


# --------------------------------------------------------------------------- #
# B7 -- the antisymmetric cases and the handedness machinery
# --------------------------------------------------------------------------- #
def test_only_acrl_carries_roll():
    """``unbal_moment`` is non-zero on ``ACRL`` alone -- a **measured** finding.

    Plan 11 phase 2 is worded "the antisymmetric wing cases (``ACRL``, ``TORS``)",
    but the handedness of a wing case lives entirely in ``WingLoadCase.unbal_moment``
    (FAR 23.349), and every shipped fixture enters zero for ``TORS``. That is not
    a fixture oversight: a *steady* roll has no unbalanced rolling moment by
    definition -- the aileron moment is balanced by roll damping -- and the
    up-going/down-going aero asymmetry that remains has no spanwise
    representation anywhere in this suite. ``TORS`` is therefore assembled as the
    symmetric case it is.

    Pinned so that a fixture which ever enters a rolling ``TORS`` goes red here
    rather than being assembled symmetrically and quietly meaning nothing.
    """
    assert "TORS" in SYMMETRIC_WING_CONDITIONS
    assert ROLLING_WING_CONDITIONS == ("ACRL",)
    for example in EXAMPLES:
        project = _project(example)
        for case in (project.wing_mass.cases if project.wing_mass else []):
            if case.name == "ACRL":
                continue
            assert case.unbal_moment == 0.0, (
                f"{example} {case.name} carries UNB={case.unbal_moment}: it is "
                "antisymmetric and must not be assembled as a symmetric case")


@pytest.mark.parametrize("example", _with_cases())
def test_the_roll_moment_is_the_applied_couple(example):
    """``residual_mx`` is **exactly** the applied aileron couple, and nothing else.

    Two statements in one: the rolling cases carry ``-UNB`` to machine precision,
    and every other case carries no rolling moment at all. If any other load in
    the assembly had a roll component -- a mirroring slip, an inertia strip on the
    wrong side -- it would land here.

    B8a-3 exempts the **lateral** family, and the exemption is the physics: a fin
    load sits above the roll axis, so ``-Fy*(z - z_cg)`` is a genuine rolling
    moment the case is *supposed* to carry, and it is asserted positively here
    rather than merely excused -- the roll must equal the fin set's own moment
    about the CG, with no contribution from anything else in the assembly.
    """
    project = _project(example)
    for case in _flight_cases(project):
        where = f"{example} {case.label}{case.hand}"
        if is_lateral(case):
            cg = _ref_of(case)
            fin = [ld for ld in case.loads if ld.source == "vtail-air"]
            _, _, _, mx, _, _ = resultant6(fin, (cg.xcg, 0.0, cg.zcg))
            assert case.residual_mx == pytest.approx(mx, rel=1e-12), (
                f"{where}: the pre-closure roll is not the fin load's own moment")
            assert case.unbal_moment == 0.0, where
            continue
        if is_unsymmetrical_htail(case):
            # Same statement for the 23.427(a) family (D-R8): the whole roll of
            # the case must be the h-tail set's own moment about the CG -- the
            # left/right split and nothing else. A mirroring slip in the wing or
            # a strip on the wrong side would land here, exactly as before.
            cg = _ref_of(case)
            ht = [ld for ld in case.loads if ld.source == "htail-air"]
            _, _, _, mx, _, _ = resultant6(ht, (cg.xcg, 0.0, cg.zcg))
            assert case.residual_mx == pytest.approx(mx, rel=1e-12), (
                f"{where}: the pre-closure roll is not the tail split's own moment")
            assert case.unbal_moment == 0.0, where
            continue
        assert case.residual_mx == pytest.approx(-case.unbal_moment, abs=1e-6), where
        if not case.hand:
            assert case.unbal_moment == 0.0, where


#: The share of the aileron's rolling moment the **wing span** reacts, per
#: fixture: ``p_dot(closure) / (Mx / Sum w*y^2)``. Pinned because it is the one
#: number the two roll producers do *not* share, and because it is a physical
#: statement about the airplane rather than a tolerance -- see
#: :func:`test_roll_closure_reproduces_winginer`.
_WING_SPAN_ROLL_SHARE = {
    "ga6_normal.project.json": 0.795230,
    # 0.872612 -> 0.871435 on 2026-08-17 (D-27): the RJ's fuselage masses moved
    # forward and its cabin zones re-spaced, so Sum w*y^2 vs the wing's own
    # share shifted by 0.1 %. Mass layout, not physics.
    # 0.871435 -> 0.871426 on 2026-08-30 with the re-seeded CG cases.
    "concept_regional_jet.project.json": 0.871426,
}


@pytest.mark.parametrize("example", _with_handed_roll())
def test_roll_closure_reproduces_winginer(example):
    """**The B7 closure gate**, as B8a-2 restated it: shape exactly, magnitude pinned.

    Concept mode has no printed oracle, so a stated closure gate against an
    *independent producer* stands in for one (``CLAUDE.md`` practice 2). Here the
    two producers are as independent as the codebase allows: WINGINER's
    ``fz_r``/``iwxx`` recurrence, which is oracle-locked FAR 23 code untouched by
    this step, and the balance layer's roll-acceleration solve, which knows
    nothing about it and closes a residual it computed itself.

    **What B8a-2 changed, and why it is not a weakening.** Through B7 this was an
    equality: the closure's roll strips *were* ``ur*fz_r``, ratio 1.000000. That
    held because the roll DOF solved on ``Sum w*y^2``, and every mass in every
    fixture's database sits at ``y = 0``, so the wing span was the airplane's
    entire roll inertia by construction. The full d'Alembert field (decision L-2)
    ends that: a mass **above** the roll axis is thrown sideways by a roll
    acceleration, so ``Sum w*dz^2`` joins the roll inertia -- on
    ``concept_regional_jet`` it is +30 % of ``Sum w*y^2`` on its own -- and each
    item's entered self-``Ixx`` joins it too (decision L-3). The airplane
    therefore reacts about a fifth of the aileron moment somewhere other than the
    wing span, and WINGINER's wing-only model has no counterpart to that.

    So the gate asserts the two halves separately, which is strictly more than
    the equality did:

    * **shape** -- ``fz / (ur*fz_r)`` is the *same constant* on every strip, to
      1e-9. This is the whole of what WINGINER's distribution says, and it is
      untouched: the relief is still exactly ``-w*p_dot*y``;
    * **magnitude** -- that constant is the wing span's share of the roll
      moment, pinned per fixture (:data:`_WING_SPAN_ROLL_SHARE`), and it equals
      ``p_dot / (Mx / Sum w*y^2)`` by construction. It goes red if the roll
      inertia model drifts, which the old equality could not see at all.
    """
    project = _project(example)
    wm = project.wing_mass
    geom = project.geometry.by_name(wm.surface)
    u = inertia_units(geom, wm, *wing_plane(project, wm.surface))
    winginer = {round(y, 6): f for y, f in zip(u.ye, u.fz_r) if f}

    # ``hand == "R"`` no longer means "rolling": from B8a-3 the lateral family is
    # handed too. Selected on the condition, which is what the check is about.
    rolling = [c for c in build_balanced_cases(project)
               if c.hand == "R" and c.label in ROLLING_WING_CONDITIONS]
    assert rolling, f"{example}: no rolling case to check"
    for case in rolling:
        ur = case.unbal_moment / 100000.0
        strips = [ld for ld in case.loads
                  if ld.source == "closure-roll" and ld.y > 0
                  and round(ld.y, 6) in winginer]
        assert len(strips) >= 5, f"{example}: only {len(strips)} strips matched"

        ratios = [ld.fz / (ur * winginer[round(ld.y, 6)]) for ld in strips]
        for ld, got in zip(strips, ratios):
            assert got == pytest.approx(ratios[0], rel=1e-9), (
                f"{example} {case.label} strip y={ld.y}: the roll relief is no "
                f"longer WINGINER's shape -- ratio {got} against {ratios[0]}")

        share = _WING_SPAN_ROLL_SHARE[example]
        assert ratios[0] == pytest.approx(share, rel=1e-5), (
            f"{example} {case.label}: the wing span now reacts {ratios[0]:.6f} "
            f"of the aileron rolling moment, not the pinned {share}")

        # ...and that constant IS the roll-inertia ratio, not a fitted number.
        masses = [ld for ld in case.loads if ld.weight_lb]
        span_only = sum(ld.weight_lb * ld.y ** 2 for ld in masses)
        assert ratios[0] == pytest.approx(
            case.p_dot / (case.residual_mx / span_only), rel=1e-9), (
            f"{example} {case.label}: the magnitude ratio does not equal the "
            "wing-span share of the assembled roll inertia")


# --------------------------------------------------------------------------- #
# The B8a-2 gates (plan 13 §7): G1, G4, G5, G6
# --------------------------------------------------------------------------- #
def _oeo_history(project):
    """``(CaseInputs, [HistoryRow])`` of the first one-engine-out speed case.

    ``None`` when the project enters no such case at all. **Every number here is
    now the fixture's own.** Until 2026-08-13 this supplied a synthetic 2000 hp,
    because no shipped fixture entered engine horsepower and ONENGOUT could not
    execute on any of them; ``atr42_100`` and ``dhc8_dash8`` carry their
    certificated ratings since, so the injection is gone and G1 reads a history
    built entirely from fixture data. (The identity under test never depended on
    it -- ``psi_2dot = Mz / Izz`` is about the operator and holds at every step of
    any history -- but a gate that feeds itself an input is one an unrelated data
    change can quietly hollow out.)
    """
    oeo = project.one_engine_out
    if oeo is None or not project.engines:
        return None
    try:
        cases = one_engine_out._load_cases(project, oeo)
        if not cases:
            return None
        inputs = one_engine_out._case_inputs(project, cases[0].v_hi_kt)
        rows, _ = one_engine_out.simulate(inputs)
    except (MissingInputError, ValueError):
        return None
    return inputs, rows



#: Which fixtures carry a one-engine-out case, and so can serve as G1's
#: independent producer. Pinned, and deliberately **disjoint** from
#: :func:`_with_cases`: the two fixtures that assemble balanced cases enter no
#: ``one_engine_out`` slice, and the two that enter one assemble no balanced
#: case. That is why G1 is stated as an identity on the *solve* rather than on a
#: case -- the two producers do not meet on any single fixture, and a gate
#: parametrised over the balanced-case fixtures would have skipped itself into
#: vacuity on every run.
_WITH_ONE_ENGINE_OUT = ("atr42_100.project.json", "dhc8_dash8.project.json")


def test_g1_has_a_producer_to_check_against():
    """The vacuity guard for :func:`test_the_yaw_dof_reproduces_onengout`."""
    got = tuple(e for e in EXAMPLES if _oeo_history(_project(e)) is not None)
    assert got == _WITH_ONE_ENGINE_OUT, got


@pytest.mark.parametrize("example", _WITH_ONE_ENGINE_OUT)
def test_the_yaw_dof_reproduces_onengout(example):
    """**G1.** The closure's yaw solve is ``psi_2dot = Mz / Izz`` -- ONENGOUT's.

    B8a-2's counterpart to the B7 roll gate, and the stronger of the two,
    because the other producer here is **oracle-locked FAR 23 code**:
    ``ONENGOUT.BAS`` 282-286 (Ref 1 Ch 11 p87-88, FAR 23.367) integrates
    ``THETA2DOT = MOM/12/IZZ*57.3`` and knows nothing whatever about balanced
    cases. The yaw degree of freedom is new at B8a-2 and has no other check.

    Run against the module's **own time history** rather than a re-derived
    formula, so the comparison is with what ONENGOUT actually computes at each
    step, at that step's own moment. Both sides read the one deg/rad owner
    (``constants.DEG_PER_RAD``; ONENGOUT's 57.3 was retired 2026-08-17) -- the
    identity under test is the physics ``M/(12*Izz)``, not a radian's rounding.
    """
    inputs, history = _oeo_history(_project(example))
    # ONENGOUT is a single-DOF yaw model with no products of inertia, so the
    # tensor to compare against is diagonal. ``ixx``/``iyy`` are filled only to
    # keep it invertible -- with every product of inertia zero the yaw row
    # decouples exactly, and their values cannot reach the answer.
    izz = inputs.izz * LBIN2_PER_SLUGFT2
    tensor = InertiaTensor(ixx=izz, iyy=izz, izz=izz)
    checked = 0
    for row in history:
        if not row.moment:
            continue
        omega_dot = tensor.solve((0.0, 0.0, row.moment))
        got = radians_per_s2(omega_dot)[2] * DEG_PER_RAD
        assert got == pytest.approx(row.theta_2dot, rel=1e-12), (
            f"{example} t={row.time}: closure {got} vs ONENGOUT {row.theta_2dot}")
        checked += 1
    assert checked > 10, f"{example}: only {checked} steps compared"


#: ``Izz`` of the assembled closure tensor, slug-ft^2, per fixture and loading.
#: **G4**, and it is an equality rather than a comparison: with decision L-3
#: answered, ``Izz(closure)`` must equal ``Izz(WTONECG) - wing self-Izz +
#: Sum w*y^2(WINGINER spread)`` -- the same airplane from two producers that
#: share no code. Pinned as well as reconciled, because a reconciliation that
#: drifted on both sides at once would still balance.
_CLOSURE_IZZ = {
    'ga6_normal.project.json': {'CG2': 2933.5, 'CG3': 2534.2, 'CG1': 2992.1, 'CG4': 2424.1},
    'cessna_210.project.json': {'fwd gross': 2724.5, 'min weight': 2646.9, 'aft gross': 3097.3, 'fwd regardless': 2735.7},
    # The three fuel-in-wing fixtures moved on 2026-08-17 (design note 29): the
    # wing-tank fuel left the centreline lump for WINGINER's spanwise spread, so
    # Izz gained its Sum w*y^2 -- +33 % / +31 % / +29 %. Physics, not drift.
    'atr42_100.project.json': {'fwd gross': 197124.6, 'aft gross': 204234.6},
    'dhc8_dash8.project.json': {'fwd gross': 276188.3, 'min weight': 184928.0, 'aft gross': 269576.3, 'fwd regardless': 261441.6},
    'concept_heavy.project.json': {'CGmax': 32302.1},
#: The RJ's three moved on 2026-08-30: its CG cases were re-seeded to the
#: WTENV limits the closed-form planform integral now gives (the stations
#: shifted ~0.05 in), and Izz follows the CG.
    'concept_regional_jet.project.json': {'fwd gross': 254256.5, 'min weight': 196104.9, 'aft gross': 255823.4},
}


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_izz_is_pinned_and_reconciles(example):
    """**G4.** Three producers give three ``Izz`` for one airplane; pin the one
    that reacts the load, and show it is the others' identity.

    Plan 13 §3.4 measured the spread and it is not noise: ``select._default_izz``
    (Ch 9) gives ``ga6_normal`` 4169, ``WTONECG`` gives 3023, and the assembled
    mass set gives 2934. Two of those are printed in Appendix A, side by side,
    38 % apart. The mitigation (risk R5) is that the case reports which one
    reacted its load -- so this asserts that number, and that it is reachable
    from the deliverable rather than only from a scratch script.
    """
    for case in _flight_cases(_project(example)):
        want = _CLOSURE_IZZ[example][case.cg]
        got = case.closure_inertia.izz / LBIN2_PER_SLUGFT2
        assert got == pytest.approx(want, rel=1e-4), (
            f"{example} {case.label} {case.cg}: Izz(closure) {got:.1f} "
            f"against the pinned {want}")
        # The tensor is the assembled model's, not a re-derivation: it must be
        # positive-definite in the obvious sense and carry the Ixz coupling.
        assert case.closure_inertia.ixx > 0 and case.closure_inertia.iyy > 0
        assert case.closure_inertia.ixz != 0.0
        assert case.closure_inertia.ixy == pytest.approx(0.0, abs=1e-6), (
            f"{example} {case.label}: the mass model is not mirror-symmetric")


@pytest.mark.parametrize("example", _with_cases())
def test_a_symmetric_case_reduces_to_three_dof(example):
    """**G5.** The 6-DOF closure on a symmetric case is the 3-DOF one it replaced.

    The reduction that makes B8a-2 a superset rather than a change: with no
    lateral applied load, the lateral three solve to zero and the deck carries
    the same physics it did before -- ``n_x``/``n_z`` identical by construction
    (they are still ``F/W``), and the pitch DOF still reacting the whole
    ``My`` residual.

    What did **not** stay identical, and is asserted rather than glossed:
    ``q_dot`` is no longer ``My / Sum w*dx^2``. The pitch inertia became a real
    ``Iyy`` -- it gained ``Sum w*dz^2`` and the non-wing self-inertia -- so
    ``q_dot`` fell 18-22 % on ``ga6_normal`` and 3-4 % on the regional jet. The
    *deck* barely moved, because the pitch relief is only 0.06-0.56 % of a peak
    node load, but the reported acceleration did, and it moved towards the
    truth.
    """
    project = _project(example)
    for case in _flight_cases(project):
        if case.hand:
            continue
        where = f"{example} {case.label}"
        cg = _ref_of(case)
        masses = [ld for ld in case.loads if ld.weight_lb]
        w_total = sum(ld.weight_lb for ld in masses)

        # The translational three are unchanged: still F/W, exactly.
        assert case.delta_n == pytest.approx(case.residual_fz / w_total, rel=1e-12)
        assert case.delta_nx == pytest.approx(case.residual_fx / w_total, rel=1e-12)
        assert case.delta_ny == 0.0, where

        # Pitch reacts the whole My residual, through the real Iyy -- about the
        # **mass centroid**, which is where the relief field is exact. The
        # reported residual is stated about the entered CG (D-R8), so the
        # transfer ``M_c = M_cg + (cg - c) x F`` belongs in the identity rather
        # than in a tolerance: it is identically zero on a loading whose ballast
        # was solved from the CG, and non-zero (0.0008 in on the RJ's entered
        # CG3, 0.0024 in on ga6's CG4) whenever the loading is a real one that
        # lands near its case instead of on it.
        cxx = sum(ld.weight_lb * ld.x for ld in masses) / w_total
        czz = sum(ld.weight_lb * ld.z for ld in masses) / w_total
        my_c = (case.residual_my + (cg.zcg - czz) * case.residual_fx
                - (cg.xcg - cxx) * case.residual_fz)
        assert case.q_dot == pytest.approx(
            my_c / case.closure_inertia.iyy, rel=1e-9), where
        # ...which is strictly larger than the Sum w*dx^2 the 3-DOF closure used.
        old_j = sum(ld.weight_lb * (ld.x - cg.xcg) ** 2 for ld in masses)
        assert case.closure_inertia.iyy > old_j, where
        assert abs(case.q_dot) < abs(case.residual_my / old_j), where


#: What ``ACRL`` gained at B8a-2, per fixture: the peak nodal companion side
#: force the roll field applies, and the yaw acceleration ``Ixz`` induces from
#: it, in deg/s^2. **G6** -- the one shipped case whose *physics* L-2 changes,
#: so the change is asserted rather than re-baselined (risk R1).
_ACRL_LATERAL = {
    'ga6_normal.project.json': {"companion_fy_lb": 89.83, "r_dot_deg_s2": 18.930},
    'concept_regional_jet.project.json': {"companion_fy_lb": 307.46, "r_dot_deg_s2": 4.394},
}


@pytest.mark.parametrize("example", _with_handed_roll())
def test_acrl_gained_the_companion_field_and_an_induced_yaw(example):
    """**G6.** A rolling airplane with non-zero ``Ixz`` yaws, and throws mass sideways.

    Both are new at B8a-2 and both are real physics the shipped model could not
    express. The companion ``fy = +w*p_dot*dz`` is *larger* than the roll term
    already in the deck, because ``fz = -w*p_dot*dy`` reaches only the wing
    strips -- every item in every fixture's database sits at ``y = 0`` -- while
    the companion reaches every mass off the roll axis.

    The net side force it adds must be **zero**: it is a d'Alembert reaction to
    an angular acceleration, not a side load, and if it netted anything the case
    would be applying a lateral force nothing asked for.
    """
    want = _ACRL_LATERAL[example]
    rolling = [c for c in build_balanced_cases(_project(example))
               if c.hand == "R" and c.label in ROLLING_WING_CONDITIONS]
    assert rolling, f"{example}: no rolling case"
    for case in rolling:
        roll = [ld for ld in case.loads if ld.source == "closure-roll"]
        assert roll, f"{example}: no roll relief"
        peak = max(abs(ld.fy) for ld in roll)
        assert peak == pytest.approx(want["companion_fy_lb"], rel=1e-3), (
            f"{example} {case.label}: companion peak fy {peak:.1f} lb")
        assert sum(ld.fy for ld in roll) == pytest.approx(
            0.0, abs=1e-9 * case.weight_lb), (
            f"{example} {case.label}: the companion field nets a side force")

        r_dot = math.degrees(radians_per_s2((0.0, 0.0, case.r_dot))[2])
        assert r_dot == pytest.approx(want["r_dot_deg_s2"], rel=1e-3), (
            f"{example} {case.label}: induced yaw {r_dot:.3f} deg/s^2")
        # It is Ixz that induces it -- zero the coupling and the yaw goes away.
        assert case.closure_inertia.ixz != 0.0
        uncoupled = replace(case.closure_inertia, ixz=0.0, ixy=0.0, iyz=0.0)
        assert uncoupled.solve(
            (case.residual_mx, case.residual_my, case.residual_mz))[2] == \
            pytest.approx(0.0, abs=abs(case.r_dot) * 1e-3)


@pytest.mark.parametrize("example", _with_cases())
def test_the_case_closes_in_all_six_dof(example):
    """After relief, all six rigid-body components are zero to machine precision.

    The three symmetric DOF were already gated at B2; roll is the one B7 adds, and
    it is the one an antisymmetric case fails silently without -- ``ACRL``
    assembled with no roll term closes ``Fx``/``Fz``/``My`` to 1e-11 while
    carrying a whole unreacted aileron couple.
    """
    project = _project(example)
    for case in build_balanced_cases(project):
        cg = _ref_of(case)
        fx, fy, fz, mx, my, mz = resultant6(case.loads, (cg.xcg, 0.0, cg.zcg))
        where = f"{example} {case.label}{case.hand}"
        scale = case.n_w
        assert abs(fx) < 1e-6 * scale, f"{where} Fx"
        assert abs(fy) < 1e-6 * scale, f"{where} Fy"
        assert abs(fz) < 1e-6 * scale, f"{where} Fz"
        assert abs(mx) < 1e-6 * scale * case.semi_span, f"{where} Mx"
        assert abs(my) < 1e-6 * scale * case.mac, f"{where} My"
        assert abs(mz) < 1e-6 * scale * case.semi_span, f"{where} Mz"


@pytest.mark.parametrize("example", _with_cases())
def test_the_lateral_dof_are_untouched(example):
    """No **applied** load in the symmetric families has a side component (**G5**).

    ``Fy``/``Mz`` are computed rather than assumed so B8a's lateral cases inherit
    a complete resultant; this pins that today no applied load creates one, which
    is what makes the roll check above unambiguous.

    B8a-2 split the statement in two, because a rolling case now *does* carry a
    lateral relief field (``fy = +w*p_dot*dz``, decision L-2) -- real physics, and
    the point of the step. What stays absolutely true is the **applied** set, and
    what stays true of a **symmetric** case is that its lateral relief is
    float-cancellation noise rather than load: ``residual_mx``/``residual_mz`` on
    a mirror-symmetric mass model are zero up to summation order, so the solve
    returns ~1e-18 rad-equivalents and the relief it produces is fifteen orders
    below a card the deck would even print. Bounded rather than asserted exactly
    zero, because rounding the residual to zero to make the claim exact would be
    a rounding dressed as physics.

    B8a-3 scopes it to the **symmetric and rolling** families, which is what it
    always meant: the lateral family exists precisely to apply a side load, and
    its own statement of the same kind is
    :func:`test_the_symmetric_half_of_a_lateral_case_still_closes` -- strip the
    fin set out and this claim holds again, to the last digit.
    """
    for case in _flight_cases(_project(example)):
        if is_lateral(case):
            continue
        applied = [ld for ld in case.loads if not ld.source.startswith("closure-")]
        assert all(ld.fy == 0.0 and ld.mz == 0.0 for ld in applied), case.label
        assert case.residual_fy == 0.0, case.label
        assert abs(case.residual_mz) < 1e-6 * case.n_w * case.semi_span, case.label
        if case.hand:
            continue
        # A symmetric case: the lateral DOF close on noise, not on load.
        assert case.delta_ny == 0.0, case.label
        lateral = max(max(abs(ld.fy), abs(ld.mz)) for ld in case.loads)
        assert lateral < 1e-9 * case.n_w, f"{case.label}: {lateral} lb of side load"


# --------------------------------------------------------------------------- #
# The B8a-3 gates (plan 13 §7): G9, G10, and the L-6 predicate
# --------------------------------------------------------------------------- #
#: **G10.** What each lateral case *is*, per fixture: the net applied fin side
#: load (lb), the lateral load factor it produces (g), and the yaw and roll
#: accelerations (deg/s^2). Four numbers per condition, pinned in both
#: directions -- these are the whole answer of a rudder or gust case, and there
#: is no printed oracle for any of them, so a stated measurement is the gate
#: (``CLAUDE.md`` practice 2).
#:
#: Three of them are *not* free parameters and are asserted structurally as well
#: as pinned: ``n_y`` is ``L_v / W`` exactly (the ``Sum Fy = 0`` of plan 13 §2),
#: the yaw follows from the same ``Izz``/``Ixz`` tensor B8a-2 pinned, and the
#: roll is the fin's own moment about the CG (asserted in
#: :func:`test_the_roll_moment_is_the_applied_couple`). The fin loads themselves
#: are SELECT's, unchanged -- see :func:`sloads.modules.balance.fin_sets`.
#:
#: The yaw figures are **not** those of plan 13 §3.1: those were measured against
#: the placement-only ``Izz`` that preceded L-3. Against the shipped tensor
#: ga6 ``SUDDEN RUDDER`` is 178.05 deg/s^2 rather than 205.7 -- a ratio of 0.866
#: where the ``Izz`` ratio alone would give 0.886, the difference being the
#: ``Ixz`` coupling. Plan 13 §7 is amended to these.
_LATERAL_CASE_NUMBERS = {
    # Re-pinned 2026-08-30: ga6 entered its printed Appendix A fin, and the
    # planform integral went closed-form. Two effects, and they are different
    # sizes, which is how they can be told apart. The **lever** moved a lot: the
    # entered fin's load centroid sits 2.11 in below the derived rectangle's
    # half-span, so the roll arm (z - z_cg) fell 14.00 -> 11.89 in and p_dot
    # with it, -20.16 -> -14.93 deg/s^2 on SIDE GUST (-26 %). The **aero** moved
    # barely at all: the fin loads and Ny shift by at most 0.012 % (SUDDEN
    # RUDDER 585.7113 -> 585.6409), which is the wing MAC's 0.042 % reaching the
    # sideslip through the balance. r_dot carries both through the Ixz coupling.
    'ga6_normal.project.json': {
        'SIDE GUST': (603.9910, +0.177644, +185.862912, -14.925045),
        'SUDDEN RUDDER': (585.6409, +0.172247, +179.065785, -6.887951),
        'YAW 15 NEUTRAL': (-525.6850, -0.154613, -152.266518, +7.196692),
        'YAW TO SIDESLIP': (-97.7496, -0.028750, -18.880689, +2.467749),
    },
    # The three fixtures with a published fuselage outline (T-8a). Backlog Pri 1
    # gave the "fuselage-top" branch of fin_root_waterline its body datum --
    # z_centre(xv25) + height(xv25)/2 in place of the wing root plus half the
    # *maximum* body height -- which on these high-wing types brought the fin
    # root back DOWN (atr42 223.15 -> 191.17 in; see test_tail_geometry's
    # _FIN_ROOT), so the fin's roll arm (z - z_cg) shrank and p_dot with it;
    # r_dot moves a little through the Ixz coupling. The fin LOAD and Ny are
    # untouched, which is the check that this moved a lever arm and not the
    # aerodynamics.
    # Pri 1, the fixture-data pass (2026-08-17): these four fixtures' fins are
    # now ENTERED tapered, swept planforms (taper 0.45-0.7, LE sweep 30-35 deg,
    # estimated from the type three-view; ga6 stays derived). The fin LOAD and
    # Ny are bit-identical -- the strips are normalised by their own quadrature
    # area now, so an entered polyline cannot move SELECT's total -- while
    # p_dot fell 6-10 % (a tapered fin's load centroid sits lower, so the roll
    # arm about the CG shrinks) and r_dot moved < 1 % (the swept fin's load
    # centroid moves aft a little). Both are the taper doing what taper does,
    # and the load/Ny identity is the check that only lever arms moved.
    'cessna_210.project.json': {
        'SIDE GUST': (555.7869, +0.146260, +183.2345, -54.8133),
        'SUDDEN RUDDER': (553.1178, +0.145557, +161.4395, -52.9215),
        'YAW 15 NEUTRAL': (-529.0494, -0.139224, -146.5050, +51.1365),
        'YAW TO SIDESLIP': (-134.6463, -0.035433, -29.0171, +13.5560),
    },
    # The twins' r_dot / p_dot fell on 2026-08-17 (design note 29): their
    # wing-tank fuel now spreads along the span, so Izz and Ixx grew (+33 % /
    # +31 % Izz) and the same fin load turns the airplane more slowly. Fin load
    # and Ny are untouched -- the check that this moved inertia, not aero.
    'atr42_100.project.json': {
        'SIDE GUST': (4139.6916, +0.112440, +43.0761, -13.9735),
        'SUDDEN RUDDER': (4288.1132, +0.116471, +43.6751, -14.5046),
        'YAW 15 NEUTRAL': (-4878.1324, -0.132497, -47.3004, +16.5760),
        'YAW TO SIDESLIP': (-2053.4588, -0.055775, -17.8155, +7.0442),
    },
    'dhc8_dash8.project.json': {
        'SIDE GUST': (4527.1258, +0.131221, +32.8181, -12.5184),
        'SUDDEN RUDDER': (3491.5168, +0.101203, +26.2773, -9.9271),
        'YAW 15 NEUTRAL': (-3937.1072, -0.114119, -28.1137, +11.2348),
        'YAW TO SIDESLIP': (-1626.7225, -0.047151, -10.2705, +4.6782),
    },
    # Re-seeded CG cases (2026-08-30) move the RJ's yaw and roll by ~0.04 %;
    # the fin loads and Ny are unchanged, so this is the CG station moving and
    # not the aerodynamics.
    'concept_regional_jet.project.json': {
        'SIDE GUST': (7082.5380, +0.214622, +54.746975, -61.475670),
        'SUDDEN RUDDER': (6907.5333, +0.209319, +54.207528, -59.659156),
        'YAW 15 NEUTRAL': (-8042.9389, -0.243725, -58.674365, +71.160684),
        'YAW TO SIDESLIP': (-3548.2873, -0.107524, -22.069147, +32.849733),
    },
}


@pytest.mark.parametrize("example", _with_lateral_cases())
def test_the_lateral_cases_are_pinned(example):
    """**G10.** Every lateral case's applied load and the motion it causes.

    The starboard case is the computed one; the port twin is its mirror and is
    checked as such by :func:`test_the_handed_twins_are_mirror_images`, so the
    pins are stated once.
    """
    want = _LATERAL_CASE_NUMBERS[example]
    got = {c.label: c for c in build_balanced_cases(_project(example))
           if is_lateral(c) and c.hand == "R"}
    assert sorted(got) == sorted(want), f"{example}: {sorted(got)}"
    assert sorted(got) == sorted(BALANCED_VTAIL_CONDITIONS), example

    for label, (fin, ny, r_dot, p_dot) in want.items():
        case = got[label]
        where = f"{example} {label}"
        assert fin_load(case) == pytest.approx(fin, rel=1e-4), (
            f"{where}: fin side load {fin_load(case):.4f} lb")
        assert case.delta_ny == pytest.approx(ny, rel=1e-4), (
            f"{where}: Ny {case.delta_ny:+.6f} g")
        # ...and Ny is not a fitted number: it is Sum Fy = 0, i.e. L_v / W.
        assert case.delta_ny == pytest.approx(
            fin_load(case) / case.weight_lb, rel=1e-12), where

        got_p, _, got_r = (math.degrees(v) for v in
                           radians_per_s2((case.p_dot, case.q_dot, case.r_dot)))
        assert got_r == pytest.approx(r_dot, rel=1e-4), (
            f"{where}: yaw acceleration {got_r:+.4f} deg/s^2")
        assert got_p == pytest.approx(p_dot, rel=1e-4), (
            f"{where}: roll acceleration {got_p:+.4f} deg/s^2")


@pytest.mark.parametrize("example", _with_lateral_cases())
def test_the_applied_fin_set_is_air_only_so_the_mass_is_applied_once(example):
    """The fin's mass enters an assembled case **once**, in the closure field.

    Since the tail-mass SSOT step the per-condition fin deck carries its own
    lateral inertia (``-n_y*W_vt``), so ``WingStationLoad.fz`` is a *net* load
    there. An assembled case must still apply the applied-aerodynamic set air
    only, because it accounts for the fin's mass separately through the
    ``VTAIL``-tagged items — reading the net would relieve the side load with a
    mass it is also carrying in the closure field.

    Asserted against SELECT's own totals, which no part of the assembly touches:
    Σ applied fin ``fy`` must be the condition's ``LT25+LT50`` exactly, not the
    ``(1 − W_vt/W)`` fraction of it the fin deck reports. Caught here in the
    first place only by a pinned number, which is why it now has a gate that says
    what it means.
    """
    project = _project(example)
    spans = {r.case: r for r in build_tail_span(project)[VTAIL]}
    for case in build_balanced_cases(project):
        if not is_lateral(case) or case.hand != "R":
            continue
        span = spans[case.label]
        assert fin_load(case) == pytest.approx(span.air_total, rel=1e-12), (
            f"{example} {case.label}: the applied fin set is not air only -- "
            f"{fin_load(case):.4f} lb against SELECT's {span.air_total:.4f} lb")
        # And the deck the fin is sized from *does* carry the inertia, so the two
        # differ by exactly the mass ratio. Both statements have to hold at once.
        if span.inertia_modelled and span.case_weight_lb:
            net = sum(st.fz for st in span.stations)
            assert net == pytest.approx(
                span.air_total * (1.0 - span.surface_weight_lb / span.case_weight_lb),
                rel=1e-12), f"{example} {case.label}"


@pytest.mark.parametrize("example", _with_lateral_cases())
def test_the_symmetric_half_of_a_lateral_case_still_closes(example):
    """**G9.** The residual gate that *does* apply to a lateral case.

    Plan 11's 1 % residual gate is meaningless laterally by construction:
    ``residual_fy``/``residual_mz`` before closure **are** the fin load in full,
    because nothing in an airplane balances a rudder kick -- it yaws, and the
    closure is that yaw. (The same standing ``ACRL``'s roll residual has had
    since B7.) Gating them would either be vacuous or force a fictitious
    balancing load into the case.

    What must still hold is that adding the fin set broke nothing in the half
    that *does* balance: strip the ``vtail-air`` loads out and the symmetric
    residual is unchanged to the last digit -- which it is *exactly*, and for a
    reason worth stating: the fin set carries ``fy`` and ``mz`` only, so it
    cannot contribute to ``Fx``/``Fz``/``My`` at all. Asserted rather than
    argued, because a frame-map slip -- the fin's normal force landing back on
    ``fz`` -- is precisely the error that would break it, and it would break it
    silently.
    """
    project = _project(example)
    lateral = [c for c in build_balanced_cases(project) if is_lateral(c)]
    assert lateral, f"{example}: no lateral case"
    for case in lateral:
        cg = _ref_of(case)
        where = f"{example} {case.label}{case.hand}"
        applied = [ld for ld in case.loads
                   if not ld.source.startswith("closure-")]
        half = [ld for ld in applied if ld.source != "vtail-air"]
        fx, fy, fz, mx, my, mz = resultant6(half, (cg.xcg, 0.0, cg.zcg))

        assert fx == pytest.approx(case.residual_fx, rel=1e-12), f"{where} Fx"
        assert fz == pytest.approx(case.residual_fz, rel=1e-12), f"{where} Fz"
        assert my == pytest.approx(case.residual_my, rel=1e-12), f"{where} My"
        # The symmetric half is symmetric: no side force, and its roll and yaw
        # are summation noise rather than load.
        assert fy == 0.0, f"{where}: the symmetric half carries {fy} lb of Fy"
        assert abs(mx) < 1e-9 * case.n_w * case.semi_span, f"{where} Mx"
        assert abs(mz) < 1e-9 * case.n_w * case.semi_span, f"{where} Mz"

        # ...and the lateral residual IS the fin load, not a balance error.
        assert case.residual_fy == pytest.approx(fin_load(case), rel=1e-12), where


# --------------------------------------------------------------------------- #
# The D-R8 gates: the 23.427(a) unsymmetrical h-tail family
# --------------------------------------------------------------------------- #
#: What SELECT gives the 23.427(a) case, per fixture: ``(RH, LH, total)`` in lb
#: and the ``pc`` split percent. **Read from SELECT, never recomputed here** --
#: pinned so a change in the oracle-locked search shows up as a change in the
#: assembled deliverable rather than passing through it unremarked. (Re-pinned
#: 2026-08-17, issue #26: SELECT's 57.3 / 32.2 / 295 went to the exact owners in
#: ``constants``; <= 0.08 % per value, register line in 02_approved_corrections.)
#: Re-pinned 2026-08-30: closed-form planform integration (register line in
#: 02_approved_corrections). The wing MAC and area move by 0.042 % and 0.019 %,
#: and the fin side load with them -- 0.019 % on ga6, 0.0007 % on the C210,
#: 0.0005 % on the Dash 8. The ATR42 and the RJ do not move at all: their
#: planforms integrate to the same numbers either way.
_UNSYMMETRICAL_SPLIT = {
    'ga6_normal.project.json': (-700.2880318468195, -504.20738292971004, 72.0),
    'cessna_210.project.json': (-687.2978354106667, -494.85444149568, 72.0),
    'atr42_100.project.json': (3464.295823974718, 2771.436659179775, 80.0),
    'dhc8_dash8.project.json': (-3302.095528143376, -2641.6764225147012, 80.0),
    'concept_regional_jet.project.json': (6076.817597362804, 4861.454077890244, 80.0),
}


def _unsymmetrical(project):
    return [c for c in build_balanced_cases(project) if is_unsymmetrical_htail(c)]


@pytest.mark.parametrize("example", _with_unsymmetrical_cases())
def test_the_unsymmetrical_case_carries_selects_own_split(example):
    """**The D-R8 composition gate.** The applied tail load *is* SELECT's.

    Two producers, one answer, and that is the whole point of the branch: SELECT
    picks the governing symmetric tail load and splits it 100 % / ``pc`` %
    (oracle-locked, an approved deviation of record), and the assembly's job is
    to distribute that -- not to re-derive it. So each half of the applied set
    must sum to SELECT's own ``RH``/``LH`` to the last digit, and the port twin
    must be the same two numbers **swapped**, which is what makes the pair the
    "either side" of 23.427(a) rather than one case printed twice.
    """
    project = _project(example)
    rh_want, lh_want, pc = _UNSYMMETRICAL_SPLIT[example]
    cases = _unsymmetrical(project)
    assert [c.hand for c in cases] == ["R", "L"], f"{example}: {cases}"
    # Pinned above *and* read from SELECT here: a pin alone would drift with the
    # search it is meant to be pinning.
    cond = next(c for c in default_critical(project).conditions
                if c.component == "htail" and c.label == "UNSYMMETRICAL")
    select = {lv.key: lv.value for lv in cond.loads}
    assert select["rh_side_load"] == pytest.approx(rh_want, rel=1e-9), example
    assert select["lh_side_load"] == pytest.approx(lh_want, rel=1e-9), example
    assert select["other_side_percent"] == pc, example
    # The split percent is SELECT's rule, restated here only to show the pair
    # really is asymmetric -- a 100/100 "split" would pass every other assertion.
    assert lh_want == pytest.approx(pc / 100.0 * rh_want, rel=1e-6)

    for case in cases:
        where = f"{example} {case.label}{case.hand}"
        rh, lh = htail_side_loads(case)
        want = (rh_want, lh_want) if case.hand == "R" else (lh_want, rh_want)
        assert rh == pytest.approx(want[0], rel=1e-9), f"{where} starboard half"
        assert lh == pytest.approx(want[1], rel=1e-9), f"{where} port half"
        assert htail_load(case) == pytest.approx(rh_want + lh_want, rel=1e-9), where
        # ...and it replaces the trim tail load rather than joining it: a case
        # carrying both would balance far better and be wrong.
        assert not any(ld.source == "tail-air" for ld in case.loads), where


@pytest.mark.parametrize("example", _with_unsymmetrical_cases())
def test_the_unsymmetrical_roll_is_the_closed_form(example):
    """**The D-R8 distribution gate**: an analytic target, not a re-run.

    Concept mode has no printed oracle, so the gate is a closed form the
    distribution must hit (``CLAUDE.md`` practice 2). The applied rolling moment
    about the centreline is ``(RH - LH) * y_bar`` exactly, with ``y_bar`` the
    chord-weighted centroid of the half planform -- because the chord-proportional
    distribution puts the same shape on both halves and only the scale differs.
    Computed here from the planform rather than from the load set, so the two
    sides of the identity share no code: -7167.69 lb-in on ``ga6_normal``,
    +81700.39 on the regional jet, ratio 1.000000000 on both.
    """
    project = _project(example)
    planform = resolve_tail_planform(project, HTAIL)
    strips = strip_spans(planform)
    y_bar = (sum(planform.chord(s) * ds * s for s, ds in strips)
             / sum(planform.chord(s) * ds for s, ds in strips))
    rh_want, lh_want, _ = _UNSYMMETRICAL_SPLIT[example]

    for case in _unsymmetrical(project):
        where = f"{example} {case.label}{case.hand}"
        rh, lh = htail_side_loads(case)
        roll = sum(ld.y * ld.fz for ld in case.loads if ld.source == "htail-air")
        assert roll == pytest.approx((rh - lh) * y_bar, rel=1e-9), where
        # The hand is a real reversal of that moment, not a relabelling.
        assert (roll > 0) == (rh - lh > 0), where
        # Against the pinned split, whose constants carry six decimals -- hence
        # the looser tolerance than the identity above, which is exact.
        assert abs(roll) == pytest.approx(abs(rh_want - lh_want) * y_bar, rel=1e-7)


@pytest.mark.parametrize("example", _with_unsymmetrical_cases())
def test_the_trim_half_of_an_unsymmetrical_case_still_closes(example):
    """**The D-R8 residual gate** -- the one that does apply to this family.

    Plan 11's 1 % gate is meaningless on a 23.427(a) case for a stronger version
    of the lateral reason: its applied tail load is a *maneuver* load and it
    replaces the trim tail load the V-n point balances at, so the pre-closure
    ``Fz``/``My`` are that mismatch in full (49.8 % of ``n*W`` on ``ga6_normal``)
    and the vertical and pitch closure is the motion it causes -- an abrupt
    elevator input, which is what 23.423 and 23.427 are about.

    What must still hold is that everything *else* in the case is the shipped
    balanced assembly: put the trim tail load back, as a lumped force at the
    tail's own reference point, and the case closes inside the 1 % gate again.
    That also pins the replacement itself -- if the h-tail set were being applied
    *beside* ``vn.lt`` rather than instead of it, this restoration would double
    the tail load and the residual would blow out.
    """
    project = _project(example)
    vn = {p.case: p for p in default_envelope(project).vn}
    fl = project.flight_loads
    wr = require_wing_reference(project)
    cases = _unsymmetrical(project)
    assert cases, f"{example}: no 23.427(a) case"

    for case in cases:
        where = f"{example} {case.label}{case.hand}"
        cg = _ref_of(case)
        point = vn[case.vn_case]
        trim = [ld for ld in case.loads
                if not ld.source.startswith("closure-")
                and ld.source != "htail-air"]
        trim.append(BalancedLoad(x=fl.xtc, y=0.0, z=wr.zw, fz=point.lt,
                                 source="tail-air", side="C"))
        fx, fy, fz, mx, my, mz = resultant6(trim, (cg.xcg, 0.0, cg.zcg))

        n_w = case.n_w
        force_ceiling = _FORCE_RESIDUAL_RATCHET[example]["unsymmetrical"]
        assert abs(fz) < force_ceiling * n_w, (
            f"{where}: trim-half force residual {100 * fz / n_w:.3f} % of n*W, "
            f"over the ratchet {force_ceiling * 100:.2f} % "
            "-- see _FORCE_RESIDUAL_RATCHET")
        ratchet = _PITCH_RESIDUAL_RATCHET[example]["unsymmetrical"]
        assert abs(my) < RESIDUAL_GATE * n_w * case.mac, (
            f"{where}: trim-half pitch residual "
            f"{100 * my / (n_w * case.mac):.3f} %")
        assert abs(my) < ratchet * n_w * case.mac, (
            f"{where}: trim-half pitch residual "
            f"{100 * my / (n_w * case.mac):.4f} % over the ratchet "
            f"{ratchet * 100:.2f} % -- see _PITCH_RESIDUAL_RATCHET")
        # The trim half is symmetric: the whole hand of the case is the tail
        # split, and putting the lumped load back removes it entirely.
        assert fy == 0.0, f"{where}: trim half carries {fy} lb of Fy"
        assert abs(mx) < 1e-9 * n_w * case.semi_span, f"{where} trim-half roll"
        assert abs(mz) < 1e-9 * n_w * case.semi_span, f"{where} trim-half yaw"


@pytest.mark.parametrize("example", _with_cases())
def test_the_closure_is_solved_at_the_mass_centroid(example):
    """The relief field is referred to the mass set's own centroid, not the
    entered CG -- and on one shipped loading those differ (D-R8).

    The two coincide on every loading the fixtures had before the 23.427(a) case
    arrived, which is why the difference could sit unnoticed in a decoupled
    ``n = F/W`` solve: an angular acceleration applied about the wrong point
    leaves ``-omega_dot x Sum w_i r_i`` of unclosed force, and with the tiny
    ``omega_dot`` of a trimmed case that is nothing. ``ga6_normal``'s ``CG4``
    loading sits 0.0024 in forward and 0.0052 in below its own entered CG, and
    the 23.427(a) case accelerates it at 637 deg/s^2: 0.31 lb of ``Fx``, four
    orders above the closure gate. Asserted as a property so it cannot come back
    on a loading nobody thought to check.
    """
    project = _project(example)
    offsets = []
    for case in build_balanced_cases(project):
        cg = _ref_of(case)
        masses = [ld for ld in case.loads
                  if ld.weight_lb and not ld.source.startswith("closure-")]
        w = sum(ld.weight_lb for ld in masses)
        offsets.append(max(
            abs(sum(ld.weight_lb * (ld.x - cg.xcg) for ld in masses) / w),
            abs(sum(ld.weight_lb * (ld.z - cg.zcg) for ld in masses) / w)))
        # Closure is exact regardless (the six-DOF gate asserts the same thing
        # case by case); what this test adds is that the property is *tested*
        # against a loading where the two reference points really differ.
    if example == "ga6_normal.project.json":
        assert max(offsets) > 1e-3, (
            "no shipped loading's mass centroid differs from its entered CG any "
            "more -- this gate has stopped gating anything, and the closure's "
            "reference point needs a constructed case instead")


def test_the_handedness_predicate():
    """The **L-6 drift guard**: what makes a case handed, stated in isolation.

    ``is_handed`` reads the *distribution* and not the resultant, which is the
    whole of decision L-6: ``ga6_normal``'s ``YAW TO SIDESLIP`` nets -97.8 lb of
    side force out of parts worth -683 and +586, and a net-based predicate would
    mint it unhanded on that near-cancellation and assemble a rudder-kick case
    as a symmetric one. The two-strip set below is that failure in miniature.
    """
    def load(**kw):
        return BalancedLoad(x=0.0, y=0.0, z=0.0, **kw)

    n_w = 1000.0
    assert not is_handed([], n_w)
    assert not is_handed([load(fz=500.0), load(fz=-500.0, my=3.0)], n_w)

    # Nets to zero, but each half is a real side load: handed.
    assert is_handed([load(fy=400.0), load(fy=-400.0)], n_w)
    # A roll or yaw component is enough on its own.
    assert is_handed([load(mx=1.0)], n_w)
    assert is_handed([load(mz=1.0)], n_w)

    # The threshold is a fraction of n*W, so it means the same on any airplane.
    just_under = 0.4 * HANDEDNESS_TOL * n_w
    assert not is_handed([load(fy=just_under), load(fy=just_under)], n_w)
    assert is_handed([load(fy=just_under), load(fy=just_under)], n_w / 10.0)

    # D-R8: a net rolling moment made by the DISTRIBUTION itself -- 23.427(a)'s
    # only signature, since it carries no side force and no free moment. It
    # needs a length to be judged against, and with none supplied the roll test
    # is skipped rather than run against a number whose units decide it.
    span = 100.0
    split = [BalancedLoad(x=0.0, y=+50.0, z=0.0, fz=-100.0),
             BalancedLoad(x=0.0, y=-50.0, z=0.0, fz=-72.0)]
    assert is_handed(split, n_w, span)
    assert not is_handed(split, n_w)
    # A mirror-symmetric distribution is not handed by it, at any length.
    even = [BalancedLoad(x=0.0, y=+50.0, z=0.0, fz=-100.0),
            BalancedLoad(x=0.0, y=-50.0, z=0.0, fz=-100.0)]
    assert not is_handed(even, n_w, span)


@pytest.mark.parametrize("example", _with_handed_cases())
def test_the_handed_twins_are_mirror_images(example):
    """The port twin is the starboard case reflected -- pairwise, load by load.

    Everything even under the mirror is *identical* (the twin's vertical,
    longitudinal and pitching balance is the same case), and everything odd
    reverses. Checked on the loads themselves rather than on totals, because a
    totals-only check passes for a case that reflected nothing at all.

    **G7**, extended by B8a-3 to the lateral family, where the mirror has a
    physical name: the port twin of a rudder kick is the *opposite* kick, the
    ``-beta`` of a ``+beta`` case. That makes the applied set odd as well as the
    closure -- the fin's ``fy`` and its ``mz`` torsion both reverse -- which the
    rolling family, whose applied loads are all symmetric, never exercised.
    """
    cases = build_balanced_cases(_project(example))
    # A twin is emitted immediately after the case it was reflected from, so the
    # pairs are consecutive and non-overlapping. Walked rather than zipped: a
    # sliding window also matches (twin, next computed case), which on the
    # one-wheel family -- three consecutive conditions sharing one label -- pairs
    # ``LG-10L`` with ``LG-11R`` and compares two different conditions.
    adjacent, i = [], 0
    while i < len(cases) - 1:
        a, b = cases[i], cases[i + 1]
        if a.hand and b.hand == reflect_side(a.hand) and a.label == b.label:
            adjacent.append((a, b))
            i += 2
            continue
        i += 1
    pairs = [(a, b) if a.hand == "R" else (b, a) for a, b in adjacent]
    assert pairs, f"{example}: no handed pair"
    for right, left in pairs:
        # **Identity follows decision G-8, which has two shapes.** Where the
        # suite mints the twin itself the hand is a *suffix* on the physical
        # condition's id (``W-05R``/``W-05L``, ``LG-10R``/``LG-10L``). Where
        # LANDLOAD already supplies both hands -- the 23.485 side family, three
        # loadings x two drift directions -- the twin has an id of its **own**
        # (``LG-20`` beside ``LG-19``) and gets no suffix, because minting one
        # would put two ids on one physical condition, which M4-2 decision 1
        # forbids. The hand is a field either way; only the id differs.
        rid, lid = right.case_ref.case_id, left.case_ref.case_id
        if rid.endswith("R"):
            assert lid == rid[:-1] + "L"
        else:
            assert not lid.endswith(("R", "L")), (
                f"{example}: {rid}/{lid} is the manual's own twin pair and must "
                "keep LANDLOAD's ids unsuffixed")
            assert {rid, lid} == {f"LG-{n:02d}" for n in
                                  (int(rid.split("-")[1]), int(lid.split("-")[1]))}
            assert abs(int(rid.split("-")[1]) - int(lid.split("-")[1])) == 1
        assert left.unbal_moment == -right.unbal_moment
        # Odd under the mirror -- the lateral three, all of which B8a-2 made
        # non-trivial: roll reverses, and so do the yaw and side-force relief it
        # induces through Ixz.
        assert left.p_dot == -right.p_dot
        assert left.r_dot == -right.r_dot
        assert left.delta_ny == -right.delta_ny
        assert left.residual_fy == -right.residual_fy
        assert left.residual_mx == -right.residual_mx
        assert left.residual_mz == -right.residual_mz
        assert fin_load(left) == -fin_load(right)
        # Even under the mirror: the twin is the same case in these DOF.
        assert left.residual_fz == right.residual_fz
        assert left.residual_fx == right.residual_fx
        assert left.residual_my == right.residual_my
        assert left.delta_n == right.delta_n
        assert left.q_dot == right.q_dot
        assert len(left.loads) == len(right.loads)
        for a, b in zip(right.loads, left.loads):
            assert (b.x, b.y, b.z) == (a.x, -a.y, a.z)
            assert (b.fx, b.fy, b.fz) == (a.fx, -a.fy, a.fz)
            assert (b.mx, b.my, b.mz) == (-a.mx, a.my, -a.mz)
            assert b.source == a.source


def test_a_symmetric_case_has_no_twin():
    """A symmetric case is its own mirror image; minting a twin would put the same
    load set in the deck twice."""
    cases = build_balanced_cases(_project("ga6_normal.project.json"))
    symmetric = next(c for c in cases if not c.hand)
    with pytest.raises(ValueError, match="no hand"):
        handed_twin(symmetric)


def test_the_reflection_operator_is_an_involution():
    """The B-6 drift guard: reflect twice and you are back where you started.

    The operator has **one owner** (``export/coordinates.py``) precisely because a
    sign convention copied to a second call site is the class of error that
    produces a deck which parses, solves, and sizes structure to a load the
    airplane never sees. This is the guard ``CLAUDE.md`` practice 3 asks for
    alongside that owner.
    """
    assert reflect_point(1.0, 2.0, 3.0) == (1.0, -2.0, 3.0)
    assert reflect_force(1.0, 2.0, 3.0) == (1.0, -2.0, 3.0)
    # A moment is an axial vector and transforms the other way round: roll and
    # yaw reverse, pitch does not. Applying the force rule here would mirror a
    # rolling case into itself and negate its pitch.
    assert reflect_moment(1.0, 2.0, 3.0) == (-1.0, 2.0, -3.0)
    assert reflect_side("R") == "L" and reflect_side("L") == "R"
    assert reflect_side("C") == "C"
    for v in ((1.0, 2.0, 3.0), (-4.5, 0.0, 6.25)):
        assert reflect_point(*reflect_point(*v)) == v
        assert reflect_force(*reflect_force(*v)) == v
        assert reflect_moment(*reflect_moment(*v)) == v


@pytest.mark.parametrize("example", _with_handed_roll())
def test_the_rolling_deck_states_that_it_rolls(example):
    """A rolling deck must say so, and say the couple is applied rather than
    unbalanced -- otherwise a reader sees a 2-7 % 'residual' and distrusts the
    case for the wrong reason."""
    text = balanced_deck(_project(example))
    assert "ROLLING case: applied aileron couple" in text
    assert "STARBOARD roll" in text and "PORT roll" in text
    over = [ln for ln in text.splitlines() if ln.startswith("$") and len(ln) > 72]
    assert not over, over


def _ground_examples():
    return [e for e, v in _EXPECTED_GROUND_CASES.items() if v]


@pytest.mark.parametrize("example", _ground_examples())
def test_no_surface_calls_a_ground_case_a_v_n_point(example):
    """**R6-C3's pin.** A ground case's number is LANDLOAD's, not the V-n table's.

    ``BalancedCaseResult.vn_case`` carries the *source* case number, and the two
    producers both number from 1: "V-n point 19" on a LANDLOAD case 19 sends a
    reader to a real and unrelated flight point -- the silent-wrong-join class
    design note 17's case identity exists to prevent.

    Every surface that prints the number is checked here, because the defect was
    one wording repeated at five of them: the deck ``$`` header, the deck case
    map, ``run()``'s condition titles, the rows table and the skipped record.
    The flight families' wording is pinned in the same breath -- the fix must
    not have renamed a V-n point either.
    """
    project = _project(example)
    # One assembly, reused by every surface below: on the RJ each rebuild is
    # tens of seconds, and re-deriving the same cases five times would make this
    # pin the slowest test in the file for nothing.
    skipped = []
    cases = build_balanced_cases(project, skipped)
    ground = [c for c in cases if is_ground(c)]
    assert ground, example

    # 1. The deck's ``$`` header, per case. Asked of the header builder rather
    # than of a substring of the whole deck, because the two families' case
    # numbers COLLIDE -- V-n point 14 and LANDLOAD case 14 both exist on the RJ,
    # which is the finding -- so only a per-case check can tell them apart.
    u = deliverable_units(UnitSystem.IMPERIAL, Channel.SOLVER)
    for c in cases:
        head = " ".join(" ".join(ln.lstrip("$ ") for ln
                                 in balanced_deck_module._header(c, u)).split())
        want = ("LANDLOAD case" if is_ground(c) else "V-n point")
        assert f"-- {want} {c.vn_case}, loading" in head, (example, c.label)
        if is_ground(c):
            # Not "no 'V-n' anywhere": the G-7 lift note legitimately says the
            # borrowed Schrenk shape involves no V-n point at all. What must
            # not appear is the number under a V-n wording.
            assert f"V-n {c.vn_case}" not in head, (example, c.label)
            assert f"V-n point {c.vn_case}" not in head, (example, c.label)

    # 2. The deck's case map -- one line per case, found by its case id.
    text = balanced_deck(project, cases=cases, skipped=skipped)
    # Reassembled from the wrapped comment lines: a map entry runs past 70
    # columns on the longer ground labels, so "LANDLOAD case 4" itself straddles
    # the break.
    block = " ".join(ln.lstrip("$ ").strip() for ln in text.splitlines()
                     if ln.startswith("$"))
    entries = {e.split(" = ")[1].split(" -- ")[0]: e
               for e in ("SUBCASE " + p for p in block.split("SUBCASE ")[1:])
               if " = " in e}
    for c in ground:
        entry = entries[c.case_ref.case_id]
        assert f"LANDLOAD case {c.vn_case}" in entry, entry
        assert "V-n" not in entry.split("Nz")[0], entry

    # 3. run()'s titles.
    titles = [cond.title for cond in balance_module.run(project).conditions]
    for c in ground:
        assert any(f"(LANDLOAD case {c.vn_case}," in t for t in titles), c.label
    # 4. The rows table -- family-aware value under a family-neutral header.
    rows = balanced_case_rows(cases)
    assert "V-n point" not in rows[0]
    by_id = {r["ID"]: r["Source case"] for r in rows}
    for c in ground:
        assert by_id[c.case_ref.case_id] == f"LANDLOAD case {c.vn_case}"
    for c in cases:
        if not is_ground(c):
            assert by_id[c.case_ref.case_id] == f"V-n point {c.vn_case}"

    # 5. The skipped record: a ground skip names LANDLOAD's table too.
    ground_skips = [s for s in skipped if s.ground]
    assert ground_skips, example
    for s in ground_skips:
        assert f"(LANDLOAD case {s.case})" in s.name, s.name
    assert all("V-n" not in s.name for s in ground_skips)
    assert all("V-n" in s.name for s in skipped
               if not s.ground and s.case is not None)


def test_the_source_case_label_has_one_owner():
    """The wording is a function, not five literals (``CLAUDE.md`` practice 3)."""
    assert source_case_name(19, True) == "LANDLOAD case 19"
    # No short form for the ground stem: abbreviating it would invent a fourth
    # name for the same number.
    assert source_case_name(19, True, short=True) == "LANDLOAD case 19"
    assert source_case_name(19, False) == "V-n point 19"
    assert source_case_name(19, False, short=True) == "V-n 19"
    for module in (balanced_deck_module, balance_module):
        source = open(module.__file__, encoding="utf-8").read()
        assert "V-n point {" not in source, module.__name__
        assert 'f"V-n ' not in source, module.__name__


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
