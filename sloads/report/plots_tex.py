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
from typing import Iterable, List, Optional, Sequence, Tuple

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


def _x_range(data: PlotData) -> Optional[tuple]:
    xs: List[float] = []
    for s in data.series:
        xs += [x for x, _y in _finite(s)]
    xs += [x for _label, x, _y in data.points]
    xs += [x for _label, x in data.vlines]
    if not xs:
        return None
    lo, hi = min(xs), max(xs)
    return (lo - 1.0, hi + 1.0) if lo == hi else (lo, hi)


#: Where a marker label may sit, best first.
#:
#: ``anchor`` names the node edge pinned to the point, so ``south`` puts the
#: label *above* it and ``east`` puts it to the *left*. ``(dx, dy)`` is the
#: direction the label body extends, in normalised axis units, and is what the
#: clearance is scored along. ``south`` leads so that a marker with nothing near
#: it is placed exactly where every marker was placed before 2026-09-01.
_LABEL_ANCHORS: Tuple[Tuple[str, float, float], ...] = (
    ("south", 0.0, 1.0),                # above
    ("west", 1.0, 0.0),                 # to the right
    ("east", -1.0, 0.0),                # to the left
    ("north", 0.0, -1.0),               # below
    # The diagonals earn their place on the GA6's weight/CG figure, where the
    # minimum-weight corner has three lines and a marker inside a few percent
    # of the axis and no cardinal direction is clear of all of them.
    ("south west", 0.7071, 0.7071),     # up and to the right
    ("south east", -0.7071, 0.7071),    # up and to the left
    ("north west", 0.7071, -0.7071),    # down and to the right
    ("north east", -0.7071, -0.7071),   # down and to the left
)

#: The footprint of a label, in fractions of the axis range: one ``\tiny``
#: character wide, one line high, and the gap it is held off its marker by.
#:
#: A label is scored as the **box it occupies**, not as a point beside the
#: marker. Scoring a point was the first attempt and it placed
#: "CG3 / fwd light" -- fifteen characters, an eighth of the axis wide -- so
#: that its first character cleared the loading edge and the rest of it did
#: not. The numbers are for ``\tiny`` (about 2.5 pt per character, 5 pt per
#: line) on the default 0.86\\textwidth by 7.2 cm axis; they are an estimate of
#: text this emitter never measures, so they are deliberately generous.
_LABEL_CHAR_WIDTH = 0.0085
_LABEL_HEIGHT = 0.030
_LABEL_GAP = 0.012

#: The clearance at which a position is "good enough" and the search stops.
#:
#: The rule is *first acceptable*, not *best available*. Maximising clearance was
#: the first attempt: it moved every label, including the ones that were never in
#: anything's way, because some direction is always marginally roomier than
#: another. A figure whose labels sit above their markers except where they
#: cannot reads as a convention; one whose labels each point a different way
#: reads as a fault. So a label stays where it has always been unless it is
#: genuinely obstructed, and only then goes looking.
_LABEL_MIN_CLEARANCE = 0.012


