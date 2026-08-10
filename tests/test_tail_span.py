"""The spanwise empennage distribution and its closed-form gates (plan 09 T2).

No printed oracle exists for a spanwise tail distribution — Appendix A stops at
the totals (SELECT) and the chordwise profile (TAILDIST). So the gate is
``CLAUDE.md`` practice 2's substitute: a **stated physics closure**, and here it
is an unusually strong one, because the chord-proportional shape (decision T-2)
makes every target *analytic*.

The five closures of plan 09 §4, each with its hand-derived target:

* **force** — Σ strip air load = ``LT25 + LT50``, exactly;
* **bending** — each half's root bending = ``L_half · ybar``, with ``ybar`` the
  half-planform area centroid, ``(b/3)(c_r + 2c_t)/(c_r + c_t)`` for a trapezoid;
* **centreline rolling** — net moment about the centreline = ``(L_RH − L_LH)·ybar``,
  which is **identically zero for every symmetric case** and the asymmetry moment
  for 23.427(a). This is the gate the full-span topology (T-8) buys and a
  per-side deck could not state;
* **torsion** — ``(LT25+LT50)·x̄_lra − LT25·x̄_25 − LT50·x̄_50``, area-weighted;
* **inertia** — Σ = ``−n·W_surf`` exactly, **signed by n alone** (T-9), with a
  companion test asserting a down-load case comes out *larger* in magnitude than
  air alone. That one pins the sign convention against the plausible-looking
  regression: a rule that opposes the air load would relieve exactly the
  conditions that size a GA h-tail.

Plus the reduction identity: with the LRA at 25 % chord the ``LT25`` torsion term
vanishes, the same property the wing's LRA transfer is pinned by.
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from sloads import io  # noqa: E402
from sloads.models import MissingInputError, SurfaceInput, TailMassInput  # noqa: E402
from sloads.modules.flight_envelope import build_envelope  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.modules.tail_span import (  # noqa: E402
    X25_PCT,
    X50_PCT,
    air_total,
    attachment_stations,
    build_tail_span,
    distribute,
    free_torsion_total,
    inertia_total,
    root_index,
    side_scales,
    strip_spans,
)
from sloads.export.coordinates import tail_station_to_airplane  # noqa: E402
from sloads.tail_geometry import HTAIL, VTAIL, half_area_centroid, resolve_tail_planform  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Fixtures with a modelled empennage. ``concept_heavy`` has no tail slice; the
#: twins have one, so the sweep is the full set that can produce a tail deck.
EXAMPLES = ("ga6_normal.project.json", "cessna_210.project.json",
            "atr42_100.project.json", "dhc8_dash8.project.json",
            "concept_regional_jet.project.json")

#: A tail mass held **fixed across every fixture**, so the analytic closures below
#: read one number instead of six. Since the SSOT step the surface weight is
#: derived from the ``htail``/``vtail``-tagged weight items (42/23 lb on ga6,
#: 520/640 on the RJ), so pinning it takes the documented explicit-override path
#: -- which is also what exercises that path. ``weight=0.0`` is the same
#: mechanism used to switch the inertia off: an override *of zero*, not an
#: absent input, because an absent input now correctly derives a real mass.
_TAIL_WEIGHT = 42.0

_CACHE = {}


def _project(example: str, weight: float = _TAIL_WEIGHT):
    key = (example, weight)
    if key not in _CACHE:
        p = io.load_project(os.path.join(_ROOT, "examples", example))
        if p.envelope is None:
            p.envelope = build_envelope(p)
        if p.envelope.critical is None:
            p.envelope.critical = build_critical(p)
        p.tail_mass = [
            TailMassInput(surface=s, panel_weight_lb=weight, weight_is_override=True)
            for s in (HTAIL, VTAIL)
        ]
        _CACHE[key] = p
    return copy.deepcopy(_CACHE[key])


def _results(example: str, weight: float = _TAIL_WEIGHT):
    spans = build_tail_span(_project(example, weight))
    return spans[HTAIL] + spans[VTAIL]


# --------------------------------------------------------------------------- #
# Force closure (plan §4)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_strip_loads_sum_to_the_select_total_plus_the_inertia(example):
    """Σ strip ``fz`` = air total + inertia total, exactly.

    The air half is SELECT's ``LT25 + LT50`` (per-side scaled for 23.427(a)) and
    the inertia half is ``−n·W_surf``; both are known independently of this
    quadrature, so the sum is a real check and not a restatement.
    """
    results = _results(example)
    assert results, example
    for r in results:
        got = sum(st.fz for st in r.stations)
        want = air_total(r) + inertia_total(r)
        assert got == pytest.approx(want, rel=1e-9, abs=1e-9), \
            f"{example} {r.component} {r.case}"


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_air_only_distribution_sums_to_the_select_total(example):
    """With the mass switched off, Σ = ``LT25 + LT50`` on the nose.

    Separated from the test above because it is the one that would catch a
    factor-of-two in the half/full bookkeeping: the h-tail's strips cover **both**
    halves and ``LT25``/``LT50`` are both-sides totals, so the two must meet with
    no factor anywhere.
    """
    for r in _results(example, weight=0.0):
        got = sum(st.fz for st in r.stations)
        assert got == pytest.approx(air_total(r), rel=1e-9, abs=1e-9), \
            f"{example} {r.component} {r.case}"
        assert inertia_total(r) == 0.0


# --------------------------------------------------------------------------- #
# Bending closure
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_root_bending_is_the_half_load_times_the_area_centroid(example):
    """Root bending = ``L_half · ybar`` — the hand-derived target of plan §4.

    ``ybar`` is the half-planform **area centroid**, which for the chord-
    proportional distribution is also the load centroid; the target is therefore
    analytic and is computed here from the planform, not from the load table the
    module built.
    """
    project = _project(example, weight=0.0)
    for r in build_tail_span(project)[HTAIL] + build_tail_span(project)[VTAIL]:
        planform = resolve_tail_planform(project, r.component)
        ybar = half_area_centroid(planform)
        # The h-tail's polyline is one side of a symmetric surface, so a half
        # carries half the both-sides total; the fin is a single surface and
        # carries all of it. This is the half/full seam, and getting it wrong
        # here is exactly the factor of two the plan warns about.
        side_air = (0.5 * (r.lt25 + r.lt50) if r.component == HTAIL
                    else r.lt25 + r.lt50)
        for side, scale in (("R", r.rh_scale), ("L", r.lh_scale)):
            if r.component == VTAIL and side == "L":
                continue
            want = scale * side_air * ybar
            outer = [st for st in r.stations
                     if (st.y > 0 if side == "R" else st.y < 0)]
            if not outer:
                continue
            root = min(outer, key=lambda st: abs(st.y))
            # The cumulative table's root station is half a strip off the
            # centreline, so its bending is that of the load outboard of it about
            # *itself*; add the whole half-load's moment over that offset back.
            got = root.mxx + root.sz * abs(root.y)
            assert got == pytest.approx(want, rel=1e-6), \
                f"{example} {r.component} {r.case} {side}"


# --------------------------------------------------------------------------- #
# Centreline rolling closure -- what the full-span topology (T-8) buys
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_symmetric_cases_roll_the_centreline_by_nothing(example):
    """Net moment about the centreline = ``(L_RH − L_LH)·ybar`` — zero when
    symmetric, and the asymmetry moment for 23.427(a).

    A per-side deck cannot state this at all; it is the specific check that a
    mis-placed attachment or a mirrored-wrong half would fail.
    """
    project = _project(example, weight=0.0)
    spans = build_tail_span(project)
    for r in spans[HTAIL]:
        planform = resolve_tail_planform(project, HTAIL)
        ybar = half_area_centroid(planform)
        half_air = 0.5 * (r.lt25 + r.lt50)
        want = (r.rh_scale - r.lh_scale) * half_air * ybar
        got = sum(st.fz * st.y for st in r.stations)
        assert got == pytest.approx(want, rel=1e-6, abs=1e-6), \
            f"{example} {r.case}"
        if r.rh_scale == r.lh_scale:
            assert got == pytest.approx(0.0, abs=1e-6), f"{example} {r.case}"


def test_the_unsymmetrical_case_rolls_and_the_others_do_not():
    """23.427(a) is the *only* h-tail condition with a net rolling input.

    Pinned as a fact about the condition set, not just about one case: it is the
    reason the full-span deck exists, and if a second condition ever grew an
    asymmetry the deck's support pair would need re-examining.
    """
    project = _project("ga6_normal.project.json", weight=0.0)
    rolling = {r.case: sum(st.fz * st.y for st in r.stations)
               for r in build_tail_span(project)[HTAIL]}
    assert rolling["UNSYMMETRICAL"] != pytest.approx(0.0, abs=1.0)
    for case, moment in rolling.items():
        if case != "UNSYMMETRICAL":
            assert moment == pytest.approx(0.0, abs=1e-6), case


def test_the_unsymmetrical_side_scales_come_from_select():
    """``rh_scale``/``lh_scale`` are SELECT's own RH/LH split, read not recomputed.

    ``pc = min(100 − 10(n−1), 80)`` stays owned by ``select_htail_unsymmetrical``
    (oracle-locked, with an approved deviation recorded against it); this module
    must never carry a second copy of that rule.
    """
    project = _project("ga6_normal.project.json", weight=0.0)
    cond = next(c for c in project.envelope.critical.conditions
                if c.component == HTAIL and c.label == "UNSYMMETRICAL")
    rh_scale, lh_scale = side_scales(cond)
    rh = next(lv.value for lv in cond.loads if lv.key == "rh_side_load")
    lh = next(lv.value for lv in cond.loads if lv.key == "lh_side_load")
    assert rh_scale == pytest.approx(1.0)
    assert lh_scale == pytest.approx(lh / rh)
    # ...and the distribution honours them: each half integrates to its own share.
    r = next(r for r in build_tail_span(project)[HTAIL] if r.case == "UNSYMMETRICAL")
    assert sum(st.fz for st in r.stations if st.y > 0) == pytest.approx(rh, rel=1e-9)
    assert sum(st.fz for st in r.stations if st.y < 0) == pytest.approx(lh, rel=1e-9)


# --------------------------------------------------------------------------- #
# Torsion closure + the LRA reduction identity
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_torsion_is_the_area_weighted_closed_form(example):
    """Σ strip torsion = ``(LT25+LT50)·x̄_lra − LT25·x̄_25 − LT50·x̄_50``.

    The target is assembled here from area-weighted chordwise means computed off
    the planform, which is a different computation from the module's per-strip
    sum even though both are exact.
    """
    project = _project(example, weight=0.0)
    for component in (HTAIL, VTAIL):
        planform = resolve_tail_planform(project, component)
        if planform is None:
            continue
        for r in build_tail_span(project)[component]:
            means = {}
            for pct in (planform.ref_axis_pct, X25_PCT, X50_PCT):
                num = den = 0.0
                for s, ds in strip_spans(planform):
                    da = planform.chord(s) * ds
                    num += da * planform.x_at(s, pct)
                    den += da
                means[pct] = num / den
            sides = ((r.rh_scale + r.lh_scale) / 2.0 if component == HTAIL
                     else r.rh_scale)
            want = sides * ((r.lt25 + r.lt50) * means[planform.ref_axis_pct]
                            - r.lt25 * means[X25_PCT] - r.lt50 * means[X50_PCT])
            got = free_torsion_total(planform, r.lt25, r.lt50,
                                     rh_scale=r.rh_scale, lh_scale=r.lh_scale)
            assert got == pytest.approx(want, rel=1e-9, abs=1e-9), \
                f"{example} {component} {r.case}"


def test_the_lt25_torsion_term_vanishes_at_a_quarter_chord_axis():
    """The reduction identity: with the LRA at 25 % chord, ``LT25`` contributes no
    torsion at all — so a tail reported about the quarter chord reproduces the
    original suite's reference exactly, as the wing's LRA transfer does."""
    project = _project("ga6_normal.project.json", weight=0.0)
    planform = resolve_tail_planform(project, HTAIL)
    assert planform.ref_axis_pct == pytest.approx(X25_PCT)
    assert free_torsion_total(planform, 1000.0, 0.0) == pytest.approx(0.0, abs=1e-9)
    # ...and LT50 alone does not vanish, so the test above is not vacuous.
    assert free_torsion_total(planform, 0.0, 1000.0) != pytest.approx(0.0, abs=1.0)


def test_an_offset_lra_moves_the_torsion_by_the_stated_lever():
    """Shifting the LRA aft by a fraction of chord moves the torsion by exactly
    ``L · Δpct · c`` — the statics of moving a moment reference, on a rectangle
    where the lever is the same at every station."""
    project = _project("ga6_normal.project.json", weight=0.0)
    planform = resolve_tail_planform(project, HTAIL)
    chord = planform.chord(planform.span / 2.0)
    base = free_torsion_total(planform, 900.0, -400.0)
    planform.ref_axis_pct = X25_PCT + 0.20
    moved = free_torsion_total(planform, 900.0, -400.0)
    assert moved - base == pytest.approx((900.0 - 400.0) * 0.20 * chord, rel=1e-9)


# --------------------------------------------------------------------------- #
# Inertia -- decision T-9's sign, which is the one worth a dedicated gate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_inertia_sums_to_minus_n_times_the_surface_weight(example):
    """Σ bending inertia = ``−n_normal·W_surf``, on each surface's own axis.

    The normal-direction factor is the vertical ``n_case`` for the h-tail and the
    lateral ``n_y`` for the fin — the distinction the fin's inertia turns on, and
    the one a single shared ``n`` would silently get wrong.
    """
    for r in _results(example):
        if not r.inertia_modelled:
            assert inertia_total(r) == 0.0
            continue
        n = r.n_y if r.component == VTAIL else r.n_case
        assert inertia_total(r) == pytest.approx(-n * _TAIL_WEIGHT, rel=1e-12)
        assert sum(st.fz for st in r.stations) == pytest.approx(
            air_total(r) + inertia_total(r), rel=1e-9, abs=1e-9)


def test_the_inertia_sign_is_dalembert_not_load_opposing():
    """A **down**-load h-tail case must come out LARGER in magnitude with inertia.

    This is decision T-9 made testable. The intuition "inertia relieves the air
    load" is wrong for a tail: the sign is set by the load factor alone, so on a
    positive-``n`` case the tail's own mass pulls *down* — adding to a down-load
    condition. The GA6 conditions that size the h-tail are exactly those
    (``UNCHECKED MAN DN``), so the opposing rule would have relieved the governing
    case, which is the unconservative direction.
    """
    with_mass = {r.case: r for r in _results("ga6_normal.project.json")}
    air_only = {r.case: r for r in _results("ga6_normal.project.json", weight=0.0)}
    down = "UNCHECKED MAN DN"
    net = sum(st.fz for st in with_mass[down].stations)
    air = sum(st.fz for st in air_only[down].stations)
    assert air < 0.0, "the case is expected to be a down-load one"
    assert abs(net) > abs(air), (
        f"inertia relieved a down-load case ({net:.1f} against {air:.1f}) -- the "
        "T-9 d'Alembert sign has been replaced by a load-opposing rule")
    assert net == pytest.approx(air - with_mass[down].n_case * _TAIL_WEIGHT, rel=1e-9)


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_fin_lateral_inertia_is_exactly_the_weight_ratio_of_the_air_load(example):
    """**The fin gate.** Σ inertia / Σ air ≡ ``−W_vt/W_case``, to machine zero.

    This is what makes the new lateral term self-checking, and it is a real check
    rather than a restatement: the left side comes out of the strip quadrature
    (chord-proportional areas summed over the planform) and the right side is two
    scalars the quadrature never touches. ``n_y = Fy/W_case`` cancels the air load
    out of the ratio entirely — so the identity holds on a rudder-kick case and a
    side-gust case alike, and it fails the moment anyone reaches for ``n_case``
    (vertical) where the fin's lateral factor belongs.

    The relief is also the number a reviewer should see: 0.68 % on ga6's fin,
    and it is *unconservative*, which is exactly why it is pinned.
    """
    for r in _results(example):
        if r.component != VTAIL or not r.inertia_modelled:
            continue
        assert r.case_weight_lb > 0.0
        got = sum(st.fz for st in r.stations)
        want = air_total(r) * (1.0 - _TAIL_WEIGHT / r.case_weight_lb)
        assert got == pytest.approx(want, rel=1e-12), f"{example} {r.case}"


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_fin_axial_column_is_minus_nz_times_the_surface_weight(example):
    """Σ ``f_span`` = ``−n_z·W_vt`` on the fin, and identically zero elsewhere.

    The term that exists *because* the fin spans in Z: the vertical acceleration
    that bends a horizontal tail compresses a vertical one. It must also make no
    bending — an axial load has no moment about its own line of action — so the
    root bending is asserted to be the air+lateral value with the axial column
    present, not something the axial term has leaked into.
    """
    for r in _results(example):
        axial = sum(st.f_span for st in r.stations)
        if r.component != VTAIL or not r.inertia_modelled:
            assert axial == 0.0, f"{example} {r.component} carries an axial term"
            continue
        assert axial == pytest.approx(-r.n_case * _TAIL_WEIGHT, rel=1e-12)
        assert r.stations[root_index(r)].s_span == pytest.approx(axial, rel=1e-12)
        # No bending from it: the normal-direction closure still holds exactly.
        assert sum(st.fz for st in r.stations) == pytest.approx(
            air_total(r) + inertia_total(r), rel=1e-12)


def test_a_fin_case_with_no_vn_point_gets_no_lateral_inertia_and_says_so():
    """No V-n point means no case weight, so ``n_y`` has no denominator.

    The alternative — falling back to a gross-weight stand-in — would put a
    number nobody entered into a structural load. It reports instead.
    """
    p = _project("ga6_normal.project.json")
    for cond in p.envelope.critical.conditions:
        if cond.component == VTAIL:
            cond.case = None
    for r in build_tail_span(p)[VTAIL]:
        assert r.n_y == 0.0 and r.case_weight_lb == 0.0
        assert inertia_total(r) == 0.0
        assert any("no V-n point" in n for n in r.notes)
        # The axial term survives: it needs no case weight, only the load factor.
        assert sum(st.f_span for st in r.stations) == pytest.approx(
            -r.n_case * _TAIL_WEIGHT, rel=1e-12)


#: The fin's height above the airplane CG, per fixture. This is the quantity
#: B8a-1 exists for: the roll moment a fin side load makes about the CG is
#: ``-Fy*(z - z_cg)``, so the sign of this number is the sign of that moment.
_FIN_ROLL_ARM = {
    "ga6_normal.project.json": (107.0, 93.0, +14.0),
    "concept_regional_jet.project.json": (156.0, 70.0, +86.0),
}


@pytest.mark.parametrize("example", sorted(_FIN_ROLL_ARM))
def test_the_fin_sits_above_the_cg_with_the_pinned_roll_arm(example):
    """B8a-1's acceptance (plan 13 §5.1).

    Before this step ``tail_span`` passed ``z_offset = 0`` for the v-tail while
    computing the fin root and discarding it, so every fin was modelled on the
    waterline datum: ``ga6_normal``'s load centroid sat at ``z = 28.5`` against a
    CG at 93 — **64.5 in below it** — and the RJ's landed within 1 in of its CG.
    Both gave a roll moment that was wrong, and ga6's was wrong in sign.

    A fin is above the CG. That is what this asserts, and it is deliberately a
    *sign* assertion as well as a value one.
    """
    want_zc, want_zcg, want_arm = _FIN_ROLL_ARM[example]
    project = _project(example, weight=0.0)
    vn = {p.case: p for p in project.envelope.vn}
    cgs = {c.name: c for c in project.flight_loads.cg_cases}
    conditions = {c.label: c for c in project.envelope.critical.conditions
                  if c.component == VTAIL}

    planform = resolve_tail_planform(project, VTAIL)
    for r in build_tail_span(project)[VTAIL]:
        # A v-tail station carries the fin root in ``z`` and the span coordinate
        # in ``y``; the airplane waterline is composed by the export mapper, so
        # this asserts the number the deck's GRID cards actually get.
        z = [tail_station_to_airplane(s.x, s.y, VTAIL, s.z)[2] for s in r.stations]
        assert min(z) > planform.root_z, "stations start outboard of the root"
        assert max(z) < planform.root_z + planform.span

        total = sum(s.fz for s in r.stations)
        z_centroid = sum(s.fz * zi for s, zi in zip(r.stations, z)) / total
        z_cg = cgs[vn[conditions[r.case].case].cg].zcg
        assert z_centroid == pytest.approx(want_zc, rel=1e-6)
        assert z_cg == pytest.approx(want_zcg, rel=1e-9)
        assert z_centroid - z_cg == pytest.approx(want_arm, rel=1e-6)
        assert z_centroid > z_cg, (
            f"{example} {r.case}: the fin is modelled BELOW the CG "
            f"({z_centroid:.1f} against {z_cg:.1f}), which reverses the sign of "
            "the roll moment its side load makes")


# --------------------------------------------------------------------------- #
# Topology (T-8) and provenance
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", EXAMPLES)
def test_the_htail_table_is_full_span_and_the_vtail_single_sided(example):
    project = _project(example, weight=0.0)
    spans = build_tail_span(project)
    for r in spans[HTAIL]:
        planform = resolve_tail_planform(project, HTAIL)
        assert len(r.stations) == 2 * max(2, planform.elements)
        assert min(st.y for st in r.stations) < 0 < max(st.y for st in r.stations)
        assert len(r.attachment_y) == 2 and r.attachment_y[0] < 0 < r.attachment_y[1]
    for r in spans[VTAIL]:
        assert all(st.y > 0 for st in r.stations)
        assert r.attachment_y == []


def test_the_attachment_stations_follow_the_fuselage_when_it_is_known():
    """The supports are the fuselage sides where that width exists, and the
    centreline pair — stated, not silent — where it does not."""
    project = _project("ga6_normal.project.json", weight=0.0)
    planform = resolve_tail_planform(project, HTAIL)
    assert project.geometry.parametric.fuselage_width in (None, 0, 0.0)
    ds = planform.span / planform.elements
    assert attachment_stations(project, planform) == pytest.approx([-ds / 2, ds / 2])

    project.geometry.parametric.fuselage_width = 40.0
    assert attachment_stations(project, planform) == pytest.approx([-20.0, 20.0])


@pytest.mark.parametrize("example", EXAMPLES)
def test_every_result_names_its_torsion_axis_and_its_provenance(example):
    """Every torsion names its axis, and a derived planform says it is derived."""
    for r in _results(example):
        assert r.torsion_axis.startswith("LRA ")
        assert r.planform_assumed
        assert any("DERIVED" in n for n in r.notes)
        assert r.case_ref is not None and r.safety_factor > 0


@pytest.mark.parametrize("example", EXAMPLES)
def test_the_spanwise_and_chordwise_views_cover_the_same_conditions(example):
    """The two tail views are the same conditions seen two ways; a condition that
    appears in one and not the other is a routing defect, not a modelling choice."""
    from sloads.modules.taildist import build_tail_chordwise

    project = _project(example, weight=0.0)
    spans = build_tail_span(project)
    chord_cases = {(r.component, r.case) for r in build_tail_chordwise(project)}
    span_cases = {(r.component, r.case) for r in spans[HTAIL] + spans[VTAIL]}
    assert span_cases == chord_cases, example


# --------------------------------------------------------------------------- #
# An entered (tapered, swept) planform -- the path the fixtures do not exercise
# --------------------------------------------------------------------------- #
def _tapered_project():
    project = _project("ga6_normal.project.json", weight=0.0)
    b, c_r, c_t = 73.1, 48.0, 24.0
    project.tail_loads.htail_area_sqft = 2.0 * 0.5 * (c_r + c_t) * b / 144.0
    project.tail_loads.htail_semispan_in = b
    project.geometry.surfaces.append(SurfaceInput(
        name=HTAIL,
        leading_edge=[(200.0, 0.0), (215.0, b)],      # swept
        trailing_edge=[(200.0 + c_r, 0.0), (215.0 + c_t, b)],
        elements=12, ref_axis_pct=0.40))
    return project


def test_a_tapered_swept_planform_still_closes():
    """The closures are not properties of the rectangle.

    The shipped fixtures all take the derived rectangular planform, so without
    this the gates would only ever have seen a constant chord and no sweep — and
    the torsion transfer term, which is identically zero there, would go
    unchecked.
    """
    project = _tapered_project()
    planform = resolve_tail_planform(project, HTAIL)
    assert not planform.assumed
    results = build_tail_span(project)[HTAIL]
    assert results
    for r in results:
        assert sum(st.fz for st in r.stations) == pytest.approx(air_total(r), rel=1e-9)
        # Bending against the tapered centroid, which is *not* b/2 here.
        ybar = half_area_centroid(planform)
        assert ybar < 0.48 * planform.span, "the test planform should be tapered"
        right = [st for st in r.stations if st.y > 0]
        root = min(right, key=lambda st: abs(st.y))
        want = r.rh_scale * 0.5 * (r.lt25 + r.lt50) * ybar
        assert root.mxx + root.sz * abs(root.y) == pytest.approx(want, rel=1e-6)


def test_sweep_puts_a_transfer_term_in_the_cumulative_torsion():
    """On a swept surface the cumulative torsion is **not** the free-torsion sum.

    ``myy`` accumulates the sweep transfer of outboard shear, exactly as
    ``airloads`` does — the same distinction the balanced-case work had to make
    for the wing (a cumulative torsion is not a free moment). Pinned so the two
    quantities never get conflated here either.
    """
    project = _tapered_project()
    planform = resolve_tail_planform(project, HTAIL)
    r = build_tail_span(project)[HTAIL][0]
    root = r.stations[root_index(r)]
    free_half = 0.5 * free_torsion_total(planform, r.lt25, r.lt50)
    assert root.myy != pytest.approx(free_half, rel=1e-3), \
        "a swept planform's cumulative torsion should differ from the free sum"


# --------------------------------------------------------------------------- #
# T5 -- the control-surface load mode
# --------------------------------------------------------------------------- #
def test_the_smeared_mode_is_the_default_and_changes_nothing():
    """T5's gate: smeared output is **bit-identical** to T2's.

    The mode is a statement about what the numbers mean, not a transformation of
    them -- ``LT50`` *is* the camber/elevator load and it was already distributed
    with the rest. Pinning the identity is what makes T6's ``"discrete"`` mode a
    provable change rather than an unmeasured one.
    """
    from dataclasses import asdict

    plain = _results("ga6_normal.project.json")
    project = _project("ga6_normal.project.json")
    for tm in project.tail_mass:
        tm.control_load_mode = "smeared"
    tagged = build_tail_span(project)
    tagged = tagged[HTAIL] + tagged[VTAIL]

    assert [r.control_load_mode for r in plain] == ["smeared"] * len(plain)
    for a, b in zip(plain, tagged):
        assert [asdict(st) for st in a.stations] == [asdict(st) for st in b.stations]


def test_the_discrete_mode_refuses_rather_than_falling_back():
    """``"discrete"`` needs hinge/actuator geometry the schema does not carry yet.

    Refused, loudly. A silent downgrade to ``"smeared"`` would hand back a deck
    that says one thing about the load path and contains another -- and the whole
    reason to select ``"discrete"`` is to see the load concentrated at the hinges.
    """
    project = _project("ga6_normal.project.json")
    project.tail_mass[0].control_load_mode = "discrete"
    with pytest.raises(MissingInputError, match="hinge and actuator"):
        build_tail_span(project)


def test_an_unknown_mode_raises():
    project = _project("ga6_normal.project.json")
    project.tail_mass[0].control_load_mode = "sideways"
    with pytest.raises(ValueError, match="unknown control_load_mode"):
        build_tail_span(project)


def test_the_deck_states_the_mode():
    """The deck says which load path it contains -- T5's other gate."""
    from sloads.export import sbeam_bridge as sb

    results = build_tail_span(_project("ga6_normal.project.json"))[HTAIL]
    text = sb.tail_span_force_moment_cards(results, component=HTAIL)
    assert "Control-surface load: SMEARED into this surface." in text


