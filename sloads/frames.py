"""The two frames LANDLOAD states a ground load in, and the manual's words for them.

LANDLOAD prints its whole reaction matrix **twice** -- once with respect to the
ground line, once with respect to the airplane datum -- and says so in a banner
above each table (LANDLOAD.BAS lines 5140 / 5230, Appendix A p230-p233)::

    VALUES ARE WITH RESPECT TO GROUND LINE -- DENOTED BY P (PRIME)
    VALUES ARE WITH RESPECT TO AIRPLANE DATUM

The replication has carried both sets of numbers since M4-17e and named neither,
which is the gap design note 38 GF-7 closes: a reader moving between the Oracle's
per-case table and the assembled deck had no stated bridge, and the two tables
differ by a rotation of the ground angle.

**This module is the single owner** (``CONVENTIONS.md`` §7): the frame constants,
the caption text, and the rule for what each frame is *for*. Both GUIs caption
their reactions tables from :func:`caption` rather than writing the words twice,
and every landing :class:`~sloads.models.LoadValue` names its frame so the
render/export boundary can tell a deliverable from an analysis view
(:data:`~sloads.models.LoadValue.frame`).

**The transform between them lives here too** -- :func:`to_airplane_datum`,
:func:`to_ground_line` and :func:`rotation_deg`. They were in
:mod:`sloads.gear_loads` until design note 38 GF-6 (#134), which needed the
rotation in :mod:`sloads.modules.landing` -- the module ``gear_loads`` itself
imports from -- to build the airplane-datum load factors. A second copy of a
rotation is a sign error waiting to happen, so the function moved down to the
module that names the two frames rather than being written twice.

**What each frame is for.** The ground-line ("primed") set is the frame the
manual prints and a gear engineer reads -- the reaction resolved against the
runway. The airplane-datum set is the frame a beam model applies: the same
reaction in body axes, which is what a ``FORCE`` card carries. Design note 38
GF-6 rules that the delivered CSV carries the body frame **only**, and the
primed set stays in the text report beside it -- see
:func:`sloads.report.render.results_to_rows`.
"""

from __future__ import annotations

import math
from typing import Tuple

__all__ = [
    "AIRPLANE_DATUM",
    "FRAMES",
    "GROUND_LINE",
    "caption",
    "is_report_only",
    "rotation_deg",
    "to_airplane_datum",
    "to_ground_line",
]

#: The manual's primed set: resolved against the runway. Report-only in the
#: delivered CSV (design note 38 GF-6).
GROUND_LINE = "ground line"

#: Body axes -- the frame the assembled deck and every exported card use.
AIRPLANE_DATUM = "airplane datum"

#: Every frame a value may name. A ``LoadValue`` with a blank frame names none,
#: which is the right answer for a sink rate or a load factor and is why the
#: field defaults to empty rather than to either of these.
FRAMES = (GROUND_LINE, AIRPLANE_DATUM)

_CAPTIONS = {
    GROUND_LINE: "with respect to ground line",
    AIRPLANE_DATUM: "with respect to airplane datum",
}


def caption(frame: str) -> str:
    """The manual's own words for ``frame``, for a table heading or a caption.

    Raises on an unknown frame rather than returning a blank: a reactions table
    with a silently empty frame caption is the exact defect GF-7 exists to fix.
    """
    try:
        return _CAPTIONS[frame]
    except KeyError:
        raise ValueError(
            f"no caption for frame {frame!r}; expected one of {FRAMES}") from None


def is_report_only(frame: str) -> bool:
    """Whether a value in ``frame`` is a report view rather than a deliverable.

    The one rule behind GF-6's split: the ground-line set is the manual's
    analysis view and stays in the text report; everything else -- the body
    frame, and every frameless quantity -- is delivered. Read by
    :func:`sloads.report.render.results_to_rows`, which is the only channel that
    drops rows, so the text report keeps both sets by construction.
    """
    return frame == GROUND_LINE


# --------------------------------------------------------------------------- #
# The rotation between the two frames
# --------------------------------------------------------------------------- #
def rotation_deg(v_datum: float, d_datum: float,
                 v_ground: float, d_ground: float) -> float:
    """``rho`` -- the angle from the ground line to the airplane datum, in degrees.

    Measured from **one reaction resolved both ways** rather than from ``GRA``::

        rho = atan2(d_datum, v_datum) - atan2(d_ground, v_ground)

    i.e. the angle between the airplane-datum pair LANDLOAD resolves through
    ``PHIM``/``PHIN`` and the ground-line pair it resolved. Doing it this way
    means no caller has to restate a sign: ``rho`` comes out ``-GRA`` on every
    attitude (design note 38 GF-1, landed 2026-08-29), and it comes out that way
    because the numbers say so, not because a constant here says so.

    Two things read it. **The ground-line lift axis** (decision G-7a -- the lift
    is perpendicular to the flight path, so it lies along the ground-line
    vertical and enters the airplane's axes tilted by ``rho``), which is both the
    assembled deck's lift and the ``NV``/``ND`` datum load factors' lift term
    (design note 38 GF-6/OQ-1). And **the closed-form load-factor gate** (G-6),
    where rotating the solved rigid-body field back to the ground line must
    reproduce ``NVP``/``NDP`` exactly. The exported cards themselves take
    LANDLOAD's ``vm``/``dm`` directly and never see this angle.
    """
    return math.degrees(math.atan2(d_datum, v_datum) - math.atan2(d_ground, v_ground))


def to_airplane_datum(v: float, d: float, rho_deg: float) -> Tuple[float, float]:
    """Ground-line ``(V, D)`` -> airplane-datum ``(v, d)``, rotating by ``rho``.

    The inverse of what :func:`rotation_deg` measures, and the one place the
    rotation is *applied*. Every gear reaction is taken from LANDLOAD's own
    ``vm``/``dm`` instead of being rotated here, which is why this is a small
    function rather than the centre of gravity of anything: what needs it is the
    ground-line **lift** (G-7a), in the deck and in the datum load factors.

    It also carries the datum unbalanced moments (design note 38 §1.13). A moment
    vector rotates exactly as a force vector does under the same change of frame;
    the pairing is ``v = YAW`` and ``d = ROLL``, because roll is about the drag
    axis and yaw about the vertical one -- see ``landing.landing_reactions``.
    """
    a = math.radians(rho_deg)
    return (v * math.cos(a) - d * math.sin(a),
            d * math.cos(a) + v * math.sin(a))


def to_ground_line(v: float, d: float, rho_deg: float) -> Tuple[float, float]:
    """Airplane-datum ``(v, d)`` -> ground-line ``(V, D)``. The exact inverse of
    :func:`to_airplane_datum`, and what G-6's gate rotates the solved load-factor
    field through before comparing it with ``NVP``/``NDP``."""
    a = math.radians(rho_deg)
    return (v * math.cos(a) + d * math.sin(a),
            d * math.cos(a) - v * math.sin(a))
