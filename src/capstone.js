// ---------- 项目实战：照着里程碑把项目做出来，AI 按验收标准评审，最后沉淀成简历和面试故事 ----------
const CAPS = JSON.parse(document.getElementById("capstones-data").textContent || "[]");
const CAPST = {
  get(id) { return LS.get("tiyan:cap:" + id, { ms: {}, metrics: "", out: null }); },
  set(id, v) { LS.set("tiyan:cap:" + id, v); },
  ms(id, mid) { const v = this.get(id); return v.ms[mid] || { checks: [], done: false, notes: "", submission: "" }; },
  setMs(id, mid, patch) { const v = this.get(id); v.ms[mid] = Object.assign(this.ms(id, mid), patch, { at: Date.now() }); this.set(id, v); },
};
function capProgress(c) { const v = CAPST.get(c.id); return c.milestones.filter(m => (v.ms[m.id] || {}).done).length; }
function codeBox(text) {
  const pre = h("pre", { class: "example", style: "white-space:pre;position:relative" }, text);
  const b = h("button", { class: "btn sm copy", type: "button", style: "position:absolute;top:6px;right:6px" }, "复制");
  b.addEventListener("click", () => copyText(text, b));
  pre.append(b);
  return pre;
}

function viewCapList() {
  if (!CAPS.length) return h("div", { class: "page" }, h("h1", null, "项目实战"), h("p", { class: "muted" }, "项目还在准备中，稍后刷新再来。"));
  return h("div", { class: "page" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "项目实战"), h("h1", null, "做一个能写进简历、经得起深挖的项目"),
      h("p", { class: "lede" }, "单点练习证明你会写某个函数；社招面试要的是一个完整、能跑、有数据的项目。这里有两个项目，按里程碑在你自己的电脑上实现，每一步都有测试和验收标准；做完把测试输出、代码和数据交给 AI 评审，最后整理成简历描述、项目介绍和面试故事。")),
    h("div", { class: "hubs" }, CAPS.map(c => {
      const done = capProgress(c);
      return h("a", { class: "panel hub", href: "#cap-" + c.id },
        h("div", { class: "spread" }, h("span", { class: "eyebrow" }, c.role), h("span", { class: "small faint num" }, `${done} / ${c.milestones.length} 个里程碑`)),
        h("h2", null, c.title), h("p", { class: "muted" }, c.summary),
        h("div", { class: "bar" }, h("i", { style: `width:${done / c.milestones.length * 100}%` })),
        h("div", { class: "row" }, (c.stack || []).slice(0, 6).map(s => h("span", { class: "tag" }, s))));
    })),
    h("section", { class: "panel" }, h("h2", null, "怎么用"),
      h("ol", { class: "steps" }, [
        ["下载项目骨架", "骨架里有完整的目录结构、函数签名、文档模板和每个里程碑的测试；实现部分是空的。"],
        ["按里程碑实现", "每完成一个里程碑，对应的 pytest 测试应该全部通过。卡住了看提示，或者问 AI。"],
        ["交给 AI 评审", "把测试输出、关键代码、你做的决定和数据贴进来，AI 按验收标准逐条判断有没有证据。"],
        ["记下决策和数据", "每一步写几句：为什么这么设计、遇到什么问题、数据是多少。这是之后面试被深挖时的弹药。"],
        ["沉淀成简历和面试故事", "全部完成后，一键生成简历描述、2 分钟项目介绍、STAR 故事和深挖问答，并存成模拟面试的项目卡。"],
      ].map(([t, d], i) => h("li", null, h("b", { class: "num" }, i + 1), h("span", null, h("b", null, t), "：", d))))));
}

