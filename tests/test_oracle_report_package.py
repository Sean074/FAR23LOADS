"""The issue package on disk (design note 44, G-OR-1/14/15/16/17/19).

The package is what actually gets archived and signed, so what matters here is
not that files appear but that the package *describes itself completely and
truthfully*: the manifest names everything and nothing more, every hash matches,
the spec the user edits is not rewritten by the build, and two builds of one
recipe are the same bytes.

Two gates below are **vacuously true in this iteration** and say so in place:
G-OR-15 and G-OR-17 act on ``data/`` files, and the front-matter-only document
ships none yet. They are written now so the assertion exists before the first
table lands, not because they currently prove anything about shipped data.
"""

import hashlib
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.export import report_package as pkg  # noqa: E402
from sloads.models.report import ReportSpec, SignatureRow  # noqa: E402
from sloads.report import fingerprint as fp  # noqa: E402
from sloads.report import oracle_package as op  # noqa: E402
from sloads.units import UnitSystem  # noqa: E402

_EXAMPLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_TWIN = os.path.join(_EXAMPLES, "baron_58.project.json")

#: A fixed build stamp. The builder takes the timestamp as an argument precisely
#: so this can be held still -- a clock read inside the builder would make
#: G-OR-16 impossible to state, let alone assert.
_BUILT = "2026-08-30 12:00"


def _spec(**kwargs) -> ReportSpec:
    base = dict(title="FAR 23 Structural Design Loads", report_number="LR-0142",
                revision="B", issue_date="2026-08-30", abstract="An abstract.",
                marking="COMPANY CONFIDENTIAL")
    base.update(kwargs)
    return ReportSpec(**base)


def _build(tmp: str, path: str = _GA, spec: ReportSpec = None) -> str:
    project = io.load_project(path)
    return pkg.build_package(
        project, spec or _spec(), root=tmp, built=_BUILT, version="test",
        fingerprint=fp.fingerprint(project),
        fingerprint_version=fp.FINGERPRINT_VERSION)


def _tree(root: str):
    """Every file in the package, as relative POSIX paths."""
    found = []
    for base, _dirs, names in os.walk(root):
        for name in names:
            rel = os.path.relpath(os.path.join(base, name), root)
            found.append(rel.replace(os.sep, "/"))
    return sorted(found)


def _manifest_entries(root: str):
    """``{name: sha256}`` parsed back out of ``MANIFEST.txt``.

    Parsed rather than trusted: the manifest is the artifact the reader holds, so
    the test reads what they would read, not the structure it was built from.
    """
    with open(os.path.join(root, op.PACKAGE_MANIFEST), encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    entries, current = {}, None
    for line in lines:
        stripped = line.strip()
        if line.startswith("  ") and not line.startswith("    ") and stripped:
            current = stripped
        elif stripped.startswith("sha256") and current:
            entries[current] = stripped.split(None, 1)[1]
    return entries


# --------------------------------------------------------------------------- #
# G-OR-1 -- it builds, for both example airplanes (OR-11)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("example", [_GA, _TWIN])
def test_the_package_builds_for_both_examples(example):
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp, example)
        assert os.path.basename(out) == "LR-0142_RevB"
        with open(os.path.join(out, op.PACKAGE_TEX), encoding="utf-8") as fh:
            tex = fh.read()
        assert tex.startswith("\\documentclass")
        assert tex.rstrip().endswith("\\end{document}")


# --------------------------------------------------------------------------- #
# G-OR-14 -- the package is exactly its manifest, both directions
# --------------------------------------------------------------------------- #
def test_the_package_contains_exactly_what_the_manifest_lists():
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        assert set(_tree(out)) == set(_manifest_entries(out)), (
            "the manifest and the directory disagree; a file listed but absent "
            "sends the reader hunting, and a file present but unlisted travels "
            "without the basis statement the manifest exists to give it")


