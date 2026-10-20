SECTIONS = [
    dict(
        id="dev-api", course="dev", order=1,
        title="调用大模型 API", summary="把消息、流式、重试和配额做成可靠调用层",
        md="""### 一句话与核心概念
调用大模型 API 不是发一个字符串等答案，而是把消息、工具、模型参数、超时、重试、限流、审计组合成一层稳定的远程推理客户端。面试里要能说清：消息结构决定模型看到什么，流式 SSE 决定用户什么时候看到，错误分类决定能不能重试，配额与限流决定系统会不会被模型服务反压打垮，多供应商兼容决定业务是否被单一接口绑定。

核心对象通常包括 message、request、response、usage、error、retry policy。message 有 role 和 content，role 用来区分系统规则、用户输入、助手历史、工具结果。request 还会带 model、temperature、max_tokens、stop、tools、response_format、stream 等参数。response 不只看文本，还要看 finish_reason、tool_calls、usage、request_id。生产系统要把这些字段保存到调用日志里，但不能保存敏感原文。

### 原理：消息序列、SSE 与退避为什么这样工作
聊天模型把一段有序消息序列序列化成上下文，下一 token 的概率可抽象为 P(x_t | system, history, user, tools, x_<t)。system 更像高优先级约束，user 是当前任务，assistant 是历史输出，tool 是外部观察。顺序错、role 混用、工具结果伪装成用户输入，都会让模型误判状态。

流式输出常用 SSE。服务端把一次推理切成多个 event，每个 event 携带 delta：可能是文本片段，也可能是工具调用参数片段。客户端的状态机一般是：连接建立 → 逐行读取 data → 解析 JSON → 合并 delta → 遇到 DONE 或 finish_reason 结束 → 做完整校验。流式降低首字等待时间，但不会降低总计算成本，且失败时可能只拿到半截结果。

重试的原理是把瞬时失败和永久失败分开。401、403、参数错误一般是永久失败；网络抖动、连接重置、部分 5xx、429 可能是瞬时失败。指数退避用 delay = min(cap, base * 2^attempt) + jitter，jitter 避免大量客户端同时重试造成二次洪峰。复杂度上，单次调用主要消耗由输入 token 和输出 token 决定；客户端状态机是 O(n)，n 是收到的事件数或字节数。

### 工程实现要点
建议把模型调用封装成独立 client，而不是在业务代码里到处直接调 SDK。接口至少包含：统一请求结构、供应商适配器、重试策略、超时策略、限流器、错误分类、日志脱敏、指标上报。

```python
import random, time

class RetryableError(Exception): pass
class FatalError(Exception): pass

def backoff_sleep(attempt, base=0.5, cap=8.0):
    delay = min(cap, base * (2 ** attempt))
    time.sleep(delay + random.random() * delay * 0.2)

def call_with_retry(send, request, max_attempts=4):
    last = None
    for attempt in range(max_attempts):
        try:
            return send(request, timeout=(5, 60))
        except FatalError:
            raise
        except RetryableError as exc:
            last = exc
            if attempt == max_attempts - 1:
                break
            backoff_sleep(attempt)
    raise last
```

超时要分三层：连接超时、读取超时、业务总超时。连接超时防网络卡住；读取超时防长时间无事件；业务总超时防一次请求占住 worker。限流要同时看请求数和 token 数。经验上，请求并发上限只控制连接数量，不能控制长输出消耗，最好再维护每分钟 token 预算或队列。

多供应商兼容不要只做 URL 替换。差异通常出现在模型名、工具调用格式、JSON 输出能力、错误码、usage 字段、流式 chunk、最大上下文、限流口径。适配层要输出内部统一事件，例如 text_delta、tool_call_delta、completed、failed。业务层只消费统一事件。

### 生产落地：方案、踩坑与排查
问题一：线上偶发超时。现象是接口 p95 升高，应用线程堆积，用户刷新后又发起新请求。原因可能是没有业务总超时，或者读取超时太长。定位看 request_id、首字时间、总耗时、输入输出 token、连接池等待时间。解决是设置总 deadline，流式请求做心跳检测，后台任务用队列隔离，超时后写入可重试状态。

问题二：429 突然增多。现象是批量任务大面积失败，重试后更严重。原因通常是并发过高、token 预算估算不足、所有 worker 同时退避结束。定位看每分钟请求数、每分钟 token、重试次数、队列长度和供应商返回的限流维度。解决是令牌桶、指数退避加 jitter、按租户分配预算，必要时降级到小模型或延迟执行。

问题三：流式 JSON 解析失败。现象是前端已经展示了一半 JSON，最后校验不通过。原因是把 delta 当完整对象解析，或断线后没有区分半成品和最终结果。定位看原始 SSE、合并后的 buffer、finish_reason。解决是流式只展示自然语言，结构化结果必须等 DONE 后整体解析；工具调用参数要按 id 聚合后再校验。

问题四：切供应商后效果或工具调用坏了。现象是同样提示词在新模型上不按 schema 输出。原因是兼容接口只覆盖传输，不覆盖行为差异。定位看请求参数映射、工具 schema、采样参数、拒答和截断比例。解决是为每个供应商建立回归集，适配层做能力声明，业务按 capability 选择模型而不是按字符串硬编码。

### 取舍与对比
| 方案 | 优点 | 风险 | 适用场景 |
|---|---|---|---|
| 非流式 | 实现简单，结果完整后再校验 | 首字慢，长回答体验差 | 后台批处理、结构化抽取 |
| 流式 SSE | 首字快，可边生成边展示 | 状态机复杂，半截结果多 | 聊天、代码解释、长文生成 |
| SDK 直连 | 上手快，字段更新及时 | 业务到处耦合供应商 | 原型、小工具 |
| 自建适配层 | 可观测、可切换、可治理 | 初期代码量更多 | 多业务、多模型、生产系统 |
| 激进重试 | 短时成功率更高 | 放大限流和成本 | 小流量、幂等任务 |
| 保守重试 | 成本可控，故障清晰 | 瞬时失败暴露给上游 | 高并发、强 SLA 系统 |

### 结合项目怎么讲
可以按“背景 → 问题 → 方案 → 数据/效果 → 反思”讲。背景：给测试平台做失败日志摘要和用例生成，需要接入多个大模型。问题：直接在业务里调 SDK 后，遇到超时、429、流式中断、JSON 不合法，很难定位责任。方案：我抽了一层 LLM Gateway，统一 messages、response、error、usage；实现 SSE 聚合、错误分类、指数退避、令牌桶限流；日志只记录 request_id、耗时、token、模型和脱敏摘要；每个供应商有独立适配器和回归样例。数据/效果：经验上超时和限流问题能从日志里快速定位，批量任务失败可以按错误类型重放，切模型时不改业务代码。反思：兼容层不能承诺所有模型行为一致，必须用能力矩阵和回归集约束；结构化输出不要相信首个返回，要完整校验后进入业务。""",
        points=[
            "消息 role、顺序和工具结果会直接影响模型状态理解。",
            "流式 SSE 需要按 delta 聚合，最终结果仍要完整校验。",
            "重试必须区分永久错误和瞬时错误，并加退避与抖动。",
            "限流要同时控制请求数、并发数和 token 预算。",
            "多供应商兼容要抽象能力和事件，不只是替换 URL。",
        ],
        drill=[
            dict(level="基础", q="大模型 API 调用里 messages 的 role 怎么理解？", a="system 放全局规则和安全边界，user 放用户当前输入，assistant 放模型历史输出，tool 放外部工具的执行结果。模型会按消息顺序理解上下文，所以不能把工具观察伪装成用户新需求。生产里还要保存请求摘要、模型名、usage 和 request_id，便于追踪。敏感内容要脱敏或不落盘。"),
            dict(level="原理", q="流式 SSE 为什么不能直接当完整 JSON 使用？", a="SSE 推送的是增量 delta，一次事件可能只有几个字符，也可能只是工具调用参数的一部分。中途断线或被截断时，客户端拿到的是半成品。正确做法是按事件 id 或工具调用 id 聚合 buffer，遇到结束信号后再整体解析和校验。展示层可以边显示文本，但业务入库必须等最终完成。"),
            dict(level="实现", q="你会怎样封装一个 LLM Client？", a="我会定义内部统一请求和统一事件，业务只传 messages、模型能力需求、超时和预算。Client 内部包含供应商适配器、错误分类、重试退避、限流、日志脱敏和指标上报。非流式返回完整 response，流式返回 text_delta、tool_call_delta、completed、failed 等事件。这样切模型或接新供应商时只改适配层。"),
            dict(level="落地", q="哪些错误可以重试，哪些不能重试？", a="认证失败、权限不足、参数 schema 错误、上下文超长通常不能重试，因为再次发送大概率仍失败。网络抖动、连接重置、部分服务端 5xx、429 在满足幂等和预算的前提下可以重试。重试要有最大次数、总耗时上限和指数退避加抖动。对可能产生副作用的工具调用结果，不能简单重放整个 Agent 轮次。"),
            dict(level="排查", q="线上 429 暴涨你怎么定位？", a="先看是请求数限流、token 限流还是账户配额耗尽。指标上看每分钟请求、每分钟输入输出 token、并发数、重试次数和队列长度。日志上按模型、租户、任务类型聚合 request_id 和错误体。解决上先降并发和停激进重试，再加令牌桶、队列削峰、预算隔离，必要时做模型降级。"),
            dict(level="取舍", q="什么时候用流式，什么时候不用？", a="聊天、解释、长文本生成适合流式，因为用户关心首字延迟。结构化抽取、后台批处理、需要强校验的任务更适合非流式，拿到完整结果后再解析。也可以内部流式接收但不对业务暴露半成品，只用于心跳和进度。选择标准是交互体验、状态机复杂度、校验要求和失败恢复成本。"),
            dict(level="设计", q="如果要同时支持三个模型供应商，你会怎么设计？", a="我会先定义内部 capability，例如是否支持工具调用、JSON schema、视觉输入、最大上下文和流式工具参数。每个供应商实现 adapter，把原始请求和响应映射为内部格式。路由层按任务、成本、延迟、配额和能力选择模型。再配回归集、影子调用和可观测指标，避免只在接口层兼容、实际行为却不可控。"),
        ],
        choice=[
            dict(q="关于 messages role，下列说法正确的是？", options=["tool 结果可以随意拼到 user 里", "system 适合放长期规则和边界", "assistant 历史完全不影响后续输出", "role 只影响日志，不影响模型理解"], answer=[1], explain="system 承载长期规则和边界。tool 结果应保持独立 role，assistant 历史会影响上下文，role 对模型理解有实际影响。"),
            dict(q="哪些情况通常可以考虑重试？", options=["参数字段名写错", "认证密钥无效", "短暂网络连接重置", "429 且有退避和预算控制"], answer=[2, 3], explain="网络抖动和受控的 429 可重试。参数错误和认证失败属于永久错误，重试只会放大负载。"),
            dict(q="流式 SSE 的正确处理方式是？", options=["每个 delta 都立刻当 JSON 解析入库", "只要收到第一个 token 就算请求成功", "聚合增量并在结束后做完整校验", "流式一定比非流式成本低"], answer=[2], explain="delta 是片段，必须聚合后校验。首 token 不等于成功，流式改善体验但不必然降低成本。"),
            dict(q="多供应商兼容最容易被低估的是什么？", options=["域名配置", "接口行为和能力差异", "HTTP 方法", "是否能打印日志"], answer=[1], explain="真正困难在工具调用、JSON 输出、错误码、usage 和上下文限制等行为差异，不是简单域名替换。"),
        ],
        short=[
            dict(q="设计一个生产可用的大模型调用层，需要哪些模块？", points=["统一请求/响应和事件抽象", "错误分类、重试退避、超时", "限流、预算、队列削峰", "日志脱敏、指标和 request_id", "供应商能力矩阵与适配器"], reference="我会把模型调用从业务里抽成独立客户端或网关。入口接收统一 messages、模型能力需求、超时和预算；内部按能力矩阵选择供应商适配器。调用路径上要有连接超时、读取超时、业务总超时，错误分类后只对网络抖动、429、部分 5xx 做指数退避重试。高并发下用令牌桶和队列控制请求数与 token 数。所有响应都记录 request_id、耗时、usage、finish_reason 和脱敏摘要，便于排查。流式场景输出统一事件，业务只在 completed 后入库。"),
            dict(q="说明流式输出的状态机和常见失败处理。", points=["建立连接并逐行读取 SSE", "解析 data 并合并 text/tool delta", "区分半成品和 completed", "处理断线、超时和截断", "最终做 schema 或业务校验"], reference="流式客户端先建立连接，然后按 SSE 行读取 data 字段，把每个 JSON delta 解析成内部事件。文本 delta 可以追加到展示 buffer，工具调用参数要按 tool_call_id 聚合。只有收到结束信号或 finish_reason，才把结果标记为 completed。若中途断线、读取超时或上下文截断，状态应是 failed 或 partial，不能把半成品写入业务表。对 JSON 或工具参数，必须在完整聚合后做 schema 校验，失败时走修复、重试或人工处理。"),
            dict(q="为什么多模型兼容要做能力矩阵，而不是只封装 base_url？", points=["模型能力不等价", "响应字段和错误码有差异", "结构化输出和工具调用差异明显", "路由需要成本、延迟、配额信息", "回归集能防行为漂移"], reference="base_url 只能解决传输入口问题，不能保证行为一致。不同模型在上下文长度、工具调用格式、JSON schema 约束、流式 chunk、usage 返回和错误码上都可能不同。生产里应定义能力矩阵，例如支持工具调用、支持严格 JSON、最大上下文、是否支持图像、限流口径等。路由层按任务要求、成本、延迟和配额选择模型。每次新增或切换供应商，都用固定回归集验证输出格式、失败分类和关键业务样例。"),
        ],
        labs=["lab-retry-backoff", "lab-sse-parser"],
        related=["llm-serving", "dev-function-calling", "dev-observability", "arch-model-routing"],
    ),

    dict(
        id="dev-prompt", course="dev", order=2,
        title="提示词工程与结构化输出", summary="把提示词当可测试、可版本化的接口契约",
        md="""### 一句话与核心概念
提示词工程不是写一段“请认真回答”，而是为模型定义任务接口：输入是什么、输出是什么、禁止什么、遇到异常怎么办、如何验证。结构化输出的目标是让模型结果能被程序消费，所以提示词、JSON Schema、约束解码、解析校验、修复策略、版本管理和回归测试要一起设计。

一个稳定提示词通常分为任务目标、角色边界、上下文、输出格式、约束、示例、错误处理。few-shot 的作用不是堆案例，而是给模型示范边界：正常样例、反例、歧义输入、缺失字段时怎么处理。结构化输出常见形态是 JSON 对象、数组、枚举分类、函数参数。面试时要强调：提示词是概率接口，校验器才是确定性边界。

### 原理：提示条件、few-shot 与约束解码
模型生成可抽象为在条件上下文 C 下逐 token 采样：P(y_t | C, y_<t)。提示词改变 C，从而改变候选 token 分布。few-shot 把输入输出映射模式放进上下文，让模型在局部模式上做类比。它对格式、口径、分类边界很有用，但会占用上下文，也可能让模型过拟合示例表面形式。

JSON 模式有三层强度。第一层是自然语言要求“只输出 JSON”，最弱。第二层是 response_format 或工具参数 schema，让模型更倾向于结构化。第三层是约束解码或语法解码，在解码过程中屏蔽不合法 token，使输出满足 JSON 或 schema 语法。约束越强，格式越稳，但可能降低表达灵活性，也不能保证字段语义正确。

结构化输出的数据流可以写成：raw_input → prompt_template(version) → model_output → parse_json → validate_schema → validate_business_rules → repair_or_retry → typed_result。解析只解决字符串到对象；schema 解决类型、必填、枚举；业务校验解决“日期范围是否合理”“引用是否存在”“分数是否在阈值内”。复杂度通常由输出长度和 schema 大小决定，校验远便宜于重新调用模型。

### 工程实现要点
提示词要像代码一样管理。模板文件包含 version、适用场景、输入变量、输出 schema、变更记录和回归样例。不要在业务代码里散落长字符串。每次修改提示词，都跑固定样例集，比较结构化通过率、关键字段准确率、平均 token 和人工抽检结果。

```python
import json
from jsonschema import validate, ValidationError

SCHEMA = {
    "type": "object",
    "required": ["risk", "reason", "actions"],
    "properties": {
        "risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "reason": {"type": "string", "minLength": 1},
        "actions": {"type": "array", "items": {"type": "string"}},
    },
}

def parse_and_validate(text):
    data = json.loads(text)
    validate(instance=data, schema=SCHEMA)
    if data["risk"] == "high" and not data["actions"]:
        raise ValueError("high risk needs actions")
    return data
```

修复策略要分级。轻微格式问题，例如代码块包裹、尾逗号、前后解释文本，可以本地清洗。字段缺失、枚举错误，可以把校验错误回填给模型要求修复。语义不确定或证据不足，不应强行修复成看似合法的结果，而要返回 unknown、needs_review 或触发人工确认。

### 生产落地：方案、踩坑与排查
问题一：模型偶尔输出非 JSON。现象是解析失败率低但持续存在。原因可能是提示词只用自然语言约束，或流式半成品被解析。定位看原始输出、finish_reason、是否被截断、解析错误类型。解决是使用 JSON schema 或工具调用，结束后再解析；增加失败样例到回归集；对轻微包装做本地清洗。

问题二：字段合法但语义错。现象是 schema 全通过，但业务结果离谱。原因是 schema 只约束形状，不约束事实和推理。定位看证据输入、模型引用、字段来源、人工标注差异。解决是增加业务规则校验、要求输出 evidence_ids、对关键字段做二次检索或规则校验，把“无法判断”作为合法输出。

问题三：提示词改动后线上效果回退。现象是通过率差不多，但某类样本错误增多。原因是没有版本和回归分桶，只看整体指标。定位看 prompt_version、样本标签、字段级准确率、失败 diff。解决是提示词版本化、灰度发布、保留回滚能力，并用黄金集覆盖正常、边界、反例和恶意输入。

问题四：few-shot 越加越差。现象是 token 增加、延迟上升、模型照抄示例。原因是示例冗余或分布偏。定位看输入与示例相似度、输出重复片段、成本变化。解决是保留最能划清边界的少量示例，按任务动态选择示例，或把稳定规则移到 schema 和校验器里。

### 取舍与对比
| 方法 | 稳定性 | 成本 | 适用场景 | 主要风险 |
|---|---|---|---|---|
| 纯自然语言提示 | 低到中 | 低 | 原型、开放问答 | 格式漂移 |
| few-shot | 中 | 中到高 | 分类口径、边界示范 | 占上下文、照抄 |
| JSON Schema | 高 | 中 | 结构化抽取、配置生成 | 语义仍可能错 |
| 约束解码 | 格式最高 | 取决于实现 | 强格式接口 | 表达受限 |
| 校验后修复 | 高 | 额外调用 | 可容忍重试的任务 | 修复掩盖事实错误 |
| 人工复核 | 最高 | 高 | 高风险决策 | 吞吐低 |

### 结合项目怎么讲
可以讲“给测试平台做知识库问答和缺陷摘要”。背景：用户输入日志、报错和代码片段，希望模型输出原因分类、证据和下一步动作。问题：早期提示词只写“输出 JSON”，经常出现多余解释、字段缺失、风险等级不一致。方案：我把提示词拆成任务、输入、输出 schema、约束和 few-shot；输出字段包括 risk、reason、evidence_ids、actions、confidence；先做 JSON Schema 校验，再做业务规则校验，例如 evidence_ids 必须来自检索结果；失败时把校验错误回填修复，仍失败则进入人工复核。数据/效果：可以用结构化通过率、字段准确率、人工抽检一致率和平均成本衡量。反思：提示词不是一次写完，必须版本化和回归；schema 保证形状，事实正确性要靠证据和业务校验。""",
        points=[
            "提示词是概率接口，Schema 和校验器才是确定性边界。",
            "few-shot 用来示范边界，不是越多越好。",
            "结构化输出要经过解析、Schema 校验和业务规则校验。",
            "修复策略要区分格式错误、字段错误和语义不确定。",
            "提示词必须版本化、灰度和回归测试。",
        ],
        drill=[
            dict(level="基础", q="一个好的提示词通常包含哪些部分？", a="通常包含任务目标、输入说明、角色或边界、输出格式、约束条件、示例和异常处理。对结构化输出，还要明确字段名、类型、枚举、缺失信息怎么表示。不要只写“请严格输出 JSON”，要把允许和禁止的行为写清楚。生产里还要给提示词版本号，便于回归和回滚。"),
            dict(level="原理", q="few-shot 为什么有用，又为什么不能滥用？", a="few-shot 把输入到输出的模式放进上下文，模型会根据局部模式做类比，所以对分类口径、格式边界和反例很有帮助。但示例会占用上下文，增加成本和延迟，也可能让模型照抄示例。示例分布偏时，会把模型带向错误口径。更好的做法是保留少量高信息量样例，并用回归集评估。"),
            dict(level="实现", q="如何保证模型输出能被程序稳定消费？", a="我会优先使用 JSON Schema、工具调用参数或约束解码来限制格式。拿到输出后先解析 JSON，再做 schema 校验，最后做业务规则校验。失败时按错误类型决定本地清洗、模型修复、重试或人工复核。业务代码只消费 typed result，不直接消费模型原文。"),
            dict(level="落地", q="提示词版本管理怎么做？", a="每个提示词模板要有 version、变更说明、输入变量、输出 schema 和适用场景。调用日志记录 prompt_version、model、参数、样本标签和校验结果。修改提示词必须跑固定回归集，比较结构化通过率、字段准确率、成本和延迟。上线时灰度一部分流量，保留旧版本快速回滚。"),
            dict(level="排查", q="schema 校验都通过了但用户说结果不对，怎么查？", a="先承认 schema 只保证形状，不保证事实。排查时看输入证据是否完整、检索片段是否相关、模型是否引用了不存在的证据、关键字段是否来自提示词允许范围。再按样本标签分桶，看是某类场景系统性错还是个别幻觉。解决可以增加 evidence_ids、业务规则校验、二次检索验证，必要时引入人工复核。"),
            dict(level="取舍", q="JSON Schema、约束解码和后置校验怎么取舍？", a="JSON Schema 易接入，能明显提升结构稳定性，是多数业务的首选。约束解码格式最强，但依赖模型或推理框架支持，复杂 schema 可能影响表达。后置校验成本低且确定，但只能发现问题，不能阻止模型生成错误。生产里通常三者组合：生成时尽量约束，返回后必须校验，失败再修复或降级。"),
            dict(level="设计", q="设计一个缺陷摘要的结构化输出方案，你会怎么做？", a="我会定义字段：summary、root_cause、evidence_ids、risk、next_actions、confidence 和 unknown_reason。提示词要求只使用输入日志和检索证据，证据不足时输出 unknown。Schema 约束字段类型和枚举，业务规则校验证据 id 必须存在，高风险必须有动作。再建立包含正常、缺日志、误导文本、长日志和边界错误码的回归集，用字段级准确率和人工一致率评估。"),
        ],
        choice=[
            dict(q="关于提示词工程，下列说法正确的是？", options=["提示词写清楚后就不需要校验", "提示词应当像接口一样版本化", "few-shot 越多效果一定越好", "只要输出 JSON 就代表语义正确"], answer=[1], explain="提示词需要版本化、回归和回滚。校验仍必需，few-shot 不是越多越好，JSON 合法不代表事实正确。"),
            dict(q="结构化输出流水线中哪些步骤通常必要？", options=["解析模型原文", "Schema 校验", "业务规则校验", "跳过日志以减少成本"], answer=[0, 1, 2], explain="解析、schema 和业务校验分别解决对象化、形状和语义规则问题。日志是排查基础，不能简单跳过。"),
            dict(q="few-shot 最适合用来做什么？", options=["替代所有业务规则", "示范分类边界和输出格式", "保证模型永不幻觉", "减少所有 token 成本"], answer=[1], explain="few-shot 擅长示范模式和边界，但不能替代规则，也不能保证事实正确，通常还会增加 token。"),
            dict(q="模型输出字段类型正确但 evidence_ids 不存在，属于什么问题？", options=["解析错误", "传输错误", "业务规则校验失败", "无需处理"], answer=[2], explain="JSON 和 schema 可能都通过，但 evidence_ids 必须来自给定证据，这是业务规则校验问题。"),
        ],
        short=[
            dict(q="说明结构化输出从提示词到业务入库的完整链路。", points=["模板和版本", "模型生成与格式约束", "JSON 解析和 Schema 校验", "业务规则校验", "修复、重试、人工复核和日志"], reference="完整链路从 prompt_template 开始，模板带版本、输入变量、输出 schema 和约束。模型生成时尽量使用 JSON 模式、工具参数或约束解码。返回后先提取和解析 JSON，再用 Schema 校验必填字段、类型、枚举和数组结构。之后做业务规则校验，例如证据 id 是否存在、金额或时间范围是否合理。失败时按类型处理：轻微格式问题本地清洗，字段缺失可回填错误让模型修复，证据不足要输出 unknown 或进入人工复核。所有步骤记录 prompt_version、错误类型和样本标签。"),
            dict(q="如何给提示词建立回归测试？", points=["构建黄金样例和边界样例", "按标签分桶评估", "比较结构化通过率和字段准确率", "记录成本与延迟", "灰度和回滚"], reference="提示词回归要先准备固定样例集，覆盖正常输入、边界输入、缺失信息、反例、恶意注入和历史线上失败样本。每条样例有期望字段或人工标注。每次修改提示词或模型参数后，批量运行并按标签分桶统计结构化通过率、关键字段准确率、人工一致率、平均 token 和延迟。不能只看整体分数，因为某类样本可能回退。上线时用 prompt_version 灰度，日志能按版本对比，发现问题可快速回滚。"),
            dict(q="为什么 Schema 不能替代业务校验？", points=["Schema 只约束形状", "事实和证据需要额外验证", "业务约束常跨字段", "合法 JSON 也可能幻觉", "需要 unknown 或人工复核路径"], reference="Schema 擅长检查类型、必填、枚举、长度等结构问题，但它不知道模型引用的证据是否真实，也不知道跨字段业务关系是否成立。例如 risk 是 high 且 actions 为空，类型上可能合法，业务上却不可接受；evidence_ids 是字符串数组，但 id 可能并不存在。模型还可能生成合法 JSON 的幻觉内容。所以生产系统要在 Schema 后增加业务校验、证据校验和跨字段规则。对于无法判断的样本，应允许 unknown 或人工复核，而不是强行修成看似正确的结果。"),
        ],
        labs=["lab-json-repair", "lab-tool-schema"],
        related=["dev-api", "dev-eval-driven", "dev-testing", "llm-decoding"],
    ),

    dict(
        id="dev-function-calling", course="dev", order=3,
        title="函数调用循环实现", summary="用可控循环把模型意图变成真实工具执行",
        md="""### 一句话与核心概念
函数调用不是模型直接执行代码，而是模型按 schema 生成“想调用哪个工具、参数是什么”，宿主程序校验参数、执行工具、把结果再喂回模型，直到模型给出最终答案或达到停止条件。关键点是循环、参数校验、工具错误回填、并行调用、最大轮数、权限和流式增量拼接。

最小对象包括 tools 注册表、JSON Schema、messages、tool_calls、tool_result、loop_state。模型只负责选择工具和生成参数，宿主负责执行。这样设计把不可信的自然语言推理和可信边界分开：模型不能越过 schema 和权限直接操作系统。面试时要说清楚 tool role 的结果必须和 tool_call_id 配对，否则模型无法把观察对应到前一次动作。

### 原理：工具调用循环的数据流
基本伪代码是：把用户问题和工具描述发给模型；如果返回 final answer，就结束；如果返回 tool_calls，就逐个校验和执行；把每个结果作为 tool message 追加；进入下一轮。这个循环类似“计划-行动-观察”的状态机。复杂度约为 O(R * (M + T))，R 是最大轮数，M 是模型调用成本，T 是工具执行成本。真正贵的是模型 token 和慢工具，而不是循环代码本身。

并行调用的前提是工具之间没有数据依赖。若模型同一轮返回多个 tool_call，例如查询两个独立文件、查两个接口，可以并发执行并按原 call_id 回填。若第二个工具依赖第一个结果，就必须让模型下一轮再决定。流式下工具调用更复杂，因为 name 和 arguments 可能分片到达，客户端要按 tool_call index 或 id 累积参数字符串，等 finish_reason 表明 tool_calls 完成后再解析。

错误回填很重要。工具失败不一定要结束，可以把结构化错误返回给模型：error_type、message、retryable、hint。模型下一轮可能换参数、换工具或承认失败。但宿主必须限制最大轮数和最大工具次数，避免模型在错误上无限循环。

### 工程实现要点
工具注册表建议用 name 到 ToolSpec 的映射，ToolSpec 包含描述、schema、callable、timeout、permission、是否可并行。参数校验使用 jsonschema 或 Pydantic，校验通过后才执行。工具结果要截断，避免把超长日志塞回上下文。

```python
import json, concurrent.futures

def run_loop(client, tools, messages, max_rounds=6):
    for _ in range(max_rounds):
        resp = client.chat(messages=messages, tools=[t.schema for t in tools.values()])
        msg = resp.message
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg["content"]

        def run_one(call):
            name = call["function"]["name"]
            raw = call["function"].get("arguments") or "{}"
            try:
                tool = tools[name]
                args = json.loads(raw)
                tool.validate(args)
                result = tool.invoke(args)
                content = {"ok": True, "result": result}
            except Exception as exc:
                content = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
            return {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(content, ensure_ascii=False)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            tool_messages = list(pool.map(run_one, calls))
        messages.extend(tool_messages)
    raise RuntimeError("tool loop reached max_rounds")
```

生产代码还要加权限检查、工具超时、取消、幂等键、审计日志、结果大小限制和敏感字段脱敏。对写操作工具，建议分为 plan、confirm、execute，或者要求人工批准。对读操作工具，也要限制路径、域名、SQL 和返回行数。

### 生产落地：方案、踩坑与排查
问题一：模型反复调用同一个失败工具。现象是轮数耗尽、成本升高、用户只看到失败。原因是错误回填太模糊，或者没有最大轮数。定位看 loop_trace、tool_name、参数 diff、错误类型和轮数。解决是返回结构化错误和可操作 hint，设置 max_rounds、max_tool_calls、相同错误熔断。

问题二：参数看似合法但执行危险。现象是模型传入 `../../` 路径、超大 limit、危险 shell。原因是只做 JSON 类型校验，没有业务白名单和权限。定位看工具参数审计、拒绝日志、权限命中规则。解决是 schema 加枚举和范围，业务层做路径归一化、域名白名单、SQL 只读限制，写操作走审批。

问题三：并行工具结果对不上。现象是模型把 A 工具结果当成 B 的观察，下一轮回答混乱。原因是回填消息没有保留 tool_call_id，或并发后顺序和 id 丢失。定位看 assistant tool_calls 与后续 tool messages 的 id 配对。解决是每个结果必须带原 call_id，必要时按原调用顺序追加，但语义靠 id 绑定。

问题四：流式工具调用参数 JSON 解析失败。现象是 arguments 少了后半截或多个工具参数串在一起。原因是按 chunk 直接解析，没有按 index/id 聚合。定位看原始 chunk、tool_call_delta 的 index、聚合 buffer。解决是完成前只缓存，收到工具调用结束标志后再 json.loads 和 schema 校验。

### 取舍与对比
| 设计 | 优点 | 风险 | 适用场景 |
|---|---|---|---|
| 串行工具调用 | 简单、依赖清晰 | 慢 | 工具之间有依赖 |
| 并行工具调用 | 降低总耗时 | 结果配对和资源控制复杂 | 独立查询、批量读取 |
| 抛异常终止 | 失败清晰 | 模型无法自修复 | 高风险写操作 |
| 错误回填给模型 | 可自动换参或解释失败 | 可能循环消耗 | 读操作、低风险工具 |
| 宽松参数 | 模型更灵活 | 安全和稳定性差 | 原型 |
| 严格 schema | 可控、可审计 | 需要维护 schema | 生产系统 |

### 结合项目怎么讲
可以讲“用 Agent 自动生成和修复自动化用例”。背景：用户给需求和失败日志，Agent 需要读文件、搜索代码、运行测试、修改建议。问题：早期让模型直接输出命令，容易参数错误、重复执行、日志爆上下文。方案：我把能力拆成 read_file、search、run_test、write_patch 等工具，每个工具有 schema、权限和超时；主循环限制 6 轮，每轮工具错误结构化回填；读操作可并行，写操作必须审批；工具结果截断并带 evidence id。数据/效果：可以用任务成功率、平均轮数、工具失败率、人工接管率衡量。反思：函数调用提高可控性，但不是安全本身，安全来自校验、权限、审计和停止条件。""",
        points=[
            "模型只生成工具意图，宿主程序负责校验、权限和执行。",
            "tool_call_id 与 tool message 必须一一配对。",
            "工具错误应结构化回填，但要限制最大轮数和熔断。",
            "并行调用只适合无依赖工具，结果要保留 id。",
            "流式工具参数必须按片段聚合完成后再解析。",
        ],
        drill=[
            dict(level="基础", q="函数调用和普通文本回答有什么区别？", a="普通文本回答是模型直接生成给用户看的内容。函数调用是模型生成一个结构化意图，包括工具名和参数，真正执行由宿主程序完成。宿主会按 schema 校验参数、检查权限、调用工具，再把结果作为 tool message 放回上下文。这样可以让模型使用外部能力，同时保留工程边界。"),
            dict(level="原理", q="为什么工具结果要带 tool_call_id？", a="同一轮模型可能发起多个工具调用，尤其是并行调用时，返回顺序可能和发起顺序不同。tool_call_id 是观察和动作的关联键，模型下一轮需要知道哪个结果对应哪个调用。如果丢掉 id，模型可能把一个文件的内容当成另一个查询结果。生产日志也要用 call_id 串起模型请求、工具参数和工具返回。"),
            dict(level="实现", q="写函数调用循环时最小需要哪些步骤？", a="第一步把 messages 和 tool schema 发给模型。第二步判断模型是否返回 tool_calls，没有就返回最终答案。第三步逐个解析 arguments，做 schema 和业务校验。第四步执行工具，把成功或失败结果包装成 tool message。第五步追加到 messages 进入下一轮，并在最大轮数内停止。"),
            dict(level="落地", q="工具报错时应该直接失败还是回填给模型？", a="取决于风险和错误类型。读操作、可重试的网络错误、参数可修正的错误，可以结构化回填给模型，让它换参数或解释失败。权限拒绝、危险写操作、不可恢复错误应直接终止或请求人工确认。无论哪种，都要记录错误类型、参数摘要和轮数，并设置最大重试和熔断。"),
            dict(level="排查", q="Agent 工具循环成本异常升高怎么查？", a="先看平均轮数、每轮 token、工具调用次数、重复调用比例和错误回填次数。再按任务类型聚合，看是否某个工具经常失败导致模型反复尝试。检查提示词是否缺少停止条件，错误信息是否不可操作。解决包括限制 max_rounds、相同参数去重、错误 hint 更具体、对高成本工具加预算和审批。"),
            dict(level="取舍", q="并行工具调用有什么收益和风险？", a="收益是独立工具可以同时执行，降低总等待时间，特别是多个检索、多个文件读取或多个只读接口。风险是资源瞬时放大、结果配对复杂、工具之间隐含依赖被破坏。实现上要限制并发数、保留 tool_call_id、对工具声明是否可并行。若调用有依赖，宁可串行让模型下一轮基于观察再决策。"),
            dict(level="设计", q="如果要做一个支持写文件的 Coding Agent 工具层，你会怎么设计？", a="我会把读写工具分开：read_file、search 是只读，可自动执行；write_patch 是写操作，要求路径在工作区内、补丁可解析、命中权限规则，必要时人工确认。每次工具调用记录 call_id、参数摘要、diff 摘要和结果。循环有最大轮数、最大写次数和预算。执行后必须跑相关测试或静态检查，失败结果回填给模型，但不能无限自动修改。"),
        ],
        choice=[
            dict(q="函数调用中真正执行工具的是谁？", options=["模型本身", "宿主程序或客户端", "提示词模板", "JSON Schema"], answer=[1], explain="模型只产生工具名和参数，宿主程序负责校验、权限和执行。Schema 只是约束参数形状。"),
            dict(q="工具调用循环必须包含哪些保护？", options=["最大轮数", "参数校验", "权限检查", "允许无限重试直到成功"], answer=[0, 1, 2], explain="最大轮数、参数校验和权限检查是基本保护。无限重试会放大成本和风险。"),
            dict(q="并行工具调用的前提是什么？", options=["工具之间没有数据依赖", "所有工具都是写操作", "不需要 tool_call_id", "模型温度必须为 0"], answer=[0], explain="并行只适合无依赖调用。写操作更要谨慎，tool_call_id 仍然必需，温度不是并行前提。"),
            dict(q="流式工具参数应该什么时候解析 JSON？", options=["收到第一个参数片段时", "每个 chunk 都解析", "按 id 聚合完成后", "不需要解析"], answer=[2], explain="arguments 可能被分片，必须按 id 或 index 聚合完成后再解析和校验。"),
        ],
        short=[
            dict(q="写出函数调用循环的关键步骤。", points=["发送 messages 和 tools", "判断 final 或 tool_calls", "解析和校验参数", "执行工具并包装 tool message", "追加观察并限制最大轮数"], reference="关键步骤是一个受控状态机。先把当前 messages 和工具 schema 发给模型。若模型返回普通内容且没有 tool_calls，就把它作为最终答案。若返回 tool_calls，宿主按工具名查注册表，解析 arguments，做 JSON Schema 和业务校验，再检查权限和预算。执行工具后，把成功结果或结构化错误包装成 role 为 tool、带 tool_call_id 的消息追加回上下文。循环继续，直到最终答案、错误终止或达到最大轮数。"),
            dict(q="如何处理工具错误，避免无限循环？", points=["错误结构化", "区分可重试和不可重试", "设置 max_rounds 和 max_tool_calls", "相同错误熔断", "审计工具参数和结果"], reference="工具错误不要只返回一段自然语言。应包含 error_type、message、retryable、hint 和必要的安全说明。可修复的参数错误和临时网络错误可以回填给模型，不可恢复的权限拒绝或危险操作要终止。循环层要设置 max_rounds、max_tool_calls、单工具超时和预算。若同一工具同一参数重复失败，应熔断而不是继续烧 token。日志要记录 call_id、工具名、参数摘要、错误类型和轮数，方便定位。"),
            dict(q="流式场景下实现工具调用有哪些额外注意？", points=["delta 可能分片", "按 index/id 聚合 name 和 arguments", "完成后再解析 JSON", "处理中断和截断", "不要执行半成品参数"], reference="流式返回中，工具名和 arguments 可能分多次到达，甚至多个工具调用交错出现。客户端不能在收到第一个片段时执行工具，而要按 tool_call index 或 id 维护 buffer，持续合并 name 和 arguments。只有当模型表明本轮工具调用结束时，才对完整 arguments 做 json.loads、schema 校验和权限检查。若流中断、超时或 finish_reason 表示截断，应把本轮标记失败，不能执行半成品参数。所有原始 chunk 最好可追踪，便于排查解析问题。"),
        ],
        labs=["lab-tool-loop", "lab-tool-schema", "lab-sse-parser"],
        related=["agent-tools", "harness-loop", "harness-permission", "dev-api"],
    ),

    dict(
        id="dev-mini-agent", course="dev", order=4,
        title="从零写一个可用的 Agent", summary="用 80 行核心循环做出可控的最小 Agent",
        md="""### 一句话与核心概念
可用 Agent 的最小闭环是：接收目标，维护上下文，让模型选择工具，执行并观察，直到完成、失败或触发停止条件。它不是“提示词加模型”这么简单，而是一个带状态、工具、权限、预算、日志和评测的运行时。面试时要能从 80 行核心代码讲到生产清单：日志、重试、预算、权限、持久化、评测和回滚。

一个 Mini Agent 至少包含六个部分：system prompt、messages、tools、loop、stop condition、result。再往生产走，要有 run_id、trace、token_budget、tool_budget、permission policy、checkpoint、evaluation。核心原则是：模型负责决策建议，程序负责边界控制；能确定的用代码，不要交给模型自由发挥。

### 原理：Agent 循环为什么能工作
Agent 循环可以看成“状态 s_t → 模型策略 π(a_t|s_t) → 工具环境执行 a_t → 观察 o_t → 新状态 s_{t+1}”。状态包括目标、历史消息、工具结果、预算和约束；动作是回答或工具调用；观察是工具返回。它类似强化学习里的 agent-environment loop，但生产实现不需要训练策略，只是用预训练模型作为策略函数。

停止条件比提示词更可靠。常见停止包括：模型给出 final、达到最大轮数、预算耗尽、权限被拒、工具连续失败、用户取消。复杂度由轮数乘以每轮模型和工具成本决定，所以必须把 max_rounds、max_tokens、max_tool_calls 暴露为配置。没有这些限制，Agent 会把一个小问题变成不可控长任务。

上下文管理决定 Agent 是否稳定。短任务可以保留全量 messages；长任务要做裁剪、摘要或 checkpoint。裁剪不能破坏工具调用配对，即 assistant 的 tool_calls 和对应 tool messages 要一起保留或一起摘要。否则模型下一轮会看到不完整状态。

### 工程实现要点
下面是约 80 行核心代码的结构示意。真实项目会把日志、权限、schema 和 SDK 细节拆开，但主循环就是这些步骤。

```python
import json, time, uuid

class MiniAgent:
    def __init__(self, client, tools, policy, max_rounds=8):
        self.client = client
        self.tools = {t.name: t for t in tools}
        self.policy = policy
        self.max_rounds = max_rounds

    def run(self, goal):
        run_id = str(uuid.uuid4())
        messages = [
            {"role": "system", "content": "完成任务。需要工具时调用工具；证据不足就说明不足。"},
            {"role": "user", "content": goal},
        ]
        trace = []
        for step in range(self.max_rounds):
            started = time.time()
            resp = self.client.chat(messages=messages, tools=[t.schema for t in self.tools.values()])
            msg = resp.message
            messages.append(msg)
            trace.append({"run_id": run_id, "step": step, "model_ms": int((time.time() - started) * 1000)})
            calls = msg.get("tool_calls") or []
            if not calls:
                return {"ok": True, "answer": msg.get("content", ""), "trace": trace}

            for call in calls:
                name = call["function"]["name"]
                raw = call["function"].get("arguments") or "{}"
                try:
                    tool = self.tools[name]
                    args = json.loads(raw)
                    tool.validate(args)
                    decision = self.policy.check(name, args)
                    if not decision.allow:
                        raise PermissionError(decision.reason)
                    result = tool.invoke(args)
                    payload = {"ok": True, "result": result}
                except Exception as exc:
                    payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(payload, ensure_ascii=False)})
                trace.append({"run_id": run_id, "step": step, "tool": name, "ok": payload["ok"]})
        return {"ok": False, "error": "max_rounds", "trace": trace}
```

生产化清单：日志要记录 run_id、step、模型、token、工具、耗时、错误；重试只包模型瞬时错误和幂等工具；预算包括 token、工具次数、墙钟时间和金额；权限按工具、路径、域名、写操作分级；持久化保存目标、消息摘要、trace、产物和 checkpoint；评测用固定任务集统计成功率、平均轮数、人工接管率和危险操作拦截率。

### 生产落地：方案、踩坑与排查
问题一：Agent 看似在工作但没有完成。现象是日志很多、工具调用很多，最终回答空泛。原因是没有明确完成判据，模型把探索当进度。定位看 trace 的 step、工具结果是否产生新信息、final 是否引用证据。解决是提示词定义完成标准，程序限制轮数，并让最终回答包含证据和未完成项。

问题二：成本失控。现象是少量任务消耗大量 token。原因是上下文无限增长、工具返回太长、失败循环。定位看每步输入 token、工具返回大小、重复调用比例。解决是结果截断、上下文裁剪、摘要、预算上限、相同动作去重，高成本工具先估算再执行。

问题三：权限边界被模型绕过。现象是模型尝试读取无关路径、访问外部域名、执行写操作。原因是只在 system prompt 里写禁止，没有程序级 policy。定位看被拒绝工具参数和权限命中日志。解决是工具层硬校验、deny 优先、写操作审批、最小权限运行，拒绝原因回填但不泄露敏感规则。

问题四：任务中断后无法恢复。现象是进程重启后任务只能从头开始。原因是没有 checkpoint 和产物索引。定位看是否保存 run_id、messages、工具结果、文件 diff、测试结果。解决是每轮持久化 trace 和 checkpoint，可恢复时从最近一致状态继续，而不是重复执行副作用工具。

### 取舍与对比
| 方案 | 优点 | 风险 | 适用场景 |
|---|---|---|---|
| 纯脚本流程 | 可预测、易测试 | 灵活性低 | 固定流水线 |
| Mini Agent | 灵活、代码少 | 稳定性依赖边界 | 探索性任务、辅助开发 |
| 复杂多 Agent | 可分工、可并行 | 编排和一致性复杂 | 大任务拆解 |
| 全量历史上下文 | 信息完整 | 成本上涨、超长 | 短任务 |
| 摘要和裁剪 | 成本可控 | 可能丢关键状态 | 长任务 |
| 自动写操作 | 效率高 | 风险大 | 低风险沙箱 |

### 结合项目怎么讲
可以讲“在 CI 里跑 Coding Agent 做缺陷修复”。背景：CI 发现单测失败，希望 Agent 读取失败日志、定位文件、尝试补丁、运行相关测试。问题：直接让模型自由输出命令，容易重复跑全量测试、修改无关文件、失败后无证据。方案：我实现 Mini Agent，工具只有 read_file、search、apply_patch、run_test；每个工具有 schema、超时和权限；Agent 有 token 与轮数预算，trace 记录每步证据；写补丁限制在工作区，测试失败回填给模型，最多修复两轮。数据/效果：用修复成功率、平均轮数、测试通过率、人工审查拒绝率衡量。反思：Mini Agent 的价值是闭环和可审计，不是替代所有工程流程；高风险动作仍要审批和回滚。""",
        points=[
            "Mini Agent 是状态机：目标、模型动作、工具观察、停止条件。",
            "生产边界靠代码控制，不能只靠 system prompt。",
            "预算要覆盖 token、工具次数、墙钟时间和金额。",
            "持久化 trace 和 checkpoint 才能排查、恢复和审计。",
            "评测要看任务成功率、平均轮数、接管率和安全拦截率。",
        ],
        drill=[
            dict(level="基础", q="一个最小可用 Agent 需要哪些组件？", a="至少需要 system prompt、messages、工具注册表、模型调用、工具执行循环和停止条件。模型负责决定回答还是调用工具，宿主程序负责参数校验、权限和执行。还要有最大轮数，避免无限循环。若要生产可用，还需要日志、预算、持久化和评测。"),
            dict(level="原理", q="Agent 循环和普通函数调用有什么关系？", a="函数调用是 Agent 循环里的动作执行机制。Agent 每轮把当前状态交给模型，模型可能返回最终答案，也可能返回工具调用。工具结果变成观察，再进入下一轮。普通一次函数调用只解决单步工具使用，Agent 循环解决多步计划、观察和修正。"),
            dict(level="实现", q="80 行 Mini Agent 代码里最重要的控制点是什么？", a="最重要的是工具注册、参数校验、权限检查、错误回填和停止条件。代码要保证模型不能直接执行工具，只能提交结构化参数。每次工具结果都要用 tool_call_id 回填。循环必须有 max_rounds，并在返回结果中带 trace，方便知道每一步做了什么。"),
            dict(level="落地", q="Agent 的预算应该怎么设计？", a="预算不能只看一次模型调用。要同时限制总 token、最大轮数、工具调用次数、单工具超时、总墙钟时间和金额估算。预算要按任务类型配置，例如聊天问答和代码修复不同。每轮执行前检查剩余预算，不足时让模型总结当前进度并停止。日志中记录预算消耗，方便优化成本。"),
            dict(level="排查", q="Agent 经常失败但日志里只有最终错误，怎么办？", a="说明缺少 step 级 trace。需要记录 run_id、step、模型请求摘要、tool_call_id、工具名、参数摘要、耗时、返回大小、错误类型和最终状态。还要保存关键产物，例如补丁、测试输出摘要、检索证据 id。这样才能判断是模型决策错、工具失败、权限拒绝、预算耗尽还是提示词不清。"),
            dict(level="取舍", q="什么时候用 Agent，什么时候用固定工作流？", a="任务路径固定、规则清晰、结果可枚举时，固定工作流更稳定、更便宜。任务需要探索、分支决策、跨工具组合、根据观察修正时，Agent 更合适。生产里可以混合：外层是确定性流程，某些需要推理的节点交给 Agent。不要为了新潮把所有 if-else 都改成 Agent。"),
            dict(level="设计", q="设计一个自动修复测试失败的 Agent，你会怎么限制风险？", a="我会把工具限制在工作区内，读操作自动允许，写操作只允许补丁格式并限制文件范围。每轮有 token、时间和工具次数预算，最多尝试少数修复轮次。运行测试只跑相关子集，避免无限消耗。所有修改生成 diff 和理由，最终必须报告测试结果、未验证项和风险。高风险文件或大范围改动要求人工确认。"),
        ],
        choice=[
            dict(q="Mini Agent 的核心循环是什么？", options=["一次性生成完整答案", "状态、动作、工具观察、再决策", "只调用搜索引擎", "把所有规则写进 prompt"], answer=[1], explain="Agent 的核心是基于当前状态选择动作，执行工具得到观察，再进入下一轮。prompt 不是唯一控制手段。"),
            dict(q="生产化 Agent 必须记录哪些信息？", options=["run_id 和 step", "工具名、参数摘要和耗时", "错误类型和预算消耗", "用户的所有敏感原文永久明文保存"], answer=[0, 1, 2], explain="trace、工具和预算信息是排查基础。敏感原文不能无控制明文保存，应脱敏或按策略处理。"),
            dict(q="只靠 system prompt 禁止危险操作为什么不够？", options=["模型可能误解或被注入诱导", "程序级权限更确定", "提示词不能做路径归一化", "因为模型完全不会遵守任何指令"], answer=[0, 1, 2], explain="模型通常会遵守指令，但不能作为安全边界。权限、路径和资源限制要由程序实现。"),
            dict(q="Agent 任务中断后想恢复，最需要什么？", options=["更高 temperature", "checkpoint 和 trace", "删除所有历史", "只保存最终答案"], answer=[1], explain="恢复依赖一致的 checkpoint、messages 摘要、工具结果和产物索引，而不是模型采样参数。"),
        ],
        short=[
            dict(q="描述一个 Mini Agent 的核心架构。", points=["模型客户端", "工具注册表和 schema", "循环与停止条件", "权限和预算", "trace 与结果"], reference="Mini Agent 可以分为模型客户端、工具注册表、运行循环、控制策略和结果记录。工具注册表保存 name、description、schema、callable、timeout 和权限。循环每轮调用模型，若有 tool_calls 就解析参数、校验 schema、检查权限、执行工具并把观察追加到 messages；若无工具调用则返回最终答案。控制策略包括 max_rounds、token 预算、工具次数和错误熔断。结果中带 answer、trace、产物和未完成项，方便审计和复现。"),
            dict(q="Agent 上线前的生产化清单有哪些？", points=["日志和指标", "重试与超时", "预算控制", "权限与隔离", "持久化和评测"], reference="上线前要补齐运行时能力。日志记录 run_id、step、模型、token、工具、耗时和错误；指标统计成功率、平均轮数、工具失败率和成本。模型瞬时错误和幂等工具可以受控重试，所有工具有超时。预算限制 token、时间、工具次数和金额。权限按工具、路径、域名、写操作分级，危险动作审批。每轮持久化 trace、checkpoint 和产物。评测用固定任务集和线上抽检衡量成功率、安全拦截率和人工接管率。"),
            dict(q="为什么 Agent 需要评测，而不是只看演示效果？", points=["演示样例覆盖不足", "模型输出有随机性", "回归需要量化", "安全和成本也要评估", "不同任务要分桶"], reference="Agent 的失败往往出现在长尾输入、工具异常、权限边界和多轮循环里，演示样例很难覆盖。模型输出也有随机性，同一任务可能因上下文和采样变化产生不同路径。评测集可以固定任务、期望结果、允许工具和评分标准，用成功率、平均轮数、成本、人工接管率和危险动作拦截率做量化。还要按任务类型分桶，例如问答、代码修复、检索摘要分开看。每次改提示词、工具或模型后跑回归，才能知道是否退化。"),
        ],
        labs=["lab-tool-loop", "lab-permission", "lab-context-trim"],
        related=["agent-what", "agent-reasoning", "agent-tools", "agent-eval", "harness-loop"],
    ),

    dict(
        id="dev-mcp", course="dev", order=5,
        title="写一个 MCP 服务器", summary="用标准协议把工具安全暴露给 Agent 客户端",
        md="""### 一句话与核心概念
MCP 是把外部工具、资源和提示模板暴露给 Agent 客户端的一套协议思路。它解决“工具如何被发现、描述、调用、返回结果”的标准化问题，而不是替代函数调用或自动解决安全。写 MCP 服务器时，要讲清协议要点、Python SDK 示意、本地与远程传输、鉴权、调试和测试。

从应用视角看，MCP 服务器像一个独立工具进程。客户端连接后初始化，读取 tools/list、resources/list 或 prompts/list。模型决定使用某个工具时，客户端向服务器发 tools/call，服务器校验参数、执行逻辑、返回结构化内容。模型并不直接连服务器，真正的调用仍由客户端和宿主控制。

### 原理：JSON-RPC、能力发现与传输边界
MCP 的交互可理解为基于 JSON-RPC 的请求响应。每个请求有 method、params、id；响应要么有 result，要么有 error。初始化阶段协商协议能力，工具列表阶段返回 name、description、inputSchema。调用阶段传入工具名和 arguments。这个设计让客户端不需要提前写死每个工具，而是在运行时发现能力。

本地传输常见是 stdio：客户端启动服务器进程，通过标准输入输出发送 JSON 消息。优点是部署简单、权限跟随本机进程，适合文件系统、本地索引、开发工具。远程传输可以通过 HTTP 或流式 HTTP 一类方式承载，适合共享服务、集中鉴权和跨机器访问，但要处理身份、网络、租户隔离和限流。

MCP 与函数调用的关系是上下游。函数调用描述“模型想调用哪个工具”；MCP 描述“客户端怎样连接一个工具服务器并执行调用”。客户端通常把 MCP server 暴露的工具转换成模型可见的 tool schema，再把模型 tool_call 转发成 MCP tools/call。安全边界仍在客户端、服务器和部署环境三处共同实现。

### 工程实现要点
Python SDK 的具体 API 可能随版本演进，下面是示意结构，重点是工具定义、参数类型、启动方式和错误返回。实际项目要以当前 SDK 文档为准。

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("text-tools")

@mcp.tool()
def summarize(text: str, max_sentences: int = 3) -> dict:
    if not text.strip():
        raise ValueError("text is empty")
    if max_sentences < 1 or max_sentences > 5:
        raise ValueError("max_sentences out of range")
    parts = [p.strip() for p in text.split(".") if p.strip()]
    return {"summary": ". ".join(parts[:max_sentences])}

if __name__ == "__main__":
    mcp.run()
```

工具设计要小而清晰。名称用动词加对象，例如 search_docs、read_note、create_ticket。description 写能力边界和限制，不要写营销话术。inputSchema 尽量用枚举、最小最大值、必填字段和格式约束。返回内容要结构化，包含 ok、data、error 或 content blocks，避免只返回一大段不可解析文本。

本地 stdio 配置一般包含 server name、command、args、env。env 里放凭据引用，不要把密钥写进配置仓库。远程服务要做鉴权、租户隔离、请求限流、审计和 TLS。服务器端还要限制执行时间、并发、返回大小和访问范围。调试时保留原始 JSON-RPC 日志摘要，但不要记录敏感参数明文。

### 生产落地：方案、踩坑与排查
问题一：客户端看不到工具。现象是 MCP 进程启动了，但工具列表为空或连接失败。原因可能是启动命令错误、工作目录不对、标准输出被普通日志污染、初始化失败。定位看客户端 MCP 日志、服务器 stderr、initialize 请求响应、tools/list 响应。解决是日志写 stderr 或文件，stdout 只走协议消息；固定工作目录和环境变量；加启动自检。

问题二：工具调用参数总是不符合预期。现象是模型传错字段、漏字段或传超大值。原因是工具描述太模糊，schema 太宽，错误信息不可操作。定位看 tools/list 暴露给模型的 schema、失败 arguments、校验错误分布。解决是收窄 schema，增加枚举和范围，把错误返回成字段级说明，并加入回归样例。

问题三：本地工具泄露权限。现象是 Agent 读取了不该读的文件或访问了不该访问的网络。原因是把 MCP server 当成可信插件，没有做路径和域名限制。定位看工具审计日志、访问路径归一化结果、权限命中规则。解决是最小权限运行、工作区沙箱、路径白名单、只读模式、远程请求域名白名单和敏感字段脱敏。

问题四：远程 MCP 服务不稳定。现象是工具调用慢、偶发 5xx、多个客户端互相影响。原因是没有限流、隔离和超时，或者工具内部依赖慢服务。定位看服务端 p95、队列长度、并发、租户维度错误率、下游耗时。解决是租户级限流、超时和熔断、异步队列、缓存只读结果，并把 retryable 信息返回给客户端。

### 取舍与对比
| 方案 | 优点 | 风险 | 适用场景 |
|---|---|---|---|
| 内置函数工具 | 简单、延迟低 | 难复用、耦合客户端 | 单应用小工具 |
| 本地 stdio MCP | 部署轻、适合本机资源 | 进程和环境问题多 | 文件、IDE、本地索引 |
| 远程 MCP | 可共享、易集中治理 | 鉴权和隔离复杂 | 企业服务、共享知识库 |
| 宽 schema 工具 | 模型自由度高 | 参数错误和风险高 | 原型验证 |
| 窄 schema 工具 | 稳定、可审计 | 需要更多工具拆分 | 生产工具 |
| 直接暴露底层 API | 能力完整 | 安全边界薄 | 内部受控脚本 |

### 结合项目怎么讲
可以讲“给测试平台做知识库问答的 MCP 工具”。背景：多个 Agent 客户端都需要查文档、查用例、读失败日志摘要。问题：如果每个客户端各写一套检索和权限逻辑，行为不一致，也难审计。方案：我把检索、读取片段、列出最近失败记录封装成 MCP server；tools/list 暴露 search_docs、read_chunk、list_failures；每个工具有 schema、租户参数、limit 上限和只读权限；本地开发用 stdio，部署共享服务时用远程传输和鉴权；调用日志记录 request_id、tool、耗时、命中数量和错误类型。数据/效果：可以用工具成功率、p95、无效参数率、权限拒绝率衡量。反思：MCP 提高复用和标准化，但安全和稳定性仍要自己做，不能把服务器变成无限能力黑盒。""",
        points=[
            "MCP 标准化工具发现、描述和调用，不等于模型直接执行。",
            "客户端把 MCP 工具转换给模型，再转发 tools/call。",
            "本地 stdio 简单，远程传输更需要鉴权、限流和隔离。",
            "工具 schema 要窄，返回要结构化，错误要可操作。",
            "调试重点看 initialize、tools/list、tools/call 和协议日志。",
        ],
        drill=[
            dict(level="基础", q="MCP 解决的核心问题是什么？", a="MCP 解决的是 Agent 客户端如何发现和调用外部工具、资源和提示模板的问题。服务器声明工具名、描述和输入 schema，客户端连接后获取列表，再把模型的工具调用转发给服务器。它让工具可以独立开发和复用，但不代表模型直接执行工具。安全、权限和审计仍然要由客户端、服务器和部署环境共同保证。"),
            dict(level="原理", q="MCP 和函数调用是什么关系？", a="函数调用是模型输出的一种结构化意图，表示想用某个工具和参数。MCP 是客户端和工具服务器之间的协议，负责工具发现、调用和返回结果。常见流程是客户端从 MCP server 获取工具 schema，提供给模型；模型返回 tool_call 后，客户端再发 MCP tools/call。两者配合使用，但解决的问题层次不同。"),
            dict(level="实现", q="写一个 MCP 工具时要注意哪些字段？", a="工具名要稳定且语义明确，description 要说明能力边界和限制。inputSchema 要尽量窄，使用必填字段、枚举、范围和格式约束。返回值要结构化，能被客户端和模型理解。异常要转成可诊断错误，包含错误类型和字段提示，而不是只抛一段堆栈。"),
            dict(level="落地", q="本地 stdio MCP 和远程 MCP 怎么选？", a="本地 stdio 适合访问本机文件、IDE、开发工具和个人索引，部署简单，延迟低，但容易受进程环境、工作目录和 stdout 日志影响。远程 MCP 适合共享服务和集中治理，可以统一鉴权、审计和限流，但网络、租户隔离和可用性要求更高。选择时看工具资源在哪里、是否要多人复用、权限边界和运维成本。"),
            dict(level="排查", q="客户端连接 MCP 后没有工具，怎么查？", a="先看服务器进程是否正常启动，command、args、工作目录和环境变量是否正确。再看 initialize 是否成功、tools/list 是否返回工具。检查 stdout 是否被普通日志污染，因为 stdio 协议要求 stdout 是协议消息。服务器日志最好写 stderr 或文件。最后确认工具装饰器或注册代码确实执行，异常没有在启动阶段被吞掉。"),
            dict(level="取舍", q="为什么不把一个万能 execute 工具暴露成 MCP？", a="万能 execute 表面灵活，但 schema 太宽，模型容易传危险参数，权限和审计也很难做细。生产里更推荐小工具、窄 schema、明确权限和返回结构。比如 read_doc、search_docs、create_issue 分开，比 execute(command) 更可控。确实需要通用执行时，也要放在沙箱里，限制命令、路径、时间和网络。"),
            dict(level="设计", q="设计一个远程 MCP 服务给多个 Agent 使用，你会怎么保证安全和稳定？", a="我会在入口做身份认证和租户识别，对每个租户配置工具白名单、QPS、并发和 token 或结果大小限制。工具内部做参数 schema 和业务校验，访问下游时设置超时、熔断和审计。日志记录 request_id、client_id、tool、耗时、错误类型和脱敏参数。部署上用最小权限、隔离凭据和版本化发布，配合回归测试验证 tools/list 和关键 tools/call。"),
        ],
        choice=[
            dict(q="MCP 的主要作用是什么？", options=["训练大模型", "标准化工具发现和调用", "替代所有权限控制", "让模型直接访问数据库"], answer=[1], explain="MCP 标准化客户端与工具服务器之间的发现和调用。权限仍需实现，模型也不应直接访问底层资源。"),
            dict(q="MCP 工具描述通常应包含哪些内容？", options=["name", "description", "inputSchema", "任意明文密钥"], answer=[0, 1, 2], explain="工具需要名称、描述和输入 schema。密钥不应放入工具描述或配置仓库。"),
            dict(q="本地 stdio MCP 常见连接失败原因是？", options=["启动命令或工作目录错误", "stdout 被普通日志污染", "initialize 阶段异常", "因为 stdio 天然不能传 JSON"], answer=[0, 1, 2], explain="stdio 可以传 JSON 协议消息。常见问题是启动、环境、stdout 污染或初始化失败。"),
            dict(q="远程 MCP 相比本地 stdio 额外需要重点考虑什么？", options=["鉴权、租户隔离和限流", "完全不需要日志", "可以信任所有调用方", "必须把 schema 放宽"], answer=[0], explain="远程服务面对网络和多客户端，必须重点做鉴权、隔离、限流和审计。"),
        ],
        short=[
            dict(q="说明 MCP tools/list 到 tools/call 的完整流程。", points=["客户端连接并 initialize", "服务器返回能力和工具列表", "工具 schema 暴露给模型", "模型返回 tool_call", "客户端转发并回填结果"], reference="流程从客户端启动或连接 MCP server 开始，先发送 initialize 协商能力。随后客户端请求 tools/list，服务器返回工具名、描述和 inputSchema。客户端把这些工具转换成模型可理解的工具定义，随 messages 发给模型。模型若返回 tool_call，客户端取出工具名和 arguments，向 MCP server 发 tools/call。服务器校验参数、执行工具、返回 result 或 error。客户端再把结果包装成 tool message 回填给模型，进入下一轮或生成最终答案。"),
            dict(q="写 MCP 服务器时如何做安全控制？", points=["最小权限运行", "参数 schema 和业务校验", "路径/域名/租户白名单", "超时、并发和返回大小限制", "脱敏审计日志"], reference="安全要分层做。进程用最小权限运行，凭据通过环境或安全配置注入，不写入代码和日志。每个工具先做 inputSchema 校验，再做业务校验，例如路径归一化、工作区限制、域名白名单、只读 SQL、limit 上限。远程服务还要做身份认证、租户隔离、QPS 和并发限制。所有工具有超时和返回大小限制。审计日志记录 request_id、工具、耗时、错误类型和脱敏参数，既能追责又不泄露敏感信息。"),
            dict(q="如何调试一个 MCP 工具调用失败？", points=["区分连接、发现、调用和工具内部错误", "查看 initialize 和 tools/list", "检查 schema 与 arguments", "检查服务器 stderr 和审计日志", "构造最小 JSON-RPC 用例"], reference="调试时先分层。连接失败看进程是否启动、命令参数、工作目录和环境变量。工具不可见看 initialize 与 tools/list 是否成功，stdout 是否被普通日志污染。调用失败看模型传入 arguments 是否符合 inputSchema，字段名、枚举和范围是否正确。服务器内部错误看 stderr、审计日志、下游依赖耗时和异常类型。最后构造一个最小 tools/call 请求绕过模型直接调用，确认是协议、schema、模型参数还是工具逻辑的问题。"),
        ],
        labs=["lab-mcp-jsonrpc", "lab-tool-schema"],
        related=["agent-protocols", "harness-extend", "harness-tools", "arch-tool-gateway"],
    ),
]
