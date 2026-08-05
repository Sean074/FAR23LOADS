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
the root torsion by construction. With the WINGINER quadrature
(``mxx[i] = mxx[i+1] + sz[i+1]*dy`` and ``y[i]-y[0] = i*dy``) the same increments
reproduce the root bending exactly as ``sum(dFz * (y - y_root))`` -- the
force/moment-closure guarantee the C4 acceptance test checks.

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
from typing import List, Sequence, Union

from ..constants import ULTIMATE_FACTOR
from ..models import (
    BodyLoadResult,
    ControlSurfaceLoadResult,
    Project,
    TailChordResult,
    WingLoadResult,
    WingStationLoad,
)
from ..report import ultimate_units
from ..units import Channel, DeliverableUnits, UnitSystem, deliverable_units
from .coordinates import SBEAM_CID, to_force, to_grid, to_moment, to_pressure
# Single-sourced from the calc that owns the limitation (public symbol, no cycle:
# nothing under sloads/modules imports the export bridge).
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
                      ControlSurfaceLoadResult]) -> float:
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

# GRID id of the clamped wing-root node in the stick model; station nodes follow.
_ROOT_GID = 1
_STATION_GID_BASE = 1  # station i -> GID _STATION_GID_BASE + 1 + i (= 2, 3, ...)


def _fmt(val: float) -> str:
    """Format a load/coordinate component in NASTRAN 6-digit scientific style."""
    return f"{val:.6E}"


def station_gid(i: int) -> int:
    """GRID id of wing station ``i`` (0 = root), past the clamped root node."""
    return _STATION_GID_BASE + 1 + i


@dataclass
class NodalLoad:
    """One wing station's exported nodal load (the applied FORCE/MOMENT content).

    ``fx``/``fz`` are the applied force components (lb) and ``my`` the applied
    torsion (lb-in) at the torsion-reference-axis point ``(x, y, z)`` (in) --
    the station ``x`` of the source result: 25% chord as computed, or the
    surface LRA after ``net_loads.to_loads_ref_axis`` -- recovered as
    increments of the NETLOADS cumulative table. ``sz``/``mxx``/``myy`` are the
    cumulative shear / bending / torsion at the station, carried through for the
    span-load CSV's engineering columns."""
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


def wing_nodal_loads(result: WingLoadResult) -> List[NodalLoad]:
    """Applied nodal loads for one case, from the cumulative NETLOADS stations.

    The nodal force/torsion at each station is the increment of the cumulative
    shear/torsion to the next station outboard (the last/tip station keeps its
    full value), so the set sums back to the root totals exactly.

    Forces/moments are returned as ULTIMATE loads (LIMIT x the case's
    ``safety_factor``); the scale is uniform within the case, which preserves the
    force/moment-closure guarantee (``sum(dFz) == safety_factor x root``).
    """
    s: List[WingStationLoad] = result.stations
    sf = _sf(result)
    n = len(s)
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


