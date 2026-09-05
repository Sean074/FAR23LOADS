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


def test_gui_design_schema_paragraph_points_at_the_owner():
    """GUI_design.md's schema paragraph names the owner, never the number.

    M4-16 guarded the *value* here (the line went stale three times: v31, v32,
    the v33 bump) — which kept the copy current but kept the copy. The 2026-08-16
    documentation-currency rule (`00_program_overview.md`) retires the copy: the
    paragraph points at `SCHEMA_VERSION` in `sloads/models/project.py`, and
    `tests/test_doc_currency.py` fails on any literal beside it. This asserts the
    pointer is present, so the paragraph cannot silently lose it either.
    """
    doc = os.path.join(_REPO, "docs", "10_standard", "GUI_design.md")
    with open(doc, encoding="utf-8") as fh:
        text = fh.read()
    assert "`SCHEMA_VERSION`, whose owner is `sloads/models/project.py`" in text, (
        "GUI_design.md's schema paragraph must point at the SCHEMA_VERSION owner (no literal value)."
    )


if __name__ == "__main__":
    test_committed_doc_matches_generator()
    test_every_input_slice_is_documented()
    test_schema_version_recorded()
    test_gui_design_schema_paragraph_points_at_the_owner()
    print("ok")
