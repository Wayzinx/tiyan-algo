from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable


class EvalCase(dict):
    """评测样例字典类型。"""


def load_dataset(path: str | Path) -> list[EvalCase]:
    """读取 JSONL 评测集，并校验每条包含 id、input、expected。"""
    raise NotImplementedError


def evaluate(agent_factory: Callable[[], Any], dataset: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """执行评测，计算任务成功率、工具正确率、平均轮数、延迟和成本。"""
    raise NotImplementedError


def compare_reports(name_a: str, result_a: dict[str, Any], name_b: str, result_b: dict[str, Any]) -> str:
    """生成两个配置的 Markdown 对比报告。"""
    raise NotImplementedError


def write_markdown_report(path: str | Path, markdown: str) -> None:
    """写出 Markdown 报告。"""
    raise NotImplementedError
