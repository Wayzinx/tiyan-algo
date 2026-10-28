SYSTEMS = [
    dict(
        id="x2",
        order=2,
        priority=True,
        title="自动化测试执行平台",
        brief="设计一个能管理用例、调度执行节点、占用环境资源、收集可信报告并支撑合入门禁的自动化测试执行平台。",
        statement="""你要设计一个自动化测试执行平台，服务对象是多个研发团队的接口用例和界面用例。平台要支持用例管理：用例有标签、所属业务、优先级、类型、版本和脚本入口；测试计划可以选择用例集、环境、触发方式，触发方式包括手动、定时和代码合入触发。计划运行后，系统要把几千条用例分发到执行节点池，并且正确处理设备、浏览器、测试账号、测试环境这类资源的占用与释放；同一资源可能要求独占，同一计划也有并发上限和优先级。执行结果要按用例和步骤收集日志、截图、断言、耗时和错误分类。平台还要做失败重试与 flaky 识别：同一用例要看历史通过率，失败后最多自动重跑一次，长期不稳定的用例进入隔离名单。最后它要支撑合入门禁：关键用例集必须通过才允许发布，但 flaky 不能无意义阻塞合入，真失败也不能被重试掩盖。要求多租户隔离、审计可追溯，报告延迟可接受但门禁结论必须可信。""",
        focus="""题眼不是单纯把任务扔给 worker，而是 15 分钟内跑完几千条用例，同时让结论可信。低延迟来自分片、资源约束建模和队列调度；可信来自 attempt 级记录、失败分类、重跑不覆盖首败、flaky 只降权不洗白。""",
        scale="""规模假设：平台有 200 个团队、10 万条用例、每日 5000 次计划运行；典型回归计划 3000 条用例，平均 10 秒，P95 30 秒，目标 15 分钟完成。执行节点 50 个，每个节点并发 6 个轻量接口用例或 1 个浏览器用例，峰值触发 20 个计划并发。结果日志平均每用例 80KB，截图平均失败用例 2MB，保存 90 天；调度请求峰值约 1000 case_run/min，报告查询峰值 300 QPS。""",
        example="""一次代码合入触发 3000 条回归计划，包含 2200 条接口用例、800 条界面用例，50 个执行节点可用。20 条支付类用例依赖同一个只能独占的测试账号，不能并发；其中 2 条历史通过率只有 85%，属于 flaky 候选。候选人的设计要说明这些用例如何入队、如何抢资源、如何重试、如何给出门禁结论。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清目标和边界",
                minutes=3,
                prompt="先问清用例类型、资源约束、门禁语义、重试规则、多租户隔离和报告保留策略。",
                points=[
                    "确认 API 和 UI 用例的执行模型是否不同",
                    "确认资源独占、共享、租约和释放规则",
                    "确认门禁只看关键集还是全部用例",
                    "确认 flaky 的识别、隔离和人工恢复规则",
                    "确认触发来源、优先级和并发上限",
                    "确认日志截图的保存时间和权限隔离",
                ],
                reference="""澄清时先把业务目标翻译成调度约束。API 用例通常可高并发，UI 用例受浏览器、设备和桌面环境限制，不能用同一个并发模型。资源要分清共享池和独占池，例如测试账号独占、浏览器可按版本共享、环境可能按命名空间隔离。门禁语义也要提前定死：关键集失败是阻断，非关键集失败是告警；flaky 不是通过，而是从硬门禁里剥离到风险项，并要求有历史证据和隔离名单。还要确认触发来源的优先级，代码合入触发通常比手动探索低或高取决于组织策略，但同一租户必须有并发配额，防止一个团队把 50 个节点吃满。报告侧需要知道日志、截图、断言证据保存多久、谁可见，以及删除后门禁审计是否还保留摘要。最后要问清失败分类由谁给出：执行节点只能上报事实，结果服务可以做错误归类，门禁服务才能给准出结论。这个边界能避免 worker 自报成功就被当成产品通过。""",
            ),
            dict(
                key="estimate",
                title="规模估算",
                minutes=4,
                prompt="用题目数字估算完成时间、调度吞吐、存储量、节点数量和资源瓶颈，并说明这些数字影响了哪些设计。",
                points=[
                    "计算 3000 条用例在 15 分钟内的平均吞吐",
                    "估算 50 个节点的有效并发和瓶颈资源",
                    "估算日志、截图、索引数据的存储量",
                    "估算调度和心跳的 QPS",
                    "说明为什么需要分片队列和资源租约",
                    "说明哪些指标决定是否扩容",
                ],
                reference="""3000 条用例 15 分钟完成，平台需要平均每分钟完成 200 条，也就是约 3.4 条每秒。若平均 10 秒，每秒完成 3.4 条意味着运行中并发至少 34；考虑 P95 30 秒、UI 用例更慢、失败重试和节点抖动，实际需要 150 到 250 个 case_run 并发。50 个节点如果每个可跑 6 个 API 或 1 个 UI，理论可支撑 300 个轻量并发，但 800 条 UI 会受浏览器槽位限制，所以调度要按资源类型分桶，而不是只看节点数。独占账号的 20 条用例即使每条 10 秒，也会形成至少 200 秒串行尾巴，必须提前识别并在计划内排序，避免最后才排到导致超过 15 分钟。日志按 3000 乘 80KB 约 240MB，若 5% 失败且每个失败 2MB 截图，单次约再加 300MB；每日 5000 次不可能全放关系库，关系库只存索引和摘要，对象存储放大日志与截图。调度写入峰值 1000 case_run/min 约 17 QPS，但心跳按 50 节点每 5 秒一次约 10 QPS，瓶颈更多在队列扫描和资源 CAS，因此需要状态索引、延迟队列和租约表。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出服务、存储、队列、执行节点和外部触发方；说明每个服务职责、是否有状态、如何扩展和通信方式。",
                points=[
                    "区分用例管理、计划编排、调度、资源、执行、报告和门禁",
                    "说明控制面和执行面的边界",
                    "说明队列按租户、优先级、资源类型分片",
                    "说明对象存储和关系库各放什么",
                    "说明节点心跳、租约续期和结果回传",
                    "说明扩容时先扩哪个服务",
                ],
                diagram="""flowchart LR
  A["触发方"] --> B["计划服务"]
  C["用例服务"] --> B
  B --> D["调度器"]
  D --> E["任务队列"]
  D --> F["资源服务"]
  F --> G["资源库"]
  E --> H["执行节点"]
  H --> I["结果服务"]
  I --> J["对象存储"]
  I --> K["关系库"]
  K --> L["报告服务"]
  L --> M["门禁服务"]
  M --> A""",
                reference="""服务要按控制面和执行面拆。用例服务管理 case 与 case_version，只负责版本化元数据和脚本入口，不直接执行。计划服务接收手动、定时、代码合入触发，冻结本次 plan_run 的用例版本和环境参数，避免运行中用例被改导致报告不可复现。调度器是有状态协调者，可以多实例部署但同一 plan_run 或同一队列分片只由一个 leader 消费，通过数据库租约或队列消费者组做选主；它负责把 case_run 按租户、优先级、资源类型放入任务队列。资源服务维护资源池和 resource_lease，所有独占资源都必须先拿租约再派发，租约有过期时间和心跳续期。执行节点是无状态或弱状态 worker，从队列拉任务，准备环境，执行脚本，流式上传步骤日志和截图，最后回传 attempt 结果。结果服务接收事件并写关系库摘要，把大日志与截图放对象存储。报告服务读摘要和对象存储生成可审计报告。门禁服务只读 plan_run、case_run、flaky_stat 和关键集规则，给出 PASS、FAIL、RISK 三类结论，不允许执行节点自己判断门禁。扩展上，执行节点和结果服务水平扩展最直接；如果调度慢，按租户或资源类型拆分队列分片。通信上控制面用同步 API，执行结果和调度事件用消息队列，状态落库用 CAS。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="设计核心表，覆盖用例版本、计划运行、单用例 attempt、执行节点、资源租约、flaky 统计和报告索引。",
                points=[
                    "case 与 case_version 分离，运行时冻结版本",
                    "plan 与 plan_run 分离，保留触发上下文",
                    "case_run 记录 attempt 且唯一键不覆盖首败",
                    "executor 和 resource_lease 支持心跳与租约恢复",
                    "flaky_stat 支持历史通过率和隔离名单",
                    "说明日志截图不直接塞进关系库",
                ],
                ddl="""
CREATE TABLE `test_case` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用例主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `name` VARCHAR(128) NOT NULL COMMENT '用例名',
  `case_type` ENUM('API','UI') NOT NULL COMMENT '用例类型',
  `priority` INT NOT NULL DEFAULT 0 COMMENT '优先级',
  `tags` JSON COMMENT '标签列表',
  `current_version_id` BIGINT UNSIGNED COMMENT '当前版本',
  `status` ENUM('ACTIVE','DISABLED','ISOLATED') NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`,`name`),
  KEY `idx_tenant_type_priority` (`tenant_id`,`case_type`,`priority`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB COMMENT='用例元数据';

CREATE TABLE `case_version` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '版本主键',
  `case_id` BIGINT UNSIGNED NOT NULL COMMENT '用例主键',
  `version_no` INT NOT NULL COMMENT '版本号',
  `script_uri` VARCHAR(512) NOT NULL COMMENT '脚本地址',
  `env_schema` JSON COMMENT '环境参数声明',
  `resource_requirements` JSON COMMENT '资源需求',
  `checksum` VARCHAR(64) NOT NULL COMMENT '脚本校验和',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_case_version` (`case_id`,`version_no`),
  KEY `idx_case_created` (`case_id`,`created_at`)
) ENGINE=InnoDB COMMENT='用例版本';

CREATE TABLE `test_plan` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '计划主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `name` VARCHAR(128) NOT NULL COMMENT '计划名',
  `case_selector` JSON NOT NULL COMMENT '用例选择条件',
  `environment` VARCHAR(64) NOT NULL COMMENT '目标环境',
  `trigger_type` ENUM('MANUAL','SCHEDULE','MERGE') NOT NULL COMMENT '触发方式',
  `max_concurrency` INT NOT NULL DEFAULT 100 COMMENT '计划并发上限',
  `gate_policy` JSON COMMENT '门禁策略',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`,`name`),
  KEY `idx_tenant_trigger` (`tenant_id`,`trigger_type`)
) ENGINE=InnoDB COMMENT='测试计划';

CREATE TABLE `plan_run` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '运行主键',
  `plan_id` BIGINT UNSIGNED NOT NULL COMMENT '计划主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `trigger_id` VARCHAR(128) NOT NULL COMMENT '外部触发幂等号',
  `status` ENUM('CREATED','SCHEDULING','RUNNING','AGGREGATING','PASSED','FAILED','BLOCKED','CANCELLED') NOT NULL COMMENT '运行状态',
  `total_cases` INT NOT NULL DEFAULT 0 COMMENT '用例总数',
  `passed_cases` INT NOT NULL DEFAULT 0 COMMENT '通过数',
  `failed_cases` INT NOT NULL DEFAULT 0 COMMENT '失败数',
  `risk_cases` INT NOT NULL DEFAULT 0 COMMENT '风险数',
  `started_at` DATETIME(3) COMMENT '开始时间',
  `finished_at` DATETIME(3) COMMENT '结束时间',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_plan_trigger` (`plan_id`,`trigger_id`),
  KEY `idx_tenant_status` (`tenant_id`,`status`),
  KEY `idx_plan_started` (`plan_id`,`started_at`)
) ENGINE=InnoDB COMMENT='计划运行';

