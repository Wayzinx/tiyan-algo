// ---------- 八股：计算机基础（数据结构 / 并发 / 操作系统 / MySQL / Redis / MQ / 网络 / 语言 / 设计模式 / 测试） ----------
// 内容来自 data/bg/*.py → gen_bg.py → bg.json。进度只存在本机：tiyan:bg（每张卡的复习阶段）、tiyan:bg:probe（摸底记录）。
const BG = (() => { try { return JSON.parse(document.getElementById("bg-data").textContent); } catch (e) { return { chapters: [] }; } })();
const BG_CARDS = BG.chapters.flatMap(ch => ch.cards.map(c => Object.assign({ chId: ch.id, chName: ch.name }, c)));
const BG_BY = Object.fromEntries(BG_CARDS.map(c => [c.id, c]));
const BG_LEVEL = { 1: "必会", 2: "常问", 3: "进阶" };
const BG_TABS = [["bg", "总览"], ["bg-read", "学习"], ["bg-cards", "闪卡"], ["bg-probe", "模拟摸底"]];
const BG_RATE = { bad: "不会", vague: "模糊", good: "会了" };

const BGS = {
  all() { return LS.get("tiyan:bg", {}); },
  get(id) { return this.all()[id] || null; },
  rate(id, r, score) {
    const all = this.all();
    const d = all[id] || { stage: 0, n: 0 };
    const now = Date.now();
    if (r === "good") { d.due = startOfDay(now) + INTERVALS[Math.min(d.stage || 0, INTERVALS.length - 1)] * DAY; d.stage = Math.min((d.stage || 0) + 1, 5); }
    else if (r === "vague") { d.due = startOfDay(now) + DAY; d.stage = Math.max((d.stage || 0) - 1, 0); }
    else { d.due = startOfDay(now) + DAY; d.stage = 0; }
    d.last = r; d.n = (d.n || 0) + 1; d.at = now;
    if (score != null) d.score = score;
    all[id] = d;
    LS.set("tiyan:bg", all);
    const day = new Date().toISOString().slice(0, 10);
    const days = LS.get("tiyan:bg:days", {});
    days[day] = (days[day] || 0) + 1;
    LS.set("tiyan:bg:days", days);
  },
  due(filter) { const all = this.all(), now = Date.now(); return BG_CARDS.filter(c => all[c.id] && all[c.id].due <= now && (!filter || filter(c))).sort((a, b) => all[a.id].due - all[b.id].due); },
  fresh(filter) { const all = this.all(); return BG_CARDS.filter(c => !all[c.id] && (!filter || filter(c))).sort((a, b) => a.level - b.level); },
  today() { return LS.get("tiyan:bg:days", {})[new Date().toISOString().slice(0, 10)] || 0; },
  streak() {
    const days = LS.get("tiyan:bg:days", {});
    let n = 0;
    for (let d = new Date(); n < 400; d.setDate(d.getDate() - 1)) {
      const k = d.toISOString().slice(0, 10);
      if (days[k]) n++;
      else if (n > 0 || k !== new Date().toISOString().slice(0, 10)) break;
    }
    return n;
  },
  mix(ids) {
    const all = this.all(), m = { good: 0, vague: 0, bad: 0, new: 0 };
    for (const id of ids) { const d = all[id]; m[d ? d.last : "new"]++; }
    return m;
  },
};

function bgTabs(cur) {
  const due = BGS.due().length;
  return h("nav", { class: "page-tabs", "aria-label": "八股" }, BG_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t,
    k === "bg-cards" && due ? h("span", { class: "badge num" }, due) : "")));
}
function bgMixBar(ids) {
  const m = BGS.mix(ids), n = ids.length || 1;
  return h("div", { class: "bg-mix", title: `会了 ${m.good} · 模糊 ${m.vague} · 不会 ${m.bad} · 未学 ${m.new}` },
    ["good", "vague", "bad"].map(k => m[k] ? h("i", { class: k, style: `width:${(m[k] / n) * 100}%` }) : ""));
}
function bgOpenCard(id) { LS.set("tiyan:sec:bg", id); go("bg-read"); }
function bgLevelTag(c) { return h("span", { class: "bg-lv l" + c.level }, BG_LEVEL[c.level]); }

const BG_TEACHER = `你是「题眼」里的计算机基础（八股）老师，帮一名测试开发工程师（主要写 Python）从零捡回面试基础：数据结构、进程线程与并发、操作系统与 Linux、MySQL、Redis、消息队列、计算机网络、Python / Java 语言特性、设计模式、测试基础。
规则：
1. 先在站内卡片里找依据（可以用 search_notes 搜索、read_section 读全文）；资料里没写的用通用知识补充，并说明。
2. 讲解顺序：一句话结论 → 用类比讲机制 → 一个具体例子（时序 / 代码 / SQL / 命令）→ 面试里怎么说（30 秒版）→ 常见追问。
3. 尽量把知识点挂到测开场景：并发测试、压测、造数据、断言、监控、排障命令。
4. 中文、口语化、准确；不确定的版本细节直说，不要编参数名和数字。`;

