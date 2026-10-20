from agent_service.agent import AgentRunner
from agent_service.llm import FakeLLM
from agent_service.persistence import SQLiteStore, persist_result, resume_and_run
from agent_service.tools import ToolRegistry


def test_sqlite_store_saves_and_loads_messages(tmp_path):
    """SQLite 能按步骤保存并按顺序读取消息。"""
    store = SQLiteStore(tmp_path / "agent.db")
    store.save_step("s1", 0, {"role": "user", "content": "hi"})
    store.save_step("s1", 1, {"role": "assistant", "content": "ok"})
    assert [msg["content"] for msg in store.load_messages("s1")] == ["hi", "ok"]


def test_persist_result_writes_full_trace(tmp_path):
    """AgentResult 的完整消息轨迹能持久化。"""
    result = AgentRunner(FakeLLM(["hello"]), ToolRegistry()).run("hi")
    store = SQLiteStore(tmp_path / "agent.db")
    persist_result(store, "s1", result)
    assert len(store.load_messages("s1")) == 2


def test_resume_and_run_continues_from_last_step(tmp_path):
    """进程中断后能从最后一步消息继续运行。"""
    store = SQLiteStore(tmp_path / "agent.db")
    store.save_step("s1", 0, {"role": "user", "content": "之前"})
    result = resume_and_run(store, "s1", AgentRunner(FakeLLM(["继续完成"]), ToolRegistry()), "现在")
    assert result.output == "继续完成"
    assert store.load_messages("s1")[-1]["content"] == "继续完成"


def test_tool_result_idempotency_key_prevents_duplicate_side_effect(tmp_path):
    """工具调用幂等键能避免重复保存有副作用结果。"""
    store = SQLiteStore(tmp_path / "agent.db")
    assert store.save_tool_result("s1", "tool:abc", {"ok": True}) is True
    assert store.save_tool_result("s1", "tool:abc", {"ok": False}) is False
    assert store.get_tool_result("s1", "tool:abc") == {"ok": True}


def test_store_survives_reopen(tmp_path):
    """关闭后重新打开数据库仍能读取历史会话。"""
    path = tmp_path / "agent.db"
    SQLiteStore(path).save_step("s1", 0, {"role": "user", "content": "persist"})
    assert SQLiteStore(path).load_messages("s1")[0]["content"] == "persist"
