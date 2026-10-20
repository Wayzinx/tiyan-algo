# 校验「手写实战」题目：参考实现必须通过全部测试，起始代码必须不能直接通过；生成 labs.json
# 用法：<带 numpy 的 python3.12> gen_labs.py [--only labs/l1.py]
import json, sys, os, glob, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import harness
REQ = ["id", "course", "title", "level", "desc", "starter", "tests", "hidden", "solution", "hints", "points"]
def load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.LABS
files = [os.path.join(D, sys.argv[sys.argv.index("--only") + 1])] if "--only" in sys.argv else sorted(glob.glob(os.path.join(D, "labs", "*.py")))
labs, errors, ids = [], [], set()
for f in files:
    labs += load(f)
for lab in labs:
    lid = lab.get("id", "?")
    miss = [k for k in REQ if not lab.get(k)]
    if miss: errors.append(f"{lid} 缺字段 {miss}"); continue
    if lid in ids: errors.append(f"{lid} id 重复")
    ids.add(lid)
    if lab["course"] not in ("llm", "agent", "harness", "dev", "arch"): errors.append(f"{lid} course 不合法")
    if lab["level"] not in ("easy", "medium", "hard"): errors.append(f"{lid} level 不合法")
    if len(lab["hints"]) != 3: errors.append(f"{lid} hints 需要 3 条")
    if len(lab["desc"]) < 300: errors.append(f"{lid} 题面太短")
    nv = lab["tests"].count("def test_"); nh = lab["hidden"].count("def test_")
    if not (3 <= nv <= 6 and 2 <= nh <= 6): errors.append(f"{lid} 可见测试 3–6 个、隐藏测试 2–6 个（现在 {nv}/{nh}）")
    r = json.loads(harness.run_lab(lab["solution"], lab["tests"] + "\n\n" + lab["hidden"]))
    if r["compile_error"]: errors.append(f"{lid} 参考实现无法运行：{r['compile_error']}"); continue
    bad = [c for c in r["cases"] if not c["pass"]]
    if bad: errors.append(f"{lid} 参考实现没通过：{bad[0]['name']} {bad[0].get('error', '')[:200]}")
    slow = [c for c in r["cases"] if c["ms"] > 1500]
    if slow: errors.append(f"{lid} 测试太慢：{slow[0]['name']} {slow[0]['ms']}ms")
    s = json.loads(harness.run_lab(lab["starter"], lab["tests"]))
    if not s["compile_error"] and s["passed"] == s["total"]: errors.append(f"{lid} 起始代码直接就能通过可见测试，起始代码应该留空待实现")
    lab["numpy"] = bool(lab.get("numpy"))
print("实战题:", len(labs), {c: sum(1 for l in labs if l.get("course") == c) for c in ("llm", "agent", "harness", "dev", "arch")})
if errors:
    print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
if "--only" not in sys.argv:
    json.dump(labs, open(os.path.join(D, "labs.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("OK -> labs.json", len(json.dumps(labs, ensure_ascii=False)), "chars")
else:
    print("OK")