CREATE TABLE `case_run` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '单用例运行主键',
  `plan_run_id` BIGINT UNSIGNED NOT NULL COMMENT '计划运行',
  `case_id` BIGINT UNSIGNED NOT NULL COMMENT '用例主键',
  `case_version_id` BIGINT UNSIGNED NOT NULL COMMENT '冻结版本',
  `attempt` INT NOT NULL COMMENT '第几次尝试',
  `status` ENUM('PENDING','LEASED','RUNNING','PASSED','FAILED','RETRYING','SKIPPED','CANCELLED') NOT NULL COMMENT '状态',
  `executor_id` BIGINT UNSIGNED COMMENT '执行节点',
  `resource_key` VARCHAR(128) COMMENT '占用资源键',
  `error_type` VARCHAR(64) COMMENT '错误分类',
  `duration_ms` INT COMMENT '耗时毫秒',
  `log_uri` VARCHAR(512) COMMENT '日志对象地址',
  `screenshot_uri` VARCHAR(512) COMMENT '截图对象地址',
  `started_at` DATETIME(3) COMMENT '开始时间',
  `finished_at` DATETIME(3) COMMENT '结束时间',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_case_attempt` (`plan_run_id`,`case_id`,`attempt`),
  KEY `idx_run_status` (`plan_run_id`,`status`),
  KEY `idx_executor_status` (`executor_id`,`status`),
  KEY `idx_case_finished` (`case_id`,`finished_at`)
) ENGINE=InnoDB COMMENT='单用例尝试';

CREATE TABLE `executor` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '节点主键',
  `pool` VARCHAR(64) NOT NULL COMMENT '节点池',
  `capabilities` JSON NOT NULL COMMENT '能力标签',
  `max_slots` INT NOT NULL COMMENT '最大槽位',
  `used_slots` INT NOT NULL DEFAULT 0 COMMENT '已用槽位',
  `status` ENUM('ONLINE','DRAINING','OFFLINE') NOT NULL COMMENT '节点状态',
  `last_heartbeat_at` DATETIME(3) NOT NULL COMMENT '最后心跳',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pool_id` (`pool`,`id`),
  KEY `idx_status_heartbeat` (`status`,`last_heartbeat_at`)
) ENGINE=InnoDB COMMENT='执行节点';

