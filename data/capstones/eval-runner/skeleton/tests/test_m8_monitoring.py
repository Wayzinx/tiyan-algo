from pathlib import Path

from evalrunner.dataset import EvalCase
from evalrunner.monitoring import OnlineLog, UserFeedback, detect_metric_drift, feedback_to_case, merge_feedback_cases, sample_logs


def test_m8_samples_online_logs_with_injected_rng():
    """线上日志抽样使用注入随机源，结果可复现。"""
    logs = [OnlineLog(str(index), f"q{index}", "ok", 1.0, ["x"]) for index in range(4)]
    values = iter([0.1, 0.9, 0.2, 0.8])
    sampled = sample_logs(logs, 0.5, lambda: next(values))
    assert [row.request_id for row in sampled] == ["0", "2"]


def test_m8_feedback_converts_to_case():
    """用户反馈可以转换成带默认评分器的新用例。"""
    case = feedback_to_case(UserFeedback("1", "问题", "答案", ["qa"]))
    assert case.id == "fb-1"
    assert case.scorers == [{"type": "exact"}]
    assert "feedback" in case.tags


def test_m8_feedback_merge_deduplicates_existing_cases():
    """反馈入库前会与已有用例去重。"""
    existing = [EvalCase(id="fb-1", input="问题", expected="答案", scorers=[{"type": "exact"}], tags=["qa", "feedback"], difficulty="medium", source="feedback")]
    merged = merge_feedback_cases(existing, [UserFeedback("1", "问题", "答案", ["qa"]), UserFeedback("2", "新问题", "新答案", ["qa"])])
    assert [case.id for case in merged] == ["fb-1", "fb-2"]


def test_m8_metric_drift_alerts_on_sliding_window():
    """滑动窗口均值偏离基线超过阈值会触发漂移告警。"""
    result = detect_metric_drift([0.9, 0.8, 0.5, 0.4, 0.4], baseline=0.9, window=3, threshold=0.3)
    assert result["alerts"]
    assert result["alerts"][-1]["delta"] < 0


def test_m8_metric_drift_handles_insufficient_samples():
    """样本不足一个窗口时返回不可判定状态且无告警。"""
    result = detect_metric_drift([0.8], baseline=0.9, window=3, threshold=0.2)
    assert result == {"status": "insufficient", "alerts": []}


def test_m8_document_templates_exist_with_required_sections():
    """测试计划和验收报告模板包含必要章节。"""
    root = Path(__file__).resolve().parents[1]
    plan = (root / "docs" / "test_plan_template.md").read_text(encoding="utf-8")
    report = (root / "docs" / "acceptance_report_template.md").read_text(encoding="utf-8")
    assert "## 测试范围" in plan
    assert "## 准出结论" in report
