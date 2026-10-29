LANG = [
    dict(id="fe1", order=1, track="前端", lang="JavaScript", topic="事件循环与微任务", kind="output", q="下面代码的输出顺序是什么？", code="""
console.log("A");
setTimeout(() => console.log("B"), 0);
Promise.resolve().then(() => console.log("C"));
queueMicrotask(() => console.log("D"));
console.log("E");
""", answer="""A
E
C
D
B""", explain="""同步代码先压入调用栈执行，所以先打印 A、E。Promise.then 和 queueMicrotask 都进入微任务队列，按入队顺序在本轮宏任务结束后清空，因此 C 在 D 前。setTimeout 是下一轮宏任务，即使延迟为 0，也要等微任务清空后才执行，所以最后是 B。面试中要说清调用栈、微任务队列、宏任务队列三层机制。"""),
    dict(id="fe2", order=2, track="前端", lang="JavaScript", topic="Promise 链", kind="output", q="Promise 链中 then、catch、finally 的输出是什么？", code="""
Promise.resolve(1)
  .then(v => {
    console.log("then1", v);
    return v + 1;
  })
  .finally(() => {
    console.log("finally");
    return 99;
  })
  .then(v => {
    console.log("then2", v);
    throw new Error("x");
  })
  .catch(e => console.log("catch", e.message));
console.log("sync");
""", answer="""sync
then1 1
finally
then2 2
catch x""", explain="""Promise 回调都是微任务，所以同步的 sync 先输出。第一个 then 返回 2，finally 默认透传前一个 fulfilled 值，除非它抛错或返回 rejected Promise，因此 then2 收到的仍是 2。then2 抛错后链路转为 rejected，最近的 catch 消费错误。线上订单页常用这种链式流程，要避免误以为 finally 的返回值会覆盖正常结果。"""),
    dict(id="fe3", order=3, track="前端", lang="JavaScript", topic="async/await 顺序", kind="output", q="async/await 与 Promise 微任务交织时的输出顺序是什么？", code="""
async function run() {
  console.log("run1");
  await Promise.resolve();
  console.log("run2");
  await 0;
  console.log("run3");
}
console.log("start");
run();
Promise.resolve().then(() => console.log("then"));
console.log("end");
""", answer="""start
run1
end
run2
then
run3""", explain="""async 函数会同步执行到第一个 await 之前，所以 start、run1 先出现。await 后面的继续执行被排进微任务队列；run 调用后又注册了一个 Promise.then，因此队列先有 run2，再有 then。run2 内第二个 await 再追加一个微任务，所以 run3 最后。面试回答要指出 await 不是线程阻塞，而是拆分成后续微任务。"""),
    dict(id="fe4", order=4, track="前端", lang="JavaScript", topic="闭包与 var/let", kind="output", q="下面两组定时器为什么输出不同？", code="""
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log("var", i), 0);
}
for (let j = 0; j < 3; j++) {
  setTimeout(() => console.log("let", j), 0);
}
""", answer="""var 3
var 3
var 3
let 0
let 1
let 2""", explain="""var 是函数作用域，三个回调闭包共享同一个 i，循环结束时 i 已经变成 3，所以三个定时器都读到 3。let 在 for 循环每轮创建新的词法环境，每个回调绑定自己的 j，因此分别输出 0、1、2。这个差异常见于列表按钮绑定订单 id，失败模式是所有按钮都操作最后一条数据。"""),
    dict(id="fe5", order=5, track="前端", lang="JavaScript", topic="this 绑定", kind="output", q="普通函数、箭头函数、call 改变 this 后分别输出什么？", code="""
"use strict";
function makeOrder() {
  return {
    name: "order",
    normal() { return this.name; },
    arrow: () => (this === undefined ? "undefined" : this.name),
  };
}
const obj = makeOrder();
const fn = obj.normal;
console.log(obj.normal());
console.log(fn.call({ name: "pay" }));
console.log(obj.arrow.call({ name: "ship" }));
""", answer="""order
pay
undefined""", explain="""普通方法通过 obj.normal() 调用时，this 指向点号左侧的对象，所以是 order；把函数取出来再用 call 显式绑定，this 变成传入的对象，所以是 pay。箭头函数没有自己的 this，它捕获的是定义时外层函数 makeOrder 的 this；严格模式下直接调用 makeOrder()，this 是 undefined，而且 call 改不了箭头函数的 this，所以输出 undefined。面试要强调：普通函数的 this 由调用方式决定，箭头函数的 this 由定义位置决定。注意别把箭头函数直接写在脚本顶层考 this：Node 的 CommonJS 顶层 this 是 module.exports，浏览器顶层 this 是 window，结果不同。"""),
    dict(id="fe6", order=6, track="前端", lang="JavaScript", topic="原型链", kind="output", q="属性屏蔽与原型链查找的输出是什么？", code="""
function User(name) {
  this.name = name;
}
User.prototype.role = "buyer";
const u = new User("A");
console.log(u.role, u.hasOwnProperty("role"));
u.role = "seller";
console.log(u.role, u.hasOwnProperty("role"));
delete u.role;
console.log(u.role, Object.getPrototypeOf(u) === User.prototype);
""", answer="""buyer false
seller true
buyer true""", explain="""读取属性时先查实例自身，再沿原型链向上查。第一次 u 自身没有 role，所以读到 User.prototype.role，hasOwnProperty 为 false。赋值会在实例上创建同名自有属性，屏蔽原型值。delete 删除实例属性后，查找再次落到原型。面试可结合组件实例方法复用解释：机制省内存，但共享可变对象会带来串数据风险。"""),
    dict(id="fe7", order=7, track="前端", lang="JavaScript", topic="相等比较与类型转换", kind="choice", q="关于下面表达式，哪些说法正确？\n[] == ![]、0 == '0'、null == undefined、Number.isNaN(NaN)", options=["[] == ![] 为 true，因为 ![] 先转成 false，比较时两侧继续做 ToPrimitive/ToNumber", "null == 0 为 true，因为 null 会被转成数字 0", "0 == '0' 为 true，宽松相等会把字符串按数字比较", "Number.isNaN(NaN) 为 false，因为 NaN 不等于自身"], answer=[0, 2], explain="""宽松相等的失败模式是隐式转换链太长。![] 先得到 false，[] 与 false 比较时都会走数字化，最终是 0 == 0。0 与 '0' 也会把字符串转为数字，所以为 true。null 只与 undefined 在宽松相等下相等，不等于 0。Number.isNaN 不做类型强转，能准确识别真正的 NaN。面试建议说明业务代码优先使用 ===。"""),
    dict(id="fe8", order=8, track="前端", lang="JavaScript", topic="浮点数精度", kind="output", q="浮点运算与金额处理相关的输出是什么？", code="""
const a = 0.1 + 0.2;
console.log(a === 0.3);
console.log(a.toFixed(2));
const cents = 10 + 20;
console.log(cents === 30);
""", answer="""false
0.30
true""", explain="""JavaScript Number 使用二进制浮点，0.1 和 0.2 不能被精确表示，相加后不是严格等于 0.3。toFixed 只是按展示精度四舍五入，不代表底层值精确。订单金额、运费、优惠券核算应使用分为单位的整数或十进制定点库，指标上至少监控支付金额与订单金额差异，兜底是拒绝异常结算而不是静默抹零。"""),
    dict(id="fe9", order=9, track="前端", lang="JavaScript", topic="数组 sort/map/reduce", kind="output", q="数组默认排序、map 稀疏项、reduce 初值会带来什么输出？", code="""
const a = [10, 2, 1];
console.log(a.sort().join(","));
const b = [1, , 3].map(x => x * 2);
console.log(0 in b, 1 in b, b.length);
console.log([1, 2, 3].reduce((sum, x) => sum + x));
""", answer="""1,10,2
true false 3
6""", explain="""sort 默认按字符串字典序比较，所以 10 排在 2 前面，数字排序必须传 (a,b)=>a-b。map 不会访问稀疏数组的空洞，结果仍保留空洞，所以索引 1 不存在但长度是 3。reduce 没有初值时用第一个元素当累计值，空数组会抛错。分页价格排序和批量运费汇总中，这些默认行为都可能造成线上错序或异常。"""),
    dict(id="fe10", order=10, track="前端", lang="JavaScript", topic="深浅拷贝", kind="output", q="浅拷贝对象后修改嵌套字段，原对象会如何变化？", code="""
const order = { id: 1, items: [{ sku: "A", count: 1 }] };
const copy = { ...order };
copy.id = 2;
copy.items[0].count = 9;
console.log(order.id, order.items[0].count);
console.log(order.items === copy.items);
""", answer="""1 9
true""", explain="""对象展开只复制第一层属性值，id 是基础值，所以改 copy.id 不影响原对象；items 是引用值，复制的是同一个数组引用，修改嵌套商品数量会反映到原对象。业务失败模式是编辑草稿污染列表缓存。机制代价是深拷贝更耗 CPU 和内存，兜底可以用不可变更新、结构共享或只克隆发生变化的路径。"""),
    dict(id="fe11", order=11, track="前端", lang="JavaScript", topic="getter 副作用", kind="output", q="getter 被访问几次，输出是什么？", code="""
let hits = 0;
const obj = {
  get value() {
    hits += 1;
    return hits * 10;
  }
};
console.log(obj.value);
console.log(obj.value);
const { value } = obj;
console.log(value, hits);
""", answer="""10
20
30 3""", explain="""getter 是属性访问时执行的函数，不是存好的字段。每次读取 obj.value 都会触发一次，所以前两次分别把 hits 加到 1、2。解构时也会读取一次 getter，并把返回值保存到局部变量 value，因此是 30，hits 为 3。面试可补充：状态管理或响应式系统依赖 getter 收集依赖，getter 带副作用会让读取变成写操作，调试成本很高。"""),
    dict(id="fe12", order=12, track="前端", lang="JavaScript", topic="Proxy 拦截", kind="output", q="Proxy get/set 拦截后的输出是什么？", code="""
const log = [];
const target = { stock: 3 };
const proxy = new Proxy(target, {
  get(obj, key) {
    log.push("get:" + String(key));
    return obj[key];
  },
  set(obj, key, value) {
    log.push("set:" + String(key) + "=" + value);
    obj[key] = value;
    return true;
  }
});
proxy.stock -= 1;
console.log(target.stock);
console.log(log.join("|"));
""", answer="""2
get:stock|set:stock=2""", explain="""复合赋值 proxy.stock -= 1 会先读取旧值再写入新值，因此依次触发 get 和 set。set 中写的是原始 target，最终库存变为 2。Proxy 常用于响应式和表单校验，机制优势是能统一拦截对象操作，代价是调试调用栈更长、性能略有开销，兜底要保持 trap 返回值和语言规范一致，否则严格模式下会抛错。"""),
    dict(id="fe13", order=13, track="前端", lang="JavaScript", topic="生成器", kind="output", q="生成器 yield 与 return 的输出是什么？", code="""
function* ids() {
  yield "A";
  yield "B";
  return "C";
}
const it = ids();
console.log(JSON.stringify(it.next()));
console.log(JSON.stringify(it.next()));
console.log(JSON.stringify(it.next()));
console.log(JSON.stringify(it.next()));
""", answer="""{"value":"A","done":false}
{"value":"B","done":false}
{"value":"C","done":true}
{"done":true}""", explain="""生成器每次 next 恢复到下一个 yield，返回 {value, done}。前两次 yield 的 done 为 false。执行到 return 时 value 是 C、done 为 true，表示迭代结束。结束后继续 next 仍然 done 为 true，value 为 undefined；JSON.stringify 会省略 undefined 字段，所以只剩 done。面试中可把它类比为可暂停的拉模式数据流。"""),
    dict(id="fe14", order=14, track="前端", lang="JavaScript", topic="迭代器协议", kind="output", q="自定义迭代器配合 for...of 会输出什么？", code="""
const range = {
  from: 2,
  to: 4,
  [Symbol.iterator]() {
    let cur = this.from;
    const end = this.to;
    return {
      next() {
        return cur <= end ? { value: cur++, done: false } : { done: true };
      }
    };
  }
};
const out = [];
for (const n of range) out.push(n * 10);
console.log(out.join(","));
""", answer="""20,30,40""", explain="""for...of 会读取对象的 Symbol.iterator 方法，拿到迭代器后不断调用 next，直到 done 为 true。这里闭包中的 cur 从 2 增到 4，每次产出一个数字，循环体乘以 10 后得到 20、30、40。面试可强调可迭代对象与数组不是同一概念，分页游标、流式日志、批量订单处理都适合用迭代协议表达。"""),
    dict(id="fe15", order=15, track="前端", lang="JavaScript", topic="Promise 错误恢复", kind="output", q="catch 返回普通值后，后续 then 的状态是什么？", code="""
Promise.reject("bad")
  .then(() => console.log("then1"))
  .catch(e => {
    console.log("catch", e);
    return "ok";
  })
  .then(v => console.log("then2", v));
console.log("sync");
""", answer="""sync
catch bad
then2 ok""", explain="""初始 Promise 是 rejected，第一个 then 没有失败处理器，因此错误继续向后传。catch 捕获 bad 并返回普通值 ok，链路会恢复为 fulfilled，后续 then 正常执行。同步日志先输出，微任务里的 catch 和 then2 后输出。订单提交失败后如果 catch 只打日志又返回默认成功值，可能让 UI 误显示成功，所以要明确错误恢复边界。"""),
    dict(id="fe16", order=16, track="前端", lang="JavaScript", topic="深拷贝方案取舍", kind="short", q="在电商订单编辑页，为什么不能无脑使用 JSON.parse(JSON.stringify(obj)) 做深拷贝？请说明失败模式、替代方案和验证指标。", answer="""JSON 深拷贝只适合纯数据对象，遇到 Date 会变成字符串，Map、Set、函数、undefined、Symbol、循环引用会丢失或报错，原型链也会消失。订单编辑页如果包含本地校验函数、时间字段或缓存引用，可能出现金额展示正常但提交字段类型错误。更稳妥的做法是按业务 schema 做结构化复制，现代运行环境可评估 structuredClone，复杂状态用不可变更新和结构共享，只复制被修改路径。验证时看提交 payload 类型、脏字段数量、编辑撤销一致性、复制耗时 P95 和内存峰值。""", points=["说明 JSON 深拷贝会丢类型、丢原型、无法处理循环引用", "能给出 structuredClone、schema 复制、不可变更新等替代方案", "指出订单时间、金额、校验函数、缓存引用等具体失败模式", "提到性能和内存代价，不能只看功能正确", "给出 payload 类型、P95 耗时、内存峰值等验证指标"], explain="""这题考察候选人是否只背 API。深拷贝的约束来自数据类型和对象图，失败模式是类型退化或引用断裂；机制是序列化只能表达 JSON 子集；代价是 CPU、内存和 GC 压力；兜底要按字段契约复制并用指标验证。"""),
    dict(id="fe17", order=17, track="前端", lang="TypeScript", topic="类型收窄", kind="output", q="类型守卫只影响编译期，运行时输出是什么？", code="""
type Result = { ok: true; data: string } | { ok: false; error: string };
function show(r: Result) {
  if (r.ok) {
    console.log(r.data.toUpperCase());
  } else {
    console.log("ERR:" + r.error);
  }
}
show({ ok: true, data: "paid" });
show({ ok: false, error: "timeout" });
""", answer="""PAID
ERR:timeout""", explain="""判别联合用 ok 字段做类型收窄，TypeScript 在编译期知道 true 分支有 data，false 分支有 error。运行时并没有额外类型系统，代码被擦除后就是普通 JavaScript 分支判断。面试中要说明类型收窄能减少错误字段访问，但接口返回仍需运行时校验，否则后端字段漂移会绕过编译期保障。"""),
    dict(id="fe18", order=18, track="前端", lang="TypeScript", topic="泛型约束", kind="output", q="泛型约束保证有 id 字段，运行时输出是什么？", code="""
function pickId<T extends { id: string | number }>(item: T): string {
  return String(item.id);
}
const order = { id: 1001, status: "created" };
const user = { id: "u7", name: "ann" };
console.log(pickId(order));
console.log(pickId(user));
""", answer="""1001
u7""", explain="""T extends { id: string | number } 是编译期约束，保证传入对象至少有 id 字段，同时保留额外字段的类型信息。运行时类型标注被擦除，函数实际只是读取 item.id 并转字符串。泛型的价值是让订单、用户、商品等不同对象复用同一逻辑，不用把参数写成 any；代价是过度抽象会降低可读性。"""),
    dict(id="fe19", order=19, track="前端", lang="TypeScript", topic="联合与交叉类型", kind="choice", q="关于联合类型 A | B 和交叉类型 A & B，哪些说法正确？", options=["联合类型表示值满足 A 或 B，访问字段时只能直接访问所有成员共有字段", "交叉类型通常表示同时满足 A 和 B，因此会合并两边可兼容的字段约束", "如果两个对象类型交叉后同名字段类型冲突，该字段可能变成 never，从而难以构造", "联合类型在运行时会自动带上类型标签，所以不需要判别字段"], answer=[0, 1, 2], explain="""联合类型表达多种可能，编译器只允许直接访问共同字段，除非通过 in、typeof 或判别字段收窄。交叉类型表达同时具备多组能力，常用于组合基础字段和扩展字段。同名字段若约束互斥，例如 string 与 number 交叉，字段会变成 never。类型系统在运行时会被擦除，不会自动生成标签，所以接口设计仍要提供 status、kind 等判别字段。"""),
    dict(id="fe20", order=20, track="前端", lang="TypeScript", topic="unknown vs any", kind="short", q="接口返回数据应该优先用 unknown 还是 any？结合订单详情接口说明原因。", answer="""接口边界更推荐先用 unknown 表示“我还不知道类型”，因为 unknown 不能直接访问属性，必须经过 typeof、Array.isArray、字段存在性或 schema 校验后才能使用。any 会关闭类型检查，order.total.price 写错、把字符串金额当数字相加，都可能在编译期静默通过。订单详情接口可以把 fetch 结果声明为 unknown，然后校验 id、status、items、amountCents 等字段，再转换成内部 Order 类型。代价是多写校验代码，但换来边界清晰、错误更早暴露，线上兜底可以把校验失败计入接口契约错误指标。""", points=["unknown 需要收窄后才能访问，any 会绕过类型检查", "接口边界数据不可信，必须做运行时校验", "结合订单金额、状态、明细字段说明错误后果", "说明校验代码的成本与收益", "给出契约错误率或校验失败计数等指标"], explain="""这题考察类型安全边界。约束是网络数据不受前端编译器控制，失败模式是字段漂移和类型误用；unknown 通过强制收窄建立机制，代价是样板代码增加，兜底是运行时校验和指标告警。"""),
    dict(id="fe21", order=21, track="前端", lang="TypeScript", topic="satisfies", kind="output", q="satisfies 不改变运行时对象，下面输出是什么？", code="""
const route = {
  path: "/orders",
  cache: "short",
} satisfies { path: string; cache: "none" | "short" | "long" };
console.log(route.path);
console.log(route.cache === "short");
""", answer="""/orders
true""", explain="""satisfies 用来在编译期检查对象是否满足目标类型，同时尽量保留对象字面量自身的窄类型。它不会生成运行时代码，也不会改变对象结构，所以输出仍来自原始对象。配置类代码适合用 satisfies：既能检查 cache 是否在枚举范围内，又不会把 path、cache 过度扩大成模糊类型。"""),
    dict(id="fe22", order=22, track="前端", lang="TypeScript", topic="条件类型", kind="short", q="解释条件类型 T extends U ? X : Y 的用途，并说明在 API 响应封装中的一个应用。", answer="""条件类型可以根据输入类型在编译期选择输出类型，形式像类型层面的 if。它常与泛型和 infer 配合，从 Promise<T> 中取出 T，或根据接口是否分页返回不同的数据结构。例如请求函数 receive<T, Paged extends boolean> 可以让 Paged 为 true 时返回 {list:T[]; total:number}，否则返回 T。约束是这只发生在编译期，运行时仍要按真实响应字段判断。过度复杂的条件类型会让错误信息难懂，因此公共工具类型要有单元类型测试和简洁命名。""", points=["说明条件类型是编译期类型选择", "提到泛型、infer、Promise 解包等常见用途", "给出分页响应或 API 封装场景", "区分编译期类型和运行时数据校验", "指出复杂类型的可读性和维护成本"], explain="""条件类型的价值是把重复的类型分支抽象成规则，减少 API 响应手写类型。机制在编译器中完成，不会校验线上 JSON。面试回答要同时讲收益和代价，否则容易写出难维护的类型体操。"""),
    dict(id="fe23", order=23, track="前端", lang="TypeScript", topic="工具类型", kind="choice", q="关于 Partial、Pick、Omit、Readonly 等工具类型，哪些说法正确？", options=["Partial<T> 会把 T 的第一层属性变成可选，不会递归处理深层对象", "Pick<T, K> 选择指定字段，适合从完整订单类型中抽出列表卡片需要的字段", "Readonly<T> 会在运行时冻结对象，调用 push 一定会抛错", "Omit<T, K> 可以排除指定字段，常用于提交表单时去掉只读展示字段"], answer=[0, 1, 3], explain="""内置工具类型大多是编译期映射类型，不会生成运行时代码。Partial 默认只处理第一层字段；Pick 能从大类型里选择一组字段，减少重复定义；Omit 能排除字段，适合提交前去掉展示态或后端生成字段。Readonly 只限制 TypeScript 层面的写入，不能替代 Object.freeze 或不可变数据结构。面试要说明这些工具能提升一致性，但不能替代接口校验。"""),
    dict(id="fe24", order=24, track="前端", lang="React", topic="渲染与重新渲染", kind="choice", q="哪些情况通常会触发 React 组件重新渲染？", options=["组件自身 state 发生更新", "父组件重新渲染且子组件没有被 memo 等机制跳过", "直接修改 useRef.current 的值", "组件接收到的 props 引用或值发生变化"], answer=[0, 1, 3], explain="""React 重新渲染来自状态、属性和父子渲染链。state 更新会调度当前组件；父组件渲染时，子组件默认也会执行渲染函数，除非被 memo 且 props 比较通过；props 变化会让子组件看到新输入。useRef.current 修改不会触发渲染，因为它是可变容器。订单列表性能优化要先用渲染次数和单次耗时定位，而不是盲目加 memo。"""),
    dict(id="fe25", order=25, track="前端", lang="React", topic="useEffect 时机与清理", kind="short", q="订单详情页订阅物流轨迹轮询时，useEffect 的执行和清理应该怎么设计？", answer="""useEffect 在浏览器完成绘制后异步执行，适合启动轮询、订阅和日志上报等副作用。物流轨迹轮询应把 orderId 放进依赖数组，effect 内创建定时器或 AbortController，每次 orderId 变化前以及组件卸载时执行 cleanup，清掉定时器并取消未完成请求，避免旧订单请求覆盖新订单状态。约束是网络慢和用户快速切换订单会产生竞态，兜底可以在响应回来时校验当前 orderId 或使用请求序号。指标看重复请求数、取消请求数、错误率和页面卸载后的请求残留。""", points=["说明 useEffect 在提交和绘制后执行", "依赖数组应包含 orderId 等真实依赖", "cleanup 清理定时器、订阅、未完成请求", "识别快速切换订单导致的竞态", "给出请求残留、重复请求、错误率等指标"], explain="""这题重点不是背生命周期，而是副作用契约。约束是组件会重复挂载、依赖会变化、请求会乱序；机制是 effect 返回清理函数；代价是多写取消逻辑；兜底是响应校验和指标监控。"""),
    dict(id="fe26", order=26, track="前端", lang="React", topic="闭包陷阱", kind="choice", q="关于 React Hooks 闭包陷阱，哪些说法正确？", options=["定时器回调会捕获创建时那次渲染的变量值", "依赖数组漏掉 count，effect 内看到的 count 可能长期是旧值", "把所有依赖都删掉可以提升性能且不会影响正确性", "可用函数式 setState 或 ref 读取最新值来处理部分场景"], answer=[0, 1, 3], explain="""函数组件每次渲染都会创建新的变量绑定，回调闭包捕获的是当次渲染的值。依赖数组漏项会让 effect 不重新创建，回调持续使用旧 count，常见失败是购物车数量、倒计时或轮询参数不同步。删除依赖只是隐藏问题。函数式更新能基于最新状态计算，ref 可保存可变最新值，但要权衡可读性和一致性。"""),
    dict(id="fe27", order=27, track="前端", lang="React", topic="key 与列表复用", kind="short", q="为什么订单行列表不能用数组下标作为 key？什么时候可以例外？", answer="""key 用来帮助 React 在同一层子节点之间建立稳定身份。订单行如果支持插入、删除、排序、筛选，用下标作为 key 会让同一 DOM 和组件状态被错误复用，例如第 2 行输入框的备注在删除第 1 行后跑到别的订单上。应该使用订单行 id、skuId 加仓库 id 等稳定业务标识。例外是列表完全静态、不会重排、不会插入删除、也没有行内状态时，下标 key 风险较低。验证可以写一个先编辑第 N 行再删除前一行的测试。""", points=["说明 key 是稳定身份，不只是消除警告", "指出插入、删除、排序会导致状态错位", "给出订单备注或行内输入框的具体失败模式", "推荐稳定业务 id", "说明静态列表才可低风险使用下标"], explain="""key 的机制是协调算法用它判断复用还是新建。下标 key 的约束是位置变化会改变身份，失败模式是状态错绑。面试中要能给出可复现步骤，而不是只说性能不好。"""),
    dict(id="fe28", order=28, track="前端", lang="React", topic="memo 与 useMemo/useCallback", kind="choice", q="关于 React.memo、useMemo、useCallback 的使用，哪些说法正确？", options=["React.memo 只有在 props 比较能跳过渲染时才有收益", "useMemo 适合缓存昂贵计算结果，但依赖不准会得到过期值", "useCallback 总能显著提升性能，所以每个函数都应该包一层", "如果子组件不做 memo，单独 useCallback 稳定函数引用通常收益有限"], answer=[0, 1, 3], explain="""这些 API 的约束都是缓存需要成本。React.memo 要做 props 比较，只有跳过渲染的收益大于比较成本才值得；useMemo 缓存计算结果，依赖错会产生旧数据；useCallback 缓存函数引用，主要用于传给 memo 子组件或作为 effect 依赖。大促订单表格优化应先用性能面板找到慢组件，再用渲染次数和交互耗时验证收益。"""),
    dict(id="fe29", order=29, track="前端", lang="React", topic="状态批处理", kind="choice", q="关于 React 状态批处理，哪些说法正确？", options=["同一次事件处理中的多次 setState 通常会被批处理，减少渲染次数", "连续 setCount(count + 1) 两次一定等价于加 2", "需要基于前一个状态更新时，函数式写法 setCount(c => c + 1) 更可靠", "批处理意味着 setState 后立刻读取 state 变量一定是新值"], answer=[0, 2], explain="""批处理会把同一批更新合并提交，减少中间渲染，这是性能机制。闭包里的 count 是当前渲染快照，连续 setCount(count + 1) 可能两次都计算同一个值；函数式更新能按队列中的前值逐步计算，更适合库存加减、购物车数量累加。setState 后当前闭包变量不会同步变新，读取新值应依赖下一次渲染或 effect。"""),
    dict(id="fe30", order=30, track="前端", lang="React", topic="受控组件", kind="short", q="商家工作台表单中，受控组件和非受控组件如何取舍？", answer="""受控组件把输入值放在 React state 中，value 和 onChange 构成单一数据源，适合需要实时校验、联动、禁用提交按钮、草稿保存的表单，例如库存数量变化后立即重新计算可售状态。代价是每次输入都可能触发渲染，大表单要拆分组件、局部状态或延迟校验。非受控组件把值留在 DOM，通过 ref 在提交时读取，适合简单搜索框、文件上传或性能敏感但联动很少的场景。兜底是明确字段所有权，避免同一输入在受控和非受控之间切换。""", points=["受控组件以 state 为单一数据源", "说明实时校验、联动、草稿保存等适用场景", "说明渲染成本和大表单优化手段", "非受控适合简单或文件等场景", "避免受控与非受控切换"], explain="""表单取舍的因果链是：约束来自字段联动和校验实时性，机制是 state 或 DOM 持有值，代价是渲染频率或可控性，兜底是字段所有权一致，指标看输入延迟和校验错误率。"""),
    dict(id="fe31", order=31, track="前端", lang="React", topic="性能优化", kind="short", q="订单列表首屏慢，React 侧你会如何定位和优化？", answer="""先分清网络、脚本、渲染三类耗时：用性能面板看首屏时间、长任务和提交阶段耗时，用组件分析工具看哪些组件重复渲染。若数据量大，优先做分页、虚拟列表或服务端过滤，减少 DOM 节点数量；若单行渲染重，再拆分行组件、使用 memo、稳定 props、缓存昂贵格式化；若交互卡顿，可把搜索输入和列表计算解耦，必要时使用延迟渲染。兜底指标包括首屏 P75/P95、交互延迟、渲染提交耗时、行数和内存峰值。""", points=["先定位网络、脚本、渲染瓶颈", "使用性能面板和组件渲染分析", "数据量大优先分页或虚拟列表", "单组件重再使用 memo、缓存和拆分", "给出首屏、交互延迟、提交耗时等指标"], explain="""性能题要避免直接开药。约束可能是数据量、计算量或渲染树太大；失败模式是首屏慢、滚动卡、输入延迟；机制和代价不同，优化顺序也不同。面试回答要先测量再改动。"""),
    dict(id="fe32", order=32, track="前端", lang="Vue", topic="响应式 Proxy", kind="short", q="Vue 3 为什么用 Proxy 做响应式？它相比 defineProperty 解决了什么问题，又有哪些边界？", answer="""Proxy 可以拦截对象的 get、set、deleteProperty、has、ownKeys 等操作，Vue 3 借此在读取时收集依赖，在写入时触发更新。相比 defineProperty 逐个属性劫持，Proxy 更容易处理新增属性、删除属性、数组索引和 length 变化，初始化成本也更低。边界是 Proxy 只能代理对象本身，解构后可能丢失响应式连接，嵌套对象通常在访问时再递归代理，原始值要用 ref 包装。代价是需要现代运行环境支持，调试时也要区分原始对象和代理对象。""", points=["说明 get 收集依赖、set 触发更新", "对比 defineProperty 对新增删除和数组处理的不足", "指出解构、原始值、嵌套对象等边界", "说明代理对象和原始对象的区别", "提到初始化成本和运行环境约束"], explain="""响应式的因果链是读取建立依赖、写入通知更新。Proxy 扩大了可拦截操作范围，减少对数组和新增属性的特殊处理；代价是代理身份不同、部分写法会断开依赖，面试要讲机制而非只说更快。"""),
    dict(id="fe33", order=33, track="前端", lang="Vue", topic="computed vs watch", kind="choice", q="关于 computed 和 watch，哪些说法正确？", options=["computed 适合从已有响应式状态派生同步值，并且有缓存", "watch 适合响应状态变化后执行异步请求、日志或命令式副作用", "computed getter 中发请求是推荐写法，因为能自动缓存接口结果", "当订单金额由商品行派生时，computed 通常比 watch 手动赋值更清晰"], answer=[0, 1, 3], explain="""computed 是声明式派生值，依赖不变时会缓存结果，适合订单总价、筛选条件展示等同步计算。watch 关注变化后的副作用，适合根据订单 id 拉取物流、写本地缓存或上报日志。computed getter 应保持纯净，不应发请求，否则读取行为会变成副作用，缓存失效和错误处理都不直观。面试回答要把派生状态和副作用分开。"""),
    dict(id="fe34", order=34, track="前端", lang="Vue", topic="nextTick", kind="short", q="Vue 中 nextTick 解决什么问题？在库存输入后滚动到错误项的场景如何使用？", answer="""Vue 会批量合并同一轮事件中的响应式更新，并在异步队列中刷新 DOM。修改库存数量后，错误提示节点不会立刻出现在当前同步代码可读的 DOM 中，此时直接 querySelector 可能找不到或位置不准。nextTick 会等本轮 DOM 更新完成后再执行回调或 Promise，适合在校验状态变更后滚动到第一个错误项、测量元素尺寸、聚焦输入框。代价是它只保证 Vue DOM 刷新完成，不保证图片加载或网络请求完成，复杂场景还要监听对应事件。""", points=["说明 Vue 会批量异步刷新 DOM", "指出同步读取 DOM 可能拿到旧结构", "给出滚动错误项、测量尺寸、聚焦输入等场景", "区分 nextTick 与网络或资源加载完成", "说明它是兜底时机工具而非业务状态管理"], explain="""nextTick 的机制来自批量更新：状态已变但 DOM 尚未提交。失败模式是读旧 DOM 或滚动位置错误；兜底是在 DOM 更新后执行命令式操作。面试要强调不要用它掩盖状态设计问题。"""),
    dict(id="fe35", order=35, track="前端", lang="Vue", topic="v-if vs v-show", kind="choice", q="关于 v-if 和 v-show 的取舍，哪些说法正确？", options=["v-if 会真正创建或销毁节点，初始条件为 false 时可以不渲染", "v-show 通过 display 控制显示隐藏，节点仍然存在", "频繁切换的面板通常更适合 v-show，但初始渲染成本仍要承担", "权限敏感内容用 v-show 隐藏就等于安全，不会被查看"], answer=[0, 1, 2], explain="""v-if 是条件渲染，切换会创建和销毁组件，适合低频切换或初始不需要渲染的重组件。v-show 是样式显示隐藏，切换成本低但初始仍渲染，适合高频展开收起。权限内容不能只靠前端隐藏，v-show 下 DOM 仍存在，接口和后端权限必须控制。面试要能从切换频率、初始成本、安全边界三方面回答。"""),
    dict(id="fe36", order=36, track="前端", lang="Vue", topic="组件通信", kind="short", q="Vue 商家工作台中父子、跨层、全局状态分别适合用什么通信方式？", answer="""父组件向子组件传只读输入用 props，子组件需要通知父组件时用 emits，适合商品行编辑后把变化交给订单表单。跨层但关系稳定的配置，如表单上下文、主题、校验器，可以用 provide/inject，避免逐层透传。多个页面或远距离组件共享的登录用户、购物车、仓库选择，应放到全局状态管理中，并定义清晰的 action 和持久化策略。事件总线虽然方便，但来源难追踪，大型页面容易失控。指标上要关注状态来源数量、重复请求、调试可追踪性和组件复用成本。""", points=["props/emits 用于父子单向数据流", "provide/inject 用于稳定跨层依赖", "全局状态用于多页面共享数据", "指出事件总线的可追踪性问题", "结合商家工作台场景说明边界"], explain="""通信方式的约束是组件距离、共享范围和可追踪性。机制越全局，耦合和调试成本越高。面试回答要避免一个工具打天下，而是按状态所有权选择最小可用范围。"""),
    dict(id="fe37", order=37, track="前端", lang="CSS", topic="BFC", kind="short", q="什么是 BFC？它能解决哪些布局问题，代价是什么？", answer="""BFC 是块级格式化上下文，可以理解为一块独立的布局区域，内部浮动和外部元素不会随意相互影响。常见触发方式包括 overflow 非 visible、display: flow-root、浮动、绝对定位、inline-block 等。它可以清除浮动导致的父元素高度塌陷，也能避免外边距折叠和文字环绕浮动元素。代价是某些触发方式会带来副作用，例如 overflow: hidden 会裁剪阴影和下拉层。更推荐语义清晰的 display: flow-root，面试要说明解决的是布局隔离问题。""", points=["说明 BFC 是独立布局上下文", "列举 overflow、flow-root、float、absolute 等触发方式", "说明清浮动、高度塌陷、外边距折叠等问题", "指出 overflow hidden 的裁剪副作用", "推荐根据副作用选择触发方式"], explain="""BFC 的因果链是浮动和外边距会影响相邻布局，独立格式化上下文提供隔离机制。不同触发方式代价不同，不能只背清浮动，要能说明为什么 flow-root 更直观。"""),
    dict(id="fe38", order=38, track="前端", lang="CSS", topic="层叠上下文与 z-index", kind="choice", q="关于层叠上下文和 z-index，哪些说法正确？", options=["z-index 只在定位元素或特定布局上下文中按规则生效，不是任意元素都能比较", "transform、opacity 小于 1、position 配合 z-index 等都可能创建新的层叠上下文", "子元素的 z-index 再大，也不能突破祖先层叠上下文去压过外部更高层", "把弹窗 z-index 设成 999999 一定能盖住所有内容"], answer=[0, 1, 2], explain="""层叠上下文是分组比较机制，先比较不同上下文，再比较上下文内部。transform、opacity、定位加 z-index 等会创建新上下文，导致子元素只能在父上下文内部排序。弹窗被父容器 transform 或 overflow 限制时，单纯增大 z-index 可能无效。订单操作弹窗常用 portal 挂到页面根节点，并统一管理层级 token，指标看遮挡投诉和弹层冲突数。"""),
    dict(id="fe39", order=39, track="前端", lang="CSS", topic="flex 布局计算", kind="short", q="解释 flex: 1 的含义，以及订单列表中左右栏宽度异常时如何排查。", answer="""flex: 1 通常等价于 flex-grow: 1、flex-shrink: 1、flex-basis: 0%，表示项目从 0 基础宽度开始按剩余空间伸展，也允许收缩。左右栏宽度异常时，先看容器主轴方向、可用宽度、gap 和 padding，再看每个项目的 flex-basis、grow、shrink、min-width。很多文本列默认 min-width: auto，会因为长订单号或地址不换行而撑开容器，需要设置 min-width: 0 并配合 overflow 省略。验证指标是不同屏宽下列宽、换行次数和横向滚动是否出现。""", points=["说明 flex:1 的 grow、shrink、basis 含义", "排查主轴、剩余空间、gap、padding", "关注 min-width:auto 和长文本撑开", "给出 min-width:0、overflow 等修复手段", "说明多屏宽验证指标"], explain="""flex 问题常来自约束不完整：剩余空间如何分、项目能否缩、最小内容宽度是多少。机制是主轴空间分配，失败模式是长文本撑破或比例不对，兜底是明确 basis 和 min-width。"""),
    dict(id="fe40", order=40, track="前端", lang="CSS", topic="盒模型", kind="choice", q="关于盒模型，哪些说法正确？", options=["content-box 下 width 只包含内容区，padding 和 border 会额外增加总宽度", "border-box 下 width 包含内容区、padding 和 border，更适合组件布局", "margin 会计入元素自身 width，因此 border-box 能限制 margin 不溢出", "全局设置 box-sizing: border-box 可以减少表单和卡片宽度计算错误"], answer=[0, 1, 3], explain="""标准盒模型 content-box 中，声明 width 只是内容宽度，总占位还要加 padding、border、margin。border-box 把 padding 和 border 包进 width，更符合组件设计稿的固定宽度直觉，但 margin 仍在盒子外，不会被包含。后台表格、筛选栏和卡片布局通常全局设置 border-box，减少 100% 宽度再加 padding 导致横向滚动的失败模式。"""),
    dict(id="fe41", order=41, track="前端", lang="浏览器", topic="渲染流程与重排重绘", kind="short", q="浏览器从拿到 HTML 到页面可见大致经历哪些步骤？如何减少重排重绘？", answer="""浏览器会解析 HTML 构建 DOM，解析 CSS 构建 CSSOM，两者合成渲染树后计算布局，再绘制和合成图层。JavaScript 可能阻塞解析，也可能读取布局信息迫使浏览器提前刷新布局。重排影响几何尺寸和位置，成本通常高于只改颜色的重绘。优化上要批量读写 DOM，避免循环中交替读取 offsetHeight 和写 style；动画优先使用 transform、opacity；大列表减少节点数；关键 CSS 尽量早到达。指标看首屏时间、长任务、布局次数、布局耗时和帧率。""", points=["说明 DOM、CSSOM、渲染树、布局、绘制、合成流程", "区分重排和重绘", "指出 JS 读写布局可能强制同步布局", "给出批量读写、transform、虚拟列表等优化", "给出布局耗时、帧率、首屏等指标"], explain="""浏览器性能的约束是主线程要解析、执行脚本和布局绘制。失败模式是强制同步布局和节点过多。机制层面减少几何变化和 DOM 数量，兜底用性能面板量化，而不是凭感觉优化。"""),
    dict(id="fe42", order=42, track="前端", lang="浏览器", topic="HTTP 缓存", kind="choice", q="关于强缓存和协商缓存，哪些说法正确？", options=["Cache-Control: max-age=60 命中时，浏览器可在 60 秒内不发请求直接用本地缓存", "ETag/If-None-Match 或 Last-Modified/If-Modified-Since 属于协商缓存，需要向服务器确认", "304 响应表示资源未变化，通常复用本地缓存体", "no-store 表示可以缓存但每次都必须重新验证"], answer=[0, 1, 2], explain="""强缓存命中时不走网络，适合带 hash 的静态资源，约束是内容变更必须换 URL 或版本。协商缓存会发请求，让服务器用 ETag 或 Last-Modified 判断是否变化，未变化返回 304，节省响应体流量。no-store 是不存储，no-cache 才是可存但使用前必须验证。订单后台 HTML 通常短缓存或 no-cache，静态 JS/CSS 用长缓存加内容 hash。"""),
    dict(id="fe43", order=43, track="前端", lang="浏览器", topic="跨域与 CORS 预检", kind="short", q="为什么有些跨域请求会先发 OPTIONS 预检？后端需要返回哪些关键头？", answer="""浏览器同源策略限制脚本读取跨源响应。CORS 允许服务器声明哪些来源、方法和请求头可以访问。非简单请求，例如 PUT、DELETE、Content-Type 为 application/json 或带自定义请求头时，浏览器会先发 OPTIONS 预检，询问服务端是否允许真实请求。后端通常要返回 Access-Control-Allow-Origin、Access-Control-Allow-Methods、Access-Control-Allow-Headers；带 Cookie 时还要 Access-Control-Allow-Credentials: true，且 Origin 不能随意写 *。指标看预检成功率、真实请求错误率和预检缓存时间。""", points=["说明同源策略和 CORS 的关系", "说明非简单请求触发 OPTIONS 预检", "列出 Allow-Origin、Allow-Methods、Allow-Headers", "说明带凭证时 Credentials 和非通配 Origin", "给出预检成功率、错误率、缓存时间等指标"], explain="""预检的约束是浏览器要先确认跨源写操作或复杂头是否被允许。机制是 OPTIONS 握手，失败模式是前端只看到 CORS 错误但真实接口没被调用。面试要能区分浏览器限制和服务端业务错误。"""),
    dict(id="fe44", order=44, track="前端", lang="浏览器", topic="Cookie 与本地存储", kind="choice", q="关于 Cookie、localStorage、sessionStorage 和 SameSite，哪些说法正确？", options=["Cookie 会按域名和路径等规则随请求自动携带，适合会话标识但要注意安全属性", "localStorage 容量通常比 Cookie 大，但不会自动随请求发送", "SameSite 可以降低跨站请求伪造风险，常见取值有 Strict、Lax、None", "把访问令牌放到 localStorage 后就完全不怕脚本注入风险"], answer=[0, 1, 2], explain="""Cookie 的特点是自动随请求携带，适合会话，但要配置 HttpOnly、Secure、SameSite 等属性降低脚本读取和跨站请求风险。localStorage 和 sessionStorage 由脚本读写，不自动上送，容量通常更大，但遇到脚本注入时可能被读取。SameSite 限制跨站请求携带 Cookie，None 通常要求 Secure。面试要把存储能力、自动携带、安全边界分开讲。"""),
    dict(id="fe45", order=45, track="前端", lang="工程化", topic="Vite vs Webpack", kind="short", q="Vite 和 Webpack 在开发构建上的核心差异是什么？适合如何选型？", answer="""Webpack 以模块图为中心，开发时通常先打包再提供给浏览器，生态成熟，适合复杂历史项目、深度 loader/plugin 定制和多种遗留格式。Vite 开发时利用浏览器原生 ESM，源文件按需转换，依赖预构建后缓存，因此冷启动和热更新通常更快；生产构建仍会做打包和优化。选型要看项目规模、框架生态、插件需求、兼容目标、构建耗时和团队熟悉度。约束不是“新工具一定更好”，迁移要用首启时间、热更新时间、生产包体、插件替代成本来验证。""", points=["说明 Webpack 打包型开发流程", "说明 Vite 基于原生 ESM 和按需转换", "指出生产构建仍需打包优化", "按生态、插件、兼容、团队成本选型", "给出首启、热更新、包体等指标"], explain="""工程化选型要讲约束和指标。Vite 的机制降低开发期全量打包成本，Webpack 的机制和生态适合复杂定制。失败模式是只看口号迁移，最后插件不兼容或生产包体退化。"""),
    dict(id="fe46", order=46, track="前端", lang="工程化", topic="Tree Shaking 与代码分割", kind="choice", q="关于 Tree Shaking、sideEffects 和代码分割，哪些说法正确？", options=["Tree Shaking 依赖静态模块结构，ESM 比动态 require 更容易分析", "package.json 的 sideEffects 可帮助打包器判断未引用模块能否安全删除", "代码分割一定会减少首屏请求数量，所以总是越碎越好", "动态 import 常用于路由级或重组件懒加载，能降低首屏执行成本"], answer=[0, 1, 3], explain="""Tree Shaking 的约束是打包器要静态判断导入导出和副作用，ESM 更利于分析。sideEffects 声明能帮助删除未使用文件，但错误声明会删掉必要的全局样式或初始化代码。代码分割减少首屏下载和执行，但 chunk 太碎会增加请求调度和缓存管理成本。订单后台常按路由、图表、富文本等重模块懒加载，用首屏 JS 体积、执行耗时和缓存命中率验证。"""),
    dict(id="fe47", order=47, track="前端", lang="网络", topic="HTTP/2 与 HTTP/3", kind="short", q="HTTP/2 和 HTTP/3 分别解决了什么问题？对前端性能有什么影响？", answer="""HTTP/2 在一个 TCP 连接上复用多个请求，引入头部压缩和流优先级，减少 HTTP/1.1 多连接和队头排队带来的开销。但因为底层仍是 TCP，一个包丢失可能阻塞同连接上的多个流。HTTP/3 基于 QUIC 和 UDP，把多路复用做到传输层，降低 TCP 队头阻塞影响，并支持更快的连接建立。前端影响是资源合并策略、域名分片和小文件加载策略会改变。验证要看首字节时间、丢包网络下加载时间、连接复用率和错误回退率。""", points=["HTTP/2 多路复用和头部压缩", "指出 HTTP/2 仍受 TCP 丢包影响", "HTTP/3 基于 QUIC/UDP 减少传输层队头阻塞", "说明资源合并、域名分片策略变化", "给出 TTFB、弱网加载、复用率等指标"], explain="""网络协议题要从约束讲起：连接建立、头部冗余、队头阻塞。机制升级带来性能收益，但也有部署和回退成本。面试回答不能只说版本更高更快，要说明在什么网络条件下体现。"""),
    dict(id="fe48", order=48, track="前端", lang="网络", topic="HTTPS 与状态码", kind="choice", q="关于 HTTPS 握手和常见状态码，哪些说法正确？", options=["HTTPS 通过证书验证服务端身份，并协商对称密钥保护后续传输", "301 通常表示永久重定向，302 通常表示临时重定向", "304 表示未授权，需要重新登录", "401 表示未认证，403 表示已识别身份但无权限"], answer=[0, 1, 3], explain="""HTTPS 的核心是先用证书链验证服务端身份，再协商会话密钥，后续用对称加密保护传输机密性和完整性。301 和 302 都是重定向，但缓存和语义不同，永久迁移更适合 301。304 是缓存协商未修改，不是权限问题。401 表示需要认证或认证失效，403 表示身份已知但权限不足。订单后台排障时要把缓存、登录态和权限拦截分开看。"""),
]
