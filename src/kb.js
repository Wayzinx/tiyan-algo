// ---------- 知识库：导入自己的学习资料，边读边问 AI ----------
// 资料只存在当前浏览器（localStorage），不会进代码仓库；提问时只把相关段落发给 DeepSeek。

const KB_BUILTIN = {
  id: "builtin-agent", builtin: true, title: "Agent 与大模型开发速览（内置）", source: "内置", addedAt: 0,
  md: `# Agent 与大模型开发速览（内置）

> 一份公开知识的入门地图。读完能说清：大模型在做什么、Agent 由什么组成、Harness 负责什么、怎么评测。更深的内容导入你自己的资料。

## 1. 大模型在做什么

大模型（LLM）本质上是“根据前文预测下一个 token”。所有能力——回答、写代码、调用工具——都来自这一个动作反复执行。

- **token 与上下文窗口**：模型一次能看到的内容有上限（上下文窗口），超出的部分它完全看不到。
- **采样**：temperature 越高输出越发散；需要稳定结果（判题、抽取）时调低。
- **幻觉**：模型只保证“读起来通顺”，不保证正确。缓解方法是给它依据（检索）、让它调用工具验证，并要求标注出处。

## 2. 提示词与结构化输出

- **system prompt** 放长期规则（角色、边界、输出格式），用户消息放本次任务和数据。
- **few-shot**：给 1–3 个输入输出示例，比长篇描述更能稳定格式。
- **结构化输出**：要求 JSON（JSON mode / JSON Schema），程序才能可靠解析；解析失败要能重试或降级。
- 好提示词的三要素：任务说清楚、数据给全、输出格式写死。

## 3. Agent 是什么：模型 + 工具 + 循环

Agent = 大模型在一个循环里反复“思考 → 调用工具 → 观察结果”，直到任务完成。

1. 模型读当前上下文，决定下一步：直接回答，还是调用某个工具；
2. 运行框架执行工具，把结果放回上下文；
3. 重复，直到模型给出最终答案，或者触发停止条件（轮数上限、预算、错误、人工中断）。

和普通对话的区别：Agent 能**行动**（读写文件、查数据、跑代码），也能**根据结果调整**下一步。

## 4. 工具调用与工具设计

工具调用（function calling）：开发者用 JSON Schema 描述工具的名字、用途和参数，模型输出“调用哪个工具、传什么参数”，由程序真正执行。

工具设计原则：
- **少而确定**：几个职责清晰的工具，好过几十个重叠的工具；
- **描述写给模型看**：什么时候用、返回什么、有什么限制；
- **错误信息要可行动**：告诉模型错在哪、怎么改，它才能自己修正；
- **返回要精简**：只返回需要的字段，避免把上下文撑爆；
- **危险操作要确认**：删除、付款、外发这类操作加人工确认或权限控制。

## 5. 上下文工程

模型的表现很大程度取决于“这一刻上下文里有什么”。上下文工程就是决定放什么、什么时候放、放多少。

- **预加载 vs 按需检索**：长期规则和项目约定预先放进去（如项目说明文件）；具体资料让 Agent 自己搜索、读取。
- **压缩**：对话太长时，把早期内容总结成摘要，保留决策和关键事实，丢掉过程细节。
- **隔离**：把大任务拆给子 Agent，子 Agent 在独立上下文里干活，只把结论交回来，主上下文保持干净。
- 上下文越长，模型越容易漏看中间的信息，所以“少而准”比“多而全”好。

## 6. 记忆与 RAG（检索增强生成）

RAG：先从资料库检索相关片段，再把片段和问题一起交给模型回答。

- **切分（chunking）**：按标题、段落切，块太大检索不准，太小丢上下文；
- **检索**：关键词检索（BM25）擅长专有名词，向量检索擅长语义相近；两者结合（混合检索）+ 重排序效果最好；
- **引用**：要求模型标注出处，方便核对，也能减少编造；
- **评测**：召回率（该找的找到没有）、答案正确率、引用是否真的支持结论。
- 常见失败：没检索到 → 答非所问；检索到了但模型没用；资料过期。

## 7. Harness：Agent 的运行框架

Harness 是包在模型外面、让 Agent 能稳定跑起来的那层工程：

- **循环控制**：何时继续、何时停（轮数、预算、超时）；
- **工具执行**：沙箱、权限、并发、超时、重试；
- **上下文管理**：加载规则文件、压缩历史、子 Agent 隔离；
- **扩展点**：钩子（hooks）、插件、自定义工具（如 MCP 服务器）；
- **状态与可观测性**：会话持久化、断点恢复、日志和链路追踪、成本统计。

一句话：**模型决定“做什么”，Harness 决定“能不能做、怎么安全地做、做完怎么收尾”。**

## 8. 多 Agent 与编排

- **编排者 + 工作者**：主 Agent 拆任务、分派给多个子 Agent 并行做，再汇总；
- **流水线**：固定步骤（检索 → 生成 → 校验），每步一个专门的 Agent 或程序；
- 什么时候不要用多 Agent：任务本身是强顺序的、需要共享大量上下文的，拆开反而更慢、更容易出错。

## 9. 评测（Eval）

- **离线评测集**：一批带标准答案或评分标准的任务，每次改动都跑一遍防回归；
- **LLM 评审（LLM-as-judge）**：用模型按评分标准打分，要先校准它和人工打分的一致性；
- **轨迹评测**：不只看结果，也看过程——工具调用是否合理、有没有多余步骤、有没有越权；
- **指标**：成功率、pass@k、平均轮数、成本、耗时、人工接管率。

## 10. 面试高频问题清单

1. Agent 和普通的大模型调用有什么区别？
2. 工具调用是怎么实现的？模型怎么知道该调用哪个工具？
3. 上下文窗口不够用怎么办？
4. RAG 的完整流程是什么？效果不好时怎么排查？
5. 怎么减少幻觉？
6. Harness 负责哪些事？模型能力变强后，哪些 Harness 逻辑可以去掉？
7. 多 Agent 什么时候有用，什么时候反而有害？
8. 怎么评测一个 Agent？
9. 怎么保证 Agent 的安全（权限、危险操作、提示词注入）？
10. 如果让你从零搭一个 Agent，你会怎么设计？
`,
};

