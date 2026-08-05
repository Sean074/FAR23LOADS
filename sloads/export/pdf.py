"""Compile the summary report's ``.tex`` to PDF — the one impure piece (Step G8.6).

**I/O exemption (documented, per the Step G8 plan §3).** Everything in
:mod:`sloads.report` is pure: no filesystem, no subprocess. Compiling LaTeX needs
both, so that one step lives here instead, on the same footing as :mod:`sloads.io`
— an *export-side* helper that contains no math, produces no engineering number,
and is imported by nothing in the calc or report packages. The pure renderer never
touches the filesystem; this module never touches an equation.

Decision G8-1 makes the PDF **best-effort**: the ``.tex`` is the primary artifact
and is always delivered, so a machine with no TeX engine still gets a complete
bundle. Consequently nothing here raises. A missing engine or a failed compile
comes back as a :class:`CompileResult` with ``pdf is None`` and a log the caller
can surface as a caption.

Engine order (resolved when G8.6 was built): ``tectonic`` first — it is
self-contained and needs no TeX Live — then ``latexmk``, then ``pdflatex``. Set
:data:`ENGINE_ENV_VAR` to a binary name or path to override the search entirely.
tectonic downloads its support bundle on first use (needs network once, then
caches), which is why it is never invoked from the test suite except by the
opt-in compile test.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import List, NamedTuple, Optional, Sequence

#: Environment variable naming an explicit engine (binary name or absolute path).
ENGINE_ENV_VAR = "SLOADS_TEX_ENGINE"

#: Search order when the environment names nothing.
ENGINE_PREFERENCE = ("tectonic", "latexmk", "pdflatex")

#: Default wall-clock ceiling for one compile. A LaTeX run that has stalled (a
#: missing package prompting on stdin, say) must not hang a Streamlit page.
DEFAULT_TIMEOUT_S = 240


class CompileResult(NamedTuple):
    """The outcome of one compile attempt.

    ``pdf`` is the PDF bytes on success and ``None`` on any failure; ``engine`` is
    the binary actually used (``""`` when none was found); ``log`` is the engine
    output (or the reason no engine ran), for the caller to show verbatim.
    """

    pdf: Optional[bytes]
    engine: str
    log: str

    @property
    def ok(self) -> bool:
        return self.pdf is not None


def find_engine(preferred: Optional[str] = None) -> Optional[str]:
    """The TeX engine this machine will use, or ``None`` if it has none.

    ``preferred`` (or :data:`ENGINE_ENV_VAR`) wins over the search order, and may
    be an absolute path so a caller can pin an engine that is not on ``PATH``.
    """
    explicit = preferred or os.environ.get(ENGINE_ENV_VAR, "")
    if explicit:
        if os.path.isabs(explicit) and os.access(explicit, os.X_OK):
            return explicit
        found = shutil.which(explicit)
        if found:
            return found
        return None
    for name in ENGINE_PREFERENCE:
        found = shutil.which(name)
        if found:
            return found
    return None


def _command(engine: str, tex_path: str, out_dir: str) -> List[List[str]]:
    """The command line(s) to run for ``engine``.

    ``pdflatex`` is run twice on purpose: the table of contents and the
    ``lastpage`` "page n of m" references are only correct on the second pass.
    ``latexmk`` and ``tectonic`` handle the reruns themselves.
    """
    name = os.path.basename(engine).lower()
    if name.startswith("tectonic"):
        return [[engine, "--outdir", out_dir, "--keep-logs", "--print", tex_path]]
    if name.startswith("latexmk"):
        return [[engine, "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                 f"-outdir={out_dir}", tex_path]]
    return [[engine, "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={out_dir}", tex_path]] * 2


def compile_pdf(tex: str, *, engine: Optional[str] = None,
                timeout: int = DEFAULT_TIMEOUT_S,
                job_name: str = "report") -> CompileResult:
    """Compile ``tex`` and return the PDF bytes, never raising.

    The compile runs in a temporary directory that is removed afterwards, so no
    auxiliary file (``.aux``, ``.log``, ``.toc``) is left beside the caller's
    output. Only the bytes come back.
    """
    binary = find_engine(engine)
    if not binary:
        return CompileResult(
            None, "",
            "No TeX engine found. Install one of "
            + ", ".join(ENGINE_PREFERENCE)
            + f", or set {ENGINE_ENV_VAR} to the engine to use. The .tex source is "
              "complete and can be compiled elsewhere.",
        )

    logs: List[str] = []
    with tempfile.TemporaryDirectory(prefix="sloads-report-") as work:
        tex_path = os.path.join(work, f"{job_name}.tex")
        out_dir = os.path.join(work, "out")
        os.makedirs(out_dir, exist_ok=True)
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(tex)

        for command in _command(binary, tex_path, out_dir):
            result = _run(command, work, timeout)
            logs.append(result[1])
            if result[0] is False:
                return CompileResult(None, binary, "\n".join(logs))

        pdf_path = os.path.join(out_dir, f"{job_name}.pdf")
        if not os.path.exists(pdf_path):
            logs.append(f"{binary} reported success but wrote no {job_name}.pdf")
            return CompileResult(None, binary, "\n".join(logs))
        with open(pdf_path, "rb") as fh:
            return CompileResult(fh.read(), binary, "\n".join(logs))


def _run(command: Sequence[str], cwd: str, timeout: int):
    """Run one command; ``(ok, log)``. Any failure mode becomes a log line."""
    try:
        proc = subprocess.run(
            list(command), cwd=cwd, timeout=timeout,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"{command[0]} timed out after {timeout}s"
    except OSError as exc:  # pragma: no cover - engine vanished between which() and run
        return False, f"{command[0]} could not be run: {exc}"
    output = proc.stdout.decode("utf-8", "replace") if proc.stdout else ""
    if proc.returncode != 0:
        return False, f"{command[0]} exited {proc.returncode}\n{_tail(output)}"
    return True, _tail(output)


def _tail(text: str, lines: int = 40) -> str:
    """The last ``lines`` of engine output — the part that names the error."""
    parts = text.rstrip().splitlines()
    return "\n".join(parts[-lines:])


__all__ = [
    "ENGINE_ENV_VAR",
    "ENGINE_PREFERENCE",
    "CompileResult",
    "find_engine",
    "compile_pdf",
]
