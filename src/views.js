// ---------- 顶栏 / 路由 ----------
const NAV = [["home", "首页"], ["learn", "教程"], ["problems", "题库"], ["review", "复习"], ["quiz", "识题训练"], ["ask", "问老师"]];
let cleanups = [];
function onLeave(fn) { cleanups.push(fn); }
function parseRoute() {
  const t = decodeURIComponent((location.hash || "").slice(1));
  if (!t || t === "home") return { view: "home" };
  if (t.startsWith("t-")) return { view: "pattern", key: t.slice(2) };
  if (t.startsWith("p-")) return { view: "ws", id: t.slice(2) };
  if (["learn", "problems", "review", "quiz", "ask"].includes(t)) return { view: t };
  return { view: "home" };
}
function go(hash) { if (location.hash === "#" + hash) render(); else location.hash = hash; }
function render() {
  for (const f of cleanups) { try { f(); } catch (e) { /* ignore */ } }
  cleanups = [];
  TTS.stop();
  S.route = parseRoute();
  renderNav();
  const main = $("#main");
  main.textContent = "";
  const v = VIEWS[S.route.view] || VIEWS.home;
  main.append(v(S.route));
  window.scrollTo(0, 0);
}
let refreshQueued = false;
function softRefresh() {
  if (refreshQueued) return;
  refreshQueued = true;
  requestAnimationFrame(() => {
    refreshQueued = false;
    renderNav();
    const r = S.route;
    if (!r) return;
    if (["home", "review", "learn"].includes(r.view) || (r.view === "problems" && !S.importing)) {
      const y = window.scrollY;
      const main = $("#main");
      main.textContent = "";
      main.append(VIEWS[r.view](r));
      window.scrollTo(0, y);
    } else if (r.view === "ws" && S.ws && S.ws.refresh) S.ws.refresh();
    else if (r.view === "pattern" && S.patternRefresh) S.patternRefresh();
    for (const c of S.liveChats || []) c.sync();
  });
}
function renderNav() {
  const nav = $("#nav");
  nav.textContent = "";
  const due = dueList().length;
  for (const [k, label] of NAV) {
    const on = S.route && (S.route.view === k || (k === "learn" && S.route.view === "pattern") || (k === "problems" && S.route.view === "ws"));
    nav.append(h("a", { href: "#" + k, class: on ? "on" : "" }, label, k === "review" && due ? h("span", { class: "badge num" }, due) : ""));
  }
}
function updateChips() {
  const box = $("#chips");
  if (!box) return;
  box.textContent = "";
  const py = { loading: ["load", "Python 加载中"], ready: ["ok", "Python 就绪"], failed: ["bad", "Python 不可用"] }[S.py];
  const ai = { unknown: ["load", "AI 连接中"], ready: ["ok", "AI 老师在线"], off: ["bad", "AI 服务未连接"], nokey: ["warn", "未配置 DeepSeek"], locked: ["warn", "AI 需要密码"], needkey: ["warn", "填写 DeepSeek key"] }[S.ai] || ["warn", "AI 未连接"];
  const st = S.store === "db" ? ["ok", "进度云端同步"] : ["ok", "进度存在本浏览器"];
  for (const [cls, text, title] of [[...py, S.py === "failed" ? "判题会改用 AI 推演。原因：" + Py.error : "代码在你的浏览器里真实运行"], [...ai, AI.model ? `DeepSeek：对话用 ${AI.model}，出题和动画用 ${AI.pro}` : "AI 老师由 DeepSeek 驱动"], [...st, "换浏览器或换设备时，在「复习」页导出 / 导入进度"]]) {
    const chip = h("span", { class: "schip " + cls, title }, h("i"), text);
    if (AI.mode === "direct" && text === ai[1]) {
      chip.setAttribute("role", "button"); chip.tabIndex = 0; chip.style.cursor = "pointer"; chip.title = "设置 DeepSeek API key";
      chip.addEventListener("click", openKeyDialog);
      chip.addEventListener("keydown", e => { if (e.key === "Enter") openKeyDialog(); });
    }
    box.append(chip);
  }
  for (const c of S.liveChats || []) c.sync();
}

