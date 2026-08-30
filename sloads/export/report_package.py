"""Writing the oracle report's **issue package** to disk, and finding one again.

Design note 44, OR-22/OR-25/OR-29. This is the impure half of the package:
:mod:`sloads.report.oracle_package` decides *what the files are*, and this module
puts them on the filesystem. That split is why it lives here -- everything in
:mod:`sloads.report` is pure, and :mod:`sloads.export.pdf` is the standing
precedent for the piece that cannot be.

It is also what the oracle GUI needs. That front end may not import ``os``,
``pathlib``, ``json`` or ``hashlib`` at all (gate G1,
``tests/test_oracle_gui.py``), so every path the report page shows or writes has
to be computed here or in :mod:`sloads.io`. The import gate turns "the page owns
no filesystem knowledge" from a convention into something enforced.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import List, Optional, Sequence

from .. import io as io_
from ..models import Project
from ..models.report import ReportSpec, default_spec
from ..report.oracle_package import (
    DATA_DIR,
    PACKAGE_SPEC,
    PackageMember,
    package_members,
)


def build_timestamp() -> str:
    """``YYYY-MM-DD HH:MM`` now -- the one clock read on the report path.

    Deliberately a separate call rather than a default argument inside the
    builder: the builder must be given a timestamp, so a test can hold it fixed
    and G-OR-16's byte-identical rebuild means something. A default here would
    make determinism accidental.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def tool_version() -> str:
    """The installed ``sloads`` version, for ``build.json``.

    Here for the same reason :func:`build_timestamp` is: the report page may not
    import ``importlib`` (the oracle GUI's import gate), and a stamp that records
    the generator without recording *which* generator answers half the question a
    reader of an archived package is asking.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("sloads")
    except PackageNotFoundError:
        # Running from a source tree with no install. Say so rather than
        # inventing a number the package would then claim it was built by.
        return "unknown"


def package_dir(root: str, dirname: str) -> str:
    return os.path.join(root, dirname)


def discover_packages(root: str) -> List[str]:
    """Names of the issue packages under ``root``, sorted.

    A directory counts as a package if it holds a ``report.json`` -- the spec is
    the thing that makes it one (OR-28). A missing root is not an error: it is a
    project that has no reports yet, which is every project the first time.
    """
    if not os.path.isdir(root):
        return []
    names = []
    for name in os.listdir(root):
        if os.path.isfile(os.path.join(root, name, PACKAGE_SPEC)):
            names.append(name)
    return sorted(names)


def read_spec(root: str, dirname: str) -> ReportSpec:
    """The spec of the package at ``root/dirname``, or a blank draft."""
    if not dirname:
        return default_spec()
    return io_.load_report(os.path.join(package_dir(root, dirname), PACKAGE_SPEC))


def write_spec(root: str, dirname: str, spec: ReportSpec) -> str:
    """Save the spec into its package directory, creating it if needed.

    This is the page's Save, and it is the *only* writer of ``report.json``
    besides the build's own copy of the identical bytes (OR-30).
    """
    target = package_dir(root, dirname)
    os.makedirs(target, exist_ok=True)
    io_.save_report(spec, os.path.join(target, PACKAGE_SPEC))
    return target


def write_members(root: str, dirname: str,
                  members: Sequence[PackageMember]) -> str:
    """Write ``members`` into ``root/dirname`` and return the directory.

    **Overwrites in place, silently** (OR-25): the package is a build product and
    the edit-build-read loop must not carry friction.

    Two things it does *not* do, both deliberate:

    * it never removes the package directory. A ``report.pdf`` from a local
      compile lives there (OR-22) and is not ours to delete;
    * but it does clear ``data/`` first. A CSV left over from a build whose
      section has since been excluded would survive as a stray, and the manifest
      would then be wrong in the one direction G-OR-14 exists to catch.

    Every member name is checked to stay inside the package root before anything
    is written -- ``SUMMARY_REPORT.md`` §2's *Data reference* clause requires
    relative, in-package paths, and a path that escapes is a bug worth failing on
    rather than a file worth writing.
    """
    target = os.path.abspath(package_dir(root, dirname))
    for member in members:
        resolved = os.path.abspath(os.path.join(target, member.name))
        if os.path.commonpath([target, resolved]) != target:
            raise ValueError(
                f"package member {member.name!r} resolves outside the package "
                "root; every path in a package must be relative and stay inside "
                "it (SUMMARY_REPORT.md 2, Data reference)")
    os.makedirs(target, exist_ok=True)
    data_dir = os.path.join(target, DATA_DIR)
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
    for member in members:
        path = os.path.join(target, member.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(member.content)
    return target


def build_package(project: Project, spec: ReportSpec, *, root: str,
                  built: Optional[str] = None, version: Optional[str] = None,
                  **kwargs: object) -> str:
    """Plan and write one issue package; return its directory.

    The directory name comes from the report number and revision
    (:func:`sloads.io.report_package_dirname`), so rebuilding an issue lands on
    the same directory and bumping the revision makes a new one beside it --
    an issued revision is never destroyed by continued work (OR-25).
    """
    dirname = io_.report_package_dirname(spec.report_number, spec.revision)
    members = package_members(project, spec,
                              built=built or build_timestamp(),
                              tool_version=(tool_version() if version is None
                                            else version),
                              **kwargs)  # type: ignore[arg-type]
    return write_members(root, dirname, members)


__all__ = [
    "build_package",
    "build_timestamp",
    "discover_packages",
    "package_dir",
    "read_spec",
    "tool_version",
    "write_members",
    "write_spec",
]
