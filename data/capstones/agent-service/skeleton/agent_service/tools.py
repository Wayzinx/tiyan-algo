from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

Permission = Literal["read", "write", "dangerous"]


class ToolError(RuntimeError):
    """工具执行错误基类。"""


class ToolValidationError(ToolError):
    """工具参数不符合签名或 JSON Schema。"""


class ToolPermissionError(ToolError):
    """危险工具未获得审批。"""


class ToolTimeoutError(ToolError):
    """工具执行超时。"""


def schema_from_signature(func: Callable[..., Any]) -> dict[str, Any]:
    """从函数签名生成对象形 JSON Schema。"""
    raise NotImplementedError


@dataclass
class ToolSpec:
    """工具注册后的元数据。"""

    name: str
    description: str
    schema: dict[str, Any]
    func: Callable[..., Any]
    permission: Permission = "read"
    timeout: float | None = None

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """校验并补齐默认参数。"""
        raise NotImplementedError


class ToolRegistry:
    """工具注册表，负责注册、Schema 导出、权限审批、超时和执行。"""

    def __init__(self) -> None:
        """初始化注册表。"""
        raise NotImplementedError

    def register(self, func: Callable[..., Any] | None = None, *, name: str | None = None, description: str | None = None, permission: Permission = "read", timeout: float | None = None) -> Callable[..., Any]:
        """注册工具；既可直接调用，也可作为装饰器。"""
        raise NotImplementedError

    def get(self, name: str) -> ToolSpec:
        """按名称取得工具。"""
        raise NotImplementedError

    def list_schemas(self) -> list[dict[str, Any]]:
        """导出 OpenAI tools 兼容的函数工具 schema。"""
        raise NotImplementedError

    def call(self, name: str, arguments: dict[str, Any], *, approval_callback: Callable[[ToolSpec, dict[str, Any]], bool] | None = None) -> Any:
        """执行工具并处理参数校验、危险审批和超时。"""
        raise NotImplementedError


def tool(*, name: str | None = None, description: str | None = None, permission: Permission = "read", timeout: float | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """给函数标记工具元数据，便于后续注册。"""
    raise NotImplementedError


def calculator(expression: str) -> float:
    """计算安全算术表达式。"""
    raise NotImplementedError


def make_document_search(documents: dict[str, str]) -> Callable[[str], str]:
    """创建可注入文档检索工具。"""
    raise NotImplementedError


def make_http_get(fetcher: Callable[[str], str]) -> Callable[[str], str]:
    """创建可注入 HTTP GET 工具，测试中可传入 MockTransport 或假函数。"""
    raise NotImplementedError


def default_registry() -> ToolRegistry:
    """返回包含计算器的默认工具注册表。"""
    raise NotImplementedError
