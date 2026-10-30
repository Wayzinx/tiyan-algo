// ---------- 面经：导入本机的面试复盘文件夹（报告 / 对话稿 / 题库 / 弱项 / 话术），在浏览器里复练 ----------
// 数据只存在这台电脑的浏览器（IndexedDB），不上传、不进网站仓库；AI 点评时才把相关片段发给 DeepSeek。
const IVDB = {
  db: null,
  open() { return this.db || (this.db = new Promise((res, rej) => { const r = indexedDB.open("tiyan-iv", 1); r.onupgradeneeded = () => r.result.createObjectStore("kv"); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); })); },
  async tx(mode, fn) { const db = await this.open(); return new Promise((res, rej) => { const t = db.transaction("kv", mode), q = fn(t.objectStore("kv")); t.oncomplete = () => res(q && q.result); t.onerror = () => rej(t.error); }); },
  get(k) { return this.tx("readonly", s => s.get(k)); },
  set(k, v) { return this.tx("readwrite", s => s.put(v, k)); },
  del(k) { return this.tx("readwrite", s => s.delete(k)); },
};
let IV = null;   // 已导入的数据（内存里一份）；false = 还没导入
async function ivLoad() { if (IV === null) { try { IV = (await IVDB.get("bundle")) || false; } catch (e) { IV = false; } } return IV; }
const IVS = {   // 练习记录（小，放 localStorage）
  get() { return LS.get("tiyan:iv", {}); },
  at(path) { let o = this.get(); for (const k of path) o = o && o[k]; return o; },
  patch(path, val) { const a = this.get(); let o = a; for (const k of path.slice(0, -1)) o = o[k] = o[k] || {}; o[path[path.length - 1]] = val; LS.set("tiyan:iv", a); },
};
const IV_JOBS = {};
let IV_REDRAW = null;
function ivJob(key, prompt, path, onDone) {
  if (IV_JOBS[key]) return;
  if (!AI.ok()) { toast(aiErr({ code: S.ai === "needkey" ? "need_key" : "unavailable" })); if (S.ai === "needkey") openKeyDialog(); return; }
  IV_JOBS[key] = true; IVS.patch(path.concat("err"), ""); if (IV_REDRAW) IV_REDRAW();
  AI.ask(prompt, { json: true, tier: "default" })
    .then(r => { IVS.patch(path.concat("ev"), r); if (onDone) onDone(r); })
    .catch(e => IVS.patch(path.concat("err"), e && e.code ? aiErr(e) : "评估失败：" + ((e && e.message) || e)))
    .finally(() => { delete IV_JOBS[key]; if (IV_REDRAW) IV_REDRAW(); });
}

