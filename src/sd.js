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
const SD_TABS = [["sd", "总览"], ["sd-kit", "机制工具箱"], ["sd-s1", "① 识别模式"], ["sd-s2", "② 口述积木题"], ["sd-s3", "③ 口述设计题"], ["sd-s4", "④ 随机抽题"], ["sd-s5", "⑤ 压力追问"]];
function sdTabs(cur) { return h("nav", { class: "page-tabs" }, SD_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t))); }
function sdPage(cur, title, lede, ...body) {
  return h("div", { class: "page wide sd-page" }, h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "设计编码"), h("h1", null, title), lede ? h("p", { class: "lede" }, lede) : ""), sdTabs(cur), ...body, sdTutorEl());
}

// ----- AI 老师：查漏补缺。整个模块共用一段对话，能看到当前题目、你的作答和最近一次评估 -----
const TB = SDD.toolbox || {};
const SD_COACH_RULE = `点评要像资深面试官带徒弟：直接、具体，落到哪一层 / 什么状态 / 什么字段 / 什么数字，不说套话。重点是查漏补缺：他哪里想错了（概念错误、因果颠倒、机制用错地方）、哪里思路不对或漏了、哪里可以更好，以及下次遇到类似场景该怎么想。如果他过度设计（加了题目并不需要的机制），也要指出。`;
const SD_COACH_JSON = `"wrong": ["哪里想错了：先引用他的说法，再说错在哪、正确的理解是什么（没有就给空数组）"], "optimize": ["哪里可以更好：更准确的说法、更简单的方案或更好的取舍"], "next_time": ["下次遇到类似场景的思考步骤，3–5 步，可复用"], "best_practice": "一条最值得记住的最佳实践（一句话）"`;
const SD_TEACHER = `你是「题眼」设计编码模块里的 AI 老师，帮学习者准备 Agent / Harness / 后端系统设计与编码面试（社招、资深面试官会连续追问）。
你的核心任务是查漏补缺：
1. 先指出他哪里想错了（概念错误、因果颠倒、机制用错地方），引用他的原话再纠正；
2. 再指出思路上漏了什么（状态、不变量、失败模式、规模假设、权威状态、指标口径）；
3. 说哪里可以更好（更简单的方案、更准确的说法、更好的取舍）；
4. 最后给“下次遇到类似场景怎么想”的可复用步骤和一条最佳实践。
讲设计时用因果链：业务约束 → 失败模式 → 机制 → 代价 → 兜底 → 指标；讲选型用五句：约束 / 选择 / 备选 / 为什么不选备选 / 缺点 + 兜底 + 指标；讲指标先说统计对象、分子、分母、排除项和口径陷阱。
不是每个系统都需要所有机制：他过度设计时也要指出。
风格：先给结论，再展开；具体到哪一层、什么状态、什么字段、什么数字；不堆名词，不说套话。一般控制在 600 字以内，他要求详细再展开。他让你当面试官时，一次只问一个问题，等他回答再点评。
站内资料（12 道积木题、设计题、机制工具箱）用 search_notes / read_section 查，引用时说出处；站内没有的用通用工程知识回答。`;
const SD_CTX = { where: "", topic: null, attempt: "", review: "" };
let SD_LIB = null, SD_TUTOR = null;
function sdBlockText(b) {
  return [`积木题 ${b.id.toUpperCase()} ${b.title}`, "题目：" + b.statement, "本质：" + b.essence, "触发信号：" + b.triggers.join("；"),
    "两个核心状态：" + b.states.map(s => `${s.name}（${s.desc}）`).join("；"), "不变量：" + b.invariants.join("；"), "状态变化：" + b.transitions,
    "失败情况：" + b.failures.map(f => `${f.case}→${f.handle}`).join("；"), "口述参考：" + [b.oral.structure, b.oral.flow, b.oral.pitfalls].join("\n"),
    "进阶追问：\n" + b.followups.map(x => `问：${x.q}\n答：${x.a}`).join("\n"), "易错点：" + b.pitfalls.join("；"), "换皮：" + b.variants.map(v => v.context).join("；")].join("\n");
}
function sdDesignText(d) {
  return [`设计题 ${d.id} ${d.title}`, "题目：" + d.statement, "开口模板：" + d.opening,
    ...d.steps.map(s => `【${s.title}】得分点：${s.points.join("；")}\n参考：${s.reference}`),
    "进阶追问：\n" + d.followups.map(x => `问：${x.q}\n答：${x.a}`).join("\n"), "常见错误：" + d.pitfalls.join("；"),
    d.pressure ? "压力追问：\n" + d.pressure.map(p => `问：${p.q}\n答：${p.a}`).join("\n") : "",
    d.metrics ? "指标口径：\n" + d.metrics.map(m => `${m.name}：分子 ${m.numerator}；分母 ${m.denominator}；排除 ${m.exclude}；陷阱 ${m.traps.join("、")}`).join("\n") : "",
    d.choices ? "技术选型：\n" + d.choices.map(c => `${c.topic}：约束 ${c.constraint}；选择 ${c.choice}；备选 ${c.alternatives}；不选原因 ${c.why_not}；缺点与兜底 ${c.downside}；指标 ${c.metric}`).join("\n") : ""].filter(Boolean).join("\n");
}
function sdLib() {
  if (SD_LIB) return SD_LIB;
  const items = SDD.blocks.map(b => ({ id: b.id, where: `积木题 › ${b.id.toUpperCase()} ${b.title}`, text: sdBlockText(b) }))
    .concat(SDD.designs.map(d => ({ id: d.id, where: `设计题 › ${d.title}`, text: sdDesignText(d) })));
  (TB.mechanisms || []).forEach((m, i) => items.push({ id: "mech" + i, where: `机制工具箱 › ${m.name}`, text: `${m.name}\n什么信号出现时用：${m.signal}\n解决什么风险：${m.solves}\n怎么做：${m.how}\n代价：${m.cost}` }));
  (TB.dims || []).forEach((x, i) => items.push({ id: "dim" + i, where: `架构工具箱 › ${x.dim}`, text: x.items.join("\n") + "\n开场：" + x.say }));
  if (TB.templates) items.push({ id: "tpl", where: "机制工具箱 › 回答模板", text: [TB.templates.chain.name, ...TB.templates.chain.steps, "反例：" + TB.templates.chain.bad, "正例：" + TB.templates.chain.good, TB.templates.choice.name, ...TB.templates.choice.steps, "例：" + TB.templates.choice.example].join("\n") });
  if (TB.styles) items.push({ id: "styles", where: "机制工具箱 › 面试官追问风格", text: TB.styles.map(s => `${s.kind}：${s.asks.join(" / ")}\n怎么答：${s.how}`).join("\n") });
  if (TB.security) items.push({ id: "security", where: "机制工具箱 › 安全清单", text: TB.security.map(s => `${s.item}：${s.detail}`).join("\n") });
  if (TB.pressure) items.push({ id: "pressure", where: "机制工具箱 › 压力追问 10 问", text: TB.pressure.map(p => `${p.q}\n想听到：${p.wants}\n常见失分：${p.trap}`).join("\n") });
  (TB.metric_drills || []).forEach((m, i) => items.push({ id: "metric" + i, where: `指标口径 › ${m.name}`, text: `${m.ask}\n分子：${m.numerator}\n分母：${m.denominator}\n排除：${m.exclude}\n陷阱：${m.traps.join("；")}\n参考：${m.answer}` }));
  if (TB.formula) items.push({ id: "formula", where: "机制工具箱 › 总纲", text: [TB.formula, TB.formula_note, TB.principle, (TB.metric_rules || []).join("\n")].join("\n") });
  return SD_LIB = new Library(items);
}
function sdTopicText(t) { return !t ? "" : t.states ? sdBlockText(t) : t.steps ? sdDesignText(t) : String(t.text || ""); }
function sdFocus(where, topic) {
  SD_CTX.where = where;
  if (topic !== undefined && topic !== SD_CTX.topic) { SD_CTX.topic = topic; SD_CTX.attempt = ""; SD_CTX.review = ""; }
  if (SD_TUTOR) SD_TUTOR.label();
}
function sdTutorEl() {
  const lib = sdLib();
  const outline = SDD.blocks.map(b => `- ${b.id} ${b.title}`).concat(SDD.designs.map(d => `- ${d.id} ${d.title}`), (TB.mechanisms || []).map((m, i) => `- mech${i} ${m.name}`), ["- tpl 回答模板", "- styles 面试官追问风格", "- security 安全清单", "- pressure 压力追问 10 问"], (TB.metric_drills || []).map((m, i) => `- metric${i} 指标口径：${m.name}`)).join("\n");
  const chat = new Chat({
    key: "sd:tutor",
    context: () => SD_TEACHER + "\n\n【站内资料目录（id 可直接 read_section）】\n" + outline
      + (SD_CTX.where ? `\n\n【学习者现在在】${SD_CTX.where}` : "")
      + (SD_CTX.topic ? "\n\n【当前题目与参考答案】（学习者没要求就不要整段照抄参考，先引导）\n" + clip(sdTopicText(SD_CTX.topic), 5000) : "")
      + (SD_CTX.attempt ? "\n\n【学习者刚才的作答】\n" + clip(SD_CTX.attempt, 3000) : "")
      + (SD_CTX.review ? "\n\n【刚才 AI 评估的结果】\n" + clip(SD_CTX.review, 2500) : ""),
    placeholder: "哪里没想通就问，比如“为什么失败不能缓存？”“这题我说用分布式锁，哪里不对？”",
    intro: "我能看到你正在练的题、你的作答和最近一次评估。写完 / 说完之后点「帮我查漏补缺」，我会告诉你哪里想错了、漏了什么、怎么说更好，以及下次遇到类似场景该怎么想。",
    actions: [
      { label: "帮我查漏补缺", run: c => c.send(SD_CTX.attempt ? "根据我刚才的作答和这道题的参考，帮我查漏补缺：① 哪里想错了（引用我的说法再纠正）② 漏了什么 ③ 哪里可以更好 ④ 下次遇到类似场景怎么想（3–5 步）⑤ 一条最佳实践。最后挑最严重的一个问题，出一个小场景让我马上再答一次。" : "我还没有作答。请针对当前这道题，先问我 3 个检查问题（核心状态 / 最重要的不变量 / 最难的失败场景），一次一个，我答完你再点评、查漏补缺。", { label: "帮我查漏补缺" }) },
      { label: "讲透这道题", run: c => c.send("用因果链讲透当前这道题的参考设计：为什么是这些核心状态 / 机制；每个机制解决什么失败模式、代价是什么、怎么兜底、用什么指标证明。最后说面试时最容易被追问的 2 个点和答法。", { label: "讲透这道题" }) },
      { label: "像面试官追问我", run: c => c.send("你现在是资深面试官。针对当前这道题，按压力追问的方式问我一个最可能被深挖的问题（比如最坏时刻挂了、多实例重复执行、10 倍流量、指标口径），只问问题，不要给答案。我回答后你再点评：哪里想错了、更好的答法、下次怎么想，然后接着追问一层。", { label: "像面试官追问我" }) },
      { label: "下次类似场景怎么做", run: c => c.send("把当前这道题背后的通用套路总结成一张“下次遇到类似场景”的检查清单：触发信号 → 先想到的状态和机制 → 必问的澄清问题 → 最容易错的点 → 该报的指标。再举两个看起来不同、本质相同的业务场景。", { label: "下次类似场景怎么做" }) },
      { label: "换皮考我", run: c => c.send("给我出一个换了业务背景、但本质是当前这道题同一模式的新题面。只给题面，让我先说核心状态、最重要的不变量和最难的失败场景；我答完你再点评、查漏补缺。", { label: "换皮考我" }) },
    ],
  });
  const rawSend = chat.send.bind(chat);
  chat.send = (prompt, o = {}) => {
    const hits = lib.search(prompt, 2);
    if (hits.length) prompt += "\n\n【可能相关的站内资料（本地检索，可能不全）】\n" + hits.map(c => `[${c.id}]【${c.where}】\n${clip(c.text, 1200)}`).join("\n\n");
    return rawSend(prompt, Object.assign({ tools: libTools(lib) }, o));
  };
  S.liveChats = [chat];
  const ctxEl = h("span", { class: "small faint sd-drawer-ctx" });
  const open0 = LS.get("tiyan:sd:tutor", false);
  const drawer = h("aside", { class: "sd-drawer" + (open0 ? " open" : ""), "aria-label": "AI 老师" },
    h("div", { class: "sd-drawer-h" }, h("div", { class: "stack", style: "gap:0" }, h("b", null, "AI 老师 · 查漏补缺"), ctxEl), h("button", { class: "btn ghost sm", type: "button", onclick: () => setOpen(false) }, "收起")), chat.el);
  const fab = h("button", { class: "btn primary sd-fab", type: "button", onclick: () => setOpen(!drawer.classList.contains("open")) }, "AI 老师");
  const setOpen = v => { drawer.classList.toggle("open", v); document.body.classList.toggle("sd-tutor-open", v); LS.set("tiyan:sd:tutor", v); if (v) setTimeout(() => { chat.scroll(); chat.ta.focus(); }, 60); };
  document.body.classList.toggle("sd-tutor-open", open0);
  const label = () => { const t = SD_CTX.topic; ctxEl.textContent = [SD_CTX.where, t ? (t.states ? `${t.id.toUpperCase()} ${t.title}` : t.title || "") : ""].filter(Boolean).join(" · ") || "设计编码"; };
  label();
  SD_TUTOR = { chat, setOpen, label };
  onLeave(() => { S.liveChats = []; if (CHAT_LIVE[chat.key] === chat) delete CHAT_LIVE[chat.key]; SD_TUTOR = null; document.body.classList.remove("sd-tutor-open"); });
  return h("div", { class: "sd-tutor" }, fab, drawer);
}
function sdTutorAsk(prompt, label) { if (!SD_TUTOR) return; SD_TUTOR.setOpen(true); SD_TUTOR.chat.send(prompt, { label }); }
// 统一的“查漏补缺”展示：想错了 / 可以更好 / 下次怎么想 / 最佳实践 + 接着问老师
function coachEl(r) {
  const wrong = arrStr(r.wrong, 5), opt = arrStr(r.optimize, 5), nxt = arrStr(r.next_time, 6);
  return h("div", { class: "stack sd-coach" },
    wrong.length ? h("div", { class: "callout" }, h("b", null, "哪里想错了"), sdList(wrong)) : "",
    opt.length ? h("div", null, h("h3", null, "哪里可以更好"), sdList(opt)) : "",
    nxt.length ? h("div", { class: "callout blue" }, h("b", null, "下次遇到类似场景，这样想"), h("ol", { class: "mock-ul" }, nxt.map(x => h("li", null, x)))) : "",
    r.best_practice ? h("div", { class: "sd-bp" }, h("b", null, "最佳实践　"), String(r.best_practice)) : "",
    h("div", { class: "row" }, h("button", { class: "btn sm", type: "button", onclick: () => sdTutorAsk("我看了刚才的评估。请挑我最严重的一个问题讲透：为什么错、正确的因果链（约束 → 失败模式 → 机制 → 代价 → 兜底 → 指标）是什么；然后出一个类似的小场景让我马上再答一次。", "接着问老师：讲透最严重的问题") }, "接着问 AI 老师"), h("span", { class: "small faint" }, "老师能看到题目、你的作答和这次评估")));
}
// 记下作答和评估，供 AI 老师接着用
function sdNote(attempt, review) { if (attempt != null) SD_CTX.attempt = attempt; if (review != null) SD_CTX.review = typeof review === "string" ? review : JSON.stringify(review); }

