"""The oracle GUI — the original FAR 23 LOADS suite's inputs, and nothing else.

Design note 32 (step OG-D). The entry point is ``oracle_app/Oracle.py``
(``streamlit run oracle_app/Oracle.py``, or the ``sloads-oracle`` console script,
OG-11); the whole front-end body is :mod:`oracle_app.form`, one renderer that
builds any of the fourteen oracle pages from :mod:`sloads.field_registry`.

Unlike ``app/``, this is an **installed package** rather than a bare script
directory, for the same reason :mod:`app_shell` is: its renderer is imported —
by its own entry point and by the gates in ``tests/test_oracle_gui.py`` — and a
module reachable only through Streamlit's implicit entry-point ``sys.path`` is
not importable by either. ``app/`` stays a script directory because nothing
imports it; the day something does, it takes the same route.

Nothing in here computes a load, converts a unit with a factor of its own, or
writes a deliverable: it reads :mod:`sloads` and :mod:`app_shell` and renders.
Gate G1 (``tests/test_oracle_gui.py``) is what keeps that true.
"""

from __future__ import annotations