function bgGroups() {
  return BG.chapters.map(ch => ({
    id: ch.id, name: ch.name, blurb: ch.blurb,
    sections: [{ id: ch.id + "-map", title: "知识地图", course: ch.name, chId: ch.id, isMap: true, md: ch.map }]
      .concat(ch.cards.map(c => Object.assign({ title: c.q, course: ch.name, md: "" }, BG_BY[c.id]))),
  }));
}
function bgText(s) {
  if (s.isMap) return `### ${s.course} · 知识地图\n\n${s.md}`;
  return [`### ${s.q}`, s.alt && s.alt.length ? "其他问法：" + s.alt.join("；") : "", "30 秒版：" + s.short, "得分点：\n- " + s.points.join("\n- "), s.explain,
    "易错：\n- " + s.pitfalls.join("\n- "), "测开视角：" + s.hook, s.followups.map(f => `追问：${f.q}\n答：${f.a}`).join("\n\n")].filter(Boolean).join("\n\n");
}

// 卡片「讲解」：30 秒版 → 得分点 → 讲透 → 易错 → 测开视角 → 自评
function bgCardBody(c, onRated) {
  const ex = h("div", { class: "md course-md" }); renderMd(ex, c.explain);
  return h("div", { class: "stack", style: "gap:18px" },
    h("div", { class: "row small" }, bgLevelTag(c), c.alt && c.alt.length ? h("span", { class: "faint" }, "也可能这样问：" + c.alt.join(" / ")) : ""),
    h("div", { class: "bg-short" }, h("div", { class: "bg-label" }, "30 秒版 · 先把这段说顺"), h("p", null, c.short)),
    h("section", { class: "stack", style: "gap:8px" }, h("h3", null, "得分点"), h("ol", { class: "bg-points" }, c.points.map(p => h("li", null, p)))),
    c.mnemonic ? h("div", { class: "bg-mnemonic" }, h("b", null, "口诀　"), c.mnemonic) : "",
    h("section", { class: "stack", style: "gap:6px" }, h("h3", null, "讲透"), ex),
    h("div", { class: "callout" }, h("b", null, "易错　"), h("ul", { class: "bg-list" }, c.pitfalls.map(p => h("li", null, p)))),
    h("div", { class: "callout blue" }, h("b", null, "测开视角　"), c.hook.replace(/^测开视角[：:]\s*/, "")),
    bgRateRow(c, onRated));
}
function bgRateRow(c, onRated) {
  const d = BGS.get(c.id);
  const row = h("div", { class: "bg-rate" }, h("span", { class: "small muted" }, d ? `上次：${BG_RATE[d.last]} · 复习 ${d.n} 次${d.due > Date.now() ? " · " + relDay(d.due) + "再练" : ""}` : "合上页面能说出 30 秒版吗？"));
  for (const k of ["bad", "vague", "good"]) {
    const b = h("button", { class: "btn sm bg-r-" + k, type: "button" }, BG_RATE[k]);
    b.addEventListener("click", () => { BGS.rate(c.id, k); toast(k === "good" ? "记下了，过几天再考你" : "记下了，明天再练"); row.replaceWith(bgRateRow(c, onRated)); if (onRated) onRated(k); });
    row.append(b);
  }
  return row;
}

