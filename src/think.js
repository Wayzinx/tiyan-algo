// ---------- 思路：拿到题怎么想（起手式 / 思路阶梯 / 盲写基本功；识题沿用 #quiz） ----------
// 阶梯与基本功来自 data/think/*.py + data/think_kit.py → gen_think.py → think.json；进度存 tiyan:think、tiyan:think:kit
const THINK = (() => { try { return JSON.parse(document.getElementById("think-data").textContent); } catch (e) { return { ladders: {}, kit: [] }; } })();
const TH_TABS = [["think", "起手式"], ["think-list", "思路阶梯"], ["think-kit", "盲写基本功"], ["quiz", "识题"]];
const TH_STEP = { ask: "它要什么", input: "题眼在哪", brute: "暴力怎么写", waste: "暴力浪费在哪", tool: "换成什么", state: "不变量 / 状态" };
const TH_REC = ["top-k-routes", "longest-substring-without-repeating-characters", "longest-palindromic-substring", "two-sum", "move-zeroes", "top-k-frequent-elements",
  "kth-largest-element-in-an-array", "reverse-linked-list", "merge-two-sorted-lists", "maximum-depth-of-binary-tree", "binary-tree-level-order-traversal", "number-of-islands",
  "climbing-stairs", "house-robber", "coin-change", "merge-intervals", "subsets", "permutations", "search-insert-position", "daily-temperatures", "subarray-sum-equals-k", "group-anagrams"];
const TH = {
  all() { return LS.get("tiyan:think", {}); },
  get(pid) { return this.all()[pid] || null; },
  set(pid, patch) { const all = this.all(); all[pid] = Object.assign({}, all[pid], patch, { at: Date.now() }); LS.set("tiyan:think", all); },
};
const TH_RUNS = {};   // 本次打开页面期间每题的作答：{ pid: { k: 选中的原始下标 } }

function thTabs(cur) {
  return h("nav", { class: "page-tabs", "aria-label": "思路" }, TH_TABS.map(([k, t]) => h("a", { href: "#" + k, class: k === cur ? "on" : "" }, t)));
}
function thPage(k, eyebrow, title, lede, ...body) {
  return h("div", { class: "page wide" }, h("section", { class: "hero", style: "gap:8px" }, h("div", { class: "eyebrow" }, "思路 · " + eyebrow), h("h1", null, title), lede ? h("p", { class: "lede" }, lede) : ""), thTabs(k), ...body);
}
function viewThink(r) {
  const sub = r.sub || "";
  if (sub === "list") return viewThinkList();
  if (sub === "kit") return viewThinkKit();
  if (sub && THINK.ladders[sub]) return viewLadder(sub);
  return viewThinkMethod();
}

