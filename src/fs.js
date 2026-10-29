// ---------- 全栈：排障演练 / SQL 专项 / 技术选型 / 代码评审 / 语言专项 / 前端手写 / 简历 × JD ----------
const FSD = JSON.parse(document.getElementById("fs-data").textContent || "{}");
const FS_JS = (document.getElementById("fsjs-src") || {}).textContent || "";
const fsCases = () => FSD.cases || [], fsSQL = () => FSD.sql || { datasets: {}, queries: [], index: [], schema: [] };
const fsTech = () => FSD.tech || { cards: [], scenarios: [] }, fsReviews = () => FSD.reviews || [], fsLang = () => FSD.lang || [], fsHand = () => FSD.hand || [];
const FS = {
  get() { return LS.get("tiyan:fs", {}); },
  at(path) { let o = this.get(); for (const k of path) { o = o && o[k]; } return o; },
  patch(path, val) { const a = this.get(); let o = a; for (const k of path.slice(0, -1)) o = o[k] = o[k] || {}; o[path[path.length - 1]] = val; LS.set("tiyan:fs", a); },
};
// AI 请求在后台跑，结果写进本地记录；离开页面不中断，回来接着显示
const FS_JOBS = {};
let FS_REDRAW = null;
function fsJob(key, prompt, path, tier) {
  if (FS_JOBS[key]) return;
  if (!AI.ok()) { toast(aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" })); if (S.ai === "needkey") openKeyDialog(); return; }
  FS_JOBS[key] = true;
  FS.patch(path.concat("err"), "");
  if (FS_REDRAW) FS_REDRAW();
  AI.ask(prompt, { json: true, tier: tier || "default" })
    .then(r => FS.patch(path.concat("ev"), r))
    .catch(e => FS.patch(path.concat("err"), e && e.code ? aiErr(e) : "评估失败：" + ((e && e.message) || e)))
    .finally(() => { delete FS_JOBS[key]; if (FS_REDRAW) FS_REDRAW(); });
}
function fsLive(box, draw) {
  FS_REDRAW = () => {
    const ae = document.activeElement, id = ae && box.contains(ae) && ae.id;
    const a = id && ae.selectionStart, b = id && ae.selectionEnd, y = window.scrollY;
    draw();
    window.scrollTo(0, y);
    if (id) { const n = document.getElementById(id); if (n) { n.focus({ preventScroll: true }); try { n.setSelectionRange(a, b); } catch (e) { /* 不支持选区 */ } } }
  };
  onLeave(() => { FS_REDRAW = null; });
}
// 小眼在全栈页的上下文
function fsProvide(where, ctx, actions) {
  Buddy.provide({ where: () => "全栈 › " + where, context: () => BUDDY_SYS.split("\n")[0] + "\n现在学习者在「全栈工程师」模块练习：" + where + "\n\n" + ctx(), actions });
  onLeave(() => Buddy.provide(null));
}
const fsPending = t => h("div", { class: "thinking" }, t || "AI 在看你的答案……（大约 15–40 秒，可以先做别的）");
const fsErr = (msg, retry) => h("div", { class: "row" }, h("span", { class: "small", style: "color:var(--red)" }, msg), h("button", { class: "btn sm", type: "button", onclick: retry }, "重试"));
function fsEvalBox(rec, key, retry, render) {
  const box = h("div", { class: "stack sd-ai" });
  if (FS_JOBS[key]) box.append(fsPending());
  else if (rec && rec.err) box.append(fsErr(rec.err, retry));
  else if (rec && rec.ev) render(box, rec.ev);
  return box;
}
const fsTa = (id, val, onInput, rows, cls) => { const t = h("textarea", { class: "mock-input " + (cls || ""), id, style: `min-height:${rows || 90}px`, spellcheck: "false" }); t.value = val || ""; t.addEventListener("input", () => onInput(t.value)); return t; };
const fsVoice = t => { const vb = h("button", { class: "btn ghost sm", type: "button", hidden: !SpeechRec }, "语音输入"); const vs = h("span", { class: "small muted" }); vb.addEventListener("click", () => toggleVoice(t, vb, vs)); return [vb, vs]; };
const FS_TABS = [["fs", "总览"], ["fs-trouble", "排障演练"], ["fs-sql", "SQL 专项"], ["fs-tech", "技术选型"], ["sd-sys", "方案设计 ↗"], ["fs-review", "代码评审"], ["fs-lang", "语言专项"], ["fs-hand", "前端手写"], ["fs-jd", "简历 × JD 出题"]];
function fsPage(cur, title, lede, ...body) {
  return h("div", { class: "page wide fs-page" }, h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "全栈工程师"), h("h1", null, title), lede ? h("p", { class: "lede" }, lede) : ""),
    h("nav", { class: "page-tabs" }, FS_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t))), ...body);
}
function viewFS({ sub }) {
  if (!fsCases().length && !fsSQL().queries.length) return h("div", { class: "page" }, h("h1", null, "全栈工程师"), h("p", { class: "muted" }, "内容还在准备中，稍后刷新再来。"));
  const one = (pre, list, fn) => { const m = new RegExp("^" + pre + "(\\d+)$").exec(sub || ""); const x = m && list.find(y => y.id === pre + m[1]); return x ? fn(x) : null; };
  if (sub === "trouble") return fsTroubleList();
  if (sub === "sql") return fsSQLList();
  if (sub === "tech") return fsTechList();
  if (sub === "review") return fsReviewList();
  if (sub === "lang") return fsLangView();
  if (sub === "hand") return fsHandList();
  if (sub === "jd") return fsJD();
  if (sub && sub.startsWith("k-")) { const c = fsTech().cards.find(x => x.id === sub.slice(2)); if (c) return fsCardView(c); }
  return one("t", fsCases(), fsCaseView) || one("q", fsSQL().queries, fsQueryView) || one("i", fsSQL().index, fsIndexView) || one("s", fsSQL().schema, fsSchemaView)
    || one("c", fsTech().scenarios, fsScenarioView) || one("r", fsReviews(), fsReviewView) || one("h", fsHand(), fsHandView) || fsOverview();
}

// ----- 总览：按 JD 拆出来的能力地图 -----
function fsOverview() {
  fsProvide("总览", () => "这是能力地图页。", null);
  const st = FS.get(), cnt = (k, arr, ok) => arr.filter(x => ok(((st[k] || {})[x.id]) || null)).length;
  const sql = fsSQL(), tech = fsTech(), lang = fsLang();
  const langDone = tr => lang.filter(x => x.track === tr && ((st.l || {})[x.id] || {}).ok).length;
  const sys = (SDD.systems || []);
  const areas = [
    ["fs-trouble", "排障演练", "线上出事了：先止血、再定位。选择排查动作（每个动作耗时），看监控 / 日志 / trace / 慢查询，写出根因、修复和预防。", cnt("t", fsCases(), r => r && r.ev), fsCases().length],
    ["fs-sql", "SQL 专项", "在真实数据上写查询（自动判对错）、给慢查询建索引（看执行计划）、按需求设计表。", cnt("q", sql.queries, r => r && r.ok) + cnt("i", sql.index, r => r && r.ok) + cnt("s", sql.schema, r => r && r.ev), sql.queries.length + sql.index.length + sql.schema.length],
    ["fs-tech", "技术选型", "Redis、MQ、ES、ClickHouse、React / Vue、SSR……每项的优缺点和适用边界；按场景用五句话做选型。", cnt("c", tech.scenarios, r => r && r.ev), tech.scenarios.length],
    ["sd-sys", "方案设计", "给一个需求：要加哪些服务、哪些组件（缓存、队列、数据库）、表怎么设计、流程怎么走、挂了怎么办。", sys.filter(x => (SYS.get(x.id).hist || []).length).length, sys.length],
    ["fs-review", "代码评审", "看一段能跑但有坑的代码：竞态、泄漏、注入、事务失效、N+1……写评审意见，AI 对照参考判你找到了几个。", cnt("r", fsReviews(), r => r && r.ev), fsReviews().length],
    ["fs-lang", "前端语言", "JS / TS / React / Vue / CSS / 浏览器 / 工程化：说输出、选择、简答。", langDone("前端"), lang.filter(x => x.track === "前端").length, "前端"],
    ["fs-lang", "后端语言", "Go / Java / Python / RESTful / 数据库 / Linux：说输出的题都真的运行过。", langDone("后端"), lang.filter(x => x.track === "后端").length, "后端"],
    ["fs-hand", "前端手写", "防抖节流、深拷贝、Promise 并发池、EventEmitter、LRU……在浏览器里跑测试。", cnt("h", fsHand(), r => r && r.pass), fsHand().length],
    ["fs-jd", "简历 × JD 出题", "贴上目标岗位 JD，结合你的简历：逐条看匹配度和缺口，生成一套会被问到的题，答完 AI 打分。", ((st.jd || {}).ev ? 1 : 0), 1],
  ];
  return fsPage("fs", "全栈面试：前端 + 后端 + 数据库 + 架构 + 排障 + 代码质量", "大多数全栈 JD 要的是同一组能力：至少一门前端框架和一门后端语言写得熟；会设计表、写 SQL；给一个需求能拆出服务和组件，并说清技术选型的取舍；线上出问题知道怎么排查；看代码能判断好坏。下面每一块都能单独练，AI 会逐题点评。",
    h("div", { class: "hubs" }, areas.map(([href, t, d, done, total, track]) => h("a", { class: "panel hub", href: "#" + href, onclick: () => { if (track) LS.set("tiyan:fs:langf", { track, langs: [], kind: "" }); } },
      h("h2", null, t), h("p", { class: "small muted" }, d), h("div", { class: "bar", style: "margin-top:auto" }, h("i", { style: `width:${total ? done / total * 100 : 0}%` })), h("div", { class: "small faint num" }, `已完成 ${done} / ${total}`)))),
    h("section", { class: "panel" }, h("h2", null, "两周节奏建议"), h("ol", { class: "steps" },
      h("li", null, h("b", { class: "num" }, 1), h("span", null, "每天：1 个排障案例 + 3 道 SQL + 1 道代码评审 + 10 道语言题（前后端交替）。")),
      h("li", null, h("b", { class: "num" }, 2), h("span", null, "隔天：1 道技术选型场景（五句话答完再看参考）+ 2 道前端手写。")),
      h("li", null, h("b", { class: "num" }, 3), h("span", null, "每周：2 道方案设计（服务 / 组件 / 表 / 流程完整写一遍）+ 用「简历 × JD」出一套题，再去模拟面试实战一轮。")),
      h("li", null, h("b", { class: "num" }, 4), h("span", null, "卡住就选中文字问右下角的小眼，或者截图给它。")))));
}

