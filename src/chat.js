// ---------- 对话组件：做题页、题型页、问老师页共用 ----------
// 正在进行的对话请求：离开页面不中断，回来后新页面接着显示同一个回答
const CHAT_JOBS = {};   // key → { text, views: Set, ctl, progress }
const CHAT_LIVE = {};   // key → 当前页面上的 Chat 实例
class Chat {
  constructor({ key, context, placeholder, actions, intro, images, who }) {
    this.key = key;
    this.who = who || ["题眼", "老师"];
    this.context = context;
    this.msgs = S.chats[key] || (S.chats[key] = []);
    this.ctl = null;
    this.busy = false;
    this.mode = null;
    this.actions = actions || [];
    this.el = h("div", { class: "chat" });
    this.offEl = h("div", { class: "ai-off", hidden: true });
    this.actEl = this.actions.length ? h("div", { class: "chat-actions" }) : null;
    this.list = h("div", { class: "msgs" });
    this.optRow = h("div", { class: "opt-row", hidden: true });
    this.ta = h("textarea", { id: "ta-" + key.replace(/[^\w-]/g, "_"), rows: 2, placeholder: placeholder || "问老师任何问题……（Enter 发送，Shift+Enter 换行）" });
    this.sendBtn = h("button", { class: "btn primary sm", type: "button" }, icon("send"), "发送");
    this.stopBtn = h("button", { class: "btn sm", type: "button", hidden: true }, icon("stop"), "停止");
    this.file = null;
    this.fileInput = null;
    const tools = [];
    if (images) {
      this.fileInput = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp,image/gif", id: "img-" + key.replace(/[^\w-]/g, "_") });
      this.fileInput.addEventListener("change", () => { this.file = this.fileInput.files[0] || null; });
      this.imgPick = h("label", { class: "file-pick", title: "附一张截图（题目、报错、手写思路都行）", hidden: !AI.images }, icon("image"), this.fileInput);
      tools.push(this.imgPick);
    }
    this.el.append(
      this.offEl,
      this.actEl || "",
      this.list,
      this.optRow,
      h("div", { class: "composer" }, this.ta, h("div", { class: "row" }, h("div", { class: "row" }, tools), h("div", { class: "row" }, this.stopBtn, this.sendBtn))),
    );
    this.ta.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); this.submit(); }
    });
    this.ta.addEventListener("input", () => { this.ta.style.height = "auto"; this.ta.style.height = Math.min(160, this.ta.scrollHeight + 2) + "px"; });
    this.sendBtn.addEventListener("click", () => this.submit());
    this.stopBtn.addEventListener("click", () => { const j = CHAT_JOBS[this.key]; if (j) j.ctl.abort(); });
    if (this.actEl) for (const a of this.actions) {
      const b = h("button", { class: "chip", type: "button", title: a.title || "" }, a.label);
      b.addEventListener("click", () => { if (!this.busy) a.run(this); });
      a.btn = b;
      this.actEl.append(b);
    }
    if (!this.msgs.length && intro) { const d = h("div", { class: "md muted" }); renderMd(d, intro); this.list.append(this.introEl = h("div", { class: "msg ai" }, h("div", { class: "who" }, h("b", null, this.who[0]), this.who[1]), d)); }
    for (const m of this.msgs) this.renderMsg(m, false);
    CHAT_LIVE[key] = this;
    const job = CHAT_JOBS[key];
    if (job) {                       // 上次离开时还在回答：接上
      const view = this.renderMsg({ role: "assistant", content: "" }, true);
      if (job.text) { view.status.hidden = true; renderMd(view.md, job.text); }
      else if (job.progress) view.progress(job.progress);
      job.views.add(view);
      this.busy = true;
    }
    this.sync();
  }
  sync() {
    const ok = AI.ok();
    this.offEl.hidden = ok;
    if (S.ai === "locked") {
      if (!this.offEl.querySelector("form")) {
        this.offEl.textContent = "";
        const pw = h("input", { type: "password", id: "pw-" + this.key.replace(/[^\w-]/g, "_"), placeholder: "访问密码", autocomplete: "current-password", style: "padding:5px 9px;border:1px solid var(--line);border-radius:6px;background:var(--surface);min-width:0;flex:1" });
        const msg = h("span", { class: "small" });
        const form = h("form", { class: "row", style: "flex-wrap:nowrap" }, h("span", null, "AI 老师需要访问密码："), pw, h("button", { class: "btn primary sm", type: "submit" }, "解锁"));
        form.addEventListener("submit", async e => {
          e.preventDefault();
          msg.textContent = "验证中……";
          const ok2 = await AI.unlock(pw.value.trim());
          msg.textContent = ok2 ? "" : "密码不对。";
        });
        this.offEl.append(form, msg);
      }
    } else if (S.ai === "needkey") {
      if (!this.offEl.querySelector("form")) {
        this.offEl.textContent = "";
        this.offEl.append(h("div", { style: "margin-bottom:6px" }, "填上你的 DeepSeek API key，AI 老师就能用了："), keyForm());
      }
    } else {
      this.offEl.textContent = S.ai === "unknown" ? "正在连接 AI 老师……"
        : S.ai === "nokey" ? "服务器还没配置 DeepSeek API key：把 key 存到 ~/.deepseek_key（或 .dev.vars）后重启 server.mjs。题目、模板、判题和复习不受影响。"
        : "连不上 AI 服务：确认 server.mjs 正在运行。题目、模板、判题和复习不受影响。";
    }
    if (this.imgPick) this.imgPick.hidden = !AI.images;
    for (const a of this.actions) if (a.btn) a.btn.disabled = this.busy || !ok || (a.enabled ? !a.enabled() : false);
    this.sendBtn.disabled = this.busy || !ok;
    this.stopBtn.hidden = !this.busy;
  }
  setMode(mode) {
    this.mode = mode;
    this.optRow.textContent = "";
    this.optRow.hidden = !mode;
    if (!mode) return;
    this.optRow.append(h("span", null, mode.hint), mode.extra || "", h("button", { class: "btn ghost sm", type: "button", onclick: () => this.setMode(null) }, "取消"));
    if (mode.placeholder) this.ta.placeholder = mode.placeholder;
    this.ta.focus();
  }
  submit() {
    const text = this.ta.value.trim();
    if (this.mode) {
      const m = this.mode;
      if (!text && !m.allowEmpty) { this.ta.focus(); return; }
      this.ta.value = "";
      this.setMode(null);
      m.send(text);
      return;
    }
    if (!text && !this.file) return;
    this.ta.value = "";
    this.ta.style.height = "auto";
    const file = this.file;
    this.file = null;
    if (this.fileInput) this.fileInput.value = "";
    if (!file) { this.send(text, { display: text }); return; }
    shrinkImage(file).then(url => this.send(text || "请看我附的截图。", { display: text || "请看我附的截图。", images: [url], thumbs: [url] }))
      .catch(() => toast("图片读不出来，换一张试试"));
  }
  scroll() { this.list.scrollTop = this.list.scrollHeight; }
  renderMsg(m, live) {
    if (this.introEl) { this.introEl.remove(); this.introEl = null; }
    if (m.role === "user") {
      const b = h("div", { class: "bubble" }, m.label ? h("span", { class: "act" }, "【" + m.label + "】") : "", m.label ? (m.display ? " " + m.display : "") : (m.display || m.content),
        m.thumbs && m.thumbs.length ? h("div", { class: "msg-thumbs" }, m.thumbs.map(u => h("img", { src: u, alt: "截图" }))) : "");
      this.list.append(h("div", { class: "msg user" }, b));
      this.scroll();
      return null;
    }
    const md = h("div", { class: "md" });
    const status = h("div", { class: "thinking", hidden: !live }, (this.who[1] === "老师" ? "老师" : this.who[0]) + "在想……");
    const note = h("div", { class: "small faint", hidden: true });
    const tools = h("div", { class: "msg-tools", hidden: live });
    const wrap = h("div", { class: "msg ai" }, h("div", { class: "who" }, h("b", null, this.who[0]), this.who[1]), status, md, note, tools);
    if (m.node) md.append(m.node);
    else if (m.content) renderMd(md, m.content);
    const addTools = () => {
      tools.textContent = "";
      if (TTS.ok && m.content) {
        const sb = h("button", { class: "btn ghost sm", type: "button" }, icon("speak"), "朗读");
        sb.addEventListener("click", () => {
          if (wrap.classList.contains("speaking")) { TTS.stop(); wrap.classList.remove("speaking"); sb.lastChild.textContent = "朗读"; return; }
          $$(".msg.speaking").forEach(x => x.classList.remove("speaking"));
          wrap.classList.add("speaking"); sb.lastChild.textContent = "停止朗读";
          TTS.speak(m.content, () => { wrap.classList.remove("speaking"); sb.lastChild.textContent = "朗读"; });
        });
        tools.append(sb);
      }
      if (m.content) {
        const cb = h("button", { class: "btn ghost sm", type: "button" }, icon("copy"), "复制");
        cb.addEventListener("click", () => copyText(m.content, cb.lastChild));
        tools.append(cb);
      }
      tools.hidden = !tools.childNodes.length;
    };
    if (!live) addTools();
    this.list.append(wrap);
    this.scroll();
    return {
      wrap, md, status,
      progress: t => { status.hidden = false; status.textContent = t; },
      note: t => { note.hidden = !t; note.textContent = t || ""; },
      done: () => { status.hidden = true; tools.hidden = false; addTools(); },
    };
  }
  addNode(node) {
    const m = { role: "assistant", content: "", node };
    this.renderMsg(m, false);
  }
  setBusy(b) { this.busy = b; this.sync(); }
  async send(prompt, o = {}) {
    if (!AI.ok()) { toast(aiErr({ code: S.ai === "denied" ? "not_granted" : S.ai === "needkey" ? "need_key" : "unavailable" })); return null; }
    if (this.busy || CHAT_JOBS[this.key]) return null;
    const key = this.key, msgs = this.msgs;
    let userMsg = o.retryOf;
    if (!userMsg) {
      userMsg = { role: "user", content: prompt, label: o.label || "", display: o.display != null ? o.display : (o.label ? "" : prompt), thumbs: o.thumbs || null, images: o.images || null };
      msgs.push(userMsg);
      this.renderMsg(userMsg, false);
    }
    const aiMsg = { role: "assistant", content: "" };
    const view = this.renderMsg(aiMsg, true);
    const job = CHAT_JOBS[key] = { text: "", views: new Set([view]), ctl: new AbortController(), progress: "" };
    this.setBusy(true);
    const turns = [{ role: "user", content: this.context() }];
    for (const m of msgs.slice(-12)) if (m.content) turns.push({ role: m.role, content: clip(m.content, 6000) });
    let queued = false;
    const paint = () => { queued = false; for (const v of job.views) { v.status.hidden = true; renderMd(v.md, job.text); } const live = CHAT_LIVE[key]; if (live) live.scroll(); };
    const jobView = { progress: t => { job.progress = t; for (const v of job.views) v.progress(t); } };
    let out = null, failed = null, partial = "";
    try {
      const res = await AI.ask(turns, {
        signal: job.ctl.signal, tier: o.tier, images: o.images || userMsg.images || undefined, onImagesDropped: () => toast("当前模型看不了图片，这次只发了文字"),
        tools: o.tools ? o.tools(jobView) : undefined,
        onText: ({ text }) => { job.text = text; if (!queued) { queued = true; requestAnimationFrame(paint); } },
      });
      aiMsg.content = res.text;
      job.text = res.text;
      paint();
      if (res.truncated) for (const v of job.views) v.note("回答太长被截断了，可以说“接着讲”。");
      msgs.push(aiMsg);
      out = res.text;
    } catch (e) {
      partial = (e && e.text) || "";
      failed = e;
      if (partial) { aiMsg.content = partial; job.text = partial; paint(); msgs.push(aiMsg); }
    } finally {
      delete CHAT_JOBS[key];
      for (const v of job.views) {
        v.done();
        if (failed) {
          const msg = aiErr(failed) || "已停止。";
          v.note(msg);
          if (!partial || failed.code !== "cancelled") {
            const retry = h("button", { class: "btn sm", type: "button" }, "重试");
            retry.addEventListener("click", () => {
              const live = CHAT_LIVE[key];
              if (!live || live.busy) return;
              const i = msgs.indexOf(aiMsg); if (i >= 0) msgs.splice(i, 1);
              v.wrap.remove();
              live.send(userMsg.content, Object.assign({}, o, { retryOf: userMsg }));
            });
            v.wrap.append(h("div", { class: "row" }, retry));
          }
        }
      }
      const live = CHAT_LIVE[key];
      if (live) { live.setBusy(false); live.scroll(); }
      if (this !== live) this.busy = false;
    }
    if (out && o.onDone) o.onDone(out);
    return out;
  }
}