// ---------- 通用片段 ----------
const CIRCLE = '<svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true"><path d="M10 25 C 4 10, 38 2, 62 4 S 99 14, 94 27 S 52 41, 24 36 S 2 24, 16 11" fill="none" style="stroke:var(--red)" stroke-width="2.4" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>';
function patternTiles() {
  return h("div", { class: "pmap" }, PATTERNS.map(pt => {
    const ps = S.all.filter(p => p.pattern === pt.key);
    const done = ps.filter(p => prog(p.id) && prog(p.id).passed).length;
    return h("a", { class: "ptile", href: "#t-" + pt.key },
      h("b", null, pt.name), h("small", null, pt.blurb),
      h("div", { class: "bar", title: `通过 ${done}/${ps.length}` }, h("i", { style: `width:${ps.length ? done / ps.length * 100 : 0}%` })),
      h("small", { class: "num" }, `${done} / ${ps.length} 题`));
  }));
}
function problemRow(p) {
  const d = prog(p.id);
  return h("a", { class: "prow", href: "#p-" + p.id },
    statusPill(p.id),
    h("span", { class: "t" }, p.title, p.lc ? h("small", null, "#" + p.lc) : (p.custom ? h("small", null, p.from ? "变体" : "自建") : "")),
    h("span", null, h("span", { class: "tag" }, pname(p))),
    h("span", { class: "lv " + p.level }, LEVEL[p.level] || ""),
    h("span", { class: "small faint" }, d && d.passed && d.due ? "复习：" + relDay(d.due) : d ? `已提交 ${d.attempts || 0} 次` : ""));
}

// ---------- 首页 ----------
function viewHome() {
  const due = dueList();
  const passed = S.all.filter(p => prog(p.id) && prog(p.id).passed).length;
  const mastered = S.all.filter(p => statusOf(p.id) === "master").length;
  const week = Object.values(S.progress).reduce((n, d) => n + (d.history || []).filter(x => x.at > Date.now() - 7 * DAY).length, 0);
  const tasks = h("div", { class: "task-list" });
  for (const p of due.slice(0, 6)) {
    tasks.append(h("a", { class: "task", href: "#p-" + p.id, onclick: () => { S.redo = p.id; } },
      h("span", { class: "task-k r" }, "复"), h("span", null, h("span", { class: "task-t" }, p.title), h("br"), h("span", { class: "small faint" }, `${pname(p)} · 从空白重写 · ${relDay(prog(p.id).due)}`)), stageDots(prog(p.id).stage)));
  }
  const fresh = [];
  for (const pt of PATTERNS) { const p = S.all.find(q => q.pattern === pt.key && !q.custom && !prog(q.id)); if (p) fresh.push(p); if (fresh.length >= (due.length ? 2 : 4)) break; }
  for (const p of fresh) {
    tasks.append(h("a", { class: "task", href: "#p-" + p.id },
      h("span", { class: "task-k n" }, "新"), h("span", null, h("span", { class: "task-t" }, p.title), h("br"), h("span", { class: "small faint" }, `${pname(p)} · ${LEVEL[p.level]} · 先读一遍「${pname(p)}」教程`)), h("span", { class: "lv " + p.level }, LEVEL[p.level])));
  }
  if (!due.length && !fresh.length) tasks.append(h("p", { class: "muted" }, "内置题都做过了。去「识题训练」混合练习，或让 AI 出几道变体题。"));
  const title = due.length
    ? h("h1", null, "今天有 ", h("span", { class: "circ" }, `${due.length} 道题`, h("span", { html: CIRCLE })), "等你重写")
    : h("h1", null, "先认出", h("span", { class: "circ" }, "题眼", h("span", { html: CIRCLE })), "，再写代码");
  return h("div", { class: "page" },
    h("section", { class: "hero" },
      h("div", { class: "eyebrow" }, new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" })),
      title,
      h("p", { class: "lede" }, "不背代码，背“一句话”：每个题型记住识别信号和核心思路，代码从这句话推出来。做过的题按 1 / 3 / 7 / 15 / 30 天从空白重写，变形题也认得出来。"),
      h("div", { class: "stats" },
        h("div", { class: "stat" }, h("b", null, `${passed}`, h("small", { class: "faint", style: "font-size:14px" }, ` / ${S.all.length}`)), h("span", null, "已通过")),
        h("div", { class: "stat" }, h("b", null, due.length), h("span", null, "今天待复习")),
        h("div", { class: "stat" }, h("b", null, mastered), h("span", null, "已掌握")),
        h("div", { class: "stat" }, h("b", null, week), h("span", null, "近 7 天提交")))),
    h("div", { class: "grid-home" },
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", null, "今日任务"), h("a", { href: "#review", class: "small" }, "全部复习 →")),
        tasks,
        h("div", { class: "row" }, h("a", { class: "btn", href: "#quiz" }, "识题训练"), h("a", { class: "btn ghost", href: "#ask" }, "导入一道题"))),
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", null, "题型地图"), h("span", { class: "small faint" }, "13 个题型，覆盖面试里绝大多数题")),
        patternTiles())),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "怎么刷才记得住")),
      h("div", { class: "rules" },
        rule("记一句话，不记代码", "每个题型只记识别信号和核心一句话，比如滑动窗口：右边进、不合法缩左边、合法时更新。"),
        rule("先按题型刷，再混着刷", "同一题型连做 3–5 道找共同点；然后用识题训练打乱顺序，专门练“认出来”。"),
        rule("卡 15 分钟就看思路", "只看提示和思路，不抄代码。看懂后关掉，从空白自己写。"),
        rule("写三行笔记", "识别信号 / 核心不变量 / 我错在哪。复习时只看这三行，然后重写。"),
        rule("间隔重写", "1、3、7、15、30 天后从空白重写，15 分钟内一次通过才算掌握。"))));
}
function rule(t, d) { return h("div", { class: "rule" }, h("b", null, t), h("p", null, d)); }

