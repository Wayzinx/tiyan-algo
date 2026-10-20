// ---------- 做题页 ----------
const P_UNDERSTAND = `请帮我读懂这道题（先别给解法）：
1. 用大白话复述题意：输入是什么、要输出什么、有哪些容易忽略的约定；
2. 用示例 1 手推一遍，用表格或分步列出；
3. 列出 2–4 个要注意的边界情况；
4. 圈出“题眼”：题目里哪几个词或条件暗示了该往哪个方向想（只说方向，不说具体做法）；
5. 最后问我一个检验理解的小问题。
控制在 400 字以内。`;
const P_HINT = n => `我卡住了，请给我第 ${n} 级提示（一共 4 级）：
1 级 = 题型方向：该往哪个题型想，从题目哪句话看出来，暴力解的瓶颈在哪；
2 级 = 核心思路：要维护什么状态 / 不变量是什么；
3 级 = 步骤：伪代码级别的步骤；
4 级 = 关键代码：最关键的 3–6 行，并解释每行为什么这么写。
只给第 ${n} 级，不要越级。如果我已经写了一部分代码，顺着我的思路往下引导；方向错了就直接指出来。`;
const P_IDEA = idea => `这是我的思路：「${idea}」
请帮我把思路变成代码：
1. 先判断思路对不对、能不能通过数据规模；有漏洞就用一个具体反例指出来；
2. 把思路拆成 3–6 步，用表格列出：思路里的这句话 → 对应的 Python 写法 → 为什么这么写；
3. 给一份代码骨架：结构完整，关键的 2–3 行留成 \`# TODO: ...\` 让我自己填；
4. 最后用一句话总结：这个思路落成代码的关键是什么。`;
const P_IDEA0 = `我还没有思路，请带我从题目一步步推到代码：
1. 暴力怎么做、复杂度多少、瓶颈在哪；
2. 针对瓶颈该用什么题型 / 数据结构，为什么；
3. 把优化后的思路拆成 3–6 步，用表格列出：这一步要做什么 → 对应的 Python 写法 → 为什么；
4. 给一份代码骨架，关键的 2–3 行留成 \`# TODO: ...\` 让我自己填。`;
const P_REVIEW = `请批改我的代码（以【最近一次运行】的真实结果为准）：
- **结论**：一句话，对 / 部分对 / 错；
- **错在哪**：指出具体行号和原因；拿一个失败用例（或你构造的最小反例）手推，说明代码在哪一步和预期分叉；
- **怎么改**：给最小改动，只写需要改的那几行，不要整段重写；
- **你可能没吃透的点**：从错误推断我哪个概念不清楚，用 2–3 句讲明白；
- **复杂度**：时间 / 空间，能不能通过约束；
- **面试加分**：边界、命名、表达上的 1–2 条建议。
如果已经全部通过：重点讲还能不能更优、代码风格，以及面试官最可能追问的 2 个问题。`;
const P_COUNTER = `请帮我找出我的代码的反例：
1. 用 compare_with_reference 工具，构造几批小规模输入（含边界：空、单元素、重复、负数、极端值等，必须符合题目约束），对比我的代码和参考解；
2. 找到不一致的输入后，挑最小的一个，手推我的代码在哪一步出错；
3. 提示怎么修（不要给完整代码）。
如果试了几批都一致，就告诉我这些输入上都正确，再说说还可能有什么风险（比如复杂度、递归深度）。`;
const P_EXPLAIN_MINE = `请逐段讲解我现在写的代码：每段在做什么、为什么这样写、有没有更地道的 Python 写法、有没有隐藏的 bug。不要改变我的思路，只在必要时给出改写的那几行。`;
const P_EXPLAIN_REF = `我想看懂参考解是怎么写出来的。请逐段讲解参考解（这次可以给出完整代码）：每段先贴代码，再讲“为什么这么写”——每个变量的含义、每个判断的作用、如果写错会怎样。`;
const P_SOLUTION = `请讲解这道题的解法（这次可以给出完整代码）：
1. 先讲怎么从题目推到这个解法：识别信号 → 暴力 → 瓶颈 → 优化；
2. 把参考代码分成几段，每段先贴代码，再讲“为什么这么写”；
3. 用示例 1 走一遍关键过程；
4. 总结：核心一句话 + 2 个易错点 + 1–2 个常见变形分别要怎么改。`;
const P_FOLLOW = `请扮演面试官，针对这道题提 3 个最可能的追问（复杂度、优化、变形、边界等）。每个追问用 <details><summary>追问 N：问题</summary>参考回答</details> 的格式，让我先自己想再展开看答案。参考回答要简洁，能直接在面试里说出口。`;
const VARIANT_KINDS = [
  ["same", "换个场景", "换一个生活化的场景和说法，但解法和原题相同（检验能否认出题型）"],
  ["twist", "加一个条件", "在原题基础上加一个条件，让原来的解法需要调整"],
  ["reverse", "换个问法", "换一个求解目标（例如求个数变求最值、求存在变求所有方案），解法随之变化"],
  ["harder", "升一级难度", "难度升一级，考察同一题型的进阶用法"],
];

