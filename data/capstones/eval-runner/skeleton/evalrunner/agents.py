from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import httpx


@dataclass
class TraceEvent:
    """一次消息或工具调用轨迹。"""

    type: str
    name: str | None = None
    content: Any | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    tokens: int = 0


@dataclass
class AgentResult:
    """被测 Agent 的输出和完整轨迹。"""

    output: Any
    trace: list[TraceEvent] = field(default_factory=list)
    elapsed_ms: float = 0.0
    tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class AgentAdapter(Protocol):
    """被测 Agent 适配器协议。"""

    def run(self, case_input: Any) -> AgentResult:
        """执行单条输入并返回标准结果。"""


class PythonFunctionAgent:
    """把 Python 函数包装成 Agent。"""

    def __init__(self, func: Callable[[Any], Any], clock: Callable[[], float] | None = None):
        """保存被测函数和可注入时钟。"""
        raise NotImplementedError

    def run(self, case_input: Any) -> AgentResult:
        """执行 Python 函数并标准化输出。"""
        raise NotImplementedError


class HTTPAgent:
    """通过 HTTP POST 调用 Agent，支持注入 httpx transport。"""

    def __init__(self, url: str, timeout: float = 5.0, transport: httpx.BaseTransport | None = None):
        """保存 URL、超时和可注入 transport。"""
        raise NotImplementedError

    def run(self, case_input: Any) -> AgentResult:
        """发起请求并转换为 AgentResult。"""
        raise NotImplementedError


class FakeAgent:
    """可编程假 Agent，测试时避免真实模型和网络。"""

    def __init__(self, responses: dict[Any, Any] | Callable[[Any], Any], failures: dict[Any, int] | None = None):
        """保存响应表和故障注入配置。"""
        raise NotImplementedError

    def run(self, case_input: Any) -> AgentResult:
        """返回预设响应或抛出预设错误。"""
        raise NotImplementedError
