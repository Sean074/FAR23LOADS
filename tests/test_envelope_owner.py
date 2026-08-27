"""One owner for the V-n envelope and the critical set (review **F-C6**).

``select.default_envelope`` has been the declared owner of the "persisted
``Project.envelope``, else built from the flight-loads inputs" choice since M2R-8,
and ``select.default_critical`` is now its counterpart for
``Project.envelope.critical``. The reason it matters is one fact about the
pipeline: **``registry.run_all_modules`` never assigns ``Project.envelope``** --
and that is the path the Export page, the CLI and every deliverable take. So a
module that reads ``project.envelope`` directly does not get "the persisted
envelope when there is one"; on the deliverable path it gets ``None``, and
whatever it does next -- silently produce no cases, silently take a default load
factor, or raise on a case it could have resolved -- it does wrong.

That defect class has been found four times: ``tail_span._load_factor`` (fixed
2026-08-10 -- every exported tail deck had been taking ``n = 1.0``), then the four
sites this suite covers: ``net_loads._air_cl_v``, ``wing_inertia`` (×2),
``body_loads`` and ``balance``. Only the tail_span instance announced itself, and
only in a note.

Two kinds of gate here, per CLAUDE.md practice 3 (a cross-cutting convention gets
a code owner **plus** a drift guard):

* :func:`test_no_calc_code_reads_project_envelope_outside_the_owners` -- the drift
  guard. An AST scan of ``sloads/``: a new direct ``project.envelope`` read fails
  until its author routes it through the owner or adds the file to the allowlist
  below with a reason. A fifth instance of this class should not need a code
  review to find.
* the behaviour gates -- each of the four sites exercised on the path that was
  broken (no persisted envelope), plus the two edges the owner exists to get
  right: a persisted envelope must be *used* (``body_loads``), and a persisted
  envelope with an empty ``vn`` must not be mistaken for a real one (``balance``).
"""

