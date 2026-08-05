"""The summary report's content model (Step G8.4).

The report is the *controlling document* of a loads deliverable, so what these
tests pin is not formatting but the promises
``docs/10_standard/SUMMARY_REPORT.md`` makes to the analyst reading it:

* every required section exists (§4), and a section whose inputs are absent says
  so instead of vanishing or rendering an empty table (§3.4);
* every load is ULTIMATE, marked in its units string and accompanied by its
  safety factor and the station/case it occurs at (§3.1, §3.3);
* nothing is recomputed: the report's governing figures are literally
  ``governing_loads_table``'s, so the report and the pages cannot disagree (§5);
* the whole document honours the caller's unit system (§3.5).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import Project, io  # noqa: E402
from sloads.models import SCHEMA_VERSION  # noqa: E402
from sloads.modules.select import build_critical  # noqa: E402
from sloads.registry import run_all_modules  # noqa: E402
from sloads.report import governing_loads_table  # noqa: E402
from sloads.report.content import (  # noqa: E402
    AVIATION_UNITS_NOTE,
    BASIS_STATEMENT,
    ReportDocument,
    build_report,
    component_loads,
)
from sloads.units import UnitSystem  # noqa: E402
import sloads.modules  # noqa: E402,F401  (module registration)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")

#: Every section SUMMARY_REPORT.md §4 requires, by the title the content model
#: gives it. A renamed or dropped section fails here rather than in a reader's
#: hands.
REQUIRED_SECTIONS = [
    "1. Input summary",
    "2. Envelope figures",
    "3. Conditions analysed and FAR coverage",
    "4. Results summary",
    "5. Methods and limitations",
    "Appendix A. Bundle manifest",
]

#: §4.5's component subsections, each of which must be present or explicitly
#: marked "not analysed".
REQUIRED_COMPONENTS = [
    "Wing", "Fuselage", "Horizontal tail", "Vertical tail",
    "Control surfaces", "Landing gear", "Engine mount",
]


def _report(path=_GA, **kwargs) -> ReportDocument:
    return build_report(io.load_project(path), tool_version="test", **kwargs)


def _all_tables(doc: ReportDocument):
    stack = list(doc.sections)
    while stack:
        section = stack.pop(0)
        for table in section.tables:
            yield section, table
        stack = list(section.subsections) + stack


# --------------------------------------------------------------------------- #
# Structure (SUMMARY_REPORT.md §4)
# --------------------------------------------------------------------------- #
def test_every_required_section_is_present():
    doc = _report()
    assert [s.title for s in doc.sections] == REQUIRED_SECTIONS


def test_every_component_subsection_is_present():
    doc = _report()
    results = doc.section("4. Results summary")
    assert [s.title for s in results.subsections] == REQUIRED_COMPONENTS


def test_sections_degrade_rather_than_raise_on_an_empty_project():
    """A half-filled project must still produce a report -- that is how an
    engineer *finds* the gaps -- with each absent section carrying a reason."""
    doc = build_report(Project(name="empty"))
    assert [s.title for s in doc.sections] == REQUIRED_SECTIONS
    inputs = doc.section("1. Input summary")
    for title in ("Geometry", "Weights and CG", "Design speeds", "Aerodynamic data"):
        sub = inputs.subsection(title)
        assert sub.absent_reason, f"{title} is empty with no stated reason"
        assert not sub.tables, f"{title} rendered a table with no inputs"
    for title in REQUIRED_COMPONENTS:
        assert doc.section("4. Results summary").subsection(title).absent_reason


def test_absent_figure_states_why_instead_of_drawing_an_empty_axis():
    doc = build_report(Project(name="empty"))
    for title in ("V-n diagram", "Weight / CG envelope", "Speed / altitude envelope"):
        figure = doc.section(title).figures[0]
        assert figure.data is None
        assert figure.absent_reason


def test_no_mach_limit_says_so_rather_than_omitting_the_figure():
    """§4.3: a project with no Mach boundary keeps the heading and states it."""
    project = io.load_project(_GA)
    project.speeds.mach_limit = None
    doc = build_report(project)
    figure = doc.section("Speed / altitude envelope").figures[0]
    assert figure.data is None
    assert "no Mach-limited boundary" in figure.absent_reason


# --------------------------------------------------------------------------- #
# Inputs are the project's own values (§4.2)
# --------------------------------------------------------------------------- #
def test_input_tables_carry_the_projects_values_and_name_their_owner():
    project = io.load_project(_GA)
    doc = build_report(project, tool_version="test")
    speeds = doc.section("Design speeds").table
    by_name = {row[0]: row for row in speeds.rows}
    assert by_name["VC (cruise)"][1] == "170"          # examples/ga6_normal chosen VC
    assert by_name["VC (cruise)"][2] == "23.335(a)"    # every condition cites its FAR
    assert by_name["VC (cruise)"][3] == "user-specified"

    config = doc.section("Configuration").table
    assert config.columns[-1] == "Owned by"            # §3.2 traceability
    assert all(row[-1] for row in config.rows)


def test_load_factors_are_reported_limit_and_unmarked():
    """§3.1: a load factor is dimensionless and limit; marking or scaling one is
    an error, not a rounding difference."""
    doc = _report()
    factors = doc.section("Design speeds").tables[1]
    rows = {row[0]: row for row in factors.rows}
    assert rows["n (positive)"][1] == "3.8"            # Appendix A, category N
    assert "ULT" not in "".join(factors.columns)


# --------------------------------------------------------------------------- #
# The ultimate-load contract (§3.1, §3.3)
# --------------------------------------------------------------------------- #
def test_every_load_column_is_ultimate_marked():
    """No deliverable column may carry a bare load unit.

    ``(lb)`` is the one ambiguous case: pounds-*force* is a load and must be
    marked, pounds-*mass* is a weight and must not be (§3.1). A weight column
    says so in its name, which is exactly the distinction the calc carries as
    ``LoadValue.quantity == "mass"``.
    """
    doc = _report()
    bare = {"(ft-lb)", "(lb-in)", "(lb/in^2)"}
    for section, table in _all_tables(doc):
        for column in table.columns:
            assert not any(column.endswith(u) for u in bare), \
                f"{section.title}/{table.title}: bare limit unit in '{column}'"
            if column.endswith("(lb)"):
                assert "weight" in column.lower(), \
                    f"{section.title}/{table.title}: unmarked force in '{column}'"


def test_wing_maxima_are_two_sided_and_name_their_station_and_axis():
    """§3.3: a maximum without a location is not usable for sizing, and a
    one-sided envelope hides the opposite-sign extreme."""
    doc = _report()
    maxima = doc.section("Wing").tables[1]
    assert maxima.columns == ["Quantity", "Units", "Maximum",
                              "Occurs at (case, station)", "Minimum",
                              "Occurs at (case, station)"]
    for row in maxima.rows:
        assert row[3] and "span station" in row[3]
        assert row[5] and "span station" in row[5]
    torsion = [r for r in maxima.rows if r[0].startswith("Torsion")][0]
    assert "% chord" in torsion[0], "wing torsion must name the axis it is about"


def test_case_index_states_a_safety_factor_for_every_case():
    doc = _report()
    index = doc.section("3. Conditions analysed and FAR coverage").table
    assert index.columns[-1] == "SF"
    assert index.rows
    for row in index.rows:
        assert row[0]                       # a case ID
        assert float(row[-1]) > 0           # its factor, stated (§3.1)


def test_governing_tables_are_governing_loads_tables_output():
    """§5 forbids the report recomputing anything: its governing figures must be
    the same function's output the GUI pages render."""
    project = io.load_project(_GA)
    doc = build_report(project, tool_version="test")
    wing_conditions = [c for c in build_critical(project).conditions
                       if c.component == "wing"]
    expected = governing_loads_table(wing_conditions, UnitSystem.IMPERIAL)
    table = doc.section("Wing").tables[0]
    assert table.columns == list(expected[0].keys())
    assert table.rows == [[str(r[c]) for c in table.columns] for r in expected]


