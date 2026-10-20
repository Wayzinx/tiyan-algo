from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .analysis import EvalOutcome


def summarize(outcomes: Iterable[EvalOutcome]) -> dict[str, Any]:
    """汇总总体和分标签通过率。"""
    raise NotImplementedError


def compare_results(baseline: Iterable[EvalOutcome], candidate: Iterable[EvalOutcome]) -> dict[str, list[str]]:
    """对比基线和候选版本，列出回归与改进。"""
    raise NotImplementedError


def render_markdown(outcomes: Iterable[EvalOutcome], baseline: Iterable[EvalOutcome] | None = None) -> str:
    """生成 Markdown 报告。"""
    raise NotImplementedError


def render_html(outcomes: Iterable[EvalOutcome], baseline: Iterable[EvalOutcome] | None = None) -> str:
    """生成 HTML 报告，并转义用例输出。"""
    raise NotImplementedError


def write_report(outcomes: Iterable[EvalOutcome], output_dir: str | Path) -> dict[str, Path]:
    """写出 Markdown、HTML 和 JSON 报告。"""
    raise NotImplementedError


def run_gate(outcomes: Iterable[EvalOutcome], config: dict[str, Any]) -> dict[str, Any]:
    """执行报告门禁配置。"""
    raise NotImplementedError
