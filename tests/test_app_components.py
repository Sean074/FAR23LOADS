"""The app scaffold helpers (M4-11): the unit boundary and the page context.

``unit_number_input`` is the whole GUI unit boundary in one function, which makes
it the single highest-leverage place in the app layer for a silent numeric bug:
a helper that converts twice, or converts the wrong way, renders *perfectly* and
quietly corrupts every input on every page. ``test_views_smoke.py`` cannot catch
that -- it asserts exception-free render, not correct values -- so the round-trip
below is the actual guard, per the M4-11 definition of done in
``docs/40_history/07_m4_maintainability_sequence_plan.md`` §4 step 3.

What is asserted:

1. **Imperial in, Imperial out** for every converted unit kind, in *both*
   systems -- the property the view layer relies on to stay canonical.
2. **The aviation carve-out is exact**, not merely close: airspeed (KEAS) and
   altitude (ft) pass through byte-identical in SI (decision D-16).
3. **The widget key is per-system when converting** and *not* when it isn't --
   a converted field must re-seed on a unit switch, a KEAS field must not.
4. **Ambiguity is rejected**: ``kind=`` and ``fixed_unit=`` together raise.
"""

import math
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sloads import UnitSystem  # noqa: E402
from sloads.units import UNIT_LABELS  # noqa: E402

pytest.importorskip("streamlit")

from app_shell import components as comp  # noqa: E402
from app_shell.widget_keys import unstamped  # noqa: E402

# Every kind the unit layer knows -- driven off UNIT_LABELS so a new kind is
# covered automatically instead of being forgotten here.
_KINDS = sorted(UNIT_LABELS[UnitSystem.IMPERIAL])

# Representative canonical-Imperial magnitudes (a wing area, a station, a weight...).
_VALUES = [1.0, 3.25, 174.0, 3400.0, 13257.0, 0.0007]


class _FakeStreamlit:
    """Records the label/key/seed ``unit_number_input`` hands to Streamlit and
    echoes the seed back, standing in for a user who typed nothing.

    ``unit_number_input`` reads the unit system through ``components.active_system``
    (decision D-16's single resolver), which the tests monkeypatch directly, so no
    session state is needed.
    """

    def __init__(self):
        self.calls = []

    def number_input(self, label, value=None, key=None, **kwargs):
        self.calls.append({"label": label, "value": value, "key": key, **kwargs})
        return value

    @property
    def last(self):
        return self.calls[-1]


def _harness(monkeypatch, system, *, typed=None):
    """Install the fake Streamlit + a fixed unit system; return the recorder.

    ``typed`` overrides the echoed value to simulate a user entering a number in
    display units (that is what exercises the return-path conversion).
    """
    fake = _FakeStreamlit()
    if typed is not None:
        fake.number_input = lambda label, value=None, key=None, **kw: (
            fake.calls.append({"label": label, "value": value, "key": key, **kw}) or typed
        )
    monkeypatch.setattr(comp, "st", fake)
    monkeypatch.setattr(comp, "active_system", lambda: system)
    return fake


# --------------------------------------------------------------------------- #
# 1. Imperial in -> Imperial out (the property the whole app layer rests on)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("system", [UnitSystem.IMPERIAL, UnitSystem.SI])
@pytest.mark.parametrize("kind", _KINDS)
def test_converted_field_round_trips_to_imperial(monkeypatch, system, kind):
    """The seed is shown converted, and an untouched field returns the *same*
    Imperial number it was given -- in both systems."""
    for value in _VALUES:
        fake = _harness(monkeypatch, system)
        out = comp.unit_number_input("Field", value, kind=kind, key="f")
        # The widget was seeded in display units...
        shown = fake.last["value"]
        if system is UnitSystem.SI and value > 0.01:
            assert not math.isclose(shown, value, rel_tol=1e-9) or kind == "inertia_lbin2", \
                f"{kind} seed was not converted for SI"
        # ...and what comes back out is canonical Imperial again.
        assert math.isclose(out, value, rel_tol=1e-6), (kind, system, value, shown, out)


@pytest.mark.parametrize("kind", _KINDS)
def test_user_entry_in_si_is_converted_home(monkeypatch, kind):
    """A number *typed in SI* comes back as Imperial -- the direction a
    double-conversion or an inverted factor would break."""
    from sloads.units import to_display, to_imperial_scalar

    imperial_truth = 123.456
    si_typed = to_display(imperial_truth, kind, UnitSystem.SI)
    _harness(monkeypatch, UnitSystem.SI, typed=si_typed)
    out = comp.unit_number_input("Field", 0.0, kind=kind, key="f")
    assert math.isclose(out, imperial_truth, rel_tol=1e-9), (kind, si_typed, out)
    # And the helper agrees with the units layer it delegates to.
    assert math.isclose(out, to_imperial_scalar(si_typed, kind, UnitSystem.SI), rel_tol=1e-12)


