"""Single-source geometry + power derivations (Step M2-6).

The wing scalars ``FlightLoadsInput.mac``/``wing_area_sqft``/``xw``/``zw``,
``WingMassInput.dihedral_deg``/``wrp_waterline`` and ``LandingInput.wing_area_sqft``
are derived from ``Project.geometry``; the fuselage ``LayoutInput`` length/width/height
are a derived summary of the ``GeometryInput.fuselage`` outline; and the weight-estimate
``max_continuous_hp`` is single-sourced from the engine list. These tests lock in the
derivation, the no-persistence/no-op-round-trip acceptance, and the no-geometry fallback.
"""

import ast
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from sloads import Project, UnitSystem, io
from sloads.constants import DEFAULT_FRONT_SPAR_PCT, DEFAULT_REAR_SPAR_PCT
from sloads.derived_geometry import (
    SOB_ENTERED,
    SOB_HALF_WIDTH,
    carry_through,
    default_spar_station,
    fuselage_summary,
    mac_reference,
    pct_mac_to_station,
    require_integrable_planform,
    require_mac_reference,
    require_wing_reference,
    sob_station,
    station_to_pct_mac,
    sync_geometry_derived,
    wing_plane,
    wing_reference,
)
from sloads.models import (
    EngineInput,
    FlightLoadsInput,
    FuselageOutline,
    FuselageSection,
    GeometryInput,
    LandingInput,
    MissingInputError,
    SurfaceInput,
    WeightEstimationInput,
    WeightInput,
    WingMassInput,
)
from sloads.modules.weight_estimate import (
    engine_list_max_continuous_hp,
    resolve_max_continuous_hp,
    resolve_max_continuous_hp_for,
)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_HEAVY = os.path.join(_EXAMPLES, "concept_heavy.project.json")


def test_wing_reference_derives_from_ga6_geometry():
    """Appendix A wing: MAC 69.246, XLEMAC 63.641; XW = XLEMAC + 0.25*MAC and
    ZW = wrp + Y_MAC*tan(dihedral) (78.5 + Y_MAC*tan(6 deg) ~= 87.73)."""
    wr = wing_reference(io.load_project(_GA), "wing")
    assert wr is not None
    assert math.isclose(wr.mac, 69.246, rel_tol=1e-3)
    assert math.isclose(wr.s_sqft, 184.125, rel_tol=1e-3)
    assert math.isclose(wr.xw, 80.953, rel_tol=1e-3)
    assert math.isclose(wr.zw, 87.734, rel_tol=1e-3)
    assert math.isclose(wr.dihedral_deg, 6.0)
    assert math.isclose(wr.wrp_waterline, 78.5)


def test_every_wing_resolver_answers_from_the_one_source():
    """Note 33 (DS-2), replacing "sync fills the derived slices".

    There are no derived slice copies left to fill: the scalars that used to be
    written onto ``flight_loads`` and ``wing_mass`` are read through the
    resolvers instead. What is worth asserting is that the resolvers are views of
    one computation rather than three re-derivations that could drift — which is
    the property the copies never had.
    """
    p = io.load_project(_GA)
    wr = wing_reference(p, "wing")
    assert require_wing_reference(p, "wing") == wr
    assert wing_plane(p, "wing") == (wr.wrp_waterline, wr.dihedral_deg)
    # And the slices genuinely no longer carry them.
    for name in ("mac", "wing_area_sqft", "xw", "zw"):
        assert not hasattr(p.flight_loads, name)
    for name in ("dihedral_deg", "wrp_waterline"):
        assert not hasattr(p.wing_mass, name)
    assert not hasattr(p.landing, "wing_area_sqft")
    for name in ("main_gear", "nose_gear", "tread_in"):
        assert not hasattr(p.landing, name)


def test_wing_scalars_not_persisted_and_round_trip_is_noop():
    """Acceptance: no wing geometric quantity is stored as an independently editable
    copy; the serialized dict is byte-stable across save->reload."""
    p = io.load_project(_GA)
    d1 = io.project_to_dict(p)
    for key in ("mac", "wing_area_sqft", "xw", "zw"):
        assert key not in d1["flight_loads"]   # note 33: not fields at all any more
    for key in ("dihedral_deg", "wrp_waterline"):
        assert key not in d1["wing_mass"]   # note 33: not fields at all any more
    assert "wing_area_sqft" not in d1.get("landing", {})
    # Reload -> re-serialize is a no-op.
    d2 = io.project_to_dict(io.project_from_dict(d1))
    assert d1 == d2


