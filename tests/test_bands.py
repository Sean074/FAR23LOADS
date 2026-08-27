"""The id-band registry's guard: disjoint by proof, and blind to nothing.

Why this file exists is the whole point of the registry it guards. GID/EID/SID
bands used to be per-file constants with prose docstrings claiming disjointness,
checked by two tests that **hand-enumerated the bands they knew about**. The
balanced deck was written into ``4001+``, which the spanwise h-tail deck already
owned; both docstrings still claimed disjointness, neither test listed the new
family, and the collision lived for two months (review 2026-08-10 **F-C1**, root
cause **F-G3**). A deck that splices two unrelated loads onto one node is the
D-19 class -- parses cleanly, silently wrong.

So the guard here is written to have no list of its own:

* :func:`test_no_two_bands_overlap` walks :data:`sloads.export.bands.BANDS`
  pairwise. A band added to the registry is checked the moment it exists.
* :func:`test_every_export_base_constant_is_a_registered_band` walks the
  **module globals** of every module in ``sloads/export`` and requires each
  id-base constant to be a registered band's ``start``. This is the
  blind-spot killer: a new deck family that invents its own ``_FOO_GID_BASE``
  fails here even if nobody thinks to add it anywhere.
* :func:`test_allocators_come_out_of_their_own_band` ties each public allocator
  to the band that claims to own it, so the registry cannot drift from the code
  it documents.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
import pkgutil

import pytest

import sloads.export as export_pkg
from sloads.case_ids import BALANCED_HAND_BLOCK, SUBCASE_BLOCK, balanced_subcase_id, subcase_id
from sloads.export import balanced_deck as bdk
from sloads.export import bands as bd
from sloads.export import mass_cards as mc
from sloads.export import roundtrip as rt
from sloads.export import sbeam_bridge as sb


# --------------------------------------------------------------------------- #
# The registry is internally sound
# --------------------------------------------------------------------------- #
def test_no_two_bands_overlap():
    """No pair of registered bands shares an id -- the F-C1 gate, exhaustive.

    ``overlaps()`` compares every pair in the registry rather than a list this
    test maintains, so the guard cannot be blind to a family it was not told
    about.
    """
    collisions = [(a.name, b.name, f"{a.start}-{a.end}", f"{b.start}-{b.end}")
                  for a, b in bd.overlaps()]
    assert not collisions, f"colliding id bands: {collisions}"


def test_the_registry_would_have_caught_the_balanced_deck_collision():
    """The gate has teeth: re-declare the old ``4001+`` wing band and it fires.

    The pre-fix numbering, restored here, is exactly what shipped from plan 11
    until 2026-08-10.
    """
    old = bd.Band("balanced-wing-right", bd.IdKind.GID, 4001, 200, "plan 11")
    clash = [b for b in bd.bands_of_kind(bd.IdKind.GID)
             if b.name != old.name and b.start <= old.end and old.start <= b.end]
    assert [b.name for b in clash] == ["tail-span-htail"]


def test_band_names_are_unique():
    names = [b.name for b in bd.BANDS]
    assert len(names) == len(set(names)), sorted(names)


def test_a_band_refuses_an_index_past_its_capacity():
    """The overflow raise is the reason allocation goes through the registry:
    ``start + index`` walks into the next family and still writes valid cards."""
    b = bd.band("tail-span-htail")
    assert b.allocate(0) == b.start
    assert b.allocate(b.size - 1) == b.end
    for bad in (-1, b.size):
        with pytest.raises(ValueError) as exc:
            b.allocate(bad)
        assert b.name in str(exc.value) and b.owner in str(exc.value)


def test_unknown_band_name_raises_and_lists_what_exists():
    with pytest.raises(ValueError) as exc:
        bd.band("no-such-band")
    assert "wing-stick" in str(exc.value)


def test_owner_of_answers_who_allocated_an_id():
    assert bd.owner_of(1001, bd.IdKind.GID) == "body-mass"
    assert bd.owner_of(6001, bd.IdKind.GID) == "balanced-wing-right"
    assert bd.owner_of(9001, bd.IdKind.EID) == "mass-baseline"
    assert bd.owner_of(9301, bd.IdKind.SID) == "massset"
    assert bd.owner_of(8000, bd.IdKind.GID) == ""


# --------------------------------------------------------------------------- #
# The registry is exhaustive -- nothing allocates outside it
# --------------------------------------------------------------------------- #
#: A module-global whose name ends in one of these is an id base by convention,
#: and must therefore be a registered band's ``start``.
_BASE_SUFFIXES = ("_GID_BASE", "_EID_BASE", "_SID_BASE", "_SID", "_GID",
                  "_EID_BASELINE", "_EID_DISCRETIONARY", "_EID_BALLAST")

#: Constants that are ids in name only -- a coordinate-system id, not a node,
#: element or load-set id. Listed explicitly so the sweep stays strict.
_NOT_AN_ID_BAND = {"SBEAM_CID"}


def _export_modules():
    for info in pkgutil.iter_modules(export_pkg.__path__):
        yield importlib.import_module(f"sloads.export.{info.name}")


def test_export_modules_were_actually_swept():
    """The sweep below is only a guard if it sees the modules that hold bands."""
    names = {m.__name__.rsplit(".", 1)[1] for m in _export_modules()}
    assert {"sbeam_bridge", "balanced_deck", "mass_cards", "roundtrip"} <= names


def test_every_export_base_constant_is_a_registered_band():
    """Every id-base constant in ``sloads/export`` is some band's ``start``.

    Discovered by introspection, not by a list -- this is what makes the guard
    blind-spot-free (review F-G3). A new deck family that opens its own band
    without registering it fails here, which is the failure the balanced deck's
    collision needed and did not get.
    """
    starts = {b.start for b in bd.BANDS}
    stray = []
    for module in _export_modules():
        for name, value in vars(module).items():
            if name in _NOT_AN_ID_BAND or not isinstance(value, int):
                continue
            if isinstance(value, bool) or not name.endswith(_BASE_SUFFIXES):
                continue
            if value not in starts:
                stray.append(f"{module.__name__}.{name} = {value}")
    assert not stray, (
        "id base constants outside the band registry -- declare them in "
        f"sloads/export/bands.py: {stray}")


def test_the_subcase_blocks_and_the_registry_cannot_drift():
    """``case_ids.SUBCASE_BLOCK`` allocates the per-component SIDs; the registry
    only mirrors them (calc must not import export). Pin the mirror.

    A block's first id is ``base + 1`` -- ``W-01`` -> ``101`` -- so the band
    starts one past the block value and is 99 wide.
    """
    mirrored = {b.name.split("-", 1)[1]: b
                for b in bd.bands_of_kind(bd.IdKind.SID)
                if b.name.startswith("subcase-")}
    assert set(mirrored) == set(SUBCASE_BLOCK), (
        f"registry {sorted(mirrored)} vs case_ids {sorted(SUBCASE_BLOCK)}")
    for prefix, base in SUBCASE_BLOCK.items():
        band = mirrored[prefix]
        assert band.start == base + 1 == subcase_id(f"{prefix}-01")
        assert band.end == base + 99 == subcase_id(f"{prefix}-99")


#: The registry name of each balanced hand block (``case_ids`` is calc-side and
#: does not know the registry exists; this pairing is the mirror being pinned).
_BALANCED_BANDS = {"": "balanced-subcase",
                   "R": "balanced-subcase-stbd",
                   "L": "balanced-subcase-port"}


def test_the_balanced_hand_blocks_and_the_registry_cannot_drift():
    """Same mirror, for the assembled deck's per-hand blocks (**D-R7**).

    A block spans the whole minted range -- the lowest id is a ``W-01`` at
    ``block + 101`` and the highest an ``LG-99`` at ``block + 699`` -- so the
    band is 599 wide, not 99: one balanced deck holds wing, tail and (from the
    ground cases) gear subcases at once.
    """
    assert set(_BALANCED_BANDS) == set(BALANCED_HAND_BLOCK)
    for hand, block in BALANCED_HAND_BLOCK.items():
        band = bd.band(_BALANCED_BANDS[hand])
        assert band.start == block + 101 == balanced_subcase_id(f"W-01{hand}")
        assert band.end == block + 699 == balanced_subcase_id(f"LG-99{hand}")


# --------------------------------------------------------------------------- #
# The allocators agree with the bands that claim to own them
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name,call", [
    ("wing-stick", lambda i: sb.station_gid(i - 1)),   # GID 1 is the clamped root
    ("body-mass", sb.beam_station_gid),
    ("tail-chord-htail", lambda i: sb.tail_station_gid("htail", i)),
    ("tail-chord-vtail", lambda i: sb.tail_station_gid("vtail", i)),
    ("control-surface", sb.control_station_gid),
    ("tail-span-htail", lambda i: sb.tail_span_gid("htail", i)),
    ("tail-span-vtail", lambda i: sb.tail_span_gid("vtail", i)),
])
def test_allocators_come_out_of_their_own_band(name, call):
    """First and last id of each allocator land on the band's own end points,
    and one past the end raises rather than entering the next family."""
    band = bd.band(name)
    assert call(0) == band.start
    assert call(band.size - 1) == band.end
    with pytest.raises(ValueError):
        call(band.size)


def test_the_public_base_constants_still_name_their_bands():
    """The per-module constants are aliases now, not sources. Callers (and the
    decks' ``$`` headers) still read them, so pin what they resolve to."""
    assert sb._ROOT_GID == bd.band("wing-stick").start == 1
    assert sb._BODY_GID_BASE == bd.band("body-mass").start == 1001
    assert sb._BODY_CARRY_GID_BASE == bd.band("body-reaction").start == 1501
    assert sb._CS_GID_BASE == bd.band("control-surface").start == 3001
    assert sb._HTAIL_SPAN_GID_BASE == bd.band("tail-span-htail").start == 4001
    assert sb._VTAIL_SPAN_GID_BASE == bd.band("tail-span-vtail").start == 4501
    assert bdk.BALANCED_WING_R_BASE == bd.band("balanced-wing-right").start == 6001
    assert bdk.BALANCED_WING_L_BASE == bd.band("balanced-wing-left").start == 6201
    assert bdk.BALANCED_BODY_BASE == bd.band("balanced-centreline").start == 6401
    assert (bdk.BALANCED_FALLBACK_SID_BASE
            == bd.band("balanced-subcase-unmapped").start == 5001)
    assert mc.MASS_EID_BASELINE == bd.band("mass-baseline").start == 9001
    assert mc.MASSSET_SID_BASE == bd.band("massset").start == 9301
    assert mc.GRAV_SID_BASE == bd.band("grav").start == 9401
    assert rt.SPC_SID == bd.band("spc").start == 1


def test_the_balanced_deck_is_out_of_the_tail_span_range():
    """The F-C1 fix itself, stated as a fact about the numbers: no balanced node
    can land in either spanwise tail band."""
    tail = [bd.band("tail-span-htail"), bd.band("tail-span-vtail")]
    for name in ("balanced-wing-right", "balanced-wing-left", "balanced-centreline"):
        b = bd.band(name)
        for t in tail:
            assert not (b.start <= t.end and t.start <= b.end), f"{name} vs {t.name}"


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
