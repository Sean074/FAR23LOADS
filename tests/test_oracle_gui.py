"""The oracle GUI's acceptance gates (design note 32, step OG-D).

Three gates from the note, plus the guards the generic renderer needs to stay
honest:

* **G1 — no dual path.** ``oracle_app/`` imports its numbers from ``sloads`` and
  the shared shell only: no unit factor of its own, no arithmetic library, no
  private CSV writer. The second front-end exists to ask for less, not to
  recompute anything.
* **G2 — the page set is derived.** The rendered pages are exactly
  :func:`sloads.workflow.oracle_steps`, and no module in the GUI holds a literal
  list of step keys. Adding a ``bas`` to a workflow step must add a page with no
  edit to the GUI at all -- so the test that matters is not "the list is right"
  but "there is no list".
* **G6 — round-trip.** A project the oracle GUI would save opens in ``app/``
  unchanged, and re-saves byte-identically. OG-13's promise from the outside:
  one schema, two front-ends, no hop.

The smoke run is the one that earns its keep day to day: fourteen pages built
from one renderer means a single introspection mistake takes out every page, and
a registry row whose type the renderer cannot map is a crash rather than a
missing widget.
"""

import ast
import glob
import io as _io
import json
import logging
import os
import re
from itertools import takewhile

import pytest

logging.disable(logging.CRITICAL)  # silence Streamlit's bare-mode warnings

from helpers import widget_editing, widgets_editing  # noqa: E402
from sloads import field_registry as fr  # noqa: E402
from sloads import io  # noqa: E402
from sloads import workflow as wf  # noqa: E402
from sloads.field_registry import reduce_to_oracle_inputs  # noqa: E402
from app_shell.components import active_system  # noqa: E402
from sloads.units import AVIATION_STANDARD, to_display  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GUI = os.path.join(_ROOT, "oracle_app")
_ENTRYPOINT = os.path.join(_GUI, "Oracle.py")
_EXAMPLES = os.path.join(_ROOT, "examples")
_EXAMPLE = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_SOURCES = sorted(glob.glob(os.path.join(_GUI, "*.py")))
#: The shared shell renders *inside* this GUI, so a download it offers is a
#: download the oracle GUI offers. Scanning only ``oracle_app/`` made G7's
#: completeness argument true of half the running app (review CR-A-8).
_SHELL = os.path.join(_ROOT, "app_shell")
_DOWNLOAD_SOURCES = _SOURCES + sorted(glob.glob(os.path.join(_SHELL, "*.py")))

pytest.importorskip("streamlit.testing.v1")


def _file_name_of(call):
    """The ``file_name=`` a ``download_button`` call writes, as a literal.

    An f-string is flattened to its literal parts (``f"{fname}.project.json"``
    -> ``".project.json"``), which is all this gate needs: the extension is what
    says whether the file is a load deliverable. ``None`` when the argument is
    not a string literal at all -- which fails the check rather than passing it.
    """
    for kw in call.keywords:
        if kw.arg != "file_name":
            continue
        node = kw.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(v.value for v in node.values
                           if isinstance(v, ast.Constant) and isinstance(v.value, str))
        # The shell names the project file through its one sanitiser (#65);
        # the call *is* the statement that the file is ``<stem>.project.json``.
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "project_filename":
            from sloads.io import PROJECT_SUFFIX
            return PROJECT_SUFFIX
        # Likewise the results zip's one naming owner (C210-45): the call *is*
        # the statement that the file is ``<stem>_results.zip``
        # (``test_results_zip.py`` asserts the suffix on the real name).
        if isinstance(node, ast.Call) and (
                getattr(node.func, "id", "") or getattr(node.func, "attr", "")
        ) in ("results_zip_name", "_results_zip_name"):
            return "_results.zip"
    return None


def _parse(path):
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def _seeded():
    return io.load_project(_EXAMPLE)


# --------------------------------------------------------------------------- #
# G1 -- no dual path
# --------------------------------------------------------------------------- #
#: What the oracle GUI may import. ``sloads`` and ``app_shell`` are the owners;
#: ``streamlit``/``pandas`` are the presentation layer; the rest is stdlib
#: introspection the generic renderer is built out of. A numerical library is
#: deliberately absent: there is nothing here to compute.
_ALLOWED_IMPORTS = {
    "sloads", "app_shell", "oracle_app", "streamlit", "pandas",
    "dataclasses", "typing", "enum", "__future__",
}

#: Imperial->SI factors. A literal from this set inside a front-end means it has
#: started converting on its own -- the defect class ``units.py`` is the single
#: owner of (CONVENTIONS.md §7). Mirrors ``test_constants.py``'s scan.
_SI_FACTORS = re.compile(
    r"\b(25\.4|0\.3048|0\.45359|4\.4482|1\.35581|6\.89475|9\.80665|386\.0)")