def test_no_geometry_leaves_explicit_slice_values_untouched():
    """The STRSPEED fallback: a directly-constructed project with no wing surface
    keeps whatever the slice carries (sync is a no-op) -- so bare unit tests that set
    fl.xw/zw or wm.dihedral directly still work."""
    p = Project(name="bare",
                flight_loads=FlightLoadsInput(),
                wing_mass=WingMassInput(),
                landing=LandingInput())
    sync_geometry_derived(p)
    # The wing plane has no slice copy to keep (note 33, DS-1/DS-3): with no
    # parametric wing it degrades to the centreline plane, which is what the
    # removed fields defaulted to -- an absent plane, not a remembered one.
    assert wing_plane(p, "wing") == (0.0, 0.0)


def test_fuselage_summary_derives_from_outline():
    outline = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=0.0, height=0.0),
        FuselageSection(x=120.0, width=48.0, height=52.0),
        FuselageSection(x=300.0, width=6.0, height=9.0),
    ])
    assert fuselage_summary(outline) == (300.0, 48.0, 52.0)
    assert fuselage_summary(None) is None
    assert fuselage_summary(FuselageOutline(sections=[])) is None


# --------------------------------------------------------------------------- #
# Wing carry-through (Ref 1 Ch 15 p103 fuselage moment closure, M4-1)
# --------------------------------------------------------------------------- #
def _wing_project(front=None, rear=None, *, root_le=45.0, root_te=146.0):
    """A minimal project whose wing root chord runs ``root_le`` -> ``root_te``.

    ``front``/``rear`` are **fuselage stations** since v61 (note 50 OR-121), not
    chord fractions.
    """
    wing = SurfaceInput(name="wing",
                        leading_edge=[(root_le, 0.0), (root_le + 20.0, 100.0)],
                        trailing_edge=[(root_te, 0.0), (root_te + 5.0, 100.0)],
                        front_spar_x_in=front, rear_spar_x_in=rear)
    return Project(name="ct", geometry=GeometryInput(surfaces=[wing]))


def test_carry_through_from_entered_spar_stations():
    """An entered station is used as given -- it is the datum, not a derivation."""
    ct = carry_through(_wing_project(63.5, 108.0))         # c_root = 101 in
    assert ct is not None and not ct.assumed
    assert math.isclose(ct.x_f, 63.5) and math.isclose(ct.x_r, 108.0)
    assert math.isclose(ct.d, 44.5)
    # The fractions are reported back *from* the stations (note 50 OR-121).
    assert math.isclose(ct.front_pct, (63.5 - 45.0) / 101.0)
    assert math.isclose(ct.rear_pct, (108.0 - 45.0) / 101.0)


def test_an_entered_station_off_the_root_chord_is_not_clamped():
    """A real spar may sit forward of the root LE on a swept wing. The station is
    honoured and the reported fraction goes negative, which is the honest
    statement -- clamping would hide the geometry the station exists to carry."""
    ct = carry_through(_wing_project(40.0, 108.0))
    assert ct is not None and math.isclose(ct.x_f, 40.0) and ct.front_pct < 0.0


def test_carry_through_defaults_are_flagged_assumed():
    """An unentered station is derived from the estimator and flags the result --
    an assumed spar location must never be reported as entered input (M4-1
    decision 2; note 50 OR-126)."""
    ct = carry_through(_wing_project())
    assert ct is not None and ct.assumed
    assert math.isclose(ct.x_f, 45.0 + DEFAULT_FRONT_SPAR_PCT * 101.0)   # 65.2
    assert math.isclose(ct.x_r, 45.0 + DEFAULT_REAR_SPAR_PCT * 101.0)    # 105.6
    assert math.isclose(ct.front_pct, DEFAULT_FRONT_SPAR_PCT)
    assert math.isclose(ct.rear_pct, DEFAULT_REAR_SPAR_PCT)
    # One entered, one absent is still 'assumed' -- the pair is only as good as
    # its weaker half -- and the entered half is still honoured.
    half = carry_through(_wing_project(front=63.5))
    assert half.assumed and math.isclose(half.x_f, 63.5)
    assert math.isclose(half.x_r, 45.0 + DEFAULT_REAR_SPAR_PCT * 101.0)
    assert carry_through(_wing_project(rear=108.0)).assumed


def test_the_estimator_has_one_owner():
    """``default_spar_station`` is what ``carry_through`` falls back to *and*
    what the geometry page's caption shows (note 50 OR-123, G-OR-78's other
    half). Asserting they agree is what stops the caption drifting from the
    analysis: a second copy of ``x_LE + pct * c_root`` anywhere is a caption
    that can quietly stop describing the number in use."""
    p = _wing_project()
    surf = p.geometry.by_name("wing")
    ct = carry_through(p)
    assert math.isclose(default_spar_station(surf), ct.x_f)
    assert math.isclose(default_spar_station(surf, rear=True), ct.x_r)
    # It answers None on the geometry carry_through refuses, so the caption says
    # "cannot answer yet" instead of showing a number nothing will use.
    assert default_spar_station(None) is None
    assert default_spar_station(
        SurfaceInput(name="wing", leading_edge=[], trailing_edge=[])) is None