function viewCap({ id, mid }) {
  const c = CAPS.find(x => x.id === id);
  if (!c) return h("div", { class: "page" }, h("h1", null, "没找到这个项目"), h("a", { class: "btn", href: "#cap" }, "回到项目列表"));
  if (mid) return viewMilestone(c, c.milestones.find(m => m.id === mid));
  const v = CAPST.get(c.id);
  const done = capProgress(c);
  return h("div", { class: "page" },
    h("div", { class: "row small" }, h("a", { href: "#cap" }, "项目实战"), h("span", { class: "faint" }, "/"), h("span", { class: "muted" }, c.title)),
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, c.role), h("h1", null, c.title), h("p", { class: "lede" }, c.why)),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "开始"),
        h("div", { class: "row" }, h("a", { class: "btn primary", href: c.zip, download: c.id + ".zip" }, "下载项目骨架（zip）"), h("span", { class: "small faint" }, `${(c.files || []).length} 个文件`)),
        h("p", { class: "small muted" }, "下载后在终端里："),
        codeBox(`unzip ${c.id}.zip && cd ${c.id}\npython3 -m venv .venv && source .venv/bin/activate\npip install -e '.[dev]'\npytest -q ${c.milestones[0].test_file}`),
        h("p", { class: "small muted" }, c.setup),
        h("div", { class: "row" }, (c.stack || []).map(s => h("span", { class: "tag" }, s)))),
      h("section", { class: "panel" }, h("h2", null, "进度"),
        h("div", { class: "mock-avg num" }, String(done), h("span", null, ` / ${c.milestones.length} 个里程碑`)),
        h("div", { class: "bar" }, h("i", { style: `width:${done / c.milestones.length * 100}%` })),
        h("p", { class: "small muted" }, done === c.milestones.length ? "全部完成了，去下面整理成简历和面试故事。" : "每个里程碑完成后点「标记完成」。顺序做最省事，后面的里程碑会用到前面的模块。"))),
    h("section", { class: "stack" }, h("h2", null, "里程碑"),
      h("div", { class: "plist" }, c.milestones.map((m, i) => {
        const st = v.ms[m.id] || {};
        const checks = (st.checks || []).filter(Boolean).length;
        return h("a", { class: "prow cap-row", href: `#cap-${c.id}--${m.id}` },
          h("span", { class: "pill " + (st.done ? "passed" : st.review || checks ? "trying" : "todo") }, st.done ? "已完成" : st.review || checks ? "进行中" : "未开始"),
          h("span", { class: "t" }, `${i + 1}. ${m.title}`, h("small", { style: "font-family:var(--sans)" }, clip(m.goal, 50))),
          h("span", { class: "small faint num" }, `验收 ${checks}/${m.acceptance.length}`),
          h("span", { class: "small faint num" }, st.review ? `评审 ${st.review.score}` : ""),
          h("span", { class: "small faint mono" }, m.test_file.split("/").pop()));
      }))),
    capFinal(c));
}

