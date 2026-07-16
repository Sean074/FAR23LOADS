"""Unit tests for the pure fleet-comparison helper (``farloads.fleet``).

The Aircraft Comparison page places one airplane against
``app/data/reference_aircraft.csv`` via this helper (GUI_design §8.4). The numeric
core is pure -- no pandas, no CSV, no Streamlit -- so these tests build a small
in-memory fleet fixture and assert the nearest-N ordering, the percentile band and
the outlier flags directly. The geometry fields (span / AR / seats, backlog F2) are
presentation-only, so a dedicated test proves they add no distance term.
"""

import math

from farloads.fleet import (
    FleetPoint,
    Subject,
    fleet_stats,
    percentile,
    percentile_rank,
)

# A compact fixture spanning a GA single -> light twin -> regional turboprop, plus a
# jet (max_hp = 0 -> no W/P) so the jet-exclusion rule is exercised.
FLEET = [
    FleetPoint("Cessna 150", 1600, 1111, 100, 160),   # W/S 10.0, W/P 16.0
    FleetPoint("Cessna 172", 2450, 1691, 180, 174),   # W/S 14.1, W/P 13.6
    FleetPoint("Bonanza A36", 3650, 2530, 300, 181),  # W/S 20.2, W/P 12.2
    FleetPoint("King Air 200", 12500, 8060, 1700, 303),  # W/S 41.3, W/P 7.4
    FleetPoint("Saab 340B", 28500, 17715, 3520, 450),    # W/S 63.3, W/P 8.1
    FleetPoint("Citation CJ3", 13870, 8770, 0, 294),     # jet: no W/P
]


def test_fleet_point_derived_loadings():
    p = FleetPoint("Cessna 172", 2450, 1691, 180, 174)
    assert math.isclose(p.w_s, 2450 / 174, rel_tol=1e-9)
    assert math.isclose(p.w_p, 2450 / 180, rel_tol=1e-9)
    jet = FleetPoint("Citation CJ3", 13870, 8770, 0, 294)
    assert jet.w_p is None  # no shaft power


def test_nearest_picks_the_closest_and_orders_by_distance():
    # A subject sitting essentially on the Cessna 172 should rank it first.
    subject = Subject("Test 172-like", mtow_lb=2450, oew_lb=1700, wing_area_ft2=174, power_hp=180)
    stats = fleet_stats(subject, FLEET, n=3)
    assert len(stats.nearest) == 3
    assert stats.nearest[0][0].name == "Cessna 172"
    assert math.isclose(stats.nearest[0][1], 0.0, abs_tol=1e-6)
    # distances are non-decreasing
    dists = [d for _, d in stats.nearest]
    assert dists == sorted(dists)


def test_default_nearest_n_is_three():
    subject = Subject("x", mtow_lb=3000, wing_area_ft2=170, power_hp=250)
    assert len(fleet_stats(subject, FLEET).nearest) == 3


def test_jet_ranks_as_neighbour_despite_missing_w_p():
    # A heavy subject near the CJ3 in MTOW/W-S should still find the jet as a
    # neighbour -- the missing W/P axis just drops out of its distance term.
    subject = Subject("bizjet-like", mtow_lb=13870, wing_area_ft2=294, power_hp=None)
    names = [p.name for p, _ in fleet_stats(subject, FLEET, n=6).nearest]
    assert "Citation CJ3" in names


def test_percentile_rank_and_band():
    # W/S population (all six carry a wing area): compute the rank of a mid value.
    ws_values = sorted(p.w_s for p in FLEET)
    # a subject W/S above every fleet member -> ~100th percentile
    subject_hi = Subject("heavy", mtow_lb=40000, wing_area_ft2=450, power_hp=4000)
    stats = fleet_stats(subject_hi, FLEET)
    assert stats.ws_percentile == 100.0
    # band low <= high, and both drawn from the fleet range
    assert stats.ws_band is not None
    lo, hi = stats.ws_band
    assert lo <= hi
    assert min(ws_values) <= lo <= hi <= max(ws_values)


def test_outlier_flag_when_outside_band():
    # A very high W/S (heavy on a tiny wing) sits above the p90 band -> W/S outlier.
    subject = Subject("stubby", mtow_lb=30000, wing_area_ft2=200, power_hp=3000)
    stats = fleet_stats(subject, FLEET)
    assert "W/S" in stats.outliers


