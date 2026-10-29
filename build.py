# 生成 public/index.html：把题库、判题 harness、样式和前端脚本拼进一个页面
# 改题库：编辑 data/problems.py → python3 data/gen.py（在 data 目录下）→ python3 build.py
import json, os
D = os.path.dirname(os.path.abspath(__file__))
r = lambda p: open(os.path.join(D, p), encoding="utf-8").read()
problems = json.load(open(os.path.join(D, "data/problems.json"), encoding="utf-8"))
pj = json.dumps(problems, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
harness = r("data/harness.py") + "\n\nbuild_list, build_tree, list_values, tree_values = _to_list, _to_tree, _from_list, _from_tree\nsys.setrecursionlimit(4000)\n"
def data(name, empty):
    p = os.path.join(D, "data", name)
    if not os.path.exists(p): return empty
    return json.dumps(json.load(open(p, encoding="utf-8")), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
knowledge, python, labs, caps, sd = data("knowledge.json", "[]"), data("python.json", '{"groups":[],"sections":[]}'), data("labs.json", "[]"), data("capstones.json", "[]"), data("sd.json", '{"blocks":[],"designs":[]}')
js = "\n".join(r("src/" + f) for f in ["patterns.js", "core.js", "chat.js", "views.js", "ws.js", "kb.js", "mock.js", "practice.js", "labs.js", "data.js", "capstone.js", "sd.js", "buddy.js", "boot.js"])
assert "</script" not in js.lower() and "</script" not in harness
out = (r("src/shell.html").replace("/*CM_CSS*/", r("src/cm.css")).replace("/*APP_CSS*/", r("src/style.css"))
       .replace("/*PROBLEMS*/", pj).replace("/*KNOWLEDGE*/", knowledge).replace("/*PYTHON*/", python).replace("/*LABS*/", labs).replace("/*CAPSTONES*/", caps).replace("/*SD*/", sd).replace("/*HARNESS*/", harness).replace("/*APP_JS*/", js))
open(os.path.join(D, "public/index.html"), "w", encoding="utf-8").write(out)
import hashlib
build = hashlib.sha1(out.encode()).hexdigest()[:10]
open(os.path.join(D, "public/sw.js"), "w", encoding="utf-8").write(r("src/sw.js").replace("__BUILD__", build))
open(os.path.join(D, ".app-check.js"), "w", encoding="utf-8").write(js)
print("public/index.html", len(out.encode()), "bytes")
