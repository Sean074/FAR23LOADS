"""Tests for the project IO layer and the module registry wiring.

These exercise Phase 0's new plumbing -- project JSON load/save, the engine
module's ``run(project)`` entry point reached via the registry, and the CSV
writer -- without introducing any new physics: the loaded project must produce
exactly the same engine results as the in-code example.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import Project, io, registry  # noqa: E402
from sloads.cg_cases import flight_cases, ground_cases  # noqa: E402
from sloads.models import (  # noqa: E402
    SCHEMA_VERSION, EngineType, LoadingDefinition, MassItem, MassItemKind,
)
from sloads.validation import LANDING_CG_NAMES  # noqa: E402
from fixtures import io520bb  # noqa: E402

EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)
GA6 = os.path.join(EXAMPLES, "ga6_normal.project.json")


def test_example_project_loads():
    project = io.load_project(GA6)
    assert isinstance(project, Project)
    # The GA6 fixture is kept at the current schema (Step M2-6 re-derived its wing
    # geometry into a parametric slice and dropped the persisted derived copies).
    assert project.schema_version == SCHEMA_VERSION
    assert project.engine is not None
    assert project.engine.engine_type == EngineType.RECIPROCATING
    # Tuple coercion at the boundary (JSON arrays -> Vec3 tuples).
    assert project.engine.engine_cg == (22.0, 0.0, -10.0)
    # Phase 1: the example also carries the mass-properties (weight) slice.
    assert project.weight is not None
    assert project.weight.estimation.seats == 6
    assert len(project.weight.items) == 24


def test_loaded_project_matches_in_code_example():
    project = io.load_project(GA6)
    # The example file is the IO-520-BB used by the calc tests; loading it and
    # running it through the registry must reproduce those very results.
    result = registry.get("engine")(project)
    assert result.module == "engine"
    expected = io520bb()
    from sloads import run_all

    ref = run_all(expected)
    assert len(result.conditions) == len(ref) == 3
    for a, b in zip(result.conditions, ref):
        assert a.far_reference == b.far_reference
        for va, vb in zip(a.values, b.values):
            assert va.value == vb.value, va.label


def test_engine_is_registered():
    assert "engine" in registry.available()


def test_run_all_modules_runs_present_slices():
    # The GA6 example carries the engine, weight (incl. envelope), geometry, speeds
    # (incl. mach_limit), aero, flight-loads and wing-mass slices, so "run all" runs
    # the engine, all three mass-properties modules, wing-geometry, structural-speeds,
    # mach-limit, airloads, flight-envelope, wing-inertia, net-loads, select (which
    # builds the envelope from flight-loads) and taildist (the tail_loads/vtail_loads
    # chordwise distribution) -- skipping any module whose slice is absent via the
    # ValueError path. The aileron/flap/tab slices (Step C8) and the landing slice
    # (Step C10) run too, as does balloads (the C11 balancing-tail verification,
    # which needs the same tail_loads/flight_loads slices). Step M2-6 gave GA6 a
    # parametric wing slice (single-sourcing the derived wing geometry), so the
    # configuration module now runs as well. M2R-3 gave GA6 a fuselage_mass slice,
    # so body_loads (the Ch 15 fuselage net distribution) now runs too. Plan 11 B2
    # adds `balance`, which assembles the symmetric wing conditions into full-span
    # free-free cases -- it runs here because ga6 has a derivable payload loading
    # for every one of them.
    project = io.load_project(GA6)
    results = registry.run_all_modules(project)
    assert {r.module for r in results} == {
        "engine", "weight_estimate", "weight_onecg", "weight_envelope",
        "wing_geometry", "structural_speeds", "mach_limit", "airloads",
        "flight_envelope", "wing_inertia", "net_loads", "select", "tail_span",
        "taildist",
        "aileron", "flap", "tab", "landing", "balloads", "configuration",
        "body_loads", "balance",
    }


def test_run_all_modules_skips_missing_slices():
    # A project with only the engine slice runs the engine module alone.
    from fixtures import io520bb

    from sloads import EngineLayout

    project = Project(name="engine only", engines=[io520bb()], engine_layout=EngineLayout.SINGLE_NOSE)
    results = registry.run_all_modules(project)
    assert [r.module for r in results] == ["engine"]


def test_project_round_trip(tmp_path=None):
    project = io.load_project(GA6)
    out = os.path.join(EXAMPLES, "_roundtrip_tmp.project.json")
    try:
        io.save_project(project, out)
        again = io.load_project(out)
        assert again.name == project.name
        assert again.engine.cylinders == project.engine.cylinders
        assert again.engine.prop_cg == project.engine.prop_cg
    finally:
        if os.path.exists(out):
            os.remove(out)


def test_surface_ref_axis_pct_round_trips():
    """The LRA persists per surface; a stored 0.25 reads back as UNSET (v52).

    The pre-v52 writer emitted ``ref_axis_pct`` unconditionally, so a stored
    0.25 carries no entered-ness information -- the reader maps it to ``None``
    ("not entered", R-7c), whose effective value through ``ref_axis`` is the
    same 0.25. Any non-default value was necessarily entered and survives.
    """
    project = io.load_project(GA6)
    wing = project.geometry.by_name("wing")
    assert wing.ref_axis_pct == 0.40          # entered fixture data (R-7a)
    wing.ref_axis_pct = 0.42
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.geometry.by_name("wing").ref_axis_pct == 0.42
    # The stored-default mapping, both directions:
    wing.ref_axis_pct = 0.25
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.geometry.by_name("wing").ref_axis_pct is None
    assert again.geometry.by_name("wing").ref_axis == 0.25
    wing.ref_axis_pct = None
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.geometry.by_name("wing").ref_axis_pct is None


def test_wing_load_result_torsion_axis_round_trips():
    """A transferred result's torsion-axis stamp survives persistence."""
    from sloads.models import WingLoadResult, LoadsResult

    project = io.load_project(GA6)
    project.loads = LoadsResult(
        wing_net=[WingLoadResult(case="X", torsion_axis="LRA 40% chord")])
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.loads.wing_net[0].torsion_axis == "LRA 40% chord"
    # And the default when absent in the file:
    d = io.project_to_dict(project)
    del d["loads"]["wing_net"][0]["torsion_axis"]
    assert io.project_from_dict(d).loads.wing_net[0].torsion_axis == "25% chord"