function viewSD({ sub }) {
  if (!SDD.blocks.length) return h("div", { class: "page" }, h("h1", null, "设计编码"), h("p", { class: "muted" }, "内容还在准备中，稍后刷新再来。"));
  if (sub === "s1") return sdStage1();
  if (sub === "s2") return sdStage2();
  if (sub === "s3") return sdStage3();
  if (sub === "s4") return sdStage4();
  if (sub === "s5") return sdStage5();
  if (sub === "kit") { sdFocus("机制工具箱", null); return sdKit(); }
  if (/^p\d+$/.test(sub) && sdBlock(sub)) { sdFocus("积木题讲解", sdBlock(sub)); return sdBlockView(sdBlock(sub)); }
  if (/^d\d+$/.test(sub) && sdDesign(sub)) { sdFocus("设计题讲解", sdDesign(sub)); return sdDesignView(sdDesign(sub)); }
  sdFocus("设计编码总览", null);
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
    ["sd-s5", "第五轮 · 30 分钟", "压力追问", "挑一道设计题，连续答 10 个深挖问题（最坏时刻、多实例、多机房、10 倍流量、选型、灰度），再练技术选型五句和指标口径。AI 面试官逐题点评。", SDD.designs.filter(d => Object.values((S5.get(d.id).ten) || {}).some(x => x && x.ev)).length],
  ];
  return sdPage("sd", "看到题目 30 秒内，先弹出骨架", "这里真正 Agent 专属的内容不多：DAG 调度是图算法加任务状态机，幂等执行是 singleflight 加状态机，无损续跑是持久化状态机加权威状态对账。你要练的不是背代码，而是建立十几个高频模式的召回路径——骨架出来了，细节就有地方挂。",
    h("section", { class: "panel sd-quick" }, h("div", { class: "spread" }, h("h2", null, "面试前一小时速通"), h("button", { class: "btn primary sm", type: "button", onclick: () => sdTutorAsk("我马上要面试 Agent / Harness 方向的系统设计。请按优先级（无损续跑 → Model Router → fan-out / workflow → 上下文与记忆 → 多 Harness 适配 → Sandbox → 工具 / API 安全）帮我快速查漏补缺：每个方向先问我一个最关键的问题，一次一个；我答完你点评（哪里想错了、更好的答法、下次怎么想），再进下一个方向。", "面试前速通：按优先级查漏补缺") }, "让 AI 老师按优先级考我")),
      h("ol", { class: "steps" },
        h("li", null, h("b", { class: "num" }, 1), h("span", null, h("a", { href: "#sd-kit" }, "机制工具箱"), "：扫一遍机制选择表和因果链 / 选型五句模板（10 分钟）")),
        h("li", null, h("b", { class: "num" }, 2), h("span", null, h("a", { href: "#sd-s5" }, "⑤ 压力追问"), "：无损续跑、Model Router 各答一轮 10 问，重点是最坏时刻、多实例、10 倍流量（30 分钟）")),
        h("li", null, h("b", { class: "num" }, 3), h("span", null, h("a", { href: "#sd-s5", onclick: () => LS.set("tiyan:sd:s5mode", "metric") }, "指标口径"), "：完成率、无损续跑率、排队 Turn 占比、记忆有效率——分子分母和排除项（10 分钟）")),
        h("li", null, h("b", { class: "num" }, 4), h("span", null, "右下角「AI 老师」：把没想通的地方问清楚，让它换皮再考一次（10 分钟）"))),
      h("p", { class: "small muted" }, "每一轮练完 AI 都会自动点评：哪里想错了、哪里可以更好、下次遇到类似场景怎么想、一条最佳实践；点「接着问 AI 老师」可以继续深挖。")),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "编码题统一起手式"), h("p", { class: "small muted" }, "先别写代码，在纸上回答五个问题："), h("ol", { class: "steps" }, SD_FIVE.map((t, i) => h("li", null, h("b", { class: "num" }, i + 1), h("span", null, t)))),
        h("p", { class: "small muted" }, "例：看到“同一个 key 并发只执行一次”，先写出 completed[key] / inflight[key] 两个状态和“同一时刻只有一个 leader、成功才缓存、失败不缓存”，这题就完成了七成。")),
      h("section", { class: "panel" }, h("h2", null, "设计题统一起手式"), h("div", { class: "oneline", style: "font-size:17px" }, "澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标"),
        h("p", { class: "small muted" }, "不会完整设计时，也可以这样开口：“我先确认一下任务数量、是否存在依赖、是否允许部分成功，以及有没有外部副作用。核心上我会把它拆成任务定义、执行状态和持久化日志三部分。正常流程先讲一遍，然后重点处理重试、幂等和恢复。”说着说着，你就有时间继续想了。"))),
    h("section", { class: "stack" }, h("h2", null, "急救训练：五轮约三个半小时"), h("div", { class: "hubs" }, plan.map(([href, when, t, d, n]) => h("a", { class: "panel hub", href: "#" + href }, h("div", { class: "eyebrow" }, when), h("h2", null, t), h("p", { class: "small muted" }, d), h("div", { class: "small faint num" }, `已练 ${n} 题`))))),
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
    sdFocus("① 识别模式", b);
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
      const attempt = `状态：${fs.states.value || "（空）"}\n不变量：${fs.invariants.value || "（空）"}\n失败情况：${fs.failures.value || "（空）"}`;
      sdNote(`【① 识别模式】只看题目 ${fmtSec(secs).replace("+", "")} 内写下：\n` + attempt, "");
      const aiBtn = h("button", { class: "btn sm", type: "button" }, "让 AI 查漏补缺");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是系统设计面试官。学习者只看题目，写下了这道题的核心状态、不变量和失败情况。请对照参考答案判分，指出缺了什么、哪里不准，并帮他查漏补缺。