CREATE TABLE `resource_lease` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '租约主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `resource_key` VARCHAR(128) NOT NULL COMMENT '资源键',
  `lease_owner` VARCHAR(128) NOT NULL COMMENT '持有者',
  `case_run_id` BIGINT UNSIGNED NOT NULL COMMENT '用例运行',
  `status` ENUM('HELD','RELEASED','EXPIRED') NOT NULL COMMENT '租约状态',
  `expire_at` DATETIME(3) NOT NULL COMMENT '过期时间',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_resource_held` (`tenant_id`,`resource_key`,`status`),
  KEY `idx_owner` (`lease_owner`),
  KEY `idx_expire` (`status`,`expire_at`)
) ENGINE=InnoDB COMMENT='资源租约';

CREATE TABLE `flaky_stat` (
  `case_id` BIGINT UNSIGNED NOT NULL COMMENT '用例主键',
  `window_days` INT NOT NULL COMMENT '统计窗口天数',
  `runs` INT NOT NULL DEFAULT 0 COMMENT '运行次数',
  `passes` INT NOT NULL DEFAULT 0 COMMENT '通过次数',
  `first_fail_then_pass` INT NOT NULL DEFAULT 0 COMMENT '首败重跑通过次数',
  `flaky_score` DECIMAL(6,4) NOT NULL DEFAULT 0 COMMENT '不稳定分',
  `is_isolated` TINYINT NOT NULL DEFAULT 0 COMMENT '是否隔离',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`case_id`,`window_days`),
  KEY `idx_score` (`flaky_score`,`is_isolated`)
) ENGINE=InnoDB COMMENT='用例稳定性统计';
""",
                reference="""表设计的关键是把定义、版本和运行 attempt 分开。test_case 放稳定元数据和当前状态，case_version 放脚本地址、参数声明、资源需求与 checksum；plan_run 创建时要冻结 case_version_id，后续用例修改不会影响本次报告。test_plan 只是模板，plan_run 才是一次真实运行，trigger_id 用来让代码合入事件幂等。case_run 以 plan_run_id、case_id、attempt 做唯一键，保证自动重跑不会覆盖第一次失败；门禁必须能看到首败、重跑结果和错误分类。executor 只记录节点能力、槽位和心跳，不把节点本地临时状态当权威。resource_lease 用 resource_key 和状态表达独占资源占用，真实系统里更常用 active_lease 表或部分唯一索引来避免历史 RELEASED 影响唯一性；这里的核心思想是拿不到租约不能派发。flaky_stat 是窗口统计，不直接决定通过，只影响是否进入隔离名单和门禁风险项。大日志、截图、视频和浏览器轨迹不该放关系库，只保存对象地址、摘要哈希和权限元数据，避免报告查询拖垮主库。""",
            ),
            dict(
                key="api",
                title="接口与事件",
                minutes=5,
                prompt="列出对外接口、执行节点接口、内部事件和幂等键；说明关键参数、返回和错误处理。",
                points=[
                    "用例和版本创建接口要有版本号或 checksum",
                    "触发计划接口要有 trigger_id 幂等键",
                    "执行节点拉取任务要携带能力和容量",
                    "结果上报按步骤和 attempt 追加",
                    "门禁查询返回通过、失败和风险原因",
                    "事件包含状态变化和资源释放",
                ],
                reference="""对外接口包括 POST /cases 创建用例，POST /cases/{id}/versions 新增版本，参数包含 script_uri、checksum、resource_requirements 和 tags；POST /plans 创建计划，包含 case_selector、environment、trigger_type、max_concurrency 和 gate_policy。触发运行用 POST /plans/{id}/runs，必须带 trigger_id 作为幂等键，返回 plan_run_id 和初始状态。查询接口包括 GET /runs/{id}、GET /runs/{id}/case-runs、GET /reports/{run_id}。执行节点接口可以是 PullTask(pool, capabilities, free_slots) 返回 case_run_id、case_version_id、resource leases 和超时时间；Heartbeat(executor_id, slots, running_case_runs) 用于节点健康；AppendStepLog(case_run_id, attempt, seq, level, message, artifact_uri) 要按 seq 幂等追加；FinishCaseRun(case_run_id, attempt, status, error_type, duration_ms, evidence_hash) 只能终结当前 attempt。内部事件包括 PlanRunCreated、CaseRunLeased、ResourceLeaseExpired、CaseRunFinished、RetryScheduled、FlakyStatUpdated、GateEvaluated。门禁接口 GET /gates/{run_id} 返回 PASS、FAIL 或 RISK，必须列出阻断用例、flaky 风险、隔离跳过项和证据链接。所有写接口都要支持 request_id，服务端保存幂等记录，避免触发方重试生成两次计划运行。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="给出 plan_run 和 case_run 的状态流转，重点说明重试、取消、超时和并发下只转换一次。",
                points=[
                    "区分计划级状态和用例级状态",
                    "失败后进入 RETRYING 而不是直接覆盖结果",
                    "资源租约过期要能回到可调度状态",
                    "计划聚合后才给门禁结论",
                    "所有状态更新用 CAS 或版本号",
                    "说明取消和节点失联分支",
                ],
                diagram="""stateDiagram-v2
  [*] --> CREATED
  CREATED --> SCHEDULING: 冻结用例
  SCHEDULING --> RUNNING: 派发开始
  RUNNING --> AGGREGATING: 全部终态
  AGGREGATING --> PASSED: 门禁通过
  AGGREGATING --> FAILED: 真失败
  AGGREGATING --> BLOCKED: 资源超时
  RUNNING --> CANCELLED: 用户取消
  FAILED --> [*]
  PASSED --> [*]
  BLOCKED --> [*]
  CANCELLED --> [*]""",
                reference="""状态机要分两层。plan_run 从 CREATED 到 SCHEDULING，表示已收到触发但还在冻结用例版本；SCHEDULING 到 RUNNING 表示 case_run 已生成并开始派发；当所有 case_run 都进入 PASSED、FAILED、SKIPPED 或 CANCELLED 这类终态后，进入 AGGREGATING；聚合服务读取 attempt、flaky_stat 和 gate_policy 后，才把计划置为 PASSED、FAILED 或 BLOCKED。case_run 的细粒度状态是 PENDING、LEASED、RUNNING、PASSED、FAILED、RETRYING、SKIPPED、CANCELLED。失败后如果满足自动重跑条件，新建 attempt=2 的 case_run，原 attempt=1 保持 FAILED，不允许把同一行改成 PASSED。节点失联时，如果租约过期且 attempt 未终态，调度器用 CAS 把 LEASED 或 RUNNING 改回 PENDING 或标记为 FAILED_TIMEOUT，再决定是否重试。并发控制靠 version 字段，例如 update case_run set status='RUNNING', version=version+1 where id=? and status='LEASED' and version=?；只有一行受影响才算抢到。计划聚合也要 CAS，防止两个聚合器同时写门禁结论。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="用一个计划运行串起触发、冻结、排队、拿资源、执行、重试、报告和门禁；再讲资源竞争和 flaky 分支。",
                points=[
                    "触发后先冻结用例版本再生成 case_run",
                    "调度前先做资源租约和节点槽位匹配",
                    "步骤日志和截图流式上传",
                    "失败重跑只新增 attempt",
                    "flaky 分支进入风险而非直接通过",
                    "报告聚合后再计算门禁",
                ],
                diagram="""sequenceDiagram
  participant T as 触发方
  participant P as 计划服务
  participant S as 调度器
  participant R as 资源服务
  participant W as 执行节点
  participant O as 结果服务
  participant G as 门禁服务
  T->>P: 触发计划 trigger_id
  P->>P: 冻结用例版本
  P->>S: 生成待执行任务
  S->>R: 申请资源租约
  S->>W: 派发任务
  W->>O: 上传步骤日志
  W->>O: 完成 attempt
  O->>S: 结果事件
  S->>S: 判断是否重试
  O->>G: 聚合完成
  G->>T: 返回门禁结论""",
                reference="""正常主链路是触发方用 trigger_id 调用计划服务，计划服务根据 plan 的选择器解析出 3000 条用例，并冻结每条用例的 case_version_id 与环境参数。调度器把 case_run 按优先级、类型和资源需求放入队列，先满足关键集和长尾独占资源，避免 20 条独占账号用例排到最后形成尾延迟。调度器给某条用例派发前，先向资源服务申请 resource_key 的租约，再检查执行节点能力和剩余槽位；成功后节点开始执行并持续上传步骤日志、断言和截图地址。结果服务收到 FinishCaseRun 后写 attempt 摘要并发 CaseRunFinished。若 attempt=1 失败且错误分类允许重跑，调度器创建 attempt=2；如果重跑通过，报告显示首败和重跑通过，门禁根据 flaky 规则给风险而不是简单 PASS。资源竞争分支里，20 条共享独占账号的用例一次只能持有一个租约，其余保持 PENDING 或延迟队列；租约超时由巡检释放。flaky 分支里，2 条历史不稳定用例若首败重跑过，门禁可以不阻塞合入，但必须在风险列表展示并推动隔离或修复。""",
            ),
            dict(
                key="reliability",
                title="可靠性方案",
                minutes=5,
                prompt="说明选主、幂等、重试、故障恢复、巡检、限流隔离、扩展和监控指标。",
                points=[
                    "调度器分片选主和租约保护",
                    "触发、派发、结果上报都要幂等",
                    "节点失联和资源泄漏有巡检恢复",
                    "重试有上限且按错误类型区分",
                    "租户级限流和资源隔离",
                    "监控 15 分钟完成率和门禁误判率",
                ],
                reference="""可靠性要围绕可信门禁。调度器可以按 tenant_id 或 plan_run_id 分片，每个分片通过租约选主；旧主恢复后写状态必须带 version，防止双主重复派发。幂等分三处：触发用 trigger_id，派发用 case_run_id 加 attempt，结果上报用 case_run_id、attempt、seq 或 evidence_hash。重试不能一刀切，环境启动失败、节点丢失、网络抖动可重试，断言失败默认是真失败，只允许按策略重跑一次用于确认 flaky。节点失联由心跳巡检发现，超过两倍心跳周期进入 DRAINING，释放过期租约，把未终态任务重新排队或标记超时。资源泄漏由 resource_lease 的 expire_at 扫描兜底，释放前要确认对应 case_run 未在正常运行，避免误抢。限流上每个租户有并发配额，关键集和合入触发可有独立队列，避免手动大计划阻塞门禁。扩展上先扩执行节点和对象存储带宽，再按队列分片扩调度器。核心监控包括计划 15 分钟完成率、排队 P95、资源租约等待时间、case_run 重复派发数、首败重跑通过率、flaky 隔离命中数、门禁误判申诉数和报告生成延迟。""",
            ),
        ],
        mistakes=[
            dict(wrong="失败了就自动重跑到通过，最后报告只展示最终结果。", verdict="最大扣分点", why="这会把真失败洗成通过，和结果可信的题眼直接冲突。正确做法是 attempt 级保存首败和重跑，门禁读取完整证据链，重跑通过只能降低阻断等级或标记风险。"),
            dict(wrong="50 个节点足够，把 3000 条任务平均分给它们就行。", verdict="有错", why="平均分忽略了 UI 槽位、独占账号、P95 耗时和节点失联。调度必须按资源类型、优先级和长尾约束建模，否则理论并发够，实际尾部仍可能超过 15 分钟。"),
            dict(wrong="flaky 用例直接不参与门禁。", verdict="方向对但不准", why="flaky 不应该无意义阻塞合入，但也不能静默消失。它要有历史窗口、隔离名单、风险报告和恢复机制，关键用例长期 flaky 本身就是质量债。"),
            dict(wrong="日志、截图都放到 MySQL，查报告方便。", verdict="有错", why="大对象进入关系库会放大写入和查询压力，影响调度主链路。正确做法是对象存储放原始证据，关系库只放 URI、摘要、状态、索引和权限元数据。"),
            dict(wrong="资源占用靠执行节点自己记，跑完释放即可。", verdict="缺失", why="节点崩溃时本地状态丢失，会造成独占账号被重复使用或永远不释放。资源租约必须在服务端持久化，有过期时间、续期和巡检释放。"),
            dict(wrong="用例表直接覆盖脚本内容，不需要版本表。", verdict="搞反", why="计划运行需要可复现，运行中脚本被改会导致报告不可解释。用例元数据和版本必须分离，plan_run 冻结 case_version_id 与 checksum。"),
        ],
        walkthrough="""这次合入事件先带 trigger_id 调用计划服务，计划服务发现没有同 trigger_id 的 plan_run，于是创建运行并解析出 3000 条用例，冻结 3000 个 case_version_id。调度器把 2200 条 API 用例放入高并发队列，把 800 条 UI 用例放入浏览器资源队列，同时把 20 条依赖同一测试账号的用例标记为独占资源队列并提前排入，避免形成最后的串行尾巴。执行节点心跳上报 50 个节点的能力和槽位后，调度器对普通 API 用例批量派发，对 UI 用例按浏览器槽位派发，对独占账号用例一次只申请一个 resource_lease。节点执行时把步骤日志、截图和断言结果上传到结果服务，结果服务写 case_run 摘要和对象地址。两条历史 flaky 用例如果第一次失败，调度器只创建 attempt=2，不覆盖 attempt=1；若重跑通过，flaky_stat 的 first_fail_then_pass 增加，报告展示风险。若某条关键用例断言失败且重跑仍失败，门禁服务在所有 case_run 终态后把 plan_run 聚合为 FAILED。若只有隔离名单里的 flaky 风险，门禁可以返回 PASS_WITH_RISK 或 RISK，触发方按策略决定是否人工确认。""",
        oral="""我会把这个平台分成控制面和执行面。控制面有用例服务、计划服务、调度器、资源服务、结果服务、报告服务和门禁服务；执行面是一组带能力标签的执行节点。核心约束是 3000 条回归要 15 分钟完成，所以不能只建一个简单任务表轮询，而要在计划触发时冻结用例版本，生成 case_run，再按租户、优先级、用例类型和资源需求分片排队。50 个节点理论吞吐够，但真正的瓶颈是 UI 槽位和那个独占测试账号，所以资源服务要用 resource_lease 表表达独占和共享，拿不到租约就不能派发。数据上，case 和 case_version 分开，plan 和 plan_run 分开，case_run 用 plan_run_id、case_id、attempt 做唯一键，保证失败重跑不会覆盖首败。日志、截图和视频放对象存储，关系库只放 URI、摘要和索引。状态机上，plan_run 从 CREATED、SCHEDULING、RUNNING 到 AGGREGATING，最后由门禁服务给 PASSED、FAILED 或 BLOCKED；case_run 从 PENDING 到 LEASED、RUNNING，再到 PASSED 或 FAILED，失败后如果策略允许就新建 attempt=2。可靠性上，调度器分片选主，所有状态更新带版本号 CAS，触发、派发、结果上报都有幂等键；节点失联靠心跳和租约过期巡检恢复。回到例子，3000 条用例会先冻结版本并排队，20 条独占账号用例被提前串行调度，2 条 flaky 用例首败重跑也保留证据，最后门禁既不会被 flaky 无谓阻塞，也不会让真失败被重试掩盖。""",
        followups=[
            dict(q="为什么 case_run 要把 attempt 放进唯一键，而不是同一行更新重试次数？", a="因为门禁可信依赖完整证据链。同一行更新会覆盖首败的错误分类、日志和截图，之后只能看到最终通过，无法判断是环境抖动、真实缺陷还是 flaky。把 attempt 放进唯一键后，每次尝试都是不可覆盖事实，聚合层可以按策略解释首败重跑通过。"),
            dict(q="20 条用例共用一个独占账号会拖尾，怎么保证 15 分钟？", a="先在冻结用例时识别 resource_requirements，把独占资源用例放到特殊队列并提前调度。假设每条 10 秒，串行约 200 秒，可以和其他 2980 条并行重叠；如果等普通用例快跑完才调度，就会产生尾延迟。指标上看资源等待 P95 和计划剩余长尾。"),
            dict(q="断言失败要不要自动重跑？", a="默认把断言失败当真失败，只有策略允许且该用例有 flaky 历史或错误类型显示环境不稳定时，才自动重跑一次。重跑的目的是确认不稳定性，不是洗掉失败；首败仍然进入报告，门禁根据关键性和隔离名单决定阻断或风险。"),
            dict(q="调度器崩溃后如何恢复正在跑的任务？", a="执行节点持续心跳并持有租约。调度器恢复后从 case_run 查 LEASED 或 RUNNING 的任务，再结合 executor 心跳和 resource_lease 过期时间判断。如果节点还活着就等待结果，如果节点失联且租约过期，用 CAS 标记超时并重新排队或创建重试 attempt。"),
            dict(q="如何做多租户隔离？", a="控制面所有核心表带 tenant_id，队列按租户和优先级分片，执行资源有租户配额和最大并发。对象存储路径和报告权限也按租户隔离。这样一个团队发起超大手动计划，只会耗尽自己的配额，不会阻塞其他团队的合入门禁。"),
            dict(q="flaky_stat 的窗口怎么设计？", a="可以用最近 7 天和最近 30 天两个窗口，记录运行数、通过数、首败重跑通过数和错误类型分布。样本太少时不自动判 flaky，避免两次偶然失败就隔离；达到阈值后进入候选，再由规则或人工确认进入隔离名单。"),
            dict(q="报告延迟和门禁延迟冲突怎么办？", a="门禁不需要等完整 HTML 报告和所有大截图转码，只需要 case_run 终态、关键断言摘要、错误分类和证据 URI。结果服务先写结构化摘要用于门禁，报告服务异步生成详情页；但证据对象上传失败时不能给硬 PASS，只能 BLOCKED 或风险。"),
            dict(q="执行节点重复收到了同一个 case_run 怎么办？", a="派发和开始执行都要 CAS。节点拿到任务后调用 StartCaseRun，只有状态从 LEASED 改为 RUNNING 且版本匹配才算成功。结果上报带 case_run_id 和 attempt，结果服务对终态写入做幂等，重复上报只返回已记录结果。"),
        ],
        variants=[
            "持续集成平台的大规模回归调度与合入门禁设计。",
            "移动设备云测试平台的设备租约、排队和报告可信设计。",
            "浏览器兼容性测试平台的并发执行与 flaky 治理。",
            "接口压测前置校验平台的资源隔离和质量门禁。",
        ],
    ),
    dict(
        id="x3",
        order=3,
        priority=True,
        title="Agent 评测平台",
        brief="设计一个可复现、可比较、能在限流下并发执行并支撑回归门禁的 Agent 评测平台。",
        statement="""你要设计一个 Agent 评测平台。平台要管理评测集：数据集有版本，样本包含输入、标注答案、标签、难度、期望工具调用或判分规则。用户可以创建评测任务，选择被测模型或 Agent 版本、数据集版本、运行参数和打分器；Runner 并发执行样本，调用被测 Agent，并处理上游模型配额、限流、超时、重试和沙箱隔离。打分部分既有规则打分，也有 LLM 裁判打分，裁判返回偶尔会是非法 JSON，平台要做格式校验、重试、降级和一致性校验。结果要支持两个版本逐样本 diff、汇总指标、显著性判断和失败样本回放。回归门禁要求核心集分数下降超过阈值就阻止发布。题目重点是结果必须可复现、可比较：同一个 Agent 版本在同一个数据集版本上两次运行差异要能解释，而不是简单说模型随机。平台要在上游模型限流下完成大规模评测，并保证多租户、审计和成本可控。""",
        focus="""题眼是可复现和可比较，其次才是吞吐。必须冻结数据集版本、Agent 版本、提示词、工具镜像、模型参数、随机种子和裁判版本；在 600 次每分钟配额下跑 2 万样本 1 小时，需要并发、限流和分阶段打分，而不是无限开 runner。""",
        scale="""规模假设：平台有 5 万条样本、100 个数据集版本、每天 300 次评测运行。核心集 2000 条，全量集 2 万条；每个样本平均调用被测 Agent 1 次、裁判 1 次，P95 单样本 8 秒。上游模型配额 600 次/分钟，等于 10 QPS；2 万样本若每样本 2 次上游调用就是 4 万次，1 小时平均 11.1 QPS，必须减少裁判调用或申请并行配额。结果记录平均 20KB，轨迹对象平均 200KB。""",
        example="""一次发布前要对比 Agent v12 和 v13 在 2000 条核心集上的表现。被测模型总配额每分钟 600 次调用，Runner 需要限流；裁判模型偶尔返回非法 JSON。候选人的设计要说明如何冻结数据集版本、如何执行两次版本评测、如何处理非法裁判结果、如何逐样本 diff，并在分数下降超过 1% 时阻止发布。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清评测语义",
                minutes=3,
                prompt="先确认样本结构、可复现口径、打分器类型、限流口径、门禁阈值和沙箱边界。",
                points=[
                    "确认数据集版本是否不可变",
                    "确认被测 Agent 版本包含哪些依赖",
                    "确认规则打分和裁判打分的优先级",
                    "确认模型配额是全局还是租户级",
                    "确认随机性、温度和种子的要求",
                    "确认门禁阈值和显著性口径",
                ],
                reference="""澄清要先把可比较的口径问死。数据集版本发布后必须不可变，样本、标注答案、标签和判分规则都属于版本内容；如果允许改样本，就不能把 v12 和 v13 的分数直接比较。Agent 版本也不只是一个字符串，要冻结代码包、提示词、工具清单、依赖镜像、模型参数、温度、随机种子和环境变量白名单。打分器要区分规则打分和裁判打分，规则能确定的样本优先用规则，裁判只处理开放答案或语义判断。限流要问清 600 次每分钟是被测 Agent 和裁判共用，还是分别计费；如果共用，2 万样本 1 小时需要减少裁判调用、分批运行或申请更多配额。门禁要确认是平均分下降、核心标签下降，还是关键样本失败，同时要问显著性和最小样本数，避免 0.2% 抖动阻塞发布。""",
            ),
            dict(
                key="estimate",
                title="容量估算",
                minutes=4,
                prompt="根据 2 万样本、1 小时、600 次每分钟配额估算吞吐、并发、存储和分片，并指出设计取舍。",
                points=[
                    "计算配额换算后的 QPS",
                    "计算 2 万样本 1 小时所需样本吞吐",
                    "估算被测调用和裁判调用总量",
                    "估算 Runner 并发和队列长度",
                    "估算结果与轨迹存储",
                    "说明何时需要跳过裁判或分层评测",
                ],
                reference="""600 次每分钟等于 10 次每秒。2 万样本 1 小时完成，需要每秒完成约 5.56 个样本。如果每个样本只调用被测 Agent 一次，配额足够；如果还要每个样本调用一次裁判，总调用变成 4 万次，平均 11.1 QPS，已经超过 10 QPS，更不用说重试和非法 JSON。所以设计上不能盲目每样本都用裁判：规则样本先规则打分，只有开放题进入裁判；裁判非法 JSON 重试有上限；全量集可分阶段，核心集优先用于门禁。P95 单样本 8 秒，要达到 5.56 样本每秒，Runner 并发至少 45；考虑沙箱启动、重试和长尾，需要 80 到 120 个并发槽位，但令牌桶会把实际外呼限制在 10 QPS。核心集 2000 条，如果每条 2 次调用，理论配额耗时约 400 秒，可以支撑发布前门禁。存储上每样本结构化结果 20KB，2 万样本约 400MB；轨迹对象 200KB 则约 4GB，关系库只存摘要、分数、错误和对象 URI。按 eval_run_id 分片 sample_result，按 dataset_version_id 建样本索引，报告查询才不会扫全表。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出数据集、任务、Runner、限流、沙箱、打分、对比、门禁和存储之间的关系。",
                points=[
                    "数据集服务负责不可变版本",
                    "评测任务服务冻结运行配置",
                    "Runner 池负责并发和沙箱执行",
                    "限流服务统一管理配额令牌",
                    "打分服务处理规则与裁判",
                    "对比和门禁服务只读结果给结论",
                ],
                diagram="""flowchart LR
  A["用户"] --> B["任务服务"]
  C["数据集服务"] --> B
  B --> D["调度器"]
  D --> E["任务队列"]
  E --> F["Runner池"]
  F --> G["限流器"]
  F --> H["沙箱"]
  H --> I["被测Agent"]
  F --> J["打分服务"]
  J --> K["裁判模型"]
  J --> L["结果库"]
  F --> M["对象存储"]
  L --> N["对比门禁"]
  N --> A""",
                reference="""服务拆分要让可复现证据有权威来源。数据集服务管理 dataset、dataset_version 和 sample，版本发布后只读，新增修订必须生成新版本。任务服务创建 eval_task 和 eval_run，冻结 Agent 版本、数据集版本、打分器版本、模型参数、随机种子、工具镜像和配额策略。调度器把 eval_run 拆成 sample_result 任务，按标签、成本和优先级进入队列；核心集和全量集可以不同队列。Runner 池负责拉任务、启动沙箱、调用被测 Agent、记录输入输出和工具轨迹。限流器是集中服务或强一致 KV 上的令牌桶，所有 Runner 调被测模型和裁判模型前都要取令牌，防止局部实例放大配额。打分服务先做规则打分，再调用裁判模型，裁判输出必须经过 JSON schema 校验和一致性检查。结果库保存结构化分数、错误、attempt 和可比较字段，对象存储保存完整轨迹、提示词快照和裁判原文。对比门禁服务只读 eval_run、sample_result、judge_result 和 baseline，计算逐样本 diff、置信区间和阈值结论，不参与执行，避免执行侧自证通过。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="设计数据集版本、样本、任务、运行、样本结果、裁判结果和基线表，强调唯一键与可复现字段。",
                points=[
                    "dataset_version 发布后不可变并有 checksum",
                    "sample 归属具体版本且带标签和标注",
                    "eval_run 冻结 Agent、打分器和模型参数",
                    "sample_result 用 eval_run_id、sample_id、attempt 唯一",
                    "judge_result 保存原文、解析状态和一致性",
                    "baseline 绑定核心集和门禁阈值",
                ],
                ddl="""
CREATE TABLE `dataset` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '数据集主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `name` VARCHAR(128) NOT NULL COMMENT '数据集名',
  `description` VARCHAR(512) COMMENT '描述',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`,`name`),
  KEY `idx_tenant_created` (`tenant_id`,`created_at`)
) ENGINE=InnoDB COMMENT='数据集';

