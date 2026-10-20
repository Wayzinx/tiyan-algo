"use strict";
// ---------- 数据 ----------
const BUILTIN = JSON.parse(document.getElementById("problems-data").textContent);
const HARNESS = document.getElementById("harness-src").textContent;
const PMAP = Object.fromEntries(PATTERNS.map(p => [p.key, p]));
const LEVEL = { easy: "简单", medium: "中等", hard: "困难" };
const DAY = 86400000;
const INTERVALS = [1, 3, 7, 15, 30];

const S = {
  progress: {}, custom: [], viz: {}, all: BUILTIN.slice(), byId: {},
  chats: {}, ws: null, py: "loading", ai: "unknown", store: "local",
  redo: null,
};

// ---------- 小工具 ----------
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  if (props) for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k in el && typeof v !== "string") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : String(c));
  }
  return el;
}
const ICONS = {
  play: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5v11l9-5.5z"/></svg>',
  pause: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M4 2.5h3v11H4zM9 2.5h3v11H9z"/></svg>',
  prev: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M3 3h2v10H3zM13 3v10L6 8z"/></svg>',
  next: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M11 3h2v10h-2zM3 3v10l7-5z"/></svg>',
  speak: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2.5 6h2.5l3.5-3v10L5 10H2.5z" fill="currentColor" stroke="none"/><path d="M11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.5a6 6 0 0 1 0 9"/></svg>',
  stop: '<svg viewBox="0 0 16 16" fill="currentColor"><rect x="3.5" y="3.5" width="9" height="9" rx="1.5"/></svg>',
  copy: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="8.5" height="8.5" rx="1.5"/><path d="M3 10.5V3.8C3 3.3 3.3 3 3.8 3h6.7"/></svg>',
  send: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M1.5 2.2 14.5 8l-13 5.8L3 8.6 9 8 3 7.4z"/></svg>',
  run: '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M4.5 2.5v11l8.5-5.5z"/></svg>',
  check: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8.5 6.5 12 13 4.5"/></svg>',
  back: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M10 3 5 8l5 5"/></svg>',
  image: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="2" y="3" width="12" height="10" rx="1.5"/><circle cx="6" cy="6.5" r="1.2"/><path d="m2.5 12 4-4 3 3 2-2 2.5 2.5"/></svg>',
};
const icon = n => h("span", { html: ICONS[n], style: "display:inline-flex" });

const LS = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* 存不了就算了 */ } },
  del(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } },
};

let toastTimer = null;
function toast(msg, ms = 2600) {
  let el = $(".toast");
  if (!el) { el = h("div", { class: "toast", role: "status" }); document.body.append(el); }
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, ms);
}

function copyText(text, btn) {
  const done = () => { if (btn) { const t = btn.textContent; btn.textContent = "已复制"; setTimeout(() => { btn.textContent = t; }, 1200); } };
  const fallback = () => {
    const ta = h("textarea", { style: "position:fixed;top:-1000px;opacity:0" });
    ta.value = text; document.body.append(ta); ta.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    ta.remove();
    if (ok) done(); else toast("浏览器不允许复制，请手动选中文本复制");
  };
  try {
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  } catch (e) { fallback(); }
}

function startOfDay(t = Date.now()) { const d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); }
function relDay(t) {
  const d = Math.round((startOfDay(t) - startOfDay()) / DAY);
  if (d === 0) return "今天";
  if (d === 1) return "明天";
  if (d === -1) return "昨天";
  if (d < 0) return `逾期 ${-d} 天`;
  return `${d} 天后`;
}
function fmtDate(t) { const d = new Date(t); return `${d.getMonth() + 1}月${d.getDate()}日`; }
function numbered(code) { return code.replace(/\s+$/, "").split("\n").map((l, i) => `${String(i + 1).padStart(3)} | ${l}`).join("\n"); }
function clip(s, n) { s = String(s ?? ""); return s.length > n ? s.slice(0, n) + "…" : s; }

