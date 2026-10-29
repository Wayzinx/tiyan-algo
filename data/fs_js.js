// 前端手写题的测试工具：浏览器 Worker 和本地 node 校验共用同一份
// 用法：test("名字", () => { assertEqual(实际, 期望) })；支持 async；sleep(ms) 等定时器
const __tests = [];
function test(name, fn) { __tests.push({ name, fn }); }
function __fmt(v) {
  try {
    if (typeof v === "function") return "[函数]";
    if (v instanceof Map) return "Map(" + JSON.stringify([...v]) + ")";
    if (v instanceof Set) return "Set(" + JSON.stringify([...v]) + ")";
    const s = JSON.stringify(v, (k, x) => x === undefined ? "__undefined__" : typeof x === "bigint" ? String(x) + "n" : x);
    return s === undefined ? String(v) : s.replace(/"__undefined__"/g, "undefined").slice(0, 300);
  } catch (e) { return String(v); }
}
function __eq(a, b, seen) {
  if (Object.is(a, b)) return true;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object") return false;
  seen = seen || new Map();
  if (seen.get(a) === b) return true;
  seen.set(a, b);
  if (Object.getPrototypeOf(a) !== Object.getPrototypeOf(b)) return false;
  if (a instanceof Date) return a.getTime() === b.getTime();
  if (a instanceof RegExp) return String(a) === String(b);
  if (a instanceof Map) { if (a.size !== b.size) return false; for (const [k, v] of a) if (!b.has(k) || !__eq(v, b.get(k), seen)) return false; return true; }
  if (a instanceof Set) { if (a.size !== b.size) return false; for (const v of a) if (!b.has(v)) return false; return true; }
  const ka = Reflect.ownKeys(a), kb = Reflect.ownKeys(b);
  if (ka.length !== kb.length) return false;
  for (const k of ka) if (!kb.includes(k) || !__eq(a[k], b[k], seen)) return false;
  return true;
}
function assert(cond, msg) { if (!cond) throw new Error(msg || "断言失败"); }
function assertEqual(actual, expected, msg) { if (!__eq(actual, expected)) throw new Error((msg ? msg + "：" : "") + "期望 " + __fmt(expected) + "，实际 " + __fmt(actual)); }
async function assertRejects(fn, msg) { let ok = false; try { await (typeof fn === "function" ? fn() : fn); } catch (e) { ok = true; } if (!ok) throw new Error(msg || "期望抛出错误 / reject，但没有"); }
function assertThrows(fn, msg) { let ok = false; try { fn(); } catch (e) { ok = true; } if (!ok) throw new Error(msg || "期望抛出错误，但没有"); }
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function __run(timeoutMs) {
  const out = [];
  for (const t of __tests) {
    const t0 = Date.now();
    let timer;
    try {
      await Promise.race([Promise.resolve().then(t.fn), new Promise((_, rej) => { timer = setTimeout(() => rej(new Error("超时（超过 " + timeoutMs + "ms 没结束）")), timeoutMs); })]);
      out.push({ name: t.name, pass: true, ms: Date.now() - t0 });
    } catch (e) { out.push({ name: t.name, pass: false, error: String((e && e.message) || e) }); }
    clearTimeout(timer);
  }
  return out;
}
