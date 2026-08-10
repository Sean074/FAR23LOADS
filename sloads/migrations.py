"""Schema migrations: normalise any historical ``project.json`` to the current shape.

**The problem this replaces (M4-10).** Before this module, ``io.project_from_dict``
decided what it was looking at by *sniffing keys* — a 19-clause ``or`` gate
enumerating every slice name — and each legacy file shape was handled by an
inline shim threaded through the readers as a ``legacy_*`` parameter. Two things
were wrong with that. Adding a slice meant remembering to extend the gate, or a
project file would be silently misread as a bare engine file. And "is this key
absent because the file is old, or because the user never filled it in?" was
answered ad hoc, differently, at five separate sites.

**The shape now.** Migration is a chain of small, pure ``dict -> dict`` hops, one
per schema version that changed the file *shape*:

    v_file --hop--> v_file+1 --hop--> ... --> SCHEMA_VERSION --> one tolerant reader

``io.project_from_dict`` therefore only ever sees a current-shape dict, and the
readers only ever describe the current schema. A version with no shape change has
no entry in :data:`MIGRATIONS` and costs nothing.

**Archaeology (M4-10 sub-step 1).** The plan noted that no document recorded
which ``SCHEMA_VERSION`` each legacy path belonged to. Reconstructed from the
version history in ``models/project.py`` and the step records in
``40_history/00_completed_development.md``:

===== ============================================================ =================================
hop    file-shape change                                            was handled by (now retired)
===== ============================================================ =================================
v0     the whole file is a bare ``EngineInput`` (the Phase-0        the ``else`` branch of the
       ``engloads`` era, before ``Project`` existed)                19-clause or-gate
v0     single ``"engine": {...}`` instead of ``"engines": [...]``   ``_engines_from_dict``
v18    ``aero_coeffs`` split out of ``flight_loads.configurations`` ``_legacy_aero_coeffs_from_flight_loads``
v19    ``weight.cg_cases`` split out of ``flight_loads.cg_cases``   ``_legacy_cg_cases_from_flight_loads``
v24    ft/in² geometry keys renamed to in/ft² (Phase G0)            ``_rename_legacy_units`` (5 sites)
v25    top-level ``configuration`` folded into ``geometry``         ``legacy_configuration=``
v27    top-level ``tail_loads``/``vtail_loads`` -> ``geometry``      ``legacy_tail_loads=`` /
       ``.empennage.htail``/``.vtail``                              ``legacy_vtail_loads=``
v28    top-level ``landing`` gear -> ``geometry.landing_gear``       ``legacy_landing=``
v36    persisted ``LoadValue`` s gain ``key`` (M4-9)                 nothing — new in v37
v39    ``speeds.mach_limit.mc``/``.md`` removed (F25-2)              nothing — new in v40
===== ============================================================ =================================

Versions 1–17, 20–23, 26, 29–35 and **37** are **additive only** — a new optional
field that the tolerant ``_filtered`` readers already default — so they need no
hop. v38 (``Project.unit_system``, M4-20) is the additive case in its purest
form: a scalar with a total default whose absence *is* its documented value
(absent → Imperial), so a pre-v38 file's deliverables render exactly as before.
The ``SCHEMA_VERSION`` bump is still required — the fields-hash tripwire in
``tests/test_schema_guards.py`` demands one for any change to a persisted shape,
which is the discipline working, not a hop being skipped.

**Supported floor.** v0 (bare engine file) and anything from v18 up are migrated.
A file claiming v1–v17 is read as v18 shape: those versions only ever added
fields, so the difference is indistinguishable from a v18 file that left them
unset. See ``PROJECT_GUIDE.md`` §5.

Pure: dicts in, dicts out, no I/O.
"""

from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List

from .models import SCHEMA_VERSION