// ---------- 进度与复习 ----------
function prog(pid) { return S.progress[pid] || null; }
function statusOf(pid) {
  const d = prog(pid);
  if (!d) return "todo";
  if (d.passed && d.due && d.due <= startOfDay() + DAY - 1) return "due";
  if (d.passed && (d.stage || 0) >= 5) return "master";
  if (d.passed) return "passed";
  return "trying";
}
const STATUS_TEXT = { todo: "未做", trying: "尝试中", passed: "已通过", due: "待复习", master: "已掌握" };
function statusPill(pid) { const s = statusOf(pid); return h("span", { class: "pill " + s }, STATUS_TEXT[s]); }
function stageDots(stage) { return h("span", { class: "stage-dots", title: `复习阶段 ${stage || 0}/5` }, [0, 1, 2, 3, 4].map(i => h("i", { class: i < (stage || 0) ? "f" : "" }))); }
function schedule(doc, rating) {
  let s = doc.stage || 0;
  if (rating === "solo") s += 1;
  else if (rating === "hint") s = Math.max(1, s);
  else s = 1;
  doc.stage = Math.min(s, 6);
  doc.due = startOfDay() + INTERVALS[Math.min(doc.stage, INTERVALS.length) - 1] * DAY;
  doc.history = (doc.history || []).slice(-19).concat([{ at: Date.now(), rating }]);
  return doc;
}
function dueList() {
  const end = startOfDay() + DAY - 1;
  return S.all.filter(p => { const d = prog(p.id); return d && d.passed && d.due && d.due <= end; })
    .sort((a, b) => prog(a.id).due - prog(b.id).due);
}
function nextNew() {
  for (const pat of PATTERNS) {
    const p = S.all.find(q => q.pattern === pat.key && !q.custom && !prog(q.id));
    if (p) return p;
  }
  return null;
}
function pname(p) { return PMAP[p.pattern] ? PMAP[p.pattern].name : "综合"; }

// ---------- 存储：db（跨设备）优先，本机兜底 ----------
const Store = {
  coll: null, docs: {}, chains: {},
  async init() {
    this.docs = LS.get("tiyan:docs", {});
    applyDocs();
    let db = null, user = null;
    try { if (window.claude && window.claude.use) [db, user] = await Promise.all([window.claude.use("db"), window.claude.use("user")]); } catch (e) { /* 无 */ }
    if (!db || !user) { S.store = "local"; updateChips(); return; }
    let uid = null;
    try { uid = await user.id(); } catch (e) { uid = null; }
    if (!uid) { S.store = "local"; updateChips(); return; }
    this.coll = db.collection("data/users/" + uid);
    S.store = "db";
    updateChips();
    let migrated = false;
    this.coll.onSnapshot(snap => {
      const docs = {};
      for (const d of snap.docs) docs[d.id] = d.data();
      if (!migrated) {
        // 本机有、云端没有的记录（登录前做的题）：显示出来；等云端结果确定后再上传
        const localOnly = Object.keys(this.docs).filter(k => !(k in docs));
        for (const k of localOnly) docs[k] = this.docs[k];
        if (!snap.metadata || !snap.metadata.fromCache) {
          migrated = true;
          const src = this.docs;
          (async () => { for (const k of localOnly) await this.write(k, src[k]); })();
        }
      }
      this.docs = docs;
      LS.set("tiyan:docs", docs);
      applyDocs();
      softRefresh();
    }, err => {
      if (err && err.code === "revoked") { this.coll = null; S.store = "local"; updateChips(); }
    });
  },
  write(key, data) {
    if (!this.coll) return Promise.resolve();
    const prev = this.chains[key] || Promise.resolve();
    const next = prev.then(() => this.coll.doc(key).set(data)).catch(async e => {
      if (e && e.code === "unavailable") {
        await new Promise(r => setTimeout(r, 600 + Math.random() * 800));
        return this.coll.doc(key).set(data).catch(() => toast("云端暂时没保存上，已先存在本机"));
      }
      if (e && e.code === "quota_exceeded") toast("云端存储满了，删掉一些自建题目再试");
      else if (e && e.code === "invalid_argument") { this.coll = null; S.store = "local"; updateChips(); toast("没有云端写入权限，进度只存在本机"); }
    });
    this.chains[key] = next;
    return next;
  },
  put(key, data) {
    this.docs[key] = JSON.parse(JSON.stringify(data));
    LS.set("tiyan:docs", this.docs);
    applyDocs();
    softRefresh();
    return this.write(key, this.docs[key]);
  },
  remove(key) {
    delete this.docs[key];
    LS.set("tiyan:docs", this.docs);
    applyDocs();
    softRefresh();
    if (this.coll) return this.coll.doc(key).delete().catch(() => {});
    return Promise.resolve();
  },
};
function applyDocs() {
  const progress = {}, custom = [], viz = {};
  for (const [k, v] of Object.entries(Store.docs)) {
    if (k.startsWith("p:")) progress[k.slice(2)] = v;
    else if (k.startsWith("x:") && v && v.id) custom.push(v);
    else if (k.startsWith("v:")) viz[k.slice(2)] = v;
  }
  custom.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
  S.progress = progress; S.custom = custom; S.viz = viz;
  S.all = BUILTIN.concat(custom);
  S.byId = Object.fromEntries(S.all.map(p => [p.id, p]));
}
function saveProg(pid, doc) { doc.pid = pid; return Store.put("p:" + pid, doc); }

