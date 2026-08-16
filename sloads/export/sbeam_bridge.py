"""Export the NETLOADS net wing load as sbeam-consumable structural load sets.

This is the C4 *export bridge*: it turns ``Project.loads.wing_net`` (the spanwise
net shear / bending / torsion NETLOADS produces) into the three artifacts sbeam
consumes for structural sizing, matching sbeam's own card style
(``sbeam/results/load_export.py``):

* a **span-load CSV** -- one row per wing station per case, the applied nodal
  loads plus the cumulative shear/BM/torsion for engineering reference;
* **FORCE / MOMENT bulk-data cards** -- comma free-field, unit-scale form
  (``FORCE, SID, GID, 0, 1.0, Fx, Fy, Fz``), one load set per critical case, to
  splice into an existing sbeam model;
* an optional minimal **CBAR stick-model BDF** -- GRID + CBAR + PBAR + MAT1 +
  SPC1 + the load cards + a SOL 101 case-control wrapper, so the load runs
  directly in sbeam.

Case identity in the deck (M4-2)
--------------------------------
Every deck's ``SUBCASE`` and load-set ``SID`` is the case's own id put through
:func:`sloads.case_ids.subcase_id` (``W-03`` -> ``103``), never its position in
the exported list, and each deck opens with a ``$`` subcase-map block naming the
governing condition behind each number (:func:`subcase_map_block`). The exported
case index carries the same number in its ``SUBCASE`` column. A deck consumer can
therefore trace ``SUBCASE 103`` back to "W-03, PHAA, FAR 23.333(b)" from the deck
alone, and a filtered export cannot renumber the subcases that survive.

The bridge is a pure renderer (like :mod:`sloads.io`): the building functions
return strings, the ``write_*`` wrappers do the only file I/O. It is **not** a
registered calc module -- the physics already lives in ``modules/net_loads.py``.

All exported force / moment / pressure magnitudes are **ULTIMATE** loads, since sbeam
sizes structure to ultimate: the calc's LIMIT values x that case's
``safety_factor`` (14 CFR 23.303 -> 1.5 by default; a case already at ultimate
carries 1.0). Coordinates and chord fractions are geometry and are not scaled. The
factor is per *case* and therefore uniform within one exported load set, which keeps
the force/moment-closure guarantees intact (the exported set sums to that case's
factor x the root/total). Every producer mints the field on its result (M4-13), so
``_sf`` reads it directly; ``_SF`` survives only as the default constant tests read.

Nodal loads from the cumulative table
-------------------------------------
``WingStationLoad`` stores per-strip forces *and* cumulative shears/moments
(root-first, i.e. ``stations[0]`` carries the integrated total). The applied
nodal load at station ``i`` is recovered as the **increment of the cumulative
quantity** between adjacent stations::

    dFz[i] = sz[i] - sz[i+1]   (sz beyond the tip = 0)

Because the cumulative columns telescope, ``sum(dFz) == sz[root]`` *exactly*, so
the exported FORCE set sums to the NETLOADS root shear and the MOMENT(My) set to
the root torsion by construction.

Concentrated masses: the offset couples
---------------------------------------
Differencing assumes the table was built by the lumped-at-nodes recursion
``mxx[i] = mxx[i+1] + sz[i+1]*dy``, which is exactly how ``airloads`` and the
panel part of ``wing_inertia`` build it. A **concentrated** wing mass (engine,
gear, fuel, store) breaks that assumption: WINGINER adds it to every station
inboard of it at its *true* station ``y_c`` (``mxx[i] += w*(y_c - ye[i])``,
WINGINER.BAS 1180-1270), and ``y_c`` is not a station. Differencing then picks
the mass up whole at the node inboard of it, moving its lever arm inboard by up
to one strip width: shear still telescopes exactly, **bending does not**.

The loss is recoverable from the published table alone. Define the per-station
defect (:func:`_moment_defect`)::

    delta[k] = mxx[k] - mxx[k+1] - sz[k+1]*(y[k+1] - y[k])

which is identically zero wherever the recursion built the table, and equals
``w*(y_c - y[j])`` at the single station ``j`` bracketing the mass -- precisely
the first moment the differencing dropped. It is restored as an applied
**offset couple** ``mx = delta[j]`` on that node's MOMENT card: a force ``w`` at
``y_c`` is statically equivalent to that force at node ``j`` plus that couple, so
nothing moves and the exported set reproduces the cumulative shear **and**
bending at *every* node, not merely at the root. ``mzz`` (in-plane bending, from
``fx``) carries the same defect and gets the same treatment.

Measured: ``delta`` is non-zero at exactly one node on the three fixtures with
concentrated masses (``atr42_100``, ``dhc8_dash8``, ``concept_heavy``) and
machine-zero everywhere on the three without -- so this is a no-op on the
Appendix A fixture, and the FORCE cards are unchanged for every wing. Before the
couples existed the exported root bending read high by 1.91 % / 1.11 % / 0.44 %
(``Mxx``) and 1.14 % / 0.67 % / 0.32 % (``Mzz``). Design note:
``docs/30_future/14_concentrated_wing_mass_nodal_split_plan.md``.

Torsion reference axis
----------------------
Every exported wing torsion states its chordwise reference axis in-band (the
span-load CSV ``MyyAxis`` column, the BDF ``$`` header comments). The calc
produces torsion about the **25% chord** (oracle-locked); when the export is
built from a ``Project``, the bridge first transfers the wing results to the
surface's **loads reference axis** (LRA, ``SurfaceInput.ref_axis_pct`` --
the beam-model elastic axis, typically 40-50% chord) via
``net_loads.loads_ref_axis_results``, exactly as the limit->ultimate factor is
applied here at the boundary. Callers passing bare ``WingLoadResult`` lists are
responsible for transferring first (the results' ``torsion_axis`` stamp is
exported either way, so the axis is always labelled).

Unit systems (M4-20 step 4)
---------------------------
Every public writer takes ``system=UnitSystem.IMPERIAL|SI`` and resolves it to
the **solver** unit set -- ``deliverable_units(system, Channel.SOLVER)``, i.e.
N / mm / N*mm / MPa in SI. The solver set is deliberately *not* the one a report
uses (N*m, kPa): a deck whose GRIDs are millimetres and whose forces are newtons
is only correct with N*mm moments, and an N*m moment in it is a silent 1000x
torsion error in a file that parses cleanly (decision D-19).

No arithmetic here knows about units. Every dimensional value this module emits
-- card fields *and* CSV cells alike -- goes through
:mod:`sloads.export.coordinates`, which is the single scale point, so a span CSV
can never disagree with the cards beside it. Imperial is the all-1.0 identity, so
an Imperial export takes the same path it always did.

Coordinate / units map: see :mod:`sloads.export.coordinates` (identity axes,
CID 0, plus the unit scale).

Reference: ``sbeam/results/load_export.py`` (card style); NASTRAN FORCE / MOMENT
/ GRID / CBAR / PBAR / MAT1 / SPC1 bulk-data cards; Ref 1 Ch 14 (net loads).
"""

from __future__ import annotations

import csv
import io as _io
import textwrap
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

from ..case_ids import (ASSEMBLED_DECK, COMPONENT_DECK, deck_load_id,
                        subcase_id)
from ..constants import ULTIMATE_FACTOR
from ..models import (
    BodyLoadResult,
    ControlSurfaceLoadResult,
    Project,
    TailChordResult,
    TailSpanResult,
    WingLoadResult,
    WingStationLoad,
)
from ..derived_geometry import SobStation, sob_station
from ..report import ultimate_units
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .bands import band
from .coordinates import (
    SBEAM_CID,
    bending_moment_vector,
    tail_axial_to_airplane,
    tail_force_to_airplane,
    tail_station_to_airplane,
    tail_torsion_to_airplane,
    to_force,
    to_grid,
    to_moment,
    to_pressure,
    ttail_transfer_to_airplane,
)
# Single-sourced from the calc that owns the limitation (public symbol, no cycle:
# nothing under sloads/modules imports the export bridge).
from ..modules import tail_span
from ..modules.body_loads import CLOSURE_ARTIFACT_CAVEAT as _BODY_ARTIFACT_CAVEAT
from ..modules.net_loads import loads_ref_axis_results


# --------------------------------------------------------------------------- #
# Unit set (M4-20 step 4)
# --------------------------------------------------------------------------- #
def _units(system: UnitSystem) -> DeliverableUnits:
    """The **solver** unit set for ``system`` -- the only one a deck may use (D-19).

    Resolved per writer rather than passed around as a bare factor, so a caller
    cannot hand one file a different set from the file beside it: the writer's
    parameter is a *system*, and which units that means for a deck is decided
    here, once.
    """
    return deliverable_units(system, Channel.SOLVER)


def _stamped(header_comment: str, deck: str) -> str:
    """Prepend a ``$``-comment block to a bulk-data deck (M4-20 step 5).

    Every BDF writer takes a ``header_comment`` for the same reason the CSV
    writers do: a deck forwarded on its own must still state that its loads are
    ULTIMATE and which unit set it is in. Until step 5 the Export page built a
    ``bdf_comment_block`` and then never applied it, so the four decks were the
    one channel in the bundle carrying no statement at all.

    ``$`` is a comment to every bulk-data parser, so the block is inert; a blank
    ``header_comment`` returns the deck untouched, which keeps every existing
    caller (and the frozen Imperial comparison) byte-identical.
    """
    if not header_comment:
        return deck
    return header_comment.rstrip("\n") + "\n" + deck


def _ult(label: str) -> str:
    """``lb`` -> ``lbs-ULT``, ``N`` -> ``N-ULT`` -- the renderer's own vocabulary.

    Shared with ``report/render.py`` so the sbeam CSVs and the human-readable
    tables mark ultimate loads identically; a second dialect in the export
    channel would be a thing to keep in sync forever."""
    return ultimate_units(label)

# --------------------------------------------------------------------------- #
# Case-index export (Step D1): ID -> full definition, across every result slice
# that carries a CaseRef. Duplicates by ``case_id`` collapse to one row (the
# same case appears in multiple deliverables -- e.g. a wing case in wing_air,
# wing_inertia and wing_net -- but the index lists it once).
# --------------------------------------------------------------------------- #

# sbeam sizes structure to ULTIMATE loads, so every exported force / moment /
# pressure magnitude is the calc's LIMIT value x the *case's* limit->ultimate factor
# (``result.safety_factor``; 14 CFR 23.303 -> 1.5 by default, 1.0 for a case whose
# values are already ultimate). Geometry (coordinates, chord fractions) is not scaled.
# ``_SF`` is the suite default constant (kept for the closure tests, which read it
# as ``sb._SF``); ``_sf`` reads each result's own field directly (M4-13/M4-16).
_SF = ULTIMATE_FACTOR


def _sf(result: Union[WingLoadResult, BodyLoadResult, TailChordResult,
                      TailSpanResult, ControlSurfaceLoadResult]) -> float:
    """The limit->ultimate factor to scale ``result``'s loads by (defect M4-7).

    Read off the result so each exported load set carries its own case's factor,
    rather than a flat suite-wide constant that would double-factor a case already
    at ultimate (``safety_factor = 1.0``). Every producer mints the field
    (M4-13), so the attribute is read directly — no ``getattr`` fallback that
    would mask an attribute rename (M4-16)."""
    return result.safety_factor


def _sf_str(sf: float) -> str:
    """``SF`` as it appears on a deliverable: ``1.0``/``1.5``/``1.25`` — always
    with a decimal point (``SF=1`` reads poorly on an engineering document,
    M4-16)."""
    s = f"{sf:g}"
    return s if "." in s else f"{sf:.1f}"

# Loads below this magnitude are treated as zero and not emitted (matches
# sbeam/results/load_export.py).
_TOL = 1e-9

# A concentrated-mass moment defect below this fraction of its own column's
# scale is floating-point cancellation residue, not a mass. See
# :func:`_moment_defect` -- it must be relative, and it cannot be ``_TOL``: the
# residue reaches 8e-10 lb-in on the shipped fixtures, which straddles it.
_DEFECT_REL_TOL = 1e-9

# GRID id of the clamped wing-root node in the stick model; station nodes follow.
# Both come out of the band registry (:mod:`sloads.export.bands`) -- see it for
# the whole GID/EID/SID map and why one owner replaced the per-file constants.
_WING_BAND = band("wing-stick")
_ROOT_GID = _WING_BAND.start
_STATION_GID_BASE = _WING_BAND.start  # station i -> GID base + 1 + i (= 2, 3, ...)

# The wing side-of-body reporting node (step 13) -- the first LRA named-node
# family (decision BM-5). Its GRID carries a ``$ SLOADS-NODE lra-sob <side>``
# tag so a consumer (or a re-import) finds it by identity, not by coordinates.
_SOB_BAND = band("lra-sob")


def sob_gid() -> int:
    """GRID id of the wing side-of-body reporting node (right half-span)."""
    return _SOB_BAND.allocate(0)


def _fmt(val: float) -> str:
    """Format a load/coordinate component in NASTRAN 6-digit scientific style."""
    return f"{val:.6E}"


def _closed(value: float, scale: float) -> float:
    """A quantity that is zero **by construction** renders as an unsigned zero.

    The fuselage set closes exactly in exact arithmetic -- ``sum(Fz) == 0`` and
    the terminal ``Myy == 0`` are the equilibrium the deck claims -- but in
    floating point the sum lands on ~1e-11 of accumulated cancellation dust. Its
    magnitude is irrelevant at any printed precision; its **sign is not
    reproducible across platforms** (x86 vs ARM, different libm/FMA builds
    reassociate the upstream arithmetic), so ``f"{total:.2f}"`` prints ``0.00``
    on one machine and ``-0.00`` on another. That is a byte difference in a
    deliverable, and it is what failed the Imperial digest baseline in CI
    (``sbeam/body_cards``) while the same commit passed locally.

    Cards already have this rule -- nothing under :data:`_TOL` is emitted at all.
    This gives the *stated totals* the same one, relative to the set's own scale
    so it cannot mask a real residual on a heavy airplane: a genuine imbalance is
    orders above ``1e-9 x`` the largest load in the same column.
    """
    return 0.0 if abs(value) <= _TOL * max(abs(scale), 1.0) else value


