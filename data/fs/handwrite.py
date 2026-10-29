HANDWRITE = [
    dict(id="h1", order=1, title="防抖 debounce", level="入门", desc="题目要求：实现 debounce(fn, wait, immediate=false)，用于搜索框联想、保存草稿等高频事件。连续触发时只允许最后一次在 wait 毫秒后执行；immediate 为 true 时第一下立即执行，后续在冷却期内被合并。需要透传 this 与参数，返回最后一次执行结果，并提供 cancel 方法清理定时器，避免组件卸载后仍触发副作用。",
         starter="""function debounce(fn, wait, immediate) {
  // TODO
}""",
         tests="""test("连续调用只执行最后一次", async () => {
  const calls = [];
  const fn = debounce((x) => calls.push(x), 20);
  fn(1); fn(2); fn(3);
  await sleep(70);
  assertEqual(calls, [3]);
});

test("间隔超过 wait 会分成多次执行", async () => {
  let count = 0;
  const fn = debounce(() => count++, 15);
  fn();
  await sleep(45);
  fn();
  await sleep(45);
  assertEqual(count, 2);
});

test("this 与参数会透传给原函数", async () => {
  const ctx = { base: 10 };
  let seen;
  const fn = debounce(function (a, b) { seen = [this.base, a, b]; }, 15);
  fn.call(ctx, 2, 3);
  await sleep(50);
  assertEqual(seen, [10, 2, 3]);
});

test("immediate 模式首调用立即执行，冷却期内不重复", async () => {
  const calls = [];
  const fn = debounce((x) => calls.push(x), 25, true);
  fn("a"); fn("b");
  assertEqual(calls, ["a"]);
  await sleep(80);
  fn("c");
  assertEqual(calls, ["a", "c"]);
});

test("cancel 会取消等待中的调用并允许 immediate 重新开始", async () => {
  const calls = [];
  const fn = debounce((x) => calls.push(x), 25, true);
  fn(1);
  fn(2);
  fn.cancel();
  await sleep(60);
  fn(3);
  assertEqual(calls, [1, 3]);
});""",
         solution="""function debounce(fn, wait, immediate = false) {
  let timer = null;
  let lastResult;
  const debounced = function (...args) {
    const context = this;
    const callNow = immediate && timer === null;
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      if (!immediate) lastResult = fn.apply(context, args);
    }, wait);
    if (callNow) lastResult = fn.apply(context, args);
    return lastResult;
  };
  debounced.cancel = function () {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };
  return debounced;
}""",
         points=["理解高频事件合并的失败模式：请求风暴、重复写入和卸载后副作用", "会管理定时器生命周期，包含重置、执行、取消三种状态", "能正确处理 this、参数与返回值，而不是只做空壳延迟"], hints=["先用一个 timer 记录冷却窗口，调用时清旧定时器再设置新定时器", "immediate 的关键是 timer 为空时才同步执行，cancel 后要恢复为空状态"]),

    dict(id="h2", order=2, title="节流 throttle", level="中等", desc="题目要求：实现 throttle(fn, wait, options)，用于滚动加载、库存价格刷新、拖拽位置上报等持续触发场景。函数在一个 wait 窗口内最多执行一次，并支持 leading 与 trailing 开关：leading 控制窗口开始是否立即执行，trailing 控制窗口结束是否补一次最后参数。需要透传 this/参数，提供 cancel，避免尾调用使用过期状态。",
         starter="""function throttle(fn, wait, options) {
  // TODO
}""",
         tests="""test("默认 leading 与 trailing 都开启", async () => {
  const calls = [];
  const fn = throttle((x) => calls.push(x), 30);
  fn(1); fn(2); fn(3);
  assertEqual(calls, [1]);
  await sleep(90);
  assertEqual(calls, [1, 3]);
});

test("leading false 时首个窗口不立即执行", async () => {
  const calls = [];
  const fn = throttle((x) => calls.push(x), 25, { leading: false });
  fn("a"); fn("b");
  assertEqual(calls, []);
  await sleep(80);
  assertEqual(calls, ["b"]);
});

test("trailing false 时窗口末尾不补调用", async () => {
  const calls = [];
  const fn = throttle((x) => calls.push(x), 25, { trailing: false });
  fn(1); fn(2); fn(3);
  await sleep(80);
  assertEqual(calls, [1]);
});

test("间隔超过 wait 会再次立即执行", async () => {
  const calls = [];
  const fn = throttle((x) => calls.push(x), 20);
  fn(1);
  await sleep(55);
  fn(2);
  assertEqual(calls, [1, 2]);
});

test("this 与最后一次参数会传给 trailing", async () => {
  const ctx = { tag: "ctx" };
  let seen;
  const fn = throttle(function (x, y) { seen = [this.tag, x, y]; }, 20);
  fn.call(ctx, 1, 1);
  fn.call(ctx, 2, 3);
  await sleep(70);
  assertEqual(seen, ["ctx", 2, 3]);
});

test("cancel 会清理待执行的 trailing", async () => {
  const calls = [];
  const fn = throttle((x) => calls.push(x), 30);
  fn(1); fn(2);
  fn.cancel();
  await sleep(90);
  assertEqual(calls, [1]);
});""",
         solution="""function throttle(fn, wait, options = {}) {
  const leading = options.leading !== false;
  const trailing = options.trailing !== false;
  let timer = null;
  let lastArgs = null;
  let lastThis = null;
  let lastInvokeTime = 0;
  let lastResult;

  function invoke(time) {
    lastInvokeTime = time;
    const args = lastArgs;
    const context = lastThis;
    lastArgs = lastThis = null;
    lastResult = fn.apply(context, args);
    return lastResult;
  }

  function startTimer(ms) {
    timer = setTimeout(() => {
      timer = null;
      if (trailing && lastArgs) invoke(Date.now());
    }, ms);
  }

  const throttled = function (...args) {
    const now = Date.now();
    if (!lastInvokeTime && !leading) lastInvokeTime = now;
    const remaining = wait - (now - lastInvokeTime);
    lastArgs = args;
    lastThis = this;
    if (remaining <= 0 || remaining > wait) {
      if (timer) { clearTimeout(timer); timer = null; }
      return invoke(now);
    }
    if (!timer && trailing) startTimer(remaining);
    return lastResult;
  };

  throttled.cancel = function () {
    if (timer) clearTimeout(timer);
    timer = null;
    lastArgs = lastThis = null;
    lastInvokeTime = 0;
  };
  return throttled;
}""",
         points=["能说明节流解决的是频率上限，而不是只保留最后一次", "掌握 leading/trailing 对用户反馈与数据一致性的取舍", "实现中要保存最后一次上下文和参数，并清理尾调用定时器"], hints=["用 lastInvokeTime 判断当前调用是否已经跨过窗口", "trailing 需要记录最后参数，窗口结束后再补一次"]),

    dict(id="h3", order=3, title="深拷贝 deepClone", level="困难", desc="题目要求：实现 deepClone(value)，用于前端状态快照、表单草稿回滚、接口数据隔离等场景。需要支持普通对象、数组、Date、RegExp、Map、Set，并处理循环引用；对象属性要尽量保留原型和 symbol key。说明浅拷贝在嵌套库存明细里会互相污染，深拷贝的代价是额外内存与遍历成本。",
         starter="""function deepClone(value) {
  // TODO
}""",
         tests="""test("基础对象和数组会递归复制", () => {
  const source = { a: 1, b: { c: 2 }, list: [1, { d: 3 }] };
  const copy = deepClone(source);
  copy.b.c = 20;
  copy.list[1].d = 30;
  assertEqual(source.b.c, 2);
  assertEqual(source.list[1].d, 3);
});

test("循环引用不会爆栈且引用关系保持", () => {
  const source = { name: "node" };
  source.self = source;
  const copy = deepClone(source);
  assert(copy !== source);
  assert(copy.self === copy);
});

test("Date 与 RegExp 会复制值而不是共享引用", () => {
  const source = { d: new Date("2024-01-02T00:00:00Z"), r: /sku-\d+/gi };
  const copy = deepClone(source);
  assert(copy.d !== source.d);
  assertEqual(copy.d.getTime(), source.d.getTime());
  assert(copy.r !== source.r);
  assertEqual(String(copy.r), String(source.r));
});

test("Map 和 Set 内部值也会深拷贝", () => {
  const inner = { qty: 1 };
  const source = new Map([["a", inner], ["s", new Set([inner])]]);
  const copy = deepClone(source);
  copy.get("a").qty = 9;
  const copiedSetValue = [...copy.get("s")][0];
  copiedSetValue.qty = 8;
  assertEqual(inner.qty, 1);
});

test("symbol key 与原型方法可保留", () => {
  const sym = Symbol("id");
  class Item { total() { return this.count * 2; } }
  const source = new Item();
  source.count = 3;
  source[sym] = { code: "x" };
  const copy = deepClone(source);
  copy[sym].code = "y";
  assert(copy instanceof Item);
  assertEqual(copy.total(), 6);
  assertEqual(source[sym].code, "x");
});""",
         solution="""function deepClone(value, seen = new WeakMap()) {
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return seen.get(value);

  if (value instanceof Date) return new Date(value.getTime());
  if (value instanceof RegExp) {
    const clonedRegExp = new RegExp(value.source, value.flags);
    clonedRegExp.lastIndex = value.lastIndex;
    return clonedRegExp;
  }

  if (value instanceof Map) {
    const clonedMap = new Map();
    seen.set(value, clonedMap);
    value.forEach((mapValue, mapKey) => {
      clonedMap.set(deepClone(mapKey, seen), deepClone(mapValue, seen));
    });
    return clonedMap;
  }

  if (value instanceof Set) {
    const clonedSet = new Set();
    seen.set(value, clonedSet);
    value.forEach((setValue) => clonedSet.add(deepClone(setValue, seen)));
    return clonedSet;
  }

  const cloned = Array.isArray(value) ? [] : Object.create(Object.getPrototypeOf(value));
  seen.set(value, cloned);
  Reflect.ownKeys(value).forEach((key) => {
    cloned[key] = deepClone(value[key], seen);
  });
  return cloned;
}""",
         points=["知道循环引用需要 WeakMap 记录原对象到新对象的映射", "能区分普通对象和内置对象的复制机制", "理解深拷贝会增加内存和 CPU，不适合无限制复制大状态"], hints=["先处理原始类型和 null，再处理已经见过的对象", "Map/Set 要先放入 seen，再递归复制内部键和值"]),

    dict(id="h4", order=4, title="实现 Promise.all 与 Promise.allSettled", level="中等", desc="题目要求：实现 promiseAll(iterable) 与 promiseAllSettled(iterable)，语义对齐原生 Promise 的核心行为。all 需要按输入顺序返回结果，任意一个失败立即 reject；allSettled 需要等待全部完成，并用 fulfilled/rejected 状态描述每个结果。面试会追问空数组、普通值、thenable、异步完成顺序和错误传播。",
         starter="""function promiseAll(iterable) {
  // TODO
}
function promiseAllSettled(iterable) {
  // TODO
}""",
         tests="""test("promiseAll 按输入顺序返回而不是完成顺序", async () => {
  const result = await promiseAll([sleep(30).then(() => 1), 2, sleep(10).then(() => 3)]);
  assertEqual(result, [1, 2, 3]);
});

test("promiseAll 遇到拒绝会 reject", async () => {
  await assertRejects(() => promiseAll([Promise.resolve(1), Promise.reject(new Error("bad"))]));
});

test("promiseAll 空数组立即得到空数组", async () => {
  const result = await promiseAll([]);
  assertEqual(result, []);
});

test("promiseAllSettled 同时记录成功和失败", async () => {
  const err = new Error("库存不足");
  const result = await promiseAllSettled([1, Promise.reject(err)]);
  assertEqual(result[0], { status: "fulfilled", value: 1 });
  assertEqual(result[1].status, "rejected");
  assert(result[1].reason === err);
});

test("promiseAllSettled 会等待所有任务完成", async () => {
  const order = [];
  const result = await promiseAllSettled([
    sleep(25).then(() => { order.push("slow"); return "s"; }),
    sleep(5).then(() => { order.push("fast"); throw new Error("x"); })
  ]);
  assertEqual(order, ["fast", "slow"]);
  assertEqual(result[0].value, "s");
  assertEqual(result[1].status, "rejected");
});

test("thenable 会通过 Promise.resolve 展开", async () => {
  const thenable = { then(resolve) { setTimeout(() => resolve(7), 5); } };
  const result = await promiseAll([thenable]);
  assertEqual(result, [7]);
});""",
         solution="""function promiseAll(iterable) {
  return new Promise((resolve, reject) => {
    const items = Array.from(iterable);
    if (items.length === 0) return resolve([]);
    const results = new Array(items.length);
    let finished = 0;
    items.forEach((item, index) => {
      Promise.resolve(item).then((value) => {
        results[index] = value;
        finished += 1;
        if (finished === items.length) resolve(results);
      }, reject);
    });
  });
}

function promiseAllSettled(iterable) {
  return new Promise((resolve) => {
    const items = Array.from(iterable);
    if (items.length === 0) return resolve([]);
    const results = new Array(items.length);
    let finished = 0;
    items.forEach((item, index) => {
      Promise.resolve(item).then(
        (value) => { results[index] = { status: "fulfilled", value }; },
        (reason) => { results[index] = { status: "rejected", reason }; }
      ).then(() => {
        finished += 1;
        if (finished === items.length) resolve(results);
      });
    });
  });
}""",
         points=["能用 Promise.resolve 统一普通值、Promise 与 thenable", "理解 all 的失败快返和 allSettled 的全量收敛差异", "结果数组必须按输入下标写入，不能按完成时间 push"], hints=["先把 iterable 转数组，这样能知道总数和下标", "每个任务完成后计数，计数等于总数再 resolve"]),

    dict(id="h5", order=5, title="带并发上限的异步任务池", level="困难", desc="题目要求：实现 asyncPool(limit, tasks)，tasks 是一组返回 Promise 的函数，最多只能同时运行 limit 个，最终结果顺序必须与输入顺序一致。该题对应批量查订单、批量拉物流轨迹、批量生成报表等场景：不限制并发会压垮后端，串行又浪费吞吐；失败时要 reject，并避免继续启动新的无意义任务。",
         starter="""function asyncPool(limit, tasks) {
  // TODO
}""",
         tests="""test("并发数不会超过 limit", async () => {
  let running = 0;
  let maxRunning = 0;
  const tasks = Array.from({ length: 6 }, (_, i) => async () => {
    running += 1;
    maxRunning = Math.max(maxRunning, running);
    await sleep(20);
    running -= 1;
    return i;
  });
  const result = await asyncPool(2, tasks);
  assertEqual(result, [0, 1, 2, 3, 4, 5]);
  assert(maxRunning <= 2, "并发数超过限制");
});

test("结果保持输入顺序而不是完成顺序", async () => {
  const tasks = [
    () => sleep(30).then(() => "slow"),
    () => sleep(5).then(() => "fast"),
    () => Promise.resolve("now")
  ];
  const result = await asyncPool(2, tasks);
  assertEqual(result, ["slow", "fast", "now"]);
});

test("limit 大于任务数时可以全部启动", async () => {
  let started = 0;
  const result = await asyncPool(10, [() => { started++; return 1; }, () => { started++; return 2; }]);
  assertEqual(started, 2);
  assertEqual(result, [1, 2]);
});

test("空任务返回空数组", async () => {
  const result = await asyncPool(3, []);
  assertEqual(result, []);
});

test("任一任务失败会 reject", async () => {
  await assertRejects(() => asyncPool(2, [() => Promise.resolve(1), () => Promise.reject(new Error("fail")), () => Promise.resolve(3)]));
});

test("非法 limit 会抛错", async () => {
  await assertRejects(() => asyncPool(0, [() => 1]));
});""",
         solution="""function asyncPool(limit, tasks) {
  return new Promise((resolve, reject) => {
    if (!Number.isInteger(limit) || limit <= 0) return reject(new Error("limit must be a positive integer"));
    const list = Array.from(tasks);
    if (list.length === 0) return resolve([]);
    const results = new Array(list.length);
    let nextIndex = 0;
    let finished = 0;
    let running = 0;
    let rejected = false;

    function launch() {
      if (rejected) return;
      while (running < limit && nextIndex < list.length) {
        const current = nextIndex++;
        running += 1;
        Promise.resolve().then(() => list[current]()).then((value) => {
          results[current] = value;
          running -= 1;
          finished += 1;
          if (finished === list.length) resolve(results);
          else launch();
        }, (error) => {
          rejected = true;
          reject(error);
        });
      }
    }
    launch();
  });
}""",
         points=["会用调度器维持 running、nextIndex、finished 三个状态", "知道结果顺序需要按任务下标写入", "能解释并发上限的代价：吞吐下降但保护依赖服务"], hints=["启动任务时记录 current 下标，完成后再补启动下一个", "失败后设置 rejected 标记，避免继续调度新任务"]),

    dict(id="h6", order=6, title="EventEmitter 事件发布订阅", level="中等", desc="题目要求：实现 EventEmitter，支持 on、off、once、emit，并能把 emit 的多个参数透传给监听器。常见于前端状态同步、微前端消息、购物车数量刷新等场景。需要处理同一事件多个监听器、once 只执行一次、off 能移除普通监听器和 once 包装后的监听器，emit 时复制队列避免监听器修改列表导致漏执行。",
         starter="""class EventEmitter {
  // TODO
}""",
         tests="""test("on 与 emit 支持多个监听器", () => {
  const bus = new EventEmitter();
  const calls = [];
  bus.on("change", (x) => calls.push("a" + x));
  bus.on("change", (x) => calls.push("b" + x));
  bus.emit("change", 1);
  assertEqual(calls, ["a1", "b1"]);
});

test("emit 会透传多个参数并绑定 this 为实例", () => {
  const bus = new EventEmitter();
  let seen;
  bus.on("sum", function (a, b) { seen = [this === bus, a + b]; });
  const returned = bus.emit("sum", 2, 3);
  assertEqual(seen, [true, 5]);
  assertEqual(returned, true);
});

test("off 可以移除指定监听器", () => {
  const bus = new EventEmitter();
  const calls = [];
  function fn(x) { calls.push(x); }
  bus.on("x", fn);
  bus.emit("x", 1);
  bus.off("x", fn);
  bus.emit("x", 2);
  assertEqual(calls, [1]);
});

test("once 只触发一次", () => {
  const bus = new EventEmitter();
  let count = 0;
  bus.once("ready", () => count++);
  bus.emit("ready");
  bus.emit("ready");
  assertEqual(count, 1);
});

test("off 可以在 once 执行前移除原函数", () => {
  const bus = new EventEmitter();
  let count = 0;
  function fn() { count++; }
  bus.once("ready", fn);
  bus.off("ready", fn);
  bus.emit("ready");
  assertEqual(count, 0);
});

test("未知事件 emit 返回 false", () => {
  const bus = new EventEmitter();
  assertEqual(bus.emit("none"), false);
});""",
         solution="""class EventEmitter {
  constructor() {
    this.events = new Map();
  }

  on(name, listener) {
    if (!this.events.has(name)) this.events.set(name, []);
    this.events.get(name).push(listener);
    return this;
  }

  off(name, listener) {
    const listeners = this.events.get(name);
    if (!listeners) return this;
    const filtered = listeners.filter((fn) => fn !== listener && fn.listener !== listener);
    if (filtered.length) this.events.set(name, filtered);
    else this.events.delete(name);
    return this;
  }

  once(name, listener) {
    const wrapper = (...args) => {
      this.off(name, wrapper);
      listener.apply(this, args);
    };
    wrapper.listener = listener;
    return this.on(name, wrapper);
  }

  emit(name, ...args) {
    const listeners = this.events.get(name);
    if (!listeners || listeners.length === 0) return false;
    listeners.slice().forEach((listener) => listener.apply(this, args));
    return true;
  }
}""",
         points=["理解发布订阅把调用方和订阅方解耦，但也会带来泄漏和顺序问题", "once 通常需要包装函数，并保留原函数引用供 off 使用", "emit 期间复制数组，防止监听器增删导致迭代错乱"], hints=["用 Map 保存事件名到监听器数组", "once 的 wrapper 上挂 listener 字段，可让 off(name, 原函数) 生效"]),

    dict(id="h7", order=7, title="柯里化 curry", level="中等", desc="题目要求：实现 curry(fn)，把多参数函数转换成可分批传参的函数，直到收集到 fn.length 个参数后执行。该技巧常用于组合校验器、预置接口参数、生成表格列格式化器。需要支持一次传多个参数、分多次传参、保留 this，并且不要在参数不足时提前调用原函数。",
         starter="""function curry(fn) {
  // TODO
}""",
         tests="""test("支持一个一个传参", () => {
  function add(a, b, c) { return a + b + c; }
  assertEqual(curry(add)(1)(2)(3), 6);
});

test("支持一次传多个参数", () => {
  function join(a, b, c, d) { return [a, b, c, d].join("-"); }
  const curried = curry(join);
  assertEqual(curried("order", "sku")("qty", 3), "order-sku-qty-3");
});

test("参数超过 arity 时会全部传给原函数", () => {
  function collect(a, b) { return Array.from(arguments); }
  assertEqual(curry(collect)(1, 2, 3), [1, 2, 3]);
});

test("this 会透传到最终执行", () => {
  const obj = { base: 5, add(a, b) { return this.base + a + b; } };
  const fn = curry(obj.add);
  assertEqual(fn.call(obj, 1)(2), 8);
});

test("参数不足时不会提前调用原函数", () => {
  let called = false;
  function fn(a, b) { called = true; return a + b; }
  const step = curry(fn)(1);
  assertEqual(called, false);
  assertEqual(step(2), 3);
  assertEqual(called, true);
});""",
         solution="""function curry(fn) {
  function collect(context, args) {
    return function curried(...nextArgs) {
      const allArgs = args.concat(nextArgs);
      const nextContext = context || this;
      if (allArgs.length >= fn.length) {
        return fn.apply(nextContext, allArgs);
      }
      return collect(nextContext, allArgs);
    };
  }
  return collect(null, []);
}""",
         points=["理解柯里化的触发条件来自函数形参数量 fn.length", "支持混合分组传参，而不是只能单参递归", "最终调用时要保留 this，否则对象方法会丢上下文"], hints=["每一层返回新函数并累积参数数组", "当累计参数数量达到 fn.length 时再 apply 调用原函数"]),

    dict(id="h8", order=8, title="数组扁平化并按 key 去重", level="中等", desc="题目要求：实现 flattenUnique(list, depth, key)，先按指定 depth 扁平化嵌套数组，再按对象的 key 字段去重，保留第一次出现的元素。业务上类似把多仓库存、多个促销分组或多页商品结果合并为展示列表。需要处理 depth 为 0、有限深度、Infinity、非对象元素和 key 缺失时的稳定行为。",
         starter="""function flattenUnique(list, depth, key) {
  // TODO
}""",
         tests="""test("按指定深度扁平化", () => {
  const input = [1, [2, [3, [4]]]];
  assertEqual(flattenUnique(input, 2, "id"), [1, 2, 3, [4]]);
});

test("depth 为 0 时不展开但仍按顶层去重", () => {
  const a = { id: 1, name: "a" };
  const b = { id: 1, name: "b" };
  assertEqual(flattenUnique([a, b], 0, "id"), [a]);
});

test("按 key 去重并保留第一次出现", () => {
  const input = [[{ id: "sku1", qty: 1 }], [{ id: "sku1", qty: 9 }, { id: "sku2", qty: 2 }]];
  const result = flattenUnique(input, Infinity, "id");
  assertEqual(result, [{ id: "sku1", qty: 1 }, { id: "sku2", qty: 2 }]);
});

test("缺少 key 的对象不互相误删", () => {
  const a = { name: "a" };
  const b = { name: "b" };
  assertEqual(flattenUnique([a, b], 1, "id"), [a, b]);
});

test("非对象元素按值去重", () => {
  assertEqual(flattenUnique([1, [1, 2, 2], "2"], Infinity, "id"), [1, 2, "2"]);
});

test("原数组不会被修改", () => {
  const input = [1, [2]];
  const result = flattenUnique(input, 1, "id");
  assertEqual(input, [1, [2]]);
  assertEqual(result, [1, 2]);
});""",
         solution="""function flattenUnique(list, depth = 1, key = "id") {
  const output = [];
  const seen = new Set();

  function flat(items, currentDepth) {
    for (const item of items) {
      if (Array.isArray(item) && currentDepth > 0) {
        flat(item, currentDepth === Infinity ? Infinity : currentDepth - 1);
      } else {
        output.push(item);
      }
    }
  }

  flat(list, depth);
  const result = [];
  for (const item of output) {
    let mark;
    if (item && typeof item === "object" && Object.prototype.hasOwnProperty.call(item, key)) {
      mark = "obj:" + String(item[key]);
    } else if (item && typeof item === "object") {
      result.push(item);
      continue;
    } else {
      mark = typeof item + ":" + String(item);
    }
    if (!seen.has(mark)) {
      seen.add(mark);
      result.push(item);
    }
  }
  return result;
}""",
         points=["能把扁平化深度和去重规则拆成两个阶段", "按 key 去重时保留首个元素，保证列表稳定性", "知道缺少 key 的对象不能都当成同一个 undefined 删除"], hints=["递归展开时 depth 每深入一层减一，Infinity 可以保持不变", "用 Set 存已出现的 key，普通值可用类型加值组成标记"]),

    dict(id="h9", order=9, title="LRU 缓存", level="中等", desc="题目要求：实现 LRUCache 类，构造函数传 capacity，提供 get(key) 与 put(key, value)，要求平均 O(1)。缓存满时淘汰最近最少使用的键；get 命中和 put 已存在键都要把该键提升为最新。该题对应商品详情、运费模板、权限配置等热点缓存，面试会追问 Map 顺序、容量边界和淘汰指标。",
         starter="""class LRUCache {
  constructor(capacity) {
    // TODO
  }
  get(key) {
    // TODO
  }
  put(key, value) {
    // TODO
  }
}""",
         tests="""test("get 未命中返回 -1", () => {
  const cache = new LRUCache(2);
  assertEqual(cache.get("missing"), -1);
});

test("put 后可以 get 到值", () => {
  const cache = new LRUCache(2);
  cache.put("a", 1);
  assertEqual(cache.get("a"), 1);
});

test("容量满时淘汰最久未使用", () => {
  const cache = new LRUCache(2);
  cache.put("a", 1);
  cache.put("b", 2);
  cache.put("c", 3);
  assertEqual(cache.get("a"), -1);
  assertEqual(cache.get("b"), 2);
  assertEqual(cache.get("c"), 3);
});

test("get 命中会刷新使用顺序", () => {
  const cache = new LRUCache(2);
  cache.put("a", 1);
  cache.put("b", 2);
  assertEqual(cache.get("a"), 1);
  cache.put("c", 3);
  assertEqual(cache.get("b"), -1);
  assertEqual(cache.get("a"), 1);
});

test("put 已存在键会更新值并刷新顺序", () => {
  const cache = new LRUCache(2);
  cache.put("a", 1);
  cache.put("b", 2);
  cache.put("a", 10);
  cache.put("c", 3);
  assertEqual(cache.get("a"), 10);
  assertEqual(cache.get("b"), -1);
});

test("capacity 为 0 时不保存任何值", () => {
  const cache = new LRUCache(0);
  cache.put("a", 1);
  assertEqual(cache.get("a"), -1);
});""",
         solution="""class LRUCache {
  constructor(capacity) {
    this.capacity = Math.max(0, capacity);
    this.map = new Map();
  }

  get(key) {
    if (!this.map.has(key)) return -1;
    const value = this.map.get(key);
    this.map.delete(key);
    this.map.set(key, value);
    return value;
  }

  put(key, value) {
    if (this.capacity <= 0) return;
    if (this.map.has(key)) this.map.delete(key);
    this.map.set(key, value);
    if (this.map.size > this.capacity) {
      const oldestKey = this.map.keys().next().value;
      this.map.delete(oldestKey);
    }
  }
}""",
         points=["利用 Map 的插入顺序实现最新元素放尾部", "get 与更新 put 都属于访问，需要刷新顺序", "容量为 0 或缓存穿透要有明确行为"], hints=["命中时先 delete 再 set，即可把键移动到 Map 尾部", "超容量时删除 map.keys().next().value"]),

    dict(id="h10", order=10, title="列表转树", level="中等", desc="题目要求：实现 listToTree(list, options)，把包含 id 与 parentId 的扁平列表转换为树结构，默认根节点 parentId 为 null。商家后台类目、仓库库区、菜单权限都常见这种结构。需要保持原始顺序，给每个节点创建 children 数组，处理父节点在后面的情况；找不到父节点的孤儿节点不要丢失，应放入 roots 并标记 orphan。",
         starter="""function listToTree(list, options) {
  // TODO
}""",
         tests="""test("基础父子关系会组成树", () => {
  const list = [{ id: 1, parentId: null, name: "root" }, { id: 2, parentId: 1, name: "child" }];
  const tree = listToTree(list);
  assertEqual(tree[0].children[0].name, "child");
});

test("父节点出现在子节点后面也能挂载", () => {
  const list = [{ id: 2, parentId: 1 }, { id: 1, parentId: null }];
  const tree = listToTree(list);
  assertEqual(tree, [{ id: 1, parentId: null, children: [{ id: 2, parentId: 1, children: [] }] }]);
});

test("孤儿节点放入根并标记 orphan", () => {
  const tree = listToTree([{ id: 3, parentId: 99, name: "lost" }]);
  assertEqual(tree[0].orphan, true);
  assertEqual(tree[0].children, []);
});

test("支持自定义字段名和根值", () => {
  const list = [{ key: "a", pid: 0 }, { key: "b", pid: "a" }];
  const tree = listToTree(list, { idKey: "key", parentKey: "pid", rootParentId: 0 });
  assertEqual(tree[0].children[0].key, "b");
});

test("不修改原始对象", () => {
  const node = { id: 1, parentId: null };
  const tree = listToTree([node]);
  tree[0].children.push({ id: 2 });
  assertEqual(node.children, undefined);
});

test("同级节点保持输入顺序", () => {
  const list = [{ id: 1, parentId: null }, { id: 2, parentId: 1 }, { id: 3, parentId: 1 }];
  const tree = listToTree(list);
  assertEqual(tree[0].children.map((x) => x.id), [2, 3]);
});""",
         solution="""function listToTree(list, options = {}) {
  const idKey = options.idKey || "id";
  const parentKey = options.parentKey || "parentId";
  const rootParentId = Object.prototype.hasOwnProperty.call(options, "rootParentId") ? options.rootParentId : null;
  const nodeMap = new Map();
  const roots = [];

  for (const item of list) {
    nodeMap.set(item[idKey], { ...item, children: [] });
  }

  for (const item of list) {
    const node = nodeMap.get(item[idKey]);
    const parentId = item[parentKey];
    if (parentId === rootParentId) {
      roots.push(node);
    } else {
      const parent = nodeMap.get(parentId);
      if (parent) parent.children.push(node);
      else {
        node.orphan = true;
        roots.push(node);
      }
    }
  }
  return roots;
}""",
         points=["两遍扫描能解决父节点出现在后面的问题", "复制节点而不是直接给原对象挂 children，避免污染输入", "孤儿节点要显式暴露，方便后续告警或数据修复"], hints=["第一遍建立 id 到新节点的 Map", "第二遍再根据 parentId 挂到父节点或 roots"]),

    dict(id="h11", order=11, title="指数退避重试 retry", level="困难", desc="题目要求：实现 retry(fn, options)，fn 返回 Promise；失败后按指数退避等待再重试，支持 retries、factor、minTimeout，最后仍失败时 reject 最后一次错误。该题对应调用库存、支付、物流轨迹等不稳定依赖：立即重试会放大故障，退避能降低冲击；但最大次数、延迟上限和错误透传必须可控，避免无限等待。",
         starter="""function retry(fn, options) {
  // TODO
}""",
         tests="""test("成功时直接返回结果", async () => {
  const result = await retry(() => Promise.resolve("ok"), { retries: 3, minTimeout: 5 });
  assertEqual(result, "ok");
});

test("失败后会重试直到成功", async () => {
  let attempts = 0;
  const result = await retry(() => {
    attempts += 1;
    if (attempts < 3) return Promise.reject(new Error("temp"));
    return Promise.resolve("done");
  }, { retries: 3, minTimeout: 5, factor: 2 });
  assertEqual(result, "done");
  assertEqual(attempts, 3);
});

test("超过最大次数返回最后一次错误", async () => {
  let attempts = 0;
  let last;
  await assertRejects(async () => {
    await retry(() => {
      attempts += 1;
      last = new Error("err" + attempts);
      return Promise.reject(last);
    }, { retries: 2, minTimeout: 5 });
  });
  assertEqual(attempts, 3);
});

test("退避等待会逐步变长", async () => {
  let attempts = 0;
  const start = Date.now();
  await assertRejects(() => retry(() => {
    attempts += 1;
    return Promise.reject(new Error("x"));
  }, { retries: 2, minTimeout: 10, factor: 2 }));
  assertEqual(attempts, 3);
  assert(Date.now() - start >= 25, "应至少等待两次退避");
});

test("同步抛错也会按失败处理", async () => {
  let attempts = 0;
  const result = await retry(() => {
    attempts += 1;
    if (attempts === 1) throw new Error("sync");
    return "ok";
  }, { retries: 1, minTimeout: 5 });
  assertEqual(result, "ok");
});

test("retries 为 0 时只执行一次", async () => {
  let attempts = 0;
  await assertRejects(() => retry(() => { attempts += 1; throw new Error("fail"); }, { retries: 0, minTimeout: 5 }));
  assertEqual(attempts, 1);
});""",
         solution="""function retry(fn, options = {}) {
  const retries = options.retries == null ? 3 : options.retries;
  const factor = options.factor == null ? 2 : options.factor;
  const minTimeout = options.minTimeout == null ? 100 : options.minTimeout;

  function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function attempt(index) {
    try {
      return await fn(index + 1);
    } catch (error) {
      if (index >= retries) throw error;
      const delay = minTimeout * Math.pow(factor, index);
      await wait(delay);
      return attempt(index + 1);
    }
  }

  return attempt(0);
}""",
         points=["区分最大重试次数和总尝试次数：总尝试 = retries + 1", "指数退避用 minTimeout * factor^失败序号，降低瞬时冲击", "必须抛出最后一次错误，方便调用方定位最终失败原因"], hints=["用 async/await 包住 fn，这样同步 throw 与 Promise reject 可统一处理", "失败后先判断次数，再 sleep，再进入下一次尝试"]),

    dict(id="h12", order=12, title="洋葱模型中间件 compose", level="困难", desc="题目要求：实现 compose(middlewares)，返回一个函数 fn(context, next)，执行顺序符合 koa 洋葱模型：前置逻辑按数组顺序进入，await next() 后的后置逻辑反向退出。需要把同一个 context 传递给所有中间件，支持外部 next，并且同一中间件里多次调用 next 必须报错，防止订单校验、鉴权、库存扣减等链路重复执行。",
         starter="""function compose(middlewares) {
  // TODO
}""",
         tests="""test("按洋葱顺序执行", async () => {
  const calls = [];
  const fn = compose([
    async (ctx, next) => { calls.push("a1"); await next(); calls.push("a2"); },
    async (ctx, next) => { calls.push("b1"); await next(); calls.push("b2"); }
  ]);
  await fn({});
  assertEqual(calls, ["a1", "b1", "b2", "a2"]);
});

test("所有中间件共享同一个 context", async () => {
  const ctx = { count: 0 };
  const fn = compose([
    async (ctx, next) => { ctx.count += 1; await next(); ctx.count += 1; },
    async (ctx) => { ctx.count += 10; }
  ]);
  await fn(ctx);
  assertEqual(ctx.count, 12);
});

test("支持外部 next", async () => {
  const calls = [];
  const fn = compose([async (ctx, next) => { calls.push("mw"); await next(); }]);
  await fn({}, async () => { calls.push("outer"); });
  assertEqual(calls, ["mw", "outer"]);
});

test("next 多次调用会 reject", async () => {
  const fn = compose([async (ctx, next) => { await next(); await next(); }]);
  await assertRejects(() => fn({}));
});

test("中间件抛错会向外 reject", async () => {
  const fn = compose([async () => { throw new Error("boom"); }]);
  await assertRejects(() => fn({}));
});

test("middlewares 必须是数组且元素必须是函数", () => {
  assertThrows(() => compose(null));
  assertThrows(() => compose([async () => {}, 1]));
});""",
         solution="""function compose(middlewares) {
  if (!Array.isArray(middlewares)) throw new TypeError("middlewares must be an array");
  for (const middleware of middlewares) {
    if (typeof middleware !== "function") throw new TypeError("middleware must be a function");
  }

  return function (context, next) {
    let index = -1;
    function dispatch(i) {
      if (i <= index) return Promise.reject(new Error("next() called multiple times"));
      index = i;
      let fn = middlewares[i];
      if (i === middlewares.length) fn = next;
      if (!fn) return Promise.resolve();
      try {
        return Promise.resolve(fn(context, function nextMiddleware() {
          return dispatch(i + 1);
        }));
      } catch (error) {
        return Promise.reject(error);
      }
    }
    return dispatch(0);
  };
}""",
         points=["能解释洋葱模型的进入顺序与退出顺序", "用 index 防止同一层多次 next 导致链路重复执行", "通过 Promise.resolve 统一同步和异步中间件"], hints=["compose 返回的函数内部递归 dispatch(i)", "如果 i 等于中间件长度，就执行外部 next 或直接 resolve"]),
]
