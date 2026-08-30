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
from sloads.export import directory_dialog as dialog
from sloads.export import report_package as pkg
from sloads.models.report import (
    DATE_MAX,
    DATE_MIN,
    ReportSpec,
    SignatureRow,
    default_spec,
    is_draft,
    parse_date,
)
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
    "report_introduction", "report_limitations",
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


def _browse_block() -> str:
    """Choose the folder reports are written to.

    **The OS dialog is the control; the in-app browser is the fallback.** The
    oracle GUI runs locally, so the machine serving this page is the machine the
    user is sitting at (OR-22) and the operating system's own folder chooser is
    reachable through :mod:`sloads.export.directory_dialog`. It is what the user
    already knows how to drive, and it can reach anywhere on the disk in one
    gesture rather than one directory per click.

    The click-through browser stays for the machine that has no dialog, and for
    the case where the dialog cannot be raised. It is not dead code: a folder
    chooser that silently does nothing would leave no way to set the location at
    all, and this page's whole job is to write somewhere.

    The page holds only the current path as a string. Every question about what
    that string *means* -- does it exist, what is inside it, may we read it --
    is answered in :mod:`sloads.export`, because this page may not import ``os``
    (gate G1).
    """
    anchors = pkg.location_anchors(saved_path())
    if _ROOT not in st.session_state:
        st.session_state[_ROOT] = pkg.browse_start(anchors[0][1])
    here = st.session_state[_ROOT]

    shown, chooser = st.columns([3, 1])
    shown.markdown(f"**Saving reports to**  \n`{here}`")
    if chooser.button("📂 Choose folder…", key=widget_key("report_pick_btn"),
                      width="stretch", disabled=not dialog.native_picker_available()):
        picked = dialog.choose_directory(
            here, prompt="Choose the folder to write report packages into")
        if picked:
            st.session_state[_ROOT] = picked
            st.rerun()
        # No message on ``None``: Cancel is a normal answer, and saying
        # "no folder chosen" to someone who deliberately pressed Cancel is noise.

    with st.expander("Or browse to it here", expanded=False):
        labels = [label for label, _path in anchors]
        jump = st.selectbox("Start from", labels, key=widget_key("report_anchor"))
        if st.button("Go", key=widget_key("report_anchor_btn"), width="stretch"):
            st.session_state[_ROOT] = pkg.browse_start(dict(anchors)[jump])
            st.rerun()

        up, into = st.columns([1, 2])
        with up:
            if st.button("⬆ Up one level", key=widget_key("report_up_btn"),
                         width="stretch", disabled=pkg.is_root(here)):
                st.session_state[_ROOT] = pkg.parent_of(here)
                st.rerun()
        subdirs = pkg.list_subdirs(here)
        with into:
            chosen = st.selectbox("Folders here", subdirs or ["(no subfolders)"],
                                  key=widget_key("report_subdir"),
                                  disabled=not subdirs, label_visibility="collapsed")
            if st.button("Open folder ▶", key=widget_key("report_down_btn"),
                         width="stretch", disabled=not subdirs):
                st.session_state[_ROOT] = pkg.child_of(here, chosen)
                st.rerun()

        made = st.text_input("New folder here", key=widget_key("report_mkdir"),
                             placeholder="e.g. Programme-X")
        if st.button("Create and use", key=widget_key("report_mkdir_btn"),
                     width="stretch", disabled=not made.strip()):
            # A folder name, not a path -- ``create_subdir`` refuses a separator
            # rather than normalising one, so this control cannot walk out of
            # the folder it is displayed in.
            try:
                st.session_state[_ROOT] = pkg.create_subdir(here, made)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
            else:
                st.rerun()

    if not pkg.is_writable(here):
        # Choosing a folder is not being granted it: macOS keeps ~/Desktop and
        # friends behind TCC, and the OS dialog hands back a path this process
        # may still not be allowed to write. Said here, before the build, rather
        # than as a failure after the user has filled the whole page in.
        st.warning(
            f"`{here}` cannot be written to by this app. On macOS, Desktop, "
            "Documents and Downloads need permission granted to the terminal "
            "running sloads (System Settings ▸ Privacy & Security ▸ Files and "
            "Folders, or Full Disk Access). Choose another folder, or grant it "
            "and reopen this page.")
    return st.session_state[_ROOT]


