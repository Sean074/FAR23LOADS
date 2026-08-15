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

**Units (M4-20 step 5).** The block states the bundle's unit system in band, so a
forwarded file never needs its units inferred from the magnitude of its numbers.
The statement is *bundle*-wide, not per-channel: one stamp is wrapped for every
channel, and the same block lands on both the human-readable CSVs (N*m, kPa) and
the sbeam decks (N*mm, MPa), so it names both sets and says which files use
which. Pass the same ``system`` the writers were given.

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
from ..units import (
    Channel,
    UnitSystem,
    deliverable_units,
    system_name,
    units_statement,
)
from .render import ultimate_units

#: Bumped with the tool, not the schema; stamped into every channel so a stray
#: CSV can be traced back to the build that produced it.
TOOL_NAME = "sloads"

#: Errors a defensive block tolerates -- the same set the report content model
#: catches. A half-filled project must still get its methods statement.
_CALC_ERRORS = (ValueError, ZeroDivisionError, KeyError, IndexError, TypeError,
                AttributeError)

#: The standing disclaimer (SUMMARY_REPORT.md §4.6 item 9), and the **one**
#: wording of it. It used to live on the report's title page alone (review
#: **F-R3**) — a page that does not travel with a forwarded CSV, deck or
#: METHODS.txt, which are exactly the files that reach a reader who never sees
#: the cover. It now leads the statement, so it is in band on every channel, and
#: ``latex.py``'s title page quotes this constant rather than restating it (the
#: title page adds its own pointer to the methods section; the disclaimer itself
#: is this text).
STANDING_DISCLAIMER = (
    "This is an initial-concept loads analysis. It is not a certification "
    "document, not a stress report, and not a substitute for the analyst's own "
    "judgement."
)

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

#: Limitations that hold for every run, regardless of project content, as
#: ``(key, text)``. Each is phrased in engineering terms with no tracking
#: identifier: the statement is read by an analyst, and SUMMARY_REPORT.md 5
#: excludes internal development artifacts (backlog IDs, ticket references,
#: source paths) from the deliverable. The tracking IDs for these gaps stay in
#: the repository's backlog.
#:
#: **The keys are the completeness contract** (review **F-R4**, which found the
#: list was not "every open caveat"): ``tests/test_methods_stamp.py`` pins the
#: key set, so opening or closing a caveat is a visible edit in the same commit
#: rather than a silent omission. Where the caveat also travels **in band** on a
#: case or a deck, the wording is the owning module's constant, not a paraphrase
#: — a caveat that reads differently in the deck and in the controlling document
#: is two caveats. Project-dependent caveats are *not* here: they are the
#: conditional blocks below (closure fallback, assumed spars, assumed tail
#: planforms), which state themselves only when they apply.
def _standing_limitations() -> tuple:
    """``((key, text), ...)`` — deferred so the owning modules import lazily."""
    from ..export.sbeam_bridge import CENTERLINE_CLAMP_NOTE
    from ..modules.balance import AILERON_COUPLE_NOTE, LATERAL_AERO_NOTE
    from ..modules.one_engine_out import PROPELLER_ONLY_NOTE

    return (
        ("control-surface-distributions",
         "Control-surface distributions are the *standard simplified* forms (not "
         "a measured or CFD chordwise distribution)."),
        ("export-case-filter",
         "Wing and control-surface exports carry the full case set even when a "
         "governing-set filter is applied elsewhere: their case identities are "
         "minted separately from the governing set, so the filter cannot reach "
         "them."),
        ("flight-only-body-deck",
         "The fuselage deck is FLIGHT-ONLY. No ground-case distributed fuselage "
         "loads: gear reactions are point reactions, not a distributed ground "
         "condition, and no ground case is assembled into a balanced free-free "
         "case. A ground-critical structure is not covered by this deliverable."),
        ("pressurization",
         "Pressurization is OUT OF SCOPE for this tool — a permanent exclusion, "
         "not a gap awaiting work. No cabin differential-pressure case (14 CFR "
         "23.365 / 25.365) is computed, and no pressure load is combined with any "
         "flight or ground case. A pressurized fuselage must have that assessment "
         "from another source, and the loads in this deliverable must not be read "
         "as the complete set for one. (The unrelated `pressurized` flag on the "
         "weight estimate is a structural-weight allowance in the WTESTIMA "
         "regression, not a load case.)"),
        ("lateral-aero",
         "Lateral aerodynamics: " + LATERAL_AERO_NOTE + "."),
        ("engine-failure-propeller-only",
         "Engine failure: " + PROPELLER_ONLY_NOTE[0].upper() + PROPELLER_ONLY_NOTE[1:]
         + "."),
        ("aileron-couple",
         "The aileron rolling moment (23.349) is applied as a lumped free couple "
         "at the wing aerodynamic centre: " + AILERON_COUPLE_NOTE + "."),
        # The deck says the same sentence after a "CAVEAT:" lead-in; here it opens
        # a bullet, so only its first letter differs.
        ("centerline-clamp",
         CENTERLINE_CLAMP_NOTE[0].upper() + CENTERLINE_CLAMP_NOTE[1:]),
    )