// ---------- 教程 ----------
function viewLearn() {
  return h("div", { class: "page" },
    h("section", { class: "hero" },
      h("div", { class: "eyebrow" }, "教程"),
      h("h1", null, "13 个题型，每个只记一句话"),
      h("p", { class: "lede" }, "面试题大多是这些题型的变形。每个题型页里有：识别信号、核心一句话、逐行写了“为什么”的 Python 模板、常见变形和练习题。")),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "遇到新题，先问自己两个问题"), h("span", { class: "small faint" }, "输入是什么结构？要的是什么？两个答案一交叉就落到某个题型")),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable" },
        h("thead", null, h("tr", null, h("th", null, "输入 / 场景"), h("th", null, "要求的是"), h("th", null, "先想到"))),
        h("tbody", null, RECOGNIZE.map(r => h("tr", null, h("td", null, r[0]), h("td", null, r[1]), h("td", null, h("span", { class: "redpen" }, r[2])))))))),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" },
        h("h2", null, "看数据规模反推复杂度"),
        h("table", { class: "ptable" }, h("tbody", null, SCALE.map(r => h("tr", null, h("td", { class: "mono num" }, r[0]), h("td", null, r[1])))))),
      h("section", { class: "panel" },
        h("h2", null, "面试时的六步"),
        h("ol", { class: "steps" }, INTERVIEW_STEPS.map((s, i) => h("li", null, h("b", { class: "num" }, i + 1), h("span", null, h("b", null, s[0]), "：", s[1])))))),
    h("section", { class: "stack" }, h("h2", null, "题型"), patternTiles()));
}

function templateBlock(t) {
  const code = t.lines.map(l => l[0]).join("\n");
  const rows = t.lines.map(([c, w]) => {
    const codeEl = h("div", { class: "tpl-code" });
    if (c) highlightInto(codeEl, c); else codeEl.textContent = " ";
    return h("div", { class: "tpl-line" + (w ? "" : " blank") }, codeEl, h("div", { class: "tpl-why" }, w));
  });
  const listen = h("button", { class: "btn ghost sm", type: "button", hidden: !TTS.ok }, icon("speak"), "听讲解");
  let playing = false;
  listen.addEventListener("click", () => {
    if (playing) { playing = false; TTS.stop(); rows.forEach(r => r.firstChild.parentElement.classList.remove("on")); listen.lastChild.textContent = "听讲解"; return; }
    playing = true; listen.lastChild.textContent = "停止";
    const items = t.lines.map((l, i) => [i, l[1]]).filter(x => x[1]);
    let k = 0;
    const next = () => {
      rows.forEach(r => { r.children[0].style.background = ""; r.children[1].style.background = ""; });
      if (!playing || k >= items.length) { playing = false; listen.lastChild.textContent = "听讲解"; return; }
      const [i, why] = items[k++];
      rows[i].children[0].style.background = "var(--hl)"; rows[i].children[1].style.background = "var(--hl)";
      TTS.speak(`第 ${i + 1} 行。${why}`, next);
    };
    next();
  });
  onLeave(() => { playing = false; });
  const cp = h("button", { class: "btn ghost sm", type: "button" }, icon("copy"), "复制代码");
  cp.addEventListener("click", () => copyText(code, cp.lastChild));
  return h("div", { class: "tpl" },
    h("div", { class: "tpl-h" }, h("b", null, t.title), h("div", { class: "row" }, listen, cp)),
    h("div", { class: "tpl-body" }, h("div", { class: "tpl-lines" }, rows)));
}

