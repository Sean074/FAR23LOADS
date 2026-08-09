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
from sloads.models import SCHEMA_VERSION, EngineType  # noqa: E402
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
        "flight_envelope", "wing_inertia", "net_loads", "select", "taildist",
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
    """The loads reference axis (LRA) persists per surface; old files default 0.25."""
    project = io.load_project(GA6)
    wing = project.geometry.by_name("wing")
    assert wing.ref_axis_pct == 0.25  # legacy file without the field
    wing.ref_axis_pct = 0.42
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.geometry.by_name("wing").ref_axis_pct == 0.42


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
    Weight/CG Grid page owns (SCHEMA_VERSION 19)."""
    project = io.load_project(GA6)
    assert project.weight.cg_cases, "the GA6 example should carry migrated cg_cases"
    names = {c.name for c in project.weight.cg_cases}
    assert names == {"CG1", "CG2", "CG3", "CG4"}

    d = io.project_to_dict(project)
    assert d["weight"]["cg_cases"][0]["name"] == "CG1"
    again = io.project_from_dict(d)
    assert [c.name for c in again.weight.cg_cases] == [c.name for c in project.weight.cg_cases]


def test_legacy_flight_loads_cg_cases_migrate_to_weight():
    """Pre-schema-19 files carried the loading scenarios only under
    ``flight_loads.cg_cases``; loading one must still populate
    ``Project.weight.cg_cases`` (Step D5 migration) without disturbing the
    calc-facing ``FlightLoadsInput.cg_cases`` the FLTLOADS/SELECT modules read.

    M4-10: the fixture now declares ``schema_version = 18``, i.e. it really is a
    pre-v19 file. Before the migration chain the shim ran on *every* file
    regardless of version, so this test passed while mutating a current-schema
    dict -- which also meant a v36 project that legitimately had no
    ``weight.cg_cases`` had them silently invented from ``flight_loads``. The
    chain runs the hop only for files old enough to need it."""
    legacy = io.project_to_dict(io.load_project(GA6))
    del legacy["weight"]["cg_cases"]
    legacy["schema_version"] = 18

    rebuilt = io.project_from_dict(legacy)
    assert [c.name for c in rebuilt.weight.cg_cases] == ["CG1", "CG2", "CG3", "CG4"]
    assert [c.name for c in rebuilt.flight_loads.cg_cases] == ["CG1", "CG2", "CG3", "CG4"]


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


def test_legacy_flat_file_still_loads(tmp_path=None):
    # A pre-Project file is just the engine fields at top level; it must wrap.
    flat = os.path.join(EXAMPLES, "_legacy_tmp.json")
    import json

    payload = io.engine_to_dict(io520bb())
    try:
        with open(flat, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        project = io.load_project(flat)
        assert project.engine is not None
        assert project.engine.cylinders == 6
    finally:
        if os.path.exists(flat):
            os.remove(flat)


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


def test_schema_status_current():
    status, message = io.schema_status(SCHEMA_VERSION)
    assert status == "ok"
    assert message == ""


def test_schema_status_older():
    status, message = io.schema_status(SCHEMA_VERSION - 1)
    assert status == "older"
    assert str(SCHEMA_VERSION) in message


def test_schema_status_newer():
    status, message = io.schema_status(SCHEMA_VERSION + 1)
    assert status == "newer"
    assert str(SCHEMA_VERSION) in message


def test_project_from_dict_raises_on_malformed():
    # A wrong-shape engine slice must raise one of the load-path's caught types,
    # not silently build a broken project (Step E5 relies on this to show st.error).
    raised = False
    try:
        io.project_from_dict({"engines": [{"engine_type": "not-a-valid-enum"}]})
    except (TypeError, ValueError, KeyError, AttributeError):
        raised = True
    assert raised


def test_legacy_ft_sqin_keys_migrate_to_canonical():
    """Phase G0 (schema v24): a legacy project with the old ft/in^2 geometry keys
    loads with those keys renamed and rescaled to canonical in/ft^2. Feet -> inches
    (x12), in^2 -> ft^2 (/144); the calc result is unchanged because the ft/in^2
    math is restored internally."""
    d = {
        "schema_version": 20,
        "tail_loads": {"airplane_length_ft": 26.522},
        "vtail_loads": {"airplane_length_ft": 26.522, "wing_span_ft": 33.5,
                        "vtail_mac_ft": 3.367},
        "configuration": {"h_tail_span_ft": 10.0, "v_tail_span_ft": 4.0},
        "tab_loads": {"tabs": [{"surface": "htail", "area_sqin": 226.0}]},
    }
    p = io.project_from_dict(d)
    assert abs(p.tail_loads.airplane_length_in - 26.522 * 12.0) < 1e-9
    assert abs(p.vtail_loads.wing_span_in - 33.5 * 12.0) < 1e-9
    assert abs(p.vtail_loads.vtail_mac_in - 3.367 * 12.0) < 1e-9
    assert abs(p.vtail_loads.airplane_length_in - 26.522 * 12.0) < 1e-9
    # v27 (Step G6): legacy top-level tail_loads/vtail_loads migrate into
    # geometry.empennage; Project.tail_loads/.vtail_loads read them via the property.
    assert p.geometry.empennage is not None
    assert p.geometry.empennage.htail is p.tail_loads
    assert abs(p.tab_loads.tabs[0].area_sqft - 226.0 / 144.0) < 1e-9
    # A canonical (new-key) value already present is not double-converted.
    p2 = io.project_from_dict({"vtail_loads": {"wing_span_in": 402.0}})
    assert p2.vtail_loads.wing_span_in == 402.0


def test_legacy_configuration_folds_into_geometry():
    """Phase G1 (schema v25): a pre-v25 file's top-level "configuration" block folds
    onto the unified geometry slice as geometry.parametric, and the fuselage outline
    is defaulted from the length/width/height scalars. The oracle-locked .surfaces
    consumers are untouched."""
    d = {
        "schema_version": 24,
        "configuration": {"wing_area_sqft": 174.0, "aspect_ratio": 6.0,
                          "fuselage_length": 300.0, "fuselage_width": 48.0,
                          "fuselage_height": 54.0, "datum_x": 0.0},
        "geometry": {"surfaces": [{"name": "wing",
                                   "leading_edge": [[0.0, 0.0], [10.0, 100.0]],
                                   "trailing_edge": [[50.0, 0.0], [55.0, 100.0]]}]},
    }
    p = io.project_from_dict(d)
    assert p.geometry is not None
    # Parametric folded in from the legacy top-level key.
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
    # Round-trips onto the new slice with no legacy top-level "configuration".
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
