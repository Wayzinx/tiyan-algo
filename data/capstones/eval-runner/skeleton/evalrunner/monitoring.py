from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .dataset import EvalCase


@dataclass(frozen=True)
class OnlineLog:
    """线上日志样本。"""

    request_id: str
    input: Any
    output: Any
    score: float
    tags: list[str]


@dataclass(frozen=True)
class UserFeedback:
    """用户反馈。"""

    feedback_id: str
    input: Any
    expected: Any
    tags: list[str]
    source: str = "feedback"


def sample_logs(logs: Iterable[OnlineLog], rate: float, rng: Callable[[], float]) -> list[OnlineLog]:
    """按注入随机源抽样线上日志。"""
    raise NotImplementedError


def feedback_to_case(feedback: UserFeedback) -> EvalCase:
    """把用户反馈转换成新评测用例。"""
    raise NotImplementedError


def merge_feedback_cases(existing: list[EvalCase], feedback: Iterable[UserFeedback]) -> list[EvalCase]:
    """反馈入库前按内容指纹去重。"""
    raise NotImplementedError


def detect_metric_drift(values: Iterable[float], *, baseline: float, window: int, threshold: float) -> dict[str, Any]:
    """滑动窗口对比基线，检测指标漂移。"""
    raise NotImplementedError
