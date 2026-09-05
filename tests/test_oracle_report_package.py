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
import subprocess
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
    # Note 49 OR-116: the package states LIMIT, names who applies the factor, and
    # keeps the -ULT marker's explanation for the two already-ultimate families.
    assert "LIMIT" in text and "-ULT" in text
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



# --- choosing the location (the report page's folder browser) --------------


def test_the_browse_opens_at_a_folder_that_exists():
    """A root that has not been created yet browses from its nearest ancestor.

    The default report root usually does *not* exist -- the first build makes
    it. Opening the browser there would show an empty folder list with no way
    out, which is a dead end rather than a starting point.
    """
    with tempfile.TemporaryDirectory() as tmp:
        deep = os.path.join(tmp, "not", "made", "yet")
        assert pkg.browse_start(deep) == os.path.abspath(tmp)
        real = os.path.join(tmp, "real")
        os.makedirs(real)
        assert pkg.browse_start(real) == os.path.abspath(real)


def test_the_folder_list_hides_dot_directories_and_files():
    """Only visible subdirectories: a user filing a signed report is not
    looking for ``.git``, and listing it invites writing into it."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "Programme-X"))
        os.makedirs(os.path.join(tmp, ".hidden"))
        with open(os.path.join(tmp, "a-file.txt"), "w") as fh:
            fh.write("x")
        assert pkg.list_subdirs(tmp) == ["Programme-X"]


def test_an_unreadable_folder_lists_empty_rather_than_raising():
    """The browser must always render. A folder deleted under the session, or
    one the process cannot read, is an empty list and not a traceback."""
    assert pkg.list_subdirs(os.path.join("/nonexistent", "nowhere")) == []


def test_new_folder_refuses_a_path_instead_of_normalising_one():
    """``create_subdir`` takes a *name*, and says so on a path.

    A "new folder here" control that silently accepts ``../../elsewhere`` is not
    the control the user believes they are using -- so a separator or a ``..``
    is refused rather than quietly walked.
    """
    with tempfile.TemporaryDirectory() as tmp:
        for bad in ("../escape", "a/b", "..", "", "   "):
            with pytest.raises(ValueError):
                pkg.create_subdir(tmp, bad)
        made = pkg.create_subdir(tmp, " Programme-X ")
        assert made == os.path.join(tmp, "Programme-X")
        assert os.path.isdir(made)


def test_going_up_terminates_at_the_filesystem_root():
    """``is_root`` is what disables the Up button; without it the browser
    offers a level above the top that quietly goes nowhere."""
    top = os.path.abspath(os.sep)
    assert pkg.is_root(top)
    assert pkg.parent_of(top) == top
    with tempfile.TemporaryDirectory() as tmp:
        assert not pkg.is_root(tmp)


def test_the_anchors_start_with_the_default_root_and_do_not_repeat():
    """The OR-29 default is offered first, and a duplicate anchor is dropped --
    two identically-pathed entries in the jump list are a UI that looks like it
    has two answers to one question."""
    anchors = pkg.location_anchors(None)
    labels = [label for label, _path in anchors]
    paths = [path for _label, path in anchors]
    assert "default" in labels[0]
    assert paths[0] == os.path.abspath(pkg.default_report_root(None))
    assert len(paths) == len(set(paths))


def test_an_unreadable_folder_lists_no_packages_rather_than_crashing():
    """The defect that took the report page down, held open.

    Browsing to ``~/Desktop`` on macOS raised ``PermissionError`` straight
    through a page render: TCC blocks ``listdir`` there for a process that has
    not been granted access. A folder this process cannot read holds no packages
    *it can open*, which is what the caller is asking, so it answers empty.
    """
    with tempfile.TemporaryDirectory() as tmp:
        blocked = os.path.join(tmp, "blocked")
        os.makedirs(os.path.join(blocked, "LR-0001_RevA"))
        with open(os.path.join(blocked, "LR-0001_RevA", op.PACKAGE_SPEC), "w") as fh:
            fh.write("{}")
        assert pkg.discover_packages(blocked) == ["LR-0001_RevA"]
        os.chmod(blocked, 0o000)
        try:
            assert pkg.discover_packages(blocked) == []
            assert pkg.list_subdirs(blocked) == []
        finally:
            os.chmod(blocked, 0o755)


def test_saved_projects_survives_an_unreadable_directory():
    """The same defect class, swept where it also lived (CLAUDE.md rule 4).

    ``list_saved_projects`` guarded a *missing* directory and not an unreadable
    one, so the sidebar carried the identical crash for anyone whose projects
    folder sat somewhere protected.
    """
    with tempfile.TemporaryDirectory() as tmp:
        blocked = os.path.join(tmp, "blocked")
        os.makedirs(blocked)
        os.chmod(blocked, 0o000)
        try:
            assert io.list_saved_projects(blocked) == []
        finally:
            os.chmod(blocked, 0o755)


def test_a_folder_that_cannot_be_written_is_reported_before_the_build():
    """Being shown a folder is not being granted it.

    The OS chooser returns a TCC-protected path quite happily; the write then
    fails at the end of a page the user has already filled in. ``is_writable``
    is what lets the page say so up front.
    """
    with tempfile.TemporaryDirectory() as tmp:
        assert pkg.is_writable(tmp)
        assert not pkg.is_writable(os.path.join(tmp, "does-not-exist"))
        blocked = os.path.join(tmp, "ro")
        os.makedirs(blocked)
        os.chmod(blocked, 0o500)
        try:
            assert not pkg.is_writable(blocked)
        finally:
            os.chmod(blocked, 0o755)


def test_the_folder_dialog_never_raises_and_never_invents_a_path(monkeypatch):
    """Every non-answer is ``None``: no dialog, Cancel, timeout, a bad path.

    The caller's response to all of them is identical -- leave the current
    folder alone -- and the in-app browser remains the way through, so a machine
    without a dialog degrades rather than breaks.

    **The real dialog is never opened here.** It waits for a human, so a test
    that called it would hang the suite behind a Finder window on any developer
    machine with a desktop session. The subprocess is stubbed and the decision
    logic is what gets tested.

    **The platform is pinned too.** Stubbing only the subprocess left this test
    asserting the host's own dialog helpers: ``choose_directory`` returns
    ``None`` before it runs anything when this machine has none, so on a bare
    Linux CI runner -- no ``zenity``, no ``kdialog`` -- the first case failed
    while passing on any developer Mac. The four non-answers below are decisions
    made *after* the helper runs, so the helper has to exist for them to be
    reachable at all. The "no helper on this machine" non-answer is the sibling
    test next door, which pins the platform the other way.
    """
    from sloads.export import directory_dialog as dlg

    monkeypatch.setattr(dlg.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dlg.shutil, "which", lambda name: f"/usr/bin/{name}")

    class _Result:
        def __init__(self, code, out):
            self.returncode, self.stdout, self.stderr = code, out, ""

    def stub(result):
        monkeypatch.setattr(dlg.subprocess, "run",
                            lambda *a, **k: result if not isinstance(result, Exception)
                            else (_ for _ in ()).throw(result))

    with tempfile.TemporaryDirectory() as tmp:
        stub(_Result(0, tmp + "\n"))
        assert dlg.choose_directory() == os.path.abspath(tmp)
        # Cancel: non-zero exit is the normal "user said no" on every helper.
        stub(_Result(1, ""))
        assert dlg.choose_directory() is None
        # A path that came back but is not a directory is not a folder choice.
        stub(_Result(0, os.path.join(tmp, "nope")))
        assert dlg.choose_directory() is None
        # A helper that is missing, or that hangs until the timeout.
        stub(OSError("no such helper"))
        assert dlg.choose_directory() is None
        stub(subprocess.TimeoutExpired("osascript", 1))
        assert dlg.choose_directory() is None


def test_no_folder_dialog_is_available_where_the_platform_has_no_helper(monkeypatch):
    """``native_picker_available`` is asked before the button is drawn, so a
    machine without a helper shows the browser instead of a dead control."""
    from sloads.export import directory_dialog as dlg

    monkeypatch.setattr(dlg.shutil, "which", lambda _name: None)
    monkeypatch.setattr(dlg.platform, "system", lambda: "Linux")
    assert dlg.native_picker_available() is False
    assert dlg.choose_directory("/tmp") is None


def test_the_dialog_escapes_a_quoted_path_into_applescript():
    """A folder name may legally contain a quote or a backslash.

    Interpolated raw, it would end the AppleScript string literal early -- at
    best a failed dialog, at worst a script that does something else. The
    command is asserted rather than the escaping helper, so the guard covers the
    place the string is actually built.
    """
    from sloads.export import directory_dialog as dlg

    command = dlg._darwin_command("", 'say "hi" \\ now')
    assert r'\"hi\"' in command[-1]
    assert command[-1].count('"') % 2 == 0

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