// ----- 排障演练 -----
const FS_KIND = { metric: "监控", log: "日志", trace: "链路", sql: "数据库", code: "代码", config: "配置", cmd: "命令", change: "变更", frontend: "前端", ask: "问人" };
function fsTroubleList() {
  fsProvide("排障演练列表", () => "学习者在选排障案例。", null);
  const st = FS.get().t || {}, by = {};
  for (const c of fsCases()) (by[c.area] = by[c.area] || []).push(c);
  return fsPage("fs-trouble", "排障演练：先止血，再定位", "每个案例是一场模拟故障：你只看到告警和系统背景，自己决定先看什么（每个动作都会耗时，算进故障时长），最后写出止血、根因、修复和预防。AI 会评你的结论和排查路径。",
    h("section", { class: "panel" }, h("h2", null, "排查的基本顺序"), h("ol", { class: "steps" },
      h("li", null, h("b", { class: "num" }, 1), h("span", null, "先确认影响面和时间点：哪些接口 / 页面、多少用户、从几点开始；同时想好止血手段（回滚、限流、降级、扩容、切流）。")),
      h("li", null, h("b", { class: "num" }, 2), h("span", null, "先看最近变更：发布、配置、数据迁移、流量活动——大部分故障都和变更有关。")),
      h("li", null, h("b", { class: "num" }, 3), h("span", null, "看大盘再下钻：流量 / 错误率 / 延迟（RED），资源的使用率 / 饱和度 / 错误（USE），再到具体实例、日志、trace、慢查询。")),
      h("li", null, h("b", { class: "num" }, 4), h("span", null, "提出假设并用证据验证，不要被同时段的无关告警带偏；定位后保留现场，复盘写 5 Whys 和改进项。")))),
    ...Object.entries(by).map(([area, list]) => h("section", { class: "stack" }, h("h2", null, area),
      h("div", { class: "hubs" }, list.map(c => { const r = st[c.id] || {}; return h("a", { class: "panel hub", href: "#fs-" + c.id }, h("div", { class: "eyebrow" }, c.level), h("h2", null, c.title), h("p", { class: "small muted" }, clip(c.symptom, 70)),
        h("div", { class: "small faint num" }, r.ev ? `已复盘 · ${r.ev.score} 分` : (r.opened || []).length ? "排查中" : "未开始")); })))));
}
function fsCaseView(c) {
  const box = h("div", { class: "stack" }), side = h("aside", { class: "panel sd-side" });
  const path = ["t", c.id], jk = "t:" + c.id;
  fsProvide(`排障 · ${c.title}`, () => {
    const r = FS.at(path) || {};
    const seen = (r.opened || []).map(k => c.checks.find(x => x.key === k)).filter(Boolean);
    return `【故障现象】${c.symptom}\n【系统背景】${c.context}\n【他已经看过的排查结果】\n${seen.map(x => `- ${x.label}：\n${clip(x.content, 800)}`).join("\n") || "（还没开始排查）"}\n【他的推理笔记】${(r.a || {}).notes || "（空）"}\n`
      + (r.ev ? `【参考根因】${c.root_cause}\n【参考修复】${c.fix}` : "【重要】他还没提交结论：不要直接说出根因或修复方案。像带教的老同事一样，引导他想清楚下一步该看什么、为什么、怎么验证假设；可以指出他推理里的漏洞。");
  }, [{ label: "我该先看什么", run: ch => ch.send("我现在该先看什么？按优先级给我 2–3 个方向和理由，不要直接告诉我根因。", { label: "我该先看什么" }) },
    { label: "帮我检查推理", run: ch => ch.send("看看我目前看过的证据和推理笔记，推理有没有漏洞、有没有被干扰信息带偏？不要直接说根因。", { label: "帮我检查推理" }) },
    { label: "教我排查方法", run: ch => ch.send("这类故障一般怎么系统地排查？给我一个可复用的排查清单（先止血还是先定位、看哪些指标、用哪些命令 / 工具）。", { label: "教我排查方法" }) }]);
  const draw = () => {
    const r = FS.at(path) || {}, a = r.a || {}, opened = r.opened || [];
    box.textContent = ""; side.textContent = "";
    const cost = opened.reduce((n, k) => n + ((c.checks.find(x => x.key === k) || {}).cost || 0), 0);
    const done = !!r.ev || r.peek;
    side.append(h("div", { class: "eyebrow" }, "模拟故障时长"), h("div", { class: "fs-mttr num" + (cost > 30 ? " over" : "") }, `${cost} 分钟`),
      h("p", { class: "small muted" }, `已执行 ${opened.length} 个排查动作。动作越准，故障时长越短。`),
      done ? h("div", { class: "small" }, `关键线索看了 ${c.checks.filter(x => x.value === 2 && opened.includes(x.key)).length} / ${c.checks.filter(x => x.value === 2).length}，干扰项看了 ${c.checks.filter(x => x.value === 0 && opened.includes(x.key)).length} 个`) : "",
      (() => { const b = h("button", { class: "btn ghost sm", type: "button" }, "重新开始这个案例"); b.addEventListener("click", () => { if (b.dataset.sure) { FS.patch(path, {}); draw(); window.scrollTo(0, 0); } else { b.dataset.sure = "1"; b.textContent = "再点一次确认重来"; } }); return b; })(),
      h("a", { class: "btn ghost sm", href: "#fs-trouble" }, "← 全部案例"));
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, h("span", { class: "pill trying" }, c.area), h("span", { class: "pill todo" }, c.level)),
      h("div", { class: "callout" }, h("b", null, "告警 / 现象　"), mdEl(c.symptom)), h("h3", null, "系统背景"), mdEl(c.context, "small")));
    // 排查动作
    box.append(h("section", { class: "panel" }, h("div", { class: "spread" }, h("h2", null, "排查动作"), h("span", { class: "small faint" }, "点一个就执行一个（括号里是耗时）")),
      h("div", { class: "fs-checks" }, c.checks.map(x => { const on = opened.includes(x.key); return h("button", { type: "button", class: "fs-check" + (on ? " on" : ""), disabled: on, onclick: () => { FS.patch(path.concat("opened"), opened.concat([x.key])); if (!r.t0) FS.patch(path.concat("t0"), Date.now()); draw(); setTimeout(() => { const n = document.getElementById("ev-" + x.key); if (n) n.scrollIntoView({ behavior: "smooth", block: "center" }); }, 30); } },
        h("span", { class: "fs-kind" }, FS_KIND[x.kind] || x.kind), h("span", null, x.label), h("small", { class: "num" }, `${x.cost} 分钟`), on ? h("span", { class: "sd-ok" }, "✓") : ""); }))));
    if (opened.length) {
      let t = 0;
      box.append(h("section", { class: "panel" }, h("h2", null, "排查记录"), h("div", { class: "fs-timeline" }, opened.map(k => { const x = c.checks.find(y => y.key === k); if (!x) return ""; t += x.cost;
        return h("div", { class: "fs-ev", id: "ev-" + k }, h("div", { class: "row" }, h("span", { class: "num small faint" }, `T+${t}′`), h("span", { class: "fs-kind" }, FS_KIND[x.kind] || x.kind), h("b", null, x.label),
          done ? h("span", { class: "pill " + (x.value === 2 ? "passed" : x.value === 1 ? "master" : "todo") }, x.value === 2 ? "关键线索" : x.value === 1 ? "有帮助" : "干扰项") : ""), mdEl(x.content, "small")); }))));
    }
    // 结论
    const F = [["notes", "推理过程 / 假设", "看到了什么 → 怀疑什么 → 怎么验证的"], ["stop", "止血措施", "先恢复服务：回滚、限流、降级、扩容、切流……"], ["root", "根因", "具体到代码 / 配置 / 数据"], ["fix", "根本修复", ""], ["prevent", "预防与改进", "监控告警、压测、规范、发布流程"]];
    const tas = F.map(([k, t, ph]) => { const el = fsTa(`fs-${c.id}-${k}`, a[k], v => FS.patch(path.concat("a", k), v), k === "notes" ? 90 : 64); el.placeholder = ph; return [k, t, el]; });
    const ask = () => {
      const now = FS.at(path) || {}, A = now.a || {}, op = now.opened || [];
      if (!(A.root || "").trim()) { toast("至少写一下你认为的根因"); return; }
      fsJob(jk, `你是资深 SRE / 后端负责人，在评一位工程师处理线上故障的表现（模拟演练）。
${SD_COACH_RULE}
【故障现象】${c.symptom}
【系统背景】${clip(c.context, 1500)}
【全部排查动作（value：2 关键线索 / 1 有帮助 / 0 干扰项）】\n${c.checks.map(x => `- ${x.key}（${x.label}，耗时 ${x.cost} 分钟，value=${x.value}）`).join("\n")}
【理想排查路径】${c.ideal_path.join(" → ")}
【参考根因】${c.root_cause}\n【参考止血】${c.stop_bleeding}\n【参考修复】${c.fix}\n【参考预防】${c.prevention}
【常见误判】${c.traps.join("；")}
【得分点】${c.points.join("；")}
【他的排查顺序】${op.join(" → ") || "（什么都没看）"}（模拟耗时 ${op.reduce((n, k) => n + ((c.checks.find(x => x.key === k) || {}).cost || 0), 0)} 分钟）
【他的结论】\n推理：${A.notes || "（空）"}\n止血：${A.stop || "（空）"}\n根因：${A.root || "（空）"}\n修复：${A.fix || "（空）"}\n预防：${A.prevent || "（空）"}
评分：根因找对且证据链完整、先止血、修复和预防到位、路径高效 → 9–10；根因对但止血或预防缺失 → 7–8.5；只找到表层原因（比如“数据库慢”但没说为什么）→ 5–6.5；被干扰项带偏 → 3–4.5。
只返回 JSON：{"score": 6.5, "verdict": "一句话", "found_root": true, "items": [{"you": "他的某个结论 / 动作", "verdict": "对|方向对但不准|有错|搞反|缺失|最大扣分点", "why": "说明"}], "path": {"comment": "排查路径评价：顺序是否合理、哪些动作多余、哪个关键线索没看", "wasted": ["多余的动作 label"], "missed": ["没看的关键线索 label"]}, "stop_bleeding": "止血措施评价", "missed": ["结论里漏掉的得分点"], ${SD_COACH_JSON}}`, path);
    };
    const evBox = fsEvalBox(r, jk, ask, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, h("span", { class: "small" }, (ev.found_root ? "✓ 找到根因　" : "✗ 没找到根因　") + (ev.verdict || ""))),
      verdictTable(ev.items), ev.path ? h("div", { class: "callout blue" }, h("b", null, "排查路径　"), String(ev.path.comment || ""), arrStr(ev.path.missed, 5).length ? h("div", { class: "small" }, "没看的关键线索：" + arrStr(ev.path.missed, 5).join("、")) : "", arrStr(ev.path.wasted, 5).length ? h("div", { class: "small" }, "多余的动作：" + arrStr(ev.path.wasted, 5).join("、")) : "") : "",
      ev.stop_bleeding ? h("p", { class: "small" }, h("b", null, "止血："), String(ev.stop_bleeding)) : "", arrStr(ev.missed, 6).length ? h("div", null, h("h3", null, "漏掉的得分点"), sdList(arrStr(ev.missed, 6))) : "", coachEl(ev)));
    const ref = done ? h("section", { class: "panel" }, h("h2", null, "参考答案与复盘"),
      h("div", { class: "fs-ref-grid" }, [["止血", c.stop_bleeding], ["根因", c.root_cause], ["根本修复", c.fix], ["预防", c.prevention]].map(([t, v]) => h("div", { class: "sd-ref" }, h("div", { class: "eyebrow" }, t), mdEl(v, "small")))),
      h("div", null, h("h3", null, "理想排查路径"), h("ol", { class: "mock-ul" }, c.ideal_path.map(k => { const x = c.checks.find(y => y.key === k); return h("li", { class: opened.includes(k) ? "sd-ok" : "" }, (x ? x.label : k) + (opened.includes(k) ? " ✓" : "（你没看）")); }))),
      h("div", null, h("h3", null, "常见误判"), sdList(c.traps)),
      h("details", { class: "qa" }, h("summary", null, "复盘报告范文"), mdEl(c.report, "small")),
      h("details", { class: "qa sd-sec" }, h("summary", null, `面试追问（${c.followups.length}）`), ...c.followups.map(f => { const e = h("details", { class: "qa" }, h("summary", null, f.q)); e.append(mdEl(f.a, "small")); return e; }))) : "";
    box.append(h("section", { class: "panel" }, h("h2", null, "写结论"), h("div", { class: "fs-ans" }, tas.map(([k, t, el]) => h("label", { class: "card-f" + (k === "notes" ? " wide" : "") }, h("b", null, t), el))),
      h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!FS_JOBS[jk], onclick: ask }, r.ev ? "改完了，重新评估" : "提交结论，让 AI 复盘"),
        !done ? h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); draw(); } }, "放弃，直接看答案") : ""), evBox), ref);
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-trouble", c.title, null, h("div", { class: "sd-grid" }, box, side));
}