# --------------------------------------------------------------------------- #
# The surface weight comes from the mass SSOT (the defect this step closed)
# --------------------------------------------------------------------------- #
#: What each fixture's empennage weighs according to the ``htail``/``vtail``-tagged
#: rows of its weight data base. Pinned here, from the fixtures, because the
#: defect being guarded is precisely that these numbers existed all along and
#: never reached the distribution. ``concept_heavy`` has no v-tail-tagged item —
#: kept in the table as ``None``, since "no data" is a different state from
#: "weighs nothing" and the code has to say which.
_DERIVED_TAIL_WEIGHT = {
    "ga6_normal.project.json": (42.0, 23.0),
    "cessna_210.project.json": (45.0, 25.0),
    "atr42_100.project.json": (320.0, 270.0),
    "dhc8_dash8.project.json": (350.0, 300.0),
    "concept_regional_jet.project.json": (520.0, 640.0),
    "concept_heavy.project.json": (400.0, None),
}


@pytest.mark.parametrize("example", sorted(_DERIVED_TAIL_WEIGHT))
def test_the_surface_weight_is_derived_from_the_tagged_items(example):
    """No ``tail_mass`` entered, and the distribution still carries the mass."""
    from sloads.mass_distribution import derived_tail_surface_weight, tail_surface_weight

    p = io.load_project(os.path.join(_ROOT, "examples", example))
    assert not p.tail_mass, f"{example} now enters a tail mass -- update this gate"
    h_want, v_want = _DERIVED_TAIL_WEIGHT[example]
    assert tail_surface_weight(p, HTAIL) == pytest.approx(h_want)
    assert derived_tail_surface_weight(p, HTAIL) == pytest.approx(h_want)
    assert tail_surface_weight(p, VTAIL) == pytest.approx(v_want or 0.0)


