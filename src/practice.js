// ---------- 练习：选择题自动判分、简答题和深挖题由 AI 阅卷；每日练习与错题本 ----------
const EX = {
  all() { return LS.get("tiyan:ex", {}); },
  get(id) { return this.all()[id] || null; },
  record(id, rec) {
    const all = this.all();
    const prev = all[id] || { n: 0 };
    all[id] = Object.assign({}, prev, rec, { n: (prev.n || 0) + 1, at: Date.now() });
    LS.set("tiyan:ex", all);
    const day = new Date().toISOString().slice(0, 10);
    const days = LS.get("tiyan:ex:days", {});
    days[day] = (days[day] || 0) + 1;
    LS.set("tiyan:ex:days", days);
  },
  wrong(rec) { return rec && ((rec.t === "c" && !rec.ok) || (rec.t !== "c" && rec.score != null && rec.score < 6)); },
  streak() {
    const days = LS.get("tiyan:ex:days", {});
    let n = 0;
    for (let d = new Date(); ; d.setDate(d.getDate() - 1)) {
      const k = d.toISOString().slice(0, 10);
      if (days[k]) n++;
      else if (n > 0 || k !== new Date().toISOString().slice(0, 10)) break;
      if (n > 400) break;
    }
    return n;
  },
  today() { return LS.get("tiyan:ex:days", {})[new Date().toISOString().slice(0, 10)] || 0; },
};
function allSections() { return KNOW.flatMap(c => c.sections.map(s => Object.assign({}, s, { course: c.name, courseId: c.id }))); }
// 题目统一编号：节 id + 题型 + 序号
function exItems(s) {
  const out = [];
  (s.choice || []).forEach((q, i) => out.push({ id: `${s.id}#c${i}`, kind: "c", sec: s, q }));
  (s.short || []).forEach((q, i) => out.push({ id: `${s.id}#s${i}`, kind: "s", sec: s, q }));
  (s.drill || []).forEach((q, i) => out.push({ id: `${s.id}#d${i}`, kind: "d", sec: s, q }));
  return out;
}

const GRADE_PROMPT = (it, answer) => {
  const q = it.q;
  const pts = it.kind === "s" ? q.points : [];
  return `你是严格但友善的阅卷老师，在批改「${it.sec.course} › ${it.sec.title}」这一节的${it.kind === "d" ? "面试深挖题" : "简答题"}。
【题目】${q.q}
${pts.length ? "【得分点】（每个得分点权重相同，满分 10 分；意思答到即可，不要求原话）\n" + pts.map((p, i) => `${i}. ${p}`).join("\n") : "【评分方式】没有固定得分点，对照参考要点判断：覆盖要点、原理正确、有具体例子或数据的给高分。"}
【参考${it.kind === "d" ? "要点" : "答案"}】${q.reference || q.a}
【学习者的回答】
${clip(answer, 3000)}
评分档位：9–10 要点全、原理准、有例子或数据；7–8.5 要点基本齐、个别不够深；5–6.5 方向对但缺关键要点；3–4.5 有错误或大部分缺失；0–2.5 基本没答或错误。
要求：答非所问、只有空话、或者有事实错误要扣分，并在 feedback 里指出错在哪。
只返回 JSON：{"score": 7, "hit": [0, 2], "partial": [1], "missed": [3], "feedback": "两三句点评：哪里好、缺了什么、哪里说错了", "better": "在学习者回答基础上改写得更好的版本，150–300 字，面试里能直接说出口"}
（hit / partial / missed 是得分点的下标；没有得分点时都给空数组）`;
};

function choiceBlock(it, onDone) {
  const q = it.q;
  const multi = q.answer.length > 1;
  const name = "opt-" + it.id.replace(/[^\w-]/g, "_");
  const prev = EX.get(it.id);
  const box = h("div", { class: "ex-item" });
  const opts = q.options.map((o, i) => h("label", { class: "ex-opt" }, h("input", { type: multi ? "checkbox" : "radio", name, value: i, id: `${name}-${i}` }), h("span", null, String.fromCharCode(65 + i) + ". " + o)));
  const result = h("div", { class: "ex-result", hidden: true });
  const btn = h("button", { class: "btn sm primary", type: "button" }, "提交");
  const again = h("button", { class: "btn sm ghost", type: "button", hidden: true }, "重做");
  btn.addEventListener("click", () => {
    const picked = opts.map((l, i) => l.querySelector("input").checked ? i : -1).filter(i => i >= 0);
    if (!picked.length) { toast("先选一个答案"); return; }
    const ok = picked.length === q.answer.length && picked.every(i => q.answer.includes(i));
    opts.forEach((l, i) => { l.classList.toggle("right", q.answer.includes(i)); l.classList.toggle("wrong", picked.includes(i) && !q.answer.includes(i)); l.querySelector("input").disabled = true; });
    result.hidden = false; result.textContent = "";
    const exp = h("div", { class: "md small" }); renderMd(exp, q.explain);
    result.append(h("b", { class: ok ? "ok" : "bad" }, ok ? "答对了" : `答错了，正确答案：${q.answer.map(i => String.fromCharCode(65 + i)).join("、")}`), exp);
    btn.hidden = true; again.hidden = false;
    EX.record(it.id, { t: "c", ok, sec: it.sec.id });
    if (onDone) onDone(ok);
  });
  again.addEventListener("click", () => { opts.forEach(l => { l.classList.remove("right", "wrong"); const x = l.querySelector("input"); x.disabled = false; x.checked = false; }); result.hidden = true; btn.hidden = false; again.hidden = true; });
  box.append(h("div", { class: "ex-q" }, h("span", { class: "tag" }, multi ? "多选" : "单选"), " ", q.q, prev ? h("span", { class: "small " + (prev.ok ? "faint" : ""), style: prev.ok ? "" : "color:var(--red)" }, prev.ok ? "　上次答对" : "　上次答错") : ""),
    h("div", { class: "ex-opts" }, opts), h("div", { class: "row" }, btn, again), result);
  return box;
}

