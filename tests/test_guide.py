"""Acceptance gates G-UG-1…G-UG-6 for the oracle GUI user guide (note 34, #96).

The guide (``docs/60_guide/``) is one chapter per oracle page in
``sloads.workflow.oracle_steps()`` order, field tables generated from
``sloads/field_registry.py`` (never hand-written), screenshots from a
re-runnable capture script, and two worked examples carried through every
chapter. These gates landed with the scaffolding — before any chapter's prose —
so every chapter is checked on arrival rather than retrofitted (UG-10).
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GUIDE = os.path.join(_ROOT, "docs", "60_guide")
_GEN = os.path.join(_GUIDE, "_generated")
_IMG = os.path.join(_GUIDE, "img")

#: The non-chapter guide files allowed to share the ``NN_`` prefix space.
_FRONT_MATTER = {
    "00_index.md",
    "01_getting_started.md",
    "02_before_you_start.md",
    "03_conventions.md",
}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _generator():
    return _load(os.path.join(_ROOT, "docs", "generate_data_dict.py"),
                 "generate_data_dict")


def _capture_script():
    return _load(os.path.join(_ROOT, "scripts", "capture_guide_shots.py"),
                 "capture_guide_shots")


def _guide_md():
    """Every hand-written .md in the guide (generated files excluded)."""
    return sorted(
        f for f in os.listdir(_GUIDE)
        if f.endswith(".md") and os.path.isfile(os.path.join(_GUIDE, f))
    )


def _chapter_files():
    gen = _generator()
    return [f"{nn}_{step.key}.md" for nn, step in gen.guide_chapters()]


# --- G-UG-1: chapters <-> oracle steps, both ways -------------------------- #

def test_g_ug_1_every_oracle_step_has_exactly_one_chapter():
    expected = set(_chapter_files())
    missing = sorted(f for f in expected
                     if not os.path.exists(os.path.join(_GUIDE, f)))
    assert not missing, (
        f"oracle steps with no chapter file: {missing} — regenerate: "
        "`.venv/bin/python docs/generate_data_dict.py` scaffolds them"
    )


def test_g_ug_1_every_numbered_file_maps_to_a_step():
    expected = set(_chapter_files()) | _FRONT_MATTER
    stray = sorted(
        f for f in _guide_md()
        if re.match(r"^\d{2}_", f) and f not in expected
    )
    assert not stray, (
        f"numbered guide files that are neither front matter nor a chapter of "
        f"an oracle step: {stray}"
    )


# --- G-UG-2: generated tree exactly reproduces the generator --------------- #

def test_g_ug_2_generated_files_match_generator():
    gen = _generator()
    tables = gen.build_guide_tables()
    on_disk = sorted(f for f in os.listdir(_GEN) if f.endswith(".md"))
    assert on_disk == sorted(tables), (
        "docs/60_guide/_generated/ file set does not match the generator — "
        "regenerate: `.venv/bin/python docs/generate_data_dict.py`"
    )
    for name, content in tables.items():
        with open(os.path.join(_GEN, name), encoding="utf-8") as fh:
            assert fh.read() == content, (
                f"_generated/{name} is stale or hand-edited — regenerate: "
                "`.venv/bin/python docs/generate_data_dict.py`"
            )


# --- G-UG-3: images referenced <-> images present, with alt text ----------- #

_IMG_REF = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def _image_refs():
    """(file, alt, target) for every image reference in the guide."""
    refs = []
    for base, _dirs, files in os.walk(_GUIDE):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(base, f)
            with open(path, encoding="utf-8") as fh:
                for alt, target in _IMG_REF.findall(fh.read()):
                    refs.append((path, alt, target))
    return refs


def test_g_ug_3_every_referenced_image_exists_with_alt_text():
    problems = []
    for path, alt, target in _image_refs():
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if not os.path.exists(resolved):
            problems.append(f"{os.path.relpath(path, _ROOT)}: missing image {target}")
        if not alt.strip():
            problems.append(f"{os.path.relpath(path, _ROOT)}: image {target} has no alt text")
    assert not problems, "\n".join(problems)


def test_g_ug_3_every_image_in_img_is_referenced():
    if not os.path.isdir(_IMG):
        return  # no images yet — vacuously true
    referenced = {
        os.path.normpath(os.path.join(os.path.dirname(path), target))
        for path, _alt, target in _image_refs()
    }
    unreferenced = sorted(
        f for f in os.listdir(_IMG)
        if f.endswith(".png")
        and os.path.normpath(os.path.join(_IMG, f)) not in referenced
    )
    assert not unreferenced, f"images in img/ referenced by no chapter: {unreferenced}"


# --- G-UG-4: both worked examples run every oracle module they reach ------- #

def _guide_examples():
    return _capture_script().GUIDE_EXAMPLES


def test_g_ug_4_examples_declared():
    examples = _guide_examples()
    assert "ga6_normal" in examples, "the single is a guide example (UG-5)"
    for name in examples:
        assert os.path.exists(
            os.path.join(_ROOT, "examples", f"{name}.project.json")
        ), f"guide example {name} has no examples/ file"


@pytest.mark.parametrize("name", sorted(_guide_examples()))
def test_g_ug_4_example_runs_every_oracle_module_it_reaches(name):
    import sloads.modules  # noqa: F401  -- self-registers every module
    from sloads import MissingInputError, io, registry, workflow as w

    spec = _guide_examples()[name]
    not_reached = set(spec.get("not_reached", ()))
    project = io.load_project(
        os.path.join(_ROOT, "examples", f"{name}.project.json")
    )
    for step in w.oracle_steps():
        if step.module is None:
            continue
        if step.key in not_reached:
            with pytest.raises(MissingInputError):
                registry.get(step.module)(project)
            continue
        result = registry.get(step.module)(project)
        assert result is not None, f"{name}: {step.module} returned nothing"


# --- G-UG-5: every relative link resolves ---------------------------------- #

_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")


def test_g_ug_5_every_relative_link_resolves():
    dangling = []
    for base, _dirs, files in os.walk(_GUIDE):
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(base, f)
            with open(path, encoding="utf-8") as fh:
                for target in _LINK.findall(fh.read()):
                    if target.startswith(("http://", "https://", "mailto:")):
                        continue
                    target = target.split("#", 1)[0]
                    if not target:
                        continue  # in-page anchor
                    resolved = os.path.normpath(
                        os.path.join(os.path.dirname(path), target)
                    )
                    if not os.path.exists(resolved):
                        dangling.append(
                            f"{os.path.relpath(path, _ROOT)} -> {target}"
                        )
    assert not dangling, "dangling guide links:\n" + "\n".join(dangling)


# --- G-UG-6: every chapter carries the eight headings, in order ------------ #

def test_g_ug_6_chapter_template_headings_in_order():
    gen = _generator()
    expected = list(gen.CHAPTER_HEADINGS)
    for name in _chapter_files():
        with open(os.path.join(_GUIDE, name), encoding="utf-8") as fh:
            headings = [
                line[3:].strip() for line in fh.read().splitlines()
                if line.startswith("## ")
            ]
        assert headings == expected, (
            f"{name}: `##` headings differ from the note-34 §3 template — "
            f"got {headings}"
        )


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
