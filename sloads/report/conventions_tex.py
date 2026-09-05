"""The report's "Axes and sign conventions" section: prose, table rows and the
three static TikZ figures (design note 15, decisions SC-1..SC-6).

This module is the **single source** for every sign-convention statement the
report makes (CLAUDE.md rule 3): the section in ``content.py`` and the figure
emitters in ``plots_tex.py`` both read from here, and
``tests/test_report_conventions.py`` guards the statements against
``export/coordinates.py`` and ``CONVENTIONS.md`` §1.1 drifting away from them.

Unlike the envelope figures, these carry **no project data** — they are the
conventions themselves, identical in every report — so the emitters take no
arguments and ``plots_tex.figure_body_tex`` dispatches them *before* its
``data is None`` absence test (a convention figure can never be "not analysed").
The TikZ below is authored source, not user input, so it is raw LaTeX; the
prose and table rows are plain text (with the Unicode ``plots_tex.escape``
maps) and go through the normal escaping path.

Greyscale, deterministic, pure: strings out, nothing in (SUMMARY_REPORT.md §2,
§4.3; decision G8-2 — source, not images).
"""

from __future__ import annotations

from typing import List

#: SUMMARY_REPORT.md §3.3 requires these two preserved ENGLOADS sentences
#: verbatim wherever they apply; the section states them once, globally.
ENGINE_TORQUE_SENTENCE = "engine-mount reaction torque is reported negative"
ROTATION_SENTENCE = "clockwise from the pilot's view is positive"

#: The frame statement. The drift guard asserts these fragments against the
#: ``export/coordinates.py`` module docstring, the frame's single owner.
FRAME_FRAGMENTS = ("positive aft", "positive right", "positive up")

CONVENTIONS_PROSE: List[str] = [
    "All loads and geometry are stated in the airplane reference frame: "
    "x = fuselage station, positive aft; y = butt line, positive right "
    "(starboard); z = waterline, positive up. The frame is right-handed and "
    "maps to the solver deck frame (NASTRAN basic CID 0) as the identity. "
    "Forces follow the axes (fz = lift, up; fx = drag, aft; fy = side force, "
    "starboard); moments are right-handed about the same axes, so +Mx rolls "
    "the starboard wing up (roll to port), +My pitches the nose up, and +Mz "
    "yaws the nose to port.",

    "Handed (left/right) case twins are mirror images through the centreline "
    "plane: a force flips only its fy component; a moment flips Mx and Mz, "
    "never My. Roll, pitch and yaw attitude angles are not state variables of "
    "this analysis — only accelerations are carried — so no attitude sign is "
    "stated or implied.",

    "Preserved suite conventions (FAR 23 LOADS): "
    + ENGINE_TORQUE_SENTENCE + "; " + ROTATION_SENTENCE
    + " for rotor RPM and stoppage torque.",
]