def test_project_engineer_date_round_trip():
    """Step D3: engineer/date are additive project metadata (SCHEMA_VERSION 17)."""
    project = io.load_project(GA6)
    project.engineer = "J. Doe"
    project.date = "2026-07-09"
    d = io.project_to_dict(project)
    assert d["engineer"] == "J. Doe"
    assert d["date"] == "2026-07-09"
    again = io.project_from_dict(d)
    assert again.engineer == "J. Doe"
    assert again.date == "2026-07-09"


def test_project_engineer_date_default_blank():
    # Old files with no engineer/date key still load (additive field).
    project = io.load_project(GA6)
    assert project.engineer == ""
    assert project.date == ""
    assert "engineer" not in io.project_to_dict(project)
    assert "date" not in io.project_to_dict(project)


def test_speeds_occupants_round_trips():
    """Step E1: StructuralSpeedsInput.occupants is additive (SCHEMA_VERSION 21)."""
    project = io.load_project(GA6)
    project.speeds.occupants = 12
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.speeds.occupants == 12


def test_speeds_occupants_default_none_on_old_file():
    # An old (v20) file has no occupants key; the speeds slice loads with the
    # None default (the applicability check then falls back to weight.seats).
    project = io.load_project(GA6)
    assert project.speeds.occupants is None
    d = io.project_to_dict(project)
    assert d["speeds"].get("occupants") is None


def test_estimation_crew_round_trips():
    """Step E1 follow-up: WeightEstimationInput.crew is additive (SCHEMA_VERSION 22)."""
    project = io.load_project(GA6)
    project.weight.estimation.crew = 2
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.weight.estimation.crew == 2


def test_estimation_crew_default_on_old_file():
    # An old (< v22) file has no crew key; the estimation loads with crew = 1.
    project = io.load_project(GA6)
    assert project.weight.estimation.crew == 1


def test_weight_cg_cases_round_trips_through_io():
    """Step D5: WeightInput.cg_cases is the shared loading-scenario list the
    Weight/CG Grid page owns (SCHEMA_VERSION 19) -- and since decision G-3 the
    *only* one, each case carrying the analyses it is run for."""
    project = io.load_project(GA6)
    assert project.weight.cg_cases, "the GA6 example should carry migrated cg_cases"
    assert {c.name for c in flight_cases(project)} == {"CG1", "CG2", "CG3", "CG4"}
    assert {c.name for c in ground_cases(project)} == set(LANDING_CG_NAMES)

    d = io.project_to_dict(project)
    assert d["weight"]["cg_cases"][0]["name"] == "CG1"
    assert d["weight"]["cg_cases"][0]["analyses"] == ["flight"]
    assert "role" not in d["weight"]["cg_cases"][0], "an unset role is not written"
    again = io.project_from_dict(d)
    assert [(c.name, c.analyses, c.role) for c in again.weight.cg_cases] == \
        [(c.name, c.analyses, c.role) for c in project.weight.cg_cases]


