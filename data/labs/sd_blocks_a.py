LABS = [
    dict(
        id="lab-sd-p1",
        course="sd",
        title="Fan-out 编排器的同步状态机",
        level="hard",
        desc='''### 背景
真实服务里，fan-out 编排器会把一个大请求拆成多个子任务，并发发给多个下游，再聚合结果。浏览器里的 Python 不能开线程、不能 sleep，也不适合启动事件循环，所以本题把并发改写成同步状态机：你显式调用 `poll()` 启动可运行任务，再用 `complete()`、`fail()`、`expire()` 推动状态变化。这样训练的是同一件事：并发上限、重试次数、运行中任务表、上下文快照和超时处理。

### 要实现什么
实现 `FanoutOrchestrator(tasks, limit, max_attempts, timeout, clock, context=None)`。`tasks` 是任务 id 列表，`limit` 是同时运行上限，`clock()` 返回当前时间。`poll()` 在不超过上限的前提下，从等待队列启动任务，返回若干 `(task_id, attempt, context_snapshot)`；每次启动要记录开始时间和第几次尝试。`complete(task_id, result)` 记录成功结果。`fail(task_id, error)` 记录失败；未达到最大尝试次数时放回队列，达到后进入最终错误。`expire()` 扫描运行中任务，超过 `timeout` 的按失败处理。

### 工程提醒
真实工程版需要锁保护队列和运行表，但不要把锁包住真实下游调用；子任务上下文要从父上下文复制，避免一个子任务写坏另一个子任务；超时和重试要有最大次数，否则会把队列拖死。''',
        starter='''class FanoutOrchestrator:
    """Synchronous state machine for bounded fan-out orchestration."""

    def __init__(self, tasks, limit, max_attempts, timeout, clock, context=None):
        raise NotImplementedError

    def poll(self):
        """Start as many pending tasks as allowed and return start records."""
        raise NotImplementedError

    def complete(self, task_id, result):
        """Mark a running task as successful."""
        raise NotImplementedError

    def fail(self, task_id, error):
        """Mark a running task as failed and retry if allowed."""
        raise NotImplementedError

    def expire(self):
        """Fail timed-out running tasks and return expired task ids."""
        raise NotImplementedError

    def done(self):
        """Return True when nothing is pending or running."""
        raise NotImplementedError
''',
        tests='''def test_respects_limit_and_starts_next_after_completion():
    """poll 不能超过并发上限，完成一个后才能补启动下一个。"""
    now = [0]
    orch = FanoutOrchestrator(["a", "b", "c"], limit=2, max_attempts=2, timeout=10, clock=lambda: now[0])
    started = orch.poll()
    assert [x[0] for x in started] == ["a", "b"], started
    assert set(orch.running) == {"a", "b"}, orch.running
    orch.complete("a", "A")
    started = orch.poll()
    assert [x[0] for x in started] == ["c"], started
    assert orch.results == {"a": "A"}, orch.results


def test_failure_retries_until_success():
    """失败未超过次数时要回到 pending，并在下一轮递增 attempt。"""
    now = [0]
    orch = FanoutOrchestrator(["a"], 1, 3, 10, lambda: now[0])
    assert orch.poll()[0][1] == 1
    orch.fail("a", "temporary")
    assert "a" not in orch.running and list(orch.pending) == ["a"]
    assert orch.poll()[0][1] == 2
    orch.complete("a", "ok")
    assert orch.results["a"] == "ok" and orch.errors == {}, orch.errors


def test_timeout_uses_same_retry_path():
    """超时任务要离开 running，并按普通失败规则决定是否重试。"""
    now = [0]
    orch = FanoutOrchestrator(["a"], 1, 2, 5, lambda: now[0])
    orch.poll()
    now[0] = 6
    expired = orch.expire()
    assert expired == ["a"], expired
    assert list(orch.pending) == ["a"], orch.pending
    assert orch.poll()[0][1] == 2


def test_context_snapshot_is_isolated_per_attempt():
    """返回给子任务的上下文应是快照，不能共享同一个可变字典。"""
    now = [0]
    base = {"trace_id": "t1"}
    orch = FanoutOrchestrator(["a", "b"], 2, 1, 10, lambda: now[0], context=base)
    first, second = orch.poll()
    first[2]["trace_id"] = "changed"
    assert base["trace_id"] == "t1", base
    assert second[2]["trace_id"] == "t1", second
    assert first[2]["task_id"] == "a" and second[2]["attempt"] == 1
''',
        hidden='''def test_final_failure_after_max_attempts():
    """达到最大尝试次数后不再回队列，而是进入 errors。"""
    now = [0]
    orch = FanoutOrchestrator(["a"], 1, 2, 10, lambda: now[0])
    orch.poll(); orch.fail("a", "e1")
    orch.poll(); orch.fail("a", "e2")
    assert list(orch.pending) == [] and orch.running == {}, orch.pending
    assert "a" in orch.errors and "e2" in orch.errors["a"], orch.errors
    assert orch.done()


def test_success_is_not_retried_after_later_poll():
    """成功结果是终态，后续 poll 不应再次启动同一任务。"""
    now = [0]
    orch = FanoutOrchestrator(["a", "b"], 1, 3, 10, lambda: now[0])
    orch.poll(); orch.complete("a", 1)
    orch.poll(); orch.complete("b", 2)
    assert orch.poll() == []
    assert orch.results == {"a": 1, "b": 2}
    assert orch.done()
''',
        solution='''from collections import deque


class FanoutOrchestrator:
    def __init__(self, tasks, limit, max_attempts, timeout, clock, context=None):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.pending = deque(tasks)
        self.limit = limit
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.clock = clock
        self.context = dict(context or {})
        self.running = {}
        self.attempts = {task: 0 for task in tasks}
        self.results = {}
        self.errors = {}

    def poll(self):
        started = []
        while self.pending and len(self.running) < self.limit:
            task_id = self.pending.popleft()
            if task_id in self.results or task_id in self.errors or task_id in self.running:
                continue
            self.attempts[task_id] = self.attempts.get(task_id, 0) + 1
            attempt = self.attempts[task_id]
            snapshot = dict(self.context)
            snapshot["task_id"] = task_id
            snapshot["attempt"] = attempt
            self.running[task_id] = {"attempt": attempt, "started_at": self.clock(), "context": snapshot}
            started.append((task_id, attempt, snapshot))
        return started

    def complete(self, task_id, result):
        if task_id not in self.running:
            raise KeyError(task_id)
        self.running.pop(task_id)
        self.results[task_id] = result

    def fail(self, task_id, error):
        if task_id not in self.running:
            raise KeyError(task_id)
        self.running.pop(task_id)
        if self.attempts.get(task_id, 0) < self.max_attempts:
            self.pending.append(task_id)
        else:
            self.errors[task_id] = str(error)

    def expire(self):
        now = self.clock()
        expired = [task_id for task_id, rec in list(self.running.items()) if now - rec["started_at"] >= self.timeout]
        for task_id in expired:
            self.fail(task_id, "timeout")
        return expired

    def done(self):
        return not self.pending and not self.running
''',
        hints=["先只维护 pending 和 running，确认 poll 永远不超过 limit。", "attempt 在启动时递增，失败时根据次数决定回队列还是进 errors。", "上下文用 dict 复制；真实并发版再加锁，不要在本题里开线程。"],
        points=["有界并发状态机", "失败重试和超时", "上下文快照隔离"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p2",
        course="sd",
        title="DAG 分层调度与失败传播",
        level="hard",
        desc='''### 背景
DAG 调度常见于构建系统、数据流水线和批处理编排。真实系统会有 worker、队列和并发执行。浏览器环境不适合启动并发 worker，所以本题把调度器写成同步状态机：`start_ready()` 找出当前入度为 0 的任务并标记运行，`succeed()` 推进下游入度，`fail()` 把失败传播给所有还没运行的后继。这样能专注训练两个核心状态：每个节点还差几个前置依赖，以及每个节点有哪些下游。

### 要实现什么
实现 `DagScheduler(tasks, dependencies)`。`tasks` 是任务 id 列表，`dependencies` 由 `(before, after)` 组成，表示 `after` 必须等 `before` 成功。构造时要建立图并拒绝未知节点和环。`start_ready()` 返回当前可运行任务列表，并把它们标记为 `running`，避免重复返回。`succeed(task)` 只能用于运行中的任务；成功后把它的下游入度减一。`fail(task, error=None)` 把该任务标记失败，并把所有依赖它的未开始后继递归标记为 `blocked`。提供 `status(task)` 和 `is_done()` 便于测试。

### 工程提醒
真实工程版还要考虑任务重试、部分重跑、持久化状态和 worker 心跳。本题不做线程和网络，只检查图算法和状态转移是否稳定。''',
        starter='''class DagScheduler:
    """Synchronous DAG scheduler with failure propagation."""

    def __init__(self, tasks, dependencies):
        raise NotImplementedError

    def start_ready(self):
        """Mark currently ready tasks as running and return them."""
        raise NotImplementedError

    def succeed(self, task):
        """Mark a running task as done and release children if possible."""
        raise NotImplementedError

    def fail(self, task, error=None):
        """Mark a running task as failed and block downstream tasks."""
        raise NotImplementedError

    def status(self, task):
        """Return one task status."""
        raise NotImplementedError

    def is_done(self):
        """Return True when every task is terminal."""
        raise NotImplementedError
''',
        tests='''def test_layered_execution_order():
    """A、B 都完成后，C 才能启动。"""
    sched = DagScheduler(["A", "B", "C"], [("A", "C"), ("B", "C")])
    assert sched.start_ready() == ["A", "B"]
    sched.succeed("A")
    assert sched.start_ready() == []
    sched.succeed("B")
    assert sched.start_ready() == ["C"]
    sched.succeed("C")
    assert sched.is_done()


def test_failure_blocks_downstream_recursively():
    """上游失败时，所有未开始下游都应进入 blocked。"""
    sched = DagScheduler(["A", "B", "C"], [("A", "B"), ("B", "C")])
    assert sched.start_ready() == ["A"]
    sched.fail("A", "boom")
    assert sched.status("A") == "failed"
    assert sched.status("B") == "blocked"
    assert sched.status("C") == "blocked"
    assert sched.is_done()


def test_multiple_parents_wait_for_all_successes():
    """一个父节点成功不够，入度必须降到 0 才能启动。"""
    sched = DagScheduler(["A", "B", "C", "D"], [("A", "D"), ("B", "D"), ("C", "D")])
    assert sched.start_ready() == ["A", "B", "C"]
    sched.succeed("A"); sched.succeed("B")
    assert sched.start_ready() == []
    sched.succeed("C")
    assert sched.start_ready() == ["D"]


def test_cycle_is_rejected_at_construction():
    """有环时不存在合法分层，构造阶段要失败。"""
    try:
        DagScheduler(["A", "B"], [("A", "B"), ("B", "A")])
    except ValueError as exc:
        assert "cycle" in str(exc).lower() or "环" in str(exc)
    else:
        raise AssertionError("cycle should be rejected")
''',
        hidden='''def test_unknown_dependency_node_is_rejected():
    """依赖边引用不存在节点时，要尽早报错。"""
    try:
        DagScheduler(["A"], [("A", "B")])
    except ValueError as exc:
        assert "unknown" in str(exc).lower() or "未知" in str(exc)
    else:
        raise AssertionError("unknown node should be rejected")


def test_terminal_task_cannot_be_completed_twice():
    """完成同一任务两次会重复扣下游入度，必须拒绝。"""
    sched = DagScheduler(["A", "B"], [("A", "B")])
    sched.start_ready()
    sched.succeed("A")
    try:
        sched.succeed("A")
    except ValueError:
        pass
    else:
        raise AssertionError("double success should fail")
    assert sched.start_ready() == ["B"]
''',
        solution='''from collections import deque


class DagScheduler:
    def __init__(self, tasks, dependencies):
        self.tasks = list(tasks)
        known = set(self.tasks)
        if len(known) != len(self.tasks):
            raise ValueError("duplicate task")
        self.children = {task: [] for task in self.tasks}
        self.indegree = {task: 0 for task in self.tasks}
        for before, after in dependencies:
            if before not in known or after not in known:
                raise ValueError("unknown dependency node")
            self.children[before].append(after)
            self.indegree[after] += 1
        self._check_acyclic()
        self._status = {task: "pending" for task in self.tasks}
        self.errors = {}

    def _check_acyclic(self):
        indegree = dict(self.indegree)
        queue = deque([task for task in self.tasks if indegree[task] == 0])
        seen = 0
        while queue:
            task = queue.popleft()
            seen += 1
            for child in self.children[task]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if seen != len(self.tasks):
            raise ValueError("cycle detected")

    def start_ready(self):
        ready = [task for task in self.tasks if self._status[task] == "pending" and self.indegree[task] == 0]
        for task in ready:
            self._status[task] = "running"
        return ready

    def succeed(self, task):
        if self._status.get(task) != "running":
            raise ValueError("task is not running")
        self._status[task] = "done"
        for child in self.children[task]:
            if self._status[child] == "pending":
                self.indegree[child] -= 1

    def fail(self, task, error=None):
        if self._status.get(task) != "running":
            raise ValueError("task is not running")
        self._status[task] = "failed"
        self.errors[task] = error
        for child in self.children[task]:
            self._block(child)

    def _block(self, task):
        if self._status[task] != "pending":
            return
        self._status[task] = "blocked"
        for child in self.children[task]:
            self._block(child)

    def status(self, task):
        return self._status[task]

    def is_done(self):
        return all(status in {"done", "failed", "blocked"} for status in self._status.values())
''',
        hints=["先从 dependencies 建 children 和 indegree。", "start_ready 要把任务改成 running，否则会重复启动。", "失败传播只覆盖 pending 下游；已完成任务不能被回滚。"],
        points=["拓扑调度", "任务状态机", "失败向下游传播"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p3",
        course="sd",
        title="最小工具调用循环",
        level="medium",
        desc='''### 背景
最小智能循环不是神秘逻辑，而是一段消息状态机：把历史消息交给模型，模型要么给最终回答，要么要求调用工具；工具结果再作为 `tool` 消息回填给模型。浏览器环境里不需要真实网络模型，本题用注入的 `model(history)` 和普通函数工具模拟。这样可以稳定测试消息协议、工具调用顺序、异常回填和停止条件。

### 要实现什么
实现 `run_agent_loop(model, tools, messages, max_steps)`。输入的 `messages` 不能被原地修改。`model(history)` 可以返回字符串，表示最终回答；也可以返回字典，包含 `content` 和 `tool_calls`。每个 tool call 至少有 `id`、`name`、`arguments`，其中 `arguments` 可以是字典或 JSON 字符串。遇到工具调用时，要追加一条 assistant 消息，再按顺序执行全部工具，并为每个工具追加 `role="tool"`、`tool_call_id` 和字符串化 `content`。未知工具或工具异常也要变成 tool 消息，不能让主循环崩溃。超过 `max_steps` 仍未得到最终回答时，返回 `status="max_steps"`。

### 工程提醒
真实工程版还要处理模型超时、工具超时、参数 schema、审计日志和消息裁剪。本题只实现同步循环，不要开线程、不要 sleep、不要联网。''',
        starter='''def run_agent_loop(model, tools, messages, max_steps):
    """Run a synchronous model/tool loop until final answer or max_steps."""
    raise NotImplementedError
''',
        tests='''def test_plain_text_finishes_immediately():
    """模型直接返回文本时，循环应立即结束。"""
    original = [{"role": "user", "content": "hi"}]
    result = run_agent_loop(lambda history: "hello", {}, original, 3)
    assert result["status"] == "final" and result["content"] == "hello", result
    assert original == [{"role": "user", "content": "hi"}], "不能修改输入列表"


def test_tool_call_is_appended_and_fed_back():
    """工具结果要作为 tool 消息回填给下一轮模型。"""
    def model(history):
        if not any(m.get("role") == "tool" for m in history):
            return {"content": "need", "tool_calls": [{"id": "c1", "name": "add", "arguments": {"a": 2, "b": 3}}]}
        assert history[-1]["role"] == "tool" and history[-1]["content"] == "5", history
        return "done"
    result = run_agent_loop(model, {"add": lambda a, b: a + b}, [], 5)
    assert result["status"] == "final" and result["content"] == "done", result


def test_multiple_tools_run_in_order():
    """同一轮多个工具调用必须按模型给出的顺序执行。"""
    order = []
    def model(history):
        if not order:
            return {"tool_calls": [
                {"id": "a", "name": "first", "arguments": {}},
                {"id": "b", "name": "second", "arguments": {}},
            ]}
        assert order == ["first", "second"], order
        return "ok"
    tools = {"first": lambda: order.append("first") or "1", "second": lambda: order.append("second") or "2"}
    result = run_agent_loop(model, tools, [], 3)
    assert result["content"] == "ok"


def test_max_steps_stops_infinite_tool_loop():
    """模型一直请求工具时，必须靠 max_steps 停止。"""
    def model(history):
        return {"tool_calls": [{"id": "x", "name": "noop", "arguments": {}}]}
    result = run_agent_loop(model, {"noop": lambda: "ok"}, [], 2)
    assert result["status"] == "max_steps", result
    assert "max" in result["content"].lower(), result
''',
        hidden='''def test_json_arguments_and_non_string_result():
    """arguments 可以是 JSON 字符串，工具返回值要转成字符串。"""
    def model(history):
        if not any(m.get("role") == "tool" for m in history):
            return {"tool_calls": [{"id": "j", "name": "pack", "arguments": "{\\\"x\\\": 7}"}]}
        assert history[-1]["content"] == "{'x': 7}", history[-1]
        return "ok"
    result = run_agent_loop(model, {"pack": lambda x: {"x": x}}, [], 3)
    assert result["content"] == "ok"


def test_unknown_tool_and_exception_are_returned_as_tool_messages():
    """未知工具和工具异常都要回填，而不是抛出到循环外。"""
    seen = []
    def bad():
        raise RuntimeError("boom")
    def model(history):
        tools = [m for m in history if m.get("role") == "tool"]
        if not tools:
            return {"tool_calls": [{"id": "u", "name": "missing", "arguments": {}}, {"id": "b", "name": "bad", "arguments": {}}]}
        seen.extend(t["content"] for t in tools)
        return "handled"
    result = run_agent_loop(model, {"bad": bad}, [], 3)
    assert result["status"] == "final"
    assert any("unknown" in x.lower() or "not found" in x.lower() for x in seen), seen
    assert any("RuntimeError" in x and "boom" in x for x in seen), seen
''',
        solution='''import json


def run_agent_loop(model, tools, messages, max_steps):
    history = [dict(message) for message in messages]
    for step in range(max_steps):
        response = model([dict(message) for message in history])
        if isinstance(response, str):
            return {"status": "final", "content": response, "messages": history, "steps": step + 1}

        tool_calls = response.get("tool_calls") or []
        content = response.get("content", "")
        assistant_message = {"role": "assistant", "content": content, "tool_calls": tool_calls}
        history.append(assistant_message)
        if not tool_calls:
            return {"status": "final", "content": content, "messages": history, "steps": step + 1}

        for call in tool_calls:
            name = call.get("name")
            raw_args = call.get("arguments", {})
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
            except Exception as exc:
                result = f"argument error: {type(exc).__name__}: {exc}"
            else:
                if name not in tools:
                    result = f"unknown tool: {name}"
                else:
                    try:
                        result = tools[name](**args)
                    except Exception as exc:
                        result = f"{type(exc).__name__}: {exc}"
            history.append({"role": "tool", "tool_call_id": call.get("id"), "content": str(result)})
    return {"status": "max_steps", "content": f"max_steps reached: {max_steps}", "messages": history, "steps": max_steps}
''',
        hints=["把 history 复制一份再改，不要原地修改输入。", "模型返回字符串是终态；返回 tool_calls 就追加 assistant 和 tool 消息。", "工具错误也是消息协议的一部分，要写回 history。"],
        points=["消息协议", "工具调用回填", "停止条件"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p4",
        course="sd",
        title="上下文预算裁剪且不留下孤儿工具消息",
        level="medium",
        desc='''### 背景
长对话进入模型前通常要按 token 预算裁剪。最容易错的地方不是少算几个 token，而是破坏消息结构：assistant 发起 tool_calls 后，后面的 tool 结果必须一起保留或一起丢弃；不能留下没有父调用的孤儿 tool 消息。浏览器环境里没有真实 tokenizer，所以本题注入 `token_counter(message)`，把裁剪逻辑做成纯同步函数。

### 要实现什么
实现 `trim_messages(messages, max_tokens, token_counter)`。输入是消息列表，输出新的消息列表，不能修改原列表。先把消息切成 unit：普通消息单独成 unit；带 `tool_calls` 的 assistant 消息要和紧随其后的对应 `tool` 消息打包成一个 unit。所有 system 消息和最后一条 user 消息是 protected unit，预算再小也要保留。其他 unit 按“越新越优先”选择，能放进预算才保留，最后按原始顺序返回。任何情况下都不能返回孤儿 tool 消息。

### 工程提醒
真实工程版还要考虑 tokenizer 差异、摘要压缩、工具结果过大和审计要求。本题只考数据结构不变量：先成组，再裁剪，不要先按单条消息贪心删除。''',
        starter='''def trim_messages(messages, max_tokens, token_counter):
    """Trim messages by budget without breaking assistant/tool-call units."""
    raise NotImplementedError
''',
        tests='''def test_protects_system_and_last_user_even_when_budget_is_tiny():
    """system 和最后一条 user 是硬保护，预算不足也要保留。"""
    messages = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "old answer"},
        {"role": "user", "content": "new"},
    ]
    out = trim_messages(messages, 1, lambda m: 10)
    assert [m["role"] for m in out] == ["system", "user"], out
    assert out[-1]["content"] == "new"


def test_does_not_leave_orphan_tool_message():
    """如果 assistant tool_call 放不下，对应 tool 结果也不能单独留下。"""
    messages = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "call", "tool_calls": [{"id": "t1"}]},
        {"role": "tool", "tool_call_id": "t1", "content": "result"},
        {"role": "user", "content": "q2"},
    ]
    out = trim_messages(messages, 2, lambda m: 1)
    assert all(m["role"] != "tool" for m in out), out
    assert out[-1]["content"] == "q2"


def test_keeps_complete_tool_unit_when_it_fits():
    """assistant tool_calls 和对应 tool 结果能放下时，要一起保留。"""
    messages = [
        {"role": "system", "content": "s"},
        {"role": "assistant", "content": "call", "tool_calls": [{"id": "t1"}]},
        {"role": "tool", "tool_call_id": "t1", "content": "result"},
        {"role": "user", "content": "next"},
    ]
    out = trim_messages(messages, 4, lambda m: 1)
    assert [m["role"] for m in out] == ["system", "assistant", "tool", "user"], out


def test_prefers_newer_optional_units():
    """可选消息放不全时，应保留较新的上下文。"""
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "old answer"},
        {"role": "assistant", "content": "new answer"},
        {"role": "user", "content": "latest"},
    ]
    out = trim_messages(messages, 3, lambda m: 1)
    assert [m["content"] for m in out] == ["s", "new answer", "latest"], out
''',
        hidden='''def test_multiple_tool_results_are_grouped_with_parent_call():
    """一个 assistant 发起多个工具时，所有对应 tool 结果属于同一组。"""
    messages = [
        {"role": "assistant", "content": "call", "tool_calls": [{"id": "a"}, {"id": "b"}]},
        {"role": "tool", "tool_call_id": "a", "content": "A"},
        {"role": "tool", "tool_call_id": "b", "content": "B"},
        {"role": "user", "content": "last"},
    ]
    out = trim_messages(messages, 4, lambda m: 1)
    assert [m["role"] for m in out] == ["assistant", "tool", "tool", "user"], out


def test_input_messages_are_not_mutated():
    """裁剪函数只能返回新列表，不能改原消息对象。"""
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    snapshot = [dict(m) for m in messages]
    out = trim_messages(messages, 10, lambda m: 1)
    assert messages == snapshot
    assert out is not messages and out[0] is not messages[0]
''',
        solution='''def trim_messages(messages, max_tokens, token_counter):
    copied = [dict(message) for message in messages]
    units = []
    index = 0
    while index < len(copied):
        message = copied[index]
        unit = [message]
        if message.get("role") == "assistant" and message.get("tool_calls"):
            wanted = {call.get("id") for call in message.get("tool_calls", [])}
            index += 1
            while index < len(copied) and copied[index].get("role") == "tool" and copied[index].get("tool_call_id") in wanted:
                unit.append(copied[index])
                index += 1
            units.append(unit)
            continue
        units.append(unit)
        index += 1

    last_user_unit = None
    for pos, unit in enumerate(units):
        if any(message.get("role") == "user" for message in unit):
            last_user_unit = pos

    protected = set()
    for pos, unit in enumerate(units):
        if any(message.get("role") == "system" for message in unit):
            protected.add(pos)
    if last_user_unit is not None:
        protected.add(last_user_unit)

    costs = [sum(token_counter(message) for message in unit) for unit in units]
    kept = set(protected)
    used = sum(costs[pos] for pos in kept)
    for pos in range(len(units) - 1, -1, -1):
        if pos in kept:
            continue
        if any(message.get("role") == "tool" for message in units[pos]) and not (
            units[pos][0].get("role") == "assistant" and units[pos][0].get("tool_calls")
        ):
            continue
        if used + costs[pos] <= max_tokens:
            kept.add(pos)
            used += costs[pos]

    result = []
    for pos, unit in enumerate(units):
        if pos in kept:
            result.extend(dict(message) for message in unit)
    return result
''',
        hints=["不要先按单条消息删；先把 assistant tool_calls 和 tool 结果打包。", "protected unit 先占预算，哪怕超预算也保留。", "可选 unit 从后往前挑，最后再恢复原始顺序。"],
        points=["上下文裁剪", "消息成组不变量", "预算贪心策略"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p5",
        course="sd",
        title="按租户分桶的令牌桶限流器",
        level="medium",
        desc='''### 背景
令牌桶用于限制请求速率，同时允许短时间突发。多租户服务还要求每个租户有独立额度，不能让一个租户消耗另一个租户的令牌。浏览器 Python 不能 sleep 等真实时间流逝，所以本题用注入的 `clock()` 模拟时间。每次 `allow()` 调用前按当前时间补充令牌，再判断本次请求是否能扣减。

### 要实现什么
实现 `TenantTokenBucket(rate, capacity, clock)`。`rate` 表示每秒补充多少令牌，`capacity` 是桶容量。每个租户第一次访问时从满桶开始，`last_refill` 记为当前时间。`allow(tenant, cost=1)` 返回布尔值：先按 `elapsed * rate` 给该租户补充令牌，最多到容量；令牌足够就扣减并返回 True，不够返回 False。`snapshot(tenant)` 返回 `(tokens, last_refill)`，便于测试。`cost` 必须为正数。

### 工程提醒
真实工程版要给每个桶的读写加锁，分布式限流还要用集中存储或一致哈希。本题只写同步状态机，不使用线程、不等待真实时间。''',
        starter='''class TenantTokenBucket:
    """Per-tenant token bucket using an injected clock."""

    def __init__(self, rate, capacity, clock):
        raise NotImplementedError

    def allow(self, tenant, cost=1):
        """Return True if this tenant can spend cost tokens now."""
        raise NotImplementedError

    def snapshot(self, tenant):
        """Return (tokens, last_refill) for one tenant."""
        raise NotImplementedError
''',
        tests='''def test_allows_burst_until_capacity_then_rejects():
    """初始满桶允许 capacity 次消耗，然后拒绝。"""
    now = [0.0]
    bucket = TenantTokenBucket(rate=1, capacity=2, clock=lambda: now[0])
    assert bucket.allow("t1") is True
    assert bucket.allow("t1") is True
    assert bucket.allow("t1") is False
    assert bucket.snapshot("t1")[0] == 0


def test_refills_by_elapsed_time_capped_at_capacity():
    """补充量由 elapsed * rate 决定，不能超过容量。"""
    now = [0.0]
    bucket = TenantTokenBucket(rate=2, capacity=5, clock=lambda: now[0])
    assert bucket.allow("t1", cost=5)
    now[0] = 1.5
    assert bucket.allow("t1", cost=3) is True
    tokens, _ = bucket.snapshot("t1")
    assert tokens == 0
    now[0] = 10.0
    bucket.allow("t1", cost=1)
    assert bucket.snapshot("t1")[0] == 4


def test_tenants_are_independent():
    """一个租户耗尽令牌，不影响另一个租户。"""
    now = [0.0]
    bucket = TenantTokenBucket(1, 1, lambda: now[0])
    assert bucket.allow("a") is True
    assert bucket.allow("a") is False
    assert bucket.allow("b") is True


def test_fractional_tokens_are_supported():
    """rate 可以产生小数令牌，累计够 cost 后才通过。"""
    now = [0.0]
    bucket = TenantTokenBucket(0.5, 1, lambda: now[0])
    assert bucket.allow("x") is True
    now[0] = 1.0
    assert bucket.allow("x") is False
    now[0] = 2.0
    assert bucket.allow("x") is True
''',
        hidden='''def test_non_positive_cost_is_rejected():
    """cost 必须为正，避免反向加令牌。"""
    bucket = TenantTokenBucket(1, 1, lambda: 0)
    for bad in [0, -1]:
        try:
            bucket.allow("x", bad)
        except ValueError:
            pass
        else:
            raise AssertionError("bad cost should fail")


def test_snapshot_initializes_tenant_without_spending():
    """snapshot 可以懒初始化租户，但不扣令牌。"""
    now = [3.0]
    bucket = TenantTokenBucket(1, 4, lambda: now[0])
    assert bucket.snapshot("new") == (4, 3.0)
    assert bucket.allow("new", 4) is True
''',
        solution='''class TenantTokenBucket:
    def __init__(self, rate, capacity, clock):
        if rate < 0:
            raise ValueError("rate must be non-negative")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.rate = rate
        self.capacity = capacity
        self.clock = clock
        self._buckets = {}

    def _ensure(self, tenant):
        if tenant not in self._buckets:
            self._buckets[tenant] = {"tokens": self.capacity, "last_refill": self.clock()}
        return self._buckets[tenant]

    def _refill(self, tenant):
        bucket = self._ensure(tenant)
        now = self.clock()
        elapsed = max(0, now - bucket["last_refill"])
        bucket["tokens"] = min(self.capacity, bucket["tokens"] + elapsed * self.rate)
        bucket["last_refill"] = now
        return bucket

    def allow(self, tenant, cost=1):
        if cost <= 0:
            raise ValueError("cost must be positive")
        bucket = self._refill(tenant)
        if bucket["tokens"] >= cost:
            bucket["tokens"] -= cost
            return True
        return False

    def snapshot(self, tenant):
        bucket = self._refill(tenant)
        return (bucket["tokens"], bucket["last_refill"])
''',
        hints=["每个 tenant 懒初始化一个桶，初始 tokens=capacity。", "每次 allow 前先 refill，再判断和扣减。", "真实并发版需要锁；本题只做同步数据结构。"],
        points=["令牌桶限流", "按租户隔离", "注入时钟测试"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p6",
        course="sd",
        title="幂等执行器的 singleflight 状态机",
        level="hard",
        desc='''### 背景
幂等执行器要解决两个问题：同一个 key 的重复请求不能重复产生副作用；同一个 key 的并发请求只能让一个 leader 真正执行，其他 follower 等同一个结果。浏览器 Python 不能开线程等待，所以本题把并发改成同步协议：调用方先 `begin(key)` 判断自己是 leader、follower 还是命中缓存；leader 再调用 `complete()` 或 `fail()` 推动状态；follower 用 `waiters_result()` 查看本轮结果。

### 要实现什么
实现 `SingleFlightExecutor`。`begin(key)`：如果 key 已成功完成，返回 `("cached", result)`；如果 key 正在执行，返回 `("follower", token)`；否则创建一次执行并返回 `("leader", token)`。`complete(key, token, result)` 只能由当前 leader token 调用，成功后写入完成缓存，并让等待者能看到 `("ok", result)`。`fail(key, token, error)` 也只能由当前 leader 调用；失败不写 completed 缓存，但等待者要能看到 `("error", error_text)`，下一次 `begin(key)` 应重新选出 leader。`waiters_result(key)` 返回当前可见结果，没有结果时返回 None。

### 工程提醒
真实工程版要用锁保护 `completed` 和 `inflight` 两张表，但锁不能包住真正副作用；进程重启后需要外部幂等表或事务状态，否则内存缓存会丢。本题只实现同步状态机。''',
        starter='''class SingleFlightExecutor:
    """Synchronous singleflight/idempotency state machine."""

    def __init__(self):
        raise NotImplementedError

    def begin(self, key):
        """Return (leader|follower|cached, token_or_result)."""
        raise NotImplementedError

    def complete(self, key, token, result):
        """Complete the in-flight execution for key."""
        raise NotImplementedError

    def fail(self, key, token, error):
        """Fail the in-flight execution for key without caching success."""
        raise NotImplementedError

    def waiters_result(self, key):
        """Return ('ok', result), ('error', text), or None."""
        raise NotImplementedError
''',
        tests='''def test_first_begin_is_leader_and_second_is_follower():
    """同一个 key 运行中时，只能有一个 leader。"""
    sf = SingleFlightExecutor()
    role1, token1 = sf.begin("k")
    role2, token2 = sf.begin("k")
    assert role1 == "leader"
    assert role2 == "follower"
    assert token1 == token2
    assert "k" in sf.inflight and sf.completed == {}


def test_complete_caches_success_for_later_calls():
    """成功结果要写入 completed，后续 begin 直接 cached。"""
    sf = SingleFlightExecutor()
    _, token = sf.begin("k")
    sf.complete("k", token, "ok")
    assert sf.waiters_result("k") == ("ok", "ok")
    assert sf.begin("k") == ("cached", "ok")
    assert "k" not in sf.inflight


def test_failure_not_cached_and_next_call_can_retry():
    """失败只通知本轮等待者，不应写成功缓存。"""
    sf = SingleFlightExecutor()
    _, token1 = sf.begin("k")
    sf.fail("k", token1, "boom")
    assert sf.waiters_result("k") == ("error", "boom")
    role, token2 = sf.begin("k")
    assert role == "leader" and token2 != token1
    assert sf.completed == {}


def test_token_must_match_current_leader():
    """过期或伪造 token 不能完成当前执行。"""
    sf = SingleFlightExecutor()
    _, token = sf.begin("k")
    try:
        sf.complete("k", token + 1, "bad")
    except ValueError:
        pass
    else:
        raise AssertionError("wrong token should fail")
    assert "k" in sf.inflight and "k" not in sf.completed
''',
        hidden='''def test_different_keys_do_not_block_each_other():
    """不同 key 应有独立 inflight 记录。"""
    sf = SingleFlightExecutor()
    r1, t1 = sf.begin("a")
    r2, t2 = sf.begin("b")
    assert r1 == r2 == "leader"
    assert t1 != t2
    sf.complete("a", t1, 1)
    assert sf.begin("b")[0] == "follower"
    assert sf.begin("a") == ("cached", 1)


def test_follower_observes_same_success_result():
    """follower 不执行副作用，只读取 leader 完成后的同一结果。"""
    sf = SingleFlightExecutor()
    _, token = sf.begin("pay")
    assert sf.begin("pay") == ("follower", token)
    assert sf.waiters_result("pay") is None
    sf.complete("pay", token, {"status": "paid"})
    assert sf.waiters_result("pay") == ("ok", {"status": "paid"})
''',
        solution='''class SingleFlightExecutor:
    def __init__(self):
        self.completed = {}
        self.inflight = {}
        self._notifications = {}
        self._next_token = 1

    def begin(self, key):
        if key in self.completed:
            return ("cached", self.completed[key])
        if key in self.inflight:
            return ("follower", self.inflight[key]["token"])
        token = self._next_token
        self._next_token += 1
        self.inflight[key] = {"token": token}
        self._notifications.pop(key, None)
        return ("leader", token)

    def _check_token(self, key, token):
        if key not in self.inflight or self.inflight[key]["token"] != token:
            raise ValueError("token does not match current leader")

    def complete(self, key, token, result):
        self._check_token(key, token)
        self.inflight.pop(key)
        self.completed[key] = result
        self._notifications[key] = ("ok", result)

    def fail(self, key, token, error):
        self._check_token(key, token)
        self.inflight.pop(key)
        self._notifications[key] = ("error", str(error))

    def waiters_result(self, key):
        if key in self._notifications:
            return self._notifications[key]
        if key in self.completed:
            return ("ok", self.completed[key])
        return None
''',
        hints=["begin 只决定角色，不执行真实副作用。", "成功写 completed，失败只通知等待者并允许下次重试。", "用 token 防止旧 leader 或伪造调用覆盖当前状态。"],
        points=["singleflight", "幂等缓存", "leader/follower 状态机"],
        numpy=False,
    ),
]
