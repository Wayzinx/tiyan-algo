# 校验「Python 刷题语法」内容：真实运行每个示例（Python 3.12），把输出写进 python.json
# 用法：~/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 gen_python.py
import json, re, sys, subprocess
from python_features import GROUPS, SECTIONS
REQ = ["id", "group", "title", "summary", "md", "examples", "algo", "pitfalls"]
errors, ids = [], set()
for s in SECTIONS:
    sid = s.get("id", "?")
    miss = [k for k in REQ if not s.get(k)]
    if miss: errors.append(f"{sid} 缺字段 {miss}"); continue
    if sid in ids: errors.append(f"{sid} id 重复")
    ids.add(sid)
    if s["group"] not in GROUPS: errors.append(f"{sid} group 不在 GROUPS 里")
    if not (1 <= len(s["examples"]) <= 5): errors.append(f"{sid} examples 需要 1–5 个")
    if len(s["md"]) > 2600: errors.append(f"{sid} 正文太长（{len(s['md'])} 字）")
    for i, ex in enumerate(s["examples"]):
        if not ex.get("title") or not ex.get("code"): errors.append(f"{sid} 示例 {i} 缺 title/code"); continue
        try:
            r = subprocess.run([sys.executable, "-c", ex["code"]], input=ex.get("stdin", ""), capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            errors.append(f"{sid} 示例「{ex['title']}」超时"); continue
        if r.returncode != 0 and not ex.get("expect_error"):
            errors.append(f"{sid} 示例「{ex['title']}」报错：{r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
        out = r.stdout if r.returncode == 0 else (r.stdout + r.stderr.strip().splitlines()[-1] + "\n")
        if not out.strip(): errors.append(f"{sid} 示例「{ex['title']}」没有输出（用 print 打印结果）")
        if len(out) > 1500: errors.append(f"{sid} 示例「{ex['title']}」输出太长")
        ex["output"] = out
print("小节:", len(SECTIONS), "分组:", {g: sum(1 for s in SECTIONS if s.get("group") == g) for g in GROUPS})
if errors:
    print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
json.dump({"groups": GROUPS, "sections": SECTIONS}, open("python.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("OK -> python.json", len(json.dumps(SECTIONS, ensure_ascii=False)), "chars")
