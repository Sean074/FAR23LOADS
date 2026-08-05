"""The report actually compiles (Step G8.6) — opt-in, skipped without an engine.

Every other report test asserts the ``.tex`` *source*. This one asserts the thing
the source exists for: that a real TeX engine turns it into a PDF. It is skipped
when no engine is on ``PATH``, which is the case in CI by design — ``tectonic``
downloads a support bundle on first use, and a test suite that needs the network
is a test suite that fails for the wrong reasons.

Run it locally with any of ``tectonic`` / ``latexmk`` / ``pdflatex`` installed, or
point ``SLOADS_TEX_ENGINE`` at a specific one.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads import Project, io  # noqa: E402
from sloads.export.pdf import (  # noqa: E402
    ENGINE_ENV_VAR,
    CompileResult,
    compile_pdf,
    find_engine,
)
from sloads.report.latex import render_report  # noqa: E402
import sloads.modules  # noqa: E402,F401  (module registration)

_EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "examples")
_GA = os.path.join(_EXAMPLES, "ga6_normal.project.json")

needs_engine = pytest.mark.skipif(
    find_engine() is None,
    reason="no TeX engine on PATH (tectonic / latexmk / pdflatex)",
)


# --------------------------------------------------------------------------- #
# Engine discovery — runs everywhere, needs no engine
# --------------------------------------------------------------------------- #
def test_missing_engine_is_reported_not_raised():
    """Decision G8-1: the PDF is best-effort. A machine with no engine still
    gets a complete ``.tex``, and the caller gets a message, never a traceback."""
    result = compile_pdf("\\documentclass{article}\\begin{document}x\\end{document}",
                         engine="definitely-not-a-tex-engine")
    assert isinstance(result, CompileResult)
    assert not result.ok and result.pdf is None
    assert ENGINE_ENV_VAR in result.log


def test_an_explicit_engine_overrides_the_search_order(monkeypatch):
    monkeypatch.setenv(ENGINE_ENV_VAR, "definitely-not-a-tex-engine")
    assert find_engine() is None
    monkeypatch.setenv(ENGINE_ENV_VAR, "python3")
    assert (find_engine() or "").endswith("python3")


# --------------------------------------------------------------------------- #
# The real compile
# --------------------------------------------------------------------------- #
@needs_engine
def test_ga_report_compiles_to_a_pdf():
    tex = render_report(io.load_project(_GA), tool_version="test",
                        generated="2026-08-05 09:00")
    result = compile_pdf(tex)
    assert result.ok, result.log
    assert result.pdf.startswith(b"%PDF-")
    assert result.pdf.rstrip().endswith(b"%%EOF")
    # Page objects live in compressed object streams in a modern PDF, so they
    # cannot be counted by scanning the bytes. Size is the available proxy for
    # "this is the whole report, not a one-page stub": the GA example runs to
    # ~20 pages of tables and three vector figures.
    assert len(result.pdf) > 50_000, "the compiled report is implausibly small"


@needs_engine
def test_an_empty_project_compiles_too():
    """The degraded document must be valid LaTeX as well — it is the one an
    engineer sees first, before any inputs exist."""
    result = compile_pdf(render_report(Project(name="Bare & empty_100%")))
    assert result.ok, result.log
    assert result.pdf.startswith(b"%PDF-")


@needs_engine
def test_compile_leaves_no_auxiliary_files_behind(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = compile_pdf(render_report(io.load_project(_GA), tool_version="test"))
    assert result.ok, result.log
    assert list(tmp_path.iterdir()) == [], "compile must clean up its temp files"


if __name__ == "__main__":  # zero-dependency self-runner (see PROGRAM_SPEC)
    if find_engine() is None:
        print("skipped: no TeX engine on PATH")
        raise SystemExit(0)
    tex = render_report(io.load_project(_GA), tool_version="test")
    outcome = compile_pdf(tex)
    print("ok" if outcome.ok else f"FAIL\n{outcome.log}")
    raise SystemExit(0 if outcome.ok else 1)
