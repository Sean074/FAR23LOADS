#!/usr/bin/env python3
"""Generate ``docs/10_standard/DATA_DICTIONARY.md`` from the dataclasses.

The ``project.json`` schema (``SCHEMA_VERSION`` is deep and climbing) has no
reference other than ``sloads/models.py`` itself. This script introspects the
**input** slices of :class:`sloads.models.Project` and emits a markdown data
dictionary: for every field its type, default, a units hint, and -- at *slice*
granularity -- the page that owns it and the calc modules that consume it.

Design (see backlog M2-11, decided 2026-07-20):

* **Source of truth is the code.** Type and default come from
  :func:`dataclasses.fields` / :func:`typing.get_type_hints`; the *units* hint is
  parsed from each field's trailing ``# comment`` in the source (falling back to a
  guess from the field-name suffix, e.g. ``_lb`` -> ``lb``). Comments are prose,
  not a structured units field, so the "Units / notes" column reproduces the
  inline comment verbatim -- treat it as a hint, not a contract.
* **Owning page / consumers are slice-level, not field-level.** ``workflow.py``
  records ``produces``/``requires`` per *slice*, not per field, so a field
  inherits its root slice's page and consumer list. The owning page is the step
  that ``produces`` the slice (plus a small override table for the slices
  ``workflow.py`` does not attribute by ``produces``); consumers are the calc
  modules whose source reads ``.<slice>``.
* **Input slices only.** The result slices (``envelope``/``mass``/``loads``) are
  outputs, not ``project.json`` inputs, and are excluded.

Run it (writes the doc in place; no third-party deps):

    .venv/bin/python docs/generate_data_dict.py

Re-run after any ``models.py`` change so the dictionary tracks the schema.
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
import re
import typing
from pathlib import Path

import sloads.field_registry as fr
import sloads.models as m
import sloads.workflow as w

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "sloads" / "modules"
OUT_PATH = REPO_ROOT / "docs" / "10_standard" / "DATA_DICTIONARY.md"

# --------------------------------------------------------------------------- #
# The Project *input* slices, in workflow order. (attr, human-readable role)
# Result slices (envelope/mass/loads) and pure metadata (schema_version) are out
# of scope -- this is a project.json *input* dictionary.
# --------------------------------------------------------------------------- #
INPUT_SLICES = [
    ("engines", "Engine-mount inputs (one per engine)"),
    ("engine_layout", "Engine layout constraint (enum)"),
    ("weight", "Weight database (WTESTIMA / WTONECG / WTENV)"),
    ("geometry", "Geometry single-source (WINGGEOM + fuselage + empennage)"),
    ("speeds", "Structural design speeds & load factors (STRSPEED)"),
    ("aero", "Spanwise airload inputs (AIRLOADS)"),
    ("aero_coeffs", "Airplane-less-tail aero coefficients (FLTLOADS input)"),
    ("flight_loads", "Flight envelope / balancing tail loads (FLTLOADS)"),
    ("wing_mass", "Wing-mass distribution & load cases (WINGINER)"),
    ("fuselage_mass", "Fuselage mass distribution (SELECT / Ch 15)"),
    ("tail_mass", "Empennage surface mass override — derived from the component-tagged weight.items by default (plan 09 T-3)"),
    ("select_input", "Critical-load selection inputs (SELECT)"),
    ("tail_loads", "Rational horizontal-tail inputs (via geometry.empennage)"),
    ("vtail_loads", "Rational vertical-tail inputs (via geometry.empennage)"),
    ("aileron_loads", "Aileron simplified loads (AILERON)"),
    ("flap_loads", "Flap simplified loads (FLAPLOAD)"),
    ("tab_loads", "Tab simplified loads (TABLOADS)"),
    ("one_engine_out", "One-engine-out v-tail loads (ONENGOUT)"),
    ("landing", "Landing loads (LANDLOAD / GEARLOAD)"),
    ("include_far25", "Opt-in FAR 25 supplemental cases (flag)"),
]

# Owning page comes from `sloads.field_registry` (design note 32, OG-14): the
# registry declares an editing page **per field**, so this generator no longer
# keeps its own slice-level override table. The two disagreed by construction --
# the overrides were a guess at what workflow.py's `produces` could not
# attribute, while the registry states it and is drift-guarded.

# Field-name suffix -> units, used when the inline comment carries no units hint.
SUFFIX_UNITS = [
    ("_rad_s", "rad/s"),
    ("_sqft", "ft^2"),
    ("_deg", "deg"),
    ("_lb", "lb"),
    ("_in", "in"),
    ("_ft", "ft"),
    ("_kt", "KEAS"),
    ("_hp", "hp"),
    ("_s", "s"),
    ("_pct_mac", "% MAC"),
    ("_mac", "% MAC"),
]


def _resolve_hints(cls):
    """`typing.get_type_hints`, tolerant of forward refs to models globals."""
    try:
        return typing.get_type_hints(cls, globalns=vars(m))
    except Exception:
        # Fall back to the raw string annotations from dataclasses.fields.
        return {f.name: f.type for f in dataclasses.fields(cls)}


def _inline_comments(cls):
    """Map field name -> trailing ``# comment`` text from the class source."""
    out = {}
    try:
        src = inspect.getsource(cls)
    except (OSError, TypeError):
        return out
    field_line = re.compile(r"^\s*([a-zA-Z_]\w*)\s*:\s*[^#]*?#\s*(.+?)\s*$")
    for line in src.splitlines():
        mo = field_line.match(line)
        if mo:
            name, comment = mo.group(1), mo.group(2)
            # First comment wins (the field's own line, not a continuation).
            out.setdefault(name, comment)
    return out


