"""FAR 23 Subpart C coverage matrix — what was analysed, and what was not.

The section of the summary report that tells a reviewer what is **missing**.
Every regulation the suite is capable of covering is listed statically below;
each row is then cross-checked against the ``far_reference`` values a given run
actually produced, and classified:

* ``covered``      -- at least one condition in this run cites it (with a count).
* ``not_applicable`` -- deliberately absent for *this* airplane, with the reason
  (flap conditions on an unflapped wing, turbopropeller cases on a piston single).
* ``not_analysed`` -- the suite covers it, but this run did not produce it,
  because an input slice is missing. **This is the gap list.**
* ``out_of_scope`` -- the suite does not implement it at all (water loads, jacking,
  towing, emergency-landing dynamics...). Declared, not silently omitted.

These distinctions are the whole value of the table. "Not applicable" is an
engineering conclusion about *this airplane*; "not analysed" is a gap in *this
run* that the analyst can close by supplying inputs; "out of scope" is a
permanent boundary of the tool that must be covered by other means. Collapsing
them into one "absent" bucket would bury 5 real gaps among 20 rows nobody needs
to act on, and the section would stop being read.

Provenance of the static table: `docs/10_standard/PROGRAM_SPEC.md` (per-module
FAR conditions) cross-read with the FAA User's Guide Table 2.2 module/condition
map (`reference/FAR23Loads_UserGuide.pdf`).

Pure: no I/O, no Streamlit.
"""

from __future__ import annotations

from typing import Callable, Dict, List, NamedTuple, Optional, Sequence

from ..models import Project

COVERED = "covered"
NOT_APPLICABLE = "not_applicable"
NOT_ANALYSED = "not_analysed"
OUT_OF_SCOPE = "out_of_scope"


class Regulation(NamedTuple):
    """One row of the static FAR 23 Subpart C table this suite can cover.

    ``prefixes`` are matched against the *tokens* of a run's ``far_reference``
    strings. Two things make a naive equality test wrong: modules cite at
    sub-paragraph granularity (``23.361(a)(1)``) while a row is the paragraph
    (``23.361``), and some modules cite several regulations at once
    (``flight_envelope`` emits ``"23.333/23.337/23.341/23.345/23.421"``). So a
    reference is split on ``/`` and each token is prefix-matched -- otherwise the
    four regulations after the first in a combined citation would be reported as
    gaps despite having been analysed.

    ``na_when`` marks the row *not applicable* for a given project and returns the
    reason. It is deliberately a predicate over the whole ``Project`` rather than
    a flag, because applicability is a property of the airplane, not of the run.
    """
    far: str
    title: str
    prefixes: Sequence[str]
    module: str = ""
    na_when: Optional[Callable[[Project], Optional[str]]] = None
    #: False when no module in the suite implements this regulation. Such a row can
    #: never be a *gap* for a given run -- it is a permanent boundary of the tool,
    #: and reporting it as "not analysed" would drown the real gaps.
    in_suite: bool = True


def _no_flaps(project: Project) -> Optional[str]:
    """Flap conditions do not apply to an airplane with no flap definition."""
    if project.flap_loads is not None:
        return None
    aero = project.aero_coeffs
    if aero is not None and getattr(aero, "flaps_down", None) is not None:
        return None
    speeds = project.speeds
    if speeds is not None and getattr(speeds, "vf", None):
        return None
    return "no flap definition on this airplane (no flap loads, flaps-down aero set or VF)"


def _single_engine(project: Project) -> Optional[str]:
    if len(project.engines) > 1:
        return None
    return "single-engine airplane — no one-engine-inoperative condition"


def _engine_failure_na(project: Project) -> Optional[str]:
    """23.367 needs both a second engine to fail and (per Ref 1 Ch 11) a turboprop."""
    return _single_engine(project) or _not_turboprop(project)


