"""The **governing safety-factor table** — the one authority for every case's factor.

Decision **G-11** (`docs/30_future/18_step10_ground_cases_plan.md`), the re-shaped
form of backlog item **M4-8**. Before this module the factor was decided ad hoc:
``ConditionResult.safety_factor`` defaulted to ``constants.ULTIMATE_FACTOR`` and
exactly one producer (:mod:`sloads.modules.one_engine_out`) overrode it, with two
silent ``getattr(item, "safety_factor", ULTIMATE_FACTOR)`` fallbacks in
``report/content.py`` reading 1.5 for a factorless case and leaving no trace.

**What the table is.** One row per **load class / condition family**, not per case
(CLAUDE.md practice 3: a cross-cutting convention gets a single-source code owner
plus a drift-guard test). Each row states its factor, its regulatory **basis**, and
its :class:`RowStatus` — derived, overridden or defaulted. A case maps to a family
through :func:`classify`, so **no case can be forgotten by omitting a row**: every
per-case factor, including the report case index's ``SF`` column and the ``SF=``
marker on a bulk-data deck, is a derived view of one of these rows.

**Where the family boundaries come from.** Not invented here — they are 14 CFR
Subpart C's own section groupings (Flight Loads, Control Surface and System Loads,
Ground Loads, ...), so the table's granularity is the regulation's granularity.
Parts 23 and 25 number Subpart C in parallel, so one range table serves both; the
part is carried in the row's basis text, not in the range.

**Why an override cannot move an oracle.** The factor is applied only at the
render/export boundary — the calc stays LIMIT — so no row of this table, however
edited, can shift an Appendix-A figure. What it *can* move is the deliverable, and
that is why an override is never silent: see :class:`GoverningTable` and the four
mitigations recorded with G-11.

Sources: ``reference/14CFR_factor_of_safety.md`` (§ 25.303 / historically § 23.303
— "a factor of safety of 1.5 must be applied to the prescribed limit load");
``reference/ug.txt`` for the Subpart C section text quoted in the row bases.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .constants import ULTIMATE_FACTOR

__all__ = [
    "LoadClass", "RowStatus", "Family", "Row", "Resolution", "GoverningTable",
    "FAMILIES", "family", "classify", "DERIVED_FACTOR", "DEFAULT_FAMILY",
    "table_for", "stamp",
]


# --------------------------------------------------------------------------- #
# Layer 1: the regulation-fixed classification
# --------------------------------------------------------------------------- #
class LoadClass:
    """How the governing regulation *classifies* the prescribed load.

    This — not the speed, not the module — decides the factor: a LIMIT load is
    multiplied by 1.5 to reach ultimate; a load the regulation already prescribes
    as ULTIMATE is delivered as computed (14 CFR 23.303 / 25.303).
    """

    LIMIT = "LIMIT"
    ULTIMATE = "ULTIMATE"


#: Layer 1 of M4-8: class -> factor. Subsumes :data:`constants.ULTIMATE_FACTOR`,
#: which stays as the carrier's dataclass default so a result built outside the
#: table is still conservative rather than unfactored.
DERIVED_FACTOR = {
    LoadClass.LIMIT: ULTIMATE_FACTOR,
    LoadClass.ULTIMATE: 1.0,
}


class RowStatus:
    """Provenance of a row's factor — stated in the table, the report and the stamp.

    ``DERIVED`` is the regulation's own value. ``OVERRIDE`` is a user-supplied
    value replacing it (G-11 makes every row editable, including the
    regulation-fixed ones, on the precedent of ``APPROVED_CORRECTIONS``: a
    deviation that is not declared is invisible to the analyst, which is the whole
    point of declaring it). ``DEFAULTED`` means a case reached the boundary that
    this table could not classify — it is factored at 1.5 and **flagged**, never
    silently accepted, and a test asserts zero defaulted rows on every shipped
    fixture so the flag cannot normalise into background noise.
    """

    DERIVED = "derived"
    OVERRIDE = "override"
    DEFAULTED = "defaulted"


@dataclass(frozen=True)
class Family:
    """One condition family: the unit the table resolves a factor for."""

    key: str
    label: str
    far_reference: str
    load_class: str
    basis: str

    @property
    def derived_factor(self) -> float:
        return DERIVED_FACTOR[self.load_class]


_LIMIT_BASIS = ("14 CFR 23.303 / 25.303 — a factor of safety of 1.5 applied to "
                "the prescribed limit load")

#: The governing table's rows, in regulation order. **Adding a produced FAR
#: reference without a family here is a red build, not a footnote** — the
#: unclassified case shows up as :data:`RowStatus.DEFAULTED`.
FAMILIES: Tuple[Family, ...] = (
    Family("general", "General structural loads", "23.301–23.307",
           LoadClass.LIMIT,
           "Strength requirements are specified in terms of limit and ultimate "
           "loads (23.301(a)); " + _LIMIT_BASIS),
    Family("flight", "Flight loads — manoeuvre, gust, engine torque and gyroscopic",
           "23.321–23.371", LoadClass.LIMIT,
           "Flight load factors represent the ratio of an aerodynamic force to "
           "the weight and are prescribed as limit values (23.321(a)); "
           + _LIMIT_BASIS),
    Family("engine_ultimate", "Sudden engine stoppage — prescribed ultimate",
           "23.367(a)(2)", LoadClass.ULTIMATE,
           "23.367(a)(2) prescribes the sudden-stoppage torque case as an "
           "ULTIMATE load, so no further factor is applied (SF = 1.0)."),
    Family("control_system", "Control surface and system loads", "23.391–23.459",
           LoadClass.LIMIT,
           "The control surface loads of 23.391–23.459, including the "
           "horizontal- and vertical-surface manoeuvre and gust conditions, are "
           "limit loads; " + _LIMIT_BASIS),
    Family("ground", "Ground and landing loads", "23.471–23.511", LoadClass.LIMIT,
           "\"The limit ground loads specified in this subpart …\" (23.471); every "
           "embedded multiplier — 1.33 and 0.83 (23.485), 0.8 (23.493), 2.25 "
           "(23.499) — is prescribed as a limit quantity, so " + _LIMIT_BASIS),
    Family("water", "Water loads", "23.521–23.537", LoadClass.LIMIT,
           "Seaplane/float water loads are limit loads (23.521); " + _LIMIT_BASIS),
    Family("emergency", "Emergency landing conditions — prescribed ultimate",
           "23.561–23.562", LoadClass.ULTIMATE,
           "23.561(b) prescribes ULTIMATE inertia load factors for the emergency "
           "landing conditions, so no further factor is applied (SF = 1.0)."),
    Family("reference_data",
           "Weight, CG and configuration reference conditions", "23.21–23.29",
           LoadClass.LIMIT,
           "Not a load case: these conditions carry weights, centres of gravity "
           "and configuration data, and the factor is never applied to them. The "
           "row exists so a reference condition is classified rather than "
           "defaulted; its factor is the LIMIT default and is inert."),
)

_BY_KEY: Dict[str, Family] = {f.key: f for f in FAMILIES}

#: The family an unclassifiable case falls back to, flagged as
#: :data:`RowStatus.DEFAULTED`.
DEFAULT_FAMILY = "general"


def family(key: str) -> Family:
    """The :class:`Family` for ``key``, or ``KeyError`` naming the valid keys."""
    try:
        return _BY_KEY[key]
    except KeyError:
        raise KeyError(f"Unknown safety-factor family {key!r}; the governing table "
                       f"has: {', '.join(_BY_KEY)}") from None


# --------------------------------------------------------------------------- #
# Classification: a case -> its family
# --------------------------------------------------------------------------- #
#: Exact-reference rows matched **before** the section ranges, because they sit
#: inside a range whose class they do not share (23.367(a)(2) is an ultimate case
#: inside the limit flight-loads range).
_EXACT: Dict[str, str] = {
    "23.367(a)(2)": "engine_ultimate",
    "25.367(a)(2)": "engine_ultimate",
}

#: ``(low, high_exclusive) -> family key`` over the Subpart C section number,
#: shared by Parts 23 and 25 (their Subpart C numbering runs in parallel).
_RANGES: Tuple[Tuple[Tuple[int, int], str], ...] = (
    ((21, 30), "reference_data"),
    ((301, 308), "general"),
    ((321, 372), "flight"),
    ((391, 460), "control_system"),
    ((471, 512), "ground"),
    ((521, 538), "water"),
    ((561, 563), "emergency"),
)

#: ``23.485``, ``25.361(a)(3)(i)`` -> part 23/25 and section 485/361. A reference
#: may name several sections (``"23.333/23.337/23.341"``); every one of them is
#: classified and they must agree on a factor (see :func:`classify`).
_REF_RE = re.compile(r"\b(2[35])\.(\d{2,3})")


def _references(text: str) -> List[str]:
    """Every ``23.xxx`` / ``25.xxx`` section named in ``text``, in written order."""
    return [f"{part}.{sec}" for part, sec in _REF_RE.findall(text or "")]


def _family_of_reference(ref: str) -> Optional[str]:
    section = int(ref.split(".")[1])
    for (low, high), key in _RANGES:
        if low <= section < high:
            return key
    return None


def classify(item: Any) -> Tuple[Optional[str], str]:
    """``(family_key, far_reference)`` for one case-carrying result.

    The FAR reference is read from the result's own ``far_reference`` or, failing
    that, from its :class:`~sloads.models.results.CaseRef` — the distributed
    component results (wing/body/tail/control) carry theirs only on the case ref.

    A reference naming several sections is classified by **all** of them: the
    first is the family, and if any other resolves to a family with a *different*
    factor the case is left unclassified rather than silently taking the first —
    an ambiguity that would otherwise decide a deliverable's factor by word order.
    ``None`` means unclassified; the caller flags it as
    :data:`RowStatus.DEFAULTED`.
    """
    text = (getattr(item, "far_reference", "") or "")
    if not _REF_RE.search(text):
        ref = getattr(item, "case_ref", None)
        text = getattr(ref, "far_reference", "") or text
    for whole, key in _EXACT.items():
        # An exact row wins outright: it exists precisely because it sits inside a
        # range whose class it does not share, so the range must not out-vote it.
        if whole in text:
            return key, text
    refs = _references(text)
    if not refs:
        # No FAR section named: a configuration/geometry/weights reference
        # condition. Anything else with prose but no section is unclassified.
        return ("reference_data"
                if text.strip().lower() in ("", "configuration", "geometry")
                else None), text
    keys = [_family_of_reference(r) for r in refs]
    if any(k is None for k in keys):
        return None, text
    if len({_BY_KEY[k].derived_factor for k in keys}) > 1:
        return None, text
    return keys[0], text


# --------------------------------------------------------------------------- #
# The table itself
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Resolution:
    """One case's factor and where it came from — never a bare float."""

    factor: float
    basis: str
    status: str
    family_key: str
    far_reference: str = ""

    @property
    def is_override(self) -> bool:
        return self.status == RowStatus.OVERRIDE

    @property
    def is_defaulted(self) -> bool:
        return self.status == RowStatus.DEFAULTED