#: The conventions table: (quantity, positive sense, charter reference).
#: Each row restates — never redefines — a CONVENTIONS.md entry; the charter
#: section cited is the authority (decisions SC-1..SC-6 for the 2026-08-10
#: additions).
CONVENTION_ROWS: List[List[str]] = [
    ["Angle of attack α", "Nose-up, waterline to relative wind; +α gives +lift",
     "§1.1"],
    ["Sideslip β", "Relative wind from starboard (nose left of the flight "
     "path); the fin's restoring load is then -fy", "§1.1 SC-1"],
    ["Elevator δe", "Trailing edge down; TE-down gives an up (+fz) tail load",
     "§1.1"],
    ["Rudder δr", "Trailing edge toward port (left pedal); gives +fy and +Mz "
     "(nose-left)", "§1.1 SC-2"],
    ["Aileron", "Throws are magnitudes per direction (down = TE-down); the "
     "hand is the case suffix (R/L), stated per case, never a global sign",
     "§1.1 SC-6"],
    ["Load factors n", "nz up; nx = -DX/W (deceleration, negative under "
     "drag); ny starboard", "§1.1"],
    ["Angular accelerations", "Right-handed about (x, y, z): +roll = "
     "starboard wing up, +pitch = nose-up, +yaw = nose-port; attitudes are "
     "not modelled", "§1.1 SC-3"],
    ["Gusts", "Ude is a magnitude; the up/down (±) hand is stated per case; "
     "the lateral gust's opposite hand is the reflected twin", "§1.1"],
    ["Wing twist table", "Section zero-lift angle, nose-up-positive in the "
     "same sense as α; washout enters negative at the tip", "§1.1 SC-4"],
    ["Wing diagrams", "Sz up, integrated tip to root; Mxx and Mzz "
     "positive-magnitude integrals (up-lift bends +Mxx); +Myy = leading-edge-"
     "up torsion about the LRA (named per figure)", "§1, §1.1"],
    ["Body diagrams", "Sz up, integrated nose to tail; Myy stated about the "
     "aft-most station; station inertia is -NZ·w", "§1"],
    ["Horizontal tail", "Maps like the wing (span y, load fz, torsion Myy); "
     "a down-load is negative", "§7.2"],
    ["Vertical tail", "Spans z; its load is the side force fy; its torsion "
     "is Mzz about its own span axis", "§7.2"],
    ["Tail inertia", "d'Alembert, signed by the case's load factor alone, "
     "on the surface's own normal axis", "§1"],
    ["Landing gear V/D/S", "Per wheel, in airplane axes: V up, D aft, S "
     "starboard; the FAR 23.485 inboard/outboard literals keep their printed "
     "signs", "§1.1 SC-5"],
    ["Engine / rotation", ROTATION_SENTENCE + " (signed RPM); the mount "
     "reaction torque is reported negative; gyroscopic moments carry no sign "
     "— all four ± permutations are cases", "§5"],
]

#: The note under the table.
CONVENTION_TABLE_NOTE = (
    "Authority: docs/10_standard/CONVENTIONS.md (the conventions charter), "
    "cited per row. Deliverable loads are LIMIT with the safety factor stated "
    "per case and applied nowhere; per-figure torsion axes and per-moment signs "
    "are also repeated at point of use."
)


# --------------------------------------------------------------------------- #
# The three static figures. Raw TikZ, core features only (no \usetikzlibrary):
# straight/curved -stealth arrows, ellipses, scopes. Black and gray only.
# --------------------------------------------------------------------------- #

