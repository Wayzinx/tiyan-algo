# 判题 harness：本地 gen.py 和浏览器里的 Pyodide 共用同一份
import json, copy, sys, io, time, traceback, linecache
from typing import *
from collections import *
import heapq, bisect, math, itertools, functools, string, operator, random
from functools import cache, lru_cache


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

    def __repr__(self):
        return "ListNode(%r)" % (_from_list(self),)


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self):
        return "TreeNode(%r)" % (_from_tree(self),)


def _to_list(arr):
    dummy = cur = ListNode()
    for v in arr:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next


def _from_list(node):
    out, steps = [], 0
    while node is not None:
        out.append(node.val)
        node = node.next
        steps += 1
        if steps > 200000:
            raise RuntimeError("链表里可能有环：遍历超过 200000 个节点")
    return out


def _to_tree(arr):
    if not arr or arr[0] is None:
        return None
    root = TreeNode(arr[0])
    q, i = deque([root]), 1
    while q and i < len(arr):
        node = q.popleft()
        if arr[i] is not None:
            node.left = TreeNode(arr[i])
            q.append(node.left)
        i += 1
        if i < len(arr) and arr[i] is not None:
            node.right = TreeNode(arr[i])
            q.append(node.right)
        i += 1
    return root


def _from_tree(root):
    if root is None:
        return []
    out, q = [], deque([root])
    while q:
        n = q.popleft()
        if n is None:
            out.append(None)
            continue
        out.append(n.val)
        q.append(n.left)
        q.append(n.right)
    while out and out[-1] is None:
        out.pop()
    return out


CONVERT_IN = {
    "ListNode": _to_list,
    "TreeNode": _to_tree,
    "ListNode[]": lambda a: [_to_list(x) for x in a],
}
CONVERT_OUT = {
    "ListNode": _from_list,
    "TreeNode": _from_tree,
}


def _jsonable(x):
    if isinstance(x, (list, tuple, set, frozenset, deque)):
        items = [_jsonable(v) for v in x]
        if isinstance(x, (set, frozenset)):
            items.sort(key=_key)
        return items
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, ListNode):
        return _from_list(x)
    if isinstance(x, TreeNode):
        return _from_tree(x)
    return x