def _units_hint(name, comment):
    """A best-effort units string: the inline comment, else a suffix guess."""
    if comment:
        return comment
    for suffix, units in SUFFIX_UNITS:
        if name.endswith(suffix):
            return units
    return ""


def _type_str(s):
    """Clean a raw string annotation (the get_type_hints-failed fallback)."""
    s = re.sub(r"\bsloads\.models\.", "", str(s))
    s = re.sub(r"\btyping\.", "", s)
    return s


def _render_type(ann):
    """Render a resolved annotation to a short string."""
    origin = typing.get_origin(ann)
    args = typing.get_args(ann)
    if origin is None:
        if hasattr(ann, "__name__"):
            return ann.__name__
        return _type_str(str(ann))
    if origin in (list, typing.List):
        return f"List[{_render_type(args[0])}]"
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        inner = " | ".join(_render_type(a) for a in non_none)
        if type(None) in args:
            return f"Optional[{inner}]"
        return inner
    if origin in (tuple, typing.Tuple):
        return "Tuple[" + ", ".join(_render_type(a) for a in args) + "]"
    name = getattr(origin, "__name__", str(origin))
    return f"{name}[" + ", ".join(_render_type(a) for a in args) + "]"


def _nested_dataclasses(ann, acc):
    """Collect dataclass types referenced by an annotation into ``acc`` (a list)."""
    if dataclasses.is_dataclass(ann):
        if ann not in acc:
            acc.append(ann)
        return
    for a in typing.get_args(ann):
        _nested_dataclasses(a, acc)


def _default_str(f):
    if f.default is not dataclasses.MISSING:
        val = f.default
        if isinstance(val, enum.Enum):
            return f"{type(val).__name__}.{val.name}"
        return repr(val)
    if f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
        try:
            sample = f.default_factory()
        except Exception:
            return "(factory)"
        if dataclasses.is_dataclass(sample):
            return f"{type(sample).__name__}() (factory)"
        return f"{sample!r} (factory)"
    return "**required**"


def _md_escape(text):
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- #
# Slice -> owning page & consuming modules, from workflow.py + module sources.
# --------------------------------------------------------------------------- #
def _owning_page(slice_attr):
    """The page(s) that edit this slice, from the field registry (OG-14).

    A slice whose fields are edited on more than one page says so rather than
    picking one -- ``geometry`` is the case that used to be flattened, and
    hiding it is precisely the ownership question the registry exists to answer.
    """
    pages = {fr.BY_PATH[p].page for p in fr.paths_under(slice_attr)}
    if not pages:
        for step in w.STEPS:
            if step.produces == slice_attr:
                return step.title
        return "(unattributed)"
    return " / ".join(sorted(w.BY_KEY[k].title for k in pages))