def test_critical_load_set_selected_case_ids_round_trip():
    """Step D5: the Critical Loads page's opt-out selection persists on
    CriticalLoadSet.selected_case_ids (SCHEMA_VERSION 19); empty means no filter."""
    from sloads.models import CriticalCondition, CriticalLoadSet, EnvelopeResult

    project = io.load_project(GA6)
    critical = CriticalLoadSet(
        conditions=[CriticalCondition(component="wing", label="PHAA", case_ref=None)],
        selected_case_ids=["W-01"],
    )
    project.envelope = EnvelopeResult(critical=critical)
    d = io.project_to_dict(project)
    assert d["envelope"]["critical"]["selected_case_ids"] == ["W-01"]
    again = io.project_from_dict(d)
    assert again.envelope.critical.selected_case_ids == ["W-01"]


def test_default_projects_dir_is_repo_relative():
    projects_dir = io.default_projects_dir()
    assert os.path.basename(projects_dir) == "projects"
    repo_root = os.path.dirname(EXAMPLES)
    assert os.path.abspath(projects_dir) == os.path.join(repo_root, "projects")


def test_list_saved_projects(tmp_path=None):
    import shutil
    import tempfile
    import time

    tmpdir = tempfile.mkdtemp()
    try:
        assert io.list_saved_projects(os.path.join(tmpdir, "missing")) == []

        older = os.path.join(tmpdir, "older.project.json")
        newer = os.path.join(tmpdir, "newer.project.json")
        ignored = os.path.join(tmpdir, "notes.txt")
        for path in (older, ignored):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{}")
        time.sleep(0.01)
        with open(newer, "w", encoding="utf-8") as fh:
            fh.write("{}")

        entries = io.list_saved_projects(tmpdir)
        names = [name for name, _mtime in entries]
        assert names == ["newer.project.json", "older.project.json"]
    finally:
        shutil.rmtree(tmpdir)


def test_configuration_round_trip():
    # The parametric layout (unified onto geometry.parametric, v25) survives a
    # dict round-trip. Step M2-6: the fuselage length/width/height are a derived
    # read-only summary of the GeometryInput.fuselage outline (not persisted), so
    # the outline is the single shape source and the scalars re-derive on load.
    from sloads import FuselageOutline, FuselageSection, GeometryInput, LayoutInput

    layout = LayoutInput(
        wing_area_sqft=174.0, aspect_ratio=6.0, taper_ratio=0.6,
        le_sweep_deg=2.0, le_root_x=45.0, datum_x=0.0,
    )
    outline = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=0.0, height=0.0),
        FuselageSection(x=120.0, width=48.0, height=52.0),
        FuselageSection(x=300.0, width=6.0, height=9.0),
    ])
    project = Project(name="cfg",
                      geometry=GeometryInput(parametric=layout, fuselage=outline))
    d = io.project_to_dict(project)
    # The derived fuselage scalars are not written.
    for k in ("fuselage_length", "fuselage_width", "fuselage_height"):
        assert k not in d["geometry"]["parametric"]

    again = io.project_from_dict(d)
    par = again.geometry.parametric
    # Non-fuselage parametric fields survive unchanged.
    assert par.wing_area_sqft == 174.0 and par.le_root_x == 45.0
    # The fuselage summary is re-derived from the outline (length = station span,
    # width/height = max section).
    assert par.fuselage_length == 300.0
    assert par.fuselage_width == 48.0
    assert par.fuselage_height == 52.0


def test_c6_slices_round_trip():
    # The v7 (Step C6) slices survive a dict round-trip: the persisted mass
    # properties (WTONECG), the fuselage mass distribution, the SELECT critical
    # set on envelope.critical, and the fuselage net distribution on loads.body_net.
    from sloads.models import (
        BodyLoadResult,
        BodyStationLoad,
        CriticalCondition,
        CriticalLoadSet,
        EnvelopeResult,
        FuselageMassInput,
        FuselageStation,
        LoadsResult,
        LoadValue,
        MassCase,
        MassResult,
    )

    mass = MassResult(cases=[
        MassCase(name="aft gross", weight_lb=2576.0, cg_x=85.1, ixx=1.0e6, iyy=2.0e6,
                 izz=3.0e6, ixz=1.2e4, gear_down=False),
    ])
    fuselage_mass = FuselageMassInput(
        stations=[FuselageStation(x=20.0, weight_lb=140.0), FuselageStation(x=200.0)],
        ref_waterline=12.0,
    )
    critical = CriticalLoadSet(conditions=[
        CriticalCondition(component="wing", label="PHAA", far_reference="23.301",
                          case=22, loads=[LoadValue("CL", 1.52), LoadValue("V", 117.4, "kt")]),
        CriticalCondition(component="fuselage", label="net", far_reference="23.471"),
    ])
    envelope = EnvelopeResult(critical=critical)
    loads = LoadsResult(body_net=[
        BodyLoadResult(case="PHAA", stations=[
            BodyStationLoad(x=20.0, fx=0.0, fy=0.0, fz=100.0, sx=0.0, sy=0.0,
                            sz=100.0, mxx=0.0, myy=2000.0, mzz=0.0),
        ]),
    ])
    project = Project(name="c6", mass=mass, fuselage_mass=fuselage_mass,
                      envelope=envelope, loads=loads)
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.mass == mass
    assert again.fuselage_mass == fuselage_mass
    assert again.envelope.critical == critical
    assert again.loads.body_net == loads.body_net
    assert again.schema_version == project.schema_version