// ----- SQL 专项：查询（结果集比对）/ 索引（执行计划）/ 建表（检查 + AI 评审） -----
async function fsPy(fn, args, timeout) {
  if (!Py.loaded.has("sqlite3")) await Py.loadPackage("sqlite3");
  return Py.json(fn, args, timeout || 15000);
}
const FS_PEEK = {}, FS_LAST = {};   // 数据集预览、最近一次运行结果（只在内存里，刷新后重新运行）
function fsDataset(did) {
  const ds = fsSQL().datasets[did];
  if (!ds) return "";
  const body = h("div", { class: "stack", style: "gap:8px" });
  const d = h("details", { class: "qa" }, h("summary", null, `数据集：${ds.title}（点开看表结构和样例数据）`), mdEl(ds.desc, "small"), body);
  d.addEventListener("toggle", async () => {
    if (!d.open || body.childNodes.length) return;
    body.append(h("div", { class: "thinking" }, S.py === "ready" ? "读取数据中……" : "Python 运行环境加载中……"));
    try {
      const r = FS_PEEK[did] || (FS_PEEK[did] = await fsPy("sql_peek", [ds.ddl, ds.seed]));
      body.textContent = "";
      if (!r.ok) { body.textContent = r.error; return; }
      for (const t of r.tables) body.append(h("div", null, h("div", { class: "small" }, h("b", { class: "mono" }, t.name), h("span", { class: "faint" }, `　${t.count} 行　`), h("span", { class: "mono faint" }, t.cols.join(", "))), fsTable(t.cols.map(c => c.split(" ")[0]), t.rows, 5)));
    } catch (e) { body.textContent = "读取失败：" + ((e && e.message) || e); }
  });
  return d;
}
function fsTable(cols, rows, max) {
  const fmt = v => v == null ? h("span", { class: "faint" }, "NULL") : typeof v === "number" && !Number.isInteger(v) ? String(Math.round(v * 10000) / 10000) : String(v);
  return h("div", { class: "scroll-x" }, h("table", { class: "ptable fs-res" }, h("thead", null, h("tr", null, cols.map(c => h("th", null, c)))), h("tbody", null, rows.slice(0, max || 50).map(r => h("tr", null, r.map(v => h("td", null, fmt(v))))))));
}
function fsCode(id, val, onInput, mode, rows) {
  const ta = fsTa(id, val, onInput, rows || 140, "mono sd-code");
  ta.addEventListener("keydown", e => { if (e.key === "Tab" && !e.shiftKey) { e.preventDefault(); const s = ta.selectionStart; ta.setRangeText("  ", s, ta.selectionEnd, "end"); onInput(ta.value); } });
  return ta;
}
function fsSQLList() {
  fsProvide("SQL 专项", () => "学习者在选 SQL 题。", null);
  const sql = fsSQL(), st = FS.get();
  const tab = LS.get("tiyan:fs:sqltab", "q");
  const seg = h("div", { class: "seg" }, [["q", `查询题 ${sql.queries.length}`], ["i", `索引优化 ${sql.index.length}`], ["s", `建表设计 ${sql.schema.length}`]].map(([k, t]) => h("button", { type: "button", class: k === tab ? "on" : "", onclick: () => { LS.set("tiyan:fs:sqltab", k); go("fs-sql"); } }, t)));
  const list = tab === "q" ? sql.queries : tab === "i" ? sql.index : sql.schema;
  const mark = x => { const r = (st[tab] || {})[x.id]; return !r ? h("span", { class: "faint" }, "—") : tab === "s" ? (r.ev ? h("span", { class: "num" }, r.ev.score) : "写过") : r.ok ? h("span", { class: "sd-ok" }, "✓") : h("span", { class: "sd-bad" }, `试了 ${r.tries || 0} 次`); };
  return fsPage("fs-sql", "SQL 专项：写查询、建索引、设计表", "查询题在真实数据上运行，结果和参考答案比对（列名不比，值和行数要一致；题目要求排序的话顺序也要一致）。索引题看执行计划有没有从全表扫描变成走索引。建表题用 SQLite 当场检查，AI 对照参考评审。",
    h("section", { class: "panel" }, h("div", { class: "spread" }, seg, h("span", { class: "small faint" }, `“今天”按 ${FSD.today || "2026-06-30"} 算`)),
      h("p", { class: "small muted" }, "在浏览器里用 SQLite 运行。常用 MySQL 函数已经兼容：IF、DATE_FORMAT、DATEDIFF、NOW、CURDATE、CONCAT、CONCAT_WS、LEFT、RIGHT、GREATEST、LEAST、UNIX_TIMESTAMP、FROM_UNIXTIME、YEAR / MONTH / DAY。注意两点：不支持 INTERVAL（用 date(d, '+1 day')）；整数相除是整除，算比例写 1.0 * a / b。"),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("thead", null, h("tr", null, ["", "题目", tab === "q" ? "考点" : "数据集", "难度", "状态"].map(x => h("th", null, x)))),
        h("tbody", null, list.map(x => h("tr", { class: "sd-row", onclick: () => go("fs-" + x.id) }, h("td", { class: "mono" }, x.id.toUpperCase()), h("td", null, h("a", { href: "#fs-" + x.id }, x.title)), h("td", { class: "muted small" }, x.topic || (fsSQL().datasets[x.dataset] || {}).title || ""), h("td", { class: "small" }, x.level || ""), h("td", { class: "num small" }, mark(x)))))))));
}
function fsQueryView(q) {
  const box = h("div", { class: "stack" }), path = ["q", q.id], jk = "q:" + q.id;
  const ds = fsSQL().datasets[q.dataset];
  fsProvide(`SQL · ${q.title}`, () => { const r = FS.at(path) || {}; return `【SQL 题】${q.question}\n【数据集】${ds.title}：${clip(ds.desc, 800)}\n【表结构】\n${clip(ds.ddl, 2500)}\n【他的 SQL】\n${r.sql || "（还没写）"}\n${r.last ? "【最近一次运行】" + (r.last.error || (r.last.match ? "结果正确" : "结果不对：" + r.last.hint)) : ""}\n${r.peek || r.ok ? "【参考答案】\n" + q.answer : "【重要】他还没做对：不要直接给出完整答案 SQL，先提示思路。"}`; },
    [{ label: "给我提示", run: ch => ch.send("这道 SQL 题我卡住了，给我一个思路提示（用到什么子句 / 函数、分几步），不要直接写完整答案。", { label: "给我提示" }) },
     { label: "我的 SQL 哪里错了", run: ch => ch.send("看看我写的 SQL 和运行结果，哪里错了？指出具体的子句和原因，先别给完整答案。", { label: "我的 SQL 哪里错了" }) },
     { label: "讲讲这类题", run: ch => ch.send("这类 SQL 题（" + q.topic + "）面试里常见的变体有哪些？通用写法和最容易错的地方是什么？", { label: "讲讲这类题" }) }]);
  const draw = () => {
    const r = FS.at(path) || {};
    box.textContent = "";
    const out = h("div", { class: "stack" });
    const ed = fsCode(`fs-${q.id}-sql`, r.sql, v => FS.patch(path.concat("sql"), v), "sql", 150);
    ed.placeholder = "SELECT ...（Ctrl / ⌘ + Enter 运行）";
    const showRes = res => {
      out.textContent = "";
      if (!res) return;
      if (res.error) { out.append(h("div", { class: "callout" }, h("b", null, "运行出错　"), res.error)); return; }
      out.append(h("div", { class: "row" }, res.match ? h("span", { class: "pill passed" }, "✓ 结果正确") : h("span", { class: "pill due" }, "✗ " + (res.hint || "结果不对")), h("span", { class: "small faint num" }, `返回 ${res.total} 行 · ${res.ms} ms`)), fsTable(res.columns, res.rows));
      if (!res.match && ((FS.at(path) || {}).tries || 0) >= 2) {
        const d = h("details", { class: "qa" }, h("summary", null, "看期望的结果（不看 SQL）"), h("div", { class: "small faint" }, `期望 ${res.ref_total} 行`), fsTable(res.ref_columns, res.ref_rows));
        out.append(d);
      }
    };
    const run = async () => {
      if (!ed.value.trim()) { toast("先写 SQL"); return; }
      out.textContent = ""; out.append(h("div", { class: "thinking" }, S.py === "ready" ? "运行中……" : "Python 运行环境加载中……"));
      try {
        const res = await fsPy("run_sql", [ds.ddl, ds.seed, ed.value, q.answer, !!q.ordered]);
        const cur = FS.at(path) || {};
        FS.patch(path, Object.assign({}, cur, { sql: ed.value, tries: (cur.tries || 0) + 1, ok: cur.ok || !!res.match, last: { error: res.error || "", match: !!res.match, hint: res.hint || "" } }));
        FS_LAST[q.id] = res;
        showRes(res);
      } catch (e) { out.textContent = "运行失败：" + ((e && e.message) || e); }
    };
    ed.addEventListener("keydown", e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); run(); } });
    const askAI = () => {
      const now = FS.at(path) || {};
      if (!(now.sql || "").trim()) { toast("先写 SQL"); return; }
      fsJob(jk, `你是资深后端 / 数据库工程师，在点评一道 SQL 面试题的答案。
${SD_COACH_RULE}
【题目】${q.question}
【表结构】\n${clip(ds.ddl, 3000)}
【参考答案】\n${q.answer}
【讲解】${q.explain}
【他的 SQL】\n${now.sql}
【运行结果】${now.last ? (now.last.error ? "报错：" + now.last.error : now.last.match ? "和参考结果一致" : "和参考结果不一致：" + now.last.hint) : "还没运行"}
从正确性（边界：NULL、重复、并列、空结果）、性能（大表下会不会全表扫描、能不能用索引、子查询 vs JOIN）、可读性、MySQL 8 和 SQLite 写法差异四个角度点评。结果正确但写法差也要指出。
只返回 JSON：{"score": 7, "verdict": "一句话", "items": [{"you": "他写法的某一点", "verdict": "对|方向对但不准|有错|搞反|缺失|最大扣分点", "why": "说明"}], "better": "更好的写法（SQL，可带注释）", ${SD_COACH_JSON}}`, path);
    };
    const evBox = fsEvalBox(r, jk, askAI, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""), verdictTable(ev.items), ev.better ? h("details", { class: "qa", open: true }, h("summary", null, "更好的写法"), h("pre", { class: "sd-pre" }, String(ev.better))) : "", coachEl(ev)));
    const ans = r.peek ? h("section", { class: "panel" }, h("h2", null, "参考答案"), h("pre", { class: "sd-pre" }, q.answer), mdEl(q.explain, "small"), h("h3", null, "常见错误"), sdList(q.pitfalls)) : "";
    const hint = h("div", { class: "hint-ladder" });
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, h("span", { class: "pill todo" }, q.level), h("span", { class: "pill trying" }, q.topic), q.ordered ? h("span", { class: "small faint" }, "这题要求排序") : ""),
      mdEl(q.question), fsDataset(q.dataset)),
      h("section", { class: "panel" }, ed, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: run }, "运行并判题"), h("button", { class: "btn sm", type: "button", disabled: !!FS_JOBS[jk], onclick: askAI }, "让 AI 点评写法"),
        h("button", { class: "btn ghost sm", type: "button", onclick: () => { hint.textContent = ""; hint.append(h("div", { class: "hint" }, h("b", null, "提示"), q.hint)); } }, "提示"),
        h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); draw(); } }, "看答案"), r.ok ? h("span", { class: "sd-ok small" }, "✓ 已做对") : ""), hint, out, evBox), ans,
      fsNav(fsSQL().queries, q.id));
    if (FS_LAST[q.id]) showRes(FS_LAST[q.id]);
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-sql", `${q.id.toUpperCase()} ${q.title}`, null, box);
}
function fsNav(list, id) {
  const i = list.findIndex(x => x.id === id), p = list[i - 1], n = list[i + 1];
  return h("div", { class: "spread" }, p ? h("a", { class: "btn ghost sm", href: "#fs-" + p.id }, "← " + clip(p.title, 16)) : h("span"), n ? h("a", { class: "btn sm", href: "#fs-" + n.id }, clip(n.title, 16) + " →") : h("span"));
}
function fsPlan(lines) { return h("pre", { class: "sd-pre" }, (lines || []).join("\n") || "（空）"); }
function fsIndexView(x) {
  const box = h("div", { class: "stack" }), path = ["i", x.id], jk = "i:" + x.id;
  const ds = fsSQL().datasets[x.dataset];
  fsProvide(`索引 · ${x.title}`, () => { const r = FS.at(path) || {}; return `【索引题】${x.question}\n【目标查询】${x.query}\n【表结构】\n${clip(ds.ddl, 2500)}\n【他的索引】${r.sql || "（还没写）"}\n${r.peek || r.ok ? "【参考】" + x.answer : "【重要】先引导，不要直接给出索引语句。"}`; }, null);
  const draw = () => {
    const r = FS.at(path) || {};
    box.textContent = "";
    const before = h("div", null, h("div", { class: "thinking" }, "读取执行计划……"));
    fsPy("run_index", [ds.ddl, ds.seed, "", x.query, x.table]).then(p => { before.textContent = ""; before.append(p.ok ? fsPlan(p.before) : h("span", null, p.error)); }).catch(e => { before.textContent = String(e && e.message || e); });
    const ed = fsCode(`fs-${x.id}-sql`, r.sql, v => FS.patch(path.concat("sql"), v), "sql", 90);
    ed.placeholder = "CREATE INDEX idx_xxx ON 表(列1, 列2);";
    const out = h("div", { class: "stack" });
    const run = async () => {
      out.textContent = ""; out.append(h("div", { class: "thinking" }, "建索引并看执行计划……"));
      try {
        const p = await fsPy("run_index", [ds.ddl, ds.seed, ed.value, x.query, x.table]);
        const cur = FS.at(path) || {};
        FS.patch(path, Object.assign({}, cur, { sql: ed.value, tries: (cur.tries || 0) + 1, ok: cur.ok || !!p.uses_index, last: p.ok ? (p.uses_index ? "走索引" : "仍是全表扫描") : p.error }));
        out.textContent = "";
        if (!p.ok) { out.append(h("div", { class: "callout" }, h("b", null, "出错　"), p.error)); return; }
        out.append(h("div", { class: "row" }, p.uses_index ? h("span", { class: "pill passed" }, `✓ ${x.table} 走索引了`) : h("span", { class: "pill due" }, `✗ ${x.table} 还是全表扫描`)), h("div", { class: "small faint" }, "加索引后的执行计划："), fsPlan(p.after),
          p.indexes.length ? h("div", { class: "small" }, "当前索引：" + p.indexes.map(i => `${i.name}(${i.cols.join(", ")})`).join("；")) : "");
      } catch (e) { out.textContent = "运行失败：" + ((e && e.message) || e); }
    };
    const askAI = () => fsJob(jk, `你是资深 DBA，在点评一道索引优化题。
${SD_COACH_RULE}
【题目】${x.question}\n【目标查询】${x.query}\n【参考索引】${x.answer}\n【讲解】${x.explain}
【他的索引】${(FS.at(path) || {}).sql || "（空）"}\n【执行计划结果】${(FS.at(path) || {}).last || "还没运行"}
从列顺序（最左前缀、等值在前范围在后、区分度）、是否覆盖索引、能否消除排序、写入代价和索引数量、是否需要改写 SQL 几方面点评。走了索引但不是最优也要指出。
只返回 JSON：{"score": 7, "verdict": "一句话", "items": [{"you": "...", "verdict": "对|方向对但不准|有错|搞反|缺失|最大扣分点", "why": "..."}], ${SD_COACH_JSON}}`, path);
    const evBox = fsEvalBox(r, jk, askAI, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""), verdictTable(ev.items), coachEl(ev)));
    box.append(h("section", { class: "panel" }, mdEl(x.question), h("h3", null, "目标查询"), h("pre", { class: "sd-pre" }, x.query), h("div", { class: "small faint" }, "现在的执行计划："), before, fsDataset(x.dataset)),
      h("section", { class: "panel" }, ed, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: run }, "建索引，看执行计划"), h("button", { class: "btn sm", type: "button", disabled: !!FS_JOBS[jk], onclick: askAI }, "让 AI 点评"),
        h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); draw(); } }, "看答案"), r.ok ? h("span", { class: "sd-ok small" }, "✓ 已走索引") : ""), out, evBox),
      r.peek ? h("section", { class: "panel" }, h("h2", null, "参考答案"), h("pre", { class: "sd-pre" }, x.answer), mdEl(x.explain, "small"), h("h3", null, "常见错误"), sdList(x.pitfalls)) : "", fsNav(fsSQL().index, x.id));
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-sql", `${x.id.toUpperCase()} ${x.title}`, null, box);
}
function fsSchemaView(x) {
  const box = h("div", { class: "stack" }), path = ["s", x.id], jk = "s:" + x.id;
  fsProvide(`建表 · ${x.title}`, () => { const r = FS.at(path) || {}; return `【建表题】${x.requirement}\n【必须支撑的查询】${x.queries_needed.join("；")}\n【他的建表】\n${r.ddl || "（还没写）"}\n【他的说明】${r.notes || ""}\n${r.peek || r.ev ? "【参考】\n" + x.reference_ddl : "【重要】先引导，不要直接给出完整建表语句。"}`; }, null);
  const draw = () => {
    const r = FS.at(path) || {};
    box.textContent = "";
    const ed = fsCode(`fs-${x.id}-ddl`, r.ddl, v => FS.patch(path.concat("ddl"), v), "sql", 260);
    ed.placeholder = "CREATE TABLE ...（MySQL 风格即可）";
    const notes = fsTa(`fs-${x.id}-notes`, r.notes, v => FS.patch(path.concat("notes"), v), 80); notes.placeholder = "设计说明：为什么这样拆表、主键 / 唯一键 / 索引服务于哪个查询、字段类型怎么选";
    const out = h("div", null, ddlView(r.chk));
    const chk = async () => { if (!ed.value.trim()) { toast("先写建表语句"); return; } out.textContent = ""; out.append(h("div", { class: "thinking" }, "建表中……")); try { const c = await checkDDL(ed.value); FS.patch(path.concat("chk"), c); out.textContent = ""; out.append(ddlView(c)); } catch (e) { out.textContent = "检查失败：" + ((e && e.message) || e); } };
    const askAI = () => {
      const now = FS.at(path) || {};
      if (!(now.ddl || "").trim()) { toast("先写建表语句"); return; }
      fsJob(jk, `你是资深后端架构师，在评审一份数据库表设计（面试题）。
${SD_COACH_RULE}
【需求】${x.requirement}\n【必须支撑的查询】${x.queries_needed.join("；")}
【参考设计】\n${x.reference_ddl}\n【参考讲解】${x.explain}\n【得分点】${x.points.join("；")}
【他的建表语句】\n${clip(now.ddl, 6000)}${now.chk ? "\n【SQLite 检查结果】\n" + ddlSummary(now.chk) : ""}\n【他的说明】${now.notes || "（空）"}
逐个检查：能否支撑每条查询、主键与唯一键（幂等 / 防重复）、索引是否服务真实查询、字段类型（金额、时间、状态）、范式与冗余取舍、并发更新的字段（版本号）、软删除、将来分库分表的键。和参考不同但成立的设计要肯定。
只返回 JSON：{"score": 7, "verdict": "一句话", "items": [{"you": "他设计的某一点", "verdict": "对|方向对但不准|有错|搞反|缺失|最大扣分点", "why": "..."}], "queries": [{"q": "必须支撑的查询", "ok": true, "comment": "能否高效支撑"}], ${SD_COACH_JSON}}`, path);
    };
    const evBox = fsEvalBox(r, jk, askAI, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""), verdictTable(ev.items),
      Array.isArray(ev.queries) && ev.queries.length ? h("ul", { class: "ex-points sd-fields" }, ev.queries.map(y => h("li", { class: y.ok ? "hit" : "miss" }, h("b", null, y.ok ? "能支撑" : "支撑不好"), h("span", null, `${y.q}：${y.comment || ""}`)))) : "", coachEl(ev)));
    box.append(h("section", { class: "panel" }, mdEl(x.requirement), h("h3", null, "这套表必须支撑的查询"), sdList(x.queries_needed)),
      h("section", { class: "panel" }, ed, h("div", { class: "row" }, h("button", { class: "btn sm", type: "button", onclick: chk }, "用 SQLite 检查建表"), h("button", { class: "btn primary sm", type: "button", disabled: !!FS_JOBS[jk], onclick: askAI }, r.ev ? "改完了，重新评审" : "让 AI 评审设计"),
        h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); draw(); } }, "看参考")), out, notes, evBox),
      r.peek ? h("section", { class: "panel" }, h("h2", null, "参考设计"), h("pre", { class: "sd-pre" }, x.reference_ddl), mdEl(x.explain, "small"), h("h3", null, "得分点"), sdList(x.points)) : "", fsNav(fsSQL().schema, x.id));
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-sql", `${x.id.toUpperCase()} ${x.title}`, null, box);
}