// ---------- Python 运行时（Pyodide，跑在 Worker 里，死循环可以直接杀掉） ----------
const WORKER_SRC = `
let py = null;
self.onmessage = async (e) => {
  const m = e.data;
  if (m.type === "init") {
    try {
      importScripts(m.base + "pyodide.js");
      py = await loadPyodide({ indexURL: m.base, stdLibURL: m.base + "python_stdlib.wasm" });
      py.runPython(m.harness);
      self.postMessage({ type: "ready", version: py.version });
    } catch (err) {
      self.postMessage({ type: "fail", error: String((err && err.message) || err) });
    }
    return;
  }
  if (m.type === "pkg") {
    try { await py.loadPackage(m.name); self.postMessage({ id: m.id, ok: true, out: "ok" }); }
    catch (err) { self.postMessage({ id: m.id, ok: false, error: String((err && err.message) || err) }); }
    return;
  }
  try {
    const f = py.globals.get(m.fn);
    const out = f(...m.args);
    if (f.destroy) f.destroy();
    self.postMessage({ id: m.id, ok: true, out: out });
  } catch (err) {
    self.postMessage({ id: m.id, ok: false, error: String((err && err.message) || err) });
  }
};`;
const Py = {
  worker: null, seq: 0, pending: new Map(), ready: null, resolveReady: null, error: "", version: "",
  start() {
    S.py = "loading"; updateChips();
    this.ready = new Promise(r => { this.resolveReady = r; });
    let base;
    try {
      base = new URL("pyodide/", location.href).href;
      if (!/^https?:/.test(base)) throw new Error("bad base");
    } catch (e) { return this.fail("拿不到运行时文件的地址"); }
    try {
      const url = URL.createObjectURL(new Blob([WORKER_SRC], { type: "text/javascript" }));
      this.worker = new Worker(url);
    } catch (e) { return this.fail("浏览器不允许启动后台线程"); }
    this.worker.onmessage = e => {
      const m = e.data;
      if (m.type === "ready") { clearTimeout(this.bootTimer); S.py = "ready"; this.version = m.version; updateChips(); this.resolveReady(true); return; }
      if (m.type === "fail") { this.fail(m.error); return; }
      const p = this.pending.get(m.id);
      if (!p) return;
      this.pending.delete(m.id);
      clearTimeout(p.timer);
      if (m.ok) p.res(m.out); else p.rej({ message: m.error });
    };
    this.worker.onerror = e => { e.preventDefault && e.preventDefault(); if (S.py === "loading") this.fail(e.message || "运行时加载失败"); };
    this.worker.postMessage({ type: "init", base, harness: HARNESS });
    this.bootTimer = setTimeout(() => { if (S.py === "loading") this.fail("加载超时"); }, 90000);
  },
  fail(msg) {
    clearTimeout(this.bootTimer);
    S.py = "failed"; this.error = String(msg || "未知错误"); updateChips();
    if (this.resolveReady) this.resolveReady(false);
    for (const p of this.pending.values()) { clearTimeout(p.timer); p.rej({ message: "Python 运行环境不可用" }); }
    this.pending.clear();
    try { this.worker && this.worker.terminate(); } catch (e) { /* ignore */ }
    softRefresh();
  },
  async call(fn, args, timeout = 8000) {
    const ok = await this.ready;
    if (!ok) throw { message: "Python 运行环境不可用：" + this.error, unavailable: true };
    const id = ++this.seq;
    return new Promise((res, rej) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        rej({ timeout: true, message: `运行超过 ${Math.round(timeout / 1000)} 秒被终止：可能有死循环，或者复杂度太高` });
        this.restart();
      }, timeout);
      this.pending.set(id, { res, rej, timer });
      this.worker.postMessage({ id, fn, args });
    });
  },
  async json(fn, args, timeout) { return JSON.parse(await this.call(fn, args, timeout)); },
  loaded: new Set(),
  async loadPackage(name, timeout = 90000) {
    if (this.loaded.has(name)) return;
    const ok = await this.ready;
    if (!ok) throw { message: "Python 运行环境不可用：" + this.error };
    const id = ++this.seq;
    await new Promise((res, rej) => {
      const timer = setTimeout(() => { this.pending.delete(id); rej({ message: `加载 ${name} 超时，检查网络后重试` }); }, timeout);
      this.pending.set(id, { res, rej, timer });
      this.worker.postMessage({ id, type: "pkg", name });
    });
    this.loaded.add(name);
  },
  restart() {
    this.loaded = new Set();
    try { this.worker.terminate(); } catch (e) { /* ignore */ }
    for (const p of this.pending.values()) { clearTimeout(p.timer); p.rej({ message: "运行环境重启了，请再试一次" }); }
    this.pending.clear();
    this.start();
  },
};
function specOf(p, tests) {
  return JSON.stringify({ fn: p.fn, types: p.types, ret_type: p.ret_type, compare: p.compare, tests: tests || p.tests });
}

