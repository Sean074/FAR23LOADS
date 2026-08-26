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


#: Field labels that :func:`pretty` cannot reach, because the schema leaf is not
#: a shortened version of the field's name -- it is a *code*. ``xt25`` is the
#: fuselage station of the h-tail quarter chord; ``fwd_regardless_pct_mac`` is
#: the forward CG limit that applies at every weight; ``elevator_aft_hinge_sqft``
#: is an *area aft of the hinge line*, not a hinge. Prettifying those gives
#: *Xt25*, *Fwd Regardless Pct MAC* and *Elevator Aft Hinge*, which name nothing
#: (PB-22). The help tooltip carries the program and the registry path and is
#: most of the remedy for this persona; this table finishes it.
#:
#: Keyed by schema **leaf** name, so one entry covers every path that ends in it
#: (both gear legs' ``carrier``, every surface's ``taper_ratio``). The value is
#: the whole label: the unit suffix is still appended by the widget, so a label
#: here must not state its own unit. Hand-written and therefore guarded --
#: ``tests/test_oracle_gui.py`` fails on a key that names no schema leaf, so a
#: renamed field cannot leave a label behind pointing at nothing.
FIELD_LABELS: Dict[str, str] = {
    # Empennage stations. The digits are percent-chord positions, not indices.
    "xt25": "H-tail quarter-chord station",
    "xt50": "H-tail half-chord station",
    "xv25": "V-tail quarter-chord station",
    "xv50": "V-tail half-chord station",
    # Areas measured either side of a hinge line -- "hinge" alone reads as the
    # fitting.
    "elevator_aft_hinge_sqft": "Elevator area aft of hinge",
    "elevator_fwd_hinge_sqft": "Elevator area fwd of hinge",
    "rudder_aft_hinge_sqft": "Rudder area aft of hinge",
    "rudder_fwd_hinge_sqft": "Rudder area fwd of hinge",
    "area_aft_hinge_sqft": "Area aft of hinge",
    "area_fwd_hinge_sqft": "Area fwd of hinge",
    # Trailing-edge travel: "Te" prettifies out of an acronym.
    "elevator_te_down_deg": "Elevator TE-down travel",
    "elevator_te_up_deg": "Elevator TE-up travel",
    # The WTENV CG limits. "% MAC" is spelled in the label because ``_pct_mac``
    # is classified dimensionless, so no widget appends it -- and a CG limit
    # whose units are not on screen is a number in inches to half its readers.
    "fwd_gross_pct_mac": "Fwd CG limit at gross weight (% MAC)",
    "aft_gross_pct_mac": "Aft CG limit at gross weight (% MAC)",
    "fwd_regardless_pct_mac": "Fwd CG limit, any weight (% MAC)",
    "fwd_regardless_weight": "Weight at the any-weight fwd limit",
    # FLTLOADS scalars. ``mn`` is the Mach the coefficients were measured at --
    # not a design Mach -- and the registry basis said otherwise until PB-22.
    "mn": "Coefficient Mach number",
    "xtc": "Tail CP station, flaps up",
    "xtf": "Tail CP station, flaps down",
    # Aero coefficient derivatives, in the notation the theory uses.
    "d_cm_dalpha": "dCm/dα",
    "cy_beta": "CYβ",
    "cn_beta": "CNβ",
    # Ratios whose leaf name says the numerator only.
    "tip_ratio": "Tip chord ratio",
    "sob_y_in": "Side-of-body Y",
    "unbal_moment": "Unbalanced moment",
    "h_tail_z": "H-tail Z",
}


def pretty(name: str) -> str:
    """A field, record or module name as a human label."""
    words = name.replace(".", " ").replace("_", " ").split()
    return " ".join(SPELLING.get(w.lower(), w.capitalize()) for w in words)


__all__ = ["FIELD_LABELS", "SPELLING", "pretty"]
