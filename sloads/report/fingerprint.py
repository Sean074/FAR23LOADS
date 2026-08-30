"""Provenance for the oracle technical report: the fingerprint and the anchors.

Design note 44, OR-21. Two different questions are answered by two different
things, and the report carries both:

* *Is this the same airplane?* -- the **anchors**: project name and FAR 23
  category. This is what a reader of the PDF actually checks, and a hex string
  tells them nothing. Reduced from six rows to two in the 2026-08-30 GUI
  review; see :func:`anchors` for what that costs.
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
from typing import Any, Dict, List, Tuple

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


def category_name(code: str) -> str:
    """``"N"`` -> ``"Normal / commuter (N)"``, from the one category owner.

    :data:`sloads.models.inputs.CATEGORIES` is that owner -- the same table the
    input widgets offer and ``normalise_code`` checks against. A second mapping
    here would be a place for the two to disagree, and the failure mode is a
    document that names a certification category the analysis did not use.
    """
    from ..models.inputs import CATEGORIES

    code = (code or "").strip().upper()
    if not code:
        return "not stated"
    name = CATEGORIES.get(code)
    return f"{name} ({code})" if name else code


def anchors(project: Project, *, tool_version: str = "") -> List[Tuple[str, str]]:
    """The human identity rows printed beside the fingerprint.

    Four rows: what the project is called, what it is being certificated as,
    which build of sloads wrote the document, and which schema version the
    project definition was written by.
    The category is **spelled out** rather than left as its code -- "N" is a
    letter a reader has to look up, and looking it up wrongly is how an analysis
    gets read as Utility.

    It used to carry design weight, wing area, VC and VD as well (GUI review,
    2026-08-30). Those are analysis outputs a reader meets in the body, and
    repeating them on the way in invited two statements of the same number.
    The consequence is recorded rather than glossed: with four rows gone, name
    and category are a weak answer to *is this the same airplane*, so the
    fingerprint beneath them is now the only thing in the document that detects
    a changed input (``ORACLE_REPORT.md`` §5).
    """
    rows = [
        ("Project", project.name or "unnamed"),
        ("FAR 23 category",
         category_name(getattr(project.speeds, "category", ""))),
    ]
    # What produced the document, and what the definition it read was written
    # by. Both are provenance a reader needs when a result cannot be reproduced
    # years later: "which build of the tool" and "which shape of the input".
    #
    # ``tool_version`` is handed in rather than looked up. Reading installed
    # package metadata is filesystem work, which this package does not do, and
    # the build already resolves it once for ``build.json`` -- resolving it
    # twice is how the document and its own stamp come to disagree.
    if tool_version:
        rows.append(("sloads version", tool_version))
    rows.append(("Project schema", f"version {project.schema_version}"))
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
    "category_name",
    "fingerprint",
    "identity_matches",
    "oracle_projection",
]