def test_carry_through_none_when_underivable():
    """No geometry / no wing / degenerate root chord / inverted spars -> None, so
    body_loads takes its flagged whole-body fallback rather than a bogus x_f/x_r."""
    assert carry_through(Project(name="bare")) is None
    assert carry_through(_wing_project(), "no_such_surface") is None
    assert carry_through(_wing_project(root_te=45.0)) is None        # c_root = 0
    assert carry_through(_wing_project(root_te=20.0)) is None        # c_root < 0
    assert carry_through(_wing_project(108.0, 63.5)) is None         # x_r <= x_f
    empty = Project(name="e", geometry=GeometryInput(
        surfaces=[SurfaceInput(name="wing", leading_edge=[], trailing_edge=[])]))
    assert carry_through(empty) is None


def test_carry_through_on_ga6_example():
    """The shipped Appendix A wing resolves on the primary path (assumed spars)."""
    ct = carry_through(io.load_project(_GA))
    assert ct is not None and ct.assumed and ct.d > 0.0


def test_spar_stations_round_trip_and_default_to_none():
    """A saved project keeps 'not entered' distinct from an entered number, and a
    file with the keys absent loads as None."""
    p = _wing_project(63.5, 108.0)
    d = io.project_to_dict(p)
    surf = d["geometry"]["surfaces"][0]
    assert (surf["front_spar_x_in"], surf["rear_spar_x_in"]) == (63.5, 108.0)
    back = io.project_from_dict(d).geometry.by_name("wing")
    assert (back.front_spar_x_in, back.rear_spar_x_in) == (63.5, 108.0)
    del surf["front_spar_x_in"], surf["rear_spar_x_in"]
    legacy = io.project_from_dict(d).geometry.by_name("wing")
    assert legacy.front_spar_x_in is None and legacy.rear_spar_x_in is None
    assert carry_through(io.project_from_dict(d)).assumed


# --------------------------------------------------------------------------- #
# Side-of-body station (step 13, decision BM-1)
# --------------------------------------------------------------------------- #
def test_sob_station_entered_wins_and_is_not_assumed():
    p = _wing_project()
    p.geometry.by_name("wing").sob_y_in = 40.0
    p.geometry.fuselage = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=10.0, height=10.0),
        FuselageSection(x=100.0, width=96.0, height=90.0),
        FuselageSection(x=300.0, width=8.0, height=9.0)])
    sync_geometry_derived(p)
    sob = sob_station(p)
    assert sob is not None and not sob.assumed
    assert sob.y == 40.0 and sob.basis == SOB_ENTERED


def test_sob_station_falls_back_to_half_the_width_marked_assumed():
    p = _wing_project()
    p.geometry.fuselage = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=10.0, height=10.0),
        FuselageSection(x=100.0, width=96.0, height=90.0),
        FuselageSection(x=300.0, width=8.0, height=9.0)])
    sob = sob_station(p)          # works un-synced too (summary fallback)
    assert sob is not None and sob.assumed
    assert math.isclose(sob.y, 48.0)
    assert sob.basis == SOB_HALF_WIDTH and "ASSUMED" in sob.note


def test_sob_station_is_none_without_a_body_and_never_the_inboard_rib():
    """BM-1's negative half: no butt line and no body -> None, and the WINGINER
    mass-panel start must never be substituted -- ``inboard_rib_y`` is a mass
    model quantity (BL 40 sits well inboard of the RJ's 52.5 in half-body)."""
    p = _wing_project()
    p.wing_mass = WingMassInput(inboard_rib_y=23.0)
    assert sob_station(p) is None
    assert sob_station(Project(name="bare")) is None
    # ``concept_heavy`` ships no fuselage data: its decks must not invent a
    # side of body. (``ga6_normal`` carried none until the Pri 1 fixture-data
    # pass, 2026-08-17, gave it the Appendix A body outline -- width 3.833 ft,
    # length 26.522 ft, height from the 17.231 sq ft frontal area as an ellipse
    # -- so it now resolves the assumed half-width like every other fixture.)
    assert sob_station(io.load_project(_HEAVY)) is None
    ga = sob_station(io.load_project(_GA))
    assert ga is not None and ga.assumed and math.isclose(ga.y, 23.0)


def test_sob_y_in_round_trips_and_defaults_to_none():
    p = _wing_project()
    p.geometry.by_name("wing").sob_y_in = 40.0
    d = io.project_to_dict(p)
    surf = d["geometry"]["surfaces"][0]
    assert surf["sob_y_in"] == 40.0
    assert io.project_from_dict(d).geometry.by_name("wing").sob_y_in == 40.0
    del surf["sob_y_in"]          # pre-v51 file: the key is absent entirely
    assert io.project_from_dict(d).geometry.by_name("wing").sob_y_in is None


