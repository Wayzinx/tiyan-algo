// ---------- 模拟面试：AI 面试官按你的材料出题、追问、打分、复盘 ----------
// 简历 / 项目材料只存在当前浏览器（localStorage）；面试时相关内容会发给 DeepSeek 用来出题和评分。

const MOCK_ROLES = ["测试开发（AI 方向）", "AI / Agent 应用开发", "大模型算法", "后端开发", "自定义岗位"];
const MOCK_TYPES = [
  ["mixed", "综合", "约一半是项目深挖，其余是岗位基础知识和场景设计题"],
  ["project", "项目深挖", "全部围绕候选人材料里的项目追问：为什么这么做、怎么验证、遇到什么问题、数据从哪来、如果重来怎么改"],
  ["basics", "基础知识", "岗位相关的原理和高频基础题，尽量结合候选人项目里用到的技术来问"],
  ["scenario", "场景设计", "给出贴近岗位的具体业务场景，让候选人设计方案并讲清取舍"],
  ["behavior", "行为面试", "沟通、协作、冲突、失败经历、成长与主动性，用 STAR 方式追问细节"],
  ["design", "系统设计", "给出贴近岗位的系统设计题（如设计一个某场景的 Agent、设计一个 Agent 评测平台），候选人写出方案：需求澄清、指标、架构、关键组件、数据与评测、风险与取舍、演进"],
  ["coding", "手写代码", "和岗位相关的小编程题（如工具调用循环、带退避的重试、评测指标计算、日志解析），候选人在回答里写 Python 代码，并说明复杂度、边界和测试思路"],
];
const MOCK_RUBRIC = `评分档位（每个维度和总分都按这个档位打，再按难度要求校正）：
- 9–10：超出该难度的预期。结论清楚，原理准确，有具体数据和验证方法，主动讲取舍和风险，经得起追问。
- 7–8.5：达到预期。要点基本完整、正确，有一定细节，个别地方深度或数据不够。
- 5–6.5：勉强及格。方向对，但关键要点缺失或停留在概念，缺少细节、数据或验证。
- 3–4.5：明显不足。有错误、答非所问或只有空话，需要提示才能继续。
- 0–2.5：没有回答，或基本错误。`;
const MOCK_DIMS = ["准确性", "完整度", "结构", "深度", "表达"];
const MK = {
  cfg() { return Object.assign({ role: MOCK_ROLES[0], jd: "", type: "mixed", count: 6, level: "中等", speak: false }, LS.get("tiyan:mock:cfg", {})); },
  saveCfg(c) { LS.set("tiyan:mock:cfg", c); },
  resume() { return LS.get("tiyan:mock:resume", ""); },
  sessions() { return LS.get("tiyan:mock:sessions", []); },
  saveSession(s) {
    const list = this.sessions().filter(x => x.id !== s.id);
    list.push(s);
    LS.set("tiyan:mock:sessions", list.slice(-30));
  },
  current() { return LS.get("tiyan:mock:current", null); },
  cards() { return LS.get("tiyan:mock:cards", []); },
  saveCards(c) { LS.set("tiyan:mock:cards", c); },
  setCurrent(s) { if (s) LS.set("tiyan:mock:current", s); else LS.del("tiyan:mock:current"); },
};

