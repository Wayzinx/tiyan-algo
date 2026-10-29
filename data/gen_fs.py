# 校验「全栈」模块内容（排障演练 / SQL 专项 / 技术选型 / 代码评审 / 语言专项 / 前端手写），生成 fs.json
# 用法：python3 gen_fs.py [--only fs/xxx.py]
# 「说输出」题会真的运行：JavaScript / TypeScript 用 node，Python 用 python3，Go / Java 用环境变量 FS_GO / FS_JAVA 指向的可执行文件（没有就跳过并警告）
import json, os, sys, glob, re, subprocess, tempfile, importlib.util, shutil
D = os.path.dirname(os.path.abspath(__file__))
_fp = os.path.join(D, ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w and w != "字节"]
spec = importlib.util.spec_from_file_location("harness", os.path.join(D, "harness.py")); H = importlib.util.module_from_spec(spec); spec.loader.exec_module(H)
JS_HARNESS = open(os.path.join(D, "fs_js.js"), encoding="utf-8").read()
NODE = shutil.which("node")
GO = os.environ.get("FS_GO") or shutil.which("go")
JAVA = os.environ.get("FS_JAVA") or shutil.which("java")
warns = []

def load(p, name):
    s = importlib.util.spec_from_file_location(os.path.basename(p)[:-3], p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return getattr(m, name, None)
def scan(obj, oid, errors):
    blob = json.dumps(obj, ensure_ascii=False)
    for w in FORBIDDEN:
        if w in blob: errors.append(f"{oid} 含有不该出现的内部词「{w}」")
def need(x, oid, keys, errors):
    miss = [k for k in keys if x.get(k) in (None, "", [], {})]
    if miss: errors.append(f"{oid} 缺字段 {miss}")
    return not miss
def ln(x, k): return len(str(x.get(k) or ""))

# ---------- 排障演练 ----------
AREAS = ["前端", "后端", "数据库", "中间件", "发布与配置", "网络"]
LEVELS = ["入门", "中等", "困难"]
KINDS = ["metric", "log", "trace", "sql", "code", "config", "cmd", "change", "frontend", "ask"]
def check_case(c, errors):
    cid = c.get("id", "?")
    if not need(c, cid, ["id", "order", "area", "level", "title", "symptom", "context", "checks", "root_cause", "stop_bleeding", "fix", "prevention", "ideal_path", "traps", "points", "followups", "report"], errors): return
    if not re.fullmatch(r"t\d{1,2}", cid): errors.append(f"{cid} id 应该是 t1、t2……")
    if c["area"] not in AREAS: errors.append(f"{cid} area 必须是 {AREAS}")
    if c["level"] not in LEVELS: errors.append(f"{cid} level 必须是 {LEVELS}")
    for k, lo in [("symptom", 60), ("context", 120), ("root_cause", 60), ("stop_bleeding", 30), ("fix", 60), ("prevention", 40), ("report", 300)]:
        if ln(c, k) < lo: errors.append(f"{cid} {k} 太短（≥{lo} 字）")
    ch = c["checks"]
    if not (8 <= len(ch) <= 14): errors.append(f"{cid} checks 需要 8–14 个排查动作")
    keys = [x.get("key") for x in ch]
    if len(set(keys)) != len(keys): errors.append(f"{cid} checks 的 key 重复")
    for x in ch:
        k = x.get("key", "?")
        if not (re.fullmatch(r"[a-z0-9_]+", str(k)) and x.get("label") and isinstance(x.get("cost"), int) and 1 <= x["cost"] <= 10 and x.get("kind") in KINDS and ln(x, "content") >= 40 and x.get("value") in (0, 1, 2)):
            errors.append(f"{cid}/{k} 需要 key(小写) / label / cost(1–10 整数) / kind∈{KINDS} / content(≥40 字) / value∈0,1,2")
    if sum(1 for x in ch if x.get("value") == 2) < 3: errors.append(f"{cid} 至少 3 个 value=2 的关键线索")
    if sum(1 for x in ch if x.get("value") == 0) < 2: errors.append(f"{cid} 至少 2 个 value=0 的干扰项")
    val = {x.get("key"): x.get("value") for x in ch}
    if not (3 <= len(c["ideal_path"]) <= 6) or any(val.get(k, 0) < 1 for k in c["ideal_path"]): errors.append(f"{cid} ideal_path 需要 3–6 个存在且有用（value≥1）的 key")
    if not (3 <= len(c["traps"]) <= 5): errors.append(f"{cid} traps 需要 3–5 条常见误判")
    if not (4 <= len(c["points"]) <= 7): errors.append(f"{cid} points 需要 4–7 个得分点")
    if not (3 <= len(c["followups"]) <= 5) or any(not (f.get("q") and ln(f, "a") >= 60) for f in c["followups"]): errors.append(f"{cid} followups 需要 3–5 个 {{q, a(≥60 字)}}")
    scan(c, cid, errors)

# ---------- SQL 专项 ----------
def check_sql(datasets, queries, index, schema, errors):
    for did, ds in datasets.items():
        if not need(ds, did, ["title", "desc", "ddl", "seed"], errors): continue
        if ln(ds, "desc") < 60: errors.append(f"数据集 {did} desc 太短（≥60 字，要写清表关系和“今天”是 {H.SQL_TODAY}）")
        try:
            con = H._sql_setup(ds["ddl"], ds["seed"])
            tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            n = sum(con.execute(f'select count(*) from "{t}"').fetchone()[0] for t in tabs)
            if len(tabs) < 3: errors.append(f"数据集 {did} 至少 3 张表")
            if n < 60: errors.append(f"数据集 {did} 数据太少（{n} 行，至少 60 行）")
        except Exception as e: errors.append(f"数据集 {did} 建表或插数据失败：{e}")
        scan(ds, "数据集 " + did, errors)
    for q in queries:
        qid = q.get("id", "?")
        if not need(q, qid, ["id", "order", "dataset", "level", "topic", "title", "question", "hint", "answer", "explain", "pitfalls"], errors): continue
        if "ordered" not in q or not isinstance(q["ordered"], bool): errors.append(f"{qid} ordered 必须是 True / False")
        if q["dataset"] not in datasets: errors.append(f"{qid} dataset 不存在"); continue
        if q["level"] not in LEVELS: errors.append(f"{qid} level 必须是 {LEVELS}")
        if ln(q, "question") < 30 or ln(q, "explain") < 60: errors.append(f"{qid} question ≥30 字、explain ≥60 字")
        if q.get("ordered") and "ORDER BY" not in q["answer"].upper(): errors.append(f"{qid} ordered=True 但参考答案没有 ORDER BY")
        ds = datasets[q["dataset"]]
        r = json.loads(H.run_sql(ds["ddl"], ds["seed"], q["answer"], q["answer"], bool(q.get("ordered"))))
        if not r.get("ok"): errors.append(f"{qid} 参考答案运行失败：{r.get('error')}")
        elif not r["match"]: errors.append(f"{qid} 参考答案和自己比较都不一致（结果不确定？加 ORDER BY 或去掉 ordered）")
        elif r["ref_total"] == 0: errors.append(f"{qid} 参考答案查出 0 行，换个条件让结果非空")
        elif r["ref_total"] > 200: errors.append(f"{qid} 参考答案返回 {r['ref_total']} 行，太多（≤200）")
        scan(q, qid, errors)
    for x in index:
        iid = x.get("id", "?")
        if not need(x, iid, ["id", "order", "dataset", "title", "question", "query", "table", "answer", "explain", "pitfalls"], errors): continue
        if x["dataset"] not in datasets: errors.append(f"{iid} dataset 不存在"); continue
        ds = datasets[x["dataset"]]
        r0 = json.loads(H.run_index(ds["ddl"], ds["seed"], "", x["query"], x["table"]))
        r1 = json.loads(H.run_index(ds["ddl"], ds["seed"], x["answer"], x["query"], x["table"]))
        if not r0.get("ok") or not r1.get("ok"): errors.append(f"{iid} 执行失败：{r0.get('error') or r1.get('error')}")
        else:
            if not r0["before_scan"] or r0["uses_index"]: errors.append(f"{iid} 不加索引时 {x['table']} 应该是全表扫描，实际计划：{r0['before']}")
            if not r1["uses_index"]: errors.append(f"{iid} 加了参考索引后 {x['table']} 没有走索引，计划：{r1['after']}")
        scan(x, iid, errors)
    for x in schema:
        sid = x.get("id", "?")
        if not need(x, sid, ["id", "order", "title", "requirement", "queries_needed", "reference_ddl", "explain", "points"], errors): continue
        if ln(x, "requirement") < 100 or ln(x, "explain") < 150: errors.append(f"{sid} requirement ≥100 字、explain ≥150 字")
        if not (3 <= len(x["queries_needed"]) <= 6) or not (4 <= len(x["points"]) <= 7): errors.append(f"{sid} queries_needed 3–6 条、points 4–7 条")
        r = json.loads(H.check_ddl(x["reference_ddl"]))
        if not r["ok"]: errors.append(f"{sid} reference_ddl 建表失败：{r['error']}")
        elif len(r["tables"]) < 3: errors.append(f"{sid} reference_ddl 至少 3 张表")
        scan(x, sid, errors)

# ---------- 技术选型 ----------
def check_tech(cards, scenarios, errors):
    ids = [c.get("id") for c in cards]
    if len(set(ids)) != len(ids): errors.append("技术卡片 id 重复")
    for c in cards:
        cid = c.get("id", "?")
        if not need(c, cid, ["id", "name", "cat", "what", "pros", "cons", "fits", "avoid", "vs", "pitfalls", "interview"], errors): continue
        rules = [("pros", 3, 6), ("cons", 3, 6), ("fits", 3, 5), ("avoid", 2, 4), ("vs", 1, 3), ("pitfalls", 3, 5), ("interview", 2, 4)]
        for k, lo, hi in rules:
            if not (lo <= len(c[k]) <= hi): errors.append(f"{cid} {k} 需要 {lo}–{hi} 条")
        if ln(c, "what") < 30: errors.append(f"{cid} what ≥30 字")
        if any(not (v.get("other") and ln(v, "diff") >= 30) for v in c["vs"]): errors.append(f"{cid} vs 需要 {{other, diff(≥30 字)}}")
        if any(not (v.get("q") and ln(v, "a") >= 60) for v in c["interview"]): errors.append(f"{cid} interview 需要 {{q, a(≥60 字)}}")
        scan(c, cid, errors)
    for s in scenarios:
        sid = s.get("id", "?")
        if not need(s, sid, ["id", "order", "title", "level", "requirement", "constraints", "options", "reference", "points"], errors): continue
        if ln(s, "requirement") < 80 or ln(s, "constraints") < 30: errors.append(f"{sid} requirement ≥80 字、constraints ≥30 字")
        if not (2 <= len(s["options"]) <= 5): errors.append(f"{sid} options 需要 2–5 个候选")
        ref = s["reference"]
        if not all(ln(ref, k) >= 20 for k in ["choice", "why", "why_not", "downside", "metric"]): errors.append(f"{sid} reference 需要 choice / why / why_not / downside / metric（各 ≥20 字）")
        if not (3 <= len(s["points"]) <= 6): errors.append(f"{sid} points 需要 3–6 条")
        scan(s, sid, errors)

# ---------- 代码评审 ----------
SEV = ["严重", "一般", "建议"]
IKIND = ["bug", "并发", "安全", "性能", "可维护", "健壮性"]
def check_review(r, errors):
    rid = r.get("id", "?")
    if not need(r, rid, ["id", "order", "lang", "title", "context", "code", "issues", "summary", "points"], errors): return
    n = r["code"].count("\n") + 1
    if n < 15: errors.append(f"{rid} code 太短（≥15 行）")
    if not (3 <= len(r["issues"]) <= 7): errors.append(f"{rid} issues 需要 3–7 个")
    for i in r["issues"]:
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", str(i.get("lines", "")))
        if not m or int(m.group(2) or m.group(1)) > n or int(m.group(1)) < 1: errors.append(f"{rid} issue lines「{i.get('lines')}」不合法（例：12 或 12-14，在 1–{n} 内）")
        if i.get("severity") not in SEV or i.get("kind") not in IKIND or ln(i, "desc") < 20 or ln(i, "fix") < 15: errors.append(f"{rid} issue 需要 severity∈{SEV} / kind∈{IKIND} / desc(≥20) / fix(≥15)")
    if not any(i.get("severity") == "严重" for i in r["issues"]): errors.append(f"{rid} 至少 1 个「严重」问题")
    if ln(r, "summary") < 40 or not (3 <= len(r["points"]) <= 6): errors.append(f"{rid} summary ≥40 字、points 3–6 条")
    scan(r, rid, errors)

# ---------- 语言专项 ----------
RUNNABLE = {"JavaScript": ".js", "TypeScript": ".ts", "Python": ".py", "Go": ".go", "Java": ".java"}
def run_code(lang, code):
    ext = RUNNABLE[lang]
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, ("Main" if lang == "Java" else "main") + ext)
        open(f, "w", encoding="utf-8").write(code)
        env = dict(os.environ, NODE_NO_WARNINGS="1", GOCACHE=os.path.join(tempfile.gettempdir(), "fs-gocache"), GOPATH=os.path.join(tempfile.gettempdir(), "fs-gopath"), GOFLAGS="-mod=mod", GO111MODULE="off")
        cmd = {"JavaScript": [NODE, f], "TypeScript": [NODE, "--experimental-strip-types", f], "Python": [sys.executable, f], "Go": [GO, "run", f], "Java": [JAVA, f]}[lang]
        if not cmd[0]: return None
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env, cwd=td)
        return p.stdout if p.returncode == 0 else "【运行失败】" + (p.stderr or p.stdout)[-600:]