@dataclass(frozen=True)
class Row:
    """A rendered row of the governing table."""

    key: str
    label: str
    far_reference: str
    load_class: str
    factor: float
    derived_factor: float
    basis: str
    status: str

    @property
    def is_override(self) -> bool:
        return self.status == RowStatus.OVERRIDE

    @property
    def below_regulation(self) -> bool:
        """An override *under* the regulation's derived value — the case that
        carries certification risk, and the one :mod:`sloads.validation` warns on."""
        return self.is_override and self.factor < self.derived_factor


@dataclass
class GoverningTable:
    """The project's governing safety-factor table: derived rows + user overrides.

    Build with :meth:`for_project`. ``defaulted`` accumulates the FAR references
    of cases this table could not classify, so a caller can state them rather than
    discover them — an empty list is the shipped-fixture requirement.
    """

    rows: List[Row] = field(default_factory=list)
    defaulted: List[str] = field(default_factory=list)

    @classmethod
    def for_project(cls, project: Any = None) -> "GoverningTable":
        overrides: Dict[str, Any] = {}
        policy = getattr(project, "safety_factors", None)
        for ov in getattr(policy, "overrides", ()) or ():
            overrides[ov.family] = ov
        rows = []
        for fam in FAMILIES:
            ov = overrides.get(fam.key)
            if ov is None:
                rows.append(Row(fam.key, fam.label, fam.far_reference,
                                fam.load_class, fam.derived_factor,
                                fam.derived_factor, fam.basis, RowStatus.DERIVED))
            else:
                rows.append(Row(fam.key, fam.label, fam.far_reference,
                                fam.load_class, float(ov.factor),
                                fam.derived_factor, ov.basis, RowStatus.OVERRIDE))
        return cls(rows=rows)

    # -- lookups ----------------------------------------------------------- #
    def row(self, key: str) -> Row:
        for r in self.rows:
            if r.key == key:
                return r
        raise KeyError(f"Unknown safety-factor family {key!r}")

    @property
    def has_overrides(self) -> bool:
        return any(r.is_override for r in self.rows)

    @property
    def overrides(self) -> List[Row]:
        return [r for r in self.rows if r.is_override]

    def resolve(self, key: str, far_reference: str = "") -> Resolution:
        """The factor for a family key, with its basis and provenance."""
        r = self.row(key)
        return Resolution(r.factor, r.basis, r.status, r.key,
                          far_reference or r.far_reference)

    def factor_for(self, item: Any) -> Resolution:
        """The factor for one case-carrying result — the per-case derived view.

        An unclassifiable case does not raise (G-11, user decision): it takes the
        conservative ``ULTIMATE_FACTOR`` and is returned as
        :data:`RowStatus.DEFAULTED`, and its reference is recorded in
        :attr:`defaulted` so the report and the methods stamp can name it.
        """
        key, ref = classify(item)
        if key is None:
            if ref not in self.defaulted:
                self.defaulted.append(ref)
            return Resolution(ULTIMATE_FACTOR,
                              "Unclassified condition — no row of the governing "
                              "table matched this FAR reference; factored at the "
                              "conservative default and flagged.",
                              RowStatus.DEFAULTED, DEFAULT_FAMILY, ref)
        return self.resolve(key, ref)

    def stamp(self, items: Sequence[Any]) -> "GoverningTable":
        """Write the table's factor onto each result's ``safety_factor`` carrier.

        The carrier stays where it is (M4-8: centralize the *policy*, not the
        carrier) — this is how an override reaches the export side, so a report
        figure and its bulk-data card can never state different factors for one
        case (the defect class review finding **F-R1** closed). Returns ``self``
        so a caller can stamp several groups in one expression.
        """
        for item in items or ():
            if hasattr(item, "safety_factor"):
                item.safety_factor = self.factor_for(item).factor
        return self


def table_for(project: Any = None) -> GoverningTable:
    """Shorthand for :meth:`GoverningTable.for_project`."""
    return GoverningTable.for_project(project)


def stamp(project: Any, *groups: Sequence[Any]) -> GoverningTable:
    """Stamp every group with ``project``'s table and return it (for its flags)."""
    table = table_for(project)
    for group in groups:
        table.stamp(group)
    return table