def test_deselected_cases_are_excluded_from_the_results_and_named_in_scope():
    """§3.4: an analyst never receives a filtered set without being told."""
    project = io.load_project(_GA)
    critical = build_critical(project)
    dropped = next(c for c in critical.conditions if c.component == "wing")
    dropped_id = dropped.case_ref.case_id
    doc = build_report(project, tool_version="test", scope="governing case set",
                       deselected_case_ids=[dropped_id])
    wing = doc.section("Wing").tables[0]
    assert dropped.label not in [row[0] for row in wing.rows]
    scope_text = " ".join(doc.section("3. Conditions analysed and FAR coverage").body)
    assert dropped_id in scope_text and "EXCLUDED" in scope_text


# --------------------------------------------------------------------------- #
# Units (§3.5)
# --------------------------------------------------------------------------- #
def test_si_report_carries_si_markers_and_converts_the_loads():
    imperial = _report()
    si = _report(system=UnitSystem.SI)

    def wing_shear(doc):
        row = [r for r in doc.section("Wing").tables[1].rows
               if r[0] == "Shear Sz"][0]
        return row[1], float(row[2])

    imp_units, imp_value = wing_shear(imperial)
    si_units, si_value = wing_shear(si)
    assert imp_units == "lbs-ULT" and si_units == "N-ULT"
    assert si_value == pytest.approx(imp_value * 4.4482216152605, rel=1e-3)