def station_gid(i: int) -> int:
    """GRID id of wing station ``i`` (0 = root), past the clamped root node.

    Allocated from the ``wing-stick`` band, so a station count that would have
    walked into the fuselage block at 1001 raises instead (review m5) -- the
    same guard every other family already had.
    """
    return _WING_BAND.allocate(1 + i)


@dataclass
class NodalLoad:
    """One wing station's exported nodal load (the applied FORCE/MOMENT content).

    ``fx``/``fz`` are the applied force components (lb) and ``my`` the applied
    torsion (lb-in) at the torsion-reference-axis point ``(x, y, z)`` (in) --
    the station ``x`` of the source result: 25% chord as computed, or the
    surface LRA after ``net_loads.to_loads_ref_axis`` -- recovered as
    increments of the NETLOADS cumulative table. ``sz``/``mxx``/``myy`` are the
    cumulative shear / bending / torsion at the station, carried through for the
    span-load CSV's engineering columns.

    ``mx``/``mz`` are the applied **offset couples** (lb-in) that restore the
    first moment of a concentrated mass sitting between two stations -- zero at
    every node of a wing that carries none. See the module docstring; they are
    stored in the calc's own bending sign (positive-magnitude), and
    :func:`~sloads.export.coordinates.bending_moment_vector` owns the mapping to
    the card's CID-0 components."""
    gid: int
    x: float
    y: float
    z: float
    fx: float
    fz: float
    my: float
    sz: float
    sx: float
    mxx: float
    myy: float
    mzz: float
    mx: float = 0.0
    mz: float = 0.0


def _moment_defect(s: Sequence[WingStationLoad], mom: str, shear: str) -> List[float]:
    """The per-station bending defect ``delta[k]`` of a cumulative column.

    ``delta[k] = mom[k] - mom[k+1] - shear[k+1]*(y[k+1] - y[k])`` -- the amount
    by which the published table departs from the lumped-at-nodes recursion the
    differencing above assumes. Identically zero wherever the table was built by
    that recursion (both ``airloads`` and ``wing_inertia`` are), and equal to
    ``w*(y_c - y[k])`` at the one station bracketing a concentrated mass at
    ``y_c``. See the module docstring for the derivation.

    Node spacing is read per interval rather than taken as the uniform ``dy``
    the calc happens to use, so a future non-uniform station set needs no change
    here.

    ``delta`` is a **difference of large nearly-cancelling numbers**, so its
    floating-point noise floor is set by the magnitude of the column it came
    from, not by any absolute value: residues of ~1e-9 lb-in appear against
    columns of ~1e7. Anything below :data:`_DEFECT_REL_TOL` of the column's own
    scale is therefore cancellation residue and is snapped to zero -- otherwise
    a wing with no concentrated mass at all would emit that residue into its
    MOMENT cards, replacing clean zeros with float noise (and, in SI, noise
    multiplied by the moment factor). The threshold is relative for the same
    reason the tolerance in ``equilibrium.closes`` is: an absolute one is a
    different test on a 200-inch wing than on a 500-inch one, and a different
    test again in N*mm. Measured separation is ~14 orders: residue sits at
    ~1e-16 of the column, a real concentrated mass at ~1e-2.
    """
    h = len(s)
    raw: List[float] = []
    for k in range(h):
        if k + 1 < h:
            dy = s[k + 1].y - s[k].y
            raw.append(getattr(s[k], mom) - getattr(s[k + 1], mom)
                       - getattr(s[k + 1], shear) * dy)
        else:
            # No station outboard of the tip: whatever the table still carries
            # here is a mass outboard of the last station, and the couple is
            # exactly as valid there (nothing to transfer a force to, which is
            # why an offset couple and not a force split -- design note 14 D-1).
            raw.append(getattr(s[k], mom))
    floor = _DEFECT_REL_TOL * max((abs(getattr(x, mom)) for x in s), default=0.0)
    return [0.0 if abs(v) <= floor else v for v in raw]


def wing_nodal_loads(result: WingLoadResult) -> List[NodalLoad]:
    """Applied nodal loads for one case, from the cumulative NETLOADS stations.

    The nodal force/torsion at each station is the increment of the cumulative
    shear/torsion to the next station outboard (the last/tip station keeps its
    full value), so the set sums back to the root totals exactly.

    A concentrated wing mass does not sit on a station, so differencing alone
    loses its lever arm (it is picked up whole at the node inboard of it). The
    missing first moment is recovered here as an applied **offset couple**
    ``mx``/``mz`` -- the exact static equivalent of the force at its true
    station -- so the exported set reproduces the cumulative shear *and* bending
    at every node, not just the root. ``mx``/``mz`` are zero at every node of a
    wing with no concentrated masses, which is every fixture the printed oracle
    covers.

    Forces/moments are returned as ULTIMATE loads (LIMIT x the case's
    ``safety_factor``); the scale is uniform within the case, which preserves the
    force/moment-closure guarantee (``sum(dFz) == safety_factor x root``).
    """
    s: List[WingStationLoad] = result.stations
    sf = _sf(result)
    n = len(s)
    d_mxx = _moment_defect(s, "mxx", "sz")
    d_mzz = _moment_defect(s, "mzz", "sx")
    out: List[NodalLoad] = []
    for i in range(n):
        nxt = s[i + 1] if i + 1 < n else None
        dfx = (s[i].sx - (nxt.sx if nxt else 0.0)) * sf
        dfz = (s[i].sz - (nxt.sz if nxt else 0.0)) * sf
        dmy = (s[i].myy - (nxt.myy if nxt else 0.0)) * sf
        out.append(NodalLoad(
            gid=station_gid(i), x=s[i].x, y=s[i].y, z=s[i].z,
            fx=dfx, fz=dfz, my=dmy,
            sz=s[i].sz * sf, sx=s[i].sx * sf,
            mxx=s[i].mxx * sf, myy=s[i].myy * sf, mzz=s[i].mzz * sf,
            mx=d_mxx[i] * sf, mz=d_mzz[i] * sf,
        ))
    return out


# --------------------------------------------------------------------------- #
# Inputs: accept a Project, a list of results, or a single result
# --------------------------------------------------------------------------- #
ResultsArg = Union[Project, WingLoadResult, Sequence[WingLoadResult]]


def _as_results(arg: ResultsArg) -> List[WingLoadResult]:
    """Coerce the argument to the list of net wing-load results to export."""
    if isinstance(arg, Project):
        if arg.loads is None or not arg.loads.wing_net:
            raise ValueError(
                "Project has no net wing loads to export -- run the 'net_loads' "
                "module (build_net_loads) first so Project.loads.wing_net is set."
            )
        # Boundary transfer: exported wing torsion is stated about the surface's
        # loads reference axis (no-op when the LRA is the 25% chord).
        return loads_ref_axis_results(arg, list(arg.loads.wing_net))
    if isinstance(arg, WingLoadResult):
        return [arg]
    results = list(arg)
    if not results:
        raise ValueError("no wing-load results to export")
    return results


def _sid(sid_base: int, case_index: int, result=None) -> int:
    """Load-set id (== the ``SUBCASE`` id) for one exported case (M4-2 decisions 8/9).

    Derived from the case's own ``case_ref.case_id`` via
    :func:`sloads.case_ids.subcase_id` -- ``W-03`` -> ``103``, ``VT-31`` -> ``331``
    -- so:

    * a filtered export (:func:`filter_by_selected_case_ids`) cannot renumber the
      cases that survive: before M4-2 the SID/SUBCASE was the case's *position*,
      so deselecting one case silently shifted every deck number after it, and a
      solver result labelled ``SUBCASE 3`` meant a different case in two exports
      of the same project;
    * the per-component blocks keep wing / tail / body / gear sets disjoint, which
      is what an assembled multi-component deck (L-1) needs;
    * ``LOAD = 103`` inside ``SUBCASE 103`` is self-documenting, and the deck's
      ``$`` map block (:func:`subcase_map_block`) and the exported case index name
      the governing condition behind it.

    ``sid_base + case_index`` remains the fallback for a result carrying **no**
    ``CaseRef`` at all -- a bare ``WingLoadResult`` built in a test or a caller
    that never ran SELECT still gets a valid, contiguous deck.
    """
    ref = getattr(result, "case_ref", None) if result is not None else None
    if ref is not None:
        return subcase_id(ref.case_id)
    return sid_base + case_index


def subcase_map(results: Sequence) -> List[tuple]:
    """``[(subcase_id, case_id, condition, far_reference), ...]`` for ``results``.

    The deck-side half of the case index: what a consumer needs to trace a
    ``SUBCASE`` back to the governing condition without opening another file.
    A result with no ``CaseRef`` contributes its positional SID and an empty id.
    """
    out: List[tuple] = []
    for idx, r in enumerate(results):
        ref = getattr(r, "case_ref", None)
        out.append((
            _sid(1, idx, r),
            ref.case_id if ref else "",
            ref.condition if ref else str(getattr(r, "case", "")),
            ref.far_reference if ref else "",
        ))
    return out


def subcase_map_block(results: Sequence) -> List[str]:
    """The deck's ``$`` subcase-map comment block (M4-2 decision 10).

    One line per exported case::

        $ SUBCASE 103 = W-03 -- PHAA -- FAR 23.333(b)

    ``$`` is a comment to every bulk-data parser, so the block is inert; it exists
    so the deck states its own case identity rather than making the reader join it
    to the case-index CSV by position."""
    rows = subcase_map(results)
    if not rows:
        return []
    lines = ["$ ---------------------------------------------------- SUBCASE MAP",
             "$ SUBCASE/SID = SLOADS case id -- condition -- FAR reference"]
    for sid, case_id, condition, far in rows:
        far_txt = f" -- FAR {far}" if far else ""
        lines.append(f"$ SUBCASE {sid} = {case_id or '(no case id)'} -- {condition}{far_txt}")
    return lines


# --------------------------------------------------------------------------- #
# Span-load CSV
# --------------------------------------------------------------------------- #
def _csv_fields(u: DeliverableUnits) -> List[str]:
    """Span-load CSV header row for unit set ``u``.

    Every dimensional column carries its unit and, if it is a load, its ``-ULT``
    marker -- so the file states its own units and nobody has to infer them from
    the magnitude of the numbers (D-21). This makes the Imperial header visibly
    different from the pre-M4-20 bare ``Fx``/``My``; D-21 authorises that, and
    the alternative (units in SI only) would leave the Imperial deck the one
    file in the suite you can misread.
    """
    ln, fo, mo = u.length.label, _ult(u.force.label), _ult(u.moment.label)
    return [
        "Case", "GID", f"X ({ln})", f"Y ({ln})", f"Z ({ln})",
        # applied nodal load (== the FORCE/MOMENT cards)
        f"Fx ({fo})", f"Fz ({fo})", f"My ({mo})",
        # concentrated-mass offset couples -- zero unless the node brackets one
        f"Mx ({mo})", f"Mz ({mo})",
        # cumulative (engineering reference)
        f"Sx ({fo})", f"Sz ({fo})",
        f"Mxx ({mo})", f"Myy ({mo})", f"Mzz ({mo})",
        "MyyAxis",                 # torsion reference axis (in-band, like Basis/SF)
        "SF",                      # the case's limit -> ultimate factor (last column)
    ]