LANGS = ["JavaScript", "TypeScript", "React", "Vue", "CSS", "浏览器", "工程化", "网络", "Go", "Java", "Python", "Web 框架", "数据库", "Linux"]
def norm_out(s): return "\n".join(l.rstrip() for l in str(s).replace("\r\n", "\n").strip().split("\n"))
def check_lang(x, errors):
    lid = x.get("id", "?")
    if not need(x, lid, ["id", "order", "track", "lang", "topic", "kind", "q", "explain"], errors): return
    if x["track"] not in ("前端", "后端"): errors.append(f"{lid} track 必须是 前端 / 后端")
    if x["lang"] not in LANGS: errors.append(f"{lid} lang 必须是 {LANGS}")
    if ln(x, "explain") < 40: errors.append(f"{lid} explain ≥40 字")
    k = x["kind"]
    if k == "output":
        if x["lang"] not in RUNNABLE: errors.append(f"{lid} 说输出题只能是 {list(RUNNABLE)}"); return
        if not x.get("code") or "answer" not in x: errors.append(f"{lid} 说输出题需要 code 和 answer（精确的标准输出）"); return
        out = run_code(x["lang"], x["code"])
        if out is None: warns.append(f"{lid}：本机没有 {x['lang']} 运行环境，没校验输出"); return
        if norm_out(out) != norm_out(x["answer"]): errors.append(f"{lid} answer 和真实运行输出不一致：\n期望：{x['answer']!r}\n实际：{norm_out(out)!r}")
    elif k == "choice":
        o, a = x.get("options") or [], x.get("answer")
        if not (3 <= len(o) <= 5) or not isinstance(a, list) or not a or any(not isinstance(i, int) or not 0 <= i < len(o) for i in a): errors.append(f"{lid} 选择题需要 options 3–5 个、answer 为正确下标列表")
    elif k == "short":
        if not (3 <= len(x.get("points") or []) <= 6) or ln(x, "answer") < 80: errors.append(f"{lid} 简答题需要 points 3–6 条、answer（参考答案 ≥80 字）")
    else: errors.append(f"{lid} kind 必须是 output / choice / short")
    scan(x, lid, errors)

