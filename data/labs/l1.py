LABS = [
    dict(
        id="lab-tool-loop",
        course="agent",
        title="实现支持工具调用的 Agent 主循环",
        level="medium",
        desc='''### 背景
真实 Agent 不只是把用户消息发给模型，还要识别模型提出的工具调用，执行本地函数，再把结果回填给模型继续推理。面试官通常会借这题考察你是否理解 tool calling 的状态机：多工具调用、异常回填、未知工具、最大轮数保护，以及消息历史不能被随意破坏。
### 要实现什么
实现 `run_agent(llm, tools, messages, max_turns)`。`llm(history)` 是注入函数，返回普通字符串表示最终回答，或返回字典 `{"content": str, "tool_calls": [...]}`。每个 tool call 至少包含 `id`、`name`、`arguments`，其中 `arguments` 可以是字典或 JSON 字符串。`tools` 是 `name -> callable` 的字典。每轮先调用模型；如果没有工具调用，返回 `{"status": "final", "content": ..., "messages": history}`；如果有工具调用，要按顺序执行全部工具，并追加 `role="tool"` 的消息。工具抛异常或工具不存在时，也要把错误文本作为工具结果回填，不能直接中断。达到 `max_turns` 仍未得到最终回答时，返回 `status="max_turns"` 和明确原因。
### 例子
模型先请求 `add({"a":2,"b":3})`，工具返回 `5`，下一轮模型回答 `done`，函数应返回最终内容 `done`，历史中包含一次 assistant tool_calls 和一次 tool 结果。
### 约束
只能使用标准库；不要联网、不要 sleep；不要修改传入的 `messages` 列表；工具返回非字符串时要转成可读文本。''',
        starter='''def run_agent(llm, tools, messages, max_turns):
    """Run an LLM/tool loop until final text or max_turns."""
    raise NotImplementedError
''',
        tests='''def test_returns_plain_text_without_tools():
    """模型直接返回文本时，应立即结束并保留原始输入不变。"""
    original = [{"role": "user", "content": "hi"}]
    result = run_agent(lambda history: "hello", {}, original, max_turns=3)
    assert result["status"] == "final", result
    assert result["content"] == "hello", result
    assert original == [{"role": "user", "content": "hi"}], "不能原地修改输入消息"


def test_executes_multiple_tool_calls_before_next_llm_turn():
    """同一轮里的多个工具调用必须全部按顺序执行并回填。"""
    calls = []
    def llm(history):
        calls.append([m["role"] for m in history])
        if len(calls) == 1:
            return {"content": "need tools", "tool_calls": [
                {"id": "c1", "name": "add", "arguments": {"a": 2, "b": 3}},
                {"id": "c2", "name": "upper", "arguments": {"text": "ok"}},
            ]}
        assert history[-2]["content"] == "5", history
        assert history[-1]["content"] == "OK", history
        return "done"
    tools = {"add": lambda a, b: a + b, "upper": lambda text: text.upper()}
    result = run_agent(llm, tools, [{"role": "user", "content": "calc"}], 5)
    assert result["status"] == "final" and result["content"] == "done", result
    assert [m["role"] for m in result["messages"]].count("tool") == 2, result["messages"]


def test_tool_exception_is_sent_back_to_model():
    """工具抛异常时不能崩溃，要把错误作为 tool 消息交还模型。"""
    def bad(x):
        raise ValueError("boom")
    def llm(history):
        if not any(m.get("role") == "tool" for m in history):
            return {"tool_calls": [{"id": "t1", "name": "bad", "arguments": {"x": 1}}]}
        last = history[-1]
        assert last["tool_call_id"] == "t1", last
        assert "ValueError" in last["content"] and "boom" in last["content"], last
        return "handled"
    result = run_agent(llm, {"bad": bad}, [], 3)
    assert result["content"] == "handled", result


def test_max_turns_returns_clear_stop_reason():
    """一直请求工具时，达到最大轮数要返回 max_turns 而不是死循环。"""
    def llm(history):
        return {"tool_calls": [{"id": "x", "name": "noop", "arguments": {}}]}
    result = run_agent(llm, {"noop": lambda: "ok"}, [], max_turns=2)
    assert result["status"] == "max_turns", result
    assert "max" in result["content"].lower(), result
''',
        hidden='''def test_unknown_tool_is_reported_as_tool_result():
    """未知工具也要变成可被模型观察到的错误结果。"""
    def llm(history):
        if not history or history[-1].get("role") != "tool":
            return {"tool_calls": [{"id": "u1", "name": "missing", "arguments": {}}]}
        assert "unknown" in history[-1]["content"].lower() or "not found" in history[-1]["content"].lower(), history[-1]
        return "ok"
    result = run_agent(llm, {}, [], 3)
    assert result["status"] == "final" and result["content"] == "ok", result


def test_json_string_arguments_are_supported():
    """arguments 是 JSON 字符串时，也要解析后传给工具函数。"""
    def llm(history):
        if not any(m.get("role") == "tool" for m in history):
            return {"tool_calls": [{"id": "j1", "name": "join", "arguments": "{\\\"a\\\": \\\"x\\\", \\\"b\\\": \\\"y\\\"}"}]}
        assert history[-1]["content"] == "xy", history[-1]
        return "done"
    result = run_agent(llm, {"join": lambda a, b: a + b}, [], 3)
    assert result["content"] == "done", result
''',
        solution='''import json


def run_agent(llm, tools, messages, max_turns):
    """Run an LLM/tool loop until final text or max_turns."""
    history = [dict(m) for m in messages]
    for _ in range(max_turns):
        response = llm([dict(m) for m in history])
        if isinstance(response, str):
            history.append({"role": "assistant", "content": response})
            return {"status": "final", "content": response, "messages": history}

        content = response.get("content", "") if isinstance(response, dict) else str(response)
        tool_calls = response.get("tool_calls") or [] if isinstance(response, dict) else []
        if not tool_calls:
            history.append({"role": "assistant", "content": content})
            return {"status": "final", "content": content, "messages": history}

        assistant_msg = {"role": "assistant", "content": content, "tool_calls": tool_calls}
        history.append(assistant_msg)
        for call in tool_calls:
            call_id = call.get("id", "")
            name = call.get("name", "")
            args = call.get("arguments", {})
            try:
                if isinstance(args, str):
                    args = json.loads(args or "{}")
                if not isinstance(args, dict):
                    raise TypeError("tool arguments must be an object")
                if name not in tools:
                    raise KeyError(f"unknown tool: {name}")
                value = tools[name](**args)
                text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            except Exception as exc:
                text = f"ERROR: {type(exc).__name__}: {exc}"
            history.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": text})
    return {"status": "max_turns", "content": f"stopped after max_turns={max_turns}", "messages": history}
''',
        hints=["把模型返回分成 final 与 tool_calls 两条路径处理。", "每轮追加 assistant 消息，再顺序追加每个 tool 结果消息。", "工具异常和未知工具都应回填给模型，而不是让主循环抛出。"],
        points=["Agent 工具调用状态机", "依赖注入与可测试设计", "异常隔离和停止条件"],
        numpy=False,
    ),
    dict(
        id="lab-tool-schema",
        course="dev",
        title="从函数签名生成工具 JSON Schema 并校验参数",
        level="hard",
        desc='''### 背景
把普通 Python 函数暴露给大模型作为工具时，通常需要把函数签名转成 JSON Schema，再在真正调用前校验模型给出的参数。面试会关注你是否熟悉 `inspect`、类型注解、默认值、`Optional`、`Literal`，以及运行时校验和 schema 生成之间的一致性。
### 要实现什么
实现 `function_to_schema(fn)` 和 `validate_args(schema, args)`。前者读取函数参数，生成对象 schema：顶层包含 `type="object"`、`properties`、`required`。支持 `int/float/str/bool/list[T]/Optional[T]/Literal[...]`；有默认值的参数写入 `default`，且不进入 required；`Optional[T]` 允许 `null`，也不进入 required。后者接收 schema 和参数字典，返回错误字符串列表；没有错误返回空列表。需要检查缺失必填、未知参数、基础类型、数组元素和枚举值。
### 例子
`def search(q: str, top_k: int = 5)` 应生成 `q` 必填、`top_k` 有默认值的 schema；`validate_args(schema, {"q":"a"})` 返回 `[]`，而 `{}` 应报告缺少 `q`。
### 约束
只能使用标准库；错误信息不要求完全一致，但必须包含能定位问题的参数名；不要调用被分析的函数。''',
        starter='''def function_to_schema(fn):
    """Build a JSON-schema-like parameter schema from a Python function."""
    raise NotImplementedError


def validate_args(schema, args):
    """Return a list of validation error messages for args."""
    raise NotImplementedError
''',
        tests='''def test_required_and_default_parameters():
    """普通注解、必填字段和默认值应被正确提取。"""
    def search(q: str, top_k: int = 5):
        return q, top_k
    schema = function_to_schema(search)
    assert schema["type"] == "object", schema
    assert schema["required"] == ["q"], schema
    assert schema["properties"]["q"]["type"] == "string", schema
    assert schema["properties"]["top_k"]["default"] == 5, schema
    assert validate_args(schema, {"q": "python"}) == [], "有默认值的参数不应必填"


def test_optional_literal_and_list_validation():
    """Optional、Literal 和 list 元素类型都要参与校验。"""
    from typing import Literal, Optional
    def tool(tags: list[str], mode: Literal["fast", "safe"], limit: Optional[int] = None):
        return None
    schema = function_to_schema(tool)
    assert set(schema["required"]) == {"tags", "mode"}, schema
    assert validate_args(schema, {"tags": ["a", "b"], "mode": "fast", "limit": None}) == []
    errors = validate_args(schema, {"tags": ["a", 1], "mode": "bad"})
    joined = "\\n".join(errors)
    assert "tags" in joined and "mode" in joined, errors


def test_bool_is_not_accepted_as_integer():
    """Python 里 bool 是 int 子类，但参数校验中二者必须区分。"""
    def fn(count: int, flag: bool):
        return None
    schema = function_to_schema(fn)
    assert validate_args(schema, {"count": 3, "flag": False}) == []
    errors = validate_args(schema, {"count": True, "flag": 1})
    assert len(errors) == 2, errors


def test_unknown_and_missing_fields_report_errors():
    """未知字段和缺少必填字段都要返回可读错误。"""
    def fn(name: str):
        return name
    schema = function_to_schema(fn)
    errors = validate_args(schema, {"extra": 1})
    text = "\\n".join(errors)
    assert "name" in text and "extra" in text, errors
''',
        hidden='''def test_float_accepts_int_but_not_bool():
    """number 类型可以接受 int，但不能把 bool 当作数字。"""
    def fn(score: float):
        return score
    schema = function_to_schema(fn)
    assert validate_args(schema, {"score": 3}) == []
    assert validate_args(schema, {"score": 3.5}) == []
    assert validate_args(schema, {"score": True}), "bool 不应通过 number 校验"


def test_unannotated_parameter_allows_any_value():
    """没有注解的参数应生成宽松 schema，但仍然保留必填关系。"""
    def fn(payload, retry: int = 1):
        return payload
    schema = function_to_schema(fn)
    assert schema["properties"]["payload"] == {}, schema
    assert schema["required"] == ["payload"], schema
    assert validate_args(schema, {"payload": {"x": object()}}) == []
''',
        solution='''import inspect
import types
from typing import Any, Literal, Union, get_args, get_origin


def _is_optional(annotation):
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        return type(None) in get_args(annotation)
    return False


def _schema_for(annotation):
    if annotation is inspect._empty or annotation is Any:
        return {}
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        return {"enum": list(args)}
    if origin in (Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(non_none) != len(args):
            inner = _schema_for(non_none[0])
            typ = inner.get("type")
            if isinstance(typ, list):
                inner["type"] = typ + ["null"]
            elif typ:
                inner["type"] = [typ, "null"]
            else:
                inner["nullable"] = True
            return inner
        return {}
    if origin is list or origin is __import__("typing").List:
        return {"type": "array", "items": _schema_for(args[0]) if args else {}}
    mapping = {int: "integer", float: "number", str: "string", bool: "boolean"}
    if annotation in mapping:
        return {"type": mapping[annotation]}
    return {}


def function_to_schema(fn):
    """Build a JSON-schema-like parameter schema from a Python function."""
    sig = inspect.signature(fn)
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        prop = _schema_for(param.annotation)
        if param.default is not inspect._empty:
            prop = dict(prop)
            prop["default"] = param.default
        properties[name] = prop
        if param.default is inspect._empty and not _is_optional(param.annotation):
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}


def _matches(schema, value):
    if "enum" in schema and value not in schema["enum"]:
        return False
    typ = schema.get("type")
    allowed = typ if isinstance(typ, list) else [typ] if typ else []
    if value is None:
        return "null" in allowed or schema.get("nullable") is True or not allowed
    if "integer" in allowed and not (isinstance(value, int) and not isinstance(value, bool)):
        if len(allowed) == 1:
            return False
    if "number" in allowed and not ((isinstance(value, (int, float)) and not isinstance(value, bool))):
        if len(allowed) == 1:
            return False
    checks = {
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "array": lambda v: isinstance(v, list),
    }
    for name, check in checks.items():
        if name in allowed and not check(value) and len(allowed) == 1:
            return False
    if "array" in allowed and isinstance(value, list):
        item_schema = schema.get("items", {})
        return all(_matches(item_schema, item) for item in value)
    return True


def validate_args(schema, args):
    """Return a list of validation error messages for args."""
    props = schema.get("properties", {})
    errors = []
    for name in schema.get("required", []):
        if name not in args:
            errors.append(f"missing required parameter: {name}")
    for name in args:
        if name not in props:
            errors.append(f"unknown parameter: {name}")
    for name, value in args.items():
        if name in props and not _matches(props[name], value):
            errors.append(f"invalid value for {name}")
    return errors
''',
        hints=["先用 inspect.signature 拿到参数、默认值和注解。", "把 Optional 看作 Union[T, None]，把 Literal 看作 enum。", "校验时要递归检查 list 元素，并特别区分 bool 与 int。"],
        points=["Python 反射与类型注解", "JSON Schema 建模", "运行时参数校验边界"],
        numpy=False,
    ),
    dict(
        id="lab-json-repair",
        course="dev",
        title="提取并修复模型输出中的 JSON",
        level="medium",
        desc='''### 背景
大模型经常说“下面是 JSON”，然后返回 Markdown 代码块、前后解释文字、尾逗号，甚至偶尔把字符串写成单引号。工程里不能把这些文本直接 `json.loads`，也不能无限宽容到吞掉截断数据。面试官会用这题考察你对解析边界、错误分类和安全修复的把握。
### 要实现什么
实现 `parse_model_json(text)`，并定义异常 `JSONRepairError`。函数需要从模型输出中提取第一个 JSON 对象或数组：要去掉 ```json 代码块包裹和前后废话；要修复对象或数组末尾的尾逗号；当 JSON 使用单引号表示字符串时，可以修复为 Python 字面量再解析；如果括号没有闭合，必须抛出 `JSONRepairError` 且原因包含截断或未闭合含义；没有发现 JSON 或修复后仍无效也要抛出带原因的异常。
### 例子
输入 `Here is: ```json\n{"a":1,}\n``` ` 返回 `{"a": 1}`；输入 `{"a": [1, 2]` 应抛出截断错误。
### 约束
只能使用标准库；不要用 `eval`；返回值只能是 dict 或 list；修复应保守，不能把完全无关的文本伪造成 JSON。''',
        starter='''class JSONRepairError(ValueError):
    """Raised when model output cannot be repaired into JSON."""


def parse_model_json(text):
    """Extract and repair a JSON object or array from model text."""
    raise NotImplementedError
''',
        tests='''def test_extracts_json_from_markdown_fence():
    """应能从 markdown json 代码块中提取对象。"""
    text = '解释文字\\n```json\\n{"a": 1, "b": [2]}\\n```\\n结尾'
    assert parse_model_json(text) == {"a": 1, "b": [2]}


def test_repairs_trailing_commas():
    """对象和数组末尾的尾逗号应被移除。"""
    got = parse_model_json('prefix {"a": [1, 2,], "b": true,} suffix')
    assert got == {"a": [1, 2], "b": True}, got


def test_accepts_single_quoted_json_like_output():
    """常见的单引号字典输出可以被保守修复。"""
    got = parse_model_json("result: {'name': 'Ada', 'scores': [1, 2]}")
    assert got == {"name": "Ada", "scores": [1, 2]}, got


def test_truncated_json_raises_reasoned_error():
    """括号未闭合时必须报截断，不能静默补全。"""
    try:
        parse_model_json('{"a": [1, 2]')
    except JSONRepairError as exc:
        assert "截断" in str(exc) or "truncated" in str(exc).lower() or "未闭合" in str(exc), exc
    else:
        assert False, "截断 JSON 应抛出 JSONRepairError"
''',
        hidden='''def test_extracts_array_with_leading_and_trailing_text():
    """不仅对象，数组也要能从前后废话中提取。"""
    assert parse_model_json("答案是： [1, {'x': 2},] 谢谢") == [1, {"x": 2}]


def test_no_json_raises_error():
    """完全没有对象或数组时要明确失败。"""
    try:
        parse_model_json("there is no structured value here")
    except JSONRepairError as exc:
        assert "json" in str(exc).lower() or "没有" in str(exc), exc
    else:
        assert False, "没有 JSON 时不应返回成功"
''',
        solution='''import ast
import json
import re


class JSONRepairError(ValueError):
    """Raised when model output cannot be repaired into JSON."""


def _inside_fence(text):
    match = re.search(r"```(?:json)?\\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else text


def _extract(text):
    text = _inside_fence(text.strip())
    start_positions = [pos for pos in (text.find("{"), text.find("[")) if pos != -1]
    if not start_positions:
        raise JSONRepairError("没有找到 JSON 对象或数组")
    start = min(start_positions)
    opening = text[start]
    pairs = {"{": "}", "[": "]"}
    stack = [pairs[opening]]
    in_string = False
    quote = ""
    escaped = False
    for i in range(start + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\\\":
                escaped = True
            elif ch == quote:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            quote = ch
        elif ch in pairs:
            stack.append(pairs[ch])
        elif stack and ch == stack[-1]:
            stack.pop()
            if not stack:
                return text[start:i + 1]
    raise JSONRepairError("JSON 可能被截断或括号未闭合")


def parse_model_json(text):
    """Extract and repair a JSON object or array from model text."""
    candidate = _extract(text)
    repaired = re.sub(r",\\s*([}\\]])", r"\\1", candidate)
    try:
        value = json.loads(repaired)
    except json.JSONDecodeError as first_error:
        try:
            value = ast.literal_eval(repaired)
        except Exception as second_error:
            raise JSONRepairError(f"无法解析 JSON: {first_error}; {second_error}") from second_error
    if not isinstance(value, (dict, list)):
        raise JSONRepairError("JSON 顶层必须是对象或数组")
    return value
''',
        hints=["先定位第一个 `{` 或 `[`，再用栈找到匹配的结束位置。", "修复尾逗号可以用正则替换逗号后紧跟 `}` 或 `]` 的情况。", "单引号只能用 ast.literal_eval 这类安全解析，不能用 eval。"],
        points=["模型输出清洗", "保守 JSON 修复", "解析错误分类"],
        numpy=False,
    ),
    dict(
        id="lab-retry-backoff",
        course="dev",
        title="实现带全抖动和 Retry-After 的重试函数",
        level="medium",
        desc='''### 背景
AI 应用经常调用外部模型、向量库或检索服务，短暂限流和网络抖动很常见。可靠的客户端不会立刻重试打爆服务，而会用指数退避和抖动；同时也不能吞掉不可重试的业务错误。面试官会看你是否能把时间、随机数、sleep 都注入，写出确定性测试。
### 要实现什么
实现 `retry(fn, retries, base, max_delay, sleep, rng, retry_on)`。调用 `fn()`，成功则返回结果；失败时先用 `retry_on(exc)` 判断是否可重试，不可重试立即抛出原异常。最多重试 `retries` 次，因此总尝试次数为 `retries + 1`。普通退避延迟为 `min(max_delay, base * 2**failure_index)`，其中第一次失败的 `failure_index` 为 0；实际 sleep 使用全抖动 `rng.uniform(0, delay)`。如果异常对象有正数属性 `retry_after`，则本次直接 sleep `min(max_delay, retry_after)`，不再抖动。重试耗尽后抛出最后一次异常。
### 例子
前两次抛出可重试异常、第三次返回 `ok`，`retries=3` 时最终返回 `ok`，并调用两次注入的 `sleep`。
### 约束
只能用标准库；不要真的 sleep；不要创建真实随机数；保持异常类型和 traceback 尽量自然。''',
        starter='''def retry(fn, retries, base, max_delay, sleep, rng, retry_on):
    """Call fn with exponential backoff, full jitter, and Retry-After support."""
    raise NotImplementedError
''',
        tests='''def test_retries_with_exponential_full_jitter():
    """可重试异常应按指数退避并使用 rng.uniform 做全抖动。"""
    attempts = {"n": 0}
    sleeps = []
    class HalfRng:
        def uniform(self, low, high):
            assert low == 0
            return high / 2
    def fn():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("temporary")
        return "ok"
    got = retry(fn, retries=3, base=2, max_delay=10, sleep=sleeps.append, rng=HalfRng(), retry_on=lambda e: isinstance(e, TimeoutError))
    assert got == "ok"
    assert attempts["n"] == 3, attempts
    assert sleeps == [1, 2], sleeps


def test_non_retryable_exception_is_raised_immediately():
    """retry_on 返回 False 时不能 sleep，也不能再次调用 fn。"""
    calls = []
    try:
        retry(lambda: (_ for _ in ()).throw(ValueError("bad request")), 5, 1, 10, calls.append, None, lambda e: False)
    except ValueError as exc:
        assert "bad request" in str(exc)
    else:
        assert False, "不可重试异常应直接抛出"
    assert calls == [], calls


def test_exhausted_retries_raise_last_exception():
    """重试次数耗尽后，应抛出最后一次异常。"""
    count = {"n": 0}
    def fn():
        count["n"] += 1
        raise TimeoutError(f"try {count['n']}")
    try:
        retry(fn, retries=2, base=1, max_delay=10, sleep=lambda x: None, rng=type("R", (), {"uniform": lambda self, a, b: 0})(), retry_on=lambda e: True)
    except TimeoutError as exc:
        assert "try 3" in str(exc), exc
    else:
        assert False, "耗尽后应抛出最后一次异常"


def test_retry_after_takes_precedence_over_jitter():
    """异常带 retry_after 时，应尊重服务端提示并受 max_delay 限制。"""
    sleeps = []
    class RateLimited(Exception):
        retry_after = 7
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RateLimited("slow down")
        return "ok"
    got = retry(fn, 2, 1, 5, sleeps.append, type("R", (), {"uniform": lambda self, a, b: 999})(), lambda e: True)
    assert got == "ok"
    assert sleeps == [5], sleeps
''',
        hidden='''def test_max_delay_caps_exponential_backoff():
    """指数退避不能超过 max_delay。"""
    sleeps = []
    attempts = {"n": 0}
    def fn():
        attempts["n"] += 1
        if attempts["n"] < 4:
            raise TimeoutError("x")
        return 42
    rng = type("R", (), {"uniform": lambda self, a, b: b})()
    assert retry(fn, 3, base=3, max_delay=5, sleep=sleeps.append, rng=rng, retry_on=lambda e: True) == 42
    assert sleeps == [3, 5, 5], sleeps


def test_zero_retries_means_single_attempt():
    """retries=0 时只尝试一次，失败立刻抛出。"""
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        raise RuntimeError("once")
    try:
        retry(fn, 0, 1, 10, lambda x: None, type("R", (), {"uniform": lambda self, a, b: 0})(), lambda e: True)
    except RuntimeError:
        pass
    else:
        assert False, "没有重试额度时应抛出"
    assert calls["n"] == 1, calls
''',
        solution='''def retry(fn, retries, base, max_delay, sleep, rng, retry_on):
    """Call fn with exponential backoff, full jitter, and Retry-After support."""
    failures = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            if not retry_on(exc) or failures >= retries:
                raise
            retry_after = getattr(exc, "retry_after", None)
            if isinstance(retry_after, (int, float)) and retry_after > 0:
                delay = min(max_delay, retry_after)
            else:
                cap = min(max_delay, base * (2 ** failures))
                delay = rng.uniform(0, cap)
            sleep(delay)
            failures += 1
''',
        hints=["总尝试次数等于首次调用加 retries 次重试。", "全抖动不是固定 sleep 上限，而是在 `[0, 上限]` 之间取随机值。", "Retry-After 是服务端明确指令，应优先于本地抖动策略。"],
        points=["可靠调用与退避策略", "异常分类", "可测试的时间和随机数注入"],
        numpy=False,
    ),
    dict(
        id="lab-rate-limiter",
        course="arch",
        title="实现可注入时钟的令牌桶限流器",
        level="medium",
        desc='''### 背景
Agent 平台常要同时保护模型 API、工具服务和内部队列。令牌桶是最常见的本地限流算法：它允许短暂突发，但长期速率受控。面试官会借这题考察你是否能把时间作为依赖注入，正确处理补充令牌、容量上限和等待时间估算。
### 要实现什么
实现类 `TokenBucket(rate, capacity, clock)`。`rate` 表示每秒补充多少令牌，`capacity` 表示桶容量，`clock()` 返回当前秒数。初始化时桶是满的。方法 `try_acquire(n=1)`：先根据当前时间补充令牌；如果令牌足够则扣减并返回 `True`，否则不扣减并返回 `False`。方法 `wait_time(n=1)`：先补充令牌，返回距离可获取 `n` 个令牌还需等待的秒数；如果当前已足够返回 `0`；如果 `n > capacity` 返回 `float("inf")`。`n <= 0` 应抛出 `ValueError`。
### 例子
容量 5、速率 2/s，初始获取 5 个成功；马上再获取 1 个失败；时钟推进 0.5 秒后等待 1 个令牌的时间为 0，且可获取 1 个。
### 约束
只能使用标准库；不要读取真实时间；浮点误差允许很小范围。''',
        starter='''class TokenBucket:
    """Token bucket rate limiter with an injected clock."""
    def __init__(self, rate, capacity, clock):
        raise NotImplementedError

    def try_acquire(self, n=1):
        raise NotImplementedError

    def wait_time(self, n=1):
        raise NotImplementedError
''',
        tests='''def test_initial_capacity_and_basic_acquire():
    """初始化时桶应是满的，扣完后不能继续获取。"""
    now = {"t": 0.0}
    bucket = TokenBucket(rate=2, capacity=5, clock=lambda: now["t"])
    assert bucket.try_acquire(5) is True
    assert bucket.try_acquire(1) is False


def test_refill_uses_injected_clock():
    """时间推进后应按 rate 补充令牌。"""
    now = {"t": 10.0}
    bucket = TokenBucket(rate=2, capacity=5, clock=lambda: now["t"])
    assert bucket.try_acquire(5)
    now["t"] = 10.5
    assert bucket.wait_time(1) == 0
    assert bucket.try_acquire(1) is True
    assert bucket.try_acquire(1) is False


def test_wait_time_reports_needed_seconds_without_consuming():
    """wait_time 只估算等待时间，不应消耗令牌。"""
    now = {"t": 0.0}
    bucket = TokenBucket(rate=4, capacity=4, clock=lambda: now["t"])
    assert bucket.try_acquire(3)
    assert bucket.wait_time(3) == 0.5
    now["t"] = 0.5
    assert bucket.try_acquire(3) is True


def test_refill_never_exceeds_capacity():
    """长时间空闲后令牌数也不能超过容量。"""
    now = {"t": 0.0}
    bucket = TokenBucket(rate=10, capacity=3, clock=lambda: now["t"])
    assert bucket.try_acquire(1)
    now["t"] = 100.0
    assert bucket.try_acquire(3) is True
    assert bucket.try_acquire(1) is False
''',
        hidden='''def test_request_larger_than_capacity_never_succeeds():
    """请求数超过容量时应失败，等待时间为无穷大。"""
    now = {"t": 0.0}
    bucket = TokenBucket(rate=1, capacity=2, clock=lambda: now["t"])
    assert bucket.try_acquire(3) is False
    assert bucket.wait_time(3) == float("inf")


def test_non_positive_request_raises_value_error():
    """n 必须是正数。"""
    bucket = TokenBucket(rate=1, capacity=2, clock=lambda: 0.0)
    for n in (0, -1):
        try:
            bucket.try_acquire(n)
        except ValueError:
            pass
        else:
            assert False, "非正请求应抛出 ValueError"
''',
        solution='''class TokenBucket:
    """Token bucket rate limiter with an injected clock."""
    def __init__(self, rate, capacity, clock):
        self.rate = float(rate)
        self.capacity = float(capacity)
        self.clock = clock
        self.tokens = float(capacity)
        self.updated_at = float(clock())

    def _check(self, n):
        if n <= 0:
            raise ValueError("n must be positive")

    def _refill(self):
        now = float(self.clock())
        elapsed = max(0.0, now - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated_at = now

    def try_acquire(self, n=1):
        self._check(n)
        self._refill()
        if n > self.capacity or self.tokens + 1e-12 < n:
            return False
        self.tokens -= n
        return True

    def wait_time(self, n=1):
        self._check(n)
        self._refill()
        if n > self.capacity:
            return float("inf")
        if self.tokens >= n:
            return 0
        return (n - self.tokens) / self.rate
''',
        hints=["每次查询或获取前都先根据 `clock()` 懒补充令牌。", "令牌数补充后要用 capacity 截断。", "wait_time 不应修改除补充时间以外的消费状态。"],
        points=["限流算法", "时间依赖注入", "突发容量与长期速率"],
        numpy=False,
    ),
    dict(
        id="lab-context-trim",
        course="harness",
        title="按预算裁剪对话历史并保持工具调用配对",
        level="hard",
        desc='''### 背景
Agent 上下文很容易超过模型 token 预算。粗暴地从头截断会丢掉 system 指令，或者留下 assistant 的 tool_calls 却删掉 tool 结果，导致模型看到不一致的历史。面试官会用这题考察你是否能把消息历史看成带约束的结构，而不是普通字符串数组。
### 要实现什么
实现 `trim_messages(messages, max_tokens, count_tokens)`。`count_tokens(message)` 是注入函数，返回单条消息的 token 数。函数返回新的消息列表，不能修改输入。要求：所有 `role="system"` 消息永远保留；最后一条 `role="user"` 消息永远保留；其余消息从最早开始丢弃，直到总 token 不超过预算或没有可丢消息。如果某条 assistant 消息包含 `tool_calls`，它和紧随其后的、`tool_call_id` 属于这些调用 id 的 tool 消息必须作为一个整体保留或整体丢弃。预算小到连必须保留的消息都超出时，返回必须保留集合即可。
### 例子
历史为 system、旧 user、assistant tool_calls、tool、最后 user；预算只够 system 和最后 user 时，应同时丢弃 assistant tool_calls 与 tool 结果。
### 约束
只能使用标准库；保持原顺序；不要重新计算或改写消息内容。''',
        starter='''def trim_messages(messages, max_tokens, count_tokens):
    """Trim chat history to a token budget while preserving required messages and tool pairs."""
    raise NotImplementedError
''',
        tests='''def _count(msg):
    return len(msg.get("content", ""))


def test_keeps_system_and_last_user_while_dropping_oldest():
    """system 和最后 user 必须保留，普通旧消息从最早开始丢。"""
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "old user"},
        {"role": "assistant", "content": "mid"},
        {"role": "user", "content": "final"},
    ]
    got = trim_messages(messages, max_tokens=11, count_tokens=_count)
    assert [m["content"] for m in got] == ["sys", "mid", "final"], got
    assert messages[1]["content"] == "old user", "不能修改输入"


def test_tool_pair_is_kept_together_when_budget_allows():
    """assistant tool_calls 与对应 tool 结果要一起保留。"""
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a"}]},
        {"role": "tool", "tool_call_id": "a", "content": "rr"},
        {"role": "assistant", "content": "new"},
        {"role": "user", "content": "ask"},
    ]
    got = trim_messages(messages, 9, _count)
    roles = [m["role"] for m in got]
    assert roles == ["system", "assistant", "tool", "assistant", "user"], got


def test_tool_pair_is_dropped_together_when_needed():
    """预算不足时不能只留下半个工具调用配对。"""
    messages = [
        {"role": "system", "content": "s"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a"}]},
        {"role": "tool", "tool_call_id": "a", "content": "tool"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "ask"},
    ]
    got = trim_messages(messages, 6, _count)
    assert all(m.get("tool_call_id") != "a" for m in got), got
    assert not any(m.get("tool_calls") for m in got), got


def test_returns_required_messages_even_when_over_budget():
    """预算小于必保消息总量时，也只能返回必保消息。"""
    messages = [
        {"role": "system", "content": "system-long"},
        {"role": "assistant", "content": "drop"},
        {"role": "user", "content": "last-user"},
    ]
    got = trim_messages(messages, 1, _count)
    assert [m["role"] for m in got] == ["system", "user"], got
''',
        hidden='''def test_all_system_messages_are_preserved():
    """不只第一条，所有 system 消息都必须保留。"""
    messages = [
        {"role": "system", "content": "a"},
        {"role": "user", "content": "old"},
        {"role": "system", "content": "b"},
        {"role": "user", "content": "last"},
    ]
    got = trim_messages(messages, 2, _count)
    assert [m["content"] for m in got] == ["a", "b", "last"], got


def test_multiple_tool_results_for_one_assistant_are_grouped():
    """一个 assistant 发起多个工具调用时，对应结果要作为一个整体。"""
    messages = [
        {"role": "system", "content": "s"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a"}, {"id": "b"}]},
        {"role": "tool", "tool_call_id": "a", "content": "aa"},
        {"role": "tool", "tool_call_id": "b", "content": "bb"},
        {"role": "user", "content": "last"},
    ]
    got = trim_messages(messages, 5, _count)
    assert [m["role"] for m in got] == ["system", "user"], got
''',
        solution='''def trim_messages(messages, max_tokens, count_tokens):
    """Trim chat history to a token budget while preserving required messages and tool pairs."""
    copied = [dict(m) for m in messages]
    last_user = None
    for i, msg in enumerate(copied):
        if msg.get("role") == "user":
            last_user = i

    units = []
    i = 0
    while i < len(copied):
        msg = copied[i]
        group = [i]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            ids = {call.get("id") for call in msg.get("tool_calls", [])}
            j = i + 1
            while j < len(copied) and copied[j].get("role") == "tool" and copied[j].get("tool_call_id") in ids:
                group.append(j)
                j += 1
            i = j
        else:
            i += 1
        protected = any(copied[idx].get("role") == "system" or idx == last_user for idx in group)
        units.append({"indices": group, "protected": protected})

    kept = set(range(len(copied)))
    total = sum(count_tokens(m) for m in copied)
    for unit in units:
        if total <= max_tokens:
            break
        if unit["protected"]:
            continue
        for idx in unit["indices"]:
            if idx in kept:
                total -= count_tokens(copied[idx])
                kept.remove(idx)
    return [copied[i] for i in range(len(copied)) if i in kept]
''',
        hints=["先把消息切成不可分割的 unit，而不是直接按单条消息删除。", "system 和最后 user 所在 unit 标记为 protected。", "从前往后删除非 protected unit，直到预算满足或无可删内容。"],
        points=["上下文窗口管理", "工具调用一致性", "不可变输入和顺序保持"],
        numpy=False,
    ),
    dict(
        id="lab-compaction",
        course="harness",
        title="把早期对话压缩成摘要并保留最近轮次",
        level="hard",
        desc='''### 背景
当对话很长时，直接丢弃历史会让 Agent 忘记用户偏好和已完成工作；更好的做法是把早期若干轮压缩成摘要，同时保留最近几轮原文，尤其不能拆散工具调用。面试官会考察你对“轮次”、预算、摘要函数注入和工具消息配对的综合处理。
### 要实现什么
实现 `compact_messages(messages, max_tokens, count_tokens, summarize, keep_recent_turns)`，返回 `(new_messages, compacted_count)`。如果总 token 未超过预算，返回输入拷贝和 0。超过预算时，把最早的若干个可压缩轮次替换为一条 `{"role":"system", "name":"summary", "content": summary}`。轮次以 `user` 消息开始，到下一个 `user` 前结束；其中的 assistant tool_calls 和后续 tool 结果不能拆开。最近 `keep_recent_turns` 个用户轮次必须保留原文；所有 system 消息保留。`summarize(compacted_messages)` 由外部注入，接收被压缩消息列表并返回摘要文本。`compacted_count` 是被替换掉的原消息条数。
### 例子
有三轮 user/assistant，对 `keep_recent_turns=1` 且预算不足时，可把第一轮或前两轮替换成一条摘要，但最后一轮必须保持原样。
### 约束
只能用标准库；不要求一定压到预算以下，因为摘要可能仍很长，但应尽量从最早轮次开始压缩。''',
        starter='''def compact_messages(messages, max_tokens, count_tokens, summarize, keep_recent_turns):
    """Compact early conversation turns into a summary message."""
    raise NotImplementedError
''',
        tests='''def _count(msg):
    return len(msg.get("content", ""))


def test_no_compaction_when_under_budget():
    """未超过预算时应只返回拷贝，不调用摘要。"""
    called = []
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "hi"}]
    new_messages, count = compact_messages(messages, 10, _count, lambda xs: called.append(xs) or "sum", 1)
    assert new_messages == messages and new_messages is not messages
    assert count == 0 and called == [], called


def test_compacts_oldest_turn_and_keeps_recent_turn():
    """超过预算时应压缩早期轮次，并保留最近一轮原文。"""
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "question one"},
        {"role": "assistant", "content": "answer one"},
        {"role": "user", "content": "question two"},
        {"role": "assistant", "content": "answer two"},
    ]
    seen = []
    def summarize(xs):
        seen[:] = xs
        return "old summary"
    new_messages, count = compact_messages(messages, 25, _count, summarize, keep_recent_turns=1)
    assert count == 2, (count, new_messages)
    assert new_messages[1]["name"] == "summary", new_messages
    assert [m["content"] for m in seen] == ["question one", "answer one"], seen
    assert new_messages[-2]["content"] == "question two", new_messages


def test_compacts_enough_early_turns_to_fit_budget():
    """如果只压缩一轮还超预算，应继续纳入更早的后续轮次。"""
    messages = [
        {"role": "user", "content": "u1xxxx"}, {"role": "assistant", "content": "a1xxxx"},
        {"role": "user", "content": "u2xxxx"}, {"role": "assistant", "content": "a2xxxx"},
        {"role": "user", "content": "u3"}, {"role": "assistant", "content": "a3"},
    ]
    new_messages, count = compact_messages(messages, 14, _count, lambda xs: "sum", keep_recent_turns=1)
    assert count == 4, (count, new_messages)
    assert [m["content"] for m in new_messages] == ["sum", "u3", "a3"], new_messages


def test_recent_tool_pair_is_preserved():
    """最近轮次里的 tool_calls 和 tool 结果不能被摘要拆散。"""
    messages = [
        {"role": "user", "content": "old"}, {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "need tool"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t"}]},
        {"role": "tool", "tool_call_id": "t", "content": "tool result"},
        {"role": "assistant", "content": "final"},
    ]
    new_messages, count = compact_messages(messages, 30, _count, lambda xs: "summary", 1)
    roles = [m["role"] for m in new_messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant"] or roles == ["system", "user", "assistant", "tool", "assistant"], new_messages
    assert any(m.get("tool_call_id") == "t" for m in new_messages), new_messages
''',
        hidden='''def test_no_eligible_turns_returns_original_even_if_over_budget():
    """只有最近轮次可保留时，即使超预算也不应压缩它。"""
    messages = [{"role": "user", "content": "very long"}, {"role": "assistant", "content": "also long"}]
    new_messages, count = compact_messages(messages, 1, _count, lambda xs: "sum", keep_recent_turns=1)
    assert new_messages == messages and count == 0, (new_messages, count)


def test_system_messages_are_preserved_around_summary():
    """system 消息要保留，摘要只替换普通轮次。"""
    messages = [
        {"role": "system", "content": "policy"},
        {"role": "user", "content": "old"}, {"role": "assistant", "content": "answer"},
        {"role": "user", "content": "last"},
    ]
    new_messages, count = compact_messages(messages, 10, _count, lambda xs: "sum", 1)
    assert new_messages[0]["content"] == "policy", new_messages
    assert new_messages[1]["name"] == "summary", new_messages
    assert count == 2, count
''',
        solution='''def compact_messages(messages, max_tokens, count_tokens, summarize, keep_recent_turns):
    """Compact early conversation turns into a summary message."""
    copied = [dict(m) for m in messages]
    if sum(count_tokens(m) for m in copied) <= max_tokens:
        return copied, 0

    user_indices = [i for i, m in enumerate(copied) if m.get("role") == "user"]
    protected_start = user_indices[-keep_recent_turns] if keep_recent_turns and len(user_indices) >= keep_recent_turns else (user_indices[0] if user_indices else len(copied))

    turns = []
    i = 0
    while i < protected_start:
        if copied[i].get("role") == "system":
            i += 1
            continue
        start = i
        if copied[i].get("role") == "user":
            i += 1
            while i < protected_start and copied[i].get("role") != "user":
                i += 1
        else:
            i += 1
        turns.append(list(range(start, i)))

    if not turns:
        return copied, 0

    for take in range(1, len(turns) + 1):
        selected = {idx for turn in turns[:take] for idx in turn}
        compacted = [copied[i] for i in range(len(copied)) if i in selected]
        summary = {"role": "system", "name": "summary", "content": summarize([dict(m) for m in compacted])}
        out = []
        inserted = False
        for i, msg in enumerate(copied):
            if i in selected:
                if not inserted:
                    out.append(summary)
                    inserted = True
                continue
            out.append(dict(msg))
        if sum(count_tokens(m) for m in out) <= max_tokens or take == len(turns):
            return out, len(compacted)
    return copied, 0
''',
        hints=["先按 user 边界把普通消息划分成轮次。", "最近 k 个 user 轮次和所有 system 消息是保护区。", "逐步扩大被摘要的早期轮次数，直到预算满足或没有更多可压缩轮次。"],
        points=["上下文压缩策略", "轮次建模", "摘要函数依赖注入"],
        numpy=False,
    ),
    dict(
        id="lab-chunker",
        course="agent",
        title="按标题路径切分 Markdown 文档",
        level="medium",
        desc='''### 背景
RAG 系统里，文档切分质量直接影响检索质量。Markdown 文档天然带标题层级，如果切分时丢掉标题路径，模型很难理解片段所属章节；如果超长章节不继续按段落拆分，又会超过 embedding 或上下文限制。面试官会用这题考察你对文本偏移、层级路径和重叠窗口的工程细节。
### 要实现什么
实现 `chunk_markdown(markdown, max_chars=1000, overlap=100)`，返回列表，每项为 `{"path": [...], "text": str, "start": int, "end": int}`。按 ATX 标题（`#` 到 `######`）识别层级；每个块带当前标题路径，如 `# A` 下的 `## B` 路径为 `["A", "B"]`。普通章节不超过 `max_chars` 时作为一个块；超过时按空行分隔的段落继续拆，下一块应包含上一块末尾最多 `overlap` 个字符作为重叠。`start/end` 是在原始字符串中的字符偏移，且 `markdown[start:end]` 应等于返回的 `text`。
### 例子
`# Intro\ntext\n## Detail\nmore` 应得到两个块，路径分别是 `["Intro"]` 和 `["Intro", "Detail"]`。
### 约束
只能使用标准库；不要丢掉标题行本身；空文档返回空列表。''',
        starter='''def chunk_markdown(markdown, max_chars=1000, overlap=100):
    """Split Markdown into heading-aware chunks with source offsets."""
    raise NotImplementedError
''',
        tests='''def test_splits_by_heading_path():
    """标题层级应转换成每个块的 path。"""
    md = "# A\\nalpha\\n## B\\nbravo\\n# C\\ncharlie\\n"
    chunks = chunk_markdown(md, max_chars=100, overlap=0)
    assert [c["path"] for c in chunks] == [["A"], ["A", "B"], ["C"]], chunks
    assert chunks[1]["text"].startswith("## B"), chunks[1]


def test_offsets_match_original_text():
    """每个块的 start/end 必须能切回原文。"""
    md = "intro\\n\\n# A\\nbody\\n"
    chunks = chunk_markdown(md, max_chars=100, overlap=0)
    for chunk in chunks:
        assert md[chunk["start"]:chunk["end"]] == chunk["text"], chunk


def test_long_section_splits_on_paragraphs_with_overlap():
    """超长章节应按段落拆分，并让相邻块有重叠文本。"""
    md = "# A\\n" + "p1-abcdef\\n\\n" + "p2-abcdef\\n\\n" + "p3-abcdef\\n"
    chunks = chunk_markdown(md, max_chars=18, overlap=4)
    assert len(chunks) >= 2, chunks
    assert all(c["path"] == ["A"] for c in chunks), chunks
    assert chunks[0]["text"][-4:] == chunks[1]["text"][:4], chunks


def test_document_without_heading_has_empty_path():
    """无标题文档也要切成 path 为空的块。"""
    chunks = chunk_markdown("plain text", max_chars=100, overlap=0)
    assert chunks == [{"path": [], "text": "plain text", "start": 0, "end": 10}], chunks
''',
        hidden='''def test_heading_hierarchy_resets_when_level_goes_up():
    """标题层级回退时，旧的下级标题不能留在 path 里。"""
    md = "# A\\ntext\\n## B\\ntext\\n### C\\ntext\\n## D\\ntext\\n"
    chunks = chunk_markdown(md, 100, 0)
    assert chunks[-1]["path"] == ["A", "D"], chunks


def test_empty_markdown_returns_empty_list():
    """空字符串应返回空列表。"""
    assert chunk_markdown("", 10, 2) == []
''',
        solution='''import re


def _split_long(markdown, start, end, path, max_chars, overlap):
    text = markdown[start:end]
    if len(text) <= max_chars:
        return [{"path": path[:], "text": text, "start": start, "end": end}]
    para_spans = []
    for match in re.finditer(r"\\S(?:.*?\\S)?(?:\\n\\s*\\n|$)", text, re.DOTALL):
        ps = start + match.start()
        pe = start + match.end()
        para_spans.append((ps, pe))
    if not para_spans:
        para_spans = [(start, end)]
    chunks = []
    cur_start = para_spans[0][0]
    cur_end = para_spans[0][1]
    for ps, pe in para_spans[1:]:
        if pe - cur_start > max_chars and cur_end > cur_start:
            chunks.append({"path": path[:], "text": markdown[cur_start:cur_end], "start": cur_start, "end": cur_end})
            cur_start = max(cur_end - overlap, start)
        cur_end = pe
    if cur_end > cur_start:
        chunks.append({"path": path[:], "text": markdown[cur_start:cur_end], "start": cur_start, "end": cur_end})
    return chunks


def chunk_markdown(markdown, max_chars=1000, overlap=100):
    """Split Markdown into heading-aware chunks with source offsets."""
    if not markdown:
        return []
    heading_re = re.compile(r"^(#{1,6})\\s+(.+?)\\s*$", re.MULTILINE)
    sections = []
    stack = []
    last_start = 0
    last_path = []
    found = False
    for match in heading_re.finditer(markdown):
        found = True
        if match.start() > last_start:
            sections.append((last_start, match.start(), last_path[:]))
        level = len(match.group(1))
        title = match.group(2).strip().strip("#").strip()
        stack = stack[:level - 1]
        stack.append(title)
        last_path = stack[:]
        last_start = match.start()
    if found:
        sections.append((last_start, len(markdown), last_path[:]))
    else:
        sections.append((0, len(markdown), []))

    chunks = []
    for start, end, path in sections:
        if start == end:
            continue
        chunks.extend(_split_long(markdown, start, end, path, max_chars, max(0, overlap)))
    return chunks
''',
        hints=["用正则的 MULTILINE 模式找到每个标题及其原文偏移。", "维护一个标题栈：新标题级别为 n 时截断到 n-1 再追加。", "超长章节拆分时，返回文本必须仍然能用 start/end 从原文切出来。"],
        points=["Markdown 结构解析", "RAG chunk 元数据", "字符偏移和重叠窗口"],
        numpy=False,
    ),
    dict(
        id="lab-bm25",
        course="agent",
        title="实现可注入分词器的 BM25 检索类",
        level="medium",
        desc='''### 背景
即使有向量检索，BM25 仍是搜索和 RAG 的强基线：它对关键词、代码符号、稀有词非常敏感，常与 embedding 结果混合使用。面试官会通过这题考察你是否理解倒排统计、IDF 平滑、文档长度归一化和可插拔分词器。
### 要实现什么
实现类 `BM25(documents, tokenizer=str.split, k1=1.5, b=0.75)`。`documents` 可以是字符串列表，也可以是 `{doc_id: text}` 字典；列表文档的 id 为下标。初始化时对文档分词，统计每篇文档词频、文档频率、平均长度。使用平滑 IDF：`log(1 + (N - df + 0.5) / (df + 0.5))`。方法 `search(query, k)` 对查询分词，返回最多 k 个 `(doc_id, score)`，按分数从高到低排序，分数为 0 的文档不返回；同分时按 doc_id 的字符串形式稳定排序。
### 例子
文档 `{"d1":"red apple", "d2":"blue car"}`，查询 `apple` 应返回 `d1` 在首位。
### 约束
只能使用标准库；不要在 `search` 时重建全部统计；空文档集合或空查询返回空列表。''',
        starter='''class BM25:
    """A small BM25 retriever with injectable tokenization."""
    def __init__(self, documents, tokenizer=str.split, k1=1.5, b=0.75):
        raise NotImplementedError

    def search(self, query, k):
        raise NotImplementedError
''',
        tests='''def test_basic_keyword_search_returns_best_doc():
    """包含查询词的文档应排在前面。"""
    bm25 = BM25({"d1": "red apple fresh", "d2": "blue car", "d3": "apple pie apple"})
    results = bm25.search("apple", 2)
    assert results[0][0] == "d3", results
    assert len(results) == 2 and results[0][1] >= results[1][1] > 0, results


def test_list_documents_use_integer_ids():
    """documents 传列表时，doc_id 应是列表下标。"""
    bm25 = BM25(["alpha beta", "gamma beta"])
    ids = [doc_id for doc_id, score in bm25.search("gamma", 10)]
    assert ids == [1], ids


def test_custom_tokenizer_is_used():
    """分词函数应完全由调用方注入。"""
    tokenizer = lambda text: [t.lower() for t in text.replace("-", " ").split()]
    bm25 = BM25({"a": "Foo-Bar", "b": "baz"}, tokenizer=tokenizer)
    assert bm25.search("foo", 1)[0][0] == "a"


def test_empty_query_or_no_match_returns_empty_list():
    """空查询和无匹配都应返回空列表。"""
    bm25 = BM25(["alpha beta"])
    assert bm25.search("", 5) == []
    assert bm25.search("zzz", 5) == []
''',
        hidden='''def test_empty_corpus_returns_empty_results():
    """空语料不应报错。"""
    assert BM25([]).search("anything", 3) == []


def test_ties_are_sorted_by_doc_id_string():
    """分数相同时按 doc_id 字符串稳定排序。"""
    bm25 = BM25({"b": "same", "a": "same"})
    assert [doc_id for doc_id, score in bm25.search("same", 10)] == ["a", "b"]
''',
        solution='''import math
from collections import Counter, defaultdict


class BM25:
    """A small BM25 retriever with injectable tokenization."""
    def __init__(self, documents, tokenizer=str.split, k1=1.5, b=0.75):
        self.tokenizer = tokenizer
        self.k1 = k1
        self.b = b
        items = documents.items() if isinstance(documents, dict) else enumerate(documents)
        self.doc_ids = []
        self.tfs = []
        self.lengths = []
        df = defaultdict(int)
        for doc_id, text in items:
            tokens = list(tokenizer(text))
            tf = Counter(tokens)
            self.doc_ids.append(doc_id)
            self.tfs.append(tf)
            self.lengths.append(len(tokens))
            for term in tf:
                df[term] += 1
        self.n = len(self.doc_ids)
        self.avgdl = sum(self.lengths) / self.n if self.n else 0
        self.idf = {term: math.log(1 + (self.n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def search(self, query, k):
        if self.n == 0 or k <= 0:
            return []
        terms = list(self.tokenizer(query))
        if not terms:
            return []
        scores = []
        for doc_id, tf, dl in zip(self.doc_ids, self.tfs, self.lengths):
            score = 0.0
            for term in terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                denom = freq + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 0))
                score += self.idf.get(term, 0.0) * (freq * (self.k1 + 1)) / denom
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda item: (-item[1], str(item[0])))
        return scores[:k]
''',
        hints=["初始化阶段完成词频、文档频率和平均长度统计。", "BM25 的分母里要包含文档长度相对平均长度的归一化。", "search 只对匹配词累加分数，并过滤 0 分文档。"],
        points=["稀疏检索基础", "倒排统计与 IDF 平滑", "排序稳定性"],
        numpy=False,
    ),
    dict(
        id="lab-hybrid-rrf",
        course="agent",
        title="实现多路检索结果的 RRF 融合",
        level="easy",
        desc='''### 背景
现代 RAG 常把 BM25、向量检索、图检索或重排器结果合并。不同检索器分数尺度不一致，直接相加不可靠；Reciprocal Rank Fusion（RRF）只使用排名，简单但很稳健。面试官会用这题考察你是否能处理多路结果、权重、去重、截断和稳定排序。
### 要实现什么
实现 `rrf(rankings, k=60, weights=None, top_n=None)`。`rankings` 是多路检索结果列表，每一路可以是 doc_id 列表，也可以是 `(doc_id, score)` 元组列表；RRF 忽略原始 score，只用名次。某一路内部重复 doc_id 时只按第一次出现计分。第 i 路权重为 `weights[i]`，未传时全为 1；贡献分为 `weight / (k + rank)`，rank 从 1 开始。合并后返回 `(doc_id, fused_score)` 列表，按融合分降序；同分按第一次在所有 ranking 中出现的先后顺序排序。`top_n` 不为 None 时只返回前 N 个。权重长度不匹配时抛出 `ValueError`。
### 例子
`[["a","b"],["b","c"]]` 中，`b` 来自两路，通常会排在 `a` 和 `c` 前面。
### 约束
只能使用标准库；函数应是纯函数，不修改输入排名列表。''',
        starter='''def rrf(rankings, k=60, weights=None, top_n=None):
    """Fuse ranked retrieval results with Reciprocal Rank Fusion."""
    raise NotImplementedError
''',
        tests='''def test_fuses_multiple_rankings_by_reciprocal_rank():
    """出现在多路结果中的文档应累加 RRF 分数。"""
    result = rrf([["a", "b", "c"], ["b", "d"]], k=60)
    assert result[0][0] == "b", result
    assert {doc for doc, score in result} == {"a", "b", "c", "d"}, result


def test_accepts_tuple_items_and_ignores_original_scores():
    """输入项可以是 (doc_id, score)，但原始 score 不参与计算。"""
    result = rrf([[("a", 100.0), ("b", 0.1)], [("b", 9.0)]], k=10)
    assert result[0][0] == "b", result


def test_weights_change_contribution():
    """weights 应能提升某一路检索结果的贡献。"""
    result = rrf([["a"], ["b"]], k=60, weights=[1, 10])
    assert result[0][0] == "b", result


def test_deduplicates_within_one_ranking_and_truncates():
    """同一路重复文档只计第一次，top_n 应截断结果。"""
    result = rrf([["a", "a", "b"], ["c"]], k=60, top_n=2)
    assert len(result) == 2, result
    score_a = dict(result).get("a")
    assert score_a == 1 / 61, result
''',
        hidden='''def test_empty_rankings_return_empty_list():
    """空输入应返回空列表。"""
    assert rrf([]) == []
    assert rrf([[]]) == []


def test_weight_length_mismatch_raises_value_error():
    """weights 长度必须与 rankings 路数一致。"""
    try:
        rrf([["a"], ["b"]], weights=[1])
    except ValueError:
        pass
    else:
        assert False, "weights 长度不匹配应抛出 ValueError"
''',
        solution='''def rrf(rankings, k=60, weights=None, top_n=None):
    """Fuse ranked retrieval results with Reciprocal Rank Fusion."""
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights length must match rankings")
    scores = {}
    first_seen = {}
    order = 0
    for ranking, weight in zip(rankings, weights):
        seen_in_ranking = set()
        rank = 0
        for item in ranking:
            doc_id = item[0] if isinstance(item, tuple) else item
            if doc_id in seen_in_ranking:
                continue
            seen_in_ranking.add(doc_id)
            rank += 1
            if doc_id not in first_seen:
                first_seen[doc_id] = order
                order += 1
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (k + rank)
    fused = sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))
    return fused if top_n is None else fused[:top_n]
''',
        hints=["RRF 只关心 rank，不关心原始检索分数。", "每一路内部先去重，避免重复结果刷分。", "全局排序需要一个 first_seen 作为同分时的稳定规则。"],
        points=["混合检索融合", "排名分数归一化", "去重和稳定排序"],
        numpy=False,
    ),
]