// ---------- 起手式 ----------
const TH_FIVE = [
  ["复述 + 手算一个小例子", "用自己的话说一遍：输入是什么、输出是什么、边界怎么算。拿最小的例子在纸上走一遍。", "A→B 和 B→A 算一条吗？起点等于终点算吗？k 比路线数还大怎么办？"],
  ["看输出，定方向", "输出的类型几乎决定了方法族：最值、计数、真假、所有方案、前 k 个、最少步数……（见下表）", "要“次数最多的前 k 条” → Top K → 先计数，再排序或用堆。"],
  ["先写暴力，别怕慢", "把所有候选答案列出来，逐个检查。暴力不是丢人，是思路的起点，也是面试里的保底分。", "遍历请求，用列表记出现过的路线和次数，最后整体排序取前 k。"],
  ["找浪费，换工具", "问自己：暴力里哪一步在重复干活？哪层循环只是在“找东西”？对照下面的“浪费 → 工具”表换掉它。", "在列表里找路线是 O(n) → 换 dict / Counter，O(1)；全排序只为前 k → 数据大时换大小为 k 的堆。"],
  ["写下不变量，再写代码", "用一句话说清每个变量的含义（窗口里…… / dp[i] 表示…… / 栈里……）。代码就是在维护这句话。", "cnt[(小, 大)] = 这条路线到目前为止被请求的次数。"],
];
const TH_OUTPUT = [
  ["最长 / 最短 / 最大 / 最小", "最值", "滑动窗口、动态规划、贪心、二分答案"],
  ["有多少个 / 多少种", "计数", "前缀和 + 哈希、动态规划"],
  ["能不能 / 是否存在", "真假", "哈希、BFS / DFS、动态规划、贪心"],
  ["列出所有组合 / 排列 / 路径", "所有方案", "回溯（+ 剪枝）"],
  ["第 k 大 / 前 k 个 / 最频繁", "Top K", "堆、排序、快速选择"],
  ["最少几步 / 最短路径", "最短", "BFS（边权相同）、Dijkstra（带权）"],
  ["在哪个位置 / 第一个满足的", "位置", "二分、哈希"],
  ["每个元素右边第一个更大 / 更小", "每个位置各一个答案", "单调栈"],
];
const TH_WASTE = [
  ["内层循环只是在找“某个值在不在 / 在哪”", "哈希表", "seen = set() / pos = {}，查找 O(n) → O(1)"],
  ["左端点右移后，右端点又退回去重扫", "滑动窗口 / 双指针", "两个下标都只往右走，O(n²) → O(n)"],
  ["反复计算某一段的和", "前缀和", "pre[r+1] - pre[l]，每次 O(1)"],
  ["在有序数据里一个个往后找", "二分", "bisect_left / 手写 lo, hi，O(n) → O(log n)"],
  ["每个元素都往右扫一遍找第一个更大的", "单调栈", "栈里存还没找到答案的下标"],
  ["只为了前 k 个，却每次都全排序", "堆", "heapq 维护大小为 k 的堆，O(n log k)"],
  ["递归里同样的参数被算了很多遍", "记忆化 / 动态规划", "@cache，或者改成 dp 数组递推"],
  ["枚举所有方案，明显不可能的分支还在往下走", "回溯 + 剪枝", "不满足条件就 return，排序后 break"],
  ["反复问“这两个是不是一组 / 连通吗”", "并查集", "find / union，近似 O(1)"],
  ["每一步都有“现在看最好”的选择，而且选了不后悔", "贪心", "先排序；举不出反例才敢用"],
];
const TH_DS = [
  ["判断在不在、去重", "set", "seen = set(); x in seen"],
  ["计数", "Counter / dict", "cnt = Counter(nums); cnt[x] += 1"],
  ["值 → 下标 / 属性", "dict", "pos[x] = i"],
  ["按某个特征分组", "defaultdict(list)", "g[key].append(x)"],
  ["先进先出、BFS", "deque", "q.append(x); q.popleft()"],
  ["后进先出、匹配、撤销", "list 当栈", "st.append(x); st.pop(); st[-1]"],
  ["反复取最小 / 最大", "heapq", "heappush(h, (key, x)); heappop(h)"],
  ["有序 + 查位置", "排好序的 list + bisect", "bisect_left(a, x)"],
  ["图的邻接关系", "defaultdict(list)", "g[u].append(v)"],
  ["连通分组", "并查集（list）", "parent = list(range(n))"],
];
const TH_STUCK = [
  ["0–2 分钟", "复述 + 澄清", "“我先确认一下：A→B 和 B→A 算同一条对吗？空输入返回空列表？数据量大概多大？”"],
  ["2–5 分钟", "先讲暴力", "“我先给一个直接的做法：……复杂度 O(n²)。先保证正确，再看哪里能优化。”"],
  ["5–10 分钟", "讲优化，确认后再写", "“暴力的瓶颈在……，换成哈希表就能 O(1) 查到。我按这个思路写，可以吗？”"],
  ["卡住 3–5 分钟", "主动说出卡点", "“我现在卡在：想用堆，但不确定怎么同时按次数降序、按字典序升序排。能给个方向吗？”——比沉默 20 分钟好得多"],
  ["写不完整", "先搭骨架", "写函数签名 + 三行注释（① 规范化 ② 计数 ③ 取前 k），能写的先写，写不出的用伪代码标出来"],
  ["写完", "自己跑一遍", "拿题目的例子逐行走一遍，再说边界：空、一个元素、全相同、k 很大；最后报时间和空间复杂度"],
];
function thTable(head, rows, hl) {
  return h("div", { class: "scroll-x" }, h("table", { class: "ptable" },
    h("thead", null, h("tr", null, head.map(x => h("th", null, x)))),
    h("tbody", null, rows.map(r => h("tr", null, r.map((c, i) => h("td", { class: i === hl ? "" : i === r.length - 1 && head.length > 2 ? "mono small" : "" }, i === hl ? h("span", { class: "redpen" }, c) : c)))))));
}
function viewThinkMethod() {
  const n = Object.keys(THINK.ladders).length;
  const all = TH.all();
  const done = Object.keys(THINK.ladders).filter(pid => all[pid] && all[pid].steps === 6).length;
  return h("div", { class: "page wide" },
    h("section", { class: "hero" },
      h("div", { class: "eyebrow" }, "思路 · 拿到题怎么想"),
      h("h1", null, "脑子一懵的时候，", h("span", { class: "circ" }, "按这五步走", h("span", { html: CIRCLE }))),
      h("p", { class: "lede" }, "想不到思路，往往不是不会，而是没有固定的起手式：一上来就想最优解，想不到就卡死。正确的顺序是先看输出定方向，写出暴力，找出暴力哪里浪费，再换工具。下面每一步都配了同一道题（高频路线 Top K）的示范。"),
      h("div", { class: "stats" },
        h("div", { class: "stat" }, h("b", null, n), h("span", null, "道题有思路阶梯")),
        h("div", { class: "stat" }, h("b", null, done), h("span", null, "已走完")),
        h("div", { class: "stat" }, h("b", null, THINK.kit.length), h("span", null, "个盲写基本功")))),
    thTabs("think"),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "五步起手式"), h("span", { class: "small faint" }, "每道题都这样过一遍，直到变成习惯")),
      h("ol", { class: "th-five" }, TH_FIVE.map(([t, d, ex], i) => h("li", null,
        h("span", { class: "th-n num" }, i + 1),
        h("div", { class: "stack", style: "gap:4px" }, h("b", null, t), h("p", { class: "muted", style: "margin:0" }, d), h("p", { class: "th-ex small" }, h("span", { class: "faint" }, "例　"), ex))))),
      h("div", { class: "row" }, h("a", { class: "btn primary", href: "#think-top-k-routes" }, "用这道题走一遍阶梯 →"), h("a", { class: "btn", href: "#think-list" }, "全部思路阶梯"))),
    h("div", { class: "grid-2" },
      h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "第 ② 步：看输出 → 方法族")), thTable(["题目问的是", "输出类型", "先想到"], TH_OUTPUT, 2)),
      h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, "选数据结构：我要…… → 用……")), thTable(["我要", "用", "Python"], TH_DS, 1))),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "第 ④ 步：暴力的浪费 → 换什么工具"), h("span", { class: "small faint" }, "这是从暴力走到最优解的那座桥")),
      thTable(["暴力里你会看到", "换成", "怎么写"], TH_WASTE, 1)),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "面试时卡住了怎么办"), h("span", { class: "small faint" }, "沉默是最贵的。面试官要看的是思考过程")),
      h("div", { class: "th-stuck" }, TH_STUCK.map(([t, a, say]) => h("div", { class: "th-stuck-row" }, h("span", { class: "tag num" }, t), h("b", null, a), h("p", { class: "small" }, say))))),
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "还要配合")),
      h("div", { class: "rules" },
        rule("看输入特征", "有序、连续子数组、区间、树、网格、依赖关系……「题型」页有一张输入特征表和数据规模反推复杂度表。"),
        rule("识题训练", "只看题面判断题型，专治“换个说法就不认识”。"),
        rule("盲写基本功", "Counter、heapq、多关键字排序、deque、bisect……思路有了却写不出来，多半卡在这些写法上。")),
      h("div", { class: "row" }, h("a", { class: "btn", href: "#learn" }, "输入特征表"), h("a", { class: "btn", href: "#quiz" }, "识题训练"), h("a", { class: "btn", href: "#think-kit" }, "盲写基本功"))));
}

