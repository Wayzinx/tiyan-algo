SYSTEMS = [
    dict(
        id="x9",
        order=9,
        title="订单履约与物流轨迹系统",
        brief="设计一个支持拆单、选仓、运单生成、多快递对接、轨迹单调展示和异常预警的订单履约系统。",
        statement="""你要设计一个电商订单履约与物流轨迹系统。用户下单后，一个订单可能因为多商家、多仓库、多温层或部分商品缺货被拆成多个履约单；系统要为每个履约单选择仓库，生成发货任务和运单，并对接多家快递。快递侧既可能主动推送轨迹回调，也可能需要平台定时主动拉取；回调会乱序、重复、缺失，字段格式也不完全一致。用户端要展示包裹状态、轨迹明细和预计送达时间，商家与客服端要看到异常件，例如超时未揽收、轨迹长时间停滞、派送失败。大促时轨迹查询 QPS 很高，用户页面 P99 要小于 100ms，同时不能因为 09:30 的旧事件晚到，就把用户已经看到的“派送中”回退成“到达分拨中心”。候选人需要说明服务拆分、表结构、状态机、幂等、乱序处理、缓存和异常兜底。""",
        focus="""题眼是多家快递回调乱序重复时，用户看到的物流状态只能单调前进、不回退；同时轨迹查询要靠预聚合和缓存把大促 P99 压到 100ms 内。""",
        scale="""规模假设：日常 100 万订单、峰值 1000 万订单；每单平均 1.4 个履约单，每个运单平均 12 条轨迹。大促峰值轨迹写入 2 万条/秒，查询 8 万 QPS，用户端 P99 < 100ms，异常预警延迟 5 分钟内。""",
        example="""同一运单 10:00 收到快递回调“派送中”，10:02 才收到事件时间 09:30 的“到达分拨中心”，10:05 又重复收到一条“派送中”。系统要保存原始事件用于审计，但用户状态仍保持“派送中”，轨迹明细按事件时间展示且去重。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清边界",
                minutes=3,
                prompt="先确认履约、快递、轨迹展示和异常预警的边界，避免把订单、仓储、物流都混成一个状态。",
                points=[
                    "确认拆单依据：商家、仓库、温层、库存和履约能力",
                    "确认选仓目标：成本、时效、库存可用性和服务区域",
                    "确认快递对接方式：推送、回调签名、主动拉取和补偿频率",
                    "确认用户状态是否要求单调前进以及哪些状态可人工修正",
                    "确认轨迹查询 P99、缓存时效和历史保留周期",
                    "确认异常件类型、告警对象和处理闭环",
                ],
                reference="""开场不要先画一个物流表，而要把业务对象和状态职责拆清。订单状态解决用户是否支付、是否完成；履约单状态解决仓库是否拣货、打包、出库；运单状态解决快递网络中的揽收、运输、派送、签收。拆单规则要问清楚，因为多商家和多仓会决定一个订单对应几个 fulfillment_order；温层和大件商品还可能禁止合包。选仓目标也不是单一最近仓，库存可用、截单时间、配送覆盖、运费和预计送达都要参与评分。快递侧要确认回调签名、事件唯一键、是否支持按运单拉取、是否支持批量查询，以及对方重试策略。用户状态单调前进是强约束：旧事件晚到只能补充明细，不能覆盖 shipment.current_status。异常预警要问谁处理，超时未揽收给仓库，轨迹停滞给客服或物流运营，派送失败可能触达用户改地址。指标也要明确：写入可最终一致，查询必须快；原始事件保存 180 天，热轨迹缓存保留 30 天。""",
            ),
            dict(
                key="estimate",
                title="规模估算",
                minutes=4,
                prompt="估算履约单、轨迹写入、查询、存储和缓存容量，并说明这些数字如何影响架构。",
                points=[
                    "按订单到履约单、运单、轨迹事件逐层放大估算",
                    "估算写入峰值和查询峰值，区分热运单和历史运单",
                    "估算轨迹原始表、展示快照和缓存大小",
                    "说明 P99 < 100ms 为什么不能每次查明细再计算状态",
                    "说明异常扫描的分片周期和延迟预算",
                    "说明哪些组件需要按快递公司或运单号分片",
                ],
                reference="""假设峰值 1000 万订单，平均 1.4 个履约单，就有 1400 万个履约单；每个履约单一个主运单，部分拆包可能再放大到 1500 万运单。每个运单平均 12 条轨迹，整场活动约 1.8 亿条轨迹事件。写入峰值如果集中在发货后 6 小时，平均约 8300 条/秒，考虑快递批量补推和回调重试，按 2 万条/秒设计。查询侧用户打开订单详情和物流页会形成更高峰值，按 8 万 QPS、P99 < 100ms 设计；这意味着查询链路不能每次扫 trajectory_event、排序、去重、计算状态，而要读 shipment_snapshot 或 Redis 中的展示快照。存储上原始事件按 1KB 计算，1.8 亿条约 180GB，MySQL 热表需要按月份和运单哈希分库分表，历史可归档到对象存储或分析库。缓存上热运单 3000 万个，每个快照 2KB 约 60GB，可按最近 30 天和访问热度淘汰。异常扫描不需要秒级，5 分钟内发现即可，因此用状态快照的 next_check_at 分片扫描，避免全表扫。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出订单、履约、选仓、快递适配、轨迹、查询、异常预警之间的调用和消息关系。",
                diagram="""flowchart LR
  A["订单服务"] --> B["履约编排服务"]
  B --> C["选仓服务"]
  C --> D["库存服务"]
  B --> E["仓库作业服务"]
  E --> F["运单服务"]
  F --> G["快递适配器"]
  G --> H["快递公司"]
  H --> I["回调网关"]
  I --> J["轨迹事件流"]
  J --> K["轨迹归一化服务"]
  K --> L["轨迹存储"]
  K --> M["展示快照缓存"]
  M --> N["物流查询 BFF"]
  L --> O["异常预警服务"]
  O --> P["客服/运营工作台"]""",
                points=[
                    "履约编排负责拆单和推进，不直接处理快递原始协议",
                    "快递适配器按承运商封装下单、取消、拉取和签名验签",
                    "轨迹归一化服务做去重、排序、状态映射和单调推进",
                    "查询 BFF 读取快照缓存，必要时降级读取数据库快照",
                    "异常预警基于快照和 SLA 规则，不扫原始事件大表",
                    "事件流解耦快递回调峰值和内部状态更新",
                    "仓库作业与库存服务通过消息保持最终一致",
                ],
                reference="""服务拆分的原则是把强一致业务动作和高吞吐外部事件分开。订单服务只发出已支付或待履约事件，不负责拆单。履约编排服务根据订单行、商家、仓库、温层和库存能力生成 fulfillment_order，并维护履约状态。选仓服务调用库存服务、仓库能力和配送时效模型，输出仓库、承运商候选和预计送达。仓库作业服务处理拣货、打包、出库，出库后由运单服务创建 shipment。快递适配器按承运商隔离协议差异，包括电子面单、取消运单、轨迹主动拉取、回调验签和限流；这样新增快递不会污染核心履约逻辑。回调网关只做鉴权、基础校验、落原始事件和投递消息，不在同步请求里复杂计算，避免对方重试导致雪崩。轨迹归一化服务消费事件流，做承运商状态映射、事件指纹去重、按 event_time 排序、按 status_rank 单调更新 shipment_snapshot。查询 BFF 面向用户端和客服端，优先读 Redis 或快照表。异常预警服务读取快照的 last_event_time、current_status、next_check_at，与 SLA 规则匹配后发告警。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="设计履约单、运单、轨迹事件、展示快照、承运商配置、异常工单等核心表。",
                ddl="""CREATE TABLE fulfillment_order (
  id BIGINT PRIMARY KEY,
  order_id BIGINT NOT NULL,
  merchant_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  promise_deliver_at DATETIME,
  version BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_order_merchant_warehouse (order_id, merchant_id, warehouse_id),
  KEY idx_merchant_status (merchant_id, status, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE shipment (
  id BIGINT PRIMARY KEY,
  fulfillment_id BIGINT NOT NULL,
  carrier_code VARCHAR(32) NOT NULL,
  tracking_no VARCHAR(64) NOT NULL,
  current_status VARCHAR(32) NOT NULL,
  status_rank INT NOT NULL,
  last_event_time DATETIME,
  estimated_deliver_at DATETIME,
  version BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_carrier_tracking (carrier_code, tracking_no),
  KEY idx_fulfillment (fulfillment_id),
  KEY idx_status_check (current_status, last_event_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE shipment_event (
  id BIGINT PRIMARY KEY,
  shipment_id BIGINT NOT NULL,
  carrier_code VARCHAR(32) NOT NULL,
  tracking_no VARCHAR(64) NOT NULL,
  carrier_event_id VARCHAR(128),
  event_fingerprint VARCHAR(64) NOT NULL,
  raw_status VARCHAR(64) NOT NULL,
  normalized_status VARCHAR(32) NOT NULL,
  status_rank INT NOT NULL,
  event_time DATETIME NOT NULL,
  received_at DATETIME NOT NULL,
  location VARCHAR(128),
  raw_payload TEXT,
  UNIQUE KEY uk_event_fp (event_fingerprint),
  KEY idx_shipment_time (shipment_id, event_time),
  KEY idx_tracking_time (carrier_code, tracking_no, event_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE shipment_snapshot (
  shipment_id BIGINT PRIMARY KEY,
  carrier_code VARCHAR(32) NOT NULL,
  tracking_no VARCHAR(64) NOT NULL,
  display_status VARCHAR(32) NOT NULL,
  status_rank INT NOT NULL,
  last_event_time DATETIME,
  last_event_desc VARCHAR(255),
  estimated_deliver_at DATETIME,
  event_count INT NOT NULL DEFAULT 0,
  next_check_at DATETIME,
  updated_at DATETIME NOT NULL,
  KEY idx_tracking (carrier_code, tracking_no),
  KEY idx_next_check (next_check_at, display_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE carrier_config (
  id BIGINT PRIMARY KEY,
  carrier_code VARCHAR(32) NOT NULL,
  api_endpoint VARCHAR(255) NOT NULL,
  callback_secret_id VARCHAR(64) NOT NULL,
  pull_interval_sec INT NOT NULL,
  qps_limit INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_carrier (carrier_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE logistics_alert (
  id BIGINT PRIMARY KEY,
  shipment_id BIGINT NOT NULL,
  alert_type VARCHAR(32) NOT NULL,
  alert_status VARCHAR(32) NOT NULL,
  due_at DATETIME NOT NULL,
  owner_type VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL,
  resolved_at DATETIME,
  UNIQUE KEY uk_open_alert (shipment_id, alert_type, alert_status),
  KEY idx_due_status (due_at, alert_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
                points=[
                    "fulfillment_order 存拆单结果和履约状态，不能把所有字段塞回订单表",
                    "shipment 用 carrier_code + tracking_no 做自然幂等键",
                    "shipment_event 保存原始事件和归一化字段，event_fingerprint 去重",
                    "shipment_snapshot 保存查询所需的当前展示状态和预计送达",
                    "carrier_config 隔离快递协议、限流和拉取频率",
                    "logistics_alert 记录异常件处理闭环",
                    "热查询索引围绕 tracking_no、shipment_id、next_check_at 设计",
                ],
                reference="""表设计要服务两类路径：写入路径追求完整可追溯，查询路径追求低延迟。fulfillment_order 是订单拆单后的履约单，一个订单可以有多条；version 用于状态 CAS，避免仓库回调和人工操作并发覆盖。shipment 用 carrier_code + tracking_no 建唯一键，因为不同承运商可能有相同运单号；current_status、status_rank、last_event_time 是当前状态快照，但展示仍以 shipment_snapshot 为准，便于缓存和扩展。shipment_event 保存所有原始事件，event_fingerprint 可以由 carrier_code、tracking_no、carrier_event_id 或 normalized_status、event_time、location 哈希生成，用来消除重复回调；received_at 和 event_time 都要存，前者用于审计回调延迟，后者用于轨迹展示排序。shipment_snapshot 是用户查询的热表，字段只放页面首屏需要的信息，event_count 让 BFF 判断是否需要拉明细。carrier_config 保存承运商协议、验签密钥标识、主动拉取周期和 QPS 限制，避免配置写死在代码里。logistics_alert 用唯一键限制同一运单同类未关闭告警重复创建。大表要按时间或 tracking_no 哈希分片，原始 payload 可冷归档；不要让用户查询直接扫 shipment_event。""",
            ),
            dict(
                key="api",
                title="接口和事件",
                minutes=5,
                prompt="列出拆单、选仓、运单、快递回调、轨迹查询和异常处理接口，说明幂等键和返回语义。",
                points=[
                    "拆单接口以 order_id + fulfillment_rule_version 保证幂等",
                    "运单创建以 fulfillment_id + carrier_code 幂等",
                    "快递回调只返回接收结果，不承诺业务状态已更新",
                    "轨迹查询接口读快照并支持明细分页",
                    "主动拉取任务按 carrier_code 和 tracking_no 分片限流",
                    "异常处理接口要带 expected_version 防止并发关闭",
                ],
                reference="""内部接口可以分同步命令和异步事件。POST /fulfillments/split 接收 order_id、order_lines、address、rule_version，幂等键是 order_id + rule_version；返回 fulfillment_order 列表，但不保证仓库已经拣货。POST /fulfillments/{id}/select-warehouse 可以由编排服务调用，参数包含候选仓、库存快照版本和 promise_at，失败时返回可重试还是不可履约。POST /shipments 接收 fulfillment_id、carrier_code、receiver_hash、package_weight，幂等键是 fulfillment_id + carrier_code + package_seq，避免仓库重复点击生成多个运单。快递回调 POST /carrier-callback/{carrier_code} 要验签、解析、落 raw_event，然后返回 200 或明确错误；200 只表示平台接收，不表示用户状态已更新。GET /shipments/{id}/tracking 返回 snapshot、events、estimated_deliver_at 和 data_freshness_ms，明细可按 cursor 分页。主动拉取任务 PullTracking(carrier_code, tracking_no, last_event_time) 要经过 carrier_config 限流，结果仍进入同一条事件流。异常接口 POST /alerts/{id}/resolve 带 expected_version 和处理备注，防止客服与自动恢复同时关闭。所有事件都要有 trace_id 和 event_id，方便从用户页面追到快递原始回调。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=5,
                prompt="画出履约单和运单的核心状态，并说明单调状态推进、旧事件补明细但不回退的规则。",
                diagram="""stateDiagram-v2
  [*] --> CREATED
  CREATED --> WAREHOUSE_SELECTED: 选仓成功
  WAREHOUSE_SELECTED --> PICKING: 下发仓库
  PICKING --> PACKED: 打包完成
  PACKED --> SHIPMENT_CREATED: 生成运单
  SHIPMENT_CREATED --> WAITING_PICKUP: 待揽收
  WAITING_PICKUP --> PICKED_UP: 已揽收
  PICKED_UP --> IN_TRANSIT: 运输中
  IN_TRANSIT --> OUT_FOR_DELIVERY: 派送中
  OUT_FOR_DELIVERY --> SIGNED: 已签收
  WAITING_PICKUP --> EXCEPTION: 超时未揽收
  IN_TRANSIT --> EXCEPTION: 轨迹停滞
  OUT_FOR_DELIVERY --> EXCEPTION: 派送失败
  EXCEPTION --> IN_TRANSIT: 恢复运输
  EXCEPTION --> SIGNED: 异常后签收
  SIGNED --> [*]""",
                points=[
                    "履约状态和物流状态要分层，不共用一个枚举",
                    "每个物流状态映射 status_rank，展示状态只允许 rank 增大或特殊转移",
                    "旧事件晚到写入事件表和明细，不覆盖 snapshot.current_status",
                    "异常状态可以是覆盖标记，也可以保留 base_status",
                    "签收是终态，除人工纠错外不被普通回调覆盖",
                    "状态更新用 shipment_id + version CAS",
                ],
                reference="""状态机要回答为什么用户不会看到回退。履约单从 CREATED、WAREHOUSE_SELECTED、PICKING、PACKED 到 SHIPMENT_CREATED，描述仓内作业；运单从 WAITING_PICKUP、PICKED_UP、IN_TRANSIT、OUT_FOR_DELIVERY 到 SIGNED，描述承运商网络。二者分层后，仓库取消、重新打包不会污染快递轨迹。每个承运商原始状态先映射为 normalized_status，再映射 status_rank，例如待揽收 10、已揽收 20、运输中 30、派送中 40、签收 50。归一化服务更新 snapshot 时执行条件：新事件未重复，且 new_rank > current_rank，或 new_rank == current_rank 且 event_time 更新，或符合白名单特殊转移。10:02 收到 09:30 的到达分拨中心，如果 rank 低于派送中，就只写 shipment_event，不更新 display_status；轨迹明细按 event_time 插入后用户能看到完整路径。异常状态要谨慎：轨迹停滞可以作为 alert 和 badge，不一定把 display_status 从派送中改成异常；派送失败则可进入 EXCEPTION，但后续恢复运输或签收要允许推进。签收后普通旧事件不能回退，除非人工纠错走审计流程。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=6,
                prompt="用顺序图说明下单到发货、快递回调到用户查询、异常预警的主流程和补偿流程。",
                diagram="""sequenceDiagram
  participant O as 订单服务
  participant F as 履约编排
  participant W as 选仓服务
  participant S as 仓库作业
  participant C as 快递适配器
  participant T as 轨迹服务
  participant Q as 查询BFF
  participant U as 用户
  O->>F: paid(order_id)
  F->>W: select(order_lines,address)
  W-->>F: warehouse,promise_at
  F->>S: create_pick_task(fulfillment_id)
  S->>C: create_waybill(package)
  C-->>S: tracking_no
  C-->>T: callback/raw_event
  T->>T: dedupe/map/monotonic_update
  U->>Q: GET tracking
  Q->>T: read snapshot/events
  T-->>Q: display_status/events
  Q-->>U: logistics view""",
                points=[
                    "支付成功事件触发拆单，拆单成功后再选仓和下发仓库",
                    "仓库出库后创建运单，运单创建失败要重试或换承运商",
                    "快递回调先落原始事件，再异步归一化和更新快照",
                    "用户查询优先读缓存，缓存未命中读 snapshot 并回填",
                    "主动拉取补偿缺失事件，结果复用同一归一化链路",
                    "异常预警基于 SLA 规则产生工单，处理后回写状态",
                ],
                reference="""主流程从订单支付成功事件开始，履约编排服务按订单行生成 fulfillment_order，然后调用选仓服务。选仓服务不是直接扣库存，而是读取库存可用量、仓库能力、截单时间和区域时效，返回可解释的 warehouse_id 与 promise_at。仓库作业服务完成拣货打包后调用快递适配器创建运单；如果承运商接口超时，运单服务用 fulfillment_id + package_seq 幂等重试，不能因为重试生成两张面单。快递回调到达后，回调网关验签、落 raw_event、投递事件流，同步返回接收结果。轨迹服务消费事件，先用 event_fingerprint 去重，再做状态映射和单调更新，最后刷新 shipment_snapshot 与缓存。用户查询时，查询 BFF 先读 Redis 快照；缓存缺失时读 snapshot 表和最近 N 条事件，组装后回填缓存，避免每次计算。主动拉取用于补偿缺失回调，但拉回的数据必须进入同一条归一化链路，不能另写一套状态逻辑。异常预警每分钟扫描 next_check_at 分片，发现超时未揽收或轨迹停滞后创建 alert，处理动作再通过事件推进或关闭告警。""",
            ),
            dict(
                key="reliability",
                title="可靠性和指标",
                minutes=7,
                prompt="说明乱序重复、快递不可用、缓存击穿、大促查询、异常误报和数据对账的兜底。",
                points=[
                    "用事件指纹和唯一键处理重复回调",
                    "用 status_rank、event_time 和 version CAS 保证单调展示",
                    "快递接口失败走退避重试、限流、熔断和主动拉取补偿",
                    "查询用 snapshot + Redis + 本地短缓存抗热点",
                    "异常预警用二次确认和人工关闭降低误报",
                    "建立原始事件、快照和快递拉取结果的对账任务",
                    "监控写入延迟、乱序率、重复率、查询 P99 和告警命中率",
                ],
                reference="""可靠性要覆盖写入正确性和查询性能。重复回调用 event_fingerprint 的唯一键兜住，fingerprint 优先用承运商事件 id，没有事件 id 时用 carrier_code、tracking_no、normalized_status、event_time、location 哈希；插入冲突只增加重复计数，不再推进状态。乱序用 status_rank 单调更新和 version CAS 解决，CAS 失败说明有并发更新，重新读取当前 rank 后再判断。快递接口不可用时，创建运单和主动拉取都要按承运商限流，失败进入指数退避；持续失败触发熔断，仓库侧可以换承运商或进入人工处理。查询 P99 靠预聚合 snapshot、Redis 热缓存、BFF 本地 1 到 3 秒短缓存和请求合并；缓存击穿时只允许一个请求回源，其余等待或返回带 freshness 的旧快照。异常预警不要只靠单个缺失事件，例如超时未揽收要结合出库时间、承运商揽收 SLA 和主动拉取确认；轨迹停滞要排除已签收和偏远地区规则。对账任务每天比对 shipment_event、snapshot、快递拉取结果，发现快照落后或事件缺口后重放事件。核心指标包括回调接收成功率、归一化延迟 P99、乱序率、重复率、快照更新失败率、物流查询 P99、缓存命中率、异常告警准确率和人工处理时长。""",
            ),
        ],
        mistakes=[
            dict(wrong="把快递回调直接覆盖运单当前状态", verdict="最大扣分点", why="这会让旧事件晚到时把用户已看到的派送中回退成运输中，违反单调展示要求，也无法解释重复回调。"),
            dict(wrong="用户查询实时扫描所有轨迹事件再排序", verdict="有错", why="大促 8 万 QPS 下扫描明细表会拖垮数据库，P99 很难小于 100ms，应读取展示快照和缓存。"),
            dict(wrong="只按 tracking_no 建唯一键", verdict="方向对但不准", why="不同承运商可能存在相同运单号，自然键必须包含 carrier_code，否则会串单。"),
            dict(wrong="异常件只靠定时全表扫描", verdict="有错", why="全表扫描在千万运单下成本过高，应维护 next_check_at 分片索引或按状态分桶扫描。"),
            dict(wrong="主动拉取写一套独立状态逻辑", verdict="有错", why="推送和拉取如果走不同逻辑，会产生状态不一致；两者都应进入同一事件归一化链路。"),
            dict(wrong="把原始 payload 全放在热查询表", verdict="方向对但不准", why="原始数据需要保留，但放入热表会降低缓存和索引效率，应热表存摘要，原始大字段归档或冷热分离。"),
        ],
        walkthrough="""回答时先声明三层对象：订单、履约单、运单，说明拆单后才有仓内履约，出库后才有快递轨迹。接着给规模估算，推出查询不能现算，必须有 shipment_snapshot 和 Redis。服务图重点讲履约编排、选仓、仓库作业、快递适配器、轨迹归一化、查询 BFF 和异常预警。表设计先讲 fulfillment_order 和 shipment 的幂等键，再讲 shipment_event 保存原始事件、shipment_snapshot 服务查询。状态机用 status_rank 解释 10:00 派送中、10:02 到达分拨中心的乱序场景：旧事件入明细但不覆盖当前展示状态。最后补可靠性：回调验签、事件指纹去重、CAS、快递限流熔断、主动拉取补偿、缓存击穿保护、异常二次确认和对账指标。""",
        oral="""我会把这个系统拆成履约和物流两条线。履约线负责订单支付后拆单、选仓、仓库作业和生成运单；物流线负责承运商协议、轨迹事件和用户展示。核心约束是快递事件天然不可靠：会重复、乱序、缺失，所以回调网关只负责验签和落原始事件，真正的轨迹服务用事件指纹去重，用承运商状态映射成统一状态，再用 status_rank 和 version CAS 推进展示快照。这样晚到的低等级事件仍然保存在明细里，但不会让 current_status 回退。查询上我不会让用户请求扫事件表，而是读 shipment_snapshot 和 Redis，明细只取最近或分页数据，缓存击穿时做请求合并和旧值兜底。异常预警基于快照的 last_event_time 和 next_check_at 分片扫描，超时未揽收、轨迹停滞、派送失败都会生成可关闭的工单。系统代价是多了一张快照表、一条异步归一化链路和对账任务，但换来的是用户状态稳定、快递接入隔离、查询 P99 可控。""",
        followups=[
            dict(q="为什么需要同时保存 event_time 和 received_at？", a="event_time 是快递事件真实发生时间，用来排序轨迹明细；received_at 是平台收到时间，用来分析回调延迟、乱序和对方重试。只有 event_time 会看不出 09:30 事件为什么 10:02 才到；只有 received_at 又会把轨迹展示顺序搞错。"),
            dict(q="预计送达怎么计算？", a="可以用仓库、目的地、承运商、揽收时间、历史时效分位数和当前状态做模型或规则。下单时给 promise_deliver_at，揽收后用实际 carrier 和第一条揽收时间修正。展示要带置信度，异常停滞时可降级为区间而不是精确时间。"),
            dict(q="缓存和数据库不一致怎么办？", a="快照表是权威展示状态，Redis 是加速层。轨迹更新先 CAS 写 snapshot，再删除或更新缓存；查询发现缓存版本低于 snapshot_version 时回源。若缓存更新失败，TTL 和读修复兜底，监控 cache_version_lag。"),
            dict(q="如何处理签收后又收到派送失败？", a="普通承运商旧事件不能覆盖 SIGNED，因为签收 rank 更高且是终态。事件仍写入明细并标记 late_event。如果确实签收错误，应走人工纠错接口，记录审计原因并触发售后或客服流程。"),
            dict(q="快递回调没有唯一事件 id 怎么去重？", a="用组合指纹：carrier_code、tracking_no、normalized_status、event_time、location、描述摘要。它不能保证百分百不冲突，所以原始事件仍可保留；展示推进以状态和时间判断，重复插入冲突只影响计数不影响状态。"),
            dict(q="异常预警如何避免误报？", a="规则要结合状态、SLA、承运商、地区和主动拉取确认。例如超时未揽收不是出库后固定 2 小时就报警，而要看仓库截单时间和承运商揽收窗口；报警前可主动拉取一次，仍无进展再创建工单。"),
            dict(q="多承运商新增接入怎么降低成本？", a="用 carrier_config 和适配器接口固定 createWaybill、cancelWaybill、parseCallback、pullTracking、mapStatus。核心履约和轨迹服务只依赖统一事件模型，新增承运商主要实现适配器、状态映射和限流配置。"),
            dict(q="轨迹明细很多时如何分页？", a="明细按 shipment_id + event_time 建索引，接口返回 cursor，cursor 可以包含最后一条 event_time 和 id，避免 offset 深分页。首屏展示快照和最近 N 条，用户展开历史再分页加载。"),
        ],
        variants=[
            "跨境物流：增加清关、干线、末端承运商多段运单，shipment 需要 parent_shipment_id 或 segment_no，状态映射要支持分段聚合。",
            "即时配送：轨迹更实时，位置点频率高，热数据可进入时序存储或地理缓存，但订单级展示仍要有单调状态快照。",
            "门店自提：没有承运商轨迹，履约状态以门店备货、待取货、已取货为主，但仍可复用 snapshot 和异常预警模型。",
        ],
    ),
    dict(
        id="x10",
        order=10,
        title="大促库存扣减（防超卖）",
        brief="设计一个支持预占、支付确认扣减、超时释放、取消回补、多仓库存和对账的大促库存系统。",
        statement="""你要设计一个电商大促库存扣减系统。商品有 SKU 维度库存，也可能分布在多个仓库；下单时需要先预占库存，支付成功后确认扣减，支付超时要释放预占，用户取消或售后前置取消要回补。系统必须保留库存流水用于审计和对账，并能处理订单重复提交、支付回调重复、取消与支付并发、缓存和数据库不一致。零点峰值每秒 5 万次下单，热点 SKU 请求集中，不能超卖，也不能因为粗暴限流导致大量明明有货的订单失败。示例：某 SKU 库存 100，零点 1 秒内 3000 个请求，其中 40 个订单支付超时，5 个支付后取消。候选人需要说明库存权威在哪里、如何预占、如何防止热点打挂数据库、如何释放和对账。""",
        focus="""题眼是在 5 万下单/秒和热点 SKU 下，仍然做到不超卖、不少卖，并且不能让所有请求直接打 MySQL 行锁。""",
        scale="""规模假设：大促峰值 5 万下单/秒，热点 SKU 单品 3000 请求/秒，SKU 总量 1000 万，多仓库存 5000 万行。下单链路库存判断 P99 < 50ms，预占成功率要接近真实可售库存，库存对账 5 分钟内发现差异。""",
        example="""某 SKU 可售库存 100，零点 1 秒内进来 3000 个下单请求。系统最多只能让 100 个请求预占成功，其余返回无货或排队失败；后续 40 个未支付超时释放，5 个已支付订单取消回补，库存流水要能解释每一次变化。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清语义",
                minutes=3,
                prompt="确认库存口径、预占时机、支付扣减、释放回补、多仓分配和一致性要求。",
                points=[
                    "确认可售库存、实物库存、预占库存和已售库存的定义",
                    "确认下单是否必须立即预占，支付多久超时释放",
                    "确认多仓是下单前选仓还是支付后调拨",
                    "确认是否允许排队、限购、预约和降级无货",
                    "确认库存流水是否作为审计权威",
                    "确认不超卖是强约束，不少卖是效率指标",
                ],
                reference="""澄清要先把库存口径说清楚。实物库存是仓库实际数量，可售库存是可以卖给用户的数量，预占库存是下单未支付或待确认占住的数量，已售库存是支付成功后真正扣掉的数量。防超卖通常要求下单阶段就预占，否则支付时才扣减会让大量用户支付失败；但预占会带来超时释放和少卖风险，因此要问支付超时时间、取消回补规则和对账频率。多仓场景要确认选仓时机：如果下单时已按地址选仓，库存键是 sku_id + warehouse_id；如果先卖总量再后置分仓，就需要虚拟共享库存和调拨失败兜底。还要问限购、预约和排队是否在库存前置过滤，避免机器人流量把库存令牌耗尽。强一致边界要说清：不超卖是硬约束，宁可部分请求失败；不少卖是通过库存令牌回补、超时释放和对账补偿提高利用率。库存流水必须记录每次预占、确认、释放、取消、人工调整，不能只看当前数量。""",
            ),
            dict(
                key="estimate",
                title="容量估算",
                minutes=4,
                prompt="估算峰值请求、热点 SKU、数据库行锁、缓存令牌和流水写入量，推出设计取舍。",
                points=[
                    "5 万下单/秒不能每次同步更新 MySQL 热行",
                    "热点 SKU 3000 请求/秒要靠令牌或分桶削峰",
                    "库存流水写入量与订单状态变更次数相关",
                    "Redis 令牌容量不能超过数据库可售库存",
                    "多仓库存键会放大库存行数和缓存键数量",
                    "对账任务要按 SKU/仓分片",
                ],
                reference="""如果每个下单请求都 update inventory set available=available-1 where sku_id=? and available>0，热点 SKU 3000 请求/秒会集中打同一行，行锁等待和主从延迟都会上升，数据库会先于业务耗尽库存而不可用。5 万下单/秒按每单一次预占、一次支付确认或释放计算，库存流水峰值至少 10 万写/秒，必须分库分表或用消息削峰。热点 SKU 库存 100 时，请求 3000 个，真正成功最多 100 个，所以可以在 Redis 预置 100 个库存令牌，获取令牌才进入订单创建；令牌数量必须来自数据库可售库存冻结值，不能凭缓存自增。为了避免单 key 成为 Redis 热点，可把 100 个令牌分到 16 或 64 个桶，客户端按哈希或随机桶扣减。多仓下库存键变成 sku_id + warehouse_id，假设 1000 万 SKU、平均 5 仓，就有 5000 万库存行；热活动只加载活动 SKU 的库存令牌，不全量进缓存。对账 5 分钟内发现差异，意味着流水、预占单和库存表都要按 sku_id/warehouse_id 分片可并行扫描。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出商品、活动、库存、订单、支付、延迟释放、对账之间的调用和消息关系。",
                diagram="""flowchart LR
  A["用户下单"] --> B["订单服务"]
  B --> C["库存服务"]
  C --> D["Redis库存令牌"]
  C --> E["库存数据库"]
  B --> F["支付服务"]
  F --> G["支付回调"]
  G --> C
  B --> H["延迟任务"]
  H --> C
  I["取消/售后"] --> C
  C --> J["库存流水"]
  J --> K["对账服务"]
  K --> E
  L["仓库系统"] --> E""",
                points=[
                    "订单服务只申请预占，不直接改库存表",
                    "库存服务是库存状态和流水的唯一写入口",
                    "Redis 令牌负责热点削峰，数据库负责最终权威",
                    "支付、取消、超时释放都通过库存服务幂等变更",
                    "延迟任务只触发检查，不能不查状态直接释放",
                    "对账服务比对库存表、预占表和流水",
                    "活动服务可提前冻结活动库存并预热令牌",
                ],
                reference="""服务划分要防止每个业务方各自改库存。商品或活动服务配置活动库存、限购和销售窗口，活动开始前把参与 SKU/仓的可售量冻结或切出活动库存池。订单服务在创建订单时调用库存服务 ReserveStock(order_id, items, address)，库存服务先走 Redis 令牌削峰，令牌成功后再写 reservation 和 stock_flow；如果数据库写失败，要归还令牌。Redis 不是权威，它只是把 3000 个热点请求挡在数据库前面。支付服务成功回调库存服务 ConfirmStock，把预占转为已售；取消、支付超时和售后前置取消调用 ReleaseStock，把预占或已售按业务规则回补。延迟任务服务只发送 order_timeout 事件，库存服务必须读取订单和 reservation 当前状态后再释放，避免支付成功后旧超时消息误释放。仓库系统可以异步回传实物出库，影响实物库存和对账，不应该直接覆盖可售。对账服务消费库存流水，也定期对比 inventory.available/reserved/sold 与 reservation 明细，发现差异生成冻结或修复任务。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="设计库存主表、预占表、库存流水、令牌桶元数据和对账差异表。",
                ddl="""CREATE TABLE inventory_stock (
  id BIGINT PRIMARY KEY,
  sku_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  total_qty INT NOT NULL,
  available_qty INT NOT NULL,
  reserved_qty INT NOT NULL,
  sold_qty INT NOT NULL,
  version BIGINT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_sku_warehouse (sku_id, warehouse_id),
  KEY idx_warehouse_sku (warehouse_id, sku_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stock_reservation (
  id BIGINT PRIMARY KEY,
  order_id BIGINT NOT NULL,
  sku_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  qty INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  expire_at DATETIME NOT NULL,
  version BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_order_sku_wh (order_id, sku_id, warehouse_id),
  KEY idx_expire_status (expire_at, status),
  KEY idx_sku_status (sku_id, warehouse_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stock_flow (
  id BIGINT PRIMARY KEY,
  flow_no VARCHAR(64) NOT NULL,
  order_id BIGINT,
  sku_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  change_type VARCHAR(32) NOT NULL,
  change_qty INT NOT NULL,
  before_available INT NOT NULL,
  after_available INT NOT NULL,
  biz_event_id VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_flow_no (flow_no),
  UNIQUE KEY uk_biz_event (biz_event_id),
  KEY idx_sku_time (sku_id, warehouse_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stock_token_bucket (
  id BIGINT PRIMARY KEY,
  sku_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  bucket_no INT NOT NULL,
  token_qty INT NOT NULL,
  token_version BIGINT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_bucket (sku_id, warehouse_id, bucket_no),
  KEY idx_sku_bucket (sku_id, warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stock_reconcile_diff (
  id BIGINT PRIMARY KEY,
  sku_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  diff_type VARCHAR(32) NOT NULL,
  expected_qty INT NOT NULL,
  actual_qty INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  detected_at DATETIME NOT NULL,
  resolved_at DATETIME,
  UNIQUE KEY uk_open_diff (sku_id, warehouse_id, diff_type, status),
  KEY idx_status_time (status, detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
                points=[
                    "inventory_stock 用 sku_id + warehouse_id 作为库存业务键",
                    "available/reserved/sold 三个数量满足守恒关系",
                    "stock_reservation 记录订单预占状态和过期时间",
                    "stock_flow 记录每次变化，biz_event_id 做幂等",
                    "stock_token_bucket 记录令牌桶初始化和回补，不替代库存权威",
                    "stock_reconcile_diff 保存对账差异和修复闭环",
                    "expire_at、sku_id、warehouse_id 都是高频查询索引",
                ],
                reference="""inventory_stock 是数据库权威，按 sku_id + warehouse_id 唯一，available_qty、reserved_qty、sold_qty 要满足 total_qty = available_qty + reserved_qty + sold_qty 加上冻结或损耗等扩展项；version 用于 CAS 或乐观锁。stock_reservation 是订单预占明细，一笔订单同一 SKU 仓只能有一条，状态包括 RESERVED、CONFIRMED、RELEASED、CANCELED，expire_at 支撑超时释放扫描。stock_flow 是审计核心，所有 Reserve、Confirm、Release、Cancel、Adjust 都必须写流水；biz_event_id 可以是 order_id + event_type + sku_id + warehouse_id，保证支付回调重复或取消重复不会多扣多加。stock_token_bucket 不是每次扣减都必须落库，它记录活动令牌初始化、桶编号和版本，方便重建 Redis 令牌和审计；运行期高频扣令牌在 Redis 原子脚本完成。stock_reconcile_diff 保存对账差异，例如库存表 reserved_qty 与 reservation 明细不一致、流水累计与当前库存不一致。所有表都有主键和业务唯一键；热点表需要按 sku_id 哈希分库分表，流水按时间归档。""",
            ),
            dict(
                key="api",
                title="接口和事件",
                minutes=5,
                prompt="列出预占、确认、释放、取消、查询和对账接口，说明幂等键、原子条件和失败返回。",
                points=[
                    "ReserveStock 返回成功、无货、可重试失败三类结果",
                    "ConfirmStock 必须基于已有 RESERVED 记录幂等推进",
                    "ReleaseStock 要检查 reservation 状态和 expire_at",
                    "CancelStock 区分未支付取消和支付后取消",
                    "库存查询不能把缓存值直接当权威审计值",
                    "对账修复接口需要人工审批和流水原因",
                ],
                reference="""ReserveStock(order_id, items, idempotency_key) 先校验订单幂等，再按商品排序加锁或批量扣令牌，避免多 SKU 死锁。单 SKU 预占成功后写 stock_reservation 和 stock_flow，并把库存表 available_qty 减少、reserved_qty 增加；返回 SUCCESS、OUT_OF_STOCK、RETRYABLE_ERROR。ConfirmStock(payment_id, order_id) 使用 biz_event_id 去重，只能把 RESERVED 改为 CONFIRMED，同时 reserved_qty 减少、sold_qty 增加；如果已 CONFIRMED 直接返回成功，不能重复扣。ReleaseStock(order_timeout_event) 必须读取订单支付状态和 reservation 状态，只有 RESERVED 且未支付才释放；过期消息晚到但订单已支付时应忽略。CancelStock(order_id, reason) 如果未支付，等价释放预占；如果已支付但未出库，要从 sold_qty 回补 available_qty，并写取消流水；已出库则进入售后库存规则，不一定立即可售。GET /stocks/{sku_id} 可返回缓存可售量用于展示，但后台审计查询要读数据库权威。对账修复 AdjustStock 需要审批单、expected_version 和原因码，所有修复也必须写 stock_flow。""",
            ),
            dict(
                key="states",
                title="状态机",
                minutes=5,
                prompt="画出库存预占从下单到支付、超时、取消和对账修复的状态，说明竞态下的合法转移。",
                diagram="""stateDiagram-v2
  [*] --> INIT
  INIT --> RESERVED: 下单预占成功
  INIT --> OUT_OF_STOCK: 令牌或库存不足
  RESERVED --> CONFIRMED: 支付成功
  RESERVED --> RELEASED: 支付超时释放
  RESERVED --> CANCELED: 未支付取消
  CONFIRMED --> REFUNDED_BACK: 支付后未出库取消
  CONFIRMED --> SHIPPED_LOCKED: 已出库不可直接回补
  RELEASED --> [*]
  CANCELED --> [*]
  REFUNDED_BACK --> [*]
  OUT_OF_STOCK --> [*]
  SHIPPED_LOCKED --> [*]""",
                points=[
                    "INIT 到 RESERVED 是唯一消耗可售库存的入口",
                    "RESERVED 到 CONFIRMED 不再减少 available，只转移 reserved 到 sold",
                    "RESERVED 到 RELEASED 才回补 available",
                    "重复支付回调命中 CONFIRMED 幂等返回",
                    "超时释放和支付成功并发时用 reservation version 决胜",
                    "已出库取消不能简单回补为可售",
                ],
                reference="""状态机的关键是数量守恒。下单预占从 INIT 到 RESERVED 时，available 减少、reserved 增加，这是唯一面对用户抢库存的动作。支付成功从 RESERVED 到 CONFIRMED 时，不再减少 available，因为下单时已经占了；它只是 reserved 减少、sold 增加。如果有人在支付成功时再次扣 available，就会少卖。支付超时从 RESERVED 到 RELEASED，reserved 减少、available 增加。未支付取消类似 RELEASED，但原因不同。支付后未出库取消可以从 CONFIRMED 到 REFUNDED_BACK，sold 减少、available 增加；如果已出库，则库存已转为实物流转，不能简单回补可售，应该进入售后或仓库入库流程。并发控制用 reservation.status + version 条件更新，例如 update ... where status='RESERVED' and version=?；支付成功和超时释放同时到达，只有一个 CAS 成功，失败方重读状态后幂等返回。OUT_OF_STOCK 是终态，不创建有效预占。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=6,
                prompt="用顺序图说明热点 SKU 下单预占、支付确认、超时释放、取消回补和对账补偿流程。",
                diagram="""sequenceDiagram
  participant U as 用户
  participant O as 订单服务
  participant I as 库存服务
  participant R as Redis令牌
  participant DB as 库存库
  participant P as 支付服务
  participant D as 延迟任务
  U->>O: submit order
  O->>I: ReserveStock(order_id,sku,qty)
  I->>R: eval扣令牌
  R-->>I: token ok
  I->>DB: 写预占/流水/CAS库存
  I-->>O: reserved
  O->>D: create payment timeout
  P-->>I: ConfirmStock(payment_id)
  D-->>I: ReleaseIfUnpaid(order_id)
  I->>DB: 按reservation状态CAS
  DB-->>I: one transition wins""",
                points=[
                    "活动开始前按数据库可售库存初始化 Redis 令牌",
                    "下单先扣令牌，成功后写数据库，数据库失败要归还令牌",
                    "多 SKU 订单要有部分失败回滚和补偿策略",
                    "支付确认和超时释放都基于 reservation 状态 CAS",
                    "取消回补要区分是否已支付、是否已出库",
                    "对账发现差异后冻结 SKU 或生成修复流水",
                ],
                reference="""活动预热时，库存服务从 inventory_stock 读取活动 SKU/仓的 available_qty，冻结活动库存版本，并初始化 Redis 令牌桶，令牌总数不能超过数据库可售量。用户下单时，订单服务先做限购和风控，再调用 ReserveStock。库存服务用 Redis Lua 脚本原子扣减令牌，令牌不足直接返回无货，避免请求进入数据库。令牌成功后写 stock_reservation、stock_flow，并 CAS 更新 inventory_stock；如果数据库失败或订单创建失败，要用补偿事件归还令牌，且归还不能超过桶初始上限加释放量。多 SKU 订单可以按 SKU 排序依次预占，任何一个失败就释放已预占项；高价值场景也可以先拆成多个履约单。支付成功和超时释放并发时，两个事件都调用库存服务更新 reservation，where status='RESERVED' 的 CAS 保证只有一个成功。取消回补读取订单履约状态，未出库才回补可售。对账任务定期用库存表、预占明细和流水重算，差异较大时先冻结活动 SKU，防止继续扩大错误。""",
            ),
            dict(
                key="reliability",
                title="可靠性和指标",
                minutes=7,
                prompt="说明防超卖、防少卖、热点保护、缓存数据库一致、消息重复、对账和降级策略。",
                points=[
                    "不超卖靠令牌上限、数据库条件更新和预占状态机三层保护",
                    "不少卖靠超时释放、取消回补、失败归还令牌和对账修复",
                    "热点 SKU 用分桶令牌、本地排队、限购和熔断保护",
                    "所有支付、取消、释放消息用 biz_event_id 幂等",
                    "Redis 丢失可从数据库和 token_bucket 重建，但重建期要限流",
                    "监控预占成功率、库存差异、令牌差异、行锁等待和释放延迟",
                    "异常时宁可短暂无货，也不能放大库存令牌",
                ],
                reference="""防超卖不能只靠一个组件。第一层是 Redis 令牌总数不超过数据库可售库存，挡住绝大多数热点请求；第二层是数据库条件更新或 reservation 唯一键，确保令牌异常时也不会把 available 扣成负数；第三层是状态机幂等，支付、取消、释放不会重复扣加。防少卖的失败模式包括订单创建失败但令牌未归还、支付超时未释放、取消后未回补、Redis 与数据库差异；对应机制是补偿消息、expire_at 扫描、取消事件、对账修复。热点保护可以用令牌分桶、单 SKU 本地队列、限购、验证码或排队页，但不能在库存还有 100 件时让 3000 个请求都打数据库。Redis 故障时，可以从 inventory_stock、stock_reservation 和 stock_token_bucket 重建令牌；重建期间对热点 SKU 限流或降级无货，不能乐观放大。消息重复靠 biz_event_id 唯一键，乱序靠 reservation 当前状态判断。核心指标包括库存扣减 P99、无货误判率、超卖数必须为 0、令牌与数据库差异、reservation 过期释放延迟、库存行锁等待、Redis 热 key QPS、对账差异修复时长。""",
            ),
        ],
        mistakes=[
            dict(wrong="所有下单请求直接 update MySQL 库存行", verdict="最大扣分点", why="热点 SKU 每秒数千请求会把单行锁打满，数据库不可用后既不能防超卖也不能保证下单体验。"),
            dict(wrong="支付成功时才扣库存", verdict="有错", why="下单到支付之间会出现大量用户同时支付同一库存，最终支付失败体验很差，也难以解释已下单未支付的库存。"),
            dict(wrong="Redis 扣减成功就认为库存权威成功", verdict="有错", why="Redis 只是削峰和快速失败层，权威仍要落 reservation、flow 和库存表，否则无法审计和对账。"),
            dict(wrong="超时消息到达就直接释放库存", verdict="有错", why="支付成功和超时取消可能并发，必须检查订单和预占状态，用 CAS 决定谁生效。"),
            dict(wrong="取消后统一回补可售库存", verdict="方向对但不准", why="未支付取消和支付后未出库可以回补，已出库订单要等仓库入库或售后规则，不能直接变可售。"),
            dict(wrong="只记录当前库存，不记录流水", verdict="缺失", why="没有流水无法定位重复扣减、人工调整和对账差异，也不能向业务解释库存变化原因。"),
        ],
        walkthrough="""先定义库存口径：available、reserved、sold，说明下单预占、支付确认、超时释放、取消回补的数量变化。再用 5 万下单/秒和热点 SKU 3000 请求/秒推出不能打数据库热行，需要 Redis 令牌或分桶削峰，但数据库库存和流水仍是权威。服务图讲订单、库存、支付、延迟任务、对账的边界。表结构讲 inventory_stock、stock_reservation、stock_flow、stock_token_bucket、reconcile_diff。状态机重点强调支付确认不再扣 available，只从 reserved 转 sold；超时释放和支付回调用 reservation CAS 决胜。最后讲可靠性：幂等键、失败归还令牌、Redis 重建、对账冻结、指标和降级策略。""",
        oral="""我的设计会把防超卖拆成三层。第一层在活动开始前按数据库可售库存初始化 Redis 令牌，热点 SKU 下单先扣令牌，令牌没有就快速无货，这样 3000 个请求不会都打到 MySQL。第二层是数据库权威，令牌成功后必须写预占表、库存流水，并用条件更新把 available 转成 reserved；如果数据库失败，要补偿归还令牌。第三层是状态机和幂等，支付成功只把 reserved 转 sold，不再扣 available；超时释放只在 reservation 仍是 RESERVED 时把 reserved 转回 available；支付回调、取消和释放都用 biz_event_id 防重复。这样 SKU 库存 100 时最多 100 个订单预占成功，40 个超时后释放，5 个取消按是否出库决定回补。代价是引入 Redis 令牌、补偿和对账链路，但它把数据库热点挡住，同时保留可审计的库存流水。异常时策略是宁可短暂无货或限流，也不放大令牌导致超卖。""",
        followups=[
            dict(q="Redis 令牌扣了但订单创建失败怎么办？", a="订单服务或库存服务要发送释放补偿，使用 reservation 或临时 token_log 的 idempotency_key 归还令牌。若补偿消息丢失，对账任务会发现令牌减少但没有 reservation，并把差异回补；期间宁可少卖，不能超发令牌。"),
            dict(q="多 SKU 订单如何保证一致？", a="按 sku_id + warehouse_id 固定顺序预占，避免死锁；任何一项失败就释放已成功预占项。严格事务跨分库成本高，通常用本地事务加补偿，订单状态在库存全部预占成功后才进入待支付。"),
            dict(q="如何避免 Redis 单 key 热点？", a="把活动库存拆成多个桶，例如 64 个 bucket，每个桶有一部分 token，按用户或请求随机选择桶扣减，失败后可尝试少量其他桶。桶数太多会增加归还和对账复杂度，太少会形成热 key。"),
            dict(q="数据库条件更新怎么写？", a="核心条件是 available_qty >= qty 和版本匹配，例如 update inventory_stock set available_qty=available_qty-?, reserved_qty=reserved_qty+?, version=version+1 where sku_id=? and warehouse_id=? and available_qty>=?。影响行数为 1 才成功。"),
            dict(q="支付回调先到、订单状态还没更新怎么办？", a="库存服务以 reservation 为准幂等推进到 CONFIRMED，订单服务随后读到库存已确认再更新订单。若 reservation 不存在，支付回调可短暂重试或进入异常队列，不能创建无预占扣减。"),
            dict(q="如何做库存对账？", a="按 sku_id/warehouse_id 分片重算：reserved_qty 应等于 RESERVED reservation 汇总，sold_qty 与 CONFIRMED/出库口径一致，流水累计应能推导当前库存。差异生成 reconcile_diff，严重差异先冻结销售再人工或自动修复。"),
            dict(q="什么叫不超卖和不少卖的取舍？", a="不超卖是安全底线，库存 100 不能卖出 101；不少卖是效率目标，不能因为令牌丢失或释放延迟导致有货卖不出。异常时先保护不超卖，再靠补偿、释放和对账恢复可售。"),
            dict(q="多仓库存怎么选仓？", a="先根据地址、仓库覆盖、运费和库存可用性选定 warehouse_id，再对 sku_id + warehouse_id 预占。若允许跨仓拆单，则每个履约单有独立预占；不要先扣总库存再随意分仓，否则会出现某仓无货履约失败。"),
        ],
        variants=[
            "预约抢购：先发资格或预约号，活动开始后资格换库存令牌，可以降低零点瞬时无效请求。",
            "总仓共享库存：需要虚拟库存池和仓库安全水位，预占后再分仓，调拨失败要有换仓或取消兜底。",
            "秒杀极小库存：可以预生成库存 token 队列，成功请求异步创建订单，但必须给用户明确排队或成功语义。",
        ],
    ),
    dict(
        id="x11",
        order=11,
        title="商家履约工作台（全栈）",
        brief="设计一个支持待发货列表、批量打单发货、Excel 导入、异常处理、看板和导出的商家履约工作台。",
        statement="""你要设计一个面向商家的履约工作台。商家每天可能有 5 万个订单，需要在网页上按订单状态、下单时间、承诺发货时间、仓库、商品、收件地区、异常类型等条件筛选待发货订单，并支持分页查看。商家可以批量打单、批量发货、上传 Excel 导入运单号，导入过程要异步处理并展示进度；如果 2000 行 Excel 里有 30 行格式错误、10 行订单已取消，系统要给出可下载的错误明细。页面还要提供异常订单处理、履约数据看板和大文件导出。前端要考虑页面与组件拆分、状态管理、虚拟滚动、重复提交、错误提示和断网恢复；后端要考虑 BFF 聚合、游标分页、批量幂等、异步任务进度、权限和导出大文件。目标是列表筛选 P99 < 500ms，批量发货 2000 单可靠、可重试、进度可见。""",
        focus="""题眼是全栈协同：前端不能只是调接口，后端也不能只给 CRUD；2000 单批量操作要幂等、可重试、可观测，列表筛选 P99 要小于 500ms。""",
        scale="""规模假设：大商家单日 5 万单，待发货峰值 2 万单，列表查询 500 QPS，筛选 P99 < 500ms；批量发货单次 2000 行，导入文件 5MB，导出最大 20 万行，异步任务进度延迟 < 3 秒。""",
        example="""商家上传一个 2000 行运单号 Excel，其中 30 行格式错误、10 行订单已取消，上传到一半网络断了。系统要支持前端续传或重新上传幂等识别，后端异步处理每行，最终展示 1960 行成功、40 行失败，并允许下载失败明细后修正重试。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清范围",
                minutes=3,
                prompt="确认商家角色、订单范围、批量动作、文件导入导出、看板实时性和前端体验要求。",
                points=[
                    "确认商家只能看自己的店铺、仓库和订单",
                    "确认待发货列表的筛选字段、排序字段和默认时间范围",
                    "确认批量打单、发货、导入运单号的业务校验",
                    "确认 Excel 大小、行数、错误明细和重试方式",
                    "确认看板指标是实时还是分钟级延迟",
                    "确认前端断网、重复点击和长列表体验要求",
                ],
                reference="""澄清时要同时问业务和前端体验。权限上，商家账号可能绑定多个店铺和仓库，所有查询和批量操作都必须带 merchant_id、shop_id 或 warehouse_id 范围，不能只靠前端过滤。列表字段要问清哪些是高频筛选，例如订单状态、承诺发货时间、仓库、商品、地区、异常类型；这些字段决定索引和搜索方案。批量动作要确认业务校验：已取消订单不能发货，已发货订单重复导入应幂等，缺少承运商或运单号格式错误要行级失败。文件导入要问是否需要模板、最大 2000 行还是更大、错误明细格式、是否允许断点续传。导出要确认同步下载还是异步生成文件，20 万行不能让浏览器等待一个长 HTTP。看板通常允许分钟级延迟，可以走汇总表或 OLAP；发货操作必须近实时。前端要问是否需要虚拟滚动、固定列、批量选择跨页、操作二次确认和断网重试提示。""",
            ),
            dict(
                key="estimate",
                title="规模估算",
                minutes=4,
                prompt="估算列表查询、批量处理、文件导入导出、前端渲染和索引数据量。",
                points=[
                    "5 万单/天决定列表必须默认限定时间范围",
                    "待发货 2 万单不能一次渲染到浏览器 DOM",
                    "2000 行批量发货要拆分为行级任务或小批次",
                    "导出 20 万行必须异步生成对象存储文件",
                    "筛选 P99 < 500ms 需要组合索引或搜索索引",
                    "进度刷新 3 秒内可用轮询或轻量推送",
                ],
                reference="""大商家一天 5 万单，如果默认查询不带时间范围，30 天就是 150 万行，offset 深分页会越来越慢，因此列表应默认近 7 天或待发货状态，并使用 merchant_id、status、promise_ship_at、order_id 等组合索引。待发货峰值 2 万单，前端不能一次渲染 2 万个 DOM 节点，否则滚动和勾选都会卡顿；每页 50 到 100 行，长列表用虚拟滚动，跨页选择用服务端 selection token 或筛选条件快照。批量发货 2000 行如果同步处理，每行调用物流和订单接口，HTTP 会超时；应创建 import_task，把文件解析为 task_item，小批次并发处理，例如每批 100 行、并发 5 到 10。导出 20 万行按每行 1KB 就有 200MB 级别，必须异步流式写 CSV 或 XLSX 到对象存储，前端轮询进度后下载。列表查询 500 QPS、P99 < 500ms，BFF 不能串行调用多个服务逐行补数据，要批量聚合商品、物流和异常信息。""",
            ),
            dict(
                key="services",
                title="服务和前端划分",
                minutes=7,
                prompt="画出前端页面组件、BFF、订单、物流、文件、任务、看板和导出服务的关系。",
                diagram="""flowchart LR
  A["商家浏览器"] --> B["履约工作台前端"]
  B --> C["筛选栏/表格/批量操作组件"]
  B --> D["上传导入/任务进度组件"]
  B --> E["看板/导出组件"]
  C --> F["商家履约BFF"]
  D --> F
  E --> F
  F --> G["订单服务"]
  F --> H["物流服务"]
  F --> I["商品服务"]
  F --> J["异步任务服务"]
  J --> K["文件存储"]
  J --> L["消息队列"]
  L --> M["导入导出Worker"]
  F --> N["看板汇总库"]""",
                points=[
                    "前端按筛选区、订单表格、批量操作、上传任务、看板导出拆组件",
                    "前端状态分为 URL 查询条件、列表数据、选择集、任务进度和用户草稿",
                    "长列表用分页加虚拟滚动，跨页选择由服务端条件快照支持",
                    "BFF 聚合订单、商品、物流、异常信息，减少前端瀑布请求",
                    "异步任务服务管理导入、批量发货和导出进度",
                    "Worker 行级处理并写成功失败明细",
                    "看板读汇总库，不阻塞交易库",
                ],
                reference="""全栈设计要把浏览器也画进去。前端页面可以拆成 FulfillmentPage、FilterBar、OrderTable、BatchActionBar、ImportDrawer、TaskProgressPanel、ExceptionModal、DashboardCards、ExportCenter。状态管理分层：筛选条件放 URL query，便于刷新和分享；列表数据交给请求缓存库或统一 store，按 cursor 缓存；勾选状态用 selectedIds、excludedIds 和 selectAllByQueryToken 表示，避免跨页全量 id 塞进浏览器；上传任务进度单独按 task_id 轮询；表单草稿本地保存以防刷新丢失。表格展示 50 到 100 行分页，行内复杂列懒加载，虚拟滚动用于大页和固定列，避免 2 万行 DOM。BFF 是关键，它校验商家权限，接收筛选条件，批量调用订单、商品、物流和异常服务，返回页面 DTO；前端不应逐行调 4 个服务。批量发货、Excel 导入和导出都创建异步任务，任务服务写 task 和 task_item，消息队列驱动 Worker 处理。看板读分钟级汇总库，避免每次统计扫订单明细。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="设计订单查询索引、批量任务、任务明细、文件和导出记录表，支撑分页、幂等和进度。",
                ddl="""CREATE TABLE merchant_order_fulfillment (
  id BIGINT PRIMARY KEY,
  merchant_id BIGINT NOT NULL,
  order_id BIGINT NOT NULL,
  warehouse_id BIGINT NOT NULL,
  order_status VARCHAR(32) NOT NULL,
  fulfillment_status VARCHAR(32) NOT NULL,
  promise_ship_at DATETIME NOT NULL,
  buyer_region VARCHAR(64),
  exception_type VARCHAR(32),
  updated_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_order (order_id),
  KEY idx_list_status_time (merchant_id, fulfillment_status, promise_ship_at, order_id),
  KEY idx_exception (merchant_id, exception_type, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE batch_task (
  id BIGINT PRIMARY KEY,
  merchant_id BIGINT NOT NULL,
  task_type VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL,
  total_count INT NOT NULL DEFAULT 0,
  success_count INT NOT NULL DEFAULT 0,
  failed_count INT NOT NULL DEFAULT 0,
  file_id BIGINT,
  result_file_id BIGINT,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_task_idem (merchant_id, task_type, idempotency_key),
  KEY idx_merchant_status (merchant_id, status, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE batch_task_item (
  id BIGINT PRIMARY KEY,
  task_id BIGINT NOT NULL,
  merchant_id BIGINT NOT NULL,
  row_no INT NOT NULL,
  order_id BIGINT,
  tracking_no VARCHAR(64),
  carrier_code VARCHAR(32),
  item_status VARCHAR(32) NOT NULL,
  error_code VARCHAR(64),
  error_message VARCHAR(255),
  attempt INT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_task_row (task_id, row_no),
  KEY idx_task_status (task_id, item_status),
  KEY idx_order_task (order_id, task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE merchant_file (
  id BIGINT PRIMARY KEY,
  merchant_id BIGINT NOT NULL,
  file_type VARCHAR(32) NOT NULL,
  object_key VARCHAR(255) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  file_size BIGINT NOT NULL,
  checksum VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_checksum (merchant_id, file_type, checksum),
  KEY idx_merchant_time (merchant_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE export_job (
  id BIGINT PRIMARY KEY,
  merchant_id BIGINT NOT NULL,
  query_hash VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  total_rows INT NOT NULL DEFAULT 0,
  file_id BIGINT,
  expire_at DATETIME NOT NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_export_idem (merchant_id, query_hash, created_by, created_at),
  KEY idx_export_status (merchant_id, status, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
                points=[
                    "merchant_order_fulfillment 是面向列表的读模型或索引表",
                    "列表组合索引以 merchant_id、状态、承诺发货时间、order_id 为核心",
                    "batch_task 保存总进度和幂等键",
                    "batch_task_item 保存行级成功失败和错误原因",
                    "merchant_file 用 checksum 支持重复上传识别",
                    "export_job 记录异步导出和下载过期时间",
                    "大字段和文件内容放对象存储，不放 MySQL",
                ],
                reference="""商家工作台的表设计通常会引入读模型。merchant_order_fulfillment 可以由订单事件同步维护，字段按页面筛选裁剪，避免列表查询跨订单、商品、物流多表 join；merchant_id 必须在所有索引最左侧，防止越权和全局扫描。idx_list_status_time 支撑待发货按承诺发货时间排序的游标分页，cursor 可以用 promise_ship_at + order_id。batch_task 是批量导入、批量发货、批量打单的任务头，idempotency_key 来自前端生成的 request_id 或文件 checksum + 操作类型，重复提交直接返回原 task_id。batch_task_item 是行级结果，row_no 唯一保证同一 Excel 行不会重复处理；error_code 和 error_message 支持前端下载失败明细。merchant_file 存对象存储 key、大小和 checksum，断网上传后再次提交同一文件可以识别。export_job 存 query_hash 和文件 id，导出结果设置 expire_at，防止永久占用存储。真正的订单详情、商品标题和地址可能在别的服务，BFF 返回列表时批量补齐。""",
            ),
            dict(
                key="api",
                title="接口设计",
                minutes=5,
                prompt="说明列表分页、批量接口幂等、Excel 上传、任务进度查询、失败明细下载和导出接口。",
                points=[
                    "列表优先游标分页，offset 只用于浅页或后台小数据",
                    "批量接口必须带 idempotency_key 和操作条件快照",
                    "上传先拿 upload_url，再提交 file_id 创建任务",
                    "任务进度接口返回总数、成功数、失败数和阶段",
                    "失败明细单独下载，支持按失败行重试",
                    "导出接口创建 job，完成后返回短期下载链接",
                ],
                reference="""GET /merchant/orders 使用 merchant_id 从登录态获取，参数包括 status、promise_ship_start/end、warehouse_id、sku_keyword、region、exception_type、cursor、limit。游标分页比 offset 更适合持续变化的待发货列表，因为 offset 在新增订单时会跳页，深页也慢；cursor 用排序字段 promise_ship_at 和 order_id。POST /merchant/orders/batch-ship 接收 order_ids 或 selection_query_token、carrier_code、idempotency_key，返回 task_id；服务端保存筛选条件快照，避免前端跨页选择传几万个 id。文件导入流程是 POST /files/upload-url 获取预签名地址，浏览器直传对象存储，POST /imports/waybills 用 file_id、checksum、idempotency_key 创建任务。GET /tasks/{task_id} 返回 status、total、success、failed、current_stage、updated_at，前端每 1 到 3 秒轮询或用轻量推送。GET /tasks/{task_id}/errors 下载失败明细，POST /tasks/{task_id}/retry-failed 只重试失败行。POST /exports 创建导出 job，GET /exports/{id} 查进度，完成后返回短期 download_url。所有写接口都要做 CSRF 或同类防护、权限校验、幂等和审计。""",
            ),
            dict(
                key="states",
                title="任务状态机",
                minutes=5,
                prompt="画出批量导入或批量发货任务状态，说明行级状态、可重试和前端展示。",
                diagram="""stateDiagram-v2
  [*] --> CREATED
  CREATED --> UPLOADING: 文件直传
  UPLOADING --> PARSING: 提交file_id
  PARSING --> VALIDATING: 解析完成
  VALIDATING --> PROCESSING: 生成行任务
  PROCESSING --> PARTIAL_SUCCESS: 部分失败
  PROCESSING --> SUCCEEDED: 全部成功
  PROCESSING --> FAILED: 系统失败
  FAILED --> RETRYING: 重试
  PARTIAL_SUCCESS --> RETRYING: 重试失败行
  RETRYING --> PROCESSING
  SUCCEEDED --> [*]
  PARTIAL_SUCCESS --> [*]""",
                points=[
                    "任务头状态和行状态分离，进度来自行状态聚合",
                    "格式错误行不进入发货调用，直接标记失败",
                    "已取消订单是业务失败，可修正后重试或跳过",
                    "系统失败可重试，业务失败不自动重试",
                    "前端根据状态展示进度、失败下载和重试按钮",
                    "重复提交命中同一 task_id，不创建新任务",
                ],
                reference="""批量任务状态要让用户看懂，也要让系统可恢复。CREATED 表示任务记录已创建；UPLOADING 是浏览器直传文件，断网可能停在这里，用户重新上传同 checksum 文件可复用 file_id。PARSING 解析 Excel，发现列缺失或行格式错误时创建失败 item；VALIDATING 校验订单归属、状态、承运商和运单号格式；PROCESSING 才真正调用订单和物流服务发货。任务头的 success_count、failed_count 由 item 状态聚合，避免一个 2000 行任务因为 40 行失败就整体失败。行状态包括 PENDING、VALIDATION_FAILED、PROCESSING、SUCCEEDED、BUSINESS_FAILED、SYSTEM_FAILED；SYSTEM_FAILED 可自动退避重试，BUSINESS_FAILED 例如订单已取消，不应自动重试。PARTIAL_SUCCESS 是常态，前端要展示成功、失败、处理中，并提供失败明细下载和仅重试失败行。重复点击提交时，idempotency_key 返回原 task_id，前端继续展示原进度。""",
            ),
            dict(
                key="flows",
                title="关键流程",
                minutes=6,
                prompt="用顺序图说明列表查询、Excel 导入发货、进度查询和导出大文件流程。",
                diagram="""sequenceDiagram
  participant FE as 前端
  participant BFF as 履约BFF
  participant FS as 文件存储
  participant TS as 任务服务
  participant W as Worker
  participant O as 订单服务
  participant L as 物流服务
  FE->>BFF: getUploadUrl(checksum)
  BFF-->>FE: upload_url,file_id
  FE->>FS: put excel chunks
  FE->>BFF: createImportTask(file_id,idempotency_key)
  BFF->>TS: create task
  TS-->>FE: task_id
  W->>TS: pull task items
  W->>O: validate order status
  W->>L: bind tracking and ship
  FE->>BFF: poll task progress
  BFF->>TS: read progress
  BFF-->>FE: success/failed/progress""",
                points=[
                    "列表查询由 BFF 校验权限后读索引表并批量聚合",
                    "文件直传对象存储，应用服务不转发大文件",
                    "创建任务和解析处理分离，HTTP 快速返回 task_id",
                    "Worker 对每行做格式、权限、订单状态和物流校验",
                    "前端轮询进度并在断网后按 task_id 恢复",
                    "导出走异步 job，完成后给短期下载链接",
                ],
                reference="""列表查询流程是前端把筛选条件写入 URL 并请求 BFF，BFF 从登录态得到 merchant_id，校验仓库权限，读取 merchant_order_fulfillment 的一页 order_id，再批量请求商品、物流、异常摘要，组装页面 DTO。Excel 导入不让应用服务器接收 5MB 到几十 MB 文件，而是先获取 upload_url，浏览器分片或直传对象存储；网络断开后，前端可以凭 file_id 或 checksum 恢复。提交导入任务后，任务服务记录 batch_task 并投递解析消息，HTTP 立即返回 task_id。Worker 解析 Excel，每行先做格式校验，格式错误直接写 VALIDATION_FAILED；再校验订单是否属于商家、是否待发货、是否已取消；通过后调用物流服务绑定运单并调用订单服务发货。进度接口只读 batch_task 聚合计数，前端轮询并在页面刷新后通过 task_id 恢复。导出流程类似，创建 export_job 后 Worker 按游标分页扫描，流式写文件，完成后返回短期下载链接，避免浏览器长连接超时。""",
            ),
            dict(
                key="reliability",
                title="可靠性和体验",
                minutes=7,
                prompt="说明前端重复提交、断网、错误提示、列表性能、异步任务、导出大文件和权限安全的兜底。",
                points=[
                    "前端按钮禁用、防抖和 idempotency_key 共同防重复提交",
                    "断网后保留 task_id、file_id 和筛选条件，恢复后继续查询",
                    "行级错误要可读、可下载、可重试",
                    "列表用虚拟滚动、列裁剪、请求取消和骨架屏提升体验",
                    "批量任务 Worker 可重试，业务失败不自动重试",
                    "导出大文件限流、过期清理和对象存储下载",
                    "监控列表 P99、任务失败率、重复提交率和前端错误率",
                ],
                reference="""可靠性要覆盖浏览器到后端。前端层面，提交按钮在请求中禁用，批量操作弹窗二次确认，并为每次用户意图生成 idempotency_key；即使用户双击或刷新重试，后端也返回同一 task_id。断网时保留 file_id、task_id、筛选条件和未提交表单草稿，恢复网络后继续轮询任务，不让用户重新猜状态。错误提示要分层：格式错误指到 Excel 行号和列名，业务错误说明订单已取消或无权限，系统错误提示稍后重试。列表性能上，虚拟滚动、固定列裁剪、请求取消、缓存上一页、骨架屏和空状态都要设计；筛选条件变更时取消旧请求，避免慢响应覆盖新结果。后端 Worker 对系统错误退避重试，对业务失败只记录失败明细。导出大文件限制并发和频率，文件生成后设置过期清理。安全上，所有接口从登录态取 merchant_id，服务端校验订单归属，不能相信前端传的商家 id。指标包括列表 P99、BFF 聚合耗时、任务进度延迟、行级失败率、重复提交命中率、导出成功率、前端 JS 错误率和接口 4xx/5xx。""",
            ),
        ],
        mistakes=[
            dict(wrong="列表用 offset 深分页并允许不带时间范围", verdict="最大扣分点", why="大商家几十万订单下深分页会越来越慢，新增订单还会导致跳页，无法保证筛选 P99 < 500ms。"),
            dict(wrong="2000 行 Excel 同步处理后再返回 HTTP", verdict="有错", why="同步请求容易超时，用户断网会丢失进度，也无法展示行级成功失败和重试。"),
            dict(wrong="前端逐行请求商品、物流和异常信息", verdict="有错", why="这会形成瀑布请求和浏览器并发瓶颈，应该由 BFF 批量聚合后返回页面 DTO。"),
            dict(wrong="只在前端禁用按钮防重复提交", verdict="方向对但不准", why="前端防抖只能改善体验，刷新、重试和多标签页仍会重复，后端必须用 idempotency_key。"),
            dict(wrong="导出大文件直接在接口内生成并返回", verdict="有错", why="20 万行导出会占用长连接和内存，应该异步生成文件并提供短期下载链接。"),
            dict(wrong="把商家 id 当成前端参数信任", verdict="最大扣分点", why="这会造成越权查看和操作订单，服务端必须从登录态和权限系统确定商家范围。"),
        ],
        walkthrough="""回答先强调这是全栈题，不只后端 CRUD。前端拆页面、筛选、表格、批量操作、上传任务、看板导出；状态分 URL 查询条件、列表缓存、选择集和任务进度。后端用履约 BFF 聚合订单、商品、物流和异常，列表用 merchant_id + status + promise_ship_at + order_id 的游标分页。批量发货和 Excel 导入都创建 batch_task 和 batch_task_item，HTTP 快速返回 task_id，Worker 行级处理并写成功失败。上传文件直传对象存储，断网用 checksum 和 file_id 恢复。导出大文件异步生成。可靠性收尾讲幂等、权限、错误明细、前端重复提交、虚拟滚动、请求取消、任务重试和指标。""",
        oral="""我会把商家履约工作台设计成前端页面加 BFF 加异步任务三层。前端页面拆成筛选栏、订单表格、批量操作栏、导入抽屉、任务进度面板、异常处理弹窗和导出中心；筛选条件放 URL，列表数据走请求缓存，跨页选择用服务端条件快照，长列表使用分页和虚拟滚动。BFF 负责权限校验和聚合，列表接口用游标分页，先从面向商家的履约读模型查一页 order_id，再批量补商品、物流和异常信息，避免前端逐行请求。批量发货和 Excel 导入不做同步处理，而是上传文件到对象存储后创建 batch_task，Worker 逐行校验格式、订单归属、订单状态和运单号，成功失败都写 task_item。前端轮询 task_id 展示进度，断网恢复后继续查。这个设计的代价是多了读模型和任务系统，但换来列表 P99 可控、2000 单批量操作可重试、错误行可下载、用户不会因为网络中断失去结果。""",
        followups=[
            dict(q="游标分页和 offset 分页怎么选？", a="待发货列表会持续新增和状态变化，深 offset 慢且容易跳页，所以主链路用 cursor，例如 promise_ship_at + order_id。offset 可以用于浅页、固定快照或后台小数据，但不能作为大商家核心分页方案。"),
            dict(q="跨页全选怎么做？", a="前端不要保存几万个 id。用户点击按当前筛选全选时，BFF 生成 selection_query_token，保存筛选条件、排除 id 和过期时间；提交批量操作时传 token，服务端按快照分页处理。"),
            dict(q="上传到一半网络断了怎么办？", a="使用对象存储分片上传或至少用 checksum 识别文件。前端保留 upload_id、file_id、checksum，恢复后续传或重新上传；后端创建任务时用 checksum + idempotency_key 防止重复处理同一文件。"),
            dict(q="30 行格式错误和 10 行订单取消如何展示？", a="解析阶段把格式错误标为 VALIDATION_FAILED，业务校验阶段把已取消标为 BUSINESS_FAILED，任务头展示成功、失败、处理中数量；失败明细提供行号、字段、错误码和修复建议，可下载后重试失败行。"),
            dict(q="列表筛选 P99 < 500ms 的关键是什么？", a="默认时间范围、商家维度组合索引、游标分页、BFF 批量聚合、读模型字段裁剪和缓存热点筛选项。不能跨多个服务逐行 join，也不能让模糊商品搜索拖慢主查询；复杂关键词可以先查搜索索引拿 order_id，再回读履约索引表。"),
            dict(q="前端如何避免慢响应覆盖新筛选结果？", a="每次筛选变化创建新的 request token 或 AbortController 取消旧请求；响应回来时校验 token 是否仍是当前查询。状态管理中把 queryKey 和数据绑定，旧 query 的结果不会写入新列表。"),
            dict(q="批量发货调用下游部分失败怎么办？", a="每行有独立状态和 attempt。系统错误退避重试，超过次数标为 SYSTEM_FAILED；订单已取消、无权限、运单号格式错是业务失败，不自动重试。任务可部分成功，用户下载失败行修正后重试。"),
            dict(q="看板数据为什么不直接扫订单表？", a="看板关注发货率、超时风险、异常数等聚合指标，实时性通常分钟级。直接扫订单热表会影响交易查询，应由事件流或定时任务写汇总库，BFF 读取汇总结果；口径变化时重算汇总，不阻塞商家发货主链路。"),
        ],
        variants=[
            "移动端商家版：减少表格列和批量能力，更多使用扫码发货和任务通知，但后端任务幂等与进度模型不变。",
            "多仓协同：筛选和权限增加 warehouse_id，批量任务按仓库拆分，避免一个仓库失败影响其他仓库。",
            "平台客服视角：权限范围从单商家变成多商家，必须加强审计、脱敏和按商家分片查询。",
        ],
    ),
    dict(
        id="x12",
        order=12,
        title="订单超时取消与延迟任务",
        brief="设计一个支持千万级延迟任务、取消改期和支付取消竞态处理的订单延迟任务系统。",
        statement="""你要设计一个订单延迟任务系统，用来处理未支付 30 分钟自动取消、未发货 48 小时提醒、签收 7 天自动确认收货等业务。系统要支持千万级待触发任务，触发误差小于 5 秒；任务可以取消和改期，例如用户延长支付时间、订单已支付后取消超时取消任务、商家发货后取消未发货提醒。系统必须处理支付回调和超时取消的竞态：订单 10:00 下单，10:30:00 超时取消任务触发，同时用户 10:29:59 发起的支付回调在 10:30:01 才到达，订单状态不能错。候选人要比较延迟消息、时间轮、定时扫描分片等方案，说明任务存储、触发、幂等、状态 CAS、补偿和监控。""",
        focus="""题眼是千万级延迟任务在误差 < 5 秒内触发，并且支付成功和超时取消并发时订单状态必须由订单状态机和版本 CAS 保证正确。""",
        scale="""规模假设：每日 1000 万订单，待触发延迟任务 3000 万到 8000 万；峰值每秒创建 5 万个支付超时任务，触发峰值 2 万/秒。触发误差 P99 < 5 秒，重复触发可接受但必须幂等。""",
        example="""订单 10:00 创建，系统写入 10:30:00 的未支付取消任务。用户 10:29:59 完成支付动作，但支付渠道回调 10:30:01 才到；同时 10:30:00 延迟任务已经触发取消检查。系统要通过支付流水时间、订单状态和 CAS 规则决定最终状态，不能出现已支付订单被取消或未支付订单永久不取消。""",
        minutes=45,
        sections=[
            dict(
                key="clarify",
                title="澄清语义",
                minutes=3,
                prompt="确认任务类型、触发误差、取消改期、竞态裁决、重复触发和业务幂等要求。",
                points=[
                    "确认延迟任务是提醒、检查还是直接执行业务变更",
                    "确认 30 分钟取消是否以创建时间、支付发起时间或支付成功时间为准",
                    "确认误差 < 5 秒是 P99 还是全部任务",
                    "确认任务可取消、可改期和可重建",
                    "确认重复触发、乱序触发和执行失败的语义",
                    "确认订单状态机是最终权威",
                ],
                reference="""先要强调延迟任务最好是触发检查，而不是不看状态直接改订单。未支付 30 分钟自动取消的业务语义要问清：从订单创建开始计时，还是允许支付发起后保留宽限；如果支付渠道回调晚到，是否以渠道支付成功时间为准。题目要求误差小于 5 秒，要确认是 P99 还是最大值，千万级任务通常承诺 P99 更现实。取消和改期是延迟系统的核心能力：订单已支付要取消支付超时任务，用户延长支付时间要改 trigger_at，商家发货后要取消未发货提醒。重复触发可接受，因为分布式系统里消息重试和扫描重入不可避免，但业务执行必须幂等。还要确认任务类型：取消订单是强业务变更，必须走订单服务状态机；未发货提醒是通知类，允许更高延迟；自动确认收货要考虑售后和物流状态。最终权威应是订单状态、支付流水和任务表状态，而不是消息队列里有没有一条消息。""",
            ),
            dict(
                key="estimate",
                title="规模估算",
                minutes=4,
                prompt="估算待触发任务量、创建触发峰值、分片扫描压力和时间轮槽位，推出存储与调度方案。",
                points=[
                    "每日千万订单会放大成多种延迟任务",
                    "峰值创建 5 万/秒要求写入路径可水平扩展",
                    "P99 < 5 秒要求不能分钟级全表扫描",
                    "近期开火任务和远期任务应分层存储",
                    "扫描分片要按 trigger_at 和 shard_key 命中索引",
                    "执行端要能承受重复和批量触发",
                ],
                reference="""每日 1000 万订单，每单至少有支付超时、发货提醒、确认收货三个任务，待触发任务可能达到 3000 万；如果订单周期跨 7 天，自动确认收货会让待触发任务累计到 8000 万以上。峰值每秒创建 5 万支付超时任务，关系库单表无法承受所有写入和扫描，必须按 shard_key 分库分表，或使用消息队列加任务库组合。误差 P99 < 5 秒意味着不能每分钟扫一次全表；扫描器需要每秒或更短周期拉取 trigger_at <= now + lookahead 的任务，并且索引是 status、trigger_at、shard_key。远期任务放数据库即可，近 5 到 10 分钟任务可以加载到时间轮或 Redis ZSet，提高触发精度。触发峰值 2 万/秒，执行端不能逐条同步调用外部服务到超时，应投递业务事件，订单服务批量消费或水平扩展。因为重复触发会发生，任务表和业务状态机都要有幂等键。""",
            ),
            dict(
                key="services",
                title="服务划分",
                minutes=7,
                prompt="画出订单服务、延迟任务服务、调度器、时间轮、消息队列、执行器和补偿扫描之间的关系。",
                diagram="""flowchart LR
  A["订单服务"] --> B["延迟任务API"]
  B --> C["任务库分片"]
  C --> D["装载器"]
  D --> E["近端时间轮/延迟队列"]
  E --> F["触发消息队列"]
  F --> G["任务执行器"]
  G --> A
  A --> H["支付服务"]
  H --> A
  I["补偿扫描器"] --> C
  I --> F
  G --> J["通知服务"]""",
                points=[
                    "延迟任务服务负责创建、取消、改期和查询任务",
                    "任务库是权威，消息队列和时间轮是触发加速层",
                    "装载器把近期任务加载到时间轮，远期任务留在数据库",
                    "执行器只发起业务检查，最终状态由订单服务 CAS",
                    "补偿扫描器处理漏装载、节点宕机和消息丢失",
                    "不同任务类型有不同执行器和重试策略",
                    "支付服务不直接删除任务，而是通过订单状态和取消接口协同",
                ],
                reference="""推荐方案是任务库加近端触发层。订单服务创建订单时调用延迟任务 API，写入 PAY_TIMEOUT task，trigger_at=created_at+30min；任务库是权威，保存状态、版本和业务键。装载器按分片扫描未来 5 到 10 分钟的 SCHEDULED 任务，加载到时间轮、Redis ZSet 或支持秒级延迟的队列。时间轮到点后投递 TriggerTask 消息到队列，执行器消费后先把 task 状态 CAS 为 TRIGGERING 或 FIRED，再调用订单服务 CancelIfUnpaid(order_id, task_id)。订单服务读取当前订单、支付流水和 version，决定是否取消。取消和改期接口更新任务库状态或 trigger_at，已加载到时间轮的旧任务即使触发，也会因 task_version 或状态不匹配被忽略。补偿扫描器持续扫描 trigger_at 已过但仍 SCHEDULED 的任务，重新投递，覆盖装载器宕机、消息丢失和时间轮丢槽。未发货提醒和自动确认收货可以复用同一任务服务，但执行器不同，重试和告警等级也不同。""",
            ),
            dict(
                key="tables",
                title="表设计",
                minutes=8,
                prompt="设计延迟任务、任务触发日志、分片游标、订单状态辅助表和执行失败表。",
                ddl="""CREATE TABLE delay_task (
  id BIGINT PRIMARY KEY,
  task_type VARCHAR(32) NOT NULL,
  biz_id VARCHAR(64) NOT NULL,
  biz_version BIGINT NOT NULL DEFAULT 0,
  shard_key BIGINT NOT NULL,
  trigger_at DATETIME NOT NULL,
  status VARCHAR(32) NOT NULL,
  payload TEXT,
  retry_count INT NOT NULL DEFAULT 0,
  version BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_biz_task (task_type, biz_id, biz_version),
  KEY idx_due (status, trigger_at, shard_key),
  KEY idx_biz (biz_id, task_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE delay_task_fire_log (
  id BIGINT PRIMARY KEY,
  task_id BIGINT NOT NULL,
  fire_id VARCHAR(64) NOT NULL,
  task_version BIGINT NOT NULL,
  fired_at DATETIME NOT NULL,
  execute_status VARCHAR(32) NOT NULL,
  error_code VARCHAR(64),
  created_at DATETIME NOT NULL,
  UNIQUE KEY uk_fire (fire_id),
  KEY idx_task_time (task_id, fired_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE delay_scan_cursor (
  id BIGINT PRIMARY KEY,
  shard_no INT NOT NULL,
  owner_id VARCHAR(64) NOT NULL,
  cursor_time DATETIME NOT NULL,
  lease_until DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_shard (shard_no),
  KEY idx_lease (lease_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE order_state_guard (
  id BIGINT PRIMARY KEY,
  order_id BIGINT NOT NULL,
  order_status VARCHAR(32) NOT NULL,
  pay_status VARCHAR(32) NOT NULL,
  paid_at DATETIME,
  cancel_reason VARCHAR(64),
  version BIGINT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_order (order_id),
  KEY idx_status_time (order_status, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE delay_dead_letter (
  id BIGINT PRIMARY KEY,
  task_id BIGINT NOT NULL,
  task_type VARCHAR(32) NOT NULL,
  biz_id VARCHAR(64) NOT NULL,
  reason VARCHAR(255) NOT NULL,
  retry_count INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL,
  resolved_at DATETIME,
  UNIQUE KEY uk_task_dead (task_id),
  KEY idx_status_time (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
                points=[
                    "delay_task 用 task_type + biz_id + biz_version 做业务幂等",
                    "trigger_at、status、shard_key 是扫描核心索引",
                    "version 用于取消、改期和触发 CAS",
                    "fire_log 记录每次触发，fire_id 防重复执行日志",
                    "scan_cursor 保存分片租约和扫描位置",
                    "order_state_guard 表示订单状态机需要的 CAS 字段",
                    "dead_letter 保存多次失败任务，便于人工处理",
                ],
                reference="""delay_task 是权威表，task_type 区分 PAY_TIMEOUT、SHIP_REMIND、AUTO_CONFIRM，biz_id 通常是 order_id，biz_version 用来处理改期或重新创建；同一个业务版本只能有一个有效任务。status 包括 SCHEDULED、CANCELED、FIRED、DONE、FAILED，trigger_at 用于到期扫描，shard_key 可以取 order_id 哈希。idx_due 必须以 status、trigger_at 开头，扫描器才能快速找到到期任务；千万级任务下还要按 shard_key 分库分表。version 用于 CAS：取消任务 update ... where status='SCHEDULED' and version=?；触发也带 task_version，旧时间轮消息会被拒绝。fire_log 是审计和幂等辅助，记录某次触发的 fire_id、task_version、执行状态和错误。scan_cursor 保存每个扫描分片的租约，多个调度器通过 lease_until 抢占，避免重复扫描过多；即使重复扫描也依赖 task CAS 去重。order_state_guard 不是要求单独建表，而是强调订单表必须有 status、pay_status、paid_at、version 等字段，延迟任务最终调用订单状态机。dead_letter 记录重试多次失败的任务，触发人工处理或告警。""",
            ),
            dict(
                key="api",
                title="接口和事件",
                minutes=5,
                prompt="列出创建、取消、改期、触发、执行和补偿接口，说明幂等键与竞态裁决。",
                points=[
                    "CreateDelayTask 幂等创建业务任务",
                    "CancelDelayTask 带 task_version 或 biz_version",
                    "RescheduleDelayTask 生成新版本或 CAS 修改 trigger_at",
                    "TriggerTask 消息带 task_id、task_version、fire_id",
                    "订单服务提供 CancelIfUnpaid 和 AutoConfirmIfEligible",
                    "查询接口能按 biz_id 查当前有效任务和触发历史",
                ],
                reference="""CreateDelayTask(task_type, biz_id, biz_version, trigger_at, payload, idempotency_key) 写 delay_task，重复调用返回已有任务。CancelDelayTask(task_type, biz_id, expected_version) 只能取消 SCHEDULED 状态，若任务已 FIRED，要让业务执行器在订单状态机中幂等判断。RescheduleDelayTask 可以 CAS 更新 trigger_at 并 version+1，也可以取消旧任务后创建 biz_version+1 的新任务；后者更容易识别旧时间轮消息。TriggerTask 消息必须带 task_id、task_version、fire_id、scheduled_trigger_at，执行器先查 task 状态和版本，不匹配就丢弃。订单服务接口 CancelIfUnpaid(order_id, task_id, scheduled_trigger_at) 的语义是检查订单仍未支付且未取消，才 CAS 改为 CANCELED；AutoConfirmIfEligible 检查已签收超过 7 天且无进行中售后。支付回调 PaymentSucceeded(order_id, paid_at, payment_id) 走订单服务状态机，如果 paid_at 在支付有效期内，即使回调晚到，也应优先让订单进入 PAID，并使超时取消执行失败为 NOT_ELIGIBLE。查询接口 GET /delay-tasks?biz_id= 返回当前任务、历史触发和失败原因，便于客服排查。""",
            ),
            dict(
                key="states",
                title="状态机和竞态",
                minutes=5,
                prompt="画出延迟任务状态和订单支付取消竞态，说明旧任务触发、取消、改期如何安全处理。",
                diagram="""stateDiagram-v2
  [*] --> SCHEDULED
  SCHEDULED --> CANCELED: 业务取消
  SCHEDULED --> RESCHEDULED: 改期生成新版本
  SCHEDULED --> TRIGGERING: 到期CAS
  TRIGGERING --> FIRED: 投递执行消息
  FIRED --> DONE: 业务检查成功
  FIRED --> SKIPPED: 条件不满足
  FIRED --> FAILED: 执行失败
  FAILED --> SCHEDULED: 退避重试
  FAILED --> DEAD: 超过重试
  CANCELED --> [*]
  RESCHEDULED --> [*]
  DONE --> [*]
  SKIPPED --> [*]
  DEAD --> [*]""",
                points=[
                    "任务到期只是进入 TRIGGERING，最终订单变更由订单状态机决定",
                    "取消和触发并发时用 task.version CAS，失败方重读状态",
                    "改期后旧版本消息因 task_version 不匹配被丢弃",
                    "支付回调和超时取消并发时用订单 version 和支付有效期裁决",
                    "重复触发最多产生重复 SKIPPED 或幂等 DONE",
                    "失败重试要避免无限重试导致状态抖动",
                ],
                reference="""延迟任务状态机和订单状态机要分开。任务从 SCHEDULED 到 TRIGGERING 表示调度器抢到了触发权，再到 FIRED 表示消息已投递；执行后可能 DONE，也可能 SKIPPED，因为业务条件已不满足，例如订单已支付。取消任务时只更新 delay_task 状态，不直接假设时间轮消息不存在；旧消息到达后读取状态发现 CANCELED 或 version 不匹配就丢弃。改期可以把旧任务置为 RESCHEDULED 并创建新 biz_version，旧消息带旧 task_version，因此不会误触发。支付与取消竞态必须在订单服务里裁决：CancelIfUnpaid 执行条件是 order_status='CREATED'、pay_status='UNPAID'、version 匹配，并且没有有效 paid_at；PaymentSucceeded 执行条件是支付流水合法且订单未进入不可逆取消。如果 10:29:59 支付成功但 10:30:01 回调才到，业务若认定 paid_at 在有效期内，应允许支付成功覆盖未完成的超时检查；若订单已 CAS 取消，则需要进入支付冲正或人工异常，这个规则必须事先定义。""",
            ),
            dict(
                key="flows",
                title="核心流程",
                minutes=6,
                prompt="用顺序图说明订单创建延迟任务、装载触发、支付回调和超时取消竞态处理。",
                diagram="""sequenceDiagram
  participant O as 订单服务
  participant D as 延迟任务服务
  participant DB as 任务库
  participant W as 时间轮
  participant Q as 触发队列
  participant E as 执行器
  participant P as 支付服务
  O->>D: create PAY_TIMEOUT(order_id,10:30)
  D->>DB: insert SCHEDULED
  D-->>O: task_id
  D->>W: load near task
  W->>Q: TriggerTask(task_id,version)
  Q->>E: consume
  E->>DB: CAS SCHEDULED->TRIGGERING
  P-->>O: PaymentSucceeded(paid_at=10:29:59)
  E->>O: CancelIfUnpaid(order_id,task_id)
  O->>O: check status/version/paid_at
  O-->>E: SKIPPED or CANCELED
  E->>DB: mark DONE/SKIPPED""",
                points=[
                    "订单创建和任务创建要在本地事务或可靠事件中保证最终都有",
                    "装载器只装载近端任务，漏装载由补偿扫描发现",
                    "触发消息带版本，执行前回查任务库",
                    "支付回调与取消检查都进入订单服务 CAS",
                    "执行结果回写任务表，失败进入重试或死信",
                    "取消改期不依赖删除队列消息，而依赖版本判断",
                ],
                reference="""订单创建时，订单服务要保证订单记录和 PAY_TIMEOUT 任务最终一致。可以在订单本地事务里写 outbox 事件，再由可靠消费者创建延迟任务；也可以同库事务写 delay_task。装载器周期性扫描未来窗口内的任务放入时间轮，时间轮负责秒级触发；如果装载器宕机，补偿扫描器会发现 trigger_at 已过但仍 SCHEDULED 的任务并重新投递。触发消息到执行器后，执行器不是直接取消订单，而是先 CAS 抢任务触发权，抢不到说明已取消、已改期或被其他执行器处理。支付回调和超时取消在顺序图中可能交叉，二者都调用订单服务状态机；订单服务用 order_id 的版本条件更新，并读取支付流水 paid_at 判断是否在有效期内。执行器根据订单服务返回 CANCELED、SKIPPED、RETRYABLE_ERROR 回写任务。取消和改期不尝试从时间轮或消息队列删除旧消息，因为删除不可靠；版本号和状态检查才是兜底。""",
            ),
            dict(
                key="reliability",
                title="可靠性和指标",
                minutes=7,
                prompt="说明漏触发、重复触发、时钟漂移、节点宕机、消息堆积、数据库压力和业务竞态的兜底。",
                points=[
                    "漏触发靠补偿扫描 trigger_at < now 且仍 SCHEDULED 的任务",
                    "重复触发靠 task.version、fire_id 和业务状态机幂等",
                    "时钟漂移通过统一时钟源和服务端 now 控制",
                    "节点宕机靠扫描租约、时间轮重建和消息重投",
                    "消息堆积时按任务类型降级，提醒类可延后，取消类优先",
                    "数据库压力靠分片、批量扫描、近端时间轮和归档",
                    "监控触发延迟 P99、漏触发数、重复率、CAS 失败率和死信数",
                ],
                reference="""延迟任务系统要默认消息不可靠、节点会宕机。漏触发的兜底是补偿扫描器：持续扫描 trigger_at < now - grace 且 status 仍为 SCHEDULED 的任务，重新投递；grace 可以是 2 到 5 秒，避免和正常触发重复太多。重复触发不可避免，所以 TriggerTask 带 task_version 和 fire_id，delay_task 状态 CAS 保证同一版本只有一个执行器进入 TRIGGERING，订单服务状态机再做最终幂等。时钟漂移会直接影响 5 秒误差，所有 trigger_at 以服务端数据库时间或统一时间源生成，调度器监控本机 clock offset，超过阈值摘除。节点宕机时，scan_cursor 的 lease_until 过期后其他节点接管；时间轮中的近端任务可从任务库重新装载。消息堆积时按任务类型优先级处理，支付超时取消优先，提醒通知可延后或合并。数据库压力通过分片、批量拉取、覆盖索引、近端时间轮和历史任务归档控制。关键指标包括创建成功率、触发延迟 P50/P99/P999、漏触发补偿数、重复触发率、任务 CAS 冲突率、执行成功率、死信数、订单竞态 SKIPPED 比例和队列堆积。""",
            ),
        ],
        mistakes=[
            dict(wrong="延迟消息到点后直接把订单改成取消", verdict="最大扣分点", why="这会在支付回调并发或订单已支付时误取消订单，延迟任务只能触发检查，最终状态必须由订单状态机裁决。"),
            dict(wrong="完全依赖消息队列延迟消息，不落任务表", verdict="有错", why="没有权威任务表就无法取消、改期、查询、补偿漏触发，也无法解释旧消息为什么被忽略。"),
            dict(wrong="用每分钟全表扫描处理千万任务", verdict="有错", why="分钟级扫描无法满足误差 < 5 秒，且全表扫描会压垮数据库，应按 trigger_at 分片索引扫描或近端时间轮。"),
            dict(wrong="取消任务时尝试删除队列里的消息作为唯一保证", verdict="方向对但不准", why="队列消息和时间轮槽位不一定能可靠删除，必须靠任务状态和版本在执行时判定。"),
            dict(wrong="支付回调晚于 30 分钟就一律失败", verdict="方向对但不准", why="要看业务定义和支付流水 paid_at，示例中 10:29:59 已发起或成功的支付可能应被认定有效。"),
            dict(wrong="所有任务类型同优先级执行", verdict="缺失", why="支付超时取消影响库存和订单状态，提醒通知可延后；堆积时必须按业务影响设置优先级。"),
        ],
        walkthrough="""先比较方案：纯延迟消息简单但取消改期和补偿弱；纯数据库扫描可靠但难做到 5 秒；时间轮精度高但内存态需要重建。推荐任务库作为权威，加近端时间轮或延迟队列做触发加速，补偿扫描兜底。表设计讲 delay_task 的 trigger_at、status、version、biz_key，fire_log 和 scan_cursor。流程讲订单创建写任务，装载器加载近端任务，到点投递 TriggerTask，执行器回查任务版本，再调用订单服务 CancelIfUnpaid。竞态用示例说明：支付回调和取消检查都走订单状态机 CAS，并按 paid_at 和业务规则裁决。最后讲漏触发、重复触发、时钟漂移、节点宕机、消息堆积、分片和监控。""",
        oral="""我会把延迟任务系统设计成权威任务库加近端触发层。任务库保存 task_type、biz_id、trigger_at、status、version，是创建、取消、改期、查询和补偿的依据；近 5 到 10 分钟的任务由装载器加载到时间轮或延迟队列，到点后发 TriggerTask 消息。执行器收到消息后必须回查任务库，用 task_version CAS 抢触发权，然后调用订单服务的 CancelIfUnpaid 或 AutoConfirmIfEligible。这样旧消息、重复消息和已取消任务都会被状态和版本拦住。支付回调与超时取消的竞态不在延迟系统里拍脑袋解决，而在订单状态机里用 order version、pay_status 和 paid_at 裁决：如果业务认定 10:29:59 的支付有效，即使回调 10:30:01 才到，超时取消也应该跳过或被纠正。这个方案比纯队列复杂，但支持千万级任务、取消改期、秒级误差和补偿扫描。监控重点是触发延迟 P99、漏触发补偿、重复触发、CAS 冲突和死信。""",
        followups=[
            dict(q="为什么不直接用延迟消息队列？", a="延迟消息适合简单到期触发，但任务取消、改期、查询、补偿和审计都弱。队列里的旧消息不一定能删除，系统重启后也难解释状态；所以需要任务库作为权威，队列只是触发通道。"),
            dict(q="时间轮和数据库扫描怎么配合？", a="数据库保存所有任务，扫描器只把未来几分钟的任务加载到时间轮。时间轮负责秒级触发，数据库补偿扫描负责漏触发和重建。这样远期任务不占大量内存，近端任务又能满足 5 秒误差。"),
            dict(q="支付成功和超时取消同时发生谁赢？", a="不能由消息先后决定，必须由订单状态机按业务规则裁决。常见规则是若支付流水 paid_at 在有效期内，支付成功优先；若已经合法取消且支付实际完成在超时后，则进入退款或异常处理。更新用 order version CAS。"),
            dict(q="任务改期后旧消息触发怎么办？", a="改期时 task version 增加或创建新 biz_version。旧消息携带旧 version，执行器回查发现不匹配就标记 SKIPPED，不调用业务变更。这比尝试删除旧消息可靠。"),
            dict(q="如何保证创建订单后一定有超时任务？", a="可以用本地事务写订单和 outbox，再由 outbox 消费者创建 delay_task；或订单和 delay_task 同库事务写入。后台扫描新建未支付但没有任务的订单做补偿，监控缺失率。"),
            dict(q="千万级任务表怎么分片？", a="按 shard_key 例如 order_id 哈希分库分表，每个分片都有 status + trigger_at 索引。扫描器按分片租约工作，每次批量拉取小窗口任务，处理后推进 cursor，历史 DONE/CANCELED 任务定期归档。"),
            dict(q="误差 < 5 秒怎么监控？", a="记录 scheduled_trigger_at、actual_fire_at、executor_start_at、business_done_at，分别计算调度延迟、队列延迟和执行业务延迟。SLO 用 P99/P999，超过阈值按任务类型看队列堆积和扫描滞后。"),
            dict(q="自动确认收货和支付超时取消有什么不同？", a="支付超时取消是强一致高优先级，会影响库存释放；自动确认收货通常可以容忍更高延迟，但要检查物流签收时间、售后状态和用户延长收货。两者复用任务系统，业务执行器和优先级不同。"),
        ],
        variants=[
            "低规模系统：可以只用数据库分片扫描和消息队列，不引入时间轮，但扫描周期必须满足业务误差。",
            "高精度倒计时：近 1 分钟任务放内存时间轮，远期任务在数据库，节点重启后从任务库重建时间轮。",
            "多地域部署：任务按订单归属地域创建和触发，跨地域只做灾备，避免两个地域同时取消同一订单。",
        ],
    ),
]
