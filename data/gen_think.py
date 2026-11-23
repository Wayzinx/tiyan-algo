# 校验「思路」模块的思路阶梯（data/think/*.py 里的 LADDERS），生成 think.json
# 用法：python3 gen_think.py                    校验全部并写 think.json（先跑 gen.py 生成 problems.json）
#       python3 gen_think.py --check think/a.py   只校验这一个文件，不写 think.json
import json, os, sys, glob, re, signal, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.setrecursionlimit(10000)
import harness
_fp = os.path.join(D, ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w and w != "字节"]
KINDS = ["ask", "input", "brute", "waste", "tool", "state"]
KEYS = ["read", "steps", "brute", "cloze", "say", "trap"]
MARK = re.compile(r"⟦(\d)⟧")
PROBLEMS = {p["id"]: p for p in json.load(open(os.path.join(D, "problems.json"), encoding="utf-8"))}


class _Timeout(BaseException):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def run(code, p, tests, limit=6):
    """返回 (是否全过, 说明)。超时算不通过。"""
    spec = json.dumps({"fn": p["fn"], "types": p["types"], "ret_type": p["ret_type"], "compare": p["compare"], "tests": tests})
    signal.signal(signal.SIGALRM, _alarm); signal.alarm(limit)
    try:
        r = json.loads(harness.run_tests(code, spec))
    except _Timeout:
        return False, "超时"
    finally:
        signal.alarm(0)
    if r["compile_error"]: return False, "编译错误：" + r["compile_error"][:200]
    bad = [c for c in r["cases"] if not c["pass"]]
    return r["ok"], ("" if not bad else f"用例 {bad[0]['i']} 不过：输入 {bad[0]['args'][:120]} 期望 {bad[0]['expected'][:80]} 得到 {bad[0].get('got', bad[0].get('error', ''))[:200]}")


def fill(code, blanks, override=None):
    def rep(m):
        i = int(m.group(1)) - 1
        return override[1] if override and override[0] == i else blanks[i]["a"]
    return MARK.sub(rep, code)


def check(pid, L, errors):
    p = PROBLEMS.get(pid)
    if not p: errors.append(f"{pid} 不在 problems.json 里"); return
    miss = [k for k in KEYS if not L.get(k)]
    if miss: errors.append(f"{pid} 缺字段 {miss}"); return
    extra = set(L) - set(KEYS)
    if extra: errors.append(f"{pid} 有未知字段 {sorted(extra)}")
    if not (20 <= len(L["read"]) <= 160): errors.append(f"{pid} read（一句话复述）20–160 字")
    st = L["steps"]
    if [s.get("k") for s in st] != KINDS: errors.append(f"{pid} steps 必须正好 6 步，k 依次是 {KINDS}"); return
    for s in st:
        tag = f"{pid}/{s['k']}"
        if not (4 <= len(s.get("q", "")) <= 60): errors.append(f"{tag} q 4–60 字")
        o = s.get("options") or []
        if not (3 <= len(o) <= 4) or len(set(o)) != len(o) or any(not isinstance(x, str) or not (2 <= len(x) <= 80) for x in o):
            errors.append(f"{tag} options 需要 3–4 个不重复的选项，每个 2–80 字")
        if not isinstance(s.get("answer"), int) or not (0 <= s["answer"] < len(o)): errors.append(f"{tag} answer 是正确选项的下标")
        if not (30 <= len(s.get("why", "")) <= 300): errors.append(f"{tag} why 30–300 字（现在 {len(s.get('why', ''))}）")
        if set(s) - {"k", "q", "options", "answer", "why"}: errors.append(f"{tag} 有未知字段")
    if not (60 <= len(L["say"]) <= 340): errors.append(f"{pid} say（30 秒口述）60–340 字")
    if not (20 <= len(L["trap"]) <= 220): errors.append(f"{pid} trap 20–220 字")
    small = [t for t in p["tests"] if len(json.dumps(t["args"])) < 1500]
    if len(small) < 3: small = p["tests"][:3]
    ok, why = run(L["brute"], p, small)
    if not ok: errors.append(f"{pid} brute（暴力解）没通过小用例：{why}")
    if L["brute"].strip() == p["solution"].strip(): errors.append(f"{pid} brute 不能和参考解一样")
    cz = L["cloze"]
    code, blanks = cz.get("code", ""), cz.get("blanks") or []
    nums = [int(x) for x in MARK.findall(code)]
    if not (2 <= len(blanks) <= 5): errors.append(f"{pid} cloze.blanks 2–5 个"); return
    if sorted(nums) != list(range(1, len(blanks) + 1)): errors.append(f"{pid} cloze.code 里 ⟦1⟧…⟦{len(blanks)}⟧ 每个正好出现一次（现在 {nums}）"); return
    for i, b in enumerate(blanks):
        a = b.get("a", "")
        if not a or "\n" in a or len(a) > 70 or "⟦" in a: errors.append(f"{pid} 空 {i + 1} 的答案要是单行、≤70 字符")
        if not (4 <= len(b.get("hint", "")) <= 80): errors.append(f"{pid} 空 {i + 1} 的 hint 4–80 字")
    if errors and errors[-1].startswith(pid + " 空"): return
    ok, why = run(fill(code, blanks), p, p["tests"])
    if not ok: errors.append(f"{pid} 填入答案后没通过全部用例：{why}")
    for i in range(len(blanks)):
        ok, _ = run(fill(code, blanks, (i, "None")), p, p["tests"], limit=4)
        if ok: errors.append(f"{pid} 空 {i + 1} 填 None 也能通过——这个空不关键，换一个")
    blob = json.dumps(L, ensure_ascii=False)
    for w in FORBIDDEN:
        if w in blob: errors.append(f"{pid} 含有不该出现的词「{w}」")