// ---------- 阶梯列表 ----------
function thStatus(pid) {
  const t = TH.get(pid), pr = prog(pid);
  return h("span", { class: "row th-st", style: "gap:6px" },
    h("span", { class: "tag" + (t && t.steps === 6 ? " on" : ""), title: "思路阶梯：答对几步" }, t && t.steps === 6 ? `阶梯 ${t.right}/6` : "阶梯"),
    h("span", { class: "tag" + (t && t.cloze ? " on" : "") }, "填空"),
    h("span", { class: "tag" + (pr && pr.passed ? " on" : "") }, "手写"));
}
function thRow(p) {
  return h("a", { class: "prow th-row", href: "#think-" + p.id }, h("span", { class: "t" }, p.title, p.lc ? h("small", null, "#" + p.lc) : h("small", null, "面试题")), h("span", { class: "lv " + p.level }, LEVEL[p.level]), thStatus(p.id));
}
function viewThinkList() {
  const has = S.all.filter(p => THINK.ladders[p.id]);
  const rec = TH_REC.map(id => has.find(p => p.id === id)).filter(Boolean);
  const nextRec = rec.find(p => !(TH.get(p.id) && TH.get(p.id).steps === 6));
  return thPage("think-list", "思路阶梯", "每道题拆成 6 个小问题，一步步推出思路",
    "① 它要什么 → ② 题眼在哪 → ③ 暴力怎么写 → ④ 暴力浪费在哪 → ⑤ 换成什么 → ⑥ 不变量。答完看思路链和 30 秒口述，再做骨架填空（真跑测试），最后从空白完整手写。",
    h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "推荐顺序"), nextRec ? h("a", { class: "btn sm primary", href: "#think-" + nextRec.id }, "下一题：" + nextRec.title) : h("span", { class: "small faint" }, "推荐题都走完了")),
      h("p", { class: "small muted" }, "前三道是面试里真实卡住过的题，然后是各题型最基础的一道。一天 2–3 道，走完阶梯当天就去完整手写。"),
      h("div", { class: "plist" }, rec.map(thRow))),
    PATTERNS.map(pt => {
      const list = has.filter(p => p.pattern === pt.key);
      if (!list.length) return "";
      return h("section", { class: "panel" }, h("div", { class: "panel-h" }, h("h2", null, pt.name), h("a", { class: "small", href: "#t-" + pt.key }, "题型教程 →")), h("div", { class: "plist" }, list.map(thRow)));
    }));
}

