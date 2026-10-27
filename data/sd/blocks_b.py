BLOCKS = [
    dict(
        id="p7",
        order=7,
        slug="p7_in_order_delivery",
        title="乱序事件按序交付",
        essence="序号 + 缓冲区",
        triggers=["事件带递增序号但乱序到达", "断线重连后会重复推送", "只能按序交给下游", "补齐缺口后要一次吐出", "重复事件不能重复消费"],
        statement="""题目：实现一个事件交付组件。上游发送的每条事件都有正整数序号，序号从指定起点开始递增。网络抖动、重试和断线重连会让事件乱序到达，也可能让同一序号的事件重复到达。组件对外提供 `push(seq, event)`，每次收到一条事件后，返回本次已经可以交给下游的事件列表。下游要求严格按序消费，不能看到跳号事件，也不能重复看到同一序号。组件需要能处理未来事件暂存、历史重复丢弃、缓冲重复丢弃、非法序号拒绝。不要依赖 sleep、线程或真实网络。""",
        states=[dict(name="next_seq", desc="下一个必须交付的序号，之前的序号都已经交付或被明确跳过"), dict(name="buffer", desc="暂存已经收到但还不能交付的未来事件，按 seq 查找")],
        extra_states=[dict(name="window", desc="工程上可选的最大缓冲窗口，用来限制极远序号撑爆内存"), dict(name="gap_since", desc="工程上可选的缺口出现时间，用来触发补拉或告警")],
        invariants=["next_seq 之前的事件绝不能再次交付", "buffer 中的序号必须大于等于 next_seq，且同一 seq 只存一份", "每次补齐 next_seq 后，都要连续排空直到遇到第一个缺口", "push 的返回列表内部必须严格按序", "非法 seq 不能进入状态机"],
        transitions="""```text
收到 seq < next_seq      -> 已交付重复，丢弃，状态不变
收到 seq > next_seq      -> 写入 buffer[seq]，等待缺口
收到 seq == next_seq     -> 交付 event，next_seq += 1
while buffer 有 next_seq -> 继续交付并推进 next_seq
断线重连重复推送         -> 由 next_seq 与 buffer 两处去重吸收
```""",
        failures=[dict(case="重复：已经交付过的序号又来了", handle="因为 seq < next_seq，直接返回空列表，不修改 buffer"), dict(case="重复：未来事件已经在缓冲区里", handle="因为 seq in buffer，丢弃新事件，保留第一次收到的内容"), dict(case="失败：中间序号长期缺失", handle="基础版继续等待；工程版记录缺口时间，超时后补拉、告警或显式跳过"), dict(case="并发：多个线程同时 push", handle="真实工程要用锁或单消费者队列保护 next_seq 和 buffer，本题用同步接口模拟"), dict(case="超时：重连后服务端只重放部分区间", handle="客户端用 last_delivered_seq + 1 重新订阅，缺失区间不能静默当作成功")],
        walkthrough="""最小例子：起点是 1。初始 `next_seq=1, buffer={}`。先收到 `(2, B)`，2 大于 1，写入 `buffer={2:B}`，返回 `[]`。再收到 `(3, C)`，继续暂存，`buffer={2:B,3:C}`。收到 `(1, A)`，正好等于 `next_seq`，先交付 A，`next_seq=2`；发现 buffer 里有 2，交付 B，`next_seq=3`；再发现有 3，交付 C，`next_seq=4`。返回 `[A,B,C]`，buffer 清空。后来 `(2, B2)` 再来，因为 2 小于 4，说明已经交付，返回空。""",
        oral=dict(
            structure="这题我先抓两个状态：一个是 `next_seq`，表示下一个必须交付的序号；另一个是 `buffer`，保存已经收到但前面有缺口的事件。最重要的不变量是：`next_seq` 之前的序号不能再次交付，buffer 里不能有已经过期的序号。每次收到事件，只判断它和 `next_seq` 的关系：小了丢弃，大了暂存，等于就交付并连续排空。",
            flow="正常流程可以这样说：初始化时 `next_seq` 等于起始序号，buffer 为空。收到未来序号时，说明前面还有缺口，不能交给下游，只把它按序号放进 buffer。收到当前期望序号时，先把这条事件放进返回列表，然后推进 `next_seq`。推进后要立刻检查 buffer 里是否已经有新的 `next_seq`，有就继续取出、追加、推进，直到遇到第一个缺口。重复事件分两类：如果序号小于 `next_seq`，它已经交付过；如果序号已经在 buffer 里，它已经暂存过。两类都返回空列表。",
            pitfalls="易错点主要有四个。第一，只交付当前这一条，忘记 while 排空 buffer，结果 2、3 已经到达时，1 到了也只吐 1，后续事件被卡住。第二，只用 `seq < next_seq` 去重，忘记 `seq in buffer`，未来重复事件会覆盖原事件。第三，接受字符串、浮点数或 True 这种序号，排序和比较会出现隐蔽错误。第四，工程上不限制窗口，缺一个很小的序号时，极远的未来序号会把内存撑大。并发版本还要注意锁只保护状态，不要让下游消费在锁里执行。",
        ),
        followups=[dict(q="并发 push 怎么办？", a="把 `next_seq` 和 `buffer` 视为同一份临界状态。可以用一把锁保护 `push` 的整个状态变化，也可以把所有事件放入单消费者队列。不要在持锁时调用下游消费逻辑，否则慢消费者会阻塞上游。"), dict(q="断线重连怎么续传？", a="客户端持久化最后成功交付的序号。重连时从 `last_delivered_seq + 1` 请求重放。服务端可以重复发送已收到事件，客户端靠 `next_seq` 与 `buffer` 去重。"), dict(q="规模扩大后 buffer 很大怎么办？", a="设置最大窗口，只接受 `seq < next_seq + window` 的事件。超过窗口的事件要拒绝或告警。还可以在缺口超时后主动补拉缺失区间。"), dict(q="能不能全局按序？", a="如果只有单分区序号，很容易按序。多分区时通常只能保证分区内有序。全局有序需要统一提交日志或全局序号分配器，成本更高。")],
        pitfalls=["忘记连续排空，补齐缺口后仍然卡住", "缓冲重复事件覆盖第一次收到的事件", "把 bool 当 int 接受，导致 True 和 1 混淆", "没有窗口上限，缺口长期不补时内存增长", "并发修改 next_seq 和 buffer 导致重复交付"],
        complexity="单次 push 均摊 O(1)，补齐大缺口时单次 O(k)；空间 O(未交付窗口大小)。",
        variants=[dict(context="消息推送客户端重连后，服务端从某个序号开始重放，客户端只能按序展示。", note="仍然是 next_seq 判断已展示边界，buffer 吸收乱序和重复。"), dict(context="日志采集端批量上传时部分批次先到，消费端必须按 offset 写入。", note="offset 就是 seq，未连续的 offset 只能暂存。"), dict(context="订单状态事件先收到已发货，后收到已付款，页面必须按业务序列更新。", note="只要题目给了严格序号，本质就是按序交付状态机。")],
        lab="lab-sd-p7",
    ),
    dict(
        id="p8",
        order=8,
        slug="p8_lru_ttl_cache",
        title="LRU + TTL 缓存",
        essence="缓存淘汰",
        triggers=["缓存有容量上限", "最近使用的数据要保留", "每条记录会过期", "读命中要刷新顺序", "过期项不能占容量"],
        statement="""题目：实现一个本地缓存。缓存有固定容量，保存 key 到 value 的映射。每个条目可以有过期时间，过期后读它应当表现为未命中。容量满时，如果还要写入新条目，需要淘汰最久没有被使用的未过期条目。读命中和写入都算一次最近使用。缓存需要支持默认 TTL，也允许单次写入覆盖 TTL；`None` 可以作为合法 value，所以不能用返回值是否为 None 判断命中。为了测试稳定，时间由外部 clock 注入，不使用 sleep。""",
        states=[dict(name="ordered entries", desc="按最近使用排序的条目表，通常最旧在前、最新在后"), dict(name="expire_at", desc="每个 key 对应的绝对过期时间，或永不过期标记")],
        extra_states=[dict(name="capacity", desc="最大条目数，只统计未过期条目"), dict(name="clock", desc="注入时钟，让 TTL 逻辑可测试")],
        invariants=["命中的 get 必须把该 key 移到最近使用端", "过期条目等同未命中，不能继续占容量", "写入已有 key 要同时刷新 value、expire_at 和使用顺序", "容量超限时只淘汰最久未使用的有效条目", "存储的 None 与未命中必须能区分"],
        transitions="""```text
put 新 key      -> 计算 expire_at，插入最近使用端，必要时淘汰最旧项
put 已有 key    -> 覆盖 value/expire_at，移动到最近使用端
get 命中未过期  -> 返回 value，移动到最近使用端
get 命中过期    -> 删除该 key，返回 default
len / contains  -> 先惰性清理过期项，再回答
```""",
        failures=[dict(case="重复：同一个 key 反复 put", handle="覆盖旧值并刷新 TTL 与 LRU 顺序，不保留多个副本"), dict(case="失败：clock 到期后仍返回旧值", handle="每次 get、len、contains 前检查 expire_at，过期就删除"), dict(case="并发：读写同时修改有序表", handle="真实工程要加锁或使用分片锁，本题用同步状态机练核心逻辑"), dict(case="超时：系统时间回拨", handle="优先用单调时钟；如果用墙钟，要接受回拨带来的异常并做监控"), dict(case="容量：过期项还在表里", handle="写入前先清理过期项，避免错误淘汰仍有效的热 key")],
        walkthrough="""例子：容量 2，默认不过期。初始 entries 为空。put a=1 后顺序是 `[a]`；put b=2 后是 `[a,b]`，a 最旧。get a 命中，把 a 移到最新，顺序变成 `[b,a]`。put c=3 时容量会变成 3，需要淘汰最旧的 b，剩下 `[a,c]`。如果 TTL 是 10 秒，x 在 t=0 写入，expire_at=10；t=9.9 get x 命中并刷新顺序；t=10 get x，发现 now >= expire_at，删除 x 并返回默认值。""",
        oral=dict(
            structure="这题我会先说两个核心状态：一个是按最近使用排序的 entries，另一个是每个条目的 `expire_at`。entries 负责回答谁最久没用，expire_at 负责回答这个 key 是否还有效。关键不变量是：过期项等同不存在，命中必须刷新最近使用顺序，容量淘汰只在有效条目里淘汰最久未使用的那个。这样 LRU 和 TTL 两条规则不会互相打架。",
            flow="正常流程是：put 时先算这条记录的过期时间，如果 key 已存在就覆盖 value 和 expire_at，并把它移到最近使用端；如果是新 key，也插入最近使用端。插入后如果容量超了，就从最旧端开始弹出。get 时先看 key 是否存在，再看当前时间是否已经到 `expire_at`。如果过期，删除并返回 default；如果未过期，返回 value，并把 key 移到最近使用端。len 和 contains 也要先清理过期项，否则过期数据会继续占容量。",
            pitfalls="常见错误有五个。第一，get 命中后不更新顺序，导致热 key 被当成冷 key 淘汰。第二，只在后台清理 TTL，本题没有后台线程，测试中就会读到过期值。第三，用 `dict.get` 返回 None 判断不存在，结果存了 None 的合法 key 被误判为未命中。第四，put 更新已有 key 时只改 value，不刷新 expire_at，导致刚更新就过期。第五，写入新 key 前不清理过期项，容量满时错误淘汰一个有效老 key，而不是移除已经过期的垃圾。",
        ),
        followups=[dict(q="并发读写怎么办？", a="有序表和过期表要作为一个整体更新。简单做法是一把锁保护 get、put、delete。高并发下可以按 key 分片，但同一分片内仍要保护顺序链表和索引一致。"), dict(q="重启后缓存要恢复吗？", a="普通内存缓存通常不保证恢复。若要恢复，需要持久化 value、expire_at 和最近使用顺序。恢复时先丢弃已过期项，避免旧数据占容量。"), dict(q="规模扩大怎么办？", a="单机容量大时要分片，降低锁竞争。分布式缓存里 LRU 可能只在每个分片内近似成立。TTL 清理可用惰性删除加周期扫描结合。"), dict(q="为什么要注入 clock？", a="注入 clock 可以不用 sleep 就测试边界时间。工程里也更容易统一使用单调时钟，避免系统时间调整导致缓存行为不稳定。")],
        pitfalls=["命中不 move_to_end，LRU 顺序失真", "过期项不删除，长度和容量判断错误", "None 值与未命中混淆", "更新 key 不刷新 TTL", "使用真实 sleep 测 TTL，测试慢且不稳定"],
        complexity="get/put/delete 期望 O(1)；惰性全量清理可能 O(n)，可按需优化；空间 O(capacity)。",
        variants=[dict(context="接口结果缓存最近访问的用户资料，5 分钟后必须重新查库。", note="用户资料是 value，访问顺序决定淘汰，过期时间决定是否可用。"), dict(context="模型调用结果缓存，容量满时保留最近命中的 prompt。", note="prompt 是 key，命中刷新 LRU，TTL 防止旧结果长期复用。"), dict(context="验证码校验记录只能短时间有效，同时内存最多保存固定数量。", note="TTL 决定有效期，容量淘汰保护内存。")],
        lab="lab-sd-p8",
    ),
    dict(
        id="p9",
        order=9,
        slug="p9_resumable_workflow",
        title="可续跑的代码化 workflow",
        essence="持久化状态机",
        triggers=["长流程失败后要从中间继续", "节点之间只传产物", "每个节点完成就保存", "重启后跳过已完成节点", "失败节点可重试"],
        statement="""题目：实现一个代码化工作流执行器。输入是一组节点，每个节点有名字、依赖列表、执行函数和重试次数。节点函数只能读取直接上游节点的产物，不能共享全局可变上下文。执行器要按依赖顺序运行节点；每个节点一旦成功，就立刻把产物保存到持久化 store 中。某个节点失败时，按配置重试，仍失败则抛出带节点名和已完成节点列表的错误。进程重启或再次调用同一个 run_id 时，已经保存成功的节点必须跳过，只从第一个未完成节点继续。""",
        states=[dict(name="checkpoint", desc="已完成节点到产物的持久化映射，是续跑的事实来源"), dict(name="cursor / pending nodes", desc="根据拓扑顺序和 checkpoint 推出的待执行节点位置")],
        extra_states=[dict(name="topological order", desc="合法执行顺序，保证依赖先于下游"), dict(name="attempt", desc="当前节点已经尝试的次数")],
        invariants=["checkpoint 中出现的节点表示该节点已经成功，续跑时不能重跑", "节点只能看到直接依赖的产物副本", "节点成功后必须立刻写 checkpoint，再进入下一个节点", "执行前必须先发现重名、未知依赖和环", "失败重试不能污染 checkpoint 中的上游产物"],
        transitions="""```text
加载 store[run_id] -> 得到 checkpoint
校验 DAG -> 生成拓扑顺序
遇到已在 checkpoint 的节点 -> skip，cursor 前进
遇到未完成节点 -> 构造依赖产物副本 -> run
run 成功 -> 写 checkpoint[node] -> cursor 前进
run 失败且还有 retries -> 重新构造输入再试
run 失败且重试耗尽 -> 抛 WorkflowError，保留 checkpoint
```""",
        failures=[dict(case="重复：同一个 run_id 再执行", handle="以 checkpoint 为准跳过已完成节点，不重复产生副作用"), dict(case="失败：节点执行异常", handle="只重试当前节点；耗尽后抛结构化错误，已成功节点保留"), dict(case="并发：两个进程跑同一 run_id", handle="真实工程要给 run_id 加租约或乐观锁，避免同一节点被双写"), dict(case="超时：节点长时间不返回", handle="工程版应给节点设置超时，把超时当失败并按重试策略处理"), dict(case="重启：进程在节点成功后崩溃", handle="只要 checkpoint 已写入，重启后该节点跳过；如果未写入，则允许重跑，节点自身要幂等")],
        walkthrough="""例子：节点是 spec -> cases、data -> execute -> report。第一次运行时 checkpoint 为空。spec 成功，保存 `{spec: S}`；cases 成功，保存 `{spec:S,cases:C}`；data 成功，保存 `{spec:S,cases:C,data:D}`。execute 失败，抛错，store 里仍有前三个节点。修复后用同一个 run_id 再跑，执行器看到 spec、cases、data 已在 checkpoint，直接跳过，只构造 `{cases:C,data:D}` 给 execute。execute 成功后保存 E，再执行 report，最终返回所有节点产物。""",
        oral=dict(
            structure="这题的核心不是怎么调用函数，而是怎么把流程变成可恢复的状态机。两个状态分别是 checkpoint 和 cursor。checkpoint 记录哪些节点已经成功以及它们的产物；cursor 可以由拓扑顺序和 checkpoint 推出来，表示下一批待执行节点。最重要的不变量是：节点一成功就落 checkpoint，续跑时 checkpoint 里的节点绝不重跑。这样失败和重启都不会把已经完成的工作推倒重来。",
            flow="正常流程先做静态校验：节点名不能重复，依赖必须存在，图里不能有环。然后生成拓扑顺序。执行时先读取 `store[run_id]` 作为 checkpoint；遍历拓扑顺序，如果当前节点已经在 checkpoint，就把产物加载到 outputs 并跳过。如果没完成，就只取直接依赖节点的产物，做深拷贝后传给节点函数。节点成功后，立即把产物深拷贝写入 checkpoint，然后继续。节点失败时只重试这个节点，每次重试重新构造输入副本；重试耗尽后抛错误，store 保留所有已成功节点。",
            pitfalls="易错点有五个。第一，把所有节点都跑完后才统一写 checkpoint，结果中间失败时前面成功的节点也无法续用。第二，把整个上下文传给节点，下游能看到不该看的产物，节点边界失效。第三，不做深拷贝，某个节点修改输入时污染上游 checkpoint。第四，续跑时只看内存 outputs，不读 store，进程重启后无法恢复。第五，执行一半才发现环或未知依赖，导致已经产生副作用后才报配置错误，所以图校验必须在执行前完成。",
        ),
        followups=[dict(q="并发跑同一个 run_id 怎么办？", a="需要持久化层支持锁或租约。一个执行器拿到 run_id 的执行权后才能推进 cursor。写 checkpoint 时最好带版本号，避免两个进程同时写同一节点。"), dict(q="重启怎么恢复 cursor？", a="不需要单独持久化 cursor。读取 checkpoint 后，沿拓扑顺序找到第一个未完成且依赖已完成的节点，就能恢复待执行位置。"), dict(q="规模扩大到很多节点怎么办？", a="拓扑排序后可以把同一层无依赖冲突的节点并行执行。checkpoint 仍按节点粒度写。返回结果可以只返回产物引用，避免大对象都进内存。"), dict(q="节点有外部副作用怎么办？", a="节点要设计幂等键，或者在 checkpoint 中保存外部资源标识。重试时先检查资源是否已创建，不能盲目再创建一份。")],
        pitfalls=["全部结束才保存，失败后无法续跑", "节点拿到全局上下文，依赖边界被破坏", "输入不拷贝，重试污染 checkpoint", "跳过已完成节点时没有恢复 outputs", "未先校验 DAG，执行后才发现配置错误"],
        complexity="拓扑校验 O(V+E)；执行开销为各节点函数之和；checkpoint 空间 O(已完成节点产物大小)。",
        variants=[dict(context="报表流水线包含拉数、清洗、聚合、生成文件，失败后从最近成功步骤继续。", note="每步产物就是 checkpoint，待执行步骤就是 cursor。"), dict(context="测试平台先生成用例、准备数据、执行、汇总，执行失败后不重做准备数据。", note="已完成节点跳过，失败节点单独重试。"), dict(context="订单补偿任务分多步调用外部系统，重启后不能重复调用已成功步骤。", note="持久化成功产物和外部资源 ID，续跑时按 checkpoint 恢复。")],
        lab="lab-sd-p9",
    ),
    dict(
        id="p10",
        order=10,
        slug="p10_session_manager",
        title="Session 管理器",
        essence="队列 + 并发上限",
        triggers=["同一会话内请求必须串行", "不同会话可以并行", "单会话要背压", "会话历史要持久化恢复", "空闲会话要回收"],
        statement="""题目：实现一个会话管理器。外部不断提交 `(session_id, turn_input)`。同一个 session 的多轮请求必须按提交顺序处理，后一轮不能越过前一轮；不同 session 之间可以同时处理，但系统有全局并发上限。每个 session 的排队中加运行中请求数不能超过阈值，超过要立即拒绝，不能无限堆积。每轮成功后，要把输入和输出追加到该 session 的历史，并写入持久化 store；失败的轮次不能写历史，但要释放 session，让后续请求可以继续。长时间没有在途请求的 session 可以从内存回收，再次提交时从 store 恢复历史。""",
        states=[dict(name="per-session queue", desc="每个会话自己的待处理队列和当前运行任务，保证会话内串行"), dict(name="active sessions", desc="当前在内存中有队列、运行任务或历史快照的会话集合，并受全局并发上限约束")],
        extra_states=[dict(name="history store", desc="持久化历史，用于回收后恢复"), dict(name="last_active_at", desc="空闲回收的时间依据"), dict(name="max_pending", desc="单会话背压阈值")],
        invariants=["同一 session 同时最多一个 running turn", "全局 running turn 数不能超过 max_active", "成功才追加历史，失败不能污染历史", "排队中加运行中的数量不能超过 max_pending", "回收只能发生在该 session 没有排队和运行任务时"],
        transitions="""```text
submit(sid, turn) -> 创建/恢复 session，检查 max_pending，入队
start_ready       -> 找到未运行且有队列的 session，受 max_active 限制启动
complete(ticket)  -> 追加历史，写 store，清 active，更新时间
fail(ticket)      -> 不写历史，清 active，更新时间
evict_idle        -> 空闲且无在途任务的 session 从内存删除
submit after evict-> 从 store 读历史，再继续入队
```""",
        failures=[dict(case="重复：同一 session 连续提交多轮", handle="全部进入该 session 队列，只允许队首运行，保证顺序"), dict(case="失败：handler 抛错", handle="把异常返回给调用方或记录失败；不追加历史，释放 active 后允许下一轮继续"), dict(case="并发：多个 session 同时有请求", handle="不同 session 可并行启动，但 running 总数受全局上限控制"), dict(case="超时：某轮长时间运行", handle="工程版应支持取消或超时失败，释放 session，否则后续轮次会永久阻塞"), dict(case="背压：单 session 堆积过多", handle="超过 max_pending 立即拒绝，让上游重试或降级")],
        walkthrough="""例子：`max_active=2`。提交 A1，A 队列 `[A1]`；提交 A2，A 队列 `[A1,A2]`；提交 B1，B 队列 `[B1]`。start_ready 时，A 没有运行任务，启动 A1；B 也没有运行任务，启动 B1；A2 不能启动，因为 A 已经有 A1 在运行。A1 complete 后，把 `(A1,out1)` 写入 A 的历史，A active 清空。下一次 start_ready 才能启动 A2，并把历史副本交给执行逻辑。""",
        oral=dict(
            structure="这题我会先讲两个状态：每个 session 一条自己的队列，外加 active sessions 这个全局视图。队列解决同一会话内串行，active sessions 解决不同会话之间的并发和全局上限。关键不变量是：一个 session 同时只能有一个 running turn；成功才写历史；空闲回收不能回收还有排队或运行任务的 session。只要这三个不变量守住，会话顺序和恢复语义就清楚了。",
            flow="提交流程是：先根据 sid 找到内存 session；如果没有，就从持久化 store 读取历史并创建 session。然后计算这个 session 的 pending 数，也就是队列长度加上是否有 running；如果超过阈值就拒绝，否则生成 ticket 入队。调度时遍历 session，只有 active 为空且队列非空的 session 才能启动一个任务，同时全局 running 数不能超过 max_active。任务成功时追加历史并写回 store；任务失败时不写历史，只清掉 active。回收时只删除没有队列、没有 running、且空闲时间足够长的内存 session。",
            pitfalls="最容易错的是把同一 session 的多个请求直接并发跑，模型或业务历史会乱序。第二个错误是失败也写入历史，后续轮次会基于错误输出继续。第三个错误是只限制全局并发，不限制单 session pending，某个热用户能把内存打满。第四个错误是回收 busy session，导致运行中的 ticket 找不到状态。第五个错误是回收后只创建空历史，不从 store 恢复，导致会话上下文丢失。",
        ),
        followups=[dict(q="并发实现怎么加锁？", a="session 表、队列、active 标记和全局 running 计数要在同一把锁或同一事件循环内修改。执行 handler 本身不要持锁，否则会阻塞其他 session。"), dict(q="重启后怎么恢复？", a="持久化 store 至少保存成功历史。重启后内存 active 全部丢失，未完成任务要由外部请求重试或任务表重新投递。恢复时从 store 加载历史。"), dict(q="规模扩大怎么办？", a="按 session_id 做一致性哈希，把同一 session 路由到同一分片。分片内保证串行，分片间自然并行。热点 session 只能排队或做业务级拆分。"), dict(q="超时中的请求怎么办？", a="给 running ticket 设置 deadline。超时后标记失败并释放 session，但真实执行线程或远端任务也要取消或隔离，防止稍后又写回旧结果。")],
        pitfalls=["同一 session 并发执行导致历史乱序", "失败轮次写入历史污染上下文", "只做全局限流，没有单 session 背压", "回收有在途任务的 session", "恢复时没有从持久化 store 读取历史"],
        complexity="submit 通常 O(1)；start_ready 与 session 数相关，可优化为就绪队列；空间 O(活跃 session 数 + 排队请求数 + 历史大小)。",
        variants=[dict(context="客服机器人同一用户的消息要按顺序回复，不同用户可以同时处理。", note="用户就是 session，消息队列保证会话内顺序。"), dict(context="在线编辑器同一文档的操作要串行应用，不同文档可并行保存。", note="文档 ID 是 session，全局并发上限保护服务。"), dict(context="支付确认同一订单的多次状态查询要排队，不同订单可并发。", note="订单 ID 作为 session，历史和 active 状态决定能否启动下一轮。")],
        lab="lab-sd-p10",
    ),
    dict(
        id="p11",
        order=11,
        slug="p11_tool_registry",
        title="工具注册与调用层",
        essence="注册表 + 调度规则",
        triggers=["工具名要稳定可发现", "调用前要校验参数", "报错要能指导模型修正", "返回太长要截断提示", "读工具可并行写工具要串行"],
        statement="""题目：实现一个工具注册与调用层。每个工具注册时提供名字、描述、参数 schema、函数、是否只读、最大返回长度。工具名必须规范，避免模型混淆；描述不能过短，因为它是调用者理解工具的说明书。调用工具时，要校验未知工具、未知参数、缺少必填参数、类型错误，并返回可操作的错误文本，而不是抛出内部异常。工具函数自身抛错时，也要变成结构化失败结果。返回内容过长时要截断，并提示调用方缩小范围或分页。批量调用时，连续只读工具可以并行，写工具以及未知工具必须作为屏障串行。""",
        states=[dict(name="registry", desc="工具名到 schema、描述、读写属性、函数和截断上限的映射"), dict(name="write lock / execution queue", desc="控制读写调用顺序的调度状态，保证写操作不与相邻读写乱序")],
        extra_states=[dict(name="validation error", desc="参数校验失败时返回给调用者的可修正说明"), dict(name="result limit", desc="单工具最大返回长度，防止撑爆上下文")],
        invariants=["未知工具、参数错误和工具异常都不能穿透调用层", "参数校验必须在执行工具函数之前完成", "写工具是屏障：之前的读先完成，之后的读必须看到写后的状态", "批量结果顺序必须和输入调用顺序一致", "超长结果要截断并告诉调用方如何继续获取"],
        transitions="""```text
register(spec) -> 校验名字/描述/重名 -> 写入 registry
call(name,args)-> 查 registry -> 校验 args -> 执行 fn -> 截断结果 -> 返回 {ok, content}
未知工具       -> 返回候选工具名，不执行
plan_batch     -> 连续 read_only 合成一批，write/unknown 单独一批
call_batch     -> 按批次执行，结果放回原下标
```""",
        failures=[dict(case="重复：注册同名工具", handle="register 直接拒绝，避免后注册覆盖前注册造成调用语义变化"), dict(case="失败：参数缺失或类型错误", handle="返回参数名、期望类型和 example，让调用者能修正后重试"), dict(case="并发：读写混在批量调用里", handle="连续读可以并行；遇到写调用必须先等待前面的读结束，再单独执行写"), dict(case="超时：工具函数卡住", handle="工程版给每个工具配置超时和取消；超时转成可读错误，不阻塞整个调度器"), dict(case="结果过长：工具返回大文本", handle="按 max_chars 截断，并提示 truncated、paginate 或 narrow query")],
        walkthrough="""例子：注册 `order_search`，参数是 keyword 必填字符串、limit 可选整数，只读；再注册 `order_create`，参数 name 必填字符串，写工具。调用 `order_serch` 时 registry 找不到名字，返回“是否想调用 order_search”。调用 `order_search({})` 时不执行函数，直接返回缺少 keyword 和 example。批量 `[search a, search b, create c, search d]` 会规划成三批：前两个 search 同批读，create 单独写，最后 search 在写之后执行，因此它能看到 create 后的状态。""",
        oral=dict(
            structure="这题的两个核心状态是 registry 和执行队列。registry 负责把工具名映射到 schema、读写属性和函数；执行队列负责保证读写顺序，尤其是写工具不能和前后的调用乱序。最重要的不变量是：调用层不能把未知工具、参数错误和工具异常直接抛出去，而要返回模型能理解、能修正的内容。这样工具层才是稳定边界，而不是把内部错误暴露给上层。",
            flow="流程先从注册开始：校验工具名格式、描述长度和是否重名，通过后写入 registry。单次调用时，先按名字查 registry；不存在就返回最接近的候选。存在则校验 args 是否是对象，有没有未知参数，必填参数是否齐全，类型是否匹配，特别注意 bool 不能当 int。校验通过才执行函数。函数抛异常时捕获异常类型和消息，不带堆栈。函数返回后转成字符串，超过上限就截断并给分页提示。批量调用先规划批次，连续只读合并，写调用和未知工具单独成批，最后按原顺序填回结果。",
            pitfalls="常见坑有五个。第一，注册时不规范化名字，模型看到相似名字会乱猜。第二，参数错了直接抛异常，上层只看到失败，无法知道该补哪个字段。第三，把工具 traceback 原样返回，既长又暴露内部细节。第四，超长结果不截断，直接占满上下文。第五，批量调用里让写操作和读操作并行，导致写之前的读看到了写之后的状态，或者写之后的读仍看旧状态。读写屏障是这题最容易漏掉的不变量。",
        ),
        followups=[dict(q="并发执行怎么保证写串行？", a="给写路径使用互斥锁，或者把批量调用先切成读批和写屏障。读批内部可以并行；写批必须独占执行；写之后再放行后续读。"), dict(q="工具注册表重启后怎么办？", a="工具定义通常来自代码或配置，进程启动时重新注册。动态工具要持久化 name、schema、版本和权限，并在恢复时重新绑定可执行函数。"), dict(q="工具很多时怎么扩展？", a="按命名空间分组，提供搜索和分页的 tools/list。模型只拿当前任务相关的一小组工具，避免一次暴露几百个名字。"), dict(q="如何处理权限？", a="权限应该是调用前校验的一部分。schema 校验通过不代表有权执行。拒绝时返回可操作原因，例如需要哪个 scope，而不是执行后才让底层报错。")],
        pitfalls=["工具名不规范导致候选混乱", "参数校验后置，错误变成函数内部异常", "返回 traceback 泄露内部细节", "超长结果没有截断提示", "写工具没有作为批量调用屏障"],
        complexity="注册 O(1)；单次调用参数校验 O(参数数)；批次规划 O(调用数)；空间 O(工具数)。",
        variants=[dict(context="订单系统给模型开放查询、创建、取消订单三个操作。", note="查询是读工具，创建和取消是写工具，本质仍是注册表和读写调度。"), dict(context="日志平台提供搜索日志、导出任务、删除任务等工具。", note="搜索可并行，导出或删除要受写屏障和参数校验保护。"), dict(context="内部运维机器人根据工具说明调用主机查询和重启操作。", note="工具名、schema、权限和可操作报错是安全边界。")],
        lab="lab-sd-p11",
    ),
    dict(
        id="p12",
        order=12,
        slug="p12_nested_sub_agents",
        title="嵌套子 agent",
        essence="树形调用 + 账本",
        triggers=["一个任务派生多个子任务", "子任务还会继续派生", "需要深度上限", "预算要逐级扣减", "取消不能留下孤儿"],
        statement="""题目：实现一个嵌套子 agent 运行时。父任务可以创建子任务，子任务还可以继续创建孙任务，因此所有调用形成一棵树。系统需要限制最大深度，防止无限递归；每个节点都有预算，子节点花费预算时，要同时扣减自己和所有祖先的账本，不能让一棵子树超过父任务总预算。子任务成功后只把摘要和产物引用回传给父任务，不能把完整过程塞回父上下文。某个子任务失败时，要变成结构化失败结果，不能拖垮兄弟任务。父任务取消时，所有后代都要取消并清理运行状态，不能留下孤儿任务。""",
        states=[dict(name="call tree", desc="父子关系、path、depth 和运行状态组成的任务树"), dict(name="budget ledger", desc="每个节点的预算上限、已用量以及指向父预算的账本链")],
        extra_states=[dict(name="running set", desc="当前还在执行的节点 path，用于取消和泄漏检查"), dict(name="summary limit", desc="子任务回传摘要的最大长度")],
        invariants=["任何节点 depth 不能超过 max_depth", "子节点 spend 必须同时记到自己和所有祖先", "父节点只能拿到子节点摘要，不拿完整过程", "子节点普通失败要隔离成 ChildResult", "取消父节点必须清理整棵子树的 running 状态"],
        transitions="""```text
spawn(parent,name) -> 计算 path/depth -> 检查深度 -> 创建子预算 -> 加入 call tree/running
子任务 spend(n)    -> 检查 min(自己剩余, 祖先剩余) -> 逐级 used += n
子任务成功         -> 截断摘要，返回 ok result，移除 running
子任务异常         -> 返回 failed result，保留错误类型，移除 running
cancel_subtree     -> 找到 path 前缀下所有节点，标记取消并清 running
```""",
        failures=[dict(case="重复：子任务名称在同一父下重复", handle="工程版应拒绝或追加唯一后缀，保证 path 能唯一归因"), dict(case="失败：子任务抛普通异常", handle="捕获后转成失败结果，兄弟任务继续执行，父任务决定是否重试"), dict(case="并发：多个子任务同时花父预算", handle="预算账本要用锁或原子事务保护，否则会同时判断余额足够而超支"), dict(case="超时：子任务超过 deadline", handle="取消该子树，等待清理完成，返回包含 cancel 的失败结果"), dict(case="取消：父任务被取消", handle="向所有后代传播取消，清理 running，不能留下后台任务继续写结果")],
        walkthrough="""例子：根任务 root 预算 100。root 派生 mid，mid 自己先花 10；mid 再派生 leaf1 和 leaf2，每个花 30。leaf1 spend 30 时，leaf1.used、mid.used、root.used 都增加 30；leaf2 同理。mid 的总 tokens 是 70，root 的 used 也是 70。每个 leaf 返回很长文本，但父任务只收到截断摘要。若 mid 再派生一个 depth 超限的节点，运行时不抛出全局异常，而是返回一个 `ok=False`、error 包含 depth 的结果。""",
        oral=dict(
            structure="这题的两个核心状态是 call tree 和 budget ledger。call tree 记录每个子任务的父节点、路径、深度和运行状态，用来做深度限制、摘要归因和取消清理。budget ledger 是一条从子节点连到根节点的账本链，任何花费都要逐级扣减。最重要的不变量是：子树不能突破祖先预算，取消父节点不能留下还在运行的后代。",
            flow="正常 spawn 时，先根据 parent 计算 path 和 depth。根节点 depth 是 0，子节点是父 depth 加 1。超过 max_depth 时，不执行函数，直接返回失败结果。没超深度就创建子预算，父预算作为它的 parent，然后把 path 放进 call tree 和 running。执行函数期间，ctx.budget.spend 会先计算自己和祖先剩余额度的最小值，足够才从当前预算一路加 used 到根预算。函数成功后，把返回值转成字符串并截断成摘要；函数抛普通异常时，转成失败结果。无论成功失败，finally 都要从 running 里移除。",
            pitfalls="常见错误有五个。第一，只检查子预算，不检查父预算，结果多个子任务合计超过父任务预算。第二，只扣子预算，不逐级扣祖先，父任务以为自己还没花钱。第三，深度超限时直接抛异常，导致整棵树失败；更好的做法是返回结构化失败，让父任务处理。第四，把子任务完整日志塞回父上下文，导致上下文爆炸。第五，取消父任务时只取消直接子任务，孙任务还在运行，最后变成孤儿写回旧结果。",
        ),
        followups=[dict(q="并发 spend 怎么办？", a="预算链上的检查和扣减必须是原子操作。可以从根到账本链加锁，也可以把预算扣减放到单线程调度器中。否则两个子任务会同时看到余额足够而一起超支。"), dict(q="重启后 call tree 怎么恢复？", a="如果需要恢复运行中任务，要持久化 path、parent、depth、状态和预算已用量。重启后通常把 running 标成 unknown 或 cancelled，再由上层重新派发未完成任务。"), dict(q="规模扩大怎么办？", a="call tree 只在父任务保留摘要和产物引用，完整日志放外部存储。运行时可以按子树分片，但预算扣减和取消命令必须能跨分片传递。"), dict(q="失败隔离的边界是什么？", a="普通业务异常变成 ChildResult，不影响兄弟。取消和系统级中断通常要向上传播，因为它表示父任务已经不需要这棵子树继续运行。")],
        pitfalls=["只扣子预算，不扣祖先预算", "深度超限抛穿整棵树", "父任务接收完整子过程导致上下文膨胀", "失败子任务拖垮兄弟任务", "取消父节点后 running 里残留后代"],
        complexity="spawn 本身 O(深度) 用于预算链扣减；cancel_subtree 朴素实现 O(节点数)；空间 O(调用树节点数)。",
        variants=[dict(context="测试编排器把大套件拆成多个子套件，子套件还会拆成用例批次。", note="套件树就是 call tree，执行时长或用例数就是预算账本。"), dict(context="自动化助手把需求分析、代码修改、验证分别交给子任务。", note="每个子任务只回摘要，预算和取消沿树传播。"), dict(context="数据处理任务按日期分片，日期任务再按租户分片。", note="分片层级需要深度限制，资源消耗要记到父任务。")],
        lab="lab-sd-p12",
    ),
]