# ---------- 前端手写 ----------
def run_js_tests(code, tests):
    prog = JS_HARNESS + "\n;\n" + code + "\n;\n" + tests + "\n;__run(3000).then(r => { console.log('__RESULT__' + JSON.stringify(r)); process.exit(0); });\n"
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "t.js"); open(f, "w", encoding="utf-8").write(prog)
        p = subprocess.run([NODE, f], capture_output=True, text=True, timeout=120)
    m = re.search(r"__RESULT__(.*)", p.stdout)
    if not m: return None, (p.stderr or p.stdout)[-600:]
    return json.loads(m.group(1)), ""
def check_hand(x, errors):
    hid = x.get("id", "?")
    if not need(x, hid, ["id", "order", "title", "level", "desc", "starter", "tests", "solution", "points", "hints"], errors): return
    if ln(x, "desc") < 60: errors.append(f"{hid} desc ≥60 字")
    if x["tests"].count("test(") < 4: errors.append(f"{hid} 至少 4 个 test(...)")
    if not (2 <= len(x["points"]) <= 5) or not (2 <= len(x["hints"]) <= 3): errors.append(f"{hid} points 2–5 条、hints 2–3 条")
    r, err = run_js_tests(x["solution"], x["tests"])
    if r is None: errors.append(f"{hid} 参考实现跑测试崩了：{err}")
    elif not all(t["pass"] for t in r): errors.append(f"{hid} 参考实现没通过：{[t for t in r if not t['pass']][:3]}")
    r2, _ = run_js_tests(x["starter"], x["tests"])
    if r2 is not None and all(t["pass"] for t in r2): errors.append(f"{hid} starter 不应该直接通过全部测试")
    scan(x, hid, errors)