// 自测：写下回答 → AI 按得分点阅卷（不进 AI 知识的错题本，单独记在八股进度里）
function bgGradeItem(c) {
  return { id: "bg:" + c.id, kind: "s", sec: { course: "八股 · " + c.chName, title: c.q, id: c.id }, q: { q: c.q, points: c.points, a: c.short + "\n\n参考展开：\n" + clip(c.explain, 2500) } };
}
async function bgGrade(c, ans) {
  const g = await AI.ask(GRADE_PROMPT(bgGradeItem(c), ans), { json: true, tier: "default" });
  return { score: Math.max(0, Math.min(10, Math.round((Number(g.score) || 0) * 2) / 2)), hit: g.hit || [], partial: g.partial || [], missed: g.missed || [], feedback: String(g.feedback || ""), better: String(g.better || "") };
}
function bgGradeView(c, g) {
  const [cls, band] = mockBand(g.score);
  const mark = (arr, i) => Array.isArray(arr) && arr.map(Number).includes(i);
  const better = h("div", { class: "md small" }); renderMd(better, g.better);
  return h("div", { class: "stack", style: "gap:10px" },
    h("div", { class: "row" }, h("span", { class: "mock-score num" }, String(g.score), h("small", null, " / 10")), h("span", { class: "pill " + cls }, band), h("span", { class: "small faint" }, "AI 估算，仅供参考")),
    g.feedback ? h("p", null, g.feedback) : "",
    h("ul", { class: "ex-points" }, c.points.map((p, i) => h("li", { class: mark(g.hit, i) ? "hit" : mark(g.partial, i) ? "part" : "miss" }, h("b", null, mark(g.hit, i) ? "答到" : mark(g.partial, i) ? "部分" : "缺失"), p))),
    g.better ? h("details", { class: "qa", open: g.score < 8 }, h("summary", null, "更好的回答"), better) : "");
}
function bgAutoRate(score) { return score >= 8 ? "good" : score >= 5 ? "vague" : "bad"; }
function bgSelfTest(c) {
  const key = "tiyan:bg:draft:" + c.id;
  const ta = h("textarea", { class: "mock-input", id: "bg-ans-" + c.id, style: "min-height:120px", placeholder: "先别看讲解。像面试一样回答：结论 → 机制 → 例子。可以用系统听写（Mac 连按两下 Fn）直接说。" });
  ta.value = LS.get(key, "");
  ta.addEventListener("input", () => LS.set(key, ta.value));
  const out = h("div", { class: "ex-result", hidden: true });
  const btn = h("button", { class: "btn sm primary", type: "button" }, "交给 AI 按得分点打分");
  const self = h("button", { class: "btn sm", type: "button" }, "不用 AI，对着得分点自查");
  btn.addEventListener("click", async () => {
    const ans = ta.value.trim();
    if (ans.length < 6) { toast("先写下你的回答"); return; }
    if (!AI.ok()) { toast(aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" })); if (S.ai === "needkey") openKeyDialog(); return; }
    btn.disabled = true; out.hidden = false; out.textContent = ""; out.append(h("div", { class: "thinking" }, "AI 在对照得分点阅卷……"));
    try {
      const g = await bgGrade(c, ans);
      out.textContent = "";
      out.append(bgGradeView(c, g), h("p", { class: "small muted" }, `已按得分记进闪卡进度：${BG_RATE[bgAutoRate(g.score)]}`));
      BGS.rate(c.id, bgAutoRate(g.score), g.score);
    } catch (e) { out.textContent = e && e.code ? aiErr(e) : "阅卷失败：" + ((e && e.message) || e); }
    finally { btn.disabled = false; }
  });
  self.addEventListener("click", () => {
    out.hidden = false; out.textContent = "";
    const boxes = c.points.map(p => h("label", { class: "ex-opt" }, h("input", { type: "checkbox" }), h("span", null, p)));
    out.append(h("p", { class: "small muted" }, "勾上你说到的得分点："), h("div", { class: "ex-opts" }, boxes),
      h("div", { class: "bg-short" }, h("div", { class: "bg-label" }, "30 秒版"), h("p", null, c.short)), bgRateRow(c));
  });
  const prev = BGS.get(c.id);
  return h("div", { class: "stack", style: "gap:12px" },
    h("p", { class: "small muted" }, "主动回忆比重读有效得多：先自己答，再对照。", prev && prev.score != null ? `上次 AI 打分 ${prev.score}。` : ""),
    h("div", { class: "bg-q" }, c.q), ta, h("div", { class: "row" }, btn, self), out);
}

function viewBG(r) {
  const sub = r.sub || "bg";
  if (!BG.chapters.length) return h("div", { class: "page" }, h("h1", null, "八股"), h("p", { class: "muted" }, "内容还没准备好。"));
  if (sub === "bg-read") return viewCourse({
    key: "bg", eyebrow: "八股 · 学习", title: "一张卡一个面试问题，先会说 30 秒版",
    lede: "每张卡：30 秒版 → 得分点 → 讲透 → 易错 → 测开视角。「自测」标签先自己答再让 AI 按得分点打分；「追问」是面试官最可能接着问的。",
    pageTabs: bgTabs("bg-read"),
    groups: bgGroups, text: bgText,
    searchHint: "搜索，如 回表、GIL、超卖、TIME_WAIT",
    teacher: BG_TEACHER,
    placeholder: "问任何不懂的：比如“MVCC 和锁是什么关系？”（Enter 发送）",
    intro: "我会先在站内卡片里找依据再回答。读不懂就让我换个说法讲；想练表达就点「面试追问我」。",
    chatActions: [
      { label: "随机摸底我 3 题", run: c => c.send("像一面面试官摸底一样，从站内八股卡片里随机挑 3 个不同章节的必会问题，一次只问一个，等我回答后点评（对照得分点指出缺了什么），再问下一个。现在只问第一个。", { label: "随机摸底", noPrefetch: true }) },
      { label: "这章最常问的 5 个", run: c => { const s = LS.get("tiyan:sec:bg", ""); const ch = BG.chapters.find(x => s.startsWith(x.id + "-")) || BG.chapters[0]; c.send(`「${ch.name}」这一章面试最常问的 5 个问题是什么？按重要程度排序，每题给一句话答题要点。`, { label: ch.name + " 高频 5 问" }); } },
    ],
    sectionActions: [
      ["换个说法讲", "我没太懂这张卡。请完全换一种讲法：先用一个生活中的类比从头讲，少用术语，最后再把术语对应回去。"],
      ["画图讲解", "用一张 ASCII 示意图（放在代码块里）画出这张卡讲的机制或时序，然后按图一步步解释。"],
      ["挂到我的测开经历上", "我是测试开发工程师，做过测试平台、接口自动化、AI 提效。请告诉我这张卡的知识点在面试里怎么和测开经历挂钩：给一段 30 秒的回答示范（结论 + 机制 + 我在测试里怎么用 / 怎么验证）。"],
      ["面试追问我", "扮演面试官，围绕这张卡对我连续追问：先问基础，等我回答后根据我的回答往深处追问（原理 → 场景 → 取舍 → 排障）。现在只问第一个问题。"],
      ["出 3 道选择题", "根据这张卡出 3 道单选题考我（选项要有迷惑性），先只给题目和选项，等我回答后再给答案和解析。"],
    ],
    sectionTabs: s => s.isMap ? null : [["learn", "讲解"], ["test", "自测", bgSelfTest], ["follow", `追问 ${s.followups.length}`, c => h("div", { class: "stack", style: "gap:12px" }, h("p", { class: "small muted" }, "先自己想答案，再展开看。"), qaList("面试官可能接着问", c.followups))]],
    extra: s => s.isMap ? bgMapExtra(s) : bgCardBody(s),
  });
  if (sub === "bg-cards") return bgPage("bg-cards", "闪卡", "每天 15 分钟，把 30 秒版背成条件反射", viewBGCards());
  if (sub === "bg-probe") return bgPage("bg-probe", "模拟摸底", "像一面那样连问，限时作答", viewBGProbe());
  return viewBGHome();
}
function bgPage(k, eyebrow, title, body) {
  return h("div", { class: "page wide" }, h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "八股 · " + eyebrow), h("h1", null, title)), bgTabs(k), body);
}
function bgMapExtra(s) {
  const ch = BG.chapters.find(x => x.id === s.chId);
  return h("section", { class: "stack", style: "gap:8px" },
    h("div", { class: "spread" }, h("h3", null, `本章 ${ch.cards.length} 张卡`), h("div", { class: "row" }, h("button", { class: "btn sm primary", type: "button", onclick: () => { LS.set("tiyan:bg:filter", { ch: [ch.id], lv1: false }); BG_SESSION = null; go("bg-cards"); } }, "本章闪卡"))),
    h("div", { class: "bg-cardlist" }, ch.cards.map(c => {
      const d = BGS.get(c.id);
      return h("button", { type: "button", class: "bg-crow", onclick: () => bgOpenCard(c.id) }, bgLevelTag(c), h("span", { class: "t" }, c.q), h("span", { class: "bg-dot " + (d ? d.last : "new"), title: d ? BG_RATE[d.last] : "未学" }));
    })));
}