function viewWorkspace({ id }) {
  const p = S.byId[id];
  if (!p) return h("div", { class: "page" }, h("h1", null, "没找到这道题"), h("p", { class: "muted" }, "它可能已经被删除了。"), h("a", { class: "btn", href: "#problems" }, "回到题库"));
  const W = S.ws = { pid: id, p, cm: null, last: null, used: { hint: false, sol: false }, aiHint: 0, redo: S.redo === id };
  S.redo = null;
  onLeave(() => { if (S.ws === W) S.ws = null; if (W.chat && W.chat.ctl) W.chat.ctl.abort(); if (W.player) W.player.pause(); if (W.vizCtl) W.vizCtl.abort(); S.liveChats = []; });

  // ----- 头部 -----
  const pill = h("span");
  const head = h("div", { class: "ws-head" },
    h("a", { class: "btn ghost sm", href: W.redo ? "#review" : "#problems" }, icon("back"), W.redo ? "复习" : "题库"),
    h("h1", null, p.title),
    p.lc ? h("span", { class: "faint mono small" }, "#" + p.lc) : "",
    h("span", { class: "lv " + p.level }, LEVEL[p.level] || ""),
    PMAP[p.pattern] ? h("a", { class: "tag", href: "#t-" + p.pattern, title: "看这个题型的教程" }, pname(p)) : h("span", { class: "tag" }, "综合"),
    pill,
    W.redo ? h("span", { class: "pill due" }, "重写模式") : "",
    p.slug ? h("a", { class: "small", href: `https://leetcode.cn/problems/${p.slug}/`, target: "_blank", rel: "noopener" }, "力扣原题 ↗") : "");
  const refreshPill = () => { pill.textContent = ""; pill.append(statusPill(id)); };
  refreshPill();

  // ----- 右侧：编辑器 -----
  const right = h("div", { class: "ws-pane right", style: "position:relative" });
  const edWrap = h("div", { class: "ed-wrap" });
  const results = h("div", { class: "results" }, h("div", { class: "empty-results" }, "点「运行样例」先跑示例，「提交」跑全部用例。代码在你的浏览器里真实运行。"));
  const runBtn = h("button", { class: "btn sm", type: "button", title: "⌘/Ctrl + Enter" }, icon("run"), "运行样例");
  const subBtn = h("button", { class: "btn primary sm", type: "button", title: "⌘/Ctrl + Shift + Enter" }, icon("check"), "提交");
  const reviewBtn = h("button", { class: "btn sm", type: "button" }, "AI 批改");
  const resetBtn = h("button", { class: "btn ghost sm", type: "button" }, "清空重写");
  right.append(h("div", { class: "ed-bar" }, runBtn, subBtn, h("span", { class: "sp" }), reviewBtn, resetBtn), edWrap, results);

  const draftKey = "tiyan:draft:" + id;
  const d0 = prog(id);
  const initial = W.redo ? p.starter : (LS.get(draftKey, null) || (d0 && d0.lastCode) || p.starter);
  const cm = W.cm = CodeMirror(edWrap, {
    value: initial, mode: "python", theme: "tiyan", lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false,
    matchBrackets: true, autoCloseBrackets: true, lineWrapping: false, styleActiveLine: true,
    extraKeys: {
      Tab: c => { if (c.somethingSelected()) c.indentSelection("add"); else c.replaceSelection("    ", "end"); },
      "Shift-Tab": "indentLess",
      "Cmd-Enter": () => run(false), "Ctrl-Enter": () => run(false),
      "Shift-Cmd-Enter": () => run(true), "Shift-Ctrl-Enter": () => run(true),
      "Cmd-/": "toggleComment", "Ctrl-/": "toggleComment",
    },
  });
  let draftTimer = null, errMark = null;
  cm.on("change", () => {
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => LS.set(draftKey, cm.getValue()), 500);
    if (errMark != null) { cm.removeLineClass(errMark, "background", "cm-err-line"); errMark = null; }
  });
  requestAnimationFrame(() => { cm.refresh(); if (W.redo) { cm.focus(); cm.setCursor({ line: 1, ch: 8 }); } });
  if (W.redo) cm.setCursor({ line: 1, ch: 8 });
  const markErr = text => {
    const m = /第 (\d+) 行/.exec(text || "");
    if (!m) return;
    const ln = Number(m[1]) - 1;
    if (ln >= 0 && ln < cm.lineCount()) { errMark = cm.addLineClass(ln, "background", "cm-err-line"); }
  };

  let armed = false;
  resetBtn.addEventListener("click", () => {
    if (!armed) { armed = true; resetBtn.textContent = "确定清空？"; resetBtn.classList.add("red"); setTimeout(() => { armed = false; resetBtn.textContent = "清空重写"; resetBtn.classList.remove("red"); }, 3000); return; }
    armed = false; resetBtn.textContent = "清空重写"; resetBtn.classList.remove("red");
    cm.setValue(p.starter); cm.focus(); cm.setCursor({ line: 1, ch: 8 });
  });

  // ----- 运行 / 判题 -----
  const hasCode = () => cm.getValue().replace(/\s+/g, "") !== p.starter.replace(/\s+/g, "") && /return|print|yield|=/.test(cm.getValue().split("\n").slice(2).join("\n"));
  async function run(all) {
    const code = cm.getValue();
    LS.set(draftKey, code);
    const n = Math.max(2, Math.min((p.examples || []).length || 2, p.tests.length));
    const tests = all ? p.tests : p.tests.slice(0, n);
    runBtn.disabled = subBtn.disabled = true;
    results.textContent = "";
    results.append(h("div", { class: "results-h" }, h("span", { class: "thinking" }, S.py === "loading" ? "Python 运行环境还在加载（第一次大约 10–20 秒）……" : `正在运行 ${tests.length} 组用例……`)));
    let r = null, err = null, aiJudged = false;
    try {
      if (S.py === "failed") {
        if (!AI.ok()) throw { message: "Python 运行环境不可用（" + Py.error + "），AI 也没有连接，暂时无法判题。" };
        r = await aiJudge(p, code, tests); aiJudged = true;
      } else {
        r = await Py.json("run_tests", [code, specOf(p, tests)], all ? 12000 : 8000);
      }
    } catch (e) { err = e && e.code ? aiErr(e) : (e && e.message) || String(e); }
    runBtn.disabled = subBtn.disabled = false;
    W.last = { all, result: r, error: err, code, aiJudged };
    showResults(W.last);
    if (r && !r.compile_error && all && !aiJudged) await recordSubmit(r, code);
    else if (r && all && aiJudged && r.ok) await recordSubmit(r, code);
    return W.last;
  }
  async function ensureRun() {
    if (W.last && W.last.code === cm.getValue() && W.last.all) return;
    if (!hasCode()) return;
    await run(true);
  }
  runBtn.addEventListener("click", () => run(false));
  subBtn.addEventListener("click", () => run(true));
  reviewBtn.addEventListener("click", async () => {
    switchTab("ai");
    if (!AI.ok()) { toast(aiErr({ code: S.ai === "denied" ? "not_granted" : "unavailable" })); return; }
    if (!hasCode()) { toast("先写点代码再让老师批改；没思路可以点“思路→代码”。"); return; }
    await ensureRun();
    W.chat.send(P_REVIEW, { label: "批改代码" });
  });

  function showResults(last) {
    results.textContent = "";
    $$(".stamp", right).forEach(x => x.remove());
    if (last.error) { results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, "没有跑完")), h("div", { class: "stdout", style: "color:var(--red)" }, last.error)); return; }
    const r = last.result;
    if (r.compile_error) {
      markErr(r.compile_error);
      results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, "代码无法运行"), askBtn(`我的代码报错了：${r.compile_error}。这是什么意思？我该怎么改？`)), h("div", { class: "stdout", style: "color:var(--red)" }, r.compile_error));
      return;
    }
    const slow = r.cases.filter(c => c.ms > 1000).length;
    const total = r.cases.reduce((s, c) => s + (c.ms || 0), 0);
    results.append(h("div", { class: "results-h" },
      h("b", { class: r.ok ? "ok" : "bad" }, r.ok ? (last.all ? "全部通过" : "样例通过") : `通过 ${r.passed} / ${r.total}`),
      h("span", { class: "small faint num" }, `${last.all ? "全部用例" : "样例"} · ${Math.round(total)} ms`),
      last.aiJudged ? h("span", { class: "pill trying" }, "AI 推演，非真实运行") : "",
      slow ? h("span", { class: "pill trying" }, `${slow} 个用例超过 1 秒，复杂度可能偏高`) : "",
      r.ok && !last.all ? h("button", { class: "btn primary sm", type: "button", onclick: () => run(true) }, "提交全部用例") : ""));
    if (r.ok && last.all) {
      const st = h("div", { class: "stamp go", "aria-hidden": "true" }, "过");
      right.append(st);
      results.append(recordPanel());
    }
    let opened = false;
    for (const c of r.cases) {
      const fail = !c.pass;
      const det = h("details", { class: "case " + (fail ? "fail" : "pass") });
      if (fail && !opened) { det.open = true; opened = true; if (c.error) markErr(c.error); }
      det.append(h("summary", null, h("span", { class: "dot" }), `用例 ${c.i + 1}`, h("span", { class: "faint num" }, `${c.ms} ms`), fail ? h("span", { style: "color:var(--red)" }, c.error ? "报错" : "答案不对") : ""),
        h("div", { class: "case-body" },
          h("div", null, h("span", null, "输入"), h("span", null, c.args)),
          h("div", null, h("span", null, "期望"), h("span", null, c.expected)),
          c.error ? h("div", null, h("span", null, "报错"), h("span", { class: "err" }, c.error)) : h("div", null, h("span", null, "实际"), h("span", { style: fail ? "color:var(--red)" : "" }, c.got)),
          fail ? h("div", null, h("span"), h("span", null, askBtn(`这个用例我没过：输入 ${c.args}，期望 ${c.expected}，${c.error ? "报错 " + c.error : "我的输出 " + c.got}。请对着我的代码手推一遍，告诉我在哪一步出了问题（先别直接给完整答案）。`))) : ""));
      results.append(det);
    }
    if (r.stdout) results.append(h("div", { class: "stdout" }, h("div", { class: "faint small", style: "font-family:var(--sans)" }, "print 输出"), r.stdout));
  }
  function askBtn(q) {
    const b = h("button", { class: "btn sm", type: "button", disabled: !AI.ok() }, "问老师");
    b.addEventListener("click", () => { switchTab("ai"); W.chat.send(q, { label: "问这个错误", display: "" }); });
    return b;
  }

  // ----- 通过后记录：三行笔记 + 自评，排进复习 -----
  function recordPanel() {
    const d = prog(id) || {};
    const notes = d.notes || {};
    let rating = W.used.sol ? "sol" : W.used.hint ? "hint" : "solo";
    const seg = h("div", { class: "seg" }, [["solo", "独立做出"], ["hint", "看了提示"], ["sol", "看了题解"]].map(([v, t]) => {
      const b = h("button", { type: "button", class: v === rating ? "on" : "" }, t);
      b.addEventListener("click", () => { rating = v; $$("button", seg).forEach(x => x.classList.remove("on")); b.classList.add("on"); });
      return b;
    }));
    const f1 = h("input", { id: "n-signal", value: notes.signal || "", placeholder: "题眼：从哪句话看出用这个方法？" });
    const f2 = h("input", { id: "n-core", value: notes.core || p.key || "", placeholder: "核心一句话 / 不变量" });
    const f3 = h("input", { id: "n-mistake", value: notes.mistake || "", placeholder: "我错在哪 / 下次注意什么" });
    const save = h("button", { class: "btn primary sm", type: "button" }, "保存并安排复习");
    const box = h("div", { class: "record" },
      h("div", { class: "spread" }, h("b", null, "写三行笔记，复习时只看这三行"), seg),
      h("label", null, "识别信号", f1), h("label", null, "核心思路", f2), h("label", null, "易错点", f3),
      h("div", { class: "row" }, save, h("span", { class: "small muted" }, "独立做出 → 进入下一阶段；看了提示 → 原地不动；看了题解 → 明天重来")));
    save.addEventListener("click", async () => {
      const doc = Object.assign({}, prog(id) || { attempts: 1, passed: true });
      doc.notes = { signal: f1.value.trim(), core: f2.value.trim(), mistake: f3.value.trim() };
      schedule(doc, rating);
      W.used = { hint: false, sol: false };
      await saveProg(id, doc);
      box.replaceWith(h("div", { class: "record" }, h("b", null, `已安排 ${relDay(doc.due)}（${fmtDate(doc.due)}）从空白重写。`), h("span", { class: "small muted" }, (doc.stage || 0) >= 5 ? "这道题已经掌握了。" : `复习阶段 ${doc.stage}/5`)));
      refreshPill();
      renderNotes();
    });
    return box;
  }
  async function recordSubmit(r, code) {
    const prev = prog(id);
    const doc = Object.assign({ attempts: 0, stage: 0 }, prev || {});
    doc.attempts = (doc.attempts || 0) + 1;
    doc.lastAt = Date.now();
    doc.lastCode = code;
    doc.lastPass = !!r.ok;
    if (r.ok && !doc.passed) { doc.passed = true; doc.firstPassAt = Date.now(); }
    if (r.ok && !prev?.due) { doc.due = startOfDay() + DAY; doc.stage = doc.stage || 0; }
    await saveProg(id, doc);
    refreshPill();
    renderNotes();
  }

  // ----- 左侧：标签页 -----
  const left = h("div", { class: "ws-pane left" });
  const tabsEl = h("div", { class: "tabs", role: "tablist" });
  const bodies = {};
  const TABS = [["desc", "题目"], ["ai", "AI 老师"], ["viz", "动画讲解"], ["notes", "笔记"]];
  for (const [k, t] of TABS) {
    const b = h("button", { class: "tab", type: "button", role: "tab", "data-k": k }, t);
    b.addEventListener("click", () => switchTab(k));
    tabsEl.append(b);
    bodies[k] = h("div", { class: "tab-body" + (k === "ai" || k === "viz" ? " flush" : ""), hidden: true });
  }
  left.append(tabsEl, ...Object.values(bodies));
  function switchTab(k) {
    W.tab = k;
    $$(".tab", tabsEl).forEach(b => b.classList.toggle("on", b.dataset.k === k));
    for (const [kk, el] of Object.entries(bodies)) el.hidden = kk !== k;
    if (k === "viz" && !W.vizBuilt) buildViz();
  }

  // 题目
  const desc = bodies.desc;
  const descMd = h("div", { class: "md" });
  renderMd(descMd, p.desc);
  const ladder = h("div", { class: "hint-ladder" });
  let shown = 0;
  const drawLadder = () => {
    ladder.textContent = "";
    (p.hints || []).forEach((t, i) => {
      if (i < shown) ladder.append(h("div", { class: "hint fade-in" }, h("b", null, `第 ${i + 1} 级`), t));
      else if (i === shown) {
        const l = h("div", { class: "hint locked", role: "button", tabindex: "0" }, h("span", null, `看第 ${i + 1} 级提示`), h("span", { class: "small" }, ["题型方向", "核心思路", "关键步骤"][i] || ""));
        const open = () => { shown++; W.used.hint = true; drawLadder(); };
        l.addEventListener("click", open);
        l.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
        ladder.append(l);
      }
    });
  };
  drawLadder();
  const solBox = h("div", { class: "stack" });
  let solArmed = false;
  const solBtn = h("button", { class: "btn sm", type: "button" }, "看参考解");
  solBtn.addEventListener("click", () => {
    if (!solArmed) { solArmed = true; solBtn.textContent = "看了会记为“看了题解”，确定？"; return; }
    W.used.sol = true;
    solBtn.remove();
    const pre = h("pre", { class: "example", style: "white-space:pre" });
    highlightInto(pre, p.solution.trim());
    solBox.append(pre, h("p", { class: "small muted" }, p.complexity),
      p.pitfalls && p.pitfalls.length ? h("ul", { class: "signals small" }, p.pitfalls.map(x => h("li", null, h("span", null, x)))) : "",
      h("div", { class: "row" }, h("button", { class: "btn sm", type: "button", disabled: !AI.ok(), onclick: () => { switchTab("ai"); W.chat.send(P_SOLUTION, { label: "讲参考解" }); } }, "让老师讲为什么这么写"),
        h("button", { class: "btn sm", type: "button", onclick: () => { switchTab("viz"); } }, icon("play"), "看动画")));
  });
  solBox.append(solBtn);
  desc.append(h("div", { class: "desc" },
    W.redo ? h("div", { class: "callout" }, h("b", null, "重写模式："), "编辑器已清空。先别看笔记和提示，试着在 15 分钟内从空白写出来。",
      h("button", { class: "btn ghost sm", type: "button", onclick: () => { const dr = LS.get(draftKey, null) || (prog(id) && prog(id).lastCode); if (dr) cm.setValue(dr); } }, "恢复上次的代码")) : "",
    p.change ? h("div", { class: "callout blue" }, h("b", null, "和原题的区别："), p.change, p.from && S.byId[p.from] ? h("span", null, "　原题：", h("a", { href: "#p-" + p.from }, S.byId[p.from].title)) : "") : "",
    p.unverified ? h("div", { class: "callout" }, "这道题的答案没有经过参考解校验（当时 Python 运行环境不可用），判题结果仅供参考。") : "",
    descMd,
    (p.examples || []).map((e, i) => h("div", { class: "example" }, h("b", null, `示例 ${i + 1}\n`), `输入：${e.input}\n输出：${e.output}`, e.note ? h("span", { class: "faint" }, `\n说明：${e.note}`) : "")),
    p.constraints && p.constraints.length ? h("div", null, h("div", { class: "eyebrow" }, "约束"), h("ul", { class: "constraints" }, p.constraints.map(c => h("li", null, c)))) : "",
    h("div", { class: "sep" }),
    h("div", { class: "stack" }, h("div", { class: "spread" }, h("h3", null, "提示阶梯"), h("span", { class: "small faint" }, "一级一级看，看了会记录")), ladder),
    h("div", { class: "stack" }, h("h3", null, "参考解"), solBox)));

  // AI 老师
  const ctx = () => [TEACHER, problemBlock(p), "【学习者当前代码】（带行号）\n```python\n" + numbered(cm.getValue()) + "\n```", runBlock(W.last),
    shown ? "【学习者已看过的提示】\n" + p.hints.slice(0, shown).join("\n") : ""].filter(Boolean).join("\n\n");
  const chat = W.chat = new Chat({
    key: "ws:" + id, context: ctx,
    placeholder: "哪里不懂就问：比如“为什么这里要先查再存？”（Enter 发送）",
    intro: "我能看到题目、你的代码和真实运行结果。没思路就点“读懂题目”或“给我提示”；写了代码就点“批改代码”或“找反例”。",
    actions: [
      { label: "读懂题目", run: c => c.send(P_UNDERSTAND, { label: "读懂题目" }) },
      { label: "给我提示", run: c => { const n = Math.min(4, W.aiHint + 1); W.aiHint = n; W.used.hint = true; c.send(P_HINT(n), { label: `提示 ${n}/4` }); } },
      { label: "思路→代码", run: c => c.setMode({ hint: "写下你的思路（大白话就行），老师帮你变成代码；留空发送 = 让老师从头带你推导", allowEmpty: true, placeholder: "比如：用字典记住每个数的下标，遍历时找 target - x 在不在……", send: t => { W.used.hint = true; c.send(t ? P_IDEA(t) : P_IDEA0, { label: "思路→代码", display: t }); } }) },
      { label: "批改代码", run: async c => { if (!hasCode()) { toast("先写点代码再批改"); return; } await ensureRun(); c.send(P_REVIEW, { label: "批改代码" }); } },
      { label: "找反例", title: "AI 会真实运行你的代码和参考解，找出让你出错的输入", enabled: () => S.py === "ready" && AI.tools, run: c => { if (!hasCode()) { toast("先写点代码再找反例"); return; } c.send(P_COUNTER, { label: "找反例", tools: pyTools(p), tier: "default" }); } },
      { label: "逐行讲解", run: c => { const mine = hasCode(); if (!mine) W.used.sol = true; c.send(mine ? P_EXPLAIN_MINE : P_EXPLAIN_REF, { label: mine ? "逐行讲我的代码" : "逐行讲参考解" }); } },
      { label: "讲参考解", run: c => { W.used.sol = true; c.send(P_SOLUTION, { label: "讲参考解" }); } },
      { label: "面试追问", run: c => c.send(P_FOLLOW, { label: "面试追问" }) },
      { label: "出个变体", run: c => variantMode(c, p) },
    ],
  });
  S.liveChats = [chat];
  bodies.ai.append(chat.el);

  // 动画
  function buildViz() {
    W.vizBuilt = true;
    const root = bodies.viz;
    root.textContent = "";
    const inner = h("div", { class: "viz", style: "padding:16px;overflow:auto;flex:1" });
    root.append(inner);
    const status = h("div", { class: "small muted" });
    let src = "ref";
    const seg = h("div", { class: "seg" }, [["ref", "演示参考解"], ["mine", "演示我的代码"]].map(([v, t]) => {
      const b = h("button", { type: "button", class: v === src ? "on" : "" }, t);
      b.addEventListener("click", () => { src = v; $$("button", seg).forEach(x => x.classList.remove("on")); b.classList.add("on"); });
      return b;
    }));
    const gen = h("button", { class: "btn primary sm", type: "button" }, S.viz[id] ? "重新生成" : "生成动画讲解");
    const stage = h("div", { class: "stack" });
    inner.append(
      h("p", { class: "small muted" }, "AI 挑一个小输入，把代码的执行过程拆成一帧一帧的画面，每帧配一句旁白，可以朗读。相当于一段能暂停、能单步、能随时提问的讲解视频。"),
      h("div", { class: "row" }, seg, gen, status), stage);
    const show = v => {
      stage.textContent = "";
      if (W.player) W.player.pause();
      W.player = new Player(stage, v.viz, v.code, frame => {
        switchTab("ai");
        W.chat.send(`我在看动画讲解的第 ${frame.n} 帧（代码第 ${frame.line || "?"} 行）：“${frame.say}”。当时的数据：${clip(JSON.stringify(frame.data), 1500)}。\n这一步我没看懂：为什么要这样做？如果不这样做会怎样？`, { label: "问动画这一步", display: `第 ${frame.n} 帧：${clip(frame.say, 60)}` });
      });
    };
    if (S.viz[id]) show(S.viz[id]);
    else stage.append(h("div", { class: "callout blue" }, "还没有这道题的动画。点「生成动画讲解」，大约需要 30–90 秒；生成后会保存，下次直接播放。"));
    gen.addEventListener("click", async () => {
      if (!AI.ok()) { status.textContent = aiErr({ code: S.ai === "denied" ? "not_granted" : "unavailable" }); return; }
      const code = src === "mine" ? cm.getValue() : p.solution;
      if (src === "mine" && !hasCode()) { status.textContent = "编辑器里还没有代码，先写一些，或者演示参考解。"; return; }
      if (src === "ref") W.used.sol = true;
      gen.disabled = true;
      status.textContent = "AI 正在拆解执行过程……";
      const ctl = W.vizCtl = new AbortController();
      try {
        const useTools = AI.tools && S.py === "ready";
        const raw = await AI.ask(vizPrompt(p, code, useTools), {
          json: true, signal: ctl.signal, tier: "complex",
          tools: useTools ? pyTools(null)({ progress: t => { status.textContent = t; } }) : undefined,
        });
        const viz = normalizeViz(raw);
        const rec = { viz, code: code.trim(), src, at: Date.now() };
        if (JSON.stringify(rec).length < 200000) await Store.put("v:" + id, rec);
        S.viz[id] = rec;
        status.textContent = "";
        gen.textContent = "重新生成";
        show(rec);
      } catch (e) {
        status.textContent = e && e.code ? aiErr(e) : "生成失败：" + ((e && e.message) || e);
      } finally { gen.disabled = false; W.vizCtl = null; }
    });
  }

  // 笔记
  function renderNotes() {
    const b = bodies.notes;
    b.textContent = "";
    const d = prog(id);
    const n = (d && d.notes) || {};
    const f1 = h("input", { id: "nn-signal", value: n.signal || "", placeholder: "题眼：从哪句话看出用这个方法？" });
    const f2 = h("input", { id: "nn-core", value: n.core || "", placeholder: "核心一句话 / 不变量" });
    const f3 = h("input", { id: "nn-mistake", value: n.mistake || "", placeholder: "我错在哪 / 下次注意什么" });
    const save = h("button", { class: "btn sm", type: "button" }, "保存笔记");
    save.addEventListener("click", async () => {
      const doc = Object.assign({ attempts: 0 }, prog(id) || {});
      doc.notes = { signal: f1.value.trim(), core: f2.value.trim(), mistake: f3.value.trim() };
      await saveProg(id, doc);
      toast("笔记已保存");
    });
    const hist = ((d && d.history) || []).slice().reverse();
    b.append(h("div", { class: "desc" },
      W.redo && !(W.last && W.last.result && W.last.result.ok) ? h("div", { class: "callout" }, "重写模式：建议写完再看笔记。") : "",
      h("div", { class: "record", style: "background:var(--surface-2);border-radius:8px;border:0" },
        h("b", null, "三行笔记"),
        h("label", null, "识别信号", f1), h("label", null, "核心思路", f2), h("label", null, "易错点", f3),
        h("div", { class: "row" }, save)),
      h("div", { class: "stack" }, h("h3", null, "练习记录"),
        d ? h("div", { class: "row small" }, h("span", null, `提交 ${d.attempts || 0} 次`), d.passed ? h("span", null, "· 首次通过 " + fmtDate(d.firstPassAt || d.lastAt)) : h("span", { class: "faint" }, "· 还没通过"),
          d.due ? h("span", null, `· 下次复习 ${relDay(d.due)}`) : "", stageDots(d.stage)) : h("p", { class: "small muted" }, "还没有提交过。"),
        hist.length ? h("ul", { class: "constraints", style: "font-family:var(--sans)" }, hist.map(x => h("li", null, `${fmtDate(x.at)}　${{ solo: "独立做出", hint: "看了提示", sol: "看了题解" }[x.rating] || x.rating}`))) : ""),
      d && d.lastCode ? h("details", { class: "case" }, h("summary", null, "上次提交的代码"), (() => { const pre = h("pre", { class: "example", style: "white-space:pre;margin:0 0 10px" }); highlightInto(pre, d.lastCode); return pre; })()) : ""));
  }
  renderNotes();

  W.refresh = () => { refreshPill(); if (W.tab !== "notes") renderNotes(); };
  switchTab(S.openTab || "desc");
  S.openTab = null;

  return h("div", { class: "ws" }, head, h("div", { class: "ws-grid" }, left, right));
}

