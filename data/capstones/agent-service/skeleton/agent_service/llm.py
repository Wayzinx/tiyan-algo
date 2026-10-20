from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """模型请求执行的工具调用。"""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """一次聊天补全响应。"""

    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMError(RuntimeError):
    """模型调用错误基类，携带是否可重试的分类。"""

    def __init__(self, message: str, *, retryable: bool, status_code: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class RetriableLLMError(LLMError):
    """网络错误或 5xx 等可重试模型错误。"""


class RateLimitError(RetriableLLMError):
    """429 限流错误。"""


class NonRetriableLLMError(LLMError):
    """参数错误、鉴权错误等不可重试模型错误。"""


def classify_http_error(status_code: int, body: str = "") -> LLMError:
    """按 HTTP 状态码分类模型错误。"""
    raise NotImplementedError


class OpenAIChatClient:
    """OpenAI 兼容的同步聊天客户端，支持流式、超时、重试和错误分类。"""

    def __init__(self, base_url: str, api_key: str | None = None, model: str = "gpt-compatible", timeout: float = 10.0, max_retries: int = 2, backoff_base: float = 0.1, client: httpx.Client | None = None, sleep: Callable[[float], None] | None = None) -> None:
        """初始化客户端依赖。"""
        raise NotImplementedError

    def chat(self, messages: Sequence[Mapping[str, Any]], *, tools: Sequence[Mapping[str, Any]] | None = None, stream: bool = False, timeout: float | None = None) -> ChatResponse | Iterator[str]:
        """发送聊天补全请求；stream=True 时返回文本增量迭代器。"""
        raise NotImplementedError


@dataclass
class FakeLLM:
    """可编程假模型，按脚本顺序返回文本或工具调用。"""

    script: list[Any]

    def chat(self, messages: Sequence[Mapping[str, Any]], *, tools: Sequence[Mapping[str, Any]] | None = None, stream: bool = False, timeout: float | None = None) -> ChatResponse | Iterator[str]:
        """返回下一条脚本响应。"""
        raise NotImplementedError
