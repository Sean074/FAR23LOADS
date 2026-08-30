"""Provenance for the oracle technical report: the fingerprint and the anchors.

Design note 44, OR-21. Two different questions are answered by two different
things, and the report carries both:

* *Is this the same airplane?* -- the **anchors**: project name, category, design
  weight, wing area, design speeds. This is what a reader of the PDF actually
  checks, and a hex string tells them nothing.
* *Has the definition changed since this issue was authored?* -- the
  **fingerprint**, because nothing else answers it cheaply.

**Scope is the point.** The fingerprint is taken over a canonical projection of
*the inputs the oracle report consumes*, never over the project file. Hashing the
file would fire on a concept-mode field, an sloads-only field, or a re-save with
different key ordering -- a warning about a document none of them can affect. A
warning that fires on noise is ignored on signal.

That projection is not defined here: :func:`sloads.field_registry.reduce_to_oracle_inputs`
already owns it, as gate G5's mechanism (note 32, OG-13). Reusing it is what makes
G-OR-13 and G-OR-6 the *same* guarantee rather than two hand-maintained scope
lists that can drift apart -- a field the oracle GUI cannot set is returned to its
default before hashing, so it can move neither the hash nor the document.

The fingerprint is **not a signature**: there is no key, so it detects accident,
not tampering. Nor is it the record of what was analysed -- the Appendix A input
echo is that. It is the fast comparator that says *go read Appendix A, something
moved*.

Not imported by :mod:`sloads.report`'s package ``__init__``: this module reaches
``sloads.io`` and ``sloads.field_registry``, and keeping it out of the eager
import block means no cycle can form there later.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from ..models import Project

#: Version of the *definition* of the projection below.
#:
#: When a later milestone adds a field to an oracle-consumed slice, every
#: existing report's stored fingerprint goes stale through no fault of its
#: author. Bumping this lets the page say *"cannot compare -- stamped by an
#: earlier fingerprint definition"* instead of crying wolf, and the human anchors
#: still compare. A comparator with no version is one that eventually gets
#: ignored.
FINGERPRINT_VERSION = 1


#: Free-text document control, excluded from the hash (but not from the report).
#:
#: These are facts about the *paperwork*, not about the airplane: renaming the
#: engineer or correcting a typo in the description cannot move a single load.
#: Including them would make the provenance warning fire on edits that change
#: nothing the report computes -- and OR-21's own reasoning is that a warning
#: firing on noise is ignored on signal. The project name is here too, and is
#: printed as an anchor instead, where a human can see it changed.
METADATA_KEYS = frozenset({
    "name", "engineer", "date", "revision", "checked_by", "approved_by",
    "description",
})


def oracle_projection(project: Project) -> Dict[str, Any]:
    """The project reduced to what the oracle report consumes, as a plain dict.

    Both owners are borrowed rather than reimplemented:
    :func:`sloads.field_registry.reduce_to_oracle_inputs` decides *what is in
    scope*, and :func:`sloads.io.project_to_dict` decides *how it serialises*.
    A second opinion on either would be a second source of truth for a scope
    boundary that already has one.

    The one thing added on top is :data:`METADATA_KEYS`: the oracle GUI does set
    those fields, so the reducer rightly keeps them, but they are document
    control rather than airplane definition and must not move the fingerprint.
    """
    from .. import io as io_
    from ..field_registry import reduce_to_oracle_inputs

    projected = io_.project_to_dict(reduce_to_oracle_inputs(project))
    return {k: v for k, v in projected.items() if k not in METADATA_KEYS}


def fingerprint(project: Project) -> str:
    """SHA-256 over the canonical projection (OR-21).

    ``sort_keys`` and ``repr``-faithful floats: a project re-saved with different
    key ordering, or by a different JSON writer, must not read as a changed
    airplane. The hash answers "did a number move", and only that.
    """
    canonical = json.dumps(oracle_projection(project), sort_keys=True,
                           separators=(",", ":"), default=repr)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fmt(value: Optional[float], unit: str) -> str:
    if value is None:
        return "not stated"
    text = f"{value:g}"
    return f"{text} {unit}".strip()


def _wing_area_sqft(project: Project) -> Optional[float]:
    """The wing area the analysis would use, entered or resolved.

    ``speeds.wing_area_sqft`` is optional because STRSPEED resolves the planform
    when it is blank (``field_registry._speeds_wing_area``). An anchor that read
    the field alone would print "not stated" for the common case of a project
    that entered a planform instead -- the identity check would be blank exactly
    where the geometry is best defined.
    """
    entered = getattr(getattr(project, "speeds", None), "wing_area_sqft", None)
    if entered:
        return float(entered)
    from ..derived_geometry import planform_area_sqft

    surface = getattr(getattr(project, "speeds", None), "wing_surface", None) or "wing"
    try:
        return planform_area_sqft(project, surface)
    except (ValueError, ZeroDivisionError):
        # A half-entered planform is not an error here: the anchor says "not
        # stated" and the fingerprint still answers the question it exists for.
        return None


def anchors(project: Project) -> List[Tuple[str, str]]:
    """The human identity rows the title page prints beside the fingerprint.

    Computed at build time, never stored in the spec: stored text goes stale as
    soon as the project moves, which is precisely the condition these rows exist
    to reveal.

    Values are the project's own canonical Imperial (a stored project is never
    converted), and each row says its unit. Kept deliberately short -- five rows
    a reader can check against a drawing beats twenty they will skip.
    """
    speeds = project.speeds
    rows: List[Tuple[str, str]] = [
        ("Project", project.name or "unnamed"),
        ("FAR 23 category", getattr(speeds, "category", "") or "not stated"),
        ("Design weight", _fmt(getattr(speeds, "weight_lb", None), "lb")),
        # "sq ft", not "ft^2": these rows are plain text that must survive being
        # typeset, pasted into an email and printed on a fax cover -- a caret is
        # a superscript in the first and a literal in the others.
        ("Wing area", _fmt(_wing_area_sqft(project), "sq ft")),
        ("Design cruising speed VC", _fmt(getattr(speeds, "chosen_vc", None), "KEAS")),
        ("Design diving speed VD", _fmt(getattr(speeds, "chosen_vd", None), "KEAS")),
    ]
    return rows


def identity_matches(stored_fingerprint: str, stored_version: int,
                     project: Project) -> Tuple[bool, str]:
    """Compare a spec's stored stamp against ``project``: ``(ok, message)``.

    Three outcomes, and none of them refuses to build (OR-21): a project is
    legitimately revised under the same report number, and refusing would
    obstruct the normal case in order to police the rare one.

    * no stamp yet -- nothing to compare, and saying so is not a warning;
    * a stamp from an earlier :data:`FINGERPRINT_VERSION` -- *cannot* compare,
      which is a different statement from *does not match* and must not be
      dressed up as one;
    * a stamp that disagrees -- say so, name what to do about it, and build.
    """
    if not stored_fingerprint:
        return True, "No provenance stamp yet -- this report has not been baselined."
    if stored_version != FINGERPRINT_VERSION:
        return False, (
            "Cannot compare -- this report was stamped by an earlier fingerprint "
            "definition. Check the anchor values by eye instead.")
    if stored_fingerprint == fingerprint(project):
        return True, "The project matches the definition this report was baselined against."
    return False, (
        "The project has changed since this report was baselined. The document "
        "still builds, and states the mismatch; read the input echo to see what "
        "moved.")


__all__ = [
    "FINGERPRINT_VERSION",
    "METADATA_KEYS",
    "anchors",
    "fingerprint",
    "identity_matches",
    "oracle_projection",
]