def _project_with_engines(hps, *, estimate_total, override):
    engines = [EngineInput(max_cont_hp=hp) for hp in hps]
    est = WeightEstimationInput(max_continuous_hp=estimate_total,
                                override_max_continuous_hp=override, engines=len(hps))
    return Project(name="p", engines=engines, weight=WeightInput(estimation=est))


def test_power_single_sourced_from_engine_list():
    # Off: the engine-list total is used, not the (drifted) stored estimate total.
    p = _project_with_engines([270.0, 270.0], estimate_total=999.0, override=False)
    assert resolve_max_continuous_hp(p) == 540.0
    # On: the stored override total wins.
    p = _project_with_engines([270.0, 270.0], estimate_total=600.0, override=True)
    assert resolve_max_continuous_hp(p) == 600.0
    # Fallback: no engine carries a rating -> the stored total is used.
    p = _project_with_engines([None, None], estimate_total=480.0, override=False)
    assert resolve_max_continuous_hp(p) == 480.0


def test_the_two_entry_points_apply_one_precedence():
    """The input-level entry point exists so a GUI holding a detached
    ``WeightEstimationInput`` -- the form's values, before Apply writes them to the
    project -- has an owner to call (#124). It must not become a second precedence:
    the project-level function is a wrapper over it, and this pins that."""
    for hps, total, override in (([270.0, 270.0], 999.0, False),
                                 ([270.0, 270.0], 600.0, True),
                                 ([None, None], 480.0, False),
                                 ([], 300.0, False)):
        p = _project_with_engines(hps, estimate_total=total, override=override)
        assert (resolve_max_continuous_hp_for(p.weight.estimation, p.engines)
                == resolve_max_continuous_hp(p))
    # And the sum is the owner's too, so "engine list total" cannot be a third
    # spelling: the view showed ``sum(...)`` beside a rule using ``math.fsum(...)``.
    assert engine_list_max_continuous_hp([EngineInput(max_cont_hp=h)
                                          for h in (270.0, None, 130.5)]) == 400.5


def _powerplant_total(at):
    """The estimate's "Total powerplant" figure as the Weight & Mass page renders it."""
    for df in at.dataframe:
        frame = df.value
        if "Quantity" not in frame:
            continue
        row = frame[frame["Quantity"] == "Total powerplant"]
        if not row.empty:
            return float(row["Value"].iloc[0])
    raise AssertionError("the page rendered no 'Total powerplant' row")


def test_the_weight_page_reads_the_hp_owner_rather_than_its_own_copy():
    """Drift guard for the second consumer (#124).

    ``app/views/weight_mass.py`` spelled the Step M2-6 precedence again inline, over
    its own ``sum(...)`` of the engine list. Two copies of one rule, agreeing on the
    day they were written -- exactly what practice 3 forbids. The inline copy is gone
    and the page calls :func:`resolve_max_continuous_hp_for`; this fails if a copy
    comes back and answers differently, because the page's estimate is checked
    against the owner's for the engine list, not against the stored total.

    Powerplant weight is the HP-sensitive line: the installed-engine and propeller
    correlations both take the resolved power (WTESTIMA Ch 3)."""
    pytest.importorskip("streamlit.testing.v1")
    from dataclasses import replace as _replace

    from streamlit.testing.v1 import AppTest

    from sloads.modules.weight_estimate import estimate

    view = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "app", "views", "weight_mass.py")

    def rendered(project):
        at = AppTest.from_file(view, default_timeout=90)
        at.session_state["project"] = project
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        return _powerplant_total(at)

    def owner_total(project):
        est = _replace(project.weight.estimation,
                       max_continuous_hp=resolve_max_continuous_hp(project))
        return _powerplant_total_of(estimate(est))

    # The engine list disagrees with the stored estimation total, override off: the
    # engine list governs. (ga6_normal ships 265 hp in both places -- agreement is
    # what makes a duplicated rule invisible, so the fixture is pulled apart here.)
    p = io.load_project(_GA)
    p.engines[0].max_cont_hp = 400.0
    engine_led = rendered(p)
    assert math.isclose(engine_led, owner_total(p))

    # Override on: the stored total governs, and the page follows the owner there too.
    p.weight.estimation.override_max_continuous_hp = True
    stored_led = rendered(p)
    assert math.isclose(stored_led, owner_total(p))

    # The two must differ, or neither assertion above could catch a wrong precedence.
    assert engine_led != stored_led


