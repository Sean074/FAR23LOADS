"""The report's "Axes and sign conventions" section (design note 15, SC-1..SC-6).

What these tests pin is the section's **single-source and drift-guard
contract** (CLAUDE.md rule 3; CONVENTIONS.md §7 table):

* the section exists in every report — conventions have no absent state;
* its statements cannot drift from the frame's code owner
  (``export/coordinates.py``) or from the two preserved ENGLOADS sentences
  SUMMARY_REPORT.md §3.3 mandates verbatim;
* the three figures are static TikZ dispatched without ``PlotData``, greyscale,
  deterministic, and every one carries the labels a reader needs;
* the table rows survive the LaTeX escaping path (Greek letters, ``±``, ``·``).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sloads.export.coordinates as coordinates  # noqa: E402
from sloads import io  # noqa: E402
from sloads.report import conventions_tex  # noqa: E402
from sloads.report.content import Figure, build_report  # noqa: E402
from sloads.report.latex import render_document  # noqa: E402
from sloads.report.plots_tex import escape, figure_body_tex  # noqa: E402
import sloads.modules  # noqa: E402,F401  (module registration)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")


def _section(path=_GA):
    doc = build_report(io.load_project(path), tool_version="test")
    return doc, doc.section("Axes and sign conventions")


# --------------------------------------------------------------------------- #
# Presence and placement
# --------------------------------------------------------------------------- #
def test_the_section_exists_with_its_three_figures_and_table():
    _doc, section = _section()
    assert section is not None and not section.absent_reason
    assert [f.key for f in section.figures] == [
        "sign_axes", "sign_controls", "sign_beams"]
    assert section.table.columns == ["Quantity", "Positive sense", "Charter"]
    assert len(section.table.rows) == len(conventions_tex.CONVENTION_ROWS)


def test_the_section_sits_between_inputs_and_the_envelope_figures():
    doc, _ = _section()
    titles = [s.title for s in doc.sections]
    assert titles.index("2. Axes and sign conventions") == \
        titles.index("1. Input summary") + 1
    assert titles.index("3. Envelope figures") == \
        titles.index("2. Axes and sign conventions") + 1


# --------------------------------------------------------------------------- #
# Drift guards (single-source contract)
# --------------------------------------------------------------------------- #
def test_the_frame_statement_matches_the_coordinates_owner():
    """`export/coordinates.py` owns the frame; the prose restates it. If the
    owner's docstring stops saying +aft/+right/+up, this must fail before a
    report ships the stale claim."""
    doc_text = coordinates.__doc__ or ""
    for fragment in conventions_tex.FRAME_FRAGMENTS:
        assert fragment in doc_text
    prose = " ".join(conventions_tex.CONVENTIONS_PROSE)
    for fragment in conventions_tex.FRAME_FRAGMENTS:
        assert fragment in prose


def test_the_preserved_engloads_sentences_appear_verbatim():
    """SUMMARY_REPORT.md §3.3: the two suite conventions SHALL be repeated."""
    prose = " ".join(conventions_tex.CONVENTIONS_PROSE)
    assert conventions_tex.ENGINE_TORQUE_SENTENCE in prose
    assert conventions_tex.ROTATION_SENTENCE in prose
    # And they survive into the rendered document.
    doc, _ = _section()
    tex = render_document(doc)
    assert "reported negative" in tex
    assert "clockwise from the pilot's view is positive" in tex


def test_every_row_cites_the_charter():
    for quantity, _sense, charter in conventions_tex.CONVENTION_ROWS:
        assert "§" in charter, quantity


def test_the_approved_decisions_are_all_cited():
    """SC-1..SC-6 (design note 15) each own at least one row."""
    charters = " ".join(r[2] for r in conventions_tex.CONVENTION_ROWS)
    for n in range(1, 7):
        assert f"SC-{n}" in charters


# --------------------------------------------------------------------------- #
# The static figures
# --------------------------------------------------------------------------- #
def test_static_figures_render_without_plotdata():
    for key in ("sign_axes", "sign_controls", "sign_beams"):
        body = figure_body_tex(Figure(key=key, title="t", data=None))
        assert body.startswith(r"\begin{tikzpicture}")
        assert body.rstrip().endswith(r"\end{tikzpicture}")


def test_static_figures_are_deterministic():
    for emit in conventions_tex.STATIC_EMITTERS.values():
        assert emit() == emit()


def test_static_figures_are_greyscale():
    """§4.3: legible in greyscale print — nothing encoded by colour."""
    import re

    for emit in conventions_tex.STATIC_EMITTERS.values():
        body = emit()
        for colour in ("red", "blue", "green", "orange", "cyan", "magenta",
                       "yellow", "violet", "brown", "pink", "purple", "teal"):
            assert not re.search(rf"\b{colour}\b", body), colour


def test_the_figures_carry_their_required_labels():
    axes = conventions_tex.sign_axes_tex()
    for label in ("$+x$ aft", "$+y$ starboard", "$+z$ up", r"$+\alpha$",
                  r"$+\beta$", "$+M_x$", "$+M_y$ nose-up", "$+M_z$ nose to port",
                  "wind from starboard"):
        assert label in axes, label
    controls = conventions_tex.sign_controls_tex()
    for label in (r"$+\delta_e$ TE down", r"$+\delta_r$ TE to port",
                  "left pedal", "clockwise from the pilot's view is positive",
                  "reported negative", "case suffix"):
        assert label in controls, label
    beams = conventions_tex.sign_beams_tex()
    for label in ("$+S_z$ up", "$+M_{xx}$ tip-up", "$+M_{yy}=$ LE-up",
                  "LRA", "aft-most station", "$+f_y$", "$M_{zz}$"):
        assert label in beams, label


def test_static_tikz_is_ascii_clean():
    """The figures bypass ``escape``; a stray Unicode glyph (an em dash, a
    minus sign) would reach the TeX engine raw and abort under pdflatex."""
    for emit in conventions_tex.STATIC_EMITTERS.values():
        assert all(ord(ch) < 128 for ch in emit())


# --------------------------------------------------------------------------- #
# Escaping (prose and rows take the normal path)
# --------------------------------------------------------------------------- #
def test_rows_and_prose_survive_the_escaper_without_dropped_glyphs():
    """``escape`` silently drops unmapped non-Latin-1 characters — a Unicode
    minus sign (U+2212) in a row would vanish and flip a stated sign. Every
    non-ASCII character used here must have a mapping."""
    from sloads.report.plots_tex import _UNICODE

    texts = [c for row in conventions_tex.CONVENTION_ROWS for c in row]
    texts += list(conventions_tex.CONVENTIONS_PROSE)
    texts.append(conventions_tex.CONVENTION_TABLE_NOTE)
    for text in texts:
        for ch in text:
            assert ord(ch) < 128 or ch in _UNICODE, repr((ch, text[:40]))
        assert escape(text)  # and nothing aborts


if __name__ == "__main__":  # zero-dependency self-runner (see PROGRAM_SPEC)
    import traceback

    failures = 0
    for name, fn in sorted(list(globals().items())):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"ok   {name}")
        except Exception:  # noqa: BLE001 - a self-runner reports, it does not raise
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    raise SystemExit(1 if failures else 0)
