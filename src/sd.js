// ---------- 设计编码：把“看得懂答案”练成“只看题目就能召回骨架” ----------
// 积木题：题目关键词 → 两个核心状态 → 不变量 → 状态变化 → 异常 → 扩展；设计题：澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标
const SDD = JSON.parse(document.getElementById("sd-data").textContent || '{"blocks":[],"designs":[]}');
const SD_CORE = ["p7", "p8", "p5", "p6", "p2", "p3", "p4"];          // 推荐顺序：先小积木，再组合
const SD_STEPS = [["clarify", "澄清"], ["objects", "对象"], ["flow", "主流程"], ["failure", "失败恢复"], ["concurrency", "并发限流"], ["metrics", "指标"]];
const SD_FIVE = ["核心状态是什么？", "必须始终成立的不变量是什么？", "正常输入怎样改变状态？", "重复、失败、并发、超时怎么办？", "用一个最小例子手动跑一遍。"];
const sdBlock = id => SDD.blocks.find(b => b.id === id);
const sdDesign = id => SDD.designs.find(d => d.id === id);
const sdOrdered = () => SD_CORE.map(sdBlock).filter(Boolean).concat(SDD.blocks.filter(b => !SD_CORE.includes(b.id)));
const SDS = {
  all() { return LS.get("tiyan:sd", { s1: {}, s2: {}, s3: {}, s4: {} }); },
  put(stage, id, rec, list) {
    const a = this.all(); a[stage] = a[stage] || {};
    if (list) { a[stage][id] = (a[stage][id] || []).concat([rec]).slice(-30); }
    else a[stage][id] = Object.assign({}, a[stage][id] || {}, rec, { at: Date.now(), n: ((a[stage][id] || {}).n || 0) + 1 });
    LS.set("tiyan:sd", a);
  },
};
const fmtSec = s => `${s < 0 ? "+" : ""}${Math.floor(Math.abs(s) / 60)}:${String(Math.abs(s) % 60).padStart(2, "0")}`;
// 倒计时：到 0 之后继续计超时（红色）
function countdown(total) {
  const el = h("span", { class: "sd-timer num" });
  let t0 = null, iv = null, stopped = null;
  const draw = () => { const used = Math.floor(((stopped || Date.now()) - (t0 || Date.now())) / 1000); const left = total - used; el.textContent = left >= 0 ? fmtSec(left) : "超时 " + fmtSec(-left).replace("+", ""); el.classList.toggle("over", left < 0); };
  draw();
  const api = {
    el,
    start() { t0 = Date.now(); stopped = null; clearInterval(iv); iv = setInterval(draw, 250); draw(); return api; },
    stop() { if (!t0) return 0; stopped = stopped || Date.now(); clearInterval(iv); draw(); return Math.round((stopped - t0) / 1000); },
    used() { return t0 ? Math.round(((stopped || Date.now()) - t0) / 1000) : 0; },
  };
  onLeave(() => clearInterval(iv));
  return api;
}
function selfMark(onPick, value) {
  const opts = [[2, "想到了"], [1, "部分"], [0, "没想到"]];
  const seg = h("div", { class: "seg sd-mark" }, opts.map(([v, t]) => {
    const b = h("button", { type: "button", class: value === v ? "on" : "" }, t);
    b.addEventListener("click", () => { $$("button", seg).forEach(x => x.classList.remove("on")); b.classList.add("on"); onPick(v); });
    return b;
  }));
  return seg;
}
function sdList(items) { return h("ul", { class: "mock-ul" }, items.map(x => h("li", null, typeof x === "string" ? x : x))); }
function sdStates(b) { return h("div", { class: "sd-states" }, b.states.map(s => h("div", { class: "sd-state" }, h("code", null, s.name), h("span", null, s.desc)))); }
function mdEl(t, cls) { const d = h("div", { class: "md " + (cls || "") }); renderMd(d, t); return d; }
function aiBox() { return h("div", { class: "stack sd-ai" }); }
async function sdAsk(box, prompt, render) {
  if (!AI.ok()) { box.textContent = aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" }); if (S.ai === "needkey") openKeyDialog(); return; }
  box.textContent = ""; box.append(h("div", { class: "thinking" }, "AI 在对照参考答案评估……（大约 15–40 秒）"));
  try { const r = await AI.ask(prompt, { json: true, tier: "default" }); box.textContent = ""; render(r); }
  catch (e) { box.textContent = e && e.code ? aiErr(e) : "评估失败：" + ((e && e.message) || e); }
}
function scoreLine(score, extra) { const [cls, band] = mockBand(score); return h("div", { class: "row" }, h("span", { class: "mock-score num" }, String(score), h("small", null, " / 10")), h("span", { class: "pill " + cls }, band), h("span", { class: "small faint" }, "AI 估算，仅供参考"), extra || ""); }
const SD_TABS = [["sd", "总览"], ["sd-s1", "① 识别模式"], ["sd-s2", "② 口述积木题"], ["sd-s3", "③ 口述设计题"], ["sd-s4", "④ 随机抽题"]];
function sdTabs(cur) { return h("nav", { class: "page-tabs" }, SD_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t))); }
function sdPage(cur, title, lede, ...body) {
  return h("div", { class: "page wide sd-page" }, h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "设计编码"), h("h1", null, title), lede ? h("p", { class: "lede" }, lede) : ""), sdTabs(cur), ...body);
}

function viewSD({ sub }) {
  if (!SDD.blocks.length) return h("div", { class: "page" }, h("h1", null, "设计编码"), h("p", { class: "muted" }, "内容还在准备中，稍后刷新再来。"));
  if (!sub) return sdOverview();
  if (sub === "s1") return sdStage1();
  if (sub === "s2") return sdStage2();
  if (sub === "s3") return sdStage3();
  if (sub === "s4") return sdStage4();
  if (/^p\d+$/.test(sub) && sdBlock(sub)) return sdBlockView(sdBlock(sub));
  if (/^d\d+$/.test(sub) && sdDesign(sub)) return sdDesignView(sdDesign(sub));
  return sdOverview();
}