// ----- 技术选型：技术卡片 + 场景题（五句话） -----
function fsTechList() {
  fsProvide("技术选型", () => "技术卡片：" + fsTech().cards.map(c => c.name).join("、"), [{ label: "随机考我一项技术", run: ch => { const c = fsTech().cards[Math.floor(Math.random() * fsTech().cards.length)]; ch.send(`随机考我「${c.name}」：先问一个它的核心原理或适用边界的问题，等我答完再点评，然后追问一个线上踩坑的问题。`, { label: "随机考我：" + c.name }); } }]);
  const t = fsTech(), st = FS.get().c || {}, by = {};
  for (const c of t.cards) (by[c.cat] = by[c.cat] || []).push(c);
  return fsPage("fs-tech", "技术选型：没有最好，只有在约束下最合适", "选型就是权衡：先说约束（一致性、延迟、规模、成本、团队能力），再说选什么、备选是什么、为什么不选备选，最后说选的方案缺点是什么、怎么兜底、用什么指标证明。下面先练场景题，卡住了去翻技术卡片。",
    h("section", { class: "panel" }, h("h2", null, `场景选型题（${t.scenarios.length}）`), h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("thead", null, h("tr", null, ["", "场景", "候选", "难度", "状态"].map(x => h("th", null, x)))),
      h("tbody", null, t.scenarios.map(s => h("tr", { class: "sd-row", onclick: () => go("fs-" + s.id) }, h("td", { class: "mono" }, s.id.toUpperCase()), h("td", null, h("a", { href: "#fs-" + s.id }, s.title)), h("td", { class: "small muted" }, s.options.join(" / ")), h("td", { class: "small" }, s.level), h("td", { class: "num small" }, (st[s.id] || {}).ev ? st[s.id].ev.score + " 分" : "—"))))))),
    ...Object.entries(by).map(([cat, cs]) => h("section", { class: "stack" }, h("h2", null, cat), h("div", { class: "fs-cards" }, cs.map(c => h("a", { class: "panel hub", href: "#fs-k-" + c.id }, h("h3", null, c.name), h("p", { class: "small muted" }, clip(c.what, 60))))))));
}
function fsCardView(c) {
  fsProvide(`技术卡片 · ${c.name}`, () => `【技术卡片】${c.name}（${c.cat}）\n${c.what}\n优点：${c.pros.join("；")}\n缺点：${c.cons.join("；")}\n适合：${c.fits.join("；")}\n不适合：${c.avoid.join("；")}\n坑：${c.pitfalls.join("；")}`,
    [{ label: "考考我", run: ch => ch.send(`考我「${c.name}」：先问一个原理或适用边界的问题，一次一个；我答完你点评（哪里想错了、更好的答法），再追问一个线上踩坑的问题。`, { label: "考考我：" + c.name }) },
     { label: "和别的比", run: ch => ch.send(`把「${c.name}」和它最常被拿来比较的 2 个方案做个对比表：模型、性能、一致性、运维成本、典型场景，最后给一句选型口诀。`, { label: "对比：" + c.name }) }]);
  const two = (a, b) => h("div", { class: "grid-2" }, a, b);
  const blk = (t, xs, cls) => h("div", { class: "panel " + (cls || "") }, h("h3", null, t), sdList(xs));
  const used = fsTech().scenarios.filter(s => s.options.some(o => o.includes(c.name) || c.name.includes(o)));
  return fsPage("fs-tech", c.name, c.cat,
    h("section", { class: "panel" }, mdEl(c.what)),
    two(blk("优点", c.pros, "fs-pro"), blk("缺点", c.cons, "fs-con")), two(blk("适合", c.fits), blk("不适合 / 别这么用", c.avoid)),
    h("section", { class: "panel" }, h("h3", null, "和谁比"), h("ul", { class: "mock-ul" }, c.vs.map(v => h("li", null, h("b", null, "vs " + v.other + "："), v.diff)))),
    blk("线上常见坑", c.pitfalls),
    h("section", { class: "panel" }, h("h3", null, "面试会问"), ...c.interview.map(f => { const e = h("details", { class: "qa" }, h("summary", null, f.q)); e.append(mdEl(f.a, "small")); return e; })),
    used.length ? h("section", { class: "panel" }, h("h3", null, "用到它的选型题"), h("div", { class: "row" }, used.map(s => h("a", { class: "chip", href: "#fs-" + s.id }, s.title)))) : "",
    h("a", { class: "btn ghost sm", href: "#fs-tech" }, "← 全部技术"));
}
function fsScenarioView(s) {
  const box = h("div", { class: "stack" }), path = ["c", s.id], jk = "c:" + s.id;
  fsProvide(`选型 · ${s.title}`, () => { const r = FS.at(path) || {}; return `【选型题】${s.requirement}\n【约束】${s.constraints}\n【候选】${s.options.join("、")}\n【他的五句】${JSON.stringify(r.f || {})}\n${r.ev || r.peek ? "【参考】" + JSON.stringify(s.reference) : "【重要】先引导他按约束推理，不要直接给出参考选择。"}`; }, null);
  const draw = () => {
    const r = FS.at(path) || {}, f = r.f || {};
    box.textContent = "";
    const tas = S5_CHOICE.map(([k, t]) => [k, t, fsTa(`fs-${s.id}-${k}`, f[k], v => FS.patch(path.concat("f", k), v), 64)]);
    const ask = () => {
      const F = (FS.at(path) || {}).f || {};
      if (Object.values(F).join("").length < 15) { toast("先把五句写上"); return; }
      fsJob(jk, `你是资深架构师，在考技术选型。学习者要用五句话说服你：约束 / 选择 / 备选 / 为什么不选备选 / 缺点 + 兜底 + 指标。
${SD_COACH_RULE}
【场景】${s.requirement}\n【约束】${s.constraints}\n【候选】${s.options.join("、")}
【参考】选择：${s.reference.choice}\n理由：${s.reference.why}\n不选其他：${s.reference.why_not}\n缺点与兜底：${s.reference.downside}\n指标：${s.reference.metric}\n【得分点】${s.points.join("；")}
【学习者】\n${S5_CHOICE.map(([k, t]) => `${t}：${F[k] || "（空）"}`).join("\n")}
他的选择不必和参考一致：能从约束推出选择、备选比较公平、代价和兜底说得清、指标可验证就给高分；在这个约束下选错了要明确说，并说清错在哪条约束。
只返回 JSON：{"score": 7, "verdict": "一句话", "items": [{"key": "constraint", "ok": true, "comment": ""}, {"key": "choice", "ok": true, "comment": ""}, {"key": "alternatives", "ok": false, "comment": ""}, {"key": "why_not", "ok": false, "comment": ""}, {"key": "downside", "ok": false, "comment": ""}], "better": "五句完整示范（像真人口述）", ${SD_COACH_JSON}}`, path);
    };
    const evBox = fsEvalBox(r, jk, ask, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""),
      h("ul", { class: "ex-points sd-fields" }, S5_CHOICE.map(([k, t]) => { const y = (Array.isArray(ev.items) ? ev.items : []).find(z => z.key === k) || {}; return h("li", { class: y.ok ? "hit" : "miss" }, h("b", null, `${t} ${y.ok ? "到位" : "缺 / 不准"}`), h("span", null, y.comment || "")); })),
      ev.better ? h("details", { class: "qa", open: true }, h("summary", null, "五句示范"), mdEl(String(ev.better), "small")) : "", coachEl(ev)));
    const cards = fsTech().cards.filter(c => s.options.some(o => o.includes(c.name) || c.name.includes(o)));
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, h("span", { class: "pill todo" }, s.level)), mdEl(s.requirement), h("div", { class: "callout" }, h("b", null, "约束　"), s.constraints),
      h("div", { class: "row" }, h("span", { class: "small faint" }, "候选："), s.options.map(o => h("span", { class: "chip" }, o))), cards.length ? h("div", { class: "row" }, h("span", { class: "small faint" }, "相关卡片："), cards.map(c => h("a", { class: "chip", href: "#fs-k-" + c.id }, c.name))) : ""),
      h("section", { class: "panel" }, h("p", { class: "small muted" }, "五句：约束是什么 → 我选什么 → 备选有哪些 → 为什么不选备选 → 缺点是什么、怎么兜底、用什么指标证明。"), h("div", { class: "sd-fill" }, tas.map(([k, t, el]) => h("label", { class: "card-f" }, h("b", null, t), el))),
        h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!FS_JOBS[jk], onclick: ask }, r.ev ? "改完了，重新点评" : "提交，让 AI 点评"), h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); draw(); } }, "看参考")), evBox),
      r.peek || r.ev ? h("section", { class: "panel" }, h("h2", null, "参考选型"), h("ul", { class: "mock-ul" }, [["选择", s.reference.choice], ["为什么", s.reference.why], ["为什么不选其他", s.reference.why_not], ["缺点与兜底", s.reference.downside], ["证明指标", s.reference.metric]].map(([t, v]) => h("li", null, h("b", null, t + "："), v))), h("h3", null, "得分点"), sdList(s.points)) : "", fsNav(fsTech().scenarios, s.id));
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-tech", s.title, null, box);
}

