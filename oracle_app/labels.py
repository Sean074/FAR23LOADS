"""How the oracle GUI spells things.

Two renderers turn a schema or module name into a heading -- the input form
(:mod:`oracle_app.form`) and the results block (:mod:`oracle_app.results`) --
and a page that writes "H-tail" above its inputs and "Htail" above its results
has two label owners and will drift. One table, one function, imported by both.

Presentation only: nothing here is data, and nothing here decides what a page
shows.
"""

from __future__ import annotations

from typing import Dict

#: Segments whose capitalisation is not ``str.capitalize``'s -- acronyms, the
#: hyphenated surface names, and the aerodynamic coefficients.
SPELLING: Dict[str, str] = {
    "htail": "H-tail", "vtail": "V-tail", "cg": "CG", "mac": "MAC", "le": "LE",
    "cl": "CL", "cm": "CM", "clmax": "CLmax", "xcg": "XCG", "zcg": "ZCG",
    "xlemac": "XLEMAC", "rpm": "RPM", "hp": "hp", "eas": "EAS", "vn": "V-n",
    "ixx": "IXX", "iyy": "IYY", "izz": "IZZ", "wrp": "WRP", "sob": "SOB",
    "id": "ID", "od": "OD", "far25": "FAR 25", "oei": "OEI",
    # Module names the results renderer heads its blocks with.
    "onecg": "One-CG", "taildist": "TAILDIST", "balloads": "BALLOADS",
    "airloads": "AIRLOADS",
}


def pretty(name: str) -> str:
    """A field, record or module name as a human label."""
    words = name.replace(".", " ").replace("_", " ").split()
    return " ".join(SPELLING.get(w.lower(), w.capitalize()) for w in words)


__all__ = ["SPELLING", "pretty"]