def span_load_csv(arg: ResultsArg, header_comment: str = "", *,
                  system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Span-load CSV: one row per wing station per case (root->tip).

    Columns ``Fx/Fz/My`` are the applied nodal loads exported as FORCE/MOMENT
    cards; ``Sx/Sz/Mxx/Myy/Mzz`` are the cumulative NETLOADS distributions. All are
    ULTIMATE; ``SF`` is the case's limit->ultimate factor they were scaled by.
    ``MyyAxis`` states the chordwise axis ``My``/``Myy`` (and station ``X``) are
    about -- the axis travels in-band with the file, like ``SF``.

    The cells go through the same ``to_grid``/``to_force``/``to_moment`` the
    cards do, so this file and the deck beside it are the same numbers in the
    same units by construction, not by matching two scale factors.
    """
    results = _as_results(arg)
    u = _units(system)
    fields = _csv_fields(u)
    (x_h, y_h, z_h, fx_h, fz_h, my_h, mx_h, mz_h,
     sx_h, sz_h, mxx_h, myy_h, mzz_h) = fields[2:15]
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        for nl in wing_nodal_loads(r):
            gx, gy, gz = to_grid(nl.x, nl.y, nl.z, u)
            fx, _, fz = to_force(nl.fx, 0.0, nl.fz, u)
            _, my, _ = to_moment(0.0, nl.my, 0.0, u)
            cmx, _, cmz = bending_moment_vector(nl.mx, nl.mz, u)
            sx, _, sz = to_force(nl.sx, 0.0, nl.sz, u)
            mxx, myy, mzz = to_moment(nl.mxx, nl.myy, nl.mzz, u)
            writer.writerow({
                "Case": r.case, "GID": nl.gid,
                x_h: f"{gx:.3f}", y_h: f"{gy:.3f}", z_h: f"{gz:.3f}",
                fx_h: f"{fx:.1f}", fz_h: f"{fz:.1f}", my_h: f"{my:.0f}",
                mx_h: f"{cmx:.0f}", mz_h: f"{cmz:.0f}",
                sx_h: f"{sx:.1f}", sz_h: f"{sz:.1f}",
                mxx_h: f"{mxx:.0f}", myy_h: f"{myy:.0f}", mzz_h: f"{mzz:.0f}",
                "MyyAxis": r.torsion_axis,
                "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def write_span_load_csv(arg: ResultsArg, path: str, *,
                        header_comment: str = "",
                        system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(span_load_csv(arg, header_comment, system=system))


# --------------------------------------------------------------------------- #
# FORCE / MOMENT bulk-data cards
# --------------------------------------------------------------------------- #
def _force_moment_lines(loads: List[NodalLoad], sid: int,
                        u: DeliverableUnits) -> List[str]:
    """FORCE/MOMENT card lines for one load set (skip ~zero components).

    The negligible-load test is applied to the **unscaled** magnitude, so which
    cards a case emits is a property of the load, not of the unit system: an SI
    deck and an Imperial deck of the same case have the same cards, differing
    only in their numbers.
    """
    lines: List[str] = []
    for nl in loads:
        fx, fy, fz = to_force(nl.fx, 0.0, nl.fz, u)
        if abs(nl.fx) > _TOL or abs(nl.fz) > _TOL:
            lines.append(
                f"FORCE, {sid}, {nl.gid}, {SBEAM_CID}, 1.0, "
                f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}"
            )
        # Torsion about y, plus the concentrated-mass offset couples about x/z
        # (zero unless this node brackets a concentrated mass). The bending pair
        # goes through its own map because ``mzz`` is stored against the vector's
        # sign -- coordinates.bending_moment_vector owns that.
        bx, _, bz = bending_moment_vector(nl.mx, nl.mz, u)
        _, my, _ = to_moment(0.0, nl.my, 0.0, u)
        if max(abs(nl.my), abs(nl.mx), abs(nl.mz)) > _TOL:
            lines.append(
                f"MOMENT, {sid}, {nl.gid}, {SBEAM_CID}, 1.0, "
                f"{_fmt(bx)}, {_fmt(my)}, {_fmt(bz)}"
            )
    return lines


def _comment(text: str) -> List[str]:
    """``text`` as ``$`` comment lines, wrapped inside the 72-column card width.

    Free-field bulk data is 72 columns; ``$ `` costs two of them, so the text
    wraps at 70. Every generated ``$`` sentence goes through here rather than
    being hand-fitted, because the same sentence is wider in SI (the same load in
    newtons carries more digits) -- which is exactly how the wing deck's ``$``
    lines reached ~100 columns unnoticed. Guarded by
    ``test_deck_comments_fit_the_free_field_card_width``.
    """
    return [f"$ {ln}" for ln in textwrap.wrap(text, width=70)]


#: Stated on the wing stick deck beside its SPC (plan 10 §1.1) **and** in the
#: report's standing limitations (review F-R4) — one wording, because a caveat
#: that reads differently in the deck and in the controlling document is two
#: caveats. The clamp sits at BL 0 because every fixture defines the wing LE
#: polyline from the centerline (gross-area convention), so a consumer who reads
#: its reaction as a wing root design load is reading the half-span total.
#: Relocating the SPC would not fix it -- one clamp reacts the whole applied load
#: wherever it sits; the side-of-body quantity is an internal load needing a node
#: the deck lacks (the side-of-body reporting-node item).
CENTERLINE_CLAMP_NOTE = (
    "the wing stick model is clamped at the aircraft CENTERLINE (BL 0), half a "
    "strip inboard of station 0 -- not at the side of body where the wing "
    "attaches. Its SPC reaction is therefore the HALF-SPAN TOTAL applied load, "
    "not a wing root design load, and the bending it reports is above what the "
    "wing-to-fuselage joint carries (23% on the reference GA wing); the "
    "balance is reacted by the carry-through structure and the fuselage. A "
    "single clamp reacts the whole load wherever it sits, so the side-of-body "
    "quantity is an internal CBAR load, not a reaction. Where the project "
    "states or implies a side of body, the deck carries a tagged reporting "
    "node (SLOADS-NODE lra-sob) and the side-of-body internal load is the "
    "CBAR end force in the first element outboard of it."
)


def _offset_couple_note(loads: List[NodalLoad]) -> List[str]:
    """The ``$`` note naming the offset couples, or ``[]`` when there are none.

    Emitted only when the wing actually carries a concentrated mass, so a deck
    for a wing without one is byte-for-byte what it was before the couples
    existed. The note states the consequence of dropping them, because a
    consumer who takes the ``FORCE`` cards and discards the ``MOMENT`` set gets
    the smeared (high) bending back -- design note 14 D-1's stated cost.
    """
    if not any(abs(nl.mx) > _TOL or abs(nl.mz) > _TOL for nl in loads):
        return []
    note = (
        "MOMENT(Mx/Mz) also carries the offset couples of the concentrated "
        "wing masses (engine/gear/fuel/store), which do not sit on a station: "
        "each is the exact static equivalent of its force at its true spanwise "
        "station, so this set reproduces the NETLOADS shear AND bending at "
        "every node. Applying the FORCE cards without the MOMENT set overstates "
        "root bending (the mass reverts to the node inboard of it)."
    )
    return _comment(note)


def _case_card_block(r: WingLoadResult, sid: int, u: DeliverableUnits) -> List[str]:
    """One case's commented FORCE/MOMENT block (header + cards)."""
    loads = wing_nodal_loads(r)
    sf = _sf(r)
    # loads carry the ULTIMATE (x sf) cumulative totals, so the comment matches the cards.
    _, _, root_sz = to_force(0.0, 0.0, loads[0].sz if loads else 0.0, u)
    _, root_myy, _ = to_moment(0.0, loads[0].myy if loads else 0.0, 0.0, u)
    lines = (
        _comment(f"SLOADS net wing load -- case {r.case} "
                 f"(Nz={r.nz:g}, Nx={r.nx:g}), SID {sid}")
        + [f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)"]
        + _comment("Axes: SLOADS station/butt/waterline -> sbeam CID 0 "
                   "(identity).")
        # Its own line, not a clause: wrapping can split a sentence anywhere,
        # and the unit statement is the one part of this block a consumer (and
        # the SI CLI test) greps for.
        + _comment(f"Lengths in {u.length.label}.")
        + _comment(f"Loads are ULTIMATE (limit x SF={_sf_str(sf)}).")
        + _comment(f"Torsion My/Myy about the {r.torsion_axis} "
                   "(station X = that axis).")
        + _comment(f"FORCE set sums to root Sz = {root_sz:.1f} {u.force.label}; "
                   f"MOMENT(My) set sums to root torsion Myy = {root_myy:.1f} "
                   f"{u.moment.label}.")
        + _offset_couple_note(loads)
    )
    lines += _force_moment_lines(loads, sid, u)
    return lines


def force_moment_cards(arg: ResultsArg, sid_base: int = 1, *,
                       header_comment: str = "",
                       system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """FORCE/MOMENT bulk-data card text for every case (one SID per case).

    ``header_comment`` is the ``$``-prefixed methods & units block
    (:func:`~sloads.report.bdf_comment_block`), prepended so a deck forwarded on
    its own states its own basis and unit set -- see :func:`_stamped`.
    """
    results = _as_results(arg)
    u = _units(system)
    blocks: List[str] = ["\n".join(subcase_map_block(results))]
    for idx, r in enumerate(results):
        blocks.append("\n".join(_case_card_block(r, _sid(sid_base, idx, r), u)))
    return _stamped(header_comment, "\n".join(b for b in blocks if b) + "\n")


def write_force_moment_cards(arg: ResultsArg, path: str, sid_base: int = 1, *,
                             header_comment: str = "",
                             system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(force_moment_cards(arg, sid_base=sid_base,
                                    header_comment=header_comment, system=system))


# --------------------------------------------------------------------------- #
# Minimal CBAR stick-model BDF (optional)
# --------------------------------------------------------------------------- #
# Nominal placeholder structural properties, quoted in the Imperial inch /
# pound-force set and converted with the rest of the deck. A clamped cantilever
# loaded only at its nodes is statically determinate, so the reaction loads sbeam
# recovers are independent of these values; they exist only to make the deck
# solvable. They are converted anyway because a deck that mixes an Imperial
# modulus with millimetre GRIDs is wrong on its face -- someone will read it, or
# swap in a real section, long before anyone re-derives that the reactions do not
# depend on it.
_MAT1_E = 1.0e7      # psi (aluminium-ish placeholder)
_MAT1_NU = 0.33      # dimensionless
_PBAR_A = 1.0        # in^2
_PBAR_I = 1.0        # in^4 (I1 = I2)
_PBAR_J = 1.0        # in^4


def _root_node(loads: List[NodalLoad]) -> tuple:
    """Clamped root-node coordinates: half a strip inboard of the first station."""
    if len(loads) >= 2:
        dy = loads[1].y - loads[0].y
    else:
        dy = 0.0
    n0 = loads[0]
    return (n0.x, n0.y - dy / 2.0, n0.z)


# --------------------------------------------------------------------------- #
# Side-of-body internal loads (step 13, note 24 R-3)
# --------------------------------------------------------------------------- #
#: A station this close (in) to the side of body is *at* it -- the existing node
#: becomes the SOB reporting node instead of a coincident duplicate.
_SOB_COINCIDENT_TOL = 1e-9


@dataclass
class SobInternalLoads:
    """The wing internal load at the side-of-body cut, in the calc's columns.

    The **wing root design load** (step 13): shear / bending / torsion carried
    across the wing-to-fuselage joint at butt line ``y`` -- distinct from the
    half-span totals, which include the centre-box strip loads inboard of the
    joint and overstate root bending by ~23 % on the reference GA wing (plan 10
    §1.1). Columns and signs are the span CSV's cumulative set (``Sz``/``Sx``/
    ``Mxx``/``Myy``/``Mzz``), torsion about the case's stated axis; magnitudes
    are ULTIMATE like every deliverable load."""
    y: float
    sz: float
    sx: float
    mxx: float
    myy: float
    mzz: float


def sob_internal_loads(result: WingLoadResult, sob_y: float) -> SobInternalLoads:
    """Closed-form SOB internal load: the applied nodal loads outboard, summed.

    One of the **two ways** the side-of-body load is stated (note 24 R-3), and
    the reference the other -- the solver's CBAR end force in the first element
    outboard of the SOB node -- is gated against in the round-trip harness.
    Each exported nodal load at ``p`` contributes its force plus the lever-arm
    couple about the cut (``fz*(y - sob_y)`` and the concentrated-mass offset
    couples ``mx``/``mz``, which restore lever arms the station table cannot
    carry), so the sum is exactly the static resultant of everything the deck
    applies outboard of the cut. A station coincident with the cut counts as
    outboard: the joint carries the loads applied *at* it.

    The general transfer rule this instantiates -- a load at ``p`` moved to
    node ``n`` carries the couple ``(p - n) x F`` -- gets its single owner in
    ``export/coordinates.py`` with the step 12 LRA exporter (note 24 R-11).
    """
    sz = sx = mxx = myy = mzz = 0.0
    for nl in wing_nodal_loads(result):
        if nl.y < sob_y - _SOB_COINCIDENT_TOL:
            continue
        arm = nl.y - sob_y
        sz += nl.fz
        sx += nl.fx
        mxx += nl.fz * arm + nl.mx
        mzz += nl.fx * arm + nl.mz
        myy += nl.my
    return SobInternalLoads(sob_y, sz, sx, mxx, myy, mzz)


def sob_collapsed_load(result: WingLoadResult,
                       sob_xyz: Tuple[float, float, float]) -> NodalLoad:
    """The strip loads inboard of the SOB, as one equivalent load *at* it.

    The start of the LRA-model wing beam (note 24 R-3): that beam runs SOB ->
    tip, and the centre-box strip loads inboard of the joint -- which the
    target model calls inaccurate as *local* loads -- are carried as this
    resultant-preserving equivalent (force plus lever-arm couples) on the SOB
    node instead. Together with :func:`sob_internal_loads` it reproduces the
    half-span totals exactly, which is the invariant the tests pin; the
    per-component wing deck never applies it (its stations are not truncated,
    plan 10 §1.1 constraint 1).

    ``mx``/``mz`` are in the calc's bending sign like every :class:`NodalLoad`
    couple; ``my`` is the summed torsion about the stated axis. The cumulative
    columns are zero -- this is an applied load, not a station of the table.
    """
    x, y, z = sob_xyz
    fx = fz = my = mx = mz = 0.0
    for nl in wing_nodal_loads(result):
        if nl.y >= y - _SOB_COINCIDENT_TOL:
            continue
        arm = nl.y - y
        fx += nl.fx
        fz += nl.fz
        my += nl.my
        mx += nl.fz * arm + nl.mx
        mz += nl.fx * arm + nl.mz
    return NodalLoad(gid=sob_gid(), x=x, y=y, z=z, fx=fx, fz=fz, my=my,
                     sz=0.0, sx=0.0, mxx=0.0, myy=0.0, mzz=0.0, mx=mx, mz=mz)


def _stick_chain(base_loads: List[NodalLoad], sob: Optional[SobStation]
                 ) -> Tuple[List[Tuple[int, Tuple[float, float, float]]],
                            Optional[int]]:
    """The stick model's node run, root -> tip, with the SOB node inserted.

    Returns ``(nodes, sob_node_gid)``: nodes are ``(gid, (x, y, z))`` in chain
    order, and ``sob_node_gid`` is the GRID carrying the ``$ SLOADS-NODE``
    tag -- an inserted :func:`sob_gid` node interpolated onto the beam line
    between its bracketing stations, or the existing station node when the side
    of body falls on one, or ``None`` when the project states no side of body
    (or states one outside the beam -- inboard of the clamped root node or
    outboard of the tip, which is a geometry statement this deck cannot carry).
    The station set is never truncated (plan 10 §1.1 constraint 1): the node is
    *added*, and every FORCE/MOMENT card stays where it was.
    """
    nodes: List[Tuple[int, Tuple[float, float, float]]] = (
        [(_ROOT_GID, _root_node(base_loads))]
        + [(nl.gid, (nl.x, nl.y, nl.z)) for nl in base_loads])
    if sob is None:
        return nodes, None
    if sob.y <= nodes[0][1][1] + _SOB_COINCIDENT_TOL:
        return nodes, None        # on or inboard of the clamped root node
    for gid, (_x, y, _z) in nodes[1:]:
        if abs(y - sob.y) <= _SOB_COINCIDENT_TOL:
            return nodes, gid
    for i in range(1, len(nodes)):
        (_ga, (xa, ya, za)) = nodes[i - 1]
        (_gb, (xb, yb, zb)) = nodes[i]
        if ya < sob.y < yb:
            t = (sob.y - ya) / (yb - ya)
            pos = (xa + t * (xb - xa), sob.y, za + t * (zb - za))
            nodes.insert(i, (sob_gid(), pos))
            return nodes, sob_gid()
    return nodes, None


def _sob_case_lines(r: WingLoadResult, sob_y: float,
                    u: DeliverableUnits) -> List[str]:
    """The ``$`` statement of one case's closed-form SOB internal loads."""
    si = sob_internal_loads(r, sob_y)
    sx, _, sz = to_force(si.sx, 0.0, si.sz, u)
    mxx, myy, mzz = to_moment(si.mxx, si.myy, si.mzz, u)
    return _comment(
        f"SOB internal loads, case {r.case} (closed-form, ULTIMATE): "
        f"Sz={sz:.1f}, Sx={sx:.1f} {u.force.label}; Mxx={mxx:.0f}, "
        f"Myy={myy:.0f}, Mzz={mzz:.0f} {u.moment.label}.")


def stick_model_bdf(arg: ResultsArg, sid_base: int = 1, *,
                    header_comment: str = "",
                    system: UnitSystem = UnitSystem.IMPERIAL,
                    sob: Optional[SobStation] = None) -> str:
    """A minimal SOL 101 CBAR stick model carrying the exported wing load sets.

    A clamped cantilever along the wing's torsion reference axis (the station
    ``x`` of the exported loads: 25% chord as computed, or the surface's LRA
    after the boundary transfer): one GRID per station plus a clamped root node,
    a single PBAR/MAT1 (nominal placeholder properties), a CBAR chain, and one
    SUBCASE per case selecting that case's FORCE/MOMENT load set. Geometry is
    shared across cases (same wing); only the load set changes.

    ``sob`` is the wing's side-of-body station (step 13): when the argument is
    a :class:`Project` it is resolved via
    :func:`sloads.derived_geometry.sob_station` (decision BM-1); callers passing
    bare result lists state it themselves or ship the pre-step-13 deck. When it
    resolves, the deck gains a tagged **reporting node** at the joint -- no load
    moves, no station is dropped -- and states each case's closed-form SOB
    internal loads beside the load sets, so the wing root design load is
    readable from the file without solving it.
    """
    results = _as_results(arg)
    if sob is None and isinstance(arg, Project):
        sob = sob_station(arg)
    u = _units(system)
    # Station geometry is shared across cases -- take it from the first.
    base_loads = wing_nodal_loads(results[0])
    chain, sob_node_gid = _stick_chain(base_loads, sob)
    sob_index = next((i for i, (gid, _p) in enumerate(chain)
                      if gid == sob_node_gid), None)
    rx, ry, rz = to_grid(*_root_node(base_loads), units=u)

    head: List[str] = ["SOL 101", "$"] + subcase_map_block(results) + ["$"]
    for idx, r in enumerate(results):
        # SUBCASE == SID == the case's own id (M4-2 decisions 8/9), so the deck's
        # numbering is a property of the case, not of this export's case list.
        sid = _sid(sid_base, idx, r)
        label = r.case_ref.case_id if r.case_ref else r.case
        head += [
            f"SUBCASE {sid}",
            f"  LABEL = {label}",
            f"  TITLE = {r.case} (Nz={r.nz:g}, Nx={r.nx:g})",
            "  SPC = 1",
            f"  LOAD = {sid}",
            "  DISPLACEMENT = ALL",
            "  SPCFORCE = ALL",
            "  FORCE = ALL",
            "$",
        ]
    head.append("BEGIN BULK")

    bulk: List[str] = [
        "$ ------------------------------------------------------------ NODES",
        f"$ Beam axis: the wing {results[0].torsion_axis} line.",
        "$ GRID, GID, CP, X1, X2, X3",
        f"GRID, {_ROOT_GID}, , {_fmt(rx)}, {_fmt(ry)}, {_fmt(rz)}",
    ]
    for gid, (x, y, z) in chain[1:]:
        if gid == sob_node_gid:
            outboard = (f" The side-of-body internal load is the CBAR end "
                        f"force in element {sob_index + 1}, the first element "
                        "outboard; per-case closed-form values are the $ SOB "
                        "lines in the LOADS section."
                        if sob_index is not None and sob_index + 1 < len(chain)
                        else "")
            bulk.append("$ SLOADS-NODE lra-sob R")
            bulk += _comment(
                f"{sob.note}. Reporting node only (step 13): no load is "
                "applied here and no station is dropped -- the FORCE/MOMENT "
                "sets and their station-0 closure are unchanged." + outboard)
        gx, gy, gz = to_grid(x, y, z, u)
        bulk.append(f"GRID, {gid}, , {_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")

    # Section properties are area / second moment, so they scale as length^2 and
    # length^4 -- derived from the one length factor, never quoted per system.
    e_mod = to_pressure(_MAT1_E, u)
    area = _PBAR_A * u.length.factor ** 2
    inertia = _PBAR_I * u.length.factor ** 4
    torsion_j = _PBAR_J * u.length.factor ** 4
    bulk += [
        "$ --------------------------------------------------------- MATERIAL",
        "$ MAT1, MID, E, G, NU, RHO",
        "$ Placeholder properties: the reactions are stiffness-independent.",
        f"$ E in {u.pressure.label}; A in {u.length.label}^2; I, J in {u.length.label}^4.",
        f"MAT1, 1, {_fmt(e_mod)}, , {_MAT1_NU}, 0.0",
        "$ ------------------------------------------------------- PROPERTIES",
        "$ PBAR, PID, MID, A, I1, I2, J",
        f"PBAR, 1, 1, {_fmt(area)}, {_fmt(inertia)}, {_fmt(inertia)}, {_fmt(torsion_j)}",
        "$ --------------------------------------------------------- ELEMENTS",
        "$ CBAR, EID, PID, GA, GB, X1, X2, X3  (orientation vector 0,0,1)",
    ]
    # CBAR chain: root node -> station 0 -> ... -> tip, through the SOB node
    # where one exists (the element split is what makes the SOB internal load a
    # recoverable CBAR end force).
    prev = _ROOT_GID
    for eid, (gid, _pos) in enumerate(chain[1:], start=1):
        bulk.append(f"CBAR, {eid}, 1, {prev}, {gid}, 0.0, 0.0, 1.0")
        prev = gid

    bulk += [
        "$ ------------------------------------------------------- CONSTRAINTS",
        "$ SPC1, SID, C, G  (clamp the root node, all 6 DOF)",
        *_comment("CAVEAT: " + CENTERLINE_CLAMP_NOTE),
        f"SPC1, 1, 123456, {_ROOT_GID}",
        "$ ------------------------------------------------------------ LOADS",
    ]
    for idx, r in enumerate(results):
        if sob is not None and sob_node_gid is not None:
            bulk += _sob_case_lines(r, sob.y, u)
        bulk += _case_card_block(r, _sid(sid_base, idx, r), u)

    return _stamped(header_comment, "\n".join(head + bulk + ["ENDDATA"]) + "\n")


def write_stick_model_bdf(arg: ResultsArg, path: str, sid_base: int = 1, *,
                          header_comment: str = "",
                          system: UnitSystem = UnitSystem.IMPERIAL,
                          sob: Optional[SobStation] = None) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(stick_model_bdf(arg, sid_base=sid_base,
                                 header_comment=header_comment, system=system,
                                 sob=sob))


# --------------------------------------------------------------------------- #
# Body (fuselage) net-load export (Step C6, R8)
# --------------------------------------------------------------------------- #
# The fuselage net distribution (Ch 15) is a longitudinal beam: each station
# carries an applied vertical force (inertia + tail air load + wing reaction) that
# sums to zero in equilibrium. The export emits a FORCE card (Fz) per station and a
# span-load CSV; there is no applied torsion, so no MOMENT cards.
#
# GIDs are keyed off each station's provenance (``BodyStationLoad.source``), not
# its index in the merged table: the wing carry-through reaction (M4-1) inserts
# extra nodes into the middle of the beam, and an index-based GID would have
# renumbered every mass station aft of the wing whenever the spar stations
# changed. Mass/tail stations therefore keep the historical ``1001 + i`` in
# nose->tail order and the reaction nodes take a disjoint block at ``1501 +``.
_BODY_MASS_BAND = band("body-mass")          # 1001-1500
_BODY_CARRY_BAND = band("body-reaction")     # 1501-2000
_BODY_GID_BASE = _BODY_MASS_BAND.start
_BODY_CARRY_GID_BASE = _BODY_CARRY_BAND.start
_BODY_GID_BLOCK = _BODY_MASS_BAND.size       # capacity of each block

#: ``BodyStationLoad.source`` values that belong to the reaction-node GID block.
_BODY_REACTION_SOURCES = ("carry", "correction")


def beam_station_gid(index: int) -> int:
    """GID of the ``index``-th **fuselage mass station**, nose->tail.

    The station table is the mass SSOT's
    (:func:`sloads.mass_distribution.fuselage_beam_stations`), and its stations
    all enter :func:`body_station_gids` with ``source="mass"`` -- so they take
    the ``1001+`` block in order. Exposed so the CONM2 mass export attaches to
    the same nodes the fuselage load deck does, rather than re-deriving the
    numbering (``CLAUDE.md`` practice 3).
    """
    return _BODY_MASS_BAND.allocate(index)


def body_station_gids(result: BodyLoadResult) -> List[int]:
    """Stable sbeam GIDs for one body result's stations, in table order.

    Fuselage mass stations and the tail air-load station number from
    :data:`_BODY_GID_BASE` in nose->tail order; the wing carry-through reaction
    nodes (or the fallback correction nodes) number from
    :data:`_BODY_CARRY_GID_BASE`. Keying on ``source`` keeps a mass station's GID
    fixed no matter how many reaction nodes are inserted around it."""
    gids: List[int] = []
    n_mass = 0
    n_reaction = 0
    try:
        for s in result.stations:
            if s.source in _BODY_REACTION_SOURCES:
                gids.append(_BODY_CARRY_BAND.allocate(n_reaction))
                n_reaction += 1
            else:
                gids.append(_BODY_MASS_BAND.allocate(n_mass))
                n_mass += 1
    except ValueError as exc:
        raise ValueError(
            f"body export: {n_mass} mass and {n_reaction} reaction stations "
            f"exceed their GID band (would collide with the next band) -- {exc}"
        ) from None
    return gids


def _shared_grid_block(gid_x: List[tuple], u: DeliverableUnits,
                       what: str, notes: Sequence[str] = ()) -> List[str]:
    """A ``GRID`` block for nodes on the ``x`` axis, emitted **once** per deck.

    Geometry is shared across the cases in a deck (same airplane), so the block
    goes ahead of the per-case load blocks exactly as :func:`stick_model_bdf`
    does. Before this existed the body and tail decks named GIDs that had no
    ``GRID`` card in any file: a consumer could not place the loads without a
    second artifact, and neither deck could be moment-checked from its own text
    (the closure the header claims). ``y``/``z`` are zero -- these decks are the
    component's beam line in isolation, not its position on the airplane.

    ``gid_x`` pairs are de-duplicated; a GID appearing twice with two different
    stations is a GID-scheme defect and raises rather than emitting whichever
    card came last.
    """
    merged: dict = {}
    for gid, x in gid_x:
        prev = merged.get(gid)
        if prev is not None and abs(prev - x) > 1e-9:
            raise ValueError(
                f"{what} export: GID {gid} is used for two different stations "
                f"({prev} and {x} in) -- the GID scheme does not separate them"
            )
        merged[gid] = x
    # Wrapped so every comment stays inside the 72-col free-field card width.
    lines = ["$ ------------------------------------------------------------ NODES"]
    for note in (f"{what} beam line; y = z = 0 (the component in isolation, not "
                 "its station on the airplane).",
                 f"Lengths in {u.length.label}.") + tuple(notes):
        lines += [f"$ {ln}" for ln in textwrap.wrap(note, width=70)]
    lines.append("$ GRID, GID, CP, X1, X2, X3")
    for gid, x in sorted(merged.items()):
        gx, gy, gz = to_grid(x, 0.0, 0.0, u)
        lines.append(f"GRID, {gid}, , {_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")
    return lines


def _body_results(arg: "Union[Project, BodyLoadResult, Sequence[BodyLoadResult]]") -> List[BodyLoadResult]:
    if isinstance(arg, Project):
        if arg.loads is None or not arg.loads.body_net:
            raise ValueError(
                "Project has no net body loads to export -- run the 'body_loads' "
                "module (build_body_loads) first so Project.loads.body_net is set."
            )
        return list(arg.loads.body_net)
    if isinstance(arg, BodyLoadResult):
        return [arg]
    results = list(arg)
    if not results:
        raise ValueError("no body-load results to export")
    return results


def body_span_load_csv(arg, header_comment: str = "", *,
                       system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Span-load CSV for the fuselage net distribution: one row per station per
    case (X, applied Fz, cumulative Sz/Myy). Loads are ULTIMATE; ``SF`` is the case's
    limit->ultimate factor they were scaled by."""
    results = _body_results(arg)
    u = _units(system)
    x_h = f"X ({u.length.label})"
    fz_h, sz_h = f"Fz ({_ult(u.force.label)})", f"Sz ({_ult(u.force.label)})"
    myy_h = f"Myy ({_ult(u.moment.label)})"
    buf = _io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["Case", "GID", x_h, fz_h, sz_h, myy_h, "SF"])
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        # The cumulative columns close to zero at the aft end (the same
        # equilibrium the deck states), so the terminal cells carry cancellation
        # dust whose sign is platform-dependent -- see :func:`_closed`.
        sz_scale = max((abs(s.sz) for s in r.stations), default=0.0) * sf
        myy_scale = max((abs(s.myy) for s in r.stations), default=0.0) * sf
        for gid, s in zip(body_station_gids(r), r.stations):
            x, _, _ = to_grid(s.x, 0.0, 0.0, u)
            _, _, fz = to_force(0.0, 0.0, s.fz * sf, u)
            _, _, sz = to_force(0.0, 0.0, s.sz * sf, u)
            _, myy, _ = to_moment(0.0, s.myy * sf, 0.0, u)
            sz, myy = _closed(sz, sz_scale), _closed(myy, myy_scale)
            writer.writerow({
                "Case": r.case, "GID": gid, x_h: f"{x:.3f}",
                fz_h: f"{fz:.1f}", sz_h: f"{sz:.1f}",
                myy_h: f"{myy:.0f}", "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def body_force_moment_cards(arg, sid_base: int = 1, *,
                            header_comment: str = "",
                            system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """FORCE bulk-data cards for the fuselage net distribution (one SID per case);
    the per-station applied Fz set sums to ~0 (vertical equilibrium).

    The set closes both ΣFz and ΣM (Ref 1 Ch 15 p103, M4-1); each block states
    both residuals. A case whose moment was closed by the whole-body fallback
    (no derivable spar stations) is additionally stamped with
    :data:`~sloads.modules.body_loads.CLOSURE_ARTIFACT_CAVEAT`.

    The deck opens with the station ``GRID`` block, so both residuals it claims
    are re-derivable from the file alone -- see
    :mod:`sloads.export.equilibrium`."""
    results = _body_results(arg)
    u = _units(system)
    grid_lines = _shared_grid_block(
        [(gid, s.x) for r in results
         for gid, s in zip(body_station_gids(r), r.stations)],
        u, "Fuselage",
        notes=[f"Nose->tail; carry-through / correction nodes take the "
               f"{_BODY_CARRY_GID_BASE}+ block."],
    )
    blocks: List[str] = ["\n".join(subcase_map_block(results)),
                         "\n".join(grid_lines)]
    for idx, r in enumerate(results):
        sid = _sid(sid_base, idx, r)
        sf = _sf(r)
        _, _, total_fz = to_force(0.0, 0.0, sum(s.fz for s in r.stations) * sf, u)
        _, terminal_myy, _ = to_moment(0.0, r.stations[-1].myy * sf, 0.0, u)
        # Both are zero by construction -- see :func:`_closed` for why the sign of
        # what floating point actually leaves behind must not reach the file.
        total_fz = _closed(total_fz, max((abs(s.fz) for s in r.stations), default=0.0) * sf)
        terminal_myy = _closed(terminal_myy,
                               max((abs(s.myy) for s in r.stations), default=0.0) * sf)
        lines = [
            f"$ SLOADS net fuselage load -- case {r.case}, SID {sid}",
            f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
            f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
            f"$ Applied Fz set sums to {total_fz:.2f} {u.force.label} "
            "(vertical equilibrium).",
            f"$ Terminal Myy {terminal_myy:.2f} {u.moment.label} "
            "(moment equilibrium).",
            "$ i.e. the FORCE moment about the aft-most GRID closes to 0.",
        ]
        if r.spars_assumed:
            lines.append("$ Wing spar stations ASSUMED (chord-fraction defaults), not entered.")
        # Wrapped so each comment stays inside the 72-col free-field card width.
        if r.closure_artifact:
            lines += [f"$ {ln}" for ln in
                      textwrap.wrap("CAVEAT: " + _BODY_ARTIFACT_CAVEAT, width=70)]
        for gid, s in zip(body_station_gids(r), r.stations):
            fx, fy, fz = to_force(0.0, 0.0, s.fz * sf, u)
            if abs(s.fz * sf) > _TOL:
                lines.append(
                    f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                    f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}"
                )
        blocks.append("\n".join(lines))
    return _stamped(header_comment, "\n".join(b for b in blocks if b) + "\n")


def _body_fitting_fields(u: DeliverableUnits) -> List[str]:
    """Fitting-load CSV header for unit set ``u``.

    This file already carried its units; what changes at M4-20 is that they come
    from the unit set rather than being written out Imperial, and that the force
    marker is the renderer's ``lbs-ULT`` rather than this file's own ``lb-ULT``
    -- one vocabulary across every deliverable."""
    ln, fo, mo = u.length.label, _ult(u.force.label), _ult(u.moment.label)
    return [
        "Case", "Case ID", f"X front ({ln})", f"R front ({fo})",
        f"X rear ({ln})", f"R rear ({fo})", f"M unbalanced ({mo})", "Spars", "SF",
    ]


def body_fitting_load_csv(arg, header_comment: str = "", *,
                          system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Wing-attach **fitting loads** CSV: one row per critical fuselage condition.

    The front/rear spar reactions of the Ch 15 p103 solve (Ref 1 p103) -- the
    sizing loads for the wing-attach fittings, reported here rather than in the
    FORCE set because the exported body distribution *already carries* them (as
    the carry-through line load); adding the point reactions on top would double
    them. Loads are ULTIMATE (``SF`` is the limit->ultimate factor applied);
    stations and the spar provenance are unscaled.

    A ``closure_artifact`` case has no spar stations and contributes no row, so
    the file is empty (header only) when every case fell back."""
    results = _body_results(arg)
    u = _units(system)
    fields = _body_fitting_fields(u)
    xf_h, rf_h, xr_h, rr_h, m_h = fields[2:7]
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for r in results:
        if r.r_front is None or r.r_rear is None:
            continue
        sf = _sf(r)
        x_front, x_rear, _ = to_grid(r.x_front, r.x_rear, 0.0, u)
        _, _, r_front = to_force(0.0, 0.0, r.r_front * sf, u)
        _, _, r_rear = to_force(0.0, 0.0, r.r_rear * sf, u)
        _, m_unbalanced, _ = to_moment(0.0, r.m_unbalanced * sf, 0.0, u)
        writer.writerow({
            "Case": r.case,
            "Case ID": r.case_ref.case_id if r.case_ref else "",
            xf_h: f"{x_front:.3f}", rf_h: f"{r_front:.1f}",
            xr_h: f"{x_rear:.3f}", rr_h: f"{r_rear:.1f}",
            m_h: f"{m_unbalanced:.0f}",
            "Spars": "assumed" if r.spars_assumed else "entered",
            "SF": _sf_str(sf),
        })
    return header_comment + buf.getvalue()


def write_body_span_load_csv(arg, path: str, *,
                             header_comment: str = "",
                             system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(body_span_load_csv(arg, header_comment, system=system))


def write_body_fitting_load_csv(arg, path: str, *,
                                header_comment: str = "",
                                system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(body_fitting_load_csv(arg, header_comment, system=system))


def write_body_force_moment_cards(arg, path: str, sid_base: int = 1, *,
                                  header_comment: str = "",
                                  system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body_force_moment_cards(arg, sid_base=sid_base,
                                         header_comment=header_comment,
                                         system=system))


# --------------------------------------------------------------------------- #
# Tail chordwise-load export (Step C7, TAILDIST)
# --------------------------------------------------------------------------- #
# The chordwise tail distribution (Ch 10) is a pressure profile (lb/in^2) on the
# average tail chord at five chord stations. The export emits the profile as a CSV
# and a per-station FORCE set scaled so its total equals the condition's tail load
# (LT25 + LT50) -- a determinate, checkable load set for the tail beam in sbeam.
#
# The profile is a **normal** pressure on the surface, so which airplane axis the
# cards land on is the surface's own: vertical for the h-tail, lateral for the fin.
# That map is not written here -- it comes from ``coordinates.py``, the single
# owner, exactly as the spanwise family below takes it (review F-C3, D-R4). It was
# hand-rolled as ``fz`` for both components until 0.5.0, which loaded a spliced fin
# in the one direction it is not designed for.
_TAIL_CHORD_BANDS = {"htail": band("tail-chord-htail"),
                     "vtail": band("tail-chord-vtail")}
_TAIL_GID_BASE = _TAIL_CHORD_BANDS["htail"].start  # 2001
# ...but the h-tail and the v-tail are different beams with different average
# chords, so their chord stations are *different points* (ga6: the h-tail's five
# run 0 -> 36.39 in, the v-tail's 0 -> 37.49 in). Sharing one 2001+ run between
# them was harmless only while the decks named GIDs that existed nowhere; the
# moment they carry GRID cards it would define one node at two locations. Each
# component therefore gets its own sub-block.
_TAIL_COMPONENT_BLOCK = _TAIL_CHORD_BANDS["htail"].size  # GIDs per tail component
_TAIL_COMPONENTS = tuple(_TAIL_CHORD_BANDS)  # block order: htail 2001+, vtail 2101+


def tail_station_gid(component: str, i: int) -> int:
    """GID of chord station ``i`` of ``component`` ("htail" / "vtail").

    Raises on an unknown component rather than falling back to a shared block:
    a silently-colliding GID puts two loads on one node in an assembled deck,
    which no downstream check would attribute back to here.
    """
    try:
        gid_band = _TAIL_CHORD_BANDS[component]
    except KeyError:
        raise ValueError(
            f"tail export: unknown component {component!r} -- expected one of "
            f"{_TAIL_COMPONENTS}; it has no GID block"
        ) from None
    return gid_band.allocate(i)


def _tail_results(arg: "Union[Project, TailChordResult, Sequence[TailChordResult]]") -> List[TailChordResult]:
    if isinstance(arg, Project):
        if arg.loads is None or not arg.loads.tail_chordwise:
            raise ValueError(
                "Project has no tail chordwise loads to export -- run the 'taildist' "
                "module (build_tail_chordwise) first so Project.loads.tail_chordwise is set."
            )
        return list(arg.loads.tail_chordwise)
    if isinstance(arg, TailChordResult):
        return [arg]
    results = list(arg)
    if not results:
        raise ValueError("no tail chordwise results to export")
    return results


def _trapezoid_tributary_forces(stations, total: float, what: str) -> List[float]:
    """Nodal forces from a chordwise pressure profile, rescaled to sum to ``total``.

    Both chordwise writers (tail and control surface) build their load set the
    same way: trapezoidal tributary width per station x that station's pressure,
    then one scale factor so the set carries the condition's own critical load
    exactly. The two had the arithmetic written out twice, verbatim (review m6).

    A profile whose tributary-weighted pressures integrate to zero cannot be
    scaled to a non-zero ``total``: it **raises** (review F-C4). The former
    ``scale = 0.0`` fallback emitted an all-zero load set under a case header
    that still claimed the non-zero applied sum -- an internally contradictory
    deck, against the raise-loudly contract every neighbouring path here honors.
    A zero ``total`` with a degenerate profile is not contradictory and keeps
    the zero set.

    ``stations`` must be sorted by ``x``; the caller owns the safety factor, so
    ``total`` arrives ULTIMATE. ``what`` names the case/component in the error.
    """
    xs = [s.x for s in stations]
    n = len(xs)
    widths = [((xs[i + 1] if i + 1 < n else xs[i])
               - (xs[i - 1] if i > 0 else xs[i])) / 2.0 for i in range(n)]
    raw = [s.psi * w for s, w in zip(stations, widths)]
    total_raw = sum(raw)
    if abs(total_raw) <= _TOL:
        if abs(total) > _TOL:
            raise ValueError(
                f"{what}: the chordwise profile integrates to zero "
                f"({total_raw:.3e} lb over {n} station(s)), so it cannot carry "
                f"the condition's {total:.4g} lb (ULT) applied load -- no "
                f"scaling of this profile reproduces the case total"
            )
        return [0.0] * n
    scale = total / total_raw
    return [v * scale for v in raw]


def _tail_force_axis(component: str) -> str:
    """Which airplane force component a strip's **normal** load lands on.

    Read out of :func:`tail_force_to_airplane` rather than tabled a second time
    here, so a deck's `$` header and its cards cannot come to disagree: the label
    is the map. Returns ``"Fz"`` for the h-tail, ``"Fy"`` for the fin.
    """
    vec = tail_force_to_airplane(1.0, component)
    return ("Fx", "Fy", "Fz")[max(range(3), key=lambda i: abs(vec[i]))]


def _tail_nodal_forces(r: TailChordResult) -> List[float]:
    """Per-station **normal** forces (lb) from the chordwise pressures, scaled so the
    set sums to the total tail load ``LT25 + LT50`` (trapezoidal chord tributaries).

    Normal to the surface, which is vertical on the h-tail and lateral on the fin:
    the airplane axis is applied by :func:`tail_force_to_airplane` at the card, not
    here (the CSV states it in its own ``Axis`` column)."""
    stations = sorted(r.stations, key=lambda s: s.x)
    return _trapezoid_tributary_forces(
        stations, (r.lt25 + r.lt50) * _sf(r),
        f"tail chordwise export: {r.component} case {r.case}")


def tail_chordwise_csv(arg, header_comment: str = "", *,
                       system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Chordwise tail-load CSV: one row per chord station per critical tail
    condition (component, chord station X, net pressure PSI, scaled nodal normal
    force ``Fn``). ``Axis`` names the airplane component that force is, which is the
    surface's own -- ``Fz`` on the h-tail, ``Fy`` on the fin -- so the CSV and the
    ``FORCE`` cards beside it state one axis, not two (D-R4). Loads are ULTIMATE;
    ``SF`` is the case's limit->ultimate factor they were scaled by."""
    results = _tail_results(arg)
    u = _units(system)
    x_h = f"X ({u.length.label})"
    psi_h = f"PSI ({_ult(u.pressure.label)})"
    fo = _ult(u.force.label)
    fn_h, lt25_h, lt50_h = f"Fn ({fo})", f"LT25 ({fo})", f"LT50 ({fo})"
    buf = _io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["Case", "Component", "GID", x_h, psi_h, fn_h,
                         lt25_h, lt50_h, "Axis", "SF"])
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        forces = _tail_nodal_forces(r)
        stations = sorted(r.stations, key=lambda s: s.x)
        _, _, lt25 = to_force(0.0, 0.0, r.lt25 * sf, u)
        _, _, lt50 = to_force(0.0, 0.0, r.lt50 * sf, u)
        axis = _tail_force_axis(r.component)
        for i, (s, fn) in enumerate(zip(stations, forces)):
            x, _, _ = to_grid(s.x, 0.0, 0.0, u)
            _, _, fn_out = to_force(0.0, 0.0, fn, u)
            writer.writerow({
                "Case": r.case, "Component": r.component,
                "GID": tail_station_gid(r.component, i),
                x_h: f"{x:.3f}", psi_h: f"{to_pressure(s.psi * sf, u):.4f}",
                fn_h: f"{fn_out:.1f}",
                lt25_h: f"{lt25:.2f}", lt50_h: f"{lt50:.2f}",
                "Axis": axis, "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def tail_force_moment_cards(arg, sid_base: int = 1, *,
                            header_comment: str = "",
                            system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """FORCE bulk-data cards for the chordwise tail loads (one SID per condition);
    each set's applied normal force sums to the total tail load ``LT25 + LT50``.

    That normal force is the surface's own airplane component -- ``Fz`` for the
    h-tail, ``Fy`` for the fin -- via :func:`tail_force_to_airplane`, the same map
    the spanwise family uses, and each case block states which (D-R4).

    The deck opens with the chord-station ``GRID`` block (one sub-block per tail
    component), so the set's chordwise first moment is re-derivable from the file
    alone -- see :mod:`sloads.export.equilibrium`. ``x`` is the distance aft of
    the component's leading edge along its average chord; ``y = z = 0``."""
    results = _tail_results(arg)
    u = _units(system)
    grid_lines = _shared_grid_block(
        [(tail_station_gid(r.component, i), s.x)
         for r in results
         for i, s in enumerate(sorted(r.stations, key=lambda s: s.x))],
        u, "Tail chord",
        notes=["x is aft of the component leading edge, along its average "
               "chord; h-tail and v-tail take separate GID blocks.",
               "Each surface's load is NORMAL to it, in airplane axes: Fz on "
               "the h-tail, Fy on the v-tail (its normal force is a side "
               "force). Per-case blocks name their own axis."],
    )
    blocks: List[str] = ["\n".join(subcase_map_block(results)),
                         "\n".join(grid_lines)]
    for idx, r in enumerate(results):
        sid = _sid(sid_base, idx, r)
        sf = _sf(r)
        forces = _tail_nodal_forces(r)
        axis = _tail_force_axis(r.component)
        _, _, total = to_force(0.0, 0.0, sum(forces), u)
        _, _, lt_total = to_force(0.0, 0.0, (r.lt25 + r.lt50) * sf, u)
        lines = [
            f"$ SLOADS chordwise {r.component} load -- case {r.case}, SID {sid}",
            f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
            f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
            f"$ Load is normal to the surface = {axis} in airplane axes.",
            # Split across two lines: a single line overran the 72-col
            # free-field card width once the load reached five figures.
            f"$ Applied {axis} set sums to {total:.1f} {u.force.label}",
            f"$   = {_sf_str(sf)} x (LT25 + LT50) = {lt_total:.1f} {u.force.label}.",
        ]
        for i, fn in enumerate(forces):
            fx2, fy2, fz2 = to_force(*tail_force_to_airplane(fn, r.component), u)
            if abs(fn) > _TOL:
                lines.append(
                    f"FORCE, {sid}, {tail_station_gid(r.component, i)}, "
                    f"{SBEAM_CID}, 1.0, {_fmt(fx2)}, {_fmt(fy2)}, {_fmt(fz2)}"
                )
        blocks.append("\n".join(lines))
    return _stamped(header_comment, "\n".join(b for b in blocks if b) + "\n")


def write_tail_chordwise_csv(arg, path: str, *,
                             header_comment: str = "",
                             system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(tail_chordwise_csv(arg, header_comment, system=system))


def write_tail_force_moment_cards(arg, path: str, sid_base: int = 1, *,
                                  header_comment: str = "",
                                  system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(tail_force_moment_cards(arg, sid_base=sid_base,
                                         header_comment=header_comment, system=system))


# --------------------------------------------------------------------------- #
# Spanwise empennage loads (plan 09 T4) -- GRID + FORCE + MOMENT
# --------------------------------------------------------------------------- #
# The tail's version of the wing stick deck, and the first deck family in the
# suite whose two surfaces do not share an axis map: the h-tail spans ``y`` and
# loads ``fz``, the fin spans ``z`` and loads ``fy``. That mapping is **not**
# written here -- it comes from ``coordinates.py``, the single owner, which is
# also where the fin's torsion sign is derived (plan 09 §2 axes note).
#
# Two differences from the wing bridge worth knowing:
#
# 1. **No differencing.** The wing writer recovers nodal loads as increments of
#    the cumulative shear, because WINGINER publishes nothing else -- and that is
#    what smears a concentrated wing mass one station inboard (the filed wing
#    export defect). ``tail_span`` publishes the strip loads themselves, so this
#    writer emits them directly and inherits none of it.
# 2. **Supported, not clamped.** The h-tail deck is a full-span member reacted at
#    the fuselage attachment stations the physics defined (decision T-8), not at a
#    root node. The v-tail is root-supported at the fuselage.
_TAIL_SPAN_BANDS = {"htail": band("tail-span-htail"),
                    "vtail": band("tail-span-vtail")}
_HTAIL_SPAN_GID_BASE = _TAIL_SPAN_BANDS["htail"].start   # 4001-4500
_VTAIL_SPAN_GID_BASE = _TAIL_SPAN_BANDS["vtail"].start   # 4501-5000
_TAIL_SPAN_BLOCK = _TAIL_SPAN_BANDS["htail"].size


def tail_span_gid(component: str, i: int) -> int:
    """GID of spanwise station ``i`` of ``component``.

    Its own band per surface, registered in :mod:`sloads.export.bands` and
    proved disjoint from every other family there -- so an assembled airframe
    can carry both surfaces at once. The claim used to live in this docstring
    alone, and was false for two months against the balanced deck (review F-C1).
    """
    gid_band = _TAIL_SPAN_BANDS.get(component)
    if gid_band is None:
        raise ValueError(
            f"tail span export: unknown component {component!r} -- expected "
            "'htail' or 'vtail'; it has no GID block")
    return gid_band.allocate(i)


_TAIL_CONTROL_BANDS = {"htail": band("tail-control-htail"),
                       "vtail": band("tail-control-vtail")}


def tail_control_gid(component: str, i: int) -> int:
    """GID of hinge/actuator node ``i`` of ``component``'s control surface (T6).

    Its own band per surface, for the reason the registry states: a hinge station
    is not a strip midpoint, so it is a different point, and a deck that gained
    hinges must not renumber the strips beside them.
    """
    gid_band = _TAIL_CONTROL_BANDS.get(component)
    if gid_band is None:
        raise ValueError(
            f"tail control export: unknown component {component!r} -- expected "
            "'htail' or 'vtail'; it has no GID block")
    return gid_band.allocate(i)


def _tail_span_results(arg, component: str) -> List:
    """The spanwise results to export for one surface."""
    if isinstance(arg, Project):
        loads = arg.loads
        slice_ = getattr(loads, f"{component}_span", None) if loads else None
        if not slice_:
            raise ValueError(
                f"Project has no spanwise {component} loads to export -- run the "
                f"'tail_span' module (build_tail_span) first so "
                f"Project.loads.{component}_span is set.")
        return list(slice_)
    results = [arg] if isinstance(arg, TailSpanResult) else list(arg)
    if not results:
        raise ValueError(f"no spanwise {component} results to export")
    return results


def _tail_span_grid_block(results: Sequence, component: str,
                          u: DeliverableUnits) -> List[str]:
    """``GRID`` cards on the surface's load reference axis, emitted once.

    Geometry is shared across the cases in a deck (same surface), so the block
    goes ahead of the per-case load blocks exactly as the wing stick model does.
    Unlike the chordwise tail deck, these nodes carry their **real airplane
    position** -- the fin's stations are at their waterlines, the h-tail's at
    their butt lines -- because a spanwise deck is a beam in the airplane, not a
    component in isolation.
    """
    lines = ["$ ------------------------------------------------------------ NODES"]
    axis = ("h-tail: span along Y, load Fz, torsion Myy."
            if component == "htail"
            else "v-tail: span along Z, load Fy, torsion Mzz (its span axis).")
    for note in (f"{component} spanwise stations on the load reference axis. {axis}",
                 f"Lengths in {u.length.label}."):
        lines += [f"$ {ln}" for ln in textwrap.wrap(note, width=70)]
    lines.append("$ GRID, GID, CP, X1, X2, X3")
    stations = results[0].stations
    for i, st in enumerate(stations):
        px, py, pz = tail_station_to_airplane(st.x, st.y, component, st.z)
        gx, gy, gz = to_grid(px, py, pz, u)
        lines.append(f"GRID, {tail_span_gid(component, i)}, , "
                     f"{_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")
    # The discrete control surface's own nodes (T6), on the same LRA line: a hinge
    # station is not a strip midpoint, so it gets its own node rather than the
    # nearest one -- rounding a hinge onto a strip is how a localized load path
    # quietly becomes the smeared one it was chosen instead of.
    control = results[0].control_loads
    if control:
        kinds = ", ".join(f"{tail_control_gid(component, i)} {cp.kind}"
                          for i, cp in enumerate(control))
        surface = "elevator" if component == "htail" else "rudder"
        for note in (f"{surface} attachment nodes on the same LRA line: {kinds}.",):
            lines += [f"$ {ln}" for ln in textwrap.wrap(note, width=70)]
        for i, cp in enumerate(control):
            px, py, pz = tail_station_to_airplane(cp.x, cp.y, component, cp.z)
            gx, gy, gz = to_grid(px, py, pz, u)
            lines.append(f"GRID, {tail_control_gid(component, i)}, , "
                         f"{_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")
    return lines


def _tail_span_case_block(r, component: str, sid: int,
                          u: DeliverableUnits) -> List[str]:
    """One case's commented FORCE/MOMENT block for a spanwise tail deck."""
    sf = _sf(r)
    _, _, air = to_force(0.0, 0.0, r.air_total * sf, u)
    lines = [
        f"$ SLOADS spanwise {component} load -- case {r.case}, SID {sid}",
        f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
        f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
        f"$ Torsion about the {r.torsion_axis}.",
        f"$ Air load {air:.1f} {u.force.label}; strip loads are applied directly",
        "$   (not differenced from a cumulative column).",
        f"$ Control-surface load: {r.control_load_mode.upper()} into this surface.",
    ]
    if r.control_load_mode == "discrete":
        _, _, cs = to_force(0.0, 0.0, r.control_surface_load_lb * sf, u)
        hm, _, _ = to_moment(r.hinge_moment_lbin * sf, 0.0, 0.0, u)
        for line in (
            f"Control-surface load {cs:.1f} {u.force.label} is NOT in the strip "
            f"loads: it is applied at the hinge nodes above, {r.control_load_basis}.",
            f"HINGE MOMENT {hm:.1f} {u.moment.label}, on an arm of "
            f"{to_grid(r.hinge_moment_arm_in, 0.0, 0.0, u)[0]:.2f} "
            f"{u.length.label} (a third of the aft-of-hinge chord), reacted as a "
            "couple at the actuator node.",
        ):
            lines += [f"$ {ln}" for ln in textwrap.wrap(line, width=70)]
    if r.tip_transfer is not None:
        t = r.tip_transfer
        _, _, tfz = to_force(0.0, 0.0, t.fz * sf, u)
        tmy, _, _ = to_moment(t.myy * sf, 0.0, 0.0, u)
        for line in (
            f"T-TAIL TRANSFER at the tip node: Fz {tfz:.1f} {u.force.label}, Myy "
            f"{tmy:.1f} {u.moment.label} -- the horizontal tail's concurrent load "
            "(T-5 pairing: the balancing load at this case's own V-n point plus "
            "the h-tail's inertia there).",
            "Roll and yaw transfer are zero: the pairing is a balancing "
            "condition, so the h-tail's halves cancel about the centreline.",
        ):
            lines += [f"$ {ln}" for ln in textwrap.wrap(line, width=70)]
    # Every ``$`` line stays inside 72 columns (the fixed-field bulk-data comment
    # width), so the inertia basis is wrapped rather than appended.
    basis: List[str] = []
    if r.inertia_modelled:
        _, _, iner = to_force(0.0, 0.0, tail_span.inertia_total(r) * sf, u)
        basis.append(f"Surface mass {r.surface_weight_lb:.1f} lb: inertia "
                     f"{iner:.1f} {u.force.label} is IN the loads above.")
        axial = tail_span.axial_total(r)
        if abs(axial) > _TOL:
            _, _, ax_u = to_force(0.0, 0.0, axial * sf, u)
            basis.append(f"Plus {ax_u:.1f} {u.force.label} AXIAL along the fin's "
                         "own span axis, carried in the same FORCE cards.")
    else:
        basis.append("NO INERTIA in these loads: air load only.")
    for line in basis:
        lines += [f"$ {ln}" for ln in textwrap.wrap(line, width=70)]
    notes = list(r.notes)
    if r.rh_scale != r.lh_scale:
        notes.append("this deck carries a NET ROLLING input to the fuselage")
    # The double-count rule, written where a consumer will read it (T-11/T4).
    notes.append(
        "SUPERSEDES the point tail-load station in the fuselage deck (GID 1001 "
        "band) for any combined-airframe sum: apply one representation, not both")
    for note in notes:
        lines += [f"$ {ln}" for ln in textwrap.wrap(f"NOTE: {note}", width=70)]

    for i, st in enumerate(r.stations):
        gid = tail_span_gid(component, i)
        # Normal (bending) and span-axis (axial) strip loads are two components of
        # one applied force, so they go on one card: emitting a second FORCE at
        # the same GID would be equally valid to a solver but would double the
        # card count and invite a consumer to apply only one of them.
        nx, ny, nz = tail_force_to_airplane(st.fz * sf, component)
        ax, ay, az = tail_axial_to_airplane(st.f_span * sf, component)
        fx, fy, fz = to_force(nx + ax, ny + ay, nz + az, u)
        if abs(st.fz) > _TOL or abs(st.f_span) > _TOL:
            lines.append(f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}")
        mx, my, mz = to_moment(*tail_torsion_to_airplane(st.myy_free * sf, component), u)
        if abs(st.myy_free) > _TOL:
            lines.append(f"MOMENT, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(mx)}, {_fmt(my)}, {_fmt(mz)}")

    # The discrete control surface's attachment loads (T6). Same axis maps as the
    # strips -- a hinge reaction is a normal force and its couple is a torsion
    # about the surface's own span axis -- which is the point of routing them
    # through ``coordinates`` rather than writing the fin's sign twice.
    for i, cp in enumerate(r.control_loads):
        gid = tail_control_gid(component, i)
        if abs(cp.f_normal) > _TOL:
            fx, fy, fz = to_force(
                *tail_force_to_airplane(cp.f_normal * sf, component), u)
            lines.append(f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}")
        if abs(cp.m_torsion) > _TOL:
            mx, my, mz = to_moment(
                *tail_torsion_to_airplane(cp.m_torsion * sf, component), u)
            lines.append(f"MOMENT, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(mx)}, {_fmt(my)}, {_fmt(mz)}")

    # The T-tail transfer (T7), on the fin's last node -- the only load in this
    # deck that is not in the fin's local frame, which is why it has its own map.
    transfer = getattr(r, "tip_transfer", None)
    if transfer is not None and r.stations:
        gid = tail_span_gid(component, len(r.stations) - 1)
        fvec, mvec = ttail_transfer_to_airplane(transfer.fz * sf, transfer.myy * sf)
        if abs(transfer.fz) > _TOL:
            fx, fy, fz = to_force(*fvec, u)
            lines.append(f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}")
        if abs(transfer.myy) > _TOL:
            mx, my, mz = to_moment(*mvec, u)
            lines.append(f"MOMENT, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                         f"{_fmt(mx)}, {_fmt(my)}, {_fmt(mz)}")
    return lines


def tail_span_force_moment_cards(arg, component: str = "htail", sid_base: int = 1, *,
                                 header_comment: str = "",
                                 system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """``GRID``+``FORCE``+``MOMENT`` cards for one surface's spanwise loads."""
    results = _tail_span_results(arg, component)
    u = _units(system)
    blocks: List[str] = ["\n".join(subcase_map_block(results)),
                         "\n".join(_tail_span_grid_block(results, component, u))]
    for idx, r in enumerate(results):
        blocks.append("\n".join(
            _tail_span_case_block(r, component, _sid(sid_base, idx, r), u)))
    return _stamped(header_comment, "\n".join(b for b in blocks if b) + "\n")


def write_tail_span_force_moment_cards(arg, path: str, component: str = "htail",
                                       sid_base: int = 1, *,
                                       header_comment: str = "",
                                       system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(tail_span_force_moment_cards(
            arg, component=component, sid_base=sid_base,
            header_comment=header_comment, system=system))


def tail_span_csv(arg, component: str = "htail", header_comment: str = "", *,
                  system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Spanwise tail-load CSV: one row per station per case, ULTIMATE."""
    results = _tail_span_results(arg, component)
    u = _units(system)
    fo, mo = _ult(u.force.label), _ult(u.moment.label)
    span_h = f"Span ({u.length.label})"
    x_h = f"X on LRA ({u.length.label})"
    f_h, s_h = f"Fn ({fo})", f"Sn ({fo})"
    b_h, t_h = f"Mxx ({mo})", f"Myy ({mo})"
    # The axial column is the fin's ``-n_z*W_vt``; identically zero on the h-tail,
    # and kept in the header there so one reader parses both surfaces.
    fa_h, sa_h = f"Fax ({fo})", f"Sax ({fo})"
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Case", "GID", span_h, x_h, f_h, s_h,
                                             b_h, t_h, fa_h, sa_h, "Axis", "SF"])
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        for i, st in enumerate(r.stations):
            _, _, fn = to_force(0.0, 0.0, st.fz * sf, u)
            _, _, sn = to_force(0.0, 0.0, st.sz * sf, u)
            bend, tor, _ = to_moment(st.mxx * sf, st.myy * sf, 0.0, u)
            writer.writerow({
                "Case": r.case, "GID": tail_span_gid(component, i),
                span_h: f"{to_grid(st.y, 0.0, 0.0, u)[0]:.3f}",
                x_h: f"{to_grid(st.x, 0.0, 0.0, u)[0]:.3f}",
                f_h: f"{fn:.2f}", s_h: f"{sn:.2f}",
                b_h: f"{bend:.0f}", t_h: f"{tor:.0f}",
                fa_h: f"{to_force(0.0, 0.0, st.f_span * sf, u)[2]:.2f}",
                sa_h: f"{to_force(0.0, 0.0, st.s_span * sf, u)[2]:.2f}",
                "Axis": r.torsion_axis, "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


# --------------------------------------------------------------------------- #
# Control-surface simplified loads (AILERON / FLAPLOAD / TABLOADS, Step C8)
# --------------------------------------------------------------------------- #
# Each control-surface condition carries a simplified chordwise pressure profile
# (fractional chord 0..1) and a critical total load; the export builds a per-station
# FORCE set scaled so its sum equals that critical load -- a determinate, checkable
# load set for the control-surface beam in sbeam.
_CS_BAND = band("control-surface")
_CS_GID_BASE = _CS_BAND.start  # control-surface chord-station GIDs: 3001-4000


def control_station_gid(i: int) -> int:
    """GID of control-surface chord station ``i``.

    The band was previously open-coded as ``_CS_GID_BASE + i`` at both call
    sites; going through the registry gives it the capacity guard the other
    families already had, and gives the disjointness test one owner to ask.
    """
    return _CS_BAND.allocate(i)


def _control_results(
    arg: "Union[Project, ControlSurfaceLoadResult, Sequence[ControlSurfaceLoadResult]]",
) -> List[ControlSurfaceLoadResult]:
    if isinstance(arg, Project):
        if arg.loads is None or not arg.loads.control_surface:
            raise ValueError(
                "Project has no control-surface loads to export -- run the 'aileron' / "
                "'flap' / 'tab' modules first so Project.loads.control_surface is set."
            )
        return list(arg.loads.control_surface)
    if isinstance(arg, ControlSurfaceLoadResult):
        return [arg]
    results = list(arg)
    if not results:
        raise ValueError("no control-surface results to export")
    return results


def _control_nodal_forces(r: ControlSurfaceLoadResult) -> List[float]:
    """Per-station forces (lb) from the simplified pressures, scaled so the set sums
    to the critical surface load (trapezoidal chord tributaries)."""
    stations = sorted(r.stations, key=lambda s: s.x)
    return _trapezoid_tributary_forces(
        stations, r.load_lb * _sf(r),
        f"control-surface export: {r.surface} case {r.case}")


def control_surface_csv(arg, header_comment: str = "", *,
                        system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Control-surface load CSV: one row per chord station per critical condition
    (surface, case, chord fraction X, pressure PSI, scaled nodal Fz, total load). Loads
    are ULTIMATE; ``SF`` is the case's limit->ultimate factor they were scaled by.

    ``X`` is a **fraction of chord** (0 = LE, 1 = TE), not a station: it is
    dimensionless and is the one column here that is identical in both unit
    systems."""
    results = _control_results(arg)
    u = _units(system)
    psi_h = f"PSI ({_ult(u.pressure.label)})"
    fo = _ult(u.force.label)
    fz_h, load_h = f"Fz ({fo})", f"Load ({fo})"
    buf = _io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["Surface", "Case", "GID", "X (chord frac)", psi_h,
                         fz_h, load_h, "SF"])
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        forces = _control_nodal_forces(r)
        stations = sorted(r.stations, key=lambda s: s.x)
        _, _, load = to_force(0.0, 0.0, r.load_lb * sf, u)
        for i, (s, fz) in enumerate(zip(stations, forces)):
            _, _, fz_out = to_force(0.0, 0.0, fz, u)
            writer.writerow({
                "Surface": r.surface, "Case": r.case, "GID": control_station_gid(i),
                "X (chord frac)": f"{s.x:.3f}",
                psi_h: f"{to_pressure(s.psi * sf, u):.4f}", fz_h: f"{fz_out:.1f}",
                load_h: f"{load:.2f}", "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def control_surface_force_moment_cards(arg, sid_base: int = 1, *,
                                       header_comment: str = "",
                                       system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """FORCE bulk-data cards for the control-surface loads (one SID per condition);
    each set's applied Fz sums to the critical surface load.

    Unlike the wing / body / tail decks this one carries **no** ``GRID`` cards.
    ``ControlSurfaceStation.x`` is a *fraction of chord* (0 = LE, 1 = TE) and
    :class:`~sloads.models.ControlSurfaceLoadResult` carries no chord length, so
    there is no way to turn ``x = 0.35`` into a station in inches or
    millimetres; emitting it as a coordinate would be a silently wrong GRID. The
    deck therefore states its closure in force only, and says so in-band."""
    results = _control_results(arg)
    u = _units(system)
    blocks: List[str] = [
        "\n".join(subcase_map_block(results)),
        "\n".join(
            ["$ ------------------------------------------------------------ NODES"]
            + [f"$ {ln}" for ln in textwrap.wrap(
                "NONE. The chordwise profile is in FRACTIONS OF CHORD (0 = LE, "
                "1 = TE), not stations, and this result carries no chord length "
                "-- so the deck carries no geometry and states its closure in "
                "force only. Place the GIDs against your own surface model.",
                width=70)]
        ),
    ]
    for idx, r in enumerate(results):
        sid = _sid(sid_base, idx, r)
        sf = _sf(r)
        forces = _control_nodal_forces(r)
        _, _, total = to_force(0.0, 0.0, sum(forces), u)
        _, _, critical = to_force(0.0, 0.0, r.load_lb * sf, u)
        lines = [
            f"$ SLOADS control-surface load -- {r.surface} {r.case}, SID {sid}",
            f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
            f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
            f"$ Applied Fz set sums to {total:.1f} {u.force.label} "
            f"(= {_sf_str(sf)} x critical load {critical:.1f} {u.force.label}).",
        ]
        for i, fz in enumerate(forces):
            fx2, fy2, fz2 = to_force(0.0, 0.0, fz, u)
            if abs(fz) > _TOL:
                lines.append(
                    f"FORCE, {sid}, {control_station_gid(i)}, {SBEAM_CID}, 1.0, "
                    f"{_fmt(fx2)}, {_fmt(fy2)}, {_fmt(fz2)}"
                )
        blocks.append("\n".join(lines))
    return _stamped(header_comment, "\n".join(b for b in blocks if b) + "\n")


def write_control_surface_csv(arg, path: str, *,
                              header_comment: str = "",
                              system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(control_surface_csv(arg, header_comment, system=system))


def write_control_surface_force_moment_cards(
    arg, path: str, sid_base: int = 1, *,
    header_comment: str = "",
    system: UnitSystem = UnitSystem.IMPERIAL,
) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(control_surface_force_moment_cards(
            arg, sid_base=sid_base, header_comment=header_comment, system=system))


# --------------------------------------------------------------------------- #
# Export-scope filter (Step D8.3): the Export page's "full set vs governing
# set" toggle, applied to any case-carrying result list whose ``case_ref``
# genuinely traces back to ``envelope.critical`` (fuselage/htail/vtail -- see
# the caller's own scoping note; wing/control-surface results are never passed
# through this since their case ids don't overlap ``envelope.critical``'s).
# --------------------------------------------------------------------------- #
def filter_by_selected_case_ids(results: Sequence, selected_ids) -> List:
    """``results`` filtered to items whose ``case_ref.case_id`` is in
    ``selected_ids``; a result with no ``case_ref`` is kept (defensive -- never
    silently drop an un-tagged case). ``selected_ids is None`` means "no
    filter", returning ``results`` unchanged."""
    if selected_ids is None:
        return list(results)
    ids = set(selected_ids)
    return [r for r in results if not r.case_ref or r.case_ref.case_id in ids]


# --------------------------------------------------------------------------- #
# Case-index table (ID -> component, condition, CG, speed, altitude, FAR)
# --------------------------------------------------------------------------- #
#: The index's deck-number column per deck family. **Two** columns, not one
#: (design note 17, user decision 2026-08-13): one case can hold a number in
#: both -- ``W-05`` is ``105`` in the wing component deck and ``5105`` in the
#: assembled full-span one -- so a single unqualified column would be silently
#: wrong for whichever family it was not quoting. Each header keeps the word
#: ``SUBCASE`` a consumer greps for beside the ``LOAD`` the card set is selected
#: by; they are one integer in the deck (``LOAD = 103`` inside ``SUBCASE 103``).
LOAD_ID_COLUMN = {
    COMPONENT_DECK: "LOAD/SUBCASE (component)",
    ASSEMBLED_DECK: "LOAD/SUBCASE (assembled)",
}


def case_index_rows_from(*groups: Sequence, assembled: Sequence = ()) -> List[dict]:
    """One row per distinct ``case_id`` across any number of case-carrying object
    groups (anything with a ``.case_ref`` -- ``WingLoadResult``, ``BodyLoadResult``,
    ``TailChordResult``, ``ControlSurfaceLoadResult``, ``CriticalCondition``,
    engine ``ConditionResult``, LANDLOAD ``GearReactionCase``, ...). Rows are
    emitted in first-seen order across the groups, in the order given; a
    ``case_id`` seen again (the same case appearing in multiple deliverables --
    e.g. a wing case in ``wing_air``, ``wing_inertia`` and ``wing_net``) is not
    repeated.

    **First-seen defines the row's flight condition**, so callers pass the
    **deck-exported load results before** SELECT's ``CriticalCondition``s (as
    :func:`case_index_rows` does, and as the report's case index and the Imperial
    baseline do). One ``case_id`` can be named at two conditions -- an entered
    ``WingLoadCase`` may restate the CL/V of a condition SELECT already picked
    (``atr42_100``'s ``PHAA``: 170 kt entered against SELECT's 185.85 kt V-n
    point) -- and this table is what a consumer joins ``SUBCASE 103`` to, so the
    condition it states is the one **the cards under that id were computed at**
    (user decision 2026-08-13; the case-side half is
    ``wing_inertia.wing_case_ref``). SELECT's own governing-loads row keeps its
    V-n point, which is what *its* numbers were computed at.

    ``assembled`` is the assembled full-span deck's own cases
    (``BalancedCaseResult``), passed separately because **which** deck column a
    row fills is a property of where the case is exported, not of its id: an id
    is quoted in a column only when it is actually in that deck. A handed id
    (``W-05R``) therefore fills the assembled column alone; a symmetric case that
    both stands as a component deck and assembles fills both, which is the point
    of carrying two columns (design note 17).
    """
    by_id: dict = {}
    rows: List[dict] = []

    def add(item, family: str) -> None:
        ref = getattr(item, "case_ref", None)
        if ref is None:
            return
        row = by_id.get(ref.case_id)
        if row is None:
            row = {
                "ID": ref.case_id,
                # The deck-side identity of the same case (M4-2 decision 10): the
                # index is where a consumer joins "SUBCASE 103" to its condition.
                LOAD_ID_COLUMN[COMPONENT_DECK]: "",
                LOAD_ID_COLUMN[ASSEMBLED_DECK]: "",
                "Component": ref.component,
                "Condition": ref.condition,
                "CG": ref.cg,
                "Speed (kt)": f"{ref.speed_kt:.2f}" if ref.speed_kt is not None else "",
                "Altitude (ft)": f"{ref.altitude_ft:.0f}" if ref.altitude_ft is not None else "",
                "FAR": ref.far_reference,
            }
            by_id[ref.case_id] = row
            rows.append(row)
        column = LOAD_ID_COLUMN[family]
        if not row[column]:
            # The hand is read off the case, not off its id (G-8): the 23.485
            # side pair carries LANDLOAD's own unsuffixed ids, so parsing the id
            # would put both twins in the symmetric block and quote a SUBCASE the
            # assembled deck does not contain.
            row[column] = deck_load_id(ref.case_id, family,
                                       getattr(item, "hand", "") or "")

    for group in groups:
        for item in group:
            add(item, COMPONENT_DECK)
    for item in assembled:
        add(item, ASSEMBLED_DECK)
    return rows


def case_index_rows(project: Project, extra: Sequence = (),
                    assembled: Sequence = ()) -> List[dict]:
    """One row per distinct ``case_id`` across ``project``'s persisted result
    slices, plus any ``extra`` case-carrying objects (e.g. a run's engine
    ``ConditionResult``s or LANDLOAD ``GearReactionCase``s -- transient results
    not stored on ``Project``, so the caller passes them in when available).

    Rows are emitted in first-seen order: ``loads`` slices (wing_net -> body_net
    -> tail_chordwise -> control_surface), then ``envelope.critical`` (SELECT's
    own conditions -- since M4-2 a wing condition and the WINGINER/NETLOADS
    distribution derived from it share one ``case_id``, so the dedupe collapses
    them to a single row), then ``extra``, then ``assembled`` (the assembled
    full-span deck's own cases, which fill the assembled deck-number column --
    see :func:`case_index_rows_from`).
    """
    groups: List[Sequence] = []
    if project.loads is not None:
        groups += [project.loads.wing_net, project.loads.body_net,
                  project.loads.tail_chordwise, project.loads.control_surface]
    if project.envelope is not None and project.envelope.critical is not None:
        groups.append(project.envelope.critical.conditions)
    groups.append(extra)
    return case_index_rows_from(*groups, assembled=assembled)


_CASE_INDEX_FIELDS = ["ID", LOAD_ID_COLUMN[COMPONENT_DECK],
                      LOAD_ID_COLUMN[ASSEMBLED_DECK], "Component", "Condition",
                      "CG", "Speed (kt)", "Altitude (ft)", "FAR"]


def _rows_to_csv(rows: List[dict], header_comment: str = "") -> str:
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CASE_INDEX_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return header_comment + buf.getvalue()


def case_index_csv(project: Project, extra: Sequence = (), header_comment: str = "",
                   assembled: Sequence = ()) -> str:
    """The case-index table (ID -> full definition) as CSV text, from ``project``'s
    persisted result slices."""
    return _rows_to_csv(case_index_rows(project, extra=extra, assembled=assembled),
                        header_comment)


def case_index_csv_from(*groups: Sequence, header_comment: str = "",
                        assembled: Sequence = ()) -> str:
    """The case-index table as CSV text, from explicit case-carrying object groups
    (for a caller -- e.g. the Export page -- that recomputes results live rather
    than reading them off ``Project``)."""
    return _rows_to_csv(case_index_rows_from(*groups, assembled=assembled),
                        header_comment)


_SAFETY_FACTOR_FIELDS = ["Family", "FAR", "Load class", "SF", "Derived SF",
                         "Status", "Basis"]


def safety_factors_csv(project: Project, header_comment: str = "") -> str:
    """The governing safety-factor table as CSV text (M4-8 / decision G-11).

    The companion file for the report's governing-factors section: it travels in
    the bundle and the manifest, stamped like every other channel, so the factor
    behind an exported deck is legible without the report beside it. ``Derived SF``
    is the regulation's own value, kept next to ``SF`` precisely so an override is
    self-evident in the file rather than only in the prose."""
    from ..safety_factors import GoverningTable

    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_SAFETY_FACTOR_FIELDS)
    writer.writeheader()
    for r in GoverningTable.for_project(project).rows:
        writer.writerow({"Family": r.label, "FAR": r.far_reference,
                         "Load class": r.load_class, "SF": f"{r.factor:g}",
                         "Derived SF": f"{r.derived_factor:g}",
                         "Status": r.status, "Basis": r.basis})
    return header_comment + buf.getvalue()


def write_safety_factors_csv(project: Project, path: str,
                             header_comment: str = "") -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(safety_factors_csv(project, header_comment))


# The row keys -- the stable programmatic vocabulary ``gear_report_rows``
# returns and the tests read. The *file* header is built per unit set by
# ``_gear_report_headers`` so the CSV states its own units (R6-C2); keeping the
# keys bare is what lets a consumer of the rows not care which system a bundle
# was rendered in.
_GEAR_REPORT_FIELDS = [
    "ID", "Case", "Condition", "FAR", "Loading", "Design weight",
    "Leg", "Wheel", "Carrier",
    "Strut state", "Ground angle (deg)", "Stroke", "Stroke (%)",
    "Patch X", "Patch Y", "Patch Z",
    "Ground-line V", "Ground-line D", "Ground-line S",
    "Datum Fx", "Datum Fy", "Datum Fz",
    "Ref point X", "Ref point Y", "Ref point Z",
    "Transfer Mx", "Transfer My", "Transfer Mz",
    "Leg weight", "Leg inertia Fz", "Net Fz above trunnion",
    "SF",
]


def _gear_report_headers(u: DeliverableUnits) -> List[str]:
    """The gear CSV's header row for unit set ``u`` (R6-C2).

    Every dimensional column carries its unit and, if it is a load, its ``-ULT``
    marker -- the same D-21 rule the span CSV follows, so this file states its
    own units instead of leaving them to the methods stamp. The weights
    (``Design weight``, ``Leg weight``) are inputs, not factored loads, so they
    carry the plain force unit; ``SF`` is the last column, exactly as on every
    sibling channel.
    """
    ln, fo = u.length.label, u.force.label
    fu, mu = _ult(fo), _ult(u.moment.label)
    labels = {
        "Design weight": f"Design weight ({fo})",
        "Stroke": f"Stroke ({ln})",
        "Patch X": f"Patch X ({ln})", "Patch Y": f"Patch Y ({ln})",
        "Patch Z": f"Patch Z ({ln})",
        "Ground-line V": f"Ground-line V ({fu})",
        "Ground-line D": f"Ground-line D ({fu})",
        "Ground-line S": f"Ground-line S ({fu})",
        "Datum Fx": f"Datum Fx ({fu})", "Datum Fy": f"Datum Fy ({fu})",
        "Datum Fz": f"Datum Fz ({fu})",
        "Ref point X": f"Ref point X ({ln})",
        "Ref point Y": f"Ref point Y ({ln})",
        "Ref point Z": f"Ref point Z ({ln})",
        "Transfer Mx": f"Transfer Mx ({mu})",
        "Transfer My": f"Transfer My ({mu})",
        "Transfer Mz": f"Transfer Mz ({mu})",
        "Leg weight": f"Leg weight ({fo})",
        "Leg inertia Fz": f"Leg inertia Fz ({fu})",
        "Net Fz above trunnion": f"Net Fz above trunnion ({fu})",
    }
    return [labels.get(f, f) for f in _GEAR_REPORT_FIELDS]


def gear_report_rows(project: Project, units: DeliverableUnits = None,
                     safety_factor: float = None) -> List[dict]:
    """The gear load report: one row per case per leg (decision G-12).

    **A free body, not a load list.** Each row states the reaction where LANDLOAD
    computes it -- the tyre contact patch, in the ground-line frame the manual
    prints and a gear engineer reads -- together with the strut state, ground
    angle and stroke it was computed at, and then the *same* reaction where the
    airframe receives it: the gear reference point, in airplane axes, with the
    lever-arm couple that carried it there. Both ends of the leg, so the two G-12
    artifacts are provably one load seen from two sides.

    **All 33 cases**, against the assembled deck's 24. The 23.499 supplementary
    nose-wheel family has no airplane equilibrium to assemble, but it is a
    gear-design case and this report is where it was always aimed -- the two
    artifacts carry different case sets by design, and each says so.

    ``Leg inertia Fz`` is the leg's own weight at the case's vertical ground-line
    load factor and is what closes the free body; ``Net Fz above trunnion`` is the
    reaction less that. Both are blank when no leg weight is entered (G-12a),
    which shows the free body **open** rather than closing it against a guess.
    See :data:`sloads.gear_loads.UNSPRUNG_NOTE` for the limit on what the inertia
    term means -- it is not a gear design load.

    Per the load-output contract, every row states its ``SF`` (R6-C2), and the
    ``Wheel`` column says which wheel a ``main`` row describes: the starboard
    one of the pair, its port twin being the mirror (R6-C4).
    """
    from ..gear_loads import MAIN, gear_case_loads
    from ..safety_factors import table_for

    u = units or deliverable_units(UnitSystem.IMPERIAL, Channel.SOLVER)
    table = table_for(project)
    rows: List[dict] = []
    for case in gear_case_loads(project):
        sf = (safety_factor if safety_factor is not None
              else table.factor_for(case).factor)
        for leg in case.legs:
            if not any(leg.airplane) and not any(leg.ground_line):
                continue          # this leg carries nothing in this case
            px, py, pz = to_grid(*leg.patch, u)
            nx, ny, nz = to_grid(*leg.node, u)
            gv, gd, gs = to_force(leg.ground_line[0] * sf, leg.ground_line[1] * sf,
                                  leg.ground_line[2] * sf, u)
            fx, fy, fz = to_force(leg.airplane[0] * sf, leg.airplane[1] * sf,
                                  leg.airplane[2] * sf, u)
            mx, my, mz = to_moment(leg.couple[0] * sf, leg.couple[1] * sf,
                                   leg.couple[2] * sf, u)
            net = leg.net_of_inertia
            inertia = ("" if leg.inertia_fz is None else
                       _fmt(to_force(0.0, 0.0, leg.inertia_fz * sf, u)[2]))
            rows.append({
                "ID": case.case_ref.case_id if case.case_ref else "",
                "Case": str(case.case),
                "Condition": case.description,
                "FAR": case.far_reference,
                "Loading": case.cg_name,
                "Design weight": _fmt(case.weight_lb * u.force.factor),
                "Leg": leg.leg,
                # A main row states the starboard wheel of the pair (its patch
                # is at +tread/2); the port twin is the mirror. Said in the
                # file rather than only in a code comment (R6-C4).
                "Wheel": "starboard" if leg.leg == MAIN else "centreline",
                "Carrier": leg.carrier.value if leg.carrier is not None else "",
                "Strut state": leg.strut_state,
                "Ground angle (deg)": f"{leg.ground_angle_deg:.3f}",
                "Stroke": _fmt(leg.stroke_in * u.length.factor),
                "Stroke (%)": f"{leg.stroke_fraction * 100:.1f}",
                "Patch X": _fmt(px), "Patch Y": _fmt(py), "Patch Z": _fmt(pz),
                "Ground-line V": _fmt(gv), "Ground-line D": _fmt(gd),
                "Ground-line S": _fmt(gs),
                "Datum Fx": _fmt(fx), "Datum Fy": _fmt(fy), "Datum Fz": _fmt(fz),
                "Ref point X": _fmt(nx), "Ref point Y": _fmt(ny),
                "Ref point Z": _fmt(nz),
                "Transfer Mx": _fmt(mx), "Transfer My": _fmt(my),
                "Transfer Mz": _fmt(mz),
                "Leg weight": ("" if leg.leg_weight_lb is None else
                               _fmt(leg.leg_weight_lb * u.force.factor)),
                "Leg inertia Fz": inertia,
                "Net Fz above trunnion": ("" if net is None else
                                          _fmt(to_force(0.0, 0.0, net[2] * sf, u)[2])),
                "SF": _sf_str(sf),
            })
    return rows


def gear_report_csv(project: Project, header_comment: str = "",
                    system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """The gear load report as CSV text -- the G-12 companion file.

    Travels in the Export bundle and the manifest, stamped like every other
    channel, so the boundary condition a gear analysis starts from is legible
    without the report beside it. Loads are **ULTIMATE**, per the standing
    load-output contract, at the factor the governing table gives the case
    (``LIMIT (14 CFR 23.471 -- ground loads are limit loads) x 1.5``).
    """
    u = deliverable_units(system, Channel.SOLVER)
    rows = gear_report_rows(project, u)
    buf = _io.StringIO()
    # The header states this bundle's units (R6-C2); the rows keep the bare
    # keys so their programmatic vocabulary is system-independent.
    csv.writer(buf).writerow(_gear_report_headers(u))
    writer = csv.DictWriter(buf, fieldnames=_GEAR_REPORT_FIELDS)
    writer.writerows(rows)
    return header_comment + buf.getvalue()


def write_gear_report_csv(project: Project, path: str, header_comment: str = "",
                          system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    # Rendered **before** the file is opened: this is the one export channel that
    # legitimately refuses (a project with no gear geometry produces no report),
    # and opening first would truncate an existing file -- or leave a new empty
    # one -- on the way to the error. The CLI's contract is that a failed export
    # leaves no partial artifact set.
    text = gear_report_csv(project, header_comment, system)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def write_case_index_csv(project: Project, path: str, extra: Sequence = (),
                         assembled: Sequence = ()) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(case_index_csv(project, extra=extra, assembled=assembled))