def _powerplant_total_of(conditions):
    for cond in conditions:
        for v in cond.values:
            if v.label == "Total powerplant":
                return float(v.value)
    raise AssertionError("the estimate produced no 'Total powerplant' value")


# --- note 33 gate DG-3: one place resolves the wing area ---------------------- #


def test_no_module_integrates_the_wing_planform_behind_the_resolvers_back():
    """Gate DG-3. The defect note 33 §2.1 found had no guard, and could not have
    one while each module wrote its own precedence.

    ``landing._wing_area`` preferred its slice copy and fell back to geometry;
    ``structural_speeds._wing_area_sqft`` preferred geometry and fell back to its
    slice copy -- opposite orders for one quantity, invisible only because
    ``sync_geometry_derived`` overwrote the landing copy before the module read
    it. This asserts the shape that keeps the divergence from coming back: the
    strip integral is performed by its **producer** and read by its **owner**,
    and nowhere else.

    Two accessors were allowlisted here until #70 -- ``landing._wing_area`` and
    ``structural_speeds._wing_area_sqft`` -- on the grounds that each keeps its
    own precedence. Their precedence is a policy (LGFACTOR refuses when there is
    no planform, STRSPEED falls back to a typed field); the integral underneath
    it is not, and leaving it copied is what let ``validation`` grow a third
    version and the oracle GUI display a fourth number entirely. Policy stays
    with the caller; the arithmetic has one home. The sweep also covers all of
    ``sloads/`` rather than ``sloads/modules/`` alone -- ``validation.py`` sat
    outside the old scan and was never checked.
    """
    import ast
    import glob

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sloads")
    allowed = {"wing_geometry.py", "derived_geometry.py"}
    offenders = []
    for path in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):
        if os.path.basename(path) in allowed:
            continue
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "total_area":
                offenders.append(f"{os.path.relpath(path, root)}:{node.lineno}")
    assert not offenders, (
        "a module integrates the wing planform itself rather than reading the one "
        f"resolver -- that is how the two-precedences defect started: {offenders}"
    )


def test_the_landing_and_speeds_wing_areas_agree_on_every_fixture():
    """DG-3's numeric half: the two modules that keep their own accessor return
    the same area. Before note 33 they could not, by construction."""
    import glob

    from sloads.modules.landing import _wing_area
    from sloads.modules.structural_speeds import _wing_area_sqft

    checked = 0
    for f in sorted(glob.glob(os.path.join(os.path.dirname(_GA), "*.json"))):
        p = io.load_project(f)
        if p.landing is None or p.speeds is None:
            continue
        assert math.isclose(_wing_area(p), _wing_area_sqft(p, p.speeds),
                            rel_tol=1e-12), f
        checked += 1
    assert checked, "no fixture carried both slices -- the check proved nothing"


# --------------------------------------------------------------------------- #
# #71 (review 2026-08-22, PB-21) -- a mid-entry planform is refused, not crashed
# --------------------------------------------------------------------------- #
#: The states a planform passes through while it is being entered in the oracle
#: GUI's curve editor, each expressed as a mutation of a shipped surface. The
#: one-point edges are what ``render_curve`` persists after the first complete
#: row; ``te=le`` and ``zero span`` are what a second row looks like before its
#: butt line or its chord is typed; ``swapped`` is the edges entered the wrong
#: way round; ``dup station`` repeats a butt line, which is what ``interp_x``
#: divides by.
_MID_ENTRY = {
    "le[:1]": lambda s: setattr(s, "leading_edge", s.leading_edge[:1]),
    "te[:1]": lambda s: setattr(s, "trailing_edge", s.trailing_edge[:1]),
    "le[]": lambda s: setattr(s, "leading_edge", []),
    "te[]": lambda s: setattr(s, "trailing_edge", []),
    "te=le": lambda s: setattr(s, "trailing_edge", list(s.leading_edge)),
    "swapped": lambda s: (lambda le, te: (setattr(s, "leading_edge", te),
                                          setattr(s, "trailing_edge", le)))(
        list(s.leading_edge), list(s.trailing_edge)),
    "zero span": lambda s: (setattr(s, "leading_edge", [(p[0], 0.0) for p in s.leading_edge]),
                            setattr(s, "trailing_edge", [(p[0], 0.0) for p in s.trailing_edge])),
    "dup station": lambda s: setattr(
        s, "leading_edge", [s.leading_edge[0], s.leading_edge[0]] + list(s.leading_edge[1:])),
    "elements=1": lambda s: setattr(s, "elements", 1),
}

#: The ``effective_engine`` (note 36, OV-7) inputs that derive-by-default *through
#: the wing planform*, mapped to the blank that triggers the derive. Only LIMNZ
#: routes through geometry today -- the mass-selector derives read
#: ``weight.items`` and cannot see a planform -- but the guard below is written
#: over the mapping so that adding a field here is the whole of covering it.
_DERIVE_BY_DEFAULT_ENGINE_FIELDS = {"limit_load_factor": 0.0}