def _key(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _norm(x, mode):
    x = _jsonable(x)
    if mode == "unordered" and isinstance(x, list):
        return sorted(x, key=_key)
    if mode == "unordered_deep" and isinstance(x, list):
        return sorted((sorted(i, key=_key) if isinstance(i, list) else i for i in x), key=_key)
    return x


def _same(got, exp, mode):
    if mode == "float":
        try:
            return abs(float(got) - float(exp)) <= 1e-5 * max(1.0, abs(float(exp)))
        except Exception:
            return False
    return _norm(got, mode) == _norm(exp, mode)


def _get_callable(ns, fn):
    if "Solution" in ns and isinstance(ns["Solution"], type):
        obj = ns["Solution"]()
        if hasattr(obj, fn):
            return getattr(obj, fn)
    if fn in ns and callable(ns[fn]):
        return ns[fn]
    raise NameError("没找到函数 %s：请保留 class Solution 里的 %s 方法" % (fn, fn))


def _call(f, args, types, ret_type):
    types = types or [None] * len(args)
    conv = [CONVERT_IN[t](copy.deepcopy(a)) if t in CONVERT_IN else copy.deepcopy(a) for a, t in zip(args, types)]
    out = f(*conv)
    if ret_type and ret_type.startswith("inplace"):
        out = conv[int(ret_type[7:] or 0)]
    elif ret_type in CONVERT_OUT:
        out = CONVERT_OUT[ret_type](out)
    return _jsonable(out)


def _short(v, limit=300):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + " …（共 %d 字符）" % len(s)


def run_tests(user_code, spec_json, max_cases=None):
    """跑用户代码。spec: {fn, types, ret_type, compare, tests:[{args, expected}]}。返回 JSON 字符串。"""
    spec = json.loads(spec_json)
    result = {"ok": False, "compile_error": None, "cases": [], "passed": 0, "total": 0, "stdout": ""}
    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        ns = {"__name__": "__solution__"}
        ns.update({k: v for k, v in globals().items() if not k.startswith("_") or k in ("__builtins__",)})
        ns["ListNode"], ns["TreeNode"] = ListNode, TreeNode
        try:
            exec(_src(user_code, "solution.py"), ns)
            f = _get_callable(ns, spec["fn"])
        except Exception as e:
            result["compile_error"] = _fmt_exc(e)
            return json.dumps(result, ensure_ascii=False)
        tests = spec["tests"][: max_cases or len(spec["tests"])]
        result["total"] = len(tests)
        for i, t in enumerate(tests):
            case = {"i": i, "args": _short(t["args"]), "expected": _short(t.get("expected"))}
            start = time.perf_counter()
            try:
                f = _get_callable(ns, spec["fn"])
                got = _call(f, t["args"], spec.get("types"), spec.get("ret_type"))
                case["got"] = _short(got)
                case["pass"] = "expected" in t and _same(got, t["expected"], spec.get("compare", "exact"))
            except RecursionError as e:
                case["error"] = "RecursionError: 递归太深（可能没写终止条件，或需要改成迭代）"
                case["pass"] = False
            except Exception as e:
                case["error"] = _fmt_exc(e)
                case["pass"] = False
            case["ms"] = round((time.perf_counter() - start) * 1000, 1)
            result["cases"].append(case)
            if case["pass"]:
                result["passed"] += 1
        result["ok"] = result["passed"] == result["total"]
    finally:
        sys.stdout = old_out
        out = buf.getvalue()
        result["stdout"] = out if len(out) < 4000 else out[:4000] + "\n…（输出过长已截断）"
    return json.dumps(result, ensure_ascii=False)


def run_reference(code, spec_json):
    """用参考解算出每个用例的 expected（AI 出的变体题用它校正答案）。"""
    spec = json.loads(spec_json)
    ns = {"__name__": "__reference__"}
    ns.update({k: v for k, v in globals().items() if not k.startswith("_")})
    exec(_src(code, "reference.py"), ns)
    f = _get_callable(ns, spec["fn"])
    outs = []
    for t in spec["tests"]:
        try:
            outs.append({"expected": _call(f, t["args"], spec.get("types"), spec.get("ret_type"))})
        except Exception as e:
            outs.append({"error": _fmt_exc(e)})
    return json.dumps(outs, ensure_ascii=False)


def run_snippet(code, stdin_text=""):
    """自由运行一段代码（AI 工具 / 草稿区用）。"""
    buf = io.StringIO()
    old_out, old_in = sys.stdout, sys.stdin
    sys.stdout, sys.stdin = buf, io.StringIO(stdin_text)
    err = None
    try:
        ns = {"__name__": "__main__"}
        ns.update({k: v for k, v in globals().items() if not k.startswith("_")})
        exec(_src(code, "snippet.py"), ns)
    except Exception as e:
        err = _fmt_exc(e)
    finally:
        sys.stdout, sys.stdin = old_out, old_in
    out = buf.getvalue()
    return json.dumps({"stdout": out[:6000], "error": err}, ensure_ascii=False)


def run_lab(user_code, tests_code):
    """手写实战：执行学习者代码，再逐个运行 tests 里的 test_ 函数。返回 JSON 字符串。"""
    result = {"compile_error": None, "cases": [], "passed": 0, "total": 0, "stdout": ""}
    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        ns = {"__name__": "__lab__"}
        try:
            exec(_src(user_code, "solution.py"), ns)
        except Exception as e:
            result["compile_error"] = _fmt_exc(e)
            return json.dumps(result, ensure_ascii=False)
        tns = dict(ns)
        try:
            exec(_src(tests_code, "tests.py"), tns)
        except Exception as e:
            result["compile_error"] = "测试代码加载失败（可能是你的代码缺少某个函数或类）：" + _fmt_exc(e)
            return json.dumps(result, ensure_ascii=False)
        tests = [(k, v) for k, v in tns.items() if k.startswith("test_") and callable(v)]
        result["total"] = len(tests)
        for name, fn in tests:
            case = {"name": name, "doc": (fn.__doc__ or "").strip()}
            start = time.perf_counter()
            try:
                fn()
                case["pass"] = True
                result["passed"] += 1
            except AssertionError as e:
                case["pass"] = False
                case["error"] = "断言失败" + (("：" + str(e)) if str(e) else "") + _where(e)
            except Exception as e:
                case["pass"] = False
                case["error"] = _fmt_exc(e)
            case["ms"] = round((time.perf_counter() - start) * 1000, 1)
            result["cases"].append(case)
    finally:
        sys.stdout = old_out
        out = buf.getvalue()
        result["stdout"] = out if len(out) < 4000 else out[:4000] + "\n…（输出过长已截断）"
    return json.dumps(result, ensure_ascii=False)


def _suite(impl_code, tests_code):
    ns = {"__name__": "__impl__"}
    exec(_src(impl_code, "impl.py"), ns)
    tns = dict(ns)
    exec(_src(tests_code, "tests.py"), tns)
    tests = [(k, v) for k, v in tns.items() if k.startswith("test_") and callable(v)]
    cases = []
    for name, fn in tests:
        case = {"name": name, "doc": (fn.__doc__ or "").strip()}
        try:
            fn()
            case["pass"] = True
        except AssertionError as e:
            case["pass"] = False
            case["error"] = "断言失败" + (("：" + str(e)) if str(e) else "") + _where(e)
        except Exception as e:
            case["pass"] = False
            case["error"] = _fmt_exc(e)
        cases.append(case)
    return cases


def run_testlab(user_tests, impl_code, mutants_json):
    """「你来写测试」：学习者的测试先要在正确实现上全部通过，再看能杀死多少个变异体（故意埋 bug 的实现）。"""
    mutants = json.loads(mutants_json)
    result = {"compile_error": None, "baseline": None, "mutants": [], "killed": 0, "total": len(mutants), "stdout": ""}
    buf = io.StringIO()
    old_out = sys.stdout
    sys.stdout = buf
    try:
        try:
            base = _suite(impl_code, user_tests)
        except Exception as e:
            result["compile_error"] = "测试代码无法运行：" + _fmt_exc(e)
            return json.dumps(result, ensure_ascii=False)
        if not base:
            result["compile_error"] = "没有找到 test_ 开头的测试函数"
            return json.dumps(result, ensure_ascii=False)
        result["baseline"] = {"cases": base, "passed": sum(c["pass"] for c in base), "total": len(base)}
        if result["baseline"]["passed"] != len(base):
            return json.dumps(result, ensure_ascii=False)
        for m in mutants:
            try:
                cases = _suite(m["code"], user_tests)
                failed = [c["name"] for c in cases if not c["pass"]]
            except Exception as e:
                failed = ["（加载失败）"]
            killed = bool(failed)
            result["mutants"].append({"name": m["name"], "killed": killed, "by": failed[:3], "desc": m.get("desc", "") if killed else "", "hint": "" if killed else m.get("hint", "")})
            result["killed"] += killed
    finally:
        sys.stdout = old_out
        out = buf.getvalue()
        result["stdout"] = out if len(out) < 4000 else out[:4000] + "\n…（输出过长已截断）"
    return json.dumps(result, ensure_ascii=False)


def run_perf(user_code, ref_code, spec_json, gen_code, seed):
    """性能检查：用同一个大输入，在同一台机器上比较学习者代码和参考解的耗时（比值与机器快慢无关）。"""
    spec = json.loads(spec_json)
    out = {"error": None}
    try:
        gns = {}
        exec(compile(gen_code, "perf_gen.py", "exec"), gns)
        args = gns["gen_large"](random.Random(int(seed)))
        def timed(code, name, reps):
            ns = {"__name__": name}
            ns.update({k: v for k, v in globals().items() if not k.startswith("_")})
            exec(_src(code, name + ".py"), ns)
            f = _get_callable(ns, spec["fn"])
            best, res = None, None
            for _ in range(reps):
                t = time.perf_counter()
                res = _call(f, args, spec.get("types"), spec.get("ret_type"))
                d = (time.perf_counter() - t) * 1000
                best = d if best is None else min(best, d)
            return best, res
        ref_ms, ref_res = timed(ref_code, "reference", 2)
        user_ms, user_res = timed(user_code, "solution", 1)
        out.update({"ref_ms": round(ref_ms, 1), "user_ms": round(user_ms, 1), "ratio": round(user_ms / max(ref_ms, 1.0), 1),
                    "same": _same(user_res, ref_res, spec.get("compare", "exact"))})
    except RecursionError:
        out["error"] = "RecursionError: 大输入下递归太深，考虑改成迭代或递推"
    except Exception as e:
        out["error"] = _fmt_exc(e)
    return json.dumps(out, ensure_ascii=False)


def run_perf_one(code, name, spec_json, gen_code, seed):
    """性能检查的一半：用固定种子生成大输入，跑一遍并返回耗时和结果摘要（参考解和学习者代码分两次调用，方便按参考解耗时设超时）。"""
    import hashlib
    spec = json.loads(spec_json)
    out = {"error": None}
    try:
        gns = {}
        exec(compile(gen_code, "perf_gen.py", "exec"), gns)
        args = gns["gen_large"](random.Random(int(seed)))
        ns = {"__name__": name}
        ns.update({k: v for k, v in globals().items() if not k.startswith("_")})
        exec(_src(code, name + ".py"), ns)
        f = _get_callable(ns, spec["fn"])
        best, res = None, None
        for _ in range(2 if name == "reference" else 1):
            t = time.perf_counter()
            res = _call(f, args, spec.get("types"), spec.get("ret_type"))
            d = (time.perf_counter() - t) * 1000
            best = d if best is None else min(best, d)
        out["ms"] = round(best, 1)
        out["digest"] = hashlib.md5(json.dumps(_norm(res, spec.get("compare", "exact")), sort_keys=True).encode()).hexdigest()
    except RecursionError:
        out["error"] = "RecursionError: 大输入下递归太深，考虑改成迭代或递推"
    except Exception as e:
        out["error"] = _fmt_exc(e)
    return json.dumps(out, ensure_ascii=False)


def _where(e):
    tb = [fr for fr in traceback.extract_tb(e.__traceback__) if fr.filename == "tests.py"]
    if not tb:
        return ""
    fr = tb[-1]
    return "（tests.py 第 %d 行：%s）" % (fr.lineno, (fr.line or "").strip())


def _src(code, name):
    linecache.cache[name] = (len(code), None, code.splitlines(True), name)
    return compile(code, name, "exec")


def _fmt_exc(e):
    tb = traceback.extract_tb(e.__traceback__)
    lines = [fr for fr in tb if fr.filename in ("solution.py", "snippet.py", "reference.py", "tests.py", "impl.py")]
    where = ""
    if lines:
        fr = lines[-1]
        where = "（第 %d 行：%s）" % (fr.lineno, (fr.line or "").strip())
    if isinstance(e, SyntaxError):
        where = "（第 %s 行：%s）" % (e.lineno, (e.text or "").strip())
    return "%s: %s%s" % (type(e).__name__, e, where)