// ----- 代码评审 -----
function fsReviewList() {
  fsProvide("代码评审", () => "学习者在选代码评审题。", null);
  const st = FS.get().r || {};
  return fsPage("fs-review", "代码评审：看出能跑代码里的坑", "每段代码都能跑，但藏着 3–7 个问题：竞态、泄漏、注入、事务失效、N+1、缺超时、不幂等……按“第几行：什么问题 → 什么情况下出事 → 怎么改”写评审意见，AI 对照参考判你找到了几个、严重程度判断得准不准。",
    h("section", { class: "panel" }, h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("thead", null, h("tr", null, ["", "代码", "语言", "状态"].map(x => h("th", null, x)))),
      h("tbody", null, fsReviews().map(r => h("tr", { class: "sd-row", onclick: () => go("fs-" + r.id) }, h("td", { class: "mono" }, r.id.toUpperCase()), h("td", null, h("a", { href: "#fs-" + r.id }, r.title)), h("td", { class: "small muted" }, r.lang), h("td", { class: "num small" }, (st[r.id] || {}).ev ? st[r.id].ev.score + " 分" : "—"))))))));
}
function fsCodeBlock(code, marks) {
  const lines = code.replace(/\n$/, "").split("\n");
  return h("div", { class: "fs-codeview" }, lines.map((l, i) => h("div", { class: "fs-line" + (marks && marks[i + 1] ? " mark " + marks[i + 1] : "") }, h("span", { class: "fs-ln num" }, i + 1), h("code", null, l || " "))));
}
function fsReviewView(rv) {
  const box = h("div", { class: "stack" }), path = ["r", rv.id], jk = "r:" + rv.id;
  fsProvide(`代码评审 · ${rv.title}`, () => { const r = FS.at(path) || {}; return `【代码评审题】${rv.title}（${rv.lang}）\n${rv.context}\n【代码（带行号）】\n${rv.code.split("\n").map((l, i) => `${i + 1}: ${l}`).join("\n")}\n【他的评审意见】${r.text || "（还没写）"}\n${r.ev || r.peek ? "【参考问题】" + rv.issues.map(i => `第${i.lines}行 ${i.severity} ${i.desc}`).join("；") : "【重要】先引导他自己找，不要直接列出全部问题。"}`; },
    [{ label: "给我一个方向", run: ch => ch.send("这段代码我只找到一部分问题。给我一个方向提示（比如“看看并发”“看看资源释放”），不要直接说是哪一行。", { label: "给我一个方向" }) },
     { label: "评审的检查清单", run: ch => ch.send("给我一份这类代码（" + rv.lang + "）的 Code Review 检查清单：正确性、并发、资源、安全、性能、可维护性各看什么。", { label: "评审检查清单" }) }]);
  const draw = () => {
    const r = FS.at(path) || {}, done = !!(r.ev || r.peek);
    box.textContent = "";
    const marks = {};
    if (done) for (const i of rv.issues) { const [a, b] = String(i.lines).split("-").map(Number); for (let n = a; n <= (b || a); n++) marks[n] = i.severity === "严重" ? "sev" : i.severity === "一般" ? "mid" : "low"; }
    const ta = fsTa(`fs-${rv.id}-text`, r.text, v => FS.patch(path.concat("text"), v), 180);
    ta.placeholder = "按条写：\n第 12 行：……问题。在……情况下会……。建议改成……\n第 20–23 行：……";
    const ask = () => {
      const t = ((FS.at(path) || {}).text || "").trim();
      if (t.length < 10) { toast("先写几条评审意见"); return; }
      fsJob(jk, `你是资深工程师，在评一位候选人做的 Code Review（面试题）。
${SD_COACH_RULE}
【代码背景】${rv.context}
【代码（带行号）】\n${rv.code.split("\n").map((l, i) => `${i + 1}: ${l}`).join("\n")}
【参考问题清单】\n${rv.issues.map((i, n) => `${n}. 第 ${i.lines} 行 [${i.severity} / ${i.kind}] ${i.desc}；修法：${i.fix}`).join("\n")}
【参考总评】${rv.summary}
【他的评审意见】\n${t}
逐条判断参考问题他有没有找到（意思对、行号大致对就算），严重程度判断是否合理；他提的参考之外的问题，判断是真问题（加分）还是误报。
只返回 JSON：{"score": 7, "verdict": "一句话", "found": [{"i": 0, "hit": true, "comment": "他怎么说的 / 差在哪"}], "extra": [{"you": "他提的参考外问题", "valid": true, "why": "真问题还是误报"}], ${SD_COACH_JSON}}`, path);
    };
    const evBox = fsEvalBox(r, jk, ask, (b, ev) => {
      const found = Array.isArray(ev.found) ? ev.found : [];
      b.append(scoreLine(Number(ev.score) || 0, h("span", { class: "small" }, `找到 ${found.filter(x => x.hit).length} / ${rv.issues.length}　${ev.verdict || ""}`)),
        h("ul", { class: "ex-points sd-fields" }, rv.issues.map((i, n) => { const y = found.find(z => Number(z.i) === n) || {}; return h("li", { class: y.hit ? "hit" : "miss" }, h("b", null, `${y.hit ? "找到" : "漏了"} · 第 ${i.lines} 行`), h("span", null, `[${i.severity}] ${i.desc}${y.comment ? "　—— " + y.comment : ""}`)); })),
        Array.isArray(ev.extra) && ev.extra.length ? h("div", null, h("h3", null, "你额外提的"), h("ul", { class: "mock-ul" }, ev.extra.map(x => h("li", null, h("span", { class: "pill " + (x.valid ? "passed" : "todo") }, x.valid ? "真问题" : "误报"), " ", String(x.you || ""), h("span", { class: "small faint" }, "　" + String(x.why || "")))))) : "", coachEl(ev));
    });
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, h("span", { class: "pill trying" }, rv.lang)), mdEl(rv.context, "small"), fsCodeBlock(rv.code, marks)),
      h("section", { class: "panel" }, h("h2", null, "你的评审意见"), ta, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!FS_JOBS[jk], onclick: ask }, r.ev ? "改完了，重新评估" : "提交，让 AI 对照参考"), h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); draw(); } }, "看参考")), evBox),
      done ? h("section", { class: "panel" }, h("h2", null, "参考评审"), h("div", { class: "scroll-x" }, h("table", { class: "ptable sd-verdicts" }, h("thead", null, h("tr", null, ["行", "严重程度", "问题", "怎么改"].map(x => h("th", null, x)))),
        h("tbody", null, rv.issues.map(i => h("tr", null, h("td", { class: "num" }, i.lines), h("td", null, h("span", { class: "pill " + (i.severity === "严重" ? "due" : i.severity === "一般" ? "trying" : "todo") }, i.severity), h("div", { class: "small faint" }, i.kind)), h("td", null, i.desc), h("td", null, mdEl(i.fix, "small"))))))),
        h("div", { class: "callout blue" }, h("b", null, "总评　"), rv.summary), h("h3", null, "得分点"), sdList(rv.points)) : "", fsNav(fsReviews(), rv.id));
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-review", rv.title, null, box);
}