def _examples():
    import glob
    return sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json")))


@pytest.mark.parametrize("example", _examples(),
                         ids=[os.path.basename(f).split(".")[0] for f in _examples()])
def test_a_mid_entry_planform_is_refused_by_name_not_by_traceback(example):
    """Gate for #71 (PB-21), stated as the property rather than the four sites.

    Every module, on every shipped fixture, for every surface, in every state a
    planform passes through while it is being typed: the only exception allowed
    out is a ``ValueError``. That is what the oracle GUI's ``_NOT_READY`` catches
    and renders as "cannot run yet"; anything else reaches the page as a
    traceback, which is what PB-21 reported for Wing Loads.

    Written as a sweep on purpose. The finding named one site
    (``wing_geometry.interp_x`` via ``wing_inertia``); the sweep found four more
    that no one had looked at -- ``tail_geometry``'s two polyline integrals,
    reached from SELECT and the balance, and the Schrenk distribution's own copy
    of the guard, which had the point check but still divided by an area of
    zero. A per-site test would have locked in the one site and missed them.
    """
    import copy

    import sloads.modules  # noqa: F401  -- registers the modules
    from sloads import registry

    base = io.load_project(example)
    if base.geometry is None:
        pytest.skip("no geometry slice to half-enter")
    names = sorted(registry.available())
    escaped = []
    for surf in base.geometry.surfaces:
        for label, mutate in _MID_ENTRY.items():
            project = copy.deepcopy(base)
            mutate(project.geometry.by_name(surf.name))
            for name in names:
                try:
                    registry.get(name)(project)
                except ValueError:
                    pass                       # refused by name: the contract
                except Exception as exc:
                    escaped.append(f"{surf.name} {label} -> {name}: "
                                   f"{type(exc).__name__}: {exc}")
    assert not escaped, (
        "a half-entered planform reached the page as a traceback rather than a "
        f"named refusal (#71): {escaped}")


@pytest.mark.parametrize("example", _examples(),
                         ids=[os.path.basename(f).split(".")[0] for f in _examples()])
def test_a_derive_by_default_field_refuses_through_a_half_entered_planform(example):
    """#122: the sweep above, run down the *derive* path instead of the typed one.

    Every shipped fixture types its ``engines[].limit_load_factor``, so the note
    36 OV-7 derive -- blank LIMNZ -> ``design_speed_values(project).n``, added by
    C210-41 because a 0 LIMNZ silently zeroes every mount load -- was never
    walked by the sweep above. It reads the wing planform, so it is a geometry
    consumer and owes the #71 contract like any other; blanking the field in the
    test rather than in a fixture keeps that true no matter what the examples
    happen to type (and the guard survives a fixture entering the number, which
    is how #122 came to be found and then hidden again).

    Stated over the fields rather than over one field on purpose: this is a
    property of the OV-7 resolver, so a future derive-by-default input routed
    through geometry is covered the day it is added (rule 4).
    """
    import copy

    import sloads.modules  # noqa: F401  -- registers the modules
    from sloads import registry

    base = io.load_project(example)
    if base.geometry is None or not base.engines:
        pytest.skip("no geometry slice to half-enter, or no engine to blank")
    names = sorted(registry.available())
    escaped = []
    for surf in base.geometry.surfaces:
        for label, mutate in _MID_ENTRY.items():
            project = copy.deepcopy(base)
            mutate(project.geometry.by_name(surf.name))
            for eng in project.engines:
                for field, blank in _DERIVE_BY_DEFAULT_ENGINE_FIELDS.items():
                    setattr(eng, field, blank)
            for name in names:
                try:
                    registry.get(name)(project)
                except ValueError:
                    pass                       # refused by name: the contract
                except Exception as exc:
                    escaped.append(f"{surf.name} {label} -> {name}: "
                                   f"{type(exc).__name__}: {exc}")
    assert not escaped, (
        "a half-entered planform reached the page as a traceback rather than a "
        f"named refusal on the derive path (#122): {escaped}")