def test_the_oracle_gui_imports_only_owners_and_presentation():
    """Gate G1, first half: nothing to compute with, nowhere else to get a number."""
    offenders = []
    for path in _SOURCES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Import):
                roots = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                roots = [(node.module or "").split(".")[0]]
            else:
                continue
            for root in roots:
                if root and root not in _ALLOWED_IMPORTS:
                    offenders.append(f"{os.path.relpath(path, _ROOT)}: imports {root!r}")
    assert not offenders, (
        "the oracle GUI imports something outside sloads / app_shell / the "
        "presentation layer -- it is a front-end, not a second analysis path "
        "(note 32, OG-1/G1):\n" + "\n".join(offenders))


def test_the_oracle_gui_holds_no_unit_factor_of_its_own():
    """Gate G1, second half: every conversion goes through ``sloads.units``."""
    offenders = []
    for path in _SOURCES:
        with open(path, encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if _SI_FACTORS.search(line):
                    offenders.append(f"{os.path.relpath(path, _ROOT)}:{number}: {line.strip()}")
    assert not offenders, (
        "a unit factor literal in a GUI package -- convert through "
        "sloads.units (owner) or app_shell's unit_number_input:\n"
        + "\n".join(offenders))


def test_the_oracle_gui_writes_no_deliverable_of_its_own():
    """Gate G1, third half: no private CSV writer. Every file the GUI offers is
    rendered by ``sloads.io``/``sloads.report`` or by ``app_shell.limit_csv``
    (OG-6 as amended) -- a ``to_csv`` here would be a fourth format nothing
    else in the project can vouch for."""
    offenders = []
    for path in _SOURCES:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        for marker in ("to_csv(", "csv.writer", "DictWriter"):
            if marker in source:
                offenders.append(f"{os.path.relpath(path, _ROOT)}: {marker}")
    assert not offenders, (
        "the oracle GUI builds a CSV itself -- route it through the existing "
        "owners (note 32, OG-6/G7):\n" + "\n".join(offenders))


# --------------------------------------------------------------------------- #
# G2 -- the page set is derived
# --------------------------------------------------------------------------- #
def test_there_is_no_page_list_in_the_gui():
    """Gate G2, the part that actually prevents drift.

    A correct hand-written page list is still a hand-written page list: it stops
    being correct the day a workflow step gains a ``bas``. So the assertion is
    that no step key appears as a string literal anywhere in the GUI at all.
    """
    keys = set(wf.BY_KEY)
    offenders = []
    for path in _SOURCES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Constant) and node.value in keys:
                offenders.append(
                    f"{os.path.relpath(path, _ROOT)}:{node.lineno}: {node.value!r}")
    assert not offenders, (
        "a workflow step key is written out in the oracle GUI -- its page set "
        "is derived from workflow.oracle_steps() and must stay so (OG-2/G2):\n"
        + "\n".join(offenders))