// ----- 达标统计 -----
function sdCriteria() {
  const a = SDS.all(), core = SD_CORE.filter(sdBlock);
  const last4 = id => (a.s4[id] || []).filter(x => !x.variant).slice(-1)[0];
  const c1 = core.filter(id => { const r = last4(id); return r && r.marks[0] && r.secs <= 30; }).length;
  const c2 = core.filter(id => { const r = last4(id); const s1 = a.s1[id]; return (r && r.marks[1]) || (s1 && s1.self && s1.self.invariants >= 1); }).length;
  const c3 = core.filter(id => { const s1 = a.s1[id]; return s1 && s1.secs <= 300 && s1.self && s1.self.failures >= 1 && s1.self.states >= 1; }).length;
  const c4 = core.filter(id => (a.s4[id] || []).some(x => x.variant && x.marks[0] && x.marks[1])).length;
  const c5 = core.filter(id => { const s2 = a.s2[id]; return s2 && s2.self && s2.self.followup >= 1; }).length;
  return [
    ["看到题目 30 秒内能说出核心状态", c1, "④ 随机抽题里 30 秒内说对核心状态"],
    ["2 分钟内能说出最重要的不变量", c2, "④ 抽题或 ① 识别里说出不变量"],
    ["5 分钟内能写出正常流程和失败流程", c3, "① 识别里 5 分钟内写出状态和失败情况"],
    ["换一个业务背景仍能识别出相同模式", c4, "④ 换皮模式里认出核心状态和不变量"],
    ["被追问并发、重启、失败时不从零思考", c5, "② 口述里进阶追问一段答到了"],
  ].map(([t, n, how]) => ({ t, n, total: core.length, how }));
}
function sdOverview() {
  const a = SDS.all();
  const mark = (id, st) => { const r = st === "s4" ? (a.s4[id] || []).slice(-1)[0] : a[st][id]; if (!r) return h("span", { class: "faint" }, "—"); if (st === "s4") return h("span", { class: r.marks.every(Boolean) && r.secs <= 30 ? "sd-ok" : "sd-bad" }, `${r.secs}s`); return h("span", { class: "sd-ok" }, "✓"); };
  const rows = sdOrdered().map(b => h("tr", { class: "sd-row", onclick: () => go("sd-" + b.id) },
    h("td", { class: "mono" }, b.id.toUpperCase()), h("td", null, h("a", { href: "#sd-" + b.id }, b.title)), h("td", { class: "muted" }, b.essence),
    h("td", null, h("div", { class: "row", style: "gap:4px" }, b.states.map(s => h("code", { class: "sd-chip" }, s.name)))),
    h("td", { class: "num" }, mark(b.id, "s1")), h("td", { class: "num" }, mark(b.id, "s2")), h("td", { class: "num" }, mark(b.id, "s4"))));
  const crit = sdCriteria();
  const plan = [
    ["sd-s1", "第一轮 · 40 分钟", "只练识别模式", "每题只看题目，5 分钟内写下：状态、不变量、失败情况。写不出来再看提示，最后才看答案。", SD_CORE.filter(id => a.s1[id]).length],
    ["sd-s2", "第二轮 · 60 分钟", "口述 P2–P8", "每题 6–8 分钟：1 分钟核心结构、2 分钟正常流程、2 分钟易错点、1 分钟进阶追问。不要求默写代码。", SD_CORE.filter(id => a.s2[id]).length],
    ["sd-s3", "第三轮 · 60 分钟", "口述设计题", "严格按：澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标。设计 1 至少完整说两遍。", SDD.designs.filter(d => (a.s3[d.id] || []).length).length],
    ["sd-s4", "第四轮 · 20 分钟", "随机抽题", "只看题目名，30 秒内说出：两个核心状态、一个最重要不变量、一个失败场景、一个扩展追问。", SD_CORE.filter(id => (a.s4[id] || []).length).length],
  ];
  return sdPage("sd", "看到题目 30 秒内，先弹出骨架", "这里真正 Agent 专属的内容不多：DAG 调度是图算法加任务状态机，幂等执行是 singleflight 加状态机，无损续跑是持久化状态机加权威状态对账。你要练的不是背代码，而是建立十几个高频模式的召回路径——骨架出来了，细节就有地方挂。",
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "编码题统一起手式"), h("p", { class: "small muted" }, "先别写代码，在纸上回答五个问题："), h("ol", { class: "steps" }, SD_FIVE.map((t, i) => h("li", null, h("b", { class: "num" }, i + 1), h("span", null, t)))),
        h("p", { class: "small muted" }, "例：看到“同一个 key 并发只执行一次”，先写出 completed[key] / inflight[key] 两个状态和“同一时刻只有一个 leader、成功才缓存、失败不缓存”，这题就完成了七成。")),
      h("section", { class: "panel" }, h("h2", null, "设计题统一起手式"), h("div", { class: "oneline", style: "font-size:17px" }, "澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标"),
        h("p", { class: "small muted" }, "不会完整设计时，也可以这样开口：“我先确认一下任务数量、是否存在依赖、是否允许部分成功，以及有没有外部副作用。核心上我会把它拆成任务定义、执行状态和持久化日志三部分。正常流程先讲一遍，然后重点处理重试、幂等和恢复。”说着说着，你就有时间继续想了。"))),
    h("section", { class: "stack" }, h("h2", null, "急救训练：四轮约三小时"), h("div", { class: "hubs" }, plan.map(([href, when, t, d, n]) => h("a", { class: "panel hub", href: "#" + href }, h("div", { class: "eyebrow" }, when), h("h2", null, t), h("p", { class: "small muted" }, d), h("div", { class: "small faint num" }, `已练 ${n} 题`))))),
    h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "模式索引"), h("span", { class: "small faint" }, "推荐顺序：P7 → P8 → P5 → P6 → P2 → P3 → P4 → 设计题；每题最该记住的是两个核心状态")),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable sd-table" }, h("thead", null, h("tr", null, ["", "题目", "本质", "两个核心状态", "①", "②", "④"].map(x => h("th", null, x)))), h("tbody", null, rows)))),
    h("section", { class: "panel" }, h("h2", null, "设计题 = 积木的组合"),
      h("div", { class: "stack" }, SDD.designs.map(d => h("div", { class: "row sd-compose" }, h("a", { href: "#sd-" + d.id, class: "sd-dlink" }, (d.priority ? "★ " : "") + d.title), h("span", { class: "faint" }, "←"), d.composes.map(c => sdBlock(c) ? h("a", { class: "chip", href: "#sd-" + c }, `${c.toUpperCase()} ${sdBlock(c).title}`) : ""), h("span", { class: "small faint num" }, `口述 ${(a.s3[d.id] || []).length} 遍`))))),
    h("section", { class: "panel" }, h("h2", null, "怎么判断真的练出来了"), h("p", { class: "small muted" }, "按 P2–P8 七道核心题统计，数据来自你在四个阶段里的练习记录。"),
      h("div", { class: "stack", style: "gap:8px" }, crit.map(c => h("div", { class: "sd-crit" }, h("span", null, c.t), h("div", { class: "bar", title: c.how }, h("i", { style: `width:${c.n / Math.max(1, c.total) * 100}%` })), h("span", { class: "num small" }, `${c.n} / ${c.total}`))))));
}

