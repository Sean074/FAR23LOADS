"""The one place the sloads version is written.

Deliberately a module of its own, holding a single literal and importing
nothing. Two things read it and they must never disagree:

* the packaging metadata -- ``pyproject.toml`` declares ``dynamic = ["version"]``
  and points ``[tool.setuptools.dynamic]`` at this attribute;
* :func:`sloads.export.report_package.tool_version`, which stamps the version
  into a report's analysis basis and ``build.json``.

**Why not ``importlib.metadata``.** That reads ``PKG-INFO``, a snapshot written
when the package was *installed*. In an editable install it goes stale the
moment the version is bumped and stays stale until somebody reinstalls -- which
is exactly what happened: the 0.8.1 bump landed and reports kept stamping 0.8.0,
naming a build they did not come from. A provenance field that is wrong but
plausible is worse than one that is absent.

**Why not ``sloads/__init__.py``.** Setuptools reads this attribute statically,
but falls back to *importing* the module when it cannot; ``sloads/__init__.py``
pulls in the whole package, and the build environment has none of its
dependencies. A file with one literal in it cannot fail that way.
"""

__version__ = "0.8.1"

__all__ = ["__version__"]
