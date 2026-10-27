# 校验「设计编码」模块内容（积木题 + 设计题），生成 sd.json
# 用法：python3 gen_sd.py [--only sd/blocks_a.py]
import json, os, sys, glob, re, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
_fp = os.path.join(D, ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w and w != "字节"]
STEP_KEYS = ["clarify", "objects", "flow", "failure", "concurrency", "metrics"]
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
errors = []
if "--only" in sys.argv:
    p = os.path.join(D, sys.argv[sys.argv.index("--only") + 1])
    blocks, designs = load(p, "BLOCKS"), load(p, "DESIGNS")
    for b in blocks: check_block(b, errors)
    for d in designs: check_design(d, None, errors)
    print(f"积木题 {len(blocks)}，设计题 {len(designs)}"); print("\n".join("ERROR " + e for e in errors) or "OK"); sys.exit(1 if errors else 0)
blocks, designs = [], []
for f in sorted(glob.glob(os.path.join(D, "sd", "*.py"))):
    blocks += load(f, "BLOCKS"); designs += load(f, "DESIGNS")
ids = [b["id"] for b in blocks]
if len(set(ids)) != len(ids): errors.append("积木题 id 重复")
for b in blocks: check_block(b, errors)
for d in designs: check_design(d, set(ids), errors)
print("积木题:", sorted(ids, key=lambda x: int(x[1:])), "设计题:", [d["id"] for d in designs])
if errors: print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
json.dump({"blocks": sorted(blocks, key=lambda b: b["order"]), "designs": sorted(designs, key=lambda d: d["order"])}, open(os.path.join(D, "sd.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> sd.json")
