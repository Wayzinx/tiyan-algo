from __future__ import annotations

import time
from typing import Any, Callable

from fastapi import FastAPI
from pydantic import BaseModel

from .agent import AgentRunner


class ChatRequest(BaseModel):
    """聊天接口请求。"""

    message: str
    session_id: str | None = None


class TokenBucket:
    """可注入时钟的 API key 令牌桶限流器。"""

    def __init__(self, capacity: int, refill_per_second: float, *, clock: Callable[[], float] = time.time) -> None:
        """初始化令牌桶。"""
        raise NotImplementedError

    def allow(self, key: str) -> bool:
        """消费一个令牌，返回是否允许。"""
        raise NotImplementedError


class InMemorySessionStore:
    """服务层演示用内存会话存储。"""

    def __init__(self) -> None:
        """初始化内存会话表。"""
        raise NotImplementedError

    def save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """保存会话消息。"""
        raise NotImplementedError

    def get(self, session_id: str) -> list[dict[str, Any]] | None:
        """读取会话消息。"""
        raise NotImplementedError


def create_app(runner_factory: Callable[[], AgentRunner] | None = None, *, api_keys: set[str] | None = None, bucket: TokenBucket | None = None) -> FastAPI:
    """创建 FastAPI 应用，暴露聊天、流式聊天、会话、健康和指标接口。"""
    raise NotImplementedError


app = FastAPI(title="Agent Service Capstone Skeleton")
