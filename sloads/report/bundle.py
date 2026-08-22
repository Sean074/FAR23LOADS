"""The Export bundle's **member plan** -- the single owner of what the zip carries.

Why this is a module and not ten ``z.writestr`` calls in the Export page: the
bundle manifest (:func:`sloads.report.content._manifest_rows`, Appendix A) is
the controlling document's statement of *every file the bundle carries and on
what basis*, and until 2026-08-22 nothing compared the two. Three members had
drifted past the manifest by then -- the LRA beam model (review CR-C-1, the
F-D2 class re-opened one release later) and the summary report's own ``.tex``
and ``.pdf``, which the review's class-sweep missed.

A gate can only close that class for good if it reads **the artifact the user
receives**. So the page no longer decides the member list: it calls
:func:`bundle_members`, which is pure, Streamlit-free and importable by a test,
and every member states the manifest row that names it. The zip's namelist is
then a property of this module, and ``tests/test_bundle_manifest.py`` asserts
``{m.manifest_name} <= {manifest rows}`` on every fixture. Adding a member
without its manifest row is a test failure, not a silently unnamed file.

Manifest rows spell the project stem as ``<project>``; a real member spells it
out. :func:`manifest_name_for` is the one place that translation happens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Union

#: How a manifest row spells the project stem (``sbeam/<project>_wing_loads.bdf``).
MANIFEST_PLACEHOLDER = "<project>"

Content = Union[str, bytes]


@dataclass(frozen=True)
class BundleMember:
    """One file in the Export zip, with the manifest row that names it.

    ``manifest_name`` is carried rather than derived so that the one-row-covers-
    many case (``load_cases/<project>_<module>.csv`` names one row for every
    module CSV) is stated by the builder instead of pattern-matched by the gate.
    """

    name: str
    content: Content
    manifest_name: str


def manifest_name_for(name: str, stem: str) -> str:
    """The manifest spelling of a real zip member path."""
    return name.replace(f"{stem}_", f"{MANIFEST_PLACEHOLDER}_", 1).replace(
        f"{stem}.", f"{MANIFEST_PLACEHOLDER}.", 1)


def _member(name: str, content: Content, stem: str,
            manifest_name: Optional[str] = None) -> BundleMember:
    return BundleMember(name, content,
                        manifest_name or manifest_name_for(name, stem))


def bundle_members(
    stem: str,
    *,
    project_json: str,
    text_report: str = "",
    module_csvs: Optional[Mapping[str, str]] = None,
    case_index_csv: str = "",
    safety_factors_csv: str = "",
    gear_report_csv: str = "",
    methods: str = "",
    report_tex: str = "",
    report_pdf: Optional[bytes] = None,
    sbeam_artifacts: Optional[Mapping[str, str]] = None,
) -> List[BundleMember]:
    """Every file the Export bundle carries, in zip order.

    Empty content is omitted rather than written blank, exactly as the page did:
    a component that produced nothing contributes no member and its manifest row
    is likewise absent, so the two stay in step by construction.
    """
    members: List[BundleMember] = [
        _member(f"{stem}.json", project_json, stem),
    ]
    if text_report.strip():
        members.append(_member(f"{stem}_report.txt", text_report, stem))
    for module, csv in (module_csvs or {}).items():
        if csv:
            members.append(BundleMember(
                f"load_cases/{stem}_{module}.csv", csv,
                f"load_cases/{MANIFEST_PLACEHOLDER}_<module>.csv"))
    if case_index_csv.strip():
        members.append(_member(f"{stem}_case_index.csv", case_index_csv, stem))
    if safety_factors_csv:
        members.append(_member(f"{stem}_safety_factors.csv", safety_factors_csv, stem))
    if gear_report_csv.strip():
        members.append(_member(f"{stem}_gear_loads.csv", gear_report_csv, stem))
    # The bundle's own controlling statement -- readable without opening a CSV.
    if methods:
        members.append(BundleMember("METHODS.txt", methods, "METHODS.txt"))
    # The controlling document travels with the data it controls (Step G8): the
    # .tex always, the PDF once it has been compiled on the Export page.
    if report_tex:
        members.append(_member(f"{stem}_summary_report.tex", report_tex, stem))
        if report_pdf:
            members.append(_member(f"{stem}_summary_report.pdf", report_pdf, stem))
    for name, content in (sbeam_artifacts or {}).items():
        if content:
            members.append(_member(f"sbeam/{stem}_{name}", content, stem))
    return members


def bundle_zip_bytes(members: Sequence[BundleMember]) -> bytes:
    """The members as a deflated zip -- the bytes the download button serves."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for member in members:
            z.writestr(member.name, member.content)
    return buf.getvalue()


def manifest_names(members: Sequence[BundleMember]) -> Dict[str, str]:
    """``{manifest row name: the member that claims it}`` -- the gate's input."""
    return {m.manifest_name: m.name for m in members}


__all__ = [
    "MANIFEST_PLACEHOLDER",
    "BundleMember",
    "bundle_members",
    "bundle_zip_bytes",
    "manifest_name_for",
    "manifest_names",
]
