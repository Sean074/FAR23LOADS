"""A JSON ``null`` is refused where ``None`` is not a value (#121).

``sloads.io`` coerced numeric *containers* (#76) and said so in its own block
comment -- "Scalars are deliberately NOT in scope here". So a scalar ``null``
went straight through into whatever field it named: ``"full_down_aileron_deg":
null`` landed on a field declared ``float = 0.0``, the file loaded clean, and the
main GUI died three modules later at ``float(None)`` -- a raw ``TypeError`` out
of a ``st.number_input``, on a page the user had only opened.

The refusal is at the loader rather than at the widget on purpose. It is the one
boundary that maps JSON onto the dataclasses, so one guard there covers every
field and both GUIs, where hardening the ~137 ``float(...)`` calls in
``app/views`` would have covered one directory and rotted at the next widget
(rule 3 + rule 4). The alternative -- reading the null as the field's default --
is the silent zeroing ``test_the_limnz_derive_refuses_rather_than_resolving_to_zero``
already refuses for #122: the author's intent is not recoverable from the file.

The assertions are stated over the whole class, not over the field that found
it. Every scalar in every shipped example is nulled in turn, and the null must
either be **refused by name** or land as a **meaningful ``None``** on an
``Optional`` field -- never a traceback, and never quietly swallowed into the
default, which is the same defect wearing the other face.
"""

import copy
import dataclasses
import glob
import importlib
import json
import os
import pkgutil
import sys
import typing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from sloads import io

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.project.json")))
_GA6 = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


def _ids(paths):
    return [os.path.basename(p).split(".")[0] for p in paths]


def _scalar_sites(raw):
    """Every scalar leaf in a raw project dict, as a list-of-keys path.

    Read off the file rather than off the schema: what has to survive being
    nulled is what a hand-edited (or foreign-written) file can actually say.
    """
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, path + [key])
                elif value is not None:
                    out.append(path + [key])
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, path + [i])

    walk(raw, [])
    return out


def _with_null_at(raw, path):
    d = copy.deepcopy(raw)
    cur = d
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = None
    return d


@pytest.mark.parametrize("example", _EXAMPLES, ids=_ids(_EXAMPLES))
def test_a_null_is_refused_by_name_or_lands_as_a_meaningful_none(example):
    """The whole class, over every scalar the file holds.

    Two failure modes, one test, because fixing either one alone re-opens the
    other: a ``TypeError``/``AttributeError`` escaping means the null reached a
    consumer (the #121 crash), and a null that changes *nothing* means the
    loader read it as the field's default and the user's file now disagrees with
    the project in memory (the silent half, which no "nothing escaped" sweep can
    see).
    """
    with open(example, encoding="utf-8") as fh:
        raw = json.load(fh)
    baseline = io.project_to_dict(io.project_from_dict(copy.deepcopy(raw)))

    escaped, swallowed = [], []
    for path in _scalar_sites(raw):
        where = ".".join(str(p) for p in path)
        try:
            loaded = io.project_to_dict(
                io.project_from_dict(_with_null_at(raw, path)))
        except ValueError:
            continue                       # refused by name: the contract
        except Exception as exc:  # that is the finding
            escaped.append(f"{where} -> {type(exc).__name__}: {exc}")
            continue
        if loaded == baseline:
            swallowed.append(where)

    assert not escaped, (
        "a null in the project file reached a consumer as a traceback rather "
        f"than a named refusal at the loader (#121): {escaped}")
    assert not swallowed, (
        "a null in the project file was read as the field's default and "
        "changed nothing -- the file and the loaded project disagree, with "
        f"nothing said (#121, the silent half): {swallowed}")


def test_the_refusal_names_the_record_and_the_field():
    """The message is the whole of what the user gets, so it has to locate the
    key in the file they must edit -- ``_NOT_READY``-style (#73), not a bare
    type. ``full_down_aileron_deg`` is the field that found the class."""
    with open(_GA6, encoding="utf-8") as fh:
        raw = json.load(fh)
    raw["select_input"]["full_down_aileron_deg"] = None

    with pytest.raises(ValueError) as exc:
        io.project_from_dict(raw)

    message = str(exc.value)
    assert "SelectInput" in message, message
    assert "full_down_aileron_deg" in message, message
    assert "null" in message, message


def test_an_optional_field_keeps_its_null():
    """The refusal must not eat the states where ``None`` is the answer.

    ``SurfaceInput.front_spar_pct`` is ``None = not entered`` (M4-1) and the gear
    ``carrier`` is ``None = not stated`` (G-2) -- both meaningful, both written
    as ``null`` by this app's own writer.
    """
    with open(_GA6, encoding="utf-8") as fh:
        raw = json.load(fh)
    raw["geometry"]["surfaces"][0]["front_spar_pct"] = None

    project = io.project_from_dict(raw)
    assert project.geometry.surfaces[0].front_spar_pct is None


def _model_dataclasses():
    import sloads.models as models

    seen = {}
    for mod in pkgutil.walk_packages(models.__path__, models.__name__ + "."):
        module = importlib.import_module(mod.name)
        for obj in vars(module).values():
            if (isinstance(obj, type) and dataclasses.is_dataclass(obj)
                    and obj.__module__.startswith("sloads.")):
                seen[obj] = True
    return list(seen)


def test_no_model_field_defaults_to_none_outside_an_optional_annotation():
    """What makes the refusal safe to turn on: this app cannot write a file it
    would then refuse to read.

    A field defaulting to ``None`` under a non-``Optional`` annotation would be
    written as ``null`` by ``asdict`` and refused on the way back in -- a
    save/reload round trip that fails. There are none today; this fails the
    build the day one is added, next to the field rather than in a bug report.
    """
    offenders = []
    for cls in _model_dataclasses():
        try:
            hints = typing.get_type_hints(cls)
        except Exception:  # unresolvable forward ref
            continue
        nullable = io._nullable_fields(cls)
        for field in dataclasses.fields(cls):
            if field.default is None and field.name not in nullable:
                offenders.append(f"{cls.__name__}.{field.name}: {hints.get(field.name)}")
    assert not offenders, (
        "a model field defaults to None under an annotation that does not admit "
        "it -- save writes null and load refuses it (#121). Annotate it "
        f"Optional[...], or give it a real default: {offenders}")


if __name__ == "__main__":  # zero-dependency self-runner
    for _ex in _EXAMPLES:
        test_a_null_is_refused_by_name_or_lands_as_a_meaningful_none(_ex)
    test_the_refusal_names_the_record_and_the_field()
    test_an_optional_field_keeps_its_null()
    test_no_model_field_defaults_to_none_outside_an_optional_annotation()
    print("ok")
