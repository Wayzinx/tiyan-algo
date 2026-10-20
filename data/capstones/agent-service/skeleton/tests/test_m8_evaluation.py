from pathlib import Path

from agent_service.agent import AgentRunner
from agent_service.evaluation import compare_reports, evaluate, load_dataset, write_markdown_report
from agent_service.llm import FakeLLM
from agent_service.tools import ToolRegistry


def test_eval_dataset_has_at_least_twenty_cases():
    """评测集至少 20 条并覆盖多个任务类型。"""
    cases = load_dataset(Path(__file__).parents[1] / "eval" / "dataset.jsonl")
    assert len(cases) >= 20
    assert {case["category"] for case in cases} >= {"tool", "rag", "refusal", "recovery"}


def test_evaluate_calculates_success_rate_and_average_rounds():
    """评测脚本能计算成功率和平均轮数。"""
    dataset = [{"id": "e1", "input": "hi", "expected": "ok"}, {"id": "e2", "input": "hi", "expected": "missing"}]
    result = evaluate(lambda: AgentRunner(FakeLLM(["ok"]), ToolRegistry()), dataset)
    assert result["total"] == 2
    assert result["task_success_rate"] == 0.5
    assert result["avg_rounds"] == 1


def test_evaluate_tracks_tool_call_accuracy():
    """评测脚本能统计期望工具是否被调用。"""
    registry = ToolRegistry()

    @registry.register(name="echo")
    def echo(text: str) -> str:
        return text

    script = [{"tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "ok"}}]}, "ok"]
    result = evaluate(lambda: AgentRunner(FakeLLM(script.copy()), registry), [{"id": "e1", "input": "x", "expected": "ok", "expected_tools": ["echo"]}])
    assert result["tool_call_accuracy"] == 1.0


def test_compare_reports_outputs_markdown_table():
    """两个配置的对比报告会输出 Markdown 表格。"""
    md = compare_reports("base", {"task_success_rate": 0.5}, "new", {"task_success_rate": 0.8})
    assert "| 指标 | base | new |" in md
    assert "task_success_rate" in md


def test_report_template_and_write_report_exist(tmp_path):
    """复盘模板存在，评测报告可写入 Markdown 文件。"""
    template = Path(__file__).parents[1] / "docs" / "report_template.md"
    assert "问题与归因" in template.read_text(encoding="utf-8")
    out = tmp_path / "report.md"
    write_markdown_report(out, "# report")
    assert out.read_text(encoding="utf-8") == "# report"
