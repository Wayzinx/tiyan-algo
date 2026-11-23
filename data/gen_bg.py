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


def main():
    args = sys.argv[1:]
    only = args[args.index("--check") + 1] if "--check" in args else None
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
