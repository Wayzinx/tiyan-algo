// ---------- 手写实战：在浏览器里写代码、跑测试，AI 老师批改 ----------
const LABS = JSON.parse(document.getElementById("labs-data").textContent || "[]");
const LABSTAT = {
  all() { return LS.get("tiyan:lab:stat", {}); },
  get(id) { return this.all()[id] || null; },
  set(id, rec) { const a = this.all(); a[id] = Object.assign({}, a[id] || {}, rec, { at: Date.now() }); LS.set("tiyan:lab:stat", a); },
};
const COURSE_NAME = { llm: "大模型原理", agent: "Agent 原理", harness: "Harness 工程", dev: "AI 应用开发实战", arch: "Agent 系统架构" };

function viewLabList() {
  if (!LABS.length) return h("div", { class: "panel" }, h("h2", null, "实战题还在准备中"), h("p", { class: "muted" }, "稍后刷新再来。"));
  const groups = Object.keys(COURSE_NAME).map(c => [c, LABS.filter(l => l.course === c)]).filter(g => g[1].length);
  const passed = LABS.filter(l => (LABSTAT.get(l.id) || {}).passed).length;
  return h("div", { class: "stack", style: "gap:18px" },
    h("p", { class: "small muted" }, `共 ${LABS.length} 题，已通过 ${passed} 题。「写代码」题有可见和隐藏测试；「写测试」题反过来：你写测试，用故意埋了 bug 的实现（变异体）检验你的测试能抓到几个。需要 numpy / sqlite3 / yaml 的题第一次运行会自动加载对应的包。`),
    groups.map(([c, list]) => h("section", { class: "stack", style: "gap:8px" }, h("h2", null, COURSE_NAME[c]),
      h("div", { class: "plist" }, list.map(l => {
        const st = LABSTAT.get(l.id) || {};
        return h("a", { class: "prow", href: "#lab-" + l.id.replace(/^lab-/, "") },
          h("span", { class: "pill " + (st.passed ? "passed" : st.tried ? "trying" : "todo") }, st.passed ? "已通过" : st.tried ? "尝试中" : "未做"),
          h("span", { class: "t" }, l.title, l.kind === "tests" ? h("small", null, "写测试") : "", (l.packages || []).length ? h("small", null, l.packages.join(" ")) : (l.numpy ? h("small", null, "numpy") : "")),
          h("span", null, h("span", { class: "tag" }, COURSE_NAME[l.course])),
          h("span", { class: "lv " + l.level }, LEVEL[l.level] || l.level),
          h("span", { class: "small faint" }, (l.points || []).slice(0, 1).join("")));
      })))));
}

const LAB_P = {
  explain: "请帮我读懂这道题：用大白话讲清楚要实现什么、输入输出约定、有哪些边界情况要注意、面试官出这道题想考察什么。先别给代码。",
  hint: n => `我卡住了，给我第 ${n} 级提示（共 3 级：1 思路方向，2 关键步骤和数据结构，3 最容易写错的地方 + 关键 3–5 行代码）。只给这一级，结合我现在的代码。`,
  review: "请批改我的代码（以【最近一次运行】的真实结果为准）：结论；失败的测试为什么失败（定位到行）；怎么改（只给需要改的几行）；有没有隐藏的边界问题；代码风格和工程化（可读性、异常处理、复杂度）；面试官可能的追问。",
  solution: "请讲解参考实现：逐段说明每一块在做什么、为什么这么写、有哪些常见错误写法，并对比我的实现（如果我写了）。",
  follow: "如果这是面试现场手写题，面试官写完后最可能追问哪 3 个问题（扩展、性能、生产化）？每个给出回答要点，用 <details><summary>追问</summary>回答要点</details> 格式。",
};