CREATE TABLE `dataset_version` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '数据集版本主键',
  `dataset_id` BIGINT UNSIGNED NOT NULL COMMENT '数据集主键',
  `version_no` INT NOT NULL COMMENT '版本号',
  `status` ENUM('DRAFT','PUBLISHED','ARCHIVED') NOT NULL COMMENT '版本状态',
  `sample_count` INT NOT NULL DEFAULT 0 COMMENT '样本数',
  `checksum` VARCHAR(64) NOT NULL COMMENT '版本内容校验和',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  `published_at` DATETIME(3) COMMENT '发布时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_version` (`dataset_id`,`version_no`),
  UNIQUE KEY `uk_checksum` (`checksum`),
  KEY `idx_dataset_status` (`dataset_id`,`status`)
) ENGINE=InnoDB COMMENT='不可变数据集版本';

CREATE TABLE `sample` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '样本主键',
  `dataset_version_id` BIGINT UNSIGNED NOT NULL COMMENT '数据集版本',
  `sample_key` VARCHAR(128) NOT NULL COMMENT '样本业务键',
  `input_uri` VARCHAR(512) NOT NULL COMMENT '输入对象地址',
  `expected_uri` VARCHAR(512) COMMENT '标注答案地址',
  `tags` JSON COMMENT '标签',
  `difficulty` VARCHAR(32) COMMENT '难度',
  `scoring_rule` JSON COMMENT '规则打分配置',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_version_sample` (`dataset_version_id`,`sample_key`),
  KEY `idx_version_difficulty` (`dataset_version_id`,`difficulty`)
) ENGINE=InnoDB COMMENT='评测样本';

CREATE TABLE `eval_task` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `name` VARCHAR(128) NOT NULL COMMENT '任务名',
  `dataset_version_id` BIGINT UNSIGNED NOT NULL COMMENT '数据集版本',
  `agent_version` VARCHAR(128) NOT NULL COMMENT '被测 Agent 版本',
  `scorer_version` VARCHAR(128) NOT NULL COMMENT '打分器版本',
  `run_config` JSON NOT NULL COMMENT '运行参数',
  `gate_policy` JSON COMMENT '门禁策略',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_name` (`tenant_id`,`name`),
  KEY `idx_dataset_agent` (`dataset_version_id`,`agent_version`)
) ENGINE=InnoDB COMMENT='评测任务模板';