function viewBGHome() {
  const total = BG_CARDS.length, all = BGS.all();
  const seen = BG_CARDS.filter(c => all[c.id]).length, good = BG_CARDS.filter(c => all[c.id] && all[c.id].last === "good").length;
  const due = BGS.due().length;
  const last = LS.get("tiyan:sec:bg", "");
  const lastCard = BG_BY[last];
  const probes = LS.get("tiyan:bg:probe", []);
  const lastProbe = probes[0];
  const avg = p => { const s = p.items.filter(x => x.g).map(x => x.g.score); return s.length ? (s.reduce((a, b) => a + b, 0) / s.length).toFixed(1) : "—"; };
  return h("div", { class: "page wide" },
    h("section", { class: "hero" },
      h("div", { class: "eyebrow" }, "八股 · 计算机基础"),
      h("h1", null, "面试官摸底时，", h("span", { class: "circ" }, "每题先说出 30 秒版", h("span", { html: CIRCLE }))),
      h("p", { class: "lede" }, `${BG.chapters.length} 章 ${total} 张卡，覆盖一面最常摸底的基础：数据结构、进程线程与线程安全、MySQL 慢查询 / 事务 / 锁、Redis 缓存与超卖、消息队列、网络、操作系统与 Linux、Python / Java、设计模式、测试基础。每张卡都有 30 秒版、得分点、讲透、追问和测开视角。`),
      h("div", { class: "stats" },
        h("div", { class: "stat" }, h("b", null, `${seen}`, h("small", { class: "faint", style: "font-size:14px" }, ` / ${total}`)), h("span", null, "学过")),
        h("div", { class: "stat" }, h("b", null, good), h("span", null, "会了")),
        h("div", { class: "stat" }, h("b", null, due), h("span", null, "今天待复习")),
        h("div", { class: "stat" }, h("b", null, BGS.streak()), h("span", null, "连续天数")))),
    bgTabs("bg"),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", null, "今天做什么")),
        h("div", { class: "task-list" },
          h("a", { class: "task", href: "#bg-cards" }, h("span", { class: "task-k r" }, "卡"), h("span", null, h("span", { class: "task-t" }, due ? `复习 ${due} 张到期的卡` : "开始今天的闪卡"), h("br"), h("span", { class: "small faint" }, "看问题 → 先自己说 → 翻面对照得分点 → 自评")), ""),
          h("a", { class: "task", href: "#bg-read", onclick: () => { if (!lastCard) LS.set("tiyan:sec:bg", BG.chapters[0].id + "-map"); } }, h("span", { class: "task-k n" }, "学"), h("span", null, h("span", { class: "task-t" }, lastCard ? "接着学：" + clip(lastCard.q, 24) : "从「" + BG.chapters[0].name + "」开始"), h("br"), h("span", { class: "small faint" }, "一次学 3–5 张，学完点「会了 / 模糊 / 不会」")), ""),
          h("a", { class: "task", href: "#bg-probe" }, h("span", { class: "task-k n" }, "考"), h("span", null, h("span", { class: "task-t" }, "模拟摸底一轮"), h("br"), h("span", { class: "small faint" }, lastProbe ? `上次 ${fmtDate(lastProbe.at)}：平均 ${avg(lastProbe)} 分` : "随机抽必会题，限时作答，AI 按得分点打分")), ""))),
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", null, "建议顺序"), h("span", { class: "small faint" }, "每天 30–40 分钟，两周过完一遍")),
        h("div", { class: "rules" },
          rule("第 1–2 天：数据结构 + 进程线程", "摸底第一问就是“说出你知道的数据结构”“什么是线程安全”。先把这两章的必会卡说顺。"),
          rule("第 3–5 天：MySQL → Redis → 消息队列", "慢查询 / 索引 / 事务 / 锁，缓存问题与超卖，消息丢失 / 重复 / 积压，后端面试的主干。"),
          rule("第 6–8 天：网络 + 操作系统 + Python", "TCP、HTTPS、IO 多路复用、Linux 排查命令，再补 Python 语言特性和 pytest。"),
          rule("第 9–10 天：设计模式 + 测试基础 + Java", "设计模式至少说出 4 个并各配一个测试场景；Java 按需。"),
          rule("之后：每天闪卡 15 分钟 + 每两天摸底一轮", "低分题自动回到闪卡队列，直到“会了”。")))),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "章节"), h("span", { class: "small faint" }, "条形：会了 / 模糊 / 不会，空白是还没学")),
      h("div", { class: "bg-chapters" }, BG.chapters.map(ch => {
        const ids = ch.cards.map(c => c.id);
        return h("div", { class: "bg-ch" },
          h("div", { class: "spread" }, h("b", null, ch.name), h("span", { class: "small faint num" }, `${ch.cards.length} 张 · 必会 ${ch.cards.filter(c => c.level === 1).length}`)),
          h("p", { class: "small muted" }, ch.blurb),
          bgMixBar(ids),
          h("div", { class: "row" },
            h("a", { class: "btn sm", href: "#bg-read", onclick: () => LS.set("tiyan:sec:bg", ch.id + "-map") }, "学习"),
            h("button", { class: "btn sm ghost", type: "button", onclick: () => { LS.set("tiyan:bg:filter", { ch: [ch.id], lv1: false }); BG_SESSION = null; go("bg-cards"); } }, "闪卡"),
            h("button", { class: "btn sm ghost", type: "button", onclick: () => { LS.set("tiyan:bg:probecfg", Object.assign(LS.get("tiyan:bg:probecfg", {}), { ch: [ch.id] })); go("bg-probe"); } }, "摸底")));
      }))));
}

