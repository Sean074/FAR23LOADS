"""The oracle GUI's **Report** page: edit an issue's spec, build its package.

Design note 44, OR-16. This is the one page of the oracle GUI that is not a
workflow step -- it produces a document *about* the analysis rather than a part
of it -- which is why it is registered directly on ``st.navigation`` and left out
of ``register_pages`` (that mapping is the derived step set, gate G2, and it stays
exactly that).

**The page computes nothing.** Not a number, not a hash, not a path, not the
time: every one of those comes from ``sloads``. That is enforced rather than
intended -- the oracle GUI may not import ``os``, ``json``, ``hashlib`` or
``datetime`` at all (gate G1), so a page that tried to build its own file paths
would fail the import gate before it failed review.

**The build writes a directory, and offers no download.** The oracle GUI is run
locally, so the user's machine is the server (OR-22); and the GUI has exactly one
download call site by gate, which belongs to the results page.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, List

import pandas as pd
import streamlit as st

from app_shell.components import active_project, gate
from app_shell.project_state import saved_path
from app_shell.widget_keys import widget_key
from sloads import io as sloads_io
from sloads import workflow as wf
from sloads.export import report_package as pkg
from sloads.models.report import ReportSpec, SignatureRow, default_spec, is_draft
from sloads.report import fingerprint as fingerprint_owner
from sloads.report import oracle_content as oc
from sloads.units import UnitSystem

PAGE_TITLE = "Report"

#: Session-state keys, page-local by OR-17: the report belongs to this page, and
#: ``app_shell``'s sidebar is shared with ``app/``, which has no report.
_ROOT = "report_root"
_DIRNAME = "report_dirname"
_SPEC = "report_spec"
_SAVED = "report_spec_saved"

_NEW = "New report"

#: Every widget key this page seeds from the spec.
#:
#: Streamlit resolves a keyed widget from session state and **ignores the
#: ``value=`` handed to it on later reruns** -- so opening a different issue
#: would redraw the previous one's title and signatures over the spec that was
#: just loaded, and saving would then write them back. Retiring these keys on a
#: switch is the fix; ``bump_generation()`` is not, because that is the shared
#: project-replaced signal and would retire every analysis page's widgets too.
_SPEC_WIDGETS = (
    "report_title", "report_number", "report_revision", "report_issue_date",
    "report_org", "report_customer", "report_abstract", "report_marking",
    "report_distribution", "report_units",
    "report_prepared_name", "report_prepared_role", "report_prepared_date",
    "report_checked_name", "report_checked_role", "report_checked_date",
    "report_approved_name", "report_approved_role", "report_approved_date",
)


def _retire_spec_widgets() -> None:
    """Drop the spec widgets' state so they re-seed from the spec just loaded."""
    for base in _SPEC_WIDGETS:
        st.session_state.pop(widget_key(base), None)
    for step in oc.analysis_steps():
        st.session_state.pop(widget_key(f"report_sel_{step.key}"), None)


def _spec() -> ReportSpec:
    return st.session_state.get(_SPEC) or default_spec()


def _set_spec(spec: ReportSpec) -> None:
    st.session_state[_SPEC] = spec


def _dirty() -> bool:
    """Whether the spec differs from what was last loaded or saved.

    Compared through :func:`sloads.io.report_spec_to_dict`, the same mapping
    owner the file is written with, so "unsaved" means exactly "would write
    different bytes" rather than a field-by-field opinion that can drift from it.
    """
    return sloads_io.report_spec_to_dict(_spec()) != st.session_state.get(_SAVED)


def _mark_saved() -> None:
    st.session_state[_SAVED] = sloads_io.report_spec_to_dict(_spec())


def _text(label: str, value: str, key: str, *, help_text: str = "",
          area: bool = False) -> str:
    widget = st.text_area if area else st.text_input
    return widget(label, value=value, key=widget_key(key), help=help_text or None)