def test_converted_label_carries_the_active_systems_unit(monkeypatch):
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        fake = _harness(monkeypatch, system)
        comp.unit_number_input("Area S", 174.0, kind="area_sqft", key="s")
        assert fake.last["label"] == f"Area S ({UNIT_LABELS[system]['area_sqft']})"


# --------------------------------------------------------------------------- #
# 2. The aviation carve-out (decision D-16) -- exact, in both systems
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("system", [UnitSystem.IMPERIAL, UnitSystem.SI])
@pytest.mark.parametrize("unit", [comp.KEAS, comp.ALTITUDE_FT])
def test_fixed_unit_is_never_converted(monkeypatch, system, unit):
    """Airspeed is KEAS and altitude is feet in *both* systems -- so these pass
    through untouched, and exactly so (not merely within tolerance)."""
    fake = _harness(monkeypatch, system)
    out = comp.unit_number_input("V", 212.4, fixed_unit=unit, key="v")
    assert fake.last["value"] == 212.4, "a fixed-unit field must be seeded raw"
    assert out == 212.4, "a fixed-unit field must return exactly what it was given"
    assert fake.last["label"] == f"V ({unit})"


@pytest.mark.parametrize("kind", _KINDS)
def test_bounds_are_converted_with_the_value(monkeypatch, kind):
    """``min_value``/``max_value`` are Imperial like the value, so they must be
    converted too -- an unconverted 12-in floor becomes a 12-mm floor in SI and
    silently stops constraining anything."""
    from sloads.units import to_display

    fake = _harness(monkeypatch, UnitSystem.SI)
    comp.unit_number_input("F", 100.0, kind=kind, key="f", min_value=12.0, max_value=500.0)
    assert math.isclose(fake.last["min_value"], to_display(12.0, kind, UnitSystem.SI), rel_tol=1e-12)
    assert math.isclose(fake.last["max_value"], to_display(500.0, kind, UnitSystem.SI), rel_tol=1e-12)


def test_zero_and_absent_bounds_pass_through(monkeypatch):
    fake = _harness(monkeypatch, UnitSystem.SI)
    comp.unit_number_input("F", 1.0, kind="length", key="f", min_value=0.0)
    assert fake.last["min_value"] == 0.0
    fake = _harness(monkeypatch, UnitSystem.SI)
    comp.unit_number_input("F", 1.0, kind="length", key="f", min_value=None)
    assert fake.last["min_value"] is None


@pytest.mark.parametrize("system", [UnitSystem.IMPERIAL, UnitSystem.SI])
def test_dimensionless_field_has_no_unit_suffix(monkeypatch, system):
    fake = _harness(monkeypatch, system)
    out = comp.unit_number_input("Taper ratio λ", 0.5, key="taper")
    assert fake.last["label"] == "Taper ratio λ"
    assert out == 0.5


# --------------------------------------------------------------------------- #
# 3. Widget-key discipline -- converted fields re-seed on a unit switch
# --------------------------------------------------------------------------- #
def test_converted_key_is_per_system_but_fixed_and_plain_keys_are_not(monkeypatch):
    keys = {}
    for system in (UnitSystem.IMPERIAL, UnitSystem.SI):
        fake = _harness(monkeypatch, system)
        comp.unit_number_input("L", 10.0, kind="length", key="k")
        comp.unit_number_input("V", 10.0, fixed_unit=comp.KEAS, key="k")
        comp.unit_number_input("R", 10.0, key="k")
        keys[system] = [c["key"] for c in fake.calls]

    conv_imp, fixed_imp, plain_imp = keys[UnitSystem.IMPERIAL]
    conv_si, fixed_si, plain_si = keys[UnitSystem.SI]
    # Converted: distinct per system, so switching units re-seeds with the
    # converted default instead of reusing the stale number.
    assert conv_imp != conv_si, "a converted widget must not share a key across systems"
    # Fixed / dimensionless: the number means the same thing either way, so the
    # field must survive a unit switch unchanged.
    assert fixed_imp == fixed_si
    assert plain_imp == plain_si
    # Every key on this boundary also carries the project generation, which is
    # the other half of "is this the same widget?" (#51): a unit switch keeps
    # the field, a project *replacement* retires it. Asserted through
    # ``unstamped`` so the stamp's format stays the shell's own business.
    assert [unstamped(k) for k in (fixed_imp, plain_imp)] == ["k", "k"]
    assert all(k != unstamped(k) for k in (conv_imp, fixed_imp, plain_imp)), (
        "a widget on the unit boundary was keyed without the project-generation "
        "stamp, so a loaded project would not reach it")


