LABS = [
    dict(
        id="lab-sd-p7",
        course="sd",
        title="实现乱序事件的按序交付器",
        level="medium",
        desc='''### 背景
消息推送、支付回调、日志流水线里，事件通常带有递增序号。网络重试和断线重连会让事件乱序、重复到达。浏览器里的 Python 运行环境不适合开线程或等待真实网络，所以本题把问题改成同步状态机：每次调用 `push(seq, event)` 表示收到一条事件，函数立即返回本次已经能连续交付的事件列表。
### 要实现什么
实现 `InOrderDeliverer`。构造时可指定 `start_seq`，表示第一条期望交付的序号。`push` 收到未来序号时只能暂存；收到当前期望序号时，要继续把缓冲区里后续连续序号一起吐出；已经交付过的重复序号、已经缓冲过的重复序号都要幂等丢弃。序号必须是正整数，`bool`、字符串、浮点数、非正数都不合法。
### 工程注意
真实工程里还要给 `push` 加锁或放进单线程消费队列，并设置缓冲窗口、缺口超时、重连续传范围。这里重点训练 `next_seq + buffer` 这两个状态。''',
        starter='''class InOrderDeliverer:
    """Deliver events by increasing sequence number."""

    def __init__(self, start_seq=1):
        raise NotImplementedError

    def push(self, seq, event):
        """Return a list of events that become deliverable after this push."""
        raise NotImplementedError
''',
        tests='''def test_delivers_after_gap_is_filled():
    d = InOrderDeliverer(start_seq=1)
    assert d.push(2, "b") == []
    assert d.push(3, "c") == []
    assert d.push(1, "a") == ["a", "b", "c"]
    assert d.next_seq == 4


def test_drops_delivered_and_buffered_duplicates():
    d = InOrderDeliverer()
    assert d.push(2, "b") == []
    assert d.push(2, "b-again") == []
    assert d.push(1, "a") == ["a", "b"]
    assert d.push(1, "a-again") == []
    assert d.push(2, "b-after") == []


def test_drains_multiple_buffered_events_in_one_push():
    d = InOrderDeliverer()
    for seq, event in [(5, "e"), (3, "c"), (4, "d")]:
        assert d.push(seq, event) == []
    assert d.push(1, "a") == ["a"]
    assert d.push(2, "b") == ["b", "c", "d", "e"]


def test_rejects_invalid_sequence_values():
    d = InOrderDeliverer()
    for bad in [0, -1, True, 1.0, "1"]:
        try:
            d.push(bad, "x")
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid seq accepted: {bad!r}")
''',
        hidden='''def test_custom_start_sequence():
    d = InOrderDeliverer(start_seq=10)
    assert d.push(11, "b") == []
    assert d.push(9, "old") == []
    assert d.push(10, "a") == ["a", "b"]
    assert d.next_seq == 12


def test_payload_none_is_still_delivered_once():
    d = InOrderDeliverer()
    assert d.push(1, None) == [None]
    assert d.push(1, "dup") == []


def test_start_seq_must_be_positive_integer():
    for bad in [0, -3, False, 1.2, "7"]:
        try:
            InOrderDeliverer(start_seq=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad start_seq accepted: {bad!r}")
''',
        solution='''class InOrderDeliverer:
    """Deliver events by increasing sequence number."""

    def __init__(self, start_seq=1):
        self._validate_seq(start_seq)
        self.next_seq = start_seq
        self._buffer = {}

    @staticmethod
    def _validate_seq(seq):
        if isinstance(seq, bool) or not isinstance(seq, int) or seq <= 0:
            raise ValueError("seq must be a positive integer")

    def push(self, seq, event):
        self._validate_seq(seq)
        if seq < self.next_seq:
            return []
        if seq in self._buffer:
            return []
        if seq > self.next_seq:
            self._buffer[seq] = event
            return []

        ready = [event]
        self.next_seq += 1
        while self.next_seq in self._buffer:
            ready.append(self._buffer.pop(self.next_seq))
            self.next_seq += 1
        return ready
''',
        hints=["先写清 `seq < next_seq`、`seq == next_seq`、`seq > next_seq` 三个分支。", "补齐缺口后不要只交付一条，要用 while 连续排空缓冲区。", "去重要同时看已交付区间和缓冲区，不能只看其中一个。"],
        points=["乱序缓冲", "幂等去重", "状态机不变量"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p8",
        course="sd",
        title="实现带 TTL 的 LRU 缓存",
        level="medium",
        desc='''### 背景
缓存题常见的坑不是字典读写，而是两个维度同时变化：最近使用顺序和过期时间。真实服务里可能有后台清理线程，但浏览器环境不能依赖线程、定时器或 sleep，所以本题使用可注入的 `clock()`，并采用惰性过期：读、写、查询长度时顺手清理过期项。
### 要实现什么
实现 `LruTtlCache(capacity, ttl=None, clock=None)`。`capacity` 是最大条目数，超过时淘汰最久未使用的未过期条目。`ttl` 是默认存活秒数；`None` 表示不过期。`put(key, value, ttl=...)` 可以覆盖单条记录的 TTL。`get(key, default=None)` 命中时返回值并刷新最近使用顺序；未命中或过期时返回默认值。还要支持 `delete`、`len(cache)` 和 `key in cache`。
### 工程注意
真实工程版本要考虑锁、内存上限、时间回拨、批量清理和指标。这里重点训练 ordered entries 与 expire_at 的同步更新。''',
        starter='''class LruTtlCache:
    """LRU cache with optional per-entry TTL."""

    def __init__(self, capacity, ttl=None, clock=None):
        raise NotImplementedError

    def get(self, key, default=None):
        raise NotImplementedError

    def put(self, key, value, ttl=None):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __contains__(self, key):
        raise NotImplementedError
''',
        tests='''class FakeClock:
    def __init__(self, t=0.0):
        self.t = float(t)
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


def test_lru_eviction_uses_recent_access_order():
    c = LruTtlCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.get("b", "MISS") == "MISS"
    assert c.get("a") == 1 and c.get("c") == 3


def test_ttl_expires_lazily_with_injected_clock():
    clk = FakeClock()
    c = LruTtlCache(3, ttl=10, clock=clk)
    c.put("x", "v")
    clk.advance(9.9)
    assert c.get("x") == "v"
    clk.advance(0.1)
    assert c.get("x", "gone") == "gone"
    assert len(c) == 0


def test_put_refreshes_value_ttl_and_recency():
    clk = FakeClock()
    c = LruTtlCache(2, ttl=5, clock=clk)
    c.put("a", 1)
    clk.advance(4)
    c.put("a", 2)
    c.put("b", 3)
    assert c.get("a") == 2
    c.put("c", 4)
    assert c.get("b", "MISS") == "MISS"
    clk.advance(4.9)
    assert c.get("a") == 2


def test_stored_none_is_different_from_missing():
    c = LruTtlCache(2)
    c.put("present", None)
    assert "present" in c
    assert c.get("present", "MISS") is None
    assert c.get("absent", "MISS") == "MISS"
''',
        hidden='''class FakeClock:
    def __init__(self, t=0.0):
        self.t = float(t)
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


def test_per_key_ttl_override_and_no_expiry():
    clk = FakeClock()
    c = LruTtlCache(3, ttl=5, clock=clk)
    c.put("short", 1, ttl=1)
    c.put("forever", 2, ttl=None)
    clk.advance(2)
    assert c.get("short", "gone") == "gone"
    assert c.get("forever") == 2


def test_expired_entries_do_not_consume_capacity():
    clk = FakeClock()
    c = LruTtlCache(2, ttl=1, clock=clk)
    c.put("a", 1)
    c.put("b", 2)
    clk.advance(2)
    c.put("c", 3)
    assert len(c) == 1
    assert c.get("c") == 3


def test_delete_and_invalid_arguments():
    c = LruTtlCache(1)
    c.put("x", 1)
    assert c.delete("x") is True
    assert c.delete("x") is False
    for make in [lambda: LruTtlCache(0), lambda: LruTtlCache(True), lambda: LruTtlCache(2, ttl=0)]:
        try:
            make()
        except ValueError:
            pass
        else:
            raise AssertionError("bad cache arguments accepted")
''',
        solution='''from collections import OrderedDict
import time


class LruTtlCache:
    """LRU cache with optional per-entry TTL."""

    _USE_DEFAULT = object()

    def __init__(self, capacity, ttl=None, clock=None):
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be positive or None")
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock or time.monotonic
        self._data = OrderedDict()

    def _expire_key(self, key):
        item = self._data.get(key)
        if item is None:
            return False
        _, expire_at = item
        if self.clock() >= expire_at:
            del self._data[key]
            return True
        return False

    def _purge(self):
        for key in list(self._data.keys()):
            self._expire_key(key)

    def get(self, key, default=None):
        if self._expire_key(key) or key not in self._data:
            return default
        value, expire_at = self._data[key]
        self._data.move_to_end(key)
        return value

    def put(self, key, value, ttl=_USE_DEFAULT):
        self._purge()
        effective_ttl = self.ttl if ttl is self._USE_DEFAULT else ttl
        if effective_ttl is not None and effective_ttl <= 0:
            raise ValueError("ttl must be positive or None")
        expire_at = float("inf") if effective_ttl is None else self.clock() + effective_ttl
        self._data[key] = (value, expire_at)
        self._data.move_to_end(key)
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def delete(self, key):
        return self._data.pop(key, self._USE_DEFAULT) is not self._USE_DEFAULT

    def __len__(self):
        self._purge()
        return len(self._data)

    def __contains__(self, key):
        return not self._expire_key(key) and key in self._data
''',
        hints=["用有序字典保存条目，末尾表示最近使用。", "每个条目同时保存 value 和 expire_at，读到过期项要删除后返回未命中。", "写入前先清理过期项，再按容量淘汰最旧的未过期项。"],
        points=["缓存淘汰", "时间依赖注入", "惰性过期"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p9",
        course="sd",
        title="实现可续跑的代码化 workflow",
        level="hard",
        desc='''### 背景
长流程经常由多个节点组成：生成数据、执行任务、汇总报告。失败后如果从头再跑，会重复副作用、浪费时间，还可能覆盖已经正确的产物。浏览器环境不能依赖外部队列或进程重启，所以本题把持久化层简化成传入的 `store` 字典，把每个节点函数当作同步函数。
### 要实现什么
实现 `run_workflow(nodes, store, run_id)`。`nodes` 由 `WfNode(name, fn, deps, retries)` 描述。执行前要校验重名、未知依赖和环。每个节点只接收直接依赖节点的产物副本。节点成功后立刻写入 `store[run_id][node_name]`，同一个 `run_id` 续跑时要跳过已完成节点。节点失败时按 `retries` 重试；耗尽后抛 `WorkflowError`，并保留已经落盘的 checkpoint。
### 工程注意
真实工程里 checkpoint 应写数据库或对象存储，并要记录版本、输入摘要和幂等键。这里重点训练 checkpoint 与 cursor 的关系。''',
        starter='''from dataclasses import dataclass, field


class WorkflowError(Exception):
    pass


@dataclass
class WfNode:
    name: str
    fn: object
    deps: list = field(default_factory=list)
    retries: int = 0


def run_workflow(nodes, store, run_id):
    """Run a checkpointed workflow and return artifacts by node order."""
    raise NotImplementedError
''',
        tests='''def test_checkpoint_and_resume_skip_completed_nodes():
    calls = []
    state = {"fail": True}

    def record(name, fn):
        def wrapped(inputs):
            calls.append(name)
            return fn(inputs)
        return wrapped

    def execute(inputs):
        assert set(inputs) == {"cases", "data"}
        if state["fail"]:
            raise RuntimeError("worker unavailable")
        return {"passed": len(inputs["cases"]), "data": inputs["data"]}

    nodes = [
        WfNode("spec", record("spec", lambda i: {"title": "checkout"})),
        WfNode("cases", record("cases", lambda i: ["c1", "c2"]), deps=["spec"]),
        WfNode("data", record("data", lambda i: "rows=3"), deps=["spec"]),
        WfNode("execute", record("execute", execute), deps=["cases", "data"]),
        WfNode("report", record("report", lambda i: f"passed={i['execute']['passed']}"), deps=["execute"]),
    ]
    store = {}
    try:
        run_workflow(nodes, store, "r1")
    except WorkflowError as exc:
        assert exc.node == "execute"
        assert set(exc.completed) == {"spec", "cases", "data"}
    else:
        raise AssertionError("failure should raise WorkflowError")
    assert set(store["r1"]) == {"spec", "cases", "data"}

    state["fail"] = False
    calls.clear()
    out = run_workflow(nodes, store, "r1")
    assert calls == ["execute", "report"]
    assert out["report"] == "passed=2"


def test_successful_rerun_executes_nothing():
    calls = []
    nodes = [WfNode("a", lambda i: calls.append("a") or 1), WfNode("b", lambda i: calls.append("b") or 2, deps=["a"])]
    store = {}
    assert run_workflow(nodes, store, "r") == {"a": 1, "b": 2}
    calls.clear()
    assert run_workflow(nodes, store, "r") == {"a": 1, "b": 2}
    assert calls == []


def test_node_gets_only_direct_dependency_copies():
    def make_a(inputs):
        return {"items": []}
    def make_b(inputs):
        inputs["a"]["items"].append("dirty")
        return "b"
    def make_c(inputs):
        assert set(inputs) == {"b"}
        return inputs["b"] + "c"
    nodes = [WfNode("a", make_a), WfNode("b", make_b, deps=["a"]), WfNode("c", make_c, deps=["b"])]
    store = {}
    out = run_workflow(nodes, store, "r")
    assert out == {"a": {"items": []}, "b": "b", "c": "bc"}
    assert store["r"]["a"] == {"items": []}


def test_retries_use_fresh_input_copies():
    seen = {"n": 0}
    def flaky(inputs):
        inputs["a"].append("dirty")
        seen["n"] += 1
        if seen["n"] < 3:
            raise RuntimeError("again")
        return len(inputs["a"])
    nodes = [WfNode("a", lambda i: []), WfNode("b", flaky, deps=["a"], retries=2)]
    assert run_workflow(nodes, {}, "r")["b"] == 1
''',
        hidden='''def test_invalid_graphs_fail_before_execution():
    for bad in [
        [WfNode("a", lambda i: 1), WfNode("a", lambda i: 2)],
        [WfNode("a", lambda i: 1, deps=["ghost"])],
        [WfNode("a", lambda i: 1, deps=["b"]), WfNode("b", lambda i: 1, deps=["a"])],
    ]:
        try:
            run_workflow(bad, {}, "x")
        except ValueError:
            pass
        else:
            raise AssertionError("bad workflow graph accepted")


def test_checkpoint_written_immediately_before_later_failure():
    def boom(inputs):
        raise LookupError("missing")
    nodes = [WfNode("a", lambda i: {"ok": True}), WfNode("b", boom, deps=["a"])]
    store = {}
    try:
        run_workflow(nodes, store, "run")
    except WorkflowError as exc:
        assert exc.node == "b"
        assert exc.completed == ["a"]
    else:
        raise AssertionError("expected WorkflowError")
    assert store == {"run": {"a": {"ok": True}}}


def test_result_order_follows_node_definition_order():
    nodes = [WfNode("z", lambda i: "z"), WfNode("a", lambda i: "a", deps=["z"])]
    out = run_workflow(nodes, {}, "r")
    assert list(out) == ["z", "a"]
''',
        solution='''from dataclasses import dataclass, field
import copy


class WorkflowError(Exception):
    def __init__(self, node, cause, completed):
        super().__init__(f"node {node!r} failed: {type(cause).__name__}: {cause}")
        self.node = node
        self.cause = cause
        self.completed = completed


@dataclass
class WfNode:
    name: str
    fn: object
    deps: list = field(default_factory=list)
    retries: int = 0


def _topo_order(nodes):
    by_name = {node.name: node for node in nodes}
    if len(by_name) != len(nodes):
        raise ValueError("duplicate node name")
    for node in nodes:
        for dep in node.deps:
            if dep not in by_name:
                raise ValueError(f"unknown dependency {dep!r}")
    state = {}
    order = []

    def visit(name):
        if state.get(name) == "visiting":
            raise ValueError("cycle detected")
        if state.get(name) == "done":
            return
        state[name] = "visiting"
        for dep in by_name[name].deps:
            visit(dep)
        state[name] = "done"
        order.append(name)

    for node in nodes:
        visit(node.name)
    return order, by_name


def run_workflow(nodes, store, run_id):
    order, by_name = _topo_order(nodes)
    checkpoint = store.setdefault(run_id, {})
    outputs = {name: copy.deepcopy(value) for name, value in checkpoint.items()}
    for name in order:
        if name in checkpoint:
            outputs[name] = copy.deepcopy(checkpoint[name])
            continue
        node = by_name[name]
        last_error = None
        for _ in range(node.retries + 1):
            inputs = {dep: copy.deepcopy(outputs[dep]) for dep in node.deps}
            try:
                artifact = node.fn(inputs)
            except Exception as exc:
                last_error = exc
                continue
            checkpoint[name] = copy.deepcopy(artifact)
            outputs[name] = copy.deepcopy(artifact)
            break
        else:
            raise WorkflowError(name, last_error, sorted(checkpoint.keys()))
    return {node.name: copy.deepcopy(outputs[node.name]) for node in nodes}
''',
        hints=["先校验图，再执行；不要边跑边发现重名或环。", "checkpoint 是成功节点集合，cursor 可以从拓扑顺序中第一个未完成节点推出。", "给节点的输入和写入 store 的产物都要做深拷贝，避免后续节点污染历史结果。"],
        points=["持久化状态机", "失败续跑", "产物隔离"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p10",
        course="sd",
        title="实现同步状态机版 Session 管理器",
        level="hard",
        desc='''### 背景
会话服务既要保证同一用户会话内按轮次串行，又要让不同会话并行处理。真实系统会用队列、协程或线程池，但浏览器 Python 不能依赖这些机制。本题把它改成同步状态机：`submit` 只入队，`start_ready` 显式取出可运行任务，测试再调用 `complete` 或 `fail` 模拟处理完成。
### 要实现什么
实现 `SessionManager(store, max_pending=4, max_active=2, idle_ttl=300, clock=None)`。每个会话有自己的队列，同一会话同时最多一个 running；全局 running 数不能超过 `max_active`。同一会话排队加运行超过 `max_pending` 要抛 `SessionBusy`。任务成功后把 `(turn_input, output)` 追加到历史并写入 `store[sid]`；失败不写历史，但会释放会话让后续轮次继续。空闲超过 `idle_ttl` 且没有在途任务的会话可以回收，再次提交时要从 store 恢复历史。
### 工程注意
真实工程需要线程安全、请求取消、结果通知和持久化事务。这里重点训练 per-session queue 与 active sessions。''',
        starter='''class SessionBusy(Exception):
    pass


class SessionManager:
    """Synchronous state machine for queued session turns."""

    def __init__(self, store, max_pending=4, max_active=2, idle_ttl=300, clock=None):
        raise NotImplementedError

    def submit(self, sid, turn_input):
        raise NotImplementedError

    def start_ready(self):
        raise NotImplementedError

    def complete(self, ticket, output):
        raise NotImplementedError

    def fail(self, ticket, error):
        raise NotImplementedError

    def evict_idle(self):
        raise NotImplementedError

    def active_sessions(self):
        raise NotImplementedError
''',
        tests='''class FakeClock:
    def __init__(self, t=0.0):
        self.t = float(t)
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


def test_same_session_serial_different_sessions_can_start_together():
    mgr = SessionManager({}, max_active=2)
    a1 = mgr.submit("A", "A1")
    a2 = mgr.submit("A", "A2")
    b1 = mgr.submit("B", "B1")
    started = mgr.start_ready()
    assert [(j["sid"], j["turn_input"]) for j in started] == [("A", "A1"), ("B", "B1")]
    assert {j["ticket"] for j in started} == {a1, b1}
    assert mgr.start_ready() == []


def test_complete_persists_history_and_unblocks_next_turn():
    store = {}
    mgr = SessionManager(store, max_active=1)
    t1 = mgr.submit("S", "one")
    t2 = mgr.submit("S", "two")
    job = mgr.start_ready()[0]
    assert job["history"] == []
    mgr.complete(t1, "out1")
    job = mgr.start_ready()[0]
    assert job["ticket"] == t2
    assert job["history"] == [("one", "out1")]
    mgr.complete(t2, "out2")
    assert store["S"] == [("one", "out1"), ("two", "out2")]


def test_failure_does_not_persist_but_releases_session():
    store = {}
    mgr = SessionManager(store)
    bad = mgr.submit("S", "bad")
    good = mgr.submit("S", "good")
    mgr.start_ready()
    mgr.fail(bad, "model error")
    job = mgr.start_ready()[0]
    assert job["ticket"] == good and job["history"] == []
    mgr.complete(good, "ok")
    assert store["S"] == [("good", "ok")]


def test_backpressure_counts_queued_and_running():
    mgr = SessionManager({}, max_pending=2)
    mgr.submit("S", 1)
    mgr.submit("S", 2)
    try:
        mgr.submit("S", 3)
    except SessionBusy:
        pass
    else:
        raise AssertionError("expected SessionBusy")
''',
        hidden='''class FakeClock:
    def __init__(self, t=0.0):
        self.t = float(t)
    def __call__(self):
        return self.t
    def advance(self, dt):
        self.t += dt


def test_idle_evict_skips_busy_sessions_and_restores_from_store():
    clk = FakeClock()
    store = {"A": [("old", "out")], "B": []}
    mgr = SessionManager(store, idle_ttl=10, clock=clk)
    t_next = mgr.submit("A", "next")
    mgr.submit("B", "busy")
    first = mgr.start_ready()
    busy = next(job for job in first if job["sid"] == "B")
    mgr.complete(t_next, "done")
    clk.advance(11)
    assert mgr.evict_idle() == ["A"]
    mgr.complete(busy["ticket"], "done")
    clk.advance(11)
    assert mgr.evict_idle() == ["B"]
    ticket = mgr.submit("A", "again")
    job = mgr.start_ready()[0]
    assert ticket == job["ticket"]
    assert job["history"] == [("old", "out"), ("next", "done")]


def test_global_active_limit_starts_more_after_completion():
    mgr = SessionManager({}, max_active=1)
    a = mgr.submit("A", "a")
    b = mgr.submit("B", "b")
    assert [j["ticket"] for j in mgr.start_ready()] == [a]
    assert mgr.start_ready() == []
    mgr.complete(a, "ao")
    assert [j["ticket"] for j in mgr.start_ready()] == [b]


def test_history_snapshot_given_to_job_is_isolated():
    store = {}
    mgr = SessionManager(store)
    t1 = mgr.submit("S", "one")
    job = mgr.start_ready()[0]
    job["history"].append(("dirty", "value"))
    mgr.complete(t1, "out")
    t2 = mgr.submit("S", "two")
    job2 = mgr.start_ready()[0]
    assert job2["history"] == [("one", "out")]
''',
        solution='''from collections import deque
import copy
import time


class SessionBusy(Exception):
    pass


class SessionManager:
    """Synchronous state machine for queued session turns."""

    def __init__(self, store, max_pending=4, max_active=2, idle_ttl=300, clock=None):
        self.store = store
        self.max_pending = max_pending
        self.max_active = max_active
        self.idle_ttl = idle_ttl
        self.clock = clock or time.monotonic
        self._sessions = {}
        self._jobs = {}
        self._next_id = 1

    def _ensure_session(self, sid):
        if sid not in self._sessions:
            self._sessions[sid] = {
                "history": copy.deepcopy(self.store.get(sid, [])),
                "queue": deque(),
                "active": None,
                "last": self.clock(),
            }
        return self._sessions[sid]

    def submit(self, sid, turn_input):
        session = self._ensure_session(sid)
        pending = len(session["queue"]) + (1 if session["active"] is not None else 0)
        if pending >= self.max_pending:
            raise SessionBusy(f"session {sid!r} has too many pending turns")
        ticket = f"job-{self._next_id}"
        self._next_id += 1
        job = {"ticket": ticket, "sid": sid, "turn_input": turn_input, "status": "queued"}
        self._jobs[ticket] = job
        session["queue"].append(ticket)
        session["last"] = self.clock()
        return ticket

    def start_ready(self):
        started = []
        active_count = sum(1 for s in self._sessions.values() if s["active"] is not None)
        made_progress = True
        while active_count < self.max_active and made_progress:
            made_progress = False
            for sid, session in self._sessions.items():
                if active_count >= self.max_active:
                    break
                if session["active"] is None and session["queue"]:
                    ticket = session["queue"].popleft()
                    session["active"] = ticket
                    session["last"] = self.clock()
                    job = self._jobs[ticket]
                    job["status"] = "running"
                    active_count += 1
                    made_progress = True
                    started.append({
                        "ticket": ticket,
                        "sid": sid,
                        "turn_input": job["turn_input"],
                        "history": copy.deepcopy(session["history"]),
                    })
        return started

    def _finish(self, ticket):
        job = self._jobs[ticket]
        session = self._sessions[job["sid"]]
        if session["active"] != ticket or job["status"] != "running":
            raise ValueError("ticket is not running")
        session["active"] = None
        session["last"] = self.clock()
        return job, session

    def complete(self, ticket, output):
        job, session = self._finish(ticket)
        job["status"] = "done"
        job["output"] = output
        session["history"].append((job["turn_input"], output))
        self.store[job["sid"]] = copy.deepcopy(session["history"])

    def fail(self, ticket, error):
        job, _ = self._finish(ticket)
        job["status"] = "failed"
        job["error"] = str(error)

    def evict_idle(self):
        now = self.clock()
        evicted = []
        for sid, session in list(self._sessions.items()):
            if session["active"] is None and not session["queue"] and now - session["last"] >= self.idle_ttl:
                evicted.append(sid)
                del self._sessions[sid]
        return sorted(evicted)

    def active_sessions(self):
        return sorted(self._sessions)
''',
        hints=["每个会话保存 queue、active、history、last 四类信息。", "`start_ready` 只负责把 queued 变成 running，不要在里面执行真实业务。", "成功才追加历史；失败只释放 active，否则后续轮次会被永久卡住。"],
        points=["会话串行化", "背压", "持久化恢复"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p11",
        course="sd",
        title="实现工具注册与调用层",
        level="hard",
        desc='''### 背景
工具调用层要同时服务模型和工程系统：名字要稳定，参数错误要可修正，返回结果不能无限长，读写操作还要遵守调度规则。真实服务里的读工具可以并行、写工具需要串行和隔离；浏览器 Python 不适合开线程，所以本题把并行要求拆成同步的批次规划：连续只读调用进入同一个批次，写调用和未知工具作为单独屏障。
### 要实现什么
实现 `ToolRegistry` 和 `ToolSpec`。注册时校验工具名是 2 到 4 段小写下划线，拒绝重名和过短描述。`call(name, args)` 永远返回 `{"ok": bool, "content": str}`，不要把工具异常抛给调用方。参数校验要能指出未知参数、缺失必填、类型不符，并给出 example。超长结果要截断，并提示 truncated 和 paginate。`plan_batch(calls)` 返回调用下标的批次，`call_batch(calls)` 按批次执行并保持结果顺序。
### 工程注意
真实工程里批次内读操作可以交给线程池或异步运行，写操作要配锁或事务。这里重点训练 registry 与 write barrier。''',
        starter='''from dataclasses import dataclass


@dataclass
class ToolSpec:
    name: str
    description: str
    params: dict
    fn: object
    read_only: bool = True
    max_chars: int = 2000


class ToolRegistry:
    """Register tools, validate calls, and plan read/write batches."""

    def __init__(self):
        raise NotImplementedError

    def register(self, spec):
        raise NotImplementedError

    def call(self, name, args):
        raise NotImplementedError

    def plan_batch(self, calls):
        raise NotImplementedError

    def call_batch(self, calls):
        raise NotImplementedError
''',
        tests='''def test_register_rejects_bad_names_duplicates_and_short_descriptions():
    reg = ToolRegistry()
    reg.register(ToolSpec("order_search", "Search orders by keyword", {"keyword": (str, True)}, lambda keyword: keyword))
    for bad in [
        ToolSpec("Search", "Search orders", {}, lambda: None),
        ToolSpec("order_search", "Search again", {}, lambda: None),
        ToolSpec("order_list", "short", {}, lambda: None),
    ]:
        try:
            reg.register(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("bad tool registration accepted")


def test_call_validates_arguments_and_suggests_unknown_tool():
    reg = ToolRegistry()
    reg.register(ToolSpec("order_search", "Search orders by keyword", {"keyword": (str, True), "limit": (int, False)}, lambda keyword, limit=5: "ok"))
    assert "order_search" in reg.call("order_serch", {"keyword": "x"})["content"]
    missing = reg.call("order_search", {})
    assert not missing["ok"] and "keyword" in missing["content"] and "example" in missing["content"]
    wrong = reg.call("order_search", {"keyword": "x", "limit": True})
    assert not wrong["ok"] and "limit" in wrong["content"] and "int" in wrong["content"]
    unknown = reg.call("order_search", {"keyword": "x", "page": 1})
    assert not unknown["ok"] and "page" in unknown["content"] and "allowed" in unknown["content"]


def test_tool_exception_and_truncation_are_reported_as_content():
    reg = ToolRegistry()
    reg.register(ToolSpec("order_delete", "Delete one order by id", {"order_id": (str, True)}, lambda order_id: (_ for _ in ()).throw(PermissionError("denied")), read_only=False))
    reg.register(ToolSpec("order_dump", "Dump many order ids", {}, lambda: "x" * 80, max_chars=20))
    err = reg.call("order_delete", {"order_id": "o1"})
    assert not err["ok"] and "PermissionError" in err["content"] and "Traceback" not in err["content"]
    long = reg.call("order_dump", {})
    assert long["ok"] and len(long["content"]) < 80 and "truncated" in long["content"] and "paginate" in long["content"]


def test_plan_batch_groups_reads_and_keeps_writes_as_barriers():
    reg = ToolRegistry()
    reg.register(ToolSpec("order_search", "Search orders by keyword", {}, lambda: "r"))
    reg.register(ToolSpec("order_get", "Get one order by id", {}, lambda: "g"))
    reg.register(ToolSpec("order_create", "Create one order", {}, lambda: "w", read_only=False))
    calls = [("order_search", {}), ("order_get", {}), ("order_create", {}), ("order_search", {}), ("missing_tool", {})]
    assert reg.plan_batch(calls) == [[0, 1], [2], [3], [4]]
''',
        hidden='''def test_call_batch_preserves_order_and_write_visibility():
    reg = ToolRegistry()
    db = {"rows": 0}
    seen = []
    def read():
        seen.append(("read", db["rows"]))
        return db["rows"]
    def write():
        db["rows"] += 1
        seen.append(("write", db["rows"]))
        return "created"
    reg.register(ToolSpec("item_read", "Read current item count", {}, read))
    reg.register(ToolSpec("item_write", "Create one item", {}, write, read_only=False))
    res = reg.call_batch([("item_read", {}), ("item_read", {}), ("item_write", {}), ("item_read", {})])
    assert [r["content"] for r in res] == ["0", "0", "created", "1"]
    assert seen == [("read", 0), ("read", 0), ("write", 1), ("read", 1)]


def test_optional_parameters_may_be_omitted_and_bool_is_not_int():
    reg = ToolRegistry()
    reg.register(ToolSpec("math_add", "Add two small numbers", {"a": (int, True), "b": (int, False)}, lambda a, b=1: a + b))
    assert reg.call("math_add", {"a": 2}) == {"ok": True, "content": "3"}
    bad = reg.call("math_add", {"a": True})
    assert not bad["ok"] and "bool" in bad["content"]


def test_call_never_raises_when_args_is_not_dict():
    reg = ToolRegistry()
    reg.register(ToolSpec("echo_text", "Echo text back to caller", {"text": (str, True)}, lambda text: text))
    result = reg.call("echo_text", None)
    assert not result["ok"] and "arguments" in result["content"]
''',
        solution='''from dataclasses import dataclass
import difflib
import re


@dataclass
class ToolSpec:
    name: str
    description: str
    params: dict
    fn: object
    read_only: bool = True
    max_chars: int = 2000


class ToolRegistry:
    """Register tools, validate calls, and plan read/write batches."""

    NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z][a-z0-9]*){1,3}$")

    def __init__(self):
        self._tools = {}

    def register(self, spec):
        if not self.NAME_RE.fullmatch(spec.name):
            raise ValueError("tool name must be 2 to 4 lowercase segments")
        if spec.name in self._tools:
            raise ValueError("duplicate tool")
        if len(spec.description.strip()) < 10:
            raise ValueError("description is too short")
        self._tools[spec.name] = spec

    def _validate(self, spec, args):
        if not isinstance(args, dict):
            return "arguments must be an object"
        unknown = sorted(set(args) - set(spec.params))
        if unknown:
            return f"unknown parameter(s) {unknown}; allowed: {sorted(spec.params)}"
        required = []
        for name, (typ, is_required) in spec.params.items():
            if is_required:
                required.append(f"{name}=<{typ.__name__}>")
            if name not in args:
                if is_required:
                    example = f"example: {spec.name}(" + ", ".join(required) + ")"
                    return f"missing required parameter {name!r} ({typ.__name__}); {example}"
                continue
            value = args[name]
            if (typ is int and isinstance(value, bool)) or not isinstance(value, typ):
                return f"parameter {name!r} expects {typ.__name__}, got {type(value).__name__}"
        return None

    def call(self, name, args):
        spec = self._tools.get(name)
        if spec is None:
            close = difflib.get_close_matches(name, list(self._tools), n=1)
            hint = f"; did you mean {close[0]}" if close else f"; available: {sorted(self._tools)}"
            return {"ok": False, "content": f"unknown tool {name!r}{hint}"}
        error = self._validate(spec, args)
        if error:
            return {"ok": False, "content": error}
        try:
            text = str(spec.fn(**args))
        except Exception as exc:
            return {"ok": False, "content": f"{type(exc).__name__}: {exc}"}
        if len(text) > spec.max_chars:
            hidden = len(text) - spec.max_chars
            text = text[:spec.max_chars] + f"\\n[truncated: {hidden} chars; narrow the query or paginate]"
        return {"ok": True, "content": text}

    def plan_batch(self, calls):
        batches = []
        i = 0
        while i < len(calls):
            name, _ = calls[i]
            spec = self._tools.get(name)
            if spec is not None and spec.read_only:
                group = []
                while i < len(calls):
                    next_spec = self._tools.get(calls[i][0])
                    if next_spec is None or not next_spec.read_only:
                        break
                    group.append(i)
                    i += 1
                batches.append(group)
            else:
                batches.append([i])
                i += 1
        return batches

    def call_batch(self, calls):
        results = [None] * len(calls)
        for batch in self.plan_batch(calls):
            for index in batch:
                name, args = calls[index]
                results[index] = self.call(name, args)
        return results
''',
        hints=["注册表只保存元数据和函数，不要在注册时执行工具。", "`call` 的所有失败都返回结构化内容，不能让异常穿透。", "批次规划先连续吃掉只读调用，遇到写调用或未知工具就单独成批。"],
        points=["工具 schema", "可操作报错", "读写调度"],
        numpy=False,
    ),
    dict(
        id="lab-sd-p12",
        course="sd",
        title="实现同步嵌套子 agent 运行时",
        level="hard",
        desc='''### 背景
多 agent 系统常把大任务拆成树形调用。难点不是能不能调用函数，而是父子关系、深度上限、预算逐级扣减、摘要回传、失败隔离和取消清理。浏览器环境不能启动真实子进程、线程或事件循环，所以本题把子 agent 改成同步函数 `fn(ctx, runtime)`，由 `spawn` 显式执行。
### 要实现什么
实现 `Budget`、`AgentCtx`、`ChildResult` 和 `AgentRuntime`。`Budget.remaining()` 取自己剩余额度和祖先剩余额度的最小值；`spend(n)` 超额抛 `BudgetExceeded`，成功时从当前预算一路扣到根。`spawn(parent, name, fn, budget)` 建立路径和深度，超过 `max_depth` 返回失败结果而不是抛异常；普通异常要变成失败结果；成功只回传截断摘要和本子树花费。`spawn_many` 按输入顺序返回多个结果，单个失败不能中断兄弟。`cancel_subtree(path)` 用同步方式清理 call tree 中的运行标记，用来模拟真实工程里的级联取消。
### 工程注意
真实版本要取消真实任务并等待退出，避免孤儿进程或后台协程。这里重点训练 call tree 与 budget ledger。''',
        starter='''from dataclasses import dataclass


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, limit, parent=None):
        raise NotImplementedError

    def remaining(self):
        raise NotImplementedError

    def spend(self, n):
        raise NotImplementedError


@dataclass
class AgentCtx:
    path: str
    depth: int
    budget: Budget


@dataclass
class ChildResult:
    path: str
    ok: bool
    summary: str = ""
    error: str = None
    tokens: int = 0


class AgentRuntime:
    def __init__(self, max_depth=2, summary_chars=200):
        raise NotImplementedError

    def spawn(self, parent, name, fn, budget):
        raise NotImplementedError

    def spawn_many(self, parent, specs):
        raise NotImplementedError

    def cancel_subtree(self, path):
        raise NotImplementedError
''',
        tests='''def test_nested_paths_depth_summary_and_budget_rollup():
    rt = AgentRuntime(max_depth=2, summary_chars=5)
    seen = {}

    def leaf(ctx, runtime):
        ctx.budget.spend(30)
        seen[ctx.path] = ctx.depth
        return "abcdef"

    def mid(ctx, runtime):
        ctx.budget.spend(10)
        kids = runtime.spawn_many(ctx, [("leaf1", leaf, 100), ("leaf2", leaf, 100)])
        seen["kids"] = [(k.path, k.ok, k.summary, k.tokens) for k in kids]
        return "middle"

    def root(ctx, runtime):
        result = runtime.spawn(ctx, "mid", mid, 1000)
        seen["mid"] = (result.ok, result.summary, result.tokens)
        return "root-ok"

    result = rt.spawn(None, "root", root, 1000)
    assert result.ok and result.summary == "root-"
    assert seen["kids"] == [("root/mid/leaf1", True, "abcde", 30), ("root/mid/leaf2", True, "abcde", 30)]
    assert seen["root/mid/leaf1"] == 2
    assert seen["mid"] == (True, "middl", 70)
    assert result.tokens == 70
    assert rt.running == set()


def test_depth_limit_returns_failure_result():
    rt = AgentRuntime(max_depth=1)
    parent = AgentCtx("root/child", 1, Budget(100))
    result = rt.spawn(parent, "too_deep", lambda c, r: "never", 10)
    assert not result.ok and "depth" in result.error
    assert result.path == "root/child/too_deep"


def test_budget_cannot_exceed_ancestor_remaining():
    root_budget = Budget(100)
    parent = AgentCtx("root", 0, root_budget)
    rt = AgentRuntime()
    def spend60(ctx, runtime):
        ctx.budget.spend(60)
        return "ok"
    results = rt.spawn_many(parent, [("a", spend60, 80), ("b", spend60, 80)])
    assert [r.ok for r in results] == [True, False]
    assert "BudgetExceeded" in results[1].error
    assert root_budget.used == 60 and root_budget.remaining() == 40


def test_failure_is_isolated_from_siblings():
    rt = AgentRuntime()
    def ok(ctx, runtime):
        return "ok"
    def crash(ctx, runtime):
        raise KeyError("missing")
    results = rt.spawn_many(None, [("ok", ok, 10), ("bad", crash, 10), ("ok2", ok, 10)])
    assert [r.ok for r in results] == [True, False, True]
    assert "KeyError" in results[1].error
''',
        hidden='''def test_direct_budget_remaining_and_spend_validation():
    parent = Budget(5)
    child = Budget(10, parent)
    assert child.remaining() == 5
    try:
        child.spend(6)
    except BudgetExceeded:
        pass
    else:
        raise AssertionError("child spent more than parent remaining")
    child.spend(3)
    assert child.used == 3 and parent.used == 3
    try:
        child.spend(-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative spend accepted")


def test_cancel_subtree_marks_descendants_and_clears_running():
    rt = AgentRuntime()
    def child(ctx, runtime):
        runtime.running.add(ctx.path + "/manual")
        runtime.call_tree[ctx.path + "/manual"] = {"parent": ctx.path, "depth": ctx.depth + 1, "status": "running"}
        cancelled = runtime.cancel_subtree(ctx.path)
        return ",".join(cancelled)
    result = rt.spawn(None, "root", child, 10)
    assert result.ok
    assert "root" in result.summary and "root/manual" in result.summary
    assert rt.running == set()
    assert rt.call_tree["root"]["status"] == "cancelled"
    assert rt.call_tree["root/manual"]["status"] == "cancelled"


def test_invalid_budget_limit_is_rejected():
    for bad in [0, -1, True, 1.5]:
        try:
            Budget(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("bad budget limit accepted")
''',
        solution='''from dataclasses import dataclass


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, limit, parent=None):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("budget limit must be a positive integer")
        self.limit = limit
        self.parent = parent
        self.used = 0

    def remaining(self):
        own = self.limit - self.used
        return own if self.parent is None else min(own, self.parent.remaining())

    def spend(self, n):
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("spend amount must be a non-negative integer")
        if n > self.remaining():
            raise BudgetExceeded(f"need {n}, remaining {self.remaining()}")
        current = self
        while current is not None:
            current.used += n
            current = current.parent


@dataclass
class AgentCtx:
    path: str
    depth: int
    budget: Budget


@dataclass
class ChildResult:
    path: str
    ok: bool
    summary: str = ""
    error: str = None
    tokens: int = 0


class AgentRuntime:
    def __init__(self, max_depth=2, summary_chars=200):
        self.max_depth = max_depth
        self.summary_chars = summary_chars
        self.running = set()
        self.call_tree = {}

    def spawn(self, parent, name, fn, budget):
        depth = 0 if parent is None else parent.depth + 1
        path = name if parent is None else f"{parent.path}/{name}"
        parent_path = None if parent is None else parent.path
        if depth > self.max_depth:
            self.call_tree[path] = {"parent": parent_path, "depth": depth, "status": "failed"}
            return ChildResult(path, False, error=f"depth limit {self.max_depth} exceeded")
        ctx = AgentCtx(path, depth, Budget(budget, None if parent is None else parent.budget))
        self.call_tree[path] = {"parent": parent_path, "depth": depth, "status": "running"}
        self.running.add(path)
        try:
            value = fn(ctx, self)
            if self.call_tree.get(path, {}).get("status") != "cancelled":
                self.call_tree[path]["status"] = "succeeded"
            return ChildResult(path, True, summary=str(value)[:self.summary_chars], tokens=ctx.budget.used)
        except Exception as exc:
            self.call_tree[path]["status"] = "failed"
            return ChildResult(path, False, error=f"{type(exc).__name__}: {exc}", tokens=ctx.budget.used)
        finally:
            self.running.discard(path)

    def spawn_many(self, parent, specs):
        return [self.spawn(parent, name, fn, budget) for name, fn, budget in specs]

    def cancel_subtree(self, path):
        cancelled = []
        prefix = path + "/"
        for node_path in sorted(list(self.call_tree)):
            if node_path == path or node_path.startswith(prefix):
                self.call_tree[node_path]["status"] = "cancelled"
                self.running.discard(node_path)
                cancelled.append(node_path)
        return cancelled
''',
        hints=["path 和 depth 都从 parent 推导，根节点 depth 为 0。", "预算花费要沿父链逐级增加，不能只扣子预算。", "`spawn` 捕获普通异常并返回失败结果，但 finally 必须清理 running。"],
        points=["树形调用", "预算账本", "失败隔离与取消清理"],
        numpy=False,
    ),
]
