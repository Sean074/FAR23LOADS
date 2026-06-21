"""Per-program load modules for the FAR 23 LOADS suite.

Importing this package imports each module so it registers itself with
:mod:`farloads.registry`. Phase 0 shipped the engine-mount module; Phase 1 adds
the mass-properties modules (weight estimation and one-condition CG/inertia).
"""

from . import airloads  # noqa: F401  (import for side effect: self-registration)
from . import body_loads  # noqa: F401
from . import configuration  # noqa: F401
from . import engine  # noqa: F401
from . import flight_envelope  # noqa: F401
from . import mach_limit  # noqa: F401
from . import net_loads  # noqa: F401
from . import select  # noqa: F401
from . import structural_speeds  # noqa: F401
from . import taildist  # noqa: F401
from . import weight_envelope  # noqa: F401
from . import weight_estimate  # noqa: F401
from . import weight_onecg  # noqa: F401
from . import wing_geometry  # noqa: F401
from . import wing_inertia  # noqa: F401
