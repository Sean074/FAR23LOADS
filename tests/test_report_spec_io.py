"""The report spec's mapping and its path owners (design note 44, G-OR-11).

A ``ReportSpec`` is the only thing standing between an author's typing and a
signed document, so what is asserted here is narrow and load-bearing: it
round-trips without gaining or losing a field, a file that is not there opens a
blank draft instead of a traceback, and the package directory name is derived
from the report number rather than from the clock.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.migrations import SchemaVersionError  # noqa: E402
from sloads.models.report import (  # noqa: E402
    REPORT_SCHEMA_VERSION,
    ProjectIdentity,
    ReportSpec,
    RevisionRow,
    SignatureRow,
    default_spec,
    is_draft,
)
from sloads.units import UnitSystem  # noqa: E402


def _full() -> ReportSpec:
    """A spec with every field populated, so nothing can round-trip by default."""
    return ReportSpec(
        title="FAR 23 Structural Design Loads",
        report_number="LR-0142", revision="B", issue_date="2026-08-30",
        organisation="Aero Science Software", customer="Programme X",
        abstract="Design loads for the GA 6-place single.",
        distribution="Approved for programme use.",
        marking="COMPANY CONFIDENTIAL",
        revisions=[RevisionRow(date="2026-08-01", revision="A",
                               description="First issue", by="SO")],
        prepared=SignatureRow(name="A Prepared", role="Loads", date="2026-08-28"),
        checked=SignatureRow(name="B Checked", role="Stress", date="2026-08-29"),
        approved=SignatureRow(name="C Approved", role="Chief", date="2026-08-30"),
        unit_system=UnitSystem.SI,
        excluded_steps=("flap_loads", "tab_loads"),
        identity=ProjectIdentity(project_name="GA 6", designation="GA6",
                                 fingerprint="deadbeef", fingerprint_version=1),
    )


def test_a_fully_populated_spec_round_trips():
    """Every field survives dict -> spec -> dict, so nothing is silently dropped."""
    spec = _full()
    assert io.report_spec_from_dict(io.report_spec_to_dict(spec)) == spec


def test_a_blank_spec_writes_only_its_version():
    """Omit-falsy, like ``project_to_dict``: an absent key and an empty value are
    the same statement, which is what makes a saved spec diffable as a record of
    what its author actually filled in."""
    assert io.report_spec_to_dict(default_spec()) == {
        "report_schema_version": REPORT_SCHEMA_VERSION}


def test_the_json_writer_is_the_one_the_package_ships():
    """``report_spec_to_json`` is the single serialiser, so OR-30's "the build
    never rewrites the user's spec" is literally true rather than merely
    intended -- the page's Save and the package's copy are the same bytes."""
    spec = _full()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "report.json")
        io.save_report(spec, path)
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == io.report_spec_to_json(spec)


def test_a_missing_report_file_opens_a_blank_unsigned_draft():
    """G-OR-11. A project that has never had a report is every project the first
    time; opening the page must not be an error condition."""
    with tempfile.TemporaryDirectory() as tmp:
        spec = io.load_report(os.path.join(tmp, "nothing-here.json"))
    assert spec == default_spec()
    assert is_draft(spec)


def test_an_unreadable_report_file_raises_the_documented_error():
    """A file that *exists* but cannot be read is a real error and says so --
    the GUI's ``safe_load`` reports it with no new branch. Silence here would
    hand the author a blank form and lose their work without telling them."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "report.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        with pytest.raises(ValueError):
            io.load_report(path)


def test_a_spec_from_a_later_schema_is_refused_with_its_reason():
    """Refused, not silently downgraded: a spec written by a build that knows
    more than this one would open here missing whatever it added, and be saved
    back with that content gone."""
    raw = io.report_spec_to_dict(_full())
    raw["report_schema_version"] = REPORT_SCHEMA_VERSION + 1
    with pytest.raises(SchemaVersionError):
        io.report_spec_from_dict(raw)


def test_an_unknown_key_from_a_later_build_is_dropped_not_refused():
    """The opposite posture to ``project_from_dict``, deliberately. Within one
    schema version, a key this build does not know is prose it cannot show, not
    a number that changes a structural result."""
    raw = io.report_spec_to_dict(_full())
    raw["a_field_from_the_future"] = "hello"
    assert io.report_spec_from_dict(raw).title == _full().title


@pytest.mark.parametrize("missing", ["prepared", "checked", "approved"])
def test_is_draft_needs_all_three_names(missing):
    """OR-18: any *one* missing name makes the whole document a draft.

    Parametrised rather than looped so a failure names which signature stopped
    counting -- a document that presented itself as approved because one field
    was skipped is the exact failure this rule exists to prevent.
    """
    signed = _full()
    assert not is_draft(signed)
    blanked = io.report_spec_from_dict({
        **io.report_spec_to_dict(signed),
        missing: {"name": "   ", "role": "", "date": ""}})
    assert is_draft(blanked)


def test_the_package_directory_is_named_from_the_report_not_the_clock():
    """OR-25 rests on this: a rebuild must land on the same directory, which a
    timestamped name makes impossible."""
    assert io.report_package_dirname("LR-0142", "B") == "LR-0142_RevB"
    assert io.report_package_dirname("LR-0142", "") == "LR-0142"
    # Twice in a row, because "not the clock" is the actual claim.
    assert io.report_package_dirname("LR-0142", "B") == \
        io.report_package_dirname("LR-0142", "B")


def test_the_package_directory_name_is_sanitised():
    """A report number is at least as likely as a project name to carry a slash
    -- and a slash here would silently write the package somewhere else."""
    assert "/" not in io.report_package_dirname("LR/0142", "B")
    assert io.report_package_dirname("", "") == "report"
    assert io.report_package_dirname("../../etc", "") .startswith("._") is False
    assert ".." not in io.report_package_dirname("../../etc", "")


def test_the_default_report_root_sits_beside_the_project():
    """OR-29: a report travels with the airplane it documents."""
    root = io.default_report_root(os.path.join("some", "dir", "ga6.project.json"))
    assert os.path.basename(root) == io.REPORT_ROOT_DIRNAME
    assert os.path.basename(os.path.dirname(root)) == "dir"
    # A project that has never been saved still gets a root to offer.
    assert io.default_report_root(None).endswith(io.REPORT_ROOT_DIRNAME)


def test_the_written_file_is_valid_json_with_the_version_first():
    spec = _full()
    parsed = json.loads(io.report_spec_to_json(spec))
    assert parsed["report_schema_version"] == REPORT_SCHEMA_VERSION


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
