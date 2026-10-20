import json

from evalrunner.analysis import EvalOutcome
from evalrunner.cli import main
from evalrunner.reports import compare_results, render_html, render_markdown, run_gate, write_report


def test_m6_markdown_report_contains_required_sections():
    """Markdown 报告包含总览、分标签、失败明细和基线对比。"""
    rows = [EvalOutcome("c1", True, ["math"], "ok"), EvalOutcome("c2", False, ["chat"], "bad")]
    baseline = [EvalOutcome("c2", True, ["chat"], "ok")]
    report = render_markdown(rows, baseline)
    assert "## 总览" in report
    assert "## 分标签" in report
    assert "## 失败明细" in report
    assert "回归：c2" in report


def test_m6_html_report_escapes_failure_output():
    """HTML 报告会转义失败输出，避免报告注入。"""
    html = render_html([EvalOutcome("c1", False, ["x"], "<script>alert(1)</script>")])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_m6_compare_results_lists_regressions_and_improvements():
    """基线对比能列出回归和改进用例。"""
    baseline = [EvalOutcome("a", True), EvalOutcome("b", False)]
    candidate = [EvalOutcome("a", False), EvalOutcome("b", True)]
    assert compare_results(baseline, candidate) == {"regressions": ["a"], "improvements": ["b"]}


def test_m6_write_report_creates_markdown_html_json(tmp_path):
    """报告写出函数会生成 Markdown、HTML 和 JSON 三类产物。"""
    paths = write_report([EvalOutcome("c1", True, ["x"], "ok")], tmp_path)
    assert paths["markdown"].exists()
    assert paths["html"].exists()
    assert json.loads(paths["json"].read_text(encoding="utf-8"))[0]["case_id"] == "c1"


def test_m6_gate_failure_returns_non_zero_intent():
    """门禁失败结果可用于 CLI 非 0 退出码。"""
    gate = run_gate([EvalOutcome("c1", False, ["x"])], {"gate": {"overall": 0.5}})
    assert gate["passed"] is False


def test_m6_cli_run_and_compare(tmp_path, capsys):
    """evalrun run 和 compare 子命令可在本地文件上运行。"""
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(json.dumps({"id": "c1", "input": "hi", "expected": "hi", "scorers": [{"type": "exact"}], "tags": ["x"], "difficulty": "easy", "source": "test"}) + "\n", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(f"dataset: {dataset}\noutput_dir: {tmp_path / 'out'}\ngate:\n  overall: 1.0\n", encoding="utf-8")
    assert main(["run", str(config)]) == 0
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(f"dataset: {dataset}\noutput_dir: {tmp_path / 'bad'}\nfake_responses:\n  hi: wrong\ngate:\n  overall: 1.0\n", encoding="utf-8")
    assert main(["run", str(bad_config)]) == 1
    left = tmp_path / "a.json"
    right = tmp_path / "b.json"
    left.write_text(json.dumps([{"case_id": "c1", "passed": True}]), encoding="utf-8")
    right.write_text(json.dumps([{"case_id": "c1", "passed": False}]), encoding="utf-8")
    assert main(["compare", str(left), str(right)]) == 0
    assert "regressions" in capsys.readouterr().out