def _sid(sid_base: int, case_index: int) -> int:
    """Load-set id for the ``case_index``-th case (0-based)."""
    return sid_base + case_index


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
    x_h, y_h, z_h, fx_h, fz_h, my_h, sx_h, sz_h, mxx_h, myy_h, mzz_h = fields[2:13]
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        for nl in wing_nodal_loads(r):
            gx, gy, gz = to_grid(nl.x, nl.y, nl.z, u)
            fx, _, fz = to_force(nl.fx, 0.0, nl.fz, u)
            _, my, _ = to_moment(0.0, nl.my, 0.0, u)
            sx, _, sz = to_force(nl.sx, 0.0, nl.sz, u)
            mxx, myy, mzz = to_moment(nl.mxx, nl.myy, nl.mzz, u)
            writer.writerow({
                "Case": r.case, "GID": nl.gid,
                x_h: f"{gx:.3f}", y_h: f"{gy:.3f}", z_h: f"{gz:.3f}",
                fx_h: f"{fx:.1f}", fz_h: f"{fz:.1f}", my_h: f"{my:.0f}",
                sx_h: f"{sx:.1f}", sz_h: f"{sz:.1f}",
                mxx_h: f"{mxx:.0f}", myy_h: f"{myy:.0f}", mzz_h: f"{mzz:.0f}",
                "MyyAxis": r.torsion_axis,
                "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def write_span_load_csv(arg: ResultsArg, path: str, *,
                        system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(span_load_csv(arg, system=system))


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
        mx, my, mz = to_moment(0.0, nl.my, 0.0, u)
        if abs(nl.my) > _TOL:
            lines.append(
                f"MOMENT, {sid}, {nl.gid}, {SBEAM_CID}, 1.0, "
                f"{_fmt(mx)}, {_fmt(my)}, {_fmt(mz)}"
            )
    return lines


def _case_card_block(r: WingLoadResult, sid: int, u: DeliverableUnits) -> List[str]:
    """One case's commented FORCE/MOMENT block (header + cards)."""
    loads = wing_nodal_loads(r)
    sf = _sf(r)
    # loads carry the ULTIMATE (x sf) cumulative totals, so the comment matches the cards.
    _, _, root_sz = to_force(0.0, 0.0, loads[0].sz if loads else 0.0, u)
    _, root_myy, _ = to_moment(0.0, loads[0].myy if loads else 0.0, 0.0, u)
    lines = [
        f"$ SLOADS net wing load -- case {r.case} (Nz={r.nz:g}, Nx={r.nx:g}), SID {sid}",
        f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
        "$ Axes: SLOADS station/butt/waterline -> sbeam CID 0 (identity); "
        f"lengths in {u.length.label}.",
        f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
        f"$ Torsion My/Myy about the {r.torsion_axis} (station X = that axis).",
        f"$ FORCE set sums to root Sz = {root_sz:.1f} {u.force.label}; "
        f"MOMENT(My) set sums to root torsion Myy = {root_myy:.1f} {u.moment.label}.",
    ]
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
    blocks: List[str] = []
    for idx, r in enumerate(results):
        blocks.append("\n".join(_case_card_block(r, _sid(sid_base, idx), u)))
    return _stamped(header_comment, "\n".join(blocks) + "\n")


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


def stick_model_bdf(arg: ResultsArg, sid_base: int = 1, *,
                    header_comment: str = "",
                    system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """A minimal SOL 101 CBAR stick model carrying the exported wing load sets.

    A clamped cantilever along the wing's torsion reference axis (the station
    ``x`` of the exported loads: 25% chord as computed, or the surface's LRA
    after the boundary transfer): one GRID per station plus a clamped root node,
    a single PBAR/MAT1 (nominal placeholder properties), a CBAR chain, and one
    SUBCASE per case selecting that case's FORCE/MOMENT load set. Geometry is
    shared across cases (same wing); only the load set changes.
    """
    results = _as_results(arg)
    u = _units(system)
    # Station geometry is shared across cases -- take it from the first.
    base_loads = wing_nodal_loads(results[0])
    rx, ry, rz = to_grid(*_root_node(base_loads), units=u)

    head: List[str] = ["SOL 101", "$"]
    for idx, r in enumerate(results):
        sid = _sid(sid_base, idx)
        head += [
            f"SUBCASE {idx + 1}",
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
    for nl in base_loads:
        gx, gy, gz = to_grid(nl.x, nl.y, nl.z, u)
        bulk.append(f"GRID, {nl.gid}, , {_fmt(gx)}, {_fmt(gy)}, {_fmt(gz)}")

    # Section properties are area / second moment, so they scale as length^2 and
    # length^4 -- derived from the one length factor, never quoted per system.
    e_mod = to_pressure(_MAT1_E, u)
    area = _PBAR_A * u.length.factor ** 2
    inertia = _PBAR_I * u.length.factor ** 4
    torsion_j = _PBAR_J * u.length.factor ** 4
    bulk += [
        "$ --------------------------------------------------------- MATERIAL",
        "$ MAT1, MID, E, G, NU, RHO  (placeholder; reactions are stiffness-independent)",
        f"$ E in {u.pressure.label}; A in {u.length.label}^2; I, J in {u.length.label}^4.",
        f"MAT1, 1, {_fmt(e_mod)}, , {_MAT1_NU}, 0.0",
        "$ ------------------------------------------------------- PROPERTIES",
        "$ PBAR, PID, MID, A, I1, I2, J",
        f"PBAR, 1, 1, {_fmt(area)}, {_fmt(inertia)}, {_fmt(inertia)}, {_fmt(torsion_j)}",
        "$ --------------------------------------------------------- ELEMENTS",
        "$ CBAR, EID, PID, GA, GB, X1, X2, X3  (orientation vector 0,0,1)",
    ]
    # CBAR chain: root node -> station 0 -> station 1 -> ... -> tip.
    prev = _ROOT_GID
    for eid, nl in enumerate(base_loads, start=1):
        bulk.append(f"CBAR, {eid}, 1, {prev}, {nl.gid}, 0.0, 0.0, 1.0")
        prev = nl.gid

    bulk += [
        "$ ------------------------------------------------------- CONSTRAINTS",
        "$ SPC1, SID, C, G  (clamp the root node, all 6 DOF)",
        f"SPC1, 1, 123456, {_ROOT_GID}",
        "$ ------------------------------------------------------------ LOADS",
    ]
    for idx, r in enumerate(results):
        bulk += _case_card_block(r, _sid(sid_base, idx), u)

    return _stamped(header_comment, "\n".join(head + bulk + ["ENDDATA"]) + "\n")


def write_stick_model_bdf(arg: ResultsArg, path: str, sid_base: int = 1, *,
                          header_comment: str = "",
                          system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(stick_model_bdf(arg, sid_base=sid_base,
                                 header_comment=header_comment, system=system))


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
_BODY_GID_BASE = 1001         # fuselage mass stations + the tail air load: 1001-1500
_BODY_CARRY_GID_BASE = 1501   # carry-through / fallback correction nodes: 1501-2000
_BODY_GID_BLOCK = 500         # capacity of each block (tail GIDs start at 2001)

#: ``BodyStationLoad.source`` values that belong to the reaction-node GID block.
_BODY_REACTION_SOURCES = ("carry", "correction")


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
    for s in result.stations:
        if s.source in _BODY_REACTION_SOURCES:
            gids.append(_BODY_CARRY_GID_BASE + n_reaction)
            n_reaction += 1
        else:
            gids.append(_BODY_GID_BASE + n_mass)
            n_mass += 1
    if max(n_mass, n_reaction) > _BODY_GID_BLOCK:
        raise ValueError(
            f"body export: {n_mass} mass and {n_reaction} reaction stations "
            f"exceed the {_BODY_GID_BLOCK}-GID block (would collide with the "
            "tail GIDs at 2001)"
        )
    return gids


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
        for gid, s in zip(body_station_gids(r), r.stations):
            x, _, _ = to_grid(s.x, 0.0, 0.0, u)
            _, _, fz = to_force(0.0, 0.0, s.fz * sf, u)
            _, _, sz = to_force(0.0, 0.0, s.sz * sf, u)
            _, myy, _ = to_moment(0.0, s.myy * sf, 0.0, u)
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
    :data:`~sloads.modules.body_loads.CLOSURE_ARTIFACT_CAVEAT`."""
    results = _body_results(arg)
    u = _units(system)
    blocks: List[str] = []
    for idx, r in enumerate(results):
        sid = sid_base + idx
        sf = _sf(r)
        _, _, total_fz = to_force(0.0, 0.0, sum(s.fz for s in r.stations) * sf, u)
        _, terminal_myy, _ = to_moment(0.0, r.stations[-1].myy * sf, 0.0, u)
        lines = [
            f"$ SLOADS net fuselage load -- case {r.case}, SID {sid}",
            f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
            f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
            f"$ Applied Fz set sums to {total_fz:.2f} {u.force.label} "
            "(vertical equilibrium).",
            f"$ Terminal Myy {terminal_myy:.2f} {u.moment.label} "
            "(moment equilibrium).",
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
    return _stamped(header_comment, "\n".join(blocks) + "\n")


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


# --------------------------------------------------------------------------- #
# Tail chordwise-load export (Step C7, TAILDIST)
# --------------------------------------------------------------------------- #
# The chordwise tail distribution (Ch 10) is a pressure profile (lb/in^2) on the
# average tail chord at five chord stations. The export emits the profile as a CSV
# and a per-station FORCE set scaled so its total equals the condition's tail load
# (LT25 + LT50) -- a determinate, checkable load set for the tail beam in sbeam.
_TAIL_GID_BASE = 2001  # tail chordwise-station GIDs (disjoint from wing/body GIDs)


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


def _tail_nodal_forces(r: TailChordResult) -> List[float]:
    """Per-station vertical forces (lb) from the chordwise pressures, scaled so the
    set sums to the total tail load ``LT25 + LT50`` (trapezoidal chord tributaries)."""
    stations = sorted(r.stations, key=lambda s: s.x)
    n = len(stations)
    widths = []
    for i, s in enumerate(stations):
        lo = stations[i - 1].x if i > 0 else s.x
        hi = stations[i + 1].x if i + 1 < n else s.x
        widths.append((hi - lo) / 2.0)
    raw = [s.psi * w for s, w in zip(stations, widths)]
    total_raw = sum(raw)
    total = (r.lt25 + r.lt50) * _sf(r)  # ULTIMATE tail load
    scale = (total / total_raw) if abs(total_raw) > _TOL else 0.0
    return [v * scale for v in raw]


def tail_chordwise_csv(arg, header_comment: str = "", *,
                       system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """Chordwise tail-load CSV: one row per chord station per critical tail
    condition (component, chord station X, net pressure PSI, scaled nodal Fz). Loads
    are ULTIMATE; ``SF`` is the case's limit->ultimate factor they were scaled by."""
    results = _tail_results(arg)
    u = _units(system)
    x_h = f"X ({u.length.label})"
    psi_h = f"PSI ({_ult(u.pressure.label)})"
    fo = _ult(u.force.label)
    fz_h, lt25_h, lt50_h = f"Fz ({fo})", f"LT25 ({fo})", f"LT50 ({fo})"
    buf = _io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["Case", "Component", "GID", x_h, psi_h, fz_h,
                         lt25_h, lt50_h, "SF"])
    writer.writeheader()
    for r in results:
        sf = _sf(r)
        forces = _tail_nodal_forces(r)
        stations = sorted(r.stations, key=lambda s: s.x)
        _, _, lt25 = to_force(0.0, 0.0, r.lt25 * sf, u)
        _, _, lt50 = to_force(0.0, 0.0, r.lt50 * sf, u)
        for i, (s, fz) in enumerate(zip(stations, forces)):
            x, _, _ = to_grid(s.x, 0.0, 0.0, u)
            _, _, fz_out = to_force(0.0, 0.0, fz, u)
            writer.writerow({
                "Case": r.case, "Component": r.component, "GID": _TAIL_GID_BASE + i,
                x_h: f"{x:.3f}", psi_h: f"{to_pressure(s.psi * sf, u):.4f}",
                fz_h: f"{fz_out:.1f}",
                lt25_h: f"{lt25:.2f}", lt50_h: f"{lt50:.2f}",
                "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def tail_force_moment_cards(arg, sid_base: int = 1, *,
                            header_comment: str = "",
                            system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """FORCE bulk-data cards for the chordwise tail loads (one SID per condition);
    each set's applied Fz sums to the total tail load ``LT25 + LT50``."""
    results = _tail_results(arg)
    u = _units(system)
    blocks: List[str] = []
    for idx, r in enumerate(results):
        sid = sid_base + idx
        sf = _sf(r)
        forces = _tail_nodal_forces(r)
        _, _, total = to_force(0.0, 0.0, sum(forces), u)
        _, _, lt_total = to_force(0.0, 0.0, (r.lt25 + r.lt50) * sf, u)
        lines = [
            f"$ SLOADS chordwise {r.component} load -- case {r.case}, SID {sid}",
            f"$ Case ID: {r.case_ref.case_id}" if r.case_ref else "$ Case ID: (none)",
            f"$ Loads are ULTIMATE (limit x SF={_sf_str(sf)}).",
            f"$ Applied Fz set sums to {total:.1f} {u.force.label} "
            f"(= {_sf_str(sf)} x (LT25 + LT50) = {lt_total:.1f} {u.force.label}).",
        ]
        for i, fz in enumerate(forces):
            fx2, fy2, fz2 = to_force(0.0, 0.0, fz, u)
            if abs(fz) > _TOL:
                lines.append(
                    f"FORCE, {sid}, {_TAIL_GID_BASE + i}, {SBEAM_CID}, 1.0, "
                    f"{_fmt(fx2)}, {_fmt(fy2)}, {_fmt(fz2)}"
                )
        blocks.append("\n".join(lines))
    return _stamped(header_comment, "\n".join(blocks) + "\n")


def write_tail_chordwise_csv(arg, path: str, *,
                             system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(tail_chordwise_csv(arg, system=system))


def write_tail_force_moment_cards(arg, path: str, sid_base: int = 1, *,
                                  header_comment: str = "",
                                  system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(tail_force_moment_cards(arg, sid_base=sid_base,
                                         header_comment=header_comment, system=system))


# --------------------------------------------------------------------------- #
# Control-surface simplified loads (AILERON / FLAPLOAD / TABLOADS, Step C8)
# --------------------------------------------------------------------------- #
# Each control-surface condition carries a simplified chordwise pressure profile
# (fractional chord 0..1) and a critical total load; the export builds a per-station
# FORCE set scaled so its sum equals that critical load -- a determinate, checkable
# load set for the control-surface beam in sbeam.
_CS_GID_BASE = 3001  # control-surface chord-station GIDs (disjoint from wing/body/tail)


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
    n = len(stations)
    widths = []
    for i, s in enumerate(stations):
        lo = stations[i - 1].x if i > 0 else s.x
        hi = stations[i + 1].x if i + 1 < n else s.x
        widths.append((hi - lo) / 2.0)
    raw = [s.psi * w for s, w in zip(stations, widths)]
    total_raw = sum(raw)
    total = r.load_lb * _sf(r)  # ULTIMATE critical surface load
    scale = (total / total_raw) if abs(total_raw) > _TOL else 0.0
    return [v * scale for v in raw]


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
                "Surface": r.surface, "Case": r.case, "GID": _CS_GID_BASE + i,
                "X (chord frac)": f"{s.x:.3f}",
                psi_h: f"{to_pressure(s.psi * sf, u):.4f}", fz_h: f"{fz_out:.1f}",
                load_h: f"{load:.2f}", "SF": f"{_sf_str(sf)}",
            })
    return header_comment + buf.getvalue()


def control_surface_force_moment_cards(arg, sid_base: int = 1, *,
                                       header_comment: str = "",
                                       system: UnitSystem = UnitSystem.IMPERIAL) -> str:
    """FORCE bulk-data cards for the control-surface loads (one SID per condition);
    each set's applied Fz sums to the critical surface load."""
    results = _control_results(arg)
    u = _units(system)
    blocks: List[str] = []
    for idx, r in enumerate(results):
        sid = sid_base + idx
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
                    f"FORCE, {sid}, {_CS_GID_BASE + i}, {SBEAM_CID}, 1.0, "
                    f"{_fmt(fx2)}, {_fmt(fy2)}, {_fmt(fz2)}"
                )
        blocks.append("\n".join(lines))
    return _stamped(header_comment, "\n".join(blocks) + "\n")


def write_control_surface_csv(arg, path: str, *,
                              system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(control_surface_csv(arg, system=system))


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
def case_index_rows_from(*groups: Sequence) -> List[dict]:
    """One row per distinct ``case_id`` across any number of case-carrying object
    groups (anything with a ``.case_ref`` -- ``WingLoadResult``, ``BodyLoadResult``,
    ``TailChordResult``, ``ControlSurfaceLoadResult``, ``CriticalCondition``,
    engine ``ConditionResult``, LANDLOAD ``GearReactionCase``, ...). Rows are
    emitted in first-seen order across the groups, in the order given; a
    ``case_id`` seen again (the same case appearing in multiple deliverables --
    e.g. a wing case in ``wing_air``, ``wing_inertia`` and ``wing_net``) is not
    repeated.
    """
    seen = set()
    rows: List[dict] = []
    for group in groups:
        for item in group:
            ref = getattr(item, "case_ref", None)
            if ref is None or ref.case_id in seen:
                continue
            seen.add(ref.case_id)
            rows.append({
                "ID": ref.case_id,
                "Component": ref.component,
                "Condition": ref.condition,
                "CG": ref.cg,
                "Speed (kt)": f"{ref.speed_kt:.2f}" if ref.speed_kt is not None else "",
                "Altitude (ft)": f"{ref.altitude_ft:.0f}" if ref.altitude_ft is not None else "",
                "FAR": ref.far_reference,
            })
    return rows


def case_index_rows(project: Project, extra: Sequence = ()) -> List[dict]:
    """One row per distinct ``case_id`` across ``project``'s persisted result
    slices, plus any ``extra`` case-carrying objects (e.g. a run's engine
    ``ConditionResult``s or LANDLOAD ``GearReactionCase``s -- transient results
    not stored on ``Project``, so the caller passes them in when available).

    Rows are emitted in first-seen order: ``loads`` slices (wing_net -> body_net
    -> tail_chordwise -> control_surface), then ``envelope.critical`` (SELECT's
    own conditions, including its separate wing sequence -- see the accepted-gap
    note in ``docs/30_future/00_backlog.md`` Step D1), then ``extra``.
    """
    groups: List[Sequence] = []
    if project.loads is not None:
        groups += [project.loads.wing_net, project.loads.body_net,
                  project.loads.tail_chordwise, project.loads.control_surface]
    if project.envelope is not None and project.envelope.critical is not None:
        groups.append(project.envelope.critical.conditions)
    groups.append(extra)
    return case_index_rows_from(*groups)


_CASE_INDEX_FIELDS = ["ID", "Component", "Condition", "CG", "Speed (kt)", "Altitude (ft)", "FAR"]


def _rows_to_csv(rows: List[dict], header_comment: str = "") -> str:
    buf = _io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CASE_INDEX_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return header_comment + buf.getvalue()


def case_index_csv(project: Project, extra: Sequence = (), header_comment: str = "") -> str:
    """The case-index table (ID -> full definition) as CSV text, from ``project``'s
    persisted result slices."""
    return _rows_to_csv(case_index_rows(project, extra=extra), header_comment)


def case_index_csv_from(*groups: Sequence, header_comment: str = "") -> str:
    """The case-index table as CSV text, from explicit case-carrying object groups
    (for a caller -- e.g. the Export page -- that recomputes results live rather
    than reading them off ``Project``)."""
    return _rows_to_csv(case_index_rows_from(*groups), header_comment)


def write_case_index_csv(project: Project, path: str, extra: Sequence = ()) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(case_index_csv(project, extra=extra))