${SD_COACH_RULE}
【题目】${b.statement}
【参考】核心状态：${b.states.map(s => s.name + "（" + s.desc + "）").join("；")}；不变量：${b.invariants.join("；")}；失败情况：${b.failures.map(x => x.case + "→" + x.handle).join("；")}
【学习者】状态：${fs.states.value || "（空）"}\n不变量：${fs.invariants.value || "（空）"}\n失败情况：${fs.failures.value || "（空）"}
意思对即可，名字不同没关系。评分档位：9–10 全对且有自己的洞见；7–8.5 基本对；5–6.5 抓到一半；3–4.5 大部分缺失；0–2.5 基本没写。
只返回 JSON：{"states": {"score": 8, "comment": "一句话"}, "invariants": {"score": 6, "comment": ""}, "failures": {"score": 5, "comment": ""}, "overall": 6.5, "missed": ["最关键的遗漏（具体）"], "tip": "下次看到这类题，先想到什么", ${SD_COACH_JSON}}`, r => {
        sdNote(null, r);
        ai.append(scoreLine(Number(r.overall) || 0), h("ul", { class: "ex-points" }, [["状态", r.states], ["不变量", r.invariants], ["失败情况", r.failures]].map(([t, x]) => h("li", { class: (x && x.score >= 7) ? "hit" : (x && x.score >= 4) ? "part" : "miss" }, h("b", null, `${t} ${x ? x.score : "-"}`), h("span", null, x ? x.comment : "")))),
          r.missed && r.missed.length ? h("div", null, h("h3", null, "最关键的遗漏"), sdList(arrStr(r.missed, 5))) : "", r.tip ? h("div", { class: "callout blue" }, h("b", null, "下次看到这类题，先想到："), String(r.tip)) : "", coachEl(r));
        SDS.put("s1", b.id, { ai: Number(r.overall) || 0 });
      }));
      if (AI.ok() && [fs.states, fs.invariants, fs.failures].some(t => t.value.trim().length > 4)) setTimeout(() => aiBtn.click(), 0);
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
    sdFocus("② 口述积木题", b);
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
      sdNote("【② 口述积木题】四段口述记录：\n" + SEGS.map(([k, t]) => `${k === "followup" ? "进阶追问：" + fq.q : t}：${texts[k] || "（空）"}`).join("\n"), "");
      const aiBtn = h("button", { class: "btn sm", type: "button", disabled: !has, title: has ? "" : "没有文字记录，AI 没法评估；可以只用自评" }, "让 AI 查漏补缺");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是系统设计 / 编码面试官。学习者口述了一道积木题，分四段（下面是他的口述记录，可能是要点或语音转写，允许口语化）。请逐段对照参考评分，指出漏掉的关键点，给出更好的说法，并帮他查漏补缺。
${SD_COACH_RULE}
【题目】${b.title}：${clip(b.statement, 1500)}
${SEGS.map(([k, t]) => `【${k === "followup" ? "进阶追问：" + fq.q : t}】\n学习者：${texts[k] || "（空）"}\n参考：${refs[k]}`).join("\n\n")}
评分档位：9–10 完整准确、表达清楚；7–8.5 基本到位；5–6.5 抓到一半；3–4.5 大部分缺失；0–2.5 基本没说。
只返回 JSON：{"segments": [{"key": "structure", "score": 7, "missed": ["漏掉的关键点"], "better": "更好的说法（2–4 句）"}], "overall": 7, "advice": "下一遍口述最该改的一点", ${SD_COACH_JSON}}（segments 按 structure / flow / pitfalls / followup 顺序）`, r => {
        sdNote(null, r);
        const segs = Array.isArray(r.segments) ? r.segments : [];
        ai.append(scoreLine(Number(r.overall) || 0), ...segs.map(x => { const t = (SEGS.find(s => s[0] === x.key) || [, x.key])[1]; return h("div", { class: "sd-cmp" }, h("div", { class: "row" }, h("b", null, t), h("span", { class: "num" }, `${x.score} 分`)), x.missed && x.missed.length ? sdList(arrStr(x.missed, 5)) : "", x.better ? mdEl(String(x.better), "small") : ""); }),
          r.advice ? h("div", { class: "callout blue" }, h("b", null, "下一遍最该改："), String(r.advice)) : "", coachEl(r));
        SDS.put("s2", b.id, { ai: Number(r.overall) || 0 });
      }));
      if (AI.ok() && has) setTimeout(() => aiBtn.click(), 0);
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
    sdFocus("③ 口述设计题", d);
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
      sdNote("【③ 口述设计题】六步口述记录：\n" + d.steps.map(s => `${s.title}：${texts[s.key] || "（空）"}`).join("\n"), "");
      const aiBtn = h("button", { class: "btn sm", type: "button", disabled: !has }, "让 AI 当面试官查漏补缺");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是资深系统设计面试官。学习者按“澄清 → 对象 → 主流程 → 失败恢复 → 并发限流 → 指标”六步口述了一道设计题（下面是他的口述记录，允许口语化）。请逐步对照得分点评分，指出缺失，给出 2 个你会追问的问题，并帮他查漏补缺。
