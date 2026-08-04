"""The methods & limitations statement — one source, every export channel.

A loads deliverable that leaves this tool must carry its own basis. A CSV of
span loads forwarded to a stress engineer, a BDF handed to sbeam, a PDF filed in
a design review — each one has to say, *in band*, that the numbers are ULTIMATE,
what category they were computed under, how the tool is verified, and what it
does not do. An on-page caption does not travel with a downloaded file.

So the statement is built **once**, here, and wrapped for each channel
(decision G8-3):

* :func:`methods_statement` -- the full prose block (report §5, ``METHODS.txt``,
  the workbook's *Methods* sheet).
* :func:`csv_comment_block` -- the same, ``#``-prefixed, for a CSV header.
* :func:`bdf_comment_block` -- the same, ``$``-prefixed, for a NASTRAN deck.

**Determinism.** Nothing here reads the clock. ``generated`` is a caller-supplied
string, omitted when ``None`` -- the GUI passes one, the tests do not. Two runs
of the same project must produce byte-identical output, or the ``.tex`` diff
between two revisions becomes unreadable and the tests turn flaky.

Pure: no I/O, no Streamlit. See ``docs/30_future/05_step_g8_summary_report_plan.md``
§5 for the content specification this implements.
"""

from __future__ import annotations

from typing import List, Optional

from ..applicability import far23_applicability
from ..constants import ULTIMATE_FACTOR
from ..models import SCHEMA_VERSION, Project

#: Bumped with the tool, not the schema; stamped into every channel so a stray
#: CSV can be traced back to the build that produced it.
TOOL_NAME = "sloads"

#: The three approved deviations from McMaster's manual, with their citations.
#: The authoritative register is ``docs/20_theory/02_approved_corrections.md``;
#: this is its one-line-per-entry export form. Keep the two in step -- a
#: correction that is not declared here is invisible to the analyst reading the
#: deliverable, which is the whole point of declaring it.
APPROVED_CORRECTIONS = (
    ("23.361(a)(1)", "Takeoff-torque factor: the mean-torque factor is applied to the "
                     "takeoff case too, per AC 23-19A / Amdt 23-45; the manual prints "
                     "the pre-amendment unfactored value."),
    ("23.361(a)(3)", "Turboprop-malfunction case uses the mean-torque factor rather "
                     "than the manual's unfactored torque."),
    ("23.427(a)", "Unsymmetrical-tail search restores the full SELECT.BAS candidate "
                  "set, including the two conditions the printed listing omits."),
)

#: Limitations that hold for every run, regardless of project content.
_STANDING_LIMITATIONS = (
    "Control-surface distributions are the *standard simplified* forms (not a "
    "measured or CFD chordwise distribution).",
    "Wing and control-surface exports carry the full case set even when a "
    "governing-set filter is applied elsewhere (case-identity gap, backlog M4-2).",
    "No ground-case distributed fuselage loads: gear reactions are point "
    "reactions, not a distributed ground condition (backlog M4-6).",
    "No pressurization load cases.",
)


def _category_block(project: Project) -> List[str]:
    """Category, or the concept-mode caveat with its specific exceedances."""
    speeds = project.speeds
    category = (speeds.category if speeds is not None else "") or "(not set)"
    if not project.is_concept:
        return [
            f"CATEGORY: FAR 23 category '{category}'. The airplane is inside the "
            "certificated band this replication is calibrated to."
        ]

    out = [
        "CATEGORY: CONCEPT (C) -- UNVERIFIED EXTRAPOLATION. These loads are a "
        "concept-mode extrapolation above the FAR 23 calibration band, not a "
        "certified analysis, and the load factors are user-declared rather than "
        "capped by 14 CFR 23.337.",
    ]
    exceedances = far23_applicability(project)
    if exceedances:
        out.append("  FAR 23 applicability exceeded on:")
        out.extend(
            f"    - {e.label}: {e.value:,.0f} exceeds the limit of {e.limit:,.0f}"
            for e in exceedances
        )
    return out


def _closure_block(project: Project) -> List[str]:
    """The fuselage closure caveat, verbatim, only when a case actually fell back.

    Imported lazily: :mod:`sloads.modules.body_loads` imports the flight envelope,
    and this module is imported from ``sloads.report``'s package init.
    """
    loads = project.loads
    body = getattr(loads, "body_net", None) if loads is not None else None
    if not body:
        return []
    artifacts = [b for b in body if getattr(b, "closure_artifact", False)]
    if not artifacts:
        return [
            "  Fuselage moment closure: the unbalanced moment is reacted at the "
            "wing front/rear spar attachments (Ref 1 Ch 15 p103); both the vertical "
            "residual and the terminal Myy close."
        ]
    from ..modules.body_loads import CLOSURE_ARTIFACT_CAVEAT

    return [
        f"  Fuselage moment closure: {len(artifacts)} case(s) used the fallback path.",
        f"    {CLOSURE_ARTIFACT_CAVEAT}",
    ]


def _spar_block(project: Project) -> List[str]:
    loads = project.loads
    body = getattr(loads, "body_net", None) if loads is not None else None
    if body and any(getattr(b, "spars_assumed", False) for b in body):
        return [
            "  Wing spar stations were ASSUMED (front/rear spar chord fractions not "
            "entered); the carry-through reaction location is a default, not an input."
        ]
    return []


