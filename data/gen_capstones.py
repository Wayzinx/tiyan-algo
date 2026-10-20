# 校验「项目实战」：参考实现必须通过全部测试；骨架代码的每个里程碑测试都必须失败；生成 capstones.json 和骨架 zip
# 用法：<装了 fastapi/httpx/pydantic/pyyaml/pytest 的 python3.12> gen_capstones.py [--only agent-service]
import json, os, sys, subprocess, filecmp, zipfile, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(os.path.dirname(D), "public", "capstones")
REQ_M = ["id", "title", "goal", "why", "tasks", "deliverables", "acceptance", "test_file", "hints", "interview", "resume"]
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
errors, out = [], []
def pytest(cwd, target):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", target], cwd=cwd, capture_output=True, text=True, timeout=600)
    return r.returncode, (r.stdout + r.stderr)[-1500:]
for cid in sorted(os.listdir(os.path.join(D, "capstones"))):
    if only and cid != only: continue
    base = os.path.join(D, "capstones", cid)
    if not os.path.isdir(base): continue
    spec = importlib.util.spec_from_file_location("meta", os.path.join(base, "meta.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cap = m.CAPSTONE
    for k in ["id", "role", "title", "summary", "why", "stack", "setup", "milestones", "final"]:
        if not cap.get(k): errors.append(f"{cid} 缺字段 {k}")
    sk, ref = os.path.join(base, "skeleton"), os.path.join(base, "reference")
    if not (os.path.isdir(sk) and os.path.isdir(ref)): errors.append(f"{cid} 需要 skeleton/ 和 reference/ 两个目录"); continue
    cmp = filecmp.dircmp(os.path.join(sk, "tests"), os.path.join(ref, "tests"))
    if cmp.left_only or cmp.right_only or cmp.diff_files: errors.append(f"{cid} skeleton/tests 和 reference/tests 必须完全一致：{cmp.left_only + cmp.right_only + cmp.diff_files}")
    code, log = pytest(ref, "tests")
    if code != 0: errors.append(f"{cid} 参考实现没有通过全部测试：\n{log}")
    ms = cap.get("milestones", [])
    if not (6 <= len(ms) <= 10): errors.append(f"{cid} 里程碑需要 6–10 个")
    for mm in ms:
        miss = [k for k in REQ_M if not mm.get(k)]
        if miss: errors.append(f"{cid}/{mm.get('id')} 缺字段 {miss}"); continue
        tf = os.path.join(sk, mm["test_file"])
        if not os.path.exists(tf): errors.append(f"{cid}/{mm['id']} 测试文件不存在：{mm['test_file']}"); continue
        c2, log2 = pytest(sk, mm["test_file"])
        if c2 == 0: errors.append(f"{cid}/{mm['id']} 骨架代码直接通过了 {mm['test_file']}，骨架应该只有空实现")
        if len(mm["acceptance"]) < 4: errors.append(f"{cid}/{mm['id']} 验收标准至少 4 条")
        if len(mm["hints"]) != 3: errors.append(f"{cid}/{mm['id']} hints 需要 3 条")
    os.makedirs(PUB, exist_ok=True)
    zp = os.path.join(PUB, cid + ".zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(sk):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".pytest_cache", ".venv")]
            for f in files:
                if f.endswith(".pyc"): continue
                full = os.path.join(root, f)
                z.write(full, os.path.join(cid, os.path.relpath(full, sk)))
    cap["zip"] = "capstones/" + cid + ".zip"
    cap["files"] = sorted(os.path.relpath(os.path.join(r, f), sk) for r, ds, fs in os.walk(sk) for f in fs if "__pycache__" not in r and not f.endswith(".pyc"))
    out.append(cap)
print("项目:", [(c["id"], len(c["milestones"])) for c in out])
if errors:
    print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
if not only:
    json.dump(out, open(os.path.join(D, "capstones.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("OK")