// ---------- 单题阶梯 ----------
function thShuffle(n, seed) {
  const idx = [...Array(n).keys()];
  let s = 0;
  for (const ch of seed) s = (s * 31 + ch.charCodeAt(0)) >>> 0;
  for (let i = n - 1; i > 0; i--) { s = (s * 1103515245 + 12345) >>> 0; const j = s % (i + 1); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  return idx;
}
function viewLadder(pid) {
  const L = THINK.ladders[pid], p = S.all.find(x => x.id === pid);
  if (!p) return h("div", { class: "page" }, h("p", null, "没找到这道题。"));
  const run = TH_RUNS[pid] = TH_RUNS[pid] || {};
  const stepsBox = h("div", { class: "stack", style: "gap:14px" });
  const after = h("div", { class: "stack", style: "gap:16px" });
  const desc = h("div", { class: "md" }); renderMd(desc, p.desc);
  const ctx = { attempt: "" };
  Buddy.provide({
    where: () => `思路阶梯 › ${p.title}`,
    context: () => TEACHER + `\n\n学习者在用“思路阶梯”练习从题面推出思路（它要什么 → 题眼 → 暴力 → 浪费 → 换工具 → 不变量），他的痛点是拿到题没思路。引导为主：先问他怎么想，再给提示，除非他明确要求，不要直接给完整代码。\n\n【题目】${p.title}\n${p.desc}\n\n【阶梯参考】\n` +
      L.steps.map(s => `${TH_STEP[s.k]}：${s.options[s.answer]}（${s.why}）`).join("\n") + `\n口述：${L.say}\n易错：${L.trap}` +
      (Object.keys(run).length ? "\n\n【学习者的选择】\n" + L.steps.filter(s => s.k in run).map(s => `${TH_STEP[s.k]}：选了「${s.options[run[s.k]]}」${run[s.k] === s.answer ? "（对）" : "（错）"}`).join("\n") : "") +
      (ctx.attempt ? "\n\n【学习者的填空代码】\n" + clip(ctx.attempt, 3000) : ""),
    actions: [
      { label: "我卡在这一步", run: c => c.send("我在这道题的思路阶梯上卡住了。根据我已经做的选择，给我一个提示（问我一个引导性的问题），先别给答案。", { label: "我卡在这一步" }) },
      { label: "为什么我想错了", run: c => c.send("看我在阶梯里选错的那几步：分别说说我当时可能是怎么想的、为什么这个思路走不通、正确的想法是从题面哪句话推出来的。", { label: "为什么我想错了" }) },
      { label: "同套路换一道题", run: c => c.send("出一道和这道题思路套路相同、但题面换了业务背景的新题。只给题面和一个例子，让我按“它要什么 → 题眼 → 暴力 → 浪费 → 换工具 → 不变量”六步先说思路，我说完你再点评。", { label: "同套路换一道题" }) },
      { label: "讲讲另一种解法", run: c => c.send("这道题除了阶梯里的方法，还有别的解法吗？对比一下复杂度、代码难度和面试里该先说哪个。", { label: "另一种解法" }) },
    ],
  });
  onLeave(() => Buddy.provide(null));

  function drawSteps() {
    stepsBox.textContent = "";
    let open = true;
    L.steps.forEach((s, si) => {
      if (!open) return;
      const chosen = run[s.k];
      const answered = chosen != null;
      const order = thShuffle(s.options.length, pid + s.k);
      const opts = h("div", { class: "th-opts" }, order.map(oi => {
        const b = h("button", { type: "button", class: "quiz-opt" + (answered ? (oi === s.answer ? " right" : oi === chosen ? " wrong" : "") : ""), disabled: answered }, s.options[oi]);
        b.addEventListener("click", () => { run[s.k] = oi; drawSteps(); if (Object.keys(run).length === 6) finish(); });
        return b;
      }));
      stepsBox.append(h("section", { class: "panel th-step" + (answered ? " done" : " cur") },
        h("div", { class: "row", style: "gap:10px" }, h("span", { class: "th-n num" }, si + 1), h("span", { class: "eyebrow" }, TH_STEP[s.k]), answered ? h("span", { class: "small " + (chosen === s.answer ? "ok" : "bad") }, chosen === s.answer ? "想对了" : "想偏了") : ""),
        h("div", { class: "bg-q" }, s.q),
        opts,
        answered ? h("div", { class: "callout" + (chosen === s.answer ? " blue" : "") }, h("b", null, chosen === s.answer ? "为什么　" : `应该是「${s.options[s.answer]}」　`), s.why) : h("p", { class: "small faint" }, "先自己想 20 秒再点。没把握也选一个，错了才记得住。")));
      if (!answered) open = false;
    });
    drawAfter();
  }
  function finish() {
    const right = L.steps.filter(s => run[s.k] === s.answer).length;
    const prev = TH.get(pid);
    TH.set(pid, { steps: 6, right: prev && prev.steps === 6 ? Math.max(prev.right, right) : right, last: right });
  }
  function drawAfter() {
    after.textContent = "";
    if (Object.keys(run).length < 6) return;
    const right = L.steps.filter(s => run[s.k] === s.answer).length;
    const sayBtn = h("button", { class: "btn sm ghost", type: "button" }, icon("speak"), " 朗读");
    sayBtn.addEventListener("click", () => TTS.speak(L.say));
    const brute = h("pre", { class: "code th-code" }); highlightInto(brute, L.brute);
    after.append(
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", null, "把思路串起来"), h("span", { class: "small faint" }, `6 步答对 ${right} 步`)),
        h("ol", { class: "th-chain" }, L.steps.map(s => h("li", null, h("span", { class: "eyebrow" }, TH_STEP[s.k]), h("span", null, s.options[s.answer])))),
        h("div", { class: "bg-short" }, h("div", { class: "spread" }, h("div", { class: "bg-label" }, "30 秒口述 · 面试时这样说"), sayBtn), h("p", null, L.say)),
        h("div", { class: "callout" }, h("b", null, "最容易错　"), L.trap),
        h("details", { class: "qa" }, h("summary", null, "暴力保底版（卡住时先把它写出来）"), brute),
        h("div", { class: "row" }, h("button", { class: "btn sm ghost", type: "button", onclick: () => { TH_RUNS[pid] = {}; render(); } }, "重走一遍阶梯"))),
      clozePanel());
  }
  function clozePanel() {
    const parts = L.cloze.code.split(/⟦(\d)⟧/);
    const inputs = {};
    const pre = h("pre", { class: "code th-cloze" });
    const saved = LS.get("tiyan:think:cz:" + pid, {});
    parts.forEach((seg, i) => {
      if (i % 2 === 0) { const sp = h("span"); highlightInto(sp, seg); pre.append(sp); return; }
      const n = +seg, b = L.cloze.blanks[n - 1];
      const inp = h("input", { class: "th-blank", spellcheck: false, autocomplete: "off", "aria-label": `第 ${n} 空`, placeholder: `⟦${n}⟧`, style: `width:${Math.max(b.a.length, 6) + 2}ch` });
      inp.value = saved[n] || "";
      inp.addEventListener("input", () => { saved[n] = inp.value; LS.set("tiyan:think:cz:" + pid, saved); inp.classList.remove("bad", "good"); });
      inp.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); check(); } });
      inputs[n] = inp;
      pre.append(inp);
    });
    const out = h("div", { class: "stack", style: "gap:8px" });
    const hints = h("ol", { class: "th-hints small", hidden: true }, L.cloze.blanks.map((b, i) => h("li", null, `⟦${i + 1}⟧ `, b.hint)));
    const assemble = () => parts.map((seg, i) => i % 2 === 0 ? seg : (inputs[+seg].value.trim() || "None")).join("");
    async function check() {
      const empty = Object.values(inputs).filter(x => !x.value.trim());
      if (empty.length) { empty[0].focus(); toast(`还有 ${empty.length} 个空没填`); return; }
      const code = assemble();
      ctx.attempt = code;
      out.textContent = ""; out.append(h("div", { class: "thinking" }, S.py === "ready" ? "运行测试……" : "等待 Python 运行环境……"));
      try {
        const r = await Py.json("run_tests", [code, specOf(p)], 10000);
        out.textContent = "";
        if (r.compile_error) { out.append(h("div", { class: "callout" }, h("b", null, "代码跑不起来　"), h("pre", { class: "small", style: "white-space:pre-wrap;margin:6px 0 0" }, r.compile_error))); return; }
        if (r.ok) {
          Object.values(inputs).forEach(x => x.classList.add("good"));
          TH.set(pid, { cloze: true });
          out.append(h("div", { class: "callout blue" }, h("b", null, `全部 ${r.total} 个用例通过。`), "关键几行你已经能写对了。现在关掉这页，从空白把整道题写一遍——这一步才是真正的掌握。"),
            h("div", { class: "row" }, h("a", { class: "btn primary", href: "#p-" + pid, onclick: () => { S.redo = pid; } }, "从空白完整手写 →")));
        } else {
          const c = r.cases.find(x => !x.pass);
          out.append(h("div", { class: "callout" }, h("b", null, `通过 ${r.passed} / ${r.total}。`), "第一个没过的用例：",
            h("pre", { class: "small", style: "white-space:pre-wrap;margin:6px 0 0" }, `输入：${c.args}\n期望：${c.expected}\n${c.error ? "报错：" + c.error : "得到：" + c.got}`)),
            h("p", { class: "small muted" }, "对照提示检查每个空；也可以问右下角的小眼（它能看到你的填空）。"));
          hints.hidden = false;
        }
      } catch (e) { out.textContent = (e && e.message) || String(e); }
    }
    return h("section", { class: "panel" },
      h("div", { class: "panel-h" }, h("h2", null, "骨架填空"), h("span", { class: "small faint" }, `${L.cloze.blanks.length} 个空，填的是体现思路的关键行；判题会真跑全部用例`)),
      pre,
      h("div", { class: "row" },
        h("button", { class: "btn primary", type: "button", onclick: check }, "运行测试"),
        h("button", { class: "btn", type: "button", onclick: () => { hints.hidden = !hints.hidden; } }, "提示"),
        h("button", { class: "btn ghost", type: "button", onclick: () => { L.cloze.blanks.forEach((b, i) => { inputs[i + 1].value = b.a; saved[i + 1] = b.a; }); LS.set("tiyan:think:cz:" + pid, saved); toast("已填入参考答案：看懂后清空再自己填一遍"); } }, "看答案"),
        h("button", { class: "btn ghost", type: "button", onclick: () => { Object.values(inputs).forEach(x => { x.value = ""; x.classList.remove("good", "bad"); }); LS.set("tiyan:think:cz:" + pid, {}); } }, "清空")),
      hints, out);
  }
  drawSteps();
  const ex = p.examples && p.examples[0];
  return h("div", { class: "page", style: "max-width:900px" },
    h("section", { class: "hero", style: "gap:8px" },
      h("div", { class: "eyebrow" }, h("a", { href: "#think-list" }, "思路阶梯"), ` · ${pname(p)} · ${LEVEL[p.level]}`),
      h("h1", null, p.title),
      h("p", { class: "lede" }, L.read)),
    h("details", { class: "panel th-prob", open: true }, h("summary", null, h("b", null, "题面")), desc,
      ex ? h("div", { class: "example" }, h("b", null, "示例　"), `输入：${ex.input}\n输出：${ex.output}${ex.note ? "\n说明：" + ex.note : ""}`) : "",
      p.constraints && p.constraints.length ? h("ul", { class: "small muted" }, p.constraints.map(c => h("li", null, c))) : ""),
    stepsBox, after,
    h("div", { class: "row" }, h("a", { class: "btn ghost", href: "#think-list" }, "← 全部阶梯"), h("a", { class: "btn ghost", href: "#t-" + p.pattern }, `「${pname(p)}」题型教程`), h("a", { class: "btn ghost", href: "#p-" + pid }, "直接去写代码")));
}