def _segment_distance(px: float, py: float,
                      ax: float, ay: float, bx: float, by: float) -> float:
    """Distance from ``(px, py)`` to segment ``a``--``b``, all normalised."""
    dx, dy = bx - ax, by - ay
    span = dx * dx + dy * dy
    t = (0.0 if span == 0.0
         else min(1.0, max(0.0, ((px - ax) * dx + (py - ay) * dy) / span)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _crosses_box(ax: float, ay: float, bx: float, by: float,
                 x0: float, y0: float, x1: float, y1: float) -> bool:
    """Does segment ``a``--``b`` meet the axis-aligned box? (Liang-Barsky.)"""
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0.0:
            if q < 0.0:
                return False            # parallel and outside this edge
            continue
        t = q / p
        if p < 0.0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _point_box_distance(px: float, py: float,
                        x0: float, y0: float, x1: float, y1: float) -> float:
    return math.hypot(max(x0 - px, 0.0, px - x1), max(y0 - py, 0.0, py - y1))


def _segment_box_distance(seg: Tuple[float, float, float, float],
                          box: Tuple[float, float, float, float]) -> float:
    """Distance from a segment to a box -- ``0`` when they meet.

    Sampling points around the box was the first attempt and it let a box
    *straddle* a line: with samples on both sides and none on it, the emitter
    scored a label as clear of the very line running through the middle of it.
    """
    ax, ay, bx, by = seg
    x0, y0, x1, y1 = box
    if _crosses_box(ax, ay, bx, by, x0, y0, x1, y1):
        return 0.0
    return min([_point_box_distance(ax, ay, x0, y0, x1, y1),
                _point_box_distance(bx, by, x0, y0, x1, y1)]
               + [_segment_distance(cx, cy, ax, ay, bx, by)
                  for cx, cy in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])


def _label_anchors(data: PlotData,
                   drawable: Sequence[tuple]) -> List[Tuple[str, str, float, float]]:
    """``(anchor, label, x, y)`` for every marker, placed clear of the ink.

    Every marker label used to be emitted ``anchor=south`` -- directly above its
    point -- so any marker sitting on or near a line had its label written
    through that line. On the GA6 that was ``Vh`` on the never-exceed boundary,
    two CG cases on the loading edges, and all four gust labels on the V-n
    boundary (owner's PDF review, 2026-09-01).

    The placement is a rule, not a table of hand-tuned offsets: each candidate
    position is scored by the clearance of the **box the text occupies** from
    every plotted segment, every reference line and every other marker, in
    normalised axis units so the two axes are comparable. The candidates are
    tried in :data:`_LABEL_ANCHORS` order and the **first one that clears**
    (:data:`_LABEL_MIN_CLEARANCE`) is taken; if none does, the roomiest is. A
    hand-tuned offset is right for the project it was tuned on and silently
    wrong for the next one -- and these figures are built for whatever project a
    reader loads.

    Deterministic by construction, and an uncrowded marker keeps the placement
    it has always had, because ``south`` is tried first and accepted whenever
    there is room for it.
    """
    x_range, y_range = _x_range(data), _y_range(data)
    if x_range is None or y_range is None:
        return [("south", label, x, y) for label, x, y in data.points]
    x0, x1 = x_range
    y0, y1 = y_range
    xs, ys = (x1 - x0) or 1.0, (y1 - y0) or 1.0

    def norm(x: float, y: float) -> Tuple[float, float]:
        return ((x - x0) / xs, (y - y0) / ys)

    segments: List[Tuple[float, float, float, float]] = []
    for _s, pts in drawable:
        normed = [norm(x, y) for x, y in pts]
        segments += [(a[0], a[1], b[0], b[1]) for a, b in zip(normed, normed[1:])]
        if len(normed) == 1:                      # a lone point is its own segment
            segments.append((normed[0][0], normed[0][1], normed[0][0], normed[0][1]))
    for _label, x in data.vlines:
        ax, _ = norm(x, y0)
        segments.append((ax, 0.0, ax, 1.0))
    markers = [norm(x, y) for _label, x, y in data.points]

    placed = []
    for index, (label, x, y) in enumerate(data.points):
        px, py = norm(x, y)
        others = [m for i, m in enumerate(markers) if i != index]
        half_w = 0.5 * max(len(label), 1) * _LABEL_CHAR_WIDTH
        half_h = 0.5 * _LABEL_HEIGHT
        best, best_score = _LABEL_ANCHORS[0][0], None
        for anchor, dx, dy in _LABEL_ANCHORS:
            cx = px + dx * (_LABEL_GAP + half_w)
            cy = py + dy * (_LABEL_GAP + half_h)
            # The clearance that matters is the whole word's, not the end of it
            # nearest the marker, so the label is scored as the box it occupies.
            box = (cx - half_w, cy - half_h, cx + half_w, cy + half_h)
            score = min([_segment_box_distance(seg, box) for seg in segments]
                        + [_point_box_distance(mx, my, *box)
                           for mx, my in others]
                        + [1.0])
            # Never place a label off the axis: a corner marker has no room on
            # two of its four sides, and half a word outside the frame is worse
            # than a word over a grid line.
            if not (box[0] >= 0.0 and box[1] >= 0.0
                    and box[2] <= 1.0 and box[3] <= 1.0):
                score -= 1.0
            if best_score is None or score > best_score:
                best, best_score = anchor, score
            if score >= _LABEL_MIN_CLEARANCE:
                best, best_score = anchor, score
                break
        placed.append((best, label, x, y))
    return placed


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
        # An altitude axis was printing "0.5 1 1.5" under a "*10^4" multiplier
        # (owner's PDF review, 2026-09-01). A reviewer signing a report should
        # read a tick, not decode one. Every other axis in both documents is
        # already in fixed notation -- pgfplots only reaches for the multiplier
        # past a certain exponent -- so this changes the tick text of a figure
        # with a large range and no other.
        (r"  scaled ticks=false, x tick label style={/pgf/number format/fixed, "
         r"/pgf/number format/1000 sep={,}}, y tick label style="
         r"{/pgf/number format/fixed, /pgf/number format/1000 sep={,}},"),
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
        for anchor, label, x, y in _label_anchors(data, drawable):
            lines.append(f"\\node[anchor={anchor}, font=\\tiny] at "
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

    The planform figures are dispatched by key rather than through
    :data:`_EMITTERS` because their emitter takes no ``height`` — ``axis equal
    image`` derives it — so it is not the ``PlotData -> str`` shape the table
    holds. Both imports are local for the same reason: those modules read
    ``escape`` and friends from here.
    """
    from .conventions_tex import STATIC_EMITTERS
    from .planform_tex import PLANFORM_KEYS, planform_tex

    static = STATIC_EMITTERS.get(figure.key)
    if static is not None:
        return static()
    if figure.data is None:
        return ""
    if figure.key in PLANFORM_KEYS:
        return planform_tex(figure.data, key=figure.key)
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