function viewPattern({ key }) {
  const pt = PMAP[key];
  if (!pt) return viewLearn();
  const ps = S.all.filter(p => p.pattern === key);
  const list = h("div", { class: "plist" });
  const fill = () => { list.textContent = ""; for (const p of ps) list.append(problemRow(p)); };
  fill();
  S.patternRefresh = fill;
  onLeave(() => { S.patternRefresh = null; });
  const ctx = () => [TEACHER, `【当前在学的题型】${pt.name}（${pt.en}）`, `核心一句话：${pt.one}`, "识别信号：\n- " + pt.signals.join("\n- "),
    "模板：\n" + pt.templates.map(t => `${t.title}\n\`\`\`python\n${t.lines.map(l => l[0]).join("\n")}\n\`\`\``).join("\n"),
    "常见变形：\n" + pt.variants.map(v => `- ${v[0]}：${v[1]}`).join("\n"),
    "本题型的练习题：" + ps.map(p => p.title).join("、")].join("\n\n");
  const chat = new Chat({
    key: "pattern:" + key, context: ctx,
    placeholder: `关于「${pt.name}」哪里不懂？比如：为什么用 while 而不是 if？`,
    intro: `我可以逐行讲「${pt.name}」的模板、举变形题，或者出一道新题让你练。点上面的按钮，或者直接问。`,
    actions: [
      { label: "逐行讲模板", run: c => c.send(`请像老师上课一样讲「${pt.name}」：\n1. 什么时候该想到它：识别信号，各举 1 个题目例子；\n2. 逐行讲解上面的模板代码：每行为什么这么写，去掉或写错会怎样（举具体输入）；\n3. 两个常见变形分别要改模板的哪几行；\n4. 最后出一道 3 分钟能想完的小练习，只给题目，不给答案。`, { label: "逐行讲模板" }) },
      { label: "和相近题型的区别", run: c => c.send(`「${pt.name}」最容易和哪些题型混淆？请用对比表格说明：识别信号、适用条件、什么情况下会失效，并各举一道题。`, { label: "和相近题型的区别" }) },
      { label: "思路怎么变成代码", run: c => c.send(`用「${pt.name}」的一道典型题做例子，演示从“读题 → 想到这个题型 → 写出代码”的完整过程：每一步脑子里在想什么，每一句思路对应哪几行代码。用表格把“思路 → 代码 → 为什么”对应起来。`, { label: "思路怎么变成代码" }) },
      { label: "出一道新题", run: c => newProblemFromPattern(c, pt) },
    ],
  });
  S.liveChats = [chat];
  onLeave(() => { S.liveChats = []; if (chat.ctl) chat.ctl.abort(); });
  const first = ps.find(p => !p.custom);
  return h("div", { class: "page" },
    h("div", { class: "row small" }, h("a", { href: "#learn" }, "教程"), h("span", { class: "faint" }, "/"), h("span", { class: "muted" }, pt.name)),
    h("section", { class: "hero" },
      h("div", { class: "eyebrow" }, pt.en.toUpperCase()),
      h("h1", null, pt.name),
      h("div", { class: "oneline" }, pt.one)),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "识别信号"), h("ul", { class: "signals" }, pt.signals.map(s => h("li", null, h("span", null, s))))),
      h("section", { class: "panel" }, h("h2", null, "易错点"), h("ul", { class: "signals" }, pt.pitfalls.map(s => h("li", null, h("span", null, s)))),
        first ? h("div", { class: "row" }, h("a", { class: "btn", href: "#p-" + first.id, onclick: () => { S.openTab = "viz"; } }, icon("play"), `看动画：${first.title}`), h("a", { class: "btn primary", href: "#p-" + first.id }, "开始练习")) : "")),
    h("section", { class: "stack" }, h("div", { class: "panel-h" }, h("h2", null, "模板：每一行为什么这么写"), h("span", { class: "small faint" }, "左边是代码，右边是理由；鼠标悬停高亮对应行")), pt.templates.map(templateBlock)),
    h("section", { class: "panel" }, h("h2", null, "常见变形：模板要改哪里"),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("thead", null, h("tr", null, h("th", null, "变形"), h("th", null, "怎么改"))), h("tbody", null, pt.variants.map(v => h("tr", null, h("td", { style: "white-space:nowrap;font-weight:600" }, v[0]), h("td", null, v[1]))))))),
    h("section", { class: "stack" }, h("h2", null, `练习题（${ps.length}）`), list),
    h("section", { class: "stack" }, h("h2", null, "问老师"), h("div", { class: "inline-ai" }, chat.el)));
}
function newProblemFromPattern(chat, pt) {
  chat.setMode({
    hint: "出题难度：", allowEmpty: true, placeholder: "可以补充要求，比如“和字符串相关”“面试常见的”，也可以留空直接发送",
    extra: h("span", { class: "seg" }, ["easy", "medium", "hard"].map(l => { const b = h("button", { type: "button", class: l === "medium" ? "on" : "" }, LEVEL[l]); b.addEventListener("click", () => { $$("button", b.parentElement).forEach(x => x.classList.remove("on")); b.classList.add("on"); chat.level = l; }); return b; })),
    send: text => runGenerate(chat, `你是算法出题老师。请出一道考察「${pt.name}」的${LEVEL[chat.level || "medium"]}难度原创练习题，题面不要和 LeetCode 原题雷同，用来检验学习者能否在新场景里认出并用对这个题型。${text ? "学习者的要求：" + text : ""}\n核心思路参考：${pt.one}\n\n${PROBLEM_SCHEMA}`, `出一道「${pt.name}」新题`, {}),
  });
  chat.level = "medium";
}
async function runGenerate(chat, prompt, label, extra, images) {
  if (!AI.ok()) { toast(aiErr({ code: "unavailable" })); return; }
  chat.msgs.push({ role: "user", content: "", label, display: "" });
  chat.renderMsg({ role: "user", label, display: "" });
  const box = h("div", { class: "stack" });
  const status = h("div", { class: "thinking" }, "AI 正在出题……");
  box.append(status);
  chat.addNode(box);
  chat.setBusy(true);
  S.importing = true;
  try {
    const p = await generateProblem(prompt, { images, extra, step: t => { status.textContent = t; } });
    status.remove();
    box.append(h("div", null, h("b", null, p.title), "　", h("span", { class: "tag" }, pname(p)), " ", h("span", { class: "lv " + p.level }, LEVEL[p.level])),
      p.change ? h("p", { class: "small muted" }, p.change) : "",
      h("p", { class: "small faint" }, `${p.tests.length} 组用例${p.unverified ? "（未经参考解校验）" : p.fixed ? `，其中 ${p.fixed} 组的答案已用参考解校正` : "，答案已用参考解校验"}。题目已保存到题库「我的题」。`),
      h("div", { class: "row" }, h("a", { class: "btn primary sm", href: "#p-" + p.id }, "开始练习")));
    chat.msgs.push({ role: "assistant", content: `已生成题目「${p.title}」，保存在题库「我的题」里：[开始练习](#p-${p.id})` });
  } catch (e) {
    status.remove();
    box.append(h("p", { class: "small", style: "color:var(--red)" }, e && e.code ? aiErr(e) : "出题失败：" + ((e && e.message) || e)));
  } finally {
    S.importing = false;
    chat.setBusy(false);
  }
}