function variantMode(chat, p) {
  chat.setMode({
    hint: "出哪种变体？",
    extra: h("span", { class: "row" }, VARIANT_KINDS.map(([k, t, d]) => {
      const b = h("button", { class: "chip", type: "button", title: d }, t);
      b.addEventListener("click", () => {
        chat.setMode(null);
        runGenerate(chat, `你是算法出题老师。基于下面这道原题出一道变体题，要求：${d}。目的是检验学习者是否真正理解了解法，而不是背答案；题面不要照搬原题。\n\n${problemBlock(p)}\n\n${PROBLEM_SCHEMA}\n另外加一个字段 "change"：说明和原题哪里不同、这个变化为什么会影响解法（2–3 句）。`, "出变体：" + t, { from: p.id });
      });
      return b;
    })),
    send: () => {},
  });
}

// 判题兜底：Python 运行环境不可用时，让 AI 推演
async function aiJudge(p, code, tests) {
  const out = await AI.ask(`你是判题机。请在脑中逐个执行学习者的代码，判断每组用例的输出。只返回 JSON：{"cases": [{"i": 0, "got": "实际输出（JSON 字符串）", "pass": true, "error": null}]}，error 写运行时会抛的异常（没有就是 null）。\n\n函数签名：\n${p.starter}\n比较方式：${p.compare}\n\n学习者代码：\n\`\`\`python\n${code}\n\`\`\`\n\n用例：\n${tests.map((t, i) => `${i}. 输入 ${JSON.stringify(t.args)}，期望 ${JSON.stringify(t.expected)}`).join("\n")}`, { json: true, tier: "default" });
  const cases = tests.map((t, i) => {
    const c = (out && Array.isArray(out.cases) ? out.cases.find(x => Number(x.i) === i) : null) || {};
    return { i, args: clip(JSON.stringify(t.args), 300), expected: clip(JSON.stringify(t.expected), 300), got: String(c.got ?? "?"), pass: !!c.pass, error: c.error || null, ms: 0 };
  });
  const passed = cases.filter(c => c.pass).length;
  return { ok: passed === cases.length, compile_error: null, cases, passed, total: cases.length, stdout: "" };
}

