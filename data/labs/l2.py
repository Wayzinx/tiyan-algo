LABS = [
    dict(
        id="lab-react-parser",
        course="agent",
        title="解析 ReAct 格式输出",
        level="medium",
        desc=r'''### 背景
ReAct 是很多 Agent 原型和面试题都会使用的输出格式：模型先写 Thought，再写 Action 与 Action Input，或者直接给出 Final Answer。真实系统里，解析器不能只靠一次字符串切分，因为模型经常会多打空格、大小写不一致、把 JSON 分多行写，甚至漏掉字段。面试官通常想看你能否把“模型输出是半结构化文本”这个事实考虑进去：既要尽量容错，又要在格式不满足工具调用契约时返回可回填给模型的错误提示，而不是让后续执行器崩溃。

### 要实现什么
实现 `parse_react(text)`。成功解析工具动作时返回 `{"ok": True, "type": "action", "thought": str|None, "action": str, "action_input": object}`；成功解析最终答案时返回 `{"ok": True, "type": "final", "thought": str|None, "final_answer": str}`；格式错误时返回 `{"ok": False, "error": "..."}`。标签名 `Thought`、`Action`、`Action Input`、`Final Answer` 大小写不敏感，冒号前后可以有空白，字段内容可以跨多行，Action Input 必须是合法 JSON 对象或数组。

### 例子
输入 `Thought: 需要查天气\nAction: search\nAction Input: {"q":"today weather"}`，返回 action 结构，`action_input` 是字典。输入 `thought: 已经足够\nfinal answer: 42`，返回 final 结构。

### 约束
只能使用标准库。不要调用模型或工具；这个函数只做解析。实现应对空字符串、缺少 Action Input、JSON 非法、同时出现 Action 与 Final Answer 等情况给出明确错误。''',
        starter=r'''def parse_react(text):
    """解析 ReAct 文本，返回结构化动作、最终答案或可回填给模型的错误。"""
    raise NotImplementedError
''',
        tests=r'''def test_parse_action_with_json_input():
    """解析标准 Action 和 JSON 参数。"""
    text = "Thought: 需要查询\nAction: search\nAction Input: {\"q\": \"agent\", \"top_k\": 3}"
    got = parse_react(text)
    assert got["ok"] is True, got
    assert got["type"] == "action", got
    assert got["thought"] == "需要查询", got
    assert got["action"] == "search", got
    assert got["action_input"] == {"q": "agent", "top_k": 3}, got


def test_parse_final_answer_case_insensitive():
    """标签大小写和多余空白不影响 Final Answer。"""
    got = parse_react("  thought : done\n FINAL ANSWER : 结果是 42  ")
    assert got["ok"] is True, got
    assert got["type"] == "final", got
    assert got["thought"] == "done", got
    assert got["final_answer"] == "结果是 42", got


def test_invalid_json_returns_feedback_error():
    """Action Input 不是合法 JSON 时返回可回填错误。"""
    got = parse_react("Thought: x\nAction: calc\nAction Input: {'a': 1}")
    assert got["ok"] is False, got
    assert "Action Input" in got["error"] and "JSON" in got["error"], got


def test_missing_action_input_is_error():
    """有 Action 但缺少 Action Input 必须报错。"""
    got = parse_react("Thought: x\nAction: search")
    assert got["ok"] is False, got
    assert "Action Input" in got["error"], got
''',
        hidden=r'''def test_multiline_action_input_and_whitespace():
    """跨行 JSON 参数也能解析。"""
    text = "thought: plan\n action : write_file \n action input : {\n  \"path\": \"a.txt\",\n  \"content\": \"hi\"\n}"
    got = parse_react(text)
    assert got["ok"] is True, got
    assert got["action"] == "write_file", got
    assert got["action_input"] == {"path": "a.txt", "content": "hi"}, got


def test_action_and_final_together_is_error():
    """同一条输出不能既调用工具又给最终答案。"""
    got = parse_react("Thought: x\nAction: a\nAction Input: {}\nFinal Answer: done")
    assert got["ok"] is False, got
    assert "不能同时" in got["error"] or "同时" in got["error"], got


def test_unknown_or_empty_output_is_error():
    """空输出或没有任何标签时返回错误提示。"""
    got = parse_react("   just text   ")
    assert got["ok"] is False, got
    assert "Thought" in got["error"] and "Final Answer" in got["error"], got
''',
        solution=r'''def parse_react(text):
    """解析 ReAct 文本，返回结构化动作、最终答案或可回填给模型的错误。"""
    import json
    import re

    if not isinstance(text, str) or not text.strip():
        return {"ok": False, "error": "输出为空，请按 Thought + Action/Action Input 或 Final Answer 格式重新输出。"}
    label_re = re.compile(r"^\s*(thought|action input|action|final answer)\s*:\s*(.*)$", re.I)
    labels = []
    current = None
    chunks = []
    for line in text.splitlines():
        match = label_re.match(line)
        if match:
            if current is not None:
                labels.append((current, "\n".join(chunks).strip()))
            current = match.group(1).lower()
            chunks = [match.group(2)]
        elif current is not None:
            chunks.append(line)
    if current is not None:
        labels.append((current, "\n".join(chunks).strip()))
    if not labels:
        return {"ok": False, "error": "未找到 Thought、Action、Action Input 或 Final Answer 标签，请按 ReAct 格式重新输出。"}
    fields = {}
    for name, value in labels:
        fields[name] = value
    has_action = bool(fields.get("action"))
    has_final = bool(fields.get("final answer"))
    if has_action and has_final:
        return {"ok": False, "error": "一次输出不能同时包含 Action 和 Final Answer，请二选一。"}
    thought = fields.get("thought")
    if has_final:
        return {"ok": True, "type": "final", "thought": thought, "final_answer": fields["final answer"].strip()}
    if has_action:
        if "action input" not in fields or not fields["action input"].strip():
            return {"ok": False, "error": "检测到 Action，但缺少 Action Input。请补充合法 JSON，例如 Action Input: {\"key\": \"value\"}。"}
        try:
            action_input = json.loads(fields["action input"])
        except Exception as exc:
            return {"ok": False, "error": "Action Input 必须是合法 JSON，解析失败：%s。请重新输出。" % exc}
        if not isinstance(action_input, (dict, list)):
            return {"ok": False, "error": "Action Input 应是 JSON 对象或数组，便于工具执行器读取参数。"}
        return {"ok": True, "type": "action", "thought": thought, "action": fields["action"].strip(), "action_input": action_input}
    return {"ok": False, "error": "未找到可执行的 Action 或 Final Answer，请按 Thought + Action/Action Input 或 Final Answer 格式重新输出。"}
''',
        hints=["先用正则按行识别标签，再把每个标签后的跨行内容收集起来。", "Action Input 不要手写解析，交给 json.loads，并把异常转成模型可读提示。", "同时出现 Action 和 Final Answer、缺字段、空文本都要返回 ok=False，而不是抛异常。"],
        points=["半结构化模型输出解析", "容错标签匹配与跨行字段", "JSON 参数校验", "可回填错误设计"],
        numpy=False,
    ),
    dict(
        id="lab-mcp-jsonrpc",
        course="agent",
        title="最小 MCP 风格 JSON-RPC 服务端",
        level="hard",
        desc=r'''### 背景
MCP 风格的工具服务通常建立在 JSON-RPC 2.0 之上：客户端发 `initialize` 握手，再通过 `tools/list` 发现工具，最后用 `tools/call` 调用工具。面试和实际工作里，很多人只实现了“成功路径”，却忽略了 JSON-RPC 的错误码、通知和批量请求，导致 SDK 一接入就出现难排查的问题。本题要求你实现一个最小但协议边界清楚的服务端入口，重点考察协议理解、错误分层和输入校验。

### 要实现什么
实现 `handle(request_json)`，输入是 JSON 字符串，输出是响应 JSON 字符串；如果输入是通知且不需要回复，返回 `None`。支持方法：`initialize` 返回协议版本和 capabilities；`tools/list` 返回内置工具 `echo` 与 `add` 的描述；`tools/call` 支持 `{"name":"echo","arguments":{"text":"hi"}}` 和 `{"name":"add","arguments":{"a":1,"b":2}}`。必须实现 JSON-RPC 2.0 错误：解析失败 `-32700`，请求对象非法 `-32600`，未知方法 `-32601`，参数非法 `-32602`。没有 `id` 的合法请求视为通知，不回复；批量请求要分别处理每个元素，所有元素都不需要回复时返回 `None`。

### 例子
`handle('{"jsonrpc":"2.0","id":1,"method":"initialize"}')` 返回带 `id:1` 的成功响应。`handle('{bad')` 返回 `-32700` 错误。批量请求输入数组时，返回响应数组。

### 约束
只能使用标准库。不要启动 HTTP 服务，也不要读写文件。响应必须能被 `json.loads` 解析；错误响应的 `id` 在无法确定时使用 `None`。参数校验要保守：版本不是 2.0、method 不是字符串、params 类型不对、工具不存在或参数缺失都不能走成功路径。''',
        starter=r'''def handle(request_json):
    """处理一个 JSON-RPC 2.0 请求字符串，返回响应 JSON 字符串；通知返回 None。"""
    raise NotImplementedError
''',
        tests=r'''import json


def test_initialize_success():
    """initialize 返回协议版本和能力声明。"""
    resp = json.loads(handle('{"jsonrpc":"2.0","id":1,"method":"initialize"}'))
    assert resp["jsonrpc"] == "2.0" and resp["id"] == 1, resp
    assert "result" in resp and "capabilities" in resp["result"], resp


def test_tools_call_echo_success():
    """tools/call 能调用内置 echo 工具。"""
    req = {"jsonrpc": "2.0", "id": "a", "method": "tools/call", "params": {"name": "echo", "arguments": {"text": "hi"}}}
    resp = json.loads(handle(json.dumps(req)))
    assert resp["id"] == "a" and "result" in resp, resp
    assert resp["result"]["content"][0]["text"] == "hi", resp


def test_parse_error_code():
    """非法 JSON 返回 -32700。"""
    resp = json.loads(handle('{bad json'))
    assert resp["error"]["code"] == -32700, resp
    assert resp["id"] is None, resp


def test_notification_returns_none():
    """没有 id 的合法通知不返回响应。"""
    assert handle('{"jsonrpc":"2.0","method":"tools/list"}') is None


def test_batch_mixes_response_and_notification():
    """批量请求只返回需要回复的元素。"""
    batch = [{"jsonrpc": "2.0", "method": "initialize"}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
    resp = json.loads(handle(json.dumps(batch)))
    assert isinstance(resp, list) and len(resp) == 1, resp
    assert resp[0]["id"] == 2 and "result" in resp[0], resp
''',
        hidden=r'''import json


def test_invalid_request_and_unknown_method_codes():
    """请求结构非法和未知方法使用不同错误码。"""
    bad = json.loads(handle(json.dumps({"jsonrpc": "2.0", "id": 1, "params": {}})))
    assert bad["error"]["code"] == -32600, bad
    unknown = json.loads(handle(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "missing"})))
    assert unknown["error"]["code"] == -32601, unknown


def test_invalid_params_for_tool_call():
    """工具名或参数不合法返回 -32602。"""
    req = {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "add", "arguments": {"a": 1}}}
    resp = json.loads(handle(json.dumps(req)))
    assert resp["error"]["code"] == -32602, resp


def test_empty_batch_is_invalid_request():
    """空批量请求按 JSON-RPC 规范是非法请求。"""
    resp = json.loads(handle("[]"))
    assert resp["error"]["code"] == -32600 and resp["id"] is None, resp


def test_add_tool_returns_number_text():
    """add 工具会把两个数字相加并以文本内容返回。"""
    req = {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "add", "arguments": {"a": 2, "b": 5}}}
    resp = json.loads(handle(json.dumps(req)))
    assert resp["result"]["content"][0]["text"] == "7", resp
''',
        solution=r'''def handle(request_json):
    """处理一个 JSON-RPC 2.0 请求字符串，返回响应 JSON 字符串；通知返回 None。"""
    import json

    def success(req_id, result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def error(req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def call_tool(params):
        if not isinstance(params, dict):
            raise ValueError("params must be object")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be object")
        if name == "echo":
            if "text" not in arguments:
                raise ValueError("echo requires text")
            return {"content": [{"type": "text", "text": str(arguments["text"])}]}
        if name == "add":
            if "a" not in arguments or "b" not in arguments:
                raise ValueError("add requires a and b")
            a, b = arguments["a"], arguments["b"]
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                raise ValueError("a and b must be numbers")
            total = a + b
            text = str(int(total)) if isinstance(total, float) and total.is_integer() else str(total)
            return {"content": [{"type": "text", "text": text}]}
        raise ValueError("unknown tool")

    def process(req):
        if not isinstance(req, dict):
            return error(None, -32600, "Invalid Request")
        req_id = req.get("id") if "id" in req else None
        is_notification = "id" not in req
        if req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
            return None if is_notification else error(req_id, -32600, "Invalid Request")
        method = req["method"]
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        elif method == "tools/list":
            result = {"tools": [{"name": "echo", "description": "return input text"}, {"name": "add", "description": "add two numbers"}]}
        elif method == "tools/call":
            try:
                result = call_tool(req.get("params"))
            except ValueError as exc:
                return None if is_notification else error(req_id, -32602, str(exc))
        else:
            return None if is_notification else error(req_id, -32601, "Method not found")
        return None if is_notification else success(req_id, result)

    try:
        payload = json.loads(request_json)
    except Exception:
        return json.dumps(error(None, -32700, "Parse error"), ensure_ascii=False, separators=(",", ":"))
    if isinstance(payload, list):
        if not payload:
            return json.dumps(error(None, -32600, "Invalid Request"), ensure_ascii=False, separators=(",", ":"))
        responses = [resp for resp in (process(item) for item in payload) if resp is not None]
        return None if not responses else json.dumps(responses, ensure_ascii=False, separators=(",", ":"))
    resp = process(payload)
    return None if resp is None else json.dumps(resp, ensure_ascii=False, separators=(",", ":"))
''',
        hints=["先把解析 JSON、单个请求处理、批量聚合拆开，错误码会清楚很多。", "通知的判断只看是否存在 id；合法通知和未知方法通知都不需要回复。", "-32600 是请求壳子错，-32601 是 method 不存在，-32602 是已知方法的参数错。"],
        points=["JSON-RPC 2.0 协议边界", "MCP 工具发现与调用最小模型", "通知与批量请求处理", "错误码分层"],
        numpy=False,
    ),
    dict(
        id="lab-permission",
        course="harness",
        title="工具权限规则匹配",
        level="medium",
        desc=r'''### 背景
Agent Harness 在执行工具前通常要做权限决策：读文件可能直接允许，运行构建命令可能需要询问用户，删除文件或执行危险命令必须拒绝。真实产品的规则常写成 `Bash(git *)`、`Read(src/**)` 这种“工具名 + 参数模式”的形式。面试官想考察你能否把规则优先级、通配符匹配和默认策略讲清楚并实现出来，而不是只写几个针对样例的 if 判断。

### 要实现什么
实现 `decide(tool, args, rules)`，返回字符串 `allow`、`ask` 或 `deny`。`tool` 是工具名，如 `Bash`、`Read`；`args` 可以是字符串、列表或字典，函数需要把它规范成可匹配文本：字符串原样，列表用空格连接，字典优先取 `cmd`、`command`、`path`，否则按 key 排序拼成 `key=value`。`rules` 是字典，包含 `default` 和 `entries`，每条 entry 形如 `{"pattern":"Bash(git *)","decision":"ask"}`。模式括号内使用 `fnmatch` 通配符，`*` 匹配一段文本，`**` 可用于路径前缀。

### 例子
`decide("Bash", "git status", rules)` 命中 `Bash(git *)` 返回 `ask`。如果同时命中 `Bash(*)` 的 allow 和 `Bash(rm *)` 的 deny，执行 `rm -rf tmp` 必须返回 `deny`。

### 约束
只能使用标准库。优先级固定为 `deny > ask > allow`，没有命中任何规则时返回 `default`，默认值缺失时按 `ask` 处理。非法 decision 或无法解析的 pattern 应忽略，不要让权限判断崩溃。''',
        starter=r'''def decide(tool, args, rules):
    """根据工具名、参数和权限规则返回 allow / ask / deny。"""
    raise NotImplementedError
''',
        tests=r'''def test_allow_read_src_path():
    """Read(src/**) 能允许读取 src 下路径。"""
    rules = {"default": "ask", "entries": [{"pattern": "Read(src/**)", "decision": "allow"}]}
    assert decide("Read", "src/app/main.py", rules) == "allow"


def test_deny_overrides_allow():
    """同时命中时 deny 优先于 allow。"""
    rules = {"default": "allow", "entries": [
        {"pattern": "Bash(*)", "decision": "allow"},
        {"pattern": "Bash(rm *)", "decision": "deny"},
    ]}
    assert decide("Bash", "rm -rf build", rules) == "deny"


def test_ask_overrides_allow():
    """ask 的优先级高于 allow。"""
    rules = {"default": "deny", "entries": [
        {"pattern": "Bash(*)", "decision": "allow"},
        {"pattern": "Bash(git *)", "decision": "ask"},
    ]}
    assert decide("Bash", ["git", "status"], rules) == "ask"


def test_default_when_no_match():
    """没有命中任何规则时返回默认策略。"""
    rules = {"default": "deny", "entries": [{"pattern": "Read(src/**)", "decision": "allow"}]}
    assert decide("Write", {"path": "tmp/a.txt"}, rules) == "deny"
''',
        hidden=r'''def test_dict_args_use_command_or_path():
    """字典参数优先使用 command/cmd/path 字段匹配。"""
    rules = {"default": "ask", "entries": [{"pattern": "Bash(pytest *)", "decision": "allow"}]}
    assert decide("Bash", {"command": "pytest tests"}, rules) == "allow"


def test_invalid_rules_are_ignored():
    """非法规则不会影响其他规则和默认值。"""
    rules = {"default": "allow", "entries": [
        {"pattern": "Broken", "decision": "deny"},
        {"pattern": "Read(secret/**)", "decision": "deny"},
        {"pattern": "Read(*)", "decision": "maybe"},
    ]}
    assert decide("Read", "secret/token.txt", rules) == "deny"
    assert decide("Read", "docs/a.md", rules) == "allow"


def test_missing_default_falls_back_to_ask():
    """缺少 default 时使用 ask。"""
    assert decide("Bash", "python build.py", {"entries": []}) == "ask"
''',
        solution=r'''def decide(tool, args, rules):
    """根据工具名、参数和权限规则返回 allow / ask / deny。"""
    import fnmatch
    import re

    precedence = {"allow": 1, "ask": 2, "deny": 3}

    def arg_text(value):
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            return " ".join(str(x) for x in value)
        if isinstance(value, dict):
            for key in ("cmd", "command", "path"):
                if key in value:
                    return str(value[key])
            return " ".join("%s=%s" % (k, value[k]) for k in sorted(value))
        return str(value)

    text = arg_text(args)
    best = None
    entries = rules.get("entries", []) if isinstance(rules, dict) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        decision = entry.get("decision")
        if decision not in precedence:
            continue
        pattern = entry.get("pattern", "")
        match = re.fullmatch(r"\s*([A-Za-z_][\w]*)\s*\((.*)\)\s*", pattern)
        if not match:
            continue
        rule_tool, arg_pattern = match.group(1), match.group(2)
        if rule_tool != tool:
            continue
        if fnmatch.fnmatchcase(text, arg_pattern):
            if best is None or precedence[decision] > precedence[best]:
                best = decision
    if best is not None:
        return best
    default = rules.get("default", "ask") if isinstance(rules, dict) else "ask"
    return default if default in precedence else "ask"
''',
        hints=["先把 args 统一成字符串，再做规则匹配。", "用 fnmatch.fnmatchcase 处理通配符，自己只需要解析 Tool(pattern) 外壳。", "不要按规则顺序直接返回；必须收集命中结果后按 deny > ask > allow 决策。"],
        points=["权限规则建模", "通配符匹配", "优先级合并", "安全默认策略"],
        numpy=False,
    ),
    dict(
        id="lab-hooks",
        course="harness",
        title="工具调用钩子管线",
        level="medium",
        desc=r'''### 背景
成熟的 Agent Harness 不会直接把工具调用发出去，而是在调用前后提供钩子：PreToolUse 可以做审计、补全参数、拦截危险操作；PostToolUse 可以改写结果、脱敏输出或追加指标。工程中最容易出错的地方是钩子顺序、可变参数传递、异常处理和拦截语义。本题要求你实现一个小而完整的管线，让调用主流程可预测、可观测，并且不会因为某个钩子的 bug 让整个工具执行崩溃。

### 要实现什么
实现 `run_with_hooks(tool_fn, args, pre_hooks=None, post_hooks=None)`。`tool_fn` 是接收关键字参数的函数，`args` 是参数字典。Pre 钩子按注册顺序执行，签名为 `hook(context)`；`context` 至少包含 `args`、`errors`。Pre 返回 `{"args": new_args}` 时替换参数，返回 `{"block": "原因"}` 时拦截并不调用工具。Post 钩子在工具成功后按注册顺序执行，返回 `{"result": new_result}` 时改写结果。任何钩子抛异常都不能让主流程崩溃，但要把异常信息记录到 `errors`。

### 例子
一个 Pre 钩子把 `{"path":"a"}` 改成 `{"path":"safe/a"}`，工具实际收到新路径。另一个 Pre 钩子返回 `{"block":"danger"}`，最终返回结构里 `ok` 为 `False`，`blocked` 为 `danger`，且工具不会被调用。

### 约束
只能使用标准库。返回字典应包含 `ok`、`result`、`blocked`、`errors`、`args`。工具自身抛异常时可以继续抛出，不要求吞掉；本题重点是钩子异常隔离。不要使用全局变量记录状态，测试会多次调用函数。''',
        starter=r'''def run_with_hooks(tool_fn, args, pre_hooks=None, post_hooks=None):
    """执行带 PreToolUse / PostToolUse 钩子的工具调用管线。"""
    raise NotImplementedError
''',
        tests=r'''def test_pre_hook_can_modify_args():
    """Pre 钩子可以修改工具参数。"""
    def tool(path):
        return path
    def prefix(ctx):
        return {"args": {"path": "safe/" + ctx["args"]["path"]}}
    got = run_with_hooks(tool, {"path": "a.txt"}, pre_hooks=[prefix])
    assert got["ok"] is True, got
    assert got["result"] == "safe/a.txt" and got["args"] == {"path": "safe/a.txt"}, got


def test_pre_hook_can_block_call():
    """Pre 钩子可以拦截并阻止工具执行。"""
    called = []
    def tool():
        called.append(True)
        return "done"
    def block(ctx):
        return {"block": "danger"}
    got = run_with_hooks(tool, {}, pre_hooks=[block])
    assert got["ok"] is False and got["blocked"] == "danger", got
    assert called == [], called


def test_post_hook_can_rewrite_result():
    """Post 钩子可以按顺序改写结果。"""
    def tool(x):
        return x + 1
    def double(ctx):
        return {"result": ctx["result"] * 2}
    got = run_with_hooks(tool, {"x": 2}, post_hooks=[double])
    assert got["ok"] is True and got["result"] == 6, got


def test_hook_exception_is_recorded():
    """钩子异常会记录但不会让主流程崩溃。"""
    def tool():
        return "ok"
    def bad(ctx):
        raise RuntimeError("boom")
    got = run_with_hooks(tool, {}, pre_hooks=[bad])
    assert got["ok"] is True and got["result"] == "ok", got
    assert got["errors"] and "boom" in got["errors"][0], got
''',
        hidden=r'''def test_hooks_run_in_registration_order():
    """多个钩子按注册顺序执行。"""
    order = []
    def tool(x):
        order.append("tool")
        return x
    def p1(ctx):
        order.append("p1")
        return {"args": {"x": ctx["args"]["x"] + "1"}}
    def p2(ctx):
        order.append("p2")
        return {"args": {"x": ctx["args"]["x"] + "2"}}
    def q(ctx):
        order.append("post")
        return {"result": ctx["result"] + "3"}
    got = run_with_hooks(tool, {"x": ""}, [p1, p2], [q])
    assert got["result"] == "123", got
    assert order == ["p1", "p2", "tool", "post"], order


def test_post_exception_keeps_current_result():
    """Post 钩子异常时保留当前结果并记录错误。"""
    def tool():
        return "raw"
    def bad(ctx):
        raise ValueError("post failed")
    got = run_with_hooks(tool, {}, post_hooks=[bad])
    assert got["result"] == "raw" and got["ok"] is True, got
    assert any("post failed" in e for e in got["errors"]), got
''',
        solution=r'''def run_with_hooks(tool_fn, args, pre_hooks=None, post_hooks=None):
    """执行带 PreToolUse / PostToolUse 钩子的工具调用管线。"""
    pre_hooks = list(pre_hooks or [])
    post_hooks = list(post_hooks or [])
    current_args = dict(args or {})
    errors = []
    context = {"args": current_args, "errors": errors}

    for hook in pre_hooks:
        try:
            update = hook(context)
        except Exception as exc:
            errors.append("PreToolUse %s: %s" % (type(exc).__name__, exc))
            continue
        if isinstance(update, dict) and update.get("block"):
            return {"ok": False, "result": None, "blocked": str(update["block"]), "errors": errors, "args": dict(current_args)}
        if isinstance(update, dict) and "args" in update:
            current_args = dict(update["args"])
            context["args"] = current_args

    result = tool_fn(**current_args)
    context["result"] = result
    for hook in post_hooks:
        try:
            update = hook(context)
        except Exception as exc:
            errors.append("PostToolUse %s: %s" % (type(exc).__name__, exc))
            continue
        if isinstance(update, dict) and "result" in update:
            result = update["result"]
            context["result"] = result
    return {"ok": True, "result": result, "blocked": None, "errors": errors, "args": dict(current_args)}
''',
        hints=["把 args、result、errors 放到同一个 context 里传给钩子。", "Pre 的 block 要立刻返回，且不能调用 tool_fn。", "钩子异常只记录，Post 异常不能丢掉已经得到的 result。"],
        points=["钩子管线语义", "拦截与参数改写", "异常隔离", "执行顺序保证"],
        numpy=False,
    ),
    dict(
        id="lab-passk",
        course="agent",
        title="pass@k 无偏估计与结果汇总",
        level="medium",
        desc=r'''### 背景
评估代码生成 Agent 时，经常让模型对同一道题采样 n 个候选，其中 c 个能通过测试，然后报告 pass@k。很多人会把 pass@k 错写成“前 k 个里是否有成功”或 `c/n`，这会让不同采样数的结果不可比较。真实评测通常使用无偏估计：从 n 个候选中不放回抽 k 个，至少抽到一个正确答案的概率。本题还要求按标签汇总成功率和平均轮数，贴近面试与日常评测报表。

### 要实现什么
实现 `pass_at_k(n, c, k)` 和 `summarize(results)`。`pass_at_k` 返回浮点数：当 `c==0` 返回 0；当 `n-c < k` 返回 1；否则用数值稳定的乘积公式计算 `1 - C(n-c,k)/C(n,k)`，不要直接计算巨大组合数。`summarize(results)` 接收若干字典，每条至少包含 `label`、`passed`、`rounds`，返回按 label 汇总的字典，每个 label 下包含 `total`、`success`、`success_rate`、`avg_rounds`，并额外包含 `__all__` 总计。

### 例子
`pass_at_k(10, 2, 1)` 为 `0.2`；`pass_at_k(10, 2, 5)` 是至少抽中一个成功样本的概率。`summarize([{"label":"easy","passed":True,"rounds":2}])` 中 easy 的成功率为 1。

### 约束
只能使用标准库。`n`、`c`、`k` 必须满足 `n>=0`、`0<=c<=n`、`k>=1`，否则抛 `ValueError`。`k>n` 可理解为抽取全部候选。汇总时缺失 rounds 的记录按 0 轮处理。''',
        starter=r'''def pass_at_k(n, c, k):
    """计算代码生成评测里的 pass@k 无偏估计。"""
    raise NotImplementedError


def summarize(results):
    """按标签汇总成功率和平均轮数，并返回 __all__ 总计。"""
    raise NotImplementedError
''',
        tests=r'''def test_pass_at_1_equals_success_ratio():
    """k=1 时 pass@k 等于成功样本占比。"""
    got = pass_at_k(10, 2, 1)
    assert abs(got - 0.2) < 1e-12, got


def test_pass_at_k_without_combination_overflow():
    """较大 n 时仍能稳定计算。"""
    got = pass_at_k(1000, 3, 10)
    assert 0.0 < got < 1.0, got
    assert abs(got - 0.02973045189478052) < 1e-12, got


def test_pass_at_k_returns_one_when_sampling_enough():
    """k 覆盖所有失败以外样本时结果为 1。"""
    assert pass_at_k(5, 2, 4) == 1.0


def test_summarize_by_label_and_all():
    """summarize 同时给出标签和总体统计。"""
    data = [
        {"label": "easy", "passed": True, "rounds": 1},
        {"label": "easy", "passed": False, "rounds": 3},
        {"label": "hard", "passed": True, "rounds": 2},
    ]
    got = summarize(data)
    assert got["easy"]["total"] == 2 and got["easy"]["success"] == 1, got
    assert got["easy"]["success_rate"] == 0.5, got
    assert got["__all__"]["total"] == 3 and got["__all__"]["success"] == 2, got
''',
        hidden=r'''def test_invalid_inputs_raise_value_error():
    """非法 n/c/k 会抛 ValueError。"""
    for args in [(0, 0, 1), (3, 4, 1), (3, 1, 0), (-1, 0, 1)]:
        try:
            pass_at_k(*args)
        except ValueError:
            pass
        else:
            assert False, "expected ValueError for %r" % (args,)


def test_zero_success_is_zero_even_if_k_large():
    """没有成功样本时 pass@k 为 0。"""
    assert pass_at_k(5, 0, 10) == 0.0


def test_summarize_empty_results():
    """空结果也返回 __all__ 零统计。"""
    got = summarize([])
    assert got == {"__all__": {"total": 0, "success": 0, "success_rate": 0.0, "avg_rounds": 0.0}}, got
''',
        solution=r'''def pass_at_k(n, c, k):
    """计算代码生成评测里的 pass@k 无偏估计。"""
    if n <= 0 or c < 0 or c > n or k <= 0:
        raise ValueError("require n > 0, 0 <= c <= n and k >= 1")
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    product = 1.0
    for i in range(n - c + 1, n + 1):
        product *= 1.0 - k / i
    return 1.0 - product


def summarize(results):
    """按标签汇总成功率和平均轮数，并返回 __all__ 总计。"""
    buckets = {"__all__": {"total": 0, "success": 0, "round_sum": 0.0}}
    for row in results:
        label = row.get("label", "unknown")
        for key in (label, "__all__"):
            buckets.setdefault(key, {"total": 0, "success": 0, "round_sum": 0.0})
            buckets[key]["total"] += 1
            buckets[key]["success"] += 1 if row.get("passed") else 0
            buckets[key]["round_sum"] += float(row.get("rounds", 0) or 0)
    out = {}
    for key, item in buckets.items():
        total = item["total"]
        out[key] = {
            "total": total,
            "success": item["success"],
            "success_rate": item["success"] / total if total else 0.0,
            "avg_rounds": item["round_sum"] / total if total else 0.0,
        }
    return out
''',
        hints=["pass@k 是“不放回抽 k 个至少一个成功”的概率，不是 top-k accuracy。", "用乘积公式避免直接算巨大组合数。", "汇总时先累加 total/success/round_sum，最后再计算 rate 和 average。"],
        points=["代码生成评估指标", "数值稳定组合概率", "分组聚合", "边界输入校验"],
        numpy=False,
    ),
    dict(
        id="lab-judge-agreement",
        course="dev",
        title="评审结果一致性指标",
        level="medium",
        desc=r'''### 背景
在 AI 应用开发中，经常用 LLM 评审器判断回答是否合格，但上线前必须和人工标注对齐。只看准确率很容易误导：如果数据里 95% 都是 pass，一个总是预测 pass 的评审器也有 95% 准确率。Cohen's kappa 可以扣除随机一致性，更适合衡量评审器是否真正学到了人工标准。面试官会关注你是否能正确构造混淆矩阵、处理类别缺失，并在边界场景给出稳定结果。

### 要实现什么
实现 `judge_agreement(items)`。`items` 是列表，每项包含 `human` 和 `llm` 两个标签。返回字典：`accuracy` 为准确率，`confusion_matrix` 是嵌套字典 `matrix[human_label][llm_label] = count`，`kappa` 为 Cohen's kappa，`labels` 为排序后的标签列表。标签可以是字符串、数字或布尔值；输出矩阵里的键保留原标签。空输入时返回准确率 0、kappa 0、空矩阵和空标签。

### 例子
三条样本里两条一致，则 accuracy 为 `2/3`。如果人工和 LLM 都只有同一个类别且全部一致，kappa 定义为 1；如果期望一致率分母为 0 但并非完全一致，返回 0。

### 约束
只能使用标准库。不要依赖 pandas 或 sklearn。kappa 公式为 `(po - pe) / (1 - pe)`，其中 `po` 是观测一致率，`pe` 是按人工边际分布和 LLM 边际分布计算的随机一致率。排序标签时不同类型要用 `repr` 或字符串键保证确定性。''',
        starter=r'''def judge_agreement(items):
    """计算 LLM 评审与人工标注的一致性指标。"""
    raise NotImplementedError
''',
        tests=r'''def test_accuracy_and_confusion_matrix():
    """能计算准确率和混淆矩阵。"""
    items = [{"human": "pass", "llm": "pass"}, {"human": "fail", "llm": "pass"}, {"human": "fail", "llm": "fail"}]
    got = judge_agreement(items)
    assert abs(got["accuracy"] - 2 / 3) < 1e-12, got
    assert got["confusion_matrix"]["fail"]["pass"] == 1, got
    assert got["confusion_matrix"]["pass"]["pass"] == 1, got


def test_kappa_for_perfect_single_class_is_one():
    """只有一个类别且全部一致时 kappa 为 1。"""
    got = judge_agreement([{"human": "ok", "llm": "ok"}, {"human": "ok", "llm": "ok"}])
    assert got["accuracy"] == 1.0, got
    assert got["kappa"] == 1.0, got


def test_empty_input_returns_zero_metrics():
    """空输入返回零指标而不是报错。"""
    got = judge_agreement([])
    assert got == {"accuracy": 0.0, "confusion_matrix": {}, "kappa": 0.0, "labels": []}, got


def test_kappa_not_same_as_accuracy():
    """类别分布不均衡时 kappa 与 accuracy 不一定相同。"""
    items = [{"human": "yes", "llm": "yes"}, {"human": "yes", "llm": "yes"}, {"human": "no", "llm": "yes"}, {"human": "no", "llm": "no"}]
    got = judge_agreement(items)
    assert got["accuracy"] == 0.75, got
    assert abs(got["kappa"] - 0.5) < 1e-12, got
''',
        hidden=r'''def test_labels_include_llm_only_category():
    """只出现在 LLM 预测里的类别也要进入标签和矩阵列。"""
    got = judge_agreement([{"human": "a", "llm": "b"}])
    assert set(got["labels"]) == {"a", "b"}, got
    assert got["confusion_matrix"]["a"]["b"] == 1, got
    assert got["confusion_matrix"]["b"]["a"] == 0, got


def test_mixed_label_types_are_supported():
    """不同类型标签也能确定性排序和计数。"""
    got = judge_agreement([{"human": True, "llm": True}, {"human": 0, "llm": True}])
    assert got["confusion_matrix"][True][True] == 1, got
    assert got["confusion_matrix"][0][True] == 1, got
    assert len(got["labels"]) == 2, got
''',
        solution=r'''def judge_agreement(items):
    """计算 LLM 评审与人工标注的一致性指标。"""
    n = len(items)
    if n == 0:
        return {"accuracy": 0.0, "confusion_matrix": {}, "kappa": 0.0, "labels": []}
    labels = []
    seen = set()
    for item in items:
        for value in (item.get("human"), item.get("llm")):
            key = (type(value).__name__, repr(value))
            if key not in seen:
                seen.add(key)
                labels.append(value)
    labels.sort(key=lambda x: (type(x).__name__, repr(x)))
    matrix = {h: {l: 0 for l in labels} for h in labels}
    human_counts = {l: 0 for l in labels}
    llm_counts = {l: 0 for l in labels}
    agree = 0
    for item in items:
        human = item.get("human")
        llm = item.get("llm")
        matrix[human][llm] += 1
        human_counts[human] += 1
        llm_counts[llm] += 1
        if human == llm:
            agree += 1
    po = agree / n
    pe = sum(human_counts[label] * llm_counts[label] for label in labels) / (n * n)
    if abs(1.0 - pe) < 1e-15:
        kappa = 1.0 if abs(po - 1.0) < 1e-15 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)
    return {"accuracy": po, "confusion_matrix": matrix, "kappa": kappa, "labels": labels}
''',
        hints=["先收集 human 和 llm 两侧出现过的所有标签。", "混淆矩阵的行是人工标签，列是 LLM 标签，缺失组合也填 0。", "kappa 的 pe 来自两个边际分布；pe 等于 1 时要单独处理。"],
        points=["评审器离线评估", "混淆矩阵构造", "Cohen's kappa", "单类别边界处理"],
        numpy=False,
    ),
    dict(
        id="lab-prefix-cache",
        course="harness",
        title="Prompt 前缀缓存命中计算",
        level="medium",
        desc=r'''### 背景
大模型服务常按固定 token 块缓存 prompt 前缀：如果本次请求和历史请求的开头完全一致，就可以复用已经计算过的 KV 前缀，降低延迟和成本。但缓存命中通常要求块对齐，例如块大小为 4 时，即使前 6 个 token 相同，也只能复用前 4 个。本题模拟 Harness 里的前缀缓存计算，考察你是否理解“最长公共前缀”和“块对齐”这两个概念，以及如何在多个历史请求中选择最长命中。

### 要实现什么
实现 `reusable_prefix_len(prev_tokens, tokens, block_size)` 和类 `PrefixCache(block_size)`。函数返回两个 token 列表的可复用前缀长度：先计算最长公共前缀，再向下取整到 `block_size` 的倍数。`PrefixCache` 需要提供 `add(tokens, value=None)` 保存历史请求，以及 `match(tokens)` 在所有历史请求中找最长命中，返回 `{"length": 命中长度, "value": 对应value}`；没有任何块级命中时长度为 0，value 为 `None`。

### 例子
`reusable_prefix_len([1,2,3,4,5], [1,2,3,4,9], 4)` 返回 4；块大小为 4 时，公共前缀只有 3 个 token 则返回 0。若缓存里有 `[1,2,3,4]` 和 `[1,2,3,4,5,6,7,8]`，查询第二种前缀应返回长度 8。

### 约束
只能使用标准库。tokens 可以是字符串或数字组成的列表，比较使用 Python 的相等语义。`block_size` 必须大于 0，否则抛 `ValueError`。缓存不要求淘汰策略，但多个历史命中长度相同可返回任意一个对应 value。''',
        starter=r'''def reusable_prefix_len(prev_tokens, tokens, block_size):
    """返回两个 token 序列按块对齐后可复用的公共前缀长度。"""
    raise NotImplementedError


class PrefixCache:
    """保存多个历史请求，并返回最长块对齐前缀命中。"""
    def __init__(self, block_size):
        raise NotImplementedError

    def add(self, tokens, value=None):
        raise NotImplementedError

    def match(self, tokens):
        raise NotImplementedError
''',
        tests=r'''def test_reusable_prefix_is_block_aligned():
    """公共前缀长度会向下对齐到块大小。"""
    assert reusable_prefix_len([1, 2, 3, 4, 5], [1, 2, 3, 4, 9], 4) == 4
    assert reusable_prefix_len([1, 2, 3], [1, 2, 3], 4) == 0


def test_reusable_prefix_stops_at_first_difference():
    """遇到第一个不同 token 后不能继续复用。"""
    got = reusable_prefix_len(["a", "b", "x", "d"], ["a", "b", "c", "d"], 2)
    assert got == 2, got


def test_cache_returns_longest_history_hit():
    """多个历史请求中取最长命中。"""
    cache = PrefixCache(block_size=2)
    cache.add([1, 2, 9, 9], value="short")
    cache.add([1, 2, 3, 4, 5], value="long")
    got = cache.match([1, 2, 3, 4, 8])
    assert got == {"length": 4, "value": "long"}, got


def test_cache_no_block_hit():
    """没有块级命中时返回长度 0 和空值。"""
    cache = PrefixCache(4)
    cache.add([1, 2, 3], value="too-short")
    assert cache.match([1, 2, 3]) == {"length": 0, "value": None}
''',
        hidden=r'''def test_invalid_block_size_raises():
    """块大小必须大于 0。"""
    try:
        reusable_prefix_len([1], [1], 0)
    except ValueError:
        pass
    else:
        assert False, "expected ValueError"


def test_cache_copies_tokens_on_add():
    """添加后修改原列表不应污染缓存。"""
    tokens = ["a", "b", "c", "d"]
    cache = PrefixCache(2)
    cache.add(tokens, value="v")
    tokens[0] = "x"
    assert cache.match(["a", "b", "z"])["length"] == 2


def test_full_exact_match():
    """完全相同时也只返回块对齐长度。"""
    assert reusable_prefix_len([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], 2) == 4
''',
        solution=r'''def reusable_prefix_len(prev_tokens, tokens, block_size):
    """返回两个 token 序列按块对齐后可复用的公共前缀长度。"""
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    limit = min(len(prev_tokens), len(tokens))
    i = 0
    while i < limit and prev_tokens[i] == tokens[i]:
        i += 1
    return (i // block_size) * block_size


class PrefixCache:
    """保存多个历史请求，并返回最长块对齐前缀命中。"""
    def __init__(self, block_size):
        if block_size <= 0:
            raise ValueError("block_size must be positive")
        self.block_size = block_size
        self._items = []

    def add(self, tokens, value=None):
        self._items.append((list(tokens), value))

    def match(self, tokens):
        best_len = 0
        best_value = None
        query = list(tokens)
        for cached, value in self._items:
            length = reusable_prefix_len(cached, query, self.block_size)
            if length > best_len:
                best_len = length
                best_value = value
        return {"length": best_len, "value": best_value if best_len else None}
''',
        hints=["最长公共前缀要逐 token 比较，不能用集合或子串。", "命中长度必须向下取整到 block_size 的倍数。", "缓存匹配时遍历所有历史请求，保留 length 最大的那一个。"],
        points=["KV 前缀缓存语义", "块对齐计算", "多历史最长命中", "输入复制防污染"],
        numpy=False,
    ),
    dict(
        id="lab-ttl-lru",
        course="arch",
        title="带 TTL 的 LRU 缓存",
        level="medium",
        desc=r'''### 背景
AI 应用里常缓存模型配置、工具 schema、检索结果或短期会话状态。只做 LRU 会留下过期数据，只做 TTL 又可能在高流量下占满内存，因此工程里经常需要 TTL + LRU 的组合：先删除过期项，再按最近最少使用淘汰。面试官会看你是否能用可注入时钟写出确定性测试，是否能在 get、put、更新已有 key 时维护访问顺序，并正确统计命中率。

### 要实现什么
实现 `TTLLRUCache(capacity, ttl, clock)`。`capacity` 是最大条目数，`ttl` 是每条记录的存活秒数，`clock` 是无参函数，返回当前时间。方法：`put(key, value)` 写入或更新；`get(key)` 命中且未过期时返回 value，并刷新最近使用顺序；未命中或过期返回 `None`；`stats()` 返回 `{"hits": h, "misses": m, "hit_rate": rate}`。过期判断使用 `clock() >= expires_at`。

### 例子
容量 2 时依次 `put("a",1)`、`put("b",2)`、`get("a")`、`put("c",3)`，应淘汰 `b`。若 ttl 为 10，写入时刻为 0，在时刻 10 读取应视为过期。

### 约束
只能使用标准库。可以使用 `collections.OrderedDict`。`capacity<=0` 时缓存不保存任何数据，但统计仍然有效。每次 `get` 和 `put` 前应先清理过期项，避免过期项占用容量。不要使用真实时间，测试会传入 fake clock。''',
        starter=r'''class TTLLRUCache:
    """带 TTL 的 LRU 缓存。"""
    def __init__(self, capacity, ttl, clock):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def put(self, key, value):
        raise NotImplementedError

    def stats(self):
        raise NotImplementedError
''',
        tests=r'''def test_get_put_and_hit_rate():
    """基本 get/put 和命中率统计正确。"""
    now = [0]
    cache = TTLLRUCache(2, ttl=10, clock=lambda: now[0])
    cache.put("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None
    stats = cache.stats()
    assert stats["hits"] == 1 and stats["misses"] == 1, stats
    assert stats["hit_rate"] == 0.5, stats


def test_capacity_evicts_least_recently_used():
    """容量满时淘汰最近最少使用项。"""
    now = [0]
    cache = TTLLRUCache(2, 100, lambda: now[0])
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1 and cache.get("c") == 3


def test_expired_item_is_miss():
    """到达过期时间后读取返回 None。"""
    now = [0]
    cache = TTLLRUCache(2, 5, lambda: now[0])
    cache.put("a", 1)
    now[0] = 5
    assert cache.get("a") is None


def test_update_existing_refreshes_value_and_order():
    """更新已有 key 会刷新值和最近使用顺序。"""
    now = [0]
    cache = TTLLRUCache(2, 100, lambda: now[0])
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)
    cache.put("c", 3)
    assert cache.get("a") == 10
    assert cache.get("b") is None
''',
        hidden=r'''def test_expired_items_do_not_consume_capacity():
    """put 前清理过期项，避免误淘汰未过期项。"""
    now = [0]
    cache = TTLLRUCache(2, 5, lambda: now[0])
    cache.put("a", 1)
    cache.put("b", 2)
    now[0] = 6
    cache.put("c", 3)
    assert cache.get("c") == 3
    assert cache.get("a") is None and cache.get("b") is None


def test_zero_capacity_never_stores():
    """容量为 0 时不保存任何值。"""
    cache = TTLLRUCache(0, 10, lambda: 0)
    cache.put("a", 1)
    assert cache.get("a") is None


def test_stats_before_any_get():
    """没有读取时命中率为 0。"""
    cache = TTLLRUCache(1, 10, lambda: 0)
    assert cache.stats() == {"hits": 0, "misses": 0, "hit_rate": 0.0}
''',
        solution=r'''class TTLLRUCache:
    """带 TTL 的 LRU 缓存。"""
    def __init__(self, capacity, ttl, clock):
        from collections import OrderedDict
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock
        self._data = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _purge_expired(self):
        now = self.clock()
        expired = [key for key, (_, expires_at) in self._data.items() if now >= expires_at]
        for key in expired:
            self._data.pop(key, None)

    def get(self, key):
        self._purge_expired()
        if key not in self._data:
            self.misses += 1
            return None
        value, expires_at = self._data.pop(key)
        if self.clock() >= expires_at:
            self.misses += 1
            return None
        self._data[key] = (value, expires_at)
        self.hits += 1
        return value

    def put(self, key, value):
        self._purge_expired()
        if self.capacity <= 0:
            self._data.clear()
            return
        if key in self._data:
            self._data.pop(key)
        self._data[key] = (value, self.clock() + self.ttl)
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def stats(self):
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses, "hit_rate": self.hits / total if total else 0.0}
''',
        hints=["OrderedDict 的左侧可以表示最久未使用，右侧表示最近使用。", "get 命中后要 pop 再插回去，刷新 LRU 顺序。", "每次操作前清理过期项，过期判断是 now >= expires_at。"],
        points=["缓存淘汰策略", "TTL 与 LRU 组合", "可注入时钟", "命中率统计"],
        numpy=False,
    ),
    dict(
        id="lab-sse-parser",
        course="dev",
        title="解析流式 SSE 增量输出",
        level="hard",
        desc=r'''### 背景
很多大模型 API 使用 SSE 返回流式结果：每个事件里有一段 `data:` JSON，JSON 中的 `delta.content` 逐步拼接成文本，工具调用的函数名和参数也可能被拆成多个片段。网络层还会把任意位置切断，不能假设一次 `feed` 就拿到完整事件。面试官会用这题考察你是否理解流式协议、缓冲区和增量状态，而不是只会对完整字符串 `split("\n\n")`。

### 要实现什么
实现类 `SSEParser`，提供 `feed(chunk)` 方法。`chunk` 是新收到的字符串片段，方法返回当前快照字典：`{"content": str, "tool_calls": list, "done": bool, "finish_reason": str|None}`。解析 SSE 事件时，只处理 `data:` 行；一个事件以空行结束；`data: [DONE]` 表示结束。普通 JSON 事件结构参考 Chat Completions：`choices[0].delta.content` 追加到 content；`choices[0].delta.tool_calls` 按 `index` 聚合，每个 tool_call 拼接 `function.name` 和 `function.arguments`；`finish_reason` 出现时保存。

### 例子
先 feed 半段 `data: {"choices":[{"delta":{"content":"你"` 不应输出错误，直到后续 chunk 补齐空行才更新 content。工具调用参数可能分成 `{"city"` 和 `:"Beijing"}` 两段，要拼接成完整 arguments 字符串。

### 约束
只能使用标准库。忽略注释行和无法识别的非 data 行。JSON 解析失败的完整事件应记录到 `errors` 属性或快照中的 `errors`，但不能导致解析器崩溃。`feed` 可能被调用多次，必须保留内部缓冲区和已解析状态。''',
        starter=r'''class SSEParser:
    """增量解析 SSE，并拼接模型文本与工具调用片段。"""
    def __init__(self):
        raise NotImplementedError

    def feed(self, chunk):
        raise NotImplementedError
''',
        tests=r'''def test_content_split_across_chunks():
    """任意切断的 chunk 最终能拼接 content。"""
    parser = SSEParser()
    part1 = 'data: {"choices":[{"delta":{"content":"你"}}]}'
    assert parser.feed(part1)["content"] == ""
    snap = parser.feed('\n\ndata: {"choices":[{"delta":{"content":"好"}}]}\n\n')
    assert snap["content"] == "你好", snap


def test_done_marker_sets_done():
    """data: [DONE] 会标记流结束。"""
    parser = SSEParser()
    snap = parser.feed("data: [DONE]\n\n")
    assert snap["done"] is True, snap


def test_finish_reason_is_recorded():
    """finish_reason 出现时会保存。"""
    parser = SSEParser()
    snap = parser.feed('data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n')
    assert snap["finish_reason"] == "stop", snap


def test_tool_call_fragments_are_joined_by_index():
    """tool_calls 的 name 和 arguments 会按 index 拼接。"""
    parser = SSEParser()
    parser.feed('data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"sea","arguments":"{\\\"q\\\""}}]}}]}\n\n')
    snap = parser.feed('data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"rch","arguments":":\\\"x\\\"}"}}]}}]}\n\n')
    assert snap["tool_calls"][0]["function"]["name"] == "search", snap
    assert snap["tool_calls"][0]["function"]["arguments"] == '{"q":"x"}', snap
''',
        hidden=r'''def test_multiline_data_event():
    """一个事件的多行 data 会合并后解析。"""
    parser = SSEParser()
    event = 'data: {"choices":[{"delta":{"content":"A"}}]}\n' + 'data: \n\n'
    snap = parser.feed(event)
    assert snap["content"] == "A", snap


def test_invalid_json_is_recorded_not_raised():
    """完整事件 JSON 非法时记录错误但不抛异常。"""
    parser = SSEParser()
    snap = parser.feed("data: {bad}\n\n")
    assert snap["content"] == "", snap
    assert snap["errors"], snap


def test_multiple_tool_indexes_are_kept_separate():
    """不同 index 的 tool_call 不会互相串。"""
    parser = SSEParser()
    payload = 'data: {"choices":[{"delta":{"tool_calls":[{"index":1,"function":{"name":"b","arguments":"2"}},{"index":0,"function":{"name":"a","arguments":"1"}}]}}]}\n\n'
    snap = parser.feed(payload)
    assert [c["index"] for c in snap["tool_calls"]] == [0, 1], snap
    assert snap["tool_calls"][0]["function"]["arguments"] == "1", snap
    assert snap["tool_calls"][1]["function"]["arguments"] == "2", snap
''',
        solution=r'''class SSEParser:
    """增量解析 SSE，并拼接模型文本与工具调用片段。"""
    def __init__(self):
        self.buffer = ""
        self.content = ""
        self.tool_calls = {}
        self.done = False
        self.finish_reason = None
        self.errors = []

    def _snapshot(self):
        calls = []
        for index in sorted(self.tool_calls):
            call = self.tool_calls[index]
            calls.append({"index": index, "function": {"name": call["name"], "arguments": call["arguments"]}})
        return {"content": self.content, "tool_calls": calls, "done": self.done, "finish_reason": self.finish_reason, "errors": list(self.errors)}

    def _handle_event(self, event):
        import json
        data_lines = []
        for raw_line in event.splitlines():
            line = raw_line.rstrip("\r")
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                value = line[5:]
                if value.startswith(" "):
                    value = value[1:]
                data_lines.append(value)
        if not data_lines:
            return
        data = "\n".join(data_lines).strip()
        if data == "[DONE]":
            self.done = True
            return
        try:
            payload = json.loads(data)
        except Exception as exc:
            self.errors.append(str(exc))
            return
        for choice in payload.get("choices", []):
            if choice.get("finish_reason") is not None:
                self.finish_reason = choice.get("finish_reason")
            delta = choice.get("delta") or {}
            if delta.get("content"):
                self.content += delta["content"]
            for item in delta.get("tool_calls", []) or []:
                index = item.get("index", 0)
                current = self.tool_calls.setdefault(index, {"name": "", "arguments": ""})
                function = item.get("function") or {}
                current["name"] += function.get("name") or ""
                current["arguments"] += function.get("arguments") or ""

    def feed(self, chunk):
        self.buffer += chunk
        while True:
            marker = self.buffer.find("\n\n")
            if marker == -1:
                break
            event = self.buffer[:marker]
            self.buffer = self.buffer[marker + 2:]
            self._handle_event(event)
        return self._snapshot()
''',
        hints=["维护一个字符串 buffer，只有遇到空行才处理完整事件。", "SSE 事件里可能有多行 data，需要先合并再 json.loads。", "tool_calls 要用 index 分桶，name 和 arguments 都是增量字符串。"],
        points=["SSE 协议解析", "流式缓冲区", "增量文本拼接", "工具调用分片聚合"],
        numpy=False,
    ),
    dict(
        id="lab-dag-runner",
        course="arch",
        title="任务 DAG 分层执行与失败传播",
        level="hard",
        desc=r'''### 背景
复杂 Agent 工作流常被拆成多个任务节点：检索、规划、工具调用、评审、报告生成等。没有依赖关系的节点可以并行，有依赖关系的节点必须等待上游完成。架构面试里，DAG Runner 是高频手写题，因为它同时考察拓扑排序、环检测、执行状态传播和错误隔离。尤其在自动化系统里，一个任务失败后，下游任务不能继续拿着无效输入运行，而应标记为 skipped。

### 要实现什么
实现 `topological_layers(deps)` 和 `run_dag(tasks, deps)`。`deps` 是字典 `node -> [dependency_node, ...]`，返回的拓扑层是列表的列表，同一层节点可并行；节点顺序要求确定性，按字符串排序。若存在环，抛出 `CycleError`，异常对象包含 `nodes` 属性，列出环上的节点。`tasks` 是 `node -> callable`，`run_dag` 按层执行：上游都成功时调用任务；任务返回值写入 results；任务抛异常则该节点状态为 failed；任何依赖 failed 或 skipped 的节点状态为 skipped。

### 例子
依赖 `{"b":["a"], "c":["a"], "d":["b","c"]}` 的层为 `[["a"], ["b", "c"], ["d"]]`。如果 `b` 失败，则 `d` skipped，但 `c` 仍可成功执行。

### 约束
只能使用标准库。`deps` 里只作为依赖出现的节点也要纳入图。`tasks` 中没有对应 callable 的节点可以使用默认空任务，返回 `None`。不要真的并发执行；本题只要求计算可并行层并按层顺序执行。错误信息保存为字符串即可。''',
        starter=r'''class CycleError(Exception):
    """DAG 中存在环。"""
    pass


def topological_layers(deps):
    """把 DAG 依赖关系分成可并行执行的拓扑层。"""
    raise NotImplementedError


def run_dag(tasks, deps):
    """按拓扑层执行任务，失败时跳过下游。"""
    raise NotImplementedError
''',
        tests=r'''def test_topological_layers_basic():
    """拓扑分层会把同层可并行节点放在一起。"""
    deps = {"b": ["a"], "c": ["a"], "d": ["b", "c"]}
    assert topological_layers(deps) == [["a"], ["b", "c"], ["d"]]


def test_cycle_detection_reports_nodes():
    """存在环时抛 CycleError 且包含环上节点。"""
    try:
        topological_layers({"a": ["b"], "b": ["a"]})
    except CycleError as exc:
        assert set(exc.nodes) == {"a", "b"}, exc.nodes
    else:
        assert False, "expected CycleError"


def test_run_dag_success_results():
    """所有任务成功时返回 succeeded 状态和结果。"""
    tasks = {"a": lambda: 1, "b": lambda: 2}
    got = run_dag(tasks, {"b": ["a"]})
    assert got["status"]["a"] == "succeeded" and got["results"]["b"] == 2, got


def test_failure_skips_downstream_only():
    """任务失败会跳过下游，但不影响无关分支。"""
    def bad():
        raise RuntimeError("boom")
    got = run_dag({"a": lambda: "ok", "b": bad, "c": lambda: "c", "d": lambda: "d"}, {"b": ["a"], "c": ["a"], "d": ["b", "c"]})
    assert got["status"]["b"] == "failed", got
    assert got["status"]["c"] == "succeeded", got
    assert got["status"]["d"] == "skipped", got
''',
        hidden=r'''def test_dependency_only_node_is_included():
    """只作为依赖出现的节点也会纳入层次和执行状态。"""
    got = topological_layers({"b": ["a"]})
    assert got == [["a"], ["b"]], got
    run = run_dag({"b": lambda: "b"}, {"b": ["a"]})
    assert run["status"]["a"] == "succeeded" and run["results"]["a"] is None, run


def test_self_cycle():
    """自依赖也会被识别为环。"""
    try:
        topological_layers({"a": ["a"]})
    except CycleError as exc:
        assert exc.nodes == ["a"], exc.nodes
    else:
        assert False, "expected CycleError"


def test_deterministic_sorting_inside_layer():
    """同层节点按字符串排序，输出确定。"""
    got = topological_layers({"z": [], "a": [], "m": []})
    assert got == [["a", "m", "z"]], got
''',
        solution=r'''class CycleError(Exception):
    """DAG 中存在环。"""
    def __init__(self, nodes):
        self.nodes = sorted(nodes)
        super().__init__("cycle detected: " + ", ".join(self.nodes))


def _normalize_graph(deps):
    nodes = set(deps)
    for parents in deps.values():
        nodes.update(parents)
    graph = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    parent_map = {node: set(deps.get(node, [])) for node in nodes}
    for node, parents in parent_map.items():
        for parent in parents:
            graph.setdefault(parent, set()).add(node)
            indegree[node] = indegree.get(node, 0) + 1
            indegree.setdefault(parent, 0)
    return nodes, graph, indegree, parent_map


def topological_layers(deps):
    """把 DAG 依赖关系分成可并行执行的拓扑层。"""
    nodes, graph, indegree, _ = _normalize_graph(deps)
    ready = sorted([node for node in nodes if indegree[node] == 0])
    layers = []
    seen = 0
    while ready:
        layer = ready
        layers.append(layer)
        seen += len(layer)
        next_ready = []
        for node in layer:
            for child in sorted(graph.get(node, ())):
                indegree[child] -= 1
                if indegree[child] == 0:
                    next_ready.append(child)
        ready = sorted(next_ready)
    if seen != len(nodes):
        cycle_nodes = [node for node in nodes if indegree[node] > 0]
        raise CycleError(cycle_nodes)
    return layers


def run_dag(tasks, deps):
    """按拓扑层执行任务，失败时跳过下游。"""
    layers = topological_layers(deps)
    _, _, _, parent_map = _normalize_graph(deps)
    status = {}
    results = {}
    errors = {}
    for layer in layers:
        for node in layer:
            parents = parent_map.get(node, set())
            if any(status.get(parent) in ("failed", "skipped") for parent in parents):
                status[node] = "skipped"
                results[node] = None
                continue
            fn = tasks.get(node, lambda: None)
            try:
                results[node] = fn()
            except Exception as exc:
                status[node] = "failed"
                results[node] = None
                errors[node] = str(exc)
            else:
                status[node] = "succeeded"
    return {"layers": layers, "status": status, "results": results, "errors": errors}
''',
        hints=["先把只作为依赖出现的节点也加入 nodes，再构造 indegree。", "Kahn 算法每次取当前入度为 0 的节点作为一层，层内排序保证确定性。", "执行阶段不要因为一个节点失败而停止整个 DAG，只把依赖它的下游标记 skipped。"],
        points=["拓扑排序与分层", "环检测", "任务状态传播", "确定性执行顺序"],
        numpy=False,
    ),
]