function viewMilestone(c, m) {
  if (!m) return h("div", { class: "page" }, h("h1", null, "没找到这个里程碑"), h("a", { class: "btn", href: "#cap-" + c.id }, "回到项目"));
  const idx = c.milestones.indexOf(m);
  const st = CAPST.ms(c.id, m.id);
  const checks = m.acceptance.map((a, i) => {
    const cb = h("input", { type: "checkbox", id: `acc-${c.id}-${m.id}-${i}`, checked: !!(st.checks || [])[i] });
    cb.addEventListener("change", () => { const cur = CAPST.ms(c.id, m.id); const arr = (cur.checks || []).slice(); arr[i] = cb.checked; CAPST.setMs(c.id, m.id, { checks: arr }); });
    return h("label", { class: "ex-opt" }, cb, h("span", null, a));
  });
  let shown = 0;
  const ladder = h("div", { class: "hint-ladder" });
  const drawLadder = () => { ladder.textContent = ""; m.hints.forEach((t, i) => { if (i < shown) ladder.append(h("div", { class: "hint" }, h("b", null, `第 ${i + 1} 级`), t)); else if (i === shown) ladder.append(h("div", { class: "hint locked", role: "button", tabindex: "0", onclick: () => { shown++; drawLadder(); } }, h("span", null, `看第 ${i + 1} 级提示`))); }); };
  drawLadder();
  const notes = h("textarea", { id: `notes-${c.id}-${m.id}`, class: "mock-input", style: "min-height:110px", placeholder: "我的记录：做了哪些设计决定、为什么；遇到了什么问题、怎么定位和解决的；关键数据（测试数量、耗时、成功率……）。这些会用来生成简历和面试故事。" });
  notes.value = st.notes || "";
  notes.addEventListener("input", () => { clearTimeout(notes._t); notes._t = setTimeout(() => CAPST.setMs(c.id, m.id, { notes: notes.value }), 400); });
  const sub = h("textarea", { id: `sub-${c.id}-${m.id}`, class: "mock-input", style: "min-height:150px", placeholder: `贴上要评审的内容：\n1. 运行 pytest 的输出（如 ${m.test_file} 的结果）\n2. 关键代码（不用全贴，挑核心函数）\n3. 你的设计说明和数据` });
  sub.value = st.submission || "";
  sub.addEventListener("input", () => { clearTimeout(sub._t); sub._t = setTimeout(() => CAPST.setMs(c.id, m.id, { submission: sub.value }), 400); });
  const reviewBox = h("div", { class: "stack" });
  const drawReview = rv => {
    reviewBox.textContent = "";
    if (!rv) return;
    const [cls, band] = mockBand(rv.score);
    reviewBox.append(
      h("div", { class: "row" }, h("span", { class: "mock-score num" }, String(rv.score), h("small", null, " / 10")), h("span", { class: "pill " + cls }, band), h("span", { class: "small faint" }, `AI 估算，仅供参考 · ${fmtDate(rv.at)}`)),
      h("ul", { class: "ex-points" }, rv.criteria.map(x => h("li", { class: x.status === "met" ? "hit" : x.status === "partial" ? "part" : "miss" }, h("b", null, x.status === "met" ? "达到" : x.status === "partial" ? "部分" : "没证据"), h("span", null, (m.acceptance[x.i] || "") + (x.comment ? `　— ${x.comment}` : ""))))),
      rv.strengths.length ? h("div", null, h("h3", null, "做得好"), h("ul", { class: "mock-ul good" }, rv.strengths.map(x => h("li", null, x)))) : "",
      rv.gaps.length ? h("div", null, h("h3", null, "还缺什么"), h("ul", { class: "mock-ul bad" }, rv.gaps.map(x => h("li", null, x)))) : "",
      rv.next.length ? h("div", null, h("h3", null, "下一步"), h("ul", { class: "mock-ul" }, rv.next.map(x => h("li", null, x)))) : "",
      rv.interview.length ? h("div", null, h("h3", null, "根据你提交的内容，面试官会追问"), ...rv.interview.map(x => { const d = h("details", { class: "qa" }, h("summary", null, x.q)); const a = h("div", { class: "md small" }); renderMd(a, x.a); d.append(a); return d; })) : "");
  };
  drawReview(st.review);
  const status = h("span", { class: "small muted" });
  const revBtn = h("button", { class: "btn primary sm", type: "button" }, "交给 AI 评审");
  revBtn.addEventListener("click", async () => {
    if (sub.value.trim().length < 30) { status.textContent = "先贴上测试输出、关键代码或设计说明。"; return; }
    if (!AI.ok()) { status.textContent = aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" }); if (S.ai === "needkey") openKeyDialog(); return; }
    revBtn.disabled = true; status.textContent = "AI 在按验收标准评审……（大约 20–60 秒）";
    try {
      const r = await AI.ask(`你是资深${c.role}面试官兼代码评审，在评审候选人做的「${c.title}」项目的里程碑「${m.title}」。
【里程碑目标】${m.goal}
【验收标准】
${m.acceptance.map((a, i) => `${i}. ${a}`).join("\n")}
【候选人的记录】
${clip(notes.value, 3000) || "（没写）"}
【候选人提交的材料】（测试输出、关键代码、设计说明、数据）
${clip(sub.value, 14000)}

请逐条对照验收标准判断：met（有证据达到）/ partial（部分达到）/ missing（没看到证据）。只认证据（测试输出、代码、数据），不要只信候选人的自述；代码里有明显 bug 或不符合生产要求的地方要指出。
评分档位：9–10 全部达到且有超出预期的工程质量；7–8.5 基本达到；5–6.5 一半左右；3–4.5 大部分缺失；0–2.5 几乎没有证据。
只返回 JSON：{"score": 7, "criteria": [{"i": 0, "status": "met", "comment": "依据"}], "strengths": ["做得好的地方"], "gaps": ["具体还缺什么"], "next": ["下一步建议"], "interview": [{"q": "根据提交的内容，面试官会追问的问题", "a": "回答要点"}]}`, { json: true, tier: "complex" });
      const rv = {
        score: Math.max(0, Math.min(10, Math.round((Number(r.score) || 0) * 2) / 2)), at: Date.now(),
        criteria: (Array.isArray(r.criteria) ? r.criteria : []).map(x => ({ i: Number(x.i), status: ["met", "partial", "missing"].includes(x.status) ? x.status : "missing", comment: String(x.comment || "") })).filter(x => x.i >= 0 && x.i < m.acceptance.length),
        strengths: arrStr(r.strengths, 6), gaps: arrStr(r.gaps, 8), next: arrStr(r.next, 6),
        interview: (Array.isArray(r.interview) ? r.interview : []).slice(0, 4).map(x => ({ q: String((x && x.q) || ""), a: String((x && x.a) || "") })),
      };
      CAPST.setMs(c.id, m.id, { review: rv, submission: sub.value });
      drawReview(rv); status.textContent = "";
    } catch (e) { status.textContent = e && e.code ? aiErr(e) : "评审失败：" + ((e && e.message) || e); }
    finally { revBtn.disabled = false; }
  });
  const doneBtn = h("button", { class: "btn sm", type: "button" }, st.done ? "已完成（点击取消）" : "标记完成");
  doneBtn.addEventListener("click", () => {
    const cur = CAPST.ms(c.id, m.id);
    CAPST.setMs(c.id, m.id, { done: !cur.done });
    doneBtn.textContent = !cur.done ? "已完成（点击取消）" : "标记完成";
    toast(!cur.done ? "已标记完成" : "已取消完成");
  });
  const prev = c.milestones[idx - 1], next = c.milestones[idx + 1];
  return h("div", { class: "page" },
    h("div", { class: "row small" }, h("a", { href: "#cap" }, "项目实战"), h("span", { class: "faint" }, "/"), h("a", { href: "#cap-" + c.id }, c.title), h("span", { class: "faint" }, "/"), h("span", { class: "muted" }, `里程碑 ${idx + 1}`)),
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, `${c.title} · 里程碑 ${idx + 1} / ${c.milestones.length}`), h("h1", null, m.title), h("p", { class: "lede" }, m.goal)),
    h("div", { class: "callout blue" }, h("b", null, "面试官为什么关心："), m.why),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "要做的事"), h("ol", { class: "steps" }, m.tasks.map((t, i) => h("li", null, h("b", { class: "num" }, i + 1), h("span", null, t))))),
      h("section", { class: "panel" }, h("h2", null, "交付物"), h("ul", { class: "signals" }, m.deliverables.map(t => h("li", null, h("span", null, t)))),
        h("h3", null, "跑测试"), codeBox(`pytest -q ${m.test_file}`))),
    h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "验收标准"), h("span", { class: "small faint" }, "做到一条勾一条")), h("div", { class: "ex-opts" }, checks)),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "提示"), ladder),
      h("section", { class: "panel" }, h("h2", null, "做完后面试官会问"), ...m.interview.map(x => { const d = h("details", { class: "qa" }, h("summary", null, x.q)); const a = h("div", { class: "md small" }); renderMd(a, x.a); d.append(a); return d; }),
        h("p", { class: "small muted" }, h("b", null, "写进简历："), m.resume))),
    h("section", { class: "panel" }, h("h2", null, "我的记录"), notes),
    h("section", { class: "panel" }, h("h2", null, "AI 评审"), sub, h("div", { class: "row" }, revBtn, doneBtn, status), reviewBox,
      h("p", { class: "small faint" }, "提交的内容会发给 DeepSeek 评审；不要贴密钥、内网地址等敏感信息。")),
    h("div", { class: "spread" },
      prev ? h("a", { class: "btn sm", href: `#cap-${c.id}--${prev.id}` }, "← " + prev.title) : h("span"),
      next ? h("a", { class: "btn sm primary", href: `#cap-${c.id}--${next.id}` }, next.title + " →") : h("a", { class: "btn sm primary", href: "#cap-" + c.id }, "回到项目，整理成果 →")));
}