// ---------- 动画讲解 ----------
function vizPrompt(p, code, tools) {
  return `为这道题制作一段“算法动画讲解”的分镜数据，帮学习者看懂代码每一步在做什么、为什么这么做。

${problemBlock(p, false)}

要演示的代码（行号从 1 开始）：
\`\`\`
${numbered(code)}
\`\`\`

要求：
1. 自己挑一个能体现关键过程的小输入（数组长度 ≤ 8，网格 ≤ 4×4，树 ≤ 7 个节点，字符串 ≤ 8 个字符）；
2. ${tools ? "先用 run_python 工具运行一个在关键位置 print 中间状态的版本（可以直接改写上面的代码加 print），确保每一帧的数据和真实执行完全一致；" : "仔细模拟执行，确保每一帧的数据和真实执行一致；"}
3. 生成 8–20 帧，每帧对应一个有意义的步骤：跳过平淡的重复步骤，但关键分支（比如指针移动、入栈出栈、更新答案）都要有；
4. say 是旁白，会被语音朗读：1–2 句口语，讲清“现在在做什么、为什么这么做”，不要堆代码符号；
5. line 是这一帧正在执行的代码行号；
6. 用合适的画面：数组用 arrays（指针放 pointers，当前比较 / 处理的元素放 highlight，窗口放 window [左, 右]）；DP 表或网格用 table；栈 / 队列 / 堆用 stack；二叉树用 tree（层序数组）；其他关键变量放 vars。

只返回一个 JSON 对象：
{"title": "这段动画讲什么", "input": "nums = [2,7,11,15], target = 9", "frames": [{"line": 3, "say": "旁白", "arrays": [{"name": "nums", "values": [2,7,11,15], "pointers": {"i": 0}, "highlight": [0], "window": null}], "table": null, "stack": null, "tree": null, "vars": {"target": 9}}], "summary": "一句话总结"}
table 格式：{"name": "dp", "rows": [[0,1],[1,1]], "rowLabels": ["", "a"], "colLabels": ["", "b"], "highlight": [[0,1]], "current": [1,1]}
stack 格式：{"name": "st", "items": [1,2], "kind": "stack"}（kind 是 stack / queue / heap，可以给一个数组放多个）
tree 格式：{"values": [3,9,20,null,null,15,7], "highlight": [0]}（highlight 是层序数组的下标）`;
}
function normalizeViz(o) {
  if (!o || !Array.isArray(o.frames) || !o.frames.length) throw new Error("AI 没有返回动画分镜");
  const asArr = x => Array.isArray(x) ? x : (x && typeof x === "object" ? [x] : []);
  const ints = x => Array.isArray(x) ? x.map(Number).filter(Number.isFinite) : [];
  const frames = o.frames.slice(0, 40).map(f => ({
    line: Number(f.line) || 0,
    say: String(f.say || ""),
    arrays: asArr(f.arrays).filter(a => a && Array.isArray(a.values)).slice(0, 4).map(a => ({
      name: String(a.name || ""), values: a.values.slice(0, 40),
      pointers: a.pointers && typeof a.pointers === "object" ? Object.fromEntries(Object.entries(a.pointers).filter(([, v]) => Number.isFinite(Number(v)) && v !== null).map(([k, v]) => [k, Number(v)])) : {},
      highlight: ints(a.highlight), window: Array.isArray(a.window) && a.window.length === 2 ? ints(a.window) : null, dim: ints(a.dim),
    })),
    table: f.table && Array.isArray(f.table.rows) ? {
      name: String(f.table.name || ""), rows: f.table.rows.slice(0, 20).map(r => Array.isArray(r) ? r.slice(0, 20) : []),
      rowLabels: Array.isArray(f.table.rowLabels) ? f.table.rowLabels : null, colLabels: Array.isArray(f.table.colLabels) ? f.table.colLabels : null,
      highlight: Array.isArray(f.table.highlight) ? f.table.highlight.filter(Array.isArray).map(ints) : [], current: Array.isArray(f.table.current) ? ints(f.table.current) : null,
    } : null,
    stacks: asArr(f.stack).filter(s => s && Array.isArray(s.items)).slice(0, 3).map(s => ({ name: String(s.name || ""), items: s.items.slice(0, 30), kind: ["stack", "queue", "heap"].includes(s.kind) ? s.kind : "stack" })),
    tree: f.tree && Array.isArray(f.tree.values) ? { values: f.tree.values.slice(0, 31), highlight: ints(f.tree.highlight) } : null,
    vars: f.vars && typeof f.vars === "object" && !Array.isArray(f.vars) ? f.vars : {},
  }));
  return { title: String(o.title || ""), input: String(o.input || ""), summary: String(o.summary || ""), frames };
}
function fmtVal(v) { return typeof v === "string" ? v : JSON.stringify(v); }

