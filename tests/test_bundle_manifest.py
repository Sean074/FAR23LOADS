"""The Export zip against Appendix A: every file the bundle carries is named.

Review **CR-C-1**: the LRA beam model shipped inside the bundle from 0.6.0 with
no manifest row -- the F-D2 class ("an artifact the controlling document does
not name travels without a basis") re-opened one release later, on the newest
deliverable. The gate that should have caught it read the *manifest* against a
hand-kept set in ``test_report_content.SUMMARISED_IN``; nothing read the zip.
So the manifest and the bundle drifted apart in the one direction no test could
see, and a second sweep here found two more members in the same state: the
summary report's own ``.tex`` and ``.pdf``.

This module reads the artifact the user receives. ``sloads.report.bundle`` is
the single owner of the member list (the Export page loops over it), so the
names asserted below are the names in the downloaded zip, and every one of them
must resolve to a row of the rendered manifest table.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import io  # noqa: E402
from sloads.export import mass_cards as mc  # noqa: E402
from sloads.export import sbeam_bridge as sb  # noqa: E402
from sloads.export.balanced_deck import balanced_deck  # noqa: E402
from sloads.export.lra_model import lra_model_bdf  # noqa: E402
from sloads.modules.balance import build_balanced_cases  # noqa: E402
from sloads.registry import run_all_modules  # noqa: E402
from sloads.report.bundle import (  # noqa: E402
    bundle_members,
    bundle_zip_bytes,
    manifest_name_for,
)
from sloads.report.content import build_report, component_loads  # noqa: E402
import sloads.modules  # noqa: E402,F401  (module registration)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXAMPLES = os.path.join(_ROOT, "examples")
_VIEW = os.path.join(_ROOT, "app", "views", "export_report.py")


def _try(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs) or ""
    except (ValueError, ZeroDivisionError, KeyError, IndexError):
        return ""


#: The sbeam artifacts, keyed exactly as the Export page keys them. Kept in step
#: with the page by :func:`test_the_view_builds_no_artifact_this_gate_cannot`,
#: which reads the page's own ``_bdf_artifacts[...]`` assignments -- so a new
#: deck cannot be added to the bundle without arriving here, and from here it
#: cannot reach the zip without a manifest row.
def _sbeam_artifacts(project, comps, cases):
    art = {}
    if comps.wing:
        from sloads.derived_geometry import sob_station

        art["wing_loads.bdf"] = _try(sb.force_moment_cards, comps.wing)
        art["wing_span_loads.csv"] = _try(sb.span_load_csv, comps.wing)
        art["wing_stick.bdf"] = _try(sb.stick_model_bdf, comps.wing,
                                     sob=sob_station(project))
    if comps.body:
        art["fuselage_loads.bdf"] = _try(sb.body_force_moment_cards, comps.body)
        art["fuselage_span_loads.csv"] = _try(sb.body_span_load_csv, comps.body)
        art["fuselage_fitting_loads.csv"] = _try(sb.body_fitting_load_csv, comps.body)
    if comps.tail:
        art["tail_loads.bdf"] = _try(sb.tail_force_moment_cards, comps.tail)
        art["tail_chordwise.csv"] = _try(sb.tail_chordwise_csv, comps.tail)
    if comps.control:
        art["control_surface_loads.bdf"] = _try(
            sb.control_surface_force_moment_cards, comps.control)
        art["control_surface_loads.csv"] = _try(sb.control_surface_csv, comps.control)
    if cases:
        art["balanced_airframe.bdf"] = _try(balanced_deck, project, cases=cases)
        art["lra_model.bdf"] = _try(lra_model_bdf, project, cases=cases)
    if project.weight is not None and project.weight.items:
        art["mass_model.bdf"] = _try(mc.conm2_fragment, project)
        art["mass_check.bdf"] = _try(mc.mass_check_deck, project)
        art["inertia_only.bdf"] = _try(mc.inertia_only_cards, project)
    return art


def _bundle(name, *, with_pdf=False):
    """``(zip namelist, manifest row names, stem)`` for one fixture."""
    project = io.load_project(os.path.join(_EXAMPLES, f"{name}.project.json"))
    stem = (project.name or "project").strip().replace(" ", "_") or "project"
    results = run_all_modules(project)
    comps = component_loads(project)
    skipped = []
    cases = _try(build_balanced_cases, project, skipped) or []
    doc = build_report(project, module_results=results, components=comps,
                       tool_version="test")
    tex = "\\documentclass{article}"  # content is irrelevant; presence is not
    members = bundle_members(
        stem,
        project_json=io.project_to_json(project),
        text_report="report text",
        module_csvs={mr.module: _try(io.load_cases_csv, mr) for mr in results},
        case_index_csv=_try(sb.case_index_csv_from, comps.wing or [], comps.body or [],
                            comps.tail or [], comps.control,
                            *(mr.conditions for mr in results)),
        safety_factors_csv=_try(sb.safety_factors_csv, project),
        gear_report_csv=_try(sb.gear_report_csv, project),
        methods="methods",
        report_tex=tex,
        report_pdf=b"%PDF-1.4" if with_pdf else None,
        sbeam_artifacts=_sbeam_artifacts(project, comps, cases),
    )
    manifest = {row[0] for row
                in doc.section("Appendix A. Bundle manifest").table.rows}
    return members, manifest, stem


def test_every_file_the_bundle_carries_is_named_by_the_manifest():
    """The gate CR-C-1 asks for, in both of the shapes the defect took.

    Runs on the fixture that exports every channel (``ga6_normal``), with the
    PDF present, so the assertion covers the compiled-report member too.
    """
    members, manifest, stem = _bundle("ga6_normal", with_pdf=True)
    unnamed = sorted({m.manifest_name for m in members} - manifest)
    assert not unnamed, (
        "these files ship in the bundle with no manifest row (F-D2/CR-C-1): "
        + ", ".join(unnamed))
    # ...and the row that started it is present under its real name.
    assert "sbeam/<project>_lra_model.bdf" in manifest
    assert f"sbeam/{stem}_lra_model.bdf" in {m.name for m in members}


def test_the_manifest_names_no_file_the_bundle_does_not_carry():
    """The other direction, which is the same defect pointing outward: a row for
    an absent file tells the analyst to look for a basis that is not there.

    ``ga6_normal`` exports every channel, so on it the two sets are equal.
    """
    members, manifest, _ = _bundle("ga6_normal", with_pdf=True)
    missing = sorted(manifest - {m.manifest_name for m in members})
    assert not missing, (
        "manifest rows with no file behind them: " + ", ".join(missing))


def test_a_refused_lra_model_is_neither_shipped_nor_manifested():
    """``concept_heavy`` assembles balanced cases and its LRA model **refuses**
    (no side of body resolves -- ``LraRefusal``, a stated absence, BM-3/LM-4).

    This is why the manifest row is gated on the model building rather than on
    ``run.cases``: the obvious gate would have named a deck this bundle does not
    contain, on a shipped fixture.
    """
    members, manifest, _ = _bundle("concept_heavy")
    assert "sbeam/<project>_lra_model.bdf" not in manifest
    assert not [m for m in members if "lra_model" in m.name]
    # ...and the rest of the bundle is still fully named.
    assert not {m.manifest_name for m in members} - manifest


def test_the_pdf_is_manifested_only_as_a_conditional_member():
    """The compiled PDF rides in the zip only when a TeX engine ran, but its
    manifest row is unconditional and says so -- the manifest describes the
    bundle's file set, and a reader must be able to tell an absent file from an
    unnamed one."""
    with_pdf, manifest, stem = _bundle("ga6_normal", with_pdf=True)
    without, _, _ = _bundle("ga6_normal")
    assert f"{stem}_summary_report.pdf" in {m.name for m in with_pdf}
    assert f"{stem}_summary_report.pdf" not in {m.name for m in without}
    assert "<project>_summary_report.pdf" in manifest
    assert "<project>_summary_report.tex" in manifest


def test_the_view_builds_no_artifact_this_gate_cannot():
    """Rule 3, the load-bearing half: the gate is only structural if the page
    cannot grow a member behind its back. Every ``_bdf_artifacts[...]`` key the
    Export page assigns must be one this module builds, so a new deck fails here
    first and reaches the zip only once it has a manifest row."""
    import inspect

    src = open(_VIEW, encoding="utf-8").read()
    keys = set(re.findall(r'_bdf_artifacts\["([^"]+)"\]\s*=', src))
    assert keys, "the artifact assignments moved -- this guard reads nothing"
    built = set(re.findall(r'art\["([^"]+)"\]\s*=',
                           inspect.getsource(_sbeam_artifacts)))
    assert keys <= built, (
        "the Export page builds artifacts this gate does not: "
        + ", ".join(sorted(keys - built)))


def test_the_page_writes_no_zip_member_of_its_own():
    """The member list has one owner. A ``writestr`` back in the view is how the
    two sets came apart in the first place, so the page may not have one."""
    src = open(_VIEW, encoding="utf-8").read()
    assert "writestr" not in src, (
        "app/views/export_report.py writes a zip member directly; add it to "
        "sloads/report/bundle.py with its manifest row instead")


def test_manifest_name_for_is_the_stem_substitution():
    assert manifest_name_for("sbeam/ga6_wing_loads.bdf", "ga6") == \
        "sbeam/<project>_wing_loads.bdf"
    assert manifest_name_for("ga6.json", "ga6") == "<project>.json"


def test_the_zip_bytes_are_the_member_list():
    """``bundle_zip_bytes`` writes the plan and nothing else -- what the gate
    asserts about members is therefore true of the downloaded file."""
    import zipfile
    import io as _io

    members, _, _ = _bundle("ga6_normal", with_pdf=True)
    with zipfile.ZipFile(_io.BytesIO(bundle_zip_bytes(members))) as z:
        assert z.namelist() == [m.name for m in members]


if __name__ == "__main__":  # zero-dependency self-runner (see PROGRAM_SPEC)
    import traceback

    failures = 0
    for _name, _fn in sorted(list(globals().items())):
        if not _name.startswith("test_") or not callable(_fn):
            continue
        try:
            _fn()
            print(f"ok   {_name}")
        except Exception:  # noqa: BLE001 - a self-runner reports, it does not raise
            failures += 1
            print(f"FAIL {_name}")
            traceback.print_exc()
    raise SystemExit(1 if failures else 0)
