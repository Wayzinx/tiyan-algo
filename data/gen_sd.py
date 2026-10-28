# 校验「设计编码」模块内容（积木题 + 设计题），生成 sd.json
# 用法：python3 gen_sd.py [--only sd/blocks_a.py]
import json, os, sys, glob, re, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
_fp = os.path.join(D, ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w and w != "字节"]
STEP_KEYS = ["clarify", "objects", "flow", "failure", "concurrency", "metrics"]
# 压力追问：每道设计题固定 10 问（顺序固定），参考答案按因果链：约束 → 失败模式 → 机制 → 代价 → 兜底 → 指标
PRESSURE_KEYS = ["core", "scale", "authority", "crash", "dup", "multi", "region", "tenx", "choice", "rollout"]
CHOICE_KEYS = ["topic", "constraint", "choice", "alternatives", "why_not", "downside", "metric"]
LAB_IDS = set()
for f in glob.glob(os.path.join(D, "labs", "*.py")):
    LAB_IDS |= set(re.findall(r'id="(lab-[a-z0-9-]+)"', open(f, encoding="utf-8").read()))
def load(p, name):
    spec = importlib.util.spec_from_file_location(os.path.basename(p)[:-3], p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, name, [])
def scan(obj, oid, errors):
    blob = json.dumps(obj, ensure_ascii=False)
    for w in FORBIDDEN:
        if w in blob: errors.append(f"{oid} 含有不该出现的内部词「{w}」")
def check_block(b, errors):
    bid = b.get("id", "?")
    for k in ["id", "order", "slug", "title", "essence", "triggers", "statement", "states", "invariants", "transitions", "failures", "walkthrough", "oral", "followups", "pitfalls", "complexity", "variants", "lab"]:
        if not b.get(k) and b.get(k) != 0: errors.append(f"{bid} 缺字段 {k}")
    if errors and errors[-1].startswith(bid + " 缺字段"): return
    if not re.fullmatch(r"p\d{1,2}", bid): errors.append(f"{bid} id 应该是 p1–p12")
    if len(b["states"]) != 2 or any(not (s.get("name") and s.get("desc")) for s in b["states"]): errors.append(f"{bid} states 需要正好 2 个核心状态 {{name, desc}}（其他状态放 extra_states）")
    if not (3 <= len(b["invariants"]) <= 6): errors.append(f"{bid} invariants 需要 3–6 条（第一条是最重要的）")
    if not (3 <= len(b["failures"]) <= 6) or any(not (x.get("case") and x.get("handle")) for x in b["failures"]): errors.append(f"{bid} failures 需要 3–6 个 {{case, handle}}")
    if not (3 <= len(b["triggers"]) <= 6): errors.append(f"{bid} triggers 需要 3–6 条")
    o = b["oral"]
    for k, lo in [("structure", 80), ("flow", 150), ("pitfalls", 150)]:
        if len(o.get(k, "")) < lo: errors.append(f"{bid} oral.{k} 太短（≥{lo} 字）")
    if not (3 <= len(b["followups"]) <= 6) or any(not (x.get("q") and x.get("a")) for x in b["followups"]): errors.append(f"{bid} followups 需要 3–6 个 {{q, a}}")
    if not (2 <= len(b["variants"]) <= 4) or any(not (x.get("context") and x.get("note")) for x in b["variants"]): errors.append(f"{bid} variants 需要 2–4 个 {{context, note}}")
    if len(b["statement"]) < 150: errors.append(f"{bid} statement 太短")
    if LAB_IDS and b["lab"] not in LAB_IDS: errors.append(f"{bid} lab {b['lab']} 不存在于 labs/*.py")
    scan(b, bid, errors)
def check_design(d, block_ids, errors):
    did = d.get("id", "?")
    for k in ["id", "order", "title", "statement", "composes", "opening", "steps", "followups", "pitfalls", "variants"]:
        if not d.get(k): errors.append(f"{did} 缺字段 {k}")
    if errors and errors[-1].startswith(did + " 缺字段"): return
    if [s.get("key") for s in d["steps"]] != STEP_KEYS: errors.append(f"{did} steps 必须按顺序是 {STEP_KEYS}")
    for s in d["steps"]:
        if not (s.get("title") and s.get("minutes") and s.get("prompt") and isinstance(s.get("points"), list) and 3 <= len(s["points"]) <= 7 and len(s.get("reference", "")) >= 150):
            errors.append(f"{did}/{s.get('key')} 需要 title / minutes / prompt / points(3–7) / reference(≥150 字)")
    for c in d["composes"]:
        if block_ids and c not in block_ids: errors.append(f"{did} composes 引用了不存在的积木 {c}")
    if not (4 <= len(d["followups"]) <= 7): errors.append(f"{did} followups 需要 4–7 个")
    if len(d["opening"]) < 80: errors.append(f"{did} opening 开口模板太短")
    scan(d, did, errors)
