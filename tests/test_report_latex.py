"""The ``.tex`` renderer and its pgfplots figures (Step G8.5).

The renderer's failure modes are cheap to pin and expensive to miss:

* **An unescaped special aborts the compile** (or, worse, typesets silently
  wrong) the first time a project is called "Model 100 & 100A" — and every
  project name, engineer, condition label and unit string is user-supplied.
* **A non-deterministic render** makes the diff between two revisions of one
  report unreadable, which is the whole point of a controlled document
  (``SUMMARY_REPORT.md`` §2).
* **A figure that quietly loses its data** leaves a blank axis where a boundary
  should be; §4.3 requires the corner points to be readable *and* plotted.

These run without a TeX engine — compiling is ``test_pdf_compile.py``'s job.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.modules  # noqa: F401  (module registration)
from sloads import Project, io
from sloads.modules.structural_speeds import design_speed_values
from sloads.report.content import PlotData, Series, build_report
from sloads.report.latex import NOT_ANALYSED_MARKER, render_document, render_report
from sloads.report.plots_tex import escape, plot_tex, vn_diagram_tex
from sloads.units import UnitSystem

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")
_CONCEPT = os.path.join(_EXAMPLES, "concept_regional_jet.project.json")
_CONCEPT_HEAVY = os.path.join(_EXAMPLES, "concept_heavy.project.json")
#: A second FAR 23 (non-concept) fixture, so the concept-caveat test proves the
#: caveat is conditional rather than merely present. Every twin in ``examples/``
#: is a concept-category airplane, which is why this one is another GA single.
_GA_2 = os.path.join(_EXAMPLES, "cessna_210.project.json")
_TWIN = os.path.join(_EXAMPLES, "dhc8_dash8.project.json")


def _tex(path=_GA, **kwargs) -> str:
    kwargs.setdefault("tool_version", "test")
    return render_report(io.load_project(path), **kwargs)


# --------------------------------------------------------------------------- #
# It renders at all, for every fixture family
# --------------------------------------------------------------------------- #
def test_renders_for_every_fixture_family():
    for path in (_GA, _TWIN, _CONCEPT, _CONCEPT_HEAVY):
        tex = _tex(path)
        assert tex.startswith("\\documentclass")
        assert tex.rstrip().endswith(r"\end{document}")
        assert r"\tableofcontents" in tex


def test_renders_for_an_empty_project():
    """A half-filled project still produces a document — the sections it cannot
    fill say so (§3.4)."""
    tex = render_report(Project(name="empty"))
    assert r"\end{document}" in tex
    assert r"\textbf{Not analysed.}" in tex


def test_two_renders_are_byte_identical():
    """§2: determinism. A timestamp is the caller's to supply, never the
    renderer's to read from the clock."""
    kwargs = dict(tool_version="test", generated="2026-08-05 09:00")
    assert _tex(**kwargs) == _tex(**kwargs)


# --------------------------------------------------------------------------- #
# Escaping
# --------------------------------------------------------------------------- #
def test_escapes_latex_specials_in_a_project_name():
    project = io.load_project(_GA)
    project.name = "Model 100 & 100A_50% #2 ~$x^2$"
    project.engineer = "A. Engineer {contract}"
    tex = render_report(project, tool_version="test")
    # The raw specials never reach the document...
    assert "100A_50" not in tex
    assert "& 100A" not in tex.replace(r"\& 100A", "")
    # ...and their escaped forms do.
    for escaped in (r"\&", r"\_", r"\%", r"\#", r"\textasciitilde{}",
                    r"\textasciicircum{}", r"\{", r"\}"):
        assert escaped in tex


def test_escape_maps_units_and_prose_glyphs_to_portable_latex():
    """The unit labels and prose carry glyphs pdflatex cannot typeset raw."""
    assert escape("N·m") == r"N$\cdot$m"
    assert escape("m²") == r"m\textsuperscript{2}"
    assert escape("lb/in^2-ULT") == r"lb/in\textasciicircum{}2-ULT"
    assert escape("a — b") == "a --- b"
    assert escape("α") == r"$\alpha$"
    # Anything left outside ASCII is dropped rather than risking the compile.
    assert escape("ok中") == "ok"


