from pydantic import BaseModel

from agent_service.agent import AgentRunner
from agent_service.llm import FakeLLM
from agent_service.tools import ToolRegistry


def registry_with_math() -> ToolRegistry:
    registry = ToolRegistry()

    @registry.register(name="add")
    def add(a: int, b: int) -> int:
        return a + b

    @registry.register(name="fail")
    def fail() -> str:
        raise ValueError("boom")

    return registry


def test_agent_runs_multi_round_tool_call():
    """Agent 能把工具结果回填给模型并得到最终答案。"""
    llm = FakeLLM([{"tool_calls": [{"id": "c1", "name": "add", "arguments": {"a": 1, "b": 2}}]}, "答案是 3"])
    result = AgentRunner(llm, registry_with_math()).run("1+2")
    assert result.output == "答案是 3"
    assert result.stop_reason == "final"
    assert result.tool_results[0]["content"] == "3"


def test_agent_runs_parallel_tool_calls():
    """同一轮多个工具调用会全部执行并回填。"""
    llm = FakeLLM([{"tool_calls": [{"id": "c1", "name": "add", "arguments": {"a": 1, "b": 2}}, {"id": "c2", "name": "add", "arguments": {"a": 3, "b": 4}}]}, "done"])
    result = AgentRunner(llm, registry_with_math()).run("calc")
    assert [item["content"] for item in result.tool_results] == ["3", "7"]


def test_agent_feeds_tool_error_back_to_model():
    """工具失败不会中断主循环，而是以错误内容回填。"""
    llm = FakeLLM([{"tool_calls": [{"id": "c1", "name": "fail", "arguments": {}}]}, "已处理错误"])
    result = AgentRunner(llm, registry_with_math()).run("fail")
    assert result.tool_results[0]["ok"] is False
    assert "ERROR" in result.messages[-2]["content"]
    assert result.output == "已处理错误"


def test_structured_output_is_repaired_once():
    """结构化最终输出校验失败时会要求模型修正一次。"""
    class Answer(BaseModel):
        value: int

    llm = FakeLLM(["不是 json", '{"value": 42}'])
    result = AgentRunner(llm, registry_with_math(), output_model=Answer).run("structured")
    assert result.stop_reason == "final_repaired"
    assert result.output.value == 42


def test_stop_conditions_for_max_rounds_token_budget_and_repeated_call():
    """最大轮数、token 预算和重复工具调用都会给出 stop_reason。"""
    repeated_call = {"tool_calls": [{"id": "c1", "name": "add", "arguments": {"a": 1, "b": 1}}]}
    assert AgentRunner(FakeLLM([repeated_call, repeated_call]), registry_with_math(), max_rounds=5).run("x").stop_reason == "repeated_tool_call"
    assert AgentRunner(FakeLLM([repeated_call]), registry_with_math(), max_rounds=1).run("x").stop_reason == "max_rounds"
    assert AgentRunner(FakeLLM(["never"]), registry_with_math(), token_budget=1).run("很长很长很长很长的输入").stop_reason == "token_budget"
