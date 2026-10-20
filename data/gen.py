# 校验题库并生成 problems.json：用参考解算出每个用例的 expected
import json, sys
sys.setrecursionlimit(10000)
import harness
from problems import PROBLEMS

PATTERNS = {"hash", "two_pointers", "sliding_window", "prefix_sum", "binary_search", "mono_stack",
            "heap", "linked_list", "tree", "graph", "backtracking", "dp", "greedy"}
REQUIRED = ["id", "title", "pattern", "level", "lc", "slug", "desc", "examples", "constraints", "fn",
            "params", "ret", "tests", "solution", "complexity", "hints", "key", "pitfalls"]


def starter(p):
    sig = ", ".join("%s: %s" % (n, t) for n, t in p["params"])
    return "class Solution:\n    def %s(self, %s) -> %s:\n        " % (p["fn"], sig, p["ret"])


out, errors, ids = [], [], set()
for p in PROBLEMS:
    pid = p.get("id", "?")
    miss = [k for k in REQUIRED if k not in p]
    if miss:
        errors.append("%s 缺字段 %s" % (pid, miss)); continue
    if pid in ids:
        errors.append("%s id 重复" % pid)
    ids.add(pid)
    if p["pattern"] not in PATTERNS:
        errors.append("%s pattern 不合法: %s" % (pid, p["pattern"]))
    if p["level"] not in ("easy", "medium", "hard"):
        errors.append("%s level 不合法" % pid)
    if len(p["tests"]) < 6:
        errors.append("%s 用例少于 6 个" % pid)
    if len(p["hints"]) != 3:
        errors.append("%s hints 需要正好 3 条" % pid)
    types = p.get("types") or [None] * len(p["params"])
    if len(types) != len(p["params"]):
        errors.append("%s types 长度和 params 不一致" % pid)
    spec = {"fn": p["fn"], "types": types, "ret_type": p.get("ret_type"), "compare": p.get("compare", "exact"),
            "tests": [{"args": list(a)} for a in p["tests"]]}
    for a in p["tests"]:
        if len(a) != len(p["params"]):
            errors.append("%s 有用例参数个数不对: %r" % (pid, a)[:200])
    try:
        refs = json.loads(harness.run_reference(p["solution"], json.dumps(spec)))
    except Exception as e:
        errors.append("%s 参考解无法运行: %r" % (pid, e)); continue
    bad = [r for r in refs if "error" in r]
    if bad:
        errors.append("%s 参考解报错: %s" % (pid, bad[0]["error"])); continue
    for t, r in zip(spec["tests"], refs):
        t["expected"] = r["expected"]
    check = json.loads(harness.run_tests(p["solution"], json.dumps(spec)))
    if not check["ok"]:
        errors.append("%s 参考解没通过自身用例: %s" % (pid, check.get("compile_error") or check["cases"][:1]))
    try:
        compile(starter(p) + "pass\n", "starter", "exec")
    except SyntaxError as e:
        errors.append("%s starter 语法错误 %s" % (pid, e))
    size = len(json.dumps(spec["tests"]))
    if size > 25000:
        errors.append("%s 用例 JSON 太大 (%d 字节)，请缩小大用例" % (pid, size))
    q = {k: p[k] for k in REQUIRED if k != "tests"}
    q.update({"types": types, "ret_type": p.get("ret_type"), "compare": p.get("compare", "exact"),
              "starter": starter(p), "tests": spec["tests"], "params": [list(x) for x in p["params"]]})
    out.append(q)

counts = {}
for q in out:
    counts[q["pattern"]] = counts.get(q["pattern"], 0) + 1
print("题目数:", len(out), "各题型:", counts)
if errors:
    print("\n".join("ERROR " + e for e in errors))
    sys.exit(1)
json.dump(out, open("problems.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> problems.json", len(json.dumps(out, ensure_ascii=False)), "chars")