function viewLab({ id }) {
  const lab = LABS.find(l => l.id === "lab-" + id);
  if (!lab) return h("div", { class: "page" }, h("h1", null, "没找到这道题"), h("a", { class: "btn", href: "#kb-labs" }, "回到实战列表"));
  const draftKey = "tiyan:lab:draft:" + lab.id;
  const isTests = lab.kind === "tests";
  const W = { last: null, hintsShown: 0, aiHint: 0 };
  // 右：编辑器 + 结果
  const edWrap = h("div", { class: "ed-wrap" });
  const results = h("div", { class: "results" }, h("div", { class: "empty-results" }, "「运行测试」跑可见测试，「提交」跑全部测试（含隐藏）。代码在你的浏览器里运行。"));
  const runBtn = h("button", { class: "btn sm", type: "button" }, icon("run"), lab.kind === "tests" ? "在正确实现上运行" : "运行测试");
  const subBtn = h("button", { class: "btn primary sm", type: "button" }, icon("check"), "提交");
  const resetBtn = h("button", { class: "btn ghost sm", type: "button" }, "恢复起始代码");
  const right = h("div", { class: "ws-pane right", style: "position:relative" }, h("div", { class: "ed-bar" }, runBtn, subBtn, h("span", { class: "sp" }), resetBtn), edWrap, results);
  const cm = CodeMirror(edWrap, {
    value: LS.get(draftKey, null) || lab.starter, mode: "python", theme: "tiyan", lineNumbers: true, indentUnit: 4, tabSize: 4,
    matchBrackets: true, autoCloseBrackets: true, styleActiveLine: true,
    extraKeys: { Tab: c => { if (c.somethingSelected()) c.indentSelection("add"); else c.replaceSelection("    ", "end"); }, "Shift-Tab": "indentLess", "Cmd-Enter": () => run(false), "Ctrl-Enter": () => run(false), "Shift-Cmd-Enter": () => run(true), "Shift-Ctrl-Enter": () => run(true), "Cmd-/": "toggleComment", "Ctrl-/": "toggleComment" },
  });
  let dt = null;
  cm.on("change", () => { clearTimeout(dt); dt = setTimeout(() => LS.set(draftKey, cm.getValue()), 500); });
  requestAnimationFrame(() => cm.refresh());
  let armed = false;
  resetBtn.addEventListener("click", () => {
    if (!armed) { armed = true; resetBtn.textContent = "确定恢复？"; setTimeout(() => { armed = false; resetBtn.textContent = "恢复起始代码"; }, 3000); return; }
    armed = false; resetBtn.textContent = "恢复起始代码"; cm.setValue(lab.starter);
  });

  async function run(all) {
    runBtn.disabled = subBtn.disabled = true;
    results.textContent = "";
    const msg = h("span", { class: "thinking" }, S.py === "ready" ? "运行中……" : "Python 运行环境加载中……");
    results.append(h("div", { class: "results-h" }, msg));
    let r = null, err = null;
    try {
      for (const pkg of (lab.packages || (lab.numpy ? ["numpy"] : []))) {
        if (!Py.loaded.has(pkg)) { msg.textContent = `正在加载 ${pkg}（第一次需要下载）……`; await Py.loadPackage(pkg); }
      }
      msg.textContent = "运行中……";
      if (isTests) r = await Py.json("run_testlab", [cm.getValue(), lab.impl, all ? JSON.stringify(lab.mutants) : "[]"], 20000);
      else r = await Py.json("run_lab", [cm.getValue(), all ? lab.tests + "\n\n" + lab.hidden : lab.tests], 15000);
    } catch (e) { err = (e && e.message) || String(e); }
    runBtn.disabled = subBtn.disabled = false;
    W.last = { all, r, err, code: cm.getValue() };
    const okNow = isTests ? (all && r && !r.compile_error && r.baseline && r.baseline.passed === r.baseline.total && r.killed === r.total)
      : (all && r && !r.compile_error && r.passed === r.total);
    LABSTAT.set(lab.id, { tried: true, passed: !!((LABSTAT.get(lab.id) || {}).passed || okNow) });
    if (isTests) showTests(); else show();
  }
  function show() {
    const { all, r, err } = W.last;
    results.textContent = "";
    if (err) { results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, "没有跑完")), h("div", { class: "stdout", style: "color:var(--red)" }, err)); return; }
    if (r.compile_error) { results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, "代码无法运行")), h("div", { class: "stdout", style: "color:var(--red)" }, r.compile_error)); return; }
    const ok = r.passed === r.total;
    results.append(h("div", { class: "results-h" }, h("b", { class: ok ? "ok" : "bad" }, ok ? (all ? "全部通过（含隐藏测试）" : "可见测试全部通过") : `通过 ${r.passed} / ${r.total}`),
      h("span", { class: "small faint" }, all ? "全部测试" : "可见测试"),
      ok && !all ? h("button", { class: "btn primary sm", type: "button", onclick: () => run(true) }, "提交（跑隐藏测试）") : ""));
    if (ok && all) right.append(h("div", { class: "stamp go", "aria-hidden": "true" }, "过"));
    let opened = false;
    for (const c of r.cases) {
      const det = h("details", { class: "case " + (c.pass ? "pass" : "fail") });
      if (!c.pass && !opened) { det.open = true; opened = true; }
      det.append(h("summary", null, h("span", { class: "dot" }), c.doc || c.name, h("span", { class: "faint num" }, `${c.ms} ms`)),
        h("div", { class: "case-body" }, h("div", null, h("span", null, "测试"), h("span", null, c.name)), c.error ? h("div", null, h("span", null, "原因"), h("span", { class: "err" }, c.error)) : ""));
      results.append(det);
    }
    if (r.stdout) results.append(h("div", { class: "stdout" }, r.stdout));
  }
  function showTests() {
    const { all, r, err } = W.last;
    results.textContent = "";
    if (err) { results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, "没有跑完")), h("div", { class: "stdout", style: "color:var(--red)" }, err)); return; }
    if (r.compile_error) { results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, "测试无法运行")), h("div", { class: "stdout", style: "color:var(--red)" }, r.compile_error)); return; }
    const b = r.baseline;
    const baseOk = b.passed === b.total;
    if (!baseOk) results.append(h("div", { class: "results-h" }, h("b", { class: "bad" }, `你的测试在正确实现上没通过（${b.passed} / ${b.total}）`), h("span", { class: "small faint" }, "测试本身写错了：先修好它，再去抓 bug")));
    else if (!all) results.append(h("div", { class: "results-h" }, h("b", { class: "ok" }, `在正确实现上全部通过（${b.total} 个测试）`), h("button", { class: "btn primary sm", type: "button", onclick: () => run(true) }, "提交：看能抓到几个 bug")));
    else {
      const full = r.killed === r.total;
      results.append(h("div", { class: "results-h" }, h("b", { class: full ? "ok" : "bad" }, `抓到 ${r.killed} / ${r.total} 个 bug`), h("span", { class: "small faint" }, full ? "全部变异体都被你的测试杀死了" : "还有 bug 溜过去了，看下面的提示补测试")));
      if (full) right.append(h("div", { class: "stamp go", "aria-hidden": "true" }, "过"));
      for (const mu of r.mutants) results.append(h("details", { class: "case " + (mu.killed ? "pass" : "fail"), open: !mu.killed },
        h("summary", null, h("span", { class: "dot" }), mu.killed ? "抓到了：" + mu.desc : "没抓到：" + mu.name),
        h("div", { class: "case-body" }, mu.killed ? h("div", null, h("span", null, "失败的测试"), h("span", null, mu.by.join("、"))) : h("div", null, h("span", null, "提示"), h("span", null, mu.hint)))));
    }
    for (const c of b.cases) if (!c.pass) results.append(h("details", { class: "case fail", open: true }, h("summary", null, h("span", { class: "dot" }), c.doc || c.name), h("div", { class: "case-body" }, h("div", null, h("span", null, "原因"), h("span", { class: "err" }, c.error)))));
    if (r.stdout) results.append(h("div", { class: "stdout" }, r.stdout));
  }
  runBtn.addEventListener("click", () => run(false));
  subBtn.addEventListener("click", () => run(true));

  // 左：题面 / AI 老师
  const tabs = h("div", { class: "tabs" });
  const bodyDesc = h("div", { class: "tab-body" });
  const bodyAI = h("div", { class: "tab-body flush", hidden: true });
  const left = h("div", { class: "ws-pane left" }, tabs, bodyDesc, bodyAI);
  const sw = k => { $$(".tab", tabs).forEach(b => b.classList.toggle("on", b.dataset.k === k)); bodyDesc.hidden = k !== "desc"; bodyAI.hidden = k !== "ai"; };
  [["desc", "题目"], ["ai", "AI 老师"]].forEach(([k, t]) => { const b = h("button", { class: "tab", type: "button", "data-k": k }, t); b.addEventListener("click", () => sw(k)); tabs.append(b); });
  const desc = h("div", { class: "md" }); renderMd(desc, lab.desc);
  const visTests = h("pre", { class: "example", style: "white-space:pre" }); highlightInto(visTests, (isTests ? lab.impl : lab.tests).trim());
  const ladder = h("div", { class: "hint-ladder" });
  const drawLadder = () => {
    ladder.textContent = "";
    lab.hints.forEach((t, i) => {
      if (i < W.hintsShown) ladder.append(h("div", { class: "hint" }, h("b", null, `第 ${i + 1} 级`), t));
      else if (i === W.hintsShown) ladder.append(h("div", { class: "hint locked", role: "button", tabindex: "0", onclick: () => { W.hintsShown++; drawLadder(); } }, h("span", null, `看第 ${i + 1} 级提示`)));
    });
  };
  drawLadder();
  const sol = h("div", { class: "stack" });
  let solArmed = false;
  const solBtn = h("button", { class: "btn sm", type: "button" }, "看参考实现");
  solBtn.addEventListener("click", () => {
    if (!solArmed) { solArmed = true; solBtn.textContent = "确定要看参考实现？先自己再试一次也不迟"; return; }
    solBtn.remove();
    const pre = h("pre", { class: "example", style: "white-space:pre" }); highlightInto(pre, lab.solution.trim()); sol.append(pre);
  });
  sol.append(solBtn);
  bodyDesc.append(h("div", { class: "desc" },
    h("div", { class: "row" }, h("span", { class: "tag" }, COURSE_NAME[lab.course]), h("span", { class: "lv " + lab.level }, LEVEL[lab.level] || lab.level), lab.numpy ? h("span", { class: "tag" }, "numpy") : ""),
    desc,
    lab.points && lab.points.length ? h("div", null, h("h3", null, "考察点"), h("ul", { class: "signals" }, lab.points.map(p => h("li", null, h("span", null, p))))) : "",
    isTests ? h("div", { class: "stack" }, h("h3", null, "被测实现（这是正确版本）"), visTests, h("p", { class: "small muted" }, `提交时会用 ${lab.mutants.length} 个故意埋了 bug 的版本去跑你的测试。`)) : h("details", { class: "qa" }, h("summary", null, "可见测试代码"), visTests),
    h("div", { class: "stack" }, h("h3", null, "提示阶梯"), ladder),
    h("div", { class: "stack" }, h("h3", null, "参考实现"), sol)));
  const ctx = () => [KNOW_TEACHER.split("\n")[0], isTests ? "现在学习者在做一道「你来写测试」题：他要为下面的正确实现写测试，用变异体检验测试质量。你是他的测试设计老师：引导他从等价类、边界、异常、状态和注入依赖等角度设计用例，不要直接给出能杀死全部变异体的完整测试。" : "现在学习者在做一道「手写实战」编程题，你是他的编程老师：讲清为什么这么写，先引导再给代码。",
    "【题目】" + lab.title + "\n" + lab.desc, isTests ? "【被测实现】\n```python\n" + clip(lab.impl, 4000) + "\n```" : "【可见测试】\n```python\n" + clip(lab.tests, 3000) + "\n```",
    "【参考实现】（学习者没要求就不要贴完整代码）\n```python\n" + lab.solution + "\n```",
    "【学习者当前代码】\n```python\n" + numbered(cm.getValue()) + "\n```",
    W.last ? "【最近一次运行】" + (W.last.err || (W.last.r.compile_error ? "无法运行：" + W.last.r.compile_error
      : isTests ? `在正确实现上通过 ${W.last.r.baseline.passed}/${W.last.r.baseline.total}` + (W.last.all ? `；抓到 ${W.last.r.killed}/${W.last.r.total} 个变异体；没抓到的提示：` + W.last.r.mutants.filter(x => !x.killed).map(x => x.hint).join("；") : "")
      : `通过 ${W.last.r.passed}/${W.last.r.total}\n` + W.last.r.cases.filter(c => !c.pass).slice(0, 3).map(c => `- ${c.name}：${c.error}`).join("\n"))) : "【最近一次运行】还没运行。"].join("\n\n");
  const chat = new Chat({
    key: "lab:" + lab.id, context: ctx,
    placeholder: "哪里不懂就问，比如“为什么工具报错要回填给模型？”",
    intro: "我能看到题目、你的代码和测试结果。没思路点「讲讲题意」或「给我提示」，写完了点「批改代码」。",
    actions: [
      { label: "讲讲题意", run: c => c.send(LAB_P.explain, { label: "讲讲题意" }) },
      { label: "给我提示", run: c => { W.aiHint = Math.min(3, W.aiHint + 1); c.send(LAB_P.hint(W.aiHint), { label: `提示 ${W.aiHint}/3` }); } },
      { label: "批改代码", run: async c => { if (!W.last || W.last.code !== cm.getValue()) await run(false); c.send(LAB_P.review, { label: "批改代码" }); } },
      { label: "讲参考实现", run: c => c.send(LAB_P.solution, { label: "讲参考实现" }) },
      { label: "面试追问", run: c => c.send(LAB_P.follow, { label: "面试追问" }) },
    ],
  });
  bodyAI.append(chat.el);
  S.liveChats = [chat];
  onLeave(() => { S.liveChats = []; if (chat.ctl) chat.ctl.abort(); });
  sw("desc");
  return h("div", { class: "ws" },
    h("div", { class: "ws-head" }, h("a", { class: "btn ghost sm", href: "#kb-labs" }, icon("back"), "实战列表"), h("h1", null, lab.title), h("span", { class: "lv " + lab.level }, LEVEL[lab.level] || lab.level)),
    h("div", { class: "ws-grid" }, left, right));
}