// ----- 在浏览器 Worker 里运行 JS：说输出验证 / 手写题测试 -----
const FS_W_PRE = `const __send = x => postMessage(x);
const __cfmt = v => typeof v === "string" ? v : v === undefined ? "undefined" : typeof v === "function" ? "[Function]" : typeof v === "bigint" ? v + "n" : (() => { try { const s = JSON.stringify(v); return s === undefined ? String(v) : s; } catch (e) { return String(v); } })();
console.log = (...a) => __send({ log: a.map(__cfmt).join(" ") }); console.info = console.warn = console.error = console.log;
`;
function fsWorker(src, timeout) {
  return new Promise(res => {
    const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
    const w = new Worker(url), logs = [];
    let t = null;
    const done = v => { clearTimeout(t); w.terminate(); URL.revokeObjectURL(url); res(Object.assign({ logs }, v)); };
    t = setTimeout(() => done({ timeout: true }), timeout);
    w.onmessage = e => { const m = e.data || {}; if (m.log != null) logs.push(m.log); else done(m); };
    w.onerror = e => { e.preventDefault(); done({ error: e.message || "运行出错" }); };
  });
}
// 包一层函数并以 {} 作为 this 调用：和 Node CommonJS 一致（顶层 this 是 module.exports，变量是模块作用域，"use strict" 仍是第一句）
const fsRunOutput = code => fsWorker(FS_W_PRE + "(function () {\n" + code + "\n}).call({});\nsetTimeout(() => __send({ done: true }), 600);", 5000);
const fsRunTests = (code, tests) => fsWorker(FS_W_PRE + FS_JS + "\n;\n" + code + "\n;\n" + tests + "\n;__run(3000).then(r => __send({ cases: r }));", 20000);

// ----- 语言专项：说输出 / 选择 / 简答，一题一题刷 -----
const FS_LANG_ORDER = ["JavaScript", "TypeScript", "React", "Vue", "CSS", "浏览器", "工程化", "网络", "Go", "Java", "Python", "Web 框架", "数据库", "Linux"];
function fsLangView() {
  const all = fsLang();
  const box = h("div", { class: "stack" }), side = h("aside", { class: "panel sd-side" });
  let f = Object.assign({ track: "", langs: [], kind: "", mode: "seq" }, LS.get("tiyan:fs:langf", {}));
  const pool = () => {
    const rec = FS.get().l || {};
    return all.filter(x => (!f.track || x.track === f.track) && (!f.langs.length || f.langs.includes(x.lang)) && (!f.kind || x.kind === f.kind)
      && (f.mode !== "wrong" || (rec[x.id] && rec[x.id].ok === false)) && (f.mode !== "new" || !rec[x.id]));
  };
  let cur = LS.get("tiyan:fs:langcur", null);
  fsProvide("语言专项", () => { const x = all.find(y => y.id === cur); const r = x && (FS.get().l || {})[x.id]; return x ? `【当前题】${x.lang} · ${x.topic}\n${x.q}\n${x.code ? "```\n" + x.code + "\n```" : ""}\n${x.options ? "选项：" + x.options.map((o, i) => `${i}. ${o}`).join("；") : ""}\n【他的作答】${r ? JSON.stringify(r.ans) : "（还没答）"}\n${r ? "【参考答案】" + JSON.stringify(x.answer) + "\n【讲解】" + x.explain : "【重要】他还没作答：不要直接说出答案，可以先帮他理清概念。"}` : "还没选题。"; },
    [{ label: "讲透这道题", run: ch => ch.send("把这道题背后的原理讲透：为什么是这个答案，涉及的机制是什么，再给一个容易混淆的变体考我。", { label: "讲透这道题" }) },
     { label: "再出一道类似的", run: ch => ch.send("按这道题的考点再出一道类似但更难一点的题考我（只出题，不给答案），我答完你再点评。", { label: "再出一道类似的" }) }]);
  const draw = () => {
    const P = pool(), rec = FS.get().l || {};
    if (!P.find(x => x.id === cur)) cur = P[0] ? P[0].id : null;
    LS.set("tiyan:fs:langcur", cur); LS.set("tiyan:fs:langf", f);
    box.textContent = ""; side.textContent = "";
    // 筛选
    const seg = (opts, val, set) => h("div", { class: "seg" }, opts.map(([v, t]) => h("button", { type: "button", class: val === v ? "on" : "", onclick: () => { set(v); draw(); } }, t)));
    const langs = FS_LANG_ORDER.filter(l => all.some(x => x.lang === l && (!f.track || x.track === f.track)));
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, seg([["", "全部"], ["前端", "前端"], ["后端", "后端"]], f.track, v => { f.track = v; f.langs = []; }),
      seg([["", "全部题型"], ["output", "说输出"], ["choice", "选择"], ["short", "简答"]], f.kind, v => { f.kind = v; }), seg([["seq", "顺序"], ["new", "没做过的"], ["wrong", "错题"]], f.mode, v => { f.mode = v; })),
      h("div", { class: "row", style: "gap:6px" }, langs.map(l => { const n = all.filter(x => x.lang === l), ok = n.filter(x => (rec[x.id] || {}).ok).length; return h("button", { type: "button", class: "chip" + (f.langs.includes(l) ? " on" : ""), onclick: () => { f.langs = f.langs.includes(l) ? f.langs.filter(y => y !== l) : f.langs.concat([l]); draw(); } }, `${l} ${ok}/${n.length}`); }))));
    const x = P.find(y => y.id === cur);
    if (!x) { box.append(h("section", { class: "panel" }, h("p", { class: "muted" }, f.mode === "wrong" ? "没有错题了 👍" : "这个筛选下没有题。"))); return; }
    const i = P.indexOf(x), r = rec[x.id] || null, done = !!(r && (r.ok != null || r.ev));
    const go2 = n => { cur = P[n].id; draw(); window.scrollTo(0, 0); };
    const card = h("section", { class: "panel" }, h("div", { class: "spread" }, h("div", { class: "row" }, h("span", { class: "pill trying" }, x.lang), h("span", { class: "pill todo" }, x.topic), h("span", { class: "small faint" }, { output: "说输出", choice: "选择", short: "简答" }[x.kind])), h("span", { class: "small faint num" }, `${i + 1} / ${P.length}`)),
      h("p", { class: "sd-prompt", style: "font-size:17px" }, x.q), x.code ? h("pre", { class: "sd-pre" }, x.code) : "");
    const res = h("div", { class: "stack" });
    const reveal = ok => { res.textContent = ""; res.append(ok != null ? h("div", { class: "row" }, ok ? h("span", { class: "pill passed" }, "✓ 对了") : h("span", { class: "pill due" }, "✗ 不对")) : "", x.kind === "output" ? h("div", null, h("div", { class: "small faint" }, "实际输出"), h("pre", { class: "sd-pre" }, x.answer)) : x.kind === "short" ? h("details", { class: "qa" }, h("summary", null, "参考答案"), mdEl(x.answer, "small"), h("div", { class: "small" }, "得分点："), sdList(x.points || [])) : "", h("div", { class: "callout blue" }, h("b", null, "讲解　"), mdEl(x.explain, "small"))); };
    if (x.kind === "output") {
      const ta = fsTa(`fs-l-${x.id}`, r ? r.ans : "", () => {}, 70, "mono");
      ta.placeholder = "写出程序的输出（多行就换行写）";
      const norm = s => String(s || "").replace(/\s+/g, " ").trim();
      const check = () => { const ok = norm(ta.value) === norm(x.answer); FS.patch(["l", x.id], { ok, ans: ta.value, at: Date.now() }); reveal(ok); drawSide(); };
      const runBtn = x.lang === "JavaScript" ? h("button", { class: "btn ghost sm", type: "button", onclick: async () => { const o = await fsRunOutput(x.code); res.append(h("div", null, h("div", { class: "small faint" }, "在你的浏览器里运行的结果" + (o.error ? "（报错：" + o.error + "）" : o.timeout ? "（超时）" : "")), h("pre", { class: "sd-pre" }, o.logs.join("\n") || "（没有输出）"))); } }, "在浏览器里运行验证") : "";
      card.append(ta, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: check }, "提交"), done ? runBtn : ""), res);
      if (done) reveal(r.ok);
    } else if (x.kind === "choice") {
      const multi = x.answer.length > 1, picked = new Set(r && Array.isArray(r.ans) ? r.ans : []);
      const opts = h("div", { class: "stack", style: "gap:6px" }, x.options.map((o, k) => h("button", { type: "button", class: "quiz-opt" + (done ? (x.answer.includes(k) ? " right" : picked.has(k) ? " wrong" : "") : picked.has(k) ? " picked" : ""), disabled: done,
        onclick: e => { if (multi) { picked.has(k) ? picked.delete(k) : picked.add(k); e.currentTarget.classList.toggle("picked"); } else { picked.clear(); picked.add(k); submit(); } } }, `${"ABCDE"[k]}. ${o}`)));
      const submit = () => { const a = [...picked].sort(); const ok = a.length === x.answer.length && a.every((v, k) => v === [...x.answer].sort()[k]); FS.patch(["l", x.id], { ok, ans: a, at: Date.now() }); draw(); };
      card.append(multi ? h("div", { class: "small faint" }, "多选") : "", opts, multi && !done ? h("button", { class: "btn primary sm", type: "button", onclick: submit }, "提交") : "", res);
      if (done) reveal(r.ok);
    } else {
      const jk = "l:" + x.id;
      const ta = fsTa(`fs-l-${x.id}`, r ? r.ans : "", v => FS.patch(["l", x.id, "ans"], v), 120);
      const [vb, vs] = fsVoice(ta);
      const ask = () => {
        if (ta.value.trim().length < 10) { toast("先写几句"); return; }
        FS.patch(["l", x.id, "ans"], ta.value);
        fsJob(jk, `你是资深面试官，在给一道${x.lang}简答题打分。
${SD_COACH_RULE}
【题目】${x.q}${x.code ? "\n```\n" + x.code + "\n```" : ""}
【得分点】${(x.points || []).map((p, k) => k + ". " + p).join("；")}
【参考答案】${x.answer}
【他的回答】${ta.value}
意思对即可。评分档位：9–10 全部得分点且有自己的理解；7–8.5 基本到位；5–6.5 一半；3–4.5 大部分缺失。
只返回 JSON：{"score": 7, "hit": [0, 2], "verdict": "一句话", "better": "更好的回答（像面试里口述，100–200 字）", ${SD_COACH_JSON}}`, ["l", x.id]);
      };
      const evBox = fsEvalBox(r, jk, ask, (b, ev) => {
        const sc = Number(ev.score) || 0;
        if ((FS.at(["l", x.id]) || {}).ok == null) FS.patch(["l", x.id, "ok"], sc >= 7);
        b.append(scoreLine(sc, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""), h("ul", { class: "ex-points sd-fields" }, (x.points || []).map((p, k) => { const hit = (ev.hit || []).map(Number).includes(k); return h("li", { class: hit ? "hit" : "miss" }, h("b", null, hit ? "答到" : "漏了"), h("span", null, p)); })),
          ev.better ? h("details", { class: "qa", open: true }, h("summary", null, "更好的回答"), mdEl(String(ev.better), "small")) : "", coachEl(ev));
        reveal(null);
      });
      card.append(ta, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!FS_JOBS[jk], onclick: ask }, r && r.ev ? "改完了，重新打分" : "提交，让 AI 打分"), vb, vs, !(r && r.ev) ? h("button", { class: "btn ghost sm", type: "button", onclick: () => reveal(null) }, "直接看答案") : ""), evBox, res);
    }
    card.append(h("div", { class: "spread" }, i > 0 ? h("button", { class: "btn ghost sm", type: "button", onclick: () => go2(i - 1) }, "← 上一题") : h("span"), i < P.length - 1 ? h("button", { class: "btn sm", type: "button", onclick: () => go2(i + 1) }, "下一题 →") : h("span", { class: "small faint" }, "这一组做完了")));
    box.append(card);
    drawSide();
  };
  const drawSide = () => {
    const rec = FS.get().l || {};
    side.textContent = "";
    side.append(h("div", { class: "eyebrow" }, "进度"), ...["前端", "后端"].map(tr => { const xs = all.filter(x => x.track === tr), done = xs.filter(x => rec[x.id] && (rec[x.id].ok != null)), ok = done.filter(x => rec[x.id].ok); return h("div", { class: "small" }, h("b", null, tr), `　做过 ${done.length} / ${xs.length}，对 ${ok.length}`); }),
      h("p", { class: "small muted" }, "说输出的题都在真实环境里跑过（JS / TS 用 Node，Go、Java、Python 用各自的运行时），答案就是真实输出。JS 题做完可以在浏览器里再跑一次。"));
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-lang", "语言专项：前端 + 后端", "前端：JS / TS / React / Vue / CSS / 浏览器 / 工程化 / 网络；后端：Go / Java / Python / RESTful / 数据库 / Linux。说输出和选择题自动判对错，简答题 AI 按得分点打分。", h("div", { class: "sd-grid" }, box, side));
}

