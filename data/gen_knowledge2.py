# 校验「AI 知识」第二版（深度版）内容并生成 knowledge.json
# 用法：python3 gen_knowledge2.py            → 校验 data/k2/*.py 全部并生成
#       python3 gen_knowledge2.py --only k2/c1.py  → 只校验一个文件（不生成）
import json, re, sys, os, glob, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
COURSES = [
    ("llm", "大模型原理", "从 token 到对齐与推理部署：原理讲透，再讲工程和落地。"),
    ("agent", "Agent 原理", "Agent 的核心机制：推理、工具、上下文、记忆、RAG、协议、多 Agent、评测与安全。"),
    ("harness", "Harness 工程", "包在模型外面、让 Agent 稳定运行的那一层：循环、工具、上下文、权限、扩展、成本。"),
    ("dev", "AI 应用开发实战", "用 Python 把 LLM 应用和 Agent 做出来、测起来、上线运维。"),
    ("arch", "Agent 系统架构与生产落地", "生产级 Agent 系统怎么设计、怎么扛住线上：架构、编排、护栏、路由、观测和案例。"),
]
_fp = os.path.join(D, ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w and w != "字节"]
HEADINGS = ["### 一句话与核心概念", "### 原理", "### 工程实现", "### 生产落地", "### 取舍与对比", "### 结合项目怎么讲"]
LEVELS = {"基础", "原理", "实现", "落地", "排查", "取舍", "设计"}
LAB_IDS = set()
for f in glob.glob(os.path.join(D, "labs", "*.py")):
    for m in re.finditer(r'id="(lab-[a-z0-9-]+)"', open(f, encoding="utf-8").read()):
        LAB_IDS.add(m.group(1))
LAB_IDS |= set(re.findall(r"lab-[a-z0-9-]+", open(os.path.join(D, "lab_ids.txt"), encoding="utf-8").read())) if os.path.exists(os.path.join(D, "lab_ids.txt")) else set()

def load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.SECTIONS

def check(sections, errors, ids):
    for s in sections:
        sid = s.get("id", "?")
        for k in ["id", "course", "order", "title", "summary", "md", "points", "drill", "choice", "short"]:
            if k not in s or s[k] in (None, "", []): errors.append(f"{sid} 缺字段 {k}")
        if errors and errors[-1].startswith(sid + " 缺字段"): continue
        if sid in ids: errors.append(f"{sid} id 重复")
        ids.add(sid)
        if s["course"] not in [c[0] for c in COURSES]: errors.append(f"{sid} course 不合法")
        n = len(s["md"])
        if n < 3000: errors.append(f"{sid} 正文太短（{n} 字，要求 3000–6500）")
        if n > 6500: errors.append(f"{sid} 正文太长（{n} 字）")
        for hd in HEADINGS:
            if hd not in s["md"]: errors.append(f"{sid} 正文缺小标题「{hd}…」")
        if re.search(r"^#{1,2} ", s["md"], re.M): errors.append(f"{sid} 正文里不要用 # 或 ## 标题")
        if s["md"].count("```") % 2: errors.append(f"{sid} 代码块没闭合")
        if len(s["summary"]) > 60: errors.append(f"{sid} summary 超过 60 字")
        if not (3 <= len(s["points"]) <= 6): errors.append(f"{sid} points 需要 3–6 条")
        if not (6 <= len(s["drill"]) <= 8): errors.append(f"{sid} drill 需要 6–8 条")
        for d in s["drill"]:
            if not (d.get("q") and d.get("a") and d.get("level") in LEVELS): errors.append(f"{sid} drill 项需要 level/q/a，level 取 {sorted(LEVELS)}"); break
            if len(d["a"]) < 80: errors.append(f"{sid} drill 回答太短：{d['q'][:20]}"); break
        if len(s["choice"]) != 4: errors.append(f"{sid} choice 需要正好 4 道")
        multi = 0
        for c in s["choice"]:
            ok = c.get("q") and isinstance(c.get("options"), list) and 3 <= len(c["options"]) <= 5 and isinstance(c.get("answer"), list) and c["answer"] and all(isinstance(i, int) and 0 <= i < len(c["options"]) for i in c["answer"]) and c.get("explain")
            if not ok: errors.append(f"{sid} choice 格式不对：{str(c.get('q'))[:30]}"); break
            multi += len(c["answer"]) > 1
        if s["choice"] and multi < 1: errors.append(f"{sid} choice 里至少要有 1 道多选题")
        if len(s["short"]) != 3: errors.append(f"{sid} short 需要正好 3 道")
        for x in s["short"]:
            if not (x.get("q") and isinstance(x.get("points"), list) and 3 <= len(x["points"]) <= 5 and len(x.get("reference", "")) >= 150): errors.append(f"{sid} short 格式不对（points 3–5 个，reference ≥150 字）：{str(x.get('q'))[:30]}"); break
        for lab in s.get("labs", []):
            if LAB_IDS and lab not in LAB_IDS: errors.append(f"{sid} labs 引用了不存在的 {lab}")
        blob = json.dumps(s, ensure_ascii=False)
        for w in FORBIDDEN:
            if w in blob: errors.append(f"{sid} 含有不该出现的内部词「{w}」")

errors, ids = [], set()
if "--only" in sys.argv:
    path = sys.argv[sys.argv.index("--only") + 1]
    secs = load(os.path.join(D, path) if not os.path.isabs(path) else path)
    check(secs, errors, ids)
    print(f"{path}: {len(secs)} 节", [(s.get('id'), len(s.get('md', ''))) for s in secs])
    print("\n".join("ERROR " + e for e in errors) or "OK")
    sys.exit(1 if errors else 0)
allsecs = []
for f in sorted(glob.glob(os.path.join(D, "k2", "*.py"))):
    allsecs += load(f)
check(allsecs, errors, ids)
all_ids = {s["id"] for s in allsecs}
for s in allsecs:
    for r in s.get("related", []):
        if r not in all_ids: errors.append(f"{s['id']} related 引用了不存在的 {r}")
out = []
for cid, name, blurb in COURSES:
    secs = sorted([s for s in allsecs if s.get("course") == cid], key=lambda s: s.get("order", 99))
    if secs: out.append({"id": cid, "name": name, "blurb": blurb, "sections": secs})
print("课程:", [(c["id"], len(c["sections"])) for c in out], "共", sum(len(c["sections"]) for c in out), "节")
if errors:
    print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
json.dump(out, open(os.path.join(D, "knowledge.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> knowledge.json", sum(len(json.dumps(c, ensure_ascii=False)) for c in out), "chars")
