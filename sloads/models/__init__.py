"""Project schema + per-module input/result dataclasses.

Split from the former single ``models.py`` at M3-1 into lifecycle submodules
(enums / inputs / results / project). Every public name is re-exported here so
``from sloads.models import X`` and the ``sloads`` package re-export block keep
resolving unchanged.
"""

# ruff: noqa: I001  -- the star-import order is the resolution order (project last); keep it explicit
from .enums import *  # noqa: F403
from .inputs import *  # noqa: F403
from .results import *  # noqa: F403
from .project import *  # noqa: F403

from .enums import __all__ as _enums_all
from .inputs import __all__ as _inputs_all
from .results import __all__ as _results_all
from .project import __all__ as _project_all

__all__ = [*_enums_all, *_inputs_all, *_results_all, *_project_all]  # noqa: PLE0604  -- assembled from the submodules' own lists