${SD_COACH_RULE}
特别检查：有没有说清权威状态在哪、最坏时刻挂了怎么办、多实例怎么不重复执行、指标的分子分母；每个机制有没有说出它解决的失败模式和代价（因果链：约束 → 失败模式 → 机制 → 代价 → 兜底 → 指标）。
【题目】${d.title}：${d.statement}
${d.steps.map(s => `【${s.title}】得分点：${s.points.join("；")}\n学习者：${texts[s.key] || "（空）"}`).join("\n\n")}
评分档位：9–10 完整且有取舍和数据；7–8.5 基本到位；5–6.5 抓到一半；3–4.5 大部分缺失；0–2.5 基本没说。
只返回 JSON：{"steps": [{"key": "clarify", "score": 7, "hit": [0, 2], "missed": ["缺失的点"]}], "overall": 6.5, "verdict": "整体评价一句话", "followups": ["面试官会追问的问题"], "advice": "下一遍最该改的一点", ${SD_COACH_JSON}}（steps 按 clarify / objects / flow / failure / concurrency / metrics 顺序；hit 是得分点下标）`, r => {
        sdNote(null, r);
        const steps = Array.isArray(r.steps) ? r.steps : [];
        ai.append(scoreLine(Number(r.overall) || 0, r.verdict ? h("span", { class: "small" }, String(r.verdict)) : ""),
          ...steps.map(x => { const s = d.steps.find(y => y.key === x.key); if (!s) return ""; const hit = Array.isArray(x.hit) ? x.hit.map(Number) : []; return h("div", { class: "sd-cmp" }, h("div", { class: "row" }, h("b", null, s.title), h("span", { class: "num" }, `${x.score} 分`)), h("ul", { class: "ex-points" }, s.points.map((p, i) => h("li", { class: hit.includes(i) ? "hit" : "miss" }, h("b", null, hit.includes(i) ? "说到" : "缺"), h("span", null, p)))), x.missed && x.missed.length ? sdList(arrStr(x.missed, 4)) : ""); }),
          r.followups && r.followups.length ? h("div", null, h("h3", null, "面试官接着会问"), sdList(arrStr(r.followups, 4))) : "",
          r.advice ? h("div", { class: "callout blue" }, h("b", null, "下一遍最该改："), String(r.advice)) : "", coachEl(r),
          d.pressure ? h("div", { class: "row" }, h("a", { class: "btn sm", href: "#sd-s5", onclick: () => LS.set("tiyan:sd:s5cur", d.id) }, "接着练这道题的压力追问 →")) : "");
        const all = SDS.all(); const arr = all.s3[d.id] || []; if (arr.length) { arr[arr.length - 1].ai = Number(r.overall) || 0; LS.set("tiyan:sd", all); }
      }));
      if (AI.ok() && has) setTimeout(() => aiBtn.click(), 0);
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
      sdFocus("④ 随机抽题", b);
      const said = FIELDS.map(([k, t], i) => `${t}：${ins[i].value || "（没写）"}`).join("\n");
      sdNote(`【④ 随机抽题】${v ? "换皮题面：" + v.context : "题目名：" + b.title}，用时 ${secs} 秒，说出：\n` + said, "");
      const ai = aiBox();
      const aiBtn = h("button", { class: "btn sm", type: "button" }, "让 AI 查漏补缺");
      aiBtn.addEventListener("click", () => sdAsk(ai, `你是系统设计面试官。学习者在 30 秒随机抽题里，只看${v ? "一个换了业务背景的题面" : "题目名"}，说出这道题的骨架。请逐项判断对不对，并帮他查漏补缺。