// ----- 解析面试复盘的文件 -----
const IV_FILES = ["report.md", "followups.md", "transcript.json", "context.md", "meta.json"];
function ivParseSession(dir, f) {
  const m = /^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})_(.*)$/.exec(dir) || [];
  const rep = f["report.md"] || "";
  const ctx = {};
  for (const line of (f["context.md"] || "").split("\n")) { const k = /^(公司|岗位|轮次)[：:]\s*(.*)$/.exec(line.trim()); if (k) ctx[k[1]] = k[2].trim(); }
  const jd = ((f["context.md"] || "").split(/JD[：:]/)[1] || "").trim();
  const overall = (/整体\s*\**\s*([\d.]+)\s*\/\s*5/.exec(rep) || [])[1];
  const oneLine = ((/一句话结论\**[：:]\**\s*(.*)/.exec(rep) || [])[1] || "").replace(/\*\*/g, "");
  // 逐题：### Q2 · 类别 · 题目 `[00:02:46]` — 3/5；#### Q2.1 是追问
  const lines = rep.split("\n"), qs = [];
  let cur = null;
  const close = () => { if (cur) { cur.body = cur.body.join("\n").trim(); qs.push(cur); cur = null; } };
  for (const line of lines) {
    const q = /^(#{3,4})\s+(Q[\d.]+)\s*·\s*(.*)$/.exec(line);
    if (q) {
      close();
      let rest = q[3];
      const score = (/—\s*([\d.]+)\s*\/\s*5\s*$/.exec(rest) || [])[1];
      const ts = (/`\[(\d\d:\d\d:\d\d)\]`/.exec(rest) || [])[1] || "";
      rest = rest.replace(/`\[\d\d:\d\d:\d\d\]`/, "").replace(/—\s*[\d.]+\s*\/\s*5\s*$/, "").trim();
      const parts = rest.split(/\s*·\s*/);
      cur = { n: q[2], level: q[1].length, cat: parts.length > 1 ? parts[0] : "", title: parts.length > 1 ? parts.slice(1).join(" · ") : parts[0], ts, score: score != null ? Number(score) : null, body: [] };
      continue;
    }
    if (cur && /^#{1,3}\s/.test(line)) { close(); continue; }
    if (cur) cur.body.push(line);
  }
  close();
  const sec = name => { const i = rep.indexOf("## " + name); if (i < 0) return ""; const j = rep.indexOf("\n## ", i + 3); return rep.slice(rep.indexOf("\n", i) + 1, j < 0 ? undefined : j).trim(); };
  let turns = [];
  try { const t = JSON.parse(f["transcript.json"] || "{}"); turns = (t.turns || t.segments || []).map(x => ({ s: x.speaker || "", t: Math.round(x.start || 0), x: x.text || "" })); } catch (e) { turns = []; }
  const title = (/^#\s+(.*)$/m.exec(rep) || [])[1] || m[4] || dir;
  return {
    id: dir, date: m[1] || "", time: m[2] ? `${m[2]}:${m[3]}` : "", name: m[4] || dir, title: title.replace(/^面试复盘\s*·\s*/, ""),
    company: ctx["公司"] || "", role: ctx["岗位"] || "", round: ctx["轮次"] || "", jd,
    overall: overall != null ? Number(overall) : null, oneLine, report: rep, followups: f["followups.md"] || "",
    fix3: sec("最该改的 3 件事"), prep: sec("下次面试前的准备清单"), questions: qs.map(q => Object.assign(q, { id: dir + "#" + q.n })), turns,
  };
}
function ivTable(md, head) {   // 取 markdown 里第一张以 head 开头的表格
  const lines = md.split("\n"), i = lines.findIndex(l => l.trim().startsWith("|") && l.includes(head));
  if (i < 0) return [];
  const cols = lines[i].split("|").slice(1, -1).map(s => s.trim()), rows = [];
  for (let k = i + 2; k < lines.length && lines[k].trim().startsWith("|"); k++) {
    const c = lines[k].split("|").slice(1, -1).map(s => s.trim());
    rows.push(Object.fromEntries(cols.map((h0, j) => [h0, (c[j] || "").replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")])));
  }
  return rows;
}
async function ivReadFolder(entries) {   // entries：[{path: "dir/file", file: () => Promise<File>}]
  const by = {}, root = {};
  for (const e of entries) {
    const parts = e.path.split("/").filter(Boolean);
    if (parts.length !== 2) continue;
    const [d, name] = parts;
    if (d.startsWith("_")) { if (["_bank/questions.md", "_bank/weaknesses.md", "_qa/qa_bank.json", "_profile/resume.txt"].includes(d + "/" + name)) root[d + "/" + name] = e; continue; }
    if (/^\d{4}-\d{2}-\d{2}_/.test(d) && IV_FILES.includes(name)) (by[d] = by[d] || {})[name] = e;
  }
  const text = async e => e ? (await e.file()).text() : "";
  const sessions = [];
  for (const d of Object.keys(by).sort()) {
    if (!by[d]["report.md"]) continue;
    const f = {};
    for (const n of IV_FILES) f[n] = await text(by[d][n]);
    sessions.push(ivParseSession(d, f));
  }
  let qa = null;
  try { const t = await text(root["_qa/qa_bank.json"]); qa = t ? JSON.parse(t) : null; } catch (e) { qa = null; }
  const weakMd = await text(root["_bank/weaknesses.md"]), bankMd = await text(root["_bank/questions.md"]);
  return { importedAt: Date.now(), sessions, qa, weakMd, bankMd, weak: ivTable(weakMd, "弱项"), bank: ivTable(bankMd, "题目"), resume: await text(root["_profile/resume.txt"]) };
}
async function ivEntriesFromHandle(dir) {
  const out = [];
  for await (const [name, h] of dir.entries()) {
    if (h.kind !== "directory" || name.startsWith(".")) continue;
    for await (const [fn, fh] of h.entries()) if (fh.kind === "file") out.push({ path: name + "/" + fn, file: () => fh.getFile() });
  }
  return out;
}
function ivEntriesFromFiles(files) {
  return [...files].map(f => { const p = (f.webkitRelativePath || f.name).split("/"); return { path: p.slice(-2).join("/"), file: async () => f }; });
}
async function ivImport(entries, status) {
  status("读取中……");
  const b = await ivReadFolder(entries);
  if (!b.sessions.length && !b.qa) throw new Error("没在这个文件夹里找到面试复盘（应该是包含「日期_时间_公司-岗位」子文件夹的 Interviews 目录）");
  await IVDB.set("bundle", b);
  IV = b;
  return b;
}
async function ivPickFolder(status) {
  if (window.showDirectoryPicker) {
    const dir = await window.showDirectoryPicker({ id: "interviews", mode: "read" });
    try { await IVDB.set("dir", dir); } catch (e) { /* 有的浏览器存不了目录句柄，下次再选一次就行 */ }
    return ivImport(await ivEntriesFromHandle(dir), status);
  }
  return null;
}
async function ivResync(status) {
  const dir = await IVDB.get("dir").catch(() => null);
  if (!dir) return null;
  if ((await dir.queryPermission({ mode: "read" })) !== "granted" && (await dir.requestPermission({ mode: "read" })) !== "granted") return null;
  return ivImport(await ivEntriesFromHandle(dir), status);
}

// ----- 页面骨架 -----
const IV_TABS = [["iv", "总览"], ["iv-sessions", "场次复盘"], ["iv-practice", "真题再练"], ["iv-qa", "话术题库"], ["iv-weak", "弱项专练"]];
function ivPage(cur, title, lede, ...body) {
  return h("div", { class: "page wide iv-page" }, h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "面经 · 只在本机"), h("h1", null, title), lede ? h("p", { class: "lede" }, lede) : ""),
    h("nav", { class: "page-tabs" }, IV_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t))), ...body);
}
function viewIV({ sub }) {
  const root = h("div");
  const paint = () => { root.textContent = ""; root.append(ivRoute(sub || "")); };
  if (IV === null) { root.append(h("div", { class: "page" }, h("div", { class: "thinking" }, "读取本机的面经数据……"))); ivLoad().then(paint); }
  else paint();
  return root;
}
function ivRoute(sub) {
  if (!IV) return ivImportPage();
  if (sub === "import") return ivPage("iv", "重新导入", null, ivImportPage(true));
  if (sub === "sessions") return ivSessions();
  if (sub.startsWith("s-")) { const s = IV.sessions[Number(sub.slice(2))]; if (s) return ivSession(s, Number(sub.slice(2))); }
  if (sub === "practice") return ivPractice();
  if (sub === "qa") return ivQA();
  if (sub.startsWith("qa-")) { const it = IV.qa && IV.qa.items.find(x => x.id === sub.slice(3)); if (it) return ivQAItem(it); }
  if (sub === "weak") return ivWeak();
  return ivOverview();
}
function ivProvide(where, ctx) {
  Buddy.provide({ where: () => "面经 › " + where, context: () => BUDDY_SYS.split("\n")[0] + "\n现在学习者在「面经」模块，看的是他自己真实面试的复盘数据（只在本机）。\n" + ctx() + (IV && IV.resume ? "\n【他的简历（节选）】\n" + clip(IV.resume, 1500) : "") });
  onLeave(() => Buddy.provide(null));
}
const ivScore = (s, max = 5) => s == null ? h("span", { class: "faint" }, "—") : h("span", { class: "pill " + (s / max >= .7 ? "passed" : s / max >= .5 ? "trying" : "due") }, `${s}/${max}`);
const ivAllQ = () => IV.sessions.flatMap(s => s.questions.map(q => Object.assign({ sid: s.id, sname: s.name, date: s.date }, q)));

// ----- 导入页 -----
function ivImportPage(again) {
  const status = h("div", { class: "small muted" });
  const input = h("input", { type: "file", webkitdirectory: true, multiple: true, hidden: true });
  const done = b => { toast(`导入了 ${b.sessions.length} 场面试${b.qa ? `、${b.qa.items.length} 道话术题` : ""}`); go("iv"); render(); };
  const fail = e => { if (e && e.name === "AbortError") { status.textContent = ""; return; } status.textContent = "导入失败：" + ((e && e.message) || e); };
  input.addEventListener("change", async () => { try { done(await ivImport(ivEntriesFromFiles(input.files), t => { status.textContent = t; })); } catch (e) { fail(e); } input.value = ""; });
  const pick = async () => { try { const b = await ivPickFolder(t => { status.textContent = t; }); if (b) done(b); else input.click(); } catch (e) { fail(e); } };
  const panel = h("section", { class: "panel" }, h("h2", null, again ? "重新导入" : "导入你的面试复盘"),
    h("p", null, "选择本机的 ", h("code", null, "Interviews"), " 文件夹（面试复盘工具存数据的地方，里面是「日期_时间_公司-岗位」的子文件夹）。会读取每场的复盘报告、逐题得分、对话稿、追问记录，以及 ", h("code", null, "_bank"), " 下的题库和弱项档案、", h("code", null, "_qa/qa_bank.json"), " 里的话术题库。录音文件不读。"),
    h("div", { class: "callout blue" }, h("b", null, "只在本机　"), "文件在你的浏览器里读取，存在这台电脑的浏览器数据库里，不会上传，也不会出现在网站上；换浏览器或换电脑需要重新导入。只有你点「让 AI 点评」时，才会把那一道题的相关片段发给 DeepSeek（用你自己的 key）。Chrome 选文件夹时可能提示“上传”，其实只是在本地读取。"),
    h("div", { class: "row" }, h("button", { class: "btn primary", type: "button", onclick: pick }, "选择 Interviews 文件夹"), input, status),
    h("details", { class: "qa" }, h("summary", null, "话术题库从哪来"), h("p", { class: "small" }, "飞书上的「面试题库与优化话术」可以用本机脚本同步成 ", h("code", null, "_qa/qa_bank.json"), "：在终端运行 ", h("code", null, "python3 ~/Interviews/_qa/sync_lark_qa.py"), "，再回来重新导入。")));
  return again ? panel : ivPage("iv", "面经：把每一场真实面试变成复练材料", "导入面试复盘的数据后：看每场的复盘和对话稿，把低分真题再答一遍让 AI 对比上次，按话术题库自测，按弱项专练。", panel);
}

// ----- 总览 -----
function ivOverview() {
  ivProvide("总览", () => `【已导入】${IV.sessions.length} 场：${IV.sessions.map(s => `${s.date} ${s.name} 整体 ${s.overall ?? "?"}/5`).join("；")}\n【弱项】${IV.weak.slice(0, 6).map(w => `${w["弱项"]}（${w["出现次数"]} 次）`).join("；")}`);
  const qs = ivAllQ(), prac = IVS.get().p || {};
  const due = ivDue(qs, prac).slice(0, 8);
  const ss = IV.sessions.filter(s => s.overall != null);
  const last = IV.sessions[IV.sessions.length - 1];
  const resync = h("button", { class: "btn sm", type: "button" }, "重新同步");
  resync.addEventListener("click", async () => { try { const b = await ivResync(() => {}); if (b) { toast(`已同步：${b.sessions.length} 场`); render(); } else go("iv-import"); } catch (e) { toast("同步失败：" + ((e && e.message) || e)); } });
  const clear = h("button", { class: "btn ghost sm", type: "button" }, "清除本机数据");
  clear.addEventListener("click", async () => { if (!clear.dataset.sure) { clear.dataset.sure = "1"; clear.textContent = "再点一次确认清除"; return; } await IVDB.del("bundle"); await IVDB.del("dir").catch(() => {}); IV = false; toast("已清除"); render(); });
  return ivPage("iv", "面经总览", null,
    h("section", { class: "panel" }, h("div", { class: "spread" }, h("div", null, h("b", null, `${IV.sessions.length} 场面试 · ${qs.length} 道真题`), IV.qa ? `　· ${IV.qa.items.length} 道话术题` : "", h("div", { class: "small faint" }, `导入于 ${new Date(IV.importedAt).toLocaleString()}　数据只在这台电脑的浏览器里`)),
      h("div", { class: "row" }, resync, h("a", { class: "btn ghost sm", href: "#iv-import" }, "换个文件夹导入"), clear))),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("h2", null, "每场整体得分"), ss.length ? h("div", { class: "iv-bars" }, ss.map(s => h("a", { class: "iv-bar", href: "#iv-s-" + IV.sessions.indexOf(s), title: `${s.date} ${s.name}：${s.overall}/5` }, h("i", { style: `height:${s.overall / 5 * 100}%` }), h("span", { class: "num" }, s.overall), h("small", null, s.date.slice(5))))) : h("p", { class: "muted" }, "还没有带分数的场次。")),
      h("section", { class: "panel" }, h("div", { class: "spread" }, h("h2", null, "弱项 Top"), h("a", { class: "small", href: "#iv-weak" }, "去专练 →")),
        IV.weak.length ? h("ul", { class: "mock-ul" }, IV.weak.slice().sort((a, b) => (parseInt(b["出现次数"]) || 0) - (parseInt(a["出现次数"]) || 0)).slice(0, 5).map(w => h("li", null, h("b", null, w["弱项"]), h("span", { class: "small faint" }, `　${w["出现次数"]} 次 · 最近 ${w["最近日期"]}${w["状态"] ? " · " + clip(w["状态"], 24) : ""}`)))) : h("p", { class: "muted" }, "没有导入弱项档案。"))),
    h("section", { class: "panel" }, h("div", { class: "spread" }, h("h2", null, "今天先练这几道"), h("a", { class: "small", href: "#iv-practice" }, "全部真题 →")), h("p", { class: "small muted" }, "低分题和很久没练的题排在前面：答过之后按得分隔 1 / 3 / 7 天再出现。"),
      due.length ? h("ul", { class: "mock-ul" }, due.map(q => h("li", null, h("a", { href: "#iv-practice", onclick: () => LS.set("tiyan:iv:cur", q.id) }, q.title), "　", ivScore(q.score), h("span", { class: "small faint" }, `　${q.date} ${q.sname}`)))) : h("p", { class: "muted" }, "都练过了，过几天再来。")),
    last && last.fix3 ? h("section", { class: "panel" }, h("h2", null, `最近一场（${last.name}）最该改的 3 件事`), mdEl(last.fix3, "small")) : "");
}
function ivDue(qs, prac) {
  const now = Date.now(), DAY = 864e5;
  return qs.map(q => {
    const r = (prac[q.id] || []).slice(-1)[0];
    const base = q.score == null ? 3 : q.score;
    if (!r) return [q, -10 + base];                             // 没练过：低分优先
    const gap = r.score >= 8 ? 7 : r.score >= 6 ? 3 : 1;         // 练过：按上次得分安排间隔
    return [q, (r.at + gap * DAY - now) / DAY];
  }).filter(([, d]) => d <= 0).sort((a, b) => a[1] - b[1]).map(([q]) => q);
}

