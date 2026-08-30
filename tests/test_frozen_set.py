"""The 0.8.2 freeze is a manifest, not a promise (design note 44 §6, G-OR-9).

Milestone 0.8.2 builds the oracle technical report — a *view* of an analysis
that is already oracle-locked (note 44 OR-6). Building a view is not an occasion
to adjust what is being viewed, so OR-13 freezes the solver (``sloads/modules``)
and the existing oracle GUI (``oracle_app``'s pages) for the milestone's
duration, additive work excepted.

A prose freeze would not hold. The Appendix A oracles catch a solver change that
moves a printed number, and nothing catches the ones that do not: a rename, a
reordered expression, a formatter's hand. This test hashes every frozen path and
fails on any difference, which is what ``CLAUDE.md`` rule 3 asks of a
cross-cutting convention — a code owner and a drift guard, never a rule alone.

**Updating the manifest is the exception mechanism, not a workaround.** Three
authorities admit a change to a frozen file (OR-13): a new file (not frozen at
all, so not here), the single OR-3 docstring amendment in ``Oracle.py``, and a
blocking-defect fix admitted under OR-15. In every case the commit that changes
the file updates its hash here and names its authority in the commit message.
Regenerate a hash with::

    python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('PATH').read_bytes()).hexdigest())"

This guard lapses at the 0.8.2 cut: note 44 §6 is milestone-scoped, and the
release that closes the milestone deletes this file.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: SHA-256 of every path frozen by note 44 OR-13, taken at the 0.8.2 branch open
#: (2026-08-30). Keys are repo-relative POSIX paths.
MANIFEST: dict[str, str] = {
    # --- the solver (OR-13, row 1) ---------------------------------------
    "sloads/modules/__init__.py": "ad862f182589947ad0d0aad539bd89a77013cf4644e9973bdb4c2227a64102c3",
    "sloads/modules/_vtail.py": "8233445eef930439c5e7e55908ea90b8ecbba278f9a71e1bb3ab38041005c950",
    "sloads/modules/aileron.py": "9b9868b55af4cad68380e82bbb88192d6f0cacbc8d9531e59088aa65d60e3eb6",
    "sloads/modules/airloads.py": "d29ca569e220c75aa92429421c2dbb195a1f10f6aa38bfe6b7e069eefd388f3d",
    "sloads/modules/balance.py": "94a2a8c7f40e97647f31834507bbb6b41edc212a22ec332ab169e4fa5c3c1bc2",
    "sloads/modules/balloads.py": "62137ed968f4d7d814b552c76fc0fa17edd56fb8777281357b5aa4f95f11c5ce",
    "sloads/modules/body_loads.py": "d6ab6b3849892901a429580b00591791c0ad86f8c351289b9cca11679c976b77",
    "sloads/modules/configuration.py": "b512ff7e1380de69dcf1fda4e2d029324d5a1ffa36d0bc6719b4afe7506857b2",
    "sloads/modules/engine.py": "572e52b63e2587a9ad7a59987dad3f3970c3e5401c2a7f00fd92b67f9a1488c6",
    "sloads/modules/flap.py": "3bd3bfa06ddc4922227ee922dce85e46691daa528cca28ca582d18c19034ec52",
    "sloads/modules/flight_envelope.py": "acb92d1e78674588fcafb133903dc905c6e40dab05c0ea1afa6d606d60fcb067",
    "sloads/modules/landing.py": "e74744924f42f5fba83ba81fe918210db31790d88b02557f068262df052cc56c",
    "sloads/modules/mach_limit.py": "118af4d9c35b2978d5ee204912329e6c5cf2d7b7381535300ea4ed48ef1b5859",
    "sloads/modules/net_loads.py": "db41cfb9d5f32297b7c702dccbe8026e6279f3c6d916cf678ad836d83aec52f4",
    "sloads/modules/one_engine_out.py": "d53cb6f04a47fffc2acb5a1be8c7bb93587f63a912d7db57c9bc402372f35045",
    "sloads/modules/select.py": "3f05f945107e2230593e29167d051b6e5511dbdd8eef868aca7808525b141adc",
    "sloads/modules/structural_speeds.py": "8fdbc1cc6eb17dbbdda4f5f1b224c7d5d4b86dfe14c923457292db7e123814c1",
    "sloads/modules/tab.py": "f81ff82261cccabedef57491635b3f56767faa61bae31c2d0d0017fc3bcb07e7",
    "sloads/modules/tail_span.py": "22a7832553de87ef9826c6e869e8ec8f1fe4e39c04706224f6af63e0847212b5",
    "sloads/modules/taildist.py": "3848d95ed35894bfe58e16e2c2f6a21e12a93ea493e533ccfdf40bf4caead3fb",
    "sloads/modules/weight_envelope.py": "8e8e22b2807411219642ddaf63e54a65794bdf13287b9f2c57a8204a199098d2",
    "sloads/modules/weight_estimate.py": "8439bb62fa62dd1e11e13efe603e2efad517584f5ca441ad52cbc49048c286fe",
    "sloads/modules/weight_onecg.py": "a306666ca1ca3b4bba0a783e424bdb0ed2bcaadb66480c29bbfadfcfe0e1cd24",
    "sloads/modules/wing_geometry.py": "0cc54b5291c3243a16ae9331289813212c7c8ad0ae18c0e56b4d598b4618d6cc",
    "sloads/modules/wing_inertia.py": "2bf2f00614725a842f0a75a5e213669cdbdf3b0199313fa22c7dc5096df44f81",
    # --- the existing oracle GUI (OR-13, row 2) ---------------------------
    "oracle_app/Oracle.py": "b478bf06fd1c998ffa9ee1eebbc51225c24a26a813840529105779b51f5085a1",
    "oracle_app/__init__.py": "bb3135345b421b8fac0f02226050b821770a53c647c4ead72c8dfbd2d156f3d0",
    "oracle_app/form.py": "d5a34df08c76a4e16ac70f1c83ac8fff175d35794390b22dffb177ad83ea76fb",
    "oracle_app/labels.py": "93e442a1fff2174fdd17dd56f8d0b5f91e071641ead341be3dc5b71ede7cebf9",
    "oracle_app/results.py": "b49e5a8676cc747e559579c8ca0f5f5f8b2e8d2be07903d8cdd4b214b5b46645",
}

#: Directories the manifest claims to cover completely, so that a *new* file
#: dropped into the solver cannot slip past the freeze unhashed. ``oracle_app``
#: is not here: OR-13 permits new files there (the report page is the
#: milestone's first commit), and only the listed ones are frozen.
SEALED_DIRS = ("sloads/modules",)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("rel", sorted(MANIFEST))
def test_frozen_file_unchanged(rel: str) -> None:
    """A frozen path still hashes to what note 44 OR-13 froze."""
    path = REPO_ROOT / rel
    assert path.exists(), (
        f"{rel} is frozen by design note 44 OR-13 but no longer exists. Deleting "
        "a frozen file needs the same authority as editing one."
    )
    assert _sha256(path) == MANIFEST[rel], (
        f"{rel} changed, and it is frozen for milestone 0.8.2 (design note 44 "
        "OR-13). Permitted changes are: the OR-3 docstring amendment in "
        "oracle_app/Oracle.py, or a blocking-defect fix admitted under OR-15 "
        "with an issue number. Either way, update this manifest in the same "
        "commit and name the authority in the commit message. A defect you "
        "found while writing the report is filed, not fixed (OR-14)."
    )


@pytest.mark.parametrize("sealed", SEALED_DIRS)
def test_no_unhashed_files_in_sealed_dirs(sealed: str) -> None:
    """A new file in a sealed directory is a freeze gap, so it fails here."""
    found = {
        p.relative_to(REPO_ROOT).as_posix()
        for p in (REPO_ROOT / sealed).glob("*.py")
    }
    missing = sorted(found - set(MANIFEST))
    assert not missing, (
        f"{missing} live in {sealed}/, which design note 44 OR-13 freezes whole, "
        "but carry no manifest hash. Adding a solver module during 0.8.2 is a "
        "change to the frozen set: it needs OR-15 authority and a hash here."
    )


if __name__ == "__main__":  # zero-dependency self-runner
    sys.exit(pytest.main([__file__, "-p", "no:xdist", "-q"]))