// ---------- AI（经自己的后端转发到 DeepSeek） ----------
function mergeTurns(list) {
  const out = [];
  for (const m of list) {
    if (!m.content) continue;
    const last = out[out.length - 1];
    if (last && last.role === m.role) last.content += "\n\n" + m.content;
    else out.push({ role: m.role, content: m.content });
  }
  return out;
}
function parseJsonLoose(text) {
  const t = String(text || "").trim();
  try { return JSON.parse(t); } catch (e) { /* 继续尝试 */ }
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) { try { return JSON.parse(fence[1]); } catch (e) { /* 继续 */ } }
  const a = t.search(/[{[]/), b = Math.max(t.lastIndexOf("}"), t.lastIndexOf("]"));
  if (a >= 0 && b > a) { try { return JSON.parse(t.slice(a, b + 1)); } catch (e) { /* 放弃 */ } }
  return undefined;
}
const AI_CODES = { locked: "locked", no_key: "no_key", bad_key: "bad_key", insufficient_balance: "insufficient_balance", rate_limited: "rate_limited", too_large: "prompt_too_large", bad_request: "invalid_request" };
const DS_DEFAULT = { base: "https://api.deepseek.com", model: "deepseek-flash", pro: "deepseek-v4-pro" };
const AI = {
  tools: true, images: false, model: "", pro: "", needPassword: false, mode: "server",
  pw() { return LS.get("tiyan:pw", ""); },
  key() { return LS.get("tiyan:dskey", ""); },
  direct() { return Object.assign({}, DS_DEFAULT, LS.get("tiyan:dsconf", {})); },
  async init() {
    let c = null;
    try {
      const r = await fetch("api/config", { headers: { "x-site-password": this.pw() }, cache: "no-store" });
      if (r.ok && /json/.test(r.headers.get("content-type") || "")) c = await r.json();
    } catch (e) { c = null; }
    if (c && typeof c.hasKey === "boolean" && (c.hasKey || !this.key())) {
      this.mode = "server";
      this.model = c.model || ""; this.pro = c.pro || ""; this.needPassword = !!c.needPassword; this.images = !!c.vision;
      S.ai = !c.hasKey ? "nokey" : c.authed ? "ready" : "locked";
    } else {
      // 没有后端（GitHub Pages 等静态托管）：浏览器直连 DeepSeek，key 只存在本机浏览器
      const d = this.direct();
      this.mode = "direct"; this.model = d.model; this.pro = d.pro; this.images = false;
      S.ai = this.key() ? "ready" : "needkey";
    }
    updateChips();
    softRefresh();
  },
  async setKey(k) { LS.set("tiyan:dskey", k.trim()); await this.init(); },
  clearKey() { LS.del("tiyan:dskey"); this.init(); },
  async unlock(pw) { LS.set("tiyan:pw", pw); await this.init(); return S.ai === "ready"; },
  ok() { return S.ai === "ready"; },
  async ask(input, o = {}) {
    if (!this.ok()) throw { code: { locked: "locked", nokey: "no_key", needkey: "need_key" }[S.ai] || "unavailable" };
    const messages = mergeTurns(typeof input === "string" ? [{ role: "user", content: input }] : input);
    if (!messages.length || messages[messages.length - 1].role !== "user") throw { code: "invalid_request" };
    let tools = o.tools ? o.tools.filter(t => !t.needsPy || S.py === "ready") : null;
    if (tools && !tools.length) tools = null;
    const spec = tools ? tools.map(t => ({ type: "function", function: { name: t.name, description: t.description, parameters: t.inputSchema || { type: "object", properties: {} } } })) : undefined;
    let full = "", truncated = false;
    const MAX = 6;
    for (let round = 0; round < MAX; round++) {
      const last = round === MAX - 1;
      let r;
      try {
        r = await this.round(messages, {
          json: !!o.json && (!spec || last), tools: last ? undefined : spec, tier: o.tier, signal: o.signal,
          onDelta: o.json ? null : d => { full += d; if (o.onText) o.onText({ text: full, delta: d }); },
        });
      } catch (e) { if (full) e.text = full; throw e; }
      truncated = r.finish === "length";
      if (r.toolCalls.length && !last) {
        messages.push({ role: "assistant", content: r.content || "", tool_calls: r.toolCalls.map(c => ({ id: c.id, type: "function", function: { name: c.name, arguments: c.args || "{}" } })) });
        for (const c of r.toolCalls) {
          const tool = tools.find(t => t.name === c.name);
          let result;
          try { result = tool ? await tool.execute(JSON.parse(c.args || "{}"), { signal: o.signal }) : { error: "没有这个工具：" + c.name }; }
          catch (e) { result = { error: String((e && e.message) || e) }; }
          if (o.signal && o.signal.aborted) throw { code: "cancelled", text: full };
          messages.push({ role: "tool", tool_call_id: c.id, content: clip(typeof result === "string" ? result : JSON.stringify(result), 20000) });
        }
        if (full && !/\n\n$/.test(full)) full += "\n\n";
        continue;
      }
      if (o.json) {
        const v = parseJsonLoose(r.content);
        if (v === undefined) throw { code: "invalid_json", text: r.content };
        return v;
      }
      if (!full.trim()) throw { code: "empty_completion" };
      return { text: full, truncated };
    }
    throw { code: "upstream_error", text: full };
  },
  async round(messages, { json, tools, tier, signal, onDelta }) {
    let resp;
    const direct = this.mode === "direct";
    try {
      if (direct) {
        const d = this.direct();
        const payload = { model: tier === "complex" ? d.pro : d.model, messages, stream: true, max_tokens: 8192 };
        if (tools) payload.tools = tools;
        if (json) payload.response_format = { type: "json_object" };
        resp = await fetch(d.base.replace(/\/+$/, "") + "/chat/completions", {
          method: "POST", signal,
          headers: { "content-type": "application/json", authorization: "Bearer " + this.key() },
          body: JSON.stringify(payload),
        });
      } else {
        resp = await fetch("api/chat", {
          method: "POST", signal,
          headers: { "content-type": "application/json", "x-site-password": this.pw() },
          body: JSON.stringify({ messages, tools, json, tier }),
        });
      }
    } catch (e) {
      if (signal && signal.aborted) throw { code: "cancelled" };
      throw { code: direct ? "network" : "unavailable", message: String((e && e.message) || e) };
    }
    if (!resp.ok) {
      let j = {};
      try { j = await resp.json(); } catch (e) { /* 不是 JSON */ }
      let code;
      if (direct) code = { 400: "invalid_request", 401: "bad_key", 402: "insufficient_balance", 422: "invalid_request", 429: "rate_limited" }[resp.status] || "upstream_error";
      else code = AI_CODES[j.error] || "upstream_error";
      if (code === "locked") { S.ai = "locked"; updateChips(); }
      const msg = j.message || (j.error && j.error.message) || "";
      throw { code, message: typeof msg === "string" ? msg : JSON.stringify(msg) };
    }
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "", content = "", finish = null;
    const calls = [];
    const eat = line => {
      line = line.trim();
      if (!line.startsWith("data:")) return;
      const data = line.slice(5).trim();
      if (!data || data === "[DONE]") return;
      let ev;
      try { ev = JSON.parse(data); } catch (e) { return; }
      const ch = ev.choices && ev.choices[0];
      if (!ch) return;
      const d = ch.delta || {};
      if (d.content) { content += d.content; if (onDelta) onDelta(d.content); }
      if (Array.isArray(d.tool_calls)) for (const t of d.tool_calls) {
        const k = t.index ?? calls.length;
        const c = calls[k] || (calls[k] = { id: "", name: "", args: "" });
        if (t.id) c.id = t.id;
        if (t.function) { if (t.function.name) c.name += t.function.name; if (t.function.arguments) c.args += t.function.arguments; }
      }
      if (ch.finish_reason) finish = ch.finish_reason;
    };
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf("\n")) >= 0) { eat(buf.slice(0, i)); buf = buf.slice(i + 1); }
      }
      if (buf) eat(buf);
    } catch (e) {
      if (signal && signal.aborted) throw { code: "cancelled" };
      throw { code: "upstream_error", message: String((e && e.message) || e) };
    }
    return { content, finish, toolCalls: calls.filter(c => c && c.name).map((c, i) => ({ ...c, id: c.id || "call_" + i })) };
  },
};
function aiErr(e) {
  switch (e && e.code) {
    case "cancelled": return "";
    case "locked": return "需要访问密码：在 AI 老师面板顶部输入密码。";
    case "need_key": return "还没有填 DeepSeek API key：点右上角「AI」状态，或在 AI 老师面板顶部填写。";
    case "network": return "连不上 DeepSeek（api.deepseek.com）：检查网络或代理后再试。";
    case "no_key": return "服务器还没配置 DeepSeek API key。";
    case "bad_key": return AI.mode === "direct" ? "DeepSeek API key 无效：点右上角「AI」状态重新填写。" : "DeepSeek API key 无效，请检查服务器上的 key。";
    case "insufficient_balance": return "DeepSeek 账户余额不足，去 platform.deepseek.com 充值后再试。";
    case "rate_limited": return "请求太频繁，被 DeepSeek 限流了，稍等一会儿再试。";
    case "invalid_json": return "AI 返回的格式不对，再点一次试试。";
    case "prompt_too_large": return "内容太长了：删减一些代码或对话再试。";
    case "empty_completion": return "AI 没有输出内容，换个问法再试。";
    case "invalid_request": return "请求格式有问题" + (e.message ? "：" + clip(e.message, 200) : "。");
    case "unavailable": return AI.mode === "direct" ? "AI 老师还没准备好，稍后再试。" : "连不上 AI 服务：确认 server.mjs 还在运行，或稍后再试。";
    default: return "AI 暂时出错了" + (e && e.message ? "：" + clip(e.message, 200) : "，稍后再试一次。");
  }
}