def check_extras(did, x, errors):
    if not isinstance(x, dict): errors.append(f"{did} extras 需要是 dict(pressure=…, metrics=…, choices=…)"); return
    pr = x.get("pressure") or []
    if [p.get("key") for p in pr] != PRESSURE_KEYS: errors.append(f"{did} pressure 必须正好 10 问，key 按顺序是 {PRESSURE_KEYS}")
    for p in pr:
        if not p.get("q") or not (150 <= len(p.get("a", "")) <= 700): errors.append(f"{did}/pressure/{p.get('key')} 需要 q，且 a 为 150–700 字")
    ms = x.get("metrics") or []
    if not (2 <= len(ms) <= 3): errors.append(f"{did} metrics 需要 2–3 个指标口径练习")
    for m in ms:
        if not all(m.get(k) for k in ["name", "ask", "numerator", "denominator", "exclude", "traps", "answer"]) or not (2 <= len(m["traps"]) <= 4) or len(m["answer"]) < 100:
            errors.append(f"{did}/metrics/{m.get('name')} 需要 name / ask / numerator / denominator / exclude / traps(2–4) / answer(≥100 字)")
    cs = x.get("choices") or []
    if len(cs) != 2: errors.append(f"{did} choices 需要正好 2 个技术选型")
    for c in cs:
        if not all(len(str(c.get(k, ""))) >= (4 if k == "topic" else 15) for k in CHOICE_KEYS): errors.append(f"{did}/choices/{c.get('topic')} 需要 {CHOICE_KEYS}（topic 之外每项 ≥15 字）")
    scan(x, did + "/extras", errors)
def all_block_ids():
    ids = set()
    for f in glob.glob(os.path.join(D, "sd", "*.py")): ids |= {b["id"] for b in load(f, "BLOCKS")}
    return ids
EXTRA_FIELDS = ["pressure", "metrics", "choices"]
# 系统设计实战：给需求，设计服务 / 表 / 接口 / 状态机 / 流程；参考 DDL 必须真能建表
SYS_KEYS = ["clarify", "estimate", "services", "tables", "api", "states", "flows", "reliability"]
SYS_DIAGRAM = {"services": ("flowchart", "graph"), "states": ("stateDiagram",), "flows": ("sequenceDiagram",)}
VERDICTS = ["对", "方向对但不准", "有错", "搞反", "缺失", "最大扣分点"]
def _harness():
    spec = importlib.util.spec_from_file_location("harness", os.path.join(D, "harness.py")); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def check_system(x, errors):
    xid = x.get("id", "?")
    for k in ["id", "order", "title", "brief", "statement", "focus", "scale", "example", "minutes", "sections", "mistakes", "walkthrough", "oral", "followups", "variants"]:
        if not x.get(k): errors.append(f"{xid} 缺字段 {k}")
    if errors and errors[-1].startswith(xid + " 缺字段"): return
    if not re.fullmatch(r"x\d{1,2}", xid): errors.append(f"{xid} id 应该是 x1、x2……")
    for k, lo in [("statement", 200), ("focus", 20), ("scale", 40), ("example", 60), ("walkthrough", 200), ("oral", 300)]:
        if len(x[k]) < lo: errors.append(f"{xid} {k} 太短（≥{lo} 字）")
    if not (35 <= int(x["minutes"]) <= 60): errors.append(f"{xid} minutes 应在 35–60")
    secs = x["sections"]
    if [c.get("key") for c in secs] != SYS_KEYS: errors.append(f"{xid} sections 必须按顺序是 {SYS_KEYS}")
    for c in secs:
        k = c.get("key")
        if not (c.get("title") and c.get("minutes") and c.get("prompt") and isinstance(c.get("points"), list) and 3 <= len(c["points"]) <= 8 and len(c.get("reference", "")) >= 300):
            errors.append(f"{xid}/{k} 需要 title / minutes / prompt / points(3–8) / reference(≥300 字)")
        if k in SYS_DIAGRAM and not str(c.get("diagram", "")).lstrip().startswith(SYS_DIAGRAM[k]): errors.append(f"{xid}/{k} 需要 diagram（Mermaid，以 {SYS_DIAGRAM[k]} 开头）")
        if k == "tables":
            ddl = c.get("ddl", "")
            if ddl.upper().count("CREATE TABLE") < 4: errors.append(f"{xid}/tables 的 ddl 至少 4 张表")
            else:
                r = json.loads(_harness().check_ddl(ddl))
                if not r["ok"]: errors.append(f"{xid}/tables 的 ddl 建表失败：{r['error']}\n转换后的语句：\n{r['converted'][:1500]}")
                elif any(not any(i["unique"] or i["origin"] == "pk" for i in t["indexes"]) and not any(c2["pk"] for c2 in t["cols"]) for t in r["tables"]): errors.append(f"{xid}/tables 每张表都要有主键")
    if sum(int(c.get("minutes") or 0) for c in secs) != int(x["minutes"]): errors.append(f"{xid} 各环节 minutes 之和应等于 minutes")
    if not (4 <= len(x["mistakes"]) <= 8) or any(not (m.get("wrong") and m.get("verdict") in VERDICTS and len(m.get("why", "")) >= 30) for m in x["mistakes"]):
        errors.append(f"{xid} mistakes 需要 4–8 个 {{wrong, verdict∈{VERDICTS}, why(≥30 字)}}")
    if not (6 <= len(x["followups"]) <= 10) or any(not (f.get("q") and len(f.get("a", "")) >= 80) for f in x["followups"]): errors.append(f"{xid} followups 需要 6–10 个 {{q, a(≥80 字)}}")
    if not (2 <= len(x["variants"]) <= 5): errors.append(f"{xid} variants 需要 2–5 个")
    scan(x, xid, errors)