def _location_block() -> None:
    """Where packages live, and which one is open (OR-28, OR-29)."""
    st.subheader("Report package")
    st.caption(
        "One issue, one directory. The directory holds the report source, the "
        "spec you are editing, the data behind the document and the project it "
        "was built from -- so an issue can be archived and reopened as one thing."
    )
    default_root = sloads_io.default_report_root(saved_path())
    root = _text("Reports folder", st.session_state.get(_ROOT, default_root),
                 _ROOT,
                 help_text="Defaults to a 'reports' folder beside the project "
                           "file, so a report travels with the airplane it "
                           "documents.")
    st.session_state[_ROOT] = root

    found = pkg.discover_packages(root)
    options = [_NEW] + found
    current = st.session_state.get(_DIRNAME) or _NEW
    chosen = st.selectbox("Open", options,
                          index=options.index(current) if current in options else 0,
                          key=widget_key("report_open"))
    if chosen != st.session_state.get(_DIRNAME):
        st.session_state[_DIRNAME] = chosen
        _set_spec(pkg.read_spec(root, "" if chosen == _NEW else chosen))
        _mark_saved()
        _retire_spec_widgets()
        st.rerun()
    if not found:
        st.caption("No report packages here yet. Fill in a report number and "
                   "build to create the first.")


def _identity_block() -> None:
    spec = _spec()
    st.subheader("Document identity")
    left, right = st.columns(2)
    with left:
        title = _text("Report title", spec.title, "report_title")
        number = _text("Report number", spec.report_number, "report_number",
                       help_text="Names the package directory, with the "
                                 "revision. Never the clock, so a rebuild "
                                 "lands on the same directory.")
        revision = _text("Revision", spec.revision, "report_revision")
    with right:
        issue_date = _text("Issue date", spec.issue_date, "report_issue_date")
        organisation = _text("Issuing organisation", spec.organisation,
                             "report_org")
        customer = _text("Customer / programme", spec.customer, "report_customer")
    _set_spec(replace(spec, title=title, report_number=number, revision=revision,
                      issue_date=issue_date, organisation=organisation,
                      customer=customer))


def _abstract_block() -> None:
    spec = _spec()
    st.subheader("Abstract")
    st.caption("The author's abstract. The computed summary of governing loads "
               "is a separate, generated section -- it is not this field.")
    _set_spec(replace(spec, abstract=_text(
        "Abstract", spec.abstract, "report_abstract", area=True)))


def _signature_row(label: str, row: SignatureRow, key: str) -> SignatureRow:
    a, b, c = st.columns([2, 2, 1])
    with a:
        name = _text(f"{label} - name", row.name, f"{key}_name")
    with b:
        role = _text(f"{label} - function", row.role, f"{key}_role")
    with c:
        date = _text(f"{label} - date", row.date, f"{key}_date")
    return SignatureRow(name=name, role=role, date=date)


def _signature_block() -> None:
    spec = _spec()
    st.subheader("Signatures")
    prepared = _signature_row("Prepared by", spec.prepared, "report_prepared")
    checked = _signature_row("Checked by", spec.checked, "report_checked")
    approved = _signature_row("Approved by", spec.approved, "report_approved")
    spec = replace(spec, prepared=prepared, checked=checked, approved=approved)
    _set_spec(spec)
    if is_draft(spec):
        st.info("Any empty name makes this a DRAFT: the document carries a "
                "watermark and a footer saying so. It still builds -- the point "
                "is that it never presents itself as approved by default.")
    else:
        st.success("All three signatures are present: this issue builds without "
                   "the DRAFT marking.")


def _marking_block() -> None:
    spec = _spec()
    st.subheader("Distribution and marking")
    marking = _text("Classification marking", spec.marking, "report_marking",
                    help_text="Rendered in every page footer, not only on the "
                              "cover.")
    distribution = _text("Distribution statement", spec.distribution,
                         "report_distribution", area=True)
    system = st.radio(
        "Units for the document", list(UnitSystem),
        index=list(UnitSystem).index(spec.unit_system),
        format_func=lambda s: "SI" if s is UnitSystem.SI else "Imperial",
        horizontal=True, key=widget_key("report_units"))
    st.caption("This governs the **document**. The sidebar's unit toggle governs "
               "what the analysis pages display; the two are deliberately "
               "separate, so a report plus a project is a complete recipe.")
    _set_spec(replace(spec, marking=marking, distribution=distribution,
                      unit_system=system))


def _selection_block() -> List[wf.WorkflowStep]:
    spec = _spec()
    st.subheader("Sections in this issue")
    st.caption("A deselected section is still printed, stating that it was "
               "excluded -- a reader is never handed a shortened document "
               "without being told.")
    steps = oc.analysis_steps()
    excluded = set(spec.excluded_steps)
    columns = st.columns(3)
    keep: List[str] = []
    for index, step in enumerate(steps):
        with columns[index % 3]:
            if not st.checkbox(step.title, value=step.key not in excluded,
                               key=widget_key(f"report_sel_{step.key}")):
                keep.append(step.key)
    _set_spec(replace(spec, excluded_steps=tuple(keep)))
    return steps


