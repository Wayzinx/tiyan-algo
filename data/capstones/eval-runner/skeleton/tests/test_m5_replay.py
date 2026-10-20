import pytest

from evalrunner.agents import TraceEvent
from evalrunner.replay import Cassette, CassetteMissError, aggregate_badcases, call_with_cassette, classify_badcase


def test_m5_cassette_records_and_replays_by_fingerprint(tmp_path):
    """cassette 会按请求指纹录制并回放响应。"""
    cassette = Cassette(tmp_path / "model.json")
    request = {"model": "fake", "prompt": "hi"}
    key = cassette.record(request, {"text": "hello"})
    assert key in cassette.records
    assert Cassette(tmp_path / "model.json").replay(request) == {"text": "hello"}


def test_m5_replay_mode_does_not_call_sender(tmp_path):
    """回放命中时不会调用真实 sender。"""
    cassette = Cassette(tmp_path / "tool.json")
    cassette.record({"tool": "search", "q": "a"}, {"result": 1})
    called = False

    def sender(request):
        nonlocal called
        called = True
        return {}

    assert call_with_cassette(cassette, {"tool": "search", "q": "a"}, sender, mode="replay") == {"result": 1}
    assert called is False


def test_m5_replay_miss_raises_clear_error(tmp_path):
    """请求变化导致回放 miss 时会抛出明确错误。"""
    cassette = Cassette(tmp_path / "empty.json")
    with pytest.raises(CassetteMissError):
        cassette.replay({"prompt": "new"})


def test_m5_rule_based_badcase_classification():
    """规则分类可以识别工具、格式、超时和拒答问题。"""
    assert classify_badcase(output="x", error="TimeoutError: slow") == "timeout"
    assert classify_badcase(output="not-json", expected_format="json") == "format_error"
    assert classify_badcase(output="cannot answer this") == "improper_refusal"
    assert classify_badcase(output="x", trace=[TraceEvent(type="tool", name="unknown")]) == "tool_selection_error"


def test_m5_custom_classifier_overrides_rules():
    """注入分类函数可以覆盖默认 badcase 规则。"""
    result = classify_badcase(output="anything", classifier=lambda **kwargs: "hallucination")
    assert result == "hallucination"


def test_m5_aggregate_badcases_counts_and_ratios():
    """badcase 聚合会输出数量和比例。"""
    summary = aggregate_badcases(["timeout", "timeout", "format_error"])
    assert summary["timeout"] == {"count": 2, "ratio": 2 / 3}
    assert summary["format_error"]["count"] == 1
