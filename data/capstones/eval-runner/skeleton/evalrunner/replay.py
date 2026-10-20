from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .agents import TraceEvent


class CassetteMissError(KeyError):
    """回放模式未命中请求指纹。"""


class Cassette:
    """按请求指纹录制和回放响应。"""

    def __init__(self, path: str | Path):
        """打开或初始化 cassette 文件。"""
        raise NotImplementedError

    def fingerprint(self, request: dict[str, Any]) -> str:
        """计算请求指纹。"""
        raise NotImplementedError

    def record(self, request: dict[str, Any], response: Any) -> str:
        """记录一次请求和响应。"""
        raise NotImplementedError

    def replay(self, request: dict[str, Any]) -> Any:
        """回放命中的响应，未命中时失败。"""
        raise NotImplementedError


def call_with_cassette(
    cassette: Cassette,
    request: dict[str, Any],
    sender: Callable[[dict[str, Any]], Any],
    *,
    mode: str = "record",
) -> Any:
    """在录制或回放模式下调用模型 / 工具。"""
    raise NotImplementedError


def classify_badcase(
    *,
    output: Any,
    error: str | None = None,
    trace: list[TraceEvent] | None = None,
    expected_format: str | None = None,
    classifier: Callable[..., str | None] | None = None,
) -> str:
    """按规则和可注入函数分类失败原因。"""
    raise NotImplementedError


def aggregate_badcases(categories: list[str]) -> dict[str, dict[str, float]]:
    """按 badcase 类别聚合数量和比例。"""
    raise NotImplementedError