// ----- 前端手写：编辑器 + 浏览器里跑测试 -----
function fsHandList() {
  fsProvide("前端手写题", () => "学习者在选前端手写题。", null);
  const st = FS.get().h || {};
  return fsPage("fs-hand", "前端手写：在浏览器里跑测试", "防抖节流、深拷贝、Promise 并发池、EventEmitter、LRU、compose……面试高频手写题。写完点运行，测试在浏览器沙箱（Worker）里跑；全部通过后可以让 AI 从边界、复杂度和面试表达角度点评。",
    h("div", { class: "hubs" }, fsHand().map(x => { const r = st[x.id] || {}; return h("a", { class: "panel hub", href: "#fs-" + x.id }, h("div", { class: "eyebrow" }, x.level), h("h2", null, x.title), h("p", { class: "small muted" }, clip(x.desc, 60)), h("div", { class: "small faint" }, r.pass ? "✓ 已通过" : r.code ? "写过，未全部通过" : "未开始")); })));
}
function fsHandView(x) {
  const path = ["h", x.id], jk = "h:" + x.id;
  const left = h("div", { class: "stack" }), edWrap = h("div", { class: "fs-editor" }), out = h("div", { class: "stack" }), evWrap = h("div");
  let cm = null, hints = 0;
  const code = () => cm ? cm.getValue() : (FS.at(path) || {}).code || x.starter;
  fsProvide(`手写 · ${x.title}`, () => { const r = FS.at(path) || {}; return `【前端手写题】${x.title}\n${x.desc}\n【测试】\n${clip(x.tests, 2500)}\n【他的代码】\n${code()}\n${r.last ? "【最近一次测试】" + r.last : ""}\n${r.pass || r.peek ? "【参考实现】\n" + x.solution : "【重要】先引导，不要直接贴完整实现。"}`; },
    [{ label: "给我提示", run: ch => ch.send("给我一个思路提示（关键数据结构 / 关键步骤），不要直接写完整代码。", { label: "给我提示" }) },
     { label: "为什么测试没过", run: ch => ch.send("看看我的代码和最近一次测试结果，为什么没过？指出具体是哪段逻辑，先别给完整答案。", { label: "为什么测试没过" }) }]);
  const ladder = h("div", { class: "hint-ladder" });
  const hintBtn = h("button", { class: "btn ghost sm", type: "button", onclick: () => { if (hints >= x.hints.length) return; ladder.append(h("div", { class: "hint" }, h("b", null, `提示 ${hints + 1}`), x.hints[hints])); hints++; if (hints >= x.hints.length) hintBtn.disabled = true; } }, "提示");
  const sol = h("div");
  left.append(h("section", { class: "panel" }, h("div", { class: "row" }, h("span", { class: "pill todo" }, x.level)), mdEl(x.desc), h("h3", null, "考察点"), sdList(x.points),
    h("details", { class: "qa" }, h("summary", null, "测试代码"), h("pre", { class: "sd-pre" }, x.tests)), h("div", { class: "row" }, hintBtn, h("button", { class: "btn ghost sm", type: "button", onclick: () => { FS.patch(path.concat("peek"), true); sol.textContent = ""; sol.append(h("h3", null, "参考实现"), h("pre", { class: "sd-pre" }, x.solution)); } }, "看参考实现")), ladder, sol));
  const run = async () => {
    const c = code();
    FS.patch(path.concat("code"), c);
    out.textContent = ""; out.append(h("div", { class: "thinking" }, "运行测试中……"));
    const r = await fsRunTests(c, x.tests);
    out.textContent = "";
    if (r.error || r.timeout) { const msg = r.timeout ? "运行超时（死循环？或者有 Promise 一直没 resolve）" : r.error; FS.patch(path.concat("last"), msg); out.append(h("div", { class: "callout" }, h("b", null, "没跑起来　"), msg)); return; }
    const cases = r.cases || [], pass = cases.filter(t => t.pass).length, all = pass === cases.length && cases.length > 0;
    FS.patch(path.concat("last"), `通过 ${pass}/${cases.length}；` + cases.filter(t => !t.pass).map(t => `${t.name}：${t.error}`).join("；"));
    if (all) FS.patch(path.concat("pass"), true);
    out.append(h("div", { class: "row" }, all ? h("span", { class: "pill passed" }, `✓ 全部通过 ${pass}/${cases.length}`) : h("span", { class: "pill due" }, `通过 ${pass}/${cases.length}`)),
      h("ul", { class: "ex-points sd-fields" }, cases.map(t => h("li", { class: t.pass ? "hit" : "miss" }, h("b", null, t.pass ? "通过" : "失败"), h("span", null, t.name + (t.pass ? "" : "：" + t.error))))),
      r.logs.length ? h("details", { class: "qa" }, h("summary", null, `console 输出（${r.logs.length}）`), h("pre", { class: "sd-pre" }, r.logs.join("\n"))) : "");
  };
  const ask = () => fsJob(jk, `你是资深前端面试官，在点评一道手写题。
${SD_COACH_RULE}
【题目】${x.title}：${x.desc}\n【考察点】${x.points.join("；")}\n【参考实现】\n${x.solution}
【他的代码】\n${code()}\n【测试结果】${(FS.at(path) || {}).last || "还没运行"}
从正确性与边界（this、参数透传、异常、取消、并发时序）、复杂度、代码可读性、面试时怎么讲四个角度点评；测试通过但写法有隐患也要指出。
只返回 JSON：{"score": 7, "verdict": "一句话", "items": [{"you": "...", "verdict": "对|方向对但不准|有错|搞反|缺失|最大扣分点", "why": "..."}], "talk": "面试时讲这道题的 30 秒说法", ${SD_COACH_JSON}}`, path);
  const drawEval = () => { evWrap.textContent = ""; evWrap.append(fsEvalBox(FS.at(path) || {}, jk, ask, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""), verdictTable(ev.items), ev.talk ? h("div", { class: "callout blue" }, h("b", null, "面试时这样讲　"), String(ev.talk)) : "", coachEl(ev)))); };
  FS_REDRAW = drawEval; onLeave(() => { FS_REDRAW = null; });
  const right = h("div", { class: "stack" }, h("section", { class: "panel" }, edWrap, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: run }, "运行测试（Ctrl / ⌘ + Enter）"), h("button", { class: "btn sm", type: "button", onclick: ask }, "让 AI 点评"),
    h("button", { class: "btn ghost sm", type: "button", onclick: () => { if (cm) cm.setValue(x.starter); } }, "恢复初始代码")), out, evWrap), fsNav(fsHand(), x.id));
  loadScript("vendor/cm-javascript.js").catch(() => null).then(() => {
    cm = CodeMirror(edWrap, { value: (FS.at(path) || {}).code || x.starter, mode: "javascript", lineNumbers: true, indentUnit: 2, tabSize: 2, matchBrackets: true, autoCloseBrackets: true, theme: "tiyan", viewportMargin: Infinity, extraKeys: { "Ctrl-Enter": run, "Cmd-Enter": run, Tab: c => c.replaceSelection("  ") } });
    let t = 0; cm.on("change", () => { clearTimeout(t); t = setTimeout(() => FS.patch(path.concat("code"), cm.getValue()), 400); });
  });
  drawEval();
  return fsPage("fs-hand", x.title, null, h("div", { class: "fs-hand" }, left, right));
}

