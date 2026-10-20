from fastapi.testclient import TestClient

from agent_service.agent import AgentRunner
from agent_service.llm import FakeLLM
from agent_service.service import TokenBucket, create_app
from agent_service.tools import ToolRegistry


def make_client(clock=lambda: 0.0):
    app = create_app(lambda: AgentRunner(FakeLLM(["你好"]), ToolRegistry()), api_keys={"k"}, bucket=TokenBucket(1, 0.0, clock=clock))
    return TestClient(app)


def test_healthz_and_metrics_are_public():
    """健康检查和指标接口可读取服务状态。"""
    client = make_client()
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/metrics").json()["requests"] == 0


def test_chat_requires_api_key_and_returns_uniform_error():
    """聊天接口需要 API key，错误响应格式统一。"""
    client = make_client()
    response = client.post("/v1/chat", json={"message": "hi"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_chat_endpoint_returns_agent_result_and_session_readback():
    """POST /v1/chat 返回结果并能通过会话接口读回。"""
    client = make_client()
    response = client.post("/v1/chat", headers={"Authorization": "Bearer k"}, json={"message": "hi", "session_id": "s1"})
    assert response.json()["output"] == "你好"
    session = client.get("/v1/sessions/s1", headers={"Authorization": "Bearer k"})
    assert session.json()["messages"][0]["content"] == "hi"


def test_stream_endpoint_returns_sse():
    """POST /v1/chat/stream 返回 SSE 增量事件。"""
    client = make_client()
    response = client.post("/v1/chat/stream", headers={"Authorization": "Bearer k"}, json={"message": "hi"})
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "[DONE]" in response.text


def test_token_bucket_rate_limits_by_api_key():
    """令牌桶按 API key 限流并使用可注入时钟。"""
    client = make_client()
    assert client.post("/v1/chat", headers={"Authorization": "Bearer k"}, json={"message": "one"}).status_code == 200
    blocked = client.post("/v1/chat", headers={"Authorization": "Bearer k"}, json={"message": "two"})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
