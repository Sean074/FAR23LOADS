"""Tests for the project IO layer and the module registry wiring.

These exercise Phase 0's new plumbing -- project JSON load/save, the engine
module's ``run(project)`` entry point reached via the registry, and the CSV
writer -- without introducing any new physics: the loaded project must produce
exactly the same engine results as the in-code example.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from farloads import Project, io, registry  # noqa: E402
from farloads.models import SCHEMA_VERSION, EngineType  # noqa: E402
from test_engine import io520bb  # noqa: E402

EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)
GA6 = os.path.join(EXAMPLES, "ga6_normal.project.json")


def test_example_project_loads():
    project = io.load_project(GA6)
    assert isinstance(project, Project)
    assert project.schema_version == 12
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
    from farloads import run_all

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
    # which needs the same tail_loads/flight_loads slices).
    project = io.load_project(GA6)
    results = registry.run_all_modules(project)
    assert {r.module for r in results} == {
        "engine", "weight_estimate", "weight_onecg", "weight_envelope",
        "wing_geometry", "structural_speeds", "mach_limit", "airloads",
        "flight_envelope", "wing_inertia", "net_loads", "select", "taildist",
        "aileron", "flap", "tab", "landing", "balloads",
    }


def test_run_all_modules_skips_missing_slices():
    # A project with only the engine slice runs the engine module alone.
    from test_engine import io520bb

    from farloads import EngineLayout

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
    calc-facing ``FlightLoadsInput.cg_cases`` the FLTLOADS/SELECT modules read."""
    legacy = io.project_to_dict(io.load_project(GA6))
    del legacy["weight"]["cg_cases"]

    rebuilt = io.project_from_dict(legacy)
    assert [c.name for c in rebuilt.weight.cg_cases] == ["CG1", "CG2", "CG3", "CG4"]
    assert [c.name for c in rebuilt.flight_loads.cg_cases] == ["CG1", "CG2", "CG3", "CG4"]


def test_critical_load_set_selected_case_ids_round_trip():
    """Step D5: the Critical Loads page's opt-out selection persists on
    CriticalLoadSet.selected_case_ids (SCHEMA_VERSION 19); empty means no filter."""
    from farloads.models import CriticalCondition, CriticalLoadSet, EnvelopeResult

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
    # dict round-trip.
    from farloads import GeometryInput, LayoutInput

    layout = LayoutInput(
        fuselage_length=300.0, fuselage_width=48.0, wing_area_sqft=174.0,
        aspect_ratio=6.0, taper_ratio=0.6, le_sweep_deg=2.0, le_root_x=45.0,
        nose_gear_x=20.0, main_gear_x=110.0, track=90.0, gear_height=30.0,
    )
    project = Project(name="cfg", geometry=GeometryInput(parametric=layout))
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.geometry.parametric == layout


def test_c6_slices_round_trip():
    # The v7 (Step C6) slices survive a dict round-trip: the persisted mass
    # properties (WTONECG), the fuselage mass distribution, the SELECT critical
    # set on envelope.critical, and the fuselage net distribution on loads.body_net.
    from farloads.models import (
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
    from farloads import FuselageOutline, FuselageSection, GeometryInput, LayoutInput

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
