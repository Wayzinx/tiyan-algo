from __future__ import annotations

from typing import Any, Mapping, Sequence, Type

from pydantic import BaseModel

from .tools import ToolRegistry


class AgentResult(BaseModel):
    """Agent 运行结果，包含输出、消息轨迹和停止原因。"""

    output: Any
    messages: list[dict[str, Any]]
    rounds: int
    stop_reason: str
    tool_results: list[dict[str, Any]] = []


def approximate_tokens(messages: Sequence[Mapping[str, Any]]) -> int:
    """用字符长度近似 token，用于预算保护。"""
    raise NotImplementedError


class AgentRunner:
    """支持多轮、并行工具调用、结构化输出修正和停止条件的 Agent 主循环。"""

    def __init__(self, llm: Any, tools: ToolRegistry | None = None, *, output_model: Type[BaseModel] | None = None, max_rounds: int = 5, token_budget: int = 4000, approval_callback: Any = None) -> None:
        """初始化 Agent 运行依赖。"""
        raise NotImplementedError

    def run(self, user_input: str | Sequence[Mapping[str, Any]]) -> AgentResult:
        """运行 Agent，直到最终回答或触发停止条件。"""
        raise NotImplementedError