function capFinal(c) {
  const v = CAPST.get(c.id);
  const metrics = h("textarea", { id: `metrics-${c.id}`, class: "mock-input", style: "min-height:90px", placeholder: "填写你实测的关键数据和口径，比如：评测集 40 条；任务成功率 82%（两次运行取平均）；P95 延迟 3.1s；单次平均成本 0.004 元；断点恢复测试 12 个场景全部通过……" });
  metrics.value = v.metrics || "";
  metrics.addEventListener("input", () => { clearTimeout(metrics._t); metrics._t = setTimeout(() => { const cur = CAPST.get(c.id); cur.metrics = metrics.value; CAPST.set(c.id, cur); }, 400); });
  const outBox = h("div", { class: "stack" });
  const status = h("span", { class: "small muted" });
  const draw = o => {
    outBox.textContent = "";
    if (!o) return;
    const mdBlock = t => { const d = h("div", { class: "md" }); renderMd(d, t); return d; };
    const toCard = h("button", { class: "btn sm", type: "button" }, "存成模拟面试的项目卡");
    toCard.addEventListener("click", () => { const cs = MK.cards(); cs.push(Object.assign({ id: "c" + Date.now().toString(36) }, o.card || {}, { name: (o.card && o.card.name) || o.title })); MK.saveCards(cs); toast("已存成项目卡，去「模拟面试」就能用"); });
    const md = [`# ${o.title}`, "", o.oneliner, "", "## 简历描述", "", ...o.bullets.map(b => "- " + b), "", "## 2 分钟项目介绍", "", o.pitch, "", "## STAR", "", `- S：${o.star.S}`, `- T：${o.star.T}`, `- A：${o.star.A}`, `- R：${o.star.R}`, "", "## 深挖问答", "", ...o.deep.flatMap(x => [`### ${x.q}`, "", x.a, ""])].join("\n");
    const dl = h("button", { class: "btn sm", type: "button", onclick: () => downloadFile(`${c.title}-简历与面试材料.md`, md, "text/markdown") }, "导出 Markdown");
    outBox.append(
      h("h3", null, o.title), h("p", { class: "muted" }, o.oneliner),
      h("h3", null, "简历描述"), h("ul", { class: "mock-ul" }, o.bullets.map(b => h("li", null, b))),
      h("h3", null, "2 分钟项目介绍"), mdBlock(o.pitch),
      h("h3", null, "STAR"), h("ul", { class: "mock-ul" }, ["S", "T", "A", "R"].map(k => h("li", null, h("b", null, k + "："), o.star[k] || ""))),
      h("h3", null, "面试官最可能深挖的问题"), ...o.deep.map(x => { const d = h("details", { class: "qa" }, h("summary", null, x.q)); d.append(mdBlock(x.a)); return d; }),
      h("div", { class: "row" }, toCard, dl),
      h("p", { class: "small faint" }, "【待补充】的地方是 AI 认为缺数据的位置，请用你的真实数据替换，不要直接用占位。"));
  };
  draw(v.out);
  const gen = h("button", { class: "btn primary sm", type: "button" }, "生成简历描述和面试故事");
  gen.addEventListener("click", async () => {
    if (!AI.ok()) { status.textContent = aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" }); return; }
    const cur = CAPST.get(c.id);
    const log = c.milestones.map((m, i) => { const s = cur.ms[m.id] || {}; return `${i + 1}. ${m.title}：${s.done ? "已完成" : "未完成"}；验收 ${(s.checks || []).filter(Boolean).length}/${m.acceptance.length}${s.review ? `；AI 评审 ${s.review.score} 分，缺：${s.review.gaps.slice(0, 2).join("；")}` : ""}\n   记录：${clip(s.notes || "（没写）", 600)}`; }).join("\n");
    gen.disabled = true; status.textContent = "AI 在整理……（大约 30–60 秒）";
    try {
      const r = await AI.ask(`根据候选人完成「${c.title}」（${c.role} 方向）项目的记录，写简历和面试材料。只能用候选人记录里的事实和数据，缺数据的地方写成【待补充：应该补什么数据】，不要编造数字。
【项目说明】${c.summary}\n${c.why}\n技术栈：${(c.stack || []).join("、")}
【各里程碑情况】
${log}
【候选人填写的关键数据】
${clip(metrics.value, 3000) || "（没填）"}
只返回 JSON：{"title": "简历上的项目名", "oneliner": "一句话介绍", "bullets": ["3–5 条简历描述：动词开头，讲清做了什么、怎么做的、效果数据"], "pitch": "2 分钟口语化项目介绍", "star": {"S": "", "T": "", "A": "", "R": ""}, "deep": [{"q": "面试官最可能深挖的问题（5–8 个）", "a": "回答要点，引用候选人的真实设计和数据"}], "card": {"name": "", "background": "", "role": "", "actions": "", "results": "", "tradeoffs": "", "validation": "", "reflection": ""}}`, { json: true, tier: "complex" });
      const o = { title: String(r.title || c.title), oneliner: String(r.oneliner || ""), bullets: arrStr(r.bullets, 6), pitch: String(r.pitch || ""), star: Object.assign({ S: "", T: "", A: "", R: "" }, r.star || {}), deep: (Array.isArray(r.deep) ? r.deep : []).slice(0, 8).map(x => ({ q: String((x && x.q) || ""), a: String((x && x.a) || "") })), card: r.card && typeof r.card === "object" ? Object.fromEntries(CARD_FIELDS.map(([k]) => [k, String(r.card[k] || "")])) : null };
      const now = CAPST.get(c.id); now.out = o; CAPST.set(c.id, now);
      draw(o); status.textContent = "";
    } catch (e) { status.textContent = e && e.code ? aiErr(e) : "生成失败：" + ((e && e.message) || e); }
    finally { gen.disabled = false; }
  });
  return h("section", { class: "panel" }, h("h2", null, "整理成简历和面试故事"),
    h("p", { class: "small muted" }, "建议全部里程碑完成、每一步都写了记录之后再生成。只会用你记录里的事实；缺数据的地方会标【待补充】。"),
    metrics, h("div", { class: "row" }, gen, status), outBox);
}