${SD_COACH_RULE}
【题面】${v ? v.context : b.title}
【它的模式】${b.title}：${b.essence}
【参考】两个核心状态：${b.states.map(s => s.name + "（" + s.desc + "）").join("；")}；最重要的不变量：${b.invariants[0]}；常见失败场景：${b.failures.map(x => x.case + "→" + x.handle).join("；")}；扩展追问：${b.followups.map(x => x.q).join("；")}
【学习者，用时 ${secs} 秒】\n${said}
意思对即可，名字不同没关系。${v ? "换皮模式下先判断他有没有认出这是哪个模式。" : ""}
只返回 JSON：{"items": [{"key": "states", "ok": true, "comment": "一句话"}, {"key": "invariant", "ok": false, "comment": ""}, {"key": "failure", "ok": true, "comment": ""}, {"key": "followup", "ok": true, "comment": ""}], "recognized": true, "overall": 7, ${SD_COACH_JSON}}`, r => {
        sdNote(null, r);
        const items = Array.isArray(r.items) ? r.items : [];
        ai.append(scoreLine(Number(r.overall) || 0, v && r.recognized === false ? h("span", { class: "pill due" }, "没认出模式") : ""),
          h("ul", { class: "ex-points sd-fields" }, FIELDS.map(([k, t]) => { const x = items.find(y => y.key === k) || {}; return h("li", { class: x.ok ? "hit" : "miss" }, h("b", null, `${t} ${x.ok ? "对" : "缺 / 不准"}`), h("span", null, x.comment || "")); })),
          coachEl(r));
      }));
      const refs = [sdStates(b), h("div", null, b.invariants[0]), sdList(b.failures.slice(0, 3).map(x => `${x.case}：${x.handle}`)), sdList(b.followups.slice(0, 3).map(x => x.q))];
      res.append(h("div", { class: "callout " + (secs <= 30 ? "blue" : "") }, h("b", null, `${b.id.toUpperCase()} ${b.title}`), `　用时 ${secs} 秒${secs > 30 ? "（超过 30 秒：召回路径还没建立）" : ""}。逐项对照，说对了就点“对”。`),
        ...FIELDS.map(([k, t], i) => h("div", { class: "sd-cmp" }, h("div", { class: "spread" }, h("b", null, t), (() => { const seg = h("div", { class: "seg sd-mark" }, [[1, "对"], [0, "不对 / 没说"]].map(([val, label]) => { const btn = h("button", { type: "button", class: val === 0 ? "on" : "" }, label); btn.addEventListener("click", () => { marks[i] = val; $$("button", seg).forEach(x => x.classList.remove("on")); btn.classList.add("on"); save(); drawStats(); }); return btn; })); return seg; })()),
          h("div", { class: "sd-cmp-grid" }, h("div", { class: "sd-user" }, ins[i].value || "（没写）"), h("div", null, refs[i])))),
        h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: round }, "再抽一题"), aiBtn, h("a", { class: "btn ghost sm", href: "#sd-" + b.id }, "看这题的完整讲解")), ai);
      drawStats();
      if (AI.ok() && ins.some(x => x.value.trim())) setTimeout(() => aiBtn.click(), 0);
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

// ----- 机制工具箱：什么信号用什么机制、架构工具箱、回答模板、追问风格、安全清单、指标口径 -----
function sdKit() {
  if (!TB.mechanisms) return sdPage("sd-kit", "机制工具箱", "内容还在准备中，稍后刷新再来。");
  const quiz = m => sdTutorAsk(`考我「${m.name}」：出一个具体的业务场景（不要直接说要用什么机制），让我判断需不需要${m.name}、为什么、代价是什么、不用会坏成什么样。只出题，等我回答后再点评：哪里想错了、更好的答法、下次怎么判断。`, `考我：${m.name}`);
  const dsg = id => sdDesign(id) ? h("a", { class: "chip", href: "#sd-" + id }, sdDesign(id).title) : "";
  const blk = id => sdBlock(id) ? h("a", { class: "chip", href: "#sd-" + id }, id.toUpperCase()) : "";
  const T = TB.templates;
  return sdPage("sd-kit", "机制工具箱：先找信号，再选机制", TB.formula,
    h("section", { class: "panel" }, h("p", null, TB.formula_note), h("div", { class: "callout" }, h("b", null, "原则　"), TB.principle)),
    h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "机制选择表"), h("span", { class: "small faint" }, "每个机制都要说出：什么信号出现、解决什么失败模式、代价是什么")),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable sd-kit-table" }, h("thead", null, h("tr", null, ["机制", "什么信号出现时用", "解决什么风险", "怎么做", "代价 / 别滥用", ""].map(x => h("th", null, x)))),
        h("tbody", null, TB.mechanisms.map(m => h("tr", null, h("td", null, h("b", null, m.name), h("div", { class: "row", style: "gap:4px;margin-top:4px" }, (m.blocks || []).map(blk))), h("td", null, m.signal), h("td", null, m.solves), h("td", null, m.how), h("td", { class: "muted" }, m.cost), h("td", null, h("button", { class: "btn sm", type: "button", onclick: () => quiz(m) }, "考我")))))))),
    h("section", { class: "stack" }, h("h2", null, "架构工具箱：按维度检查有没有漏"), h("p", { class: "small muted" }, "口述设计题讲完主流程后，按这八个维度扫一遍；面试官的追问基本落在这里。"),
      h("div", { class: "sd-dims" }, TB.dims.map(x => h("div", { class: "panel" }, h("h3", null, x.dim), sdList(x.items), h("p", { class: "small" }, h("b", null, "开场一句："), x.say))))),
    h("section", { class: "grid-2" },
      h("div", { class: "panel" }, h("h2", null, "因果链答法"), h("div", { class: "oneline" }, T.chain.name.replace(/^因果链：/, "")), h("ol", { class: "mock-ul" }, T.chain.steps.map(x => h("li", null, x))),
        h("div", { class: "callout" }, h("b", null, "反例　"), T.chain.bad), h("div", { class: "callout blue" }, h("b", null, "正例　"), T.chain.good)),
      h("div", { class: "panel" }, h("h2", null, "技术选型五句"), h("ol", { class: "mock-ul" }, T.choice.steps.map(x => h("li", null, x))), h("div", { class: "callout blue" }, h("b", null, "例：session 路由　"), T.choice.example),
        h("div", { class: "row" }, h("a", { class: "btn primary sm", href: "#sd-s5", onclick: () => LS.set("tiyan:sd:s5mode", "choice") }, "用五句模板练一题 →")))),
    h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "压力追问 10 问"), h("a", { class: "btn primary sm", href: "#sd-s5", onclick: () => LS.set("tiyan:sd:s5mode", "ten") }, "去练 →")), h("p", { class: "small muted" }, "每道设计题讲完，面试官大概率按这十个方向连续追问。每一问都按因果链答。"),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("thead", null, h("tr", null, ["", "追问", "面试官想听到", "常见失分"].map(x => h("th", null, x)))), h("tbody", null, TB.pressure.map((p, i) => h("tr", null, h("td", { class: "num" }, i + 1), h("td", null, h("b", null, p.q)), h("td", null, p.wants), h("td", { class: "muted" }, p.trap))))))),
    h("section", { class: "stack" }, h("h2", null, "面试官的五种追问风格"), h("div", { class: "sd-dims" }, TB.styles.map(x => h("div", { class: "panel" }, h("h3", null, x.kind), sdList(x.asks.map(q => "“" + q + "”")), h("p", { class: "small" }, h("b", null, "怎么答："), x.how),
      h("button", { class: "btn sm", type: "button", onclick: () => sdTutorAsk(`你是资深面试官，用「${x.kind}」这种风格追问我。先让我选一道设计题（站内设计题或我自己项目里的系统），然后一次只问一个问题；我答完你点评：哪里想错了、更好的答法、下次怎么答，再接着追问。`, `用「${x.kind}」追问我`) }, "让老师这样追问我"))))),
    h("section", { class: "grid-2" },
      h("div", { class: "panel" }, h("h2", null, "安全清单"), h("p", { class: "small muted" }, "Agent 能调工具、能执行代码，安全题按“分级 → 最小权限 → 隔离 → 审批 → 审计 → fail-closed”答。"), h("ul", { class: "mock-ul" }, TB.security.map(x => h("li", null, h("b", null, x.item), "：", x.detail)))),
      h("div", { class: "panel" }, h("h2", null, "指标口径六条"), h("ol", { class: "mock-ul" }, TB.metric_rules.map(x => h("li", null, x))),
        h("p", { class: "small muted" }, "练习：" + TB.metric_drills.map(m => m.name).join("、")), h("a", { class: "btn primary sm", href: "#sd-s5", onclick: () => LS.set("tiyan:sd:s5mode", "metric") }, "去练指标口径 →"))),
    h("section", { class: "panel" }, h("h2", null, "高频方向（按优先级）"), h("p", { class: "small muted" }, "时间不够时从上往下准备；每个方向至少能用因果链讲清一道题、答住 10 问里的 crash / multi / tenx 三问。"),
      h("ol", { class: "steps" }, TB.topics.map((t, i) => h("li", null, h("b", { class: "num" }, i + 1), h("div", null, h("b", null, t.title), h("div", { class: "small muted" }, t.why), h("div", { class: "row", style: "gap:4px;margin-top:4px" }, t.designs.map(dsg)))))),
      h("h3", null, "同一套积木还能组合出这些纯架构题"), sdList(TB.variants)));
}

// ----- ⑤ 压力追问：10 问 / 技术选型五句 / 指标口径；AI 面试官逐题点评并追问一层 -----
const SD_JOBS = {};          // 请求进行中的 key；结果写进本地记录，离开页面也不中断
let SD_REDRAW = null;
const S5 = {
  all() { return LS.get("tiyan:sd:s5", {}); },
  get(did) { return this.all()[did] || {}; },
  patch(did, path, val) { const a = this.all(); let o = a[did] = a[did] || {}; for (const k of path.slice(0, -1)) o = o[k] = o[k] || {}; o[path[path.length - 1]] = val; LS.set("tiyan:sd:s5", a); },
};
function sdJob(key, prompt, path) {
  if (SD_JOBS[key]) return;
  if (!AI.ok()) { toast(aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" })); if (S.ai === "needkey") openKeyDialog(); return; }
  const [did, ...rest] = path;
  SD_JOBS[key] = true;
  S5.patch(did, rest.concat("err"), "");
  if (SD_REDRAW) SD_REDRAW();
  AI.ask(prompt, { json: true, tier: "default" })
    .then(r => { S5.patch(did, rest.concat("ev"), r); sdNote(null, r); })
    .catch(e => S5.patch(did, rest.concat("err"), e && e.code ? aiErr(e) : "评估失败：" + ((e && e.message) || e)))
    .finally(() => { delete SD_JOBS[key]; if (SD_REDRAW) SD_REDRAW(); });
}
const S5_CHAIN = [["constraint", "业务约束"], ["failure", "失败模式"], ["mechanism", "机制"], ["cost", "代价"], ["fallback", "兜底"], ["metric", "指标"]];
const S5_SHORT = { core: "核心", scale: "规模", authority: "权威状态", crash: "最坏时刻", dup: "重复乱序", multi: "多实例", region: "多机房", tenx: "10 倍", choice: "选型", rollout: "灰度" };
const S5_CHOICE = [["constraint", "约束是什么"], ["choice", "我选什么"], ["alternatives", "备选有哪些"], ["why_not", "为什么不选备选"], ["downside", "缺点 + 兜底 + 指标"]];
const S5_METRIC = [["numerator", "统计对象与分子"], ["denominator", "分母"], ["exclude", "排除项与理由"], ["traps", "口径陷阱与护栏指标"]];
const sdPQ = d => d.pressure || (TB.pressure || []).map(p => ({ key: p.key, q: p.q, a: "" }));
function sdStage5() {
  let cur = LS.get("tiyan:sd:s5cur", (SDD.designs.find(d => d.pressure && d.priority) || SDD.designs.find(d => d.pressure) || SDD.designs[0]).id);
  if (!sdDesign(cur)) cur = SDD.designs[0].id;
  let mode = LS.get("tiyan:sd:s5mode", "ten");
  const box = h("div", { class: "stack" });
  const side = h("aside", { class: "panel sd-side" });
  const ta = (id, val, onInput, rows) => { const t = h("textarea", { class: "mock-input", id, style: `min-height:${rows || 110}px` }); t.value = val || ""; t.addEventListener("input", () => onInput(t.value)); return t; };
  const voice = t => { const vb = h("button", { class: "btn sm", type: "button", hidden: !SpeechRec }, "语音输入"); const vs = h("span", { class: "small muted" }); vb.addEventListener("click", () => toggleVoice(t, vb, vs)); return [vb, vs]; };
  const pending = () => h("div", { class: "thinking" }, "AI 面试官在看你的回答……（大约 15–40 秒，可以先去答下一问）");
  const errRow = (msg, retry) => h("div", { class: "row" }, h("span", { class: "small", style: "color:var(--red)" }, msg), h("button", { class: "btn sm", type: "button", onclick: retry }, "重试"));
  const better = t => t ? h("details", { class: "qa", open: true }, h("summary", null, "更好的回答"), mdEl(String(t), "small")) : "";
  const fieldList = (defs, items) => h("ul", { class: "ex-points sd-fields" }, defs.map(([k, t]) => { const x = (Array.isArray(items) ? items : []).find(y => y.key === k) || {}; return h("li", { class: x.ok ? "hit" : "miss" }, h("b", null, `${t} ${x.ok ? "到位" : "缺 / 不准"}`), h("span", null, x.comment || "")); }));
  const drawSide = d => {
    const st = S5.all();
    side.textContent = "";
    side.append(h("div", { class: "eyebrow" }, "设计题"), h("ol", { class: "sd-order" }, SDD.designs.map(x => { const t = (st[x.id] || {}).ten || {}; const done = Object.values(t).filter(y => y && y.ev).length; return h("li", { class: x.id === cur ? "on" : "" }, h("a", { href: "#sd-s5", onclick: e => { e.preventDefault(); cur = x.id; draw(); window.scrollTo(0, 0); } }, (x.priority ? "★ " : "") + x.title), h("span", { class: "small faint num" }, ` ${done}/10`)); })),
      h("p", { class: "small muted" }, "优先级：无损续跑 → Model Router → fan-out / workflow → 上下文与记忆 → 多 Harness 适配 → Sandbox → 工具 / API 安全。"));
  };
  // 10 问
  const drawTen = (d, wrap) => {
    const PQ = sdPQ(d), rec = S5.get(d.id), ten = rec.ten || {};
    let i = Math.min(Math.max(0, rec.i || 0), PQ.length - 1);
    const p = PQ[i], g = (TB.pressure || []).find(x => x.key === p.key) || {}, r = ten[p.key] || {};
    const jk = `${d.id}:ten:${p.key}`, fk = `${d.id}:fu:${p.key}`;
    const goQ = n => { S5.patch(d.id, ["i"], n); draw(); };
    const dots = h("div", { class: "sd-dots" }, PQ.map((x, n) => { const e = (ten[x.key] || {}).ev; const sc = e ? Number(e.score) || 0 : null; return h("button", { type: "button", class: (n === i ? "on " : "") + (sc == null ? "" : sc >= 7 ? "ok" : sc >= 5 ? "mid" : "bad"), title: x.q, onclick: () => goQ(n) }, h("span", { class: "num" }, n + 1), S5_SHORT[x.key] || x.key, sc != null ? h("small", { class: "num" }, " " + sc) : ""); }));
    const timer = countdown(120);
    const ans = ta(`s5-${d.id}-${p.key}`, r.ans, v => { if (!timer.used()) timer.start(); S5.patch(d.id, ["ten", p.key, "ans"], v); }, 140);
    const [vb, vs] = voice(ans);
    const ask = () => {
      const a = ans.value.trim(); if (a.length < 6) { toast("先说几句再提交"); return; }
      stopVoice(); timer.stop();
      sdNote(`【⑤ 压力追问】${d.title} · 第 ${i + 1} 问：${p.q}\n我的回答：${a}`, "");
      sdJob(jk, `你是资深后端 / Agent 平台面试官，正在对一道设计题做压力追问。学习者的回答可能是口述记录或语音转写，允许口语化。