def test_the_limnz_derive_refuses_rather_than_resolving_to_zero():
    """The half of #122 a "no traceback escaped" sweep cannot see.

    Suppressing the planform refusal inside ``effective_engine`` also passes the
    sweep -- nothing escapes, because nothing is raised. What it leaves behind is
    LIMNZ = 0 on a half-entered wing, which is C210-41's silent zeroing of every
    mount load with no typed value on the page to show what went wrong. So the
    assertion is on the refusal itself, not merely on its type.
    """
    import copy

    from sloads.modules.engine import resolved_engines

    base = io.load_project(_GA)
    assert base.engines and base.speeds is not None
    for eng in base.engines:
        eng.limit_load_factor = 0.0

    # Intact planform: the derive resolves to the 23.337 limit, not to 0.
    from sloads.modules.structural_speeds import design_speed_values
    expected = design_speed_values(base, base.speeds).n
    assert expected > 0
    assert all(math.isclose(e.limit_load_factor, expected)
               for e in resolved_engines(copy.deepcopy(base)))

    # Half-entered planform: refused by name, naming the surface.
    for label in _MID_ENTRY:
        project = copy.deepcopy(base)
        _MID_ENTRY[label](project.geometry.by_name("wing"))
        with pytest.raises(ValueError) as exc:
            resolved_engines(project)
        assert "'wing'" in str(exc.value), f"{label}: {exc.value}"

    # No wing planform at all is *not* a refusal: STRSPEED's typed
    # ``wing_area_sqft`` fallback is live there, so the derive still answers.
    project = copy.deepcopy(base)
    project.geometry.surfaces = [s for s in project.geometry.surfaces if s.name != "wing"]
    project.speeds.wing_area_sqft = 184.125
    assert all(e.limit_load_factor > 0 for e in resolved_engines(project))


def test_the_planform_precondition_names_the_surface_and_what_is_wrong():
    """The refusal is only useful if it says which surface and which edge.

    ``_NOT_READY`` prints ``str(exc)`` alone (showing the type and a traceback is
    #73's), so the message is the whole of what the user gets.
    """
    surf = io.load_project(_GA).geometry.by_name("wing")

    def refusal(mutation):
        import copy
        s = copy.deepcopy(surf)
        _MID_ENTRY[mutation](s)
        try:
            require_integrable_planform(s)
        except ValueError as exc:
            return str(exc)
        return ""

    assert "'wing'" in refusal("le[:1]") and "LE and TE points" in refusal("le[:1]")
    assert "leading edge" in refusal("dup station"), refusal("dup station")
    assert "integration elements" in refusal("elements=1")
    assert not refusal("te=le"), "a zero-area planform is refused after the sweep, not before"


def test_every_strip_sweep_asks_the_precondition_owner():
    """Rule 3's drift guard: a new sweep must not repeat ``wing_inertia``'s omission.

    The structural mark of a strip sweep is that it interpolates an edge
    polyline -- it hands ``leading_edge``/``trailing_edge`` to ``interp_x`` (or
    ``tail_geometry._interp``), which divides by the butt-line difference of the
    segment it lands on and indexes ``pts[-2]``. Those are the entry points a
    GUI can reach with a half-entered planform. Before #71 there were five, and
    of the five two carried an inline copy of the check, one carried half of it
    and two carried nothing; the copies had already begun to differ. Anything
    that interpolates an edge asks the owner.

    Reading an *endpoint* is not a sweep and is not covered here: ``balance``
    takes ``leading_edge[-1][1]`` as a semispan and ``configuration`` reads root
    and tip stations, each behind its own emptiness check, and neither divides
    by anything the polyline controls.
    """
    import ast
    import glob

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "sloads")
    offenders = []
    for path in sorted(glob.glob(os.path.join(root, "**", "*.py"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename=path)
        interpolates_edge = any(
            isinstance(node, ast.Call)
            and any(isinstance(a, ast.Attribute)
                    and a.attr in ("leading_edge", "trailing_edge")
                    for a in node.args)
            for node in ast.walk(tree))
        if interpolates_edge and "require_integrable_planform" not in source:
            offenders.append(os.path.relpath(path, root))
    assert not offenders, (
        "a strip sweep interpolates an edge polyline without asking "
        f"`require_integrable_planform` -- that is exactly how PB-21 happened: {offenders}")


def _py_files(directory):
    """Every ``.py`` under ``directory``, skipping dot/dunder directories."""
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "__"))]
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)

# --------------------------------------------------------------------------- #
# The %MAC <-> station owner (#80, C210-13)
# --------------------------------------------------------------------------- #
def _ga6():
    return io.load_project(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "ga6_normal.project.json"))


def test_a_blank_envelope_derives_the_reference_from_the_planform():
    """The C210-13 fallback, now named by the value it returns rather than
    happening silently inside WTENV."""
    project = _ga6()
    project.weight.envelope.xlemac = None
    project.weight.envelope.mac = None
    ref = mac_reference(project)
    wing = require_wing_reference(project)
    assert ref.source == "planform"
    assert (ref.xlemac, ref.mac) == (wing.xlemac, wing.mac)


def test_a_typed_pair_overrides_the_planform_and_says_so():
    project = _ga6()
    project.weight.envelope.xlemac = 50.0
    project.weight.envelope.mac = 60.0
    ref = mac_reference(project)
    assert (ref.xlemac, ref.mac, ref.source) == (50.0, 60.0, "override")


