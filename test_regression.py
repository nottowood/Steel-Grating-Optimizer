"""Phase-3 Integration Regression Test Suite."""

from models import FabricatedPanel
from processor import process_panels, process_panels_optimized, process_panels_with_recovery


def make_panels():
    return [
        FabricatedPanel(mark="G01", product_code="TA325/1", fabricated_width=1115, fabricated_length=1450, qty=10),
        FabricatedPanel(mark="G02", product_code="TA325/1", fabricated_width=995, fabricated_length=1250, qty=25),
        FabricatedPanel(mark="G03", product_code="TA325/1", fabricated_width=965, fabricated_length=1250, qty=25),
        FabricatedPanel(mark="G04", product_code="TA325/1", fabricated_width=605, fabricated_length=1450, qty=10),
    ]


def test_1_phase1_baseline():
    print("=== TEST 1: Phase-1 Baseline ===")
    p, s, w = process_panels(make_panels())
    print(f"  Yield: {s.yield_percent}%")
    print(f"  Scrap: {s.scrap_percent}%")
    print(f"  Sold Area: {s.total_sold_area}")
    print(f"  Raw Material Area: {s.total_raw_material_area}")
    print(f"  Expansion: {s.expansion_count}, Reduction: {s.reduction_count}")
    print(f"  Warnings: {w}")
    return s, w


def test_2_phase2_baseline():
    print("=== TEST 2: Phase-2 Baseline ===")
    p, s, opt, w = process_panels_optimized(make_panels())
    print(f"  Yield: {s.yield_percent}%")
    print(f"  Scrap: {s.scrap_percent}%")
    print(f"  Consistency: {opt.overall_consistency}%")
    print(f"  Yield Individual: {opt.yield_individual}%")
    print(f"  Yield Optimized: {opt.yield_optimized}%")
    print(f"  Warnings: {w}")
    for fg in opt.floor_groups:
        print(f"  Floor Group: {fg.group_name}")
        print(f"    Common Start: {fg.common_start}")
        print(f"    Coverage: {fg.coverage_percent}%")
        print(f"    Status: {fg.consistency_status}")
        for i, sc in enumerate(fg.all_scenarios):
            print(f"    Scenario {i+1}: start={sc.representative_start}, score={sc.score}, selected={sc.selected}, rejection={sc.rejection_reason}")
    return s, opt, w


def test_3_phase3_depth_none():
    print("=== TEST 3: Phase-3 (depth_map=None) ===")
    r = process_panels_with_recovery(make_panels(), depth_map=None)
    s = r["summary"]
    rec = r["recovery_summary"]
    val = r["validation_report"]
    print(f"  Frozen Yield: {s.yield_percent}%")
    print(f"  Recovery Rate: {rec.recovery_rate}%")
    print(f"  Matches: {len(rec.matches)}")
    print(f"  Unmatched: {len(rec.unmatched_demands)}")
    print(f"  Validation Passed: {val.all_passed}")
    print(f"  Warnings: {r['warnings']}")
    return r


def test_4_phase3_depth_provided():
    print("=== TEST 4: Phase-3 (depth_map provided) ===")
    r = process_panels_with_recovery(make_panels(), depth_map={"TA325/1": 25.0})
    s = r["summary"]
    rec = r["recovery_summary"]
    val = r["validation_report"]
    print(f"  Frozen Yield: {s.yield_percent}%")
    print(f"  Recovery Rate: {rec.recovery_rate}%")
    print(f"  Matches: {len(rec.matches)}")
    print(f"  Unmatched: {len(rec.unmatched_demands)}")
    print(f"  Recovered Area: {rec.recovered_area_m2}")
    print(f"  Dead Scrap Area: {rec.dead_scrap_area_m2}")
    print(f"  Remaining Stock: {rec.remaining_stock_area_m2}")
    print(f"  Validation Passed: {val.all_passed}")
    for v in val.results:
        print(f"    {v.rule_id}: {v.status} - {v.detail}")
    print(f"  Warnings: {r['warnings']}")
    return r


