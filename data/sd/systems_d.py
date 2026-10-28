SYSTEMS = [
    dict(
        id="x6",
        order=6,
        title="分布式定时任务平台（秒级）",
        brief="设计一个百万级定时任务平台，按 cron、固定间隔和一次性延时到点回调业务方，并尽量做到不漏不重。",
        statement="""你要设计一个分布式定时任务平台。业务方可以注册 cron、固定间隔和一次性延时任务，平台在每个触发点到达时回调业务方的 HTTP 或 RPC 接口。系统要支持启停任务、修改任务、查询执行记录、失败重试、超时控制和分片广播：一个任务可以拆成 N 个 shard，分别交给多个业务实例处理。核心语义是每个触发点恰好触发一次：平台侧不能漏掉，也不能由两个触发节点同时发起同一个 fire_time；业务方需要用平台传入的幂等键抵御网络重试导致的重复到达。非功能要求是秒级触发精度、百万级任务、峰值集中触发、99.9% 可用、多租户隔离和可观测。你需要给出服务划分、数据表、接口、状态机、核心流程和可靠性方案，特别说明节点宕机、租约过期、时钟漂移、消息重复、业务方超时和高峰第 0 秒同时触发时怎么处理。""",
        focus="""题眼不是“会解析 cron”，而是百万任务下到点触发的精度与不重不漏之间的矛盾。内存时间轮能降低扫描延迟，但权威状态必须落在带唯一键和 fencing 的存储里；lease 负责把任务分片分给触发节点，trigger_record 的唯一键负责把每个 job_id、fire_time 收敛成一次。""",
        scale="""规模假设：100 万个启用任务，20 万个任务在每分钟第 0 秒触发；平均每分钟 35 万次触发，平时约 5800 trigger/s，整点峰值 20 万 trigger/s。每次触发平均 2 个执行 shard，执行日志保留 30 天，约 300 亿条 execution_log。触发精度目标 P99 小于 1 秒，P99.9 小于 3 秒；调度节点 64 台，每台预加载 15 秒窗口，单节点峰值约 3000 到 5000 trigger/s。""",
        example="""10:00:00 时有 100 万个任务处于启用状态，其中 20 万个都在第 0 秒触发。触发节点 A 通过 lease 持有 3 万个任务的 owner 分片，并已在 09:59:45 预加载到本地时间轮。10:00:00 刚开始，A 发出了 2000 个 trigger_record 后宕机。作答者要说明剩余 2.8 万个任务如何被其他节点接管，已经发出的 2000 个如何避免重发，以及业务方超时时怎么重试。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清语义与边界",
                minutes=3,
                prompt="先问清任务类型、触发语义、业务幂等能力、秒级精度口径、分片广播和多租户隔离，不要直接讲分布式锁。",
                points=[
                    "确认 cron、固定间隔、一次性延时的 next_fire_time 计算口径",
                    "确认恰好一次是平台触发记录唯一，还是业务副作用也保证一次",
                    "确认业务回调是否支持幂等键和超时查询",
                    "确认分片广播的 shard 数、实例选择和失败语义",
                    "确认秒级精度的统计口径与允许的时钟漂移",
                    "确认租户级限流、暂停、补偿和日志保留时间",
                ],
                reference="""我会先把语义边界问清楚。业务说“恰好触发一次”时，平台能保证的是同一个 job_id、fire_time、shard_no 只产生一个权威 trigger_record，并且只有拿到有效 fencing_token 的触发节点能把它推进；但 HTTP/RPC 在超时后无法知道业务方是否已经执行，所以回调必须带 event_id 和 idempotency_key，业务方按这个键去重。时间语义也要明确：cron 用租户时区计算 next_fire_time，固定间隔从上次计划触发时间推进而不是从实际完成时间推进，一次性延时只触发一次。秒级精度要定义成 fire_time 到平台首次发起回调的差值，而不是业务处理完成时间。分片广播要问清一个任务 N 片是每片都必须成功，还是允许部分失败；这里按每个 shard 单独有 execution_log，任务级查询再聚合。最后确认多租户配额、暂停任务后是否取消已在途触发、日志保留 30 天还是更久，因为这些会影响分表、索引和补偿扫描范围。""",
            ),
            dict(
                key="estimate",
                title="规模估算",
                minutes=4,
                prompt="用题目数字算触发峰值、时间轮槽位、存储量、分片数和机器数，并说明这些数字改变了哪些设计决定。",
                points=[
                    "从 20 万个第 0 秒任务算峰值 trigger/s",
                    "估算执行日志保留 30 天的数据量",
                    "估算 owner 分片数量和单节点持有任务数",
                    "估算预加载窗口与时间轮槽位大小",
                    "说明为什么不能每秒全表扫描",
                    "说明数据库写入和回调并发如何削峰",
                ],
                reference="""按 100 万启用任务估算，平时平均 35 万次每分钟触发是 5800 trigger/s，但真正决定架构的是 20 万个任务都在每分钟第 0 秒触发。如果每个任务平均 2 个 shard，峰值就是 40 万条 execution_log 和 20 万条 trigger_record 在几秒内生成，不能靠一个数据库实例和每秒全表扫描硬扛。设计上我会把任务 owner 切成 4096 个逻辑分片，64 台触发节点平均每台 64 个 owner 分片、约 1.5 万任务；热点第 0 秒如果某台持有 3 万任务，单机需要在 1 到 3 秒内完成批量 insert ignore trigger_record 和投递。时间轮按 100 毫秒或 1 秒槽位都可以，面试中我会选 1 秒槽位加 15 秒预加载窗口：每个节点只扫描自己 owner 分片内 next_fire_time 落入窗口的任务，把精确到秒的触发放入本地 wheel。存储上，30 天、平均每分钟 35 万 trigger、每 trigger 2 shard，execution_log 大约 302 亿条太大，所以实际要按天分库分表、日志冷热分层；在线查询只保留近 7 天热表，更久走对象存储或离线索引。这个估算直接决定了：权威去重表必须支持水平拆分，执行日志必须异步写和按时间分片，回调并发必须按租户和下游限流。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出控制面、时间计算、owner/lease、触发节点、执行派发、记录查询和监控告警，说明哪些有状态、如何扩展。",
                diagram="""flowchart LR
  A["业务方"] --> B["控制面API"]
  B --> C["任务库"]
  B --> D["时间计算器"]
  D --> C
  E["Owner协调器"] --> F["Owner表"]
  G["触发节点"] --> F
  G --> C
  G --> H["时间轮"]
  H --> I["触发记录库"]
  I --> J["执行派发器"]
  J --> K["回调网关"]
  K --> A
  J --> L["执行日志库"]
  M["巡检补偿器"] --> I
  M --> C""",
                points=[
                    "控制面只负责注册、修改、启停和查询",
                    "时间计算器统一计算 next_fire_time，避免各节点口径不同",
                    "Owner 协调器用 lease 和 fencing 分配任务分片",
                    "触发节点本地有时间轮但不做权威判定",
                    "执行派发器负责 shard 拆分、重试、超时和限流",
                    "巡检补偿器扫描漏触发和卡住的记录",
                    "查询服务从热表与冷存储聚合执行记录",
                ],
                reference="""我会把系统拆成控制面和触发面。控制面 API 是无状态服务，负责 job 的创建、修改、启停、查询和权限校验；它把任务定义写入任务库，并调用时间计算器生成 next_fire_time。时间计算器可以做成库或独立服务，关键是 cron、固定间隔和租户时区的计算口径只有一份，否则不同触发节点会算出不同时间。Owner 协调器负责把 job_owner 的逻辑分片租给触发节点，写入 lease_until 和 fencing_token；它本身可以多实例运行，但每次续租通过数据库 CAS 或一致性 KV 完成。触发节点是有状态 worker，状态是本地预加载窗口和时间轮，扩展方式是增加节点后重新分配 owner 分片；它不能只凭内存认定成功，必须批量写 trigger_record 的唯一键。执行派发器读取已创建的 trigger_record，按 job_shard 生成 execution_log，走回调网关发 HTTP/RPC，并做租户级、任务级、下游域名级限流。回调网关无状态扩展，负责协议适配、超时、签名和幂等键透传。巡检补偿器按 fire_time 窗口扫描应该触发但缺 trigger_record 的任务，以及长时间 RUNNING 的执行记录，触发补偿或标记超时。查询服务从热执行表、冷对象存储和 trigger_record 聚合结果。组件通信上，控制面同步写库，触发面使用数据库批量写和内部队列异步派发；消息队列只做削峰，不作为恰好一次的权威。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="给出 job、job_shard 或 job_owner、trigger_record、execution_log 等核心表，说明唯一键、索引、lease 和 fencing 的用途。",
                ddl="""
CREATE TABLE `job` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `name` VARCHAR(128) NOT NULL COMMENT '任务名',
  `schedule_type` ENUM('CRON','INTERVAL','ONCE') NOT NULL COMMENT '调度类型',
  `schedule_expr` VARCHAR(256) NOT NULL COMMENT 'cron表达式或间隔秒',
  `timezone` VARCHAR(64) NOT NULL COMMENT '时区',
  `callback_type` ENUM('HTTP','RPC') NOT NULL COMMENT '回调类型',
  `callback_target` VARCHAR(512) NOT NULL COMMENT '回调地址',
  `shard_count` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '分片数',
  `status` ENUM('ENABLED','PAUSED','DELETED') NOT NULL COMMENT '任务状态',
  `next_fire_time` DATETIME(3) NOT NULL COMMENT '下次计划触发时间',
  `version` BIGINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '配置版本',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`,`name`),
  KEY `idx_status_next` (`status`,`next_fire_time`),
  KEY `idx_tenant_status` (`tenant_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务定义表';

CREATE TABLE `job_shard` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务分片ID',
  `job_id` BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  `shard_no` INT UNSIGNED NOT NULL COMMENT '分片编号',
  `route_key` VARCHAR(128) NOT NULL COMMENT '业务路由键',
  `status` ENUM('ENABLED','PAUSED') NOT NULL COMMENT '分片状态',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_job_shard` (`job_id`,`shard_no`),
  KEY `idx_job_status` (`job_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务广播分片表';

CREATE TABLE `job_owner` (
  `owner_shard` INT UNSIGNED NOT NULL COMMENT '逻辑归属分片',
  `worker_id` VARCHAR(128) NOT NULL COMMENT '触发节点ID',
  `lease_until` DATETIME(3) NOT NULL COMMENT '租约到期时间',
  `fencing_token` BIGINT UNSIGNED NOT NULL COMMENT '防脑裂令牌',
  `version` BIGINT UNSIGNED NOT NULL COMMENT 'CAS版本',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`owner_shard`),
  KEY `idx_worker_lease` (`worker_id`,`lease_until`),
  KEY `idx_lease_until` (`lease_until`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务归属租约表';

CREATE TABLE `trigger_record` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '触发记录ID',
  `job_id` BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `fire_time` DATETIME(3) NOT NULL COMMENT '计划触发时间',
  `job_version` BIGINT UNSIGNED NOT NULL COMMENT '触发时任务版本',
  `owner_shard` INT UNSIGNED NOT NULL COMMENT '归属分片',
  `fencing_token` BIGINT UNSIGNED NOT NULL COMMENT '创建者令牌',
  `status` ENUM('INIT','DISPATCHING','DONE','PARTIAL_FAILED','CANCELED') NOT NULL COMMENT '触发状态',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_job_fire` (`job_id`,`fire_time`),
  KEY `idx_fire_status` (`fire_time`,`status`),
  KEY `idx_tenant_fire` (`tenant_id`,`fire_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='触发去重记录表';

CREATE TABLE `execution_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '执行记录ID',
  `trigger_id` BIGINT UNSIGNED NOT NULL COMMENT '触发记录ID',
  `job_id` BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  `shard_no` INT UNSIGNED NOT NULL COMMENT '分片编号',
  `attempt` INT UNSIGNED NOT NULL COMMENT '尝试次数',
  `idempotency_key` VARCHAR(128) NOT NULL COMMENT '业务幂等键',
  `status` ENUM('READY','RUNNING','SUCCEEDED','FAILED','TIMEOUT','CANCELED') NOT NULL COMMENT '执行状态',
  `callback_target` VARCHAR(512) NOT NULL COMMENT '实际回调目标',
  `request_id` VARCHAR(128) NOT NULL COMMENT '请求ID',
  `error_code` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '错误码',
  `started_at` DATETIME(3) NULL COMMENT '开始时间',
  `finished_at` DATETIME(3) NULL COMMENT '结束时间',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trigger_shard_attempt` (`trigger_id`,`shard_no`,`attempt`),
  UNIQUE KEY `uk_idempotency` (`idempotency_key`),
  KEY `idx_job_created` (`job_id`,`created_at`),
  KEY `idx_status_created` (`status`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回调执行日志表';
""",
                points=[
                    "job 存任务定义、状态、版本和 next_fire_time",
                    "job_shard 存广播分片，不把实例动态心跳塞进 job",
                    "job_owner 存 owner_shard、lease_until、fencing_token 和 CAS version",
                    "trigger_record 用 (job_id, fire_time) 唯一键防重复触发",
                    "execution_log 用 trigger、shard、attempt 和幂等键记录每次回调",
                    "按 fire_time、tenant_id、status 建索引用于扫描与查询",
                    "长期日志按时间冷热分层，不让在线表无限增长",
                ],
                reference="""权威表要围绕“谁拥有任务”和“某个触发点是否已经创建”设计。job 表保存任务定义、调度表达式、callback、shard_count、status、next_fire_time 和 version；修改任务时 version 增加，触发记录带 job_version，避免老配置和新配置混在一起。job_shard 表描述广播分片的静态配置，route_key 可以让业务方把 shard 路由到自己的实例；业务实例心跳、临时负载不应该放在这里，否则任务配置表会被高频写污染。job_owner 表是触发节点归属，owner_shard 是逻辑分片，worker_id、lease_until、fencing_token 和 version 支持 CAS 续租；旧节点租约过期后即使还活着，也因为 fencing_token 过旧不能推进记录。trigger_record 是最关键的去重表，唯一键 uk_job_fire 把同一个 job_id 和 fire_time 收敛成一条记录；如果要 shard 级去重，也可以把 shard_no 下沉到 trigger_shard 表，但本设计用 trigger_record 表示一次计划触发，再由 execution_log 表示每个分片执行。execution_log 记录 trigger_id、shard_no、attempt、idempotency_key、状态和回调目标，唯一键 uk_trigger_shard_attempt 防止同一尝试重复写，uk_idempotency 让业务幂等键可追溯。idx_fire_status 用于补偿器扫描某个时间窗口内未完成触发，idx_status_created 用于找超时执行。不要把大响应体、完整错误堆栈和长期统计直接塞进在线表；大内容放对象存储，在线表只存摘要、错误码和引用。""",
            ),
            dict(
                key="api",
                title="接口与事件",
                minutes=5,
                prompt="列出业务注册、启停、查询接口，以及内部抢租、创建触发、派发执行和回调协议，明确幂等键。",
                points=[
                    "注册和修改任务要带租户、表达式、回调、分片数和幂等键",
                    "启停任务要基于 version 或 etag 防并发覆盖",
                    "查询接口区分 trigger_record 和 execution_log",
                    "内部 AcquireOwnerLease 使用 CAS 和 fencing",
                    "CreateTrigger 使用 job_id、fire_time 唯一键",
                    "回调请求带 event_id、fire_time、shard_no、attempt、idempotency_key",
                ],
                reference="""对外接口我会分控制和查询两类。POST /v1/jobs 创建任务，参数包含 tenant_id、name、schedule_type、schedule_expr、timezone、callback_type、callback_target、shard_count、timeout_ms、retry_policy 和 request_id；request_id 是控制面幂等键，避免业务方重复提交创建出两个任务。PATCH /v1/jobs/{job_id} 修改表达式或回调时必须带 version，服务端 CAS 更新并重新计算 next_fire_time。POST /v1/jobs/{job_id}:pause 和 :resume 也带 version，语义是阻止未来触发，不强行撤回已经 RUNNING 的 execution。GET /v1/jobs/{job_id}/triggers?from=&to= 查询计划触发，GET /v1/triggers/{trigger_id}/executions 查询每个 shard 的尝试记录。内部接口包括 AcquireOwnerLease(owner_shard, worker_id, old_version, now)：只有 lease_until 过期或当前 worker 续租时才能更新，返回新的 fencing_token；BatchLoadJobs(owner_shard, window_start, window_end) 只加载本 owner 分片内 ENABLED 且 next_fire_time 在窗口内的任务；CreateTrigger(job_id, fire_time, job_version, fencing_token) 使用 insert ignore 或 upsert，返回 created 或 existed。执行派发事件 TriggerCreated(trigger_id) 进入内部队列，Dispatcher 生成 ExecutionReady(trigger_id, shard_no)。回调业务方时，无论 HTTP 还是 RPC 都传 event_id=execution_log.id、job_id、fire_time、shard_no、attempt、idempotency_key、scheduled_at、deadline_at 和签名；业务方返回 2xx 表示成功，明确的 4xx 可以按不可重试失败处理，5xx、超时和连接失败按退避重试。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="画出触发记录和执行记录的状态流转，说明合法转换、失败重试和并发 CAS。",
                diagram="""stateDiagram-v2
  [*] --> SCHEDULED
  SCHEDULED --> TRIGGER_INIT: 到点写入
  TRIGGER_INIT --> DISPATCHING: 拆分片
  DISPATCHING --> RUNNING: 发起回调
  RUNNING --> SUCCEEDED: 成功
  RUNNING --> RETRY_WAIT: 超时或可重试失败
  RETRY_WAIT --> RUNNING: 到重试时间
  RUNNING --> FAILED: 重试耗尽
  DISPATCHING --> PARTIAL_FAILED: 部分分片失败
  SUCCEEDED --> [*]
  FAILED --> [*]
  PARTIAL_FAILED --> [*]
  SCHEDULED --> CANCELED: 暂停或删除
  CANCELED --> [*]""",
                points=[
                    "区分计划状态、触发状态和单 shard 执行状态",
                    "trigger_record 从 INIT 到 DISPATCHING 到 DONE 或 PARTIAL_FAILED",
                    "execution_log 从 READY 到 RUNNING 到 SUCCEEDED/FAILED/TIMEOUT",
                    "重试进入 RETRY_WAIT，新 attempt 递增但幂等键稳定或可推导",
                    "暂停任务只影响未来 SCHEDULED，不随意杀死 RUNNING",
                    "所有状态更新带 version、status 条件和 fencing_token",
                ],
                reference="""状态机要分层讲，否则容易把任务配置状态、一次触发状态和一次回调尝试混成一团。job 的状态只有 ENABLED、PAUSED、DELETED，控制的是未来是否继续计算 next_fire_time。trigger_record 的状态从 INIT 开始，表示某个 job_id、fire_time 已经被唯一键占住；派发器成功生成所有分片的 execution_log 后进入 DISPATCHING 或 DONE，若部分 shard 最终失败则进入 PARTIAL_FAILED。execution_log 的状态更细：READY 表示等待发送，RUNNING 表示某个 dispatcher 持有执行权，SUCCEEDED 表示业务方确认成功，FAILED 表示不可重试或重试耗尽，TIMEOUT 表示超过 deadline 但还不知道业务方是否执行。可重试失败不要覆盖原记录，而是按 attempt 新增或推进到 RETRY_WAIT 后再创建下一次尝试；idempotency_key 要稳定包含 job_id、fire_time、shard_no，使业务方即使收到多次也能去重。并发控制上，每次状态迁移都带 where status in (...)、version=old_version，以及 trigger_record.fencing_token 不小于当前 owner token；抢到 0 行说明已经被其他节点推进。旧 owner 租约过期后如果继续写，因为 token 过期会失败；补偿器只接管 READY、RETRY_WAIT、长时间 RUNNING 等可恢复状态，不把已经 SUCCEEDED 的记录回滚。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="用时序图讲注册、预加载、到点触发、宕机接管、派发回调和补偿扫描。",
                diagram="""sequenceDiagram
  participant Biz as 业务方
  participant Api as 控制面
  participant Store as 任务库
  participant Owner as Owner协调器
  participant T as 触发节点
  participant Rec as 触发记录库
  participant Disp as 执行派发器
  participant Gw as 回调网关
  Biz->>Api: 创建任务 request_id
  Api->>Store: 写job和next_fire_time
  T->>Owner: 续租owner分片
  Owner-->>T: fencing_token
  T->>Store: 预加载15秒窗口
  T->>Rec: 到点批量写trigger_record
  Rec-->>T: created或existed
  T->>Disp: TriggerCreated
  Disp->>Gw: 发送shard回调
  Gw->>Biz: idempotency_key
  Biz-->>Gw: 成功或失败
  Disp->>Rec: 汇总触发状态""",
                points=[
                    "正常主链路从注册到 next_fire_time 入库开始",
                    "触发节点先拿 owner lease 再预加载窗口",
                    "到点批量写 trigger_record，唯一键处理重复",
                    "派发器按 shard 生成 execution_log 并调用业务方",
                    "节点宕机后 lease 过期，其他节点重新预加载并补写缺失记录",
                    "超时回调通过重试和业务幂等键收敛",
                ],
                reference="""正常流程是：业务方调用创建接口，控制面校验租户配额、表达式和回调地址，写 job、job_shard，并计算第一轮 next_fire_time。触发节点周期性向 Owner 协调器续租 owner_shard，拿到 fencing_token 后，只扫描自己 owner 分片里 15 秒窗口内的 ENABLED 任务，把 job_id、fire_time、job_version 放入本地时间轮。到 10:00:00 时，触发节点不是直接回调业务方，而是先批量写 trigger_record；写成功说明本节点赢得这个触发点，写冲突说明其他节点已经创建，直接跳过。随后 TriggerCreated 事件交给派发器，派发器读取 job_shard，为每个 shard 创建 execution_log，回调网关带 idempotency_key 调业务方。关键分支是触发节点宕机：如果 A 在 10:00:00 持有 3 万任务，只写了 2000 条就挂了，Owner 表中的 lease_until 到期后，B 通过 CAS 把 owner_shard 抢过来并得到更大的 fencing_token；B 重新扫描 09:59:45 到 10:00:15 的窗口，对 3 万任务再次尝试写 trigger_record。已经存在的 2000 条因 uk_job_fire 冲突不会重复派发，剩下 2.8 万条会被补写并派发。另一个分支是业务方超时：dispatcher 把 execution_log 标成 TIMEOUT 或 RETRY_WAIT，按指数退避重试；如果第一次实际已成功，业务方用同一个 idempotency_key 返回已处理，平台再收敛为 SUCCEEDED。""",
            ),
            dict(
                key="reliability",
                title="可靠性方案",
                minutes=5,
                prompt="围绕选主、幂等、重试、补偿、限流、扩展和指标，说明每个失败模式的机制、代价和兜底。",
                points=[
                    "owner lease 续租、过期接管和 fencing 防脑裂",
                    "trigger_record 唯一键和业务 idempotency_key 双层幂等",
                    "重试按错误分类和指数退避，不无限打业务方",
                    "巡检补偿扫描漏触发、卡住执行和 next_fire_time 异常",
                    "租户、任务、下游域名多级限流与隔离",
                    "监控触发延迟、漏触发、重复冲突、lease 抖动和队列堆积",
                ],
                reference="""可靠性要按失败模式闭环。第一类是触发节点宕机或网络分区，机制是 job_owner lease 加 fencing_token：租约短会接管快但抖动大，租约长会增加恢复延迟，所以可以取 5 到 10 秒租约、2 秒续租，并用指标观察 lease_renew_fail 和 owner_rebalance_count。第二类是重复触发，平台侧由 trigger_record 的 uk_job_fire 保证同一 fire_time 只有一条记录，业务侧由 idempotency_key 抵御超时重试；代价是数据库写入成为关键路径，因此要批量写、分库分表和热点削峰。第三类是漏触发，靠预加载窗口、接管后回扫窗口和巡检补偿三层兜底；补偿器按 fire_time 和 status 扫描，发现 job.next_fire_time 已过但没有 trigger_record 就补写，指标是 missed_trigger_found。第四类是业务方慢或失败，按错误分类重试：连接失败、5xx、超时可退避重试，明确 4xx 不重试；每个租户、任务和 callback_target 有并发上限，防止一个下游拖垮全局。第五类是存储和队列故障，消息队列只做派发削峰，权威状态在数据库；队列丢消息时补偿器从 trigger_record 重建派发。扩展上，owner_shard 数固定大于机器数，增加触发节点只需迁移租约；执行日志按天和 tenant_id 分片，冷数据异步归档。核心指标包括 trigger_lag_p99、trigger_insert_conflict_rate、execution_success_rate、retry_exhausted_count、timeout_rate、补偿发现数量、数据库写入延迟和每租户限流次数。""",
            ),
        ],
        mistakes=[
            dict(wrong="我每秒扫一遍 job 表，next_fire_time 到了就直接调用业务接口。", verdict="最大扣分点", why="百万任务和 20 万同秒触发下，全表扫描会把数据库打爆，且直接回调没有权威触发记录，节点宕机后无法判断哪些已触发、哪些漏触发。"),
            dict(wrong="用消息队列保证 exactly once，消费者只要不重复消费就行。", verdict="有错", why="通用消息队列通常只能提供至少一次或有限去重，不能替代业务维度的 (job_id, fire_time) 唯一键；权威去重必须落在触发记录表或等价存储。"),
            dict(wrong="加一个分布式锁，抢到锁的机器负责所有任务。", verdict="方向对但不准", why="锁只能解决互斥，不能解决百万任务扩展、锁过期后的旧持有者写入、分片迁移和局部故障恢复；要用 owner 分片、lease 和 fencing。"),
            dict(wrong="业务方超时我就立刻再调一次，直到成功为止。", verdict="有错", why="超时并不等于业务没执行，盲目重试会造成重复副作用；必须带稳定幂等键、限制重试次数、指数退避，并区分 4xx、5xx 和网络错误。"),
            dict(wrong="时间轮在内存里很快，所以不用落 trigger_record。", verdict="缺失", why="时间轮只解决触发精度和扫描成本，不是权威状态。进程重启、迁移和补偿都需要可查询的触发记录，否则无法证明不漏不重。"),
            dict(wrong="暂停任务时把所有执行记录都改成取消。", verdict="搞反", why="暂停语义通常只阻止未来 fire_time；已经 RUNNING 的回调可能已经对业务产生副作用，不能靠平台单方面回滚，只能标记和后续补偿。"),
        ],
        walkthrough="""按例子走一遍。09:59:45，节点 A 已经持有若干 owner_shard 的租约，fencing_token 为 101，它扫描自己分片内 10:00:00 前后 15 秒窗口的任务，把 3 万个 fire_time=10:00:00 的任务放入本地时间轮。10:00:00 到达后，A 先批量写 trigger_record，而不是直接回调业务方；前 2000 条写入成功，每条都有唯一的 (job_id, fire_time)，随后对应 TriggerCreated 被派发器消费并生成各 shard 的 execution_log。此时 A 宕机，剩余 2.8 万个还没写。10:00:07 左右，A 的 lease_until 过期，节点 B 通过 CAS 抢到同一批 owner_shard，获得 fencing_token 102。B 会回扫 09:59:45 到 10:00:15 的窗口并再次尝试为 3 万任务写 trigger_record。已经由 A 写入的 2000 条因为 uk_job_fire 冲突返回 existed，不会再产生新的派发；剩余 2.8 万条被 B 创建并继续派发。若 A 假死后恢复，拿旧 token 101 更新状态会失败。业务方回调超时时，dispatcher 进入 RETRY_WAIT，用同一个 idempotency_key 退避重试，最终由业务方幂等表把可能重复到达的请求收敛成一次副作用。""",
        oral="""我会把这题分成控制面、归属面、触发面和执行面。控制面负责注册、修改、启停和查询，写 job、job_shard，并统一计算 next_fire_time。归属面用 job_owner 把任务按 owner_shard 分给触发节点，每个租约都有 lease_until、version 和 fencing_token，避免锁过期后的旧节点继续写。触发面不每秒全表扫描，而是每个节点只预加载自己 owner 分片未来 15 秒的任务，放入本地时间轮；到点后第一步是批量写 trigger_record，靠 (job_id, fire_time) 唯一键保证同一个触发点只有一条权威记录。执行面读取 trigger_record，按 job_shard 生成 execution_log，通过回调网关调用业务 HTTP/RPC，带 job_id、fire_time、shard_no、attempt 和稳定 idempotency_key。状态上，job 的 ENABLED/PAUSED 只影响未来触发；trigger_record 从 INIT 到 DISPATCHING 再到 DONE 或 PARTIAL_FAILED；execution_log 从 READY、RUNNING 到 SUCCEEDED、FAILED 或 RETRY_WAIT。可靠性上，节点宕机靠 lease 过期后接管并回扫窗口，重复创建靠唯一键吸收，旧节点靠 fencing 被拒绝；业务超时靠幂等键、错误分类、指数退避和重试上限收敛；队列丢消息靠补偿器从 trigger_record 重建派发。回到例子，A 在 10 点持有 3 万任务并写了 2000 条后宕机，B 接管后重扫同一窗口，已存在的 2000 条不会重复，剩余 2.8 万条补写并派发。指标看 trigger_lag_p99、冲突率、漏触发补偿数、lease 抖动、回调成功率和每租户限流次数。""",
        followups=[
            dict(q="为什么不用数据库定时扫描就够了？", a="因为题眼是百万任务和同秒 20 万峰值。数据库扫描可以做补偿，但不能做主路径；主路径要先用 owner 分片缩小扫描范围，再用预加载窗口和时间轮降低到点延迟。否则每秒全表扫会造成锁竞争和 IO 峰值，触发精度也会随着表量线性变差。"),
            dict(q="如果两个节点同时认为自己拥有同一个 owner 分片怎么办？", a="这就是 lease 过期和网络分区带来的脑裂风险。只说分布式锁不够，必须让每次写 trigger_record 或推进状态都携带 fencing_token；存储层只接受当前 job_owner 中最新 token 的写入。旧节点即使恢复并继续执行，也只能写入失败或被唯一键吸收。"),
            dict(q="恰好一次和业务 HTTP 超时矛盾怎么处理？", a="平台无法在 HTTP 超时时证明业务方没有执行，所以不能承诺业务副作用恰好一次。正确拆法是平台保证同一 job_id、fire_time、shard_no 的权威触发唯一，回调带稳定 idempotency_key；业务方按幂等键查重，平台重试只是在至少一次投递上收敛到业务侧一次副作用。"),
            dict(q="20 万任务都在第 0 秒，数据库写入扛不住怎么办？", a="先承认唯一键写入是关键路径，然后用多级削峰：owner_shard 水平拆分、trigger_record 按 job_id 或 fire_time 分库分表、批量 insert ignore、连接池限流，以及对非高优任务允许几秒内扩散。不能牺牲唯一键去换速度，否则故障恢复时会重复触发。"),
            dict(q="如何处理修改 cron 时刚好到点？", a="job 表带 version，修改任务用 CAS 更新并计算新的 next_fire_time。触发节点预加载时带 job_version 写 trigger_record；如果控制面已经把任务改到新版本，派发前再校验版本和状态。这样可以定义清楚：修改提交前已经创建的 fire_time 按老版本执行，提交后的未来触发按新版本执行。"),
            dict(q="补偿器怎么避免把已成功的任务再次触发？", a="补偿器不直接调用业务，而是走同一条 CreateTrigger 路径。它扫描应触发但缺记录的时间窗口，写 trigger_record 时仍受 uk_job_fire 限制；已成功的触发已经有记录，所以只会返回 existed。补偿器的权限是补记录和恢复卡住状态，不允许覆盖 SUCCEEDED。"),
            dict(q="多租户隔离怎么落地？", a="控制面按 tenant_id 做任务数、触发 QPS、并发回调和日志查询配额；触发面调度时可以在同一 owner 内按租户公平队列派发；执行面按 tenant、job、callback_target 三维限流。这样某个租户的大促任务只会消耗自己的配额，不会拖慢其他租户的秒级触发。"),
            dict(q="时钟漂移会不会导致提前或延后触发？", a="触发节点需要使用统一时间源并监控本机 clock offset，超过阈值就停止续租 owner。fire_time 的权威值来自时间计算器写入的计划时间，本地时间轮只负责到点唤醒；补偿器按数据库时间回扫，可以兜住个别节点慢几秒造成的漏触发。"),
        ],
        variants=[
            "分布式延迟队列如何做到秒级投递和故障恢复",
            "工作流系统里的周期调度器如何设计",
            "IoT 设备百万级定时指令下发平台",
            "优惠券定时发放任务的去重与补偿设计",
        ],
    ),
    dict(
        id="x7",
        order=7,
        title="告警与通知平台",
        brief="设计一个从指标、日志和事件中生成告警，聚合降噪后多渠道通知并支持升级和值班的告警平台。",
        statement="""你要设计一个告警与通知平台。系统接入指标、日志和事件来源，用户可以配置告警规则，包括阈值、持续时间、同比环比、标签过滤和优先级。原始告警进入平台后要做聚合降噪：同类告警合并成 incident，支持抑制、静默、维护窗口和根因关联；同一告警不能重复通知，但关键 P0 不能漏发。系统还要支持分级与升级，例如值班人 5 分钟未确认升级给二线，10 分钟后升级给负责人；通知渠道包括 IM、短信、电话和 Webhook，并记录投递回执。需要提供值班表、静默规则、告警查询、认领、关闭和复盘数据。非功能要求是在告警风暴下不刷屏、不漏发关键告警，通知去重可审计，多租户隔离，核心告警端到端延迟秒级到十秒级。""",
        focus="""题眼是告警风暴时的两个相反目标：不要刷屏，但关键告警不能被降噪吞掉。设计必须用 fingerprint 把原始 alert_event 聚合成 incident，用 notify_task 唯一键保证同一接收人、渠道、级别只通知一次，再用优先级旁路、升级状态机和回执补偿兜住 P0。""",
        scale="""规模假设：正常 2 万 alert_event/min，网络抖动时 2 分钟 5 万条原始告警；其中 P0 可能只有 3 条但必须 10 秒内通知首个值班人。规则 5 万条，活跃 incident 10 万个，通知峰值 5000 task/min。事件保留 30 天，incident 保留 180 天；聚合查询 P95 小于 300ms，通知去重窗口 24 小时。""",
        example="""某机房网络抖动 2 分钟内产生 5 万条原始告警，来源包括主机 ping 失败、服务错误率上升和日志连接超时。大部分都属于同一网络根因，应合并、抑制或静默；但其中 3 条核心服务 P0 告警必须绕过普通降噪，通知当前值班人。如果 5 分钟无人确认，要自动升级到下一位。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清告警语义",
                minutes=3,
                prompt="先问清数据源、规则类型、聚合维度、静默语义、升级策略、通知渠道和回执可信度。",
                points=[
                    "确认指标、日志、事件来源的格式和乱序延迟",
                    "确认规则支持阈值、持续时间、同比环比和标签过滤",
                    "确认 fingerprint 由哪些标签组成",
                    "确认抑制、静默、维护窗口和关闭语义",
                    "确认 P0 是否可以绕过部分降噪",
                    "确认通知渠道的回执、重试和升级时限",
                ],
                reference="""我会先问清告警从哪里来以及什么叫“不漏”。指标告警通常按时间窗口计算，日志和事件可能乱序到达，所以 alert_event 要保存 source_event_id、event_time 和 received_at，评估规则时要有 watermark 或延迟窗口。规则语义上，阈值、持续时间和同比环比会影响状态：持续 5 分钟才告警就不能第一条异常马上通知；同比环比需要历史基线。聚合维度要明确，fingerprint 通常由 rule_id、service、region、cluster、resource_type 和可控标签组成，不能把 instance_id 全放进去，否则风暴时无法合并。静默和维护窗口是“抑制通知”还是“连 incident 都不创建”也要问清；我倾向于仍创建 incident 并标记 suppressed，便于审计。P0 规则要有 bypass_normal_silence 或 critical_path 标识，避免被大范围网络告警完全吞掉。通知侧要问渠道回执是否可信，电话接通、短信提交成功、IM 已读含义不同；升级依据应是 incident 未 ACK，而不是某个渠道未回执。""",
            ),
            dict(
                key="estimate",
                title="容量估算",
                minutes=4,
                prompt="根据 2 分钟 5 万条风暴和 3 条 P0，估算事件写入、聚合比例、通知任务量、存储和分片。",
                points=[
                    "计算风暴时 alert_event 写入速率",
                    "估算聚合后 incident 和 notify_task 的量级",
                    "估算规则匹配和 fingerprint 查询压力",
                    "估算事件与通知日志存储量",
                    "说明哪些路径要优先级队列",
                    "说明为什么通知不能按原始事件逐条发送",
                ],
                reference="""例子里 2 分钟 5 万条，平均 416 event/s，不算特别高，但真实问题是这些事件可能集中在几十秒内并触发多个规则，而且如果逐条通知会产生 5 万次消息，直接把值班人刷爆。正常 2 万/min 是 333 event/s，按每条事件 2KB 计算，30 天原始事件约 1.7TB，需要冷热分层。规则 5 万条不能每条事件逐个全量匹配，应该按数据源、租户、service、metric_name 或 event_type 建规则索引，先筛候选规则，再计算窗口。聚合后假设 5 万条网络抖动合成 100 到 300 个 incident，notify_task 如果每个 incident 首轮通知 2 人 2 渠道，就是几百到一千条，而不是 5 万条。P0 的 3 条必须走高优先级通道：事件摄取、规则评估、incident upsert、notify_task 创建和发送队列都要有 priority 字段或独立队列，避免被普通 P2/P3 风暴排队淹没。存储上 alert_event 按天和 tenant 分片，incident 以 fingerprint 唯一键做当前窗口 upsert，notify_task 以 incident_id、receiver、channel、level 唯一键去重；这些数字决定了主路径要异步化和批量化，但 P0 通知创建不能依赖长批处理。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出接入、规则引擎、聚合降噪、incident、通知、升级、值班和查询服务，说明状态归属。",
                diagram="""flowchart LR
  A["指标日志事件"] --> B["接入网关"]
  B --> C["事件队列"]
  C --> D["规则引擎"]
  D --> E["事件库"]
  D --> F["聚合降噪器"]
  F --> G["Incident库"]
  F --> H["静默规则库"]
  G --> I["通知编排器"]
  J["值班服务"] --> I
  I --> K["通知任务库"]
  I --> L["渠道网关"]
  L --> M["外部渠道"]
  N["升级巡检器"] --> G
  N --> I""",
                points=[
                    "接入网关做鉴权、格式化和 source_event_id 去重",
                    "规则引擎按候选规则索引计算阈值和持续时间",
                    "聚合降噪器负责 fingerprint、抑制、静默和根因关联",
                    "Incident 服务是聚合后权威状态",
                    "通知编排器根据值班表生成 notify_task",
                    "渠道网关适配 IM、短信、电话和 Webhook",
                    "升级巡检器按未 ACK 时间推进级别",
                ],
                reference="""服务上我会按数据流拆。接入网关是无状态服务，负责租户鉴权、限流、规范化字段、source_event_id 去重和写入事件队列；它不做复杂规则计算，避免入口被慢查询拖垮。规则引擎消费事件队列，根据 tenant、source_type、metric_name、service 等索引找到候选 alert_rule，维护短窗口状态，判断阈值、持续时间和同比环比是否成立，成立后写 alert_event。聚合降噪器读取 alert_event，计算 fingerprint，并查询 silence_rule、抑制关系和维护窗口；它通过 incident 表的 fingerprint 唯一键 upsert 聚合后的事件。Incident 服务或库是告警生命周期的权威，保存 OPEN、ACKED、RESOLVED、CLOSED、SUPPRESSED 等状态，以及 severity、first_seen、last_seen、event_count。通知编排器在 incident 新建、升级或恢复时读取值班服务，生成 notify_task；notify_task 的唯一键保证同一 incident、receiver、channel、level 不重复通知。渠道网关是无状态适配层，处理 IM、短信、电话、Webhook 的签名、回执和重试。升级巡检器周期扫描未 ACK 且 next_escalate_at 到期的 incident，推进 escalation_level 并重新调用通知编排器。查询和复盘服务走事件库、incident 库和通知任务库，重查询不影响主链路。状态归属上，规则配置在 alert_rule，原始事实在 alert_event，聚合事实在 incident，通知事实在 notify_task；缓存和队列只做加速，不能当最终判定。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="给出 alert_rule、alert_event、incident、notify_task、oncall_schedule、silence_rule 等表，说明 fingerprint 和通知唯一键。",
                ddl="""
CREATE TABLE `alert_rule` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '规则ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `name` VARCHAR(128) NOT NULL COMMENT '规则名称',
  `source_type` ENUM('METRIC','LOG','EVENT') NOT NULL COMMENT '来源类型',
  `expr` TEXT NOT NULL COMMENT '规则表达式',
  `duration_seconds` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '持续时间',
  `severity` ENUM('P0','P1','P2','P3') NOT NULL COMMENT '级别',
  `fingerprint_tpl` VARCHAR(512) NOT NULL COMMENT '指纹模板',
  `status` ENUM('ENABLED','DISABLED') NOT NULL COMMENT '状态',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`,`name`),
  KEY `idx_tenant_source_status` (`tenant_id`,`source_type`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警规则表';

CREATE TABLE `alert_event` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '原始告警事件ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `rule_id` BIGINT UNSIGNED NOT NULL COMMENT '规则ID',
  `source_event_id` VARCHAR(128) NOT NULL COMMENT '来源事件ID',
  `fingerprint` VARCHAR(128) NOT NULL COMMENT '聚合指纹',
  `severity` ENUM('P0','P1','P2','P3') NOT NULL COMMENT '级别',
  `labels_json` JSON NOT NULL COMMENT '标签',
  `summary` VARCHAR(512) NOT NULL COMMENT '摘要',
  `event_time` DATETIME(3) NOT NULL COMMENT '事件时间',
  `received_at` DATETIME(3) NOT NULL COMMENT '接收时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_source_event` (`tenant_id`,`source_event_id`),
  KEY `idx_fingerprint_time` (`fingerprint`,`event_time`),
  KEY `idx_tenant_time` (`tenant_id`,`event_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='原始告警事件表';

CREATE TABLE `incident` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '聚合事件ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `fingerprint` VARCHAR(128) NOT NULL COMMENT '聚合指纹',
  `rule_id` BIGINT UNSIGNED NOT NULL COMMENT '主规则ID',
  `severity` ENUM('P0','P1','P2','P3') NOT NULL COMMENT '最高级别',
  `status` ENUM('OPEN','ACKED','RESOLVED','CLOSED','SUPPRESSED') NOT NULL COMMENT '状态',
  `event_count` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '事件数',
  `first_seen_at` DATETIME(3) NOT NULL COMMENT '首次出现',
  `last_seen_at` DATETIME(3) NOT NULL COMMENT '最近出现',
  `ack_by` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '确认人',
  `ack_at` DATETIME(3) NULL COMMENT '确认时间',
  `escalation_level` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '升级级别',
  `next_escalate_at` DATETIME(3) NULL COMMENT '下次升级时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_fingerprint` (`tenant_id`,`fingerprint`),
  KEY `idx_status_escalate` (`status`,`next_escalate_at`),
  KEY `idx_tenant_status_seen` (`tenant_id`,`status`,`last_seen_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='聚合告警事件表';

CREATE TABLE `notify_task` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '通知任务ID',
  `incident_id` BIGINT UNSIGNED NOT NULL COMMENT '聚合事件ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `receiver` VARCHAR(128) NOT NULL COMMENT '接收人',
  `channel` ENUM('IM','SMS','PHONE','WEBHOOK') NOT NULL COMMENT '渠道',
  `level` INT UNSIGNED NOT NULL COMMENT '升级级别',
  `status` ENUM('PENDING','SENDING','SENT','ACKED','FAILED','CANCELED') NOT NULL COMMENT '通知状态',
  `dedup_key` VARCHAR(256) NOT NULL COMMENT '通知去重键',
  `attempt` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '尝试次数',
  `next_retry_at` DATETIME(3) NULL COMMENT '下次重试时间',
  `receipt_at` DATETIME(3) NULL COMMENT '回执时间',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_incident_receiver_channel_level` (`incident_id`,`receiver`,`channel`,`level`),
  UNIQUE KEY `uk_dedup_key` (`dedup_key`),
  KEY `idx_status_retry` (`status`,`next_retry_at`),
  KEY `idx_tenant_created` (`tenant_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知任务表';

CREATE TABLE `oncall_schedule` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '值班表ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `team_id` BIGINT UNSIGNED NOT NULL COMMENT '团队ID',
  `level` INT UNSIGNED NOT NULL COMMENT '升级级别',
  `start_at` DATETIME(3) NOT NULL COMMENT '开始时间',
  `end_at` DATETIME(3) NOT NULL COMMENT '结束时间',
  `receiver` VARCHAR(128) NOT NULL COMMENT '值班人',
  `channels_json` JSON NOT NULL COMMENT '通知渠道',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_team_level_start` (`team_id`,`level`,`start_at`),
  KEY `idx_tenant_team_time` (`tenant_id`,`team_id`,`start_at`,`end_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='值班排班表';

CREATE TABLE `silence_rule` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '静默规则ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `matcher_json` JSON NOT NULL COMMENT '标签匹配条件',
  `scope` ENUM('RULE','SERVICE','TEAM','GLOBAL') NOT NULL COMMENT '范围',
  `starts_at` DATETIME(3) NOT NULL COMMENT '开始时间',
  `ends_at` DATETIME(3) NOT NULL COMMENT '结束时间',
  `created_by` VARCHAR(128) NOT NULL COMMENT '创建人',
  `status` ENUM('ACTIVE','EXPIRED','CANCELED') NOT NULL COMMENT '状态',
  PRIMARY KEY (`id`),
  KEY `idx_tenant_time_status` (`tenant_id`,`starts_at`,`ends_at`,`status`),
  KEY `idx_scope_status` (`scope`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='静默规则表';
""",
                points=[
                    "alert_rule 存规则表达式、持续时间、级别和 fingerprint 模板",
                    "alert_event 用 source_event_id 去重并保留原始事实",
                    "incident 用 (tenant_id, fingerprint) 唯一键聚合同类告警",
                    "notify_task 用 (incident_id, receiver, channel, level) 唯一键防重复通知",
                    "oncall_schedule 支持按团队和升级级别查当前值班人",
                    "silence_rule 保存匹配条件和时间窗，不能直接删除历史 incident",
                    "大标签和原始日志只存摘要或引用，避免在线表膨胀",
                ],
                reference="""表设计的核心是把“原始事件、聚合事件、通知任务”分开。alert_rule 保存规则表达式、duration_seconds、severity 和 fingerprint_tpl；fingerprint 模板决定哪些标签参与聚合，必须版本化或至少在规则变更时能解释历史事件。alert_event 保存每条原始告警，tenant_id 和 source_event_id 唯一键用于入口去重，event_time 和 received_at 用于处理乱序和延迟；labels_json 可存标签，但大日志正文不应放在线表，只存摘要和对象引用。incident 是降噪后的权威状态，(tenant_id, fingerprint) 唯一键让同类告警 upsert 到同一行，event_count、first_seen_at、last_seen_at 记录风暴规模，status、ack_by、escalation_level 和 next_escalate_at 驱动生命周期。notify_task 是通知幂等账本，uk_incident_receiver_channel_level 保证同一 incident 在同一升级级别不会给同一人同一渠道重复发；dedup_key 便于跨重试和渠道回执查账。oncall_schedule 按 team、level、时间范围查询当前和下一升级人，channels_json 表示个人偏好的渠道顺序。silence_rule 不应该删除 alert_event 或 incident，而是命中后把 incident 标记 SUPPRESSED 或跳过 notify_task，这样复盘时还能解释为什么没通知。查询索引围绕 tenant、时间、status、fingerprint 和 next_escalate_at 设计；风暴期间最热的是 incident upsert 和 notify_task 唯一键写入，所以要按 tenant 或 fingerprint 分片。""",
            ),
            dict(
                key="api",
                title="接口与事件",
                minutes=5,
                prompt="列出接入事件、规则管理、incident 操作、静默、值班和通知回执接口，明确幂等和返回。",
                points=[
                    "事件接入要带 source_event_id 和 event_time",
                    "规则创建修改要校验表达式和 fingerprint 模板",
                    "incident ACK、关闭和备注要 CAS 防并发覆盖",
                    "静默规则创建要返回命中预估和审计信息",
                    "通知回执要能按 provider_msg_id 回写 notify_task",
                    "内部 IncidentUpsert 和 NotifyTaskCreate 要幂等",
                ],
                reference="""对外接入接口是 POST /v1/events，参数包括 tenant_id、source_type、source_event_id、event_time、labels、metric_value 或 log_summary，返回 accepted_event_id；source_event_id 是入口幂等键，同一来源重发不会生成两条 alert_event。规则接口包括 POST /v1/rules、PATCH /v1/rules/{id}、POST /v1/rules/{id}:enable，创建时要校验表达式可执行、duration 合法、fingerprint_tpl 不包含高基数字段。incident 操作包括 GET /v1/incidents?status=&severity=&service=，POST /v1/incidents/{id}:ack，POST /v1/incidents/{id}:close；ack 和 close 带 version 或 updated_at，避免两个人同时操作互相覆盖。静默接口 POST /v1/silences，参数是 matcher、starts_at、ends_at、reason，返回预计命中规则和审计 id；关键 P0 是否允许被静默要由规则策略控制。值班接口 GET /v1/oncall/current?team_id=&time= 给通知编排器查人。渠道回执接口 POST /v1/notify/receipts，带 provider_msg_id、status、receipt_at 和 raw_code，回写 notify_task。内部事件包括 AlertEventCreated、IncidentUpserted、NotifyTaskCreated、NotifyReceiptUpdated、IncidentEscalated；IncidentUpsert 以 tenant_id、fingerprint 幂等，NotifyTaskCreate 以 incident_id、receiver、channel、level 幂等。返回值要区分 accepted、deduplicated、suppressed 和 rate_limited，方便排查“为什么没通知”。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="画出 incident 与 notify_task 的状态，说明 ACK、恢复、关闭、静默和升级如何转换。",
                diagram="""stateDiagram-v2
  [*] --> OPEN
  OPEN --> SUPPRESSED: 命中静默
  SUPPRESSED --> OPEN: 静默结束仍异常
  OPEN --> ACKED: 值班人确认
  OPEN --> ESCALATED: 超时未确认
  ESCALATED --> ACKED: 升级后确认
  ACKED --> RESOLVED: 指标恢复
  OPEN --> RESOLVED: 自动恢复
  RESOLVED --> CLOSED: 关闭归档
  ACKED --> OPEN: 再次触发
  RESOLVED --> OPEN: 复燃
  CLOSED --> [*]""",
                points=[
                    "incident 状态包括 OPEN、SUPPRESSED、ESCALATED、ACKED、RESOLVED、CLOSED",
                    "升级是未 ACK 的派生状态或 escalation_level 增加",
                    "notify_task 独立维护 PENDING、SENDING、SENT、FAILED、CANCELED",
                    "恢复事件只能把仍同 fingerprint 的 incident 推到 RESOLVED",
                    "关闭后同 fingerprint 再来可复燃或开新 incident，需定义窗口",
                    "状态迁移用 version/CAS，通知创建用唯一键",
                ],
                reference="""incident 状态机要和通知任务状态机分开。incident 新建后是 OPEN，表示需要处理；如果命中静默或维护窗口，可以进入 SUPPRESSED，但我会保留事件计数和时间，避免事后无法复盘。OPEN 超过 ack_deadline 没有人确认时，不一定要改成另一个终态，可以把 escalation_level 加一并记录 ESCALATED 事件；图里画成 ESCALATED 是为了提醒候选人升级也是状态变化。值班人确认后进入 ACKED，后续同 fingerprint 的事件继续增加 event_count 但不重复首轮通知；如果异常指标恢复，进入 RESOLVED，人工确认复盘后 CLOSED。RESOLVED 或 ACKED 后再次收到同 fingerprint，要看 reopen_window：窗口内复燃回到 OPEN，窗口外可以创建新的 incident generation。notify_task 独立从 PENDING 到 SENDING、SENT、FAILED 或 CANCELED，渠道回执只影响通知任务，不等于 incident 已 ACK；真正 ACK 必须来自用户操作或可信渠道按钮。并发上，ACK、关闭、恢复、升级巡检可能同时发生，所以 incident 更新要带 version 和当前 status 条件；notify_task 创建要依赖唯一键，巡检器重复跑也不会重复发同一 level 的同一渠道。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="用时序图讲事件进入、规则评估、聚合、静默判断、通知、回执和升级巡检。",
                diagram="""sequenceDiagram
  participant Src as 数据源
  participant In as 接入网关
  participant Q as 事件队列
  participant Rule as 规则引擎
  participant Agg as 聚合降噪器
  participant Inc as Incident库
  participant Noti as 通知编排器
  participant Oncall as 值班服务
  participant Chan as 渠道网关
  Src->>In: 上报告警事件
  In->>Q: 规范化后入队
  Q->>Rule: 消费事件
  Rule->>Agg: AlertEventCreated
  Agg->>Inc: 按fingerprint upsert
  Agg->>Noti: 需要通知
  Noti->>Oncall: 查询值班人
  Noti->>Chan: 创建notify_task并发送
  Chan-->>Noti: 回执
  Noti->>Inc: 更新通知结果""",
                points=[
                    "入口先去重和限流，再异步进入规则引擎",
                    "规则引擎生成 alert_event，不直接通知用户",
                    "聚合降噪器通过 fingerprint upsert incident",
                    "静默命中时记录 suppressed，不创建普通通知任务",
                    "P0 使用高优先级队列和升级策略",
                    "升级巡检基于 incident 未 ACK 和 next_escalate_at",
                ],
                reference="""正常流程是数据源把指标、日志或事件送到接入网关，网关校验租户、按 source_event_id 去重，并把规范化事件写入队列。规则引擎消费后，只对候选规则计算阈值、持续时间或同比环比；条件满足时写 alert_event，并把 AlertEventCreated 发给聚合降噪器。聚合降噪器根据规则的 fingerprint_tpl 提取标签，计算 fingerprint，查询静默规则和抑制关系，然后 upsert incident：新 incident 记录 first_seen，已有 incident 只更新 last_seen、event_count 和最高 severity。若 incident 需要通知，通知编排器查 oncall_schedule，按严重级别生成 receiver 和 channel 列表，再用 notify_task 唯一键创建任务，渠道网关发送并回写回执。关键分支一是风暴：5 万条网络事件会不断 upsert 同一批 incident，event_count 增加，但首轮 notify_task 因唯一键只生成一次；后续只按节流策略发送摘要更新。关键分支二是 P0：规则标记 critical 后进入高优先级队列，即使命中普通网络抑制，也至少通知核心服务值班人或要求人工确认抑制。关键分支三是无人 ACK：升级巡检器扫描 OPEN 且 next_escalate_at 到期的 incident，CAS 增加 escalation_level，再为下一位值班人生成新的 notify_task；如果 CAS 失败说明已被 ACK 或其他巡检器处理。""",
            ),
            dict(
                key="reliability",
                title="可靠性方案",
                minutes=5,
                prompt="说明告警风暴、重复通知、漏发、渠道失败、升级失效、静默误伤和可观测指标。",
                points=[
                    "入口限流分级，P0 独立优先级通道",
                    "source_event_id、fingerprint、notify_task 唯一键三层去重",
                    "通知失败按渠道重试和降级，不无限刷屏",
                    "升级巡检从 incident 权威状态重建通知",
                    "静默规则可审计，关键规则可禁止全局静默",
                    "监控事件延迟、聚合比、重复通知、漏发补偿和 ACK 时长",
                ],
                reference="""可靠性要围绕“不刷屏、不漏 P0”展开。告警风暴时，入口按租户和来源限流，但 P0 或 critical 事件走独立优先级队列；普通 P2/P3 可以降采样或延迟聚合，不能占满通知线程。重复通知靠三层幂等：source_event_id 防入口重复，incident 的 fingerprint 唯一键防同类事件变成多条 incident，notify_task 的 incident_id、receiver、channel、level 唯一键防巡检或重试重复发。漏发风险来自队列丢失、通知服务宕机、渠道失败和静默误伤；兜底是所有状态落库，通知编排器和升级巡检器都能从 incident 表扫描 OPEN 且未生成对应 notify_task 的记录重建任务。渠道失败按策略重试和降级：IM 失败可转短信，短信失败可转电话，但每个渠道有 attempt 和退避，避免无限刷屏。静默规则必须有创建人、时间窗、matcher 和审计记录，P0 可以要求双人审批或只允许降噪不允许完全静默。扩展上，alert_event 按时间和租户分片，incident 按 fingerprint 分片，通知任务按 status 和 next_retry_at 扫描。指标包括 event_ingest_lag、rule_eval_lag、incident_aggregation_ratio、notify_duplicate_blocked、P0_first_notify_latency、ack_latency、escalation_count、silenced_p0_count、channel_success_rate 和风暴期间队列堆积。""",
            ),
        ],
        mistakes=[
            dict(wrong="所有原始告警都直接发给值班人，最多加个限流。", verdict="最大扣分点", why="这和题眼直接冲突。风暴时 5 万条会把人刷爆，限流还可能丢掉 P0；必须先 fingerprint 聚合成 incident，再按级别和值班策略通知。"),
            dict(wrong="只要 fingerprint 一样就永远合成一条，不需要状态机。", verdict="有错", why="同一指纹也有打开、确认、恢复、关闭和复燃窗口。没有状态机会导致历史告警和新故障混在一起，升级和 SLA 统计都不可信。"),
            dict(wrong="通知发送成功就说明告警已确认。", verdict="搞反", why="渠道回执只表示消息提交或送达，不代表人处理。incident 的 ACK 必须来自用户确认或可信交互按钮，否则升级流程会被误停止。"),
            dict(wrong="静默规则命中就不记录任何东西。", verdict="缺失", why="不记录会导致事后无法解释为什么关键告警没通知。正确做法是保留 alert_event 和 suppressed incident，通知可抑制但审计不能丢。"),
            dict(wrong="用消息队列去重，消费者失败就重试发送。", verdict="方向对但不准", why="队列重试只能保证任务再次被消费，不能防止同一 incident 对同一人重复通知；notify_task 必须有业务唯一键和状态表。"),
            dict(wrong="P0 也完全服从全局静默，维护窗口里一律不发。", verdict="有错", why="核心告警不能被粗粒度静默误伤。P0 至少要有旁路、审批或降级通知策略，否则一次错误静默会造成关键事故漏发。"),
        ],
        walkthrough="""例子中，机房网络抖动开始后，5 万条原始事件先进入接入网关，按 source_event_id 去重并写入事件队列。规则引擎对 ping 失败、错误率、连接超时等候选规则做窗口计算，产出 alert_event。聚合降噪器计算 fingerprint，例如 region=某机房、failure_type=network、service_group=基础网络，大量普通事件 upsert 到少量 incident，event_count 持续增加，但 notify_task 的唯一键只让首轮值班通知生成一次，后续最多按节流发送摘要。与此同时，3 条核心服务 P0 的规则带 critical 标记，进入高优先级队列；即使它们也和网络抖动有关，系统仍创建独立或提升 severity 的 incident，并立即查询 oncall_schedule，生成当前值班人的 IM、短信或电话 notify_task。渠道网关发送后回写 SENT，但 incident 仍是 OPEN。5 分钟后如果没有 ACK，升级巡检器扫描到 next_escalate_at 到期，用 CAS 把 escalation_level 从 0 推到 1，再为二线值班人创建新的 notify_task。若网络恢复，规则引擎发恢复事件，incident 进入 RESOLVED，人工复盘后 CLOSED；所有静默、抑制和通知回执都可审计。""",
        oral="""我会把告警平台拆成事件接入、规则评估、聚合降噪、incident 状态、通知编排和值班升级六层。入口接指标、日志和事件，先做租户鉴权、source_event_id 去重和限流，然后进入队列。规则引擎按 source_type、metric_name、service 等索引找候选规则，计算阈值、持续时间和同比环比，产出 alert_event。alert_event 只是原始事实，不直接通知；聚合降噪器根据规则的 fingerprint 模板，把同类事件 upsert 到 incident，fingerprint 唯一键保证风暴时不会产生海量重复告警。incident 保存 OPEN、ACKED、RESOLVED、CLOSED、SUPPRESSED、escalation_level、next_escalate_at 和 event_count，是告警生命周期权威。通知编排器只在 incident 新建、升级、恢复等状态变化时查值班表，生成 notify_task；notify_task 用 incident_id、receiver、channel、level 唯一键保证同一人同一渠道同一级别只发一次。可靠性上，P0 走高优先级队列和可配置旁路，避免被普通风暴或静默吞掉；渠道失败按退避重试和渠道降级，升级巡检器从 incident 表重建漏掉的通知任务。回到例子，2 分钟 5 万条网络告警大部分合并成少量网络 incident，只发摘要和一次首轮通知；3 条核心 P0 立即创建高优先级 incident，10 秒内通知当前值班人，5 分钟未 ACK 就 CAS 推进升级并通知二线。指标看聚合比、重复通知拦截数、P0 首次通知延迟、ACK 时长、静默命中 P0 数和渠道成功率。""",
        followups=[
            dict(q="fingerprint 应该包含哪些字段？", a="它要包含能表示同一故障根因的稳定字段，例如 rule_id、service、region、cluster、resource_type 和 failure_type；不要包含 instance_id、pod_id、request_id 这类高基数字段，否则风暴时无法聚合。代价是可能把相邻故障合并，所以要保留 labels 和样本事件供复盘。"),
            dict(q="如何确保 P0 不被静默误伤？", a="策略上 P0 规则可以禁止全局静默完全屏蔽，或要求静默命中后仍创建 SUPPRESSED incident 并通知安全接收人。实现上，规则有 critical 标志和 bypass_normal_silence 字段，聚合降噪器命中静默时根据级别决定是否跳过 notify_task。"),
            dict(q="通知服务挂了 10 分钟，恢复后怎么补？", a="因为 notify_task 和 incident 都落库，恢复后扫描 OPEN 或 ESCALATED 且缺少对应 level notify_task 的 incident，重新创建任务；已创建但 PENDING/SENDING 超时的任务按 next_retry_at 重试。唯一键保证补偿器重复扫描不会重复发。"),
            dict(q="同一 incident 的事件量一直增加，要不要一直通知？", a="不能每来一条都通知。一般首条通知，随后按时间或数量节流发送摘要，例如 10 分钟或 event_count 翻倍才发送 update；P0 可以更频繁，但仍应合并内容。状态变化如升级、恢复、关闭优先通知，因为它改变处理动作。"),
            dict(q="ACK 后又收到同类告警怎么办？", a="如果在同一次故障窗口内，只更新 event_count 和 last_seen，不重复首轮通知；如果超过 reopen_window 或已经 CLOSED，则可以创建新 generation 或把状态从 RESOLVED 拉回 OPEN。这个规则要写在 incident 状态机里，否则 SLA 和复盘会混乱。"),
            dict(q="渠道回执不可靠怎么办？", a="要把渠道提交成功、送达、已读、用户 ACK 分成不同字段。短信提交成功不能停止升级，只能说明渠道网关完成发送；升级依据应是 incident.ack_at。对于电话接通这类强回执，可以作为辅助，但最好仍要求按键或链接确认。"),
            dict(q="告警风暴时规则引擎会不会被打爆？", a="会，所以入口要按租户和来源限流，规则引擎要用候选规则索引和窗口聚合，而不是每条事件遍历 5 万规则。P0 或核心服务规则走优先级队列；普通事件可以批处理和延迟几秒，但不能阻塞关键路径。"),
            dict(q="如何证明没有重复通知？", a="从 notify_task 表证明，而不是从渠道日志猜。统计同一 incident_id、receiver、channel、level 的唯一键冲突数和实际发送数；如果渠道重试导致 provider 有多条记录，也要用 dedup_key 关联到一个 notify_task。"),
        ],
        variants=[
            "监控系统的告警聚合与升级设计",
            "SRE 事件响应平台如何防告警风暴",
            "多渠道通知中心的幂等与回执设计",
            "日志异常检测后的 incident 管理平台",
        ],
    ),
    dict(
        id="x8",
        order=8,
        title="短链服务",
        brief="设计一个读多写少的短链生成与跳转服务，支持统计、过期、封禁和防刷。",
        statement="""你要设计一个短链服务。用户提交长链接后，系统生成短码，访问短码时以毫秒级延迟跳转到原始 URL。系统要支持自定义短码、随机短码、批量创建、过期时间、封禁域名、访问统计、渠道参数、防刷和管理后台查询。非功能要求是跳转读多写少，热门活动会让少量短码在短时间内承受极高流量，P99 跳转延迟小于 10ms；短码不能被轻易遍历猜测，也不能因为哈希冲突覆盖已有链接。你需要说明短码生成、缓存、302 与 301 的取舍、异步统计、过期与封禁、限流和数据表设计。""",
        focus="""题眼是热身但不能答成 CRUD：跳转路径读多写少且 P99 < 10ms，所以必须缓存前置、数据库只做回源；同时短码不可被遍历猜测，不能用自增 ID 直接暴露，需要号段加混淆或随机码并处理冲突。""",
        scale="""规模假设：每天创建 100 万条短链，跳转 5 亿次，平均 5800 QPS；营销活动 10 分钟内 50 万次跳转集中在 3 个短码，单码峰值约 300 到 1000 QPS。短链总量 10 亿，短码长度 7 到 8 位，跳转 P99 < 10ms，创建接口 P95 < 100ms，访问统计允许分钟级延迟。""",
        example="""某营销活动创建了 3 个短码，10 分钟内产生 50 万次跳转。用户访问 /aB7x9Kq 时，系统要快速判断短码是否存在、是否过期、目标域名是否被封禁，然后返回跳转；统计系统要记录来源、地域、设备和渠道，但不能让统计写入拖慢跳转。""",
        minutes=35,
        sections=[
            dict(
                key="clarify",
                title="澄清需求",
                minutes=2,
                prompt="先问清短码类型、跳转语义、统计实时性、过期封禁、防刷和自定义短码规则。",
                points=[
                    "确认是否支持自定义短码和批量创建",
                    "确认 302 还是 301，以及目标 URL 是否可能变更",
                    "确认统计是实时精确还是可异步近似",
                    "确认过期、封禁和删除后的用户体验",
                    "确认短码是否要求不可预测",
                    "确认租户、域名和 IP 维度限流",
                ],
                reference="""我会先问清几个会改变设计的点。第一，短码是否允许自定义；自定义短码需要保留词、长度、字符集和唯一性校验，随机短码则要讨论冲突重试。第二，跳转用 302 还是 301；如果长链可能被封禁、过期或运营修改，默认用 302，避免浏览器和搜索引擎长期缓存错误目标。第三，统计口径是什么：跳转主链路只需要尽快返回，PV、UV、地域、设备可以异步写队列并分钟级聚合，不能同步更新数据库计数。第四，过期和封禁的体验要定义清楚，是返回 404、410 还是安全提示页；这会影响缓存里的 negative entry 和 blocked_domain 判断。第五，短码不可预测意味着不能直接把自增 ID base62 暴露，至少要加随机扰动、号段混淆或直接用安全随机码。最后确认租户隔离、防刷和 QPS 上限，因为热门活动的少数短码会成为缓存热点。""",
            ),
            dict(
                key="estimate",
                title="容量估算",
                minutes=3,
                prompt="用每天创建量、跳转量和活动峰值估算短码空间、缓存命中、数据库容量和统计队列。",
                points=[
                    "估算 7 到 8 位 base62 的码空间",
                    "估算日跳转平均 QPS 与活动峰值",
                    "估算短链表和统计表容量",
                    "说明热点短码必须走缓存",
                    "说明统计写入为何异步",
                ],
                reference="""base62 的 7 位空间约 3.5 万亿，8 位约 218 万亿；即使 10 亿短链，随机 7 位也有冲突概率，需要唯一键和重试，但空间总体足够。每天 100 万创建，短链元数据如果每条 1KB，一年约 365GB，数据库按 tenant 或 id 分片即可。跳转每天 5 亿，平均约 5800 QPS，活动 10 分钟 50 万次平均 833 QPS，集中在 3 个短码时单码约 278 QPS，真实峰值可能到 1000 QPS 以上。P99 < 10ms 决定跳转服务不能每次查数据库，必须本地缓存或分布式缓存命中后直接返回 302；数据库只处理缓存未命中、过期回源和管理查询。统计如果每次跳转同步 update visit_stat_daily，会产生热点行锁，尤其 3 个短码会把同一行打爆；正确做法是跳转路径投递轻量 visit event 到队列，聚合器按分钟或批量更新 visit_stat_daily。短码不可预测决定不能单纯 base62(id)，可以用发号器分配内部 id，再经过带密钥的置换或随机码生成，并由 code 唯一键兜底。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=5,
                prompt="画出创建服务、发号器、跳转服务、缓存、统计、风控和后台，说明读写路径分离。",
                diagram="""flowchart LR
  A["用户"] --> B["创建API"]
  B --> C["发号器"]
  C --> D["号段库"]
  B --> E["短链库"]
  A --> F["跳转服务"]
  F --> G["缓存"]
  G --> E
  F --> H["风控封禁"]
  F --> I["统计队列"]
  I --> J["统计聚合器"]
  J --> K["统计库"]
  L["管理后台"] --> E
  L --> H""",
                points=[
                    "创建 API 负责校验长链、租户配额和自定义短码",
                    "发号器用号段减少数据库抢号压力",
                    "跳转服务无状态扩展，主路径先查缓存",
                    "风控封禁提供域名、短码和 IP 规则",
                    "统计队列异步承接访问事件",
                    "管理后台负责封禁、解封、查询和审计",
                ],
                reference="""短链服务要明显读写分离。创建 API 是写路径，负责鉴权、校验 URL、检查 blocked_domain、处理自定义 code、调用发号器拿内部 id 或随机 code，最后写 short_link。发号器可以用 id_segment 表一次取一段号，例如每个创建节点拿 1 万个 id，在内存里递增，减少每次创建都访问数据库；生成 code 时再做 base62 和混淆，或者直接用安全随机码并靠 code 唯一键重试。跳转服务是读路径，无状态横向扩展，收到 /{code} 后先查本地缓存或分布式缓存，缓存命中且未过期、未封禁就立即返回 302；未命中才查 short_link 并回填缓存。风控封禁服务提供 blocked_domain、短码黑名单、IP 频率限制和异常 UA 判断，跳转服务在返回前做轻量检查。统计队列接收访问事件，统计聚合器按 code、date、channel、device 聚合写 visit_stat_daily。管理后台做创建查询、封禁解封、过期调整和审计。缓存不是权威，权威状态在 short_link 和 blocked_domain；封禁或修改目标 URL 时要主动删除缓存或把 cache_version 放进缓存值，避免继续跳转到危险链接。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=6,
                prompt="给出 short_link、id_segment、visit_stat_daily、blocked_domain 等表，说明唯一键和热点统计处理。",
                ddl="""
CREATE TABLE `short_link` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '内部ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `code` VARCHAR(32) NOT NULL COMMENT '短码',
  `long_url` VARCHAR(2048) NOT NULL COMMENT '原始URL',
  `domain` VARCHAR(255) NOT NULL COMMENT '目标域名',
  `status` ENUM('ACTIVE','EXPIRED','BLOCKED','DELETED') NOT NULL COMMENT '状态',
  `expire_at` DATETIME(3) NULL COMMENT '过期时间',
  `created_by` VARCHAR(128) NOT NULL COMMENT '创建人',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_tenant_created` (`tenant_id`,`created_at`),
  KEY `idx_domain_status` (`domain`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短链表';

CREATE TABLE `id_segment` (
  `biz_key` VARCHAR(64) NOT NULL COMMENT '业务键',
  `max_id` BIGINT UNSIGNED NOT NULL COMMENT '已分配最大ID',
  `step` INT UNSIGNED NOT NULL COMMENT '号段步长',
  `version` BIGINT UNSIGNED NOT NULL COMMENT 'CAS版本',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`biz_key`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='号段发号表';

CREATE TABLE `visit_stat_daily` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '统计ID',
  `code` VARCHAR(32) NOT NULL COMMENT '短码',
  `stat_date` DATE NOT NULL COMMENT '统计日期',
  `channel` VARCHAR(64) NOT NULL COMMENT '渠道',
  `pv` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '访问次数',
  `uv` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '访客数',
  `last_visit_at` DATETIME(3) NOT NULL COMMENT '最近访问时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code_date_channel` (`code`,`stat_date`,`channel`),
  KEY `idx_date_pv` (`stat_date`,`pv`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短链日统计表';

CREATE TABLE `blocked_domain` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '封禁ID',
  `domain` VARCHAR(255) NOT NULL COMMENT '域名',
  `reason` VARCHAR(256) NOT NULL COMMENT '原因',
  `status` ENUM('ACTIVE','CANCELED') NOT NULL COMMENT '状态',
  `created_by` VARCHAR(128) NOT NULL COMMENT '创建人',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_domain` (`domain`),
  KEY `idx_status_created` (`status`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='封禁域名表';
""",
                points=[
                    "short_link 的 code 唯一，保存 long_url、domain、status、expire_at",
                    "id_segment 用 biz_key、max_id、step 和 version 做号段发号",
                    "visit_stat_daily 按 code、date、channel 聚合，不能同步更新",
                    "blocked_domain 用 domain 唯一键做封禁判断",
                    "索引服务于 code 跳转、租户查询、域名封禁和统计排行",
                    "原始访问明细可进日志或对象存储，不放核心表",
                ],
                reference="""short_link 是权威映射表，code 唯一，long_url 是跳转目标，domain 冗余出来是为了快速检查封禁和后台按域名查询；status 和 expire_at 让跳转服务能区分 ACTIVE、EXPIRED、BLOCKED、DELETED。id_segment 是发号器表，biz_key 可以按租户或全局区分号段，max_id 和 step 通过 CAS 更新；创建节点拿到号段后本地生成 id，再编码成短码，避免每次创建都抢数据库自增。visit_stat_daily 是聚合结果表，唯一键 code、stat_date、channel 支持幂等 upsert；但它不是跳转主链路的一部分，PV/UV 由聚合器批量写入，热点 code 可以先在流处理或内存计数里局部聚合，避免同一行高频 update。blocked_domain 保存封禁域名和状态，管理后台封禁时既写表，也发布缓存失效事件。不要把每次访问的 IP、UA、referer 全塞进 visit_stat_daily；原始访问明细如果需要风控或审计，应进入日志流或冷存储，再异步分析。索引上，跳转只需要 uk_code；后台查询用 tenant_id、created_at；域名处置用 domain、status；统计排行用 stat_date、pv。""",
            ),
            dict(
                key="api",
                title="接口设计",
                minutes=4,
                prompt="列出创建短链、批量创建、跳转、封禁、统计查询和内部统计事件，明确幂等和返回码。",
                points=[
                    "创建接口带 long_url、expire_at、自定义 code 和 request_id",
                    "跳转接口 GET /{code} 返回 302 或错误页",
                    "批量创建要逐条返回成功、冲突或非法域名",
                    "封禁接口要失效缓存",
                    "统计事件异步包含 code、time、ip、ua、referer、channel",
                    "防刷接口或中间件按 IP、code、tenant 限流",
                ],
                reference="""创建接口 POST /v1/links，参数包括 tenant_id、long_url、expire_at、custom_code、channel_tags 和 request_id；request_id 用于创建幂等，custom_code 如果已存在要返回 409，而随机 code 冲突可以内部重试几次。批量创建 POST /v1/links:batch 要逐条返回 code、status、error_code，不能因为一条非法 URL 回滚全部。跳转接口是 GET /{code}，命中 ACTIVE 且未过期时返回 302 Location: long_url；默认不使用 301，因为短链可能过期、封禁或调整目标，301 被浏览器缓存后会绕过平台控制。过期可返回 410，封禁返回安全提示页或 451，缺失返回 404。管理接口包括 POST /v1/links/{code}:block、:unblock、PATCH /v1/links/{code} 修改 expire_at 或目标 URL，修改后要发布 CacheInvalidate(code)。统计查询 GET /v1/links/{code}/stats?from=&to=&channel= 读取聚合表。内部 VisitEvent 包含 code、visit_time、ip_hash、user_agent、referer、channel、status_code 和 request_id；跳转服务投递失败时可以采样降级，但不能阻塞跳转。防刷可以作为中间件接口 RateLimitCheck(code, ip, tenant)，超过阈值返回验证码页或 429。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=4,
                prompt="画出短链从创建到激活、过期、封禁、删除和恢复的状态转换。",
                diagram="""stateDiagram-v2
  [*] --> CREATING
  CREATING --> ACTIVE: 写入成功
  CREATING --> CONFLICT: 短码冲突
  ACTIVE --> EXPIRED: 到期
  ACTIVE --> BLOCKED: 风控封禁
  BLOCKED --> ACTIVE: 解封
  EXPIRED --> ACTIVE: 延期
  ACTIVE --> DELETED: 删除
  EXPIRED --> DELETED: 清理
  BLOCKED --> DELETED: 清理
  CONFLICT --> [*]
  DELETED --> [*]""",
                points=[
                    "短链主要状态是 ACTIVE、EXPIRED、BLOCKED、DELETED",
                    "短码冲突发生在创建期，不能覆盖旧 long_url",
                    "过期可以延期恢复，删除一般不可恢复",
                    "封禁优先级高于普通跳转和缓存命中",
                    "状态变更要失效缓存并记录审计",
                ],
                reference="""短链状态机比较简单，但要把冲突和封禁讲清楚。创建时先进入 CREATING，随机码写 short_link 时如果 uk_code 冲突，就重新生成 code；自定义 code 冲突则返回 CONFLICT，绝不能覆盖已有 long_url。写入成功后是 ACTIVE，跳转服务只有在 ACTIVE 且 expire_at 未到、domain 未封禁时才返回 302。到期后进入 EXPIRED，默认返回 410；如果运营延期，可以从 EXPIRED 回到 ACTIVE，但必须删除缓存。风控或管理员可以把 ACTIVE 改成 BLOCKED，BLOCKED 的优先级高于缓存中的旧 ACTIVE 值，所以封禁事件要主动失效缓存，跳转服务也可以在缓存值里带 status_version。解封后可回 ACTIVE。DELETED 用于用户删除或清理，通常不可恢复，短码是否可复用要谨慎；我建议长时间不复用，避免旧链接被别人接管造成安全问题。状态变更用 version 或 updated_at 做 CAS，避免管理员同时修改目标 URL 和封禁状态互相覆盖。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=6,
                prompt="用时序图讲创建、跳转缓存命中、回源、异步统计和封禁缓存失效。",
                diagram="""sequenceDiagram
  participant U as 用户
  participant Api as 创建API
  participant Seg as 发号器
  participant DB as 短链库
  participant R as 跳转服务
  participant C as 缓存
  participant Q as 统计队列
  participant S as 统计聚合器
  U->>Api: 创建长链
  Api->>Seg: 获取号段或随机码
  Api->>DB: 写short_link
  U->>R: GET /code
  R->>C: 查询code
  C-->>R: long_url和状态
  R-->>U: 302跳转
  R->>Q: 异步VisitEvent
  Q->>S: 批量消费
  S->>DB: 更新统计表""",
                points=[
                    "创建路径校验 URL 和封禁域名，再生成 code 写库",
                    "跳转路径先查缓存，未命中回源并回填",
                    "缓存值包含 long_url、status、expire_at 和版本",
                    "返回 302 后异步投递统计事件",
                    "封禁和修改发布缓存失效",
                    "统计聚合批量 upsert，避免热点行同步写",
                ],
                reference="""创建流程是用户提交 long_url，创建 API 先规范化 URL，抽取 domain，检查 blocked_domain 和租户配额；如果是自定义 code，直接尝试写 short_link，冲突返回 409；如果是随机 code，则从发号器拿内部 id 或生成随机码，编码后插入，遇到 uk_code 冲突再重试。跳转流程必须短：用户 GET /code，跳转服务先查本地缓存或分布式缓存，缓存值里有 long_url、status、expire_at、domain 和 version；若 ACTIVE 且未过期，并且 domain 没有在快速封禁缓存里，就立即返回 302。未命中时查 short_link，查不到写短 TTL 的 negative cache，查到后根据状态返回 302、410 或安全提示，并回填缓存。返回用户后，跳转服务异步投递 VisitEvent 到统计队列；即使统计队列短暂不可用，也只能降级采样或写本地缓冲，不能把 P99 跳转拖到 10ms 以上。统计聚合器按 code、date、channel 做批量 upsert。封禁流程是管理员写 blocked_domain 或把 short_link.status 改为 BLOCKED，同时发布 CacheInvalidate；如果失效消息丢了，缓存 TTL 和跳转时的封禁域名快速检查作为兜底。""",
            ),
            dict(
                key="reliability",
                title="可靠性与取舍",
                minutes=5,
                prompt="说明缓存穿透、热点、短码冲突、统计丢失、封禁生效、防刷、扩展和指标。",
                points=[
                    "短码生成靠唯一键和重试处理冲突",
                    "缓存穿透用 negative cache 和布隆过滤器",
                    "热点短码用本地缓存、多级缓存和预热",
                    "统计异步可丢少量但要有缓冲和重放",
                    "封禁靠主动失效、短 TTL 和快速规则检查",
                    "防刷按 IP、code、tenant 和 UA 限流",
                ],
                reference="""可靠性首先是短码冲突，随机码或混淆号段都不能假设永不冲突，必须依赖 short_link.uk_code 和有限重试；自定义 code 冲突直接失败。跳转 P99 < 10ms 的主要风险是缓存未命中、缓存穿透和热点。不存在的 code 用 negative cache 或布隆过滤器挡住，避免恶意遍历把数据库打爆；热门活动短码要预热到本地缓存和分布式缓存，缓存值小而稳定，单机就能承受很高 QPS。统计不能同步写数据库，队列失败时可以本地环形缓冲、采样或降级，并通过队列堆积和丢弃计数告警；如果业务要求精确计费，就需要可靠日志和重放，而不是普通异步队列。封禁的失败模式是旧缓存继续跳转，机制是管理操作发布失效、缓存 TTL 控制在分钟级、跳转服务额外查 blocked_domain 的本地快照；代价是多一次轻量内存判断。防刷按 IP、code、tenant、UA 做令牌桶，对可疑遍历返回 429 或验证码页。扩展上，创建服务按租户分片，跳转服务无状态加机器，short_link 可按 code hash 分库。指标包括 redirect_p99、cache_hit_rate、db_fallback_qps、code_conflict_count、blocked_redirect_count、visit_event_lag、stat_drop_count、rate_limited_count 和 404/410 比例。""",
            ),
        ],
        mistakes=[
            dict(wrong="短码就用数据库自增 ID 做 base62，简单高效。", verdict="方向对但不准", why="发号方向可以，但直接暴露自增 ID 容易被遍历猜测。需要混淆、随机化或加密置换，并仍然用 code 唯一键防冲突。"),
            dict(wrong="每次跳转都 update 一下访问次数，统计最准确。", verdict="最大扣分点", why="热门短码会把同一统计行打成热点，直接破坏 P99 < 10ms。跳转主链路必须异步投递统计事件，再由聚合器批量更新。"),
            dict(wrong="短链永久不变，所以一律返回 301。", verdict="有错", why="短链可能过期、封禁或修改目标，301 被浏览器缓存后会绕过平台控制。默认应返回 302，只有明确永久且无风控变更时才考虑 301。"),
            dict(wrong="缓存里有 long_url 就直接跳，不用再管封禁。", verdict="缺失", why="封禁要求可能晚于缓存写入，旧缓存继续生效会造成安全风险。需要主动失效、短 TTL、缓存版本或跳转前的封禁快照检查。"),
            dict(wrong="随机码空间很大，不用处理冲突。", verdict="有错", why="空间大只表示概率低，不表示不发生；并发创建和自定义短码都可能冲突。必须依赖唯一键和重试，不能覆盖已有映射。"),
        ],
        walkthrough="""以营销活动为例，运营先通过创建 API 创建 3 个短码。创建服务校验长链域名没有被封禁，调用发号器拿号段或生成随机码，写 short_link；code 唯一键保证不会覆盖别人短链。活动开始后，用户访问 /aB7x9Kq，跳转服务先查本地缓存，命中后看到 status=ACTIVE、expire_at 未到，且 domain 不在封禁快照中，立即返回 302 Location 到长链。这个过程不更新数据库统计，只在响应后投递 VisitEvent。10 分钟 50 万次访问集中在 3 个短码时，缓存命中率接近 100%，数据库不会成为瓶颈；统计聚合器从队列批量消费，按 code、date、channel 聚合写 visit_stat_daily。如果活动中目标域名被封禁，管理后台写 blocked_domain 或把 short_link 改成 BLOCKED，并发布缓存失效。后续跳转即使本地还有旧值，也会因为封禁快照或短 TTL 被拦截，返回安全提示页；统计仍记录 blocked_redirect_count 供复盘。""",
        oral="""我会把短链拆成创建路径、跳转路径、统计路径和风控管理。创建路径负责校验长链、域名封禁、租户配额和自定义短码；随机短码可以用号段发号后做混淆编码，也可以用安全随机码，但最终都靠 short_link.code 唯一键处理冲突，自定义冲突返回 409，随机冲突重试。跳转路径是核心，因为读多写少且 P99 要小于 10ms：跳转服务无状态扩展，先查本地或分布式缓存，缓存值包含 long_url、status、expire_at、domain 和 version；ACTIVE 且未过期、未封禁就返回 302。默认不用 301，因为短链可能被封禁、过期或修改，301 会被客户端缓存。统计路径不能同步 update 数据库，跳转服务响应后投递 VisitEvent，聚合器按 code、日期、渠道批量写 visit_stat_daily，热点短码先局部聚合再入库。风控上，blocked_domain 和短码状态是权威，封禁时主动失效缓存，缓存 TTL 和本地封禁快照兜底；防刷按 IP、code、tenant、UA 做限流，并用 negative cache 或布隆过滤器挡恶意遍历。回到例子，50 万次跳转集中在 3 个短码，缓存预热后绝大多数请求不碰数据库，只异步写统计队列，因此能守住低延迟；如果域名被封禁，缓存失效和封禁快照会让后续请求进入安全页。""",
        followups=[
            dict(q="为什么默认 302，不用 301？", a="301 会被浏览器和搜索引擎长期缓存，后续平台即使封禁、过期或修改目标 URL，用户也可能绕过短链服务直达旧目标。短链通常需要运营控制和风控兜底，所以默认 302；只有确定永久映射且可接受缓存风险时才用 301。"),
            dict(q="如何让短码不可预测？", a="不要直接 base62 自增 ID。可以用号段生成内部 ID 后经过带密钥的置换或打乱，也可以直接生成安全随机码；无论哪种，都用 code 唯一键兜底冲突。不可预测的目标是让攻击者不能顺序枚举有效短码。"),
            dict(q="缓存穿透怎么防？", a="不存在的 code 如果每次都查库，会被遍历攻击打爆数据库。可以用布隆过滤器判断可能存在，再给 404 写短 TTL negative cache；同时按 IP 和 code 前缀限流。这样不存在请求大多在缓存层结束。"),
            dict(q="统计要求非常准确怎么办？", a="如果统计用于计费，不能接受普通异步队列丢失，就要把 VisitEvent 写入可靠日志，使用至少一次消费和聚合幂等键重放；跳转主链路仍不应该同步更新统计表，否则热点短码会破坏延迟目标。"),
            dict(q="封禁后旧缓存还在怎么办？", a="封禁操作要写 blocked_domain 或 short_link.status，并发布缓存失效；跳转服务还应维护本地封禁域名快照，在返回前做内存检查。即使失效消息丢失，短 TTL 和快照也能把旧缓存风险限制在很短时间。"),
            dict(q="热门短码单码峰值继续涨怎么办？", a="先保证缓存命中路径不访问数据库，然后做本地缓存、边缘缓存或 CDN 缓存 302 响应；统计事件按本地批量聚合后再发送。需要注意封禁和过期时必须能快速失效边缘缓存，否则低延迟会牺牲安全控制。"),
        ],
        variants=[
            "二维码跳转与访问统计服务",
            "活动落地页跳转网关",
            "邀请码生成与兑换查询服务",
        ],
    ),
]
