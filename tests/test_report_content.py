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
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: F401  (module registration)
from sloads import Project, io
from sloads.models import SCHEMA_VERSION
from sloads.modules.select import build_critical
from sloads.registry import run_all_modules
from sloads.report import governing_loads_table
from sloads.report.content import (
    AVIATION_UNITS_NOTE,
    BASIS_STATEMENT,
    SECTIONS,
    ReportDocument,
    build_report,
    component_loads,
    section_heading,
    section_ref,
)
from sloads.units import UnitSystem

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")
_HEAVY = os.path.join(_EXAMPLES, "concept_heavy.project.json")

#: Every section SUMMARY_REPORT.md §4 requires, by the title the content model
#: gives it. A renamed or dropped section fails here rather than in a reader's
#: hands.
REQUIRED_SECTIONS = [
    "1. Input summary",
    "2. Axes and sign conventions",
    # M4-8 / G-11: the governing safety-factor table is a numbered section of
    # record, placed with the conventions it belongs beside -- the factor is a
    # convention of the deliverable, not a result of it.
    "3. Governing safety factors",
    "4. Envelope figures",
    "5. Conditions analysed and FAR coverage",
    "6. Results summary",
    "7. Balanced free-free airframe cases",
    # G-12: the gear interface load definition, placed after the assembled cases
    # it is the other side of -- the reference-point reaction it states is the
    # load the assembled deck applies at that node, sign-flipped.
    "8. Landing gear interface loads",
    "9. Methods and limitations",
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
    results = doc.section("Results summary")
    assert [s.title for s in results.subsections] == REQUIRED_COMPONENTS


def test_sections_degrade_rather_than_raise_on_an_empty_project():
    """A half-filled project must still produce a report -- that is how an
    engineer *finds* the gaps -- with each absent section carrying a reason."""
    doc = build_report(Project(name="empty"))
    assert [s.title for s in doc.sections] == REQUIRED_SECTIONS
    inputs = doc.section("Input summary")
    for title in ("Geometry", "Weights and CG", "Design speeds", "Aerodynamic data"):
        sub = inputs.subsection(title)
        assert sub.absent_reason, f"{title} is empty with no stated reason"
        assert not sub.tables, f"{title} rendered a table with no inputs"
    for title in REQUIRED_COMPONENTS:
        assert doc.section("Results summary").subsection(title).absent_reason


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


def test_the_wing_root_design_loads_are_the_sob_cut_not_the_half_span_totals():
    """Step 13: where a project states a side of body, the report states the
    wing root design loads at it -- distinct from the half-span maxima -- and a
    project without one must not gain an invented joint (``concept_heavy``;
    ``ga6_normal`` carries the Appendix A body outline since the Pri 1
    fixture-data pass and so states its assumed half-width SOB like the rest)."""
    doc = _report(_CONCEPT)
    tables = doc.section("Wing").tables
    sob = [t for t in tables if t.title.startswith("Wing side-of-body")]
    assert len(sob) == 1
    table = sob[0]
    assert "BL 52.5" in table.title
    assert table.columns[0] == "Case" and table.columns[-1] == "SF"
    assert all("-ULT" in c for c in table.columns[1:6])
    assert table.rows and all(len(r) == 7 for r in table.rows)
    assert "outboard of the side of body" in table.note
    assert "ASSUMED" in table.note        # the half-width fallback says so
    ga_tables = _report().section("Wing").tables
    assert len([t for t in ga_tables if t.title.startswith("Wing side-of-body")]) == 1
    heavy_tables = _report(_HEAVY).section("Wing").tables
    assert not [t for t in heavy_tables if t.title.startswith("Wing side-of-body")]


def test_case_index_states_a_safety_factor_for_every_case():
    doc = _report()
    index = doc.section("Conditions analysed and FAR coverage").table
    assert index.columns[-1] == "SF"
    assert index.rows
    for row in index.rows:
        assert row[0]                       # a case ID
        assert float(row[-1]) > 0           # its factor, stated (§3.1)


def _skips_table(doc):
    section = doc.section("Conditions analysed and FAR coverage")
    tables = [t for t in section.tables
              if t.title == "Conditions not assembled into a balanced case"]
    assert len(tables) == 1, [t.title for t in section.tables]
    return tables[0]


def test_the_report_states_which_conditions_did_not_assemble():
    """The assembled full-span model is the primary deliverable, and a deck lists
    only what it holds -- so the controlling document, not the deck alone, has to
    say which conditions are absent from it and why (review F-C7)."""
    from sloads.modules.balance import build_balanced_cases, skipped_condition_lines

    project = io.load_project(_CONCEPT)
    skipped = []
    build_balanced_cases(project, skipped)
    assert skipped, "fixture no longer exercises the record"

    rows = [row[0] for row in _skips_table(build_report(project)).rows]
    assert rows == skipped_condition_lines(skipped)
    # The fixture's own example has moved twice. D-25 brought its flight NMAA in
    # (the case states its loading); Pri 5 / D-26 brought its whole ground family
    # in as well, so nothing is dropped for want of a loading on any fixture any
    # more. What the record still carries -- and always will -- are the
    # structural exclusions: LANDLOAD conditions the assembly has no branch for.
    assert any("supplementary nose-wheel" in row for row in rows), rows


def test_the_skipped_conditions_table_states_absence_rather_than_vanishing():
    """A project the balancer cannot run at all still gets the statement: silence
    is the failure mode the record exists to close."""
    table = _skips_table(build_report(Project(name="empty")))
    assert len(table.rows) == 1
    assert "No balanced case could be assembled" in table.rows[0][0]


# --------------------------------------------------------------------------- #
# §6 -- the assembled deliverable is in the controlling document (D-R2, F-D2)
# --------------------------------------------------------------------------- #
def _balanced_section(path=_GA):
    return _report(path).section("Balanced free-free airframe cases")


def test_the_balanced_case_table_is_the_decks_own_row_builder():
    """§5 forbids the report recomputing anything, and the balanced deck is the
    primary deliverable: its per-case n, residuals and closure in the report must
    be literally the rows the deck and the Balanced Cases page render."""
    from sloads.export.balanced_deck import balanced_case_rows
    from sloads.modules.balance import build_balanced_cases

    project = io.load_project(_GA)
    expected = balanced_case_rows(build_balanced_cases(project, []))
    assert expected, "fixture no longer assembles a balanced case"

    table = _balanced_section().tables[0]
    assert table.columns == list(expected[0])
    assert table.rows == [[r[c] for c in table.columns] for r in expected]
    # The four D-R2 facts, by column rather than by prose.
    for column in ("Nz", "Hand", "Residual Fz (% n*W)", "Closure dn (g)"):
        assert column in table.columns


def test_the_balanced_sections_residual_verdict_is_over_the_gated_family_only():
    """The rendered §6 sentence, on a fixture that assembles ground cases (CR-C-2).

    The defect this pins was in the *claim*, not in the physics: §6 maximised the
    pre-closure residual over every case, so on `ga6_normal` it declared the
    primary deliverable at 143.885 % against a 1 % gate — that number being the
    23.427(a) maneuver tail load, which the deck's own `$` header, the case-table
    note and `balanced_cases.md` §3/§9.4 all say the gate does not apply to. The
    gate read the case objects and nothing read the sentence, so the report
    contradicted the deck it describes in every shipped ga6/RJ bundle since 0.6.0.
    Asserted against `residual_gate_applies`, the owner, rather than a literal.
    """
    from sloads.modules.balance import (
        FORCE_RESIDUAL_ACCEPTANCE,
        RESIDUAL_GATE,
        build_balanced_cases,
        is_ground,
        residual_gate_applies,
        residual_gate_family,
    )

    project = io.load_project(_GA)
    cases = build_balanced_cases(project, [])
    judged, _clamped = residual_gate_family(cases)
    assert any(is_ground(c) for c in cases), "fixture no longer assembles ground cases"
    assert judged and len(judged) < len(cases), "fixture no longer exercises both sides"
    force = max(c.force_residual_fraction for c in judged)
    pitch = max(c.moment_residual_fraction for c in judged)
    assert force < FORCE_RESIDUAL_ACCEPTANCE and pitch < RESIDUAL_GATE, (
        "fixture's judged family no longer passes acceptance")

    text = " ".join(_balanced_section().body)
    # Each component against its own acceptance: reporting max(force, pitch)
    # against the tighter of the two was the same false claim in a second coat.
    assert f"{force:.3%}" in text and f"{pitch:.3%}" in text, text
    assert f"{FORCE_RESIDUAL_ACCEPTANCE:.1%}" in text and f"{RESIDUAL_GATE:.0%}" in text
    assert f"{len(judged)} of them" in text
    # The two things the old sentence got wrong: the exempt families' standing is
    # stated, and the retired cause is gone.
    assert "does not apply to" in text and "ground" in text
    assert "non-wing drag" not in text
    # And the number that used to be reported as the deliverable's verdict is not
    # presented as one.
    ungated_worst = max(max(c.force_residual_fraction, c.moment_residual_fraction)
                        for c in cases if not residual_gate_applies(c))
    assert f"{ungated_worst:.3%}" not in text


def test_the_balanced_section_states_its_handed_twin_pairs():
    """An asymmetric case ships as a left/right pair (plan 11 B-6). A reader who
    is shown one hand and not told of the other sizes half an airplane."""
    section = _balanced_section()
    text = " ".join(section.body)
    assert "twin pair" in text
    hands = {row[section.tables[0].columns.index("Hand")]
             for row in section.tables[0].rows}
    assert {"L", "R"} <= hands, hands


def test_the_balanced_section_names_the_massset_of_every_payload_case():
    """The mass-case identity, from the same mint the CONM2 cards use: a consumer
    selecting the wrong MASSSET sizes the airplane at the wrong weight and CG."""
    from sloads.export.mass_cards import mass_case_rows, massset_identity
    from sloads.mass_distribution import derive_case_loadings

    project = io.load_project(_GA)
    rows = mass_case_rows(project)
    exported = [r for r in rows if r["exported"]]
    assert exported, "fixture no longer exports a payload case"
    derivable = [ld for ld in derive_case_loadings(project) if ld.derivable]
    sid, label = massset_identity(derivable, 0)
    assert exported[0]["massset_sid"] == sid
    assert exported[0]["massset_label"] == label

    table = _balanced_section().tables[1]
    assert table.columns[0] == "Payload case"
    assert [row[0] for row in table.rows] == [r["case"] for r in rows]
    massset = table.columns.index("MASSSET")
    assert f"{sid} ({label})" in table.rows[0][massset]
    # D-25: every row states which route produced its loading.
    provenance = table.columns.index("Loading")
    assert {row[provenance] for row in table.rows} <= {"entered", "derived"}


def test_a_payload_case_the_database_cannot_produce_is_reported_not_dropped():
    """"Absent from the mass model" is the fact a consumer needs (plan 12 C-1).

    The unproducible case is **built** here. Since Pri 5 / D-26 every case of
    every shipped fixture is a loading its own weight database can produce, so
    there is no fixture left to read it off -- and a reporting path whose only
    test is "some fixture happens to fail" stops testing anything the day the
    fixtures are fixed, which is the day that step arrived.
    """
    from sloads.export.mass_cards import mass_case_rows

    path = os.path.join(_EXAMPLES, "atr42_100.project.json")
    project = io.load_project(path)
    assert all(r["exported"] for r in mass_case_rows(project))     # as shipped

    case = next(c for c in project.weight.cg_cases if c.name == "fwd gross")
    case.loading = None
    case.xcg = min(it.x for it in project.weight.items) - 40.0
    rows = mass_case_rows(project)
    assert any(not r["exported"] for r in rows)
    doc = build_report(project, tool_version="test")
    table = next(t for t in doc.section("Balanced free-free airframe cases").tables
                 if t.title.startswith("Payload cases"))
    assert any(row[1] == "NOT EXPORTED" for row in table.rows)


def test_the_balanced_section_states_its_absence_rather_than_vanishing():
    """§3.4: the primary deliverable being absent is content, not silence."""
    section = build_report(Project(name="empty")).section(
        "Balanced free-free airframe cases")
    assert not section.tables
    assert "NOT part of this deliverable" in section.absent_reason


def test_the_mass_model_is_tabulated_even_when_nothing_assembles():
    """The mass model is a deliverable of its own, and the manifest points every
    one of its files at §6 — so a fixture that exports mass but assembles no
    balanced case must still find its table there."""
    heavy = os.path.join(_EXAMPLES, "concept_heavy.project.json")
    project = io.load_project(heavy)
    if not (project.weight is not None and project.weight.items):
        pytest.skip("fixture no longer carries a weight database")
    section = _balanced_section(heavy)
    if section.absent_reason:
        assert len(section.tables) == 1
        assert section.tables[0].columns[0] == "Payload case"
    else:                                    # the fixture started assembling
        assert len(section.tables) == 2


def test_the_manifest_lists_the_balanced_deck_and_the_mass_model():
    """review F-D2: an artifact the controlling document does not name travels
    without the basis statement the manifest exists to give it."""
    files = [row[0] for row in _report().section("Appendix A. Bundle manifest").table.rows]
    for name in ("sbeam/<project>_balanced_airframe.bdf",
                 "sbeam/<project>_mass_model.bdf",
                 "sbeam/<project>_mass_check.bdf",
                 "sbeam/<project>_inertia_only.bdf"):
        assert name in files, files
    # ...and every one of them points at the section that summarises it.
    for row in _report().section("Appendix A. Bundle manifest").table.rows:
        if "balanced_airframe" in row[0] or "mass_" in row[0] or "inertia_" in row[0]:
            assert row[-1] == section_ref("balanced"), row


# --------------------------------------------------------------------------- #
# Manifest conformance (review CR-C-1 / CR-C-3)
# --------------------------------------------------------------------------- #
#: The **basis** each manifest row states, pinned by its text and not merely by
#: the filename (review **CR-C-3**). The manifest declared ``inertia_only.bdf``
#: ULTIMATE while the file itself writes ``LIMIT (no SF)`` in band and its
#: writer's docstring says the unfactored comparison is the whole point: the
#: controlling document and the artifact were out by 1.5x on the one file whose
#: only job is to be compared against a solver's own recovery. The F-D2 test
#: could not see it, because it read the row's name and stopped there. So every
#: row's basis cell is pinned here, and a new row arrives with its basis stated.
MANIFEST_BASIS = {
    "<project>.json": "\u2014",
    "<project>_case_index.csv": "IDs are verbatim, never renumbered",
    "<project>_safety_factors.csv": "factors, not loads \u2014 nothing here is scaled",
    "METHODS.txt": "\u2014",
    "<project>_summary_report.tex": "the basis of every other file here",
    "<project>_summary_report.pdf": "identical content to the .tex beside it",
    "load_cases/<project>_<module>.csv": "ULTIMATE loads, SF column per case",
    "<project>_report.txt": "ULTIMATE",
    "<project>_gear_loads.csv":
        "ULTIMATE; contact patch ground-line, reference point airplane-datum",
    "sbeam/<project>_wing_stick.bdf": "geometry only",
    "sbeam/<project>_fuselage_loads.bdf": "ULTIMATE",
    "sbeam/<project>_fuselage_fitting_loads.csv":
        "already carried by the span loads \u2014 do not superpose",
    "sbeam/<project>_control_surface_loads.csv":
        "standard simplified distributions; ULTIMATE",
    "sbeam/<project>_control_surface_loads.bdf": "ULTIMATE",
    "sbeam/<project>_balanced_airframe.bdf":
        "ULTIMATE; determinate support, its reaction is the residual",
    "sbeam/<project>_lra_model.bdf": "ULTIMATE; torsion about each surface's LRA",
    "sbeam/<project>_mass_model.bdf":
        "mass, NOT weight; do not apply with the load decks",
    "sbeam/<project>_mass_check.bdf": "no load cards, by construction",
    "sbeam/<project>_inertia_only.bdf":
        "LIMIT (no SF) \u2014 comparison only, never applied",
}

#: Rows whose basis cell names a **live** value (the wing's loads reference axis,
#: which the project may move) and so is pinned by substring, not by equality.
MANIFEST_BASIS_CONTAINS = {
    "sbeam/<project>_wing_span_loads.csv": ("torsion Myy about the", "ULTIMATE"),
    "sbeam/<project>_wing_loads.bdf": ("torsion about the", "ULTIMATE"),
    "sbeam/<project>_fuselage_span_loads.csv": ("torsion Mxx about the body X axis",
                                                "ULTIMATE"),
    "sbeam/<project>_tail_chordwise.csv": ("Fn is normal to the surface", "ULTIMATE"),
    "sbeam/<project>_tail_loads.bdf": ("normal to each surface", "ULTIMATE"),
}


def test_every_manifest_row_states_the_basis_its_file_actually_carries():
    """**CR-C-3.** The basis cell is the reason the manifest exists; pin it.

    Exhaustive on the GA fixture, both ways: a row with an unpinned basis fails
    here, and a pin with no row fails too \u2014 the pair of holes that let the
    ``inertia_only`` mislabel sit through two reviews.
    """
    rows = _report().section("Appendix A. Bundle manifest").table.rows
    for row in rows:
        name, basis = row[0], row[3]
        if name in MANIFEST_BASIS_CONTAINS:
            for fragment in MANIFEST_BASIS_CONTAINS[name]:
                assert fragment in basis, (name, fragment, basis)
            continue
        assert name in MANIFEST_BASIS, f"unpinned basis cell: {name} -> {basis}"
        assert basis == MANIFEST_BASIS[name], (name, basis)
    assert {r[0] for r in rows} == set(MANIFEST_BASIS) | set(MANIFEST_BASIS_CONTAINS)


def test_the_inertia_check_is_declared_limit_because_that_is_what_it_is():
    """The specific mislabel CR-C-3 found, held against the artifact itself: the
    deck the manifest describes writes LIMIT in band, deliberately (the M-b
    roundtrip leg compares it unfactored), so an ULTIMATE claim in the manifest
    would be wrong by exactly the 1.5 factor."""
    from sloads.export.mass_cards import inertia_only_cards

    assert "LIMIT (no SF)" in inertia_only_cards(io.load_project(_GA))
    row = [r for r in _report().section("Appendix A. Bundle manifest").table.rows
           if r[0] == "sbeam/<project>_inertia_only.bdf"]
    assert row, "the inertia check is no longer manifested"
    assert "LIMIT (no SF)" in row[0][3]
    assert "ULTIMATE" not in row[0][3]


# --------------------------------------------------------------------------- #
# Section numbering and cross-references (review F-R2)
# --------------------------------------------------------------------------- #
#: Which section summarises each companion file, by section **key** and the
#: subsection it names — never by number. The numbers themselves are
#: :data:`sloads.report.content.SECTIONS`' business; what this map pins is the
#: pointing, which is the part a reader follows and the part that was wrong:
#: after the §2 sign-conventions insertion three rows still pointed one section
#: short, and the §6 balanced insertion moved methods to §7 without moving the
#: manifest with it (F-R2). Add a row to the manifest, add it here.
SUMMARISED_IN = {
    "<project>.json": ("inputs", ""),
    "<project>_case_index.csv": ("conditions", ""),
    "<project>_safety_factors.csv": ("factors", ""),
    "METHODS.txt": ("methods", ""),
    "load_cases/<project>_<module>.csv": ("results", ""),
    "<project>_report.txt": ("results", ""),
    "sbeam/<project>_wing_span_loads.csv": ("results", "Wing"),
    "sbeam/<project>_wing_loads.bdf": ("results", "Wing"),
    "sbeam/<project>_wing_stick.bdf": ("results", "Wing"),
    "sbeam/<project>_fuselage_span_loads.csv": ("results", "Fuselage"),
    "sbeam/<project>_fuselage_loads.bdf": ("results", "Fuselage"),
    "sbeam/<project>_fuselage_fitting_loads.csv": ("results", "Fuselage"),
    "sbeam/<project>_tail_chordwise.csv": ("results", "Horizontal tail / Vertical tail"),
    "sbeam/<project>_tail_loads.bdf": ("results", "Horizontal tail / Vertical tail"),
    "sbeam/<project>_control_surface_loads.csv": ("results", "Control surfaces"),
    "sbeam/<project>_control_surface_loads.bdf": ("results", "Control surfaces"),
    "<project>_summary_report.tex": ("inputs", ""),
    "<project>_summary_report.pdf": ("inputs", ""),
    "sbeam/<project>_balanced_airframe.bdf": ("balanced", ""),
    "sbeam/<project>_lra_model.bdf": ("balanced", ""),
    "sbeam/<project>_mass_model.bdf": ("balanced", ""),
    "sbeam/<project>_mass_check.bdf": ("balanced", ""),
    "sbeam/<project>_inertia_only.bdf": ("balanced", ""),
    "<project>_gear_loads.csv": ("gear", ""),
}


def test_the_numbering_owner_agrees_with_the_document():
    """``SECTIONS`` is the single source of the numbering, so its numbers must be
    the document's own positions -- otherwise every reference built from it is
    wrong in one move rather than right in one move."""
    titles = [s.title for s in _report().sections]
    for key, _ in SECTIONS:
        assert section_heading(key) in titles, (key, titles)
        assert section_ref(key) == f"§{titles.index(section_heading(key)) + 1}"


def test_the_manifest_points_each_file_at_the_section_that_summarises_it():
    """Review **F-R2**. Every companion file's "Summarised in" cell names the
    section that actually describes it -- the reference an analyst follows from
    the file back to its basis."""
    rows = _report().section("Appendix A. Bundle manifest").table.rows
    assert rows
    for row in rows:
        assert row[0] in SUMMARISED_IN, f"manifest row not pinned: {row[0]}"
        assert row[-1] == section_ref(*SUMMARISED_IN[row[0]]), row
    # The GA fixture exports every channel, so the pin is exhaustive on it: a new
    # manifest row cannot slip in unpinned.
    assert {row[0] for row in rows} == set(SUMMARISED_IN)


def test_every_manifest_reference_resolves_to_a_real_section():
    """A cross-reference is only useful if the thing it names exists. Checks the
    number against the document's own order and each suffix against the
    referenced section's real subsection titles ("§5 Tails" named no heading)."""
    doc = _report()
    manifest = doc.section("Appendix A. Bundle manifest")
    for row in manifest.table.rows:
        m = re.fullmatch(r"§(\d+)(?: (.+))?", row[-1])
        assert m, row
        number = int(m.group(1))
        assert 1 <= number <= len(SECTIONS), row
        section = doc.sections[number - 1]
        assert section.title.startswith(f"{number}. "), (row, section.title)
        for name in (m.group(2) or "").split(" / "):
            if name:
                assert section.subsection(name) is not None, (row, name)


def test_no_rendered_cross_reference_points_past_the_last_section():
    """The document-wide sweep behind the two pins above: nothing rendered
    anywhere -- prose, table cells, notes, the methods statement -- may name a
    section the document does not have."""
    doc = _report()
    numbered = len(SECTIONS)
    strings = [doc.basis, doc.units_note, doc.methods]
    stack = list(doc.sections)
    while stack:
        s = stack.pop(0)
        strings += list(s.body) + [s.absent_reason or ""]
        for t in s.tables:
            strings += [t.title, t.note] + [str(c) for row in t.rows for c in row]
        stack = list(s.subsections) + stack
    seen = 0
    for text in strings:
        for ref in re.findall(r"§(\d+)", text or ""):
            seen += 1
            assert 1 <= int(ref) <= numbered, f"stale section reference §{ref}: {text}"
    assert seen, "no cross-reference found -- the sweep is not looking at the text"


def test_the_manifest_does_not_list_files_the_bundle_will_not_contain():
    """A manifest naming an artifact that was never written is worse than none:
    the reader goes looking for it."""
    files = [row[0] for row in
             build_report(Project(name="empty")).section("Appendix A. Bundle manifest").table.rows]
    assert not any("balanced_airframe" in f or "mass_" in f for f in files), files


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
    scope_text = " ".join(doc.section("Conditions analysed and FAR coverage").body)
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
    assert doc.section("Methods and limitations").body[0] == doc.methods


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
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    raise SystemExit(1 if failures else 0)