// ----- 简历 × JD：匹配度、缺口、会被问到的题 -----
const FS_CAT_LINK = { "前端": "fs-lang", "后端": "fs-lang", "数据库": "fs-sql", "架构设计": "sd-sys", "技术选型": "fs-tech", "排障": "fs-trouble", "代码质量": "fs-review" };
function fsJD() {
  const box = h("div", { class: "stack" }), path = ["jd"], jk = "jd";
  fsProvide("简历 × JD", () => { const ev = (FS.at(path) || {}).ev; return `【目标 JD】${clip(LS.get("tiyan:fs:jdtext", ""), 3000)}\n【简历】${clip(LS.get("tiyan:mock:resume", ""), 3000)}\n${ev ? "【匹配分析】" + clip(JSON.stringify(ev), 4000) : ""}`; },
    [{ label: "怎么补最大的缺口", run: ch => ch.send("根据 JD 和我的简历，我最大的 2 个缺口是什么？给我一个两周的补齐计划（每天做什么、练站里哪些模块），以及面试时被问到这块怎么诚实又不失分地回答。", { label: "怎么补最大的缺口" }) },
     { label: "帮我改简历措辞", run: ch => ch.send("对照这份 JD，帮我找出简历里 3 处最该改的措辞（更贴近 JD 的关键词、补上量化结果），给出改前 / 改后。不要编造我没做过的事。", { label: "帮我改简历措辞" }) }]);
  const draw = () => {
    const r = FS.at(path) || {}, ev = r.ev;
    box.textContent = "";
    const jd = fsTa("fs-jd-text", LS.get("tiyan:fs:jdtext", ""), v => LS.set("tiyan:fs:jdtext", v), 160);
    jd.placeholder = "把目标岗位的 JD 贴进来（职位描述 + 职位要求，可以贴好几个）";
    const cv = fsTa("fs-jd-cv", LS.get("tiyan:mock:resume", ""), v => LS.set("tiyan:mock:resume", v), 160);
    cv.placeholder = "简历 / 项目经历（和「模拟面试」共用同一份，只存在你的浏览器里）";
    const file = h("input", { type: "file", accept: ".pdf,.docx,.txt,.md", hidden: true });
    const fstat = h("span", { class: "small muted" });
    file.addEventListener("change", async () => { const f0 = file.files[0]; if (!f0) return; try { const t = await readDocFile(f0, s => { fstat.textContent = s; }); cv.value = t; LS.set("tiyan:mock:resume", t); fstat.textContent = `读取了 ${t.length} 字`; } catch (e) { fstat.textContent = "读取失败：" + ((e && e.message) || e); } file.value = ""; });
    const analyze = () => {
      if (jd.value.trim().length < 50) { toast("先贴上 JD"); return; }
      if (cv.value.trim().length < 50) { toast("先贴上简历或项目经历"); return; }
      fsJob(jk, `你是资深技术面试官兼招聘负责人。请对照目标岗位 JD 和候选人简历，做匹配分析并出一套面试题。
要求：
1. 匹配度逐条对照 JD 的每一项要求：简历里有没有证据（引用简历原话或项目），强 / 中 / 弱 / 缺，给出怎么补或怎么讲的建议。不要编造候选人没写的经历。
2. 题目要结合候选人的真实项目和 JD 的业务场景出：项目深挖（为什么这么做、数据怎么来、遇到什么问题、怎么验证）、前端、后端、数据库、架构设计、技术选型、排障、代码质量、AI 协同、行为；24–30 题，基础 / 进阶 / 深挖都有。每题写清为什么会问、得分点、可能的追问。
3. 计划：最该先准备的 5 件事。
【JD】\n${clip(jd.value, 6000)}
【简历】\n${clip(cv.value, 8000)}
只返回 JSON：{"summary": "两三句话：整体匹配度和最大风险", "fit": 6.5, "match": [{"req": "JD 要求", "evidence": "简历里的证据（没有就写“无”）", "level": "强|中|弱|缺", "advice": "怎么补 / 怎么讲"}], "gaps": [{"gap": "缺口", "why": "为什么重要", "plan": "怎么补（具体到练什么）"}], "questions": [{"id": "q1", "cat": "项目深挖|前端|后端|数据库|架构设计|技术选型|排障|代码质量|AI 协同|行为", "level": "基础|进阶|深挖", "q": "问题", "why": "为什么会问", "points": ["得分点"], "followups": ["可能的追问"]}], "plan": ["最该先准备的事"]}`, path, "complex");
    };
    box.append(h("section", { class: "panel" }, h("h2", null, "1. 目标岗位 JD"), jd),
      h("section", { class: "panel" }, h("div", { class: "spread" }, h("h2", null, "2. 你的简历"), h("div", { class: "row" }, h("button", { class: "btn ghost sm", type: "button", onclick: () => file.click() }, "上传 PDF / Word"), fstat, file)), cv,
        h("p", { class: "small muted" }, "内容只存在你的浏览器里；点下面的按钮时会连同 JD 一起发给 AI。不想暴露的信息（公司名、手机号）可以先在「模拟面试」页用脱敏工具处理。")),
      h("div", { class: "row" }, h("button", { class: "btn primary", type: "button", disabled: !!FS_JOBS[jk], onclick: analyze }, ev ? "重新分析并出题" : "分析匹配度并出题"), h("span", { class: "small faint" }, "用更强的模型，大约 40–90 秒")));
    if (FS_JOBS[jk]) box.append(fsPending("AI 在逐条对照 JD 和简历……"));
    else if (r.err) box.append(fsErr(r.err, analyze));
    if (!ev) return;
    const LV = { "强": "passed", "中": "master", "弱": "trying", "缺": "due" };
    const qs = Array.isArray(ev.questions) ? ev.questions : [];
    const cats = [...new Set(qs.map(q => q.cat))];
    box.append(h("section", { class: "panel" }, h("h2", null, "匹配分析"), scoreLine(Number(ev.fit) || 0, h("span", { class: "small" }, String(ev.summary || ""))),
      h("div", { class: "scroll-x" }, h("table", { class: "ptable sd-verdicts" }, h("thead", null, h("tr", null, ["JD 要求", "简历里的证据", "匹配", "建议"].map(t => h("th", null, t)))),
        h("tbody", null, (ev.match || []).map(m => h("tr", null, h("td", null, String(m.req || "")), h("td", { class: "small" }, String(m.evidence || "")), h("td", null, h("span", { class: "pill " + (LV[m.level] || "todo") }, String(m.level || ""))), h("td", { class: "small" }, String(m.advice || ""))))))),
      (ev.gaps || []).length ? h("div", null, h("h3", null, "缺口与补法"), h("ul", { class: "mock-ul" }, ev.gaps.map(g => h("li", null, h("b", null, String(g.gap || "")), "：", String(g.why || ""), h("div", { class: "small" }, "补法：" + String(g.plan || "")))))) : "",
      arrStr(ev.plan, 6).length ? h("div", { class: "callout blue" }, h("b", null, "最该先准备"), h("ol", { class: "mock-ul" }, arrStr(ev.plan, 6).map(t => h("li", null, t)))) : ""));
    const toMock = () => { LS.set("tiyan:mock:preset", { type: "mixed", count: 8, focus: `按这份目标岗位 JD 面试（全栈方向）：${clip(jd.value.replace(/\s+/g, " "), 600)}。重点考察：${(ev.gaps || []).map(g => g.gap).join("、")}；优先问这些题：${qs.slice(0, 8).map(q => q.q).join(" / ")}` }); go("mock"); };
    box.append(h("section", { class: "stack" }, h("div", { class: "spread" }, h("h2", null, `会被问到的题（${qs.length}）`), h("button", { class: "btn primary sm", type: "button", onclick: toMock }, "带着这份 JD 去模拟面试 →")),
      ...cats.map(cat => h("section", { class: "panel" }, h("div", { class: "spread" }, h("h3", null, cat), FS_CAT_LINK[cat] ? h("a", { class: "small", href: "#" + FS_CAT_LINK[cat] }, "去练这块 →") : ""),
        ...qs.filter(q => q.cat === cat).map(q => fsJDQuestion(q))))));
  };
  fsLive(box, draw);
  draw();
  return fsPage("fs-jd", "简历 × JD：会被问什么、哪里还缺", "贴上目标岗位 JD 和你的简历：逐条对照 JD 要求看简历里有没有证据，列出缺口和补法，再结合你的真实项目出一套 24–30 题。每题可以直接作答，AI 按得分点打分；也可以带着这份 JD 去模拟面试。", box);
}
function fsJDQuestion(q) {
  const key = String(q.id || q.q).slice(0, 40), path = ["jdq", key], jk = "jdq:" + key, r = FS.at(path) || {};
  const d = h("details", { class: "qa", open: !!(r.ans || r.ev) }, h("summary", null, h("span", { class: "pill todo" }, String(q.level || "")), " ", String(q.q || ""), r.ev ? h("span", { class: "small num" }, `　${r.ev.score} 分`) : ""));
  const ta = fsTa("fs-jdq-" + key.replace(/\W/g, "_"), r.ans, v => FS.patch(path.concat("ans"), v), 100);
  const [vb, vs] = fsVoice(ta);
  const ask = () => {
    if (ta.value.trim().length < 10) { toast("先答几句"); return; }
    fsJob(jk, `你是资深面试官，按 JD 面试候选人。
${SD_COACH_RULE}
【问题】${q.q}\n【为什么问】${q.why || ""}\n【得分点】${(q.points || []).map((p, k) => k + ". " + p).join("；")}
【候选人简历（节选）】${clip(LS.get("tiyan:mock:resume", ""), 2500)}
【他的回答】${ta.value}
评分档位：9–10 全部得分点、有数据和取舍；7–8.5 基本到位；5–6.5 一半；3–4.5 大部分缺失。项目题要看是否说清自己做了什么、为什么、结果和数据。
只返回 JSON：{"score": 7, "hit": [0, 1], "verdict": "一句话", "followup": "你会接着追问的一句话", "better": "更好的回答（结合他的简历，像真人口述，150–300 字，不编造经历）", ${SD_COACH_JSON}}`, path);
  };
  d.append(h("div", { class: "small muted" }, "为什么会问：" + String(q.why || "")), arrStr(q.followups, 4).length ? h("div", { class: "small faint" }, "可能追问：" + arrStr(q.followups, 4).join(" / ")) : "", ta,
    h("div", { class: "row" }, h("button", { class: "btn sm", type: "button", disabled: !!FS_JOBS[jk], onclick: ask }, r.ev ? "改完了，重新打分" : "提交，让 AI 打分"), vb, vs),
    fsEvalBox(r, jk, ask, (b, ev) => b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""),
      h("ul", { class: "ex-points sd-fields" }, (q.points || []).map((p, k) => { const hit = (ev.hit || []).map(Number).includes(k); return h("li", { class: hit ? "hit" : "miss" }, h("b", null, hit ? "答到" : "漏了"), h("span", null, String(p))); })),
      ev.followup ? h("div", { class: "callout blue" }, h("b", null, "面试官会追问　"), String(ev.followup)) : "", ev.better ? h("details", { class: "qa", open: true }, h("summary", null, "更好的回答"), mdEl(String(ev.better), "small")) : "", coachEl(ev))));
  return d;
}
