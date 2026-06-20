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
from farloads.models import EngineType  # noqa: E402
from test_engine import io520bb  # noqa: E402

EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)
GA6 = os.path.join(EXAMPLES, "ga6_normal.project.json")


def test_example_project_loads():
    project = io.load_project(GA6)
    assert isinstance(project, Project)
    assert project.schema_version == 4
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
    # mach-limit, airloads, flight-envelope, wing-inertia and net-loads (skipping any
    # module whose slice is absent via the ValueError path).
    project = io.load_project(GA6)
    results = registry.run_all_modules(project)
    assert {r.module for r in results} == {
        "engine", "weight_estimate", "weight_onecg", "weight_envelope",
        "wing_geometry", "structural_speeds", "mach_limit", "airloads",
        "flight_envelope", "wing_inertia", "net_loads",
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


def test_configuration_round_trip():
    # The configuration/layout slice survives a dict round-trip (v6 schema).
    from farloads import LayoutInput

    layout = LayoutInput(
        fuselage_length=300.0, fuselage_width=48.0, wing_area_sqft=174.0,
        aspect_ratio=6.0, taper_ratio=0.6, le_sweep_deg=2.0, le_root_x=45.0,
        h_tail_area=21.0, h_tail_arm=180.0, nose_gear_x=20.0, main_gear_x=110.0,
        track=90.0, gear_height=30.0,
    )
    project = Project(name="cfg", configuration=layout)
    again = io.project_from_dict(io.project_to_dict(project))
    assert again.configuration == layout


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
    assert len(lines) == 1 + 3  # header + LC1..LC3
    assert lines[0].startswith("ID,FAR,Case description")


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