// ---------- 题库 ----------
const LIST_F = { pattern: "all", level: "all", status: "all" };
function viewProblems() {
  const list = h("div", { class: "plist" });
  const mine = h("div", { class: "plist" });
  const fill = () => {
    list.textContent = "";
    const ps = BUILTIN.filter(p => (LIST_F.pattern === "all" || p.pattern === LIST_F.pattern) && (LIST_F.level === "all" || p.level === LIST_F.level) && (LIST_F.status === "all" || statusOf(p.id) === LIST_F.status));
    for (const p of ps) list.append(problemRow(p));
    if (!ps.length) list.append(h("p", { class: "empty-results" }, "没有符合条件的题。"));
  };
  const chips = (arr, field) => h("div", { class: "filters" }, arr.map(([v, label]) => {
    const b = h("button", { class: "chip" + (LIST_F[field] === v ? " on" : ""), type: "button" }, label);
    b.addEventListener("click", () => { LIST_F[field] = v; $$(".chip", b.parentElement).forEach(x => x.classList.remove("on")); b.classList.add("on"); fill(); });
    return b;
  }));
  fill();
  for (const p of S.custom.slice().reverse()) {
    const del = h("button", { class: "btn ghost sm", type: "button" }, "删除");
    let armed = false;
    del.addEventListener("click", e => {
      e.preventDefault(); e.stopPropagation();
      if (!armed) { armed = true; del.textContent = "确定删除？"; del.classList.add("red"); setTimeout(() => { armed = false; del.textContent = "删除"; del.classList.remove("red"); }, 3000); return; }
      Store.remove("x:" + p.id); Store.remove("p:" + p.id); toast("已删除「" + p.title + "」");
    });
    const row = problemRow(p);
    row.lastChild.replaceWith(del);
    mine.append(row);
  }
  return h("div", { class: "page" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "题库"), h("h1", null, `${BUILTIN.length} 道高频题，按题型分组`),
      h("p", { class: "lede" }, "力扣 Hot 100 里最常考的题，题面用自己的话重写过。每道题都能在浏览器里真实运行判题；也可以导入你自己遇到的题。")),
    h("section", { class: "stack" },
      chips([["all", "全部题型"], ...PATTERNS.map(p => [p.key, p.name])], "pattern"),
      h("div", { class: "spread" }, chips([["all", "全部难度"], ["easy", "简单"], ["medium", "中等"], ["hard", "困难"]], "level"),
        chips([["all", "全部状态"], ["todo", "未做"], ["trying", "尝试中"], ["passed", "已通过"], ["due", "待复习"], ["master", "已掌握"]], "status")),
      list),
    h("section", { class: "stack" }, h("div", { class: "panel-h" }, h("h2", null, `我的题（${S.custom.length}）`), h("a", { href: "#ask", class: "small" }, "导入 / 让 AI 出题 →")),
      S.custom.length ? mine : h("p", { class: "muted small" }, "还没有。在做题页的 AI 老师里点“出个变体”，或者到「问老师」粘贴题目、上传截图，生成的题会出现在这里。")));
}

