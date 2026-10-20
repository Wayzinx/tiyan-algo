// ---------- 我的数据：备份 / 恢复全部进度、数据去向说明、材料脱敏 ----------
const DATA_GROUPS = [
  ["算法题进度与笔记", k => k === "tiyan:docs" || k.startsWith("tiyan:draft:")],
  ["AI 知识练习与错题", k => /^tiyan:(ex|ex:days|daily|exdraft:|read:|sec:|sectab:)/.test(k)],
  ["手写实战", k => k.startsWith("tiyan:lab:")],
  ["模拟面试（材料、项目卡、记录）", k => k.startsWith("tiyan:mock:")],
  ["项目实战", k => k.startsWith("tiyan:cap")],
  ["我的笔记", k => k === "tiyan:kb:docs"],
  ["偏好设置", k => /^tiyan:(rate|narrate|dsconf)$/.test(k)],
];
const SECRET_KEYS = ["tiyan:dskey", "tiyan:pw"];
function lsKeys() { try { return Object.keys(localStorage).filter(k => k.startsWith("tiyan:")); } catch (e) { return []; } }
function exportAll() {
  const data = {};
  for (const k of lsKeys()) if (!SECRET_KEYS.includes(k)) { try { data[k] = localStorage.getItem(k); } catch (e) { /* ignore */ } }
  return { app: "tiyan", version: 2, at: Date.now(), data };
}
function downloadFile(name, text, type = "application/json") {
  const a = h("a", { href: URL.createObjectURL(new Blob([text], { type })), download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
function importAll(obj, mode) {
  if (!obj || obj.app !== "tiyan") throw new Error("不是题眼导出的备份文件");
  let n = 0;
  if (obj.version === 1 && obj.docs) {       // 旧版只导出了算法进度
    const docs = LS.get("tiyan:docs", {});
    for (const [k, d] of Object.entries(obj.docs)) { if (mode === "merge" && docs[k] && (docs[k].lastAt || 0) > (d.lastAt || 0)) continue; docs[k] = d; n++; }
    LS.set("tiyan:docs", docs);
  } else {
    for (const [k, v] of Object.entries(obj.data || {})) {
      if (!k.startsWith("tiyan:") || SECRET_KEYS.includes(k)) continue;
      if (mode === "merge" && localStorage.getItem(k) != null && /^tiyan:(docs|ex|lab:stat|mock:sessions)$/.test(k)) {
        try { localStorage.setItem(k, JSON.stringify(mergeJson(k, JSON.parse(localStorage.getItem(k)), JSON.parse(v)))); n++; continue; } catch (e) { /* 合并失败就覆盖 */ }
      }
      try { localStorage.setItem(k, v); n++; } catch (e) { throw new Error("浏览器存储空间不够了"); }
    }
  }
  Store.docs = LS.get("tiyan:docs", {}); applyDocs();
  return n;
}
function mergeJson(k, cur, inc) {
  if (k === "tiyan:mock:sessions") { const ids = new Set(cur.map(s => s.id)); return cur.concat(inc.filter(s => !ids.has(s.id))).sort((a, b) => a.at - b.at).slice(-30); }
  const out = Object.assign({}, cur);
  for (const [id, v] of Object.entries(inc)) { const c = out[id]; if (!c || (v && (v.at || v.lastAt || 0) > (c.at || c.lastAt || 0))) out[id] = v; }
  return out;
}

// ----- 脱敏 -----
const PII_RULES = [
  ["手机号", /(?<!\d)1[3-9]\d{9}(?!\d)/g, "[手机号]"],
  ["邮箱", /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, "[邮箱]"],
  ["身份证号", /(?<!\d)[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)/g, "[身份证号]"],
  ["银行卡号", /(?<!\d)\d{16,19}(?!\d)/g, "[银行卡号]"],
  ["座机", /(?<!\d)0\d{2,3}-\d{7,8}(?!\d)/g, "[电话]"],
  ["网址", /https?:\/\/[^\s)）]+/g, "[链接]"],
];
function findPII(text) {
  const hits = [];
  let t = String(text || "");
  for (const [name, re, rep] of PII_RULES) { let n = 0; t = t.replace(re, () => { n++; return rep; }); if (n) hits.push([name, n]); }
  return hits;
}
function redactText(text, words) {
  let out = String(text || ""), n = 0;
  for (const [, re, rep] of PII_RULES) out = out.replace(re, () => { n++; return rep; });
  for (const w of (words || []).map(s => s.trim()).filter(s => s.length >= 2)) {
    const re = new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
    out = out.replace(re, () => { n++; return "[已隐去]"; });
  }
  return [out, n];
}
// 脱敏面板：给一个 textarea 用
function redactPanel(ta, onChange) {
  const words = h("input", { id: "redact-words", placeholder: "还要隐去的词，用逗号分隔：比如你的姓名、公司名、内部项目名", value: LS.get("tiyan:mock:redactwords", ""), style: "flex:1;min-width:200px;padding:6px 9px;border:1px solid var(--line);border-radius:6px;background:var(--paper)" });
  words.addEventListener("input", () => LS.set("tiyan:mock:redactwords", words.value));
  const scan = h("span", { class: "small" });
  const btn = h("button", { class: "btn sm", type: "button" }, "一键脱敏");
  const refresh = () => {
    const hits = findPII(ta.value);
    scan.textContent = hits.length ? "检测到可能的个人信息：" + hits.map(([k, n]) => `${k} ${n} 处`).join("、") : (ta.value.trim() ? "没检测到手机号、邮箱、证件号这类信息。" : "");
    scan.style.color = hits.length ? "var(--red)" : "var(--ink-3)";
  };
  btn.addEventListener("click", () => {
    const [out, n] = redactText(ta.value, words.value.split(/[,，、\n]/));
    ta.value = out; onChange && onChange();
    toast(n ? `已替换 ${n} 处` : "没有需要替换的内容");
    refresh();
  });
  ta.addEventListener("input", () => { clearTimeout(ta._rt); ta._rt = setTimeout(refresh, 400); });
  refresh();
  return h("div", { class: "stack", style: "gap:6px" }, h("div", { class: "row" }, words, btn), scan);
}

function viewData() {
  const keys = lsKeys();
  const size = keys.reduce((n, k) => { try { return n + (localStorage.getItem(k) || "").length; } catch (e) { return n; } }, 0);
  const rows = DATA_GROUPS.map(([name, test]) => {
    const ks = keys.filter(test);
    const sz = ks.reduce((n, k) => n + (localStorage.getItem(k) || "").length, 0);
    return h("tr", null, h("td", null, name), h("td", { class: "num" }, ks.length ? `${ks.length} 项` : "—"), h("td", { class: "num faint" }, sz ? `${Math.max(1, Math.round(sz / 1024))} KB` : ""));
  });
  const status = h("div", { class: "small muted" });
  const exp = h("button", { class: "btn primary sm", type: "button" }, "导出全部进度");
  exp.addEventListener("click", () => { downloadFile(`题眼备份-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(exportAll())); status.textContent = "已导出。备份里不包含 DeepSeek key 和访问密码。"; });
  const file = h("input", { type: "file", id: "restore-file", accept: "application/json,.json", hidden: true });
  let mode = "merge";
  const seg = h("div", { class: "seg" }, [["merge", "合并（保留较新的）"], ["replace", "覆盖"]].map(([v, t]) => { const b = h("button", { type: "button", class: v === mode ? "on" : "" }, t); b.addEventListener("click", () => { mode = v; $$("button", seg).forEach(x => x.classList.remove("on")); b.classList.add("on"); }); return b; }));
  const imp = h("button", { class: "btn sm", type: "button", onclick: () => file.click() }, "从备份恢复");
  file.addEventListener("change", async () => {
    const f = file.files && file.files[0]; file.value = "";
    if (!f) return;
    try { const n = importAll(JSON.parse(await f.text()), mode); toast(`已恢复 ${n} 项`); render(); }
    catch (e) { status.textContent = "恢复失败：" + ((e && e.message) || e); }
  });
  let armed = false;
  const clear = h("button", { class: "btn ghost sm", type: "button" }, "清空这台设备上的全部数据");
  clear.addEventListener("click", () => {
    if (!armed) { armed = true; clear.textContent = "确定清空？建议先导出备份"; clear.classList.add("red"); setTimeout(() => { armed = false; clear.textContent = "清空这台设备上的全部数据"; clear.classList.remove("red"); }, 4000); return; }
    for (const k of lsKeys()) LS.del(k);
    toast("已清空"); location.hash = "#home"; location.reload();
  });
  return h("div", { class: "page", style: "max-width:960px" },
    h("section", { class: "hero" }, h("div", { class: "eyebrow" }, "我的数据"), h("h1", null, "数据存在哪、发给了谁"),
      h("p", { class: "lede" }, "这个网站没有自己的服务器。你的进度、练习记录、简历材料都只存在当前浏览器里；换设备或清理浏览器数据前，先在这里导出备份。")),
    h("section", { class: "panel" }, h("h2", null, "存在这个浏览器里的数据"), h("div", { class: "scroll-x" }, h("table", { class: "ptable" }, h("thead", null, h("tr", null, h("th", null, "类别"), h("th", null, "条目"), h("th", null, "大小"))), h("tbody", null, rows))),
      h("p", { class: "small faint" }, `合计约 ${Math.round(size / 1024)} KB。DeepSeek key ${AI.key() ? "已保存（不会出现在备份里）" : "未保存"}。`),
      h("div", { class: "row" }, exp, imp, seg, file), status, h("div", { class: "sep" }), h("div", { class: "row" }, clear)),
    h("section", { class: "panel" }, h("h2", null, "哪些内容会发给 DeepSeek"),
      h("ul", { class: "signals" }, [
        "你主动点 AI 功能时（提问、批改、阅卷、出题、模拟面试、项目评审）：当前题目、你写的代码和回答、真实运行结果，以及和问题相关的站内资料片段。",
        "模拟面试：简历 / 项目材料和项目卡里与当前问题相关的部分。",
        "不会发送：你的进度统计、其他题目的代码、DeepSeek key 以外的任何凭证。不点 AI 功能就不会发送任何内容。",
        "DeepSeek 在服务端怎么保存和使用数据，以它的隐私政策为准，这个网站无法控制。含公司内部信息或个人隐私的材料，先脱敏再用。",
      ].map(t => h("li", null, h("span", null, t))))),
    h("section", { class: "panel" }, h("h2", null, "代码运行"), h("p", { class: "muted" }, "判题、实战题、Python 例子都在你的浏览器里用 Pyodide 运行，代码不会上传。PDF 和 Word 也在浏览器里本地解析。")));
}
