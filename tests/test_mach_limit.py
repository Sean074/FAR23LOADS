"""Validate MACHLIM against the FAR 23 LOADS manual, Appendix A.

The 6-place single's Mach-limit lines are printed in Appendix A p160: inputs
MC 0.323, MD 0.403, shoulder 12000 ft, max operating 18000 ft, 1000 ft steps;
outputs MNE 0.3627 and the per-altitude Mach-limited equivalent airspeeds, e.g.
at 12000 ft V(MC) 170.16, V(MNE) 191.08, V(MD) 212.31, falling to V(MC) 150.77 at
18000 ft.

The same page prints MFC 0.4836 and V(FC) 254.77 at 12000 ft, which this port
**deliberately does not produce** (#79): flutter clearance is 23.629
substantiation rather than a design load, and the symbol collides with 25.253's
VFC/MFC. Registered as a scope withdrawal in
``docs/20_theory/02_approved_corrections.md`` -- the printed figures are correct
and unchallenged. The values stay in this docstring so the page can still be
checked against what the tool does and does not claim.

Per Decision 3 the figures are matched within ±0.1%; the shared
``standard_atmosphere`` uses a = 29.02436 vs the program's 29.02 (~0.01%).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob

from helpers import value_of

from sloads import MachLimitInput, Project, StructuralSpeedsInput, io
from sloads.modules import mach_limit as calc
from sloads.modules.structural_speeds import design_speed_values

TOL = 1e-3  # ±0.1% relative

_EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_EXAMPLE = os.path.join(_EXAMPLES_DIR, "ga6_normal.project.json")


def results():
    project = io.load_project(_EXAMPLE)
    ds = design_speed_values(project, project.speeds)
    return calc.mach_limit_lines(project.speeds.mach_limit, ds.mc, ds.md,
                                 project.speeds.shoulder_altitude_ft)


def _line_at(conditions, altitude):
    for c in conditions:
        if c.title.endswith(f"{altitude:g} ft"):
            return c
    raise KeyError(altitude)


def test_mne():
    # MNE = 0.9*MD = 0.3627. (The page's MFC 0.4836 is out of scope -- #79.)
    r = results()
    assert math.isclose(value_of(r, "never_exceed_mach_mne"), 0.3627, rel_tol=TOL)


def test_line_at_shoulder_altitude():
    # 12000 ft: V(MC) 170.16, V(MNE) 191.08, V(MD) 212.31.
    # (The page also prints V(FC) 254.77, out of scope -- #79.)
    line = _line_at(results(), 12000)
    assert math.isclose(value_of([line], "v_mc"), 170.16, rel_tol=TOL)
    assert math.isclose(value_of([line], "v_mne"), 191.08, rel_tol=TOL)
    assert math.isclose(value_of([line], "v_md"), 212.31, rel_tol=TOL)


def test_line_at_max_altitude():
    # 18000 ft: V(MC) 150.77, V(MD) 188.11.
    line = _line_at(results(), 18000)
    assert math.isclose(value_of([line], "v_mc"), 150.77, rel_tol=TOL)
    assert math.isclose(value_of([line], "v_md"), 188.11, rel_tol=TOL)


def test_altitude_rows_span_shoulder_to_max():
    # Shoulder (12000) through max (18000) in 1000 ft steps => 7 altitude lines.
    lines = [c for c in results() if c.title.startswith("Mach limit line")]
    assert len(lines) == 7
    assert lines[0].title.endswith("12000 ft")
    assert lines[-1].title.endswith("18000 ft")


def test_no_flutter_clearance_quantity_is_produced():
    """#79: MFC and V(FC) are out of scope, not merely unasserted.

    A removal that only deletes assertions leaves the quantity free to come back
    -- and it would come back looking like every other Mach line, which is the
    misread the removal is about. Every emitted key is checked, on the summary
    and on every altitude row.
    """
    keys = {v.key for c in results() for v in c.values}
    assert "flutter_clearance_mach_mfc" not in keys
    assert "v_fc" not in keys
    assert {"never_exceed_mach_mne", "v_mc", "v_mne", "v_md"} <= keys


def test_run_requires_mach_limit_inputs():
    raised = False
    try:
        calc.run(Project(name="no speeds"))
    except ValueError:
        raised = True
    assert raised
    raised = False
    try:
        calc.run(Project(name="no mach", speeds=StructuralSpeedsInput()))
    except ValueError:
        raised = True
    assert raised


def test_mc_md_come_from_strspeed_on_every_front_end():
    """The MC/MD drift guard (F25-2).

    MC/MD used to be *stored* on the MACHLIM slice and *recomputed* by the
    Streamlit page, which ignored the stored pair. The registry/CLI path honoured
    it, so ``examples/concept_regional_jet.project.json`` reported MNE 0.738 from
    the CLI and MNE 0.848 from the GUI -- the same project, the same module, two
    answers, which breaks the "GUI, CLI and tests are interchangeable front-ends"
    contract. There is now one producer; this asserts it for every shipped
    fixture, so the duplicate cannot come back.
    """
    for path in sorted(glob.glob(os.path.join(_EXAMPLES_DIR, "*.project.json"))):
        project = io.load_project(path)
        if project.speeds is None or project.speeds.mach_limit is None:
            continue
        ds = design_speed_values(project, project.speeds)
        r = calc.run(project).conditions
        name = os.path.basename(path)
        assert math.isclose(value_of(r, "cruise_mach_mc"), ds.mc, rel_tol=1e-12), name
        assert math.isclose(value_of(r, "dive_mach_md"), ds.md, rel_tol=1e-12), name
        assert math.isclose(value_of(r, "never_exceed_mach_mne"), 0.9 * ds.md, rel_tol=1e-12), name
        assert "flutter_clearance_mach_mfc" not in {v.key for c in r for v in c.values}, name


def test_mach_limit_input_no_longer_carries_mc_md():
    """The structural half of the guard above: the duplicate field is gone, so a
    future edit cannot quietly start reading a stored copy again."""
    from dataclasses import fields as dc_fields

    assert not ({f.name for f in dc_fields(MachLimitInput)} & {"mc", "md"})


def test_above_tropopause_uses_constant_speed_of_sound():
    # Above 35332 ft the speed of sound is constant (~575 kt); two high altitudes
    # share the same a, so V scales only with sqrt(sigma).
    inp = MachLimitInput(max_operating_altitude_ft=40000, increment_ft=2000)
    r = calc.mach_limit_lines(inp, 0.5, 0.6, shoulder_altitude_ft=36000)
    lines = [c for c in r if c.title.startswith("Mach limit line")]
    assert len(lines) == 3  # 36000, 38000, 40000
    # V(MD) decreases monotonically with altitude (sigma falls).
    vmd = [value_of([line], "v_md") for line in lines]
    assert vmd[0] > vmd[1] > vmd[2]


def test_no_shipped_module_computes_a_flutter_clearance_speed():
    """The structural half: removed from the code, not just from the output.

    The runtime guard above proves the current fixtures emit no MFC. This one
    proves nobody recomputes it locally -- which is exactly how it survived in
    the first place: ``app/views/structural_speeds.py`` carried its own
    ``mne, mfc = 0.9 * md, 1.2 * md`` beside the module's, so deleting the
    module's alone would have left the Speed-Altitude chart still drawing the
    line (#79).

    Reads identifiers and load-value keys out of the AST, so the prose in this
    file's own docstrings -- and in ``mach_limit.py``'s, which has to explain
    what was withdrawn -- is not the subject. Comments never reach the AST at
    all.
    """
    import ast

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = []
    for package in ("sloads", "app", "app_shell", "oracle_app"):
        for dirpath, _dirs, files in os.walk(os.path.join(root, package)):
            if "__pycache__" in dirpath:
                continue
            targets += [os.path.join(dirpath, f) for f in files if f.endswith(".py")]
    targets.append(os.path.join(root, "cli.py"))

    _KEYS = {"v_fc", "flutter_clearance_mach_mfc"}
    offenders = []
    for path in sorted(targets):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.arg):
                name = node.arg
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.keyword):
                name = node.arg
            elif isinstance(node, ast.Constant) and node.value in _KEYS:
                name = node.value
            if name and ("mfc" in name.lower() or name in _KEYS):
                offenders.append(f"{os.path.relpath(path, root)}: {name}")
    assert not offenders, offenders



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
