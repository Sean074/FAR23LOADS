"""The TikZ emitter for section 2.1's planform figures (design note 44, OR-45).

One figure per main surface — wing, horizontal tail, vertical tail — drawing the
surface's entered edge polylines as a closed outline with its control surfaces
filled on top. Source, not an image: ``SUMMARY_REPORT.md`` §2 *Self-containment*
forbids the report referencing an external image file, and the 2026-08-30
OR-23/OR-26 amendment reaffirms the prohibition verbatim while opening only the
plain-text *data* channel. A planform is a closed polygon, so the property costs
nothing here — the figure stays deterministic, diffable, unit-testable as text
and vector in the document's own fonts.

**Why a separate emitter rather than an option on** :func:`~sloads.report.plots_tex.plot_tex`.
A planform needs ``axis equal image``: drawn on independent axes, a swept tapered
surface reads as a different shape than the one the loads were computed for, which
is the one thing this figure exists to show. Nothing else the report plots wants
that, and a V-n diagram forced square would be unreadable.

**Greyscale, and fill *density* rather than colour** (``SUMMARY_REPORT.md`` §4.3):
the parent surface is an unfilled heavy outline, each control surface a distinct
grey. :attr:`~sloads.report.content.Series.style` carries the TikZ option string
that decides which — a plain option list, the same kind of token the existing
``"solid"``/``"dashed"`` styles already are, so a planform series that ever
reached the default emitter would still compile.

**Region names, and the areas beside them, are built by the content layer** and
arrive here already formatted and already converted, exactly as ``Table`` cells
do. This module decides nothing about what a number means.

A series with an empty :attr:`~sloads.report.content.Series.name` is drawn
``forget plot`` and gets no legend entry — that is how a symmetric surface's
mirrored half is drawn without claiming to be a second surface.

Pure: strings in, strings out.
"""

from __future__ import annotations

from typing import List

from .content import PlotData
from .plots_tex import _coordinates, _finite, _num, escape

#: The parent surface: a heavy unfilled outline. It is the boundary the areas
#: are quoted against, so it must stay readable under whatever fills it.
OUTLINE_STYLE = "very thick"

#: The control surfaces drawn on top of a parent, in the order the content layer
#: hands them over. Two greys, far enough apart to survive a greyscale print and
#: a photocopy of one; a third control surface on one parent would need a third
#: value here rather than wrapping onto the first, which would make two different
#: surfaces look like the same one.
#:
#: ``area legend`` is not decoration: without it pgfplots draws a filled plot's
#: legend entry as a bare line, so the two control surfaces of a wing get
#: identical black dashes in the key and the fill that distinguishes them on the
#: drawing is exactly what the reader cannot look up.
REGION_STYLES = ("fill=gray!20, area legend", "fill=gray!50, area legend")

#: The figure keys this emitter owns, dispatched by
#: :func:`sloads.report.plots_tex.figure_body_tex`.
#:
#: Exact keys, and that matters: the V-n figures key themselves ``vn_<index>``,
#: which never matches ``_EMITTERS["vn"]`` and silently falls through to the
#: default emitter. It happens to be harmless there. Here it would drop
#: ``axis equal image`` and print a planform to the wrong shape, so the keys the
#: content layer mints and the keys registered here are the same frozen set and
#: ``test_oracle_report.py`` holds them together.
PLANFORM_KEYS = frozenset({"planform_wing", "planform_htail", "planform_vtail"})

#: The figures drawn nose-up: fuselage station is the **vertical** axis and it
#: increases *downward*, so the surface sits the way a plan view is read.
#:
#: A wing spans 402 in against a 101 in root chord. Drawn with station across, on
#: the equal axes the figure exists to hold, it is four times taller than it is
#: wide and a page cannot carry it; drawn with station up, the nose points down
#: the page. Both are avoided by reversing the axis, and the tick labels stay the
#: airplane's own stations rather than something negated to make a picture work.
#:
#: The vertical tail is not in here: its second coordinate is a waterline, it is
#: naturally taller than it is long, and a fin is read nose-left with the
#: waterline running up -- which is the unreversed default.
NOSE_UP_KEYS = frozenset({"planform_wing", "planform_htail"})


def planform_tex(data: PlotData, *, key: str = "",
                 width: str = "0.72\\textwidth") -> str:
    r"""One :class:`~sloads.report.content.PlotData` as a to-scale planform.

    Returns ``""`` when there is nothing to draw, so a caller never emits an
    empty axis — §3.4 requires the section to say *why* instead.

    No ``height``: ``axis equal image`` derives it from the width and the data
    range, which is the whole point. Passing one would either be ignored or
    fight the equal-axis constraint.
    """
    drawable = [(s, _finite(s)) for s in data.series]
    drawable = [(s, pts) for s, pts in drawable if len(pts) >= 3]
    if not drawable:
        return ""

    lines: List[str] = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        f"  width={width}, axis equal image,",
        f"  xlabel={{{escape(data.x_label)}}}, ylabel={{{escape(data.y_label)}}},",
        r"  grid=both, grid style={gray!25}, axis lines=box,",
        r"  tick label style={font=\footnotesize}, label style={font=\small},",
        # Offset in *baselines* from the axis's bottom edge, not in axis-relative
        # units. Under ``axis equal image`` the axis height is whatever the
        # planform's own proportions make it -- a wing is a wide strip, a fin is
        # nearly square -- so a fraction-of-height offset that clears the x label
        # on one figure sits on top of it on the next, which is what it did.
        (r"  legend style={font=\footnotesize, at={(0.5,0)}, anchor=north, "
         r"yshift=-3\baselineskip, legend columns=1, draw=gray!50, "
         r"cells={anchor=west}},"),
    ]
    if key in NOSE_UP_KEYS:
        lines.append(r"  y dir=reverse,")
    lines.append(r"]")
    for series, points in drawable:
        # `--cycle` closes the path itself rather than trusting the caller to
        # repeat its first point: an unclosed path fills to a straight chord
        # between the ends, which on a swept surface is a visibly wrong outline
        # rather than an obviously broken one.
        forget = "" if series.name else ", forget plot"
        lines.append(f"\\addplot[black, {series.style}{forget}, mark=none] "
                     f"coordinates {{{_coordinates(points)}}} --cycle;")
        if series.name:
            lines.append(f"\\addlegendentry{{{escape(series.name)}}}")

    if data.points:
        # The entered polyline vertices. Marked, not annotated: the horizontal
        # tail is entered as fifteen points and fifteen coordinate labels is not
        # a drawing. A point carrying a label still gets one, so the mechanism is
        # there for a figure that has few enough to name.
        lines.append("\\addplot[only marks, mark=*, mark size=1pt, black, "
                     "forget plot] coordinates {"
                     + _coordinates((x, y) for _label, x, y in data.points) + "};")
        for label, x, y in data.points:
            if not label:
                continue
            lines.append(f"\\node[anchor=south, font=\\tiny] at "
                         f"(axis cs:{_num(x)},{_num(y)}) {{{escape(label)}}};")
    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    return "\n".join(lines)


__all__ = [
    "OUTLINE_STYLE",
    "PLANFORM_KEYS",
    "REGION_STYLES",
    "planform_tex",
]