def _date(label: str, value: str, key: str, *, help_text: str = "") -> str:
    """A date picker that stores an ISO string -- and starts **empty**.

    ``st.date_input`` defaults its value to *today*. Left alone it would stamp
    the current date onto an issue date and three signature dates that nobody
    filled in, and the document would then assert, on its title page, that it
    was issued and signed today. That is the same class as the placeholder that
    printed "Not analysed" over the generator's own gap: a control quietly
    putting words in the author's mouth. So the value is always passed
    explicitly, and an unset date stays unset.

    A stored value that is **not** a date is preserved rather than eaten. The
    spec is a JSON file a person is meant to be able to edit, so a hand-typed
    "TBD" has to survive being loaded; the picker shows empty, the page says
    what is in the file, and the string stands until a real date replaces it.
    """
    parsed = parse_date(value)
    if value and parsed is None:
        st.caption(f"⚠ `{value}` is not a date. Pick one to replace it.")
    chosen = st.date_input(label, value=parsed, key=widget_key(key),
                           min_value=DATE_MIN, max_value=DATE_MAX,
                           format="YYYY-MM-DD", help=help_text or None)
    if chosen is None:
        # Cleared, or never set. Keep an unparseable stored value; a real date
        # that the user has just cleared is genuinely cleared.
        return "" if parsed is not None else value
    return chosen.isoformat()


def _location_block() -> None:
    """Where packages live, and which one is open (OR-28, OR-29)."""
    st.subheader("Report package")
    st.caption(
        "One issue, one directory. The directory holds the report source, the "
        "spec you are editing, the data behind the document and the project it "
        "was built from -- so an issue can be archived and reopened as one thing."
    )
    root = _browse_block()

    found = pkg.discover_packages(root)
    options = [_NEW] + found
    current = st.session_state.get(_DIRNAME) or _NEW
    chosen = st.selectbox("Open", options,
                          index=options.index(current) if current in options else 0,
                          key=widget_key("report_open"))
    # An explicit Open, not a load on selection change: opening replaces the
    # spec being edited, and the sidebar guards the same act behind a button for
    # the same reason. Selecting is browsing; the discard happens on the click.
    switching = chosen != current
    if switching and _dirty():
        st.warning(
            f"**{current}** has unsaved changes. Opening **{chosen}** discards "
            "them. Save first if you want to keep them.")
    if st.button("Open", key=widget_key("report_open_btn"), width="stretch",
                 disabled=not switching):
        st.session_state[_DIRNAME] = chosen
        _set_spec(pkg.read_spec(root, "" if chosen == _NEW else chosen))
        _mark_saved()
        _retire_spec_widgets()
        st.rerun()
    if not found:
        st.caption("No report packages in this folder yet. Fill in a report "
                   "number and build to create the first.")


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
        issue_date = _date("Issue date", spec.issue_date, "report_issue_date",
                           help_text="The date this issue is released. "
                                     "Left empty until it is.")
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


def _prose_block(project) -> None:
    """Section 1's prose: the introduction, and limitations and scope.

    Both open **pre-filled** with the generator's text and are the author's
    from then on (owner's decision, 2026-08-30). That makes each a snapshot:
    a later improvement to the default will not reach a report already written,
    which is the price of a signed issue continuing to say what it said when it
    was signed. The empty spec field means "not yet edited", so the renderer
    falls back to the same default and an old spec still produces a full
    document.
    """
    spec = _spec()
    st.subheader("Introduction")
    st.caption("Section 1 of the report. Pre-filled with the standard text -- "
               "edit it freely; what you leave here is what the document says.")
    introduction = _text("Introduction", spec.introduction or oc.default_introduction(),
                         "report_introduction", area=True)
    st.caption("Limitations and scope appears as a subsection of the "
               "introduction. It is pre-filled from the same methods and "
               "limitations statement the CSV and deck exports carry, so the "
               "report opens saying what they say. Once edited it is yours, and "
               "will not track later changes to the project.")
    limitations = _text("Limitations and scope",
                        spec.limitations or oc.default_limitations(project),
                        "report_limitations", area=True)
    _set_spec(replace(spec, introduction=introduction, limitations=limitations))


def _signature_row(label: str, row: SignatureRow, key: str) -> SignatureRow:
    a, b, c = st.columns([2, 2, 1])
    with a:
        name = _text(f"{label} - name", row.name, f"{key}_name")
    with b:
        role = _text(f"{label} - function", row.role, f"{key}_role")
    with c:
        date = _date(f"{label} - date", row.date, f"{key}_date")
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
                      for label, value in fingerprint_owner.anchors(
                          project, tool_version=pkg.tool_version())]),
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
        # Same failure class the build already reports: a chosen folder is not
        # necessarily a writable one, and Save must say so rather than traceback.
        try:
            pkg.write_spec(root, dirname, spec)
        except OSError as exc:
            st.error(f"Could not save the spec: {exc}")
        else:
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
    _prose_block(project)
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