#: Keys that make a dict a *project* rather than a bare engine file. Derived from
#: ``Project``'s own dataclass fields plus the historical top-level slice names
#: that later moved elsewhere -- so adding a slice to ``Project`` extends this set
#: automatically, which the hand-maintained 19-clause or-gate did not.
_LEGACY_TOP_LEVEL_KEYS = frozenset({
    "configuration",    # pre-v25 parametric layout
    "tail_loads",       # pre-v27
    "vtail_loads",      # pre-v27
    "engine",           # pre-multi-engine singular key
})


def _project_keys() -> frozenset:
    from dataclasses import fields as dc_fields

    from .models import Project

    return frozenset(f.name for f in dc_fields(Project)) | _LEGACY_TOP_LEVEL_KEYS


def is_project_dict(d: Dict[str, Any]) -> bool:
    """True when ``d`` is a project file, False when it is a bare engine file.

    Replaces the 19-clause key sniff. A bare ``EngineInput`` dict shares no key
    with ``Project``'s field set, so the test is a set intersection that keeps
    working when a slice is added -- the old gate had to be edited by hand, and a
    forgotten edit silently downgraded a real project to an engine-only read.
    """
    return bool(set(d) & _project_keys())


# --------------------------------------------------------------------------- #
# Unit renames (v24, Phase G0)
# --------------------------------------------------------------------------- #
def _rename_scaled(d: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Rename ``old -> new`` and rescale, only when the legacy key is present."""
    for old, (new, factor) in mapping.items():
        if old in d and d.get(old) is not None:
            d[new] = float(d.pop(old)) * factor
        else:
            d.pop(old, None)
    return d


def _v24_units(d: Dict[str, Any]) -> Dict[str, Any]:
    """ft/in² geometry inputs -> the canonical in/ft² of one-unit-per-dimension."""
    select_input = d.get("select_input")
    if isinstance(select_input, dict):
        _rename_scaled(select_input, {"airplane_length_ft": ("airplane_length_in", 12.0)})

    # Both tail slices are still top-level at v24 -- the v27 hop that folds them
    # into geometry.empennage runs *after* this one, which is exactly why the
    # renames have to happen here rather than inside the empennage reader.
    htail = d.get("tail_loads")
    if isinstance(htail, dict):
        _rename_scaled(htail, {"airplane_length_ft": ("airplane_length_in", 12.0)})

    vtail = d.get("vtail_loads")
    if isinstance(vtail, dict):
        _rename_scaled(vtail, {
            "airplane_length_ft": ("airplane_length_in", 12.0),
            "wing_span_ft": ("wing_span_in", 12.0),
            "vtail_mac_ft": ("vtail_mac_in", 12.0),
        })

    config = d.get("configuration")
    if isinstance(config, dict):
        _rename_scaled(config, {
            "h_tail_span_ft": ("h_tail_span_in", 12.0),
            "v_tail_span_ft": ("v_tail_span_in", 12.0),
        })

    tabs = d.get("tab_loads")
    if isinstance(tabs, dict):
        for tab in tabs.get("tabs") or []:
            if isinstance(tab, dict):
                _rename_scaled(tab, {"area_sqin": ("area_sqft", 1.0 / 144.0)})
    return d


# --------------------------------------------------------------------------- #
# Slice splits (v18, v19)
# --------------------------------------------------------------------------- #
def _v18_aero_coeffs(d: Dict[str, Any]) -> Dict[str, Any]:
    """``aero_coeffs`` split out of ``flight_loads.configurations`` (Step D4.1)."""
    if d.get("aero_coeffs") is not None:
        return d
    fl = d.get("flight_loads")
    configs = (fl or {}).get("configurations") if isinstance(fl, dict) else None
    if not configs:
        return d
    by_name = {c.get("name", ""): c for c in configs if isinstance(c, dict)}
    cruise = by_name.get("cruise") or (configs[0] if configs else None)
    flaps_down = by_name.get("flaps_down") or by_name.get("landing")
    coeffs: Dict[str, Any] = {}
    if cruise:
        coeffs["cruise"] = cruise
    if flaps_down and flaps_down is not cruise:
        coeffs["flaps_down"] = flaps_down
    if coeffs:
        d["aero_coeffs"] = coeffs
    return d


def _v19_cg_cases(d: Dict[str, Any]) -> Dict[str, Any]:
    """``weight.cg_cases`` split out of ``flight_loads.cg_cases`` (Step D5)."""
    weight = d.get("weight")
    if not isinstance(weight, dict) or weight.get("cg_cases"):
        return d
    fl = d.get("flight_loads")
    cases = (fl or {}).get("cg_cases") if isinstance(fl, dict) else None
    if cases:
        weight["cg_cases"] = copy.deepcopy(cases)
    return d


# --------------------------------------------------------------------------- #
# Geometry unification (v25, v27, v28)
# --------------------------------------------------------------------------- #
def _geometry(d: Dict[str, Any]) -> Dict[str, Any]:
    geometry = d.get("geometry")
    if not isinstance(geometry, dict):
        geometry = {}
        d["geometry"] = geometry
    return geometry


def _v25_configuration(d: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level ``configuration`` -> ``geometry.parametric`` (Phase G1)."""
    config = d.pop("configuration", None)
    if isinstance(config, dict) and config:
        geometry = _geometry(d)
        geometry.setdefault("parametric", config)
    return d


def _v27_empennage(d: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level ``tail_loads``/``vtail_loads`` -> ``geometry.empennage`` (Phase G6)."""
    htail = d.pop("tail_loads", None)
    vtail = d.pop("vtail_loads", None)
    if not (htail or vtail):
        return d
    geometry = _geometry(d)
    empennage = geometry.get("empennage")
    if not isinstance(empennage, dict):
        empennage = {}
        geometry["empennage"] = empennage
    if htail and not empennage.get("htail"):
        empennage["htail"] = htail
    if vtail and not empennage.get("vtail"):
        empennage["vtail"] = vtail
    return d


def _v28_landing_gear(d: Dict[str, Any]) -> Dict[str, Any]:
    """A pre-G6b file's gear geometry lived on ``landing`` -> ``geometry.landing_gear``."""
    landing = d.get("landing")
    if not isinstance(landing, dict):
        return d
    if not any(landing.get(k) for k in ("main_gear", "nose_gear", "tread_in")):
        return d
    geometry = _geometry(d)
    if geometry.get("landing_gear"):
        return d
    geometry["landing_gear"] = {
        k: copy.deepcopy(landing[k])
        for k in ("main_gear", "nose_gear", "tread_in")
        if k in landing
    }
    return d


# --------------------------------------------------------------------------- #
# LoadValue.key backfill (v36, M4-9)
# --------------------------------------------------------------------------- #
#: The **frozen** label -> key table for every ``LoadValue`` a v36-or-older file
#: could carry in ``envelope.critical.conditions[].loads`` -- i.e. every label
#: ``modules/select.py`` emitted, captured at the moment M4-9 keyed it.
#:
#: Frozen means frozen: this table describes what *old files say*, so it must not
#: be regenerated when a label is later reworded. Rewording a label is precisely
#: what M4-9 makes safe, and it changes nothing about a file already on disk.
_V36_LOAD_VALUE_KEYS = {
    "Altitude": "altitude",
    "AoA load (cp 25%)": "aoa_load_cp_25_pct",
    "AoA load LT25 (cp 25%)": "aoa_load_lt25_cp_25_pct",
    "Balanced tail load": "balanced_tail_load",
    "Balancing tail load": "balancing_tail_load",
    "CL": "cl",
    "CP of total load": "cp_of_total_load",
    "Camber/elevator load LT50 (cp 50%)": "camber_elevator_load_lt50_cp_50_pct",
    "Elevator deflection": "elevator_deflection",
    "Elevator deflection (TE dn +)": "elevator_deflection_te_dn",
    "Elevator load": "elevator_load",
    "Elevator-deflection increment (cp 50%)": "elevator_deflection_increment_cp_50_pct",
    "Fuselage down load on wing": "fuselage_down_load_on_wing",
    "Fuselage load on wing": "fuselage_load_on_wing",
    "Gust increment (cp 25%)": "gust_increment_cp_25_pct",
    "Inertia drag factor NX": "inertia_drag_factor_nx",
    "LH side load": "lh_side_load",
    "Load due to rudder (cp 50%)": "load_due_to_rudder_cp_50_pct",
    "Load due to yaw 19.5deg (cp 25%)": "load_due_to_yaw_19_5deg_cp_25_pct",
    "Load factor NZ": "load_factor_nz",
    "Load on rudder": "load_on_rudder",
    "Maneuver load increment": "maneuver_load_increment",
    "Other-side percent": "other_side_percent",
    "Pitch inertia Iyy": "pitch_inertia_iyy",
    "RH side load": "rh_side_load",
    "Tail angle of attack AT": "tail_angle_of_attack_at",
    "Tail load": "tail_load",
    "Total tail load": "total_tail_load",
    "Total tail load (cp 25%)": "total_tail_load_cp_25_pct",
    "V (EAS)": "v_eas",
    "Yaw inertia IZZ": "yaw_inertia_izz",
}


def _v36_load_value_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """Backfill ``LoadValue.key`` on the persisted SELECT critical conditions (M4-9).

    A v36 file stores each critical condition's loads as ``{label, value, units}``
    with no key, and every consumer now matches on the key -- so without this the
    reloaded governing-loads table would silently lose its columns, which is the
    exact failure mode M4-9 exists to remove, re-entering through the file path.

    An unrecognised label keeps ``key == ""``. That is deliberate: guessing a key
    for a label this build has never emitted would invent an identity, and the row
    is still displayed (the label was always the display text). Re-running SELECT
    regenerates the slice with real keys.
    """
    envelope = d.get("envelope")
    critical = envelope.get("critical") if isinstance(envelope, dict) else None
    if not isinstance(critical, dict):
        return d
    for cond in critical.get("conditions") or []:
        if not isinstance(cond, dict):
            continue
        for load in cond.get("loads") or []:
            if isinstance(load, dict) and not load.get("key"):
                load["key"] = _V36_LOAD_VALUE_KEYS.get(load.get("label", ""), "")
    return d


def _v39_mach_limit_mc_md(d: Dict[str, Any]) -> Dict[str, Any]:
    """Drop the stale ``speeds.mach_limit.mc``/``.md`` duplicate (F25-2).

    MC and MD were persisted here *and* recomputed from the design speeds by the
    Streamlit Speed-Altitude tab, which ignored the stored pair outright. The
    registry/CLI path did not -- so ``examples/concept_regional_jet.project.json``
    reported MNE 0.738 from the CLI and MNE 0.848 from the GUI, for the same
    project and the same module. MC/MD are now derived once by
    ``structural_speeds.design_speed_values`` and handed to ``mach_limit_lines``.

    Dropping rather than migrating the values is deliberate and is *not* silent
    data loss: the stored pair was never a user decision the tool acted on in the
    GUI, and the derived pair is what the design speeds actually imply. A file
    whose stored MC/MD disagreed with its own VC/VD was, by construction,
    internally inconsistent.
    """
    speeds = d.get("speeds")
    if not isinstance(speeds, dict):
        return d
    ml = speeds.get("mach_limit")
    if isinstance(ml, dict):
        ml.pop("mc", None)
        ml.pop("md", None)
    return d


def _v40_fuselage_stations_override(d: Dict[str, Any]) -> Dict[str, Any]:
    """Keep a pre-B1 file's hand-entered fuselage beam (step B1).

    B1 makes ``weight.items`` the mass SSOT and *derives* the Ch 15 station table
    from it (:func:`sloads.mass_distribution.fuselage_beam_stations`), because the
    two models had never been compared and the entered table was short by 10-100 %
    of the beam on every shipped fixture. Derived is the new default.

    A file that already carries a station table, however, carries somebody's
    modelling decision, and silently switching their fuselage loads on load is not
    ours to do -- the numbers would move without anybody asking. So a migrated
    file keeps its table by being marked an **explicit override**; the difference
    against the derived distribution is reported by
    ``mass_distribution.fuselage_reconciliation`` (surfaced on the Fuselage Loads
    page), and adopting the SSOT is then the user's decision, taken with the gap
    in front of them.

    Files with no ``fuselage_mass`` at all are untouched: there is nothing to
    preserve, and they get the derived table.

    ``MassItem.component`` needs no hop -- it is an optional field, absent means
    "not tagged", and ``mass_distribution.infer_component`` handles the untagged
    case by design.
    """
    fm = d.get("fuselage_mass")
    if isinstance(fm, dict) and fm.get("stations"):
        fm.setdefault("stations_are_override", True)
    return d


def _v43_tail_mass_override(d: Dict[str, Any]) -> Dict[str, Any]:
    """Keep a pre-SSOT file's hand-entered tail panel weight.

    The empennage half of :func:`_v40_fuselage_stations_override`, and it keeps
    faith the same way: the surface weight the spanwise tail distribution smears
    is now **derived** from the ``htail``/``vtail``-tagged ``weight.items``
    (:func:`sloads.mass_distribution.tail_surface_weight`), because the entered
    ``tail_mass`` was a second mass model nothing reconciled -- and one that no
    shipped fixture ever populated, so every h-tail deck was air-only.

    A file that *did* enter a weight made a modelling decision, so it is marked
    an explicit override rather than being silently replaced by the item sum;
    ``mass_distribution.tail_reconciliation`` reports the difference either way.
    A zero or absent weight is left alone -- there is nothing to preserve, and it
    gets the derived value, which is the whole point of the step.
    """
    for tm in d.get("tail_mass") or []:
        if isinstance(tm, dict) and tm.get("panel_weight_lb"):
            tm.setdefault("weight_is_override", True)
    return d


# --------------------------------------------------------------------------- #
# The chain
# --------------------------------------------------------------------------- #
#: ``{from_version: hop}`` -- applied in ascending order, each turning a file of
#: version *n* into version *n+1* shape. A version absent here changed only by
#: adding optional fields, which the tolerant readers already default.
MIGRATIONS: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    18: _v18_aero_coeffs,
    19: _v19_cg_cases,
    24: _v24_units,
    25: _v25_configuration,
    27: _v27_empennage,
    28: _v28_landing_gear,
    36: _v36_load_value_keys,
    39: _v39_mach_limit_mc_md,
    40: _v40_fuselage_stations_override,
    43: _v43_tail_mass_override,
}

#: The oldest project version whose *shape* is described by a hop. Below this a
#: file is treated as v18 shape (v1-v17 were additive-only), which is why the
#: floor is documented rather than enforced with an error.
SUPPORTED_FLOOR = 18


def migrate(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``d`` normalised to the current :data:`SCHEMA_VERSION` shape.

    Applies every hop from the file's own version upward, in order, on a deep
    copy -- the caller's dict is never mutated, which matters because the GUI
    hands the same dict to the JSON editor.

    An unversioned dict is assumed to predate the versioned era and is run
    through the whole chain; a dict claiming a version *newer* than this build is
    passed through untouched, so a forward-compatible file degrades to "read what
    you understand" instead of being mangled by hops that do not apply to it.
    """
    out = copy.deepcopy(d)
    version = out.get("schema_version")
    version = SUPPORTED_FLOOR if not isinstance(version, int) else version

    for hop_from in sorted(MIGRATIONS):
        if version <= hop_from:
            out = MIGRATIONS[hop_from](out)
    out["schema_version"] = max(version, SCHEMA_VERSION) if version > SCHEMA_VERSION \
        else SCHEMA_VERSION
    return out


def applied_hops(from_version: int) -> List[int]:
    """Which hops :func:`migrate` would run for a file of ``from_version``.

    Exposed for the tests and for a future "this file was migrated from vN"
    provenance line in the methods statement.
    """
    return [h for h in sorted(MIGRATIONS) if from_version <= h]