// ---------- 盲写基本功 ----------
function viewThinkKit() {
  const rec = LS.get("tiyan:think:kit", {});
  const list = h("div", { class: "stack", style: "gap:16px" });
  for (const k of THINK.kit) list.append(kitBlock(k, rec));
  const passed = THINK.kit.filter(k => rec[k.id] && rec[k.id].ok).length;
  return thPage("think-kit", "盲写基本功", "思路有了却写不出来？多半卡在这几个写法上",
    `${THINK.kit.length} 个刷题最常用的 Python 写法：计数、Top K 排序键、heapq、规范化 key、分组、BFS、栈、双指针、滑动窗口、前缀和、bisect、二维数组、@cache、链表、字符串。不看资料写出来、测试全过才算会。已通过 ${passed} / ${THINK.kit.length}。`,
    list);
}
function kitBlock(k, rec) {
  const ed = h("div", { class: "kit-ed" });
  const out = h("div", { class: "stack", style: "gap:6px" });
  const key = "tiyan:think:kitcode:" + k.id;
  let cm = null;
  const box = h("section", { class: "panel kit" + (rec[k.id] && rec[k.id].ok ? " ok" : "") });
  const mount = () => {
    if (cm) return;
    cm = CodeMirror(ed, { value: LS.get(key, k.starter), mode: "python", theme: "tiyan", lineNumbers: true, indentUnit: 4, tabSize: 4, viewportMargin: Infinity, matchBrackets: true, autoCloseBrackets: true,
      extraKeys: { Tab: c => c.replaceSelection("    ", "end"), "Cmd-Enter": () => run(), "Ctrl-Enter": () => run() } });
    cm.on("change", () => LS.set(key, cm.getValue()));
    setTimeout(() => cm.refresh(), 0);
  };
  async function run() {
    mount();
    out.textContent = ""; out.append(h("div", { class: "thinking" }, S.py === "ready" ? "运行测试……" : "等待 Python 运行环境……"));
    try {
      const r = await Py.json("run_lab", [cm.getValue(), k.tests], 10000);
      out.textContent = "";
      if (r.compile_error) { out.append(h("pre", { class: "small callout", style: "white-space:pre-wrap" }, r.compile_error)); return; }
      const ok = r.passed === r.total;
      const all = LS.get("tiyan:think:kit", {});
      all[k.id] = { ok: ok || !!(all[k.id] && all[k.id].ok), at: Date.now() };
      LS.set("tiyan:think:kit", all);
      box.classList.toggle("ok", all[k.id].ok);
      out.append(h("div", { class: ok ? "callout blue" : "callout" }, h("b", null, ok ? `全部 ${r.total} 个测试通过` : `通过 ${r.passed} / ${r.total}`)),
        ...r.cases.filter(c => !c.pass).map(c => h("pre", { class: "small", style: "white-space:pre-wrap;margin:0" }, `${c.name}：${c.error}`)),
        r.stdout ? h("pre", { class: "small faint", style: "white-space:pre-wrap;margin:0" }, r.stdout) : "");
    } catch (e) { out.textContent = (e && e.message) || String(e); }
  }
  const ref = h("pre", { class: "code th-code" }); highlightInto(ref, k.solution);
  const tests = h("pre", { class: "code th-code" }); highlightInto(tests, k.tests);
  box.append(
    h("div", { class: "panel-h" }, h("h2", null, k.title), rec[k.id] && rec[k.id].ok ? h("span", { class: "pill passed" }, "已通过") : ""),
    h("p", { class: "small muted", style: "margin:0" }, k.use),
    h("div", { class: "md" }, (() => { const d = h("div"); renderMd(d, k.prompt); return d; })()),
    ed,
    h("div", { class: "row" }, h("button", { class: "btn primary sm", type: "button", onclick: run }, "运行测试 ", h("span", { class: "kbd" }, "⌘↵")),
      h("button", { class: "btn ghost sm", type: "button", onclick: () => { mount(); cm.setValue(k.starter); } }, "重置")),
    out,
    h("details", { class: "qa" }, h("summary", null, "关键写法（写不出来再看）"), h("p", { class: "small" }, k.tip)),
    h("details", { class: "qa" }, h("summary", null, "参考写法"), ref),
    h("details", { class: "qa" }, h("summary", null, "测试代码"), tests));
  // 编辑器在进入视口时再创建，十几个 CodeMirror 同时初始化会卡
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { mount(); io.disconnect(); } }, { rootMargin: "200px" });
    io.observe(ed);
    onLeave(() => io.disconnect());
  } else setTimeout(mount, 0);
  return box;
}