# ---------- 汇总 ----------
NAMES = ["CASES", "SQL_DATASETS", "SQL_QUERIES", "SQL_INDEX", "SQL_SCHEMA", "TECH_CARDS", "TECH_SCENARIOS", "REVIEWS", "LANG", "HANDWRITE"]
def collect(files):
    acc = {n: ({} if n == "SQL_DATASETS" else []) for n in NAMES}
    for f in files:
        for n in NAMES:
            v = load(f, n)
            if v is None: continue
            if n == "SQL_DATASETS": acc[n].update(v)
            else: acc[n] += v
    return acc
def validate(acc, errors, all_datasets=None):
    for c in acc["CASES"]: check_case(c, errors)
    check_sql(all_datasets or acc["SQL_DATASETS"], acc["SQL_QUERIES"], acc["SQL_INDEX"], acc["SQL_SCHEMA"], errors)
    check_tech(acc["TECH_CARDS"], acc["TECH_SCENARIOS"], errors)
    for r in acc["REVIEWS"]: check_review(r, errors)
    for x in acc["LANG"]: check_lang(x, errors)
    for x in acc["HANDWRITE"]: check_hand(x, errors)
    for n in ["CASES", "SQL_QUERIES", "SQL_INDEX", "SQL_SCHEMA", "TECH_SCENARIOS", "REVIEWS", "LANG", "HANDWRITE"]:
        ids = [x.get("id") for x in acc[n]]
        if len(set(ids)) != len(ids): errors.append(f"{n} 里 id 重复：{sorted({i for i in ids if ids.count(i) > 1})}")