const KB = {
  docs: [], chunks: [], byId: {}, index: null,
  load() {
    let list = [];
    try { list = JSON.parse(localStorage.getItem("tiyan:kb:docs") || "[]"); } catch (e) { list = []; }
    this.docs = [KB_BUILTIN].concat(Array.isArray(list) ? list : []);
    this.reindex();
  },
  save() {
    const mine = this.docs.filter(d => !d.builtin);
    try { localStorage.setItem("tiyan:kb:docs", JSON.stringify(mine)); return true; }
    catch (e) { toast("浏览器存储空间不够了：删掉一些资料再导入"); return false; }
  },
  add(title, md, source) {
    const doc = { id: "d" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5), title: clip(title || "未命名资料", 60), md: kbClean(md), source: source || "导入", addedAt: Date.now() };
    this.docs.push(doc);
    if (!this.save()) { this.docs.pop(); return null; }
    this.reindex();
    return doc;
  },
  remove(id) { this.docs = this.docs.filter(d => d.id !== id || d.builtin); this.save(); this.reindex(); },
  reindex() {
    this.chunks = [];
    for (const d of this.docs) this.chunks.push(...kbChunk(d));
    this.byId = Object.fromEntries(this.chunks.map(c => [c.id, c]));
    const df = new Map();
    let total = 0;
    for (const c of this.chunks) {
      const tf = new Map();
      for (const t of kbTokens(c.text)) tf.set(t, (tf.get(t) || 0) + 1);
      for (const t of kbTokens(c.where)) tf.set(t, (tf.get(t) || 0) + 2);
      c.tf = tf;
      c.len = [...tf.values()].reduce((a, b) => a + b, 0);
      total += c.len;
      for (const t of tf.keys()) df.set(t, (df.get(t) || 0) + 1);
    }
    this.index = { df, avg: total / Math.max(1, this.chunks.length), n: this.chunks.length };
  },
  search(q, k = 6, docId) {
    const qt = [...new Set(kbTokens(q))];
    if (!qt.length) return [];
    const { df, avg, n } = this.index;
    const scored = [];
    for (const c of this.chunks) {
      if (docId && c.docId !== docId) continue;
      let s = 0;
      for (const t of qt) {
        const f = c.tf.get(t);
        if (!f) continue;
        const idf = Math.log(1 + (n - (df.get(t) || 0) + .5) / ((df.get(t) || 0) + .5));
        s += idf * (f * 2.2) / (f + 1.2 * (.25 + .75 * c.len / avg));
      }
      if (s > 0) scored.push([s, c]);
    }
    return scored.sort((a, b) => b[0] - a[0]).slice(0, k).map(x => x[1]);
  },
  outline(maxChars = 5000) {
    const lines = [];
    for (const d of this.docs) {
      lines.push(`- 《${d.title}》`);
      const secs = this.chunks.filter(c => c.docId === d.id && c.level <= 3 && c.part === 0);
      for (const c of secs.slice(0, 60)) lines.push(`${"  ".repeat(Math.min(3, c.level))}- ${c.heading}（id: ${c.id}）`);
    }
    let out = lines.join("\n");
    if (out.length > maxChars) out = out.slice(0, maxChars) + "\n  ……（目录太长已截断，用 search_notes 搜索）";
    return out;
  },
};

