"""A render pass must not mutate the project (M2-3, review G4).

The sidebar's "Unsaved changes" flag is ``project_to_dict(p) != saved_snapshot``
(``app/Home.py``). Two views used to *auto-seed* derived slices on every render --
``flight_envelope`` wrote ``flight_loads`` and ``structural_speeds`` wrote
``speeds.mach_limit`` -- so merely visiting them tripped the dirty flag with zero
user edits and fired the discard-confirm dialog spuriously.

These views now persist only on an explicit **Apply** (``st.form_submit_button``),
computing the live diagram from an in-memory copy. This test drives each view via
``AppTest`` with **no widget interaction** and asserts the seeded project's
serialized form is byte-for-byte unchanged -- the regression guard for the fix.
"""

import glob
import logging
import os

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VIEWS_DIR = os.path.join(_ROOT, "app", "views")
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))

# The two views the review flagged (G4). Both reach their persist path on any
# example that carries the upstream slices; on a sparser example they gate out
# early -- either way a plain render must leave the project untouched.
_VIEWS = ["structural_speeds.py", "flight_envelope.py"]

pytest.importorskip("streamlit.testing.v1")


def _ids(paths):
    return [os.path.basename(p) for p in paths]


@pytest.mark.parametrize("view", _VIEWS)
@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_render_leaves_project_unchanged(view, example):
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(example)
    before = io.project_to_dict(project)  # a fresh snapshot dict

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, view), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]

    after = io.project_to_dict(at.session_state["project"])
    assert after == before, (
        f"{view} mutated the project on render for {os.path.basename(example)} "
        "(dirty flag would trip with no user edit)"
    )


_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


def _apply_buttons(at):
    return [b for b in at.button if "Apply" in (b.label or "")]


def test_mach_limit_persists_only_on_apply():
    """structural_speeds: MACHLIM is absent after a plain render, present after Apply."""
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(_GA6)
    project.speeds.mach_limit = None  # observe a fresh seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "structural_speeds.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].speeds.mach_limit is None, "render seeded MACHLIM"

    # The Speed-Altitude tab's Apply is the second "Apply" submit button.
    _apply_buttons(at)[1].set_value(True).run()
    assert at.session_state["project"].speeds.mach_limit is not None, "Apply did not persist"


def test_flight_loads_persists_only_on_apply():
    """flight_envelope: flight_loads is absent after a plain render, present after Apply."""
    from streamlit.testing.v1 import AppTest

    from farloads import io

    project = io.load_project(_GA6)
    project.flight_loads = None  # observe a fresh seed

    at = AppTest.from_file(os.path.join(_VIEWS_DIR, "flight_envelope.py"), default_timeout=60)
    at.session_state["project"] = project
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["project"].flight_loads is None, "render seeded flight_loads"

    _apply_buttons(at)[0].set_value(True).run()
    assert at.session_state["project"].flight_loads is not None, "Apply did not persist"


if __name__ == "__main__":  # zero-dependency-ish fallback (needs streamlit)
    for _view in _VIEWS:
        for _ex in _EXAMPLES:
            test_render_leaves_project_unchanged(_view, _ex)
    test_mach_limit_persists_only_on_apply()
    test_flight_loads_persists_only_on_apply()
    print("ok")