${SD_COACH_RULE}
【设计题】${d.title}：${clip(d.statement, 1200)}
【这一问】${p.q}
【面试官想听到】${g.wants || ""}　【常见失分】${g.trap || ""}
${p.a ? "【参考答案（因果链）】" + p.a : "（这道题还没有参考答案，请按你的专业判断）"}
【学习者回答】${a}
检查因果链六要素是否齐全：业务约束 / 失败模式 / 机制 / 代价 / 兜底 / 指标；以及是否落到哪一层、什么状态、什么字段、什么数字。不要求和参考一字不差，思路对、取舍说得通就给分。
评分档位：9–10 因果链完整、具体到字段和数字、有取舍；7–8.5 基本到位但缺一两环；5–6.5 有机制但缺失败模式或代价；3–4.5 只有名词堆砌；0–2.5 答非所问。
只返回 JSON：{"score": 6.5, "verdict": "一句话总评", "chain": {"constraint": true, "failure": false, "mechanism": true, "cost": false, "fallback": false, "metric": false}, "concrete": "具体程度的一句话评价", "missed": ["漏掉的关键点"], "better": "更好的回答：像真人在面试里口述，按因果链，150–300 字", "followup": "你作为面试官接下来最可能追问的一句话", ${SD_COACH_JSON}}`, [d.id, "ten", p.key]);
    };
    const ev = r.ev;
    const evBox = h("div", { class: "stack sd-ai" });
    if (SD_JOBS[jk]) evBox.append(pending());
    else if (r.err) evBox.append(errRow(r.err, ask));
    else if (ev) {
      const fu = r.fu || {};
      const fuTa = ev.followup ? ta(`s5-${d.id}-${p.key}-fu`, fu.ans, v => S5.patch(d.id, ["ten", p.key, "fu", "ans"], v), 90) : null;
      const askFu = () => {
        const a = fuTa.value.trim(); if (a.length < 4) { toast("先回答追问"); return; }
        sdNote(`【⑤ 压力追问】${d.title} · ${p.q}\n我的回答：${ans.value}\n面试官追问：${ev.followup}\n我的回答：${a}`, "");
        sdJob(fk, `你是资深面试官，在压力追问。
