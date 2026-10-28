SYSTEMS = [
    dict(
        id="x4",
        order=4,
        title="大模型网关（多模型路由 + 配额计费）",
        brief="设计一个统一大模型网关，兼顾多模型路由、共享配额、流式低延迟和准确计费。",
        statement="""你要设计一个大模型网关。业务方通过统一的对话补全接口接入，接口形态兼容常见大模型调用习惯：请求里带 model、messages、stream、max_tokens，Header 里带租户应用密钥和请求幂等键。网关背后接多家上游模型和多个上游 key，要按租户、应用、模型能力、价格、健康度、延迟和路由规则选目标；主模型限流、故障或熔断时可以 fallback 到备用模型，但只能在请求边界切换，不能把同一个生成请求切到一半换上游。系统还要做租户 key 和上游 key 管理、审计日志、请求级 usage_record、日账单 billing_daily，以及可选的语义缓存。非功能要求是：同一租户在 8 到 16 个网关实例并发调用时，分钟请求数、每日 token 和金额配额不能超发；流式转发的 P99 额外延迟小于 20ms；客户端断开、上游中断、网关重启时，计费不能多也不能少，并且能解释每一次扣费。""",
        focus="题眼是共享配额、流式低延迟和准确计费三者同时成立：配额扣减必须强一致，流式热路径又不能同步写库，结算必须能从检查点和 usage_record 幂等恢复。",
        scale="假设 2,000 个租户、8,000 个 app_key、30 个逻辑模型、60 个上游 key。峰值 12,000 QPS，其中 35% 是流式；每个请求平均输入 1,200 token、输出 800 token，日可结算 usage_record 8,000 万条，账单明细保留 400 天，流式连接平均持续 45 秒。",
        example="租户 A 配置每分钟 1,000 次请求、每天 500 万 token，同一时刻有 8 个网关实例接入请求。请求 r1 估算 3,200 token，主模型返回 429，网关在请求边界切到备用上游；另一个流式请求 r2 输出到一半客户端断开，已向客户端成功写出 120 个分片、3,840 个输出 token，最终只按已确认输入和已写出输出结算，并释放未使用预占。",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清目标和边界",
                minutes=3,
                prompt="先问清租户层级、配额口径、流式中断计费边界、fallback 条件和延迟口径，不要一上来只画反向代理。",
                points=[
                    "确认租户、应用、逻辑模型、上游 key 的层级关系",
                    "确认配额按请求数、token、金额还是组合限制",
                    "确认流式中断按已发送 token 还是上游最终账单计费",
                    "确认 fallback 只在请求边界发生，不能生成到一半切模型",
                    "确认上游 key 明文不能进日志、上下文和响应",
                    "确认 P99 额外延迟小于 20ms 的测量点",
                ],
                reference="""我会先把语义问清楚。第一，租户下面有多个 app_key，app_key 有模型授权和 QPS 限制；逻辑 model 是产品对外承诺，upstream_key 是实际调用上游的凭据池，两者分离后才能在上游限流时替换 key 或切备用。第二，配额至少有三层：tenant、app_key、model，包含每分钟请求数、每日 token 和每日金额；实时限流要在请求前完成，账单聚合可以异步。第三，流式计费边界要提前定：输入 token 一旦请求发到上游就计入，输出 token 只按网关已经成功写给客户端、且有连续 chunk_seq 检查点的部分计入；只收到上游但还没写给客户端的分片不能收费。第四，fallback 只在请求发起前或上游明确返回 429/5xx 且尚未向客户端输出任何分片时发生；一旦开始输出，模型语义已经绑定，不能中途换模型。第五，额外延迟按网关相对直连上游增加的时间算，首包 P99 增量小于 20ms，分片转发增量 P99 小于 5ms。""",
            ),
            dict(
                key="estimate",
                title="容量估算",
                minutes=4,
                prompt="用规模数字算出 QPS、长连接、token 吞吐、存储量和分片数，并说明这些数字如何改变设计。",
                points=[
                    "峰值 12,000 QPS，流式 4,200 QPS",
                    "45 秒平均流式时长带来约 18.9 万并发连接",
                    "峰值 token 吞吐约 2,400 万 token/s",
                    "usage_record 日写入 8,000 万条，需要按日期和租户分片",
                    "实时配额路径预算 3 到 5ms，不能走数据库行锁",
                    "账单日聚合约 30 万活跃维度行/天",
                ],
                reference="""估算的目的不是炫数字，而是推出哪些组件必须异步、哪些组件必须强一致。峰值 12,000 QPS 中 35% 流式，即 4,200 条新流式请求每秒；平均持续 45 秒，则同时在线流式连接约 18.9 万，Gateway 必须无状态横向扩展，连接层不能依赖单机内存作为权威状态。平均每请求 2,000 token，峰值吞吐约 2,400 万 token/s，如果每个 token 或每个 chunk 同步写 MySQL，数据库和分片延迟都会把首包 P99 打爆，所以热路径只做内存计数和本地顺序日志，按 100ms 或 256 token 批量提交。实时配额必须在 3 到 5ms 内完成，因为它在请求首包前；MySQL 行锁在热点租户下会排队，因此实时余额放 Redis 原子脚本，MySQL 保存规则和最终账本。usage_record 日 8,000 万条，按 bill_date 分区、tenant_id hash 分片；billing_daily 是 tenant/app/model/day 维度，活跃组合约 30 万行/天，可以小时级 upsert、日终 sealed。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出接入、鉴权、路由、配额、流式转发、用量、账单和审计的职责边界。",
                points=[
                    "Gateway 终止协议、保持流式连接、透传分片",
                    "AuthService 校验租户 app_key 和模型授权",
                    "RouteService 选择逻辑模型对应的上游 key 和 fallback",
                    "QuotaService 对多层桶做原子预占、结算释放",
                    "UsageService 幂等写 usage_record 并驱动账单",
                    "BillingJob 从 usage_record 聚合 billing_daily",
                    "AuditLog 记录请求、路由、密钥别名和管理变更",
                ],
                diagram="""flowchart LR
  C["业务客户端"] --> G["网关接入层"]
  G --> A["鉴权服务"]
  G --> R["路由服务"]
  R --> H["健康探测"]
  G --> Q["配额服务"]
  Q --> K["配额KV"]
  Q --> DB["规则库"]
  G --> P["流式代理"]
  P --> U1["上游模型一"]
  P --> U2["上游模型二"]
  P --> UB["用量缓冲"]
  UB --> US["用量服务"]
  US --> B["账单任务"]
  US --> AD["审计日志"]""",
                reference="""服务划分围绕失败模式来定。接入层要保证低延迟，所以 Gateway 只做协议终止、鉴权调用、路由调用、配额预占和字节流转发，不在首包路径同步写账单。AuthService 用 key_hash 查 app_key、tenant 状态和允许模型，结果短缓存 60 秒，但缓存命中也要带版本号，避免禁用 key 后长期有效。RouteService 读取 route_rule、model 价格、upstream_key 健康度和熔断状态，给出 upstream_key_id、fallback_chain 和 route_trace；主模型返回 429 且尚未输出分片时，Gateway 才能按 chain 发起第二次上游请求。QuotaService 是强一致关键路径，用 Redis Lua 一次性检查 tenant/app/model 三类请求桶和 token 桶，任何一个不足则整体不扣。流式代理只把 chunk 透传并写入轻量 UsageBuffer，UsageService 异步落 usage_record；BillingJob 只消费 usage_record 聚合 billing_daily。审计日志不保存密钥明文，只保存 key_alias、规则版本、route_trace 和 request_id，便于追责但不扩大泄露面。""",
            ),
            dict(
                key="tables",
                title="表结构设计",
                minutes=8,
                prompt="设计租户、应用密钥、模型、上游 key、配额、路由、用量和账单表，说明索引服务哪个查询。",
                points=[
                    "tenant 是租户隔离和默认预算边界",
                    "app_key 保存 key_hash 和模型授权，不保存明文",
                    "model 与 upstream_key 分离逻辑模型和物理凭据",
                    "quota_rule 表达 tenant/app/model 的规则作用域",
                    "route_rule 表达优先级、权重、fallback 和熔断阈值",
                    "usage_record 用 request_id 唯一约束保证计费幂等",
                    "billing_daily 用日期、租户、应用、模型唯一聚合",
                ],
                ddl="""CREATE TABLE tenant (
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  tenant_code VARCHAR(64) NOT NULL COMMENT '租户编码',
  tenant_name VARCHAR(128) NOT NULL COMMENT '租户名称',
  status VARCHAR(16) NOT NULL COMMENT 'active/frozen/deleted',
  default_daily_token_limit BIGINT NOT NULL DEFAULT 0 COMMENT '默认每日token上限',
  default_daily_amount_cent BIGINT NOT NULL DEFAULT 0 COMMENT '默认每日金额上限',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (tenant_id),
  UNIQUE KEY uk_tenant_code (tenant_code),
  KEY idx_status_updated (status, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租户表';

CREATE TABLE app_key (
  app_key_id BIGINT NOT NULL COMMENT '应用密钥ID',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  key_hash CHAR(64) NOT NULL COMMENT '密钥哈希',
  app_name VARCHAR(128) NOT NULL COMMENT '应用名称',
  allowed_models JSON NOT NULL COMMENT '允许访问的模型列表',
  status VARCHAR(16) NOT NULL COMMENT 'active/disabled/deleted',
  qps_limit INT NOT NULL DEFAULT 0 COMMENT '应用级QPS限制',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (app_key_id),
  UNIQUE KEY uk_key_hash (key_hash),
  KEY idx_tenant_status (tenant_id, status),
  KEY idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应用密钥表';

CREATE TABLE model (
  model_id BIGINT NOT NULL COMMENT '逻辑模型ID',
  model_code VARCHAR(64) NOT NULL COMMENT '逻辑模型编码',
  capability VARCHAR(64) NOT NULL COMMENT 'chat/embedding/vision',
  input_price_per_1k_cent INT NOT NULL COMMENT '输入每千token价格',
  output_price_per_1k_cent INT NOT NULL COMMENT '输出每千token价格',
  max_context_tokens INT NOT NULL COMMENT '最大上下文token数',
  status VARCHAR(16) NOT NULL COMMENT 'active/offline',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (model_id),
  UNIQUE KEY uk_model_code (model_code),
  KEY idx_capability_status (capability, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='逻辑模型表';

CREATE TABLE upstream_key (
  upstream_key_id BIGINT NOT NULL COMMENT '上游keyID',
  model_id BIGINT NOT NULL COMMENT '逻辑模型ID',
  provider_code VARCHAR(64) NOT NULL COMMENT '抽象上游供应方编码',
  key_alias VARCHAR(64) NOT NULL COMMENT '上游key别名',
  encrypted_key VARCHAR(512) NOT NULL COMMENT '加密后的上游凭据',
  weight INT NOT NULL DEFAULT 100 COMMENT '默认权重',
  status VARCHAR(16) NOT NULL COMMENT 'active/limited/offline',
  p95_latency_ms INT NOT NULL DEFAULT 0 COMMENT '最近P95延迟',
  error_rate_ppm INT NOT NULL DEFAULT 0 COMMENT '错误率百万分比',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (upstream_key_id),
  UNIQUE KEY uk_provider_alias (provider_code, key_alias),
  KEY idx_model_status_latency (model_id, status, p95_latency_ms),
  KEY idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='上游key表';

CREATE TABLE quota_rule (
  quota_rule_id BIGINT NOT NULL COMMENT '配额规则ID',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  app_key_id BIGINT NOT NULL DEFAULT 0 COMMENT '应用密钥ID，0表示租户级',
  model_id BIGINT NOT NULL DEFAULT 0 COMMENT '模型ID，0表示全部模型',
  period_type VARCHAR(16) NOT NULL COMMENT 'minute/day/month',
  request_limit BIGINT NOT NULL DEFAULT 0 COMMENT '周期请求数上限',
  token_limit BIGINT NOT NULL COMMENT '周期token上限',
  amount_limit_cent BIGINT NOT NULL COMMENT '周期金额上限',
  reserve_ratio INT NOT NULL DEFAULT 120 COMMENT '预占比例百分比',
  status VARCHAR(16) NOT NULL COMMENT 'active/disabled',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (quota_rule_id),
  UNIQUE KEY uk_scope_period (tenant_id, app_key_id, model_id, period_type),
  KEY idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配额规则表';

CREATE TABLE route_rule (
  route_rule_id BIGINT NOT NULL COMMENT '路由规则ID',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  app_key_id BIGINT NOT NULL DEFAULT 0 COMMENT '应用密钥ID，0表示租户默认',
  model_id BIGINT NOT NULL COMMENT '逻辑模型ID',
  upstream_key_id BIGINT NOT NULL COMMENT '上游keyID',
  priority INT NOT NULL DEFAULT 100 COMMENT '优先级，数字越小越优先',
  weight INT NOT NULL DEFAULT 100 COMMENT '同优先级权重',
  fallback_enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否允许fallback',
  max_error_rate_ppm INT NOT NULL DEFAULT 50000 COMMENT '最大允许错误率',
  max_p95_latency_ms INT NOT NULL DEFAULT 2000 COMMENT '最大允许P95延迟',
  status VARCHAR(16) NOT NULL COMMENT 'active/disabled',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (route_rule_id),
  UNIQUE KEY uk_route_scope (tenant_id, app_key_id, model_id, upstream_key_id),
  KEY idx_model_status_priority (model_id, status, priority),
  KEY idx_tenant_app (tenant_id, app_key_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='路由规则表';

CREATE TABLE usage_record (
  usage_id BIGINT NOT NULL COMMENT '用量记录ID',
  request_id VARCHAR(96) NOT NULL COMMENT '请求幂等ID',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  app_key_id BIGINT NOT NULL COMMENT '应用密钥ID',
  model_id BIGINT NOT NULL COMMENT '逻辑模型ID',
  upstream_key_id BIGINT NOT NULL COMMENT '上游keyID',
  stream_flag TINYINT NOT NULL COMMENT '是否流式',
  finish_reason VARCHAR(32) NOT NULL COMMENT 'stop/client_abort/upstream_error/timeout',
  input_tokens BIGINT NOT NULL COMMENT '输入token数',
  output_tokens BIGINT NOT NULL COMMENT '输出token数',
  reserved_tokens BIGINT NOT NULL COMMENT '预占token数',
  charged_tokens BIGINT NOT NULL COMMENT '实际计费token数',
  amount_cent BIGINT NOT NULL COMMENT '计费金额',
  first_chunk_latency_ms INT NOT NULL DEFAULT 0 COMMENT '首分片延迟',
  extra_latency_ms INT NOT NULL DEFAULT 0 COMMENT '网关额外延迟',
  bill_date DATE NOT NULL COMMENT '账单日期',
  started_at DATETIME(3) NOT NULL COMMENT '开始时间',
  finished_at DATETIME(3) NOT NULL COMMENT '结束时间',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (usage_id),
  UNIQUE KEY uk_request_id (request_id),
  KEY idx_bill_tenant_app_model (bill_date, tenant_id, app_key_id, model_id),
  KEY idx_tenant_started (tenant_id, started_at),
  KEY idx_finish_reason (finish_reason)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='请求用量记录表';

CREATE TABLE billing_daily (
  bill_id BIGINT NOT NULL COMMENT '日账单ID',
  bill_date DATE NOT NULL COMMENT '账单日期',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  app_key_id BIGINT NOT NULL COMMENT '应用密钥ID',
  model_id BIGINT NOT NULL COMMENT '逻辑模型ID',
  request_count BIGINT NOT NULL COMMENT '请求数',
  stream_count BIGINT NOT NULL COMMENT '流式请求数',
  input_tokens BIGINT NOT NULL COMMENT '输入token汇总',
  output_tokens BIGINT NOT NULL COMMENT '输出token汇总',
  charged_tokens BIGINT NOT NULL COMMENT '计费token汇总',
  amount_cent BIGINT NOT NULL COMMENT '计费金额汇总',
  adjusted_amount_cent BIGINT NOT NULL DEFAULT 0 COMMENT '校准金额',
  status VARCHAR(16) NOT NULL COMMENT 'open/sealed',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (bill_id),
  UNIQUE KEY uk_bill_scope (bill_date, tenant_id, app_key_id, model_id),
  KEY idx_tenant_date (tenant_id, bill_date),
  KEY idx_status_date (status, bill_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日账单表';""",
                reference="""表结构要把配置、凭据、可结算事实和聚合账单分开。tenant 是最高隔离边界，保存状态和默认预算；app_key 只保存 key_hash 和授权范围，不保存明文，因为明文一旦进数据库、日志或截图，泄露面会不可控。model 表描述逻辑能力、价格和上下文上限；upstream_key 表描述实际供应方凭据、健康指标和权重，所以同一个逻辑模型可以挂多个上游 key，某个 key 限流时不影响对外模型名。quota_rule 的唯一键是 tenant_id、app_key_id、model_id、period_type，0 表示通配，查询时从细到粗匹配；实时余额不放 MySQL 表里，是因为热点扣减需要原子 KV 支撑。route_rule 用优先级、权重和熔断阈值表达 fallback 链。usage_record 是请求级事实表，request_id 唯一保证结算、补偿和客户端重试不会重复扣费。billing_daily 只能从 usage_record 聚合生成，不能由网关内存直接写最终金额；sealed 后如需修正，写 adjusted_amount_cent 和原因，不覆盖原始明细。缓存命中结果、提示词原文和上游密钥明文都不应直接放在这些核心表中，最多保存哈希、对象存储引用和审计摘要。""",
            ),
            dict(
                key="api",
                title="接口和事件",
                minutes=5,
                prompt="列出对外调用接口、管理接口、内部配额和用量事件，说明幂等键和返回内容。",
                points=[
                    "POST /v1/chat/completions 同时支持非流式和流式",
                    "X-Request-Id 是端到端计费幂等键",
                    "流式最后事件返回 usage_summary 和 finish_reason",
                    "内部 ReserveQuota/SettleUsage/ReleaseUnused 必须幂等",
                    "管理接口变更 quota_rule 和 route_rule 要带版本",
                    "账单查询按日期、租户、应用、模型维度过滤",
                ],
                reference="""接口分数据面、管理面和内部事件。数据面核心是 POST /v1/chat/completions，请求包含 model、messages、stream、max_tokens、temperature，Header 包含 Authorization 和 X-Request-Id。X-Request-Id 由客户端生成，网关把它贯穿到 quota reservation、route_trace、usage_record 和 audit_log；如果客户端超时重试，同一个 request_id 已经 BILLED，就返回已完成的 usage_summary 或可查询状态，而不是重新扣配额。流式响应用 SSE，每个 data 只放增量内容和 chunk_seq，最后一个 done 事件放 request_id、model、upstream_alias、input_tokens、output_tokens、charged_tokens、finish_reason；如果客户端断开拿不到最后事件，也可以用 GET /v1/usage/{request_id} 查询。管理面有 POST /admin/quota-rules、POST /admin/route-rules、POST /admin/upstream-keys/rotate、GET /admin/billing-daily，所有管理写都带 operator_id、rule_version 和审计原因。内部 RPC 包括 ReserveQuota(request_id, scope, estimated_tokens)、CommitUsage(request_id, actual_tokens, amount)、ReleaseUnused(request_id)、EmitUsageCheckpoint(request_id, chunk_seq, token_delta)，全部以 request_id 幂等，避免重试造成重复扣减。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="描述请求从鉴权、预占、路由、流式转发、结算到补偿的合法状态转换，以及如何只转换一次。",
                points=[
                    "CREATED 完成请求幂等登记但未占配额",
                    "RESERVED 表示三层配额桶原子预占成功",
                    "ROUTED 选定上游 key，开始后不再中途切换",
                    "STREAMING 只记录连续已发送分片用量",
                    "SETTLING 计算实际 token 和金额",
                    "BILLED 幂等写 usage_record 并释放差额",
                    "COMPENSATING 处理重启、中断和未知上游结果",
                    "状态转换用 request_id 唯一键和版本号 CAS 保证一次",
                ],
                diagram="""stateDiagram-v2
  [*] --> CREATED
  CREATED --> REJECTED: 鉴权失败或无权限
  CREATED --> RESERVED: 配额预占成功
  CREATED --> REJECTED: 配额不足
  RESERVED --> ROUTED: 选中上游
  ROUTED --> WAITING: 非流式请求
  ROUTED --> STREAMING: 流式请求
  ROUTED --> RESERVED: 429且未输出时fallback
  STREAMING --> SETTLING: 正常结束
  STREAMING --> SETTLING: 客户端中断
  STREAMING --> COMPENSATING: 网关重启
  WAITING --> SETTLING: 上游返回
  WAITING --> COMPENSATING: 结果未知
  SETTLING --> BILLED: 写入usage_record
  COMPENSATING --> BILLED: 补账成功
  COMPENSATING --> REFUNDED: 无成功证据
  BILLED --> [*]
  REFUNDED --> [*]
  REJECTED --> [*]""",
                reference="""状态机要防止两类事故：重复扣费和未知成本。CREATED 表示网关已经接受 request_id 并完成基础校验，但还没有消耗配额；RESERVED 表示 QuotaService 用原子脚本把 tenant、app_key、model 三个桶一起预占成功，预占记录带 TTL 和 reserved_tokens。ROUTED 表示选定 upstream_key，进入 WAITING 或 STREAMING 后就不能中途换模型；如果主上游返回 429 且尚未向客户端输出任何分片，可以回到 RESERVED 并按 fallback_chain 选择备用上游。STREAMING 时每个分片都有 chunk_seq、output_token_delta、sent_to_client 标记，只有最大连续 sent_to_client=true 的分片进入结算。SETTLING 根据输入 token、连续输出 token、价格和 finish_reason 计算 amount；BILLED 通过 usage_record(request_id) 唯一键只写一次，并调用 ReleaseUnused 释放预占差额。COMPENSATING 用于网关重启或结果未知，先读本地顺序日志、usage checkpoint 和上游可查询结果；无法证明上游成功才 REFUNDED。状态表或 KV 记录带 version，更新时用 compare-and-set，旧实例恢复后如果 version 落后就不能覆盖新状态。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="用时序讲清正常调用、主模型 429 fallback、流式中断计费和账单聚合。",
                points=[
                    "鉴权后先估算 token 并原子预占配额",
                    "路由只选择健康且满足规则的上游 key",
                    "主模型 429 且未输出时在请求边界 fallback",
                    "流式分片先透传再异步记录检查点",
                    "客户端中断后按连续已发送分片结算",
                    "usage_record 幂等写入后释放未使用预占",
                    "billing_daily 从 usage_record 增量聚合",
                ],
                diagram="""sequenceDiagram
  participant C as 客户端
  participant G as 网关
  participant A as 鉴权
  participant R as 路由
  participant Q as 配额
  participant U as 上游模型
  participant S as 备用上游
  participant B as 用量服务
  participant D as 数据库
  C->>G: POST completion + request_id
  G->>A: 校验app_key和模型权限
  A-->>G: tenant/app/model_scope
  G->>Q: reserve三层桶
  Q-->>G: reserved_tokens
  G->>R: choose upstream
  R-->>G: primary + fallback
  G->>U: 发起请求
  U-->>G: 429且未输出
  G->>S: 请求边界fallback
  S-->>G: stream chunks
  G-->>C: 立即透传chunk
  G-->>B: 异步checkpoint
  C-->>G: 连接断开
  G->>B: settle实际token
  B->>D: insert usage_record
  B->>Q: release unused
  B->>D: upsert billing_daily""",
                reference="""这条流程要同时解释低延迟和准确计费。客户端带 request_id 调用后，Gateway 先鉴权，再按输入长度和 max_tokens 估算本次最多消耗多少 token，例如输入 1,200、最大输出 2,000，乘 120% 预占 3,840。QuotaService 在一个原子脚本里检查并扣减 tenant_minute_request、tenant_day_token、app_day_token、model_day_token 等桶，任何一个不足都不扣，因此 8 个实例同时请求也不会先读后写导致超发。路由服务选主上游，主上游返回 429 且尚未输出分片，Gateway 可以在请求边界切备用；如果已经发出任何 chunk，就只能结束当前请求并按失败或中断结算。备用上游开始流式后，Gateway 收到 chunk 先写客户端 socket，再把 chunk_seq 和 token_delta 放进内存队列与本地顺序日志，后台批量提交 UsageService，所以热路径没有数据库往返。客户端中断时，Gateway 根据最大连续 sent_to_client chunk_seq 计算 output_tokens，写 usage_record；如果这一步因重启没完成，补偿任务用本地日志和上游查询恢复。billing_daily 只从 usage_record 增量聚合，避免网关内存计数直接变成账单。""",
            ),
            dict(
                key="reliability",
                title="可靠性方案",
                minutes=5,
                prompt="覆盖选主、幂等、重试退避、故障恢复、兜底巡检、限流隔离、扩展和监控指标。",
                points=[
                    "配额 KV 不可用时 fail-closed，避免超发",
                    "request_id 贯穿预占、结算和 usage_record 幂等",
                    "上游按 429/5xx/超时分类重试和熔断",
                    "流式用量写本地顺序日志，失败后补偿",
                    "账单日终从 usage_record 重算校准",
                    "热点租户按子桶分摊但保持总额度约束",
                    "监控超发、额外延迟、计费误差和补偿积压",
                ],
                reference="""可靠性要围绕三条红线。第一是不超发：配额 KV 或原子脚本不可用时，对消耗配额的请求 fail-closed，只放行健康检查和管理查询；热点租户可以拆 16 或 64 个子桶，但子桶只是总额度切片，不能每个子桶各有一份完整额度，子桶不足时走慢路径再平衡。第二是低延迟：UsageService 队列满时不能阻塞已建立的流式 socket，先降级写本地顺序日志，单机至少保留 30 分钟；如果本地日志也不可写，就拒绝新的流式请求，因为继续服务会让计费不可审计。第三是计费准确：request_id 是唯一事实键，Reserve、Commit、Release 和 usage_record 都幂等；补偿任务扫描 RESERVED 超过 TTL 但无 usage_record 的请求，能找到检查点就结算，找不到成功证据才释放预占。上游错误按类别处理：429 可以换备用，5xx 指数退避并熔断，4xx 参数错误不重试。关键指标包括 quota_oversell_count 必须为 0、stream_extra_latency_p99 小于 20ms、usage_record_duplicate_count 为 0、client_abort_billing_error_rate 小于 0.05%、billing_daily_diff_cent 小于日金额 0.1%、compensation_backlog_age_p99 小于 10 分钟。""",
            ),
        ],
        mistakes=[
            dict(wrong="每个网关实例在本地内存里扣租户配额，定时同步到数据库。", verdict="最大扣分点", why="这和题眼正面冲突。8 个实例会同时看到本地余额充足，先放量后同步必然超发；正确做法是请求前经过共享原子配额服务预占。"),
            dict(wrong="流式请求等完整结束后再记录用量，客户端中断就算失败不计费。", verdict="有错", why="客户端中断前已经消耗上游资源并收到部分输出，完全不计费会形成成本漏洞；应按连续已发送分片和输入 token 结算。"),
            dict(wrong="为了计费准确，每个流式 chunk 都同步插入 MySQL。", verdict="方向对但不准", why="准确性方向对，但同步写库会把每个分片都变成远程事务，P99 额外延迟很难小于 20ms，应使用轻量检查点和批量异步落库。"),
            dict(wrong="主模型生成到一半变慢，就把剩余 token 切到备用模型继续生成。", verdict="搞反", why="生成到一半切模型会破坏语义一致性和审计边界，也难以计费。fallback 只能在请求边界或尚未输出任何分片前发生。"),
            dict(wrong="只保存 billing_daily，不保存请求级 usage_record。", verdict="缺失", why="日账单无法解释单请求争议，也无法支撑幂等补偿和流式中断审计；请求级 usage_record 必须作为账单事实来源。"),
            dict(wrong="把上游 key 明文放在路由规则表和错误日志里，方便排查。", verdict="有错", why="密钥明文进入数据库和日志会扩大泄露面。表里只能放加密凭据或别名，日志记录 key_alias、版本和审计摘要。"),
        ],
        walkthrough="""例子里租户 A 有每分钟 1,000 次请求和每日 500 万 token 两类限制，同一时刻 8 个网关实例收到请求。每个 Gateway 先用 app_key 查到 tenant_id、app_key_id 和模型授权，再根据输入长度与 max_tokens 估算预占 token。请求 r1 估算 3,200 token，QuotaService 用原子脚本同时检查 tenant_minute_request、tenant_day_token、app_day_token 和 model_day_token，按 120% 预占 3,840 token；因为脚本在共享 KV 上串行执行，8 个实例不会各自超发。RouteService 选主 upstream_key，主上游返回 429 且尚未输出分片，Gateway 按 route_rule 选择备用上游重新发起请求，并在 route_trace 里记录原因。请求 r2 是流式，Gateway 收到备用上游分片后先写给客户端，再异步记录 chunk_seq 和 token_delta；写到第 120 个分片后客户端断开，状态进入 SETTLING。UsageService 取最大连续 sent_to_client 的分片，统计输出 3,840 token，加上输入 token 计算 amount，按 request_id 唯一写 usage_record，然后释放 reserved_tokens 与 charged_tokens 的差额。BillingJob 后续只从 usage_record 聚合 billing_daily，所以补偿重跑也不会重复收费。""",
        oral="""我会把这题分成四层讲。第一层是接入和鉴权：业务只看到统一的对话接口，Header 里有 app_key 和 request_id，AuthService 用 key_hash 查租户、应用、模型授权和状态，密钥明文不进日志。第二层是路由：对外的 model 是逻辑模型，内部 route_rule 把它映射到多个 upstream_key，路由看优先级、权重、价格、健康度和延迟；主上游 429 或故障时可以 fallback，但只在尚未输出分片的请求边界切换。第三层是配额和限流：每个请求发往上游前必须按估算 token 做原子预占，QuotaService 用共享 KV 脚本一次性检查 tenant、app、model 三层请求桶和 token 桶，失败整体不扣，所以多实例不会超发。第四层是用量和账单：流式 chunk 到达后先透传给客户端，热路径只做内存计数和本地顺序日志，后台批量写 checkpoint，保证 P99 额外延迟小于 20ms；请求结束或客户端断开后进入结算，按输入 token 和连续已发送输出 token 生成 usage_record，request_id 唯一保证补偿不重复扣费，再释放未使用预占。billing_daily 只能由 usage_record 聚合，日终再 sealed。可靠性上，配额服务不可用就 fail-closed，上游错误按 429、5xx、超时分类退避和熔断，补偿任务扫描 RESERVED 但未 BILLED 的请求。我要盯的指标是 quota_oversell_count 等于 0、stream_extra_latency_p99 小于 20ms、client_abort_billing_error_rate 小于 0.05%、usage_record_duplicate_count 等于 0。""",
        followups=[
            dict(q="为什么不用 MySQL 行锁直接扣配额？", a="MySQL 行锁能保证一致性，但热点租户在 12,000 QPS 峰值下会把 tenant 或 app 的余额行打成串行锁，首包前等待直接放大流式延迟。更合适的是规则和审计放 MySQL，实时余额放共享 KV 原子脚本；KV 失败时 fail-closed，后台用 usage_record 和规则表对账。"),
            dict(q="预占后网关崩溃，额度会不会永远丢失？", a="预占记录要带 request_id、reserved_tokens、状态和 TTL，例如 2 小时。补偿任务扫描 RESERVED 且没有 usage_record 的请求，能从检查点或上游查询证明已有输出就结算，无法证明成功才释放预占。这样短期冻结额度，但不会永久丢失，也不会为了可用性放开超发。"),
            dict(q="流式中断到底按什么边界计费？", a="边界是已经成功写给客户端、且 chunk_seq 连续的输出分片，加上已经发送给上游的输入 token。只收到上游但还没写出 socket 的 chunk 不算 sent_to_client；已经写出并有检查点的 chunk 要计费。这个口径能同时解释客户端断网、上游异常和网关重启。"),
            dict(q="如何证明额外延迟 P99 小于 20ms？", a="需要在 Gateway 入口、上游请求发出、上游首分片到达、客户端首分片写出四个点打时间戳。额外延迟按模型、上游 key、租户分桶统计。热路径只做内存计数、队列入队和顺序日志，不做同步数据库和远程账单调用，才能稳定压住 P99。"),
            dict(q="上游最终 usage 和本地 tokenizer 不一致怎么办？", a="正常完成时优先采用上游最终 usage；流式中断没有最终 usage 时使用与该模型绑定的 tokenizer 估算，并标记 estimate_flag。若后续上游可查询到最终 usage，补偿任务写 adjusted 字段和原因，不静默覆盖原始 usage_record。"),
            dict(q="热点租户的配额 key 压力太高怎么办？", a="可以把租户日桶拆成 16 或 64 个子桶，请求按 request_id 哈希到子桶；但子桶只是总额度切片，不能各自拥有完整额度。子桶不足时走慢路径申请再平衡，保证吞吐提升不破坏总额度不超发。"),
            dict(q="缓存命中还要扣费吗？", a="这取决于产品规则，但必须在 quota_rule 和 billing 里显式表达。通常缓存命中可以不扣上游成本或按较低价格扣平台服务费；无论哪种，都要写 usage_record，标记 cache_hit、charged_tokens 和 amount，否则日账单和审计会少一类事实。"),
            dict(q="管理面改路由规则如何避免旧规则继续放量？", a="管理接口写 MySQL 时生成递增 rule_version，并发布变更事件。Gateway 和 RouteService 本地缓存一般 30 秒，但每次 ReserveQuota 带版本；如果缓存版本落后超过阈值，高风险请求拒绝或强制刷新。这样兼顾热路径性能和规则收敛。"),
        ],
        variants=[
            "统一模型代理平台：多个业务团队共用模型额度，要求按部门出账。",
            "推理 API 商业化网关：支持预付费额度、后付费账单和上游供应方熔断。",
            "多供应方文本生成服务：主供应方限流时自动切备用，但要求请求级审计可解释。",
            "带语义缓存的大模型调用层：缓存命中、真实上游调用和中断请求要分开计费。",
        ],
    ),
    dict(
        id="x5",
        order=5,
        title="Agent 运行时平台（Session / Turn / Tool / Sandbox）",
        brief="设计一个 Agent 运行时，支持长会话、每轮多次工具调用、沙箱执行、事件流重连和无损续跑。",
        statement="""你要设计一个 Agent 运行时平台。用户创建一个 Agent 会话，随后每一轮 Turn 输入自然语言任务；模型在一轮 Turn 内可以多次调用工具，工具可能是读操作、写操作或代码执行，代码执行必须放在沙箱中。前端通过事件流看到模型输出、工具调用、工具结果和最终回答；网络断开后要能按 last_event_id 重连并补发。用户可以中断、取消或续跑会话；平台滚动发布、实例重启、worker 崩溃后，几小时长会话和上百个 Turn 不能丢进度。多租户之间要资源隔离，单租户不能占满沙箱和 worker。题眼不是“能聊天”，而是第 37 个 Turn 里已经成功执行了一个有副作用工具后，运行时实例发布重启，恢复时不能重复创建资源，也不能把事件顺序补乱。""",
        focus="题眼是长会话无损恢复和工具副作用幂等：权威状态必须在 session、turn、event_log、tool_call、sandbox_lease、checkpoint 中可重建，worker 只能持有短租约执行权。",
        scale="假设日活用户 20 万，峰值 5 万个活跃 session；普通 session 平均 30 个 Turn，长 session 可持续 3 小时、超过 120 个 Turn。峰值 800 Turn/s，每个 Turn 平均 15 条事件、3 次工具调用、1 次 checkpoint；事件热存 7 天、冷归档 90 天，实例重启后 60 秒内恢复。",
        example="用户在第 37 个 Turn 输入“创建工单并发送通知”。模型先调用 create_ticket，工具成功返回 ticket_id 后，运行时实例因为发布重启；第二个 send_notice 还没执行。新实例接管 session 后，要从 checkpoint 和 event_log 恢复：create_ticket 不能重复执行，前端重连后能补发第 37 轮已发生事件，并继续执行 send_notice。",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清语义和边界",
                minutes=3,
                prompt="先确认会话顺序、工具副作用、事件补发、取消语义、沙箱隔离和恢复目标。",
                points=[
                    "确认同一 session 内 Turn 是否串行",
                    "确认工具分读、写、危险操作，哪些需要人工确认",
                    "确认事件流断线后按 seq 补发，客户端按 seq 去重",
                    "确认取消是协作取消还是强杀沙箱",
                    "确认沙箱是否允许出网、文件持久化和凭据注入",
                    "确认恢复 RTO、事件 RPO 和副作用重复率目标",
                ],
                reference="""我会先把承诺说清楚。同一 session 内 Turn 默认串行，因为消息上下文和工具结果有顺序依赖；不同 session 可以并行，同一租户受资源配额限制。工具要分级：读工具可以自动重试，写工具必须有 idempotency_key，危险工具要 dry-run 或人工确认；模型不能绕过权限直接拿平台超级凭据。事件流是服务端权威事件日志的投影，客户端断线后用 last_event_id 或 last_seq 重连，服务端从 event_log 补发，客户端按 seq 去重。取消语义也要收敛：已发起的外部副作用不能假装撤回，只能记录 cancel_requested，并在可中断点停止后续步骤。沙箱默认无持久身份，凭据通过短期令牌或出口代理注入，租户之间文件系统、网络、CPU、内存隔离。恢复目标是实例异常后 60 秒内从 checkpoint 继续，event_log 已提交事件 RPO 为 0，工具副作用重复率小于 0.001%。""",
            ),
            dict(
                key="estimate",
                title="容量估算",
                minutes=4,
                prompt="估算 Turn QPS、事件写入、checkpoint 体积、worker 和沙箱数量，并说明分片策略。",
                points=[
                    "峰值 800 Turn/s，每 Turn 平均 15 条事件",
                    "event_log 写入约 12,000 rows/s，热数据约 1.6TB/天",
                    "每 Turn 3 次工具调用，tool_call 写入约 2,400 rows/s",
                    "平均 Turn 执行 20 秒，需要约 16,000 并发执行槽",
                    "30% Turn 需要沙箱、平均 90 秒，需约 21,600 个沙箱租约",
                    "checkpoint 大对象放对象存储，表里只放引用和哈希",
                ],
                reference="""规模估算直接决定存储和调度方式。峰值 800 Turn/s，每个 Turn 平均 15 条事件，event_log 写入约 12,000 rows/s；按每条事件 1.5KB 算，每天热事件约 1.6TB，必须按 session_id hash 分片，并按 created_at 做冷热分层。每个 Turn 平均 3 次工具调用，tool_call 约 2,400 rows/s，唯一键冲突是正常恢复路径，索引要能支撑按 idempotency_key 查询。平均 Turn 执行 20 秒，峰值需要 16,000 个并发执行槽；如果单 worker 稳定承载 80 个并发 Turn，基础需要 200 台，预留 30% 发布和故障容量后约 260 台。30% Turn 需要沙箱、平均持有 90 秒，则并发 sandbox_lease 约 800 * 0.3 * 90 = 21,600 个，必须租约化和限流，不能每个 session 常驻沙箱。checkpoint 每 Turn 至少一次，如果压缩后 20KB，每天约 1.4TB，MySQL 只保存 blob_ref、hash、event_seq 和 state_version，避免大字段拖慢事务。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出 Gateway、Session、Turn、Worker、Tool、Sandbox、Event、Checkpoint 的职责与通信。",
                points=[
                    "Gateway 做鉴权、租户限流、SSE 连接和请求幂等",
                    "SessionService 管理 session 状态、owner lease 和 fencing token",
                    "TurnService 分配 turn_seq、入队并保证同 session 串行",
                    "Worker 执行模型循环、工具编排和 checkpoint",
                    "ToolService 管理工具幂等、权限和结果缓存",
                    "SandboxManager 管理沙箱租约、续租、回收和隔离",
                    "EventLogService 负责 append-only 事件和断线补发",
                    "CheckpointService 保存可恢复状态快照",
                ],
                diagram="""flowchart LR
  C["前端"] --> G["运行时网关"]
  G --> SS["会话服务"]
  G --> TS["回合服务"]
  TS --> Q["会话队列"]
  Q --> W["执行器"]
  W --> TO["工具服务"]
  W --> SM["沙箱管理"]
  W --> CP["快照服务"]
  W --> EL["事件日志"]
  EL --> DB["状态库"]
  CP --> OB["对象存储"]
  TO --> XT["外部工具"]
  SM --> SP["沙箱池"]
  G --> ES["事件流"]
  ES --> EL""",
                reference="""服务拆分的依据是恢复边界。Runtime Gateway 是无状态入口，负责鉴权、租户限流、POST turn 幂等和 SSE 连接；它可以重启，因为权威事件在 EventLogService。SessionService 管理 session 生命周期、owner_instance_id、owner_token 和 lease_until；同一 session 任意时刻只有一个有效 owner，避免两个 worker 同时写消息。TurnService 在事务里分配 turn_seq、写 TURN_ACCEPTED 事件并入队，保证同 session Turn 顺序。Worker 是可替换执行者，拿到 owner lease 后执行模型循环，遇到工具调用交给 ToolService 登记幂等记录，遇到代码执行向 SandboxManager 申请 sandbox_lease，每个重要边界写 checkpoint。EventLogService 是 append-only，提供 next_seq 分配、批量写入和按 after_seq 补发；CheckpointService 把大状态写对象存储并保存 hash。ToolService 不直接相信模型请求，先做权限校验和参数规范化，再用 idempotency_key 防重复副作用。SandboxManager 用 lease 和心跳管理沙箱，实例死掉后按过期租约回收。""",
            ),
            dict(
                key="tables",
                title="表结构设计",
                minutes=8,
                prompt="设计 session、turn、message/event_log、tool_call、sandbox_lease、checkpoint 等表，并说明唯一键服务的并发语义。",
                points=[
                    "agent_session 保存 owner lease、fencing token 和水位",
                    "agent_turn 保存 turn_seq、request_id 和状态",
                    "message 保存最终消息，event_log 保存可补发事件",
                    "event_log 用 (session_id, seq) 唯一保证会话事件全序",
                    "tool_call 用 idempotency_key 唯一保证副作用不重复",
                    "sandbox_lease 用 lease_until 支撑回收和接管",
                    "checkpoint 用 state_version 和 event_seq 支撑恢复",
                ],
                ddl="""CREATE TABLE agent_session (
  id BIGINT NOT NULL COMMENT '自增ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  tenant_id VARCHAR(64) NOT NULL COMMENT '租户ID',
  user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
  status VARCHAR(32) NOT NULL COMMENT 'ACTIVE/DRAINING/CLOSED',
  owner_instance_id VARCHAR(128) DEFAULT NULL COMMENT '当前owner实例',
  owner_token BIGINT NOT NULL DEFAULT 0 COMMENT 'fencing token',
  owner_lease_until DATETIME(3) DEFAULT NULL COMMENT 'owner租约到期时间',
  last_turn_seq BIGINT NOT NULL DEFAULT 0 COMMENT '最后turn序号',
  last_event_seq BIGINT NOT NULL DEFAULT 0 COMMENT '最后事件序号',
  ack_event_seq BIGINT NOT NULL DEFAULT 0 COMMENT '客户端确认水位',
  checkpoint_id VARCHAR(64) DEFAULT NULL COMMENT '最新checkpoint',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_session_id (session_id),
  KEY idx_tenant_user (tenant_id, user_id),
  KEY idx_owner_lease (owner_instance_id, owner_lease_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话表';

CREATE TABLE agent_turn (
  id BIGINT NOT NULL COMMENT '自增ID',
  turn_id VARCHAR(64) NOT NULL COMMENT '回合ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  turn_seq BIGINT NOT NULL COMMENT '会话内turn序号',
  request_id VARCHAR(128) NOT NULL COMMENT '客户端幂等ID',
  status VARCHAR(32) NOT NULL COMMENT 'QUEUED/RUNNING/WAITING_TOOL/CHECKPOINTED/SUCCEEDED/FAILED',
  input_hash CHAR(64) NOT NULL COMMENT '输入哈希',
  worker_instance_id VARCHAR(128) DEFAULT NULL COMMENT '执行实例',
  started_at DATETIME(3) DEFAULT NULL COMMENT '开始时间',
  finished_at DATETIME(3) DEFAULT NULL COMMENT '结束时间',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_turn_id (turn_id),
  UNIQUE KEY uk_session_turn_seq (session_id, turn_seq),
  UNIQUE KEY uk_session_request (session_id, request_id),
  KEY idx_session_status (session_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回合表';

CREATE TABLE message (
  id BIGINT NOT NULL COMMENT '自增ID',
  message_id VARCHAR(64) NOT NULL COMMENT '消息ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  turn_id VARCHAR(64) NOT NULL COMMENT '回合ID',
  seq BIGINT NOT NULL COMMENT '消息序号',
  role VARCHAR(32) NOT NULL COMMENT 'user/assistant/tool/system',
  content MEDIUMTEXT NOT NULL COMMENT '消息内容',
  content_hash CHAR(64) NOT NULL COMMENT '内容哈希',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_message_id (message_id),
  UNIQUE KEY uk_message_session_seq (session_id, seq),
  KEY idx_message_turn (turn_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='最终消息表';

CREATE TABLE event_log (
  id BIGINT NOT NULL COMMENT '自增ID',
  event_id VARCHAR(64) NOT NULL COMMENT '事件ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  turn_id VARCHAR(64) DEFAULT NULL COMMENT '回合ID',
  seq BIGINT NOT NULL COMMENT '会话内事件序号',
  event_type VARCHAR(64) NOT NULL COMMENT '事件类型',
  payload_json JSON NOT NULL COMMENT '事件载荷',
  payload_hash CHAR(64) NOT NULL COMMENT '载荷哈希',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_event_id (event_id),
  UNIQUE KEY uk_event_session_seq (session_id, seq),
  KEY idx_event_turn (turn_id),
  KEY idx_event_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='事件日志表';

CREATE TABLE tool_call (
  id BIGINT NOT NULL COMMENT '自增ID',
  tool_call_id VARCHAR(64) NOT NULL COMMENT '工具调用ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  turn_id VARCHAR(64) NOT NULL COMMENT '回合ID',
  tool_name VARCHAR(128) NOT NULL COMMENT '工具名称',
  idempotency_key VARCHAR(160) NOT NULL COMMENT '工具幂等键',
  status VARCHAR(32) NOT NULL COMMENT 'REGISTERED/RUNNING/SUCCEEDED/FAILED/UNKNOWN',
  request_hash CHAR(64) NOT NULL COMMENT '规范化参数哈希',
  result_ref VARCHAR(512) DEFAULT NULL COMMENT '结果引用',
  result_hash CHAR(64) DEFAULT NULL COMMENT '结果哈希',
  error_code VARCHAR(64) DEFAULT NULL COMMENT '错误码',
  attempt_count INT NOT NULL DEFAULT 0 COMMENT '尝试次数',
  lease_until DATETIME(3) DEFAULT NULL COMMENT '执行租约到期时间',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_tool_call_id (tool_call_id),
  UNIQUE KEY uk_tool_idempotency_key (idempotency_key),
  KEY idx_tool_turn (turn_id),
  KEY idx_tool_status_lease (status, lease_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工具调用表';

CREATE TABLE sandbox_lease (
  id BIGINT NOT NULL COMMENT '自增ID',
  lease_id VARCHAR(64) NOT NULL COMMENT '租约ID',
  sandbox_id VARCHAR(64) NOT NULL COMMENT '沙箱ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  turn_id VARCHAR(64) DEFAULT NULL COMMENT '回合ID',
  owner_instance_id VARCHAR(128) NOT NULL COMMENT '持有实例',
  owner_token BIGINT NOT NULL COMMENT 'fencing token',
  status VARCHAR(32) NOT NULL COMMENT 'LEASED/EXTENDING/RECLAIMING/RELEASED',
  lease_until DATETIME(3) NOT NULL COMMENT '租约到期时间',
  resource_spec_json JSON NOT NULL COMMENT '资源规格',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  updated_at DATETIME(3) NOT NULL COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_lease_id (lease_id),
  KEY idx_sandbox_session (session_id),
  KEY idx_sandbox_status_lease (status, lease_until),
  KEY idx_sandbox_id_status (sandbox_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='沙箱租约表';

CREATE TABLE checkpoint (
  id BIGINT NOT NULL COMMENT '自增ID',
  checkpoint_id VARCHAR(64) NOT NULL COMMENT '快照ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
  turn_id VARCHAR(64) NOT NULL COMMENT '回合ID',
  event_seq BIGINT NOT NULL COMMENT '快照覆盖到的事件序号',
  state_version BIGINT NOT NULL COMMENT '状态版本',
  blob_ref VARCHAR(512) NOT NULL COMMENT '快照对象存储引用',
  blob_hash CHAR(64) NOT NULL COMMENT '快照哈希',
  created_at DATETIME(3) NOT NULL COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_checkpoint_id (checkpoint_id),
  UNIQUE KEY uk_checkpoint_session_version (session_id, state_version),
  KEY idx_checkpoint_turn (turn_id),
  KEY idx_checkpoint_session_event (session_id, event_seq)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='恢复快照表';""",
                reference="""这些表的核心是让运行时状态可重建。agent_session 保存 owner lease、fencing token 和事件水位，worker 重启后其他实例可以通过 owner_lease_until 过期接管；owner_token 防止旧实例恢复后覆盖新实例。agent_turn 用 (session_id, turn_seq) 保证会话内顺序，用 (session_id, request_id) 保证客户端重试不会创建两个 Turn。message 是最终对话视图，event_log 是恢复和补发依据，(session_id, seq) 唯一保证同一会话事件全序；事件必须先落库再推送，否则客户端看到的进度无法补发。tool_call 的 idempotency_key 是防重复副作用的关键，应该由 tenant、session、turn、tool、规范化参数哈希和业务 key 组成，不能用随机数。sandbox_lease 通过 lease_until 和 status 让孤儿沙箱可回收，也避免短暂网络抖动时误杀。checkpoint 存 event_seq、state_version、blob_ref 和 hash，恢复时只加载最新完整快照，再从 event_log 补齐后续事件。大模型上下文裁剪结果、沙箱大文件和工具大结果不应直接塞进 MySQL 行，应放对象存储并保存引用和哈希。""",
            ),
            dict(
                key="api",
                title="接口和事件",
                minutes=5,
                prompt="定义创建会话、提交 Turn、事件流重连、取消、工具回调和沙箱续租接口。",
                points=[
                    "POST /sessions 创建会话并初始化事件水位",
                    "POST /sessions/{id}/turns 用 request_id 幂等提交输入",
                    "GET /sessions/{id}/events?after_seq=N 补发事件",
                    "POST /sessions/{id}/cancel 记录取消意图",
                    "ToolService RegisterToolCall 先登记幂等再执行",
                    "Sandbox heartbeat 续租并携带 owner_token",
                ],
                reference="""API 要把“请求已接收”和“任务已完成”区分开。POST /sessions 创建会话，返回 session_id、initial_seq 和租户资源配额；POST /sessions/{session_id}/turns 提交一轮输入，Header 或 body 里必须有 request_id，服务端用 (session_id, request_id) 去重，返回 turn_id 只表示已进入 QUEUED。GET /sessions/{session_id}/events?after_seq=N 是 SSE 或长轮询补发接口，服务端从 event_log 找 seq>N 的连续事件；如果 after_seq 早于保留窗口，返回需要加载 message 快照的错误码，而不是假装补发成功。POST /sessions/{session_id}/cancel 写入 cancel_requested 事件，worker 在模型调用间、工具调用前和沙箱命令间检查它；已经完成的工具副作用不撤销。内部接口 RegisterToolCall(turn_id, tool_name, normalized_args_hash, idempotency_key) 先插入 tool_call，冲突则返回旧状态；CompleteToolCall 只允许持有 lease 的执行者写结果。SandboxHeartbeat(lease_id, owner_token) 续租，token 不匹配就拒绝，防止旧 worker 复活后继续写。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=6,
                prompt="画出 session、turn、tool_call、sandbox_lease 的状态和合法转换，并说明并发下如何只转换一次。",
                points=[
                    "Session 在 ACTIVE、DRAINING、CLOSED 间转换",
                    "Turn 在 QUEUED、RUNNING、WAITING_TOOL、CHECKPOINTED、SUCCEEDED、FAILED 间转换",
                    "ToolCall 在 REGISTERED、RUNNING、SUCCEEDED、FAILED、UNKNOWN 间转换",
                    "SandboxLease 在 LEASED、EXTENDING、RECLAIMING、RELEASED 间转换",
                    "状态更新用 owner_token、version 或租约 CAS",
                    "UNKNOWN 工具不能盲目重试，必须先对账",
                ],
                diagram="""stateDiagram-v2
  [*] --> ACTIVE
  ACTIVE --> DRAINING: 发布或空闲回收
  DRAINING --> ACTIVE: 新owner接管
  DRAINING --> CLOSED: 用户关闭或过期
  [*] --> QUEUED
  QUEUED --> RUNNING: 获得owner租约
  RUNNING --> WAITING_TOOL: 工具已登记
  WAITING_TOOL --> RUNNING: 工具结果已落库
  RUNNING --> CHECKPOINTED: 快照已保存
  CHECKPOINTED --> SUCCEEDED: 最终消息已保存
  RUNNING --> FAILED: 不可重试错误
  FAILED --> QUEUED: 可重试且有快照
  [*] --> REGISTERED
  REGISTERED --> RUNNING: 持有工具租约
  RUNNING --> SUCCEEDED: 结果落库
  RUNNING --> FAILED: 明确失败
  RUNNING --> UNKNOWN: 副作用边界崩溃
  UNKNOWN --> SUCCEEDED: 对账发现成功
  UNKNOWN --> FAILED: 对账确认无效果
  [*] --> LEASED
  LEASED --> EXTENDING: 心跳续租
  EXTENDING --> LEASED: 续租成功
  LEASED --> RECLAIMING: 租约过期
  RECLAIMING --> RELEASED: 清理完成""",
                reference="""状态机是恢复协议。Session ACTIVE 表示可接收 Turn；发布时进入 DRAINING，Gateway 不再把新 Turn 分配给旧 owner，但旧 owner 可以在短时间内完成当前 step 并写 checkpoint；超时后租约过期，新 owner 接管再回 ACTIVE。Turn 从 QUEUED 到 RUNNING 必须先拿到 session owner lease；进入 WAITING_TOOL 前必须已经写 tool_call REGISTERED 事件；工具结果落库后回 RUNNING；每完成一个不可重复阶段写 CHECKPOINTED，最终消息和 TURN_SUCCEEDED 事件都落库后才 SUCCEEDED。ToolCall 是防副作用重复的核心：REGISTERED 表示幂等行已存在但未发起外部副作用；RUNNING 表示可能已经发起；如果 worker 在副作用边界崩溃，状态变 UNKNOWN，新 worker 不能直接重试，必须用业务 key 查询外部权威状态，查到成功就补 SUCCEEDED，查不到且工具语义允许才重试。SandboxLease 用 lease_until 控制回收，清理器只处理过期且 token 失效的租约。所有转换用 where status=old_status and owner_token=token 或 version=old_version 的 CAS，保证并发下只有一个执行者推进状态。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=7,
                prompt="按第 37 个 Turn 的例子，讲提交、工具调用、实例重启、事件补发和续跑。",
                points=[
                    "提交 Turn 时先写 agent_turn 和 TURN_ACCEPTED 事件",
                    "worker 获取 session owner lease 后才能执行",
                    "工具调用先 register idempotency_key 再执行副作用",
                    "工具成功后先持久化 result_ref 再写事件和 checkpoint",
                    "实例重启后新 worker 抢占 owner 并加载 checkpoint",
                    "事件流按 after_seq 补发，客户端按 seq 去重",
                    "已成功工具复用结果，未执行工具继续执行",
                ],
                diagram="""sequenceDiagram
  participant C as 前端
  participant G as 网关
  participant T as 回合服务
  participant E as 事件日志
  participant W as 执行器
  participant O as 工具服务
  participant S as 沙箱管理
  participant P as 快照服务
  C->>G: POST turn request_id
  G->>T: create turn if absent
  T->>E: append TURN_ACCEPTED seq37
  T-->>C: turn_id
  W->>T: acquire owner token7
  W->>E: append TURN_STARTED
  W->>O: register create_ticket key1
  O-->>W: RUNNING lease
  W->>O: complete create_ticket result
  W->>P: save checkpoint event_seq
  W->>E: append TOOL_SUCCEEDED
  W->>S: renew sandbox lease
  W-->>G: instance restarting
  C->>G: reconnect after_seq
  G->>E: replay missing events
  W->>T: new owner token8
  W->>O: load key1 result
  W->>O: register send_notice key2
  O-->>W: execute once""",
                reference="""以第 37 个 Turn 为例。前端提交“创建工单并发送通知”，Gateway 用 request_id 调 TurnService；TurnService 在一个事务里写 agent_turn、分配 turn_seq=37，并追加 TURN_ACCEPTED 事件。Worker 拿到 session owner token=7 后开始执行，模型决定先调用 create_ticket。ToolService 先插入 tool_call，idempotency_key 由 session、turn、tool、业务参数哈希组成；插入成功后才真正调用外部工具。create_ticket 成功返回 ticket_id 后，ToolService 先把 result_ref 和 result_hash 写入 tool_call=SUCCEEDED，Worker 再保存 checkpoint，checkpoint.event_seq 覆盖到 TOOL_SUCCEEDED 前后，并追加事件。此时实例发布重启，send_notice 还没执行。新实例发现 owner_lease_until 过期，用 token=8 接管 session，读取最新 checkpoint 和 event_log；看到 create_ticket 已 SUCCEEDED，就把 ticket_id 作为已完成工具结果放回模型上下文，不再次调用 create_ticket。前端用 after_seq 重连，EventLogService 补发第 37 轮缺失事件；客户端按 seq 去重，所以旧连接收到过的事件不会重复展示。随后 worker 登记 send_notice 的 idempotency_key 并执行一次，最终写 MESSAGE_DELTA、TURN_SUCCEEDED 和 checkpoint。""",
            ),
            dict(
                key="reliability",
                title="可靠性方案",
                minutes=5,
                prompt="覆盖选主租约、幂等、重试退避、故障恢复、巡检、限流隔离、扩展和监控。",
                points=[
                    "session 单 owner lease 加 fencing token，防双写",
                    "tool_call 幂等键和 UNKNOWN 对账防重复副作用",
                    "event_log 先落库再推送，断线按 seq 补发",
                    "checkpoint 保存到对象存储并校验 hash",
                    "沙箱按租约回收，租户资源限流隔离",
                    "发布先 drain 再停止续租，60 秒内接管",
                    "监控恢复成功率、事件缺口、副作用重复和沙箱泄漏",
                ],
                reference="""可靠性方案要接受一个取舍：为了不重复副作用，某些未知状态要暂停对账，而不是盲目重试。选主上，同一 session 只有一个 owner lease，写 event_log、turn 状态和 checkpoint 都带 owner_token；旧实例恢复后 token 落后会被拒绝。幂等上，Turn 用 (session_id, request_id) 去重，Tool 用 idempotency_key 去重，外部工具如果没有查询接口或自身幂等键，就不能被标为自动安全重试。重试上，模型超时可以指数退避重试，读工具可重试，写工具必须先查 tool_call；UNKNOWN 超过 5 分钟告警并暂停同类工具。故障恢复上，EventLogService 先落库再推送，checkpoint blob 写入后校验 hash，再提交 checkpoint 行；恢复时加载最新 checkpoint，并从 event_seq 后重放事件。沙箱按租约和心跳续租，过期 2 个周期后进入 RECLAIMING；每租户限制 worker 并发、沙箱数量、CPU、内存和出网域名，防止单租户拖垮全局。发布时每批 drain 不超过 10% worker，20 秒内写 checkpoint，30 秒后停止续租让新实例接管。监控指标包括 recovery_success_rate 大于 99.99%、event_seq_gap_count 为 0、duplicated_tool_effect_rate 小于 0.001%、expired_sandbox_reclaim_p99 小于 120 秒、rollout_turn_fail_increase 小于 0.1%。""",
            ),
        ],
        mistakes=[
            dict(wrong="只把最终回答保存到 message 表，中间 tool_call 和事件不用存。", verdict="最大扣分点", why="这会导致重启后不知道工具是否已经执行，尤其写工具成功后崩溃会重复副作用；必须保存事件、工具状态和 checkpoint。"),
            dict(wrong="实例重启后从用户输入重新跑一遍第 37 个 Turn。", verdict="有错", why="重新跑会再次调用已经成功的 create_ticket，造成重复工单。正确做法是从 checkpoint 和 tool_call 结果恢复，只继续未完成步骤。"),
            dict(wrong="SSE 断线后让前端刷新整个页面，不需要补发事件。", verdict="缺失", why="刷新页面只能看到最终消息，丢失工具执行进度和审计链；长会话必须按 event_log 的 session_id、seq 补发并去重。"),
            dict(wrong="工具调用的 idempotency_key 用随机 UUID，每次重试生成新的。", verdict="搞反", why="随机键无法把同一业务副作用合并，重试会变成新请求；幂等键应由会话、回合、工具、参数哈希和业务 key 稳定生成。"),
            dict(wrong="同一个 session 的多个 Turn 可以随便并行执行，提高吞吐。", verdict="方向对但不准", why="不同 session 可以并行，但同一 session 消息上下文有顺序依赖；随便并行会让工具结果、消息和 checkpoint 顺序错乱。"),
            dict(wrong="worker 持有沙箱进程，worker 死了就让沙箱自然退出，不用表记录。", verdict="缺失", why="沙箱是昂贵且有隔离风险的资源，worker 死亡可能遗留进程和文件；必须有 sandbox_lease、心跳和过期回收。"),
        ],
        walkthrough="""第 37 个 Turn 的流程是：前端提交 request_id=r37，TurnService 用 (session_id, request_id) 幂等创建 agent_turn，并写 TURN_ACCEPTED(seq=3701)。Worker 获得 session owner_token=7 后写 TURN_STARTED，模型决定先执行 create_ticket。ToolService 规范化参数，生成 idempotency_key=hash(session,37,create_ticket,args,business_key)，插入 tool_call=REGISTERED，成功后才调用外部工具；工具返回 ticket_id 后，先把 tool_call 更新为 SUCCEEDED、保存 result_ref，再写 TOOL_SUCCEEDED 事件和 checkpoint。此时旧实例发布重启，send_notice 尚未登记。新实例等 owner_lease_until 过期后用 token=8 接管，加载 checkpoint 和 event_log，发现 create_ticket 已成功，于是把 ticket_id 作为既有工具结果放入模型上下文，而不是再次调用。前端重连带 after_seq=3701，EventLogService 补发 TOOL_RUNNING、TOOL_SUCCEEDED、CHECKPOINT_SAVED 等事件；客户端按 seq 去重。随后 Worker 登记 send_notice 的幂等键并执行，写 TOOL_SUCCEEDED、最终 assistant message 和 TURN_SUCCEEDED。这样用户看到连续进度，平台没有重复创建工单。""",
        oral="""我会把 Agent 运行时分成控制面、执行面、事件面和隔离面。控制面里，SessionService 保存 session 状态、owner lease 和 fencing token，TurnService 用 request_id 幂等创建 Turn 并分配 turn_seq，同一 session 默认串行执行。执行面里，Worker 只是临时 owner，不是权威状态；它执行模型循环，遇到工具调用先找 ToolService 登记 idempotency_key，登记成功才执行副作用，工具成功后先把 result_ref 落库，再写事件和 checkpoint。事件面里，EventLogService 是 append-only，每个 session 有单调 seq，事件先落库再通过 SSE 推给前端；断线重连时客户端带 after_seq，服务端补发连续事件，客户端按 seq 去重。隔离面里，SandboxManager 给代码执行分配 sandbox_lease，心跳续租，过期回收，并按租户限制 CPU、内存、并发和出网。恢复流程是这题核心：实例发布或崩溃后，新 worker 等租约过期，用更大的 owner_token 接管，加载最新 checkpoint，再从 event_log 重放后续事件；已经 SUCCEEDED 的 tool_call 直接复用结果，UNKNOWN 的写工具先对账，未登记的工具才继续执行。代价是所有关键步骤都要落事件和快照，延迟和存储成本会上升；兜底是事件热存 7 天、checkpoint 大对象放对象存储、后台巡检 RUNNING 但租约过期的 turn 和 sandbox。指标上看 recovery_success_rate、event_seq_gap_count、duplicated_tool_effect_rate、checkpoint_save_p99、expired_sandbox_reclaim_p99 和发布期间 Turn 失败增量。""",
        followups=[
            dict(q="模型调用本身没有幂等键，恢复时要不要重调模型？", a="模型输出通常不保证同输入同输出，所以已落库的模型 delta 和 tool_call 决策要复用。只有模型调用还没有产生可见事件、没有发起工具副作用，并且 checkpoint 表明可安全重试时，才允许重新调用模型。否则恢复要从事件日志构造已有上下文继续。"),
            dict(q="工具成功了但 worker 在写本地结果前崩溃怎么办？", a="这就是 UNKNOWN 状态。恢复时不能直接重试写工具，要用业务 key 或工具自身查询接口查外部权威状态；查到已经成功就补写 tool_call=SUCCEEDED 和 result_ref，查不到且工具承诺幂等时才重试，否则进入人工确认。"),
            dict(q="客户端收到了事件，但 ack 请求丢了怎么办？", a="服务端会认为客户端水位较旧，重连时从旧 after_seq 后补发；客户端按 session_id 和 seq 去重即可。这会增加重复传输，但不会造成用户界面重复展示。不能因为 ack 可能丢就跳过补发，否则会破坏断线恢复。"),
            dict(q="为什么同一 session 不允许多个 Turn 并行？", a="Agent 上下文是顺序语义，后一个 Turn 可能依赖前一个 Turn 的工具结果、记忆写入和消息裁剪。如果同一 session 并行，message、event_log 和 checkpoint 都会乱序。可以并行的是同一 Turn 内明确无依赖的读工具，且要在事件日志里合并有序结果。"),
            dict(q="发布时怎么做到不中断几小时长会话？", a="发布控制器先把旧 worker 标记 DRAINING，不再接新 session；正在执行的 step 在 20 秒内尽量写 checkpoint，超过 30 秒停止续租 owner lease。新版本 worker 用更高 token 接管，从 checkpoint 继续。代价是发布速度变慢，但不会丢进度或重复工具。"),
            dict(q="事件日志太大，能不能只保留最近几条？", a="热日志至少要覆盖断线重连和恢复窗口，例如 7 天；更久历史可归档到对象存储。可以用 message 快照加 checkpoint 降低重放成本，但不能在 Turn 未完成或客户端未 ack 前删除必要事件，否则无法证明进度和副作用边界。"),
            dict(q="沙箱里的代码需要访问外部系统怎么办？", a="默认不把长期凭据放进沙箱。读写外部系统应通过工具代理或短期、限定范围的令牌，出网走白名单和审计代理；危险操作需要用户确认。这样即使模型被提示注入诱导，也不能直接拿凭据访问任意资源。"),
            dict(q="如何处理租户资源隔离？", a="入口按 tenant 做 Turn QPS、并发 worker、sandbox 数、CPU、内存和队列长度限制。调度队列按租户加权公平，不能让大租户占满全局沙箱池。资源超限时返回排队或限流事件，并在 event_log 中记录，方便用户解释为什么等待。"),
        ],
        variants=[
            "长任务代码助手：执行测试、改文件、调用外部 API，实例重启后继续且不重复提交。",
            "客服 Agent 工单处理平台：退款、建单、通知等写操作必须幂等并可审计。",
            "自动化运维 Agent：沙箱中执行命令，事件流断线后要补发日志并恢复任务。",
            "多租户工具编排平台：不同租户共享 worker 和沙箱池，但资源和凭据严格隔离。",
        ],
    ),
]

BLOCKS = []
DESIGNS = []
EXTRAS = {}
TOOLBOX = {}
