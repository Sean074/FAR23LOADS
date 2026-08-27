"""Selector names -- the fields the calc keys on -- as one owner (#63, PB-5/PB-9).

The original suite expressed these things by *position*: which ``*GEOM.INP``
a planform came from, which of FLTLOADS' screens a CG case was typed into,
which coefficient set is the flapped one. This model carries each as a
**name** (``geometry.surfaces[].name``, ``weight.cg_cases[].name``,
``aero_coeffs.cruise.name`` / ``flaps_down.name``), and downstream code uses
the name as a dictionary key. Two rows with one name therefore collapse into
one entry, and before this module nothing said so: blanking every CG-case
name on the GA-6 changed TAILDIST's chordwise table in 7 of 13 rows while
every page reported success (review 2026-08-22 PB-5).

Three rules, stated once:

* :func:`keyed` builds the dictionary the consumers read and **refuses a
  duplicate** instead of collapsing it -- ``select.py`` reads its CG cases
  and coefficient sets through it, so the collapse cannot happen silently
  anywhere.
* :func:`duplicate_selectors` is the same check asked of a whole project, in
  the form's words, so a page can withhold its results before a module runs.
* :func:`seed_name` says what a freshly created row is called -- the first
  surface is ``wing`` because everything downstream keys on it (PB-9), CG
  cases are ``CG1 … CGn``, the coefficient sets ``CRUISE`` / ``LANDING`` --
  instead of ``""``, which the user had to notice and replace.

Name identity is :func:`~sloads.models.same_name`'s (case and edge spaces
forgiven), the rule ``by_name`` reads; :func:`duplicates` applies the same
folding.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Sequence, Tuple, TypeVar

from .models import Project

T = TypeVar("T")

#: Registry path of each selector name -> the name a new row gets, by index.
#: Guarded in ``tests/test_selectors.py``: every ``supplied`` name path in the
#: field registry has an entry here, so a new selector cannot seed blank.
NAME_SEEDS: Dict[str, Callable[[int], str]] = {
    "geometry.surfaces[].name": lambda i: "wing" if i == 0 else f"surface{i + 1}",
    # Mirrors the geometry seed: an aero row pairs with the planform of the
    # same name (#98; note 36 OV-8 derives rows for unpaired planforms).
    "aero.surfaces[].name": lambda i: "wing" if i == 0 else f"surface{i + 1}",
    "weight.cg_cases[].name": lambda i: f"CG{i + 1}",
    "aero_coeffs.cruise.name": lambda _i: "CRUISE",
    "aero_coeffs.flaps_down.name": lambda _i: "LANDING",
}


def seed_name(path: str, index: int = 0) -> str:
    """The name a new row at ``path`` is created with (``""`` if none is declared)."""
    seed = NAME_SEEDS.get(path)
    return seed(index) if seed is not None else ""


def _key(name: str) -> str:
    return name.strip().casefold()


def duplicates(names: Sequence[str]) -> List[str]:
    """The names that appear more than once (by :func:`same_name`), first spelling, in order."""
    seen: Dict[str, str] = {}
    out: List[str] = []
    for name in names:
        k = _key(name)
        if k in seen and seen[k] not in out:
            out.append(seen[k])
        seen.setdefault(k, name)
    return out


def keyed(items: Sequence[T], name_of: Callable[[T], str], what: str) -> Dict[str, T]:
    """``{name: item}`` for the consumers that look a selector up -- or a
    ``ValueError`` naming the duplicate, never a dictionary missing a row."""
    dupes = duplicates([name_of(it) for it in items])
    if dupes:
        raise ValueError(
            f"{what} names must be unique: {', '.join(repr(d) for d in dupes)} "
            f"is used more than once")
    return {name_of(it): it for it in items}


def selector_groups(project: Project) -> List[Tuple[str, List[str]]]:
    """Each key space the project carries, as ``(what, names)``."""
    groups: List[Tuple[str, List[str]]] = []
    if project.geometry is not None:
        groups.append(("Geometry surface", [s.name for s in project.geometry.surfaces]))
    if project.aero is not None:
        groups.append(("Aerodynamic surface", [s.name for s in project.aero.surfaces]))
    if project.weight is not None:
        groups.append(("CG case", [c.name for c in project.weight.cg_cases]))
    if project.aero_coeffs is not None:
        sets = [cs.name for cs in (project.aero_coeffs.cruise, project.aero_coeffs.flaps_down)
                if cs is not None]
        groups.append(("Coefficient set", sets))
    return groups


def duplicate_selectors(project: Project) -> List[str]:
    """One sentence per key space with a duplicate or blank name; empty when clean."""
    out: List[str] = []
    for what, names in selector_groups(project):
        dupes = duplicates(names)
        if dupes:
            out.append(f"{what} names must be unique: "
                       f"{', '.join(repr(d) for d in dupes)} is used more than once.")
        if any(not n.strip() for n in names):
            out.append(f"Every {what.lower()} needs a name: {sum(1 for n in names if not n.strip())} "
                       "row(s) are blank.")
    return out


__all__ = ["NAME_SEEDS", "duplicate_selectors", "duplicates", "keyed", "seed_name",
           "selector_groups"]
