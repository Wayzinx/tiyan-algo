from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .agents import TraceEvent


@dataclass
class ScoreResult:
    """评分结果。"""

    passed: bool
    score: float
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


def score_output(output: Any, expected: Any, scorer: dict[str, Any], custom: dict[str, Callable[..., bool]] | None = None) -> ScoreResult:
    """按配置对输出评分。"""
    raise NotImplementedError


def validate_json_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """校验一个轻量 JSON Schema 子集。"""
    raise NotImplementedError


def assert_trace(trace: list[TraceEvent], assertions: dict[str, Any]) -> ScoreResult:
    """检查工具轨迹：必调、禁用、参数、顺序和最大步数。"""
    raise NotImplementedError


def llm_as_judge(output: Any, expected: Any, rubric: str, judge: Callable[[Any, Any, str], dict[str, Any]]) -> ScoreResult:
    """通过注入的 judge 函数按 rubric 打分并返回理由。"""
    raise NotImplementedError


def reviewer_accuracy(predictions: list[Any], labels: list[Any]) -> float:
    """计算评审结果与人工标注的一致准确率。"""
    raise NotImplementedError


def cohens_kappa(predictions: list[Any], labels: list[Any]) -> float:
    """计算 Cohen's kappa。"""
    raise NotImplementedError