errors = []
files = sorted(glob.glob(os.path.join(D, "fs", "*.py")))
if "--only" in sys.argv:
    p = os.path.join(D, sys.argv[sys.argv.index("--only") + 1])
    acc = collect([p])
    validate(acc, errors, collect(files)["SQL_DATASETS"])
    print({n: len(v) for n, v in acc.items()})
    for w in warns: print("WARN", w)
    print("\n".join("ERROR " + e for e in errors) or "OK"); sys.exit(1 if errors else 0)
acc = collect(files)
validate(acc, errors)
print({n: len(v) for n, v in acc.items()})
for w in warns: print("WARN", w)
if errors: print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
o = lambda xs: sorted(xs, key=lambda x: x.get("order", 0))
json.dump({"cases": o(acc["CASES"]), "sql": {"datasets": acc["SQL_DATASETS"], "queries": o(acc["SQL_QUERIES"]), "index": o(acc["SQL_INDEX"]), "schema": o(acc["SQL_SCHEMA"])},
           "tech": {"cards": acc["TECH_CARDS"], "scenarios": o(acc["TECH_SCENARIOS"])}, "reviews": o(acc["REVIEWS"]), "lang": o(acc["LANG"]), "hand": o(acc["HANDWRITE"]), "today": H.SQL_TODAY},
          open(os.path.join(D, "fs.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> fs.json")