def _consuming_modules(slice_attr):
    """Module files whose source reads ``.<slice_attr>`` (word-bounded)."""
    pat = re.compile(r"\.%s\b" % re.escape(slice_attr))
    hits = []
    for path in sorted(MODULES_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        if pat.search(text):
            hits.append(path.stem)
    return hits


def _slice_type(slice_attr):
    """Resolve the dataclass type behind a Project slice (incl. the two proxies)."""
    proxy = {"tail_loads": m.TailLoadsInput, "vtail_loads": m.VTailLoadsInput}
    if slice_attr in proxy:
        return proxy[slice_attr]
    hints = _resolve_hints(m.Project)
    ann = hints.get(slice_attr)
    acc = []
    _nested_dataclasses(ann, acc)
    return acc[0] if acc else None


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_dataclass_table(cls, lines, seen):
    """Emit a field table for ``cls`` and queue any nested dataclasses."""
    hints = _resolve_hints(cls)
    comments = _inline_comments(cls)
    doc = inspect.getdoc(cls) or ""
    summary = doc.split("\n\n")[0].replace("\n", " ").strip() if doc else ""

    lines.append(f"### `{cls.__name__}`")
    lines.append("")
    if summary:
        lines.append(f"{_md_escape(summary)}")
        lines.append("")
    lines.append("| Field | Type | Units / notes | Default |")
    lines.append("| --- | --- | --- | --- |")

    queue = []
    for f in dataclasses.fields(cls):
        ann = hints.get(f.name, f.type)
        type_s = _render_type(ann) if not isinstance(ann, str) else _type_str(ann)
        comment = comments.get(f.name, "")
        units = _units_hint(f.name, comment)
        lines.append(
            f"| `{f.name}` | `{_md_escape(type_s)}` | "
            f"{_md_escape(units)} | `{_md_escape(_default_str(f))}` |"
        )
        _nested_dataclasses(ann, queue)
    lines.append("")

    for nested in queue:
        if nested not in seen:
            seen.append(nested)


def build():
    lines = []
    lines.append("# `project.json` Input Data Dictionary")
    lines.append("")
    lines.append(
        "> **Generated file — do not edit by hand.** Produced by "
        "[`docs/generate_data_dict.py`](../generate_data_dict.py) from "
        "`sloads/models.py`. Regenerate after any schema change: "
        "`.venv/bin/python docs/generate_data_dict.py`."
    )
    lines.append("")
    lines.append(f"Schema version: **{m.SCHEMA_VERSION}**.")
    lines.append("")
    lines.append(
        "This dictionary covers the **input** slices of `Project` "
        "(`sloads/models.py`) — the fields that make up a `project.json`. The "
        "result slices (`envelope`, `mass`, `loads`) are computed outputs and are "
        "out of scope."
    )
    lines.append("")
    lines.append("**Column meaning & caveats:**")
    lines.append("")
    lines.append(
        "- *Type* / *Default* are introspected from the dataclass "
        "(`typing.get_type_hints` / `dataclasses.fields`) — authoritative."
    )
    lines.append(
        "- *Units / notes* reproduces the field's inline `# comment` verbatim "
        "(falling back to a guess from the name suffix, e.g. `_lb`→lb). Comments "
        "are prose, not a structured units field — treat it as a hint."
    )
    lines.append(
        "- *Owning page* and *Consumed by* are **slice-level**, not per-field: "
        "`workflow.py` tracks data flow per slice, so every field inherits its "
        "root slice's page and consumer list. Owning page is the workflow step "
        "that `produces` the slice (with a small override table in the generator "
        "for slices workflow doesn't attribute); *Consumed by* lists the calc "
        "modules whose source reads `.<slice>`."
    )
    lines.append("")

    # ---- Top-level slice map ------------------------------------------------ #
    lines.append("## Project slice map")
    lines.append("")
    lines.append(
        "The top-level `Project` fields. `name`/`engineer`/`date` are free-text "
        "metadata; `schema_version` is set by `io.py`. The rest are the input "
        "slices detailed below."
    )
    lines.append("")
    lines.append("| Slice | Type | Owning page | Consumed by | Role |")
    lines.append("| --- | --- | --- | --- | --- |")
    for attr, role in INPUT_SLICES:
        cls = _slice_type(attr)
        if attr == "engine_layout":
            type_s = "EngineLayout (enum)"
        elif attr == "include_far25":
            type_s = "bool"
        elif attr == "engines":
            type_s = "List[EngineInput]"
        elif attr == "tail_mass":
            type_s = "List[TailMassInput]"
        else:
            type_s = cls.__name__ if cls else "?"
        consumers = _consuming_modules(attr)
        consumers_s = ", ".join(f"`{c}`" for c in consumers) if consumers else "—"
        lines.append(
            f"| `{attr}` | `{type_s}` | {_owning_page(attr)} | "
            f"{consumers_s} | {_md_escape(role)} |"
        )
    lines.append("")

    # ---- Per-dataclass field tables ---------------------------------------- #
    lines.append("## Field tables")
    lines.append("")
    lines.append(
        "One table per input dataclass, in slice order (nested types follow the "
        "slice that first references them). A field typed as another dataclass is "
        "detailed in that dataclass's own table."
    )
    lines.append("")

    rendered = []          # dataclasses already emitted
    seen = []              # discovery queue (nested types to emit)
    for attr, _role in INPUT_SLICES:
        cls = _slice_type(attr)
        if cls is None or cls in rendered:
            continue
        rendered.append(cls)
        render_dataclass_table(cls, lines, seen)
        # Emit newly-discovered nested dataclasses right after their referrer.
        i = 0
        while i < len(seen):
            nested = seen[i]
            i += 1
            if nested not in rendered:
                rendered.append(nested)
                render_dataclass_table(nested, lines, seen)

    # ---- Enums appendix ----------------------------------------------------- #
    lines.append("## Enumerations")
    lines.append("")
    enum_types = [
        obj
        for _name, obj in sorted(vars(m).items())
        if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj is not enum.Enum
    ]
    for et in enum_types:
        # Only the enum's *own* docstring -- getdoc() would inherit str/Enum's.
        # Python <= 3.10's EnumMeta also stamps the placeholder "An enumeration."
        # into a docstring-less enum's own __dict__; drop it so the output is
        # identical on every interpreter in the CI matrix.
        doc = et.__dict__.get("__doc__") or ""
        if doc.strip() == "An enumeration.":
            doc = ""
        summary = doc.split("\n\n")[0].replace("\n", " ").strip()
        members = ", ".join(f"`{e.name}` = `{e.value!r}`" for e in et)
        lines.append(f"- **`{et.__name__}`** — {members}."
                     + (f" {_md_escape(summary)}" if summary else ""))
    lines.append("")

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# The oracle GUI user guide (docs/60_guide/) — design note 34, issue #96.
#
# UG-3: every chapter's field table is *generated* from `sloads.field_registry`
# (path, quantity, units, type, origin), written to `_generated/<step_key>.md`
# and linked from the chapter — prose never restates a units string, a default,
# or a field count. UG-7: the chapter set and its order are
# `sloads.workflow.oracle_steps()`, so adding a `.BAS`-backed step scaffolds a
# chapter here with no hand edit (note 32's G2 property, inherited).
# Gates G-UG-1…G-UG-6: `tests/test_guide.py`.
# --------------------------------------------------------------------------- #
GUIDE_DIR = REPO_ROOT / "docs" / "60_guide"
GEN_DIR = GUIDE_DIR / "_generated"

GENERATED_BANNER = (
    "<!-- Generated by docs/generate_data_dict.py — DO NOT EDIT.\n"
    "     Regenerate: .venv/bin/python docs/generate_data_dict.py -->"
)

#: The eight chapter section headings, in order (note 34 §3). Guard G-UG-6
#: asserts every chapter carries exactly these as its `##` sequence, so chapter
#: fourteen stays as complete as chapter one.
CHAPTER_HEADINGS = (
    "What this page is for",
    "Before this page",
    "The inputs",
    "Screenshots",
    "Worked example — single (`ga6_normal`)",
    "Worked example — twin (`baron_58`)",
    "Results on this page",
    "Common mistakes",
)


def guide_chapters():
    """``[("01", step), …]`` — chapter number and workflow step, UG-7 order."""
    return [(f"{i:02d}", step) for i, step in enumerate(w.oracle_steps(), start=1)]


def _page_entries(step_key):
    """This page's registry rows, in registry declaration order."""
    return [e for e in fr.REGISTRY if e.page == step_key]


def _entry_units(path):
    """The units hint for a registry path, from the owning dataclass source."""
    located = fr._locate(path)
    if located is None:
        return ""
    cls, field = located
    comment = _inline_comments(cls).get(field.name, "")
    return _units_hint(field.name, comment)


def _entry_type(path):
    ann = fr.field_type(path)
    if ann is None:
        return "?"
    return _render_type(ann) if not isinstance(ann, str) else _type_str(ann)


def _entry_default(path):
    located = fr._locate(path)
    if located is None:
        return ""
    _cls, field = located
    return _default_str(field)


def _origin_cell(e):
    label = e.origin.value
    if e.supplied:
        label += " (supplied)"
    return label


def _provenance_cell(e):
    parts = [e.basis]
    if e.quantity:
        parts.append(f"quantity: *{e.quantity}*")
    if e.derived_from:
        kind = "override" if e.governs else "display-only copy"
        parts.append(f"{kind} of `{e.derived_from}`")
    return _md_escape("; ".join(p for p in parts if p))


def _guide_field_table(step):
    """The generated field-table file for one oracle page."""
    lines = [GENERATED_BANNER, ""]
    lines.append(f"### Input fields — {step.title} (`{step.key}`)")
    lines.append("")
    entries = _page_entries(step.key)
    if not entries:
        lines.append(
            "This page enters no input fields of its own — every quantity it "
            "uses is entered on an earlier page (see the chapter's *Before "
            "this page* section)."
        )
        lines.append("")
        return "\n".join(lines) + "\n"
    lines.append(
        "Generated from `sloads/field_registry.py` — the registry of record "
        "for where each input field is edited and where it came from. "
        "*Origin* `original` means a named `.BAS` program asked for the field; "
        "`sloads` marks capability this replication added (`supplied` = the "
        "oracle input set needs it anyway). Types, units and defaults are "
        "introspected from `sloads/models.py`."
    )
    lines.append("")
    lines.append("| Field | Type | Units / notes | Default | Origin | Provenance |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for e in entries:
        lines.append(
            f"| `{e.path}` | `{_md_escape(_entry_type(e.path))}` | "
            f"{_md_escape(_entry_units(e.path))} | "
            f"`{_md_escape(_entry_default(e.path))}` | {_origin_cell(e)} | "
            f"{_provenance_cell(e)} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _guide_chapter_list():
    """The generated chapter index (UG-7 — no hand-maintained chapter list)."""
    lines = [GENERATED_BANNER, ""]
    lines.append("### The chapters, in workflow order")
    lines.append("")
    lines.append("| # | Chapter | Page key | Original program(s) |")
    lines.append("| --- | --- | --- | --- |")
    for nn, step in guide_chapters():
        bas = f"`{step.bas}`" if step.bas else "— (modern page)"
        lines.append(
            f"| {int(nn)} | [{step.title}](../{nn}_{step.key}.md) | "
            f"`{step.key}` | {bas} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def build_guide_tables():
    """Every file under ``_generated/``: ``{filename: content}``."""
    out = {"chapters.md": _guide_chapter_list()}
    for _nn, step in guide_chapters():
        out[f"{step.key}.md"] = _guide_field_table(step)
    return out


def _chapter_stub(nn, step):
    """A template-conformant placeholder chapter (filled by #96's later stages)."""
    bas = f"`{step.bas}`" if step.bas else "none — a modern page the workflow needs"
    body = [
        f"# {int(nn)}. {step.title}",
        "",
        "> **Placeholder chapter** — scaffolded by `docs/generate_data_dict.py`; "
        "the prose lands with the chapter stages of issue #96 (design note 34).",
        "",
        f"*Original program(s):* {bas}.",
        "",
    ]
    for heading in CHAPTER_HEADINGS:
        body.append(f"## {heading}")
        body.append("")
        if heading == "The inputs":
            body.append(
                "The field table for this page is generated from "
                f"`sloads/field_registry.py`: [`_generated/{step.key}.md`]"
                f"(_generated/{step.key}.md)."
            )
            body.append("")
        body.append("*Not yet written.*")
        body.append("")
    return "\n".join(body)


def scaffold_chapters():
    """Create any missing chapter file as a stub; never touch an existing one."""
    created = []
    for nn, step in guide_chapters():
        path = GUIDE_DIR / f"{nn}_{step.key}.md"
        if not path.exists():
            path.write_text(_chapter_stub(nn, step), encoding="utf-8")
            created.append(path)
    return created


def write_guide():
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    tables = build_guide_tables()
    for name, content in tables.items():
        (GEN_DIR / name).write_text(content, encoding="utf-8")
    for stale in GEN_DIR.glob("*.md"):
        if stale.name not in tables:
            stale.unlink()
            print(f"Removed stale {stale.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(tables)} files under {GEN_DIR.relative_to(REPO_ROOT)}/")
    for path in scaffold_chapters():
        print(f"Scaffolded {path.relative_to(REPO_ROOT)}")


def main():
    OUT_PATH.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    write_guide()


if __name__ == "__main__":
    main()
