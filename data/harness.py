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


# ---------- 系统设计：检查建表语句（MySQL 风格先转成 SQLite 再真正建一遍）----------
def _ddl_to_sqlite(ddl):
    import re
    s = ddl.replace("`", '"')
    s = re.sub(r"--[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\bCOMMENT\s*=?\s*'(?:[^'\\]|\\.|'')*'", "", s, flags=re.I)
    s = re.sub(r"\bENGINE\s*=\s*\w+|\b(DEFAULT\s+)?(CHARSET|CHARACTER\s+SET)\s*=?\s*\w+|\bCOLLATE\s*=?\s*\w+|\bROW_FORMAT\s*=\s*\w+", "", s, flags=re.I)
    s = re.sub(r"\bAUTO_INCREMENT\s*=\s*\d+", "", s, flags=re.I)
    s = re.sub(r"\bAUTO_INCREMENT\b|\bUNSIGNED\b|\bON\s+UPDATE\s+CURRENT_TIMESTAMP(\(\d*\))?", "", s, flags=re.I)
    s = re.sub(r"\bENUM\s*\([^)]*\)|\bSET\s*\('[^)]*\)", "TEXT", s, flags=re.I)
    s = re.sub(r"\b(CURRENT_TIMESTAMP|NOW)\s*\(\s*\d*\s*\)", "CURRENT_TIMESTAMP", s, flags=re.I)
    out, extra, i = [], [], 0
    head = re.compile(r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?(\"?[\w.]+\"?)\s*\(", re.I)
    while True:
        m = head.search(s, i)
        if not m:
            out.append(s[i:]); break
        out.append(s[i:m.end()])
        depth, j = 1, m.end()
        while j < len(s) and depth:
            depth += {"(": 1, ")": -1}.get(s[j], 0); j += 1
        body, table = s[m.end():j - 1], m.group(2).strip('"')
        parts, cur, d = [], "", 0
        for ch in body:
            if ch == "(": d += 1
            if ch == ")": d -= 1
            if ch == "," and d == 0: parts.append(cur); cur = ""
            else: cur += ch
        parts.append(cur)
        keep = []
        for p in parts:
            k = re.match(r"\s*(UNIQUE\s+|FULLTEXT\s+|SPATIAL\s+)?(KEY|INDEX)\s+(\"?\w+\"?)?\s*\((.*)\)\s*$", p, re.I | re.S)
            k2 = re.match(r"\s*UNIQUE\s*\(", p, re.I)
            if k:
                cols = re.sub(r"\(\d+\)", "", k.group(4))
                name = (k.group(3) or "idx_%s_%d" % (table, len(extra))).strip('"')
                extra.append('CREATE %sINDEX "%s_%s" ON "%s"(%s);' % ("UNIQUE " if (k.group(1) or "").strip().upper() == "UNIQUE" else "", table, name, table, cols))
            elif k2 or p.strip():
                keep.append(p)
        out.append(",".join(keep) + ")")
        i = j
    s = "".join(out)
    s = re.sub(r"\)\s*[^;()]*;", ");", s)          # 去掉表选项残留
    return s + "\n" + "\n".join(extra)


def check_ddl(ddl):
    """返回表、列、主键、索引；失败时给出 SQLite 的报错和转换后的语句。"""
    import sqlite3
    conv = _ddl_to_sqlite(ddl)
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(conv)
    except Exception as e:
        return json.dumps({"ok": False, "error": "%s: %s" % (type(e).__name__, e), "converted": conv[:4000]}, ensure_ascii=False)
    tables = []
    for (name,) in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by rowid"):
        cols = [dict(name=r[1], type=r[2], notnull=bool(r[3]), pk=bool(r[5])) for r in con.execute('pragma table_info("%s")' % name)]
        idx = []
        for r in con.execute('pragma index_list("%s")' % name):
            cs = [x[2] for x in con.execute('pragma index_info("%s")' % r[1])]
            idx.append(dict(name=r[1].replace(name + "_", "", 1), unique=bool(r[2]), cols=cs, origin=r[3]))
        tables.append(dict(name=name, cols=cols, indexes=idx))
    return json.dumps({"ok": True, "tables": tables}, ensure_ascii=False)


# ---------- 全栈 · SQL 专项：SQLite 里补上常用 MySQL 函数，比较结果集，检查执行计划 ----------
SQL_TODAY = "2026-06-30"
def _sql_conn():
    import sqlite3, datetime
    con = sqlite3.connect(":memory:")
    def dt(x):
        if x is None: return None
        if isinstance(x, (int, float)): return datetime.datetime.fromtimestamp(x, datetime.timezone.utc).replace(tzinfo=None)
        s = str(x).strip().replace("T", " ")
        for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try: return datetime.datetime.strptime(s[:19] if f.endswith("%S") else s[:len(datetime.datetime(2000, 1, 1).strftime(f))], f)
            except ValueError: pass
        return None
    MY = {"%Y": "%Y", "%y": "%y", "%m": "%m", "%d": "%d", "%H": "%H", "%i": "%M", "%s": "%S", "%S": "%S", "%M": "%B", "%b": "%b", "%W": "%A", "%a": "%a", "%j": "%j", "%p": "%p", "%T": "%H:%M:%S", "%%": "%"}
    def date_format(x, f):
        d = dt(x)
        if d is None or f is None: return None
        out, i = "", 0
        while i < len(f):
            k = f[i:i + 2]
            if k in MY: out += d.strftime(MY[k]); i += 2
            elif k == "%c": out += str(d.month); i += 2
            elif k == "%e": out += str(d.day); i += 2
            else: out += f[i]; i += 1
        return out
    def datediff(a, b):
        x, y = dt(a), dt(b)
        return None if x is None or y is None else (x.date() - y.date()).days
    def concat(*a): return None if any(v is None for v in a) else "".join(str(v) for v in a)
    def concat_ws(sep, *a): return None if sep is None else str(sep).join(str(v) for v in a if v is not None)
    fns = [("IF", 3, lambda c, a, b: a if c else b), ("DATE_FORMAT", 2, date_format), ("DATEDIFF", 2, datediff),
           ("NOW", 0, lambda: SQL_TODAY + " 23:59:59"), ("CURDATE", 0, lambda: SQL_TODAY), ("CURRENT_DATE", 0, lambda: SQL_TODAY),
           ("CONCAT", -1, concat), ("CONCAT_WS", -1, concat_ws),
           ("LEFT", 2, lambda s, n: None if s is None else str(s)[:int(n)]), ("RIGHT", 2, lambda s, n: None if s is None else (str(s)[-int(n):] if int(n) else "")),
           ("GREATEST", -1, lambda *a: None if any(v is None for v in a) else max(a)), ("LEAST", -1, lambda *a: None if any(v is None for v in a) else min(a)),
           ("UNIX_TIMESTAMP", 1, lambda x: None if dt(x) is None else int(dt(x).replace(tzinfo=datetime.timezone.utc).timestamp())),
           ("FROM_UNIXTIME", 1, lambda x: None if x is None else datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
           ("YEAR", 1, lambda x: None if dt(x) is None else dt(x).year), ("MONTH", 1, lambda x: None if dt(x) is None else dt(x).month),
           ("DAY", 1, lambda x: None if dt(x) is None else dt(x).day), ("HOUR", 1, lambda x: None if dt(x) is None else dt(x).hour)]
    for name, n, f in fns: con.create_function(name, n, f, deterministic=True)
    return con


def _sql_setup(ddl, seed):
    con = _sql_conn()
    con.executescript(_ddl_to_sqlite(ddl) if ("ENGINE" in ddl.upper() or "COMMENT" in ddl.upper() or "`" in ddl) else ddl)
    if seed: con.executescript(seed)
    return con


def _sql_norm(v):
    if isinstance(v, bool): return int(v)
    if isinstance(v, (int, float)): return round(float(v), 4)
    if isinstance(v, bytes): return v.hex()
    return v


def _sql_exec(con, sql):
    sql = sql.strip().rstrip(";").strip()
    if not sql: raise ValueError("没有写 SQL")
    if ";" in sql.replace("';'", ""):
        parts = [p for p in sql.split(";") if p.strip()]
        for p in parts[:-1]: con.execute(p)
        sql = parts[-1]
    t0 = time.time()
    cur = con.execute(sql)
    cols = [c[0] for c in (cur.description or [])]
    rows = cur.fetchmany(2001)
    return cols, rows, int((time.time() - t0) * 1000)


def run_sql(ddl, seed, user_sql, ref_sql, ordered):
    """在同一份数据上分别跑学习者和参考 SQL，比较结果集（列名不比，列数和值要一致；ordered 时顺序也要一致）。"""
    out = {"ok": False}
    try:
        con = _sql_setup(ddl, seed)
        rc, rr, _ = _sql_exec(con, ref_sql)
    except Exception as e:
        return json.dumps({"ok": False, "error": "参考答案运行失败：%s" % e}, ensure_ascii=False)
    try:
        con2 = _sql_setup(ddl, seed)
        uc, ur, ms = _sql_exec(con2, user_sql)
    except Exception as e:
        return json.dumps({"ok": False, "error": "%s: %s" % (type(e).__name__, e), "ref_columns": rc, "ref_rows": [list(map(_sql_norm, r)) for r in rr[:50]]}, ensure_ascii=False)
    U = [tuple(_sql_norm(v) for v in r) for r in ur]
    R = [tuple(_sql_norm(v) for v in r) for r in rr]
    key = lambda t: tuple((0, "") if v is None else (1, v) if isinstance(v, float) else (2, str(v)) for v in t)
    same_cols = len(uc) == len(rc)
    match = same_cols and (U == R if ordered else sorted(U, key=key) == sorted(R, key=key))
    hint = ""
    if not same_cols: hint = "列数不对：你返回 %d 列，期望 %d 列" % (len(uc), len(rc))
    elif len(U) != len(R): hint = "行数不对：你返回 %d 行，期望 %d 行" % (len(U), len(R))
    elif not match and ordered and sorted(U, key=key) == sorted(R, key=key): hint = "数据都对，但顺序不对（这题要求排序）"
    elif not match: hint = "行数对，但有值不一样"
    out.update(ok=True, match=match, hint=hint, ms=ms, columns=uc, rows=[list(map(_sql_norm, r)) for r in ur[:50]], total=len(ur),
               ref_columns=rc, ref_rows=[list(map(_sql_norm, r)) for r in rr[:50]], ref_total=len(rr))
    return json.dumps(out, ensure_ascii=False)


def _plan(con, query, table):
    rows = con.execute("EXPLAIN QUERY PLAN " + query.strip().rstrip(";")).fetchall()
    detail = [r[-1] for r in rows]
    t = table.lower()
    mine = [d for d in detail if (" " + t + " ") in (" " + d.lower() + " ") or d.lower().endswith(" " + t)]
    scan = any(d.upper().startswith("SCAN") and "INDEX" not in d.upper() for d in mine)
    uses = any(("USING INDEX" in d.upper() or "USING COVERING INDEX" in d.upper() or "USING INTEGER PRIMARY KEY" in d.upper() or "USING PRIMARY KEY" in d.upper()) for d in mine)
    return detail, scan, uses


def run_index(ddl, seed, index_sql, query, table):
    """先看原始执行计划，再执行学习者的建索引语句，看目标表是否从全表扫描变成走索引。"""
    try:
        con = _sql_setup(ddl, seed)
        before, b_scan, b_uses = _plan(con, query, table)
    except Exception as e:
        return json.dumps({"ok": False, "error": "题目数据有问题：%s" % e}, ensure_ascii=False)
    try:
        if index_sql.strip(): con.executescript(index_sql)
        after, a_scan, a_uses = _plan(con, query, table)
        idx = [dict(name=r[1], cols=[x[2] for x in con.execute('pragma index_info("%s")' % r[1])]) for r in con.execute('pragma index_list("%s")' % table) if not r[1].startswith("sqlite_autoindex")]
    except Exception as e:
        return json.dumps({"ok": False, "error": "%s: %s" % (type(e).__name__, e), "before": before}, ensure_ascii=False)
    return json.dumps({"ok": True, "before": before, "after": after, "before_scan": b_scan, "after_scan": a_scan, "uses_index": a_uses and not a_scan, "indexes": idx}, ensure_ascii=False)


def sql_peek(ddl, seed):
    """数据集预览：每张表的列、行数和前 5 行。"""
    try:
        con = _sql_setup(ddl, seed)
        out = []
        for (t,) in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by rowid"):
            cols = [r[1] + (" " + r[2] if r[2] else "") for r in con.execute('pragma table_info("%s")' % t)]
            n = con.execute('select count(*) from "%s"' % t).fetchone()[0]
            rows = [list(map(_sql_norm, r)) for r in con.execute('select * from "%s" limit 5' % t)]
            out.append(dict(name=t, cols=cols, count=n, rows=rows))
        return json.dumps({"ok": True, "tables": out}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