${SD_COACH_RULE}
【设计题】${d.title}
【上一问】${p.q}
【他的回答】${ans.value}
【你的追问】${ev.followup}
【他对追问的回答】${a}
只返回 JSON：{"score": 6, "verdict": "一句话", "missed": ["漏掉的关键点"], "better": "更好的回答（100–250 字，像真人口述）", ${SD_COACH_JSON}}`, [d.id, "ten", p.key, "fu"]);
      };
      evBox.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""),
        h("div", { class: "sd-chain" }, S5_CHAIN.map(([k, t]) => h("span", { class: ev.chain && ev.chain[k] ? "hit" : "miss" }, (ev.chain && ev.chain[k] ? "✓ " : "✗ ") + t))),
        ev.concrete ? h("p", { class: "small muted" }, "具体程度：" + ev.concrete) : "",
        ev.missed && ev.missed.length ? h("div", null, h("h3", null, "漏掉的关键点"), sdList(arrStr(ev.missed, 5))) : "",
        better(ev.better), coachEl(ev));
      if (ev.followup) {
        const fe = fu.ev;
        evBox.append(h("div", { class: "sd-cmp" }, h("div", { class: "callout blue" }, h("b", null, "面试官追问："), String(ev.followup)), fuTa,
          h("div", { class: "row" }, h("button", { class: "btn sm", type: "button", disabled: !!SD_JOBS[fk], onclick: askFu }, fe ? "重新评估追问" : "回答追问"), ...voice(fuTa)),
          SD_JOBS[fk] ? pending() : fu.err ? errRow(fu.err, askFu) : fe ? h("div", { class: "stack" }, scoreLine(Number(fe.score) || 0, fe.verdict ? h("span", { class: "small" }, String(fe.verdict)) : ""), fe.missed && fe.missed.length ? sdList(arrStr(fe.missed, 4)) : "", better(fe.better), coachEl(fe)) : ""));
      }
    }
    const ref = p.a ? h("details", { class: "qa", open: !!ev }, h("summary", null, "参考答案（因果链）"), mdEl(p.a, "small")) : "";
    const answered = PQ.filter(x => (ten[x.key] || {}).ev);
    const rep = rec.report || {}, rk = `${d.id}:report`;
    const askReport = () => sdJob(rk, `你是资深面试官，刚对学习者做完一道设计题的压力追问。请做整场复盘，帮他查漏补缺。
${SD_COACH_RULE}
【设计题】${d.title}
${answered.map(x => { const t = ten[x.key]; return `【${x.q}】\n回答：${clip(t.ans, 600)}\n得分：${t.ev.score}；总评：${t.ev.verdict || ""}`; }).join("\n\n")}
只返回 JSON：{"overall": 6.5, "pattern": ["反复出现的问题模式（具体，引用他的回答）"], "strong": ["做得好的地方"], "fix_first": "最该先补的一件事", "checklist": ["下次回答压力追问的检查清单，5–7 条"], "drill": ["接下来具体练什么（到哪道题哪一问）"], ${SD_COACH_JSON}}`, [d.id, "report"]);
    const repBox = h("div", { class: "stack" });
    if (SD_JOBS[rk]) repBox.append(pending());
    else if (rep.err) repBox.append(errRow(rep.err, askReport));
    else if (rep.ev) { const e = rep.ev; repBox.append(scoreLine(Number(e.overall) || 0), e.fix_first ? h("div", { class: "callout" }, h("b", null, "最该先补："), String(e.fix_first)) : "", arrStr(e.pattern, 5).length ? h("div", null, h("h3", null, "反复出现的问题"), sdList(arrStr(e.pattern, 5))) : "", arrStr(e.strong, 4).length ? h("div", null, h("h3", null, "做得好的"), sdList(arrStr(e.strong, 4))) : "", arrStr(e.checklist, 8).length ? h("div", { class: "callout blue" }, h("b", null, "下次答压力追问的检查清单"), h("ol", { class: "mock-ul" }, arrStr(e.checklist, 8).map(x => h("li", null, x)))) : "", arrStr(e.drill, 5).length ? h("div", null, h("h3", null, "接下来练"), sdList(arrStr(e.drill, 5))) : "", coachEl(e)); }
    wrap.append(dots,
      h("section", { class: "panel" }, h("div", { class: "spread" }, h("div", { class: "eyebrow" }, `第 ${i + 1} / ${PQ.length} 问 · ${S5_SHORT[p.key] || p.key}`), h("div", { class: "row" }, h("span", { class: "small faint" }, "建议 1–2 分钟"), timer.el)),
        h("p", { class: "sd-prompt", style: "font-size:19px" }, p.q),
        g.wants ? h("details", { class: "qa" }, h("summary", null, "提示：面试官想听到什么"), h("p", { class: "small" }, g.wants), h("p", { class: "small muted" }, "常见失分：" + g.trap)) : "",
        h("p", { class: "small muted" }, "按因果链答：业务约束 → 失败模式 → 机制 → 代价 → 兜底 → 指标。出声说，同时在框里记要点。"),
        ans, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!SD_JOBS[jk], onclick: ask }, ev ? "改完了，重新点评" : "提交，让面试官点评"), vb, vs,
          i < PQ.length - 1 ? h("button", { class: "btn sm", type: "button", onclick: () => goQ(i + 1) }, "下一问 →") : "", i > 0 ? h("button", { class: "btn ghost sm", type: "button", onclick: () => goQ(i - 1) }, "← 上一问") : ""),
        evBox, ref),
      h("section", { class: "panel" }, h("div", { class: "spread" }, h("h2", null, "整场复盘"), h("button", { class: "btn sm", type: "button", disabled: answered.length < 3 || !!SD_JOBS[rk], onclick: askReport }, answered.length < 3 ? `至少答 3 问（已 ${answered.length}）` : rep.ev ? "重新复盘" : "生成复盘")),
        h("p", { class: "small muted" }, "看你在 10 问里反复犯的错，给出下次的检查清单。"), repBox));
  };
  // 技术选型五句 / 指标口径：同一种“填空 → AI 点评 → 对照参考”
  const drawFill = (d, wrap, kind) => {
    const isC = kind === "choice";
    const items = isC ? (d.choices || []).map((c, n) => ({ id: "c" + n, title: c.topic, ref: c, group: "" }))
      : (d.metrics || []).map((m, n) => ({ id: "m" + n, title: m.name, ref: m, group: "这道题" })).concat((TB.metric_drills || []).map((m, n) => ({ id: "g" + n, title: m.name, ref: m, group: "通用" })));
    if (isC) items.push({ id: "free", title: "自选一个选型点", ref: null, group: "" });
    const rec = S5.get(d.id), bag = (isC ? rec.ch : rec.mt) || {};
    const selKey = `tiyan:sd:s5${kind}:${d.id}`;
    let sel = LS.get(selKey, items[0].id); if (!items.find(x => x.id === sel)) sel = items[0].id;
    const it = items.find(x => x.id === sel), r = bag[sel] || {}, f = r.f || {};
    const DEF = isC ? S5_CHOICE : S5_METRIC, path = [d.id, isC ? "ch" : "mt", sel], jk = `${d.id}:${kind}:${sel}`;
    const pick = h("div", { class: "row", style: "gap:6px" }, items.map(x => h("button", { type: "button", class: "chip" + (x.id === sel ? " on" : ""), onclick: () => { LS.set(selKey, x.id); draw(); } }, (x.group === "通用" ? "通用 · " : "") + x.title, (bag[x.id] || {}).ev ? h("small", { class: "num" }, " " + bag[x.id].ev.score) : "")));
    const topicIn = !it.ref && isC ? h("input", { class: "mock-input", id: `s5-${d.id}-free-topic`, style: "min-height:0;padding:8px 10px", placeholder: "例如：session 状态存数据库还是事件日志？队列用什么？", value: f.topic || "" }) : null;
    if (topicIn) topicIn.addEventListener("input", () => S5.patch(d.id, path.concat("f", "topic"), topicIn.value));
    const tas = DEF.map(([k, t]) => [k, t, ta(`s5-${d.id}-${sel}-${k}`, f[k], v => S5.patch(d.id, path.concat("f", k), v), 64)]);
    const ask = () => {
      const vals = Object.fromEntries(tas.map(([k, , t]) => [k, t.value.trim()]));
      if (Object.values(vals).join("").length < 10) { toast("先把几项填上再提交"); return; }
      const topic = it.ref ? it.title : (topicIn.value.trim() || "（未写选型点）");
      const mine = tas.map(([k, t]) => `${t}：${vals[k] || "（空）"}`).join("\n");
      sdNote(`【⑤ ${isC ? "技术选型五句" : "指标口径"}】${d.title} · ${topic}\n${mine}`, "");
      const ref = it.ref;
      sdJob(jk, isC ? `你是资深架构面试官，在考技术选型的表达。学习者要用五句说服你：约束 / 选择 / 备选 / 为什么不选备选 / 缺点 + 兜底 + 指标。
