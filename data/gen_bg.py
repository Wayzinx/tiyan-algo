# 校验「八股」模块内容（data/bg/*.py 里的 CHAPTER），生成 bg.json
# 用法：python3 gen_bg.py            校验全部并写 bg.json
#       python3 gen_bg.py --check bg/redis.py   只校验这一个文件，不写 bg.json
import json, os, sys, glob, re, importlib.util
D = os.path.dirname(os.path.abspath(__file__))
_fp = os.path.join(D, ".forbidden.txt")
FORBIDDEN = [w.strip() for w in open(_fp, encoding="utf-8")] if os.path.exists(_fp) else []
FORBIDDEN = [w for w in FORBIDDEN if w and w != "字节"]
# 公开仓库：具体公司 / 产品名也放在不入库的 .forbidden.txt 里
CARD_KEYS = ["id", "q", "level", "short", "points", "explain", "followups", "pitfalls", "hook"]


def load(p):
    spec = importlib.util.spec_from_file_location("bg_" + os.path.basename(p)[:-3], p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, "CHAPTER", None)


def check_card(c, chap, errors):
    cid = c.get("id", "?")
    miss = [k for k in CARD_KEYS if not c.get(k)]
    if miss: errors.append(f"{cid} 缺字段 {miss}"); return
    if not re.fullmatch(rf"{chap}-[a-z0-9]+(-[a-z0-9]+)*", cid): errors.append(f"{cid} id 要以「{chap}-」开头，只用小写字母数字和短横线")
    if c["level"] not in (1, 2, 3): errors.append(f"{cid} level 只能是 1（必会）/ 2（常问）/ 3（进阶）")
    if not (8 <= len(c["q"]) <= 60): errors.append(f"{cid} q 是面试官的原话问法，8–60 字（现在 {len(c['q'])}）")
    if not (50 <= len(c["short"]) <= 260): errors.append(f"{cid} short 是 30 秒能说完的版本，50–260 字（现在 {len(c['short'])}）")
    if not (3 <= len(c["points"]) <= 6) or any(not isinstance(p, str) or not (6 <= len(p) <= 80) for p in c["points"]):
        errors.append(f"{cid} points 需要 3–6 个得分点，每个 6–80 字")
    ex = c["explain"]
    if not (700 <= len(ex) <= 3800): errors.append(f"{cid} explain 700–3800 字（现在 {len(ex)}）")
    prose = re.sub(r"```.*?```", "", ex, flags=re.S)   # 代码块里的 # 注释不算标题
    if len(re.findall(r"^### ", prose, re.M)) < 2: errors.append(f"{cid} explain 至少 2 个 ### 小标题")
    if re.search(r"^#{1,2} ", prose, re.M): errors.append(f"{cid} explain 里不要用 # / ## 大标题，只用 ###")
    if ex.count("```") % 2: errors.append(f"{cid} explain 代码块 ``` 没有成对")
    fu = c["followups"]
    if not (2 <= len(fu) <= 5) or any(not (isinstance(x, dict) and x.get("q") and x.get("a") and len(x["a"]) >= 30) for x in fu):
        errors.append(f"{cid} followups 需要 2–5 个 {{q, a}}，a 至少 30 字")
    if not (1 <= len(c["pitfalls"]) <= 4) or any(not isinstance(x, str) or len(x) < 8 for x in c["pitfalls"]):
        errors.append(f"{cid} pitfalls 需要 1–4 条，每条至少 8 字")
    if len(c["hook"]) < 40: errors.append(f"{cid} hook（测开 / 项目视角）至少 40 字")
    if "alt" in c and (not isinstance(c["alt"], list) or any(not isinstance(x, str) for x in c["alt"])): errors.append(f"{cid} alt 应该是字符串列表")
    if "mnemonic" in c and not isinstance(c["mnemonic"], str): errors.append(f"{cid} mnemonic 应该是字符串")
    extra = set(c) - set(CARD_KEYS) - {"alt", "mnemonic"}
    if extra: errors.append(f"{cid} 有未知字段 {sorted(extra)}")


def check_chapter(ch, path, errors):
    if not isinstance(ch, dict): errors.append(f"{path} 没有 CHAPTER 字典"); return
    cid = ch.get("id", "?")
    for k in ["id", "order", "name", "blurb", "map", "cards"]:
        if not ch.get(k) and ch.get(k) != 0: errors.append(f"{path} 缺字段 {k}")
    if errors and errors[-1].startswith(path + " 缺字段"): return
    if os.path.basename(path)[:-3] != cid: errors.append(f"{path} 文件名应该是 {cid}.py")
    if not (8 <= len(ch["blurb"]) <= 40): errors.append(f"{cid} blurb 8–40 字")
    if not (300 <= len(ch["map"]) <= 2600): errors.append(f"{cid} map（知识地图）300–2600 字")
    cards = ch["cards"]
    if not (8 <= len(cards) <= 16): errors.append(f"{cid} cards 需要 8–16 张（现在 {len(cards)}）")
    if sum(1 for c in cards if c.get("level") == 1) < 4: errors.append(f"{cid} 至少 4 张 level=1（摸底必问）")
    for c in cards: check_card(c, cid, errors)
    blob = json.dumps(ch, ensure_ascii=False)
    for w in FORBIDDEN:
        if w in blob: errors.append(f"{cid} 含有不该出现的词「{w}」")


