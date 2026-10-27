BLOCKS = [
    dict(
        id="p1",
        order=1,
        slug="p1_fanout_orchestrator",
        title="fan-out 编排器",
        essence="有界并发 + 重试",
        triggers=[
            "一个请求拆成多个子任务",
            "限制同时运行的下游调用数",
            "每个子任务要带独立上下文",
            "失败要按次数重试",
            "运行超时要回收",
        ],
        statement="""### 题目
实现一个 fan-out 编排器。输入是一批互相独立的子任务、并发上限、最大重试次数、单次运行超时时间和父请求上下文。编排器要分批启动子任务，任何时刻运行中的任务数不能超过上限。每次启动子任务时，要给它一个上下文快照，不能让子任务共享同一个可变上下文。任务成功后记录结果；任务失败或超时后，如果没有超过最大尝试次数，就重新排队；如果已经达到上限，就记录最终失败。要求提供可观察的状态，能看见哪些任务还在等待、哪些任务正在运行、每个任务尝试了几次、哪些任务已经成功或失败。不要假设真实线程可用，接口可以设计成显式 poll、complete、fail、expire。""",
        states=[
            dict(name="pending", desc="等待启动的任务队列，保存还没有进入本轮执行的任务 id"),
            dict(name="running[task_id]", desc="正在运行的任务集合，记录 attempt、started_at 和上下文快照"),
        ],
        extra_states=[
            dict(name="attempts[task_id]", desc="每个任务已经启动过几次"),
            dict(name="results/errors", desc="任务的终态结果，成功和最终失败分开记录"),
            dict(name="clock", desc="注入时钟，用来判断运行超时"),
        ],
        invariants=[
            "running 的数量永远不能超过并发上限",
            "同一个任务同一时刻只能在 pending 或 running 中出现一次",
            "attempt 只在真正启动任务时递增，不能在排队时递增",
            "上下文必须按任务和尝试次数复制，不能共享可变对象",
            "成功任务不再重试，最终失败任务不再回到 pending",
        ],
        transitions="""```text
pending 队首 --poll/有空位--> running[task]
running[task] --complete--> results[task]
running[task] --fail/未达上限--> pending 队尾
running[task] --fail/已达上限--> errors[task]
running[task] --expire--> 走 fail 的同一条路径
```""",
        failures=[
            dict(case="重复：同一个任务被 poll 多次启动", handle="启动前检查任务不在 running、results、errors 中；启动后立即从 pending 移走。"),
            dict(case="失败：临时错误需要重试", handle="fail 时先移出 running，再根据 attempts 和 max_attempts 决定回 pending 还是进 errors。"),
            dict(case="并发：多个空位同时补任务", handle="poll 用 while 循环补位，但每次都检查 len(running) < limit。"),
            dict(case="超时：任务一直不回调", handle="expire 扫描 running，超过 timeout 的任务按失败处理，不能留在 running。"),
            dict(case="上下文污染：子任务改了父上下文", handle="启动时复制父上下文，并写入 task_id、attempt 等只属于本次运行的信息。"),
        ],
        walkthrough="""例子：任务 A、B、C，并发上限 2，最大尝试 2。初始 pending=[A,B,C]，running={}，attempts={}。第一次 poll，启动 A 和 B，pending=[C]，running={A:attempt1,B:attempt1}。A 成功，results={A:ok}，running 只剩 B。再次 poll，空位补 C，pending=[]，running={B:attempt1,C:attempt1}。B 失败，attempts[B]=1 未达上限，把 B 放回 pending=[B]。C 成功后 running={}。再 poll 启动 B 第二次，pending=[]，running={B:attempt2}。如果 B 这次成功，results 有 A、C、B；如果 B 再失败，errors={B:...}，不会再回队列。""",
        oral=dict(
            structure="这题我先抓两个状态：pending 队列和 running 集合。pending 表示还没启动的子任务，顺序决定下一批补谁；running 表示已经发出去但还没结束的子任务，里面要放 attempt、开始时间和上下文快照。最重要的不变量是 running 的数量不能超过并发上限。attempt 不应该在排队时加，只能在真正启动时加。成功和最终失败都是终态，不能再回到队列里。",
            flow="正常流程可以这样讲：初始化时所有任务都在 pending，running 为空。调用 poll 时，只要 running 还有空位，就从 pending 头部取任务，复制父上下文，加上 task_id 和 attempt，放入 running，并把这次启动记录返回给外部执行器。外部执行成功后调用 complete，编排器从 running 删除该任务，把结果写入 results。外部执行失败后调用 fail，编排器先从 running 删除它，再看 attempts 是否小于最大次数；如果还能重试，就把任务放回 pending 队尾；如果不能重试，就写入 errors。超时不是第三套逻辑，expire 只是找出运行太久的任务，然后复用失败路径。这样队列补位、结果记录、重试和超时都由同一个状态机控制。",
            pitfalls="最容易错的第一点是把并发理解成一次启动所有任务，然后靠 worker 自己限流，这样 running 数量会失控。第二点是 attempt 的时机错了，排队时就加次数会导致任务还没执行就用完重试额度。第三点是上下文直接传同一个 dict，某个子任务写入临时字段后会污染兄弟任务。第四点是超时后只记录错误但不从 running 删除，后续 poll 永远补不上空位。第五点是失败和超时写两套逻辑，最后两边的重试次数、错误记录和清理行为不一致。"
        ),
        followups=[
            dict(q="并发怎么办？", a="真实工程里用锁保护 pending、running、attempts 这些表。锁只包住状态修改，不包住真实下游调用。否则一个慢下游会阻塞所有任务的启动和完成。多进程场景要把状态放到外部存储或队列里。"),
            dict(q="重启怎么办？", a="内存 pending 和 running 会丢，所以要周期性持久化 run 状态。恢复时，results 可以直接保留；running 里的任务要么重新置为 pending，要么根据外部幂等键查询是否已经完成。不能盲目重复产生副作用。"),
            dict(q="规模扩大怎么办？", a="单机队列可以拆成分片队列，按任务类型或租户做限流。大批量任务不要一次全部放入内存，可以分页加载 pending。running 的超时扫描也要用小顶堆或时间轮，避免每次全表扫描。"),
            dict(q="如何处理不可重试错误？", a="错误要分类。网络抖动、限流可以重试；参数错误、权限错误通常直接终态失败。状态机可以在 fail 时接收 retryable 标志，retryable=False 时不看剩余次数，直接进入 errors。"),
        ],
        pitfalls=[
            "把所有任务一次性启动，导致并发上限只存在于注释里。",
            "attempt 在失败时递增，造成运行中的 attempt 和返回给执行器的 attempt 对不上。",
            "超时任务没有从 running 清理，后续调度被卡住。",
            "上下文浅层或直接共享，子任务之间互相污染字段。",
        ],
        complexity="每个任务每次尝试入队和出队一次，调度总时间 O(任务数 × 最大尝试次数)；pending、running、attempts、结果表总空间 O(任务数)。",
        variants=[
            dict(context="一个订单要同时通知短信、邮件、站内信和 webhook，每类通知失败可以重试，但同时最多发 3 个。", note="本质仍是 pending 等待队列加 running 运行集合，用并发上限和重试规则驱动状态变化。"),
            dict(context="一次日志回放要把 100 个分片发给下游处理，某个分片超时后重新排队。", note="分片就是子任务，超时复用失败重试路径。"),
            dict(context="批量查询多个供应商报价，单个供应商失败不影响其他供应商，但要限制并发请求数。", note="独立请求 fan-out，核心仍是补位、完成、失败和终态记录。"),
        ],
        lab="lab-sd-p1",
    ),
    dict(
        id="p2",
        order=2,
        slug="p2_dag_scheduler",
        title="DAG 分层调度 + 失败传播",
        essence="图算法 + 状态机",
        triggers=[
            "任务之间有前置依赖",
            "同一层任务可以并行",
            "失败要阻断所有下游",
            "需要检测环或非法依赖",
            "成功后释放后继任务",
        ],
        statement="""### 题目
实现一个 DAG 调度器。输入是一组任务和依赖边，依赖边 `(A, B)` 表示 B 必须等 A 成功后才能运行。调度器需要返回当前所有可运行任务，并在任务成功时释放下游，在任务失败时把所有依赖它的未开始下游标记为 blocked。要求构造阶段拒绝未知节点和环；运行阶段不能重复启动同一个任务，不能让未满足依赖的任务提前运行，也不能因为某个分支失败就错误地停止无关分支。接口可以是 start_ready、succeed、fail、status、is_done。真实执行可以由外部 worker 完成，本题只写确定性的调度状态机。""",
        states=[
            dict(name="indegree[task]", desc="每个任务还剩多少个未成功的前置依赖"),
            dict(name="children[task]", desc="每个任务成功或失败后需要影响哪些后继任务"),
        ],
        extra_states=[
            dict(name="status[task]", desc="pending、running、done、failed、blocked 的任务状态"),
            dict(name="errors[task]", desc="失败任务的错误原因，方便审计和展示"),
        ],
        invariants=[
            "只有 indegree 为 0 且 status 为 pending 的任务才能启动",
            "任务从 running 进入终态后不能再次改变",
            "成功只影响直接 children 的 indegree，不影响无关节点",
            "失败要递归阻断所有仍 pending 的下游",
            "有环图没有合法执行顺序，必须在构造阶段拒绝",
        ],
        transitions="""```text
pending + indegree=0 --start_ready--> running
running --succeed--> done，并让 children 的 indegree -= 1
running --fail--> failed
pending downstream --上游 failed/blocked--> blocked
blocked/failed/done 都是终态
```""",
        failures=[
            dict(case="重复：同一任务被 start_ready 返回两次", handle="返回任务前立刻把 status 改成 running。"),
            dict(case="失败：上游执行失败", handle="失败节点进入 failed，所有 pending 下游递归进入 blocked，无关分支继续。"),
            dict(case="并发：同层多个任务同时完成", handle="每个 succeed 只扣自己的 children 入度，扣到 0 的任务下一轮才会启动。"),
            dict(case="超时：运行中任务长时间不结束", handle="工程上由外层超时器调用 fail，本调度器只负责把失败传播给下游。"),
            dict(case="非法图：依赖引用未知任务或形成环", handle="构造时校验节点集合，并用拓扑计数检测环。"),
        ],
        walkthrough="""例子：A、B 都是 C 的前置。初始 indegree={A:0,B:0,C:2}，children={A:[C],B:[C]}，status 全是 pending。start_ready 返回 A、B，并把它们改成 running。A 成功后 status[A]=done，C 的 indegree 从 2 变 1，此时 C 不能启动。B 成功后 status[B]=done，C 的 indegree 从 1 变 0。下一次 start_ready 返回 C。若 A 失败，则 status[A]=failed，C 仍 pending，但它依赖失败上游，所以直接 blocked；B 如果已经 running 或可以运行，不受 C blocked 影响。""",
        oral=dict(
            structure="这题我会先说两个核心状态：indegree 和 children。indegree 记录一个任务还差几个前置任务成功，children 记录一个任务结束后会影响哪些下游。status 也需要有，但我会把它当辅助状态，用来区分 pending、running、done、failed、blocked。最重要的不变量是：只有 indegree 等于 0 且仍然 pending 的任务才能启动。成功只释放下游，失败只阻断下游，不能影响无关分支。",
            flow="正常流程是先建图。对每条依赖 A 到 B，把 B 的 indegree 加一，把 B 放进 A 的 children。构造后先做一次拓扑检测，发现环就直接报错。运行时调用 start_ready，扫描所有 pending 且 indegree 为 0 的任务，返回前把它们改成 running。某个任务成功时，只允许 running 状态调用 succeed，然后把它改成 done，并遍历 children，把仍 pending 的下游 indegree 减一。减到 0 的下游不会在 succeed 里直接执行，而是在下一轮 start_ready 返回。某个任务失败时，把它改成 failed，再递归遍历 children；只要下游还 pending，就标记 blocked，并继续阻断它的下游。这样独立分支不会被误伤。",
            pitfalls="第一类错误是只存 parents 不存 children，结果失败传播和成功释放都要全表扫描，复杂度和代码都变差。第二类错误是 start_ready 返回任务后不改 running，下一次调用会重复启动。第三类错误是成功时重复调用 succeed，导致 children 的 indegree 被扣成负数，下游提前运行。第四类错误是失败只阻断直接孩子，没有递归阻断孙子节点。第五类错误是遇到一个失败就全局停止，把本来可以继续执行的独立分支也标记失败。"
        ),
        followups=[
            dict(q="并发怎么办？", a="调度器只输出 ready 集合，不直接跑任务。多个 worker 可以抢 ready 任务，但抢占和状态改为 running 必须是原子操作。成功和失败回写也要校验当前状态，避免重复回调。"),
            dict(q="重启怎么办？", a="要持久化 status、indegree 和已完成产物。恢复时不要重新扣已经成功节点的 children；可以从持久化状态重新推导 ready 集合。running 任务需要根据心跳改回 pending 或标为失败。"),
            dict(q="规模扩大怎么办？", a="大图不要每次扫描所有节点找 ready，可以维护 ready 队列。children 用邻接表存储。跨机器时可以按子图分片，但跨分片边需要事件通知。"),
            dict(q="如何支持局部重跑？", a="先确定重跑起点，把它和依赖它的下游恢复成 pending，并重算这些节点的 indegree。已经成功且仍可信的上游产物可以复用。不能简单把全图清空。"),
        ],
        pitfalls=[
            "没有检测环，导致永远没有 ready 任务但调度器也不报错。",
            "重复边没有处理，可能让 indegree 多加一次，任务永远不能启动。",
            "失败传播覆盖 running 或 done 节点，破坏已经确定的结果。",
            "把 blocked 当 failed，导致错误归因不清楚。",
        ],
        complexity="建图 O(V+E)，拓扑检测 O(V+E)，每条边在成功或失败传播中最多处理一次；空间 O(V+E)。",
        variants=[
            dict(context="构建系统里，编译目标必须等源文件生成后才能开始，某个生成步骤失败会跳过依赖它的目标。", note="目标和生成步骤是节点，依赖边决定 indegree 和 children。"),
            dict(context="数据流水线中，清洗任务成功后才能跑特征任务，特征失败会阻断训练任务。", note="本质是 DAG 状态机，失败向下游传播，无关分支继续。"),
            dict(context="订单风控流程里，基础校验完成后才能做高阶评分，基础校验失败就不再运行后续评分。", note="只要有前置依赖和下游阻断，就是同一模式。"),
        ],
        lab="lab-sd-p2",
    ),
    dict(
        id="p3",
        order=3,
        slug="p3_agentic_loop",
        title="最小 agentic loop",
        essence="消息协议 + 循环",
        triggers=[
            "模型会请求工具调用",
            "工具结果要回填给模型",
            "未知工具不能让主循环崩溃",
            "需要最大步数防死循环",
            "消息历史要完整保留",
        ],
        statement="""### 题目
实现一个最小智能循环。输入是模型函数、工具表、初始消息和最大步数。每轮把当前消息历史交给模型；如果模型返回最终文本，就结束并返回内容和完整历史；如果模型返回工具调用，就把 assistant 的工具调用消息追加到历史里，再按顺序执行每个工具，把每个结果作为 tool 消息追加回历史。工具参数可能是字典，也可能是 JSON 字符串。未知工具、参数解析失败、工具执行异常都不能让主循环直接崩溃，而要变成可被模型看到的 tool 结果。循环必须有最大步数保护，不能无限调用模型。不要修改传入的原始消息列表。""",
        states=[
            dict(name="messages", desc="按顺序保存 user、assistant、tool 的完整消息历史"),
            dict(name="step", desc="已经完成的模型轮数，用来判断最大步数"),
        ],
        extra_states=[
            dict(name="tool_calls", desc="当前 assistant 消息里等待执行的工具调用列表"),
            dict(name="tools", desc="工具名到本地函数的映射"),
        ],
        invariants=[
            "每条 tool 消息必须对应前面 assistant 消息中的一个 tool_call_id",
            "工具异常是消息内容，不是主循环异常",
            "模型不再请求工具时才是正常终止",
            "每轮最多调用一次模型，然后执行这一轮返回的全部工具",
            "输入 messages 不能被原地修改",
        ],
        transitions="""```text
messages + step
  --model 返回 final--> 结束 final
  --model 返回 tool_calls--> 追加 assistant
assistant tool_calls --逐个执行工具--> 追加 tool 结果
step += 1，回到下一轮 model
step == max_steps 且未 final --> max_steps 结束
```""",
        failures=[
            dict(case="重复：同一个工具调用被执行两次", handle="一轮只遍历当前 assistant 返回的 tool_calls，执行后只追加结果，不把它重新放入待执行列表。"),
            dict(case="失败：工具抛异常", handle="捕获异常并写成 tool 消息，内容包含异常类型和信息，让模型下一轮处理。"),
            dict(case="并发：同轮多个工具调用", handle="最小版本按顺序执行，真实系统可以只并行只读工具，但回填仍要按 call_id 对齐。"),
            dict(case="超时：模型一直请求工具", handle="用 step 和 max_steps 停止，返回明确的 max_steps 状态。"),
            dict(case="协议错误：未知工具或 JSON 参数错误", handle="不要抛出主循环，统一转成 tool 结果消息。"),
        ],
        walkthrough="""例子：初始 messages=[user: 计算 2+3]，step=0。第一轮模型返回 assistant tool_calls=[add(id=c1,args={a:2,b:3})]。循环追加 assistant 消息，然后执行 add，得到 5，再追加 tool 消息 {tool_call_id:c1, content:'5'}。step 变 1。第二轮把完整 messages 交给模型，模型看到 tool 结果后返回 final='答案是 5'。循环返回 status=final、content='答案是 5'，messages 中保留 user、assistant tool_calls、tool result 三类消息。""",
        oral=dict(
            structure="这题我抓两个状态：messages 和 step。messages 是完整协议历史，不能只保存最后一句；step 是模型轮数，用来防止无限循环。辅助状态是当前轮的 tool_calls 和工具表。关键不变量是 tool 消息必须能对上前面的 tool_call_id，工具失败也要回填成消息。只有模型不再要求工具，才算正常 final；达到最大步数只是保护性停止。",
            flow="流程从复制输入 messages 开始，避免污染调用方。每轮先把历史传给模型。如果模型返回字符串或没有 tool_calls，就把它当最终回答返回。如果模型返回 tool_calls，就先追加 assistant 消息，里面保留 content 和 tool_calls。然后按顺序处理每个 call：解析 arguments，查工具名，调用工具，把返回值转成字符串，追加 role 为 tool 的消息，并带上 tool_call_id。未知工具、解析失败、工具异常都走同一条回填路径，只是 content 写错误信息。当前轮工具都回填后，step 加一，进入下一轮模型调用。如果循环到 max_steps 还没有 final，就返回 max_steps 状态和完整历史。",
            pitfalls="最常见错误是工具调用后不保存 assistant 消息，只保存 tool 结果；这样下一轮模型看不到自己之前请求了什么。第二个错误是工具抛异常就让 run 函数抛出，导致模型没有机会根据错误修正。第三个错误是按工具名而不是 call_id 回填，多个同名工具调用时会对不上。第四个错误是没有 max_steps，模型一直请求工具会死循环。第五个错误是直接修改传入 messages，外层重试或测试复用时会出现脏状态。"
        ),
        followups=[
            dict(q="并发怎么办？", a="可以把同一轮中的只读工具并行执行，但回填必须仍然和 call_id 对齐。写工具通常要串行或加审批屏障。并发执行的异常也要收敛成 tool 消息。"),
            dict(q="重启怎么办？", a="把 messages 和 step 持久化。恢复时从最后一个完整消息边界继续。如果最后只有 assistant tool_calls 没有全部 tool 结果，要么补执行缺失工具，要么写入恢复错误，不能跳过半截协议。"),
            dict(q="规模扩大怎么办？", a="长历史要接上下文裁剪或摘要，但裁剪必须保留未完成工具调用的配对关系。工具表变大后要加 schema 校验、权限控制和审计日志。"),
            dict(q="未知工具怎么处理？", a="不要直接报错退出。应该追加一条 tool 消息，说明工具不存在或未授权，让模型下一轮选择别的工具或给出失败解释。"),
        ],
        pitfalls=[
            "忘记追加 assistant tool_calls 消息，导致协议历史不完整。",
            "工具异常直接穿透，主循环提前崩溃。",
            "没有最大步数，遇到模型反复调用工具会死循环。",
            "JSON 字符串参数没有解析，工具收到错误类型。",
        ],
        complexity="设模型轮数为 S、工具调用总数为 T，循环本身时间 O(S+T)，消息空间 O(历史消息数)。工具执行耗时另计。",
        variants=[
            dict(context="客服机器人先查订单工具，再根据工具返回解释物流状态。", note="模型请求工具、工具结果回填、模型再回答，仍是同一循环。"),
            dict(context="运维助手先调用日志查询，再调用指标查询，最后生成排障建议。", note="多工具顺序执行和错误回填是核心。"),
            dict(context="表单助手发现缺字段时调用校验工具，校验失败后继续追问用户。", note="工具失败作为消息进入下一轮，而不是让程序崩溃。"),
        ],
        lab="lab-sd-p3",
    ),
    dict(
        id="p4",
        order=4,
        slug="p4_context_trimming",
        title="上下文预算裁剪",
        essence="数据结构不变量",
        triggers=[
            "长对话超过模型预算",
            "不能留下孤儿 tool 消息",
            "system 消息必须保留",
            "最后一条用户消息必须保留",
            "工具调用和工具结果要成组裁剪",
        ],
        statement="""### 题目
实现一个上下文裁剪函数。输入是消息列表、最大预算和 token 计数函数，输出裁剪后的消息列表。要求保护所有 system 消息和最后一条 user 消息，即使预算不足也不能删除。普通历史消息可以丢弃，但 assistant 发起 tool_calls 后，紧随其后的对应 tool 结果必须和它作为一个整体保留或整体删除，不能留下没有父调用的 tool 消息，也不能留下缺少结果的工具调用单元。裁剪策略优先保留较新的可选上下文，最后输出仍按原始顺序排列。不要修改输入列表，也不要把单条 tool 消息当成普通消息单独保留。""",
        states=[
            dict(name="message_units", desc="把普通消息和 assistant tool_calls + 对应 tool 结果打包后的单元列表"),
            dict(name="protected_units", desc="必须保留的单元集合，包括 system 和最后一条 user 所在单元"),
        ],
        extra_states=[
            dict(name="budget", desc="最大可用 token 预算"),
            dict(name="used", desc="已经选中单元的 token 成本"),
            dict(name="cost[unit]", desc="每个单元的 token 成本"),
        ],
        invariants=[
            "assistant tool_calls 和对应 tool 结果必须一起保留或一起删除",
            "所有 system 消息必须保留",
            "最后一条 user 消息必须保留",
            "输出消息顺序必须和输入顺序一致",
            "输入消息不能被原地修改",
        ],
        transitions="""```text
messages --扫描--> message_units
message_units --标记 system/last user--> protected_units
protected_units 先进入 kept，used += cost
从后往前尝试 optional units：能放入预算就 kept
kept units --按原顺序展开--> trimmed messages
```""",
        failures=[
            dict(case="重复：同一条消息被多个单元引用", handle="扫描时用索引单调前进，打包 tool 结果后继续从下一个未消费位置开始。"),
            dict(case="失败：预算小于保护消息成本", handle="保护单元仍然保留，返回结果可以超过预算，但不能破坏硬不变量。"),
            dict(case="并发：裁剪函数被多请求复用", handle="函数内部只用局部变量，并复制消息对象，避免共享可变状态。"),
            dict(case="超时：计数函数很慢或外部 tokenizer 不稳定", handle="工程上缓存单元成本；本题只调用注入的计数函数，不做网络计数。"),
            dict(case="孤儿：只保留 tool 结果", handle="tool 消息不单独成可选上下文，必须跟父 assistant 单元绑定。"),
        ],
        walkthrough="""例子：messages=[system S, user U1, assistant call t1, tool result t1, assistant A2, user U3]，每条成本 1，预算 4。先打包 units：unit0=[S]，unit1=[U1]，unit2=[assistant call, tool result]，unit3=[A2]，unit4=[U3]。protected 是 unit0 和 unit4，used=2。可选单元从后往前看，unit3 成本 1，可以保留，used=3；unit2 成本 2，放进去会超过 4，所以整组丢弃，不能只留 tool；unit1 成本 1，可以保留或按策略看剩余，若保留 used=4。最后按原顺序展开 kept。""",
        oral=dict(
            structure="这题我先讲两个状态：message_units 和 protected_units。message_units 是裁剪的基本单位，不一定是一条消息；如果 assistant 有 tool_calls，它和后面的 tool 结果要打包。protected_units 是硬保护集合，至少包含 system 消息和最后一条 user 消息。最重要的不变量是不能出现孤儿 tool 消息，也不能把一个工具调用链拆开。预算是辅助状态，不应该凌驾于协议正确性之上。",
            flow="正常流程是先复制输入消息，然后从头扫描。普通 user、assistant、system 各自成一个 unit；如果遇到带 tool_calls 的 assistant，就收集它后面 tool_call_id 能对应上的连续 tool 消息，作为同一个 unit。打包完成后，找出所有包含 system 的 unit，再找出最后一条 user 所在 unit，这些都放入 protected。接着计算每个 unit 的成本，先把 protected 放入 kept。然后从消息末尾往前遍历可选 unit，能放进预算就加入 kept，放不下就丢弃。最后按原始 unit 顺序展开 kept，返回新的消息对象列表。",
            pitfalls="第一大坑是按单条消息裁剪，最后留下 role=tool 但前面没有 assistant tool_calls，模型协议直接坏掉。第二大坑是为了严格预算删除 system 或最后 user，导致模型失去规则或当前问题。第三大坑是从后往前选完后直接倒序输出，破坏对话顺序。第四大坑是只按 assistant 是否有 tool_calls 打包，但没有检查 tool_call_id，可能把不相关的 tool 结果吃进去。第五大坑是原地 pop 输入列表，外层还要用原历史时就出错。"
        ),
        followups=[
            dict(q="并发怎么办？", a="裁剪函数最好是纯函数，不依赖全局缓存。若 tokenizer 成本缓存是共享的，要用线程安全结构，但消息列表本身不能被原地修改。"),
            dict(q="重启怎么办？", a="裁剪不是业务状态，重启后可以重新计算。但如果做了摘要压缩，摘要要带来源范围和版本，避免恢复后不知道摘要覆盖了哪些消息。"),
            dict(q="规模扩大怎么办？", a="大量历史可以先分层：最近窗口直接保留，较远历史先摘要，工具大输出改成引用。unit 成本可以缓存，避免每次全量重新计数。"),
            dict(q="预算太小怎么办？", a="硬保护优先，允许结果超过预算并返回告警，或者触发更强压缩。不能为了凑预算返回协议非法的消息。"),
        ],
        pitfalls=[
            "先删消息再分组，容易留下孤儿 tool 消息。",
            "把最后一条 assistant 当保护对象，却忘了最后一条 user 才是当前问题。",
            "严格控制预算而删除 system，导致规则丢失。",
            "输出顺序按选择顺序排列，破坏原对话顺序。",
        ],
        complexity="分组、标记、选择、展开都是线性扫描，时间 O(n)，空间 O(n)，其中 n 是消息数。",
        variants=[
            dict(context="客服对话太长，要删旧消息，但不能把订单查询结果和发起查询的消息拆开。", note="工具调用和结果必须作为 unit 裁剪。"),
            dict(context="日志分析助手要压缩历史，系统安全规则和用户最新问题必须保留。", note="system 和最后 user 是 protected units。"),
            dict(context="多轮表单填写中，校验工具的错误结果不能单独留在上下文里。", note="孤儿 tool 消息会让下一轮模型误解状态。"),
        ],
        lab="lab-sd-p4",
    ),
    dict(
        id="p5",
        order=5,
        slug="p5_token_bucket",
        title="令牌桶限流 + 按租户分桶",
        essence="限流 + 并发安全",
        triggers=[
            "限制平均请求速率",
            "允许短时间突发",
            "不同租户额度互不影响",
            "用时钟补充令牌",
            "检查和扣减必须原子",
        ],
        statement="""### 题目
实现一个按租户分桶的令牌桶限流器。每个租户都有自己的桶，桶容量为 capacity，按 rate 个令牌每秒补充，最多补到 capacity。每次请求指定 tenant 和 cost，限流器要先根据当前时间补充该租户令牌，再判断令牌是否足够；足够则扣减并返回允许，不足则返回拒绝。第一次访问某个租户时，该租户从满桶开始。接口要支持注入时钟，方便确定性测试，不允许用真实 sleep。要求 cost 必须为正数，不同租户互相隔离；真实工程版需要保证同一个租户的补充、判断、扣减是原子的。""",
        states=[
            dict(name="tokens[tenant]", desc="某个租户当前可用令牌数，可以是小数"),
            dict(name="last_refill[tenant]", desc="某个租户上次按时间补充令牌的时间点"),
        ],
        extra_states=[
            dict(name="rate", desc="每秒补充令牌数"),
            dict(name="capacity", desc="桶容量，也是突发上限"),
            dict(name="clock", desc="注入时钟，避免依赖真实时间"),
        ],
        invariants=[
            "每个租户的 tokens 永远在 0 到 capacity 之间",
            "同一次请求的 refill、检查、扣减必须作为一个原子步骤",
            "租户之间的桶互相独立，不能共享 tokens",
            "拒绝请求不能扣减令牌",
            "时间回拨不能让令牌变成负数或额外增加",
        ],
        transitions="""```text
allow(tenant, cost):
  elapsed = max(0, now - last_refill[tenant])
  tokens = min(capacity, tokens + elapsed * rate)
  last_refill = now
  if tokens >= cost: tokens -= cost，返回 True
  else: tokens 不变，返回 False
```""",
        failures=[
            dict(case="重复：同一请求被重放", handle="限流器本身只负责额度；如果要请求幂等，需要在外层用请求 id 去重。"),
            dict(case="失败：令牌不足", handle="返回 False，不扣减 tokens，并可额外返回预计等待时间。"),
            dict(case="并发：两个请求同时看到足够令牌", handle="真实工程中用锁、原子脚本或事务把 refill 和扣减包成原子操作。"),
            dict(case="超时：调用方等待令牌太久", handle="本题不 sleep；工程上可返回 wait_time，让调用方自己排队或快速失败。"),
            dict(case="时间异常：时钟回拨", handle="elapsed 使用 max(0, now-last_refill)，并把 last_refill 更新到当前可接受时间。"),
        ],
        walkthrough="""例子：rate=2，capacity=5，租户 A 在 t=0 第一次请求 cost=5。初始化 tokens[A]=5，last_refill[A]=0，允许后 tokens[A]=0。t=1.5 再请求 cost=3，elapsed=1.5，补充 3 个令牌，tokens 变 3，允许后 tokens=0，last_refill=1.5。t=10 再请求 cost=1，elapsed=8.5，理论补充 17，但封顶为 5，扣 1 后 tokens=4。租户 B 第一次来仍然是满桶 5，不受 A 影响。""",
        oral=dict(
            structure="这题我只需要记住两个核心状态：tokens 和 last_refill，而且它们都是按租户分开的。tokens 表示当前还能花多少额度，last_refill 表示上次结算时间。最重要的不变量是 tokens 不能小于 0，也不能超过 capacity。每次请求都先根据时间补充，再判断是否足够，足够才扣减。真实并发里，这三步必须原子化，否则会出现超卖。",
            flow="正常流程是 allow 收到 tenant 和 cost。先检查 cost 必须大于 0。然后取当前时间 now，如果这个 tenant 没见过，就初始化 tokens=capacity、last_refill=now。接着计算 elapsed=now-last_refill，如果时间回拨就按 0 处理。新的 tokens 等于旧 tokens 加 elapsed 乘 rate，但最多是 capacity，并把 last_refill 更新为 now。然后比较 tokens 和 cost：如果 tokens 足够，就扣掉 cost，返回 True；如果不够，就保持 tokens 不变，返回 False。注意租户 A 的状态只存在 A 的桶里，不会影响租户 B。",
            pitfalls="第一类错误是忘记封顶，系统空闲很久后 tokens 累积到远超 capacity，突发流量失控。第二类错误是所有租户共用一个 tokens，导致大租户把小租户额度耗光。第三类错误是先扣减再判断，拒绝请求也消耗额度。第四类错误是并发下没有原子保护，两个请求都看到 tokens=1，然后都通过。第五类错误是用 sleep 写测试，浏览器和单元测试都会变慢且不稳定。"
        ),
        followups=[
            dict(q="并发怎么办？", a="单机用每个租户一把锁，或用分片锁降低竞争。分布式用支持原子读改写的存储，例如脚本或事务。关键是 refill、比较、扣减不能拆成多个可交错步骤。"),
            dict(q="重启怎么办？", a="内存桶重启会丢状态。严格限流要把 tokens 和 last_refill 放到外部存储；不严格的边缘限流可以接受重启后满桶，但要知道这会放大短时突发。"),
            dict(q="规模扩大怎么办？", a="租户很多时要懒初始化，并清理长时间不用的桶。热点租户可以单独分片。跨机限流要用集中状态或把租户稳定路由到同一分片。"),
            dict(q="如何返回等待时间？", a="如果 tokens 不足，缺口是 cost-tokens，等待时间是缺口除以 rate。rate 为 0 时表示永远等不到，应该直接拒绝或返回无穷等待。"),
        ],
        pitfalls=[
            "没有 capacity 封顶，空闲后突发无限放大。",
            "所有租户共享一个桶，隔离性失效。",
            "拒绝请求也扣令牌，导致越拒绝越难恢复。",
            "用真实 sleep 测试 refill，造成测试慢且不确定。",
        ],
        complexity="每次 allow 只访问一个租户桶，时间 O(1)，每个活跃租户占 O(1) 空间，总空间 O(租户数)。",
        variants=[
            dict(context="消息推送平台限制每个商户每秒最多发送 100 条，但允许短时攒到 500 条。", note="每个商户一个令牌桶，rate 是平均速率，capacity 是突发上限。"),
            dict(context="开放 API 对每个访问方单独限流，某个访问方打满不能影响别人。", note="按租户分桶正是隔离额度。"),
            dict(context="日志写入服务允许每个应用短暂突增，但长期写入速度要受控。", note="令牌随时间补充，足够才允许写入。"),
        ],
        lab="lab-sd-p5",
    ),
    dict(
        id="p6",
        order=6,
        slug="p6_idempotent_executor",
        title="幂等执行器 / singleflight",
        essence="singleflight + 状态机",
        triggers=[
            "同一个 key 并发只执行一次",
            "重复请求不能重复产生副作用",
            "等待者共享 leader 的结果",
            "成功结果可以缓存",
            "失败不应缓存成成功",
        ],
        statement="""### 题目
实现一个幂等执行器。调用方用 key 表示一次有副作用的业务操作，例如支付回调、订单创建或消息投递。同一个 key 如果已经成功完成，后续请求要直接返回缓存结果；如果同一个 key 正在执行，只允许第一个请求成为 leader 真正执行副作用，其他请求成为 follower，等待或读取同一轮结果；如果 leader 成功，则写入 completed 缓存并通知等待者；如果 leader 失败，则本轮等待者看到同一个异常或错误，但不能把失败写成成功缓存，下一次同 key 请求可以重新执行。接口可以拆成 begin、complete、fail、waiters_result，用同步状态机模拟并发。""",
        states=[
            dict(name="completed[key]", desc="已经成功完成的 key 到结果的映射"),
            dict(name="inflight[key]", desc="正在执行的 key 到本轮 leader token 和等待者状态的映射"),
        ],
        extra_states=[
            dict(name="lock", desc="真实工程里保护 completed 和 inflight，但不包住副作用执行"),
            dict(name="notification[key]", desc="本轮 leader 完成后，等待者可以读取的结果或异常"),
            dict(name="token", desc="区分当前 leader 和过期 leader 的执行凭证"),
        ],
        invariants=[
            "同一个 key 同一时刻只能有一个 leader 执行副作用",
            "成功才写 completed，失败不能写成功缓存",
            "follower 必须看到与 leader 同一轮的结果或异常",
            "锁只保护状态表，不能包住真实副作用",
            "过期 leader 不能覆盖新一轮 inflight 状态",
        ],
        transitions="""```text
不存在 --begin--> inflight[key]=RUNNING，本请求是 leader
inflight 存在 --begin--> follower，拿到同一 token
RUNNING --complete/token 匹配--> completed[key]=result，通知 ok，删除 inflight
RUNNING --fail/token 匹配--> 通知 error，删除 inflight，不写 completed
completed 存在 --begin--> cached result
```""",
        failures=[
            dict(case="重复：成功后的同 key 再次请求", handle="begin 先查 completed，命中后直接返回 cached，不再进入 inflight。"),
            dict(case="失败：leader 执行抛异常", handle="删除 inflight，通知等待者 error，但不写 completed，允许下次重试。"),
            dict(case="并发：两个请求同时 begin", handle="真实工程用锁让检查 completed、检查 inflight、创建 inflight 成为原子步骤。"),
            dict(case="超时：leader 长时间不 complete", handle="工程上给 inflight 加租约或超时回收；回收时要防止旧 leader 之后又写回。"),
            dict(case="过期：旧 leader 失败后又 complete", handle="complete/fail 必须校验 token 等于当前 inflight token。"),
        ],
        walkthrough="""例子：key=pay-1。初始 completed={}，inflight={}。请求 R1 调 begin，发现没有 completed 和 inflight，于是创建 inflight[pay-1]={token:1}，R1 是 leader。R2 同时调 begin，发现 inflight 已存在，返回 follower 和 token 1，不执行副作用。R1 执行业务成功后调用 complete(pay-1,1,'ok')，状态变成 completed={pay-1:'ok'}，inflight 删除，notification={pay-1:('ok','ok')}。R2 读取 waiters_result，看到同一结果。之后 R3 再 begin(pay-1)，直接返回 cached。若 R1 调 fail，则 completed 仍为空，下一次 begin 会产生 token 2 的新 leader。""",
        oral=dict(
            structure="这题我会先说两个核心状态：completed 和 inflight。completed 存成功结果，表示这个 key 的副作用已经确定完成；inflight 存正在执行的那一次，里面至少要有 leader token。最重要的不变量是同一个 key 同一时刻只能有一个 leader 真正执行副作用。follower 不能再执行一遍，只能等 leader 的结果。成功才缓存，失败不缓存。锁只保护这两张表，不能包住业务函数。",
            flow="正常流程是 begin 先查 completed，命中就返回 cached。没命中再查 inflight，如果已经有人在执行，就返回 follower 和当前 token。两者都没有，才创建 inflight，生成新 token，当前请求成为 leader。leader 在锁外执行真实副作用。成功后调用 complete，complete 要重新检查 key 还在 inflight 且 token 匹配，然后删除 inflight，写 completed，并把结果发布给等待者。失败后调用 fail，也要检查 token，删除 inflight，发布错误给等待者，但不写 completed。这样同一轮等待者看到同一个结果，下一轮是否重试由 completed 是否存在决定。",
            pitfalls="最危险的错误是把业务函数放在全局锁里执行，一个慢请求会拖死所有 key。第二个错误是 follower 发现 inflight 后自己也执行副作用，幂等目标直接失败。第三个错误是失败也写入 completed，导致这个 key 永久返回失败结果，无法重试。第四个错误是先唤醒等待者再写结果，等待者可能读到空状态。第五个错误是没有 token，旧 leader 超时后又回来 complete，会覆盖新一轮执行结果。"
        ),
        followups=[
            dict(q="并发怎么办？", a="用锁保护 completed 和 inflight 的读写，或者用外部存储的原子插入。leader 选出后必须释放锁再执行副作用。complete 和 fail 再短暂拿锁校验 token 并发布结果。"),
            dict(q="重启怎么办？", a="内存状态会丢。要用持久化幂等表记录 key、状态、结果凭证和更新时间。重启后 RUNNING 太久的记录要进入对账或可重试状态，不能盲目判成功。"),
            dict(q="规模扩大怎么办？", a="按 key 做分片，减少锁竞争。completed 可以设置 TTL 或只保存结果引用。热点 key 的等待者数量要限制，避免一个慢操作挂住大量连接。"),
            dict(q="超时怎么办？", a="给 inflight 加租约时间。租约过期后可以允许新 leader，但必须用 token 或版本号防止旧 leader 回写。对外部副作用还要有业务幂等键。"),
        ],
        pitfalls=[
            "锁包住真实副作用，导致不同 key 也互相阻塞。",
            "失败写入 completed，后续永远不能重试。",
            "follower 没有等待同一结果，而是自己又执行一遍。",
            "没有 token 或版本，旧 leader 覆盖新执行。",
        ],
        complexity="begin、complete、fail 对单个 key 都是 O(1)；空间 O(成功缓存 key 数 + 正在执行 key 数)。持久化和清理策略另计。",
        variants=[
            dict(context="支付回调可能重复到达，同一个支付单号只能入账一次，并发重复回调要共享同一结果。", note="支付单号就是 key，completed 防重复，inflight 防并发双执行。"),
            dict(context="图片转码请求用文件哈希作为 key，同一文件同时提交时只转码一次。", note="leader 做转码，follower 等同一产物。"),
            dict(context="消息投递接口按业务消息 id 去重，成功投递后重复请求直接返回已投递。", note="成功缓存和失败可重试是同一状态机。"),
        ],
        lab="lab-sd-p6",
    ),
]

DESIGNS = []
