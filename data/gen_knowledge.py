# 校验「AI 知识」课程内容并生成 knowledge.json
# 用法：python3 gen_knowledge.py   （读取 knowledge_llm_agent.py 和 knowledge_harness_dev.py）
import json, re, sys, importlib
import os
# 不允许出现在公开内容里的词（公司内部名称等）；清单只放在本机的 .forbidden.txt，不提交
_fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w]
REQ = ["id", "title", "summary", "md", "points", "interview", "quiz"]
courses, errors, ids = [], [], set()
for mod in ["knowledge_llm_agent", "knowledge_harness_dev"]:
    try:
        m = importlib.import_module(mod)
    except ModuleNotFoundError:
        print("跳过（还没写）:", mod); continue
    courses.extend(m.COURSES)
all_ids = {s["id"] for c in courses for s in c.get("sections", [])}
for c in courses:
    for k in ["id", "name", "blurb", "sections"]:
        if k not in c: errors.append(f"课程缺字段 {k}: {c.get('id')}")
    for s in c.get("sections", []):
        sid = s.get("id", "?")
        miss = [k for k in REQ if not s.get(k)]
        if miss: errors.append(f"{sid} 缺字段 {miss}"); continue
        if sid in ids: errors.append(f"{sid} id 重复")
        ids.add(sid)
        if not re.fullmatch(r"[a-z0-9-]+", sid): errors.append(f"{sid} id 只能用小写字母数字和 -")
        n = len(s["md"])
        if n < 700: errors.append(f"{sid} 正文太短（{n} 字）")
        if n > 3800: errors.append(f"{sid} 正文太长（{n} 字），拆小节或精简")
        if len(s["summary"]) > 60: errors.append(f"{sid} summary 超过 60 字")
        if not (3 <= len(s["points"]) <= 6): errors.append(f"{sid} points 需要 3–6 条")
        if not (2 <= len(s["interview"]) <= 4) or any(not (x.get("q") and x.get("a")) for x in s["interview"]): errors.append(f"{sid} interview 需要 2–4 个 {{q, a}}")
        if not (2 <= len(s["quiz"]) <= 4) or any(not (x.get("q") and x.get("a")) for x in s["quiz"]): errors.append(f"{sid} quiz 需要 2–4 个 {{q, a}}")
        for r in s.get("related", []):
            if r not in all_ids: errors.append(f"{sid} related 引用了不存在的 {r}")
        blob = json.dumps(s, ensure_ascii=False)
        for w in FORBIDDEN:
            if w in blob: errors.append(f"{sid} 含有不该出现的内部词「{w}」")
        if "```" in s["md"] and s["md"].count("```") % 2: errors.append(f"{sid} 代码块没闭合")
print("课程:", [(c["id"], len(c["sections"])) for c in courses], "共", sum(len(c["sections"]) for c in courses), "节")
if errors:
    print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
json.dump(courses, open("knowledge.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> knowledge.json", sum(len(json.dumps(c, ensure_ascii=False)) for c in courses), "chars")