def _ult_markers(system: UnitSystem) -> str:
    """The ``-ULT`` markers a bundle in ``system`` can actually contain.

    Derived from the unit sets rather than listed by hand, so it cannot fall out
    of step with what the writers emit -- the hard-coded list this replaced still
    named the pre-M4-20 set and would have advertised markers no file carried.
    Both channels contribute: in SI the solver deck adds ``Nmm-ULT``/``MPa-ULT``
    to the human channel's ``Nm-ULT``/``kPa-ULT``.
    """
    seen = {}  # ordered set
    for channel in (Channel.HUMAN, Channel.SOLVER):
        u = deliverable_units(system, channel)
        for dim in (u.force, u.torque, u.moment, u.pressure):
            seen[ultimate_units(dim.label)] = None
    return ", ".join(seen)


def _units_block(system: UnitSystem) -> List[str]:
    """The bundle's UNITS statement -- one system, and the channels it splits into.

    This is bundle-wide prose, not a per-file line: one stamp is wrapped for every
    channel (decision G8-3), and the Export page puts the *same* block on the
    human load-case CSVs and on the sbeam CSVs/decks. A channel-specific statement
    would therefore be wrong on half the files it lands in, so the statement names
    both sets and says which files use which.
    """
    human = deliverable_units(system, Channel.HUMAN)
    solver = deliverable_units(system, Channel.SOLVER)
    carve_out = (
        "Airspeed is KEAS and altitude is ft in both systems (aviation standard, "
        "never converted)."
    )
    def dims(u):
        return (u.force, u.length, u.moment, u.pressure)

    if dims(human) == dims(solver):
        # Imperial: one set does both jobs, so do not imply a split that isn't there.
        return [f"UNITS: {units_statement(human)} throughout. {carve_out}"]
    def listed(u):
        # Just the units -- the system is already named once, at the front.
        return f"{u.force.label}, {u.length.label}, {u.moment.label}, {u.pressure.label}"

    return [
        f"UNITS: {system_name(system)}. Human-readable deliverables (report, "
        f"load-case CSVs, workbook) are in {listed(human)}; the sbeam "
        f"solver decks and their span CSVs are in {listed(solver)} -- a "
        "deck whose GRID coordinates are mm and whose FORCE cards are N is only "
        "correct when its MOMENT cards are N*mm and its stresses MPa. "
        + carve_out,
    ]


def _safety_factor_block(project: Project) -> List[str]:
    """The governing-table override declaration (M4-8 / G-11), or nothing.

    Silent when the table is the regulation's own values — which is the shipped
    state, and the reason this block cannot make an unmodified bundle differ by a
    single byte. It speaks only when there is a deviation to declare.
    """
    from ..safety_factors import GoverningTable

    table = GoverningTable.for_project(project)
    if not table.has_overrides:
        return []
    out = ["SAFETY FACTOR OVERRIDES: the governing safety-factor table has been "
           "edited for this project. The factors below are NOT the values 14 CFR "
           "23.303/25.303 derives, and every ULTIMATE load delivered under them "
           "reflects the override, not the regulation."]
    for row in table.overrides:
        risk = (" *** BELOW THE REGULATION — CERTIFICATION RISK ***"
                if row.below_regulation else "")
        out.append(f"  - {row.label} ({row.far_reference}): SF = {row.factor:g} "
                   f"(regulation derives {row.derived_factor:g}).{risk} "
                   f"Basis: {row.basis or '(none stated)'}")
    out.append("")
    return out


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


#: Component key -> the name the deliverable calls it. The planform block below
#: reads this rather than printing ``htail``, because the statement is read by an
#: analyst, not by the code that produced it.
_TAIL_LABELS = {"htail": "Horizontal tail", "vtail": "Vertical tail"}


def _tail_planform_block(project: Project) -> List[str]:
    """The ASSUMED-planform caveat, per surface, only where it is assumed.

    ``tail_geometry.resolve_tail_planform`` derives a **rectangular** planform
    from the area/span scalars whenever ``geometry.surfaces`` carries no entry for
    the surface, and marks it ``assumed``. That marker reached the page, the CSV
    and the tail-span result and stopped there, so the report — the controlling
    document — described a distribution as if the planform had been entered
    (review **F-R4**). Resolved from the project's own inputs rather than from a
    persisted result, so a headless bundle states it too.
    """
    from ..tail_geometry import resolve_tail_planform

    out: List[str] = []
    for component, label in _TAIL_LABELS.items():
        try:
            planform = resolve_tail_planform(project, component)
        except _CALC_ERRORS:
            # A half-filled project must still produce its statement -- the
            # methods block is how an analyst finds the gaps (SUMMARY_REPORT 3.4).
            continue
        if planform is not None and planform.assumed:
            out.append(
                f"  {label} planform ASSUMED: derived as a rectangle from the "
                f"area and span scalars (no '{component}' entry in the geometry "
                "surfaces). A tapered surface carries its load further inboard, "
                "so root bending here is conservative but the station-by-station "
                "distribution is not the surface's own."
            )
    return out