@pytest.mark.parametrize("example", EXAMPLES)
def test_no_shipped_fixture_produces_an_air_only_htail_deck(example):
    """The regression gate for the defect itself.

    Before this step ``tail_span`` read only the entered ``tail_mass``, no fixture
    set one, and **every h-tail deck the suite shipped was air-only** — an
    omission that announced itself in a note and in no number. This asserts the
    omission cannot come back silently: on the shipped file, untouched, every
    h-tail result carries a real weight and a non-zero inertia.
    """
    p = io.load_project(os.path.join(_ROOT, "examples", example))
    p.envelope = build_envelope(p)
    results = build_tail_span(p)[HTAIL]
    assert results, example
    for r in results:
        assert r.surface_weight_lb > 0.0, f"{example} {r.case} has no surface mass"
        assert r.inertia_modelled and inertia_total(r) != 0.0
        assert not any("air load only" in n for n in r.notes)


def test_an_entered_weight_is_an_override_and_is_reconciled():
    """Entered beats derived only when marked, and the gap is always reported."""
    from sloads.mass_distribution import tail_reconciliation, tail_surface_weight
    from sloads.models import TailMassInput as _TMI

    p = io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    # Entered but not marked: the SSOT still wins, and the difference is reported.
    p.tail_mass = [_TMI(surface=HTAIL, panel_weight_lb=60.0)]
    assert tail_surface_weight(p, HTAIL) == pytest.approx(42.0)
    check = tail_reconciliation(p, HTAIL)
    assert check is not None and not check.ok
    assert check.got == 60.0 and check.want == pytest.approx(42.0)
    assert "derived value is what the distribution uses" in check.detail
    # Marked: the user's number wins, and the report says which one is in use.
    p.tail_mass[0].weight_is_override = True
    assert tail_surface_weight(p, HTAIL) == pytest.approx(60.0)
    assert "explicit override" in tail_reconciliation(p, HTAIL).detail