// ----- 场次复盘 -----
function ivSessions() {
  ivProvide("场次列表", () => IV.sessions.map(s => `${s.date} ${s.name}：${s.oneLine}`).join("\n"));
  return ivPage("iv-sessions", "场次复盘", null, h("div", { class: "hubs" }, IV.sessions.slice().reverse().map(s => h("a", { class: "panel hub", href: "#iv-s-" + IV.sessions.indexOf(s) },
    h("div", { class: "eyebrow" }, `${s.date} ${s.time}`), h("h2", null, s.name), h("p", { class: "small muted" }, clip(s.oneLine || "（没有一句话结论）", 90)),
    h("div", { class: "row" }, ivScore(s.overall), h("span", { class: "small faint" }, `${s.questions.length} 道题 · ${s.turns.length} 段对话`))))));
}
function ivSession(s, idx) {
  let tab = LS.get("tiyan:iv:stab", "report");
  const box = h("div", { class: "stack" });
  ivProvide(`场次 · ${s.name}`, () => `【这场面试】${s.date} ${s.name}\n【复盘报告】\n${clip(s.report, 6000)}`);
  const draw = () => {
    box.textContent = "";
    LS.set("tiyan:iv:stab", tab);
    const seg = h("div", { class: "seg" }, [["report", "复盘报告"], ["qs", `逐题 ${s.questions.length}`], ["talk", "对话稿"], ["fu", "追问记录"], ["ctx", "岗位信息"]].map(([k, t]) => h("button", { type: "button", class: k === tab ? "on" : "", onclick: () => { tab = k; draw(); } }, t)));
    box.append(h("section", { class: "panel" }, h("div", { class: "spread" }, h("div", { class: "row" }, ivScore(s.overall), h("span", { class: "small faint" }, `${s.date} ${s.time}`)), seg), s.oneLine ? h("div", { class: "callout blue" }, h("b", null, "一句话结论　"), s.oneLine) : ""));
    if (tab === "report") box.append(h("section", { class: "panel iv-md" }, mdEl(s.report.replace(/^#\s.*\n/, ""))));
    else if (tab === "qs") box.append(h("section", { class: "panel" }, ...s.questions.map(q => { const d = h("details", { class: "qa" + (q.level === 4 ? " iv-sub" : "") }, h("summary", null, h("span", { class: "mono small faint" }, q.n + " "), q.cat ? h("span", { class: "pill todo" }, q.cat) : "", " ", q.title, " ", ivScore(q.score), q.ts ? h("span", { class: "small faint num" }, " " + q.ts) : ""));
      d.append(mdEl(q.body, "small"), h("div", { class: "row" }, h("a", { class: "btn sm", href: "#iv-practice", onclick: () => LS.set("tiyan:iv:cur", q.id) }, "再答一次"))); return d; })));
    else if (tab === "talk") {
      const q = h("input", { class: "mock-input", style: "min-height:0;padding:8px 10px", placeholder: "在对话稿里搜索……", id: "iv-talk-q" });
      const list = h("div", { class: "iv-talk" });
      const fill = () => { const k = q.value.trim(); list.textContent = ""; for (const t of s.turns) { if (k && !t.x.includes(k)) continue; list.append(h("div", { class: "iv-turn" + (t.s === "我" ? " me" : "") }, h("span", { class: "small faint num" }, `${String(Math.floor(t.t / 60)).padStart(2, "0")}:${String(t.t % 60).padStart(2, "0")}`), h("b", null, t.s), h("span", null, t.x))); } if (!list.childNodes.length) list.append(h("p", { class: "muted" }, "没有匹配的对话。")); };
      q.addEventListener("input", fill); fill();
      box.append(h("section", { class: "panel" }, q, list));
    } else if (tab === "fu") box.append(h("section", { class: "panel iv-md" }, s.followups ? mdEl(s.followups) : h("p", { class: "muted" }, "这场没有追问记录。")));
    else box.append(h("section", { class: "panel" }, h("p", null, [["公司", s.company], ["岗位", s.role], ["轮次", s.round]].filter(x => x[1]).map(x => `${x[0]}：${x[1]}`).join("　")), s.jd ? mdEl(s.jd, "small") : h("p", { class: "muted" }, "没有记录 JD。")));
  };
  draw();
  return ivPage("iv-sessions", s.name, null, box, h("div", { class: "spread" }, idx > 0 ? h("a", { class: "btn ghost sm", href: "#iv-s-" + (idx - 1) }, "← 上一场") : h("span"), idx < IV.sessions.length - 1 ? h("a", { class: "btn sm", href: "#iv-s-" + (idx + 1) }, "下一场 →") : h("span")));
}

// ----- 真题再练：再答一遍，AI 对比上次 -----
let IV_LIB = null;
function ivLib() {
  if (IV_LIB && IV_LIB.v === IV.importedAt) return IV_LIB.lib;
  const items = (IV.qa ? IV.qa.items : []).map(x => ({ id: x.id, where: `话术 › ${x.id} ${x.title}`, text: [x.title, x.focus, x.last, x.answer].join("\n") }));
  IV_LIB = { v: IV.importedAt, lib: new Library(items) };
  return IV_LIB.lib;
}
function ivPrompt(q, ans, extra) {
  const hit = IV.qa ? ivLib().search(q.title + " " + q.body.slice(0, 200), 1)[0] : null;
  const qa = hit && IV.qa.items.find(x => x.id === hit.id);
  return `你是资深面试官兼面试教练。学习者在复练一道他真实面试里被问过的题，请对照他上次的表现，判断这次有没有进步。
${SD_COACH_RULE}
【题目】${q.title}${q.cat ? "（" + q.cat + "）" : ""}
【出处】${q.date} ${q.sname}，上次得分 ${q.score ?? "?"}/5
【上次的复盘（包括他当时怎么答的、问题在哪、更好的答法）】\n${clip(q.body, 3000)}
${qa ? `【他整理的优化话术（${qa.id} ${qa.title}）】\n${clip(qa.answer, 2000)}\n【追问预案】${qa.followups.map(f => f.q + " → " + f.a).join("；")}` : ""}
【他反复出现的弱项】${IV.weak.slice(0, 6).map(w => w["弱项"]).join("；")}
${IV.resume ? "【简历（节选）】" + clip(IV.resume, 1500) : ""}
${extra || ""}
【这次的回答】\n${ans}
只用他简历和复盘里真实存在的经历和数字，不要编造。评分档位（满分 10）：9–10 结论先行、结构清楚、有真实数字、经得起追问；7–8.5 基本到位；5–6.5 有内容但老问题还在；3–4.5 明显不足。
只返回 JSON：{"score": 7, "verdict": "一句话", "improved": ["相比上次进步的地方"], "still": ["上次的老问题这次还在的（对照弱项）"], "better": "更好的回答（像真人口述，150–300 字，用他的真实素材）", "followup": "面试官接下来最可能追问的一句话", ${SD_COACH_JSON}}`;
}
function ivEvalView(b, ev) {
  b.append(scoreLine(Number(ev.score) || 0, ev.verdict ? h("span", { class: "small" }, String(ev.verdict)) : ""),
    arrStr(ev.improved, 5).length ? h("div", null, h("h3", null, "比上次进步的"), h("ul", { class: "ex-points sd-fields" }, arrStr(ev.improved, 5).map(t => h("li", { class: "hit" }, h("b", null, "进步"), h("span", null, t))))) : "",
    arrStr(ev.still, 5).length ? h("div", null, h("h3", null, "老问题还在"), h("ul", { class: "ex-points sd-fields" }, arrStr(ev.still, 5).map(t => h("li", { class: "miss" }, h("b", null, "还在"), h("span", null, t))))) : "",
    ev.followup ? h("div", { class: "callout blue" }, h("b", null, "面试官会追问　"), String(ev.followup)) : "", ev.better ? h("details", { class: "qa", open: true }, h("summary", null, "更好的回答"), mdEl(String(ev.better), "small")) : "", coachEl(ev));
}
function ivPractice() {
  const all = ivAllQ(), box = h("div", { class: "stack" }), side = h("aside", { class: "panel sd-side" });
  let f = Object.assign({ cat: "", max: 5, only: "" }, LS.get("tiyan:iv:pf", {}));
  let cur = LS.get("tiyan:iv:cur", null);
  ivProvide("真题再练", () => { const q = all.find(x => x.id === cur); const r = q && IVS.at(["e", q.id]); return q ? `【当前真题】${q.title}（${q.date} ${q.sname}，上次 ${q.score}/5）\n【上次的复盘】\n${clip(q.body, 2500)}\n【他这次的回答】${(r && r.ans) || "（还没答）"}` : ""; });
  const draw = () => {
    const prac = IVS.get().p || {};
    const P = all.filter(q => (!f.cat || q.cat === f.cat) && (q.score == null || q.score <= f.max) && (f.only !== "new" || !prac[q.id]) && (f.only !== "due" || ivDue([q], prac).length));
    if (!P.find(q => q.id === cur)) cur = (ivDue(P, prac)[0] || P[0] || {}).id || null;
    LS.set("tiyan:iv:cur", cur); LS.set("tiyan:iv:pf", f);
    box.textContent = ""; side.textContent = "";
    const cats = [...new Set(all.map(q => q.cat).filter(Boolean))];
    const seg = (opts, val, set) => h("div", { class: "seg" }, opts.map(([v, t]) => h("button", { type: "button", class: val === v ? "on" : "", onclick: () => { set(v); draw(); } }, t)));
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, seg([[5, "全部"], [3, "≤3 分"], [2, "≤2 分"]], f.max, v => { f.max = v; }), seg([["", "全部"], ["due", "该复练的"], ["new", "没练过的"]], f.only, v => { f.only = v; })),
      h("div", { class: "row", style: "gap:6px" }, [""].concat(cats).map(c => h("button", { type: "button", class: "chip" + (f.cat === c ? " on" : ""), onclick: () => { f.cat = c; draw(); } }, c || "全部类别")))));
    side.append(h("div", { class: "eyebrow" }, `题目（${P.length}）`), h("ol", { class: "sd-order" }, P.map(q => { const r = (prac[q.id] || []).slice(-1)[0]; return h("li", { class: q.id === cur ? "on" : "" }, h("a", { href: "#iv-practice", onclick: e => { e.preventDefault(); cur = q.id; draw(); window.scrollTo(0, 0); } }, clip(q.title, 26)), h("span", { class: "small faint num" }, ` ${q.score ?? "-"}/5${r ? " → " + r.score + "/10" : ""}`)); })));
    const q = P.find(x => x.id === cur);
    if (!q) { box.append(h("section", { class: "panel" }, h("p", { class: "muted" }, "这个筛选下没有题。"))); return; }
    const path = ["e", q.id], jk = "iv:" + q.id, r = IVS.at(path) || {};
    const ta = fsTa("iv-ans-" + q.id.replace(/\W/g, "_"), r.ans, v => IVS.patch(path.concat("ans"), v), 150);
    ta.placeholder = "像在面试里一样回答（可以用语音输入）。先给结论，再讲做法和数字。";
    const [vb, vs] = fsVoice(ta);
    const ask = () => {
      if (ta.value.trim().length < 15) { toast("先答几句"); return; }
      ivJob(jk, ivPrompt(q, ta.value), path, ev => { const list = (IVS.get().p || {})[q.id] || []; IVS.patch(["p", q.id], list.concat([{ at: Date.now(), score: Number(ev.score) || 0 }]).slice(-10)); });
    };
    const evBox = h("div", { class: "stack sd-ai" });
    if (IV_JOBS[jk]) evBox.append(fsPending("AI 在对比你上次的回答……"));
    else if (r.err) evBox.append(fsErr(r.err, ask));
    else if (r.ev) ivEvalView(evBox, r.ev);
    const hist = prac[q.id] || [];
    box.append(h("section", { class: "panel" }, h("div", { class: "row" }, q.cat ? h("span", { class: "pill todo" }, q.cat) : "", h("span", { class: "small faint" }, `${q.date} ${q.sname}`), h("span", { class: "small" }, "上次 "), ivScore(q.score), hist.length ? h("span", { class: "small faint" }, "　复练：" + hist.map(x => x.score).join(" → ")) : ""),
      h("p", { class: "sd-prompt", style: "font-size:18px" }, q.title),
      h("details", { class: "qa" }, h("summary", null, "上次的复盘（先自己答，再展开看）"), mdEl(q.body, "small")),
      ta, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!IV_JOBS[jk], onclick: ask }, r.ev ? "改完了，重新点评" : "提交，让 AI 对比上次"), vb, vs), evBox));
  };
  IV_REDRAW = () => { const ae = document.activeElement, id = ae && box.contains(ae) && ae.id, y = window.scrollY; draw(); window.scrollTo(0, y); if (id) { const n = document.getElementById(id); if (n) n.focus({ preventScroll: true }); } };
  onLeave(() => { IV_REDRAW = null; });
  draw();
  return ivPage("iv-practice", "真题再练", "这些都是你真实被问过的题。先自己再答一遍，AI 对照当时的复盘看你这次哪里进步了、哪些老问题还在；答过的题按得分隔 1 / 3 / 7 天再排进「该复练的」。",
    h("div", { class: "sd-grid" }, box, side), h("div", { class: "row" }, h("button", { class: "btn sm", type: "button", onclick: () => { const low = ivAllQ().filter(q => q.score != null && q.score <= 2).slice(0, 10); LS.set("tiyan:mock:preset", { type: "project", count: Math.min(8, Math.max(4, low.length)), focus: "用我真实面试里答得不好的题来面：" + low.map(q => q.title).join(" / ") }); go("mock"); } }, "用低分真题模拟面试 →")));
}