// ---------- 复习 ----------
function viewReview() {
  const done = S.all.filter(p => prog(p.id) && prog(p.id).passed);
  const end = startOfDay() + DAY - 1;
  const due = dueList();
  const soon = done.filter(p => prog(p.id).due > end && statusOf(p.id) !== "master").sort((a, b) => prog(a.id).due - prog(b.id).due);
  const master = done.filter(p => statusOf(p.id) === "master");
  const row = (p, redo) => {
    const d = prog(p.id);
    return h("a", { class: "prow", href: "#p-" + p.id, onclick: () => { if (redo) S.redo = p.id; } },
      statusPill(p.id),
      h("span", { class: "t" }, p.title, d.notes && d.notes.signal ? h("small", { style: "font-family:var(--sans)" }, "题眼：" + clip(d.notes.signal, 30)) : ""),
      h("span", null, h("span", { class: "tag" }, pname(p))),
      stageDots(d.stage),
      h("span", { class: "small " + (d.due <= end ? "" : "faint"), style: d.due < startOfDay() ? "color:var(--red)" : "" }, relDay(d.due)));
  };
  const sec = (title, arr, redo, empty) => h("section", { class: "stack" }, h("div", { class: "panel-h" }, h("h2", null, title), h("span", { class: "small faint num" }, arr.length + " 道")),
    arr.length ? h("div", { class: "plist" }, arr.map(p => row(p, redo))) : h("p", { class: "muted small" }, empty));
  const nn = nextNew();
  return h("div", { class: "page" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "复习"), h("h1", null, "从空白重写，才算真的记住"),
      h("p", { class: "lede" }, "题目通过后按 1 / 3 / 7 / 15 / 30 天安排重写。重写时编辑器是空的，先别看笔记；写完再对照三行笔记。独立做出进入下一阶段，看了提示原地不动，看了题解从头开始。"),
      done.length ? "" : h("div", { class: "row" }, h("span", { class: "muted" }, "还没有通过的题。"), nn ? h("a", { class: "btn primary", href: "#p-" + nn.id }, "做第一道：" + nn.title) : "")),
    sec("今天要重写", due, true, "今天没有到期的题。"),
    sec("接下来", soon, true, "暂无。"),
    sec("已掌握（30 天后仍能独立写出）", master, true, "坚持复习，题目会陆续进入这里。"),
    backupPanel());
}
function backupPanel() {
  const status = h("span", { class: "small muted" });
  const exp = h("button", { class: "btn sm", type: "button" }, "导出进度");
  exp.addEventListener("click", () => {
    const data = JSON.stringify({ app: "tiyan", version: 1, at: Date.now(), docs: Store.docs }, null, 1);
    const a = h("a", { href: URL.createObjectURL(new Blob([data], { type: "application/json" })), download: `题眼进度-${new Date().toISOString().slice(0, 10)}.json` });
    document.body.append(a); a.click(); a.remove();
    status.textContent = `已导出 ${Object.keys(Store.docs).length} 条记录。`;
  });
  const file = h("input", { type: "file", accept: "application/json,.json", id: "import-progress", hidden: true });
  const imp = h("button", { class: "btn sm", type: "button", onclick: () => file.click() }, "导入进度");
  file.addEventListener("change", async () => {
    const f = file.files && file.files[0];
    if (!f) return;
    try {
      const j = JSON.parse(await f.text());
      if (!j || j.app !== "tiyan" || typeof j.docs !== "object") throw new Error("不是题眼导出的进度文件");
      let n = 0;
      for (const [k, d] of Object.entries(j.docs)) {
        if (!/^[pxv]:/.test(k)) continue;
        const cur = Store.docs[k];
        if (k.startsWith("p:") && cur && (cur.lastAt || 0) > (d.lastAt || 0)) continue;
        Store.docs[k] = d; n++;
      }
      LS.set("tiyan:docs", Store.docs);
      applyDocs(); softRefresh();
      toast(`导入了 ${n} 条记录`);
    } catch (e) { status.textContent = "导入失败：" + ((e && e.message) || e); }
    file.value = "";
  });
  return h("section", { class: "panel" },
    h("div", { class: "panel-h" }, h("h2", null, "备份进度"), h("span", { class: "small faint" }, "进度存在当前浏览器里；换浏览器、换设备，或者清理浏览器数据之前，先导出一份")),
    h("div", { class: "row" }, exp, imp, file, status));
}