// AI 能调用的页面工具：真跑 Python，避免它“脑补”运行结果
function pyTools(p) {
  return view => {
    const tools = [{
      name: "run_python", needsPy: true,
      description: "在浏览器里的 Python 3.12 中运行一段完整代码，返回 {stdout, error}。可以直接用 ListNode、TreeNode、build_list(数组)、build_tree(层序数组)、list_values(链表)、tree_values(树)，以及 collections / heapq / bisect / functools 等标准库。单次限时 8 秒。",
      inputSchema: { type: "object", properties: { code: { type: "string", description: "要运行的 Python 代码，用 print 输出你需要看的结果" } }, required: ["code"] },
      execute: async input => {
        view.progress("正在运行 Python 代码核对……");
        try { return await Py.json("run_snippet", [String(input.code || ""), ""], 8000); }
        catch (e) { throw new Error(e.message || "运行失败"); }
      },
    }];
    if (p && p.solution) tools.push({
      name: "compare_with_reference", needsPy: true,
      description: "用学习者编辑器里的当前代码和参考解分别运行若干组输入，返回每组输入下两者的输出以及是否一致。inputs 是“参数列表”的数组，例如 [[[2,7,11,15], 9], [[3,3], 6]]；链表、树用数组表示（树用层序数组，空位写 null）。",
      inputSchema: { type: "object", properties: { inputs: { type: "array", items: { type: "array" }, description: "每一项是一组函数参数" } }, required: ["inputs"] },
      execute: async input => {
        const inputs = Array.isArray(input.inputs) ? input.inputs.filter(Array.isArray).slice(0, 40) : [];
        if (!inputs.length) throw new Error("inputs 不能为空，每一项是一组参数");
        view.progress(`正在用 ${inputs.length} 组输入对比你的代码和参考解……`);
        try { return await compareWithRef(p, S.ws && S.ws.cm ? S.ws.cm.getValue() : "", inputs); }
        catch (e) { throw new Error(e.message || "运行失败"); }
      },
    });
    return tools;
  };
}
async function compareWithRef(p, code, inputs) {
  const tests = inputs.map(a => ({ args: a }));
  const refs = await Py.json("run_reference", [p.solution, specOf(p, tests)], 10000);
  const good = [];
  tests.forEach((t, i) => { if (refs[i] && !refs[i].error) good.push({ args: t.args, expected: refs[i].expected }); });
  if (!good.length) return { error: "这些输入在参考解上都报错，可能不符合题目约束：" + ((refs[0] && refs[0].error) || "") };
  const r = await Py.json("run_tests", [code, specOf(p, good)], 10000);
  if (r.compile_error) return { error: "学习者的代码无法运行：" + r.compile_error };
  return r.cases.map(c => ({ input: c.args, user: c.error ? "报错 " + c.error : c.got, reference: c.expected, same: !!c.pass }));
}

