import pytest

from evalrunner.agents import TraceEvent
from evalrunner.scorers import assert_trace, cohens_kappa, llm_as_judge, reviewer_accuracy, score_output


def test_m3_basic_scorers_cover_exact_contains_regex():
    """基础评分器支持 exact、contains 和 regex。"""
    assert score_output("abc", "abc", {"type": "exact"}).passed
    assert score_output("hello world", "world", {"type": "contains"}).passed
    assert score_output("订单号 A123", None, {"type": "regex", "pattern": r"A\d+"}).passed


def test_m3_json_schema_and_numeric_tolerance():
    """JSON Schema 子集和数值容差能处理边界值。"""
    schema = {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "number"}}}
    assert score_output({"answer": 3.14}, schema, {"type": "json_schema", "schema": schema}).passed
    assert score_output(9.9, 10, {"type": "numeric_tolerance", "tolerance": 0.1}).passed
    assert not score_output({"answer": "bad"}, schema, {"type": "json_schema", "schema": schema}).passed


def test_m3_custom_property_function_is_injected():
    """自定义属性评分函数通过注册表注入。"""
    custom = {"len_at_least": lambda output, expected, cfg: len(output) >= cfg["min"]}
    result = score_output("abcd", None, {"type": "custom_property", "name": "len_at_least", "min": 4}, custom)
    assert result.passed and result.score == 1.0


def test_m3_trace_assertions_check_tools_arguments_and_order():
    """轨迹断言会检查必调工具、参数、顺序和最大步数。"""
    trace = [
        TraceEvent(type="message", content="start"),
        TraceEvent(type="tool", name="search", arguments={"q": "cat"}),
        TraceEvent(type="tool", name="calc", arguments={"x": 2}),
    ]
    result = assert_trace(trace, {"must_call": ["search"], "order": ["search", "calc"], "max_steps": 3, "arguments": [{"tool": "search", "name": "q", "equals": "cat"}]})
    assert result.passed
    assert not assert_trace(trace, {"forbidden_tools": ["calc"]}).passed


def test_m3_llm_judge_returns_score_and_reason():
    """LLM-as-judge 使用注入函数返回分数和理由。"""
    def judge(output, expected, rubric):
        return {"score": 0.8, "threshold": 0.7, "reason": f"{rubric}:{output}:{expected}"}

    result = llm_as_judge("ok", "ok", "是否正确", judge)
    assert result.passed
    assert "是否正确" in result.reason


def test_m3_reviewer_consistency_metrics():
    """人工标注一致性会计算准确率和 Cohen's kappa。"""
    predictions = ["pass", "fail", "pass", "fail"]
    labels = ["pass", "fail", "fail", "fail"]
    assert reviewer_accuracy(predictions, labels) == 0.75
    assert round(cohens_kappa(predictions, labels), 2) == 0.5
    with pytest.raises(ValueError):
        reviewer_accuracy([1], [1, 2])
