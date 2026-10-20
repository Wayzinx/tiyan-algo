LABS = [
    dict(
        id="lab-t-json-extract",
        kind="tests",
        course="dev",
        title="给 JSON 提取器写测试",
        level="medium",
        desc=r"""### 背景
在 AI 应用里，模型经常把结构化结果包在 Markdown 代码块、解释性文字、前后寒暄或调试信息中。评测系统、Agent 编排器和后处理任务不能假设输出刚好就是纯 JSON，否则一次多余的说明、一个尾逗号或数组结果就会让链路误判失败。`extract_json(text)` 是一个典型的“看起来简单、实际很容易漏边界”的工具函数，适合用变异测试练习真实测试设计。
### 被测函数的需求
函数接收字符串 `text`，返回其中第一个可解析的 JSON 值，返回值是 `json.loads` 后的 Python 对象。它要优先尝试 Markdown 代码块，代码块语言可以是 `json`，也可以不写；如果代码块解析失败，再从全文中扫描第一个完整的 JSON 对象或数组。允许对象和数组在闭合括号前出现尾逗号，例如 `{"a": 1,}` 或 `[1, 2,]`。扫描括号时必须正确处理字符串里的 `{`、`}`、`[`、`]` 和转义字符，不能被 JSON 字符串内容干扰。找不到任何可解析 JSON 时必须抛出 `ValueError`，不能返回 `None` 或空字典。
### 怎么判分
你的测试会先在正确实现上运行，全部通过后，再分别替换成若干带真实缺陷的实现。每个变异体代表常见工程错误，例如只支持对象、不支持尾逗号、没有优先处理代码块、括号扫描没考虑字符串、找不到时静默返回。能杀死更多变异体，说明测试覆盖了更多等价类和边界。
### 要求
只写 `test_` 开头的函数，直接调用 `extract_json`；只用标准库和 `assert`；不要联网，不要依赖随机数或时间。""",
        impl=r'''import json
import re


def _clean_json_candidate(source):
    return re.sub(r",\s*([}\]])", r"\1", source.strip())


def _loads_candidate(source):
    return json.loads(_clean_json_candidate(source))


def extract_json(text):
    for match in re.finditer(r"```(?:json|JSON)?\s*(.*?)```", text, re.S):
        try:
            return _loads_candidate(match.group(1))
        except json.JSONDecodeError:
            pass

    pairs = {"{": "}", "[": "]"}
    for start, ch in enumerate(text):
        if ch not in pairs:
            continue
        stack = []
        in_string = False
        escaped = False
        for pos in range(start, len(text)):
            cur = text[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif cur == "\\":
                    escaped = True
                elif cur == '"':
                    in_string = False
                continue
            if cur == '"':
                in_string = True
            elif cur in pairs:
                stack.append(pairs[cur])
            elif stack and cur == stack[-1]:
                stack.pop()
                if not stack:
                    try:
                        return _loads_candidate(text[start:pos + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("no JSON value found")
''',
        mutants=[
            dict(
                name="object_only",
                desc="只扫描 JSON 对象，完全漏掉数组作为顶层 JSON 的情况。",
                hint="不要只测花括号结果，模型有时会直接返回列表。",
                code=r'''import json
import re


def _clean_json_candidate(source):
    return re.sub(r",\s*([}\]])", r"\1", source.strip())


def _loads_candidate(source):
    return json.loads(_clean_json_candidate(source))


def extract_json(text):
    for match in re.finditer(r"```(?:json|JSON)?\s*(.*?)```", text, re.S):
        try:
            return _loads_candidate(match.group(1))
        except json.JSONDecodeError:
            pass
    for start, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        for pos in range(start, len(text)):
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
                if depth == 0:
                    return _loads_candidate(text[start:pos + 1])
    raise ValueError("no JSON value found")
'''),
            dict(
                name="no_trailing_comma",
                desc="没有清理尾逗号，遇到模型常见的宽松 JSON 会解析失败。",
                hint="考虑闭合括号前多一个逗号的输出。",
                code=r'''import json
import re


def _loads_candidate(source):
    return json.loads(source.strip())


def extract_json(text):
    for match in re.finditer(r"```(?:json|JSON)?\s*(.*?)```", text, re.S):
        try:
            return _loads_candidate(match.group(1))
        except json.JSONDecodeError:
            pass
    pairs = {"{": "}", "[": "]"}
    for start, ch in enumerate(text):
        if ch not in pairs:
            continue
        stack = []
        in_string = False
        escaped = False
        for pos in range(start, len(text)):
            cur = text[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif cur == "\\":
                    escaped = True
                elif cur == '"':
                    in_string = False
                continue
            if cur == '"':
                in_string = True
            elif cur in pairs:
                stack.append(pairs[cur])
            elif stack and cur == stack[-1]:
                stack.pop()
                if not stack:
                    return _loads_candidate(text[start:pos + 1])
    raise ValueError("no JSON value found")
'''),
            dict(
                name="whole_code_block_only",
                desc="一旦发现代码块就只解析代码块，代码块坏掉时不会继续扫描正文里的有效 JSON。",
                hint="可以构造一个坏代码块后面跟着好 JSON 的模型输出。",
                code=r'''import json
import re


def _clean_json_candidate(source):
    return re.sub(r",\s*([}\]])", r"\1", source.strip())


def _loads_candidate(source):
    return json.loads(_clean_json_candidate(source))


def extract_json(text):
    match = re.search(r"```(?:json|JSON)?\s*(.*?)```", text, re.S)
    if match:
        return _loads_candidate(match.group(1))
    pairs = {"{": "}", "[": "]"}
    for start, ch in enumerate(text):
        if ch not in pairs:
            continue
        depth = 0
        for pos in range(start, len(text)):
            if text[pos] in pairs:
                depth += 1
            elif text[pos] in "}]":
                depth -= 1
                if depth == 0:
                    return _loads_candidate(text[start:pos + 1])
    raise ValueError("no JSON value found")
'''),
            dict(
                name="returns_none_when_missing",
                desc="找不到 JSON 时静默返回 None，而不是显式抛出 ValueError。",
                hint="异常路径也要写断言，不要只测成功解析。",
                code=r'''import json
import re


def _clean_json_candidate(source):
    return re.sub(r",\s*([}\]])", r"\1", source.strip())


def _loads_candidate(source):
    return json.loads(_clean_json_candidate(source))


def extract_json(text):
    for match in re.finditer(r"```(?:json|JSON)?\s*(.*?)```", text, re.S):
        try:
            return _loads_candidate(match.group(1))
        except json.JSONDecodeError:
            pass
    for start, ch in enumerate(text):
        if ch in "[{":
            try:
                return _loads_candidate(text[start:])
            except json.JSONDecodeError:
                pass
    return None
'''),
            dict(
                name="string_brace_confusion",
                desc="括号配对时没有跳过 JSON 字符串，字符串里的右括号会提前截断候选片段。",
                hint="JSON 字符串内容也可以包含括号字符。",
                code=r'''import json
import re


def _clean_json_candidate(source):
    return re.sub(r",\s*([}\]])", r"\1", source.strip())


def _loads_candidate(source):
    return json.loads(_clean_json_candidate(source))


def extract_json(text):
    for match in re.finditer(r"```(?:json|JSON)?\s*(.*?)```", text, re.S):
        try:
            return _loads_candidate(match.group(1))
        except json.JSONDecodeError:
            pass
    pairs = {"{": "}", "[": "]"}
    for start, ch in enumerate(text):
        if ch not in pairs:
            continue
        stack = []
        for pos in range(start, len(text)):
            cur = text[pos]
            if cur in pairs:
                stack.append(pairs[cur])
            elif stack and cur == stack[-1]:
                stack.pop()
                if not stack:
                    return _loads_candidate(text[start:pos + 1])
    raise ValueError("no JSON value found")
'''),
        ],
        starter=r'''def test_extracts_simple_object():
    assert extract_json('{"ok": true}') == {"ok": True}
''',
        solution=r'''def test_extracts_json_from_markdown_with_trailing_commas():
    text = '解释如下：\n```json\n{"items": [1, 2,], "ok": true,}\n```\n谢谢'
    assert extract_json(text) == {"items": [1, 2], "ok": True}


def test_extracts_top_level_array_after_noise():
    assert extract_json('前缀文字 [1, {"a": 2,}, 3,] 后缀') == [1, {"a": 2}, 3]


def test_falls_back_after_bad_code_block():
    text = '```json\n{bad\n```\n最终答案是 {"final": 7}'
    assert extract_json(text) == {"final": 7}


def test_handles_braces_inside_json_strings():
    text = '模型说 {"text": "literal } bracket", "nested": {"x": "[ok]"}} done'
    assert extract_json(text) == {"text": "literal } bracket", "nested": {"x": "[ok]"}}


def test_raises_value_error_when_no_json_exists():
    try:
        extract_json('only natural language, no structured value')
    except ValueError:
        pass
    else:
        assert False, '找不到 JSON 时必须抛 ValueError'
''',
        hints=["先按代码块、正文对象、正文数组、失败路径划分等价类。", "尾逗号和字符串里的括号是最容易漏掉的边界。", "构造坏代码块后面跟有效 JSON，可以检查是否真的做了 fallback。"],
        points=["模型输出清洗与宽松 JSON 解析", "异常路径断言", "复杂字符串扫描边界"],
    ),
    dict(
        id="lab-t-retry",
        kind="tests",
        course="dev",
        title="给重试退避函数写测试",
        level="medium",
        desc=r"""### 背景
调用模型、检索服务或外部工具时，瞬时失败很常见。重试逻辑如果写错，轻则把临时错误放大成用户可见失败，重则吞掉不可重试异常、睡眠过久、最后抛出包装后的异常导致上层无法分类。`retry_call` 把“次数上限、指数退避、抖动、异常过滤、依赖注入”集中在一个小函数里，是面试中检验测试设计能力的好题。
### 被测函数的需求
`retry_call(fn, retries, base, max_delay, sleep, rng, retry_on)` 调用无参函数 `fn`。初始调用失败后，只有异常属于 `retry_on` 时才重试；`retries` 表示失败后最多再试几次，所以总调用次数最多是 `retries + 1`。第 `i` 次重试前的上限延迟是 `min(max_delay, base * 2**i)`，实际 sleep 时间是该上限乘以 `rng.random()`，从而可测试地注入抖动。每次重试前调用注入的 `sleep(delay)`，测试中不能真的睡眠。若最终仍失败，必须原样抛出最后一次捕获的异常对象；不在 `retry_on` 中的异常必须立即抛出且不 sleep。
### 怎么判分
你的测试先在正确实现上通过，再挑战变异体。变异体会模拟常见错误：把 `retries` 当总次数、捕获所有异常、没有指数退避、没有最大延迟上限、忽略随机抖动、重新包装最后异常等。
### 要求
测试必须确定性，用假的 `sleep` 收集延迟，用假的 `rng.random()` 返回固定序列；只用 `assert`，直接调用 `retry_call`。""",
        impl=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except retry_on:
            if attempt >= retries:
                raise
            cap = min(max_delay, base * (2 ** attempt))
            sleep(cap * rng.random())
            attempt += 1
''',
        mutants=[
            dict(name="retries_as_total_attempts", desc="把 retries 当成总调用次数，少做了一次初始调用后的重试。", hint="确认 retries=2 时最多应调用几次 fn。", code=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except retry_on:
            if attempt >= retries - 1:
                raise
            cap = min(max_delay, base * (2 ** attempt))
            sleep(cap * rng.random())
            attempt += 1
'''),
            dict(name="catches_all_exceptions", desc="捕获并重试所有异常，破坏了 retry_on 的异常过滤语义。", hint="除了可重试异常，也要测一个不可重试异常。", code=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except Exception:
            if attempt >= retries:
                raise
            cap = min(max_delay, base * (2 ** attempt))
            sleep(cap * rng.random())
            attempt += 1
'''),
            dict(name="fixed_delay", desc="每次都用 base 作为退避上限，没有指数增长。", hint="至少让函数连续失败两次，检查两次 sleep 的参数。", code=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except retry_on:
            if attempt >= retries:
                raise
            cap = min(max_delay, base)
            sleep(cap * rng.random())
            attempt += 1
'''),
            dict(name="no_max_delay_cap", desc="指数退避没有套 max_delay，上限可能无限变大。", hint="把 base 和 max_delay 设成能触发封顶的组合。", code=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except retry_on:
            if attempt >= retries:
                raise
            cap = base * (2 ** attempt)
            sleep(cap * rng.random())
            attempt += 1
'''),
            dict(name="no_jitter", desc="直接 sleep 退避上限，没有乘以注入随机数。", hint="让 rng.random 返回不是 1 的固定值。", code=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except retry_on:
            if attempt >= retries:
                raise
            cap = min(max_delay, base * (2 ** attempt))
            sleep(cap)
            attempt += 1
'''),
            dict(name="wraps_last_exception", desc="耗尽重试后抛 RuntimeError，丢失了最后一次异常对象。", hint="不仅要断言会抛，还要断言抛出的就是原异常类型和对象。", code=r'''def retry_call(fn, retries, base, max_delay, sleep, rng, retry_on):
    attempt = 0
    while True:
        try:
            return fn()
        except retry_on as exc:
            if attempt >= retries:
                raise RuntimeError("retry exhausted") from exc
            cap = min(max_delay, base * (2 ** attempt))
            sleep(cap * rng.random())
            attempt += 1
'''),
        ],
        starter=r'''def test_returns_success_without_retry():
    class Rng:
        def random(self):
            return 0.5
    assert retry_call(lambda: "ok", 3, 1.0, 10.0, lambda delay: None, Rng(), (ValueError,)) == "ok"
''',
        solution=r'''class FixedRng:
    def __init__(self, values):
        self.values = list(values)
    def random(self):
        return self.values.pop(0)


def test_retries_until_success_with_exponential_jitter_and_cap():
    sleeps = []
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        if calls["n"] < 4:
            raise TimeoutError("temporary")
        return "done"
    result = retry_call(fn, 3, 2.0, 5.0, sleeps.append, FixedRng([0.5, 0.25, 1.0]), (TimeoutError,))
    assert result == "done"
    assert calls["n"] == 4
    assert sleeps == [1.0, 1.0, 5.0], sleeps


def test_non_retryable_exception_is_not_slept_or_retried():
    sleeps = []
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        raise TypeError("bad input")
    try:
        retry_call(fn, 5, 1.0, 9.0, sleeps.append, FixedRng([0.1]), (TimeoutError,))
    except TypeError:
        pass
    else:
        assert False, "不可重试异常应立即抛出"
    assert calls["n"] == 1
    assert sleeps == []


def test_last_retryable_exception_is_raised_unchanged():
    sleeps = []
    first = TimeoutError("first")
    last = TimeoutError("last")
    errors = [first, last]
    def fn():
        raise errors.pop(0)
    try:
        retry_call(fn, 1, 3.0, 10.0, sleeps.append, FixedRng([0.2]), (TimeoutError,))
    except TimeoutError as exc:
        assert exc is last
    else:
        assert False, "耗尽重试后应抛最后一次原始异常"
    assert sleeps == [0.6000000000000001]
''',
        hints=["先把成功、可重试失败、不可重试失败三类路径分开。", "用 fake sleep 和 fake rng 断言精确延迟，不要真的 sleep。", "最后一次异常的身份也值得测，不能只测异常类型。"],
        points=["依赖注入测试时间和随机性", "重试次数边界", "异常过滤与原样传播"],
    ),
    dict(
        id="lab-t-trim",
        kind="tests",
        course="harness",
        title="给对话裁剪函数写测试",
        level="medium",
        desc=r"""### 背景
Agent 测试框架经常要把长对话裁剪到模型上下文预算内。裁剪不是简单地从头删消息：系统提示承载安全和任务约束，最后一条用户消息是当前问题，工具调用消息还存在成对一致性。如果这些状态被破坏，模型可能丢指令、回答旧问题，或看到孤立的 tool 结果而无法恢复轨迹。
### 被测函数的需求
`trim_history(messages, budget, count_tokens)` 返回新的消息列表，不修改输入。`count_tokens(message)` 由调用方注入，用于计算每条消息成本；预算是保留消息 token 总和的上限。所有 `role == "system"` 的消息和最后一条 `role == "user"` 的消息必须保留，即使它们本身已经超过预算。其余消息从最早开始按组丢弃，直到总成本不超过预算或只剩受保护消息。若一条 assistant 消息包含 `tool_calls`，它和紧随其后的、`tool_call_id` 属于这些调用 id 的 tool 消息是一个原子组：要么一起保留，要么一起丢弃，不能只留下 assistant 或 tool 的半边。
### 怎么判分
变异体会模拟常见裁剪错误：忘记保留 system、忘记保留最后用户消息、按单条消息拆开工具调用、从最新消息开始删、用消息数量代替 token、直接修改原列表等。好的测试应该同时覆盖预算压力、成组一致性和输入不可变性。
### 要求
测试中直接调用 `trim_history`，用简单确定性的 `count_tokens`；只用 `assert`。""",
        impl=r'''def trim_history(messages, budget, count_tokens):
    last_user = None
    for idx, message in enumerate(messages):
        if message.get("role") == "user":
            last_user = idx
    protected = {idx for idx, message in enumerate(messages) if message.get("role") == "system"}
    if last_user is not None:
        protected.add(last_user)

    groups = []
    idx = 0
    while idx < len(messages):
        message = messages[idx]
        calls = message.get("tool_calls") if message.get("role") == "assistant" else None
        if calls:
            ids = {call.get("id") for call in calls}
            group = [idx]
            j = idx + 1
            while j < len(messages) and messages[j].get("role") == "tool" and messages[j].get("tool_call_id") in ids:
                group.append(j)
                j += 1
            groups.append(group)
            idx = j
        else:
            groups.append([idx])
            idx += 1

    kept = [True] * len(groups)

    def total_tokens():
        return sum(count_tokens(messages[i]) for g, keep in zip(groups, kept) if keep for i in g)

    for group_index, group in enumerate(groups):
        if total_tokens() <= budget:
            break
        if any(i in protected for i in group):
            continue
        kept[group_index] = False
    return [dict(messages[i]) for group, keep in zip(groups, kept) if keep for i in group]
''',
        mutants=[
            dict(name="drops_system", desc="没有把 system 消息设为受保护，预算紧张时会删掉系统约束。", hint="预算小到需要删除消息时，检查 system 是否还在。", code=r'''def trim_history(messages, budget, count_tokens):
    last_user = None
    for idx, message in enumerate(messages):
        if message.get("role") == "user":
            last_user = idx
    protected = {last_user} if last_user is not None else set()
    result = list(messages)
    while sum(count_tokens(m) for m in result) > budget and len(result) > len(protected):
        for i, message in enumerate(result):
            original = messages.index(message)
            if original not in protected:
                result.pop(i)
                break
        else:
            break
    return [dict(m) for m in result]
'''),
            dict(name="drops_last_user", desc="没有保护最后一条 user 消息，可能把当前问题裁掉。", hint="最后一条 user 和较早 user 的保护规则不一样。", code=r'''def trim_history(messages, budget, count_tokens):
    protected = {idx for idx, message in enumerate(messages) if message.get("role") == "system"}
    result = list(messages)
    while sum(count_tokens(m) for m in result) > budget:
        for i, message in enumerate(result):
            original = messages.index(message)
            if original not in protected:
                result.pop(i)
                break
        else:
            break
    return [dict(m) for m in result]
'''),
            dict(name="splits_tool_pair", desc="按单条消息裁剪，可能只保留 assistant tool_calls 或只保留 tool 结果。", hint="构造预算刚好只能保留工具调用组的一半。", code=r'''def trim_history(messages, budget, count_tokens):
    last_user = None
    for idx, message in enumerate(messages):
        if message.get("role") == "user":
            last_user = idx
    protected = {idx for idx, message in enumerate(messages) if message.get("role") == "system"}
    if last_user is not None:
        protected.add(last_user)
    result = [(idx, dict(message)) for idx, message in enumerate(messages)]
    while sum(count_tokens(m) for _, m in result) > budget:
        for pos, (idx, _) in enumerate(result):
            if idx not in protected:
                result.pop(pos)
                break
        else:
            break
    return [m for _, m in result]
'''),
            dict(name="removes_newest_first", desc="从最新上下文开始删，违反从最早开始丢弃的策略。", hint="让旧消息和较新 assistant 同时可删，观察保留的是哪一个。", code=r'''def trim_history(messages, budget, count_tokens):
    last_user = None
    for idx, message in enumerate(messages):
        if message.get("role") == "user":
            last_user = idx
    protected = {idx for idx, message in enumerate(messages) if message.get("role") == "system"}
    if last_user is not None:
        protected.add(last_user)
    result = [(idx, dict(message)) for idx, message in enumerate(messages)]
    while sum(count_tokens(m) for _, m in result) > budget:
        for pos in range(len(result) - 1, -1, -1):
            if result[pos][0] not in protected:
                result.pop(pos)
                break
        else:
            break
    return [m for _, m in result]
'''),
            dict(name="counts_messages_not_tokens", desc="用消息条数判断预算，没有调用 count_tokens。", hint="设置每条消息 token 差异很大的场景。", code=r'''def trim_history(messages, budget, count_tokens):
    last_user = None
    for idx, message in enumerate(messages):
        if message.get("role") == "user":
            last_user = idx
    protected = {idx for idx, message in enumerate(messages) if message.get("role") == "system"}
    if last_user is not None:
        protected.add(last_user)
    result = [(idx, dict(message)) for idx, message in enumerate(messages)]
    while len(result) > budget:
        for pos, (idx, _) in enumerate(result):
            if idx not in protected:
                result.pop(pos)
                break
        else:
            break
    return [m for _, m in result]
'''),
            dict(name="mutates_input", desc="通过 pop 直接修改传入的 messages 列表。", hint="调用后重新检查原始列表内容和长度。", code=r'''def trim_history(messages, budget, count_tokens):
    last_user = None
    for idx, message in enumerate(messages):
        if message.get("role") == "user":
            last_user = idx
    protected = {idx for idx, message in enumerate(messages) if message.get("role") == "system"}
    if last_user is not None:
        protected.add(last_user)
    while sum(count_tokens(m) for m in messages) > budget:
        for idx in range(len(messages)):
            if idx not in protected:
                messages.pop(idx)
                protected = {p - 1 if p > idx else p for p in protected if p != idx}
                break
        else:
            break
    return messages
'''),
        ],
        starter=r'''def test_keeps_short_history_unchanged():
    messages = [{"role": "user", "content": "hi"}]
    assert trim_history(messages, 10, lambda m: 1) == messages
''',
        solution=r'''def token_count(message):
    return message.get("tokens", 1)


def test_protects_system_and_last_user_even_when_over_budget():
    messages = [
        {"role": "system", "content": "rules", "tokens": 5},
        {"role": "user", "content": "old", "tokens": 1},
        {"role": "assistant", "content": "old answer", "tokens": 1},
        {"role": "user", "content": "current", "tokens": 5},
    ]
    result = trim_history(messages, 3, token_count)
    assert [m["content"] for m in result] == ["rules", "current"], result


def test_drops_earliest_unprotected_by_token_budget():
    messages = [
        {"role": "system", "content": "s", "tokens": 1},
        {"role": "user", "content": "old", "tokens": 4},
        {"role": "assistant", "content": "recent", "tokens": 2},
        {"role": "user", "content": "now", "tokens": 1},
    ]
    result = trim_history(messages, 4, token_count)
    assert [m["content"] for m in result] == ["s", "recent", "now"], result


def test_tool_calls_and_tool_results_are_atomic_groups():
    messages = [
        {"role": "system", "content": "s", "tokens": 1},
        {"role": "assistant", "content": "call", "tokens": 2, "tool_calls": [{"id": "a"}]},
        {"role": "tool", "tool_call_id": "a", "content": "result", "tokens": 2},
        {"role": "assistant", "content": "summary", "tokens": 1},
        {"role": "user", "content": "next", "tokens": 1},
    ]
    result = trim_history(messages, 5, token_count)
    roles = [m["role"] for m in result]
    assert roles == ["system", "assistant", "user"], result
    assert all(m.get("tool_call_id") != "a" for m in result)


def test_does_not_mutate_input_messages():
    messages = [
        {"role": "system", "content": "s", "tokens": 1},
        {"role": "user", "content": "old", "tokens": 5},
        {"role": "user", "content": "new", "tokens": 1},
    ]
    before = [dict(m) for m in messages]
    trim_history(messages, 2, token_count)
    assert messages == before
''',
        hints=["先列出哪些消息绝对不能删，再考虑普通消息的删除顺序。", "tool_calls assistant 与对应 tool 消息必须按组测试。", "预算建议用自定义 token 字段，才能杀死按条数裁剪的错误。"],
        points=["状态历史裁剪", "工具调用轨迹一致性", "输入不可变性"],
    ),
    dict(
        id="lab-t-scorer",
        kind="tests",
        course="agent",
        title="给规则评分器写测试",
        level="medium",
        desc=r"""### 背景
Agent 评测通常不会只有一种断言方式：有些题要求完全一致，有些只要求包含关键词，有些需要正则匹配，有些要解析 JSON，有些数值答案允许微小误差。`score(output, rule)` 把这些判分规则统一成一个函数，测试时必须把“大小写、空白、正则语义、JSON 键、数值容差”说清楚，否则很容易出现线上评测和本地理解不一致。
### 被测函数的需求
`rule["type"]` 支持 `exact`、`contains`、`regex`、`json_keys`、`number_tolerance`。`exact` 比较 `output.strip()` 和 `rule["expected"].strip()`，大小写敏感，内部空白不折叠。`contains` 检查 `rule["expected"]` 是否作为子串出现在输出中，默认大小写敏感；只有 `rule.get("ignore_case")` 为真时才忽略大小写。`regex` 使用 `re.search`，同样只在 `ignore_case` 为真时加忽略大小写标志。`json_keys` 要求输出能解析为 JSON 对象，并且包含 `rule["keys"]` 中所有顶层键。`number_tolerance` 从输出中提取第一个数字，与 `expected` 的绝对误差小于等于 `tolerance` 时通过。未知类型抛 `ValueError`。
### 怎么判分
变异体会把 exact 写成忽略大小写、contains 总是忽略大小写、regex 错用 fullmatch、JSON 键只要命中一个就通过、数值容差边界写错等。你的测试要覆盖每种 rule，并且包含能区分语义的反例。
### 要求
测试直接调用 `score`，只用标准库和 `assert`。""",
        impl=r'''import json
import re


def score(output, rule):
    kind = rule.get("type")
    if kind == "exact":
        return output.strip() == str(rule.get("expected", "")).strip()
    if kind == "contains":
        expected = str(rule.get("expected", ""))
        haystack = output
        if rule.get("ignore_case"):
            expected = expected.lower()
            haystack = haystack.lower()
        return expected in haystack
    if kind == "regex":
        flags = re.I if rule.get("ignore_case") else 0
        return re.search(rule["pattern"], output, flags) is not None
    if kind == "json_keys":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and all(key in value for key in rule.get("keys", []))
    if kind == "number_tolerance":
        match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
        if not match:
            return False
        actual = float(match.group(0))
        return abs(actual - float(rule["expected"])) <= float(rule.get("tolerance", 0))
    raise ValueError("unknown rule type")
''',
        mutants=[
            dict(name="exact_ignore_case", desc="exact 比较错误地忽略大小写。", hint="exact 默认应大小写敏感。", code=r'''import json
import re


def score(output, rule):
    kind = rule.get("type")
    if kind == "exact":
        return output.strip().lower() == str(rule.get("expected", "")).strip().lower()
    if kind == "contains":
        expected = str(rule.get("expected", ""))
        haystack = output
        if rule.get("ignore_case"):
            expected = expected.lower(); haystack = haystack.lower()
        return expected in haystack
    if kind == "regex":
        return re.search(rule["pattern"], output, re.I if rule.get("ignore_case") else 0) is not None
    if kind == "json_keys":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and all(key in value for key in rule.get("keys", []))
    if kind == "number_tolerance":
        match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
        return bool(match) and abs(float(match.group(0)) - float(rule["expected"])) <= float(rule.get("tolerance", 0))
    raise ValueError("unknown rule type")
'''),
            dict(name="contains_always_ignore_case", desc="contains 无视 ignore_case 配置，始终大小写不敏感。", hint="contains 也需要测默认大小写敏感的失败例。", code=r'''import json
import re


def score(output, rule):
    kind = rule.get("type")
    if kind == "exact":
        return output.strip() == str(rule.get("expected", "")).strip()
    if kind == "contains":
        return str(rule.get("expected", "")).lower() in output.lower()
    if kind == "regex":
        return re.search(rule["pattern"], output, re.I if rule.get("ignore_case") else 0) is not None
    if kind == "json_keys":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and all(key in value for key in rule.get("keys", []))
    if kind == "number_tolerance":
        match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
        return bool(match) and abs(float(match.group(0)) - float(rule["expected"])) <= float(rule.get("tolerance", 0))
    raise ValueError("unknown rule type")
'''),
            dict(name="regex_fullmatch", desc="regex 使用 fullmatch，导致只匹配整段文本。", hint="正则规则应能在较长输出中 search 到片段。", code=r'''import json
import re


def score(output, rule):
    kind = rule.get("type")
    if kind == "exact":
        return output.strip() == str(rule.get("expected", "")).strip()
    if kind == "contains":
        expected = str(rule.get("expected", "")); haystack = output
        if rule.get("ignore_case"):
            expected = expected.lower(); haystack = haystack.lower()
        return expected in haystack
    if kind == "regex":
        return re.fullmatch(rule["pattern"], output, re.I if rule.get("ignore_case") else 0) is not None
    if kind == "json_keys":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and all(key in value for key in rule.get("keys", []))
    if kind == "number_tolerance":
        match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
        return bool(match) and abs(float(match.group(0)) - float(rule["expected"])) <= float(rule.get("tolerance", 0))
    raise ValueError("unknown rule type")
'''),
            dict(name="json_keys_any", desc="json_keys 只要任意一个键存在就通过，没有要求全部键。", hint="缺一个必需键时应失败。", code=r'''import json
import re


def score(output, rule):
    kind = rule.get("type")
    if kind == "exact":
        return output.strip() == str(rule.get("expected", "")).strip()
    if kind == "contains":
        expected = str(rule.get("expected", "")); haystack = output
        if rule.get("ignore_case"):
            expected = expected.lower(); haystack = haystack.lower()
        return expected in haystack
    if kind == "regex":
        return re.search(rule["pattern"], output, re.I if rule.get("ignore_case") else 0) is not None
    if kind == "json_keys":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and any(key in value for key in rule.get("keys", []))
    if kind == "number_tolerance":
        match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
        return bool(match) and abs(float(match.group(0)) - float(rule["expected"])) <= float(rule.get("tolerance", 0))
    raise ValueError("unknown rule type")
'''),
            dict(name="number_tolerance_exclusive", desc="数值误差刚好等于 tolerance 时错误地判失败。", hint="容差边界是小于等于，不是严格小于。", code=r'''import json
import re


def score(output, rule):
    kind = rule.get("type")
    if kind == "exact":
        return output.strip() == str(rule.get("expected", "")).strip()
    if kind == "contains":
        expected = str(rule.get("expected", "")); haystack = output
        if rule.get("ignore_case"):
            expected = expected.lower(); haystack = haystack.lower()
        return expected in haystack
    if kind == "regex":
        return re.search(rule["pattern"], output, re.I if rule.get("ignore_case") else 0) is not None
    if kind == "json_keys":
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and all(key in value for key in rule.get("keys", []))
    if kind == "number_tolerance":
        match = re.search(r"[-+]?\d+(?:\.\d+)?", output)
        return bool(match) and abs(float(match.group(0)) - float(rule["expected"])) < float(rule.get("tolerance", 0))
    raise ValueError("unknown rule type")
'''),
        ],
        starter=r'''def test_exact_trims_outer_space():
    assert score('  yes\n', {"type": "exact", "expected": "yes"}) is True
''',
        solution=r'''def test_exact_is_case_sensitive_but_trims_edges():
    assert score('  Answer\n', {"type": "exact", "expected": "Answer"}) is True
    assert score('answer', {"type": "exact", "expected": "Answer"}) is False


def test_contains_respects_ignore_case_flag():
    assert score('The Final Answer is Paris', {"type": "contains", "expected": "final answer"}) is False
    assert score('The Final Answer is Paris', {"type": "contains", "expected": "final answer", "ignore_case": True}) is True


def test_regex_uses_search_not_fullmatch():
    assert score('prefix id=ABC-123 suffix', {"type": "regex", "pattern": r"[A-Z]{3}-\d{3}"}) is True


def test_json_keys_requires_all_top_level_keys():
    assert score('{"answer": 1, "reason": "ok"}', {"type": "json_keys", "keys": ["answer", "reason"]}) is True
    assert score('{"answer": 1}', {"type": "json_keys", "keys": ["answer", "reason"]}) is False
    assert score('[{"answer": 1}]', {"type": "json_keys", "keys": ["answer"]}) is False


def test_number_tolerance_is_inclusive_and_uses_first_number():
    assert score('value: -3.5 units', {"type": "number_tolerance", "expected": -3.0, "tolerance": 0.5}) is True
    assert score('value: 10.6', {"type": "number_tolerance", "expected": 10.0, "tolerance": 0.5}) is False
''',
        hints=["每种 rule 至少写一个正例和能区分语义的反例。", "大小写和空白不要混在一起测，分别构造断言。", "数值容差要测刚好等于 tolerance 的边界。"],
        points=["多规则评分语义", "大小写与空白约定", "JSON 与数值边界"],
    ),
    dict(
        id="lab-t-trajectory",
        kind="tests",
        course="agent",
        title="给工具轨迹检查器写测试",
        level="medium",
        desc=r"""### 背景
Agent 评测不能只看最终回答，有时还必须确认它是否按规定调用了检索、计算、提交等工具，并且没有调用危险工具。轨迹检查器通常用于自动化验收、红线审计和回归测试。如果它只返回第一个问题、忽略参数或把调用顺序当成集合，就会把不合格 Agent 放过。
### 被测函数的需求
`check_trajectory(steps, spec)` 返回违规原因字符串列表，空列表表示通过。`steps` 是按时间顺序排列的字典列表，每步至少可含 `tool` 和 `args`。`spec` 支持：`required_tools`，每个工具名至少出现一次；`forbidden_tools`，出现即违规；`order`，这些工具必须按给定相对顺序出现，中间允许有其他工具；`max_steps`，总步数不能超过该值；`arg_conditions`，形如 `{tool: {arg_name: expected}}`，该工具的每次调用都要满足参数条件，`expected` 可以是普通值，也可以是返回布尔值的谓词函数。函数必须收集所有违规项，而不是发现一个就停止。
### 怎么判分
变异体包含只返回首个违规、忽略 forbidden、忽略参数、把顺序当集合、最大步数边界写成 `>=`、只检查某工具第一次调用等。测试应覆盖合法轨迹和多违规轨迹，且断言返回列表中包含关键信息。
### 要求
测试直接调用 `check_trajectory`；只用 `assert`，不要依赖外部系统。""",
        impl=r'''def check_trajectory(steps, spec):
    violations = []
    tools = [step.get("tool") for step in steps]

    max_steps = spec.get("max_steps")
    if max_steps is not None and len(steps) > max_steps:
        violations.append(f"max_steps exceeded: {len(steps)} > {max_steps}")

    for tool in spec.get("required_tools", []):
        if tool not in tools:
            violations.append(f"required tool missing: {tool}")

    for tool in spec.get("forbidden_tools", []):
        if tool in tools:
            violations.append(f"forbidden tool used: {tool}")

    pos = -1
    for tool in spec.get("order", []):
        try:
            pos = next(i for i in range(pos + 1, len(tools)) if tools[i] == tool)
        except StopIteration:
            violations.append(f"order violation near: {tool}")
            break

    for tool, conditions in spec.get("arg_conditions", {}).items():
        for index, step in enumerate(steps):
            if step.get("tool") != tool:
                continue
            args = step.get("args", {}) or {}
            for name, expected in conditions.items():
                actual = args.get(name)
                ok = expected(actual) if callable(expected) else actual == expected
                if not ok:
                    violations.append(f"argument violation at step {index}: {tool}.{name}")
    return violations
''',
        mutants=[
            dict(name="stops_after_first_violation", desc="发现第一个违规后立即返回，无法一次报告所有问题。", hint="构造同时违反多个规则的轨迹。", code=r'''def check_trajectory(steps, spec):
    tools = [step.get("tool") for step in steps]
    max_steps = spec.get("max_steps")
    if max_steps is not None and len(steps) > max_steps:
        return [f"max_steps exceeded: {len(steps)} > {max_steps}"]
    for tool in spec.get("required_tools", []):
        if tool not in tools:
            return [f"required tool missing: {tool}"]
    for tool in spec.get("forbidden_tools", []):
        if tool in tools:
            return [f"forbidden tool used: {tool}"]
    return []
'''),
            dict(name="ignores_forbidden", desc="完全没有检查 forbidden_tools。", hint="不要只测必须调用的工具，也要测禁止调用。", code=r'''def check_trajectory(steps, spec):
    violations = []
    tools = [step.get("tool") for step in steps]
    if spec.get("max_steps") is not None and len(steps) > spec.get("max_steps"):
        violations.append("max_steps exceeded")
    for tool in spec.get("required_tools", []):
        if tool not in tools:
            violations.append(f"required tool missing: {tool}")
    pos = -1
    for tool in spec.get("order", []):
        try:
            pos = next(i for i in range(pos + 1, len(tools)) if tools[i] == tool)
        except StopIteration:
            violations.append(f"order violation near: {tool}")
            break
    for tool, conditions in spec.get("arg_conditions", {}).items():
        for index, step in enumerate(steps):
            if step.get("tool") == tool:
                for name, expected in conditions.items():
                    actual = (step.get("args") or {}).get(name)
                    if (expected(actual) if callable(expected) else actual == expected) is False:
                        violations.append(f"argument violation at step {index}: {tool}.{name}")
    return violations
'''),
            dict(name="ignores_arg_conditions", desc="只检查工具名和顺序，不检查参数条件。", hint="同一个工具名参数不符合时也应失败。", code=r'''def check_trajectory(steps, spec):
    violations = []
    tools = [step.get("tool") for step in steps]
    if spec.get("max_steps") is not None and len(steps) > spec.get("max_steps"):
        violations.append("max_steps exceeded")
    for tool in spec.get("required_tools", []):
        if tool not in tools:
            violations.append(f"required tool missing: {tool}")
    for tool in spec.get("forbidden_tools", []):
        if tool in tools:
            violations.append(f"forbidden tool used: {tool}")
    pos = -1
    for tool in spec.get("order", []):
        try:
            pos = next(i for i in range(pos + 1, len(tools)) if tools[i] == tool)
        except StopIteration:
            violations.append(f"order violation near: {tool}")
            break
    return violations
'''),
            dict(name="order_as_set", desc="只检查 order 中的工具都出现过，没有检查相对顺序。", hint="把两个必需步骤反过来放。", code=r'''def check_trajectory(steps, spec):
    violations = []
    tools = [step.get("tool") for step in steps]
    if spec.get("max_steps") is not None and len(steps) > spec.get("max_steps"):
        violations.append("max_steps exceeded")
    for tool in spec.get("required_tools", []):
        if tool not in tools:
            violations.append(f"required tool missing: {tool}")
    for tool in spec.get("forbidden_tools", []):
        if tool in tools:
            violations.append(f"forbidden tool used: {tool}")
    for tool in spec.get("order", []):
        if tool not in tools:
            violations.append(f"order violation near: {tool}")
            break
    for tool, conditions in spec.get("arg_conditions", {}).items():
        for index, step in enumerate(steps):
            if step.get("tool") == tool:
                for name, expected in conditions.items():
                    actual = (step.get("args") or {}).get(name)
                    if not (expected(actual) if callable(expected) else actual == expected):
                        violations.append(f"argument violation at step {index}: {tool}.{name}")
    return violations
'''),
            dict(name="max_steps_inclusive_bug", desc="把步数等于 max_steps 也判为违规。", hint="最大步数是可以刚好等于的上限。", code=r'''def check_trajectory(steps, spec):
    violations = []
    tools = [step.get("tool") for step in steps]
    max_steps = spec.get("max_steps")
    if max_steps is not None and len(steps) >= max_steps:
        violations.append(f"max_steps exceeded: {len(steps)} >= {max_steps}")
    for tool in spec.get("required_tools", []):
        if tool not in tools:
            violations.append(f"required tool missing: {tool}")
    for tool in spec.get("forbidden_tools", []):
        if tool in tools:
            violations.append(f"forbidden tool used: {tool}")
    pos = -1
    for tool in spec.get("order", []):
        try:
            pos = next(i for i in range(pos + 1, len(tools)) if tools[i] == tool)
        except StopIteration:
            violations.append(f"order violation near: {tool}")
            break
    for tool, conditions in spec.get("arg_conditions", {}).items():
        for index, step in enumerate(steps):
            if step.get("tool") == tool:
                for name, expected in conditions.items():
                    actual = (step.get("args") or {}).get(name)
                    if not (expected(actual) if callable(expected) else actual == expected):
                        violations.append(f"argument violation at step {index}: {tool}.{name}")
    return violations
'''),
            dict(name="first_call_args_only", desc="同一工具多次调用时只检查第一次参数，后续错误被放过。", hint="让同一个工具第二次调用参数不合规。", code=r'''def check_trajectory(steps, spec):
    violations = []
    tools = [step.get("tool") for step in steps]
    if spec.get("max_steps") is not None and len(steps) > spec.get("max_steps"):
        violations.append("max_steps exceeded")
    for tool in spec.get("required_tools", []):
        if tool not in tools:
            violations.append(f"required tool missing: {tool}")
    for tool in spec.get("forbidden_tools", []):
        if tool in tools:
            violations.append(f"forbidden tool used: {tool}")
    pos = -1
    for tool in spec.get("order", []):
        try:
            pos = next(i for i in range(pos + 1, len(tools)) if tools[i] == tool)
        except StopIteration:
            violations.append(f"order violation near: {tool}")
            break
    for tool, conditions in spec.get("arg_conditions", {}).items():
        for index, step in enumerate(steps):
            if step.get("tool") == tool:
                for name, expected in conditions.items():
                    actual = (step.get("args") or {}).get(name)
                    if not (expected(actual) if callable(expected) else actual == expected):
                        violations.append(f"argument violation at step {index}: {tool}.{name}")
                break
    return violations
'''),
        ],
        starter=r'''def test_empty_spec_accepts_any_steps():
    assert check_trajectory([{"tool": "search", "args": {}}], {}) == []
''',
        solution=r'''def test_valid_trajectory_satisfies_all_rules_at_step_limit():
    steps = [
        {"tool": "search", "args": {"query": "agent testing"}},
        {"tool": "summarize", "args": {"format": "brief"}},
        {"tool": "submit", "args": {"final": True}},
    ]
    spec = {
        "required_tools": ["search", "submit"],
        "forbidden_tools": ["delete"],
        "order": ["search", "submit"],
        "max_steps": 3,
        "arg_conditions": {"submit": {"final": True}, "search": {"query": lambda value: "agent" in value}},
    }
    assert check_trajectory(steps, spec) == []


def test_reports_multiple_violations_in_one_result():
    steps = [{"tool": "delete", "args": {}}, {"tool": "search", "args": {"query": "x"}}]
    spec = {"required_tools": ["submit"], "forbidden_tools": ["delete"], "max_steps": 1}
    violations = check_trajectory(steps, spec)
    joined = "\n".join(violations)
    assert len(violations) >= 3, violations
    assert "submit" in joined and "delete" in joined and "max" in joined


def test_order_is_relative_not_just_membership():
    steps = [{"tool": "submit", "args": {}}, {"tool": "search", "args": {}}]
    violations = check_trajectory(steps, {"order": ["search", "submit"]})
    assert any("order" in v for v in violations), violations


def test_argument_conditions_apply_to_every_call():
    steps = [
        {"tool": "search", "args": {"query": "agent case"}},
        {"tool": "search", "args": {"query": ""}},
    ]
    violations = check_trajectory(steps, {"arg_conditions": {"search": {"query": lambda value: bool(value)}}})
    assert any("search.query" in v for v in violations), violations
''',
        hints=["同时准备一个完全合法轨迹和一个多处违规轨迹。", "顺序测试要让工具都出现但顺序反了。", "参数条件要覆盖同工具多次调用的后续调用。"],
        points=["Agent 轨迹约束", "违规聚合", "工具参数断言"],
    ),
    dict(
        id="lab-t-passk",
        kind="tests",
        course="agent",
        title="给 pass@k 统计函数写测试",
        level="medium",
        desc=r"""### 背景
代码生成、Agent 任务和评测平台常用 pass@k 估计“生成 k 次至少一次成功”的概率。这个指标看似是数学公式，实际实现里很容易在边界条件上出错：没有成功样本、全部成功、k 大于失败数、k 大于样本数、或者汇总时把字典对象本身当成真值。错误的 pass@k 会直接误导模型或 Agent 的质量判断。
### 被测函数的需求
`pass_at_k(n, c, k)` 中 `n` 是总运行次数，`c` 是成功次数，`k` 是抽样次数。参数要求 `n > 0`、`0 <= c <= n`、`1 <= k <= n`，否则抛 `ValueError`。当 `c == 0` 返回 `0.0`；当 `c == n` 返回 `1.0`；当 `k > n - c` 时必然抽到成功，返回 `1.0`；其他情况按 `1 - comb(n-c, k) / comb(n, k)` 计算。`summarize(runs)` 接收布尔值或带 `passed` 字段的字典列表，返回 `{"n": n, "c": c}`，并在 `k <= n` 时包含 `pass@1`、`pass@5`、`pass@10`。
### 怎么判分
变异体覆盖公式偏移、边界分支缺失、允许非法 k、全部成功处理错误、汇总时把所有非空字典都算成功等。测试应包含可手算的小样本和关键边界。
### 要求
测试直接调用 `pass_at_k` 和 `summarize`；只用 `assert`，不需要随机模拟。""",
        impl=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("invalid pass@k arguments")
    if c == 0:
        return 0.0
    if c == n:
        return 1.0
    if k > n - c:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def summarize(runs):
    n = len(runs)
    c = 0
    for run in runs:
        c += bool(run.get("passed")) if isinstance(run, dict) else bool(run)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
''',
        mutants=[
            dict(name="zero_success_formula", desc="c=0 时错误地继续走组合公式并返回 1。", hint="没有成功样本时 pass@k 必须是 0。", code=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("invalid pass@k arguments")
    if c == n:
        return 1.0
    if k > n - c:
        return 1.0
    return 1.0 if c == 0 else 1.0 - math.comb(n - c, k) / math.comb(n, k)


def summarize(runs):
    n = len(runs); c = sum(bool(r.get("passed")) if isinstance(r, dict) else bool(r) for r in runs)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
'''),
            dict(name="all_success_ratio", desc="c=n 时返回 c/n 以外路径虽常为 1，但和非法/边界组合混在一起容易误实现；这里让 k=1 返回近似但非精确。", hint="全部成功时应精确等于 1.0。", code=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("invalid pass@k arguments")
    if c == 0:
        return 0.0
    if c == n:
        return 0.999999
    if k > n - c:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def summarize(runs):
    n = len(runs); c = sum(bool(r.get("passed")) if isinstance(r, dict) else bool(r) for r in runs)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
'''),
            dict(name="rejects_k_gt_failures", desc="把 k > n-c 误判为非法参数，而不是返回必然成功的 1.0。", hint="当抽样次数超过失败样本数时，概率应直接是 1。", code=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("invalid pass@k arguments")
    if c == 0:
        return 0.0
    if c == n:
        return 1.0
    if k > n - c:
        raise ValueError("k cannot exceed failures")
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def summarize(runs):
    n = len(runs); c = sum(bool(r.get("passed")) if isinstance(r, dict) else bool(r) for r in runs)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
'''),
            dict(name="clamps_k_gt_n", desc="k 大于 n 时悄悄截断为 n，没有抛 ValueError。", hint="非法参数需要显式测试异常。", code=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0:
        raise ValueError("invalid pass@k arguments")
    k = min(k, n)
    if c == 0:
        return 0.0
    if c == n:
        return 1.0
    if k > n - c:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def summarize(runs):
    n = len(runs); c = sum(bool(r.get("passed")) if isinstance(r, dict) else bool(r) for r in runs)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
'''),
            dict(name="off_by_one_formula", desc="组合公式里使用 k-1，导致概率系统性偏低。", hint="选一个能手算的 n、c、k 校验公式。", code=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("invalid pass@k arguments")
    if c == 0:
        return 0.0
    if c == n:
        return 1.0
    if k > n - c:
        return 1.0
    return 1.0 - math.comb(n - c, k - 1) / math.comb(n, k)


def summarize(runs):
    n = len(runs); c = sum(bool(r.get("passed")) if isinstance(r, dict) else bool(r) for r in runs)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
'''),
            dict(name="summarize_truthy_dict", desc="summarize 把所有非空 dict 都当作成功，没有读取 passed 字段。", hint="汇总里放一个 {'passed': False}。", code=r'''import math


def pass_at_k(n, c, k):
    if n <= 0 or c < 0 or c > n or k <= 0 or k > n:
        raise ValueError("invalid pass@k arguments")
    if c == 0:
        return 0.0
    if c == n:
        return 1.0
    if k > n - c:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def summarize(runs):
    n = len(runs)
    c = sum(bool(run) for run in runs)
    result = {"n": n, "c": c}
    for k in (1, 5, 10):
        if k <= n:
            result[f"pass@{k}"] = pass_at_k(n, c, k)
    return result
'''),
        ],
        starter=r'''def test_pass_at_1_equals_success_rate_for_small_case():
    assert pass_at_k(4, 1, 1) == 0.25
''',
        solution=r'''def assert_raises_value_error(fn):
    try:
        fn()
    except ValueError:
        return
    assert False, "expected ValueError"


def test_pass_at_k_core_formula_and_edges():
    assert pass_at_k(4, 1, 1) == 0.25
    assert abs(pass_at_k(5, 2, 2) - 0.7) < 1e-12
    assert pass_at_k(5, 0, 3) == 0.0
    assert pass_at_k(5, 5, 1) == 1.0
    assert pass_at_k(5, 2, 4) == 1.0


def test_pass_at_k_rejects_invalid_k_greater_than_n():
    assert_raises_value_error(lambda: pass_at_k(3, 1, 4))


def test_summarize_counts_passed_field_and_selected_ks():
    runs = [{"passed": True}, {"passed": False}, True, False, {"passed": True}]
    summary = summarize(runs)
    assert summary["n"] == 5
    assert summary["c"] == 3
    assert summary["pass@1"] == 0.6
    assert summary["pass@5"] == 1.0
    assert "pass@10" not in summary
''',
        hints=["先测公式可手算的小样本，再测 c=0、c=n、k 边界。", "非法参数要用异常断言覆盖。", "summarize 中 dict 的真值和 passed 字段不是一回事。"],
        points=["pass@k 组合公式", "概率边界条件", "评测运行结果汇总"],
    ),
    dict(
        id="lab-t-redact",
        kind="tests",
        course="arch",
        title="给敏感信息脱敏函数写测试",
        level="medium",
        desc=r"""### 背景
日志、评测报告和 Agent 轨迹经常包含用户输入。脱敏函数如果漏掉邮箱、手机号、身份证号或银行卡号，会造成隐私风险；如果过度匹配，又会破坏普通数字、日期和业务编号，使问题排查困难。`redact(text)` 是架构类测试里很典型的安全边界题，需要同时考虑“该替换的替换”和“不该替换的不替换”。
### 被测函数的需求
函数返回脱敏后的字符串。邮箱替换为 `<EMAIL>`，手机号替换为 `<PHONE>`，18 位身份证号替换为 `<ID>`，16 到 19 位连续银行卡号替换为 `<CARD>`。手机号按常见 11 位格式匹配：以 `1` 开头，第二位为 `3` 到 `9`，且前后不能是更长数字的一部分。身份证号是 17 位数字加 1 位数字或 `X/x`，前后不能是字母数字的一部分。银行卡号是连续 16–19 位数字，前后不能接数字。函数不能误伤普通短数字、日期如 `2026-10-21`、版本号或 11 位但不符合手机号号段的数字。若一个片段同时可能被多种规则触及，应优先按更具体的身份证号识别。
### 怎么判分
变异体会模拟过度匹配数字、漏掉 X 结尾身份证、手机号号段过宽、只支持 16 位卡号、邮箱不支持加号、先匹配银行卡导致身份证被破坏等。好的测试要同时写正例和反例。
### 要求
测试直接调用 `redact`；只用 `assert`，不要引入第三方库。""",
        impl=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = CARD_RE.sub("<CARD>", text)
    return text
''',
        mutants=[
            dict(name="over_redacts_long_numbers", desc="把 8 位以上数字都当敏感信息，误伤日期和普通编号。", hint="除了敏感号码，也要测普通数字应保留。", code=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{8,19}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = CARD_RE.sub("<CARD>", text)
    return text
'''),
            dict(name="misses_id_with_x", desc="身份证最后一位只允许数字，漏掉 X/x 校验位。", hint="身份证号末位不一定是数字。", code=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{18}(?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = CARD_RE.sub("<CARD>", text)
    return text
'''),
            dict(name="phone_too_broad", desc="任意 11 位数字都按手机号替换，误伤普通数字。", hint="手机号号段有格式限制。", code=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = CARD_RE.sub("<CARD>", text)
    return text
'''),
            dict(name="card_only_16_digits", desc="银行卡只匹配 16 位，漏掉 19 位卡号。", hint="银行卡长度是一个范围，不是单点。", code=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{16}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = CARD_RE.sub("<CARD>", text)
    return text
'''),
            dict(name="email_no_plus", desc="邮箱正则不支持加号别名，漏掉常见邮箱格式。", hint="邮箱本地部分可能包含 +。", code=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = CARD_RE.sub("<CARD>", text)
    return text
'''),
            dict(name="card_before_id", desc="先匹配银行卡，导致 18 位加 X 的身份证前 17 或 18 位被错误替换。", hint="重叠模式要关注替换顺序。", code=r'''import re


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_RE = re.compile(r"(?<![A-Za-z0-9])\d{17}[\dXx](?![A-Za-z0-9])")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")


def redact(text):
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = CARD_RE.sub("<CARD>", text)
    text = ID_RE.sub("<ID>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    return text
'''),
        ],
        starter=r'''def test_redacts_simple_email():
    assert redact('mail a@example.com') == 'mail <EMAIL>'
''',
        solution=r'''def test_redacts_all_supported_sensitive_types():
    text = 'phone 13812345678 email dev+qa@example.com id 11010519491231002X card 6222021234567890123'
    assert redact(text) == 'phone <PHONE> email <EMAIL> id <ID> card <CARD>'


def test_does_not_redact_dates_short_numbers_or_invalid_phone_like_digits():
    text = 'date 2026-10-21 build 12345678 code 20123456789 version 1.2.3'
    assert redact(text) == text


def test_redacts_lowercase_x_id_as_id_not_partial_card():
    assert redact('id=11010519491231002x') == 'id=<ID>'


def test_card_length_range_includes_16_and_19_digits():
    assert redact('cards 1234567890123456 1234567890123456789') == 'cards <CARD> <CARD>'
''',
        hints=["正例要覆盖四类敏感信息，反例要覆盖普通数字和日期。", "手机号、身份证、银行卡都需要边界，不能只测一种长度。", "身份证末位 X 与银行卡数字串存在重叠风险，注意替换顺序。"],
        points=["隐私脱敏正则", "误伤控制", "重叠模式优先级"],
    ),
    dict(
        id="lab-t-gate",
        kind="tests",
        course="dev",
        title="给回归准入门禁写测试",
        level="medium",
        desc=r"""### 背景
模型、Agent 或服务发布前，经常要比较 baseline 与 candidate 的回归结果。一个合格的门禁不能只看总体通过率：总体小幅下降可能掩盖某个标签的大幅退化；历史已失败用例和新增失败用例也要分清；阈值边界必须稳定，否则会出现同一批结果今天能发、明天不能发的争议。
### 被测函数的需求
`regression_gate(baseline, candidate, rules)` 返回 `{"passed": bool, "reasons": list[str]}`。`baseline` 和 `candidate` 都是用例结果列表，每项至少有 `id`、`passed`，可选 `labels` 字段（字符串列表）。总体通过率按各自列表中 `passed` 为真的比例计算；若 `baseline_rate - candidate_rate` 大于 `rules["max_overall_drop"]`，加入原因。对 baseline 与 candidate 中出现过的每个标签分别计算通过率；若某标签下降大于 `rules["max_label_drop"]`，加入原因。新增失败数指 candidate 中失败，且 baseline 中不存在该 id 或 baseline 中该 id 通过的用例数量；若数量大于 `rules["max_new_failures"]`，加入原因。下降等于阈值仍允许通过，只有严格大于才失败。空原因表示通过。
### 怎么判分
变异体包含把阈值当最低通过率、忽略分标签退化、把所有失败都算新增、漏算全新失败用例、阈值用 `>=`、只按总体判断等。测试应分别覆盖总体、标签、新增失败和阈值等号边界。
### 要求
测试直接调用 `regression_gate`；只用 `assert`，不要访问外部服务。""",
        impl=r'''def _is_passed(case):
    return bool(case.get("passed"))


def _rate(cases):
    if not cases:
        return 1.0
    return sum(_is_passed(case) for case in cases) / len(cases)


def _labels(case):
    labels = case.get("labels", [])
    if isinstance(labels, str):
        return [labels]
    return list(labels)


def regression_gate(baseline, candidate, rules):
    reasons = []
    overall_drop = _rate(baseline) - _rate(candidate)
    if overall_drop > rules.get("max_overall_drop", 0):
        reasons.append(f"overall pass rate dropped by {overall_drop:.3f}")

    all_labels = sorted({label for case in baseline + candidate for label in _labels(case)})
    for label in all_labels:
        base_cases = [case for case in baseline if label in _labels(case)]
        cand_cases = [case for case in candidate if label in _labels(case)]
        drop = _rate(base_cases) - _rate(cand_cases)
        if drop > rules.get("max_label_drop", 0):
            reasons.append(f"label {label} pass rate dropped by {drop:.3f}")

    baseline_by_id = {case.get("id"): case for case in baseline}
    new_failures = 0
    for case in candidate:
        if _is_passed(case):
            continue
        old = baseline_by_id.get(case.get("id"))
        if old is None or _is_passed(old):
            new_failures += 1
    if new_failures > rules.get("max_new_failures", 0):
        reasons.append(f"new failures: {new_failures}")
    return {"passed": not reasons, "reasons": reasons}
''',
        mutants=[
            dict(name="overall_threshold_as_absolute_rate", desc="把 max_overall_drop 当成 candidate 最低通过率，而不是下降阈值。", hint="baseline 不是 100% 时，总体下降和候选绝对通过率不同。", code=r'''def _is_passed(case):
    return bool(case.get("passed"))


def _rate(cases):
    return 1.0 if not cases else sum(_is_passed(case) for case in cases) / len(cases)


def _labels(case):
    labels = case.get("labels", [])
    return [labels] if isinstance(labels, str) else list(labels)


def regression_gate(baseline, candidate, rules):
    reasons = []
    if _rate(candidate) < rules.get("max_overall_drop", 0):
        reasons.append("overall pass rate too low")
    all_labels = sorted({label for case in baseline + candidate for label in _labels(case)})
    for label in all_labels:
        base_cases = [case for case in baseline if label in _labels(case)]
        cand_cases = [case for case in candidate if label in _labels(case)]
        drop = _rate(base_cases) - _rate(cand_cases)
        if drop > rules.get("max_label_drop", 0):
            reasons.append(f"label {label} pass rate dropped by {drop:.3f}")
    baseline_by_id = {case.get("id"): case for case in baseline}
    new_failures = sum((not _is_passed(case)) and (case.get("id") not in baseline_by_id or _is_passed(baseline_by_id[case.get("id")])) for case in candidate)
    if new_failures > rules.get("max_new_failures", 0):
        reasons.append(f"new failures: {new_failures}")
    return {"passed": not reasons, "reasons": reasons}
'''),
            dict(name="ignores_label_drop", desc="只看总体通过率和新增失败，忽略分标签下降。", hint="构造总体不变但某个标签明显下降的样本。", code=r'''def _is_passed(case):
    return bool(case.get("passed"))


def _rate(cases):
    return 1.0 if not cases else sum(_is_passed(case) for case in cases) / len(cases)


def regression_gate(baseline, candidate, rules):
    reasons = []
    drop = _rate(baseline) - _rate(candidate)
    if drop > rules.get("max_overall_drop", 0):
        reasons.append(f"overall pass rate dropped by {drop:.3f}")
    baseline_by_id = {case.get("id"): case for case in baseline}
    new_failures = sum((not _is_passed(case)) and (case.get("id") not in baseline_by_id or _is_passed(baseline_by_id[case.get("id")])) for case in candidate)
    if new_failures > rules.get("max_new_failures", 0):
        reasons.append(f"new failures: {new_failures}")
    return {"passed": not reasons, "reasons": reasons}
'''),
            dict(name="counts_all_candidate_failures_as_new", desc="把 candidate 中所有失败都算新增失败，包括 baseline 已经失败的历史问题。", hint="历史已失败用例不应算新增失败。", code=r'''def _is_passed(case):
    return bool(case.get("passed"))


def _rate(cases):
    return 1.0 if not cases else sum(_is_passed(case) for case in cases) / len(cases)


def _labels(case):
    labels = case.get("labels", [])
    return [labels] if isinstance(labels, str) else list(labels)


def regression_gate(baseline, candidate, rules):
    reasons = []
    if _rate(baseline) - _rate(candidate) > rules.get("max_overall_drop", 0):
        reasons.append("overall pass rate dropped")
    for label in sorted({label for case in baseline + candidate for label in _labels(case)}):
        base_cases = [case for case in baseline if label in _labels(case)]
        cand_cases = [case for case in candidate if label in _labels(case)]
        if _rate(base_cases) - _rate(cand_cases) > rules.get("max_label_drop", 0):
            reasons.append(f"label {label} pass rate dropped")
    new_failures = sum(not _is_passed(case) for case in candidate)
    if new_failures > rules.get("max_new_failures", 0):
        reasons.append(f"new failures: {new_failures}")
    return {"passed": not reasons, "reasons": reasons}
'''),
            dict(name="misses_brand_new_failure", desc="只统计 baseline 中通过后变失败的用例，漏掉 candidate 新增且失败的 id。", hint="新增失败包括 baseline 不存在的失败用例。", code=r'''def _is_passed(case):
    return bool(case.get("passed"))


def _rate(cases):
    return 1.0 if not cases else sum(_is_passed(case) for case in cases) / len(cases)


def _labels(case):
    labels = case.get("labels", [])
    return [labels] if isinstance(labels, str) else list(labels)


def regression_gate(baseline, candidate, rules):
    reasons = []
    if _rate(baseline) - _rate(candidate) > rules.get("max_overall_drop", 0):
        reasons.append("overall pass rate dropped")
    for label in sorted({label for case in baseline + candidate for label in _labels(case)}):
        base_cases = [case for case in baseline if label in _labels(case)]
        cand_cases = [case for case in candidate if label in _labels(case)]
        if _rate(base_cases) - _rate(cand_cases) > rules.get("max_label_drop", 0):
            reasons.append(f"label {label} pass rate dropped")
    baseline_by_id = {case.get("id"): case for case in baseline}
    new_failures = sum((not _is_passed(case)) and (case.get("id") in baseline_by_id and _is_passed(baseline_by_id[case.get("id")])) for case in candidate)
    if new_failures > rules.get("max_new_failures", 0):
        reasons.append(f"new failures: {new_failures}")
    return {"passed": not reasons, "reasons": reasons}
'''),
            dict(name="threshold_ge_bug", desc="下降或新增失败数等于阈值时也判失败。", hint="阈值语义是严格大于才失败。", code=r'''def _is_passed(case):
    return bool(case.get("passed"))


def _rate(cases):
    return 1.0 if not cases else sum(_is_passed(case) for case in cases) / len(cases)


def _labels(case):
    labels = case.get("labels", [])
    return [labels] if isinstance(labels, str) else list(labels)


def regression_gate(baseline, candidate, rules):
    reasons = []
    overall_drop = _rate(baseline) - _rate(candidate)
    if overall_drop >= rules.get("max_overall_drop", 0):
        reasons.append(f"overall pass rate dropped by {overall_drop:.3f}")
    for label in sorted({label for case in baseline + candidate for label in _labels(case)}):
        base_cases = [case for case in baseline if label in _labels(case)]
        cand_cases = [case for case in candidate if label in _labels(case)]
        drop = _rate(base_cases) - _rate(cand_cases)
        if drop >= rules.get("max_label_drop", 0):
            reasons.append(f"label {label} pass rate dropped by {drop:.3f}")
    baseline_by_id = {case.get("id"): case for case in baseline}
    new_failures = sum((not _is_passed(case)) and (case.get("id") not in baseline_by_id or _is_passed(baseline_by_id[case.get("id")])) for case in candidate)
    if new_failures >= rules.get("max_new_failures", 0):
        reasons.append(f"new failures: {new_failures}")
    return {"passed": not reasons, "reasons": reasons}
'''),
        ],
        starter=r'''def test_gate_passes_when_results_identical():
    cases = [{"id": "a", "passed": True, "labels": ["smoke"]}]
    assert regression_gate(cases, cases, {"max_overall_drop": 0, "max_label_drop": 0, "max_new_failures": 0})["passed"] is True
''',
        solution=r'''def test_overall_drop_uses_delta_not_absolute_candidate_rate():
    baseline = [
        {"id": "a", "passed": True, "labels": ["core"]},
        {"id": "b", "passed": True, "labels": ["core"]},
        {"id": "c", "passed": False, "labels": ["edge"]},
        {"id": "d", "passed": False, "labels": ["edge"]},
    ]
    candidate = [
        {"id": "a", "passed": True, "labels": ["core"]},
        {"id": "b", "passed": False, "labels": ["core"]},
        {"id": "c", "passed": False, "labels": ["edge"]},
        {"id": "d", "passed": False, "labels": ["edge"]},
    ]
    result = regression_gate(baseline, candidate, {"max_overall_drop": 0.2, "max_label_drop": 1.0, "max_new_failures": 9})
    assert result["passed"] is False
    assert any("overall" in reason for reason in result["reasons"]), result


def test_label_drop_can_fail_even_when_overall_allowed():
    baseline = [
        {"id": "a", "passed": True, "labels": ["search"]},
        {"id": "b", "passed": True, "labels": ["search"]},
        {"id": "c", "passed": False, "labels": ["chat"]},
        {"id": "d", "passed": False, "labels": ["chat"]},
    ]
    candidate = [
        {"id": "a", "passed": False, "labels": ["search"]},
        {"id": "b", "passed": True, "labels": ["search"]},
        {"id": "c", "passed": True, "labels": ["chat"]},
        {"id": "d", "passed": False, "labels": ["chat"]},
    ]
    result = regression_gate(baseline, candidate, {"max_overall_drop": 0.5, "max_label_drop": 0.4, "max_new_failures": 9})
    assert result["passed"] is False
    assert any("search" in reason for reason in result["reasons"]), result


def test_new_failures_exclude_historical_failures_but_include_brand_new_ids():
    baseline = [
        {"id": "old_bad", "passed": False, "labels": ["core"]},
        {"id": "old_good", "passed": True, "labels": ["core"]},
    ]
    candidate = [
        {"id": "old_bad", "passed": False, "labels": ["core"]},
        {"id": "old_good", "passed": True, "labels": ["core"]},
        {"id": "new_bad", "passed": False, "labels": ["core"]},
    ]
    result = regression_gate(baseline, candidate, {"max_overall_drop": 1.0, "max_label_drop": 1.0, "max_new_failures": 0})
    assert result["passed"] is False
    assert any("new failures: 1" in reason for reason in result["reasons"]), result


def test_equal_to_threshold_still_passes():
    baseline = [
        {"id": "a", "passed": True, "labels": ["x"]},
        {"id": "b", "passed": True, "labels": ["x"]},
    ]
    candidate = [
        {"id": "a", "passed": True, "labels": ["x"]},
        {"id": "b", "passed": False, "labels": ["x"]},
    ]
    result = regression_gate(baseline, candidate, {"max_overall_drop": 0.5, "max_label_drop": 0.5, "max_new_failures": 1})
    assert result == {"passed": True, "reasons": []}
''',
        hints=["把总体下降、分标签下降、新增失败拆成独立用例。", "历史已失败和全新失败 id 要分开测。", "阈值等号边界是严格大于规则的关键。"],
        points=["回归门禁指标", "分组统计", "新增失败与阈值边界"],
    ),
]
