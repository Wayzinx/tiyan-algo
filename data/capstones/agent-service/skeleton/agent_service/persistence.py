from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent import AgentResult, AgentRunner


class SQLiteStore:
    """SQLite 会话存储，保存步骤消息、工具结果和幂等记录。"""

    def __init__(self, path: str | Path) -> None:
        """打开数据库并初始化 schema。"""
        raise NotImplementedError

    def create_session(self, session_id: str) -> None:
        """创建或确认会话存在。"""
        raise NotImplementedError

    def save_step(self, session_id: str, step: int, message: dict[str, Any]) -> None:
        """保存指定步骤的消息。"""
        raise NotImplementedError

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        """读取会话已保存消息。"""
        raise NotImplementedError

    def save_tool_result(self, session_id: str, idempotency_key: str, result: Any) -> bool:
        """保存工具结果；若幂等键已存在则返回 False。"""
        raise NotImplementedError

    def get_tool_result(self, session_id: str, idempotency_key: str) -> Any | None:
        """按幂等键读取工具结果。"""
        raise NotImplementedError


def persist_result(store: SQLiteStore, session_id: str, result: AgentResult) -> None:
    """把 AgentResult 的消息轨迹写入 SQLite。"""
    raise NotImplementedError


def resume_and_run(store: SQLiteStore, session_id: str, runner: AgentRunner, new_user_input: str | None = None) -> AgentResult:
    """从最后保存的消息恢复，并可追加新用户输入继续运行。"""
    raise NotImplementedError