// 清理飞书导出的 Markdown 里的专有标签
function kbClean(md) {
  return String(md || "")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<title>[\s\S]*?<\/title>/g, "")
    .replace(/<whiteboard[^>]*\/?>(<\/whiteboard>)?/g, "（此处原文是一张画板）")
    .replace(/<cite[^>]*title="([^"]*)"[^>]*>(<\/cite>)?/g, "《$1》")
    .replace(/<callout[^>]*>/g, "\n").replace(/<\/callout>/g, "\n")
    .replace(/<\/?(p|focus|project|mention[^>]*)>/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
function kbPlain(md) { return md.replace(/<[^>]+>/g, "").replace(/!\[[^\]]*\]\([^)]*\)/g, "").trim(); }
function kbTokens(s) {
  s = String(s || "").toLowerCase();
  const out = s.match(/[a-z][a-z0-9_+#.-]{1,}|\d{2,}/g) || [];
  for (const seg of s.match(/[一-鿿]+/g) || []) {
    if (seg.length === 1) out.push(seg);
    for (let i = 0; i < seg.length - 1; i++) out.push(seg.slice(i, i + 2));
  }
  return out;
}
function kbChunk(doc) {
  const out = [];
  const lines = doc.md.split("\n");
  let path = [], buf = [], level = 0, inCode = false, n = 0;
  const body = () => kbPlain(buf.join("\n")).replace(/^#{1,4}\s.*$/gm, "").trim();
  const flush = () => {
    const text = buf.join("\n").trim();
    const empty = body().length < 2;
    buf = [];
    if (empty) return;
    const parts = [];
    if (text.length <= 1800) parts.push(text);
    else {
      let cur = "";
      for (const para of text.split(/\n{2,}/)) {
        if (cur && cur.length + para.length > 1500) { parts.push(cur); cur = ""; }
        cur += (cur ? "\n\n" : "") + para;
      }
      if (cur) parts.push(cur);
    }
    const heading = path.filter(Boolean).slice(-1)[0] || doc.title;
    const where = `${doc.title} › ${path.filter(Boolean).join(" › ") || "开头"}`;
    parts.forEach((p, i) => out.push({ id: `${doc.id}~${n++}`, docId: doc.id, heading: heading + (parts.length > 1 ? `（${i + 1}/${parts.length}）` : ""), where, level: level || 1, part: i, text: p }));
  };
  for (const line of lines) {
    if (/^\s*```/.test(line)) inCode = !inCode;
    const m = !inCode && line.match(/^(#{1,4})\s+(.+?)\s*#*\s*$/);
    if (m) {
      // 只有标题、没有正文的章节（比如“第 1 章”下面直接是小节）并入下一节，避免出现空白段
      if (body().length >= 2) flush();
      level = m[1].length;
      path = path.slice(0, level - 1);
      path[level - 1] = m[2].replace(/[*_`]/g, "").trim();
    }
    buf.push(line);
  }
  flush();
  return out;
}

function kbTools() {
  return view => [{
    name: "search_notes",
    description: "在学习者导入的学习资料里做关键词检索，返回最相关的若干段（id、出处、开头摘要）。可以多次用不同关键词搜索。",
    inputSchema: { type: "object", properties: { query: { type: "string", description: "关键词或问题，中英文都可以" }, k: { type: "integer", description: "返回几段，默认 6，最多 10" } }, required: ["query"] },
    execute: input => {
      view.progress(`在资料里搜索“${clip(String(input.query || ""), 20)}”……`);
      const hits = KB.search(String(input.query || ""), Math.min(10, Number(input.k) || 6));
      if (!hits.length) return { results: [], note: "没有找到相关段落，可以换个关键词，或者说明资料里没有" };
      return { results: hits.map(c => ({ id: c.id, where: c.where, preview: clip(kbPlain(c.text).replace(/\s+/g, " "), 220) })) };
    },
  }, {
    name: "read_section",
    description: "按 id 读取资料里某一段的全文（id 来自 search_notes 的结果或目录）。",
    inputSchema: { type: "object", properties: { id: { type: "string" } }, required: ["id"] },
    execute: input => {
      const c = KB.byId[String(input.id || "")];
      if (!c) throw new Error("没有这个 id，请先用 search_notes 找到正确的 id");
      view.progress(`在读【${clip(c.where, 30)}】……`);
      return { where: c.where, text: clip(kbPlain(c.text), 3500) };
    },
  }];
}

const KB_TEACHER = `你是「题眼」里的 AI 学习助教，帮学习者吸收 Agent、大模型、Agent 开发、Harness 等知识，也帮他准备面试。
规则：
1. 先在资料里找依据：可以用 search_notes 搜索、read_section 读全文；用户消息里也可能已附上相关片段。回答以资料为准；资料里没有的，用你自己的知识补充，并明确说“资料里没写，以下是通用知识”。
2. 讲解顺序：一句话核心 → 关键概念（用类比讲清楚）→ 具体例子 → 容易误解的点；涉及面试时，给出可以直接说出口的回答要点。
3. 引用资料时，在句末用【文档名 › 小节】标注出处，出处必须真实存在。
4. 用中文，口语化、准确、简洁；用 Markdown。不确定就直说，不要编造。`;

const KBS = { doc: null, sec: null, outlineOpen: true };

function viewKB() {
  KB.load();
  if (!KBS.doc || !KB.docs.find(d => d.id === KBS.doc)) KBS.doc = KB.docs[0].id;
  const secs = () => KB.chunks.filter(c => c.docId === KBS.doc);
  if (!KBS.sec || !KB.byId[KBS.sec] || KB.byId[KBS.sec].docId !== KBS.doc) KBS.sec = (secs()[0] || {}).id;

  const chat = new Chat({
    key: "kb",
    context: () => KB_TEACHER + "\n\n【学习者的资料目录】\n" + KB.outline(),
    placeholder: "问任何不懂的：比如“harness 和 agent 框架有什么区别？”（Enter 发送）",
    intro: "我会先在你的资料里找依据再回答，并标出出处。左边读到哪里不懂，选中文字点「问 AI」，或者用这一节的按钮。",
    actions: [
      { label: "这些资料讲了什么", run: c => c.send("请根据资料目录，给我一张学习地图：这些资料分别讲什么、彼此什么关系、建议按什么顺序学、每部分学完应该能回答什么问题。", { label: "学习地图", tools: kbTools() }) },
      { label: "随机考我一题", run: c => c.send("从我的资料里随机挑一个重要知识点，出一道面试式问题考我。只出题，等我回答后再点评，先别给答案。", { label: "随机考我一题", tools: kbTools() }) },
      { label: "面试高频题", run: c => c.send("根据我的资料，列出面试最可能问的 8 个问题，按重要程度排序；每题给一句话答题要点，并标注出处。", { label: "面试高频题", tools: kbTools() }) },
    ],
  });
  const send = chat.send.bind(chat);
  chat.send = (prompt, o = {}) => {
    // 先在本地检索，把最相关的几段直接附在问题后面，少一轮工具调用
    if (!o.noPrefetch) {
      const hits = KB.search(prompt, 4);
      if (hits.length) prompt += "\n\n【可能相关的资料片段（本地检索结果，可能不全）】\n" + hits.map(c => `[${c.id}]【${c.where}】\n${clip(kbPlain(c.text), 1200)}`).join("\n\n");
    }
    return send(prompt, Object.assign({ tools: kbTools() }, o));
  };
  S.liveChats = [chat];
  onLeave(() => { S.liveChats = []; if (chat.ctl) chat.ctl.abort(); });

  // 左侧：资料选择 + 目录 + 当前章节
  const docSel = h("select", { id: "kb-doc", class: "btn sm", style: "max-width:100%" }, KB.docs.map(d => h("option", { value: d.id, selected: d.id === KBS.doc }, d.title)));
  docSel.addEventListener("change", () => { KBS.doc = docSel.value; KBS.sec = (secs()[0] || {}).id; drawReader(); });
  const outline = h("div", { class: "kb-outline" });
  const reader = h("div", { class: "md kb-reader" });
  const where = h("div", { class: "small faint" });
  const nav = h("div", { class: "row" });
  const selBtn = h("button", { class: "btn primary sm kb-ask", type: "button", hidden: true }, "问 AI 这段");
  let selText = "";
  selBtn.addEventListener("mousedown", e => e.preventDefault());
  selBtn.addEventListener("click", () => {
    const c = KB.byId[KBS.sec];
    selBtn.hidden = true;
    chat.send(`我没看懂这段：「${clip(selText, 1500)}」（出自【${c ? c.where : ""}】）。请用大白话解释，讲清它在说什么、为什么，必要时举个例子。`, { label: "问 AI 这段", display: clip(selText, 80), noPrefetch: false });
  });
  reader.addEventListener("mouseup", () => setTimeout(() => {
    const s = window.getSelection();
    selText = s ? String(s).trim() : "";
    if (selText.length < 2 || !reader.contains(s.anchorNode)) { selBtn.hidden = true; return; }
    const r = s.getRangeAt(0).getBoundingClientRect();
    const box = reader.parentElement.getBoundingClientRect();
    selBtn.style.top = (r.bottom - box.top + reader.parentElement.scrollTop + 6) + "px";
    selBtn.style.left = Math.max(8, Math.min(r.left - box.left, box.width - 120)) + "px";
    selBtn.hidden = false;
  }, 0));
  const secAct = (label, prompt) => {
    const b = h("button", { class: "chip", type: "button" }, label);
    b.addEventListener("click", () => {
      const c = KB.byId[KBS.sec];
      if (!c) return;
      chat.send(`${prompt}\n\n【这一节：${c.where}】\n${clip(kbPlain(c.text), 3500)}`, { label: `${label}：${clip(c.heading, 20)}`, noPrefetch: true });
    });
    return b;
  };
  const actions = h("div", { class: "row" },
    secAct("讲解这一节", "请讲解这一节：一句话核心 → 关键概念（用类比）→ 一个具体例子 → 2 个最容易误解的点。"),
    secAct("出题考我", "根据这一节出 3 道自测题，由浅入深，最后一道是面试式开放题。每题用 <details><summary>题目</summary>参考答案</details> 的格式。"),
    secAct("面试怎么问", "如果面试官围绕这一节提问，最可能问哪 3 个问题？给出能直接说出口的回答要点（每个 3–5 句），并指出可能的追问方向。"),
    secAct("画图讲解", "用一张 ASCII 示意图（放在代码块里）画出这一节讲的机制或流程，然后按图一步步解释。"));
  function drawReader() {
    const list = secs();
    outline.textContent = "";
    for (const c of list) {
      if (c.part > 0) continue;
      const a = h("button", { type: "button", class: "kb-ol" + (c.id === KBS.sec ? " on" : ""), style: `padding-left:${8 + (c.level - 1) * 12}px` }, c.heading);
      a.addEventListener("click", () => { KBS.sec = c.id; drawReader(); });
      outline.append(a);
    }
    const c = KB.byId[KBS.sec];
    renderMd(reader, c ? c.text : "这份资料是空的。");
    where.textContent = c ? c.where : "";
    nav.textContent = "";
    const i = list.findIndex(x => x.id === KBS.sec);
    nav.append(
      h("button", { class: "btn sm", type: "button", disabled: i <= 0, onclick: () => { KBS.sec = list[i - 1].id; drawReader(); reader.parentElement.scrollTop = 0; } }, "上一节"),
      h("span", { class: "small faint num" }, `${i + 1} / ${list.length}`),
      h("button", { class: "btn sm", type: "button", disabled: i >= list.length - 1, onclick: () => { KBS.sec = list[i + 1].id; drawReader(); reader.parentElement.scrollTop = 0; } }, "下一节"));
    selBtn.hidden = true;
  }
  drawReader();

  // 资料管理：导入 / 删除
  const fileIn = h("input", { type: "file", id: "kb-files", accept: ".md,.markdown,.txt,text/markdown,text/plain", multiple: true });
  const pTitle = h("input", { id: "kb-paste-title", placeholder: "标题（可选）", style: "padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--paper)" });
  const pText = h("textarea", { id: "kb-paste-text", placeholder: "或者直接粘贴文字：从飞书文档全选复制、网页文章、笔记都可以", style: "width:100%;min-height:90px;border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--paper);resize:vertical" });
  const status = h("div", { class: "small muted" });
  const docList = h("div", { class: "stack", style: "gap:4px" });
  const drawDocs = () => {
    docList.textContent = "";
    for (const d of KB.docs) {
      const n = KB.chunks.filter(c => c.docId === d.id).length;
      const del = d.builtin ? h("span", { class: "small faint" }, "内置") : h("button", { class: "btn ghost sm", type: "button" }, "删除");
      if (!d.builtin) {
        let armed = false;
        del.addEventListener("click", () => {
          if (!armed) { armed = true; del.textContent = "确定删除？"; setTimeout(() => { armed = false; del.textContent = "删除"; }, 3000); return; }
          KB.remove(d.id); toast("已删除《" + d.title + "》"); render();
        });
      }
      docList.append(h("div", { class: "spread", style: "flex-wrap:nowrap" }, h("span", { style: "min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }, d.title, h("span", { class: "small faint" }, `　${n} 段 · ${Math.round(d.md.length / 1000)}k 字`)), del));
    }
  };
  drawDocs();
  fileIn.addEventListener("change", async () => {
    let ok = 0;
    for (const f of fileIn.files || []) {
      if (f.size > 1500000) { status.textContent = `《${f.name}》太大了（超过 1.5MB），没有导入。`; continue; }
      const text = await f.text();
      const t = (text.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || f.name.replace(/\.(md|markdown|txt)$/i, "");
      if (KB.add(t.trim(), text, "文件")) ok++;
    }
    fileIn.value = "";
    if (ok) { toast(`导入了 ${ok} 份资料`); KBS.doc = KB.docs[KB.docs.length - 1].id; KBS.sec = null; render(); }
  });
  const pasteBtn = h("button", { class: "btn sm", type: "button" }, "保存粘贴的内容");
  pasteBtn.addEventListener("click", () => {
    const text = pText.value.trim();
    if (text.length < 20) { status.textContent = "内容太短了。"; return; }
    const t = pTitle.value.trim() || (text.match(/^#\s+(.+)$/m) || [])[1] || clip(text.split("\n")[0], 30);
    if (KB.add(t, text, "粘贴")) { toast("已保存《" + t + "》"); KBS.doc = KB.docs[KB.docs.length - 1].id; KBS.sec = null; render(); }
  });

  return h("div", { class: "page wide" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "知识库"),
      h("h1", null, "边读资料，边问 AI"),
      h("p", { class: "lede" }, "导入你的学习资料（Agent、大模型、Harness、面试手册……），左边按章节读，右边随时问。AI 会先在你的资料里找依据再回答，并标出出处。")),
    h("div", { class: "kb-grid" },
      h("section", { class: "panel kb-left" },
        h("div", { class: "spread" }, docSel, h("button", { class: "btn ghost sm", type: "button", onclick: () => { KBS.outlineOpen = !KBS.outlineOpen; outline.hidden = !KBS.outlineOpen; } }, "目录")),
        outline,
        h("div", { class: "kb-read-wrap" }, where, reader, selBtn),
        actions, nav),
      h("div", { class: "inline-ai kb-chat" }, chat.el)),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "我的资料"), h("span", { class: "small faint" }, "只存在这个浏览器里，不会上传到网站或代码仓库")),
      docList,
      h("div", { class: "callout blue small" }, "提问时，会把和问题相关的几段资料发给 DeepSeek 用来回答。含公司内部信息、客户信息或个人隐私的资料，先确认是否允许发给外部 AI 服务再导入。"),
      h("div", { class: "grid-2" },
        h("div", { class: "stack" }, h("b", null, "导入文件"), h("label", { class: "file-pick" }, "选择 .md / .txt 文件（可多选）", fileIn), h("p", { class: "small muted" }, "飞书文档可以用「…」→「下载为」→ Markdown 导出后再导入。")),
        h("div", { class: "stack" }, h("b", null, "粘贴文字"), pTitle, pText, h("div", { class: "row" }, pasteBtn))),
      status));
}
