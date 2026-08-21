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
for _p in (_ROOT, os.path.dirname(os.path.abspath(__file__))):
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
    # The unit selection lives on the project (M4-20 step 2, decision D-22) and
    # ``components.active_system()`` reads it there. The session key is still set
    # because it is the fallback for a render with no project yet -- but the
    # project field is what the views actually follow, so setting only the
    # session key here would silently test the Imperial path twice.
    project.unit_system = system.value
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


# --------------------------------------------------------------------------- #
# The same contract through the second GUI (design note 32, OG-F)
# --------------------------------------------------------------------------- #
# The oracle GUI puts all 230 of its fields through the same
# ``unit_number_input`` boundary, from one generic renderer -- so the cases here
# are per *widget kind* rather than per page: a scalar, a member of a composite,
# and a cell of an editable table are the three paths a number can take into the
# project, and each is written once in ``oracle_app/form.py``. A conversion bug
# in any of them is a bug on every page at once, which is the reverse of the
# per-view risk above and needs the reverse of a per-view test.
_ORACLE_SCRIPT = "from oracle_app.form import render_step\nrender_step({key!r})\n"


def _run_oracle(key: str, system: UnitSystem, project):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_ORACLE_SCRIPT.format(key=key), default_timeout=90)
    project.unit_system = system.value
    at.session_state["project"] = project
    at.session_state["unit_system"] = system
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _oracle_number(at, path: str):
    """The oracle GUI's number widget for a registry ``path``.

    ``unit_number_input`` appends the active system to the widget key, which is
    the mechanism that re-seeds a field when the user switches systems -- so the
    lookup matches the path and lets the suffix be whatever the shell chose.
    """
    hits = [n for n in at.number_input
            if n.key == path or (n.key or "").startswith(f"{path}_")]
    assert len(hits) == 1, f"expected one widget for {path!r}, got {[n.key for n in hits]}"
    return hits[0]


@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_an_oracle_scalar_is_stored_imperial_from_either_system(system):
    """A plain number: type 100 in, get 100 in; type 2540 mm, get the same 100 in."""
    from sloads import io

    project = io.load_project(_GA6)
    at = _run_oracle("structural_speeds", system, project)
    field = _oracle_number(at, "speeds.wing_area_sqft")
    assert (UNIT_LABELS[system]["area_sqft"] in (field.label or "")), (
        f"{system.value}: {field.label!r} does not state the active area unit")

    typed = to_display(150.0, "area_sqft", system)
    field.set_value(typed).run()
    stored = at.session_state["project"].speeds.wing_area_sqft
    assert math.isclose(stored, 150.0, rel_tol=1e-9), (
        f"{system.value}: typed {typed} and stored {stored}, expected 150.0 sq ft")


@pytest.mark.parametrize("system", _SYSTEMS, ids=[s.value for s in _SYSTEMS])
def test_an_oracle_composite_member_is_stored_imperial_from_either_system(system):
    """A member of a ``Tuple[float, float]`` -- the gear axle's (X, Z) station,
    which has no unit suffix in its own name and gets one from the registry."""
    from sloads import io

    project = io.load_project(_GA6)
    at = _run_oracle("landing_loads", system, project)
    field = _oracle_number(at, "landing.main_gear.axle_static.0")

    typed = to_display(120.0, "length", system)
    field.set_value(typed).run()
    stored = at.session_state["project"].landing.main_gear.axle_static[0]
    assert math.isclose(stored, 120.0, rel_tol=1e-9), (
        f"{system.value}: typed {typed} and stored {stored}, expected 120.0 in")


def _oracle_keys():
    from sloads import workflow as wf

    return sorted(wf.oracle_step_keys())


@pytest.mark.parametrize("key", _oracle_keys())
def test_an_untouched_oracle_page_stores_exactly_what_it_loaded_in_si(key):
    """The rounding trap, in the GUI that renders every field live.

    ``app/`` gets one shot at this per Apply; the oracle GUI writes on every
    rerun, so a value converted out to SI and straight back would walk the
    project a hair at a time, on every keystroke anywhere on the page. It did:
    ``116 in`` came back as ``115.99999999999999``, on untouched geometry, for
    every SI user. Nothing is typed here at all.

    Every page, and SI only: ``tests/test_dirty_flag.py`` runs the Imperial
    direction over every page and example, and Imperial cannot drift -- its
    conversion is the identity. This is the direction with a factor in it.
    """
    from sloads import io

    project = io.load_project(_GA6)
    project.unit_system = UnitSystem.SI.value  # the selection is itself an edit (D-22)
    before = io.project_to_dict(project)
    at = _run_oracle(key, UnitSystem.SI, project)
    assert io.project_to_dict(at.session_state["project"]) == before, (
        f"rendering {key} in SI changed the project")


if __name__ == "__main__":  # pragma: no cover - needs pytest for parametrize
    raise SystemExit(pytest.main([__file__, "-q"]))