function writtenBlock(it, onDone) {
  const q = it.q;
  const prev = EX.get(it.id);
  const box = h("div", { class: "ex-item" });
  const ta = h("textarea", { class: "mock-input", id: "ans-" + it.id.replace(/[^\w-]/g, "_"), style: "min-height:96px", placeholder: it.kind === "d" ? "像面试一样回答：先说结论，再讲原理和例子" : "写下你的回答，然后交给老师阅卷" });
  ta.value = LS.get("tiyan:exdraft:" + it.id, "");
  ta.addEventListener("input", () => LS.set("tiyan:exdraft:" + it.id, ta.value));
  const btn = h("button", { class: "btn sm primary", type: "button" }, "交给老师阅卷");
  const ref = h("details", { class: "qa" }, h("summary", null, it.kind === "d" ? "看参考要点" : "看参考答案"));
  const refMd = h("div", { class: "md small" }); renderMd(refMd, q.reference || q.a); ref.append(refMd);
  if (it.kind === "s") ref.append(h("div", { class: "small muted" }, "得分点：" + q.points.join("；")));
  const out = h("div", { class: "ex-result", hidden: true });
  btn.addEventListener("click", async () => {
    const ans = ta.value.trim();
    if (ans.length < 6) { toast("先写下你的回答"); return; }
    if (!AI.ok()) { toast(aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" })); if (S.ai === "needkey") openKeyDialog(); return; }
    btn.disabled = true; out.hidden = false; out.textContent = ""; out.append(h("div", { class: "thinking" }, "老师在阅卷……"));
    try {
      const g = await AI.ask(GRADE_PROMPT(it, ans), { json: true, tier: "default" });
      const score = Math.max(0, Math.min(10, Math.round((Number(g.score) || 0) * 2) / 2));
      out.textContent = "";
      const [cls, band] = mockBand(score);
      const pts = it.kind === "s" ? q.points : [];
      const mark = (arr, i) => Array.isArray(arr) && arr.map(Number).includes(i);
      const better = h("div", { class: "md small" }); renderMd(better, String(g.better || ""));
      out.append(
        h("div", { class: "row" }, h("span", { class: "mock-score num" }, String(score), h("small", null, " / 10")), h("span", { class: "pill " + cls }, band), h("span", { class: "small faint" }, "AI 估算，仅供参考")),
        g.feedback ? h("p", null, String(g.feedback)) : "",
        pts.length ? h("ul", { class: "ex-points" }, pts.map((p, i) => h("li", { class: mark(g.hit, i) ? "hit" : mark(g.partial, i) ? "part" : "miss" }, h("b", null, mark(g.hit, i) ? "答到" : mark(g.partial, i) ? "部分" : "缺失"), p))) : "",
        g.better ? h("details", { class: "qa", open: score < 8 }, h("summary", null, "更好的回答"), better) : "");
      EX.record(it.id, { t: it.kind, score, sec: it.sec.id });
      if (onDone) onDone(score);
    } catch (e) {
      out.textContent = e && e.code ? aiErr(e) : "阅卷失败：" + ((e && e.message) || e);
    } finally { btn.disabled = false; }
  });
  box.append(h("div", { class: "ex-q" }, h("span", { class: "tag" }, it.kind === "d" ? `深挖 · ${q.level}` : "简答"), " ", q.q,
    prev && prev.score != null ? h("span", { class: "small", style: prev.score < 6 ? "color:var(--red)" : "color:var(--ink-3)" }, `　上次 ${prev.score} 分`) : ""),
    ta, h("div", { class: "row" }, btn), out, ref);
  return box;
}
function exBlock(it, onDone) { return it.kind === "c" ? choiceBlock(it, onDone) : writtenBlock(it, onDone); }

// 节内「练习」标签
function sectionPractice(s) {
  const items = exItems(s);
  const done = items.filter(x => x.kind !== "d" && EX.get(x.id)).length;
  return h("div", { class: "stack", style: "gap:16px" },
    h("p", { class: "small muted" }, `选择题提交后马上判分；简答题交给 AI 老师按得分点阅卷。已做 ${done} / ${items.filter(x => x.kind !== "d").length} 题，结果会记进错题本和每日练习。`),
    h("h3", null, "选择题"), items.filter(x => x.kind === "c").map(x => exBlock(x)),
    h("h3", null, "简答题"), items.filter(x => x.kind === "s").map(x => exBlock(x)));
}
// 节内「深挖」标签
function sectionDrill(s) {
  const items = exItems(s).filter(x => x.kind === "d");
  const hasMaterial = !!MK.resume().trim();
  const toMock = h("button", { class: "btn primary sm", type: "button" }, "结合我的项目，模拟面试这一节");
  toMock.addEventListener("click", () => {
    LS.set("tiyan:mock:preset", { focus: `「${s.title}」这一节的知识点（${(s.points || []).join("；")}），并结合候选人项目里的相关经历深挖落地细节`, type: "project", count: 4 });
    go("mock");
  });
  return h("div", { class: "stack", style: "gap:16px" },
    h("div", { class: "callout blue" }, h("b", null, "面试官会这样一层层追问。"), "先自己答，再交给老师阅卷，最后对照参考要点。",
      h("div", { class: "row", style: "margin-top:8px" }, toMock, h("span", { class: "small muted" }, hasMaterial ? "会用你在「模拟面试」里填的简历和项目材料。" : "先去「模拟面试」填好简历和项目材料，效果更好。"))),
    items.map(x => exBlock(x)));
}

// ----- 每日练习 -----
function pickDaily() {
  const all = allSections().flatMap(exItems).filter(x => x.kind !== "d");
  const day = new Date().toISOString().slice(0, 10);
  const saved = LS.get("tiyan:daily", null);
  if (saved && saved.day === day) return saved.ids.map(id => all.find(x => x.id === id)).filter(Boolean);
  const rnd = (seed => () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; })(Number(day.replace(/-/g, "")) % 233280);
  const shuffle = a => a.map(x => [rnd(), x]).sort((p, q) => p[0] - q[0]).map(x => x[1]);
  const wrong = shuffle(all.filter(x => EX.wrong(EX.get(x.id))));
  const fresh = shuffle(all.filter(x => !EX.get(x.id)));
  const old = shuffle(all.filter(x => EX.get(x.id) && !EX.wrong(EX.get(x.id)))).sort((a, b) => EX.get(a.id).at - EX.get(b.id).at);
  const pick = (kind, n) => [...wrong, ...fresh, ...old].filter(x => x.kind === kind).filter((x, i, arr) => arr.findIndex(y => y.id === x.id) === i).slice(0, n);
  const ids = [...pick("c", 6), ...pick("s", 2)].map(x => x.id);
  LS.set("tiyan:daily", { day, ids });
  return ids.map(id => all.find(x => x.id === id));
}
function viewDaily() {
  const items = pickDaily();
  const stat = h("div", { class: "stats" });
  const drawStat = () => {
    stat.textContent = "";
    const done = items.filter(x => { const r = EX.get(x.id); return r && new Date(r.at).toISOString().slice(0, 10) === new Date().toISOString().slice(0, 10); }).length;
    stat.append(h("div", { class: "stat" }, h("b", null, `${done}`, h("small", { class: "faint", style: "font-size:14px" }, ` / ${items.length}`)), h("span", null, "今日完成")),
      h("div", { class: "stat" }, h("b", null, EX.streak()), h("span", null, "连续天数")),
      h("div", { class: "stat" }, h("b", null, Object.values(EX.all()).filter(r => EX.wrong(r)).length), h("span", null, "错题本")));
  };
  drawStat();
  return h("div", { class: "stack", style: "gap:18px" },
    h("div", { class: "spread" }, stat, h("p", { class: "small muted", style: "max-width:46ch" }, "每天 8 题：6 道选择 + 2 道简答。优先出错题和没做过的题，同一天打开题目不变。")),
    items.map((x, i) => h("section", { class: "panel", style: "gap:10px" },
      h("div", { class: "spread small faint" }, h("span", null, `第 ${i + 1} 题 · ${x.sec.course} › ${x.sec.title}`), h("a", { href: "#kb", onclick: e => { e.preventDefault(); LS.set("tiyan:sec:ai", x.sec.id); go("kb"); } }, "回到这一节 →")),
      exBlock(x, drawStat))));
}

// ----- 错题本 -----
function viewWrong() {
  const all = allSections().flatMap(exItems);
  const items = all.filter(x => EX.wrong(EX.get(x.id))).sort((a, b) => EX.get(b.id).at - EX.get(a.id).at);
  if (!items.length) return h("div", { class: "panel" }, h("h2", null, "错题本是空的"), h("p", { class: "muted" }, "选择题答错、简答题低于 6 分，会自动收进这里。重新答对就会移出去。"));
  return h("div", { class: "stack", style: "gap:14px" },
    h("p", { class: "small muted" }, `共 ${items.length} 题。重新答对（简答 ≥ 6 分）后会自动移出。`),
    items.map(x => h("section", { class: "panel", style: "gap:10px" },
      h("div", { class: "small faint" }, `${x.sec.course} › ${x.sec.title} · 做过 ${EX.get(x.id).n} 次`),
      exBlock(x))));
}
