"""Drift guard for the generated project.json data dictionary.

`docs/generate_data_dict.py` introspects `farloads.models` and writes
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
    import farloads.models as models

    gen = _load_generator()
    assert f"Schema version: **{models.SCHEMA_VERSION}**" in gen.build()


if __name__ == "__main__":
    test_committed_doc_matches_generator()
    test_every_input_slice_is_documented()
    test_schema_version_recorded()
    print("ok")