def test_5_frozen_kpi_bitexact(s1, s2, r3, r4):
    print("=== TEST 5: Frozen KPI Bit-Exact ===")
    s3 = r3["summary"]
    s4 = r4["summary"]
    all_pass = True
    for name in ["yield_percent", "scrap_percent", "total_sold_area", "total_production_area", "total_raw_material_area"]:
        v1 = getattr(s1, name)
        v2 = getattr(s2, name)
        v3 = getattr(s3, name)
        v4 = getattr(s4, name)
        ok = v1 == v2 == v3 == v4
        if not ok:
            all_pass = False
        print(f"  {name}: P1={v1}, P2={v2}, P3a={v3}, P3b={v4} -> {'PASS' if ok else 'FAIL'}")
    print(f"  Overall: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


def test_6_scoring_ranking(opt2, r4):
    print("=== TEST 6: Scoring/Ranking ===")
    opt3 = r4["opt_summary"]
    all_pass = True
    for fg2, fg3 in zip(opt2.floor_groups, opt3.floor_groups):
        cs_ok = fg2.common_start == fg3.common_start
        cov_ok = fg2.coverage_percent == fg3.coverage_percent
        if not cs_ok or not cov_ok:
            all_pass = False
        print(f"  {fg2.group_name}: CommonStart P2={fg2.common_start} P3={fg3.common_start} {'PASS' if cs_ok else 'FAIL'}")
        print(f"  {fg2.group_name}: Coverage P2={fg2.coverage_percent}% P3={fg3.coverage_percent}% {'PASS' if cov_ok else 'FAIL'}")
        for s2, s3 in zip(fg2.all_scenarios, fg3.all_scenarios):
            sc_ok = s2.score == s3.score
            sel_ok = s2.selected == s3.selected
            if not sc_ok or not sel_ok:
                all_pass = False
            print(f"    start={s2.representative_start}: score={s2.score}/{s3.score} {'PASS' if sc_ok else 'FAIL'} | selected={s2.selected}/{s3.selected} {'PASS' if sel_ok else 'FAIL'}")
    print(f"  Overall: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


def test_7_warnings(w1, w2, r3, r4):
    print("=== TEST 7: Warnings ===")
    w3 = r3["warnings"]
    w4 = r4["warnings"]
    ok = w1 == w2 == w3 == w4
    print(f"  P1: {w1}")
    print(f"  P2: {w2}")
    print(f"  P3a: {w3}")
    print(f"  P3b: {w4}")
    print(f"  All identical: {'PASS' if ok else 'FAIL'}")
    return ok


def test_8_return_structure(r4):
    print("=== TEST 8: Return Structure ===")
    expected = {"processed", "summary", "opt_summary", "warnings", "recovery_summary", "validation_report", "recovery_report"}
    actual = set(r4.keys())
    ok = expected == actual
    print(f"  Expected: {sorted(expected)}")
    print(f"  Actual:   {sorted(actual)}")
    print(f"  Match: {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    s1, w1 = test_1_phase1_baseline()
    print()
    s2, opt2, w2 = test_2_phase2_baseline()
    print()
    r3 = test_3_phase3_depth_none()
    print()
    r4 = test_4_phase3_depth_provided()
    print()
    t5 = test_5_frozen_kpi_bitexact(s1, s2, r3, r4)
    print()
    t6 = test_6_scoring_ranking(opt2, r4)
    print()
    t7 = test_7_warnings(w1, w2, r3, r4)
    print()
    t8 = test_8_return_structure(r4)
    print()

    results = [
        ("Frozen KPI Bit-Exact", t5),
        ("Scoring/Ranking", t6),
        ("Warnings", t7),
        ("Return Structure", t8),
    ]
    print("=== REGRESSION SUMMARY ===")
    all_ok = True
    for name, passed in results:
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_ok = False
    print(f"  OVERALL: {'PASS' if all_ok else 'FAIL'}")