# --------------------------------------------------------------------------- #
# 4. Ambiguity is a hard error, not a silent precedence rule
# --------------------------------------------------------------------------- #
def test_kind_and_fixed_unit_together_raise(monkeypatch):
    _harness(monkeypatch, UnitSystem.IMPERIAL)
    with pytest.raises(ValueError):
        comp.unit_number_input("Bad", 1.0, kind="length", fixed_unit=comp.KEAS, key="b")


# --------------------------------------------------------------------------- #
# A link names a step, not a path (design note 32, OG-F)
# --------------------------------------------------------------------------- #
def test_a_link_targets_the_running_guis_own_page(monkeypatch):
    """``workflow_page_link`` hands ``st.page_link`` the registered page object.

    Before OG-F it built ``views/<key>.py`` -- one front-end's directory layout,
    inside the shell both of them import. The page a link points at now comes
    from whichever GUI registered its own set.
    """
    from app_shell import nav

    sentinel = object()
    targets = []
    monkeypatch.setattr(comp.st, "session_state", {nav.PAGES: {"wing_loads": sentinel}})
    monkeypatch.setattr(comp.st, "page_link", lambda page, **kw: targets.append((page, kw)))
    monkeypatch.setattr(comp.st, "markdown", lambda *a, **k: targets.append(("markdown", a)))

    comp.workflow_page_link("wing_loads")
    assert len(targets) == 1
    page, kwargs = targets[0]
    assert page is sentinel, "the link did not target the registered page object"
    assert kwargs["label"] == "Wing Loads", "the label is not the step's own title"


def test_a_link_to_a_page_this_gui_does_not_carry_degrades_to_text(monkeypatch):
    """The oracle GUI carries fourteen of the twenty-two steps, and a view driven
    standalone registers nothing at all. Neither may raise, and neither may emit
    a link to a page that is not there -- a gate hint must still be readable."""
    from app_shell import nav

    calls = []
    monkeypatch.setattr(comp.st, "session_state", {nav.PAGES: {}})
    monkeypatch.setattr(comp.st, "page_link",
                        lambda *a, **k: pytest.fail("linked to an unregistered page"))
    monkeypatch.setattr(comp.st, "markdown", lambda text, **k: calls.append(text))

    comp.workflow_page_link("wing_loads")
    assert calls == ["Wing Loads"]


# --------------------------------------------------------------------------- #
# 5. The applicability banner's action is optional; its warning is not (CR-A-4)
# --------------------------------------------------------------------------- #
def _banner_harness(monkeypatch):
    """Render the banner against a recorder; return ``(warnings, buttons)``."""
    from sloads import io

    fake = _harness(monkeypatch, UnitSystem.IMPERIAL)
    warnings, buttons = [], []
    fake.warning = lambda text, **k: warnings.append(text)
    fake.markdown = lambda text, **k: None
    fake.button = lambda label, **k: buttons.append(label) or False

    example = os.path.join(_ROOT, "examples", "ga6_normal.project.json")
    project = io.load_project(example)
    # Above the 12,500 lb ceiling: both members of the MTOW SSOT read (G-14).
    project.weight.max_takeoff_weight_lb = 20000.0
    project.speeds.weight_lb = 20000.0
    return project, warnings, buttons


def test_the_banner_offers_the_concept_switch_by_default(monkeypatch):
    """The main GUI's behaviour, pinned so the shell default cannot be flipped
    for everyone by a fix aimed at one front-end."""
    project, warnings, buttons = _banner_harness(monkeypatch)
    comp.render_applicability_banner(project)
    assert warnings and "Exceeds FAR 23 applicability" in warnings[0]
    assert buttons == ["Switch to Concept"]


def test_the_banner_without_its_action_still_warns(monkeypatch):
    """``switch_action=False`` drops the button and nothing else -- an
    out-of-band airplane is still told its results are an extrapolation."""
    project, warnings, buttons = _banner_harness(monkeypatch)
    comp.render_applicability_banner(project, switch_action=False)
    assert warnings and "Exceeds FAR 23 applicability" in warnings[0]
    assert buttons == []


if __name__ == "__main__":  # pragma: no cover - needs pytest for parametrize/monkeypatch
    raise SystemExit(pytest.main([__file__, "-q"]))