CREATE TABLE `eval_run` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '运行主键',
  `eval_task_id` BIGINT UNSIGNED NOT NULL COMMENT '任务主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `run_key` VARCHAR(128) NOT NULL COMMENT '幂等运行键',
  `dataset_version_id` BIGINT UNSIGNED NOT NULL COMMENT '冻结数据集版本',
  `agent_version` VARCHAR(128) NOT NULL COMMENT '冻结 Agent 版本',
  `agent_digest` VARCHAR(64) NOT NULL COMMENT '代码或镜像摘要',
  `scorer_version` VARCHAR(128) NOT NULL COMMENT '冻结打分器版本',
  `model_params` JSON NOT NULL COMMENT '模型参数和随机种子',
  `status` ENUM('CREATED','RUNNING','SCORING','COMPARING','PASSED','FAILED','BLOCKED','CANCELLED') NOT NULL COMMENT '运行状态',
  `total_samples` INT NOT NULL DEFAULT 0 COMMENT '样本总数',
  `score` DECIMAL(8,4) COMMENT '总分',
  `started_at` DATETIME(3) COMMENT '开始时间',
  `finished_at` DATETIME(3) COMMENT '结束时间',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_run_key` (`eval_task_id`,`run_key`),
  KEY `idx_tenant_status` (`tenant_id`,`status`),
  KEY `idx_dataset_agent` (`dataset_version_id`,`agent_version`)
) ENGINE=InnoDB COMMENT='评测运行';

CREATE TABLE `sample_result` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '样本结果主键',
  `eval_run_id` BIGINT UNSIGNED NOT NULL COMMENT '评测运行',
  `sample_id` BIGINT UNSIGNED NOT NULL COMMENT '样本主键',
  `attempt` INT NOT NULL COMMENT '尝试次数',
  `status` ENUM('PENDING','RUNNING','AGENT_DONE','SCORED','FAILED','TIMEOUT','CANCELLED') NOT NULL COMMENT '状态',
  `runner_id` VARCHAR(128) COMMENT 'Runner 标识',
  `agent_output_uri` VARCHAR(512) COMMENT '被测输出地址',
  `trace_uri` VARCHAR(512) COMMENT '轨迹对象地址',
  `rule_score` DECIMAL(8,4) COMMENT '规则分',
  `final_score` DECIMAL(8,4) COMMENT '最终分',
  `error_type` VARCHAR(64) COMMENT '错误分类',
  `duration_ms` INT COMMENT '耗时毫秒',
  `started_at` DATETIME(3) COMMENT '开始时间',
  `finished_at` DATETIME(3) COMMENT '结束时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_run_sample_attempt` (`eval_run_id`,`sample_id`,`attempt`),
  KEY `idx_run_status` (`eval_run_id`,`status`),
  KEY `idx_sample` (`sample_id`)
) ENGINE=InnoDB COMMENT='样本执行结果';