${SD_COACH_RULE}
【设计题】${d.title}：${clip(d.statement, 1000)}
【选型点】${topic}
${ref ? `【参考】约束：${ref.constraint}\n选择：${ref.choice}\n备选：${ref.alternatives}\n为什么不选：${ref.why_not}\n缺点与兜底：${ref.downside}\n指标：${ref.metric}` : "（自选选型点，没有参考答案，请按你的专业判断）"}
【学习者】\n${mine}
他的选择不必和参考一致：约束推得出选择、备选比较公平、代价和兜底说清楚、指标可验证，就给高分；如果在这个约束下选错了，要明确说。
只返回 JSON：{"score": 6.5, "verdict": "一句话", "items": [{"key": "constraint", "ok": true, "comment": ""}, {"key": "choice", "ok": true, "comment": ""}, {"key": "alternatives", "ok": false, "comment": ""}, {"key": "why_not", "ok": false, "comment": ""}, {"key": "downside", "ok": false, "comment": ""}], "better": "五句完整示范（像真人口述）", ${SD_COACH_JSON}}`
        : `你是资深面试官，在追问指标口径。
${SD_COACH_RULE}
【场景】${it.group === "通用" ? "通用 Agent 平台指标" : d.title}
【面试官问】${ref.ask}
【参考口径】分子：${ref.numerator}\n分母：${ref.denominator}\n排除：${ref.exclude}\n口径陷阱：${ref.traps.join("；")}\n参考说法：${ref.answer}
【学习者】\n${mine}
不要求和参考一字不差：统计对象清楚、分子分母可采集、排除项有理由、想到了会被刷高的方式和护栏，就给高分。
只返回 JSON：{"score": 6.5, "verdict": "一句话", "items": [{"key": "numerator", "ok": true, "comment": ""}, {"key": "denominator", "ok": false, "comment": ""}, {"key": "exclude", "ok": false, "comment": ""}, {"key": "traps", "ok": false, "comment": ""}], "better": "更好的口述（100–250 字）", ${SD_COACH_JSON}}`, path);
    };
    const ev = r.ev, evBox = h("div", { class: "stack sd-ai" });
    if (SD_JOBS[jk]) evBox.append(pending());
    else if (r.err) evBox.append(errRow(r.err, ask));
    else if (ev) evBox.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""), fieldList(DEF, ev.items), better(ev.better), coachEl(ev));
    const ref = it.ref;
    const refEl = !ref ? "" : isC ? h("details", { class: "qa", open: !!ev }, h("summary", null, "参考五句"), h("ol", { class: "mock-ul" }, [["约束", ref.constraint], ["选择", ref.choice], ["备选", ref.alternatives], ["为什么不选", ref.why_not], ["缺点 + 兜底", ref.downside], ["指标", ref.metric]].map(([t, x]) => h("li", null, h("b", null, t + "："), x))))
      : h("details", { class: "qa", open: !!ev }, h("summary", null, "参考口径"), h("ul", { class: "mock-ul" }, h("li", null, h("b", null, "分子："), ref.numerator), h("li", null, h("b", null, "分母："), ref.denominator), h("li", null, h("b", null, "排除："), ref.exclude), h("li", null, h("b", null, "口径陷阱："), ref.traps.join("；"))), mdEl(ref.answer, "small"));
    wrap.append(h("section", { class: "panel" }, pick,
      h("p", { class: "sd-prompt", style: "font-size:19px" }, isC ? (ref ? `选型：${ref.topic}——用五句说服面试官` : "自选一个这道题里的关键选型点，用五句说服面试官") : ref.ask),
      isC ? h("p", { class: "small muted" }, "五句：约束是什么 → 我选什么 → 备选有哪些 → 为什么不选备选 → 缺点是什么、怎么兜底、用什么指标证明。") : h("p", { class: "small muted" }, "先说统计对象（任务 / session / turn），再说分子、分母、排除项和理由，最后说这个指标可能被怎么刷高、配套什么护栏指标。"),
      topicIn || "",
      h("div", { class: "sd-fill" }, tas.map(([k, t, el]) => h("label", { class: "card-f" }, h("b", null, t), el))),
      h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!SD_JOBS[jk], onclick: ask }, ev ? "改完了，重新点评" : "提交，让面试官点评")),
      evBox, refEl));
  };
  const draw = () => {
    const d = sdDesign(cur);
    LS.set("tiyan:sd:s5cur", cur); LS.set("tiyan:sd:s5mode", mode);
    sdFocus("⑤ 压力追问", d);
    box.textContent = "";
    drawSide(d);
    const seg = h("div", { class: "seg" }, [["ten", "10 问压力追问"], ["choice", "技术选型五句"], ["metric", "指标口径"]].map(([k, t]) => h("button", { type: "button", class: k === mode ? "on" : "", onclick: () => { mode = k; draw(); } }, t)));
    box.append(h("section", { class: "panel" }, h("div", { class: "spread" }, h("h2", null, (d.priority ? "★ " : "") + d.title), seg),
      h("details", { class: "qa" }, h("summary", null, "题目"), mdEl(d.statement)),
      !d.pressure ? h("p", { class: "small muted" }, "这道题的专属追问和参考答案还在准备中，先用通用 10 问练；AI 面试官会按专业判断点评。") : ""));
    const wrap = h("div", { class: "stack" });
    if (mode === "ten") drawTen(d, wrap);
    else if (mode === "choice" && !(d.choices || []).length) { wrap.append(h("section", { class: "panel" }, h("p", { class: "muted" }, "这道题的选型参考还在准备中；可以先选「自选一个选型点」练五句模板。"))); drawFill(d, wrap, "choice"); }
    else drawFill(d, wrap, mode === "metric" ? "metric" : "choice");
    box.append(wrap);
  };
  SD_REDRAW = () => {
    const ae = document.activeElement, id = ae && box.contains(ae) && ae.id;
    const a = id && ae.selectionStart, b = id && ae.selectionEnd, y = window.scrollY;
    draw();
    window.scrollTo(0, y);
    if (id) { const n = document.getElementById(id); if (n) { n.focus({ preventScroll: true }); try { n.setSelectionRange(a, b); } catch (e) { /* input 类型不支持选区 */ } } }
  };
  onLeave(() => { SD_REDRAW = null; });
  draw();
  return sdPage("sd-s5", "第五轮：压力追问", "讲完设计，面试官会连续深挖：最坏时刻挂了、多实例重复执行、多机房、10 倍流量、为什么选它、怎么证明收益。每一问都按因果链答，AI 面试官逐题点评、追问一层，最后给整场复盘。", h("div", { class: "sd-grid" }, box, side));
}