def methods_statement(
    project: Project,
    *,
    generated: Optional[str] = None,
    tool_version: str = "",
    scope: str = "",
    deselected_case_ids: Optional[List[str]] = None,
    system: UnitSystem = UnitSystem.IMPERIAL,
) -> str:
    """The full methods & limitations statement for ``project``.

    ``generated`` is the caller's timestamp string (omitted when ``None`` -- see
    the module docstring on determinism). ``scope`` describes what this export
    contains ("full case set" / "governing case set"); ``deselected_case_ids``
    lists any case an opt-out filter removed, because an analyst must never
    silently receive a filtered set.

    ``system`` (M4-20 step 5) is the system the *bundle* was written in, and it
    must be the same value the writers were given -- this block is the in-band
    statement that makes a forwarded file self-describing, so a stamp that
    disagrees with its own numbers is worse than no stamp at all. It is the
    bundle's system, not a channel's: see :func:`_units_block`.
    """
    L: List[str] = []
    L.append("METHODS AND LIMITATIONS")
    L.append("")

    # 0. Standing disclaimer ------------------------------------------------- #
    # SUMMARY_REPORT.md 4.6 item 9. Stated first rather than last: it governs how
    # much weight everything below can bear, and a reader who skims only the head
    # of a stamped CSV or deck must still meet it (review F-R3).
    L.append(f"STATUS: {STANDING_DISCLAIMER}")
    L.append("")

    # 1. Basis --------------------------------------------------------------- #
    L.append(
        f"BASIS: All loads reported here are ULTIMATE (ultimate = limit x safety "
        f"factor). Every case states its own safety factor in an 'SF' column or an "
        f"'SF=' marker; the default is {ULTIMATE_FACTOR} per 14 CFR 23.303 "
        f"(25.303 for Part 25). Load quantities carry a '-ULT' unit marker "
        f"({_ult_markers(system)}). Load factors (n, Nz) are limit and "
        f"dimensionless, and geometry, weights, inertias, areas, speeds and angles "
        f"are never scaled."
    )
    L.append("")

    # 1a. Safety-factor overrides -------------------------------------------- #
    # G-11 mitigation 1: an override cannot be silent. It is stated here, in the
    # stamp every companion file and deck carries, so a reader of ANY single
    # stamped file learns that a factor is not the regulation's own -- the
    # APPROVED_CORRECTIONS precedent, where an undeclared deviation is invisible
    # to the analyst, which is the whole point of declaring it.
    L.extend(_safety_factor_block(project))

    # 1b. Units -------------------------------------------------------------- #
    L.extend(_units_block(system))
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
    L.extend(_tail_planform_block(project))
    L.extend(f"  {text}" for _, text in _standing_limitations())
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
    is forwarded on its own still states that its loads are ultimate and which
    unit system it is written in (``system=``, M4-20 step 5).
    """
    return _prefixed(methods_statement(project, **kwargs), "#")


def bdf_comment_block(project: Project, **kwargs) -> str:
    """The statement as ``$``-prefixed NASTRAN comment lines.

    ``$`` is a comment to every bulk-data parser, so this is free -- it follows
    the existing ``body_loads`` caveat precedent already stamped into decks.

    Pass the result as every sbeam BDF writer's ``header_comment`` (M4-20 step 5).
    Until then this wrapper had one caller, which built the block and never
    applied it, so the decks were the only channel in a bundle stating neither
    their basis nor their units.
    """
    return _prefixed(methods_statement(project, **kwargs), "$")


def strip_comment_lines(csv_text: str) -> str:
    """Drop the leading ``#`` block from a stamped CSV, leaving parseable text.

    The reader-side counterpart of :func:`csv_comment_block`. Any code in this
    repo that parses an exported CSV must go through this (or pandas'
    ``comment="#"``) -- G8.3 made the stamp universal, and a reader that does not
    skip it silently takes the first comment line as its header row.

    **CSV only, deliberately.** There is no ``$`` analogue for a bulk-data deck
    and there must not be one: a deck's ``$`` lines are mostly the deliverable
    itself -- the subcase map, the axis statement, the per-case residuals -- and
    the stamp is not separable from them by line prefix. A reader that wants the
    unstamped deck rebuilds it with ``header_comment=""``; a test that wants to
    check the stamp asserts the deck *ends with* its unstamped form.
    """
    # keepends: ``csv.DictWriter`` emits CRLF, and rejoining on "\n" would
    # silently rewrite every line ending in the payload it is meant to leave alone.
    return "".join(
        ln for ln in csv_text.splitlines(keepends=True)
        if not ln.lstrip().startswith("#")
    )
