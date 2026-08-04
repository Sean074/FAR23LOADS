"""Canonical :class:`~sloads.models.LoadValue` keys for the load-case schema (M4-9).

Every ``LoadValue`` carries a stable ``key``; this module names only the handful
that **cross a module boundary** — the components of the flat load-case row that
``report.load_cases_to_rows`` builds and the sbeam bridge exports. Producers
(``modules/engine.py`` today) and consumers (``report``, the views, the tests)
import the same constant, so a rename is a one-line change that the type checker
and the test suite both follow.

Keys that never leave their own module are named inline at the producing site;
they still must be unique within their ``ConditionResult``
(``test_load_keys.py`` asserts that across every example project).

Why this exists: before M4-9 these were display-label string literals duplicated
in ``report.py``, the views and ~150 test call sites, and a cosmetic relabel
silently blanked the CSV column rather than raising.
"""

from __future__ import annotations

import re

_NON_WORD = re.compile(r"[^0-9A-Za-z]+")

# --- Application point (geometry, never scaled to ultimate) ----------------- #
LOC_X = "loc_x"
LOC_Y = "loc_y"
LOC_Z = "loc_z"
LOC_KEYS = (LOC_X, LOC_Y, LOC_Z)

# --- Forces ----------------------------------------------------------------- #
#: 1g/manoeuvre vertical down load on the mount.
FZ_VERTICAL = "fz_vertical"
#: The 2.5g vertical load carried alongside the gyroscopic moments (23.371(b)).
FZ_VERTICAL_2_5G = "fz_vertical_2_5g"
#: Either vertical load fills the load-case row's vertical column, first match wins.
VERTICAL_KEYS = (FZ_VERTICAL, FZ_VERTICAL_2_5G)

FY_SIDE = "fy_side"
FX_THRUST = "fx_thrust"

# --- Moments ---------------------------------------------------------------- #
#: Engine-mount reaction torque about the thrust axis (reported negative — see
#: the preserved-conventions note in CLAUDE.md).
MX_MOUNT_TORQUE = "mx_mount_torque"

#: The four 23.371(b) sign combinations each emit a pitching (Myy) and a yawing
#: (Mzz) moment. The model cannot carry four ``case_ref`` s on one
#: ``ConditionResult`` (backlog Step D1), so the sub-case number rides in the key
#: — our own namespace, minted and parsed here, never a display string.
GYRO_KEY_PREFIX = "gyro_case"


def gyro_key(case: int, component: str) -> str:
    """The key for one gyroscopic sub-case component (``component``: myy/mzz)."""
    return f"{GYRO_KEY_PREFIX}{case}_{component.lower()}"


def parse_gyro_key(key: str):
    """``(case_number, component)`` for a gyro sub-case key, else ``None``."""
    if not key.startswith(GYRO_KEY_PREFIX):
        return None
    rest = key[len(GYRO_KEY_PREFIX):]
    num, _, comp = rest.partition("_")
    if not num.isdigit() or comp not in ("myy", "mzz"):
        return None
    return int(num), comp


def key_from_label(label: str) -> str:
    """A snake_case key derived from ``label``.

    **Use sparingly.** Deriving the key from the label is exactly what M4-9
    removes, so this is only for rows whose "label" is *data* rather than display
    text — ``weight_estimate``'s group rows, whose names are the keys of the
    ``WT_*_FRACTIONS`` tables in :mod:`sloads.constants`. Everywhere else the key
    is written at the producing site and the label is free to change.
    """
    out = label.replace("%", " pct ").replace("&", " and ")
    out = "_".join(part for part in _NON_WORD.split(out) if part).lower()
    return f"n{out}" if out[:1].isdigit() else out


#: Keys whose presence means "these results carry structural load-case data", i.e.
#: the ``load_cases_to_rows`` schema applies rather than the generic table.
LOAD_CASE_KEYS = frozenset(
    LOC_KEYS + VERTICAL_KEYS + (FY_SIDE, FX_THRUST, MX_MOUNT_TORQUE)
)
