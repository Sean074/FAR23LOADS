"""The sidebar's whole-project results zip (C210-45, backlog 19c).

The C210 build review (2026-08-23) left the owner collecting thirteen pages of
results one hand-clicked download at a time; no control delivered a complete
results set for a project. This module is the **pure** builder behind the shared
sidebar's "Download results (zip)" button (`app_shell/sidebar.py`): run every
registered module for the current project, render each through the owners the
CLI and oracle GUI already use, and return the zip bytes for
``st.download_button``.

**Every artifact comes from an owner** (the OG-6 rule, one level up):

* text report -- :func:`sloads.report.module_text_report`, the call ``cli.py``
  makes, so the ULT marker and per-case SF statement are identical by
  construction;
* load-case CSV -- :func:`sloads.io.load_cases_csv` with
  :func:`sloads.report.methods.csv_comment_block` (the G8.3 basis statement:
  a CSV that leaves the tool states its basis and unit system);
* the project itself -- :func:`sloads.io.project_to_json` under the same
  sanitised ``.project.json`` name Save-to-disk writes (CR-D-9);
* zip assembly -- :class:`sloads.report.bundle.BundleMember` /
  :func:`sloads.report.bundle.bundle_zip_bytes`, the Export bundle's writers.

**Skip-and-manifest.** A module that raises ``MissingInputError`` (slice absent)
or ``ValueError`` (input present but unusable -- the error contract's two
halves, ``00_program_overview.md``) contributes no files; ``MANIFEST.txt``
states every module's outcome, so silent truncation is impossible: the one
document a recipient reads first says exactly what ran and what refused, and
why. Any other exception propagates (M2R-8: a genuine defect stays visible).

**Safety factors.** Results are stamped from the project's governing
safety-factor table before rendering (:func:`sloads.safety_factors.stamp`),
exactly as :func:`sloads.registry.run_all_modules` does -- so a zip member can
never state a different factor than the page it mirrors. Which *basis* those
loads are on is the caller's ``channel`` (design note 48): the shared sidebar
serves this zip in both GUIs, so ``app/Home.py`` opts into LIMIT while the
frozen ``oracle_app/Oracle.py`` passes nothing and keeps ULTIMATE. The wording
here used to say "than the deliverable would" -- since note 48 the per-module
zip is not the deliverable, the exported deck is.

Deterministic: the builder never reads the clock (``generated`` is the caller's
timestamp and defaults to absent), so two runs on one project are
byte-identical -- the ``report.methods`` provenance rule.

Pure functions, no Streamlit; ``tests/test_results_zip.py`` is the guard.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .. import io as sloads_io
from .. import registry
from ..models import MissingInputError, Project
from ..safety_factors import stamp
from ..units import UnitSystem
from .bundle import BundleMember, bundle_zip_bytes
from .methods import csv_comment_block
from .render import LoadChannel, module_text_report

__all__ = ["results_zip_bytes", "results_zip_members", "results_zip_name"]


def results_zip_name(project: Project) -> str:
    """``<stem>_results.zip`` -- the Save-to-disk stem (#65 sanitiser, CR-D-9)."""
    stem = sloads_io.project_filename(project.name)
    if stem.endswith(sloads_io.PROJECT_SUFFIX):
        stem = stem[: -len(sloads_io.PROJECT_SUFFIX)]
    return f"{stem}_results.zip"


def _run_all(project: Project) -> Tuple[list, List[str]]:
    """Every module's result or its manifest line, in registration order."""
    results = []
    manifest: List[str] = []
    for name in registry.available():
        try:
            results.append(registry.get(name)(project))
            manifest.append(f"{name}: OK")
        except MissingInputError as exc:
            manifest.append(f"{name}: SKIPPED (missing input) -- {exc}")
        except ValueError as exc:
            manifest.append(f"{name}: FAILED (invalid input) -- {exc}")
    stamp(project, *[r.conditions for r in results])
    return results, manifest


def results_zip_members(
    project: Project,
    *,
    system: UnitSystem = UnitSystem.IMPERIAL,
    tool_version: str = "",
    generated: Optional[str] = None,
    channel: LoadChannel = LoadChannel.LIMIT,
) -> Tuple[List[BundleMember], List[str]]:
    """``(zip members, manifest lines)`` for the whole-project results zip.

    Members: the serialized project, one ``reports/<module>.txt`` and one
    ``load_cases/<module>.csv`` per module that ran, and ``MANIFEST.txt``.
    The manifest lines are also returned so the GUI can caption the outcome
    without re-opening the zip.
    """
    results, manifest = _run_all(project)
    stamp_block = csv_comment_block(
        project, tool_version=tool_version, scope="full case set",
        system=system, generated=generated or None, channel=channel)

    members: List[BundleMember] = [
        BundleMember(sloads_io.project_filename(project.name),
                     sloads_io.project_to_json(project),
                     "the project as analysed"),
    ]
    for result in results:
        # Same two calls as ``cli.py``: the text report renders at the boundary
        # itself; the CSV writer converts internally (M4-20 step 3), so both get
        # the raw results. Both take the same ``channel``, so a module's text
        # report and its CSV can never state two different bases (note 48).
        members.append(BundleMember(
            f"reports/{result.module}.txt",
            module_text_report(result.module, result.conditions,
                               channel=channel),
            "per-module text report"))
        members.append(BundleMember(
            f"load_cases/{result.module}.csv",
            sloads_io.load_cases_csv(result.conditions,
                                     header_comment=stamp_block, system=system,
                                     channel=channel),
            "per-module load-case CSV"))
    header = ["Results zip -- every registered module, run against the",
              "project in this archive. One line per module; a SKIPPED or",
              "FAILED module contributed no files.", ""]
    members.append(BundleMember(
        "MANIFEST.txt", "\n".join(header + manifest) + "\n",
        "what ran and what refused"))
    return members, manifest


def results_zip_bytes(
    project: Project,
    *,
    system: UnitSystem = UnitSystem.IMPERIAL,
    tool_version: str = "",
    generated: Optional[str] = None,
    channel: LoadChannel = LoadChannel.LIMIT,
) -> Tuple[bytes, List[str]]:
    """``(zip bytes, manifest lines)`` -- what the download button serves."""
    members, manifest = results_zip_members(
        project, system=system, tool_version=tool_version, generated=generated,
        channel=channel)
    return bundle_zip_bytes(members), manifest