def test_half_an_override_is_not_an_override():
    """WTENV has always required *both*; a lone XLEMAC over a planform MAC would
    be a reference no one entered."""
    for field in ("xlemac", "mac"):
        project = _ga6()
        project.weight.envelope.xlemac = None
        project.weight.envelope.mac = None
        setattr(project.weight.envelope, field, 42.0)
        assert mac_reference(project).source == "planform", field


def test_the_two_directions_are_one_relation():
    ref = mac_reference(_ga6())
    for pct in (0.0, 15.0, 25.0, 40.0, 100.0):
        assert math.isclose(station_to_pct_mac(pct_mac_to_station(pct, ref), ref), pct,
                            abs_tol=1e-9)
    assert math.isclose(pct_mac_to_station(0.0, ref), ref.xlemac)
    assert math.isclose(pct_mac_to_station(100.0, ref), ref.xlemac + ref.mac)


def test_the_report_column_and_wtenv_measure_the_same_wing():
    """The defect the consolidation closes: with a typed override, WTENV drew
    the CG-limit lines from it while the report's ``% MAC`` column read the
    planform -- two wings on one chart, with nothing on it saying so. No shipped
    example carries an override, which is why this went unseen; the test makes
    one disagree on purpose."""
    from sloads.modules.weight_envelope import envelope
    from sloads.report.content import Units, _weight_cg_figure

    project = _ga6()
    wing = require_wing_reference(project)
    project.weight.envelope.xlemac = wing.xlemac + 10.0   # deliberately disagree
    project.weight.envelope.mac = wing.mac * 1.5
    ref = mac_reference(project)
    assert ref.source == "override"

    stations = {v.key: v.value
                for r in envelope(project, project.weight.envelope) for v in r.values}
    assert math.isclose(
        station_to_pct_mac(stations["aft_gross_station"], ref),
        project.weight.envelope.aft_gross_pct_mac, abs_tol=1e-9)

    figure, table = _weight_cg_figure(project, Units(UnitSystem.IMPERIAL))
    # The chart's limit lines are the closed structural-limit polygon since note
    # 45 (they were three vertical rules before). Same invariant, new owner: its
    # corners must sit on the stations WTENV derived from the *override*, or the
    # chart and the % MAC column beside it describe two different wings again.
    polygon = next(s for s in figure.data.series if s.name == "Structural limits")
    assert math.isclose(max(polygon.x), stations["aft_gross_station"], abs_tol=1e-9)
    assert math.isclose(min(polygon.x), stations["forward_regardless_station"],
                        abs_tol=1e-9)

    station_col = table.columns.index(next(c for c in table.columns if "station" in c))
    pct_col = table.columns.index(next(c for c in table.columns if "% MAC" in c))
    for row in table.rows:
        assert math.isclose(
            float(row[pct_col]),
            station_to_pct_mac(float(row[station_col]), ref), abs_tol=0.02), row


def test_a_project_with_no_wing_and_no_override_has_no_reference():
    project = _ga6()
    project.geometry = None
    project.weight.envelope.xlemac = None
    project.weight.envelope.mac = None
    assert mac_reference(project) is None
    with pytest.raises(MissingInputError):
        require_mac_reference(project)


def test_no_second_spelling_of_the_mac_station_relation():
    """CLAUDE.md rule 3: the relation gets one owner *and* a guard. It was
    spelled three times before #80 -- WTENV's ``xlemac + pct/100*mac``, the
    report's ``(x - xlemac)/mac*100`` and ``wing_reference``'s 25%-MAC station
    -- so a fourth is the failure mode this test exists to catch. Any arithmetic
    that combines an XLEMAC-ish name with a MAC-ish name outside the owner
    module is one."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    owner = os.path.join(root, "sloads", "derived_geometry.py")
    offenders = []
    for package in ("sloads", "app", "app_shell", "oracle_app"):
        for path in _py_files(os.path.join(root, package)):
            if os.path.abspath(path) == owner:
                continue
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.BinOp):
                    continue
                names = {n.attr.lower() if isinstance(n, ast.Attribute) else n.id.lower()
                         for n in ast.walk(node)
                         if isinstance(n, (ast.Name, ast.Attribute))}
                if any("xlemac" in n for n in names) and any(
                        n == "mac" or n.endswith("_mac") or "mac" in n.split("_")
                        for n in names):
                    offenders.append(f"{os.path.relpath(path, root)}:{node.lineno}")
    assert not offenders, (
        "a second spelling of X = XLEMAC + pct/100*MAC (or its inverse) -- read "
        "`sloads.derived_geometry.mac_reference` and the two %MAC functions "
        f"instead, so a typed override cannot be honoured in one place only: {offenders}")