def _not_turboprop(project: Project) -> Optional[str]:
    if any(getattr(e, "engine_type", None) is not None
           and str(getattr(e.engine_type, "value", e.engine_type)).lower() == "turboprop"
           for e in project.engines):
        return None
    return ("no turbopropeller engine — the 23.361(a)(3) malfunction, 23.367 "
            "engine-failure and 23.371(b) gyroscopic rotor cases are "
            "turbopropeller-specific (Ref 1 Ch 11)")


#: The static table. Order is regulation order, which is also roughly the order an
#: analyst reads a loads report in.
FAR23_SUBPART_C: Sequence[Regulation] = (
    Regulation("23.301", "Loads — limit/ultimate and the 1.5 factor",
               ("23.301",), "select / net_loads"),
    Regulation("23.321", "Flight loads — general", ("23.321",), "flight_envelope"),
    Regulation("23.331", "Symmetrical flight conditions", ("23.331",), "select"),
    Regulation("23.333", "Flight envelope (manoeuvring and gust)",
               ("23.333",), "flight_envelope"),
    Regulation("23.335", "Design airspeeds (VA/VC/VD/VF)", ("23.335",), "structural_speeds"),
    Regulation("23.337", "Limit manoeuvring load factors", ("23.337",), "structural_speeds"),
    Regulation("23.341", "Gust load factors", ("23.341",), "flight_envelope"),
    Regulation("23.345", "High-lift (flap) conditions", ("23.345",), "flight_envelope / flap",
               na_when=_no_flaps),
    Regulation("23.347", "Unsymmetrical flight conditions", ("23.347",), "select"),
    Regulation("23.349", "Rolling conditions", ("23.349",), "select / aileron"),
    Regulation("23.351", "Yawing conditions", ("23.351",), "select"),
    Regulation("23.361", "Engine torque", ("23.361",), "engine"),
    Regulation("23.363", "Side load on engine mount", ("23.363",), "engine"),
    Regulation("23.367", "Unsymmetrical loads due to engine failure",
               ("23.367",), "engine / one_engine_out", na_when=_engine_failure_na),
    Regulation("23.371", "Gyroscopic and aerodynamic loads", ("23.371",), "engine",
               na_when=_not_turboprop),
    Regulation("23.373", "Speed control devices", ("23.373",), "", in_suite=False),
    Regulation("23.391", "Control-surface loads — general", ("23.391",), "taildist"),
    Regulation("23.393", "Loads parallel to hinge line", ("23.393",), "taildist"),
    Regulation("23.395", "Control-system loads", ("23.395",), "", in_suite=False),
    Regulation("23.397", "Limit control forces and torques", ("23.397",), "", in_suite=False),
    Regulation("23.399", "Dual-control system", ("23.399",), "", in_suite=False),
    Regulation("23.405", "Secondary control system", ("23.405",), "", in_suite=False),
    Regulation("23.407", "Trim-tab effects", ("23.407",), "tab"),
    Regulation("23.409", "Tabs", ("23.409",), "tab"),
    Regulation("23.415", "Ground gust conditions", ("23.415",), "", in_suite=False),
    Regulation("23.421", "Balancing loads (horizontal tail)", ("23.421",), "select / balloads"),
    Regulation("23.423", "Manoeuvring loads (horizontal tail)", ("23.423",), "select"),
    Regulation("23.425", "Gust loads (horizontal tail)", ("23.425",), "select"),
    Regulation("23.427", "Unsymmetrical loads (horizontal tail)", ("23.427",), "select"),
    Regulation("23.441", "Manoeuvring loads (vertical tail)", ("23.441",), "select"),
    Regulation("23.443", "Gust loads (vertical tail)", ("23.443",), "select"),
    Regulation("23.445", "Outboard fins / winglets", ("23.445",), "", in_suite=False),
    Regulation("23.455", "Ailerons", ("23.455",), "aileron"),
    Regulation("23.457", "Wing flaps", ("23.457",), "flap", na_when=_no_flaps),
    Regulation("23.459", "Special devices", ("23.459",), "", in_suite=False),
    Regulation("23.471", "Ground loads — general", ("23.471",), "landing"),
    Regulation("23.473", "Ground load conditions and assumptions", ("23.473",), "landing"),
    Regulation("23.477", "Landing gear arrangement", ("23.477",), "landing"),
    Regulation("23.479", "Level landing conditions", ("23.479",), "landing"),
    Regulation("23.481", "Tail-down landing conditions", ("23.481",), "landing"),
    Regulation("23.483", "One-wheel landing conditions", ("23.483",), "landing"),
    Regulation("23.485", "Side load conditions", ("23.485",), "landing"),
    Regulation("23.493", "Braked roll conditions", ("23.493",), "landing"),
    Regulation("23.497", "Supplementary conditions for tail wheels", ("23.497",), "", in_suite=False),
    Regulation("23.499", "Supplementary conditions for nose wheels", ("23.499",), "landing"),
    Regulation("23.505", "Supplementary conditions for skiplanes", ("23.505",), "", in_suite=False),
    Regulation("23.507", "Jacking loads", ("23.507",), "", in_suite=False),
    Regulation("23.509", "Towing loads", ("23.509",), "", in_suite=False),
    Regulation("23.511", "Ground load — unsymmetrical on multiple-wheel units",
               ("23.511",), "", in_suite=False),
    Regulation("23.521", "Water loads", ("23.521",), "", in_suite=False),
    Regulation("23.561", "Emergency landing conditions — general", ("23.561",), "", in_suite=False),
    Regulation("23.562", "Emergency landing dynamic conditions", ("23.562",), "", in_suite=False),
)