errors = []
if "--only" in sys.argv:
    p = os.path.join(D, sys.argv[sys.argv.index("--only") + 1])
    blocks, designs, extras = load(p, "BLOCKS"), load(p, "DESIGNS"), load(p, "EXTRAS") or {}
    systems = load(p, "SYSTEMS")
    for x in systems: check_system(x, errors)
    if systems: print("系统设计题", [x.get("id") for x in systems])
    for b in blocks: check_block(b, errors)
    bids = all_block_ids()
    for d in designs: check_design(d, bids, errors)
    for d in designs:
        x = extras.get(d["id"]) or {k: d[k] for k in EXTRA_FIELDS if k in d}
        check_extras(d["id"], x, errors)
    for did, x in extras.items():
        if not any(d["id"] == did for d in designs): check_extras(did, x, errors)
    print(f"积木题 {len(blocks)}，设计题 {len(designs)}，压力追问 {len(extras) + sum(1 for d in designs if 'pressure' in d and d['id'] not in extras)}"); print("\n".join("ERROR " + e for e in errors) or "OK"); sys.exit(1 if errors else 0)
blocks, designs, extras, systems = [], [], {}, []
for f in sorted(glob.glob(os.path.join(D, "sd", "*.py"))):
    blocks += load(f, "BLOCKS"); designs += load(f, "DESIGNS"); extras.update(load(f, "EXTRAS") or {}); systems += load(f, "SYSTEMS")
toolbox = {}
for f in sorted(glob.glob(os.path.join(D, "sd", "*.py"))):
    toolbox.update(load(f, "TOOLBOX") or {})
ids = [b["id"] for b in blocks]
if len(set(ids)) != len(ids): errors.append("积木题 id 重复")
for b in blocks: check_block(b, errors)
for d in designs: check_design(d, set(ids), errors)
missing = []
for d in designs:
    d.update(extras.get(d["id"], {}))
    if all(k in d for k in EXTRA_FIELDS): check_extras(d["id"], {k: d[k] for k in EXTRA_FIELDS}, errors)
    else: missing.append(d["id"])
if missing: print("WARN 还没有压力追问 / 指标口径 / 技术选型：", missing)
if toolbox: scan(toolbox, "toolbox", errors)
for x in systems: check_system(x, errors)
if len({x["id"] for x in systems}) != len(systems): errors.append("系统设计题 id 重复")
print("积木题:", sorted(ids, key=lambda x: int(x[1:])), "设计题:", [d["id"] for d in designs], "系统设计题:", [x.get("id") for x in systems])
if errors: print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
json.dump({"blocks": sorted(blocks, key=lambda b: b["order"]), "designs": sorted(designs, key=lambda d: d["order"]), "toolbox": toolbox, "systems": sorted(systems, key=lambda x: x["order"])}, open(os.path.join(D, "sd.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> sd.json")