def test_an_untagged_surface_says_so_rather_than_reporting_zero():
    """A surface with no tagged item is an omission in the data, and is named."""
    from sloads.mass_distribution import untagged_tail_surfaces

    p = io.load_project(os.path.join(_ROOT, "examples", "concept_heavy.project.json"))
    assert untagged_tail_surfaces(p) == [VTAIL]
    p2 = io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    assert untagged_tail_surfaces(p2) == []


def test_the_override_flag_round_trips_and_an_old_file_keeps_its_weight():
    """Schema + migration: v43 entered weights survive as explicit overrides."""
    from sloads.migrations import migrate

    p = io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    p.tail_mass = [TailMassInput(surface=HTAIL, panel_weight_lb=99.0,
                                 weight_is_override=True)]
    back = io.project_from_dict(io.project_to_dict(p))
    assert back.tail_mass == p.tail_mass

    old = {"schema_version": 43, "name": "x",
           "tail_mass": [{"surface": HTAIL, "panel_weight_lb": 99.0},
                         {"surface": VTAIL, "panel_weight_lb": 0.0}]}
    hopped = migrate(old)["tail_mass"]
    assert hopped[0]["weight_is_override"] is True, "an entered weight was discarded"
    assert "weight_is_override" not in hopped[1], "a zero weight was pinned as an override"


def test_the_deck_states_its_inertia_basis():
    """The deck's own text says whether inertia is in the numbers, and how much."""
    from sloads.export import sbeam_bridge as sb

    p = io.load_project(os.path.join(_ROOT, "examples", "ga6_normal.project.json"))
    p.envelope = build_envelope(p)
    spans = build_tail_span(p)
    h_text = sb.tail_span_force_moment_cards(spans[HTAIL], component=HTAIL)
    assert "Surface mass 42.0 lb: inertia" in h_text
    assert "NO INERTIA" not in h_text
    v_text = sb.tail_span_force_moment_cards(spans[VTAIL], component=VTAIL)
    assert "Surface mass 23.0 lb: inertia" in v_text
    assert "AXIAL along the fin's" in v_text


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
