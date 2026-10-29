// ---------- 小眼：挂在右下角的学习搭子 ----------
// 点它聊天；页面上任何地方选中的文字都能直接问；可以框选页面截图，或者粘贴 / 拖入外部截图
const BUDDY_SYS = `你是「小眼」，「题眼」学习网站右下角的学习搭子。学习者在准备 Agent / Harness / AI 测试开发 / 后端方向的社招面试，也在用 Python 刷算法题。
他可能：选中页面上的一段文字问你；发页面区域截图（会同时附上从页面直接读出的文字，以文字为准）；发外部截图（题目、报错、面试题、手写思路，你直接看图）。
回答方式：
1. 先给结论，再用大白话解释为什么，必要时举例或给代码；和面试相关时补一句“面试里怎么答”。
2. 查漏补缺：他的说法有错就直接指出并纠正，不要顺着说。
3. 他在做题时先引导、给提示，不要一上来贴完整答案，除非他要。
4. 站内资料用 search_notes / read_section 查，引用时说出处；站内没有就用通用知识。
5. 语气像靠谱的学长 / 搭子：亲切、直接、不啰嗦，一般 400 字以内。`;
const BUDDY_ACTIONS = [
  ["讲讲这一页", "用大白话给我讲讲我现在看的这一页：最重要的 3 个点是什么，面试里会怎么问。"],
  ["我卡住了", "我在这一页卡住了。先问我卡在哪一步（给我 2–3 个可能的选项），再一步步引导我，不要直接给完整答案。"],
  ["考考我", "根据我现在看的这一页，出一道最可能在面试里被问到的题考我。只出题，等我回答后再点评：哪里想错了、更好的答法、下次怎么想。"],
  ["总结成速记卡", "把这一页总结成一张能背下来的速记卡：核心概念、关键数字或公式、易错点、面试一句话答法。"],
];
const BUDDY_PET = `<svg viewBox="0 0 72 72" aria-hidden="true">
  <ellipse class="bd-shadow" cx="36" cy="67" rx="17" ry="3"/>
  <g class="bd-bod">
    <path class="bd-tuft" d="M33 9c1-5 5-7 9-6-3 1-5 3-5 6"/>
    <path class="bd-body" d="M36 8c15 0 27 11 27 28 0 17-11 27-27 27S9 53 9 36C9 19 21 8 36 8z"/>
    <ellipse class="bd-blush" cx="19" cy="44" rx="4.5" ry="2.6"/><ellipse class="bd-blush" cx="53" cy="44" rx="4.5" ry="2.6"/>
    <g class="bd-eyes">
      <g class="bd-eye"><ellipse class="bd-white" cx="27" cy="34" rx="7" ry="8"/><circle class="bd-pupil" cx="27" cy="35" r="3.6"/><circle class="bd-shine" cx="28.4" cy="33.2" r="1.1"/></g>
      <g class="bd-eye"><ellipse class="bd-white" cx="45" cy="34" rx="7" ry="8"/><circle class="bd-pupil" cx="45" cy="35" r="3.6"/><circle class="bd-shine" cx="46.4" cy="33.2" r="1.1"/></g>
    </g>
    <path class="bd-mouth" d="M32 47q4 4 8 0"/>
  </g>
  <text class="bd-z" x="54" y="14">z</text>
</svg>`;
const Buddy = {
  open: false, provider: null, quote: null, att: [], lib: null, unread: false, idleAt: Date.now(),
  init() {
    if (this.root) return;
    const hist = LS.get("tiyan:buddy:hist", []);
    if (!S.chats.buddy && Array.isArray(hist)) S.chats.buddy = hist;
    this.root = h("div", { class: "bd-root" + (LS.get("tiyan:buddy:hidden", false) ? " tucked" : "") });
    // 宠物本体
    this.pet = h("button", { class: "bd-pet", type: "button", title: "小眼：点我聊天；选中页面文字可以直接问我", "aria-label": "打开小眼" });
    this.pet.innerHTML = BUDDY_PET;
    this.badge = h("span", { class: "bd-badge", hidden: true });
    this.say = h("div", { class: "bd-say", hidden: true });
    this.tab = h("button", { class: "bd-tab", type: "button", title: "叫出小眼", onclick: () => this.tuck(false) }, "👀");
    this.pet.append(this.badge);
    // 面板
    this.chat = new Chat({
      key: "buddy", who: ["小眼", "学习搭子"], context: () => this.context(),
      placeholder: "问我任何问题……（Enter 发送；⌘V / Ctrl+V 直接粘贴截图）",
      intro: "嗨，我是小眼 👀 有不懂的随时问我：\n- 在页面上**选中任何文字**，旁边会冒出「问小眼」；\n- 点下面的「截图」框选页面的一块区域发给我，或者直接**粘贴 / 拖进来**外部截图；\n- 我能看到你现在在哪一页，也能查站内资料。",
    });
    const raw = this.chat.send.bind(this.chat);
    this.chat.send = (prompt, o = {}) => {
      const lib = this.buddyLib();
      if (!o.noPrefetch) {
        const hits = lib.search(prompt, 2);
        if (hits.length) prompt += "\n\n【可能相关的站内资料（本地检索，可能不全）】\n" + hits.map(c => `[${c.id}]【${c.where}】\n${clip(c.text, 1200)}`).join("\n\n");
      }
      const p = raw(prompt, Object.assign({ tools: libTools(lib) }, o));
      this.mood("think");
      Promise.resolve(p).then(() => this.answered(), () => this.answered());
      return p;
    };
    this.chat.submit = () => this.submit();
    this.actRow = h("div", { class: "chat-actions" });
    this.chat.el.insertBefore(this.actRow, this.chat.list);
    this.tray = h("div", { class: "bd-tray", hidden: true });
    const composer = $(".composer", this.chat.el);
    composer.parentNode.insertBefore(this.tray, composer);
    this.file = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp,image/gif", multiple: true, hidden: true });
    this.file.addEventListener("change", () => { for (const f of this.file.files) this.addImage(f); this.file.value = ""; });
    const tools = $(".composer .row .row", this.chat.el);
    tools.append(h("button", { class: "btn ghost sm", type: "button", title: "框选页面上的一块区域发给小眼", onclick: () => this.capture() }, "✂︎ 截图"),
      h("button", { class: "btn ghost sm", type: "button", title: "发一张图片（也可以直接粘贴或拖进来）", onclick: () => this.file.click() }, icon("image"), "图片"), this.file);
    this.chat.ta.addEventListener("paste", e => this.onPaste(e));
    this.whereEl = h("span", { class: "small faint bd-where" });
    this.panel = h("section", { class: "bd-panel", hidden: true, "aria-label": "小眼" },
      h("div", { class: "bd-head" }, h("span", { class: "bd-mini", html: BUDDY_PET }), h("div", { class: "stack", style: "gap:0;min-width:0;flex:1" }, h("b", null, "小眼 · 学习搭子"), this.whereEl),
        h("button", { class: "btn ghost sm", type: "button", title: "清空和小眼的对话", onclick: () => this.reset() }, "新对话"),
        h("button", { class: "btn ghost sm", type: "button", title: "把小眼收到屏幕边上", onclick: () => this.tuck(true) }, "藏起来"),
        h("button", { class: "btn ghost sm bd-x", type: "button", "aria-label": "关闭", onclick: () => this.toggle(false) }, "✕")),
      this.chat.el);
    this.panel.addEventListener("dragover", e => { if ([...(e.dataTransfer.items || [])].some(i => i.kind === "file")) { e.preventDefault(); this.panel.classList.add("drop"); } });
    this.panel.addEventListener("dragleave", e => { if (!this.panel.contains(e.relatedTarget)) this.panel.classList.remove("drop"); });
    this.panel.addEventListener("drop", e => { e.preventDefault(); this.panel.classList.remove("drop"); for (const f of e.dataTransfer.files) if (/^image\//.test(f.type)) this.addImage(f); });
    // 选中文字后冒出来的小气泡
    this.sel = h("div", { class: "bd-sel", hidden: true },
      h("button", { type: "button", class: "on", onclick: () => this.fromSel("ask") }, "👀 问小眼"),
      h("button", { type: "button", onclick: () => this.fromSel("explain") }, "解释"),
      h("button", { type: "button", onclick: () => this.fromSel("quiz") }, "考我"));
    this.sel.addEventListener("mousedown", e => e.preventDefault());
    this.root.append(this.panel, this.say, this.pet, this.tab, this.sel);
    document.body.append(this.root);
    this.drag();
    this.place();
    this.renderActions();
    this.listen();
    if (!LS.get("tiyan:buddy:greeted", false)) setTimeout(() => { this.talk("我是小眼～ 选中页面上的任何文字就能问我，也可以截图给我 👀", 9000); LS.set("tiyan:buddy:greeted", true); }, 1800);
  },
  // ----- 上下文：页面专属（设计编码会注册自己的老师上下文）或通用页面内容 -----
  provide(p) { this.provider = p; this.renderActions(); this.refresh(); },
  refresh() { if (this.whereEl) this.whereEl.textContent = (this.provider && this.provider.where ? this.provider.where() : "") || this.pageWhere(); },
  pageWhere() {
    const r = S.route || {}, nav = (typeof NAV !== "undefined" ? NAV : []).find(([k]) => k === r.view), t = $("#main h1");
    return [nav ? nav[1] : "", t ? t.textContent.trim() : ""].filter(Boolean).join(" › ") || "题眼";
  },
  pageText() { const m = $("#main"); return m ? clip(m.innerText.replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n"), 3500) : ""; },
  context() {
    const base = BUDDY_SYS;
    if (this.provider) return base + "\n\n" + this.provider.context();
    return base + `\n\n【学习者现在在】${this.pageWhere()}\n【这一页的主要内容（节选，帮你理解他在看什么）】\n${this.pageText()}`;
  },
  buddyLib() {
    if (this.lib) return this.lib;
    const items = [];
    for (const c of (typeof KNOW !== "undefined" ? KNOW : [])) for (const s of c.sections || []) items.push({ id: "k-" + s.id, where: `AI 知识 › ${c.name} › ${s.title}`, text: [s.title, s.summary, s.md, (s.points || []).join("\n")].filter(Boolean).join("\n") });
    for (const s of (typeof PYDATA !== "undefined" ? PYDATA.sections : [])) items.push({ id: "py-" + s.id, where: `Python › ${s.title}`, text: [s.title, s.summary, s.md, s.algo, (s.pitfalls || []).join("\n")].filter(Boolean).join("\n") });
    const sd = typeof sdLib === "function" && SDD.blocks.length ? sdLib().items : [];
    return this.lib = new Library(items.concat(sd.map(x => ({ id: x.id, where: x.where, text: x.text }))));
  },
  renderActions() {
    if (!this.actRow) return;
    const acts = this.provider && this.provider.actions ? this.provider.actions : BUDDY_ACTIONS.map(([label, prompt]) => ({ label, run: c => c.send(prompt, { label }) }));
    this.actRow.textContent = "";
    for (const a of acts) { const b = h("button", { class: "chip", type: "button" }, a.label); b.addEventListener("click", () => { if (!this.chat.busy) a.run(this.chat); }); this.actRow.append(b); }
  },
  // ----- 打开 / 发送 -----
  toggle(v) {
    this.open = v == null ? !this.open : v;
    this.panel.hidden = !this.open;
    this.root.classList.toggle("opened", this.open);
    if (this.open) { this.tuck(false); this.unread = false; this.badge.hidden = true; this.say.hidden = true; this.refresh(); this.place(); setTimeout(() => { this.chat.scroll(); this.chat.ta.focus(); }, 30); }
  },
  ask(prompt, label, quote) { this.toggle(true); this.send(prompt, label, quote || null, []); },
  submit() {
    const text = this.chat.ta.value.trim();
    if (!text && !this.att.length && !this.quote) return;
    if (this.att.some(a => a.pending)) { toast("截图还在处理，稍等一下"); return; }
    this.chat.ta.value = ""; this.chat.ta.style.height = "auto";
    const quote = this.quote, att = this.att.slice();
    this.quote = null; this.att = []; this.drawTray();
    this.send(text, "", quote, att);
  },
  send(text, label, quote, att) {
    let prompt = text || (att.length ? "请看我发的截图：先说清它在讲什么，再回答或讲解里面的问题。" : quote ? "这段我没看懂，请用大白话解释一下。" : "");
    if (quote) prompt = `我在页面上选中了这段（出自：${quote.where}）：\n「${clip(quote.text, 3000)}」\n\n${prompt}`;
    att.forEach((a, i) => { if (a.text) prompt += `\n\n【截图 ${i + 1} 框选区域里的文字（从页面直接读出，比看图更准）】\n${clip(a.text, 4000)}`; });
    const imgs = att.map(a => a.url).filter(Boolean);
    const disp = (label ? "" : text || (att.length ? "看看这张截图" : "解释一下")) + (quote ? `\n> ${clip(quote.text.replace(/\s+/g, " "), 80)}` : "");
    this.chat.send(prompt, { label: label || "", display: disp, images: imgs, thumbs: imgs });
  },
  answered() {
    this.save();
    this.mood(null);
    if (!this.open) { this.unread = true; this.badge.hidden = false; this.talk("回答好了，点我看 👀", 6000); }
    this.hop();
  },
  save() { LS.set("tiyan:buddy:hist", (S.chats.buddy || []).slice(-30).map(m => ({ role: m.role, content: clip(m.content || "", 8000), label: m.label || "", display: m.display != null ? clip(m.display, 300) : undefined }))); },
  reset() {
    const j = CHAT_JOBS.buddy; if (j) j.ctl.abort();
    (S.chats.buddy || []).length = 0; LS.del("tiyan:buddy:hist");
    this.chat.list.textContent = ""; this.quote = null; this.att = []; this.drawTray();
    toast("已开始新对话");
  },
  // ----- 附件托盘：引用的文字、截图 -----
  setQuote(text, where) { this.quote = { text, where: where || this.pageWhere() }; this.drawTray(); },
  drawTray() {
    this.tray.textContent = "";
    if (this.quote) this.tray.append(h("div", { class: "bd-chip q" }, h("span", null, "引用：" + clip(this.quote.text.replace(/\s+/g, " "), 60)), h("button", { type: "button", "aria-label": "去掉引用", onclick: () => { this.quote = null; this.drawTray(); } }, "✕")));
    this.att.forEach(a => this.tray.append(h("div", { class: "bd-chip" }, a.url ? h("img", { src: a.url, alt: "" }) : h("span", { class: "thinking" }, ""),
      h("span", null, a.pending ? "截图处理中……" : a.text ? `页面截图 · 读出 ${a.text.length} 字` : "图片"),
      h("button", { type: "button", "aria-label": "去掉", onclick: () => { this.att = this.att.filter(x => x !== a); this.drawTray(); } }, "✕"))));
    this.tray.hidden = !this.tray.childNodes.length;
  },
  async addImage(file) {
    if (this.att.length >= 4) { toast("一次最多 4 张图"); return; }
    const a = { pending: true, url: "", text: "" };
    this.att.push(a); this.drawTray(); this.toggle(true);
    try { a.url = await shrinkImage(file); } catch (e) { this.att = this.att.filter(x => x !== a); toast("这张图读不出来"); }
    a.pending = false; this.drawTray();
    if (!AI.images) toast("当前模型看不了图片；页面截图会附上读出的文字，外部图片可能用不上");
  },
  onPaste(e) {
    const files = [...(e.clipboardData && e.clipboardData.files || [])].filter(f => /^image\//.test(f.type));
    if (!files.length) return;
    e.preventDefault();
    files.forEach(f => this.addImage(f));
  },
  // ----- 框选页面截图：读出框里的文字 + 渲染一张图 -----
  capture() {
    if (this.capturing) return;
    this.capturing = true;
    const wasOpen = this.open;
    this.panel.hidden = true; this.hideSel();
    const box = h("div", { class: "bd-box", hidden: true });
    const tip = h("div", { class: "bd-cap-tip" }, "拖动鼠标框选要问的区域　·　Esc 取消");
    const cap = h("div", { class: "bd-cap bd-root" }, box, tip);
    let x0 = 0, y0 = 0, rect = null;
    const end = () => { cap.remove(); document.removeEventListener("keydown", esc, true); this.capturing = false; };
    const esc = e => { if (e.key === "Escape") { e.preventDefault(); end(); if (wasOpen) this.toggle(true); } };
    cap.addEventListener("pointerdown", e => { x0 = e.clientX; y0 = e.clientY; box.hidden = false; tip.hidden = true; cap.setPointerCapture(e.pointerId); rect = null; });
    cap.addEventListener("pointermove", e => {
      if (box.hidden) return;
      const l = Math.min(x0, e.clientX), t = Math.min(y0, e.clientY), w = Math.abs(e.clientX - x0), hh = Math.abs(e.clientY - y0);
      Object.assign(box.style, { left: l + "px", top: t + "px", width: w + "px", height: hh + "px" });
      rect = { left: l, top: t, width: w, height: hh, right: l + w, bottom: t + hh };
    });
    cap.addEventListener("pointerup", async () => {
      end();
      if (!rect || rect.width < 12 || rect.height < 12) { if (wasOpen) this.toggle(true); return; }
      const a = { pending: true, url: "", text: this.textIn(rect) };
      this.att.push(a); this.toggle(true); this.drawTray();
      try { a.url = await this.snap(rect); } catch (e) { /* 渲染失败也没关系：框里的文字已经读出来了 */ }
      a.pending = false; this.drawTray();
      if (!a.url && !a.text) { this.att = this.att.filter(x => x !== a); this.drawTray(); toast("框里没有读到内容，换个区域试试"); }
    });
    document.addEventListener("keydown", esc, true);
    document.body.append(cap);
  },
  textIn(r) {
    const hit = q => q.width && q.height && q.right > r.left && q.left < r.right && q.bottom > r.top && q.top < r.bottom;
    const skip = el => !el || el.closest(".bd-root, script, style, noscript, .CodeMirror-measure");
    const out = [];
    let lastBottom = null;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: n => n.nodeValue.trim() && !skip(n.parentElement) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
    const range = document.createRange();
    for (let n; (n = walker.nextNode());) {
      range.selectNodeContents(n);
      const rs = [...range.getClientRects()].filter(hit);
      if (!rs.length) continue;
      const t = n.nodeValue.replace(/\s+/g, " ").trim();
      if (lastBottom != null) out.push(rs[0].top >= lastBottom - 3 ? "\n" : " ");
      out.push(t);
      lastBottom = rs[rs.length - 1].bottom;
    }
    for (const el of document.querySelectorAll("textarea, input[type=text], input:not([type])")) {
      if (skip(el) || !el.value.trim() || el.closest(".CodeMirror")) continue;
      if (hit(el.getBoundingClientRect())) out.push("\n【输入框里的内容】" + clip(el.value, 2000));
    }
    return out.join("").replace(/\n{3,}/g, "\n\n").trim().slice(0, 8000);
  },
  async snap(r) {
    await loadScript("vendor/html2canvas-pro.min.js");
    const fn = typeof window.html2canvas === "function" ? window.html2canvas : window.html2canvas && window.html2canvas.default;
    const canvas = await fn(document.body, {
      x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width, height: r.height,
      scale: Math.min(2, window.devicePixelRatio || 1), backgroundColor: getComputedStyle(document.body).backgroundColor, logging: false,
      ignoreElements: el => !!(el.classList && el.classList.contains("bd-root")),
    });
    return shrinkImage(canvas);
  },
  // ----- 选中文字 → 冒气泡 -----
  listen() {
    const later = e => setTimeout(() => this.onSelect(e), 0);
    document.addEventListener("mouseup", later);
    document.addEventListener("keyup", e => { if (e.key === "Shift" || e.shiftKey) later(null); });
    let st = null;
    document.addEventListener("selectionchange", () => { if (!this.touch) return; clearTimeout(st); st = setTimeout(() => this.onSelect(null), 500); });
    document.addEventListener("touchstart", () => { this.touch = true; }, { passive: true });
    document.addEventListener("mousedown", e => { this.touch = false; if (!e.target.closest(".bd-sel")) this.hideSel(); });
    let dt = 0;
    const dodgeSoon = ms => { clearTimeout(dt); dt = setTimeout(() => this.dodge(), ms || 180); };
    window.addEventListener("scroll", () => { this.hideSel(); dodgeSoon(); }, { passive: true });
    window.addEventListener("resize", () => { this.place(); dodgeSoon(); });
    window.addEventListener("hashchange", () => { this.hideSel(); setTimeout(() => this.refresh(), 0); dodgeSoon(400); });
    document.addEventListener("click", () => dodgeSoon(250));
    dodgeSoon(600);
    document.addEventListener("paste", e => { if (this.open && !(e.target.closest && e.target.closest("textarea, input, [contenteditable], .CodeMirror"))) this.onPaste(e); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") { this.hideSel(); if (this.open && this.panel.contains(document.activeElement)) this.toggle(false); } });
    let raf = 0;
    document.addEventListener("pointermove", e => { this.idleAt = Date.now(); if (this.root.classList.contains("sleep")) this.mood(null); if (raf) return; raf = requestAnimationFrame(() => { raf = 0; this.look(e.clientX, e.clientY); }); }, { passive: true });
    setInterval(() => { if (!this.open && Date.now() - this.idleAt > 180000 && !this.root.classList.contains("think")) this.mood("sleep"); }, 15000);
  },
  onSelect(e) {
    if (this.capturing) return;
    if (e && e.target && e.target.closest && e.target.closest(".bd-sel")) return;
    let text = "", rect = null;
    const ae = document.activeElement, pt = e ? { left: e.clientX, right: e.clientX, top: e.clientY, bottom: e.clientY } : null;
    const cm = ae && ae.closest && ae.closest(".CodeMirror");
    if (cm && cm.CodeMirror) { text = cm.CodeMirror.getSelection(); rect = pt || cm.getBoundingClientRect(); }
    else if (ae && (ae.tagName === "TEXTAREA" || ae.tagName === "INPUT") && ae.selectionEnd > ae.selectionStart) {
      if (ae.closest(".bd-root")) { this.hideSel(); return; }
      text = ae.value.slice(ae.selectionStart, ae.selectionEnd); rect = pt || ae.getBoundingClientRect();
    } else {
      const ws = window.getSelection();
      text = ws ? String(ws) : "";
      if (text.trim() && ws.rangeCount) { const q = ws.getRangeAt(0).getBoundingClientRect(); rect = q.width || q.height ? q : pt; }
    }
    text = (text || "").trim();
    if (text.length < 2 || text.length > 6000 || !rect) { this.hideSel(); return; }
    this.selText = text; this.selWhere = this.pageWhere();
    this.sel.hidden = false;
    const w = this.sel.offsetWidth || 200, below = rect.bottom + 8 + 40 < window.innerHeight;
    this.sel.style.top = (below ? rect.bottom + 8 : Math.max(8, rect.top - 44)) + "px";
    this.sel.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - w - 8)) + "px";
    this.look(rect.left, rect.top); this.hop();
  },
  hideSel() { if (this.sel) this.sel.hidden = true; },
  fromSel(kind) {
    const text = this.selText, where = this.selWhere;
    this.hideSel();
    if (!text) return;
    if (kind === "ask") { this.setQuote(text, where); this.toggle(true); return; }
    const q = { text, where };
    if (kind === "explain") this.ask("用大白话解释我选中的这段：它在说什么、为什么这样，必要时举个例子；如果和面试有关，补一句面试里怎么答。", "解释", q);
    else this.ask("根据我选中的这段，出一道最可能被面试官问到的题考我。只出题，等我回答后再点评：哪里想错了、更好的答法、下次怎么想。", "考我", q);
  },
  // ----- 宠物：眼睛跟着鼠标、思考 / 睡觉 / 跳一下、说话、拖动 -----
  look(x, y) {
    if (!this.pet || this.root.classList.contains("sleep")) return;
    const r = this.pet.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height * 0.45;
    const dx = x - cx, dy = y - cy, d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 160) * 2.6;
    for (const p of this.pet.querySelectorAll(".bd-pupil, .bd-shine")) p.style.transform = `translate(${(dx / d * k).toFixed(2)}px, ${(dy / d * k).toFixed(2)}px)`;
  },
  mood(m) { this.root.classList.remove("think", "sleep"); if (m) this.root.classList.add(m); },
  hop() { this.root.classList.remove("hop"); void this.pet.offsetWidth; this.root.classList.add("hop"); setTimeout(() => this.root.classList.remove("hop"), 600); },
  talk(text, ms) { if (this.open) return; this.say.textContent = text; this.say.hidden = false; clearTimeout(this.sayT); this.sayT = setTimeout(() => { this.say.hidden = true; }, ms || 5000); this.placeSay(); },
  tuck(v) { this.root.classList.toggle("tucked", v); LS.set("tiyan:buddy:hidden", v); if (v) { this.panel.hidden = true; this.open = false; this.root.classList.remove("opened"); } },
  drag() {
    let sx = 0, sy = 0, ox = 0, oy = 0, moved = false, down = false;
    this.pet.addEventListener("pointerdown", e => { down = true; moved = false; sx = e.clientX; sy = e.clientY; const r = this.pet.getBoundingClientRect(); ox = r.left; oy = r.top; this.pet.setPointerCapture(e.pointerId); });
    this.pet.addEventListener("pointermove", e => {
      if (!down) return;
      if (!moved && Math.hypot(e.clientX - sx, e.clientY - sy) < 6) return;
      moved = true; this.root.classList.add("dragging");
      const s = this.pet.offsetWidth;
      const x = Math.max(4, Math.min(window.innerWidth - s - 4, ox + e.clientX - sx)), y = Math.max(4, Math.min(window.innerHeight - s - 4, oy + e.clientY - sy));
      this.pos = { right: window.innerWidth - x - s, bottom: window.innerHeight - y - s };
      this.place();
    });
    this.pet.addEventListener("pointerup", () => { if (!down) return; down = false; this.root.classList.remove("dragging"); if (moved) LS.set("tiyan:buddy:pos", this.pos); else this.toggle(); });
  },
  place() {
    if (!this.pet) return;
    const p = this.pos || LS.get("tiyan:buddy:pos", null), s = this.pet.offsetWidth || 64;
    const right = p ? Math.max(4, Math.min(window.innerWidth - s - 4, p.right)) : null, bottom = p ? Math.max(4, Math.min(window.innerHeight - s - 4, p.bottom)) : null;
    this.pet.style.right = right == null ? "" : right + "px"; this.pet.style.bottom = bottom == null ? "" : bottom + "px";
    if (this.open && window.innerWidth > 720) {
      // 上方放得下就放上方，其次下方，都不够就放在宠物旁边；面板不能盖住宠物
      const W = window.innerWidth, H = window.innerHeight, r = this.pet.getBoundingClientRect(), pw = Math.min(420, W - 24);
      const above = r.top - 22, below = H - r.bottom - 22, onRight = r.left + r.width / 2 > W / 2;
      let ph = Math.min(640, H - 24), left, top;
      if (above >= Math.min(ph, 520) || below >= Math.min(ph, 520)) {
        const up = above >= below;
        ph = Math.min(ph, up ? above : below);
        left = onRight ? Math.max(12, r.right - pw) : Math.min(W - pw - 12, r.left);
        top = up ? r.top - ph - 10 : r.bottom + 10;
      } else {
        left = onRight ? Math.max(12, r.left - pw - 12) : Math.min(W - pw - 12, r.right + 12);
        top = Math.max(12, Math.min(H - ph - 12, r.top + r.height / 2 - ph / 2));
      }
      Object.assign(this.panel.style, { left: left + "px", top: top + "px", width: pw + "px", height: ph + "px" });
    } else Object.assign(this.panel.style, { left: "", top: "", width: "", height: "" });
    this.placeSay();
  },
  // 没被拖过时自动避让：身下压着按钮 / 链接 / 输入框就往上挪，最多挪 5 格
  dodge() {
    if (!this.pet || this.pos || LS.get("tiyan:buddy:pos", null) || this.root.classList.contains("tucked") || this.root.classList.contains("dragging")) return;
    const blocked = () => {
      const r = this.pet.getBoundingClientRect();
      return [[r.left + 8, r.top + 10], [r.right - 8, r.top + 10], [r.left + 8, r.bottom - 8], [r.right - 8, r.bottom - 8], [r.left + r.width / 2, r.top + r.height / 2]]
        .some(([x, y]) => document.elementsFromPoint(x, y).some(el => !el.closest(".bd-root") && el.closest("button, a, input, textarea, select, label, .CodeMirror, .chip, [role=button]")));
    };
    let off = 0;
    this.root.classList.add("measuring");
    for (let i = 0; i <= 5; i++) { this.pet.style.setProperty("--bd-dodge", off + "px"); if (!blocked()) break; off += 52; }
    if (off > 52 * 5) { off = 0; this.pet.style.setProperty("--bd-dodge", "0px"); }
    this.root.classList.remove("measuring");
    this.placeSay();
  },
  placeSay() {
    if (!this.say || this.say.hidden) return;
    const r = this.pet.getBoundingClientRect(), w = this.say.offsetWidth || 220;
    this.say.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left + r.width / 2 - w + 30)) + "px";
    this.say.style.top = Math.max(8, r.top - this.say.offsetHeight - 10) + "px";
  },
};
