import json

import pytest

from agent_service.observability import MetricsSummary, TraceWriter, calculate_cost, read_events


def test_trace_writer_records_success_span(tmp_path):
    """TraceWriter 会把成功 span 写成 JSONL。"""
    ticks = iter([1.0, 1.2])
    writer = TraceWriter(tmp_path / "trace.jsonl", clock=lambda: next(ticks))
    with writer.span("model", tokens=3) as span:
        span["cost"] = 0.1
    event = read_events(tmp_path / "trace.jsonl")[0]
    assert event["name"] == "model"
    assert event["ok"] is True
    assert event["duration_ms"] == pytest.approx(200.0)


def test_trace_writer_records_error_span(tmp_path):
    """TraceWriter 会记录异常类型和失败状态。"""
    ticks = iter([1.0, 1.1])
    writer = TraceWriter(tmp_path / "trace.jsonl", clock=lambda: next(ticks))
    with pytest.raises(ValueError):
        with writer.span("tool"):
            raise ValueError("bad")
    event = read_events(tmp_path / "trace.jsonl")[0]
    assert event["ok"] is False
    assert "ValueError" in event["error"]


def test_calculate_cost_uses_price_table():
    """成本按 prompt 和 completion 单价表计算。"""
    cost = calculate_cost("standard", {"prompt_tokens": 1000, "completion_tokens": 500})
    assert cost == pytest.approx(0.002)


def test_metrics_summary_calculates_rate_latency_and_cost():
    """汇总统计包含成功率、P50、P95 和平均成本。"""
    summary = MetricsSummary()
    for event in [
        {"ok": True, "duration_ms": 10, "cost": 0.1},
        {"ok": False, "duration_ms": 20, "cost": 0.3},
        {"ok": True, "duration_ms": 30, "cost": 0.2},
    ]:
        summary.add_event(event)
    data = summary.summary()
    assert data["success_rate"] == pytest.approx(2 / 3)
    assert data["p50_ms"] == 20
    assert data["avg_cost"] == pytest.approx(0.2)


def test_jsonl_events_are_structured(tmp_path):
    """写出的事件每行都是可解析 JSON 对象。"""
    writer = TraceWriter(tmp_path / "trace.jsonl")
    writer.write({"type": "model", "ok": True})
    assert json.loads((tmp_path / "trace.jsonl").read_text().strip())["type"] == "model"