function mockBand(score) {
  if (score == null) return ["todo", "未评分"];
  if (score >= 8) return ["master", "优秀"];
  if (score >= 6) return ["trying", "合格"];
  return ["due", "需加强"];
}
function meter(label, value, max = 10) {
  const v = Math.max(0, Math.min(max, Number(value) || 0));
  const tone = v >= 8 ? "good" : v >= 6 ? "mid" : "low";
  return h("div", { class: "meter " + tone, title: `${label}：${v} / ${max}` },
    h("span", { class: "meter-l" }, label),
    h("span", { class: "meter-t" }, h("i", { style: `width:${v / max * 100}%` })),
    h("span", { class: "meter-v num" }, String(Math.round(v * 10) / 10)));
}
function kbLink(item) {
  const sec = item.section && KNOW.flatMap(c => c.sections).find(s => s.id === item.section);
  const label = item.topic || (sec && sec.title) || "知识点";
  const body = h("span", null, h("b", null, label), item.why ? h("span", { class: "muted" }, "：" + item.why) : "");
  if (!sec) return h("li", null, body);
  return h("li", null, body, " ", h("a", { href: "#kb", onclick: e => { e.preventDefault(); LS.set("tiyan:sec:ai", sec.id); go("kb"); } }, `去学「${sec.title}」→`));
}
function knowList() { return KNOW.flatMap(c => c.sections.map(s => `${s.id}｜${c.name} › ${s.title}`)).join("\n"); }
function materialLib(text) {
  const items = [];
  let path = [], buf = [], n = 0;
  const flush = () => { const t = buf.join("\n").trim(); buf = []; if (t.length > 20) for (let i = 0; i < t.length; i += 1500) items.push({ id: "m" + n++, where: path.join(" › ") || "材料", text: t.slice(i, i + 1500) }); };
  for (const line of String(text || "").split("\n")) {
    const m = line.match(/^(#{1,4})\s+(.+)$/);
    if (m) { flush(); path = path.slice(0, m[1].length - 1); path[m[1].length - 1] = m[2].trim(); }
    buf.push(line);
  }
  flush();
  return new Library(items);
}
function relevantMaterial(session, q, limit = 6000) {
  const text = session.resume || "";
  if (text.length <= limit) return text;
  const hits = materialLib(text).search(q, 6);
  let out = "";
  for (const c of hits) { if (out.length + c.text.length > limit) break; out += `【${c.where}】\n${c.text}\n\n`; }
  return out || text.slice(0, limit);
}
function roleLine(s) { return s.role === "自定义岗位" ? "（岗位见 JD）" : s.role; }
const CARD_FIELDS = [["name", "项目名"], ["background", "背景与目标"], ["role", "我的角色与职责"], ["actions", "关键动作 / 方案"], ["results", "量化结果（数据口径）"], ["tradeoffs", "关键取舍"], ["validation", "怎么验证的"], ["reflection", "问题与反思"]];
function cardsText(cards) {
  return (cards || []).map((c, i) => `【项目卡 ${i + 1}：${c.name || "未命名"}】\n` + CARD_FIELDS.slice(1).map(([k, t]) => c[k] ? `${t}：${c[k]}` : "").filter(Boolean).join("\n")).join("\n\n");
}
function materialsFor(s, q, limit) {
  const cards = cardsText(s.cards);
  const rest = Math.max(1500, limit - cards.length);
  return (cards ? cards + "\n\n" : "") + relevantMaterial(s, q, rest);
}

const MOCK_P = {
  plan: s => `你是一位资深技术面试官，正在面试应聘「${roleLine(s)}」的候选人。${s.jd ? "\n岗位 JD：\n" + clip(s.jd, 3000) : ""}
面试类型：${MOCK_TYPES.find(t => t[0] === s.type)[2]}。难度：${s.level}。${s.focus ? "\n这一轮的考察重点：" + s.focus : ""}
请根据候选人的材料设计 ${s.count} 道主问题：
- 项目深挖题要具体到材料里的某个项目、设计点或数字；
- 基础知识题围绕岗位核心知识，尽量和候选人用过的技术挂钩；
- 题目由易到难，覆盖不同方面，互不重复；
- 材料里如果有准备好的题目和答案，不要原样照搬，换个问法或往深处问；
- 没有材料时，按岗位通用的高频题来出。
只返回 JSON：{"opening": "面试官开场白（1–2 句，口语化）", "questions": [{"q": "问题（口语化，像真人面试官在问）", "type": "项目深挖 | 基础知识 | 场景设计 | 行为", "focus": "考察点（一句话）", "source": "依据材料哪一部分，没有就写 通用"}]}

【候选人的项目卡】（最重要的出题依据）
${cardsText(s.cards) || "（没有项目卡）"}

【候选人材料】
${clip(s.resume || "（候选人没有提供材料）", 12000)}`,

  evaluate: (s, item) => `你是资深技术面试官，在面试「${roleLine(s)}」，按「${s.level}」级别候选人的标准评分。请评估候选人对这道题的回答，严格但有建设性。
【题目】${item.q}（类型：${item.type || "综合"}；考察点：${item.focus || "未注明"}）
【候选人的回答】
${clip(item.answer, 4000)}
【之前的问答】${s.items.filter(x => x !== item && x.eval).map((x, i) => `\n${i + 1}. ${clip(x.q, 60)} —— ${x.eval.score} 分`).join("") || "无"}
【候选人材料与项目卡（用来核对事实、找出回答里没讲到的亮点）】
${materialsFor(s, item.q + "\n" + item.answer, 7000)}

${MOCK_RUBRIC}

评分（每项 0–10，可以用 0.5）：
- 准确性：事实和原理是否正确；
- 完整度：是否覆盖考察点的关键部分；
- 结构：是否结论先行、分点清楚（项目和行为题看 STAR）；
- 深度：是否讲到原理、取舍、数据和验证方法，而不只是描述做了什么；
- 表达：是否简洁具体、像面试里能说出口的话。
总分 score 是综合判断（0–10），不是简单平均；回答很短、答非所问或明显错误时要给低分。代码题还要看正确性、边界和复杂度；设计题看需求澄清、架构合理性、指标和取舍。
knowledge 从下面的站内小节里挑最相关的 id 填进 section，没有合适的就写空字符串。
站内小节：
${knowList()}

只返回 JSON：{"score": 7.5, "dims": {"准确性": 8, "完整度": 7, "结构": 6, "深度": 7, "表达": 8}, "verdict": "一句话评价", "strengths": ["做得好的地方"], "issues": ["具体问题：缺了什么、哪里不准、哪里啰嗦"], "better_answer": "优化后的示范回答：Markdown，尽量用候选人自己的项目和数据，面试里能直接说出口，200–400 字", "knowledge": [{"topic": "需要补充的知识点", "why": "为什么需要", "section": "站内小节 id 或空字符串"}], "follow_up": "需要追问时写一个追问问题（往原理、实现细节、数据口径、故障排查或取舍方向深挖，不要重复已经问过的）；回答已经很好或没有追问价值就写空字符串"}`,

  hint: (s, item) => `你是面试官，候选人在这道题上卡住了：「${item.q}」（考察点：${item.focus || "未注明"}）。
请给一个提示：只点方向——一个答题框架（比如“先讲背景，再讲方案，最后讲效果和数据”）加 1–2 个关键词，不要给出完整答案。控制在 80 字以内，直接对候选人说。
候选人材料（节选）：
${relevantMaterial(s, item.q, 2500)}`,

  report: s => `你是资深面试官，请根据这场「${roleLine(s)}」模拟面试的记录写一份复盘报告。
【问答记录】
${s.items.map((x, i) => `${i + 1}. [${x.type || "追问"}] ${x.q}\n回答：${x.skipped ? "（跳过）" : clip(x.answer, 600)}\n得分：${x.eval ? x.eval.score : "无"}；主要问题：${x.eval ? (x.eval.issues || []).slice(0, 2).join("；") : "无"}`).join("\n\n")}
站内小节（knowledge_plan 的 section 从这里选 id，没有就写空字符串）：
${knowList()}
只返回 JSON：{"level": "整体水平一句话", "summary": "总评，3–5 句", "strengths": ["优势"], "weaknesses": ["最需要改进的地方，具体"], "knowledge_plan": [{"topic": "要补的知识", "why": "为什么", "section": "站内小节 id 或空字符串"}], "next_steps": ["接下来一周具体怎么练，3–5 条"], "hire": "如果这是真实面试：通过 / 待定 / 不通过，加一句原因"}`,
};

function viewMock() {
  const root = h("div", { class: "page mock-page" });
  const cur = MK.current();
  const preset = LS.get("tiyan:mock:preset", null);
  if (preset) { LS.del("tiyan:mock:preset"); if (cur && cur.phase !== "interview") MK.setCurrent(null); }
  if (cur && cur.phase === "interview") drawInterview(root, cur);
  else if (preset) drawSetup(root, preset.focus, preset);
  else if (cur && cur.phase === "report") drawReport(root, cur);
  else drawSetup(root);
  onLeave(() => { TTS.stop(); if (MOCKCTL) MOCKCTL.abort(); stopVoice(); });
  return root;
}
let MOCKCTL = null;

// ----- 设置页 -----
function drawSetup(root, presetFocus, preset) {
  root.textContent = "";
  const cfg = Object.assign(MK.cfg(), preset && preset.type ? { type: preset.type } : {}, preset && preset.count ? { count: preset.count } : {});
  const resume = h("textarea", { id: "mock-resume", class: "mock-input", placeholder: "粘贴你的简历、项目介绍或准备稿（Markdown / 纯文字都行）。面试官会根据它出题、追问，并核对你回答里的事实。" });
  resume.value = MK.resume();
  let t = null;
  resume.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => LS.set("tiyan:mock:resume", resume.value), 400); count(); });
  const counter = h("span", { class: "small faint num" });
  const count = () => { counter.textContent = resume.value.trim() ? `${resume.value.trim().length} 字` : "还没有材料：面试官会按岗位通用题来问"; };
  count();
  const file = h("input", { type: "file", id: "mock-file", multiple: true, accept: ".pdf,.docx,.md,.markdown,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown" });
  const fileStatus = h("span", { class: "small muted" });
  file.addEventListener("change", async () => {
    const files = [...(file.files || [])];
    file.value = "";
    let added = 0;
    for (const f of files) {
      try {
        const text = await readDocFile(f, t => { fileStatus.textContent = `「${f.name}」${t}`; });
        const block = files.length > 1 || resume.value.trim() ? `# ${f.name}\n\n${text}` : text;
        resume.value = resume.value.trim() ? resume.value.replace(/\s*$/, "") + "\n\n" + block : block;
        added++;
      } catch (e) { fileStatus.textContent = `「${f.name}」导入失败：${(e && e.message) || e}`; toast(fileStatus.textContent, 4000); }
    }
    if (added) {
      LS.set("tiyan:mock:resume", resume.value); count();
      fileStatus.textContent = `已导入 ${added} 个文件，请检查一下文字是否完整（PDF 的表格和多栏排版可能会错位）。`;
    }
  });
  const role = h("select", { id: "mock-role", class: "btn sm" }, MOCK_ROLES.map(r => h("option", { value: r, selected: r === cfg.role }, r)));
  const jd = h("textarea", { id: "mock-jd", class: "mock-input", style: "min-height:70px", placeholder: "可选：粘贴岗位 JD，面试官会按 JD 的要求出题", hidden: cfg.role !== "自定义岗位" && !cfg.jd });
  jd.value = cfg.jd || "";
  const jdToggle = h("button", { class: "btn ghost sm", type: "button", onclick: () => { jd.hidden = !jd.hidden; } }, "粘贴 JD");
  let type = cfg.type;
  const typeSeg = h("div", { class: "seg" }, MOCK_TYPES.map(([k, label, desc]) => {
    const b = h("button", { type: "button", class: k === type ? "on" : "", title: desc }, label);
    b.addEventListener("click", () => { type = k; $$("button", typeSeg).forEach(x => x.classList.remove("on")); b.classList.add("on"); typeDesc.textContent = desc; });
    return b;
  }));
  const typeDesc = h("p", { class: "small muted" }, MOCK_TYPES.find(x => x[0] === type)[2]);
  const countSel = h("select", { id: "mock-count", class: "btn sm" }, [4, 6, 8, 10].map(n => h("option", { value: n, selected: n === Number(cfg.count) }, `${n} 道主问题`)));
  const levelSel = h("select", { id: "mock-level", class: "btn sm" }, ["基础", "中等", "资深"].map(l => h("option", { value: l, selected: l === cfg.level }, `难度：${l}`)));
  const speak = h("input", { type: "checkbox", id: "mock-speak", checked: !!cfg.speak && TTS.ok, disabled: !TTS.ok });
  const depthSel = h("select", { id: "mock-depth", class: "btn sm", title: "回答不够深时，面试官对同一道题最多追问几层" }, [0, 1, 2, 3].map(n => h("option", { value: n, selected: n === Number(cfg.depth ?? 2) }, n ? `每题最多追问 ${n} 层` : "不追问")));
  const dbl = h("input", { type: "checkbox", id: "mock-double", checked: !!cfg.double });
  const status = h("div", { class: "small muted" });
  const startBtn = h("button", { class: "btn primary", type: "button" }, "开始面试");
  startBtn.addEventListener("click", async () => {
    if (!AI.ok()) { status.textContent = aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" }); if (S.ai === "needkey") openKeyDialog(); return; }
    const c = { role: role.value, jd: jd.value.trim(), type, count: Number(countSel.value), level: levelSel.value, speak: speak.checked, depth: Number(depthSel.value), double: dbl.checked };
    MK.saveCfg(c);
    LS.set("tiyan:mock:resume", resume.value);
    const s = Object.assign({ id: "m" + Date.now().toString(36), at: Date.now(), phase: "plan", resume: resume.value.trim(), cards: MK.cards(), items: [], idx: 0, focus: presetFocus || "" }, c);
    startBtn.disabled = true;
    status.textContent = "面试官正在看你的材料、准备问题……（大约 20–60 秒）";
    MOCKCTL = new AbortController();
    try {
      const plan = await AI.ask(MOCK_P.plan(s), { json: true, tier: "complex", signal: MOCKCTL.signal });
      const qs = (plan && Array.isArray(plan.questions) ? plan.questions : []).filter(q => q && q.q).slice(0, 12);
      if (!qs.length) throw new Error("面试官没出题，再试一次");
      s.opening = String(plan.opening || "你好，我们开始吧。");
      s.plan = qs.map(q => ({ q: String(q.q), type: String(q.type || ""), focus: String(q.focus || ""), source: String(q.source || "") }));
      s.phase = "interview";
      s.items = [Object.assign({ main: 0 }, s.plan[0])];
      MK.setCurrent(s);
      drawInterview(root, s);
    } catch (e) {
      status.textContent = e && e.code ? aiErr(e) : "开始失败：" + ((e && e.message) || e);
    } finally { startBtn.disabled = false; MOCKCTL = null; }
  });

  const hist = MK.sessions().filter(x => x.report);
  root.append(
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "模拟面试"), h("h1", null, "让 AI 面试官先问你一遍"),
      h("p", { class: "lede" }, "面试官根据你的简历和项目材料出题、追问；每答完一题给五个维度的评分、问题清单、优化后的示范回答和需要补的知识；结束后出一份复盘报告。")),
    presetFocus ? h("div", { class: "callout blue" }, h("b", null, preset && preset.type ? "这一轮的重点：" : "这一轮针对上次的薄弱点："), presetFocus) : "",
    h("div", { class: "grid-home", style: "grid-template-columns:minmax(0,7fr) minmax(0,5fr)" },
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", null, "你的材料"), counter),
        resume,
        h("div", { class: "row" }, h("label", { class: "file-pick" }, "或导入 PDF / Word（.docx）/ .md / .txt", file)), fileStatus,
        redactPanel(resume, () => { LS.set("tiyan:mock:resume", resume.value); count(); }),
        h("p", { class: "small faint" }, "文件在你的浏览器里本地解析，不会上传；材料只保存在这个浏览器里。面试时，相关内容会发给 DeepSeek 用来出题和评分。")),
      h("section", { class: "panel" },
        h("h2", null, "这一场怎么面"),
        h("div", { class: "row" }, role, jdToggle), jd,
        h("div", { class: "stack", style: "gap:6px" }, typeSeg, typeDesc),
        h("div", { class: "row" }, countSel, levelSel, depthSel),
        h("label", { class: "row small", style: "gap:6px" }, speak, TTS.ok ? "面试官朗读问题" : "这个浏览器不支持朗读"),
        h("label", { class: "row small", style: "gap:6px" }, dbl, "每题评两次取平均（更稳定，耗时和费用翻倍）"),
        h("details", { class: "qa" }, h("summary", null, "评分标准"), h("div", { class: "md small" }, ...MOCK_RUBRIC.split("\n").map(l => h("div", null, l)))),
        h("p", { class: "small faint" }, "分数是 AI 估算的，只能当参考：同一个回答多次评分可能有 1 分左右的波动。"),
        h("div", { class: "row" }, startBtn), status)),
    cardsPanel(resume),
    hist.length ? historyPanel(root, hist) : "");
}

