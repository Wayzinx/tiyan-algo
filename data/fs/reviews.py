REVIEWS = [
    dict(
        id="r1",
        order=1,
        lang="TypeScript / React",
        title="商品搜索列表根据关键词请求接口并渲染结果",
        context="电商商家工作台的商品搜索组件，运营在输入框里连续输入关键词，组件会调用后端搜索接口并展示商品。代码看起来能跑，但在慢网络、快速输入、路由切换时会暴露状态一致性问题。",
        code="""import React, { useEffect, useState } from "react";

type Product = {
  id: string;
  name: string;
  stock: number;
};

export function ProductSearch({ keyword }: { keyword: string }) {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!keyword) {
      setItems([]);
      return;
    }
    setLoading(true);
    fetch(`/api/products/search?q=${encodeURIComponent(keyword)}`)
      .then((res) => res.json())
      .then((data) => {
        setItems(data.items || []);
        setLoading(false);
      });
  }, []);

  return (
    <section>
      <h3>商品搜索</h3>
      {loading && <p>加载中...</p>}
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.name} / 库存 {item.stock}</li>
        ))}
      </ul>
    </section>
  );
}
""",
        issues=[
            dict(lines="12-27", severity="严重", kind="bug", desc="useEffect 依赖数组为空，keyword 变化后不会重新请求，用户改搜索词仍看到旧商品，导致运营误判库存和商品状态。", fix="把 keyword 放入依赖数组，并在空关键词分支同时复位 loading。"),
            dict(lines="18-24", severity="严重", kind="健壮性", desc="没有处理请求竞态，先输入的慢请求可能后返回并覆盖后输入的新结果，典型后发先至会展示错误列表。", fix="使用 AbortController 或递增 requestId，只允许最后一次请求写入 state。"),
            dict(lines="21-23", severity="一般", kind="bug", desc="组件卸载后请求仍可能 resolve 并 setState，路由切换时会产生无效更新和难排查的告警。", fix="在 effect cleanup 中 abort 请求，或用 active 标记阻止卸载后的状态写入。"),
            dict(lines="19-24", severity="一般", kind="健壮性", desc="fetch、HTTP 非 2xx、JSON 解析失败都没有 catch，loading 也不会复位，页面会一直显示加载中。", fix="检查 res.ok，用 try/catch/finally 统一落错误态和 loading。"),
        ],
        summary="总评：这段代码最大风险是异步请求生命周期没有和 React 渲染生命周期对齐。合并前必须补齐 keyword 依赖、取消过期请求、处理错误和卸载清理，否则慢网络下会把旧搜索结果当成当前结果展示。",
        points=["指出 useEffect 依赖缺失", "识别请求竞态和旧结果覆盖", "说明卸载后 setState 风险", "要求错误处理和 loading 兜底", "能给出 AbortController 或 requestId 修法"],
    ),
    dict(
        id="r2",
        order=2,
        lang="TypeScript / React",
        title="购物车列表调整商品数量并重新计算小计",
        context="订单确认页的购物车组件，用户可以增加或减少商品数量，前端先做乐观更新再等待后端保存。评审重点是列表渲染稳定性、状态不可变更新，以及在插入删除商品时数据是否串行。",
        code="""import React, { useState } from "react";

type CartLine = {
  skuId: string;
  title: string;
  priceCent: number;
  quantity: number;
};

export function CartEditor({ initial }: { initial: CartLine[] }) {
  const [lines, setLines] = useState(initial);
  const [message, setMessage] = useState("");

  function changeQuantity(index: number, delta: number) {
    const next = lines;
    next[index].quantity += delta;
    if (next[index].quantity <= 0) {
      next.splice(index, 1);
    }
    setLines(next);
    setMessage("已更新");
  }

  function totalCent() {
    return lines.reduce((sum, line) => sum + line.priceCent * line.quantity, 0);
  }

  return (
    <div>
      <h3>购物车</h3>
      {message && <span>{message}</span>}
      {lines.map((line, index) => (
        <div className="cart-line" key={index}>
          <b>{line.title}</b>
          <span>{line.quantity}</span>
          <button onClick={() => changeQuantity(index, -1)}>-</button>
          <button onClick={() => changeQuantity(index, 1)}>+</button>
        </div>
      ))}
      <strong>合计 {(totalCent() / 100).toFixed(2)}</strong>
    </div>
  );
}
""",
        issues=[
            dict(lines="32", severity="严重", kind="bug", desc="列表使用 index 作为 key，删除或插入商品后 React 会复用错误节点，数量、焦点或子组件内部状态可能串到另一件商品上。", fix="使用稳定业务主键作为 key，例如 key={line.skuId}，不要用数组下标。"),
            dict(lines="15-20", severity="严重", kind="bug", desc="const next = lines 后直接修改原数组和对象，再把同一个引用传给 setLines，React 可能跳过渲染或污染 props。", fix="使用函数式 setLines，map/filter 返回新数组，并复制被修改的行对象。"),
            dict(lines="16", severity="一般", kind="健壮性", desc="数量没有边界校验，连续点击可能把数量改成负数后再删除，和后端最小购买数、库存约束不一致。", fix="在更新前 clamp 到 0 到可售库存，并把库存校验结果展示给用户。"),
            dict(lines="14-21", severity="建议", kind="可维护", desc="用 index 作为更新定位依赖当前排序，后续如果支持按价格排序或优惠分组，点击按钮可能更新错误行。", fix="changeQuantity 改为接收 skuId，用业务 id 定位要修改的商品。"),
        ],
        summary="总评：这段代码的根因是把数组位置当成业务身份，并且破坏了 React state 不可变约束。合并前必须改成 skuId key、函数式不可变更新和数量边界校验，否则购物车会出现错行更新。",
        points=["指出 index key 在删除插入时错位", "指出直接修改 state 引用", "给出函数式 setState 修法", "关注业务 id 定位", "补充数量边界和库存约束"],
    ),
    dict(
        id="r3",
        order=3,
        lang="TypeScript / React",
        title="订单备注预览并计算含税金额",
        context="商家工作台允许客服录入订单备注，页面会即时预览备注富文本，并根据商品金额和税率展示应收金额。代码容易被认为只是展示逻辑，但它同时处理用户输入和金额计算，风险很高。",
        code="""import React, { useMemo, useState } from "react";

type Props = {
  subtotal: number;
  taxRate: number;
  savedRemark?: string;
};

export function OrderRemarkPreview({ subtotal, taxRate, savedRemark }: Props) {
  const [remark, setRemark] = useState(savedRemark || "");

  const amount = useMemo(() => {
    const tax = subtotal * taxRate;
    const discount = subtotal > 200 ? 0.1 : 0;
    return subtotal + tax - subtotal * discount;
  }, [subtotal]);

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setRemark(e.target.value);
  }

  return (
    <div className="remark-card">
      <textarea value={remark} onChange={handleChange} />
      <div className="preview" dangerouslySetInnerHTML={{ __html: remark }} />
      <p>应收金额：{amount.toFixed(2)} 元</p>
    </div>
  );
}
""",
        issues=[
            dict(lines="25", severity="严重", kind="安全", desc="把客服可输入内容直接交给 dangerouslySetInnerHTML，攻击者可注入脚本，窃取登录态或代替用户操作订单。", fix="默认按文本渲染；如必须支持富文本，使用可信白名单净化库并限制标签和属性。"),
            dict(lines="12-16", severity="严重", kind="bug", desc="金额用 number 浮点计算，0.1 等小数无法精确表示，叠加税率和折扣后可能出现分级、对账差一分。", fix="前后端统一用分为单位的整数或 Decimal，最后一层才格式化展示。"),
            dict(lines="16", severity="一般", kind="bug", desc="useMemo 依赖只写 subtotal，taxRate 变化时金额不会重新计算，活动税率或地区切换会显示旧金额。", fix="依赖数组补齐 taxRate，或移除 useMemo 保持简单可读。"),
            dict(lines="10", severity="建议", kind="可维护", desc="savedRemark 后续如果异步加载或切换订单，useState 初始值不会跟随 props 更新，页面仍显示上一单备注。", fix="用订单 id 触发重置，或把 remark 状态提升到父组件统一管理。"),
        ],
        summary="总评：这段代码同时踩中安全和资金计算两条红线。合并前必须去掉未净化 HTML、把金额改为整数分或 Decimal，并补齐依赖，否则会产生 XSS 和对账差异。",
        points=["识别 dangerouslySetInnerHTML 的 XSS", "指出金额不能用浮点数结算", "发现 useMemo 依赖缺失", "说明 props 初始化 state 的同步问题", "给出白名单净化和整数分方案"],
    ),
    dict(
        id="r4",
        order=4,
        lang="TypeScript / React",
        title="订单提交按钮创建订单并跳转支付页",
        context="移动端订单确认页的提交按钮会创建订单并跳转支付。用户可能在弱网下连续点击，后端也可能返回库存不足、优惠失效等错误，前端必须保证交互状态和错误提示可靠。",
        code="""import React, { useState } from "react";

type SubmitPayload = {
  addressId: string;
  couponId?: string;
};

export function SubmitOrder({ payload }: { payload: SubmitPayload }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setLoading(true);
    const res = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    window.location.href = `/pay?orderId=${data.orderId}`;
    setLoading(false);
  }

  return (
    <div>
      {error && <p className="error">{error}</p>}
      <button disabled={false} onClick={submit}>
        {loading ? "提交中" : "提交订单"}
      </button>
    </div>
  );
}
""",
        issues=[
            dict(lines="27", severity="严重", kind="bug", desc="按钮 disabled 永远是 false，弱网下多次点击会并发创建多个订单，后端没有幂等时会重复占库存或重复支付。", fix="disabled 绑定 loading，并在 submit 开头用 loading 或本地锁阻止重复提交。"),
            dict(lines="14-20", severity="严重", kind="健壮性", desc="没有检查 res.ok，也没有处理接口错误，库存不足或优惠失效时仍可能读取空 orderId 并跳到错误支付页。", fix="根据 HTTP 状态和业务码分支处理，失败时 setError 并停止跳转。"),
            dict(lines="13-21", severity="一般", kind="bug", desc="await 中任何一步抛错都会跳过 setLoading(false)，按钮文案一直停在提交中，用户无法判断是否成功。", fix="使用 try/catch/finally，finally 中复位 loading，catch 中展示可理解错误。"),
            dict(lines="20", severity="建议", kind="安全", desc="orderId 直接拼 URL，虽然通常来自服务端，仍应 encode，避免异常字符破坏跳转地址或埋点解析。", fix="使用 encodeURIComponent(data.orderId)，并校验 orderId 存在再跳转。"),
        ],
        summary="总评：这段代码把创建订单当作普通点击事件处理，没有重复提交保护、错误分支和最终状态复位。合并前必须加前端防抖锁、后端幂等键配合、res.ok 检查和 finally。",
        points=["指出重复提交会重复创建订单", "要求 disabled 绑定 loading", "检查 HTTP 和业务错误", "使用 try/catch/finally 复位状态", "关注 orderId 编码与存在性校验"],
    ),
    dict(
        id="r5",
        order=5,
        lang="Vue",
        title="商品筛选面板根据筛选条件刷新商品数",
        context="Vue 商家后台的筛选面板包含类目、价格、库存、标签等条件，页面希望实时展示命中的商品数。对象会被频繁修改，数据量较大，代码需要避免把派生计算和网络副作用混在一起。",
        code="""<template>
  <aside>
    <p>当前命中 {{ matchedCount }} 个商品</p>
    <button @click="filters.onlyOnSale = !filters.onlyOnSale">切换在售</button>
  </aside>
</template>

<script setup>
import { computed, reactive, watch } from "vue";

const filters = reactive({
  categoryIds: [],
  price: { min: 0, max: 999999 },
  tags: [],
  onlyOnSale: true,
  warehouse: { city: "", zones: [] },
});

let cache = 0;

watch(
  filters,
  async (value) => {
    const res = await fetch("/api/products/count", {
      method: "POST",
      body: JSON.stringify(value),
    });
    cache = (await res.json()).count;
  },
  { deep: true, immediate: true }
);

const matchedCount = computed(async () => {
  const res = await fetch("/api/products/count", {
    method: "POST",
    body: JSON.stringify(filters),
  });
  return (await res.json()).count || cache;
});
</script>
""",
        issues=[
            dict(lines="21-31", severity="严重", kind="性能", desc="对 filters 做 deep watch，会遍历整个对象且每个嵌套字段变化都发请求，标签多或滑动价格时会把接口打爆。", fix="只监听序列化后的必要字段，加入 debounce，并在后端做频控和缓存。"),
            dict(lines="33-39", severity="严重", kind="bug", desc="computed 中发异步请求会返回 Promise，不是稳定的派生值，模板可能显示对象文本且每次依赖变化都产生副作用。", fix="computed 只做同步派生；请求放到 watchEffect 或显式方法中写入 ref。"),
            dict(lines="24-28", severity="一般", kind="健壮性", desc="fetch 没有 Content-Type，也没有错误处理，网关返回 4xx 或 5xx 时 cache 保持旧值，用户看不到失败原因。", fix="补齐请求头、try/catch、错误态，并在失败时展示刷新失败而不是旧数据。"),
            dict(lines="19-29", severity="建议", kind="可维护", desc="cache 是普通变量，不是 ref，更新后不会触发视图刷新，逻辑依赖 computed 再次执行才可能被看到。", fix="把 count、loading、error 都建成 ref，由请求流程统一更新。"),
        ],
        summary="总评：这段代码最大问题是把大对象深监听、异步请求和 computed 混在一起，导致性能不可控且渲染语义错误。合并前应拆成显式查询状态、受控监听字段、去抖和错误处理。",
        points=["指出 deep watch 大对象的遍历和请求成本", "指出 computed 不能承载异步副作用", "要求 debounce 和字段级监听", "发现普通变量不触发响应式更新", "补充错误态和请求头"],
    ),
    dict(
        id="r6",
        order=6,
        lang="Vue",
        title="物流轨迹浮层监听窗口变化并重算高度",
        context="订单详情页打开物流轨迹浮层后，需要在窗口尺寸变化和全局快捷键下调整展示区域。组件会被频繁打开关闭，如果全局监听和定时任务不清理，长时间使用后台会越来越卡。",
        code="""<template>
  <div class="drawer" :style="{ height: height + 'px' }">
    <h3>物流轨迹</h3>
    <button @click="$emit('close')">关闭</button>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

const height = ref(400);

function resize() {
  height.value = window.innerHeight - 120;
}

function onKeydown(e) {
  if (e.key === "Escape") {
    document.querySelector(".drawer button")?.click();
  }
}

onMounted(() => {
  resize();
  window.addEventListener("resize", resize);
  window.addEventListener("keydown", onKeydown);
  setInterval(() => {
    resize();
  }, 1000);
});
</script>
""",
        issues=[
            dict(lines="24-30", severity="严重", kind="性能", desc="组件挂载时注册全局 resize、keydown 和定时器，但卸载时不清理，反复打开浮层会累积监听器和定时任务。", fix="在 onUnmounted 中 removeEventListener，并保存 intervalId 后 clearInterval。"),
            dict(lines="17-21", severity="一般", kind="可维护", desc="keydown 通过 document.querySelector 查找按钮再 click，绕过组件状态和事件流，多个浮层或同名按钮时会关闭错误组件。", fix="用 defineEmits 声明 close 事件，在处理函数里直接 emit('close')。"),
            dict(lines="13-15", severity="一般", kind="健壮性", desc="直接使用 window.innerHeight，服务端渲染或单元测试环境没有 window 时会报错，组件无法渲染。", fix="在浏览器生命周期内访问 window，并对非浏览器环境给默认高度。"),
            dict(lines="27-29", severity="建议", kind="性能", desc="每秒 setInterval 重算高度没有必要，resize 事件已经覆盖尺寸变化，后台标签页会浪费 CPU。", fix="删除轮询；如必须兜底，用 requestAnimationFrame 或可取消的低频任务。"),
        ],
        summary="总评：这段代码最大风险是全局副作用没有生命周期清理，会在后台页面越用越慢。合并前必须补 onUnmounted 清理，改掉 DOM 查询式关闭，并去除不必要轮询。",
        points=["指出全局事件监听未移除", "指出 interval 未清理", "要求 onUnmounted 释放资源", "识别 querySelector 跨组件误操作", "补充 SSR 或测试环境 window 保护"],
    ),
    dict(
        id="r7",
        order=7,
        lang="Go",
        title="批量刷新库存并汇总每个仓库的结果",
        context="库存服务收到一批仓库刷新任务后并发调用外部库存源，再把结果写入 map 供后续返回。代码在小流量下可能正常，但在高并发大促预热时会出现 goroutine 卡死和数据竞争。",
        code="""package inventory

import (
    "fmt"
    "os"
)

type Warehouse struct {
    ID   string
    Path string
}

func Refresh(warehouses []Warehouse) map[string]int {
    result := map[string]int{}
    done := make(chan string)

    for _, wh := range warehouses {
        f, err := os.Open(wh.Path)
        if err != nil {
            continue
        }
        defer f.Close()

        go func() {
            count := loadCount(f)
            result[wh.ID] = count
            done <- wh.ID
        }()
    }

    for i := 0; i < len(warehouses); i++ {
        id := <-done
        fmt.Println("refreshed", id)
    }
    return result
}

func loadCount(f *os.File) int {
    return 100
}
""",
        issues=[
            dict(lines="28-31", severity="严重", kind="并发", desc="等待次数按 warehouses 长度计算，但打开文件失败时没有启动 goroutine，done 接收次数大于发送次数会永久阻塞。", fix="使用 sync.WaitGroup 按实际启动任务等待，或只等待启动成功的数量。"),
            dict(lines="24", severity="严重", kind="并发", desc="多个 goroutine 并发写普通 map，Go 运行时可能直接 fatal，也可能产生数据竞争和错误结果。", fix="用 mutex 保护 map，或让 goroutine 把结果发送到 channel 后单线程汇总。"),
            dict(lines="20", severity="一般", kind="性能", desc="在循环里 defer 关闭文件，会等 Refresh 返回才关闭，仓库很多时同时占用大量文件描述符。", fix="把每次处理封装成函数，在单次任务结束时 close，或显式及时关闭。"),
            dict(lines="22-26", severity="一般", kind="bug", desc="闭包直接引用循环变量 wh 和文件 f，旧版本 Go 或复杂重构后容易读到错误仓库，结果写错 key。", fix="在循环内复制 wh、f 作为 goroutine 参数传入，避免共享循环变量。"),
            dict(lines="14", severity="建议", kind="健壮性", desc="done 是无缓冲 channel，任何提前返回或 panic 都会导致发送端或接收端互相等待，缺少取消机制。", fix="传入 context，错误通过 errgroup 返回，并在取消时停止剩余任务。"),
        ],
        summary="总评：这段代码最大问题是并发控制没有闭环：任务数量、结果收集、共享 map 和资源关闭都不安全。合并前应改成 errgroup 或 WaitGroup 加结果 channel，并用 context 做取消。",
        points=["发现 channel 收发次数不匹配", "指出 map 并发写", "指出循环 defer 资源释放滞后", "识别闭包捕获风险", "给出 WaitGroup、errgroup、结果 channel 修法"],
    ),
    dict(
        id="r8",
        order=8,
        lang="Go",
        title="履约服务调用配送报价接口生成运费",
        context="订单履约服务在创建配送单前调用第三方报价接口，接口延迟会直接影响下单链路。代码要能继承请求超时和取消信号，并且区分网络错误、HTTP 错误和解析错误。",
        code="""package shipping

import (
    "context"
    "encoding/json"
    "net/http"
)

type Quote struct {
    FeeCent int `json:"feeCent"`
}

func GetQuote(ctx context.Context, orderID string) Quote {
    url := "https://carrier.example.com/quote?orderId=" + orderID
    req, _ := http.NewRequest("GET", url, nil)
    resp, _ := http.DefaultClient.Do(req)
    defer resp.Body.Close()

    var quote Quote
    json.NewDecoder(resp.Body).Decode(&quote)
    if quote.FeeCent == 0 {
        quote.FeeCent = 800
    }
    return quote
}
""",
        issues=[
            dict(lines="16", severity="严重", kind="健壮性", desc="使用 http.DefaultClient 且没有超时，报价接口卡住会无限占用请求 goroutine，最终拖垮下单线程池。", fix="构造带 Timeout 的 client，或依赖传入 client，并设置连接、TLS、响应头超时。"),
            dict(lines="15-16", severity="严重", kind="bug", desc="忽略 NewRequest 和 Do 的 error，resp 可能为 nil，下一行 defer resp.Body.Close 会直接 panic。", fix="逐层返回 Quote, error，任何错误都带上下文信息向上抛出。"),
            dict(lines="15", severity="一般", kind="健壮性", desc="传入的 ctx 没有传给请求，用户取消下单或上游超时后，外部报价调用仍继续占用资源。", fix="使用 http.NewRequestWithContext(ctx, ...) 让取消信号向下传递。"),
            dict(lines="14", severity="一般", kind="安全", desc="orderID 直接拼接 URL，没有 QueryEscape，特殊字符会改变查询参数结构，日志和签名也可能不一致。", fix="用 url.Values 或 url.QueryEscape 构造查询参数。"),
            dict(lines="20-23", severity="建议", kind="bug", desc="JSON 解析错误和真实 0 元运费都被静默改成 800 分，掩盖上游故障并产生错误收费。", fix="检查 Decode error 和 HTTP 状态，默认值只能在明确的业务降级分支使用。"),
        ],
        summary="总评：这段代码把远程调用写成了本地函数，没有超时、错误和取消传播。合并前必须返回 error、设置客户端超时、使用 NewRequestWithContext，并明确降级策略和监控指标。",
        points=["指出 HTTP 客户端无超时", "指出忽略 error 会 panic", "要求 context 继续向下传", "检查状态码和 JSON 错误", "说明默认运费会掩盖故障"],
    ),
    dict(
        id="r9",
        order=9,
        lang="Java",
        title="订单导出任务使用线程池异步生成文件",
        context="商家后台支持批量导出订单，控制器提交异步任务后立即返回任务号。高峰期大量商家同时导出，如果线程池边界和拒绝策略不合理，会把接口机器内存打满。",
        code="""import java.util.List;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

public class OrderExportService {
    private final ThreadPoolExecutor executor = new ThreadPoolExecutor(
            8,
            64,
            60,
            TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(),
            new ThreadPoolExecutor.DiscardPolicy());

    public String submit(long merchantId, List<Long> orderIds) {
        String jobId = "job-" + System.currentTimeMillis();
        executor.execute(() -> {
            byte[] file = buildExcel(orderIds);
            upload(jobId, file);
            markSuccess(jobId);
        });
        return jobId;
    }

    private byte[] buildExcel(List<Long> orderIds) {
        return new byte[orderIds.size() * 1024];
    }

    private void upload(String jobId, byte[] file) {
    }

    private void markSuccess(String jobId) {
    }
}
""",
        issues=[
            dict(lines="8-13", severity="严重", kind="性能", desc="LinkedBlockingQueue 未设置容量，任务堆积时会无限占用堆内存，maxPoolSize 也基本不会生效。", fix="使用有界队列，按内存和平均文件大小估算容量，并配合监控队列长度。"),
            dict(lines="13", severity="严重", kind="健壮性", desc="DiscardPolicy 会静默丢弃任务，接口已经返回 jobId，用户之后只会看到任务永远不完成。", fix="使用自定义拒绝策略，落失败状态并向调用方返回可重试错误。"),
            dict(lines="17-20", severity="一般", kind="bug", desc="任务内部异常没有捕获，buildExcel 或 upload 失败时不会 markFailure，任务状态卡在处理中。", fix="在线程任务内 try/catch/finally，失败时记录原因并更新任务状态。"),
            dict(lines="15", severity="建议", kind="可维护", desc="jobId 使用当前毫秒时间，批量并发提交时可能重复，覆盖任务状态或上传文件。", fix="使用数据库自增、UUID 或雪花 ID，并建立唯一约束。"),
            dict(lines="17", severity="建议", kind="性能", desc="一次性把所有订单构造成 byte[]，大导出会制造大对象和长时间 GC。", fix="分页读取订单并流式写文件，限制单任务最大订单数。"),
        ],
        summary="总评：这段代码缺少异步任务系统最基本的容量边界和失败闭环。合并前必须改有界队列、可观测拒绝策略、任务失败状态和流式导出，否则高峰期会丢任务或 OOM。",
        points=["指出无界队列导致内存风险", "指出 DiscardPolicy 静默丢任务", "要求任务异常落失败状态", "关注 jobId 唯一性", "提出流式导出和容量估算"],
    ),
    dict(
        id="r10",
        order=10,
        lang="Java",
        title="售后服务取消订单并释放库存",
        context="售后系统允许客服取消未发货订单，代码需要在同一事务里更新订单、释放库存、记录流水。实现使用 Spring 注解事务，看起来完整，但代理调用和异常处理会让事务失效。",
        code="""import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CancelOrderService {
    private final OrderRepository orderRepository;
    private final StockRepository stockRepository;

    public CancelOrderService(OrderRepository orderRepository, StockRepository stockRepository) {
        this.orderRepository = orderRepository;
        this.stockRepository = stockRepository;
    }

    public boolean cancel(Long orderId) {
        try {
            doCancel(orderId);
            return true;
        } catch (Exception e) {
            System.out.println("cancel failed " + e.getMessage());
            return false;
        }
    }

    @Transactional
    public void doCancel(Long orderId) {
        Order order = orderRepository.find(orderId);
        order.setStatus("CANCELLED");
        orderRepository.save(order);
        stockRepository.release(order.getSkuId(), order.getQuantity());
        orderRepository.insertLog(orderId, "cancelled");
    }
}
""",
        issues=[
            dict(lines="15", severity="严重", kind="bug", desc="同类内部 self-invocation 调用 doCancel，不经过 Spring 代理，@Transactional 不生效，订单和库存可能部分成功。", fix="把事务方法放到另一个 Bean，或从代理对象调用，确保事务拦截器生效。"),
            dict(lines="16-20", severity="严重", kind="健壮性", desc="catch 吞掉异常并返回 false，如果外层还有事务会被认为正常结束，不会按异常回滚。", fix="记录日志后继续抛出业务异常，或显式设置 rollbackOnly 并返回明确错误码。"),
            dict(lines="25-29", severity="一般", kind="并发", desc="取消前没有校验订单当前状态和版本，两个客服并发取消可能重复释放库存。", fix="使用条件更新 where status='PAID' and version=?，成功后再释放库存。"),
            dict(lines="28", severity="一般", kind="健壮性", desc="释放库存和订单日志缺少幂等键，重试或并发时可能重复增加库存。", fix="以 orderId 和 skuId 建立释放流水唯一约束，重复调用直接返回已处理。"),
        ],
        summary="总评：这段代码看似有事务，实际因为自调用和吞异常破坏了事务边界。合并前必须让事务代理生效，异常可回滚，并补状态条件更新和库存释放幂等。",
        points=["指出 @Transactional 自调用失效", "指出 catch 吞异常影响回滚", "要求状态机条件更新", "补充库存释放幂等", "能说明订单和库存一致性风险"],
    ),
    dict(
        id="r11",
        order=11,
        lang="Java",
        title="网关过滤器记录租户上下文和格式化请求时间",
        context="多租户后台网关会从请求头读取商家租户号，写入 ThreadLocal 供下游日志和权限校验使用，同时格式化请求时间。网关线程会复用，线程安全和上下文清理必须非常严格。",
        code="""import java.text.SimpleDateFormat;
import java.util.Date;

public class TenantFilter {
    private static final ThreadLocal<Long> TENANT = new ThreadLocal<>();
    private static final SimpleDateFormat FORMAT = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    public void doFilter(Request request, Response response, FilterChain chain) throws Exception {
        String tenantHeader = request.getHeader("X-Tenant-Id");
        if (tenantHeader != null) {
            TENANT.set(Long.parseLong(tenantHeader));
        }
        String start = FORMAT.format(new Date());
        response.setHeader("X-Start-Time", start);
        chain.doFilter(request, response);
        audit(TENANT.get(), request.getPath());
    }

    public static Long currentTenant() {
        return TENANT.get();
    }

    private void audit(Long tenantId, String path) {
        System.out.println(tenantId + " " + path);
    }
}
""",
        issues=[
            dict(lines="10-17", severity="严重", kind="安全", desc="ThreadLocal 没有在 finally 中 remove，线程复用后下一个请求可能继承上一个租户，造成越权读写。", fix="用 try/finally 包住 chain.doFilter，finally 中 TENANT.remove()。"),
            dict(lines="6", severity="严重", kind="并发", desc="SimpleDateFormat 是可变且非线程安全的静态对象，并发格式化可能输出错误日期甚至抛异常。", fix="改用线程安全的 DateTimeFormatter，或每次创建局部格式化器。"),
            dict(lines="10-12", severity="一般", kind="健壮性", desc="租户头为空或非法时没有明确拒绝，旧 ThreadLocal 残留会让匿名请求带上旧租户。", fix="缺失或解析失败直接返回 401/400，并确保清理上下文。"),
            dict(lines="15-16", severity="一般", kind="bug", desc="chain.doFilter 抛异常时 audit 不执行且上下文不清理，错误请求更容易留下污染。", fix="try/catch/finally 分别负责审计失败、设置响应和清理资源。"),
        ],
        summary="总评：这段代码风险集中在线程复用场景，ThreadLocal 泄漏会变成租户越权，SimpleDateFormat 共享会造成并发错乱。合并前必须 finally 清理并替换线程安全时间格式化。",
        points=["指出 ThreadLocal 未清理", "说明线程复用导致租户串号", "指出 SimpleDateFormat 非线程安全", "要求非法租户头拒绝", "使用 try/finally 包住过滤链"],
    ),
    dict(
        id="r12",
        order=12,
        lang="Java",
        title="支付回调更新订单、缓存和分布式锁",
        context="支付渠道回调到订单系统后，服务需要防止并发处理同一订单，更新数据库状态，并清理订单缓存。代码包含缓存、分布式锁和回调处理，是面试中常见的一致性评审题。",
        code="""public class PayCallbackService {
    private final RedisClient redis;
    private final OrderRepository orderRepository;

    public void onPaid(PayNotify notify) {
        String lockKey = "pay:lock:" + notify.getOrderId();
        boolean locked = redis.setNx(lockKey, "1");
        if (!locked) {
            return;
        }

        Order order = orderRepository.find(notify.getOrderId());
        if (order == null) {
            redis.del(lockKey);
            return;
        }
        order.setPaidAmount(notify.getAmountCent());
        order.setStatus("PAID");
        redis.del("order:" + order.getId());
        orderRepository.save(order);
        sendPaidMessage(order.getId());
        redis.del(lockKey);
    }

    private void sendPaidMessage(Long orderId) {
    }
}
""",
        issues=[
            dict(lines="7", severity="严重", kind="并发", desc="分布式锁只 setNx 不设置过期时间，进程在保存前崩溃会留下永久锁，之后支付回调全部被跳过。", fix="使用 set key value nx px 原子命令设置过期，过期时间按最长处理耗时估算。"),
            dict(lines="14-22", severity="严重", kind="并发", desc="释放锁时不校验持有者，锁过期后别的线程拿到新锁，旧线程仍可能 del 掉别人的锁。", fix="锁 value 使用随机 token，Lua 脚本比较 token 相等才删除。"),
            dict(lines="12-20", severity="严重", kind="bug", desc="回调没有幂等判断，支付渠道重试或并发通知会重复发送已支付消息，履约可能重复发货。", fix="用支付流水号或订单状态做唯一幂等，只有待支付到已支付的条件更新成功才发消息。"),
            dict(lines="18-19", severity="一般", kind="健壮性", desc="先删除缓存再保存数据库，如果保存失败，读请求会回源读到旧状态并重新写入旧缓存。", fix="先在事务内更新数据库和流水，再延迟双删或基于 binlog 失效缓存。"),
            dict(lines="20", severity="一般", kind="健壮性", desc="消息发送不在可靠事务之后，数据库成功但发消息失败时，履约系统收不到状态变化。", fix="使用本地消息表或事务消息，后台重试投递并记录投递状态。"),
        ],
        summary="总评：这段代码把支付回调的锁、幂等、缓存和消息都写成了最佳努力，任何一步失败都会放大成重复履约或状态不一致。合并前必须补锁过期和 token、条件更新幂等、可靠消息和缓存失效策略。",
        points=["指出分布式锁无过期", "指出释放锁不校验持有者", "指出支付回调无幂等", "分析缓存与数据库更新顺序", "提出可靠消息或本地消息表"],
    ),
    dict(
        id="r13",
        order=13,
        lang="Python",
        title="合并默认活动配置并返回给前端",
        context="促销后台会把默认活动配置和商家自定义配置合并后返回给前端预览。函数被多个请求复用，看起来只是字典处理，但默认参数和浅拷贝会让不同商家的配置互相污染。",
        code="""DEFAULT_RULES = {
    "discounts": [],
    "limits": {"max_items": 99},
}

def build_campaign_config(merchant_id, custom={}, tags=[]):
    custom["merchant_id"] = merchant_id
    tags.append("preview")

    config = DEFAULT_RULES.copy()
    config["discounts"].append({"type": "full_reduce", "amount": 10})
    config["tags"] = tags

    if custom.get("max_items"):
        config["limits"]["max_items"] = custom["max_items"]

    for key, value in custom.items():
        config[key] = value

    return config

def preview():
    a = build_campaign_config(1001, {"max_items": 5})
    b = build_campaign_config(1002)
    return a, b
""",
        issues=[
            dict(lines="6", severity="严重", kind="bug", desc="custom 和 tags 使用可变默认参数，函数多次调用会共享同一个 dict/list，商家之间会串配置。", fix="默认值改为 None，函数内创建新 dict 和 list。"),
            dict(lines="10", severity="严重", kind="bug", desc="DEFAULT_RULES.copy() 是浅拷贝，discounts 和 limits 仍共享嵌套对象，一次 append 会污染全局默认配置。", fix="使用 copy.deepcopy，或显式构造全新的嵌套结构。"),
            dict(lines="11", severity="一般", kind="可维护", desc="每次预览都会向默认折扣列表追加活动，调用次数越多折扣越多，问题很隐蔽。", fix="不要修改默认模板，在局部新列表中追加本次需要的折扣。"),
            dict(lines="7", severity="一般", kind="bug", desc="直接修改传入 custom，会让调用方持有的原始配置被额外加入 merchant_id，产生副作用。", fix="先 custom = dict(custom or {})，后续只修改本地副本。"),
            dict(lines="14-15", severity="建议", kind="健壮性", desc="if custom.get('max_items') 会忽略 0 这类合法值，业务想表达不允许购买时会被跳过。", fix="用 'max_items' in custom 判断字段是否存在，再校验范围。"),
        ],
        summary="总评：这段代码最大风险是共享可变对象，导致不同请求、不同商家、默认模板之间互相污染。合并前必须去掉可变默认参数，深拷贝或重建嵌套结构，并避免修改入参。",
        points=["指出可变默认参数", "指出浅拷贝嵌套对象共享", "说明全局默认配置污染", "要求不修改入参", "补充存在性判断和范围校验"],
    ),
    dict(
        id="r14",
        order=14,
        lang="Python",
        title="订单查询接口同步拉取风控并拼接 SQL",
        context="客服系统提供订单查询接口，支持按手机号筛选，并展示风控标签。接口处在高频查询链路，既要防注入，也要避免在请求线程里同步等待慢外部接口拖垮服务。",
        code="""import requests

def list_orders(request, db):
    phone = request.args.get("phone", "")
    page = int(request.args.get("page", "1"))
    size = int(request.args.get("size", "20"))

    risk = requests.get(
        "https://risk.example.com/check",
        params={"phone": phone},
    ).json()

    sql = "select * from orders where phone = '%s' order by created_at desc limit %s offset %s" % (
        phone,
        size,
        (page - 1) * size,
    )
    rows = db.execute(sql).fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "amount": row["amount"],
            "risk": risk.get("level"),
        })
    return {"items": result}
""",
        issues=[
            dict(lines="13-17", severity="严重", kind="安全", desc="直接用字符串拼接 phone、limit、offset，攻击者可构造 SQL 注入读取或修改订单数据。", fix="使用参数化查询，page 和 size 转整数后做范围限制。"),
            dict(lines="8-11", severity="严重", kind="性能", desc="请求线程同步调用外部风控且没有 timeout，风控慢或挂掉会拖慢整个订单查询接口。", fix="设置短超时和熔断；非核心标签可异步预计算或降级为空。"),
            dict(lines="8-11", severity="一般", kind="健壮性", desc="没有检查 HTTP 状态和 JSON 解析错误，返回 HTML 错误页时会抛异常导致接口 500。", fix="检查 status_code，捕获 requests 和 JSON 异常，记录指标后返回降级结果。"),
            dict(lines="5-6", severity="一般", kind="健壮性", desc="page 和 size 没有上下限，负数或超大 size 会制造异常 SQL 或一次拉取过多数据。", fix="限制 page>=1，size 在 1 到 100 之间，并对非法参数返回 400。"),
            dict(lines="13", severity="建议", kind="性能", desc="select * 会读取不需要的列，订单表字段多时增加 IO、网络传输和对象构造成本。", fix="只选择列表页需要的 id、amount、created_at 等字段。"),
        ],
        summary="总评：这段代码把用户输入直接拼到 SQL，同时把慢外部调用放在查询链路核心路径。合并前必须参数化查询、限制分页、设置超时和降级，否则会有注入和级联超时风险。",
        points=["指出 SQL 注入", "要求参数化查询", "指出同步慢接口无超时", "要求外部调用降级和熔断", "补充分页边界和 select 列裁剪"],
    ),
    dict(
        id="r15",
        order=15,
        lang="SQL",
        title="订单列表页按商家查询商品名称和物流状态",
        context="商家工作台的订单列表需要展示订单、首个商品名和最近物流状态。代码把主查询结果再逐行查明细和物流，并使用大 OFFSET 翻页，在订单量达到百万级后会明显变慢。",
        code="""-- Python-like pseudo code used by the API layer
def list_order_page(db, merchant_id, page, size):
    offset = (page - 1) * size
    orders = db.query(
        "select id, order_no, buyer_id, amount_cent, created_at "
        "from orders where merchant_id = ? "
        "order by created_at desc limit ? offset ?",
        [merchant_id, size, offset],
    )

    items = []
    for order in orders:
        sku = db.query_one(
            "select sku_name from order_items where order_id = ? limit 1",
            [order["id"]],
        )
        track = db.query_one(
            "select status from logistics_track where order_id = ? order by event_time desc limit 1",
            [order["id"]],
        )
        items.append({
            "orderNo": order["order_no"],
            "skuName": sku["sku_name"] if sku else "",
            "trackStatus": track["status"] if track else "",
        })
    return items
""",
        issues=[
            dict(lines="12-20", severity="严重", kind="性能", desc="循环里按每个订单查询商品和物流，页面 50 条就至少 101 次查询，典型 N+1 会把数据库连接池打满。", fix="先批量取 order_id，再用 IN 查询明细和轨迹，或用窗口函数取每单最新轨迹。"),
            dict(lines="7", severity="严重", kind="性能", desc="大页码 OFFSET 需要扫描并丢弃前面大量行，百万订单翻到后面会越来越慢。", fix="改用基于 created_at 和 id 的游标翻页，并建立匹配排序的复合索引。"),
            dict(lines="5-7", severity="一般", kind="性能", desc="如果没有 merchant_id、created_at、id 复合索引，按商家排序分页会 filesort 或回表扫描。", fix="建立 (merchant_id, created_at desc, id desc) 索引，并让查询带上 id 作为稳定排序。"),
            dict(lines="14", severity="一般", kind="bug", desc="首个商品没有 order by，数据库可返回任意一行，页面展示的商品名不稳定。", fix="明确按 item_no 或 created_at 排序，或者在写入订单时冗余首件商品名。"),
            dict(lines="21-26", severity="建议", kind="可维护", desc="API 层拼装多个来源但没有降级标记，物流查询失败时调用方无法区分空状态和查询失败。", fix="返回 trackStatusSource 或 warning，并对批量物流查询设置独立错误处理。"),
        ],
        summary="总评：这段代码最大风险是查询次数随页大小线性放大，并且 OFFSET 随页码放大扫描成本。合并前必须批量查询或 join 聚合，改游标分页，并补齐覆盖排序索引。",
        points=["识别 N+1 查询", "指出大 OFFSET 深分页问题", "要求复合索引匹配 where 和 order by", "发现无 order by 的不确定性", "给出批量 IN 或窗口函数方案"],
    ),
    dict(
        id="r16",
        order=16,
        lang="SQL",
        title="订单表建表和查询语句评审",
        context="新订单中心设计了一张订单表，并提供客服按订单号、手机号、状态查询的 SQL。表结构和查询在测试数据下能跑，但字段类型、索引、隐式转换和 OR 条件会影响生产性能。",
        code="""create table orders (
  id varchar(64) primary key,
  order_no varchar(64),
  merchant_id varchar(64),
  buyer_phone int,
  amount double,
  status varchar(32),
  created_at varchar(32),
  updated_at varchar(32)
);

create index idx_status on orders(status);

select *
from orders
where status = 'PAID'
  and (order_no = 'O20261001001' or buyer_phone = '13800000000')
  and created_at >= '2026-10-01'
order by created_at desc
limit 20;
""",
        issues=[
            dict(lines="5", severity="严重", kind="bug", desc="手机号用 int 会丢失前导 0，部分数据库还会溢出，查询时字符串比较也会触发隐式转换。", fix="手机号使用 varchar(32)，只做格式校验，不参与数值运算。"),
            dict(lines="6", severity="严重", kind="bug", desc="金额用 double 存储会产生浮点误差，订单支付和退款对账可能出现分级差异。", fix="金额用 bigint amount_cent 存分，或 decimal(18,2) 并统一舍入规则。"),
            dict(lines="8-9", severity="一般", kind="性能", desc="时间字段用 varchar，范围查询和排序依赖字符串格式，无法利用时间类型统计信息。", fix="使用 datetime/timestamp，并统一时区和写入精度。"),
            dict(lines="12-18", severity="一般", kind="性能", desc="只有 status 单列索引，where 同时按状态和时间排序，仍可能扫描大量已支付订单再排序。", fix="为常用列表建立 (status, created_at desc, id) 或按商家维度的复合索引。"),
            dict(lines="13", severity="建议", kind="性能", desc="select * 会读取无关列，后续表变宽后增加 IO，也让覆盖索引失去价值。", fix="只选择页面需要的 id、order_no、amount_cent、created_at 等列。"),
            dict(lines="16", severity="建议", kind="性能", desc="order_no 和 buyer_phone 用 OR 组合，优化器可能无法同时高效利用两个索引，数据大时退化扫描。", fix="拆成两个查询 union all，或按用户选择的搜索类型走对应索引。"),
        ],
        summary="总评：这段 SQL 的核心问题是字段类型和索引设计没有贴合订单业务：手机号、金额、时间类型都会影响正确性，查询又包含 SELECT *、OR 和缺复合索引。合并前必须先修模型再谈优化。",
        points=["指出手机号不应使用 int", "指出金额不能用 double", "指出时间字段类型错误", "分析复合索引缺失", "识别 SELECT * 和 OR 的索引问题"],
    ),
]