def test_the_manifest_lists_itself():
    """Review CR-C-1's defect was a manifest that named every file except the one
    the reader is holding. Its own hash cannot be inside it, so the row says so
    rather than being quietly dropped."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        entries = _manifest_entries(out)
        assert entries[op.PACKAGE_MANIFEST] == op.SELF_HASH


def test_every_manifest_hash_matches_the_file():
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        for name, digest in _manifest_entries(out).items():
            if digest == op.SELF_HASH:
                continue
            with open(os.path.join(out, name), "rb") as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
            assert actual == digest, name


def test_no_engine_aux_files_reach_the_package():
    """OR-26: the PDF is compiled out of tree and only the PDF copied back, or
    the determinism gate becomes an argument with the toolchain."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        for name in _tree(out):
            assert not name.endswith((".aux", ".log", ".out", ".toc", ".fls"))


# --------------------------------------------------------------------------- #
# G-OR-14 as widened by OR-35 -- it is a SUMMARY_REPORT.md 4.7 manifest
# --------------------------------------------------------------------------- #
def test_the_manifest_states_the_package_unit_system_once_up_front():
    """§4.7: the manifest opens by stating the bundle's unit system and asserting
    every listed file is in it. A per-file units column that disagrees with that
    statement is a conformance failure, not a footnote."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp, spec=_spec(unit_system=UnitSystem.SI))
        with open(os.path.join(out, op.PACKAGE_MANIFEST), encoding="utf-8") as fh:
            text = fh.read()
    assert "SI units" in text
    assert "ULTIMATE" in text and "-ULT" in text
    assert "safety factor" in text and "basis" in text


def test_every_manifest_row_carries_the_four_required_facts():
    """§4.7 requires each file's contents, units, conventions and the section
    that summarises it -- the CR-C-3 lesson is that a row pinned by its filename
    alone let a LIMIT artifact be labelled ULTIMATE through two reviews."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        with open(os.path.join(out, op.PACKAGE_MANIFEST), encoding="utf-8") as fh:
            text = fh.read()
        for name in _manifest_entries(out):
            block = text.split(f"  {name}\n", 1)[1]
            for label in ("contents", "units", "conventions", "summarised in"):
                assert label in block.split("\n\n", 1)[0], \
                    f"{name} is missing {label}"


def test_the_manifest_never_writes_a_section_number_as_a_literal():
    """§4.7: references are built from the numbering owner. A reference that does
    not move when a section is inserted above it is a reference to the wrong
    section (review F-R2)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        with open(os.path.join(out, op.PACKAGE_MANIFEST), encoding="utf-8") as fh:
            text = fh.read()
    assert "§" not in text, "a literal section mark reached the manifest"


# --------------------------------------------------------------------------- #
# G-OR-16 / G-OR-19 -- determinism, and the spec the build must not touch
# --------------------------------------------------------------------------- #
def test_two_builds_of_one_project_and_spec_are_byte_identical():
    """G-OR-16, extending G-OR-5 from the document to the whole tree.

    Same project, same spec, same supplied timestamp -- the qualifier is real and
    is stated in ``ORACLE_REPORT.md``: ``build.json`` carries the build time, so
    determinism is over the recipe, not over the wall clock.
    """
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        a, b = _build(one), _build(two)
        assert _tree(a) == _tree(b)
        for name in _tree(a):
            with open(os.path.join(a, name), "rb") as fh1, \
                    open(os.path.join(b, name), "rb") as fh2:
                assert fh1.read() == fh2.read(), name


def test_the_build_does_not_rewrite_the_users_spec():
    """G-OR-19 / OR-30. ``report.json`` is what a person typed; the as-built
    stamp lives in ``build.json``. Keeping them apart is what lets the gate above
    compare whole files instead of maintaining a list of fields to ignore."""
    with tempfile.TemporaryDirectory() as tmp:
        spec = _spec()
        out = _build(tmp, spec=spec)
        with open(os.path.join(out, op.PACKAGE_SPEC), encoding="utf-8") as fh:
            written = fh.read()
    assert written == io.report_spec_to_json(spec)
    assert "fingerprint" not in json.loads(written)


def test_the_build_stamp_carries_the_provenance():
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        with open(os.path.join(out, op.PACKAGE_BUILD), encoding="utf-8") as fh:
            stamp = json.load(fh)
    assert stamp["built"] == _BUILT
    assert stamp["tool_version"] == "test"
    assert stamp["fingerprint"] == fp.fingerprint(io.load_project(_GA))
    assert stamp["fingerprint_version"] == fp.FINGERPRINT_VERSION


def test_rebuilding_the_same_revision_overwrites_in_place():
    """OR-25: the package is a build product and the edit-build-read loop must
    not carry friction."""
    with tempfile.TemporaryDirectory() as tmp:
        first = _build(tmp)
        second = _build(tmp, spec=_spec(abstract="A revised abstract."))
        assert first == second
        assert pkg.discover_packages(tmp) == ["LR-0142_RevB"]
        with open(os.path.join(second, op.PACKAGE_SPEC), encoding="utf-8") as fh:
            assert "revised abstract" in fh.read()


def test_a_new_revision_makes_a_new_directory_beside_the_old():
    """OR-25's other half: an issued revision is never destroyed by continued
    work."""
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp)
        _build(tmp, spec=_spec(revision="C"))
        assert pkg.discover_packages(tmp) == ["LR-0142_RevB", "LR-0142_RevC"]


def test_a_local_pdf_survives_a_rebuild():
    """OR-22 lists ``report.pdf`` in the tree and the build did not put it there,
    so the build has no business deleting it."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        pdf = os.path.join(out, "report.pdf")
        with open(pdf, "wb") as fh:
            fh.write(b"%PDF-1.4 pretend")
        _build(tmp)
        assert os.path.isfile(pdf)