def test_geometry_areas_and_lengths_convert_with_their_labels_in_si():
    """A mislabelled quantity is worse than an unconverted one: it reads as
    correct. Every geometry row's value and unit move together (§3.5)."""
    def row(doc, name):
        return {r[0]: (r[1], r[2]) for r in doc.section("Geometry").table.rows}[name]

    imperial, si = _report(), _report(system=UnitSystem.SI)
    for name, factor, imp_unit, si_unit in (
        ("Wing area S", 0.09290304, "ft^2", "m^2"),
        ("Horizontal-tail area ST", 0.09290304, "ft^2", "m^2"),
        ("Wing MAC", 25.4, "in", "mm"),
    ):
        imp_value, imp_units = row(imperial, name)
        si_value, si_units = row(si, name)
        assert (imp_units, si_units) == (imp_unit, si_unit)
        assert float(si_value) == pytest.approx(float(imp_value) * factor, rel=1e-3)


def test_speeds_and_altitudes_are_not_converted_in_si():
    """Aviation-standard carve-out (§3.5): KEAS and ft in both systems."""
    doc = _report(system=UnitSystem.SI)
    speeds = doc.section("Design speeds").table
    assert speeds.columns[1] == "Value (KEAS)"
    assert dict((r[0], r[1]) for r in speeds.rows)["VC (cruise)"] == "170"
    assert AVIATION_UNITS_NOTE in speeds.note


def test_manifest_states_one_system_for_the_whole_bundle():
    doc = _report(system=UnitSystem.SI)
    manifest = doc.section("Appendix A. Bundle manifest")
    opening = " ".join(manifest.body)
    assert "written in SI" in opening
    # The solver channel's consistent set is named where the decks are listed
    # (D-19): a deck in N and mm needs N*mm moments, not the report's N*m.
    assert "N·mm" in opening and "MPa" in opening


# --------------------------------------------------------------------------- #
# Title page and concept mode (§4.1, §4.6)
# --------------------------------------------------------------------------- #
def test_title_page_carries_the_control_block_and_basis():
    doc = _report()
    control = dict(doc.control)
    for label in ("Project", "Engineer", "Date", "Revision", "Checked by",
                  "Approved by", "Certification basis", "Tool", "Units"):
        assert label in control, f"document-control row '{label}' is missing"
    assert control["Project schema version"] == str(SCHEMA_VERSION)
    assert doc.basis == BASIS_STATEMENT
    assert "FAR 23" in doc.badge


def test_concept_project_is_badged_and_caveated():
    doc = _report(_CONCEPT)
    assert "Concept" in doc.badge and "unverified extrapolation" in doc.badge
    assert "UNVERIFIED EXTRAPOLATION" in doc.methods
    assert "CONCEPT" in doc.methods


def test_report_methods_section_is_the_shared_statement_verbatim():
    """§4.6: the report's statement and the one stamped into the CSV/BDF exports
    come from one source, so they cannot diverge."""
    doc = _report()
    assert doc.section("5. Methods and limitations").body[0] == doc.methods


def test_no_internal_development_artifacts_in_the_document():
    """§5 excludes backlog IDs, source paths and code identifiers: the reader is
    an analyst, not a maintainer."""
    text = [doc_text for doc_text in _collect_text(_report())]
    joined = "\n".join(text)
    for artifact in ("backlog", ".py", "TODO", "sloads/"):
        assert artifact not in joined, f"internal artifact '{artifact}' in the report"


def _collect_text(doc: ReportDocument):
    yield doc.methods
    stack = list(doc.sections)
    while stack:
        section = stack.pop(0)
        yield section.title
        yield section.absent_reason
        yield from section.body
        for table in section.tables:
            yield table.title
            yield table.note
            yield from table.columns
            for row in table.rows:
                yield from row
        for figure in section.figures:
            yield figure.title
            yield figure.caption
            yield figure.absent_reason
        stack = list(section.subsections) + stack


# --------------------------------------------------------------------------- #
# The shared component recompute
# --------------------------------------------------------------------------- #
def test_component_loads_recomputes_every_family_for_the_ga_example():
    comps = component_loads(io.load_project(_GA))
    assert comps.wing and comps.body and comps.tail and comps.control and comps.critical


def test_component_loads_degrades_on_an_empty_project():
    comps = component_loads(Project(name="empty"))
    assert comps.wing == [] and comps.body == [] and comps.tail == []
    assert comps.control == [] and comps.critical == []


def test_build_report_accepts_precomputed_results():
    """The Export page computes the module results and component loads once for
    the whole bundle; the report must reuse them rather than recompute."""
    project = io.load_project(_GA)
    results = run_all_modules(project)
    comps = component_loads(project)
    doc = build_report(project, module_results=results, components=comps,
                       tool_version="test")
    assert doc.section("Wing").tables


if __name__ == "__main__":  # zero-dependency self-runner (see PROGRAM_SPEC)
    import traceback

    failures = 0
    for name, fn in sorted(list(globals().items())):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"ok   {name}")
        except Exception:  # noqa: BLE001 - a self-runner reports, it does not raise
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    raise SystemExit(1 if failures else 0)