// ---------- AI 出题（变体 / 导入 / 按题型出新题） ----------
const PROBLEM_SCHEMA = `只返回一个 JSON 对象，不要其他文字。字段：
{"title": "题目名", "pattern": "从 ${PATTERNS.map(p => p.key).join(" / ")} 里选最贴切的一个", "level": "easy | medium | hard", "desc": "题面：中文 Markdown，2–5 句，变量名用反引号", "examples": [{"input": "nums = [1,2,3], k = 2", "output": "3", "note": "一句话说明，可为空"}], "constraints": ["1 <= len(nums) <= 10^5"], "fn": "方法名（camelCase）", "params": [["nums", "List[int]"], ["k", "int"]], "ret": "int", "types": [null, null], "ret_type": null, "compare": "exact", "tests": [{"args": [[1,2,3], 2], "expected": 3}], "solution": "class Solution:\\n    def 方法名(self, nums, k):\\n        ...", "complexity": "时间 O(n)，空间 O(1)", "hints": ["第 1 级：题型方向和识别信号", "第 2 级：核心思路 / 状态定义", "第 3 级：关键步骤"], "key": "核心一句话", "pitfalls": ["易错点 1", "易错点 2"]}
规则：
- types：参数是链表写 "ListNode"，二叉树写 "TreeNode"，链表数组写 "ListNode[]"，其余写 null；tests 里链表和树都写成数组（树用层序数组，空位 null）；
- ret_type：返回链表写 "ListNode"，返回树写 "TreeNode"；原地修改第 0 个参数、没有返回值写 "inplace0"；其余写 null；
- compare：结果顺序无所谓写 "unordered"，内外层顺序都无所谓写 "unordered_deep"，浮点数写 "float"，其余写 "exact"；
- tests 给 8–12 组：前两组和 examples 一致，然后覆盖边界，最后一组稍大（数组长度不超过 200）；每组输入都必须满足约束；
- solution：正确、简洁的 Python 参考解，class Solution，方法名与 fn 一致；页面会用它重新计算每组 expected；
- 只出“调用一个函数、比较返回值”的题；如果题目必须设计类（如 LRU 缓存）或交互式输入输出，返回 {"error": "原因"}。`;

