"""The sloads version has exactly one owner, and packaging reads it.

``sloads/_version.py`` holds the literal. ``pyproject.toml`` declares the version
dynamic and points at that attribute; the report generator reads the same
attribute. Before this, packaging held its own literal and the generator asked
``importlib.metadata`` -- which reads install-time ``PKG-INFO`` and had been
stamping 0.8.0 into reports since the 0.8.1 bump, because an editable install's
metadata is a snapshot and nobody had reinstalled.

CLAUDE.md rule 3: a cross-cutting value gets one owner plus a drift-guard test,
never a prose rule alone.
"""

from __future__ import annotations

import ast
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sloads._version import __version__  # noqa: E402
from sloads.export.report_package import tool_version  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PYPROJECT = os.path.join(_ROOT, "pyproject.toml")


def _pyproject() -> str:
    with open(_PYPROJECT, encoding="utf-8") as fh:
        return fh.read()


def test_pyproject_declares_the_version_dynamic_and_names_the_owner():
    """No second literal to fall out of step with the first."""
    text = _pyproject()
    assert 'dynamic = ["version"]' in text
    assert 'version = {attr = "sloads._version.__version__"}' in text


def test_pyproject_holds_no_version_literal_of_its_own():
    """The failure this guards is silent: two literals that agree today and
    disagree after the next bump, with the document quoting the stale one."""
    project_block = _pyproject().split("[project]", 1)[1].split("\n[", 1)[0]
    literal = re.search(r'^version\s*=\s*"', project_block, re.MULTILINE)
    assert literal is None, (
        "pyproject.toml carries its own version literal again; the owner is "
        "sloads/_version.py and packaging must read it via attr:")


def test_the_report_stamp_reads_the_owner_not_install_metadata():
    """``tool_version`` must track an edit immediately.

    Asserted against the attribute rather than against ``importlib.metadata``
    on purpose: the two are equal only just after an install, and it is exactly
    when they differ that the report must follow the source.
    """
    assert tool_version() == __version__
    # Scanned as an *import*, not as text: the function's own docstring
    # explains why importlib.metadata is not used, and a substring search would
    # match the explanation and fail on the very comment that documents it.
    src = os.path.join(_ROOT, "sloads/export/report_package.py")
    with open(src, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(name.startswith("importlib") for name in imported), (
        "the version stamp is back on install-time metadata, which goes stale "
        f"at every bump in an editable checkout: {sorted(imported)}")


def test_the_version_is_a_plain_dotted_literal():
    """Setuptools reads the attribute statically; anything computed would force
    it to import ``sloads``, whose dependencies the build environment lacks."""
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[.-]\w+)?", __version__), __version__
    with open(os.path.join(_ROOT, "sloads/_version.py"), encoding="utf-8") as fh:
        module = fh.read()
    assert re.search(r'^__version__ = "[^"]+"$', module, re.MULTILINE), (
        "the version must stay a module-level string literal")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
