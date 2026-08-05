"""Persistence verification (Step M2-7 / decision G-3).

Two guarantees:

1. **Save->reload is a no-op for every shipped example** -- the project JSON is the
   single reloadable store; loading and re-serializing changes nothing.
2. **Field coverage: every input-dataclass field survives an ``io`` round-trip** --
   a *completeness guard*. For each input slice we build an instance with every field
   set to a distinct non-default sentinel (recursively, through nested dataclasses /
   lists / enums), round-trip it through its ``io`` ``*_from_dict``/``*_to_dict`` pair,
   and assert every field comes back unchanged. This fails the build when a field is
   added to an input dataclass but not wired into ``io`` -- the classic silent
   persistence bug. Fields that are *intentionally* derived rather than stored (the
   Step M2-6 single-source cleanup, the Step G6/G6b geometry moves) are listed in
   ``DERIVED_NOT_PERSISTED`` and skipped.
"""

import dataclasses
import enum
import glob
import json
import os
import re
import sys
import typing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.models import (  # noqa: E402
    AeroCoefficientsInput,
    AeroInput,
    AileronLoadsInput,
    EngineInput,
    FlapLoadsInput,
    FlightLoadsInput,
    FuselageMassInput,
    GeometryInput,
    LandingInput,
    OneEngineOutInput,
    SelectInput,
    StructuralSpeedsInput,
    TabLoadsInput,
    WeightInput,
    WingMassInput,
)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


# --------------------------------------------------------------------------- #
# 1. Save->reload no-op on every example
# --------------------------------------------------------------------------- #
def _norm(d):
    """JSON-normalize (tuples -> lists) so the comparison is at the serialized level."""
    return json.loads(json.dumps(d))


def test_every_example_save_reload_is_a_noop():
    files = sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json")))
    assert files, "no example projects found"
    for f in files:
        d1 = _norm(io.project_to_dict(io.load_project(f)))
        d2 = _norm(io.project_to_dict(io.project_from_dict(d1)))
        assert d1 == d2, f"save->reload changed {os.path.basename(f)}"


# --------------------------------------------------------------------------- #
# 2. Field-coverage completeness guard
# --------------------------------------------------------------------------- #
# (dataclass name, field) pairs that are intentionally NOT persisted -- derived from
# the single-source geometry (Step M2-6) or relocated to their single home (G6/G6b).
DERIVED_NOT_PERSISTED = {
    ("FlightLoadsInput", "mac"),
    ("FlightLoadsInput", "wing_area_sqft"),
    ("FlightLoadsInput", "xw"),
    ("FlightLoadsInput", "zw"),
    ("WingMassInput", "dihedral_deg"),
    ("WingMassInput", "wrp_waterline"),
    ("LandingInput", "wing_area_sqft"),   # M2-6: from the geometry wing
    ("LandingInput", "main_gear"),        # G6b: from geometry.landing_gear
    ("LandingInput", "nose_gear"),        # G6b
    ("LandingInput", "tread_in"),         # G6b
    ("LayoutInput", "fuselage_length"),   # M2-6: derived summary of the outline
    ("LayoutInput", "fuselage_width"),
    ("LayoutInput", "fuselage_height"),
}

# Each input slice with its io (from_dict, to_dict) pair. geometry_from_dict's legacy
# migration args are all defaulted, so it round-trips a filled GeometryInput directly.
SLICES = [
    (EngineInput, io.engine_from_dict, io.engine_to_dict),
    (WeightInput, io.weight_from_dict, io.weight_to_dict),
    (GeometryInput, io.geometry_from_dict, io.geometry_to_dict),
    (StructuralSpeedsInput, io.speeds_from_dict, io.speeds_to_dict),
    (AeroInput, io.aero_from_dict, io.aero_to_dict),
    (AeroCoefficientsInput, io.aero_coefficients_from_dict, io.aero_coefficients_to_dict),
    (FlightLoadsInput, io.flight_loads_from_dict, io.flight_loads_to_dict),
    (WingMassInput, io.wing_mass_from_dict, io.wing_mass_to_dict),
    (FuselageMassInput, io.fuselage_mass_from_dict, io.fuselage_mass_to_dict),
    (SelectInput, io.select_input_from_dict, io.select_input_to_dict),
    (OneEngineOutInput, io.one_engine_out_from_dict, io.one_engine_out_to_dict),
    (LandingInput, io.landing_from_dict, io.landing_to_dict),
    (AileronLoadsInput, io.aileron_loads_from_dict, io.aileron_loads_to_dict),
    (FlapLoadsInput, io.flap_loads_from_dict, io.flap_loads_to_dict),
    (TabLoadsInput, io.tab_loads_from_dict, io.tab_loads_to_dict),
]