// ---------- 闪卡 ----------
let BG_SESSION = null;
function viewBGCards() {
  const box = h("div", { class: "stack", style: "gap:16px" });
  const f = LS.get("tiyan:bg:filter", { ch: [], lv1: false, n: 12 });
  const filter = c => (!f.ch || !f.ch.length || f.ch.includes(c.chId)) && (!f.lv1 || c.level === 1);
  const fkey = JSON.stringify(f);
  if (!BG_SESSION || BG_SESSION.fkey !== fkey) {
    const due = BGS.due(filter).map(c => c.id);
    const fresh = BGS.fresh(filter).slice(0, f.n || 12).map(c => c.id);
    BG_SESSION = { fkey, queue: due.concat(fresh), i: 0, flipped: false, stats: { good: 0, vague: 0, bad: 0 }, again: new Set(), nDue: due.length, nNew: fresh.length };
  }
  const ss = BG_SESSION;
  const chips = h("div", { class: "row bg-filter" },
    h("button", { type: "button", class: "chip" + (!f.ch || !f.ch.length ? " on" : ""), onclick: () => setF({ ch: [] }) }, "全部章节"),
    BG.chapters.map(ch => h("button", { type: "button", class: "chip" + (f.ch && f.ch.includes(ch.id) ? " on" : ""), onclick: () => { const cur = new Set(f.ch || []); cur.has(ch.id) ? cur.delete(ch.id) : cur.add(ch.id); setF({ ch: [...cur] }); } }, ch.name)));
  const opts = h("div", { class: "row small" },
    h("label", { class: "row", style: "gap:6px" }, h("input", { type: "checkbox", checked: !!f.lv1, onchange: e => setF({ lv1: e.target.checked }) }), "只练必会"),
    h("span", { class: "faint" }, "每轮新卡"),
    h("div", { class: "seg" }, [6, 12, 20].map(n => h("button", { type: "button", class: (f.n || 12) === n ? "on" : "", onclick: () => setF({ n }) }, n))));
  function setF(p) { LS.set("tiyan:bg:filter", Object.assign({}, f, p)); BG_SESSION = null; render(); }
  const stage = h("div", { class: "stack", style: "gap:14px" });
  const onKey = e => {
    if (S.route.view !== "bg" || /input|textarea|select/i.test((e.target && e.target.tagName) || "")) return;
    if (!ss.flipped && (e.key === " " || e.key === "Enter")) { e.preventDefault(); flip(); }
    else if (ss.flipped && ["1", "2", "3"].includes(e.key)) rate(["bad", "vague", "good"][+e.key - 1]);
  };
  document.addEventListener("keydown", onKey);
  onLeave(() => document.removeEventListener("keydown", onKey));
  function flip() { ss.flipped = true; draw(); }
  function rate(k) {
    const id = ss.queue[ss.i];
    if (!ss.again.has(id)) { BGS.rate(id, k); ss.stats[k]++; }
    if (k === "bad" && !ss.again.has(id)) { ss.again.add(id); ss.queue.push(id); }
    ss.i++; ss.flipped = false; draw();
  }
  function draw() {
    stage.textContent = "";
    if (!ss.queue.length) {
      stage.append(h("div", { class: "panel" }, h("h2", null, "这个范围里没有要练的卡"), h("p", { class: "muted" }, "到期的都复习完了，新卡也都学过了。换个章节，或者去「模拟摸底」考一轮。"), h("div", { class: "row" }, h("a", { class: "btn primary", href: "#bg-probe" }, "模拟摸底"), h("button", { class: "btn", type: "button", onclick: () => setF({ ch: [], lv1: false }) }, "看全部章节"))));
      return;
    }
    if (ss.i >= ss.queue.length) {
      stage.append(h("div", { class: "panel" }, h("h2", null, "这一轮练完了"),
        h("p", null, `会了 ${ss.stats.good} · 模糊 ${ss.stats.vague} · 不会 ${ss.stats.bad}`),
        h("p", { class: "small muted" }, "“会了”的卡按 1 / 3 / 7 / 15 / 30 天再出现；模糊和不会的明天再来。"),
        h("div", { class: "row" }, h("button", { class: "btn primary", type: "button", onclick: () => { BG_SESSION = null; render(); } }, "再来一轮"), h("a", { class: "btn", href: "#bg-probe" }, "模拟摸底"), h("a", { class: "btn ghost", href: "#bg" }, "回总览"))));
      return;
    }
    const c = BG_BY[ss.queue[ss.i]];
    const pct = Math.round((ss.i / ss.queue.length) * 100);
    const d = BGS.get(c.id);
    const card = h("div", { class: "panel bg-flash" + (ss.flipped ? " flipped" : "") },
      h("div", { class: "spread small" }, h("span", { class: "row", style: "gap:8px" }, h("span", { class: "tag" }, c.chName), bgLevelTag(c), d ? h("span", { class: "faint" }, `上次${BG_RATE[d.last]}`) : h("span", { class: "faint" }, "新卡")), h("span", { class: "faint num" }, `${ss.i + 1} / ${ss.queue.length}`)),
      h("div", { class: "bg-progress" }, h("i", { style: `width:${pct}%` })),
      h("div", { class: "bg-q big" }, c.q),
      c.alt && c.alt.length ? h("div", { class: "small faint" }, "也可能问：" + c.alt.join(" / ")) : "");
    if (!ss.flipped) {
      card.append(h("p", { class: "muted" }, "先在心里或出声答一遍：结论 → 机制 → 例子。说不出来也没关系，翻过来看。"),
        h("div", { class: "row" }, h("button", { class: "btn primary", type: "button", onclick: flip }, "翻面看答案 ", h("span", { class: "kbd" }, "空格"))));
    } else {
      const boxes = c.points.map(p => h("label", { class: "ex-opt" }, h("input", { type: "checkbox" }), h("span", null, p)));
      card.append(
        h("div", { class: "bg-short" }, h("div", { class: "bg-label" }, "30 秒版"), h("p", null, c.short)),
        h("div", { class: "stack", style: "gap:6px" }, h("div", { class: "small muted" }, "得分点（勾上你刚才说到的）："), h("div", { class: "ex-opts" }, boxes)),
        c.mnemonic ? h("div", { class: "bg-mnemonic" }, h("b", null, "口诀　"), c.mnemonic) : "",
        h("div", { class: "spread" },
          h("a", { class: "small", href: "#bg-read", onclick: () => LS.set("tiyan:sec:bg", c.id) }, "看讲透 →"),
          h("div", { class: "row" },
            ["bad", "vague", "good"].map((k, i) => h("button", { class: "btn bg-r-" + k, type: "button", onclick: () => rate(k) }, BG_RATE[k], " ", h("span", { class: "kbd" }, String(i + 1)))))));
    }
    stage.append(card);
  }
  draw();
  box.append(h("div", { class: "panel", style: "gap:10px" }, chips, h("div", { class: "spread" }, opts, h("span", { class: "small faint" }, `本轮：到期 ${ss.nDue} 张 + 新卡 ${ss.nNew} 张`))), stage);
  return box;
}