// ---------- 识题训练 ----------
const QUIZ = { score: 0, total: 0, cur: null, answered: false };
function viewQuiz() {
  const box = h("div", { class: "stack" });
  const scoreEl = h("span", { class: "small muted num" });
  const next = () => {
    const pool = S.all.filter(p => PMAP[p.pattern] && (!QUIZ.cur || p.id !== QUIZ.cur.id));
    QUIZ.cur = pool[Math.floor(Math.random() * pool.length)];
    QUIZ.answered = false;
    draw();
  };
  const draw = () => {
    const p = QUIZ.cur;
    scoreEl.textContent = QUIZ.total ? `本次 ${QUIZ.score} / ${QUIZ.total}` : "";
    box.textContent = "";
    const others = PATTERNS.filter(x => x.key !== p.pattern).sort(() => Math.random() - .5).slice(0, 3);
    const opts = [PMAP[p.pattern], ...others].sort(() => Math.random() - .5);
    const md = h("div", { class: "md" });
    renderMd(md, p.desc);
    const result = h("div", { class: "stack", hidden: true });
    const optsEl = h("div", { class: "quiz-opts" }, opts.map(o => {
      const b = h("button", { class: "quiz-opt", type: "button" }, o.name);
      b.addEventListener("click", () => {
        if (QUIZ.answered) return;
        QUIZ.answered = true; QUIZ.total++;
        const right = o.key === p.pattern;
        if (right) QUIZ.score++;
        $$(".quiz-opt", optsEl).forEach((x, i) => { x.disabled = true; if (opts[i].key === p.pattern) x.classList.add("right"); });
        if (!right) b.classList.add("wrong");
        scoreEl.textContent = `本次 ${QUIZ.score} / ${QUIZ.total}`;
        result.hidden = false;
        result.append(
          h("div", { class: "callout" + (right ? " blue" : "") }, h("b", null, right ? "认对了。" : `是「${pname(p)}」。`), " ", (p.hints && p.hints[0]) || ""),
          p.key ? h("p", null, h("span", { class: "faint small" }, "核心一句话　"), h("span", { class: "hl" }, p.key)) : "",
          h("div", { class: "row" }, h("span", { class: "muted" }, "这道题是：", h("b", null, p.title)), h("a", { class: "btn", href: "#p-" + p.id }, "去做这道题"), h("button", { class: "btn primary", type: "button", onclick: next }, "下一题")));
      });
      return b;
    }));
    box.append(h("div", { class: "panel" },
      h("div", { class: "spread" }, h("span", { class: "eyebrow" }, "只看题面：该用什么题型？"), h("span", { class: "lv " + p.level }, LEVEL[p.level])),
      md,
      p.examples && p.examples[0] ? h("div", { class: "example" }, h("b", null, "示例　"), `输入：${p.examples[0].input}\n输出：${p.examples[0].output}`) : "",
      optsEl, result));
  };
  if (!QUIZ.cur) next(); else draw();
  return h("div", { class: "page", style: "max-width:820px" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "识题训练"), h("h1", null, "题目一变形就不会，多半是没认出题型"),
      h("p", { class: "lede" }, "这里只给题面、隐藏题名，让你判断该用什么方法。答完会告诉你识别信号在哪句话里。每天花 5 分钟混着练，专治“换个说法就不认识”。")),
    h("div", { class: "spread" }, scoreEl, h("button", { class: "btn ghost sm", type: "button", onclick: next }, "换一题")),
    box);
}

