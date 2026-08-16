"""LRA model **import**: an external beam line becomes the loads' target
(step 12, note 24 R-10; implementation note 25 §6).

The export half writes the geometry-derived LRA model; this half accepts a
consumer's own beam model -- a ``GRID``/``CBAR`` BDF subset -- and **uses its
node line as the LRA**: the same balanced-case load sets, the same LM-1
nearest-node transfer with the exact lever-arm couple, landed on the imported
nodes under the imported GIDs (the imported numbering wins). The emitted file
is subcase map + ``FORCE``/``MOMENT`` cards only, ready to splice into the
model it was routed against.

How the import knows which node is which
----------------------------------------
The ``$ SLOADS-NODE <family> <side>`` tags (decision BM-5) -- the same
contract the exported model carries, so an export -> import round trip maps
every family by identity. A model with no tags (or a family it does not tag)
still works: every load falls back to nearest-imported-node over the whole
node set, **marked assumed in the header**, which is the note's stated
fallback. A sidecar map ``{"<family> <side>": gid}`` is accepted as the tag
substitute for a consumer who will not edit their deck.

Because the imported line *is* the consumer's elastic axis, the torsion
reference question is closed by construction and the header says so (R-7d).

Validation
----------
Every tagged node is checked against the geometry-derived position for its
family (the wing SOB, the posts, the fin root...) at
:data:`LRA_IMPORT_TOL_IN`; divergence **raises**, naming both points -- the
T1 planform-validator pattern. An imported model that disagrees with the
project about where the side of body is would silently misstate every
internal load this deliverable exists to state.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ..models import BalancedCaseResult, Project
from ..modules.balance import build_balanced_cases
from ..units import Channel, UnitSystem, deliverable_units
from .balanced_deck import case_sids
from .coordinates import SBEAM_CID, to_force, to_moment, transfer_couple
from .equilibrium import parse_cards
from .lra_model import (LraModel, LraNode, LraRefusal, _dist2, _member_key,
                        build_lra_model)
from .sbeam_bridge import _comment, _fmt, _sf_str, _stamped

Vec3 = Tuple[float, float, float]

_TOL = 1e-9

#: How far (in) an imported tagged node may sit from the geometry-derived
#: position of its family before the import fails loudly. Two inches is a
#: modelling difference; two feet is a different airplane.
LRA_IMPORT_TOL_IN = 2.0

#: Families whose geometry-derived position the validation compares against.
#: Chain-station families (untagged) have no single reference point.
_VALIDATED_FAMILIES = ("lra-sob", "lra-post", "lra-fin-root", "lra-attach",
                      "lra-centre")


@dataclass
class ImportedModel:
    """An external ``GRID``/``CBAR`` model, parsed for load routing.

    ``tags`` maps ``"<family> <side>"`` -> GID -- from ``$ SLOADS-NODE``
    comment lines (each applies to the next ``GRID`` card) or from a sidecar
    map. ``nodes`` is every imported GRID.
    """
    nodes: List[LraNode] = field(default_factory=list)
    cbars: List[Tuple[int, int, int]] = field(default_factory=list)
    tags: Dict[str, int] = field(default_factory=dict)

    def tagged(self, family: str) -> List[LraNode]:
        gids = {gid for key, gid in self.tags.items()
                if key.split()[0] == family}
        return [n for n in self.nodes if n.gid in gids]


def read_lra_model(text: str,
                   sidecar: Optional[Dict[str, int]] = None) -> ImportedModel:
    """Parse an external beam model's ``GRID``/``CBAR`` subset + node tags.

    ``$ SLOADS-NODE <family> <side>`` comment lines tag the next ``GRID``
    card, exactly as the exporter writes them; ``sidecar`` entries
    (``{"lra-sob R": 7001, ...}``) override/extend the in-deck tags. Raises
    when the model carries no ``GRID`` at all -- there is nothing to route
    loads onto.
    """
    grids, cbars, _spc, _f, _m = parse_cards(text)
    if not grids:
        raise ValueError(
            "imported model carries no GRID cards -- there are no nodes to "
            "use as the LRA")
    tags: Dict[str, int] = {}
    pending: Optional[str] = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("$ SLOADS-NODE"):
            parts = line.split()
            # "$ SLOADS-NODE family side" -> "family side" (side optional)
            pending = " ".join(parts[2:4])
        elif line and not line.startswith("$"):
            if pending and line.split(",")[0].strip().upper() == "GRID":
                gid = int(line.split(",")[1])
                tags[pending] = gid
            pending = None
    if sidecar:
        tags.update(sidecar)
    by_gid = {}
    for key, gid in tags.items():
        if gid not in grids:
            raise ValueError(
                f"tag {key!r} names GID {gid}, which has no GRID card in the "
                "imported model")
        by_gid[gid] = key
    nodes = [LraNode(gid, pos,
                     by_gid.get(gid, "").split()[0] if gid in by_gid else "",
                     (by_gid[gid].split() + [""])[1] if gid in by_gid else "")
             for gid, pos in sorted(grids.items())]
    return ImportedModel(nodes=nodes, cbars=list(cbars), tags=tags)


def _reference_positions(model: LraModel) -> Dict[str, Vec3]:
    """``{"family side": position}`` of the geometry-derived named nodes."""
    return {f"{n.family} {n.side}".strip(): n.pos
            for n in model.nodes if n.family in _VALIDATED_FAMILIES}


def validate_imported_model(project: Project,
                            imported: ImportedModel) -> List[str]:
    """Check every tagged import node against the geometry-derived skeleton.

    Raises on divergence beyond :data:`LRA_IMPORT_TOL_IN`, naming both
    points. Returns the validation notes (which tags were checked; which
    geometry families the import does not tag). A project the geometry-derived
    model itself refuses (:class:`~sloads.export.lra_model.LraRefusal`) skips
    the position check -- there is nothing to compare against -- and says so.
    """
    try:
        reference = _reference_positions(build_lra_model(project))
    except LraRefusal as exc:
        return [f"geometry positions not validated -- the geometry-derived "
                f"model does not build for this project ({exc})"]
    notes: List[str] = []
    checked = 0
    for key, gid in imported.tags.items():
        ref = reference.get(key)
        if ref is None:
            continue
        node = next(n for n in imported.nodes if n.gid == gid)
        dist = _dist2(node.pos, ref) ** 0.5
        if dist > LRA_IMPORT_TOL_IN:
            raise ValueError(
                f"imported node {gid} is tagged {key!r} at "
                f"({node.pos[0]:.2f}, {node.pos[1]:.2f}, {node.pos[2]:.2f}) "
                f"but the project's geometry puts that node at "
                f"({ref[0]:.2f}, {ref[1]:.2f}, {ref[2]:.2f}) -- "
                f"{dist:.2f} in apart, over the {LRA_IMPORT_TOL_IN:.1f} in "
                "tolerance. The imported model and the project disagree "
                "about the airplane; fix one of them rather than exporting "
                "loads onto the wrong structure")
        checked += 1
    notes.append(f"{checked} tagged node(s) validated against the "
                 f"geometry-derived positions at +-{LRA_IMPORT_TOL_IN:.1f} in")
    missing = sorted(set(reference) - set(imported.tags))
    if missing:
        notes.append(
            "families the import does not tag (their loads route "
            f"nearest-node, ASSUMED): {', '.join(missing)}")
    return notes


def _routing_members(imported: ImportedModel) -> Dict[str, List[LraNode]]:
    """The LM-7 member table for an imported node set.

    An import cannot state which nodes form each chain, so the member table
    is built from the **tags**: the gear family routes gear loads, the sob/
    attach/fin tags anchor nothing by themselves, and every other member key
    falls back to ``all`` -- nearest-imported-node, the note's marked-assumed
    fallback. This keeps the resultant exact (LM-1) whatever the import
    looks like; what a richer tag set buys is better *internal* attribution.
    """
    members: Dict[str, List[LraNode]] = {"all": list(imported.nodes)}
    gear = imported.tagged("lra-gear")
    if gear:
        members["gear"] = gear
    return members


def lra_loads_on_imported_model(project: Project, imported: ImportedModel, *,
                                header_comment: str = "",
                                system: UnitSystem = UnitSystem.IMPERIAL,
                                cases: Sequence[BalancedCaseResult] = ()
                                ) -> str:
    """The balanced cases' load sets, transferred onto an imported model.

    The emitted text is subcase map + ``FORCE``/``MOMENT`` cards under the
    **imported GIDs** -- no geometry, no elements, no constraints: it splices
    into the model it was routed against. Same SIDs, same ULTIMATE boundary
    scaling as the assembled balanced deck and the exported LRA model, so a
    consumer can trace one case across all three artifacts by number.
    """
    validation = validate_imported_model(project, imported)
    cases = list(cases) or build_balanced_cases(project, [])
    if not cases:
        raise ValueError("no balanced case could be assembled -- there is no "
                         "load set to transfer onto the imported model")
    u = deliverable_units(system, Channel.SOLVER)
    sids = case_sids(cases)
    members = _routing_members(imported)

    lines: List[str] = []
    lines += _comment(
        "SLOADS loads on an IMPORTED beam model (step 12 import): the "
        "assembled balanced cases' load sets transferred onto the imported "
        "GRID set by the LM-1 nearest-node rule with the exact lever-arm "
        "couple -- identical resultant per case. GIDs are the imported "
        "model's own; splice these cards into it.")
    lines += _comment(
        "The imported beam line IS the consumer's elastic axis, so torsion "
        "is about it by construction (note 24 R-7d).")
    for note in validation:
        lines += _comment("VALIDATION: " + note)
    lines += _comment(
        "Routing: families the import tags route by identity; everything "
        "else lands on the nearest imported node (marked-assumed fallback, "
        "note 24 R-10).")
    lines.append("$ ------------------------------------------------- CASE MAP")
    for sid, case in zip(sids, cases):
        entry = (f"SUBCASE/SID {sid} = "
                 f"{case.case_ref.case_id if case.case_ref else '(no id)'}"
                 f" -- {case.label}{('-' + case.hand) if case.hand else ''}")
        lines += [f"$ {ln}" for ln in textwrap.wrap(entry, width=70,
                                                    subsequent_indent="    ")]
    for sid, case in zip(sids, cases):
        sf = case.safety_factor
        lines.append("$")
        lines += _comment(
            f"Case {case.case_ref.case_id if case.case_ref else case.label} "
            f"-- SID {sid}, ULTIMATE (limit x SF={_sf_str(sf)}).")
        acc: Dict[int, Tuple[List[float], List[float]]] = {}
        for load in case.loads:
            member = members.get(_member_key(load, members), members["all"])
            p = (load.x, load.y, load.z)
            node = min(member, key=lambda n: _dist2(n.pos, p))
            f = (load.fx, load.fy, load.fz)
            cx, cy, cz = transfer_couple(p, node.pos, f)
            force, moment = acc.setdefault(node.gid, ([0.0] * 3, [0.0] * 3))
            force[0] += load.fx
            force[1] += load.fy
            force[2] += load.fz
            moment[0] += load.mx + cx
            moment[1] += load.my + cy
            moment[2] += load.mz + cz
        for gid in sorted(acc):
            force, moment = acc[gid]
            fx, fy, fz = to_force(force[0] * sf, force[1] * sf,
                                  force[2] * sf, u)
            if max(abs(v) for v in force) * sf > _TOL:
                lines.append(f"FORCE, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                             f"{_fmt(fx)}, {_fmt(fy)}, {_fmt(fz)}")
            mx, my, mz = to_moment(moment[0] * sf, moment[1] * sf,
                                   moment[2] * sf, u)
            if max(abs(v) for v in moment) * sf > _TOL:
                lines.append(f"MOMENT, {sid}, {gid}, {SBEAM_CID}, 1.0, "
                             f"{_fmt(mx)}, {_fmt(my)}, {_fmt(mz)}")
    return _stamped(header_comment, "\n".join(lines) + "\n")


def write_lra_loads_on_imported_model(project: Project, model_path: str,
                                      out_path: str, *,
                                      header_comment: str = "",
                                      system: UnitSystem = UnitSystem.IMPERIAL
                                      ) -> None:
    """Read a consumer's beam-model BDF and write the transferred load cards."""
    with open(model_path, encoding="utf-8") as fh:
        imported = read_lra_model(fh.read())
    text = lra_loads_on_imported_model(project, imported,
                                       header_comment=header_comment,
                                       system=system)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)


__all__ = [
    "LRA_IMPORT_TOL_IN",
    "ImportedModel",
    "lra_loads_on_imported_model",
    "read_lra_model",
    "validate_imported_model",
    "write_lra_loads_on_imported_model",
]
