from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


@dataclass
class EvalOutcome:
    """用于统计分析的轻量结果。"""

    case_id: str
    passed: bool
    tags: list[str] = field(default_factory=list)
    output: Any = None


def pass_at_k(total_runs: int, correct_runs: int, k: int) -> float:
    """计算 pass@k 无偏估计。"""
    raise NotImplementedError


def pass_power(pass_rate: float, k: int) -> float:
    """计算独立重复采样下的 pass^k。"""
    raise NotImplementedError


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """计算 Wilson 置信区间。"""
    raise NotImplementedError


def bootstrap_compare(
    baseline: Sequence[bool],
    candidate: Sequence[bool],
    *,
    samples: int = 500,
    rng: random.Random | None = None,
) -> dict[str, float]:
    """bootstrap 比较两个版本通过率差异。"""
    raise NotImplementedError


def threshold_gate(
    outcomes: Iterable[EvalOutcome],
    *,
    overall_threshold: float,
    tag_thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """按总体和标签阈值执行门禁。"""
    raise NotImplementedError


def stability_consistency(outcomes: Iterable[EvalOutcome]) -> dict[str, float]:
    """计算同一用例多次运行输出的一致率。"""
    raise NotImplementedError