// 图片压到最长边 1600px 的 JPEG 再发给能看图的模型（截图原图常常好几 MB）
async function shrinkImage(src, max = 1600) {
  let img = src, url = null;
  if (!(src instanceof HTMLCanvasElement)) {
    url = typeof src === "string" ? src : URL.createObjectURL(src);
    img = await new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("图片读不出来")); im.src = url; });
  }
  try {
    const w = img.naturalWidth || img.width, hh = img.naturalHeight || img.height, k = Math.min(1, max / Math.max(w, hh, 1));
    const c = document.createElement("canvas"); c.width = Math.max(1, Math.round(w * k)); c.height = Math.max(1, Math.round(hh * k));
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.drawImage(img, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", 0.9);
  } finally { if (url && typeof src !== "string") URL.revokeObjectURL(url); }
}
function arrStr(a, n) { return Array.isArray(a) ? a.slice(0, n).map(x => String(x)) : []; }
function normalizeProblem(o, extra = {}) {
  if (!o || typeof o !== "object" || Array.isArray(o)) throw new Error("AI 没有返回题目");
  if (o.error) throw new Error(String(o.error));
  for (const k of ["title", "desc", "fn", "params", "ret", "tests", "solution"]) if (!o[k]) throw new Error("生成的题目缺少字段 " + k);
  const fn = String(o.fn);
  if (!/^[A-Za-z_]\w*$/.test(fn)) throw new Error("函数名不合法：" + fn);
  const params = (Array.isArray(o.params) ? o.params : []).map(x => Array.isArray(x) ? [String(x[0]), String(x[1] || "Any")] : [String(x && x.name), String((x && x.type) || "Any")]);
  if (!params.length || params.some(([n]) => !/^[A-Za-z_]\w*$/.test(n))) throw new Error("参数列表不合法");
  const T = ["ListNode", "TreeNode", "ListNode[]"];
  const types = params.map((_, i) => (Array.isArray(o.types) && T.includes(o.types[i])) ? o.types[i] : null);
  const tests = (Array.isArray(o.tests) ? o.tests : []).map(t => Array.isArray(t) ? { args: t } : (t && Array.isArray(t.args) ? ("expected" in t ? { args: t.args, expected: t.expected } : { args: t.args }) : null))
    .filter(t => t && t.args.length === params.length).slice(0, 16);
  if (tests.length < 3) throw new Error("可用的测试用例太少");
  const ret = String(o.ret);
  return Object.assign({
    id: "c-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5),
    custom: true, createdAt: Date.now(),
    title: clip(o.title, 40), pattern: PMAP[o.pattern] ? o.pattern : "custom",
    level: ["easy", "medium", "hard"].includes(o.level) ? o.level : "medium",
    desc: String(o.desc),
    examples: (Array.isArray(o.examples) ? o.examples : []).slice(0, 4).map(e => ({ input: String((e && e.input) ?? ""), output: String((e && e.output) ?? ""), note: String((e && e.note) ?? "") })),
    constraints: arrStr(o.constraints, 8), fn, params, ret, types,
    ret_type: ["ListNode", "TreeNode", "inplace0"].includes(o.ret_type) ? o.ret_type : null,
    compare: ["exact", "unordered", "unordered_deep", "float"].includes(o.compare) ? o.compare : "exact",
    tests, solution: String(o.solution), complexity: String(o.complexity || ""),
    hints: arrStr(o.hints, 3), key: String(o.key || ""), pitfalls: arrStr(o.pitfalls, 4),
    starter: `class Solution:\n    def ${fn}(self, ${params.map(([n, t]) => `${n}: ${t}`).join(", ")}) -> ${ret}:\n        `,
    lc: null, slug: null,
    change: o.change ? String(o.change) : "",
  }, extra);
}
async function verifyProblem(p, step) {
  if (S.py === "loading") { step("等 Python 运行环境就绪……"); await Py.ready; }
  if (S.py !== "ready") {
    p.unverified = true;
    p.tests = p.tests.filter(t => "expected" in t);
    if (p.tests.length < 3) throw new Error("Python 运行环境不可用，而且 AI 没给出足够的答案，没法判题");
    return p;
  }
  step("用参考解重新计算每组用例的答案……");
  let refs;
  try { refs = await Py.json("run_reference", [p.solution, specOf(p, p.tests.map(t => ({ args: t.args })))], 15000); }
  catch (e) { throw new Error("参考解运行失败：" + (e.message || "")); }
  let fixed = 0;
  const tests = [];
  p.tests.forEach((t, i) => {
    const r = refs[i];
    if (!r || r.error) return;
    if ("expected" in t && JSON.stringify(t.expected) !== JSON.stringify(r.expected)) fixed++;
    tests.push({ args: t.args, expected: r.expected });
  });
  if (tests.length < 3) throw new Error("参考解在大多数用例上报错，这道题生成得不好，再试一次");
  p.tests = tests;
  p.fixed = fixed;
  return p;
}
async function generateProblem(prompt, { images, step, extra }) {
  step("AI 正在出题……（通常 20–60 秒）");
  const raw = await AI.ask(prompt, { json: true, tier: "complex", images });
  const p = normalizeProblem(raw, extra);
  await verifyProblem(p, step);
  if (JSON.stringify(p).length > 200000) throw new Error("题目太大了，存不下");
  await Store.put("x:" + p.id, p);
  return p;
}