def test_a_member_that_escapes_the_package_root_is_refused():
    """``SUMMARY_REPORT.md`` §2's *Data reference* clause requires every path to
    be relative and stay inside the package. A path that escapes is a bug worth
    failing on, not a file worth writing."""
    member = op.PackageMember(name="../escaped.txt", content="x", contents="x")
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError):
            pkg.write_members(tmp, "LR-0142_RevB", [member])


# --------------------------------------------------------------------------- #
# Discovery, and the page's read path
# --------------------------------------------------------------------------- #
def test_discovery_finds_packages_and_tolerates_a_missing_root():
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "no-reports-yet")
        assert pkg.discover_packages(missing) == []
        _build(tmp)
        assert pkg.discover_packages(tmp) == ["LR-0142_RevB"]
        # A directory without a spec is not a package.
        os.makedirs(os.path.join(tmp, "not-a-package"))
        assert pkg.discover_packages(tmp) == ["LR-0142_RevB"]


def test_reopening_a_package_returns_the_spec_that_was_saved():
    """OR-28: the package directory is the spec's home, so opening one is
    resuming work rather than reading history."""
    spec = _spec(prepared=SignatureRow(name="A Prepared"))
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp, spec=spec)
        assert pkg.read_spec(tmp, "LR-0142_RevB") == spec
    assert pkg.read_spec("nowhere", "") == ReportSpec()


# --------------------------------------------------------------------------- #
# G-OR-15 / G-OR-17 -- written now, vacuous until the first analysis section
# --------------------------------------------------------------------------- #
def test_every_shipped_data_file_is_self_describing():
    """G-OR-15. **Vacuous in this iteration**: the front-matter-only document
    draws no table or plot from shipped data, so there is nothing under ``data/``
    to check. The assertion exists so it is in place before the first section
    that does ship data -- it is not evidence that shipped data has been checked.
    """
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        data = [n for n in _tree(out) if n.startswith(op.DATA_DIR + "/")]
        assert not data, (
            "data files now ship: give this test its real body -- units with the "
            "-ULT marker, safety factor and basis, step key and fingerprint in "
            "every header (OR-23)")


def test_no_orphan_data_files_in_either_direction():
    """G-OR-17, **vacuous for the same reason** and kept for the same one."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _build(tmp)
        with open(os.path.join(out, op.PACKAGE_TEX), encoding="utf-8") as fh:
            tex = fh.read()
        data = [n for n in _tree(out) if n.startswith(op.DATA_DIR + "/")]
        for name in data:
            assert name in tex, f"{name} ships but the document never reads it"
        assert "\\input{" not in tex or data, (
            "the document reads a fragment the package does not carry")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