CREATE TABLE `judge_result` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '裁判结果主键',
  `sample_result_id` BIGINT UNSIGNED NOT NULL COMMENT '样本结果',
  `judge_version` VARCHAR(128) NOT NULL COMMENT '裁判版本',
  `attempt` INT NOT NULL COMMENT '裁判尝试次数',
  `status` ENUM('VALID','INVALID_JSON','INCONSISTENT','FAILED') NOT NULL COMMENT '裁判状态',
  `raw_output_uri` VARCHAR(512) NOT NULL COMMENT '裁判原文地址',
  `parsed_score` DECIMAL(8,4) COMMENT '解析分数',
  `reason_hash` VARCHAR(64) COMMENT '理由摘要',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sample_judge_attempt` (`sample_result_id`,`judge_version`,`attempt`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB COMMENT='裁判打分结果';

CREATE TABLE `baseline` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '基线主键',
  `tenant_id` BIGINT UNSIGNED NOT NULL COMMENT '租户',
  `dataset_version_id` BIGINT UNSIGNED NOT NULL COMMENT '数据集版本',
  `agent_version` VARCHAR(128) NOT NULL COMMENT '基线 Agent 版本',
  `eval_run_id` BIGINT UNSIGNED NOT NULL COMMENT '基线运行',
  `metric_name` VARCHAR(64) NOT NULL COMMENT '指标名',
  `metric_value` DECIMAL(8,4) NOT NULL COMMENT '指标值',
  `drop_threshold` DECIMAL(8,4) NOT NULL COMMENT '下降阈值',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_baseline_metric` (`tenant_id`,`dataset_version_id`,`metric_name`),
  KEY `idx_run` (`eval_run_id`)
) ENGINE=InnoDB COMMENT='回归基线';
""",
                reference="""表设计要把可复现字段落到 eval_run，而不是只靠任务名。dataset 是逻辑集合，dataset_version 是不可变快照，checksum 绑定样本、标注、标签和规则；sample 必须归属于具体版本，sample_key 只在版本内唯一。eval_task 是模板，eval_run 才是一次执行事实，里面冻结 dataset_version_id、agent_version、agent_digest、scorer_version、model_params 和 run_key。sample_result 用 eval_run_id、sample_id、attempt 唯一，Runner 超时或重试不会覆盖第一次失败，这和测试平台类似。judge_result 保存裁判版本、尝试次数、原始输出、解析状态和分数；非法 JSON 不是简单丢弃，而是可审计事实。baseline 绑定数据集版本和指标阈值，门禁比较时必须确认 candidate 和 baseline 用的是同一个 dataset_version 与可兼容的 scorer_version。对象存储保存输入、输出、轨迹、裁判原文和回放材料，关系库保存 URI、摘要、分数、状态和索引；不要把完整对话轨迹塞进 sample_result。""",
            ),
            dict(
                key="api",
                title="接口与事件",
                minutes=5,
                prompt="列出数据集发布、创建评测、Runner 拉任务、打分、对比和门禁接口，说明幂等和返回。",
                points=[
                    "发布数据集版本返回 checksum",
                    "创建 eval_run 使用 run_key 幂等",
                    "Runner 拉任务携带容量和能力",
                    "模型调用前走限流令牌接口",
                    "裁判接口返回解析状态和重试建议",
                    "对比接口返回逐样本 diff 与门禁结论",
                ],
                reference="""对外接口从数据集开始：POST /datasets 创建集合，POST /datasets/{id}/versions 上传样本清单并生成 checksum，POST /dataset-versions/{id}/publish 发布不可变版本。评测接口是 POST /eval-tasks 创建模板，POST /eval-tasks/{id}/runs 创建运行，参数包含 run_key、agent_version、agent_digest、model_params、scorer_version 和 baseline_id；run_key 保证触发方重试不生成重复运行。Runner 接口可以是 PullSample(run_id, runner_id, capabilities, free_slots) 返回 sample_id、输入 URI、超时和沙箱配置；AcquireToken(provider, purpose, cost) 从限流器取令牌；FinishAgentCall(sample_result_id, attempt, output_uri, trace_uri, status, error_type) 写被测输出。打分接口 ScoreSample(sample_result_id, scorer_version) 先规则打分，必要时调用裁判；裁判返回必须包含 status、parsed_score、raw_output_uri 和 retryable。对比接口 GET /eval-runs/{id}/compare?baseline_run_id=xxx 返回总体分、标签分、逐样本 win/loss/tie、置信区间和下降原因。门禁接口 GET /eval-runs/{id}/gate 返回 PASS、FAIL 或 BLOCKED，并列出超过阈值的指标、非法裁判比例和不可复现实例。内部事件包括 EvalRunCreated、SampleLeased、AgentCallFinished、JudgeInvalidJson、SampleScored、EvalRunCompared、GateEvaluated。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="说明 eval_run 和 sample_result 的状态，覆盖限流等待、超时、裁判非法 JSON、比较和门禁。",
                points=[
                    "eval_run 先执行再打分再比较",
                    "sample_result attempt 不覆盖",
                    "非法 JSON 是裁判状态而非样本通过",
                    "限流等待不算失败但要计入耗时",
                    "门禁只在比较完成后产生",
                    "状态更新用 CAS 防重复执行",
                ],
                diagram="""stateDiagram-v2
  [*] --> CREATED
  CREATED --> RUNNING: 拆分样本
  RUNNING --> SCORING: Agent完成
  SCORING --> COMPARING: 打分完成
  COMPARING --> PASSED: 未下降
  COMPARING --> FAILED: 超过阈值
  RUNNING --> BLOCKED: 配额不足
  SCORING --> BLOCKED: 裁判不可用
  RUNNING --> CANCELLED: 用户取消
  PASSED --> [*]
  FAILED --> [*]
  BLOCKED --> [*]
  CANCELLED --> [*]""",
                reference="""eval_run 的状态体现阶段边界。CREATED 表示运行配置已冻结；RUNNING 表示 Runner 正在调用被测 Agent；所有样本有被测输出或终态错误后进入 SCORING；规则和裁判打分都完成后进入 COMPARING；对比 baseline 并计算门禁后才进入 PASSED 或 FAILED。如果配额长期不足、裁判服务不可用或证据缺失，应该是 BLOCKED，而不是给一个低分或假 PASS。sample_result 也有状态：PENDING、RUNNING、AGENT_DONE、SCORED、FAILED、TIMEOUT、CANCELLED。被测 Agent 超时可以按策略重试，但新建 attempt，保留旧 attempt 的超时证据。裁判非法 JSON 属于 judge_result 的 INVALID_JSON 状态，打分服务可用修复提示重试一次；多次仍非法则样本进入评分失败或人工复核，不应把空分当 0 分静默参与比较。并发下 Runner 拉任务、开始执行和写终态都用 CAS，例如只有 PENDING 才能改 RUNNING，只有当前 attempt 才能写终态。这样重复拉取和重试不会产生两个互相覆盖的结果。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="用 v12/v13 核心集对比串起冻结、执行、限流、裁判、对比和门禁；再讲非法 JSON 分支。",
                points=[
                    "创建运行时冻结所有可复现输入",
                    "Runner 调用前统一拿令牌",
                    "沙箱记录工具轨迹和输出",
                    "规则优先，裁判补充",
                    "非法 JSON 校验失败后有限重试",
                    "同版本对比同一数据集版本",
                ],
                diagram="""sequenceDiagram
  participant U as 用户
  participant T as 任务服务
  participant Q as 调度器
  participant R as Runner
  participant L as 限流器
  participant A as 被测Agent
  participant S as 打分服务
  participant C as 对比门禁
  U->>T: 创建v13运行
  T->>T: 冻结配置
  T->>Q: 拆分样本
  R->>Q: 拉取样本
  R->>L: 获取令牌
  R->>A: 调用Agent
  R->>S: 提交输出
  S->>S: 规则或裁判打分
  S->>C: 样本得分完成
  C->>U: 返回diff和门禁""",
                reference="""以 v12 和 v13 的 2000 条核心集对比为例，先确认 v12 已有 baseline，并且 baseline 的 dataset_version、scorer_version 和核心标签集合与本次兼容。用户创建 v13 eval_run 时，任务服务冻结 Agent 包摘要、提示词、工具镜像、模型参数、随机种子、数据集版本和打分器版本。调度器生成 2000 个 sample_result，Runner 拉取样本后先向限流器取令牌，拿不到就等待而不是直接失败；拿到后在沙箱中调用被测 Agent，记录输入、输出、工具调用、耗时和错误。打分服务先检查样本是否有规则打分，能规则判断就不调用裁判；需要裁判时，再取裁判配额并要求返回 JSON。若裁判返回非法 JSON，打分服务保存 raw_output_uri 和 INVALID_JSON，使用更严格的格式提示重试一次；仍失败则该样本标为评分失败，门禁可能 BLOCKED。全部样本有分数后，对比服务按 sample_id 与 v12 逐样本 diff，统计 win、loss、tie、标签分和置信区间。如果总分或关键标签分下降超过 1%，且下降不是由不可评分样本造成，就门禁失败并列出最影响分数的样本。""",
            ),
            dict(
                key="reliability",
                title="可靠性方案",
                minutes=5,
                prompt="说明幂等、限流、重试、沙箱恢复、裁判一致性、巡检、扩展和监控指标。",
                points=[
                    "运行创建、样本执行、裁判写入都幂等",
                    "集中令牌桶保护模型配额",
                    "超时和非法 JSON 有分类重试",
                    "沙箱失败保留轨迹并可回放",
                    "裁判一致性用抽样复判或双裁判",
                    "监控可复现差异和门禁误判",
                ],
                reference="""可靠性首先服务于可复现。eval_run 创建用 run_key 幂等，sample_result 用 eval_run_id、sample_id、attempt 唯一，judge_result 用 sample_result_id、judge_version、attempt 唯一，任何重试都不能覆盖旧证据。限流器使用集中令牌桶或强一致 KV，按 provider、purpose、tenant 三维度扣令牌；Runner 本地可以预取少量令牌，但要有过期时间，避免实例崩溃造成配额幻觉。重试按错误分类：上游 429 按退避重试，沙箱启动失败可换节点重试，Agent 业务输出错误不重试，裁判非法 JSON 可用更严格 schema 提示重试一次。沙箱执行要限制网络、文件和时间，输出完整轨迹到对象存储，Runner 崩溃后由巡检把 RUNNING 且心跳过期的样本标记超时并重新排队。裁判一致性可以对高影响样本双裁判或抽样复判，若两个裁判差异超过阈值进入人工复核或 BLOCKED。扩展上，Runner 可水平扩展，但 QPS 受限流器控制；结果库按 eval_run_id 分片，轨迹对象走对象存储。监控包括配额利用率、令牌等待 P95、样本完成率、同版本复跑分差、非法 JSON 比例、裁判一致率、门禁失败原因分布和 1 小时完成率。""",
            ),
        ],
        mistakes=[
            dict(wrong="评测集直接改样本就行，反正任务里记录了运行时间。", verdict="最大扣分点", why="这会让 v12 和 v13 在不同题目上比较，结果不可复现也不可解释。正确做法是 dataset_version 发布后不可变，任何样本或标注变化都生成新版本并重新建立 baseline。"),
            dict(wrong="所有开放题都让 LLM 裁判打分，不需要额外校验。", verdict="有错", why="裁判会返回非法 JSON，也会有随机偏差。不做 schema 校验、一致性复判和原文留存，就无法判断分数变化来自被测 Agent 还是裁判噪声。"),
            dict(wrong="配额 600/min，就把 Runner 开到 600 并发。", verdict="搞反", why="600/min 是调用速率不是并发数。并发过高只会制造 429 和重试风暴；应由集中令牌桶限制 QPS，再按 P95 耗时配置 Runner 并发隐藏延迟。"),
            dict(wrong="同一个版本两次跑分不同是模型随机，接受就行。", verdict="缺失", why="随机性也要可解释。平台要冻结温度、种子、提示词、工具镜像和裁判版本，并记录上游错误、超时和裁判差异，否则回归门禁没有可信依据。"),
            dict(wrong="裁判非法 JSON 就按 0 分处理。", verdict="方向对但不准", why="按 0 分会把平台打分故障伪装成被测 Agent 退化。正确做法是记录 INVALID_JSON、有限重试，超过阈值时 BLOCKED 或人工复核，而不是静默拉低分数。"),
            dict(wrong="只看总分下降，没有必要逐样本 diff。", verdict="有错", why="总分掩盖标签和关键样本退化，也无法定位发布风险。对比必须按 sample_id 做 win/loss/tie 和标签分，门禁才知道是普遍退化还是少数高权重样本失败。"),
        ],
        walkthrough="""发布前用户选择 v13、2000 条核心集和 v12 baseline 创建 eval_run。任务服务先检查 baseline 的 dataset_version 与本次一致，再冻结 v13 的 agent_digest、提示词、工具镜像、模型参数、随机种子和 scorer_version，生成 run_key 防止重复触发。调度器为 2000 个样本创建 sample_result，Runner 池按能力拉取任务。每次调用被测 Agent 前，Runner 向限流器申请令牌；600/min 的配额让系统约按 10 QPS 外呼，Runner 多并发只是覆盖 8 秒 P95 延迟。Agent 输出和工具轨迹进入对象存储，sample_result 保存 URI、耗时和错误类型。打分服务先跑规则打分，开放题再调用裁判。某个裁判返回非法 JSON 时，judge_result 记录 INVALID_JSON 和原文 URI，随后用严格 schema 提示重试一次；如果仍非法，该样本评分失败并计入 BLOCKED 风险。全部样本完成后，对比服务按 sample_id 把 v13 与 v12 做 diff，计算总分、标签分、win/loss/tie 和置信区间。如果 v13 总分下降 1.4%，且核心标签也下降，门禁返回 FAILED；如果下降主要来自裁判不可用或非法 JSON 超阈值，则返回 BLOCKED，要求重跑或人工复核。""",
        oral="""我会先强调这题的核心是可复现和可比较。平台拆成数据集服务、任务服务、调度器、Runner 池、限流器、沙箱、打分服务、结果库、对象存储和对比门禁服务。数据上，dataset 和 dataset_version 分开，版本发布后不可变；sample 绑定具体版本；eval_task 是模板，eval_run 是一次执行事实，里面冻结 Agent 版本、代码摘要、提示词、工具镜像、模型参数、随机种子、数据集版本和打分器版本。sample_result 用 eval_run_id、sample_id、attempt 做唯一键，judge_result 单独保存裁判版本、原文、解析状态和分数，这样超时、重试和非法 JSON 都不会覆盖旧证据。吞吐上，600 次每分钟是 10 QPS；2 万样本 1 小时需要 5.56 样本每秒，如果每个样本还都调用裁判会超过配额，所以规则能打的先规则打分，裁判只处理开放题，核心集优先。Runner 可以有 80 到 120 个并发来覆盖 P95 延迟，但每次外呼都必须从集中令牌桶取令牌。状态上，eval_run 从 CREATED、RUNNING、SCORING 到 COMPARING，最后门禁给 PASSED、FAILED 或 BLOCKED；裁判非法 JSON 是可审计状态，不是直接 0 分。回到 v12 和 v13 的例子，v13 运行会冻结全部配置，在同一 2000 条核心集上执行，裁判失败有限重试并留存原文，最后按 sample_id 与 v12 做逐样本 diff，若核心分下降超过 1% 且差异显著，就阻止发布。""",
        followups=[
            dict(q="为什么数据集版本发布后必须不可变？", a="因为比较的前提是两个 Agent 面对同一批样本、标注和规则。如果发布后还能改样本，v13 分数变化可能来自题目变化而不是能力变化。不可变版本加 checksum 能让 baseline、报告和回放都指向同一事实。"),
            dict(q="2 万样本 1 小时在 600/min 配额下怎么做？", a="先把 600/min 换成 10 QPS，再看每样本调用数。若每样本被测和裁判各一次会超过配额，所以要规则优先、裁判抽样或只评开放题，核心集优先，必要时分阶段跑全量。Runner 并发用于隐藏 8 秒 P95，不突破令牌桶。"),
            dict(q="裁判模型返回非法 JSON 怎么办？", a="裁判原文先入对象存储，judge_result 记 INVALID_JSON，不把它当有效分数。打分服务可以用更严格的 schema 提示重试一次；仍失败则样本评分失败。若比例低，可以标风险；若影响门禁阈值，就返回 BLOCKED 而不是让候选版本背锅。"),
            dict(q="如何证明同一版本两次运行差异可解释？", a="eval_run 要冻结 agent_digest、提示词、工具镜像、模型参数、随机种子、数据集版本和 scorer_version。报告中展示上游 429、超时、裁判不一致和样本级 diff。若这些外因很少但分差仍大，才说明 Agent 本身有非确定性或依赖外部状态。"),
            dict(q="规则打分和 LLM 裁判冲突时听谁的？", a="先按样本的 scoring_rule 定义权威来源。精确答案、JSON 字段、工具调用轨迹这类可确定样本应以规则为准；开放语义题才用裁判。若同时配置两个分数，报告要分别展示，并定义 final_score 的合成权重，不能临场选择好看的结果。"),
            dict(q="baseline 怎么更新？", a="baseline 更新应该是受控操作。只有某个 eval_run 在固定 dataset_version 和 scorer_version 下通过审查，才能写 baseline 表，且保留旧 baseline。更新时记录指标值和阈值，之后候选版本必须和同一版本数据集的 baseline 比较。"),
            dict(q="Runner 沙箱为什么重要？", a="Agent 可能调用工具、读写文件或访问网络，不隔离会污染样本、泄漏数据或让不同样本互相影响。沙箱限制时间、网络、文件和环境变量，并记录工具轨迹，失败时可以回放。这也是可复现的一部分。"),
            dict(q="显著性怎么做，不只是看平均分？", a="可以按 sample_id 做配对比较，统计 win/loss/tie，并对总分差做 bootstrap 置信区间；关键标签单独计算。若平均下降 0.3% 但置信区间跨 0，可能只报警不阻断；若核心标签下降超过阈值，即使总分没降也要阻断。"),
        ],
        variants=[
            "大模型问答系统的离线评测与发布门禁设计。",
            "工具调用 Agent 的轨迹回放和裁判一致性平台。",
            "搜索排序模型的样本集版本化、AB 前离线评测与回归阻断。",
            "代码生成助手的基准集评测、沙箱执行和结果对比平台。",
        ],
    ),
]