// ---------- Markdown 渲染（AI 回复） ----------
function renderMd(el, text) {
  let html = "";
  try { html = marked.parse(String(text || ""), { gfm: true, breaks: false }); } catch (e) { html = ""; }
  el.innerHTML = DOMPurify.sanitize(html, { ADD_TAGS: ["details", "summary"], ADD_ATTR: ["open"] });
  for (const code of $$("pre code", el)) {
    const src = code.textContent;
    const lang = ((code.className || "").match(/language-([\w+-]+)/) || [])[1] || "";
    if (!lang || /^(py|python|python3)$/i.test(lang)) {
      code.textContent = "";
      try { CodeMirror.runMode(src, "python", code); } catch (e) { code.textContent = src; }
    }
    const btn = h("button", { class: "btn sm copy", type: "button" }, "复制");
    btn.addEventListener("click", () => copyText(src, btn));
    code.parentElement.append(btn);
  }
  for (const a of $$("a", el)) if (/^https?:/i.test(a.getAttribute("href") || "")) { a.target = "_blank"; a.rel = "noopener"; }
}
function highlightInto(el, code) {
  el.textContent = "";
  try { CodeMirror.runMode(code, "python", el); } catch (e) { el.textContent = code; }
  return el;
}

// ---------- 语音朗读（浏览器自带 TTS） ----------
const TTS = {
  ok: typeof window.speechSynthesis !== "undefined" && typeof window.SpeechSynthesisUtterance !== "undefined",
  voice: null, rate: LS.get("tiyan:rate", 1.05), token: 0, current: null,
  pick() {
    if (!this.ok) return;
    const vs = speechSynthesis.getVoices() || [];
    this.voice = vs.find(v => /zh[-_]CN/i.test(v.lang) && /Tingting|Xiaoxiao|Yunxi|Google/i.test(v.name)) || vs.find(v => /zh[-_]CN/i.test(v.lang)) || vs.find(v => /^zh/i.test(v.lang)) || null;
  },
  clean(md) {
    return String(md || "")
      .replace(/```[\s\S]*?```/g, "。这里有一段代码，请看屏幕。")
      .replace(/<details>[\s\S]*?<\/details>/g, "")
      .replace(/<[^>]+>/g, "")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/^\s*\|?\s*:?-{2,}.*$/gm, "")
      .replace(/\|/g, "，")
      .replace(/^#+\s*/gm, "")
      .replace(/[*_>#~]/g, "")
      .replace(/^\s*[-+]\s+/gm, "")
      .replace(/\n{2,}/g, "。\n")
      .replace(/\s+/g, " ")
      .trim();
  },
  speak(text, onend) {
    if (!this.ok) { onend && onend(); return; }
    this.stop();
    if (!this.voice) this.pick();
    const tok = ++this.token;
    const parts = (this.clean(text).match(/[^。！？；\n!?;]+[。！？；\n!?;]?/g) || []).reduce((acc, s) => {
      const last = acc[acc.length - 1];
      if (last && (last + s).length < 120) acc[acc.length - 1] = last + s; else acc.push(s);
      return acc;
    }, []);
    if (!parts.length) { onend && onend(); return; }
    parts.forEach((t, i) => {
      const u = new SpeechSynthesisUtterance(t);
      u.lang = "zh-CN";
      if (this.voice) u.voice = this.voice;
      u.rate = this.rate;
      if (i === parts.length - 1) u.onend = () => { if (tok === this.token) { this.current = null; onend && onend(); } };
      u.onerror = () => { if (tok === this.token && i === parts.length - 1) { this.current = null; onend && onend(); } };
      speechSynthesis.speak(u);
    });
    this.current = tok;
  },
  stop() { if (!this.ok) return; this.token++; this.current = null; try { speechSynthesis.cancel(); } catch (e) { /* ignore */ } },
};
if (TTS.ok) { TTS.pick(); try { speechSynthesis.onvoiceschanged = () => TTS.pick(); } catch (e) { /* ignore */ } }

// ---------- AI 老师的公共规则与上下文 ----------
const TEACHER = `你是「题眼」算法陪练里的 AI 老师。学习者在准备大厂技术面试，用 Python 刷题；他的痛点是：死记硬背记不住、题目一变形就不会写。
教学原则：
1. 讲清“为什么这么写”：把每个关键写法和背后的理由对应起来，而不是只给答案；
2. 每次都点出这题的“题眼”（题目里哪句话提示了该用什么方法）和“核心一句话”；
3. 先引导、后给答案：除非学习者明确要求看答案，不要直接贴完整解答代码；
4. 用中文，口语化、准确、简洁；用 Markdown，代码用 \`\`\`python 代码块，引用学习者代码时写明行号；
5. 运行结果以页面提供的真实结果为准，不确定的地方直说，不要编造。`;

function problemBlock(p, withRef = true) {
  return [
    `【题目】${p.title}（${LEVEL[p.level] || ""}，题型：${pname(p)}）`,
    p.desc,
    "示例：\n" + (p.examples || []).map((e, i) => `${i + 1}. 输入：${e.input}　输出：${e.output}${e.note ? "　说明：" + e.note : ""}`).join("\n"),
    "约束：" + (p.constraints || []).join("；"),
    "函数签名：\n" + p.starter.trim(),
    p.change ? "【这是一道变体题，和原题的区别】" + p.change : "",
    withRef && p.solution ? "【参考解】（只用于判断对错和引导；学习者没要求看答案时，不要贴出完整参考代码）\n```python\n" + p.solution.trim() + "\n```\n复杂度：" + (p.complexity || "") : "",
  ].filter(Boolean).join("\n\n");
}
function runBlock(last) {
  if (!last) return "【最近一次运行】还没运行过。";
  const r = last.result;
  if (!r) return "【最近一次运行】" + (last.error || "运行失败");
  if (r.compile_error) return "【最近一次运行】代码无法运行：" + r.compile_error;
  const fails = r.cases.filter(c => !c.pass).slice(0, 3).map(c => `- 输入 ${clip(c.args, 300)}；期望 ${clip(c.expected, 200)}；${c.error ? "报错 " + c.error : "实际 " + clip(c.got, 200)}`);
  const slow = r.cases.filter(c => c.ms > 1000).length;
  return `【最近一次运行】（${last.all ? "全部用例" : "样例"}，真实运行）通过 ${r.passed}/${r.total}` +
    (fails.length ? "\n失败的用例：\n" + fails.join("\n") : "") +
    (slow ? `\n有 ${slow} 个用例耗时超过 1 秒，复杂度可能偏高。` : "") +
    (r.stdout ? "\nprint 输出：\n" + clip(r.stdout, 800) : "");
}

// ---------- DeepSeek key 设置（直连模式） ----------
function keyForm(onDone) {
  const inp = h("input", { type: "password", id: "ds-key", placeholder: "sk-……", autocomplete: "off", spellcheck: "false", style: "padding:7px 10px;border:1px solid var(--line);border-radius:6px;background:var(--surface);min-width:0;flex:1" });
  const msg = h("div", { class: "small muted" });
  const form = h("form", { class: "stack", style: "gap:8px" },
    h("div", { class: "row", style: "flex-wrap:nowrap" }, inp, h("button", { class: "btn primary sm", type: "submit" }, "保存")),
    h("div", { class: "small muted" }, "在 ", h("a", { href: "https://platform.deepseek.com/api_keys", target: "_blank", rel: "noopener" }, "platform.deepseek.com"), " 创建 key。key 只保存在这个浏览器里，由浏览器直接发给 DeepSeek，不经过任何其他服务器。"),
    msg);
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const k = inp.value.trim();
    if (!/^sk-\S{10,}$/.test(k)) { msg.textContent = "格式不对：DeepSeek key 以 sk- 开头。"; return; }
    msg.textContent = "检查 key……";
    let ok = true, note = "";
    try {
      const r = await fetch(AI.direct().base.replace(/\/+$/, "") + "/user/balance", { headers: { authorization: "Bearer " + k } });
      if (r.status === 401) ok = false;
      else if (r.ok) {
        const b = await r.json();
        const info = (b.balance_infos || [])[0];
        if (info) note = `余额 ${info.total_balance} ${info.currency === "CNY" ? "元" : info.currency}`;
      }
    } catch (err) { note = "暂时没法联网验证，先保存了"; }
    if (!ok) { msg.textContent = "DeepSeek 说这个 key 无效，请检查。"; return; }
    await AI.setKey(k);
    msg.textContent = "已保存" + (note ? "，" + note : "") + "。";
    if (onDone) onDone();
  });
  return form;
}
function openKeyDialog() {
  const close = () => { wrap.remove(); };
  const box = h("div", { class: "panel", style: "max-width:520px;width:100%;box-shadow:var(--shadow)", role: "dialog", "aria-label": "DeepSeek 设置" },
    h("div", { class: "panel-h" }, h("h2", null, "DeepSeek 设置"), h("button", { class: "btn ghost sm", type: "button", onclick: close }, "关闭")),
    h("p", { class: "small muted" }, AI.key() ? `已保存 key（…${AI.key().slice(-4)}）。对话用 ${AI.model}，出题和动画用 ${AI.pro}。` : "AI 老师需要你自己的 DeepSeek API key。"),
    keyForm(() => setTimeout(close, 900)),
    AI.key() ? h("div", { class: "row" }, h("button", { class: "btn ghost sm", type: "button", onclick: () => { AI.clearKey(); close(); toast("已删除这个浏览器里的 key"); } }, "删除已保存的 key")) : "");
  const wrap = h("div", { style: "position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.35);display:grid;place-items:center;padding:16px" }, box);
  wrap.addEventListener("click", e => { if (e.target === wrap) close(); });
  document.body.append(wrap);
  $("#ds-key", box).focus();
}