def _preflight_block(project) -> List[oc.SectionPlan]:
    spec = _spec()
    plan = oc.section_plan(project, spec)
    st.subheader("Preflight")
    rows: List[Dict[str, str]] = []
    for entry in plan:
        rows.append({
            "Section": entry.number,
            "Title": entry.title,
            "Selected": "yes" if entry.selected else "no",
            "Inputs present": "yes" if entry.inputs_present else "no",
            "State": entry.state.value,
            "Reason": entry.reason or "-",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(
        "'Selected' and 'inputs present' stay visible even where another state "
        "takes precedence, so a choice you made is never hidden by a limitation "
        "of the generator.")
    return plan


def _provenance_block(project) -> str:
    spec = _spec()
    st.subheader("Provenance")
    current = fingerprint_owner.fingerprint(project)
    ok, message = fingerprint_owner.identity_matches(
        spec.identity.fingerprint, spec.identity.fingerprint_version, project)
    (st.success if ok else st.warning)(message)
    st.dataframe(
        pd.DataFrame([{"Anchor": label, "Value": value}
                      for label, value in fingerprint_owner.anchors(project)]),
        width="stretch", hide_index=True)
    if st.button("Baseline this report against the current project",
                 key=widget_key("report_baseline"),
                 help="Records the current project's identity and fingerprint "
                      "in the spec. Do this when the report is authored, or "
                      "deliberately re-baselined after a project revision."):
        _set_spec(replace(spec, identity=replace(
            spec.identity, project_name=project.name,
            fingerprint=current,
            fingerprint_version=fingerprint_owner.FINGERPRINT_VERSION)))
        st.rerun()
    return current


def _build_block(project, fingerprint: str) -> None:
    spec = _spec()
    root = st.session_state.get(_ROOT, "")
    st.subheader("Build")
    dirname = sloads_io.report_package_dirname(spec.report_number, spec.revision)
    st.caption(f"Writes `{dirname}` into the reports folder, replacing that "
               "issue's previous build. Bumping the revision makes a new "
               "directory beside it, so an issued revision is never overwritten "
               "by continued work.")
    left, right = st.columns(2)
    if left.button("Save spec", key=widget_key("report_save"),
                   disabled=not _dirty()):
        pkg.write_spec(root, dirname, spec)
        st.session_state[_DIRNAME] = dirname
        _mark_saved()
        st.success("Spec saved.")
    if right.button("Build issue package", type="primary",
                    key=widget_key("report_build")):
        try:
            written = pkg.build_package(
                project, spec, root=root,
                fingerprint=fingerprint,
                fingerprint_version=fingerprint_owner.FINGERPRINT_VERSION)
        except (OSError, ValueError) as exc:
            st.error(f"{type(exc).__name__}: {exc}")
        else:
            st.session_state[_DIRNAME] = dirname
            _mark_saved()
            st.success(f"Issue package written to {written}")
            st.caption("Compile report.tex from inside that directory so its "
                       "relative references resolve. Two passes are needed for "
                       "the contents list and the draft mark to settle.")
    if _dirty():
        st.caption("The spec has unsaved edits. Building writes them into the "
                   "package as part of the issue.")


def render_report_page() -> None:
    """The page body, bound into the oracle GUI's navigation by ``Oracle.py``."""
    st.title(PAGE_TITLE)
    st.caption("A formal technical report of this project's FAR 23 analysis, "
               "built from the analysis itself.")
    project = active_project()
    if project is None:
        gate("Load or create a project before writing a report.")
        return
    if _SPEC not in st.session_state:
        _set_spec(default_spec())
        _mark_saved()

    _location_block()
    st.divider()
    _identity_block()
    st.divider()
    _abstract_block()
    st.divider()
    _signature_block()
    st.divider()
    _marking_block()
    st.divider()
    _selection_block()
    st.divider()
    _preflight_block(project)
    st.divider()
    fingerprint = _provenance_block(project)
    st.divider()
    _build_block(project, fingerprint)


__all__ = ["PAGE_TITLE", "render_report_page"]