import ast
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io
from sloads.models import EnvelopeResult, MissingInputError, WingMassInput
from sloads.modules.balance import build_balanced_cases
from sloads.modules.body_loads import build_body_loads
from sloads.modules.flight_envelope import build_envelope
from sloads.modules.net_loads import build_net_loads
from sloads.modules.select import (
    build_critical,
    default_critical,
    default_envelope,
    vn_by_case,
    vn_points,
)
from sloads.modules.tail_span import _vn_points as tail_span_vn
from sloads.modules.taildist import _critical_set as taildist_critical
from sloads.modules.wing_inertia import (
    build_wing_inertia,
    resolve_wing_cases,
    wing_case_ref,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PKG = os.path.join(_ROOT, "sloads")
_GA = os.path.join(_ROOT, "examples", "ga6_normal.project.json")


# --------------------------------------------------------------------------- #
# The drift guard
# --------------------------------------------------------------------------- #
#: Files allowed a direct ``project.envelope`` read, each for a stated reason that
#: is *not* "persisted, else compute" -- that rule has exactly one owner.
_ALLOWED = {
    "modules/select.py":
        "the owner itself (default_envelope / default_critical / vn_points)",
    "io.py":
        "the only dataclass<->JSON mapping: it serialises whatever the project holds",
    "validation.py":
        "reports on what the project *holds* (a persisted safety factor mutated "
        "in-session); computing an envelope here would check a different object "
        "than the one that will be exported",
    "export/sbeam_bridge.py":
        "the case index lists the cases the project carries; the bridge renders, "
        "it never computes loads",
    "modules/body_loads.py":
        "_critical_fuselage: a documented narrow variant -- fuselage conditions "
        "only, via select_fuselage rather than build_critical, so a body deck does "
        "not require well-formed tail inputs. Its V-n side goes through the owner.",
}


def _project_envelope_reads(path):
    """``[(line, source_segment)]`` for every ``project.envelope`` attribute read.

    An AST walk, not a regex: docstrings and comments discuss ``project.envelope``
    constantly (this file included) and none of that is a read.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == "envelope"
                and isinstance(node.value, ast.Name)
                and node.value.id in ("project", "proj")):
            out.append((node.lineno, f"{node.value.id}.envelope"))
    return out


def test_no_calc_code_reads_project_envelope_outside_the_owners():
    scanned = 0
    for dirpath, _dirs, files in os.walk(_PKG):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, _PKG)
            scanned += 1
            reads = _project_envelope_reads(path)
            if not reads:
                continue
            assert rel in _ALLOWED, (
                f"{rel}:{reads[0][0]} reads {reads[0][1]} directly. "
                "registry.run_all_modules never assigns Project.envelope, so on the "
                "deliverable path this read is None: route it through "
                "select.default_envelope / default_critical / vn_points (or "
                "vn_by_case), or add the file to _ALLOWED here with the reason it "
                "is not the persisted-else-compute rule."
            )
    # The scan must actually be seeing the package (guards against a moved dir).
    assert scanned >= 30, f"only {scanned} modules scanned under sloads/"


def test_the_allowlist_has_no_stale_entries():
    """An allowlisted file that no longer reads ``project.envelope`` loses its
    exemption, so the list cannot quietly grow into a blanket."""
    for rel in sorted(_ALLOWED):
        path = os.path.join(_PKG, rel)
        assert os.path.exists(path), f"_ALLOWED names a missing file: {rel}"
        assert _project_envelope_reads(path), (
            f"{rel} no longer reads project.envelope -- drop it from _ALLOWED")


# --------------------------------------------------------------------------- #
# The owners themselves
# --------------------------------------------------------------------------- #
def test_the_owners_prefer_the_persisted_objects_and_build_otherwise():
    project = io.load_project(_GA)
    assert project.envelope is None, "fixture now persists an envelope"

    built = default_envelope(project)
    assert built.vn, "no V-n matrix built from the flight-loads inputs"
    assert vn_by_case(project) == {p.case: p for p in built.vn}
    assert [c.label for c in default_critical(project).conditions] == \
        [c.label for c in build_critical(project).conditions]

    # Persisted: returned as-is, identity included -- the CaseRefs stamped on it
    # are what downstream case IDs dedupe against.
    project.envelope = build_envelope(project)
    project.envelope.critical = build_critical(project)
    assert default_envelope(project) is project.envelope
    assert default_critical(project) is project.envelope.critical


def test_an_empty_persisted_vn_is_not_mistaken_for_an_envelope():
    """The edge ``project.envelope or build_envelope(project)`` got wrong: an
    ``EnvelopeResult`` with no points is truthy but useless."""
    project = io.load_project(_GA)
    project.envelope = EnvelopeResult()
    assert default_envelope(project).vn, "an empty persisted vn was accepted"
    assert vn_points(project), "the tolerant read accepted an empty persisted vn"


def test_the_tolerant_read_is_empty_rather_than_raising():
    """``vn_points`` exists so a documented in-band fallback (tail_span's
    ``n = 1.0``) is not turned into an input error by absent flight-loads inputs --
    while ``default_envelope`` stays loud for consumers that need the matrix."""
    project = io.load_project(_GA)
    project.flight_loads = None
    assert vn_points(project) == []
    assert vn_by_case(project) == {}
    with pytest.raises(MissingInputError):
        default_envelope(project)


# --------------------------------------------------------------------------- #
# Site 1 + 2: net_loads / wing_inertia on the run_all_modules path
# --------------------------------------------------------------------------- #
def _derived_case_project():
    """ga6 with its hand-entered wing cases removed and **no** persisted envelope --
    i.e. exactly what ``registry.run_all_modules`` hands these modules."""
    project = io.load_project(_GA)
    project.wing_mass.cases = []
    assert project.envelope is None
    return project


def test_the_derived_wing_cases_resolve_with_no_persisted_envelope():
    """Before the sweep: ``resolve_wing_cases`` returned ``[]`` here (the critical
    set was read only from ``project.envelope``), so both modules raised "needs at
    least one load case" on every project that left the table empty."""
    project = _derived_case_project()
    cases = resolve_wing_cases(project, WingMassInput())
    assert cases, "no wing cases derived on the run_all_modules path"
    want = [c.label for c in build_critical(project).conditions if c.component == "wing"]
    assert [c.name for c in cases] == want

    inertia = build_wing_inertia(project)          # was MissingInputError
    assert [r.case for r in inertia] == want
    net = build_net_loads(project)                 # was MissingInputError (_air_cl_v)
    assert [r.case for r in net.wing_net] == want
    for r in net.wing_air:
        assert any(st.fz for st in r.stations), f"{r.case} carries no air load"


def test_a_derived_case_ref_names_its_flight_condition():
    """``wing_case_ref`` read the V-n point through ``project.envelope`` too, so on
    this path every wing case reported an empty CG and no altitude -- the case
    index shipped without the condition it was flown at."""
    project = _derived_case_project()
    cases = resolve_wing_cases(project, WingMassInput())
    assert cases, "no cases to check -- the derivation itself is broken"
    for i, case in enumerate(cases):
        ref = wing_case_ref(project, i, case)
        assert ref.cg, f"{case.name} names no CG case"
        assert ref.altitude_ft is not None and ref.speed_kt is not None

    # And SELECT's own CaseRef wins when it named the condition (M4-2 decision 1:
    # one ID per physical condition), which is what the case-index dedupe assumes.
    select_refs = {c.label: c.case_ref for c in build_critical(project).conditions
                   if c.component == "wing"}
    for i, case in enumerate(cases):
        want = select_refs.get(case.name)
        if want is not None:
            assert wing_case_ref(project, i, case).case_id == want.case_id


def test_the_two_wing_modules_agree_on_every_case_ref():
    """The threading must not let ``net_loads`` and ``wing_inertia`` resolve
    different sources for the same case list."""
    project = _derived_case_project()
    inertia = {r.case: r.case_ref for r in build_wing_inertia(project)}
    net = {r.case: r.case_ref for r in build_net_loads(project).wing_inertia}
    assert inertia.keys() == net.keys()
    for case in inertia:
        assert inertia[case] == net[case], case


def test_an_unresolvable_wing_case_still_names_itself():
    """The loud failure stays loud (and stays specific) when there is genuinely no
    V-n matrix to resolve a case against."""
    project = io.load_project(_GA)
    project.wing_mass.cases[0].nz = None
    project.wing_mass.cases[0].nx = None
    project.flight_loads = None
    with pytest.raises(MissingInputError) as err:
        build_wing_inertia(project)
    assert project.wing_mass.cases[0].name in str(err.value)


# --------------------------------------------------------------------------- #
# Site 3: body_loads must integrate against the envelope that selected its cases
# --------------------------------------------------------------------------- #
def test_body_loads_uses_the_persisted_envelope_it_selected_from():
    """``_critical_fuselage`` prefers the persisted conditions while the loop read a
    **freshly built** V-n matrix: a condition could be paired with an ``nz``/``lt``
    from a different envelope than the one that selected it. Perturbing a persisted
    point must move the distribution -- if it does not, the rebuild is back.
    """
    project = io.load_project(_GA)
    project.envelope = build_envelope(project)
    project.envelope.critical = build_critical(project)
    base = {r.case: r for r in build_body_loads(project)}
    assert base, "no fuselage conditions assembled"

    perturbed = copy.deepcopy(project)
    cases = {c.case for c in perturbed.envelope.critical.conditions
             if c.component == "fuselage"}
    for p in perturbed.envelope.vn:
        if p.case in cases:
            p.nz *= 2.0
    got = {r.case: r for r in build_body_loads(perturbed)}
    assert got.keys() == base.keys()
    assert any(sum(s.fz for s in got[c].stations) != sum(s.fz for s in base[c].stations)
               for c in base), (
        "doubling the persisted V-n load factors changed nothing -- body_loads is "
        "rebuilding its own envelope again")


def test_body_loads_still_runs_with_no_persisted_envelope():
    """And the ordinary deliverable path is unchanged."""
    project = io.load_project(_GA)
    assert build_body_loads(project), "no body loads on the run_all_modules path"


# --------------------------------------------------------------------------- #
# Site 4: balance
# --------------------------------------------------------------------------- #
def test_balance_ignores_an_empty_persisted_envelope_rather_than_dropping_cases():
    """``project.envelope or build_envelope(project)`` accepted an envelope with an
    empty ``vn``; every condition then failed its V-n lookup and dropped out under
    a misleading "nothing to balance"."""
    project = io.load_project(_GA)
    want = [(c.label, c.vn_case, c.hand) for c in build_balanced_cases(project)]
    assert want, "the fixture assembles no balanced cases"

    empty = io.load_project(_GA)
    empty.envelope = EnvelopeResult()
    assert [(c.label, c.vn_case, c.hand)
            for c in build_balanced_cases(empty)] == want


# --------------------------------------------------------------------------- #
# The two sites already fixed: they stay on the owner
# --------------------------------------------------------------------------- #
def test_the_tail_modules_read_the_matrix_on_the_deliverable_path():
    """The 2026-08-10 ``n = 1.0`` defect, pinned at last: ``tail_span`` must see the
    V-n matrix (and ``taildist`` the critical set) with nothing persisted."""
    project = io.load_project(_GA)
    assert tail_span_vn(project), "tail_span sees no V-n points -- the n=1.0 defect"
    assert taildist_critical(project).conditions


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
