from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterator

PRICE_TABLE = {"fake": {"prompt": 0.0, "completion": 0.0}, "standard": {"prompt": 0.001, "completion": 0.002}}


def calculate_cost(model: str, usage: dict[str, int], price_table: dict[str, dict[str, float]] | None = None) -> float:
    """按单价表计算一次模型调用成本。"""
    raise NotImplementedError


class TraceWriter:
    """把 trace/span 事件以 JSONL 写出。"""

    def __init__(self, path: str | Path, *, clock: Callable[[], float] | None = None) -> None:
        """初始化写出路径和时钟。"""
        raise NotImplementedError

    def write(self, event: dict[str, Any]) -> None:
        """写入单条事件。"""
        raise NotImplementedError

    def span(self, name: str, **attrs: Any) -> Iterator[dict[str, Any]]:
        """记录一个带耗时和错误字段的 span。"""
        raise NotImplementedError


def read_events(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSONL trace 文件。"""
    raise NotImplementedError


class MetricsSummary:
    """根据事件汇总成功率、延迟分位和平均成本。"""

    def __init__(self) -> None:
        """初始化统计器。"""
        raise NotImplementedError

    def add_event(self, event: dict[str, Any]) -> None:
        """追加事件。"""
        raise NotImplementedError

    def summary(self) -> dict[str, float]:
        """计算汇总指标。"""
        raise NotImplementedError
