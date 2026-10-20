import json

import httpx
import pytest

from agent_service.config import load_settings
from agent_service.llm import FakeLLM, NonRetriableLLMError, OpenAIChatClient, RateLimitError, ToolCall


def test_fake_llm_returns_text_and_tool_calls():
    """FakeLLM 能按脚本返回文本和工具调用。"""
    llm = FakeLLM(["你好", {"tool_calls": [{"id": "c1", "name": "calculator", "arguments": {"expression": "1+2"}}]}])
    assert llm.chat([{"role": "user", "content": "hi"}]).content == "你好"
    second = llm.chat([{"role": "user", "content": "算"}])
    assert second.tool_calls == [ToolCall(id="c1", name="calculator", arguments={"expression": "1+2"})]


def test_openai_client_posts_compatible_payload_and_parses_response():
    """OpenAI 客户端发送兼容载荷并解析非流式响应。"""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 2, "completion_tokens": 1}})

    client = OpenAIChatClient("https://api.test/v1", api_key="k", model="m", client=httpx.Client(transport=httpx.MockTransport(handler)))
    response = client.chat([{"role": "user", "content": "hello"}])
    assert seen["payload"]["model"] == "m"
    assert response.content == "ok"
    assert response.usage["prompt_tokens"] == 2


def test_openai_client_streams_sse_chunks():
    """OpenAI 客户端能解析 SSE 文本增量。"""
    body = 'data: {"choices":[{"delta":{"content":"你"}}]}\n\ndata: {"choices":[{"delta":{"content":"好"}}]}\n\ndata: [DONE]\n\n'
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=body))
    client = OpenAIChatClient("https://api.test/v1", client=httpx.Client(transport=transport))
    assert "".join(client.chat([{"role": "user", "content": "hi"}], stream=True)) == "你好"


def test_retry_then_success_and_rate_limit_classification():
    """可重试错误会指数退避重试，429 会分类为限流。"""
    attempts = {"n": 0}
    sleeps = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(500, text="temporary")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = OpenAIChatClient("https://api.test/v1", client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=sleeps.append, backoff_base=0.01)
    assert client.chat([{"role": "user", "content": "x"}]).content == "ok"
    assert sleeps == [0.01]
    limited = OpenAIChatClient("https://api.test/v1", max_retries=0, client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429, text="slow"))))
    with pytest.raises(RateLimitError):
        limited.chat([{"role": "user", "content": "x"}])


def test_non_retriable_error_and_env_config():
    """不可重试错误立即抛出，配置可由环境变量覆盖。"""
    client = OpenAIChatClient("https://api.test/v1", max_retries=3, client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(400, text="bad"))))
    with pytest.raises(NonRetriableLLMError):
        client.chat([{"role": "user", "content": "x"}])
    settings = load_settings(env={"AGENT_MODEL": "demo", "AGENT_TIMEOUT_SECONDS": "3.5", "AGENT_API_KEYS": "a,b"})
    assert settings.model == "demo"
    assert settings.timeout_seconds == 3.5
    assert settings.api_keys == ["a", "b"]