// ----- 积木题 / 设计题详情 -----
function sdBlockView(b) {
  const lab = (typeof LABS !== "undefined" ? LABS : []).find(l => l.id === b.lab);
  const sec = (title, ...kids) => h("details", { class: "qa sd-sec" }, h("summary", null, title), h("div", { class: "stack", style: "gap:8px;margin-top:8px" }, ...kids));
  return sdPage("", `${b.id.toUpperCase()} ${b.title}`, null,
    h("section", { class: "panel" }, h("div", { class: "eyebrow" }, "题目"), mdEl(b.statement),
      h("div", { class: "row" }, h("a", { class: "btn sm", href: "#sd-s1", onclick: () => LS.set("tiyan:sd:s1cur", b.id) }, "① 先自己识别"), h("a", { class: "btn sm", href: "#sd-s2", onclick: () => LS.set("tiyan:sd:s2cur", b.id) }, "② 口述这道题"), lab ? h("a", { class: "btn primary sm", href: "#lab-" + lab.id.replace(/^lab-/, "") }, "写代码（浏览器里跑测试）") : "")),
    h("p", { class: "small muted" }, "下面是答案。先合上自己想：两个核心状态是什么？最重要的不变量是什么？"),
    sec("本质与触发信号", h("p", null, h("b", null, b.essence)), sdList(b.triggers)),
    sec("两个核心状态", sdStates(b), b.extra_states && b.extra_states.length ? h("div", { class: "small muted" }, "辅助状态：", b.extra_states.map(s => `${s.name}（${s.desc}）`).join("；")) : ""),
    sec("不变量（第一条最重要）", sdList(b.invariants)),
    sec("状态变化", mdEl(b.transitions)),
    sec("重复、失败、并发、超时", h("ul", { class: "mock-ul" }, b.failures.map(f => h("li", null, h("b", null, f.case), "：", f.handle)))),
    sec("最小例子走一遍", mdEl(b.walkthrough)),
    sec("口述参考（1 + 2 + 2 分钟）", h("h3", null, "核心结构"), mdEl(b.oral.structure), h("h3", null, "正常流程"), mdEl(b.oral.flow), h("h3", null, "易错点"), mdEl(b.oral.pitfalls)),
    sec("进阶追问", ...b.followups.map(x => { const d = h("details", { class: "qa" }, h("summary", null, x.q)); d.append(mdEl(x.a, "small")); return d; })),
    sec("易错点与复杂度", sdList(b.pitfalls), h("p", { class: "small muted" }, b.complexity)),
    sec("换个业务背景还认得出吗", h("ul", { class: "mock-ul" }, b.variants.map(v => h("li", null, v.context, h("div", { class: "small faint" }, v.note))))));
}
function sdDesignView(d) {
  return sdPage("", (d.priority ? "★ " : "") + d.title, null,
    h("section", { class: "panel" }, h("div", { class: "eyebrow" }, "题目"), mdEl(d.statement),
      h("div", { class: "row" }, h("span", { class: "small faint" }, "由这些积木组成："), d.composes.map(c => sdBlock(c) ? h("a", { class: "chip", href: "#sd-" + c }, `${c.toUpperCase()} ${sdBlock(c).title}`) : "")),
      h("div", { class: "row" }, h("a", { class: "btn primary sm", href: "#sd-s3", onclick: () => LS.set("tiyan:sd:s3cur", d.id) }, "③ 口述这道题"))),
    h("details", { class: "qa" }, h("summary", null, "卡住时怎么开口"), mdEl(d.opening)),
    ...d.steps.map((s, i) => h("details", { class: "qa sd-sec" }, h("summary", null, `${i + 1}. ${s.title}（${s.minutes} 分钟）`), h("p", { class: "small muted" }, s.prompt), h("div", { class: "small" }, "得分点："), sdList(s.points), mdEl(s.reference))),
    h("details", { class: "qa sd-sec" }, h("summary", null, "进阶追问"), ...d.followups.map(x => { const e = h("details", { class: "qa" }, h("summary", null, x.q)); e.append(mdEl(x.a, "small")); return e; })),
    h("details", { class: "qa sd-sec" }, h("summary", null, "常见设计错误"), sdList(d.pitfalls)),
    h("details", { class: "qa sd-sec" }, h("summary", null, "同类题"), sdList(d.variants)));
}