class Player {
  constructor(root, viz, code, onAsk) {
    this.viz = viz; this.frames = viz.frames; this.i = 0; this.playing = false; this.timer = null;
    this.speed = 1; this.narrate = LS.get("tiyan:narrate", true) && TTS.ok;
    this.arrEls = {};
    this.codeLines = code.replace(/\s+$/, "").split("\n").map((l, k) => {
      const c = h("span");
      highlightInto(c, l || " ");
      return h("div", null, h("span", null, k + 1), c);
    });
    this.codeEl = h("div", { class: "viz-code" }, this.codeLines);
    this.dataEl = h("div", { class: "viz-data" });
    this.sayEl = h("div", { class: "vz-say", "aria-live": "polite" });
    this.slider = h("input", { type: "range", min: 0, max: this.frames.length - 1, value: 0, id: "viz-slider", "aria-label": "帧" });
    this.playBtn = h("button", { class: "btn primary sm", type: "button" }, icon("play"), "播放");
    const prev = h("button", { class: "btn sm", type: "button", title: "上一帧" }, icon("prev"));
    const next = h("button", { class: "btn sm", type: "button", title: "下一帧" }, icon("next"));
    const speed = h("select", { id: "viz-speed", class: "btn sm", "aria-label": "速度" }, [["0.75", "0.75×"], ["1", "1×"], ["1.5", "1.5×"]].map(([v, t]) => h("option", { value: v, selected: v === "1" }, t)));
    const nar = h("button", { class: "btn sm" + (this.narrate ? " primary" : ""), type: "button", hidden: !TTS.ok }, icon("speak"), "旁白");
    const ask = h("button", { class: "btn ghost sm", type: "button", disabled: !AI.ok() }, "这一步没看懂");
    this.playBtn.addEventListener("click", () => this.playing ? this.pause() : this.play());
    prev.addEventListener("click", () => { this.pause(); this.show(this.i - 1); });
    next.addEventListener("click", () => { this.pause(); this.show(this.i + 1); });
    this.slider.addEventListener("input", () => { this.pause(); this.show(Number(this.slider.value)); });
    speed.addEventListener("change", () => { this.speed = Number(speed.value); });
    nar.addEventListener("click", () => { this.narrate = !this.narrate; LS.set("tiyan:narrate", this.narrate); nar.classList.toggle("primary", this.narrate); if (!this.narrate) TTS.stop(); });
    ask.addEventListener("click", () => { this.pause(); const f = this.frames[this.i]; onAsk({ n: this.i + 1, line: f.line, say: f.say, data: { arrays: f.arrays, table: f.table, stacks: f.stacks, tree: f.tree, vars: f.vars } }); });
    this.counter = h("span", { class: "small faint num" });
    root.append(
      h("div", { class: "spread" }, h("div", null, h("b", null, viz.title || "动画讲解"), viz.input ? h("div", { class: "small muted mono" }, "输入：" + viz.input) : ""), this.counter),
      h("div", { class: "viz-stage" }, this.codeEl, this.dataEl),
      this.sayEl,
      h("div", { class: "vz-ctrl" }, prev, this.playBtn, next, this.slider, speed, nar, ask),
      viz.summary ? h("p", { class: "small muted" }, h("span", { class: "hl" }, "总结"), "　" + viz.summary) : "");
    this.show(0);
  }
  show(i) {
    i = Math.max(0, Math.min(this.frames.length - 1, i));
    this.i = i;
    const f = this.frames[i];
    this.slider.value = i;
    this.counter.textContent = `${i + 1} / ${this.frames.length}`;
    this.codeLines.forEach((el, k) => el.classList.toggle("cur", k + 1 === f.line));
    const cur = this.codeLines[f.line - 1];
    if (cur) { const top = cur.offsetTop - this.codeEl.clientHeight / 2; this.codeEl.scrollTop = Math.max(0, top); }
    this.sayEl.textContent = "";
    this.sayEl.append(h("b", null, f.line ? `第 ${f.line} 行` : `第 ${i + 1} 帧`), f.say);
    this.drawData(f);
  }
  drawData(f) {
    const seen = new Set();
    for (const a of f.arrays) {
      const key = a.name || "_";
      seen.add(key);
      let A = this.arrEls[key];
      if (!A) {
        A = this.arrEls[key] = { block: h("div", { class: "vz-block" }), cells: h("div", { class: "vz-cells" }), ptrs: h("div", { class: "vz-ptrs" }), ptrEls: {} };
        A.block.append(h("div", { class: "vz-name" }, a.name), h("div", { class: "vz-arr" }, A.cells, A.ptrs));
      }
      A.cells.textContent = "";
      const lo = a.window ? a.window[0] : -1, hi = a.window ? a.window[1] : -2;
      a.values.forEach((v, k) => A.cells.append(h("div", { class: "vz-cell" + (a.highlight.includes(k) ? " hl" : "") + (k >= lo && k <= hi ? " win" : "") + (a.dim.includes(k) ? " dim" : "") }, h("i", null, k), h("b", null, v === null ? "·" : clip(fmtVal(v), 5)))));
      A.ptrs.style.width = (a.values.length * 44) + "px";
      const byIdx = {};
      const live = new Set();
      for (const [label, idx] of Object.entries(a.pointers)) {
        live.add(label);
        let el = A.ptrEls[label];
        if (!el) { el = A.ptrEls[label] = h("div", { class: "vz-ptr" }, label); A.ptrs.append(el); }
        const row = byIdx[idx] = (byIdx[idx] || 0) + 1;
        el.style.transform = `translate(${idx * 44}px, ${(row - 1) * 22}px)`;
      }
      const rows = Math.max(1, ...Object.values(byIdx));
      A.ptrs.style.height = (rows * 22) + "px";
      for (const [label, el] of Object.entries(A.ptrEls)) if (!live.has(label)) { el.remove(); delete A.ptrEls[label]; }
    }
    for (const k of Object.keys(this.arrEls)) if (!seen.has(k)) { this.arrEls[k].block.remove(); delete this.arrEls[k]; }
    const extra = [];
    if (f.table) {
      const t = f.table;
      const isH = (r, c) => t.highlight.some(x => x[0] === r && x[1] === c);
      const isC = (r, c) => t.current && t.current[0] === r && t.current[1] === c;
      extra.push(h("div", { class: "vz-block" }, h("div", { class: "vz-name" }, t.name), h("div", { class: "scroll-x" }, h("table", { class: "vz-table" },
        t.colLabels ? h("tr", null, t.rowLabels ? h("th") : "", t.colLabels.map(c => h("th", null, fmtVal(c)))) : "",
        t.rows.map((row, r) => h("tr", null, t.rowLabels ? h("th", null, fmtVal(t.rowLabels[r] ?? "")) : "", row.map((v, c) => h("td", { class: isC(r, c) ? "cur" : isH(r, c) ? "hl" : "" }, v === null ? "" : clip(fmtVal(v), 6)))))))));
    }
    for (const s of f.stacks) extra.push(h("div", { class: "vz-block" }, h("div", { class: "vz-name" }, `${s.name} (${{ stack: "栈，右边是栈顶", queue: "队列，左边是队头", heap: "堆" }[s.kind]})`),
      h("div", { class: "vz-stack " + s.kind }, s.items.length ? s.items.map(v => h("span", null, clip(fmtVal(v), 12))) : h("em", null, "空"))));
    if (f.tree) extra.push(h("div", { class: "vz-block vz-tree" }, h("div", { class: "vz-name" }, "tree"), treeSvg(f.tree.values, f.tree.highlight)));
    const vars = Object.entries(f.vars);
    if (vars.length) extra.push(h("div", { class: "vz-block" }, h("div", { class: "vz-name" }, "变量"), h("div", { class: "vz-vars" }, vars.map(([k, v]) => h("span", null, k, " = ", h("b", null, clip(fmtVal(v), 40)))))));
    this.dataEl.textContent = "";
    for (const k of Object.keys(this.arrEls)) this.dataEl.append(this.arrEls[k].block);
    this.dataEl.append(...extra);
  }
  play() {
    if (this.i >= this.frames.length - 1) this.show(0);
    this.playing = true;
    this.playBtn.textContent = ""; this.playBtn.append(icon("pause"), "暂停");
    this.step();
  }
  step() {
    if (!this.playing) return;
    const f = this.frames[this.i];
    const advance = () => {
      if (!this.playing) return;
      if (this.i >= this.frames.length - 1) { this.pause(); return; }
      this.show(this.i + 1);
      this.step();
    };
    if (this.narrate && TTS.ok && f.say) {
      const base = TTS.rate;
      TTS.rate = Math.max(.6, Math.min(2, base * this.speed));
      TTS.speak(f.say, () => { if (this.playing) this.timer = setTimeout(advance, 380 / this.speed); });
      TTS.rate = base;
    } else this.timer = setTimeout(advance, Math.max(1500, f.say.length * 130) / this.speed);
  }
  pause() {
    this.playing = false;
    clearTimeout(this.timer);
    TTS.stop();
    this.playBtn.textContent = ""; this.playBtn.append(icon("play"), "播放");
  }
}
function treeSvg(values, hl) {
  if (!values.length || values[0] == null) return h("div", { class: "small faint" }, "空树");
  const root = { v: values[0], i: 0, d: 0 };
  const nodes = [root], q = [root];
  let k = 1;
  while (q.length && k < values.length) {
    const n = q.shift();
    for (const side of ["l", "r"]) {
      if (k >= values.length) break;
      const v = values[k];
      if (v != null) { const c = { v, i: k, d: n.d + 1 }; n[side] = c; nodes.push(c); q.push(c); }
      k++;
    }
  }
  let x = 0;
  const walk = n => { if (!n) return; walk(n.l); n.x = x++; walk(n.r); };
  walk(root);
  const W = x * 46 + 12, H = (Math.max(...nodes.map(n => n.d)) + 1) * 54 + 12;
  const px = n => 6 + n.x * 46 + 23, py = n => 6 + n.d * 54 + 22;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="二叉树">`;
  for (const n of nodes) for (const c of [n.l, n.r]) if (c) svg += `<line x1="${px(n)}" y1="${py(n)}" x2="${px(c)}" y2="${py(c)}"/>`;
  for (const n of nodes) svg += `<circle cx="${px(n)}" cy="${py(n)}" r="17" class="${hl.includes(n.i) ? "hl" : ""}"/><text x="${px(n)}" y="${py(n)}">${esc(clip(fmtVal(n.v), 4))}</text>`;
  return h("div", { html: svg + "</svg>" });
}
