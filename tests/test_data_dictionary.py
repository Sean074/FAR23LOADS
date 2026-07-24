"""Drift guard for the generated project.json data dictionary.

`docs/generate_data_dict.py` introspects `sloads.models` and writes
`docs/10_standard/DATA_DICTIONARY.md`. This test asserts the committed doc is
in sync with the current dataclasses (so a schema change that forgets to
regenerate fails CI) and that every input slice is documented.
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GEN = os.path.join(_REPO, "docs", "generate_data_dict.py")
_DOC = os.path.join(_REPO, "docs", "10_standard", "DATA_DICTIONARY.md")


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_data_dict", _GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_doc_matches_generator():
    gen = _load_generator()
    with open(_DOC, encoding="utf-8") as fh:
        committed = fh.read()
    assert committed == gen.build(), (
        "DATA_DICTIONARY.md is stale — regenerate it: "
        "`.venv/bin/python docs/generate_data_dict.py`"
    )


def test_every_input_slice_is_documented():
    gen = _load_generator()
    doc = gen.build()
    for attr, _role in gen.INPUT_SLICES:
        assert f"`{attr}`" in doc, f"slice {attr} missing from data dictionary"


def test_schema_version_recorded():
    import sloads.models as models

    gen = _load_generator()
    assert f"Schema version: **{models.SCHEMA_VERSION}**" in gen.build()


def test_gui_design_schema_line_current():
    """The hand-written GUI_design.md schema line matches models.SCHEMA_VERSION.

    This line went stale three times (v31, v32 and the v33 bump — the 2026-07-21
    review's single CRITICAL and the 2026-07-23 review's CRITICAL were the same
    defect); this guard makes a fourth occurrence unmergeable (M4-16).
    """
    import sloads.models as models

    doc = os.path.join(_REPO, "docs", "10_standard", "GUI_design.md")
    with open(doc, encoding="utf-8") as fh:
        text = fh.read()
    assert f"`SCHEMA_VERSION = {models.SCHEMA_VERSION}`" in text, (
        f"GUI_design.md's 'currently `SCHEMA_VERSION = …`' paragraph is stale — "
        f"update it (and its migration-history list) to {models.SCHEMA_VERSION}."
    )


if __name__ == "__main__":
    test_committed_doc_matches_generator()
    test_every_input_slice_is_documented()
    test_schema_version_recorded()
    test_gui_design_schema_line_current()
    print("ok")