// ----- ① 识别模式：只看题目，5 分钟写状态 / 不变量 / 失败情况 -----
function sdStage1() {
  const list = sdOrdered();
  let cur = LS.get("tiyan:sd:s1cur", list[0].id);
  if (!sdBlock(cur)) cur = list[0].id;
  const box = h("div", { class: "stack" });
  const side = h("aside", { class: "panel sd-side" });
  const draw = () => {
    const b = sdBlock(cur), a = SDS.all(), rec = a.s1[b.id];
    LS.set("tiyan:sd:s1cur", cur);
    box.textContent = ""; side.textContent = "";
    side.append(h("div", { class: "eyebrow" }, "题目顺序"), h("ol", { class: "sd-order" }, list.map((x, i) => h("li", { class: x.id === cur ? "on" : "" }, h("a", { href: "#sd-s1", onclick: e => { e.preventDefault(); cur = x.id; draw(); } }, `${i < SD_CORE.length ? "" : "（扩展）"}第 ${i + 1} 题`), a.s1[x.id] ? h("span", { class: "sd-ok" }, " ✓") : ""))));
    const timer = countdown(300);
    const f = k => { const t = h("textarea", { class: "mock-input", id: `s1-${b.id}-${k}`, style: "min-height:90px" }); t.value = LS.get(`tiyan:sd:s1d:${b.id}:${k}`, ""); t.addEventListener("input", () => { if (!timer.used()) timer.start(); LS.set(`tiyan:sd:s1d:${b.id}:${k}`, t.value); }); return t; };
    const fs = { states: f("states"), invariants: f("invariants"), failures: f("failures") };
    const hint = h("div", { class: "hint-ladder" });
    let hints = 0;
    const hintBtn = h("button", { class: "btn sm", type: "button" }, "写不出来，看提示");
    hintBtn.addEventListener("click", () => {
      hints++;
      if (hints === 1) hint.append(h("div", { class: "hint" }, h("b", null, "提示 1"), "本质：" + b.essence));
      if (hints === 2) { hint.append(h("div", { class: "hint" }, h("b", null, "提示 2"), "两个核心状态叫：" + b.states.map(s => s.name).join("、"))); hintBtn.disabled = true; }
    });
    const reveal = h("div", { class: "stack" });
    const submit = h("button", { class: "btn primary sm", type: "button" }, "写完了，对照答案");
    const marks = { states: null, invariants: null, failures: null };
    submit.addEventListener("click", () => {
      const secs = timer.stop() || 0;
      submit.disabled = true;
      const save = () => SDS.put("s1", b.id, { secs, hints, self: { ...marks } });
      const col = (title, user, key, ref) => h("div", { class: "sd-cmp" }, h("h3", null, title), h("div", { class: "sd-cmp-grid" }, h("div", null, h("div", { class: "small faint" }, "你写的"), h("div", { class: "sd-user" }, user || "（没写）")), h("div", null, h("div", { class: "small faint" }, "参考"), ref)),
        h("div", { class: "row" }, h("span", { class: "small muted" }, "自评："), selfMark(v => { marks[key] = v; save(); }, null)));
      reveal.append(
        h("div", { class: "callout blue" }, h("b", null, `${b.id.toUpperCase()} ${b.title}`), `　用时 ${fmtSec(secs).replace("+", "")}${hints ? `，看了 ${hints} 级提示` : ""}。本质：${b.essence}`),
        col("状态", fs.states.value, "states", h("div", null, sdStates(b), b.extra_states && b.extra_states.length ? h("div", { class: "small muted" }, "辅助：" + b.extra_states.map(s => s.name).join("、")) : "")),
        col("不变量", fs.invariants.value, "invariants", sdList(b.invariants)),
        col("失败情况", fs.failures.value, "failures", h("ul", { class: "mock-ul" }, b.failures.map(x => h("li", null, h("b", null, x.case), "：", x.handle)))),
        h("details", { class: "qa" }, h("summary", null, "状态变化"), mdEl(b.transitions)));
      const ai = aiBox();
      const aiBtn = h("button", { class: "btn sm", type: "button" }, "让 AI 判一下");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是系统设计面试官。学习者只看题目，写下了这道题的核心状态、不变量和失败情况。请对照参考答案判分，指出缺了什么、哪里不准。
【题目】${b.statement}
【参考】核心状态：${b.states.map(s => s.name + "（" + s.desc + "）").join("；")}；不变量：${b.invariants.join("；")}；失败情况：${b.failures.map(x => x.case + "→" + x.handle).join("；")}
【学习者】状态：${fs.states.value || "（空）"}\n不变量：${fs.invariants.value || "（空）"}\n失败情况：${fs.failures.value || "（空）"}
意思对即可，名字不同没关系。评分档位：9–10 全对且有自己的洞见；7–8.5 基本对；5–6.5 抓到一半；3–4.5 大部分缺失；0–2.5 基本没写。
只返回 JSON：{"states": {"score": 8, "comment": "一句话"}, "invariants": {"score": 6, "comment": ""}, "failures": {"score": 5, "comment": ""}, "overall": 6.5, "missed": ["最关键的遗漏（具体）"], "tip": "下次看到这类题，先想到什么"}`, r => {
        ai.append(scoreLine(Number(r.overall) || 0), h("ul", { class: "ex-points" }, [["状态", r.states], ["不变量", r.invariants], ["失败情况", r.failures]].map(([t, x]) => h("li", { class: (x && x.score >= 7) ? "hit" : (x && x.score >= 4) ? "part" : "miss" }, h("b", null, `${t} ${x ? x.score : "-"}`), h("span", null, x ? x.comment : "")))),
          r.missed && r.missed.length ? h("div", null, h("h3", null, "最关键的遗漏"), sdList(arrStr(r.missed, 5))) : "", r.tip ? h("div", { class: "callout blue" }, h("b", null, "下次先想到："), String(r.tip)) : "");
        SDS.put("s1", b.id, { ai: Number(r.overall) || 0 });
      }));
      const idx = list.indexOf(b);
      reveal.append(h("div", { class: "row" }, aiBtn, list[idx + 1] ? h("button", { class: "btn primary sm", type: "button", onclick: () => { cur = list[idx + 1].id; draw(); window.scrollTo(0, 0); } }, "下一题 →") : h("a", { class: "btn primary sm", href: "#sd-s2" }, "去第二轮：口述 →"), h("a", { class: "btn ghost sm", href: "#sd-" + b.id }, "看完整讲解")), ai);
      LS.del(`tiyan:sd:s1d:${b.id}:states`); LS.del(`tiyan:sd:s1d:${b.id}:invariants`); LS.del(`tiyan:sd:s1d:${b.id}:failures`);
      save();
    });
    box.append(h("section", { class: "panel" },
      h("div", { class: "spread" }, h("div", { class: "eyebrow" }, `第 ${list.indexOf(b) + 1} 题 · 只看题目，不看答案`), h("div", { class: "row" }, h("span", { class: "small faint" }, "建议 5 分钟"), timer.el, h("button", { class: "btn ghost sm", type: "button", onclick: () => timer.start() }, "开始计时"))),
      mdEl(b.statement),
      rec ? h("div", { class: "small faint" }, `上次：用时 ${fmtSec(rec.secs || 0).replace("+", "")}，练过 ${rec.n} 次`) : ""),
      h("div", { class: "sd-three" },
        h("label", { class: "card-f" }, h("b", null, "状态"), h("span", { class: "small faint" }, "最核心的两个状态变量，各存什么"), fs.states),
        h("label", { class: "card-f" }, h("b", null, "不变量"), h("span", { class: "small faint" }, "任何时候都必须成立的条件"), fs.invariants),
        h("label", { class: "card-f" }, h("b", null, "失败情况"), h("span", { class: "small faint" }, "重复、失败、并发、超时怎么办"), fs.failures)),
      h("div", { class: "row" }, submit, hintBtn), hint, reveal);
  };
  draw();
  return sdPage("sd-s1", "第一轮：只练识别模式", "每题只看题目，5 分钟内在下面写：状态、不变量、失败情况。写不出来先看提示，不要直接看答案。开始打字时自动计时。", h("div", { class: "sd-grid" }, box, side));
}

// ----- ② 口述积木题：1 + 2 + 2 + 1 分钟 -----
function sdStage2() {
  const list = sdOrdered();
  let cur = LS.get("tiyan:sd:s2cur", SD_CORE.find(id => sdBlock(id) && id !== "p7" && id !== "p8") || list[0].id);
  if (!sdBlock(cur)) cur = list[0].id;
  const box = h("div", { class: "stack" });
  const side = h("aside", { class: "panel sd-side" });
  const SEGS = [["structure", "核心结构", 60, "两个核心状态是什么、各存什么、最重要的不变量"], ["flow", "正常流程", 120, "一步步讲状态怎么变化"], ["pitfalls", "易错点", 120, "最容易写错的地方，以及会出什么问题"], ["followup", "进阶追问", 60, ""]];
  const draw = () => {
    const b = sdBlock(cur), a = SDS.all();
    LS.set("tiyan:sd:s2cur", cur);
    box.textContent = ""; side.textContent = "";
    side.append(h("div", { class: "eyebrow" }, "选题"), h("ol", { class: "sd-order" }, list.map(x => h("li", { class: x.id === cur ? "on" : "" }, h("a", { href: "#sd-s2", onclick: e => { e.preventDefault(); cur = x.id; draw(); } }, `${x.id.toUpperCase()} ${x.title}`), a.s2[x.id] ? h("span", { class: "sd-ok" }, " ✓") : ""))));
    const fq = b.followups[Math.floor(Math.random() * b.followups.length)];
    let si = -1;
    const texts = {};
    const stage = h("div", { class: "stack" });
    const total = countdown(480);
    const start = h("button", { class: "btn primary", type: "button" }, "开始口述（共 6 分钟）");
    const segBar = h("div", { class: "sd-segbar" }, SEGS.map(([k, t, s]) => h("span", { "data-k": k }, `${t} ${s / 60}′`)));
    const next = () => {
      if (si >= 0) texts[SEGS[si][0]] = stage.querySelector("textarea").value;
      si++;
      $$("span", segBar).forEach((x, i) => { x.classList.toggle("on", i === si); x.classList.toggle("done", i < si); });
      stage.textContent = "";
      if (si >= SEGS.length) return finish();
      const [k, t, sec, guide] = SEGS[si];
      const tm = countdown(sec).start();
      const ta = h("textarea", { class: "mock-input", id: `s2-${b.id}-${k}`, style: "min-height:120px", placeholder: "可以出声口述，同时在这里记几个关键词；也可以用语音输入转成文字。" });
      const vb = h("button", { class: "btn sm", type: "button", hidden: !SpeechRec }, "语音输入");
      const vs = h("span", { class: "small muted" });
      vb.addEventListener("click", () => toggleVoice(ta, vb, vs));
      stage.append(h("div", { class: "spread" }, h("h2", null, `${si + 1}. ${t}`), tm.el),
        k === "followup" ? h("div", { class: "callout blue" }, h("b", null, "面试官追问："), fq.q) : h("p", { class: "muted" }, guide),
        ta, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: () => { stopVoice(); tm.stop(); next(); } }, si < SEGS.length - 1 ? "下一段 →" : "说完了，对照参考"), vb, vs));
      ta.focus();
    };
    const finish = () => {
      const secs = total.stop();
      const marks = {};
      const save = () => SDS.put("s2", b.id, { secs, self: { ...marks } });
      const refs = { structure: b.oral.structure, flow: b.oral.flow, pitfalls: b.oral.pitfalls, followup: fq.a };
      stage.append(h("div", { class: "callout blue" }, `${b.id.toUpperCase()} ${b.title}：总用时 ${fmtSec(secs).replace("+", "")}（目标 6–8 分钟）。逐段对照，诚实自评。`),
        ...SEGS.map(([k, t]) => h("div", { class: "sd-cmp" }, h("h3", null, k === "followup" ? `进阶追问：${fq.q}` : t), h("div", { class: "sd-cmp-grid" }, h("div", null, h("div", { class: "small faint" }, "你说的（记录）"), h("div", { class: "sd-user" }, texts[k] || "（没记）")), h("div", null, h("div", { class: "small faint" }, "参考"), mdEl(refs[k], "small"))),
          h("div", { class: "row" }, h("span", { class: "small muted" }, "自评："), selfMark(v => { marks[k] = v; save(); }, null)))));
      const ai = aiBox();
      const has = Object.values(texts).some(t => t && t.trim().length > 10);
      const aiBtn = h("button", { class: "btn sm", type: "button", disabled: !has, title: has ? "" : "没有文字记录，AI 没法评估；可以只用自评" }, "让 AI 评估我的口述");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是系统设计 / 编码面试官。学习者口述了一道积木题，分四段（下面是他的口述记录，可能是要点或语音转写，允许口语化）。请逐段对照参考评分，指出漏掉的关键点，并给出更好的说法。
【题目】${b.title}：${clip(b.statement, 1500)}
${SEGS.map(([k, t]) => `【${k === "followup" ? "进阶追问：" + fq.q : t}】\n学习者：${texts[k] || "（空）"}\n参考：${refs[k]}`).join("\n\n")}
评分档位：9–10 完整准确、表达清楚；7–8.5 基本到位；5–6.5 抓到一半；3–4.5 大部分缺失；0–2.5 基本没说。
只返回 JSON：{"segments": [{"key": "structure", "score": 7, "missed": ["漏掉的关键点"], "better": "更好的说法（2–4 句）"}], "overall": 7, "advice": "下一遍口述最该改的一点"}（segments 按 structure / flow / pitfalls / followup 顺序）`, r => {
        const segs = Array.isArray(r.segments) ? r.segments : [];
        ai.append(scoreLine(Number(r.overall) || 0), ...segs.map(x => { const t = (SEGS.find(s => s[0] === x.key) || [, x.key])[1]; return h("div", { class: "sd-cmp" }, h("div", { class: "row" }, h("b", null, t), h("span", { class: "num" }, `${x.score} 分`)), x.missed && x.missed.length ? sdList(arrStr(x.missed, 5)) : "", x.better ? mdEl(String(x.better), "small") : ""); }),
          r.advice ? h("div", { class: "callout blue" }, h("b", null, "下一遍最该改："), String(r.advice)) : "");
        SDS.put("s2", b.id, { ai: Number(r.overall) || 0 });
      }));
      const idx = SD_CORE.indexOf(b.id);
      const nxt = idx >= 0 && SD_CORE[idx + 1];
      stage.append(h("div", { class: "row" }, aiBtn, h("button", { class: "btn sm", type: "button", onclick: draw }, "再说一遍"), nxt ? h("button", { class: "btn primary sm", type: "button", onclick: () => { cur = nxt; draw(); window.scrollTo(0, 0); } }, "下一题 →") : h("a", { class: "btn primary sm", href: "#sd-s3" }, "去第三轮：设计题 →")), ai);
      save();
    };
    start.addEventListener("click", () => { start.remove(); total.start(); next(); });
    box.append(h("section", { class: "panel" },
      h("div", { class: "spread" }, h("h2", null, `${b.id.toUpperCase()} ${b.title}`), h("div", { class: "row" }, h("span", { class: "small faint" }, "总用时"), total.el)),
      h("details", { class: "qa" }, h("summary", null, "题目"), mdEl(b.statement)),
      segBar, h("p", { class: "small muted" }, "不要求默写代码。按段讲，到时间就进入下一段；最后一段会随机抽一个面试官追问。最好出声讲，同时在框里记关键词。"),
      start, stage));
  };
  draw();
  return sdPage("sd-s2", "第二轮：口述积木题", "每题 6–8 分钟：1 分钟讲核心结构，2 分钟讲正常流程，2 分钟讲易错点，1 分钟回答一个进阶追问。", h("div", { class: "sd-grid" }, box, side));
}