PROFILE_KEYS = ["id", "order", "name", "cat", "one", "say", "points", "features", "pros", "cons", "use", "skip", "decide", "vs", "test", "issues", "followups"]


def _objs(v, keys, lo, hi, tag, errors, minlen=None):
    """v 是 lo–hi 个字典的列表，每个都有 keys 里的非空字符串字段；minlen 给出字段最短长度。"""
    if not isinstance(v, list) or not (lo <= len(v) <= hi):
        errors.append(f"{tag} 需要 {lo}–{hi} 项（现在 {len(v) if isinstance(v, list) else '不是列表'}）"); return
    for i, x in enumerate(v):
        if not isinstance(x, dict) or any(not isinstance(x.get(k), str) or not x.get(k).strip() for k in keys):
            errors.append(f"{tag}[{i}] 需要字段 {keys}"); continue
        for k, n in (minlen or {}).items():
            if len(x[k]) < n: errors.append(f"{tag}[{i}].{k} 至少 {n} 字")
        if set(x) - set(keys): errors.append(f"{tag}[{i}] 有未知字段 {sorted(set(x) - set(keys))}")


def check_profile(pf, path, chapter_ids, errors):
    pid = pf.get("id", "?") if isinstance(pf, dict) else "?"
    tag = f"comp/{pid}"
    if not isinstance(pf, dict): errors.append(f"{path} 没有 PROFILE 字典"); return
    miss = [k for k in PROFILE_KEYS if not pf.get(k) and pf.get(k) != 0]
    if miss: errors.append(f"{tag} 缺字段 {miss}"); return
    if set(pf) - set(PROFILE_KEYS) - {"chapter"}: errors.append(f"{tag} 有未知字段 {sorted(set(pf) - set(PROFILE_KEYS) - {'chapter'})}")
    if os.path.basename(path)[:-3] != pid: errors.append(f"{path} 文件名应该是 {pid}.py")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", pid): errors.append(f"{tag} id 只用小写字母数字和短横线")
    if pf.get("chapter") and pf["chapter"] not in chapter_ids: errors.append(f"{tag} chapter={pf['chapter']} 不是已有章节")
    if not (15 <= len(pf["one"]) <= 90): errors.append(f"{tag} one（一句话定位）15–90 字")
    if not (120 <= len(pf["say"]) <= 420): errors.append(f"{tag} say（30 秒版）120–420 字（现在 {len(pf['say'])}）")
    if not (3 <= len(pf["points"]) <= 6) or any(not isinstance(x, str) or not (6 <= len(x) <= 80) for x in pf["points"]): errors.append(f"{tag} points 3–6 个，每个 6–80 字")
    _objs(pf["features"], ["name", "desc"], 4, 8, tag + " features", errors, {"desc": 20})
    _objs(pf["pros"], ["point", "why"], 3, 6, tag + " pros", errors, {"why": 20})
    _objs(pf["cons"], ["point", "impact"], 3, 6, tag + " cons", errors, {"impact": 20})
    _objs(pf["use"], ["scene", "why"], 3, 7, tag + " use", errors, {"why": 15})
    _objs(pf["skip"], ["scene", "alt", "why"], 3, 6, tag + " skip", errors, {"why": 15})
    if not (3 <= len(pf["decide"]) <= 7) or any(not isinstance(x, str) or len(x) < 15 for x in pf["decide"]): errors.append(f"{tag} decide 3–7 条，每条至少 15 字")
    _objs(pf["vs"], ["other", "diff"], 2, 4, tag + " vs", errors, {"diff": 30})
    t = pf["test"]
    if not isinstance(t, list) or not (4 <= len(t) <= 7) or any(not isinstance(g, dict) or not g.get("area") or not isinstance(g.get("items"), list) or not (2 <= len(g["items"]) <= 6) for g in t):
        errors.append(f"{tag} test 需要 4–7 组 {{area, items: 2–6 条}}")
    _objs(pf["issues"], ["symptom", "cause", "check"], 3, 6, tag + " issues", errors, {"check": 10})
    _objs(pf["followups"], ["q", "a"], 2, 5, tag + " followups", errors, {"a": 30})
    blob = json.dumps(pf, ensure_ascii=False)
    for w in FORBIDDEN:
        if w in blob: errors.append(f"{tag} 含有不该出现的词「{w}」")