def test_no_outlier_for_a_central_design():
    # A garden-variety single sits inside the p10-p90 band on both loadings.
    subject = Subject("normal single", mtow_lb=2450, wing_area_ft2=174, power_hp=180)
    stats = fleet_stats(subject, FLEET)
    assert stats.outliers == []


def test_subject_without_wing_area_has_no_ws_metric():
    # The Weight Estimate page supplies MTOW/OEW/power but no wing area.
    subject = Subject("weight-est", mtow_lb=3000, oew_lb=1900, power_hp=250)
    stats = fleet_stats(subject, FLEET)
    assert stats.ws_percentile is None
    assert stats.ws_band is None
    assert "W/S" not in stats.outliers
    assert stats.wp_percentile is not None  # W/P still computable


def test_subject_span_derivation():
    # Explicit span wins; else span = sqrt(AR * S); else None.
    assert Subject("s", mtow_lb=3000, wing_area_ft2=170, wingspan_ft=36.0).span == 36.0
    derived = Subject("s", mtow_lb=3000, wing_area_ft2=180, aspect_ratio=7.5).span
    assert derived is not None and math.isclose(derived, math.sqrt(7.5 * 180))
    assert Subject("s", mtow_lb=3000, wing_area_ft2=180).span is None  # no AR, no span
    assert Subject("s", mtow_lb=3000).span is None  # no area either


def test_subject_aspect_ratio_derivation():
    # Explicit AR wins; else AR = span^2 / S; else None.
    assert Subject("s", mtow_lb=3000, wing_area_ft2=180, aspect_ratio=7.5).aspect_ratio_effective == 7.5
    derived = Subject("s", mtow_lb=3000, wing_area_ft2=180, wingspan_ft=36.0).aspect_ratio_effective
    assert derived is not None and math.isclose(derived, 36.0 ** 2 / 180)
    assert Subject("s", mtow_lb=3000, wing_area_ft2=180).aspect_ratio_effective is None


def test_fleet_point_span_and_aspect_ratio_match_subject_rules():
    # FleetPoint carries the same presentation-only derivations as Subject.
    p = FleetPoint("x", 2450, 1691, 180, 174, wingspan_ft=36.1, aspect_ratio=7.5)
    assert p.span == 36.1
    assert p.aspect_ratio_effective == 7.5
    q = FleetPoint("y", 2450, 1691, 180, 180, aspect_ratio=7.5)  # span derived
    assert q.span is not None and math.isclose(q.span, math.sqrt(7.5 * 180))


def test_geometry_fields_add_no_distance_term():
    # The nearest-N ranking runs on MTOW / W/S / W/P only (decision D-F2-a): a subject
    # with geometry ranks byte-identically to the same subject without it.
    base = Subject("t", mtow_lb=2450, oew_lb=1700, wing_area_ft2=174, power_hp=180)
    with_geom = Subject("t", mtow_lb=2450, oew_lb=1700, wing_area_ft2=174, power_hp=180,
                        wingspan_ft=36.1, aspect_ratio=7.5, seats=4)
    a = fleet_stats(base, FLEET, n=6)
    b = fleet_stats(with_geom, FLEET, n=6)
    assert [(p.name, round(d, 12)) for p, d in a.nearest] == \
           [(p.name, round(d, 12)) for p, d in b.nearest]
    assert a.ws_percentile == b.ws_percentile
    assert a.wp_percentile == b.wp_percentile
    assert a.outliers == b.outliers


def test_percentile_helpers_standalone():
    assert percentile_rank(5, [1, 2, 3, 4, 5]) == 100.0
    assert percentile_rank(3, [1, 2, 3, 4, 5]) == 60.0
    assert percentile_rank(0, [1, 2, 3]) == 0.0
    assert percentile_rank(1, []) is None
    assert percentile([1, 2, 3, 4, 5], 50) == 3.0
    assert percentile([10, 20], 0) == 10.0
    assert percentile([10, 20], 100) == 20.0
    assert percentile([], 50) is None


def test_empty_fleet_is_safe():
    subject = Subject("lonely", mtow_lb=2000, wing_area_ft2=150, power_hp=150)
    stats = fleet_stats(subject, [])
    assert stats.nearest == []
    assert stats.ws_percentile is None
    assert stats.outliers == []


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