// ----- ③ 口述设计题：澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标 -----
function sdStage3() {
  let cur = LS.get("tiyan:sd:s3cur", (SDD.designs.find(d => d.priority) || SDD.designs[0]).id);
  if (!sdDesign(cur)) cur = SDD.designs[0].id;
  const box = h("div", { class: "stack" });
  const side = h("aside", { class: "panel sd-side" });
  const draw = () => {
    const d = sdDesign(cur), a = SDS.all();
    LS.set("tiyan:sd:s3cur", cur);
    box.textContent = ""; side.textContent = "";
    side.append(h("div", { class: "eyebrow" }, "设计题"), h("ol", { class: "sd-order" }, SDD.designs.map(x => h("li", { class: x.id === cur ? "on" : "" }, h("a", { href: "#sd-s3", onclick: e => { e.preventDefault(); cur = x.id; draw(); } }, (x.priority ? "★ " : "") + x.title), h("span", { class: "small faint num" }, ` ${(a.s3[x.id] || []).length} 遍`)))),
      d.priority ? h("p", { class: "small muted" }, `设计 1 至少完整说两遍：已完成 ${(a.s3[d.id] || []).length} 遍`) : "");
    const total = countdown(d.steps.reduce((n, s) => n + s.minutes * 60, 0));
    const texts = {};
    let si = -1;
    const stage = h("div", { class: "stack" });
    const segBar = h("div", { class: "sd-segbar" }, d.steps.map(s => h("span", null, `${SD_STEPS.find(x => x[0] === s.key)[1]} ${s.minutes}′`)));
    const start = h("button", { class: "btn primary", type: "button" }, `开始（约 ${d.steps.reduce((n, s) => n + s.minutes, 0)} 分钟）`);
    const next = () => {
      if (si >= 0) texts[d.steps[si].key] = stage.querySelector("textarea").value;
      si++;
      $$("span", segBar).forEach((x, i) => { x.classList.toggle("on", i === si); x.classList.toggle("done", i < si); });
      stage.textContent = "";
      if (si >= d.steps.length) return finish();
      const s = d.steps[si];
      const tm = countdown(s.minutes * 60).start();
      const ta = h("textarea", { class: "mock-input", id: `s3-${d.id}-${s.key}`, style: "min-height:140px", placeholder: "出声讲，同时记关键词；也可以用语音输入。" });
      const vb = h("button", { class: "btn sm", type: "button", hidden: !SpeechRec }, "语音输入");
      const vs = h("span", { class: "small muted" });
      vb.addEventListener("click", () => toggleVoice(ta, vb, vs));
      stage.append(h("div", { class: "spread" }, h("h2", null, `${si + 1}. ${s.title}`), tm.el), h("p", { class: "muted" }, s.prompt), ta,
        h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: () => { stopVoice(); tm.stop(); next(); } }, si < d.steps.length - 1 ? "下一步 →" : "讲完了，对照参考"), vb, vs));
      ta.focus();
    };
    const finish = () => {
      const secs = total.stop();
      const marks = {};
      const rec = { at: Date.now(), secs, self: marks };
      SDS.put("s3", d.id, rec, true);
      const resave = () => { const all = SDS.all(); const arr = all.s3[d.id] || []; if (arr.length) { arr[arr.length - 1].self = { ...marks }; LS.set("tiyan:sd", all); } };
      stage.append(h("div", { class: "callout blue" }, `总用时 ${fmtSec(secs).replace("+", "")}。这是你第 ${(SDS.all().s3[d.id] || []).length} 遍完整口述这道题。`),
        ...d.steps.map((s, i) => h("div", { class: "sd-cmp" }, h("h3", null, `${i + 1}. ${s.title}`),
          h("div", { class: "sd-cmp-grid" }, h("div", null, h("div", { class: "small faint" }, "你说的（记录）"), h("div", { class: "sd-user" }, texts[s.key] || "（没记）")), h("div", null, h("div", { class: "small faint" }, "得分点"), sdList(s.points), h("details", { class: "qa" }, h("summary", null, "参考回答"), mdEl(s.reference, "small")))),
          h("div", { class: "row" }, h("span", { class: "small muted" }, "自评："), selfMark(v => { marks[s.key] = v; resave(); }, null)))));
      const ai = aiBox();
      const has = Object.values(texts).some(t => t && t.trim().length > 10);
      const aiBtn = h("button", { class: "btn sm", type: "button", disabled: !has }, "让 AI 当面试官评估");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是资深系统设计面试官。学习者按“澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标”六步口述了一道设计题（下面是他的口述记录，允许口语化）。请逐步对照得分点评分，指出缺失，最后给出 2 个你会追问的问题。
【题目】${d.title}：${d.statement}
${d.steps.map(s => `【${s.title}】得分点：${s.points.join("；")}\n学习者：${texts[s.key] || "（空）"}`).join("\n\n")}
评分档位：9–10 完整且有取舍和数据；7–8.5 基本到位；5–6.5 抓到一半；3–4.5 大部分缺失；0–2.5 基本没说。
只返回 JSON：{"steps": [{"key": "clarify", "score": 7, "hit": [0, 2], "missed": ["缺失的点"]}], "overall": 6.5, "verdict": "整体评价一句话", "followups": ["面试官会追问的问题"], "advice": "下一遍最该改的一点"}（steps 按 clarify / objects / flow / failure / concurrency / metrics 顺序；hit 是得分点下标）`, r => {
        const steps = Array.isArray(r.steps) ? r.steps : [];
        ai.append(scoreLine(Number(r.overall) || 0, r.verdict ? h("span", { class: "small" }, String(r.verdict)) : ""),
          ...steps.map(x => { const s = d.steps.find(y => y.key === x.key); if (!s) return ""; const hit = Array.isArray(x.hit) ? x.hit.map(Number) : []; return h("div", { class: "sd-cmp" }, h("div", { class: "row" }, h("b", null, s.title), h("span", { class: "num" }, `${x.score} 分`)), h("ul", { class: "ex-points" }, s.points.map((p, i) => h("li", { class: hit.includes(i) ? "hit" : "miss" }, h("b", null, hit.includes(i) ? "说到" : "缺"), h("span", null, p)))), x.missed && x.missed.length ? sdList(arrStr(x.missed, 4)) : ""); }),
          r.followups && r.followups.length ? h("div", null, h("h3", null, "面试官接着会问"), sdList(arrStr(r.followups, 4))) : "",
          r.advice ? h("div", { class: "callout blue" }, h("b", null, "下一遍最该改："), String(r.advice)) : "");
        const all = SDS.all(); const arr = all.s3[d.id] || []; if (arr.length) { arr[arr.length - 1].ai = Number(r.overall) || 0; LS.set("tiyan:sd", all); }
      }));
      stage.append(h("div", { class: "row" }, aiBtn, h("button", { class: "btn primary sm", type: "button", onclick: draw }, "再完整说一遍"), h("a", { class: "btn ghost sm", href: "#sd-" + d.id }, "看完整参考")), ai);
    };
    start.addEventListener("click", () => { start.remove(); total.start(); next(); });
    box.append(h("section", { class: "panel" },
      h("div", { class: "spread" }, h("h2", null, (d.priority ? "★ " : "") + d.title), h("div", { class: "row" }, h("span", { class: "small faint" }, "总用时"), total.el)),
      mdEl(d.statement),
      h("div", { class: "row" }, h("span", { class: "small faint" }, "会用到的积木："), d.composes.map(c => sdBlock(c) ? h("a", { class: "chip", href: "#sd-" + c }, `${c.toUpperCase()} ${sdBlock(c).title}`) : "")),
      h("details", { class: "qa" }, h("summary", null, "不知道怎么开口？"), mdEl(d.opening)),
      segBar, start, stage));
  };
  draw();
  return sdPage("sd-s3", "第三轮：口述设计题", "每题严格按六步讲：澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标。每步有建议时长，到时间就往下走。设计 1 优先，至少完整说两遍。", h("div", { class: "sd-grid" }, box, side));
}

// ----- ④ 随机抽题：只看题目名，30 秒说出骨架 -----
function sdStage4() {
  let variantMode = LS.get("tiyan:sd:s4variant", false);
  const box = h("div", { class: "stack" });
  const stats = h("aside", { class: "panel sd-side" });
  const pool = () => sdOrdered();
  const pick = () => {
    const a = SDS.all();
    const weight = b => { const r = (a.s4[b.id] || []).slice(-1)[0]; if (!r) return 3; return r.marks.every(Boolean) && r.secs <= 30 ? 1 : 4; };
    const arr = pool().flatMap(b => Array(weight(b)).fill(b));
    return arr[Math.floor(Math.random() * arr.length)];
  };
  const drawStats = () => {
    const a = SDS.all();
    stats.textContent = "";
    const weak = pool().filter(b => { const r = (a.s4[b.id] || []).slice(-1)[0]; return !r || !r.marks.every(Boolean) || r.secs > 30; });
    stats.append(h("div", { class: "eyebrow" }, "召回情况（最近一次）"),
      h("table", { class: "ptable" }, h("tbody", null, pool().map(b => { const r = (a.s4[b.id] || []).slice(-1)[0]; return h("tr", null, h("td", { class: "mono small" }, b.id.toUpperCase()), h("td", { class: "small" }, b.title), h("td", { class: "num small " + (r ? (r.marks.every(Boolean) && r.secs <= 30 ? "sd-ok" : "sd-bad") : "faint") }, r ? `${r.secs}s ${r.marks.filter(Boolean).length}/4` : "—")); }))),
      h("p", { class: "small muted" }, weak.length ? `还没建立召回路径：${weak.map(b => b.id.toUpperCase()).join("、")}。抽题时会更常抽到它们。` : "全部题目都能在 30 秒内说全了。"));
  };
  const modeSeg = h("div", { class: "seg" }, [[false, "看题目名"], [true, "换皮模式（只给业务背景）"]].map(([v, t]) => { const b = h("button", { type: "button", class: variantMode === v ? "on" : "" }, t); b.addEventListener("click", () => { variantMode = v; LS.set("tiyan:sd:s4variant", v); $$("button", modeSeg).forEach(x => x.classList.remove("on")); b.classList.add("on"); }); return b; }));
  const round = () => {
    box.textContent = "";
    const b = pick();
    const v = variantMode ? b.variants[Math.floor(Math.random() * b.variants.length)] : null;
    const timer = countdown(30).start();
    const FIELDS = [["states", "两个核心状态"], ["invariant", "一个最重要的不变量"], ["failure", "一个失败场景"], ["followup", "一个扩展追问"]];
    const ins = FIELDS.map(([k, t], i) => { const x = h("input", { id: `s4-${k}`, class: "mock-input", style: "min-height:0;padding:8px 10px", placeholder: t, autocomplete: "off" }); x.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); if (i < FIELDS.length - 1) ins[i + 1].focus(); else done(); } }); return x; });
    const doneBtn = h("button", { class: "btn primary sm", type: "button" }, "说完了（Enter）");
    const res = h("div", { class: "stack" });
    let finished = false;
    const done = () => {
      if (finished) return; finished = true;
      const secs = timer.stop();
      doneBtn.disabled = true; ins.forEach(x => { x.disabled = true; });
      const marks = [0, 0, 0, 0];
      const save = () => { const all = SDS.all(); const arr = all.s4[b.id] || []; const last = arr[arr.length - 1]; if (last && last.at === stamp) { last.marks = marks.slice(); LS.set("tiyan:sd", all); } };
      const stamp = Date.now();
      SDS.put("s4", b.id, { at: stamp, secs, marks: marks.slice(), variant: !!v }, true);
      const refs = [sdStates(b), h("div", null, b.invariants[0]), sdList(b.failures.slice(0, 3).map(x => `${x.case}：${x.handle}`)), sdList(b.followups.slice(0, 3).map(x => x.q))];
      res.append(h("div", { class: "callout " + (secs <= 30 ? "blue" : "") }, h("b", null, `${b.id.toUpperCase()} ${b.title}`), `　用时 ${secs} 秒${secs > 30 ? "（超过 30 秒：召回路径还没建立）" : ""}。逐项对照，说对了就点“对”。`),
        ...FIELDS.map(([k, t], i) => h("div", { class: "sd-cmp" }, h("div", { class: "spread" }, h("b", null, t), (() => { const seg = h("div", { class: "seg sd-mark" }, [[1, "对"], [0, "不对 / 没说"]].map(([val, label]) => { const btn = h("button", { type: "button", class: val === 0 ? "on" : "" }, label); btn.addEventListener("click", () => { marks[i] = val; $$("button", seg).forEach(x => x.classList.remove("on")); btn.classList.add("on"); save(); drawStats(); }); return btn; })); return seg; })()),
          h("div", { class: "sd-cmp-grid" }, h("div", { class: "sd-user" }, ins[i].value || "（没写）"), h("div", null, refs[i])))),
        h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: round }, "再抽一题"), h("a", { class: "btn ghost sm", href: "#sd-" + b.id }, "看这题的完整讲解")));
      drawStats();
    };
    doneBtn.addEventListener("click", done);
    box.append(h("section", { class: "panel sd-draw" },
      h("div", { class: "spread" }, h("div", { class: "eyebrow" }, v ? "换皮模式：这是哪个模式？" : "题目"), timer.el),
      v ? h("p", { class: "sd-prompt" }, v.context) : h("p", { class: "sd-prompt" }, h("span", { class: "mono faint" }, b.slug), h("br"), b.title),
      h("div", { class: "sd-four" }, ins), h("div", { class: "row" }, doneBtn, h("span", { class: "small muted" }, "可以出声说，再在框里写关键词；30 秒到了也可以继续，但会记为超时。")), res));
    ins[0].focus();
  };
  drawStats();
  const controls = h("section", { class: "panel" }, h("p", { class: "muted" }, "点「抽一题」后开始 30 秒倒计时。只看题目名（或者只看换了业务背景的题面），说出两个核心状态、一个最重要的不变量、一个失败场景、一个扩展追问。说不出来的题会更常被抽到。"),
    h("div", { class: "row" }, modeSeg, h("button", { class: "btn primary", type: "button", onclick: round }, "抽一题")));
  return sdPage("sd-s4", "第四轮：随机抽题", "关掉讲解，只看目录名：30 秒内说出两个核心状态、一个最重要不变量、一个失败场景、一个扩展追问。", h("div", { class: "sd-grid" }, h("div", { class: "stack" }, controls, box), stats));
}
