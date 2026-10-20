from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .agents import AgentAdapter
from .dataset import EvalCase


class CaseTimeoutError(TimeoutError):
    """单用例执行超时。"""


@dataclass
class CaseRunResult:
    """单条用例一次执行的结果。"""

    case_id: str
    repeat_index: int
    ok: bool
    output: Any = None
    trace: list[Any] = field(default_factory=list)
    elapsed_ms: float = 0.0
    tokens: int = 0
    attempts: int = 1
    error: str | None = None


def run_cases(
    cases: Iterable[EvalCase],
    agent: AgentAdapter,
    *,
    concurrency: int = 4,
    timeout_s: float = 5.0,
    retries: int = 0,
    repeats: int = 1,
) -> list[CaseRunResult]:
    """并发执行用例，支持超时、重试和重复运行。"""
    raise NotImplementedError