def _fill(tp, counter):
    """A distinct non-default value for ``tp`` (recursively for dataclasses/containers)."""
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is typing.Union:                      # Optional[X] / Union[X, None]
        inner = next(a for a in args if a is not type(None))
        return _fill(inner, counter)
    if origin in (list, typing.List):
        return [_fill(args[0], counter)]
    if origin in (tuple, typing.Tuple):
        if len(args) == 2 and args[1] is Ellipsis:
            return (_fill(args[0], counter),)
        return tuple(_fill(a, counter) for a in args)
    if origin in (dict, typing.Dict):
        return {"k": _fill(args[1], counter)}
    if isinstance(tp, type) and issubclass(tp, enum.Enum):
        return list(tp)[-1]                          # a non-default member
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        return _fill_dataclass(tp, counter)
    counter[0] += 1
    if tp is bool:
        return True
    if tp is int:
        return counter[0] + 100
    if tp is float:
        return float(counter[0]) + 0.5
    if tp is str:
        return f"v{counter[0]}"
    raise AssertionError(f"filler has no rule for type {tp!r}")


def _fill_dataclass(cls, counter):
    hints = typing.get_type_hints(cls)
    return cls(**{f.name: _fill(hints[f.name], counter) for f in dataclasses.fields(cls)})


def _assert_survives(a, b, path=""):
    """Assert every field of dataclass ``a`` equals ``b`` after a round-trip, skipping
    the (class, field) pairs in DERIVED_NOT_PERSISTED (at any nesting depth)."""
    if dataclasses.is_dataclass(a) and not isinstance(a, type):
        for f in dataclasses.fields(a):
            if (type(a).__name__, f.name) in DERIVED_NOT_PERSISTED:
                continue
            _assert_survives(getattr(a, f.name), getattr(b, f.name), f"{path}.{f.name}")
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_survives(x, y, f"{path}[{i}]")
    else:
        assert a == b, f"{path}: io dropped/altered field ({a!r} != {b!r})"


def test_input_dataclasses_round_trip_every_field():
    counter = [0]
    for cls, from_dict, to_dict in SLICES:
        filled = _fill_dataclass(cls, counter)
        back = from_dict(to_dict(filled))
        _assert_survives(filled, back, cls.__name__)


def test_derived_allowlist_entries_are_real_fields():
    """Guard the guard: every DERIVED_NOT_PERSISTED entry names a real dataclass field
    (so a rename can't silently turn the allowlist into dead weight)."""
    import sloads.models as M

    by_name = {c.__name__: c for c in vars(M).values()
               if isinstance(c, type) and dataclasses.is_dataclass(c)}
    for cls_name, field_name in DERIVED_NOT_PERSISTED:
        assert cls_name in by_name, f"unknown dataclass {cls_name}"
        names = {f.name for f in dataclasses.fields(by_name[cls_name])}
        assert field_name in names, f"{cls_name} has no field {field_name}"


# --------------------------------------------------------------------------- #
# 3. No input page holds input data outside st.session_state["project"]
# --------------------------------------------------------------------------- #
_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")

# The only session_state keys the GUI may *write*. All are UI state, not airplane
# input data (which lives on the single reloadable `project`):
#   project                  -- the canonical single store (the whole airplane)
#   unit_system              -- the Imperial/SI display preference
#   _saved_project_snapshot  -- the dirty-flag baseline (derived from project)
#   engine_sel               -- which engine the Engine Mount radio has selected
_ALLOWED_SESSION_KEYS = {
    "project", "unit_system", "_saved_project_snapshot", "engine_sel",
    # Step G8.6: the compiled summary-report PDF, the .tex it was compiled from
    # (the freshness key) and the engine log. All three are *output* held between
    # reruns so a compile survives the next widget interaction -- none is airplane
    # input, and every one is rebuilt from `project` on demand.
    "report_pdf_bytes", "report_pdf_key", "report_pdf_log",
}
# Files allowed to write session_state under a *variable* key (not a string literal).
# The Project Editor stages the raw JSON text in a re-seeded scratchpad, committed to
# `project` on Apply -- a text buffer, not un-persisted airplane input.
_ALLOWED_VARIABLE_KEY_FILES = {"project_editor.py"}

_LITERAL_WRITE = re.compile(r"""st\.session_state\[\s*(["'])(?P<key>.+?)\1\s*\]\s*=""")
_VARIABLE_WRITE = re.compile(r"""st\.session_state\[\s*(?!["'])[^\]]+\]\s*=""")


def test_no_input_data_written_outside_project_session_state():
    """Every `st.session_state[...] = ` write across the app uses an allow-listed UI
    key (or the Project Editor's text scratchpad). A new key trips this test so the
    reviewer must decide whether it is input data that belongs on `project` (G-3)."""
    offenders_literal = {}
    offenders_variable = {}
    for path in glob.glob(os.path.join(_APP, "**", "*.py"), recursive=True):
        src = open(path, encoding="utf-8").read()
        base = os.path.basename(path)
        for m in _LITERAL_WRITE.finditer(src):
            key = m.group("key")
            if key not in _ALLOWED_SESSION_KEYS:
                offenders_literal.setdefault(base, set()).add(key)
        if base not in _ALLOWED_VARIABLE_KEY_FILES and _VARIABLE_WRITE.search(src):
            offenders_variable[base] = True
    assert not offenders_literal, f"un-allowlisted session_state keys written: {offenders_literal}"
    assert not offenders_variable, (
        f"session_state written under a non-literal key outside the Project Editor: "
        f"{sorted(offenders_variable)}")
