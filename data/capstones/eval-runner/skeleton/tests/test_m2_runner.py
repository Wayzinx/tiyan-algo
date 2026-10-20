import threading
import time
import json

import httpx

from evalrunner.agents import AgentResult, FakeAgent, HTTPAgent, PythonFunctionAgent, TraceEvent
from evalrunner.dataset import EvalCase
from evalrunner.runner import run_cases


def _case(case_id, case_input):
    return EvalCase(id=case_id, input=case_input, expected=case_input, scorers=[{"type": "exact"}], tags=["t"], difficulty="easy", source="test")


def test_m2_python_function_adapter_records_trace():
    """Python 函数适配器会返回统一输出和轨迹。"""
    agent = PythonFunctionAgent(lambda value: value.upper())
    result = agent.run("hi")
    assert result.output == "HI"
    assert result.trace[0].type == "message"
    assert result.tokens >= 1


def test_m2_http_adapter_uses_injected_transport():
    """HTTP 适配器可以使用注入的 MockTransport。"""
    def handler(request):
        payload = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"output": payload["input"] + "!", "trace": [{"type": "tool", "name": "search"}], "tokens": 3})

    agent = HTTPAgent("https://agent.local/run", transport=httpx.MockTransport(handler))
    result = agent.run("go")
    assert result.output == "go!"
    assert result.trace[0].name == "search"


def test_m2_runner_retries_and_repeats():
    """Runner 会按配置重试失败并重复运行用例。"""
    agent = FakeAgent({"x": "ok"}, failures={"x": 1})
    results = run_cases([_case("c1", "x")], agent, concurrency=1, retries=1, repeats=2)
    assert len(results) == 2
    assert results[0].ok is True and results[0].attempts == 2
    assert results[1].ok is True and results[1].repeat_index == 1


def test_m2_runner_limits_concurrency():
    """并发执行不会超过指定并发数。"""
    lock = threading.Lock()
    current = 0
    peak = 0

    def slow(value):
        nonlocal current, peak
        with lock:
            current += 1
            peak = max(peak, current)
        time.sleep(0.02)
        with lock:
            current -= 1
        return value

    cases = [_case(str(index), index) for index in range(6)]
    results = run_cases(cases, PythonFunctionAgent(slow), concurrency=2)
    assert all(item.ok for item in results)
    assert peak <= 2


def test_m2_timeout_is_captured_as_failed_result():
    """单用例超时会被记录为失败结果而不是中断整批任务。"""
    results = run_cases([_case("slow", "x")], PythonFunctionAgent(lambda value: time.sleep(0.05) or value), concurrency=1, timeout_s=0.001)
    assert results[0].ok is False
    assert "Timeout" in results[0].error


def test_m2_fake_agent_can_return_full_trace():
    """FakeAgent 支持返回包含工具调用的完整轨迹。"""
    result = AgentResult(output="done", trace=[TraceEvent(type="tool", name="calc", arguments={"x": 1}, tokens=2)], tokens=2)
    agent = FakeAgent({"q": result})
    assert agent.run("q").trace[0].arguments == {"x": 1}