// ---------- 问老师 / 导入题目 ----------
function viewAsk() {
  const chat = new Chat({
    key: "ask", images: true,
    context: () => TEACHER + "\n\n这是自由提问区：学习者可以问任何算法、数据结构、Python 写法或面试表达的问题，也可能贴题目或截图。回答要结合例子讲清“为什么”。站内有这些题型的教程：" + PATTERNS.map(p => p.name).join("、") + "。",
    placeholder: "问任何算法问题，或者贴一道题让老师带你分析（可以附截图）",
    intro: "我是你的算法老师。你可以问概念（“@cache 为什么能把递归变成 DP？”），贴一道题让我带你分析，或者把题目整理成练习题在线判题。",
    actions: [
      { label: "滑动窗口和双指针的区别", run: c => c.send("滑动窗口和双指针有什么区别？各自什么时候用？用两道题对比说明。") },
      { label: "DP 还是贪心？", run: c => c.send("什么时候该用动态规划，什么时候可以贪心？怎么快速判断贪心会不会出错？请举反例。") },
      { label: "@cache 为什么就是 DP", run: c => c.send("Python 里给递归函数加 @cache，为什么就等于动态规划？什么时候会出问题（递归深度、参数不可哈希）？怎么翻译成递推？") },
      { label: "面试卡住了怎么说", run: c => c.send("面试写算法题卡住了，应该怎么和面试官沟通，才能拿到提示又不扣太多分？给我几句可以直接说的话术。") },
    ],
  });
  S.liveChats = [chat];
  onLeave(() => { S.liveChats = []; if (chat.ctl) chat.ctl.abort(); });
  // 导入题目
  const ta = h("textarea", { id: "import-text", placeholder: "粘贴题目原文：力扣、牛客、面经里的题都行。包含题意、示例、约束越完整越好。" });
  ta.value = S.importDraft || "";
  ta.addEventListener("input", () => { S.importDraft = ta.value; });
  const file = h("input", { type: "file", id: "import-img", accept: "image/png,image/jpeg,image/webp,image/gif" });
  const status = h("div", { class: "small muted" });
  const btn = h("button", { class: "btn primary", type: "button" }, "整理成练习题");
  btn.addEventListener("click", async () => {
    const text = ta.value.trim();
    const img = file.files && file.files[0];
    if (!text && !img) { status.textContent = AI.images ? "先粘贴题目文字，或者选一张题目截图。" : "先粘贴题目文字。"; return; }
    if (img && !AI.images) { status.textContent = "当前环境不能把图片发给 AI，请粘贴文字。"; return; }
    if (!AI.ok()) { status.textContent = aiErr({ code: "unavailable" }); return; }
    btn.disabled = true; S.importing = true;
    try {
      const p = await generateProblem(`把学习者提供的题目${img ? "（见截图" + (text ? "和下面的文字" : "") + "）" : ""}整理成一道可以在线判题的 Python 练习题。保留原题的意思，题面用中文重新组织；补全示例、约束和测试用例；参考解要正确。\n\n${text ? "【学习者提供的题目】\n" + clip(text, 8000) + "\n\n" : ""}${PROBLEM_SCHEMA}`,
        { images: img ? [img] : undefined, extra: { imported: true }, step: t => { status.textContent = t; } });
      S.importDraft = ""; ta.value = ""; file.value = "";
      status.textContent = "";
      toast("已导入「" + p.title + "」");
      go("p-" + p.id);
    } catch (e) {
      status.textContent = e && e.code ? aiErr(e) : "导入失败：" + ((e && e.message) || e);
    } finally { btn.disabled = false; S.importing = false; }
  });
  return h("div", { class: "page wide" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "问老师"), h("h1", null, "哪里不懂，就问到懂为止"),
      h("p", { class: "lede" }, "AI 老师由 DeepSeek 驱动。回答可以朗读；做题页里的老师还能看到你的代码和真实运行结果。")),
    h("div", { class: "grid-home", style: "grid-template-columns:minmax(0,7fr) minmax(0,4fr)" },
      h("div", { class: "inline-ai", style: "max-height:none;min-height:520px" }, chat.el),
      h("section", { class: "panel import-box" },
        h("h2", null, "导入一道题"),
        h("p", { class: "small muted" }, "AI 会整理题面、补全测试用例并写参考解；页面再用参考解真实运行，重新算出每组用例的答案。DeepSeek 不能看图，请粘贴题目文字。"),
        ta,
        AI.images ? h("label", { class: "file-pick" }, icon("image"), "或上传题目截图", file) : "",
        h("div", { class: "row" }, btn), status)));
}

const VIEWS = { home: viewHome, learn: viewLearn, pattern: viewPattern, problems: viewProblems, review: viewReview, quiz: viewQuiz, ask: viewAsk, ws: r => viewWorkspace(r) };