def test_safety_factor_round_trips_on_result_slices():
    """Defect M4-7: the per-case limit->ultimate factor survives save/load.

    Every case-carrying result the sbeam export scales by must persist its own
    factor -- otherwise a reloaded project silently reverts to the suite default
    and the exported cards disagree with the rendered report.
    """
    from sloads.constants import ULTIMATE_FACTOR
    from sloads.models import (
        BodyLoadResult,
        ControlSurfaceLoadResult,
        ControlSurfaceStation,
        CriticalCondition,
        CriticalLoadSet,
        EnvelopeResult,
        LoadsResult,
        TailChordResult,
        TailChordStation,
        WingLoadResult,
        WingStationLoad,
    )

    envelope = EnvelopeResult(critical=CriticalLoadSet(conditions=[
        CriticalCondition(component="htail", label="balancing", safety_factor=1.0,
                          note="already ultimate"),
    ]))
    loads = LoadsResult(
        wing_net=[WingLoadResult(case="PHAA", safety_factor=1.0, stations=[
            WingStationLoad(x=1.0, y=2.0, z=3.0, fx=1.0, fz=2.0, sx=1.0, sz=2.0,
                            mxx=3.0, myy=4.0, mzz=5.0)])],
        body_net=[BodyLoadResult(case="net", safety_factor=1.25)],
        tail_chordwise=[TailChordResult(case="balancing", component="htail", lt25=10.0,
                                        lt50=2.0, safety_factor=1.0,
                                        stations=[TailChordStation(x=0.0, psi=0.5)])],
        control_surface=[ControlSurfaceLoadResult(surface="aileron", case="down aileron",
                                                  load_lb=300.0, safety_factor=1.0,
                                                  stations=[ControlSurfaceStation(x=0.0, psi=1.0)])],
    )
    project = Project(name="m4-7", envelope=envelope, loads=loads)
    again = io.project_from_dict(io.project_to_dict(project))

    assert again.envelope.critical == envelope.critical   # incl. note + safety_factor
    assert again.loads.wing_net == loads.wing_net
    assert again.loads.body_net == loads.body_net
    assert again.loads.tail_chordwise == loads.tail_chordwise
    assert again.loads.control_surface == loads.control_surface

    # A file predating the field takes the suite default (lenient migration).
    d = io.project_to_dict(project)
    for r in d["loads"]["wing_net"]:
        r.pop("safety_factor")
    assert io.project_from_dict(d).loads.wing_net[0].safety_factor == ULTIMATE_FACTOR


def _m4_14_project_dict():
    """A persisted project with one case in every safety_factor-carrying slice."""
    from sloads.models import (
        BodyLoadResult,
        BodyStationLoad,
        ControlSurfaceLoadResult,
        ControlSurfaceStation,
        CriticalCondition,
        CriticalLoadSet,
        EnvelopeResult,
        LoadsResult,
        TailChordResult,
        TailChordStation,
        WingLoadResult,
        WingStationLoad,
    )

    envelope = EnvelopeResult(critical=CriticalLoadSet(conditions=[
        CriticalCondition(component="htail", label="balancing")]))
    loads = LoadsResult(
        wing_net=[WingLoadResult(case="PHAA", stations=[
            WingStationLoad(x=1.0, y=2.0, z=3.0, fx=1.0, fz=2.0, sx=1.0, sz=2.0,
                            mxx=3.0, myy=4.0, mzz=5.0)])],
        body_net=[BodyLoadResult(case="net", stations=[
            BodyStationLoad(x=20.0, fx=0.0, fy=0.0, fz=100.0, sx=0.0, sy=0.0,
                            sz=100.0, mxx=0.0, myy=2000.0, mzz=0.0)])],
        tail_chordwise=[TailChordResult(case="balancing", component="htail", lt25=10.0,
                                        lt50=2.0,
                                        stations=[TailChordStation(x=0.0, psi=0.5)])],
        control_surface=[ControlSurfaceLoadResult(surface="aileron", case="down aileron",
                                                  load_lb=300.0,
                                                  stations=[ControlSurfaceStation(x=0.0, psi=1.0)])],
    )
    return io.project_to_dict(Project(name="m4-14", envelope=envelope, loads=loads))


def _set_all_safety_factors(d, value):
    d["envelope"]["critical"]["conditions"][0]["safety_factor"] = value
    for family in ("wing_net", "body_net", "tail_chordwise", "control_surface"):
        for r in d["loads"][family]:
            r["safety_factor"] = value