def load(path):
    spec = importlib.util.spec_from_file_location("think_" + os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, "LADDERS", {})


def main():
    args = sys.argv[1:]
    only = args[args.index("--check") + 1] if "--check" in args else None
    files = [os.path.join(D, only)] if only else sorted(glob.glob(os.path.join(D, "think", "*.py")))
    out, errors = {}, []
    for f in files:
        try: lad = load(f)
        except Exception as e: errors.append(f"{f} 导入失败：{e!r}"); continue
        for pid, L in lad.items():
            if pid in out: errors.append(f"{pid} 在多个文件里重复")
            check(pid, L, errors)
            out[pid] = L
    print(f"阶梯 {len(out)} / 题库 {len(PROBLEMS)}")
    if not only:
        missing = [k for k in PROBLEMS if k not in out]
        if missing: print("还没有阶梯的题：", ", ".join(missing))
    kit = [] if only else check_kit(errors)
    if errors:
        print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
    if only: print("OK（只校验，未写 think.json）"); return
    json.dump({"ladders": out, "kit": kit}, open(os.path.join(D, "think.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"OK -> think.json（盲写基本功 {len(kit)} 题）")


def check_kit(errors):
    """盲写基本功：solution 通过全部测试、starter 至少挂一个、字段齐全。"""
    from think_kit import KIT
    ids = set()
    for k in KIT:
        kid = "kit/" + k["id"]
        if k["id"] in ids: errors.append(f"{kid} id 重复")
        ids.add(k["id"])
        for f in ["title", "use", "prompt", "starter", "solution", "tests", "tip"]:
            if not k.get(f): errors.append(f"{kid} 缺 {f}")
        good = json.loads(harness.run_lab(k["solution"], k["tests"]))
        if good["compile_error"] or good["passed"] != good["total"] or not good["total"]:
            errors.append(f"{kid} 参考写法没通过测试：{good['compile_error'] or [c for c in good['cases'] if not c['pass']][:1]}")
        bad = json.loads(harness.run_lab(k["starter"], k["tests"]))
        if not bad["compile_error"] and bad["passed"] == bad["total"]:
            errors.append(f"{kid} 初始代码就能通过测试，测试太弱")
    return KIT


if __name__ == "__main__":
    main()
