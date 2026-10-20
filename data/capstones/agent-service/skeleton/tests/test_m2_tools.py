import time

import pytest

from agent_service.tools import ToolPermissionError, ToolRegistry, ToolTimeoutError, ToolValidationError, calculator, make_document_search, make_http_get, schema_from_signature


def test_schema_from_signature_marks_types_and_required():
    """函数签名能转换成包含类型和必填字段的 JSON Schema。"""
    def demo(name: str, count: int = 1, ok: bool = True) -> str:
        return name * count

    schema = schema_from_signature(demo)
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["required"] == ["name"]


def test_registry_decorator_validates_and_calls_tool():
    """工具注册装饰器能校验参数并执行函数。"""
    registry = ToolRegistry()

    @registry.register(description="加法")
    def add(a: int, b: int) -> int:
        return a + b

    assert registry.call("add", {"a": 2, "b": 3}) == 5
    with pytest.raises(ToolValidationError):
        registry.call("add", {"a": "2", "b": 3})


def test_dangerous_tool_requires_approval_callback():
    """dangerous 权限工具必须通过审批回调。"""
    registry = ToolRegistry()

    @registry.register(permission="dangerous")
    def delete(path: str) -> str:
        return f"deleted {path}"

    with pytest.raises(ToolPermissionError):
        registry.call("delete", {"path": "/tmp/a"})
    assert registry.call("delete", {"path": "/tmp/a"}, approval_callback=lambda spec, args: args["path"].startswith("/tmp")) == "deleted /tmp/a"


def test_tool_timeout_is_enforced():
    """工具执行超过配置超时时会抛出 ToolTimeoutError。"""
    registry = ToolRegistry()

    @registry.register(timeout=0.01)
    def slow() -> str:
        time.sleep(0.05)
        return "done"

    with pytest.raises(ToolTimeoutError):
        registry.call("slow", {})


def test_builtin_calculator_document_search_and_http_get():
    """内置计算器、文档检索和可注入 HTTP GET 都可离线运行。"""
    assert calculator("2 + 3 * 4") == 14
    search = make_document_search({"a": "Agent uses tools", "b": "RAG retrieves markdown"})
    assert "RAG" in search("markdown")
    http_get = make_http_get(lambda url: f"body:{url}")
    assert http_get("https://example.test") == "body:https://example.test"
