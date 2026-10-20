SECTIONS = [
    dict(
        id="harness-hooks", course="harness", order=7,
        title="Hooks 与确定性逻辑",
        summary="把稳定规则放到模型外强制执行。",
        md="""### 一句话与核心概念
Hooks 是挂在 Agent 生命周期关键事件上的确定性管线。它不等模型“想起来”再执行，而是在会话开始、工具调用前、工具返回后、文件写入后、最终回复前等固定点自动运行。面试里要把它讲成 harness 的控制面：模型负责语义推理，Hook 负责可判定规则、审计、拦截和标准化。

典型事件可以分为四类。第一类是会话事件，如 SessionStart、UserPromptSubmit、Stop，用于加载规则、打审计点、发送通知。第二类是模型事件，如 AssistantMessage、ToolCallProposed，用于抽取计划、检查输出格式。第三类是工具事件，如 PreToolUse、PostToolUse，用于拦截危险命令、改写参数、解析工具结果。第四类是文件事件，如 FileWrite、PatchApplied，用于格式化、静态检查、生成索引。

Hooks 的价值不是“多跑几个脚本”，而是把非确定性的 Agent 循环切出确定性边界。例如禁止访问密钥文件、写入后必须格式化、测试失败必须把报告结构化回填，这些规则不需要创造力。把它们交给模型，会遇到遗忘、被提示注入绕过、解释不一致和审计困难。写成 Hook，输入输出固定，失败可重放，责任边界清楚。

### 原理：事件流、拦截语义与确定性边界
一个 Hook 系统可以抽象成事件总线加规则链。Agent 每一步产生事件 event，harness 按事件类型找到匹配的 handler，依次执行。handler 返回 decision，常见值是 allow、deny、modify、append_observation、notify。Pre 阶段可以阻断动作或改参数；Post 阶段不能改变已发生的外部事实，但可以改写返回给模型的观察、触发补救动作或记录审计。

伪代码如下：

```python
def dispatch(event, context):
    handlers = registry.match(event.type, event.tool, event.paths)
    current = event
    audit = []
    for h in sorted(handlers, key=lambda x: x.priority):
        result = h.run(current, context)
        audit.append(result.to_log())
        if result.decision == "deny":
            return HookResult(blocked=True, reason=result.reason, audit=audit)
        if result.decision == "modify":
            current = current.with_update(result.patch)
        if result.decision == "append_observation":
            context.observations.append(result.message)
    return HookResult(event=current, audit=audit)
```

这里有三个核心语义。第一是顺序。权限拦截通常要在参数改写前或至少在最终参数上再做一次，否则可能出现“先放行、后改成危险命令”。第二是幂等。Post Hook 可能因进程重试重复执行，通知、写日志、格式化应带 event_id 或内容摘要，避免重复副作用。第三是可观察。每个 Hook 要记录 event_id、输入摘要、决策、耗时、错误和修改摘要，不能只在屏幕上打印。

复杂度主要取决于匹配规则数和 Hook 执行成本。简单匹配是 O(R)，R 是规则数；可用事件类型、工具名、路径前缀建索引降到近似 O(k)。真正昂贵的是外部命令，如格式化和测试，所以要区分同步阻塞 Hook 与异步通知 Hook。安全拦截必须同步，通知和指标上报可以异步。

### 工程实现要点
实现时先定义稳定的事件结构，而不是先写脚本。事件至少包含 type、session_id、turn_id、tool_name、args、paths、cwd、env_whitelist、timestamp、actor、request_id。Hook 返回结构至少包含 decision、reason、patch、observation、evidence、duration_ms。不要让 Hook 直接随意读写全局状态，否则调试会很困难。

一个可落地的数据结构如下：

```python
from dataclasses import dataclass, field

@dataclass
class HookEvent:
    type: str
    tool: str | None
    args: dict
    paths: list[str]
    session_id: str
    turn_id: str

@dataclass
class HookDecision:
    action: str              # allow / deny / modify / observe
    reason: str = ""
    patch: dict = field(default_factory=dict)
    observation: str = ""

def block_secret_file(event: HookEvent) -> HookDecision:
    if event.type == "PreToolUse" and any(p.endswith(".env") for p in event.paths):
        return HookDecision("deny", "secret-like file is not allowed")
    return HookDecision("allow")
```

配置层要支持匹配条件、优先级、超时和失败策略。安全 Hook 建议 fail closed，即 Hook 自己异常时也拒绝高风险动作；格式化 Hook 可以 fail open，但要把失败回填给模型。参数修改要保留前后 diff，不能静默改写。Hook 还要区分“硬规则”和“建议规则”：硬规则直接 deny，建议规则追加 observation，让模型选择修复。

常见 Hook 包括：PreToolUse 拦截 rm、curl 上传、越权路径；PreToolUse 给命令注入超时；PostToolUse 解析 pytest、lint、构建日志；FileWrite 后按后缀运行格式化；Stop 前检查最终回复是否包含验证范围。对于测试开发背景，可以强调“测试报告解析 Hook”：工具只返回长日志时，模型容易漏读；Hook 抽取失败用例、错误栈、产物路径，再把结构化摘要给模型，下一步修复更稳定。

### 生产落地：方案、踩坑与排查
问题一：Hook 偶发把合法命令拦掉。现象是 Agent 反复请求同一个动作，但都被 deny。原因通常是规则过粗，例如按字符串包含 rm 拦截，误伤 npm run build:remove-cache。定位要看 Hook 审计日志里的规则 id、命令原文、解析后的 argv 和命中条件。解决方式是先把 shell 命令解析成 argv，再按命令、参数、路径做结构化匹配；高风险规则保留 deny，模糊规则改为 ask 或 observe。

问题二：自动格式化导致模型困惑。现象是模型刚写完文件，随后 diff 和它预期不一致，甚至把格式化结果改回去。原因是 PostWrite Hook 静默改写了文件，却没有把变更摘要回填。定位看文件修改时间、Hook duration、格式化器输出和模型下一轮读取内容。解决方式是把格式化作为显式 observation 返回：“已格式化这些文件，语义未变”；如果格式化失败，返回错误和命令，而不是吞掉。

问题三：Hook 自身拖慢循环。现象是简单任务每轮都很慢，用户以为模型慢。原因可能是每次工具后都跑全量测试、全仓扫描或网络通知。定位看 per-hook latency、调用次数、P95 耗时和失败重试次数。解决方式是按事件缩小触发范围，只对变更文件运行增量检查；耗时动作改为用户确认或后台任务；给 Hook 加超时和熔断。

问题四：Hook 产生不可回滚副作用。现象是任务回滚了代码，但消息、工单或外部系统已被通知。原因是通知 Hook 被放在中间事件，且没有幂等键和撤销语义。定位看 event_id 与外部 request_id 是否绑定。解决方式是把外部副作用尽量放在最终确认阶段，带幂等 key，记录 receipt，并在最终报告中说明不可自动撤销的动作。

### 取舍与对比
| 方案 | 优点 | 风险 | 适合场景 |
| --- | --- | --- | --- |
| 靠提示词要求模型执行规则 | 成本低，改动快 | 容易忘，易被绕过，难审计 | 软性偏好、临时任务 |
| Hook 强制执行 | 稳定，可重放，可审计 | 增加延迟和调试复杂度 | 安全、格式化、校验、审计 |
| 权限系统拦截 | 决策集中，用户可理解 | 对上下文语义理解有限 | 文件、命令、网络边界 |
| 工具内部校验 | 离执行点最近 | 各工具重复实现，视野窄 | 单个工具参数合法性 |

判断一条规则是否该做成 Hook，可以问四个问题：是否稳定、是否可判定、是否跨任务复用、误判成本是否可控。如果答案大多为是，就放进 Hook；如果需要理解产品意图、需求优先级或用户偏好，就不要硬编码。模型变强后，Hook 仍然必要，因为它解决的不是智力问题，而是工程一致性和安全边界。

### 结合项目怎么讲
可以用“用 Agent 自动生成和修复自动化用例”的通用项目来讲。背景：团队希望 Agent 根据需求和失败日志生成测试代码，并自动运行验证。问题：模型经常忘记格式化、漏读测试失败摘要，偶尔尝试访问不该读的配置文件。方案：在 harness 中加入 PreToolUse、PostToolUse、FileWrite 三类 Hook；PreToolUse 做路径和危险命令拦截，FileWrite 按文件类型运行格式化，PostToolUse 解析测试报告并回填失败用例、错误栈和产物路径。数据/效果：可以讲“经验上减少了人工提醒次数，失败定位从读长日志变成读结构化摘要”，不要编造固定百分比。反思：Hook 不能替代模型规划，规则也不能无限堆；后续要按命中率、误拦截率和耗时持续清理。""",
        points=[
            "Hook 是事件驱动的确定性管线，不依赖模型主动调用。",
            "Pre Hook 可拦截或改参数，Post Hook 更适合解析、审计和回填观察。",
            "稳定、可判定、跨任务复用的规则适合写成 Hook。",
            "Hook 要有优先级、超时、失败策略、幂等键和审计日志。",
            "不要把复杂业务语义硬编码进 Hook。",
        ],
        drill=[
            dict(level="基础", q="什么是 Hooks？它和工具调用有什么区别？", a="Hooks 是 harness 在固定生命周期事件上自动执行的逻辑，例如工具调用前、工具返回后、文件写入后。工具调用通常由模型主动选择，模型可能忘记或选错；Hook 不依赖模型选择。Hook 适合执行稳定规则，如拦截、格式化、校验、通知和审计。工具适合提供能力，如读文件、跑命令、查资料。面试时要强调 Hook 是控制面，不是业务智能本身。"),
            dict(level="原理", q="PreToolUse 和 PostToolUse 的语义差异是什么？", a="PreToolUse 发生在工具真正执行之前，所以可以拒绝动作、要求确认或修改参数。PostToolUse 发生在动作之后，外部事实已经产生，一般不能假装没发生。Post 更适合解析结果、记录审计、追加观察和触发补救。安全边界要优先放在 Pre 阶段，Post 阶段只能做检测和收敛。两者都要记录 event_id、输入摘要、决策和耗时。"),
            dict(level="实现", q="如果让你实现 Hook 管线，关键数据结构有哪些？", a="我会先定义 HookEvent，包含事件类型、工具名、参数、路径、会话 id、轮次 id、当前目录和调用者。再定义 HookDecision，包含 allow、deny、modify、observe 等动作，以及原因、参数补丁和回填消息。Registry 按事件类型、工具名和路径前缀匹配 handler，并支持优先级。执行结果要写审计日志，包含规则 id、命中条件、耗时和异常。安全 Hook 的失败策略通常是 fail closed，普通提示类 Hook 可以 fail open。"),
            dict(level="落地", q="哪些规则不应该交给模型，而应该写成 Hook？", a="稳定且可判定的规则应该写成 Hook，比如禁止读取密钥文件、危险命令拦截、写入后格式化、测试结果结构化、命令超时、最终报告检查。模型适合判断需求意图、错误根因和下一步修复策略，不适合保证每次都执行固定动作。把固定规则交给模型会有遗忘和提示注入风险，也不方便审计。Hook 的输出可重放、可统计，适合做生产控制。"),
            dict(level="排查", q="Hook 误拦截合法命令时，你怎么定位？", a="先看审计日志里的 event_id、规则 id、命令原文、解析后的 argv、路径列表和命中条件。再确认是字符串误匹配、路径规范化问题，还是参数改写后没有二次校验。必要时用同一事件重放 Hook 管线，比较每个 handler 的决策。解决上要把模糊字符串规则改成结构化匹配，给高风险规则保留 deny，给低置信规则改成 ask 或 observe。还要补一条回归样例，避免再次误伤。"),
            dict(level="取舍", q="Hook 越多越安全吗？", a="不是。Hook 多会增加延迟、失败点和理解成本，也可能让模型拿到过多噪声观察。安全相关的硬边界应该保留，但格式化、通知、报告解析要按触发范围和耗时控制。设计上要统计命中率、误拦截率、平均耗时和失败率，定期删除低价值 Hook。好的 Hook 系统是少而硬：关键规则强制执行，软偏好不要到处拦截。"),
            dict(level="设计", q="设计一个用于自动化用例生成 Agent 的 Hook 体系。", a="我会分四层：会话层加载项目规则和预算，PreToolUse 层做路径、命令、网络和权限拦截，PostToolUse 层解析测试、构建和 lint 输出，FileWrite 层做格式化和增量静态检查。每个 Hook 都要有规则 id、优先级、超时和失败策略。安全 Hook 同步阻塞，通知和指标异步执行。所有决策写入审计日志，并把对模型有帮助的信息作为结构化 observation 回填。最后用误拦截率、修复轮数和每轮耗时评估效果。"),
        ],
        choice=[
            dict(q="关于 Hook 和工具的关系，哪项最准确？", options=["Hook 是模型主动选择的工具", "Hook 是固定事件上由 harness 自动执行的逻辑", "Hook 只能用于发送通知", "Hook 不需要审计日志"], answer=[1], explain="B 正确。工具通常由模型选择，Hook 由事件触发。Hook 可用于拦截、改写、解析和通知，不只通知；生产中必须记录审计。"),
            dict(q="哪些逻辑适合放入 Hook？（多选）", options=["禁止读取密钥文件", "写 Python 文件后运行格式化", "判断需求是否应该延期", "解析测试报告并回填失败摘要"], answer=[0, 1, 3], explain="A、B、D 都是稳定、可判定、可复用规则。C 涉及业务优先级和语义判断，不应硬编码为 Hook。"),
            dict(q="PreToolUse 最适合做什么？", options=["在工具执行前拦截危险参数", "修改已经发出的外部通知", "总结整段会话", "替代模型做全部规划"], answer=[0], explain="PreToolUse 发生在执行前，适合拦截或改参数。已经发生的外部副作用不能靠 Pre 修改；总结和规划不是它的核心职责。"),
            dict(q="Hook 设计中最容易被忽略但很关键的是哪项？", options=["给每个 Hook 起很长的名字", "幂等、超时、失败策略和审计", "让所有 Hook 都异步执行", "把所有业务判断都写成规则"], answer=[1], explain="B 是生产可运维的关键。名字长没有本质价值；安全 Hook 不能都异步；业务判断全部规则化会僵化且误伤。"),
        ],
        short=[
            dict(q="简述为什么有些规则不该交给模型执行。", points=["指出模型输出非确定且可能遗忘", "说明提示注入和审计困难", "举出格式化、权限、超时等例子", "说明 Hook 的可重放和可统计价值"], reference="有些规则本质上不需要智能，只需要稳定执行。比如禁止读取密钥文件、命令超时、写入后格式化、测试报告解析，这些规则可判定、跨任务复用，交给模型反而会出现忘记执行、理解偏差或被提示注入诱导的问题。模型还可能用自然语言解释自己做了，但没有真实执行，审计时很难复现。写成 Hook 后，每次在固定事件触发，输入、决策、耗时和结果都能记录，失败也能重放。模型继续负责语义推理和修复策略，Hook 负责工程边界和一致性。"),
            dict(q="设计 Hook 管线时如何处理失败策略？", points=["区分安全 Hook 与辅助 Hook", "说明 fail closed 和 fail open", "包含超时、熔断、审计", "说明对模型回填错误信息"], reference="Hook 失败不能一刀切。安全类 Hook 例如权限、危险命令、敏感路径检查，失败时应该 fail closed，宁可阻断也不要放过高风险动作。辅助类 Hook 例如格式化、通知、报告美化，可以 fail open 或降级，但必须把失败作为 observation 回填给模型或写入审计。所有 Hook 都要有超时，避免卡住主循环；连续失败要熔断，避免每轮重复拖慢。审计日志要记录规则 id、异常、输入摘要和失败策略，方便之后重放定位。"),
            dict(q="如何排查 Hook 导致 Agent 循环变慢？", points=["查看 per-hook latency 和调用次数", "区分同步阻塞与异步 Hook", "检查是否全量扫描或重复运行测试", "用触发条件、增量检查、超时优化"], reference="先不要猜模型慢，要把每轮耗时拆开。查看每个 Hook 的调用次数、平均耗时、P95 耗时、失败重试次数和触发事件。若发现文件写入后总是全仓扫描或每次工具调用后都跑全量测试，就说明触发范围太宽。安全拦截必须同步，但通知、指标上报可以异步。优化方式包括只对变更文件运行检查，按后缀和路径过滤，给外部命令设置超时，对连续失败的 Hook 熔断，并把耗时 Hook 改成用户确认后运行。"),
        ],
        labs=["lab-hooks", "lab-permission"],
        related=["harness-tools", "harness-permission", "dev-testing"],
    ),

    dict(
        id="harness-extend", course="harness", order=8,
        title="扩展机制：MCP、Skills、命令与插件",
        summary="扩展能力越开放，边界成本越高。",
        md="""### 一句话与核心概念
扩展机制让 Coding Agent 不把所有能力写死在内核里，而是通过协议、配置和插件接入外部工具、知识、工作流和界面能力。常见形态包括 MCP 服务器、Skills、自定义命令和插件。面试里要讲清两件事：扩展提供能力发现和能力调用；扩展也会带来上下文膨胀、权限扩大、供应链风险和调试复杂度。

MCP 可以理解为一种面向 Agent 的工具和资源接入协议。客户端连接服务器，完成初始化，发现 tools、resources、prompts，再按 schema 调用工具。Skills 更偏“可复用操作说明和附属资源”，通常包含何时使用、约束、脚本、模板和示例。自定义命令是把高频工作流封装成入口，比如“生成变更说明”“跑指定测试并总结”。插件则更宽，可能扩展 UI、工具、索引、权限或上下文源。

不要把扩展理解为“越多越强”。对模型来说，每个扩展都可能增加工具选择空间、schema token、系统规则和攻击面。好的 harness 会延迟加载扩展：先根据用户请求、仓库文件、显式配置和少量路由规则判断候选扩展，再把必要的说明和工具暴露给模型，而不是一次性塞进上下文。

### 原理：能力发现、延迟加载与信任边界
扩展接入的数据流通常是：配置发现 -> 元数据读取 -> 安全筛选 -> 能力注册 -> 按需注入上下文 -> 调用执行 -> 结果规范化。MCP 类扩展多一层远程或本地进程通信，自定义命令和 Skills 多一层文件系统加载，插件多一层生命周期管理。

延迟加载的核心是把“可用能力全集”和“当前轮暴露能力集”分开。能力全集可能有很多工具，但当前轮只暴露与任务相关且权限允许的工具。可以用一个简单打分：score = intent_match + repo_match + explicit_mention - risk_penalty - token_cost。分数超过阈值才加载详细说明；否则只保留短元数据。

伪代码如下：

```python
def select_extensions(user_text, repo_signals, registry, budget):
    candidates = []
    for ext in registry.list_metadata():
        score = 0
        score += match_intent(user_text, ext.triggers)
        score += match_repo(repo_signals, ext.file_patterns)
        score -= ext.risk_level * 2
        score -= estimate_tokens(ext.full_prompt) / 1000
        if score > ext.threshold:
            candidates.append((score, ext))
    chosen = fit_budget(sorted(candidates, reverse=True), budget)
    return [load_full_extension(e) for _, e in chosen]
```

MCP 的关键是 schema 契约。工具名、描述、输入 JSON Schema、错误码和返回结构会直接影响模型是否能正确调用。描述太短，模型不知道何时用；描述太长，缓存和上下文成本上升。资源读取也要分层：列表操作只返回 uri、标题、摘要和大小；真正内容在模型需要时再读。这样既省 token，也减少敏感信息暴露。

信任边界要分清。扩展的说明文本本身可能包含提示注入，外部资源也可能要求模型忽略系统规则。harness 不能把扩展内容等同系统指令。扩展最多提供工具说明和任务知识，不能覆盖权限、沙箱和用户目标。插件代码如果能执行本地命令，更要有签名、来源、版本锁定和最小权限。

### 工程实现要点
工程上建议把扩展注册表设计成 metadata-first。Metadata 小而稳定，包含 id、kind、version、description、triggers、capabilities、risk_level、token_cost、entrypoint、permissions。Full spec 只有被选中时才加载，包含完整工具 schema、使用说明、示例和脚本路径。这样有利于 prompt caching，因为稳定前缀可以只放已排序的短元数据，变化内容放后面。

MCP 服务器接入要处理初始化、能力列表、调用、超时和错误映射。不要让模型直接面对底层异常，应规范化为 tool_error，包含 code、message、retryable、evidence。工具参数必须在客户端二次校验，因为模型给的 JSON 可能缺字段、多字段或类型错。对返回值要限制大小，长结果写成 artifact，再返回摘要和路径。

一个工具注册结构可以这样写：

```python
class ExtensionRegistry:
    def __init__(self):
        self.meta = {}
        self.loaded = {}

    def register(self, meta):
        assert meta["id"] not in self.meta
        self.meta[meta["id"]] = meta

    def load(self, ext_id):
        if ext_id not in self.loaded:
            spec = read_and_validate(self.meta[ext_id]["entrypoint"])
            self.loaded[ext_id] = sandbox_wrap(spec)
        return self.loaded[ext_id]
```

Skills 的实现重点是触发边界和资源组织。Skill 文档要写“何时使用”和“不要用于什么”，否则路由会泛化。脚本要可独立运行，输入输出稳定。自定义命令要避免把隐式环境写死，参数、默认值、工作目录和权限都要显式。插件要有启用、禁用、升级和回滚机制；任何自动更新都要考虑供应链风险。

### 生产落地：方案、踩坑与排查
问题一：工具太多导致模型选错。现象是明明有专用工具，模型却调用通用 shell，或在相似工具之间反复试错。原因是一次性暴露了太多扩展，描述重叠，schema 命名不清。定位看每轮 tools 列表、模型选择轨迹、失败工具名和 token 占用。解决方式是延迟加载，合并重复工具，改清描述，把高风险工具放到显式触发后才暴露。

问题二：扩展破坏 prompt caching。现象是相同仓库相似任务，缓存命中率很低。原因常见于扩展列表顺序不稳定、每次注入动态时间戳、工具 schema 带随机字段、插件版本浮动。定位看请求前缀 diff、工具列表排序、schema 摘要和缓存命中长度。解决方式是稳定排序，把动态字段放在后缀，metadata 与 full spec 分离，版本锁定并记录 digest。

问题三：MCP 服务器慢或不稳定。现象是 Agent 卡在工具列表或工具调用，模型反复重试。原因可能是服务器启动慢、stdio 管道阻塞、网络超时、返回结果过大。定位看 initialize 耗时、tools/list 耗时、tools/call 耗时、stderr、退出码和返回字节数。解决方式是进程池预热、工具列表缓存、调用超时、结果分页和大小上限；可重试错误才重试，不可重试错误直接回填。

问题四：扩展带来安全越权。现象是一个看似只读的 Skill 实际调用脚本写文件或访问网络。原因是扩展说明和真实权限不一致，或者插件拿到了过大的环境权限。定位看扩展声明权限、实际系统调用、文件 diff、网络日志和审计事件。解决方式是最小权限、沙箱执行、环境变量白名单、来源校验和显式用户授权；不要因为扩展来自本地文件就默认可信。

### 取舍与对比
| 扩展形态 | 主要价值 | 成本 | 适合内容 |
| --- | --- | --- | --- |
| MCP 服务器 | 标准化工具与资源接入，跨客户端复用 | 进程、协议、权限、超时复杂 | 外部系统、数据库、浏览器、检索 |
| Skills | 复用操作流程和领域经验 | 触发误判、上下文占用 | 特定任务 SOP、模板、脚本 |
| 自定义命令 | 把高频流程变成短入口 | 参数设计和环境依赖 | 生成报告、跑测试、发布检查 |
| 插件 | 深度扩展产品能力 | 供应链和兼容性风险最高 | UI、索引、权限、工具网关 |

扩展设计的核心取舍是开放性和可控性。开放扩展让 Agent 快速接入新能力，但会扩大工具选择空间和攻击面。保守扩展更安全，但容易把所有需求压回核心代码。一个实用原则是：协议层保持通用，注册层做最小元数据，运行层做沙箱和审计，上下文层只注入当前任务必要部分。

### 结合项目怎么讲
可以用“给测试平台做知识库问答和自动操作助手”的通用场景。背景：团队希望 Agent 既能回答平台使用问题，又能调用工具创建测试任务、查询执行结果。问题：如果把所有 API 文档、操作流程和工具 schema 都塞进 prompt，模型上下文爆炸，还会选错工具。方案：把查询、任务管理、报告读取做成 MCP 工具；把常见排查流程做成 Skills；把“生成回归报告”做成自定义命令；注册表只给模型稳定摘要，命中意图后再加载完整 spec。数据/效果：可以讲“同类问题复用同一套工具契约，失败能从工具错误码定位”，不要声称所有问题都自动解决。反思：扩展不是越多越好，要持续统计工具使用率、误触发率、权限申请次数和 token 成本，低价值扩展要下线或合并。""",
        points=[
            "扩展把外部能力接入 harness，但会增加上下文、权限和供应链成本。",
            "MCP 偏工具与资源协议，Skills 偏任务流程和可复用经验。",
            "延迟加载能减少工具选择噪声和缓存失效。",
            "扩展内容不能覆盖系统规则、权限和用户目标。",
            "工具 schema、错误码、返回大小和超时是工程成败关键。",
        ],
        drill=[
            dict(level="基础", q="Coding Agent 的扩展机制通常包括哪些形态？", a="常见有 MCP 服务器、Skills、自定义命令和插件。MCP 偏标准化工具、资源和提示模板接入；Skills 偏可复用操作说明、脚本和模板；自定义命令把高频工作流封装成入口；插件可以扩展 UI、工具、索引或权限。它们都让核心 harness 不必内置所有能力。区别在于接入深度、上下文成本和安全边界不同。"),
            dict(level="原理", q="为什么扩展要做延迟加载？", a="因为扩展全集往往很大，一次性暴露会增加 token、破坏缓存，也让模型在相似工具之间选错。延迟加载把短元数据和完整说明分开，先根据用户意图、仓库信号和显式提及选择候选，再注入完整 schema。这样能降低上下文噪声，也能把高风险工具放到需要时再授权。它还利于 prompt caching，因为稳定前缀更短、更固定。"),
            dict(level="实现", q="接入 MCP 工具时，客户端要做哪些校验？", a="客户端要在初始化后校验服务器返回的工具名、描述和 JSON Schema，避免重复名和非法 schema。模型给出的参数要按 schema 二次校验，不能直接传给服务器。调用要有超时、最大返回大小、错误码映射和重试策略。返回长内容时应转成 artifact 或分页，只把摘要给模型。所有调用还要经过权限和审计，不能因为是 MCP 工具就绕过本地边界。"),
            dict(level="落地", q="Skill 文档怎么写才不容易误触发？", a="Skill 要明确写触发条件，也要写不要用于什么场景。描述应包含任务类型、输入要求、输出产物和风险边界，而不是泛泛写‘提升效率’。脚本和模板要有稳定路径和参数说明。示例要覆盖正例和反例，让路由能区分相近任务。生产中还要统计触发次数、成功率和人工纠正次数，发现泛化过度就收窄触发规则。"),
            dict(level="排查", q="模型总是选错扩展，你会怎么查？", a="先记录每轮实际暴露的扩展列表，而不是只看注册表。检查工具描述是否重叠、名称是否含糊、schema 是否过长或缺少关键约束。再看用户请求到扩展路由的打分、显式触发词和仓库信号。也要看是不是高风险工具被过早暴露，吸引模型尝试。解决上可以合并重复工具、优化描述、延迟加载、提高阈值，必要时让模型先选择能力类别再展开具体工具。"),
            dict(level="取舍", q="扩展开放性和安全性怎么平衡？", a="我会把扩展分层管理：元数据可以广泛发现，完整说明按需加载，执行必须经过权限和沙箱。低风险只读工具可以自动允许，高风险写操作、网络访问和外部副作用要确认或禁止。扩展来源要校验，版本要锁定，能力要最小化。开放性体现在协议和生态，安全性体现在运行时边界和审计。不能为了接入方便把环境变量、文件系统和网络全部开放给插件。"),
            dict(level="设计", q="设计一个支持 MCP、Skills 和自定义命令的扩展系统。", a="我会设计统一注册表，保存 id、kind、版本、触发条件、能力、风险等级、token 成本和入口。路由层根据用户意图、仓库信号和预算选择扩展，先加载 metadata，再按需加载 full spec。执行层对 MCP 调用、Skill 脚本和自定义命令统一走权限、超时、返回大小限制和审计。上下文层把工具 schema 稳定排序，并把动态内容放后缀。运维层统计使用率、失败率、误触发率和缓存命中，支持禁用、升级和回滚。"),
        ],
        choice=[
            dict(q="关于 MCP、Skills、自定义命令的说法，哪项正确？", options=["MCP 主要用于标准化工具和资源接入", "Skills 通常只是一段模型闲聊提示，没有脚本或模板", "自定义命令必须绕过权限系统", "插件越多越不会影响上下文"], answer=[0], explain="A 正确。Skills 可包含说明、脚本、模板和示例；自定义命令仍要走权限；插件增多会增加上下文和选择成本。"),
            dict(q="延迟加载扩展的收益有哪些？（多选）", options=["减少无关 schema 占用 token", "降低模型选错工具的概率", "让高风险能力按需授权", "保证所有工具都一定成功"], answer=[0, 1, 2], explain="A、B、C 是延迟加载的直接收益。它不能保证工具成功，工具仍可能超时、参数错误或外部服务失败。"),
            dict(q="扩展内容包含“忽略之前规则”时，harness 应该怎么处理？", options=["把它当系统指令执行", "只把它视为不可信内容，不允许覆盖权限和用户目标", "自动删除整个仓库", "让模型自行决定是否覆盖系统规则"], answer=[1], explain="B 正确。扩展、资源和工具返回都可能包含提示注入，不能覆盖系统规则、权限边界和用户目标。"),
            dict(q="MCP 工具返回超长结果时，较好的做法是？", options=["完整塞回模型上下文", "直接丢弃", "保存为 artifact，返回摘要、大小和引用", "让模型猜结果"], answer=[2], explain="C 能控制 token，并保留可追溯证据。完整塞回会浪费上下文，丢弃或猜测都会损害正确性。"),
        ],
        short=[
            dict(q="解释扩展机制带来的上下文成本和安全成本。", points=["说明工具 schema 和说明会占 token", "说明工具过多导致选择噪声", "说明权限扩大和供应链风险", "提出延迟加载、最小权限、审计"], reference="扩展机制让 Agent 接入更多工具和流程，但每个扩展的描述、schema、示例和规则都可能进入上下文，占用 token 并影响 prompt caching。工具太多时，模型会在相似能力之间选错，甚至用高风险工具替代低风险工具。安全上，扩展可能读取文件、访问网络、执行脚本，也可能携带提示注入或供应链风险。工程上应使用 metadata-first 和延迟加载，只注入当前任务需要的能力；执行时走最小权限、沙箱、超时、返回大小限制和审计日志。"),
            dict(q="如何设计扩展注册表的元数据？", points=["包含 id、kind、version、description", "包含 triggers、capabilities、risk_level", "包含 token_cost、entrypoint、permissions", "区分 metadata 和 full spec"], reference="扩展注册表不应只存一个入口路径。元数据至少包含 id、类型、版本、短描述、触发条件、能力标签、风险等级、预计 token 成本、入口和所需权限。短元数据用于路由和展示，完整 spec 包含工具 schema、详细说明、示例、脚本和模板，只有命中后才加载。这样能保持稳定前缀，减少无关上下文，也方便审计和禁用。版本、来源和 digest 也应记录，便于升级回滚和供应链排查。"),
            dict(q="MCP 服务器调用失败时如何排查？", points=["区分 initialize、tools/list、tools/call 阶段", "检查超时、stderr、退出码、返回大小", "校验参数 schema 和错误码", "设置缓存、预热、分页和重试策略"], reference="排查 MCP 失败要先分阶段。initialize 慢通常是服务器启动或依赖加载问题；tools/list 失败可能是协议不兼容或 schema 非法；tools/call 失败可能是参数错误、外部服务超时或返回过大。需要查看耗时、stderr、退出码、请求参数、错误码和返回字节数。客户端应对参数做 schema 校验，对调用设置超时和大小上限，对工具列表做缓存。只有 retryable 错误才重试，不可重试错误要结构化回填给模型，避免盲目循环。"),
        ],
        labs=["lab-mcp-jsonrpc", "lab-tool-schema"],
        related=["dev-mcp", "harness-tools", "harness-context", "agent-protocols"],
    ),

    dict(
        id="harness-headless", course="harness", order=9,
        title="无头模式、SDK 与 CI 集成",
        summary="非交互 Agent 要先设计隔离和退出语义。",
        md="""### 一句话与核心概念
无头模式是让 Agent 在没有交互式终端或 IDE 的情况下运行：输入来自命令行参数、配置、任务队列或 CI 事件，输出是结构化结果、补丁、日志和退出码。SDK 则把同一套能力嵌入到应用或流水线里。面试里要强调：无头不是“把聊天界面关掉”，而是把确认、权限、产物、失败和隔离都显式协议化。

交互模式下，模型遇到高风险操作可以问用户；无头模式下不能卡住等待确认，所以必须预设权限策略，例如 allow read、ask 写操作不可用、deny 网络、只允许指定目录。输出也不能只是一段自然语言，要有 JSON、JUnit、SARIF、patch、artifact manifest 或固定字段，方便 CI 消费。退出码要表达机器可判断的状态：成功、发现问题但未修复、权限阻断、测试失败、内部错误。

CI 中跑 Coding Agent 的价值是自动修复小缺陷、生成测试、解释失败、做代码审查建议。风险也很集中：仓库权限、密钥暴露、供应链脚本、外部副作用、成本失控和不稳定提交。因此生产方案通常要求短时凭证、最小权限、临时工作区、网络限制、产物留存和人工合入门槛。

### 原理：非交互运行的数据流、状态机与退出码
无头 Agent 可以抽象为有限状态机：prepare -> plan -> act -> verify -> emit -> cleanup。prepare 拉取输入、创建临时工作区、加载权限预设；plan 生成计划但不能无限展开；act 调用工具修改文件或运行命令；verify 执行测试或静态检查；emit 输出结构化结果和产物；cleanup 清理临时资源。任何阶段失败都要映射到稳定错误类别。

伪代码如下：

```python
def run_headless(task, policy):
    session = prepare_workspace(task, policy)
    try:
        for step in range(policy.max_steps):
            action = model_next(session.messages, tools=policy.tools)
            decision = permission_check(action, policy)
            if decision.blocked:
                return emit("blocked", reason=decision.reason)
            obs = execute(action, timeout=policy.timeout)
            session.add_observation(obs)
            if is_done(session):
                break
        verdict = verify(session, policy.verify_cmds)
        return emit(verdict.status, artifacts=session.artifacts)
    finally:
        cleanup(session, policy.cleanup)
```

与交互模式相比，无头模式多了三个约束。第一，所有需要用户判断的分支都要提前变成 policy。第二，所有给人看的过程都要变成 artifact 和结构化字段。第三，所有外部副作用都要在隔离环境里执行，并能在报告中解释。复杂度上，模型轮数乘以工具调用成本仍是主体，但 CI 还要加上环境准备、依赖安装和验证命令。若每个 PR 都跑 Agent，成本和排队时间会很明显，所以要设置触发条件和预算。

### 工程实现要点
接口设计要先定义输入输出契约。输入可以包括 repo、base_ref、head_ref、task_text、changed_files、policy_id、budget、allowed_tools、secrets_policy、artifact_dir。输出建议固定为 result.json，包含 status、summary、changed_files、tests、permissions、cost、artifacts、warnings、error。自然语言总结可以作为 summary，但不能替代结构化字段。

权限预设要可审计。常见预设包括 read_only、edit_workspace、test_only、repair_with_tests。read_only 只允许读取和分析；edit_workspace 允许改工作区文件但不能网络；test_only 允许运行白名单测试命令；repair_with_tests 允许改文件、跑测试、生成 patch，但禁止发布、删除远程资源和读取未授权密钥。预设要和沙箱一起生效，不能只靠提示词。

一个结果结构示例：

```python
result = {
    "status": "failed",          # passed / failed / blocked / error
    "summary": "tests still failing after attempted repair",
    "changed_files": ["tests/test_api.py"],
    "checks": [{"cmd": "pytest tests/test_api.py", "exit_code": 1}],
    "permissions": [{"action": "network", "decision": "deny"}],
    "artifacts": [{"path": "artifacts/log.txt", "kind": "log"}],
    "cost": {"input_tokens": 0, "output_tokens": 0},
}
```

SDK 集成要注意可取消、可恢复和可观测。调用方需要 request_id 关联日志，需要 stream events 展示进度，需要 cancel API 停止长任务，需要 webhook 或回调接收结果。CI 中要固定依赖、固定基础镜像、清理工作区，并把模型生成的补丁作为候选产物，而不是默认直接合入主分支。

### 生产落地：方案、踩坑与排查
问题一：CI 任务卡住不退出。现象是流水线一直 running，没有结构化结果。原因可能是模型等待用户确认、命令无超时、工具进程阻塞或网络请求挂起。定位看 step event、最后一个工具调用、子进程树和超时配置。解决方式是无头模式禁用 ask，全部映射为 allow/deny；每个工具设置超时；总任务设置 max_steps 和 wall time；finally 中强制 emit error result。

问题二：Agent 在 CI 中读到密钥或越权访问。现象是日志里出现敏感变量名、工具尝试访问家目录或网络。原因是 CI 环境变量过多、工作区挂载过宽、权限预设没有硬隔离。定位看环境变量白名单、文件访问审计、网络连接日志和权限决策。解决方式是短时最小权限凭证、环境变量白名单、临时容器、只挂载仓库目录、禁用不必要网络，并对日志做脱敏。

问题三：无头输出人能看懂但机器不能消费。现象是流水线下游不知道该失败还是放行，只能解析自然语言。原因是没有定义 result schema 和退出码。定位看产物目录是否有 result.json、字段是否稳定、状态枚举是否完整。解决方式是固定 schema，状态只用 passed、failed、blocked、error 等有限枚举；自然语言只做补充；退出码与状态一一映射。

问题四：自动修复引入新风险。现象是 Agent 修复了当前测试，却修改了无关模块或跳过断言。原因是目标函数不清、验证范围窄、没有 diff 审查。定位看 changed_files、diff 统计、测试覆盖、删除断言和权限事件。解决方式是限制可写路径，要求最小 diff，增加静态检查和测试选择策略，把补丁作为 MR 或 patch 产物，必须人工审查后合入。

### 取舍与对比
| 运行方式 | 优点 | 风险 | 适用场景 |
| --- | --- | --- | --- |
| 交互式终端 | 可随时确认和纠偏，适合探索 | 难自动化，结果不稳定 | 本地开发、复杂排查 |
| 无头 CLI | 容易接 CI，输入输出清晰 | 权限和失败分支要预设 | 批量修复、自动审查 |
| SDK 嵌入 | 可接业务系统和任务队列 | 调用方要承担隔离和观测 | 平台化 Agent 能力 |
| IDE 集成 | 上下文贴近编辑体验 | 难做大规模无人值守 | 局部修改、解释代码 |

无头模式的关键取舍是自动化程度和控制风险。越自动，越需要严格权限、预算和验证；越保守，越容易 blocked，需要人工接管。一个实用分层是：默认 read_only 生成建议；低风险任务允许生成 patch；只有在强隔离、强测试和人工门禁下，才允许 Agent 自动提交候选分支。

### 结合项目怎么讲
可以用“在 CI 里跑 Coding Agent 做缺陷修复”的通用故事。背景：回归测试失败后，希望 Agent 自动分析失败日志并尝试生成修复补丁。问题：CI 没有人确认，不能让 Agent 随意访问网络、读取密钥或直接合入代码。方案：设计 headless runner，输入为失败用例、变更文件和日志；权限预设为只读加工作区写入；工具命令白名单只允许指定测试；输出 result.json、patch、日志和验证结果。数据/效果：可以讲“低风险失败能自动给出候选补丁，高风险或证据不足输出 blocked”，不要把 blocked 说成失败。反思：CI Agent 的价值不是完全替代开发，而是把可重复的分析和候选修复前移；最终仍要靠测试、审查和权限边界兜底。""",
        points=[
            "无头模式要把确认、权限、输出和失败语义协议化。",
            "CI 中必须使用最小权限、临时工作区、超时和产物留存。",
            "结构化结果和退出码比自然语言总结更重要。",
            "自动修复应产出候选 patch，不应默认直接合入。",
            "SDK 集成要支持取消、流式事件、回调和审计。",
        ],
        drill=[
            dict(level="基础", q="什么是无头模式？和交互式 Agent 有什么不同？", a="无头模式是在没有人工实时交互的环境中运行 Agent，输入来自 CLI、配置、队列或 CI 事件，输出是结构化结果和产物。交互式 Agent 可以随时问用户确认，无头模式不能等待人，所以权限、预算、工具和失败策略都要预设。它更强调退出码、result.json、日志和 artifact。交互模式适合探索，无头模式适合自动化和批量任务。"),
            dict(level="原理", q="无头 Agent 的典型状态机是什么？", a="我会拆成 prepare、plan、act、verify、emit、cleanup。prepare 创建隔离工作区并加载策略；plan 生成有限步骤；act 调用工具并受权限控制；verify 运行测试或检查；emit 输出结构化结果和产物；cleanup 清理临时资源。每个阶段都要能失败，并映射到 passed、failed、blocked、error 这类有限状态。这样 CI 才能稳定消费结果。"),
            dict(level="实现", q="CI 集成时 result.json 应包含哪些字段？", a="至少要有 status、summary、changed_files、checks、permissions、artifacts、cost、error。status 要是有限枚举，不能只写自然语言。checks 记录命令、退出码和摘要；permissions 记录被拒绝或确认的动作；artifacts 给日志、补丁、报告的路径和类型。这样下游可以自动判断是否失败、展示什么产物、是否需要人工介入。"),
            dict(level="落地", q="在 CI 中跑 Agent 最大的风险有哪些？", a="主要是权限、密钥、供应链、成本和错误修复。CI 环境常有凭证和发布权限，Agent 如果能任意跑命令或访问网络，风险很高。依赖安装脚本也可能执行不可信代码。模型循环可能消耗大量 token 和时间。修复上还可能为了通过测试删除断言或改无关模块，所以要限制路径、命令和网络，并把补丁作为候选产物。"),
            dict(level="排查", q="无头任务卡住不返回，你怎么查？", a="先看最后一个 event：是模型请求确认、工具进程未退出，还是验证命令超时。再看 max_steps、wall timeout、子进程树、stdout/stderr 是否持续输出。无头模式不应出现 ask 等待人工，权限要预先映射为 allow 或 deny。每个工具都要有超时，总任务也要有 finally emit，保证即使内部错误也写 result.json。必要时记录 heartbeat，让 CI 能判断 runner 还活着。"),
            dict(level="取舍", q="为什么不建议让 CI Agent 自动直接合入代码？", a="因为模型生成的补丁可能只修当前表象，或者修改了无关模块、降低断言、引入安全风险。CI 环境的验证范围也有限，不能代表全部业务正确。更稳妥的做法是生成候选 patch、测试证据和结构化结论，再经过代码审查和门禁。只有非常低风险、强约束、强测试覆盖的场景，才可以考虑自动提交到候选分支。自动化程度越高，隔离和回滚要求越高。"),
            dict(level="设计", q="设计一个 CI Coding Agent Runner。", a="我会让 runner 接收任务描述、变更范围、失败日志和 policy_id。prepare 阶段创建临时工作区，只注入白名单环境变量。权限预设限制可写路径、命令白名单、网络和总预算。执行中用事件流记录模型消息、工具调用、权限决策和产物。验证阶段运行指定测试和静态检查。最后输出 result.json、patch、日志和指标，状态分为 passed、failed、blocked、error。cleanup 阶段删除临时资源，外部副作用必须有 receipt。"),
        ],
        choice=[
            dict(q="无头模式最核心的工程变化是什么？", options=["把 UI 隐藏但保留人工确认", "把确认、权限、输出和失败都协议化", "禁止所有工具调用", "只输出一段自然语言总结"], answer=[1], explain="B 正确。无头模式无法依赖实时人工确认，必须用策略、结构化输出和稳定状态表达结果。"),
            dict(q="CI 中运行 Coding Agent 应采取哪些措施？（多选）", options=["使用临时工作区", "最小权限和环境变量白名单", "给工具和总任务设置超时", "默认允许读取所有密钥以便排查"], answer=[0, 1, 2], explain="A、B、C 是基本隔离和稳定性措施。D 是明显风险，CI 中应尽量不暴露密钥。"),
            dict(q="result.json 的 status 最好如何设计？", options=["自由文本，越详细越好", "有限枚举，如 passed、failed、blocked、error", "只使用 HTTP 200", "不需要 status，看 summary 即可"], answer=[1], explain="B 便于机器判断。自由文本和 summary 适合给人看，但不适合作为 CI 控制信号。"),
            dict(q="Agent 在 CI 中生成补丁后，较稳妥的下一步是？", options=["无条件合入主分支", "删除失败测试", "输出候选 patch、验证证据和审查信息", "隐藏修改细节只报成功"], answer=[2], explain="C 保留自动化价值和人工门禁。A、B、D 都会放大模型错误和治理风险。"),
        ],
        short=[
            dict(q="为什么无头模式不能简单复用交互模式的权限流程？", points=["无头环境不能等待用户确认", "ask 要映射为预设 allow/deny", "需要结构化状态和退出码", "要防止 CI 卡死"], reference="交互模式下，Agent 遇到写文件、联网或危险命令可以询问用户；无头模式通常运行在 CI 或任务队列中，没有人实时确认。如果继续保留 ask，任务会卡住，流水线也拿不到稳定结果。因此无头模式要提前定义 policy，把动作映射为 allow 或 deny，并设置最大轮数、工具超时和总超时。结果要写入结构化文件并用退出码表达状态，不能只依赖自然语言。权限阻断应返回 blocked，而不是无限等待。"),
            dict(q="描述一个 CI Agent 的隔离方案。", points=["临时工作区或容器", "只挂载仓库和必要缓存", "环境变量白名单和短时凭证", "限制网络、命令和可写路径", "保留日志和产物"], reference="CI Agent 应在临时工作区或容器中运行，只挂载当前仓库和必要缓存，不共享开发者家目录。环境变量使用白名单，凭证尽量短时、最小权限，并对日志脱敏。权限策略限制可写路径、命令白名单、网络访问和总预算。工具执行要有超时，子进程要能被清理。运行结束后保留 result.json、patch、测试日志和权限审计，便于人工判断和复盘。这样即使模型行为异常，也能把影响限制在工作区内。"),
            dict(q="如何设计无头 Agent 的输出契约？", points=["固定 result.json schema", "状态枚举与退出码映射", "记录 changed_files、checks、permissions", "artifact manifest 保存日志和 patch"], reference="无头 Agent 的输出要给机器消费，所以需要固定 schema。result.json 应包含 status、summary、changed_files、checks、permissions、cost、artifacts 和 error。status 使用有限枚举，并与退出码映射，例如 passed 表示验证通过，failed 表示验证未通过，blocked 表示权限或信息不足，error 表示 runner 异常。日志、补丁和报告放在 artifact 目录，并在 manifest 中记录路径、类型和大小。自然语言总结只做辅助，不能替代结构化字段。"),
        ],
        labs=["lab-permission", "lab-tool-loop"],
        related=["harness-permission", "harness-loop", "dev-testing", "dev-launch"],
    ),

    dict(
        id="harness-checkpoint", course="harness", order=10,
        title="Checkpoint、回滚与会话恢复",
        summary="快照能回滚文件，不能抹掉外部事实。",
        md="""### 一句话与核心概念
Checkpoint 是 Agent 在关键步骤保存的可恢复状态，通常包括文件快照、会话消息、工具调用记录、计划、权限决策和产物索引。回滚是把工作区恢复到某个 checkpoint。会话恢复是重新加载上下文，让 Agent 接着之前的任务继续。面试里要特别强调局限：文件系统可以快照，外部副作用不能凭空回滚。

为什么 Coding Agent 需要 checkpoint？因为模型会探索，会试错，会修改多个文件再运行测试。没有快照，用户很难撤销半成品；没有会话持久化，长任务中断后只能靠记忆重来；没有工具记录，恢复后不知道哪些命令已经执行过。Checkpoint 把“模型循环”变成可审计、可恢复的工程流程。

常见 checkpoint 触发点包括：任务开始前、每次批量修改前、测试前、权限升级前、外部副作用前、用户确认点、会话结束时。粒度可以是全量快照、增量 diff、内容寻址对象或版本控制 worktree。选择取决于仓库大小、文件数量、性能要求和需要恢复的语义。

### 原理：快照、日志与恢复语义
一个完整 checkpoint 可以拆成三部分。第一是 workspace snapshot，记录文件路径、内容哈希、权限位和必要元数据。第二是 session log，记录消息、工具调用、Hook 决策、权限结果和 artifact。第三是 execution cursor，记录当前任务状态，例如进行到第几步、待办列表、预算和最后一次验证结果。

增量快照常用内容哈希。保存时遍历受管路径，计算 hash(path_content)，与上一个 checkpoint 比较，只存变化文件和删除标记。恢复时先校验当前工作区是否有未归属修改，再按 checkpoint manifest 删除新增文件、恢复修改文件、重建删除文件。复杂度上，全量扫描是 O(N * file_size)，增量存储节省空间，但恢复逻辑更复杂。大仓库通常要结合路径过滤和文件监控。

伪代码如下：

```python
def create_checkpoint(root, previous=None):
    manifest = {}
    for path in tracked_files(root):
        digest = sha256(read_bytes(path))
        if not previous or previous.digest(path) != digest:
            blob_id = store_blob(path, digest)
        else:
            blob_id = previous.blob(path)
        manifest[path] = {"digest": digest, "blob": blob_id}
    return Checkpoint(id=new_id(), manifest=manifest, parent=previous.id if previous else None)

def restore(checkpoint, root):
    assert no_unowned_changes(root)
    remove_files_not_in(checkpoint.manifest)
    for path, meta in checkpoint.manifest.items():
        write_bytes(path, load_blob(meta["blob"]))
```

恢复语义要讲清楚：文件回到 checkpoint 状态，消息和计划回到某个游标，预算和审计记录通常不能删除，只能追加“已回滚”事件。外部副作用，如发请求、创建远程资源、发送通知、消耗 token、安装依赖、写数据库，不会因文件回滚自动消失。harness 只能记录 receipt、提供补偿动作或提醒人工处理。

### 工程实现要点
实现 checkpoint 前要定义受管范围。通常只管理工作区文件，排除 .git、依赖目录、构建产物、缓存和大型二进制。排除规则要可见，否则用户会误以为所有东西都能恢复。每个 checkpoint 要有 id、parent_id、created_at、reason、manifest_digest、tracked_paths、excluded_paths、session_cursor、external_receipts。

创建 checkpoint 的时机要平衡性能和可恢复性。每个 token 都快照不现实；每次工具调用都快照也可能太慢。常见做法是：工具将要写文件前创建轻量 checkpoint；批量修改后记录 diff；运行高风险命令或外部副作用前创建显式 checkpoint。对大文件只记录哈希和引用，不把内容塞进会话上下文。

恢复时最怕覆盖用户新改动。必须先做 dirty check，判断当前文件是否与 checkpoint 子链中的某个状态一致。如果存在未归属修改，应阻断并提示用户选择保存、丢弃或另存补丁。恢复操作本身也要写审计日志，包含 from_checkpoint、to_checkpoint、影响文件和不可回滚副作用列表。

会话恢复要处理“上下文可恢复”和“外部状态已漂移”的差异。恢复后可以重放消息摘要、计划和工具结果，但不要假设旧测试结果仍然有效。依赖、分支、远程状态、当前时间和服务状态都可能变化。好的恢复流程会先做环境校验，再决定继续、重跑验证或重新规划。

### 生产落地：方案、踩坑与排查
问题一：回滚覆盖了用户手工修改。现象是用户在 Agent 运行中改了文件，回滚后丢失。原因是没有区分 Agent 管理的修改和用户并发修改。定位看文件 mtime、hash 链、编辑事件和 checkpoint manifest。解决方式是恢复前做 no_unowned_changes 检查；发现冲突时生成 patch 让用户选择，而不是直接覆盖。

问题二：用户以为外部副作用也回滚了。现象是文件恢复了，但远程任务、通知或数据库记录仍存在。原因是报告没有说明 checkpoint 的边界。定位看 external_receipts、工具审计和外部 request_id。解决方式是在高风险动作前提示“不可自动回滚”，记录 receipt；回滚报告列出未撤销副作用；能补偿的提供补偿命令，不能补偿的标记人工处理。

问题三：恢复后继续执行得出错误结论。现象是 Agent 恢复旧会话后直接引用之前测试通过，实际环境已经变了。原因是会话状态恢复了，但验证证据过期。定位看 checkpoint 时间、依赖版本、分支状态、测试产物时间和环境摘要。解决方式是恢复后先运行环境校验，关键验证必须重跑；旧结果只能作为历史证据，不作为当前通过结论。

问题四：checkpoint 占用空间过大。现象是长任务后磁盘迅速膨胀。原因是全量复制仓库、保存构建产物或大型日志。定位看 blob store 大小、单 checkpoint 增量、最大文件列表和排除规则。解决方式是内容寻址去重、路径白名单、大小上限、日志压缩、保留策略和手动 pin 重要 checkpoint。

### 取舍与对比
| 方案 | 优点 | 风险 | 适合场景 |
| --- | --- | --- | --- |
| 全量目录复制 | 实现简单，恢复直观 | 慢，占空间大 | 小项目、短任务 |
| 增量内容哈希 | 节省空间，可追溯 | 实现复杂，需冲突检测 | 中大型仓库 |
| 版本控制分支或 worktree | 利用现有 diff 能力 | 未跟踪文件和外部状态需额外处理 | 代码仓库任务 |
| 只保存会话日志 | 成本低 | 不能恢复文件 | 只读分析任务 |

Checkpoint 的取舍不是“越频繁越好”。频繁快照恢复点多，但影响性能和空间；稀疏快照成本低，但回滚粒度粗。生产上通常用“关键动作前强制 checkpoint + 定期轻量 diff + 用户可手动 pin”的组合。还要把 checkpoint 和权限、Hook、无头输出连起来，形成可审计链路。

### 结合项目怎么讲
可以用“用 Agent 自动生成和修复自动化用例”的场景。背景：Agent 会批量改测试代码、运行验证并多轮修复。问题：模型有时尝试错误方向，用户希望回到修改前；任务中断后又希望继续。方案：任务开始创建 baseline checkpoint；每次批量写文件前创建 checkpoint；测试前记录 session cursor；外部动作记录 receipt。回滚时先检查未归属修改，再恢复文件并列出不可回滚事项。数据/效果：可以说“减少手工清理半成品的时间，恢复后能从最近验证点继续”，不要声称能撤销所有副作用。反思：checkpoint 是安全网，不是事务系统；对外部系统要用幂等、补偿和人工确认来配合。""",
        points=[
            "Checkpoint 包含文件快照、会话日志、执行游标和外部副作用记录。",
            "回滚文件前必须检查未归属修改，避免覆盖用户工作。",
            "外部副作用不可凭空回滚，只能记录、补偿或人工处理。",
            "恢复旧会话后关键验证要重跑，历史结果不能当当前结论。",
            "快照粒度要在性能、空间和恢复点之间取舍。",
        ],
        drill=[
            dict(level="基础", q="Checkpoint 在 Coding Agent 中解决什么问题？", a="它解决可恢复和可审计问题。Agent 会多轮修改文件、运行命令和试错，没有 checkpoint 就很难撤销半成品。Checkpoint 保存文件快照、会话日志、工具调用、权限决策和执行游标。回滚可以恢复工作区状态，会话恢复可以让中断任务继续。但它不是万能事务，外部副作用不能自动消失。"),
            dict(level="原理", q="文件快照和会话恢复有什么区别？", a="文件快照关注工作区内容，如路径、哈希、权限位和文件内容。会话恢复关注 Agent 的上下文，如消息、计划、工具结果、预算和游标。只恢复文件，模型可能不知道之前为什么改；只恢复会话，文件可能已经不匹配。生产中要把二者用 checkpoint id 绑定，并在恢复后校验当前环境。外部状态漂移时，旧验证结果只能作为历史记录。"),
            dict(level="实现", q="如何实现增量 checkpoint？", a="可以为受管文件计算内容哈希，与父 checkpoint 比较，只保存变化文件的 blob 和删除标记。Manifest 记录 path、digest、blob_id、权限和大小。恢复时根据 manifest 删除新增文件、写回变化文件、重建删除文件。为了避免覆盖用户修改，恢复前要检查当前 hash 是否属于 checkpoint 链。大型目录要用排除规则、大小上限和内容寻址去重。"),
            dict(level="落地", q="哪些时机应该创建 checkpoint？", a="任务开始前要有 baseline，批量写文件前要有恢复点，运行高风险命令或外部副作用前要有显式 checkpoint，用户确认点和会话结束也应保存。每次小工具调用都全量快照可能太慢，所以要结合增量 diff。对于无头 CI，生成候选 patch 前后也应记录状态。关键是让用户能回到有意义的阶段，而不是生成一堆不可理解的恢复点。"),
            dict(level="排查", q="用户说回滚后还是有东西没撤销，你怎么解释和定位？", a="先区分文件系统状态和外部副作用。查看 checkpoint manifest，确认受管文件是否恢复到目标哈希。再查看工具审计和 external_receipts，找出是否创建过远程资源、发送通知、安装依赖或调用外部 API。文件回滚不会自动撤销这些事实。能补偿的提供补偿操作，不能补偿的在报告里列出并要求人工处理。后续应在这类动作前增加确认和 receipt 记录。"),
            dict(level="取舍", q="为什么不能每一步都做完整快照？", a="完整快照实现简单，但对大仓库会很慢，占用大量磁盘，也会保存无关构建产物。每一步都快照还会让恢复点太多，用户难以选择。更好的方式是在关键动作前创建 checkpoint，平时记录增量 diff，并使用内容寻址去重。对只读操作可以只记录会话日志，对写操作再保存文件状态。这样在可恢复性、性能和空间之间平衡。"),
            dict(level="设计", q="设计一个支持回滚和恢复的 Agent 会话系统。", a="我会把 workspace snapshot、session log、execution cursor 和 external receipts 绑定到同一个 checkpoint id。文件层用内容哈希和 manifest 做增量快照，恢复前做未归属修改检查。会话层保存消息摘要、工具调用、权限决策、预算和验证结果。外部副作用记录 request_id、幂等键和补偿建议。恢复时先校验工作区、依赖和分支状态，再决定继续、重跑验证或重新规划。所有回滚动作本身也要追加审计。"),
        ],
        choice=[
            dict(q="Checkpoint 最不能保证的是哪件事？", options=["恢复受管文件内容", "记录会话日志", "自动撤销已经发生的外部副作用", "保存工具调用证据"], answer=[2], explain="C 是局限。文件和日志可以由 harness 保存，外部副作用只能记录、补偿或人工处理。"),
            dict(q="恢复 checkpoint 前应该检查什么？（多选）", options=["当前是否有未归属修改", "目标 checkpoint 的 manifest 是否完整", "是否存在不可回滚外部副作用", "是否可以忽略用户新改动直接覆盖"], answer=[0, 1, 2], explain="A、B、C 都是恢复前检查。D 错，直接覆盖会造成数据丢失。"),
            dict(q="会话恢复后，旧测试通过结果应如何使用？", options=["直接当作当前通过", "作为历史证据，关键验证需要重跑", "完全删除", "改成失败"], answer=[1], explain="B 正确。环境可能漂移，旧结果不能替代当前验证，但可作为历史参考。"),
            dict(q="减少 checkpoint 磁盘占用的合理方法是？", options=["保存整个依赖目录", "内容寻址去重和排除构建产物", "把所有日志塞进模型上下文", "禁用 manifest"], answer=[1], explain="B 是常见优化。依赖目录和大日志会放大空间；manifest 是恢复和审计所必需的。"),
        ],
        short=[
            dict(q="说明 checkpoint 与事务的区别。", points=["checkpoint 可恢复文件和会话状态", "事务强调原子提交和回滚", "外部副作用不可自动撤销", "需要 receipt、幂等和补偿"], reference="Checkpoint 更像工程快照，不是严格数据库事务。它可以保存受管文件、会话日志、工具调用和执行游标，让用户回到某个工作区状态。事务则要求一组操作要么全部提交，要么全部回滚，并且外部观察不到中间状态。Agent 执行中可能调用外部 API、发送通知、消耗 token 或创建远程资源，这些副作用不会因为文件回滚自动消失。因此生产系统要记录 receipt，使用幂等键，能补偿的提供补偿动作，不能补偿的明确提示人工处理。"),
            dict(q="如何避免回滚覆盖用户并发修改？", points=["记录 checkpoint hash 链", "恢复前做 dirty check", "区分 Agent 修改和未归属修改", "冲突时生成 patch 或要求用户选择"], reference="避免覆盖的关键是恢复前校验。创建 checkpoint 时记录受管文件的 hash、路径和父 checkpoint。恢复时比较当前文件 hash 是否属于这条 checkpoint 链；如果文件被用户或其他进程改过，就属于未归属修改。此时不能直接写回目标版本，应阻断恢复，展示冲突文件，允许用户保存为 patch、放弃修改或手动合并。恢复动作本身也要写审计日志，说明哪些文件恢复、哪些被跳过。"),
            dict(q="会话恢复后为什么要重新验证？", points=["外部环境可能漂移", "依赖、分支、时间和服务状态可能变化", "旧结果只是历史证据", "恢复后先做环境校验和关键测试"], reference="会话恢复只能恢复 harness 保存的消息、计划、工具结果和部分工作区状态，不能保证外部环境不变。依赖版本、分支内容、远程服务、当前时间、缓存和权限都可能发生变化。如果恢复后直接引用旧测试通过，就可能给出错误结论。正确做法是先校验工作区和环境摘要，再对关键验证重新执行。旧测试结果可以帮助理解历史路径，但当前是否通过必须由新的验证证据支持。"),
        ],
        labs=["lab-context-trim"],
        related=["harness-loop", "harness-headless", "harness-permission"],
    ),

    dict(
        id="harness-cost", course="harness", order=11,
        title="模型、思考强度与成本",
        summary="成本设计影响上下文、循环和模型路由。",
        md="""### 一句话与核心概念
Coding Agent 的成本不是单次 API 价格，而是模型选择、思考强度、上下文长度、工具 schema、循环轮数、并行子任务和缓存命中共同决定的系统成本。面试里要把 token 预算、prompt caching、模型分级和循环控制放在一起讲。成本控制不是简单省钱，它也影响延迟、稳定性和任务完成率。

模型越强，单次调用通常越贵，但可能减少轮数和返工；模型越便宜，可能需要更多提示、更多验证和更多重试。思考强度越高，复杂任务质量可能更好，但延迟和输出前内部消耗也会增加。上下文越长，模型看到的信息越多，但无关信息会稀释注意力并破坏缓存。好的 harness 会根据任务风险和阶段选择模型，而不是全程一个档位。

Prompt caching 的核心是前缀复用。很多服务会对请求前面完全相同或按块对齐相同的部分复用计算。稳定系统提示、工具 schema、项目规则和少变上下文放在前面，用户新问题、最新日志和动态结果放在后面，更容易命中。缓存不是语义相似缓存，通常要求字节级或 token 级前缀一致。

### 原理：token 成本、缓存前缀与循环预算
一次 Agent 任务的粗略成本可以写成：total_cost = sum(call_i_input_tokens * price_in(model_i) + call_i_output_tokens * price_out(model_i)) + tool_cost + human_wait_cost。真实系统还要考虑缓存折扣、重试、并行子代理和验证命令成本。对工程设计更有用的是拆指标：每轮输入 token、输出 token、缓存命中 token、工具 schema token、检索 token、思考强度、轮数、失败重试数。

Prompt caching 关注最长公共前缀。设上一次请求 token 序列为 A，当前请求为 B，命中长度 L = max k，使得 A[0:k] == B[0:k]，并满足服务端的块对齐规则。若在前缀中插入时间戳、随机排序工具、变化的日志摘要，L 会骤降。优化原则是“稳定的放前面，变化的放后面；长而少变的放前面，短而变化的放后面”。

伪代码如下：

```python
def build_prompt(static_rules, tool_schemas, repo_summary, task, recent_logs):
    prefix = [
        stable_sort(static_rules),
        stable_sort(tool_schemas),
        repo_summary.digest_pinned_text,
    ]
    suffix = [task.user_text, recent_logs.tail_summary]
    return prefix + suffix

def choose_model(stage, risk, budget):
    if stage == "plan" and risk == "high":
        return "strong"
    if stage in {"format", "summarize_log"}:
        return "small"
    if budget.remaining_tokens < budget.reserve:
        return "small_or_stop"
    return "default"
```

循环预算要防止“越失败越贵”。每次失败都会把错误日志加入上下文，使下一轮更长。若没有裁剪和停止条件，成本会呈轮数累积上升。harness 需要设置 max_steps、max_tool_calls、max_tokens、max_retries、per_stage_budget 和 stop reason。预算用完时要输出 blocked 或 partial，不要假装成功。

### 工程实现要点
模型路由可以按阶段分层。需求理解、架构修改、安全敏感修复用强模型；日志摘要、格式化建议、简单代码解释用轻量模型；最终报告可根据用户要求选择。路由输入包括任务类型、风险等级、代码影响面、失败次数、剩余预算和是否需要长上下文。路由决策要可审计，不能只写在提示词里。

上下文构建要为缓存服务。工具 schema 稳定排序，描述不要每轮拼动态内容。规则文件、仓库摘要、Skill 元数据尽量版本化并带 digest。动态信息放在后缀，如用户当前请求、最新命令输出、失败日志尾部。长日志先用确定性截断或小模型摘要，再把 artifact 路径和摘要放入主模型。不要把全量测试日志每轮重复塞入前缀。

一个预算对象可以这样设计：

```python
class Budget:
    def __init__(self, token_limit, step_limit, reserve):
        self.token_limit = token_limit
        self.step_limit = step_limit
        self.reserve = reserve
        self.used = 0
        self.steps = 0

    def allow_call(self, estimated_tokens):
        if self.steps >= self.step_limit:
            return False, "step_limit"
        if self.used + estimated_tokens > self.token_limit - self.reserve:
            return False, "token_budget"
        return True, "ok"
```

观测指标要覆盖成本和效果：每任务总 token、每轮 token、缓存命中率、命中前缀长度、模型分布、平均轮数、重试率、因预算停止比例、单位成功任务成本。只看总费用没有意义，要和通过率、人工接管率、延迟一起看。

### 生产落地：方案、踩坑与排查
问题一：缓存命中率突然下降。现象是相同任务类型成本和延迟上升。原因常见于工具列表顺序变了、系统提示插入时间戳、扩展 schema 每轮带随机 id、仓库摘要放入动态计数。定位看相邻请求前缀 diff、cache hit tokens、工具 schema digest 和 prompt 构建日志。解决方式是稳定排序，移除前缀动态字段，把变化内容后移，给长规则和 schema 固定版本。

问题二：低价模型反而更贵。现象是单次调用便宜，但任务总成本更高。原因是模型能力不足导致重试、误改、测试失败和人工介入增加。定位看按模型分组的轮数、成功率、返工率和总 token。解决方式是按阶段路由：低风险摘要用小模型，高风险规划和修复用强模型；连续失败时升级模型，而不是继续低价重试。

问题三：日志越修越长，最终预算耗尽。现象是 Agent 每轮都把全量错误日志加入上下文，几轮后无法继续。原因是缺少日志摘要、artifact 引用和上下文裁剪。定位看每轮输入 token 构成，尤其是 tool_result 和 recent_logs。解决方式是长日志落盘，提取错误栈、失败用例和关键 diff；旧轮次压缩成摘要；保持工具调用配对完整；预算不足时停止并说明缺什么。

问题四：并行子任务省时间但费用爆炸。现象是墙钟时间下降，总 token 和工具调用翻倍。原因是子代理重复读取同一仓库、重复加载工具 schema、产出重叠分析。定位看每个子任务输入 token、重复上下文比例和合并冲突。解决方式是只并行独立任务，给子任务窄上下文和明确产出；共享摘要和 artifact；主代理做去重和合并；设置并发预算。

### 取舍与对比
| 策略 | 优点 | 风险 | 适用场景 |
| --- | --- | --- | --- |
| 全程强模型高思考 | 成功率和复杂推理更稳 | 成本和延迟高 | 高风险架构、复杂修复 |
| 全程轻量模型 | 单次便宜、响应快 | 返工多，易误判 | 简单摘要、格式转换 |
| 阶段化模型路由 | 成本与质量平衡 | 路由实现复杂 | 生产 Agent 默认选择 |
| 激进上下文裁剪 | 省 token，速度快 | 可能丢关键证据 | 日志长、预算紧 |

成本优化不能只盯 token 单价。强模型一次解决可能比弱模型五次便宜；少给上下文可能省 token 但增加误修；并行能省时间但不一定省钱。成熟 harness 会把成本作为约束放进规划：先粗判任务风险，再决定模型、思考强度、上下文预算、验证范围和是否派生子任务。

### 结合项目怎么讲
可以用“给测试平台做知识库问答”的场景。背景：用户问题既有简单用法，也有复杂故障排查。问题：全用强模型成本高，全用小模型复杂问题答不准；文档和工具 schema 每轮重复注入，缓存命中差。方案：把稳定系统规则、工具 schema、文档目录摘要放前缀并固定排序；用户问题和检索片段放后缀；简单问答用轻量模型，跨模块故障和代码生成升级强模型；设置 token 和轮数预算，长日志用摘要加 artifact。数据/效果：可以讲“缓存命中和平均轮数成为核心指标”，不要编造固定节省比例。反思：成本控制是系统设计，不是最后砍预算；预算不足时要诚实输出 blocked 或需要人工补充，而不是压缩证据后乱答。""",
        points=[
            "总成本由模型、思考强度、上下文、轮数、重试、并行和缓存共同决定。",
            "Prompt caching 依赖稳定前缀，动态内容应尽量后移。",
            "模型路由要按阶段、风险、失败次数和预算决策。",
            "预算耗尽要输出明确停止原因，不能伪造成功。",
            "成本指标必须和成功率、延迟、人工接管率一起看。",
        ],
        drill=[
            dict(level="基础", q="Coding Agent 的成本主要由哪些因素决定？", a="不只是模型单价。输入 token、输出 token、思考强度、工具 schema、上下文长度、循环轮数、重试次数、并行子任务和缓存命中都会影响总成本。工具本身也有成本，例如 CI 时间和外部 API。强模型单次贵，但可能减少返工；弱模型单次便宜，但可能增加总轮数。要按任务总成本和成功率评估，而不是只看一次调用。"),
            dict(level="原理", q="Prompt caching 为什么强调稳定前缀？", a="缓存通常复用请求开头相同部分的计算结果，所以命中取决于最长公共前缀。系统规则、工具 schema、项目摘要如果顺序稳定，就能在相似任务之间复用。若在前缀插入时间戳、随机排序工具或动态日志，前缀很早就不相同，命中长度会下降。优化原则是稳定内容放前面，动态内容放后面，并保持排序和版本固定。"),
            dict(level="实现", q="如何设计模型路由策略？", a="我会按阶段、风险、影响面、失败次数和预算路由。规划、复杂修复和安全敏感任务用强模型；日志摘要、格式转换和简单解释用轻量模型；连续失败时升级，而不是低价模型无限重试。路由要记录决策原因和预估成本。还要设置保留预算，确保最终总结和验证结果能输出。模型路由和权限、上下文裁剪一样，应该是 harness 逻辑而不是临时提示词。"),
            dict(level="落地", q="缓存命中率低怎么排查？", a="先对比相邻请求的前缀，找第一个不同位置。再看工具列表顺序、schema digest、系统提示是否有动态字段、扩展是否每轮注入不同内容。检查 cache hit tokens 和 prompt 构建日志，按模块拆出规则、工具、仓库摘要和动态日志的 token。解决上稳定排序、移除时间戳、版本锁定 schema，把变化内容放到后缀。必要时把长上下文分为固定前缀和按需加载资源。"),
            dict(level="排查", q="预算耗尽但任务没完成，应如何处理？", a="首先不能把未验证结果说成成功。应该输出 stopped 或 blocked，说明耗尽的是 step、token、时间还是工具预算，并列出已完成步骤、剩余风险和下一步需要什么。内部上要分析 token 构成，是日志过长、工具 schema 过多、重试太多还是子任务重复。修复方式可能是压缩历史、裁剪日志、升级模型减少轮数、缩小任务范围或让用户确认增加预算。"),
            dict(level="取舍", q="强模型一定更贵吗？", a="从单次调用看通常更贵，但从任务总成本看不一定。强模型可能一次规划正确，减少错误修改、重试和人工接管；弱模型可能多轮失败，最终 token 和 CI 时间更多。是否更贵取决于任务复杂度、验证成本和失败代价。生产系统应按阶段混用模型，并用真实指标比较单位成功任务成本，而不是只看输入输出单价。"),
            dict(level="设计", q="设计一个成本可控的 Coding Agent 循环。", a="我会先为任务设置 token、轮数、工具调用和时间预算，并保留最终报告预算。上下文构建采用稳定前缀和动态后缀，长日志用摘要加 artifact。模型按阶段路由，复杂规划和多次失败升级强模型，简单摘要用轻量模型。循环中记录每轮 token、缓存命中、工具耗时和验证结果。达到预算阈值时停止并输出 blocked，不继续盲目重试。最后用单位成功成本、平均轮数和人工接管率调优。"),
        ],
        choice=[
            dict(q="Prompt caching 最依赖什么？", options=["语义相似即可", "请求前缀稳定一致", "输出越长越容易命中", "模型随机性越高越好"], answer=[1], explain="B 正确。缓存通常依赖前缀 token 或字节一致，而不是只看语义相似。"),
            dict(q="哪些做法容易导致缓存失效？（多选）", options=["工具 schema 稳定排序", "在系统提示前部插入当前时间", "每轮随机排列工具列表", "把动态日志放在请求后缀"], answer=[1, 2], explain="B、C 会破坏稳定前缀。A 和 D 通常有利于缓存。"),
            dict(q="低价模型总成本更高的常见原因是？", options=["单次调用太短", "能力不足导致重试和返工", "缓存命中太高", "工具 schema 太稳定"], answer=[1], explain="B 正确。总成本要看任务完成路径，弱模型多次失败可能比强模型一次成功更贵。"),
            dict(q="预算用尽时，正确做法是？", options=["声称已完成", "无限继续直到成功", "输出停止原因、已完成证据和剩余风险", "删除日志节省 token 后给结论"], answer=[2], explain="C 是诚实且可运维的做法。A、B、D 都会降低可信度并可能产生错误结论。"),
        ],
        short=[
            dict(q="说明 prompt caching 的工程优化方法。", points=["稳定系统规则和工具 schema", "固定排序和版本 digest", "动态内容后移", "避免时间戳和随机字段进入前缀", "观察 cache hit tokens"], reference="Prompt caching 的关键是让相似请求拥有尽可能长的稳定前缀。工程上应把系统规则、工具 schema、稳定项目摘要放在前面，并固定排序、版本和 digest。用户当前问题、最新日志、命令输出等动态内容放在后缀。不要在前缀插入时间戳、随机 id、每轮变化的统计或不稳定扩展列表。排查时要记录 prompt 构建各部分 token 和 cache hit tokens，对比相邻请求第一个不同位置。这样才能把缓存问题从猜测变成可定位的构建问题。"),
            dict(q="如何判断是否应该升级到更强模型？", points=["考虑任务风险和影响面", "考虑连续失败和返工成本", "考虑验证成本和预算", "按单位成功成本评估"], reference="是否升级模型不能只看单次价格。高风险架构修改、安全敏感操作、跨文件复杂修复和多次失败后的任务，适合升级强模型，因为错误修复和返工成本更高。如果轻量模型已经连续失败，继续重试往往会浪费 token 和 CI 时间。还要看验证成本：测试很慢时，一次错误尝试代价很高。生产中应记录按模型分组的成功率、平均轮数、人工接管率和单位成功成本，用数据决定路由策略。"),
            dict(q="设计 token 预算时要保留哪些余量？", points=["保留最终总结预算", "保留验证结果回填预算", "限制轮数和工具调用", "预算不足时停止而不是伪造"], reference="Token 预算不能全部用于中间推理，否则最后无法总结和解释验证结果。应为最终回复、关键工具结果回填和错误报告保留 reserve。循环层要限制最大轮数、最大工具调用、单轮输入上限和总 token 上限。长日志要落盘并摘要，历史消息要压缩但保持工具调用配对完整。预算接近阈值时应选择收敛：运行最关键验证、输出剩余风险，或明确 blocked。不能为了省 token 删除证据后给确定结论。"),
        ],
        labs=["lab-prefix-cache", "lab-context-trim", "lab-compaction"],
        related=["harness-context", "harness-loop", "arch-model-routing", "arch-observability"],
    ),

    dict(
        id="harness-compare", course="harness", order=12,
        title="主流 Coding Agent 对比与 Harness 演进",
        summary="比较工具要看工程边界，不看产品排名。",
        md="""### 一句话与核心概念
主流 Coding Agent 的目标相似：理解代码、规划修改、调用工具、验证结果并向用户交付。差异主要在交互入口、上下文来源、权限模型、扩展机制、执行环境、可恢复性和团队治理。面试里不要把对比讲成产品排名，也不要编造不稳定细节。更好的讲法是：不同形态服务不同工作流，harness 的演进方向是减少模型外的过度脚手架，保留工程边界。

常见形态可以粗分为三类。终端型 Agent 如 Claude Code、Codex CLI，更贴近命令行和仓库级任务，擅长读写文件、运行命令、生成 diff、接 CI。IDE 型 Agent 如 Cursor，更贴近编辑器上下文、光标、选区、内联修改和人工边看边改。平台或 SDK 型 Agent 则把能力嵌入任务系统、代码评审、测试平台或内部工具，强调 API、权限和产物协议。

公开稳定点可以讲：终端型通常强调工作目录、命令执行、权限审批和补丁交付；IDE 型通常强调编辑体验、上下文选择和代码补全；支持 MCP 或类似协议的工具可以接外部能力；多数成熟工具都会遇到同样问题：上下文爆炸、权限边界、工具失败、回滚、成本和审计。

### 原理：从模型能力到 Harness 职责的重新分配
早期 harness 往往用大量提示词教模型“先分析、再计划、再执行”，还会硬编码非常细的推理模板。模型能力增强后，一些脚手架可以删除：重复的思考格式、过度的链式自问、固定但低价值的计划模板、要求模型复述显而易见步骤的规则。删除这些能降低 token、减少模型被格式束缚，也有利于自然处理复杂任务。

但有些 harness 逻辑不能因为模型变强就删。权限、沙箱、工具 schema、Hook、审计、预算、上下文检索、checkpoint、结构化输出都不是智力问题，而是工程控制问题。再强的模型也不应该靠自觉决定是否读取密钥、是否无限花费预算、是否把外部副作用当作可回滚。演进方向是把“教模型怎么想”的提示减少，把“系统允许做什么、证据怎么留、失败怎么退出”的边界做硬。

一个评估 Coding Agent 的框架可以写成：capability = model_reasoning + context_quality + tool_reliability + control_boundary + feedback_loop。模型只是其中一项。上下文质量决定是否读到正确文件；工具可靠性决定计划能否落地；控制边界决定是否安全；反馈循环决定失败后能否修复。

### 工程实现要点
对比工具时可以建立评估矩阵，而不是凭体验下结论。维度包括：交互入口、上下文选择、工具执行、权限预设、扩展协议、会话恢复、无头能力、结构化输出、成本观测和团队治理。每个维度都问“能否配置、能否审计、失败时能否恢复”。

示例评估结构：

```python
dimensions = [
    "interaction", "context", "tools", "permission",
    "extension", "checkpoint", "headless", "observability",
]

def score_agent(observations):
    return {
        d: {
            "supported": observations[d].supported,
            "auditable": observations[d].has_logs,
            "recoverable": observations[d].has_recovery,
            "risk": observations[d].risk_level,
        }
        for d in dimensions
    }
```

面试中可以选一两个公开稳定差异展开。例如终端型更容易脚本化和接 CI，但对编辑器即时上下文不如 IDE 自然；IDE 型局部修改体验好，但无人值守和权限策略要看具体实现；SDK 型适合平台化，但调用方要自己处理隔离、预算和产物。不要断言某个产品永远更强，因为模型、功能和生态变化很快。

Harness 演进还包括“删除负担”。如果模型已经能稳定理解自然语言计划，就不要强制它输出冗长模板；如果工具 schema 已经足够清晰，就不要再用一大段提示重复解释；如果 Hook 能确定性检查格式，就不要要求模型每次自查十遍。删除的标准是：删除后通过率不降、成本下降、错误更少、边界不变弱。

### 生产落地：方案、踩坑与排查
问题一：选型只看 demo。现象是演示中生成代码很快，接入真实仓库后频繁失败。原因是 demo 没覆盖权限、依赖安装、测试、回滚和团队流程。定位要跑代表性任务集，统计成功率、人工接管、平均轮数、失败类型和安全事件。解决方式是用真实但脱敏的任务做评测，比较端到端闭环，而不是只看生成片段。

问题二：IDE Agent 和终端 Agent 混用造成上下文不一致。现象是 IDE 中看到的文件状态和终端运行状态不同，修改相互覆盖。原因是多个工具共享工作区但没有 checkpoint 和变更边界。定位看文件 mtime、diff、会话日志和运行目录。解决方式是约定单任务单执行者，或使用独立 worktree；切换工具前先同步 diff 和验证状态。

问题三：模型升级后旧 harness 变慢或误导。现象是新模型本来能直接解决，旧提示却要求输出过长计划、固定格式或重复自检，导致成本高。原因是脚手架没有随模型能力演进。定位看提示 token 占比、模型违反模板的频率、删除规则后的 A/B 结果。解决方式是把软性推理模板删减，保留权限、工具契约和审计；用任务集验证删除是否影响通过率。

问题四：对比时忽略治理成本。现象是个人使用很好，团队推广后出现密钥、审计、成本分摊和插件管理问题。原因是只看开发体验，没有看管理员和平台视角。定位看权限配置、日志留存、扩展来源、成本报表和退出机制。解决方式是把治理维度纳入评估：谁能启用工具、谁能审批高风险动作、日志保存多久、如何禁用插件、如何限制预算。

### 取舍与对比
| 维度 | 终端型 Agent | IDE 型 Agent | SDK/平台型 Agent |
| --- | --- | --- | --- |
| 交互体验 | 命令驱动，适合仓库级任务 | 贴近编辑器，适合局部修改 | 嵌入业务流程，适合批量任务 |
| 权限边界 | 通常围绕命令、文件、网络审批 | 通常围绕编辑和项目访问 | 取决于调用方策略和沙箱 |
| 扩展方式 | 配置、命令、MCP、脚本较自然 | 插件和编辑器生态较自然 | API、工具网关、任务队列较自然 |
| 无头/CI | 相对容易接入 | 通常不是主场景 | 最适合平台化无人值守 |
| 风险 | 命令副作用和仓库范围大 | 上下文隐式、覆盖修改 | 隔离、成本和治理要自建 |

模型变强后应该删掉的是低价值、重复、脆弱的 harness 逻辑；不该删的是硬边界。可以删除过细的“先输出三点计划再做事”模板、重复解释工具用法的长提示、只为弥补旧模型理解力的强制格式。不能删除权限、沙箱、审计、预算、checkpoint、结构化产物和验证门禁。评价演进是否正确，要看通过率、成本、延迟、误操作和可恢复性，而不是看提示词变短多少。

### 结合项目怎么讲
可以用“团队引入 Coding Agent 辅助自动化用例维护”的通用模板。背景：开发和测试都希望用 Agent 处理失败日志、补测试和做小修复。问题：有人喜欢 IDE 边看边改，有人希望 CI 自动给候选补丁；如果没有统一边界，会出现权限、成本和证据混乱。方案：选型上把 IDE Agent 用于局部编辑和解释，终端或无头 Agent 用于仓库级修复和验证；统一要求产出 diff、测试命令、结构化结果和审计日志；扩展能力通过受控协议接入；模型升级后定期清理旧提示模板。数据/效果：可以讲“按任务集评估成功率、平均轮数、人工接管和安全事件”，不要用主观排名。反思：Agent 工具会快速变化，长期稳定的是评估框架和工程边界；选型要能替换模型和前端，而不是绑定某个产品习惯。""",
        points=[
            "主流 Coding Agent 差异主要在交互入口、上下文、权限、扩展和恢复能力。",
            "终端型偏仓库和 CI，IDE 型偏编辑体验，SDK 型偏平台化。",
            "模型变强后可删过度提示，但不能删权限、审计、预算和验证。",
            "选型要用端到端任务集评估，不要只看 demo 生成效果。",
            "Harness 演进目标是更少脚手架、更硬工程边界。",
        ],
        drill=[
            dict(level="基础", q="如何比较 Claude Code、Codex CLI、Cursor 这类 Coding Agent？", a="我会从交互入口、上下文来源、工具执行、权限边界、扩展机制、恢复能力、无头集成和观测审计比较。终端型更适合仓库级任务、命令执行和 CI；IDE 型更适合局部编辑、光标上下文和边看边改。不能只比较一次生成代码的质量，要看真实工程闭环。产品能力变化很快，所以结论要基于公开稳定点和任务评测。"),
            dict(level="原理", q="为什么模型变强后 harness 仍然重要？", a="模型变强主要提升理解、规划和代码生成能力，但权限、沙箱、预算、审计、checkpoint 和结构化输出是工程控制问题。再强的模型也不应该凭自觉决定是否读取敏感文件或无限调用工具。工具失败、外部副作用和团队治理也需要 harness 管理。可以减少教模型思考的脚手架，但不能删除系统边界。好的演进是让模型更自由地推理，同时让执行更可控。"),
            dict(level="实现", q="设计一个 Coding Agent 选型评估矩阵。", a="矩阵维度包括交互入口、上下文选择、工具可靠性、权限模型、扩展机制、checkpoint、无头能力、结构化输出、成本观测和团队治理。每个维度都看是否支持、是否可配置、是否可审计、失败是否可恢复。评测任务要覆盖读代码、跨文件修改、运行测试、处理失败、权限阻断和回滚。指标包括成功率、平均轮数、人工接管率、成本、延迟和安全事件。"),
            dict(level="落地", q="终端型和 IDE 型 Agent 应如何协同使用？", a="可以把 IDE 型用于局部理解、补全、选区重构和人工强参与修改，把终端或无头 Agent 用于仓库级任务、批量修改、运行测试和生成候选补丁。关键是不要让多个 Agent 同时无边界地改同一工作区。可以用独立 worktree、checkpoint 或任务锁隔离。切换工具前要同步 diff、测试结果和未提交修改。团队层面还要统一产物格式和审计要求。"),
            dict(level="排查", q="模型升级后旧提示效果变差，你怎么处理？", a="先拆分是模型问题、提示问题还是工具问题。查看系统提示 token 占比、固定模板是否限制了回答、模型是否频繁违反旧格式、任务成功率和成本变化。对低价值脚手架做 A/B：删除冗长计划模板、重复工具说明和过度自检，看通过率、轮数和误操作是否改善。保留硬边界，如权限、schema、Hook 和审计。不要因为新模型聪明就一次性删掉所有控制逻辑。"),
            dict(level="取舍", q="为什么不应该把工具对比讲成产品排名？", a="因为这些工具的模型、功能和生态变化很快，排名很容易过期。更重要的是不同形态适合不同工作流：终端、IDE、SDK 的优势不同。团队还要考虑权限、审计、成本、扩展、CI 和治理，而不只是个人体验。面试中讲评估维度和场景匹配，比说某个产品绝对最好更专业。结论应基于任务集和公开稳定能力。"),
            dict(level="设计", q="模型越来越强后，你会如何重构现有 harness？", a="我会先盘点 harness 逻辑，分成软性推理脚手架和硬工程边界。对软性部分做实验性删除，如冗长计划模板、重复自检、固定思考格式；用任务集观察成功率、成本和错误类型。对硬边界继续加强，包括权限、沙箱、结构化工具、Hook、checkpoint、预算和审计。上下文层改为更少但更准的检索，扩展层做延迟加载。最终目标是让模型少受无效格式束缚，但所有动作仍可控、可恢复、可追溯。"),
        ],
        choice=[
            dict(q="比较 Coding Agent 时，最合理的方式是？", options=["只看哪个 demo 生成代码最多", "按交互、上下文、权限、扩展、恢复和观测等维度评估", "只看模型名称", "只看界面是否好看"], answer=[1], explain="B 正确。真实工程闭环由多维能力决定，不是单次 demo、模型名或界面能决定。"),
            dict(q="模型变强后，哪些 harness 逻辑仍不应删除？（多选）", options=["权限和沙箱", "审计日志和预算", "checkpoint 和结构化输出", "所有冗长固定思考模板"], answer=[0, 1, 2], explain="A、B、C 是工程边界。D 属于可能被删减的软性脚手架，不是必须保留。"),
            dict(q="终端型 Agent 的相对优势通常是？", options=["更适合仓库级命令流和 CI 集成", "一定比 IDE 型更懂当前光标", "不需要权限控制", "不能修改多文件"], answer=[0], explain="A 是公开稳定的形态差异。终端型不一定拥有编辑器光标上下文，仍需要权限控制，也可以修改多文件。"),
            dict(q="团队推广 Agent 时容易忽略什么？", options=["治理、审计、成本分摊和扩展来源", "代码是否能显示彩色", "模型是否会说中文", "是否支持自然语言"], answer=[0], explain="A 是生产推广常见难点。其他选项可能影响体验，但不是核心治理风险。"),
        ],
        short=[
            dict(q="说明终端型、IDE 型和 SDK/平台型 Agent 的差异。", points=["终端型适合仓库级和 CI", "IDE 型适合编辑器上下文和局部修改", "SDK/平台型适合嵌入流程", "比较权限、扩展、恢复和治理"], reference="终端型 Agent 以工作目录和命令行为中心，适合仓库级修改、运行测试、生成 diff 和接入 CI。IDE 型 Agent 贴近编辑器，能利用光标、选区、打开文件和内联修改体验，适合局部开发。SDK 或平台型 Agent 把能力嵌入任务系统、评审或测试平台，适合批量和无人值守流程，但调用方要处理隔离、权限和产物。三者不是简单强弱关系，应该按任务场景、权限模型、扩展方式、恢复能力和治理成本选择。"),
            dict(q="模型能力提升后，哪些 harness 逻辑可以考虑删除？", points=["过细固定思考模板", "重复工具说明", "低价值自检话术", "通过任务集 A/B 验证", "不删除硬边界"], reference="可以考虑删除的是为弥补旧模型理解能力而加的软性脚手架，例如冗长固定计划模板、要求复述显而易见步骤的规则、重复解释工具怎么用的大段提示、低价值自检话术。删除不能靠感觉，要用代表性任务集 A/B，观察通过率、轮数、成本和错误类型。如果删除后质量不降且成本下降，就可以简化。但权限、沙箱、工具 schema、审计、预算、checkpoint 和验证门禁不能因此删除，因为它们解决的是工程控制和组织治理问题。"),
            dict(q="如何做 Coding Agent 选型验证？", points=["构造代表性端到端任务集", "覆盖读、改、测、失败、回滚、权限", "记录成功率、轮数、成本、人工接管", "使用真实但脱敏场景", "避免只看 demo"], reference="选型验证应构造代表性端到端任务集，而不是只看演示。任务要覆盖代码理解、跨文件修改、运行测试、处理失败日志、权限阻断、回滚和结构化报告。场景最好来自真实工作但做脱敏，避免只测玩具项目。指标包括任务成功率、平均轮数、总 token、耗时、人工接管率、误操作、安全事件和产物质量。还要评估扩展接入、日志留存、成本报表和禁用机制。最终结论应说明适合哪些场景，不做绝对排名。"),
        ],
        labs=[],
        related=["harness-what", "harness-extend", "harness-headless", "arch-case-coding-agent"],
    ),
]