def test_si_render_carries_si_markers_only():
    tex = _tex(system=UnitSystem.SI)
    assert "N-ULT" in tex and "Nm-ULT" in tex
    assert "lbs-ULT" not in tex


# --------------------------------------------------------------------------- #
# The content that must reach the page (§3.1, §4.1, §4.4)
# --------------------------------------------------------------------------- #
def test_title_page_states_the_basis_the_units_and_the_signature_block():
    tex = _tex()
    assert "All loads are ULTIMATE" in tex
    assert "Airspeed is KEAS" in tex
    assert r"\hrulefill" in tex, "unsigned control rows must still leave a line"
    assert r"\pageref{LastPage}" in tex, "a controlled document numbers page n of m"


def test_ultimate_markers_and_sf_columns_are_present():
    tex = _tex()
    assert "lbs-ULT" in tex and "lb-in-ULT" in tex
    assert r"\textbf{SF}" in tex


def test_not_analysed_rows_are_visually_distinct_without_colour():
    """§4.4: the coverage matrix is how a reviewer finds gaps, so its gap rows
    are emphasised — in bold, because §4.3 requires greyscale legibility."""
    tex = _tex()
    assert r"\textbf{" + NOT_ANALYSED_MARKER + "}" in tex
    assert "color" not in tex.lower().replace("hidelinks", "")


def test_concept_caveat_appears_only_in_concept_fixtures():
    for path in (_CONCEPT, _CONCEPT_HEAVY):
        assert "UNVERIFIED EXTRAPOLATION" in _tex(path)
    for path in (_GA, _GA_2):
        assert "UNVERIFIED EXTRAPOLATION" not in _tex(path)


def test_wide_tables_drop_to_a_smaller_font_rather_than_overflowing():
    tex = _tex()
    assert r"\footnotesize" in tex
    assert r"\begin{longtable}" in tex


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def test_vn_figure_plots_the_corner_speeds_it_tabulates():
    """§4.3: the plotted boundary and the corner table are the same numbers."""
    project = io.load_project(_GA)
    speeds = design_speed_values(project, project.speeds)
    doc = build_report(project, tool_version="test")
    figure = doc.section("V-n diagram").figures[0]
    tex = vn_diagram_tex(figure.data)
    coordinates = [float(m) for m in re.findall(r"\(([-0-9.e+]+),", tex)]
    assert any(abs(v - speeds.va) < 0.5 for v in coordinates), "VA is not plotted"
    assert any(abs(v - speeds.vd) < 0.5 for v in coordinates), "VD is not plotted"
    corner = doc.section("V-n diagram").tables[0]
    assert [row[0] for row in corner.rows] == ["VS", "VSF", "VA", "VC", "VD", "VF"]


def test_figures_are_greyscale_line_styles_not_colours():
    """§4.3: traces are distinguished by line style, never by colour — a report
    is read in greyscale print as often as on screen."""
    tex = _tex()
    for style in ("solid", "dashed", "dotted"):
        assert style in tex
    assert "[black," in tex
    assert r"\definecolor" not in tex and "color=" not in tex


def test_plot_tex_is_empty_when_there_is_nothing_to_draw():
    """An empty axis is worse than a stated absence, so the emitter refuses."""
    assert plot_tex(PlotData("x", "y", [])) == ""
    assert plot_tex(PlotData("x", "y", [Series("empty", [], [])])) == ""


def test_plot_tex_labels_are_escaped():
    tex = plot_tex(PlotData("V & n", "Weight (m²)", [Series("a_b", [0, 1], [0, 1])]))
    assert r"V \& n" in tex and r"m\textsuperscript{2}" in tex and r"a\_b" in tex


def test_figures_do_not_float_away_from_their_corner_table():
    tex = _tex()
    assert r"\begin{figure}[H]" in tex
    assert r"\begin{figure}[htbp]" not in tex


def test_render_document_and_render_report_agree():
    project = io.load_project(_GA)
    doc = build_report(project, tool_version="test")
    assert render_document(doc) == render_report(project, tool_version="test")


if __name__ == "__main__":  # zero-dependency self-runner (see PROGRAM_SPEC)
    import traceback

    failures = 0
    for name, fn in sorted(list(globals().items())):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"ok   {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    raise SystemExit(1 if failures else 0)
