// ---------- 学习中心：「AI 知识」和「Python 刷题语法」两个模块共用的阅读器 + AI 答疑 ----------
const KNOW = JSON.parse(document.getElementById("knowledge-data").textContent || "[]");
const PYDATA = JSON.parse(document.getElementById("python-data").textContent || '{"groups":[],"sections":[]}');

// ---------- 检索：一组文本段 + BM25（中文按双字切分） ----------
function kbTokens(s) {
  s = String(s || "").toLowerCase();
  const out = s.match(/[a-z][a-z0-9_+#.-]{1,}|\d{2,}/g) || [];
  for (const seg of s.match(/[一-鿿]+/g) || []) {
    if (seg.length === 1) out.push(seg);
    for (let i = 0; i < seg.length - 1; i++) out.push(seg.slice(i, i + 2));
  }
  return out;
}
class Library {
  constructor(items) { this.set(items); }
  set(items) {
    this.items = items;
    this.byId = Object.fromEntries(items.map(x => [x.id, x]));
    const df = new Map();
    let total = 0;
    for (const c of items) {
      const tf = new Map();
      for (const t of kbTokens(c.text)) tf.set(t, (tf.get(t) || 0) + 1);
      for (const t of kbTokens(c.where)) tf.set(t, (tf.get(t) || 0) + 3);
      c.tf = tf;
      c.len = [...tf.values()].reduce((a, b) => a + b, 0);
      total += c.len;
      for (const t of tf.keys()) df.set(t, (df.get(t) || 0) + 1);
    }
    this.df = df; this.avg = total / Math.max(1, items.length);
  }
  search(q, k = 6) {
    const qt = [...new Set(kbTokens(q))];
    if (!qt.length) return [];
    const n = this.items.length, scored = [];
    for (const c of this.items) {
      let s = 0;
      for (const t of qt) {
        const f = c.tf.get(t);
        if (!f) continue;
        const d = this.df.get(t) || 0;
        s += Math.log(1 + (n - d + .5) / (d + .5)) * (f * 2.2) / (f + 1.2 * (.25 + .75 * c.len / this.avg));
      }
      if (s > 0) scored.push([s, c]);
    }
    return scored.sort((a, b) => b[0] - a[0]).slice(0, k).map(x => x[1]);
  }
}
function libTools(lib) {
  return view => [{
    name: "search_notes",
    description: "在站内学习资料里做关键词检索，返回最相关的若干段（id、出处、摘要）。可以换关键词多搜几次。",
    inputSchema: { type: "object", properties: { query: { type: "string", description: "关键词或问题" }, k: { type: "integer", description: "返回几段，默认 6，最多 10" } }, required: ["query"] },
    execute: input => {
      view.progress(`在资料里搜索“${clip(String(input.query || ""), 20)}”……`);
      const hits = lib.search(String(input.query || ""), Math.min(10, Number(input.k) || 6));
      if (!hits.length) return { results: [], note: "没有找到相关段落；可以换个关键词，或者说明站内资料没有，再用通用知识回答" };
      return { results: hits.map(c => ({ id: c.id, where: c.where, preview: clip(c.text.replace(/\s+/g, " "), 200) })) };
    },
  }, {
    name: "read_section",
    description: "按 id 读取某一段资料的全文（id 来自 search_notes 的结果或目录）。",
    inputSchema: { type: "object", properties: { id: { type: "string" } }, required: ["id"] },
    execute: input => {
      const c = lib.byId[String(input.id || "")];
      if (!c) throw new Error("没有这个 id，请先用 search_notes 找到正确的 id");
      view.progress(`在读【${clip(c.where, 30)}】……`);
      return { where: c.where, text: clip(c.text, 4000) };
    },
  }];
}

// ---------- 用户自己的笔记（可选，只存本浏览器） ----------
const NOTES = {
  docs: [],
  load() { try { this.docs = JSON.parse(localStorage.getItem("tiyan:kb:docs") || "[]") || []; } catch (e) { this.docs = []; } return this; },
  save() { try { localStorage.setItem("tiyan:kb:docs", JSON.stringify(this.docs)); return true; } catch (e) { toast("浏览器存储空间不够了：删掉一些笔记再试"); return false; } },
  add(title, md) {
    const d = { id: "n" + Date.now().toString(36), title: clip(title || "我的笔记", 60), md: kbClean(md), addedAt: Date.now() };
    this.docs.push(d);
    if (!this.save()) { this.docs.pop(); return null; }
    return d;
  },
  remove(id) { this.docs = this.docs.filter(d => d.id !== id); this.save(); },
};
function kbClean(md) {
  return String(md || "")
    .replace(/<!--[\s\S]*?-->/g, "").replace(/<title>[\s\S]*?<\/title>/g, "")
    .replace(/<whiteboard[^>]*\/?>(<\/whiteboard>)?/g, "（此处原文是一张画板）")
    .replace(/<cite[^>]*title="([^"]*)"[^>]*>(<\/cite>)?/g, "《$1》")
    .replace(/<\/?(callout|p|focus|project)[^>]*>/g, "\n")
    .replace(/\n{3,}/g, "\n\n").trim();
}
function noteChunks(d) {
  const out = [];
  let path = [], buf = [], n = 0;
  const flush = () => {
    const text = buf.join("\n").trim();
    buf = [];
    if (text.replace(/^#{1,4}\s.*$/gm, "").trim().length < 2) return;
    for (let i = 0; i < text.length; i += 1800) out.push({ id: `${d.id}~${n++}`, where: `我的笔记 › ${d.title}${path.length ? " › " + path.join(" › ") : ""}`, text: text.slice(i, i + 1800) });
  };
  let inCode = false;
  for (const line of d.md.split("\n")) {
    if (/^\s*```/.test(line)) inCode = !inCode;
    const m = !inCode && line.match(/^(#{1,4})\s+(.+)$/);
    if (m && buf.join("").replace(/^#{1,4}\s.*$/gm, "").trim().length >= 2) flush();
    if (m) { path = path.slice(0, m[1].length - 1); path[m[1].length - 1] = m[2].trim(); }
    buf.push(line);
  }
  flush();
  return out;
}

// ---------- 两个模块的数据整理 ----------
function knowGroups() {
  return KNOW.map(c => ({ id: c.id, name: c.name, blurb: c.blurb, sections: c.sections.map(s => Object.assign({}, s, { course: c.name, courseId: c.id })) }));
}
function knowText(s) {
  return [`### ${s.title}`, s.summary, s.md, "要点：\n- " + (s.points || []).join("\n- "),
    (s.drill || s.interview || []).map(x => `面试问：${x.q}\n答：${x.a}`).join("\n\n")].join("\n\n");
}
function pyGroups() {
  return PYDATA.groups.map(g => ({ id: g, name: g, blurb: "", sections: PYDATA.sections.filter(s => s.group === g).map(s => Object.assign({ course: g }, s)) }));
}
function pyText(s) {
  return [`### ${s.title}`, s.summary, s.md,
    (s.examples || []).map(e => `示例「${e.title}」：\n${e.code}\n输出：\n${e.output || ""}`).join("\n\n"),
    "刷题里怎么用：" + s.algo, "易错点：\n- " + (s.pitfalls || []).join("\n- ")].join("\n\n");
}

// ---------- 通用阅读页 ----------
function viewCourse(cfg) {
  const groups = cfg.groups();
  const all = groups.flatMap(g => g.sections);
  const lib = new Library(all.map(s => ({ id: s.id, where: `${s.course} › ${s.title}`, text: cfg.text(s) })).concat(cfg.extraItems ? cfg.extraItems() : []));
  const readKey = "tiyan:read:" + cfg.key;
  const readSet = new Set(LS.get(readKey, []));
  const markRead = id => { if (!readSet.has(id)) { readSet.add(id); LS.set(readKey, [...readSet]); drawNav(); } };
  let cur = LS.get("tiyan:sec:" + cfg.key, null);
  if (!all.find(s => s.id === cur)) cur = all[0] && all[0].id;

  if (!all.length) return h("div", { class: "page" }, h("h1", null, cfg.title), h("p", { class: "muted" }, "内容还没准备好。"));

  const outline = groups.map(g => `- ${g.name}\n` + g.sections.map(s => `  - ${s.title}（id: ${s.id}）`).join("\n")).join("\n");
  const chat = new Chat({
    key: "course:" + cfg.key,
    context: () => {
      const s = all.find(x => x.id === cur);
      return cfg.teacher + "\n\n【站内资料目录】\n" + clip(outline, 6000) + (s ? `\n\n【学习者正在读】${s.course} › ${s.title}（id: ${s.id}）` : "");
    },
    placeholder: cfg.placeholder,
    intro: cfg.intro,
    actions: cfg.chatActions || [],
  });
  const rawSend = chat.send.bind(chat);
  chat.send = (prompt, o = {}) => {
    if (!o.noPrefetch) {
      const hits = lib.search(prompt, 3);
      if (hits.length) prompt += "\n\n【可能相关的站内资料（本地检索，可能不全）】\n" + hits.map(c => `[${c.id}]【${c.where}】\n${clip(c.text, 1400)}`).join("\n\n");
    }
    const tools = libTools(lib);
    const extra = cfg.extraTools;
    return rawSend(prompt, Object.assign({ tools: view => tools(view).concat(extra ? extra(view) : []) }, o));
  };
  S.liveChats = [chat];
  onLeave(() => { S.liveChats = []; if (chat.ctl) chat.ctl.abort(); });

  // 左栏：目录
  const nav = h("nav", { class: "course-nav", "aria-label": cfg.title + "目录" });
  const sel = h("select", { class: "btn sm course-select", id: "sel-" + cfg.key, "aria-label": "选择小节" });
  function drawNav() {
    nav.textContent = "";
    sel.textContent = "";
    for (const g of groups) {
      const done = g.sections.filter(s => readSet.has(s.id)).length;
      nav.append(h("div", { class: "cn-group" }, h("b", null, g.name), h("span", { class: "small faint num" }, `${done}/${g.sections.length}`)));
      const og = h("optgroup", { label: g.name });
      for (const s of g.sections) {
        const b = h("button", { type: "button", class: "cn-item" + (s.id === cur ? " on" : "") + (readSet.has(s.id) ? " read" : "") }, s.title);
        b.addEventListener("click", () => open(s.id));
        nav.append(b);
        og.append(h("option", { value: s.id, selected: s.id === cur }, s.title));
      }
      sel.append(og);
    }
  }
  sel.addEventListener("change", () => open(sel.value));

  // 搜索
  const q = h("input", { type: "search", id: "q-" + cfg.key, placeholder: cfg.searchHint, class: "course-search" });
  const results = h("div", { class: "course-results", hidden: true });
  q.addEventListener("input", () => {
    const v = q.value.trim();
    results.textContent = "";
    if (!v) { results.hidden = true; return; }
    const hits = lib.search(v, 8).filter(c => all.find(s => s.id === c.id));
    results.hidden = false;
    if (!hits.length) results.append(h("div", { class: "small faint", style: "padding:8px" }, "没找到，换个词试试，或者直接问右边的 AI。"));
    for (const c of hits) {
      const b = h("button", { type: "button", class: "cn-item" }, c.where);
      b.addEventListener("click", () => { q.value = ""; results.hidden = true; open(c.id); });
      results.append(b);
    }
  });

  // 中间：正文
  const body = h("article", { class: "course-body" });
  const selBtn = h("button", { class: "btn primary sm kb-ask", type: "button", hidden: true }, "问 AI 这段");
  let selText = "";
  selBtn.addEventListener("mousedown", e => e.preventDefault());
  selBtn.addEventListener("click", () => {
    selBtn.hidden = true;
    const s = all.find(x => x.id === cur);
    chat.send(`我没看懂这段：「${clip(selText, 1500)}」（出自【${s.course} › ${s.title}】）。请用大白话解释它在说什么、为什么，必要时举个例子。`, { label: "问 AI 这段", display: clip(selText, 80) });
  });
  body.addEventListener("mouseup", () => setTimeout(() => {
    const ws = window.getSelection();
    selText = ws ? String(ws).trim() : "";
    if (selText.length < 2 || !body.contains(ws.anchorNode)) { selBtn.hidden = true; return; }
    const r = ws.getRangeAt(0).getBoundingClientRect();
    const box = body.getBoundingClientRect();
    selBtn.style.top = (r.bottom - box.top + 6) + "px";
    selBtn.style.left = Math.max(0, Math.min(r.left - box.left, box.width - 110)) + "px";
    selBtn.hidden = false;
  }, 0));

  function open(id) {
    cur = id;
    LS.set("tiyan:sec:" + cfg.key, id);
    const s = all.find(x => x.id === id);
    const i = all.indexOf(s);
    body.textContent = "";
    const md = h("div", { class: "md course-md" });
    renderMd(md, s.md);
    const act = (label, prompt) => h("button", { class: "chip", type: "button", onclick: () => chat.send(`${prompt}\n\n【这一节：${s.course} › ${s.title}】\n${clip(cfg.text(s), 4000)}`, { label: `${label}：${clip(s.title, 18)}`, noPrefetch: true }) }, label);
    const tabsDef = cfg.sectionTabs ? cfg.sectionTabs(s) : null;
    let tab = tabsDef ? LS.get("tiyan:sectab:" + cfg.key, tabsDef[0][0]) : null;
    if (tabsDef && !tabsDef.find(t => t[0] === tab)) tab = tabsDef[0][0];
    const tabBody = h("div", { class: "stack", style: "gap:18px" });
    const tabBar = tabsDef ? h("div", { class: "tabs sec-tabs" }) : "";
    const drawTab = () => {
      tabBody.textContent = "";
      if (!tabsDef || tab === tabsDef[0][0]) tabBody.append(h("div", { class: "row course-actions" }, cfg.sectionActions.map(([l, p]) => act(l, p))), md, cfg.extra(s));
      else tabBody.append(tabsDef.find(t => t[0] === tab)[2](s));
      if (tabsDef) $$(".tab", tabBar).forEach(b => b.classList.toggle("on", b.dataset.k === tab));
    };
    if (tabsDef) for (const [kk, label] of tabsDef) {
      const b = h("button", { class: "tab", type: "button", "data-k": kk }, label);
      b.addEventListener("click", () => { tab = kk; LS.set("tiyan:sectab:" + cfg.key, kk); drawTab(); });
      tabBar.append(b);
    }
    drawTab();
    body.append(
      h("div", { class: "eyebrow" }, `${s.course} · 第 ${(groups.find(g => g.sections.includes(s)) || { sections: [s] }).sections.indexOf(s) + 1} 节`),
      h("h1", { class: "course-title" }, s.title),
      s.summary ? h("div", { class: "oneline" }, s.summary) : "",
      tabBar,
      tabBody,
      h("div", { class: "spread course-pager" },
        i > 0 ? h("button", { class: "btn sm", type: "button", onclick: () => { markRead(s.id); open(all[i - 1].id); } }, "← " + clip(all[i - 1].title, 14)) : h("span"),
        h("button", { class: "btn sm" + (readSet.has(s.id) ? "" : " primary"), type: "button", onclick: () => { markRead(s.id); if (i < all.length - 1) open(all[i + 1].id); else toast("这一模块读完了"); } }, i < all.length - 1 ? "读完了，下一节 → " + clip(all[i + 1].title, 14) : "读完了")),
      selBtn);
    drawNav();
    const top = body.getBoundingClientRect().top + window.scrollY - 80;
    if (window.scrollY > top) window.scrollTo(0, Math.max(0, top));
  }

  drawNav();
  open(cur);
  return h("div", { class: "page wide course-page" },
    h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, cfg.eyebrow), h("h1", null, cfg.title), h("p", { class: "lede" }, cfg.lede)),
    cfg.pageTabs || "",
    h("div", { class: "course-grid" },
      h("aside", { class: "course-side" }, q, results, nav),
      h("div", { class: "course-main" }, h("div", { class: "course-top" }, sel), body, cfg.footer ? cfg.footer() : ""),
      h("div", { class: "inline-ai course-chat" }, chat.el)));
}

function qaList(title, list, open) {
  if (!list || !list.length) return "";
  return h("section", { class: "stack", style: "gap:8px" }, h("h3", null, title),
    list.map(x => { const d = h("details", { class: "qa" }, h("summary", null, x.q)); const a = h("div", { class: "md small" }); renderMd(a, x.a); d.append(a); if (open) d.open = true; return d; }));
}

// ---------- AI 知识 ----------
const KNOW_TEACHER = `你是「题眼」里的 AI 学习助教，帮学习者系统学习大模型、Agent、Harness 和 AI 应用开发，并准备相关面试。
规则：
1. 先在站内资料里找依据：可以用 search_notes 搜索、read_section 读全文；用户消息里也可能附了相关段落。资料里没写的，用你自己的知识补充，并说明“站内资料没写，以下是通用知识”。
2. 讲解顺序：一句话核心 → 关键概念（用类比讲清楚）→ 具体例子 → 容易误解的点；面试相关的问题，给出能直接说出口的回答要点。
3. 引用站内资料时在句末标【课程 › 小节】，出处必须真实存在。
4. 中文，口语化、准确、简洁，用 Markdown。不确定就直说，不要编造版本号、数字和论文结论。`;

const KB_TABS = [["kb", "课程"], ["kb-daily", "每日练习"], ["kb-labs", "手写实战"], ["kb-wrong", "错题本"]];
function kbPageTabs(cur) {
  const wrong = Object.values(EX.all()).filter(r => EX.wrong(r)).length;
  return h("nav", { class: "page-tabs", "aria-label": "AI 知识" }, KB_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t,
    k === "kb-wrong" && wrong ? h("span", { class: "badge num" }, wrong) : "",
    k === "kb-daily" ? h("span", { class: "small faint" }, ` ${EX.today()}`) : "")));
}
function viewKB(sub) {
  NOTES.load();
  const key = sub || "kb";
  if (key !== "kb") {
    const body = key === "kb-daily" ? viewDaily() : key === "kb-labs" ? viewLabList() : viewWrong();
    const titles = { "kb-daily": ["每日练习", "每天 8 题，保持手感"], "kb-labs": ["手写实战", "面试要你手写的，先在这里写一遍"], "kb-wrong": ["错题本", "答错的题，再做一遍"] };
    return h("div", { class: "page wide" },
      h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "AI 知识 · " + titles[key][0]), h("h1", null, titles[key][1])),
      kbPageTabs(key), body);
  }
  return viewCourse({
    key: "ai", eyebrow: "AI 知识", title: "大模型、Agent、Harness，一节一节学透",
    lede: "五门课：大模型原理、Agent 原理、Harness 工程、AI 应用开发实战、Agent 系统架构与生产落地。每节分「讲解 / 练习 / 深挖」：讲解到原理、实现和生产落地；练习有选择题和简答题，AI 老师阅卷；深挖是面试官的层层追问，还能结合你的项目模拟面试。",
    pageTabs: kbPageTabs("kb"),
    groups: () => knowGroups(),
    text: knowText,
    extraItems: () => NOTES.docs.flatMap(noteChunks),
    searchHint: "搜索知识点，如 KV Cache、MCP、上下文压缩",
    teacher: KNOW_TEACHER,
    placeholder: "问任何不懂的：比如“harness 和 agent 框架有什么区别？”（Enter 发送）",
    intro: "我会先在站内课程里找依据再回答，并标出出处。读到不懂的地方，选中文字点「问 AI 这段」，或者用正文上方的按钮。",
    chatActions: [
      { label: "给我一条学习路线", run: c => c.send("根据站内五门课的目录，给我一条 3 周的学习路线：每天学哪几节、配哪些手写实战、学完应该能回答什么问题、怎么检验自己学会了。", { label: "学习路线" }) },
      { label: "随机考我一题", run: c => c.send("从站内课程里随机挑一个重要知识点，出一道面试式问题考我。只出题，等我回答后再点评，先别给答案。", { label: "随机考我一题", noPrefetch: true }) },
      { label: "面试高频 10 问", run: c => c.send("列出 Agent 开发 / AI 应用开发方向面试最常问的 10 个问题，按重要程度排序；每题给一句话答题要点，并标出对应的站内小节。", { label: "面试高频 10 问" }) },
    ],
    sectionActions: [
      ["讲解这一节", "请讲解这一节：一句话核心 → 关键概念（用类比）→ 一个具体例子 → 2 个最容易误解的点。"],
      ["换个说法讲", "我没太懂这一节。请完全换一种讲法：用一个生活中的类比从头讲一遍，少用术语，最后再把术语对应回去。"],
      ["落地怎么做", "如果要在真实项目里落地这一节的内容，完整方案是什么？请按：目标与指标 → 架构/流程 → 关键实现 → 上线前测试 → 线上监控与排障 的顺序讲，并给出 3 个最容易踩的坑。"],
      ["面试追问我", "扮演面试官，围绕这一节对我连续追问：先问一个基础问题，等我回答后再根据我的回答往深处追问（原理 → 实现 → 落地 → 取舍）。现在只问第一个问题。"],
      ["画图讲解", "用一张 ASCII 示意图（放在代码块里）画出这一节讲的机制或流程，然后按图一步步解释。"],
    ],
    sectionTabs: s => [["learn", "讲解"], ["practice", `练习 ${(s.choice || []).length + (s.short || []).length}`, sectionPractice], ["drill", `深挖 ${(s.drill || []).length}`, sectionDrill]],
    extra: s => h("div", { class: "stack", style: "gap:18px" },
      s.points && s.points.length ? h("section", { class: "stack", style: "gap:8px" }, h("h3", null, "速记要点"), h("ul", { class: "signals" }, s.points.map(p => h("li", null, h("span", null, p))))) : "",
      s.interview ? qaList("面试怎么答", s.interview) : "",
      s.labs && s.labs.length ? h("section", { class: "stack", style: "gap:8px" }, h("h3", null, "动手实现"), h("div", { class: "row" }, s.labs.map(id => { const l = LABS.find(x => x.id === id); return l ? h("a", { class: "chip", href: "#lab-" + id.replace(/^lab-/, "") }, "手写：" + l.title) : ""; }))) : "",
      s.related && s.related.length ? h("div", { class: "row small" }, h("span", { class: "faint" }, "相关："), s.related.map(r => { const t = knowGroups().flatMap(g => g.sections).find(x => x.id === r); return t ? h("a", { href: "#kb", onclick: e => { e.preventDefault(); LS.set("tiyan:sec:ai", r); render(); } }, t.title) : ""; })) : ""),
    footer: () => notesPanel(),
  });
}