def _all_loaded_safety_factors(d):
    p = io.project_from_dict(d)
    return ([c.safety_factor for c in p.envelope.critical.conditions]
            + [r.safety_factor for r in p.loads.wing_net + p.loads.body_net
               + p.loads.tail_chordwise + p.loads.control_surface])


def test_safety_factor_corrupt_values_coerce_to_default_on_load():
    """Defect M4-14: a corrupt persisted factor must never pass the readers.

    null crashed the export (`TypeError` out of `body_span_load_csv`); 0.5 (or any
    value below 1.0) silently under-scaled every card still labelled ULTIMATE. The
    legal band is [1.0, ULTIMATE_FACTOR], owned by the load-case definition;
    anything else falls back to the conservative default.
    """
    from sloads.constants import ULTIMATE_FACTOR

    for bad in (None, "1.25", True, float("nan"), float("inf"),
                0.5, -1.5, 0.0, 0.999, 1.6, 2.0):
        d = _m4_14_project_dict()
        _set_all_safety_factors(d, bad)
        assert _all_loaded_safety_factors(d) == [ULTIMATE_FACTOR] * 5, bad


def test_safety_factor_legal_band_loads_verbatim():
    """[1.0, 1.5] inclusive is legal (a case already at ultimate is SF=1.0)."""
    for good in (1.0, 1.25, 1.5):
        d = _m4_14_project_dict()
        _set_all_safety_factors(d, good)
        assert _all_loaded_safety_factors(d) == [good] * 5, good


def test_safety_factor_null_no_longer_crashes_the_export():
    """The exact M4-14 repro: `"safety_factor": null` then the body export."""
    from sloads.export.sbeam_bridge import body_span_load_csv

    d = _m4_14_project_dict()
    _set_all_safety_factors(d, None)
    p = io.project_from_dict(d)
    csv_text = body_span_load_csv(p.loads.body_net)   # raised TypeError before
    assert csv_text.strip().splitlines()[1].endswith("1.5")


