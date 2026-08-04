"""A number typed into a view reaches the project in Imperial — in both systems.

This is the M4-11 acceptance test the plan calls "the real one"
(``docs/40_history/07_m4_maintainability_sequence_plan.md`` §4 step 3).
``test_views_smoke.py`` parametrizes over every view but asserts only
*exception-free render*: a ``unit_number_input`` that converted twice, or in the
wrong direction, would render perfectly and silently corrupt every input on
every page. ``test_app_components.py`` pins the helper in isolation; this file
pins it **through a real view**, driven headlessly via ``AppTest`` — the widget,
the form, the Apply handler and the persist path together.

The shape of every case below: run the view in a unit system, type a number into
a field *in that system's display units*, press that form's Apply (by form key,
per M4-12a), then assert ``st.session_state["project"]`` holds the **Imperial**
equivalent. Imperial and SI runs assert the *same* stored Imperial value from
different typed numbers, which is exactly the property a conversion bug breaks.
"""

import math
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "app"), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import logging  # noqa: E402

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

from sloads import UnitSystem  # noqa: E402
from sloads.units import UNIT_LABELS, to_display  # noqa: E402

pytest.importorskip("streamlit.testing.v1")

from helpers import apply_button  # noqa: E402

_VIEWS_DIR = os.path.join(_ROOT, "app", "views")
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")

_SYSTEMS = [UnitSystem.IMPERIAL, UnitSystem.SI]


def _run(view: str, system: UnitSystem, project):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, view), default_timeout=90)
    at.session_state["project"] = project
    at.session_state["unit_system"] = system
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _field(at, label_prefix: str):
    """The one number_input whose label starts with ``label_prefix``.

    Selecting on the *prefix* rather than the whole label is deliberate: the
    unit suffix is the thing under test and differs per system, so pinning the
    full string would make the test restate the behaviour it is checking.
    """
    hits = [n for n in at.number_input if (n.label or "").startswith(label_prefix)]
    assert len(hits) == 1, (
        f"expected exactly one field starting {label_prefix!r}, got "
        f"{[n.label for n in hits]}"
    )
    return hits[0]


def _labelled(at, label_prefix: str, kind: str, system: UnitSystem):
    """The field, having first asserted its label carries the active system's unit."""
    field = _field(at, label_prefix)
    assert field.label.endswith(f"({UNIT_LABELS[system][kind]})"), (
        f"{field.label!r} does not show the {system.value} unit for {kind}"
    )
    return field


# --------------------------------------------------------------------------- #
# Geometry page -- the empennage form (30 fields converted by M4-11; before it,
# these were hard-coded to Imperial labels and took raw Imperial in SI mode)
# --------------------------------------------------------------------------- #
_HT_AREA_IMPERIAL = 42.5  # ft^2


@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_empennage_area_is_stored_imperial_from_either_system(system):
    from sloads import io

    project = io.load_project(_GA6)
    at = _run("configuration_layout.py", system, project)

    typed = to_display(_HT_AREA_IMPERIAL, "area_sqft", system)
    _labelled(at, "H-tail area ST", "area_sqft", system).set_value(typed)
    apply_button(at, "empennage_form").set_value(True).run()

    stored = at.session_state["project"].tail_loads
    assert stored is not None, "empennage Apply did not persist"
    assert math.isclose(stored.htail_area_sqft, _HT_AREA_IMPERIAL, rel_tol=1e-6), (
        f"typed {typed} in {system.value}; project holds "
        f"{stored.htail_area_sqft} ft^2, expected {_HT_AREA_IMPERIAL}"
    )


_XT25_IMPERIAL = 261.5  # in


@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_empennage_station_is_stored_imperial_from_either_system(system):
    """A length field, to cover a different conversion factor than area."""
    from sloads import io

    project = io.load_project(_GA6)
    at = _run("configuration_layout.py", system, project)

    typed = to_display(_XT25_IMPERIAL, "length", system)
    _labelled(at, "25% tail-MAC station xt25", "length", system).set_value(typed)
    apply_button(at, "empennage_form").set_value(True).run()

    stored = at.session_state["project"].tail_loads
    assert stored is not None
    assert math.isclose(stored.xt25, _XT25_IMPERIAL, rel_tol=1e-6), (
        f"typed {typed} in {system.value}; project holds {stored.xt25} in"
    )


# --------------------------------------------------------------------------- #
# Geometry page -- the landing-gear form (7 fields; its caption used to read
# "Values are Imperial (in)" because they genuinely were, in both systems)
# --------------------------------------------------------------------------- #
_TREAD_IMPERIAL = 96.0  # in


@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_landing_gear_tread_is_stored_imperial_from_either_system(system):
    from sloads import io

    project = io.load_project(_GA6)
    at = _run("configuration_layout.py", system, project)

    typed = to_display(_TREAD_IMPERIAL, "length", system)
    _labelled(at, "Tread between mains", "length", system).set_value(typed)
    apply_button(at, "landing_gear_form").set_value(True).run()

    gear = at.session_state["project"].geometry.landing_gear
    assert gear is not None, "landing-gear Apply did not persist"
    assert math.isclose(gear.tread_in, _TREAD_IMPERIAL, rel_tol=1e-6), (
        f"typed {typed} in {system.value}; project holds {gear.tread_in} in"
    )


# --------------------------------------------------------------------------- #
# Geometry page -- the parametric wing form (the pre-existing `_num` path, now
# delegating to the same helper; guards the adapter as well as the helper)
# --------------------------------------------------------------------------- #
_WING_AREA_IMPERIAL = 191.0  # ft^2


@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_wing_area_is_stored_imperial_from_either_system(system):
    from sloads import io

    project = io.load_project(_GA6)
    at = _run("configuration_layout.py", system, project)

    typed = to_display(_WING_AREA_IMPERIAL, "area_sqft", system)
    _labelled(at, "Area S", "area_sqft", system).set_value(typed)
    apply_button(at, "layout_form").set_value(True).run()

    layout = at.session_state["project"].geometry.parametric
    assert math.isclose(layout.wing_area_sqft, _WING_AREA_IMPERIAL, rel_tol=1e-6), (
        f"typed {typed} in {system.value}; project holds {layout.wing_area_sqft} ft^2"
    )


# --------------------------------------------------------------------------- #
# An untouched field must not drift the project (the rounding trap)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_apply_without_edits_leaves_values_bit_identical(system):
    """Apply with nothing typed must store exactly what was loaded.

    The display seed is rounded to 4 decimals for legibility, so converting that
    rounded number back would return a value a hair off the original -- and an SI
    user's project would drift by that hair on every Apply. ``unit_number_input``
    returns the caller's own Imperial value when the field is untouched; this is
    the end-to-end guard for that.
    """
    from sloads import io

    project = io.load_project(_GA6)
    before = project.geometry.parametric.wing_area_sqft
    before_le = project.geometry.parametric.le_root_x

    at = _run("configuration_layout.py", system, project)
    apply_button(at, "layout_form").set_value(True).run()

    layout = at.session_state["project"].geometry.parametric
    assert layout.wing_area_sqft == before, (
        f"{system.value}: untouched wing area drifted {before} -> {layout.wing_area_sqft}"
    )
    assert layout.le_root_x == before_le, (
        f"{system.value}: untouched LE station drifted {before_le} -> {layout.le_root_x}"
    )


if __name__ == "__main__":  # pragma: no cover - needs pytest for parametrize
    raise SystemExit(pytest.main([__file__, "-q"]))
