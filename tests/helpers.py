"""Shared test helpers (M4-12a).

Before this module every second test file carried its own private ``_value``
lookup -- nine near-identical copies with three subtly different signatures
(one ``ConditionResult`` vs. a list of them; value vs. ``LoadValue``) -- and
seven files imported fixtures out of ``test_engine``, so a test module was also
a library. Both are consolidated here.

The three lookup functions are the D-18 API (see
``docs/40_history/07_m4_maintainability_sequence_plan.md`` §2). They all take the
same ``source``: a :class:`~sloads.models.ModuleResult`, a single
:class:`~sloads.models.ConditionResult`, or a (possibly nested) list of either
-- the same normalisation ``sloads.io._as_conditions`` performs for the CSV
writer. All raise ``KeyError`` on a missing key, matching the helpers they
replace.

All three look up ``LoadValue.key`` -- the calc's stable machine identity for a
quantity -- **not** the display label (**M4-9**). That is the point of having
consolidated them here first: re-pointing ~150 assertions was one edit to three
functions plus a mechanical rename of the string constants, and a reworded label
now breaks nothing.

Test input builders live next door in :mod:`fixtures`; no test module imports
another test module.
"""

from typing import Dict


def _conditions(source):
    """Normalise ``source`` to a flat list of ``ConditionResult``.

    Accepts a ``ModuleResult`` (has ``.conditions``), a ``ConditionResult``
    (has ``.values``), or any iterable of those, nested arbitrarily.
    """
    if hasattr(source, "conditions"):
        return list(source.conditions)
    if hasattr(source, "values"):
        return [source]
    out = []
    for item in source:
        out.extend(_conditions(item))
    return out


def load_value(source, key):
    """The first :class:`LoadValue` whose ``key`` is ``key``. ``KeyError`` if absent.

    Use this when the assertion is about ``units`` or ``quantity``; use
    :func:`value_of` when only the number matters.
    """
    for cond in _conditions(source):
        for v in cond.values:
            if v.key == key:
                return v
    raise KeyError(key)


def value_of(source, key) -> float:
    """The first value keyed ``key``. ``KeyError`` if absent."""
    return load_value(source, key).value


def values_by_key(source) -> Dict[str, float]:
    """Every ``key -> value`` pair, flattened across all conditions.

    Later duplicates win, so this is for property tables whose keys are unique
    across conditions; prefer :func:`value_of` when one quantity is under test.
    """
    out = {}
    for cond in _conditions(source):
        for v in cond.values:
            out[v.key] = v.value
    return out


# --------------------------------------------------------------------------- #
# Streamlit AppTest
# --------------------------------------------------------------------------- #
def widgets_editing(at, path, kind="number_input"):
    """Every ``kind`` widget in ``at`` whose key edits ``path``.

    A widget key is not the thing it edits. Two shell mechanisms decorate it:
    ``unit_number_input`` appends the active unit system, so a system switch
    re-seeds the field, and ``app_shell.widget_keys`` prefixes the *project
    generation*, so a project replacement retires the widget. Both are the
    shell's business, not a test's — this matches on what the widget edits and
    lets either decoration be whatever the shell chose. Three test modules had
    grown their own copy of this lookup before it moved here.
    """
    from app_shell.widget_keys import unstamped

    hits = []
    for widget in getattr(at, kind):
        base = unstamped(widget.key)
        if base == path or base.startswith(f"{path}_"):
            hits.append(widget)
    return hits


def widget_editing(at, path, kind="number_input"):
    """The one ``kind`` widget editing ``path``; fails if there is not exactly one."""
    hits = widgets_editing(at, path, kind)
    assert len(hits) == 1, (
        f"expected one {kind} for {path!r}, got {[w.key for w in hits]}")
    return hits[0]


def apply_button(at, form_key: str):
    """The submit button of the form keyed ``form_key``, or fail loudly.

    ``AppTest`` exposes every ``st.form_submit_button`` in the flat ``at.button``
    list, so selecting "the Apply button" positionally silently rebinds to a
    different form whenever a view gains, loses or reorders one -- and the test
    keeps passing while asserting something else entirely. Selecting through the
    form's key is stable, and the assertion below turns a key rename into a
    failure instead of an empty selection.
    """
    hits = [b for b in at.button if b.proto.form_id == form_key]
    assert hits, (
        f"no submit button found for form {form_key!r}; "
        f"forms present: {sorted({b.proto.form_id for b in at.button})}"
    )
    assert len(hits) == 1, f"form {form_key!r} has {len(hits)} submit buttons"
    return hits[0]


# --------------------------------------------------------------------------- #
# Free-field BDF reader (sbeam export deck)
# --------------------------------------------------------------------------- #
# The reader now lives in ``sloads.export.equilibrium`` -- production code, so
# the round-trip harness and any later runtime deck validator read decks the same
# way the tests do rather than reimplementing it. Re-exported here so no existing
# test import moves.
from sloads.export.equilibrium import parse_cards  # noqa: E402,F401