def test_a_bare_engine_file_is_refused():
    """A pre-``Project`` file is just the engine fields at top level. It used to
    be wrapped into a project, discriminated by key-sniffing; since #93 it has no
    ``schema_version`` and so is refused like any other file this build does not
    read. The refusal is the load path's, not a special case for this shape."""
    import json
    import tempfile

    from sloads.migrations import SchemaVersionError

    payload = io.engine_to_dict(io520bb())
    with tempfile.TemporaryDirectory() as tmp:
        flat = os.path.join(tmp, "legacy.json")
        with open(flat, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        raised = False
        try:
            io.load_project(flat)
        except SchemaVersionError:
            raised = True
        assert raised, "a file with no schema_version was read anyway"


def test_csv_has_three_load_cases():
    project = io.load_project(GA6)
    result = registry.get("engine")(project)
    csv_text = io.load_cases_csv(result)
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    assert len(lines) == 1 + 3  # header + EM-01..EM-03 (Step D1 structured ids)
    assert lines[0].startswith(
        "ID,FAR,Case description,Component,Condition,CG,Speed (kt),Altitude (ft),SF,"
    )
    # Loads are reported ultimate: force/moment headers carry the ULT marker.
    assert "ULT" in lines[0]


def test_reading_a_project_dict_does_not_migrate_it():
    """``read_project_dict`` is the raw file; ``load_project`` is it plus
    ``project_from_dict``. The split is what lets a caller hold the dict the user
    actually wrote -- what the JSON editor edits, and what
    ``migrations.source_schema_version`` reads -- rather than only the built
    project."""
    import json

    with open(GA6, encoding="utf-8") as fh:
        assert io.read_project_dict(GA6) == json.load(fh)


def test_project_from_dict_raises_on_malformed():
    # A wrong-shape engine slice must raise one of the load-path's caught types,
    # not silently build a broken project (Step E5 relies on this to show st.error).
    raised = False
    try:
        io.project_from_dict({"engines": [{"engine_type": "not-a-valid-enum"}]})
    except (TypeError, ValueError, KeyError, AttributeError):
        raised = True
    assert raised


def test_a_parametric_block_defaults_the_fuselage_outline():
    """The fuselage outline is defaulted from the parametric length/width/height
    scalars, and the oracle-locked ``.surfaces`` consumers are untouched.

    Written against the current schema. It used to enter through the v25 hop from
    a pre-v25 top-level ``configuration`` block, which #93 retired -- but the
    defaulting is the reader's, not the hop's, and is what this test is about.
    """
    d = {
        "schema_version": SCHEMA_VERSION,
        "geometry": {
            "parametric": {"wing_area_sqft": 174.0, "aspect_ratio": 6.0,
                           "fuselage_length": 300.0, "fuselage_width": 48.0,
                           "fuselage_height": 54.0, "datum_x": 0.0},
            "surfaces": [{"name": "wing",
                          "leading_edge": [[0.0, 0.0], [10.0, 100.0]],
                          "trailing_edge": [[50.0, 0.0], [55.0, 100.0]]}],
        },
    }
    p = io.project_from_dict(d)
    assert p.geometry is not None
    # The parametric block arrives on the geometry slice.
    assert p.geometry.parametric is not None
    assert p.geometry.parametric.wing_area_sqft == 174.0
    # Surfaces (oracle path) preserved unchanged.
    assert [s.name for s in p.geometry.surfaces] == ["wing"]
    # Fuselage outline defaulted from the scalars: nose -> max (0.35L) -> tail.
    secs = p.geometry.fuselage.sections
    assert len(secs) == 3
    assert secs[0].x == 0.0 and secs[0].width == 0.0
    assert abs(secs[1].x - 0.35 * 300.0) < 1e-9
    assert secs[1].width == 48.0 and secs[1].height == 54.0
    # Round-trips on the geometry slice, with no top-level "configuration".
    out = io.project_to_dict(p)
    assert "configuration" not in out
    assert out["geometry"]["parametric"]["wing_area_sqft"] == 174.0
    assert len(out["geometry"]["fuselage"]["sections"]) == 3
    again = io.project_from_dict(out)
    assert again.geometry.parametric == p.geometry.parametric
    assert again.geometry.fuselage == p.geometry.fuselage


def test_explicit_fuselage_outline_round_trip_and_not_defaulted():
    """An explicit fuselage outline survives the round-trip verbatim and is NOT
    overwritten by the scalar default."""
    from sloads import FuselageOutline, FuselageSection, GeometryInput, LayoutInput

    fuse = FuselageOutline(sections=[
        FuselageSection(x=0.0, width=0.0, height=0.0),
        FuselageSection(x=120.0, width=60.0, height=66.0),
        FuselageSection(x=280.0, width=8.0, height=12.0),
    ])
    project = Project(name="f", geometry=GeometryInput(
        parametric=LayoutInput(fuselage_length=300.0, fuselage_width=48.0),
        fuselage=fuse))
    again = io.project_from_dict(io.project_to_dict(project))
    # Explicit sections preserved (not replaced by the 48-in-wide scalar default).
    assert again.geometry.fuselage == fuse


# --------------------------------------------------------------------------- #
# M2R-7: tolerant readers -- an unknown field anywhere in a project file must be
# ignored on load (forward-compat with files saved by another app version), not
# crash the ``cls(**d)`` splat with an unexpected-keyword TypeError.
# --------------------------------------------------------------------------- #
_UNKNOWN_KEY = "__unknown_future_field__"


def _inject_unknown(obj):
    """Recursively add an unknown key to every dict (at every depth, including dicts
    nested inside lists) in a serialized-project structure."""
    if isinstance(obj, dict):
        out = {k: _inject_unknown(v) for k, v in obj.items()}
        out[_UNKNOWN_KEY] = "ignore-me"
        return out
    if isinstance(obj, list):
        return [_inject_unknown(v) for v in obj]
    return obj


def test_unknown_field_in_every_ga6_slice_is_ignored():
    """The reported crash (`MassItem.__init__() got an unexpected keyword argument`)
    and its siblings: poison every slice of ga6_normal with an unknown key and assert
    the file still loads and re-serializes identically (the garbage is dropped)."""
    clean = io.project_to_dict(io.load_project(GA6))
    loaded = io.project_from_dict(_inject_unknown(clean))  # must not raise
    assert io.project_to_dict(loaded) == clean


def _augmented_project():
    """ga6 plus the *result* slices (envelope / mass / loads / one_engine_out) that the
    fixture lacks, each with nested objects (VnPoint+CaseRef, CriticalCondition+LoadValue,
    the four station-load families), so the poison test also exercises those readers."""
    from sloads.models import (
        BodyLoadResult,
        BodyStationLoad,
        CaseRef,
        ControlSurfaceLoadResult,
        ControlSurfaceStation,
        CriticalCondition,
        CriticalLoadSet,
        EnvelopeResult,
        LoadsResult,
        LoadValue,
        MassCase,
        MassResult,
        OneEngineOutInput,
        TailBalanceLoad,
        TailChordResult,
        TailChordStation,
        VnPoint,
        WingLoadResult,
        WingStationLoad,
    )

    p = io.load_project(GA6)
    ref = CaseRef("w1", "wing", "PHAA")
    p.envelope = EnvelopeResult(
        vn=[VnPoint(case="PHAA", condition="A", config="cruise", cg="fwd", altitude_ft=0.0,
                    v_eas_kt=1, nz=1, alpha_deg=1, g_corr=1, cl=1, m_wf=1, lzw=1, lt=1, dx=1,
                    case_ref=ref)],
        tail_balance=[TailBalanceLoad(case="c", condition="A", tail_load_lb=1.0,
                                      tail_cp_station=1.0, flaps_down=False)],
        critical=CriticalLoadSet(
            conditions=[CriticalCondition(component="wing", label="PHAA",
                                          loads=[LoadValue("Fz", 1.0)], case_ref=ref)],
            selected_case_ids=["w1"]),
    )
    p.mass = MassResult(cases=[MassCase("aft gross", weight_lb=3400.0)])
    p.loads = LoadsResult(
        wing_net=[WingLoadResult(case="c", stations=[WingStationLoad(*([1.0] * 10))], case_ref=ref)],
        body_net=[BodyLoadResult(case="c", stations=[BodyStationLoad(*([1.0] * 10))])],
        tail_chordwise=[TailChordResult(case="c", component="htail", lt25=1.0, lt50=1.0,
                                        stations=[TailChordStation(x=1.0, psi=1.0)])],
        control_surface=[ControlSurfaceLoadResult(surface="aileron", case="c", load_lb=1.0,
                                                  stations=[ControlSurfaceStation(x=1.0, psi=1.0)])],
    )
    p.one_engine_out = OneEngineOutInput()
    return p


def test_unknown_field_in_every_result_slice_is_ignored():
    """Same guarantee for the result slices (envelope/mass/loads/one_engine_out) and
    their nested readers, which ga6 alone does not carry."""
    clean = io.project_to_dict(_augmented_project())
    # Sanity: the augmented dict actually carries the extra slices.
    assert {"envelope", "mass", "loads", "one_engine_out"} <= set(clean)
    loaded = io.project_from_dict(_inject_unknown(clean))  # must not raise
    assert io.project_to_dict(loaded) == clean


# --------------------------------------------------------------------------- #
# D-25 -- the explicit loading definition (schema v50)
# --------------------------------------------------------------------------- #
def test_an_entered_loading_round_trips():
    """Every member survives the write/read/write cycle, ballast row included."""
    project = io.load_project(os.path.join(EXAMPLES, "concept_regional_jet.project.json"))
    case = next(c for c in project.weight.cg_cases if c.name == "fwd regardless")
    case.loading = LoadingDefinition(
        aboard=["Passengers, fwd cabin (24)", "Mission fuel"],
        fractions={"Mission fuel": 0.4},
        ballast=MassItem(name="Test ballast", weight_lb=120.0, x=200.0, z=60.0,
                         kind=MassItemKind.DISCRETIONARY),
    )
    once = io.project_to_dict(project)
    twice = io.project_to_dict(io.project_from_dict(once))
    assert once == twice

    back = next(c for c in io.project_from_dict(once).weight.cg_cases
                if c.name == "fwd regardless").loading
    assert back.aboard == ["Passengers, fwd cabin (24)", "Mission fuel"]
    assert back.fractions == {"Mission fuel": 0.4}
    assert back.ballast == case.loading.ballast


def test_a_case_without_a_loading_writes_no_loading_key():
    """D-25c: absent is the pre-v50 shape *and* the live "derive it" state, so a
    re-saved older file keeps the bytes it had."""
    project = io.load_project(GA6)
    cases = io.project_to_dict(project)["weight"]["cg_cases"]
    assert all("loading" not in c for c in cases)
    assert all(c.loading is None for c in project.weight.cg_cases)


def test_a_pre_v50_file_loads_with_no_loading():
    """The migration is "nothing to do", asserted rather than assumed: an on-disk
    case with no ``loading`` key loads, and derives its loading as it always did."""
    from sloads import mass_distribution as md

    project = io.load_project(GA6)
    assert project.schema_version <= SCHEMA_VERSION
    assert [ld.entered for ld in md.derive_case_loadings(project)] == [False] * 4


# --------------------------------------------------------------------------- #
# Numbers in, numbers stored (#76, the C210-7 residual). A grid rendered from an
# object-typed column hands back text, so a project can be *saved* with its wing
# corners as strings; until now the loader took them, and the crash landed three
# modules away as a bare ``TypeError``.
# --------------------------------------------------------------------------- #
def _as_text(node):
    """Every number that sits inside a **list** becomes text; dict scalars are
    left alone. That is exactly the damage the grid does -- a curve/point widget
    writes a list of cells -- and exactly the class the loader coerces (scalars
    are deliberately out of scope, so stringifying them would test a promise
    that was not made)."""
    if isinstance(node, dict):
        return {k: _as_text(v) for k, v in node.items()}
    if isinstance(node, list):
        return [str(x) if isinstance(x, (int, float)) and not isinstance(x, bool)
                else _as_text(x) for x in node]
    return node


def _module_values(project, name):
    result = registry.get(name)(project)
    return [(v.key, v.value) for c in result.conditions for v in c.values]


def test_a_text_polyline_loads_as_numbers_and_runs():
    """C210-7's residual, end to end: the file that crashed WINGGEOM now runs.

    ``TypeError: unsupported operand type(s) for -: 'str' and 'str'`` at
    ``ytip - yroot`` was the reported symptom; the same strings also killed
    ``to_display`` on the main GUI's layout page -- the page that would otherwise
    repair the corners -- so the loader is the only boundary that reaches both.
    """
    import json
    import warnings

    with open(GA6, encoding="utf-8") as fh:
        clean = json.load(fh)
    damaged = json.loads(json.dumps(clean))
    wing = damaged["geometry"]["surfaces"][0]
    for edge in ("leading_edge", "trailing_edge"):
        wing[edge] = [[str(x), str(y)] for x, y in wing[edge]]

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        project = io.project_from_dict(damaged)
    surface = project.geometry.surfaces[0]
    assert all(isinstance(v, float) for p in surface.leading_edge for v in p), \
        surface.leading_edge
    assert _module_values(project, "wing_geometry") == \
        _module_values(io.project_from_dict(clean), "wing_geometry")


def test_every_numeric_container_survives_a_file_written_as_text():
    """Rule-4 sweep, asserted over the whole fixture rather than the one field.

    ``leading_edge`` was where it was found, but 12 more numeric containers --
    the aero curves, three ``hinges_span_in`` (an sbeam export input), the gear
    axle points, the engine CGs -- read the same way. Only ``altitudes_ft``
    coerced. Every module must give bit-identical answers from the text file.
    """
    import json
    import warnings

    with open(GA6, encoding="utf-8") as fh:
        clean = json.load(fh)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        project = io.project_from_dict(_as_text(json.loads(json.dumps(clean))))
    assert caught, "a repaired file must say so -- the GUI shows these as toasts"

    reference = io.project_from_dict(clean)
    for name in ("structural_speeds", "wing_geometry", "airloads", "flight_envelope",
                 "balloads", "tail_span", "body_loads", "wing_inertia", "net_loads",
                 "landing", "balance", "engine", "flap", "tab", "taildist",
                 "weight_envelope", "weight_estimate"):
        assert _module_values(project, name) == _module_values(reference, name), name


def test_the_coerced_field_set_is_read_off_the_model_not_a_hand_list():
    """Rule-3 drift guard: a numeric container added tomorrow is covered today.

    The shapes come from the dataclass annotations, so this asserts the *rule*
    (every numeric container ``_filtered`` is handed arrives numeric) rather
    than a list of field names that would go stale the next time the schema
    grows one. The three paths that bypass ``_filtered`` -- the polylines, the
    engine vectors, the gear axles -- are covered end-to-end above.
    """
    import dataclasses
    import warnings

    from sloads.models import inputs as model_inputs

    sample = {"tuple": ["1", "2"], "list": ["3", "4"], "points": [["5", "6"]]}
    seen = 0
    for cls in vars(model_inputs).values():
        if not dataclasses.is_dataclass(cls):
            continue
        for field, shape in io._numeric_containers(cls).items():
            with warnings.catch_warnings():  # every sample is a repair, by design
                warnings.simplefilter("ignore")
                loaded = io._filtered(cls, {field: sample[shape]})[field]
            flat = [v for m in loaded for v in (m if isinstance(m, tuple) else [m])] \
                if shape == "points" else list(loaded)
            assert all(isinstance(v, float) for v in flat), f"{cls.__name__}.{field}"
            seen += 1
    # The resolver finding nothing would make every assertion above vacuous.
    assert seen >= 13, seen
    assert io._numeric_containers(model_inputs.SurfaceInput)["leading_edge"] == "points"


def test_an_unparseable_value_is_refused_by_name():
    """Text that is not a number is not guessed at. The message names the field
    and the member, and ``ValueError`` is one of the types the GUI load path
    already catches and shows as ``st.error`` (``project_state.safe_load``)."""
    import json

    with open(GA6, encoding="utf-8") as fh:
        damaged = json.load(fh)
    damaged["geometry"]["surfaces"][0]["leading_edge"][0][0] = "abc"
    try:
        io.project_from_dict(damaged)
    except ValueError as exc:
        assert "SurfaceInput.leading_edge[0][0]" in str(exc), str(exc)
        assert "'abc'" in str(exc), str(exc)
    else:
        raise AssertionError("a non-numeric corner must be refused, not stored")


def test_a_repair_warns_once_per_field_not_once_per_number():
    """Twenty text corners are one thing that happened, not forty. The warning
    is the #66/PB-7 load-path channel, which the GUI renders as a toast."""
    import json
    import warnings

    with open(GA6, encoding="utf-8") as fh:
        damaged = json.load(fh)
    wing = damaged["geometry"]["surfaces"][0]
    wing["leading_edge"] = [[str(x), str(y)] for x, y in wing["leading_edge"]]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        io.project_from_dict(damaged)
    said = [str(w.message) for w in caught if "leading_edge" in str(w.message)]
    assert len(said) == 1, said
    assert "stored as text" in said[0]


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
