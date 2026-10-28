BLOCKS = []
DESIGNS = []
EXTRAS = {}
TOOLBOX = {}

SYSTEMS = [
    dict(
        id="x1",
        order=1,
        priority=True,
        title="数据开发平台的 DAG 调度系统",
        brief="设计一个按时间和上游依赖自动生成、低延迟调度、可重跑补数的 DAG 任务调度系统。",
        statement="""你要设计一个面向多用户的数据开发平台调度系统。用户可以创建任务，填写名称、负责人、租户、调度周期 cron、依赖的上游任务、重试次数、重试间隔、超时时间、队列、优先级和告警规则；任务上线后，平台要按业务时间自动生成运行实例，并在计划时间和上游依赖都满足后尽快调度执行。系统还要支持手动重跑、补数据，补数据可以回溯一段业务时间并限制最大并行度；支持失败重试、kill、人工强制成功、跳过、超时终止和告警。非功能要求是：上游完成到下游启动的调度延迟尽可能低，常规链路希望秒级以内，关键链路要接近一次事件处理耗时；调度控制面可用性 99.9%，不能因为单个执行节点慢或挂掉影响全局；多租户之间要有公平配额，低优先级补数不能挤占线上周期任务；实例生成和状态推进要幂等，任务改版不能影响已经生成的历史实例。面试时请给出服务拆分、核心表、接口、状态机、主流程和可靠性方案。""",
        focus="""这道题的题眼不是“能跑任务”，而是“上游完成到下游启动的延迟尽可能低”。因此设计必须避免扫库轮询上游状态，改成时间延迟队列加依赖事件驱动：计划时间到、上游完成这两个入口统一检查 ready 条件，谁后到谁触发。另一个核心约束是实例必须绑定任务版本，并用任务层依赖边加业务时间映射计算父实例键，不能把某次运行的上游 instance_id 固化进下游实例。""",
        scale="""规模假设：有 2 万个租户任务、每天生成 300 万个周期实例，峰值 20 万实例在 10 分钟窗口内到点；单实例状态事件平均 8 条，日事件 2400 万条；单任务最多 2000 个直接下游，DAG 最大深度 50；常规调度延迟 P95 小于 2 秒，关键队列 P95 小于 300 毫秒；实例状态保留 180 天，热表保留 30 天，历史归档到对象存储。""",
        example="""例子：任务 c 的计划运行时间是 0:50，实际跑 8 分钟，0:58 成功；任务 a 的计划运行时间是 1:00，依赖 b 和 c；任务 b 的计划运行时间是 1:10，实际跑 15 分钟，1:25 成功。请回答 a 到底什么时候启动，以及系统怎样在不轮询数据库的情况下做到。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清语义和边界",
                minutes=3,
                prompt="先问清任务、实例、业务时间、计划时间、依赖映射、重跑补数和成功语义，不要直接画一个大队列。",
                points=[
                    "区分任务定义、任务版本和运行实例",
                    "区分业务时间 task_time 与计划运行时间 scheduled_at",
                    "确认依赖是任务层 DAG，运行时按业务时间映射父实例",
                    "确认重跑、补数据、手动触发和周期触发是否共享状态机",
                    "确认延迟目标、可用性、租户配额和优先级",
                    "确认 kill、超时、强制成功、跳过等人工操作语义",
                    "确认任务改版后历史实例是否固定旧版本",
                ],
                reference="""我会先把三个概念拆开：task 是用户维护的任务定义，task_version 是一次发布快照，instance 是某个 task 在某个业务时间 task_time 的运行实例。scheduled_at 是计划可以启动的墙钟时间，task_time 是处理哪一段数据，两者不能混用；比如小时任务 1:00 启动，处理的可能是 0:00 到 1:00 的数据。依赖也要问清楚是不是任务层依赖，而不是实例层依赖：边上要有父子周期映射，例如小时任务依赖当天日任务，或者依赖自己上一小时。重跑和补数据最好复用同一张实例表和同一套状态机，只是 trigger_type 不同，补数据再加最大并行度和范围。成功语义要问到人工强制成功是否放行下游、上游失败时下游是否继续等待、kill 是否触发重试。最后确认低延迟指标、租户公平性和关键队列优先级，因为这些约束会直接决定不能扫库轮询、不能让 worker 抢未来任务等待、需要事件持久化和配额准入。""",
            ),
            dict(
                key="estimate",
                title="规模估算",
                minutes=4,
                prompt="用题目数字算 QPS、峰值、存储和分片，说明数字如何改变架构选择。",
                points=[
                    "按日实例数和峰值窗口估算生成与调度 QPS",
                    "按状态事件数估算事件写入量和补偿扫描量",
                    "估算实例表热数据、索引和归档策略",
                    "估算下游 fan-out 对事件风暴的压力",
                    "给出 scheduler 分片数和队列隔离依据",
                    "说明为什么这些数字排除扫库轮询方案",
                ],
                reference="""按每天 300 万实例算，平均生成和状态推进只有几十 QPS，但峰值才是设计依据：20 万实例集中在 10 分钟到点，等价于 333 个实例每秒进入 ready 检查；如果每个实例平均 8 条状态事件，峰值状态写入可能到 2000 到 3000 QPS。单个上游最多 2000 个直接下游，成功瞬间会形成 fan-out 事件风暴，所以不能让每个下游都做重型扫库，应该先按依赖边批量取 child_task，再把事件分片投递给归属 scheduler。存储上，300 万实例每天、180 天是 5.4 亿行，如果算补数和重跑放大到 10 亿行级别，热表只保留 30 天约 9000 万行，按租户或项目分表，并把老实例和状态事件归档到对象存储。调度分片可以先按 64 或 128 个 scheduler_id 虚拟分片，每个 scheduler 副本认领若干分片，实例行也写入 scheduler_id 索引。这个规模下每秒扫一遍 WAITING_DEPENDENCY 不现实：哪怕只有 100 万等待实例，每轮查多条上游也会把数据库压垮，并且轮询间隔天然决定延迟下限。因此设计选择是时间用内存延迟队列，依赖用事件触发，数据库只做权威状态和恢复来源。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出 API、控制面、scheduler、worker、monitor、alarm、存储和消息的职责边界，特别说明 worker 不能等时间和判依赖。",
                diagram="""flowchart LR
U["用户"] --> A["API服务"]
A --> D["元数据库"]
A --> M["控制面Leader"]
M --> D
M --> Q["事件队列"]
D --> S["Scheduler集群"]
Q --> S
S --> K["热KV"]
S --> W["Worker池"]
W --> E["执行引擎"]
W --> Q
N["Monitor巡检"] --> D
N --> Q
Q --> L["Alarm告警"]
S --> D
""",
                points=[
                    "API 负责任务编辑、发布、环检测和版本号",
                    "控制面 Leader 负责提前生成实例和维护任务依赖图",
                    "scheduler 无状态多副本，按 scheduler_id 分片处理实例",
                    "worker 只执行已派发任务，不等到点、不判依赖",
                    "monitor 做补偿巡检和超时推进，alarm 消费状态事件",
                    "比较 scheduler 推送与 worker 拉取已就绪作业的取舍",
                    "说明队列、配额和热 KV 的使用边界",
                ],
                reference="""服务边界要按“控制、调度、执行”拆开。API 服务是无状态入口，负责任务增删改、发布上线、版本号递增、参数校验和 DAG 环检测；发布成功写 task_version，后续实例绑定这个版本。控制面 master 用选主保证同一时刻只有一个 Leader 生成未来实例，通常提前 1 小时把下一周期实例写入 instance，靠 (task_id, task_time) 唯一键防重复；它还把任务依赖图加载到内存，维护队列、租户配额和 scheduler 分片分配。scheduler 是无状态多副本，按实例上的 scheduler_id 或虚拟分片认领任务；未到点实例进入本地内存延迟队列精确唤醒，到点后检查依赖和配额，依赖事件也进入同一个 ready 检查函数。worker 是纯执行资源，只接收已经 ready 的派发，提交到执行引擎并回传 SUBMITTED、RUNNING、SUCCEEDED、FAILED 等状态，绝不提前拉取未来实例后占着 slot 等时间，也不判断上游依赖。monitor 周期巡检卡住的状态、超时实例、丢失的下游触发事件，并把补偿事件写回队列；alarm 消费最终失败、超时、人工 kill 等状态事件发告警。派发方式有两种：scheduler 推给 worker 延迟最低，适合关键链路，但 scheduler 要感知 worker 容量；worker 按 slot 拉取“已就绪队列”解耦更好，适合大量普通任务。两者都必须只处理已就绪作业，不能让 worker 拉未来实例等待，否则执行槽被空占，低延迟和公平性都会被破坏。""",
            ),
            dict(
                key="tables",
                title="核心表设计",
                minutes=8,
                prompt="写出任务、依赖、版本、实例、触发、事件、队列配额表，并解释唯一键、索引和哪些字段不该存。",
                ddl="""
CREATE TABLE `task` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `name` VARCHAR(128) NOT NULL COMMENT '任务名称',
  `owner` VARCHAR(128) NOT NULL COMMENT '负责人',
  `cron_expr` VARCHAR(128) NOT NULL COMMENT '调度周期表达式',
  `queue_name` VARCHAR(64) NOT NULL COMMENT '队列名称',
  `priority` INT NOT NULL DEFAULT 5 COMMENT '优先级，数字越小越高',
  `retry_num` INT NOT NULL DEFAULT 0 COMMENT '最大重试次数',
  `retry_interval_sec` INT NOT NULL DEFAULT 60 COMMENT '基础重试间隔秒',
  `timeout_sec` INT NOT NULL DEFAULT 3600 COMMENT '超时秒数',
  `status` ENUM('DRAFT','ONLINE','OFFLINE') NOT NULL DEFAULT 'DRAFT' COMMENT '任务状态',
  `current_version` INT NOT NULL DEFAULT 0 COMMENT '当前发布版本',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`, `name`),
  KEY `idx_status_cron` (`status`, `cron_expr`),
  KEY `idx_queue_priority` (`queue_name`, `priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务定义表';

CREATE TABLE `task_dependency` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '依赖边ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `parent_task_id` BIGINT UNSIGNED NOT NULL COMMENT '上游任务ID',
  `child_task_id` BIGINT UNSIGNED NOT NULL COMMENT '下游任务ID',
  `parent_time_offset_min` INT NOT NULL DEFAULT 0 COMMENT '按子实例业务时间计算父业务时间的偏移分钟',
  `mapping_type` ENUM('SAME','PREV','HOURLY_TO_DAILY','CUSTOM') NOT NULL DEFAULT 'SAME' COMMENT '周期映射类型',
  `mapping_conf` JSON NOT NULL COMMENT '依赖映射配置',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_parent_child` (`parent_task_id`, `child_task_id`, `mapping_type`),
  KEY `idx_child` (`child_task_id`),
  KEY `idx_parent` (`parent_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务层依赖边表';

CREATE TABLE `task_version` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '版本行ID',
  `task_id` BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  `version` INT NOT NULL COMMENT '版本号',
  `snapshot` JSON NOT NULL COMMENT '任务发布快照',
  `published_by` VARCHAR(128) NOT NULL COMMENT '发布人',
  `published_at` DATETIME(3) NOT NULL COMMENT '发布时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_version` (`task_id`, `version`),
  KEY `idx_published_at` (`published_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务版本历史表';

CREATE TABLE `instance_trigger` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '触发ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `trigger_type` ENUM('SYSTEM','MANUAL','RERUN','BACKFILL') NOT NULL COMMENT '触发类型',
  `task_id` BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  `range_start_time` DATETIME(3) NOT NULL COMMENT '补数或触发范围开始业务时间',
  `range_end_time` DATETIME(3) NOT NULL COMMENT '补数或触发范围结束业务时间',
  `max_parallelism` INT NOT NULL DEFAULT 1 COMMENT '最大并行实例数',
  `created_by` VARCHAR(128) NOT NULL COMMENT '触发人',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_created` (`task_id`, `created_at`),
  KEY `idx_type_tenant` (`trigger_type`, `tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实例触发来源表';

CREATE TABLE `instance` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '实例ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `task_id` BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  `task_version` INT NOT NULL COMMENT '实例绑定的任务版本',
  `task_time` DATETIME(3) NOT NULL COMMENT '业务时间',
  `scheduled_at` DATETIME(3) NOT NULL COMMENT '计划运行时间',
  `attempt` INT NOT NULL DEFAULT 0 COMMENT '当前尝试次数',
  `status` ENUM('INIT','WAITING_TIME','WAITING_DEPENDENCY','WAITING_RESOURCE','SUBMITTED','RUNNING','SUCCEEDED','DOWNSTREAM_TRIGGERED','FAILED','FAILED_FINAL','CANCELED','KILLED','SKIPPED','FORCE_SUCCEEDED') NOT NULL COMMENT '实例状态',
  `generation` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '状态版本号，用于CAS',
  `scheduler_id` INT NOT NULL COMMENT '调度分片ID',
  `worker_id` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '执行节点ID',
  `trigger_id` BIGINT UNSIGNED NOT NULL COMMENT '触发来源ID',
  `ready_at` DATETIME(3) NULL COMMENT '满足时间和依赖的时间',
  `submitted_at` DATETIME(3) NULL COMMENT '提交时间',
  `started_at` DATETIME(3) NULL COMMENT '开始运行时间',
  `ended_at` DATETIME(3) NULL COMMENT '结束时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_time` (`task_id`, `task_time`),
  KEY `idx_scheduler_status_time` (`scheduler_id`, `status`, `scheduled_at`),
  KEY `idx_status_updated` (`status`, `updated_at`),
  KEY `idx_trigger` (`trigger_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运行实例表';

CREATE TABLE `scheduler_event` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '事件ID',
  `event_type` ENUM('CHECK_UPSTREAM','TRIGGER_DOWNSTREAM','RETRY','RECOVER') NOT NULL COMMENT '事件类型',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `task_id` BIGINT UNSIGNED NOT NULL COMMENT '相关任务ID',
  `task_time` DATETIME(3) NOT NULL COMMENT '相关业务时间',
  `instance_id` BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '相关实例ID，没有则为0',
  `priority` INT NOT NULL DEFAULT 5 COMMENT '事件优先级',
  `status` ENUM('NEW','PROCESSING','DONE','FAILED') NOT NULL DEFAULT 'NEW' COMMENT '事件处理状态',
  `next_fire_at` DATETIME(3) NOT NULL COMMENT '下次可处理时间',
  `payload` JSON NOT NULL COMMENT '事件载荷',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_status_fire_priority` (`status`, `next_fire_at`, `priority`),
  KEY `idx_task_time` (`task_id`, `task_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='可靠调度事件表';

CREATE TABLE `queue_quota` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '配额ID',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户ID',
  `queue_name` VARCHAR(64) NOT NULL COMMENT '队列名称',
  `max_running` INT NOT NULL COMMENT '最大运行实例数',
  `max_submitting` INT NOT NULL COMMENT '最大提交中实例数',
  `weight` INT NOT NULL DEFAULT 1 COMMENT '公平调度权重',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_queue` (`tenant_id`, `queue_name`),
  KEY `idx_queue` (`queue_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='队列配额表';
""",
                points=[
                    "task 保存当前定义、版本号、队列、优先级、重试和超时",
                    "task_dependency 只存任务层边和业务时间映射，两边都建索引",
                    "task_version 保存发布快照，实例绑定版本",
                    "instance 用 (task_id, task_time) 做幂等键并保存状态时间点",
                    "instance 不存上游 instance_id，运行时按依赖边计算父业务键",
                    "event 表用于可靠补偿，处理完成可删除或归档",
                    "queue_quota 支持租户和队列公平准入",
                ],
                reference="""表设计的关键是把定义、版本、实例和事件拆开。task 存当前任务定义，包括 version、cron、priority、queue、retry_num、retry_interval、timeout、owner、tenant 和 status；这些字段影响调度准入和失败处理，不能散落在配置文本里。task_dependency 是任务层依赖边，parent_task_id 和 child_task_id 两边都要索引，因为上游成功要按 parent 找下游，检查某个实例是否 ready 要按 child 找所有上游。边上要存 offset 或周期映射，运行时用“子实例 task_time + 映射”算出父实例业务键 (parent_task_id, parent_task_time)，再查父实例状态。instance 表故意不存上游 instance_id，因为父实例可能尚未生成，跨周期依赖和自依赖需要动态计算，重跑也不能让旧 id 把依赖绑死。task_version 保存每次发布快照，instance 绑定 task_version，用户改 cron 或重试策略不会影响历史实例。instance 的 (task_id, task_time) 唯一键是系统周期生成、手动重跑幂等和补数据去重的核心；generation 是 CAS 版本号，保证两个 scheduler 或两个上游事件同时触发时只有一个状态推进成功。scheduler_event 可以是表或可靠消息的落地形态，保存 CHECK_UPSTREAM、TRIGGER_DOWNSTREAM、RETRY、RECOVER 等事件，处理完删除或归档，用于丢消息补偿。queue_quota 保存租户队列并发和权重。不要把执行日志大文本、任务产物、完整上游列表快照放进 instance 热表，产物放对象存储或执行引擎，长日志按 instance_id 单独归档，否则热索引会被拖慢。""",
            ),
            dict(
                key="api",
                title="接口和事件",
                minutes=5,
                prompt="列出对外任务/实例接口、内部调度 RPC 和事件，说明参数、幂等键和返回语义。",
                points=[
                    "任务创建、发布、依赖校验和环检测接口",
                    "实例查询、重跑、补数据、kill、强制成功接口",
                    "scheduler 到 worker 的派发或 worker 拉取已就绪接口",
                    "worker 回传状态要带 generation 或 attempt",
                    "事件类型和幂等键要能去重",
                    "补数据接口要带范围和最大并行度",
                ],
                reference="""对外接口分任务和实例两类。任务侧可以是 POST /tasks 创建草稿，PUT /tasks/{id} 修改配置，POST /tasks/{id}/publish 发布版本；发布时参数包含 expected_version，服务端先做 cron 校验、依赖存在性校验和 DAG 环检测，成功后 current_version 加一并写 task_version。依赖接口 POST /tasks/{id}/dependencies 接收 parent_task_id、mapping_type、offset 和 mapping_conf，返回受影响的下游范围。实例侧 GET /instances 支持按 task_id、task_time、status、trigger_id 查询；POST /instances/{id}/rerun 使用 idempotency_key 和 from_attempt，生成同一业务键的新 attempt 或重置到 INIT；POST /backfills 接收 task_id、start_task_time、end_task_time、max_parallelism、priority，返回 trigger_id 和将要生成的实例数；POST /instances/{id}/kill 带 expected_generation，只有 SUBMITTED/RUNNING 可转 KILLED；POST /instances/{id}/force_success 带原因和 expected_generation，转 FORCE_SUCCEEDED 后允许触发下游。内部接口可以是 Dispatch(instance_id, generation, queue, priority, attempt) 从 scheduler 到 worker，worker 返回 accepted_worker_id；或者 worker 调 PullReady(queue, capacity) 拉取已就绪作业，但队列里只能放 WAITING_RESOURCE 之后的实例。worker 状态回传 ReportStatus(instance_id, attempt, from_status, to_status, worker_id, started_at, ended_at, error_code) 必须带 attempt 和 generation，防止旧 worker 覆盖新状态。事件包括 CHECK_UPSTREAM、TRIGGER_DOWNSTREAM、RETRY、RECOVER，幂等键可以用 event_type + instance_id + attempt 或 parent_task_id + parent_task_time + child_task_id，重复投递只会触发一次 CAS 成功。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="画出实例状态机，说明等待时间、等待依赖、等待资源为什么要拆开，以及并发下如何只提交一次。",
                diagram="""stateDiagram-v2
[*] --> INIT
INIT --> WAITING_TIME: 未到点
INIT --> WAITING_DEPENDENCY: 到点缺上游
INIT --> WAITING_RESOURCE: ready
WAITING_TIME --> WAITING_DEPENDENCY: 到点缺上游
WAITING_TIME --> WAITING_RESOURCE: 到点且上游齐
WAITING_DEPENDENCY --> WAITING_RESOURCE: 上游齐
WAITING_RESOURCE --> SUBMITTED: 派发
SUBMITTED --> RUNNING: 开始
RUNNING --> SUCCEEDED: 成功
SUCCEEDED --> DOWNSTREAM_TRIGGERED: 触发下游
SUBMITTED --> FAILED: 提交失败
RUNNING --> FAILED: 执行失败
FAILED --> WAITING_RESOURCE: 退避重试
FAILED --> FAILED_FINAL: 超过次数
WAITING_RESOURCE --> CANCELED: 取消
SUBMITTED --> KILLED: kill
RUNNING --> KILLED: kill
WAITING_DEPENDENCY --> SKIPPED: 跳过
WAITING_DEPENDENCY --> FORCE_SUCCEEDED: 强制成功
FORCE_SUCCEEDED --> DOWNSTREAM_TRIGGERED: 放行
DOWNSTREAM_TRIGGERED --> [*]
FAILED_FINAL --> [*]
CANCELED --> [*]
KILLED --> [*]
SKIPPED --> [*]
""",
                points=[
                    "INIT 后按时间和依赖拆成不同等待状态",
                    "WAITING_RESOURCE 才能参与配额和派发",
                    "FAILED 按 retry_interval 指数退避，超过 retry_num 进 FAILED_FINAL",
                    "SUCCEEDED 与 DOWNSTREAM_TRIGGERED 分开，便于丢事件补偿",
                    "CANCELED、KILLED、SKIPPED、FORCE_SUCCEEDED 语义不同",
                    "所有转换用 generation CAS 和兼容前置状态",
                    "并发事件采用更靠后的状态优先",
                ],
                reference="""状态机不能只有 pending、running、success、failed 四个词，因为调度问题的失败模式恰好藏在 pending 里。INIT 表示实例刚生成；如果未到 scheduled_at 进入 WAITING_TIME，如果已到点但父实例未齐进入 WAITING_DEPENDENCY，如果时间和依赖都满足进入 WAITING_RESOURCE。WAITING_RESOURCE 表示可以竞争配额和执行资源，还没有真正提交，只有这个状态能派发给 worker。SUBMITTED 表示已经交给 worker 或执行引擎，RUNNING 表示引擎确认开始。SUCCEEDED 只是本实例成功，DOWNSTREAM_TRIGGERED 表示下游触发事件已经至少写入一次，把两者拆开是为了补偿：如果成功后进程崩溃，monitor 看到 SUCCEEDED 但不是 DOWNSTREAM_TRIGGERED，就知道还要补发下游事件。FAILED 是可重试失败，按照 retry_interval × 2^(n-1) 做指数退避并设置上限，退避结束后回 WAITING_RESOURCE 或重新检查依赖；超过 retry_num 才是 FAILED_FINAL。CANCELED 是未执行前取消，KILLED 是运行中终止，SKIPPED 是人工跳过且通常不触发下游，FORCE_SUCCEEDED 是人工认定成功并可放行下游。并发控制靠 generation CAS：update instance set status=?, generation=generation+1 where id=? and generation=? and status in (...)。两个上游同时完成时都会触发子实例检查，但只有一个能把 WAITING_DEPENDENCY 改成 WAITING_RESOURCE；如果一个旧 worker 回报 FAILED，而实例已经重跑成功，状态机按 attempt 和“更靠后的状态优先”拒绝旧写入。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="用时序图讲实例生成、时间到、上游成功触发下游、配额派发和关键分支。",
                diagram="""sequenceDiagram
participant M as 控制面Leader
participant DB as 元数据库
participant S as Scheduler
participant Q as 事件队列
participant W as Worker
participant E as 执行引擎
participant N as Monitor
M->>DB: 生成下一小时实例
DB-->>S: 恢复分片实例
S->>S: 放入内存延迟队列
S->>DB: 时间到后CAS检查状态
S->>DB: 查询父实例业务键状态
S->>DB: 配额准入并改WAITING_RESOURCE
S->>W: Dispatch实例
W->>E: 提交执行
W->>Q: 回传状态事件
Q->>S: TRIGGER_DOWNSTREAM
S->>DB: 查下游边并检查依赖
S->>W: 下游ready后派发
N->>DB: 巡检超时和卡住状态
N->>Q: 写RECOVER事件
""",
                points=[
                    "Leader 提前生成实例，唯一键兜底重复生成",
                    "scheduler 重启后从 DB 恢复自己分片的延迟队列",
                    "时间到和上游成功进入同一个 ready 检查函数",
                    "ready_time = max(计划时间, 所有上游完成时间)",
                    "派发前检查配额、队列和优先级",
                    "上游失败时下游保持等待，人工强制成功才放行",
                    "monitor 只补偿，不代替主链路轮询",
                ],
                reference="""正常主链路先由控制面 Leader 周期性生成实例。Leader 根据上线任务的 cron 计算下一小时需要的 task_time 和 scheduled_at，插入 instance；如果 Leader 切换或重复执行，(task_id, task_time) 唯一键让生成幂等。scheduler 认领自己的 scheduler_id 分片，启动时从数据库加载 INIT、WAITING_TIME、WAITING_DEPENDENCY、WAITING_RESOURCE 等在途实例；未到点的放入本地内存延迟队列，到点后调用统一的 check_ready。check_ready 先看 scheduled_at 是否已到，再按 task_dependency 的 child_task_id 找全部父任务，用子实例 task_time 加 offset 或周期映射算出父实例业务键，查热 KV 或数据库确认父实例是 SUCCEEDED、DOWNSTREAM_TRIGGERED 或 FORCE_SUCCEEDED；如果还有父实例缺失或失败，就保持 WAITING_DEPENDENCY，不做循环等待。如果上游成功事件到达，scheduler 按 parent_task_id 找下游边，定位子实例后也调用同一个 check_ready。这样“时间到”和“上游齐”两个入口合并，谁后到谁触发；ready_time 等于计划时间和所有上游完成时间的最大值。ready 后先查 queue_quota 和租户并发，按优先级队列派发给 worker。关键分支包括：上游 FAILED_FINAL 时下游继续 WAITING_DEPENDENCY 并告警，不自动失败，人工 force success 才放行；worker 提交后超时由 monitor 转 FAILED 或 KILLED；事件丢失时 monitor 扫描 SUCCEEDED 但未 DOWNSTREAM_TRIGGERED 的实例补写 TRIGGER_DOWNSTREAM。monitor 是兜底，不是主调度循环，因此巡检周期可以是分钟级，不影响低延迟主链路。""",
            ),
            dict(
                key="reliability",
                title="可靠性和扩展",
                minutes=5,
                prompt="说明选主、幂等、重试退避、补偿、限流隔离、扩展、监控指标和数据归档。",
                points=[
                    "Leader 选主和唯一键保证实例生成一次",
                    "事件持久化加补偿 loader 保证下游至少触发一次",
                    "scheduler 重启按分片从 DB 恢复在途实例",
                    "状态转换和派发用 generation CAS 防重复提交",
                    "重试退避、超时、kill 和人工操作有明确语义",
                    "补数据按最大并行度分批并与周期任务隔离",
                    "实例表分表、冷热归档和监控指标",
                ],
                reference="""可靠性要按失败模式逐个闭环。控制面可能挂，所以 master 通过租约选主，只有 Leader 生成实例；重复生成用 (task_id, task_time) 唯一键兜底。scheduler 可能挂，所以它本身尽量无状态，内存延迟队列只是加速结构，重启时按 scheduler_id 从数据库恢复 WAITING_TIME、WAITING_DEPENDENCY、WAITING_RESOURCE、SUBMITTED 等在途实例；如果分片迁移，新 scheduler 先获得分片租约再恢复。事件可能丢，所以状态事件写可靠队列或 scheduler_event 表，成功实例和 DOWNSTREAM_TRIGGERED 分离，monitor 或补偿 loader 定期找 SUCCEEDED 但未触发下游、FAILED 到退避时间、SUBMITTED 长时间无心跳的实例，写 RECOVER 事件。重复事件不可避免，所以所有状态推进都用 generation CAS、attempt 校验和幂等键；派发前从 WAITING_RESOURCE CAS 到 SUBMITTED，失败才允许其他 scheduler 重试。失败重试用指数退避加上限和抖动，确定性配置错误不要无限重试；超时由 monitor 转 FAILED 或 KILLED。补数据一万个实例时，trigger 表记录范围和 max_parallelism，scheduler 只释放窗口内实例，并把 BACKFILL 队列与周期队列隔离，避免补数打爆线上任务。扩展上，实例表按租户或项目分片，热数据保留 30 天，冷数据归档；热 KV 缓存父实例成功状态，降低依赖检查读压。监控指标包括上游成功到下游 ready 的延迟、ready 到 submitted 的资源等待、事件积压、CAS 冲突、重复派发拦截、分片恢复耗时、队列配额命中、补偿事件数量和每租户失败率。""",
            ),
        ],
        mistakes=[
            dict(
                wrong="我每隔一分钟扫一次所有等待中的实例，查它们上游是否成功，成功就提交。",
                verdict="最大扣分点",
                why="轮询上游状态和低延迟题眼直接冲突，轮询间隔就是延迟下限；等待实例多时还会把数据库打爆。正确做法是时间用延迟队列，依赖用上游成功事件触发，巡检只做兜底补偿。",
            ),
            dict(
                wrong="worker 从数据库拉取未来一小时的实例，自己睡到 scheduled_at，再检查依赖并执行。",
                verdict="搞反",
                why="worker 是执行资源，不该等待时间或判断依赖。提前拉未来实例会白占执行槽，也会把调度策略散到每个 worker。应该由 scheduler 判断 ready，再推送或让 worker 拉取已就绪作业。",
            ),
            dict(
                wrong="实例状态就 pending、running、success、failed 四个，pending 里自己判断原因。",
                verdict="方向对但不准",
                why="pending 过粗会看不出是在等时间、等上游还是等资源，补偿和告警都无法精确。应拆成 WAITING_TIME、WAITING_DEPENDENCY、WAITING_RESOURCE，并记录 ready、submit、start、end 时间。",
            ),
            dict(
                wrong="生成 a 实例时把 b、c 的 instance_id 存到 a 的 upstream_instance_ids 字段里。",
                verdict="有错",
                why="实例层固化上游 id 会被跨周期依赖、上游尚未生成、自依赖和重跑换 attempt 击穿。依赖应只在任务层存边，运行时用子 task_time 和边上的映射计算父实例业务键。",
            ),
            dict(
                wrong="API、scheduler、worker 谁发现下一周期没实例都可以直接插入，重复了再人工清理。",
                verdict="有错",
                why="实例生成必须有单一控制面和幂等键，否则 Leader 切换或并发补数会产生重复实例。正确做法是 Leader 提前生成，(task_id, task_time) 唯一键兜底，触发记录标明来源。",
            ),
            dict(
                wrong="任务表只存名称、cron 和脚本路径，重试、优先级、超时上线后再从配置中心读。",
                verdict="方向对但不准",
                why="调度决策依赖 retry、priority、queue、timeout 和 version，这些字段必须成为任务版本快照的一部分。否则历史实例重跑会读到新配置，优先级和超时也无法稳定复现。",
            ),
            dict(
                wrong="上游失败后下游也直接失败，等用户重跑整条链路。",
                verdict="缺失",
                why="上游失败不一定意味着下游最终失败，因为可能人工修复后强制成功或单独重跑上游。下游应保持 WAITING_DEPENDENCY 并告警，只有依赖满足、跳过或强制成功后才继续。",
            ),
        ],
        walkthrough="""按例子走一遍。控制面提前生成 c(0:50)、a(1:00)、b(1:10) 三个业务实例，并按 task_id 与 task_time 写唯一键。c 到 0:50 后 scheduler 从延迟队列唤醒，发现没有未满足依赖，查配额后派发给 worker；0:58 worker 回报 c 成功，scheduler 持久化 SUCCEEDED，并写 TRIGGER_DOWNSTREAM。事件处理时按 c 的下游边找到 a，但 a 的 scheduled_at 是 1:00，此时 check_ready 发现未到点，因此 a 仍在 WAITING_TIME 或保持未 ready，只记录 c 已成功的热 KV，不扫库等待。1:00 a 的延迟队列触发，scheduler 检查父实例：c 的父业务键已成功，b 对应的业务实例还没有成功，因为 b 计划 1:10 才跑，所以 a 转为 WAITING_DEPENDENCY 并挂起，不启动轮询。1:10 b 到点后运行，1:25 成功并写 TRIGGER_DOWNSTREAM。scheduler 收到 b 成功事件，再次定位 a，按依赖边计算 b、c 两个父实例业务键并检查状态，发现都已成功；此时 ready_time = max(a 的计划时间 1:00, c 完成 0:58, b 完成 1:25) = 1:25。a 经过队列配额准入后立即从 WAITING_DEPENDENCY CAS 到 WAITING_RESOURCE，再到 SUBMITTED，派发给 worker。所以上游 b 完成到 a 启动的调度延迟只有一次事件投递、依赖检查和派发的毫秒到秒级耗时，而不是轮询周期。""",
        oral="""我会把这个系统拆成控制面、调度面和执行面。API 服务负责任务编辑和发布，发布时做参数校验、DAG 环检测并生成 task_version；master 通过选主成为单 Leader，提前约一小时按 cron 生成实例，用 (task_id, task_time) 唯一键保证幂等，同时维护任务依赖图、队列和配额。scheduler 是无状态多副本，按 scheduler_id 分片认领实例；未到点实例进入内存延迟队列，到点后调用 check_ready；上游成功会投 TRIGGER_DOWNSTREAM 事件，scheduler 找到下游实例后也调用同一个 check_ready。这样时间到和依赖齐两个入口合并，ready_time 等于计划时间和所有上游完成时间的最大值，谁后到谁触发。worker 只接收已就绪实例并提交到执行引擎，回传状态，不等时间、不判依赖。数据模型上，task 存当前配置，task_version 存发布快照，task_dependency 只存任务层边和周期映射，instance 绑定 task_version，并用 generation 做 CAS。注意 instance 不存上游 instance_id，运行时用子 task_time 加依赖边 offset 算父实例业务键，这样能处理父实例尚未生成、小时依赖天、自依赖和重跑。状态机从 INIT 拆到 WAITING_TIME、WAITING_DEPENDENCY、WAITING_RESOURCE、SUBMITTED、RUNNING、SUCCEEDED、DOWNSTREAM_TRIGGERED，失败按 retry_interval 指数退避，超过 retry_num 进 FAILED_FINAL；SUCCEEDED 和 DOWNSTREAM_TRIGGERED 分开，是为了成功后丢触发事件时能补偿。可靠性上，Leader 选主加唯一键防重复生成，事件表或可靠队列保证下游至少触发一次，monitor 巡检卡住状态和超时，scheduler 重启按分片从数据库恢复在途实例；所有状态推进带 generation 和 attempt，重复事件只会有一个 CAS 成功。回到例子，c 0:58 成功会触发 a 检查，但 a 未到 1:00 不启动；1:00 a 到点发现 b 未成功，进入等待依赖；1:25 b 成功事件再次触发 a，b、c 都齐，a 立即查配额派发，所以 a 应在 1:25 后几乎立刻启动。""",
        followups=[
            dict(
                q="master 挂了会怎样？",
                a="master 只负责控制面工作，不在实例执行的关键路径上。它通过租约选主，挂掉后新节点拿到 Leader 租约，重新加载任务定义和依赖图，继续生成未来窗口实例。重复生成由 (task_id, task_time) 唯一键兜底；已经生成并在 scheduler 分片里的实例不依赖 master 存活，所以调度可以继续，只是新周期实例生成会短暂延迟，需要监控 future_window_lag。",
            ),
            dict(
                q="同一实例被两个 scheduler 处理怎么办？",
                a="先用 scheduler_id 或虚拟分片减少并发处理概率，但不能只依赖分片。每次关键转换都带 generation、attempt 和前置状态 CAS，例如 WAITING_RESOURCE 到 SUBMITTED 只能 update 一行成功。两个 scheduler 同时处理同一上游事件时，一个 CAS 成功，另一个读到 generation 变化后退出；worker 回传也必须校验 attempt，旧尝试不能覆盖新尝试的成功状态。",
            ),
            dict(
                q="补数据一万个实例怎么不打爆集群？",
                a="补数据先写 instance_trigger，包含业务时间范围、优先级和 max_parallelism。实例可以批量生成，但 scheduler 只按窗口释放，比如同一 trigger 最多同时 100 个 WAITING_RESOURCE；BACKFILL 使用独立队列和较低权重，周期任务保留硬配额。失败重试也要进入同一配额体系，不能绕过队列，否则补数据遇到失败会用重试风暴挤垮线上任务。",
            ),
            dict(
                q="跨周期依赖如何计算父实例？",
                a="依赖边只存任务层 parent_task_id、child_task_id 和映射配置。检查子实例时，用子 task_time 输入映射函数，得到父任务应该对应的 parent_task_time，再用 (parent_task_id, parent_task_time) 查父实例状态。比如小时任务依赖当天日任务，映射函数把任意小时归到当天 00:00 的日实例；自依赖上一小时则 offset 为 -60 分钟。这样不需要预先知道父 instance_id。",
            ),
            dict(
                q="一个上游有 2000 个下游，成功时不会触发风暴吗？",
                a="会有 fan-out 压力，所以事件处理要分层削峰。上游成功后先按 parent_task_id 批量读依赖边，再按 child_task_id 或 scheduler_id 分片投递 TRIGGER_DOWNSTREAM，事件带优先级并可批量合并；scheduler 本地对同一 child instance 做短时间去重。真正检查依赖时优先查热 KV 中父成功状态，避免 2000 个下游都打满数据库。指标看 fanout_event_lag 和事件积压。",
            ),
            dict(
                q="为什么不用 MQ 延迟消息完全代替内存延迟队列？",
                a="延迟消息可以做兜底，但完全依赖它会让精度、可见性和批量调整受队列实现限制。scheduler 的内存延迟队列可以毫秒级唤醒、按分片快速重排、结合本地优先级和配额判断；重启后再从数据库恢复即可，不丢权威状态。MQ 延迟消息适合做 RECOVER 或粗粒度提醒，不能替代数据库权威状态和 scheduler 的 ready 检查。",
            ),
            dict(
                q="实例表 10 亿行怎么办？",
                a="首先热冷分层，调度只需要近 30 天热实例，老实例按月归档到对象存储或冷库。热表按租户、项目或 task_id 哈希分表，索引围绕 scheduler_id/status/scheduled_at、task_id/task_time、trigger_id 建，不做全表状态扫描。状态事件表处理完删除或归档，日志和产物不进实例热表。查询历史时走离线检索链路，不影响调度库。",
            ),
            dict(
                q="上游成功事件写入后，scheduler 还没触发下游就崩溃怎么办？",
                a="状态和触发要有可恢复边界。实例先从 RUNNING CAS 到 SUCCEEDED，再写 TRIGGER_DOWNSTREAM 事件；如果写事件前崩溃，monitor 会扫描 SUCCEEDED 但非 DOWNSTREAM_TRIGGERED 的实例补写事件。如果写了事件但处理前崩溃，事件仍在表或可靠队列里，会被其他 scheduler 接走。重复补写也没关系，下游 ready 转换靠 CAS 去重。",
            ),
            dict(
                q="上游失败后下游为什么不直接失败？",
                a="因为调度系统里失败常常是可修复的：上游可能重试成功，或人工修数据后将实例强制成功，也可能只重跑上游某个业务时间。如果下游直接失败，会迫使用户重跑整条链路并丢失等待语义。更稳妥的是下游保持 WAITING_DEPENDENCY，告警说明卡在哪个父实例；只有父实例进入成功或强制成功状态时才放行。",
            ),
        ],
        variants=[
            "离线数仓任务编排系统，要求小时、天、周任务按依赖低延迟启动，并支持补历史分区。",
            "机器学习特征流水线调度系统，上游特征产出后要尽快触发下游训练或校验任务。",
            "报表刷新平台，多租户报表按周期生成并依赖多个数据集，失败后支持重跑和人工跳过。",
            "通用工作流调度器，节点有 cron、依赖、重试、超时、队列和优先级，需要解释 Airflow 类系统的核心取舍。",
        ],
    ),
]