def profile_md(pf):
    """把画像拼成 Markdown：给站内检索和 AI 老师读。"""
    L = [f"### {pf['name']}：{pf['one']}", "", "**30 秒版**：" + pf["say"], "", "### 核心特性"]
    L += [f"- **{x['name']}**：{x['desc']}" for x in pf["features"]]
    L += ["", "### 优点"] + [f"- **{x['point']}**：{x['why']}" for x in pf["pros"]]
    L += ["", "### 缺点"] + [f"- **{x['point']}**：{x['impact']}" for x in pf["cons"]]
    L += ["", "### 什么时候用"] + [f"- **{x['scene']}**：{x['why']}" for x in pf["use"]]
    L += ["", "### 什么时候不用"] + [f"- **{x['scene']}** → {x['alt']}：{x['why']}" for x in pf["skip"]]
    L += ["", "### 选型前先问"] + [f"- {x}" for x in pf["decide"]]
    L += ["", "### 对比"] + [f"- **vs {x['other']}**：{x['diff']}" for x in pf["vs"]]
    L += ["", "### 测试要点"] + [f"- **{g['area']}**：" + "；".join(g["items"]) for g in pf["test"]]
    L += ["", "### 常见线上问题"] + [f"- {x['symptom']} ← {x['cause']}（排查：{x['check']}）" for x in pf["issues"]]
    return "\n".join(L)


def comp_chapter(chapter_ids, errors):
    files = sorted(glob.glob(os.path.join(D, "comp", "*.py")))
    if not files: return None
    profiles, seen = [], set()
    for f in files:
        try:
            spec = importlib.util.spec_from_file_location("comp_" + os.path.basename(f)[:-3], f)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            pf = getattr(m, "PROFILE", None)
        except Exception as e:
            errors.append(f"{f} 导入失败：{e!r}"); continue
        check_profile(pf, f, chapter_ids, errors)
        if isinstance(pf, dict):
            if pf.get("id") in seen: errors.append(f"comp/{pf.get('id')} id 重复")
            seen.add(pf.get("id")); profiles.append(pf)
    profiles.sort(key=lambda x: x.get("order", 99))
    mp = os.path.join(D, "comp", "map.md")
    cards = [dict(id="comp-" + pf["id"], q=f"说说你对 {pf['name']} 的理解：特性、优缺点，什么时候该用？", level=1, short=pf["say"], points=pf["points"],
                  explain=profile_md(pf), followups=pf["followups"], pitfalls=[], hook="", profile=pf) for pf in profiles if isinstance(pf, dict) and pf.get("name")]
    return dict(id="comp", order=0, name="组件画像", blurb="MySQL、Redis、MQ、ES……特性、优缺点、选型和测试要点",
                map=open(mp, encoding="utf-8").read() if os.path.exists(mp) else "", cards=cards)


def main():
    args = sys.argv[1:]
    only = args[args.index("--check") + 1] if "--check" in args else None
    if only and only.startswith("comp/"):
        errors = []
        chapter_ids = {os.path.basename(f)[:-3] for f in glob.glob(os.path.join(D, "bg", "*.py"))}
        spec = importlib.util.spec_from_file_location("one", os.path.join(D, only)); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        check_profile(getattr(m, "PROFILE", None), os.path.join(D, only), chapter_ids, errors)
        print(f"组件画像 {only}，字数 {len(json.dumps(getattr(m, 'PROFILE', {}), ensure_ascii=False))}")
        if errors: print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
        print("OK（只校验，未写 bg.json）"); return
    files = [os.path.join(D, only)] if only else sorted(glob.glob(os.path.join(D, "bg", "*.py")))
    errors, chapters, ids = [], [], set()
    for f in files:
        try: ch = load(f)
        except Exception as e: errors.append(f"{f} 导入失败：{e!r}"); continue
        check_chapter(ch, f, errors)
        if isinstance(ch, dict):
            for c in ch.get("cards", []):
                if c.get("id") in ids: errors.append(f"{c.get('id')} id 重复")
                ids.add(c.get("id"))
            chapters.append(ch)
    if not only:
        comp = comp_chapter({c.get("id") for c in chapters}, errors)
        if comp: chapters.append(comp)
    n = sum(len(c.get("cards", [])) for c in chapters)
    print(f"章节 {len(chapters)}，卡片 {n}，字数 {sum(len(json.dumps(c, ensure_ascii=False)) for c in chapters)}")
    if errors:
        print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
    if only: print("OK（只校验，未写 bg.json）"); return
    chapters.sort(key=lambda c: c["order"])
    json.dump({"chapters": chapters}, open(os.path.join(D, "bg.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("OK -> bg.json")


if __name__ == "__main__":
    main()