// ----- 话术题库 -----
function ivQA() {
  ivProvide("话术题库", () => IV.qa ? IV.qa.items.map(x => `${x.id} ${x.title}`).join("\n") : "没有导入话术题库。");
  if (!IV.qa) return ivPage("iv-qa", "话术题库", null, h("section", { class: "panel" }, h("p", null, "还没有导入话术题库。在终端运行 ", h("code", null, "python3 ~/Interviews/_qa/sync_lark_qa.py"), " 把飞书上的题库同步到 ", h("code", null, "_qa/qa_bank.json"), "，再回「总览」点重新同步。")));
  const st = IVS.get().q || {};
  return ivPage("iv-qa", IV.qa.title, `同步于 ${IV.qa.synced_at}。每道题先自己答，再对照优化话术和追问预案，AI 会告诉你差在哪。`,
    ...IV.qa.overview.map((o, i) => h("details", { class: "qa sd-sec", open: i === 0 }, h("summary", null, o.title), h("div", { class: "iv-md" }, mdEl(o.md, "small")))),
    ...IV.qa.sections.filter(s => s.items.length || s.intro).map(s => h("section", { class: "panel" }, h("h2", null, s.title), s.items.length ? h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("tbody", null, s.items.map(id => { const x = IV.qa.items.find(y => y.id === id); const r = st[id]; return h("tr", { class: "sd-row", onclick: () => go("iv-qa-" + id) }, h("td", { class: "mono" }, id), h("td", null, h("a", { href: "#iv-qa-" + id }, x.title)), h("td", { class: "small muted" }, clip(x.source, 40)), h("td", { class: "num small" }, r && r.ev ? r.ev.score + " 分" : "—")); })))) : h("div", { class: "iv-md" }, mdEl(s.intro, "small")))));
}
function ivQAItem(x) {
  const box = h("div", { class: "stack" }), path = ["q", x.id], jk = "ivq:" + x.id;
  ivProvide(`话术 · ${x.id}`, () => { const r = IVS.at(path) || {}; return `【话术题】${x.id} ${x.title}\n考察点：${x.focus}\n上次的问题：${x.last}\n【他这次的回答】${r.ans || "（还没答）"}\n${r.ev || r.peek ? "【优化话术】" + x.answer : "【重要】他还没看话术：先引导，不要直接背给他。"}`; });
  const draw = () => {
    const r = IVS.at(path) || {}, open = !!(r.ev || r.peek);
    box.textContent = "";
    const ta = fsTa("iv-qa-" + x.id, r.ans, v => IVS.patch(path.concat("ans"), v), 150);
    const [vb, vs] = fsVoice(ta);
    const ask = () => {
      if (ta.value.trim().length < 15) { toast("先答几句"); return; }
      ivJob(jk, `你是面试教练。学习者在用自己整理的题库自测：先不看优化话术自己答，你对照话术和追问预案点评。
${SD_COACH_RULE}
【题目】${x.title}\n【考察点】${x.focus}\n【他上次面试的问题】${x.last}
【优化话术（参考，不要求一字不差，要点和数字对就行）】\n${clip(x.answer, 3000)}
【追问预案】${x.followups.map(f => f.q + " → " + f.a).join("；")}
${IV.resume ? "【简历（节选）】" + clip(IV.resume, 1200) : ""}
【这次的回答】\n${ta.value}
只返回 JSON：{"score": 7, "verdict": "一句话", "improved": ["做到了的要点"], "still": ["漏掉或说错的要点（对照话术和上次的问题）"], "better": "按话术整理的口述版（150–300 字）", "followup": "从追问预案里挑一个最可能接着问的", ${SD_COACH_JSON}}`, path);
    };
    const evBox = h("div", { class: "stack sd-ai" });
    if (IV_JOBS[jk]) evBox.append(fsPending()); else if (r.err) evBox.append(fsErr(r.err, ask)); else if (r.ev) ivEvalView(evBox, r.ev);
    box.append(h("section", { class: "panel" }, h("p", { class: "sd-prompt", style: "font-size:18px" }, `${x.id} · ${x.title}`),
      x.source ? h("div", { class: "small faint" }, "出处：" + x.source) : "", x.focus ? h("div", { class: "small" }, h("b", null, "考察点："), x.focus) : "", x.last ? h("div", { class: "callout" }, h("b", null, "上次的问题　"), x.last) : "",
      ta, h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", disabled: !!IV_JOBS[jk], onclick: ask }, r.ev ? "改完了，重新点评" : "提交，对照话术点评"), vb, vs, !open ? h("button", { class: "btn ghost sm", type: "button", onclick: () => { IVS.patch(path.concat("peek"), true); draw(); } }, "直接看话术") : ""), evBox),
      open ? h("section", { class: "panel" }, h("h2", null, "优化话术"), mdEl(x.answer || "（这题没有写话术）"), x.followups.length ? h("div", null, h("h3", null, "追问预案"), ...x.followups.map(f => { const d = h("details", { class: "qa" }, h("summary", null, f.q)); d.append(mdEl(f.a, "small")); return d; })) : "", ...x.extras.map(e => h("details", { class: "qa" }, h("summary", null, e.label), mdEl(e.md, "small")))) : "",
      (() => { const i = IV.qa.items.indexOf(x), p = IV.qa.items[i - 1], n = IV.qa.items[i + 1]; return h("div", { class: "spread" }, p ? h("a", { class: "btn ghost sm", href: "#iv-qa-" + p.id }, "← " + p.id) : h("span"), n ? h("a", { class: "btn sm", href: "#iv-qa-" + n.id }, n.id + " →") : h("span")); })());
  };
  IV_REDRAW = () => { const y = window.scrollY; draw(); window.scrollTo(0, y); };
  onLeave(() => { IV_REDRAW = null; });
  draw();
  return ivPage("iv-qa", `${x.id} ${x.title}`, null, box);
}

// ----- 弱项专练：按弱项挑出相关的真题，点评时专盯这个弱项 -----
function ivWeak() {
  ivProvide("弱项专练", () => "弱项：" + IV.weak.map(w => `${w["弱项"]}（${w["出现次数"]} 次）`).join("；"));
  if (!IV.weak.length) return ivPage("iv-weak", "弱项专练", null, h("section", { class: "panel" }, h("p", { class: "muted" }, "没有导入弱项档案（_bank/weaknesses.md）。")));
  const lib = new Library(ivAllQ().map(q => ({ id: q.id, where: q.title, text: q.title + "\n" + q.body })));
  const pick = w => lib.search(w["弱项"] + " " + (w["例子"] || ""), 3).map(c => ivAllQ().find(q => q.id === c.id)).filter(Boolean);
  return ivPage("iv-weak", "弱项专练", "每个弱项挑出几道最容易暴露它的真题。练的时候点评会专门盯这个弱项：比如“不主动报数字”，就看你这次有没有一开口就给出数据。",
    ...IV.weak.slice().sort((a, b) => (parseInt(b["出现次数"]) || 0) - (parseInt(a["出现次数"]) || 0)).map(w => h("section", { class: "panel" },
      h("div", { class: "spread" }, h("h2", null, w["弱项"]), h("span", { class: "small faint" }, `${w["出现次数"]} 次 · 最近 ${w["最近日期"]}${w["状态"] ? " · " + w["状态"] : ""}`)),
      w["例子"] ? h("p", { class: "small muted" }, "例子：" + clip(w["例子"], 220)) : "",
      h("div", { class: "row" }, pick(w).map(q => h("a", { class: "chip", href: "#iv-practice", onclick: () => { LS.set("tiyan:iv:cur", q.id); LS.set("tiyan:iv:pf", { cat: "", max: 5, only: "" }); } }, clip(q.title, 30)))),
      h("button", { class: "btn sm", type: "button", onclick: () => Buddy.ask(`我的弱项是「${w["弱项"]}」（出现 ${w["出现次数"]} 次，例子：${clip(w["例子"] || "", 300)}）。请从我真实面试里挑一道最容易暴露这个弱项的题考我，只出题；我答完你专门针对这个弱项点评，再给一个下次的固定开口模板。`, "弱项专练：" + clip(w["弱项"], 16)) }, "让小眼针对这个弱项考我"))));
}
