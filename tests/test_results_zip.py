"""Guard for the whole-project results zip (C210-45, backlog 19c).

The builder is pure (`sloads/report/results_zip.py`); these tests read **the
artifact the user receives** -- the zip bytes -- not a source pattern that
resembles it (the G7 lesson).
"""

from __future__ import annotations

import io
import zipfile

import pytest

from sloads import io as sloads_io
from sloads import registry
from sloads.report.results_zip import (
    results_zip_bytes,
    results_zip_members,
    results_zip_name,
)

GA6 = "examples/ga6_normal.project.json"


@pytest.fixture(scope="module")
def ga6_zip():
    project = sloads_io.load_project(GA6)
    data, manifest = results_zip_bytes(project, tool_version="test")
    return project, zipfile.ZipFile(io.BytesIO(data)), manifest


def test_every_module_is_manifested(ga6_zip):
    """One manifest line per registered module -- silent truncation impossible."""
    _, z, manifest = ga6_zip
    named = {line.split(":", 1)[0] for line in manifest}
    assert named == set(registry.available())
    assert "MANIFEST.txt" in z.namelist()
    body = z.read("MANIFEST.txt").decode()
    for line in manifest:
        assert line in body


def test_ok_modules_contribute_report_and_csv(ga6_zip):
    """A module that ran owes both members; one that refused owes neither."""
    _, z, manifest = ga6_zip
    names = set(z.namelist())
    for line in manifest:
        module, outcome = line.split(":", 1)
        has_txt = f"reports/{module}.txt" in names
        has_csv = f"load_cases/{module}.csv" in names
        if outcome.strip() == "OK":
            assert has_txt and has_csv, module
        else:
            assert not has_txt and not has_csv, module


def test_report_is_the_cli_renderer(ga6_zip):
    """The text report carries the ULT contract statement, as cli.py's does."""
    _, z, _ = ga6_zip
    txt = z.read("reports/flap.txt").decode()
    assert "Loads are LIMIT" in txt and "sizing analysis" in txt


def test_csv_carries_the_basis_statement(ga6_zip):
    """A CSV that leaves the tool states its basis (G8.3)."""
    _, z, _ = ga6_zip
    csv_text = z.read("load_cases/flap.csv").decode()
    assert csv_text.startswith("#")  # the csv_comment_block header


def test_project_round_trips(ga6_zip):
    """The archived project reloads to the same serialization."""
    project, z, _ = ga6_zip
    member = sloads_io.project_filename(project.name)
    assert member in z.namelist()
    reloaded = sloads_io.project_from_dict(
        __import__("json").loads(z.read(member).decode()))
    assert sloads_io.project_to_json(reloaded) == sloads_io.project_to_json(project)


def test_deterministic_and_named(ga6_zip):
    """Two builds of one project are member-identical; the name is sanitised."""
    project, z, _ = ga6_zip
    data2, _ = results_zip_bytes(project, tool_version="test")
    assert zipfile.ZipFile(io.BytesIO(data2)).namelist() == z.namelist()
    name = results_zip_name(project)
    assert name.endswith("_results.zip")
    assert " " not in name


def test_members_match_bytes(ga6_zip):
    """`results_zip_members` is the namelist of the bytes -- one member plan."""
    project, z, _ = ga6_zip
    members, _ = results_zip_members(project, tool_version="test")
    assert [m.name for m in members] == z.namelist()


if __name__ == "__main__":  # zero-dependency self-runner (repo convention)
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