def _module_assignments(tree):
    """``{name: value node}`` for the entry point's module-level assignments."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = node.value
    return out


def _derives_from(node, assignments, wanted, _seen=None):
    """True if ``node`` reaches a call to ``wanted``, following module names."""
    _seen = _seen or set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Attribute) and inner.attr == wanted:
            return True
        if isinstance(inner, ast.Name) and inner.id in assignments and inner.id not in _seen:
            _seen.add(inner.id)
            if _derives_from(assignments[inner.id], assignments, wanted, _seen):
                return True
    return False


def test_the_entry_point_navigates_the_derived_step_set():
    """Gate G2: the navigated page set is built from ``oracle_steps()`` -- and
    the page set the link helper resolves against is *the same one* (OG-F).

    Two page sets built from the same source would still drift the day one of
    them gains a filter; the assertion is that there is one set, derived, used
    twice.
    """
    tree = ast.parse(open(_ENTRYPOINT, encoding="utf-8").read())
    assignments = _module_assignments(tree)
    calls = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in ("navigation", "register_pages"):
                calls.setdefault(name, []).append(node)

    assert len(calls.get("navigation", [])) == 1, "expected exactly one st.navigation call"
    assert len(calls.get("register_pages", [])) == 1, (
        "the oracle GUI must register its page set exactly once, for the links")
    for name, call in ((n, c[0]) for n, c in calls.items()):
        assert _derives_from(call.args[0], assignments, "oracle_steps"), (
            f"{name}() is not built from workflow.oracle_steps()")


def test_the_derived_page_set_is_the_fourteen_oracle_steps():
    """The set itself, so a change to ``oracle_steps`` is visible here too."""
    keys = [s.key for s in wf.oracle_steps()]
    assert keys == [s.key for s in wf.STEPS if s.key in wf.oracle_step_keys()]
    assert set(keys) == wf.oracle_step_keys()
    assert len(keys) == 14


# --------------------------------------------------------------------------- #
# The renderer
# --------------------------------------------------------------------------- #
#: A one-page script: the whole GUI body is ``render_step`` bound to a key, so
#: this is exactly what ``Oracle.py``'s navigation runs for that page.
_PAGE_SCRIPT = "from oracle_app.form import render_step\nrender_step({key!r})\n"


def _render(key, project=None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(_PAGE_SCRIPT.format(key=key), default_timeout=60)
    at.session_state["project"] = project if project is not None else _seeded()
    at.run()
    return at


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_oracle_page_renders(key):
    """One renderer, fourteen pages: an introspection mistake takes out all of
    them, and a field type it cannot map is a crash, not a missing widget."""
    at = _render(key)
    assert not at.exception, [e.message for e in at.exception]


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_oracle_page_renders_on_an_empty_project(key):
    """The state the GUI is *for*: a blank project, every slice absent. The
    renderer has to create the records rather than gate on them."""
    from sloads import Project

    at = _render(key, Project(name=""))
    assert not at.exception, [e.message for e in at.exception]


# --------------------------------------------------------------------------- #
# Scope -- concept mode is not this GUI's (OG-1; review 2026-08-20 CR-A-4)
# --------------------------------------------------------------------------- #
# The shared header rendered the applicability banner with its default
# ``switch_action=True``, so an out-of-band airplane got a **Switch to Concept**
# button on a front-end that carries no concept page and shows no concept field:
# one click wrote ``speeds.category="C"`` and seeded ``chosen_n``/``chosen_nneg``
# into a project the user could then only get back in ``app/``. The warning
# itself belongs here -- it says the numbers are an extrapolation -- so the fix
# is warning-without-action, not ``banner=False``.
def _out_of_band():
    """The Appendix-A GA single re-stated above the 12,500 lb FAR 23 ceiling.

    Both members move together because the gate reads the MTOW SSOT (G-14) and
    ``speeds.weight_lb`` is its derived read.
    """
    project = _seeded()
    project.weight.max_takeoff_weight_lb = 20000.0
    project.speeds.weight_lb = 20000.0
    return project


def test_an_out_of_band_airplane_is_warned_but_offered_no_concept_switch():
    """The banner states the exceedance; the action that leaves this GUI's
    scope is gone."""
    at = _render(sorted(wf.oracle_step_keys())[0], _out_of_band())
    assert not at.exception, [e.message for e in at.exception]

    warnings = " ".join(w.value for w in at.warning)
    assert "Exceeds FAR 23 applicability" in warnings, (
        "the oracle GUI stopped telling an out-of-band airplane its results are "
        "a concept-mode extrapolation")
    labels = [b.label for b in at.button]
    assert "Switch to Concept" not in labels, (
        "the oracle GUI offers the switch to concept mode, which it does not "
        "carry a single page or field for (OG-1, CR-A-4)")


# --------------------------------------------------------------------------- #
# The entry-error channel (#82, C210-35)
# --------------------------------------------------------------------------- #
def _contradictory_wing_row():
    """The C210-35 entry: a wing-tagged mass row also carrying ``wing_fraction``.

    ``wing_fraction`` is the wing-reacted fraction of a row tagged to *another*
    component, so 1 on a wing row is a contradiction the checks name. This is the
    exact entry that survived a whole build review unshown.
    """
    from sloads.models import MassComponent

    project = _seeded()
    item = next(i for i in project.weight.items
                if i.component == MassComponent.WING)
    item.wing_fraction = 1.0
    return project


def test_an_entry_error_is_shown_on_the_page_that_owns_it():
    """The oracle GUI renders the ``consistency_warnings`` channel (#82).

    Until this, ``oracle_app``/``app_shell`` had no consumer of
    ``ConsistencyWarning`` at all: a page-targeted entry-error channel that is
    part of the analysis contract (C210-15) was dark exactly where entries are
    made. Read from the rendered warnings, not from the source.
    """
    at = _render("weight_mass", _contradictory_wing_row())
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "wing_fraction" in shown, (
        "the oracle GUI's weights page does not show the entry-error warning "
        "its own validator raises")


def test_an_entry_error_is_not_shown_on_a_page_that_does_not_own_it():
    """The ``page`` tag is honoured, not ignored: the same project's warning
    must not appear on an unrelated page, or every page becomes a wall of text
    and the targeting the channel is built on means nothing."""
    at = _render("flap_loads", _contradictory_wing_row())
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "wing_fraction" not in shown, shown


def test_the_flap_page_says_when_the_slipstream_case_is_skipped():
    """#83 (C210-40) on the GUI the C210 was built in.

    The build entered the slipstream band (AF 15.2, BLPROP 0) with no engine
    record yet, and the page printed a critical flap load with the 23.457(b)
    amplification silently absent -- since #85, a delivered case that does not
    exist. The warning rides #82's channel, so the oracle GUI gets it with no
    per-page wiring at all.
    """
    project = _seeded()
    project.engines = []
    at = _render("flap_loads", project)
    assert not at.exception, [e.message for e in at.exception]
    shown = " ".join(w.value for w in at.warning)
    assert "slipstream effect included" in shown, [w.value for w in at.warning]
    assert "Engine Mount Loads" in shown, shown


def test_the_one_engine_out_page_withholds_its_form_on_a_single(monkeypatch):
    """#84 (C210-43): the page for a condition the airplane cannot have takes no
    input at all -- it says why and stops, instead of collecting a simulation's
    worth of transient inputs for a run that prints zeros under a false
    "uncontrollable" verdict."""
    project = _seeded()
    assert len(project.engines) == 1, "the GA6 fixture is the single this is about"
    at = _render("one_engine_out", project)
    assert not at.exception, [e.message for e in at.exception]
    said = " ".join(i.value for i in at.info)
    assert "FAR 23.367 does not apply" in said, said
    # No form, and no results table underneath it.
    assert not at.number_input, [w.label for w in at.number_input]
    assert not at.subheader, [s.value for s in at.subheader]


def test_the_aero_page_fills_the_stall_cl_it_was_given_field_by_field():
    """#81 (C210-23), on the real path rather than a stand-in for it.

    This GUI creates the coefficient sets blank and writes the CLmax trio
    afterwards, one widget at a time, so ``__post_init__`` -- which had the only
    copy of the M1-1b fill -- never ran again. The live sets kept
    ``stall_cl = 0.0`` and Flight Envelope and SELECT died on "float division by
    zero" until the project was saved and reloaded. Rendering the page must now
    leave a runnable slice behind, which is what ``refresh_derived`` (already
    called after every persist) does.
    """
    from sloads.models import AeroCoefficientsInput, AeroCoeffSet
    from sloads.modules.flight_envelope import build_envelope

    project = _seeded()
    authored = project.aero_coeffs.cruise
    project.aero_coeffs = AeroCoefficientsInput(cruise=AeroCoeffSet(
        name="CRUISE", lift=authored.lift, drag=authored.drag, moment=authored.moment))
    project.aero_coeffs.clmax_clean = 1.4068
    project.aero_coeffs.clmax_clean_neg = -0.59
    project.aero_coeffs.clmax_flap = 1.5857
    assert project.aero_coeffs.cruise.stall_cl == 0.0, "the state this is about"

    at = _render("aero_coefficients", project)
    assert not at.exception, [e.message for e in at.exception]
    live = at.session_state["project"]
    assert live.aero_coeffs.cruise.stall_cl == 1.4068
    assert live.aero_coeffs.cruise.neg_stall_cl == -0.59
    # The reported symptom, gone: the envelope runs without a save-and-reload.
    assert build_envelope(live).vn


def test_no_oracle_page_can_reach_the_concept_switch():
    """The drift guard behind the assertion above (``CLAUDE.md`` rule 3).

    Every shared-header call in the GUI has to disclaim the switch action --
    either by not rendering the banner at all or by rendering it without its
    button. A fifteenth page added the day this file is not touched inherits the
    shell default, and the behavioural test above only exercises one page.
    """
    offenders = []
    for path in _SOURCES:
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name not in ("page", "page_header", "render_applicability_banner"):
                continue
            passed = {kw.arg: kw.value for kw in node.keywords}
            off = [k for k in ("switch_action", "banner")
                   if isinstance(passed.get(k), ast.Constant) and passed[k].value is False]
            if not off:
                offenders.append(f"{os.path.relpath(path, _ROOT)}:{node.lineno}: {name}()")
    assert not offenders, (
        "an oracle-GUI page renders the shared header without disclaiming the "
        "switch-to-Concept action -- pass switch_action=False (CR-A-4):\n"
        + "\n".join(offenders))


def test_every_page_shows_every_field_the_registry_gives_it():
    """No field in the input set is dropped on the floor: the page groups
    partition the registry's rows for that page exactly."""
    from oracle_app.form import page_groups

    keep = fr.oracle_input_paths()
    shown = {p for key in wf.oracle_step_keys()
             for _prefix, paths in page_groups(key) for p in paths}
    expected = {row.path for row in fr.REGISTRY
                if row.path in keep and row.page in wf.oracle_step_keys()}
    assert shown == expected


def test_every_input_field_lands_on_an_oracle_page():
    """The other direction: a field in the input set whose editing page is not
    an oracle page would be unenterable, which is what amended OG-2."""
    keep = fr.oracle_input_paths()
    orphans = sorted(row.path for row in fr.REGISTRY
                     if row.path in keep and row.page not in wf.oracle_step_keys())
    assert not orphans, (
        "these fields are in the oracle GUI's input set but their editing page "
        f"is not an oracle page, so nothing can enter them: {orphans}")


def test_every_composite_field_declares_its_member_labels():
    """``MEMBER_LABELS`` is presentation, but it is hand-written, so it gets the
    same totality treatment as everything else here: a new composite field in
    the input set must be named, not silently rendered as "1, 2"."""
    from oracle_app.form import MEMBER_LABELS, is_composite

    from oracle_app.form import _enum_of, _list_element

    missing = sorted(
        path.rsplit(".", 1)[-1] for path in fr.oracle_input_paths()
        if is_composite(fr.field_type(path))
        # An enum set is a multiselect, not a row of members: its labels are the
        # enum's own names.
        and _enum_of(_list_element(fr.field_type(path))) is None
        and path.rsplit(".", 1)[-1] not in MEMBER_LABELS)
    assert not missing, (
        f"composite fields with no member labels in oracle_app.form: {missing}")


def test_the_aviation_units_agree_with_the_shell():
    """``units.AVIATION_STANDARD`` supplies ``unit_number_input``'s
    ``fixed_unit``, so its values must be the shell's own two labels -- not a
    third spelling of "knots"."""
    from app_shell.components import ALTITUDE_FT, KEAS

    assert set(AVIATION_STANDARD.values()) == {KEAS, ALTITUDE_FT}


# --------------------------------------------------------------------------- #
# G7 -- output contract
# --------------------------------------------------------------------------- #
# The gate reads the *payloads*, not the source. ``test_ultimate_contract.py``
# scans ``app/views/*.py`` for a literal ``file_name="....csv"`` and matches the
# call that built it; pointed at a derived GUI it would find no literal and pass
# on an empty set -- a green gate over an unchecked front-end, which is the
# failure OG-9 exists to prevent. So the subject here is
# ``results.page_artifacts``: the bytes a user actually downloads. Completeness
# comes from the call-site test below -- one ``download_button`` in the package,
# fed from the same function this gate reads.
_STAMP = "# BASIS: All loads reported here are ULTIMATE"
_TEXT_HEADER = "Loads are ULTIMATE (= limit x SF); load factors are limit."


def _artifacts(key, project=None):
    from sloads import UnitSystem
    from oracle_app.results import page_artifacts

    return page_artifacts(project if project is not None else _seeded(),
                          key, UnitSystem.IMPERIAL)


def test_the_gui_has_exactly_one_download_call_site():
    """What makes the payload gate *complete*: every file the oracle GUI offers
    is an ``Artifact`` from ``page_artifacts``, because there is nowhere else a
    download can be created. A second call site would be an artifact G7 never
    saw."""
    sites = []
    for path in _DOWNLOAD_SOURCES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "download_button":
                sites.append((os.path.relpath(path, _ROOT), node.lineno,
                              _file_name_of(node)))

    renderer = [s for s in sites if s[0] == os.path.join("oracle_app", "results.py")]
    assert len(renderer) == 1, (
        "the oracle GUI offers a load download from somewhere other than the one "
        "renderer -- gate G7 reads page_artifacts() and would not see it:\n"
        + "\n".join(f"{f}:{n}" for f, n, _ in renderer))

    # The shell's own downloads are allowed, and bounded: the project file is an
    # input, not a load deliverable, so it is outside G7 by content rather than
    # by which directory it lives in. Anything else the shell offers is a file a
    # user gets from this GUI that page_artifacts() never saw.
    # The results zip (C210-45) *is* a load deliverable, and its payload gate is
    # ``tests/test_results_zip.py``, which reads the artifact bytes the way this
    # file's G7 reads ``page_artifacts()``: the zip's members come from the same
    # two owners the per-page artifacts do (``module_text_report`` and
    # ``io.load_cases_csv`` + ``csv_comment_block``), so the ULT marker and the
    # basis statement are asserted on the bytes a user receives, not assumed.
    others = [s for s in sites if s not in renderer]
    offenders = [f"{f}:{n} -> {name}" for f, n, name in others
                 if name is None or not name.endswith((".project.json",
                                                       "_results.zip"))]
    assert not offenders, (
        "the shared shell offers a download the oracle GUI's output gate cannot "
        "see -- route it through results.page_artifacts() or state why it is not "
        "a load deliverable:\n" + "\n".join(offenders))


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_csv_the_oracle_gui_offers_states_its_basis(key):
    """Gate G7, the CSV half: ULTIMATE by the stamp and an ``SF`` column, or
    LIMIT in-band *and* in a ``*_LIMIT.csv`` filename. A load CSV with a neutral
    name and no basis is the M4-15 defect class."""
    for art in _artifacts(key):
        if not art.file_name.endswith(".csv"):
            continue
        body = [ln for ln in art.payload.splitlines() if not ln.startswith("#")]
        header = body[0] if body else ""
        if art.file_name.endswith("_LIMIT.csv"):
            assert "LIMIT" in art.payload, (
                f"{art.file_name} is named LIMIT but never says so in-band")
            assert _STAMP not in art.payload, (
                f"{art.file_name} claims ULTIMATE and LIMIT at once")
        else:
            # In the **comment block**, not merely somewhere in the payload
            # (review CR-A-8): a stamp that only has to appear anywhere is
            # satisfied by a data row that happens to contain the words, and a
            # consumer reads the head of the file, not a grep of it.
            head = list(takewhile(lambda ln: ln.startswith("#"),
                                  art.payload.splitlines()))
            assert any(ln.startswith(_STAMP) for ln in head), (
                f"{art.file_name} leaves the oracle GUI with no basis statement "
                f"in its comment block -- pass report.csv_comment_block(project)")
            assert "SF" in header.split(","), (
                f"{art.file_name} states ULTIMATE but has no per-case SF column")


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_every_text_report_says_what_the_cli_says(key):
    """Gate G7, the text half: the same ULT marker and per-case SF statement as
    ``cli.py``'s, which is guaranteed by being the same call -- so the assertion
    is byte equality with the CLI's own output, title line aside."""
    from sloads import UnitSystem, convert_results, registry
    from sloads.report import module_text_report

    project = _seeded()
    for art in _artifacts(key, project):
        if not art.file_name.endswith(".txt"):
            continue
        assert _TEXT_HEADER in art.payload, f"{art.file_name} drops the ULT statement"
        assert "[ULTIMATE, SF=" in art.payload, f"{art.file_name} states no per-case SF"
        module = art.file_name[: -len(".txt")]
        result = registry.get(module)(project)
        # cli.py: module_text_report(result.module, convert_results(...)).
        expected = module_text_report(
            module, convert_results(result.conditions, UnitSystem.IMPERIAL))
        assert art.payload.splitlines()[1:] == expected.splitlines()[1:], (
            f"{art.file_name} differs from the CLI's report for {module}")


def test_no_page_offers_two_files_with_the_same_name():
    """The download widget's key is the filename, so a collision is both a
    duplicate-key crash and two different files under one name."""
    for key in sorted(wf.oracle_step_keys()):
        names = [a.file_name for a in _artifacts(key)]
        assert len(names) == len(set(names)), (key, names)


def test_the_station_tables_are_keyed_by_module_not_by_page():
    """The one hand-declared table in the results renderer. Keyed by module
    because which row builder a program has is a fact about the program -- and
    keying it by page would put a step key back in the GUI (gate G2)."""
    from sloads import registry
    from oracle_app.results import STATION_TABLES

    assert set(STATION_TABLES) <= set(registry.available())
    assert not set(STATION_TABLES) & set(wf.BY_KEY)


def test_every_page_runs_the_programs_its_bas_string_claims():
    """OG-E's premise: a page headed "WTESTIMA+WTONECG+WTENV" shows all three.
    The modules come from ``workflow.step_modules``, so this is really a check
    that the renderer runs what the SSOT gives it and drops nothing."""
    from oracle_app.results import step_results
    from sloads import UnitSystem

    project = _seeded()
    for key in sorted(wf.oracle_step_keys()):
        blocks = step_results(project, key, UnitSystem.IMPERIAL)
        if len(blocks) == 1 and not blocks[0].module:
            continue  # gated: upstream slices missing, which the page says
        shown = {b.module for b in blocks}
        assert shown == set(wf.step_modules(key)), key


def test_a_page_with_no_program_of_its_own_shows_no_results():
    """Aerodynamic Data is on the page set because it *produces* a slice the
    ``.BAS`` steps require (OG-2 as amended), not because it runs one. An empty
    Results heading would be a worse answer than none."""
    from oracle_app.results import step_results
    from sloads import UnitSystem

    for key in sorted(wf.oracle_step_keys()):
        if wf.step_modules(key):
            continue
        assert step_results(_seeded(), key, UnitSystem.IMPERIAL) == []


@pytest.mark.parametrize("key", sorted(wf.oracle_step_keys()))
def test_the_results_block_survives_an_empty_project(key):
    """The blank-project path: every program is unrunnable and the page has to
    say so rather than raise."""
    from sloads.models import Project
    from sloads import UnitSystem
    from oracle_app.results import step_results

    for block in step_results(Project(name=""), key, UnitSystem.IMPERIAL):
        assert block.note or block.rows, (key, block.title)


def test_a_self_sufficient_page_is_not_sent_upstream():
    """#45 (CR-D-3), measured BB-4: on a fresh project ``weight_mass`` and
    ``engine_mount`` are missing only slices *their own form enters*, so the
    blocked note must point at the form above — "run the pages before this one
    first" was wrong guidance on the beta's first-run path. A genuinely
    dependent page keeps the upstream wording."""
    from sloads.models import Project
    from sloads import UnitSystem
    from oracle_app.results import step_results

    fresh = Project(name="")
    for key in ("weight_mass", "engine_mount"):
        (block,) = step_results(fresh, key, UnitSystem.IMPERIAL)
        assert "fill in the form above" in (block.note or ""), (key, block.note)
        assert "run the pages before" not in (block.note or ""), (key, block.note)
    (block,) = step_results(fresh, "structural_speeds", UnitSystem.IMPERIAL)
    assert "run the pages before this one first" in (block.note or "")
    assert "`aero_coeffs`" in block.note


# --------------------------------------------------------------------------- #
# G6 -- round-trip
# --------------------------------------------------------------------------- #
def _examples():
    return sorted(glob.glob(os.path.join(_EXAMPLES, "*.project.json")))


@pytest.mark.parametrize("path", _examples(), ids=lambda p: os.path.basename(p))
def test_a_project_the_oracle_gui_would_save_reloads_identically(path):
    """Gate G6: what the second front-end writes is the same ``project.json``
    the first one does -- no schema hop, no dropped slice on reload (OG-13)."""
    reduced = reduce_to_oracle_inputs(io.load_project(path))
    once = io.project_to_json(reduced)
    twice = io.project_to_json(io.project_from_dict(json.loads(once)))
    assert once == twice


def test_a_project_the_oracle_gui_would_save_opens_in_the_full_app():
    """Gate G6, the direction that matters to a user: hand the reduced project
    to ``app/`` and it builds, pages and all."""
    from streamlit.testing.v1 import AppTest

    reduced = reduce_to_oracle_inputs(io.load_project(_EXAMPLE))
    for view in ("Home.py", os.path.join("views", "configuration_layout.py"),
                 os.path.join("views", "weight_mass.py"),
                 os.path.join("views", "dashboard.py")):
        at = AppTest.from_file(os.path.join(_ROOT, "app", view), default_timeout=60)
        at.session_state["project"] = io.project_from_dict(
            json.loads(io.project_to_json(reduced)))
        at.run()
        assert not at.exception, (view, [e.message for e in at.exception])


def test_the_oracle_entry_point_builds():
    """The entry point itself: one ``set_page_config``, a derived navigation."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(_ENTRYPOINT, default_timeout=60)
    at.session_state["project"] = _seeded()
    at.run()
    assert not at.exception, [e.message for e in at.exception]


def test_the_launcher_points_at_the_entry_point():
    """OG-11's console script resolves to the file it claims to run."""
    import oracle

    assert os.path.isfile(oracle.entry_point_path())
    assert os.path.samefile(oracle.entry_point_path(), _ENTRYPOINT)


def test_the_launcher_reports_a_missing_entry_point_instead_of_raising():
    import contextlib

    import oracle

    original = oracle.ENTRY_POINT
    oracle.ENTRY_POINT = os.path.join("oracle_app", "NotHere.py")
    try:
        stderr = _io.StringIO()
        with contextlib.redirect_stderr(stderr):
            assert oracle.main([]) == 2
        assert "not found" in stderr.getvalue()
    finally:
        oracle.ENTRY_POINT = original


# --------------------------------------------------------------------------- #
# One owner at render (#36, CR-A-2)
# --------------------------------------------------------------------------- #
def _copies():
    """Every non-owner copy of a shared quantity that the oracle GUI renders."""
    oracle = fr.oracle_input_paths()
    out = []
    for rows in fr.quantities().values():
        for row in rows:
            if (not row.is_owner and not row.owner_is_external
                    and row.owner_path and row.path in oracle):
                out.append(row)
    return sorted(out, key=lambda r: r.path)


def test_the_registry_still_has_copies_to_mark():
    """Guard the guard. The consolidation (note 33) removed most of the copies,
    and if the rest ever go the tests below would pass by having nothing to
    check — which is exactly how a rule quietly stops being enforced."""
    assert _copies(), "no non-owner copies left: retire the marking, do not keep a vacuous guard"


@pytest.mark.parametrize("path", [r.path for r in _copies()])
def test_no_copy_of_a_shared_quantity_renders_as_a_plain_widget(path):
    """A non-owner copy must say so on the page (#36, CR-A-2).

    Before this, the registry knew which field owned each shared quantity and the
    renderer did not read it, so wing reference area was independently editable on
    four pages and gear tread on two, with nothing warning that the numbers
    disagreed. Every copy now renders either **disabled** (display-only: the
    consumer resolves the owner, so anything entered here is inert) or **marked**
    (an override the calc honours), and each states the owner's path.
    """
    row = fr.entry(path)
    at = _render(row.page)
    assert not at.exception, [e.message for e in at.exception]

    captions = " ".join(c.value or "" for c in at.caption)
    assert row.owner_path in captions, (
        f"{path} renders on page {row.page!r} without naming its owner "
        f"{row.owner_path!r}; the page implies an independent input")

    hits = widgets_editing(at, path)
    widget = hits[0] if hits else None
    if widget is not None and not row.governs:
        assert widget.disabled, (
            f"{path} is display-only — the analysis resolves {row.owner_path!r} "
            "instead — but its widget is editable, so a value typed here is "
            "silently ignored")


def test_a_display_only_copy_shows_the_value_that_governs():
    """The dead wing-area input (#36; #29 review, note 32 §8).

    ``speeds.wing_area_sqft`` was editable on Structural Speeds while STRSPEED
    resolved the wing planform instead — an 18 % divergence measured on atr42,
    with the page showing the number the analysis did not use. It now renders
    disabled at the owner's value.
    """
    project = io.load_project(_EXAMPLE)
    project.speeds.wing_area_sqft = 1.0          # a value the analysis ignores
    at = _render("structural_speeds", project)
    assert not at.exception, [e.message for e in at.exception]

    widget = widget_editing(at, "speeds.wing_area_sqft")
    assert widget.disabled
    owner = project.geometry.parametric.wing_area_sqft
    assert widget.value == pytest.approx(to_display(owner, "area_sqft", active_system()), rel=1e-6)
    # ...and rendering it did not write the displayed value back over the stored
    # one: visiting a page must leave the project alone (OG-F).
    assert project.speeds.wing_area_sqft == 1.0


def test_an_override_that_disagrees_with_its_owner_warns():
    """An override may differ — that is what it is for — so this warns, it does
    not correct. ``speeds.weight_lb`` is read verbatim by STRSPEED while
    ``weight.max_takeoff_weight_lb`` is the MTOW owner (G-14); the two silently
    disagreeing is the wrong-belief half of CR-A-2."""
    project = io.load_project(_EXAMPLE)
    project.speeds.weight_lb = project.weight.max_takeoff_weight_lb + 500.0
    at = _render("structural_speeds", project)
    assert not at.exception, [e.message for e in at.exception]
    assert any("max_takeoff_weight_lb" in (w.value or "") for w in at.warning), (
        "a design weight disagreeing with the MTOW owner drew no warning")

    project.speeds.weight_lb = project.weight.max_takeoff_weight_lb
    agreed = _render("structural_speeds", project)
    assert not any("max_takeoff_weight_lb" in (w.value or "") for w in agreed.warning), (
        "agreement must be quiet, or the warning is noise nobody reads")


if __name__ == "__main__":  # zero-dependency self-runner
    import sys

    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))


def test_grid_pages_carry_the_commit_hint():
    """C210 review 2026-08-23: a part-filled grid row is held out of the project,
    which is invisible until it vanishes on a rerun — so every page that renders
    a ``st.data_editor`` says so once, and a page with no grid does not nag.
    (The hint's original Enter warning was the C210-4 remount race, fixed by
    ``_stable_frame``.)"""
    hint = "fill every column to keep the row"
    at = _render("configuration_layout")   # surfaces/sections grids
    assert any(hint in c.value for c in at.caption), (
        "a grid page must carry the incomplete-row hint")
    at = _render("structural_speeds")      # scalars only
    assert not any(hint in c.value for c in at.caption), (
        "a page with no grid must not carry the hint")
