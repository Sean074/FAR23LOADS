"""Geometry page Apply must validate before persisting (M2R-6).

The sidebar **Apply geometry** used to store whatever was typed -- including an
invalid wing (e.g. Area S = 0) -- which then crashed ``configuration_properties``
in the page body and hit ``st.stop()``, blanking the *unrelated* empennage /
landing-gear / outline forms further down. The fix validates the candidate layout
first and rejects an invalid Apply with a targeted message, leaving the last valid
layout (and the rest of the page) intact.

Driven headlessly via ``AppTest``.

Also home to the **Apply must not drop a field** guard (#36): a form that rebuilds
an input dataclass field-by-field silently zeroes every field it forgets to name,
so pressing Apply destroyed values a hand-written ``project.json`` supplied.
"""

import dataclasses
import logging
import os
import sys

import pytest

from helpers import apply_button

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEW = os.path.join(_ROOT, "app", "views", "configuration_layout.py")
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")

# Under pytest ``conftest.py`` puts these on the path; the __main__ self-runner
# has to do it itself, or the view fails on ``import app_shell``.
for _p in (_ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytest.importorskip("streamlit.testing.v1")


def _run(project):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(_VIEW, default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_invalid_apply_is_rejected_and_page_stays_alive():
    from sloads import io

    project = io.load_project(_GA6)
    before_area = project.geometry.parametric.wing_area_sqft
    assert before_area > 0

    at = _run(project)
    # Drive the wing area to 0 and Apply.
    {n.label: n for n in at.number_input}["Area S (ft²)"].set_value(0.0)
    apply_button(at, "layout_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]

    # (1) The invalid layout was NOT persisted -- the last valid area survives.
    assert at.session_state["project"].geometry.parametric.wing_area_sqft == before_area
    # (2) A targeted rejection message is shown.
    assert any("not applied" in (e.value or "").lower() for e in at.error), \
        [e.value for e in at.error]
    # (3) The page stayed alive: the unrelated empennage & landing-gear forms (which
    #     live *below* the old blanking st.stop()) still render their Apply buttons.
    apply_button(at, "empennage_form")
    apply_button(at, "landing_gear_form")


def test_valid_apply_persists():
    """A valid edit still applies (guard against over-rejection)."""
    from sloads import io

    project = io.load_project(_GA6)
    at = _run(project)
    {n.label: n for n in at.number_input}["Area S (ft²)"].set_value(200.0)
    apply_button(at, "layout_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].geometry.parametric.wing_area_sqft == 200.0
    assert not any("not applied" in (e.value or "").lower() for e in at.error)


def test_apply_keeps_the_gear_fields_the_form_used_to_drop():
    """#36: Apply must round-trip ``carrier``/``attach``/``weight_lb``.

    ``_gear_leg`` rebuilt ``LandingGearInput`` from the widgets it renders, and it
    rendered neither the G-2 carrier, the G-12 trunnion node nor the G-12a leg
    weight -- so a project that carried them lost them the moment the user pressed
    Apply, and the sbeam ground model exported with no gear nodes at all.
    """
    from sloads import GearCarrier, LandingGearInput, io

    project = io.load_project(_GA6)
    lg = project.geometry.landing_gear
    project.geometry.landing_gear = dataclasses.replace(
        lg,
        main_gear=dataclasses.replace(lg.main_gear, carrier=GearCarrier.WING,
                                      attach=(101.0, 34.0, 12.0), weight_lb=155.0),
        nose_gear=dataclasses.replace(lg.nose_gear, carrier=GearCarrier.BODY,
                                      attach=(22.0, 0.0, 9.0), weight_lb=48.0))

    at = _run(project)
    apply_button(at, "landing_gear_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]

    out = at.session_state["project"].geometry.landing_gear
    assert out.main_gear.carrier is GearCarrier.WING
    assert out.main_gear.attach == (101.0, 34.0, 12.0)
    assert out.main_gear.weight_lb == 155.0
    assert out.nose_gear.carrier is GearCarrier.BODY
    assert out.nose_gear.attach == (22.0, 0.0, 9.0)
    assert out.nose_gear.weight_lb == 48.0

    # ``carrier`` has no default (G-2), so "not stated" must survive Apply too --
    # a selector that silently picked BODY would be the guess the enum refuses.
    blank = dataclasses.replace(project.geometry.landing_gear,
                                main_gear=LandingGearInput(), nose_gear=LandingGearInput())
    project.geometry.landing_gear = blank
    at = _run(project)
    apply_button(at, "landing_gear_form").set_value(True).run()
    assert at.session_state["project"].geometry.landing_gear.main_gear.carrier is None


def test_apply_keeps_the_fin_root_waterline():
    """#36, same class one form up: the empennage Apply dropped B8a-1's waterline.

    Zeroing it does not look like data loss -- 0 is the documented "derive it"
    value -- so the fin quietly moved to the airplane centreline as a *marked
    assumption* on every Apply, which is the failure mode the marking exists to
    make visible.
    """
    from sloads import io

    project = io.load_project(_GA6)
    project.vtail_loads = dataclasses.replace(project.vtail_loads,
                                              vtail_root_waterline_z=41.5)
    at = _run(project)
    apply_button(at, "empennage_form").set_value(True).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].vtail_loads.vtail_root_waterline_z == 41.5


def _stated(value) -> bool:
    """Is this a value the project *states*, as opposed to an unset default?"""
    if value is None or value == "":
        return False
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def _losses(before, after, path=""):
    """Paths where ``before`` stated something and ``after`` no longer does."""
    if isinstance(before, dict):
        if not isinstance(after, dict):
            return [path] if _stated(before) and not _stated(after) else []
        out = []
        for k, v in before.items():
            out += _losses(v, after.get(k), f"{path}.{k}")
        return out
    if isinstance(before, list):
        if not isinstance(after, list):
            return [path] if _stated(before) and not _stated(after) else []
        if len(after) < len(before):
            return [f"{path} (list {len(before)} -> {len(after)})"]
        out = []
        for i, v in enumerate(before):
            out += _losses(v, after[i], f"{path}[{i}]")
        return out
    return [f"{path} ({before!r} -> {after!r})"] if _stated(before) and not _stated(after) else []


@pytest.mark.parametrize("view_name", sorted(
    f for f in os.listdir(os.path.join(_ROOT, "app", "views")) if f.endswith(".py")))
def test_apply_never_turns_a_stated_value_into_an_unstated_one(view_name):
    """The structural half of #36 (rule 3), swept over every page's every form.

    Both defects above are one shape -- a form rebuilds an input dataclass from the
    widgets it happens to render, and every field it does not render silently
    reverts to its default. A round-trip assertion per field would never keep up
    with the schema, so this presses each Apply button **without touching a single
    widget** and asserts that nothing the project stated has become unstated.

    Deliberately one-sided. Apply is allowed to *add* (``speeds.occupants`` seeded
    from the weight slice, an optional sub-record materialised as explicitly
    disabled) and to re-derive a number; what it may never do is delete. That is
    the difference between this and a strict equality check, and it is why this
    guard can be broad enough to cover all fourteen pages.
    """
    from streamlit.testing.v1 import AppTest

    from sloads import io

    path = os.path.join(_ROOT, "app", "views", view_name)

    def render():
        at = AppTest.from_file(path, default_timeout=90)
        at.session_state["project"] = io.load_project(_GA6)
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        return at

    at = render()
    before = io.project_to_dict(io.load_project(_GA6))
    forms = sorted({b.proto.form_id for b in at.button if b.proto.form_id})
    if not forms:
        pytest.skip(f"{view_name} has no Apply form")

    for form in forms:
        at = render()
        hits = [b for b in at.button if b.proto.form_id == form]
        if not hits:
            continue
        hits[0].set_value(True).run()
        assert not at.exception, [e.message for e in at.exception]
        lost = _losses(before, io.project_to_dict(at.session_state["project"]))
        assert not lost, (
            f"pressing Apply on {view_name} form {form!r}, with no widget touched, "
            "erased values the project stated:\n  " + "\n  ".join(lost))


if __name__ == "__main__":  # zero-dependency-ish fallback (needs streamlit)
    test_invalid_apply_is_rejected_and_page_stays_alive()
    test_valid_apply_persists()
    test_apply_keeps_the_gear_fields_the_form_used_to_drop()
    test_apply_keeps_the_fin_root_waterline()
    for _v in sorted(f for f in os.listdir(os.path.join(_ROOT, "app", "views"))
                     if f.endswith(".py")):
        test_apply_never_turns_a_stated_value_into_an_unstated_one(_v)
    print("ok")