function notesPanel() {
  const list = h("div", { class: "stack", style: "gap:4px" });
  const draw = () => {
    list.textContent = "";
    if (!NOTES.docs.length) list.append(h("p", { class: "small muted" }, "还没有。加进来的笔记只存在这个浏览器里，AI 回答时会一起检索。"));
    for (const d of NOTES.docs) {
      const del = h("button", { class: "btn ghost sm", type: "button" }, "删除");
      del.addEventListener("click", () => { NOTES.remove(d.id); draw(); toast("已删除"); });
      list.append(h("div", { class: "spread", style: "flex-wrap:nowrap" }, h("span", { style: "min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, d.title, h("span", { class: "small faint" }, `　${Math.round(d.md.length / 1000)}k 字`)), del));
    }
  };
  draw();
  const t = h("input", { id: "note-title", placeholder: "标题", style: "padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--paper)" });
  const x = h("textarea", { id: "note-text", placeholder: "粘贴你自己的学习笔记（Markdown 或纯文字）", style: "width:100%;min-height:80px;border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--paper);resize:vertical" });
  const save = h("button", { class: "btn sm", type: "button" }, "保存笔记");
  save.addEventListener("click", () => {
    if (x.value.trim().length < 10) { toast("内容太短了"); return; }
    if (NOTES.add(t.value.trim() || clip(x.value.trim().split("\n")[0], 30), x.value)) { t.value = ""; x.value = ""; draw(); toast("已保存，刷新页面后会参与检索"); }
  });
  return h("details", { class: "panel notes-panel" }, h("summary", null, h("b", null, "我的笔记（可选）"), h("span", { class: "small faint" }, "　只存在本浏览器；提问时相关段落会发给 DeepSeek")),
    list, t, x, h("div", { class: "row" }, save));
}

// ---------- Python 刷题语法 ----------
const PY_TEACHER = `你是「题眼」里的 Python 刷题语法助教。学习者用 Python 刷算法题，经常因为忘了语法糖、内置库用法或语言特性而写不出代码。
规则：
1. 先在站内 Python 模块里找依据（search_notes / read_section），再回答；资料没写的用你的知识补充。
2. 回答要能直接用到解题里：给出简短、可运行的 Python 3 代码，说明时间复杂度和容易错的地方。需要确认输出时，用 run_python 工具真实运行一下再说结果。
3. 学习者描述“我想做 X”时，直接告诉他“用 Y 写法”，再给一个最小例子。
4. 中文，简洁，用 Markdown；引用站内小节时标【分组 › 小节】。`;

function exampleBlock(ex) {
  const wrap = h("div", { class: "py-ex" });
  const head = h("div", { class: "py-ex-h" }, h("b", null, ex.title));
  const edEl = h("div", { class: "py-ex-ed" });
  const out = h("pre", { class: "py-ex-out" }, ex.output || "");
  const runBtn = h("button", { class: "btn sm", type: "button" }, icon("run"), "运行");
  const resetBtn = h("button", { class: "btn ghost sm", type: "button" }, "还原");
  head.append(h("div", { class: "row" }, resetBtn, runBtn));
  wrap.append(head, edEl, h("div", { class: "py-ex-label small faint" }, "输出"), out);
  const cm = CodeMirror(edEl, { value: ex.code, mode: "python", theme: "tiyan", lineNumbers: false, indentUnit: 4, tabSize: 4, viewportMargin: Infinity, extraKeys: { Tab: c => c.replaceSelection("    ", "end"), "Cmd-Enter": () => run(), "Ctrl-Enter": () => run() } });
  requestAnimationFrame(() => cm.refresh());
  async function run() {
    runBtn.disabled = true;
    out.textContent = S.py === "ready" ? "运行中……" : "Python 运行环境加载中……";
    out.classList.remove("err");
    try {
      const r = await Py.json("run_snippet", [cm.getValue(), ex.stdin || ""], 8000);
      out.textContent = (r.stdout || "") + (r.error ? (r.stdout ? "\n" : "") + r.error : "") || "（没有输出：用 print 打印结果）";
      if (r.error) out.classList.add("err");
    } catch (e) { out.textContent = e.message || String(e); out.classList.add("err"); }
    runBtn.disabled = false;
  }
  runBtn.addEventListener("click", run);
  resetBtn.addEventListener("click", () => { cm.setValue(ex.code); out.textContent = ex.output || ""; out.classList.remove("err"); });
  if (ex.stdin) wrap.insertBefore(h("div", { class: "small faint" }, "标准输入：", h("code", null, clip(ex.stdin.replace(/\n/g, " ⏎ "), 80))), out.previousSibling);
  return wrap;
}

function viewPython() {
  return viewCourse({
    key: "py", eyebrow: "Python 刷题语法", title: "思路有了，别卡在写法上",
    lede: "刷题最常用的语法糖、内置库和语言特性，每个例子都能直接改、直接运行。忘了怎么写就搜一下，或者问右边的 AI：“我想要 X，Python 怎么写？”",
    groups: () => pyGroups(),
    text: pyText,
    searchHint: "搜索写法，如 前缀和、大顶堆、二维数组、排序",
    teacher: PY_TEACHER,
    extraTools: view => pyTools(null)(view),
    placeholder: "比如：“想要一个默认值是 0 的字典怎么写？”“怎么按第二个元素倒序排序？”",
    intro: "告诉我你想实现什么，我给你 Python 写法和能运行的例子；需要的话我会真实运行代码确认输出。",
    chatActions: [
      { label: "最容易忘的 10 个写法", run: c => c.send("列出刷算法题时最容易忘、但最常用的 10 个 Python 写法，每个给一行代码和一句用途。", { label: "最容易忘的 10 个写法" }) },
      { label: "考我写法", run: c => c.send("出一道“我想做 X，用 Python 怎么写”的小题考我（比如把列表按某规则排序、统计频次取前 k），只出题，等我写完再点评。", { label: "考我写法", noPrefetch: true }) },
      { label: "C++/Java 写法怎么换成 Python", run: c => c.send("我习惯 C++ / Java 的哪些写法在 Python 里有更简单的等价写法？列一张对照表（优先队列、哈希表、栈、队列、排序比较器、字符串处理等）。", { label: "C++/Java → Python" }) },
    ],
    sectionActions: [
      ["讲解这一节", "请讲解这一节：先说刷题时什么时候会用到，再讲关键写法和复杂度，最后说最容易错的 2 个地方，每个写法配一行代码。"],
      ["出 3 道小练习", "根据这一节出 3 道写法小练习（每道题要求我写出 1–5 行 Python），由易到难。每题用 <details><summary>题目</summary>参考写法和输出</details> 的格式。"],
      ["用在哪些题", "这一节的写法在哪些经典算法题里会用到？列出 4–6 道题（写题名和简短说明），并给出其中一道题里的关键代码行。"],
      ["对比相近写法", "把这一节的写法和容易混淆的相近写法做一张对比表：写法、作用、复杂度、什么时候用哪个。"],
    ],
    extra: s => h("div", { class: "stack", style: "gap:18px" },
      s.examples && s.examples.length ? h("section", { class: "stack", style: "gap:10px" }, h("h3", null, "可运行的例子"), s.examples.map(exampleBlock)) : "",
      s.algo ? h("div", { class: "callout blue" }, h("b", null, "刷题里怎么用："), s.algo) : "",
      s.pitfalls && s.pitfalls.length ? h("section", { class: "stack", style: "gap:8px" }, h("h3", null, "易错点"), h("ul", { class: "signals" }, s.pitfalls.map(p => h("li", null, h("span", null, p))))) : "",
      s.complexity && s.complexity.length ? h("section", { class: "stack", style: "gap:8px" }, h("h3", null, "复杂度"), h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("tbody", null, s.complexity.map(r => h("tr", null, h("td", { class: "mono" }, r[0]), h("td", null, r[1]))))))) : ""),
  });
}