// ----- 项目卡：把项目讲成结构化的证据（背景、角色、动作、量化结果、取舍、验证、反思） -----
function cardsPanel(resumeTA) {
  const box = h("div", { class: "stack", style: "gap:10px" });
  const status = h("span", { class: "small muted" });
  const draw = () => {
    box.textContent = "";
    const cards = MK.cards();
    if (!cards.length) box.append(h("p", { class: "small muted" }, "还没有项目卡。项目卡会作为面试官出题的主要依据，比整段简历更容易被深挖到点子上。"));
    cards.forEach((c, i) => {
      const det = h("details", { class: "qa card-edit", open: !c.name });
      const del = h("button", { class: "btn ghost sm", type: "button" }, "删除");
      del.addEventListener("click", e => { e.preventDefault(); const cs = MK.cards(); cs.splice(i, 1); MK.saveCards(cs); draw(); });
      det.append(h("summary", null, c.name || "新项目卡", h("span", { class: "small faint" }, `　${CARD_FIELDS.filter(([k]) => c[k]).length}/${CARD_FIELDS.length} 项已填`)));
      const grid = h("div", { class: "card-grid" });
      for (const [k, t] of CARD_FIELDS) {
        const el = h(k === "name" ? "input" : "textarea", { id: `card-${c.id}-${k}`, class: "mock-input", style: k === "name" ? "min-height:0;padding:7px 10px" : "min-height:64px", placeholder: t + (k === "results" ? "：写清数字和口径，比如“采纳率 70%（人工抽检 200 条）”" : "") });
        el.value = c[k] || "";
        el.addEventListener("input", () => { const cs = MK.cards(); cs[i][k] = el.value; MK.saveCards(cs); if (k === "name") det.querySelector("summary").firstChild.textContent = el.value || "新项目卡"; });
        grid.append(h("label", { class: "card-f" }, h("span", { class: "small faint" }, t), el));
      }
      det.append(grid, h("div", { class: "row" }, del));
      box.append(det);
    });
  };
  draw();
  const add = h("button", { class: "btn sm", type: "button" }, "新增项目卡");
  add.addEventListener("click", () => { const cs = MK.cards(); cs.push({ id: "c" + Date.now().toString(36) }); MK.saveCards(cs); draw(); });
  const ai = h("button", { class: "btn sm", type: "button" }, "让 AI 从材料里整理项目卡");
  ai.addEventListener("click", async () => {
    const text = resumeTA.value.trim();
    if (text.length < 50) { status.textContent = "先在上面填好材料。"; return; }
    if (!AI.ok()) { status.textContent = aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" }); return; }
    ai.disabled = true; status.textContent = "AI 在整理……（大约 20–40 秒）";
    try {
      const r = await AI.ask(`从下面的候选人材料里整理出项目卡（最多 5 个最重要的项目）。字段：name 项目名、background 背景与目标、role 我的角色与职责、actions 关键动作 / 方案、results 量化结果（写清口径）、tradeoffs 关键取舍、validation 怎么验证的、reflection 问题与反思。
规则：只用材料里写到的事实，不要编造；材料没写的字段写成“（待补充：应该写什么）”，比如 results 没有数字就写“（待补充：上线后的采纳率 / 节省人力，口径是什么）”。
只返回 JSON：{"cards": [{"name": "", "background": "", "role": "", "actions": "", "results": "", "tradeoffs": "", "validation": "", "reflection": ""}]}

【候选人材料】
${clip(text, 14000)}`, { json: true, tier: "default" });
      const got = (r && Array.isArray(r.cards) ? r.cards : []).slice(0, 5).map(c => Object.assign({ id: "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5) }, Object.fromEntries(CARD_FIELDS.map(([k]) => [k, String((c && c[k]) || "")]))));
      if (!got.length) throw new Error("没整理出项目");
      MK.saveCards(MK.cards().concat(got)); draw();
      status.textContent = `整理出 ${got.length} 张项目卡，请逐项检查、补上“待补充”的内容。`;
    } catch (e) { status.textContent = e && e.code ? aiErr(e) : "整理失败：" + ((e && e.message) || e); }
    finally { ai.disabled = false; }
  });
  return h("section", { class: "panel" },
    h("div", { class: "panel-h" }, h("h2", null, "项目卡"), h("span", { class: "small faint" }, "背景 → 角色 → 动作 → 量化结果 → 取舍 → 验证 → 反思")),
    box, h("div", { class: "row" }, add, ai, status));
}

function historyPanel(root, hist) {
  const scores = hist.map(x => x.report.overall);
  let spark = "";
  if (scores.length >= 2) {
    const W = 220, H = 44, n = scores.length;
    const x = i => 6 + i * (W - 12) / (n - 1), y = v => H - 6 - (v / 10) * (H - 12);
    const pts = scores.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const last = scores[n - 1];
    spark = h("div", { class: "row", style: "gap:10px" }, h("span", { class: "small faint" }, "总分趋势"),
      h("span", { html: `<svg class="spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="历次总分：${scores.join("、")}"><line x1="6" x2="${W - 6}" y1="${y(6)}" y2="${y(6)}" class="spark-ref"/><polyline points="${pts}" class="spark-line"/>${scores.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="${i === n - 1 ? 4 : 2.5}" class="${i === n - 1 ? "spark-end" : "spark-dot"}"><title>第 ${i + 1} 场：${v} 分</title></circle>`).join("")}</svg>` }),
      h("b", { class: "num" }, `${last} 分`));
  }
  return h("section", { class: "panel" },
    h("div", { class: "panel-h" }, h("h2", null, "历次面试"), spark),
    h("div", { class: "plist", style: "border:0" }, hist.slice().reverse().map(s => {
      const [cls, band] = mockBand(s.report.overall);
      const row = h("button", { type: "button", class: "prow mock-hrow" },
        h("span", { class: "pill " + cls }, band),
        h("span", { class: "t" }, `${s.role} · ${MOCK_TYPES.find(t => t[0] === s.type)[1]}`, h("small", { style: "font-family:var(--sans)" }, s.report.level || "")),
        h("span", { class: "small faint" }, fmtDate(s.at)),
        h("span", { class: "num", style: "font-weight:600" }, s.report.overall),
        h("span", { class: "small faint" }, `${s.items.filter(x => x.eval).length} 题`));
      row.addEventListener("click", () => drawReport(root, s, true));
      return row;
    })));
}

// ----- 面试进行中 -----
function drawInterview(root, s) {
  root.textContent = "";
  const log = h("div", { class: "mock-log" });
  const board = h("aside", { class: "panel mock-board" });
  const ta = h("textarea", { id: "mock-answer", class: "mock-input", placeholder: "像真实面试一样回答：先说结论，再展开。（Cmd/Ctrl + Enter 提交）" });
  const timer = h("span", { class: "small faint num" });
  const sendBtn = h("button", { class: "btn primary", type: "button" }, "提交回答");
  const hintBtn = h("button", { class: "btn sm", type: "button" }, "我卡住了，给点提示");
  const skipBtn = h("button", { class: "btn ghost sm", type: "button" }, "跳过这题");
  const voiceBtn = h("button", { class: "btn sm", type: "button", hidden: !SpeechRec }, "语音回答");
  const endBtn = h("button", { class: "btn sm", type: "button" }, "结束面试，出报告");
  const status = h("div", { class: "small muted" });
  const composer = h("div", { class: "mock-composer" }, ta, h("div", { class: "spread" }, h("div", { class: "row" }, sendBtn, voiceBtn, hintBtn, skipBtn), timer), status);
  root.append(
    h("div", { class: "spread" }, h("div", null, h("div", { class: "eyebrow" }, `模拟面试 · ${s.role} · ${MOCK_TYPES.find(t => t[0] === s.type)[1]}`), h("h1", { style: "font-size:24px" }, "面试进行中")), endBtn),
    h("div", { class: "mock-grid" }, h("div", { class: "stack", style: "gap:14px;min-width:0" }, log, composer), board));

  let started = Date.now();
  const tick = setInterval(() => { const sec = Math.round((Date.now() - started) / 1000); timer.textContent = `本题用时 ${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`; }, 1000);
  onLeave(() => clearInterval(tick));

  function drawLog() {
    log.textContent = "";
    log.append(h("div", { class: "mock-msg ask" }, h("div", { class: "mock-who" }, "面试官"), h("div", null, s.opening)));
    s.items.forEach((it, i) => {
      log.append(h("div", { class: "mock-msg ask" }, h("div", { class: "mock-who" }, it.follow ? "面试官 · 追问" : `面试官 · 第 ${it.main + 1} 题`, it.type && !it.follow ? h("span", { class: "tag" }, it.type) : ""), h("div", null, it.q),
        it.hint ? h("div", { class: "small muted", style: "margin-top:6px" }, "提示：" + it.hint) : ""));
      if (it.answer || it.skipped) log.append(h("div", { class: "mock-msg me" }, h("div", { class: "mock-who" }, "我"), h("div", { style: "white-space:pre-wrap" }, it.skipped ? "（跳过）" : it.answer)));
      if (it.eval) log.append(evalCard(it, i === s.items.length - 1 || i === s.items.length - 2));
    });
    drawBoard();
  }
  function drawBoard() {
    const done = s.items.filter(x => x.eval);
    const avg = done.length ? Math.round(done.reduce((a, x) => a + Number(x.eval.score || 0), 0) / done.length * 10) / 10 : null;
    board.textContent = "";
    board.append(h("div", { class: "eyebrow" }, "目前得分"),
      h("div", { class: "mock-avg num" }, avg == null ? "—" : String(avg), h("span", null, " / 10")),
      h("div", { class: "small faint" }, `主问题 ${Math.min(s.plan.length, (s.items[s.items.length - 1] || { main: 0 }).main + 1)} / ${s.plan.length}　已评分 ${done.length} 题`),
      done.length ? h("div", { class: "stack", style: "gap:6px" }, MOCK_DIMS.map(d => meter(d, done.reduce((a, x) => a + Number((x.eval.dims || {})[d] || 0), 0) / done.length))) : h("p", { class: "small muted" }, "答完第一题后这里显示各维度平均分。"),
      h("div", { class: "sep" }),
      h("ol", { class: "mock-qlist" }, s.plan.map((q, i) => {
        const its = s.items.filter(x => x.main === i && x.eval);
        const sc = its.length ? its[0].eval.score : null;
        return h("li", { class: i === (s.items[s.items.length - 1] || {}).main ? "on" : "" }, h("span", null, clip(q.q, 34)), h("b", { class: "num" }, sc == null ? "" : sc));
      })));
  }
  function currentItem() { return s.items[s.items.length - 1]; }
  function ask() {
    const it = currentItem();
    started = Date.now();
    drawLog();
    ta.value = LS.get("tiyan:mock:draft", "") || "";
    ta.focus();
    log.lastChild && log.lastChild.scrollIntoView({ block: "nearest", behavior: "smooth" });
    if (s.speak && TTS.ok) TTS.speak(it.q);
  }
  function save() { MK.setCurrent(s); }
  ta.addEventListener("input", () => LS.set("tiyan:mock:draft", ta.value));
  ta.addEventListener("keydown", e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submit(); } });
  const busy = b => { [sendBtn, hintBtn, skipBtn, endBtn].forEach(x => { x.disabled = b; }); ta.disabled = b; };

  async function submit() {
    const it = currentItem();
    const ans = ta.value.trim();
    if (ans.length < 4) { status.textContent = "先写下你的回答（哪怕只有思路）。"; return; }
    stopVoice();
    TTS.stop();
    it.answer = ans; it.seconds = Math.round((Date.now() - started) / 1000);
    LS.del("tiyan:mock:draft");
    save(); drawLog();
    busy(true);
    status.textContent = "面试官在评估你的回答……（大约 15–40 秒）";
    MOCKCTL = new AbortController();
    try {
      if (s.double) {
        const sig = MOCKCTL.signal;
        const [a, b] = await Promise.all([AI.ask(MOCK_P.evaluate(s, it), { json: true, tier: "complex", signal: sig }), AI.ask(MOCK_P.evaluate(s, it) + "\n（这是独立的第二次评分，请重新独立判断。）", { json: true, tier: "complex", signal: sig })]);
        const ea = normEval(a), eb = normEval(b);
        const avg = (x, y) => Math.round((x + y) / 2 * 2) / 2;
        it.eval = Object.assign({}, ea, { score: avg(ea.score, eb.score), dims: Object.fromEntries(MOCK_DIMS.map(d => [d, avg(ea.dims[d], eb.dims[d])])), scores: [ea.score, eb.score], follow_up: ea.follow_up || eb.follow_up });
      } else {
        const ev = await AI.ask(MOCK_P.evaluate(s, it), { json: true, tier: "complex", signal: MOCKCTL.signal });
        it.eval = normEval(ev);
      }
      status.textContent = "";
      next(it);
    } catch (e) {
      status.textContent = e && e.code ? aiErr(e) : "评估失败：" + ((e && e.message) || e);
      if (e && e.code === "cancelled") return;
      status.append(" ", h("button", { class: "btn sm", type: "button", onclick: () => { ta.value = it.answer; it.answer = ""; save(); submit(); } }, "重新评估"));
    } finally { busy(false); MOCKCTL = null; save(); }
  }
  function next(it) {
    const followCount = s.items.filter(x => x.main === it.main && x.follow).length;
    if (it.eval && it.eval.follow_up && followCount < (s.depth ?? 1) && !it.skipped) {
      s.items.push({ main: it.main, follow: true, q: it.eval.follow_up, type: "追问", focus: it.focus });
    } else if (it.main + 1 < s.plan.length) {
      s.items.push(Object.assign({ main: it.main + 1 }, s.plan[it.main + 1]));
    } else {
      save(); drawLog();
      status.textContent = "";
      status.append("问题都问完了。", h("button", { class: "btn primary sm", type: "button", onclick: finish }, "生成复盘报告"));
      ta.disabled = true; sendBtn.disabled = true; hintBtn.disabled = true; skipBtn.disabled = true;
      return;
    }
    save(); ask();
  }
  sendBtn.addEventListener("click", submit);
  skipBtn.addEventListener("click", () => { const it = currentItem(); it.skipped = true; it.answer = ""; LS.del("tiyan:mock:draft"); next(it); });
  hintBtn.addEventListener("click", async () => {
    const it = currentItem();
    busy(true); status.textContent = "面试官在想怎么提示你……";
    MOCKCTL = new AbortController();
    try {
      const r = await AI.ask(MOCK_P.hint(s, it), { tier: "default", signal: MOCKCTL.signal });
      it.hint = r.text.trim(); save(); drawLog(); status.textContent = "";
    } catch (e) { status.textContent = aiErr(e); }
    finally { busy(false); MOCKCTL = null; ta.focus(); }
  });
  voiceBtn.addEventListener("click", () => toggleVoice(ta, voiceBtn, status));
  async function finish() {
    if (!s.items.some(x => x.eval)) { MK.setCurrent(null); drawSetup(root); return; }
    busy(true); status.textContent = "面试官在写复盘报告……（大约 20–60 秒）";
    MOCKCTL = new AbortController();
    try {
      const r = await AI.ask(MOCK_P.report(s), { json: true, tier: "complex", signal: MOCKCTL.signal });
      s.report = normReport(r, s);
      s.phase = "report";
      MK.saveSession(s); MK.setCurrent(s);
      drawReport(root, s);
    } catch (e) { status.textContent = e && e.code ? aiErr(e) : "生成报告失败：" + ((e && e.message) || e); busy(false); }
    finally { MOCKCTL = null; }
  }
  endBtn.addEventListener("click", finish);
  ask();
}

function normEval(e) {
  if (!e || typeof e !== "object") throw new Error("评估结果格式不对，点“重新评估”");
  const num = v => Math.max(0, Math.min(10, Math.round((Number(v) || 0) * 2) / 2));
  const dims = {};
  for (const d of MOCK_DIMS) dims[d] = num(e.dims && e.dims[d]);
  return {
    score: num(e.score), dims, verdict: String(e.verdict || ""),
    strengths: arrStr(e.strengths, 5), issues: arrStr(e.issues, 6),
    better: String(e.better_answer || ""),
    knowledge: (Array.isArray(e.knowledge) ? e.knowledge : []).slice(0, 5).map(k => ({ topic: String((k && k.topic) || ""), why: String((k && k.why) || ""), section: String((k && k.section) || "") })),
    follow_up: String(e.follow_up || "").trim(),
  };
}
function normReport(r, s) {
  const done = s.items.filter(x => x.eval);
  const overall = done.length ? Math.round(done.reduce((a, x) => a + x.eval.score, 0) / done.length * 10) / 10 : 0;
  return {
    overall, level: String((r && r.level) || ""), summary: String((r && r.summary) || ""),
    strengths: arrStr(r && r.strengths, 6), weaknesses: arrStr(r && r.weaknesses, 6),
    knowledge: (Array.isArray(r && r.knowledge_plan) ? r.knowledge_plan : []).slice(0, 8).map(k => ({ topic: String((k && k.topic) || ""), why: String((k && k.why) || ""), section: String((k && k.section) || "") })),
    next: arrStr(r && r.next_steps, 6), hire: String((r && r.hire) || ""),
    dims: Object.fromEntries(MOCK_DIMS.map(d => [d, done.length ? Math.round(done.reduce((a, x) => a + (x.eval.dims[d] || 0), 0) / done.length * 10) / 10 : 0])),
  };
}

function evalCard(it, open) {
  const e = it.eval;
  const [cls, band] = mockBand(e.score);
  const better = h("div", { class: "md" });
  renderMd(better, e.better || "（没有示范回答）");
  const card = h("details", { class: "mock-eval", open });
  card.append(
    h("summary", null, h("span", { class: "mock-score num" }, String(e.score), h("small", null, " / 10")), h("span", { class: "pill " + cls }, band), h("span", { class: "mock-verdict" }, e.verdict),
      e.scores ? h("span", { class: "small " + (Math.abs(e.scores[0] - e.scores[1]) > 1.5 ? "" : "faint"), style: Math.abs(e.scores[0] - e.scores[1]) > 1.5 ? "color:var(--amber)" : "" }, `两次评分 ${e.scores.join(" / ")}${Math.abs(e.scores[0] - e.scores[1]) > 1.5 ? "，分歧较大" : ""}`) : "",
      h("span", { class: "small faint" }, "AI 估算")),
    h("div", { class: "mock-eval-body" },
      h("div", { class: "stack", style: "gap:6px" }, MOCK_DIMS.map(d => meter(d, e.dims[d]))),
      e.strengths.length ? h("div", null, h("h3", null, "亮点"), h("ul", { class: "mock-ul good" }, e.strengths.map(x => h("li", null, x)))) : "",
      e.issues.length ? h("div", null, h("h3", null, "可以改进"), h("ul", { class: "mock-ul bad" }, e.issues.map(x => h("li", null, x)))) : "",
      h("details", { class: "qa", open: true }, h("summary", null, "优化后的回答（参考着说）"), better),
      e.knowledge.length ? h("div", null, h("h3", null, "需要补充的知识"), h("ul", { class: "mock-ul" }, e.knowledge.map(kbLink))) : "",
      TTS.ok && e.better ? h("div", { class: "row" }, h("button", { class: "btn ghost sm", type: "button", onclick: ev => { ev.preventDefault(); TTS.speak(e.better); } }, icon("speak"), "朗读示范回答")) : ""));
  return card;
}

// ----- 复盘报告 -----
function drawReport(root, s, fromHistory) {
  root.textContent = "";
  const r = s.report;
  const [cls, band] = mockBand(r.overall);
  const done = s.items.filter(x => x.eval || x.skipped);
  root.append(
    h("div", { class: "spread" }, h("div", null, h("div", { class: "eyebrow" }, `复盘报告 · ${s.role} · ${MOCK_TYPES.find(t => t[0] === s.type)[1]} · ${fmtDate(s.at)}`), h("h1", { style: "font-size:26px" }, r.level || "这场面试的复盘")),
      h("div", { class: "row" },
        h("button", { class: "btn", type: "button", onclick: () => downloadFile(`模拟面试-${fmtDate(s.at)}-${s.role}.md`, sessionMarkdown(s), "text/markdown") }, "导出 Markdown"),
        h("button", { class: "btn", type: "button", onclick: () => { MK.setCurrent(null); drawSetup(root); } }, "回到设置"),
        h("button", { class: "btn primary", type: "button", onclick: () => { MK.setCurrent(null); drawSetup(root, r.weaknesses.slice(0, 3).join("；")); window.scrollTo(0, 0); } }, "针对薄弱点再来一轮"))),
    h("div", { class: "mock-grid" },
      h("div", { class: "stack", style: "gap:16px;min-width:0" },
        h("section", { class: "panel" },
          h("div", { class: "mock-hero" },
            h("div", null, h("div", { class: "small faint" }, "总分"), h("div", { class: "mock-hero-num num" }, String(r.overall), h("span", null, " / 10")), h("span", { class: "pill " + cls }, band)),
            h("div", { class: "stack", style: "gap:6px;flex:1;min-width:220px" }, MOCK_DIMS.map(d => meter(d, r.dims[d])))),
          r.summary ? h("p", null, r.summary) : "",
          r.hire ? h("div", { class: "callout" }, h("b", null, "面试官的判断："), r.hire) : "",
          h("p", { class: "small faint" }, `总分是各题分数的平均；所有分数和判断都是 AI 按评分标准估算的（难度：${s.level}${s.double ? "，每题评两次取平均" : ""}），只能当参考，不代表真实面试结果。`)),
        h("div", { class: "grid-2" },
          h("section", { class: "panel" }, h("h2", null, "优势"), h("ul", { class: "mock-ul good" }, r.strengths.map(x => h("li", null, x)))),
          h("section", { class: "panel" }, h("h2", null, "最需要改进"), h("ul", { class: "mock-ul bad" }, r.weaknesses.map(x => h("li", null, x))))),
        r.knowledge.length ? h("section", { class: "panel" }, h("h2", null, "要补的知识"), h("ul", { class: "mock-ul" }, r.knowledge.map(kbLink))) : "",
        r.next.length ? h("section", { class: "panel" }, h("h2", null, "接下来一周怎么练"), h("ol", { class: "steps" }, r.next.map((x, i) => h("li", null, h("b", { class: "num" }, i + 1), h("span", null, x))))) : "",
        h("section", { class: "stack" }, h("h2", null, "逐题回顾"), done.map((it, i) => h("div", { class: "panel", style: "gap:10px" },
          h("div", { class: "small faint" }, it.follow ? `第 ${it.main + 1} 题 · 追问` : `第 ${it.main + 1} 题 · ${it.type || ""}`),
          h("b", null, it.q),
          h("div", { class: "mock-answer-view" }, it.skipped ? "（跳过）" : it.answer),
          it.eval ? evalCard(it, false) : "")))),
      h("aside", { class: "panel mock-board" }, h("div", { class: "eyebrow" }, "各题得分"),
        h("div", { class: "stack", style: "gap:6px" }, s.items.filter(x => x.eval).map((x, i) => meter(`${x.follow ? "追问" : "第 " + (x.main + 1) + " 题"}`, x.eval.score))),
        fromHistory ? "" : h("p", { class: "small faint" }, "这场面试已保存，在「模拟面试」首页的历次面试里能找到。"))));
  window.scrollTo(0, 0);
}

// ----- 语音输入（浏览器支持时） -----
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition || null;
let REC = null;
function stopVoice() { if (REC) { try { REC.stop(); } catch (e) { /* ignore */ } REC = null; } }
function toggleVoice(ta, btn, status) {
  if (REC) { stopVoice(); btn.textContent = "语音回答"; return; }
  if (!SpeechRec) return;
  const rec = new SpeechRec();
  rec.lang = "zh-CN"; rec.continuous = true; rec.interimResults = true;
  const base = ta.value ? ta.value.replace(/\s*$/, "") + "\n" : "";
  rec.onresult = e => {
    let text = "";
    for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
    ta.value = base + text;
    LS.set("tiyan:mock:draft", ta.value);
  };
  rec.onerror = e => {
    status.textContent = e.error === "not-allowed" ? "浏览器没有麦克风权限：在地址栏左侧允许麦克风后再试。"
      : e.error === "network" ? "这个浏览器的语音识别服务连不上（Chrome 需要访问谷歌服务）。可以改用系统听写：Mac 上按两下 fn 键。"
      : "语音识别出错：" + e.error;
  };
  rec.onend = () => { if (REC === rec) { REC = null; btn.textContent = "语音回答"; } };
  try { rec.start(); REC = rec; btn.textContent = "停止语音"; status.textContent = "正在听……说完点“停止语音”，再检查一下文字。"; }
  catch (e) { status.textContent = "语音识别启动失败。"; }
}

function sessionMarkdown(s) {
  const r = s.report || {};
  const lines = [`# 模拟面试复盘：${s.role} · ${(MOCK_TYPES.find(t => t[0] === s.type) || [, ""])[1]}`, "", `- 时间：${new Date(s.at).toLocaleString("zh-CN")}`, `- 难度：${s.level}；追问深度：${s.depth ?? 1}；${s.double ? "每题评两次取平均" : "每题评一次"}`, `- 总分：${r.overall ?? "—"} / 10（AI 估算，仅供参考）`, ""];
  if (r.level) lines.push(`## 整体`, "", r.level, "", r.summary || "", "", r.hire ? `面试官判断：${r.hire}` : "", "");
  if (r.dims) lines.push("## 各维度", "", ...MOCK_DIMS.map(d => `- ${d}：${r.dims[d]}`), "");
  if (r.strengths && r.strengths.length) lines.push("## 优势", "", ...r.strengths.map(x => "- " + x), "");
  if (r.weaknesses && r.weaknesses.length) lines.push("## 最需要改进", "", ...r.weaknesses.map(x => "- " + x), "");
  if (r.knowledge && r.knowledge.length) lines.push("## 要补的知识", "", ...r.knowledge.map(k => `- ${k.topic}${k.why ? "：" + k.why : ""}`), "");
  if (r.next && r.next.length) lines.push("## 接下来怎么练", "", ...r.next.map((x, i) => `${i + 1}. ${x}`), "");
  lines.push("## 逐题记录", "");
  s.items.forEach(it => {
    lines.push(`### ${it.follow ? "追问" : "第 " + (it.main + 1) + " 题"}：${it.q}`, "", "**我的回答**", "", it.skipped ? "（跳过）" : (it.answer || "（未作答）"), "");
    if (it.eval) {
      const e = it.eval;
      lines.push(`**得分**：${e.score} / 10（${MOCK_DIMS.map(d => `${d} ${e.dims[d]}`).join("，")}）`, "", e.verdict ? `**评价**：${e.verdict}` : "", "");
      if (e.strengths.length) lines.push("**亮点**", "", ...e.strengths.map(x => "- " + x), "");
      if (e.issues.length) lines.push("**可以改进**", "", ...e.issues.map(x => "- " + x), "");
      if (e.better) lines.push("**优化后的回答**", "", e.better, "");
    }
  });
  return lines.filter((l, i, a) => !(l === "" && a[i - 1] === "")).join("\n");
}