class CoverageRow(NamedTuple):
    """One classified regulation, ready to render."""
    far: str
    title: str
    module: str
    status: str        # COVERED | NOT_APPLICABLE | NOT_ANALYSED
    case_count: int
    reason: str = ""

    @property
    def is_gap(self) -> bool:
        """True for the rows a reviewer must look at: covered by the suite, absent here."""
        return self.status == NOT_ANALYSED


def _counts_by_prefix(far_references: Sequence[str]) -> Dict[str, int]:
    """How many produced conditions cite each regulation prefix."""
    out: Dict[str, int] = {}
    for ref in far_references:
        if not ref:
            continue
        tokens = [t.strip() for t in str(ref).split("/") if t.strip()]
        for reg in FAR23_SUBPART_C:
            if any(t.startswith(pfx) for t in tokens for pfx in reg.prefixes):
                out[reg.far] = out.get(reg.far, 0) + 1
    return out


def coverage_matrix(project: Project, far_references: Sequence[str]) -> List[CoverageRow]:
    """Classify every regulation in the static table against one run.

    ``far_references`` is every ``far_reference`` the run produced (duplicates
    included -- the count is reported). A regulation is *covered* when any of them
    starts with one of its prefixes; otherwise the row's ``na_when`` predicate
    decides between *not applicable* (with a reason) and *not analysed*.
    """
    counts = _counts_by_prefix(far_references)
    rows: List[CoverageRow] = []
    for reg in FAR23_SUBPART_C:
        n = counts.get(reg.far, 0)
        if n:
            rows.append(CoverageRow(reg.far, reg.title, reg.module, COVERED, n))
            continue
        if not reg.in_suite:
            rows.append(CoverageRow(
                reg.far, reg.title, reg.module, OUT_OF_SCOPE, 0,
                "not implemented by this tool — cover by other means",
            ))
            continue
        reason = reg.na_when(project) if reg.na_when is not None else None
        if reason:
            rows.append(CoverageRow(reg.far, reg.title, reg.module, NOT_APPLICABLE, 0, reason))
        else:
            rows.append(CoverageRow(
                reg.far, reg.title, reg.module, NOT_ANALYSED, 0,
                f"the {reg.module} module covers this, but this run produced no "
                "condition citing it — check its inputs are present",
            ))
    return rows


def coverage_summary(rows: Sequence[CoverageRow]) -> Dict[str, int]:
    """``{status: count}`` for the section's one-line headline."""
    out = {COVERED: 0, NOT_APPLICABLE: 0, NOT_ANALYSED: 0, OUT_OF_SCOPE: 0}
    for r in rows:
        out[r.status] = out.get(r.status, 0) + 1
    return out