def methods_statement(
    project: Project,
    *,
    generated: Optional[str] = None,
    tool_version: str = "",
    scope: str = "",
    deselected_case_ids: Optional[List[str]] = None,
) -> str:
    """The full methods & limitations statement for ``project``.

    ``generated`` is the caller's timestamp string (omitted when ``None`` -- see
    the module docstring on determinism). ``scope`` describes what this export
    contains ("full case set" / "governing case set"); ``deselected_case_ids``
    lists any case an opt-out filter removed, because an analyst must never
    silently receive a filtered set.
    """
    L: List[str] = []
    L.append("METHODS AND LIMITATIONS")
    L.append("")

    # 1. Basis --------------------------------------------------------------- #
    L.append(
        f"BASIS: All loads reported here are ULTIMATE (ultimate = limit x safety "
        f"factor). Every case states its own safety factor in an 'SF' column or an "
        f"'SF=' marker; the default is {ULTIMATE_FACTOR} per 14 CFR 23.303 "
        f"(25.303 for Part 25). Load quantities carry a '-ULT' unit marker "
        f"(lbs-ULT, ft-lb-ULT, N-ULT, Nm-ULT). Load factors (n, Nz) are limit and "
        f"dimensionless, and geometry, weights, inertias, areas, speeds and angles "
        f"are never scaled."
    )
    L.append("")

    # 2. Category ------------------------------------------------------------ #
    L.extend(_category_block(project))
    L.append("")

    # 3. Verification status ------------------------------------------------- #
    L.append(
        "VERIFICATION: The FAR 23 general-aviation path is oracle-locked to the "
        "printed Appendix A example of Reference 1 (McMaster, FAR 23 LOADS) within "
        "+/-0.1%. Appendix B (the 10-place twin turboprop) is NOT bundled with the "
        "reference, so twin-only and turbopropeller-only cases are CLOSURE-LOCKED, "
        "NOT ORACLE-LOCKED: they are validated by sub-formula exactness against the "
        "original .BAS source plus physics/integration closure. Treat twin-specific "
        "results accordingly."
    )
    L.append("")

    # 4. Modernized math ----------------------------------------------------- #
    L.append(
        "MATH: Equations are modernized (math.pi and clean algebra) rather than "
        "reproducing the source program's 3.1416 literal, so agreement with the "
        "manual's printed figures is tolerance-based (+/-0.1%), not exact."
    )
    L.append("")

    # 5. Approved corrections ------------------------------------------------ #
    L.append("APPROVED CORRECTIONS (deliberate, documented deviations from the source manual):")
    L.extend(f"  {far}: {text}" for far, text in APPROVED_CORRECTIONS)
    L.append("")

    # 6. Known limitations --------------------------------------------------- #
    L.append("KNOWN LIMITATIONS:")
    L.extend(_closure_block(project))
    L.extend(_spar_block(project))
    L.extend(f"  {item}" for item in _STANDING_LIMITATIONS)
    L.append("")

    # 7. Scope of this export ------------------------------------------------ #
    if scope or deselected_case_ids:
        L.append(f"SCOPE OF THIS EXPORT: {scope or 'full case set'}.")
        if deselected_case_ids:
            L.append(
                "  DESELECTED cases (present in the analysis, EXCLUDED from this "
                f"export): {', '.join(deselected_case_ids)}"
            )
        L.append("")

    # 8. Provenance ---------------------------------------------------------- #
    L.append("PROVENANCE:")
    L.append(f"  Tool: {TOOL_NAME} {tool_version}".rstrip())
    # The tool's current schema, not project.schema_version: io.load_project
    # migrates an older file forward in memory, so the data in this export
    # conforms to SCHEMA_VERSION regardless of what the file on disk said.
    L.append(f"  Project schema version: {SCHEMA_VERSION}")
    if project.schema_version != SCHEMA_VERSION:
        L.append(f"  (loaded from a v{project.schema_version} file and migrated forward)")
    if project.name:
        L.append(f"  Project: {project.name}")
    for label, value in (
        ("Engineer", project.engineer),
        ("Date", project.date),
        ("Revision", getattr(project, "revision", "")),
        ("Checked by", getattr(project, "checked_by", "")),
        ("Approved by", getattr(project, "approved_by", "")),
    ):
        if value:
            L.append(f"  {label}: {value}")
    if generated:
        L.append(f"  Generated: {generated}")

    return "\n".join(L).rstrip() + "\n"


def _prefixed(text: str, marker: str) -> str:
    """Prefix every line with ``marker``, keeping blank lines as a bare marker."""
    lines = text.rstrip("\n").split("\n")
    return "\n".join(f"{marker} {ln}".rstrip() for ln in lines) + "\n"


def csv_comment_block(project: Project, **kwargs) -> str:
    """The statement as ``#``-prefixed CSV header lines.

    A consumer must be told to skip them (``pandas.read_csv(..., comment="#")``);
    every in-repo reader was audited at G8.3. The trade is deliberate: a CSV that
    is forwarded on its own still states that its loads are ultimate.
    """
    return _prefixed(methods_statement(project, **kwargs), "#")


def bdf_comment_block(project: Project, **kwargs) -> str:
    """The statement as ``$``-prefixed NASTRAN comment lines.

    ``$`` is a comment to every bulk-data parser, so this is free -- it follows
    the existing ``body_loads`` caveat precedent already stamped into decks.
    """
    return _prefixed(methods_statement(project, **kwargs), "$")


def strip_comment_lines(csv_text: str) -> str:
    """Drop the leading ``#`` block from a stamped CSV, leaving parseable text.

    The reader-side counterpart of :func:`csv_comment_block`. Any code in this
    repo that parses an exported CSV must go through this (or pandas'
    ``comment="#"``) -- G8.3 made the stamp universal, and a reader that does not
    skip it silently takes the first comment line as its header row.
    """
    # keepends: ``csv.DictWriter`` emits CRLF, and rejoining on "\n" would
    # silently rewrite every line ending in the payload it is meant to leave alone.
    return "".join(
        ln for ln in csv_text.splitlines(keepends=True)
        if not ln.lstrip().startswith("#")
    )
