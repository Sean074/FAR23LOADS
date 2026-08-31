"""pgfplots/TikZ emitters for the summary report's three figures (Step G8.5).

Decision G8-2: the report's figures are **source, not images**. Each one is a
``tikzpicture`` written as text, so it is deterministic, unit-testable the same
way a BDF card is, vector in the final PDF, and set in the document's own fonts —
with no plotly, no ``kaleido``, and no image file for the ``.tex`` to depend on
(SUMMARY_REPORT.md §2 forbids external *image* files, which is what protects those
properties). §2's *Data reference* clause permits a **packaged** report to read
plain-text data from inside its own package; this report is also delivered as a
standalone ``.tex``, so its figures carry their coordinates inline.

The plot *data* arrives as a :class:`~sloads.report.content.PlotData` built from
the same pure functions the Streamlit pages plot (``build_vn_diagram``,
``loading_envelope_points``, ``mach_limit_lines``), so the report's figures cannot
drift from the GUI's.

**Greyscale, not colour.** Traces are distinguished by line *style*; §4.3 requires
a figure to stay legible in greyscale print, and a colour-only encoding fails
that. The LaTeX escaper lives here rather than in :mod:`sloads.report.latex`
because both modules need it and this is the lower-level one.

Pure: strings in, strings out.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Optional

from .content import Figure, PlotData, Series

#: Non-ASCII characters that reach the ``.tex`` (unit labels, condition titles,
#: em dashes in prose) mapped to portable LaTeX. Transliterating rather than
#: relying on the engine's Unicode support keeps one ``.tex`` compiling under
#: tectonic/XeTeX **and** pdflatex, which cannot typeset a bare Greek letter.
_UNICODE = {
    "·": r"$\cdot$", "×": r"$\times$", "±": r"$\pm$", "°": r"$^\circ$",
    "²": r"\textsuperscript{2}", "³": r"\textsuperscript{3}",
    "—": "---", "–": "--", "‑": "-", "‒": "--",
    "“": "``", "”": "''", "‘": "`", "’": "'", "…": r"\ldots{}",
    "α": r"$\alpha$", "β": r"$\beta$", "Δ": r"$\Delta$", "δ": r"$\delta$",
    "Σ": r"$\Sigma$", "σ": r"$\sigma$", "μ": r"$\mu$", "π": r"$\pi$",
    "≤": r"$\leq$", "≥": r"$\geq$", "→": r"$\rightarrow$", "≈": r"$\approx$",
    "⁺": r"$^{+}$", "⁻": r"$^{-}$", "§": r"\S{}", "✔": r"\checkmark{}",
    "⚠": "!", "•": r"$\bullet$", " ": "~",
}

#: The LaTeX specials, in an order that keeps the backslash rule first (it
#: introduces backslashes of its own, so it must not be re-escaped afterwards).
_SPECIALS = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
    ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
    ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
]


def escape(text: object) -> str:
    """Escape a user-supplied string for LaTeX text mode.

    Project names carry ``&``, ``_`` and ``%``; condition labels carry ``%``;
    unit strings carry ``^``. Every one of them is a LaTeX special that would
    otherwise be silently swallowed or abort the compile, so **all** text placed
    in the document goes through here. Characters outside Latin-1 that have no
    mapping in :data:`_UNICODE` are dropped rather than passed through: a
    stray glyph that breaks pdflatex is a worse failure than a missing one.
    """
    s = "" if text is None else str(text)
    for src, dst in _SPECIALS:
        s = s.replace(src, dst)
    for src, dst in _UNICODE.items():
        s = s.replace(src, dst)
    return "".join(ch for ch in s if ord(ch) < 128)


def _num(value: object) -> str:
    """A coordinate, formatted deterministically (and never in exponent form
    pgfplots misreads).

    Typed ``object`` on purpose: the callers hand it whatever a project's data
    produced, so ``None``, a bool or a non-finite float are real inputs here, not
    impossible ones. Each degrades to ``0`` rather than emitting a coordinate a
    TeX engine would choke on.
    """
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return "0"
    v = float(value)
    if not math.isfinite(v):
        return "0"
    return f"{v:.6g}"


def _finite(series: Series) -> List[tuple]:
    return [(x, y) for x, y in zip(series.x, series.y)
            if isinstance(x, (int, float)) and isinstance(y, (int, float))
            and math.isfinite(x) and math.isfinite(y)]


def _coordinates(points: Iterable[tuple]) -> str:
    return " ".join(f"({_num(x)},{_num(y)})" for x, y in points)


def _y_range(data: PlotData) -> Optional[tuple]:
    ys: List[float] = []
    for s in data.series:
        ys += [y for _x, y in _finite(s)]
    ys += [y for _label, _x, y in data.points]
    if not ys:
        return None
    lo, hi = min(ys), max(ys)
    if lo == hi:
        return lo - 1.0, hi + 1.0
    pad = 0.05 * (hi - lo)
    return lo - pad, hi + pad


def plot_tex(data: PlotData, *, width: str = "0.86\\textwidth",
             height: str = "7.2cm", legend_columns: int = 2) -> str:
    """One :class:`PlotData` as a standalone ``tikzpicture``.

    Returns ``""`` when there is nothing to draw, so a caller never emits an empty
    axis — §3.4 requires the section to say *why* instead.
    """
    drawable = [(s, _finite(s)) for s in data.series]
    drawable = [(s, pts) for s, pts in drawable if len(pts) >= 1]
    if not drawable and not data.points:
        return ""

    lines = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        f"  width={width}, height={height},",
        f"  xlabel={{{escape(data.x_label)}}}, ylabel={{{escape(data.y_label)}}},",
        r"  grid=both, grid style={gray!25}, axis lines=box,",
        r"  tick label style={font=\footnotesize}, label style={font=\small},",
        (r"  legend style={font=\footnotesize, at={(0.5,-0.24)}, anchor=north, "
         f"legend columns={legend_columns}, draw=gray!50}},"),
        r"]",
    ]
    for s, pts in drawable:
        lines.append(f"\\addplot[black, {s.style}, thick, mark=none] coordinates "
                     f"{{{_coordinates(pts)}}};")
        lines.append(f"\\addlegendentry{{{escape(s.name)}}}")

    y_range = _y_range(data)
    for label, x in data.vlines:
        if y_range is None:
            continue
        lo, hi = y_range
        lines.append(f"\\addplot[gray, dashed, forget plot, mark=none] coordinates "
                     f"{{({_num(x)},{_num(lo)}) ({_num(x)},{_num(hi)})}};")
        lines.append(f"\\node[anchor=south, rotate=90, font=\\tiny, gray] at "
                     f"(axis cs:{_num(x)},{_num(lo)}) {{{escape(label)}}};")
    if data.points:
        lines.append("\\addplot[only marks, mark=diamond*, mark size=2pt, black] "
                     "coordinates {"
                     + _coordinates((x, y) for _l, x, y in data.points) + "};")
        lines.append("\\addlegendentry{" + escape(data.points_label) + "}")
        for label, x, y in data.points:
            lines.append(f"\\node[anchor=south, font=\\tiny] at "
                         f"(axis cs:{_num(x)},{_num(y)}) {{{escape(label)}}};")
    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The three named figures (SUMMARY_REPORT.md §4.3)
# --------------------------------------------------------------------------- #
def vn_diagram_tex(data: PlotData) -> str:
    """The V-n diagram: manoeuvre + stall boundaries, flap envelope, gust lines."""
    return plot_tex(data, height="7.6cm", legend_columns=2)


def weight_cg_tex(data: PlotData) -> str:
    """The weight/CG envelope: loading polygon, CG limits, design CG cases."""
    return plot_tex(data, height="7.2cm", legend_columns=2)


def speed_altitude_tex(data: PlotData) -> str:
    """The speed/altitude envelope: the Mach-limited EAS lines above the shoulder."""
    return plot_tex(data, height="7.2cm", legend_columns=2)


_EMITTERS = {
    "vn": vn_diagram_tex,
    "weight_cg": weight_cg_tex,
    "speed_altitude": speed_altitude_tex,
}


def figure_body_tex(figure: Figure) -> str:
    """The ``tikzpicture`` for ``figure``, or ``""`` when it has no data.

    Static figures (the sign-convention diagrams) are dispatched **before** the
    ``data is None`` absence test: they carry no ``PlotData`` because they
    depend on no project data, and a convention can never be "not analysed".
    """
    from .conventions_tex import STATIC_EMITTERS

    static = STATIC_EMITTERS.get(figure.key)
    if static is not None:
        return static()
    if figure.data is None:
        return ""
    emit = _EMITTERS.get(figure.key, plot_tex)
    return emit(figure.data)


__all__ = [
    "escape",
    "figure_body_tex",
    "plot_tex",
    "speed_altitude_tex",
    "vn_diagram_tex",
    "weight_cg_tex",
]