#: Plan view is drawn looking down with the nose to the left: +x (aft) runs
#: right and +y (starboard) runs *down* the page, keeping the drawn frame
#: right-handed with +z out of the page toward the viewer... which it is not —
#: looking down, +z points *at* the viewer's feet. The moment arrows below are
#: therefore drawn from the derived physical senses (+Mz = nose to port), not
#: from a screen-handedness rule, so the picture cannot be silently wrong-handed.
_SIGN_AXES = r"""\begin{tikzpicture}[font=\footnotesize, >=stealth]
% --- Side view: alpha and +My ------------------------------------------------
\begin{scope}
  \draw[gray, thick] (0.0,0.0) ellipse [x radius=1.9, y radius=0.30];
  \draw[gray, thick] (1.35,0.12) -- (1.75,0.95) -- (2.05,0.95) -- (1.85,0.10);
  \draw[gray] (-0.55,-0.02) -- (0.55,-0.10);
  \draw[->, thick] (0,0) -- (2.7,0) node[right] {$+x$ aft};
  \draw[->, thick] (0,0) -- (0,1.5) node[above left] {$+z$ up};
  \draw[->, dashed] (-3.3,-0.8) -- (-2.05,-0.4);
  \node[below] at (-2.9,-0.85) {relative wind};
  \node[left] at (-2.15,0.05) {$+\alpha$ nose-up};
  \draw[->, thick] (0.35,1.05) arc[start angle=140, end angle=40, radius=0.85];
  \node[above] at (1.0,1.42) {$+M_y$ nose-up};
  \node[gray] at (0,-1.0) {side view};
\end{scope}
% --- Plan view: beta and +Mz -------------------------------------------------
\begin{scope}[shift={(8.6,0)}]
  \draw[gray, thick] (0.0,0.0) ellipse [x radius=1.9, y radius=0.24];
  \draw[gray, thick] (-0.5,0.05) -- (0.45,1.15) -- (0.85,1.15) -- (0.35,0.05);
  \draw[gray, thick] (-0.5,-0.05) -- (0.45,-1.15) -- (0.85,-1.15) -- (0.35,-0.05);
  \draw[gray, thick] (1.5,0.04) -- (1.85,0.55) -- (2.05,0.55) -- (1.85,0.04);
  \draw[gray, thick] (1.5,-0.04) -- (1.85,-0.55) -- (2.05,-0.55) -- (1.85,-0.04);
  \draw[->, thick] (0,0) -- (2.75,0) node[right] {$+x$ aft};
  \draw[->, thick] (0,0) -- (0,-1.8) node[below] {$+y$ starboard};
  \draw[->, dashed] (-3.4,-1.6) -- (-2.1,-0.55);
  \node[below] at (-3.3,-1.7) {wind from starboard};
  \node[below right] at (-2.1,-0.5) {$+\beta$};
  \draw[->, thick] (-2.9,-0.75) arc[start angle=-90, end angle=90, radius=0.75];
  \node[above] at (-2.9,0.95) {$+M_z$ nose to port};
  \node[gray] at (0,-2.45) {plan view (from above)};
\end{scope}
% --- Front view: +Mx ---------------------------------------------------------
\begin{scope}[shift={(4.2,-4.6)}]
  \draw[gray, thick] (0,0.05) circle [radius=0.32];
  \draw[gray, thick] (-2.1,-0.28) -- (-0.3,-0.06) (0.3,-0.06) -- (2.1,-0.28);
  \draw[gray, thick] (-0.09,0.35) -- (-0.05,1.0) -- (0.09,1.0) -- (0.09,0.35);
  \draw[->, thick] (0,0) -- (1.5,0) node[above right] {$+y$ starboard};
  \draw[->, thick] (0.45,0.05) -- (0.45,0.9) node[right] {$+z$ up};
  \draw[->, thick] (1.35,0.35) arc[start angle=20, end angle=160, radius=1.45];
  \node[above] at (0,1.55) {$+M_x$ starboard wing up (roll to port)};
  \node[gray] at (0,-0.85) {front view};
\end{scope}
\end{tikzpicture}"""

_SIGN_CONTROLS = r"""\begin{tikzpicture}[font=\footnotesize, >=stealth]
% --- Elevator, side view -----------------------------------------------------
\begin{scope}
  \draw[gray, thick] (-1.6,0) -- (0.35,0);
  \draw[thick] (0.35,0) -- (1.35,-0.28);
  \fill (0.35,0) circle [radius=0.045];
  \draw[->] (1.35,0.15) arc[start angle=25, end angle=-25, radius=1.0];
  \node[right] at (1.45,-0.05) {$+\delta_e$ TE down};
  \node[gray, align=center] at (0,-1.0) {elevator (side view)\\TE-down gives an up tail load};
\end{scope}
% --- Rudder, plan view (from above; +y starboard is down the page) -----------
\begin{scope}[shift={(6.4,0)}]
  \draw[gray, thick] (-1.6,0) -- (0.35,0);
  \draw[thick] (0.35,0) -- (1.35,0.28);
  \fill (0.35,0) circle [radius=0.045];
  \draw[->] (1.35,-0.15) arc[start angle=-25, end angle=25, radius=1.0];
  \node[right] at (1.45,0.05) {$+\delta_r$ TE to port (left pedal)};
  \draw[->, thick] (-0.6,-0.15) -- (-0.6,-0.75) node[below] {$+f_y$};
  \node[gray, align=center] at (0.4,-1.75) {rudder (plan view, from above)\\gives $+f_y$ and $+M_z$ (nose-left)};
\end{scope}
% --- Rotation, front view from the pilot's seat ------------------------------
\begin{scope}[shift={(3.2,-4.1)}]
  \draw[gray, thick] (0,0) circle [radius=0.85];
  \fill[gray] (0,0) circle [radius=0.08];
  \draw[->, thick] (0.72,0.55) arc[start angle=37, end angle=-53, radius=0.9];
  \node[right, align=left] at (1.15,0.15)
    {rotation: clockwise from the pilot's view is positive\\
     mount \emph{reaction} torque is reported negative};
  \node[gray, align=center] at (0,-1.35) {rotor / propeller disc\\(pilot's view)};
\end{scope}
% --- Ailerons ----------------------------------------------------------------
\node[align=center, gray] at (3.2,-6.6)
  {ailerons: throws are magnitudes per direction (down $=$ TE-down);\\
   the hand is the case suffix --- an R rolling case deflects right TE-down / left TE-up,\\
   its L twin the mirror};
\end{tikzpicture}"""

