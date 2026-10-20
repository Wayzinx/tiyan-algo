import random

from evalrunner.analysis import EvalOutcome, bootstrap_compare, pass_at_k, pass_power, stability_consistency, threshold_gate, wilson_interval


def test_m4_pass_at_k_unbiased_estimator():
    """pass@k 使用无偏估计公式而不是简单幂次。"""
    assert round(pass_at_k(total_runs=10, correct_runs=2, k=3), 4) == 0.5333
    assert pass_at_k(total_runs=5, correct_runs=0, k=3) == 0.0
    assert pass_at_k(total_runs=5, correct_runs=4, k=3) == 1.0


def test_m4_pass_power_is_distinct_metric():
    """pass^k 按独立重复抽样计算。"""
    assert round(pass_power(0.2, 3), 3) == 0.488
    assert pass_power(0.5, 0) == 0.0


def test_m4_wilson_interval_handles_edges():
    """Wilson 区间在 0 和 1 的边界仍保持合法范围。"""
    low, high = wilson_interval(0, 10)
    assert low == 0.0 and 0 < high < 0.5
    low2, high2 = wilson_interval(10, 10)
    assert 0.5 < low2 < 1.0 and high2 == 1.0


def test_m4_bootstrap_compare_is_reproducible():
    """bootstrap 比较在注入随机种子后可复现。"""
    baseline = [True, False, False, True]
    candidate = [True, True, False, True]
    first = bootstrap_compare(baseline, candidate, samples=50, rng=random.Random(7))
    second = bootstrap_compare(baseline, candidate, samples=50, rng=random.Random(7))
    assert first == second
    assert first["mean_diff"] > 0


def test_m4_threshold_gate_checks_overall_and_tags():
    """阈值门禁同时检查总体和分标签通过率。"""
    rows = [
        EvalOutcome("c1", True, ["math"]),
        EvalOutcome("c2", False, ["math"]),
        EvalOutcome("c3", True, ["chat"]),
    ]
    result = threshold_gate(rows, overall_threshold=0.7, tag_thresholds={"math": 0.6, "chat": 1.0})
    assert result["passed"] is False
    assert result["failed"] == ["overall", "math"]


def test_m4_stability_consistency_groups_repeats():
    """稳定性指标按同一用例多次输出计算一致率。"""
    rows = [EvalOutcome("c1", True, output="a"), EvalOutcome("c1", True, output="a"), EvalOutcome("c1", False, output="b")]
    assert stability_consistency(rows)["c1"] == 2 / 3
