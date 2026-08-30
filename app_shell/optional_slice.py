"""Whether an Apply creates an ``Optional`` project slice, or leaves it absent.

#143 settled the rule for the oracle GUI: an ``Optional`` record is created by a
named gesture and removed by a named gesture, never attached because a widget in
its block was touched. That fix was registry-driven and reached
``oracle_app/form.py`` only, so the main GUI kept attaching. Pressing **Apply**
on a page whose form nobody filled in wrote a whole zero-valued slice into the
project — `aileron_loads`, `flap_loads`, `tab_loads`, `select_input`,
`fuselage_mass`, `landing`, `engine_layout`, `one_engine_out`, depending on which
page was visited — and the slice then saved into the ``.project.json``. Two of
them are not cosmetic: a zero-area ``flap_loads`` makes the ``flap`` module run
and raise, which took **Results Review and Export down on three of the seven
bundled examples** (#145).

Here the named gesture is the Apply button itself, so the app-side form of the
same rule is narrower than the oracle GUI's add/remove pair and needs no change
to any page's layout:

    **An Apply may fill a slice in, and may empty one out. It may not create one
    out of nothing.**

:func:`store` is the single owner of that decision (``CLAUDE.md`` rule 3) — one
predicate instead of eight page-local conditions that drift apart — and
``tests/test_gui_journey.py`` is its drift guard: it walks every page of every
bundled example pressing every Apply with nothing entered, so a new page that
writes an ``Optional`` slice directly fails the walk the day it is written.

Note the asymmetry, which is deliberate and is the half #143 insisted on: an
*existing* slice is written back unconditionally, so unticking a box or clearing
a field still lands. "Never write" would satisfy the attachment rule on its own
and break the page.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional, TypeVar

T = TypeVar("T")


def entered_nothing(record: Any) -> bool:
    """True when every field of ``record`` still holds its declared default.

    Read off the dataclass rather than from a per-page list of fields, so a
    field added to a slice later is covered the day it is added. A field with no
    declared default (a required constructor argument) counts as entered when it
    is truthy, which is the only reading available: there is no default to
    compare it against.
    """
    if not dataclasses.is_dataclass(record) or isinstance(record, type):
        return False
    for field in dataclasses.fields(record):
        value = getattr(record, field.name)
        if field.default is not dataclasses.MISSING:
            if value != field.default:
                return False
        elif field.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            if value != field.default_factory():  # type: ignore[misc]
                return False
        elif value:
            return False
    return True


def store(record: T, existing: Optional[T], seed: Optional[T] = None) -> Optional[T]:
    """The value to persist for an ``Optional`` slice on Apply.

    ``existing`` is the slice as it stood **before** this page's form touched it
    — capture it above the widgets, since the page usually mutates the record in
    place. Returns ``record`` whenever the project already had the slice or the
    form entered something, and ``None`` when Apply would otherwise attach a
    slice nobody filled in.

    ``seed`` is for the pages whose widgets do **not** default to the dataclass's
    own defaults — an engine form whose blade-count minimum is 2, say, builds a
    record that is not all-defaults even when nobody typed in it. Pass the record
    the form was seeded from and "entered nothing" becomes "did not move it",
    which is the same question asked where the all-defaults test cannot answer
    it.
    """
    if existing is not None:
        return record
    if seed is not None:
        return None if record == seed else record
    return None if entered_nothing(record) else record