// ---------- 模拟摸底 ----------
let BG_PROBE_VIEW = null;
const BG_JOBS = {};
function bgProbes() { return LS.get("tiyan:bg:probe", []); }
function bgSaveProbe(p) { const all = bgProbes().filter(x => x.id !== p.id); all.unshift(p); LS.set("tiyan:bg:probe", all.slice(0, 30)); }
function bgRunGrading(p) {
  if (BG_JOBS[p.id] || !AI.ok()) return;
  BG_JOBS[p.id] = true;
  const todo = p.items.filter(x => !x.g && x.ans && x.ans.trim().length >= 4);
  let k = 0;
  const worker = async () => {
    while (k < todo.length) {
      const it = todo[k++];
      try { it.g = await bgGrade(BG_BY[it.cid], it.ans); BGS.rate(it.cid, bgAutoRate(it.g.score), it.g.score); }
      catch (e) { it.err = e && e.code ? aiErr(e) : String((e && e.message) || e); }
      const cur = bgProbes().find(x => x.id === p.id) || p;
      const tgt = cur.items.find(x => x.cid === it.cid);
      if (tgt) Object.assign(tgt, { g: it.g, err: it.err });
      bgSaveProbe(cur);
      if (BG_PROBE_VIEW && BG_PROBE_VIEW.sid === p.id) BG_PROBE_VIEW.redraw();
    }
  };
  Promise.all([worker(), worker(), worker()]).finally(() => {
    delete BG_JOBS[p.id];
    if (BG_PROBE_VIEW && BG_PROBE_VIEW.sid === p.id) BG_PROBE_VIEW.redraw();
  });
}
function viewBGProbe() {
  const box = h("div", { class: "stack", style: "gap:16px" });
  let run = null;   // 正在答题：{ p, i, left, timer }
  BG_PROBE_VIEW = { sid: null, redraw: () => draw() };
  onLeave(() => { if (run && run.timer) clearInterval(run.timer); BG_PROBE_VIEW = null; });
  const cfg = Object.assign({ ch: [], n: 6, sec: 90, lv1: true }, LS.get("tiyan:bg:probecfg", {}));
  const setCfg = p => { Object.assign(cfg, p); LS.set("tiyan:bg:probecfg", cfg); draw(); };
  function start() {
    const pool = BG_CARDS.filter(c => (!cfg.ch.length || cfg.ch.includes(c.chId)) && (!cfg.lv1 || c.level === 1));
    if (!pool.length) { toast("这个范围里没有题"); return; }
    // 优先抽：没学过 / 上次不会或模糊的；同一章不扎堆
    const all = BGS.all();
    const w = c => (!all[c.id] ? 2 : all[c.id].last === "bad" ? 3 : all[c.id].last === "vague" ? 2 : 1) * Math.random();
    const sorted = pool.slice().sort((a, b) => w(b) - w(a));
    const pick = [], usedCh = {};
    for (const pass of [1, 2, 99]) for (const c of sorted) { if (pick.length >= cfg.n) break; if (!pick.includes(c) && (usedCh[c.chId] || 0) < pass) { pick.push(c); usedCh[c.chId] = (usedCh[c.chId] || 0) + 1; } }
    const p = { id: "pr" + Date.now().toString(36), at: Date.now(), sec: cfg.sec, items: pick.map(c => ({ cid: c.id, ans: "", t: 0 })) };
    run = { p, i: 0, left: cfg.sec };
    draw();
  }
  function next(skip) {
    const it = run.p.items[run.i];
    const ta = $("#bg-probe-ans");
    it.ans = skip ? "" : (ta ? ta.value : "");
    it.t = run.p.sec - run.left;
    clearInterval(run.timer);
    run.i++;
    if (run.i >= run.p.items.length) {
      const p = run.p; run = null;
      p.items.filter(x => !x.ans || x.ans.trim().length < 4).forEach(x => BGS.rate(x.cid, "bad", 0));
      bgSaveProbe(p);
      BG_PROBE_VIEW.sid = p.id;
      LS.set("tiyan:bg:probeview", p.id);
      bgRunGrading(p);
      draw();
      return;
    }
    run.left = run.p.sec;
    draw();
  }
  function draw() {
    box.textContent = "";
    if (run) return drawRun();
    const vid = BG_PROBE_VIEW.sid || LS.get("tiyan:bg:probeview", null);
    const p = vid && bgProbes().find(x => x.id === vid);
    if (p) { BG_PROBE_VIEW.sid = p.id; return drawReport(p); }
    drawSetup();
  }
  function drawSetup() {
    const hist = bgProbes();
    box.append(h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "设置"), h("span", { class: "small faint" }, "一面摸底通常 5–8 个问题、每题 1–2 分钟")),
      h("div", { class: "row bg-filter" },
        h("button", { type: "button", class: "chip" + (!cfg.ch.length ? " on" : ""), onclick: () => setCfg({ ch: [] }) }, "全部章节"),
        BG.chapters.map(ch => h("button", { type: "button", class: "chip" + (cfg.ch.includes(ch.id) ? " on" : ""), onclick: () => { const s = new Set(cfg.ch); s.has(ch.id) ? s.delete(ch.id) : s.add(ch.id); setCfg({ ch: [...s] }); } }, ch.name))),
      h("div", { class: "row small" },
        h("span", { class: "faint" }, "题数"), h("div", { class: "seg" }, [5, 6, 8, 10].map(n => h("button", { type: "button", class: cfg.n === n ? "on" : "", onclick: () => setCfg({ n }) }, n))),
        h("span", { class: "faint" }, "每题"), h("div", { class: "seg" }, [60, 90, 120].map(n => h("button", { type: "button", class: cfg.sec === n ? "on" : "", onclick: () => setCfg({ sec: n }) }, n + " 秒"))),
        h("label", { class: "row", style: "gap:6px" }, h("input", { type: "checkbox", checked: cfg.lv1, onchange: e => setCfg({ lv1: e.target.checked }) }), "只抽必会题")),
      h("p", { class: "small muted" }, "规则：每题限时，时间到自动进入下一题；答完一起交给 AI 按得分点打分（没配 AI 就对着得分点自查）。打分结果自动记进闪卡：低于 5 分算“不会”，5–7.5 分算“模糊”。优先抽你没学过、上次不会的卡。", AI.ok() ? "" : h("b", null, "　当前 AI 未就绪：可以照常作答，结束后自查。")),
      h("div", { class: "row" }, h("button", { class: "btn primary", type: "button", onclick: start }, "开始摸底"))),
      hist.length ? h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "历史")),
        h("div", { class: "stack", style: "gap:6px" }, hist.slice(0, 10).map(p => {
          const s = p.items.filter(x => x.g).map(x => x.g.score);
          return h("button", { type: "button", class: "bg-crow", onclick: () => { BG_PROBE_VIEW.sid = p.id; LS.set("tiyan:bg:probeview", p.id); draw(); } },
            h("span", { class: "tag" }, fmtDate(p.at)), h("span", { class: "t" }, p.items.map(x => BG_BY[x.cid] ? BG_BY[x.cid].chName : "").filter((v, i, a) => v && a.indexOf(v) === i).join(" · ")),
            h("span", { class: "num small" }, s.length ? `平均 ${(s.reduce((a, b) => a + b, 0) / s.length).toFixed(1)}` : "未评分"));
        }))) : "");
  }
  function drawRun() {
    const it = run.p.items[run.i], c = BG_BY[it.cid];
    const ta = h("textarea", { class: "mock-input", id: "bg-probe-ans", style: "min-height:150px", placeholder: "像面试一样回答：先一句结论，再讲机制和例子。Mac 可以连按两下 Fn 用听写直接说。" });
    const bar = h("i", { style: `width:${(run.left / run.p.sec) * 100}%` });
    const left = h("span", { class: "num" }, run.left + " 秒");
    box.append(h("section", { class: "panel bg-flash" },
      h("div", { class: "spread small" }, h("span", { class: "row", style: "gap:8px" }, h("span", { class: "tag" }, c.chName), bgLevelTag(c)), h("span", { class: "faint num" }, `第 ${run.i + 1} / ${run.p.items.length} 题 · `, left)),
      h("div", { class: "bg-progress timer" + (run.left <= 15 ? " low" : "") }, bar),
      h("div", { class: "bg-q big" }, c.q),
      ta,
      h("div", { class: "spread" }, h("button", { class: "btn ghost sm", type: "button", onclick: () => next(true) }, "不会，跳过"), h("button", { class: "btn primary", type: "button", onclick: () => next(false) }, run.i + 1 < run.p.items.length ? "下一题 →" : "交卷"))));
    setTimeout(() => ta.focus(), 30);
    clearInterval(run.timer);
    run.timer = setInterval(() => {
      run.left--;
      left.textContent = run.left + " 秒";
      bar.style.width = (run.left / run.p.sec) * 100 + "%";
      bar.parentNode.classList.toggle("low", run.left <= 15);
      if (run.left <= 0) next(false);
    }, 1000);
  }
  function drawReport(p) {
    const graded = p.items.filter(x => x.g), s = graded.map(x => x.g.score);
    const avg = s.length ? s.reduce((a, b) => a + b, 0) / s.length : null;
    const pending = AI.ok() && p.items.some(x => !x.g && !x.err && x.ans && x.ans.trim().length >= 4);
    const byCh = {};
    for (const x of graded) { const n = BG_BY[x.cid].chName; (byCh[n] = byCh[n] || []).push(x.g.score); }
    const weak = Object.entries(byCh).map(([n, a]) => [n, a.reduce((x, y) => x + y, 0) / a.length]).sort((a, b) => a[1] - b[1]);
    const head = h("section", { class: "panel" },
      h("div", { class: "spread" }, h("h2", null, `${fmtDate(p.at)} 的摸底`), h("div", { class: "row" },
        h("button", { class: "btn sm", type: "button", onclick: () => { BG_PROBE_VIEW.sid = null; LS.del("tiyan:bg:probeview"); draw(); } }, "← 设置 / 历史"),
        h("button", { class: "btn sm primary", type: "button", onclick: () => { BG_PROBE_VIEW.sid = null; LS.del("tiyan:bg:probeview"); start(); } }, "再来一轮"))),
      h("div", { class: "row" },
        avg != null ? h("span", { class: "mock-score num" }, avg.toFixed(1), h("small", null, " / 10 平均")) : "",
        pending ? h("span", { class: "thinking" }, `AI 正在阅卷（${graded.length} / ${p.items.length}）……离开页面也会继续`) : "",
        !AI.ok() && !graded.length ? h("span", { class: "small muted" }, "AI 未就绪：对照每题的得分点自查，再点会了 / 模糊 / 不会。") : ""),
      weak.length ? h("p", { class: "small" }, "按章节：", weak.map(([n, v]) => h("span", { class: "tag", style: "margin-right:6px" }, `${n} ${v.toFixed(1)}`))) : "",
      AI.ok() && p.items.some(x => x.err) ? h("button", { class: "btn sm", type: "button", onclick: () => { p.items.forEach(x => { delete x.err; }); bgSaveProbe(p); bgRunGrading(p); draw(); } }, "重试失败的阅卷") : "");
    box.append(head);
    p.items.forEach((x, i) => {
      const c = BG_BY[x.cid];
      if (!c) return;
      const ansMd = h("div", { class: "md small" }); renderMd(ansMd, x.ans || "（没有作答）");
      const body = h("div", { class: "stack", style: "gap:10px" });
      if (x.g) body.append(bgGradeView(c, x.g));
      else if (x.err) body.append(h("p", { class: "small", style: "color:var(--red)" }, "阅卷失败：" + x.err));
      else if (!x.ans || x.ans.trim().length < 4) body.append(h("p", { class: "small muted" }, "没有作答，已记为“不会”。"));
      else if (!AI.ok()) body.append(h("ul", { class: "bg-list" }, c.points.map(pt => h("li", null, pt))), bgRateRow(c));
      box.append(h("section", { class: "panel", style: "gap:10px" },
        h("div", { class: "spread small" }, h("span", { class: "row", style: "gap:8px" }, h("b", { class: "num" }, `Q${i + 1}`), h("span", { class: "tag" }, c.chName), bgLevelTag(c)), h("span", { class: "faint num" }, x.t ? `用时 ${x.t} 秒` : "")),
        h("div", { class: "bg-q" }, c.q),
        h("details", { class: "qa" }, h("summary", null, "我的回答"), ansMd),
        body,
        h("details", { class: "qa" }, h("summary", null, "30 秒版"), h("p", { class: "small" }, c.short)),
        h("a", { class: "small", href: "#bg-read", onclick: () => LS.set("tiyan:sec:bg", c.id) }, "去学这张卡 →")));
    });
  }
  // 回到页面时，没跑完的阅卷接着跑
  const vid = LS.get("tiyan:bg:probeview", null);
  const pv = vid && bgProbes().find(x => x.id === vid);
  if (pv && AI.ok() && pv.items.some(x => !x.g && !x.err && x.ans && x.ans.trim().length >= 4)) bgRunGrading(pv);
  draw();
  return box;
}