_SIGN_BEAMS = r"""\begin{tikzpicture}[font=\footnotesize, >=stealth]
% --- Wing semispan -----------------------------------------------------------
\begin{scope}
  \draw[thick] (0,0) -- (4.2,0);
  \draw[gray] (0,-0.3) -- (0,0.3) node[above] {root};
  \node[above] at (4.2,0.02) {tip};
  \foreach \x/\l in {0.8/0.55, 1.6/0.48, 2.4/0.40, 3.2/0.30, 4.0/0.18}
    \draw[->] (\x,0) -- (\x,\l);
  \node[right] at (4.35,0.35) {$+S_z$ up};
  \draw[->, thick] (2.0,0.85) arc[start angle=130, end angle=50, radius=1.1];
  \node[above] at (2.7,1.0) {$+M_{xx}$ tip-up};
  \node[gray, align=left] at (2.1,-0.85)
    {integrated tip $\to$ root;\\
     $+M_{yy}=$ LE-up torsion about the LRA (axis named per figure)};
\end{scope}
% --- Body beam ---------------------------------------------------------------
\begin{scope}[shift={(0,-3.4)}]
  \draw[thick] (0,0) -- (4.2,0);
  \node[above] at (0,0.02) {nose};
  \node[above] at (4.2,0.02) {tail};
  \foreach \x/\l in {0.7/-0.30, 1.5/-0.42, 2.3/-0.48, 3.1/-0.38, 3.9/0.45}
    \draw[->] (\x,0) -- (\x,\l);
  \node[right] at (4.35,0.3) {$+S_z$ up};
  \node[gray, align=left] at (2.1,-1.15)
    {integrated nose $\to$ tail; terminal $M_{yy}$ stated about the aft-most station;\\
     station inertia $-N_z w$ (down for positive $N_z$); tail load carries its own sign};
\end{scope}
% --- Fin ---------------------------------------------------------------------
\begin{scope}[shift={(9.2,-3.4)}]
  \draw[thick] (0,0) -- (0,2.3);
  \node[right] at (0.05,2.3) {tip};
  \node[right] at (0.05,0) {root};
  \foreach \z/\l in {0.5/0.5, 1.1/0.42, 1.7/0.32, 2.2/0.2}
    \draw[->] (0,\z) -- (-\l,\z);
  \node[left] at (-0.7,1.6) {$+f_y$};
  \node[gray, align=left] at (0.3,-0.55)
    {fin: spans $z$, loaded in $f_y$;\\torsion $M_{zz}$ about its span axis};
\end{scope}
\end{tikzpicture}"""


def sign_axes_tex() -> str:
    """The frame figure: three views, the axis triad, +α/+β, +Mx/+My/+Mz."""
    return _SIGN_AXES


def sign_controls_tex() -> str:
    """The control-surface and rotation senses (SC-2, SC-6, §5)."""
    return _SIGN_CONTROLS


def sign_beams_tex() -> str:
    """The shear/moment/torsion diagram conventions per component."""
    return _SIGN_BEAMS


#: Dispatched by ``plots_tex.figure_body_tex`` **before** its ``data is None``
#: absence test: a static figure carries no ``PlotData`` and is never absent.
STATIC_EMITTERS = {
    "sign_axes": sign_axes_tex,
    "sign_controls": sign_controls_tex,
    "sign_beams": sign_beams_tex,
}

__all__ = [
    "CONVENTIONS_PROSE",
    "CONVENTION_ROWS",
    "CONVENTION_TABLE_NOTE",
    "ENGINE_TORQUE_SENTENCE",
    "FRAME_FRAGMENTS",
    "ROTATION_SENTENCE",
    "STATIC_EMITTERS",
    "sign_axes_tex",
    "sign_beams_tex",
    "sign_controls_tex",
]
