"""The empennage planform resolver and its drift guard (plan 09 T1).

The tail carries its geometry **twice**: as the scalar area/span the
oracle-locked modules have always read (SELECT, TAILDIST, BALLOADS), and — from
T1 — optionally as an ``"htail"``/``"vtail"`` planform in ``geometry.surfaces``,
which is what a spanwise strip integrator needs. Two representations of one
surface is exactly the situation that goes quietly wrong, so these tests gate the
three things that keep it from doing so:

1. an entered planform that disagrees with the scalars **fails loudly**, with the
   half/full bookkeeping applied correctly per surface (getting that backwards is
   a factor of two in every strip);
2. where no planform is entered, one is **derived and marked assumed** — never
   silently treated as input;
3. the new schema round-trips and every shipped fixture still loads.
"""

import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from imperial_baseline import EXAMPLES

from sloads import io
from sloads.models import SCHEMA_VERSION, SurfaceInput, TailMassInput
from sloads.tail_geometry import (
    HTAIL,
    PLANFORM_TOLERANCE,
    VTAIL,
    _polyline_mac_and_x25,
    half_area_centroid,
    resolve_tail_planform,
    validate_tail_planform,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Which fixtures model which tail surface, pinned so a skip below is a recorded
#: fact rather than a silently vanished check. ``concept_heavy`` carries no tail
#: slice at all — the same gap ``test_export_equilibrium`` already pins.
_TAIL_COVERAGE = {
    "atr42_100.project.json": (True, True),
    "cessna_210.project.json": (True, True),
    "concept_heavy.project.json": (False, False),
    "concept_regional_jet.project.json": (True, True),
    "dhc8_dash8.project.json": (True, True),
    "ga6_normal.project.json": (True, True),
}


def _project(example: str):
    return io.load_project(os.path.join(_ROOT, "examples", example))


@pytest.mark.parametrize("example", EXAMPLES)
def test_which_fixtures_model_a_tail_is_pinned(example):
    project = _project(example)
    got = tuple(resolve_tail_planform(project, c) is not None for c in (HTAIL, VTAIL))
    assert got == _TAIL_COVERAGE[example], example


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_derived_planform_reproduces_taildist_average_chord(example):
    """A derived planform's chord **is** TAILDIST's ``CAVE`` — by construction, and
    checked because it is what makes the two tail views describe one surface.

    TAILDIST spreads the load chordwise over ``CAVE = S / span``; the derived
    rectangle uses the same area and the same span, so its constant chord must be
    that number. On ``ga6_normal`` both come to 36.39 in for the h-tail.
    """
    project = _project(example)
    for component, span_attr in ((HTAIL, "htail"), (VTAIL, "vtail")):
        planform = resolve_tail_planform(project, component)
        if planform is None:
            continue
        assert planform.assumed == (example not in _ENTERED_TAILS), (
            f"{example} {component}: the entered-polyline set is pinned")
        if not planform.assumed:
            continue   # the entered fixtures are checked by the test below
        full_span = 2.0 * planform.span if component == HTAIL else planform.span
        want = planform.area / full_span
        for s in (0.0, planform.span / 2.0, planform.span):
            assert planform.chord(s) == pytest.approx(want, rel=1e-12), \
                f"{example} {component} at s={s}"
        assert span_attr in component


#: The fixtures whose empennage is **entered** as polylines (backlog Pri 1, the
#: fixture-data pass, 2026-08-17) -- taper and sweep estimated from the type's
#: published three-view, area/span/25 %-MAC station tied to the scalars.
#: ``ga6_normal`` stays derived on purpose: Appendix A prints no tail chords, and
#: an invented taper on the oracle fixture would be reported as entered data.
_ENTERED_TAILS = frozenset({
    "atr42_100.project.json",
    "cessna_210.project.json",
    "dhc8_dash8.project.json",
    "concept_regional_jet.project.json",
})


@pytest.mark.parametrize("example", sorted(_ENTERED_TAILS))
def test_an_entered_fixture_tail_is_tapered_and_sits_on_its_scalar_station(example):
    """The entered polylines describe the *same* surface the scalars do -- and a
    real one: tapered (root chord > tip chord), the strip quadrature's area equal
    to the scalar area to the validator's tolerance, and the polyline's own
    quarter-MAC station on ``xt25``/``xv25`` -- so the deck's strips and the
    balance's tail arm agree on where the load is."""
    project = _project(example)
    for component in (HTAIL, VTAIL):
        planform = resolve_tail_planform(project, component)
        assert planform is not None and not planform.assumed, f"{example} {component}"
        assert planform.chord(0.0) > planform.chord(planform.span), (
            f"{example} {component}: expected a tapered surface")
        assert planform.strip_area() == pytest.approx(planform.area, rel=PLANFORM_TOLERANCE)
        surf = project.geometry.by_name(component)
        want = project.tail_loads.xt25 if component == HTAIL else project.vtail_loads.xv25
        mac, x25 = _polyline_mac_and_x25(surf)
        assert x25 == pytest.approx(want, abs=PLANFORM_TOLERANCE * mac), f"{example} {component}"


def test_a_polyline_off_its_scalar_station_is_refused():
    """The third leg of the T-1 validator (backlog Pri 1): a polyline whose
    quarter-MAC point is not at ``xt25`` puts the deck's tail load on a lever arm
    the balance did not use. Area and span can agree while this does not."""
    project = _project("ga6_normal.project.json")
    ti = project.tail_loads
    b = ti.htail_semispan_in
    chord = ti.htail_area_sqft * 144.0 / (2.0 * b)
    x_le = ti.xt25 - 0.25 * chord
    def surf(shift):
        return SurfaceInput(name=HTAIL,
                            leading_edge=[(x_le + shift, 0.0), (x_le + shift, b)],
                            trailing_edge=[(x_le + shift + chord, 0.0), (x_le + shift + chord, b)])
    validate_tail_planform(surf(0.0), HTAIL, ti.htail_area_sqft, b, ti.xt25)
    with pytest.raises(ValueError, match="25 %-MAC station"):
        validate_tail_planform(surf(0.05 * chord), HTAIL, ti.htail_area_sqft, b, ti.xt25)


@pytest.mark.parametrize("example", EXAMPLES)
def test_a_derived_planform_says_so(example):
    """``assumed`` travels with a note, because a derived rectangular tail is a
    first-order stand-in and every consumer has to be able to say so."""
    project = _project(example)
    for component in (HTAIL, VTAIL):
        planform = resolve_tail_planform(project, component)
        if planform is None or not planform.assumed:
            continue
        assert planform.notes and "DERIVED" in planform.notes[0]


def test_the_rectangle_centroid_is_half_span():
    """``ybar = b/2`` for the derived rectangle — the bending target, and the
    reason a derived planform is conservative.

    A straight-tapered surface has ``ybar = (b/3)(c_r + 2c_t)/(c_r + c_t)``, which
    falls from ``b/2`` (untapered) toward ``b/3`` (pointed tip). The derived
    planform therefore puts the load further **outboard** than a real tapered
    tail, i.e. high in root bending.
    """
    planform = resolve_tail_planform(_project("ga6_normal.project.json"), HTAIL)
    assert half_area_centroid(planform) == pytest.approx(planform.span / 2.0, rel=1e-9)


def test_a_tapered_planform_centroid_matches_the_closed_form():
    """The integrator reproduces ``(b/3)(c_r + 2c_t)/(c_r + c_t)``.

    Two independent producers of one number: the analytic trapezoid centroid,
    written here by hand, and the strip integration the module actually uses.
    """
    b, c_r, c_t = 60.0, 40.0, 20.0
    surf = SurfaceInput(
        name=HTAIL,
        leading_edge=[(100.0, 0.0), (100.0, b)],
        trailing_edge=[(100.0 + c_r, 0.0), (100.0 + c_t, b)],
        elements=200,
    )
    project = _project("ga6_normal.project.json")
    area_in2 = 2.0 * 0.5 * (c_r + c_t) * b
    project.tail_loads.htail_area_sqft = area_in2 / 144.0
    project.tail_loads.htail_semispan_in = b
    project.tail_loads.xt25 = _polyline_mac_and_x25(surf)[1]   # sit on the scalar station
    project.geometry.surfaces.append(surf)

    planform = resolve_tail_planform(project, HTAIL)
    assert not planform.assumed
    want = (b / 3.0) * (c_r + 2.0 * c_t) / (c_r + c_t)
    assert half_area_centroid(planform) == pytest.approx(want, rel=1e-4)


# --------------------------------------------------------------------------- #
# The drift guard (T1's stated gate)
# --------------------------------------------------------------------------- #
def _rect_surface(name, span, chord, x_le=100.0):
    return SurfaceInput(name=name,
                        leading_edge=[(x_le, 0.0), (x_le, span)],
                        trailing_edge=[(x_le + chord, 0.0), (x_le + chord, span)],
                        elements=10)


def test_the_htail_validator_applies_the_half_full_rule():
    """An h-tail polyline is **one side**, so its area doubles before comparison.

    This is the check that catches the factor-of-two: a polyline whose *doubled*
    area matches passes, and one whose raw area matches (i.e. half the airplane's
    real tail) fails.
    """
    span, chord = 73.1, 36.39
    area_sqft = 2.0 * span * chord / 144.0
    validate_tail_planform(_rect_surface(HTAIL, span, chord), HTAIL, area_sqft, span)
    with pytest.raises(ValueError, match="disagrees with its scalar geometry"):
        validate_tail_planform(_rect_surface(HTAIL, span, chord / 2.0),
                               HTAIL, area_sqft, span)


def test_the_vtail_validator_applies_no_factor():
    """The fin is a single surface: polyline area compares to ``vtail_area_sqft``
    directly. Doubling it here would be the same defect mirrored."""
    span, chord = 57.0, 37.49
    area_sqft = span * chord / 144.0
    validate_tail_planform(_rect_surface(VTAIL, span, chord), VTAIL, area_sqft, span)
    with pytest.raises(ValueError, match="disagrees"):
        validate_tail_planform(_rect_surface(VTAIL, span, 2.0 * chord),
                               VTAIL, area_sqft, span)


def test_the_validator_fires_just_outside_the_tolerance():
    """Pinned at the boundary, so the gate is known to be the stated 1 % and not
    whatever the fixtures happen to satisfy."""
    span, chord = 60.0, 30.0
    area_sqft = 2.0 * span * chord / 144.0
    inside = _rect_surface(HTAIL, span, chord * (1.0 + PLANFORM_TOLERANCE * 0.9))
    outside = _rect_surface(HTAIL, span, chord * (1.0 + PLANFORM_TOLERANCE * 1.1))
    validate_tail_planform(inside, HTAIL, area_sqft, span)
    with pytest.raises(ValueError):
        validate_tail_planform(outside, HTAIL, area_sqft, span)


def test_an_entered_planform_wins_and_is_not_assumed():
    project = _project("ga6_normal.project.json")
    ti = project.tail_loads
    span = ti.htail_semispan_in
    chord = ti.htail_area_sqft * 144.0 / (2.0 * span)
    surf = _rect_surface(HTAIL, span, chord, x_le=ti.xt25 - 0.25 * chord)
    surf.elements = 7
    surf.ref_axis_pct = 0.42
    project.geometry.surfaces.append(surf)

    planform = resolve_tail_planform(project, HTAIL)
    assert not planform.assumed and not planform.notes
    assert planform.elements == 7 and planform.ref_axis_pct == 0.42


def test_an_inconsistent_entered_planform_is_refused_through_the_resolver():
    """The validator is not merely available — it is on the resolution path."""
    project = _project("ga6_normal.project.json")
    project.geometry.surfaces.append(_rect_surface(HTAIL, 73.1, 10.0))
    with pytest.raises(ValueError, match="disagrees"):
        resolve_tail_planform(project, HTAIL)


def test_an_unknown_component_raises():
    with pytest.raises(ValueError, match="unknown tail component"):
        resolve_tail_planform(_project("ga6_normal.project.json"), "canard")


# --------------------------------------------------------------------------- #
# Schema (T1's other stated gate)
# --------------------------------------------------------------------------- #
def test_tail_mass_round_trips():
    project = _project("ga6_normal.project.json")
    project.tail_mass = [TailMassInput(surface=HTAIL, panel_weight_lb=42.0),
                         TailMassInput(surface=VTAIL, panel_weight_lb=23.0)]
    back = io.project_from_dict(json.loads(json.dumps(io.project_to_dict(project))))
    assert back.tail_mass == project.tail_mass
    assert back.schema_version == SCHEMA_VERSION


def test_a_project_without_tail_mass_writes_no_key():
    """Absent stays absent: a project with no empennage mass round-trips
    byte-identically to a pre-v42 file."""
    project = _project("ga6_normal.project.json")
    assert not project.tail_mass
    assert "tail_mass" not in io.project_to_dict(project)


@pytest.mark.parametrize("example", EXAMPLES)
def test_every_fixture_still_loads_and_round_trips(example):
    """T1's third gate: the schema bump is additive and moves no shipped file."""
    project = _project(example)
    once = io.project_to_dict(project)
    twice = io.project_to_dict(io.project_from_dict(copy.deepcopy(once)))
    assert once == twice, example


# --------------------------------------------------------------------------- #
# The fin root waterline (plan 13 B8a-1, decision L-1)
# --------------------------------------------------------------------------- #
#: Where each fixture's fin root resolves to, and on whose authority. Pinned
#: because the value is the lever arm of a first-order roll load: before B8a-1
#: every fin sat at ``z = 0``, which put ``ga6_normal``'s **below its own CG**
#: and reversed the sign of the roll moment a side load makes.
#:
#: T-8a moved three of them, and backlog Pri 1 moved the same three again by
#: giving the "fuselage-top" branch its body datum. The branch is now
#: ``z_centre(x_fin) + height(x_fin)/2`` -- the section-centre line
#: (``derived_geometry.fuselage_centreline``, note 24 R-4; defaulted from the
#: body-drag waterline and marked assumed on all three, since no fixture enters
#: ``z_centre``) plus half the **local** body height at the fin's ``xv25``.
#: The formula it replaced, ``root_waterline_z + fuselage_height/2``, read the
#: WING root as the body centreline (the substitution D-1 refuses), and on
#: these three high-wing types stacked half a body above the real top:
#: ``atr42_100`` 223.15 -> 191.17, ``dhc8_dash8`` 232.95 -> 203.45,
#: ``cessna_210`` 109.60 -> 100.24. That formula survives only as the
#: no-outline fallback, which is what still places ``ga6_normal`` (no fuselage
#: outline, ``fuselage_height`` 0, so it degrades to the wing root waterline
#: and says so).
#: ``ga6_normal`` **enters** its fin root since backlog Pri 1 (2026-08-17):
#: ``vtail_root_waterline_z = 78.5`` pins the value the fallback had been
#: producing, as a stated one, so that the body outline (and L-7) can land with
#: an attributable digest wave -- note 19 §10.2 (i). Zero movement, by design.
_FIN_ROOT = {
    "ga6_normal.project.json": (78.5, "entered"),
    "concept_regional_jet.project.json": (87.0, "t-tail"),
    "cessna_210.project.json": (100.2354943818504, "fuselage-top"),
    "atr42_100.project.json": (191.1672210589451, "fuselage-top"),
    "dhc8_dash8.project.json": (203.4541778899263, "fuselage-top"),
}


@pytest.mark.parametrize("example", sorted(_FIN_ROOT))
def test_the_fin_root_waterline_is_pinned_per_fixture(example):
    want_z, want_basis = _FIN_ROOT[example]
    planform = resolve_tail_planform(_project(example), VTAIL)
    assert planform is not None
    assert planform.root_z == pytest.approx(want_z, rel=1e-9)
    assert planform.root_z_basis == want_basis
    assert planform.root_z_assumed == (want_basis != "entered"), example


def test_an_entered_fin_root_wins_and_is_not_assumed():
    """The explicit input is the top of the resolution order (L-1)."""
    project = _project("ga6_normal.project.json")
    project.vtail_loads.vtail_root_waterline_z = 101.5
    planform = resolve_tail_planform(project, VTAIL)
    assert planform.root_z == pytest.approx(101.5)
    assert not planform.root_z_assumed and planform.root_z_basis == "entered"
    assert not any("ASSUMED" in n for n in planform.notes)


def test_the_t_tail_branch_puts_the_fin_tip_at_the_horizontal_tail():
    """The T-tail relation is the inverse of the three-view's own default, which
    places a T-tail's horizontal surface at the fin tip. Solving it for the root
    is what keeps the two surfaces in contact when ``h_tail_z`` is entered rather
    than defaulted — the fuselage-top formula leaves them 18 in apart on the RJ."""
    project = _project("concept_regional_jet.project.json")
    layout = project.geometry.parametric
    planform = resolve_tail_planform(project, VTAIL)
    fin_tip = planform.root_z + planform.span
    assert fin_tip == pytest.approx(layout.root_waterline_z + layout.h_tail_z)
    fuselage_top = layout.root_waterline_z + layout.fuselage_height / 2.0
    assert fuselage_top - planform.root_z == pytest.approx(18.0)


def test_the_outline_branch_states_its_datum_and_a_pointed_cone_falls_through():
    """Backlog Pri 1: the fuselage-top branch is ``z_centre(xv25) + height(xv25)/2``
    from the fuselage outline, and its note carries both the formula and the
    defaulted-centreline provenance. Where the outline pinches to nothing at the
    fin station (a pointed tail cone states no top to sit on) the branch declines
    and the layout fallback answers -- naming the wing-root substitution it makes."""
    project = _project("atr42_100.project.json")
    planform = resolve_tail_planform(project, VTAIL)
    note = next(n for n in planform.notes if "local fuselage top" in n)
    assert "z_centre" in note and "fuselage centre line ASSUMED" in note

    # Pinch the outline: zero height everywhere aft of the nose section.
    for section in project.geometry.fuselage.sections[1:]:
        section.height = 0.0
    from sloads.derived_geometry import sync_geometry_derived
    sync_geometry_derived(project)   # fuselage_height follows the outline
    fallback = resolve_tail_planform(project, VTAIL)
    layout = project.geometry.parametric
    assert fallback.root_z == pytest.approx(
        layout.root_waterline_z + layout.fuselage_height / 2.0)
    assert any("WING root stands in" in n for n in fallback.notes)


def test_a_fin_with_no_placement_at_all_says_so_loudly():
    """The floor of the resolution order. Silent zero is the defect B8a-1 fixed,
    so the zero that remains possible has to announce itself."""
    project = _project("ga6_normal.project.json")
    project.vtail_loads.vtail_root_waterline_z = 0.0   # un-enter the Pri 1 pin
    project.geometry.fuselage = None                    # ...and its Pri 1 outline
    project.geometry.parametric.root_waterline_z = 0.0
    project.geometry.parametric.fuselage_height = 0.0
    planform = resolve_tail_planform(project, VTAIL)
    assert planform.root_z == 0.0 and planform.root_z_basis == "none"
    assert any("wrong in sign" in n for n in planform.notes)


@pytest.mark.parametrize("example", sorted(_FIN_ROOT))
def test_the_three_view_and_the_load_path_place_one_fin_once(example):
    """The drift guard for the new single-source owner (CONVENTIONS.md §7).

    ``configuration.tail_planform`` draws the fin and ``tail_span`` loads it. They
    read the same function now; this fails the day one of them grows its own copy
    of the formula.
    """
    from sloads.modules.configuration import tail_planform

    project = _project(example)
    panels = tail_planform(project.geometry.parametric, project.geometry.empennage,
                           project)
    sketch_root = min(z for _, z in panels["v_tail"]["side"])
    assert sketch_root == pytest.approx(
        resolve_tail_planform(project, VTAIL).root_z, rel=1e-9)


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
